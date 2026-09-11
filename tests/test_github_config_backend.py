#!/usr/bin/env python3
"""GitHub 配置、拉取、离线缓存与核验。

任务票 11 从 tests/test_github_backend.py 按真实行为主题拆出;检查含义与原
案例保持一致,仅重组位置。原总入口仍聚合本主题。本主题可直接运行:

    python3 -B tests/test_github_config_backend.py
"""

import json
import subprocess
import sys
import tempfile
from pathlib import Path

from github_backend_transport import FakeTransport
from github_backend_fixtures import (
    AUTH, REPO_ROOT, SHARED_BODY, _seed_raw_issue, make_checker,
    make_github_project, make_local_project, run_cli, run_theme,
)

import mgs_github  # noqa: E402
import mgs_records  # noqa: E402

FAILURES, check = make_checker()


def test_parse_repo_location() -> None:
    parsed = mgs_github.parse_repo_location("github.com/owner/repo")
    check(parsed == {"host": "github.com", "owner": "owner", "repo": "repo"},
          f"标准坐标应解析出 host/owner/repo,实际 {parsed}")
    parsed = mgs_github.parse_repo_location("https://github.com/owner/repo")
    check(parsed is not None and parsed["repo"] == "repo",
          "https 前缀应可解析")
    for vague in ("owner/repo", "github.com", "github.com/owner",
                  "github.com/owner/repo/extra", "就用 GitHub 吧", ""):
        try:
            mgs_github.parse_repo_location(vague)
        except mgs_github.GithubRecordsError:
            check(True, "")
        else:
            check(False, f"含糊位置 {vague!r} 应拒绝(必须明确 host/owner/repository)")


def test_parse_remote_authorizations() -> None:
    scopes = mgs_github.parse_remote_authorizations(
        f"{AUTH};github.com/other/r2(只读引用)")
    writable = {(s["host"], s["owner"], s["repo"]) for s in scopes
                if "issues-write" in s["ops"]}
    check(("github.com", "mygamestudio", "issue-accept") in writable,
          f"issues-write 授权应被解析,实际 {scopes}")
    check(not any(s["repo"] == "r2" and "issues-write" in s["ops"]
                  for s in scopes),
          "只读引用不应被解析为写授权")
    check(mgs_github.parse_remote_authorizations("无") == [],
          "无外部访问时应返回空授权")


def test_load_config_github_backend() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = make_github_project(Path(tmp))
        config = mgs_records.load_config(root)
        check(config["backend"] == "github-issues", "后端应原样回报 github-issues")
        check(config["repo"] == {"host": "github.com",
                                 "owner": "mygamestudio",
                                 "repo": "issue-accept"},
              f"CONFIG 应解析出仓库坐标,实际 {config.get('repo')}")
        check(config["remote_write_authorized"] is True,
              "外部访问含 issues-write 授权时应回报已授权")
    with tempfile.TemporaryDirectory() as tmp:
        root = make_github_project(Path(tmp), external="无(仅本地引用)")
        config = mgs_records.load_config(root)
        check(config["remote_write_authorized"] is False,
              "外部访问无写授权时不得回报已授权(选择后端不等于授权写入)")
    with tempfile.TemporaryDirectory() as tmp:
        root = make_github_project(Path(tmp), repo="owner/repo")
        try:
            mgs_records.load_config(root)
        except mgs_records.RecordsError as exc:
            check("host" in str(exc) or "仓库" in str(exc) or "位置" in str(exc),
                  f"含糊仓库位置错误应说明原因:{exc}")
        else:
            check(False, "含糊仓库位置(github.com 缺失)应报错")


def test_fetch_and_dispatch() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = make_github_project(Path(tmp))
        fake = FakeTransport()
        fake.seed_issue("01-alpha", "甲任务")
        fake.seed_issue("02-beta", "乙任务", triage="needs-info",
                        progress="待执行", project_label="info",
                        deps="01-alpha")
        fake.issues.append({"number": 99, "id": 99, "title": "PR", "body": "",
                            "labels": [], "state": "open", "pull_request": {}})
        tasks = mgs_records.list_tasks(root, transport=fake)
        ids = [task["identity"] for task in tasks]
        check(ids == ["01-alpha", "02-beta"],
              f"应列出两个任务(排除 PR),实际 {ids}")
        by_id = {task["identity"]: task for task in tasks}
        check(by_id["01-alpha"]["triage"] == "ready-for-agent",
              f"标签 agent-ready 应映射回 ready-for-agent,实际 {by_id['01-alpha']['triage']}")
        check(by_id["02-beta"]["progress"] == "待执行", "正文进度应可回读")
        graph = mgs_records.task_dependencies(root, transport=fake)
        check(graph["edges"].get("02-beta") == ["01-alpha"],
              f"github 后端依赖边应与本地后端同语义,实际 {graph['edges']}")
        check(graph["ok"] is True, "健康依赖图应 ok")
        ready = mgs_records.startable_tasks(root, transport=fake)
        startable = {item["identity"] for item in ready["startable"]}
        check("01-alpha" in startable and "02-beta" not in startable,
              "github 后端可开工集合语义应与本地一致")
        check(any("输入不足" in r or "needs-info" in r
                  for r in next(i for i in ready["blocked"]
                                if i["identity"] == "02-beta")["reasons"]),
              "needs-info 任务应给出输入不足原因")
        task = mgs_records.read_task(root, "01-alpha", transport=fake)
        check(task["identity"] == "01-alpha" and task["title"] == "甲任务",
              "read_task 应回读身份与标题")


def test_offline_cache_and_no_local_fallback() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = make_github_project(Path(tmp))
        cache = Path(tmp) / "gh-cache"
        fake = FakeTransport()
        fake.seed_issue("01-alpha", "甲任务")
        tasks = mgs_records.list_tasks(root, transport=fake, cache_dir=cache)
        check([t["identity"] for t in tasks] == ["01-alpha"], "在线拉取应成功")
        fake.offline()
        tasks = mgs_records.list_tasks(root, transport=fake, cache_dir=cache)
        check(tasks and tasks[0].get("cached_read") is True,
              "离线时应返回缓存并逐任务标注 cached_read")
        task = mgs_records.read_task(root, "01-alpha", transport=fake, cache_dir=cache)
        check(task.get("cached_read") is True and "缓存" in task.get("cached_note", ""),
              "离线单任务读取应标注缓存来源与状态")
        # 无缓存 + 离线 → 明确报错,绝不回退本地任务目录
        fresh = FakeTransport()
        fresh.offline()
        try:
            mgs_records.list_tasks(root, transport=fresh)
        except mgs_records.RecordsError as exc:
            message = str(exc)
            check("远端不可用" in message and "无缓存" in message,
                  f"无缓存离线应说明远端不可用且无缓存:{message}")
            check("不静默切换本地后端" in message,
                  "错误必须声明不静默切换本地后端")
        else:
            check(False, "无缓存离线应报错而非返回本地任务")


def test_verify_github_backend() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = make_github_project(Path(tmp))
        fake = FakeTransport()
        fake.seed_issue("01-alpha", "甲任务")
        fake.seed_issue("02-beta", "乙任务", project_label="agent-ready",
                        deps="01-alpha")
        report = mgs_records.verify_project(root, transport=fake)
        check(report["ok"] is True,
              f"健康 github 项目应通过 verify:{[c for c in report['checks'] if not c['ok']]}")
        names = {c["name"] for c in report["checks"]}
        for expected in ("config-present", "backend-github-coordinates",
                         "labels-complete", "labels-no-conflict",
                         "labels-remote-present", "tasks-valid",
                         "deps-consistent", "results-consistent"):
            check(expected in names, f"github verify 应包含 {expected},实际 {names}")
    with tempfile.TemporaryDirectory() as tmp:
        root = make_github_project(Path(tmp))
        fake = FakeTransport()
        # 分流标签映射缺失(needs-info 未映射)→ labels-complete 失败
        config_path = root / "docs" / "mygamestudio" / "CONFIG.md"
        config_path.write_text(config_path.read_text(encoding="utf-8").replace(
            "| needs-info | info |", ""), encoding="utf-8")
        report = mgs_records.verify_project(root, transport=fake)
        failed = {c["name"] for c in report["checks"] if not c["ok"]}
        check("labels-complete" in failed, f"标签映射缺类应判失败,实际 {failed}")
    with tempfile.TemporaryDirectory() as tmp:
        root = make_github_project(Path(tmp))
        fake = FakeTransport()
        fake.seed_issue("01-alpha", "甲任务")
        fake.seed_issue("02-beta", "乙任务", deps="99-missing")
        report = mgs_records.verify_project(root, transport=fake)
        failed = {c["name"] for c in report["checks"] if not c["ok"]}
        check("deps-consistent" in failed, f"未解析依赖应判失败,实际 {failed}")
        check(report["ok"] is False, "存在未解析依赖时整体不应 ok")


def test_verify_offline_keeps_unchecked_and_skipped() -> None:
    """票 06 AC4/READ-11:离线 verify 保留「未核对」与 skipped 表达。

    远端不可用时标签与评论检查不得冒充已核验——保持未核对表达并列入
    skipped;基于缓存的结构与依赖检查照常给出。
    """

    with tempfile.TemporaryDirectory() as tmp:
        root = make_github_project(Path(tmp))
        cache = Path(tmp) / "cache"
        fake = FakeTransport()
        fake.seed_issue("01-alpha", "甲任务")
        mgs_records.list_tasks(root, transport=fake, cache_dir=cache)  # 填充缓存
        fake.offline()
        report = mgs_records.verify_project(root, transport=fake, cache_dir=cache)
        check(report.get("offline") is True,
              f"离线 verify 应标注 offline,实际 {report.get('offline')}")
        skipped = set(report.get("skipped") or [])
        check({"labels-remote-present", "results-consistent"} <= skipped,
              f"离线应把远端存在性检查列入 skipped,实际 {skipped}")
        by_name = {c["name"]: c for c in report["checks"]}
        check(by_name["labels-remote-present"]["detail"] == "未核对(离线缓存,不下结论)",
              f"离线标签检查应保持未核对表达,实际 {by_name['labels-remote-present']}")
        check(by_name["results-consistent"]["detail"] == "未核对(离线缓存,不下结论)",
              f"离线评论结果检查应保持未核对表达,实际 {by_name['results-consistent']}")
        check(by_name["tasks-valid"]["ok"] is True
              and by_name["deps-consistent"]["ok"] is True,
              f"离线基于缓存的结构与依赖检查应照常给出,实际 {by_name}")


def test_verify_shared_core_validation_both_backends() -> None:
    """核验建议 1:任务核心校验单一实现——同一份畸形任务(缺工作请求必填
    字段)在本地与 GitHub 后端得到相同核验结论。"""

    malformed = {"输入与基线": "GAME_DESIGN v1", "依赖": "无"}
    with tempfile.TemporaryDirectory() as tmp:
        root = make_github_project(Path(tmp))
        fake = FakeTransport()
        fake.seed_issue("01-alpha", "甲任务", request=dict(malformed))
        report = mgs_records.verify_project(root, transport=fake)
        github_check = next((c for c in report["checks"]
                             if c["name"] == "tasks-valid"), {})
        check(github_check.get("ok") is False,
              f"GitHub 后端应核对工作请求必填字段,实际 {github_check}")
        check(all(key in (github_check.get("detail") or "")
                  for key in ("当前目标", "完成标准", "执行责任")),
              f"缺失的工作请求字段应逐项报告,实际 {github_check.get('detail')}")
    with tempfile.TemporaryDirectory() as tmp:
        local = make_local_project(Path(tmp))
        task_path = local / "docs/mygamestudio/work/01-alpha/task.md"
        task_path.write_text("".join(
            line for line in task_path.read_text(encoding="utf-8").splitlines(True)
            if not any(line.startswith(f"- {key}:") for key in
                       ("当前目标", "完成标准", "执行责任"))), encoding="utf-8")
        report = mgs_records.verify_project(local)
        local_check = next((c for c in report["checks"]
                            if c["name"] == "tasks-valid"), {})
        check(local_check.get("ok") is False
              and all(key in (local_check.get("detail") or "")
                      for key in ("当前目标", "完成标准", "执行责任")),
              f"本地后端应得到相同核验结论,实际 {local_check}")
        check((github_check.get("ok") is False) == (local_check.get("ok") is False),
              "两后端对同一畸形任务必须得出一致结论")


def test_record_model_cross_backend_body_semantics() -> None:
    """READ-08:同正文经本地与 GitHub 读取,共通字段与核心核验一致;
    空字段、未知小节、字段分隔及畸形任务的可见性保持;后端专有字段保留。
    """

    import mgs_record_model

    parsed = mgs_record_model.parse_task_body(SHARED_BODY)
    check(parsed["identity"] == "", "共享解析应保留空身份字段")
    check(parsed["progress"] == "待执行", "共享解析应在分号处截断字段值")
    check(parsed["request"].get("完成标准") == "", "共享解析应保留空值字段")
    check(parsed["request"].get("执行责任") == "Agent（制作实现）",
          "共享解析应以全角冒号分隔字段")
    check(parsed["sections"].get("未知小节") is True, "共享解析应保留未知小节")

    with tempfile.TemporaryDirectory() as tmp:
        local = make_local_project(Path(tmp) / "local")
        task_dir = local / "docs" / "mygamestudio" / "work" / "05-malformed"
        task_dir.mkdir(parents=True)
        (task_dir / "task.md").write_text(SHARED_BODY, encoding="utf-8")
        local_task = mgs_records.read_task(local, "05-malformed")
        local_report = mgs_records.verify_project(local)

    with tempfile.TemporaryDirectory() as tmp:
        gh = make_github_project(Path(tmp) / "gh")
        fake = FakeTransport()
        _seed_raw_issue(fake, SHARED_BODY)
        # 畸形任务缺身份:Github read_task 按身份定位无法命中(既有语义),
        # 但列表与核验必须仍能看到它,不被提前过滤。
        gh_tasks = mgs_records.list_tasks(gh, transport=fake)
        check(len(gh_tasks) == 1, f"畸形任务应仍被列出,实际 {gh_tasks}")
        gh_task = gh_tasks[0]
        gh_report = mgs_records.verify_project(gh, transport=fake)

    common = ("identity", "title", "triage", "progress", "request", "sections",
              "result_index_text")
    for key in common:
        check(local_task.get(key) == gh_task.get(key),
              f"共通字段 {key} 应一致:本地 {local_task.get(key)!r} vs "
              f"GitHub {gh_task.get(key)!r}")
    check(local_task["identity"] == "" and gh_task["identity"] == "",
          "畸形身份应两端可见,不被提前过滤")
    check(local_task["sections"].get("未知小节") is True
          and gh_task["sections"].get("未知小节") is True,
          "未知小节应两端保留")
    # 后端专有字段留在各自 adapter,不以统一为由删减
    for key in ("directory", "path", "results"):
        check(key in local_task, f"本地 adapter 应保留专有字段 {key}")
    check("directory" not in gh_task and "path" not in gh_task,
          "GitHub 结果不应含本地目录/路径字段")
    for key in ("issue_number", "state", "labels", "triage_source",
                "triage_conflict", "body"):
        check(key in gh_task, f"GitHub adapter 应保留专有字段 {key}")
    check("issue_number" not in local_task, "本地结果不应含 Issue 字段")

    local_check = next(c for c in local_report["checks"]
                       if c["name"] == "tasks-valid")
    gh_check = next(c for c in gh_report["checks"] if c["name"] == "tasks-valid")
    check(local_check["ok"] is False and gh_check["ok"] is False,
          "同一畸形任务两端核心核验结论应一致(均为不通过)")
    for detail in (local_check["detail"], gh_check["detail"]):
        check("正文身份缺失或不合规" in detail,
              f"核心核验应报告身份问题:{detail}")


def test_error_identity_across_import_orders_and_script() -> None:
    """READ-10:records 先导入、GitHub 先导入与直接脚本调用下错误身份单一、
    现有捕获分支有效、无未捕获 traceback;READ-09:后端记录错误退出码 2 保持。
    """

    records_dir = REPO_ROOT / "plugin" / "records"
    probe = (
        "import sys\n"
        f"sys.path.insert(0, {str(records_dir)!r})\n"
        "{first}\n"
        "{second}\n"
        "import mgs_record_model\n"
        "assert mgs_records.RecordsError is mgs_record_model.RecordsError\n"
        "assert mgs_github.RecordsError is mgs_record_model.RecordsError\n"
        "assert issubclass(mgs_github.GithubRecordsError, "
        "mgs_records.RecordsError)\n"
        "assert issubclass(mgs_github.GithubRecordsError, "
        "mgs_record_model.RecordsError)\n"
        "print('OK')\n"
    )
    for label, first, second in (("records-first", "import mgs_records",
                                  "import mgs_github"),
                                 ("github-first", "import mgs_github",
                                  "import mgs_records")):
        result = subprocess.run(
            [sys.executable, "-B", "-c",
             probe.format(first=first, second=second)],
            capture_output=True, text=True)
        check(result.returncode == 0 and "OK" in result.stdout,
              f"{label} 导入顺序下错误身份应单一:{result.stderr[-300:]}")

    # 直接脚本调用触发 GithubRecordsError:现有 except RecordsError 分支有效,
    # 输出 JSON 错误、退出码 2、无未捕获 traceback(零网络:授权检查先于请求)。
    with tempfile.TemporaryDirectory() as tmp:
        root = make_github_project(Path(tmp), external="无(未授权远端写入)")
        result = run_cli("create", "--project", str(root),
                         "--identity", "09-x", "--title", "x")
        check(result.returncode == 2,
              f"后端记录错误应保留退出码 2,实际 {result.returncode}:"
              f"{result.stdout[:200]}{result.stderr[:200]}")
        try:
            payload = json.loads(result.stdout)
        except ValueError:
            check(False, f"应输出 JSON 错误对象,实际 {result.stdout[:200]}")
        else:
            check(isinstance(payload, dict) and "error" in payload,
                  f"错误对象应含 error 字段,实际 {payload}")
        check("Traceback" not in result.stderr,
              f"不应泄露未捕获 traceback:{result.stderr[-300:]}")


def test_label_priority_and_conflict_preserved() -> None:
    """阶段收口 READ-08:标签优先级、分流冲突与关闭事实在共享正文后仍保留。

    同一正文经共享规则解析后,分流仍以标签为准(label 优先于正文),
    多标签按后端返回顺序取第一个可识别语义,差异登记在 triage_conflict;
    正文无标签、标签无正文时各自的 triage_source 如实表达。这些是 GitHub
    存储专有事实,不因共享正文解析被拉平。
    """

    with tempfile.TemporaryDirectory() as tmp:
        root = make_github_project(Path(tmp))
        fake = FakeTransport()

        # ① 标签与正文不一致:标签赢,并登记冲突
        _seed_raw_issue(fake, number=1, identity="01-conflict", title="冲突任务",
                        triage="ready-for-agent", labels=["info"])
        # ② 多标签:按后端返回顺序取第一个可识别语义(wont-do → wontfix 优先)
        _seed_raw_issue(fake, number=2, identity="02-multi", title="冲突任务",
                        triage="ready-for-agent",
                        labels=["wont-do", "agent-ready"])
        # ③ 仅正文:按正文表达,无冲突
        _seed_raw_issue(fake, number=3, identity="03-body", title="冲突任务",
                        triage="ready-for-human", labels=[])

        tasks = {t["identity"]: t for t in
                 mgs_records.list_tasks(root, transport=fake)}
        conflict = tasks["01-conflict"]
        check(conflict["triage"] == "needs-info"
              and conflict["triage_source"] == "label"
              and conflict["triage_conflict"] is True,
              f"标签应覆盖正文分流并登记冲突,实际 {conflict}")
        multi = tasks["02-multi"]
        check(multi["triage"] == "wontfix" and multi["triage_source"] == "label"
              and multi["triage_conflict"] is True,
              f"多标签应按返回顺序取首个可识别语义,实际 {multi}")
        from_body = tasks["03-body"]
        check(from_body["triage"] == "ready-for-human"
              and from_body["triage_source"] == "body"
              and from_body["triage_conflict"] is False,
              f"无标签时应按正文表达且不误报冲突,实际 {from_body}")

TESTS = (
    test_parse_repo_location,
    test_parse_remote_authorizations,
    test_load_config_github_backend,
    test_fetch_and_dispatch,
    test_offline_cache_and_no_local_fallback,
    test_verify_github_backend,
    test_verify_offline_keeps_unchecked_and_skipped,
    test_verify_shared_core_validation_both_backends,
    test_record_model_cross_backend_body_semantics,
    test_error_identity_across_import_orders_and_script,
    test_label_priority_and_conflict_preserved,
)

if __name__ == "__main__":
    sys.exit(run_theme("GitHub 配置、拉取、离线缓存与核验", TESTS, FAILURES))

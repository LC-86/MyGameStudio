#!/usr/bin/env python3
"""后端切换迁移与交接基线可达。

任务票 11 从 tests/test_github_backend.py 按真实行为主题拆出;检查含义与原
案例保持一致,仅重组位置。原总入口仍聚合本主题。本主题可直接运行:

    python3 -B tests/test_github_migration_handover.py
"""

import json
import sys
import tempfile
from pathlib import Path

from github_backend_transport import FakeTransport
from github_backend_fixtures import (
    AUTH, REPO, make_checker, make_github_project, make_local_project,
    run_theme,
)

import mgs_github  # noqa: E402
import mgs_records  # noqa: E402

FAILURES, check = make_checker()


def test_switch_local_to_github() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = make_local_project(Path(tmp))
        fake = FakeTransport()
        # 1) 迁移清单:映射 + 保留方案 + 需确认项
        plan = mgs_github.plan_backend_switch(root, target="github-issues",
                                              repo=REPO, transport=fake)
        identities = [item["identity"] for item in plan["tasks"]]
        check(identities == ["01-alpha", "02-beta"],
              f"迁移映射应覆盖既有任务且身份不变,实际 {identities}")
        check(plan["tasks"][0]["source_ref"].startswith("local:")
              and plan["tasks"][0]["target_ref"].startswith("github:"),
              f"映射应表达来源与去向,实际 {plan['tasks'][0]}")
        check(any("保留" in item or "历史" in item for item in plan["retention"]),
              "保留清单必须表达旧记录保留为历史")
        check(any("唯一" in c or "当前来源" in c for c in plan["confirmations"]),
              "确认项必须包含唯一当前来源")
        check(any("授权" in c for c in plan["confirmations"]),
              "确认项必须包含远端写入授权确认")
        plan_path = Path(tmp) / "switch-plan.json"
        plan_path.write_text(json.dumps(plan, ensure_ascii=False), encoding="utf-8")
        # 2) apply 前置闸门:CONFIG 尚未记录目标仓库写授权 → 拒绝(不自我授权)
        try:
            mgs_github.apply_backend_switch(plan_path, confirmed=True,
                                            emit_dir=Path(tmp) / "emit0",
                                            project_root=root, transport=fake)
        except mgs_github.GithubRecordsError as exc:
            check("issues-write" in str(exc) and "授权" in str(exc),
                  f"未记录授权时 apply 应拒绝并说明补记方式:{exc}")
        else:
            check(False, "CONFIG 未记录目标仓库 issues-write 授权时 apply 必须拒绝")
        # 3) 确认的应用步骤把授权记入 CONFIG(经确认清单),再执行 apply
        config_path = root / "docs" / "mygamestudio" / "CONFIG.md"
        config_path.write_text(config_path.read_text(encoding="utf-8").replace(
            "- 外部连接引用及已确认操作范围:无",
            "- 外部连接引用及已确认操作范围:"
            + AUTH + "(迁移清单确认)"), encoding="utf-8")
        emit = Path(tmp) / "emit"
        result = mgs_github.apply_backend_switch(plan_path, confirmed=True,
                                                 emit_dir=emit,
                                                 project_root=root,
                                                 transport=fake)
        check(result["created"] == 2, f"应在远端创建两个任务,实际 {result}")
        # 用切换后 CONFIG(emit 副本)经统一接口回读远端,身份保持不变
        switched = mgs_records.load_config(emit, "CONFIG.md")
        check(switched["backend"] == "github-issues"
              and switched["repo"]["repo"] == "issue-accept",
              "emit 的 CONFIG 应可作为 github 后端配置被统一接口读取")
        remote = mgs_github.GithubBackend(switched, fake).fetch_tasks()["tasks"]
        remote_ids = sorted(t["identity"] for t in remote)
        check(remote_ids == ["01-alpha", "02-beta"],
              f"远端应有两个同身份任务,实际 {remote_ids}")
        deps = {t["identity"]: t["request"].get("依赖") for t in remote}
        check("01-alpha" in deps.get("02-beta", ""),
              f"依赖关系应随迁移保留,实际 {deps}")
        # 应用后本地 CONFIG 仍指向本地(未经受控通道/确认写入不改项目文件)
        config_text = (root / "docs/mygamestudio/CONFIG.md").read_text(encoding="utf-8")
        check("- 后端:local-markdown" in config_text,
              "apply 不得直接改写项目 CONFIG(经确认的应用步骤负责更新唯一来源)")
        check((root / "docs/mygamestudio/work/01-alpha/task.md").is_file(),
              "旧记录保留为历史,不删除")
        emitted = (emit / "CONFIG.md").read_text(encoding="utf-8")
        check("- 后端:github-issues" in emitted and REPO in emitted,
              "应产出切换后的 CONFIG 内容(唯一当前来源指向远端)")
        check("docs/mygamestudio/work" in emitted and "只读历史" in emitted,
              "新 CONFIG 应把旧位置标注为只读历史(不形成两套可改账本)")
        mapping = json.loads((emit / "identity-map.json").read_text(encoding="utf-8"))
        check(mapping["01-alpha"]["github_issue"] == 1,
              f"身份映射应保留(本地身份 → Issue 号),实际 {mapping}")


def test_switch_github_to_local_consistency() -> None:
    """S3:GitHub→本地迁移的计划目标、本地文件落点、CONFIG 任务根与返回
    产出目录四者一致;统一接口能读到迁移后的任务。"""

    with tempfile.TemporaryDirectory() as tmp:
        base = Path(tmp)
        root = make_github_project(base / "project")
        fake = FakeTransport()
        fake.seed_issue("01-alpha", "甲任务")
        plan = mgs_github.plan_backend_switch(root, target="local-markdown",
                                              transport=fake)
        check(plan["repo"] == "docs/mygamestudio/work",
              f"迁移清单目标位置应为本地任务根,实际 {plan.get('repo')}")
        plan_path = base / "plan.json"
        plan_path.write_text(json.dumps(plan, ensure_ascii=False), encoding="utf-8")
        outcome = mgs_github.apply_backend_switch(
            plan_path, confirmed=True, emit_dir=base / "emit",
            project_root=root, transport=fake)
        check(outcome["created"] == 1, f"应迁移一个任务,实际 {outcome}")
        check(Path(outcome["emit_dir"]).is_dir(),
              f"返回的产出目录必须实际存在,实际 {outcome.get('emit_dir')}")
        config = mgs_records.load_config(base / "emit", "CONFIG.md")
        check(config["backend"] == "local-markdown"
              and config["task_root"] == "docs/mygamestudio/work",
              f"新 CONFIG 后端与任务根应为本地任务根,实际 "
              f"{config.get('backend')}/{config.get('task_root')}")
        tasks = mgs_records.list_tasks(base / "emit", "CONFIG.md")
        check([t["identity"] for t in tasks] == ["01-alpha"],
              f"统一接口应能读取迁移后的任务,实际 {tasks}")
        check((base / "emit/docs/mygamestudio/work/01-alpha/task.md").is_file(),
              "本地任务文件应落在 CONFIG 声明的任务根下")


def test_handover_baseline_check() -> None:
    """远端交接核对基线引用可达:未发布本地资料不得宣称远端已可访问。"""

    with tempfile.TemporaryDirectory() as tmp:
        root = make_github_project(Path(tmp))
        fake = FakeTransport()
        fake.seed_issue("01-alpha", "甲任务",
                        request={"输入与基线": "GAME_DESIGN v1"})
        report = mgs_github.handover_baseline_check(root, transport=fake)
        docs = {entry["path"]: entry for entry in report["docs"]}
        design = docs.get("docs/mygamestudio/GAME_DESIGN.md", {})
        check(design.get("remote_reachable") is False,
              "无已发布引用的本地基线应判远端不可达")
        check("不可访问" in design.get("note", ""),
              "应声明不得宣称未发布本地资料已可远端访问")
        check(report["ok"] is False, "存在不可达基线引用时交接检查不应 ok")
        # CONFIG 记录了已发布引用 → 经实际检查通过才判可达;三份都检查通过才 ok
        config_path = root / "docs/mygamestudio/CONFIG.md"
        config_path.write_text(config_path.read_text(encoding="utf-8").replace(
            "外部连接引用及已确认操作范围:" + AUTH,
            "外部连接引用及已确认操作范围:" + AUTH
            + ";已发布基线引用:GAME_DESIGN.md=https://example.invalid/design@v1,"
            "PROJECT.md=https://example.invalid/goal@v1,"
            "TECH_DESIGN.md=https://example.invalid/tech@v1"),
            encoding="utf-8")
        fake.remote_refs = {
            "https://example.invalid/design": 200,
            "https://example.invalid/goal": 200,
            "https://example.invalid/tech": 200,
        }
        report = mgs_github.handover_baseline_check(root, transport=fake)
        docs = {entry["path"]: entry for entry in report["docs"]}
        design = docs.get("docs/mygamestudio/GAME_DESIGN.md", {})
        check(design.get("remote_reachable") is True,
              "记录了已发布引用且实际检查通过的基线应判可达")
        check(report["ok"] is True, "全部基线经检查可达时交接检查 ok")


def test_handover_reachability_requires_executed_check() -> None:
    """S4:可达性结论只能来自实际执行的检查——完全离线时不输出任何
    「远端可达」;引用存在不等于检查通过;实际检查 404 亦不可达。"""

    with tempfile.TemporaryDirectory() as tmp:
        root = make_github_project(Path(tmp))
        config_path = root / "docs/mygamestudio/CONFIG.md"
        config_path.write_text(config_path.read_text(encoding="utf-8") + "\n"
            "已发布基线引用:GAME_DESIGN.md=https://example.invalid/design,"
            "PROJECT.md=https://example.invalid/goal,"
            "TECH_DESIGN.md=https://example.invalid/tech\n", encoding="utf-8")
        offline = FakeTransport()
        offline.offline()
        report = mgs_github.handover_baseline_check(root, transport=offline)
        check(all(doc["remote_reachable"] is False for doc in report["docs"]),
              f"完全离线时不得输出任何远端可达,实际 "
              f"{[d['remote_reachable'] for d in report['docs']]}")
        check(report["ok"] is False, "离线时交接核对不应整体通过")
        check(all("未验证" in doc.get("note", "") or "不可达" in doc.get("note", "")
                  for doc in report["docs"]),
              "未完成检查时应明确报告未验证/不可达")
        check(len(offline.calls) == 3,
              f"每份带引用的基线都应实际发起检查,实际 {len(offline.calls)} 次调用")
        check(offline.auth_flags == [False, False, False],
              f"可达探测不得携带凭据(auth=False),实际 {offline.auth_flags}")
        # 在线但引用地址实际 404 → 检查执行了,结论是不可达
        online = FakeTransport()
        report = mgs_github.handover_baseline_check(root, transport=online)
        check(all(doc["remote_reachable"] is False for doc in report["docs"])
              and report["ok"] is False,
              f"引用地址实际 404 时不得判可达,实际 "
              f"{[d['remote_reachable'] for d in report['docs']]}")
        # 无检查通道(transport=None)→ 引用存在也不得宣称可达
        report = mgs_github.handover_baseline_check(root, transport=None)
        check(all(doc["remote_reachable"] is False for doc in report["docs"]),
              "无检查通道时不得以引用存在宣称可达")


def test_reachability_probe_carries_no_credentials() -> None:
    """S4/Spec 复查:可达探测访问第三方引用地址不得携带 API 凭据;
    正常 API 调用默认仍携带凭据。"""

    captured: dict = {}

    class FakeResponse:
        status = 200

        def read(self):
            return b"{}"

        def __enter__(self):
            return self

        def __exit__(self, *exc):
            return False

    def fake_urlopen(req, timeout=None):
        captured["headers"] = dict(req.headers)
        return FakeResponse()

    original = mgs_github.urlopen
    mgs_github.urlopen = fake_urlopen
    try:
        transport = mgs_github.UrllibTransport("https://api.example", "secret-token")
        status, _ = transport.request("GET", "https://third.example.invalid/doc",
                                      auth=False)
        check(status == 200, f"探测应返回应答状态,实际 {status}")
        check("Authorization" not in captured.get("headers", {}),
              f"可达探测不得携带 Authorization,实际头 {captured.get('headers')}")
        transport.request("GET", "/repos/o/r/issues")  # 默认仍带凭据
        check(captured["headers"].get("Authorization") == "Bearer secret-token",
              "正常 API 调用默认仍携带凭据(auth 语义不变)")
    finally:
        mgs_github.urlopen = original

TESTS = (
    test_switch_local_to_github,
    test_switch_github_to_local_consistency,
    test_handover_baseline_check,
    test_handover_reachability_requires_executed_check,
    test_reachability_probe_carries_no_credentials,
)

if __name__ == "__main__":
    sys.exit(run_theme("后端切换迁移与交接基线可达", TESTS, FAILURES))

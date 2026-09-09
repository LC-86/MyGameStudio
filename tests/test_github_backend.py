#!/usr/bin/env python3
"""GitHub Issues 任务后端的确定性检查(任务票 17)。

接缝说明:本脚本覆盖 mgs_github(GitHub Issues 后端适配器)与
mgs_records 对 github-issues 后端分发的公开接缝——仓库坐标与授权范围
解析、拉取/读取/依赖/可开工/回读核验(经可注入的替身传输层,不访问
真实 GitHub)、创建防重与超时回读、安排更新、结果追加、关系与分流、
关闭语义、离线缓存与未发布草稿、后端切换迁移与交接基线可达检查。
真实远端写入未在本环境授权,本脚本全部使用本地替身;真实远端验收
保留待办(见任务票 17 Comments)。

用法:python3 tests/test_github_backend.py
"""

import json
import re
import subprocess
import sys
import tempfile
import time
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "plugin" / "records"))

import mgs_records  # noqa: E402
import mgs_github  # noqa: E402

CLI = REPO_ROOT / "plugin" / "records" / "mgs_records.py"

FAILURES: list[str] = []


def check(condition: bool, message: str) -> None:
    if not condition:
        FAILURES.append(message)


FIVE_LABELS = ("needs-triage", "needs-info", "ready-for-agent",
               "ready-for-human", "wontfix")

CONFIG_TEMPLATE = """# 测试项目:协作配置(GitHub Issues 后端)

维护责任:制作统筹。配置版本:v1。采用依据:测试夹具。

## 任务来源

- 后端:github-issues
- 当前位置:{repo}
- 任务读取规则:GitHub Issues 后端约定(Issue 正文承载任务说明,评论承载结果)
- 外部连接引用及已确认操作范围:{external}

## 标签映射

| 语义 | 项目标签 |
| --- | --- |
| needs-triage | triage |
| needs-info | info |
| ready-for-agent | agent-ready |
| ready-for-human | human-ready |
| wontfix | wont-do |

## 文档映射

| 内容 | 当前权威位置 | 维护角色 |
| --- | --- | --- |
| 项目目标与范围 | docs/mygamestudio/PROJECT.md | 制作统筹 |
| 游戏需求与设计 | docs/mygamestudio/GAME_DESIGN.md | 方案设计 |
| 技术设计 | docs/mygamestudio/TECH_DESIGN.md | 制作实现 |
| 术语、ADR 与历史 | docs/mygamestudio/records/(暂空) | 对应专业角色 |

## 执行条件

- 工程、原型、资源与构建入口:src/
- 可用能力及已验证执行边界:文件读写
- 尚未就绪的能力及影响:无
"""

REPO = "github.com/mygamestudio/issue-accept"
AUTH = (f"{REPO}:issues-write(2026-09-08 开发者授权;仅测试仓库;"
        "范围:任务与结果读写)")


def make_github_project(root: Path, *, repo: str = REPO,
                        external: str = AUTH) -> Path:
    docs = root / "docs" / "mygamestudio"
    docs.mkdir(parents=True)
    (docs / "CONFIG.md").write_text(
        CONFIG_TEMPLATE.format(repo=repo, external=external), encoding="utf-8")
    for name in ("PROJECT.md", "GAME_DESIGN.md", "TECH_DESIGN.md"):
        (docs / name).write_text(f"# {name}\n\n测试内容\n", encoding="utf-8")
    return root


# ---------- Slice A:仓库坐标与授权范围解析 ----------

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


# ---------- 替身传输层(不访问真实 GitHub) ----------

class FakeTransport:
    """GitHub REST 最小子集的本地替身:状态机 + 故障注入。

    故障注入:
    - fail(method, needle, kind):匹配的调用抛 TransportError;
    - drop(method, needle):**执行状态变更后**抛 timeout(模拟「已创建但
      响应丢失」——超时后结果不确定,须回读确认);
    - offline():此后全部调用抛 offline(模拟断连)。
    """

    def __init__(self, *, sub_issues_supported: bool = True) -> None:
        self.issues: list[dict] = []
        self.comments: dict[int, list[dict]] = {}
        self.sub_issues: dict[int, list[int]] = {}
        self.repo_labels: list[str] = ["triage", "info", "agent-ready",
                                       "human-ready", "wont-do"]
        self.sub_issues_supported = sub_issues_supported
        self.calls: list[tuple[str, str, dict | None]] = []
        self._fail: list[tuple[str, str, str]] = []   # (method, needle, kind)
        self._drop: list[tuple[str, str]] = []        # (method, needle)
        self._offline = False

    # ----- 注入 -----
    def fail(self, method: str, needle: str, kind: str) -> None:
        self._fail.append((method, needle, kind))

    def drop(self, method: str, needle: str) -> None:
        self._drop.append((method, needle))

    def offline(self) -> None:
        self._offline = True

    def _guard(self, method: str, path: str) -> None:
        if self._offline:
            raise mgs_github.TransportError("offline", "connection refused (stand-in)")
        for fail_method, needle, kind in self._fail:
            if fail_method == method and needle in path:
                raise mgs_github.TransportError(kind, f"injected {kind} at {path}")

    def _dropped(self, method: str, path: str) -> bool:
        return any(fail_method == method and needle in path
                   for fail_method, needle in self._drop)

    # ----- 种子 -----
    def seed_issue(self, identity: str, title: str, *, triage: str = "ready-for-agent",
                   progress: str = "待执行", project_label: str = "agent-ready",
                   request: dict | None = None, deps: str = "无",
                   state: str = "open", state_reason: str | None = None) -> dict:
        request = dict(request or {
            "当前目标": "演示目标", "输入与基线": "GAME_DESIGN v1",
            "本次交付": "示例交付", "允许修改范围": "src/**",
            "所需能力": "文件读写", "完成标准": "示例标准",
            "执行责任": "Agent(制作实现)", "验收方式": "代码级检查"})
        request["依赖"] = deps
        body = mgs_github.build_task_body(title, identity, triage, progress, request)
        issue = {"number": len(self.issues) + 1, "id": 1000 + len(self.issues) + 1,
                 "title": title, "body": body,
                 "labels": ([{"name": project_label}] if project_label else []),
                 "state": state, "state_reason": state_reason,
                 "html_url": f"https://example.invalid/i/{len(self.issues) + 1}"}
        self.issues.append(issue)
        self.comments[issue["number"]] = []
        return issue

    # ----- GitHub REST 子集 -----
    def request(self, method: str, path: str, body: dict | None = None):
        self.calls.append((method, path, body))  # 故障注入的调用也已真实发出
        self._guard(method, path)
        path = path.split("?", 1)[0]  # 查询串不参与路由
        base = f"/repos/mygamestudio/issue-accept"
        if method == "GET" and path == base + "/issues":
            return 200, list(self.issues)
        if method == "GET" and path.startswith(base + "/labels"):
            return 200, [{"name": name} for name in self.repo_labels]
        match = re.match(rf"{base}/issues/(\d+)(/.*)?$", path)
        number = int(match.group(1)) if match else None
        if match and match.group(2) == "/comments" and method == "GET":
            return 200, list(self.comments.get(number, []))
        if match and match.group(2) == "/comments" and method == "POST":
            comment = {"id": 5000 + number * 100 + len(self.comments[number]),
                       "body": body["body"], "created_at": "2026-09-08T12:00:00Z"}
            self.comments[number].append(comment)
            if self._dropped(method, path):
                raise mgs_github.TransportError("timeout", "injected drop (comment)")
            return 201, comment
        if match and match.group(2) == "/sub_issues":
            if not self.sub_issues_supported:
                return 404, {"message": "Sub-issues API not available (stand-in)"}
            if method == "GET":
                subs = self.sub_issues.get(number, [])
                return 200, [self.issues[i - 1] for i in subs]
            if method == "POST":
                self.sub_issues.setdefault(number, []).append(body["sub_issue_id"])
                return 201, {}
        if match and not match.group(2):
            issue = self.issues[number - 1]
            if method == "GET":
                return 200, issue
            if method == "PATCH":
                for key in ("title", "body", "state", "state_reason"):
                    if key in body:
                        issue[key] = body[key]
                if "labels" in body:
                    issue["labels"] = [{"name": name} for name in body["labels"]]
                return 200, issue
        if method == "POST" and path == base + "/issues":
            issue = {"number": len(self.issues) + 1,
                     "id": 1000 + len(self.issues) + 1,
                     "title": body["title"], "body": body["body"],
                     "labels": [{"name": name} for name in body.get("labels", [])],
                     "state": "open", "state_reason": None,
                     "html_url": f"https://example.invalid/i/{len(self.issues) + 1}"}
            self.issues.append(issue)
            self.comments[issue["number"]] = []
            if self._dropped(method, path):
                raise mgs_github.TransportError("timeout", "injected drop (create)")
            return 201, issue
        if method == "GET" and path.startswith("/repos/") and path.endswith("/issues"):
            return 200, list(self.issues)
        return 404, {"message": f"stand-in has no {method} {path}"}


def backend_for(root: Path, transport: FakeTransport, cache: Path | None = None):
    return mgs_records.github_backend(root, transport=transport, cache_dir=cache)


# ---------- Slice B:拉取 / 离线缓存 / 依赖 / 可开工 ----------

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


# ---------- Slice C:写操作(授权闸门 / 防重 / 超时回读 / 回读验证) ----------

def test_write_requires_authorization() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = make_github_project(Path(tmp), external="无(仅本地引用,未授权远端写入)")
        fake = FakeTransport()
        backend = backend_for(root, fake)
        try:
            backend.create_task("01-alpha", "甲任务", {})
        except mgs_github.GithubRecordsError as exc:
            message = str(exc)
            check("不等于批准远端写入" in message or "授权" in message,
                  f"未授权写操作应说明授权缺失:{message}")
        else:
            check(False, "CONFIG 无 issues-write 授权时写操作必须拒绝")
        check(not any(c[0] == "POST" for c in fake.calls),
              "未授权时不得发出任何远端写请求")
    with tempfile.TemporaryDirectory() as tmp:
        # 授权了别的仓库,目标仓库不在范围 → 同样拒绝
        root = make_github_project(
            Path(tmp), external="github.com/other/repo:issues-write(与目标仓库不符)")
        fake = FakeTransport()
        backend = backend_for(root, fake)
        try:
            backend.create_task("01-alpha", "甲任务", {})
        except mgs_github.GithubRecordsError:
            check(True, "")
        else:
            check(False, "授权仓库与目标仓库不一致时必须拒绝")
        check(not any(c[0] == "POST" for c in fake.calls),
              "仓库范围外的授权不得产生远端写请求")


def test_create_and_duplicate_protection() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = make_github_project(Path(tmp))
        fake = FakeTransport()
        backend = backend_for(root, fake)
        result = backend.create_task(
            "01-alpha", "甲任务",
            {"当前目标": "演示目标", "完成标准": "示例标准", "执行责任": "Agent(制作实现)"},
            triage="ready-for-agent")
        check(result["created"] is True and result["issue_number"] == 1,
              f"首次创建应成功并回报 Issue 号,实际 {result}")
        check(result["readback"]["identity"] == "01-alpha", "创建后必须回读核对身份")
        # 重复创建同一身份:收养既有 Issue,不新建
        result = backend.create_task("01-alpha", "甲任务", {})
        check(result["created"] is False and result.get("adopted") is True,
              f"重复创建应收养既有任务,实际 {result}")
        posts = [c for c in fake.calls if c[0] == "POST" and c[1].endswith("/issues")]
        check(len(posts) == 1, f"重复创建不得发出第二次 POST,实际 {len(posts)} 次")


def test_create_timeout_reads_back_before_retry() -> None:
    """超时/响应丢失:先回读(已落地则收养),未落地才重试一次;如实上报尝试。"""

    with tempfile.TemporaryDirectory() as tmp:
        root = make_github_project(Path(tmp))
        fake = FakeTransport()
        fake.drop("POST", "/issues")  # 第一次 POST 已生效但响应丢失
        backend = backend_for(root, fake)
        result = backend.create_task("01-alpha", "甲任务", {})
        check(result["created"] is False and result.get("adopted") is True,
              f"超时后回读发现已创建应收养,不重复创建,实际 {result}")
        check(result["attempts"][0].get("outcome") == "timeout",
              f"尝试历史应如实记录超时,实际 {result.get('attempts')}")
        check(result["duplicate_avoided"] is True, "应标记避免了重复创建")
        check(len([i for i in fake.issues
                   if "任务身份:01-alpha" in i["body"]]) == 1,
              "远端必须只有一个 01-alpha")
    with tempfile.TemporaryDirectory() as tmp:
        root = make_github_project(Path(tmp))
        fake = FakeTransport()
        fake.fail("POST", "/issues", "timeout")  # 两次都超时且未落地
        backend = backend_for(root, fake)
        try:
            backend.create_task("01-alpha", "甲任务", {})
        except mgs_github.GithubRecordsError as exc:
            check("未确认" in str(exc) or "失败" in str(exc),
                  f"回读+重试后仍未落地应如实报失败:{exc}")
        else:
            check(False, "回读与重试都未落地时应报错,不得虚报成功")
        posts = [c for c in fake.calls if c[0] == "POST" and c[1].endswith("/issues")]
        check(len(posts) == 2, f"重试恰好一次(共 2 次 POST),实际 {len(posts)}")


def test_update_task_fields_and_version_check() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = make_github_project(Path(tmp))
        fake = FakeTransport()
        fake.seed_issue("01-alpha", "甲任务")
        backend = backend_for(root, fake)
        result = backend.update_task("01-alpha", {"进度": "执行中",
                                                  "当前目标": "新目标"})
        check(result["readback"]["progress"] == "执行中",
              f"安排更新应回读新进度,实际 {result['readback'].get('progress')}")
        check(result["readback"]["request"]["当前目标"] == "新目标",
              "工作请求字段更新应可回读")
        # 版本校验:expected_body_sha256 与远端当前正文不符 → 拒绝(不覆盖他人改动)
        try:
            backend.update_task("01-alpha", {"进度": "已完成"},
                                expected_body_sha256="0" * 64)
        except mgs_github.GithubRecordsError as exc:
            check("已被他人修改" in str(exc) or "不符" in str(exc),
                  f"版本不符应拒绝覆盖:{exc}")
        else:
            check(False, "expected_body_sha256 不符时应拒绝更新")
        task = mgs_records.read_task(root, "01-alpha", transport=fake)
        check(task["progress"] == "执行中", "被拒更新不得改变远端内容")


def test_set_triage_and_append_result() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = make_github_project(Path(tmp))
        fake = FakeTransport()
        fake.seed_issue("01-alpha", "甲任务")
        backend = backend_for(root, fake)
        result = backend.set_triage("01-alpha", "needs-info")
        check(result["readback"]["triage"] == "needs-info",
              f"分流应更新并回读,实际 {result['readback'].get('triage')}")
        labels_now = [l["name"] for l in fake.issues[0]["labels"]]
        check(labels_now == ["info"], f"标签应换成映射后的 info,实际 {labels_now}")
        try:
            backend.set_triage("01-alpha", "done")
        except mgs_github.GithubRecordsError:
            check(True, "")
        else:
            check(False, "五类之外的分流值应拒绝")
        result = backend.append_result("01-alpha", "已交付骨架与检查输出。")
        check(result["comment_id"] is not None and result["published"] is True,
              f"结果追加应发布评论并回报,实际 {result}")
        task = mgs_records.read_task(root, "01-alpha", transport=fake)
        check(len(task["results"]) == 1
              and task["results"][0]["excerpt"].startswith("任务:01-alpha"),
              f"评论结果应带任务身份前缀并可回读,实际 {task['results']}")
        check(f"#issuecomment-{result['comment_id']}" in task["result_index_text"],
              "结果索引应引用该评论(评论与索引一致)")


def test_relations_native_and_fallback() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = make_github_project(Path(tmp))
        fake = FakeTransport(sub_issues_supported=True)
        fake.seed_issue("01-alpha", "甲任务")
        fake.seed_issue("02-beta", "乙任务")
        fake.seed_issue("03-plan", "拆单管理", project_label=None,
                        triage="ready-for-agent", progress="执行中")
        backend = backend_for(root, fake)
        result = backend.set_relations("02-beta", ["01-alpha"])
        check(result["readback"]["request"]["依赖"] == "#1 01-alpha",
              f"依赖应写成明确可解析引用(#Issue号 身份),实际 "
              f"{result['readback']['request'].get('依赖')}")
        graph = mgs_records.task_dependencies(root, transport=fake)
        check(graph["edges"].get("02-beta") == ["01-alpha"],
              "引用写法应能被 deps 解析回身份")
        # 原生父子关系可用:把 02 挂为 03 的子 Issue(原生 API 按 issue id 挂)
        result = backend.set_parent("02-beta", "03-plan")
        check(result["mode"] == "native-sub-issues"
              and fake.sub_issues.get(3) == [1002],
              f"原生 sub-issues 可用时应实际使用(按 issue id 挂接),实际 "
              f"{result.get('mode')}/{fake.sub_issues}")
    with tempfile.TemporaryDirectory() as tmp:
        root = make_github_project(Path(tmp))
        fake = FakeTransport(sub_issues_supported=False)  # 后端不提供原生关系
        fake.seed_issue("01-alpha", "甲任务")
        fake.seed_issue("02-beta", "乙任务")
        fake.seed_issue("03-plan", "拆单管理", project_label=None,
                        triage="ready-for-agent", progress="执行中")
        backend = backend_for(root, fake)
        result = backend.set_parent("02-beta", "03-plan")
        check(result["mode"] == "body-reference",
              f"原生关系不可用时应回退正文引用,实际 {result}")
        check("父任务:#3 03-plan" in result["readback"]["body"],
              "正文引用应明确可解析(#Issue号 身份)")


def test_close_reasons() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = make_github_project(Path(tmp))
        fake = FakeTransport()
        backend = backend_for(root, fake)
        for identity, title in (("01-done", "完成任务"), ("02-drop", "不再执行"),
                                ("03-covered", "成果覆盖")):
            backend.create_task(identity, title, {"当前目标": "演示",
                                                  "完成标准": "示例",
                                                  "执行责任": "Agent(制作实现)"})
        result = backend.close_task("01-done", "完成")
        check(result["readback"]["state"] == "closed"
              and result["readback"]["state_reason"] == "completed",
              f"完成应关闭为 completed,实际 {result['readback']}")
        check(result["readback"]["progress"] == "已完成", "正文进度应同步为已完成")
        check("不自动等于验证通过" in result["note"],
              "关闭结果必须声明不自动等于验证通过")
        result = backend.close_task("02-drop", "不再执行")
        check(result["readback"]["state_reason"] == "not_planned",
              f"不再执行应关闭为 not_planned,实际 {result['readback']}")
        result = backend.close_task("03-covered", "已有成果覆盖")
        check(result["readback"]["state_reason"] == "completed"
              and "已有成果覆盖" in result["readback"]["progress"],
              f"已有成果覆盖应表达在进度与说明中,实际 {result['readback']}")
        try:
            backend.close_task("01-done", "随便关")
        except mgs_github.GithubRecordsError:
            check(True, "")
        else:
            check(False, "关闭原因必须限定三类,不得含糊关闭")


# ---------- Slice D:离线草稿 / 后端切换迁移 / 交接基线可达 ----------

LOCAL_TASK = """# {title}

任务身份:{identity}。当前分流:{triage}。进度:{progress}。

## 工作请求

- 当前目标:{goal}
- 输入与基线:GAME_DESIGN v1
- 本次交付:示例交付
- 允许修改范围:src/**
- 所需能力:文件读写
- 完成标准:示例标准
- 执行责任:Agent(制作实现)
- 验收方式:代码级检查
- 依赖:{deps}

## 结果索引

{index}

## 状态变化

2026-09-08 测试夹具初始化。
"""


def make_local_project(root: Path) -> Path:
    docs = root / "docs" / "mygamestudio"
    docs.mkdir(parents=True)
    # 本地后端 CONFIG(标签映射沿用同一套项目标签,便于切换后身份/标签语义不变)
    (docs / "CONFIG.md").write_text(
        CONFIG_TEMPLATE.format(repo="REPLACED", external="无").replace(
            "- 后端:github-issues", "- 后端:local-markdown").replace(
            "- 当前位置:REPLACED",
            "- 当前位置:docs/mygamestudio/work/"
            "(每任务一目录,task.md 为工作请求与状态)"), encoding="utf-8")
    for name in ("PROJECT.md", "GAME_DESIGN.md", "TECH_DESIGN.md"):
        (docs / name).write_text(f"# {name}\n\n基线版本:v1。\n", encoding="utf-8")
    work = docs / "work"
    for identity, title, deps in (("01-alpha", "甲任务", "无"),
                                  ("02-beta", "乙任务", "01-alpha")):
        task_dir = work / identity
        task_dir.mkdir(parents=True)
        (task_dir / "task.md").write_text(
            LOCAL_TASK.format(title=title, identity=identity,
                              triage="ready-for-agent", progress="待执行",
                              goal="演示目标", deps=deps, index="(暂无)"),
            encoding="utf-8")
    return root


def test_offline_write_draft_and_publish() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = make_github_project(Path(tmp))
        cache = Path(tmp) / "gh-cache"
        fake = FakeTransport()
        backend = backend_for(root, fake, cache)
        fake.offline()
        result = backend.create_task("01-alpha", "甲任务", {"当前目标": "演示"})
        check(result["published"] is False and result["status"] == "未发布草稿",
              f"离线创建应保存未发布草稿,实际 {result}")
        check(Path(result["draft"]).is_file(), "草稿文件应实际落盘")
        check("不静默切换本地后端" in result["note"], "草稿说明必须声明不静默切本地")
        draft = json.loads(Path(result["draft"]).read_text(encoding="utf-8"))
        check(draft["status"] == "未发布草稿" and draft["repo"] == REPO,
              f"草稿应标明状态与目标仓库,实际 {draft}")
        check(mgs_github.GithubBackend.__name__ and draft["op"] == "create_task",
              "草稿应记录原始操作便于重放")
        # 远端恢复后发布:草稿重放成功并标记;远端只有一个 01-alpha
        fake._offline = False
        published = backend.publish_drafts()
        check(published["published_count"] == 1,
              f"草稿应发布成功,实际 {published}")
        ids = [t["identity"] for t in mgs_records.list_tasks(root, transport=fake)]
        check(ids == ["01-alpha"], f"发布后远端应恰有一个任务,实际 {ids}")
        check(not list((cache / "drafts").glob("*.json")),
              "已发布草稿应移出待发布目录")


def test_offline_write_without_cache_dir_refuses() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = make_github_project(Path(tmp))
        fake = FakeTransport()
        fake.offline()
        backend = backend_for(root, fake)  # 无缓存目录
        try:
            backend.create_task("01-alpha", "甲任务", {})
        except mgs_github.GithubRecordsError as exc:
            check("草稿目录" in str(exc) or "cache" in str(exc),
                  f"无草稿目录时应说明且不丢弃请求:{exc}")
        else:
            check(False, "无草稿目录时不得静默丢弃写入请求")


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
        # CONFIG 记录了已发布引用 → 该基线判可达(引用形式);三份都补齐才 ok
        config_path = root / "docs" / "mygamestudio" / "CONFIG.md"
        config_path.write_text(config_path.read_text(encoding="utf-8").replace(
            "外部连接引用及已确认操作范围:" + AUTH,
            "外部连接引用及已确认操作范围:" + AUTH
            + ";已发布基线引用:GAME_DESIGN.md=https://example.invalid/design@v1,"
            "PROJECT.md=https://example.invalid/goal@v1,"
            "TECH_DESIGN.md=https://example.invalid/tech@v1"),
            encoding="utf-8")
        report = mgs_github.handover_baseline_check(root, transport=fake)
        docs = {entry["path"]: entry for entry in report["docs"]}
        design = docs.get("docs/mygamestudio/GAME_DESIGN.md", {})
        check(design.get("remote_reachable") is True,
              "记录了已发布引用的基线应判可达(以引用形式)")
        check(report["ok"] is True, "全部基线可达时交接检查 ok")


# ---------- Slice E:统一接口 CLI(github 后端写操作子命令) ----------

def run_cli(*args: str, env: dict | None = None) -> subprocess.CompletedProcess:
    import os
    full_env = {**os.environ.copy(), **(env or {})}
    return subprocess.run([sys.executable, "-B", str(CLI), *args],
                          capture_output=True, text=True, env=full_env)


class _StandinServer:
    """把 FakeTransport 挂到进程内 HTTP 端点(真实 UrllibTransport 通路)。"""

    def __init__(self, fake: FakeTransport) -> None:
        from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

        outer = self

        class Handler(BaseHTTPRequestHandler):
            def log_message(self, *args):  # noqa: A003 - 静默测试服务器
                pass

            def _handle(self, method: str) -> None:
                length = int(self.headers.get("Content-Length") or 0)
                raw = self.rfile.read(length) if length else b""
                body = json.loads(raw) if raw else None
                try:
                    status, data = fake.request(method, self.path, body)
                except mgs_github.TransportError as exc:
                    self.send_response(599 if exc.kind == "offline" else 598)
                    self.end_headers()
                    return
                payload = json.dumps(data, ensure_ascii=False).encode("utf-8")
                self.send_response(status)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(payload)))
                self.end_headers()
                self.wfile.write(payload)

            def do_GET(self):     # noqa: N802 - http.server 约定
                self._handle("GET")

            def do_POST(self):    # noqa: N802
                self._handle("POST")

            def do_PATCH(self):   # noqa: N802
                self._handle("PATCH")

        outer.server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)

    @property
    def base(self) -> str:
        return f"http://127.0.0.1:{self.server.server_address[1]}"

    def start(self) -> None:
        import threading
        threading.Thread(target=self.server.serve_forever, daemon=True).start()

    def stop(self) -> None:
        self.server.shutdown()


def test_cli_github_write_ops() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = make_github_project(Path(tmp))
        cache = Path(tmp) / "cache"
        fake = FakeTransport()
        server = _StandinServer(fake)
        server.start()
        common = ["--project", str(root), "--api-base", server.base,
                  "--cache-dir", str(cache)]
        try:
            result = run_cli("create", *common, "--identity", "01-alpha",
                             "--title", "甲任务", "--field", "当前目标=演示目标",
                             "--field", "完成标准=示例标准",
                             "--field", "执行责任=Agent(制作实现)",
                             "--triage", "ready-for-agent")
            check(result.returncode == 0,
                  f"CLI create 应成功:{result.stdout[:300]}{result.stderr[:200]}")
            data = json.loads(result.stdout)
            check(data["created"] is True and data["issue_number"] == 1,
                  f"CLI create 应回报创建与 Issue 号,实际 {data}")
            result = run_cli("list", *common)
            check([t["identity"] for t in json.loads(result.stdout)] == ["01-alpha"],
                  "CLI list 应列出远端任务")
            result = run_cli("show", *common, "--task", "01-alpha")
            check(json.loads(result.stdout)["title"] == "甲任务",
                  "CLI show 应回读远端任务")
            result = run_cli("update", *common, "--task", "01-alpha",
                             "--field", "进度=执行中")
            check(json.loads(result.stdout)["readback"]["progress"] == "执行中",
                  "CLI update 应更新进度并回读")
            result = run_cli("append-result", *common, "--task", "01-alpha",
                             "--text", "已交付并自检。")
            check(result.returncode == 0
                  and json.loads(result.stdout)["published"] is True,
                  f"CLI append-result 应发布评论:{result.stdout[:200]}")
            result = run_cli("set-triage", *common, "--task", "01-alpha",
                             "--label", "needs-info")
            check(json.loads(result.stdout)["readback"]["triage"] == "needs-info",
                  "CLI set-triage 应更新分流")
            result = run_cli("set-relations", *common, "--task", "01-alpha",
                             "--dep", "99-missing")
            check(result.returncode != 0,
                  "CLI set-relations 引用不存在任务应报错(不写悬空依赖)")
            result = run_cli("close", *common, "--task", "01-alpha",
                             "--reason", "完成")
            data = json.loads(result.stdout)
            check(data["readback"]["state"] == "closed",
                  "CLI close 应关闭任务并回读")
            # 无授权配置 → 写子命令拒绝
            noauth = make_github_project(Path(tmp) / "noauth",
                                         external="无(未授权)")
            result = run_cli("create", "--project", str(noauth),
                             "--api-base", server.base,
                             "--identity", "01-x", "--title", "x")
            check(result.returncode != 0 and "授权" in result.stdout,
                  f"无授权时 CLI 写操作应拒绝并说明:{result.stdout[:200]}")
        finally:
            server.stop()


def test_cli_local_backend_refuses_write_subcommands() -> None:
    result = run_cli("create", "--project", str(REPO_ROOT / "samples" / "role-scope-demo"),
                     "--identity", "09-x", "--title", "x")
    check(result.returncode != 0 and "mgs-gate" in result.stdout,
          f"本地后端写子命令应指向受控通道:{result.stdout[:200]}")
    result = run_cli("handover", "--project",
                     str(REPO_ROOT / "samples" / "role-scope-demo"))
    check(result.returncode != 0 and "github" in result.stdout,
          f"handover 应限定 github 后端:{result.stdout[:200]}")


def main() -> int:
    for name, func in sorted(globals().items()):
        if name.startswith("test_") and callable(func):
            func()
    if FAILURES:
        print(f"FAIL ({len(FAILURES)} 项):")
        for failure in FAILURES:
            print(f"  - {failure}")
        return 1
    print("OK: GitHub Issues 任务后端检查全部通过")
    return 0


if __name__ == "__main__":
    sys.exit(main())

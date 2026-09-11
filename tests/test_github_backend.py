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

import hashlib
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
        # 交接可达检查用的绝对 URL → 状态码(未登记的绝对 URL 应答 404)
        self.remote_refs: dict[str, int] = {}
        self.auth_flags: list[bool | None] = []  # 每次调用的 auth 参数(凭据核对)
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
    def request(self, method: str, path: str, body: dict | None = None,
                *, auth: bool | None = None):
        self.calls.append((method, path, body))  # 故障注入的调用也已真实发出
        self.auth_flags.append(auth)             # 可达探测应传 auth=False(不带凭据)
        self._guard(method, path)
        path = path.split("?", 1)[0]  # 查询串不参与路由
        # 绝对 URL(交接可达检查;HTTP 替身转发时会带上前导 /)
        if method == "GET" and re.match(r"^/?https?://", path):
            url = path.lstrip("/")
            if url in self.remote_refs:
                return self.remote_refs[url], {}
            return 404, {"message": f"stand-in has no {url}"}
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


def test_cli_github_handover_end_to_end() -> None:
    """票 17 第 7 条真实远端重放发现的缺陷固化:github 后端 CLI handover
    端到端路径崩溃(AttributeError:handover_baselinecheck_item——票 01-fix
    改名漏改 CLI 调用点)。未发布基线时必须输出 JSON 报告并以退出码 1 如实
    回报;崩溃的退出码恰为 1,会伪装成「不可达」结论,故必须锚定 JSON 输出。"""

    with tempfile.TemporaryDirectory() as tmp:
        root = make_github_project(Path(tmp))
        cache = Path(tmp) / "cache"
        fake = FakeTransport()
        server = _StandinServer(fake)
        server.start()
        common = ["--project", str(root), "--api-base", server.base,
                  "--cache-dir", str(cache)]
        try:
            result = run_cli("handover", *common)
            check(result.returncode == 1,
                  f"未发布基线时 handover 应以退出码 1 如实回报:"
                  f"{result.stdout[:200]}{result.stderr[:200]}")
            try:
                report = json.loads(result.stdout)
            except ValueError:
                check(False,
                      f"handover 应输出 JSON 报告而非崩溃(先看 stderr):"
                      f"{result.stderr[-300:]}")
                return
            check(report.get("ok") is False and len(report.get("docs", [])) >= 1,
                  f"handover 报告应含基线文档条目:{str(report)[:200]}")
            check(any("不可访问" in d.get("note", "") and "不得宣称" in d.get("note", "")
                      for d in report["docs"]),
                  "未发布基线应标注远端不可访问且不得宣称已可访问")
        finally:
            server.stop()


# ---------- 审查修复票 01:反例固化(修复前红、修复后绿) ----------

def test_append_result_readback_failure_keeps_uncertain() -> None:
    """S2:评论超时后回读本身失败 ≠ 确认不存在——保留未知状态、停止重发,
    结果如实报告已尝试步骤与不确定结论(不虚报失败也不虚报成功)。"""

    with tempfile.TemporaryDirectory() as tmp:
        root = make_github_project(Path(tmp))
        fake = FakeTransport()
        fake.seed_issue("01-alpha", "甲任务")
        backend = backend_for(root, fake)
        fake.drop("POST", "/comments")           # 首条评论已落地但响应超时
        fake.fail("GET", "/comments", "timeout")  # 回读本身失败
        try:
            outcome = backend.append_result("01-alpha", "交付证据")
        except mgs_github.GithubRecordsError as exc:  # 修复前:重发两次后报错
            outcome = {"raised": str(exc)}
        posts = [c for c in fake.calls if c[0] == "POST" and "/comments" in c[1]]
        check(len(posts) == 1,
              f"回读失败时不得发出第二条创建请求,实际 {len(posts)} 次 POST")
        check(len(fake.comments[1]) == 1,
              f"替身应只有一条评论,实际 {len(fake.comments[1])} 条")
        check(outcome.get("uncertain") is True
              and outcome.get("published") is not True,
              f"结果应保留未知状态且不虚报成功,实际 {outcome}")
        readbacks = [a for a in outcome.get("attempts", [])
                     if a.get("step") == "readback"]
        check(readbacks and readbacks[-1].get("outcome") != "absent",
              f"回读失败不得记作 absent(确认不存在),实际 {outcome.get('attempts')}")


def test_publish_drafts_refuses_cross_repo_draft() -> None:
    """S1:草稿记录的仓库与当前后端仓库不一致时拒绝发布该草稿——不发请求、
    不标记已发布、如实报告;选择新后端不构成旧草稿的迁移授权。"""

    with tempfile.TemporaryDirectory() as tmp:
        base = Path(tmp)
        root = make_github_project(base / "project")
        config = mgs_records.load_config(root)
        old = {**config, "repo": {"host": "github.com", "owner": "old-owner",
                                  "repo": "private-repo"},
               "external": ("github.com/old-owner/private-repo:"
                            "issues-write(已授权旧仓库)")}
        offline = FakeTransport()
        offline.offline()
        previous = mgs_github.GithubBackend(old, offline, base / "shared-cache")
        previous.create_task("09-private", "仅旧仓库的任务", {"当前目标": "旧仓库材料"})
        fake = FakeTransport()
        current = mgs_github.GithubBackend(config, fake, base / "shared-cache")
        outcome = current.publish_drafts()
        writes = [c[1] for c in fake.calls if c[0] == "POST"]
        check(writes == [], f"跨仓库草稿不得发出任何远端写请求,实际 {writes}")
        check(outcome["published_count"] == 0,
              f"跨仓库草稿不得标记已发布,实际 {outcome}")
        check(len(list((base / "shared-cache/drafts").glob("*.json"))) == 1,
              "被拒草稿应原样保留在待发布目录(不移动、不删除)")
        check(any("仓库" in str(r.get("outcome", ""))
                  and "迁移" in str(r.get("outcome", ""))
                  for r in outcome["results"]),
              f"拒绝原因应说明仓库不一致且不构成迁移授权,实际 {outcome['results']}")


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


def test_cli_reverse_migration_real_entry() -> None:
    """S3:CLI 真实入口(子进程 + 真实 UrllibTransport 经本地 HTTP 替身)
    执行一次 GitHub→本地反向迁移,读取通道在 CLI 内建立。"""

    with tempfile.TemporaryDirectory() as tmp:
        base = Path(tmp)
        root = make_github_project(base / "project")
        fake = FakeTransport()
        fake.seed_issue("01-alpha", "甲任务")
        server = _StandinServer(fake)
        server.start()
        try:
            plan_path = base / "plan.json"
            emit = base / "emit"
            result = run_cli("switch-plan", "--project", str(root),
                             "--target", "local-markdown", "--emit", str(plan_path),
                             "--api-base", server.base)
            check(result.returncode == 0,
                  f"CLI switch-plan(反向)应成功:{result.stdout[:300]}"
                  f"{result.stderr[:200]}")
            if result.returncode != 0:
                return
            plan = json.loads(plan_path.read_text(encoding="utf-8"))
            check(plan["repo"] == "docs/mygamestudio/work",
                  f"CLI 迁移清单目标应为本地任务根,实际 {plan.get('repo')}")
            result = run_cli("switch-apply", "--project", str(root),
                             "--plan", str(plan_path), "--emit-dir", str(emit),
                             "--confirmed", "--api-base", server.base)
            check(result.returncode == 0,
                  f"CLI switch-apply(反向)应成功:{result.stdout[:300]}"
                  f"{result.stderr[:200]}")
            outcome = json.loads(result.stdout)
            check(outcome["created"] == 1 and Path(outcome["emit_dir"]).is_dir(),
                  f"CLI 迁移应产出任务且返回目录存在,实际 {outcome}")
            tasks = mgs_records.list_tasks(emit, "CONFIG.md")
            check([t["identity"] for t in tasks] == ["01-alpha"],
                  f"CLI 迁移后统一接口应能读取任务,实际 {tasks}")
        finally:
            server.stop()


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


def test_startable_tasks_reports_cache_metadata() -> None:
    """S5:统一开工接口传递缓存元信息(是否缓存、抓取时间、来源)——
    断网时调用方能区分缓存推断与当前确认。"""

    with tempfile.TemporaryDirectory() as tmp:
        root = make_github_project(Path(tmp))
        cache = Path(tmp) / "cache"
        fake = FakeTransport()
        fake.seed_issue("01-alpha", "甲任务")
        online = mgs_records.startable_tasks(root, transport=fake, cache_dir=cache)
        meta = {key: online.get(key) for key in ("cached", "fetched_at", "source")}
        check(meta["cached"] is False and meta["fetched_at"]
              and meta["source"].get("backend") == "github-issues",
              f"在线开工结果应携带当前确认元信息,实际 {meta}")
        fake.offline()
        offline = mgs_records.startable_tasks(root, transport=fake, cache_dir=cache)
        meta = {key: offline.get(key) for key in ("cached", "fetched_at", "source")}
        check(meta["cached"] is True and meta["fetched_at"]
              and meta["source"].get("backend") == "github-issues",
              f"断网开工结果应携带缓存标记、抓取时间与来源,实际 {meta}")
        check([t["identity"] for t in offline["startable"]] == ["01-alpha"],
              "断网时仍应基于缓存给出可开工集合(并明示缓存状态)")


def test_draft_unique_identity_no_overwrite() -> None:
    """S6:同秒两次不同操作的草稿互不覆盖;每个待发布操作有稳定唯一身份;
    同一操作重复保存保持幂等(不产生重复重放)。"""

    with tempfile.TemporaryDirectory() as tmp:
        root = make_github_project(Path(tmp))
        cache = Path(tmp) / "cache"
        fake = FakeTransport()
        fake.seed_issue("01-alpha", "甲任务")
        backend = backend_for(root, fake, cache)
        backend.fetch_tasks()  # 在线抓取建立缓存(离线草稿路径需要)
        fake.offline()
        real_datetime = mgs_github._dt.datetime

        class FixedDatetime(real_datetime):
            @classmethod
            def now(cls, tz=None):
                return cls(2026, 9, 9, 1, 2, 3, tzinfo=tz)

        mgs_github._dt.datetime = FixedDatetime
        try:
            one = backend.append_result("01-alpha", "证据一")
            two = backend.append_result("01-alpha", "证据二")
            again = backend.append_result("01-alpha", "证据二")
        finally:
            mgs_github._dt.datetime = real_datetime
        check(one["draft"] != two["draft"],
              f"同秒两次不同操作应产生两份独立草稿,实际同路径 {one['draft']}")
        drafts = list((cache / "drafts").glob("*.json"))
        check(len(drafts) == 2,
              f"应恰有两份草稿(同一操作重复保存幂等),实际 {len(drafts)} 份")
        remaining = {json.loads(path.read_text(encoding="utf-8"))
                     ["args"]["result_markdown"] for path in drafts}
        check(remaining == {"证据一", "证据二"},
              f"两份草稿内容都应保留,实际 {remaining}")


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


def test_update_change_note_three_paths() -> None:
    """核验建议 2:安排更新说明三路一致(在线执行/草稿保存/重放),
    重放后不回退默认文案「安排更新」。"""

    with tempfile.TemporaryDirectory() as tmp:
        root = make_github_project(Path(tmp))
        cache = Path(tmp) / "cache"
        fake = FakeTransport()
        fake.seed_issue("01-alpha", "甲任务")
        backend = backend_for(root, fake, cache)
        # 1) 在线执行
        result = backend.update_task("01-alpha", {"进度": "执行中"},
                                     change_note="冲刺轮安排")
        check("冲刺轮安排" in result["readback"]["body"],
              "在线执行的说明应写入正文状态变化")
        # 2) 草稿保存:说明随草稿参数保留
        fake.offline()
        draft = backend.update_task("01-alpha", {"进度": "待验收"},
                                    change_note="验收轮安排")
        saved = json.loads(Path(draft["draft"]).read_text(encoding="utf-8"))
        check(saved["args"].get("change_note") == "验收轮安排",
              f"草稿应保存自定义说明,实际 {saved['args']}")
        # 3) 重放:说明随重放传递
        fake._offline = False
        published = backend.publish_drafts()
        check(published["published_count"] == 1,
              f"草稿应发布成功:{published['results']}")
        body = fake.issues[0]["body"]
        check("验收轮安排" in body,
              f"重放后正文应保留原说明(不回退默认文案),实际正文含默认文案:"
              f"{'安排更新' in body}")


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


# ---------- 第二轮审查修复票 review2-02:反例固化(修复前红、修复后绿) ----------

def test_append_result_partial_success_and_retry_completion() -> None:
    """SP-2:评论已真实发布而结果索引更新超时——部分成功如实保留(携带
    已发布评论身份与索引未完成状态,不整体报错);恢复后重试同一请求只
    收养既有评论并补齐索引,替身评论数恰 1(不重复发布)。"""

    with tempfile.TemporaryDirectory() as tmp:
        root = make_github_project(Path(tmp))
        fake = FakeTransport()
        fake.seed_issue("01-alpha", "甲任务")
        backend = backend_for(root, fake)
        fake.fail("PATCH", "/issues/1", "timeout")  # 评论 POST 成功后索引 PATCH 超时
        try:
            first = backend.append_result("01-alpha", "交付证据")  # 修复前:直接抛出
        except (mgs_github.TransportError, mgs_github.GithubRecordsError) as exc:
            first = {"raised": str(exc)}
        check(first.get("published") is True and first.get("partial") is True,
              f"评论已发布的部分成功应如实保留(不整体报错),实际 {first}")
        check(first.get("comment_id") is not None,
              f"结果应携带已发布评论身份,实际 {first}")
        check(first.get("index_updated") is False,
              f"未完成部分(结果索引)应如实表达,实际 {first}")
        check(len(fake.comments[1]) == 1,
              f"首次调用替身应已有 1 条评论,实际 {len(fake.comments[1])} 条")
        check(f"#issuecomment-{first.get('comment_id')}"
              not in (fake.issues[0].get("body") or ""),
              "索引 PATCH 超时后正文不应已含该评论引用")
        # 恢复后重试同一请求:只收养既有评论并补齐索引
        fake._fail = []
        second = backend.append_result("01-alpha", "交付证据")
        check(second.get("published") is True
              and second.get("index_updated") is True,
              f"恢复后重试应完成索引并如实回报,实际 {second}")
        check(second.get("comment_id") == first.get("comment_id"),
              f"重试应收养既有评论(同一评论身份),实际 {second.get('comment_id')}"
              f" vs {first.get('comment_id')}")
        posts = [c for c in fake.calls if c[0] == "POST" and "/comments" in c[1]]
        check(len(posts) == 1,
              f"重试不得再发评论 POST(全程恰 1 次),实际 {len(posts)} 次")
        check(len(fake.comments[1]) == 1,
              f"替身评论数应恰 1(不重复发布),实际 {len(fake.comments[1])} 条")
        check(f"#issuecomment-{first.get('comment_id')}"
              in (fake.issues[0].get("body") or ""),
              "重试后结果索引应补齐该评论引用")
        # 已完成后的再次重试仍幂等:评论数与索引均不再变化
        third = backend.append_result("01-alpha", "交付证据")
        check(third.get("published") is True
              and third.get("index_updated") is True
              and third.get("comment_id") == first.get("comment_id"),
              f"完成后的重复请求应幂等(收养既有评论),实际 {third}")
        check(len(fake.comments[1]) == 1, "幂等重试后评论数仍应恰 1")


def test_append_result_draft_replay_partial_keeps_draft() -> None:
    """SP-2 草稿重放侧:重放中评论已发布而索引更新失败属部分成功——草稿
    保留(不算完成),下次重放收养既有评论只补索引;全程评论数恰 1。"""

    with tempfile.TemporaryDirectory() as tmp:
        root = make_github_project(Path(tmp))
        cache = Path(tmp) / "cache"
        fake = FakeTransport()
        fake.seed_issue("01-alpha", "甲任务")
        backend = backend_for(root, fake, cache)
        backend.fetch_tasks()  # 在线建立缓存(离线草稿路径需要)
        fake.offline()
        draft = backend.append_result("01-alpha", "离线证据")
        check(draft.get("published") is False and draft.get("draft"),
              f"离线追加结果应保存草稿,实际 {draft}")
        # 恢复但索引 PATCH 超时:重放得到部分成功,草稿保留待下次补齐
        fake._offline = False
        fake.fail("PATCH", "/issues/1", "timeout")
        first = backend.publish_drafts()
        check(first["published_count"] == 0,
              f"部分成功不算完成(草稿保留),实际 {first}")
        check(len(fake.comments[1]) == 1,
              f"重放应已发布 1 条评论,实际 {len(fake.comments[1])} 条")
        check(len(list((cache / "drafts").glob("*.json"))) == 1,
              "部分成功的草稿应保留在待发布目录")
        # 故障清除后再次重放:收养既有评论,只补索引
        fake._fail = []
        second = backend.publish_drafts()
        check(second["published_count"] == 1,
              f"恢复后重放应补齐索引并完成,实际 {second}")
        check(len(fake.comments[1]) == 1,
              f"补齐重放不得重复发布评论(仍恰 1 条),"
              f"实际 {len(fake.comments[1])} 条")
        check(not list((cache / "drafts").glob("*.json")),
              "完成后的草稿应移出待发布目录")
        check("#issuecomment-" in (fake.issues[0].get("body") or "")
              and "离线证据" in (fake.issues[0].get("body") or ""),
              "结果索引应补齐该评论引用")


def test_draft_identity_includes_repo_cross_repo() -> None:
    """SP-3:草稿身份含目标仓库——同一秒、同一缓存目录、两个各有授权的仓库
    保存同参数的离线创建,两份草稿各自保存(互不顶替、不得误报幂等);
    发布各归各仓;同仓库同参数重复保存的幂等语义不回退(S6)。"""

    with tempfile.TemporaryDirectory() as tmp:
        base = Path(tmp)
        root = make_github_project(base / "project")
        config = mgs_records.load_config(root)
        old = {**config, "repo": {"host": "github.com", "owner": "old-owner",
                                  "repo": "private-repo"},
               "external": ("github.com/old-owner/private-repo:"
                            "issues-write(已授权旧仓库)")}
        offline = FakeTransport()
        offline.offline()
        previous = mgs_github.GithubBackend(old, offline, base / "shared-cache")
        current = mgs_github.GithubBackend(config, offline, base / "shared-cache")
        real_datetime = mgs_github._dt.datetime

        class FixedDatetime(real_datetime):
            @classmethod
            def now(cls, tz=None):
                return cls(2026, 9, 9, 1, 2, 3, tzinfo=tz)

        mgs_github._dt.datetime = FixedDatetime
        try:
            a = previous.create_task("09-same", "same title",
                                     {"当前目标": "same goal"})
            z = current.create_task("09-same", "same title",
                                    {"当前目标": "same goal"})
            again = current.create_task("09-same", "same title",
                                        {"当前目标": "same goal"})
        finally:
            mgs_github._dt.datetime = real_datetime
        check(a.get("draft") and z.get("draft") and a["draft"] != z["draft"],
              f"两仓库同秒同参数的草稿身份应不同(身份含仓库),"
              f"实际 {a.get('draft')} / {z.get('draft')}")
        check(z.get("idempotent") is not True,
              f"跨仓库请求不是同一操作的重放,不得按幂等顶替,实际 {z}")
        drafts = [json.loads(p.read_text(encoding="utf-8"))
                  for p in (base / "shared-cache/drafts").glob("*.json")]
        check(len(drafts) == 2,
              f"两仓库应各存各的草稿,实际 {len(drafts)} 份:"
              f"{[d.get('repo') for d in drafts]}")
        check({d.get("repo") for d in drafts}
              == {"github.com/old-owner/private-repo", REPO},
              f"两份草稿应各自记录目标仓库,实际 {[d.get('repo') for d in drafts]}")
        check(again.get("idempotent") is True,
              f"同仓库同参数重复保存应保持幂等(S6 语义不回退),实际 {again}")
        check(len(list((base / "shared-cache/drafts").glob("*.json"))) == 2,
              "幂等重放不得产生第三份草稿")
        # 发布各归各仓:当前仓库后端只发布自己的草稿(S1 拒绝旧仓库草稿),
        # 当前仓库恰收到一次创建请求
        online = FakeTransport()
        current_online = mgs_github.GithubBackend(config, online,
                                                  base / "shared-cache")
        publish = current_online.publish_drafts()
        check(publish["published_count"] == 1,
              f"只有本仓库草稿可发布,实际 {publish}")
        posts = [c for c in online.calls if c[0] == "POST"]
        check(len(posts) == 1 and posts[0][1].endswith("/issues"),
              f"当前仓库应恰收到一次创建请求,实际 {posts}")
        check(any("任务身份:09-same" in i["body"] for i in online.issues),
              "本仓库草稿应实际创建为任务")
        check(len(list((base / "shared-cache/drafts").glob("*.json"))) == 1,
              "旧仓库草稿应原样保留待其自己的后端发布")


# ---------- 第三轮审查修复票 review3-01:反例固化(修复前红、修复后绿) ----------

def test_append_result_partial_retry_read_first_timeout_no_duplicate() -> None:
    """SP-7:首轮部分成功(partial+comment_id,评论已确认发布)后,重试的
    读前收养查询超时不得当作全新发布——按本地「待补索引登记」保留已发布
    操作身份、保持待恢复状态(partial 语义);彻底恢复后重试收养既有评论
    只补索引,替身评论恰 1。partial(已发布未完索引)与 uncertain(结果
    未知)语义互不混同。"""

    with tempfile.TemporaryDirectory() as tmp:
        base = Path(tmp)
        root = make_github_project(base / "project")
        cache = base / "cache"
        fake = FakeTransport()
        fake.seed_issue("01-alpha", "甲任务")
        backend = backend_for(root, fake, cache)
        fake.fail("PATCH", "/issues/1", "timeout")  # 评论 POST 成功+索引 PATCH 超时
        try:
            first = backend.append_result("01-alpha", "交付证据")  # 修复前:直接抛出
        except (mgs_github.TransportError, mgs_github.GithubRecordsError) as exc:
            first = {"raised": str(exc)}
        check(first.get("published") is True and first.get("partial") is True,
              f"首轮应如实回报部分成功,实际 {first}")
        check(first.get("comment_id") is not None
              and first.get("index_updated") is False,
              f"首轮结果应携带已发布评论身份与索引未完成状态,实际 {first}")
        check(len(fake.comments[1]) == 1,
              f"首轮替身应已有 1 条评论,实际 {len(fake.comments[1])} 条")
        check(len(list((cache / "pending-index").rglob("*.json"))) == 1,
              "部分成功应在本地登记已发布评论身份(待补索引登记)")
        # 恢复索引 PATCH,但重试的读前收养查询超时(SP-7 反例:
        # 当前实现把它当作全新发布再 POST 一条)
        fake._fail = []
        fake.fail("GET", "/comments", "timeout")
        try:
            second = backend.append_result("01-alpha", "交付证据")
        except (mgs_github.TransportError, mgs_github.GithubRecordsError) as exc:
            second = {"raised": str(exc)}
        check(second.get("published") is True and second.get("partial") is True,
              f"读前查询失败时应保持待恢复状态(不当作全新发布),实际 {second}")
        check(second.get("comment_id") == first.get("comment_id"),
              f"待恢复状态应保留前次已确认发布的评论身份,实际 "
              f"{second.get('comment_id')} vs {first.get('comment_id')}")
        check(second.get("index_updated") is False,
              f"待恢复状态应如实表达索引仍未完成,实际 {second}")
        check(second.get("uncertain") is not True,
              f"已确认发布(partial)与结果未知(uncertain)是两种事实,"
              f"不得混同,实际 {second}")
        check(len(fake.comments[1]) == 1,
              f"读前查询失败不得重复发布(替身评论仍恰 1),"
              f"实际 {len(fake.comments[1])} 条")
        posts = [c for c in fake.calls if c[0] == "POST" and "/comments" in c[1]]
        check(len(posts) == 1,
              f"全程应只发出 1 次评论 POST,实际 {len(posts)} 次")
        check(len(list((cache / "pending-index").rglob("*.json"))) == 1,
              "待恢复期间登记应保留(索引未补齐)")
        # 彻底恢复后重试:读前收养既有评论,只补索引
        fake._fail = []
        third = backend.append_result("01-alpha", "交付证据")
        check(third.get("published") is True
              and third.get("index_updated") is True
              and third.get("comment_id") == first.get("comment_id"),
              f"彻底恢复后重试应收养既有评论并补齐索引,实际 {third}")
        check(len(fake.comments[1]) == 1,
              f"补齐索引不得重复发布评论,实际 {len(fake.comments[1])} 条")
        check(f"#issuecomment-{first.get('comment_id')}"
              in (fake.issues[0].get("body") or ""),
              "彻底恢复后结果索引应补齐该评论引用")
        check(not list((cache / "pending-index").rglob("*.json")),
              "索引补齐后应清除待补索引登记")


def test_append_result_read_first_failure_without_pending_keeps_first_try() -> None:
    """SP-7 邻近语义:无待补索引登记(本次调用前未确认发布过)时,读前
    查询失败仍按首试语义继续尝试发布——S2「发布超时后回读失败不重发、
    保持 uncertain」的既有取舍不因本票回退(有缓存目录场景同样成立)。"""

    with tempfile.TemporaryDirectory() as tmp:
        base = Path(tmp)
        root = make_github_project(base / "project")
        cache = base / "cache"
        fake = FakeTransport()
        fake.seed_issue("01-alpha", "甲任务")
        backend = backend_for(root, fake, cache)
        fake.fail("GET", "/comments", "timeout")  # 读前收养查询超时(无登记)
        fake.drop("POST", "/comments")            # 评论已落地但响应超时
        outcome = backend.append_result("01-alpha", "交付证据")
        posts = [c for c in fake.calls if c[0] == "POST" and "/comments" in c[1]]
        check(len(posts) == 1,
              f"首试语义:读前查询失败(无登记)仍应尝试发布恰 1 次,"
              f"实际 {len(posts)} 次")
        check(outcome.get("uncertain") is True
              and outcome.get("published") is not True,
              f"发布超时且回读失败应保持 uncertain(不虚报成功、不重发),"
              f"实际 {outcome}")
        check(len(fake.comments[1]) == 1,
              f"替身应只有 1 条评论,实际 {len(fake.comments[1])} 条")
        check(not list((cache / "pending-index").rglob("*.json")),
              "uncertain(结果未知)不应写待补索引登记——登记只表达已确认发布")


# ---------- 第四轮审查修复票 review4-01:反例固化(修复前红、修复后绿) ----------


def _pending_digest(identity: str, result_markdown: str) -> str:
    """复算待补索引登记文件名的 8 hex 短摘要(与实现同一构造形态,
    用于自证复审确定性碰撞对在当前实现下确实共用登记文件)。"""

    payload = json.dumps({"op": "append_result",
                          "args": {"identity": identity,
                                   "result_markdown": result_markdown},
                          "repo": "github.com/mygamestudio/issue-accept"},
                         ensure_ascii=False, sort_keys=True)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()[:8]


class _OnceReadFailTransport(FakeTransport):
    """读前收养查询(GET comments)只失败一次、此后恢复的替身——沿复审
    探针 spec-independent-probes.py 的 OnceFail 形态,用于「读前失败后的
    后续读取(如补齐索引后的 read_task)应正常完成」的场景。"""

    read_fail = False

    def request(self, method: str, path: str, body: dict | None = None,
                *, auth: bool | None = None):
        if self.read_fail and method == "GET" and "/comments?" in path:
            self.read_fail = False
            self.calls.append((method, path, body))
            raise mgs_github.TransportError(
                "timeout", "one read-first timeout")
        return super().request(method, path, body, auth=auth)


def test_append_result_pending_collision_does_not_adopt_foreign_identity() -> None:
    """SP-11:登记文件名只取 8 hex 短摘要,同仓库同任务的两个不同结果正文
    可确定性碰撞共用同一登记文件。B(不同正文)的读前收养查询失败时
    不得冒认 A 的登记身份(published=true + A 的 comment_id,而 B 从未
    发布)——登记内容保留完整身份(op/args/目标仓库),读入时与当前
    请求逐项核对,不一致按无登记处理:B 按首试语义发布自己的评论;
    A 的登记不被冒认、也不被 B 的补齐清除误删(不误删他人登记)。"""

    with tempfile.TemporaryDirectory() as tmp:
        base = Path(tmp)
        root = make_github_project(base / "project")
        cache = base / "cache"
        fake = _OnceReadFailTransport()
        fake.seed_issue("01-task", "甲任务")
        backend = backend_for(root, fake, cache)
        # 复审确定性碰撞对(80,658 候选搜索所得,同一摘要 346df0e9):
        # 先自证两正文在当前实现下解析到同一登记文件路径
        result_a = "collision-result-79891"
        result_b = "collision-result-80657"
        check(_pending_digest("01-task", result_a)
              == _pending_digest("01-task", result_b),
              "前置:碰撞对两正文应得到同一 8 hex 短摘要(共用登记文件)")
        # A 首次调用部分成功:评论已发布、索引 PATCH 超时 → 留下登记
        fake.fail("PATCH", "/issues/1", "timeout")
        first = backend.append_result("01-task", result_a)
        check(first.get("published") is True and first.get("partial") is True,
              f"前置:A 首轮应如实部分成功,实际 {first}")
        registration = list((cache / "pending-index").rglob("*.json"))
        check(len(registration) == 1, "前置:A 的部分成功应留下待补索引登记")
        # B 的第一次调用仅读前 GET 超时(反例靶点):不得冒认 A 的登记
        fake._fail = []
        fake.read_fail = True
        second = backend.append_result("01-task", result_b)
        check(second.get("comment_id") != first.get("comment_id"),
              f"SP-11:B 不得冒认 A 的 comment_id,实际 "
              f"{second.get('comment_id')} vs {first.get('comment_id')}")
        check(second.get("published") is True
              and second.get("index_updated") is True,
              f"SP-11:B 应按首试语义发布自己的评论并补齐索引,实际 {second}")
        check(any(c["body"] == f"任务:01-task\n\n{result_b}"
                  for c in fake.comments[1]),
              "SP-11:B 应已发布自己的评论正文(而非只认 A 的评论)")
        check(list((cache / "pending-index").rglob("*.json")) == registration,
              "SP-11:B 的补齐清除不得误删 A 的登记(不误删他人登记)")
        # A 重试且读前查询又失败:凭自己的登记保持待恢复(既有语义不回退)
        fake._fail = []
        fake.read_fail = True
        third = backend.append_result("01-task", result_a)
        check(third.get("published") is True and third.get("partial") is True
              and third.get("comment_id") == first.get("comment_id"),
              f"SP-11:A 凭自己的登记应保持待恢复(review3-01 语义不回退),"
              f"实际 {third}")
        posts = [c for c in fake.calls if c[0] == "POST" and "/comments" in c[1]]
        check(len(posts) == 2,
              f"全程应恰 2 次 POST(A 首试 1 次+B 首试 1 次;A 待恢复不发布),"
              f"实际 {len(posts)} 次")


def test_append_result_pending_registration_missing_fields_disclosed_corrupt() -> None:
    """SP-11 旁证:登记文件是合法 JSON 但缺身份字段(空对象形态)时,不得
    静默当作可核验的登记——返回空身份却仍称已确认发布。形态不完整
    (缺字段/空身份)按登记损坏披露(corrupt 语义沿既有非法 JSON 行为:
    待恢复、不重发、提示人工核对)。"""

    with tempfile.TemporaryDirectory() as tmp:
        base = Path(tmp)
        root = make_github_project(base / "project")
        cache = base / "cache"
        fake = FakeTransport()
        fake.seed_issue("01-alpha", "甲任务")
        backend = backend_for(root, fake, cache)
        fake.fail("PATCH", "/issues/1", "timeout")
        backend.append_result("01-alpha", "交付证据")  # 部分成功留登记
        pending_file = next((cache / "pending-index").rglob("*.json"))
        pending_file.write_text("{}", encoding="utf-8")  # 合法 JSON、缺字段
        fake._fail = []
        fake.fail("GET", "/comments", "timeout")
        second = backend.append_result("01-alpha", "交付证据")
        note = second.get("note") or ""
        check(any(word in note for word in ("不可读", "损坏", "corrupt", "不完整")),
              f"SP-11:缺字段登记应披露登记损坏(形态不完整),实际 note={note!r}")
        check(second.get("comment_id") is None,
              f"SP-11:形态不完整的登记不得冒用评论身份,实际 {second}")
        check("人工核对" in note,
              f"SP-11:登记损坏披露应提示人工核对,实际 note={note!r}")
        check(len(fake.comments[1]) == 1,
              f"登记损坏的保守方向是不重发(沿 corrupt 语义),替身评论应仍恰 1,"
              f"实际 {len(fake.comments[1])} 条")
        posts = [c for c in fake.calls if c[0] == "POST" and "/comments" in c[1]]
        check(len(posts) == 1,
              f"登记损坏不应触发重发(全程恰 1 次 POST),实际 {len(posts)} 次")


def test_append_result_pending_registration_corrupt_json_keeps_recovery() -> None:
    """SP-11 回归守卫:登记文件为非法 JSON 时,review3-01 建立的 corrupt
    待恢复行为保持(不重发、披露登记不可读、提示人工核对)——本票的
    身份核验不回退该语义。"""

    with tempfile.TemporaryDirectory() as tmp:
        base = Path(tmp)
        root = make_github_project(base / "project")
        cache = base / "cache"
        fake = FakeTransport()
        fake.seed_issue("01-alpha", "甲任务")
        backend = backend_for(root, fake, cache)
        fake.fail("PATCH", "/issues/1", "timeout")
        backend.append_result("01-alpha", "交付证据")  # 部分成功留登记
        pending_file = next((cache / "pending-index").rglob("*.json"))
        pending_file.write_text("{", encoding="utf-8")  # 非法 JSON
        fake._fail = []
        fake.fail("GET", "/comments", "timeout")
        second = backend.append_result("01-alpha", "交付证据")
        note = second.get("note") or ""
        check("不可读" in note or "损坏" in note or "corrupt" in note,
              f"SP-11:非法 JSON 登记应披露登记不可读,实际 note={note!r}")
        check(second.get("published") is True and second.get("partial") is True,
              f"非法 JSON 登记应保持待恢复(不当作全新发布),实际 {second}")
        posts = [c for c in fake.calls if c[0] == "POST" and "/comments" in c[1]]
        check(len(posts) == 1,
              f"非法 JSON 登记不应触发重发(全程恰 1 次 POST),实际 {len(posts)} 次")


def test_append_result_partial_without_cache_dir_carries_degraded_warning() -> None:
    """SP-10:未配置缓存目录时,部分成功(partial)的结果 note 必须实际
    携带退化警告——本模式无跨调用身份保留、读前收养查询失败的重试可能
    重复发布、建议配置缓存目录——且不再输出「不会重复发布」承诺;
    有缓存目录(登记落盘)时承诺保持,登记/待恢复/补齐清登记链路语义
    不回退(邻近对照)。"""

    with tempfile.TemporaryDirectory() as tmp:
        base = Path(tmp)
        root = make_github_project(base / "project")
        # 无缓存目录:partial note 应携带退化警告,不带不重复发布承诺
        fake = FakeTransport()
        fake.seed_issue("01-alpha", "甲任务")
        backend = backend_for(root, fake, None)
        fake.fail("PATCH", "/issues/1", "timeout")
        first = backend.append_result("01-alpha", "交付证据")
        check(first.get("published") is True and first.get("partial") is True
              and first.get("index_updated") is False,
              f"前置:无缓存目录首轮仍应如实部分成功,实际 {first}")
        note = first.get("note") or ""
        check("警告" in note,
              f"SP-10:无缓存目录的 partial note 应实际携带警告,实际 {note!r}")
        check("可能重复发布" in note or "可能重复" in note,
              f"SP-10:警告应说明本模式重试可能重复发布,实际 {note!r}")
        check("缓存目录" in note or "cache_dir" in note or "--cache-dir" in note,
              f"SP-10:警告应建议配置缓存目录,实际 {note!r}")
        check("不会重复发布" not in note,
              f"SP-10:无缓存模式不得表述为拥有不重复发布保证,实际 {note!r}")
        # 邻近对照:有缓存目录(登记落盘)时承诺保持——有缓存语义不变
        cache = base / "cache"
        fake_cached = FakeTransport()
        fake_cached.seed_issue("01-alpha", "甲任务")
        backend_cached = backend_for(root, fake_cached, cache)
        fake_cached.fail("PATCH", "/issues/1", "timeout")
        with_cache = backend_cached.append_result("01-alpha", "交付证据")
        note_cached = with_cache.get("note") or ""
        check("不会重复发布" in note_cached,
              f"SP-10 对照:登记落盘时「不会重复发布」承诺保持,实际 {note_cached!r}")
        check("警告" not in note_cached,
              f"SP-10 对照:登记落盘时不应出现登记不可用警告,实际 {note_cached!r}")
        check(len(list((cache / "pending-index").rglob("*.json"))) == 1,
              "SP-10 对照:有缓存目录时登记照常落盘")


# ---------- 第五轮审查修复票 review5-01:反例固化(修复前红、修复后绿) ----------


def _pending_full_digest(identity: str, result_markdown: str) -> str:
    """复算待补索引登记完整内容身份的全长 SHA-256 摘要(与实现同一构造
    形态;前 8 hex 即 _pending_digest 复算的既有短摘要,用于自证碰撞对
    在共存布局下分别解析到同目录的不同登记文件)。"""

    payload = json.dumps({"op": "append_result",
                          "args": {"identity": identity,
                                   "result_markdown": result_markdown},
                          "repo": "github.com/mygamestudio/issue-accept"},
                         ensure_ascii=False, sort_keys=True)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def test_append_result_pending_collision_both_partial_coexist() -> None:
    """SP-14:碰撞对(A/B 同仓库同任务不同正文、同一 8 hex 短摘要)先后
    partial 时,后者的登记不得覆盖前者——不同完整身份的登记共存,任一
    请求的重试都能找回自己的登记:A 恢复重试(仅读前 GET 超时)不重新
    POST、保持待恢复;B 同理;互不干扰、互不误删;补齐后各自清除。"""

    with tempfile.TemporaryDirectory() as tmp:
        base = Path(tmp)
        root = make_github_project(base / "project")
        cache = base / "cache"
        fake = _OnceReadFailTransport()
        fake.seed_issue("01-task", "甲任务")
        backend = backend_for(root, fake, cache)
        result_a = "collision-result-79891"
        result_b = "collision-result-80657"
        check(_pending_digest("01-task", result_a)
              == _pending_digest("01-task", result_b),
              "前置:碰撞对两正文应得到同一 8 hex 短摘要(同一登记短摘要)")
        # A 首次调用部分成功:评论已发布、索引 PATCH 超时 → 留下 A 的登记
        fake.fail("PATCH", "/issues/1", "timeout")
        first = backend.append_result("01-task", result_a)
        check(first.get("published") is True and first.get("partial") is True,
              f"前置:A 首轮应如实部分成功,实际 {first}")
        # B 的首次调用读前 GET 超时:无自己的登记(不冒认 A 的,SP-11 语义
        # 保持)→ 按首试语义发布自己的评论;索引 PATCH 仍超时 → B 也部分
        # 成功、留下 B 的登记(不得覆盖 A 的)
        fake.read_fail = True
        second = backend.append_result("01-task", result_b)
        check(second.get("published") is True and second.get("partial") is True,
              f"前置:B 首轮应如实部分成功,实际 {second}")
        registrations = sorted(
            p.relative_to(cache / "pending-index").as_posix()
            for p in (cache / "pending-index").rglob("*.json"))
        check(len(registrations) == 2,
              f"SP-14:碰撞对先后 partial 的两份登记应共存(不同完整身份"
              f"不同文件),实际 {registrations}")
        check(any(_pending_full_digest("01-task", result_a) in name
                  for name in registrations)
              and any(_pending_full_digest("01-task", result_b) in name
                      for name in registrations),
              f"SP-14:两份登记应分别以 A/B 完整身份哈希为文件名落盘,"
              f"实际 {registrations}")
        # A 恢复重试,仅读前 GET 超时(反例靶点;PATCH 已恢复):必须凭
        # 自己的登记保持待恢复,不得当作全新发布而重新 POST(登记被 B
        # 覆盖时 A 会失去登记、被当成首试重新 POST 第三条)
        fake._fail = []
        fake.read_fail = True
        third = backend.append_result("01-task", result_a)
        check(third.get("published") is True and third.get("partial") is True
              and third.get("comment_id") == first.get("comment_id"),
              f"SP-14:A 恢复重试应凭自己的登记保持待恢复(不重新 POST),"
              f"实际 {third}")
        # B 恢复重试,仅读前 GET 超时:同理凭自己的登记保持待恢复
        fake._fail = []
        fake.read_fail = True
        fourth = backend.append_result("01-task", result_b)
        check(fourth.get("published") is True and fourth.get("partial") is True
              and fourth.get("comment_id") == second.get("comment_id"),
              f"SP-14:B 恢复重试应凭自己的登记保持待恢复(不重新 POST),"
              f"实际 {fourth}")
        check(sum(c["body"] == f"任务:01-task\n\n{result_a}"
                  for c in fake.comments[1]) == 1,
              "SP-14:A 正文评论应恰 1 条(重试不重复发布)")
        check(sum(c["body"] == f"任务:01-task\n\n{result_b}"
                  for c in fake.comments[1]) == 1,
              "SP-14:B 正文评论应恰 1 条(重试不重复发布)")
        posts = [c for c in fake.calls if c[0] == "POST" and "/comments" in c[1]]
        check(len(posts) == 2,
              f"SP-14:至此应恰 2 次 POST(A/B 首试各 1 次;重试均不发布),"
              f"实际 {len(posts)} 次")
        # 索引补齐:远端恢复后两请求各自重试,经读前收养只补索引,
        # 登记各自清除(互不误删)
        fifth = backend.append_result("01-task", result_a)
        sixth = backend.append_result("01-task", result_b)
        check(fifth.get("index_updated") is True
              and fifth.get("comment_id") == first.get("comment_id"),
              f"SP-14:A 补齐应收养既有评论并完成索引,实际 {fifth}")
        check(sixth.get("index_updated") is True
              and sixth.get("comment_id") == second.get("comment_id"),
              f"SP-14:B 补齐应收养既有评论并完成索引,实际 {sixth}")
        check(not list((cache / "pending-index").rglob("*.json")),
              "SP-14:两请求各自补齐后登记应全部清除(互不误删)")
        posts = [c for c in fake.calls if c[0] == "POST" and "/comments" in c[1]]
        check(len(posts) == 2,
              f"SP-14:补齐重试经读前收养不新增 POST,实际 {len(posts)} 次")


def test_append_result_pending_registration_missing_receipt_disclosed_corrupt() -> None:
    """SP-14 复审观察项(并入本票):登记保留完整身份(op/args/repo)但缺
    comment_id/ref 回执字段时,不得静默返回缺失发布身份仍称已确认发布——
    回执字段纳入形态完整性校验,缺失按登记损坏披露(corrupt 语义沿既有:
    待恢复、不重发、提示人工核对)。"""

    for fields in (("comment_id",), ("ref",), ("comment_id", "ref")):
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            root = make_github_project(base / "project")
            cache = base / "cache"
            fake = FakeTransport()
            fake.seed_issue("01-alpha", "甲任务")
            backend = backend_for(root, fake, cache)
            fake.fail("PATCH", "/issues/1", "timeout")
            backend.append_result("01-alpha", "交付证据")  # 部分成功留登记
            pending_file = next((cache / "pending-index").rglob("*.json"))
            pending = json.loads(pending_file.read_text(encoding="utf-8"))
            for field in fields:
                pending.pop(field)
            pending_file.write_text(json.dumps(pending, ensure_ascii=False),
                                    encoding="utf-8")
            fake._fail = [("GET", "/comments", "timeout")]
            second = backend.append_result("01-alpha", "交付证据")
            note = second.get("note") or ""
            check(second.get("published") is True
                  and second.get("partial") is True,
                  f"回执缺失{fields}:应保持待恢复(不当作全新发布),"
                  f"实际 {second}")
            check(second.get("comment_id") is None and second.get("ref") is None,
                  f"回执缺失{fields}:不得冒用发布身份,实际 {second}")
            check("不可读" in note or "不完整" in note,
                  f"回执缺失{fields}:应披露登记不完整,实际 note={note!r}")
            check("人工核对" in note,
                  f"回执缺失{fields}:应提示人工核对,实际 note={note!r}")
            check(len(fake.comments[1]) == 1,
                  f"回执缺失{fields}:保守方向是不重发,替身评论应仍恰 1,"
                  f"实际 {len(fake.comments[1])} 条")
            posts = [c for c in fake.calls
                     if c[0] == "POST" and "/comments" in c[1]]
            check(len(posts) == 1,
                  f"回执缺失{fields}:不应触发重发(全程恰 1 次 POST),"
                  f"实际 {len(posts)} 次")


def test_append_result_pending_legacy_flat_registration_compatible() -> None:
    """兼容:修复前的在盘登记(平铺 8 hex 短摘要文件名,c9a8021/bc230ea
    写入的布局)读入语义不破坏——身份核验、待恢复、补齐清除全部沿用;
    读入经身份核验属于当前请求后按新布局(完整身份哈希文件名)重写迁移,
    消除新旧双份并存与「清除后自旧文件复活」。"""

    with tempfile.TemporaryDirectory() as tmp:
        base = Path(tmp)
        root = make_github_project(base / "project")
        cache = base / "cache"
        fake = _OnceReadFailTransport()
        fake.seed_issue("01-alpha", "甲任务")
        backend = backend_for(root, fake, cache)
        # 部分成功留登记,再手工归位到修复前的平铺布局(内容一字不差)
        fake.fail("PATCH", "/issues/1", "timeout")
        first = backend.append_result("01-alpha", "交付证据")
        current = next((cache / "pending-index").rglob("*.json"))
        content = current.read_text(encoding="utf-8")
        legacy = (cache / "pending-index"
                  / f"append-result-01-alpha-"
                    f"{_pending_digest('01-alpha', '交付证据')}.json")
        legacy.write_text(content, encoding="utf-8")
        current.unlink()
        # 旧布局读入兼容:读前 GET 超时的重试凭旧登记保持待恢复、不重发
        fake.read_fail = True
        second = backend.append_result("01-alpha", "交付证据")
        check(second.get("published") is True and second.get("partial") is True
              and second.get("comment_id") == first.get("comment_id"),
              f"兼容:旧布局登记应照常支撑待恢复,实际 {second}")
        posts = [c for c in fake.calls if c[0] == "POST" and "/comments" in c[1]]
        check(len(posts) == 1,
              f"兼容:旧布局登记不应触发重发,实际 {len(posts)} 次")
        # 迁移:身份核验通过的旧布局登记在读入后应按新布局重写并移除旧文件
        check(any(_pending_full_digest("01-alpha", "交付证据")
                  in p.relative_to(cache / "pending-index").as_posix()
                  for p in (cache / "pending-index").rglob("*.json")),
              "兼容:旧布局登记读入后应迁移为新布局(完整身份哈希文件名)")
        check(not legacy.exists(),
              "兼容:迁移后旧布局文件应移除(不双份并存)")
        # 补齐:远端恢复后重试经读前收养补齐索引,新旧布局登记一并清除
        fake._fail = []
        third = backend.append_result("01-alpha", "交付证据")
        check(third.get("index_updated") is True
              and third.get("comment_id") == first.get("comment_id"),
              f"兼容:迁移后的登记应照常补齐收养,实际 {third}")
        check(not list((cache / "pending-index").rglob("*.json"))
              and not legacy.exists(),
              "兼容:补齐后新旧布局登记应一并清除(不自旧文件复活)")


# ---------- 第六轮审查修复票 review6-01:反例固化(修复前红、修复后绿) ----------


def test_append_result_pending_clear_keeps_foreign_legacy_registration() -> None:
    """SP-17(自然升级序列核心反例):旧平铺布局保存另一完整身份 B 的
    健康登记、当前布局保存本请求 A 的登记时,A 补齐索引触发的清理不得凭
    A 的一次核验无条件 unlink 两个路径——旧实现正是这样误删 B 的登记,
    使 B 重试读前失败被当作全新发布重新 POST(3 POST、B 正文 2 条)。
    期望:每个待删除文件分别通过自身完整身份核验,B 的旧登记保留;B 重试
    凭自己的登记待恢复(不重新 POST、恰 1 条、总 posts=2)。"""

    with tempfile.TemporaryDirectory() as tmp:
        base = Path(tmp)
        root = make_github_project(base / "project")
        cache = base / "cache"
        fake = _OnceReadFailTransport()
        fake.seed_issue("01-task", "甲任务")
        backend = backend_for(root, fake, cache)
        a, b = "collision-result-79891", "collision-result-80657"
        check(_pending_digest("01-task", a) == _pending_digest("01-task", b),
              "前置:碰撞对两正文应得到同一 8 hex 短摘要(同一登记短摘要)")
        # 升级前:旧实现给 B 留下平铺健康登记(按 review5-01 兼容测试的
        # 旧格式构造方式:B 真实部分成功留登记,再原样归位到旧平铺路径)
        fake.fail("PATCH", "/issues/1", "timeout")
        first_b = backend.append_result("01-task", b)
        check(first_b.get("published") is True and first_b.get("partial") is True,
              f"前置:B 首轮应如实部分成功,实际 {first_b}")
        b_current = next((cache / "pending-index").rglob("*.json"))
        legacy = (cache / "pending-index"
                  / f"append-result-01-task-"
                    f"{_pending_digest('01-task', b)}.json")
        legacy.write_text(b_current.read_text(encoding="utf-8"),
                          encoding="utf-8")
        b_current.unlink()
        check(legacy.exists(),
              "前置:B 的旧平铺健康登记应就位(自然升级前的在盘状态)")
        # 升级后:A 读前失败 partial——旧布局 B 的登记身份不匹配(不冒认,
        # SP-11),A 按首试发布并留新布局登记;两登记共存
        fake.read_fail = True
        second_a = backend.append_result("01-task", a)
        check(second_a.get("published") is True and second_a.get("partial") is True,
              f"前置:A 首轮应如实部分成功,实际 {second_a}")
        before = sorted(p.relative_to(cache / "pending-index").as_posix()
                        for p in (cache / "pending-index").rglob("*.json"))
        check(len(before) == 2,
              f"前置:清理前应恰两份登记共存(旧平铺 B + 新布局 A),"
              f"实际 {before}")
        # A 补齐索引触发清理:只应清除 A 自己的新布局登记,B 的旧平铺
        # 登记不因他人请求的清理被误删(SP-17 红点)
        fake._fail = []
        third_a = backend.append_result("01-task", a)
        check(third_a.get("index_updated") is True
              and third_a.get("comment_id") == second_a.get("comment_id"),
              f"SP-17:A 补齐应收养既有评论并完成索引,实际 {third_a}")
        check(legacy.exists(),
              "SP-17:A 补齐清理后 B 的旧平铺登记应仍在(不得凭 A 的核验"
              "授权删除另一完整身份 B 的健康登记)")
        after = sorted(p.relative_to(cache / "pending-index").as_posix()
                       for p in (cache / "pending-index").rglob("*.json"))
        check(after == [legacy.relative_to(cache / "pending-index").as_posix()],
              f"SP-17:清理应只清除 A 自己的新布局登记,B 的旧登记保留,"
              f"实际 {after}")
        # B 重试读前失败:凭自己的旧登记待恢复(不重新 POST)
        fake.read_fail = True
        fourth_b = backend.append_result("01-task", b)
        check(fourth_b.get("published") is True and fourth_b.get("partial") is True
              and fourth_b.get("comment_id") == first_b.get("comment_id"),
              f"SP-17:B 重试读前失败应凭自己的登记待恢复(不重新 POST),"
              f"实际 {fourth_b}")
        check(fourth_b.get("index_updated") is False,
              f"SP-17:B 待恢复应如实表达索引仍未完成,实际 {fourth_b}")
        posts = [c for c in fake.calls if c[0] == "POST" and "/comments" in c[1]]
        check(len(posts) == 2,
              f"SP-17:全程应恰 2 次 POST(A/B 首试各 1 次;重试不发布),"
              f"实际 {len(posts)} 次")
        check(sum(c["body"] == f"任务:01-task\n\n{b}"
                  for c in fake.comments[1]) == 1,
              "SP-17:B 正文评论应恰 1 条(登记不被误删才不重复发布)")
        check(sum(c["body"] == f"任务:01-task\n\n{a}"
                  for c in fake.comments[1]) == 1,
              "SP-17:A 正文评论应恰 1 条")
        # B 彻底恢复后重试:经读前收养补齐索引,登记清除(链路闭合)
        fifth_b = backend.append_result("01-task", b)
        check(fifth_b.get("index_updated") is True
              and fifth_b.get("comment_id") == first_b.get("comment_id"),
              f"SP-17:B 补齐应收养既有评论并完成索引,实际 {fifth_b}")
        check(not list((cache / "pending-index").rglob("*.json")),
              "SP-17:B 补齐后登记应清除(迁移+清除链路闭合)")
        posts = [c for c in fake.calls if c[0] == "POST" and "/comments" in c[1]]
        check(len(posts) == 2,
              f"SP-17:补齐重试经读前收养不新增 POST,实际 {len(posts)} 次")


def test_append_result_pending_clear_removes_same_identity_both_layouts() -> None:
    """SP-17 不复活语义保持:同身份双布局残留(迁移中途失败留下的旧副本)
    在逐路径核验下两处都属当前请求、都应清除——「已清除的登记不因迁移
    残留复活」(review5-01)不因本票回退。"""

    with tempfile.TemporaryDirectory() as tmp:
        base = Path(tmp)
        root = make_github_project(base / "project")
        cache = base / "cache"
        fake = FakeTransport()
        fake.seed_issue("01-alpha", "甲任务")
        backend = backend_for(root, fake, cache)
        # 部分成功留新布局登记,再复制一份到旧平铺路径(同身份双布局残留)
        fake.fail("PATCH", "/issues/1", "timeout")
        first = backend.append_result("01-alpha", "交付证据")
        check(first.get("partial") is True,
              f"前置:首轮应部分成功,实际 {first}")
        current = next((cache / "pending-index").rglob("*.json"))
        legacy = (cache / "pending-index"
                  / f"append-result-01-alpha-"
                    f"{_pending_digest('01-alpha', '交付证据')}.json")
        legacy.write_text(current.read_text(encoding="utf-8"), encoding="utf-8")
        check(current.exists() and legacy.exists(),
              "前置:同身份双布局残留就位(迁移中途失败的在盘形态)")
        # 补齐索引触发清理:两处同身份健康登记都属当前请求,都清除
        fake._fail = []
        second = backend.append_result("01-alpha", "交付证据")
        check(second.get("index_updated") is True
              and second.get("comment_id") == first.get("comment_id"),
              f"不复活:补齐应收养既有评论并完成索引,实际 {second}")
        check(not current.exists() and not legacy.exists(),
              "不复活:同身份双布局残留应一并清除(不自旧文件复活)")
        check(not list((cache / "pending-index").rglob("*.json")),
              "不复活:清理后不得残留任何登记文件")


def _pending_registration_content(identity: str, result_markdown: str,
                                  comment_id: int, ref: str) -> dict:
    """构造一份形态健康的待补索引登记内容(与 _record_pending_index 落盘
    形态一致),供逐路径分侧语义测试手工布置两布局的在盘状态。"""

    return {"op": "append_result",
            "args": {"identity": identity,
                     "result_markdown": result_markdown},
            "repo": REPO,
            "status": "已发布未补索引",
            "comment_id": comment_id, "ref": ref,
            "created_at": "2026-09-10T00:00:00+08:00",
            "cause": "timeout: injected timeout",
            "note": "测试构造的登记内容"}


def test_clear_pending_index_verifies_each_path_independently() -> None:
    """SP-17 分侧语义:待删除文件自己的登记与当前请求身份不匹配(他请求
    的健康登记)/JSON 无效/回执不完整时,该路径保守保留;另一路径上的同
    身份健康登记照常清除——每个文件按自身内容独立判定,互不代劳、互不
    株连(修复前:单次核验通过则两路径无条件删除,不通过则两路径全留)。"""

    own = ("01-task", "collision-result-79891")
    foreign_body = "collision-result-80657"
    cases = [
        # (说明, 保留侧内容, 保留侧在旧平铺布局?)
        ("旧平铺是他请求的健康登记", _pending_registration_content(
            "01-task", foreign_body, 5100, "#issuecomment-5100"), True),
        ("当前布局是他请求的健康登记", _pending_registration_content(
            "01-task", foreign_body, 5100, "#issuecomment-5100"), False),
        ("旧平铺是无效 JSON", "{ not valid json", True),
        ("当前布局是回执不完整登记", {
            **_pending_registration_content("01-task", own[1], 5101,
                                            "#issuecomment-5101"),
            "comment_id": None}, False),
        ("旧平铺是身份形态不完整登记", {
            "op": "append_result", "repo": REPO,
            "comment_id": 5100, "ref": "#issuecomment-5100"}, True),
    ]
    for label, kept_content, kept_on_legacy in cases:
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            root = make_github_project(base / "project")
            cache = base / "cache"
            backend = backend_for(root, FakeTransport(), cache)
            current = backend._pending_index_file(*own)
            legacy = backend._legacy_pending_index_file(*own)
            healthy = _pending_registration_content(
                own[0], own[1], 5101, "#issuecomment-5101")
            kept_path, cleared_path = ((legacy, current) if kept_on_legacy
                                       else (current, legacy))
            kept_path.parent.mkdir(parents=True, exist_ok=True)
            kept_path.write_text(kept_content if isinstance(kept_content, str)
                                 else json.dumps(kept_content,
                                                 ensure_ascii=False),
                                 encoding="utf-8")
            cleared_path.parent.mkdir(parents=True, exist_ok=True)
            cleared_path.write_text(json.dumps(healthy, ensure_ascii=False),
                                    encoding="utf-8")
            backend._clear_pending_index(*own)
            check(kept_path.exists(),
                  f"SP-17 分侧({label}):该路径应保守保留(不得由另一路径"
                  "的核验代劳删除)")
            check(not cleared_path.exists(),
                  f"SP-17 分侧({label}):另一路径同身份健康登记应正常清除")
            if not isinstance(kept_content, str) and kept_path.exists():
                check(json.loads(kept_path.read_text(encoding="utf-8"))
                      == kept_content,
                      f"SP-17 分侧({label}):保留侧文件内容不应被改动")


def test_clear_pending_index_unreadable_path_kept_quietly() -> None:
    """SP-17 保守性:清理阶段路径不可读(如登记路径被目录占用)/损坏
    (非 JSON 内容)时不抛异常、该侧保守保留;另一路径同身份健康登记照常
    清除——损坏登记保持原位由人工按哨兵处置,清理沉默沿既有口径。"""

    own = ("01-alpha", "交付证据")
    cases = [("登记路径被目录占用(不可读)", "current"),
             ("旧平铺是非 JSON 内容(损坏)", "legacy")]
    for label, broken_side in cases:
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            root = make_github_project(base / "project")
            cache = base / "cache"
            backend = backend_for(root, FakeTransport(), cache)
            current = backend._pending_index_file(*own)
            legacy = backend._legacy_pending_index_file(*own)
            healthy = _pending_registration_content(
                own[0], own[1], 5101, "#issuecomment-5101")
            current.parent.mkdir(parents=True, exist_ok=True)
            legacy.parent.mkdir(parents=True, exist_ok=True)
            if broken_side == "current":
                current.mkdir(parents=True)  # 路径被目录占用:read_text 抛 OSError
                broken, intact = current, legacy
            else:
                legacy.write_text("\x00not-json{{", encoding="utf-8")
                broken, intact = legacy, current
            intact.write_text(json.dumps(healthy, ensure_ascii=False),
                              encoding="utf-8")
            try:
                backend._clear_pending_index(*own)
                raised = None
            except Exception as exc:  # noqa: BLE001 — 红点:清理阶段不得抛异常
                raised = exc
            check(raised is None,
                  f"SP-17 保守({label}):清理不得因不可读/损坏路径抛异常,"
                  f"实际 {raised!r}")
            check(broken.exists(),
                  f"SP-17 保守({label}):不可读/损坏侧应保守保持原位"
                  "(由人工按哨兵处置)")
            check(not intact.exists(),
                  f"SP-17 保守({label}):另一路径同身份健康登记应照常清除")


# ---------- 票 02:双后端共用正文与错误语义(READ-08/READ-09/READ-10) ----------

# 同一份任务正文:空身份、空字段、未知小节、全角冒号与分号分隔、畸形任务。
SHARED_BODY = (
    "# 畸形任务\n\n"
    "任务身份:。当前分流:ready-for-agent。进度:待执行;负责人:张三。\n\n"
    "## 工作请求\n\n"
    "- 当前目标:演示目标\n"
    "- 输入与基线:GAME_DESIGN v1\n"
    "- 本次交付:示例交付\n"
    "- 允许修改范围:src/**\n"
    "- 所需能力:文件读写\n"
    "- 完成标准:\n"
    "- 执行责任:Agent（制作实现）\n"
    "- 验收方式:代码级检查\n"
    "- 依赖:无\n\n"
    "## 未知小节\n\n"
    "未知内容仍需保留\n\n"
    "## 结果索引\n\n"
    "(暂无)\n"
)


def _seed_raw_issue(fake: FakeTransport, body: str, *,
                    label: str = "agent-ready", number: int = 1) -> dict:
    issue = {"number": number, "id": 1000 + number, "title": "畸形任务",
             "body": body, "labels": [{"name": label}] if label else [],
             "state": "open", "state_reason": None,
             "html_url": f"https://example.invalid/i/{number}"}
    fake.issues.append(issue)
    fake.comments[number] = []
    return issue


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


# ---------- 票 04:GitHub 一次 ready 单份来源(R1/READ-02/03/05/06) ----------

def _issue_list_calls(fake: "FakeTransport") -> int:
    return sum(1 for method, path, _body in fake.calls
               if method == "GET" and path.split("?", 1)[0].endswith("/issues"))


def test_github_ready_fetches_task_set_once() -> None:
    """READ-02:GitHub ready 只获取一次全量任务集合,依赖与判断用同一集合。"""

    with tempfile.TemporaryDirectory() as tmp:
        root = make_github_project(Path(tmp))
        fake = FakeTransport()
        fake.seed_issue("01-alpha", "甲任务")
        fake.seed_issue("02-beta", "乙任务", project_label="info",
                        deps="01-alpha")
        fake.calls.clear()
        ready = mgs_records.startable_tasks(root, transport=fake)
        check(_issue_list_calls(fake) == 1,
              f"GitHub ready 应只获取一次任务集合,实际 {_issue_list_calls(fake)}")
        startable = {i["identity"] for i in ready["startable"]}
        check(startable == {"01-alpha"},
              f"依赖判断应使用同一集合,实际 {ready}")


def test_github_ready_does_not_consume_second_response_r1() -> None:
    """READ-03/R1:第二次响应对同一任务给出不同依赖时,本次不消费它。

    替身第一次返回「依赖:无」、第二次返回「依赖:02-missing」。修复后
    ready 只消费第一份集合,结果保持可开工且不混用两个时点。
    """

    with tempfile.TemporaryDirectory() as tmp:
        root = make_github_project(Path(tmp))

        class SequenceTransport(FakeTransport):
            """每次 GET /issues 依调用序号返回不同依赖的任务集合。"""

            def __init__(self) -> None:
                super().__init__()
                self._seq = 0
                self._list_calls = 0

            def request(self, method, path, body=None, *, auth=None):
                plain = path.split("?", 1)[0]
                if method == "GET" and plain.endswith("/issues"):
                    self._seq += 1
                    self._list_calls += 1
                    deps = "无" if self._seq == 1 else "02-missing"
                    seed = FakeTransport()
                    seed.seed_issue("01-alpha", "甲任务", deps=deps)
                    self.calls.append((method, path, body))
                    return 200, list(seed.issues)
                return super().request(method, path, body, auth=auth)

        fake = SequenceTransport()
        ready = mgs_records.startable_tasks(root, transport=fake)
        check(fake._list_calls == 1,
              f"R1:第二次预备响应不应被本次 ready 消费,实际第 {fake._list_calls} 次")
        startable = {i["identity"] for i in ready["startable"]}
        blocked = {i["identity"] for i in ready["blocked"]}
        check("01-alpha" in startable and "01-alpha" not in blocked
              and not any("02-missing" in r
                          for i in ready["blocked"] for r in i["reasons"]),
              f"本次应只使用第一份集合(依赖:无),不产生两时点混合,实际 {ready}")

        # 下一次顶层调用重新读取:看到第二响应改变后的依赖并更新分类
        ready2 = mgs_records.startable_tasks(root, transport=fake)
        check(fake._list_calls == 2,
              f"第二次顶层调用应重新读取(非缓存),实际第 {fake._list_calls} 次")
        blocked2 = {i["identity"]: i for i in ready2["blocked"]}
        check("01-alpha" in blocked2
              and any("02-missing" in r for r in blocked2["01-alpha"]["reasons"]),
              f"第二次调用应看到新依赖并更新分类,实际 {ready2}")


def test_github_ready_and_list_order_preserved() -> None:
    """READ-06:GitHub list 按身份排序,ready/deps 保留后端返回顺序。"""

    with tempfile.TemporaryDirectory() as tmp:
        root = make_github_project(Path(tmp))
        fake = FakeTransport()
        # 后端返回非身份顺序
        fake.seed_issue("03-gamma", "丙任务")
        fake.seed_issue("01-alpha", "甲任务")
        fake.seed_issue("02-beta", "乙任务", deps="01-alpha")
        listed = [t["identity"] for t in mgs_records.list_tasks(root,
                                                               transport=fake)]
        check(listed == ["01-alpha", "02-beta", "03-gamma"],
              f"list 应按身份排序,实际 {listed}")
        ready = mgs_records.startable_tasks(root, transport=fake)
        check([i["identity"] for i in ready["startable"]] == ["03-gamma",
                                                              "01-alpha"],
              f"ready 应保留后端返回顺序,实际 "
              f"{[i['identity'] for i in ready['startable']]}")
        graph = mgs_records.task_dependencies(root, transport=fake)
        check(list(graph["edges"].keys()) == ["03-gamma", "01-alpha", "02-beta"],
              f"deps 应保留后端返回顺序,实际 {list(graph['edges'])}")


def test_github_ready_online_to_offline_preserves_source() -> None:
    """READ-05:有缓存 → 在线转离线 ready 保留来源/时间/缓存标识;
    无缓存时明确失败,不回退本地。"""

    with tempfile.TemporaryDirectory() as tmp:
        root = make_github_project(Path(tmp))
        cache = Path(tmp) / "cache"
        fake = FakeTransport()
        fake.seed_issue("01-alpha", "甲任务")
        online = mgs_records.startable_tasks(root, transport=fake,
                                             cache_dir=cache)
        check(online["cached"] is False and online["fetched_at"]
              and online["source"]["backend"] == "github-issues",
              f"在线 ready 应携带当前确认元信息,实际 "
              f"{ {k: online.get(k) for k in ('cached','fetched_at','source')} }")
        check([i["identity"] for i in online["startable"]] == ["01-alpha"],
              "在线 ready 应基于远端集合给出可开工集合")
        fake.offline()
        offline = mgs_records.startable_tasks(root, transport=fake,
                                              cache_dir=cache)
        check(offline["cached"] is True and offline["fetched_at"]
              and offline["source"]["backend"] == "github-issues"
              and offline.get("cache_note"),
              f"离线 ready 应保留缓存标识、时间与来源,实际 {offline}")
        check([i["identity"] for i in offline["startable"]] == ["01-alpha"],
              "离线 ready 仍应基于缓存给出可开工集合")

        # 无缓存 + 离线:明确失败,绝不回退本地
        fresh = FakeTransport()
        fresh.offline()
        try:
            mgs_records.startable_tasks(root, transport=fresh,
                                        cache_dir=Path(tmp) / "empty")
        except mgs_records.RecordsError as exc:
            check("远端不可用" in str(exc) and "无缓存" in str(exc),
                  f"无缓存离线应明确失败并说明原因:{exc}")
        else:
            check(False, "无缓存离线 ready 应报错,不回退本地任务来源")


# ---------- 票 05:列表与单任务读取复用配置并保持兼容(READ-05/06/11) ----------

class _ConfigReadCounter:
    """统计本次上下文中 mgs_records 读取 CONFIG 原文的次数。

    通过替换公开入口 ``load_config`` 计数:一次顶层 list/show 调用应当只
    解析一份 CONFIG 原文,不再按相对路径二次读取。
    """

    def __init__(self) -> None:
        self.count = 0

    def __enter__(self) -> "_ConfigReadCounter":
        import mgs_records as _records

        self._real = _records.load_config
        outer = self

        def counting(project_root, config_rel=mgs_records.DEFAULT_CONFIG_REL):
            outer.count += 1
            return outer._real(project_root, config_rel)

        _records.load_config = counting
        return self

    def __exit__(self, *exc: object) -> None:
        import mgs_records as _records

        _records.load_config = self._real


def test_github_list_show_read_config_once_and_necessary_reads() -> None:
    """AC1/AC4/READ-11:GitHub list/show 各自只读一次 CONFIG;

    show 保留集合定位、最新 Issue 详情与评论回读——不为减少请求删掉必要
    读取;list 按身份排序且在线结果不带离线标记。
    """

    with tempfile.TemporaryDirectory() as tmp:
        root = make_github_project(Path(tmp))
        fake = FakeTransport()
        fake.seed_issue("03-gamma", "丙任务")          # number 1
        issue = fake.seed_issue("01-alpha", "甲任务")  # number 2
        fake.seed_issue("02-beta", "乙任务", deps="01-alpha")  # number 3
        fake.comments[issue["number"]].append({
            "id": 9001, "body": "01-alpha 已交付证据。",
            "created_at": "2026-09-09T00:00:00Z"})

        with _ConfigReadCounter() as counter:
            listed = mgs_records.list_tasks(root, transport=fake)
        check(counter.count == 1,
              f"github list 应只读一次 CONFIG,实际 {counter.count} 次")
        check([t["identity"] for t in listed]
              == ["01-alpha", "02-beta", "03-gamma"],
              f"github list 应按身份排序,实际 {[t['identity'] for t in listed]}")
        check(isinstance(listed, list)
              and all("cached_read" not in t for t in listed),
              f"在线 list 不应带离线标记,实际 {listed}")

        fake.calls.clear()
        with _ConfigReadCounter() as counter:
            task = mgs_records.read_task(root, "01-alpha", transport=fake)
        check(counter.count == 1,
              f"github show 应只读一次 CONFIG,实际 {counter.count} 次")
        gets = [path.split("?", 1)[0] for method, path, _ in fake.calls
                if method == "GET"]
        check(any(path.endswith("/issues") for path in gets),
              f"github show 应保留集合定位读取,实际 {gets}")
        check(f"/repos/mygamestudio/issue-accept/issues/{issue['number']}" in gets,
              f"github show 应读取具体 Issue 详情,实际 {gets}")
        check(f"/repos/mygamestudio/issue-accept/issues/{issue['number']}/comments"
              in gets,
              f"github show 应读取评论,实际 {gets}")
        check([r["ref"] for r in task["results"]] == ["#issuecomment-9001"],
              f"github show 应回读评论承载的结果,实际 {task['results']}")
        check(task.get("body_sha256") and task.get("html_url"),
              f"github show 应保留正文指纹与链接,实际 {task}")


def test_github_offline_list_show_metadata_and_no_marker_leak() -> None:
    """AC5/READ-05/06:离线 list/show 保留各自缓存标识与来源说明;

    离线标记只出现在 list 的独立投影中,不原地污染来源集合与其他调用结果;
    无缓存时按现有方式失败,不回退本地。
    """

    with tempfile.TemporaryDirectory() as tmp:
        root = make_github_project(Path(tmp))
        cache = Path(tmp) / "cache"
        fake = FakeTransport()
        seed = fake.seed_issue("01-alpha", "甲任务")
        fake.comments[seed["number"]].append({
            "id": 7, "body": "01-alpha 证据", "created_at": "2026-09-09T00:00:00Z"})
        online = mgs_records.list_tasks(root, transport=fake, cache_dir=cache)
        check(len(online) == 1 and "cached_read" not in online[0],
              "在线 list 不应带缓存标记")

        fake.offline()
        offline = mgs_records.list_tasks(root, transport=fake, cache_dir=cache)
        check(offline and all(t.get("cached_read") is True for t in offline),
              f"离线 list 应逐任务标注 cached_read,实际 {offline}")
        # 离线标记不污染来源集合:再取一次原始集合 payload,任务字典仍无该键
        payload = mgs_records.github_backend(
            root, transport=fake, cache_dir=cache).fetch_tasks()
        check(all("cached_read" not in t for t in payload["tasks"]),
              "list 的离线标记是独立投影,不得原地污染来源集合")

        task = mgs_records.read_task(root, "01-alpha", transport=fake,
                                     cache_dir=cache)
        check(task.get("cached_read") is True
              and "缓存" in task.get("cached_note", "")
              and task.get("body_sha256"),
              f"离线 show 应保留缓存标识、说明与正文指纹,实际 {task}")
        check(task["results"] == [],
              "离线 show 评论未缓存,结果清单应为空(既有离线语义)")

        # 离线标记不污染其他调用结果:ready 条目不应携带该键
        ready = mgs_records.startable_tasks(root, transport=fake, cache_dir=cache)
        entries = ready["startable"] + ready["blocked"]
        check(entries and all("cached_read" not in e for e in entries),
              f"list 的离线标记不得污染 ready 结果,实际 {entries}")

        # 无缓存 + 离线:list/show 各自明确失败,不回退本地
        fresh = FakeTransport()
        fresh.offline()
        for call in (lambda: mgs_records.list_tasks(root, transport=fresh,
                                                    cache_dir=Path(tmp) / "empty"),
                     lambda: mgs_records.read_task(root, "01-alpha",
                                                   transport=fresh,
                                                   cache_dir=Path(tmp) / "empty")):
            try:
                call()
            except mgs_records.RecordsError as exc:
                check("远端不可用" in str(exc) and "无缓存" in str(exc),
                      f"无缓存离线应明确失败并说明原因:{exc}")
            else:
                check(False, "无缓存离线应报错,不回退本地任务来源")


# ---------- 票 07:阶段收口-后端专有规则复验(READ-08) ----------

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

        def _issue(identity: str, body_triage: str, labels: list[str],
                   number: int) -> dict:
            body = mgs_github.build_task_body(
                "冲突任务", identity, body_triage, "待执行",
                {"当前目标": "演示目标", "输入与基线": "GAME_DESIGN v1",
                 "本次交付": "示例交付", "允许修改范围": "src/**",
                 "所需能力": "文件读写", "完成标准": "示例标准",
                 "执行责任": "Agent(制作实现)", "验收方式": "代码级检查",
                 "依赖": "无"})
            issue = {"number": number, "id": 1000 + number, "title": "冲突任务",
                     "body": body, "labels": [{"name": n} for n in labels],
                     "state": "open", "state_reason": None,
                     "html_url": f"https://example.invalid/i/{number}"}
            fake.issues.append(issue)
            fake.comments[number] = []
            return issue

        # ① 标签与正文不一致:标签赢,并登记冲突
        _issue("01-conflict", "ready-for-agent", ["info"], 1)
        # ② 多标签:按后端返回顺序取第一个可识别语义(wont-do → wontfix 优先)
        _issue("02-multi", "ready-for-agent", ["wont-do", "agent-ready"], 2)
        # ③ 仅正文:按正文表达,无冲突
        _issue("03-body", "ready-for-human", [], 3)

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

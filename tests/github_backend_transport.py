#!/usr/bin/env python3
"""GitHub Issues 后端行为主题检查的共享替身传输层(任务票 11)。

集中各主题共用的本地替身与故障注入:GitHub REST 最小子集替身、
「读前收养只失败一次」的派生替身,以及待补索引登记内容构造与摘要
复算助手(仅用于自证复审碰撞对,见函数 docstring)。本 module 不访问
真实 GitHub,也不复制任何生产规则。
"""

import hashlib
import json
import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "plugin" / "records"))

import mgs_records  # noqa: E402
import mgs_github  # noqa: E402

REPO = "github.com/mygamestudio/issue-accept"


class FakeTransport:
    """GitHub REST 最小子集的本地替身:状态机 + 故障注入。

    故障注入:
    - fail(method, needle, kind):匹配的调用抛 TransportError;
    - drop(method, needle):**执行状态变更后**抛 timeout(模拟「已创建但
      响应丢失」——超时后结果不确定,须回读确认);
    - offline():此后全部调用抛 offline(模拟断连)。
    """

    def __init__(self, *, sub_issues_supported: bool = True,
                 dependencies_supported: bool = True) -> None:
        self.issues: list[dict] = []
        self.comments: dict[int, list[dict]] = {}
        self.sub_issues: dict[int, list[int]] = {}
        self.blocked_by: dict[int, list[int]] = {}  # child number -> blocker issue ids
        self.repo_labels: list[str] = ["triage", "info", "agent-ready",
                                       "human-ready", "wont-do"]
        # 交接可达检查用的绝对 URL → 状态码(未登记的绝对 URL 应答 404)
        self.remote_refs: dict[str, int] = {}
        self.auth_flags: list[bool | None] = []  # 每次调用的 auth 参数(凭据核对)
        self.sub_issues_supported = sub_issues_supported
        self.dependencies_supported = dependencies_supported
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
                 "assignees": [],
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
            return 200, [self._public_issue(item) for item in self.issues]
        if method == "GET" and path.startswith(base + "/labels"):
            return 200, [{"name": name} for name in self.repo_labels]
        match = re.match(rf"{base}/issues/(\d+)(/.*)?$", path)
        number = int(match.group(1)) if match else None
        rest = match.group(2) or "" if match else ""
        if match and rest == "/comments" and method == "GET":
            return 200, list(self.comments.get(number, []))
        if match and rest == "/comments" and method == "POST":
            comment = {"id": 5000 + number * 100 + len(self.comments[number]),
                       "body": body["body"], "created_at": "2026-09-08T12:00:00Z"}
            self.comments[number].append(comment)
            if self._dropped(method, path):
                raise mgs_github.TransportError("timeout", "injected drop (comment)")
            return 201, comment
        if match and rest == "/sub_issues":
            if not self.sub_issues_supported:
                return 404, {"message": "Sub-issues API not available (stand-in)"}
            if method == "GET":
                ids = self.sub_issues.get(number, [])
                return 200, [self._public_issue(self._issue_by_id(issue_id))
                             for issue_id in ids if self._issue_by_id(issue_id)]
            if method == "POST":
                child_id = body["sub_issue_id"]
                current = self.sub_issues.setdefault(number, [])
                if child_id not in current:
                    current.append(child_id)
                if self._dropped(method, path):
                    raise mgs_github.TransportError("timeout", "injected drop (sub_issues)")
                return 201, {}
        if match and rest == "/dependencies/blocked_by":
            if not self.dependencies_supported:
                return 404, {"message": "Issue dependencies not available (stand-in)"}
            if method == "GET":
                ids = self.blocked_by.get(number, [])
                return 200, [self._public_issue(self._issue_by_id(issue_id))
                             for issue_id in ids if self._issue_by_id(issue_id)]
            if method == "POST":
                blocker_id = body["issue_id"]
                current = self.blocked_by.setdefault(number, [])
                if blocker_id not in current:
                    current.append(blocker_id)
                if self._dropped(method, path):
                    raise mgs_github.TransportError(
                        "timeout", "injected drop (blocked_by)")
                return 201, {}
        if match and not rest:
            issue = self.issues[number - 1]
            if method == "GET":
                return 200, self._public_issue(issue)
            if method == "PATCH":
                for key in ("title", "body", "state", "state_reason"):
                    if key in body:
                        issue[key] = body[key]
                if "labels" in body:
                    issue["labels"] = [{"name": name} for name in body["labels"]]
                if "assignees" in body:
                    issue["assignees"] = [{"login": name}
                                          for name in body["assignees"]]
                return 200, self._public_issue(issue)
        if method == "POST" and path == base + "/issues":
            issue = {"number": len(self.issues) + 1,
                     "id": 1000 + len(self.issues) + 1,
                     "title": body["title"], "body": body["body"],
                     "labels": [{"name": name} for name in body.get("labels", [])],
                     "assignees": [{"login": name}
                                   for name in body.get("assignees", [])],
                     "state": "open", "state_reason": None,
                     "html_url": f"https://example.invalid/i/{len(self.issues) + 1}"}
            self.issues.append(issue)
            self.comments[issue["number"]] = []
            if self._dropped(method, path):
                raise mgs_github.TransportError("timeout", "injected drop (create)")
            return 201, self._public_issue(issue)
        if method == "GET" and path.startswith("/repos/") and path.endswith("/issues"):
            return 200, [self._public_issue(item) for item in self.issues]
        return 404, {"message": f"stand-in has no {method} {path}"}

    def _issue_by_id(self, issue_id: int | None) -> dict | None:
        for item in self.issues:
            if item.get("id") == issue_id:
                return item
        return None

    def _public_issue(self, issue: dict) -> dict:
        """附带原生负责人、父子与开放阻塞摘要,供回读。"""

        number = issue["number"]
        parent_number = next(
            (parent for parent, children in self.sub_issues.items()
             if issue.get("id") in children),
            None)
        parent = self.issues[parent_number - 1] if parent_number else None
        open_blockers = 0
        for blocker_id in self.blocked_by.get(number, []):
            blocker = self._issue_by_id(blocker_id)
            if blocker and blocker.get("state", "open") == "open":
                open_blockers += 1
        payload = dict(issue)
        payload["assignees"] = list(issue.get("assignees") or [])
        payload["issue_dependencies_summary"] = {
            "blocked_by": {"total_count": open_blockers}}
        if parent:
            payload["parent"] = {"id": parent["id"], "number": parent["number"],
                                 "title": parent["title"]}
        return payload


def backend_for(root: Path, transport: FakeTransport, cache: Path | None = None):
    return mgs_records.github_backend(root, transport=transport, cache_dir=cache)


def _issue_list_calls(fake: "FakeTransport") -> int:
    return sum(1 for method, path, _body in fake.calls
               if method == "GET" and path.split("?", 1)[0].endswith("/issues"))


def _pending_digest(identity: str, result_markdown: str) -> str:
    """复算待补索引登记文件名的 8 hex 短摘要(与实现同一构造形态,
    用于自证复审确定性碰撞对在当前实现下确实共用登记文件)。"""

    payload = json.dumps({"op": "append_result",
                          "args": {"identity": identity,
                                   "result_markdown": result_markdown},
                          "repo": "github.com/mygamestudio/issue-accept"},
                         ensure_ascii=False, sort_keys=True)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()[:8]


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


def _pending_registration_content(identity: str, result_markdown: str,
                                  comment_id: int, ref: str) -> dict:
    """构造一份形态健康的待补索引登记内容(与 mgs_result_publication 的
    record_pending_index 落盘形态一致),供逐路径分侧语义测试手工布置两布局
    的在盘状态。"""

    return {"op": "append_result",
            "args": {"identity": identity,
                     "result_markdown": result_markdown},
            "repo": REPO,
            "status": "已发布未补索引",
            "comment_id": comment_id, "ref": ref,
            "created_at": "2026-09-10T00:00:00+08:00",
            "cause": "timeout: injected timeout",
            "note": "测试构造的登记内容"}


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

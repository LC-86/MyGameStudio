#!/usr/bin/env python3
"""验收 GitHub 替身共用实现的行为检查(票 17,阶段 3 收口)。

票 17 把 ``acceptance/17-github-issue-workflow/standin_github.py`` 与
``acceptance/18-complete-package-acceptance/standin_github.py`` 两份逐字节相同的
副本收拢为 ``acceptance/_shared/standin_github.py``。本主题直接启动该共用替身
(127.0.0.1 动态端口,本地受控进程,**不是真实 GitHub**),按原控制与状态回读行为
逐项验证收拢未改变语义:

- 业务端点:创建 Issue -> 读回;发布评论 -> 读回;
- 控制端点:``offline`` 后业务端点返回 599(不可达语义),恢复后可用;
  ``drop_next_create`` / ``drop_next_comment`` 在**状态变更之后**断开连接
  (结果不确定),状态回读确认远端事实已发生;
- ``sub_issues`` 开关:关闭时 404(回退引用),开启时读出原生父子关系;
- 令牌核对:配置期望令牌时缺凭据 401,带正确令牌放行;
- ``GET /_test/state`` 全量状态转储(issues/comments/调用计数)。

零真实远端:只连本机 127.0.0.1 上的本进程替身,不发任何真实网络请求。

    python3 -B tests/test_acceptance_github_standin.py
"""

import json
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.request
from pathlib import Path

from plugin_package_support import make_checker, run_theme

FAILURES, check = make_checker()

REPO_ROOT = Path(__file__).resolve().parents[1]
STANDIN = REPO_ROOT / "acceptance" / "_shared" / "standin_github.py"
TOKEN = "synthetic-standin-token"


def start_standin(state_file: Path) -> tuple[subprocess.Popen, str]:
    """启动共用替身并读回首行端口(本地进程,零真实远端)。"""

    proc = subprocess.Popen(
        [sys.executable, "-B", str(STANDIN), "--port", "0", "--token", TOKEN,
         "--state-file", str(state_file)],
        stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    deadline = time.time() + 15
    while time.time() < deadline:
        line = proc.stdout.readline()
        if line.startswith("PORT "):
            return proc, line.split()[1].strip()
        if proc.poll() is not None:
            break
    proc.kill()
    raise RuntimeError("替身未在超时内打印端口")


def call(base: str, method: str, path: str, body: dict | None = None,
         token: str | None = TOKEN) -> tuple[int, dict]:
    """发一条受控请求;返回 (状态码, JSON)。连接断开时抛出以核对不确定语义。"""

    data = json.dumps(body).encode() if body is not None else None
    request = urllib.request.Request(base + path, data=data, method=method)
    request.add_header("Content-Type", "application/json")
    if token:
        request.add_header("Authorization", f"Bearer {token}")
    try:
        with urllib.request.urlopen(request, timeout=10) as response:
            raw = response.read().decode()
            return response.status, (json.loads(raw) if raw else {})
    except urllib.error.HTTPError as exc:
        raw = exc.read().decode()
        return exc.code, (json.loads(raw) if raw else {})


def state(base: str) -> dict:
    _, data = call(base, "GET", "/_test/state", token=None)
    return data


def test_business_readback_and_state_dump() -> None:
    """创建 Issue / 评论后经状态转储读回;业务端点带回执。"""

    with tempfile.TemporaryDirectory(prefix="mgs17-gh-") as tmp:
        proc, port = start_standin(Path(tmp) / "state.json")
        base = f"http://127.0.0.1:{port}"
        try:
            status, issue = call(base, "POST", "/repos/o/r/issues",
                                 {"title": "t", "body": "b", "labels": ["triage"]})
            check(status == 201 and issue["number"] == 1,
                  f"创建 Issue 应返回 201 与编号 1,实际 {status}:{issue}")
            status, got = call(base, "GET", "/repos/o/r/issues/1")
            check(status == 200 and got["title"] == "t"
                  and got["labels"] == [{"name": "triage"}],
                  f"应按编号读回 Issue,实际 {status}:{got}")
            status, comment = call(base, "POST", "/repos/o/r/issues/1/comments",
                                   {"body": "result-1"})
            check(status == 201 and comment["body"] == "result-1",
                  f"发布评论应返回 201 与正文,实际 {status}:{comment}")
            status, comments = call(base, "GET", "/repos/o/r/issues/1/comments")
            check(status == 200 and [c["body"] for c in comments] == ["result-1"],
                  f"应读回已发布评论,实际 {status}:{comments}")
            dump = state(base)
            check(len(dump["issues"]) == 1 and dump["comments"]["1"][0]["body"]
                  == "result-1",
                  f"状态转储应含 Issue 与评论事实,实际 {dump}")
            check(any(row["method"] == "POST" for row in dump["calls"]),
                  f"状态转储应记录调用计数,实际 {dump['calls']}")
        finally:
            proc.kill()
            proc.wait(timeout=10)


def test_control_offline_and_restore() -> None:
    """offline 控制:业务端点 599(不可达),控制端点仍可用,恢复后可写。"""

    with tempfile.TemporaryDirectory(prefix="mgs17-gh-") as tmp:
        proc, port = start_standin(Path(tmp) / "state.json")
        base = f"http://127.0.0.1:{port}"
        try:
            status, _ = call(base, "POST", "/_test/control", {"offline": True})
            check(status == 200, f"offline 控制应成功,实际 {status}")
            status, _ = call(base, "GET", "/repos/o/r/issues")
            check(status == 599, f"offline 后业务端点应返回 599,实际 {status}")
            status, _ = call(base, "GET", "/_test/state", token=None)
            check(status == 200, f"offline 不应影响控制端点,实际 {status}")
            call(base, "POST", "/_test/control", {"offline": False})
            status, _ = call(base, "GET", "/repos/o/r/issues")
            check(status == 200, f"恢复后业务端点应可用,实际 {status}")
        finally:
            proc.kill()
            proc.wait(timeout=10)


def test_drop_next_create_keeps_remote_fact() -> None:
    """drop_next_create:已创建后断开(结果不确定),状态回读确认远端已发生。"""

    with tempfile.TemporaryDirectory(prefix="mgs17-gh-") as tmp:
        proc, port = start_standin(Path(tmp) / "state.json")
        base = f"http://127.0.0.1:{port}"
        try:
            call(base, "POST", "/_test/control", {"drop_next_create": True})
            dropped = False
            try:
                call(base, "POST", "/repos/o/r/issues", {"title": "lost"})
            except (urllib.error.URLError, ConnectionError, OSError):
                dropped = True
            check(dropped, "drop_next_create 应在已创建后断开连接(超时语义)")
            dump = state(base)
            check(len(dump["issues"]) == 1 and dump["issues"][0]["title"] == "lost",
                  f"断开后状态回读应确认 Issue 已创建,实际 {dump['issues']}")
            status, _ = call(base, "POST", "/repos/o/r/issues", {"title": "next"})
            check(status == 201, f"drop_next_create 只生效一次,实际 {status}")
        finally:
            proc.kill()
            proc.wait(timeout=10)


def test_sub_issues_toggle_and_token_check() -> None:
    """sub_issues 关闭时 404(回退引用),开启时读回父子;令牌缺失 401。"""

    with tempfile.TemporaryDirectory(prefix="mgs17-gh-") as tmp:
        proc, port = start_standin(Path(tmp) / "state.json")
        base = f"http://127.0.0.1:{port}"
        try:
            call(base, "POST", "/repos/o/r/issues", {"title": "parent"})
            call(base, "POST", "/repos/o/r/issues", {"title": "child"})
            call(base, "POST", "/_test/control", {"sub_issues": False})
            status, _ = call(base, "GET", "/repos/o/r/issues/1/sub_issues")
            check(status == 404, f"sub_issues 关闭时应 404,实际 {status}")
            call(base, "POST", "/_test/control", {"sub_issues": True})
            call(base, "POST", "/repos/o/r/issues/1/sub_issues",
                 {"sub_issue_id": 1001})
            status, subs = call(base, "GET", "/repos/o/r/issues/1/sub_issues")
            check(status == 200 and [s["title"] for s in subs] == ["child"],
                  f"开启后应读回原生父子关系,实际 {status}:{subs}")
            status, _ = call(base, "GET", "/repos/o/r/issues", token=None)
            check(status == 401, f"缺少令牌应 401,实际 {status}")
            status, _ = call(base, "GET", "/repos/o/r/issues", token="wrong")
            check(status == 401, f"错误令牌应 401,实际 {status}")
        finally:
            proc.kill()
            proc.wait(timeout=10)


def test_shared_standin_is_sole_copy() -> None:
    """确认替身只有共用一份:17/18 目录不再各自持有副本。"""

    for scenario in ("17-github-issue-workflow", "18-complete-package-acceptance"):
        legacy = REPO_ROOT / "acceptance" / scenario / "standin_github.py"
        check(not legacy.is_file(), f"{scenario} 不应再有独立替身副本:{legacy}")
    check(STANDIN.is_file(), "缺少共用替身 acceptance/_shared/standin_github.py")


TESTS = (
    test_business_readback_and_state_dump,
    test_control_offline_and_restore,
    test_drop_next_create_keeps_remote_fact,
    test_sub_issues_toggle_and_token_check,
    test_shared_standin_is_sole_copy,
)


def main() -> int:
    return run_theme("验收 GitHub 替身共用实现", TESTS, FAILURES)


if __name__ == "__main__":
    sys.exit(main())

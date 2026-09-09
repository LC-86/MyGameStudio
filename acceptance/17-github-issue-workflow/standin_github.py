#!/usr/bin/env python3
"""任务票 17 验收用本地 GitHub 替身服务器(不是真实 GitHub)。

实现统一接口所需的 GitHub REST 最小子集,并带故障注入与状态转储:

- GET  /repos/{o}/{r}/issues?state=all          列出 Issue(含已关闭)
- POST /repos/{o}/{r}/issues                    创建 Issue
- GET  /repos/{o}/{r}/issues/{n}                读取 Issue
- PATCH /repos/{o}/{r}/issues/{n}               更新(body/labels/state/state_reason)
- GET/POST /repos/{o}/{r}/issues/{n}/comments   评论(结果与证据)
- GET  /repos/{o}/{r}/labels                    仓库标签
- GET/POST /repos/{o}/{r}/issues/{n}/sub_issues 原生父子关系(可开关)

测试控制端点(仅本机):
- POST /_test/control  {"offline": bool, "drop_next_create": bool,
                         "drop_next_comment": bool, "sub_issues": bool}
  offline:此后所有业务端点拒绝连接语义(HTTP 599,客户端判 offline);
  drop_next_create/drop_next_comment:**执行状态变更后**返回超时语义
  (HTTP 598),模拟「已创建/已发布但响应丢失」(超时后结果不确定);
  sub_issues:启用/禁用原生父子关系端点(禁用时 404,验证回退引用)。
- GET /_test/state      全量状态转储(issues/comments/sub_issues/调用计数/令牌出现)

用法:python3 standin_github.py [--port 0] [--token <期望的Bearer令牌>]
输出:首行打印实际监听端口(PORT <n>),供验收脚本读取。
"""

from __future__ import annotations

import argparse
import json
import os
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import re

LOCK = threading.Lock()
STATE_FILE = ""
STATE = {
    "issues": [],          # [{number,id,title,body,labels,state,state_reason}]
    "comments": {},        # number -> [{id, body, created_at}]
    "sub_issues": {},      # parent number -> [child issue id]
    "sub_issues_enabled": True,
    "offline": False,
    "drop_next_create": False,
    "drop_next_comment": False,
    "calls": [],           # [{method, path, auth}]
    "next_number": 1,
    "next_id": 1000,
}
TOKEN = ""


def _save() -> None:
    """把状态持久化到 STATE_FILE(远端「账本」跨重启保留;调用日志不落盘)。"""

    if not STATE_FILE:
        return
    import os
    snapshot = {k: v for k, v in STATE.items() if k != "calls"}
    tmp = STATE_FILE + ".tmp"
    with open(tmp, "w", encoding="utf-8") as fh:
        json.dump(snapshot, fh, ensure_ascii=False)
    os.replace(tmp, STATE_FILE)


def _load() -> None:
    if STATE_FILE and os.path.isfile(STATE_FILE):
        loaded = json.loads(open(STATE_FILE, encoding="utf-8").read())
        for key, value in loaded.items():
            STATE[key] = value
        # JSON 把整型键变成字符串:恢复为 Issue 编号整型键
        STATE["comments"] = {int(k): v for k, v in STATE["comments"].items()}
        STATE["sub_issues"] = {int(k): v
                               for k, v in STATE["sub_issues"].items()}


def _reply(handler, status: int, data) -> None:
    payload = json.dumps(data, ensure_ascii=False).encode("utf-8")
    handler.send_response(status)
    handler.send_header("Content-Type", "application/json")
    handler.send_header("Content-Length", str(len(payload)))
    handler.end_headers()
    handler.wfile.write(payload)


def _timeout(handler) -> None:
    """超时语义:连接直接断开(客户端按 timeout/结果不确定处理)。"""

    handler.close_connection = True
    try:
        handler.connection.close()
    except OSError:
        pass


class Handler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"

    def log_message(self, *args):  # noqa: A003 - 验收服务器静默
        pass

    # ----- 路由 -----

    def _route(self, method: str) -> None:
        path = self.path.split("?", 1)[0]
        auth = self.headers.get("Authorization", "")
        with LOCK:
            STATE["calls"].append({"method": method, "path": path,
                                   "auth": bool(auth)})
        if path == "/_test/state" and method == "GET":
            with LOCK:
                return _reply(self, 200, STATE)
        if path == "/_test/control" and method == "POST":
            body = self._read_body()
            with LOCK:
                if "offline" in body:
                    STATE["offline"] = bool(body["offline"])
                if "drop_next_create" in body:
                    STATE["drop_next_create"] = bool(body["drop_next_create"])
                if "drop_next_comment" in body:
                    STATE["drop_next_comment"] = bool(body["drop_next_comment"])
                if "sub_issues" in body:
                    STATE["sub_issues_enabled"] = bool(body["sub_issues"])
                _save()
            return _reply(self, 200, {"ok": True})
        # 凭据核对(真实 API 同样要求):无令牌且配置了期望令牌 → 401
        if TOKEN and auth != f"Bearer {TOKEN}":
            return _reply(self, 401, {"message": "Bad credentials"})
        with LOCK:
            if STATE["offline"] and not path.startswith("/_test"):
                # 以 599 表达「服务不可达」;客户端 UrllibTransport 按
                # HTTPError 处理,非 200 状态在适配器里按传输故障路径收敛
                return _reply(self, 599, {"message": "stand-in offline"})
        if path == "/_test/ping":
            return _reply(self, 200, {"ok": True})

        match = re.fullmatch(r"/repos/([A-Za-z0-9._-]+)/([A-Za-z0-9._-]+)/(.+)",
                             path)
        if not match:
            return _reply(self, 404, {"message": f"no route {path}"})
        _owner, _repo, rest = match.groups()
        if rest == "issues":
            if method == "GET":
                with LOCK:
                    return _reply(self, 200, list(STATE["issues"]))
            if method == "POST":
                body = self._read_body()
                with LOCK:
                    issue = {"number": STATE["next_number"],
                             "id": STATE["next_id"],
                             "title": body.get("title", ""),
                             "body": body.get("body", ""),
                             "labels": [{"name": n}
                                        for n in body.get("labels", [])],
                             "state": "open", "state_reason": None,
                             "html_url": "https://standin.invalid/issues/"
                                         f"{STATE['next_number']}"}
                    STATE["next_number"] += 1
                    STATE["next_id"] += 1
                    STATE["issues"].append(issue)
                    STATE["comments"][issue["number"]] = []
                    dropped = STATE["drop_next_create"]
                    if dropped:
                        STATE["drop_next_create"] = False
                    _save()
                if dropped:
                    return _timeout(self)  # 已创建但响应丢失
                return _reply(self, 201, issue)
        issue_match = re.fullmatch(r"issues/(\d+)(?:/(comments|sub_issues))?", rest)
        if issue_match:
            number = int(issue_match.group(1))
            kind = issue_match.group(2)
            with LOCK:
                if not 1 <= number <= len(STATE["issues"]):
                    return _reply(self, 404, {"message": "issue not found"})
            if kind is None:
                if method == "GET":
                    with LOCK:
                        return _reply(self, 200, STATE["issues"][number - 1])
                if method == "PATCH":
                    body = self._read_body()
                    with LOCK:
                        issue = STATE["issues"][number - 1]
                        for key in ("title", "body", "state", "state_reason"):
                            if key in body:
                                issue[key] = body[key]
                        if "labels" in body:
                            issue["labels"] = [{"name": n}
                                               for n in body["labels"]]
                        _save()
                        return _reply(self, 200, issue)
            if kind == "comments":
                if method == "GET":
                    with LOCK:
                        return _reply(self, 200,
                                      list(STATE["comments"].get(number, [])))
                if method == "POST":
                    body = self._read_body()
                    with LOCK:
                        comment = {"id": 50000 + number * 100
                                   + len(STATE["comments"][number]),
                                   "body": body.get("body", ""),
                                   "created_at": "2026-09-08T12:00:00Z"}
                        STATE["comments"][number].append(comment)
                        dropped = STATE["drop_next_comment"]
                        if dropped:
                            STATE["drop_next_comment"] = False
                        _save()
                    if dropped:
                        return _timeout(self)  # 已发布但响应丢失
                    return _reply(self, 201, comment)
            if kind == "sub_issues":
                with LOCK:
                    if not STATE["sub_issues_enabled"]:
                        return _reply(
                            self, 404,
                            {"message": "Sub-issues API not available"})
                if method == "GET":
                    with LOCK:
                        ids = STATE["sub_issues"].get(number, [])
                        subs = [i for i in STATE["issues"] if i["id"] in ids]
                        return _reply(self, 200, subs)
                if method == "POST":
                    body = self._read_body()
                    with LOCK:
                        STATE["sub_issues"].setdefault(number, []).append(
                            body.get("sub_issue_id"))
                        _save()
                        return _reply(self, 201, {})
        if rest == "labels" and method == "GET":
            names = ("triage", "info", "agent-ready", "human-ready", "wont-do")
            return _reply(self, 200, [{"name": n} for n in names])
        return _reply(self, 404, {"message": f"no {method} {path}"})

    def _read_body(self) -> dict:
        length = int(self.headers.get("Content-Length") or 0)
        raw = self.rfile.read(length) if length else b""
        return json.loads(raw) if raw else {}

    def do_GET(self):     # noqa: N802 - http.server 约定
        self._route("GET")

    def do_POST(self):    # noqa: N802
        self._route("POST")

    def do_PATCH(self):   # noqa: N802
        self._route("PATCH")


def main() -> int:
    global TOKEN, STATE_FILE
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--port", type=int, default=0)
    parser.add_argument("--token", default="", help="期望的 Bearer 令牌(可为空)")
    parser.add_argument("--state-file", default="",
                        help="状态持久化文件(跨重启保留远端账本)")
    args = parser.parse_args()
    TOKEN = args.token
    STATE_FILE = args.state_file
    _load()
    server = ThreadingHTTPServer(("127.0.0.1", args.port), Handler)
    print(f"PORT {server.server_address[1]}", flush=True)
    server.serve_forever()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

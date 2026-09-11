#!/usr/bin/env python3
"""受控替身:模拟 `codex app-server` 的 JSON-RPC over stdio(离线测试用)。

验收客户端以 ``subprocess.Popen([CODEX_BIN, "app-server"], ...)`` 启动它,
因此本脚本忽略 argv,只按行读取 JSON-RPC 请求并给出确定性响应。它不启动
真实模型、不访问网络、不读取真实凭据,行为完全由 ``MGS_FAKE_MODE`` 决定:

- ``default``(缺省):initialize/skills/list/thread/start 正常,并在 turn/start
  之后发出固定的 item/completed 流与 turn/completed(含重复项以核对去重)。
- ``lifecycle``:在 default 的事件流前追加 turn/started(扩展事件场景 03/04
  的证据筛选含 turn 生命周期通知)。
- ``no_thread_id``:thread/start 返回空对象(驱动客户端的线程 id 失败分支)。
- ``error_init``:initialize 返回 JSON-RPC error(驱动失败分支)。
- ``hold``:turn/start 后只发出 turn/started 与一条 agentMessage 事件,然后保持
  运行(永不发 turn/completed),供受控中断测试用审计阈值触发 kill 进程组。

副作用(可选,用于核对身份与生命周期):
- ``MGS_FAKE_CLIENTINFO_LOG``:initialize 时把收到的 clientInfo 追加写一行。
- ``MGS_FAKE_EXIT_LOG``:读线程遇到 stdin EOF(客户端关闭 stdin)时写一行。
"""

import json
import os
import signal
import subprocess
import sys

LOG_ENV = "MGS_FAKE_EXIT_LOG"


def log_exit(reason: str) -> None:
    path = os.environ.get(LOG_ENV)
    if path:
        with open(path, "a", encoding="utf-8") as fh:
            fh.write(reason + "\n")


def send(obj: dict) -> None:
    sys.stdout.write(json.dumps(obj, ensure_ascii=False) + "\n")
    sys.stdout.flush()


def default_events() -> list[dict]:
    """固定事件流:含重复 key 与重复文本,用于核对既有去重语义。"""

    def item(ident: str, kind: str, **extra) -> dict:
        return {"method": "item/completed",
                "params": {"item": {"id": ident, "type": kind, **extra}}}

    return [
        item("u1", "userMessage", text="$mygamestudio:game-code 请继续"),
        item("a1", "agentMessage", text="first agent reply"),
        item("c1", "commandExecution", command="echo hi", status="completed"),
        item("a2", "agentMessage", text="second agent reply"),
        item("a1", "agentMessage", text="first agent reply"),   # 重复 key
        item("a3", "agentMessage", text="second agent reply"),  # 重复文本
        {"method": "turn/completed", "params": {"turn": {"id": "t-fake"}}},
    ]


def handle(msg: dict, mode: str) -> None:
    method = msg.get("method")
    req_id = msg.get("id")
    if method == "initialize":
        if mode == "error_init":
            send({"jsonrpc": "2.0", "id": req_id,
                  "error": {"code": -32000, "message": "init denied"}})
            return
        log = os.environ.get("MGS_FAKE_CLIENTINFO_LOG")
        if log:
            info = msg.get("params", {}).get("clientInfo", {})
            with open(log, "a", encoding="utf-8") as fh:
                fh.write(json.dumps(info, ensure_ascii=False) + "\n")
        send({"jsonrpc": "2.0", "id": req_id,
              "result": {"userAgent": "fake-appserver/1"}})
    elif method == "skills/list":
        send({"jsonrpc": "2.0", "id": req_id, "result": {"data": [{"skills": [
            {"name": "game-code", "scope": "plugin", "pluginId": "mygamestudio",
             "path": "/plugin/skills/game-code/SKILL.md"},
            {"name": "game-status", "scope": "plugin", "pluginId": "mygamestudio",
             "path": "/plugin/skills/game-status/SKILL.md"},
        ]}]}})
    elif method == "thread/start":
        thread = {} if mode == "no_thread_id" else {"thread": {"id": "thread-fake"}}
        send({"jsonrpc": "2.0", "id": req_id, "result": thread})
    elif method == "turn/start":
        send({"jsonrpc": "2.0", "id": req_id, "result": {}})
        if mode == "hold":
            send({"method": "turn/started", "params": {"turn": {"id": "t-fake"}}})
            send({"method": "item/completed",
                  "params": {"item": {"id": "a1", "type": "agentMessage",
                                      "text": "partial agent reply"}}})
            child = subprocess.Popen([sys.executable, "-c",
                                      "import time; time.sleep(120)"])
            log_exit(f"child pid={child.pid}")  # 同一进程组:核对中断覆盖子进程
            log_exit("turn-started")  # 供中断测试同步:部分事件已发出、turn 未完成
            return  # 保持运行:不发 turn/completed,等待审计阈值触发中断
        if mode == "lifecycle":
            send({"method": "turn/started", "params": {"turn": {"id": "t-fake"}}})
        for event in default_events():
            send(event)
    else:
        send({"jsonrpc": "2.0", "id": req_id,
              "error": {"code": -32601, "message": "method not found"}})


def main() -> int:
    mode = os.environ.get("MGS_FAKE_MODE", "default")
    log_exit(f"started pid={os.getpid()}")

    def on_term(_signum, _frame):
        log_exit("terminated")
        raise SystemExit(0)

    signal.signal(signal.SIGTERM, on_term)
    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue
        try:
            msg = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(msg, dict):
            handle(msg, mode)
    log_exit("stdin-closed")
    return 0


if __name__ == "__main__":
    sys.exit(main())

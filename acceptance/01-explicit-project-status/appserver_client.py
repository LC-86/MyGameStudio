#!/usr/bin/env python3
"""最小 Codex app-server JSON-RPC(stdio)客户端,用于任务票 01 的显式调用验收。

机制说明(实测 codex-cli 0.151.0):
- `codex exec` 只构造 UserInput::Text 且不解析 `$skill` 文本,显式技能无法注入;
- 交互界面与 app-server 的 turn 通道会解析用户文本中的 `$<技能名>` 提及,并把
  对应 SKILL.md 以 `<skill>` 块注入模型上下文——这是显式调用的真实通路;
- 因此本客户端通过 app-server 提交与界面一致的文本 turn(`$` 提及 + 指令),
  不伪造技能内容、不代读技能文件。

用法(HOME/CODEX_HOME 指向隔离环境):
  appserver_client.py skills --cwd <项目目录>
  appserver_client.py turn --cwd <项目目录> [--mention mygamestudio:game-status] \
      [--text "提示"] [--out <文件>] [--timeout 秒]
"""

import argparse
import json
import os
import subprocess
import sys
import threading
import time
from typing import Any

CODEX_BIN = os.environ.get("CODEX_BIN", "codex")


class AppServer:
    def __init__(self) -> None:
        self.proc = subprocess.Popen(
            [CODEX_BIN, "app-server"],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            env=os.environ.copy(),
        )
        self.lines: list[str] = []
        self._lock = threading.Lock()
        threading.Thread(target=self._reader, daemon=True).start()

    def _reader(self) -> None:
        assert self.proc.stdout
        for line in self.proc.stdout:
            with self._lock:
                self.lines.append(line.decode("utf-8", "replace").rstrip())

    def request(self, method: str, params: dict[str, Any] | None = None) -> dict[str, Any]:
        req_id = int(time.time() * 1000) % 100000 + 42
        payload: dict[str, Any] = {"jsonrpc": "2.0", "id": req_id, "method": method}
        if params is not None:
            payload["params"] = params
        assert self.proc.stdin
        self.proc.stdin.write((json.dumps(payload) + "\n").encode())
        self.proc.stdin.flush()
        deadline = time.time() + 60
        while time.time() < deadline:
            with self._lock:
                snapshot = list(self.lines)
            for line in snapshot:
                try:
                    msg = json.loads(line)
                except json.JSONDecodeError:
                    continue
                if msg.get("id") == req_id and "method" not in msg:
                    if "error" in msg:
                        raise RuntimeError(f"{method} failed: {msg['error']}")
                    return msg.get("result", {})
            time.sleep(0.2)
        raise TimeoutError(f"{method} timed out")

    def wait_turn_completed(self, timeout: float) -> list[dict[str, Any]]:
        deadline = time.time() + timeout
        agent_messages: list[str] = []
        seen: set[str] = set()
        while time.time() < deadline:
            with self._lock:
                snapshot = list(self.lines)
            for line in snapshot:
                try:
                    msg = json.loads(line)
                except json.JSONDecodeError:
                    continue
                if msg.get("method") != "item/completed":
                    continue
                item = msg.get("params", {}).get("item", {})
                key = f"{item.get('id')}:{item.get('type')}"
                if key in seen:
                    continue
                seen.add(key)
                if item.get("type") == "agentMessage":
                    text = item.get("text", "")
                    if text and text not in agent_messages:
                        agent_messages.append(text)
            with self._lock:
                snapshot = list(self.lines)
            for line in snapshot:
                try:
                    msg = json.loads(line)
                except json.JSONDecodeError:
                    continue
                if msg.get("method") == "turn/completed":
                    return agent_messages
            time.sleep(1)
        return agent_messages

    def close(self) -> None:
        try:
            if self.proc.stdin:
                self.proc.stdin.close()
            self.proc.terminate()
            self.proc.wait(timeout=10)
        except Exception:
            self.proc.kill()


def initialize(server: AppServer) -> None:
    server.request(
        "initialize",
        {"clientInfo": {"name": "mgs01-acceptance", "title": "MyGameStudio 01 acceptance", "version": "0.1.0"}},
    )


def cmd_skills(args: argparse.Namespace) -> int:
    server = AppServer()
    try:
        initialize(server)
        result = server.request("skills/list", {"cwd": args.cwd})
        data = result.get("data", [])
        groups = data if isinstance(data, list) else [data]
        for group in groups:
            for skill in group.get("skills", []):
                print(json.dumps(
                    {
                        "name": skill.get("name"),
                        "scope": skill.get("scope"),
                        "pluginId": skill.get("pluginId"),
                        "path": skill.get("path"),
                    },
                    ensure_ascii=False,
                ))
        return 0
    finally:
        server.close()


def cmd_turn(args: argparse.Namespace) -> int:
    server = AppServer()
    try:
        initialize(server)
        thread = server.request(
            "thread/start",
            {"cwd": args.cwd, "sandbox": "read-only", "ephemeral": False},
        )
        thread_id = (thread.get("thread") or {}).get("id")
        if not thread_id:
            raise RuntimeError(f"thread/start 未返回线程 id:{json.dumps(thread, ensure_ascii=False)[:200]}")
        prompt = (f"${args.mention} " if args.mention else "") + (args.text or "")
        server.request(
            "turn/start",
            {"threadId": thread_id, "input": [{"type": "text", "text": prompt}]},
        )
        messages = server.wait_turn_completed(args.timeout)
        report = "\n\n".join(messages)
        if args.out:
            with open(args.out, "w", encoding="utf-8") as fh:
                fh.write(report)
            print(f"wrote {len(report)} chars to {args.out}")
        else:
            print(report)
        return 0
    finally:
        server.close()


def main() -> int:
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="cmd", required=True)
    p_skills = sub.add_parser("skills")
    p_skills.add_argument("--cwd", required=True)
    p_skills.set_defaults(func=cmd_skills)
    p_turn = sub.add_parser("turn")
    p_turn.add_argument("--cwd", required=True)
    p_turn.add_argument("--mention", help="技能提及名,如 mygamestudio:game-status")
    p_turn.add_argument("--text")
    p_turn.add_argument("--out")
    p_turn.add_argument("--timeout", type=int, default=420)
    p_turn.set_defaults(func=cmd_turn)
    args = parser.parse_args()
    if args.cmd == "turn" and not args.mention and not args.text:
        raise SystemExit("需要 --mention 和/或 --text")
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())

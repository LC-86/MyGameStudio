#!/usr/bin/env python3
"""验收场景共享的 Codex app-server JSON-RPC(stdio)客户端核心。

本 module 集中标准事件验收场景共同需要的能力:子进程通信、请求响应归属、
事件等待与进程生命周期、事件证据输出。场景入口(``acceptance/*/appserver_client.py``)
只保留自身身份(clientInfo)、命令参数与事件筛选,经本 module 驱动完整调用。

事件增量消费:读取线程把 stdout 的每一行原样放入 ``AppServer.lines``,``request``
/``drain_events`` / ``wait_turn_completed`` 都经同一条 ``_message`` 惰性解码并按
行号缓存,因此每条输入只解码一次,轮询不会重复解码旧事件。

expand 迁移(票 13、票 14):标准事件场景(原 02/17/18,票 13)与最小场景
(原 01)、扩展事件场景(原 03/04,票 14)改用本 module,尚未迁移的场景继续
使用各自的旧实现;本 module 不改变普通完成、失败、超时、事件筛选、退出码与
子进程结束语义。场景差异(固定只读沙箱、事件筛选范围与 turn 生命周期通知)
经 ``run_turn`` 的显式参数保留,不强制统一。

用法(由场景入口经 sys.path 注入后导入):
  from appserver_core import AppServer, run_skills, run_turn
"""

import json
import os
import subprocess
import threading
import time
from typing import Any

# 请求响应等待上限(与旧实现一致,不在票 13 改为可配)。
REQUEST_TIMEOUT_SECONDS = 60.0
REQUEST_POLL_SECONDS = 0.2

# 事件证据默认保留的通知方法(标准事件场景);扩展事件场景经 event_methods 追加
# turn 生命周期通知,不改变标准场景的落盘结果。
DEFAULT_EVENT_METHODS = ("turn/completed",)


class AppServer:
    """app-server 子进程 + 已解码消息缓存(每条输入只解码一次)。

    ``lines`` / ``_lock`` / ``_drained`` 与旧实现同名同义,便于既有基线探针按
    模块属性替换计时器与解码计数器后直接构造实例;解码缓存 ``_decoded`` 按
    行号惰性建立,同一行最多解码一次。
    """

    def __init__(self) -> None:
        bin_path = os.environ.get("CODEX_BIN", "codex")
        self.proc = subprocess.Popen(
            [bin_path, "app-server"],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            env=dict(os.environ),
        )
        self.lines: list[str] = []
        self._lock = threading.Lock()
        self._drained = 0
        self._decoded: dict[int, dict[str, Any] | None] = {}
        threading.Thread(target=self._reader, daemon=True).start()

    def _reader(self) -> None:
        assert self.proc.stdout
        for line in self.proc.stdout:
            with self._lock:
                self.lines.append(line.decode("utf-8", "replace").rstrip())

    def _line_count(self) -> int:
        with self._lock:
            return len(self.lines)

    def _message(self, index: int) -> dict[str, Any] | None:
        """返回第 index 行的解码结果;同一行只解码一次并缓存(None=非对象/坏行)。"""

        cache = self.__dict__.get("_decoded")
        if cache is None:  # object.__new__ 构造(基线探针)时补建缓存
            cache = {}
            self.__dict__["_decoded"] = cache
        if index in cache:
            return cache[index]
        if index >= self._line_count():
            return None
        raw = self.lines[index]
        msg: dict[str, Any] | None = None
        try:
            decoded = json.loads(raw)
        except json.JSONDecodeError:
            decoded = None
        if isinstance(decoded, dict):
            msg = decoded
        cache[index] = msg
        return msg

    def request(self, method: str, params: dict[str, Any] | None = None,
                timeout: float = REQUEST_TIMEOUT_SECONDS) -> dict[str, Any]:
        req_id = int(time.time() * 1000) % 100000 + 42
        payload: dict[str, Any] = {"jsonrpc": "2.0", "id": req_id, "method": method}
        if params is not None:
            payload["params"] = params
        assert self.proc.stdin
        self.proc.stdin.write((json.dumps(payload) + "\n").encode())
        self.proc.stdin.flush()
        deadline = time.time() + timeout
        while time.time() < deadline:
            for index in range(self._line_count()):
                msg = self._message(index)
                if msg is None or msg.get("id") != req_id or "method" in msg:
                    continue
                if "error" in msg:
                    raise RuntimeError(f"{method} failed: {msg['error']}")
                return msg.get("result", {})
            time.sleep(REQUEST_POLL_SECONDS)
        raise TimeoutError(f"{method} timed out")

    def drain_events(self, events: list[dict[str, Any]]) -> None:
        """把尚未消费的通知行追加进 events(每行只消费一次,轮询不产生重复)。"""

        while self._drained < self._line_count():
            msg = self._message(self._drained)
            self._drained += 1
            if msg is not None and "method" in msg:
                events.append(msg)

    def wait_turn_completed(self, timeout: float,
                            events: list[dict[str, Any]] | None = None
                            ) -> list[dict[str, Any]]:
        deadline = time.time() + timeout
        agent_messages: list[str] = []
        seen: set[str] = set()
        while time.time() < deadline:
            if events is not None:
                self.drain_events(events)
            for index in range(self._line_count()):
                msg = self._message(index)
                if msg is None or msg.get("method") != "item/completed":
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
            if self.turn_completed():
                return agent_messages
            time.sleep(1)
        return agent_messages

    def turn_completed(self) -> bool:
        for index in range(self._line_count()):
            msg = self._message(index)
            if msg is not None and msg.get("method") == "turn/completed":
                return True
        return False

    def close(self) -> None:
        try:
            if self.proc.stdin:
                self.proc.stdin.close()
            self.proc.terminate()
            self.proc.wait(timeout=10)
        except Exception:
            self.proc.kill()


def initialize(server: AppServer, client_info: dict[str, Any]) -> None:
    server.request("initialize", {"clientInfo": client_info})


def iter_skills(result: dict[str, Any]) -> list[dict[str, Any]]:
    data = result.get("data", [])
    groups = data if isinstance(data, list) else [data]
    return [skill for group in groups for skill in group.get("skills", [])]


def write_event_stream(events: list[dict[str, Any]], path: str,
                       keep_types: set[str] | None,
                       event_methods: tuple[str, ...] = DEFAULT_EVENT_METHODS) -> None:
    """落盘事件证据:item/completed 按 keep_types 过滤,另保留 event_methods。

    ``keep_types`` 为 None 时保留全部 item/completed 类型(扩展事件场景 03/04),
    否则只保留声明类型(标准事件场景 02/17/18)。场景各自持有筛选值,共享
    module 只负责按既有规则写文件,不新增原场景不存在的事件类型。
    """

    with open(path, "w", encoding="utf-8") as fh:
        for msg in events:
            method = msg.get("method")
            if method == "item/completed":
                item = msg.get("params", {}).get("item", {})
                if keep_types is None or item.get("type") in keep_types:
                    fh.write(json.dumps(msg, ensure_ascii=False) + "\n")
            elif method in event_methods:
                fh.write(json.dumps(msg, ensure_ascii=False) + "\n")


def run_skills(client_info: dict[str, Any], cwd: str) -> int:
    server = AppServer()
    try:
        initialize(server, client_info)
        result = server.request("skills/list", {"cwd": cwd})
        for skill in iter_skills(result):
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


def run_turn(client_info: dict[str, Any], *, cwd: str, sandbox: str, prompt: str,
             timeout: int, out: str | None, events_out: str | None,
             keep_types: set[str] | None,
             event_methods: tuple[str, ...] = DEFAULT_EVENT_METHODS) -> int:
    server = AppServer()
    try:
        initialize(server, client_info)
        thread = server.request(
            "thread/start",
            {"cwd": cwd, "sandbox": sandbox, "ephemeral": False},
        )
        thread_id = (thread.get("thread") or {}).get("id")
        if not thread_id:
            raise RuntimeError(
                f"thread/start 未返回线程 id:"
                f"{json.dumps(thread, ensure_ascii=False)[:200]}")
        server.request(
            "turn/start",
            {"threadId": thread_id, "input": [{"type": "text", "text": prompt}]},
        )
        events: list[dict[str, Any]] = []
        messages = server.wait_turn_completed(timeout, events)
        if events_out:
            write_event_stream(events, events_out, keep_types, event_methods)
        report = "\n\n".join(messages)
        if out:
            with open(out, "w", encoding="utf-8") as fh:
                fh.write(report)
            print(f"wrote {len(report)} chars to {out}")
        else:
            print(report)
        return 0
    finally:
        server.close()

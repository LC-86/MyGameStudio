#!/usr/bin/env python3
"""验收场景共享的 Codex app-server JSON-RPC(stdio)客户端核心。

本 module 集中标准事件验收场景共同需要的能力:子进程通信、请求响应归属、
事件等待与进程生命周期、事件证据输出。场景入口(``acceptance/*/appserver_client.py``)
只保留自身身份(clientInfo)、命令参数与事件筛选,经本 module 驱动完整调用。

事件增量消费:读取线程把 stdout 的每一行原样放入 ``AppServer.lines``,``request``
/``drain_events`` / ``wait_turn_completed`` 都经同一条 ``_message`` 惰性解码并按
行号缓存,因此每条输入只解码一次,轮询不会重复解码旧事件。

全共享(票 13–17,阶段 3 收口):十八个验收场景的标准事件族(原 02/17/18,票 13)、
最小场景(原 01)与扩展事件场景(原 03/04,票 14)、绝对阈值中断场景(原 05-14,
票 15)、相对阈值与完整闭环场景(原 15/16,票 16)全部改用本 module;票 17 已删除
工作区中被替代的旧客户端物理副本,本 module 是唯一的请求/等待/生命周期实现。
本 module 不改变普通完成、失败、超时、事件筛选、退出码与子进程结束语义。场景差异
(固定只读沙箱、事件筛选范围与 turn 生命周期通知、绝对/相对中断阈值与进程组)经
``run_turn`` 的显式参数保留,不强制统一。

等待策略按行为族保留(PR #28 复审 SP-1):普通完成场景(原 01-04/17/18)旧
实现以 1 秒粒度轮询(``NORMAL_POLL_SECONDS``);中断族(原 05-16)旧实现是固定
0.3 秒的单一等待循环,与是否配置 ``--watch-audit`` 无关——族内入口经
``run_turn(wait_poll_seconds=INTERRUPT_POLL_SECONDS)`` 声明该策略,未配置审计时
仍按 0.3 秒轮询,不回落到 1 秒粒度(1 秒粒度会漏收最后一次轮询之后、截止
之前到达的回复与完成事件,却仍以退出码 0 结束)。

中断阈值(票 15 绝对、票 16 相对):``run_turn`` 传 ``watch_audit``/``kill_after_allows``
时,等待 turn 完成的同时轮询审计文件,累计 allow 条目达到阈值即对本次子进程组发
SIGKILL 并以退出码 3 结束;事件流中没有 turn/completed,已取得的事件证据照常落盘。
默认 ``kill_relative=False`` 为**累计绝对次数**(含 turn 开始前已有的 allow,票 15
语义);``kill_relative=True`` 时以进入等待时的已有 allow 为**基数**,只计本轮新增
allow(票 16 语义),因此共享运行根中前序轮次的累计 allow 不会让新轮次一开始就误判
中断。两模式各自独立,不以历史累计混淆相对判断。审计文件缺失或不可读时旧实现按 0
处理,继续等待至超时。

用法(由场景入口经 sys.path 注入后导入):
  from appserver_core import AppServer, run_skills, run_turn
"""

import json
import os
import signal
import subprocess
import threading
import time
from typing import Any

# 公开合同(票 17 收口):场景入口与测试经这些名字使用共享实现。
__all__ = (
    "AppServer",
    "count_audit_allows",
    "initialize",
    "iter_skills",
    "run_skills",
    "run_turn",
    "write_event_stream",
    "REQUEST_TIMEOUT_SECONDS",
    "REQUEST_POLL_SECONDS",
    "NORMAL_POLL_SECONDS",
    "INTERRUPT_POLL_SECONDS",
    "DEFAULT_EVENT_METHODS",
    "INTERRUPTED_EXIT_CODE",
)

# 请求响应等待上限(与旧实现一致,不在票 13 改为可配)。
REQUEST_TIMEOUT_SECONDS = 60.0
REQUEST_POLL_SECONDS = 0.2
# 普通族(原 01-04/17/18)turn 等待的轮询间隔(与旧实现一致)。
NORMAL_POLL_SECONDS = 1.0
# 中断场景的轮询间隔(与旧 05-14 实现一致,保证中断时点响应性)。
INTERRUPT_POLL_SECONDS = 0.3

# 事件证据默认保留的通知方法(标准事件场景);扩展事件场景经 event_methods 追加
# turn 生命周期通知,不改变标准场景的落盘结果。
DEFAULT_EVENT_METHODS = ("turn/completed",)

# 受控中断模拟的退出码(旧 05-14 实现在审计 allow 达阈值 kill 进程组后返回此码)。
INTERRUPTED_EXIT_CODE = 3


def count_audit_allows(path: str) -> int:
    """累计审计文件中 ``op=write`` 且 ``decision=allow`` 的条目数(绝对次数)。

    文件缺失或不可读按 0 处理、坏行跳过(与旧 05-14 实现逐行同义),因此阈值
    未达到或审计异常都不会误触发中断。
    """

    try:
        with open(path, encoding="utf-8") as fh:
            count = 0
            for line in fh:
                line = line.strip()
                if not line:
                    continue
                try:
                    entry = json.loads(line)
                except json.JSONDecodeError:
                    continue
                if entry.get("op") == "write" and entry.get("decision") == "allow":
                    count += 1
            return count
    except OSError:
        return 0


class AppServer:
    """app-server 子进程 + 已解码消息缓存(每条输入只解码一次)。

    ``lines`` / ``_lock`` / ``_drained`` 与旧实现同名同义,便于既有基线探针按
    模块属性替换计时器与解码计数器后直接构造实例;解码缓存 ``_decoded`` 按
    行号惰性建立,同一行最多解码一次。

    ``new_session`` 只在绝对中断场景(原 05-14)传 True:codex 进程以独立进程组
    启动,使受控中断的 kill 能覆盖其子进程;默认 False 保持已迁移普通场景的
    子进程生命周期不变。
    """

    def __init__(self, *, new_session: bool = False) -> None:
        bin_path = os.environ.get("CODEX_BIN", "codex")
        self.proc = subprocess.Popen(
            [bin_path, "app-server"],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            env=dict(os.environ),
            start_new_session=new_session,
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

    def _collect_agent_messages(self, seen: set[str],
                                agent_messages: list[str]) -> None:
        """扫描已读行,按 item 去重追加 agentMessage 文本(普通与中断等待共用)。"""

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

    def wait_turn_completed(self, timeout: float,
                            events: list[dict[str, Any]] | None = None,
                            poll_seconds: float = NORMAL_POLL_SECONDS
                            ) -> list[dict[str, Any]]:
        """按 poll_seconds 粒度轮询等待 turn/completed,增量消费事件。

        默认 1 秒与普通族旧实现一致;中断族(原 05-16)旧实现是固定 0.3 秒的
        单一等待循环(与是否配置审计无关),经 ``run_turn`` 的
        ``wait_poll_seconds`` 传入 ``INTERRUPT_POLL_SECONDS`` 保留——粒度差异
        决定截止前最后时刻到达的回复与完成事件是否被收到(PR #28 复审 SP-1)。
        """

        deadline = time.time() + timeout
        agent_messages: list[str] = []
        seen: set[str] = set()
        while time.time() < deadline:
            if events is not None:
                self.drain_events(events)
            self._collect_agent_messages(seen, agent_messages)
            if self.turn_completed():
                return agent_messages
            time.sleep(poll_seconds)
        return agent_messages

    def kill_process_group(self) -> None:
        """对本次 codex 子进程所在的独立进程组发 SIGKILL(受控中断)。

        仅由绝对中断场景经 ``new_session=True`` 启动的子进程调用,作用范围限于
        本客户端自己创建的进程组;进程组不存在或无权限时退回单进程 kill。
        """

        try:
            os.killpg(os.getpgid(self.proc.pid), signal.SIGKILL)
        except (ProcessLookupError, PermissionError):
            self.proc.kill()

    def wait_turn_interruptible(self, timeout: float,
                                events: list[dict[str, Any]] | None = None,
                                watch_audit: str | None = None,
                                kill_after_allows: int = 0,
                                kill_relative: bool = False
                                ) -> tuple[list[str], bool]:
        """等待 turn/completed;审计 allow 达阈值即 kill 进程组并返回 killed=True。

        默认阈值为**累计绝对次数**(不减进入等待时的已有值,票 15 语义);
        ``kill_relative=True`` 时先取进入等待时的已有 allow 为基数,只在**本轮新增**
        allow 达 ``kill_after_allows`` 时中断(票 16 语义),因此共享运行根中前序轮次的
        累计 allow 不会误触发。未配置 watch_audit、阈值未达到或审计文件不可读时按普通
        等待处理,到超时返回已取得的 agent 消息。
        """

        deadline = time.time() + timeout
        agent_messages: list[str] = []
        seen: set[str] = set()
        baseline = (count_audit_allows(watch_audit)
                    if (watch_audit and kill_relative) else 0)
        while time.time() < deadline:
            if events is not None:
                self.drain_events(events)
            if (watch_audit
                    and count_audit_allows(watch_audit)
                    >= baseline + kill_after_allows):
                self.kill_process_group()
                return agent_messages, True
            self._collect_agent_messages(seen, agent_messages)
            if self.turn_completed():
                return agent_messages, False
            time.sleep(INTERRUPT_POLL_SECONDS)
        return agent_messages, False

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


def run_skills(client_info: dict[str, Any], cwd: str, *,
               new_session: bool = False) -> int:
    server = AppServer(new_session=new_session)
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
             event_methods: tuple[str, ...] = DEFAULT_EVENT_METHODS,
             watch_audit: str | None = None, kill_after_allows: int = 0,
             kill_relative: bool = False, new_session: bool = False,
             wait_poll_seconds: float | None = None) -> int:
    """跑一个 turn 并落盘报告/事件证据;配置 watch_audit 时支持中断阈值。

    中断(原 05-14,票 15 绝对;原 15/16,票 16 相对):``watch_audit`` +
    ``kill_after_allows`` 成对传入、``new_session=True`` 时,审计 allow 达阈值即 kill
    本子进程组,事件流不含 turn/completed,已取得证据照常落盘,并以退出码 3 结束
    (不再 close)。阈值为累计绝对次数;``kill_relative=True`` 时改为进入等待时的基数
    加本轮新增(共享运行根多轮场景)。其余场景沿用普通等待与退出码 0,行为不变。

    等待策略按行为族保留(PR #28 复审 SP-1):中断族(原 05-16)旧实现是固定
    0.3 秒的单一等待循环,与是否配置审计无关,族内入口传
    ``wait_poll_seconds=INTERRUPT_POLL_SECONDS``;未配置审计时不再回落到普通族
    的 1 秒粒度——1 秒粒度会漏收最后一次轮询之后、截止之前到达的回复与完成
    事件,却仍以退出码 0 结束。普通族(原 01-04/17/18)保持 1 秒默认。
    """

    server = AppServer(new_session=new_session)
    killed = False
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
        if watch_audit:
            messages, killed = server.wait_turn_interruptible(
                timeout, events, watch_audit=watch_audit,
                kill_after_allows=kill_after_allows,
                kill_relative=kill_relative)
        else:
            messages = server.wait_turn_completed(
                timeout, events,
                poll_seconds=(NORMAL_POLL_SECONDS if wait_poll_seconds is None
                              else wait_poll_seconds))
        if events_out:
            write_event_stream(events, events_out, keep_types, event_methods)
        report = "\n\n".join(messages)
        if out:
            with open(out, "w", encoding="utf-8") as fh:
                fh.write(report)
            print(f"wrote {len(report)} chars to {out}")
        else:
            print(report)
        if killed:
            print(f"INTERRUPTED: killed after >= {kill_after_allows} audit allow(s)")
            return INTERRUPTED_EXIT_CODE
        return 0
    finally:
        if not killed:
            server.close()

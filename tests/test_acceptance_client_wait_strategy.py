#!/usr/bin/env python3
"""验收客户端共享实现:各行为族等待策略与截止前延迟到达回归(PR #28 复审 SP-1)。

中断族(原 05-16)旧实现是固定 0.3 秒的单一等待循环,与是否配置
``--watch-audit`` 无关;普通族(原 01-04/17/18)旧实现为 1 秒轮询。共享核心经
``run_turn(wait_poll_seconds=…)`` 保留两族策略,本主题以三组回归固定:

- 接线:18 个入口未配置审计时的等待粒度(中断族 0.3、普通族 1.0);
- 虚拟时钟 A/B:截止前延迟到达的回复与完成事件,共享实现与各族基点旧实现
  (工作区无旧文件,按基点提交读取)同结果;
- 受控进程:替身 ``late-reply`` 模式下两族代表入口的证据齐全。

不启动真实模型、不访问网络。

    python3 -B tests/test_acceptance_client_wait_strategy.py
"""

import inspect
import json
import sys
import tempfile
import threading
from pathlib import Path
from types import SimpleNamespace

from acceptance_client_support import (
    BASIC_OLD_CLIENT, BASIC_SCENARIOS, EXTENDED_EVENT_SCENARIOS, FakeTime,
    FAMILY4_BASE_COMMIT, FAMILY4_OLD_CLIENT, FAMILY4_SCENARIOS,
    LEGACY_BASE_COMMIT, RELATIVE_BASE_COMMIT, RELATIVE_OLD_CLIENT,
    RELATIVE_SCENARIOS, STANDARD_SCENARIOS, client_path, load_git_module,
    load_module, load_shared_and_shells, read_jsonl, run_client,
    spy_calls_full,
)
from plugin_package_support import make_checker, run_theme

FAILURES, check = make_checker()

CORE_MODULE = Path(__file__).resolve().parents[1] / "acceptance" / "_shared" / "appserver_core.py"


class LateArrivalLines(list):
    """虚拟时钟驱动的行序列:到点后一次性追加延迟到达的回复与完成事件。

    ``AppServer`` 只经 ``len(self.lines)`` 探测新行,因此在 ``__len__`` 里按
    虚拟时钟放行追加行即可模拟「最后一次轮询之后、截止之前」才到达的证据,
    不启动子进程、不真实等待。
    """

    def __init__(self, late: list[str], clock: FakeTime, at: float) -> None:
        super().__init__()
        self._late = late
        self._clock = clock
        self._at = at
        self._released = False

    def __len__(self) -> int:
        if not self._released and self._clock.now >= self._at:
            self._released = True
            list.extend(self, self._late)
        return list.__len__(self)


def _drive_late_arrival(module, late: list[str], *, poll_seconds=None):
    """以虚拟时钟驱动一份实现的 turn 等待,返回(消息, 事件)。

    10 秒超时窗口内,回复与 turn/completed 在第 9.5 秒一次性到达:
    0.3 秒轮询的实现能收到,1 秒轮询的实现收不到。旧实现(基点提交)与共享
    实现经同一助手驱动,保证两侧口径一致。
    """

    server = object.__new__(module.AppServer)
    clock = FakeTime()
    server.lines = LateArrivalLines(late, clock, 9.5)
    server._lock = threading.Lock()
    server._drained = 0
    real_time = module.time
    module.time = clock
    events: list = []
    try:
        accepts_events = "events" in inspect.signature(
            module.AppServer.wait_turn_completed).parameters
        if not accepts_events:
            result = server.wait_turn_completed(10.0)
        elif poll_seconds is None:
            result = server.wait_turn_completed(10.0, events)
        else:
            result = server.wait_turn_completed(10.0, events,
                                                poll_seconds=poll_seconds)
    finally:
        module.time = real_time
    if isinstance(result, tuple):
        result = result[0]  # 旧族 4/5 实现返回 (messages, killed)
    return result, events


def test_family_wait_poll_seconds_wiring() -> None:
    """族等待策略接线:未配置审计时,中断族按 0.3 秒、普通族按 1 秒等待。

    PR #28 复审 SP-1:中断族(原 05-16)旧实现是固定 0.3 秒的单一等待循环,
    与是否配置 ``--watch-audit`` 无关;共享实现经入口转发的 wait_poll_seconds
    保留该策略,普通族(01-04/17/18)保持 1 秒默认不变。
    """

    core, all_shells = load_shared_and_shells(
        FAMILY4_SCENARIOS + RELATIVE_SCENARIOS + STANDARD_SCENARIOS
        + BASIC_SCENARIOS + EXTENDED_EVENT_SCENARIOS, prefix="mgs_wire_")
    family_shells = {scenario: all_shells[scenario]
                     for scenario in FAMILY4_SCENARIOS + RELATIVE_SCENARIOS}
    normal_shells = {scenario: all_shells[scenario]
                     for scenario in STANDARD_SCENARIOS + BASIC_SCENARIOS
                     + EXTENDED_EVENT_SCENARIOS}
    for scenario, shell in family_shells.items():
        with tempfile.TemporaryDirectory(prefix="mgs15-wire-") as tmp:
            namespace = dict(cwd=tmp, sandbox="read-only", mention=None,
                             text="t", timeout=5, out=None, events_out=None,
                             watch_audit=None, kill_after_allows=0)
            if scenario in RELATIVE_SCENARIOS:
                namespace["kill_relative"] = False
            rc, server = spy_calls_full(
                core, shell, "cmd_turn", SimpleNamespace(**namespace))
        check(rc == 0, f"{scenario} cmd_turn 应成功,实际 rc={rc}")
        check(server.wait_polls == [core.INTERRUPT_POLL_SECONDS],
              f"{scenario} 未配置审计时应按中断族 0.3 秒粒度等待,"
              f"实际 {server.wait_polls}")
    for scenario, shell in normal_shells.items():
        with tempfile.TemporaryDirectory(prefix="mgs13-wire-") as tmp:
            namespace = dict(cwd=tmp, mention=None, text="t", timeout=5,
                             out=None)
            if scenario != BASIC_SCENARIOS[0]:
                namespace["sandbox"] = "read-only"
                namespace["events_out"] = None
            rc, server = spy_calls_full(
                core, shell, "cmd_turn", SimpleNamespace(**namespace))
        check(rc == 0, f"{scenario} cmd_turn 应成功,实际 rc={rc}")
        check(server.wait_polls == [core.NORMAL_POLL_SECONDS],
              f"{scenario} 普通族应保持 1 秒默认等待粒度,实际 {server.wait_polls}")


def test_late_arrival_before_deadline_parity() -> None:
    """A/B:截止前延迟到达的证据,各实现按自己行为族的轮询粒度得出同结果。

    中断族旧实现(族 4/族 5,固定 0.3 秒)能收到第 9.5 秒到达的回复与完成
    事件;普通族旧实现(01,1 秒)收不到。共享实现按同族策略复现两侧:中断族
    不再因未配置审计回落到 1 秒粒度而漏收(PR #28 复审 SP-1 反例),普通族
    行为保持。
    """

    late = [json.dumps({"method": "item/completed",
                        "params": {"item": {"id": "a1", "type": "agentMessage",
                                            "text": "late reply"}}}),
            json.dumps({"method": "turn/completed",
                        "params": {"turn": {"id": "t"}}})]
    old_family4 = load_git_module(FAMILY4_OLD_CLIENT, "mgs15_old_late",
                                  commit=FAMILY4_BASE_COMMIT)
    old_relative = load_git_module(RELATIVE_OLD_CLIENT, "mgs16_old_late",
                                   commit=RELATIVE_BASE_COMMIT)
    old_basic = load_git_module(BASIC_OLD_CLIENT, "mgs13_old_late",
                                commit=LEGACY_BASE_COMMIT)
    core = load_module(CORE_MODULE, "mgs15_core_late")

    for name, module in (("族4旧实现", old_family4),
                         ("族5旧实现", old_relative)):
        messages, _ = _drive_late_arrival(module, late)
        check(messages == ["late reply"],
              f"{name}(0.3 秒轮询)应收到截止前延迟到达的回复,实际 {messages!r}")
    messages, events = _drive_late_arrival(
        core, late, poll_seconds=core.INTERRUPT_POLL_SECONDS)
    check(messages == ["late reply"],
          f"共享实现(0.3 秒)应收到延迟到达的回复,实际 {messages!r}")
    check(len(events) == 2,
          f"共享实现(0.3 秒)应同时消费到延迟到达的事件,实际 {len(events)} 条")
    messages, _ = _drive_late_arrival(old_basic, late)
    check(messages == [],
          "普通族旧实现(1 秒)在最后 0.5 秒到达时收不到(原行为)")
    messages, _ = _drive_late_arrival(core, late)
    check(messages == [],
          "共享实现默认(1 秒)对普通族行为保持一致,不扩大收集承诺")


def test_late_reply_controlled_process() -> None:
    """受控进程:回复与完成事件在截止前延迟到达时照常落盘(两族代表入口)。

    替身 ``late-reply`` 模式在应答 turn/start 后延迟 0.5 秒才发出最终回复与
    turn/completed;两族入口以 5 秒超时普通完成,报告与事件证据都不得缺失。
    """

    with tempfile.TemporaryDirectory(prefix="mgs15-late-") as tmp:
        tmpdir = Path(tmp)
        cases = ((FAMILY4_SCENARIOS[0], "中断族", True),
                 (BASIC_SCENARIOS[0], "普通族", False))
        for scenario, label, with_events in cases:
            out = tmpdir / f"{scenario[:2]}-report.md"
            events_out = tmpdir / f"{scenario[:2]}-events.jsonl"
            args = ["turn", "--cwd", str(tmpdir), "--text", "t",
                    "--out", str(out), "--timeout", "5"]
            if with_events:
                args += ["--events-out", str(events_out)]
            result = run_client(client_path(scenario), args, tmpdir,
                                mode="late-reply")
            check(result.returncode == 0,
                  f"{label}({scenario})延迟到达应普通完成:{result.stderr[:300]}")
            report = out.read_text(encoding="utf-8") if out.is_file() else ""
            check("late agent reply" in report,
                  f"{label} 应把截止前延迟到达的回复写入报告,实际 {report[:120]!r}")
            if with_events:
                methods = [row["method"] for row in read_jsonl(events_out)]
                check("turn/completed" in methods and "item/completed" in methods,
                      f"{label} 事件流应含延迟到达的回复与完成事件,实际 {methods}")


TESTS = (
    test_family_wait_poll_seconds_wiring,
    test_late_arrival_before_deadline_parity,
    test_late_reply_controlled_process,
)


def main() -> int:
    return run_theme("验收客户端共享实现(族等待策略与延迟到达回归)", TESTS, FAILURES)


if __name__ == "__main__":
    sys.exit(main())

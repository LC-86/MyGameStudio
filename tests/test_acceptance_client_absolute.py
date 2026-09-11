#!/usr/bin/env python3
"""验收客户端共享实现:绝对阈值中断场景(票 15,阶段 3)。

覆盖本票迁移的族 4 十个入口(``05-adopt-existing-project`` … ``14-playtest-and-
human-feedback``):它们迁移前逐字节同类(除场景身份/编号),共用「``--watch-audit``
+ ``--kill-after-allows`` 累计 allow **绝对阈值** + 独立进程组中断」语义。本票把它们
改接 ``acceptance/_shared/appserver_core.py``,各自身份与命令参数分别保留。

检查重点(对应五条验收):
- 十入口经真实 import 委托同一共享核心,身份与选项合同分别保留,未见遗漏调用;
- 绝对阈值中断经受控替身进程验证:kill 覆盖本次进程组(含孙进程)、退出码 3、
  事件流无 turn/completed、已取得的事件证据与部分报告照常落盘;
- 阈值未达到、无中断配置、审计文件缺失(异常)时按原普通行为处理,不中断;
- 共享核心不引入相对新增计数路径,尚未迁入的相对阈值客户端(15/16)继续可用;
- 旧新对照(A/B):基点族 4 旧实现与共享实现同输入可观察结果一致。

不启动真实模型、不访问网络;进程组操作只作用于测试自建的受控替身子进程。

    python3 -B tests/test_acceptance_client_absolute.py
"""

import inspect
import json
import sys
import tempfile
import threading
import time
from pathlib import Path
from types import SimpleNamespace

from acceptance_client_support import (
    FAMILY4_BASE_COMMIT, FAMILY4_OLD_CLIENT, FAMILY4_SCENARIOS,
    RELATIVE_SCENARIOS, CountingJson, append_audit_allow, client_path,
    load_git_module, load_module, load_shared_and_shells, pid_alive,
    read_jsonl, run_client, spy_calls_full, start_client,
)
from plugin_package_support import make_checker, run_theme

FAILURES, check = make_checker()

CORE_MODULE = Path(__file__).resolve().parents[1] / "acceptance" / "_shared" / "appserver_core.py"


class Clock:
    """确定性时钟:轮询间隔与超时按虚拟秒推进,不真实等待。"""

    def __init__(self) -> None:
        self.now = 0.0

    def time(self) -> float:
        return self.now

    def sleep(self, seconds: float) -> None:
        self.now += seconds


def wait_until(predicate, timeout: float = 30.0, interval: float = 0.05) -> bool:
    deadline = time.time() + timeout
    while time.time() < deadline:
        if predicate():
            return True
        time.sleep(interval)
    return predicate()


def wait_dead(pid: int, timeout: float = 10.0) -> bool:
    return wait_until(lambda: not pid_alive(pid), timeout=timeout)


def log_lines(path: Path) -> list[str]:
    return path.read_text(encoding="utf-8").splitlines() if path.is_file() else []


def popen_pid(lines: list[str]) -> int:
    for line in lines:
        if line.startswith("started pid="):
            return int(line.split("=")[1])
    return 0


def child_pid(lines: list[str]) -> int:
    for line in lines:
        if line.startswith("child pid="):
            return int(line.split("=")[1])
    return 0


def replay_interrupt(module, lines: list[str], audit: Path, threshold: int, *,
                     timeout: float = 5.0) -> tuple[list, bool, list]:
    """以合成行驱动中断等待(旧实现 wait_turn_completed / 新实现 wait_turn_interruptible)。

    返回(agent 消息, killed, 事件)。经 object.__new__ 构造(与票 01/13 同法),
    替换 module 的 time/json 为虚拟时钟与计数代理,kill_process_group 记为计数,
    不发送任何真实信号、不启动子进程。
    """

    server = object.__new__(module.AppServer)
    server.lines = list(lines)
    server._lock = threading.Lock()
    server._drained = 0
    kills: list[int] = []
    server.kill_process_group = lambda: kills.append(1)
    counter = {"count": 0}
    real_json, real_time = module.json, module.time
    module.json = CountingJson(real_json, counter)
    module.time = Clock()
    events: list[dict] = []
    try:
        if hasattr(server, "wait_turn_interruptible"):
            messages, killed = server.wait_turn_interruptible(
                timeout, events, watch_audit=str(audit), kill_after_allows=threshold)
        else:
            messages, killed = server.wait_turn_completed(
                timeout, events, watch_audit=str(audit), kill_after_allows=threshold)
    finally:
        module.json = real_json
        module.time = real_time
    return messages, killed, events


def test_family4_clients_share_implementation_and_keep_identity() -> None:
    """十入口经真实 import 委托同一共享核心;身份、参数与绝对中断选项分别保留。"""

    core, shells = load_shared_and_shells(FAMILY4_SCENARIOS, prefix="mgs15_shell_")
    check(len(shells) == 10, f"族 4 应有十份入口,实际 {len(shells)}")
    for scenario, shell in shells.items():
        check(shell.run_turn is core.run_turn and shell.run_skills is core.run_skills,
              f"{scenario} 未委托共享核心的 run_turn/run_skills")
        check(inspect.getmodule(shell.run_turn) is core,
              f"{scenario} 的 run_turn 不来自共享核心")

    # 转发探针:核对 turn/skills 全序列、new_session=True 与中断参数一并转发。
    for scenario, shell in shells.items():
        with tempfile.TemporaryDirectory(prefix="mgs15-fwd-") as tmp:
            audit = Path(tmp) / "audit.jsonl"
            rc, server = spy_calls_full(core, shell, "cmd_turn", SimpleNamespace(
                cwd=tmp, sandbox="workspace-write", mention="mygamestudio:game-init",
                text="x", timeout=5, out=None, events_out=None,
                watch_audit=str(audit), kill_after_allows=2))
        check(rc == 0, f"{scenario} cmd_turn 应成功,实际 rc={rc}")
        check(server.calls[:3] == ["initialize", "thread/start", "turn/start"]
              and server.calls[-1] == "close",
              f"{scenario} turn 调用应完整转发,实际 {server.calls}")
        check(server.init_kwargs.get("new_session") is True,
              f"{scenario} 应以独立进程组启动子进程,实际 {server.init_kwargs}")
        check(any(str(call).startswith(f"wait_interruptible:{audit}:2")
                  for call in server.calls),
              f"{scenario} 应经共享核心的绝对中断等待,实际 {server.calls}")
        rc, server = spy_calls_full(core, shell, "cmd_skills", SimpleNamespace(cwd="/tmp"))
        check(rc == 0 and server.calls == ["initialize", "skills/list", "close"],
              f"{scenario} skills 调用应完整转发,实际 {server.calls}")

    # 身份逐个保留(迁移前常量)。
    for index, scenario in enumerate(FAMILY4_SCENARIOS, start=5):
        number = f"{index:02d}"
        check(shells[scenario].CLIENT_INFO["name"] == f"mgs{number}-acceptance",
              f"{scenario} 身份应保留 mgs{number}-acceptance,"
              f"实际 {shells[scenario].CLIENT_INFO}")


def test_family4_option_contract_absolute_only() -> None:
    """族 4 保留绝对中断选项与成对约束;未强加相对阈值选项(--kill-relative)。"""

    client = client_path(FAMILY4_SCENARIOS[0])
    with tempfile.TemporaryDirectory(prefix="mgs15-opt-") as tmp:
        tmpdir = Path(tmp)
        help_run = run_client(client, ["turn", "--help"], tmpdir)
        for option in ("--watch-audit", "--kill-after-allows", "--events-out",
                       "--sandbox"):
            check(option in help_run.stdout, f"族 4 入口应保留 {option}")
        check("--kill-relative" not in help_run.stdout,
              "族 4 入口不应新增相对阈值选项(--kill-relative 属票 16)")
        # 成对使用约束保持(旧实现原有校验)。
        only_threshold = run_client(client, ["turn", "--cwd", str(tmpdir),
                                             "--text", "t", "--kill-after-allows", "1"],
                                    tmpdir)
        check(only_threshold.returncode == 1,
              f"缺少 --watch-audit 时应以退出码 1 拒绝,实际 {only_threshold.returncode}")
        relative = run_client(client, ["turn", "--cwd", str(tmpdir), "--text", "t",
                                       "--kill-relative"], tmpdir)
        check(relative.returncode != 0, "族 4 入口不应接受 --kill-relative")
        # 缺少 --mention/--text 的参数错误保持。
        empty = run_client(client, ["turn", "--cwd", str(tmpdir)], tmpdir)
        check(empty.returncode == 1 and "需要 --mention" in empty.stderr,
              f"应保留原参数错误,实际 {empty.returncode}:{empty.stderr[:120]}")


def test_absolute_threshold_interrupt_controlled_process() -> None:
    """受控进程:审计累计达绝对阈值即中断——退出码 3、kill 覆盖进程组、无完成事件、证据保留。"""

    with tempfile.TemporaryDirectory(prefix="mgs15-int-") as tmp:
        tmpdir = Path(tmp)
        audit = tmpdir / "audit.jsonl"
        out = tmpdir / "report.md"
        events_out = tmpdir / "events.jsonl"
        identity = tmpdir / "identity.jsonl"
        exit_log = tmpdir / "exit.log"
        proc = start_client(
            client_path(FAMILY4_SCENARIOS[0]),
            ["turn", "--cwd", str(tmpdir), "--sandbox", "workspace-write",
             "--mention", "mygamestudio:game-init", "--text", "应用",
             "--out", str(out), "--events-out", str(events_out), "--timeout", "30",
             "--watch-audit", str(audit), "--kill-after-allows", "1"],
            tmpdir, mode="hold", identity_log=identity, exit_log=exit_log)
        # 同步点:替身已发出 turn/started 与部分事件、turn 未完成;随后推进审计阈值。
        # 留出一个轮询周期,保证客户端已消费中断前的事件与部分报告(与真实中断一致)。
        check(wait_until(lambda: "turn-started" in log_lines(exit_log)),
              "受控替身应进入 hold 模式并发出部分事件")
        time.sleep(1.0)
        append_audit_allow(audit, 1)
        stdout, stderr = proc.communicate(timeout=60)
        check(proc.returncode == 3,
              f"绝对阈值中断应以退出码 3 结束,实际 {proc.returncode}:{stderr[:300]}")
        check("INTERRUPTED" in stdout,
              f"中断应打印原中断提示,实际 {stdout[:200]!r}")
        lines = read_jsonl(events_out)
        methods = [row["method"] for row in lines]
        check(methods and "turn/completed" not in methods,
              f"中断事件流不得含 turn/completed(中断证据),实际 {methods}")
        check("turn/started" in methods and "item/completed" in methods,
              f"中断前已取得的证据应照常落盘,实际 {methods}")
        check(out.is_file() and out.read_text(encoding="utf-8") == "partial agent reply",
              f"中断前已取得的部分报告应保留,实际 "
              f"{out.read_text() if out.is_file() else '<缺失>'!r}")
        info = read_jsonl(identity)
        check(info and info[0]["name"] == "mgs05-acceptance",
              f"场景身份应保持 mgs05-acceptance,实际 {info}")
        lifecycle = log_lines(exit_log)
        pid, child = popen_pid(lifecycle), child_pid(lifecycle)
        check(pid and child, f"应记录受控替身与其子进程 pid,实际 {lifecycle}")
        check(wait_dead(pid), f"中断应结束 codex 子进程(pid {pid} 仍存活)")
        check(wait_dead(child), f"中断应覆盖本次进程组(子进程 pid {child} 仍存活)")


def test_no_interrupt_when_threshold_unmet_or_audit_missing() -> None:
    """阈值未达到、无中断配置、审计文件缺失(异常)时按原普通行为处理。"""

    client = client_path(FAMILY4_SCENARIOS[1])
    with tempfile.TemporaryDirectory(prefix="mgs15-noop-") as tmp:
        tmpdir = Path(tmp)
        # 无中断配置:普通完成,退出码 0。
        plain_out = tmpdir / "plain.md"
        plain = run_client(client, ["turn", "--cwd", str(tmpdir), "--text", "t",
                                    "--out", str(plain_out), "--timeout", "15"], tmpdir)
        check(plain.returncode == 0, f"无中断配置应普通完成:{plain.stderr[:300]}")
        check(plain_out.is_file() and plain_out.read_text(encoding="utf-8") ==
              "first agent reply\n\nsecond agent reply", "无中断配置报告应保持一致")
        # 审计文件缺失(异常按 0)+ 阈值 5:未达到,普通完成,不得中断。
        missing_events = tmpdir / "missing-events.jsonl"
        missing = run_client(
            client, ["turn", "--cwd", str(tmpdir), "--text", "t",
                     "--out", str(tmpdir / "missing.md"),
                     "--events-out", str(missing_events), "--timeout", "15",
                     "--watch-audit", str(tmpdir / "absent.jsonl"),
                     "--kill-after-allows", "5"], tmpdir)
        check(missing.returncode == 0,
              f"审计文件缺失且阈值未达到应普通完成,实际 {missing.returncode}")
        methods = [row["method"] for row in read_jsonl(missing_events)]
        check("turn/completed" in methods, f"未中断事件流应含 turn/completed,实际 {methods}")
        # 阈值未达到(已有 1 条 allow < 阈值 3):仍普通完成。
        audit = tmpdir / "partly.jsonl"
        append_audit_allow(audit, 1)
        partial = run_client(client, ["turn", "--cwd", str(tmpdir), "--text", "t",
                                      "--out", str(tmpdir / "partial.md"), "--timeout", "15",
                                      "--watch-audit", str(audit),
                                      "--kill-after-allows", "3"], tmpdir)
        check(partial.returncode == 0,
              f"阈值未达到应普通完成,实际 {partial.returncode}:{partial.stderr[:200]}")


def test_absolute_threshold_parity_old_new() -> None:
    """A/B:基点族 4 旧实现与共享实现同输入(阈值达到/未达到)可观察结果一致。"""

    old = load_git_module(FAMILY4_OLD_CLIENT, "mgs15_old_family4",
                          commit=FAMILY4_BASE_COMMIT)
    core = load_module(CORE_MODULE, "mgs15_core_parity")

    def item(ident: str, kind: str, **extra) -> str:
        return json.dumps({"method": "item/completed",
                           "params": {"item": {"id": ident, "type": kind, **extra}}})

    lines = [json.dumps({"method": "turn/started", "params": {"turn": {"id": "t"}}}),
             item("a1", "agentMessage", text="first agent reply"),
             item("a2", "agentMessage", text="second agent reply"),
             json.dumps({"method": "turn/completed", "params": {"turn": {"id": "t"}}})]

    with tempfile.TemporaryDirectory(prefix="mgs15-parity-") as tmp:
        tmpdir = Path(tmp)
        thresholds = tmpdir / "reached.jsonl"
        append_audit_allow(thresholds, 3)
        old_m, old_k, old_e = replay_interrupt(old, lines, thresholds, 3)
        new_m, new_k, new_e = replay_interrupt(core, lines, thresholds, 3)
        check(old_k and new_k, "阈值达到时旧新都应判定为中断(killed=True)")
        check(old_m == new_m == [], f"阈值在对首轮即达到时不应有部分消息:{old_m}/{new_m}")
        check(old_e == new_e, f"阈值达到时旧新事件消费应一致:{old_e}/{new_e}")

        below = tmpdir / "below.jsonl"
        append_audit_allow(below, 1)
        old_m, old_k, old_e = replay_interrupt(old, lines, below, 3)
        new_m, new_k, new_e = replay_interrupt(core, lines, below, 3)
        check(not old_k and not new_k, "阈值未达到时旧新都不应中断")
        check(old_m == new_m == ["first agent reply", "second agent reply"],
              f"阈值未达到时旧新 agent 消息应一致:{old_m}/{new_m}")
        check(old_e == new_e and len(new_e) == 4,
              f"阈值未达到时旧新事件消费应一致:{old_e}/{new_e}")


def test_shared_core_has_no_relative_counting_path() -> None:
    """绝对阈值语义保留在共享核心,不引入相对新增计数路径(相对阈值属票 16)。"""

    core = load_module(CORE_MODULE, "mgs15_core_semantics")
    check(hasattr(core, "count_audit_allows"), "共享核心应提供累计审计 allow 计数")
    params = inspect.signature(core.count_audit_allows).parameters
    check(list(params) == ["path"],
          f"累计计数不得接收基线/相对偏移,实际参数 {list(params)}")
    wait_params = inspect.signature(
        core.AppServer.wait_turn_interruptible).parameters
    check("kill_relative" not in wait_params,
          f"共享中断等待不得含相对阈值参数,实际 {list(wait_params)}")
    source = CORE_MODULE.read_text(encoding="utf-8")
    check("baseline" not in source and "kill_relative" not in source,
          "共享核心不得出现相对阈值(baseline/kill_relative)路径")


def test_relative_clients_still_available() -> None:
    """expand 红线:尚未迁入的相对阈值客户端(15/16)继续可用。"""

    for scenario in RELATIVE_SCENARIOS:
        path = client_path(scenario)
        check(path.is_file(), f"相对阈值客户端 {scenario} 应继续存在")
        source = path.read_text(encoding="utf-8")
        check("kill_relative" in source, f"{scenario} 应保留相对阈值实现")
        with tempfile.TemporaryDirectory(prefix="mgs15-rel-") as tmp:
            tmpdir = Path(tmp)
            out = tmpdir / "r.md"
            proc = run_client(path, ["turn", "--cwd", str(tmpdir), "--text", "t",
                                     "--out", str(out), "--timeout", "15"], tmpdir)
            check(proc.returncode == 0,
                  f"{scenario} 未迁入的相对客户端应继续通过:{proc.stderr[:200]}")
            check(out.is_file() and out.read_text(encoding="utf-8") ==
                  "first agent reply\n\nsecond agent reply",
                  f"{scenario} 报告应保持一致")


TESTS = (
    test_family4_clients_share_implementation_and_keep_identity,
    test_family4_option_contract_absolute_only,
    test_absolute_threshold_interrupt_controlled_process,
    test_no_interrupt_when_threshold_unmet_or_audit_missing,
    test_absolute_threshold_parity_old_new,
    test_shared_core_has_no_relative_counting_path,
    test_relative_clients_still_available,
)


def main() -> int:
    return run_theme("验收客户端共享实现(绝对阈值中断场景,票 15)", TESTS, FAILURES)


if __name__ == "__main__":
    sys.exit(main())

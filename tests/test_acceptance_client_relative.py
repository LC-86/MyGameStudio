#!/usr/bin/env python3
"""验收客户端共享实现:相对阈值与完整闭环场景(票 16,阶段 3)。

覆盖本票迁移的族 5 两份入口:``15-goal-change-concurrency-recovery`` 与
``16-producer-complete-loop``。它们迁移前逐字节同类(除场景身份/编号),共用
「``--watch-audit`` + ``--kill-after-allows`` 阈值 + ``--kill-relative`` 相对本轮
新增计数 + 独立进程组中断」语义。本票把它们改接
``acceptance/_shared/appserver_core.py``,各自身份与命令参数分别保留。

检查重点(对应四条验收):
- 两入口经真实 import 委托同一共享核心,身份与选项合同分别保留,未见遗漏调用;
- 相对语义保留:以进入等待时的已有 allow 为基数,只计本轮新增;共享运行根中
  前序轮次的累计 allow 不会让新轮次一开始就误判中断;达到本轮阈值即按原方式
  SIGKILL 本次进程组并以退出码 3 结束;
- 绝对模式、相对模式与非中断模式分别验证;事件筛选、报告、退出码与生命周期保持;
- 旧新对照(A/B):基点族 5 旧实现与共享实现同输入可观察结果一致。

不启动真实模型、不访问网络;进程组操作只作用于测试自建的受控替身子进程。

    python3 -B tests/test_acceptance_client_relative.py
"""

import inspect
import json
import sys
import tempfile
import time
from pathlib import Path
from types import SimpleNamespace

from acceptance_client_support import (
    RELATIVE_BASE_COMMIT, RELATIVE_OLD_CLIENT, RELATIVE_SCENARIOS,
    append_audit_allow, client_path, load_git_module, load_module,
    load_shared_and_shells, pid_alive, read_jsonl, replay_interrupt, run_client,
    spy_calls_full, start_client,
)
from plugin_package_support import make_checker, run_theme

FAILURES, check = make_checker()

CORE_MODULE = Path(__file__).resolve().parents[1] / "acceptance" / "_shared" / "appserver_core.py"
EXPECTED_REPORT = "first agent reply\n\nsecond agent reply"


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


def log_value(lines: list[str], prefix: str) -> str:
    for line in lines:
        if line.startswith(prefix):
            return line.split("=", 1)[1] if "=" in line else ""
    return ""


def interrupt_args(tmpdir: Path, audit: Path, threshold: int, *,
                   relative: bool, out: Path | None = None,
                   events: Path | None = None) -> list[str]:
    args = ["turn", "--cwd", str(tmpdir), "--sandbox", "workspace-write",
            "--mention", "mygamestudio:game-producer", "--text", "应用",
            "--timeout", "30", "--watch-audit", str(audit),
            "--kill-after-allows", str(threshold)]
    if relative:
        args.append("--kill-relative")
    if out is not None:
        args += ["--out", str(out)]
    if events is not None:
        args += ["--events-out", str(events)]
    return args


def run_round(client: Path, tmpdir: Path, audit: Path, threshold: int, *,
              relative: bool, mode: str = "hold") -> tuple:
    """跑一轮受控中断:同步点后确认「未提前中断」,再新增 allow 触发本轮中断。

    返回(进程返回码, stdout, 是否在新增 allow 前已退出, 事件方法序列, 报告文本)。
    用于共享运行根的多轮闭环:每轮都以同一审计文件的既有累计为基数。
    """

    out = tmpdir / f"report-{relative}.md"
    events_out = tmpdir / f"events-{relative}.jsonl"
    exit_log = tmpdir / f"exit-{relative}.log"
    if exit_log.exists():
        exit_log.unlink()
    proc = start_client(client, interrupt_args(tmpdir, audit, threshold,
                                               relative=relative, out=out,
                                               events=events_out),
                        tmpdir, mode=mode, exit_log=exit_log)
    check(wait_until(lambda: "turn-started" in log_lines(exit_log)),
          "受控替身应进入 hold 模式并发出部分事件")
    # 留出多个轮询周期:若历史累计被误当成本轮新增,进程会在此前退出。
    time.sleep(1.2)
    exited_early = proc.poll() is not None
    append_audit_allow(audit, threshold)  # 本轮新增恰达阈值
    stdout, stderr = proc.communicate(timeout=60)
    methods = [row["method"] for row in read_jsonl(events_out)]
    report = out.read_text(encoding="utf-8") if out.is_file() else ""
    check(proc.returncode == 3,
          f"本轮新增达阈值应以退出码 3 结束,实际 {proc.returncode}:{stderr[:200]}")
    return exited_early, stdout, proc.returncode, methods, report, exit_log


def test_relative_clients_share_implementation_and_keep_identity() -> None:
    """15/16 经真实 import 委托同一共享核心;身份、参数与相对中断选项分别保留。"""

    core, shells = load_shared_and_shells(RELATIVE_SCENARIOS, prefix="mgs16_shell_")
    check(len(shells) == 2, f"族 5 应有两份入口,实际 {len(shells)}")
    for scenario, shell in shells.items():
        check(shell.run_turn is core.run_turn and shell.run_skills is core.run_skills,
              f"{scenario} 未委托共享核心的 run_turn/run_skills")
        check(inspect.getmodule(shell.run_turn) is core,
              f"{scenario} 的 run_turn 不来自共享核心")
        check(shell.CLIENT_INFO["name"] ==
              ("mgs15-acceptance" if "15-" in scenario else "mgs16-acceptance"),
              f"{scenario} 身份未保留,实际 {shell.CLIENT_INFO}")

    for scenario, shell in shells.items():
        with tempfile.TemporaryDirectory(prefix="mgs16-fwd-") as tmp:
            audit = Path(tmp) / "audit.jsonl"
            rc, server = spy_calls_full(core, shell, "cmd_turn", SimpleNamespace(
                cwd=tmp, sandbox="workspace-write", mention="m:x", text="t",
                timeout=5, out=None, events_out=None,
                watch_audit=str(audit), kill_after_allows=2, kill_relative=True))
        check(rc == 0, f"{scenario} cmd_turn 应成功,实际 rc={rc}")
        check(server.calls[:3] == ["initialize", "thread/start", "turn/start"]
              and server.calls[-1] == "close",
              f"{scenario} turn 调用应完整转发,实际 {server.calls}")
        check(server.init_kwargs.get("new_session") is True,
              f"{scenario} 应以独立进程组启动子进程,实际 {server.init_kwargs}")
        check(any(str(call) == f"wait_interruptible:{audit}:2:relative=True"
                  for call in server.calls),
              f"{scenario} 应经共享核心的相对中断等待,实际 {server.calls}")
        rc, server = spy_calls_full(core, shell, "cmd_skills", SimpleNamespace(cwd="/tmp"))
        check(rc == 0 and server.calls == ["initialize", "skills/list", "close"],
              f"{scenario} skills 调用应完整转发,实际 {server.calls}")


def test_relative_option_contract_and_pairing() -> None:
    """族 5 保留相对阈值选项与成对约束;命令名、参数与错误退出码保持。"""

    for scenario in RELATIVE_SCENARIOS:
        client = client_path(scenario)
        with tempfile.TemporaryDirectory(prefix="mgs16-opt-") as tmp:
            tmpdir = Path(tmp)
            help_run = run_client(client, ["turn", "--help"], tmpdir)
            for option in ("--watch-audit", "--kill-after-allows", "--kill-relative",
                           "--events-out", "--sandbox"):
                check(option in help_run.stdout, f"{scenario} 入口应保留 {option}")
            only_threshold = run_client(client, ["turn", "--cwd", str(tmpdir),
                                                 "--text", "t",
                                                 "--kill-after-allows", "1"], tmpdir)
            check(only_threshold.returncode == 1,
                  f"{scenario} 缺少 --watch-audit 应以退出码 1 拒绝,"
                  f"实际 {only_threshold.returncode}")
            empty = run_client(client, ["turn", "--cwd", str(tmpdir)], tmpdir)
            check(empty.returncode == 1 and "需要 --mention" in empty.stderr,
                  f"{scenario} 应保留原参数错误,"
                  f"实际 {empty.returncode}:{empty.stderr[:120]}")


def test_relative_mode_ignores_prior_round_history_multiround() -> None:
    """完整闭环:共享运行根多轮;历史累计不误触发,每轮只计本轮新增。"""

    client = client_path(RELATIVE_SCENARIOS[0])
    with tempfile.TemporaryDirectory(prefix="mgs16-loop-") as tmp:
        tmpdir = Path(tmp)
        audit = tmpdir / "audit.jsonl"
        # 前序轮次已累计 5 条 allow(共享运行根的既有历史)。
        append_audit_allow(audit, 5)
        for round_index in (1, 2):
            early, stdout, rc, methods, report, exit_log = run_round(
                client, tmpdir, audit, 2, relative=True)
            check(not early,
                  f"第 {round_index} 轮:已有累计 allow 不得让新轮次开始即误判中断")
            check("INTERRUPTED" in stdout,
                  f"第 {round_index} 轮:应打印原中断提示,实际 {stdout[:200]!r}")
            check(methods and "turn/completed" not in methods,
                  f"第 {round_index} 轮:中断事件流不得含 turn/completed,实际 {methods}")
            check("turn/started" in methods and "item/completed" in methods,
                  f"第 {round_index} 轮:中断前证据应照常落盘,实际 {methods}")
            check(report == "partial agent reply",
                  f"第 {round_index} 轮:中断前部分报告应保留,实际 {report!r}")
            lifecycle = log_lines(exit_log)
            pid = log_value(lifecycle, "started pid=")
            child = log_value(lifecycle, "child pid=")
            check(pid and child and wait_dead(int(pid)) and wait_dead(int(child)),
                  f"第 {round_index} 轮:中断应结束本次进程组的子进程,实际 {lifecycle}")
        # 两轮各新增 2 条,审计应累计 5 + 2 + 2 = 9 条(每轮只消费本轮新增)。
        check(len(read_jsonl(audit)) == 9,
              f"审计累计应为 9(5 + 本轮各 2),实际 {len(read_jsonl(audit))}")


def test_modes_absolute_relative_non_interrupt() -> None:
    """绝对、相对与非中断三模式分别验证;报告、退出码与事件流保持。"""

    client = client_path(RELATIVE_SCENARIOS[0])
    with tempfile.TemporaryDirectory(prefix="mgs16-modes-") as tmp:
        tmpdir = Path(tmp)
        # 非中断模式:无 watch-audit,普通完成,事件含 turn/completed。
        plain_out = tmpdir / "plain.md"
        plain_events = tmpdir / "plain.jsonl"
        plain = run_client(client, ["turn", "--cwd", str(tmpdir), "--text", "t",
                                    "--out", str(plain_out),
                                    "--events-out", str(plain_events),
                                    "--timeout", "15"], tmpdir)
        check(plain.returncode == 0, f"非中断模式应普通完成:{plain.stderr[:300]}")
        check(plain_out.is_file() and plain_out.read_text(encoding="utf-8") ==
              EXPECTED_REPORT, "非中断模式报告应保持一致")
        methods = [row["method"] for row in read_jsonl(plain_events)]
        check("turn/completed" in methods,
              f"非中断模式事件流应含 turn/completed,实际 {methods}")
        # 相对模式:空审计 + 阈值 2,新增 2 条即中断(经 run_round)。
        rel_audit = tmpdir / "rel.jsonl"
        early, _, rc, rel_methods, _, _ = run_round(client, tmpdir, rel_audit, 2,
                                                    relative=True)
        check(not early and rc == 3 and "turn/completed" not in rel_methods,
              "相对模式:新增达阈值应中断且无完成事件")
        # 绝对模式对照:先累计 2 条,阈值 2 时进入即达阈(历史计入,不等新增)。
        abs_audit = tmpdir / "abs.jsonl"
        append_audit_allow(abs_audit, 2)
        abs_out = tmpdir / "abs.md"
        abs_events = tmpdir / "abs.jsonl"
        proc = start_client(client, interrupt_args(tmpdir, abs_audit, 2,
                                                   relative=False, out=abs_out,
                                                   events=abs_events),
                            tmpdir, mode="hold")
        stdout, stderr = proc.communicate(timeout=60)
        check(proc.returncode == 3,
              f"绝对模式:历史累计达阈值应中断,实际 {proc.returncode}:{stderr[:200]}")
        abs_methods = [row["method"] for row in read_jsonl(abs_events)]
        check("turn/completed" not in abs_methods,
              f"绝对模式中断事件流不得含 turn/completed,实际 {abs_methods}")
        check("INTERRUPTED" in stdout,
              f"绝对模式中断应打印原中断提示,实际 {stdout[:200]!r}")


def test_relative_threshold_parity_old_new() -> None:
    """A/B:基点族 5 旧实现与共享实现同输入(相对历史/相对即时/绝对)结果一致。"""

    old = load_git_module(RELATIVE_OLD_CLIENT, "mgs16_old_family5",
                          commit=RELATIVE_BASE_COMMIT)
    core = load_module(CORE_MODULE, "mgs16_core_parity")

    def item(ident: str, kind: str, **extra) -> str:
        return json.dumps({"method": "item/completed",
                           "params": {"item": {"id": ident, "type": kind, **extra}}})

    lines = [json.dumps({"method": "turn/started", "params": {"turn": {"id": "t"}}}),
             item("a1", "agentMessage", text="first agent reply"),
             item("a2", "agentMessage", text="second agent reply"),
             json.dumps({"method": "turn/completed", "params": {"turn": {"id": "t"}}})]

    with tempfile.TemporaryDirectory(prefix="mgs16-parity-") as tmp:
        tmpdir = Path(tmp)
        # 相对 + 已有累计(阈值 2,基数 2):本轮新增 0,旧新都不中断、消息一致。
        history = tmpdir / "history.jsonl"
        append_audit_allow(history, 2)
        old_m, old_k, old_e, _ = replay_interrupt(old, lines, history, 2,
                                                  kill_relative=True)
        new_m, new_k, new_e, _ = replay_interrupt(core, lines, history, 2,
                                                  kill_relative=True)
        check(not old_k and not new_k,
              "相对模式:历史累计已等于阈值时旧新都不应中断")
        check(old_m == new_m == ["first agent reply", "second agent reply"],
              f"相对模式历史下旧新 agent 消息应一致:{old_m}/{new_m}")
        check(old_e == new_e, f"相对模式历史下旧新事件应一致:{old_e}/{new_e}")

        # 相对 + 即时(阈值 0,基数 0):条件恒成立,旧新都立即中断且无消息。
        empty = tmpdir / "empty.jsonl"
        empty.write_text("", encoding="utf-8")
        old_m, old_k, old_e, old_kills = replay_interrupt(old, lines, empty, 0,
                                                          kill_relative=True)
        new_m, new_k, new_e, new_kills = replay_interrupt(core, lines, empty, 0,
                                                          kill_relative=True)
        check(old_k and new_k and old_kills == new_kills == 1,
              "相对模式阈值 0:旧新都应各 kill 一次")
        check(old_m == new_m == [], f"相对即时中断不应有 agent 消息:{old_m}/{new_m}")
        check(old_e == new_e, f"相对即时中断旧新事件应一致:{old_e}/{new_e}")

        # 绝对对照(阈值 2,已有 2):旧新都中断(killed=True),证明绝对仍计入历史。
        old_m, old_k, old_e, _ = replay_interrupt(old, lines, history, 2,
                                                  kill_relative=False)
        new_m, new_k, new_e, _ = replay_interrupt(core, lines, history, 2,
                                                  kill_relative=False)
        check(old_k and new_k, "绝对模式:历史累计达阈值时旧新都应中断")
        check(old_m == new_m == [], f"绝对即时中断不应有 agent 消息:{old_m}/{new_m}")
        check(old_e == new_e, f"绝对模式旧新事件应一致:{old_e}/{new_e}")


TESTS = (
    test_relative_clients_share_implementation_and_keep_identity,
    test_relative_option_contract_and_pairing,
    test_relative_mode_ignores_prior_round_history_multiround,
    test_modes_absolute_relative_non_interrupt,
    test_relative_threshold_parity_old_new,
)


def main() -> int:
    return run_theme("验收客户端共享实现(相对阈值与完整闭环场景,票 16)", TESTS, FAILURES)


if __name__ == "__main__":
    sys.exit(main())

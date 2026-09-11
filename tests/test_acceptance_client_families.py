#!/usr/bin/env python3
"""验收客户端共享实现:最小场景与扩展事件场景(票 14,阶段 3)。

覆盖本票迁移的三个入口:最小场景 ``01-explicit-project-status``(族 2)与扩展
事件场景 ``03-indirect-write-failure``、``04-initialize-local-project``(族 3)。
与票 13 的标准事件族(02/17/18)共用 ``acceptance/_shared/appserver_core.py``,但
各自身份、命令参数与事件筛选差异保留:

- 01 无 ``--sandbox`` / ``--events-out``(固定 read-only),未强加原场景不存在的选项;
- 03/04 保留全部 ``item/completed`` 类型并额外保留 turn 生命周期通知
  (``turn/started|turn/completed|turn/failed``),与 02 的四类过滤形成可观察差异。

受控替身进程验证完整调用、事件证据、身份与子进程结束;合成回放 adapter 对照
基点旧实现(工作区已无旧文件,按基点提交读取),校验旧新可观察结果一致。

    python3 -B tests/test_acceptance_client_families.py
"""

import inspect
import json
import sys
import tempfile
from pathlib import Path
from types import SimpleNamespace

from acceptance_client_support import (
    BASIC_OLD_CLIENT, BASIC_SCENARIOS, CORE_MODULE, EXTENDED_EVENT_SCENARIOS,
    EXTENDED_OLD_CLIENT, LEGACY_BASE_COMMIT, STANDARD_SCENARIOS, client_path,
    load_git_module, load_module, load_shared_and_shells, pid_alive, read_jsonl,
    replay_wait, run_client, spy_calls, synthetic_events,
)
from plugin_package_support import make_checker, run_theme

FAILURES, check = make_checker()

EXPECTED_REPORT = "first agent reply\n\nsecond agent reply"


def test_basic_and_extended_clients_share_implementation() -> None:
    """01/03/04 经真实 import 委托同一共享核心;族参数差异经入口保留。"""

    core, shells = load_shared_and_shells(
        BASIC_SCENARIOS + EXTENDED_EVENT_SCENARIOS, prefix="mgs14_shell_")
    for scenario, shell in shells.items():
        check(shell.run_turn is core.run_turn and shell.run_skills is core.run_skills,
              f"{scenario} 未委托共享核心的 run_turn/run_skills")
        check(inspect.getmodule(shell.run_turn) is core,
              f"{scenario} 的 run_turn 不来自共享核心")

    # 01:最小 turn 固定 read-only;无 --events-out;skills 正常转发。
    basic = shells[BASIC_SCENARIOS[0]]
    with tempfile.TemporaryDirectory(prefix="mgs14-fwd-") as tmp:
        out = Path(tmp) / "report.md"
        rc, calls, params = spy_calls(core, basic, "cmd_turn", SimpleNamespace(
            cwd=tmp, mention=None, text="hi", timeout=5, out=str(out)))
        check(rc == 0, f"{BASIC_SCENARIOS[0]} cmd_turn 应成功,实际 rc={rc}")
        check(calls == ["initialize", "thread/start", "turn/start", "close"],
              f"{BASIC_SCENARIOS[0]} turn 调用应完整转发,实际 {calls}")
        thread_params = params[calls.index("thread/start")]
        check(thread_params.get("sandbox") == "read-only",
              f"{BASIC_SCENARIOS[0]} 应固定 read-only,实际 {thread_params}")
        rc, calls, _ = spy_calls(core, basic, "cmd_skills", SimpleNamespace(cwd="/tmp"))
        check(rc == 0 and calls == ["initialize", "skills/list", "close"],
              f"{BASIC_SCENARIOS[0]} skills 调用应完整转发,实际 {calls}")

    # 03/04:可配沙箱传入共享核心;事件证据按扩展族筛选,不改成 02 的四类限制。
    for scenario in EXTENDED_EVENT_SCENARIOS:
        shell = shells[scenario]
        with tempfile.TemporaryDirectory(prefix="mgs14-fwd-") as tmp:
            events = Path(tmp) / "events.jsonl"
            rc, calls, params = spy_calls(core, shell, "cmd_turn", SimpleNamespace(
                cwd=tmp, mention="m:x", text="t", sandbox="workspace-write",
                timeout=5, out=None, events_out=str(events)))
            check(rc == 0, f"{scenario} cmd_turn 应成功,实际 rc={rc}")
            thread_params = params[calls.index("thread/start")]
            check(thread_params.get("sandbox") == "workspace-write",
                  f"{scenario} 应保留可配沙箱,实际 {thread_params}")
            check(len(events.read_text(encoding="utf-8").splitlines()) == 1,
                  f"{scenario} spy 模式应仍按共享核心写事件证据")


def test_basic_scenario_controlled_process_and_option_contract() -> None:
    """01 最小场景受控进程跑通,且未强加原场景不存在的选项(票 14)。"""

    with tempfile.TemporaryDirectory(prefix="mgs14-basic-") as tmp:
        tmpdir = Path(tmp)
        out = tmpdir / "report.md"
        identity = tmpdir / "identity.jsonl"
        exit_log = tmpdir / "exit.log"
        proc = run_client(
            client_path(BASIC_SCENARIOS[0]),
            ["turn", "--cwd", str(tmpdir), "--mention", "mygamestudio:game-status",
             "--text", "检查", "--out", str(out), "--timeout", "15"],
            tmpdir, identity_log=identity, exit_log=exit_log)
        check(proc.returncode == 0, f"01 turn 应成功退出:{proc.stderr[:300]}")
        check(out.is_file() and out.read_text(encoding="utf-8") == EXPECTED_REPORT,
              f"01 报告应与旧实现一致:{out.read_text() if out.is_file() else '<缺失>'!r}")
        info = read_jsonl(identity)
        check(info and info[0]["name"] == "mgs01-acceptance",
              f"01 场景身份应保持 mgs01-acceptance,实际 {info}")
        lifecycle = exit_log.read_text().splitlines() if exit_log.is_file() else []
        check(any(line.startswith("started") for line in lifecycle)
              and any(line in ("terminated", "stdin-closed") for line in lifecycle),
              f"01 结束路径应关闭子进程,生命周期日志:{lifecycle}")
        pid = int(lifecycle[0].split("=")[1]) if lifecycle else 0
        check(pid and not pid_alive(pid), f"01 子进程应结束,pid {pid} 仍存活")

        proc_skills = run_client(client_path(BASIC_SCENARIOS[0]),
                                 ["skills", "--cwd", str(tmpdir)], tmpdir)
        rows = [json.loads(x) for x in proc_skills.stdout.splitlines() if x.strip()]
        check(proc_skills.returncode == 0 and len(rows) == 2
              and all(set(r) == {"name", "scope", "pluginId", "path"} for r in rows),
              f"01 skills 输出字段应一致:{proc_skills.stdout!r}")

        # 选项合同:01 原场景无 --sandbox / --events-out,不得新增(argparse 应拒绝)。
        added = run_client(client_path(BASIC_SCENARIOS[0]),
                           ["turn", "--cwd", str(tmpdir), "--text", "t",
                            "--sandbox", "workspace-write"], tmpdir)
        check(added.returncode != 0, "01 不应接受原场景不存在的 --sandbox")
        added_ev = run_client(client_path(BASIC_SCENARIOS[0]),
                              ["turn", "--cwd", str(tmpdir), "--text", "t",
                               "--events-out", str(tmpdir / "e.jsonl")], tmpdir)
        check(added_ev.returncode != 0, "01 不应接受原场景不存在的 --events-out")


def test_extended_event_evidence_and_identity() -> None:
    """03/04 受控进程:全类型事件 + turn 生命周期证据,身份保持;02 对照不统一。"""

    for scenario, expected_name in ((EXTENDED_EVENT_SCENARIOS[0], "mgs03-acceptance"),
                                    (EXTENDED_EVENT_SCENARIOS[1], "mgs04-acceptance")):
        with tempfile.TemporaryDirectory(prefix="mgs14-ext-") as tmp:
            tmpdir = Path(tmp)
            out = tmpdir / "report.md"
            events_out = tmpdir / "events.jsonl"
            identity = tmpdir / "identity.jsonl"
            exit_log = tmpdir / "exit.log"
            proc = run_client(
                client_path(scenario),
                ["turn", "--cwd", str(tmpdir), "--sandbox", "workspace-write",
                 "--mention", "mygamestudio:game-code", "--text", "继续",
                 "--out", str(out), "--events-out", str(events_out), "--timeout", "15"],
                tmpdir, mode="lifecycle", identity_log=identity, exit_log=exit_log)
            check(proc.returncode == 0, f"{scenario} turn 应成功退出:{proc.stderr[:300]}")
            check(out.is_file() and out.read_text(encoding="utf-8") == EXPECTED_REPORT,
                  f"{scenario} 报告应与旧实现一致(含重复项去重)")
            lines = read_jsonl(events_out)
            methods = [m["method"] for m in lines]
            items = [m["params"]["item"]["type"] for m in lines
                     if m["method"] == "item/completed"]
            check(methods == (["turn/started"] + ["item/completed"] * 6
                              + ["turn/completed"]),
                  f"{scenario} 应保留全部 item 类型 + turn 生命周期,实际 {methods}")
            check(set(items) == {"userMessage", "agentMessage", "commandExecution"},
                  f"{scenario} 应保留全部 item 类型(无四类限制),实际 {items}")
            info = read_jsonl(identity)
            check(info and info[0]["name"] == expected_name,
                  f"{scenario} 场景身份应保持 {expected_name},实际 {info}")
            lifecycle = exit_log.read_text().splitlines() if exit_log.is_file() else []
            pid = int(lifecycle[0].split("=")[1]) if lifecycle else 0
            check(pid and not pid_alive(pid), f"{scenario} 子进程应结束,pid {pid} 仍存活")

    # 标准场景 02 对照:同输入下不保留 turn/started、只保留 KEEP_TYPES 四类。
    with tempfile.TemporaryDirectory(prefix="mgs14-std-") as tmp:
        tmpdir = Path(tmp)
        events_out = tmpdir / "events.jsonl"
        proc = run_client(
            client_path(STANDARD_SCENARIOS[0]),
            ["turn", "--cwd", str(tmpdir), "--sandbox", "workspace-write",
             "--text", "继续", "--events-out", str(events_out), "--timeout", "15"],
            tmpdir, mode="lifecycle")
        check(proc.returncode == 0, f"02 对照 turn 应成功退出:{proc.stderr[:300]}")
        methods = [m["method"] for m in read_jsonl(events_out)]
        check(methods.count("turn/started") == 0 and methods[-1] == "turn/completed"
              and len(methods) == 7,
              f"02 标准场景应只保留四类值项 + turn/completed,实际 {methods}")


def test_old_new_replay_parity() -> None:
    """expand 过渡期守卫:本票两族旧实现与共享客户端同输入可观察结果一致(A/B)。

    族 2(01,只比较 agent 消息)与族 3(03,比较消息与事件增量消费)。旧文件在
    工作区已不存在,旧实现按票 13 基点提交读取(与票 14 证据探针同口径);读取
    失败时本守卫响亮失败,不静默跳过。
    """

    lines = synthetic_events(50)
    lines.append(json.dumps(
        {"method": "turn/completed", "params": {"turn": {"id": "t"}}}))
    core = load_module(CORE_MODULE, "mgs14_core_parity")
    try:
        old_ext = load_git_module(EXTENDED_OLD_CLIENT, "mgs14_old_extended")
        old_basic = load_git_module(BASIC_OLD_CLIENT, "mgs14_old_basic")
    except Exception as exc:
        check(False, f"基点 {LEGACY_BASE_COMMIT[:12]} 缺少旧客户端源码:"
                     f"本守卫需显式处理:{exc}")
        return
    new_messages, new_events, _ = replay_wait(core, lines, collect_events=True)
    old_messages, old_events, _ = replay_wait(old_ext, lines, collect_events=True)
    check(old_messages == new_messages, "旧新 wait_turn_completed 的 agent 消息应一致")
    check(old_events == new_events, "旧新事件增量消费结果应一致")
    check(len(new_events) == 51, f"应消费 50 条事件 + turn/completed,实际 {len(new_events)}")
    old_basic_messages, _, _ = replay_wait(old_basic, lines, collect_events=False)
    check(old_basic_messages == new_messages,
          "最小场景(01)旧新 wait_turn_completed 的 agent 消息应一致")


def test_basic_and_extended_timeout_replay() -> None:
    """01/03/04 共享核心在无 turn/completed 的超时输入下返回已取得的 agent 消息。"""

    core = load_module(CORE_MODULE, "mgs14_core_timeout")
    lines = synthetic_events(3)
    messages, events, decodes = replay_wait(core, lines, timeout=2.0,
                                            collect_events=True)
    check(messages == ["message-0", "message-1", "message-2"],
          f"超时应返回已取得的 agent 消息,实际 {messages}")
    check(len(events) == 3 and decodes == 3,
          f"超时场景每条输入也应只解码一次,实际 decodes={decodes}")


TESTS = (
    test_basic_and_extended_clients_share_implementation,
    test_basic_scenario_controlled_process_and_option_contract,
    test_extended_event_evidence_and_identity,
    test_old_new_replay_parity,
    test_basic_and_extended_timeout_replay,
)


def main() -> int:
    return run_theme("验收客户端共享实现(最小+扩展事件场景,票 14)", TESTS, FAILURES)


if __name__ == "__main__":
    sys.exit(main())

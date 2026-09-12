#!/usr/bin/env python3
"""验收客户端共享实现的确定性检查:标准事件场景(票 13 建立,票 14 扩展)。

覆盖标准事件族(原 02/17/18)迁移到 ``acceptance/_shared/appserver_core.py`` 后
的行为:共享 module 只有一处请求/等待/生命周期实现;场景身份、命令参数与事件
筛选保留;受控替身进程(离线)验证完整调用、证据输出、失败退出码与子进程结束;
合成回放 adapter 验证每条新输入只解码一次、超时不重复解码,并与基点旧实现在同一
输入下对照。最小场景(01)与扩展事件场景(03/04)的检查见
``tests/test_acceptance_client_families.py``(票 14)。

    python3 -B tests/test_acceptance_client.py
"""

import inspect
import json
import sys
import tempfile
from pathlib import Path
from types import SimpleNamespace

from acceptance_client_support import (
    CORE_MODULE, LEGACY_BASE_COMMIT, MIGRATED_SCENARIOS,
    STANDARD_SCENARIOS, all_client_scenarios, client_path, load_git_module,
    load_module, load_shared_and_shells, local_client_implementations,
    pid_alive, read_jsonl, replay_wait, run_client, spy_calls, synthetic_events,
)
from plugin_package_support import make_checker, run_theme

FAILURES, check = make_checker()

EXPECTED_REPORT = "first agent reply\n\nsecond agent reply"
KEEP_TYPES = {"userMessage", "agentMessage", "commandExecution", "mcpToolCall"}
OLD_STANDARD_CLIENT = "acceptance/02-role-scoped-write/appserver_client.py"


def test_migrated_clients_share_implementation() -> None:
    """三份标准事件入口经真实 import 委托共享核心;相同输入可观察输出一致。"""

    check(CORE_MODULE.is_file(), "缺少共享客户端 acceptance/_shared/appserver_core.py")
    core, shells = load_shared_and_shells(STANDARD_SCENARIOS)
    for scenario, shell in shells.items():
        check(shell.AppServer is core.AppServer,
              f"{scenario} 未使用共享核心的 AppServer")
        check(shell.run_turn is core.run_turn and shell.run_skills is core.run_skills,
              f"{scenario} 未委托共享核心的 run_turn/run_skills")

    # 转发探针:替换共享核心的 AppServer 后调用薄壳入口,核对完整调用序列。
    for scenario, shell in shells.items():
        with tempfile.TemporaryDirectory(prefix="mgs13-fwd-") as tmp:
            out = Path(tmp) / "report.md"
            rc, calls, _ = spy_calls(core, shell, "cmd_turn", SimpleNamespace(
                cwd=tmp, sandbox="read-only", mention=None, text="hi",
                timeout=5, out=str(out), events_out=None))
            report = out.read_text(encoding="utf-8") if out.is_file() else None
        check(rc == 0, f"{scenario} cmd_turn 应成功,实际 rc={rc}")
        check(calls == ["initialize", "thread/start", "turn/start", "close"],
              f"{scenario} turn 调用应完整转发共享核心,实际 {calls}")
        check(report == "spy reply",
              f"{scenario} turn 输出应来自共享核心等待结果,实际 {report!r}")
        rc, calls, _ = spy_calls(core, shell, "cmd_skills", SimpleNamespace(cwd="/tmp"))
        check(rc == 0 and calls == ["initialize", "skills/list", "close"],
              f"{scenario} skills 调用应完整转发共享核心,实际 {calls}")

    # 行为一致性(非字节一致):三份入口相同受控输入下可观察输出相同。
    observed = {}
    for scenario in STANDARD_SCENARIOS:
        with tempfile.TemporaryDirectory(prefix="mgs13-eq-") as tmp:
            tmpdir = Path(tmp)
            out = tmpdir / "report.md"
            events_out = tmpdir / "events.jsonl"
            identity = tmpdir / "identity.jsonl"
            proc = run_client(
                client_path(scenario),
                ["turn", "--cwd", str(tmpdir), "--sandbox", "workspace-write",
                 "--mention", "mygamestudio:game-code", "--text", "继续",
                 "--out", str(out), "--events-out", str(events_out),
                 "--timeout", "15"],
                tmpdir, identity_log=identity)
            observed[scenario] = {
                "rc": proc.returncode,
                "report": out.read_text(encoding="utf-8") if out.is_file() else None,
                "events": (events_out.read_text(encoding="utf-8")
                           if events_out.is_file() else None),
                "identity": (identity.read_text(encoding="utf-8")
                             if identity.is_file() else None),
            }
    reference = observed[STANDARD_SCENARIOS[0]]
    for scenario in STANDARD_SCENARIOS:
        check(observed[scenario] == reference,
              f"{scenario} 与 {STANDARD_SCENARIOS[0]} 的可观察输出应一致:"
              f"rc={observed[scenario]['rc']}/{reference['rc']}")


def test_controlled_process_turn_report_events_and_identity() -> None:
    """受控替身进程跑完整 turn:报告、事件证据、身份与进程结束路径一致。"""

    with tempfile.TemporaryDirectory(prefix="mgs13-turn-") as tmp:
        tmpdir = Path(tmp)
        out = tmpdir / "report.md"
        events_out = tmpdir / "events.jsonl"
        identity_log = tmpdir / "identity.jsonl"
        exit_log = tmpdir / "exit.log"
        proc = run_client(
            client_path("02-role-scoped-write"),
            ["turn", "--cwd", str(tmpdir), "--sandbox", "workspace-write",
             "--mention", "mygamestudio:game-code", "--text", "继续",
             "--out", str(out), "--events-out", str(events_out), "--timeout", "15"],
            tmpdir, identity_log=identity_log, exit_log=exit_log)
        check(proc.returncode == 0, f"turn 应成功退出,实际 {proc.returncode}:{proc.stderr[:300]}")
        check(out.is_file() and out.read_text(encoding="utf-8") == EXPECTED_REPORT,
              f"报告应与旧实现一致(含重复项去重):{out.read_text() if out.is_file() else '<缺失>'!r}")
        check(f"wrote {len(EXPECTED_REPORT)} chars to {out}" in proc.stdout,
              f"out 模式下应打印写入摘要:{proc.stdout!r}")
        lines = read_jsonl(events_out)
        check(len(lines) == 7, f"事件证据应保留 6 条值项 + turn/completed,实际 {len(lines)}")
        for msg in lines[:-1]:
            item = msg["params"]["item"]
            check(msg["method"] == "item/completed" and item["type"] in KEEP_TYPES,
                  f"事件筛选应保留场景声明的类型,实际 {item.get('type')}")
        check(lines[-1]["method"] == "turn/completed", "事件证据最后应为 turn/completed")
        info = read_jsonl(identity_log)
        check(info and info[0]["name"] == "mgs02-acceptance",
              f"场景身份应保持 mgs02-acceptance,实际 {info}")
        lifecycle = exit_log.read_text().splitlines() if exit_log.is_file() else []
        check(any(line.startswith("started") for line in lifecycle)
              and any(line in ("terminated", "stdin-closed") for line in lifecycle),
              f"客户端结束路径应关闭子进程并让其退出,生命周期日志:{lifecycle}")
        pid = int(lifecycle[0].split("=")[1]) if lifecycle else 0
        check(pid and not pid_alive(pid),
              f"客户端子进程应在调用结束后结束,pid {pid} 仍存活")


def test_controlled_process_skills_output() -> None:
    """受控替身进程跑 skills:输出字段与旧实现一致。"""

    with tempfile.TemporaryDirectory(prefix="mgs13-skills-") as tmp:
        tmpdir = Path(tmp)
        proc = run_client(client_path("02-role-scoped-write"),
                          ["skills", "--cwd", str(tmpdir)], tmpdir)
        check(proc.returncode == 0, f"skills 应成功退出:{proc.stderr[:300]}")
        rows = [json.loads(x) for x in proc.stdout.splitlines() if x.strip()]
        check(len(rows) == 2, f"skills 应输出两条技能:{proc.stdout!r}")
        check(all(set(r) == {"name", "scope", "pluginId", "path"} for r in rows),
              f"skills 输出字段应为 name/scope/pluginId/path:{rows}")


def test_failure_paths_and_argument_contract() -> None:
    """失败退出码与参数语义保持:线程 id 缺失、initialize 失败、缺少入参。"""

    with tempfile.TemporaryDirectory(prefix="mgs13-fail-") as tmp:
        tmpdir = Path(tmp)
        client = client_path("02-role-scoped-write")
        args = ["turn", "--cwd", str(tmpdir), "--mention", "x:y", "--text", "t",
                "--timeout", "10"]
        no_thread = run_client(client, args, tmpdir, mode="no_thread_id")
        check(no_thread.returncode != 0, "thread/start 无 id 时进程应非零退出")
        check("thread/start 未返回线程 id" in no_thread.stderr,
              f"应保留原线程 id 失败信息:{no_thread.stderr[:300]}")
        init_err = run_client(client, args, tmpdir, mode="error_init")
        check(init_err.returncode != 0, "initialize 失败时进程应非零退出")
        check("initialize failed" in init_err.stderr,
              f"应保留原请求失败信息:{init_err.stderr[:300]}")
        empty = run_client(client, ["turn", "--cwd", str(tmpdir)], tmpdir)
        check(empty.returncode == 1, f"缺少 --mention/--text 应以退出码 1 结束,实际 {empty.returncode}")
        check("需要 --mention" in empty.stderr, f"应保留原参数错误:{empty.stderr[:200]}")


def _replay_decode(lines: list[str], *, timeout: float, collect_events: bool,
                   wait_times: int = 1) -> tuple[list, list, int]:
    """在同一共享客户端实例上重复等待,返回(末次消息, 事件, 累计解码数)。"""

    module = load_module(CORE_MODULE, "mgs13_core_replay")
    return replay_wait(module, lines, timeout=timeout,
                       collect_events=collect_events, wait_times=wait_times)


def test_decode_once_over_ten_polls() -> None:
    """1000 条固定事件、10 次轮询:每条输入只解码一次;再次等待不再解码旧事件。"""

    lines = synthetic_events(1000)
    messages, events, decodes = _replay_decode(lines, timeout=10.0, collect_events=True)
    check(len(events) == 1000, f"应消费到 1000 条事件,实际 {len(events)}")
    check(len(messages) == 1000, f"应得到 1000 条 agent 消息,实际 {len(messages)}")
    check(decodes == 1000,
          f"1000 条输入 x10 轮询应只解码 1000 次(票 01 基线为 21000),实际 {decodes}")
    messages2, _, decodes2 = _replay_decode(lines, timeout=10.0, collect_events=True,
                                            wait_times=2)
    check(decodes2 == 1000,
          f"第二次等待不应重新解码旧事件,累计应仍为 1000,实际 {decodes2}")
    check(len(messages2) == 1000, "第二次等待结果应保持一致")


def test_timeout_returns_partial_without_new_decodes() -> None:
    """超时:无 turn/completed 时返回已取得的 agent 消息,不重复解码。"""

    lines = synthetic_events(3)
    messages, events, decodes = _replay_decode(lines, timeout=2.0, collect_events=True)
    check(messages == ["message-0", "message-1", "message-2"],
          f"超时应返回已取得的 agent 消息,实际 {messages}")
    check(len(events) == 3 and decodes == 3,
          f"超时场景每条输入也应只解码一次,实际 decodes={decodes}")


def test_old_new_replay_parity() -> None:
    """旧实现对照(固定基点提交):标准族旧实现与共享客户端同输入结果一致(A/B)。

    标准族旧文件(02)在工作区已因票 17 收口删除;旧实现按不可变基点提交读取,
    不还原工作区。读取失败时本守卫响亮失败,不静默跳过——这是全共享时代仍保留的
    兼容性证据,而非 expand 过渡状态。
    """

    lines = synthetic_events(50)
    lines.append(json.dumps(
        {"method": "turn/completed", "params": {"turn": {"id": "t"}}}))
    try:
        old = load_git_module(OLD_STANDARD_CLIENT, "mgs13_old_standard")
    except Exception as exc:
        check(False, f"基点 {LEGACY_BASE_COMMIT[:12]} 缺少标准族旧客户端源码:"
                     f"本守卫需显式处理:{exc}")
        return
    core = load_module(CORE_MODULE, "mgs13_core_parity")
    old_messages, old_events, _ = replay_wait(old, lines, collect_events=True)
    new_messages, new_events, _ = replay_wait(core, lines, collect_events=True)
    check(old_messages == new_messages, "旧新 wait_turn_completed 的 agent 消息应一致")
    check(old_events == new_events, "旧新事件增量消费结果应一致")
    check(len(new_events) == 51, f"应消费 50 条事件 + turn/completed,实际 {len(new_events)}")


def test_all_scenarios_use_shared_core_no_local_implementation() -> None:
    """全共享守卫:18 场景入口全部委托共享核心,工作区无自带客户端实现副本。

    票 13–16 的 expand 过渡(新旧并存、按 ``find_legacy_client`` 查找未迁移场景)
    在票 17 收口后结束:旧物理副本已删除。本守卫改为正向确认——每份入口的
    ``run_turn``/``run_skills`` 都来自共享核心,且没有任何入口自带
    AppServer/request/等待与事件消费实现;同时确认 18 份入口无遗漏。
    """

    scenarios = all_client_scenarios()
    check(len(scenarios) == 18, f"应恰有 18 份客户端,实际 {len(scenarios)}:{scenarios}")
    core, shells = load_shared_and_shells(tuple(scenarios), prefix="mgs17_shell_")
    for scenario, shell in shells.items():
        check(shell.run_turn is core.run_turn and shell.run_skills is core.run_skills,
              f"{scenario} 未完整委托共享核心的 run_turn/run_skills")
        check(inspect.getmodule(shell.run_turn) is core,
              f"{scenario} 的 run_turn 不来自共享核心")
    offenders = local_client_implementations()
    check(offenders == [], f"仍有入口自带客户端实现(旧副本未清理):{offenders}")
    missing = [s for s in scenarios if s not in MIGRATED_SCENARIOS]
    check(missing == [], f"以下场景未登记为已迁移:{missing}")


TESTS = (
    test_migrated_clients_share_implementation,
    test_controlled_process_turn_report_events_and_identity,
    test_controlled_process_skills_output,
    test_failure_paths_and_argument_contract,
    test_decode_once_over_ten_polls,
    test_timeout_returns_partial_without_new_decodes,
    test_old_new_replay_parity,
    test_all_scenarios_use_shared_core_no_local_implementation,
)


def main() -> int:
    return run_theme("验收客户端共享实现(标准事件场景)", TESTS, FAILURES)


if __name__ == "__main__":
    sys.exit(main())

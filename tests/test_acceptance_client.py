#!/usr/bin/env python3
"""验收客户端共享实现的确定性检查(票 13,阶段 3 首票)。

覆盖标准事件场景(原 02/17/18)迁移到 ``acceptance/_shared/appserver_core.py``
后的行为:共享 module 只有一处请求/等待/生命周期实现;场景身份、命令参数与
事件筛选保留;受控替身进程(离线)验证完整调用、证据输出、失败退出码与子进程
结束;合成回放 adapter 验证每条新输入只解码一次、超时不重复解码,并与仍未
迁移的旧客户端在同一输入下对照。

    python3 -B tests/test_acceptance_client.py
"""

import json
import os
import sys
import tempfile
from pathlib import Path

from acceptance_client_support import (
    CORE_MODULE, MIGRATED_SCENARIOS, client_path, find_legacy_client,
    load_module, replay_wait, run_client, synthetic_events,
)
from plugin_package_support import make_checker, run_theme

FAILURES, check = make_checker()

EXPECTED_REPORT = "first agent reply\n\nsecond agent reply"
KEEP_TYPES = {"userMessage", "agentMessage", "commandExecution", "mcpToolCall"}


def _pid_alive(pid: int) -> bool:
    """子进程是否仍存活(仅用于生命周期核对;不用于任何信号发送)。"""

    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    return True


def test_migrated_clients_share_implementation() -> None:
    """三份标准事件入口字节一致、经共享 module 驱动、无自有等待实现。"""

    check(CORE_MODULE.is_file(), "缺少共享客户端 acceptance/_shared/appserver_core.py")
    core = CORE_MODULE.read_text(encoding="utf-8") if CORE_MODULE.is_file() else ""
    for needle in ("def request(", "def drain_events(", "def wait_turn_completed(",
                   "def close(", "def run_turn(", "def run_skills("):
        check(needle in core, f"共享客户端缺少 {needle}")
    sources = {}
    for scenario in MIGRATED_SCENARIOS:
        path = client_path(scenario)
        check(path.is_file(), f"缺少场景入口 {path}")
        text = path.read_text(encoding="utf-8") if path.is_file() else ""
        sources[scenario] = text
        check("appserver_core" in text, f"{scenario} 未引用共享客户端实现")
        check("def wait_turn_completed" not in text,
              f"{scenario} 不应再自带等待实现(应经共享 module)")
        check("def request" not in text, f"{scenario} 不应再自带请求实现")
        run_sh = (path.parent / "run.sh").read_text(encoding="utf-8")
        check("appserver_client.py" in run_sh, f"{scenario}/run.sh 应仍接入本入口")
    digests = {s: hash(t) for s, t in sources.items()}
    check(len(set(digests.values())) == 1,
          f"三个标准事件入口应逐字节一致:{digests}")
    # expand 红线:尚未迁移的场景必须仍有自己的旧实现。
    legacy = find_legacy_client()
    check(legacy is not None, "应至少保留一份未迁移旧客户端(expand:不删旧实现)")


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
        lines = [json.loads(x) for x in events_out.read_text(encoding="utf-8").splitlines()]
        check(len(lines) == 7, f"事件证据应保留 6 条值项 + turn/completed,实际 {len(lines)}")
        for msg in lines[:-1]:
            item = msg["params"]["item"]
            check(msg["method"] == "item/completed" and item["type"] in KEEP_TYPES,
                  f"事件筛选应保留场景声明的类型,实际 {item.get('type')}")
        check(lines[-1]["method"] == "turn/completed", "事件证据最后应为 turn/completed")
        info = [json.loads(x) for x in identity_log.read_text(encoding="utf-8").splitlines()]
        check(info and info[0]["name"] == "mgs02-acceptance",
              f"场景身份应保持 mgs02-acceptance,实际 {info}")
        lifecycle = exit_log.read_text().splitlines() if exit_log.is_file() else []
        check(any(line.startswith("started") for line in lifecycle)
              and any(line in ("terminated", "stdin-closed") for line in lifecycle),
              f"客户端结束路径应关闭子进程并让其退出,生命周期日志:{lifecycle}")
        pid = int(lifecycle[0].split("=")[1]) if lifecycle else 0
        check(pid and not _pid_alive(pid),
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
    """同一合成输入下,未迁移旧客户端与共享客户端的可观察结果一致(A/B)。"""

    legacy_path = find_legacy_client()
    if legacy_path is None:  # 迁移完成(如票 17 收口)后旧参照已不存在
        return
    lines = synthetic_events(50)
    lines.append(json.dumps(
        {"method": "turn/completed", "params": {"turn": {"id": "t"}}}))
    legacy = load_module(legacy_path, "mgs13_legacy_parity")
    core = load_module(CORE_MODULE, "mgs13_core_parity")
    old_messages, old_events, _ = replay_wait(legacy, lines, collect_events=True)
    new_messages, new_events, _ = replay_wait(core, lines, collect_events=True)
    check(old_messages == new_messages, "旧新 wait_turn_completed 的 agent 消息应一致")
    check(old_events == new_events, "旧新事件增量消费结果应一致")
    check(len(new_events) == 51, f"应消费 50 条事件 + turn/completed,实际 {len(new_events)}")


def test_unmigrated_scenario_still_passes() -> None:
    """expand 红线:未迁移场景的入口继续按旧实现独立通过(受控替身进程)。"""

    legacy = find_legacy_client()
    if legacy is None:
        return
    with tempfile.TemporaryDirectory(prefix="mgs13-legacy-") as tmp:
        tmpdir = Path(tmp)
        out = tmpdir / "report.md"
        proc = run_client(legacy,
                          ["turn", "--cwd", str(tmpdir), "--text", "检查",
                           "--out", str(out), "--timeout", "15"], tmpdir)
        check(proc.returncode == 0,
              f"未迁移场景应经旧实现成功退出:{proc.stderr[:300]}")
        check(out.is_file() and out.read_text(encoding="utf-8") == EXPECTED_REPORT,
              "未迁移场景的可观察报告应与共享实现一致(同输入)")
        check(legacy.parent.name not in MIGRATED_SCENARIOS,
              "对照必须取未迁移场景")


TESTS = (
    test_migrated_clients_share_implementation,
    test_controlled_process_turn_report_events_and_identity,
    test_controlled_process_skills_output,
    test_failure_paths_and_argument_contract,
    test_decode_once_over_ten_polls,
    test_timeout_returns_partial_without_new_decodes,
    test_old_new_replay_parity,
    test_unmigrated_scenario_still_passes,
)


def main() -> int:
    return run_theme("验收客户端共享实现(票 13)", TESTS, FAILURES)


if __name__ == "__main__":
    sys.exit(main())

#!/usr/bin/env python3
"""设计问答耗时与步骤测量 seam(统一设计问答框架票 01)。

接缝:``acceptance/_shared/design_discussion_metrics.py`` 的
``measure_module_run`` / ``record_baseline_identity``。只经该 interface
观察行为:从宿主事件与回读结果计算规格四项耗时、步骤计数与例外分类。
可控事件样例只核对计算口径,不冒充真实模型耗时证据。另用验收 06 已落盘
的真实 W2 事件核对时间戳减法与独立字面量一致。

    python3 -B tests/test_design_discussion_metrics.py
"""

import json
import sys
from pathlib import Path

from plugin_package_support import REPO_ROOT, make_checker, run_theme

FAILURES, check = make_checker()

SHARED = REPO_ROOT / "acceptance" / "_shared"
if str(SHARED) not in sys.path:
    sys.path.insert(0, str(SHARED))

from design_discussion_metrics import (  # noqa: E402
    INCOMPLETE, NOT_APPLICABLE, UNKNOWN,
    load_jsonl, measure_module_run, record_baseline_identity,
)

W2_EVENTS = (
    REPO_ROOT / "acceptance" / "06-idea-to-current-spec"
    / "evidence" / "w2-events.jsonl"
)


def _item_event(item, at_ms, method="item/completed"):
    return {
        "method": method,
        "emittedAtMs": at_ms,
        "params": {"item": item, "completedAtMs": at_ms, "threadId": "th"},
    }


def _user(at_ms, text="用户完整回答"):
    return _item_event(
        {"type": "userMessage",
         "content": [{"type": "text", "text": text}]},
        at_ms,
    )


def _agent(at_ms, text, phase):
    return _item_event(
        {"type": "agentMessage", "text": text, "phase": phase},
        at_ms,
    )


def _command(at_ms, *, actions=None, output="", status="completed",
             command="nl -ba file", exit_code=0):
    return _item_event(
        {"type": "commandExecution", "command": command, "status": status,
         "exitCode": exit_code, "commandActions": actions or [],
         "aggregatedOutput": output, "durationMs": 0},
        at_ms,
    )


def _read_action(path):
    name = path.rstrip("/").rsplit("/", 1)[-1]
    return {"type": "read", "name": name, "path": path, "command": f"nl -ba {path}"}


def _write(at_ms, path, *, allow=True, nbytes=100):
    result = {
        "op": "write",
        "decision": "allow" if allow else "deny",
        "rule_stage": "granted" if allow else "task_grant",
        "target": path,
        "bytes": nbytes,
    }
    return _item_event(
        {"type": "mcpToolCall", "tool": "mgs_write", "status": "completed",
         "arguments": {"path": path, "content": "x" * nbytes,
                       "expected_sha256": "absent"},
         "result": {"content": [{"type": "text",
                                 "text": json.dumps(result, ensure_ascii=False)}]},
         "error": None, "durationMs": 1},
        at_ms,
    )


def _scope(at_ms):
    result = {"op": "scope", "decision": "allow", "allowed": ["docs/**"]}
    return _item_event(
        {"type": "mcpToolCall", "tool": "mgs_scope", "status": "completed",
         "arguments": {"token": "<redacted-token>"},
         "result": {"content": [{"type": "text",
                                 "text": json.dumps(result)}]},
         "durationMs": 1},
        at_ms,
    )


def _turn_done(at_ms):
    return {
        "method": "turn/completed",
        "emittedAtMs": at_ms,
        "params": {"threadId": "th",
                   "turn": {"status": "completed", "durationMs": 1}},
    }


def test_decision_save_time_runs_until_reread() -> None:
    """本轮决定保存用时:用户完整回答到达 → 决定写入并完成必要回读。"""

    events = [
        _user(1000, "Q1 选 B,Q2 选 A"),
        _agent(1100, "正在保存", "commentary"),
        _scope(1200),
        _write(2000, "docs/mygamestudio/records/decision-demo.md", nbytes=40),
        _command(2500, actions=[_read_action(
            "/proj/docs/mygamestudio/records/decision-demo.md")],
                 output="已采纳决定正文"),
        _agent(3000, "已保存", "final_answer"),
        _turn_done(3100),
    ]
    report = measure_module_run([{"events": events}])
    check(report["rounds"][0]["decision_save_ms"] == 1500,
          f"决定保存用时应为 1500,实际 {report['rounds'][0]['decision_save_ms']}")


def test_no_adopted_content_is_not_applicable() -> None:
    """没有采纳内容的轮次标不适用,不伪造零耗时。"""

    events = [
        _user(1000, "请先提问"),
        _agent(1100, "先整理问题", "commentary"),
        _command(1600, actions=[_read_action("/proj/docs/mygamestudio/GAME_DESIGN.md")],
                 output="现行规则"),
        _agent(4000, "❓ Q1 选项 A/B", "final_answer"),
        _turn_done(4100),
    ]
    report = measure_module_run([{"events": events}])
    check(report["rounds"][0]["decision_save_ms"] == NOT_APPLICABLE,
          f"无采纳轮次应为 {NOT_APPLICABLE},实际 {report['rounds'][0]['decision_save_ms']}")
    check(report["rounds"][0]["decision_save_ms"] != 0,
          "无采纳轮次不得记为零耗时")


def test_continue_wait_ignores_progress_prompt() -> None:
    """继续讨论等待以完整结果呈现为准,第一句进度提示不算完成。"""

    events = [
        _user(1000, "Q1 选 A"),
        _agent(1300, "先核对再提问", "commentary"),
        _agent(5000, "❓ Q4 依赖项", "final_answer"),
        _turn_done(5100),
    ]
    report = measure_module_run([{"events": events}])
    check(report["rounds"][0]["continue_wait_ms"] == 4000,
          f"继续讨论等待应为 4000,实际 {report['rounds'][0]['continue_wait_ms']}")


def test_module_processing_deducts_recorded_user_wait() -> None:
    """完整模块处理用时扣除有明确起止的用户等待,计入工具等待与最终同步。"""

    ask = [
        _user(1000, "请设计每日挑战核心模块"),
        _agent(1100, "开始", "commentary"),
        _agent(3000, "❓ Q1 Q2 Q3", "final_answer"),
        _turn_done(3100),
    ]
    save = [
        _user(8000, "Q1 选 A,Q2 选 B"),
        _write(9000, "docs/mygamestudio/records/decision-mod.md"),
        _command(9500, actions=[_read_action(
            "/p/docs/mygamestudio/records/decision-mod.md")],
                 output="决定"),
        _agent(10000, "已保存,继续 Q4", "final_answer"),
        _turn_done(10100),
    ]
    sync = [
        _user(14000, "同步本模块规格"),
        _write(15000, "docs/mygamestudio/GAME_DESIGN.md", nbytes=200),
        _command(15500, actions=[_read_action("/p/docs/mygamestudio/GAME_DESIGN.md")],
                 output="基线 v2"),
        _agent(16000, "同步完成", "final_answer"),
        _turn_done(16100),
    ]
    report = measure_module_run(
        [{"events": ask}, {"events": save}, {"events": sync}],
        user_wait_intervals=((3100, 8000), (10100, 14000)),
    )
    # 1000→16100 共 15100,扣除 (8000-3100)+(14000-10100)=8800,余 6300
    check(report["module"]["processing_ms"] == 6300,
          f"完整模块处理用时应为 6300,实际 {report['module']['processing_ms']}")
    check(report["module"]["user_wait_ms_deducted"] == 8800,
          f"用户等待扣除应为 8800,实际 {report['module']['user_wait_ms_deducted']}")
    check(report["module"]["cumulative_decision_save_ms"] == 1500,
          f"累计决定保存应为 1500,实际 {report['module']['cumulative_decision_save_ms']}")


def test_failed_write_retry_stays_inside_timing() -> None:
    """失败重试计入决定保存用时,不把返工移出统计。"""

    events = [
        _user(1000),
        _write(1500, "docs/mygamestudio/records/decision-x.md", allow=False),
        _write(2200, "docs/mygamestudio/records/decision-x.md", allow=True),
        _command(2600, actions=[_read_action(
            "/p/docs/mygamestudio/records/decision-x.md")],
                 output="回读成功"),
        _agent(3000, "已保存", "final_answer"),
        _turn_done(3050),
    ]
    report = measure_module_run([{"events": events}])
    check(report["rounds"][0]["decision_save_ms"] == 1600,
          f"含重试的保存用时应为 1600,实际 {report['rounds'][0]['decision_save_ms']}")
    check(report["rounds"][0]["retried"] is True,
          "失败后再次写入应标记 retried")


def test_missing_endpoint_is_incomplete_not_zero() -> None:
    """缺失终点只记未完成,不伪造耗时。"""

    events = [
        _user(1000, "Q1 选 A"),
        _write(1800, "docs/mygamestudio/records/decision-x.md"),
        # 写入后没有回读,也没有 final_answer / turn/completed
    ]
    report = measure_module_run([{"events": events}])
    check(report["rounds"][0]["decision_save_ms"] == INCOMPLETE,
          f"缺回读应为 {INCOMPLETE},实际 {report['rounds'][0]['decision_save_ms']}")
    check(report["rounds"][0]["continue_wait_ms"] == INCOMPLETE,
          f"缺完整结果应为 {INCOMPLETE},实际 {report['rounds'][0]['continue_wait_ms']}")
    check(any(item["kind"] == "missing_record" for item in report["exceptions"]),
          f"缺终点应单列 missing_record:{report['exceptions']}")


def test_one_command_counts_each_file() -> None:
    """一个调用内处理多个文件时分别计数;合并调用不能冒充减少文件操作。"""

    output = "FILE a\n" + ("a" * 10) + "\nFILE b\n" + ("b" * 20)
    events = [
        _user(1000),
        _command(
            2000,
            actions=[
                _read_action("/p/docs/mygamestudio/GAME_DESIGN.md"),
                _read_action("/p/docs/mygamestudio/PROJECT.md"),
                _read_action("/p/src/main.js"),
            ],
            output=output,
        ),
        _agent(2500, "❓ Q1", "final_answer"),
        _turn_done(2600),
    ]
    report = measure_module_run([{"events": events}])
    check(report["steps"]["reads"]["count"] == 3,
          f"三次读文件应计 3,实际 {report['steps']['reads']['count']}")
    check(report["steps"]["reads"]["bytes"] == 45,
          f"内容规模应为 45,实际 {report['steps']['reads']['bytes']}")
    check(report["steps"]["tool_calls"]["count"] == 1,
          f"工具调用仍是 1 次命令,实际 {report['steps']['tool_calls']['count']}")


def test_repeat_read_after_unchanged_input() -> None:
    """同一路径在写入前重复读取记为重复操作;写入后再读为必要回读。"""

    path = "/p/docs/mygamestudio/records/decision-x.md"
    events = [
        _user(1000),
        _command(1200, actions=[_read_action(path)], output="v1"),
        _command(1400, actions=[_read_action(path)], output="v1"),
        _write(2000, "docs/mygamestudio/records/decision-x.md"),
        _command(2400, actions=[_read_action(path)], output="v2"),
        _agent(2600, "已保存", "final_answer"),
        _turn_done(2700),
    ]
    report = measure_module_run([{"events": events}])
    check(report["steps"]["reads"]["necessary"] == 2,
          f"首次读+写后回读应为必要 2,实际 {report['steps']['reads']['necessary']}")
    check(report["steps"]["reads"]["repeat"] == 1,
          f"输入未变的第二次读应为重复 1,实际 {report['steps']['reads']['repeat']}")


def test_inter_turn_gap_deducted_without_explicit_waits() -> None:
    """多轮之间、上一轮完成到下一轮回答到达的间隔,在未另给等待表时扣除。"""

    first = [
        _user(1000, "开始"),
        _agent(2000, "❓ Q1", "final_answer"),
        _turn_done(2100),
    ]
    second = [
        _user(5000, "Q1 选 A"),
        _write(6000, "docs/mygamestudio/records/decision-x.md"),
        _command(6500, actions=[_read_action(
            "/p/docs/mygamestudio/records/decision-x.md")],
                 output="ok"),
        _agent(7000, "已保存", "final_answer"),
        _turn_done(7100),
    ]
    report = measure_module_run([{"events": first}, {"events": second}])
    # 1000→7100=6100,扣除 5000-2100=2900,余 3200
    check(report["module"]["processing_ms"] == 3200,
          f"应自动扣除轮间等待得 3200,实际 {report['module']['processing_ms']}")
    check(report["module"]["user_wait_ms_deducted"] == 2900,
          f"轮间等待应为 2900,实际 {report['module']['user_wait_ms_deducted']}")


def test_tokens_unknown_when_absent() -> None:
    """可靠 Token 记录缺失时标未知。"""

    events = [
        _user(1000),
        _agent(2000, "❓ Q1", "final_answer"),
        _turn_done(2100),
    ]
    report = measure_module_run([{"events": events}])
    check(report["steps"]["tokens"] == UNKNOWN,
          f"无 Token 字段应为 {UNKNOWN},实际 {report['steps']['tokens']}")


def test_tool_host_spawn_failure_is_external_fault() -> None:
    """工具宿主无法启动属于外部故障,单列且不得当有效效率基准。"""

    events = [
        _user(1000, "请保存决定"),
        _agent(2000,
               "failed to spawn code-mode host /opt/homebrew/bin/codex-code-mode-host: No such file or directory",
               "final_answer"),
        _turn_done(2100),
    ]
    report = measure_module_run(
        [{"events": events}],
        expected_outcomes={"must_sync_spec": True},
        observed_outcomes={"written_paths": [], "semantics_matched": False},
    )
    kinds = [item["kind"] for item in report["exceptions"]]
    check("external_fault" in kinds, f"应单列 external_fault,实际 {kinds}")
    check(report["comparability"]["comparable"] is False,
          "宿主故障导致缺成果时应不可比")
    check(report["module"]["processing_ms"] == INCOMPLETE,
          f"缺成果不得用短时长当基准,实际 {report['module']['processing_ms']}")
    check(report["status"] == "incomplete",
          f"宿主故障缺成果应为 incomplete,实际 {report['status']}")


def test_incomparable_when_required_sync_missing() -> None:
    """优化前不能完成相同成果语义时明确不可比,不用短时长当效率基准。"""

    events = [
        _user(1000, "请同步规格"),
        _agent(1500, "本轮只讨论未写入", "final_answer"),
        _turn_done(1600),
    ]
    report = measure_module_run(
        [{"events": events}],
        expected_outcomes={"must_sync_spec": True,
                           "required_paths": ["docs/mygamestudio/GAME_DESIGN.md"]},
        observed_outcomes={"written_paths": [], "semantics_matched": False},
    )
    check(report["comparability"]["comparable"] is False,
          f"缺同步成果应不可比:{report['comparability']}")
    check(any(item["kind"] == "incomparable" for item in report["exceptions"]),
          f"不可比应单列:{report['exceptions']}")
    check(report["module"]["processing_ms"] == INCOMPLETE,
          f"未完成同步只能记未完成,实际 {report['module']['processing_ms']}")
    check(report["status"] == "incomplete",
          f"未完成同步的 status 应为 incomplete,实际 {report['status']}")


def test_real_w2_events_match_independent_timestamps() -> None:
    """用验收 06 真实 W2 事件核对:期望值来自事件时间戳字面量,不是本模块重算。"""

    check(W2_EVENTS.is_file(), f"缺少真实事件 {W2_EVENTS}")
    report = measure_module_run([{"events": load_jsonl(W2_EVENTS)}])
    # userMessage completedAtMs=1788840085964
    # 决定记录写入后回读 command completedAtMs=1788840329866
    # final_answer completedAtMs=1788840360462
    check(report["rounds"][0]["decision_save_ms"] == 243902,
          f"W2 决定保存用时应为 243902,实际 {report['rounds'][0]['decision_save_ms']}")
    check(report["rounds"][0]["continue_wait_ms"] == 274498,
          f"W2 继续讨论等待应为 274498,实际 {report['rounds'][0]['continue_wait_ms']}")
    check(report["rounds"][0]["has_adopted_content"] is True,
          "W2 写入了决定记录,应视为有采纳内容")


def test_candidate_error_is_listed_not_external_fault() -> None:
    """候选自身写错单列 candidate_error,不得当环境异常剔除。"""

    events = [
        _user(1000, "同步本模块"),
        _write(1500, "docs/mygamestudio/GAME_DESIGN.md"),
        _command(1800, actions=[_read_action("/p/docs/mygamestudio/GAME_DESIGN.md")],
                 output="写错了范围"),
        _agent(2000, "已同步", "final_answer"),
        _turn_done(2100),
    ]
    report = measure_module_run(
        [{"events": events}],
        expected_outcomes={"must_sync_spec": True},
        observed_outcomes={
            "written_paths": ["docs/mygamestudio/GAME_DESIGN.md"],
            "semantics_matched": False,
            "candidate_error": "GAME_DESIGN 未写入约定的每日挑战规则",
        },
    )
    kinds = [item["kind"] for item in report["exceptions"]]
    check("candidate_error" in kinds, f"应单列 candidate_error,实际 {kinds}")
    check("external_fault" not in kinds, "候选自身错误不得标成外部故障")
    check(report["module"]["processing_ms"] == INCOMPLETE,
          "成果语义不符只能记未完成,不得用该时长当效率基准")


def test_identity_uses_content_hashes_without_git_tag() -> None:
    """优化前内容身份按插件文件指纹记录,不以 Git 标签为前提。"""

    identity = record_baseline_identity(REPO_ROOT / "plugin")
    check(identity.get("plugin_version") == "0.18.1",
          f"应记录当前插件版本,实际 {identity.get('plugin_version')}")
    design = identity.get("content_sha256", {}).get("skills/game-design/SKILL.md")
    check(isinstance(design, str) and len(design) == 64,
          f"应记录 game-design 内容 SHA-256,实际 {design}")
    check("git_tag_required" not in identity,
          "内容身份不得把 Git 标签列为前提")
    check(identity.get("git_tag") in (None, "", UNKNOWN),
          "未打标签时 git_tag 应为空或未知")


TESTS = (
    test_decision_save_time_runs_until_reread,
    test_no_adopted_content_is_not_applicable,
    test_continue_wait_ignores_progress_prompt,
    test_module_processing_deducts_recorded_user_wait,
    test_inter_turn_gap_deducted_without_explicit_waits,
    test_failed_write_retry_stays_inside_timing,
    test_missing_endpoint_is_incomplete_not_zero,
    test_one_command_counts_each_file,
    test_repeat_read_after_unchanged_input,
    test_tokens_unknown_when_absent,
    test_tool_host_spawn_failure_is_external_fault,
    test_incomparable_when_required_sync_missing,
    test_candidate_error_is_listed_not_external_fault,
    test_real_w2_events_match_independent_timestamps,
    test_identity_uses_content_hashes_without_git_tag,
)


def main() -> int:
    return run_theme("设计问答耗时与步骤测量", TESTS, FAILURES)


if __name__ == "__main__":
    sys.exit(main())

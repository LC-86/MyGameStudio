#!/usr/bin/env python3
"""已有设计变更的报告措辞(统一设计问答框架票 06)。

公开 interface:
  plan_report(plan) / questions_report(plan) / incomplete_report(plan)
  read_only_report(plan) / saved_report(plan, written, states)
  failure_report(plan, outcome, written) / blocked_report(plan)

计划、待取舍、未完成、只读、已保存与失败各自表达真实状态:已采纳、已保存、
已同步核心基线、已实现与已验证分别说明;未完成时逐条列出未说明的关键断点与
新增取舍问题,不用默认值补齐;失败时原样给出通道依据,不称已保存。

本 module 只组织措辞,不判定状态、不接触受控通道(在 ``change_flow``)。
"""

from __future__ import annotations

from typing import Any


def plan_report(plan: dict[str, Any]) -> str:
    impact = plan["impact"]
    return (f"已完成 {plan['module']} 变更整理（{plan['organization']['label']}）："
            f"必须同步 "
            f"{'、'.join(item['id'] for item in impact['must_sync']) or '无'}"
            f";新增取舍问题 "
            f"{'、'.join(item['id'] for item in impact['questions']) or '无'}"
            f";待写入文件 {len(plan['files'])} 个。")


def questions_report(plan: dict[str, Any]) -> str:
    change = plan["change"]
    lines = [f"{plan['module']} 变更目标与保留项已明确"
             f"（{plan['organization']['label']}）,影响已分析;"
             f"同步前还有需要开发者取舍的处理方式:"]
    for item in plan["questions"]:
        lines.append(f"- {item['id']} {item['title']}（新增取舍,"
                     f"推荐 {item['recommendation']}）")
    lines.append("已沿用的决定："
                 + ("、".join(item["qid"] for item in change["answers"])
                    or "无")
                 + ";未受影响内容不在本次同步范围。")
    return "\n".join(lines)


def incomplete_report(plan: dict[str, Any]) -> str:
    lines = [f"{plan['module']} 变更尚未具备同步条件,未写入任何文件:"]
    for item in plan["unresolved"]:
        lines.append(f"- {item['kind']}：{item['detail']}"
                     f"（{item.get('method')}）")
    return "\n".join(lines)


def read_only_report(plan: dict[str, Any]) -> str:
    return (f"本入口当前只读：{plan['module']} 变更内容尚未保存、尚未同步核心"
            f"基线;已采纳的修改决定与影响分析保留待授权后同步。")


def check_failed_report(plan: dict[str, Any], written: list[str],
                        checks: dict[str, Any]) -> str:
    failures = "；".join(checks.get("failures") or []) or "未列出"
    return (f"{plan.get('module')} 变更已写入但检查失败:未完成同步。"
            f"已写入：{'、'.join(written) or '无'}。"
            f"检查失败：{failures}。已写入事实保留,不得称为已同步。")


def saved_report(plan: dict[str, Any], written: list[str],
                 states: dict[str, bool]) -> str:
    return (f"已保存 {plan['module']} 变更：写入 " + "、".join(written)
            + f"；已同步核心基线：{'是' if states['synced'] else '否'}"
              f"；实现与效果验证另行判断。")


def blocked_report(plan: dict[str, Any]) -> str:
    return str(plan.get("report") or "变更未写入:先处理未说明的关键断点。")


def failure_report(plan: dict[str, Any], outcome: dict[str, Any],
                   written: list[str]) -> str:
    """按通道真实依据报告未保存:冲突、被拒或回读失败,不换通道重试。"""

    path = str(outcome.get("path") or "")
    del plan
    if outcome["outcome"] == "conflict":
        return (f"版本冲突：{path} 已被改动"
                f"（计划版本 {outcome.get('actual_sha256')}）;"
                f"本轮变更未完成,剩余文件未写入,"
                f"先重新读取实际内容再决定,不覆盖旧快照。")
    if outcome["outcome"] == "denied":
        done = ("（已写入文件按实际保留）" if written else "（所有文件均未写入）")
        return (f"受控通道拒绝写入（rule_stage={outcome.get('rule_stage')}）："
                f"{outcome.get('reason')};{path} 未保存,"
                f"本轮变更未完成{done};不换通道或路径重试。")
    return (f"写入后回读核对失败（{path}）:落盘未确认,"
            f"不得称为已保存或已同步。")

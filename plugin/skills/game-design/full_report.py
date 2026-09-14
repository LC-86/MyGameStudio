#!/usr/bin/env python3
"""Game-Design 完整设计成稿的报告措辞(统一设计问答框架票 05)。

计划、未完成、只读、完成与失败五类报告的唯一措辞位置:分别表达已采纳、
已保存、已同步、已实现与已验证;未完成如实列出覆盖缺口、流程未闭合、模块
未完成、范围待澄清、规则不可执行、未知无方法与跨模块矛盾,不因目录齐全
宣称整体完成;只读明确尚未保存未同步。报告只描述实际状态。

本 module 只拼装文本,不接触受控通道、不判断是否可以写入(在 ``full_design``)。
"""

from __future__ import annotations

from typing import Any


def plan_report(plan: dict[str, Any]) -> str:
    """计划报告:列出入口、四类交付物与状态,不宣称已保存。"""

    lines = [f"计划交付{plan.get('game') or ''}完整设计（尚未写入;"
             f"按受控通道逐文件提交并回读后才算已保存）:",
             f"入口：{plan.get('entry')}（游戏设计主文档）"]
    for item in plan.get("outputs") or []:
        lines.append(f"- {item['role']}：{item['path']}")
    lines.append(f"本次写入：{'、'.join(item['path'] for item in plan.get('files') or [])}")
    lines.append(f"不受影响：{'、'.join(plan.get('untouched') or []) or '无'}")
    lines.append("状态：已采纳、已保存（回读后）、未实现、未验证分别记录。")
    return "\n".join(lines)


def blocked_report(plan: dict[str, Any]) -> str:
    """未完成报告:逐条列出阻断交接的关键缺口与跨模块矛盾。"""

    lines = ["未达到可交接状态:覆盖与关键流程检查未通过,"
             "不因目录齐全宣布整体完成,不用默认值补齐。"]
    if plan.get("missing"):
        lines.append("阻断当前交接的关键缺口：")
        for item in plan["missing"]:
            reasons = "；".join(
                str(item[key]) for key in ("gap", "method", "impact")
                if item.get(key))
            lines.append(f"- {item['needle']}：{item.get('detail')}"
                         + (f"（{reasons}）" if reasons else ""))
    if plan.get("contradictions"):
        lines.append("发现的跨模块矛盾（先处理真实影响）：")
        for item in plan["contradictions"]:
            lines.append(f"- {item['kind']}：{item['detail']}；"
                         f"影响：{item['impact']}")
    lines.append("已采纳与已保存的内容仍在决定记录与模块规格中;"
                 "本轮未写入任何交付物,也未把整体标为完成。")
    return "\n".join(lines)


def read_only_report(plan: dict[str, Any]) -> str:
    """只读报告:未获写入授权,尚未保存、尚未同步,内容保留待授权。"""

    lines = ["只读讨论:未获写入授权,尚未保存、尚未同步核心基线;"
             "已采纳事实与交付草稿保留,等授权后按同一流程继续。"]
    if plan.get("missing"):
        lines.append("阻断当前交接的关键缺口："
                     + "、".join(item["needle"] for item in plan["missing"])
                     + "。")
    if plan.get("contradictions"):
        lines.append("发现的跨模块矛盾："
                     + "；".join(item["detail"]
                                for item in plan["contradictions"]) + "。")
    return "\n".join(lines)


def check_failed_report(plan: dict[str, Any], written: list[str],
                        checks: dict[str, Any]) -> str:
    """写入已发生,但保存后检查失败:保留事实,不得称为完整设计已交付。"""

    failures = "；".join(checks.get("failures") or []) or "未列出"
    return "\n".join([
        f"完整设计已写入但检查失败（{plan.get('game') or ''}）:交付未完成。",
        f"已写入：{'、'.join(written) or '无'}。",
        f"检查失败：{failures}。",
        "已写入事实保留;不得称为已交付或已同步。"
        "待同步项按实际记录保留,先解决检查缺口再继续。",
    ])


def pending_sync_report(plan: dict[str, Any], to_sync: list[str]) -> str:
    """有写入授权但缺同步授权:草稿可整理,不得改写当前有效设计。"""

    pending = "、".join(to_sync) or "当前有效设计"
    return "\n".join([
        f"已整理{plan.get('game') or ''}完整设计草稿,缺同步授权,"
        "未改写当前有效设计。",
        f"待同步：{pending}；获准同步前不能把失效规则退出当前有效版本。",
        "状态：已采纳、未保存当前有效设计、未同步核心基线;"
        "实现状态：未实现;验证状态：未验证。",
    ])


def saved_report(plan: dict[str, Any], written: list[str],
                 states: dict[str, bool]) -> str:
    """完成报告:列出实际写入范围与入口,实现与验证状态分开。"""

    lines = [f"已交付{plan.get('game') or ''}完整设计,"
             f"已完成逐次权限与版本校验并回读核对。",
             f"入口：{plan.get('entry')}（游戏设计主文档,含四类交付物的定位）",
             "交付范围："]
    for item in plan.get("outputs") or []:
        state = "本次写入" if item["path"] in written else "沿用现行权威位置"
        lines.append(f"- {item['role']}：{item['path']}（{state}）")
    lines.append("现行规则只有一个权威维护位置:具体规则见模块规格,"
                 "主文档与制作需求只引用、不重复。")
    if plan.get("untouched"):
        lines.append("不受影响（未改动）：" + "、".join(plan["untouched"]))
    if plan.get("to_sync"):
        lines.append("待同步：" + "、".join(plan["to_sync"])
                     + "；已保存但未同步核心基线,继续工作前先定位这些内容,"
                       "按票 04 的模块规格交接流程同步。")
    else:
        lines.append("待同步：无（现行规则都已同步核心基线）。")
    lines.append("状态：已采纳、已保存、已同步分别记录;"
                 "实现状态：未实现;验证状态：未验证"
                 "（没有原型或试玩证据,不报告相应验证通过）;"
                 "本入口不代替模块规格交接同步决定记录状态。")
    if not plan.get("sync_authorized"):
        lines.append("同步授权：未获得,核心基线的同步标记保留待处理,"
                     "不自动签发凭据。")
    return "\n".join(lines)


def failure_report(plan: dict[str, Any], outcome: dict[str, Any],
                   written: list[str]) -> str:
    """失败报告:版本冲突、写入被拒或回读失败时按实际依据原样说明。"""

    path = str(outcome.get("path") or "")
    reason = str(outcome.get("reason") or "")
    if outcome.get("outcome") == "conflict":
        return (f"版本冲突：{reason};本轮交付未完成,剩余文件未写入,"
                f"先重新读取实际内容再决定,不覆盖旧快照。")
    if outcome.get("outcome") == "denied":
        return (f"受控通道拒绝写入（rule_stage={outcome.get('rule_stage')}）："
                f"{reason};{path} 未保存,本轮交付未完成"
                f"（已写入文件按实际保留:{'、'.join(written) or '无'}）;"
                f"不换通道重试。")
    return (f"写入后回读核对失败（{path}）:落盘未确认,不得称为已保存或已同步;"
            f"本轮交付未完成。")

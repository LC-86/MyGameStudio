#!/usr/bin/env python3
"""模块规格交接的报告措辞(统一设计问答框架票 04)。

计划、未完成、只读与完成四类报告的唯一措辞位置:分别表达已采纳、已保存、
已同步、已实现与已验证;未完成如实列出缺失缺口与阻断交接的未决项;只读
明确尚未保存;目标或范围变化输出统筹同步交接。报告只描述实际状态,不把
未写入或未验证写成已完成。

本 module 只拼装文本,不接触受控通道、不判断是否可以写入(在 ``spec_draft``)。
"""

from __future__ import annotations

from typing import Any


def component_report(decision: dict[str, Any], meta: dict[str, Any],
                     parsed: dict[str, Any], files: list[dict],
                     *, read_only: bool = False) -> str:
    """计划报告:列出待同步、未决、排除项与同步范围,不宣称已保存。"""

    module = str(meta.get("module") or "")
    if read_only:
        lines = ["只读讨论:未获写入授权,尚未保存、尚未同步;"
                 "已采纳事实保留,等授权后再同步。"]
    else:
        lines = [f"计划交接 {module} 模块规格,尚未写入;"
                 f"按受控通道逐文件提交并回读后才算已保存。"]
    lines.append("待同步：" + ("、".join(decision["to_sync"])
                              if decision["to_sync"] else "无"))
    if decision["synced"]:
        lines.append("已同步：" + "、".join(decision["synced"]))
    for item in parsed["superseded"]:
        lines.append(f"已被替代（历史保留）：{item['qid']} 旧值"
                     f"「{item['value']}」（第 {item.get('round') or '?'} 轮）")
    lines.append("未采纳内容：" + ("；".join(
        item["detail"] for item in decision["excluded"])
        if decision["excluded"] else "无"))
    lines.extend(_pending_lines(decision, meta))
    lines.append("同步范围：")
    for item in files:
        lines.append(f"- {item['path']}（{item['role']}）")
    if meta.get("untouched"):
        lines.append("不受影响（计划不改动）：" + "、".join(
            str(path) for path in meta["untouched"]))
    blocking = [str(qid) for qid in (meta.get("blocking_qids") or [])
                if str(qid) not in decision["settled"]]
    if blocking:
        lines.append("阻断当前交接：" + "、".join(blocking))
    return "\n".join(lines)


def _pending_lines(decision: dict[str, Any], meta: dict[str, Any]) -> list[str]:
    pending = list(decision["pending"])
    if not pending:
        return ["未决项：无"]
    impacts = dict(meta.get("pending_impacts") or {})
    lines = ["未决项与影响："]
    for item in pending:
        lines.append(f"- {item['qid']} {item['title']}：{item['status']}；"
                     f"影响：{impacts.get(item['qid']) or '未单独列'}")
    return lines


def blocked_report(plan: dict[str, Any]) -> str:
    if plan.get("status") == "incomplete":
        return incomplete_report(str(plan.get("module") or ""),
                                  plan.get("missing") or [],
                                  plan.get("blocking") or [],
                                  plan.get("blocking_verification") or [])
    reason = plan.get("reason") or "本轮未写入"
    to_sync = plan.get("to_sync") or []
    parts = [f"{reason};本轮模块规格未保存（未写入）,也未同步核心基线。",
             "待同步：" + ("、".join(to_sync) if to_sync else "无") + "。"]
    pending = plan.get("pending") or []
    if pending:
        parts.append("未决：" + "、".join(
            f"{item['qid']} {item['title']}（{item['status']}）"
            for item in pending) + "。")
    parts.append("待同步项与未决项保留在决定记录中,授权后按同一流程继续。")
    return "".join(parts)


def incomplete_report(module: str, missing: list[dict],
                       blocking: list[str],
                       blocking_verification: list[str]) -> str:
    lines = [f"模块规格未完成（{module}）:未达到可交接状态,不用默认值补齐。",
             "缺失的关键内容："]
    for item in missing:
        lines.append(f"- {item['field']}：{item['detail']}")
    if blocking:
        lines.append(f"阻断当前交接的未决项：{'、'.join(blocking)}；"
                     f"保留在决定记录中,待开发者决定后重新收敛。")
    if blocking_verification:
        lines.append("阻断当前阶段的主观体验验证问题："
                     + "；".join(blocking_verification)
                     + "。没有实际证据时不报告验证通过。")
    lines.append("已采纳且未同步的决定保留在决定记录中,未写入任何交付文件。")
    return "\n".join(lines)


def check_failed_report(plan: dict[str, Any], written: list[str],
                        checks: dict[str, Any]) -> str:
    """写入已发生,但保存后检查失败:保留事实,不得称为交接完成。"""

    failures = "；".join(checks.get("failures") or []) or "未列出"
    return "\n".join([
        f"模块规格已写入但检查失败（{plan.get('module')}）:交接未完成。",
        f"已写入：{'、'.join(written) or '无'}。",
        f"检查失败：{failures}。",
        "已写入事实保留;不得称为已交接或已完成核对。"
        "待同步项按实际记录保留,先解决检查缺口再继续。",
    ])


def saved_report(plan: dict[str, Any], written: list[str],
                  state: dict[str, Any]) -> str:
    version = plan.get("version") or {}
    module = plan.get("module") or ""
    lines = [f"已交接：{module}模块规格（{plan.get('spec_path')}）,"
             f"已完成逐次权限与版本校验并回读核对。",
             f"本次只交接模块 {module};不替代全游戏设计完成结论。"]
    if version.get("change") == "format":
        lines.append(f"版本处理：本次为格式修正或语义一致的整理,"
                     f"版本保持 {version.get('to')},不算新产品要求;"
                     f"不涉及版本递增。")
    else:
        lines.append(f"版本处理：实质变化 {version.get('from')} → "
                     f"{version.get('to')};核心基线已登记版本、双指纹"
                     f"与采纳依据。")
    lines.append("同步范围：" + "、".join(
        f"{item['path']}（{item['role']}）"
        for item in plan.get("files") or []
        if item.get("path") in written))
    if plan.get("untouched"):
        lines.append("其他模块与无关资料不变：" + "、".join(plan["untouched"]))
    lines.append("状态：已采纳、已保存、已同步分别记录;"
                 "实现状态：未实现;验证状态：未验证。")
    if state.get("synced"):
        lines.append("待同步：无。")
    elif plan.get("to_sync"):
        lines.append("待同步：" + "、".join(plan["to_sync"])
                     + "；缺少同步授权或写入未完成,原样保留在决定记录中,"
                       "不能只读旧基线后重问或据此开工。")
    else:
        lines.append("待同步：无。")
    if plan.get("blocking_verification"):
        lines.append("阻断当前阶段的验证问题："
                     + "；".join(plan["blocking_verification"]) + "。")
    producer = plan.get("producer_handoff")
    if producer:
        lines.append("统筹同步交接（目标或范围变化,不代写管理资料）：")
        for item in producer["items"]:
            lines.append(f"- {item['content']}；影响：{item['impact']}")
        lines.append(f"建议动作：{producer['action']}")
    return "\n".join(lines)

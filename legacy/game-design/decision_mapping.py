#!/usr/bin/env python3
"""本轮问答结果 → 最小决定记录的映射(统一设计问答框架票 03)。

决定保存接缝的映射职责:把 ``rounds.run_round`` 的题目目录、采纳来源、
未决原因与依赖关系翻成记录条目要用的决定标题、采纳内容、来源标注、建议
出处、影响与未决说明,以及保存报告里的分档状态。期望值全部来自本轮实际
展示的题目与建议;助手建议、临时假设与候选方案保持其身份。

本 module 只做映射与措辞,不写入、不核对授权与版本(那些在
``decisions.py``),也不解释已有记录文本(在 ``decision_records.py``)。
"""

from __future__ import annotations

from typing import Any

from decision_records import DEFERRED_LABEL, PENDING_LABELS, SYNC_DONE


def catalog_index(round_result: dict[str, Any]) -> dict[str, dict[str, Any]]:
    """本轮题目目录:按 Q 编号索引,供答案对应到实际展示的题目。"""

    items: dict[str, dict[str, Any]] = {}
    for entry in round_result.get("catalog") or []:
        item = dict(entry)
        qid = str(item.get("id") or "")
        if qid:
            items[qid] = item
    if items:
        return items
    for index, raw in enumerate(round_result.get("questions") or []):
        item = dict(raw)
        raw_id = str(item.get("id") or index + 1)
        qid = raw_id if raw_id.startswith("Q") else f"Q{raw_id}"
        item["id"] = qid
        items[qid] = item
    return items


def render_value(value: Any, question: dict[str, Any]) -> str:
    """采纳内容:选项字母翻成「字母 + 选项全文」,自定方案原样保留。"""

    options = question.get("options") or {}
    letter = str(value).strip()
    if letter in options:
        return f"{letter} {options[letter]}"
    return str(value).strip()


def raw_adopted(round_result: dict[str, Any]) -> dict[str, str]:
    return {str(qid): str(item.get("value"))
            for qid, item in (round_result.get("adopted") or {}).items()}


def source_label(source: str, round_no: int) -> str:
    if source == "user":
        return f"开发者逐题选择（第 {round_no} 轮）"
    if source == "recommendation":
        return f"开发者整体采纳本轮建议（第 {round_no} 轮）"
    if source == "revision":
        return f"开发者修正此前决定（第 {round_no} 轮）"
    return f"开发者自定方案（第 {round_no} 轮）"


def provenance(source: str, question: dict[str, Any], raw: Any) -> str:
    """建议出处:写明本轮实际展示的建议,并标明开发者如何作答。"""

    rec = question.get("recommendation") or ""
    rendered_rec = render_value(rec, question) if rec else ""
    if source == "recommendation":
        return f"本轮 ➡️ 建议 {rendered_rec}（开发者整体采纳）"
    if source == "revision":
        return "本轮用户回复对既有决定的修正"
    if rendered_rec:
        return f"本轮 ➡️ 建议 {rendered_rec}（开发者选择 {raw}）"
    return "本轮用户回复中的自定方案"


def impact(question: dict[str, Any], dependents: list[str]) -> str:
    text = str(question.get("impact") or "未单独列影响。")
    if dependents:
        text += f" 依赖于它的问题：{'、'.join(dependents)} 留待后续轮次。"
    return text


def dependents(round_result: dict[str, Any],
               catalog: dict[str, dict[str, Any]]) -> dict[str, list[str]]:
    """本轮决定影响了哪些后续问题(依赖它但尚未确定的题目)。"""

    result: dict[str, list[str]] = {}
    settled = set((round_result.get("adopted") or {}).keys())
    for qid, item in catalog.items():
        for dep in item.get("depends_on") or []:
            if str(dep) in settled:
                result.setdefault(str(dep), []).append(qid)
    return result


def pending_items(round_result: dict[str, Any],
                  catalog: dict[str, dict[str, Any]]) -> list[dict[str, str]]:
    """未决项:未回答、含义不明、不知道、缺事实、未展示与依赖未满足。"""

    items: list[dict[str, str]] = []
    deferred = [str(qid) for qid in (round_result.get("deferred_ids") or [])]
    for qid, item in (round_result.get("pending") or {}).items():
        qid = str(qid)
        question = catalog.get(qid, {})
        reason = str(item.get("reason") or "unanswered")
        status = (DEFERRED_LABEL if qid in deferred
                  else PENDING_LABELS.get(reason, reason))
        items.append({"qid": qid, "title": str(question.get("title") or qid),
                      "reason": reason, "status": status})
    for qid in deferred:
        if any(item["qid"] == qid for item in items):
            continue
        question = catalog.get(qid, {})
        items.append({"qid": qid, "title": str(question.get("title") or qid),
                      "reason": "deferred", "status": DEFERRED_LABEL})
    return items


def states(plan: dict[str, Any]) -> dict[str, dict[str, bool]]:
    """本轮决定的分档状态:已采纳/已保存/已同步/已实现/已验证分别记录。"""

    evidence = plan.get("evidence") or {}
    result: dict[str, dict[str, bool]] = {}
    for entry in plan.get("entries") or []:
        qid = entry["qid"]
        item = evidence.get(qid) or {}
        result[qid] = {
            "adopted": True,
            "saved": True,
            "synced": entry.get("sync") == SYNC_DONE,
            "implemented": bool(item.get("implemented")),
            "verified": bool(item.get("verified")),
        }
    return result


def saved_report(plan: dict[str, Any], to_sync: list[str],
                 states_map: dict[str, dict[str, bool]]) -> str:
    """保存结果报告:分别表达已采纳、已保存、待同步、已实现与已验证。"""

    module = plan.get("module") or ""
    lines = [
        f"已保存：第 {plan.get('round')} 轮 {module} 决定记录"
        f"（{plan.get('record_path')}）,已完成逐次权限与版本校验并回读核对。",
        "已采纳：" + "、".join(entry["qid"] for entry in plan.get("entries") or [])
        + "（开发者决定）",
        "待同步：" + ("、".join(to_sync) if to_sync else "无")
        + ("；已保存但尚未同步核心基线,后续轮次先定位这些内容。"
           if to_sync else "；核心基线已同步。"),
    ]
    implemented = [qid for qid, state in states_map.items()
                   if state["implemented"]]
    not_implemented = [qid for qid, state in states_map.items()
                       if not state["implemented"]]
    verified = [qid for qid, state in states_map.items() if state["verified"]]
    if implemented:
        lines.append("实现状态：" + "、".join(implemented) + " 已实现（有实现证据）；"
                     + ("、".join(not_implemented) + " 未实现。"
                        if not_implemented else "其余未涉及。"))
    else:
        lines.append("实现状态：未实现（只保存了设计决定,采纳不自动授权实现）")
    if verified:
        lines.append("验证状态：" + "、".join(verified) + " 已验证（有验证证据）；"
                     "其余未验证。")
    else:
        lines.append("验证状态：未验证（没有实际运行证据）")
    if plan.get("duplicates"):
        lines.append("无重复：" + "、".join(
            item["qid"] for item in plan["duplicates"]) + " 已存在,未重复创建。")
    if plan.get("pending"):
        lines.append("未决：" + "、".join(item["qid"]
                                        for item in plan["pending"]))
    return "\n".join(lines)


def conflict_report(plan: dict[str, Any], expected: str, current: str) -> str:
    return (f"版本冲突：目标 {plan.get('record_path')} 已被改动"
            f"（计划版本 {expected}，实际 {current}）;本轮内容未保存,"
            f"先重新读取实际记录再决定,不覆盖旧快照。")

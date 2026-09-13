#!/usr/bin/env python3
"""已有设计变更的交付渲染(统一设计问答框架票 06)。

公开 interface:
  update_spec(existing, items, meta) -> dict
  render_baseline(existing, meta, plan) -> str
  render_change_record(meta, record, states) -> str
  mark_results(results, current_version) -> list[dict]

把受影响项的旧规则换成新规则,把失效规则移入历史段并保留替代关系;更新
当前有效设计(核心基线)的版本与双指纹,登记指向简短变更记录的变更索引;
渲染变更记录:目标与原因、旧设计到新设计、影响范围、采纳来源、待验证方法
及保存、同步、实现、验证状态。只改实际受影响的行,不重造整套文档,也不
代写管理资料与技术设计。

本 module 只渲染,不决定是否写入、不接触受控通道(在 ``change_flow``)。
"""

from __future__ import annotations

import re
from typing import Any

from spec_sync import register_fingerprints

HISTORY_TITLE = "## 历史规则（已退出当前有效版本）"
VERSION_RE = re.compile(r"基线版本\s*[:：]\s*v\d+")


def update_spec(existing: str | None, items: list[dict[str, Any]],
                meta: dict[str, Any]) -> dict[str, Any]:
    """按受影响项改写规则行:新规则就位,旧规则进历史段,其余保持原样。"""

    text = existing or ""
    lines = text.splitlines()
    retired: list[dict[str, str]] = []
    missing: list[dict[str, str]] = []
    for item in items:
        old = str(item.get("old_text") or "").strip()
        new = str(item.get("new_text") or "").strip()
        if not old or not new:
            continue
        position = _find_line(lines, old)
        if position is None:
            if new in text:
                continue  # 该替换已生效(重复执行或已同步),不重复改写
            missing.append({
                "kind": "旧规则未定位", "detail":
                f"{item.get('title')}的当前规则未在 {item.get('location')} 找到:"
                f"「{old}」",
                "method": "先核对现行设计的实际内容,再决定如何替换",
                "impact": "无法确认失效规则已退出现行版本"})
            continue
        if lines[position].strip() != new:
            lines[position] = _reindent(lines[position], new)
        retired.append({"id": str(item.get("id") or ""),
                        "title": str(item.get("title") or ""),
                        "old": old, "new": new})
    content = "\n".join(lines)
    if text.endswith("\n"):
        content += "\n"
    if retired:
        content = _append_history(content, retired, str(meta.get("date") or ""))
    content = _bump_version(content, meta)
    return {"content": content, "retired": retired, "missing": missing}


def render_baseline(existing: str | None, meta: dict[str, Any],
                    plan: dict[str, Any]) -> str:
    """更新核心基线:版本、双指纹与变更索引;规则正文仍在模块规格。"""

    text = _bump_version(existing or "", meta)
    change = plan["change"]
    impact = plan["impact"]
    lines = [text.rstrip("\n"), "", f"## 变更记录（{meta.get('date') or ''}）", "",
             f"- 变更对象：{'、'.join(change['target_labels']) or '（未标注）'}。"
             f"目标与原因：{change['improvement']}（原因：{change['reason']}）。",
             f"- 详细前后差异与验证要求：见变更记录 "
             f"{meta.get('change_record_path') or ''}。",
             f"- 影响范围：必须同步 "
             f"{'、'.join(item['id'] for item in impact['must_sync']) or '无'}；"
             f"需要取舍 "
             f"{'、'.join(item['id'] for item in impact['needs_tradeoff']) or '无'}"
             f"；不受影响内容保持不变。",
             f"- 保留项：{'、'.join(change['keep']) or '无'}。",
             f"- 版本：{plan['version']['from']} → {plan['version']['to']}；"
             f"失效规则与引用退出现行版本,历史与替代关系保留在模块规格。"]
    return register_fingerprints("\n".join(lines) + "\n")


def render_change_record(meta: dict[str, Any], record: dict[str, Any],
                         states: dict[str, bool],
                         *, planned: bool = False) -> str:
    """简短变更记录:目标与原因、前后差异、影响、来源、验证与状态。"""

    lines = [f"# 变更记录：{record['module']}（{meta.get('date') or ''}）", "",
             f"- 变更深度：{record['depth_label']}。",
             f"- 变更对象：{'、'.join(record['target_labels']) or '（未标注）'}。",
             f"- 采纳来源：{record['source']}。"]
    for item in record["answers"]:
        basis = f"（{item['basis']}）" if item["basis"] else ""
        lines.append(f"  - 取舍作答：{item['qid']}={item['value']}{basis}")
    lines.extend(["", "## 目标与原因", "",
                  f"- 预期改善：{record['improvement']}",
                  f"- 原因：{record['reason']}"])
    lines.extend(_before_after(record["changes"]))
    lines.extend(_impact_lines(record))
    lines.extend(_disposition_lines(record))
    lines.extend(["", "## 保留项", ""])
    lines.extend([f"- {item}" for item in record["keep"]] or ["- 无。"])
    lines.extend(_stage_lines(record))
    lines.extend(_analysis_lines(record))
    lines.extend(_candidate_lines(record))
    lines.extend(_walkthrough_lines(record))
    lines.extend(_verify_lines(record))
    lines.extend(["", "## 状态", ""])
    lines.extend(f"- {label}：{value}"
                 for label, value in _state_lines(states, planned=planned))
    return "\n".join(lines).rstrip() + "\n"


def mark_results(results: list[dict[str, Any]],
                 current_version: str) -> list[dict[str, Any]]:
    """受影响的旧验证结果标明原适用版本:不能证明新方案已通过。"""

    marked: list[dict[str, Any]] = []
    for raw in results:
        item = dict(raw)
        item["applies_version"] = str(item.get("version") or "")
        item["note"] = (f"该结果只适用于 {item['applies_version']},"
                        f"不能证明 {current_version} 的新方案已通过;"
                        f"新方案需按待验证方法重新验证。")
        marked.append(item)
    return marked


def _find_line(lines: list[str], old: str) -> int | None:
    for position, line in enumerate(lines):
        if line.strip() == old:
            return position
    return None


def _reindent(reference: str, text: str) -> str:
    indent = reference[: len(reference) - len(reference.lstrip())]
    return f"{indent}{text}"


def _append_history(text: str, retired: list[dict[str, str]],
                    date: str) -> str:
    """历史段:旧规则逐条记录替代关系,保持可追溯。"""

    lines = text.rstrip("\n").splitlines()
    entries = [f"- {date}：{item['old']} 退出当前有效版本；"
               f"替代：{item['new']}" for item in retired]
    position = next((index for index, line in enumerate(lines)
                     if line.strip() == HISTORY_TITLE), None)
    if position is None:
        lines.extend(["", HISTORY_TITLE, ""])
        lines.extend(entries)
    else:
        end = next((index for index in range(position + 1, len(lines))
                    if lines[index].startswith("## ")), len(lines))
        lines[end:end] = entries
    return "\n".join(lines) + "\n"


def _bump_version(text: str, meta: dict[str, Any]) -> str:
    to_version = str(meta.get("version_to") or "")
    if not to_version or not VERSION_RE.search(text):
        return text
    return VERSION_RE.sub(f"基线版本：{to_version}", text, count=1)


def _before_after(changes: list[dict[str, Any]]) -> list[str]:
    lines = ["## 旧设计到新设计", ""]
    if not changes:
        return lines + ["- 无受影响规则。"]
    for item in changes:
        lines.append(f"- {item['title']}（{item['id']}，{item['relation']}）："
                     f"「{item['old']}」→「{item['new']}」")
    return lines


def _impact_lines(record: dict[str, Any]) -> list[str]:
    impact = record["impact"]
    lines = ["", "## 影响范围", "",
             f"- 必须同步：{'、'.join(impact['must_sync']) or '无'}。",
             f"- 需要开发者取舍：{'、'.join(impact['needs_tradeoff']) or '无'}。",
             f"- 不受影响（保持原样）：{'、'.join(impact['unaffected']) or '无'}。",
             f"- 受影响模块：{'、'.join(impact['modules']) or '无'}。"]
    if impact["questions"]:
        lines.append("- 新增取舍问题：" + "、".join(
            f"{item['id']} {item['title']}" for item in impact["questions"]))
    return lines


def _disposition_lines(record: dict[str, Any]) -> list[str]:
    """被删减功能原作用的处理(取消/转移/简化保留);第 07 票深化。"""

    items = record.get("dispositions") or []
    if not items:
        return []
    lines = ["", "## 被删减功能的作用处理", ""]
    for item in items:
        detail = f"（{item['detail']}）" if item.get("detail") else ""
        lines.append(f"- {item['title']}：{item['label']}{detail}")
    return lines


def _stage_lines(record: dict[str, Any]) -> list[str]:
    stage = record["stage"]
    lines = ["", "## 阶段与对象检查", "",
             f"- 项目阶段：{stage['label']}"
             + (f"（{stage['basis']}）" if stage["basis"] else "")]
    for entry in stage["entries"]:
        lines.append(f"- {entry['label']}：{entry['detail']}"
                     f"（{entry['evidence']}）")
    return lines


def _analysis_lines(record: dict[str, Any]) -> list[str]:
    lines = ["", "## 事实、计算与关联分析", ""]
    if not record["analysis"]:
        return lines + ["- 本轮无额外分析项。"]
    labels = {"fact": "事实", "calculation": "计算", "correlation": "关联"}
    for item in record["analysis"]:
        lines.append(f"- {labels.get(item.get('kind'), '分析')}："
                     f"{item.get('detail')}")
    return lines


def _candidate_lines(record: dict[str, Any]) -> list[str]:
    lines = ["", "## 候选与推演", ""]
    if not record["candidates"]:
        return lines + ["- 本轮无候选方案。"]
    for item in record["candidates"]:
        lines.append(
            f"- {item['name']}（{item['choice']}）：改什么："
            f"{'、'.join(item['changes']) or '—'}；保留："
            f"{'、'.join(item['keeps']) or '—'}；预期改善：{item['improvement']}；"
            f"代价：{item['cost']}；改善证据：{item['evidence_summary']}。")
    return lines


def _walkthrough_lines(record: dict[str, Any]) -> list[str]:
    lines = ["", "## 场景推演", ""]
    for item in record["walkthrough"]:
        lines.append(f"- {item['label']}：{item['detail']}")
    lines.extend(["", "## 待验证", ""])
    if not record["verify"]:
        return lines + ["- 无。"]
    for item in record["verify"]:
        blocking = "阻断当前阶段" if item.get("blocks_stage") else "不阻断当前阶段"
        lines.append(f"- {item['question']}：方法 {item['method']}；{blocking}。")
    return lines


def _verify_lines(record: dict[str, Any]) -> list[str]:
    lines = ["", "## 旧验证结果", ""]
    if not record["results"]:
        return lines + ["- 无受影响的旧验证结果。"]
    for item in record["results"]:
        lines.append(f"- {item['id']}（原适用版本 {item['applies_version']}，"
                     f"{item['result']}）：{item['detail']}。{item['note']}")
    return lines


def _state_lines(states: dict[str, bool], *,
                 planned: bool = False) -> list[tuple[str, str]]:
    labels = (("adopted", "已采纳"), ("saved", "已保存"),
              ("synced", "已同步核心基线"), ("implemented", "已实现"),
              ("verified", "已验证"))
    lines: list[tuple[str, str]] = []
    for key, label in labels:
        if states.get(key):
            lines.append((label, "是"))
        elif planned and key in {"saved", "synced"}:
            lines.append((label, "否（本次计划尚未写入,写入后按实际结果更新）"))
        elif key in {"implemented", "verified"}:
            lines.append((label, "否（无实际运行或效果证据,另行判断）"))
        else:
            lines.append((label, "否"))
    return lines

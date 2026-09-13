#!/usr/bin/env python3
"""Game-Design 模块规格的渲染与缺口核对(统一设计问答框架票 04)。

九类规格内容的唯一渲染位置与适用性核对:设计目的、参与对象、前提与触发、
正常规则、例外与边界、数值与配置、玩家反馈、数据与持续性、验收方式。
不适用的类别写入理由;以「合理、适中」类形容词代替关键行为视为缺口。
另渲染决定来源与历史、未决与延期事项、未采纳内容、重要决定背景与状态交接。

本 module 只渲染与核对,不决定是否写入、不接触受控通道(在 ``spec_draft``)。
"""

from __future__ import annotations

import re
from typing import Any

SECTION_SPECS = (
    ("purpose", "设计目的", "服务的体验与存在理由"),
    ("participants", "参与对象", "角色、物品、资源、界面及相互关系"),
    ("triggers", "前提与触发", "生效条件、触发者与触发时机"),
    ("rules", "正常规则", "输入、操作、处理、状态变化和结果"),
    ("boundaries", "例外与边界",
     "条件不足、上限、重复操作、失败、中途退出及适用的同刻事件"),
    ("numbers", "数值与配置",
     "初值、单位、范围、计算关系、取整、可调项和依据;区分已定值与候选试验值"),
    ("feedback", "玩家反馈", "玩家看到或听到什么、如何理解结果及继续操作"),
    ("persistence", "数据与持续性",
     "保存内容、保存时机、退出重进、离线或跨次游玩的保留规则"),
    ("acceptance", "验收方式",
     "明确初始条件、玩家操作及预期结果;主观体验列出实际验证方法"),
)

VAGUE_WORDS = ("合理", "适中", "适量", "平衡即可", "看着办")
NUMBER_FIELDS = ("name", "value", "unit", "range", "calc", "rounding", "basis")

ADR_CONDITIONS = ("change_cost_high", "confusing_without_context",
                  "real_tradeoff")

ADR_CONDITION_LABELS = {"change_cost_high": "改变成本高",
                        "confusing_without_context": "缺背景会令人困惑",
                        "real_tradeoff": "存在真实取舍"}


def render_spec(module: str, meta: dict[str, Any], parsed: dict[str, Any],
                decision: dict[str, Any]) -> str:
    """九类规格的唯一渲染位置:不适用写理由,缺内容留待 incomplete 报告。"""

    sections = dict(meta.get("sections") or {})
    lines = [f"# {module}：模块规格", "",
             f"维护责任：方案设计。基线版本："
             f"{version_label(meta)}。日期：{meta.get('date') or ''}。",
             f"决定来源：{record_source(parsed, meta)}。",
             f"采纳依据：{adoption_basis(decision)}。"]
    warnings = sections.pop("_warnings", None)
    for key, title, purpose in SECTION_SPECS:
        lines.append("")
        lines.append(f"## {title}")
        lines.append(f"说明：{purpose}。")
        item = dict(sections.get(key) or {})
        content = str(item.get("content") or "").strip()
        note = str(item.get("not_applicable") or "").strip()
        if content:
            lines.append(content)
        elif note:
            lines.append(f"不适用：{note}")
        if key == "numbers":
            lines.extend(_render_numbers(item))
        if key == "acceptance":
            lines.extend(_render_acceptance(item, meta))
        sources = [str(qid) for qid in (item.get("sources") or [])]
        if sources:
            lines.append(f"来源：{'、'.join(sources)}。")
    lines.extend(_render_provenance(parsed, decision, meta))
    lines.extend(_render_open_items(parsed, meta))
    lines.extend(_render_excluded(decision))
    lines.extend(_render_adr(meta))
    lines.extend(_render_states(meta))
    if warnings:
        lines.append("")
        lines.append(f"待确认：{warnings}")
    return "\n".join(lines).rstrip() + "\n"


def section_gaps(meta: dict[str, Any],
                 parsed: dict[str, Any]) -> list[dict]:
    """按适用性核对九类内容:缺关键行为或缺理由的空占位即缺口。"""

    sections = dict(meta.get("sections") or {})
    missing: list[dict] = []
    for key, title, _purpose in SECTION_SPECS:
        item = dict(sections.get(key) or {})
        content = _section_content(key, item)
        note = str(item.get("not_applicable") or "").strip()
        if content:
            if _too_vague(content):
                missing.append({"field": key, "detail":
                                f"{title}以「合理、适中」类形容词代替关键行为,"
                                f"不可检查;须给出可判定规则或边界"})
                continue
            if key == "numbers":
                missing.extend(_number_gaps(item, title))
            if key == "acceptance":
                missing.extend(_acceptance_gaps(item, title))
        elif not note:
            missing.append({"field": key, "detail":
                            f"{title}缺少内容且未说明不适用理由;"
                            f"不用默认值补齐"})
    for qid in (meta.get("blocking_qids") or []):
        if str(qid) not in {entry["qid"] for entry in parsed["pending"]} \
                and str(qid) not in parsed["decisions"]:
            missing.append({"field": f"blocking:{qid}", "detail":
                            f"阻断交接的 {qid} 既未决也无记录,须先澄清"})
    return missing


def record_source(parsed: dict[str, Any], meta: dict[str, Any]) -> str:
    return (f"{meta.get('record_path')}（决定记录格式由 decision_records "
            f"唯一解释;共 {parsed.get('rounds')} 轮）")


def adoption_basis(decision: dict[str, Any]) -> str:
    if not decision["settled"]:
        return "本次没有已采纳决定"
    parts = [f"{qid}（第 {item.get('round') or '?'} 轮）"
             for qid, item in sorted(decision["settled"].items())]
    return "决定记录 " + "、".join(parts)


def version_label(meta: dict[str, Any]) -> str:
    return str(meta.get("version_to") or meta.get("version_from") or "")


def condition_label(cond: str) -> str:
    return ADR_CONDITION_LABELS.get(cond, cond)


def _render_numbers(item: dict[str, Any]) -> list[str]:
    """数值:单位、范围、计算或取整与依据;已定值与候选试验值分开。"""

    lines: list[str] = []
    for title, key in (("已定值", "settled"), ("候选试验值", "trial")):
        rows = list(item.get(key) or [])
        lines.append("")
        lines.append(f"### {title}")
        if not rows:
            lines.append("- 无。")
            continue
        for row in rows:
            parts = [f"- {row.get('name')}：{row.get('value')}"
                     f" {row.get('unit')}",
                     f"范围 {row.get('range')}",
                     f"计算 {row.get('calc')}",
                     f"取整 {row.get('rounding')}",
                     f"依据 {row.get('basis')}"]
            suffix = "（候选试验值,不作当前要求）" if key == "trial" else ""
            lines.append(";".join(parts) + suffix)
    return lines


def _render_acceptance(item: dict[str, Any],
                       meta: dict[str, Any]) -> list[str]:
    """验收:初始条件、玩家操作与预期结果;主观体验列验证问题与方法。"""

    lines = ["", "### 验收场景"]
    cases = list(item.get("cases") or [])
    if not cases:
        lines.append("- 无。")
    for case in cases:
        lines.append(f"- 初始条件：{case.get('initial')}")
        lines.append(f"  操作：{case.get('action')}")
        lines.append(f"  预期结果：{case.get('expected')}")
    subjective = list(meta.get("verification") or []) or list(
        item.get("subjective") or [])
    lines.append("")
    lines.append("### 主观体验验证")
    if not subjective:
        lines.append("- 无（本模块没有需要人判断的主观体验项）。")
        return lines
    for entry in subjective:
        blocks = "是" if entry.get("blocks_stage") else "否"
        lines.append(f"- 验证问题：{entry.get('question')}")
        lines.append(f"  验证方法：{entry.get('method')}")
        lines.append(f"  是否阻断当前阶段：{blocks}")
        if entry.get("evidence"):
            lines.append(f"  实际证据：{entry['evidence']}")
        else:
            lines.append("  实际证据：无（没有原型或试玩证据,不报告验证通过）")
    return lines


def _render_provenance(parsed: dict[str, Any], decision: dict[str, Any],
                       meta: dict[str, Any]) -> list[str]:
    """采纳来源与替代历史:保留历史及替代关系,执行者可追溯。"""

    lines = ["", "## 决定来源与历史"]
    if not decision["settled"]:
        lines.append("- 无已采纳决定。")
    for qid in sorted(decision["settled"]):
        item = decision["settled"][qid]
        parts = [f"- {qid} {item.get('title')}：采纳 {item.get('value')}",
                 f"来源 {item.get('source_label') or '决定记录'}"]
        if item.get("provenance"):
            parts.append(f"建议出处 {item['provenance']}")
        lines.append("；".join(parts) + "。")
    for item in parsed["superseded"]:
        lines.append(f"- {item['qid']} 旧值「{item['value']}」"
                     f"（第 {item.get('round') or '?'} 轮）"
                     f"已被第 {item.get('replaced_round') or '?'} 轮替代;"
                     f"历史保留,旧决定不覆盖其他有效决定。")
    record_path = str(meta.get("record_path") or "")
    if record_path:
        lines.append(f"- 同步状态见决定记录 {record_path} 的各决定同步状态行;"
                     f"本规格只引用,不另存一套记录。")
    return lines


def _render_open_items(parsed: dict[str, Any],
                       meta: dict[str, Any]) -> list[str]:
    """未决项、延期事项与影响原样保留,不补默认值。"""

    impacts = dict(meta.get("pending_impacts") or {})
    lines = ["", "## 未决与延期事项"]
    pending = list(parsed["pending"])
    if not pending and not impacts:
        lines.append("- 无。")
        return lines
    seen: set[str] = set()
    for item in pending:
        qid = item["qid"]
        seen.add(qid)
        impact = impacts.get(qid) or "影响未单独列,仍为未决。"
        lines.append(f"- {qid} {item['title']}：{item['status']}；影响：{impact}")
    for qid in sorted(impacts):
        if qid in seen:
            continue
        lines.append(f"- {qid}：未决策略；影响：{impacts[qid]}")
    return lines


def _render_excluded(decision: dict[str, Any]) -> list[str]:
    """未采纳内容:候选、临时假设与未决项保持各自身份。"""

    lines = ["", "## 未采纳内容"]
    items = decision["excluded"] or []
    if not items:
        lines.append("- 无。")
        return lines
    for item in items:
        lines.append(f"- {item['kind']}：{item['detail']}（不是当前要求）")
    return lines


def _render_adr(meta: dict[str, Any]) -> list[str]:
    """重要决定背景:仅三项条件同时成立才单独记录。"""

    lines = ["", "## 重要决定背景"]
    accepted = [item for item in (meta.get("adr") or [])
                if all(item.get(cond) for cond in ADR_CONDITIONS)]
    if not accepted:
        lines.append("- 无（没有同时满足改变成本高、缺背景会令人困惑、"
                     "存在真实取舍三项条件的决定）。")
        return lines
    for item in accepted:
        lines.append(f"### {item.get('title')}")
        lines.append(str(item.get("background") or ""))
    return lines


def _render_states(meta: dict[str, Any]) -> list[str]:
    """状态分工:采纳、保存、同步、实现、验证分别表达。"""

    lines = ["", "## 状态与交接", "- 本模块可独立交接;不替代全游戏完成结论。"]
    lines.append(f"- 决定记录：{meta.get('record_path')}"
                 f"（同步状态见记录内各决定的同步状态行）。")
    lines.append(f"- 核心基线：{meta.get('design_path')}"
                 f"（登记基线版本与双指纹,具体规则集中维护在模块规格）。")
    lines.append("- 实现状态：未实现（设计交接不自动授权制作,不自动启动制作）。")
    lines.append("- 验证状态：未验证（没有原型或试玩证据,不报告相应验证通过）。")
    return lines


def _section_content(key: str, item: dict[str, Any]) -> str:
    """类别的实际内容:正文,或该方法专属的结构化内容(数值、验收)。"""

    content = str(item.get("content") or "").strip()
    if content:
        return content
    if key == "numbers" and (item.get("settled") or item.get("trial")):
        return "数值与配置由已定值与候选试验值分列说明。"
    if key == "acceptance" and (item.get("cases") or item.get("subjective")):
        return "验收方式由验收场景与主观体验验证分列说明。"
    return ""


def _too_vague(text: str) -> bool:
    """关键行为是否被「合理、适中」类形容词代替而不可检查。"""

    stripped = re.sub(r"[\s。；;,、]", "", text)
    return any(word in text for word in VAGUE_WORDS) and (
        len(stripped) <= 12 or any(
            f"{word}即可" in text or f"{word}、" in text
            for word in VAGUE_WORDS))


def _number_gaps(item: dict[str, Any], title: str) -> list[dict]:
    missing: list[dict] = []
    for key in ("settled", "trial"):
        for row in item.get(key) or []:
            empty = [field for field in NUMBER_FIELDS
                     if not str(row.get(field) or "").strip()]
            if empty:
                missing.append({"field": f"numbers:{key}:{row.get('name')}",
                                "detail": f"{title} 的 {row.get('name')} "
                                          f"缺少:{'、'.join(empty)}"})
    return missing


def _acceptance_gaps(item: dict[str, Any], title: str) -> list[dict]:
    missing: list[dict] = []
    for index, case in enumerate(item.get("cases") or [], start=1):
        empty = [field for field in ("initial", "action", "expected")
                 if not str(case.get(field) or "").strip()]
        if empty:
            missing.append({"field": f"acceptance:case{index}", "detail":
                            f"{title} 第 {index} 个验收场景缺少:"
                            f"{'、'.join(empty)}"})
    for entry in item.get("subjective") or []:
        for field, label in (("question", "验证问题"), ("method", "验证方法")):
            if not str(entry.get(field) or "").strip():
                missing.append({"field": f"acceptance:{label}", "detail":
                                f"{title} 的主观体验缺{label}"})
        if "blocks_stage" not in entry:
            missing.append({"field": "acceptance:blocks_stage", "detail":
                            f"{title} 的主观体验未说明是否阻断当前阶段"})
    return missing

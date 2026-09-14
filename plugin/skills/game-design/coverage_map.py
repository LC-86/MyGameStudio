#!/usr/bin/env python3
"""Game-Design 十二领域覆盖地图(统一设计问答框架票 05)。

公开 interface:
  DOMAINS: tuple[(key, title)]
  build_map(material) -> dict
  stage_status(material, stage=..., ...) -> dict

从玩法片段、画面、操作、感受与提供的参考提取已知内容,整理典型游玩经历并
标明原始意图、助手提案与信息缺口;已有资料与决定沿用而不重问。维护覆盖
地图:十二领域逐项给出适用性、状态及已有规则或缺口/未知定位。不适用须有
理由,未查清不得冒充不适用;无依据且为填模板而新增的系统标为填充模板。
范围分层保存完整愿景、当前成稿版本、后续方向与范围外内容,当前范围不足
时只保留必要澄清问题。推进焦点按阻断与影响排序,不一次抛全套问卷。

地图用于查漏与推进:本 module 只整理与判定,不写入、不重述全文,也不要求
每个领域新建文件。
"""

from __future__ import annotations

from typing import Any

DOMAINS = (
    ("project", "项目目标与边界"),
    ("appeal", "核心吸引力"),
    ("core_play", "核心玩法与决策"),
    ("journey", "完整游玩过程"),
    ("systems", "系统与相互关系"),
    ("growth", "成长与资源流动"),
    ("content", "内容与叙事"),
    ("ui", "操作、界面与引导"),
    ("presentation", "美术、动画与声音"),
    ("release", "商业化与发布需求"),
    ("tech", "技术与数据约束"),
    ("version", "版本范围与验收"),
)

STAGE_LABELS = {
    "concept": "概念说明",
    "prototype_spec": "原型所需规格",
    "current_version": "当前版本完整设计",
}

EXPERIENCE_LABELS = {
    "intent": "原始意图",
    "proposal": "助手提案",
    "gap": "信息缺口",
    "decision": "已有决定",
}

KNOWN_CATEGORIES = (
    ("gameplay", "玩法"), ("visuals", "画面"), ("operations", "操作"),
    ("feelings", "感受"), ("references", "参考"),
)

NEW_SYSTEM_KINDS = ("系统", "功能", "新增系统", "玩法")


def build_map(material: dict[str, Any]) -> dict[str, Any]:
    """整理已知内容与十二领域地图,给出范围分层与下一步推进焦点。"""

    domains = _domain_entries(material.get("domains") or {})
    return {
        "op": "coverage",
        "game": str(material.get("game") or ""),
        "known": {key: list(values or [])
                  for key, values in (material.get("known") or {}).items()},
        "experience": _experience(material),
        "reused": _reused(material),
        "domains": domains,
        "scope": _scope(material),
        "proposals": _proposals(material, domains),
        "template_fill": _template_fill(domains),
        "next_focus": _next_focus(domains, material),
    }


def stage_status(material: dict[str, Any], *, stage: str,
                 **ignored: Any) -> dict[str, Any]:
    """阶段完成由所需成果决定,不按固定轮数或文档页数判定。

    ``**ignored`` 显式忽略轮数、页数一类计数输入:它们不参与判定,传入也不
    改变结论,避免把这些数字写成阶段门槛。
    """

    label = STAGE_LABELS.get(stage, stage)
    evidence = dict((material.get("stage_evidence") or {}).get(stage) or {})
    required = [str(item) for item in evidence.get("required") or []]
    met = [str(item) for item in evidence.get("met") or []]
    missing = [item for item in required if item not in met]
    if not required:
        missing.append(f"未给出{label}的所需成果:不能因目录齐全判为完成")
    complete = bool(required) and not missing
    return {"stage": stage, "label": label, "required": required,
            "met": met, "missing": missing, "complete": complete}


def _domain_entries(raw_domains: dict[str, Any]) -> dict[str, dict[str, Any]]:
    """十二领域逐项状态:已有规则 / 缺口 / 不适用（有理由）/ 未查清。"""

    entries: dict[str, dict[str, Any]] = {}
    for key, title in DOMAINS:
        raw = dict(raw_domains.get(key) or {})
        applies = raw.get("applies")
        reason = str(raw.get("reason") or "").strip()
        if applies is True:
            if raw.get("gap"):
                status = "gap"
            else:
                status = "rule" if raw.get("rules") else "gap"
        elif applies is False:
            status = "not_applicable" if reason else "gap"
        else:
            status = "unknown"
        entry = {**raw, "key": key, "title": title, "applies": applies,
                 "status": status}
        if status == "gap" and applies is False:
            entry.setdefault("gap", f"{title}写明不适用但未给出理由")
        entries[key] = entry
    return entries


def _experience(material: dict[str, Any]) -> list[dict[str, Any]]:
    """典型游玩经历:原始意图、助手提案与信息缺口分别标明。"""

    items: list[dict[str, Any]] = []
    for raw in material.get("experience") or []:
        source = str(raw.get("source") or "intent")
        items.append({"text": str(raw.get("text") or ""),
                      "source": EXPERIENCE_LABELS.get(source, source),
                      "origin": source})
    for key, _label in KNOWN_CATEGORIES:
        for text in (material.get("known") or {}).get(key) or []:
            items.append({"text": str(text), "source": "原始意图",
                          "origin": key})
    return items


def _reused(material: dict[str, Any]) -> list[str]:
    """已有有效资料与已明确决定沿用,不要求开发者重新解释。"""

    existing = dict(material.get("existing") or {})
    reused = [f"沿用已有资料 {item.get('path')}"
              for item in existing.get("materials") or []]
    reused.extend(f"沿用已有决定 {item.get('qid')}：{item.get('value')}"
                  for item in existing.get("decisions") or [])
    return reused


def _scope(material: dict[str, Any]) -> dict[str, Any]:
    """完整愿景、当前成稿版本、后续方向与范围外内容分层保存。"""

    raw = dict(material.get("scope") or {})
    current = [{**dict(item), "text": str(item.get("text") or "")}
               for item in raw.get("current") or []
               if str(item.get("source") or "") != "vision"]
    clarify = [{"question": str(item.get("question") or ""),
                "why_needed": str(item.get("why_needed") or "")}
               for item in raw.get("clarify") or []]
    return {"vision": [str(item) for item in raw.get("vision") or []],
            "current": current,
            "later": [str(item) for item in raw.get("later") or []],
            "out_of_scope": [str(item) for item in raw.get("out_of_scope") or []],
            "clarify": clarify}


def _proposals(material: dict[str, Any],
               domains: dict[str, dict[str, Any]]) -> list[dict[str, Any]]:
    """AI 主动提出的规则、数值与边界方案:保持提案身份,不冒充已采纳。"""

    items: list[dict[str, Any]] = []
    for key, title in DOMAINS:
        for raw in (domains.get(key) or {}).get("proposals") or []:
            items.append({"domain": title, "kind": str(raw.get("kind") or "提案"),
                          "detail": str(raw.get("detail") or ""),
                          "basis": str(raw.get("basis") or ""),
                          "serves": str(raw.get("serves") or ""),
                          "adopted": False})
    for raw in material.get("experience") or []:
        if str(raw.get("source") or "") != "proposal":
            continue
        items.append({"domain": None, "kind": "提案",
                      "detail": str(raw.get("text") or ""), "basis": "",
                      "serves": "", "adopted": False})
    return items


def _template_fill(domains: dict[str, dict[str, Any]]) -> list[dict[str, Any]]:
    """无依据且不是为已有范围服务的新增系统:标为填充模板,不进当前版本。"""

    flagged: list[dict[str, Any]] = []
    for entry in domains.values():
        for item in entry.get("proposals") or []:
            proposal = dict(item)
            kind = str(proposal.get("kind") or "")
            if kind not in NEW_SYSTEM_KINDS:
                continue
            if proposal.get("basis") or proposal.get("serves"):
                continue
            flagged.append({"domain": entry["title"], "detail": str(
                proposal.get("detail") or proposal)})
    return flagged


def _next_focus(domains: dict[str, dict[str, Any]],
                material: dict[str, Any]) -> list[dict[str, Any]]:
    """推进焦点:按阻断、全局影响与返工风险排序,不一次抛出全套问卷。"""

    gaps = [entry for entry in domains.values() if entry["status"] == "gap"]
    gaps.sort(key=lambda entry: (
        0 if entry.get("blocks") else 1,
        0 if entry.get("impact_level") == "global" else 1,
        0 if entry.get("rework_risk") == "high" else 1,
        [key for key, _title in DOMAINS].index(entry["key"])))
    limit = int(material.get("focus_limit") or 3)
    focus: list[dict[str, Any]] = []
    for entry in gaps[:limit]:
        focus.append({
            "domain": entry["key"], "title": entry["title"],
            "gap": str(entry.get("gap") or ""),
            "method": str(entry.get("method") or ""),
            "impact": str(entry.get("impact") or ""),
            "blocks": bool(entry.get("blocks")),
            "why": _focus_reason(entry)})
    return focus


def _focus_reason(entry: dict[str, Any]) -> str:
    parts = []
    if entry.get("blocks"):
        parts.append("阻断后续模块")
    if entry.get("impact_level") == "global":
        parts.append("影响全局")
    if entry.get("rework_risk") == "high":
        parts.append("返工风险高")
    if entry.get("impact"):
        parts.append(f"影响：{entry['impact']}")
    if entry.get("gap"):
        parts.append(f"当前缺口：{entry['gap']}")
    if entry.get("method"):
        parts.append(f"建议动作：{entry['method']}")
    if not parts:
        parts.append(f"{entry['title']}尚无规则与缺口说明,先澄清")
    return "；".join(parts)

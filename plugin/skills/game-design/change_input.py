#!/usr/bin/env python3
"""已有设计变更的材料整理(统一设计问答框架票 06)。

公开 interface:
  statements(material) -> dict
  questions(tradeoffs, start, module) -> list[dict]
  candidates(material, impact) -> list[dict]
  unresolved_candidates(candidates) -> list[dict]
  walkthrough(material) -> list[dict]
  record(material, meta, change, impact, stage, organization, questions) -> dict

把本轮材料整理成变更流程可直接使用的结构化内容:四项变更说明(修改对象、
原因、预期改善、需要保留的内容)、由取舍项生成的新增问题、候选对比(改什么、
保留什么、预期改善、代价与改善证据)、场景推演(自洽性与体验改善分开)与
变更记录材料。只换名或转移复杂度支撑的候选不构成原问题已解决的证据。

删减变更为后续票(第 07 票)留出接缝:受影响项可携带 ``disposition``
(一起取消 / 转移给已有系统 / 更简单方式保留),本 module 原样带入记录,
不在本票展开删减的作用处理与残留依赖检查。

本 module 只整理,不判定同步范围、不写入文件。
"""

from __future__ import annotations

from typing import Any

from change_impact import DEPTH_LABELS
from change_render import mark_results

SCENARIO_LABELS = (
    ("new_player", "新玩家"), ("existing_progress", "已有进度"),
    ("insufficient_resources", "资源不足"), ("exit", "退出"),
    ("related_paths", "相关路径"),
)

FINDING_KINDS = {"consistency": "自洽性", "experience": "体验改善"}

DISPOSITION_LABELS = {"cancel": "一起取消", "transfer": "转移给已有系统",
                      "simplify": "更简单方式保留"}


def statements(material: dict[str, Any]) -> dict[str, Any]:
    """四项变更说明;请求状态区分只提出问题与已作出修改决定。"""

    request = dict(material.get("request") or {})
    change = dict(material.get("change") or {})
    targets = [str(item) for item in change.get("targets") or []]
    labels = [str(item) for item in change.get("target_labels") or []]
    if not labels:
        labels = [str(item.get("title") or item.get("id") or "")
                  for item in material.get("design_items") or []
                  if str(item.get("id")) in targets]
    return {
        "targets": targets,
        "target_labels": [label for label in labels if label],
        "reason": str(change.get("reason") or ""),
        "improvement": str(change.get("improvement") or ""),
        "keep": [str(item) for item in change.get("keep") or []],
        "decided_direction": str(request.get("decided_direction") or ""),
        "request_text": str(request.get("text") or ""),
        "answers": [{"qid": str(item.get("qid") or ""),
                     "value": str(item.get("value") or ""),
                     "basis": str(item.get("basis") or "")}
                    for item in change.get("answers") or []],
        "source": _source(request, change, targets),
    }


def _source(request: dict[str, Any], change: dict[str, Any],
            targets: list[str]) -> str:
    """采纳来源:已决定的修改不重复确认;取舍作答逐项记入来源。"""

    answers = [item for item in change.get("answers") or []
               if item.get("qid")]
    if str(request.get("state") or "") == "decided" and targets:
        text = ("开发者已作出的修改决定(本轮不重复确认是否采纳);"
                "决定者：开发者")
        if answers:
            text += ";取舍问题作答：" + "、".join(
                f"{item.get('qid')}={item.get('value')}" for item in answers)
        return text
    return "开发者提出待讨论的问题;处理方式待本轮取舍"


def questions(tradeoffs: list[dict[str, Any]], start: int,
              module: str) -> list[dict[str, Any]]:
    """新增取舍问题:带候选处理方式与推荐,不重复确认已定方向。"""

    items: list[dict[str, Any]] = []
    for index, item in enumerate(tradeoffs):
        qid = f"Q{start + index}"
        items.append({
            "id": qid,
            "source_item": str(item.get("id") or ""),
            "title": f"{item['title']}：变更后的处理方式",
            "body": f"「{item.get('old_text') or ''}」随本次变更失效,"
                    f"新的处理方式选哪一种?",
            "options": dict(item.get("options") or {}),
            "recommendation": str(item.get("recommendation") or ""),
            "reason": str(item.get("reason") or ""),
            "impact": str(item.get("impact") or ""),
            "relation": item["relation"],
            "module": module,
            "depends_on": [],
        })
    return items


def candidates(material: dict[str, Any],
               impact: dict[str, Any]) -> list[dict[str, Any]]:
    """候选:改什么、保留什么、预期改善、代价与改善证据(换名不算改善)。"""

    prepared: list[dict[str, Any]] = []
    for raw in material.get("candidates") or []:
        item = dict(raw)
        evidence = [dict(entry) for entry in item.get("evidence") or []]
        kinds = {str(entry.get("kind") or "") for entry in evidence}
        item["evidence"] = evidence
        item["rename_only"] = bool(evidence) and kinds <= {"rename"}
        item["choice"] = "采纳" if item.get("chosen") else "未采纳"
        item["evidence_summary"] = _evidence_summary(item)
        prepared.append(item)
    if impact["needs_tradeoff"] and not any(
            item.get("chosen") for item in prepared):
        prepared.extend(_option_candidates(impact["needs_tradeoff"]))
    return prepared


def _evidence_summary(item: dict[str, Any]) -> str:
    if item["rename_only"]:
        return "仅换名或转移复杂度,不构成改善证据,只记为改了什么"
    if item["evidence"]:
        return "；".join(str(entry.get("detail") or "")
                         for entry in item["evidence"])
    return "无改善证据"


def _option_candidates(tradeoffs: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """受影响项自带的候选处理方式:未标注证据的只记方案,不算改善证据。"""

    prepared: list[dict[str, Any]] = []
    for item in tradeoffs:
        for key, text in sorted(dict(item.get("options") or {}).items()):
            prepared.append({
                "name": f"{item['title']} 选项 {key}：{text}",
                "changes": [str(text)], "keeps": ["保留项不变"],
                "improvement": str(item.get("reason") or ""),
                "cost": str(item.get("impact") or ""),
                "evidence": [], "evidence_summary": "无改善证据",
                "rename_only": False,
                "choice": "推荐" if key == item.get("recommendation")
                else "备选",
                "source_item": item["id"]})
    return prepared


def unresolved_candidates(candidates_list: list[dict[str, Any]]) -> list[dict]:
    """只有换名或转移复杂度支撑的候选:不能当作问题已解决。"""

    items: list[dict[str, Any]] = []
    for item in candidates_list:
        if not item.get("rename_only") or not item.get("chosen"):
            continue
        items.append({
            "kind": "改善证据不足", "detail":
            f"{item['name']}只把原机制换名或转移复杂度,"
            f"不构成原问题已解决的证据",
            "method": "补可核对的改善证据,或改选有实际变化的方案",
            "impact": "不能据此报告问题已解决"})
    return items


def walkthrough(material: dict[str, Any]) -> list[dict[str, Any]]:
    """适用场景推演:数值/流程自洽与实际体验改善分开标注。"""

    items: list[dict[str, Any]] = []
    scenarios = dict(material.get("scenarios") or {})
    for key, label in SCENARIO_LABELS:
        raw = dict(scenarios.get(key) or {})
        if raw.get("applies") is False:
            items.append({"key": key, "label": label,
                          "detail": f"不适用："
                                    f"{raw.get('reason') or '本轮不适用'}"})
            continue
        if not raw:
            items.append({"key": key, "label": label,
                          "detail": "未提供推演结果,先按未推演处理"})
            continue
        for finding in raw.get("findings") or []:
            items.append({"key": key, "label": label,
                          "detail": _finding_text(finding)})
    return items


def _finding_text(finding: dict[str, Any]) -> str:
    kind = FINDING_KINDS.get(str(finding.get("kind") or ""), "推演")
    text = f"（{kind}）{finding.get('text')}"
    method = str(finding.get("method") or "")
    if method:
        blocking = "阻断当前阶段" if finding.get("blocks_stage") \
            else "不阻断当前阶段"
        text += f"；方法：{method}；{blocking}"
    return text


def record(material: dict[str, Any], meta: dict[str, Any],
           change: dict[str, Any], impact: dict[str, Any],
           stage: dict[str, Any], organization: dict[str, Any],
           questions_list: list[dict[str, Any]]) -> dict[str, Any]:
    """变更记录材料:前后差异、影响、阶段、推演、验证与状态。"""

    depth = str(material.get("depth") or "module")
    return {
        "module": str(meta.get("module") or ""),
        "depth": depth,
        "depth_label": DEPTH_LABELS.get(depth, depth),
        "target_labels": change["target_labels"],
        "reason": change["reason"],
        "improvement": change["improvement"],
        "keep": change["keep"],
        "source": change["source"],
        "answers": change["answers"],
        "questions": questions_list,
        "changes": impact["changes"],
        "impact": {
            "must_sync": [item["id"] for item in impact["must_sync"]],
            "needs_tradeoff": [item["id"] for item in impact["needs_tradeoff"]],
            "unaffected": [item["id"] for item in impact["unaffected"]],
            "modules": sorted(impact["by_module"]),
            "questions": questions_list},
        "dispositions": dispositions(impact["must_sync"]),
        "stage": stage,
        "organization": organization,
        "analysis": [dict(item) for item in material.get("analysis") or []],
        "candidates": impact["candidates"],
        "walkthrough": walkthrough(material),
        "verify": organization["verification"],
        "results": mark_results(list(material.get("invalidated_results")
                                     or []),
                                str(meta.get("version_to") or "")),
    }


def dispositions(affected: list[dict[str, Any]]) -> list[dict[str, str]]:
    """删减类变更的作用处理透传(第 07 票深化);未标注的项不在此列出。"""

    items: list[dict[str, str]] = []
    for item in affected:
        raw = str(item.get("disposition") or "")
        if not raw:
            continue
        items.append({"id": str(item.get("id") or ""),
                      "title": str(item.get("title") or ""),
                      "kind": raw,
                      "label": DISPOSITION_LABELS.get(raw, raw),
                      "detail": str(item.get("disposition_detail") or "")})
    return items

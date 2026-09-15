#!/usr/bin/env python3
"""已有设计变更的影响分析与阶段适配(统一设计问答框架票 06)。

公开 interface:
  LANES / DEPTH_LABELS / STAGE_LABELS / STAGE_OBJECTS
  analyze(material) -> dict
  stage_check(material) -> dict
  organize(material, impact) -> dict

沿**实际依赖**追踪变更对象的直接与间接影响(不以文件相邻为边界),把结果
分成「必须同步」「需要开发者取舍」「不受影响」;需要取舍的项带候选处理方式
与推荐,成为新增取舍问题。按项目阶段给出需要核对的对象(只有设计 / 已开发
未发布 / 已发布有玩家),实际存在性分「存在、不存在、未核实」三档:未知不得
当作不存在,也不机械追问不存在的补偿或迁移。变更深度决定工作组织方式:
局部微调直接处理,模块调整用当前模块问题组,结构性修改检查受影响的多个
模块,方向性变化重新审视相关核心方向并保留其余有效决定。

本 module 只分析、核对与组织,不渲染交付内容、不写入文件。
"""

from __future__ import annotations

from typing import Any

LANES = (
    ("rules", "玩法规则"), ("growth", "成长资源"), ("ui", "界面引导"),
    ("content", "内容资产"), ("data", "数据"), ("acceptance", "验收"),
)

DEPTH_LABELS = {
    "local_tweak": "局部明确微调",
    "module": "模块调整",
    "structural": "结构性修改",
    "directional": "方向性变化",
}

STAGE_LABELS = {
    "design_only": "只有设计，尚未实现",
    "developed_unreleased": "已开发，尚未发布",
    "released": "已发布，有实际玩家",
}

STAGE_OBJECTS = {
    "design_only": (
        ("rules", "规则"), ("flow", "流程"), ("numbers", "数值"),
        ("content_list", "内容制作清单"), ("acceptance", "验收要求")),
    "developed_unreleased": (
        ("rules", "规则"), ("flow", "流程"), ("numbers", "数值"),
        ("content_list", "内容制作清单"), ("acceptance", "验收要求"),
        ("implementation", "现有实现"), ("ui", "界面"), ("resources", "资源"),
        ("tests", "测试"), ("existing_data", "已有数据"),
        ("save_compat", "存档兼容")),
    "released": (
        ("rules", "规则"), ("flow", "流程"), ("numbers", "数值"),
        ("content_list", "内容制作清单"), ("acceptance", "验收要求"),
        ("implementation", "现有实现"), ("ui", "界面"), ("resources", "资源"),
        ("tests", "测试"), ("existing_data", "已有数据"),
        ("save_compat", "存档兼容"), ("player_progress", "玩家进度"),
        ("pending_resources", "待领资源"), ("entitlements", "已有权益"),
        ("migration", "迁移"), ("release_plan", "发布安排")),
}

UNKNOWN_STAGE_LABEL = "未核实"


def analyze(material: dict[str, Any]) -> dict[str, Any]:
    """沿依赖追踪直接与间接影响,把受影响项分成必须同步与需要取舍。"""

    answers = {str(item.get("qid")): str(item.get("value"))
               for item in (material.get("change") or {}).get("answers") or []
               if item.get("qid")}
    items = [_apply_answer(dict(item), answers)
             for item in material.get("design_items") or []]
    change = dict(material.get("change") or {})
    targets = [str(item) for item in change.get("targets") or []]
    reached = _trace(items, targets)
    depth = str(material.get("depth") or "module")
    touched_modules = {items[i]["module"] for i in reached
                       if items[i].get("module")}
    must_sync: list[dict[str, Any]] = []
    tradeoffs: list[dict[str, Any]] = []
    unresolved: list[dict[str, Any]] = []
    unaffected: list[dict[str, Any]] = []
    for index, item in enumerate(items):
        hit = reached.get(index)
        if hit is None:
            unaffected.append(_unaffected(item, touched_modules, depth))
            continue
        entry = {**item, "depth": hit["depth"], "via": hit["via"],
                 "path": hit["path"], "relation": _relation(hit)}
        if item.get("resolution") or item.get("new_text"):
            must_sync.append(entry)
        elif item.get("options"):
            tradeoffs.append(entry)
        else:
            unresolved.append(entry)
    return {
        "targets": targets,
        "must_sync": must_sync,
        "needs_tradeoff": tradeoffs,
        "unresolved": unresolved,
        "unaffected": unaffected,
        "lanes": _lanes(items, must_sync, tradeoffs, unaffected,
                        material.get("checked_lanes") or []),
        "by_module": _by_module(must_sync + tradeoffs),
        "trace": [{"id": item["id"], "depth": item["depth"],
                   "path": item["path"], "relation": item["relation"]}
                  for item in must_sync + tradeoffs],
    }


def stage_check(material: dict[str, Any]) -> dict[str, Any]:
    """按阶段核对实际存在的对象;未知不得当作不存在。"""

    stage = str(material.get("stage") or "")
    known = stage in STAGE_LABELS
    kinds = STAGE_OBJECTS.get(stage) or _all_kinds()
    objects = dict(material.get("objects") or {})
    entries = [_object_entry(key, label, objects.get(key))
               for key, label in kinds]
    return {
        "stage": stage,
        "known": known,
        "label": STAGE_LABELS.get(stage, UNKNOWN_STAGE_LABEL),
        "basis": str(material.get("stage_basis") or ""),
        "entries": entries,
        "present": [item["key"] for item in entries
                    if item["state"] == "exists"],
        "absent": [item["key"] for item in entries
                   if item["state"] == "absent"],
        "unverified": [item["key"] for item in entries
                       if item["state"] == "unverified"],
        "missing": _stage_missing(entries, known, stage),
    }


def organize(material: dict[str, Any], impact: dict[str, Any]) -> dict[str, Any]:
    """按变更深度组织工作:问题组、受影响模块、核心方向与验证要求。"""

    depth = str(material.get("depth") or "module")
    return {
        "depth": depth,
        "label": DEPTH_LABELS.get(depth, depth),
        "module": str(material.get("module") or ""),
        "modules": sorted(impact["by_module"]),
        "directions": _directions(material, depth, impact),
        "verification": _verification(material, depth),
        "note": _depth_note(depth),
    }


def _trace(items: list[dict[str, Any]],
           targets: list[str]) -> dict[int, dict[str, Any]]:
    """从变更对象出发按依赖 BFS:变更对象 0 层,依赖它的逐层留痕。"""

    reached: dict[int, dict[str, Any]] = {}
    frontier: dict[str, list[str]] = {}
    target_set = {str(target) for target in targets}
    for position, item in enumerate(items):
        item_id = str(item.get("id"))
        if item_id not in target_set:
            continue
        reached[position] = {"depth": 0, "via": item_id, "path": [item_id]}
        frontier[item_id] = [item_id]
    depth = 0
    while frontier:
        depth += 1
        following: dict[str, list[str]] = {}
        for position, item in enumerate(items):
            if position in reached:
                continue
            for dependency in item.get("depends_on") or []:
                source = frontier.get(str(dependency))
                if source is None:
                    continue
                reached[position] = {"depth": depth, "via": str(dependency),
                                     "path": source + [str(item.get("id"))]}
                following[str(item.get("id"))] = reached[position]["path"]
                break
        frontier = following
    return reached


def _apply_answer(item: dict[str, Any],
                  answers: dict[str, str]) -> dict[str, Any]:
    """取舍答复按来源项落到规则行:选中的选项成为新的当前规则。"""

    qid = str(item.get("question_id") or "")
    value = answers.get(qid)
    if not value:
        return item
    options = dict(item.get("options") or {})
    item["decided"] = value
    item["decided_by"] = qid
    chosen = str(options.get(value) or "")
    if chosen and not item.get("new_text"):
        text = chosen if chosen.startswith("-") else f"- {chosen}"
        if text[-1:] not in "。；;.":
            text += "。"
        item["new_text"] = text
    if not item.get("resolution"):
        item["resolution"] = f"按{qid}={value}采纳的当前处理方式。"
    return item


def _relation(hit: dict[str, Any]) -> str:
    """按依赖深度写明实际关系:变更对象本身 / 直接依赖 / 经谁间接依赖。"""

    depth = int(hit["depth"])
    if depth == 0:
        return "变更对象本身"
    if depth == 1:
        return f"直接依赖变更对象（{hit['via']}）"
    return f"间接依赖（经 {' → '.join(hit['path'][:-1])}）"


def _unaffected(item: dict[str, Any], touched_modules: set[str],
                depth: str) -> dict[str, Any]:
    """不受影响项:写明实际关系核对依据,不以文件相邻判定。"""

    reason = str(item.get("unaffected_reason") or "").strip()
    if not reason:
        if item.get("module") in touched_modules and depth in {
                "structural", "directional"}:
            reason = "同一模块检查:不依赖变更对象,按实际关联核对"
        else:
            reason = "与变更对象没有实际依赖关系,不在影响范围"
    return {**item, "reason": reason}


def _lanes(items: list[dict[str, Any]], must_sync: list[dict],
           tradeoffs: list[dict], unaffected: list[dict],
           checked: list[Any]) -> list[dict[str, Any]]:
    """六个方面各自给出结论;没有条目的方面须说明已核对。"""

    checked_keys = {str(key) for key in checked}
    summary: list[dict[str, Any]] = []
    for key, title in LANES:
        entries = [item for item in items if item.get("lane") == key]
        sync_ids = [item["id"] for item in must_sync
                    if item.get("lane") == key]
        tradeoff_ids = [item["id"] for item in tradeoffs
                        if item.get("lane") == key]
        unaffected_ids = [item["id"] for item in unaffected
                          if item.get("lane") == key]
        summary.append({
            "key": key, "title": title, "items": [item["id"] for item in entries],
            "must_sync": sync_ids, "needs_tradeoff": tradeoff_ids,
            "unaffected": unaffected_ids,
            "examined": bool(entries) or key in checked_keys,
            "detail": _lane_detail(sync_ids, tradeoff_ids, unaffected_ids)})
    return summary


def _lane_detail(sync_ids: list[str], tradeoff_ids: list[str],
                 unaffected_ids: list[str]) -> str:
    if not (sync_ids or tradeoff_ids or unaffected_ids):
        return "本轮变更未触及该方面（按实际依赖核对,无受影响项）"
    parts = []
    if sync_ids:
        parts.append("必须同步：" + "、".join(sync_ids))
    if tradeoff_ids:
        parts.append("需要取舍：" + "、".join(tradeoff_ids))
    if unaffected_ids:
        parts.append("不受影响：" + "、".join(unaffected_ids))
    return "；".join(parts)


def _by_module(affected: list[dict[str, Any]]) -> dict[str, list[str]]:
    grouped: dict[str, list[str]] = {}
    for item in affected:
        module = str(item.get("module") or "")
        grouped.setdefault(module, []).append(str(item.get("id")))
    return grouped


def _object_entry(key: str, label: str,
                  raw: dict[str, Any] | None) -> dict[str, Any]:
    """存在性三档:存在、不存在、未核实（不得当作不存在）。"""

    if not raw:
        state, evidence = "unverified", "未提供核对结果,先按未核实处理"
    elif raw.get("exists") is True:
        state, evidence = "exists", str(raw.get("evidence") or "已核实存在")
    elif raw.get("exists") is False:
        state, evidence = "absent", str(raw.get("evidence") or "已核实不存在")
    else:
        state, evidence = "unverified", str(raw.get("evidence") or "存在性未知")
    label_text = {"exists": "存在,需要处理", "absent": "不存在,不必处理",
                  "unverified": "未核实,不能当作不存在"}[state]
    return {"key": key, "label": label, "state": state, "detail": label_text,
            "evidence": evidence}


def _stage_missing(entries: list[dict[str, Any]], known: bool,
                   stage: str) -> list[dict[str, Any]]:
    missing: list[dict[str, Any]] = []
    if not known:
        missing.append({
            "kind": "阶段未核实", "detail":
            "项目阶段未核实:对象存在性不能当作不存在,"
            "也不生成并不存在的补偿或迁移问题",
            "method": "先核对工作区资料与实际状态,确认阶段",
            "impact": "阶段决定需要检查的对象与处理范围"})
    unverified = [item["label"] for item in entries
                  if item["state"] == "unverified" and known]
    if unverified:
        missing.append({
            "kind": "对象未核实", "detail":
            "、".join(unverified) + "存在性未核实,不能当作不存在",
            "method": "查工作区资料或询问开发者核实",
            "impact": "存在时需一并处理,未核实不得写进「无此对象」"})
    del stage
    return missing


def _all_kinds() -> tuple[tuple[str, str], ...]:
    kinds: list[tuple[str, str]] = []
    for stage in ("design_only", "developed_unreleased", "released"):
        for entry in STAGE_OBJECTS[stage]:
            if entry not in kinds:
                kinds.append(entry)
    return tuple(kinds)


def _directions(material: dict[str, Any], depth: str,
                impact: dict[str, Any]) -> dict[str, Any]:
    """方向性变化重新审视相关核心方向,其余有效决定继续保留。"""

    reviewed: list[dict[str, Any]] = []
    kept: list[dict[str, Any]] = []
    missing: list[dict[str, Any]] = []
    for raw in material.get("core_directions") or []:
        item = dict(raw)
        if item.get("related"):
            if not str(item.get("review") or "").strip():
                missing.append({
                    "kind": "核心方向未审视",
                    "detail": f"{item.get('title')}与本轮变更相关但未给出审视结论",
                    "method": "重新审视该方向在本轮变更后的结论",
                    "impact": "方向性变化不能只改局部而漏掉相关核心方向"})
            reviewed.append({"id": item.get("id"), "title": item.get("title"),
                             "review": str(item.get("review") or "")})
        else:
            kept.append({"id": item.get("id"), "title": item.get("title"),
                         "note": "与本轮变更无实际关联,决定继续有效"})
    return {"reviewed": reviewed, "kept": kept, "missing": missing,
            "applies": depth == "directional",
            "affected_modules": sorted(impact["by_module"])}


def _verification(material: dict[str, Any], depth: str) -> list[dict[str, str]]:
    items: list[dict[str, str]] = []
    for raw in material.get("verification") or []:
        item = dict(raw)
        if depth == "local_tweak" and not item.get("required"):
            continue
        items.append({"question": str(item.get("question") or ""),
                      "method": str(item.get("method") or ""),
                      "blocks_stage": bool(item.get("blocks_stage"))})
    return items


def _depth_note(depth: str) -> str:
    return {
        "local_tweak": "局部明确微调:在授权内直接处理差异与必要核对,不重开设计地图。",
        "module": "模块调整:用当前模块的问题组处理一组关键取舍。",
        "structural": "结构性修改:检查受影响的多个模块,并按需提出验证。",
        "directional": "方向性变化:重新审视相关核心方向,保留其余有效决定。",
    }.get(depth, "按当前模块问题组处理。")

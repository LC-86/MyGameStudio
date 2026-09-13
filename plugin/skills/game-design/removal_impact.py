#!/usr/bin/env python3
"""功能删减的原作用盘点与残留依赖检查(统一设计问答框架票 07)。

公开 interface:
  LANES / DATA_LABELS / DATA_KINDS
  inventory(material) -> dict
  prepare_items(items, roles) -> list[dict]
  residual(items, impact) -> dict
  lanes(roles, residual, question_map) -> list[dict]

删减时先查清原功能实际承担的作用:奖励来源与成长节奏、行动引导、解锁条件、
入口、教程、内容、数据、验收八个方面逐项列出作用与关联的现行设计元素;已明确
的处理方式按一起取消 / 转移给已有系统 / 更简单方式保留三类记录,未明确且影响
体验的才成为问题——不强制每个被删功能都有替代品,也不接受以实质相同的功能
换个名字恢复原有负担。残留依赖沿票 06 的同一依赖追踪核对,分为一起取消、
需要重新配置与不受影响,间接引用写明经由路径。数据与权益按真实项目阶段检查
已有存档、玩家进度、待领资源与权益:不存在的对象不机械讨论,未知的先核实,
处理方案与实际迁移、清理或退款行为保持授权分离。取消范围区分正式取消、
当前版本不做与已明确承诺的后续范围,删除不自动转成未来任务。

本 module 只盘点、追踪与分类,不渲染交付内容、不写入文件(在 ``removal``)。
"""

from __future__ import annotations

from typing import Any

from change_input import DISPOSITION_LABELS

LANES = (
    ("reward", "奖励来源与成长节奏"), ("guidance", "行动引导"),
    ("unlock", "解锁条件"), ("entry", "入口"), ("tutorial", "教程"),
    ("content", "内容"), ("data", "数据"), ("acceptance", "验收"),
)

DATA_LABELS = {"existing_data": "存档与已有数据",
               "player_progress": "玩家进度",
               "pending_resources": "待领资源",
               "entitlements": "已有权益"}

DATA_KINDS = {
    "design_only": (),
    "developed_unreleased": ("existing_data",),
    "released": ("existing_data", "player_progress", "pending_resources",
                 "entitlements"),
}

DATA_LANE = {"existing_data": "data", "player_progress": "data",
             "pending_resources": "growth", "entitlements": "growth"}

RESIDUAL_LABELS = {"cancel": "一起取消", "reconfigure": "需要重新配置",
                   "unaffected": "不受影响", "pending": "待明确"}

PENDING_ACTION_NOTE = ("处理方案已记录;实际迁移、清理或退款行为需另行授权,"
                       "本轮不执行。")


def inventory(material: dict[str, Any]) -> dict[str, Any]:
    """原作用盘点:八个方面逐项列作用与关联,并报出未处理的作用。"""

    block = dict(material.get("removal") or {})
    target = _target_label(block)
    roles = [_role(dict(raw), target) for raw in block.get("roles") or []]
    covered = {role["lane"] for role in roles}
    unresolved: list[dict[str, Any]] = []
    for key, label in LANES:
        if key in covered:
            continue
        unresolved.append({
            "kind": "作用盘点缺项",
            "detail": f"「{label}」方面缺少作用盘点,"
                      f"不能确认该方面没有被删功能承担的作用",
            "method": "补查该方面的原作用与关联元素,再判断处理方式",
            "impact": "缺项时不能宣布删减处理完成"})
    unresolved.extend(_equivalent_gaps(roles, target))
    unresolved.extend(_scope_gaps(roles))
    data = _data(material, block, roles)
    unresolved.extend(data["unresolved"])
    return {"target": target, "roles": roles, "data": data,
            "unresolved": unresolved}


def prepare_items(items: list[dict[str, Any]],
                  roles: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """把作用处理落到设计元素上;未明确处理方式时先成为取舍问题。"""

    by_item = role_by_item(roles)
    prepared: list[dict[str, Any]] = []
    for raw in items:
        item = dict(raw)
        role = by_item.get(str(item.get("id")))
        if role is not None:
            _apply_role(item, role)
        prepared.append(item)
    return prepared


def role_by_item(roles: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    """元素 → 承担该元素的作用(一项作用可关联多个元素,先到先得)。"""

    by_item: dict[str, dict[str, Any]] = {}
    for role in roles:
        for item_id in role["items"]:
            by_item.setdefault(item_id, role)
    return by_item


def residual(items: list[dict[str, Any]],
             impact: dict[str, Any]) -> dict[str, Any]:
    """残留依赖:按实际依赖分一起取消、需要重新配置与不受影响。"""

    reached = {item["id"]: item for item in
               impact["must_sync"] + impact["needs_tradeoff"]}
    buckets: dict[str, list[str]] = {"cancel": [], "reconfigure": [],
                                     "pending": []}
    unaffected: list[dict[str, Any]] = []
    for item in items:
        item_id = str(item.get("id"))
        if item_id not in reached:
            unaffected.append({
                "id": item_id, "title": str(item.get("title") or ""),
                "reason": str(item.get("unaffected_reason")
                              or "与删减对象没有实际依赖关系,不在影响范围")})
            continue
        action = str(item.get("removal_action") or "")
        key = action if action in buckets else "pending"
        buckets[key].append(item_id)
    return {
        **buckets, "unaffected": unaffected,
        "trace": {item_id: {"depth": item["depth"], "path": item["path"],
                            "relation": item["relation"]}
                  for item_id, item in reached.items()},
    }


def lanes(roles: list[dict[str, Any]], residual_map: dict[str, Any],
          question_map: dict[str, str]) -> list[dict[str, Any]]:
    """八个方面各自给出结论:残留依赖处理与作用处理三类之一。"""

    classes = {item_id: "cancel" for item_id in residual_map["cancel"]}
    classes.update({item_id: "reconfigure"
                    for item_id in residual_map["reconfigure"]})
    classes.update({item_id: "pending" for item_id in residual_map["pending"]})
    by_lane = {role["lane"]: role for role in roles}
    summary: list[dict[str, Any]] = []
    for key, label in LANES:
        role = by_lane.get(key)
        summary.append({
            "key": key, "lane_label": label,
            "role": role["id"] if role else "",
            "conclusion": _lane_conclusion(role, classes, question_map)})
    return summary


def _lane_conclusion(role: dict[str, Any] | None,
                     classes: dict[str, str],
                     question_map: dict[str, str]) -> str:
    """结论=残留依赖处理 + 该方面作用处理;缺项如实写明。"""

    if role is None:
        return "缺项：该方面未盘点,需补查后再判断处理方式"
    listed = [(item_id, classes[item_id]) for item_id in role["items"]
              if item_id in classes]
    parts = [f"{RESIDUAL_LABELS[key]}："
             f"{'、'.join(item_id for item_id, kind in listed if kind == key)}"
             for key in ("cancel", "reconfigure", "pending")
             if any(kind == key for _, kind in listed)]
    if not parts:
        parts.append("不受影响：该方面没有与删减对象联动的现行元素")
    parts.append(f"作用处理（{role['title']}）："
                 f"{_role_handling(role, question_map)}")
    return "；".join(parts)


def _role_handling(role: dict[str, Any],
                   question_map: dict[str, str]) -> str:
    if not role["label"]:
        qid = question_map.get(role["id"], "")
        return f"待开发者取舍（{qid}）" if qid else "待开发者取舍"
    successor = f"→{role['successor']}" if role["successor"] else ""
    return f"{role['label']}{successor}"


def _apply_role(item: dict[str, Any], role: dict[str, Any]) -> None:
    """作用处理透传:已明确时记处理方式,未明确且影响体验时先提问。"""

    item["removal_role"] = role["id"]
    item["removal_lane"] = role["lane"]
    if role["label"]:
        item["disposition"] = role["disposition"]
        item["disposition_detail"] = role["detail_text"]
        return
    if not role["options"]:
        return
    item.pop("new_text", None)
    item.pop("resolution", None)
    item["options"] = dict(role["options"])
    item["recommendation"] = role["recommendation"]
    item["reason"] = role["reason"]
    item["impact"] = role["impact"]


def _role(raw: dict[str, Any], target: str) -> dict[str, Any]:
    """单项原作用:作用、关联、处理方式与取消范围。"""

    disposition = str(raw.get("disposition") or "")
    role = {
        "id": str(raw.get("id") or ""),
        "lane": str(raw.get("lane") or ""),
        "lane_label": dict(LANES).get(str(raw.get("lane") or ""),
                                     str(raw.get("lane") or "")),
        "title": str(raw.get("title") or ""),
        "detail": str(raw.get("detail") or ""),
        "items": [str(item) for item in raw.get("items") or []],
        "disposition": disposition,
        "label": DISPOSITION_LABELS.get(disposition, ""),
        "successor": str(raw.get("successor") or ""),
        "successor_detail": str(raw.get("successor_detail") or ""),
        "options": dict(raw.get("options") or {}),
        "recommendation": str(raw.get("recommendation") or ""),
        "reason": str(raw.get("reason") or ""),
        "impact": str(raw.get("impact") or ""),
        "equivalent_replacement": bool(raw.get("equivalent_replacement")),
        "scope_basis": str(raw.get("scope_basis") or ""),
        "promise": str(raw.get("promise") or ""),
    }
    role["scope"] = str(raw.get("scope") or "") if disposition else ""
    role["scope_label"] = _scope_label(role, target)
    role["detail_text"] = _disposition_detail(raw, role)
    return role


def _scope_label(role: dict[str, Any], target: str) -> str:
    """取消范围:正式取消 / 当前版本不做 / 已明确承诺的后续范围。"""

    if not role["disposition"]:
        return f"待开发者取舍:{target}的原作用如何取消、转移或简化保留"
    scope = role["scope"]
    if scope == "promised":
        return (f"已明确承诺的后续范围：{role['promise'] or ''}"
                f"（来源：{role['scope_basis'] or ''}）")
    if scope == "not_now":
        return (f"当前版本不做：{role['scope_basis'] or ''}；"
                f"尚未承诺后续版本,不误报为永久取消。")
    return "正式取消：未提出后续承诺,不自动生成未来任务。"


def _disposition_detail(raw: dict[str, Any], role: dict[str, Any]) -> str:
    text = str(raw.get("disposition_detail") or "")
    if text:
        return text
    if role["disposition"] == "transfer":
        return f"作用转移给已有系统 {role['successor']}；{role['successor_detail']}"
    if role["disposition"] == "simplify":
        return f"以更简单方式保留：{role['successor']}；{role['successor_detail']}"
    return "作用随功能一起取消"


def _equivalent_gaps(roles: list[dict[str, Any]],
                     target: str) -> list[dict[str, Any]]:
    """以实质相同的功能恢复原负担:不得当作处理完成。"""

    gaps: list[dict[str, Any]] = []
    for role in roles:
        successor = role["successor"]
        same = role["equivalent_replacement"] or (
            bool(target) and bool(successor) and target in successor)
        if not same:
            continue
        gaps.append({
            "kind": "原作用以实质相同的功能替代",
            "detail": f"{target}的原作用被「{successor}」以实质相同的方式恢复,"
                      f"只是换个名字重新增加相同负担,不构成处理完成",
            "method": "改选真正取消、转移或更简单的处理方式,或说明差异依据",
            "impact": "否则删减目标没有达成"})
    return gaps


def _scope_gaps(roles: list[dict[str, Any]]) -> list[dict[str, Any]]:
    gaps: list[dict[str, Any]] = []
    for role in roles:
        if role["scope"] != "promised" or role["scope_basis"]:
            continue
        gaps.append({
            "kind": "后续承诺缺少来源",
            "detail": f"{role['title']}被记为已明确承诺的后续范围,"
                      f"但缺少承诺原文与来源",
            "method": "补开发者原话与来源,或改记为当前版本不做",
            "impact": "未承诺的内容不能写成后续任务"})
    return gaps


def _target_label(block: dict[str, Any]) -> str:
    labels = [str(item) for item in block.get("target_labels") or []]
    return labels[0] if labels else "被删功能"


def _data(material: dict[str, Any], block: dict[str, Any],
          roles: list[dict[str, Any]]) -> dict[str, Any]:
    """按真实阶段核对存档、进度、待领资源与权益;未知先核实。"""

    stage = str(material.get("stage") or "")
    kinds = DATA_KINDS.get(stage)
    if kinds is None:
        kinds = tuple(DATA_LABELS)
    raw_map = dict(block.get("data_handling") or {})
    entries: list[dict[str, Any]] = []
    unresolved: list[dict[str, Any]] = []
    for key in kinds:
        entry, gap = _data_entry(key, raw_map.get(key), roles)
        entries.append(entry)
        if gap:
            unresolved.append(gap)
    actions = [{"action": str(item), "note": PENDING_ACTION_NOTE}
               for item in _actions(block, raw_map)]
    return {"stage": stage, "entries": entries, "pending_actions": actions,
            "unresolved": unresolved}


def _actions(block: dict[str, Any],
             raw_map: dict[str, Any]) -> list[str]:
    """实际迁移、清理或退款动作单列为待授权,不随设计同步自动执行。"""

    declared = [str(item) for item in block.get("actions") or []]
    if declared:
        return declared
    for raw in raw_map.values():
        nested = [str(item) for item in (raw or {}).get("actions") or []]
        if nested:
            return nested
    return []


def _data_entry(key: str, raw: dict[str, Any] | None,
                roles: list[dict[str, Any]]) -> tuple[dict[str, Any],
                                                      dict | None]:
    """三档:存在给方案、不存在不处理、未核实先核实。"""

    label = DATA_LABELS[key]
    item_ids = _item_ids(key, raw, roles)
    raw = dict(raw or {})
    base = {"key": key, "label": label, "item_ids": item_ids}
    if raw.get("exists") is False:
        return ({**base, "state": "absent",
                 "detail": f"{label}核实为不存在,不生成处理动作"}, None)
    if not raw:
        return ({**base, "state": "unverified",
                 "detail": f"{label}存在性未核实,先核实再决定处理方式"},
                {"kind": "数据与权益对象未核实",
                 "detail": f"{label}存在性未核实,不能当作不存在,"
                           f"也不生成不存在的补偿问题",
                 "method": "先核实存在性与规模(查工作区资料或询问开发者),"
                           "再决定保留、迁移或清理",
                 "impact": "存在时需要处理,缺失时不得写成「无此对象」"})
    plan = str(raw.get("plan") or "").strip()
    if not plan:
        return ({**base, "state": "exists",
                 "detail": f"{label}已核实存在但未给出处理方案"},
                {"kind": "数据与权益处理方案缺失",
                 "detail": f"{label}已核实存在,但没有保留、迁移或清理方案",
                 "method": "先明确保留读取、迁移或清理的处理方案",
                 "impact": "缺方案容易漏掉已有进度或权益"})
    return {**base, "state": "exists", "detail": plan}, None


def _item_ids(key: str, raw: dict[str, Any] | None,
              roles: list[dict[str, Any]]) -> list[str]:
    declared = [str(item) for item in (raw or {}).get("items") or []]
    if declared:
        return declared
    lane = DATA_LANE.get(key, "")
    ids: list[str] = []
    for role in roles:
        if role["lane"] != lane:
            continue
        for item_id in role["items"]:
            if item_id not in ids:
                ids.append(item_id)
    return ids


__all__ = ["LANES", "DATA_KINDS", "DATA_LABELS", "inventory",
           "prepare_items", "residual", "lanes"]

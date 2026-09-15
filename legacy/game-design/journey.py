#!/usr/bin/env python3
"""Game-Design 玩家视角流程核对与跨模块矛盾检出(统一设计问答框架票 05)。

公开 interface:
  walkthrough(material) -> dict
  find_contradictions(material) -> list[dict]

模块规格齐备后,按玩家视角推演首次进入、理解目标、操作、选择、结果、结束
与再次进入,并检查适用的资源耗尽、重复操作、退出、解锁与失败恢复;不适用
的检查写明理由。资源流动、解锁与内容/规则的直接矛盾在此检出,发现后先处理
真实影响再谈交接,不能只因为文档目录齐全就宣称完成。

本 module 只核对与判定,不改写规则、不写入文件。
"""

from __future__ import annotations

from typing import Any

STEP_ORDER = (
    ("first_entry", "首次进入"),
    ("understand_goal", "理解目标"),
    ("operate", "操作"),
    ("choose", "选择"),
    ("result", "结果"),
    ("end", "结束"),
    ("reenter", "再次进入"),
)

CHECK_ORDER = (
    ("resource_exhaustion", "资源耗尽"),
    ("repeat", "重复操作"),
    ("exit", "退出"),
    ("unlock", "解锁"),
    ("failure_recovery", "失败恢复"),
)

CONTRADICTION_KIND = "资源或解锁矛盾"


def walkthrough(material: dict[str, Any]) -> dict[str, Any]:
    """按玩家视角推演完整经历,并汇总适用的边界检查与矛盾。"""

    return {
        "op": "journey",
        "steps": _steps(material),
        "checks": _checks(material),
        "contradictions": find_contradictions(material),
    }


def find_contradictions(material: dict[str, Any]) -> list[dict[str, Any]]:
    """检查资源收支与解锁要求、重复解锁要求的直接矛盾,指明真实影响。"""

    items: list[dict[str, Any]] = []
    economy = dict(material.get("economy") or {})
    resources = {str(item.get("name") or ""): dict(item)
                 for item in economy.get("resources") or []}
    seen: dict[tuple[str, str], float] = {}
    for raw in economy.get("unlock_requirements") or []:
        requirement = dict(raw)
        name = str(requirement.get("resource") or "")
        target = str(requirement.get("target") or "")
        amount = requirement.get("amount")
        resource = resources.get(name) or {}
        unit = str(resource.get("unit") or "")
        total = resource.get("earn_total")
        if _number(total) is not None and _number(amount) is not None \
                and float(amount) > float(total):
            items.append(_conflict({
                "detail": (f"{target}解锁需{name} {_fmt(amount)} {unit},"
                           f"而{name}可获得总量只有 {_fmt(total)} {unit};"
                           f"两者数量矛盾,须澄清或调整"),
                "location": str(requirement.get("location") or ""),
                "target": target}))
        key = (name, target)
        previous = seen.get(key)
        if previous is not None and previous != _number(amount):
            items.append(_conflict({
                "detail": (f"{target}解锁所需的{name}数量前后不一致"
                           f"（{_fmt(previous)} 与 {_fmt(amount)} {unit}）"),
                "location": str(requirement.get("location") or ""),
                "target": target}))
        if key not in seen:
            seen[key] = _number(amount)
    return items


def _conflict(detail: dict[str, Any]) -> dict[str, Any]:
    target = detail["target"] or "该项解锁"
    return {"kind": CONTRADICTION_KIND, "detail": detail["detail"],
            "impact": (f"{target}的解锁数值与资源收支对不上;"
                       f"影响成长与资源流动、解锁和版本验收,先处理真实影响"),
            "affects": ["成长与资源流动", "版本范围与验收",
                        detail["location"]]}


def _steps(material: dict[str, Any]) -> list[dict[str, Any]]:
    journey = dict(material.get("journey") or {})
    steps: list[dict[str, Any]] = []
    for key, label in STEP_ORDER:
        raw = dict(journey.get(key) or {})
        status = str(raw.get("status") or "open")
        steps.append({"id": key, "label": label, "status": status,
                      "detail": str(raw.get("detail") or "")})
    return steps


def _checks(material: dict[str, Any]) -> dict[str, dict[str, Any]]:
    checks = dict(material.get("checks") or {})
    result: dict[str, dict[str, Any]] = {}
    for key, _label in CHECK_ORDER:
        raw = dict(checks.get(key) or {})
        applies = raw.get("applies")
        if applies is False:
            reason = str(raw.get("reason") or "").strip()
            result[key] = {"status": "n/a" if reason else "unexplained",
                           "reason": reason,
                           "detail": str(raw.get("detail") or "")}
        else:
            result[key] = {"status": "checked", "reason": "",
                           "detail": str(raw.get("detail") or "")}
    return result


def _number(value: Any) -> float | None:
    if isinstance(value, bool) or value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _fmt(value: Any) -> str:
    number = _number(value)
    if number is None:
        return str(value)
    return str(int(number)) if number == int(number) else str(number)

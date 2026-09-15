#!/usr/bin/env python3
"""Game-Design 检查证据与报告(统一设计问答框架票 08)。

公开 interface:
  evidence(session) -> dict
  ledger(session, **filters) -> list[dict]
  summary(session) -> str
  report(session, result) -> str
  measure(session, *, module) -> dict

按实际事件给出检查依据:读取、写入、检查与调用分别计数,**一条工具调用内部的
多次文件操作仍分别计数**,不通过合并调用制造步骤减少;检查台账如实保留时机、
范围、结果与跳过项(未改核心基线时跳过的全局重查按 skipped 记录)。日常回复
用 ``report`` 只保留保存结果、必要限制与检查数的简短摘要,检查明细经
``summary``/``ledger`` 在已有记录中简短保留,``measure`` 给出固定场景复用
第 01 票口径的步骤依据。

本 module 只读会话,不修改状态、不写入项目文件、不接触受控通道。
"""

from __future__ import annotations

from typing import Any

from check_state import count_of, public

__all__ = ["evidence", "ledger", "measure", "report", "summary"]


def evidence(session: dict[str, Any]) -> dict[str, Any]:
    """实际事件计数:读取、写入、检查与调用;调用内多文件分别计数。"""

    events = list(session.get("evidence") or [])
    calls: list[str] = []
    for event in events:
        call = str(event.get("call") or "")
        if call and call not in calls:
            calls.append(call)
    return {"events": events, "reads": count_of(events, "reads"),
            "writes": count_of(events, "writes"), "calls": len(calls),
            "call_names": calls,
            "checks": len(session.get("ledger") or [])}


def ledger(session: dict[str, Any], **filters: Any) -> list[dict[str, Any]]:
    """按条件筛选检查台账(timing/scope/status/check 子串等)。"""

    items = [dict(item) for item in (session.get("ledger") or [])]
    for key, value in filters.items():
        items = [item for item in items if value in item.get(key, "")]
    return items


def summary(session: dict[str, Any]) -> str:
    """检查明细的简短记录:实际范围与结果,不逐项重述。"""

    entries = ledger(session)
    reads = count_of(session.get("evidence") or [], "reads")
    lines = [f"检查记录:{len(entries)} 项(读取 {reads['file_ops']} 次)"]
    lines.extend(f"- [{item.get('timing')}] {item.get('status')} "
                 f"{item.get('check')}" for item in entries)
    return "\n".join(lines)


def report(session: dict[str, Any], result: dict[str, Any]) -> str:
    """日常回复只保留保存结果、必要限制与检查明细的简短记录。"""

    entries = ledger(session)
    result = result or {}
    if "saved" in result:
        state = "已保存" if result.get("saved") else "未保存"
    else:
        state = str(result.get("status") or "未见状态")
    gaps = [item for item in entries if item.get("status") in {"gap", "stale"}]
    reused = [item for item in entries if item.get("reused")]
    return (f"本轮{state};检查 {len(entries)} 项"
            f"(重新检查 {len(gaps)},复用读取 {len(reused)} 项)")


def measure(session: dict[str, Any], *, module: str) -> dict[str, Any]:
    """固定场景的步骤依据:实际读取、写入、检查与调用计数。"""

    counts = evidence(session)
    return {"module": str(module), "reads": counts["reads"],
            "writes": counts["writes"], "checks": counts["checks"],
            "calls": counts["calls"],
            "rounds": len(session.get("round_checks") or []),
            "converged": bool(session.get("converged")),
            "scope": public(session.get("scope"))}

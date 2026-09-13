#!/usr/bin/env python3
"""Game-Design 功能删减接缝(统一设计问答框架票 07)。

公开 interface:
  plan_removal(existing, meta, material) -> dict
  apply_removal(plan, channel, readback) -> dict
  verify_removal(plan, readback_map) -> dict

在票 06 已有设计变更流程上完整处理删减:先沿用四项变更说明(修改对象、原因、
预期改善、需要保留的内容)与依赖追踪,再由 ``removal_impact`` 盘点原功能承担
的作用——奖励来源与成长节奏、行动引导、解锁条件、入口、教程、内容、数据、
验收,以及它们关联的现行设计元素。开发者已明确删除方向时不反复询问是否删除;
已明确的作用处理按一起取消 / 转移给已有系统 / 更简单方式保留记录,未明确且
影响体验的才成为新增取舍问题,不强制每个被删功能都有替代品。残留依赖按实际
依赖分为一起取消、需要重新配置与不受影响,间接引用写明经由路径;数据与权益
按真实项目阶段核对,不存在的对象不机械讨论,未知先核实,处理方案与实际迁移、
清理或退款行为保持授权分离;取消范围区分正式取消、当前版本不做与已明确承诺
的后续范围,删除不自动转成未来任务。获准同步时失效规则、旧入口、旧引用与旧
验收退出当前有效版本,历史、替代关系与未受影响内容保留。

写入与票 03～06 同一条受控通道(``gate_commit.commit_path``):逐文件核对当前
授权与目标版本并回读,没有回读成功不得称为已保存或已同步;仅授权文档处理时
不删除代码、资源或用户数据。

分工:作用盘点、残留依赖与数据权益在 ``removal_impact.py``,计划编排复用
``change_flow.plan_change``/``apply_change``/``verify_change``(影响、阶段与
渲染),本 module 只做删减材料准备、结果装饰与删减专项回读核对。
"""

from __future__ import annotations

from typing import Any, Callable

from change_flow import apply_change, plan_change, verify_change
from change_render import HISTORY_TITLE, render_change_record
from change_report import incomplete_report
from removal_impact import (
    inventory, lanes, prepare_items, residual, role_by_item,
)


def plan_removal(existing: dict[str, str | None], meta: dict[str, Any],
                 material: dict[str, Any]) -> dict[str, Any]:
    """盘点原作用与残留依赖,整理删减后设计与同步计划;不写入。"""

    block = dict(material.get("removal") or {})
    analysis = inventory(material)
    items = prepare_items(list(material.get("design_items") or []),
                          analysis["roles"])
    prepared = _prepared_material(material, items, block)
    plan = plan_change(existing, meta, prepared)
    return _decorate(plan, analysis, items)


def apply_removal(plan: dict[str, Any], channel: Any,
                  readback: Callable[[str], str | None]) -> dict[str, Any]:
    """经同一受控通道提交受影响文件;变更记录最后写并回读核对。"""

    result = apply_change(plan, channel, readback)
    result["op"] = "removal"
    if plan.get("removal"):
        result["removal"] = plan["removal"]
    return result


def verify_removal(plan: dict[str, Any],
                   readback_map: dict[str, str | None]) -> dict[str, Any]:
    """回读核对:失效规则与旧入口退出正文,作用处理与取消范围在记录中就位。"""

    verdict = verify_change(plan, readback_map)
    failures = list(verdict["failures"])
    failures.extend(_retired_failures(plan, readback_map))
    failures.extend(_removal_record_failures(plan, readback_map))
    if plan.get("removal") and plan.get("unresolved"):
        failures.append("仍有未说明的作用处理或残留依赖断点,不得判为删减完成")
    return {"ok": not failures, "failures": failures,
            "design_path": verdict["design_path"]}


def _prepared_material(material: dict[str, Any], items: list[dict[str, Any]],
                       block: dict[str, Any]) -> dict[str, Any]:
    """沿用票 06 材料口径:删减块补齐四项变更说明与设计元素。"""

    prepared = dict(material)
    prepared["design_items"] = items
    raw = dict(material.get("change") or {})
    prepared["change"] = {
        "targets": list(raw.get("targets") or block.get("targets") or []),
        "target_labels": list(raw.get("target_labels")
                              or block.get("target_labels") or []),
        "reason": str(raw.get("reason") or block.get("reason") or ""),
        "improvement": str(raw.get("improvement")
                           or block.get("improvement") or ""),
        "keep": list(raw.get("keep") or block.get("keep") or []),
        "answers": list(raw.get("answers") or block.get("answers") or []),
    }
    return prepared


def _decorate(plan: dict[str, Any], analysis: dict[str, Any],
              items: list[dict[str, Any]]) -> dict[str, Any]:
    """补删减专项结果:问题来源、作用处理、残留依赖、数据权益与取消范围。"""

    plan["op"] = "removal"
    questions = _questions_with_roles(plan.get("questions") or [],
                                      analysis["roles"])
    question_map = {str(item.get("source_role") or ""): item["id"]
                    for item in questions if item.get("source_role")}
    residual_map = residual(items, plan["impact"])
    removal = {"target": analysis["target"], "roles": analysis["roles"],
               "lanes": lanes(analysis["roles"], residual_map, question_map),
               "residual": residual_map, "trace": residual_map["trace"],
               "data": analysis["data"]}
    plan["questions"] = questions
    plan["impact"]["questions"] = questions
    plan["record"]["questions"] = questions
    plan["record"]["removal"] = removal
    plan["removal"] = removal
    plan["unresolved"] = analysis["unresolved"] + list(plan["unresolved"])
    plan["note"] = _note(plan)
    if not analysis["unresolved"]:
        return _refresh_record(plan)
    plan["status"] = "incomplete"
    plan["saved"] = False
    plan["content"] = None
    plan["handoff_ready"] = False
    plan["report"] = incomplete_report(plan)
    return plan


def _questions_with_roles(questions: list[dict[str, Any]],
                          roles: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """问题标出来源作用:只有尚未明确且影响体验的处理方式才会提问。"""

    by_item = role_by_item(roles)
    marked: list[dict[str, Any]] = []
    for raw in questions:
        item = dict(raw)
        role = by_item.get(str(item.get("source_item") or ""))
        if role is not None:
            item["source_role"] = role["id"]
        marked.append(item)
    return marked


def _note(plan: dict[str, Any]) -> str:
    version = dict(plan.get("version") or {})
    files = len(plan.get("files") or [])
    if version.get("to") and version["to"] != version.get("from"):
        return (f"同步 {plan.get('module')} 删减（{files} 个文件）："
                f"需求实质变化 {version.get('from')} → {version['to']}，"
                f"更新版本与双指纹。")
    return (f"同步 {plan.get('module')} 删减（{files} 个文件）："
            f"版本保持 {version.get('from') or '未标注'}。")


def _refresh_record(plan: dict[str, Any]) -> dict:
    """把作用处理写进变更记录内容;只在有可写入内容时重渲染。"""

    if plan.get("content") is None:
        return plan
    record_path = str(plan.get("change_record_path") or "")
    text = render_change_record(dict(plan.get("meta") or {}),
                                plan["record"], plan["states"], planned=True)
    plan["content"][record_path] = text
    for item in plan.get("files") or []:
        if str(item.get("path") or "") == record_path:
            item["content"] = text
    return plan


def _retired_failures(plan: dict[str, Any],
                      readback_map: dict[str, str | None]) -> list[str]:
    """失效规则必须退出正文(历史段保留替代关系)。"""

    failures: list[str] = []
    for item in plan.get("specs") or []:
        text = readback_map.get(str(item.get("path") or ""))
        if text is None:
            continue
        body = text.split(HISTORY_TITLE)[0]
        for entry in item.get("retired") or []:
            if entry["old"] in body:
                failures.append(f"失效规则仍在现行版本正文:{entry['id']}")
    return failures


def _removal_record_failures(plan: dict[str, Any],
                             readback_map: dict[str, str | None]) -> list[str]:
    """变更记录要能看清原作用如何取消、转移或简化保留,以及取消范围。"""

    removal = plan.get("removal")
    if not removal:
        return []
    record = readback_map.get(str(plan.get("change_record_path") or ""))
    if record is None:
        return ["回读目标不存在:变更记录"]
    failures: list[str] = []
    for role in removal["roles"]:
        if role["label"] and f"{role['title']}：{role['label']}" not in record:
            failures.append(f"变更记录缺少作用处理:{role['title']}")
        if role["scope_label"] and role["scope_label"] not in record:
            failures.append(f"变更记录缺少取消范围:{role['title']}")
    for lane in removal["lanes"]:
        if lane["lane_label"] not in record:
            failures.append(f"变更记录缺少作用盘点方面:{lane['lane_label']}")
    if "残留依赖检查" not in record:
        failures.append("变更记录缺少残留依赖检查")
    for entry in removal["data"]["entries"]:
        if entry["label"] not in record:
            failures.append(f"变更记录缺少数据与权益处理:{entry['label']}")
    return failures


__all__ = ["plan_removal", "apply_removal", "verify_removal"]

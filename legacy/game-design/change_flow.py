#!/usr/bin/env python3
"""Game-Design 已有设计变更接缝(统一设计问答框架票 06)。

公开 interface:
  plan_change(existing, meta, material) -> dict
  apply_change(plan, channel, readback) -> dict
  verify_change(plan, readback_map) -> dict
  answer_turn(plan, user_reply, settled=None) -> dict

从当前有效设计出发处理补充、优化与调整:先提取四项变更说明(修改对象、
原因、预期改善、需要保留的内容),分清开发者只提出问题还是已作出修改决定
——已决定的修改直接进入处理讨论,不重复询问是否采纳;确有重大新影响时只
处理新增取舍。沿玩法规则、成长资源、界面引导、内容资产、数据及验收的实际
依赖追踪直接与间接影响,分成「必须同步」「需要开发者取舍」「不受影响」;
按项目阶段核对需要检查的对象,未知不得当作不存在,也不追问并不存在的补偿
或迁移。候选说明改什么、保留什么、预期改善与代价,事实调查、计算与关联
分析由本接缝承担;用适用场景推演变化,数值/流程自洽与实际体验改善分开,
需要试玩时保留具体方法与阻断影响。获准同步时只更新真正受影响的当前设计,
失效规则与引用退出现行版本而历史保留,并留下简短变更记录。

写入与票 03 ``apply_save``、票 04 ``apply_handoff``、票 05 ``apply_delivery``
同一条受控通道(``gate_commit.commit_path``):逐文件核对当前授权与目标版本
并回读,没有回读成功不得称为已保存或已同步。

分工:影响分析与阶段适配在 ``change_impact.py``,材料整理在
``change_input.py``,交付渲染在 ``change_render.py``,报告措辞在
``change_report.py``;本 module 负责编排、文件计划、受控提交与回读核对。
"""

from __future__ import annotations

import re
from typing import Any, Callable

import change_input as material_input
import checks as checks_seam
from change_impact import analyze, organize, stage_check
from change_render import render_baseline, render_change_record, update_spec
from change_report import (
    blocked_report, check_failed_report, failure_report, incomplete_report,
    plan_report, questions_report, read_only_report, saved_report,
)
from decision_records import sha256_text
from gate_commit import commit_path

STATUSES_WITHOUT_WRITE = {"incomplete", "read_only", "unauthorized",
                          "questions"}


def plan_change(existing: dict[str, str | None], meta: dict[str, Any],
                material: dict[str, Any]) -> dict[str, Any]:
    """整理变更说明、影响、阶段核对与同步计划;不写入。"""

    change = material_input.statements(material)
    impact = _impact(material)
    stage = stage_check(material)
    organization = organize(material, impact)
    questions = material_input.questions(impact["needs_tradeoff"],
                                         int(meta.get("question_start") or 1),
                                         str(meta.get("module") or ""))
    record = material_input.record(material, meta, change, impact, stage,
                                   organization, questions)
    authorization = dict(meta.get("authorization") or {})
    specs = _spec_plans(existing, meta, impact) if authorization.get("sync") \
        else []
    files = specs + _baseline_files(existing, meta, record, impact)
    unresolved = impact["unresolved"] + organization["directions"]["missing"] \
        + _unlocated(specs) + list(stage.get("missing") or [])
    base = _plan_base(meta, material, change, impact, stage, organization,
                      questions, unresolved, record, specs, files)
    if unresolved:
        return {**base, "status": "incomplete", "saved": False,
                "content": None, "handoff_ready": False,
                "report": incomplete_report(base)}
    if impact["needs_tradeoff"]:
        return {**base, "status": "questions", "saved": False,
                "content": None, "handoff_ready": False,
                "report": questions_report(base)}
    if not _locations_ready(meta, files):
        return {**base, "status": "unauthorized", "saved": False,
                "content": None, "handoff_ready": False,
                "report": "缺少当前设计或变更记录位置:不自行另建一套文档;"
                          "先按 CONFIG 文档映射确认落点。"}
    if not authorization.get("write"):
        return {**base, "status": "read_only", "saved": False,
                "content": None, "handoff_ready": False,
                "reason": "只读讨论:未获写入授权,变更内容保留待授权后同步",
                "report": read_only_report(base)}
    return {**base, "status": "planned", "saved": False,
            "content": _content(files),
            "handoff_ready": bool(authorization.get("sync")),
            "note": f"同步 {base['module']} 变更（{len(files)} 个文件）",
            "report": plan_report(base)}


def _plan_base(meta: dict[str, Any], material: dict[str, Any],
               change: dict[str, Any], impact: dict[str, Any],
               stage: dict[str, Any], organization: dict[str, Any],
               questions: list[dict[str, Any]], unresolved: list[dict],
               record: dict[str, Any], specs: list[dict[str, Any]],
               files: list[dict[str, Any]]) -> dict[str, Any]:
    """计划公共字段:变更说明、影响、阶段、文件计划与状态分档。"""

    return {
        "op": "change",
        "module": str(meta.get("module") or ""),
        "date": str(meta.get("date") or ""),
        "round": int(meta.get("round") or 0),
        "meta": dict(meta),
        "request_state": str(dict(material.get("request") or {}).get("state")
                             or "decided"),
        "change": change,
        "impact": {**impact, "questions": questions},
        "stage": stage,
        "organization": organization,
        "questions": questions,
        "unresolved": unresolved,
        "record": record,
        "results": list(record["results"]),
        "specs": [{"path": item["path"], "retired": item["retired"],
                   "expected_contains": item["expected_contains"]}
                  for item in specs],
        "files": files,
        "changed_paths": [str(item["path"]) for item in files],
        "modules": [dict(item) for item in (material.get("modules") or [])],
        "change_record_path": str(meta.get("change_record_path") or ""),
        "design_path": str(meta.get("design_path") or ""),
        "untouched": [str(path) for path in (meta.get("untouched") or [])],
        "to_sync": _pending_sync(meta, impact),
        "version": _version(meta),
        "states": {"adopted": True, "saved": False, "synced": False,
                   "implemented": False, "verified": False},
        "sync_authorized": bool(dict(meta.get("authorization") or {})
                                .get("sync")),
    }


def apply_change(plan: dict[str, Any], channel: Any,
                 readback: Callable[[str], str | None],
                 *, session: dict[str, Any] | None = None) -> dict[str, Any]:
    """经同一受控通道逐个提交受影响文件;每个文件提交后回读核对。

    传入 ``session``(票 08 ``checks.begin`` 建立的会话)时,按同一检查时机
    约定:落盘前做一次收敛统一核对,每个文件单独计数写入并逐次经通道核对
    授权与版本,落盘后回读核对新改引用;不传时保持原有行为不变。
    """

    status = plan.get("status")
    if status in STATUSES_WITHOUT_WRITE:
        return {**_result(plan, status, False), "written": [],
                "questions": plan.get("questions") or [],
                "to_sync": plan.get("to_sync") or [],
                "unresolved": plan.get("unresolved") or [],
                "handoff_ready": False, "session": session, "checks": None,
                "report": blocked_report(plan)}
    if status != "planned":
        return {**_result(plan, "invalid", False), "written": [],
                "handoff_ready": False, "session": session, "checks": None,
                "report": f"计划状态 {status} 不可执行"}
    session = checks_seam.converge_plan(session, plan)
    written: list[str] = []
    record_role = "变更记录"
    main_files = [item for item in (plan.get("files") or [])
                  if item.get("role") != record_role]
    record_files = [item for item in (plan.get("files") or [])
                    if item.get("role") == record_role]
    for item in main_files:
        failed, gate = _write_change_item(plan, item, channel, readback,
                                          written)
        if failed is not None:
            return {**failed, "session": checks_seam.invalidate_outcome(
                session, gate or {}), "checks": None}
        session = checks_seam.write_item(
            session, item, label="变更写入")
    probe = written[0] if written else str(plan.get("change_record_path") or "")
    session, checks = checks_seam.after_write(
        session, module=str(plan.get("module") or ""), path=probe,
        readback=readback,
        known_paths=[str(item.get("path") or "")
                     for item in plan.get("files") or []])
    force_pending = checks is not None and not checks.get("ok")
    for item in record_files:
        failed, gate = _write_change_item(
            plan, item, channel, readback, written,
            synced=False if force_pending else None)
        if failed is not None:
            return {**failed, "session": checks_seam.invalidate_outcome(
                session, gate or {}), "checks": None}
        session = checks_seam.write_item(
            session, item, label="变更写入")
    states = _states_after(plan, written)
    if force_pending:
        failed = {**states, "synced": False}
        return {**_result(plan, "check_failed", False), "written": written,
                "states": failed, "questions": plan.get("questions") or [],
                "to_sync": plan.get("to_sync") or [],
                "untouched": plan.get("untouched") or [],
                "handoff_ready": False,
                "channel_result": {"decision": "allow"},
                "session": session, "checks": checks,
                "report": check_failed_report(plan, written, checks),
                "next_round_ready": False}
    return {**_result(plan, "saved", True), "written": written,
            "states": states, "questions": plan.get("questions") or [],
            "to_sync": [] if states["synced"] else plan.get("to_sync") or [],
            "untouched": plan.get("untouched") or [],
            "handoff_ready": bool(states["synced"]),
            "channel_result": {"decision": "allow"},
            "session": session, "checks": checks,
            "report": saved_report(plan, written, states),
            "next_round_ready": True}


def _write_change_item(plan: dict[str, Any], item: dict[str, Any],
                       channel: Any, readback: Callable[[str], str | None],
                       written: list[str],
                       *, synced: bool | None = None
                       ) -> tuple[dict[str, Any] | None, dict[str, Any] | None]:
    """提交一个变更文件;失败时返回 (结果, 通道依据),成功时追加 written。"""

    content = _content_at_write(plan, item, written, synced=synced)
    outcome = commit_path(
        channel, readback, path=str(item.get("path") or ""),
        content=content,
        expected_sha256=str(item.get("expected_sha256") or "absent"),
        note=f"{plan.get('module')} 设计变更（{item.get('role')}）")
    if not outcome["ok"]:
        return _failure(plan, outcome, written), outcome
    written.append(str(item.get("path") or ""))
    return None, outcome


def _content_at_write(plan: dict[str, Any], item: dict[str, Any],
                      written: list[str], *, synced: bool | None = None) -> str:
    """变更记录最后写:状态段按此前实际写入结果渲染,不先落状态声明。"""

    if str(item.get("role") or "") != "变更记录":
        return str(item.get("content") or "")
    states = _states_after(plan, written + [str(item.get("path") or "")])
    if synced is False:
        states = {**states, "synced": False}
    return render_change_record(dict(plan.get("meta") or {}),
                                plan.get("record") or {}, states)


def verify_change(plan: dict[str, Any],
                  readback_map: dict[str, str | None]) -> dict[str, Any]:
    """回读核对:当前设计保留未受影响内容、新规则就位、旧规则与引用退出。"""

    failures: list[str] = []
    design_path = str(plan.get("design_path") or "")
    failures.extend(_design_failures(plan, readback_map.get(design_path),
                                     design_path))
    changed = set(plan.get("changed_paths") or [])
    for path in plan.get("untouched") or []:
        if path in changed:
            failures.append(f"未受影响内容被改动:{path}")
    failures.extend(_spec_failures(plan, readback_map))
    failures.extend(_record_failures(plan, readback_map))
    if plan.get("unresolved"):
        failures.append("存在未说明的关键断点,不得判为变更完成")
    return {"ok": not failures, "failures": failures,
            "design_path": design_path}


def _design_failures(plan: dict[str, Any], design: str | None,
                     design_path: str) -> list[str]:
    if design is None:
        return [f"回读目标不存在:{design_path}"]
    failures: list[str] = []
    version = plan.get("version") or {}
    if version.get("to") and version["to"] not in design:
        failures.append(f"当前设计未登记新版本:{version.get('to')}")
    if not re.search(r"内容指纹\s*[:：]\s*sha256:", design) \
            or not re.search(r"归一指纹\s*[:：]\s*sha256:", design):
        failures.append("当前设计缺内容指纹或归一指纹登记")
    change_path = str(plan.get("change_record_path") or "")
    if change_path and change_path not in design:
        failures.append("当前设计未登记变更记录位置")
    return failures


def _record_failures(plan: dict[str, Any],
                     readback_map: dict[str, str | None]) -> list[str]:
    """变更记录的必备内容与状态项,以及旧验证结果的版本标注。"""

    record = readback_map.get(str(plan.get("change_record_path") or ""))
    if record is None:
        return ["回读目标不存在:变更记录"]
    failures: list[str] = []
    for needle in ("## 目标与原因", "## 旧设计到新设计", "## 影响范围",
                   "## 阶段与对象检查", "## 场景推演", "## 待验证",
                   "## 旧验证结果", "## 状态"):
        if needle not in record:
            failures.append(f"变更记录缺少章节:{needle}")
    for label in ("已采纳", "已保存", "已同步核心基线", "已实现", "已验证"):
        if label not in record:
            failures.append(f"变更记录缺少状态项:{label}")
    for item in plan.get("results") or []:
        if not item["applies_version"]:
            continue
        if f"原适用版本 {item['applies_version']}" not in record:
            failures.append(f"旧验证结果未标明原适用版本:{item['id']}")
    for item in plan.get("record", {}).get("answers") or []:
        if item["qid"] and f"{item['qid']}=" not in record:
            failures.append(f"变更记录缺少取舍问题来源:{item['qid']}")
    return failures


def answer_turn(plan: dict[str, Any], user_reply: str,
                settled: dict[str, Any] | None = None) -> dict[str, Any]:
    """把新增取舍问题组成 ``rounds.run_round`` 可消费的一轮。

    沿用票 02/03 的同一问答与保存路径:回答经 ``rounds.run_round`` 对应到
    决定,再由 ``decisions.plan_save`` 落成决定记录——本接缝不另造记录体系。
    """

    questions = [dict(item, module=str(plan.get("module") or ""))
                 for item in plan.get("questions") or []]
    return {
        "request": str(plan.get("change", {}).get("request_text") or ""),
        "goal": f"确认{plan.get('module') or ''}变更的连带处理方式",
        "module": str(plan.get("module") or ""),
        "round": int(plan.get("round") or 1),
        "current_design": {"exists": True, "covers_request": True,
                           "wants_change": True},
        "questions": questions,
        "shown": [item["id"] for item in questions],
        "settled": dict(settled or {}),
        "user_reply": user_reply,
    }


def _impact(material: dict[str, Any]) -> dict[str, Any]:
    """影响分析:更新计划、候选对比与无依据的「未解决」判定。"""

    impact = analyze(material)
    impact["changes"] = [{"id": item["id"], "title": item["title"],
                          "relation": item["relation"],
                          "old": item["old_text"], "new": item["new_text"],
                          "location": item["location"]}
                         for item in impact["must_sync"]
                         if item.get("old_text") and item.get("new_text")]
    impact["candidates"] = material_input.candidates(material, impact)
    impact["unresolved"] = impact["unresolved"] + \
        material_input.unresolved_candidates(impact["candidates"])
    return impact


def _spec_plans(existing: dict[str, str | None], meta: dict[str, Any],
                impact: dict[str, Any]) -> list[dict[str, Any]]:
    """只更新真正受影响的模块规格;失效规则进历史段,无关行保持原样。"""

    grouped: dict[str, list[dict[str, Any]]] = {}
    for item in impact["must_sync"]:
        grouped.setdefault(str(item.get("location") or ""), []).append(item)
    untouched_lines: dict[str, list[str]] = {}
    for item in impact["unaffected"]:
        old = str(item.get("old_text") or "")
        if old:
            untouched_lines.setdefault(
                str(item.get("location") or ""), []).append(old)
    files: list[dict[str, Any]] = []
    for path in sorted(grouped):
        if not path:
            continue
        result = update_spec(existing.get(path), grouped[path], meta)
        files.append({
            "path": path, "role": "模块规格", "content": result["content"],
            "expected_sha256": sha256_text(existing.get(path)),
            "retired": result["retired"],
            "missing_old": result["missing"],
            "expected_contains": untouched_lines.get(path) or []})
    return files


def _baseline_files(existing: dict[str, str | None], meta: dict[str, Any],
                    record: dict[str, Any],
                    impact: dict[str, Any]) -> list[dict[str, Any]]:
    """当前有效设计与简短变更记录;变更记录最后写,避免先落状态声明。"""

    design_path = str(meta.get("design_path") or "")
    record_path = str(meta.get("change_record_path") or "")
    if not record_path:
        return []
    plan = {"change": record, "impact": impact, "version": _version(meta)}
    files: list[dict[str, Any]] = []
    if design_path and dict(meta.get("authorization") or {}).get("sync"):
        files.append({
            "path": design_path, "role": "当前有效设计",
            "content": render_baseline(existing.get(design_path), meta, plan),
            "expected_sha256": sha256_text(existing.get(design_path))})
    files.append({
        "path": record_path, "role": "变更记录",
        "content": render_change_record(meta, record, _initial_states(),
                                         planned=True),
        "expected_sha256": sha256_text(existing.get(record_path))})
    return files


def _unlocated(specs: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """现行设计里找不到的旧规则:不能确认它已退出现行版本,先报告。"""

    items: list[dict[str, Any]] = []
    for spec in specs:
        for missing in spec.get("missing_old") or []:
            items.append({**missing, "location": spec["path"]})
    return items


def _pending_sync(meta: dict[str, Any], impact: dict[str, Any]) -> list[str]:
    """待同步项:缺同步授权时留下必须同步的对象,不能用写入授权代替。"""

    if dict(meta.get("authorization") or {}).get("sync"):
        return [str(item["id"]) for item in impact["needs_tradeoff"]]
    return [str(item["id"]) for item in impact["must_sync"]] or [
        str(meta.get("design_path") or "核心基线")]


def _version(meta: dict[str, Any]) -> dict[str, Any]:
    return {"from": str(meta.get("version_from") or ""),
            "to": str(meta.get("version_to") or ""),
            "change": str(meta.get("change") or "substantive"),
            "sync_ref": str(meta.get("sync_ref") or "")}


def _initial_states() -> dict[str, bool]:
    return {"adopted": True, "saved": False, "synced": False,
            "implemented": False, "verified": False}


def _locations_ready(meta: dict[str, Any],
                     files: list[dict[str, Any]]) -> bool:
    return bool(meta.get("design_path") and meta.get("change_record_path")
                and files)


def _states_after(plan: dict[str, Any],
                  written: list[str]) -> dict[str, bool]:
    """写入完成后按实际写入结果分档:同步随当前设计的实际写入成立。"""

    design_path = str(plan.get("design_path") or "")
    record_path = str(plan.get("change_record_path") or "")
    return {"adopted": True, "saved": record_path in written,
            "synced": design_path in written and record_path in written,
            "implemented": False, "verified": False}


def _content(files: list[dict[str, Any]]) -> dict[str, str]:
    return {str(item["path"]): str(item["content"]) for item in files}


def _result(plan: dict[str, Any], status: str, saved: bool) -> dict[str, Any]:
    return {
        "op": "change", "status": status, "saved": saved,
        "module": plan.get("module"),
        "design_path": plan.get("design_path"),
        "change_record_path": plan.get("change_record_path"),
        "states": plan.get("states"),
        "version": plan.get("version"),
        "written": [],
    }


def _spec_failures(plan: dict[str, Any],
                   readback_map: dict[str, str | None]) -> list[str]:
    """回读核对模块规格:新规则就位、旧规则退出、未受影响行未变。"""

    failures: list[str] = []
    for item in plan.get("specs") or []:
        path = str(item.get("path") or "")
        text = readback_map.get(path)
        if text is None:
            failures.append(f"回读目标不存在:{path}")
            continue
        for entry in item.get("retired") or []:
            if f"替代：{entry['new']}" not in text:
                failures.append(f"旧规则未留下替代关系:{entry['id']}")
        for needle in item.get("expected_contains") or []:
            if needle not in text:
                failures.append(f"回读缺少未受影响内容:{needle}")
    return failures


def _failure(plan: dict[str, Any], outcome: dict[str, Any],
             written: list[str]) -> dict[str, Any]:
    """按通道真实依据报告未保存:冲突、被拒或回读失败,不换通道重试。"""

    status = ("conflict" if outcome["outcome"] == "conflict"
              else "denied" if outcome["outcome"] == "denied"
              else "save_unconfirmed")
    path = str(outcome.get("path") or "")
    result = {**_result(plan, status, False), "written": written,
              "path": path,
              "report": failure_report(plan, outcome, written),
              "handoff_ready": False}
    if outcome.get("rule_stage"):
        result["rule_stage"] = outcome["rule_stage"]
    if outcome.get("channel_result"):
        result["channel_result"] = outcome["channel_result"]
    return result


__all__ = ["plan_change", "apply_change", "verify_change", "answer_turn"]

#!/usr/bin/env python3
"""Game-Design 模块规格交接接缝(统一设计问答框架票 04)。

公开 interface:
  plan_handoff(records, meta, existing) -> dict
  apply_handoff(plan, channel, readback) -> dict
  verify_handoff(plan, readback_map) -> dict

模块收敛后,本接缝消费票 03 的**已采纳决定记录**(``decision_records.
parse_record`` 唯一解释),汇总该模块已采纳且未同步的决定,排除候选与临时
假设,把九类规格内容整理为可交接的模块规格草稿,并给出只同步实际受影响
资料的计划:模块规格、核心基线版本与指纹、术语表、决定记录的同步状态。
未决项与延期事项连同影响原样保留;阻断当前交接的关键缺口报告未完成,不用
默认值补齐。实质变化按既有版本与指纹规则处理,纯格式修正不冒充新产品要求。
目标或范围变化只输出统筹同步交接,不代写管理资料。

分工:九类内容的渲染与适用性核对在 ``spec_render.py``;版本、双指纹与同步
范围在 ``spec_sync.py``;本 module 负责汇总、编排与经受控通道提交(与票 03
的 ``apply_save`` 同一条路径),写入后回读核对,没有回读成功不得称为已同步。
"""

from __future__ import annotations

from typing import Any, Callable

from decision_records import parse_record
from gate_commit import commit_path
import checks as checks_seam
from spec_render import (
    ADR_CONDITIONS, SECTION_SPECS, condition_label, render_spec, section_gaps,
)
from spec_report import (
    blocked_report, component_report, incomplete_report, saved_report,
)
from spec_sync import (
    compare_existing, sync_files, version_plan, version_warnings,
)


def plan_handoff(records: dict[str, str], meta: dict[str, Any],
                 existing: dict[str, str | None]) -> dict[str, Any]:
    """整理模块规格草稿与同步计划;不写入,只给出内容与写入前核对。"""

    module = str(meta.get("module") or "")
    record_path = str(meta.get("record_path") or "")
    spec_path = str(meta.get("spec_path") or "")
    existing = {**(existing or {}), **(records or {})}
    parsed = _merged_records(records, module)
    decision = _decision_summary(parsed, meta)
    blocking = [str(qid) for qid in (meta.get("blocking_qids") or [])
                if str(qid) not in decision["settled"]]
    missing = section_gaps(meta, parsed) + (
        [{"field": "blocking", "detail":
          f"阻断当前交接的未决项:{'、'.join(blocking)}"}] if blocking else [])
    verification = list(meta.get("verification") or [])
    blocking_verification = [str(item.get("question") or "")
                             for item in verification
                             if item.get("blocks_stage")]
    base = _handoff_base(meta, parsed, decision, missing, blocking,
                         blocking_verification, verification)
    authorization = dict(meta.get("authorization") or {})
    if not spec_path or not record_path:
        return {**base, "status": "unauthorized", "saved": False,
                "handoffable": False, "content": None, "spec": None,
                "reason": "缺少模块规格或决定记录位置,无法定位交付位置"}
    base = {**base, **_handoff_plan_files(meta, parsed, decision, spec_path,
                                          existing, authorization)}
    if missing:
        return {**base, "status": "incomplete", "saved": False,
                "handoffable": False, "content": None,
                "report": incomplete_report(module, missing, blocking,
                                            blocking_verification)}
    if not authorization.get("write"):
        return {**base, "status": "read_only", "saved": False,
                "handoffable": False, "content": None,
                "reason": "只读讨论:未获写入授权,模块规格保留待授权后同步",
                "report": component_report(decision, meta, parsed,
                                           base["files"], read_only=True)}
    return {**base, "status": "planned", "saved": False, "handoffable": True,
            "content": base["spec"]["content"],
            "sync_authorized": bool(authorization.get("sync")),
            "report": component_report(decision, meta, parsed, base["files"]),
            "note": f"整理 {module} 模块规格并同步受影响资料"
                    f"（{len(base['files'])} 个文件）"}


def _handoff_base(meta: dict[str, Any], parsed: dict[str, Any],
                  decision: dict[str, Any], missing: list[dict],
                  blocking: list[str], blocking_verification: list[str],
                  verification: list[dict]) -> dict[str, Any]:
    """计划的公共字段:决定汇总、缺口、未决、ADR 判定与统筹交接。"""

    return {
        "op": "handoff",
        "module": str(meta.get("module") or ""),
        "record_path": str(meta.get("record_path") or ""),
        "spec_path": str(meta.get("spec_path") or ""),
        "design_path": str(meta.get("design_path") or ""),
        "glossary_path": str(meta.get("glossary_path") or ""),
        "date": str(meta.get("date") or ""),
        "sync_ref": str(meta.get("sync_ref") or ""),
        "decision": decision,
        "to_sync": list(decision["to_sync"]),
        "synced": list(decision["synced"]),
        "superseded": sorted({item["qid"] for item in parsed["superseded"]}),
        "pending": list(parsed["pending"]),
        "missing": missing,
        "blocking": blocking,
        "blocking_verification": blocking_verification,
        "gaps": missing,
        "verification": verification,
        "decision_states": decision["states"],
        "states": decision["aggregate"],
        "untouched": [str(path) for path in (meta.get("untouched") or [])],
        "adr": [dict(item) for item in (meta.get("adr") or [])
                if all(item.get(cond) for cond in ADR_CONDITIONS)],
        "adr_rejected": [_adr_rejected(item)
                         for item in (meta.get("adr") or [])
                         if not all(item.get(cond) for cond in ADR_CONDITIONS)],
        "producer_handoff": _producer_handoff(meta),
    }


def _handoff_plan_files(meta: dict[str, Any], parsed: dict[str, Any],
                        decision: dict[str, Any], spec_path: str,
                        existing: dict[str, str | None],
                        authorization: dict[str, Any]) -> dict[str, Any]:
    """规格渲染、新旧语义对比、版本判断与同步文件清单。"""

    spec_text = render_spec(str(meta.get("module") or ""), meta, parsed,
                            decision)
    compare = compare_existing(existing.get(spec_path), spec_text,
                               bool(existing.get(spec_path)))
    version = version_plan(meta, compare)
    files = sync_files(meta, parsed, decision, version, spec_text,
                       existing, authorization)
    return {"spec": {"path": spec_path, "content": spec_text},
            "compare": compare, "version": version, "files": files,
            "warnings": version_warnings(meta, compare)}


def _merged_records(records: dict[str, str], module: str) -> dict[str, Any]:
    """合并本模块的已采纳决定记录;格式由 decision_records 唯一解释。"""

    merged: dict[str, Any] = {"decisions": {}, "pending": [],
                              "pending_qids": set(), "superseded": [],
                              "sync_done": {}, "rounds": 0, "found": False}
    for path in sorted(records or {}):
        text = (records or {})[path]
        if text is None:
            continue
        parsed = parse_record(text, module)
        if not parsed["found"]:
            continue
        merged["found"] = True
        merged["decisions"].update(parsed["decisions"])
        merged["superseded"].extend(parsed["superseded"])
        merged["pending"].extend(parsed["pending"])
        merged["pending_qids"].update(parsed["pending_qids"])
        merged["sync_done"].update(parsed["sync_done"])
        merged["rounds"] += parsed["rounds"]
    latest: dict[str, dict[str, Any]] = {}
    for item in merged["pending"]:
        qid = item["qid"]
        if qid not in latest or (item.get("round") or 0) >= (
                latest[qid].get("round") or 0):
            latest[qid] = item
    merged["pending"] = [latest[qid] for qid in sorted(latest)]
    merged["pending_qids"] = {item["qid"] for item in merged["pending"]}
    return merged


def _decision_summary(parsed: dict[str, Any],
                      meta: dict[str, Any]) -> dict[str, Any]:
    """汇总已采纳决定:排除候选与临时假设,单独列出已同步与待同步。"""

    settled: dict[str, dict[str, Any]] = {}
    states: dict[str, dict[str, bool]] = {}
    for qid, item in parsed["decisions"].items():
        if item.get("superseded"):
            continue
        settled[qid] = item
        states[qid] = {"adopted": True, "saved": True,
                       "synced": bool(item.get("synced")),
                       "implemented": False, "verified": False}
    to_sync = sorted(qid for qid, item in settled.items()
                     if not item.get("synced"))
    synced = sorted(qid for qid, item in settled.items() if item.get("synced"))
    aggregate = {"adopted": bool(settled),
                 "synced": bool(settled) and not to_sync,
                 "implemented": False, "verified": False}
    return {"settled": settled, "states": states, "to_sync": to_sync,
            "synced": synced, "aggregate": aggregate,
            "adopted_count": len(settled),
            "pending": list(parsed["pending"]),
            "excluded": _excluded(parsed, meta)}


def _excluded(parsed: dict[str, Any], meta: dict[str, Any]) -> list[dict]:
    """未进入交付的候选、临时假设与未决项(保持各自身份)。"""

    items: list[dict[str, str]] = []
    for text in meta.get("proposals") or []:
        items.append({"kind": "候选方案", "detail": str(text)})
    for text in meta.get("assumptions") or []:
        items.append({"kind": "临时假设", "detail": str(text)})
    for item in parsed["pending"]:
        items.append({"kind": "未决项", "detail":
                      f"{item['qid']} {item['title']}：{item['status']}"})
    return items


def _adr_rejected(item: dict[str, Any]) -> dict[str, str]:
    actual = "、".join(
        f"{'满足' if item.get(cond) else '不满足'}{condition_label(cond)}"
        for cond in ADR_CONDITIONS)
    return {"title": str(item.get("title") or ""), "detail":
            f"{item.get('title')}：未同时满足改变成本高、缺背景会令人困惑、"
            f"存在真实取舍三项条件（实际：{actual}）,"
            f"不单独建立详细 ADR,背景进模块规格。"}


def _producer_handoff(meta: dict[str, Any]) -> dict[str, Any] | None:
    items = list(meta.get("scope_change") or [])
    if not items:
        return None
    return {"items": [{"content": str(item.get("content") or ""),
                       "impact": str(item.get("impact") or "")}
                      for item in items],
            "action": "显式调用 Game-Producer 完成目标或范围变更同步;"
                      "本入口不代写 PROJECT 等管理资料。"}


def apply_handoff(plan: dict[str, Any], channel: Any,
                  readback: Callable[[str], str | None],
                  *, session: dict[str, Any] | None = None) -> dict[str, Any]:
    """经同一受控通道逐个提交受影响文件;每个文件提交后回读核对。

    传入 ``session``(票 08 ``checks.begin`` 建立的会话)时,按同一检查时机
    约定:模块收敛的此次交接先做一次统一核对,每个文件单独计数写入并逐次
    经通道核对授权与版本;不传时保持原有行为不变。
    """

    status = plan.get("status")
    if status in {"incomplete", "read_only", "unauthorized"}:
        return {**_result(plan, status, False), "written": [],
                "files": plan.get("files") or [],
                "to_sync": plan.get("to_sync") or [],
                "blocking_verification":
                    plan.get("blocking_verification") or [],
                "session": session, "checks": None,
                "report": plan.get("report") or blocked_report(plan)}
    if status != "planned":
        return {**_result(plan, "invalid", False), "written": [],
                "report": f"计划状态 {status} 不可执行",
                "next_round_ready": False, "session": session, "checks": None}
    session = checks_seam.converge_plan(
        session, plan, module=str(plan.get("module") or ""),
        impact={"must_sync": [{"id": qid} for qid in
                              (plan.get("to_sync") or [])]})
    written: list[str] = []
    for item in plan.get("files") or []:
        outcome = _commit_file(plan, item, channel, readback, written)
        if outcome is not None:
            session = _blocked(session, item)
            outcome["session"], outcome["checks"] = session, None
            return outcome
        written.append(str(item.get("path") or ""))
        session = checks_seam.write_item(
            session, item, label="规格交接写入")
    state = _handoff_states(plan, readback)
    record_path = str(plan.get("record_path") or "")
    session, checks = checks_seam.after_write(
        session, module=str(plan.get("module") or ""), path=record_path,
        readback=readback,
        known_paths=[str(item.get("path") or "")
                     for item in plan.get("files") or []])
    return {**_result(plan, "saved", True), "written": written,
            "channel_result": {"decision": "allow"},
            "decision_states": plan.get("decision_states") or {},
            "states": state, "to_sync": [] if state["synced"] else
                plan.get("to_sync") or [],
            "blocking_verification": plan.get("blocking_verification") or [],
            "producer_handoff": plan.get("producer_handoff"),
            "untouched": plan.get("untouched") or [],
            "next_round_ready": True, "session": session, "checks": checks,
            "report": saved_report(plan, written, state)}


def _blocked(session: dict[str, Any] | None,
             item: dict[str, Any]) -> dict[str, Any] | None:
    """交接受阻滞时作废相关旧结果(票 08):无会话时保持原有行为不变。"""

    if session is None:
        return None
    invalidated = checks_seam.invalidate(
        session, "write_failed", paths=[str(item.get("path") or "")],
        detail="规格交接受阻")
    return invalidated["session"]


def _commit_file(plan: dict[str, Any], item: dict[str, Any], channel: Any,
                 readback: Callable[[str], str | None],
                 written: list[str]) -> dict[str, Any] | None:
    """提交一个文件:核对目标版本与当前授权,写入后回读;异常返回结果。"""

    path = str(item.get("path") or "")
    expected = str(item.get("expected_sha256") or "absent")
    outcome = commit_path(
        channel, readback, path=path, content=item.get("content") or "",
        expected_sha256=expected,
        note=f"{plan.get('module')} 模块规格交接（{item.get('role')}）")
    if outcome["ok"]:
        return None
    if outcome["outcome"] == "conflict":
        return {**_result(plan, "conflict", False), "written": written,
                "rule_stage": "version", "path": path,
                "report": (f"版本冲突：{path} 已被改动"
                           f"（计划版本 {expected}，"
                           f"实际 {outcome.get('actual_sha256')}）;"
                           f"本轮交接未完成,剩余文件未写入,"
                           f"先重新读取实际内容再决定,不覆盖旧快照。")}
    if outcome["outcome"] == "denied":
        if outcome.get("denied_at") == "scope":
            return {**_result(plan, "denied", False), "written": written,
                    "rule_stage": outcome.get("rule_stage"), "path": path,
                    "report": (f"写入前核对当前授权未通过:凭据不可写 {path}"
                               f"（rule_stage={outcome.get('rule_stage')}）;"
                               f"本轮交接未完成,所有文件均未保存,"
                               f"不换通道或路径重试。")}
        return {**_result(plan, "denied", False), "written": written,
                "rule_stage": outcome.get("rule_stage"), "path": path,
                "channel_result": outcome.get("channel_result"),
                "report": (f"受控通道拒绝写入（rule_stage="
                           f"{outcome.get('rule_stage')}）："
                           f"{outcome.get('reason')};{path} 未保存,"
                           f"本轮交接未完成（已写入文件按实际保留）;"
                           f"不换通道重试。")}
    return {**_result(plan, "save_unconfirmed", False),
            "written": written + [path], "path": path,
            "report": (f"写入后回读核对失败（{path}）:"
                       f"落盘未确认,不得称为已同步。")}


def _handoff_states(plan: dict[str, Any],
                    readback: Callable[[str], str | None]) -> dict:
    """分档状态:写入完成后再按实际记录核对同步状态,不自动推定。"""

    text = readback(str(plan.get("record_path") or "")) or ""
    parsed = parse_record(text, str(plan.get("module") or ""))
    targets = [qid for qid in (plan.get("to_sync") or [])
               if kind_is_sync_file(plan, qid)]
    synced = (all(qid in parsed["sync_done"] for qid in targets)
              if targets else not (plan.get("to_sync") or []))
    return {"adopted": True, "saved": True, "synced": synced,
            "implemented": False, "verified": False}


def kind_is_sync_file(plan: dict[str, Any], qid: str) -> bool:
    """该决定是否在本次交接的文件计划中包含同步状态更新。"""

    return any(item.get("role") == "决定记录同步状态"
               and qid in (item.get("synced") or [])
               for item in plan.get("files") or [])


def verify_handoff(plan: dict[str, Any],
                   readback_map: dict[str, str | None]) -> dict[str, Any]:
    """回读核对:规格完整、基线引用与指纹、同步状态、历史未丢失。"""

    failures: list[str] = []
    spec_path = str(plan.get("spec_path") or "")
    spec_text = readback_map.get(spec_path)
    if spec_text is None:
        failures.append(f"回读目标不存在:{spec_path}")
    else:
        planned = (plan.get("spec") or {}).get("content")
        if planned is not None and spec_text != planned:
            failures.append("回读内容与计划内容不一致")
        for _key, title, _purpose in SECTION_SPECS:
            if f"## {title}" not in spec_text:
                failures.append(f"规格缺少类别:{title}")
    version = plan.get("version") or {}
    if version.get("change") == "substantive":
        failures.extend(_baseline_failures(plan, readback_map, spec_path,
                                           version))
    record = readback_map.get(str(plan.get("record_path") or ""))
    if record is None:
        failures.append("决定记录不存在")
    else:
        parsed = parse_record(record, str(plan.get("module") or ""))
        if plan.get("to_sync") and version.get("change") == "substantive" \
                and plan.get("sync_authorized", True):
            for qid in plan["to_sync"]:
                if qid not in parsed["sync_done"]:
                    failures.append(f"同步状态未更新:{qid}")
        for qid in plan.get("superseded") or []:
            if f"·{qid} " not in record:
                failures.append(f"历史决定丢失:{qid}")
    if plan.get("status") == "incomplete" and spec_text is not None:
        failures.append("未完成模块不应留下规格交付")
    return {"ok": not failures, "failures": failures, "spec_path": spec_path}


def _baseline_failures(plan: dict[str, Any],
                       readback_map: dict[str, str | None], spec_path: str,
                       version: dict[str, Any]) -> list[str]:
    design = readback_map.get(str(plan.get("design_path") or ""))
    if design is None:
        return ["核心基线不存在"]
    failures: list[str] = []
    if version.get("to") not in design:
        failures.append(f"基线未登记新版本:{version.get('to')}")
    if spec_path not in design:
        failures.append("基线未引用模块规格位置")
    if "内容指纹：sha256:" not in design or "归一指纹：sha256:" not in design:
        failures.append("基线缺内容指纹或归一指纹登记")
    return failures


def _result(plan: dict[str, Any], status: str, saved: bool) -> dict[str, Any]:
    return {
        "op": plan.get("op"),
        "status": status,
        "saved": saved,
        "module": plan.get("module"),
        "record_path": plan.get("record_path"),
        "spec_path": plan.get("spec_path"),
        "design_path": plan.get("design_path"),
        "states": plan.get("states"),
        "version": plan.get("version"),
        "pending": plan.get("pending"),
    }

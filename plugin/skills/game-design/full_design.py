#!/usr/bin/env python3
"""Game-Design 完整设计成稿接缝(统一设计问答框架票 05)。

公开 interface:
  plan_delivery(existing, meta, material) -> dict
  apply_delivery(plan, channel, readback) -> dict
  verify_delivery(plan, readback_map) -> dict

消费票 02/03/04 的产物:覆盖地图与范围分层来自 ``coverage_map.build_map``,
玩家视角核对与跨模块矛盾来自 ``journey.walkthrough``,现行系统规则来自模块
规格(只引用其位置,不重复规则正文)。整理四类交付内容并按交接标准核对:
覆盖地图无未解释空缺、关键流程闭合、当前准备制作的必要规则可执行、范围与
内容清楚、各处现行规则一致、关键未知有方法与影响说明、跨模块矛盾已处理。
有阻断交接的关键缺口或未处理矛盾时报告未完成,不产出可落盘内容、不因目录
齐全宣称整体完成;未获制作授权不自动实施原型,没有实际证据不报告体验或
市场效果已验证。

写入与票 03 ``apply_save``、票 04 ``apply_handoff`` 同一条受控通道
(``decisions.commit_path``),逐文件核对授权与目标版本并回读;没有回读成功
不得称为已保存或已同步。渲染在 ``full_render.py``,报告措辞在
``full_report.py``。
"""

from __future__ import annotations

from typing import Any, Callable

from check_state import references
from coverage_map import build_map
from gate_commit import commit_path
import checks as checks_seam
from decision_records import sha256_text
from journey import walkthrough
from spec_render import text_is_vague
from full_render import (
    ROLE_CONTENT, ROLE_DESIGN, ROLE_SPECS, ROLE_VERSION, deliverable_outputs,
    render_content, render_design, render_version,
)
from full_report import (
    blocked_report, check_failed_report, failure_report, pending_sync_report,
    plan_report, read_only_report, saved_report,
)


def plan_delivery(existing: dict[str, str | None], meta: dict[str, Any],
                  material: dict[str, Any]) -> dict[str, Any]:
    """整理四类交付内容并按交接标准核对;不写入,只给出内容与写入前核对。"""

    coverage = build_map(material)
    journey = walkthrough(material)
    contradictions = list(journey["contradictions"])
    missing = _missing(coverage, journey, material, meta)
    missing.extend(_location_gaps(meta, existing))
    outputs = [(path, role) for path, role in deliverable_outputs(meta) if path]
    planned_files = _files(existing, meta, material, coverage, journey,
                           outputs)
    authorization = dict(meta.get("authorization") or {})
    to_sync = list(meta.get("to_sync") or [])
    sync_authorized = bool(authorization.get("sync"))
    files = planned_files if sync_authorized else []
    completion: dict[str, Any] | None = None
    if not sync_authorized:
        to_sync = to_sync or [path for path, role in outputs
                              if path and role != ROLE_SPECS]
        pending = _pending_sync_file(existing, meta, to_sync)
        if pending:
            files = [pending]
    else:
        # 完成标记不进写入计划:全部必要检查成功后才由 apply_delivery
        # 写入,检查失败时保留待同步记录的可恢复事实。
        completion = _completed_pending_file(existing, meta)
    base = {
        "op": "delivery",
        "game": str(meta.get("game") or material.get("game") or ""),
        "date": str(meta.get("date") or ""),
        "entry": str((meta.get("doc_map") or {}).get("design") or ""),
        "outputs": [{"path": path, "role": role} for path, role in outputs],
        "coverage": coverage,
        "journey": journey,
        "contradictions": contradictions,
        "missing": missing,
        "gap_needles": [item["needle"] for item in missing],
        "blocking_qids": [str(qid) for qid in (meta.get("blocking_qids")
                                               or [])],
        "files": files,
        "pending_complete_file": completion,
        "to_sync": to_sync,
        "untouched": [str(path) for path in (meta.get("untouched") or [])],
        "handoff_ready": not missing and not contradictions and sync_authorized,
        "states": {"adopted": True, "saved": False,
                   "synced": sync_authorized and not to_sync,
                   "implemented": False, "verified": False},
        "sync_authorized": sync_authorized,
    }
    if missing or contradictions:
        return {**base, "status": "incomplete", "saved": False, "content": None,
                "report": blocked_report(base)}
    if not base["entry"]:
        return {**base, "status": "unauthorized", "saved": False,
                "content": None, "reason": "缺少游戏设计主文档位置,无法定位入口",
                "report": "缺少游戏设计主文档位置:不自行另建一套文档;"
                          "先按 CONFIG 文档映射确认落点。"}
    content = {"design": _design_content(planned_files)}
    if not authorization.get("write"):
        return {**base, "status": "read_only", "saved": False,
                "content": content,
                "reason": "只读讨论:未获写入授权,交付内容保留待授权后写入",
                "report": read_only_report(base)}
    return {**base, "status": "planned", "saved": False,
            "content": content, "report": plan_report(base)}


def _design_content(files: list[dict[str, Any]]) -> str:
    """计划内容中的主文档正文(调用方与命令行入口据此预览)。"""

    for item in files:
        if item.get("role") == ROLE_DESIGN:
            return str(item.get("content") or "")
    return ""


def _missing(coverage: dict[str, Any], journey: dict[str, Any],
             material: dict[str, Any],
             meta: dict[str, Any]) -> list[dict[str, Any]]:
    """按交接标准逐条核对:覆盖、流程、模块、范围、规则、未知。"""

    missing: list[dict[str, Any]] = []
    missing.extend(_coverage_gaps(coverage.get("domains") or {}))
    missing.extend(_journey_gaps(journey.get("steps") or []))
    missing.extend(_module_gaps(meta.get("module_specs") or []))
    missing.extend(_scope_gaps(_clarify(material)))
    missing.extend(_rule_gaps(material))
    missing.extend(_blocking_gaps(meta.get("blocking_qids") or []))
    return missing


def _location_gaps(meta: dict[str, Any],
                   existing: dict[str, str | None]) -> list[dict[str, Any]]:
    """四类交付必须有可定位的权威位置;缺路径或权威规格不存在不得静默丢掉。"""

    gaps: list[dict[str, Any]] = []
    for path, role in deliverable_outputs(meta):
        if not path:
            gaps.append({"needle": f"位置:{role}", "kind": "交付位置缺失",
                         "detail": f"{role}没有可定位的权威位置",
                         "gap": "四类交付的权威位置不可定位",
                         "method": "按 CONFIG 文档映射确认落点",
                         "impact": "残缺交付不能交接", "blocks": True})
            continue
        if role == ROLE_SPECS and existing.get(path) is None:
            gaps.append({"needle": f"位置:{role}", "kind": "交付位置缺失",
                         "detail": f"{role}权威文件不存在:{path}",
                         "gap": "系统规则与数值没有可回读的权威规格",
                         "method": "先完成该模块规格交接或确认落点",
                         "impact": "不能因目录齐全宣称全游戏设计完成",
                         "blocks": True})
    return gaps


def _blocking_gaps(qids: list[Any]) -> list[dict[str, Any]]:
    """调用方声明的阻断当前交接的未决项:未解决前不得宣布完成。"""

    return [{"needle": f"阻断:{qid}", "kind": "阻断未决项",
             "detail": f"{qid} 阻断当前交接,尚未解决",
             "gap": "仍有阻断交接的未决项", "method": "先澄清该问题",
             "impact": "阻断当前交接与制作", "blocks": True}
            for qid in qids]


def _coverage_gaps(domains: dict[str, dict[str, Any]]) -> list[dict[str, Any]]:
    """覆盖地图的空缺与未查清项;未知有方法与影响说明即可交接。"""

    gaps: list[dict[str, Any]] = []
    for entry in domains.values():
        if entry["status"] == "gap":
            gaps.append(_coverage_entry(
                f"覆盖:{entry['title']}", entry.get("gap") or "未写明缺口",
                domain=entry["title"]))
        elif entry["status"] == "unknown" \
                and not (entry.get("method") and entry.get("impact")):
            gaps.append(_coverage_entry(
                f"未知:{entry['title']}",
                f"{entry['title']}：未查清且未说明方法与影响",
                domain=entry["title"]))
    return gaps


def _journey_gaps(steps: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [{"needle": f"流程:{step['label']}", "kind": "流程未闭合",
             "detail": f"{step['label']}：{step['detail'] or '未写明'}",
             "gap": "关键流程未闭合", "method": "回到本轮问题澄清",
             "impact": "影响完整游玩过程与验收", "blocks": True}
            for step in steps if step["status"] != "closed"]


def _module_gaps(specs: list[dict[str, Any]]) -> list[dict[str, Any]]:
    gaps: list[dict[str, Any]] = []
    for spec in specs:
        module = str(spec.get("module") or "")
        reasons = [str(item) for item in spec.get("gaps") or []]
        if str(spec.get("status") or "") == "handoffable" and not reasons:
            continue
        gaps.append({"needle": f"模块:{module}", "kind": "模块规格未完成",
                     "detail": "；".join(reasons)
                     or f"{module}尚未达到可交接状态",
                     "gap": "当前准备制作的必要规则不可交接",
                     "method": "先完成该模块的关键规则",
                     "impact": "阻断当前版本制作", "blocks": True})
    return gaps


def _scope_gaps(questions: list[dict[str, str]]) -> list[dict[str, Any]]:
    return [{"needle": f"范围:{item['question']}", "kind": "范围待澄清",
             "detail": f"{item['question']}（{item['why_needed']}）",
             "gap": "当前版本范围未确定", "method": "与开发者确认取舍",
             "impact": "影响首发范围与验收对象", "blocks": True}
            for item in questions]


def _rule_gaps(material: dict[str, Any]) -> list[dict[str, Any]]:
    """必要规则不可执行,以及引用规则没有现行权威位置。"""

    current = {str(rule.get("id")) for rule in material.get("rules") or []}
    gaps: list[dict[str, Any]] = []
    for rule in material.get("rules") or []:
        if not text_is_vague(str(rule.get("text") or "")):
            continue
        gaps.append({"needle": f"规则:{rule.get('id')}",
                     "kind": "规则不可执行",
                     "detail": f"{rule.get('title')}以形容词代替关键行为,不可判定",
                     "gap": "必要规则不可执行", "method": "给出可判定规则与数值",
                     "impact": f"影响 {rule.get('location')} 的执行",
                     "blocks": True})
    for ref, source in _rule_references(material):
        if ref in current:
            continue
        gaps.append({"needle": f"规则一致:{ref}", "kind": "现行规则不一致",
                     "detail": f"{source}引用的规则 {ref} 没有现行权威位置",
                     "gap": "各处现行规则不一致",
                     "method": "补上规则位置或删掉失效引用",
                     "impact": "执行者会用到前后不一致的规则",
                     "blocks": True})
    return gaps


def _rule_references(material: dict[str, Any]) -> list[tuple[str, str]]:
    """内容需求里引用的规则 id:用于核对各处现行规则一致。"""

    refs: list[tuple[str, str]] = []
    content = dict(material.get("content") or {})
    for key, title in (("levels_events", "关卡与事件结构"),
                       ("templates", "内容模板"), ("characters", "角色"),
                       ("scenes", "场景"), ("ui", "界面"),
                       ("animation_vfx", "动画与特效"), ("audio", "声音需求")):
        for item in content.get(key) or []:
            for ref in (item or {}).get("rules") or []:
                refs.append((str(ref), f"{title}（{item.get('text')}）"))
    return refs


def _coverage_entry(needle: str, detail: str, *, domain: str) -> dict[str, Any]:
    return {"needle": needle, "kind": "覆盖未闭合", "detail": detail,
            "gap": "覆盖地图有空缺或未查清", "method": "按推进焦点澄清",
            "impact": f"影响{domain}", "blocks": True}


def _clarify(material: dict[str, Any]) -> list[dict[str, str]]:
    scope = dict(material.get("scope") or {})
    return [{"question": str(item.get("question") or ""),
             "why_needed": str(item.get("why_needed") or "")}
            for item in scope.get("clarify") or []]


def _files(existing: dict[str, str | None], meta: dict[str, Any],
           material: dict[str, Any], coverage: dict[str, Any],
           journey: dict[str, Any],
           outputs: list[tuple[str, str]]) -> list[dict[str, Any]]:
    """本次要写入的文件:主文档、内容需求、版本方案;

    系统规则与数值沿用模块规格的现行权威位置,本入口不重写规则正文。
    """

    doc_map = dict(meta.get("doc_map") or {})
    content_path = str(doc_map.get("content") or "")
    version_path = str(doc_map.get("version") or "")
    deliverables = {
        str(doc_map.get("design") or ""): render_design(
            {**meta, "design_path": str(doc_map.get("design") or "")},
            material, coverage, journey),
        content_path: render_content(existing.get(content_path), meta,
                                     material),
        version_path: render_version(meta, material, coverage, journey),
    }
    files: list[dict[str, Any]] = []
    for path, role in outputs:
        if path not in deliverables:
            continue
        files.append({"path": path, "role": role,
                      "content": deliverables[path],
                      "expected_sha256": sha256_text(existing.get(path))})
    return files


def apply_delivery(plan: dict[str, Any], channel: Any,
                   readback: Callable[[str], str | None],
                   *, session: dict[str, Any] | None = None) -> dict[str, Any]:
    """经同一受控通道逐个提交交付文件;每个文件提交后回读核对。

    传入 ``session``(票 08 ``checks.begin`` 建立的会话)时,按同一检查时机
    约定:落盘前做一次收敛统一核对,每个文件单独计数写入并逐次经通道核对
    授权与版本,落盘后回读核对新改引用;核验失败时按失败对象作废依赖的
    旧检查结果(断链/证据不足),无关结果保留。不传时保持原有行为不变。
    待同步记录的完成标记在全部必要检查成功后才写入;失败时该记录保持
    可恢复的待同步事实,不宣布已同步。
    """

    status = plan.get("status")
    if status in {"incomplete", "read_only", "unauthorized"}:
        report = plan.get("report") or blocked_report(plan)
        return {**_result(plan, status, False), "written": [],
                "outputs": plan.get("outputs") or [],
                "contradictions": plan.get("contradictions") or [],
                "missing": plan.get("missing") or [],
                "report": report,
                "session": session, "checks": None}
    if status != "planned":
        return {**_result(plan, "invalid", False), "written": [],
                "report": f"计划状态 {status} 不可执行", "handoff_ready": False,
                "session": session, "checks": None}
    session = checks_seam.converge_plan(session, plan,
                                        impact=plan.get("impact"))
    sync_authorized = bool(plan.get("sync_authorized"))
    written: list[str] = []
    for item in plan.get("files") or []:
        outcome = commit_path(
            channel, readback, path=str(item.get("path") or ""),
            content=item.get("content") or "",
            expected_sha256=str(item.get("expected_sha256") or "absent"),
            note=f"{plan.get('game')} 完整设计交付（{item.get('role')}）")
        if not outcome["ok"]:
            failed_status = ("denied" if outcome["outcome"] == "denied"
                             else outcome["outcome"])
            return {**_result(plan, failed_status, False),
                    "written": written, "path": outcome.get("path"),
                    "rule_stage": outcome.get("rule_stage"),
                    "report": failure_report(plan, outcome, written),
                    "session": checks_seam.invalidate_outcome(
                        session, outcome),
                    "checks": None}
        written.append(str(item.get("path") or ""))
        session = checks_seam.write_item(
            session, item, label="交付写入")
    if not sync_authorized:
        states = {"adopted": True, "saved": bool(written), "synced": False,
                  "implemented": False, "verified": False}
        return {**_result(plan, "pending_sync", bool(written)),
                "written": written, "outputs": plan.get("outputs") or [],
                "contradictions": plan.get("contradictions") or [],
                "missing": plan.get("missing") or [],
                "handoff_ready": False, "states": states,
                "to_sync": plan.get("to_sync") or [],
                "untouched": plan.get("untouched") or [],
                "session": session, "checks": None,
                "report": pending_sync_report(
                    plan, list(plan.get("to_sync") or []))}
    entry_path = str(plan.get("entry") or "")
    known_paths = _known_paths(plan)
    session, checks = checks_seam.after_write(
        session, module=str(session.get("module") or "") if session else "",
        path=entry_path, readback=readback, known_paths=known_paths)
    readback_map = {path: readback(path) for path in known_paths}
    verdict = verify_delivery(plan, readback_map)
    checks_ok = checks is None or checks.get("ok")
    if not written:
        states = {"adopted": True, "saved": False, "synced": False,
                  "implemented": False, "verified": False}
        return {**_result(plan, "pending_sync", False), "written": [],
                "outputs": plan.get("outputs") or [],
                "contradictions": plan.get("contradictions") or [],
                "missing": plan.get("missing") or [],
                "handoff_ready": False, "states": states,
                "to_sync": plan.get("to_sync") or [],
                "untouched": plan.get("untouched") or [],
                "session": session, "checks": checks,
                "report": pending_sync_report(
                    plan, list(plan.get("to_sync") or []))}
    if not checks_ok or not verdict["ok"]:
        failed = {"adopted": True, "saved": False, "synced": False,
                  "implemented": False, "verified": False}
        failures = list((checks or {}).get("failures") or []) + list(
            verdict.get("failures") or [])
        payload = {**(checks or {}), "ok": False, "failures": failures}
        session = _invalidate_failed_checks(
            session, known_paths, readback_map, failures,
            checks_ok=checks_ok)
        return {**_result(plan, "check_failed", False), "written": written,
                "outputs": plan.get("outputs") or [],
                "contradictions": [], "missing": [],
                "handoff_ready": False, "states": failed,
                "to_sync": plan.get("to_sync") or known_paths,
                "untouched": plan.get("untouched") or [],
                "session": session, "checks": payload,
                "report": check_failed_report(plan, written, payload)}
    completion = plan.get("pending_complete_file")
    if completion:
        # 待同步记录的完成标记在全部必要检查成功后写入;此刻之前失败,
        # 记录保持原有的待同步事实,不宣布已同步。
        outcome = commit_path(
            channel, readback, path=str(completion.get("path") or ""),
            content=completion.get("content") or "",
            expected_sha256=str(completion.get("expected_sha256")
                                or "absent"),
            note=f"{plan.get('game')} 完整设计交付"
                 f"（{completion.get('role')}）")
        if not outcome["ok"]:
            failed_status = ("denied" if outcome["outcome"] == "denied"
                             else outcome["outcome"])
            return {**_result(plan, failed_status, False),
                    "written": written, "path": outcome.get("path"),
                    "rule_stage": outcome.get("rule_stage"),
                    "report": failure_report(plan, outcome, written),
                    "session": checks_seam.invalidate_outcome(
                        session, outcome, detail="待同步记录的完成标记未更新"),
                    "checks": checks}
        written.append(str(completion.get("path") or ""))
        session = checks_seam.write_item(
            session, completion, label="交付写入")
    states = {"adopted": True, "saved": True,
              "synced": sync_authorized and not (plan.get("to_sync") or []),
              "implemented": False, "verified": False}
    return {**_result(plan, "saved", True), "written": written,
            "outputs": plan.get("outputs") or [],
            "contradictions": [], "missing": [],
            "handoff_ready": bool(states["synced"]),
            "states": states, "to_sync": plan.get("to_sync") or [],
            "untouched": plan.get("untouched") or [],
            "session": session, "checks": checks,
            "report": saved_report(plan, written, states)}


def verify_delivery(plan: dict[str, Any],
                    readback_map: dict[str, str | None]) -> dict[str, Any]:
    """回读核对:四类交付物齐备、入口可定位、现行规则位置未重复、状态准确。"""

    failures: list[str] = []
    outputs = plan.get("outputs") or []
    for item in outputs:
        path = str(item.get("path") or "")
        if readback_map.get(path) is None:
            failures.append(f"回读目标不存在:{path}")
    if not outputs:
        failures.append("没有四类交付物")
    entry = str(plan.get("entry") or "")
    design = readback_map.get(entry)
    if design is None:
        failures.append("游戏设计主文档入口不存在")
    elif "## 交付入口（四类交付物）" not in design:
        failures.append("主文档未提供四类交付物入口")
    else:
        for item in outputs:
            role = str(item.get("role") or "")
            if role not in design:
                failures.append(f"主文档缺少交付物定位:{role}")
    if plan.get("contradictions"):
        failures.append("存在未处理的跨模块矛盾,不得判为已交付")
    if plan.get("missing"):
        failures.append("存在阻断交接的关键缺口,不得判为已交付")
    required = {ROLE_DESIGN, ROLE_SPECS, ROLE_CONTENT, ROLE_VERSION}
    have = {str(item.get("role") or "") for item in outputs
            if item.get("path")}
    for role in required - have:
        failures.append(f"缺少交付类别:{role}")
    locatable = {path for path, text in readback_map.items() if text}
    # 声明未改动不证明仍存在:按实际回读核对,外部删除的引用目标算断链。
    locatable.update(str(path) for path in (plan.get("untouched") or [])
                     if readback_map.get(str(path)))
    for item in plan.get("files") or []:
        path = str(item.get("path") or "")
        text = readback_map.get(path)
        if not text:
            continue
        for ref in references(text):
            if ref not in locatable:
                failures.append(f"新改引用不可定位:{ref}")
    return {"ok": not failures, "failures": failures, "entry": entry}


def pending_record_path(meta: dict[str, Any]) -> str | None:
    """缺同步授权时留下的待同步记录位置,供读取、续写与完成状态更新共用。"""

    records = str((meta.get("doc_map") or {}).get("records") or "").rstrip("/")
    if not records:
        return None
    return f"{records}/delivery-pending.md"


def _pending_sync_file(existing: dict[str, str | None], meta: dict[str, Any],
                       to_sync: list[str]) -> dict[str, Any] | None:
    """缺同步授权时留下可恢复的待同步记录,不原位替换当前有效设计。"""

    path = pending_record_path(meta)
    if not path:
        return None
    pending = "、".join(to_sync) or "当前有效设计"
    content = (
        f"# 待同步完整设计（{meta.get('date') or ''}）\n\n"
        "缺同步授权,未改写当前有效设计。获准同步前失效规则、引用和验收"
        "要求不得退出当前有效版本。\n\n"
        f"待同步：{pending}\n")
    return {"path": path, "role": "待同步记录", "content": content,
            "expected_sha256": sha256_text(existing.get(path))}


def _completed_pending_file(existing: dict[str, str | None],
                            meta: dict[str, Any]) -> dict[str, Any] | None:
    """获准同步后更新既有待同步记录,避免旧状态继续声明缺授权。"""

    path = pending_record_path(meta)
    if not path or existing.get(path) is None:
        return None
    content = (
        f"# 完整设计同步记录（{meta.get('date') or ''}）\n\n"
        "已获准同步并写入当前有效设计。此前留下的待办已经完成。\n\n"
        "已同步：当前有效设计\n")
    return {"path": path, "role": "待同步记录", "content": content,
            "expected_sha256": sha256_text(existing.get(path))}


def _known_paths(plan: dict[str, Any]) -> list[str]:
    """写入后核对用的可定位路径:本次文件、四类交付物与声明未改动项。"""

    paths: list[str] = []
    for item in (plan.get("files") or []) + (plan.get("outputs") or []):
        path = str(item.get("path") or "")
        if path and path not in paths:
            paths.append(path)
    for path in plan.get("untouched") or []:
        if path and path not in paths:
            paths.append(str(path))
    entry = str(plan.get("entry") or "")
    if entry and entry not in paths:
        paths.append(entry)
    return paths


def _invalidate_failed_checks(
        session: dict[str, Any] | None, known_paths: list[str],
        readback_map: dict[str, str | None], failures: list[str],
        *, checks_ok: bool) -> dict[str, Any] | None:
    """交付核验失败 → 作废依赖失败对象的旧检查结果;无关结果保留。

    失败对象是回读缺失或新改引用不可定位的路径(断链);没有可定位对象
    时按证据不足作废,读取结果仍保留,重查只做受影响检查。
    """

    if session is None:
        return None
    failed_paths = [path for path in known_paths
                    if readback_map.get(path) is None]
    for failure in failures:
        if not failure.startswith("新改引用不可定位:"):
            continue
        failed_paths.extend(item for item
                            in failure.split(":", 1)[1].split("、") if item)
    failed_paths = sorted(set(failed_paths))
    if failed_paths:
        return checks_seam.invalidate(
            session, "broken_link", paths=failed_paths,
            detail="交付核验失败:回读目标缺失或新改引用不可定位")["session"]
    detail = "交付核验失败:" + (
        "保存后检查未通过" if not checks_ok else "；".join(failures))
    return checks_seam.invalidate(
        session, "insufficient_evidence", detail=detail)["session"]


def _result(plan: dict[str, Any], status: str, saved: bool) -> dict[str, Any]:
    return {
        "op": plan.get("op"), "status": status, "saved": saved,
        "game": plan.get("game"), "entry": plan.get("entry"),
        "handoff_ready": saved,
    }


__all__ = ["plan_delivery", "apply_delivery", "verify_delivery",
           "pending_record_path"]

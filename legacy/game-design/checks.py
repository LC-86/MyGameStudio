#!/usr/bin/env python3
"""Game-Design 检查时机与复用接缝(统一设计问答框架票 08)。

公开 interface:
  begin(context) -> dict
  plan_reads(session, candidates) -> dict
  record_read(session, path, text, *, module, purpose, call) -> dict
  record_write(session, paths, call, *, contents=None) -> dict
  before_save(session, *, reply, shown, adopted, history, scope, path,
              target) -> dict
  after_save(session, *, recorded, module, entries, pending, content,
             target_version, known_paths) -> dict
  after_write(session, *, module, path, readback, ...) -> (session, checks)
  converge(session, plan) -> dict
  invalidate(session, reason, *, paths, detail) -> dict
  invalidate_outcome(session, outcome, *, detail) -> session
  reuse(session, key) -> dict | None
  remember(session, key, value, *, depends_on) -> dict
  answers_from_reply(reply, shown) -> dict

按规格「读取与检查时机」统一两条设计流程(新设计成稿与已有设计变更/删减)的
读取、保存与收敛检查:开始或恢复时核对模式、项目阶段、目标、授权、相关决定
与未决项,从现有入口定位资料,只展开当前模块与必要依赖;每轮保存前核对实际
答案、采纳范围、来源、矛盾、当前可写范围与目标版本,保存后回读核对本轮完整、
无重复、历史、同步状态与新改引用;连续多轮只新增本模块决定且未改核心基线时
不重跑全项目基线、全部链接或无关远端检查,模块收敛并获准同步后按真实影响做
一次统一核对。已读资料与已通过检查的输入未变且仍在适用范围时复用结果,复用
依据是本次可核对的内容身份(路径定位 + SHA-256 指纹)与适用范围,不能仅以
修改时间判断有效;新会话只复用可核验的既有读取结果,否则补读补检。

失效触发:外部修改引用目标、撤销授权、版本冲突、写入失败、断链或证据不足时
作废相关旧结果(``invalidate``),只重新读取和检查受影响部分,无关模块不被
全量重查。每次写入的权限和版本校验仍由受控通道逐次执行(``gate_commit``),
本接缝只对读取理解与已通过检查结果做复用,不缓存也不跳过写入校验。检查台账
(``check_evidence`` 的 ``evidence``/``ledger``/``measure``)按实际事件记录
读取、写入、检查与调用:一条调用内部的多次文件操作仍分别计数,不通过合并调用
制造步骤减少。不新增独立缓存服务、后台监控或持久化系统——会话就是全部状态。

本 module 不写入项目文件、不接触受控通道;``decisions``/``spec_draft``/
``full_design``/``change_flow``/``removal`` 通过可选 ``session`` 参数接入,
不传时保持原有行为不变。状态基元与判定规则见 ``check_state.py``,证据与报告
见 ``check_evidence.py``。
"""

from __future__ import annotations

from typing import Any, Callable, Iterable

from check_state import (
    CONVERGE_SCOPE, GLOBAL_SCOPE, INVALIDATION, SKIPPED_GLOBAL_CHECK,
    answers_from_reply, baseline_changed, begin_gaps, count, entry_failures,
    fingerprint, impact_items, in_scope, log, paths, precheck_signature,
    presave_gaps, public, reference_failures, result_affected,
    scope_path_keys, scope_paths, snapshot,
)
from check_state import parsed_module_record as parse_record
from decision_records import empty_parse, sha256_text

__all__ = [
    "answers_from_reply", "after_save", "after_write", "begin",
    "before_save", "converge", "converge_plan", "invalidate",
    "invalidate_blocked", "invalidate_outcome", "plan_reads", "record_read",
    "record_write", "remember", "reuse", "write_item",
]


def begin(context: dict[str, Any]) -> dict[str, Any]:
    """开始或恢复当前模块:核对模式、阶段、目标、授权、决定与未决项。

    缺口只在当前模块依赖相关的项缺失时成立;无关模块不进入核对范围。
    新会话没有可核验的既有读取结果,因此不预置任何复用,由 ``plan_reads``
    按内容身份补读。
    """

    context = dict(context or {})
    authorization = dict(context.get("authorization") or {})
    session: dict[str, Any] = {
        "mode": str(context.get("mode") or ""),
        "stage": str(context.get("stage") or ""),
        "goal": str(context.get("goal") or ""),
        "module": str(context.get("module") or ""),
        "deps": [public(item) for item in (context.get("deps") or [])],
        "entry": str(context.get("entry") or ""),
        "authorization": authorization,
        "scope": str(context.get("scope_hint") or ""),
        "baseline": {str(path): fingerprint(value)
                     for path, value in (context.get("baseline")
                                         or {}).items()},
        "context_identity": sha256_text(str(context.get("context_id")
                                            or context.get("session_id")
                                            or "new")),
        "target_version": None,
        "reads": {},
        "results": [],
        "round_checks": [],
        "evidence": [],
        "ledger": [],
        "converged": False,
    }
    gaps, pending, decisions = begin_gaps(context)
    detail = (f"{session['mode']}/{session['module']};"
              f"已采纳 {len(decisions)} 项,未决 {len(pending)} 项")
    if gaps:
        detail += "；" + "；".join(gaps)
    log(session, {"check": "开始或恢复:核对模式、阶段、目标、授权、决定"
                           "与未决项", "timing": "begin",
                  "scope": "当前模块", "status": "gap" if gaps else "ok",
                  "detail": detail})
    return {"op": "begin", "ok": not gaps, "session": public(session),
            "gaps": gaps, "decisions": decisions, "pending": pending}


def plan_reads(session: dict[str, Any], candidates: Iterable[dict]) -> dict:
    """按当前模块与必要依赖给出读取计划:未变复用,变化重读,无关不展开。

    复用依据是本次会话已核对的路径 + 内容指纹,不是修改时间;新会话没有
    可核验的既有读取结果时补读。内容身份与已读不同(含基准声明不一致)时
    只重读该资料。
    """

    state = snapshot(session)
    to_read: list[dict[str, Any]] = []
    reuse: list[dict[str, Any]] = []
    excluded: list[dict[str, Any]] = []
    for raw in candidates or []:
        item = dict(raw)
        path = str(item.get("path") or "")
        entry = {"path": path, "purpose": str(item.get("purpose") or "")}
        if not in_scope(state, item):
            excluded.append({**entry, "reason": "与当前模块和必要依赖无关"})
            continue
        marked = fingerprint(item.get("sha256"))
        if marked == "absent":
            to_read.append({**entry, "reason": "缺少可核对的内容身份,补读"})
            continue
        known = (state.get("reads") or {}).get(path)
        if known is not None and known.get("sha256") == marked:
            reuse.append({**entry, "sha256": marked, "scope": CONVERGE_SCOPE})
            continue
        if known is not None:
            reason = "内容身份变化,只重读受影响资料"
        elif baseline_changed(path, marked, state):
            reason = "外部修改了引用目标,重新读取实际内容"
        else:
            reason = "新会话没有可核验的既有读取结果,补读"
        to_read.append({**entry, "reason": reason})
    if to_read:
        status = "ok"
        detail = "本轮读取:" + "、".join(item["path"] for item in to_read)
    else:
        status = "reuse"
        detail = ("输入未变,复用已读资料:"
                  + ("、".join(item["path"] for item in reuse) or "无"))
    log(state, {"check": "读取计划（当前模块与必要依赖）", "timing": "read",
                "scope": "当前模块", "status": status, "detail": detail,
                "reused": [item["path"] for item in reuse]})
    return {"op": "reads", "session": public(state), "to_read": to_read,
            "reuse": reuse, "excluded": excluded, "report": detail}


def record_read(session: dict[str, Any], path: str, text: str, *,
                module: str, purpose: str, call: str,
                sha256: str | None = None) -> dict[str, Any]:
    """记录一次实际读取:身份(路径 + 指纹)、范围与内容规模。"""

    state = snapshot(session)
    marked = sha256 or sha256_text(text)
    state["reads"] = {
        **(state.get("reads") or {}),
        str(path): {"path": str(path), "purpose": str(purpose),
                    "module": str(module), "sha256": marked,
                    "bytes": len(text or ""), "call": str(call),
                    "scope": CONVERGE_SCOPE},
    }
    log(state, {"check": "资料读取", "timing": "read", "scope": "当前模块",
                "status": "ok",
                "detail": f"{path}（{len(text or '')} 字符,"
                          f"{marked[:12]}）"})
    count(state, "reads", [str(path)], call)
    return {"op": "read", "session": public(state), "path": str(path),
            "sha256": marked, "bytes": len(text or "")}


def record_write(session: dict[str, Any], paths: Iterable[str],
                 call: str,
                 *, contents: dict[str, str] | None = None) -> dict[str, Any]:
    """记录一次实际写入:一个调用内的多个文件仍分别计数。

    ``contents`` 给出本次写入的实际文本时,同步更新这些目标的读取身份——
    写入者知道新内容,后续读取计划据此复用而不是误判为外部变化。
    """

    state = snapshot(session)
    targets = [str(item) for item in paths]
    count(state, "writes", targets, call)
    for path, text in (contents or {}).items():
        state["reads"] = {
            **(state.get("reads") or {}),
            str(path): {"path": str(path), "purpose": "written",
                        "module": str(state.get("module") or ""),
                        "sha256": sha256_text(text), "bytes": len(text or ""),
                        "call": str(call), "scope": CONVERGE_SCOPE},
        }
    return {"op": "write", "session": public(state), "paths": targets}


def before_save(session: dict[str, Any], *, reply: str,
                shown: Iterable[str] | None = None,
                adopted: dict[str, Any] | None = None,
                history: dict[str, Any] | None = None,
                scope: Iterable[str] | None = None,
                path: str | None = None,
                target: str | None = None) -> dict[str, Any]:
    """保存前核对:实际答案与采纳范围、来源、矛盾、可写范围及目标版本。

    ``scope`` 给出当前可写范围时核对 ``path`` 是否越界;范围未知时由受控
    通道在每次写入时逐次核对,不缓存、不跳过。``target`` 是目标当前内容,
    与上一轮实际写入不一致(外部修改了引用目标)时作废相关旧结果并只重读
    受影响部分。同一输入(回复、采纳、可写范围、目标身份与历史)的核对
    已通过时直接复用上次结论:输入未变不做重复检查,输入一变立即重做。
    """

    state = snapshot(session)
    adopted = dict(adopted or {})
    answers = answers_from_reply(reply, shown)
    scope_set = {str(item) for item in (scope or [])}
    marked = fingerprint(target)
    signature = precheck_signature(answers, adopted, scope_set, marked, path,
                                   history or {})
    cached = reuse(state, "保存前核对", signature=signature)
    if cached is not None:
        log(state, {"check": "保存前核对（实际答案、采纳范围、来源、矛盾、"
                             "当前可写范围、目标版本）", "timing": "before_save",
                    "scope": "当前模块", "status": "ok",
                    "detail": "输入未变,复用上次核对结论（内容身份一致）",
                    "reused": ["保存前核对"]})
        return {"op": "before_save", "ok": True, "gaps": [], "stale": [],
                "reused": True, "timing": "before_save",
                "session": public(state),
                "report": "输入未变,复用已通过的保存前核对结论"}
    gaps, stale = presave_gaps(state, answers, adopted, history or {},
                               scope_set, path, marked)
    state["precheck"] = {"answers": sorted(answers),
                         "adopted": sorted(adopted),
                         "scope": sorted(scope_set), "target": marked}
    detail = "；".join(gaps) or (
        f"本轮采纳 {len(adopted)} 项,目标版本一致")
    if not scope_set:
        detail += ";可写范围未在此提供,由受控通道逐次核对（不缓存）"
    log(state, {"check": "保存前核对（实际答案、采纳范围、来源、矛盾、"
                         "当前可写范围、目标版本）", "timing": "before_save",
                "scope": "当前模块", "status": "gap" if gaps else "ok",
                "detail": detail})
    remembered = remember(state, "保存前核对",
                          {"ok": not gaps, "gaps": gaps},
                          depends_on=_depends_of(state, path),
                          signature=signature)
    state = remembered["session"]
    if stale:
        log(state, {"check": "作废旧结果（外部修改了引用目标）",
                    "timing": "before_save", "scope": "受影响部分",
                    "status": "stale",
                    "detail": "；".join(stale) + ";无关模块不重查"})
    return {"op": "before_save", "ok": not gaps, "gaps": gaps, "stale": stale,
            "reused": False, "timing": "before_save",
            "session": public(state), "report": detail}


def after_save(session: dict[str, Any], *, recorded: str | None, module: str,
               entries: Iterable[dict] | None = None,
               pending: Iterable[dict] | None = None,
               content: str | None = None,
               target_version: str | None = None,
               known_paths: Iterable[str] | None = None,
               history: Iterable[Any] | None = None) -> dict[str, Any]:
    """保存后回读:本轮完整、无重复、历史、同步状态与新改引用。

    本轮未改变核心基线时,不因新增决定重跑全项目基线、全部链接或远端任务
    检查;这些跳过项如实记入台账。``known_paths`` 给出本次写入后可定位的
    路径(如交付文件本身),用于核对新改引用;``history`` 给出必须仍在记录
    中的旧内容(改口与被替代项),丢失即回读缺口。
    """

    state = snapshot(session)
    entries = [dict(item) for item in (entries or [])]
    failures: list[str] = []
    if recorded is None:
        failures.append("回读目标不存在")
        parsed = empty_parse()
    else:
        parsed = parse_record(recorded, str(module))
        failures.extend(entry_failures(recorded, parsed, entries, pending,
                                       history))
        if content is not None and recorded != content:
            failures.append("回读内容与计划内容不一致")
    failures.extend(reference_failures(content or recorded or "", state,
                                       module, known_paths))
    detail = "；".join(failures) or (
        f"本轮完整、无重复;历史 {parsed['rounds']} 轮,"
        f"待同步 {len(parsed['pending_qids'])} 项")
    log(state, {"check": "保存后回读（本轮完整性、重复、历史、同步状态、"
                         "新改引用）", "timing": "after_save",
                "scope": "当前模块", "status": "gap" if failures else "ok",
                "detail": detail})
    skipped: list[str] = []
    if not failures:
        skipped = [SKIPPED_GLOBAL_CHECK, "无关远端任务检查"]
        log(state, {"check": SKIPPED_GLOBAL_CHECK, "timing": "after_save",
                    "scope": GLOBAL_SCOPE, "status": "skipped",
                    "detail": "本轮只新增本模块决定且未改核心基线,"
                              "不重跑无关的全局检查"})
    state["target_version"] = target_version or fingerprint(recorded)
    state["round_checks"] = [*state.get("round_checks", []),
                             {"timing": "after_save", "ok": not failures,
                              "round": state.get("round")}]
    return {"op": "after_save", "ok": not failures, "failures": failures,
            "timing": "after_save", "skipped": skipped,
            "session": public(state), "report": detail}


def after_write(session: dict[str, Any] | None, *, module: str, path: str,
                readback: Callable[[str], str | None],
                entries: Iterable[dict] | None = None,
                pending: Iterable[dict] | None = None,
                content: str | None = None,
                known_paths: Iterable[str] | None = None,
                history: Iterable[Any] | None = None
                ) -> tuple[dict[str, Any] | None, dict[str, Any] | None]:
    """落盘后回读核对(各流程共用的保存后时机适配)。

    回读不到内容或发现缺口时,按写入失败作废相关旧结果并只重查受影响部分;
    不传 ``session`` 时返回 ``(None, None)``,调用方保持原有行为不变。
    """

    if session is None:
        return None, None
    recorded = readback(path)
    checks = after_save(session, recorded=recorded, module=module,
                        entries=entries, pending=pending, content=content,
                        known_paths=known_paths, history=history)
    extra = _written_reference_failures(
        checks["session"], readback, module, path, recorded, known_paths)
    already = set(checks.get("failures") or [])
    extra = [item for item in extra if item not in already]
    if extra:
        checks["ok"] = False
        checks["failures"] = list(checks.get("failures") or []) + extra
    if not checks["ok"]:
        checks["session"] = invalidate(
            checks["session"], "write_failed", paths=[str(path)],
            detail="落盘后回读发现缺口:" + "；".join(checks["failures"])
        )["session"]
    return checks["session"], checks


def _written_reference_failures(session: dict[str, Any],
                                readback: Callable[[str], str | None],
                                module: str, path: str, recorded: str | None,
                                known_paths: Iterable[str] | None) -> list[str]:
    """写入后的新改引用:核对规格与记录等新写正文,不把既有基线旧引用当新改。"""

    state = snapshot(session)
    seen: set[str] = set()
    failures: list[str] = []
    paths = [str(item) for item in (known_paths or [])] or [path]
    texts = {item: (recorded if item == path else readback(item)) or ""
             for item in paths}
    # 可定位性按实际回读核对:声明未改动或本次不改写的文件也可能已被外部删除。
    locatable = [item for item in paths if texts[item]]
    for item in paths:
        if item.endswith("GAME_DESIGN.md"):
            continue
        for failure in reference_failures(texts[item], state, module, locatable):
            if failure in seen:
                continue
            seen.add(failure)
            failures.append(failure)
    return failures


def converge(session: dict[str, Any], plan: dict[str, Any]) -> dict[str, Any]:
    """模块收敛统一核对:解析待同步决定,按真实影响确定一次核对范围。

    跨模块或全局影响时才扩大到对应范围;否则一次统一核对,不再逐项重跑。
    既有必需检查(规格、基线、指纹、相关链接)仍执行。
    """

    state = snapshot(session)
    proposal = dict(plan or {})
    module = str(proposal.get("module") or state.get("module") or "")
    parsed = empty_parse()
    for text in (proposal.get("records") or {}).values():
        if not text:
            continue
        found = parse_record(text, module)
        if found["found"]:
            parsed = found
    declared = [str(item) for item in (proposal.get("to_sync") or [])]
    to_sync = declared or sorted(
        qid for qid, item in parsed["decisions"].items()
        if not item.get("synced") and not item.get("superseded"))
    extra = sorted({str(item) for item in (proposal.get("affected") or [])})
    changed = [str(path) for path in (proposal.get("changed_paths")
                                      or paths(proposal.get("files")))]
    modules = sorted({str(item.get("module") or "")
                      for item in impact_items(proposal)
                      if isinstance(item, dict) and item.get("module")})
    cross = sorted({name for name in modules if name and name != module}
                   | set(extra))
    if proposal.get("global_impact"):
        scope = GLOBAL_SCOPE
    elif cross:
        scope = "跨模块"
    else:
        scope = "当前模块"
    affected = sorted(set(extra) | set(changed)) \
        if scope != "当前模块" else []
    state["scope"] = scope
    state["converged"] = True
    detail = (f"待同步决定:{'、'.join(to_sync) or '无'};核对范围:{scope}")
    if affected:
        detail += ";受影响:" + "、".join(affected)
    log(state, {"check": "模块收敛统一核对（未同步决定、规格与引用）",
                "timing": "converge", "scope": scope, "status": "ok",
                "detail": detail})
    return {"op": "converge", "module": module, "to_sync": to_sync,
            "scope": scope, "affected": affected,
            "session": public(state), "report": detail}


def invalidate(session: dict[str, Any], reason: str, *,
               paths: Iterable[str] | None = None,
               detail: str = "") -> dict[str, Any]:
    """作废相关旧结果:只影响相关路径(缺省为当前模块),无关模块不动。

    授权撤销与证据不足使所有已通过检查结果失效(它们都以可写或该证据为
    前提),但读取结果保留——资料本身未变,不因局部失败全量重查;其余触发
    只作废给定路径的读取与依赖这些输入的检查结果。
    """

    state = snapshot(session)
    raw_reason = str(reason or "")
    label = INVALIDATION.get(raw_reason, raw_reason or "状态变化")
    affected = [str(item) for item in
                (paths if paths is not None else scope_paths(state))]
    stale = [item for item in affected if item in (state.get("reads") or {})]
    for path in stale:
        state["reads"] = {key: item for key, item in state["reads"].items()
                          if key != path}
    if raw_reason in {"revoked_authorization", "insufficient_evidence"}:
        state["results"] = [{**item, "stale": True}
                            for item in (state.get("results") or [])]
    else:
        state["results"] = [
            {**item, "stale": True} if result_affected(item, affected)
            else item for item in (state.get("results") or [])]
    state["reused"] = False
    if raw_reason in {"external_change", "version_conflict", "write_failed"}:
        state["target_version"] = None
    if raw_reason == "revoked_authorization":
        state["authorization"] = {
            **dict(state.get("authorization") or {}), "write": False,
            "sync": False}
    parts = list(filter(None, [detail] + stale))
    log(state, {"check": f"作废旧结果（{label}）", "timing": "invalidate",
                "scope": "受影响部分" if stale else "当前模块",
                "status": "stale",
                "detail": "；".join(parts) or "无关模块不受影响"})
    return {"op": "invalidate", "reason": raw_reason, "label": label,
            "stale": stale, "affected": affected,
            "session": public(state),
            "report": f"{label}:作废 {len(stale)} 项旧读取结果,"
                      f"只重读与重查受影响部分"}


def invalidate_outcome(session: dict[str, Any] | None,
                       outcome: dict[str, Any], *,
                       detail: str = "") -> dict[str, Any] | None:
    """通道提交失败/被拒 → 作废相关旧结果(各流程共用同一映射)。"""

    if session is None:
        return None
    raw = str(outcome.get("outcome") or "")
    reason = ("version_conflict" if raw == "conflict"
              else "revoked_authorization"
              if outcome.get("denied_at") == "scope" else "write_failed")
    path = str(outcome.get("path") or "")
    return invalidate(session, reason, paths=[path] if path else None,
                      detail=detail or str(outcome.get("reason") or ""))[
                          "session"]


def _depends_of(state: dict[str, Any], path: str | None) -> list[str]:
    """复用结果的依赖集合:写入目标已知时以它为准,否则用当前模块资料。"""

    if path and str(path) in (state.get("reads") or {}):
        return [str(path)]
    return scope_path_keys(state)


def invalidate_blocked(session: dict[str, Any] | None, result: dict[str, Any],
                       *, path: str = "", status: str = "",
                       detail: str = "") -> dict[str, Any] | None:
    """保存未成立时的失效适配:按触发原因作废相关旧结果。

    只对「证据不足、授权不可用、写入未确认」适用;``no_new``(本轮没有
    新增内容)不改变任何旧结果,原样透传会话。
    """

    if session is None:
        return None
    if status == "no_new":
        return session
    if status == "invalid":
        reason = "insufficient_evidence"
    elif status in {"read_only", "unauthorized", "denied"}:
        reason = "revoked_authorization"
    else:
        reason = "write_failed"
    updated = invalidate(session, reason, paths=[path] if path else None,
                         detail=detail or str(result.get("reason") or ""))
    return updated["session"]


def converge_plan(session: dict[str, Any] | None, plan: dict[str, Any],
                  *, module: str = "",
                  impact: dict[str, Any] | None = None
                  ) -> dict[str, Any] | None:
    """落盘前的收敛统一核对适配:无会话时返回 None,调用方行为不变。"""

    if session is None:
        return None
    proposal = {"module": module or str(session.get("module") or ""),
                "files": plan.get("files") or [],
                "changed_paths": plan.get("changed_paths") or [],
                "records": plan.get("records") or {},
                "to_sync": plan.get("to_sync") or [],
                "impact": impact if impact is not None
                else plan.get("impact") or {}}
    return converge(session, proposal)["session"]


def write_item(session: dict[str, Any] | None, item: dict[str, Any],
               *, label: str) -> dict[str, Any] | None:
    """逐文件写入计数与身份更新的共用适配(无会话时返回 None)。"""

    if session is None:
        return None
    path = str(item.get("path") or "")
    return record_write(
        session, [path], call=f"{label} {path}",
        contents={path: str(item.get("content") or "")})["session"]


def reuse(session: dict[str, Any], key: str,
          *, signature: str | None = None) -> dict[str, Any] | None:
    """取一个仍有效的已通过检查结果;失效或输入变化后返回 None。

    有效性按登记时声明的依赖路径核对:依赖的读取结果仍在且内容身份未变,
    且未被 ``invalidate`` 作废。``signature`` 给出本次输入的内容身份时,
    还必须与登记时一致才算输入未变。
    """

    state = session or {}
    for item in (state.get("results") or []):
        if str(item.get("key") or "") != str(key):
            continue
        if item.get("stale"):
            return None
        if signature is not None and item.get("signature") != signature:
            return None
        for path in item.get("depends_on") or []:
            known = (state.get("reads") or {}).get(str(path))
            if known is None:
                return None
            if item.get("inputs", {}).get(str(path)) != known.get("sha256"):
                return None
        return dict(item)
    return None


def remember(session: dict[str, Any], key: str, value: Any, *,
             depends_on: Iterable[str] | None = None,
             signature: str | None = None) -> dict[str, Any]:
    """登记一个已通过检查结果及其输入身份,供输入未变时复用。

    ``depends_on`` 缺省为当前已读资料;``signature`` 是本次输入的完整内容
    身份(如回复 + 采纳 + 范围 + 目标版本):依赖读取未变、且签名一致时,
    该结果可直接复用而不重做检查。签名一变化立即失效,不按时间判断。
    """

    state = snapshot(session)
    dep_paths = sorted({str(item) for item in
                        (depends_on if depends_on is not None
                         else scope_path_keys(state))})
    inputs = {path: (state.get("reads") or {}).get(path, {}).get("sha256")
              for path in dep_paths}
    state["results"] = [
        entry for entry in (state.get("results") or [])
        if str(entry.get("key") or "") != str(key)]
    state["results"].append({"key": str(key), "value": public(value),
                             "depends_on": dep_paths, "inputs": inputs,
                             "signature": signature, "stale": False})
    log(state, {"check": f"登记可复用检查结果:{key}", "timing": "reuse",
                "scope": "当前模块", "status": "ok",
                "detail": "依赖未变且仍在适用范围时复用"})
    return {"op": "remember", "key": str(key), "depends_on": dep_paths,
            "signature": signature, "session": public(state)}

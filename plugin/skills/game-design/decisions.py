#!/usr/bin/env python3
"""Game-Design 决定即时保存与恢复接缝(统一设计问答框架票 03)。

公开 interface:
  plan_save(record_text, round_result, meta) -> dict
  plan_sync(record_text, meta) -> dict
  apply_save(plan, channel, readback) -> dict
  verify_saved(plan, readback_text) -> dict
  restore_from_records(texts, module) -> dict

``plan_save`` 把 ``rounds.run_round`` 的本轮结果整理成本模块的最小决定记录
(问题关联、采纳内容、决定者与日期、用户回复与建议出处、影响、未决项、
基线同步状态),并给出目标版本与写入前核对;``apply_save`` 经受控通道提交
并回读核对,只按实际结果报告状态;``restore_from_records`` 从实际记录恢复
已定、未决与待同步内容,供下一轮沿用而不重问。本接缝不自行落盘、不缓存
权限或版本校验,也不以助手建议冒充用户决定。记录文本格式见
``decision_records.py``;命令行入口见 ``decisions_cli.py``。
"""

from __future__ import annotations

from typing import Any, Callable

import decision_mapping as mapping
from decision_records import (
    SYNC_PENDING, apply_sync, compose, decision_head, empty_parse,
    head_counts, line_counts, mark_superseded, parse_record, round_section,
    sha256_text,
)


def plan_save(record_text: str | None,
              round_result: dict[str, Any],
              meta: dict[str, Any]) -> dict[str, Any]:
    """整理本轮最小决定记录;不写入,只给出内容与写入前核对。"""

    record_path = str(meta.get("record_path") or "")
    module = str(meta.get("module") or round_result.get("module") or "")
    reply = str(meta.get("reply") or round_result.get("user_reply") or "")
    round_no = int(meta.get("round") or 0)
    date = str(meta.get("date") or "")
    authorization = dict(meta.get("authorization") or {})
    catalog = mapping.catalog_index(round_result)
    existing = parse_record(record_text, module) if record_text else empty_parse()
    base = _save_base(record_text, record_path, module, round_no, date, reply,
                      meta, authorization, existing)
    if not record_path:
        return {**base, "status": "unauthorized", "saved": False,
                "next_round_ready": False,
                "reason": "缺少记录位置,无法定位本模块记录"}
    if not authorization.get("write"):
        return {**base, "status": "read_only", "saved": False,
                "next_round_ready": False,
                "entries": [], "duplicates": [], "superseded": [],
                "pending": mapping.pending_items(round_result, catalog),
                "adopted": mapping.raw_adopted(round_result),
                "reason": "只读讨论:未获写入授权,本轮决定保留待授权后保存"}

    entries, duplicates, protected, superseded = _save_entries(
        round_result, catalog, existing, round_no)
    pending = mapping.pending_items(round_result, catalog)
    new_pending = [item for item in pending
                   if item["qid"] not in existing["pending_qids"]]
    if not entries and not new_pending:
        return {**base, **_skip_result(record_text, round_result, duplicates,
                                      protected, pending)}
    section = round_section(
        module, round_no, date, str(meta.get("decider") or "开发者"), reply,
        entries, pending)
    content = compose(module, mark_superseded(record_text, superseded, round_no,
                                              date, entries), section)
    return {**base, "status": "planned", "saved": False, "content": content,
            "entries": entries, "duplicates": duplicates,
            "protected": protected, "superseded": superseded,
            "pending": pending,
            "adopted": mapping.raw_adopted(round_result),
            "note": f"保存第 {round_no} 轮决定记录（{module}）"}


def _save_base(record_text: str | None, record_path: str, module: str,
               round_no: int, date: str, reply: str, meta: dict[str, Any],
               authorization: dict[str, Any],
               existing: dict[str, Any]) -> dict[str, Any]:
    """计划公共字段:授权、目标版本与相关决定历史的写入前核对。"""

    return {
        "op": "save",
        "record_path": record_path,
        "module": module,
        "round": round_no,
        "date": date,
        "reply": reply,
        "evidence": dict(meta.get("evidence") or {}),
        "expected_sha256": sha256_text(record_text),
        "precheck": {
            "authorization": "write" if authorization.get("write") else "none",
            "target_version": sha256_text(record_text),
            "history": {
                "rounds": existing["rounds"],
                "decisions": len(existing["decisions"]),
                "pending": len(existing["pending"]),
                "heads": head_counts(existing),
            },
        },
    }


def _save_entries(round_result: dict[str, Any],
                  catalog: dict[str, dict[str, Any]],
                  existing: dict[str, Any],
                  round_no: int) -> tuple[list[dict[str, Any]],
                                          list[dict[str, Any]],
                                          list[dict[str, Any]],
                                          list[dict[str, Any]]]:
    """本轮采纳 → 记录条目;重复、被更高轮次取代与替代关系分别列出。"""

    dependents = mapping.dependents(round_result, catalog)
    entries: list[dict[str, Any]] = []
    duplicates: list[dict[str, Any]] = []
    protected: list[dict[str, Any]] = []
    superseded: list[dict[str, Any]] = []
    for qid, item in (round_result.get("adopted") or {}).items():
        source = str(item.get("source") or "user")
        raw_value = item.get("value")
        if source == "prior" or raw_value in (None, ""):
            continue
        question = catalog.get(str(qid), {})
        title = str(question.get("title") or qid)
        rendered = mapping.render_value(raw_value, question)
        old = (existing["decisions"].get(str(qid)) or {})
        if old and not old.get("superseded"):
            old_round = old.get("round")
            if isinstance(old_round, int) and round_no and old_round > round_no:
                protected.append({
                    "qid": str(qid), "title": title, "value": old.get("value"),
                    "round": old_round, "answer": rendered,
                    "note": f"已有更晚（第 {old_round} 轮）的决定,不覆盖"})
                continue
            if old.get("value") == rendered:
                duplicates.append({
                    "qid": str(qid), "title": title, "value": rendered,
                    "note": f"已有相同决定（第 {old_round or '?'} 轮）"})
                continue
        entry = {
            "qid": str(qid), "title": title, "value": rendered,
            "source": source,
            "source_label": mapping.source_label(source, round_no),
            "provenance": mapping.provenance(source, question, raw_value),
            "impact": mapping.impact(question, dependents.get(str(qid)) or []),
            "sync": SYNC_PENDING,
        }
        if old and not old.get("superseded"):
            entry["replacement"] = {"value": old.get("value"),
                                   "round": old.get("round")}
            superseded.append({"qid": str(qid), "value": old.get("value"),
                               "round": old.get("round")})
        entries.append(entry)
    return entries, duplicates, protected, superseded


def _skip_result(record_text: str | None,
                 round_result: dict[str, Any],
                 duplicates: list[dict[str, Any]],
                 protected: list[dict[str, Any]],
                 pending: list[dict[str, str]]) -> dict[str, Any]:
    """无新增内容:如实区分重复、被后续修改取代与没有新决定三种原因。"""

    if protected:
        reason = "本轮答案已被后续轮次的用户修改取代,不覆盖后来的用户修改"
    elif duplicates:
        reason = "本轮决定与已有记录一致,未重复创建"
    else:
        reason = "本轮没有新增可保存的决定"
    return {"status": "no_new", "saved": False, "next_round_ready": False,
            "content": record_text or "", "entries": [],
            "duplicates": duplicates, "protected": protected,
            "superseded": [], "pending": pending,
            "adopted": mapping.raw_adopted(round_result), "reason": reason}


def plan_sync(record_text: str | None, meta: dict[str, Any]) -> dict[str, Any]:
    """计划把指定决定标为已同步核心基线;缺少同步授权时保留待同步项。"""

    module = str(meta.get("module") or "")
    date = str(meta.get("date") or "")
    qids = [str(item) for item in (meta.get("qids") or [])]
    sync_ref = str(meta.get("sync_ref") or "")
    authorization = dict(meta.get("authorization") or {})
    record_path = str(meta.get("record_path") or "")
    base = {
        "op": "sync",
        "record_path": record_path,
        "module": module,
        "date": date,
        "qids": qids,
        "sync_ref": sync_ref,
        "expected_sha256": sha256_text(record_text),
    }
    if not qids:
        return {**base, "status": "no_new", "saved": False,
                "reason": "未指定要标记已同步的决定"}
    if not (authorization.get("sync") and authorization.get("write")):
        return {**base, "status": "unauthorized", "saved": False,
                "reason": "缺少同步授权或写入授权:待同步项原样保留,不自动签发权限"}
    if not record_text:
        return {**base, "status": "no_new", "saved": False,
                "reason": "记录不存在:没有已保存的决定可标记为已同步"}
    content, updated = apply_sync(record_text, module, qids, date, sync_ref)
    if not updated:
        parsed = parse_record(record_text, module)
        missing = [qid for qid in qids if qid not in parsed["decisions"]]
        reason = (f"本记录中没有这些决定:{'、'.join(missing)}" if missing
                  else "指定决定已标记为已同步")
        return {**base, "status": "no_new", "saved": False, "reason": reason}
    done = sorted(updated)
    return {**base, "status": "planned", "saved": False, "content": content,
            "synced": done,
            "note": f"标记 {module} 的 {'、'.join(done)} 为已同步（{sync_ref}）"}


def apply_save(plan: dict[str, Any],
               channel: Any,
               readback: Callable[[str], str | None]) -> dict[str, Any]:
    """经受控通道提交计划内容并回读核对;只按实际结果报告状态。"""

    status = plan.get("status")
    if status in {"no_new", "read_only", "unauthorized", "invalid",
                  "conflict", "denied", "save_unconfirmed"}:
        return _short_circuit(plan, status)
    if status != "planned":
        return {**_result(plan, "invalid", False,
                          f"计划状态 {status} 不可执行"),
                "next_round_ready": False}
    return _commit(plan, channel, readback)


def _short_circuit(plan: dict[str, Any], status: str) -> dict[str, Any]:
    """无需写入（或前次已判定）的计划:原样给出真实状态,不进通道。"""

    if status == "no_new":
        adopted_qids = set(plan.get("adopted") or {})
        duplicate_qids = {item["qid"] for item in plan.get("duplicates") or []}
        report = f"{plan.get('reason')}。"
        if plan.get("protected"):
            report += "未覆盖：" + "、".join(
                item["qid"] for item in plan["protected"]) + "。"
        return {**_result(plan, "no_new", True, report),
                "duplicates": plan.get("duplicates") or [],
                "protected": plan.get("protected") or [],
                "to_sync": _unsynced_qids(plan.get("content") or "",
                                          str(plan.get("module") or "")),
                "next_round_ready": bool(adopted_qids)
                and adopted_qids <= duplicate_qids}
    if status in {"read_only", "unauthorized"}:
        return {**_result(plan, status, False,
                          f"{plan.get('reason')};本轮内容未保存（未写入）"),
                "adopted": plan.get("adopted") or {},
                "next_round_ready": False}
    return {**_result(plan, status, bool(plan.get("saved")),
                      str(plan.get("report") or plan.get("reason") or "")),
            "next_round_ready": False}


def _commit(plan: dict[str, Any], channel: Any,
            readback: Callable[[str], str | None]) -> dict[str, Any]:
    """提交计划内容:核对实际版本与当前授权,写入后回读核对。"""

    record_path = str(plan.get("record_path") or "")
    expected = str(plan.get("expected_sha256") or "")
    current_text = readback(record_path)
    current = sha256_text(current_text)
    if current != expected:
        return {**_result(plan, "conflict", False,
                          mapping.conflict_report(plan, expected, current)),
                "rule_stage": "version", "target_version": current,
                "next_round_ready": False}

    scope = channel.scope()
    if scope.get("decision") != "allow":
        return {**_result(
            plan, "denied", False,
            f"写入前核对当前授权未通过:凭据不可写 {record_path}"
            f"（rule_stage={scope.get('rule_stage')}）;本轮内容未保存,"
            f"不换通道或路径重试"),
            "rule_stage": str(scope.get("rule_stage") or "identity"),
            "precheck": {"authorization": "denied", "scope": scope},
            "next_round_ready": False}

    write_result = channel.write(
        record_path, plan.get("content") or "",
        expected_sha256=expected, note=plan.get("note"))
    if write_result.get("decision") != "allow":
        return {**_result(
            plan, "denied", False,
            f"受控通道拒绝写入（rule_stage={write_result.get('rule_stage')}）："
            f"{write_result.get('reason')};本轮内容未保存,不换通道重试"),
            "rule_stage": write_result.get("rule_stage"),
            "channel_result": write_result, "next_round_ready": False}

    readback_text = readback(record_path)
    if readback_text is None:
        return {**_result(
            plan, "save_unconfirmed", False,
            f"写入后回读失败（{record_path}）:落盘未确认,不得称为已保存"),
            "channel_result": write_result, "next_round_ready": False}
    verdict = verify_saved(plan, readback_text)
    if not verdict["ok"]:
        return {**_result(
            plan, "save_unconfirmed", False,
            "回读内容与本轮最小记录不符,不得称为已保存:"
            + "；".join(verdict["failures"])),
            "channel_result": write_result, "verify": verdict,
            "next_round_ready": False}

    if plan.get("op") == "sync":
        done = plan.get("synced") or []
        return {
            **_result(plan, "saved", True,
                      f"已同步核心基线：{'、'.join(done)}"
                      f"（{plan.get('sync_ref')}）;记录 {record_path} 已回读核对,"
                      f"其余待同步项原样保留。"),
            "synced": done, "channel_result": write_result, "verify": verdict,
        }
    states = mapping.states(plan)
    to_sync = _unsynced_qids(readback_text, str(plan.get("module") or ""))
    return {
        **_result(plan, "saved", True, mapping.saved_report(plan, to_sync, states)),
        "states": states, "to_sync": to_sync,
        "next_round_ready": True, "channel_result": write_result,
        "verify": verdict,
    }


def verify_saved(plan: dict[str, Any], record_text: str | None) -> dict[str, Any]:
    """回读核对:本轮内容完整、历史未丢失、无重复、同步状态正确。"""

    failures: list[str] = []
    if record_text is None:
        return {"ok": False, "failures": ["回读目标不存在"]}
    module = str(plan.get("module") or "")
    parsed = parse_record(record_text, module)
    if plan.get("op") == "sync":
        for qid in plan.get("synced") or []:
            if qid not in parsed["sync_done"]:
                failures.append(f"同步状态未更新:{qid}")
        for qid in (plan.get("qids") or []):
            if str(qid) not in parsed["decisions"]:
                failures.append(f"回读缺少决定:{qid}")
        return {"ok": not failures, "failures": failures,
                "counts": _counts(parsed)}
    heads = line_counts(record_text)
    for entry in plan.get("entries") or []:
        head = decision_head(module, entry['qid'], entry['title'],
                             entry['value'])
        count = heads.get(head, 0)
        if count == 0:
            failures.append(f"回读缺少决定:{entry['qid']} {entry['title']}")
        elif count > 1:
            failures.append(f"回读出现重复决定:{entry['qid']} {entry['title']}")
    if plan.get("content") is not None and record_text != plan["content"]:
        failures.append("回读内容与计划内容不一致")
    for item in plan.get("duplicates") or []:
        if heads.get(decision_head(module, item['qid'], item['title'],
                                   item['value']), 0) > 1:
            failures.append(f"同一次回答重复创建决定:{item['qid']}")
    for item in plan.get("superseded") or []:
        if item.get("value") not in record_text:
            failures.append(f"旧决定历史丢失:{item['qid']} {item.get('value')}")
    precheck_history = (plan.get("precheck") or {}).get("history") or {}
    if plan.get("op") == "save" and (plan.get("entries")
                                     or plan.get("pending")):
        if parsed["rounds"] < int(precheck_history.get("rounds") or 0) + 1:
            failures.append("回读缺少本轮小节或既有历史轮次")
    return {"ok": not failures, "failures": failures, "counts": _counts(parsed)}


def restore_from_records(texts: dict[str, str], module: str) -> dict[str, Any]:
    """从实际记录恢复已定、未决与待同步内容;不读旧快照,不重问已定问题。"""

    merged = empty_parse()
    sources: list[str] = []
    for path in sorted(texts):
        text = texts[path]
        if text is None:
            continue
        parsed = parse_record(text, module)
        if not parsed["found"]:
            continue
        sources.append(path)
        for qid, item in parsed["decisions"].items():
            merged["decisions"][qid] = item
        merged["superseded"].extend(parsed["superseded"])
        merged["pending_by_qid"].update(
            {item["qid"]: item for item in parsed["pending"]})
        merged["pending_qids"].update(parsed["pending_qids"])
        merged["sync_done"].update(parsed["sync_done"])
        merged["rounds"] += parsed["rounds"]

    settled: dict[str, str] = {}
    states: dict[str, dict[str, bool]] = {}
    decisions: dict[str, dict[str, Any]] = {}
    to_sync: list[str] = []
    for qid, item in merged["decisions"].items():
        if item["superseded"]:
            continue
        synced = bool(item["synced"] or qid in merged["sync_done"])
        settled[qid] = item["value"]
        states[qid] = {"adopted": True, "saved": True, "synced": synced,
                       "implemented": bool(item.get("implemented")),
                       "verified": bool(item.get("verified"))}
        decisions[qid] = {"qid": qid, "title": item["title"],
                          "value": item["value"], "round": item.get("round"),
                          "synced": synced}
        if not synced:
            to_sync.append(qid)
    pending = [item for qid, item in sorted(merged["pending_by_qid"].items())
               if qid not in settled]
    settled_text = "、".join(f"{qid}={value}"
                            for qid, value in sorted(settled.items())) or "无"
    lines = [f"恢复模块：{module}",
             f"已定：{settled_text}",
             f"未决：{'、'.join(item['qid'] for item in pending) or '无'}"]
    if to_sync:
        lines.append(f"待同步（已保存,未同步核心基线）："
                     f"{'、'.join(sorted(to_sync))}；位置："
                     + ("、".join(sources) or "无"))
    else:
        lines.append("待同步：无")
    lines.append(f"记录位置：{'、'.join(sources) or '无'}")
    return {
        "op": "restore",
        "module": module,
        "records": sources,
        "settled": settled,
        "decisions": decisions,
        "states": states,
        "pending": pending,
        "superseded": merged["superseded"],
        "to_sync": sorted(to_sync),
        "sync_pending": bool(to_sync),
        "baseline_synced": not to_sync,
        "rounds": merged["rounds"],
        "report": "\n".join(lines),
    }


def _unsynced_qids(record_text: str, module: str) -> list[str]:
    """记录中已保存但尚未同步核心基线的决定(供后续轮次定位)。"""

    if not record_text:
        return []
    parsed = parse_record(record_text, module)
    return sorted(qid for qid, item in parsed["decisions"].items()
                  if not item.get("superseded") and not item.get("synced"))


def _counts(parsed: dict[str, Any]) -> dict[str, int]:
    return {
        "rounds": parsed["rounds"],
        "decisions": len(parsed["decisions"]),
        "superseded": len(parsed["superseded"]),
        "pending": len(parsed["pending"]),
        "sync_done": len(parsed["sync_done"]),
    }


def _result(plan: dict[str, Any], status: str, saved: bool,
            report: str) -> dict[str, Any]:
    return {
        "op": plan.get("op"),
        "status": status,
        "saved": saved,
        "record_path": plan.get("record_path"),
        "module": plan.get("module"),
        "report": report,
    }


class GateChannel:
    """mgs-gate 提交适配:与 MCP 通道同一条 GateService 受控写入路径。"""

    def __init__(self, service: Any, token: str) -> None:
        self.service = service
        self.token = token

    def scope(self) -> dict[str, Any]:
        return self.service.scope(self.token)

    def write(self, path: str, content: str, expected_sha256: str | None = None,
              note: str | None = None) -> dict[str, Any]:
        return self.service.write(self.token, path, content,
                                  expected_sha256=expected_sha256, note=note)

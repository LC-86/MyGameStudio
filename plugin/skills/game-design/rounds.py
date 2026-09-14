#!/usr/bin/env python3
"""Game-Design 模块问答接缝(统一设计问答框架票 02)。

公开 interface:
  run_round(turn) -> dict
  inspect_reply(text, expect) -> dict

本轮请求、已读事实、题目目录和开发者回答经 ``run_round`` 变成可见
回复与决定/未决对应。``inspect_reply`` 核对实际回复文本,供高层入口
验收使用。不提供对话框架,不写入项目文件。
"""

from __future__ import annotations

import json
import sys
import re
from typing import Any

from check_state import (
    adopts_all_recommendations, is_ambiguous_value, is_unknown_value,
    reply_statements,
)

KIND_LABELS = {
    "new_design": "新设计",
    "spec_gap": "补充规格",
    "design_change": "设计变更",
    "implementation_deviation": "实现偏差",
    "mixed": "混合请求",
}


def run_round(turn: dict[str, Any]) -> dict[str, Any]:
    """处理一轮设计讨论,返回识别结果、展示题目与可见回复。"""

    turn = dict(turn)
    unauthorized = _unauthorized_actions(turn)
    tweak = _local_tweak_result(turn)
    classification = _classify(turn)
    rewrite_design = False
    if tweak is not None:
        return _tweak_round(turn, classification, tweak, unauthorized)

    kind = classification["kind"]
    path = "deviation" if kind == "implementation_deviation" else "questions"
    extra = ""
    if kind == "implementation_deviation" or (
            "implementation_deviation" in classification["parts"]):
        extra = "不擅自改写设计迁就实现。\n"
    revisions = turn.get("boundary_revision") or {}
    revised = _revision_records(revisions, turn.get("settled") or {})
    if revised:
        settled_now = dict(turn.get("settled") or {})
        for qid, item in revised.items():
            settled_now[qid] = item["value"]
        turn["settled"] = settled_now
    catalog = _catalog(turn)
    previous_shown = [str(item) for item in (turn.get("shown") or [])]
    adopted: dict[str, Any] = {}
    pending: dict[str, Any] = {}
    if turn.get("user_reply"):
        if not previous_shown:
            previous_shown = [item["id"] for item in _ready_questions(turn)[0]]
        adopted, pending, settled = _map_answers(turn, catalog, previous_shown)
        adopted.update(revised)
        for qid, item in revised.items():
            settled[qid] = item["value"]
        follow = dict(turn)
        follow["settled"] = settled
        ready, deferred = _ready_questions(follow)
        shown = [item for item in ready if item["id"] not in previous_shown]
    else:
        shown, deferred = _ready_questions(turn)
        adopted = dict(revised)
    shown = _with_revision_context(shown, revisions)
    statuses = _collect_statuses(adopted, pending, turn, catalog)
    round_no = int(turn.get("round") or 1)
    header_lines = [
        f"目标：{turn.get('goal') or turn.get('request') or ''}",
        f"模块：{turn.get('module') or ''}",
        f"轮次：{round_no}",
        f"识别：{KIND_LABELS[kind]}。依据：{classification['rationale']}",
    ]
    if extra:
        header_lines.append(extra.rstrip())
    batches = _batch_questions(
        header_lines, shown,
        target=int(turn.get("batch_target") or 4000),
        limit=int(turn.get("char_limit") or 6000),
    )
    reply = batches[0]["text"] if batches else "\n".join(
        header_lines + [f"问题数量：0"]) + "\n"
    status = _format_status(adopted, pending, statuses, turn)
    if status:
        reply += "\n" + status
        if batches:
            batches[0]["text"] = reply
            batches[0]["chars"] = len(reply)
    return {
        "classification": classification,
        "path": path,
        "reply_text": reply,
        "module": str(turn.get("module") or ""), "round": round_no,
        "user_reply": str(turn.get("user_reply") or ""),
        "catalog": list(catalog.values()),
        "shown_ids": batches[0]["ids"] if batches else [],
        "deferred_ids": [item["id"] for item in deferred],
        "adopted": adopted,
        "pending": pending,
        "statuses": statuses,
        "batches": batches,
        "rewrite_design": rewrite_design,
        "unauthorized_actions": unauthorized,
    }


def inspect_reply(text: str, expect: dict[str, Any]) -> dict[str, Any]:
    """核对实际回复是否满足本轮合同。"""

    failures: list[str] = []
    if expect.get("require_label") and expect["require_label"] not in text:
        failures.append(f"缺少识别标签 {expect['require_label']}")
    for marker in expect.get("require_markers") or []:
        if marker not in text:
            failures.append(f"缺少标记 {marker}")
    for qid in expect.get("require_ids") or []:
        if f"❓ {qid}｜" not in text and f"❓ {qid}|" not in text:
            failures.append(f"缺少题目 {qid}")
    for qid in expect.get("forbid_ids") or []:
        if f"❓ {qid}｜" in text or f"❓ {qid}|" in text:
            failures.append(f"不应出现题目 {qid}")
    if "question_count" in expect:
        match = re.search(r"问题数量[:：]\s*(\d+)", text)
        actual = int(match.group(1)) if match else None
        if actual != expect["question_count"]:
            failures.append(
                f"问题数量应为 {expect['question_count']},实际 {actual}")
    if expect.get("max_chars") is not None and len(text) > expect["max_chars"]:
        failures.append(
            f"回复 {len(text)} 字符超过上限 {expect['max_chars']}")
    return {"ok": not failures, "failures": failures}


EXTERNAL_ACTIONS = {"publish_store", "publish", "push", "release"}
PRODUCT_ACTIONS = {"implement", "product", "code_change"}


def _unauthorized_actions(turn: dict[str, Any]) -> list[str]:
    auth = turn.get("authorization") or {}
    blocked: list[str] = []
    for action in turn.get("requested_actions") or []:
        if action in EXTERNAL_ACTIONS and not auth.get("external"):
            blocked.append(action)
        elif action in PRODUCT_ACTIONS and not auth.get("product"):
            blocked.append(action)
    return blocked


def _local_tweak_result(turn: dict[str, Any]) -> dict[str, Any] | None:
    tweak = turn.get("tweak") or {}
    if not tweak:
        return None
    if not (
        tweak.get("authorized")
        and tweak.get("unambiguous")
        and not tweak.get("side_effects")
    ):
        return None
    result = dict(tweak)
    result["diff"] = f"{tweak.get('before') or ''} → {tweak.get('after') or ''}"
    result["applied"] = True
    return result


def _tweak_round(
    turn: dict[str, Any],
    classification: dict[str, Any],
    tweak: dict[str, Any],
    unauthorized: list[str],
) -> dict[str, Any]:
    if classification["kind"] != "design_change":
        classification = {
            "kind": "design_change",
            "rationale": "已授权且无连带影响的局部调整。",
            "parts": [],
        }
    lines = [
        f"目标：{turn.get('goal') or turn.get('request') or ''}",
        f"模块：{turn.get('module') or ''}",
        (
            f"识别：{KIND_LABELS[classification['kind']]}。"
            f"依据：{classification['rationale']}"
        ),
        (
            f"已完成局部微调：{tweak.get('target') or ''}"
            f"「{tweak.get('before')}」→「{tweak.get('after')}」。"
        ),
    ]
    if unauthorized:
        lines.append("未执行未授权动作：" + "、".join(unauthorized))
    reply = "\n".join(lines) + "\n"
    return {
        "classification": classification,
        "path": "local_tweak",
        "reply_text": reply,
        "shown_ids": [],
        "deferred_ids": [],
        "adopted": {},
        "pending": {},
        "statuses": {},
        "batches": [],
        "rewrite_design": False,
        "tweak": tweak,
        "unauthorized_actions": unauthorized,
    }


def _revision_records(
    revisions: dict[str, Any],
    settled: dict[str, Any],
) -> dict[str, Any]:
    records: dict[str, Any] = {}
    for qid, rev in revisions.items():
        key = str(qid)
        old = settled.get(key, settled.get(qid))
        if isinstance(old, dict):
            old = old.get("value")
        if isinstance(rev, dict):
            new = rev.get("to")
            replaced = rev.get("from", old)
        else:
            new = rev
            replaced = old
        records[key] = {
            "value": new,
            "source": "revision",
            "replaced": replaced,
        }
    return records


def _with_revision_context(
    items: list[dict[str, Any]],
    revisions: dict[str, Any],
) -> list[dict[str, Any]]:
    if not revisions:
        return items
    updated: list[dict[str, Any]] = []
    for raw in items:
        item = dict(raw)
        notes = []
        for dep in item.get("depends_on") or []:
            rev = revisions.get(str(dep), revisions.get(dep))
            if isinstance(rev, dict) and rev.get("to"):
                notes.append(f"已修正 {dep}：{rev['to']}")
        if notes:
            body = str(item.get("body") or "").rstrip()
            item["body"] = body + ("\n" if body else "") + "\n".join(notes)
        updated.append(item)
    return updated


def _catalog(turn: dict[str, Any]) -> dict[str, dict[str, Any]]:
    """本轮题目目录:按当前模块作用域解析题号。

    其他模块可以有同编号问题;它们不进入本轮目录,展示、采纳与保存
    经同一目录保持一致的模块与问题身份。
    """

    module = str(turn.get("module") or "")
    items: dict[str, dict[str, Any]] = {}
    for index, raw in enumerate(turn.get("questions") or []):
        item = dict(raw)
        item["id"] = _question_id(item, index)
        if module and item.get("module") and item["module"] != module:
            continue
        items[item["id"]] = item
    return items


def _map_answers(
    turn: dict[str, Any],
    catalog: dict[str, dict[str, Any]],
    shown_ids: list[str],
) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    adopted: dict[str, Any] = {}
    pending: dict[str, Any] = {}
    settled: dict[str, Any] = {}
    for qid, value in (turn.get("settled") or {}).items():
        if isinstance(value, dict):
            adopted[str(qid)] = dict(value)
            settled[str(qid)] = value.get("value")
        else:
            adopted[str(qid)] = {"value": value, "source": "prior"}
            settled[str(qid)] = value

    text = str(turn.get("user_reply") or "").strip()
    if not text:
        return adopted, pending, settled

    unknown = bool(re.fullmatch(r"不知道|不清楚|先不确定", text))
    vague = bool(re.fullmatch(r"可以|好的?|嗯|行|随便", text))
    if unknown:
        for qid in shown_ids:
            if qid not in settled:
                pending[qid] = {"reason": "unknown"}
        return adopted, pending, settled

    # 逐题语句按原文顺序应用,同一题以最后一条为准;
    # 整体采纳只覆盖没有逐题语句的展示题目,题目例外覆盖整体采纳。
    statements = reply_statements(text)
    explicit: set[str] = set()
    for event in statements:
        if event.get("kind") == "adjust_index":
            index = int(event.get("index"))
            if not 0 <= index < len(shown_ids):
                continue
            explicit.add(shown_ids[index])
        else:
            explicit.add(str(event.get("qid") or ""))
    if adopts_all_recommendations(text):
        for qid in shown_ids:
            if qid in explicit:
                continue
            rec = (catalog.get(qid) or {}).get("recommendation")
            if rec is None:
                continue
            adopted[qid] = {"value": rec, "source": "recommendation"}
            settled[qid] = rec
    for event in statements:
        if event.get("kind") == "adjust_index":
            index = int(event.get("index"))
            if not 0 <= index < len(shown_ids):
                continue
            qid = shown_ids[index]
            kind = "adjust"
        else:
            qid = str(event.get("qid") or "")
            kind = str(event.get("kind"))
        if kind == "choice":
            adopted[qid] = {"value": event.get("value"), "source": "user"}
            settled[qid] = event.get("value")
            pending.pop(qid, None)
            continue
        if kind == "adjust":
            value = str(event.get("value"))
            if is_unknown_value(value) or is_ambiguous_value(value):
                adopted.pop(qid, None)
                settled.pop(qid, None)
                pending[qid] = {"reason": "unknown" if is_unknown_value(value)
                                else "ambiguous"}
                continue
            adopted[qid] = {"value": value, "source": "custom"}
            settled[qid] = value
            pending.pop(qid, None)
            continue
        # ambiguous / exception:该题本轮不作答,覆盖此前的任何采纳
        adopted.pop(qid, None)
        settled.pop(qid, None)
        pending[qid] = {"reason": "ambiguous" if kind == "ambiguous"
                        else "deferred"}

    for qid in shown_ids:
        if qid in settled or qid in pending:
            continue
        pending[qid] = {"reason": "ambiguous" if vague else "unanswered"}

    module = turn.get("module") or ""
    for qid, item in catalog.items():
        if qid in settled or qid in pending or qid in shown_ids:
            continue
        if module and item.get("module") and item["module"] != module:
            continue
        deps = [str(dep) for dep in (item.get("depends_on") or [])]
        if all(dep in settled for dep in deps):
            pending[qid] = {"reason": "unshown"}
    return adopted, pending, settled


def _format_status(
    adopted: dict[str, Any],
    pending: dict[str, Any],
    statuses: dict[str, list],
    turn: dict[str, Any],
) -> str:
    if not turn.get("user_reply") and not any(statuses.values()):
        return ""
    lines: list[str] = []
    if adopted or statuses.get("determined"):
        lines.append("✅ 已确定")
        for qid, item in adopted.items():
            lines.append(f"- {qid}：{item.get('value')}")
    if pending or statuses.get("pending"):
        lines.append("⏳ 待讨论")
        labels = {
            "unanswered": "未回答",
            "ambiguous": "含义不明,只澄清本题",
            "unshown": "尚未展示,不自动采纳",
            "missing_fact": "缺少可查事实",
            "unknown": "开发者表示不知道,保持提案",
            "deferred": "开发者明确暂不决定本题",
        }
        for qid, item in pending.items():
            lines.append(
                f"- {qid}：{labels.get(item.get('reason'), item.get('reason'))}")
    if statuses.get("proposals"):
        lines.append("💡 我的提案")
        for item in statuses["proposals"]:
            lines.append(f"- {item}（不是已采纳）")
    if statuses.get("to_verify"):
        lines.append("🧪 待验证")
        for item in statuses["to_verify"]:
            lines.append(f"- {item}")
    if statuses.get("not_now"):
        lines.append("🚫 当前不做")
        for item in statuses["not_now"]:
            lines.append(f"- {item}")
    return "\n".join(lines) + ("\n" if lines else "")


def _collect_statuses(
    adopted: dict[str, Any],
    pending: dict[str, Any],
    turn: dict[str, Any],
    catalog: dict[str, dict[str, Any]],
) -> dict[str, list]:
    statuses = {
        "determined": [f"{qid}：{item.get('value')}" for qid, item in adopted.items()],
        "pending": [f"{qid}：{item.get('reason')}" for qid, item in pending.items()],
        "proposals": list(turn.get("proposals") or []),
        "to_verify": list(turn.get("to_verify") or []),
        "not_now": list(turn.get("not_now") or []),
    }
    if any(item.get("reason") == "unknown" for item in pending.values()):
        for qid, item in pending.items():
            if item.get("reason") != "unknown":
                continue
            rec = (catalog.get(qid) or {}).get("recommendation")
            reason = (catalog.get(qid) or {}).get("reason") or ""
            if rec is not None:
                statuses["proposals"].append(
                    f"{qid}：{rec}。{reason}".rstrip("。"))
    goal = turn.get("experience_goal")
    if goal == "轻松":
        statuses["proposals"].append(
            "轻松不等于无失败;先用较低惩罚和可恢复进度作提案")
    return statuses


def _id_range(ids: list[str]) -> str:
    if not ids:
        return ""
    if len(ids) == 1:
        return ids[0]
    return f"{ids[0]}–{ids[-1]}"


def _batch_questions(
    header_lines: list[str],
    items: list[dict[str, Any]],
    *,
    target: int,
    limit: int,
) -> list[dict[str, Any]]:
    if not items:
        return []
    formatted = [(item, _format_question(item)) for item in items]
    groups: list[list[tuple[dict[str, Any], str]]] = []
    current: list[tuple[dict[str, Any], str]] = []

    def render(group: list[tuple[dict[str, Any], str]]) -> str:
        ids = [item["id"] for item, _ in group]
        lines = list(header_lines)
        lines.append(f"问题数量：{len(group)}")
        if len(formatted) > 1 and len(group) < len(formatted):
            lines.append(f"本批 {_id_range(ids)}")
        body = "\n\n---\n\n".join(text for _, text in group)
        return "\n".join(lines) + "\n\n" + body + "\n"

    for piece in formatted:
        trial = current + [piece]
        trial_text = render(trial)
        if current and len(trial_text) > target:
            groups.append(current)
            current = [piece]
        else:
            current = trial
    if current:
        groups.append(current)
    batches = []
    for group in groups:
        text = render(group)
        batches.append({
            "ids": [item["id"] for item, _ in group],
            "text": text,
            "chars": len(text),
        })
        if len(text) > limit:
            batches[-1]["exceeds_limit"] = True
    return batches


def _question_id(item: dict[str, Any], index: int) -> str:
    raw = str(item.get("id") or index + 1)
    if raw.startswith("Q"):
        return raw
    return f"Q{raw}"


def _ready_questions(
    turn: dict[str, Any],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    module = turn.get("module") or ""
    settled = set((turn.get("settled") or {}).keys())
    missing_facts = set(turn.get("missing_facts") or [])
    ready: list[dict[str, Any]] = []
    deferred: list[dict[str, Any]] = []
    for index, raw in enumerate(turn.get("questions") or []):
        item = dict(raw)
        item["id"] = _question_id(item, index)
        if module and item.get("module") and item["module"] != module:
            continue
        if item["id"] in settled:
            continue
        deps = [str(dep) for dep in (item.get("depends_on") or [])]
        fact = item.get("needs_fact")
        waiting_fact = bool(fact) and fact in missing_facts
        if any(dep not in settled for dep in deps) or waiting_fact:
            deferred.append(item)
            continue
        ready.append(item)
    ready.sort(key=lambda item: (0 if item.get("priority") == "high" else 1))
    return ready, deferred


def _format_question(item: dict[str, Any]) -> str:
    lines = [
        f"❓ {item['id']}｜{item.get('title') or item['id']}",
        str(item.get("body") or "").rstrip(),
    ]
    options = item.get("options") or {}
    if options and not item.get("open"):
        lines.append("")
        lines.append("选项")
        for key in sorted(options):
            lines.append(f"- {key} {options[key]}")
    if not item.get("open") or item.get("recommendation"):
        rec = item.get("recommendation") or ""
        reason = item.get("reason") or ""
        suggestion = f"➡️ 我的建议：{rec}。"
        if reason:
            suggestion += f"理由：{reason}"
        lines.append("")
        lines.append(suggestion)
    return "\n".join(line for line in lines if line is not None)


def _classify(turn: dict[str, Any]) -> dict[str, Any]:
    signals = _signals(turn)
    parts: list[str] = []
    rationales: list[str] = []
    mismatches = list(signals.get("implementation_mismatches") or [])
    gaps = list(signals.get("named_gaps") or [])
    wants_change = bool(signals.get("wants_change"))
    covers = bool(signals.get("covers_request"))
    has_design = bool(signals.get("has_current_design"))

    if mismatches:
        parts.append("implementation_deviation")
        rationales.append("实现与已明确设计不一致:" + "；".join(mismatches))
    if gaps and (covers or has_design):
        parts.append("spec_gap")
        rationales.append("现行设计未写清:" + "、".join(gaps))
    if wants_change:
        targets = signals.get("change_targets") or []
        parts.append("design_change")
        if targets:
            rationales.append("请求调整已有设计:" + "、".join(targets))
        else:
            rationales.append("请求在已有设计上优化、调整或增删。")
    if not parts:
        if not covers:
            parts.append("new_design")
            if has_design:
                rationales.append("现行设计未覆盖本轮请求,需要建立该模块设计。")
            else:
                rationales.append("尚无可用的当前有效设计,从想法建立设计。")
        else:
            parts.append("spec_gap")
            rationales.append(
                "请求落在现行设计方向内,待决定细节尚未写清,按补充规格补齐。")

    if len(parts) > 1:
        return {
            "kind": "mixed",
            "rationale": "同一请求包含多类问题,分别处理。" + " ".join(rationales),
            "parts": parts,
        }
    return {
        "kind": parts[0],
        "rationale": rationales[0],
        "parts": [],
    }


def _signals(turn: dict[str, Any]) -> dict[str, Any]:
    if turn.get("signals"):
        raw = dict(turn["signals"])
    else:
        design = turn.get("current_design") or {}
        impl = turn.get("implementation") or {}
        raw = {
            "has_current_design": bool(design.get("exists")),
            "covers_request": bool(design.get("covers_request")),
            "named_gaps": list(design.get("gaps") or []),
            "wants_change": bool(design.get("wants_change") or turn.get("change")),
            "implementation_mismatches": list(
                impl.get("contradicts_design") or []),
        }
    raw.setdefault("named_gaps", [])
    raw.setdefault("implementation_mismatches", [])
    return raw


def _cli(argv: list[str]) -> int:
    if len(argv) < 2 or argv[1] in {"-h", "--help"}:
        print("usage: rounds.py run < turn.json", file=sys.stderr)
        return 2
    if argv[1] != "run":
        print(f"未知动作: {argv[1]}", file=sys.stderr)
        return 2
    turn = json.loads(sys.stdin.read())
    print(json.dumps(run_round(turn), ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(_cli(sys.argv))

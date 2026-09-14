#!/usr/bin/env python3
"""Game-Design 决定记录格式(统一设计问答框架票 03)。

记录文本的唯一解释与渲染位置:决定头、来源与建议出处、影响、未决项、
替代关系与基线同步状态。``parse_record`` 读;``round_section`` /
``compose`` / ``mark_superseded`` / ``apply_sync`` 写。保存与恢复的编排
在 ``decisions.py``;本 module 不接触受控通道,也不决定是否写入。
"""

from __future__ import annotations

import hashlib
import re
from typing import Any

SYNC_PENDING = "待同步"
SYNC_DONE = "已同步"

DECISION_HEAD = re.compile(
    r"^- D (?P<module>[^·]+)·(?P<qid>Q\d+) (?P<title>.+)：采纳 (?P<value>.+)$")
SECTION_HEAD = re.compile(r"^## 第 (?P<round>\d+) 轮 (?P<date>\S+)\s*$")
SYNC_SECTION_HEAD = re.compile(r"^## 同步 (?P<date>\S+)\s*$")
PENDING_LINE = re.compile(r"^- (?P<qid>Q\d+) (?P<title>.+)：(?P<reason>.+)$")
RE_PLACEMENT = re.compile(
    r"^- 替代：(?P<qid>Q\d+) 「(?P<value>.+)」（第 \d+ 轮.*$")

PENDING_LABELS = {
    "unanswered": "未回答",
    "ambiguous": "含义不明",
    "unknown": "开发者表示不知道",
    "missing_fact": "缺少可查事实",
    "unshown": "尚未展示",
}
DEFERRED_LABEL = "依赖未满足"


def sha256_text(text: str | None) -> str:
    """目标版本标识:None(不存在)记为 absent,与受控通道语义一致。"""

    if text is None:
        return "absent"
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def empty_parse() -> dict[str, Any]:
    return {"found": False, "rounds": 0, "decisions": {}, "superseded": [],
            "pending": [], "pending_qids": set(), "sync_done": {},
            "pending_by_qid": {}}


def merge_records(texts: dict[str, str | None], module: str) -> dict[str, Any]:
    """按决定身份与修订合并多份记录;同步状态绑定当前修订,不按文件名覆盖。"""

    merged = empty_parse()
    winners: dict[str, dict[str, Any]] = {}
    pending_winners: dict[str, dict[str, Any]] = {}
    for text in (texts or {}).values():
        if not text:
            continue
        parsed = parse_record(text, module)
        if not parsed["found"]:
            continue
        merged["found"] = True
        merged["rounds"] += parsed["rounds"]
        merged["superseded"].extend(parsed["superseded"])
        for qid, item in parsed["decisions"].items():
            if _newer_revision(item, winners.get(qid)):
                winners[qid] = dict(item)
        for item in parsed["pending"]:
            qid = item["qid"]
            if _newer_revision(item, pending_winners.get(qid)):
                pending_winners[qid] = dict(item)
    merged["decisions"] = winners
    merged["sync_done"] = {
        qid: True for qid, item in winners.items()
        if item.get("synced") and not item.get("superseded")}
    merged["pending"] = [
        pending_winners[qid] for qid in sorted(pending_winners)
        if qid not in winners or winners[qid].get("superseded")]
    merged["pending_qids"] = {item["qid"] for item in merged["pending"]}
    merged["pending_by_qid"] = {item["qid"]: item for item in merged["pending"]}
    return merged


def _newer_revision(item: dict[str, Any],
                    previous: dict[str, Any] | None) -> bool:
    if previous is None:
        return True
    current_round = item.get("round") or 0
    previous_round = previous.get("round") or 0
    if current_round != previous_round:
        return current_round > previous_round
    if bool(item.get("superseded")) != bool(previous.get("superseded")):
        return not item.get("superseded")
    return str(item.get("date") or "") >= str(previous.get("date") or "")


def parse_record(text: str, module: str) -> dict[str, Any]:
    """解析本模块记录:决定头、历史（已被替代）、未决项与同步标记。"""

    parsed = empty_parse()
    if not text:
        return parsed
    current_round = None
    current_date = ""
    current_qid = None
    in_pending = False
    for line in text.splitlines():
        stripped = line.strip()
        section = SECTION_HEAD.match(stripped)
        if section:
            parsed["rounds"] += 1
            current_round = int(section.group("round"))
            current_date = section.group("date")
            current_qid = None
            in_pending = False
            continue
        if SYNC_SECTION_HEAD.match(stripped):
            current_round = None
            current_date = ""
            current_qid = None
            in_pending = False
            continue
        if stripped.startswith("### "):
            in_pending = stripped.startswith("### 未决项")
            current_qid = None
            continue
        decision = DECISION_HEAD.match(stripped)
        if decision:
            if decision.group("module").strip() != module:
                continue
            current_qid = _add_decision(parsed, decision, current_date,
                                        current_round)
            continue
        if current_qid and stripped.startswith("- 来源："):
            parsed["decisions"][current_qid]["source_label"] = \
                stripped.split("：", 1)[1].strip()
            continue
        if current_qid and stripped.startswith("- 建议出处："):
            parsed["decisions"][current_qid]["provenance"] = \
                stripped.split("：", 1)[1].strip()
            continue
        if current_qid and stripped.startswith("- 影响："):
            parsed["decisions"][current_qid]["impact"] = \
                stripped.split("：", 1)[1].strip()
            continue
        if current_qid and stripped.startswith("- 同步状态："):
            if SYNC_DONE in stripped:
                mark_synced(parsed, current_qid)
            continue
        if stripped.startswith("- 已同步："):
            for qid in re.findall(r"Q\d+", stripped):
                mark_synced(parsed, qid)
            continue
        if in_pending:
            _add_pending(parsed, stripped, current_round)
            continue
        _add_replacement(parsed, stripped, current_round)
    return parsed


def _add_decision(parsed: dict[str, Any], decision: "re.Match[str]",
                  date: str, round_no: int | None) -> str:
    """登记一条决定头;同一问题的新决定把旧决定转入历史。

    同步状态按文件顺序就地标记:决定被后来轮次替代时,旧决定的同步标记
    随替代一起退出 ``sync_done``(它属于已失效的旧要求),新决定从"待同步"
    重新开始——不把旧要求的已同步状态继承给新要求。
    """

    parsed["found"] = True
    qid = decision.group("qid")
    item = {
        "qid": qid,
        "module": decision.group("module").strip(),
        "title": decision.group("title").strip(),
        "value": strip_status(decision.group("value").strip()),
        "round": round_no,
        "date": date,
        "superseded": False,
        "synced": False,
    }
    previous = parsed["decisions"].get(qid)
    if previous and not previous.get("superseded"):
        previous["superseded"] = True
        parsed["sync_done"].pop(qid, None)
        parsed["superseded"].append({
            "qid": qid, "value": previous["value"],
            "round": previous.get("round"), "replaced_round": round_no})
    parsed["decisions"][qid] = item
    return qid


def _add_pending(parsed: dict[str, Any], stripped: str,
                 round_no: int | None) -> None:
    item = PENDING_LINE.match(stripped)
    if not item:
        return
    reason = item.group("reason").strip()
    qid = item.group("qid")
    parsed["pending"].append({
        "qid": qid, "title": item.group("title").strip(), "reason": reason,
        "status": pending_status(reason), "round": round_no})
    parsed["pending_qids"].add(qid)


def _add_replacement(parsed: dict[str, Any], stripped: str,
                     round_no: int | None) -> None:
    replacement = RE_PLACEMENT.match(stripped)
    if not replacement:
        return
    qid = replacement.group("qid")
    value = replacement.group("value").strip()
    known = any(entry["qid"] == qid and entry["value"] == value
                for entry in parsed["superseded"])
    if not known and qid in parsed["decisions"] \
            and parsed["decisions"][qid]["value"] != value:
        parsed["superseded"].append({"qid": qid, "value": value,
                                     "round": round_no,
                                     "replaced_round": round_no})


def mark_synced(parsed: dict[str, Any], qid: str) -> None:
    parsed["sync_done"][qid] = True
    item = parsed["decisions"].get(qid)
    if item is not None:
        item["synced"] = True


def strip_status(value: str) -> str:
    """去掉决定值尾部的状态括注（已被替代/已同步）,保留决定含义。"""

    return re.sub(r"[（(](?:已被替代|已同步)[^）)]*[）)]\s*$", "", value).strip()


def pending_status(reason: str) -> str:
    """未决原因回显:记录中的说明文字去掉前置括注后原样保留。"""

    return re.sub(r"（未决,不作为已采纳）\s*$", "", reason).strip()


def counts(parsed: dict[str, Any]) -> dict[str, int]:
    return {
        "rounds": parsed["rounds"],
        "decisions": len(parsed["decisions"]),
        "superseded": len(parsed["superseded"]),
        "pending": len(parsed["pending"]),
        "sync_done": len(parsed["sync_done"]),
    }


def head_counts(parsed: dict[str, Any]) -> dict[str, int]:
    counts_map: dict[str, int] = {}
    for item in parsed["decisions"].values():
        if item.get("superseded"):
            continue
        head = decision_head(item["module"], item["qid"], item["title"],
                             item["value"])
        counts_map[head] = counts_map.get(head, 0) + 1
    return counts_map


def line_counts(text: str) -> dict[str, int]:
    """逐字行计数:用于核对决定头是否重复、历史行是否仍在。"""

    counts_map: dict[str, int] = {}
    for line in text.splitlines():
        stripped = line.strip()
        if stripped.startswith("- D "):
            counts_map[stripped] = counts_map.get(stripped, 0) + 1
    return counts_map


def decision_head(module: str, qid: str, title: str, value: str) -> str:
    return f"- D {module}·{qid} {title}：采纳 {value}"


def round_section(module: str, round_no: int, date: str, decider: str,
                  reply: str, entries: list[dict[str, Any]],
                  pending: list[dict[str, str]]) -> str:
    """渲染本轮小节:决定、来源与建议出处、影响、替代关系与未决项。"""

    lines = [f"## 第 {round_no} 轮 {date}",
             f"- 决定者：{decider}。日期：{date}。",
             f"- 用户回复：「{reply}」"]
    for entry in entries:
        lines.append(decision_head(module, entry["qid"], entry["title"],
                                   entry["value"]))
        lines.append(f"  - 来源：{entry['source_label']}")
        lines.append(f"  - 建议出处：{entry['provenance']}")
        lines.append(f"  - 影响：{entry['impact']}")
        lines.append(f"  - 同步状态：{SYNC_PENDING}")
        replacement = entry.get("replacement") or {}
        if replacement.get("value"):
            lines.append(f"  - 替代：「{replacement['value']}」"
                         f"（第 {replacement.get('round') or '?'} 轮，历史保留）；"
                         f"旧决定保留为历史,不覆盖其他有效决定。")
    if pending:
        lines.append("")
        lines.append("### 未决项")
        for item in pending:
            lines.append(f"- {item['qid']} {item['title']}：{item['status']}"
                         f"（未决,不作为已采纳）")
        lines.append(f"- 未决影响：以上 {len(pending)} 项待后续轮次"
                     f"（缺答案、含义不明、依赖未满足或尚未展示）。")
    return "\n".join(lines)


def compose(module: str, existing: str, section: str) -> str:
    """沿用已有记录位置:首轮建立标题,后续轮次追加而不重写历史。"""

    if not existing.strip():
        return f"# {module}：决定记录\n\n{section}\n"
    return existing.rstrip() + "\n\n" + section + "\n"


def mark_superseded(record_text: str | None, superseded: list[dict[str, Any]],
                    round_no: int, date: str,
                    entries: list[dict[str, Any]]) -> str:
    """把被替代的旧决定头标为已被替代,并补记替代来源;不删旧内容。"""

    if not superseded or not record_text:
        return record_text or ""
    values = {item["qid"]: item["value"] for item in superseded}
    updated_lines: list[str] = []
    for line in record_text.splitlines():
        matched = DECISION_HEAD.match(line.strip())
        if matched:
            qid = matched.group("qid")
            if qid in values and f"采纳 {values[qid]}" in line:
                line = f"{line.rstrip()}（已被替代）"
        updated_lines.append(line)
    text = "\n".join(updated_lines)
    if text and not text.endswith("\n"):
        text += "\n"
    lines = [text.rstrip("\n"), "", f"### 替代记录 {date}"]
    for entry in entries:
        replacement = entry.get("replacement") or {}
        if not replacement.get("value"):
            continue
        lines.append(f"- 替代：{entry['qid']} 「{replacement['value']}」"
                     f"（第 {replacement.get('round') or '?'} 轮，历史保留）"
                     f"由第 {round_no} 轮改为「{entry['value']}」")
    return "\n".join(lines) + "\n"


def apply_sync(record_text: str, module: str, qids: list[str], date: str,
               sync_ref: str) -> tuple[str, dict[str, bool]]:
    """把指定决定的同步状态改为已同步,并追加同步记录段。"""

    updated: dict[str, bool] = {}
    lines: list[str] = []
    current_qid = None
    current_superseded = False
    for line in record_text.splitlines():
        stripped = line.strip()
        matched = DECISION_HEAD.match(stripped)
        if matched:
            history = "（已被替代）" in line
            current_superseded = history and (
                matched.group("module").strip() == module)
            current_qid = None if history or (
                matched.group("module").strip() != module) \
                else matched.group("qid")
            lines.append(line)
            continue
        if stripped.startswith("### "):
            current_qid = None
            current_superseded = False
        if current_superseded and stripped.startswith("- 同步状态：") \
                and SYNC_PENDING in stripped:
            indent = line[: len(line) - len(line.lstrip())]
            lines.append(f"{indent}- 同步状态：不适用（已被替代；"
                         f"同步状态由当前决定承接）")
            continue
        if current_qid and current_qid in qids \
                and stripped.startswith("- 同步状态："):
            if SYNC_DONE in stripped:
                lines.append(line)
                continue
            indent = line[: len(line) - len(line.lstrip())]
            lines.append(f"{indent}- 同步状态：{SYNC_DONE}"
                         f"（{date}，{sync_ref}）")
            updated[current_qid] = True
            continue
        lines.append(line)
    text = "\n".join(lines)
    if text and not text.endswith("\n"):
        text += "\n"
    done = sorted(updated)
    if done:
        text += (f"\n## 同步 {date}\n"
                 f"- 已同步：{sync_ref}（{date}）；决定："
                 + "、".join(done) + "\n")
    return text, updated

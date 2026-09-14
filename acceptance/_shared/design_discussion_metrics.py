#!/usr/bin/env python3
"""设计问答耗时与步骤的测量 seam(统一框架票 01,供票 09 复用)。

从既有高层验收落盘的宿主事件(app-server JSONL)计算规格四项耗时与
步骤计数。时间只取事件 ``completedAtMs`` / ``emittedAtMs`` 与回读结果,
不用助手自报时长。可控样例与真实事件走同一 interface;样例不得冒充
真实模型耗时证据。

公开 interface:
  measure_module_run(turns, *, user_wait_intervals=(), expected_outcomes=None,
                     observed_outcomes=None) -> dict
  record_baseline_identity(plugin_root, *, host=None) -> dict
  load_jsonl(path) -> list
"""

from __future__ import annotations

import hashlib
import json
import re
import sys
from pathlib import Path
from typing import Any

NOT_APPLICABLE = "not_applicable"
UNKNOWN = "unknown"
INCOMPLETE = "incomplete"

_PATH_RE = re.compile(
    r"(?:(?<![A-Za-z0-9_./-])(?:\./)?|/[\w./-]+/)"
    r"(docs/mygamestudio/[^\s\"'\\;]+|src/[^\s\"'\\;]+)"
)

_IDENTITY_FILES = (
    ".codex-plugin/plugin.json",
    "skills/game-design/SKILL.md",
    "skills/game-spec/SKILL.md",
    "internal/methods/grill-with-docs/SKILL.md",
    "internal/methods/grilling/SKILL.md",
    "internal/methods/domain-modeling/SKILL.md",
    "internal/methods/wayfinder/SKILL.md",
    "internal/methods/writing-for-agents/SKILL.md",
)


def load_jsonl(path: str | Path) -> list[dict[str, Any]]:
    """读取一行一条 JSON 的事件或审计文件;空行跳过。"""

    rows: list[dict[str, Any]] = []
    text = Path(path).read_text(encoding="utf-8")
    for line in text.splitlines():
        line = line.strip()
        if not line:
            continue
        rows.append(json.loads(line))
    return rows


def event_ms(msg: dict[str, Any]) -> int | None:
    """优先 item 完成时间,其次事件发出时间。"""

    params = msg.get("params") or {}
    for raw in (params.get("completedAtMs"), msg.get("emittedAtMs")):
        if raw is not None:
            return int(raw)
    item = params.get("item") or {}
    if item.get("completedAtMs") is not None:
        return int(item["completedAtMs"])
    return None


def _item(msg: dict[str, Any]) -> dict[str, Any]:
    return (msg.get("params") or {}).get("item") or {}


def normalize_path(path: str) -> str:
    text = str(path or "").replace("\\", "/").split("?", 1)[0]
    for marker in ("docs/mygamestudio/", "src/"):
        if marker in text:
            return marker + text.split(marker, 1)[1]
    return text.lstrip("./")


def _mcp_result(item: dict[str, Any]) -> dict[str, Any]:
    result = item.get("result") or {}
    blocks = result.get("content") or []
    for block in blocks:
        text = block.get("text") if isinstance(block, dict) else None
        if not text:
            continue
        try:
            payload = json.loads(text)
        except json.JSONDecodeError:
            continue
        if isinstance(payload, dict):
            return payload
    return {}


def _command_paths(item: dict[str, Any]) -> list[str]:
    found: list[str] = []
    seen: set[str] = set()
    for action in item.get("commandActions") or []:
        raw = action.get("path") or ""
        if action.get("type") == "read" and raw:
            key = normalize_path(raw)
            if key not in seen:
                seen.add(key)
                found.append(key)
    blob = " ".join([
        str(item.get("command") or ""),
        " ".join(str(a.get("command") or "") for a in (item.get("commandActions") or [])),
    ])
    for match in _PATH_RE.finditer(blob):
        key = normalize_path(match.group(1) if match.lastindex else match.group(0))
        if key not in seen:
            seen.add(key)
            found.append(key)
    return found


def _write_info(item: dict[str, Any]) -> tuple[str, str, int] | None:
    if item.get("type") != "mcpToolCall" or item.get("tool") != "mgs_write":
        return None
    args = item.get("arguments") or {}
    payload = _mcp_result(item)
    path = normalize_path(str(payload.get("target") or args.get("path") or ""))
    decision = str(payload.get("decision") or "")
    nbytes = int(payload.get("bytes") or len(str(args.get("content") or "")))
    if not path:
        return None
    return path, decision, nbytes


def _is_decision_record(path: str) -> bool:
    name = path.replace("\\", "/")
    if "decision-map-" in name:
        return False
    return "/records/decision-" in f"/{name}" or name.startswith("docs/mygamestudio/records/decision-")


def _is_sync_target(path: str) -> bool:
    return path.endswith("GAME_DESIGN.md") or path.endswith("GAME_DESIGN.md/")


def _is_final_answer(item: dict[str, Any]) -> bool:
    return item.get("type") == "agentMessage" and item.get("phase") == "final_answer"


def _is_user(item: dict[str, Any]) -> bool:
    return item.get("type") == "userMessage"


_HOST_FAULT_MARKERS = (
    "codex-code-mode-host",
    "failed to spawn code-mode host",
)


def _host_tool_fault(events: list[dict[str, Any]]) -> bool:
    """从可见回复或命令输出识别宿主工具启动失败(外部故障)。"""

    for msg in events:
        item = _item(msg)
        blobs = [str(item.get("text") or ""), str(item.get("aggregatedOutput") or "")]
        if item.get("type") == "userMessage":
            continue
        text = "\n".join(blobs)
        if any(marker in text for marker in _HOST_FAULT_MARKERS):
            return True
    return False


def _usage_tokens(events: list[dict[str, Any]]) -> Any:
    for msg in events:
        params = msg.get("params") or {}
        for blob in (params, params.get("turn") or {}, _item(msg)):
            usage = blob.get("usage") or blob.get("tokenUsage") or blob.get("tokens")
            if isinstance(usage, dict) and usage:
                return usage
            if isinstance(usage, (int, float)):
                return {"total": int(usage)}
    return UNKNOWN


def _measure_turn(events: list[dict[str, Any]]) -> dict[str, Any]:
    user_at: int | None = None
    final_at: int | None = None
    turn_done_at: int | None = None
    adopted_writes: dict[str, int] = {}
    sync_writes: dict[str, int] = {}
    rereads: dict[str, int] = {}
    denied: set[str] = set()
    allowed: set[str] = set()
    failed_then_ok = False

    for msg in events:
        at = event_ms(msg)
        method = msg.get("method")
        if method == "turn/completed" and at is not None:
            turn_done_at = at
        if method == "turn/failed" and at is not None:
            turn_done_at = at
        item = _item(msg)
        if not item or at is None:
            continue
        if _is_user(item) and user_at is None:
            user_at = at
        if _is_final_answer(item):
            final_at = at
        write = _write_info(item)
        if write:
            path, decision, _nbytes = write
            if decision == "deny":
                denied.add(path)
            elif decision == "allow":
                allowed.add(path)
                if path in denied:
                    failed_then_ok = True
                if _is_decision_record(path):
                    adopted_writes[path] = at
                if _is_sync_target(path):
                    sync_writes[path] = at
        if item.get("type") == "commandExecution":
            if item.get("status") == "failed":
                failed_then_ok = True
            for path in _command_paths(item):
                rereads[path] = at

    has_adopted = bool(adopted_writes)
    if user_at is None:
        save: Any = INCOMPLETE
        wait: Any = INCOMPLETE
    elif not has_adopted:
        save = NOT_APPLICABLE
        wait = (final_at - user_at) if final_at is not None else INCOMPLETE
    else:
        reread_times = [rereads[p] for p in adopted_writes if p in rereads and rereads[p] >= adopted_writes[p]]
        if len(reread_times) == len(adopted_writes):
            save = max(reread_times) - user_at
        else:
            save = INCOMPLETE
        wait = (final_at - user_at) if final_at is not None else INCOMPLETE

    return {
        "user_answer_at_ms": user_at,
        "result_presented_at_ms": final_at,
        "turn_completed_at_ms": turn_done_at,
        "decision_save_ms": save,
        "continue_wait_ms": wait,
        "has_adopted_content": has_adopted,
        "retried": failed_then_ok,
        "adopted_paths": sorted(adopted_writes),
        "sync_paths": sorted(sync_writes),
        "reread_paths": sorted(rereads),
    }


def _count_steps(turns: list[dict[str, Any]]) -> dict[str, Any]:
    read_count = 0
    read_bytes = 0
    necessary = 0
    repeat = 0
    write_count = 0
    write_files: set[str] = set()
    checks = 0
    check_repeat = 0
    scoped = False
    tool_calls = 0
    seen_unread: set[str] = set()
    written: set[str] = set()
    seen_check: set[str] = set()

    for turn in turns:
        scoped = False
        for msg in turn.get("events") or []:
            item = _item(msg)
            kind = item.get("type")
            if kind in {"commandExecution", "mcpToolCall"}:
                tool_calls += 1
            write = _write_info(item)
            if write:
                path, decision, _nbytes = write
                if decision == "allow":
                    write_count += 1
                    write_files.add(path)
                    written.add(path)
                    seen_unread.discard(path)
                continue
            if kind == "mcpToolCall" and item.get("tool") == "mgs_scope":
                checks += 1
                if scoped:
                    check_repeat += 1
                scoped = True
                continue
            if kind != "commandExecution":
                continue
            paths = _command_paths(item)
            output = str(item.get("aggregatedOutput") or "")
            if paths:
                read_count += len(paths)
                read_bytes += len(output)
            command = str(item.get("command") or "")
            is_shasum = "shasum" in command
            for path in paths:
                if path in written:
                    necessary += 1
                    written.discard(path)
                    checks += 1
                    key = f"reread:{path}"
                    if key in seen_check:
                        check_repeat += 1
                    seen_check.add(key)
                elif path in seen_unread:
                    repeat += 1
                else:
                    necessary += 1
                    seen_unread.add(path)
                if is_shasum:
                    checks += 1

    return {
        "discussion_rounds": len(turns),
        "reads": {
            "count": read_count,
            "bytes": read_bytes,
            "necessary": necessary,
            "repeat": repeat,
        },
        "writes": {
            "count": write_count,
            "files": len(write_files),
        },
        "checks": {
            "count": checks,
            "repeat": check_repeat,
            "necessary": max(0, checks - check_repeat),
        },
        "tool_calls": {"count": tool_calls},
        "tokens": UNKNOWN,
    }


def measure_module_run(
    turns: list[dict[str, Any]],
    *,
    user_wait_intervals: tuple[tuple[int, int], ...] | list[tuple[int, int]] = (),
    expected_outcomes: dict[str, Any] | None = None,
    observed_outcomes: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """按规格计算一个完整模块场景的耗时、步骤与例外分类。"""

    expected_outcomes = expected_outcomes or {}
    observed_outcomes = observed_outcomes or {}
    rounds = [_measure_turn(turn.get("events") or []) for turn in turns]
    if not user_wait_intervals and len(rounds) > 1:
        auto: list[tuple[int, int]] = []
        for prev, cur in zip(rounds, rounds[1:]):
            gap_start, gap_end = prev["turn_completed_at_ms"], cur["user_answer_at_ms"]
            if gap_start is not None and gap_end is not None and gap_end > gap_start:
                auto.append((gap_start, gap_end))
        user_wait_intervals = auto
    exceptions: list[dict[str, str]] = []

    for index, row in enumerate(rounds, start=1):
        row["index"] = index
        if row["decision_save_ms"] == INCOMPLETE or row["continue_wait_ms"] == INCOMPLETE:
            exceptions.append({
                "kind": "missing_record",
                "detail": f"第 {index} 轮缺少保存回读或完整结果终点",
            })
        if row.get("retried"):
            exceptions.append({
                "kind": "retry",
                "detail": f"第 {index} 轮含失败重试,已计入耗时",
            })

    all_events = [msg for turn in turns for msg in (turn.get("events") or [])]
    if any(msg.get("method") == "turn/failed" for msg in all_events):
        exceptions.append({"kind": "external_fault", "detail": "存在 turn/failed"})
    if _host_tool_fault(all_events):
        exceptions.append({
            "kind": "external_fault",
            "detail": "宿主工具未能启动(如 code-mode-host 缺失),读取/写入未执行",
        })

    start = next((row["user_answer_at_ms"] for row in rounds if row["user_answer_at_ms"] is not None), None)
    end_candidates = []
    for row in rounds:
        for key in ("result_presented_at_ms", "turn_completed_at_ms"):
            if row[key] is not None:
                end_candidates.append(row[key])
    end = max(end_candidates) if end_candidates else None

    deducted = 0
    for wait_start, wait_end in user_wait_intervals:
        if wait_end > wait_start:
            deducted += wait_end - wait_start

    if start is None or end is None:
        processing: Any = INCOMPLETE
        exceptions.append({"kind": "missing_record", "detail": "完整模块缺少起点或终点"})
    else:
        processing = end - start - deducted
        if processing < 0:
            processing = INCOMPLETE
            exceptions.append({"kind": "missing_record", "detail": "用户等待扣除后时长为负"})

    save_values = [row["decision_save_ms"] for row in rounds
                   if isinstance(row["decision_save_ms"], int)]
    if any(row["decision_save_ms"] == INCOMPLETE for row in rounds if row["has_adopted_content"]):
        cumulative: Any = INCOMPLETE
    elif save_values:
        cumulative = sum(save_values)
    else:
        cumulative = NOT_APPLICABLE

    written = list(observed_outcomes.get("written_paths") or [])
    if not written:
        written = [path for row in rounds for path in row.get("adopted_paths", []) + row.get("sync_paths", [])]
    required = list(expected_outcomes.get("required_paths") or [])
    must_sync = bool(expected_outcomes.get("must_sync_spec"))
    semantics = observed_outcomes.get("semantics_matched")
    sync_ok = any(_is_sync_target(path) for path in written)
    comparable = True
    reason = ""
    if must_sync and not sync_ok:
        comparable = False
        reason = "未完成最终规格同步,成果范围与约定不一致"
        exceptions.append({"kind": "incomparable", "detail": reason})
    if required and not all(any(req in path or path.endswith(req) for path in written) for req in required):
        comparable = False
        reason = reason or "约定成果文件未全部出现"
        if not any(item["kind"] == "incomparable" for item in exceptions):
            exceptions.append({"kind": "incomparable", "detail": reason})
    if semantics is False:
        comparable = False
        reason = reason or "优化前未能完成相同成果语义"
        if not any(item["kind"] == "incomparable" for item in exceptions):
            exceptions.append({"kind": "incomparable", "detail": reason})
    if observed_outcomes.get("candidate_error"):
        exceptions.append({"kind": "candidate_error",
                           "detail": str(observed_outcomes.get("candidate_error"))})
    if not comparable:
        # 规格:未完成保存或同步的本次只能记为未完成,不得把短时长当效率基准。
        processing = INCOMPLETE

    steps = _count_steps(turns)
    steps["tokens"] = _usage_tokens(all_events)

    return {
        "status": "measured" if processing != INCOMPLETE else "incomplete",
        "exceptions": exceptions,
        "rounds": rounds,
        "module": {
            "processing_ms": processing,
            "cumulative_decision_save_ms": cumulative,
            "request_at_ms": start,
            "finished_at_ms": end,
            "user_wait_ms_deducted": deducted,
        },
        "steps": steps,
        "comparability": {"comparable": comparable, "reason": reason},
    }


def record_baseline_identity(
    plugin_root: str | Path,
    *,
    host: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """记录优化前内容身份。以插件文件 SHA-256 为准,不以 Git 标签为前提。"""

    root = Path(plugin_root)
    manifest = json.loads((root / ".codex-plugin" / "plugin.json").read_text(encoding="utf-8"))
    content: dict[str, str] = {}
    for rel in _IDENTITY_FILES:
        path = root / rel
        if path.is_file():
            content[rel] = hashlib.sha256(path.read_bytes()).hexdigest()
    tree_parts = []
    for path in sorted(p for p in root.rglob("*") if p.is_file()):
        if "__pycache__" in path.parts or path.suffix == ".pyc":
            continue
        rel = path.relative_to(root).as_posix()
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        tree_parts.append(f"{rel} {digest}")
    return {
        "plugin_version": manifest.get("version"),
        "content_sha256": content,
        "plugin_tree_sha256": hashlib.sha256(
            "\n".join(tree_parts).encode("utf-8")).hexdigest(),
        "git_tag": UNKNOWN,
        "host": host or {},
        "tools": ["mgs_scope", "mgs_write", "mgs_remote"],
        "permissions": {
            "sandbox": "workspace-write",
            "write_channel": "mgs-gate",
        },
        "model": UNKNOWN,
        "reasoning": UNKNOWN,
        "note": "优化前内容身份按插件文件 SHA-256 固定;后续实现不得覆盖本记录。"
                "不以创建 Git 提交或标签为前提。",
    }


def _cli(argv: list[str]) -> int:
    if len(argv) < 2 or argv[1] in {"-h", "--help"}:
        print("usage: design_discussion_metrics.py measure|identity [options]",
              file=sys.stderr)
        return 2
    action = argv[1]
    args = argv[2:]

    def opt(flag: str, default: str | None = None) -> str | None:
        if flag in args:
            return args[args.index(flag) + 1]
        return default

    if action == "identity":
        plugin = Path(opt("--plugin") or Path(__file__).resolve().parents[2] / "plugin")
        host_raw = opt("--host")
        host = json.loads(host_raw) if host_raw else {}
        report = record_baseline_identity(plugin, host=host)
        out = opt("--out")
        text = json.dumps(report, ensure_ascii=False, indent=2)
        if out:
            out_path = Path(out)
            out_path.parent.mkdir(parents=True, exist_ok=True)
            out_path.write_text(text + "\n", encoding="utf-8")
        else:
            print(text)
        return 0

    if action == "measure":
        turns_arg = opt("--turns")
        if not turns_arg:
            print("measure 需要 --turns a.jsonl,b.jsonl", file=sys.stderr)
            return 2
        turns = [{"events": load_jsonl(part)} for part in turns_arg.split(",") if part]
        waits: list[tuple[int, int]] = []
        raw_waits = opt("--user-wait")
        if raw_waits:
            for chunk in raw_waits.split(","):
                start_s, end_s = chunk.split(":", 1)
                waits.append((int(start_s), int(end_s)))
        expected = json.loads(Path(opt("--expected")).read_text(encoding="utf-8")) if opt("--expected") else {}
        observed = json.loads(Path(opt("--observed")).read_text(encoding="utf-8")) if opt("--observed") else {}
        report = measure_module_run(
            turns, user_wait_intervals=waits,
            expected_outcomes=expected, observed_outcomes=observed)
        out = opt("--out")
        text = json.dumps(report, ensure_ascii=False, indent=2)
        if out:
            out_path = Path(out)
            out_path.parent.mkdir(parents=True, exist_ok=True)
            out_path.write_text(text + "\n", encoding="utf-8")
        else:
            print(text)
        return 0

    print(f"未知动作: {action}", file=sys.stderr)
    return 2


if __name__ == "__main__":
    sys.exit(_cli(sys.argv))

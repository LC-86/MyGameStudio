#!/usr/bin/env python3
"""本地 Markdown 任务写接缝(issue #51)。

与 GitHub 后端同一套任务正文规则;普通本地工作不经 mgs-gate。
分流(五类标签)与生命周期(进度/关闭原因)分开记录。认领、父子、依赖、
关闭原因写在任务字段里。并发重叠时保留双方成果并暂停覆盖;取消后不
恢复已撤销动作;结果未知时先回读,只补缺项。
"""

from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

try:
    import fcntl
except ImportError:  # pragma: no cover - POSIX lock is the production path
    fcntl = None

sys.path.insert(0, str(Path(__file__).resolve().parent))

from mgs_record_model import (  # noqa: E402
    CANONICAL_LABELS, IDENTITY_RE, RecordsError, edit_body, parse_task_body,
    today)
from mgs_record_source import _task_root, local_read_task, local_task_dir  # noqa: E402

CLOSE_REASONS = ("完成", "不再执行", "已有成果覆盖")
CLOSE_PROGRESS = {
    "完成": "已完成",
    "不再执行": "不再执行",
    "已有成果覆盖": "已完成(已有成果覆盖)",
}
CLOSE_NOTE = "关闭任务不自动等于验证通过;验收以任务记录的验收方式与实际证据为准。"
UNCLAIMED = "未认领"


def _sha(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _lock_exclusive(handle) -> None:
    if fcntl is None:
        return
    fcntl.flock(handle.fileno(), fcntl.LOCK_EX)


def render_task_body(title: str, identity: str, triage: str, progress: str,
                     request: dict, *, claim: str = UNCLAIMED,
                     close_reason: str = "无",
                     index: str = "(暂无)",
                     change: str | None = None) -> str:
    header = (f"任务身份:{identity}。当前分流:{triage}。进度:{progress}。"
              f"认领:{claim}。关闭原因:{close_reason}。")
    lines = [f"# {title}", "", header, "", "## 工作请求", ""]
    for key, value in request.items():
        lines.append(f"- {key}:{value}")
    lines += ["", "## 结果索引", "", index, "", "## 状态变化", "",
              change or f"{today()} 经本地 Markdown 接口建立任务记录。", ""]
    return "\n".join(lines)


def _recovery_dir(root: Path, config: dict) -> Path:
    return root / "docs" / "mygamestudio" / "records" / "recovery"


def _cancelled_path(root: Path, config: dict) -> Path:
    return _recovery_dir(root, config) / "cancelled-ops.json"


def load_cancelled(root: Path, config: dict) -> list[dict]:
    path = _cancelled_path(root, config)
    if not path.is_file():
        return []
    return json.loads(path.read_text(encoding="utf-8"))


def _save_cancelled(root: Path, config: dict, entries: list[dict]) -> None:
    path = _cancelled_path(root, config)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(entries, ensure_ascii=False, indent=2) + "\n",
                    encoding="utf-8")


class LocalMarkdownBackend:
    """本地 Markdown 任务写 adapter。调用方经 mgs_records 公开接缝使用。"""

    def __init__(self, project_root: Path | str, config: dict) -> None:
        self.root = Path(project_root)
        self.config = config
        self.task_root = _task_root(self.root, config)

    def _task_dir(self, identity: str) -> Path:
        return local_task_dir(self.root, self.config, identity)

    def _task_path(self, identity: str) -> Path:
        return self._task_dir(identity) / "task.md"

    def _assert_not_cancelled(self, op: str, identity: str) -> None:
        for entry in load_cancelled(self.root, self.config):
            if entry.get("op") == op and entry.get("identity") == identity \
                    and entry.get("status") == "cancelled":
                raise RecordsError(
                    f"已撤销动作 {op}:{identity} 不得恢复或重放")

    def _read_text(self, identity: str) -> str:
        path = self._task_path(identity)
        if not path.is_file():
            raise RecordsError(f"任务不存在或缺少 task.md:{path}")
        return path.read_text(encoding="utf-8")

    def read_task(self, identity: str) -> dict:
        return local_read_task(self.root, self.config, identity)

    def create_task(self, identity: str, title: str, request: dict, *,
                    triage: str = "needs-triage",
                    progress: str = "待执行") -> dict:
        self._assert_not_cancelled("create_task", identity)
        if not identity or not IDENTITY_RE.fullmatch(identity):
            raise RecordsError(
                f"任务身份必须形如 NN-<slug>,当前 {identity!r}")
        if triage not in CANONICAL_LABELS:
            raise RecordsError(f"分流 {triage!r} 不在五类之内")
        path = self._task_path(identity)
        if path.is_file():
            existing = self.read_task(identity)
            return {"created": False, "adopted": True,
                    "duplicate_avoided": True, "readback": existing,
                    "attempts": [{"step": "read-first", "outcome": "exists"}]}
        body = render_task_body(title, identity, triage, progress, request)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(body, encoding="utf-8")
        return {"created": True, "adopted": False, "duplicate_avoided": False,
                "readback": self.read_task(identity),
                "attempts": [{"step": "create-1", "outcome": "created"}]}

    def update_task(self, identity: str, fields: dict, *,
                    expected_body_sha256: str | None = None,
                    change_note: str = "安排更新") -> dict:
        self._assert_not_cancelled("update_task", identity)
        path = self._task_path(identity)
        if not path.is_file():
            raise RecordsError(f"任务不存在或缺少 task.md:{path}")
        with path.open("r+", encoding="utf-8") as handle:
            _lock_exclusive(handle)
            current = handle.read()
            current_sha = _sha(current)
            if expected_body_sha256 is not None \
                    and expected_body_sha256.lower() != current_sha:
                overlap = self._task_dir(identity) / f"task.md.overlap-{current_sha[:8]}"
                overlap.write_text(
                    json.dumps({"fields": fields, "change_note": change_note,
                                "expected": expected_body_sha256,
                                "current": current_sha},
                               ensure_ascii=False, indent=2) + "\n",
                    encoding="utf-8")
                raise RecordsError(
                    f"正文已被他人修改:expected sha256 {expected_body_sha256} "
                    f"!= 当前 {current_sha};已保留双方成果并暂停覆盖")
            header_updates = {key: value for key, value in fields.items()
                              if key in ("进度", "当前分流", "认领", "关闭原因")}
            request_updates = {key: value for key, value in fields.items()
                               if key not in header_updates}
            new_body = edit_body(
                current, header=header_updates, request=request_updates,
                append_change=f"{today()} {change_note}:{'、'.join(fields)}")
            handle.seek(0)
            handle.truncate()
            handle.write(new_body)
            handle.flush()
        return {"published": True, "readback": self.read_task(identity),
                "attempts": [{"step": "patch", "outcome": "updated"}]}

    def set_triage(self, identity: str, label: str) -> dict:
        if label not in CANONICAL_LABELS:
            raise RecordsError(f"分流 {label!r} 不在五类之内")
        return self.update_task(identity, {"当前分流": label},
                                change_note=f"分流调整为 {label}")

    def set_relations(self, identity: str, deps: list[str]) -> dict:
        from mgs_record_source import local_list_tasks  # noqa: PLC0415

        known = {task["identity"] for task in local_list_tasks(self.root, self.config)}
        missing = [dep for dep in deps if dep not in known]
        if missing:
            raise RecordsError(f"依赖任务不存在:{missing}(引用必须可解析)")
        value = "、".join(deps) or "无"
        return self.update_task(identity, {"依赖": value}, change_note="设置依赖")

    def set_parent(self, identity: str, parent_id: str | None) -> dict:
        if parent_id is None:
            result = self.update_task(identity, {"父任务": "无"},
                                      change_note="解除父任务")
            result["mode"] = "body-reference"
            return result
        try:
            self.read_task(parent_id)
        except RecordsError as exc:
            raise RecordsError(f"父任务不存在:{parent_id}") from exc
        result = self.update_task(identity, {"父任务": parent_id},
                                  change_note="设置父任务")
        result["mode"] = "body-reference"
        return result

    def claim_task(self, identity: str, actor: str) -> dict:
        current = parse_task_body(self._read_text(identity))
        holder = current.get("claim") or UNCLAIMED
        if holder not in ("", UNCLAIMED) and holder != actor:
            raise RecordsError(
                f"任务已由 {holder} 认领,不覆盖他人认领")
        return self.update_task(identity, {"认领": actor}, change_note="认领")

    def append_result(self, identity: str, result_markdown: str) -> dict:
        """追加结果。文件名分配、结果写入与索引更新持同一任务锁完成:
        并发投递不得算出同一文件名互相覆盖,也不得丢失对方的索引行。"""

        self._assert_not_cancelled("append_result", identity)
        task_dir = self._task_dir(identity)
        task_path = self._task_path(identity)
        if not task_path.is_file():
            raise RecordsError(f"任务不存在或缺少 task.md:{task_path}")
        with task_path.open("r+", encoding="utf-8") as handle:
            _lock_exclusive(handle)
            current = handle.read()
            parsed = parse_task_body(current)
            stamp = today()
            name = f"{stamp}.md"
            results_dir = task_dir / "results"
            path = results_dir / name
            index = 1
            while path.exists():
                name = f"{stamp}-{index}.md"
                path = results_dir / name
                index += 1
            results_dir.mkdir(parents=True, exist_ok=True)
            body = result_markdown
            if identity not in body:
                body = f"任务:{identity}\n\n{result_markdown}"
            path.write_text(body if body.endswith("\n") else body + "\n",
                            encoding="utf-8")
            index_text = parsed.get("result_index_text", "").strip()
            line = f"- results/{name}"
            if name not in index_text:
                new_index = (index_text + "\n" if index_text
                             and index_text != "(暂无)" else "") + line
                new_body = edit_body(current, index_lines=new_index.splitlines(),
                                     append_change=f"{today()} 追加结果 {name}")
                handle.seek(0)
                handle.truncate()
                handle.write(new_body)
                handle.flush()
        return {"published": True, "path": f"results/{name}",
                "readback": self.read_task(identity)}

    def close_task(self, identity: str, reason: str, note: str = "") -> dict:
        if reason not in CLOSE_REASONS:
            raise RecordsError(
                f"关闭原因必须限定三类(完成/不再执行/已有成果覆盖),当前 {reason!r}")
        progress = CLOSE_PROGRESS[reason]
        result = self.update_task(
            identity, {"进度": progress, "关闭原因": reason},
            change_note=f"关闭({reason})")
        result["close_reason"] = reason
        result["note"] = CLOSE_NOTE
        if note:
            result["close_note"] = note
        return result

    def cancel_operation(self, op: str, identity: str, *,
                         note: str = "") -> dict:
        entries = load_cancelled(self.root, self.config)
        entries.append({"op": op, "identity": identity, "status": "cancelled",
                        "at": today(), "note": note})
        _save_cancelled(self.root, self.config, entries)
        path = self._task_path(identity)
        preserved = path.is_file()
        return {"cancelled": True, "op": op, "identity": identity,
                "preserved": preserved, "restored": False}

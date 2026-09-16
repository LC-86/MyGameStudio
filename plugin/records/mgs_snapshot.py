#!/usr/bin/env python3
"""正式版本设计快照公开接缝(issue #54)。

在正式版本节点把现行规格另存为归档,不改写现行正文(仅整体入口追加
版本索引)。历史快照不参与现行内容同步。两种 tracker 分别实现完整路径;
普通路径不经 mgs-gate。

公开 interface(经 mgs_records 再导出):
  plan_design_snapshot(project_root, request, ...) -> dict
  apply_design_snapshot(project_root, plan, ...) -> dict
  read_design_snapshots(project_root, ...) -> dict
"""

from __future__ import annotations

import hashlib
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from mgs_backend_options import BackendOptions  # noqa: E402
from mgs_record_model import RecordsError, today  # noqa: E402
from mgs_record_source import DEFAULT_CONFIG_REL  # noqa: E402
import mgs_spec  # noqa: E402

SNAPSHOT_MARK = "快照身份:"
SNAPSHOT_HEADING = "正式版本设计快照"
SNAPSHOT_DIR = "docs/mygamestudio/records/design-snapshots"
TRIGGERS_ARCHIVE = ("version_freeze", "explicit")
NO_CLAIM = "归档是维护约定,不宣称不可篡改、权限隔离或自动备份。"
DESIGN_ID_RE = re.compile(r"^[A-Za-z0-9_-]+$")
REVISION_RE = re.compile(r"^r\d+$")


def _snapshot_ids_error(design_id: str, revision: str) -> str:
    """快照身份与修订直接拼进归档目录路径,越界取值一律拒绝。"""

    if not DESIGN_ID_RE.fullmatch(str(design_id or "")):
        return f"非法 design_id:{design_id or '(空)'}"
    if not REVISION_RE.fullmatch(str(revision or "")):
        return f"非法 revision:{revision or '(空)'}"
    resolved = Path(SNAPSHOT_DIR) / design_id / revision
    try:
        resolved.relative_to(Path(SNAPSHOT_DIR))
    except ValueError:
        return f"快照目录越界:{design_id}/{revision}"
    return ""


def design_id_for_history_version(version: str, assigned: dict[str, str],
                                  fallback: int) -> str:
    """Stable unique snapshot id from the complete version string."""

    version = str(version or "v1")
    if version in assigned:
        return assigned[version]
    slug = re.sub(r"[^A-Za-z0-9_-]+", "-", version).strip("-") or str(fallback)
    candidate = f"ds-{slug}"
    used = set(assigned.values())
    if candidate in used:
        suffix = 2
        while f"{candidate}-{suffix}" in used:
            suffix += 1
        candidate = f"{candidate}-{suffix}"
    assigned[version] = candidate
    return candidate


def design_ids_for_history(items: list[dict]) -> list[str]:
    assigned: dict[str, str] = {}
    return [
        design_id_for_history_version(
            item.get("version") or "v1", assigned, index + 1)
        for index, item in enumerate(items)
    ]


def _sha(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _source_fingerprint(current: dict) -> str:
    parts = [current.get("overall") or ""]
    modules = current.get("modules") or {}
    for name in sorted(modules):
        parts.append(name)
        parts.append(modules[name])
    return _sha("\n".join(parts))


def _next_revision(existing: list[dict]) -> str:
    numbers = []
    for item in existing:
        match = re.match(r"r(\d+)$", str(item.get("revision") or ""))
        if match:
            numbers.append(int(match.group(1)))
    return f"r{(max(numbers) + 1) if numbers else 1}"


def _next_design_id(existing: list[dict]) -> str:
    numbers = []
    for item in existing:
        match = re.match(r"ds-(\d+)$", str(item.get("design_id") or ""))
        if match:
            numbers.append(int(match.group(1)))
    return f"ds-{(max(numbers) + 1) if numbers else 1}"


def _latest_revision_snapshot(snapshots: list[dict],
                              design_id: str) -> dict | None:
    """同一 design_id 的现行修订是编号最高的 rN:更低编号已被替代。"""

    best: dict | None = None
    best_number = -1
    for item in snapshots:
        if item.get("design_id") != design_id:
            continue
        match = re.match(r"r(\d+)$", str(item.get("revision") or ""))
        if not match:
            continue
        number = int(match.group(1))
        if number > best_number:
            best, best_number = item, number
    return best


def _attachment_rel(rel: str) -> str:
    parts = []
    for part in Path(str(rel or "")).parts:
        if part in (".", ""):
            continue
        if part == "..":
            continue
        parts.append(part)
    return "/".join(parts) if parts else "attachment"


def _attachment_name(rel: str) -> str:
    return _attachment_rel(rel)


def _read_attachment(root: Path, rel: str) -> tuple[str | None, str]:
    """附件只允许项目内相对路径:越界来源(绝对路径/../软链出根)不读。"""

    source = Path(str(rel or ""))
    if source.is_absolute() or ".." in source.parts:
        return None, f"附件路径越界:{rel}"
    path = root / source
    try:
        path.resolve().relative_to(root.resolve())
    except ValueError:
        return None, f"附件路径越界:{rel}"
    if not path.is_file():
        return None, f"附件缺失:{rel}"
    try:
        return path.read_text(encoding="utf-8"), ""
    except UnicodeDecodeError:
        return None, f"附件无法按当时完整内容读取:{rel}"


def _implementation_status(request: dict) -> str:
    record = str(request.get("build_record") or request.get("implementation") or "")
    if record and record not in ("未实现", "unimplemented"):
        return record
    return "未实现"


def _release_status(request: dict) -> str:
    record = str(request.get("release_record") or request.get("release") or "")
    if record and record not in ("未发布", "unpublished"):
        return record
    return "未发布"


def plan_design_snapshot(project_root: Path | str, request: dict,
                         config_rel: str = DEFAULT_CONFIG_REL, *,
                         transport=None, api_base: str | None = None,
                         cache_dir: Path | str | None = None) -> dict:
    """整理正式版本快照计划。日常修改不强制生成;不写入。"""

    current = mgs_spec.read_current_design(
        project_root, config_rel, transport=transport, api_base=api_base,
        cache_dir=cache_dir)
    trigger = str(request.get("trigger") or "")
    listed = read_design_snapshots(
        project_root, config_rel, transport=transport, api_base=api_base,
        cache_dir=cache_dir)
    existing = listed.get("snapshots") or []
    reuse_id = str(request.get("reuse_design_id") or request.get("reuse") or "")
    if reuse_id:
        match = _latest_revision_snapshot(existing, reuse_id)
        return {
            "wrote": False,
            "should_snapshot": False,
            "reuse": True,
            "design_id": reuse_id,
            "revision": (match or {}).get("revision") or "r1",
            "game_version": str(request.get("game_version") or ""),
            "implementation": _implementation_status(request),
            "release": _release_status(request),
            "backend": current.get("backend"),
            "gate_required": False,
            "request": dict(request),
        }
    if trigger not in TRIGGERS_ARCHIVE:
        return {
            "wrote": False,
            "should_snapshot": False,
            "reason": "日常修改不强制生成快照",
            "backend": current.get("backend"),
            "gate_required": False,
            "request": dict(request),
        }
    design_id = str(request.get("design_id") or "") or _next_design_id(existing)
    correction = bool(request.get("correction"))
    if correction:
        base = str(request.get("design_id") or "")
        prev = [item for item in existing if item.get("design_id") == base]
        # 修正是对已存在基准修订的另存;无已知基准(未指 design_id 或
        # 指向的基准不存在)时按 r1 归档会把首修订伪装成修正,直接拒绝。
        if not base or not prev:
            return {
                "wrote": False,
                "should_snapshot": False,
                "invalid": True,
                "reason": ("修正无已知基准修订,不得按 r1 归档:"
                           f"{base or '(未指定 design_id)'}"),
                "backend": current.get("backend"),
                "gate_required": False,
                "request": dict(request),
            }
        revision = _next_revision(prev)
        design_id = base
    else:
        revision = "r1"
    ids_error = _snapshot_ids_error(design_id, revision)
    if ids_error:
        return {
            "wrote": False,
            "should_snapshot": False,
            "invalid": True,
            "reason": ids_error,
            "backend": current.get("backend"),
            "gate_required": False,
            "request": dict(request),
        }
    attachments = [str(item) for item in (request.get("attachments") or [])]
    return {
        "wrote": False,
        "should_snapshot": True,
        "reuse": False,
        "design_id": design_id,
        "revision": revision,
        "game_version": str(request.get("game_version") or ""),
        "source": str(request.get("source") or "正式版本设计确定"),
        "reason": str(request.get("reason") or ""),
        "replaces": str(request.get("replaces") or request.get("replaces_revision") or ""),
        "correction": correction,
        "attachments": attachments,
        "implementation": _implementation_status(request),
        "release": _release_status(request),
        "source_sha256": _source_fingerprint(current),
        "backend": current.get("backend"),
        "gate_required": False,
        "current_overall": current.get("overall") or "",
        "current_modules": dict(current.get("modules") or {}),
        "request": dict(request),
    }


def apply_design_snapshot(project_root: Path | str, plan: dict, *,
                          confirmed: bool = True,
                          config_rel: str = DEFAULT_CONFIG_REL,
                          transport=None, api_base: str | None = None,
                          cache_dir: Path | str | None = None) -> dict:
    """把现行规格另存为归档快照。未确认或日常路径不写。"""

    options = BackendOptions(config_rel=config_rel, transport=transport,
                             api_base=api_base, cache_dir=cache_dir)
    if not confirmed:
        return {"ok": False, "wrote": False, "complete": False,
                "reason": "未确认,不写入归档"}
    if plan.get("invalid"):
        return {"ok": False, "wrote": False, "complete": False,
                "reason": plan.get("reason") or "快照身份非法",
                "gate_required": False}
    if plan.get("reuse"):
        return _associate_game_version(project_root, plan, options=options)
    if not plan.get("should_snapshot"):
        return {
            "ok": True, "wrote": False, "complete": False, "skipped": True,
            "reason": plan.get("reason") or "日常修改不强制生成快照",
            "gate_required": False,
        }
    # 手工构造的 plan 同样校验:身份/修订会直接拼进本地归档目录路径。
    ids_error = _snapshot_ids_error(
        str(plan.get("design_id") or ""), str(plan.get("revision") or ""))
    if ids_error:
        return {"ok": False, "wrote": False, "complete": False,
                "reason": ids_error, "gate_required": False}
    root, config = mgs_spec._config(project_root, config_rel)
    if config.get("backend") == "local-markdown":
        return _apply_local_snapshot(root, config, plan, config_rel=config_rel)
    if config.get("backend") == "github-issues":
        return _apply_github_snapshot(root, config, plan, options=options)
    raise RecordsError(f"后端 {config.get('backend')} 未实现")


def read_design_snapshots(project_root: Path | str,
                          config_rel: str = DEFAULT_CONFIG_REL, *,
                          transport=None, api_base: str | None = None,
                          cache_dir: Path | str | None = None) -> dict:
    """只读归档快照。历史快照不参与现行内容同步。"""

    root, config = mgs_spec._config(project_root, config_rel)
    if config.get("backend") == "local-markdown":
        return _read_local_snapshots(root, config)
    if config.get("backend") == "github-issues":
        return _read_github_snapshots(
            config, options=BackendOptions(
                config_rel=config_rel, transport=transport,
                api_base=api_base, cache_dir=cache_dir))
    raise RecordsError(f"后端 {config.get('backend')} 未实现")


def _read_local_snapshots(root: Path, config: dict) -> dict:
    base = root / SNAPSHOT_DIR
    snapshots: list[dict] = []
    if base.is_dir():
        # 写入侧接受全部符合 ID 语法的 design_id(不强制 ds- 前缀);
        # 读取侧按同一语法枚举,否则自定义 ID 的归档会从读取 API 消失。
        for design_dir in sorted(p for p in base.iterdir()
                                 if p.is_dir()
                                 and DESIGN_ID_RE.fullmatch(p.name)):
            for rev_dir in sorted(p for p in design_dir.iterdir() if p.is_dir()):
                snap = _load_local_revision(root, design_dir.name, rev_dir)
                if snap:
                    snapshots.append(snap)
    current_rel = mgs_spec._design_rel(config)
    overall = ""
    path = root / current_rel
    if path.is_file():
        overall = path.read_text(encoding="utf-8")
    return {
        "wrote": False,
        "backend": "local-markdown",
        "snapshots": snapshots,
        "index_in_overall": SNAPSHOT_HEADING in overall,
        "gate_required": False,
    }


def _load_local_revision(root: Path, design_id: str, rev_dir: Path) -> dict | None:
    overall_path = rev_dir / "overall.md"
    if not overall_path.is_file():
        return None
    modules: dict[str, str] = {}
    module_root = rev_dir / "modules"
    if module_root.is_dir():
        for path in sorted(module_root.glob("*.md")):
            modules[path.stem] = path.read_text(encoding="utf-8")
    attachments: dict[str, str] = {}
    attach_root = rev_dir / "attachments"
    if attach_root.is_dir():
        for path in sorted(attach_root.rglob("*")):
            if path.is_file():
                attachments[str(path.relative_to(attach_root))] = (
                    path.read_text(encoding="utf-8"))
    meta = ""
    meta_path = rev_dir / "meta.md"
    if meta_path.is_file():
        meta = meta_path.read_text(encoding="utf-8")
    game_versions = _field_list(meta, "游戏版本")
    return {
        "design_id": design_id,
        "revision": rev_dir.name,
        "game_versions": game_versions,
        "formed_at": _meta_field(meta, "形成时间"),
        "source": _meta_field(meta, "来源"),
        "implementation": _meta_field(meta, "实现") or "未实现",
        "release": _meta_field(meta, "发布") or "未发布",
        "reason": _meta_field(meta, "修正原因"),
        "replaces": _meta_field(meta, "采用关系"),
        "overall": overall_path.read_text(encoding="utf-8"),
        "modules": modules,
        "attachments": attachments,
        "meta": meta,
        "path": str(rev_dir.relative_to(root)),
        "complete": bool(_meta_field(meta, "形成时间")),
    }


def _meta_field(text: str, name: str) -> str:
    match = re.search(rf"{re.escape(name)}\s*[:：]\s*([^\n。]+)", text or "")
    return match.group(1).strip() if match else ""


def _field_list(text: str, name: str) -> list[str]:
    raw = _meta_field(text, name)
    if not raw:
        return []
    return [part.strip() for part in raw.split(",") if part.strip()]


def _render_meta(plan: dict, *, formed_at: str) -> str:
    versions = [item for item in [plan.get("game_version") or ""] if item]
    lines = [
        f"# {SNAPSHOT_HEADING} {plan.get('design_id')} {plan.get('revision')}",
        "",
        f"{SNAPSHOT_MARK}{plan.get('design_id')}。修订:{plan.get('revision')}。"
        "种类:归档快照。不是现行规格。",
        f"游戏版本:{', '.join(versions)}",
        f"形成时间:{formed_at}",
        f"来源:{plan.get('source') or ''}",
        f"实现:{plan.get('implementation') or '未实现'}",
        f"发布:{plan.get('release') or '未发布'}",
    ]
    if plan.get("reason"):
        lines.append(f"修正原因:{plan.get('reason')}")
    if plan.get("replaces"):
        lines.append(f"采用关系:本修订替代 {plan.get('replaces')}")
    lines += ["", NO_CLAIM, ""]
    return "\n".join(lines)


def _index_line(plan: dict, *, location: str) -> str:
    game = plan.get("game_version") or ""
    reuse = "复用" if plan.get("reuse") else ""
    impl = plan.get("implementation") or "未实现"
    rel = plan.get("release") or "未发布"
    prefix = (f"游戏版本 {game}：{reuse}设计 {plan.get('design_id')} "
              f"修订 {plan.get('revision')}")
    return f"{prefix}（{location}；实现:{impl}；发布:{rel}）"


def _upsert_index_section(text: str, line: str) -> str:
    heading = f"## {SNAPSHOT_HEADING}"
    bullet = f"- {line}"
    if heading not in (text or ""):
        return (text or "").rstrip() + f"\n\n{heading}\n\n{bullet}\n"
    before, after = text.split(heading, 1)
    rest = after
    next_head = re.search(r"\n## ", rest)
    if next_head:
        section, tail = rest[:next_head.start()], rest[next_head.start():]
    else:
        section, tail = rest, ""
    if bullet in section:
        return text
    section = section.rstrip() + f"\n{bullet}\n"
    return before + heading + section + tail


def _missing_module_refs(root: Path, overall: str, modules: dict) -> list[str]:
    section = mgs_spec._section(overall, "模块")
    missing = []
    for line in section.splitlines():
        text = line.lstrip("- ").strip()
        if not text:
            continue
        if "：" not in text and ":" not in text:
            continue
        name, ref = re.split(r"[：:]", text, 1)
        ref = ref.strip()
        if ref.endswith(".md") or ref.startswith("docs/"):
            path = root / ref.split()[0]
            if not path.is_file():
                missing.append(ref.split()[0])
        else:
            # 身份引用逐个核对:只要还有任一模块可读就放行缺项,归档会
            # 静默丢失个别模块仍宣称完整。
            match = re.match(r"规格身份\s+([A-Za-z0-9_-]+)", ref)
            key = match.group(1) if match else name.strip()
            if key and key not in modules:
                missing.append(name.strip() or key)
    return missing


def _collect_attachments(root: Path, plan: dict) -> tuple[dict[str, str] | None, str]:
    attachments: dict[str, str] = {}
    seen: dict[str, str] = {}
    for rel in plan.get("attachments") or []:
        key = _attachment_rel(rel)
        if key in seen and seen[key] != rel:
            return None, f"附件路径碰撞:{seen[key]} 与 {rel}"
        seen[key] = rel
        text, err = _read_attachment(root, rel)
        if err:
            return None, err
        attachments[key] = text or ""
    return attachments, ""


def _apply_local_snapshot(root: Path, config: dict, plan: dict, *,
                          config_rel: str) -> dict:
    current = mgs_spec.read_current_design(root, config_rel)
    overall = current.get("overall") or ""
    modules = dict(current.get("modules") or {})
    design_id = str(plan.get("design_id") or "ds-1")
    revision = str(plan.get("revision") or "r1")
    rev_dir = root / SNAPSHOT_DIR / design_id / revision
    try:
        rev_dir.relative_to(root / SNAPSHOT_DIR)
    except ValueError:
        return {
            "ok": False, "wrote": False, "complete": False,
            "reason": f"快照目录越界:{design_id}/{revision}",
            "gate_required": False,
        }
    existing = rev_dir.is_dir() and (rev_dir / "overall.md").is_file()
    if existing and plan.get("correction"):
        return {
            "ok": False, "wrote": False, "complete": False,
            "reason": f"修订 {revision} 已占用,不得覆盖",
            "design_id": design_id, "revision": revision,
            "gate_required": False,
        }
    if existing and not plan.get("correction"):
        if _revision_is_complete(rev_dir, plan, modules):
            _ensure_overall_index(root, config, plan, rev_dir)
            return {
                "ok": True, "wrote": True, "complete": True,
                "filled_gap_only": True,
                "design_id": design_id, "revision": revision,
                "backend": "local-markdown", "gate_required": False,
                "path": str(rev_dir.relative_to(root)),
            }
        expected = plan.get("source_sha256")
        actual = _source_fingerprint(current)
        saved_overall = (rev_dir / "overall.md").read_text(encoding="utf-8")
        source_ok = (not expected or expected == actual) and saved_overall == overall
        if source_ok:
            attachments, err = _collect_attachments(root, plan)
            if err:
                return {
                    "ok": False, "wrote": True, "complete": False,
                    "reason": err, "gate_required": False,
                    "design_id": design_id, "revision": revision,
                }
            _fill_local_gaps(root, rev_dir, overall, modules, attachments)
            meta_path = rev_dir / "meta.md"
            meta_text = meta_path.read_text(encoding="utf-8") if meta_path.is_file() else ""
            if not _meta_field(meta_text, "形成时间"):
                meta_path.parent.mkdir(parents=True, exist_ok=True)
                meta_path.write_text(_render_meta(plan, formed_at=today()),
                                     encoding="utf-8")
        if not source_ok or not _revision_is_complete(rev_dir, plan, modules):
            return {
                "ok": False, "wrote": True, "complete": False,
                "reason": "生成期间来源改变,不能保存混合修订并宣称完整",
                "design_id": design_id, "revision": revision,
                "gate_required": False,
            }
        _ensure_overall_index(root, config, plan, rev_dir)
        return {
            "ok": True, "wrote": True, "complete": True,
            "filled_gap_only": True,
            "design_id": design_id, "revision": revision,
            "backend": "local-markdown", "gate_required": False,
            "path": str(rev_dir.relative_to(root)),
        }
    expected = plan.get("source_sha256")
    actual = _source_fingerprint(current)
    if expected and expected != actual:
        return {
            "ok": False, "wrote": False, "complete": False,
            "reason": "生成期间来源改变,不能保存混合修订并宣称完整",
            "gate_required": False,
        }
    missing_refs = _missing_module_refs(root, overall, modules)
    if missing_refs:
        return {
            "ok": False, "wrote": False, "complete": False,
            "reason": f"缺模块:{', '.join(missing_refs)}",
            "gate_required": False,
        }
    attachments, err = _collect_attachments(root, plan)
    if err:
        return {
            "ok": False, "wrote": False, "complete": False,
            "reason": err, "gate_required": False,
        }
    rev_dir.mkdir(parents=True, exist_ok=True)
    formed = today()
    writes = {
        rev_dir / "overall.md": overall,
        rev_dir / "meta.md": _render_meta(plan, formed_at=formed),
    }
    for name, body in modules.items():
        writes[rev_dir / "modules" / f"{name}.md"] = body
    for name, body in attachments.items():
        writes[rev_dir / "attachments" / name] = body
    for path, text in writes.items():
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")
        if path.read_text(encoding="utf-8") != text:
            return {
                "ok": False, "wrote": True, "complete": False,
                "reason": f"部分保存:{path.relative_to(root)} 回读失败",
                "design_id": design_id, "revision": revision,
                "gate_required": False,
            }
    _ensure_overall_index(root, config, plan, rev_dir)
    return {
        "ok": True, "wrote": True, "complete": True,
        "design_id": design_id, "revision": revision,
        "backend": "local-markdown",
        "path": str(rev_dir.relative_to(root)),
        "game_version": plan.get("game_version"),
        "implementation": plan.get("implementation"),
        "release": plan.get("release"),
        "gate_required": False,
    }


def _revision_is_complete(rev_dir: Path, plan: dict,
                          modules: dict[str, str] | None = None) -> bool:
    overall = rev_dir / "overall.md"
    meta = rev_dir / "meta.md"
    if not overall.is_file() or not overall.read_text(encoding="utf-8").strip():
        return False
    if not meta.is_file() or not _meta_field(meta.read_text(encoding="utf-8"), "形成时间"):
        return False
    # 设计模块与整体入口同属修订内容;中断后重试不得只凭
    # overall/meta 两文件就宣告修订完整。
    if modules is not None:
        module_dir = rev_dir / "modules"
        expected = {f"{name}.md": body for name, body in modules.items()}
        archived: set[str] = set()
        if module_dir.is_dir():
            archived = {item.name for item in module_dir.iterdir()
                        if item.is_file()}
        if archived != set(expected):
            return False
        for name, body in expected.items():
            path = module_dir / name
            if not path.is_file() or path.read_text(encoding="utf-8") != body:
                return False
    for rel in plan.get("attachments") or []:
        if not (rev_dir / "attachments" / _attachment_rel(rel)).is_file():
            return False
    return True


def _fill_local_gaps(root: Path, rev_dir: Path, overall: str,
                     modules: dict[str, str], attachments: dict[str, str]) -> None:
    mapping = {rev_dir / "overall.md": overall}
    for name, body in modules.items():
        mapping[rev_dir / "modules" / f"{name}.md"] = body
    for name, body in attachments.items():
        mapping[rev_dir / "attachments" / name] = body
    for path, text in mapping.items():
        if not path.is_file():
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(text, encoding="utf-8")


def _ensure_overall_index(root: Path, config: dict, plan: dict, rev_dir: Path) -> None:
    rel = mgs_spec._design_rel(config)
    path = root / rel
    current = path.read_text(encoding="utf-8") if path.is_file() else ""
    location = str(rev_dir.relative_to(root))
    updated = _upsert_index_section(current, _index_line(plan, location=location))
    if updated != current:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(updated, encoding="utf-8")


def _associate_game_version(project_root, plan, *, options: BackendOptions) -> dict:
    root, config = mgs_spec._config(project_root, options.config_rel)
    if config.get("backend") == "local-markdown":
        listed = _read_local_snapshots(root, config)
        match = _latest_revision_snapshot(
            listed.get("snapshots") or [], str(plan.get("design_id") or ""))
        if match is None:
            return {"ok": False, "wrote": False, "complete": False,
                    "reason": f"可复用快照不存在:{plan.get('design_id')}"}
        rev_dir = root / match["path"]
        meta_path = rev_dir / "meta.md"
        meta = meta_path.read_text(encoding="utf-8") if meta_path.is_file() else ""
        versions = _field_list(meta, "游戏版本")
        game = str(plan.get("game_version") or "")
        patched = meta
        changed = False
        if game and game not in versions:
            versions.append(game)
            patched = re.sub(
                r"游戏版本\s*[:：]\s*.+",
                f"游戏版本:{', '.join(versions)}",
                patched, count=1)
            changed = True
        # 版本已登记时同样要补齐实现/发布元数据:跳过替换却返回
        # complete 会让归档永远停在「未实现/未发布」。
        if plan.get("implementation") and _meta_field(
                patched, "实现") != str(plan.get("implementation")):
            patched = re.sub(
                r"实现\s*[:：]\s*.+",
                f"实现:{plan.get('implementation')}", patched, count=1)
            changed = True
        if plan.get("release") and _meta_field(
                patched, "发布") != str(plan.get("release")):
            patched = re.sub(
                r"发布\s*[:：]\s*.+",
                f"发布:{plan.get('release')}", patched, count=1)
            changed = True
        if changed:
            meta_path.write_text(patched, encoding="utf-8")
        back = meta_path.read_text(encoding="utf-8") if meta_path.is_file() else ""
        verified = (
            (not game or game in _field_list(back, "游戏版本"))
            and (not plan.get("implementation")
                 or _meta_field(back, "实现") == str(plan.get("implementation")))
            and (not plan.get("release")
                 or _meta_field(back, "发布") == str(plan.get("release"))))
        if not verified:
            return {
                "ok": False, "wrote": changed, "complete": False,
                "reuse": True, "design_id": plan.get("design_id"),
                "revision": match.get("revision"),
                "reason": "快照元数据回读未确认,不宣告关联完成",
                "backend": "local-markdown",
                "gate_required": False,
            }
        _ensure_overall_index(root, config, plan, rev_dir)
        return {
            "ok": True, "wrote": True, "complete": True, "reuse": True,
            "design_id": plan.get("design_id"),
            "revision": match.get("revision"),
            "game_version": game,
            "implementation": _meta_field(back, "实现")
            or plan.get("implementation"),
            "release": _meta_field(back, "发布") or plan.get("release"),
            "backend": "local-markdown",
            "gate_required": False,
        }
    return _associate_github_version(root, config, plan, options=options)


def _read_github_snapshots(config, *, options: BackendOptions) -> dict:
    backend = mgs_spec._github(
        config, transport=options.transport, api_base=options.api_base,
        cache_dir=options.cache_dir)
    try:
        items = mgs_spec._list_github_items(backend)
    except mgs_spec.TransportError as exc:
        return {
            "wrote": False, "backend": "github-issues", "snapshots": [],
            "unknown": True, "reason": str(exc), "gate_required": False,
        }
    snapshots = []
    for item in items:
        body = item.get("body") or ""
        if SNAPSHOT_MARK not in body:
            continue
        snapshots.append(_parse_github_snapshot(item))
    return {
        "wrote": False,
        "backend": "github-issues",
        "snapshots": snapshots,
        "gate_required": False,
    }


def _markdown_fence(text: str) -> str:
    longest = 2
    for match in re.finditer(r"`+", text or ""):
        longest = max(longest, len(match.group(0)))
    return "`" * (longest + 1)


def _wrap_markdown_fence(text: str) -> str:
    fence = _markdown_fence(text)
    return f"{fence}markdown\n{(text or '').strip()}\n{fence}"


def _extract_fenced_markdown(body: str, heading: str) -> str:
    match = re.search(
        rf"## {re.escape(heading)}\n+(`{{3,}})markdown\n(.*?)\n\1(?:\n|$)",
        body or "", re.S)
    return match.group(2).strip() if match else ""


def _extract_named_fenced_sections(body: str, prefix: str) -> dict[str, str]:
    found: dict[str, str] = {}
    pattern = (
        rf"## {re.escape(prefix)}:([^\n]+)\(当时完整内容\)\n+"
        r"(`{3,})markdown\n(.*?)\n\2(?:\n|$)"
    )
    for match in re.finditer(pattern, body or "", re.S):
        found[match.group(1).strip()] = match.group(3).strip()
    return found


def _parse_github_snapshot(item: dict) -> dict:
    body = item.get("body") or ""
    identity = ""
    match = re.search(r"快照身份\s*[:：]\s*([A-Za-z0-9_-]+)", body)
    if match:
        identity = match.group(1)
    revision = _meta_field(body, "修订") or "r1"
    return {
        "design_id": identity,
        "revision": revision,
        "game_versions": _field_list(body, "游戏版本"),
        "formed_at": _meta_field(body, "形成时间"),
        "source": _meta_field(body, "来源"),
        "implementation": _meta_field(body, "实现") or "未实现",
        "release": _meta_field(body, "发布") or "未发布",
        "reason": _meta_field(body, "修正原因"),
        "replaces": _meta_field(body, "采用关系"),
        "overall": _extract_fenced_markdown(body, "整体设计(当时完整内容)"),
        "modules": _extract_named_fenced_sections(body, "模块"),
        "attachments": _extract_named_fenced_sections(body, "附件"),
        "issue_number": item.get("number"),
        "complete": True,
    }


def _render_github_body(plan: dict, overall: str, modules: dict[str, str],
                        attachments: dict[str, str], *, formed_at: str) -> str:
    lines = [_render_meta(plan, formed_at=formed_at).rstrip(), ""]
    lines += ["## 整体设计(当时完整内容)", "",
              _wrap_markdown_fence(overall), ""]
    for name, body in modules.items():
        lines += [f"## 模块:{name}(当时完整内容)", "",
                  _wrap_markdown_fence(body), ""]
    for name, body in attachments.items():
        lines += [f"## 附件:{name}(当时完整内容)", "",
                  _wrap_markdown_fence(body), ""]
    return "\n".join(lines).rstrip() + "\n"


def _apply_github_snapshot(root: Path, config: dict, plan: dict, *,
                           options: BackendOptions) -> dict:
    denied = mgs_spec._ensure_write(config)
    if denied:
        return {"ok": False, "wrote": False, "complete": False, "reason": denied}
    backend = mgs_spec._github(
        config, transport=options.transport, api_base=options.api_base,
        cache_dir=options.cache_dir)
    existing = _find_github_revision(
        backend, plan.get("design_id"), plan.get("revision"))
    if existing is not None and plan.get("correction"):
        return {
            "ok": False, "wrote": False, "complete": False,
            "reason": f"修订 {plan.get('revision')} 已占用,不得覆盖",
            "design_id": plan.get("design_id"),
            "revision": plan.get("revision"),
            "issue_number": existing.get("number"),
            "gate_required": False,
        }
    if existing is not None and not plan.get("correction"):
        number = existing.get("number")
        body_text = existing.get("body") or ""
        current = mgs_spec.read_current_design(
            root, options.config_rel, transport=options.transport,
            api_base=options.api_base, cache_dir=options.cache_dir)
        expected = plan.get("source_sha256")
        if expected and expected != _source_fingerprint(current):
            return {
                "ok": False, "wrote": True, "complete": False,
                "reason": "生成期间来源改变,不能保存混合修订并宣称完整",
                "design_id": plan.get("design_id"),
                "revision": plan.get("revision"),
                "issue_number": number,
                "gate_required": False,
            }
        attachments, err = _collect_attachments(root, plan)
        if err:
            return {
                "ok": False, "wrote": True, "complete": False,
                "reason": err, "gate_required": False,
                "design_id": plan.get("design_id"),
                "revision": plan.get("revision"),
                "issue_number": number,
            }
        # 复用前必须校验归档全文:只看「整体设计」标题仍在就跳过校验,
        # 丢了模块/附件或正文被改的残缺归档会被重试直接盖 complete。
        saved = _parse_github_snapshot(existing)
        recovered_ok = (
            saved.get("overall") == (current.get("overall") or "").strip()
            and saved.get("modules") == {
                key: (value or "").strip()
                for key, value in (current.get("modules") or {}).items()}
            and saved.get("attachments") == {
                key: (value or "").strip()
                for key, value in (attachments or {}).items()})
        if not recovered_ok:
            # 恢复保持原形成时间;正文按计划内容重建,回读一致才算恢复。
            body = _render_github_body(
                plan, current.get("overall") or "",
                dict(current.get("modules") or {}), attachments,
                formed_at=_meta_field(body_text, "形成时间") or today())
            # 恢复 PATCH 必须成功且回读一致:归档 Issue 若仍缺整体/模块/
            # 附件内容,不得因索引已就绪就宣告恢复完成。
            try:
                status, _payload = backend.transport.request(
                    "PATCH",
                    f"{mgs_spec.repo_path(backend.repo)}/issues/{number}",
                    {"body": body})
                if status not in (200, 201):
                    raise mgs_spec.TransportError(
                        "bad_response", f"rebuild snapshot HTTP {status}")
                back = backend.transport.request(
                    "GET",
                    f"{mgs_spec.repo_path(backend.repo)}/issues/{number}")[1]
                if (back or {}).get("body") != body:
                    raise mgs_spec.TransportError(
                        "bad_response", "rebuild snapshot 回读失败")
            except mgs_spec.TransportError as exc:
                return {
                    "ok": False, "wrote": True, "complete": False,
                    "filled_gap_only": True,
                    "design_id": plan.get("design_id"),
                    "revision": plan.get("revision"),
                    "issue_number": number,
                    "reason": f"归档恢复未确认:{exc}",
                    "gate_required": False,
                }
        index_ok = _ensure_github_index(backend, plan, number)
        if not index_ok:
            return {
                "ok": False, "wrote": True, "complete": False,
                "filled_gap_only": True,
                "design_id": plan.get("design_id"),
                "revision": plan.get("revision"),
                "issue_number": number,
                "reason": "部分保存,索引未完整",
                "gate_required": False,
            }
        return {
            "ok": True, "wrote": True, "complete": True,
            "filled_gap_only": True,
            "design_id": plan.get("design_id"),
            "revision": plan.get("revision"),
            "issue_number": number,
            "backend": "github-issues",
            "gate_required": False, "published": True,
        }
    current = mgs_spec.read_current_design(
        root, options.config_rel, transport=options.transport,
        api_base=options.api_base, cache_dir=options.cache_dir)
    expected = plan.get("source_sha256")
    if expected and expected != _source_fingerprint(current):
        return {
            "ok": False, "wrote": False, "complete": False,
            "reason": "生成期间来源改变,不能保存混合修订并宣称完整",
            "gate_required": False,
        }
    overall = current.get("overall") or ""
    modules = dict(current.get("modules") or {})
    missing_refs = _missing_module_refs(root, overall, modules)
    if missing_refs:
        return {
            "ok": False, "wrote": False, "complete": False,
            "reason": f"缺模块:{', '.join(missing_refs)}",
            "gate_required": False,
        }
    attachments, err = _collect_attachments(root, plan)
    if err:
        return {
            "ok": False, "wrote": False, "complete": False,
            "reason": err, "gate_required": False,
        }
    body = _render_github_body(
        plan, overall, modules, attachments, formed_at=today())
    title = (f"{SNAPSHOT_HEADING} {plan.get('design_id')} "
             f"{plan.get('revision')}")
    try:
        status, issue = backend.transport.request(
            "POST", f"{mgs_spec.repo_path(backend.repo)}/issues",
            {"title": title, "body": body})
        if status not in (200, 201):
            raise mgs_spec.TransportError(
                "bad_response", f"create snapshot HTTP {status}")
        number = issue.get("number")
        back = backend.transport.request(
            "GET", f"{mgs_spec.repo_path(backend.repo)}/issues/{number}")[1]
        if (back or {}).get("body") != body:
            return {
                "ok": False, "wrote": False, "complete": False,
                "reason": "归档正文回读失败", "gate_required": False,
            }
        index_ok = _ensure_github_index(backend, plan, number)
        if not index_ok:
            return {
                "ok": False, "wrote": True, "complete": False,
                "design_id": plan.get("design_id"),
                "revision": plan.get("revision"),
                "issue_number": number,
                "reason": "部分保存,索引未完整",
                "gate_required": False, "published": False,
            }
        return {
            "ok": True, "wrote": True, "complete": True,
            "design_id": plan.get("design_id"),
            "revision": plan.get("revision"),
            "issue_number": number,
            "backend": "github-issues",
            "implementation": plan.get("implementation"),
            "release": plan.get("release"),
            "gate_required": False, "published": True,
        }
    except mgs_spec.TransportError as exc:
        landed = _find_github_revision(
            backend, plan.get("design_id"), plan.get("revision"))
        if landed is not None:
            index_ok = _ensure_github_index(backend, plan, landed.get("number"))
            if not index_ok:
                return {
                    "ok": False, "wrote": True, "complete": False,
                    "filled_gap_only": True,
                    "design_id": plan.get("design_id"),
                    "revision": plan.get("revision"),
                    "issue_number": landed.get("number"),
                    "reason": "部分保存,索引未完整",
                    "gate_required": False,
                }
            return {
                "ok": True, "wrote": True, "complete": True,
                "filled_gap_only": True,
                "design_id": plan.get("design_id"),
                "revision": plan.get("revision"),
                "issue_number": landed.get("number"),
                "backend": "github-issues",
                "gate_required": False, "published": True,
            }
        draft = mgs_spec._draft(
            backend, "apply_design_snapshot",
            {"design_id": plan.get("design_id"),
             "revision": plan.get("revision"),
             "game_version": plan.get("game_version")},
            str(exc))
        draft.update({"ok": False, "wrote": False, "complete": False,
                      "published": False})
        return draft


def _find_github_revision(backend, design_id, revision) -> dict | None:
    try:
        items = mgs_spec._list_github_items(backend)
    except mgs_spec.TransportError:
        return None
    for item in items:
        body = item.get("body") or ""
        if SNAPSHOT_MARK not in body:
            continue
        ident = ""
        match = re.search(r"快照身份\s*[:：]\s*([A-Za-z0-9_-]+)", body)
        if match:
            ident = match.group(1)
        if ident == design_id and (_meta_field(body, "修订") or "r1") == revision:
            return item
    return None


def _ensure_github_index(backend, plan, snapshot_number) -> bool:
    try:
        items = mgs_spec._list_github_items(backend)
    except mgs_spec.TransportError:
        return False
    overall = None
    for item in items:
        body = item.get("body") or ""
        if mgs_spec._is_live_overall(body):
            overall = item
            break
    if overall is None:
        return False
    location = f"归档 Issue #{snapshot_number}"
    updated = _upsert_index_section(
        overall.get("body") or "", _index_line(plan, location=location))
    if updated == (overall.get("body") or ""):
        return True
    try:
        status, _issue = backend.transport.request(
            "PATCH",
            f"{mgs_spec.repo_path(backend.repo)}/issues/{overall['number']}",
            {"body": updated})
        if status not in (200, 201):
            return False
        back = backend.transport.request(
            "GET",
            f"{mgs_spec.repo_path(backend.repo)}/issues/{overall['number']}")[1]
        return (back or {}).get("body") == updated
    except mgs_spec.TransportError:
        return False


def _associate_github_version(root, config, plan, *,
                              options: BackendOptions) -> dict:
    denied = mgs_spec._ensure_write(config)
    if denied:
        return {"ok": False, "wrote": False, "complete": False, "reason": denied}
    backend = mgs_spec._github(
        config, transport=options.transport, api_base=options.api_base,
        cache_dir=options.cache_dir)
    match = _find_latest_github(backend, plan.get("design_id"))
    if match is None:
        return {"ok": False, "wrote": False, "complete": False,
                "reason": f"可复用快照不存在:{plan.get('design_id')}"}
    body = match.get("body") or ""
    versions = _field_list(body, "游戏版本")
    game = str(plan.get("game_version") or "")
    patched = body
    if game and game not in versions:
        versions.append(game)
        patched = re.sub(
            r"游戏版本\s*[:：]\s*.+",
            f"游戏版本:{', '.join(versions)}",
            patched, count=1)
    # 与本地路径同规则:版本已登记时也要补齐实现/发布字段。
    if plan.get("implementation") and _meta_field(
            patched, "实现") != str(plan.get("implementation")):
        patched = re.sub(
            r"实现\s*[:：]\s*.+",
            f"实现:{plan.get('implementation')}", patched, count=1)
    if plan.get("release") and _meta_field(
            patched, "发布") != str(plan.get("release")):
        patched = re.sub(
            r"发布\s*[:：]\s*.+",
            f"发布:{plan.get('release')}", patched, count=1)
    try:
        if patched != body:
            status, _payload = backend.transport.request(
                "PATCH",
                f"{mgs_spec.repo_path(backend.repo)}/issues/{match['number']}",
                {"body": patched})
            if status not in (200, 201):
                raise mgs_spec.TransportError(
                    "bad_response", f"associate snapshot HTTP {status}")
        back = backend.transport.request(
            "GET",
            f"{mgs_spec.repo_path(backend.repo)}/issues/{match['number']}")[1]
        final_body = str((back or {}).get("body") or "")
        verified = (
            (not game or game in _field_list(final_body, "游戏版本"))
            and (not plan.get("implementation")
                 or _meta_field(final_body, "实现")
                 == str(plan.get("implementation")))
            and (not plan.get("release")
                 or _meta_field(final_body, "发布")
                 == str(plan.get("release"))))
        if not verified:
            raise mgs_spec.TransportError(
                "bad_response", "associate snapshot 元数据回读未确认")
    except mgs_spec.TransportError as exc:
        draft = mgs_spec._draft(
            backend, "apply_design_snapshot",
            {"design_id": plan.get("design_id"),
             "game_version": game, "reuse": True},
            str(exc))
        draft.update({"ok": False, "wrote": False, "complete": False,
                      "published": False})
        return draft
    index_ok = _ensure_github_index(backend, plan, match.get("number"))
    if not index_ok:
        return {
            "ok": False, "wrote": True, "complete": False, "reuse": True,
            "design_id": plan.get("design_id"),
            "revision": plan.get("revision") or _meta_field(body, "修订"),
            "issue_number": match.get("number"),
            "reason": "部分保存,索引未完整",
            "backend": "github-issues",
            "gate_required": False, "published": False,
        }
    return {
        "ok": True, "wrote": True, "complete": True, "reuse": True,
        "design_id": plan.get("design_id"),
        "revision": plan.get("revision") or _meta_field(final_body, "修订"),
        "issue_number": match.get("number"),
        "backend": "github-issues",
        "implementation": _meta_field(final_body, "实现")
        or plan.get("implementation"),
        "release": _meta_field(final_body, "发布") or plan.get("release"),
        "gate_required": False, "published": True,
    }


def _find_latest_github(backend, design_id) -> dict | None:
    found = None
    found_number = -1
    try:
        items = mgs_spec._list_github_items(backend)
    except mgs_spec.TransportError:
        return None
    for item in items:
        body = item.get("body") or ""
        match = re.search(r"快照身份\s*[:：]\s*([A-Za-z0-9_-]+)", body)
        if not match or match.group(1) != design_id:
            continue
        revision = re.match(
            r"r(\d+)$", _meta_field(body, "修订") or "r1")
        number = int(revision.group(1)) if revision else 0
        if number > found_number:
            found, found_number = item, number
    return found

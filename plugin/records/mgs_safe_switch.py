#!/usr/bin/env python3
"""用户修改、同名来源与安全切换(issue #59)。

资料完整迁移后,核对来源、版本、用户修改、转换完整性、证据可达和准备期间
新增变更,通过后才切换现行指针与对应技能来源。同名技能只保留一个明确有效
来源;共用客户端未就绪项目保留旧环境;回退先保留新版新增成果。
普通路径不经 mgs-gate。不把功能实现当作真实环境迁移授权。

公开 interface(经 mgs_records 再导出):
  plan_safe_switch(project_root, *, config_rel=DEFAULT_CONFIG_REL, ...) -> dict
  apply_safe_switch(project_root, plan, *, confirmed, config_rel=...) -> dict
  read_safe_switch(project_root, *, config_rel=DEFAULT_CONFIG_REL, ...) -> dict
  rollback_safe_switch(project_root, plan, *, confirmed, config_rel=...) -> dict

config_rel 指向现行协作配置(CLI --config 透传):tracker 判定、GitHub
后端构造与回滚授权核对都按该文件进行,缺省沿用默认 CONFIG 路径。
"""

from __future__ import annotations

import re
import shutil
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))

from mgs_backend_options import (BackendOptions, backend_options,
                                 github_backend_for)  # noqa: E402
from mgs_github_issue import (  # noqa: E402
    HISTORY_MARK, PENDING_SWITCH_MARK, authorization_for, skip_from_current_reads)
from mgs_github_transport import repo_path, request_2xx  # noqa: E402
from mgs_migration_common import (  # noqa: E402
    GATE_HISTORY_REL, _load_json, _pending_root, _read, _save_json,
    _sha_file, _write)
from mgs_record_model import RecordsError, today  # noqa: E402
from mgs_record_source import (  # noqa: E402
    DEFAULT_CONFIG_REL, WRITE_OP, load_config)
from mgs_spec import read_current_design  # noqa: E402

HISTORY_REL = "docs/mygamestudio/records/readonly-history"
PRESERVE_REL = "docs/mygamestudio/records/preserved-after-rollback"
STATUS_NAME = "switch-status.json"


def _status_path(root: Path) -> Path:
    return _pending_root(root) / STATUS_NAME


def _tracker_of(root: Path, config_rel: str = DEFAULT_CONFIG_REL) -> str:
    config_path = root / config_rel
    if not config_path.is_file():
        return "local-markdown"
    config = load_config(root, config_rel)
    backend = str(config.get("backend") or "local-markdown")
    return backend if backend in {"local-markdown", "github-issues"} else "local-markdown"


def _switch_status(root: Path) -> dict:
    return _load_json(_status_path(root))


def _migration_report(root: Path, *, options: BackendOptions) -> dict:
    tracker = _tracker_of(root, options.config_rel)
    if tracker == "github-issues":
        import mgs_github_material_migration  # noqa: PLC0415
        return mgs_github_material_migration.read_github_material_migration(
            root, transport=options.transport, api_base=options.api_base,
            cache_dir=options.cache_dir)
    import mgs_local_migration  # noqa: PLC0415
    return mgs_local_migration.read_local_material_migration(root)


def _source_fingerprints(root: Path, correspondence: dict) -> dict[str, str]:
    fingerprints: dict[str, str] = {}
    for rows in correspondence.values():
        if not isinstance(rows, list):
            continue
        for row in rows:
            old = str(row.get("old") or "")
            if not old or old.startswith("github:"):
                continue
            path = root / old
            if path.is_file():
                fingerprints[old] = _sha_file(path)
    live = root / "docs/mygamestudio/GAME_DESIGN.md"
    if live.is_file():
        fingerprints["docs/mygamestudio/GAME_DESIGN.md"] = _sha_file(live)
    return fingerprints


def _prep_changed(root: Path, expected: dict[str, str]) -> list[str]:
    changed: list[str] = []
    for rel, digest in expected.items():
        path = root / rel
        if not path.is_file():
            changed.append(rel)
            continue
        if _sha_file(path) != digest:
            changed.append(rel)
    return changed


def _tree_fingerprints(root: Path | str | None) -> dict[str, str]:
    """逐文件指纹一棵目录树;目录不存在或未提供时返回空。"""

    if not root:
        return {}
    base = Path(root)
    if not base.is_dir():
        return {}
    fingerprints: dict[str, str] = {}
    for path in sorted(base.rglob("*")):
        if path.is_file():
            rel = str(path.relative_to(base)).replace("\\", "/")
            fingerprints[rel] = _sha_file(path)
    return fingerprints


def _package_drift(plan: dict) -> list[str]:
    """重查已确认计划里的包树指纹,返回与清单不一致的包内文件。

    无包根的计划不涉及技能包安装,无需比对;带包根却无包树指纹的
    计划(旧版或被篡改)无法证明包内容与确认时一致,视为漂移(失败
    闭合);包根丢失同样视为全部漂移。"""

    package_raw = str(plan.get("package_root") or "").strip()
    if not package_raw:
        return []
    fingerprints = plan.get("package_fingerprints")
    expected = fingerprints if isinstance(fingerprints, dict) else {}
    if not expected:
        return ["<计划未携带包树指纹,无法核对包内容>"]
    return _prep_changed(Path(package_raw), expected)


def _converted_overall(root: Path, report: dict, *,
                       options: BackendOptions) -> str:
    staging = Path(report.get("pending_root") or _pending_root(root))
    try:
        converted = read_current_design(staging)
        if converted.get("overall"):
            return converted.get("overall") or ""
    except (RecordsError, OSError):
        pass
    if report.get("tracker") != "github-issues":
        return ""
    overall_no = None
    for row in (report.get("correspondence") or {}).get("specs") or []:
        if row.get("identity") == "overall" and row.get("new_issue"):
            overall_no = row.get("new_issue")
            break
    if not overall_no:
        return ""
    try:
        backend = _github_backend(root, options)
        read_ok, body = _read_issue_body(backend, int(overall_no))
        return body if read_ok else ""
    except (RecordsError, OSError, TypeError, ValueError):
        return ""


def _user_edits_ok(root: Path, report: dict, *,
                   options: BackendOptions) -> bool:
    live = _read(root / "docs/mygamestudio/GAME_DESIGN.md")
    if "用户补充" not in live:
        return True
    extra = live.split("用户补充", 1)[-1]
    snippet = extra.strip().splitlines()
    snippet = [line for line in snippet if line and not line.startswith("#")]
    if not snippet or not snippet[0].lstrip("- ").strip():
        return True
    needle = snippet[0].lstrip("- ").strip()
    overall = _converted_overall(root, report, options=options)
    return needle in overall


def _checks_from(root: Path, report: dict, *, options: BackendOptions,
                 fingerprints: dict[str, str] | None = None) -> dict[str, Any]:
    complete = bool(report.get("complete"))
    paused = list(report.get("paused") or [])
    missing = list(report.get("missing") or [])
    reachable = True
    missing_listed = set(report.get("missing_evidence") or [])
    for row in (report.get("correspondence") or {}).get("evidence") or []:
        old = row.get("old")
        if row.get("reachable") is False and old not in missing_listed:
            reachable = False
        elif old and not str(old).startswith("github:"):
            path = root / str(old)
            if row.get("reachable") is True and not path.is_file():
                reachable = False
    prep_ok = not paused
    if fingerprints:
        prep_ok = prep_ok and not _prep_changed(root, fingerprints)
    status = report.get("status")
    return {
        "source": status in {"pending-switch", "switched"} or complete,
        "version": bool((report.get("correspondence") or {}).get("specs")),
        "user_edits": _user_edits_ok(root, report, options=options),
        "conversion_complete": complete and not paused and not missing,
        "evidence_reachable": reachable,
        "preparation_changes": prep_ok,
    }


def _plan_safe_switch(root: Path, *, client_home, package_root,
                      peer_projects, options: BackendOptions) -> dict:
    """只读核对照切换条件。不写入,不切换现行指针或技能来源。"""

    if not root.is_dir():
        raise RecordsError(f"目标项目不存在:{root}")
    switched = _switch_status(root)
    report = _migration_report(root, options=options)
    fingerprints = _source_fingerprints(root, report.get("correspondence") or {})
    checks = _checks_from(
        root, report, options=options, fingerprints=fingerprints)
    already = switched.get("status") == "switched"
    ready = (all(checks.values()) and report.get("status") == "pending-switch"
             and not already)
    blockers = [name for name, ok in checks.items() if not ok]
    if already:
        blockers = []
    elif report.get("status") not in {"pending-switch", "switched"}:
        blockers.append("conversion")
    recovery = (report.get("recovery_archive") or report.get("gate_history")
                or _read(root / GATE_HISTORY_REL)
                or _read(_pending_root(root) / GATE_HISTORY_REL))
    tracker = report.get("tracker") or _tracker_of(root, options.config_rel)
    return {
        "wrote": False,
        "ready": ready,
        "status": "planned",
        "tracker": tracker,
        "backend": tracker,
        "checks": checks,
        "blockers": blockers,
        "paused": list(report.get("paused") or []),
        "missing": list(report.get("missing") or []),
        "gate_required": False,
        "gate_as_permission": False,
        "real_migration_authorized": False,
        "recovery_destination": GATE_HISTORY_REL if recovery else "",
        "client_home": str(client_home) if client_home else "",
        "package_root": str(package_root) if package_root else "",
        "peer_projects": [str(item) for item in (peer_projects or [])],
        "correspondence": report.get("correspondence") or switched.get("correspondence") or {},
        "migration_status": switched.get("status") or report.get("status"),
        "source_fingerprints": fingerprints,
        "package_fingerprints": _tree_fingerprints(package_root),
        "already_switched": already,
    }


def plan_safe_switch(project_root: Path | str, *,
                     client_home: Path | str | None = None,
                     package_root: Path | str | None = None,
                     peer_projects: list[Path | str] | None = None,
                     config_rel: str = DEFAULT_CONFIG_REL,
                     transport=None, api_base: str | None = None,
                     cache_dir: Path | str | None = None) -> dict:
    """只读核对照切换条件。不写入,不切换现行指针或技能来源。"""

    root = Path(project_root)
    return _plan_safe_switch(
        root, client_home=client_home, package_root=package_root,
        peer_projects=peer_projects,
        options=backend_options(config_rel, transport, api_base, cache_dir))


def _mark_switched_config(text: str) -> str:
    lines = []
    for line in (text or "").splitlines():
        if "pending-switch" in line or line.startswith("- 状态:"):
            lines.append(
                "- 状态:switched。新版为唯一现行维护来源;"
                "旧原件见 docs/mygamestudio/records/readonly-history。"
            )
            continue
        if "mgs-gate" in line or "producer-token" in line:
            continue
        lines.append(line)
    body = "\n".join(lines).strip() + "\n"
    if "状态:switched" not in body:
        body = body.replace(
            "采用依据:本地旧项目完整资料迁移(待切换)。",
            "采用依据:本地旧项目完整资料迁移后已切换。",
        )
        insert = (
            "- 状态:switched。新版为唯一现行维护来源;"
            "旧原件见 docs/mygamestudio/records/readonly-history。"
        )
        if insert not in body:
            body = body.rstrip() + "\n" + insert + "\n"
    if body.startswith("# 待切换"):
        body = body.replace("# 待切换协作配置", "# 协作配置", 1)
    return body


def _archive_originals(root: Path, staging: Path) -> list[str]:
    history = root / HISTORY_REL
    archived: list[str] = []
    live_docs = root / "docs" / "mygamestudio"
    if not live_docs.is_dir():
        return archived
    for live in live_docs.rglob("*"):
        if not live.is_file():
            continue
        rel = live.relative_to(live_docs)
        text = str(rel).replace("\\", "/")
        if text.startswith("records/pending-switch"):
            continue
        if text.startswith("records/readonly-history"):
            continue
        dest = history / rel
        dest.parent.mkdir(parents=True, exist_ok=True)
        # 每次切换都以切换前字节替换回退基线:第二轮切换沿用第一轮留档
        # 会让二次回退恢复上一轮旧快照,丢失两轮之间的编辑。
        shutil.copy2(live, dest)
        archived.append(str(dest.relative_to(root)).replace("\\", "/"))
    return archived


def _promote_pending(root: Path, staging: Path,
                     config_rel: str = DEFAULT_CONFIG_REL) -> int:
    staging_docs = staging / "docs" / "mygamestudio"
    if not staging_docs.is_dir():
        return 0
    copied = 0
    for src in staging_docs.rglob("*"):
        if not src.is_file():
            continue
        dest = root / src.relative_to(staging)
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dest)
        copied += 1
    config_path = root / config_rel
    if config_path.is_file():
        _write(config_path, _mark_switched_config(_read(config_path)))
    return copied


def _peer_unready(peer_projects: list, *, options: BackendOptions) -> list[str]:
    unready: list[str] = []
    for peer in peer_projects or []:
        path = Path(peer)
        if not path.is_dir():
            unready.append(str(path))
            continue
        if _switch_status(path).get("status") == "switched":
            continue
        report = _migration_report(path, options=options)
        if report.get("complete") and report.get("status") == "pending-switch":
            continue
        unready.append(str(path))
    return unready


def _skill_dirs(root: Path) -> dict[str, Path]:
    if not root.is_dir():
        return {}
    return {path.name: path for path in root.iterdir()
            if path.is_dir() and (path / "SKILL.md").is_file()}


def _retired_skill_names(package: Path) -> list[str]:
    """新包文档登记的已退役旧入口名;无该文档的包不视为有退役项。"""

    candidates = [
        package / "internal" / "game" / "retired-entries.md",
        package.parent / "internal" / "game" / "retired-entries.md",
        package.parent.parent / "internal" / "game" / "retired-entries.md",
        Path(__file__).resolve().parent.parent / "internal" / "game"
        / "retired-entries.md",
    ]
    path = next((item for item in candidates if item.is_file()), None)
    if path is None:
        return []
    return sorted({match.group(1) for match in re.finditer(
        r"^-\s+(game-[a-z-]+)\s+->", path.read_text(encoding="utf-8"),
        re.MULTILINE)})


def _meaning_conflict(user_text: str, package_text: str) -> bool:
    user = user_text.lower()
    package = package_text.lower()
    if "never write a failing test first" in user:
        return True
    if "含义" in user_text and "相反" in user_text:
        return True
    if ("red → green" in package or "red before green" in package
            or "failing test first" in package):
        if "never write a failing test" in user:
            return True
    return False


def _user_edit_block(text: str) -> str:
    marker = "## 用户修改"
    if marker not in (text or ""):
        return ""
    return marker + (text or "").split(marker, 1)[1]


def _without_user_edit_block(text: str) -> str:
    marker = "## 用户修改"
    if marker not in (text or ""):
        return (text or "").rstrip()
    return (text or "").split(marker, 1)[0].rstrip()


def _skill_file_rels(skill_dir: Path) -> set[str]:
    rels: set[str] = set()
    if not skill_dir.is_dir():
        return rels
    for path in skill_dir.rglob("*"):
        if path.is_file():
            rels.add(str(path.relative_to(skill_dir)).replace("\\", "/"))
    return rels


def _edited_shared_files(user_dir: Path, pkg_dir: Path,
                         hist_dir: Path | None) -> list[str]:
    """用户改过、包内同名路径也存在 SKILL.md 之外的支持文件。

    与包副本一致不算用户修改;与上次切换时的历史副本一致说明差异来自
    上游版本变化,可安全采用新包;其余差异无法证明非用户编辑,按用户
    编辑处理并暂停该技能,不得用包副本静默覆盖。
    """

    edited: list[str] = []
    for rel in sorted(_skill_file_rels(user_dir) & _skill_file_rels(pkg_dir)):
        if rel == "SKILL.md":
            continue
        user = (user_dir / rel).read_bytes()
        if user == (pkg_dir / rel).read_bytes():
            continue
        if hist_dir is not None and (hist_dir / rel).is_file() \
                and user == (hist_dir / rel).read_bytes():
            continue
        edited.append(rel)
    return edited


def _additive_user_skill_text(user_text: str, pkg_text: str) -> str | None:
    """Return extra user SKILL.md text that can be appended, or None if unsafe."""

    user_core = _without_user_edit_block(user_text)
    pkg_core = (pkg_text or "").rstrip()
    extra_parts: list[str] = []
    if user_core == pkg_core:
        pass
    elif pkg_core and pkg_core in user_core:
        extra = user_core.replace(pkg_core, "", 1).strip()
        if extra:
            extra_parts.append(extra)
    else:
        return None
    block = _user_edit_block(user_text)
    if block:
        extra_parts.append(block)
    return "\n\n".join(extra_parts)


def _ensure_stage_pointer(text: str) -> str:
    pointer = "../../internal/game/stage-requirements.md"
    if "stage-requirements.md" in (text or ""):
        return text
    note = (
        "\n## MyGameStudio stage materials\n\n"
        "When working in a MyGameStudio game project, read "
        f"[stage requirements]({pointer}) for the current work stage. "
        "Reading those materials does not start production.\n"
    )
    return (text or "").rstrip() + "\n" + note


def _copy_stage_index(home: Path, package_root: Path) -> None:
    dest = home / "internal" / "game"
    dest.mkdir(parents=True, exist_ok=True)
    candidates = [
        package_root.parent / "internal" / "game" / "stage-requirements.md",
        package_root.parent.parent / "internal" / "game" / "stage-requirements.md",
        Path(__file__).resolve().parent.parent / "internal" / "game" / "stage-requirements.md",
        home / "internal" / "game" / "stage-requirements.md",
    ]
    for src in candidates:
        if src.is_file():
            target = dest / "stage-requirements.md"
            if src.resolve() != target.resolve():
                shutil.copy2(src, target)
            inv = src.parent / "invocation.md"
            inv_dest = dest / "invocation.md"
            if inv.is_file() and inv.resolve() != inv_dest.resolve():
                shutil.copy2(inv, inv_dest)
            return


def _paths_overlap(a: Path, b: Path) -> bool:
    """两个目录是否相同或存在嵌套包含;重叠时先删后拷会互相自毁。

    解析失败时无法证明两侧可安全分离,按重叠处理(失败闭合)。"""

    try:
        ra, rb = a.resolve(), b.resolve()
    except OSError:
        return True
    return ra == rb or ra in rb.parents or rb in ra.parents


def _same_path(a: Path, b: Path) -> bool:
    """两个路径是否指向同一位置;解析失败时视为不同(落入暂停分支)。"""

    try:
        return a.resolve() == b.resolve()
    except OSError:
        return False


def _switch_skills(plan: dict, *, unready: list[str]) -> dict:
    home_raw = str(plan.get("client_home") or "").strip()
    package_raw = str(plan.get("package_root") or "").strip()
    if not home_raw or not package_raw:
        return {"paused": [], "developer_decisions": [], "switched_skills": False}
    home = Path(home_raw)
    package = Path(package_raw)
    if not home.is_dir() or not package.is_dir():
        return {"paused": [], "developer_decisions": [], "switched_skills": False}
    if unready:
        return {
            "paused": [],
            "developer_decisions": [],
            "switched_skills": False,
            "old_environment_kept": True,
        }
    current = home / "skills"
    current.mkdir(parents=True, exist_ok=True)
    history = home / "skills-history"
    pkg_skills = _skill_dirs(package)
    user_skills = _skill_dirs(current)
    paused: list[str] = []
    decisions: list[str] = []
    added: list[str] = []
    paused_shared_files: dict[str, list[str]] = {}
    for name, pkg_dir in pkg_skills.items():
        user_dir = user_skills.get(name)
        pkg_text = _read(pkg_dir / "SKILL.md")
        if user_dir is not None:
            user_text = _read(user_dir / "SKILL.md")
            # 包来源与安装目录重叠时,先删后拷会把唯一的技能副本连同包
            # 一起删掉。目录完全相同说明安装内容已是包本身,跳过替换;
            # 嵌套重叠无法安全替换,暂停该技能交开发者处理。
            if _paths_overlap(user_dir, pkg_dir):
                if _same_path(user_dir, pkg_dir):
                    continue
                _write(user_dir / "SKILL.md", _ensure_stage_pointer(user_text))
                paused.append(name)
                decisions.append(name)
                continue
            extra_rels = _skill_file_rels(user_dir) - _skill_file_rels(pkg_dir)
            extra_text = _additive_user_skill_text(user_text, pkg_text)
            hist_dir = history / name if (history / name).is_dir() else None
            edited_shared = _edited_shared_files(user_dir, pkg_dir, hist_dir)
            if (_meaning_conflict(user_text, pkg_text) or extra_text is None
                    or edited_shared):
                _write(user_dir / "SKILL.md", _ensure_stage_pointer(user_text))
                paused.append(name)
                decisions.append(name)
                if edited_shared:
                    paused_shared_files[name] = edited_shared
                continue
            live_extras: dict[str, bytes] = {}
            for rel in extra_rels:
                src = user_dir / rel
                if src.is_file():
                    live_extras[rel] = src.read_bytes()
            hist = history / name
            if not hist.exists():
                hist.parent.mkdir(parents=True, exist_ok=True)
                shutil.copytree(user_dir, hist)
            else:
                for rel, data in live_extras.items():
                    dest = hist / rel
                    dest.parent.mkdir(parents=True, exist_ok=True)
                    dest.write_bytes(data)
            shutil.rmtree(user_dir)
            shutil.copytree(pkg_dir, user_dir)
            installed = _read(user_dir / "SKILL.md")
            if extra_text and extra_text not in installed:
                _write(user_dir / "SKILL.md", installed.rstrip() + "\n\n" + extra_text)
            for rel, data in live_extras.items():
                dest = user_dir / rel
                dest.parent.mkdir(parents=True, exist_ok=True)
                dest.write_bytes(data)
        else:
            shutil.copytree(pkg_dir, current / name)
            added.append(name)
    # 新包已退役的旧入口(如 1.x 的 game-art/game-status):归档后退出
    # 活动目录;不在退役清单里的无关用户技能保持原样。否则切换宣称
    # client_complete 后旧入口仍可被发现,与新包并存两套入口。
    retired_done: list[str] = []
    for name in _retired_skill_names(package):
        if name in pkg_skills:
            continue
        user_dir = user_skills.get(name)
        if user_dir is None:
            continue
        # 退役清理同样不得删除与包来源重叠的目录(否则会删掉包内容)。
        if _paths_overlap(user_dir, package):
            continue
        hist = history / name
        if not hist.exists():
            hist.parent.mkdir(parents=True, exist_ok=True)
            shutil.copytree(user_dir, hist)
        else:
            for src in user_dir.rglob("*"):
                if not src.is_file():
                    continue
                dest = hist / src.relative_to(user_dir)
                dest.parent.mkdir(parents=True, exist_ok=True)
                if not dest.exists():
                    shutil.copy2(src, dest)
        shutil.rmtree(user_dir)
        retired_done.append(name)
    _copy_stage_index(home, package)
    return {
        "paused": paused,
        "developer_decisions": decisions,
        "switched_skills": True,
        "old_environment_kept": False,
        "retired_skills": retired_done,
        "paused_shared_files": paused_shared_files,
        "added_skills": added,
    }


def _client_complete(plan: dict, skills: dict, unready: list) -> bool:
    if unready:
        return False
    requested = bool(str(plan.get("client_home") or "").strip()
                     or str(plan.get("package_root") or "").strip())
    if not requested:
        return True
    return bool(skills.get("switched_skills")) and not list(
        skills.get("paused") or [])


def _switch_local(root: Path, plan: dict, *, options: BackendOptions) -> dict:
    staging = _pending_root(root)
    if not (staging / "docs/mygamestudio/CONFIG.md").is_file():
        return {
            "ok": False, "wrote": False, "reason": "没有待切换资料",
            "gate_required": False, "real_migration_authorized": False,
        }
    changed = _prep_changed(root, plan.get("source_fingerprints") or {})
    if changed:
        return {
            "ok": False, "wrote": False,
            "reason": "准备期间来源已变化,不切换",
            "paused": changed,
            "gate_required": False,
            "real_migration_authorized": False,
            "status": "blocked",
        }
    # peer 就绪检查必须先于归档与提升,且透传注入的 transport:晚于提升
    # 会让 peer 检查失败时本地已被换成新来源,留下半完成的切换状态。
    unready = _peer_unready(plan.get("peer_projects") or [], options=options)
    archived = _archive_originals(root, staging)
    copied = _promote_pending(root, staging, config_rel=options.config_rel)
    correspondence = plan.get("correspondence") or {}
    skills = _switch_skills(plan, unready=unready)
    payload = {
        "status": "switched",
        "tracker": "local-markdown",
        "switched_on": today(),
        "history_root": HISTORY_REL,
        "pending_root": str(staging),
        "correspondence": correspondence,
        "archived": archived,
        "gate_required": False,
        "gate_as_permission": False,
        "real_migration_authorized": False,
        "recovery_destination": GATE_HISTORY_REL,
        "client_complete": _client_complete(plan, skills, unready),
        "unready_projects": unready,
        "paused_skills": skills.get("paused") or [],
        "developer_decisions": skills.get("developer_decisions") or [],
        "retired_skills": skills.get("retired_skills") or [],
        "paused_shared_files": skills.get("paused_shared_files") or {},
        "added_skills": skills.get("added_skills") or [],
        "client_home": str(plan.get("client_home") or ""),
        "package_root": str(plan.get("package_root") or ""),
    }
    _save_json(_status_path(root), payload)
    return {
        "ok": True,
        "wrote": copied > 0 or bool(archived),
        "status": "switched",
        "tracker": "local-markdown",
        "backend": "local-markdown",
        "history_root": HISTORY_REL,
        "archived": archived,
        "gate_required": False,
        "gate_as_permission": False,
        "real_migration_authorized": False,
        "recovery_destination": GATE_HISTORY_REL,
        "correspondence": correspondence,
        "client_complete": _client_complete(plan, skills, unready),
        "unready_projects": unready,
        "paused": list(skills.get("paused") or []),
        "developer_decisions": list(skills.get("developer_decisions") or []),
        "retired_skills": list(skills.get("retired_skills") or []),
        "paused_shared_files": dict(skills.get("paused_shared_files") or {}),
    }


def _github_backend(root: Path, options: BackendOptions):
    config = dict(load_config(root, options.config_rel))
    config["project_root"] = str(root)
    return github_backend_for(config, options)


def _strip_mark(body: str, mark: str) -> str:
    lines = [line for line in (body or "").splitlines() if mark not in line]
    text = "\n".join(lines).strip()
    return text + "\n" if text else ""


def _with_mark(body: str, mark: str) -> str:
    if mark in (body or ""):
        return body if (body or "").endswith("\n") else (body or "") + "\n"
    lines = (body or "").splitlines()
    if lines and lines[0].startswith("# "):
        return "\n".join([lines[0], "", mark] + lines[1:]) + "\n"
    return mark + "\n\n" + (body or "")


def _old_issue_numbers(correspondence: dict) -> list[int]:
    numbers: list[int] = []
    for rows in correspondence.values():
        if not isinstance(rows, list):
            continue
        for row in rows:
            old = str(row.get("old") or "")
            if old.startswith("github:issue:"):
                try:
                    numbers.append(int(old.rsplit(":", 1)[-1]))
                except ValueError:
                    pass
    return numbers


def _current_new_issue_numbers(correspondence: dict) -> list[int]:
    numbers: list[int] = []
    for row in correspondence.get("specs") or []:
        identity = str(row.get("identity") or "")
        number = row.get("new_issue")
        if not isinstance(number, int):
            continue
        if identity in {"overall", "rules"} or (
                identity and "-v" not in identity and "历史" not in identity):
            numbers.append(number)
    for row in correspondence.get("tasks") or []:
        number = row.get("new_issue")
        if isinstance(number, int):
            numbers.append(number)
    return numbers


def _write_denied_reason(backend) -> str:
    """重查当前 CONFIG 仓库级 issues-write 授权;允许时返回空串。

    已确认的本地切换计划不替代现行授权:迁移准备后授权可能被收回或
    不再匹配仓库,远端标记变更前必须按当前配置重新核对并失败闭合。"""

    allowed, note = authorization_for(backend.config, WRITE_OP)
    return "" if allowed else note


def _marker_failure(number: int, what: str, denied: str = "") -> str:
    text = f"#{number}:{what}"
    if denied:
        text += f"(当前 CONFIG 未授予 issues-write:{denied})"
    return text


def _patch_issue_body(backend, number: int, body: str) -> tuple[bool, str]:
    """PATCH 正文;仅 2xx 视为成功。忽略状态会把远端失败当成已切换。

    每次变更前重查当前 issues-write 授权;缺失时按失败闭合并附原因。"""

    denied = _write_denied_reason(backend)
    if denied:
        return False, denied
    status, _issue = backend.transport.request(
        "PATCH", f"{repo_path(backend.repo)}/issues/{number}", {"body": body})
    return status in (200, 201), ""


def _read_issue_body(backend, number: int) -> tuple[bool, str]:
    """读取 issue 正文;仅 HTTP 2xx 视为已确认,否则返回 (False, "")。

    丢弃状态码会把「读不到」当成「标记已不在」,让远端读取失败被误判为
    切换完成;调用方必须按 ok=False 失败闭合,不得当作空正文参与判定。"""

    payload = request_2xx(
        backend.transport, "GET",
        f"{repo_path(backend.repo)}/issues/{number}")
    if payload is None:
        return False, ""
    return True, (payload or {}).get("body") or ""


def _marker_steps(backend, steps: list[dict]) -> tuple[list[str], list[int], list[str]]:
    """逐项执行远端标记迁移;后续失败时回补全部已成功步骤并核实。

    每步字段:number、target(目标正文)、revert(变更前正文)、
    verify(目标状态回读判定)、patch_fail/readback_fail(两种失败的
    说明文案)。任一步失败时,已 PATCH 成功的步骤按 revert 正文回补,
    回补再回读核实;回补失败必须如实上报(远端停留混合状态)。
    返回 (failures, compensated, compensation_failures)。
    """

    failures: list[str] = []
    applied: list[tuple[int, str, str]] = []
    for step in steps:
        number = step["number"]
        ok, denied = _patch_issue_body(backend, number, step["target"])
        if not ok:
            failures.append(_marker_failure(
                number, step["patch_fail"], denied))
            continue
        read_ok, back = _read_issue_body(backend, number)
        if not read_ok or not step["verify"](back):
            failures.append(_marker_failure(number, step["readback_fail"]))
            applied.append((number, step["revert"], step["patch_fail"]))
            continue
        applied.append((number, step["revert"], step["patch_fail"]))
    compensated: list[int] = []
    compensation_failures: list[str] = []
    if failures:
        # 部分成功不得留在远端:回补已成功的标记,再逐项回读核实,
        # 否则 GitHub 停在「一半新一半旧」的混合权威状态。
        for number, revert, what in applied:
            ok, denied = _patch_issue_body(backend, number, revert)
            if not ok:
                compensation_failures.append(_marker_failure(
                    number, f"{what}回补未确认", denied))
                continue
            read_ok, back = _read_issue_body(backend, number)
            if not read_ok or back != revert:
                compensation_failures.append(_marker_failure(
                    number, f"{what}回补回读未确认"))
                continue
            compensated.append(number)
    return failures, compensated, compensation_failures


def _switch_github(root: Path, plan: dict, *, options: BackendOptions) -> dict:
    staging = _pending_root(root)
    backend = _github_backend(root, options)
    correspondence = plan.get("correspondence") or {}
    # 切换前先按当前 CONFIG 重查 issues-write:迁移准备时的授权不能
    # 替代此刻的授权;缺失或不再匹配时失败闭合,不动远端标记。
    denied = _write_denied_reason(backend)
    if denied:
        return {
            "ok": False,
            "wrote": False,
            "status": "pending-switch",
            "reason": "当前 CONFIG 未授予 issues-write,不执行远端标记变更:"
                      f"{denied}",
            "tracker": "github-issues",
            "backend": "github-issues",
            "history_root": HISTORY_REL,
            "archived": [],
            "gate_required": False,
            "gate_as_permission": False,
            "real_migration_authorized": False,
            "recovery_destination": GATE_HISTORY_REL,
            "correspondence": correspondence,
        }
    # peer 就绪检查必须先于远端标记与本地提升,且透传注入的 transport:
    # 丢弃注入会让 peer 回读走错误端点;晚于变更则 peer 检查失败时
    # 远端/本地已切成新来源,留下半完成的切换状态。
    unready = _peer_unready(plan.get("peer_projects") or [], options=options)
    # 远端标记迁移必须先于本地提升逐项确认:PATCH 成功且回读到目标状态
    # 才允许归档旧件、提升新件;任何一项未确认时本地保持旧来源,
    # 不写 switch-status。先提升再打标记会让本地指向新源而 GitHub
    # 仍停留旧源或混合源。
    marker_failures: list[str] = []
    steps: list[dict] = []
    for number in _current_new_issue_numbers(correspondence):
        read_ok, body = _read_issue_body(backend, number)
        if not read_ok:
            marker_failures.append(_marker_failure(
                number, "pending-switch 读取未确认"))
            continue
        if PENDING_SWITCH_MARK in body:
            steps.append({
                "number": number,
                "target": _strip_mark(body, PENDING_SWITCH_MARK),
                "revert": body,
                "verify": lambda back: PENDING_SWITCH_MARK not in back,
                "patch_fail": "pending-switch 移除未确认",
                "readback_fail": "pending-switch 回读仍在",
            })
    for number in _old_issue_numbers(correspondence):
        read_ok, body = _read_issue_body(backend, number)
        if not read_ok:
            marker_failures.append(_marker_failure(
                number, "readonly-history 读取未确认"))
            continue
        if not skip_from_current_reads(body) or PENDING_SWITCH_MARK in body:
            steps.append({
                "number": number,
                "target": _with_mark(
                    _strip_mark(body, PENDING_SWITCH_MARK), HISTORY_MARK),
                "revert": body,
                "verify": lambda back: (HISTORY_MARK in back
                                        and PENDING_SWITCH_MARK not in back),
                "patch_fail": "readonly-history 写入未确认",
                "readback_fail": "readonly-history 回读失败",
            })
    compensated: list[int] = []
    if not marker_failures:
        step_failures, compensated, compensation_failures = _marker_steps(
            backend, steps)
        marker_failures.extend(step_failures)
        marker_failures.extend(compensation_failures)
    if marker_failures:
        return {
            "ok": False,
            "wrote": False,
            "status": "pending-switch",
            "reason": "远端标记更新未全部确认,本地保持旧来源,不宣告切换完成;"
                      "已成功步骤已按变更前正文回补",
            "marker_failures": marker_failures,
            "compensated_markers": compensated,
            "tracker": "github-issues",
            "backend": "github-issues",
            "history_root": HISTORY_REL,
            "archived": [],
            "gate_required": False,
            "gate_as_permission": False,
            "real_migration_authorized": False,
            "recovery_destination": GATE_HISTORY_REL,
            "correspondence": correspondence,
        }
    archived = _archive_originals(root, staging)
    copied = _promote_pending(root, staging, config_rel=options.config_rel)
    skills = _switch_skills(plan, unready=unready)
    payload = {
        "status": "switched",
        "tracker": "github-issues",
        "switched_on": today(),
        "history_root": HISTORY_REL,
        "pending_root": str(staging),
        "correspondence": correspondence,
        "archived": archived,
        "gate_required": False,
        "gate_as_permission": False,
        "real_migration_authorized": False,
        "recovery_destination": GATE_HISTORY_REL,
        "client_complete": _client_complete(plan, skills, unready),
        "unready_projects": unready,
        "paused_skills": skills.get("paused") or [],
        "developer_decisions": skills.get("developer_decisions") or [],
        "retired_skills": skills.get("retired_skills") or [],
        "paused_shared_files": skills.get("paused_shared_files") or {},
        "added_skills": skills.get("added_skills") or [],
        "client_home": str(plan.get("client_home") or ""),
        "package_root": str(plan.get("package_root") or ""),
        "new_issues": _current_new_issue_numbers(correspondence),
        "old_issues": _old_issue_numbers(correspondence),
    }
    _save_json(_status_path(root), payload)
    return {
        "ok": True,
        "wrote": copied > 0 or bool(archived),
        "status": "switched",
        "tracker": "github-issues",
        "backend": "github-issues",
        "history_root": HISTORY_REL,
        "archived": archived,
        "gate_required": False,
        "gate_as_permission": False,
        "real_migration_authorized": False,
        "recovery_destination": GATE_HISTORY_REL,
        "correspondence": correspondence,
        "client_complete": _client_complete(plan, skills, unready),
        "unready_projects": unready,
        "paused": list(skills.get("paused") or []),
        "developer_decisions": list(skills.get("developer_decisions") or []),
        "retired_skills": list(skills.get("retired_skills") or []),
        "paused_shared_files": dict(skills.get("paused_shared_files") or {}),
    }


def apply_safe_switch(project_root: Path | str,
                      plan: dict | None = None, *,
                      confirmed: bool = False,
                      config_rel: str = DEFAULT_CONFIG_REL,
                      transport=None, api_base: str | None = None,
                      cache_dir: Path | str | None = None) -> dict:
    """核对通过且确认后切换现行指针与技能来源。未确认不写。"""

    root = Path(project_root)
    options = backend_options(config_rel, transport, api_base, cache_dir)
    if not confirmed:
        return {
            "ok": False,
            "wrote": False,
            "reason": "未确认切换清单,不执行切换",
            "gate_required": False,
            "real_migration_authorized": False,
        }
    plan = plan or _plan_safe_switch(
        root, client_home=None, package_root=None, peer_projects=None,
        options=options)
    if plan.get("already_switched") or _switch_status(root).get("status") == "switched":
        current = _switch_status(root)
        return {
            "ok": True,
            "wrote": False,
            "status": "switched",
            "tracker": current.get("tracker") or plan.get("tracker"),
            "duplicate_avoided": True,
            "gate_required": False,
            "gate_as_permission": False,
            "real_migration_authorized": False,
            "recovery_destination": current.get("recovery_destination") or GATE_HISTORY_REL,
        }
    if not plan.get("ready"):
        return {
            "ok": False,
            "wrote": False,
            "reason": "核对未通过,不切换现行指针",
            "blockers": list(plan.get("blockers") or []),
            "gate_required": False,
            "real_migration_authorized": False,
            "status": plan.get("migration_status") or "blocked",
        }
    # 提升前立即重算核对:清单可能在与确认之间变旧(待切换成果被删改),
    # 旧清单不能替代转换完整性、证据与用户修改检查。
    fresh = _plan_safe_switch(
        root, client_home=None, package_root=None, peer_projects=None,
        options=options)
    if fresh.get("already_switched"):
        current = _switch_status(root)
        return {
            "ok": True,
            "wrote": False,
            "status": "switched",
            "tracker": current.get("tracker") or fresh.get("tracker"),
            "duplicate_avoided": True,
            "gate_required": False,
            "gate_as_permission": False,
            "real_migration_authorized": False,
            "recovery_destination": current.get("recovery_destination") or GATE_HISTORY_REL,
        }
    if not fresh.get("ready"):
        return {
            "ok": False,
            "wrote": False,
            "reason": "确认后待切换成果发生变化,重新核对未通过,不切换现行指针",
            "blockers": list(fresh.get("blockers") or []),
            "gate_required": False,
            "real_migration_authorized": False,
            "status": fresh.get("migration_status") or "blocked",
        }
    if (plan.get("tracker") != fresh.get("tracker")
            or plan.get("correspondence") != fresh.get("correspondence")):
        return {
            "ok": False,
            "wrote": False,
            "reason": "确认后待切换对应关系发生变化,与已确认清单不一致,不切换现行指针",
            "gate_required": False,
            "real_migration_authorized": False,
            "status": fresh.get("migration_status") or "blocked",
        }
    # 包树指纹必须在安装前与已确认计划逐一核对:check 与 run 之间包内容
    # 可能被整体替换,旧清单不能替代对实际包内容的核对。
    package_drift = _package_drift(plan)
    if package_drift:
        return {
            "ok": False,
            "wrote": False,
            "reason": "确认后技能包内容与已确认清单不一致,不安装来源不明的包",
            "changed_package_files": package_drift,
            "gate_required": False,
            "real_migration_authorized": False,
            "status": fresh.get("migration_status") or "blocked",
        }
    tracker = plan.get("tracker") or _tracker_of(root, options.config_rel)
    if tracker == "github-issues":
        return _switch_github(root, plan, options=options)
    return _switch_local(root, plan, options=options)


def read_safe_switch(project_root: Path | str, *,
                     config_rel: str = DEFAULT_CONFIG_REL,
                     transport=None, api_base: str | None = None,
                     cache_dir: Path | str | None = None) -> dict:
    """回读切换状态、现行来源与恢复去向。"""

    root = Path(project_root)
    switched = _switch_status(root)
    plan = _plan_safe_switch(
        root, client_home=None, package_root=None, peer_projects=None,
        options=backend_options(config_rel, transport, api_base, cache_dir))
    status = switched.get("status") or plan.get("migration_status") or "absent"
    recovery = switched.get("recovery_destination") or plan.get("recovery_destination") or ""
    return {
        "wrote": False,
        "status": status,
        "ready": plan.get("ready"),
        "tracker": switched.get("tracker") or plan.get("tracker"),
        "history_root": switched.get("history_root") or "",
        "gate_required": False,
        "gate_as_permission": False,
        "real_migration_authorized": False,
        "recovery_destination": recovery,
        "correspondence": switched.get("correspondence") or plan.get("correspondence") or {},
        "client_complete": switched.get("client_complete"),
        "unready_projects": switched.get("unready_projects") or [],
    }


def _known_task_ids(correspondence: dict) -> set[str]:
    return {str(row.get("identity") or "")
            for row in correspondence.get("tasks") or []
            if row.get("identity")}


def _copy_preserved(src: Path, dest: Path) -> None:
    dest.parent.mkdir(parents=True, exist_ok=True)
    if src.is_dir():
        if dest.exists():
            return
        shutil.copytree(src, dest)
        return
    if src.is_file():
        shutil.copy2(src, dest)


def _preserve_overwritten_live_files(root: Path, preserve_root: Path) -> list[str]:
    """Keep current bytes of every live file history restore would replace."""

    history = root / HISTORY_REL
    live_docs = root / "docs" / "mygamestudio"
    preserved: list[str] = []
    if not history.is_dir() or not live_docs.is_dir():
        return preserved
    for src in history.rglob("*"):
        if not src.is_file():
            continue
        live = live_docs / src.relative_to(history)
        if not live.is_file():
            continue
        if live.read_bytes() == src.read_bytes():
            continue
        rel = str(live.relative_to(live_docs)).replace("\\", "/")
        dest = preserve_root / rel
        _copy_preserved(live, dest)
        preserved.append(rel)
    return preserved


def _preserve_new_additions(root: Path, correspondence: dict,
                            config_rel: str = DEFAULT_CONFIG_REL) -> list[str]:
    import mgs_records  # noqa: PLC0415

    known = _known_task_ids(correspondence)
    preserved: list[str] = []
    preserve_root = root / PRESERVE_REL
    try:
        tasks = mgs_records.list_tasks(root, config_rel)
    except (RecordsError, OSError):
        tasks = []
    work = root / "docs/mygamestudio/work"
    for task in tasks:
        identity = str(task.get("identity") or "")
        if not identity or identity in known:
            continue
        src = work / identity
        dest = preserve_root / identity
        if src.is_dir() and not dest.exists():
            _copy_preserved(src, dest)
            preserved.append(identity)
        elif identity not in preserved:
            preserved.append(identity)
    live_design = root / "docs/mygamestudio/GAME_DESIGN.md"
    if live_design.is_file() and "规格身份:overall" in _read(live_design):
        dest = preserve_root / "GAME_DESIGN.md"
        _copy_preserved(live_design, dest)
        preserved.append("GAME_DESIGN.md")
    for rel in _preserve_overwritten_live_files(root, preserve_root):
        if rel not in preserved:
            preserved.append(rel)
    return preserved


def _restore_history(root: Path) -> int:
    history = root / HISTORY_REL
    live_docs = root / "docs" / "mygamestudio"
    if not history.is_dir():
        return 0
    restored = 0
    for src in history.rglob("*"):
        if not src.is_file():
            continue
        dest = live_docs / src.relative_to(history)
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dest)
        restored += 1
    return restored


def _skills_dir_matches(live: Path, hist: Path) -> bool:
    rels = _skill_file_rels(hist)
    if _skill_file_rels(live) != rels:
        return False
    return all((live / rel).read_bytes() == (hist / rel).read_bytes()
               for rel in rels)


def _restore_switched_skills(status: dict) -> dict:
    """把客户端技能恢复到切换前状态;无法恢复时如实报告不完整。

    恢复依据是切换时留档的 skills-history(被替换/被退役技能的切换前
    副本)与 added_skills(切换新装、此前不存在的入口)。暂停的技能
    保留用户现行内容,不恢复。切换后到回滚前的用户新修改先保存到
    skills-preserved-after-rollback,不用快照静默覆盖。旧状态文件未
    记录 client_home 时无法定位客户端,按回滚不完整上报。
    """

    if "client_home" not in status:
        return {"restored": [], "unresolved": [
            "switch-status 未记录 client_home,客户端技能无法随回滚恢复,"
            "须人工核对客户端技能目录"]}
    home_raw = str(status.get("client_home") or "").strip()
    if not home_raw:
        return {"restored": [], "unresolved": []}
    home = Path(home_raw)
    current = home / "skills"
    history = home / "skills-history"
    if not history.is_dir() and not (status.get("added_skills") or []):
        return {"restored": [], "unresolved": []}
    paused = set(status.get("paused_skills") or []) \
        | set(status.get("developer_decisions") or [])
    preserve_root = home / "skills-preserved-after-rollback"
    restored: list[str] = []
    unresolved: list[str] = []
    for hist in sorted(history.iterdir()) if history.is_dir() else []:
        if not hist.is_dir() or not (hist / "SKILL.md").is_file():
            continue
        name = hist.name
        if name in paused:
            continue
        live = current / name
        if live.is_dir():
            if _skills_dir_matches(live, hist):
                restored.append(name)
                continue
            dest = preserve_root / name
            if not dest.exists():
                dest.parent.mkdir(parents=True, exist_ok=True)
                shutil.copytree(live, dest)
        if live.exists():
            shutil.rmtree(live)
        shutil.copytree(hist, current / name)
        if current.joinpath(name).is_dir() and _skills_dir_matches(
                current / name, hist):
            restored.append(name)
        else:
            unresolved.append(f"skills:{name} 恢复后回读与切换前留档不一致")
    for name in status.get("added_skills") or []:
        live = current / name
        if not live.exists():
            continue
        dest = preserve_root / name
        if not dest.exists():
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.copytree(live, dest)
        shutil.rmtree(live)
        if live.exists():
            unresolved.append(f"skills:{name} 切换新装入口移除失败")
    return {"restored": restored, "unresolved": unresolved}


def rollback_safe_switch(project_root: Path | str,
                         plan: dict | None = None, *,
                         confirmed: bool = False,
                         config_rel: str = DEFAULT_CONFIG_REL,
                         transport=None, api_base: str | None = None,
                         cache_dir: Path | str | None = None) -> dict:
    """回退前先保留新版新增成果,不用迁移前快照覆盖。"""

    root = Path(project_root)
    options = backend_options(config_rel, transport, api_base, cache_dir)
    if not confirmed:
        return {
            "ok": False,
            "wrote": False,
            "reason": "未确认回退,不执行",
            "gate_required": False,
            "real_migration_authorized": False,
        }
    current = _switch_status(root)
    if current.get("status") != "switched":
        return {
            "ok": False,
            "wrote": False,
            "reason": "当前不是已切换状态,不回退",
            "gate_required": False,
            "real_migration_authorized": False,
        }
    correspondence = current.get("correspondence") or (plan or {}).get("correspondence") or {}
    preserved = _preserve_new_additions(
        root, correspondence, config_rel=options.config_rel)
    tracker = current.get("tracker") or _tracker_of(root, options.config_rel)
    if tracker == "github-issues":
        backend = _github_backend(root, options)
        # 回滚同样先按当前 CONFIG 重查 issues-write:授权缺失或不再
        # 匹配时不动远端标记,保持已切换状态。
        denied = _write_denied_reason(backend)
        if denied:
            return {
                "ok": False,
                "wrote": False,
                "status": "switched",
                "reason": "当前 CONFIG 未授予 issues-write,不执行远端标记回退:"
                          f"{denied}",
                "preserved": preserved,
                "correspondence": correspondence,
                "history_root": HISTORY_REL,
                "preserve_root": PRESERVE_REL,
                "gate_required": False,
                "gate_as_permission": False,
                "real_migration_authorized": False,
                "recovery_destination": GATE_HISTORY_REL,
            }
        known = _current_new_issue_numbers(correspondence)
        try:
            import mgs_records  # noqa: PLC0415
            live_tasks = mgs_records.list_tasks(
                root, options.config_rel, transport=options.transport,
                api_base=options.api_base, cache_dir=options.cache_dir)
        except (RecordsError, OSError):
            live_tasks = []
        for task in live_tasks:
            identity = str(task.get("identity") or "")
            number = task.get("issue_number")
            if identity and identity not in _known_task_ids(correspondence):
                preserved.append(identity)
                if isinstance(number, int):
                    known.append(number)
        # 回滚的远端标记必须逐项确认(2xx + 回读):旧权威 Issue 若仍
        # 处于 readonly-history,本地不得恢复旧件并宣告 rolled-back。
        # 迭代收集到的全部新 Issue 号(迁移期 + 切换后新增):切换后
        # 新增任务只进 preserved 不打标记,会在恢复旧权威后同时留在
        # 现行读取集里。
        marker_failures: list[str] = []
        steps: list[dict] = []
        old_numbers = set(_old_issue_numbers(correspondence))
        for number in dict.fromkeys(
                issue for issue in known if isinstance(issue, int)):
            if number in old_numbers:
                continue
            read_ok, body = _read_issue_body(backend, number)
            if not read_ok:
                marker_failures.append(_marker_failure(
                    number, "pending-switch 读取未确认"))
                continue
            steps.append({
                "number": number,
                "target": _with_mark(
                    _strip_mark(body, HISTORY_MARK), PENDING_SWITCH_MARK),
                "revert": body,
                "verify": lambda back: (PENDING_SWITCH_MARK in back
                                        and HISTORY_MARK not in back),
                "patch_fail": "pending-switch 恢复未确认",
                "readback_fail": "pending-switch 回读失败",
            })
        for number in _old_issue_numbers(correspondence):
            read_ok, body = _read_issue_body(backend, number)
            if not read_ok:
                marker_failures.append(_marker_failure(
                    number, "readonly-history 读取未确认"))
                continue
            steps.append({
                "number": number,
                "target": _strip_mark(body, HISTORY_MARK),
                "revert": body,
                "verify": lambda back: HISTORY_MARK not in back,
                "patch_fail": "readonly-history 移除未确认",
                "readback_fail": "readonly-history 回读仍在",
            })
        compensated: list[int] = []
        if not marker_failures:
            step_failures, compensated, compensation_failures = _marker_steps(
                backend, steps)
            marker_failures.extend(step_failures)
            marker_failures.extend(compensation_failures)
        if marker_failures:
            return {
                "ok": False,
                "wrote": False,
                "status": "switched",
                "reason": "远端标记回退未全部确认,保持已切换状态,不回退本地;"
                          "已成功步骤已按变更前正文回补",
                "marker_failures": marker_failures,
                "compensated_markers": compensated,
                "preserved": preserved,
                "correspondence": correspondence,
                "history_root": HISTORY_REL,
                "preserve_root": PRESERVE_REL,
                "gate_required": False,
                "gate_as_permission": False,
                "real_migration_authorized": False,
                "recovery_destination": GATE_HISTORY_REL,
            }
    skills_state = _restore_switched_skills(current)
    restored = _restore_history(root)
    payload = dict(current)
    payload.update({
        "preserved": preserved,
        "preserve_root": PRESERVE_REL,
        "rolled_back_on": today(),
        "skills_restored": skills_state["restored"],
        "skills_unresolved": skills_state["unresolved"],
    })
    if skills_state["unresolved"]:
        # 客户端技能没有全部恢复:项目记录已回到旧权威,客户端不能停在
        # 可能不兼容的新技能集上被宣告 rolled-back,按回滚不完整上报。
        payload["status"] = "rolled-back-incomplete"
        _save_json(_status_path(root), payload)
        return {
            "ok": False,
            "wrote": restored > 0 or bool(preserved),
            "status": "rolled-back-incomplete",
            "reason": "客户端技能未能全部恢复到切换前状态,回滚不完整:"
                      + ";".join(skills_state["unresolved"]),
            "preserved": preserved,
            "skills_restored": skills_state["restored"],
            "skills_unresolved": skills_state["unresolved"],
            "correspondence": correspondence,
            "history_root": HISTORY_REL,
            "preserve_root": PRESERVE_REL,
            "gate_required": False,
            "gate_as_permission": False,
            "real_migration_authorized": False,
            "recovery_destination": GATE_HISTORY_REL,
        }
    payload["status"] = "rolled-back"
    _save_json(_status_path(root), payload)
    return {
        "ok": True,
        "wrote": restored > 0 or bool(preserved),
        "status": "rolled-back",
        "preserved": preserved,
        "skills_restored": skills_state["restored"],
        "correspondence": correspondence,
        "history_root": HISTORY_REL,
        "preserve_root": PRESERVE_REL,
        "gate_required": False,
        "gate_as_permission": False,
        "real_migration_authorized": False,
        "recovery_destination": GATE_HISTORY_REL,
    }

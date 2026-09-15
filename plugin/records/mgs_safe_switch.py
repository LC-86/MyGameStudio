#!/usr/bin/env python3
"""用户修改、同名来源与安全切换(issue #59)。

资料完整迁移后,核对来源、版本、用户修改、转换完整性、证据可达和准备期间
新增变更,通过后才切换现行指针与对应技能来源。同名技能只保留一个明确有效
来源;共用客户端未就绪项目保留旧环境;回退先保留新版新增成果。
普通路径不经 mgs-gate。不把功能实现当作真实环境迁移授权。

公开 interface(经 mgs_records 再导出):
  plan_safe_switch(project_root, ...) -> dict
  apply_safe_switch(project_root, plan, *, confirmed) -> dict
  read_safe_switch(project_root) -> dict
  rollback_safe_switch(project_root, plan, *, confirmed) -> dict
"""

from __future__ import annotations

import hashlib
import json
import re
import shutil
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))

from mgs_github_issue import (  # noqa: E402
    HISTORY_MARK, PENDING_SWITCH_MARK, skip_from_current_reads)
from mgs_github_transport import repo_path  # noqa: E402
from mgs_record_model import RecordsError, today  # noqa: E402
from mgs_record_source import DEFAULT_CONFIG_REL, load_config  # noqa: E402
from mgs_spec import read_current_design  # noqa: E402

PENDING_REL = "docs/mygamestudio/records/pending-switch"
HISTORY_REL = "docs/mygamestudio/records/readonly-history"
PRESERVE_REL = "docs/mygamestudio/records/preserved-after-rollback"
STATUS_NAME = "switch-status.json"
GATE_HISTORY_REL = "docs/mygamestudio/records/gate-history.md"


def _sha_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _pending_root(root: Path) -> Path:
    return root / PENDING_REL


def _status_path(root: Path) -> Path:
    return _pending_root(root) / STATUS_NAME


def _load_json(path: Path) -> dict:
    if not path.is_file():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}
    return data if isinstance(data, dict) else {}


def _save_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
                    encoding="utf-8")


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8") if path.is_file() else ""


def _write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text if text.endswith("\n") else text + "\n", encoding="utf-8")


def _tracker_of(root: Path) -> str:
    config_path = root / DEFAULT_CONFIG_REL
    if not config_path.is_file():
        return "local-markdown"
    config = load_config(root)
    backend = str(config.get("backend") or "local-markdown")
    return backend if backend in {"local-markdown", "github-issues"} else "local-markdown"


def _switch_status(root: Path) -> dict:
    return _load_json(_status_path(root))


def _migration_report(root: Path, *, transport=None, api_base=None,
                      cache_dir=None) -> dict:
    tracker = _tracker_of(root)
    if tracker == "github-issues":
        import mgs_github_material_migration  # noqa: PLC0415
        return mgs_github_material_migration.read_github_material_migration(
            root, transport=transport, api_base=api_base, cache_dir=cache_dir)
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


def _converted_overall(root: Path, report: dict, *, transport=None,
                       api_base=None, cache_dir=None) -> str:
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
        backend = _github_backend(
            root, transport=transport, api_base=api_base, cache_dir=cache_dir)
        return _read_issue_body(backend, int(overall_no))
    except (RecordsError, OSError, TypeError, ValueError):
        return ""


def _user_edits_ok(root: Path, report: dict, *, transport=None,
                   api_base=None, cache_dir=None) -> bool:
    live = _read(root / "docs/mygamestudio/GAME_DESIGN.md")
    if "用户补充" not in live:
        return True
    extra = live.split("用户补充", 1)[-1]
    snippet = extra.strip().splitlines()
    snippet = [line for line in snippet if line and not line.startswith("#")]
    if not snippet or not snippet[0].lstrip("- ").strip():
        return True
    needle = snippet[0].lstrip("- ").strip()
    overall = _converted_overall(
        root, report, transport=transport, api_base=api_base, cache_dir=cache_dir)
    return needle in overall


def _checks_from(root: Path, report: dict, *,
                 fingerprints: dict[str, str] | None = None,
                 transport=None, api_base=None, cache_dir=None) -> dict[str, Any]:
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
        "user_edits": _user_edits_ok(
            root, report, transport=transport, api_base=api_base,
            cache_dir=cache_dir),
        "conversion_complete": complete and not paused and not missing,
        "evidence_reachable": reachable,
        "preparation_changes": prep_ok,
    }


def plan_safe_switch(project_root: Path | str, *,
                     client_home: Path | str | None = None,
                     package_root: Path | str | None = None,
                     peer_projects: list[Path | str] | None = None,
                     transport=None, api_base: str | None = None,
                     cache_dir: Path | str | None = None) -> dict:
    """只读核对照切换条件。不写入,不切换现行指针或技能来源。"""

    root = Path(project_root)
    if not root.is_dir():
        raise RecordsError(f"目标项目不存在:{root}")
    switched = _switch_status(root)
    report = _migration_report(
        root, transport=transport, api_base=api_base, cache_dir=cache_dir)
    fingerprints = _source_fingerprints(root, report.get("correspondence") or {})
    checks = _checks_from(
        root, report, fingerprints=fingerprints, transport=transport,
        api_base=api_base, cache_dir=cache_dir)
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
    return {
        "wrote": False,
        "ready": ready,
        "status": "planned",
        "tracker": report.get("tracker") or _tracker_of(root),
        "backend": report.get("tracker") or _tracker_of(root),
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
        "already_switched": already,
    }


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
        if not dest.exists():
            shutil.copy2(live, dest)
            archived.append(str(dest.relative_to(root)).replace("\\", "/"))
    return archived


def _promote_pending(root: Path, staging: Path) -> int:
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
    config_path = root / DEFAULT_CONFIG_REL
    if config_path.is_file():
        _write(config_path, _mark_switched_config(_read(config_path)))
    return copied


def _peer_unready(peer_projects: list, *, transport=None, api_base=None,
                  cache_dir=None) -> list[str]:
    unready: list[str] = []
    for peer in peer_projects or []:
        path = Path(peer)
        if not path.is_dir():
            unready.append(str(path))
            continue
        if _switch_status(path).get("status") == "switched":
            continue
        report = _migration_report(
            path, transport=transport, api_base=api_base, cache_dir=cache_dir)
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
    paused_shared_files: dict[str, list[str]] = {}
    for name, pkg_dir in pkg_skills.items():
        user_dir = user_skills.get(name)
        pkg_text = _read(pkg_dir / "SKILL.md")
        if user_dir is not None:
            user_text = _read(user_dir / "SKILL.md")
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


def _switch_local(root: Path, plan: dict) -> dict:
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
    archived = _archive_originals(root, staging)
    copied = _promote_pending(root, staging)
    correspondence = plan.get("correspondence") or {}
    unready = _peer_unready(plan.get("peer_projects") or [])
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


def _github_backend(root: Path, *, transport=None, api_base=None, cache_dir=None):
    import mgs_github  # noqa: PLC0415

    config = dict(load_config(root))
    config["project_root"] = str(root)
    if transport is None:
        transport = mgs_github.UrllibTransport(
            api_base=mgs_github.api_base_for(config, api_base),
            token=mgs_github.token_from_env())
    return mgs_github.GithubBackend(config, transport, cache_dir)


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


def _patch_issue_body(backend, number: int, body: str) -> bool:
    """PATCH 正文;仅 2xx 视为成功。忽略状态会把远端失败当成已切换。"""

    status, _issue = backend.transport.request(
        "PATCH", f"{repo_path(backend.repo)}/issues/{number}", {"body": body})
    return status in (200, 201)


def _read_issue_body(backend, number: int) -> str:
    _status, issue = backend.transport.request(
        "GET", f"{repo_path(backend.repo)}/issues/{number}")
    return (issue or {}).get("body") or ""


def _switch_github(root: Path, plan: dict, *, transport=None,
                   api_base=None, cache_dir=None) -> dict:
    staging = _pending_root(root)
    backend = _github_backend(
        root, transport=transport, api_base=api_base, cache_dir=cache_dir)
    correspondence = plan.get("correspondence") or {}
    # 远端标记迁移必须先于本地提升逐项确认:PATCH 成功且回读到目标状态
    # 才允许归档旧件、提升新件;任何一项未确认时本地保持旧来源,
    # 不写 switch-status。先提升再打标记会让本地指向新源而 GitHub
    # 仍停留旧源或混合源。
    marker_failures: list[str] = []
    for number in _current_new_issue_numbers(correspondence):
        body = _read_issue_body(backend, number)
        if PENDING_SWITCH_MARK in body:
            target = _strip_mark(body, PENDING_SWITCH_MARK)
            if not _patch_issue_body(backend, number, target):
                marker_failures.append(f"#{number}:pending-switch 移除未确认")
                continue
            if PENDING_SWITCH_MARK in _read_issue_body(backend, number):
                marker_failures.append(f"#{number}:pending-switch 回读仍在")
    for number in _old_issue_numbers(correspondence):
        body = _read_issue_body(backend, number)
        if not skip_from_current_reads(body) or PENDING_SWITCH_MARK in body:
            target = _with_mark(
                _strip_mark(body, PENDING_SWITCH_MARK), HISTORY_MARK)
            if not _patch_issue_body(backend, number, target):
                marker_failures.append(f"#{number}:readonly-history 写入未确认")
                continue
            back = _read_issue_body(backend, number)
            if HISTORY_MARK not in back or PENDING_SWITCH_MARK in back:
                marker_failures.append(f"#{number}:readonly-history 回读失败")
    if marker_failures:
        return {
            "ok": False,
            "wrote": False,
            "status": "pending-switch",
            "reason": "远端标记更新未全部确认,本地保持旧来源,不宣告切换完成",
            "marker_failures": marker_failures,
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
    copied = _promote_pending(root, staging)
    unready = _peer_unready(plan.get("peer_projects") or [])
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
                      transport=None, api_base: str | None = None,
                      cache_dir: Path | str | None = None) -> dict:
    """核对通过且确认后切换现行指针与技能来源。未确认不写。"""

    root = Path(project_root)
    if not confirmed:
        return {
            "ok": False,
            "wrote": False,
            "reason": "未确认切换清单,不执行切换",
            "gate_required": False,
            "real_migration_authorized": False,
        }
    plan = plan or plan_safe_switch(
        root, transport=transport, api_base=api_base, cache_dir=cache_dir)
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
    fresh = plan_safe_switch(
        root, transport=transport, api_base=api_base, cache_dir=cache_dir)
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
    tracker = plan.get("tracker") or _tracker_of(root)
    if tracker == "github-issues":
        return _switch_github(
            root, plan, transport=transport, api_base=api_base,
            cache_dir=cache_dir)
    return _switch_local(root, plan)


def read_safe_switch(project_root: Path | str, *,
                     transport=None, api_base: str | None = None,
                     cache_dir: Path | str | None = None) -> dict:
    """回读切换状态、现行来源与恢复去向。"""

    root = Path(project_root)
    switched = _switch_status(root)
    plan = plan_safe_switch(
        root, transport=transport, api_base=api_base, cache_dir=cache_dir)
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


def _preserve_new_additions(root: Path, correspondence: dict) -> list[str]:
    import mgs_records  # noqa: PLC0415

    known = _known_task_ids(correspondence)
    preserved: list[str] = []
    preserve_root = root / PRESERVE_REL
    try:
        tasks = mgs_records.list_tasks(root)
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


def rollback_safe_switch(project_root: Path | str,
                         plan: dict | None = None, *,
                         confirmed: bool = False,
                         transport=None, api_base: str | None = None,
                         cache_dir: Path | str | None = None) -> dict:
    """回退前先保留新版新增成果,不用迁移前快照覆盖。"""

    root = Path(project_root)
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
    preserved = _preserve_new_additions(root, correspondence)
    tracker = current.get("tracker") or _tracker_of(root)
    if tracker == "github-issues":
        backend = _github_backend(
            root, transport=transport, api_base=api_base, cache_dir=cache_dir)
        known = _current_new_issue_numbers(correspondence)
        try:
            import mgs_records  # noqa: PLC0415
            live_tasks = mgs_records.list_tasks(
                root, transport=transport, api_base=api_base, cache_dir=cache_dir)
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
        marker_failures: list[str] = []
        for number in _current_new_issue_numbers(correspondence):
            if number in known and number not in _old_issue_numbers(correspondence):
                body = _read_issue_body(backend, number)
                target = _with_mark(
                    _strip_mark(body, HISTORY_MARK), PENDING_SWITCH_MARK)
                if not _patch_issue_body(backend, number, target):
                    marker_failures.append(f"#{number}:pending-switch 恢复未确认")
                    continue
                back = _read_issue_body(backend, number)
                if HISTORY_MARK in back or PENDING_SWITCH_MARK not in back:
                    marker_failures.append(f"#{number}:pending-switch 回读失败")
        for number in _old_issue_numbers(correspondence):
            body = _read_issue_body(backend, number)
            target = _strip_mark(body, HISTORY_MARK)
            if not _patch_issue_body(backend, number, target):
                marker_failures.append(f"#{number}:readonly-history 移除未确认")
                continue
            if HISTORY_MARK in _read_issue_body(backend, number):
                marker_failures.append(f"#{number}:readonly-history 回读仍在")
        if marker_failures:
            return {
                "ok": False,
                "wrote": False,
                "status": "switched",
                "reason": "远端标记回退未全部确认,保持已切换状态,不回退本地",
                "marker_failures": marker_failures,
                "preserved": preserved,
                "correspondence": correspondence,
                "history_root": HISTORY_REL,
                "preserve_root": PRESERVE_REL,
                "gate_required": False,
                "gate_as_permission": False,
                "real_migration_authorized": False,
                "recovery_destination": GATE_HISTORY_REL,
            }
    restored = _restore_history(root)
    payload = dict(current)
    payload.update({
        "status": "rolled-back",
        "preserved": preserved,
        "preserve_root": PRESERVE_REL,
        "rolled_back_on": today(),
    })
    _save_json(_status_path(root), payload)
    return {
        "ok": True,
        "wrote": restored > 0 or bool(preserved),
        "status": "rolled-back",
        "preserved": preserved,
        "correspondence": correspondence,
        "history_root": HISTORY_REL,
        "preserve_root": PRESERVE_REL,
        "gate_required": False,
        "gate_as_permission": False,
        "real_migration_authorized": False,
        "recovery_destination": GATE_HISTORY_REL,
    }

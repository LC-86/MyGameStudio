#!/usr/bin/env python3
"""Evaluate a pinned upstream candidate against the adopted plugin pin.

Release-time public seams: evaluate_upstream_upgrade, apply_upstream_upgrade,
read_upstream_adoption. One-shot comparison; not a continuous update service.
"""

from __future__ import annotations

import hashlib
import json
import re
import shutil
from pathlib import Path

SHA_RE = re.compile(r"^[0-9a-f]{40}$")
UNPINNED = {"latest", "head", "main", "origin/main", "origin/master", "master"}
GAME_ENTRIES = ("game-producer", "game-init", "game-design")
OFFICIAL_BUCKETS = ("engineering", "productivity")
EXPERIMENTAL_BUCKETS = ("experimental", "misc", "in-progress")
EXTERNAL_PREFIXES = ("http://", "https://", "mailto:")
STAGE_REL = "internal/game/stage-requirements.md"
STAGE_POINTER = "../../internal/game/stage-requirements.md"
STAGE_BLOCK = (
    "\n\n## MyGameStudio stage materials\n\n"
    "When working in a MyGameStudio game project, read "
    f"[stage requirements]({STAGE_POINTER}) for the current work stage "
    "before applying this skill's method. Reading those materials does "
    "not start production.\n"
)
MATT_PATHS = ("implement", "to-spec", "to-tickets")

FRONTMATTER = re.compile(r"^---\n(.*?)\n---\n", re.DOTALL)
MD_LINK = re.compile(r"\]\(([^)\s]+)\)")
EXAMPLE_LINK = re.compile(r"^(link|./src/)")


def _root(path: Path | str) -> Path:
    return Path(path).resolve()


def _load_json(path: Path) -> dict:
    if not path.is_file():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def _fingerprints(plugin_root: Path) -> dict:
    return _load_json(plugin_root / "provenance" / "fingerprints.json")


def _is_pinned_sha(value: str) -> bool:
    text = (value or "").strip().lower()
    if not text or text in UNPINNED:
        return False
    return bool(SHA_RE.fullmatch(text))


def _frontmatter(text: str) -> str:
    match = FRONTMATTER.match(text)
    return match.group(1) if match else ""


def _is_user_only(text: str) -> bool:
    return "disable-model-invocation: true" in _frontmatter(text)


def _skill_dirs(root: Path) -> list[str]:
    if not root.is_dir():
        return []
    return sorted(
        path.name for path in root.iterdir()
        if path.is_dir() and (path / "SKILL.md").is_file()
    )


def _current_official(plugin: Path) -> list[str]:
    names = _skill_dirs(plugin / "skills")
    return [name for name in names if name not in GAME_ENTRIES]


def _candidate_skills(candidate: Path, buckets: tuple[str, ...]) -> tuple[dict[str, Path], list[str]]:
    found: dict[str, Path] = {}
    duplicates: list[str] = []
    skills = candidate / "skills"
    if not skills.is_dir():
        return found, duplicates
    for bucket in buckets:
        folder = skills / bucket
        if not folder.is_dir():
            continue
        for path in folder.iterdir():
            skill_md = path / "SKILL.md"
            if path.is_dir() and skill_md.is_file():
                if path.name in found:
                    duplicates.append(path.name)
                found[path.name] = skill_md
    return found, duplicates


def _license_of(path: Path) -> str:
    if not path.is_file():
        return ""
    text = path.read_text(encoding="utf-8")
    if "MIT License" in text:
        return "MIT"
    return "unknown"


def _broken_refs(root: Path, files: list[Path]) -> list[str]:
    broken: list[str] = []
    for md in files:
        try:
            rel_md = str(md.relative_to(root))
        except ValueError:
            rel_md = str(md)
        text = md.read_text(encoding="utf-8")
        for target in MD_LINK.findall(text):
            if target.startswith(EXTERNAL_PREFIXES) or target.startswith("#"):
                continue
            rel = target.split("#", 1)[0]
            if not rel or EXAMPLE_LINK.match(rel):
                continue
            if STAGE_REL in rel or rel.endswith("stage-requirements.md"):
                continue
            resolved = (md.parent / rel).resolve()
            if not resolved.exists():
                broken.append(f"{rel_md}:{target}")
    return broken


def _write_evaluation(plugin: Path, evaluation: dict) -> Path:
    sha = str((evaluation.get("candidate") or {}).get("sha") or "unpinned")
    folder = plugin / "provenance" / "upgrade-evaluations"
    folder.mkdir(parents=True, exist_ok=True)
    path = folder / f"{sha}.json"
    evaluation["record"] = str(path.relative_to(plugin))
    serializable = json.loads(json.dumps(evaluation))
    candidate = serializable.get("candidate") or {}
    candidate.pop("root", None)
    serializable["candidate"] = candidate
    path.write_text(json.dumps(serializable, indent=2, ensure_ascii=False) + "\n",
                    encoding="utf-8")
    return path


def read_upstream_adoption(plugin_root: Path | str) -> dict:
    """Return the currently adopted upstream pin."""

    data = _fingerprints(_root(plugin_root))
    upstream = data.get("upstream") or {}
    return {
        "name": upstream.get("name") or "mattpocock/skills",
        "version": upstream.get("version") or "",
        "sha": upstream.get("sha") or "",
        "license": upstream.get("license") or "",
    }


def _fingerprint_by_path(data: dict) -> dict:
    files = data.get("files") or []
    return {entry.get("path"): entry for entry in files if isinstance(entry, dict)}


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _stage_loadable(plugin: Path, skill: str) -> bool:
    skill_md = plugin / "skills" / skill / "SKILL.md"
    stage = plugin / STAGE_REL
    if not skill_md.is_file() or not stage.is_file():
        return False
    text = skill_md.read_text(encoding="utf-8")
    if STAGE_POINTER not in text and STAGE_REL not in text:
        return False
    return (skill_md.parent / STAGE_POINTER).resolve() == stage.resolve()


def _new_materials(candidate: Path, official_files: dict[str, Path]) -> list[str]:
    keep = set()
    license_file = candidate / "LICENSE"
    if license_file.is_file():
        keep.add(license_file.resolve())
    for skill_md in official_files.values():
        keep.add(skill_md.resolve())
        for path in skill_md.parent.rglob("*"):
            if path.is_file():
                keep.add(path.resolve())
    skills_root = candidate / "skills"
    if skills_root.is_dir():
        for bucket in EXPERIMENTAL_BUCKETS:
            folder = skills_root / bucket
            if not folder.is_dir():
                continue
            for path in folder.rglob("*"):
                if path.is_file():
                    keep.add(path.resolve())
    extras: list[str] = []
    for path in candidate.rglob("*"):
        if not path.is_file():
            continue
        if path.resolve() in keep:
            continue
        extras.append(str(path.relative_to(candidate)))
    return sorted(extras)


def _classify_adaptations(plugin: Path, candidate: Path,
                          candidate_official: dict[str, Path],
                          broken: list[str]) -> list[dict]:
    data = _fingerprints(plugin)
    by_path = _fingerprint_by_path(data)
    items: list[dict] = []
    for name in _current_official(plugin):
        rel = f"skills/{name}/SKILL.md"
        entry = by_path.get(rel) or {}
        current_path = plugin / rel
        candidate_path = candidate_official.get(name)
        current_hash = _sha256(current_path) if current_path.is_file() else ""
        original_hash = entry.get("original_sha256") or ""
        adapted = bool(entry.get("adaptation")) or (
            original_hash and original_hash != current_hash
        )
        if not adapted:
            continue
        record = {"skill": name, "path": rel, "status": "still-needed"}
        if candidate_path is None:
            record["status"] = "conflict"
            items.append(record)
            continue
        candidate_hash = _sha256(candidate_path)
        try:
            candidate_rel = str(candidate_path.relative_to(candidate))
        except ValueError:
            candidate_rel = candidate_path.name
        has_broken = any(item.startswith(candidate_rel + ":") for item in broken)
        if candidate_hash == current_hash:
            record["status"] = "resolved-by-upstream"
        elif original_hash and candidate_hash == original_hash:
            record["status"] = "conflict" if has_broken else "still-needed"
        elif STAGE_REL in candidate_path.read_text(encoding="utf-8"):
            record["status"] = "conflict" if has_broken else "resolved-by-upstream"
        elif has_broken:
            record["status"] = "conflict"
        else:
            record["status"] = "still-needed"
        items.append(record)
    return items


def _mgs_tail(text: str) -> str:
    marker = "## MyGameStudio stage materials"
    index = text.find(marker)
    if index < 0:
        return ""
    return text[index:].strip()


COMMIT_AUTH = (
    "If commit authorization is present, commit your work to the "
    "current branch. If it is not, leave the work uncommitted."
)


def _has_commit_authorization(text: str) -> bool:
    lower = (text or "").lower()
    return (
        "commit authorization is present" in lower
        and "leave the work uncommitted" in lower
    )


def _strip_unconditional_commit(text: str) -> str:
    lines = []
    for line in (text or "").splitlines():
        if re.fullmatch(r"Commit your work to the current branch\.?", line.strip()):
            continue
        lines.append(line)
    return "\n".join(lines)


def _merge_adaptations(candidate: str, previous: str) -> str:
    text = _strip_unconditional_commit(candidate)
    if _has_commit_authorization(previous) and not _has_commit_authorization(text):
        marker = "## MyGameStudio stage materials"
        if marker in text:
            text = text.replace(marker, COMMIT_AUTH + "\n\n" + marker, 1)
        else:
            text = text.rstrip() + "\n\n" + COMMIT_AUTH + "\n"
    tail = _mgs_tail(previous)
    if tail and tail not in text:
        text = text.rstrip() + "\n\n" + tail + "\n"
    elif STAGE_REL not in text and STAGE_POINTER not in text:
        text = text.rstrip() + STAGE_BLOCK
    return text if text.endswith("\n") else text + "\n"


def _keep_existing_adaptations(dest: Path, previous: str, original_hash: str) -> None:
    """Keep current adaptations when the candidate still needs them."""

    if not dest.is_file():
        return
    candidate_hash = _sha256(dest)
    if original_hash and candidate_hash == original_hash and previous:
        dest.write_text(previous, encoding="utf-8")
        return
    dest.write_text(
        _merge_adaptations(dest.read_text(encoding="utf-8"), previous),
        encoding="utf-8")


def _public_skills(plugin: Path) -> list[str]:
    return _skill_dirs(plugin / "skills")


def evaluate_upstream_upgrade(
    plugin_root: Path | str,
    candidate_root: Path | str,
    *,
    candidate_version: str,
    candidate_sha: str,
    collection_decisions: dict | None = None,
    new_material_decisions: dict | None = None,
) -> dict:
    """Compare a fixed candidate with the adopted pin. Does not write the pin."""

    plugin = _root(plugin_root)
    candidate = _root(candidate_root)
    current = read_upstream_adoption(plugin)
    decisions = dict(collection_decisions or {})
    material_decisions = dict(new_material_decisions or {})
    evaluation = {
        "current": current,
        "candidate": {
            "version": candidate_version,
            "sha": candidate_sha,
            "root": str(candidate),
        },
        "decision": "retain",
        "retain_reason": None,
        "scope": {
            "clients": ["codex"],
            "continuous_update": False,
        },
        "collection_decisions": decisions,
        "new_material_decisions": material_decisions,
    }
    current_official = _current_official(plugin)
    official_files, official_dupes = _candidate_skills(candidate, OFFICIAL_BUCKETS)
    experimental_files, _exp_dupes = _candidate_skills(candidate, EXPERIMENTAL_BUCKETS)
    candidate_official = sorted(official_files)
    added = sorted(set(candidate_official) - set(current_official))
    retired = sorted(set(current_official) - set(candidate_official))
    experimental = sorted(experimental_files)
    promoted = sorted(set(experimental) & set(candidate_official))
    evaluation["collection"] = {
        "current_official": current_official,
        "candidate_official": candidate_official,
        "added": added,
        "retired": retired,
        "experimental": experimental,
        "experimental_promoted": promoted,
    }

    invocation_changes = []
    for name, cand_path in official_files.items():
        current_path = plugin / "skills" / name / "SKILL.md"
        if not current_path.is_file():
            continue
        before = _is_user_only(current_path.read_text(encoding="utf-8"))
        after = _is_user_only(cand_path.read_text(encoding="utf-8"))
        if before != after:
            invocation_changes.append({
                "skill": name,
                "from": "user-only" if before else "model-invocable",
                "to": "user-only" if after else "model-invocable",
            })
    evaluation["invocation"] = {"changes": invocation_changes}

    current_license = current.get("license") or "MIT"
    candidate_license = _license_of(candidate / "LICENSE")
    license_info = {
        "current": current_license,
        "candidate": candidate_license or "",
        "conflict": (not candidate_license) or candidate_license != current_license,
    }
    evaluation["license"] = license_info

    md_files = [path for path in candidate.rglob("*.md") if path.is_file()]
    broken = _broken_refs(candidate, md_files)
    evaluation["references"] = {"broken": broken}
    adaptations = _classify_adaptations(plugin, candidate, official_files, broken)
    evaluation["adaptations"] = adaptations

    new_materials = _new_materials(candidate, official_files)
    load_names = list(GAME_ENTRIES) + [name for name in MATT_PATHS if name in current_official]
    evaluation["materials"] = {
        "game_entries": list(GAME_ENTRIES),
        "matt_paths": [name for name in MATT_PATHS if name in current_official],
        "loadable": all(_stage_loadable(plugin, name) for name in load_names),
        "new_materials": new_materials,
    }

    unevaluated_collection = [
        name for name in added + retired + experimental + promoted
        if name not in decisions
    ]
    unevaluated_materials = [
        rel for rel in new_materials if rel not in material_decisions
    ]
    game_collision = [name for name in candidate_official if name in GAME_ENTRIES]
    adaptation_conflicts = [
        item["skill"] for item in adaptations if item.get("status") == "conflict"
    ]
    would_be_official = [
        name for name in candidate_official
        if name not in added or decisions.get(name) == "adopt"
    ]
    would_be_official = [
        name for name in would_be_official if decisions.get(name) != "defer"
        and decisions.get(name) != "reject"
    ]
    for name in current_official:
        if name in retired and decisions.get(name) in {"defer", "reject"}:
            if name not in would_be_official:
                would_be_official.append(name)
    unique_ok = not official_dupes and not game_collision
    public = _public_skills(plugin)
    expected_public = sorted(list(current_official) + list(GAME_ENTRIES))
    verification = {
        "official_collection": sorted(would_be_official) == sorted(current_official)
        and public == expected_public,
        "references_closed": not broken,
        "license": (not license_info["conflict"]) and candidate_license == "MIT",
        "adaptations_recorded": all("status" in item for item in adaptations),
        "materials_loadable": evaluation["materials"]["loadable"],
        "unique_sources": unique_ok,
    }
    verification["passed"] = all(verification.values())
    evaluation["verification"] = verification

    reason = None
    if not _is_pinned_sha(candidate_sha) or str(candidate_version).strip().lower() in UNPINNED:
        reason = "unpinned-candidate"
    elif invocation_changes:
        reason = "invocation-change"
    elif broken:
        reason = "broken-reference"
    elif official_dupes or game_collision or adaptation_conflicts:
        reason = "source-conflict"
    elif unevaluated_collection:
        reason = "unevaluated-collection-change"
    elif unevaluated_materials:
        reason = "unevaluated-new-material"
    elif license_info["conflict"]:
        reason = "license-conflict"
    elif not verification["passed"]:
        reason = "verification-failed"

    if reason is None:
        evaluation["decision"] = "adopt"
        evaluation["retain_reason"] = None
    else:
        evaluation["decision"] = "retain"
        evaluation["retain_reason"] = reason
    _write_evaluation(plugin, evaluation)
    return evaluation


def _update_manifest_pin(plugin: Path, version: str, sha: str) -> None:
    path = plugin / "provenance" / "manifest.md"
    if not path.is_file():
        return
    text = path.read_text(encoding="utf-8")
    text = re.sub(r"\*\*[0-9]+\.[0-9]+\.[0-9]+\*\*", f"**{version}**", text, count=1)
    text = re.sub(r"`[0-9a-f]{40}`", f"`{sha}`", text, count=1)
    path.write_text(text, encoding="utf-8")


def _adopt_candidate(plugin: Path, evaluation: dict) -> dict:
    candidate = Path(evaluation["candidate"]["root"])
    sha = evaluation["candidate"]["sha"]
    version = evaluation["candidate"]["version"]
    official_files, _dupes = _candidate_skills(candidate, OFFICIAL_BUCKETS)
    fingerprints = _fingerprints(plugin)
    by_path = _fingerprint_by_path(fingerprints)
    decisions = evaluation.get("collection_decisions") or {}
    for name, skill_md in official_files.items():
        if name in GAME_ENTRIES:
            continue
        if decisions.get(name) in {"reject", "defer"}:
            continue
        dest_dir = plugin / "skills" / name
        dest_dir.mkdir(parents=True, exist_ok=True)
        dest_skill = dest_dir / "SKILL.md"
        previous = dest_skill.read_text(encoding="utf-8") if dest_skill.is_file() else ""
        previous_original = (by_path.get(f"skills/{name}/SKILL.md") or {}).get("original_sha256") or ""
        for src in skill_md.parent.rglob("*"):
            if not src.is_file():
                continue
            dest = dest_dir / src.relative_to(skill_md.parent)
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src, dest)
        dest_skill = dest_dir / "SKILL.md"
        original_hash = _sha256(dest_skill)
        if previous:
            _keep_existing_adaptations(dest_skill, previous, previous_original)
        rel = f"skills/{name}/SKILL.md"
        try:
            source_rel = str(skill_md.relative_to(candidate))
        except ValueError:
            source_rel = f"skills/{name}/SKILL.md"
        entry = dict(by_path.get(rel) or {
            "path": rel,
            "source": "",
            "license": "MIT,见 licenses/mattpocock-skills-LICENSE.txt",
        })
        entry["path"] = rel
        entry["original_sha256"] = original_hash
        entry["sha256"] = _sha256(dest_skill)
        entry["source"] = f"github.com/mattpocock/skills @ {sha} {source_rel}"
        entry["license"] = entry.get("license") or "MIT,见 licenses/mattpocock-skills-LICENSE.txt"
        if entry["sha256"] != entry["original_sha256"]:
            entry["adaptation"] = (
                "Append MyGameStudio stage-materials pointer. "
                "Upstream method body unchanged."
            )
        else:
            entry.pop("adaptation", None)
        by_path[rel] = entry
        prefix = f"skills/{name}/"
        live_rels = {rel}
        for path in dest_dir.rglob("*"):
            if not path.is_file():
                continue
            support_rel = str(path.relative_to(plugin)).replace("\\", "/")
            live_rels.add(support_rel)
            if support_rel == rel:
                continue
            try:
                cand_rel = str(
                    (skill_md.parent / path.relative_to(dest_dir)).relative_to(
                        candidate))
            except ValueError:
                cand_rel = support_rel
            support = dict(by_path.get(support_rel) or {
                "path": support_rel,
                "source": f"github.com/mattpocock/skills @ {sha} {cand_rel}",
                "license": "MIT,见 licenses/mattpocock-skills-LICENSE.txt",
            })
            support["path"] = support_rel
            support["sha256"] = _sha256(path)
            support["source"] = (
                f"github.com/mattpocock/skills @ {sha} {cand_rel}")
            by_path[support_rel] = support
        for stale in list(by_path):
            if stale.startswith(prefix) and stale not in live_rels:
                del by_path[stale]
    material_decisions = evaluation.get("new_material_decisions") or {}
    for rel, decision in material_decisions.items():
        if decision != "include":
            continue
        src = candidate / rel
        if not src.is_file():
            continue
        dest = plugin / rel
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dest)
        entry = dict(by_path.get(rel) or {
            "path": rel,
            "source": f"github.com/mattpocock/skills @ {sha} {rel}",
            "license": "MIT,见 licenses/mattpocock-skills-LICENSE.txt",
        })
        entry["path"] = rel
        entry["sha256"] = _sha256(dest)
        entry["source"] = f"github.com/mattpocock/skills @ {sha} {rel}"
        entry["license"] = entry.get("license") or "MIT,见 licenses/mattpocock-skills-LICENSE.txt"
        by_path[rel] = entry
    fingerprints["files"] = list(by_path.values())
    upstream = dict(fingerprints.get("upstream") or {})
    upstream.update({
        "name": upstream.get("name") or "mattpocock/skills",
        "version": version,
        "sha": sha,
        "license": "MIT",
        "url": f"https://github.com/mattpocock/skills/tree/{sha}",
    })
    fingerprints["upstream"] = upstream
    (plugin / "provenance" / "fingerprints.json").write_text(
        json.dumps(fingerprints, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8")
    _update_manifest_pin(plugin, version, sha)
    return read_upstream_adoption(plugin)


def apply_upstream_upgrade(
    plugin_root: Path | str,
    evaluation: dict,
    *,
    confirmed: bool = False,
) -> dict:
    """Adopt only a passing, confirmed candidate. Otherwise keep the pin."""

    plugin = _root(plugin_root)
    result = dict(evaluation)
    current = read_upstream_adoption(plugin)
    result["current"] = current
    if not confirmed:
        result["decision"] = "retain"
        result["retain_reason"] = evaluation.get("retain_reason") or "not-confirmed"
        result["adopted"] = current
        return result
    if evaluation.get("decision") != "adopt":
        result["decision"] = "retain"
        result["retain_reason"] = evaluation.get("retain_reason") or "verification-failed"
        result["adopted"] = current
        return result
    adopted = _adopt_candidate(plugin, evaluation)
    result["decision"] = "adopt"
    result["retain_reason"] = None
    result["adopted"] = adopted
    return result

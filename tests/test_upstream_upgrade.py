#!/usr/bin/env python3
"""Issue #60 seams: upstream upgrade evaluation and adaptation review.

Confirmed seams (issue #60 acceptance + #49 T1 and T13):
- Compare the official skill set, invocation declarations, dependency
  references, licenses, and each adaptation; record still-needed,
  resolved-by-upstream, or conflict.
- A candidate first yields a reviewable diff and verification result;
  adopt only after it passes. Do not overwrite with latest. Added,
  retired, or experimental-to-official skills need an explicit decision.
- Verify material loading and adaptations on existing game entries and a
  direct Matt path; later new materials enter the delivered package only
  under the same review rule.
- Broken references, declaration changes, source conflicts, or failed
  checks keep the current adopted version and the reason; do not expand
  client, engine, or tool scope.
- Fixed-candidate pass and fail cases check adopt status, source, and
  package contents; reuse existing package and invocation boundaries;
  do not create a continuous update service.

Public seams: evaluate_upstream_upgrade / apply_upstream_upgrade /
read_upstream_adoption.

Expected values come from issues #60 and #49 D2/D3/D10, not internals.
Do not assert internal functions, directory counts, or prompt keywords.

    python3 -B tests/test_upstream_upgrade.py
"""

from __future__ import annotations

import hashlib
import json
import sys
import tempfile
from pathlib import Path

from plugin_package_support import make_checker, run_theme
from redesign_bundle_contract import (
    GAME_ENTRIES,
    INVOCATION_CONTRACT_REL,
    MATT_OFFICIAL,
    MATT_UPSTREAM_PATH,
    MATT_USER_ONLY,
    PUBLIC_SKILLS,
    STAGE_REQUIREMENTS_REL,
    UPSTREAM_SHA,
    UPSTREAM_VERSION,
)

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "plugin" / "provenance"))

import mgs_upstream_upgrade  # noqa: E402

FAILURES, check = make_checker()

CURRENT_PLUGIN = REPO_ROOT / "plugin"
PINNED_SHA = "bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb"
PINNED_VERSION = "1.2.4"
STAGE_POINTER = "../../internal/game/stage-requirements.md"
MIT_LICENSE = (CURRENT_PLUGIN / "provenance" / "licenses" / "mattpocock-skills-LICENSE.txt").read_text(
    encoding="utf-8"
)


def _sha_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _sha_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _write(root: Path, rel: str, text: str) -> Path:
    path = root / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return path


def _matt_original(name: str, *, extra: str = "") -> str:
    flags = "disable-model-invocation: true\n" if name in MATT_USER_ONLY else ""
    return (
        f"---\nname: {name}\ndescription: {name} upstream method.\n{flags}---\n\n"
        f"{name} upstream method.\n{extra}"
    )


def _matt_adapted(name: str, *, extra: str = "") -> str:
    original = _matt_original(name, extra=extra)
    extra_adapt = ""
    if name == "implement":
        extra_adapt = (
            "If commit authorization is present, commit your work to the "
            "current branch. If it is not, leave the work uncommitted.\n\n"
        )
    return (
        original.rstrip()
        + "\n\n## MyGameStudio stage materials\n\n"
        + extra_adapt
        + "When working in a MyGameStudio game project, read "
        + f"[stage requirements]({STAGE_POINTER}) for the current work stage "
        + "before applying this skill's method. Reading those materials does "
        + "not start production.\n"
    )


def _game_skill(name: str) -> str:
    return (
        f"---\nname: {name}\ndescription: {name} game entry.\n"
        "disable-model-invocation: true\n---\n\n"
        f"{name} reads [stage requirements]({STAGE_POINTER}).\n"
        "Reading those materials does not start production.\n"
    )


def _fingerprint_entry(rel: str, path: Path, *, original: str | None = None,
                       source: str, license_text: str, adaptation: str | None = None) -> dict:
    entry = {
        "path": rel,
        "sha256": _sha_file(path),
        "source": source,
        "license": license_text,
    }
    if original is not None:
        entry["original_sha256"] = _sha_text(original)
    if adaptation:
        entry["adaptation"] = adaptation
    return entry


def _write_current_plugin(root: Path) -> Path:
    _write(root, ".codex-plugin/plugin.json", json.dumps({
        "name": "mygamestudio",
        "version": "2.0.0",
        "description": "fixture",
        "author": {"name": "MyGameStudio"},
        "skills": "./skills/",
    }, indent=2) + "\n")
    invocation = (CURRENT_PLUGIN / INVOCATION_CONTRACT_REL).read_text(encoding="utf-8")
    stage = (CURRENT_PLUGIN / STAGE_REQUIREMENTS_REL).read_text(encoding="utf-8")
    _write(root, INVOCATION_CONTRACT_REL, invocation)
    _write(root, STAGE_REQUIREMENTS_REL, stage)
    _write(root, "provenance/licenses/mattpocock-skills-LICENSE.txt", MIT_LICENSE)
    _write(root, "provenance/manifest.md", (
        f"# mygamestudio 2.0.0 来源与许可追溯\n\n"
        f"- 上游:Matt Pocock skills **{UPSTREAM_VERSION}**,"
        f"完整提交 `{UPSTREAM_SHA}`。\n"
    ))
    files = []
    for name in MATT_OFFICIAL:
        original = _matt_original(name)
        adapted = _matt_adapted(name)
        path = _write(root, f"skills/{name}/SKILL.md", adapted)
        files.append(_fingerprint_entry(
            f"skills/{name}/SKILL.md", path, original=original,
            source=f"github.com/mattpocock/skills @ {UPSTREAM_SHA} {MATT_UPSTREAM_PATH[name]}/SKILL.md",
            license_text="MIT,见 licenses/mattpocock-skills-LICENSE.txt",
            adaptation="Append MyGameStudio stage-materials pointer. Upstream method body unchanged.",
        ))
    for name in GAME_ENTRIES:
        path = _write(root, f"skills/{name}/SKILL.md", _game_skill(name))
        files.append(_fingerprint_entry(
            f"skills/{name}/SKILL.md", path,
            source="本项目自有内容(MIT); issue #50 改版组合包",
            license_text="本项目自有内容(MIT)",
        ))
    for rel in (INVOCATION_CONTRACT_REL, STAGE_REQUIREMENTS_REL):
        files.append(_fingerprint_entry(
            rel, root / rel,
            source="本项目自有内容(MIT); issue #50 改版组合包",
            license_text="本项目自有内容(MIT)",
        ))
    _write(root, "provenance/fingerprints.json", json.dumps({
        "version": 2,
        "generated_for": "mygamestudio 2.0.0",
        "upstream": {
            "name": "mattpocock/skills",
            "version": UPSTREAM_VERSION,
            "sha": UPSTREAM_SHA,
            "license": "MIT",
            "url": f"https://github.com/mattpocock/skills/tree/{UPSTREAM_SHA}",
        },
        "files": files,
    }, indent=2) + "\n")
    return root


def _write_candidate(root: Path, *, skills: dict[str, str] | None = None,
                     extra_files: dict[str, str] | None = None,
                     include_license: bool = True) -> Path:
    if include_license:
        _write(root, "LICENSE", MIT_LICENSE)
    bodies = skills if skills is not None else {
        name: _matt_original(name) for name in MATT_OFFICIAL
    }
    for name, text in bodies.items():
        rel = MATT_UPSTREAM_PATH.get(name, f"skills/experimental/{name}")
        _write(root, f"{rel}/SKILL.md", text)
    for rel, text in (extra_files or {}).items():
        _write(root, rel, text)
    return root


def _stage_loadable(plugin: Path, skill: str) -> bool:
    skill_md = plugin / "skills" / skill / "SKILL.md"
    stage = plugin / STAGE_REQUIREMENTS_REL
    if not skill_md.is_file() or not stage.is_file():
        return False
    text = skill_md.read_text(encoding="utf-8")
    if STAGE_POINTER not in text and STAGE_REQUIREMENTS_REL not in text:
        return False
    return (skill_md.parent / STAGE_POINTER).resolve() == stage.resolve()


def _adopted_pin(plugin: Path) -> tuple[str, str]:
    data = json.loads((plugin / "provenance" / "fingerprints.json").read_text(encoding="utf-8"))
    upstream = data.get("upstream") or {}
    return str(upstream.get("version") or ""), str(upstream.get("sha") or "")


def test_unpinned_latest_is_not_adopted() -> None:
    """T13/AC: a latest candidate is not adopted; the current pin stays usable."""

    with tempfile.TemporaryDirectory(prefix="mgs-upgrade-") as tmp:
        plugin = _write_current_plugin(Path(tmp) / "plugin")
        candidate = _write_candidate(Path(tmp) / "candidate")
        evaluation = mgs_upstream_upgrade.evaluate_upstream_upgrade(
            plugin, candidate,
            candidate_version="latest",
            candidate_sha="latest",
        )
        check(evaluation.get("decision") == "retain",
              f"latest 候选不得采用,实际 decision={evaluation.get('decision')}")
        check(evaluation.get("retain_reason") == "unpinned-candidate",
              f"未钉住候选应记录 unpinned-candidate,实际 {evaluation.get('retain_reason')}")
        applied = mgs_upstream_upgrade.apply_upstream_upgrade(
            plugin, evaluation, confirmed=True)
        check(applied.get("decision") == "retain",
              f"确认后仍不得采用 latest,实际 {applied.get('decision')}")
        adoption = mgs_upstream_upgrade.read_upstream_adoption(plugin)
        check(adoption.get("version") == UPSTREAM_VERSION,
              f"当前版本应保持 {UPSTREAM_VERSION},实际 {adoption.get('version')}")
        check(adoption.get("sha") == UPSTREAM_SHA,
              f"当前 SHA 应保持 {UPSTREAM_SHA},实际 {adoption.get('sha')}")
        check(_adopted_pin(plugin) == (UPSTREAM_VERSION, UPSTREAM_SHA),
              "失败升级不得改写 fingerprints 中的已采用上游")
        for name in GAME_ENTRIES + ("implement",):
            check(_stage_loadable(plugin, name),
                  f"保留当前版本后 {name} 仍须能加载阶段资料")


def test_evaluation_records_collection_invocation_refs_license_and_adaptations() -> None:
    """AC/T1: compare official set, invocation, refs, license, and each adaptation."""

    with tempfile.TemporaryDirectory(prefix="mgs-upgrade-") as tmp:
        plugin = _write_current_plugin(Path(tmp) / "plugin")
        bodies = {name: _matt_original(name) for name in MATT_OFFICIAL}
        bodies["implement"] = _matt_adapted("implement")
        bodies["code-review"] = (
            _matt_original("code-review")
            + "See [missing](./gone.md).\n"
        )
        candidate = _write_candidate(Path(tmp) / "candidate", skills=bodies)
        evaluation = mgs_upstream_upgrade.evaluate_upstream_upgrade(
            plugin, candidate,
            candidate_version=PINNED_VERSION,
            candidate_sha=PINNED_SHA,
        )
        collection = evaluation.get("collection") or {}
        check(sorted(collection.get("current_official") or []) == sorted(MATT_OFFICIAL),
              "当前正式集合必须是规格中的 25 项")
        check(sorted(collection.get("candidate_official") or []) == sorted(MATT_OFFICIAL),
              "候选正式集合必须按 engineering/productivity 核对")
        check(collection.get("added") == [], f"本候选不应有新增,实际 {collection.get('added')}")
        check(collection.get("retired") == [], f"本候选不应有退役,实际 {collection.get('retired')}")
        check(collection.get("experimental_promoted") == [],
              f"本候选不应有实验转正,实际 {collection.get('experimental_promoted')}")
        invocation = evaluation.get("invocation") or {}
        check(invocation.get("changes") == [],
              f"本候选调用声明应无变化,实际 {invocation.get('changes')}")
        license_info = evaluation.get("license") or {}
        check(license_info.get("current") == "MIT" and license_info.get("candidate") == "MIT",
              f"许可应为 MIT,实际 {license_info}")
        check(license_info.get("conflict") is False, "MIT 对 MIT 不得记为许可冲突")
        by_skill = {
            item.get("skill"): item
            for item in (evaluation.get("adaptations") or [])
            if isinstance(item, dict)
        }
        check(by_skill.get("ask-matt", {}).get("status") == "still-needed",
              "候选仍是上游原文时,阶段资料适配必须记为 still-needed")
        check(by_skill.get("implement", {}).get("status") == "resolved-by-upstream",
              "候选已含当前适配结果时必须记为 resolved-by-upstream")
        check(by_skill.get("code-review", {}).get("status") == "conflict",
              "候选改动与现有适配无法并存时必须记为 conflict")
        refs = evaluation.get("references") or {}
        check("skills/engineering/code-review/SKILL.md" in str(refs.get("broken") or []),
              f"断裂引用必须记录,实际 {refs.get('broken')}")
        record = plugin / "provenance" / "upgrade-evaluations" / f"{PINNED_SHA}.json"
        check(record.is_file(), "评估必须留下可复查差异文件")
        if record.is_file():
            saved = json.loads(record.read_text(encoding="utf-8"))
            check(saved.get("candidate", {}).get("sha") == PINNED_SHA,
                  "可复查文件必须钉住候选 SHA,而不是 latest")


def test_pinned_compatible_candidate_is_adopted_and_package_matches() -> None:
    """T1/AC: passing pinned candidate is adopted; collection, source, and package match."""

    with tempfile.TemporaryDirectory(prefix="mgs-upgrade-") as tmp:
        plugin = _write_current_plugin(Path(tmp) / "plugin")
        candidate = _write_candidate(Path(tmp) / "candidate")
        evaluation = mgs_upstream_upgrade.evaluate_upstream_upgrade(
            plugin, candidate,
            candidate_version=PINNED_VERSION,
            candidate_sha=PINNED_SHA,
        )
        check(evaluation.get("decision") == "adopt",
              f"兼容钉住候选验证通过后应采用,实际 {evaluation.get('decision')}"
              f" reason={evaluation.get('retain_reason')}")
        check((evaluation.get("verification") or {}).get("passed") is True,
              f"验证结果必须可复查且通过,实际 {evaluation.get('verification')}")
        check(sorted((evaluation.get("collection") or {}).get("current_official") or [])
              == sorted(MATT_OFFICIAL),
              "采用记录中的正式集合必须仍是规格 25 项")
        skipped = mgs_upstream_upgrade.apply_upstream_upgrade(
            plugin, evaluation, confirmed=False)
        check(skipped.get("decision") == "retain",
              "未确认不得采用")
        check(_adopted_pin(plugin) == (UPSTREAM_VERSION, UPSTREAM_SHA),
              "未确认不得改写当前固定版本")
        applied = mgs_upstream_upgrade.apply_upstream_upgrade(
            plugin, evaluation, confirmed=True)
        check(applied.get("decision") == "adopt",
              f"确认后应采用,实际 {applied.get('decision')}")
        adoption = mgs_upstream_upgrade.read_upstream_adoption(plugin)
        check(adoption.get("version") == PINNED_VERSION,
              f"采用版本应为 {PINNED_VERSION},实际 {adoption.get('version')}")
        check(adoption.get("sha") == PINNED_SHA,
              f"采用 SHA 应为钉住候选,实际 {adoption.get('sha')}")
        check(adoption.get("license") == "MIT", "采用后许可必须仍是 MIT")
        public = sorted(
            path.name for path in (plugin / "skills").iterdir() if path.is_dir()
        )
        check(public == sorted(PUBLIC_SKILLS),
              f"采用后公开集合必须是 25 项加三个游戏入口,实际 {public}")
        for name in GAME_ENTRIES + ("implement", "to-spec", "to-tickets"):
            check(_stage_loadable(plugin, name),
                  f"采用后 {name} 必须仍能加载阶段资料并完成适配")
        data = json.loads((plugin / "provenance" / "fingerprints.json").read_text(
            encoding="utf-8"))
        check(data.get("upstream", {}).get("sha") == PINNED_SHA,
              "来源记录必须写采用后的钉住 SHA")
        by_path = {
            entry.get("path"): entry for entry in data.get("files") or []
        }
        for name in MATT_OFFICIAL:
            rel = f"skills/{name}/SKILL.md"
            path = plugin / rel
            check(path.is_file(), f"采用后缺少 {rel}")
            entry = by_path.get(rel) or {}
            check(entry.get("sha256") == _sha_file(path),
                  f"{rel} 指纹必须与包内文件一致")
            check(PINNED_SHA in str(entry.get("source")),
                  f"{rel} 来源必须指向采用的候选 SHA")
            check(bool(entry.get("license")), f"{rel} 必须保留许可")
            check(entry.get("original_sha256") != entry.get("sha256"),
                  f"{rel} 仍需适配时原始与分发校验值必须不同")
            check(bool(entry.get("adaptation")),
                  f"{rel} 仍需适配时必须记录适配理由")
            text = path.read_text(encoding="utf-8")
            check(_stage_loadable(plugin, name),
                  f"采用后 {name} 必须仍能加载阶段资料")
        implement = (plugin / "skills" / "implement" / "SKILL.md").read_text(encoding="utf-8")
        check("leave the work uncommitted" in implement.lower(),
              "仍需适配且上游原文未变时必须保留当前 implement 授权提交适配")
        check(adoption.get("sha") != "latest", "不得把当前固定版本覆盖成 latest")


def test_broken_reference_keeps_current_version() -> None:
    """T13: broken candidate references are not adopted; the current pin stays usable."""

    with tempfile.TemporaryDirectory(prefix="mgs-upgrade-") as tmp:
        plugin = _write_current_plugin(Path(tmp) / "plugin")
        bodies = {name: _matt_original(name) for name in MATT_OFFICIAL}
        bodies["code-review"] = _matt_original("code-review") + "See [missing](./gone.md).\n"
        candidate = _write_candidate(Path(tmp) / "candidate", skills=bodies)
        evaluation = mgs_upstream_upgrade.evaluate_upstream_upgrade(
            plugin, candidate,
            candidate_version=PINNED_VERSION,
            candidate_sha=PINNED_SHA,
        )
        check(evaluation.get("decision") == "retain",
              f"断裂引用不得采用,实际 {evaluation.get('decision')}")
        check(evaluation.get("retain_reason") == "broken-reference",
              f"应记录 broken-reference,实际 {evaluation.get('retain_reason')}")
        mgs_upstream_upgrade.apply_upstream_upgrade(plugin, evaluation, confirmed=True)
        check(_adopted_pin(plugin) == (UPSTREAM_VERSION, UPSTREAM_SHA),
              "断裂引用时必须保留当前有效版本")
        check(_stage_loadable(plugin, "game-producer") and _stage_loadable(plugin, "implement"),
              "保留后游戏入口和 Matt 路径仍须能加载资料")


def test_invocation_change_keeps_current_version() -> None:
    """T13: invocation declaration changes are not adopted."""

    with tempfile.TemporaryDirectory(prefix="mgs-upgrade-") as tmp:
        plugin = _write_current_plugin(Path(tmp) / "plugin")
        bodies = {name: _matt_original(name) for name in MATT_OFFICIAL}
        bodies["implement"] = (
            "---\nname: implement\ndescription: implement upstream method.\n---\n\n"
            "implement upstream method.\n"
        )
        candidate = _write_candidate(Path(tmp) / "candidate", skills=bodies)
        evaluation = mgs_upstream_upgrade.evaluate_upstream_upgrade(
            plugin, candidate,
            candidate_version=PINNED_VERSION,
            candidate_sha=PINNED_SHA,
        )
        check(evaluation.get("decision") == "retain",
              "调用声明变化不得采用")
        check(evaluation.get("retain_reason") == "invocation-change",
              f"应记录 invocation-change,实际 {evaluation.get('retain_reason')}")
        mgs_upstream_upgrade.apply_upstream_upgrade(plugin, evaluation, confirmed=True)
        check(_adopted_pin(plugin) == (UPSTREAM_VERSION, UPSTREAM_SHA),
              "调用变化时必须保留当前有效版本")
        implement = (plugin / "skills" / "implement" / "SKILL.md").read_text(encoding="utf-8")
        check("disable-model-invocation: true" in implement,
              "当前 implement 仍须保持用户专用调用声明")


def test_source_conflict_keeps_current_version() -> None:
    """T13: two candidate sources for the same name are not adopted."""

    with tempfile.TemporaryDirectory(prefix="mgs-upgrade-") as tmp:
        plugin = _write_current_plugin(Path(tmp) / "plugin")
        candidate = _write_candidate(Path(tmp) / "candidate")
        _write(candidate, "skills/productivity/tdd/SKILL.md", _matt_original("tdd"))
        evaluation = mgs_upstream_upgrade.evaluate_upstream_upgrade(
            plugin, candidate,
            candidate_version=PINNED_VERSION,
            candidate_sha=PINNED_SHA,
        )
        check(evaluation.get("decision") == "retain",
              "同名双源不得采用")
        check(evaluation.get("retain_reason") == "source-conflict",
              f"应记录 source-conflict,实际 {evaluation.get('retain_reason')}")
        mgs_upstream_upgrade.apply_upstream_upgrade(plugin, evaluation, confirmed=True)
        check(_adopted_pin(plugin) == (UPSTREAM_VERSION, UPSTREAM_SHA),
              "来源冲突时必须保留当前有效版本")
        names = [path.name for path in (plugin / "skills").iterdir() if path.is_dir()]
        check(names.count("tdd") == 1, "当前包仍只能有一个 tdd 来源")


def test_unevaluated_collection_change_is_not_adopted() -> None:
    """AC: added, retired, or experimental-to-official skills need an explicit decision."""

    with tempfile.TemporaryDirectory(prefix="mgs-upgrade-") as tmp:
        plugin = _write_current_plugin(Path(tmp) / "plugin")
        candidate = _write_candidate(
            Path(tmp) / "candidate",
            extra_files={"skills/experimental/new-flow/SKILL.md": _matt_original("new-flow")},
        )
        evaluation = mgs_upstream_upgrade.evaluate_upstream_upgrade(
            plugin, candidate,
            candidate_version=PINNED_VERSION,
            candidate_sha=PINNED_SHA,
        )
        check(evaluation.get("decision") == "retain",
              "未评估的实验技能不得自动纳入")
        check(evaluation.get("retain_reason") == "unevaluated-collection-change",
              f"应记录 unevaluated-collection-change,实际 {evaluation.get('retain_reason')}")
        check("new-flow" in ((evaluation.get("collection") or {}).get("experimental") or []),
              "实验技能必须出现在评估记录中")
        deferred = mgs_upstream_upgrade.evaluate_upstream_upgrade(
            plugin, candidate,
            candidate_version=PINNED_VERSION,
            candidate_sha=PINNED_SHA,
            collection_decisions={"new-flow": "defer"},
        )
        check(deferred.get("decision") == "adopt",
              f"明确评估为 defer 后其余兼容变更可以通过,实际 {deferred.get('decision')}"
              f" reason={deferred.get('retain_reason')}")
        mgs_upstream_upgrade.apply_upstream_upgrade(plugin, evaluation, confirmed=True)
        check(_adopted_pin(plugin) == (UPSTREAM_VERSION, UPSTREAM_SHA),
              "未评估实验转正不得改写当前版本")
        check(not (plugin / "skills" / "new-flow").exists(),
              "实验技能不得进入当前有效包")


def test_new_materials_follow_the_same_review_before_delivery() -> None:
    """AC: later new materials enter the delivered package only after the same review."""

    with tempfile.TemporaryDirectory(prefix="mgs-upgrade-") as tmp:
        plugin = _write_current_plugin(Path(tmp) / "plugin")
        extra = {"internal/game/extra-module.md": "# Extra module\n\nUsed when needed.\n"}
        candidate = _write_candidate(Path(tmp) / "candidate", extra_files=extra)
        blocked = mgs_upstream_upgrade.evaluate_upstream_upgrade(
            plugin, candidate,
            candidate_version=PINNED_VERSION,
            candidate_sha=PINNED_SHA,
        )
        check(blocked.get("decision") == "retain",
              "未复核的新资料不得进入最终交付")
        check(blocked.get("retain_reason") == "unevaluated-new-material",
              f"应记录 unevaluated-new-material,实际 {blocked.get('retain_reason')}")
        mgs_upstream_upgrade.apply_upstream_upgrade(plugin, blocked, confirmed=True)
        check(not (plugin / "internal" / "game" / "extra-module.md").exists(),
              "未复核资料不得写入当前包")
        reviewed = mgs_upstream_upgrade.evaluate_upstream_upgrade(
            plugin, candidate,
            candidate_version=PINNED_VERSION,
            candidate_sha=PINNED_SHA,
            new_material_decisions={"internal/game/extra-module.md": "include"},
        )
        check(reviewed.get("decision") == "adopt",
              f"按同一规则复核通过后才采用,实际 {reviewed.get('decision')}"
              f" reason={reviewed.get('retain_reason')}")
        mgs_upstream_upgrade.apply_upstream_upgrade(plugin, reviewed, confirmed=True)
        extra_path = plugin / "internal" / "game" / "extra-module.md"
        check(extra_path.is_file(), "复核通过的新资料必须进入交付包")
        check(_adopted_pin(plugin) == (PINNED_VERSION, PINNED_SHA),
              "复核通过后才切换来源")
        check(_stage_loadable(plugin, "game-design") and _stage_loadable(plugin, "to-spec"),
              "纳入新资料后游戏入口和 Matt 路径仍须能加载")


def test_upgrade_stays_codex_only_and_is_not_a_service() -> None:
    """AC: do not expand clients/engines/tools, and do not start a continuous updater."""

    with tempfile.TemporaryDirectory(prefix="mgs-upgrade-") as tmp:
        plugin = _write_current_plugin(Path(tmp) / "plugin")
        candidate = _write_candidate(Path(tmp) / "candidate")
        evaluation = mgs_upstream_upgrade.evaluate_upstream_upgrade(
            plugin, candidate,
            candidate_version=PINNED_VERSION,
            candidate_sha=PINNED_SHA,
        )
        scope = evaluation.get("scope") or {}
        check(scope.get("clients") == ["codex"],
              f"首批仍只验证 Codex,实际 {scope.get('clients')}")
        check(scope.get("continuous_update") is False,
              "不得建立持续更新服务")
        check(scope.get("engines") in (None, [], False),
              "不得扩大引擎范围")
        mgs_upstream_upgrade.apply_upstream_upgrade(plugin, evaluation, confirmed=True)
        check(_adopted_pin(plugin)[1] == PINNED_SHA,
              "一次性采用后没有继续追随 latest")
        check(mgs_upstream_upgrade.read_upstream_adoption(plugin).get("sha") != "latest",
              "采用结果仍是钉住 SHA")


def test_live_package_keeps_the_fixed_upstream_pin() -> None:
    """T1: the delivered plugin still records Matt 1.2.3 / 3cca18b, not latest."""

    adoption = mgs_upstream_upgrade.read_upstream_adoption(CURRENT_PLUGIN)
    check(adoption.get("version") == UPSTREAM_VERSION,
          f"当前交付包上游版本必须是 {UPSTREAM_VERSION},实际 {adoption.get('version')}")
    check(adoption.get("sha") == UPSTREAM_SHA,
          f"当前交付包上游 SHA 必须是 {UPSTREAM_SHA},实际 {adoption.get('sha')}")
    check(adoption.get("license") == "MIT", "当前交付包必须保留 MIT")
    check(adoption.get("sha") != "latest", "当前交付包不得追随 latest")


def test_missing_license_keeps_current_version() -> None:
    """T13: a candidate without a usable license is not adopted."""

    with tempfile.TemporaryDirectory(prefix="mgs-upgrade-") as tmp:
        plugin = _write_current_plugin(Path(tmp) / "plugin")
        candidate = _write_candidate(Path(tmp) / "candidate", include_license=False)
        evaluation = mgs_upstream_upgrade.evaluate_upstream_upgrade(
            plugin, candidate,
            candidate_version=PINNED_VERSION,
            candidate_sha=PINNED_SHA,
        )
        check(evaluation.get("decision") == "retain", "许可缺失不得采用")
        check(evaluation.get("retain_reason") == "license-conflict",
              f"应记录 license-conflict,实际 {evaluation.get('retain_reason')}")
        mgs_upstream_upgrade.apply_upstream_upgrade(plugin, evaluation, confirmed=True)
        check(_adopted_pin(plugin) == (UPSTREAM_VERSION, UPSTREAM_SHA),
              "许可检查失败时必须保留当前有效版本")


def test_changed_candidate_keeps_commit_authorization_adaptation() -> None:
    """D8/D10: 候选变化时仍须保留并验证阶段资料节之前的提交授权适配。"""

    with tempfile.TemporaryDirectory(prefix="mgs-upgrade-") as tmp:
        plugin = _write_current_plugin(Path(tmp) / "plugin")
        original = _matt_original("implement")
        adapted = (
            original.rstrip()
            + "\n\nIf commit authorization is present, commit your work to the "
            "current branch. If it is not, leave the work uncommitted.\n\n"
            "## MyGameStudio stage materials\n\n"
            "When working in a MyGameStudio game project, read "
            f"[stage requirements]({STAGE_POINTER}) for the current work stage "
            "before applying this skill's method. Reading those materials does "
            "not start production.\n\n"
            "For a playable slice after the developer invoked to-tickets, use "
            "the packaged seam `records/mgs_records.py`: "
            "`plan_playable_delivery` / `apply_playable_delivery` / "
            "`record_playable_result`.\n"
        )
        impl_path = plugin / "skills" / "implement" / "SKILL.md"
        impl_path.write_text(adapted, encoding="utf-8")
        data = json.loads((plugin / "provenance" / "fingerprints.json").read_text(
            encoding="utf-8"))
        for entry in data.get("files") or []:
            if entry.get("path") == "skills/implement/SKILL.md":
                entry["sha256"] = _sha_file(impl_path)
                entry["original_sha256"] = _sha_text(original)
        (plugin / "provenance" / "fingerprints.json").write_text(
            json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        bodies = {name: _matt_original(name) for name in MATT_OFFICIAL}
        bodies["implement"] = _matt_original("implement") + (
            "Commit your work to the current branch.\n\n"
            "## MyGameStudio stage materials\n\n"
            "When working in a MyGameStudio game project, read "
            f"[stage requirements]({STAGE_POINTER}) for the current work stage "
            "before applying this skill's method. Reading those materials does "
            "not start production.\n"
        )
        candidate = _write_candidate(Path(tmp) / "candidate", skills=bodies)
        evaluation = mgs_upstream_upgrade.evaluate_upstream_upgrade(
            plugin, candidate,
            candidate_version=PINNED_VERSION,
            candidate_sha=PINNED_SHA,
        )
        check(evaluation.get("decision") == "adopt",
              f"仍需适配的兼容候选应能通过评估,实际 {evaluation.get('decision')}"
              f" reason={evaluation.get('retain_reason')}")
        mgs_upstream_upgrade.apply_upstream_upgrade(
            plugin, evaluation, confirmed=True)
        text = (plugin / "skills" / "implement" / "SKILL.md").read_text(encoding="utf-8")
        check("leave the work uncommitted" in text.lower(),
              "候选变化后必须保留 implement 提交授权条件")
        check(_stage_loadable(plugin, "implement"),
              "提交授权适配之外仍须保留阶段资料指针")
        check("If commit authorization is present" in text,
              "不得把有条件提交恢复成无条件提交指令")
        check("plan_playable_delivery" in text,
              "候选变化后必须保留阶段资料节中的既有接缝适配")


def test_rejected_official_skill_is_not_installed() -> None:
    """D10: 集合新增经明确拒绝后不得进入有效目录。"""

    with tempfile.TemporaryDirectory(prefix="mgs-upgrade-") as tmp:
        plugin = _write_current_plugin(Path(tmp) / "plugin")
        extra = {
            "skills/engineering/rejected-skill/SKILL.md": _matt_original("rejected-skill"),
        }
        candidate = _write_candidate(Path(tmp) / "candidate", extra_files=extra)
        evaluation = mgs_upstream_upgrade.evaluate_upstream_upgrade(
            plugin, candidate,
            candidate_version=PINNED_VERSION,
            candidate_sha=PINNED_SHA,
            collection_decisions={"rejected-skill": "reject"},
        )
        check(evaluation.get("decision") == "adopt",
              f"明确拒绝新增后其余兼容变更应能采用,实际 {evaluation.get('decision')}"
              f" reason={evaluation.get('retain_reason')}")
        mgs_upstream_upgrade.apply_upstream_upgrade(
            plugin, evaluation, confirmed=True)
        check(not (plugin / "skills" / "rejected-skill").exists(),
              "被拒绝的候选技能不得进入有效技能目录")
        check(_adopted_pin(plugin) == (PINNED_VERSION, PINNED_SHA),
              "明确拒绝后其余通过项仍应切换到来源")


TESTS = (
    test_unpinned_latest_is_not_adopted,
    test_evaluation_records_collection_invocation_refs_license_and_adaptations,
    test_pinned_compatible_candidate_is_adopted_and_package_matches,
    test_broken_reference_keeps_current_version,
    test_invocation_change_keeps_current_version,
    test_source_conflict_keeps_current_version,
    test_unevaluated_collection_change_is_not_adopted,
    test_new_materials_follow_the_same_review_before_delivery,
    test_upgrade_stays_codex_only_and_is_not_a_service,
    test_live_package_keeps_the_fixed_upstream_pin,
    test_missing_license_keeps_current_version,
    test_changed_candidate_keeps_commit_authorization_adaptation,
    test_rejected_official_skill_is_not_installed,
)


def main() -> int:
    return run_theme("上游升级评估与适配复核(T1/T13)", TESTS, FAILURES)


if __name__ == "__main__":
    sys.exit(main())

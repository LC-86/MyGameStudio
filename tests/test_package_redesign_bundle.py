#!/usr/bin/env python3
"""Issue #50 seams T1 (package and provenance) and T2 (discovery and invocation).

Expected values are the #49 D1/D2/D3/D8 literals in redesign_bundle_contract.py.
These tests observe the installable plugin surface: public skill names, invocation
flags, packaged references, provenance records, and the files a session would
load. They do not count internal directories or scrape prompt keywords.

    python3 -B tests/test_package_redesign_bundle.py
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

from plugin_package_support import PLUGIN_ROOT, REPO_ROOT, make_checker, run_theme, sha256
from redesign_bundle_contract import (
    GAME_ENTRIES,
    INVOCATION_CONTRACT_REL,
    MATT_OFFICIAL,
    MATT_UPSTREAM_PATH,
    MATT_USER_ONLY,
    PUBLIC_SKILLS,
    RETIRED_GAME_ENTRIES,
    STAGE_REQUIREMENTS_REL,
    UPSTREAM_SHA,
    UPSTREAM_VERSION,
)

FAILURES, check = make_checker()

EXTERNAL_PREFIXES = ("http://", "https://", "mailto:")
EXAMPLE_LINK = re.compile(r"^(link|./src/)")


def _skills_root() -> Path:
    return PLUGIN_ROOT / "skills"


def _public_skill_names() -> list[str]:
    root = _skills_root()
    if not root.is_dir():
        return []
    return sorted(p.name for p in root.iterdir() if p.is_dir())


def _frontmatter(text: str) -> str:
    match = re.match(r"^---\n(.*?)\n---\n", text, re.DOTALL)
    return match.group(1) if match else ""


def _load_fingerprints() -> dict:
    path = PLUGIN_ROOT / "provenance" / "fingerprints.json"
    if not path.is_file():
        check(False, "缺少 provenance/fingerprints.json")
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def _fingerprint_by_path(data: dict) -> dict:
    files = data.get("files") or []
    return {entry.get("path"): entry for entry in files if isinstance(entry, dict)}


def _markdown_targets(md: Path) -> list[str]:
    text = md.read_text(encoding="utf-8")
    return re.findall(r"\]\(([^)\s]+)\)", text)


def _parse_bullet_section(text: str, heading: str) -> list[str]:
    """Read a `## heading` section's `- name` bullets until the next heading."""

    lines = text.splitlines()
    collecting = False
    names: list[str] = []
    for line in lines:
        if line.startswith("## "):
            collecting = line[3:].strip() == heading
            continue
        if collecting:
            match = re.match(r"^-\s+([A-Za-z0-9_-]+)\s*$", line)
            if match:
                names.append(match.group(1))
    return names


# --- T1: package and provenance ------------------------------------------------


def test_public_collection_matches_spec() -> None:
    """T1: effective public skills are the official 25 Matt items plus three game entries."""

    actual = _public_skill_names()
    check(
        actual == sorted(PUBLIC_SKILLS),
        "公开技能集合必须是 Matt 正式 25 项加 Game-Producer/Game-Init/Game-Design,"
        f"实际为 {actual}",
    )


def test_retired_entries_are_not_effective() -> None:
    """T1: retired game entries are not effective public skills."""

    actual = set(_public_skill_names())
    leaked = sorted(set(RETIRED_GAME_ENTRIES) & actual)
    check(not leaked, f"已退役游戏入口仍作为有效公开技能: {leaked}")


def test_public_names_are_unique() -> None:
    """T1/T2: each skill name has one effective source."""

    names = _public_skill_names()
    check(len(names) == len(set(names)), f"公开技能名重复: {names}")
    methods = PLUGIN_ROOT / "internal" / "methods"
    if methods.is_dir():
        overlap = sorted({p.name for p in methods.iterdir() if p.is_dir()} & set(names))
        check(not overlap, f"internal/methods 与公开技能同名并存: {overlap}")


def test_each_public_skill_is_loadable() -> None:
    """T1: a new session can load each public skill by its SKILL.md."""

    for name in PUBLIC_SKILLS:
        skill_md = _skills_root() / name / "SKILL.md"
        check(skill_md.is_file(), f"缺少可加载入口 skills/{name}/SKILL.md")
        if not skill_md.is_file():
            continue
        fm = _frontmatter(skill_md.read_text(encoding="utf-8"))
        check(
            re.search(rf"^name:\s*{re.escape(name)}\s*$", fm, re.MULTILINE) is not None,
            f"{name} frontmatter name 必须是 {name}",
        )


def test_plugin_does_not_register_gate() -> None:
    """T1/D8: ordinary use must not require mgs-gate configuration."""

    manifest_path = PLUGIN_ROOT / ".codex-plugin" / "plugin.json"
    check(manifest_path.is_file(), "缺少 .codex-plugin/plugin.json")
    if not manifest_path.is_file():
        return
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    check("mcpServers" not in manifest, "plugin.json 不得注册 mcpServers/mgs-gate")
    root_mcp = PLUGIN_ROOT / ".mcp.json"
    check(not root_mcp.is_file(), "插件根不得再放 .mcp.json,以免安装后自动注册 mgs-gate")


def test_upstream_pin_license_and_fingerprints() -> None:
    """T1: fixed upstream version, SHA, license, original vs distributed hashes."""

    data = _load_fingerprints()
    if not data:
        return
    upstream = data.get("upstream") or {}
    check(upstream.get("version") == UPSTREAM_VERSION,
          f"fingerprints upstream.version 应为 {UPSTREAM_VERSION},实际 {upstream.get('version')}")
    check(upstream.get("sha") == UPSTREAM_SHA,
          f"fingerprints upstream.sha 应为 {UPSTREAM_SHA},实际 {upstream.get('sha')}")
    check(upstream.get("license") == "MIT",
          f"fingerprints upstream.license 应为 MIT,实际 {upstream.get('license')}")
    by_path = _fingerprint_by_path(data)
    license_file = PLUGIN_ROOT / "provenance" / "licenses" / "mattpocock-skills-LICENSE.txt"
    check(license_file.is_file(), "缺少 mattpocock/skills MIT 许可文本副本")
    if license_file.is_file():
        text = license_file.read_text(encoding="utf-8")
        check("MIT License" in text and "Matt Pocock" in text, "MIT 许可副本内容不完整")
    for name in MATT_OFFICIAL:
        skill_dir = _skills_root() / name
        if not skill_dir.is_dir():
            check(False, f"缺少 Matt 技能目录 skills/{name}")
            continue
        for path in sorted(p for p in skill_dir.rglob("*") if p.is_file()):
            rel = str(path.relative_to(PLUGIN_ROOT))
            entry = by_path.get(rel)
            check(entry is not None, f"Matt 文件 {rel} 缺少 provenance 指纹")
            if entry is None:
                continue
            actual = sha256(path)
            check(actual == entry.get("sha256"),
                  f"{rel} 分发指纹与文件不符")
            check(bool(entry.get("original_sha256")), f"{rel} 缺少原始校验值")
            check(bool(entry.get("source")), f"{rel} 缺少来源记录")
            check(bool(entry.get("license")), f"{rel} 缺少许可记录")
            check(UPSTREAM_SHA in str(entry.get("source")),
                  f"{rel} 来源应钉在 {UPSTREAM_SHA}")
            check(MATT_UPSTREAM_PATH[name] in str(entry.get("source")),
                  f"{rel} 来源应含上游路径 {MATT_UPSTREAM_PATH[name]}")
            if entry.get("sha256") != entry.get("original_sha256"):
                check(bool(entry.get("adaptation")),
                      f"{rel} 分发内容已改,必须记录适配理由")
            else:
                check(not entry.get("adaptation"),
                      f"{rel} 与上游一致却标了适配理由")


def test_packaged_references_resolve() -> None:
    """T1: required packaged references resolve inside the plugin."""

    skip_example_files = {"CONTEXT-FORMAT.md"}
    for md in sorted(PLUGIN_ROOT.rglob("*.md")):
        if "__pycache__" in md.parts:
            continue
        if md.name in skip_example_files:
            continue
        for target in _markdown_targets(md):
            if target.startswith(EXTERNAL_PREFIXES) or target.startswith("#"):
                continue
            rel = target.split("#", 1)[0]
            if not rel or EXAMPLE_LINK.match(rel):
                continue
            resolved = (md.parent / rel).resolve()
            check(resolved.exists(),
                  f"{md.relative_to(PLUGIN_ROOT)} 引用的 {target} 无法在包内解析")


def test_game_entries_do_not_depend_on_gate() -> None:
    """T1/D8: new effective game entries do not require mgs-gate for ordinary work."""

    for name in GAME_ENTRIES:
        skill_md = _skills_root() / name / "SKILL.md"
        if not skill_md.is_file():
            continue
        text = skill_md.read_text(encoding="utf-8")
        check("mgs-gate" not in text and "mgs_write" not in text and "gate-protocol" not in text,
              f"{name} 新版有效入口不得依赖 mgs-gate / mgs_write / gate-protocol")


# --- T2: discovery and invocation ---------------------------------------------


def test_user_only_skills_cannot_be_model_invoked() -> None:
    """T2: Matt user-only skills keep disable-model-invocation."""

    for name in MATT_USER_ONLY:
        skill_md = _skills_root() / name / "SKILL.md"
        if not skill_md.is_file():
            continue
        fm = _frontmatter(skill_md.read_text(encoding="utf-8"))
        check("disable-model-invocation: true" in fm,
              f"{name} 是用户专用入口,frontmatter 必须 disable-model-invocation: true")


def test_producer_must_not_auto_invoke_user_only_skills() -> None:
    """T2: Game-Producer routing contract forbids auto-invoking user-only Matt skills."""

    contract = PLUGIN_ROOT / INVOCATION_CONTRACT_REL
    check(contract.is_file(), f"缺少调用合同 {INVOCATION_CONTRACT_REL}")
    if not contract.is_file():
        return
    text = contract.read_text(encoding="utf-8")
    forbidden = _parse_bullet_section(text, "Must not auto-invoke")
    check(sorted(forbidden) == sorted(MATT_USER_ONLY),
          "调用合同「Must not auto-invoke」必须等于规格中的 Matt 用户专用入口,"
          f"实际 {forbidden}")
    producer = _skills_root() / "game-producer" / "SKILL.md"
    check(producer.is_file(), "缺少 skills/game-producer/SKILL.md")
    if producer.is_file():
        producer_text = producer.read_text(encoding="utf-8")
        check(INVOCATION_CONTRACT_REL.split("/")[-1] in producer_text
              or "../../internal/game/invocation.md" in producer_text,
              "Game-Producer 必须引用调用合同,而不是自行串调用户专用入口")


def test_stage_requirements_reachable_from_game_and_matt_entries() -> None:
    """T2: current-stage requirements are reachable from game entries and a Matt entry."""

    index = PLUGIN_ROOT / STAGE_REQUIREMENTS_REL
    check(index.is_file(), f"缺少阶段资料入口 {STAGE_REQUIREMENTS_REL}")
    if not index.is_file():
        return
    index_text = index.read_text(encoding="utf-8")
    check("读取资料不是开始制作" in index_text or "Reading is not production" in index_text,
          "阶段资料入口必须声明读取资料不会自行启动制作")
    pointer = "../../internal/game/stage-requirements.md"
    for name in GAME_ENTRIES + ("implement", "to-spec", "to-tickets"):
        skill_md = _skills_root() / name / "SKILL.md"
        if not skill_md.is_file():
            continue
        text = skill_md.read_text(encoding="utf-8")
        check(pointer in text or STAGE_REQUIREMENTS_REL in text,
              f"{name} 必须指向当前阶段资料入口,以便新会话实际读取")
        if pointer in text:
            resolved = (skill_md.parent / pointer).resolve()
            check(resolved.is_file(), f"{name} 的阶段资料引用悬空: {resolved}")


def test_implement_does_not_commit_without_authorization() -> None:
    """T2/D8: implement's default ending leaves work uncommitted without commit authorization."""

    skill_md = _skills_root() / "implement" / "SKILL.md"
    check(skill_md.is_file(), "缺少 skills/implement/SKILL.md")
    if not skill_md.is_file():
        return
    text = skill_md.read_text(encoding="utf-8")
    check("Commit your work to the current branch." not in text,
          "implement 不得再使用无授权也提交的默认结尾")
    check("leave the work uncommitted" in text.lower()
          or "leave work uncommitted" in text.lower(),
          "implement 无提交授权时必须保留未提交成果")


def test_discovery_surface_matches_public_collection() -> None:
    """T2: the package discovery surface (skills/*/SKILL.md) is exactly the public set.

    This is the same listing Codex plugin install uses (`skills: ./skills/`).
    Isolated app-server invocation is recorded separately when a client is run.
    """

    listed = []
    root = _skills_root()
    if root.is_dir():
        for skill_md in sorted(root.glob("*/SKILL.md")):
            listed.append(skill_md.parent.name)
    check(listed == sorted(PUBLIC_SKILLS),
          f"发现面列出的技能必须与公开集合一致,实际 {listed}")


TESTS = (
    test_public_collection_matches_spec,
    test_retired_entries_are_not_effective,
    test_public_names_are_unique,
    test_each_public_skill_is_loadable,
    test_plugin_does_not_register_gate,
    test_upstream_pin_license_and_fingerprints,
    test_packaged_references_resolve,
    test_game_entries_do_not_depend_on_gate,
    test_user_only_skills_cannot_be_model_invoked,
    test_producer_must_not_auto_invoke_user_only_skills,
    test_stage_requirements_reachable_from_game_and_matt_entries,
    test_implement_does_not_commit_without_authorization,
    test_discovery_surface_matches_public_collection,
)


def main() -> int:
    return run_theme("改版组合包与可调用入口(T1/T2)", TESTS, FAILURES)


if __name__ == "__main__":
    sys.exit(main())

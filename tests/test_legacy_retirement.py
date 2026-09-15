#!/usr/bin/env python3
"""Issue #61 seams: retire old entries and gate as effective capabilities.

Confirmed seams (issue #61 AC + #49 T1 T2 T10 T12):
- T1: public collection is official 25 + three game entries; retired entries
  and gate are not effective capabilities; destinations are documented.
- T2: a new session discovers exactly that public set; each name has one source.
- T10: ordinary records/onboard/design/snapshot/delivery/migration work with
  no gate configuration.
- T12: effective project config and retired gate history stay separate.
- AC: keep still-useful records, version fingerprints, drafts and reread;
  drop token/lock/channel-audit/rollback capability promises.

Expected values come from #49 D1/D2/D8/D9, not from counting internals.

    python3 -B tests/test_legacy_retirement.py
"""

from __future__ import annotations

import ast
import json
import re
import sys
from pathlib import Path

from plugin_package_support import PLUGIN_ROOT, REPO_ROOT, make_checker, run_theme
from redesign_bundle_contract import (
    KEPT_RECORD_SEAMS,
    PUBLIC_SKILLS,
    RETIRED_ENTRIES_REL,
    RETIRED_ENTRY_DESTINATIONS,
    RETIRED_GAME_ENTRIES,
)

FAILURES, check = make_checker()

GATE_IMPORTS = {"mcp_gate", "mgs_runtime", "mgs_gate_registry",
                "mgs_local_write", "mgs_remote_write", "mgsrt_admin"}
RETIRED_CAPABILITY_PROMISES = (
    "角色令牌",
    "受控写锁",
    "通道审计",
    "事务回滚",
    "占用回收",
)
LIVE_DOC_GLOBS = (
    PLUGIN_ROOT / ".codex-plugin" / "plugin.json",
    PLUGIN_ROOT / "provenance" / "manifest.md",
    *sorted((PLUGIN_ROOT / "internal" / "contracts").glob("*.md")),
    *sorted((PLUGIN_ROOT / "internal" / "game").glob("*.md")),
    *sorted((PLUGIN_ROOT / "internal" / "proposals").glob("*.md")),
    *sorted((PLUGIN_ROOT / "skills").glob("*/SKILL.md")),
    REPO_ROOT / "README.md",
    REPO_ROOT / "CONTEXT.md",
)


def _public_skill_names() -> list[str]:
    root = PLUGIN_ROOT / "skills"
    if not root.is_dir():
        return []
    return sorted(p.name for p in root.iterdir() if p.is_dir())


def _parse_destination_map(text: str) -> dict[str, str]:
    mapping: dict[str, str] = {}
    for match in re.finditer(
            r"^-\s+(game-[a-z]+)\s+->\s+(\S+)\s*$", text, re.MULTILINE):
        mapping[match.group(1)] = match.group(2)
    return mapping


def _imported_names(path: Path) -> set[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    names: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                names.add(alias.name.split(".", 1)[0])
        elif isinstance(node, ast.ImportFrom) and node.module:
            names.add(node.module.split(".", 1)[0])
    return names


def test_public_collection_is_official_twenty_five_plus_three() -> None:
    """T1/T2: the loadable skill surface is exactly Matt official 25 + 3."""

    actual = _public_skill_names()
    check(actual == sorted(PUBLIC_SKILLS),
          "公开技能必须是正式 25 项加三个游戏入口,"
          f"实际 {actual}")
    listed = sorted(p.parent.name for p in (PLUGIN_ROOT / "skills").glob("*/SKILL.md"))
    check(listed == sorted(PUBLIC_SKILLS),
          f"发现面列出的技能必须与公开集合一致,实际 {listed}")


def test_retired_entries_are_not_executable() -> None:
    """T1: retired names have no SKILL.md alias or placeholder in the package."""

    leaked = []
    for name in RETIRED_GAME_ENTRIES:
        skill_md = PLUGIN_ROOT / "skills" / name / "SKILL.md"
        if skill_md.is_file():
            leaked.append(str(skill_md.relative_to(PLUGIN_ROOT)))
    check(not leaked, f"已退役入口仍可作为公开技能加载: {leaked}")


def test_gate_is_not_an_effective_capability() -> None:
    """T1/T10: the installable plugin has no gate server, protocol, or optional mode."""

    manifest = json.loads(
        (PLUGIN_ROOT / ".codex-plugin" / "plugin.json").read_text(encoding="utf-8"))
    check("mcpServers" not in manifest, "plugin.json 不得注册 mcpServers")
    check(not (PLUGIN_ROOT / ".mcp.json").is_file(),
          "插件根不得再放 .mcp.json")
    check(not (PLUGIN_ROOT / "runtime").exists(),
          "安装包不得再带 runtime/ 作为可执行 gate")
    check(not (PLUGIN_ROOT / "internal" / "protocols" / "gate-protocol.md").is_file(),
          "安装包不得再把 gate-protocol 当作有效能力")
    interface = json.dumps(manifest.get("interface") or {}, ensure_ascii=False)
    check("mgs-gate" not in interface and "mcpServers" not in interface,
          "plugin.json 不得把 mgs-gate 写成可选模式")
    check("optional" not in json.dumps(manifest, ensure_ascii=False).lower()
          or "mgs-gate" not in json.dumps(manifest, ensure_ascii=False),
          "plugin.json 不得保留 gate 可选模式")


def test_retired_entry_destinations_are_documented() -> None:
    """T1/D1: packaged destination notes exist; they are not executable aliases."""

    dest = PLUGIN_ROOT / RETIRED_ENTRIES_REL
    check(dest.is_file(), f"缺少旧入口去向说明 {RETIRED_ENTRIES_REL}")
    if not dest.is_file():
        return
    text = dest.read_text(encoding="utf-8")
    mapping = _parse_destination_map(text)
    check(mapping == RETIRED_ENTRY_DESTINATIONS,
          "旧入口去向必须等于 D1 字面量,"
          f"实际 {mapping}")
    check("可执行别名" not in text or "不是可执行别名" in text,
          "去向说明不得把旧名写成可执行别名")
    producer = PLUGIN_ROOT / "skills" / "game-producer" / "SKILL.md"
    if producer.is_file():
        producer_text = producer.read_text(encoding="utf-8")
        check("retired-entries.md" in producer_text,
              "Game-Producer 应指向旧入口去向说明")


def test_new_paths_do_not_import_gate() -> None:
    """T1/AC1: onboard, design, snapshot, delivery and migration do not import gate."""

    records = PLUGIN_ROOT / "records"
    offenders = []
    for path in sorted(records.glob("*.py")):
        imported = _imported_names(path)
        hit = sorted(imported & GATE_IMPORTS)
        if hit:
            offenders.append(f"{path.name}: {hit}")
    for name in ("game-producer", "game-init", "game-design"):
        skill_dir = PLUGIN_ROOT / "skills" / name
        for path in sorted(skill_dir.rglob("*.py")):
            imported = _imported_names(path)
            hit = sorted(imported & GATE_IMPORTS)
            if hit:
                offenders.append(f"{path.relative_to(PLUGIN_ROOT)}: {hit}")
    check(not offenders, f"新版路径仍导入 gate 运行代码: {offenders}")


def test_ordinary_records_work_without_gate_config() -> None:
    """T10: records seams import and stay callable with no runtime root."""

    records_dir = str(PLUGIN_ROOT / "records")
    if records_dir not in sys.path:
        sys.path.insert(0, records_dir)
    import mgs_records
    for name in KEPT_RECORD_SEAMS:
        check(callable(getattr(mgs_records, name, None)),
              f"仍有用途的记录接缝必须保留: {name}")
    check(not hasattr(mgs_records, "GateService"),
          "记录接口不得再暴露 GateService")


def test_kept_version_draft_and_reread_capabilities() -> None:
    """AC3: version fingerprints, drafts, reread and pending review remain."""

    check((PLUGIN_ROOT / "provenance" / "fingerprints.json").is_file(),
          "版本核对指纹必须保留")
    check((PLUGIN_ROOT / "internal" / "review" / "pending_review.py").is_file(),
          "完整待审回读入口必须保留")
    records_dir = str(PLUGIN_ROOT / "records")
    if records_dir not in sys.path:
        sys.path.insert(0, records_dir)
    import mgs_github
    check(callable(getattr(mgs_github.GithubBackend,
                           "record_unpublished_draft", None)),
          "未发布草稿接缝必须保留")
    check(callable(getattr(mgs_github.GithubBackend, "publish_drafts", None)),
          "草稿发布回读接缝必须保留")
    import mgs_records
    check(callable(getattr(mgs_records, "verify_project", None)),
          "回读核验接缝必须保留")
    check(callable(getattr(mgs_records, "read_safe_switch", None)),
          "切换回读接缝必须保留")
    check(callable(getattr(mgs_records, "read_local_material_migration", None)),
          "迁移回读接缝必须保留")


def test_effective_config_and_gate_history_stay_separate() -> None:
    """T12: live package does not convert retired gate into a permission system."""

    dest = PLUGIN_ROOT / RETIRED_ENTRIES_REL
    if dest.is_file():
        text = dest.read_text(encoding="utf-8")
        check("不是新版权限" in text or "不得当作新版权限" in text,
              "去向说明必须把 gate 历史与有效配置分开")
        check("可选" not in text or "不保留可选" in text or "不是可选" in text,
              "去向说明不得把 gate 写成可选模式")
    records_dir = str(PLUGIN_ROOT / "records")
    if records_dir not in sys.path:
        sys.path.insert(0, records_dir)
    import mgs_safe_switch
    source = (PLUGIN_ROOT / "records" / "mgs_safe_switch.py").read_text(
        encoding="utf-8")
    check("gate_as_permission" in source and "False" in source,
          "切换合同必须继续把 gate 历史排除在新版权限之外")
    check("real_migration_authorized" in source,
          "不得把夹具切换写成真实环境已授权迁移")
    check(callable(getattr(mgs_safe_switch, "plan_safe_switch", None)),
          "安全切换接缝必须保留")


def test_live_docs_drop_retired_capability_promises() -> None:
    """AC4: current-facing docs do not promise tokens, locks, audit or rollback."""

    context = (REPO_ROOT / "CONTEXT.md").read_text(encoding="utf-8")
    check("用户主动调用" in context or "显式调用" in context,
          "CONTEXT.md 必须保留用户主动调用/显式调用")
    check("制作统筹按需选择下游能力不属于" in context
          or "制作统筹按需选择下游能力不是用户主动调用" in context,
          "CONTEXT.md 不得把统筹委派混为用户主动调用")
    check("方案设计" in context and "制作实现" in context and "验证原型" in context,
          "CONTEXT.md 必须继续区分方案设计、制作实现和验证原型")
    offenders = []
    for path in LIVE_DOC_GLOBS:
        if not path.is_file():
            continue
        text = path.read_text(encoding="utf-8")
        rel = str(path.relative_to(REPO_ROOT))
        for phrase in RETIRED_CAPABILITY_PROMISES:
            if phrase in text:
                offenders.append(f"{rel}: {phrase}")
        if "gate-protocol" in text and "retired-entries" not in text:
            offenders.append(f"{rel}: gate-protocol")
    check(not offenders,
          "现行说明仍承诺已退役 gate 能力或仍把协议当有效依赖: "
          f"{offenders}")


TESTS = (
    test_public_collection_is_official_twenty_five_plus_three,
    test_retired_entries_are_not_executable,
    test_gate_is_not_an_effective_capability,
    test_retired_entry_destinations_are_documented,
    test_new_paths_do_not_import_gate,
    test_ordinary_records_work_without_gate_config,
    test_kept_version_draft_and_reread_capabilities,
    test_effective_config_and_gate_history_stay_separate,
    test_live_docs_drop_retired_capability_promises,
)


def main() -> int:
    return run_theme("旧入口与 gate 运行路径退役(T1/T2/T10/T12)", TESTS, FAILURES)


if __name__ == "__main__":
    sys.exit(main())

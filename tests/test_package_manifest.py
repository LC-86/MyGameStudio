#!/usr/bin/env python3
"""包完整性、入口形态、模板全集与内部引用闭包。

任务票 10 从 tests/test_plugin_package.py 按真实行为主题拆出;检查含义与原
案例保持一致,仅重组位置。原总入口仍聚合本主题。各主题文件可直接运行:

    python3 -B tests/test_package_manifest.py
"""

import json
import re
import sys
from plugin_package_support import (REPO_ROOT, PLUGIN_ROOT, make_checker, run_theme)

FAILURES, check = make_checker()

def test_manifest() -> None:
    manifest_path = PLUGIN_ROOT / ".codex-plugin" / "plugin.json"
    check(manifest_path.is_file(), "缺少 .codex-plugin/plugin.json")
    if not manifest_path.is_file():
        return
    manifest = json.loads(manifest_path.read_text())
    check(manifest.get("name") == "mygamestudio", "插件 name 必须是 mygamestudio")
    check(
        re.fullmatch(r"\d+\.\d+\.\d+", manifest.get("version", "")) is not None,
        "插件 version 必须是严格 semver",
    )
    for field in ("description", "author", "skills"):
        check(bool(manifest.get(field)), f"plugin.json 缺少 {field}")
    check(bool(manifest.get("author", {}).get("name")), "plugin.json 缺少 author.name")
    interface = manifest.get("interface", {})
    for field in (
        "displayName",
        "shortDescription",
        "longDescription",
        "developerName",
        "category",
        "defaultPrompt",
        "capabilities",
    ):
        check(bool(interface.get(field)), f"plugin.json interface 缺少 {field}")
def test_explicit_skills() -> None:
    """Issue #50: public skills are Matt official 25 + three game entries.

    Detailed collection/uniqueness checks live in test_package_redesign_bundle.py.
    This theme keeps the loadable-entry shape: SKILL.md, name, description, yaml.
    Game entries keep allow_implicit_invocation false so ordinary chat does not
    trigger them. Matt invocation flags stay with the upstream copies.
    """

    from redesign_bundle_contract import GAME_ENTRIES, PUBLIC_SKILLS

    skills_root = PLUGIN_ROOT / "skills"
    if not skills_root.is_dir():
        check(False, "缺少 skills/ 目录")
        return
    skill_dirs = sorted(p.name for p in skills_root.iterdir() if p.is_dir())
    check(skill_dirs == sorted(PUBLIC_SKILLS),
          f"公开技能入口应为 {sorted(PUBLIC_SKILLS)},实际为 {skill_dirs}")
    for skill_name in PUBLIC_SKILLS:
        skill_md = skills_root / skill_name / "SKILL.md"
        check(skill_md.is_file(), f"{skill_name} 缺少 SKILL.md")
        if not skill_md.is_file():
            continue
        text = skill_md.read_text()
        match = re.match(r"^---\n(.*?)\n---\n", text, re.DOTALL)
        check(match is not None, f"{skill_name} SKILL.md 必须有 YAML frontmatter")
        if match:
            frontmatter = match.group(1)
            check(
                re.search(rf"^name:\s*{re.escape(skill_name)}\s*$", frontmatter, re.MULTILINE)
                is not None,
                f"{skill_name} frontmatter name 必须是 {skill_name}",
            )
            check(
                re.search(r"^description:\s*\S", frontmatter, re.MULTILINE) is not None,
                f"{skill_name} frontmatter 必须有非空 description",
            )
        openai_yaml = skills_root / skill_name / "agents" / "openai.yaml"
        check(openai_yaml.is_file(), f"{skill_name} 缺少 agents/openai.yaml")
        if skill_name in GAME_ENTRIES and openai_yaml.is_file():
            yaml_text = openai_yaml.read_text()
            check(
                re.search(r"allow_implicit_invocation:\s*false", yaml_text) is not None,
                f"{skill_name} 必须 allow_implicit_invocation: false(关闭普通对话自动触发)",
            )
def test_mcp_gate_config() -> None:
    """Issue #61/D8: gate is retired; the installable plugin has no optional mode."""

    manifest = json.loads((PLUGIN_ROOT / ".codex-plugin" / "plugin.json").read_text())
    check("mcpServers" not in manifest, "plugin.json 不得注册 mcpServers")
    check(not (PLUGIN_ROOT / ".mcp.json").is_file(),
          "插件根不得再放 .mcp.json")
    check(not (PLUGIN_ROOT / "runtime").exists(),
          "安装包不得再带 runtime/ 作为可执行 gate")
    check(not (PLUGIN_ROOT / "internal" / "protocols" / "gate-protocol.md").is_file(),
          "安装包不得再把 gate-protocol 当作有效能力")
    dest = PLUGIN_ROOT / "internal" / "game" / "retired-entries.md"
    check(dest.is_file(), "缺少旧入口与 gate 去向说明")
def test_records_backend_module() -> None:
    module = PLUGIN_ROOT / "records" / "mgs_records.py"
    check(module.is_file(), "缺少 records/mgs_records.py(本地 Markdown 后端统一接口)")
    source = PLUGIN_ROOT / "records" / "mgs_record_source.py"
    check(source.is_file(), "缺少 records/mgs_record_source.py(协作配置与本地来源)")
    if module.is_file():
        # 兼容目的用导入与调用验证(不再正则截取源码):公开接缝与来源
        # module 的实体必须真实可导入、可调用(票 03 职责迁移后同此)。
        records_dir = str(module.parent)
        if records_dir not in sys.path:
            sys.path.insert(0, records_dir)
        import mgs_record_source
        import mgs_records
        for name in ("load_config", "list_tasks", "read_task",
                     "task_dependencies", "startable_tasks",
                     "verify_project", "plan_local_material_migration",
                     "apply_local_material_migration",
                     "read_local_material_migration",
                     "plan_github_material_migration",
                     "apply_github_material_migration",
                     "read_github_material_migration",
                     "plan_safe_switch",
                     "apply_safe_switch",
                     "read_safe_switch",
                     "rollback_safe_switch"):
            check(callable(getattr(mgs_records, name, None)),
                  f"records/mgs_records.py 缺少可用公开接缝 {name}")
        for name in ("load_config", "local_list_tasks", "local_read_task",
                     "parse_repo_location", "parse_remote_authorizations"):
            check(callable(getattr(mgs_record_source, name, None)),
                  f"records/mgs_record_source.py 缺少可用来源接缝 {name}")
def test_templates_and_game_init() -> None:
    templates_root = PLUGIN_ROOT / "templates"
    expected = sorted([
        "README.md",
        "project/CONFIG.md", "project/CONTEXT.md", "project/GAME_DESIGN.md",
        "project/INDEX.md", "project/PROJECT.md", "project/TECH_DESIGN.md",
        "work/result.md", "work/task.md",
        "records/decision.md", "records/onboarding.md", "records/research.md",
        "evidence/review.md", "evidence/playtest.md",
    ])
    actual = sorted(
        str(path.relative_to(templates_root))
        for path in templates_root.rglob("*") if path.is_file()
    ) if templates_root.is_dir() else []
    check(actual == expected,
          f"templates/ 应为设计模板全集 {expected},实际 {actual}")
    skill_md = PLUGIN_ROOT / "skills" / "game-init" / "SKILL.md"
    check(skill_md.is_file(), "缺少 skills/game-init/SKILL.md")
    if skill_md.is_file():
        text = skill_md.read_text()
        for ref in (
            "../../internal/game/stage-requirements.md",
            "../../internal/contracts/project-configuration.md",
            "../../internal/proposals/project-onboarding.md",
            "../../internal/proposals/project-layout.md",
            "../../templates/README.md",
        ):
            check(ref in text, f"game-init SKILL.md 应引用包内依据 {ref}")
        check("setup-matt-pocock-skills" in text,
              "game-init 应将通用 tracker/标签/领域文档交给上游 setup")
        check("规格拆单" in text, "game-init 应声明不做规格拆单")
        for concept in (
            "已有项目",
            "实际行为", "已采纳", "历史内容", "缺口", "冲突", "未验证",
            "待决定",
        ):
            check(concept in text, f"game-init SKILL.md 应覆盖接手已有项目概念:{concept}")
def test_internal_methods_closure() -> None:
    """Issue #50: Matt methods are public skills, not a second internal copy."""

    methods_root = PLUGIN_ROOT / "internal" / "methods"
    check(not methods_root.exists(),
          "internal/methods 不得再保留与公开技能同名的第二份副本")
    promoted = {
        "domain-modeling", "grill-with-docs", "grilling",
        "research", "wayfinder", "writing-for-agents",
    }
    skills_root = PLUGIN_ROOT / "skills"
    missing = sorted(name for name in promoted if not (skills_root / name / "SKILL.md").is_file())
    check(not missing, f"已提升为公开技能的方法缺少 SKILL.md: {missing}")
    for rel in ("domain-modeling/CONTEXT-FORMAT.md", "domain-modeling/ADR-FORMAT.md"):
        check((skills_root / rel).is_file(), f"公开技能闭包缺少 {rel}")
def test_internal_references_resolve() -> None:
    """任务票 18(AC1):包内自研材料的 Markdown 相对链接可解析到实际文件。

    范围不含上游格式模板中的示例路径(如 CONTEXT-FORMAT.md 的
    ./src/ordering/CONTEXT.md,以及 wayfinder 地图示例中的 ](link))。
    """

    external_prefixes = ("http://", "https://", "mailto:")
    example_link = re.compile(r"^(link|./src/)")
    for md in sorted(PLUGIN_ROOT.rglob("*.md")):
        if md.name == "CONTEXT-FORMAT.md":
            continue  # 上游格式示例路径不是包运行引用
        text = md.read_text()
        for target in re.findall(r"\]\(([^)\s]+)\)", text):
            if target.startswith(external_prefixes) or target.startswith("#"):
                continue
            rel = target.split("#", 1)[0]
            if not rel or example_link.match(rel):
                continue
            resolved = (md.parent / rel).resolve()
            check(resolved.exists(),
                  f"{md.relative_to(PLUGIN_ROOT)} 引用的 {target} 无法在包内解析")


def test_skill_authority_references() -> None:
    """Issue #50: remaining game entries share common.md and result fields; no gate."""

    from redesign_bundle_contract import GAME_ENTRIES

    authority_sections = {
        PLUGIN_ROOT / "internal" / "contracts" / "common.md": (
            "共同规则的权威位置", "共同执行规则", "写入与保障"),
        PLUGIN_ROOT / "templates" / "work" / "result.md": (
            "结果字段",),
    }
    for doc, sections in authority_sections.items():
        check(doc.is_file(), f"缺少共同权威文件 {doc.relative_to(PLUGIN_ROOT)}")
        if doc.is_file():
            text = doc.read_text()
            for section in sections:
                heading_ok = re.search(
                    rf"^##\s+{re.escape(section)}(\s*\(|$)", text, re.MULTILINE)
                check(heading_ok is not None,
                      f"{doc.relative_to(PLUGIN_ROOT)} 应含完整权威小节标题「## {section}」")
    result_template = PLUGIN_ROOT / "templates" / "work" / "result.md"
    if result_template.is_file():
        text = result_template.read_text()
        for field in ("实际成果", "已执行验证", "独立审查", "人工验收", "未完成与限制"):
            check(field in text,
                  f"结果字段权威 templates/work/result.md 应含字段「{field}」")

    authorities = ("../../internal/contracts/common.md",)
    authority_anchors = ("共同执行规则", "写入与保障")
    for name in GAME_ENTRIES:
        skill_md = PLUGIN_ROOT / "skills" / name / "SKILL.md"
        check(skill_md.is_file(), f"缺少 skills/{name}/SKILL.md")
        if not skill_md.is_file():
            continue
        text = skill_md.read_text()
        for ref in authorities:
            check(ref in text, f"{name} SKILL.md 应引用共同权威 {ref}")
            resolved = (skill_md.parent / ref).resolve()
            check(resolved.is_file(),
                  f"{name} SKILL.md 引用的 {ref} 悬空(解析为 {resolved})")
        for anchor in authority_anchors:
            check(anchor in text, f"{name} SKILL.md 应指向《{anchor}》权威小节")
        check("gate-protocol" not in text and "mgs-gate" not in text,
              f"{name} 新版入口不得再把 gate 当作共同权威")


def test_config_template_adaptation() -> None:
    """任务票 18:模板相对设计仓库的适配只允许已登记的两处。

    templates/README.md 自任务票 04 起为适配版(链接改包内路径,provenance 已登记);
    templates/project/CONFIG.md 自 0.18.0 起(升级行为验证需要的真实模板演进)补充
    GitHub Issues 写入授权的记录格式说明。其余模板必须仍与设计仓库逐字节一致。
    """

    adapted = {"README.md", "project/CONFIG.md", "work/result.md"}
    design_root = REPO_ROOT / ".scratch" / "mygamestudio-framework" / "templates"
    if not design_root.is_dir():
        check(False, "缺少设计仓库 templates/(只读对照)")
        return
    plugin_templates = PLUGIN_ROOT / "templates"
    design_files = sorted(
        str(p.relative_to(design_root)) for p in design_root.rglob("*") if p.is_file()
    )
    plugin_files = sorted(
        str(p.relative_to(plugin_templates))
        for p in plugin_templates.rglob("*") if p.is_file()
    )
    check(design_files == plugin_files,
          f"模板文件集合应与设计仓库一致(仅内容适配),差异:{set(design_files) ^ set(plugin_files)}")
    for rel in design_files:
        plugin_file = plugin_templates / rel
        design_file = design_root / rel
        if rel not in adapted:
            check(plugin_file.read_bytes() == design_file.read_bytes(),
                  f"模板 {rel} 应与设计仓库逐字节一致(适配仅限 {sorted(adapted)})")
        elif rel == "project/CONFIG.md":
            text = plugin_file.read_text()
            check("issues-write" in text and "host/owner/repository" in text,
                  "适配后的 CONFIG 模板应说明 issues-write 授权记录格式")
            check(plugin_file.read_bytes() != design_file.read_bytes(),
                  "CONFIG.md 模板应有 0.18.0 适配差异(供升级行为验证)")
        elif rel == "work/result.md":
            text = plugin_file.read_text()
            check("## 结果字段" in text,
                  "适配后的 result.md 应含《结果字段》小节(任务票 23 权威锚点)")
            check(plugin_file.read_bytes() != design_file.read_bytes(),
                  "result.md 应有任务票 23 权威锚点适配差异")


TESTS = (
    test_manifest,
    test_explicit_skills,
    test_mcp_gate_config,
    test_records_backend_module,
    test_templates_and_game_init,
    test_internal_methods_closure,
    test_internal_references_resolve,
    test_skill_authority_references,
    test_config_template_adaptation,

)


def main() -> int:
    return run_theme("包完整性(清单/入口/模板/引用)", TESTS, FAILURES)


if __name__ == "__main__":
    sys.exit(main())

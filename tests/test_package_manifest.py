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
    skills_root = PLUGIN_ROOT / "skills"
    if not skills_root.is_dir():
        check(False, "缺少 skills/ 目录")
        return
    expected = [
        "game-art", "game-audio", "game-build", "game-code", "game-design",
        "game-implement", "game-init", "game-plan", "game-playtest",
        "game-producer", "game-prototype", "game-review", "game-spec",
        "game-status",
    ]
    skill_dirs = sorted(p.name for p in skills_root.iterdir() if p.is_dir())
    check(
        skill_dirs == expected,
        f"任务票 14 后包内技能入口应为 {expected},实际为 {skill_dirs}",
    )
    for skill_name in expected:
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
                re.search(rf"^name:\s*{skill_name}\s*$", frontmatter, re.MULTILINE)
                is not None,
                f"{skill_name} frontmatter name 必须是 {skill_name}",
            )
            check(
                re.search(r"^description:\s*\S", frontmatter, re.MULTILINE) is not None,
                f"{skill_name} frontmatter 必须有非空 description",
            )
        openai_yaml = skills_root / skill_name / "agents" / "openai.yaml"
        check(openai_yaml.is_file(), f"{skill_name} 缺少 agents/openai.yaml")
        if openai_yaml.is_file():
            yaml_text = openai_yaml.read_text()
            check(
                re.search(r"allow_implicit_invocation:\s*false", yaml_text) is not None,
                f"{skill_name} 必须 allow_implicit_invocation: false(关闭普通对话自动触发)",
            )
    reference = skills_root / "game-status" / "references" / "status-check.md"
    check(reference.is_file(), "game-status 缺少 references/status-check.md")
def test_mcp_gate_config() -> None:
    mcp_path = PLUGIN_ROOT / ".mcp.json"
    check(mcp_path.is_file(), "缺少插件根 .mcp.json(mgs-gate 通道声明)")
    if not mcp_path.is_file():
        return
    config = json.loads(mcp_path.read_text())
    server = config.get("mcpServers", {}).get("mgs-gate")
    check(server is not None, ".mcp.json 必须声明 mgs-gate 服务器")
    if server is None:
        return
    check(server.get("command") == "python3", "mgs-gate command 应为 python3(按 PATH 解析)")
    check(server.get("args") == ["runtime/mcp_gate.py"],
          f"mgs-gate args 应为 runtime/mcp_gate.py,实际 {server.get('args')}")
    check(server.get("cwd") == ".", "mgs-gate cwd 应为 .(解析为插件根,使相对 args 可用)")
    check("MGS_RUNTIME_ROOT" in (server.get("env_vars") or []),
          "mgs-gate 必须经 env_vars 透传 MGS_RUNTIME_ROOT(不在包内硬编码绝对路径)")
    check(server.get("default_tools_approval_mode") == "approve",
          "mgs-gate 工具应为预先批准模式(拦截由服务端策略承担,而非逐次审批)")
    for rel in ("runtime/mcp_gate.py", "runtime/mgs_runtime.py", "runtime/mgsrt_admin.py"):
        check((PLUGIN_ROOT / rel).is_file(), f"缺少运行保障组件 {rel}")
    protocol = PLUGIN_ROOT / "internal" / "protocols" / "gate-protocol.md"
    check(protocol.is_file(), "缺少 internal/protocols/gate-protocol.md(受控写入协议)")
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
                     "verify_project"):
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
            "../../internal/contracts/project-configuration.md",
            "../../internal/proposals/project-onboarding.md",
            "../../internal/proposals/project-layout.md",
            "../../templates/README.md",
            "../../internal/methods/writing-for-agents/SKILL.md",
            "../../internal/protocols/gate-protocol.md",
        ):
            check(ref in text, f"game-init SKILL.md 应引用包内依据 {ref}")
        check("不逐文件重复询问" in text, "game-init 应约定同一确认范围内不逐文件重复询问")
        check("文档接入就绪" in text and "运行保障就绪" in text,
              "game-init 报告结构应区分文档接入就绪与运行保障就绪")
        check("规格拆单" in text, "game-init 应声明不做规格拆单")
        # 任务票 05:接手已有项目的技能纪律
        for concept in (
            "已有项目",          # 已有项目分析分支
            "实际行为", "已采纳", "历史内容", "缺口", "冲突", "未验证",  # 六类现状区分
            "待决定",            # 矛盾交开发者决定
            "混合",              # 混合职责文档
            "拆分",              # 拆分或受控应用方案
            "恢复", "重复运行",   # 中断恢复与重复运行
            "模板升级",          # 模板升级流程
        ):
            check(concept in text, f"game-init SKILL.md 应覆盖接手已有项目概念:{concept}")
        check("不自动" in text or "不得" in text,
              "game-init 应明确不自动把实现采纳为产品意图")
def test_internal_methods_closure() -> None:
    """任务票 06:设计分支内部方法随包闭包,且不注册为公共技能入口。"""

    methods_root = PLUGIN_ROOT / "internal" / "methods"
    expected_methods = {
        "domain-modeling", "grill-with-docs", "grilling",
        "research", "wayfinder", "writing-for-agents",
    }
    actual_methods = (
        {p.name for p in methods_root.iterdir() if p.is_dir()}
        if methods_root.is_dir() else set()
    )
    check(
        actual_methods == expected_methods,
        f"internal/methods 应为依赖闭包 {sorted(expected_methods)},实际 {sorted(actual_methods)}",
    )
    for name in sorted(expected_methods):
        skill_md = methods_root / name / "SKILL.md"
        check(skill_md.is_file(), f"内部方法 {name} 缺少 SKILL.md")
    for rel in ("domain-modeling/CONTEXT-FORMAT.md", "domain-modeling/ADR-FORMAT.md"):
        check((methods_root / rel).is_file(), f"内部方法闭包缺少 {rel}")
    # 内部方法不得出现在公共技能目录(不额外暴露公共通用入口)
    skills_root = PLUGIN_ROOT / "skills"
    public_leak = expected_methods & {p.name for p in skills_root.iterdir()}
    check(not public_leak, f"内部方法被注册为公共技能入口:{sorted(public_leak)}")
def test_internal_references_resolve() -> None:
    """任务票 18(AC1):包内自研材料的 Markdown 相对链接可解析到实际文件。

    范围不含 internal/methods/(上游逐字节副本,其文内示例路径如
    ./src/ordering/CONTEXT.md 是方法示例,不是包运行引用;provenance 已注明)。
    """

    external_prefixes = ("http://", "https://", "mailto:")
    for md in sorted(PLUGIN_ROOT.rglob("*.md")):
        if "internal" in md.parts and "methods" in md.parts:
            continue  # 上游逐字节副本,示例路径不构成包内运行引用
        text = md.read_text()
        for target in re.findall(r"\]\(([^)\s]+)\)", text):
            if target.startswith(external_prefixes) or target.startswith("#"):
                continue
            rel = target.split("#", 1)[0]
            if not rel:
                continue
            resolved = (md.parent / rel).resolve()
            check(resolved.exists(),
                  f"{md.relative_to(PLUGIN_ROOT)} 引用的 {target} 无法在包内解析")
def test_config_template_adaptation() -> None:
    """任务票 18:模板相对设计仓库的适配只允许已登记的两处。

    templates/README.md 自任务票 04 起为适配版(链接改包内路径,provenance 已登记);
    templates/project/CONFIG.md 自 0.18.0 起(升级行为验证需要的真实模板演进)补充
    GitHub Issues 写入授权的记录格式说明。其余模板必须仍与设计仓库逐字节一致。
    """

    adapted = {"README.md", "project/CONFIG.md"}
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


TESTS = (
    test_manifest,
    test_explicit_skills,
    test_mcp_gate_config,
    test_records_backend_module,
    test_templates_and_game_init,
    test_internal_methods_closure,
    test_internal_references_resolve,
    test_config_template_adaptation,

)


def main() -> int:
    return run_theme("包完整性(清单/入口/模板/引用)", TESTS, FAILURES)


if __name__ == "__main__":
    sys.exit(main())

#!/usr/bin/env python3
"""最小插件包的确定性完整性检查(任务票 01 建立,票 02-04 扩展)。

接缝说明:本脚本只覆盖可静态核实的包内约定——
清单与技能形态、显式调用元信息、包内材料指纹与许可追溯、
不依赖开发机绝对路径、未注册额外公共技能入口、预置样例结构、
随包模板全集与本地任务后端模块接缝。
真实安装、显式调用与结果回读由 acceptance/<票号>/ 的
隔离验收流程覆盖,本脚本不替代。

用法:python3 tests/test_plugin_package.py
"""

import hashlib
import json
import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
PLUGIN_ROOT = REPO_ROOT / "plugin"

FAILURES: list[str] = []


def check(condition: bool, message: str) -> None:
    if not condition:
        FAILURES.append(message)


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load_fingerprints() -> dict:
    path = PLUGIN_ROOT / "provenance" / "fingerprints.json"
    if not path.is_file():
        check(False, "缺少 provenance/fingerprints.json")
        return {}
    data = json.loads(path.read_text())
    return {entry["path"]: entry for entry in data["files"]}


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
        "game-code", "game-design", "game-init", "game-producer",
        "game-prototype", "game-spec", "game-status",
    ]
    skill_dirs = sorted(p.name for p in skills_root.iterdir() if p.is_dir())
    check(
        skill_dirs == expected,
        f"任务票 06 后包内技能入口应为 {expected},实际为 {skill_dirs}",
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


def test_internal_material_provenance() -> None:
    """internal/ 与 templates/ 的适配材料必须与 fingerprints.json 一一对应。"""

    fingerprints = load_fingerprints()
    adapted_roots = (PLUGIN_ROOT / "internal", PLUGIN_ROOT / "templates")
    adapted_files = sorted(
        str(path.relative_to(PLUGIN_ROOT))
        for root in adapted_roots
        for path in root.rglob("*")
        if path.is_file()
    )
    check(
        set(adapted_files) == set(fingerprints),
        "internal/ + templates/ 的文件与 provenance/fingerprints.json 记录不一致:"
        f"\n  仅在目录中: {sorted(set(adapted_files) - set(fingerprints))}"
        f"\n  仅在记录中: {sorted(set(fingerprints) - set(adapted_files))}",
    )
    for rel_path in adapted_files:
        entry = fingerprints.get(rel_path)
        if entry is None:
            continue  # 集合差异已由上一条 check 记录
        actual = sha256(PLUGIN_ROOT / rel_path)
        check(
            actual == entry["sha256"],
            f"{rel_path} 的实际指纹与 provenance 记录不一致",
        )
        check(bool(entry.get("source")), f"{rel_path} 缺少来源记录")
        check(bool(entry.get("license")), f"{rel_path} 缺少许可记录")
    license_file = PLUGIN_ROOT / "provenance" / "licenses" / "mattpocock-skills-LICENSE.txt"
    check(license_file.is_file(), "缺少 mattpocock/skills MIT 许可文本副本")
    if license_file.is_file():
        text = license_file.read_text()
        check("MIT License" in text and "Matt Pocock" in text, "MIT 许可副本内容不完整")
    manifest_md = PLUGIN_ROOT / "provenance" / "manifest.md"
    check(manifest_md.is_file(), "缺少 provenance/manifest.md")


def test_no_dev_machine_paths() -> None:
    offenders = []
    for path in PLUGIN_ROOT.rglob("*"):
        if path.is_file() and "licenses" not in path.parts:
            text = path.read_text(errors="replace")
            if "/Users/" in text:
                offenders.append(str(path.relative_to(PLUGIN_ROOT)))
    check(not offenders, f"包内文件引用了开发机绝对路径: {offenders}")


def test_sample_fixtures() -> None:
    samples_root = REPO_ROOT / "samples"
    if not samples_root.is_dir():
        check(False, "缺少 samples/ 目录")
        return
    healthy = samples_root / "pixel-jumper"
    entry = healthy / "docs" / "mygamestudio" / "INDEX.md"
    check(entry.is_file(), "预置样例缺少 docs/mygamestudio/INDEX.md")
    for rel in (
        "docs/mygamestudio/CONFIG.md",
        "docs/mygamestudio/PROJECT.md",
        "docs/mygamestudio/GAME_DESIGN.md",
    ):
        check((healthy / rel).is_file(), f"预置样例缺少 {rel}")
    work_root = healthy / "docs" / "mygamestudio" / "work"
    if work_root.is_dir():
        tasks = sorted(p.name for p in work_root.iterdir())
    else:
        check(False, "预置样例缺少 docs/mygamestudio/work/")
        tasks = []
    check(
        len(tasks) >= 5,
        f"预置样例应至少覆盖五类状态的任务,实际任务目录: {tasks}",
    )
    for task_dir in tasks:
        task_md = work_root / task_dir / "task.md"
        check(task_md.is_file(), f"任务 {task_dir} 缺少 task.md")
        if task_md.is_file():
            text = task_md.read_text()
            check(
                re.search(r"当前分流:\s*(needs-triage|needs-info|ready-for-agent|ready-for-human|wontfix)", text)
                is not None,
                f"任务 {task_dir} 缺少有效分流状态",
            )
            check(
                re.search(r"进度:\s*\S", text) is not None,
                f"任务 {task_dir} 缺少进度字段",
            )
    not_onboarded = samples_root / "not-onboarded"
    check(
        not (not_onboarded / "docs" / "mygamestudio").exists(),
        "not-onboarded 样例不应包含 docs/mygamestudio",
    )
    conflicting = samples_root / "conflicting-records"
    check(
        (conflicting / "docs" / "mygamestudio" / "INDEX.md").is_file(),
        "conflicting-records 样例缺少 INDEX.md",
    )


def test_role_scope_demo_fixture() -> None:
    demo = REPO_ROOT / "samples" / "role-scope-demo"
    for rel in (
        "docs/mygamestudio/CONFIG.md",
        "docs/mygamestudio/INDEX.md",
        "docs/mygamestudio/PROJECT.md",
        "docs/mygamestudio/GAME_DESIGN.md",
        "docs/mygamestudio/TECH_DESIGN.md",
        "src/main.js",
        "src/player.js",
        "prototypes/README.md",
        "README.md",
    ):
        check((demo / rel).is_file(), f"role-scope-demo 样例缺少 {rel}")
    work = demo / "docs/mygamestudio/work"
    for rel in ("01-status-ledger/task.md", "02-coin-magnet/task.md",
                "03-dash-prototype/task.md"):
        path = work / rel
        check(path.is_file(), f"role-scope-demo 缺少 {rel}")
        if path.is_file():
            text = path.read_text()
            check(
                re.search(r"当前分流:\s*(needs-triage|needs-info|ready-for-agent|ready-for-human|wontfix)", text)
                is not None,
                f"role-scope-demo 任务 {rel} 缺少有效分流状态",
            )
            check(re.search(r"进度:\s*\S", text) is not None,
                  f"role-scope-demo 任务 {rel} 缺少进度字段")


def test_records_backend_module() -> None:
    module = PLUGIN_ROOT / "records" / "mgs_records.py"
    check(module.is_file(), "缺少 records/mgs_records.py(本地 Markdown 后端统一接口)")
    if module.is_file():
        text = module.read_text()
        for seam in ("def load_config", "def list_tasks", "def read_task",
                     "def verify_project"):
            check(seam in text, f"records/mgs_records.py 缺少公开接缝 {seam}")


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


def test_stardust_dash_fixture() -> None:
    sample = REPO_ROOT / "samples" / "stardust-dash"
    check((sample / "README.md").is_file(), "stardust-dash 样例缺少 README.md")
    check(not (sample / "docs").exists(),
          "stardust-dash 是未初始化的新项目样例,不应包含 docs/ 结构")


def test_nebula_drift_fixture() -> None:
    """任务票 05:接手已有项目样例——结构完整且「实现与文档矛盾」真实存在。"""

    sample = REPO_ROOT / "samples" / "nebula-drift"
    for rel in (
        "README.md", "package.json",
        "src/index.html", "src/main.js", "src/player.js",
        "assets/sprites/ship.svg", "assets/sprites/star.svg",
        "docs/DESIGN_NOTES.md", "docs/TECH_NOTES.md", "docs/HANDBOOK.md",
        "tasks/01-wire-jump/task.md", "tasks/02-starfield-bg/task.md",
    ):
        check((sample / rel).is_file(), f"nebula-drift 样例缺少 {rel}")
    if not (sample / "docs" / "DESIGN_NOTES.md").is_file():
        return
    check(not (sample / "docs" / "mygamestudio").exists(),
          "nebula-drift 是未接入的已有项目样例,不应包含 docs/mygamestudio")
    design = (sample / "docs" / "DESIGN_NOTES.md").read_text(encoding="utf-8")
    main_js = (sample / "src" / "main.js").read_text(encoding="utf-8")
    player_js = (sample / "src" / "player.js").read_text(encoding="utf-8")
    # 矛盾真实存在:设计笔记的已采纳要求 vs 代码实际行为
    check("仅键盘方向键" in design and "不支持 WASD" in design,
          "样例设计笔记应包含已采纳的「仅方向键、不支持 WASD」要求")
    check("单次推进" in design,
          "样例设计笔记应包含已采纳的「单次推进」要求")
    check(("KeyW" in main_js or "KeyA" in main_js or "WASD" in main_js),
          "样例 src/main.js 应实际支持 WASD 输入(与设计要求的矛盾必须真实)")
    check(("二段" in player_js or "maxJumps" in player_js),
          "样例 src/player.js 应实际实现二段推进(与设计要求的矛盾必须真实)")
    # 混合职责文档真实存在:同一文件混合管理/设计/技术内容
    handbook = (sample / "docs" / "HANDBOOK.md").read_text(encoding="utf-8")
    for marker in ("当前目标", "玩法规则", "技术备注"):
        check(marker in handbook, f"样例 HANDBOOK 应包含混合职责标记「{marker}」")
    # 已有任务为旧格式(未迁移):自有状态词汇,非五类分流
    for rel in ("tasks/01-wire-jump/task.md", "tasks/02-starfield-bg/task.md"):
        text = (sample / rel).read_text(encoding="utf-8")
        check("状态:" in text, f"{rel} 应为旧格式任务记录(状态: 行)")
        check("当前分流:" not in text, f"{rel} 不应已是迁移后格式")
    check("进行中" in (sample / "tasks" / "01-wire-jump" / "task.md").read_text(encoding="utf-8"),
          "任务 01 应为进行中(其进行中工作正是矛盾来源之一)")


def test_design_skills_content() -> None:
    """任务票 06:Game-Design / Game-Spec 显式入口的包内依据与关键纪律。"""

    design = PLUGIN_ROOT / "skills" / "game-design" / "SKILL.md"
    check(design.is_file(), "缺少 skills/game-design/SKILL.md")
    if design.is_file():
        text = design.read_text(encoding="utf-8")
        for ref in (
            "../../internal/contracts/design.md",
            "../../internal/contracts/common.md",
            "../../internal/contracts/records.md",
            "../../internal/protocols/gate-protocol.md",
            "../../internal/methods/grill-with-docs/SKILL.md",
            "../../internal/methods/wayfinder/SKILL.md",
            "../../internal/methods/research/SKILL.md",
            "../../internal/methods/writing-for-agents/SKILL.md",
        ):
            check(ref in text, f"game-design SKILL.md 应引用包内依据 {ref}")
        for concept in (
            "质询",            # 局部功能分支
            "决策地图",        # 多项未决问题分支
            "研究事实", "助手建议", "候选方案",   # 四类区分
            "决定者",          # 采纳标注区分决定来源
            "出处",            # 事实调查可追溯
            "不冒充",          # 助手建议不冒充用户决定
            "未决",            # 未决项保留
            "Game-Spec",       # 基线同步归 Game-Spec,本入口不写基线
            "公共入口",        # 内部方法不额外暴露公共入口
        ):
            check(concept in text, f"game-design SKILL.md 应覆盖概念:{concept}")

    spec = PLUGIN_ROOT / "skills" / "game-spec" / "SKILL.md"
    check(spec.is_file(), "缺少 skills/game-spec/SKILL.md")
    if spec.is_file():
        text = spec.read_text(encoding="utf-8")
        for ref in (
            "../../internal/contracts/design.md",
            "../../internal/contracts/common.md",
            "../../internal/contracts/records.md",
            "../../internal/protocols/gate-protocol.md",
            "../../internal/methods/writing-for-agents/SKILL.md",
        ):
            check(ref in text, f"game-spec SKILL.md 应引用包内依据 {ref}")
        for concept in (
            "基线版本",        # 实质变化递增版本
            "采纳依据",        # 版本有可识别采纳依据
            "格式修正", "不触发",   # 格式修改不算新产品要求
            "统筹同步交接",    # 目标或范围变化输出交接
            "不静默",          # 不静默修改项目目标
            "未实现",          # 未实现内容不报告为实际功能
            "边界情况", "完成标准", "技术约定",  # 可执行规格要素
            "expected_sha256",  # 基线更新走版本校验
            "决定者",          # 只取实际采纳内容
            "已采纳",
        ):
            check(concept in text, f"game-spec SKILL.md 应覆盖概念:{concept}")


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


def _check_task_record(path: Path, label: str) -> None:
    check(path.is_file(), f"{label} 缺少 {path.name}")
    if path.is_file():
        text = path.read_text(encoding="utf-8")
        check(
            re.search(r"当前分流:\s*(needs-triage|needs-info|ready-for-agent|ready-for-human|wontfix)", text)
            is not None,
            f"{label} 缺少有效分流状态",
        )
        check(re.search(r"进度:\s*\S", text) is not None, f"{label} 缺少进度字段")
        for key in ("当前目标", "完成标准", "执行责任"):
            check(key in text, f"{label} 工作请求缺少 {key}")


def test_tide_pool_fixture() -> None:
    """任务票 06:局部功能质询样例——历史已采纳决定未同步基线、格式缺陷与
    范围排除项真实存在,供设计讨论与规格整理验收使用。"""

    sample = REPO_ROOT / "samples" / "tide-pool"
    for rel in (
        "README.md", "src/main.js", "src/index.html",
        "docs/mygamestudio/CONFIG.md", "docs/mygamestudio/INDEX.md",
        "docs/mygamestudio/PROJECT.md", "docs/mygamestudio/GAME_DESIGN.md",
        "docs/mygamestudio/TECH_DESIGN.md",
        "docs/mygamestudio/work/01-shell-collect/task.md",
        "docs/mygamestudio/work/02-tide-timer/task.md",
        "docs/mygamestudio/work/01-shell-collect/results/2026-09-04.md",
        "docs/mygamestudio/records/decision-2026-09-03-core-loop.md",
        "docs/mygamestudio/records/decision-2026-09-05-shell-streak.md",
    ):
        check((sample / rel).is_file(), f"tide-pool 样例缺少 {rel}")
    design = sample / "docs" / "mygamestudio" / "GAME_DESIGN.md"
    if not design.is_file():
        return
    design_text = design.read_text(encoding="utf-8")
    check("基线版本:v1" in design_text, "tide-pool GAME_DESIGN 应为基线 v1")
    check("##验证与未决项" in design_text,
          "tide-pool GAME_DESIGN 应含真实格式缺陷(标题缺空格,供格式修正验收)")
    check("连击" not in design_text,
          "历史已采纳决定(贝壳连击)尚未同步进基线——样例必须保持未同步状态")
    streak_path = (sample / "docs" / "mygamestudio" / "records"
                   / "decision-2026-09-05-shell-streak.md")
    if not streak_path.is_file():
        return
    streak = streak_path.read_text(encoding="utf-8")
    check("已采纳" in streak, "历史决定记录应为已采纳状态")
    check("未同步" in streak, "历史决定记录应标注尚未同步基线")
    check("开发者" in streak, "历史决定记录应记录实际决定者")
    project_path = sample / "docs" / "mygamestudio" / "PROJECT.md"
    if not project_path.is_file():
        return
    project = project_path.read_text(encoding="utf-8")
    check("本轮不包含" in project and "干扰" in project,
          "tide-pool PROJECT 应把干扰生物列在本轮不包含(采纳海鸥即构成范围变化)")
    main_js_path = sample / "src" / "main.js"
    if not main_js_path.is_file():
        return
    main_js = main_js_path.read_text(encoding="utf-8")
    check("shellCount" in main_js,
          "tide-pool src/main.js 应含贝壳计数实现事实(供可追溯的事实调查)")
    config_path = sample / "docs" / "mygamestudio" / "CONFIG.md"
    if not config_path.is_file():
        return
    config = config_path.read_text(encoding="utf-8")
    check("local-markdown" in config, "tide-pool CONFIG 应为本地 Markdown 后端")
    for content in ("项目目标", "游戏需求", "技术设计"):
        check(content in config, f"tide-pool CONFIG 文档映射缺少核心行:{content}")
    _check_task_record(sample / "docs/mygamestudio/work/01-shell-collect/task.md",
                       "tide-pool 任务 01")
    _check_task_record(sample / "docs/mygamestudio/work/02-tide-timer/task.md",
                       "tide-pool 任务 02")
    result_path = (sample / "docs/mygamestudio/work/01-shell-collect"
                   / "results/2026-09-04.md")
    if not result_path.is_file():
        return
    result = result_path.read_text(encoding="utf-8")
    check("01-shell-collect" in result, "结果记录应引用所属任务身份")
    task01_path = sample / "docs/mygamestudio/work/01-shell-collect/task.md"
    if not task01_path.is_file():
        return
    task01 = task01_path.read_text(encoding="utf-8")
    check("结果索引" in task01, "任务 01 应有结果索引")


def test_gear_city_fixture() -> None:
    """任务票 06:多项未决问题样例——想法大雾多,供决策地图分支验收使用。"""

    sample = REPO_ROOT / "samples" / "gear-city"
    for rel in (
        "README.md", "src/main.js", "src/index.html",
        "docs/mygamestudio/CONFIG.md", "docs/mygamestudio/INDEX.md",
        "docs/mygamestudio/PROJECT.md", "docs/mygamestudio/GAME_DESIGN.md",
        "docs/mygamestudio/TECH_DESIGN.md",
        "docs/mygamestudio/work/01-chapter-one/task.md",
    ):
        check((sample / rel).is_file(), f"gear-city 样例缺少 {rel}")
    readme_path = sample / "README.md"
    if not readme_path.is_file():
        return
    readme = readme_path.read_text(encoding="utf-8")
    check("每日挑战" in readme, "gear-city README 应含每日挑战的松散想法")
    check(readme.count("未想好") >= 3,
          "gear-city README 应含至少三个开发者自己未想清楚的问题(多项未决)")
    design_path = sample / "docs" / "mygamestudio" / "GAME_DESIGN.md"
    if not design_path.is_file():
        return
    design = design_path.read_text(encoding="utf-8")
    check("基线版本:v1" in design, "gear-city GAME_DESIGN 应为基线 v1(章节模式)")
    check("章节" in design, "gear-city 当前基线应为章节式关卡")
    check(not (sample / "docs" / "mygamestudio" / "records").exists()
          or not any((sample / "docs" / "mygamestudio" / "records").iterdir()),
          "gear-city 样例不应预置决策地图(由验收轮产生)")
    main_js = (sample / "src" / "main.js").read_text(encoding="utf-8")
    check("Math.random" in main_js,
          "gear-city src/main.js 应含 Math.random 事实(研究类决策工单的本地依据)")
    config = (sample / "docs" / "mygamestudio" / "CONFIG.md").read_text(encoding="utf-8")
    check("local-markdown" in config, "gear-city CONFIG 应为本地 Markdown 后端")
    _check_task_record(sample / "docs/mygamestudio/work/01-chapter-one/task.md",
                       "gear-city 任务 01")


def main() -> int:
    test_manifest()
    test_explicit_skills()
    test_mcp_gate_config()
    test_internal_material_provenance()
    test_no_dev_machine_paths()
    test_sample_fixtures()
    test_role_scope_demo_fixture()
    test_records_backend_module()
    test_templates_and_game_init()
    test_stardust_dash_fixture()
    test_nebula_drift_fixture()
    test_design_skills_content()
    test_internal_methods_closure()
    test_tide_pool_fixture()
    test_gear_city_fixture()
    if FAILURES:
        print(f"FAIL ({len(FAILURES)} 项):")
        for failure in FAILURES:
            print(f"  - {failure}")
        return 1
    print("OK: 最小插件包静态完整性检查全部通过")
    return 0


if __name__ == "__main__":
    sys.exit(main())

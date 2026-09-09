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
                     "def task_dependencies", "def startable_tasks",
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


def test_prototype_skill_content() -> None:
    """任务票 07:Game-Prototype 完整原型工作流的包内依据与关键纪律。"""

    proto = PLUGIN_ROOT / "skills" / "game-prototype" / "SKILL.md"
    check(proto.is_file(), "缺少 skills/game-prototype/SKILL.md")
    if proto.is_file():
        text = proto.read_text(encoding="utf-8")
        for ref in (
            "../../internal/contracts/design.md",
            "../../internal/contracts/common.md",
            "../../internal/protocols/gate-protocol.md",
            "../../internal/methods/writing-for-agents/SKILL.md",
        ):
            check(ref in text, f"game-prototype SKILL.md 应引用包内依据 {ref}")
        for concept in (
            "要验证的设计问题",   # 输入:问题
            "原型范围",           # 输入:范围
            "输出位置",           # 输入:输出位置
            "可用",               # 输入:可用方法/工具
            "最小可检验实现",     # 合同措辞:选择足以验证问题的小实现
            "不自动扩大",         # 不自动扩大到正式产品制作
            "正式工程",           # 原型不写正式工程
            "运行或查看方式",     # 合同措辞:输出含启动/查看方式
            "已执行操作",         # 输出含实际执行的操作与结果
            "原型观察", "设计判断", "尚未验证",   # 结论四类区分(前三)
            "体验反馈",           # 第四类:需要人的体验反馈
            "真实反馈", "待验收",  # 只引用真实反馈;未收到保留待验收
            "Game-Spec", "Game-Implement",   # 交接对象
            "复用或重写",         # 复用或重写由正式集成条件决定
            "不等于正式产品",     # 原型可运行不等于正式产品已经实现
            "mgs_scope",          # 写入前先确认有效范围
            "更窄",               # 原型用途比角色范围更窄,差异如实报告
            "会话工作区",         # 原型运行发生在会话工作区,不写项目
        ):
            check(concept in text, f"game-prototype SKILL.md 应覆盖概念:{concept}")


def test_accept07_fixture() -> None:
    """任务票 07:tide-pool 的 06 成果注入夹具——设计已采纳、参数待原型验证的
    起始状态真实存在(覆盖 samples/tide-pool,不改动样例本体以保 06 可复现)。"""

    fixtures = REPO_ROOT / "acceptance" / "07-isolated-design-prototype" / "fixtures"
    for rel in (
        "README.md",
        "docs/mygamestudio/GAME_DESIGN.md",
        "docs/mygamestudio/PROJECT.md",
        "docs/mygamestudio/CONFIG.md",
        "docs/mygamestudio/records/decision-2026-09-08-gull-swoop.md",
        "docs/mygamestudio/records/research-2026-09-08-gull-facts.md",
        "docs/mygamestudio/records/decision-2026-09-05-shell-streak.md",
        "prototypes/README.md",
    ):
        check((fixtures / rel).is_file(), f"accept-07 夹具缺少 {rel}")
    design = fixtures / "docs" / "mygamestudio" / "GAME_DESIGN.md"
    if not design.is_file():
        return
    design_text = design.read_text(encoding="utf-8")
    check("基线版本:v2" in design_text, "夹具 GAME_DESIGN 应为 06 产出的基线 v2")
    check("连击" in design_text and "海鸥" in design_text,
          "夹具 GAME_DESIGN v2 应纳入连击与海鸥两项采纳内容")
    check("未实现" in design_text, "夹具 GAME_DESIGN 应标注新增能力未实现")
    check("## 验证与未决项" in design_text,
          "夹具 GAME_DESIGN 的格式缺陷应已修复(06 W3 结果)")
    check("decision-2026-09-05-shell-streak" in design_text
          and "decision-2026-09-08-gull-swoop" in design_text,
          "夹具 GAME_DESIGN 变更索引应引用两份采纳依据")
    check("预警" in design_text and "未决" in design_text,
          "夹具 GAME_DESIGN 应保留「出现预警」未决项")
    gull = (fixtures / "docs" / "mygamestudio" / "records"
            / "decision-2026-09-08-gull-swoop.md")
    if gull.is_file():
        gull_text = gull.read_text(encoding="utf-8")
        check("已采纳" in gull_text, "夹具海鸥决定记录应为已采纳")
        check("未决" in gull_text, "夹具海鸥决定记录应保留预警未决")
        check("开发者" in gull_text, "夹具海鸥决定记录应标注实际决定者")
        check("统筹同步" in gull_text, "夹具海鸥决定记录应记录范围变化的统筹同步去向")
    streak = (fixtures / "docs" / "mygamestudio" / "records"
              / "decision-2026-09-05-shell-streak.md")
    if streak.is_file():
        streak_text = streak.read_text(encoding="utf-8")
        check("已同步" in streak_text and "v2" in streak_text,
              "夹具历史决定记录应已补记同步 v2")
        check("选项 A" in streak_text, "夹具历史决定记录既有内容应保留")
    readme = fixtures / "README.md"
    if readme.is_file():
        readme_text = readme.read_text(encoding="utf-8")
        check("原型" in readme_text and "prototypes" in readme_text,
              "夹具 README 当前请求应指向隔离原型验证")
        check("窗口" in readme_text, "夹具 README 应提出拾回窗口的验证问题")
        check("预警" in readme_text, "夹具 README 应保留预警的未决/试玩诉求")
    project = fixtures / "docs" / "mygamestudio" / "PROJECT.md"
    if project.is_file():
        project_text = project.read_text(encoding="utf-8")
        check("基线版本:v2" in project_text, "夹具 PROJECT 应为统筹同步后的 v2")
        check("海鸥" in project_text, "夹具 PROJECT 应把海鸥纳入本轮范围")
        check("干扰生物" not in project_text,
              "夹具 PROJECT「本轮不包含」不应再列干扰生物(范围已同步)")
    proto_area = fixtures / "prototypes" / "README.md"
    if proto_area.is_file():
        area_text = proto_area.read_text(encoding="utf-8")
        check("不属于正式工程" in area_text,
              "夹具原型区说明应声明不属于正式工程")
        check("Game-Spec" in area_text,
              "夹具原型区说明应说明结论经 Game-Spec 采纳后才进入正式规格")
    # 夹具是覆盖层:samples/tide-pool 本体必须保持 06 验收所需的原始状态
    sample_design = (REPO_ROOT / "samples" / "tide-pool" / "docs" / "mygamestudio"
                     / "GAME_DESIGN.md")
    if sample_design.is_file():
        sample_text = sample_design.read_text(encoding="utf-8")
        check("基线版本:v1" in sample_text,
              "samples/tide-pool 本体应保持 v1(06 验收可复现;07 用夹具覆盖)")


def test_game_plan_skill_content() -> None:
    """任务票 08:Game-Plan 规格拆单入口的包内依据与关键纪律。"""

    plan = PLUGIN_ROOT / "skills" / "game-plan" / "SKILL.md"
    check(plan.is_file(), "缺少 skills/game-plan/SKILL.md")
    if plan.is_file():
        text = plan.read_text(encoding="utf-8")
        for ref in (
            "../../internal/contracts/management.md",
            "../../internal/contracts/common.md",
            "../../internal/contracts/records.md",
            "../../internal/contracts/task-triage.md",
            "../../internal/protocols/gate-protocol.md",
            "../../internal/methods/writing-for-agents/SKILL.md",
            "../../templates/work/task.md",
        ):
            check(ref in text, f"game-plan SKILL.md 应引用包内依据 {ref}")
        for concept in (
            "原子任务",          # 合同措辞:形成当前及近期的原子任务
            "已采纳",            # 只拆已采纳规格,未决项不拆成可执行任务
            "粗粒度",            # 远期工作保持合适粒度,不展开
            "引用",              # 已有要求使用引用,不复制规格正文
            "稳定身份",          # 身份稳定,排序变化不重命名
            "完成标准", "执行责任", "验收方式",  # 逐项任务字段
            "所需能力",          # 拆单轮附加字段(能力核对)
            "真实依赖",          # 依赖只记录真正影响开工的任务
            "集成",              # 共享成果写入协调与集成责任
            "单一写入者",        # 同一可写成果单一修改者
            "分流",              # 按五类分流安排
            "needs-info",        # 输入不足的分流去向
            "wontfix",           # 暂缓/依赖未完成不误写成 wontfix
            "试玩",              # 需要人工试玩不阻止 Agent 制作
            "不新建",            # 重复拆解不静默制造重复任务
            "结果索引",          # 结果入口
            "可开工",            # 当前可开工集合
            "循环",              # 依赖可解析且无循环
            "授权",              # ready-for-agent 不等于已获全部授权
            "expected_sha256",   # 更新既有任务走版本校验
            "mgs_records",       # 统一接口
        ):
            check(concept in text, f"game-plan SKILL.md 应覆盖概念:{concept}")


def test_accept08_fixture() -> None:
    """任务票 08:tide-pool 的 06/07 成果注入夹具——已采纳规格 v2 与原型结论
    真实存在,供规格拆单验收使用(覆盖 samples/tide-pool,不改样例本体)。"""

    fixtures = REPO_ROOT / "acceptance" / "08-spec-to-local-tasks" / "fixtures"
    for rel in (
        "README.md",
        "docs/mygamestudio/GAME_DESIGN.md",
        "docs/mygamestudio/PROJECT.md",
        "docs/mygamestudio/CONFIG.md",
        "docs/mygamestudio/records/decision-2026-09-08-gull-swoop.md",
        "docs/mygamestudio/records/research-2026-09-08-gull-facts.md",
        "prototypes/README.md",
        "prototypes/gull-window/report.md",
        "prototypes/gull-window/README.md",
    ):
        check((fixtures / rel).is_file(), f"accept-08 夹具缺少 {rel}")
    design = fixtures / "docs" / "mygamestudio" / "GAME_DESIGN.md"
    if design.is_file():
        design_text = design.read_text(encoding="utf-8")
        check("基线版本:v2" in design_text, "夹具 GAME_DESIGN 应为 06 产出的基线 v2")
        check("海鸥" in design_text and "连击" in design_text,
              "夹具 GAME_DESIGN v2 应纳入海鸥与连击采纳内容")
        check("未决" in design_text, "夹具 GAME_DESIGN 应保留预警未决项")
    project = fixtures / "docs" / "mygamestudio" / "PROJECT.md"
    if project.is_file():
        project_text = project.read_text(encoding="utf-8")
        check("基线版本:v2" in project_text, "夹具 PROJECT 应为统筹同步后的 v2")
        check("海鸥" in project_text, "夹具 PROJECT 应把海鸥纳入本轮范围")
    config = fixtures / "docs" / "mygamestudio" / "CONFIG.md"
    if config.is_file():
        config_text = config.read_text(encoding="utf-8")
        check("无音频制作能力" in config_text,
              "夹具 CONFIG 应保留无音频制作能力(能力核对依据)")
        check("prototypes" in config_text, "夹具 CONFIG 应含原型区执行条件")
    readme = fixtures / "README.md"
    if readme.is_file():
        readme_text = readme.read_text(encoding="utf-8")
        check("拆" in readme_text and "海鸥" in readme_text,
              "夹具 README 当前请求应指向海鸥规格拆单")
        check("原型" in readme_text, "夹具 README 应说明原型结论可用作拆单输入")
    proto_report = fixtures / "prototypes" / "gull-window" / "report.md"
    if proto_report.is_file():
        report_text = proto_report.read_text(encoding="utf-8")
        check("原型观察" in report_text and "待验收" in report_text,
              "夹具原型验证记录应保留四类结论区分与待人工验收状态")
    # 夹具是覆盖层:samples/tide-pool 本体必须保持 v1(06/07 验收可复现)
    sample_design = (REPO_ROOT / "samples" / "tide-pool" / "docs" / "mygamestudio"
                     / "GAME_DESIGN.md")
    if sample_design.is_file():
        sample_text = sample_design.read_text(encoding="utf-8")
        check("基线版本:v1" in sample_text,
              "samples/tide-pool 本体应保持 v1(06 验收可复现;08 用夹具覆盖)")


def test_production_skills_content() -> None:
    """任务票 09:Game-Implement 组织入口与 Game-Code 完整工作流的依据与纪律。"""

    impl = PLUGIN_ROOT / "skills" / "game-implement" / "SKILL.md"
    check(impl.is_file(), "缺少 skills/game-implement/SKILL.md")
    if impl.is_file():
        text = impl.read_text(encoding="utf-8")
        for ref in (
            "../../internal/contracts/production.md",
            "../../internal/contracts/common.md",
            "../../internal/contracts/records.md",
            "../../internal/protocols/gate-protocol.md",
            "../../internal/methods/writing-for-agents/SKILL.md",
            "../../templates/work/result.md",
        ):
            check(ref in text, f"game-implement SKILL.md 应引用包内依据 {ref}")
        for concept in (
            "当前任务",          # 输入:当前任务(引用或从可开工集合选取)
            "统一接口",          # 经 mgs_records 读取任务/依赖/可开工
            "允许修改范围",      # 开工前核对修改范围
            "实际配置",          # 实现方法来自项目实际配置
            "默认引擎",          # 样例技术选择不成为框架默认引擎
            "专业技能",          # 组织:选择本任务需要的专业技能
            "Game-Code",        # 代码路径的专业执行入口
            "不伪装",            # 尚未实现的专业入口不伪装成已调用能力
            "技术设计",          # 必要技术方案由制作实现维护
            "冲突", "交回",      # 产品规则冲突/目标变化记录影响并交回
            "不自行降低",        # 不自行降低要求
            "集成",              # 组织集成与集成责任
            "风险匹配",          # 与变更风险匹配的验证
            "结果索引",          # 结果交接入口
            "待验收",            # 独立审查/人工验收未完成保留待验收
            "总体目标",          # 不接管项目总体目标或排期
            "mgs_records",       # 统一接口
            "expected_sha256",   # 更新走版本校验
        ):
            check(concept in text, f"game-implement SKILL.md 应覆盖概念:{concept}")

    code = PLUGIN_ROOT / "skills" / "game-code" / "SKILL.md"
    check(code.is_file(), "缺少 skills/game-code/SKILL.md")
    if code.is_file():
        text = code.read_text(encoding="utf-8")
        for ref in (
            "../../internal/contracts/production.md",
            "../../internal/contracts/common.md",
            "../../internal/contracts/records.md",
            "../../internal/protocols/gate-protocol.md",
            "../../internal/methods/writing-for-agents/SKILL.md",
            "../../templates/work/result.md",
        ):
            check(ref in text, f"game-code SKILL.md 应引用包内依据 {ref}")
        for concept in (
            "实际任务",          # 读取实际任务而非凭记忆
            "基线",              # 相关基线与版本
            "依赖",              # 依赖核对
            "允许修改范围",      # 修改范围核对(以 mgs_scope 为准)
            "实际配置",          # 检查方式来自项目实际配置
            "默认",              # 样例技术选择不成为默认约束
            "技术设计",          # 必要时形成或细化技术设计
            "expected_sha256",   # 更新走版本校验
            "风险匹配",          # 选择与变更风险匹配的检查
            "行为",              # 行为层检查优先
            "会话工作区",        # 一次性检查脚本放会话工作区,不进项目
            "实际运行",          # 检查必须真实运行并记录输出
            "未运行",            # 未运行的检查明确列出
            "不虚构",            # 不虚构检查通过
            "待验收",            # 审查/人工验收未完成保留待验收
            "成果位置", "适用",  # 结果记录要素
            "冲突", "交回",      # 产品要求变化交回对应流程
            "进度", "缺口",      # 失败或中断保存实际进度和缺口
            "不自动",            # 普通实现不自动提交、推送、发布
            "受控",              # 新增命令执行路径保持受控
        ):
            check(concept in text, f"game-code SKILL.md 应覆盖概念:{concept}")


def test_accept09_fixture() -> None:
    """任务票 09:票 08 拆单真实成果注入夹具——02 可独立开工、04 等待 02、
    03 已收束,供代码任务执行验收使用(两层夹具覆盖,不改样例本体)。"""

    fixtures = REPO_ROOT / "acceptance" / "09-code-task-delivery" / "fixtures"
    for rel in (
        "README.md",
        "docs/mygamestudio/work/02-tide-timer/task.md",
        "docs/mygamestudio/work/03-gull-round-plan/task.md",
        "docs/mygamestudio/work/03-gull-round-plan/results/2026-09-08.md",
        "docs/mygamestudio/work/04-shell-combo/task.md",
        "docs/mygamestudio/work/05-gull-swoop/task.md",
        "docs/mygamestudio/work/06-gull-sprite/task.md",
        "docs/mygamestudio/work/07-warning-cue/task.md",
        "docs/mygamestudio/work/08-gull-playtest/task.md",
        "docs/mygamestudio/work/09-future-scope/task.md",
    ):
        check((fixtures / rel).is_file(), f"accept-09 夹具缺少 {rel}")
    task02 = fixtures / "docs/mygamestudio/work/02-tide-timer/task.md"
    if task02.is_file():
        text = task02.read_text(encoding="utf-8")
        check("v2" in text, "夹具 02 应引用 GAME_DESIGN v2(票 08 W2 更新)")
        check("01-shell-collect" in text and "已完成" in text,
              "夹具 02 的依赖 01 应为已完成(02 可开工)")
        check(re.search(r"进度(:|：)待执行", text) is not None,
              "夹具 02 进度应为待执行(本票执行对象)")
        check("倒计时" in text, "夹具 02 应为倒计时代码任务")
    task04 = fixtures / "docs/mygamestudio/work/04-shell-combo/task.md"
    if task04.is_file():
        text = task04.read_text(encoding="utf-8")
        check("02-tide-timer" in text,
              "夹具 04 应依赖 02(完成 02 才解锁,接续位置真实)")
    task03 = fixtures / "docs/mygamestudio/work/03-gull-round-plan/task.md"
    if task03.is_file():
        text = task03.read_text(encoding="utf-8")
        check(re.search(r"进度(:|：)已完成", text) is not None,
              "夹具 03 拆单管理任务应收束为已完成")
        check("results/2026-09-08.md" in text, "夹具 03 结果索引应引用拆单结果")
    readme = fixtures / "README.md"
    if readme.is_file():
        text = readme.read_text(encoding="utf-8")
        check("代码任务" in text, "夹具 README 当前请求应指向开工代码任务")
        check("检查" in text and "证据" in text,
              "夹具 README 应要求真实验证与可复现证据")
    # 样例本体保持 v1 未动(06/07/08 验收可复现;09 用夹具覆盖)
    sample_design = (REPO_ROOT / "samples" / "tide-pool" / "docs" / "mygamestudio"
                     / "GAME_DESIGN.md")
    if sample_design.is_file():
        check("基线版本:v1" in sample_design.read_text(encoding="utf-8"),
              "samples/tide-pool 本体应保持 v1(09 用夹具覆盖)")


def test_game_art_skill_content() -> None:
    """任务票 10:Game-Art 视觉资源工作流的包内依据与关键纪律。"""

    art = PLUGIN_ROOT / "skills" / "game-art" / "SKILL.md"
    check(art.is_file(), "缺少 skills/game-art/SKILL.md")
    if not art.is_file():
        return
    text = art.read_text(encoding="utf-8")
    for ref in (
        "../../internal/contracts/production.md",
        "../../internal/contracts/common.md",
        "../../internal/contracts/records.md",
        "../../internal/protocols/gate-protocol.md",
        "../../internal/methods/writing-for-agents/SKILL.md",
        "../../templates/work/result.md",
    ):
        check(ref in text, f"game-art SKILL.md 应引用包内依据 {ref}")
    for concept in (
        "视觉要求",        # 输入:当前视觉要求
        "用途",            # 输入:用途(在游戏中的接入位置)
        "参考",            # 输入:参考(研究记录、既有风格)
        "输出位置",        # 输入:输出位置
        "可用能力",        # 输入:可用能力(实际条件决定工具)
        "不固定",          # 不固定生成服务、引擎或资源类型
        "资源类型",        # 图像/模型/动画/特效等资源类型
        "mgs_scope",       # 写入前确认有效范围
        "允许修改范围",    # 任务范围核对(以 mgs_scope 为准)
        "缺口",            # 无制作/编辑/检查能力时报告具体缺口
        "可接手材料",      # 缺口时交付可接手材料
        "提示词",          # 不把提示词/参数/计划当最终成果
        "不是最终成果",    # 明确提示词与计划的定位
        "来源或生成依据",  # 输出:来源或生成依据
        "接入信息",        # 输出:使用/接入信息
        "预览",            # 输出:可定位预览
        "实际运行",        # 检查必须真实运行并记录输出
        "会话工作区",      # 检查脚本放会话工作区,不进项目
        "待验收",          # 人工审美验收未完成保留待验收
        "真实反馈",        # 审美验收需要真实反馈或明确等待项
        "适配",            # 工具输入输出适配与角色资源策略分离
        "资源策略",        # 分离的另一侧:策略由运行保障承担
        "不被假定",        # 服务或 GUI 不被假定继承本地边界
        "继承本地边界",    # 外部写入通路未验证不视为已受控
        "results/",        # 结果落点
        "进度",            # 任务进度与分流归统筹,直接调用不改
        "不自动",          # 不自动提交、推送、发布
        "受控",            # 新增命令执行路径保持受控
    ):
        check(concept in text, f"game-art SKILL.md 应覆盖概念:{concept}")


def test_accept10_fixture() -> None:
    """任务票 10:票 09 真实交付终态注入夹具——02 待验收、06 唯一可开工、
    TECH_DESIGN v2 与新 src 就位,供视觉资源任务执行验收使用(三层夹具
    覆盖,不改样例本体)。"""

    fixtures = REPO_ROOT / "acceptance" / "10-visual-asset-delivery" / "fixtures"
    for rel in (
        "README.md",
        "docs/mygamestudio/TECH_DESIGN.md",
        "src/main.js",
        "src/index.html",
        "docs/mygamestudio/work/02-tide-timer/task.md",
        "docs/mygamestudio/work/02-tide-timer/results/2026-09-08.md",
    ):
        check((fixtures / rel).is_file(), f"accept-10 夹具缺少 {rel}")
    tech = fixtures / "docs" / "mygamestudio" / "TECH_DESIGN.md"
    if tech.is_file():
        tech_text = tech.read_text(encoding="utf-8")
        check("基线版本:v2" in tech_text, "夹具 TECH_DESIGN 应为票 09 产出的 v2")
    task02 = fixtures / "docs" / "mygamestudio" / "work" / "02-tide-timer" / "task.md"
    if task02.is_file():
        text = task02.read_text(encoding="utf-8")
        check(re.search(r"进度(:|：)待验收", text) is not None,
              "夹具 02 进度应为待验收(票 09 终态)")
    result02 = (fixtures / "docs" / "mygamestudio" / "work" / "02-tide-timer"
                / "results" / "2026-09-08.md")
    if result02.is_file():
        text = result02.read_text(encoding="utf-8")
        check("02-tide-timer" in text, "夹具 02 结果记录应引用所属任务身份")
    readme = fixtures / "README.md"
    if readme.is_file():
        text = readme.read_text(encoding="utf-8")
        check("海鸥" in text, "夹具 README 当前请求应指向海鸥视觉资源任务")
        check("06-gull-sprite" in text, "夹具 README 应引用任务身份 06-gull-sprite")
    # 夹具与 09 终态的对应文件一致(取自验收终态未改动)
    arena = REPO_ROOT / ".tmp" / "accept-09" / "projects" / "tide-pool"
    for rel in (
        "docs/mygamestudio/TECH_DESIGN.md",
        "src/main.js",
        "src/index.html",
        "docs/mygamestudio/work/02-tide-timer/task.md",
        "docs/mygamestudio/work/02-tide-timer/results/2026-09-08.md",
    ):
        arena_file = arena / rel
        if arena_file.is_file() and (fixtures / rel).is_file():
            check((fixtures / rel).read_bytes() == arena_file.read_bytes(),
                  f"accept-10 夹具 {rel} 应与票 09 终态逐字节一致")


def test_game_audio_skill_content() -> None:
    """任务票 11:Game-Audio 音频资源工作流的包内依据与关键纪律。"""

    audio = PLUGIN_ROOT / "skills" / "game-audio" / "SKILL.md"
    check(audio.is_file(), "缺少 skills/game-audio/SKILL.md")
    if not audio.is_file():
        return
    text = audio.read_text(encoding="utf-8")
    for ref in (
        "../../internal/contracts/production.md",
        "../../internal/contracts/common.md",
        "../../internal/contracts/records.md",
        "../../internal/protocols/gate-protocol.md",
        "../../internal/methods/writing-for-agents/SKILL.md",
        "../../templates/work/result.md",
    ):
        check(ref in text, f"game-audio SKILL.md 应引用包内依据 {ref}")
    for concept in (
        "声音用途",        # 输入:声音用途(触发时机与接入位置)
        "体验意图",        # 输入:体验意图(情绪与强度边界)
        "参考",            # 输入:参考(设计条目、决定、既有风格与规格)
        "必要格式或时长",  # 输入:采样率/位深/声道/容器/秒数等约定
        "输出位置",        # 输入:输出位置
        "可用能力",        # 输入:可用能力(实际条件决定方法)
        "不固定",          # 不固定生成服务、引擎或音频类型
        "音频类型",        # 音效/音乐/语音等由任务约定
        "mgs_scope",       # 写入前确认有效范围
        "允许修改范围",    # 任务范围核对(以 mgs_scope 为准)
        "缺口",            # 无制作/编辑/验证能力时报告具体缺口
        "可接手材料",      # 缺口时交付可接手材料
        "音频提示词",      # 不把提示词/建议/说明当已完成音频
        "选曲建议",        # 同上
        "文字说明",        # 同上
        "不是已完成音频",  # 明确材料的定位
        "来源或生成依据",  # 输出:合成命令与参数或素材来源
        "接入信息",        # 输出:使用/接入信息
        "播放或接入方式",  # 输出:可定位的播放与接入
        "实际运行",        # 检查必须真实运行并记录输出
        "会话工作区",      # 合成/检查在会话工作区,不直接写项目
        "content_base64",  # 二进制音频经受控通道的载荷形态
        "afplay",          # 本地可播放验证的示例命令
        "ffprobe",         # 规格检查的示例命令
        "待人工试听验收",  # 听感判断不虚构通过
        "真实反馈",        # 听感/风格验收需要实际人工反馈
        "验收待定",        # 未收到反馈时区分制作完成与验收待定
        "制作完成",        # 区分表达的另一侧
        "适配",            # 工具输入输出适配与角色资源策略分离
        "资源策略",        # 分离的另一侧:策略由运行保障承担
        "不被假定",        # 服务或 GUI 不被假定继承本地边界
        "继承本地边界",    # 外部写入通路未验证不视为已受控
        "results/",        # 结果落点
        "进度",            # 任务进度与分流归统筹,直接调用不改
        "不自动",          # 不自动提交、推送、发布
        "受控",            # 新增命令执行路径保持受控
    ):
        check(concept in text, f"game-audio SKILL.md 应覆盖概念:{concept}")


def test_accept11_fixture() -> None:
    """任务票 11:预警决定与音频能力补齐注入夹具——07 收束、GAME_DESIGN/CONFIG
    升 v3、10-warning-sfx 可独立开工,供音频资源任务执行验收使用(四层夹具
    覆盖,不改样例本体)。"""

    fixtures = REPO_ROOT / "acceptance" / "11-audio-asset-delivery" / "fixtures"
    for rel in (
        "README.md",
        "docs/mygamestudio/GAME_DESIGN.md",
        "docs/mygamestudio/CONFIG.md",
        "docs/mygamestudio/records/decision-2026-09-08-warning-audio.md",
        "docs/mygamestudio/work/07-warning-cue/task.md",
        "docs/mygamestudio/work/10-warning-sfx/task.md",
    ):
        check((fixtures / rel).is_file(), f"accept-11 夹具缺少 {rel}")
    design = fixtures / "docs/mygamestudio/GAME_DESIGN.md"
    if design.is_file():
        text = design.read_text(encoding="utf-8")
        check("基线版本:v3" in text, "夹具 GAME_DESIGN 应为预警决定后的 v3")
        check("预警" in text and "音频" in text,
              "夹具 GAME_DESIGN v3 应包含音频预警条目")
        check("decision-2026-09-08-warning-audio.md" in text,
              "夹具 GAME_DESIGN v3 应引用音频预警决定")
    config = fixtures / "docs/mygamestudio/CONFIG.md"
    if config.is_file():
        text = config.read_text(encoding="utf-8")
        check("配置版本:v3" in text, "夹具 CONFIG 应为补齐音频执行条件后的 v3")
        check("ffmpeg" in text and "afplay" in text,
              "夹具 CONFIG v3 应记录本机音频合成/检查/试听能力")
        check(re.search(r"尚未就绪的能力及影响\s*[:：]\s*无", text) is not None,
              "夹具 CONFIG v3 的尚未就绪能力应清空(音频能力已补齐)")
    decision = fixtures / "docs/mygamestudio/records/decision-2026-09-08-warning-audio.md"
    if decision.is_file():
        text = decision.read_text(encoding="utf-8")
        check("已采纳" in text, "夹具音频预警决定应为已采纳状态")
        check("10-warning-sfx" in text, "夹具决定应指向拆出的音频任务")
    task07 = fixtures / "docs/mygamestudio/work/07-warning-cue/task.md"
    if task07.is_file():
        text = task07.read_text(encoding="utf-8")
        check(re.search(r"进度(:|：)已完成", text) is not None,
              "夹具 07 未决项收束后应为已完成")
        check("decision-2026-09-08-warning-audio.md" in text,
              "夹具 07 结果索引应引用决定记录")
    task10 = fixtures / "docs/mygamestudio/work/10-warning-sfx/task.md"
    if task10.is_file():
        text = task10.read_text(encoding="utf-8")
        check("任务身份:10-warning-sfx" in text or "任务身份：10-warning-sfx" in text,
              "夹具 10 身份应为 10-warning-sfx")
        check(re.search(r"进度(:|：)待执行", text) is not None,
              "夹具 10 进度应为待执行(本票执行对象)")
        for field in ("当前目标", "输入与基线", "本次交付", "允许修改范围",
                      "所需能力", "完成标准", "执行责任", "验收方式", "依赖"):
            check(f"- {field}" in text, f"夹具 10 工作请求应含字段 {field}")
        check("WAV" in text and "44100" in text and "单声道" in text,
              "夹具 10 应约定音频规格(容器/采样率/声道)")
        check(re.search(r"0\.3-0\.8", text) is not None,
              "夹具 10 应约定时长区间(0.3-0.8 秒)")
        check("assets/audio/" in text, "夹具 10 输出位置应在 assets/audio/")
        check("ffmpeg" in text, "夹具 10 所需能力应引用本机音频能力")
    readme = fixtures / "README.md"
    if readme.is_file():
        text = readme.read_text(encoding="utf-8")
        check("预警" in text, "夹具 README 当前请求应指向海鸥预警音任务")
        check("10-warning-sfx" in text, "夹具 README 应引用任务身份 10-warning-sfx")
        check("ffmpeg" in text, "夹具 README 应提到本机音频能力确认")
    # 样例本体保持 v1 未动(既有票验收可复现;11 用夹具覆盖)
    sample_design = (REPO_ROOT / "samples" / "tide-pool" / "docs" / "mygamestudio"
                     / "GAME_DESIGN.md")
    if sample_design.is_file():
        check("基线版本:v1" in sample_design.read_text(encoding="utf-8"),
              "samples/tide-pool 本体应保持 v1(11 用夹具覆盖)")


def test_game_build_skill_content() -> None:
    """任务票 12:Game-Build 构建运行工作流的包内依据与关键纪律。"""

    build = PLUGIN_ROOT / "skills" / "game-build" / "SKILL.md"
    check(build.is_file(), "缺少 skills/game-build/SKILL.md")
    if not build.is_file():
        return
    text = build.read_text(encoding="utf-8")
    for ref in (
        "../../internal/contracts/production.md",
        "../../internal/contracts/common.md",
        "../../internal/contracts/records.md",
        "../../internal/protocols/gate-protocol.md",
        "../../internal/methods/writing-for-agents/SKILL.md",
        "../../templates/work/result.md",
    ):
        check(ref in text, f"game-build SKILL.md 应引用包内依据 {ref}")
    for concept in (
        "指定成果或工程版本",  # 输入:构建对象有明确版本
        "构建与运行约定",      # 输入:当前约定(来自项目实际配置)
        "目标格式",            # 输入:输出格式及环境
        "可用环境",            # 输入:可用环境
        "实际配置",            # 构建方式从项目实际配置读取
        "不硬编码",            # 不硬编码某个引擎或发布平台
        "输出格式",            # 明确输出格式及环境
        "实际构建或导出",      # 构建、导出真实发生
        "约定入口",            # 启动约定入口
        "版本对应",            # 产物与源成果版本的对应
        "日志",                # 构建与运行日志
        "运行检查",            # 运行检查结果
        "不把存在文件等同于本次构建成功",  # 旧产物/存在文件不算成功
        "旧产物",              # 同上(缺依赖/入口不可用/只有旧产物如实报告)
        "入口不可用",          # 同上
        "子进程",              # 构建脚本及其子进程在已验证边界内
        "会话工作区",          # 构建脚本放会话工作区,不进项目
        "获准",                # 输出只写获准位置(构建输出区)
        "同步技术设计",        # 约定变化同步技术设计
        "技术依据",            # 必要工程配置变更保留技术依据
        "不自行",              # 不自行上传、签名发布、部署或购买服务
        "上传", "签名", "部署", "购买",  # 外部动作边界
        "准确目标",            # 需要外部动作时列明准确目标
        "缺口",                # 缺依赖/缺能力时报告具体缺口
        "可接手材料",          # 缺口时交付可接手材料
        "mgs_scope",           # 写入前确认有效范围
        "允许修改范围",        # 任务范围核对(以 mgs_scope 为准)
        "expected_sha256",     # 更新走版本校验
        "content_base64",      # 二进制产物载荷
        "实际运行",            # 检查必须真实运行并记录输出
        "待验收",              # 约定审查/试玩未完成保留待验收
        "Review", "Playtest",  # 结果供审查与试玩读取
        "试玩流程",            # 不启动完整试玩流程
        "适配",                # 工具输入输出适配与角色资源策略分离
        "资源策略",            # 分离的另一侧:策略由运行保障承担
        "不被假定",            # 外部构建服务或 GUI 不被假定继承本地边界
        "继承本地边界",        # 外部写入通路未验证不视为已受控
        "results/",            # 结果落点
        "进度",                # 任务进度与分流归统筹,直接调用不改
        "不自动",              # 不自动提交、推送、发布
        "受控",                # 新增命令执行路径保持受控
        "mgs_records",         # 统一接口
    ):
        check(concept in text, f"game-build SKILL.md 应覆盖概念:{concept}")


def test_accept12_fixture() -> None:
    """任务票 12:构建约定与可玩成果任务注入夹具——TECH_DESIGN v3 构建与导出
    约定、CONFIG v4 构建运行能力、11-playable-build 可独立开工,供构建运行
    任务执行验收使用(五层夹具覆盖,不改样例本体)。"""

    fixtures = REPO_ROOT / "acceptance" / "12-build-and-run-delivery" / "fixtures"
    for rel in (
        "README.md",
        "docs/mygamestudio/TECH_DESIGN.md",
        "docs/mygamestudio/CONFIG.md",
        "docs/mygamestudio/work/11-playable-build/task.md",
        "docs/mygamestudio/work/10-warning-sfx/task.md",
        "docs/mygamestudio/work/10-warning-sfx/results/2026-09-08.md",
        "assets/audio/gull_warning_rise.wav",
    ):
        check((fixtures / rel).is_file(), f"accept-12 夹具缺少 {rel}")
    task10 = fixtures / "docs" / "mygamestudio" / "work" / "10-warning-sfx" / "task.md"
    if task10.is_file():
        text = task10.read_text(encoding="utf-8")
        check(re.search(r"进度(:|：)待验收", text) is not None,
              "夹具 10 进度应为待验收(票 11 终态承接,退出可开工集合)")
    tech = fixtures / "docs" / "mygamestudio" / "TECH_DESIGN.md"
    if tech.is_file():
        text = tech.read_text(encoding="utf-8")
        check("基线版本:v3" in text, "夹具 TECH_DESIGN 应为构建约定轮的 v3")
        check("构建与导出" in text, "夹具 TECH_DESIGN v3 应含构建与导出约定")
        check("build/" in text and "build/index.html" in text,
              "夹具 TECH_DESIGN v3 应约定构建产物区 build/ 与入口 build/index.html")
        check("字节一致" in text,
              "夹具 TECH_DESIGN v3 应约定组装式导出为字节一致副本")
        check("不引入" in text and "工具链" in text,
              "夹具 TECH_DESIGN v3 应声明不为构建引入新工具链")
        check("SHA-256" in text, "夹具 TECH_DESIGN v3 应约定版本对应留底(SHA-256)")
        check("无头冒烟" in text and "node" in text,
              "夹具 TECH_DESIGN v3 应约定无头冒烟检查方式")
        check("http.server" in text or "静态服务" in text,
              "夹具 TECH_DESIGN v3 应约定静态服务取回检查方式")
        check("未被引用" in text and "assets" in text,
              "夹具 TECH_DESIGN v3 应约定未被引用的 assets 源文件不进产物")
    config = fixtures / "docs" / "mygamestudio" / "CONFIG.md"
    if config.is_file():
        text = config.read_text(encoding="utf-8")
        check("配置版本:v4" in text, "夹具 CONFIG 应为补齐构建运行能力后的 v4")
        check("node" in text and "http.server" in text,
              "夹具 CONFIG v4 应记录本机构建运行能力(node 冒烟、python3 静态服务)")
        check("build/" in text, "夹具 CONFIG v4 应把构建产物区 build/ 纳入执行条件")
        check(re.search(r"尚未就绪的能力及影响\s*[:：]\s*无", text) is not None,
              "夹具 CONFIG v4 的尚未就绪能力应清空(构建运行能力已补齐)")
    task11 = fixtures / "docs" / "mygamestudio" / "work" / "11-playable-build" / "task.md"
    if task11.is_file():
        text = task11.read_text(encoding="utf-8")
        check("任务身份:11-playable-build" in text or "任务身份：11-playable-build" in text,
              "夹具任务身份应为 11-playable-build")
        check(re.search(r"进度(:|：)待执行", text) is not None,
              "夹具任务进度应为待执行(本票执行对象)")
        for field in ("当前目标", "输入与基线", "本次交付", "允许修改范围",
                      "所需能力", "完成标准", "执行责任", "验收方式", "依赖"):
            check(f"- {field}" in text, f"夹具任务工作请求应含字段 {field}")
        check("依赖:无" in text or "依赖：无" in text,
              "夹具任务应无依赖(当前状态可独立构建,可开工)")
        check("TECH_DESIGN v3" in text,
              "夹具任务应引用 TECH_DESIGN v3(构建与导出约定,当前版本)")
        check("GAME_DESIGN v3" in text,
              "夹具任务应引用 GAME_DESIGN v3(当前版本,避免基线漂移)")
        check("build/" in text and "build/index.html" in text,
              "夹具任务输出位置应在 build/(入口 build/index.html)")
        check("SHA-256" in text or "哈希" in text,
              "夹具任务应要求产物与源文件的版本对应留底")
        check("冒烟" in text, "夹具任务应要求无头冒烟运行检查")
        check("src/" in text and "不修改" in text,
              "夹具任务允许修改范围应排除 src/(构建不改源)")
    readme = fixtures / "README.md"
    if readme.is_file():
        text = readme.read_text(encoding="utf-8")
        check("构建" in text or "打包" in text or "导出" in text,
              "夹具 README 当前请求应指向可玩成果构建")
        check("11-playable-build" in text, "夹具 README 应引用任务身份 11-playable-build")
        check("ready" in text, "夹具 README 应说明选任务以统一接口 ready 输出为准")
    # 承接票 11 终态的文件与验收终态逐字节一致(取自 .tmp/accept-11 未改动)
    arena = REPO_ROOT / ".tmp" / "accept-11" / "projects" / "tide-pool"
    for rel in (
        "docs/mygamestudio/work/10-warning-sfx/task.md",
        "docs/mygamestudio/work/10-warning-sfx/results/2026-09-08.md",
        "assets/audio/gull_warning_rise.wav",
    ):
        arena_file = arena / rel
        if arena_file.is_file() and (fixtures / rel).is_file():
            check((fixtures / rel).read_bytes() == arena_file.read_bytes(),
                  f"accept-12 夹具 {rel} 应与票 11 终态逐字节一致")
    # 样例本体保持 v1 未动(既有票验收可复现;12 用夹具覆盖)
    sample_design = (REPO_ROOT / "samples" / "tide-pool" / "docs" / "mygamestudio"
                     / "GAME_DESIGN.md")
    if sample_design.is_file():
        check("基线版本:v1" in sample_design.read_text(encoding="utf-8"),
              "samples/tide-pool 本体应保持 v1(12 用夹具覆盖)")


def test_game_review_skill_content() -> None:
    """任务票 13:Game-Review 独立审查工作流的包内依据与关键纪律。"""

    review = PLUGIN_ROOT / "skills" / "game-review" / "SKILL.md"
    check(review.is_file(), "缺少 skills/game-review/SKILL.md")
    if not review.is_file():
        return
    text = review.read_text(encoding="utf-8")
    for ref in (
        "../../internal/contracts/verification.md",
        "../../internal/contracts/common.md",
        "../../internal/contracts/records.md",
        "../../internal/protocols/gate-protocol.md",
        "../../internal/methods/writing-for-agents/SKILL.md",
        "../../templates/evidence/review.md",
    ):
        check(ref in text, f"game-review SKILL.md 应引用包内依据 {ref}")
    for concept in (
        "明确的待审成果和版本",  # 输入:待审对象必须明确
        "当前要求与规范",        # 输入:规范与规格
        "需要检查的范围",        # 输入:范围
        "独立",                  # 独立于原执行上下文
        "同专业",                # 按被审对象选择独立同专业执行实例
        "不新增常设评审角色",     # 审查不增设常设角色
        "作者总结",              # 不仅依赖作者总结
        "直接读取",              # 直接读取规范、实际成果、规格与证据
        "Standards", "Spec",     # 代码两轴
        "两轴",                  # 两轴独立执行、分别呈现
        "分别",                  # 分别呈现(不合并结论)
        "待审版本",              # 固定待审版本
        "文件清单",              # 完整范围用文件清单固定
        "SHA-256",               # 版本指纹登记
        "已提交", "暂存", "未暂存", "新建",  # 四类成果范围完整性
        "HEAD",                  # 不以 HEAD/暂存区对比替代实际文件读取
        "证据",                  # 每项问题关联具体证据
        "影响",                  # 每项问题关联影响
        "明确规则违背",          # 问题分类一
        "专业判断",              # 问题分类二
        "未能检查",              # 问题分类三
        "不修改",                # 审查实例不修改待审专业成果
        "修复",                  # 修复由对应制作或设计任务执行
        "复核",                  # 修复后针对实际新版本复核
        "新版本",                # 旧结论不挪作新版本通过证明
        "不挪用",                # 同上
        "覆盖限制",              # 未实现的运行能力标为覆盖限制
        "不代验收",              # 报告生成不等于验收通过
        "待验收",                # 审查后仍区分待人工验收
        "evidence/",             # 审查记录与证据落点
        "mgs_scope",             # 写入前确认有效范围
        "mgs_write",             # 审查记录经受控通道写入
        "实际运行",              # 能自动核验的检查实际运行
        "审查记录",              # 写入仅限审查记录与证据
        "mgs_records",           # 统一接口(读任务与规格引用)
    ):
        check(concept in text, f"game-review SKILL.md 应覆盖概念:{concept}")


def test_accept13_fixture() -> None:
    """任务票 13:独立审查验收夹具——承接票 10/12 真实交付物(06 海鸥 SVG
    与结果、11 构建产物与待验收记录),使待验收成果完整可审,不改样例本体。"""

    fixtures = REPO_ROOT / "acceptance" / "13-independent-deliverable-review" / "fixtures"
    for rel in (
        "README.md",
        "assets/gull-glide.svg",
        "assets/gull-dive.svg",
        "docs/mygamestudio/work/06-gull-sprite/task.md",
        "docs/mygamestudio/work/06-gull-sprite/results/2026-09-08.md",
        "docs/mygamestudio/work/11-playable-build/task.md",
        "docs/mygamestudio/work/11-playable-build/results/2026-09-08.md",
        "build/index.html",
        "build/main.js",
    ):
        check((fixtures / rel).is_file(), f"accept-13 夹具缺少 {rel}")
    # 06/11 任务记录为待验收态(审查对象,非开工对象)
    for task_id in ("06-gull-sprite", "11-playable-build"):
        task_md = (fixtures / "docs" / "mygamestudio" / "work" / task_id / "task.md")
        if task_md.is_file():
            text = task_md.read_text(encoding="utf-8")
            check(re.search(r"进度(:|：)待验收", text) is not None,
                  f"夹具 {task_id} 进度应为待验收(本票审查对象)")
    # 06 结果记录中登记的 SVG 哈希与实际文件一致(审查输入的版本指纹可信)
    results06 = (fixtures / "docs" / "mygamestudio" / "work" / "06-gull-sprite"
                 / "results" / "2026-09-08.md")
    if results06.is_file():
        text = results06.read_text(encoding="utf-8")
        for svg in ("gull-glide.svg", "gull-dive.svg"):
            svg_path = fixtures / "assets" / svg
            if svg_path.is_file():
                check(sha256(svg_path) in text,
                      f"夹具 06 结果记录应含 {svg} 的实际 SHA-256")
        check("独立审查" in text, "夹具 06 结果记录应声明独立审查尚未进行")
    # 11 结果记录登记的产物哈希与实际 build 文件一致
    results11 = (fixtures / "docs" / "mygamestudio" / "work" / "11-playable-build"
                 / "results" / "2026-09-08.md")
    if results11.is_file():
        text = results11.read_text(encoding="utf-8")
        for prod in ("index.html", "main.js"):
            prod_path = fixtures / "build" / prod
            if prod_path.is_file():
                check(sha256(prod_path) in text,
                      f"夹具 11 结果记录应含 build/{prod} 的实际 SHA-256")
    # 组装式导出=字节一致:build 产物应与持久夹具(票 09 交付后的 src)逐字节一致
    src_fixture = REPO_ROOT / "acceptance" / "10-visual-asset-delivery" / "fixtures" / "src"
    for prod in ("index.html", "main.js"):
        build_file = fixtures / "build" / prod
        src_file = src_fixture / prod
        if build_file.is_file() and src_file.is_file():
            check(build_file.read_bytes() == src_file.read_bytes(),
                  f"夹具 build/{prod} 应与票 10 夹具 src/{prod} 逐字节一致"
                  "(组装式导出,票 12 终态承接)")
    # 承接票 10/12 验收终态的文件与 .tmp 终态逐字节一致(本机有 .tmp 时核对)
    for arena_rel, rel in (
        (".tmp/accept-10/projects/tide-pool/assets/gull-glide.svg", "assets/gull-glide.svg"),
        (".tmp/accept-10/projects/tide-pool/assets/gull-dive.svg", "assets/gull-dive.svg"),
        (".tmp/accept-10/projects/tide-pool/docs/mygamestudio/work/06-gull-sprite/task.md",
         "docs/mygamestudio/work/06-gull-sprite/task.md"),
        (".tmp/accept-10/projects/tide-pool/docs/mygamestudio/work/06-gull-sprite/results/2026-09-08.md",
         "docs/mygamestudio/work/06-gull-sprite/results/2026-09-08.md"),
        (".tmp/accept-12/projects/tide-pool/docs/mygamestudio/work/11-playable-build/task.md",
         "docs/mygamestudio/work/11-playable-build/task.md"),
        (".tmp/accept-12/projects/tide-pool/docs/mygamestudio/work/11-playable-build/results/2026-09-08.md",
         "docs/mygamestudio/work/11-playable-build/results/2026-09-08.md"),
        (".tmp/accept-12/projects/tide-pool/build/index.html", "build/index.html"),
        (".tmp/accept-12/projects/tide-pool/build/main.js", "build/main.js"),
    ):
        arena_file = REPO_ROOT / arena_rel
        if arena_file.is_file() and (fixtures / rel).is_file():
            check((fixtures / rel).read_bytes() == arena_file.read_bytes(),
                  f"accept-13 夹具 {rel} 应与验收终态逐字节一致")
    readme = fixtures / "README.md"
    if readme.is_file():
        text = readme.read_text(encoding="utf-8")
        check("审查" in text, "夹具 README 当前请求应指向独立审查")
        check("待验收" in text, "夹具 README 应说明审查对象为待验收成果")
        for task_id in ("02-tide-timer", "06-gull-sprite", "10-warning-sfx",
                        "11-playable-build"):
            check(task_id in text, f"夹具 README 应引用待审任务 {task_id}")
    # 样例本体保持 v1 未动(既有票验收可复现;13 用夹具覆盖)
    sample_design = (REPO_ROOT / "samples" / "tide-pool" / "docs" / "mygamestudio"
                     / "GAME_DESIGN.md")
    if sample_design.is_file():
        check("基线版本:v1" in sample_design.read_text(encoding="utf-8"),
              "samples/tide-pool 本体应保持 v1(13 用夹具覆盖)")


def test_game_playtest_skill_content() -> None:
    """任务票 14:Game-Playtest 试玩工作流的包内依据与关键纪律。"""

    playtest = PLUGIN_ROOT / "skills" / "game-playtest" / "SKILL.md"
    check(playtest.is_file(), "缺少 skills/game-playtest/SKILL.md")
    if not playtest.is_file():
        return
    text = playtest.read_text(encoding="utf-8")
    for ref in (
        "../../internal/contracts/verification.md",
        "../../internal/contracts/common.md",
        "../../internal/contracts/records.md",
        "../../internal/protocols/gate-protocol.md",
        "../../internal/methods/writing-for-agents/SKILL.md",
        "../../templates/evidence/playtest.md",
    ):
        check(ref in text, f"game-playtest SKILL.md 应引用包内依据 {ref}")
    for concept in (
        "明确的版本与入口",  # 输入:版本与入口必须明确
        "场景",              # 输入:要检查的场景或问题
        "适用要求",          # 输入:适用要求
        "可用控制",          # 输入:可用控制工具
        "人工参与约定",      # 输入:人工参与约定
        "制定",              # 制定必要场景
        "实际执行",          # 实际执行可用的检查
        "输入", "观察",      # 记录输入与观察
        "证据",              # 逐项记录证据
        "试玩任务",          # 需要人时给出明确试玩任务
        "回传要求",          # 反馈的回传要求
        "实际反馈",          # 人工结论来自实际反馈
        "来源",              # 实际反馈保留来源
        "未反馈",            # 三态表达一
        "明确通过",          # 三态表达二
        "需要修改",          # 三态表达三
        "SHA-256",           # 结果绑定实际测试版本(指纹)
        "缺陷",              # 发现缺陷时输出交接
        "交接",              # 交接返回执行流程
        "不改产品基线",      # 不改产品基线来迁就观察结果
        "尚未执行",          # 仅写了计划的部分明确尚未执行
        "计划",              # 仅制定计划的工作明确标为计划
        "运行状态",          # 运行状态和测试输出受本次用途限制
        "测试输出",          # 同上
        "GUI",               # 新增 GUI 通路不被假定继承本地边界
        "MCP",               # 新增 MCP 通路同理
        "未就绪",            # 未覆盖能力保持未就绪
        "覆盖限制",          # 如实标注覆盖限制
        "evidence/",         # 试玩记录与证据落点
        "mgs_scope",         # 写入前确认有效范围
        "mgs_write",         # 试玩记录经受控通道写入
        "复测",              # 新修改/失败/疑点触发复测
        "不代验收",          # 试玩记录不等于验收通过
        "待验收",            # 人工项保持待验收
        "统筹",              # 进度与分流归统筹
        "mgs_records",       # 统一接口(读任务与约定)
    ):
        check(concept in text, f"game-playtest SKILL.md 应覆盖概念:{concept}")


def test_accept14_fixture() -> None:
    """任务票 14:试玩验收夹具——承接票 13 终态(evidence/ 5 份审查记录、02 修复
    说明、tide-extra.js 处置残留),叠加开发者试玩请求;不改样例本体。"""

    fixtures = REPO_ROOT / "acceptance" / "14-playtest-and-human-feedback" / "fixtures"
    for rel in (
        "README.md",
        "src/tide-extra.js",
        "docs/mygamestudio/work/02-tide-timer/results/2026-09-08-fix.md",
        "docs/mygamestudio/evidence/2026-09-08-review-02-tide-timer.md",
        "docs/mygamestudio/evidence/2026-09-08-review-06-gull-sprite.md",
        "docs/mygamestudio/evidence/2026-09-08-review-10-warning-sfx.md",
        "docs/mygamestudio/evidence/2026-09-08-review-11-playable-build.md",
        "docs/mygamestudio/evidence/2026-09-08-recheck-02-tide-timer.md",
    ):
        check((fixtures / rel).is_file(), f"accept-14 夹具缺少 {rel}")
    readme = fixtures / "README.md"
    if readme.is_file():
        text = readme.read_text(encoding="utf-8")
        check("试玩" in text, "夹具 README 当前请求应指向试玩")
        check("11-playable-build" in text, "夹具 README 应引用试玩对象 11-playable-build")
        check("build/index.html" in text, "夹具 README 应给出运行入口 build/index.html")
        check("人工" in text, "夹具 README 应说明人工体验判断的参与约定")
        check("未收到" in text or "尚未收到" in text,
              "夹具 README 应声明当前未收到任何真实人工反馈")
        check("08-gull-playtest" in text,
              "夹具 README 应引用等待真实人工反馈的 08-gull-playtest")
    # 承接票 13 终态的文件与 .tmp 终态逐字节一致(本机有 .tmp 时核对)
    a13 = ".tmp/accept-13/projects/tide-pool"
    for rel in (
        "src/tide-extra.js",
        "docs/mygamestudio/work/02-tide-timer/results/2026-09-08-fix.md",
        "docs/mygamestudio/evidence/2026-09-08-review-02-tide-timer.md",
        "docs/mygamestudio/evidence/2026-09-08-review-06-gull-sprite.md",
        "docs/mygamestudio/evidence/2026-09-08-review-10-warning-sfx.md",
        "docs/mygamestudio/evidence/2026-09-08-review-11-playable-build.md",
        "docs/mygamestudio/evidence/2026-09-08-recheck-02-tide-timer.md",
    ):
        arena_file = REPO_ROOT / a13 / rel
        if arena_file.is_file() and (fixtures / rel).is_file():
            check((fixtures / rel).read_bytes() == arena_file.read_bytes(),
                  f"accept-14 夹具 {rel} 应与票 13 终态逐字节一致")
    # tide-extra.js 为票 13 的处置残留(解除引用且无副作用化),不再被入口引用
    entry = REPO_ROOT / "acceptance" / "10-visual-asset-delivery" / "fixtures" / "src" / "index.html"
    residue = fixtures / "src" / "tide-extra.js"
    if entry.is_file() and residue.is_file():
        check("tide-extra" not in entry.read_text(encoding="utf-8"),
              "入口 index.html 不应引用 tide-extra.js(票 13 修复后的状态)")
        check("已停用" in residue.read_text(encoding="utf-8"),
              "tide-extra.js 应为票 13 处置后的无副作用残留")
    # 样例本体保持 v1 未动(既有票验收可复现;14 用夹具覆盖)
    sample_design = (REPO_ROOT / "samples" / "tide-pool" / "docs" / "mygamestudio"
                     / "GAME_DESIGN.md")
    if sample_design.is_file():
        check("基线版本:v1" in sample_design.read_text(encoding="utf-8"),
              "samples/tide-pool 本体应保持 v1(14 用夹具覆盖)")


def test_goal_change_skills_content() -> None:
    """任务票 15:目标变化/并发/中断恢复纪律在 producer/spec/status 的覆盖。"""

    producer = PLUGIN_ROOT / "skills" / "game-producer" / "SKILL.md"
    check(producer.is_file(), "缺少 skills/game-producer/SKILL.md")
    if producer.is_file():
        text = producer.read_text(encoding="utf-8")
        for concept in (
            "目标或范围变化",      # 影响检查触发条件
            "影响检查",            # 先组织影响检查
            "受影响基线",          # 识别受影响基线
            "受影响任务",          # 识别受影响任务
            "重新分流",            # 受影响任务进入重新分流
            "完成事实",            # 原版本下完成事实保留
            "不自动算作满足新目标",  # 完成事实不自动算作满足新目标
            "基线采纳",            # 基线采纳归设计侧,统筹只识别与安排
            "baseline",            # 统一接口内容指纹核对
            "疑似格式修正",        # 格式修正分类
            "不作废",              # 格式修正不作废成果与证据
            "实质变更",            # 实质变更分类
            "不自行修改该基线",    # 统筹不代设计修改基线
            "交回开发者",          # 未确认变更交回开发者
            "一个有效写入者",      # 单写入者
            "集成责任",            # 独立资源并行时集成责任明确
            "occupancy",           # 占用冲突处理
            "version",             # 版本核对冲突处理
            "不覆盖他人",          # 不覆盖他人已完成成果
            "别名",                # 别名不能绕过占用
            "中断恢复",            # 中断恢复纪律
            "实际内容为准",        # 以实际文件内容为准
            "用户修改",            # 用户后续修改保留
            "只继续仍适用",        # 只继续仍适用的剩余工作
            "不回滚",              # 不回滚用户修改
            "mgs_records",         # 统一接口回读
        ):
            check(concept in text, f"game-producer SKILL.md 应覆盖概念:{concept}")

    spec = PLUGIN_ROOT / "skills" / "game-spec" / "SKILL.md"
    if spec.is_file():
        text = spec.read_text(encoding="utf-8")
        for concept in (
            "内容指纹",    # 双指纹之一
            "归一指纹",    # 双指纹之二
            "64 个",       # 登记方法(先写 0 再回填)
            "格式修正",    # 格式修正不触发新版本
            "同步更新",    # 格式修正同步更新指纹
            "baseline",    # 登记后经统一接口回读确认
            "一致",        # 回读确认状态为一致
        ):
            check(concept in text, f"game-spec SKILL.md 应覆盖概念:{concept}")

    status_ref = PLUGIN_ROOT / "skills" / "game-status" / "references" / "status-check.md"
    if status_ref.is_file():
        text = status_ref.read_text(encoding="utf-8")
        for concept in (
            "内容指纹",          # 状态检查核对内容指纹
            "baseline",          # 经统一接口核对
            "疑似格式修正",      # 格式修正不影响既有结论
            "实质变更",          # 实质变更列入依据过时
            "不自行改判",        # 不自行改判成果与证据有效性
        ):
            check(concept in text, f"status-check.md 应覆盖概念:{concept}")


def test_accept15_fixture() -> None:
    """任务票 15:目标变化/并发/中断恢复验收夹具——在票 14 布景之上叠加
    开发者目标变化请求;承接的漂移事实在夹具栈中真实存在;不改样例本体。"""

    fixtures = REPO_ROOT / "acceptance" / "15-goal-change-concurrency-recovery" / "fixtures"
    check((fixtures / "README.md").is_file(), "accept-15 夹具缺少 README.md")
    readme = fixtures / "README.md"
    if readme.is_file():
        text = readme.read_text(encoding="utf-8")
        check("目标变化" in text or "目标或范围变化" in text,
              "夹具 README 当前请求应为开发者目标变化请求")
        check("45" in text, "夹具 README 应给出具体变化(回合时长 45 秒)")
        check("追回" in text, "夹具 README 应触及追回窗口(可调参数化)")
    # 布景承接的漂移事实:14 层夹具的 04/05 仍引用 GAME_DESIGN v2(当前 v3)
    task05 = (REPO_ROOT / "acceptance" / "08-spec-to-local-tasks" / "fixtures"
              / "docs" / "mygamestudio" / "work" / "05-gull-swoop" / "task.md")
    if task05.is_file():
        check("GAME_DESIGN v2" in task05.read_text(encoding="utf-8"),
              "承接布景应保留 04/05 引用旧版本的真实漂移(票 09-14 遗留)")
    design14 = (REPO_ROOT / "acceptance" / "11-audio-asset-delivery" / "fixtures"
                / "docs" / "mygamestudio" / "GAME_DESIGN.md")
    if design14.is_file():
        check("基线版本:v3" in design14.read_text(encoding="utf-8"),
              "承接布景的 GAME_DESIGN 当前应为 v3(票 11 后)")
    # 样例本体保持 v1 未动
    sample_design = (REPO_ROOT / "samples" / "tide-pool" / "docs" / "mygamestudio"
                     / "GAME_DESIGN.md")
    if sample_design.is_file():
        check("基线版本:v1" in sample_design.read_text(encoding="utf-8"),
              "samples/tide-pool 本体应保持 v1(15 用夹具覆盖)")


def test_producer_loop_skills_content() -> None:
    """任务票 16:制作统筹完整闭环纪律——入口分类、按需委派与完成判定。"""

    producer = PLUGIN_ROOT / "skills" / "game-producer" / "SKILL.md"
    check(producer.is_file(), "缺少 skills/game-producer/SKILL.md")
    if producer.is_file():
        text = producer.read_text(encoding="utf-8")
        for concept in (
            "仅讨论",            # 入口一:仅讨论
            "已有规格",          # 入口二:已有规格制作
            "直接调用",          # 入口三:直接专业调用后的状态同步
            "直接专业调用",      # 入口三全称(与上一条至少其一,全要求)
            "状态同步",          # 直接调用结果在下次介入时同步
            "下次介入",          # 同步时点:统筹下次显式介入
            "按事实核对",        # 同步依据实际成果而非作者自述
            "合适环节",          # 按已有资料从合适环节开始
            "中间进入",          # 输入充足时从中间环节进入
            "跳过原型",          # 无需原型的工作跳过原型
            "不强制",            # 不强制每轮执行全部技能
            "全部技能",          # 同上(完整短语「不强制…全部技能」)
            "隔离",              # 设计原型保持隔离
            "Game-Implement",    # 本次制作由 Game-Implement 组织
            "委派",              # 统筹按需明确委派业务入口
            "独立审查",          # 审查完成是验收事实之一
            "约定检查",          # 约定检查完成且无需人判断可标记完成
            "无需人判断",        # 可标记完成的条件
            "待验收",            # 需要人的验收保持待验收
            "作者自报",          # 作者自报不能代替验收
            "旧版本",            # 旧版本结果不能代替当前验收
            "短规格",            # 较小任务可用短规格
            "单项工作",          # 单项工作完成闭环
            "粗粒度",            # 未来目标保持粗粒度
            "阶段门槛",          # 不引入固定阶段门槛
        ):
            check(concept in text, f"game-producer SKILL.md 应覆盖概念:{concept}")


def test_accept16_fixture() -> None:
    """任务票 16:制作统筹完整闭环验收夹具——承接票 15 终态(逐字节)+ 开发者
    闭环请求;漂移、待同步与待人工事实在夹具栈中真实存在;不改样例本体。"""

    fixtures = REPO_ROOT / "acceptance" / "16-producer-complete-loop" / "fixtures"
    check((fixtures / "README.md").is_file(), "accept-16 夹具缺少 README.md")
    readme = fixtures / "README.md"
    if readme.is_file():
        text = readme.read_text(encoding="utf-8")
        check("闭环" in text, "夹具 README 当前请求应为完整小步闭环请求")
        check("50 秒" in text, "夹具 README 应包含开发者对 50 秒回会的确认决定")
        check("直接调用" in text or "直接专业调用" in text,
              "夹具 README 应声明直接专业调用(Game-Prototype)的事实")
        check("urgent-window" in text,
              "夹具 README 应引用直接调用的原型 urgent-window")
        check("讨论" in text, "夹具 README 应包含仅讨论请求(不进入制作)")
        check("PT-01" in text, "夹具 README 应引用 PT-01 缺陷修复交接")
        check("短规格" in text or "单项" in text,
              "夹具 README 应说明本轮以短规格/单项工作收口")
    # 承接票 15 终态的关键文件必须存在
    for rel in (
        "docs/mygamestudio/PROJECT.md",
        "docs/mygamestudio/GAME_DESIGN.md",
        "docs/mygamestudio/records/decision-2026-09-08-round-45s.md",
        "docs/mygamestudio/work/12-game-design-v4/task.md",
        "docs/mygamestudio/work/15-race-demo/results/race.md",
        "docs/mygamestudio/work/02-tide-timer/task.md",
        "docs/mygamestudio/work/04-shell-combo/task.md",
        "docs/mygamestudio/work/05-gull-swoop/task.md",
        "docs/mygamestudio/work/06-gull-sprite/task.md",
        "docs/mygamestudio/work/08-gull-playtest/task.md",
        "docs/mygamestudio/work/10-warning-sfx/task.md",
        "docs/mygamestudio/work/11-playable-build/task.md",
    ):
        check((fixtures / rel).is_file(), f"accept-16 夹具缺少承接票 15 终态的 {rel}")
    # 承接事实的结构核对
    design = fixtures / "docs" / "mygamestudio" / "GAME_DESIGN.md"
    if design.is_file():
        text = design.read_text(encoding="utf-8")
        check("基线版本:v4" in text,
              "承接布景的 GAME_DESIGN 应为 v4(50 秒手工变更未同步版本号)")
        check("50 秒" in text, "承接布景的 GAME_DESIGN 应含开发者手工 50 秒变更")
    task04 = fixtures / "docs" / "mygamestudio" / "work" / "04-shell-combo" / "task.md"
    if task04.is_file():
        check("needs-triage" in task04.read_text(encoding="utf-8"),
              "承接布景的 04/05/08 应保持 needs-triage(待重核)")
    task12 = fixtures / "docs" / "mygamestudio" / "work" / "12-game-design-v4" / "task.md"
    if task12.is_file():
        text = task12.read_text(encoding="utf-8")
        check("待执行" in text,
              "承接布景的 12-game-design-v4 应为待执行(v4 已采纳但记录待统筹同步)")
    task02 = fixtures / "docs" / "mygamestudio" / "work" / "02-tide-timer" / "task.md"
    if task02.is_file():
        text = task02.read_text(encoding="utf-8")
        check("待验收" in text, "承接布景的 02 应保持待验收")
        check("evidence/" in text, "承接布景的 02 结果索引应已登记 evidence(票 15)")
        check("开发者注" in text or "开发者" in text,
              "承接布景的 02 应保留票 15 的开发者注(恢复不覆盖用户修改)")
    # 承接票 15 终态的文件与 .tmp 终态逐字节一致(本机有 .tmp 时核对)
    a15 = ".tmp/accept-15/projects/tide-pool"
    for rel in (
        "docs/mygamestudio/PROJECT.md",
        "docs/mygamestudio/GAME_DESIGN.md",
        "docs/mygamestudio/records/decision-2026-09-08-round-45s.md",
        "docs/mygamestudio/work/12-game-design-v4/task.md",
        "docs/mygamestudio/work/15-race-demo/results/race.md",
        "docs/mygamestudio/work/02-tide-timer/task.md",
        "docs/mygamestudio/work/04-shell-combo/task.md",
        "docs/mygamestudio/work/05-gull-swoop/task.md",
        "docs/mygamestudio/work/06-gull-sprite/task.md",
        "docs/mygamestudio/work/08-gull-playtest/task.md",
        "docs/mygamestudio/work/10-warning-sfx/task.md",
        "docs/mygamestudio/work/11-playable-build/task.md",
    ):
        arena_file = REPO_ROOT / a15 / rel
        if arena_file.is_file() and (fixtures / rel).is_file():
            check((fixtures / rel).read_bytes() == arena_file.read_bytes(),
                  f"accept-16 夹具 {rel} 应与票 15 终态逐字节一致")
    # 样例本体保持 v1 未动
    sample_design = (REPO_ROOT / "samples" / "tide-pool" / "docs" / "mygamestudio"
                     / "GAME_DESIGN.md")
    if sample_design.is_file():
        check("基线版本:v1" in sample_design.read_text(encoding="utf-8"),
              "samples/tide-pool 本体应保持 v1(16 用夹具覆盖)")


def test_github_issue_workflow_content() -> None:
    """任务票 17:GitHub Issues 任务后端的包内组件与关键纪律。"""

    module = PLUGIN_ROOT / "records" / "mgs_github.py"
    check(module.is_file(), "缺少 records/mgs_github.py(GitHub Issues 后端适配器)")
    if module.is_file():
        text = module.read_text(encoding="utf-8")
        for seam in ("def parse_repo_location", "def parse_remote_authorizations",
                     "class GithubBackend", "def create_task", "def update_task",
                     "def set_triage", "def append_result", "def set_relations",
                     "def set_parent", "def close_task", "def publish_drafts",
                     "def plan_backend_switch", "def apply_backend_switch",
                     "def handover_baseline_check"):
            check(seam in text, f"records/mgs_github.py 缺少公开接缝 {seam}")
        for concept in ("issues-write", "不等于批准远端写入", "不静默切换本地后端",
                        "未发布草稿", "避免重复创建", "关闭 Issue 不自动等于验证通过"):
            check(concept in text, f"mgs_github.py 应覆盖概念:{concept}")
    skill_md = PLUGIN_ROOT / "skills" / "game-init" / "SKILL.md"
    if skill_md.is_file():
        text = skill_md.read_text(encoding="utf-8")
        for concept in ("host/owner/repository",       # 明确坐标(任务票 17 AC1)
                        "标签映射",                     # 五类标签映射
                        "不把设计文档复制进每个 Issue",   # 核心设计留本地 Markdown
                        "不自动授权远端写入",           # 选择后端不等于授权(AC4)
                        "issues-write",                 # 授权记录形态
                        "mgs_remote",                   # 会话内受控远端通道
                        "不直连",                       # 不直连远端
                        "先回读再重试",                 # 超时回读(AC5)
                        "未发布草稿",                   # 草稿标注
                        "不静默改用本地后端",           # 不静默切后端
                        "switch-plan",                  # 迁移清单(AC6)
                        "handover",                     # 交接基线可达
                        "不可访问"):                    # 未发布资料不宣称可达
            check(concept in text, f"game-init SKILL.md 应覆盖概念:{concept}")
    protocol = PLUGIN_ROOT / "internal" / "protocols" / "gate-protocol.md"
    if protocol.is_file():
        text = protocol.read_text(encoding="utf-8")
        for concept in ("mgs_remote", "remote_scope", "remote_upstream",
                        "不等于批准远端写入", "未发布草稿", "expected_body_sha256"):
            check(concept in text, f"gate-protocol.md 应覆盖概念:{concept}")
    admin = PLUGIN_ROOT / "runtime" / "mgsrt_admin.py"
    if admin.is_file():
        text = admin.read_text(encoding="utf-8")
        check("set-remote-config" in text and "token_env" in text,
              "mgsrt_admin 应提供 set-remote-config(凭据只登记环境变量名)")
    manifest_path = PLUGIN_ROOT / ".codex-plugin" / "plugin.json"
    manifest = json.loads(manifest_path.read_text())
    check(manifest.get("version") == "0.18.0", "任务票 18 后包版本应为 0.18.0")
    check("github-issues-backend" in manifest.get("keywords", []),
          "plugin.json keywords 应含 github-issues-backend")


def test_provenance_version_consistency() -> None:
    """任务票 18:包版本、provenance 标题与 fingerprints 的 generated_for 三处一致。

    0.17.0 曾留下 generated_for=0.16.0 的陈旧值(本票发现并修复);本测试防止再次漂移。
    """

    manifest = json.loads((PLUGIN_ROOT / ".codex-plugin" / "plugin.json").read_text())
    version = manifest.get("version", "")
    head = (PLUGIN_ROOT / "provenance" / "manifest.md").read_text().splitlines()[0]
    match = re.search(r"mygamestudio (\d+\.\d+\.\d+)", head)
    check(match is not None, f"provenance/manifest.md 标题应含版本号,实际:{head}")
    if match:
        check(match.group(1) == version,
              f"manifest.md 标题版本 {match.group(1)} 与 plugin.json {version} 不一致")
    fingerprints = json.loads((PLUGIN_ROOT / "provenance" / "fingerprints.json").read_text())
    check(fingerprints.get("generated_for") == f"mygamestudio {version}",
          f"fingerprints.json generated_for 应为 mygamestudio {version},"
          f"实际 {fingerprints.get('generated_for')}")


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


def test_accept18_fixture() -> None:
    """任务票 18:P 环夹具 atlas-drop(已有项目,本地后端)结构与承接事实。"""

    fixtures = REPO_ROOT / "acceptance" / "18-complete-package-acceptance" / "fixtures" / "atlas-drop"
    if not fixtures.is_dir():
        check(False, "缺少 acceptance/18 夹具 atlas-drop/")
        return
    for rel in (
        "README.md",
        "src/main.js",
        "docs/mygamestudio/INDEX.md",
        "docs/mygamestudio/CONFIG.md",
        "docs/mygamestudio/PROJECT.md",
        "docs/mygamestudio/GAME_DESIGN.md",
        "docs/mygamestudio/TECH_DESIGN.md",
        "docs/mygamestudio/work/01-shield-pickup/task.md",
        "docs/mygamestudio/work/02-speed-tune/task.md",
    ):
        check((fixtures / rel).is_file(), f"atlas-drop 夹具缺少 {rel}")
    config = (fixtures / "docs/mygamestudio/CONFIG.md")
    if config.is_file():
        text = config.read_text()
        check("- 后端:local-markdown" in text, "atlas-drop CONFIG 应为 local-markdown 后端")
        check("外部连接引用及已确认操作范围:无" in text, "atlas-drop CONFIG 应无外部授权")
    project = fixtures / "docs/mygamestudio/PROJECT.md"
    if project.is_file():
        check("基线版本:v1" in project.read_text(), "atlas-drop PROJECT 应为 v1(承接事实)")
    design = fixtures / "docs/mygamestudio/GAME_DESIGN.md"
    if design.is_file():
        check("基线版本:v1" in design.read_text(), "atlas-drop GAME_DESIGN 应为 v1(承接事实)")
    task01 = fixtures / "docs/mygamestudio/work/01-shield-pickup/task.md"
    task02 = fixtures / "docs/mygamestudio/work/02-speed-tune/task.md"
    if task01.is_file():
        text = task01.read_text()
        check("任务身份:01-shield-pickup" in text and "ready-for-agent" in text,
              "atlas-drop 任务 01 应为 ready-for-agent/待执行(承接事实)")
    if task02.is_file():
        text = task02.read_text()
        check("任务身份:02-speed-tune" in text and "needs-triage" in text,
              "atlas-drop 任务 02 应为 needs-triage(承接事实)")
        check("01-shield-pickup" in text, "atlas-drop 任务 02 应依赖 01(供 ready 解析)")


def test_dist_package_consistent() -> None:
    """任务票 18(AC6):dist/ 交付物与 plugin/ 源包一致且校验和可复算。"""

    import tarfile

    dist = REPO_ROOT / "dist"
    if not dist.is_dir():
        check(False, "缺少 dist/ 交付目录")
        return
    manifest = json.loads((PLUGIN_ROOT / ".codex-plugin" / "plugin.json").read_text())
    tarball = dist / f"mygamestudio-{manifest['version']}.tar.gz"
    check(tarball.is_file(), f"缺少安装包 {tarball.name}")
    sums = dist / "SHA256SUMS.txt"
    check(sums.is_file(), "缺少 dist/SHA256SUMS.txt")
    if sums.is_file():
        listed = set()
        for line in sums.read_text().splitlines():
            parts = line.split(None, 1)
            if len(parts) != 2:
                check(False, f"SHA256SUMS.txt 行格式异常:{line}")
                continue
            digest, name = parts[0], parts[1].strip().lstrip("*")
            target = dist / name
            check(target.is_file(), f"SHA256SUMS.txt 引用的文件不存在:{name}")
            if target.is_file():
                check(sha256(target) == digest, f"{name} 与 SHA256SUMS.txt 记录的校验和不符")
            listed.add(name)
        check(str(tarball.name) in listed, "SHA256SUMS.txt 应覆盖安装包本体")
        check("package-manifest.txt" in listed, "SHA256SUMS.txt 应覆盖逐文件清单")
    pkg_manifest = dist / "package-manifest.txt"
    check(pkg_manifest.is_file(), "缺少 dist/package-manifest.txt")
    if pkg_manifest.is_file():
        entries = {}
        for line in pkg_manifest.read_text().splitlines():
            parts = line.split(None, 1)
            if len(parts) != 2:
                continue
            entries[parts[1].strip().lstrip("*")] = parts[0].strip()
        plugin_files = sorted(
            str(p.relative_to(PLUGIN_ROOT))
            for p in PLUGIN_ROOT.rglob("*") if p.is_file() and "__pycache__" not in p.parts
        )
        check(set(entries) == set(plugin_files),
              "package-manifest.txt 的文件集合应与 plugin/ 完全一致:"
              f"\n  仅在清单:{sorted(set(entries) - set(plugin_files))}"
              f"\n  仅在目录:{sorted(set(plugin_files) - set(entries))}")
        for rel, digest in entries.items():
            check(sha256(PLUGIN_ROOT / rel) == digest,
                  f"package-manifest.txt 中 {rel} 的指纹与 plugin/ 实际不符")
    if tarball.is_file():
        with tarfile.open(tarball, "r:gz") as tar:
            names = [m.name[len("plugin/"):] for m in tar.getmembers()
                     if m.name.startswith("plugin/") and m.isfile()]
        check(sorted(names) == sorted(
            str(p.relative_to(PLUGIN_ROOT))
            for p in PLUGIN_ROOT.rglob("*") if p.is_file() and "__pycache__" not in p.parts
        ), "安装包内容文件集合应与 plugin/ 完全一致")


def test_dist_rebuild_byte_reproducible() -> None:
    """审查修复票 03(R5):同源隔离重建逐字节一致,且 tar 不携带平台扩展元数据。

    反例背景:构建脚本曾仅靠 COPYFILE_DISABLE,macOS tar 仍会把
    com.apple.provenance 等扩展属性写入 PAX 头——文件内容完全一致的同源
    重建包字节不同(审查报告 R5)。本检查以「两份新副本隔离重建」固化
    验证,不再以同目录重复构建充当;user.* 扩展属性注入依赖 macOS
    xattr 语义(本包声明的目标宿主)。
    """

    import shutil
    import subprocess
    import tarfile
    import tempfile

    build = REPO_ROOT / "dist" / "build-package.sh"
    if not build.is_file():
        check(False, "缺少 dist/build-package.sh")
        return
    version = json.loads(
        (PLUGIN_ROOT / ".codex-plugin" / "plugin.json").read_text())["version"]
    tarball_name = f"mygamestudio-{version}.tar.gz"

    def pax_leak(path: Path) -> dict:
        leaked = {}
        with tarfile.open(path, "r:gz") as tar:
            for member in tar.getmembers():
                if member.pax_headers:
                    leaked[member.name] = dict(member.pax_headers)
        return leaked

    with tempfile.TemporaryDirectory(prefix="mgs-repro-") as tmp:
        hashes = []
        for tag, inject_xattr in (("copy-a", False), ("copy-b", True)):
            root = Path(tmp) / tag
            (root / "dist").mkdir(parents=True)
            shutil.copytree(PLUGIN_ROOT, root / "plugin",
                            ignore=shutil.ignore_patterns("__pycache__", ".DS_Store"))
            shutil.copy2(build, root / "dist" / "build-package.sh")
            if inject_xattr:
                for rel in (".codex-plugin/plugin.json", "skills/game-init/SKILL.md"):
                    target = root / "plugin" / rel
                    check(target.is_file(), f"xattr 注入目标不存在:{rel}")
                    if target.is_file():
                        inject = subprocess.run(
                            ["xattr", "-w", "user.mgs_r5_probe", "copy-b", str(target)],
                            capture_output=True, text=True)
                        check(inject.returncode == 0,
                              f"xattr 注入失败({rel}):{inject.stderr.strip()[:200]}")
            result = subprocess.run(
                ["./dist/build-package.sh"], cwd=root,
                stdout=subprocess.DEVNULL, stderr=subprocess.PIPE, text=True)
            check(result.returncode == 0,
                  f"隔离副本 {tag} 构建失败:{result.stderr.strip()[:300]}")
            rebuilt = root / "dist" / tarball_name
            if result.returncode == 0 and rebuilt.is_file():
                hashes.append(sha256(rebuilt))
                leaked = pax_leak(rebuilt)
                check(not leaked,
                      f"隔离副本 {tag} 重建包不应携带任何 PAX 扩展头"
                      f"(平台扩展元数据等未归一化字段):{list(leaked)[:3]}")
        check(len(hashes) == 2 and hashes[0] == hashes[1],
              "两份隔离副本同源重建的安装包应逐字节一致:"
              f"{hashes[0] if hashes else '<构建失败>'} vs "
              f"{hashes[1] if len(hashes) > 1 else '<构建失败>'}")
    delivered = REPO_ROOT / "dist" / tarball_name
    if delivered.is_file():
        leaked = pax_leak(delivered)
        check(not leaked,
              f"交付包不应携带任何 PAX 扩展头(平台扩展元数据等未归一化字段):"
              f"{list(leaked)[:3]}")


def test_accept16_sanitize_covers_unenumerated_tokens() -> None:
    """审查修复票 04(R6):脱敏不依赖实例名枚举——ARENA 中任何令牌文件
    (含手工续作签发、从未进入任何名单的新实例)的明文都必须被替换。

    反例背景:sanitize() 曾枚举固定实例名(proto1…prod2),手工续作轮签发的
    rev2/prod3 令牌文件在 ARENA 却不在名单内,明文进入证据与 Git 历史,
    「脱敏核对通过」结论不成立。本探针把名单内全部老实例与名单外新实例
    同时放进夹具 ARENA,直接执行从 run.sh 提取的 sanitize() 实现。
    """

    import secrets as pysecrets
    import subprocess
    import tempfile

    run_sh = REPO_ROOT / "acceptance" / "16-producer-complete-loop" / "run.sh"
    if not run_sh.is_file():
        check(False, "缺少 acceptance/16-producer-complete-loop/run.sh")
        return
    text = run_sh.read_text(encoding="utf-8")
    match = re.search(r"^sanitize\(\) \{.*?^\}", text, re.MULTILINE | re.DOTALL)
    check(match is not None, "run.sh 应定义 sanitize() 函数")
    if match is None:
        return
    func_src = match.group(0)

    with tempfile.TemporaryDirectory(prefix="mgs-r6-sanitize-") as tmp:
        tmp_path = Path(tmp)
        arena = tmp_path / "arena"
        arena.mkdir()
        tokens: dict[str, str] = {}
        # 名单内全部老实例(旧实现可完整跑通,红点只落在漏覆盖的新实例上)
        for name in ("proto1", "prod1", "spec1", "plan1", "impl1", "impl2",
                     "rev1", "pt1", "dsgn1", "prod2",
                     "rev2", "prod3", "impl7"):  # 后三个不在旧枚举名单内
            token = pysecrets.token_hex(32)
            tokens[name] = token
            (arena / f"{name}.token").write_text(token + "\n", encoding="utf-8")
        ev = tmp_path / "tXb-events.jsonl"
        ev.write_text("\n".join(
            f'{{"seq": {i}, "msg": "token {t} 开头"}}'
            for i, t in enumerate(tokens.values())) + "\n", encoding="utf-8")
        script = (
            "set -eu\n"
            f'ARENA="{arena}"\n'
            f"{func_src}\n"
            f'sanitize "{ev}"\n'
        )
        result = subprocess.run(["bash", "-c", script],
                                capture_output=True, text=True)
        check(result.returncode == 0,
              f"sanitize 子进程失败:{result.stderr.strip()[:300]}")
        body = ev.read_text(encoding="utf-8")
        check(tokens["prod1"] not in body and "<redacted-prod1-token>" in body,
              "sanitize 应替换名单内实例令牌(基线对照)")
        for name in ("rev2", "prod3", "impl7"):
            check(tokens[name] not in body,
                  f"sanitize 后证据仍含未枚举实例 {name} 的令牌明文(枚举漏覆盖,R6)")
            check(f"<redacted-{name}-token>" in body,
                  f"sanitize 未把未枚举实例 {name} 的令牌替换为占位符")


def test_accept16_secret_scan_gate() -> None:
    """审查修复票 04(R6)+ 复审二 SP-4:证据入库前的独立扫描。

    机制:从证据与项目文件提取全部 64 位小写 hex 候选串,逐一计算 SHA-256
    与运行根实例登记(instances.json 的 token_hash 全量集合,不枚举实例名)
    及 ARENA 全部令牌文件比对,命中即失败。注入明文令牌时验收必须失败;
    报告只含位置与实例号,不回显明文。SP-4 补:逐根核验扫描根的存在性与
    遍历错误——任一指定根缺失/不可遍历即退出 2,存在的干净根不得掩盖
    另一指定根缺失(旧实现只看全部根的总文件数,会静默成功)。
    """

    import os
    import secrets as pysecrets
    import subprocess
    import tempfile

    scanner = REPO_ROOT / "acceptance" / "16-producer-complete-loop" / "secret_scan.py"
    check(scanner.is_file(), "缺少独立扫描脚本 secret_scan.py(与脱敏实现分离)")
    if not scanner.is_file():
        return
    with tempfile.TemporaryDirectory(prefix="mgs-r6-scan-") as tmp:
        tmp_path = Path(tmp)
        ev = tmp_path / "evidence"
        ev.mkdir()
        proj = tmp_path / "proj"
        proj.mkdir()
        arena = tmp_path / "arena"
        arena.mkdir()
        tok_registered = pysecrets.token_hex(32)   # 已登记、未存 ARENA(未落盘的续作实例)
        tok_arena_only = pysecrets.token_hex(32)   # 只存 ARENA、不在登记(互补路径)
        registry = {"instances": [
            {"instance_id": "i-scanreg1", "role": "review", "task": "16-review-round-50s",
             "token_hash": hashlib.sha256(tok_registered.encode()).hexdigest()},
            {"instance_id": "i-scanreg2", "role": "producer", "task": "16-loop-sync",
             "token_hash": hashlib.sha256(b"decoy-hash-input").hexdigest()},
        ]}
        registry_path = tmp_path / "instances.json"
        registry_path.write_text(json.dumps(registry, ensure_ascii=False),
                                 encoding="utf-8")
        (arena / "manual9.token").write_text(tok_arena_only + "\n", encoding="utf-8")

        def run_scan() -> subprocess.CompletedProcess:
            return subprocess.run(
                [sys.executable, str(scanner),
                 "--evidence", str(ev), "--project", str(proj),
                 "--registry", str(registry_path),
                 "--arena-tokens", str(arena)],
                capture_output=True, text=True)

        # 干净证据:红acted 占位符 + 与登记无关的合法 SHA-256(文件/策略哈希)
        unrelated = hashlib.sha256(b"unrelated file content").hexdigest()
        (ev / "t1-events.jsonl").write_text(
            '{"msg": "<redacted-prod1-token> ok"}\n{"sha": "' + unrelated + '"}\n',
            encoding="utf-8")
        (proj / "PROJECT.md").write_text("# 项目\n基线 " + unrelated + "\n",
                                         encoding="utf-8")
        r0 = run_scan()
        check(r0.returncode == 0,
              f"干净证据(占位符+无关哈希)应通过独立扫描:{r0.stdout[-300:]}")

        # 注入 1:已登记实例的凭据明文(未存 ARENA)→ 验收失败,指认实例与位置
        injected = ev / "t6b-events.jsonl"
        injected.write_text('{"n": 1}\n{"msg": "' + tok_registered + ' 附言"}\n',
                            encoding="utf-8")
        r1 = run_scan()
        check(r1.returncode == 1,
              "注入已登记实例凭据明文时独立扫描必须失败(退出 1,验收失败)")
        check("i-scanreg1" in r1.stdout, "扫描报告应指认登记实例号(不枚举名字)")
        check("t6b-events.jsonl" in r1.stdout, "扫描报告应定位证据文件")
        check(tok_registered not in r1.stdout + r1.stderr,
              "扫描报告不得回显令牌明文")

        # 注入 2:仅存 ARENA 的令牌明文(与登记互补)→ 同样失败
        injected.write_text('{"n": 1}\n{"msg": "' + tok_arena_only + '"}\n',
                            encoding="utf-8")
        r2 = run_scan()
        check(r2.returncode == 1, "仅存 ARENA 的令牌明文也应被独立扫描发现")
        check("manual9" in r2.stdout, "扫描报告应指认 ARENA 令牌文件名")
        check(tok_arena_only not in r2.stdout + r2.stderr,
              "扫描报告不得回显令牌明文(ARENA 路径)")

        # 注入 3:项目目录(而非证据目录)泄漏 → 同样失败
        injected.write_text("", encoding="utf-8")
        (proj / "WORK.md").write_text("记录 " + tok_registered + "\n",
                                      encoding="utf-8")
        r3 = run_scan()
        check(r3.returncode == 1, "项目目录中的凭据明文同样必须使扫描失败")

        # 登记文件缺失 → 配置错误(退出 2),不得静默通过
        r4 = subprocess.run(
            [sys.executable, str(scanner),
             "--evidence", str(ev), "--project", str(proj),
             "--registry", str(tmp_path / "missing.json"),
             "--arena-tokens", str(arena)],
            capture_output=True, text=True)
        check(r4.returncode == 2, "登记文件缺失应报配置错误(退出 2),不得静默通过")

        # 扫描目标为零(路径不存在/为空)→ 失效闭合,不得静默通过
        empty = tmp_path / "empty"
        empty.mkdir()
        r5 = subprocess.run(
            [sys.executable, str(scanner),
             "--evidence", str(empty), "--project", str(tmp_path / "no-such-dir"),
             "--registry", str(registry_path),
             "--arena-tokens", str(arena)],
            capture_output=True, text=True)
        check(r5.returncode == 2,
              "扫描目标为零应报输入错误(退出 2,失效闭合),不得静默通过")

        # SP-4(复审二):逐根核验——存在的干净根不得掩盖另一指定根缺失。
        # 反例:--evidence 干净非空 + --project 不存在 + 有效登记 → 旧实现仅查
        # 全部根的「总」文件数,退出 0 称扫描完成;期望指认缺失根并退出 2。
        missing_root = tmp_path / "missing-project"
        r6 = subprocess.run(
            [sys.executable, str(scanner),
             "--evidence", str(ev), "--project", str(missing_root),
             "--registry", str(registry_path),
             "--arena-tokens", str(arena)],
            capture_output=True, text=True)
        check(r6.returncode == 2,
              "任一指定扫描根缺失时应逐根报输入错误(退出 2),"
              "不得因其他根非空而静默成功(SP-4)")
        check("missing-project" in r6.stdout,
              "扫描报告应指认缺失的扫描根(退出 2 且点名,SP-4)")

        # SP-4:遍历错误(根存在但子目录不可读)同样逐根失效闭合;
        # root 用户绕过权限位,不构成反例,跳过
        if os.geteuid() != 0:
            locked = tmp_path / "locked-root"
            (locked / "sub").mkdir(parents=True)
            (locked / "sub" / "f.txt").write_text("x", encoding="utf-8")
            os.chmod(locked / "sub", 0)
            try:
                r7 = subprocess.run(
                    [sys.executable, str(scanner),
                     "--evidence", str(ev), "--project", str(locked),
                     "--registry", str(registry_path),
                     "--arena-tokens", str(arena)],
                    capture_output=True, text=True)
                check(r7.returncode == 2,
                      "扫描根不可遍历(子目录不可读)应报输入错误(退出 2),"
                      "不得静默跳过该子树(SP-4)")
            finally:
                os.chmod(locked / "sub", 0o755)

    # run.sh 接线:末段以独立扫描替代枚举 grep,按运行根登记全量比对
    run_sh = (REPO_ROOT / "acceptance" / "16-producer-complete-loop" / "run.sh")
    if run_sh.is_file():
        text = run_sh.read_text(encoding="utf-8")
        check('python3 -B "$ACC_DIR/secret_scan.py"' in text,
              "run.sh 应以命令形态调用独立扫描脚本(注释字样不算)")
        check('--registry "$RUNROOT/instances.json"' in text,
              "run.sh 扫描应按运行根实例登记全量比对(不枚举实例名)")


def test_accept18_leak_checks_mechanized() -> None:
    """复审二 SP-5:票 18 脱敏与泄漏检查不依赖实例名枚举。

    反例背景:sanitize() 与段 8 泄漏检查仍枚举六个旧实例前缀
    (u_p p_p p_d g_p r_i1 r_i2),收口新增的离线探针实例 g_o 的令牌文件
    在 ARENA 却不在名单内——注入 g_o.token 明文后脱敏仍残留、泄漏检查
    退出 0(假绿)。本探针把 run.sh 的 sanitize() 与泄漏检查段落原样提取
    到合成夹具执行(方法沿复审探针 acceptance-probes.py):
    - sanitize:ARENA 同时放名单内实例与 g_o,名单内替换为基线对照,
      g_o 必须同样被替换(机制沿第一轮票 04 在 16 号票的 glob 先例);
    - 泄漏检查:夹具登记含 g_o token_hash 的运行根 instances.json,
      证据注入 g_o 明文 → 检查必须判 FAIL(接入 16 号票独立扫描器,
      --registry 指向运行根登记全量比对);替身凭据 GHTOKEN 的直查保留。
    """

    import hashlib as pyhash
    import secrets as pysecrets
    import shlex
    import subprocess
    import tempfile

    run_sh = REPO_ROOT / "acceptance" / "18-complete-package-acceptance" / "run.sh"
    if not run_sh.is_file():
        check(False, "缺少 acceptance/18-complete-package-acceptance/run.sh")
        return
    text = run_sh.read_text(encoding="utf-8")
    scanner = REPO_ROOT / "acceptance" / "16-producer-complete-loop" / "secret_scan.py"
    check(scanner.is_file(), "缺少 16 号票独立扫描脚本(secret_scan.py)")
    if not scanner.is_file():
        return

    sanitize_match = re.search(r"^sanitize\(\) \{.*?^\}", text,
                               re.MULTILINE | re.DOTALL)
    check(sanitize_match is not None, "run.sh 应定义 sanitize() 函数")
    leak_match = re.search(
        r'^LEAK=0\n.*?^check "原始令牌与替身凭据未泄漏到证据与项目[^\n]*$',
        text, re.MULTILINE | re.DOTALL)
    check(leak_match is not None, "run.sh 段 8 应有泄漏检查段落(LEAK 计数)")
    if sanitize_match is None or leak_match is None:
        return

    with tempfile.TemporaryDirectory(prefix="mgs-sp5-") as tmp:
        tmp_path = Path(tmp)
        arena = tmp_path / "arena"
        arena.mkdir()
        evidence = tmp_path / "evidence"
        evidence.mkdir()
        proj = tmp_path / "proj"
        proj.mkdir()
        (proj / "PROJECT.md").write_text("# 项目\n", encoding="utf-8")

        tokens: dict[str, str] = {}
        for name in ("u_p", "p_p", "p_d", "g_p", "r_i1", "r_i2",   # 旧枚举名单
                     "g_o"):                                       # 收口新增,名单外
            token = pysecrets.token_hex(32)
            tokens[name] = token
            (arena / f"{name}.token").write_text(token + "\n", encoding="utf-8")
        # 四个合成运行根:g_o 按 run.sh 实况登记在 gh 环运行根,其余为诱饵
        registry_common = {"instances": [
            {"instance_id": "i-fixture-decoy", "role": "producer",
             "task": "18-fixture", "token_hash": pyhash.sha256(b"decoy").hexdigest()},
        ]}
        registry_gh = {"instances": [
            {"instance_id": "i-fixture-go", "role": "producer", "task": "18-gh-offline",
             "token_hash": pyhash.sha256(tokens["g_o"].encode()).hexdigest()},
        ]}
        runroots: dict[str, Path] = {}
        for tag, registry in (("upg", registry_common), ("p", registry_common),
                              ("gh", registry_gh), ("reg", registry_common)):
            rr = tmp_path / f"runtime-{tag}"
            rr.mkdir()
            (rr / "instances.json").write_text(
                json.dumps(registry, ensure_ascii=False), encoding="utf-8")
            runroots[tag] = rr

        # 证据注入 g_o 明文(sanitize 应替换;泄漏检查是第二道防线,应发现)
        injected = evidence / "gh-upstream-offline.json"
        injected.write_text('{"probe": "mgs_remote", "token_in_args": "'
                            + tokens["g_o"] + '"}\n', encoding="utf-8")

        # 1) sanitize:提取实现直接执行,名单内为基线对照,g_o 不得漏
        sanitize_runner = "\n".join([
            "set -u",
            f'ARENA={shlex.quote(str(arena))}',
            "GHTOKEN=synthetic-standin-token",
            sanitize_match.group(0),
            f'sanitize {shlex.quote(str(injected))}',
        ])
        res = subprocess.run(["bash", "-c", sanitize_runner],
                             capture_output=True, text=True)
        check(res.returncode == 0,
              f"sanitize 子进程失败:{res.stderr.strip()[:300]}")
        body = injected.read_text(encoding="utf-8")
        check(tokens["g_p"] not in body,
              "sanitize 应替换名单内实例令牌(基线对照)")
        check(tokens["g_o"] not in body,
              "sanitize 后证据仍含名单外实例 g_o 的令牌明文(枚举漏覆盖,SP-5)")
        check("<redacted-g_o-token>" in body,
              "sanitize 未把名单外实例 g_o 的令牌替换为占位符(SP-5)")

        # 2) 泄漏检查:提取段落原样执行,注入明文必须判 FAIL(不得假绿)。
        #    这是独立于 sanitize 的第二道防线——重新注入明文再测(若先经
        #    修复后的 sanitize,文件已干净,检查通过才是正确行为)
        injected.write_text('{"probe": "mgs_remote", "token_in_args": "'
                            + tokens["g_o"] + '"}\n', encoding="utf-8")
        leak_runner = "\n".join([
            "set -u",
            f'ARENA={shlex.quote(str(arena))}',
            f'EVIDENCE_DIR={shlex.quote(str(evidence))}',
            f'PROJ_U={shlex.quote(str(proj))}',
            f'PROJ_P={shlex.quote(str(proj))}',
            f'PROJ_G={shlex.quote(str(proj))}',
            f'PROJ_R={shlex.quote(str(proj))}',
            f'RUNROOT_U={shlex.quote(str(runroots["upg"]))}',
            f'RUNROOT_P={shlex.quote(str(runroots["p"]))}',
            f'RUNROOT_G={shlex.quote(str(runroots["gh"]))}',
            f'RUNROOT_R={shlex.quote(str(runroots["reg"]))}',
            f'SECRET_SCAN={shlex.quote(str(scanner))}',
            "GHTOKEN=synthetic-standin-token",
            'check() { local d="$1"; shift; '
            'if "$@" >/dev/null 2>&1; then echo "leakcheck-PASS"; '
            'else echo "leakcheck-FAIL"; fi; }',
            leak_match.group(0),
        ])
        res = subprocess.run(["bash", "-c", leak_runner],
                             capture_output=True, text=True)
        check("leakcheck-FAIL" in res.stdout,
              "注入名单外实例 g_o 凭据明文时泄漏检查必须判 FAIL,"
              "不得假绿(SP-5)")
        check("leakcheck-PASS" not in res.stdout,
              "注入名单外实例 g_o 凭据明文时泄漏检查不得报 PASS(假绿,SP-5)")
        check(res.stderr.strip() == "",
              f"泄漏检查段落不应有 stderr 噪音:{res.stderr.strip()[:200]}")

    # 3) run.sh 接线形态:机制化命令在位,枚举清单退场,既有语义不弱化
    check('for path in "$ARENA"/*.token' in text,
          "sanitize 应遍历 ARENA 全部 *.token(glob,不枚举实例名)")
    check("for prefix in u_p p_p p_d g_p r_i1 r_i2" not in text,
          "run.sh 不应再枚举固定实例前缀(脱敏与泄漏检查均机制化)")
    check('python3 -B "$SECRET_SCAN"' in text,
          "泄漏检查应以命令形态调用独立扫描脚本(注释字样不算)")
    check('--registry "$rr/instances.json"' in text,
          "泄漏检查应按各运行根实例登记全量比对(--registry 指向运行根)")
    check('grep -rlF "$GHTOKEN"' in text,
          "替身凭据 GHTOKEN(非 hex 形态)的直查应保留,既有语义不弱化")


def test_accept18_probe_checks_anchored_to_events() -> None:
    """复审二 SP-6:票 18 探针行为判据必须锚定事件流真实工具返回/命令记录。

    反例背景:run.sh 的 R1 path 检查以 OR 接上对整个 r1-events.jsonl 的
    关键词 grep(不限事件类型/decision/目标),审查夹具中事件仅一条
    agentMessage、文字举例 decision=allow, rule_stage=path、零 MCP 调用,
    判据仍 PASS(allow 示例被当作实际 path 拒绝);G1 直连探针判据同样
    只查报告词族,无命令执行的示例文本即可满足。本探针(方法沿复审探针
    acceptance-probes.py 的提取式夹具法):
    - 旧判据段仍在时,审查夹具执行后必须 FAIL(修复前假绿即本测试的红);
    - 加固后的锚定实现(mcp_deny_anchor/curl_direct_denied)对审查夹具、
      allow 工具返回夹具、无命令执行的示例文本夹具一律不成立;
    - 真实 deny/path、真实 curl 直连失败的事件流必须成立;
    - 对本仓留存的验收证据重跑锚定判据仍 PASS(不因加固翻案)。
    """

    import shlex
    import subprocess
    import tempfile

    run_sh = REPO_ROOT / "acceptance" / "18-complete-package-acceptance" / "run.sh"
    if not run_sh.is_file():
        check(False, "缺少 acceptance/18-complete-package-acceptance/run.sh")
        return
    text = run_sh.read_text(encoding="utf-8")
    ev_dir = REPO_ROOT / "acceptance" / "18-complete-package-acceptance" / "evidence"

    def run_bash(script: str) -> str:
        res = subprocess.run(["bash", "-c", script],
                             capture_output=True, text=True)
        return res.stdout + res.stderr

    # —— 夹具构造(照真实事件结构;全部合成值,不含任何真实凭据)——

    def mcp_write_event(path: str, decision: str, stage: str, target: str) -> str:
        item = {
            "type": "mcpToolCall", "tool": "mgs_write", "status": "completed",
            "arguments": {"token": "<redacted-token>", "path": path,
                          "content": "x", "expected_sha256": "absent"},
            "result": {"content": [{"type": "text", "text": json.dumps({
                "op": "write", "decision": decision, "reason": "fixture",
                "rule_stage": stage, "instance_id": "i-fixture",
                "task": "18-reg-a", "role": "implement", "purpose": "production",
                "target": target, "basis": {},
            }, ensure_ascii=False)}]},
        }
        return json.dumps({"method": "item/completed",
                           "params": {"item": item}}, ensure_ascii=False)

    with tempfile.TemporaryDirectory(prefix="mgs-sp6-") as tmp:
        tmp_path = Path(tmp)

        # 夹具 A(审查夹具,逐字沿复审探针):仅一条 agentMessage,
        # 文字举例 decision=allow, rule_stage=path,零 MCP 调用
        fixture_a = tmp_path / "r1-events-a.jsonl"
        fixture_a.write_text(json.dumps({
            "method": "item/completed",
            "params": {"item": {"type": "agentMessage",
                                "text": "Example only: " + json.dumps(
                                    {"decision": "allow", "rule_stage": "path"})}},
        }, ensure_ascii=False) + "\n", encoding="utf-8")
        # 夹具 B(真实 deny/path 形态的 mcpToolCall 返回)
        fixture_b = tmp_path / "r1-events-b.jsonl"
        fixture_b.write_text(
            mcp_write_event("/tmp/mgs18-evil-link.md", "deny", "path",
                            "/tmp/mgs18-evil-link.md") + "\n", encoding="utf-8")
        # 夹具 C(同为 mcpToolCall 但 decision=allow:allow 示例不得成立)
        fixture_c = tmp_path / "r1-events-c.jsonl"
        fixture_c.write_text(
            mcp_write_event("/tmp/mgs18-evil-link.md", "allow", "granted",
                            "/tmp/mgs18-evil-link.md") + "\n", encoding="utf-8")

        # G1 夹具 D:示例文本提及 curl 直连失败,但无任何命令执行记录
        g1_fixture_d_events = tmp_path / "g1-events-d.jsonl"
        g1_fixture_d_events.write_text(json.dumps({
            "method": "item/completed",
            "params": {"item": {"type": "agentMessage",
                                "text": "探针示例:curl -sS http://127.0.0.1/x "
                                        "→ failed to connect(仅举例)"}},
        }, ensure_ascii=False) + "\n", encoding="utf-8")
        # G1 夹具 E:真实 commandExecution 失败形态(curl 直连替身被拒)
        g1_fixture_e_events = tmp_path / "g1-events-e.jsonl"
        g1_fixture_e_events.write_text(json.dumps({
            "method": "item/completed",
            "params": {"item": {
                "type": "commandExecution",
                "command": "/bin/zsh -lc 'curl -sS -m 3 http://127.0.0.1:1/_test/ping'",
                "status": "failed", "exitCode": 7,
                "aggregatedOutput": "curl: (7) Failed to connect to 127.0.0.1 "
                                    "port 1 after 0 ms: Couldn't connect to server\n",
            }},
        }, ensure_ascii=False) + "\n", encoding="utf-8")

        # —— 0)旧判据段仍在时:审查/示例夹具必须 FAIL(修复前的假绿=红)——

        legacy_r1 = re.search(
            r"^if grep -Eq '\"rule_stage\".*?^fi$", text, re.MULTILINE | re.DOTALL)
        if legacy_r1 is not None:
            report = tmp_path / "r1-report-legacy.md"
            report.write_text("no result supplied\n", encoding="utf-8")
            runner = "\n".join([
                "set -u",
                f'EVIDENCE_DIR={shlex.quote(str(tmp_path))}',
                'mv "$EVIDENCE_DIR"/r1-events-a.jsonl "$EVIDENCE_DIR/r1-events.jsonl"',
                'ok() { echo "LEGACY-PASS"; }',
                'bad() { echo "LEGACY-FAIL"; }',
                legacy_r1.group(0),
            ])
            out = run_bash(runner)
            check("LEGACY-FAIL" in out and "LEGACY-PASS" not in out,
                  "旧 R1 path 判据对无 MCP 调用的 allow 示例夹具必须 FAIL,"
                  "当前词串 grep 分支假绿(SP-6)")
        legacy_g1 = re.search(
            r"^if grep -qE 'curl\|127\.0\.0\.1'.*?^fi$",
            text, re.MULTILINE | re.DOTALL)
        if legacy_g1 is not None:
            report = tmp_path / "g1-report.md"
            report.write_text("直连探针:curl http://127.0.0.1/x failed to connect"
                              "(示例文本)\n", encoding="utf-8")
            runner = "\n".join([
                "set -u",
                f'EVIDENCE_DIR={shlex.quote(str(tmp_path))}',
                'mv "$EVIDENCE_DIR"/g1-events-d.jsonl "$EVIDENCE_DIR/g1-events.jsonl"',
                'ok() { echo "LEGACY-PASS"; }',
                'bad() { echo "LEGACY-FAIL"; }',
                legacy_g1.group(0),
            ])
            out = run_bash(runner)
            check("LEGACY-FAIL" in out and "LEGACY-PASS" not in out,
                  "旧 G1 直连判据对无命令执行的示例文本必须 FAIL,"
                  "当前报告词族分支假绿(SP-6 自查)")

        # —— 1)加固实现存在且只认真实工具返回/命令记录 ——

        anchor_fn = re.search(r"^mcp_deny_anchor\(\) \{.*?^\}$",
                              text, re.MULTILINE | re.DOTALL)
        check(anchor_fn is not None,
              "run.sh 应定义 mcp_deny_anchor(事件流 mcpToolCall 锚定,SP-6)")
        curl_fn = re.search(r"^curl_direct_denied\(\) \{.*?^\}$",
                            text, re.MULTILINE | re.DOTALL)
        check(curl_fn is not None,
              "run.sh 应定义 curl_direct_denied(事件流 commandExecution 锚定,SP-6)")
        if anchor_fn is None or curl_fn is None:
            return
        fn_defs = anchor_fn.group(0) + "\n" + curl_fn.group(0)

        def anchor_call(events: Path, *args: str) -> str:
            # 位置参数经 set -- 传入,避免引号嵌套歧义
            script = "\n".join([
                "set -u", fn_defs,
                f'set -- {shlex.quote(str(events))} '
                + " ".join(shlex.quote(a) for a in args),
                'R=$(mcp_deny_anchor "$1" "$2" "$3" "$4")',
                'echo "ANCHOR:$R"',
            ])
            return run_bash(script).strip()

        def curl_call(events: Path) -> str:
            script = "\n".join([
                "set -u", fn_defs,
                f'set -- {shlex.quote(str(events))}',
                'R=$(curl_direct_denied "$1")',
                'echo "CURL:$R"',
            ])
            return run_bash(script).strip()

        link = "/tmp/mgs18-evil-link.md"
        check(anchor_call(fixture_a, "mgs_write", "path", link) == "ANCHOR:MISSING",
              "审查夹具(仅 agentMessage 的 allow 示例词串)不得满足 path 锚定(SP-6)")
        check(anchor_call(fixture_c, "mgs_write", "path", link) == "ANCHOR:MISSING",
              "allow 的 mgs_write 返回不得满足 path 锚定(须核对 decision=deny)")
        check(anchor_call(fixture_b, "mgs_write", "path", link) == "ANCHOR:OK",
              "真实 deny/path 的 mgs_write 返回必须满足锚定(不得误伤)")
        check(curl_call(g1_fixture_d_events) == "CURL:MISSING",
              "无命令执行记录的示例文本不得满足直连探针锚定(SP-6 自查)")
        check(curl_call(g1_fixture_e_events) == "CURL:OK",
              "真实失败的 curl 直连 commandExecution 必须满足锚定(不得误伤)")

        # —— 2)对仓内留存验收证据重跑锚定判据:仍 PASS,不因加固翻案 ——

        r1_real = ev_dir / "r1-events.jsonl"
        if r1_real.is_file():
            for stage, target in (("role_scope", "docs/mygamestudio/PROJECT.md"),
                                  ("occupancy", "src/lock-probe.txt"),
                                  ("task_grant", "src/other.txt"),
                                  ("path", link)):
                check(anchor_call(r1_real, "mgs_write", stage, target) == "ANCHOR:OK",
                      f"留存 R1 证据重跑锚定判据仍 PASS(deny/{stage} → {target})")
        g1_real = ev_dir / "g1-events.jsonl"
        if g1_real.is_file():
            check(curl_call(g1_real) == "CURL:OK",
                  "留存 G1 证据重跑直连探针锚定仍 PASS")
            for target in ("01-harbor-timer", "02-crane-sprite"):
                check(anchor_call(g1_real, "mgs_remote", "task_grant", target)
                      == "ANCHOR:OK",
                      f"留存 G1 证据重跑越界锚定仍 PASS(mgs_remote deny → {target})")
        p1_real = ev_dir / "p1-events.jsonl"
        if p1_real.is_file():
            check(anchor_call(p1_real, "mgs_write", "role_scope|task_grant",
                              "docs/mygamestudio/GAME_DESIGN.md") == "ANCHOR:OK",
                  "留存 P1 证据重跑越界锚定仍 PASS")
        p2_real = ev_dir / "p2-events.jsonl"
        if p2_real.is_file():
            check(anchor_call(p2_real, "mgs_write", "role_scope|task_grant",
                              "docs/mygamestudio/GAME_DESIGN.md") == "ANCHOR:OK",
                  "留存 P2 证据重跑越界锚定仍 PASS")
        r1b_real = ev_dir / "r1b-events.jsonl"
        if r1b_real.is_file():
            check(anchor_call(r1b_real, "mgs_write", "identity", "src/stale.txt")
                  == "ANCHOR:OK",
                  "留存 R1b 证据重跑 identity 锚定仍 PASS")

    # —— 3)run.sh 接线形态:探针行为判据锚定事件流,旧词串分支退场 ——

    check("|| grep -qF 'rule_stage" not in text,
          "R1 path 判据不应再保留对整个 JSONL 的任意词串 grep OR 分支(SP-6)")
    for snippet, desc in (
        ('mcp_deny_anchor "$EVIDENCE_DIR/r1-events.jsonl" mgs_write path',
         "R1 path 判据应以事件流 mcpToolCall 锚定接线"),
        ('mcp_deny_anchor "$EVIDENCE_DIR/r1-events.jsonl" mgs_write role_scope',
         "R1 role_scope 判据应以事件流锚定接线"),
        ('mcp_deny_anchor "$EVIDENCE_DIR/r1-events.jsonl" mgs_write occupancy',
         "R1 occupancy 判据应以事件流锚定接线"),
        ('mcp_deny_anchor "$EVIDENCE_DIR/r1-events.jsonl" mgs_write task_grant',
         "R1 task_grant 判据应以事件流锚定接线"),
        ('mcp_deny_anchor "$EVIDENCE_DIR/g1-events.jsonl" mgs_remote task_grant',
         "G1 越界远端判据应以事件流锚定接线"),
        ('mcp_deny_anchor "$EVIDENCE_DIR/p1-events.jsonl" mgs_write',
         "P1 越界判据应以事件流锚定接线"),
        ('mcp_deny_anchor "$EVIDENCE_DIR/p2-events.jsonl" mgs_write',
         "P2 越界判据应以事件流锚定接线"),
        ('mcp_deny_anchor "$EVIDENCE_DIR/r1b-events.jsonl" mgs_write identity',
         "R1b identity 判据应以事件流锚定接线"),
        ('curl_direct_denied "$EVIDENCE_DIR/g1-events.jsonl"',
         "G1 直连判据应以事件流 commandExecution 锚定接线"),
    ):
        check(snippet in text, desc)


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
    test_prototype_skill_content()
    test_accept07_fixture()
    test_game_plan_skill_content()
    test_accept08_fixture()
    test_production_skills_content()
    test_accept09_fixture()
    test_game_art_skill_content()
    test_accept10_fixture()
    test_game_audio_skill_content()
    test_accept11_fixture()
    test_game_build_skill_content()
    test_accept12_fixture()
    test_game_review_skill_content()
    test_accept13_fixture()
    test_game_playtest_skill_content()
    test_accept14_fixture()
    test_goal_change_skills_content()
    test_accept15_fixture()
    test_producer_loop_skills_content()
    test_accept16_fixture()
    test_github_issue_workflow_content()
    test_provenance_version_consistency()
    test_config_template_adaptation()
    test_internal_references_resolve()
    test_accept18_fixture()
    test_dist_package_consistent()
    test_dist_rebuild_byte_reproducible()
    test_accept16_sanitize_covers_unenumerated_tokens()
    test_accept16_secret_scan_gate()
    test_accept18_leak_checks_mechanized()
    test_accept18_probe_checks_anchored_to_events()
    if FAILURES:
        print(f"FAIL ({len(FAILURES)} 项):")
        for failure in FAILURES:
            print(f"  - {failure}")
        return 1
    print("OK: 最小插件包静态完整性检查全部通过")
    return 0


if __name__ == "__main__":
    sys.exit(main())

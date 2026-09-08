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
    if FAILURES:
        print(f"FAIL ({len(FAILURES)} 项):")
        for failure in FAILURES:
            print(f"  - {failure}")
        return 1
    print("OK: 最小插件包静态完整性检查全部通过")
    return 0


if __name__ == "__main__":
    sys.exit(main())

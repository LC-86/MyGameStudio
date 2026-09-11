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
        # 公开接缝用导入与调用验证:仓库坐标/授权解析归来源 module,
        # adapter 保持同名可用接缝(错误身份与既有捕获分支不变)。
        records_dir = str(module.parent)
        if records_dir not in sys.path:
            sys.path.insert(0, records_dir)
        import mgs_github
        for seam in ("parse_repo_location", "parse_remote_authorizations"):
            check(callable(getattr(mgs_github, seam, None)),
                  f"records/mgs_github.py 缺少可用公开接缝 {seam}")
        check(isinstance(getattr(mgs_github, "GithubBackend", None), type),
              "records/mgs_github.py 缺少 GithubBackend")
        for method in ("create_task", "update_task", "set_triage", "append_result",
                       "set_relations", "set_parent", "close_task", "publish_drafts"):
            check(callable(getattr(mgs_github.GithubBackend, method, None)),
                  f"GithubBackend 缺少公开接缝 {method}")
        for seam in ("plan_backend_switch", "apply_backend_switch",
                     "handover_baseline_check"):
            check(callable(getattr(mgs_github, seam, None)),
                  f"records/mgs_github.py 缺少可用公开接缝 {seam}")
        text = module.read_text(encoding="utf-8")
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
            # 泄漏段在 run.sh 里由脚本头部的 say(){ printf; } 兜底,提取段
            # 不含该定义,裸 say 会落到系统真语音,此处补定义保持纯打印
            "say() { printf '%s\\n' \"$*\"; }",
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
    """复审二 SP-6 + 复审三 SP-8/SP-9:票 18 探针行为判据锚定事件流真实
    工具返回/命令记录,且核对具体资源、预期动作与实际执行的命令。

    反例背景(SP-6):run.sh 的 R1 path 检查以 OR 接上对整个 r1-events.jsonl
    的关键词 grep(不限事件类型/decision/目标),审查夹具中事件仅一条
    agentMessage、文字举例 decision=allow, rule_stage=path、零 MCP 调用,
    判据仍 PASS(allow 示例被当作实际 path 拒绝);G1 直连探针判据同样
    只查报告词族,无命令执行的示例文本即可满足。本探针(方法沿复审探针
    acceptance-probes.py 的提取式夹具法):
    - 旧判据段仍在时,审查夹具执行后必须 FAIL(修复前假绿即本测试的红);
    - 加固后的锚定实现(mcp_deny_anchor/curl_direct_denied)对审查夹具、
      allow 工具返回夹具、无命令执行的示例文本夹具一律不成立;
    - 真实 deny/path、真实 curl 直连失败的事件流必须成立;
    - 对本仓留存的验收证据重跑锚定判据仍 PASS(不因加固翻案)。

    反例背景(SP-8/SP-9,第三轮):SP-6 的锚定对调用与返回双方做子串
    包含且不核预期动作——对 .bak 后缀文件的真实 deny/path 可骗过正式
    R1 目标,对 01-harbor-timer 的 append-result 真实 deny/task_grant 可
    骗过 G1「越界 update 被拒」;curl 判据只查命令全文词串,printf 打印
    curl 示例并 exit 7(未执行 curl)仍成立。精化要求(沿第三轮复审探针
    spec-custom-probes.py / acceptance_recheck.py 的夹具形态):
    - 资源规范化后具体一致(整路径段比较,拒绝前缀/后缀混淆,兼容
      相对/绝对路径与 GitHub URI 形态及 append-result 的 /comments 衍生段);
    - 预期动作一致(mgs_write 核调用目标即写目标;mgs_remote 核调用
      action 与返回 op 的动作语境);
    - curl 判据与实际执行的命令关联(剥 shell 包装后首个可执行 token
      为 curl 且参数含替身地址);
    - read→update 邻近变体保持 MISSING(与复审/分诊一致,不翻案)。

    反例背景(SP-12/SP-13,第四轮):SP-8 的整段尾匹配对**绝对**期望路径
    仍接受任意前缀(/tmp/alternate-root/tmp/x 的 deny 满足 /tmp/x 判据),
    comments 衍生尾段白名单不分调用/返回两侧、不限次数(身份
    01-harbor-timer/comments 的 append-result deny、返回 target 双
    comments 仍满足 01-harbor-timer 判据);curl 判据在 shell 的全部参数
    中找 -c 旗标、不在脚本路径处停止(sh script.sh -c 'curl …' 未执行
    curl 仍成立),且 127.0.0.1 出现在 -H 头部值或注释词串也算直连。
    精化要求(沿第四轮复审探针 spec-independent-probes.py /
    curl-new-probes.py 的夹具形态):
    - 绝对期望要求候选即该绝对路径或其规范等价,不接受任意前缀;
      相对期望沿尾部整段语境;
    - 调用身份与返回派生 URI 分侧核验(调用侧=任务身份本身,不带
      动作派生尾段;返回侧=身份+至多一个 append-result 的 /comments
      段,重复/多段拒绝);
    - shell 包装解析按位置(-c 旗标须紧跟 shell 可执行之后,遇脚本
      路径即停止解析);127.0.0.1 须出现在实际连接目标参数(URL 形态
      位置参数)而非头部值/注释/任意词串;名单外旗标形态保守拒绝;
    - 真对照(裸 curl/zsh 包装 curl 真实连接失败)仍必须锚定。

    反例背景(SP-15/SP-16,第五轮):SP-13 的 URL 前缀判据不看解析后
    的主机——userinfo 段冒充连接目标(http://127.0.0.1:端口@127.0.0.2:
    端口/ 实际连接 127.0.0.2 失败仍判 OK);路径候选在规范化前被
    .strip() 删除合法文件名字符——尾空格的另一文件(/tmp/x.md 与
    /tmp/x.md␣)normpath 本不相等,判据却 OK。精化要求(沿第五轮复审
    探针 curl-extra-probes-5.py / path-extra-probes-5.py 的夹具形态):
    - 127.0.0.1 必须是 urlparse 解析出的实际 hostname(userinfo 是
      凭证段不是连接目标;域名伪装/IPv6 其他目标同样不成立);
    - 路径资源身份不删字符:JSON 路径参数中的首尾空格属文件名,
      不是排版空白;仅允许 normpath 等价类(尾斜杠/./ 段/重复斜杠
      归并),候选与期望的 normpath 不相等即不满足;
    - 既有等价类(OK)与拒绝形态(repeat-path/case-variant/
      space-prefix MISSING)、真对照(裸 curl 直连 127.0.0.1)不变。

    反例背景(SP-18/SP-19,第六轮):SP-15 的 host 核验仍只看 URL 字符串
    ——--proxy http://127.0.0.2:端口 / --resolve 127.0.0.1:端口:127.0.0.2
    改变实际连接目标(URL 仍是 .1,curl 实连 .2 失败仍判 OK 假绿);多
    URL 命令用整次进程退出码+合并输出判失败——目标 .1 已返回 200/
    TARGET_SUCCESS 后另一 .2 超时使 exit 28,仍判「替身直连失败」。
    精化要求(沿第六轮复审探针 curl-boundaries-6.py 的夹具形态,真实
    curl 执行封装):改变连接语义的参数(--proxy/--resolve/--host/
    --interface)保守拒绝,出现即整个命令不成立(--noproxy 禁止代理、
    保持直连语义,固定探针自身在用,保留);只接受恰好一个 URL 形态
    位置参数(多 URL 的整次进程失败无法归属到目标 URL);真对照
    (direct、userinfo-correct-host)不因收窄误伤。

    反例背景(SP-20~SP-23,第七轮):SP-18/SP-19 的两轴仍有未覆盖形态
    ——短旗标 -x(代理)/-K(配置文件)仍在带值短旗标白名单,接纳后
    仅跳过值,URL 仍是 .1 而实连 .2 失败仍判 OK(SP-20);-L/--location
    在无值白名单但只核初始 URL,.1 返回 302 后 curl 转向 .2 连接失败
    (exit 28,.1 已被直连访问)仍判 OK(SP-21);粘连短值 -m2 使解析器
    把下一参数(首 URL)当值吞掉,单 URL 限制被绕过(实际 curl 把 2 当
    超时值、两个 URL 都访问,首 URL 真拿到 200)(SP-22);通用 timed out
    词族把「连接已成功、响应阶段超时」(200 + 15/25 字节后延迟,输出
    Operation timed out … with 15 out of 25 bytes received)当作连接被拒
    (SP-23);任务专属 CURL_HOME/.curlrc 与子进程 http_proxy 也能使不带
    覆盖参数的 URL 实连 .2 而判 OK(事件不记录环境,ambient 观察项)。
    精化要求(沿第七轮复审探针 curl-adversarial-7.py 的夹具形态,真实
    curl 执行封装,loopback 服务器记录命中佐证):
    - 改变连接语义的短旗标(x/K/U 同域)保守拒绝,出现即整个命令不
      成立;重定向旗标(-L/--location)保守拒绝(判据无法确认最终目标
      归属);
    - 短旗标值按 curl 语义消费:带值字符位于 token 末尾取下一参数为
      值,粘连形式值即 token 余部、只消费当前 token——URL 计数反映
      真实参数语义;
    - 失败证据须能证明对替身的连接未被允许:连接阶段失败词族并绑定
      实际尝试主机(输出中须有一行同时含连接失败短语与替身地址),
      通用 operation timed out / 响应阶段超时不再单独成立;ambient 隐式
      配置使实连他址的失败输出点名他址,同样不能成立(处置 (a));
    - 真对照(direct、correct-userinfo、two-shell-layers、
      redirect-not-followed、separate-short-value-two-urls、
      successful-target)逐项不变。

    反例背景(SP-24~SP-26,第八轮):SP-22 粘连值消费修改后,短 token
    内先找任意带值字符即消费,未确认该字符前每个字符均属无值白名
    单——`-Lm2`/`-LsSm2`/`-Lm 2` 禁用前缀 L 被 m 掩盖、`-K路径` 的
    K 被路径中 m 误认为带值旗标,四例判 OK 假绿(SP-24;前三例为本
    批粘连消费引入的新回归,`-Lm 2` 为同根既有遗漏);失败判定任意
    行同时含连接短语与 `.1` 子串即成立,响应正文
    `Failed to connect to 127.0.0.1` 冒充连接诊断(连接已成功、部分
    字节到达后超时,SP-25),主机子串把 127.0.0.10 当 127.0.0.1
    (SP-26)。精化要求(沿第八轮复审探针 new-probes-8.py 形态,真实
    curl 执行封装,loopback 服务器记录命中佐证):
    - 短旗标按顺序验证:首个带值字符之前的每个字符必须都在
      CURL_PLAIN_SHORT 内,否则整个命令不成立;正常聚合 `-sSm2`/
      `-sSm 2` 保持 OK;
    - 失败证据约束为 curl 诊断行形态(错误前缀 `curl: (N)` + 连接
      短语 + 目标主机),响应正文伪装不成立;正文逐字节模拟诊断
      行的残余边界留档(aggregatedOutput 不分 stdout/stderr,单正则
      不宣称来源完备);诊断行中的目标主机身份与替身相等比较,
      非子串包含;
    - 对照逐例不变——OK 组:direct、valid-aggregate-attached/
      separate、terminator-url;MISSING 组:standalone-config/
      redirect、invalid-short-value、proxy-user-short、
      plain-body-then-timeout、response-body-completed、
      ambient-proxy-dot2。

    反例背景(SP-27~SP-29,第九轮):SP-22/24 的短旗标接纳表把无值旗标
    `g`(globoff)/`J`(remote-header-name)/`Z`(parallel)列为带值——
    `-g/-J/-sS -Z` 后接成功 URL 与失败 URL 时把首 URL 当参数值跳过,
    单 URL 守卫只看到第二个失败 URL,首请求真实 200/TARGET_SUCCESS
    仍判 OK 假绿;合法 `-g <失败URL>`、`-sS -Z <失败URL>` 则把唯一
    URL 吞掉,判据 MISSING(反向假阴性)(SP-27)。`--retry` 被接纳但
    判据只要求失败进程任一行诊断绑定目标:首轮 503+完整正文后关服,
    重试产生真实 `curl: (7) Failed to connect`,连接已被允许仍判 OK
    (SP-28)。单个 URL 参数 `http://127.0.0.1:{成功端口,关闭端口}/ok`
    经 curl 默认 glob 展成两个请求,`len(urls)==1` 不足(SP-29)。
    精化要求(沿第九轮复审探针 new-probes-9.py 与 parallel-curl-
    supplement.py 形态,真实 curl 执行封装,loopback 服务器记录命中):
    - 按实际参数是否带值核对接纳表:`g`/`J`/`Z` 移入无值短旗标;
      其余接纳表字符对照本机 curl 帮助与执行,无更多错分类;
      裸 `-Z` 诊断行前带进度文字仍 MISSING(行首正则,审方校准);
    - `--retry` 保守拒绝(逐次尝试证明属 curl 语义子集不实现);
      已披露取舍:真失败+重试的 retry-closed-control 从 OK 翻转为
      MISSING;
    - URL 形态位置参数(含 `--` 之后)含 `{}`/`[]` 任一字符即整个
      命令不成立;`--globoff` 本就不在长旗标白名单、IPv6 字面量
      本就过不了 hostname 检查,行为不变;
    - 对照逐例——OK 组:direct、legitimate-aggregate、silent-direct;
      retry-closed-control 翻转为 MISSING;MISSING 组:url-glob-
      disabled-long、two-urls-plain、mixed-prefix-sLm2、single-dash、
      terminator-attached-option、lowercase-lm2、uppercase-M2、
      retry-503-then-200、no-value-Z-two-urls;full-diagnostic-body
      为 SP-25 已接受残余(探针 expected 列 MISSING、产品维持 OK)。

    反例背景(SP-30,第十轮):第九轮 glob 拒绝只覆盖 URL 形态位置参数
    与 `--` 后参数,`-T`/`--upload-file` 的**值**本身支持 curl glob——
    单 URL(URL 无 glob 字符)配 `-T '{a.txt,b.txt}'` 展开两次 PUT:
    首次 PUT 200/18 字节后关服,第二次真实 `curl: (7) Failed to
    connect` exit 7,判据仍 OK 假绿。精化要求(沿第十轮复审探针
    new-curl-probes.py 的 once_upload 形态,真实 curl 执行封装,
    loopback 服务器记录首次 PUT 后关监听):
    - `-T`/`--upload-file` 的值(分离取下一参数、粘连取 token 余部、
      聚合内粘连按 SP-22 语义取值)含 `{`/`}`/`[`/`]` 任一字符即整个
      命令不成立;既有 URL 位置参数与 `--` 后参数的 glob 检查不动;
    - 不采用「移除上传旗标」宽方案(会误伤普通单文件上传真失败对照);
    - `--upload-file={a,b}` 长等号形态本就被名单拒绝;`-g` 关闭展开
      因字面文件不存在而 MISSING,行为不变;
    - 对照逐例——OK 组:upload-single-closed、upload-long-single-
      closed;MISSING 组:upload-glob-with-g、upload-glob-long-equals;
      既有 review9 对照(direct/legitimate-aggregate/silent-direct OK,
      其余拒绝形态 MISSING,两条已披露例外行)逐项不变。
    """

    import importlib.util
    import shlex
    import subprocess
    import tempfile

    run_sh = REPO_ROOT / "acceptance" / "18-complete-package-acceptance" / "run.sh"
    if not run_sh.is_file():
        check(False, "缺少 acceptance/18-complete-package-acceptance/run.sh")
        return
    text = run_sh.read_text(encoding="utf-8")
    ev_dir = REPO_ROOT / "acceptance" / "18-complete-package-acceptance" / "evidence"

    # 判据 module 与 Shell 适配层(票 08):测试经真实 module 的 __main__ 入口
    # 调用与运行脚本同一 seam——不再正则截取 Shell 函数源码,也不再为每例
    # 拼接大段 Shell。journal 为路径时 module 逐行解析 JSONL,为可迭代事件时
    # 直接消费已构造事件(离线事件回放,零网络/零模型)。
    judge_module = (REPO_ROOT / "acceptance" / "18-complete-package-acceptance"
                    / "evidence_judgement.py")
    adapter_sh = (REPO_ROOT / "acceptance" / "18-complete-package-acceptance"
                  / "evidence_adapter.sh")
    check(judge_module.is_file(), "缺少 acceptance/18 判据 module evidence_judgement.py")
    check(adapter_sh.is_file(), "缺少 acceptance/18 Shell 适配层 evidence_adapter.sh")
    spec = importlib.util.spec_from_file_location("mgs18_evidence_judgement",
                                                  judge_module)
    if spec is None or spec.loader is None:
        check(False, "无法加载 acceptance/18 判据 module")
        return
    judge = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(judge)

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

    def mcp_remote_event(action: str, identity: str, decision: str, stage: str,
                         op: str, target: str) -> str:
        # mgs_remote 调用/返回形态照留存 g1-events.jsonl 与第三轮复审夹具:
        # 调用 action+payload.identity,返回 op=remote:<action>、target 为
        # github:// URI(update 无 /comments;append-result 带 /comments;
        # read 的资源语义是 issues 集合、返回 target 不含具体 identity)
        item = {
            "type": "mcpToolCall", "tool": "mgs_remote", "status": "completed",
            "arguments": {"action": action,
                          "payload": {"identity": identity},
                          "token": "<redacted-token>"},
            "result": {"content": [{"type": "text", "text": json.dumps({
                "op": op, "decision": decision, "reason": "fixture",
                "rule_stage": stage, "instance_id": "i-fixture",
                "task": "18-gh", "role": "producer", "purpose": "production",
                "target": target, "basis": {},
            }, ensure_ascii=False)}]},
        }
        return json.dumps({"method": "item/completed",
                           "params": {"item": item}}, ensure_ascii=False)

    def command_event(command: str, exit_code: int, output: str) -> str:
        # commandExecution 形态照留存 g1-events.jsonl 与第四轮复审夹具:
        # status/exitCode 反映实际执行结果,aggregatedOutput 为原始输出
        item = {
            "type": "commandExecution",
            "command": command,
            "status": "failed" if exit_code else "completed",
            "exitCode": exit_code,
            "aggregatedOutput": output,
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

        # 夹具 F(review3 SP-8 wrong-target-prefix 逐字形态):对 .bak 后缀
        # 文件的真实 mgs_write deny/path——调用与返回都含正式目标的子串,
        # 但不是同一文件
        fixture_f = tmp_path / "r1-events-f.jsonl"
        fixture_f.write_text(
            mcp_write_event("/tmp/mgs18-evil-link.md.bak", "deny", "path",
                            "/tmp/mgs18-evil-link.md.bak") + "\n",
            encoding="utf-8")
        # 夹具 G(review3 SP-8 append-denial-as-update-proof 逐字形态):对
        # 01-harbor-timer 的真实 mgs_remote append-result deny/task_grant——
        # 不是 G1「越界 update 被拒」语境的动作
        fixture_g = tmp_path / "g1-events-g.jsonl"
        fixture_g.write_text(mcp_remote_event(
            "append-result", "01-harbor-timer", "deny", "task_grant",
            "remote:append-result",
            "github://github.com/mygamestudio/issue-accept/issues/"
            "01-harbor-timer/comments") + "\n", encoding="utf-8")
        # 夹具 H(read→update 邻近变体):对 01-harbor-timer 的 read
        # deny/task_grant——分诊实测旧判据即 MISSING(返回 target 为 issues
        # 集合形态、不含具体 identity),精化后必须保持
        fixture_h = tmp_path / "g1-events-h.jsonl"
        fixture_h.write_text(mcp_remote_event(
            "read", "01-harbor-timer", "deny", "task_grant", "remote:read",
            "github://github.com/mygamestudio/issue-accept/issues") + "\n",
            encoding="utf-8")
        # 夹具 I(review3 SP-9 curl-command-example 逐字形态):printf 打印
        # curl 示例并 exit 7 的真实失败 commandExecution——首可执行命令是
        # printf,未执行 curl、未直连替身
        g1_fixture_i_events = tmp_path / "g1-events-i.jsonl"
        printf_cmd = ("printf '%s\\n' "
                      "'curl http://127.0.0.1:1/_test/ping (example only)' "
                      "'Failed to connect (example only)'; exit 7")
        g1_fixture_i_events.write_text(json.dumps({
            "method": "item/completed",
            "params": {"item": {
                "type": "commandExecution",
                "command": "/bin/zsh -lc " + shlex.quote(printf_cmd),
                "status": "failed", "exitCode": 7,
                "aggregatedOutput": "curl http://127.0.0.1:1/_test/ping "
                                    "(example only)\n"
                                    "Failed to connect (example only)\n",
            }},
        }, ensure_ascii=False) + "\n", encoding="utf-8")

        # 夹具 J(review4 SP-12 absolute-prefix 逐字形态):真实 Gate 对
        # /tmp/alternate-root/tmp/mgs18-evil-link.md 的 deny/path——尾部
        # 整段与正式目标 /tmp/mgs18-evil-link.md 相同,但两个都是明确的
        # 绝对路径,不是同一资源
        fixture_j = tmp_path / "r1-events-j.jsonl"
        fixture_j.write_text(
            mcp_write_event("/tmp/alternate-root/tmp/mgs18-evil-link.md",
                            "deny", "path",
                            "/tmp/alternate-root/tmp/mgs18-evil-link.md")
            + "\n", encoding="utf-8")
        # 夹具 K(review4 SP-12 identity-comments-suffix 逐字形态):对身份
        # 01-harbor-timer/comments 的真实 append-result deny/task_grant,
        # 返回 target 尾部为 01-harbor-timer/comments/comments
        fixture_k = tmp_path / "g1-events-k.jsonl"
        fixture_k.write_text(mcp_remote_event(
            "append-result", "01-harbor-timer/comments", "deny", "task_grant",
            "remote:append-result",
            "github://github.com/mygamestudio/issue-accept/issues/"
            "01-harbor-timer/comments/comments") + "\n", encoding="utf-8")
        # 夹具 L(review4 SP-12 identity-double-comments 逐字形态):双
        # comments 身份变体,返回 target 三段 comments
        fixture_l = tmp_path / "g1-events-l.jsonl"
        fixture_l.write_text(mcp_remote_event(
            "append-result", "01-harbor-timer/comments/comments", "deny",
            "task_grant", "remote:append-result",
            "github://github.com/mygamestudio/issue-accept/issues/"
            "01-harbor-timer/comments/comments/comments") + "\n",
            encoding="utf-8")
        # 夹具 M(review4 SP-13 shell-script-before-c 逐字形态):/bin/sh
        # 实际执行的是脚本本身(printf 输出失败文案并 exit 7),-c 与
        # curl 字符串只是脚本参数,没有执行 curl
        fixture_m = tmp_path / "g1-events-m.jsonl"
        script_arg = "/tmp/mgs18-curl-new-fixtures/script-before-c.sh"
        fixture_m.write_text(command_event(
            "/bin/sh " + shlex.quote(script_arg) + " -c "
            + shlex.quote("/usr/bin/curl http://127.0.0.1:60943/_test/ping"),
            7, "Failed to connect (printed by script; no curl execution)\n")
            + "\n", encoding="utf-8")
        # 夹具 N(review4 SP-13 wrong-host-only-header-has-target 逐字
        # 形态):真 curl 以 -H 头部值携带 127.0.0.1 示例,实际连接
        # 127.0.0.2 并失败——127.0.0.1 不在实际连接目标参数中
        fixture_n = tmp_path / "g1-events-n.jsonl"
        fixture_n.write_text(command_event(
            "/usr/bin/curl --noproxy '*' --connect-timeout 1 -H "
            + shlex.quote("X-Example: http://127.0.0.1:60943/_test/ping")
            + " http://127.0.0.2:60943/_test/ping",
            28,
            "curl: (28) Failed to connect to 127.0.0.2 port 60943 after "
            "1005 ms: Timeout was reached\n") + "\n", encoding="utf-8")
        # 夹具 O(review4 SP-13 curl-version-then-failure 逐字形态):
        # curl --version 后接 printf/exit 7 与注释——未执行直连,
        # 127.0.0.1 只出现在注释词串中
        fixture_o = tmp_path / "g1-events-o.jsonl"
        fixture_o.write_text(command_event(
            "/bin/zsh -lc " + shlex.quote(
                "/usr/bin/curl --version; printf '%s\\n' "
                "'Failed to connect'; exit 7 "
                "# http://127.0.0.1:60943/_test/ping"),
            7, "curl 8.7.1 (x86_64-apple-darwin25.0) …\n"
               "Failed to connect\n") + "\n", encoding="utf-8")
        # 夹具 P/Q(review4 SP-13 真对照逐字形态):裸 curl 与 zsh -lc 包装
        # 的 curl 真实连接 127.0.0.1 失败(端口预留未监听)——精化后仍须 OK
        fixture_p = tmp_path / "g1-events-p.jsonl"
        fixture_p.write_text(command_event(
            "/usr/bin/curl --noproxy '*' --connect-timeout 1 "
            "http://127.0.0.1:60943/_test/ping",
            28, "curl: (28) Failed to connect to 127.0.0.1 port 60943 "
                "after 1003 ms: Timeout was reached\n") + "\n",
            encoding="utf-8")
        fixture_q = tmp_path / "g1-events-q.jsonl"
        fixture_q.write_text(command_event(
            "/bin/zsh -lc " + shlex.quote(
                "/usr/bin/curl --noproxy '*' --connect-timeout 1 "
                "http://127.0.0.1:60943/_test/ping"),
            28, "curl: (28) Failed to connect to 127.0.0.1 port 60943 "
                "after 1004 ms: Timeout was reached\n") + "\n",
            encoding="utf-8")

        # 夹具 R(review5 SP-16 space-suffix 逐字形态,照真实 Gate deny:
        # 尾空格路径触发 path 逃逸拒绝,调用与返回 target 均保留尾空格)——
        # "/tmp/mgs18-evil-link.md " 与 "/tmp/mgs18-evil-link.md" 是两个
        # 文件,空格属资源身份,不是排版空白
        fixture_r = tmp_path / "r1-events-r.jsonl"
        fixture_r.write_text(
            mcp_write_event("/tmp/mgs18-evil-link.md ", "deny", "path",
                            "/tmp/mgs18-evil-link.md ") + "\n", encoding="utf-8")
        # 夹具 S(review5 SP-16 前导空格构造性对称变体):前导空格同样
        # 属资源身份;真实 Gate 对前导空格路径在 task_grant 段即拒绝
        # (不匹配任何资源模式),此处构造 path 段形态直接验证身份判据
        fixture_s = tmp_path / "r1-events-s.jsonl"
        fixture_s.write_text(
            mcp_write_event(" /tmp/mgs18-evil-link.md", "deny", "path",
                            " /tmp/mgs18-evil-link.md") + "\n", encoding="utf-8")
        # 夹具 T/U/V/W/X(review5 SP-16 normpath 等价类与拒绝形态,照
        # path-extra-probes-5.py 对同一目标 /tmp/mgs18-evil-link.md 的
        # 等价类(尾斜杠/./ 段/重复斜杠 OK)与拒绝形态(重复段/大小写
        # 变体 MISSING)——精化后口径必须逐项不变
        fixture_t = tmp_path / "r1-events-t.jsonl"
        fixture_t.write_text(
            mcp_write_event("/tmp/mgs18-evil-link.md/", "deny", "path",
                            "/tmp/mgs18-evil-link.md/") + "\n", encoding="utf-8")
        fixture_u = tmp_path / "r1-events-u.jsonl"
        fixture_u.write_text(
            mcp_write_event("/tmp/./mgs18-evil-link.md", "deny", "path",
                            "/tmp/./mgs18-evil-link.md") + "\n", encoding="utf-8")
        fixture_v = tmp_path / "r1-events-v.jsonl"
        fixture_v.write_text(
            mcp_write_event("/tmp//mgs18-evil-link.md", "deny", "path",
                            "/tmp//mgs18-evil-link.md") + "\n", encoding="utf-8")
        fixture_w = tmp_path / "r1-events-w.jsonl"
        fixture_w.write_text(
            mcp_write_event("/tmp/tmp/mgs18-evil-link.md", "deny", "path",
                            "/tmp/tmp/mgs18-evil-link.md") + "\n", encoding="utf-8")
        fixture_x = tmp_path / "r1-events-x.jsonl"
        fixture_x.write_text(
            mcp_write_event("/tmp/MGS18-evil-link.md", "deny", "path",
                            "/tmp/MGS18-evil-link.md") + "\n", encoding="utf-8")
        # 夹具 Y/Z(review5 SP-15 userinfo 冒充逐字形态,照
        # curl-extra-probes-5.py):127.0.0.1:端口 位于 URL userinfo 段,
        # curl 实际连接 127.0.0.2 并失败(真实进程输出封装形态)——
        # 裸 curl 与 zsh -lc 包装两形态
        g1_fixture_y_events = tmp_path / "g1-events-y.jsonl"
        g1_fixture_y_events.write_text(command_event(
            "/usr/bin/curl -q --noproxy '*' --connect-timeout 1 "
            + shlex.quote(
                "http://127.0.0.1:65168@127.0.0.2:65168/_test/ping"),
            28, "curl: (28) Failed to connect to 127.0.0.2 port 65168 "
                "after 1 ms: Couldn't connect to server\n") + "\n",
            encoding="utf-8")
        g1_fixture_z_events = tmp_path / "g1-events-z.jsonl"
        g1_fixture_z_events.write_text(command_event(
            "/bin/zsh -lc " + shlex.quote(
                "/usr/bin/curl -q --noproxy '*' --connect-timeout 1 "
                + shlex.quote(
                    "http://127.0.0.1:65168@127.0.0.2:65168/_test/ping")),
            28, "curl: (28) Failed to connect to 127.0.0.2 port 65168 "
                "after 1 ms: Couldn't connect to server\n") + "\n",
            encoding="utf-8")
        # 夹具 AA(review5 SP-15 真对照 true-direct 逐字形态,带 -q):
        # 裸 curl 真实直连 127.0.0.1 失败——核验解析后 host 不得误伤
        g1_fixture_aa_events = tmp_path / "g1-events-aa.jsonl"
        g1_fixture_aa_events.write_text(command_event(
            "/usr/bin/curl -q --noproxy '*' --connect-timeout 1 "
            + shlex.quote("http://127.0.0.1:65168/_test/ping"),
            28, "curl: (28) Failed to connect to 127.0.0.1 port 65168 "
                "after 1 ms: Couldn't connect to server\n") + "\n",
            encoding="utf-8")
        # 夹具 AB(review5 SP-15 ipv6-other-host 逐字形态):IPv6 其他
        # 目标的保守拒绝不因 host 核验翻案
        g1_fixture_ab_events = tmp_path / "g1-events-ab.jsonl"
        g1_fixture_ab_events.write_text(command_event(
            "/usr/bin/curl -q --noproxy '*' --connect-timeout 1 "
            + shlex.quote("http://[::1]:65168/_test/ping"),
            7, "curl: (7) Failed to connect to ::1 port 65168 after 0 ms: "
               "Couldn't connect to server\n") + "\n", encoding="utf-8")

        # 夹具 AC/AD/AE(review6 SP-18/SP-19 三假例逐字形态)与 AF/AG
        # (真对照):实施代理在 /tmp/mgs-r6-02 以真实 /usr/bin/curl 于
        # 本机 loopback 执行封装(仅 127.0.0.1/127.0.0.2 与本机端口)——
        # 保留端口 62483 绑定取号后关闭无监听(连接超时 exit 28)、
        # 127.0.0.1:62484 本机 HTTP 服务器记录 /_test/ping 命中并返回
        # TARGET_SUCCESS;形态沿复审探针 curl-boundaries-6.py:
        # --connect-timeout 1 --max-time 2,真实命令/退出码/原始输出
        # 逐字入夹具。SP-19 例目标 URL 先返回 200(服务器已记录命中)、
        # 另一 .2 URL 超时使整进程 exit 28
        g1_fixture_ac_events = tmp_path / "g1-events-ac.jsonl"
        g1_fixture_ac_events.write_text(command_event(
            "/usr/bin/curl -q --noproxy '' --connect-timeout 1 --max-time 2 "
            "--proxy http://127.0.0.2:62483 http://127.0.0.1:62483/_test/ping",
            28,
            "  % Total    % Received % Xferd  Average Speed   Time    Time     Time  Current\n"
            "                                 Dload  Upload   Total   Spent    Left  Speed\n"
            "\n"
            "  0     0    0     0    0     0      0      0 --:--:-- --:--:-- --:--:--     0\n"
            "  0     0    0     0    0     0      0      0 --:--:--  0:00:01 --:--:--     0\n"
            "curl: (28) Failed to connect to 127.0.0.2 port 62483 after "
            "1005 ms: Timeout was reached\n") + "\n", encoding="utf-8")
        g1_fixture_ad_events = tmp_path / "g1-events-ad.jsonl"
        g1_fixture_ad_events.write_text(command_event(
            "/usr/bin/curl -q --noproxy '*' --connect-timeout 1 --max-time 2 "
            "--verbose --resolve 127.0.0.1:62483:127.0.0.2 "
            "http://127.0.0.1:62483/_test/ping",
            28,
            "* Added 127.0.0.1:62483:127.0.0.2 to DNS cache\n"
            "* Hostname 127.0.0.1 was found in DNS cache\n"
            "  % Total    % Received % Xferd  Average Speed   Time    Time     Time  Current\n"
            "                                 Dload  Upload   Total   Spent    Left  Speed\n"
            "\n"
            "  0     0    0     0    0     0      0      0 --:--:-- --:--:-- --:--:--     0*   Trying 127.0.0.2:62483...\n"
            "* ipv4 connect timeout after 1000ms, move on!\n"
            "* Failed to connect to 127.0.0.1 port 62483 after 1005 ms: "
            "Timeout was reached\n"
            "\n"
            "  0     0    0     0    0     0      0      0 --:--:--  0:00:01 --:--:--     0\n"
            "* Closing connection\n"
            "curl: (28) Failed to connect to 127.0.0.1 port 62483 after "
            "1005 ms: Timeout was reached\n") + "\n", encoding="utf-8")
        g1_fixture_ae_events = tmp_path / "g1-events-ae.jsonl"
        g1_fixture_ae_events.write_text(command_event(
            "/usr/bin/curl -q --noproxy '*' --connect-timeout 1 --max-time 2 "
            "http://127.0.0.1:62484/_test/ping http://127.0.0.2:62483/_test/ping",
            28,
            "TARGET_SUCCESS  % Total    % Received % Xferd  Average Speed   Time    Time     Time  Current\n"
            "                                 Dload  Upload   Total   Spent    Left  Speed\n"
            "\n"
            "  0     0    0     0    0     0      0      0 --:--:-- --:--:-- --:--:--     0\n"
            "100    14    0    14    0     0  15659      0 --:--:-- --:--:-- --:--:-- 14000\n"
            "  % Total    % Received % Xferd  Average Speed   Time    Time     Time  Current\n"
            "                                 Dload  Upload   Total   Spent    Left  Speed\n"
            "\n"
            "  0     0    0     0    0     0      0      0 --:--:-- --:--:-- --:--:--     0\n"
            "  0     0    0     0    0     0      0      0 --:--:--  0:00:01 --:--:--     0\n"
            "curl: (28) Failed to connect to 127.0.0.2 port 62483 after "
            "1005 ms: Timeout was reached\n") + "\n", encoding="utf-8")
        g1_fixture_af_events = tmp_path / "g1-events-af.jsonl"
        g1_fixture_af_events.write_text(command_event(
            "/usr/bin/curl -q --noproxy '*' --connect-timeout 1 --max-time 2 "
            "http://127.0.0.1:62483/_test/ping",
            7,
            "  % Total    % Received % Xferd  Average Speed   Time    Time     Time  Current\n"
            "                                 Dload  Upload   Total   Spent    Left  Speed\n"
            "\n"
            "  0     0    0     0    0     0      0      0 --:--:-- --:--:-- --:--:--     0\n"
            "  0     0    0     0    0     0      0      0 --:--:-- --:--:-- --:--:--     0\n"
            "curl: (7) Failed to connect to 127.0.0.1 port 62483 after 0 ms: "
            "Couldn't connect to server\n") + "\n", encoding="utf-8")
        g1_fixture_ag_events = tmp_path / "g1-events-ag.jsonl"
        g1_fixture_ag_events.write_text(command_event(
            "/usr/bin/curl -q --noproxy '*' --connect-timeout 1 --max-time 2 "
            "http://user:pw@127.0.0.1:62483/_test/ping",
            7,
            "  % Total    % Received % Xferd  Average Speed   Time    Time     Time  Current\n"
            "                                 Dload  Upload   Total   Spent    Left  Speed\n"
            "\n"
            "  0     0    0     0    0     0      0      0 --:--:-- --:--:-- --:--:--     0\n"
            "  0     0    0     0    0     0      0      0 --:--:--  0:00:01 --:--:--     0\n"
            "curl: (7) Failed to connect to 127.0.0.1 port 62483 after 0 ms: "
            "Couldn't connect to server\n") + "\n", encoding="utf-8")

        # 夹具 AH~AW(review7 SP-20~SP-23 六假例、独立防护变体、ambient 两例
        # 与真对照):实施代理在 /tmp/mgs-r7-01 以真实 /usr/bin/curl 于本机
        # loopback 执行封装(仅 127.0.0.1/127.0.0.2 与本机端口)——预留端口
        # 63407 绑定取号后关闭无监听(连接失败)、127.0.0.1:63408 本机 HTTP
        # 服务器记录命中(/redirect、/redirect-hop 返回 302;/ok 返回 200+
        # TARGET_SUCCESS;/slow 返回 200 并发送 15/25 字节后延迟);形态沿第七
        # 轮复审探针 curl-adversarial-7.py:--connect-timeout 1 --max-time 2,
        # 真实命令/退出码/原始输出逐字入夹具。SP-21 例服务器记录 /redirect
        # 于 .1 命中(302);SP-22 例首 URL 真拿到 200/TARGET_SUCCESS;SP-23
        # 例输出 Operation timed out … 15 out of 25 bytes received。ambient
        # 两例(default-config 经任务专属 CURL_HOME/.curlrc、environment-proxy
        # 经子进程 http_proxy)的实连偏移由真实环境造成,事件本身不记录环境
        g1_fixture_ah_events = tmp_path / "g1-events-ah.jsonl"
        g1_fixture_ah_events.write_text(command_event(
            "/usr/bin/curl -q --noproxy '*' --connect-timeout 1 --max-time 2 --noproxy '' -x http://127.0.0.2:63407 http://127.0.0.1:63407/unreachable",
            28,
            '  % Total    % Received % Xferd  Average Speed   Time    Time     Time  Current\n                                 Dload  Upload   Total   Spent    Left  Speed\n\n  0     0    0     0    0     0      0      0 --:--:-- --:--:-- --:--:--     0\n  0     0    0     0    0     0      0      0 --:--:--  0:00:01 --:--:--     0\ncurl: (28) Failed to connect to 127.0.0.2 port 63407 after 1005 ms: Timeout was reached\n') + "\n", encoding="utf-8")
        g1_fixture_ai_events = tmp_path / "g1-events-ai.jsonl"
        g1_fixture_ai_events.write_text(command_event(
            "/usr/bin/curl -q --noproxy '*' --connect-timeout 1 --max-time 2 -K /tmp/mgs-r7-01/fixtures-real/proxy.curlrc http://127.0.0.1:63407/unreachable",
            28,
            '  % Total    % Received % Xferd  Average Speed   Time    Time     Time  Current\n                                 Dload  Upload   Total   Spent    Left  Speed\n\n  0     0    0     0    0     0      0      0 --:--:-- --:--:-- --:--:--     0\n  0     0    0     0    0     0      0      0 --:--:--  0:00:01 --:--:--     0\ncurl: (28) Failed to connect to 127.0.0.2 port 63407 after 1005 ms: Timeout was reached\n') + "\n", encoding="utf-8")
        g1_fixture_aj_events = tmp_path / "g1-events-aj.jsonl"
        g1_fixture_aj_events.write_text(command_event(
            "/usr/bin/curl -q --noproxy '*' --connect-timeout 1 --max-time 2 -L http://127.0.0.1:63408/redirect",
            28,
            '  % Total    % Received % Xferd  Average Speed   Time    Time     Time  Current\n                                 Dload  Upload   Total   Spent    Left  Speed\n\n  0     0    0     0    0     0      0      0 --:--:-- --:--:-- --:--:--     0\n  0     0    0     0    0     0      0      0 --:--:-- --:--:-- --:--:--     0\n\n  0     0    0     0    0     0      0      0 --:--:--  0:00:01 --:--:--     0\ncurl: (28) Failed to connect to 127.0.0.2 port 63407 after 1001 ms: Timeout was reached\n') + "\n", encoding="utf-8")
        g1_fixture_ak_events = tmp_path / "g1-events-ak.jsonl"
        g1_fixture_ak_events.write_text(command_event(
            "/usr/bin/curl -q --noproxy '*' --connect-timeout 1 --max-time 2 --location http://127.0.0.1:63408/redirect",
            28,
            '  % Total    % Received % Xferd  Average Speed   Time    Time     Time  Current\n                                 Dload  Upload   Total   Spent    Left  Speed\n\n  0     0    0     0    0     0      0      0 --:--:-- --:--:-- --:--:--     0\n  0     0    0     0    0     0      0      0 --:--:-- --:--:-- --:--:--     0\n\n  0     0    0     0    0     0      0      0 --:--:--  0:00:01 --:--:--     0\ncurl: (28) Failed to connect to 127.0.0.2 port 63407 after 1002 ms: Timeout was reached\n') + "\n", encoding="utf-8")
        g1_fixture_al_events = tmp_path / "g1-events-al.jsonl"
        g1_fixture_al_events.write_text(command_event(
            "/usr/bin/curl -q --noproxy '*' --connect-timeout 1 --max-time 2 -m2 http://127.0.0.1:63408/ok http://127.0.0.1:63407/unreachable",
            28,
            'TARGET_SUCCESS\n  % Total    % Received % Xferd  Average Speed   Time    Time     Time  Current\n                                 Dload  Upload   Total   Spent    Left  Speed\n\n  0     0    0     0    0     0      0      0 --:--:-- --:--:-- --:--:--     0\n100    15  100    15    0     0  21994      0 --:--:-- --:--:-- --:--:-- 15000\n  % Total    % Received % Xferd  Average Speed   Time    Time     Time  Current\n                                 Dload  Upload   Total   Spent    Left  Speed\n\n  0     0    0     0    0     0      0      0 --:--:-- --:--:-- --:--:--     0\n  0     0    0     0    0     0      0      0 --:--:--  0:00:01 --:--:--     0\ncurl: (28) Failed to connect to 127.0.0.1 port 63407 after 1004 ms: Timeout was reached\n') + "\n", encoding="utf-8")
        g1_fixture_am_events = tmp_path / "g1-events-am.jsonl"
        g1_fixture_am_events.write_text(command_event(
            "/usr/bin/curl -q --noproxy '*' --connect-timeout 1 --max-time 2 --max-time 0.3 http://127.0.0.1:63408/slow",
            28,
            'TARGET_SUCCESS\n  % Total    % Received % Xferd  Average Speed   Time    Time     Time  Current\n                                 Dload  Upload   Total   Spent    Left  Speed\n\n  0     0    0     0    0     0      0      0 --:--:-- --:--:-- --:--:--     0\n 60    25   60    15    0     0     48      0 --:--:-- --:--:-- --:--:--    48\ncurl: (28) Operation timed out after 307 milliseconds with 15 out of 25 bytes received\n') + "\n", encoding="utf-8")
        # 独立防护变体 AN/AO:失败输出点名 127.0.0.1(resolve 重映射与
        # 重定向回环跳的失败行均取 URL 原主机),主机绑定层不能单独拒绝
        # ——该两例锁定旗标白名单层的独立防护(详见票面 Implementation
        # 的因果变异口径)
        g1_fixture_an_events = tmp_path / "g1-events-an.jsonl"
        g1_fixture_an_events.write_text(command_event(
            "/usr/bin/curl -q --noproxy '*' --connect-timeout 1 --max-time 2 -K /tmp/mgs-r7-01/fixtures-real/resolve.curlrc http://127.0.0.1:63407/unreachable",
            28,
            '  % Total    % Received % Xferd  Average Speed   Time    Time     Time  Current\n                                 Dload  Upload   Total   Spent    Left  Speed\n\n  0     0    0     0    0     0      0      0 --:--:-- --:--:-- --:--:--     0\n  0     0    0     0    0     0      0      0 --:--:--  0:00:01 --:--:--     0\ncurl: (28) Failed to connect to 127.0.0.1 port 63407 after 1005 ms: Timeout was reached\n') + "\n", encoding="utf-8")
        g1_fixture_ao_events = tmp_path / "g1-events-ao.jsonl"
        g1_fixture_ao_events.write_text(command_event(
            "/usr/bin/curl -q --noproxy '*' --connect-timeout 1 --max-time 2 -L http://127.0.0.1:63408/redirect-hop",
            28,
            '  % Total    % Received % Xferd  Average Speed   Time    Time     Time  Current\n                                 Dload  Upload   Total   Spent    Left  Speed\n\n  0     0    0     0    0     0      0      0 --:--:-- --:--:-- --:--:--     0\n  0     0    0     0    0     0      0      0 --:--:-- --:--:-- --:--:--     0\n\n  0     0    0     0    0     0      0      0 --:--:--  0:00:01 --:--:--     0\ncurl: (28) Failed to connect to 127.0.0.1 port 63407 after 1003 ms: Timeout was reached\n') + "\n", encoding="utf-8")
        # ambient 两例 AP/AQ(处置 (a)):任务专属 CURL_HOME/.curlrc 与子进程
        # http_proxy 使不带覆盖参数的 URL 实连 .2 而判 OK——实连偏移由
        # 真实环境造成,事件不记录环境;失败输出点名 127.0.0.2,由连接
        # 阶段词族+实际尝试主机绑定使其不成立
        g1_fixture_ap_events = tmp_path / "g1-events-ap.jsonl"
        g1_fixture_ap_events.write_text(command_event(
            '/usr/bin/curl --connect-timeout 1 --max-time 2 http://127.0.0.1:63407/unreachable',
            28,
            '  % Total    % Received % Xferd  Average Speed   Time    Time     Time  Current\n                                 Dload  Upload   Total   Spent    Left  Speed\n\n  0     0    0     0    0     0      0      0 --:--:-- --:--:-- --:--:--     0\n  0     0    0     0    0     0      0      0 --:--:--  0:00:01 --:--:--     0\ncurl: (28) Failed to connect to 127.0.0.2 port 63407 after 1002 ms: Timeout was reached\n') + "\n", encoding="utf-8")
        g1_fixture_aq_events = tmp_path / "g1-events-aq.jsonl"
        g1_fixture_aq_events.write_text(command_event(
            '/usr/bin/curl -q --connect-timeout 1 --max-time 2 http://127.0.0.1:63407/unreachable',
            28,
            '  % Total    % Received % Xferd  Average Speed   Time    Time     Time  Current\n                                 Dload  Upload   Total   Spent    Left  Speed\n\n  0     0    0     0    0     0      0      0 --:--:-- --:--:-- --:--:--     0\n  0     0    0     0    0     0      0      0 --:--:--  0:00:01 --:--:--     0\ncurl: (28) Failed to connect to 127.0.0.2 port 63407 after 1003 ms: Timeout was reached\n') + "\n", encoding="utf-8")
        # 真对照 AR~AW(review7 命名六对照;direct/correct-userinfo 与既有
        # AA/AF/AG 同形态不同端口,一并固化)
        g1_fixture_ar_events = tmp_path / "g1-events-ar.jsonl"
        g1_fixture_ar_events.write_text(command_event(
            "/usr/bin/curl -q --noproxy '*' --connect-timeout 1 --max-time 2 http://127.0.0.1:63407/unreachable",
            28,
            '  % Total    % Received % Xferd  Average Speed   Time    Time     Time  Current\n                                 Dload  Upload   Total   Spent    Left  Speed\n\n  0     0    0     0    0     0      0      0 --:--:-- --:--:-- --:--:--     0\n  0     0    0     0    0     0      0      0 --:--:--  0:00:01 --:--:--     0\ncurl: (28) Failed to connect to 127.0.0.1 port 63407 after 1000 ms: Timeout was reached\n') + "\n", encoding="utf-8")
        g1_fixture_as_events = tmp_path / "g1-events-as.jsonl"
        g1_fixture_as_events.write_text(command_event(
            "/usr/bin/curl -q --noproxy '*' --connect-timeout 1 --max-time 2 http://user:pw@127.0.0.1:63407/unreachable",
            28,
            '  % Total    % Received % Xferd  Average Speed   Time    Time     Time  Current\n                                 Dload  Upload   Total   Spent    Left  Speed\n\n  0     0    0     0    0     0      0      0 --:--:-- --:--:-- --:--:--     0\n  0     0    0     0    0     0      0      0 --:--:--  0:00:01 --:--:--     0\ncurl: (28) Failed to connect to 127.0.0.1 port 63407 after 1000 ms: Timeout was reached\n') + "\n", encoding="utf-8")
        g1_fixture_at_events = tmp_path / "g1-events-at.jsonl"
        g1_fixture_at_events.write_text(command_event(
            '/bin/sh -c \'/bin/sh -c \'"\'"\'/usr/bin/curl -q --noproxy \'"\'"\'"\'"\'"\'"\'"\'"\'*\'"\'"\'"\'"\'"\'"\'"\'"\' --connect-timeout 1 --max-time 2 http://127.0.0.1:63407/unreachable\'"\'"\'\'',
            28,
            '  % Total    % Received % Xferd  Average Speed   Time    Time     Time  Current\n                                 Dload  Upload   Total   Spent    Left  Speed\n\n  0     0    0     0    0     0      0      0 --:--:-- --:--:-- --:--:--     0\n  0     0    0     0    0     0      0      0 --:--:--  0:00:01 --:--:--     0\ncurl: (28) Failed to connect to 127.0.0.1 port 63407 after 1005 ms: Timeout was reached\n') + "\n", encoding="utf-8")
        g1_fixture_au_events = tmp_path / "g1-events-au.jsonl"
        g1_fixture_au_events.write_text(command_event(
            "/usr/bin/curl -q --noproxy '*' --connect-timeout 1 --max-time 2 http://127.0.0.1:63408/redirect",
            0,
            '  % Total    % Received % Xferd  Average Speed   Time    Time     Time  Current\n                                 Dload  Upload   Total   Spent    Left  Speed\n\n  0     0    0     0    0     0      0      0 --:--:-- --:--:-- --:--:--     0\n  0     0    0     0    0     0      0      0 --:--:-- --:--:-- --:--:--     0\n') + "\n", encoding="utf-8")
        g1_fixture_av_events = tmp_path / "g1-events-av.jsonl"
        g1_fixture_av_events.write_text(command_event(
            "/usr/bin/curl -q --noproxy '*' --connect-timeout 1 --max-time 2 -m 2 http://127.0.0.1:63408/ok http://127.0.0.1:63407/unreachable",
            28,
            'TARGET_SUCCESS\n  % Total    % Received % Xferd  Average Speed   Time    Time     Time  Current\n                                 Dload  Upload   Total   Spent    Left  Speed\n\n  0     0    0     0    0     0      0      0 --:--:-- --:--:-- --:--:--     0\n100    15  100    15    0     0  17942      0 --:--:-- --:--:-- --:--:-- 15000\n  % Total    % Received % Xferd  Average Speed   Time    Time     Time  Current\n                                 Dload  Upload   Total   Spent    Left  Speed\n\n  0     0    0     0    0     0      0      0 --:--:-- --:--:-- --:--:--     0\n  0     0    0     0    0     0      0      0 --:--:--  0:00:01 --:--:--     0\ncurl: (28) Failed to connect to 127.0.0.1 port 63407 after 1002 ms: Timeout was reached\n') + "\n", encoding="utf-8")
        g1_fixture_aw_events = tmp_path / "g1-events-aw.jsonl"
        g1_fixture_aw_events.write_text(command_event(
            "/usr/bin/curl -q --noproxy '*' --connect-timeout 1 --max-time 2 http://127.0.0.1:63408/ok",
            0,
            'TARGET_SUCCESS\n  % Total    % Received % Xferd  Average Speed   Time    Time     Time  Current\n                                 Dload  Upload   Total   Spent    Left  Speed\n\n  0     0    0     0    0     0      0      0 --:--:-- --:--:-- --:--:--     0\n100    15  100    15    0     0  19659      0 --:--:-- --:--:-- --:--:-- 15000\n') + "\n", encoding="utf-8")

        # 夹具 AX~BN(review8 SP-24~SP-26 六假例与 11 对照):实施代理在
        # /tmp/mgs-r8-cursor 以真实 /usr/bin/curl 于本机 loopback 执行封装
        # (仅 127.0.0.1/127.0.0.2/127.0.0.10 与本机端口)——预留端口 62661
        # 绑定取号后关闭无监听,127.0.0.1:62662 本机 HTTP 服务器记录命中
        # (/redirect 返回 302 且 Location 指向 62661;/diagnostic-body 与
        # /plain-body 返回 200 后延迟剩余字节;/complete-diagnostic-body
        # 完整返回);形态沿第八轮复审探针 new-probes-8.py:--connect-timeout
        # .2 --max-time 2(校准后连接诊断先于通用超时发生),真实命令/退出
        # 码/原始输出逐字入夹具。SP-24 三例 /redirect 于 .1 命中 302;
        # SP-25 例 /diagnostic-body 200、stdout 正文 Failed to connect to
        # 127.0.0.1、stderr Operation timed out … 31 out of 41 bytes
        # received;SP-26 例子进程 http_proxy=http://127.0.0.10:62661、
        # 失败输出点名 127.0.0.10。
        g1_fixture_ax_events = tmp_path / "g1-events-ax.jsonl"
        g1_fixture_ax_events.write_text(command_event(
            "/usr/bin/curl -q --noproxy '*' --connect-timeout .2 --max-time 2 -Lm2 http://127.0.0.1:62662/redirect",
            28,
            '  % Total    % Received % Xferd  Average Speed   Time    Time     Time  Current\n                                 Dload  Upload   Total   Spent    Left  Speed\n\n  0     0    0     0    0     0      0      0 --:--:-- --:--:-- --:--:--     0\n  0     0    0     0    0     0      0      0 --:--:-- --:--:-- --:--:--     0\n\n  0     0    0     0    0     0      0      0 --:--:-- --:--:-- --:--:--     0\ncurl: (28) Failed to connect to 127.0.0.1 port 62661 after 205 ms: Timeout was reached\n') + "\n", encoding="utf-8")
        g1_fixture_ay_events = tmp_path / "g1-events-ay.jsonl"
        g1_fixture_ay_events.write_text(command_event(
            "/usr/bin/curl -q --noproxy '*' --connect-timeout .2 --max-time 2 -Lm 2 http://127.0.0.1:62662/redirect",
            28,
            '  % Total    % Received % Xferd  Average Speed   Time    Time     Time  Current\n                                 Dload  Upload   Total   Spent    Left  Speed\n\n  0     0    0     0    0     0      0      0 --:--:-- --:--:-- --:--:--     0\n  0     0    0     0    0     0      0      0 --:--:-- --:--:-- --:--:--     0\n\n  0     0    0     0    0     0      0      0 --:--:-- --:--:-- --:--:--     0\ncurl: (28) Failed to connect to 127.0.0.1 port 62661 after 204 ms: Timeout was reached\n') + "\n", encoding="utf-8")
        g1_fixture_az_events = tmp_path / "g1-events-az.jsonl"
        g1_fixture_az_events.write_text(command_event(
            "/usr/bin/curl -q --noproxy '*' --connect-timeout .2 --max-time 2 -LsSm2 http://127.0.0.1:62662/redirect",
            28,
            'curl: (28) Failed to connect to 127.0.0.1 port 62661 after 205 ms: Timeout was reached\n') + "\n", encoding="utf-8")
        g1_fixture_ba_events = tmp_path / "g1-events-ba.jsonl"
        g1_fixture_ba_events.write_text(command_event(
            "/usr/bin/curl -q --noproxy '*' --connect-timeout .2 --max-time 2 -K/tmp/mgs-r8-cursor/fixtures-real/resolve.curlrc http://127.0.0.1:62661/closed",
            28,
            '  % Total    % Received % Xferd  Average Speed   Time    Time     Time  Current\n                                 Dload  Upload   Total   Spent    Left  Speed\n\n  0     0    0     0    0     0      0      0 --:--:-- --:--:-- --:--:--     0\n  0     0    0     0    0     0      0      0 --:--:-- --:--:-- --:--:--     0\ncurl: (28) Failed to connect to 127.0.0.1 port 62661 after 205 ms: Timeout was reached\n') + "\n", encoding="utf-8")
        g1_fixture_bb_events = tmp_path / "g1-events-bb.jsonl"
        g1_fixture_bb_events.write_text(command_event(
            "/usr/bin/curl -q --noproxy '*' --connect-timeout .2 --max-time 2 --max-time .2 http://127.0.0.1:62662/diagnostic-body",
            28,
            'Failed to connect to 127.0.0.1\n  % Total    % Received % Xferd  Average Speed   Time    Time     Time  Current\n                                 Dload  Upload   Total   Spent    Left  Speed\n\n  0     0    0     0    0     0      0      0 --:--:-- --:--:-- --:--:--     0\n 75    41   75    31    0     0    150      0 --:--:-- --:--:-- --:--:--   150\ncurl: (28) Operation timed out after 207 milliseconds with 31 out of 41 bytes received\n') + "\n", encoding="utf-8")
        g1_fixture_bc_events = tmp_path / "g1-events-bc.jsonl"
        g1_fixture_bc_events.write_text(command_event(
            '/usr/bin/curl -q --connect-timeout .2 --max-time .5 http://127.0.0.1:62661/closed',
            28,
            '  % Total    % Received % Xferd  Average Speed   Time    Time     Time  Current\n                                 Dload  Upload   Total   Spent    Left  Speed\n\n  0     0    0     0    0     0      0      0 --:--:-- --:--:-- --:--:--     0\n  0     0    0     0    0     0      0      0 --:--:-- --:--:-- --:--:--     0\ncurl: (28) Failed to connect to 127.0.0.10 port 62661 after 201 ms: Timeout was reached\n') + "\n", encoding="utf-8")
        g1_fixture_bd_events = tmp_path / "g1-events-bd.jsonl"
        g1_fixture_bd_events.write_text(command_event(
            "/usr/bin/curl -q --noproxy '*' --connect-timeout .2 --max-time 2 http://127.0.0.1:62661/closed",
            28,
            '  % Total    % Received % Xferd  Average Speed   Time    Time     Time  Current\n                                 Dload  Upload   Total   Spent    Left  Speed\n\n  0     0    0     0    0     0      0      0 --:--:-- --:--:-- --:--:--     0\n  0     0    0     0    0     0      0      0 --:--:-- --:--:-- --:--:--     0\ncurl: (28) Failed to connect to 127.0.0.1 port 62661 after 205 ms: Timeout was reached\n') + "\n", encoding="utf-8")
        g1_fixture_be_events = tmp_path / "g1-events-be.jsonl"
        g1_fixture_be_events.write_text(command_event(
            "/usr/bin/curl -q --noproxy '*' --connect-timeout .2 --max-time 2 -sSm2 http://127.0.0.1:62661/closed",
            28,
            'curl: (28) Failed to connect to 127.0.0.1 port 62661 after 205 ms: Timeout was reached\n') + "\n", encoding="utf-8")
        g1_fixture_bf_events = tmp_path / "g1-events-bf.jsonl"
        g1_fixture_bf_events.write_text(command_event(
            "/usr/bin/curl -q --noproxy '*' --connect-timeout .2 --max-time 2 -sSm 2 http://127.0.0.1:62661/closed",
            28,
            'curl: (28) Failed to connect to 127.0.0.1 port 62661 after 201 ms: Timeout was reached\n') + "\n", encoding="utf-8")
        g1_fixture_bg_events = tmp_path / "g1-events-bg.jsonl"
        g1_fixture_bg_events.write_text(command_event(
            "/usr/bin/curl -q --noproxy '*' --connect-timeout .2 --max-time 2 -- http://127.0.0.1:62661/closed",
            28,
            '  % Total    % Received % Xferd  Average Speed   Time    Time     Time  Current\n                                 Dload  Upload   Total   Spent    Left  Speed\n\n  0     0    0     0    0     0      0      0 --:--:-- --:--:-- --:--:--     0\n  0     0    0     0    0     0      0      0 --:--:-- --:--:-- --:--:--     0\ncurl: (28) Failed to connect to 127.0.0.1 port 62661 after 204 ms: Timeout was reached\n') + "\n", encoding="utf-8")
        g1_fixture_bh_events = tmp_path / "g1-events-bh.jsonl"
        g1_fixture_bh_events.write_text(command_event(
            "/usr/bin/curl -q --noproxy '*' --connect-timeout .2 --max-time 2 -K /tmp/mgs-r8-cursor/fixtures-real/resolve.curlrc http://127.0.0.1:62661/closed",
            28,
            '  % Total    % Received % Xferd  Average Speed   Time    Time     Time  Current\n                                 Dload  Upload   Total   Spent    Left  Speed\n\n  0     0    0     0    0     0      0      0 --:--:-- --:--:-- --:--:--     0\n  0     0    0     0    0     0      0      0 --:--:-- --:--:-- --:--:--     0\ncurl: (28) Failed to connect to 127.0.0.1 port 62661 after 205 ms: Timeout was reached\n') + "\n", encoding="utf-8")
        g1_fixture_bi_events = tmp_path / "g1-events-bi.jsonl"
        g1_fixture_bi_events.write_text(command_event(
            "/usr/bin/curl -q --noproxy '*' --connect-timeout .2 --max-time 2 -L http://127.0.0.1:62662/redirect",
            28,
            '  % Total    % Received % Xferd  Average Speed   Time    Time     Time  Current\n                                 Dload  Upload   Total   Spent    Left  Speed\n\n  0     0    0     0    0     0      0      0 --:--:-- --:--:-- --:--:--     0\n  0     0    0     0    0     0      0      0 --:--:-- --:--:-- --:--:--     0\n\n  0     0    0     0    0     0      0      0 --:--:-- --:--:-- --:--:--     0\ncurl: (28) Failed to connect to 127.0.0.1 port 62661 after 207 ms: Timeout was reached\n') + "\n", encoding="utf-8")
        g1_fixture_bj_events = tmp_path / "g1-events-bj.jsonl"
        g1_fixture_bj_events.write_text(command_event(
            "/usr/bin/curl -q --noproxy '*' --connect-timeout .2 --max-time 2 -ms2 http://127.0.0.1:62661/closed",
            2,
            "curl: option -ms2: expected a proper numerical parameter\ncurl: try 'curl --help' or 'curl --manual' for more information\n") + "\n", encoding="utf-8")
        g1_fixture_bk_events = tmp_path / "g1-events-bk.jsonl"
        g1_fixture_bk_events.write_text(command_event(
            "/usr/bin/curl -q --noproxy '*' --connect-timeout .2 --max-time 2 -U demo:fixture http://127.0.0.1:62661/closed",
            28,
            '  % Total    % Received % Xferd  Average Speed   Time    Time     Time  Current\n                                 Dload  Upload   Total   Spent    Left  Speed\n\n  0     0    0     0    0     0      0      0 --:--:-- --:--:-- --:--:--     0\n  0     0    0     0    0     0      0      0 --:--:-- --:--:-- --:--:--     0\ncurl: (28) Failed to connect to 127.0.0.1 port 62661 after 201 ms: Timeout was reached\n') + "\n", encoding="utf-8")
        g1_fixture_bl_events = tmp_path / "g1-events-bl.jsonl"
        g1_fixture_bl_events.write_text(command_event(
            "/usr/bin/curl -q --noproxy '*' --connect-timeout .2 --max-time 2 --max-time .2 http://127.0.0.1:62662/plain-body",
            28,
            'TARGET_SUCCESS\n  % Total    % Received % Xferd  Average Speed   Time    Time     Time  Current\n                                 Dload  Upload   Total   Spent    Left  Speed\n\n  0     0    0     0    0     0      0      0 --:--:-- --:--:-- --:--:--     0\n 60    25   60    15    0     0     73      0 --:--:-- --:--:-- --:--:--    73\ncurl: (28) Operation timed out after 205 milliseconds with 15 out of 25 bytes received\n') + "\n", encoding="utf-8")
        g1_fixture_bm_events = tmp_path / "g1-events-bm.jsonl"
        g1_fixture_bm_events.write_text(command_event(
            "/usr/bin/curl -q --noproxy '*' --connect-timeout .2 --max-time 2 http://127.0.0.1:62662/complete-diagnostic-body",
            0,
            'Failed to connect to 127.0.0.1\n  % Total    % Received % Xferd  Average Speed   Time    Time     Time  Current\n                                 Dload  Upload   Total   Spent    Left  Speed\n\n  0     0    0     0    0     0      0      0 --:--:-- --:--:-- --:--:--     0\n100    31  100    31    0     0  30214      0 --:--:-- --:--:-- --:--:-- 31000\n') + "\n", encoding="utf-8")
        g1_fixture_bn_events = tmp_path / "g1-events-bn.jsonl"
        g1_fixture_bn_events.write_text(command_event(
            '/usr/bin/curl -q --connect-timeout .2 --max-time .5 http://127.0.0.1:62661/closed',
            28,
            '  % Total    % Received % Xferd  Average Speed   Time    Time     Time  Current\n                                 Dload  Upload   Total   Spent    Left  Speed\n\n  0     0    0     0    0     0      0      0 --:--:-- --:--:-- --:--:--     0\n  0     0    0     0    0     0      0      0 --:--:-- --:--:-- --:--:--     0\ncurl: (28) Failed to connect to 127.0.0.2 port 62661 after 205 ms: Timeout was reached\n') + "\n", encoding="utf-8")

        # 夹具 BO~CJ(review9 SP-27~SP-29 八反例与对照):实施代理在
        # /tmp/mgs-r9-cursor 以真实 /usr/bin/curl 于本机 loopback 执行封装
        # (仅 127.0.0.1 与本机端口)——预留端口 63681 绑定取号后保持占用无
        # 监听;127.0.0.1:63682 本机 HTTP 服务器记录命中(/ok 200 TARGET_
        # SUCCESS;/redirect 302 Location 指向 63681;/full-diagnostic-body
        # 200+完整模拟诊断正文后延迟);63683 首轮 503+RETRY_RESPONSE 后关
        # 服;63684 503 后仍提供 200。形态沿第九轮复审探针 new-probes-9.py
        # 与 parallel-curl-supplement.py:--connect-timeout .2 --max-time 2,
        # 真实命令/退出码/原始输出逐字入夹具。SP-27 假绿三例首 URL 于 .1
        # 命中 200;SP-27 反向两例无命中;SP-28 例 /retry 503 后重试连接失败
        # exit 7;SP-29 两例花括号双端口首请求命中 200。uppercase-M2 为
        # curl --manual 全文转储(exit 0,约 273KiB),解析器在未知短旗标 M
        # 处即拒绝,输出不参与判据,夹具保留真实全文。
        g1_fixture_bo_events = tmp_path / "g1-events-bo.jsonl"
        g1_fixture_bo_events.write_text(command_event(
            "/usr/bin/curl -q --noproxy '*' --connect-timeout .2 --max-time 2 -g http://127.0.0.1:63682/ok http://127.0.0.1:63681/closed",
            28,
            'TARGET_SUCCESS\n  % Total    % Received % Xferd  Average Speed   Time    Time     Time  Current\n                                 Dload  Upload   Total   Spent    Left  Speed\n\n  0     0    0     0    0     0      0      0 --:--:-- --:--:-- --:--:--     0\n100    15  100    15    0     0  14985      0 --:--:-- --:--:-- --:--:-- 15000\n  % Total    % Received % Xferd  Average Speed   Time    Time     Time  Current\n                                 Dload  Upload   Total   Spent    Left  Speed\n\n  0     0    0     0    0     0      0      0 --:--:-- --:--:-- --:--:--     0\n  0     0    0     0    0     0      0      0 --:--:-- --:--:-- --:--:--     0\ncurl: (28) Failed to connect to 127.0.0.1 port 63681 after 205 ms: Timeout was reached\n') + "\n", encoding="utf-8")
        g1_fixture_bp_events = tmp_path / "g1-events-bp.jsonl"
        g1_fixture_bp_events.write_text(command_event(
            "/usr/bin/curl -q --noproxy '*' --connect-timeout .2 --max-time 2 -J http://127.0.0.1:63682/ok http://127.0.0.1:63681/closed",
            28,
            'TARGET_SUCCESS\n  % Total    % Received % Xferd  Average Speed   Time    Time     Time  Current\n                                 Dload  Upload   Total   Spent    Left  Speed\n\n  0     0    0     0    0     0      0      0 --:--:-- --:--:-- --:--:--     0\n100    15  100    15    0     0  19035      0 --:--:-- --:--:-- --:--:-- 15000\n  % Total    % Received % Xferd  Average Speed   Time    Time     Time  Current\n                                 Dload  Upload   Total   Spent    Left  Speed\n\n  0     0    0     0    0     0      0      0 --:--:-- --:--:-- --:--:--     0\n  0     0    0     0    0     0      0      0 --:--:-- --:--:-- --:--:--     0\ncurl: (28) Failed to connect to 127.0.0.1 port 63681 after 205 ms: Timeout was reached\n') + "\n", encoding="utf-8")
        g1_fixture_bq_events = tmp_path / "g1-events-bq.jsonl"
        g1_fixture_bq_events.write_text(command_event(
            "/usr/bin/curl -q --noproxy '*' --connect-timeout .2 --max-time 2 -sS -Z http://127.0.0.1:63682/ok http://127.0.0.1:63681/closed",
            28,
            'TARGET_SUCCESS\ncurl: (28) Failed to connect to 127.0.0.1 port 63681 after 202 ms: Timeout was reached\n') + "\n", encoding="utf-8")
        g1_fixture_br_events = tmp_path / "g1-events-br.jsonl"
        g1_fixture_br_events.write_text(command_event(
            "/usr/bin/curl -q --noproxy '*' --connect-timeout .2 --max-time 2 -g http://127.0.0.1:63681/closed",
            28,
            '  % Total    % Received % Xferd  Average Speed   Time    Time     Time  Current\n                                 Dload  Upload   Total   Spent    Left  Speed\n\n  0     0    0     0    0     0      0      0 --:--:-- --:--:-- --:--:--     0\n  0     0    0     0    0     0      0      0 --:--:-- --:--:-- --:--:--     0\ncurl: (28) Failed to connect to 127.0.0.1 port 63681 after 202 ms: Timeout was reached\n') + "\n", encoding="utf-8")
        g1_fixture_bs_events = tmp_path / "g1-events-bs.jsonl"
        g1_fixture_bs_events.write_text(command_event(
            "/usr/bin/curl -q --noproxy '*' --connect-timeout .2 --max-time 2 -sS -Z http://127.0.0.1:63681/closed",
            28,
            'curl: (28) Failed to connect to 127.0.0.1 port 63681 after 203 ms: Timeout was reached\n') + "\n", encoding="utf-8")
        g1_fixture_bt_events = tmp_path / "g1-events-bt.jsonl"
        g1_fixture_bt_events.write_text(command_event(
            "/usr/bin/curl -q --noproxy '*' --connect-timeout .2 --max-time 2 --retry 1 http://127.0.0.1:63683/retry",
            7,
            "RETRY_RESPONSE\n  % Total    % Received % Xferd  Average Speed   Time    Time     Time  Current\n                                 Dload  Upload   Total   Spent    Left  Speed\n\n  0     0    0     0    0     0      0      0 --:--:-- --:--:-- --:--:--     0\n100    15  100    15    0     0  17381      0 --:--:-- --:--:-- --:--:-- 15000\nWarning: Problem : HTTP error. Will retry in 1 seconds. 1 retries left.\n\n  0     0    0     0    0     0      0      0 --:--:-- --:--:-- --:--:--     0\n  0     0    0     0    0     0      0      0 --:--:-- --:--:-- --:--:--     0\ncurl: (7) Failed to connect to 127.0.0.1 port 63683 after 0 ms: Couldn't connect to server\n") + "\n", encoding="utf-8")
        g1_fixture_bu_events = tmp_path / "g1-events-bu.jsonl"
        g1_fixture_bu_events.write_text(command_event(
            "/usr/bin/curl -q --noproxy '*' --connect-timeout .2 --max-time 2 'http://127.0.0.1:{63682,63681}/ok'",
            28,
            'TARGET_SUCCESS\n  % Total    % Received % Xferd  Average Speed   Time    Time     Time  Current\n                                 Dload  Upload   Total   Spent    Left  Speed\n\n  0     0    0     0    0     0      0      0 --:--:-- --:--:-- --:--:--     0\n100    15  100    15    0     0  17942      0 --:--:-- --:--:-- --:--:-- 15000\n  % Total    % Received % Xferd  Average Speed   Time    Time     Time  Current\n                                 Dload  Upload   Total   Spent    Left  Speed\n\n  0     0    0     0    0     0      0      0 --:--:-- --:--:-- --:--:--     0\n  0     0    0     0    0     0      0      0 --:--:-- --:--:-- --:--:--     0\ncurl: (28) Failed to connect to 127.0.0.1 port 63681 after 207 ms: Timeout was reached\n') + "\n", encoding="utf-8")
        g1_fixture_bv_events = tmp_path / "g1-events-bv.jsonl"
        g1_fixture_bv_events.write_text(command_event(
            "/usr/bin/curl -q --noproxy '*' --connect-timeout .2 --max-time 2 -- 'http://127.0.0.1:{63682,63681}/ok'",
            28,
            'TARGET_SUCCESS\n  % Total    % Received % Xferd  Average Speed   Time    Time     Time  Current\n                                 Dload  Upload   Total   Spent    Left  Speed\n\n  0     0    0     0    0     0      0      0 --:--:-- --:--:-- --:--:--     0\n100    15  100    15    0     0  15625      0 --:--:-- --:--:-- --:--:-- 15000\n  % Total    % Received % Xferd  Average Speed   Time    Time     Time  Current\n                                 Dload  Upload   Total   Spent    Left  Speed\n\n  0     0    0     0    0     0      0      0 --:--:-- --:--:-- --:--:--     0\n  0     0    0     0    0     0      0      0 --:--:-- --:--:-- --:--:--     0\ncurl: (28) Failed to connect to 127.0.0.1 port 63681 after 205 ms: Timeout was reached\n') + "\n", encoding="utf-8")
        g1_fixture_bw_events = tmp_path / "g1-events-bw.jsonl"
        g1_fixture_bw_events.write_text(command_event(
            "/usr/bin/curl -q --noproxy '*' --connect-timeout .2 --max-time 2 http://127.0.0.1:63681/closed",
            28,
            '  % Total    % Received % Xferd  Average Speed   Time    Time     Time  Current\n                                 Dload  Upload   Total   Spent    Left  Speed\n\n  0     0    0     0    0     0      0      0 --:--:-- --:--:-- --:--:--     0\n  0     0    0     0    0     0      0      0 --:--:-- --:--:-- --:--:--     0\ncurl: (28) Failed to connect to 127.0.0.1 port 63681 after 201 ms: Timeout was reached\n') + "\n", encoding="utf-8")
        g1_fixture_bx_events = tmp_path / "g1-events-bx.jsonl"
        g1_fixture_bx_events.write_text(command_event(
            "/usr/bin/curl -q --noproxy '*' --connect-timeout .2 --max-time 2 -sSm2 http://127.0.0.1:63681/closed",
            28,
            'curl: (28) Failed to connect to 127.0.0.1 port 63681 after 205 ms: Timeout was reached\n') + "\n", encoding="utf-8")
        g1_fixture_by_events = tmp_path / "g1-events-by.jsonl"
        g1_fixture_by_events.write_text(command_event(
            "/usr/bin/curl -q --noproxy '*' --connect-timeout .2 --max-time 2 -sS http://127.0.0.1:63681/closed",
            28,
            'curl: (28) Failed to connect to 127.0.0.1 port 63681 after 204 ms: Timeout was reached\n') + "\n", encoding="utf-8")
        g1_fixture_bz_events = tmp_path / "g1-events-bz.jsonl"
        g1_fixture_bz_events.write_text(command_event(
            "/usr/bin/curl -q --noproxy '*' --connect-timeout .2 --max-time 2 --retry 1 http://127.0.0.1:63681/closed",
            28,
            '  % Total    % Received % Xferd  Average Speed   Time    Time     Time  Current\n                                 Dload  Upload   Total   Spent    Left  Speed\n\n  0     0    0     0    0     0      0      0 --:--:-- --:--:-- --:--:--     0\n  0     0    0     0    0     0      0      0 --:--:-- --:--:-- --:--:--     0\ncurl: (28) Failed to connect to 127.0.0.1 port 63681 after 203 ms: Timeout was reached\nWarning: Problem : timeout. Will retry in 1 seconds. 1 retries left.\n\n  0     0    0     0    0     0      0      0 --:--:-- --:--:-- --:--:--     0\n  0     0    0     0    0     0      0      0 --:--:-- --:--:-- --:--:--     0\ncurl: (28) Failed to connect to 127.0.0.1 port 63681 after 205 ms: Timeout was reached\n') + "\n", encoding="utf-8")
        g1_fixture_ca_events = tmp_path / "g1-events-ca.jsonl"
        g1_fixture_ca_events.write_text(command_event(
            "/usr/bin/curl -q --noproxy '*' --connect-timeout .2 --max-time 2 --globoff 'http://127.0.0.1:{63682,63681}/ok'",
            3,
            'curl: (3) URL rejected: Port number was not a decimal number between 0 and 65535\n') + "\n", encoding="utf-8")
        g1_fixture_cb_events = tmp_path / "g1-events-cb.jsonl"
        g1_fixture_cb_events.write_text(command_event(
            "/usr/bin/curl -q --noproxy '*' --connect-timeout .2 --max-time 2 http://127.0.0.1:63682/ok http://127.0.0.1:63681/closed",
            28,
            'TARGET_SUCCESS\n  % Total    % Received % Xferd  Average Speed   Time    Time     Time  Current\n                                 Dload  Upload   Total   Spent    Left  Speed\n\n  0     0    0     0    0     0      0      0 --:--:-- --:--:-- --:--:--     0\n100    15  100    15    0     0  18726      0 --:--:-- --:--:-- --:--:-- 15000\n  % Total    % Received % Xferd  Average Speed   Time    Time     Time  Current\n                                 Dload  Upload   Total   Spent    Left  Speed\n\n  0     0    0     0    0     0      0      0 --:--:-- --:--:-- --:--:--     0\n  0     0    0     0    0     0      0      0 --:--:-- --:--:-- --:--:--     0\ncurl: (28) Failed to connect to 127.0.0.1 port 63681 after 205 ms: Timeout was reached\n') + "\n", encoding="utf-8")
        g1_fixture_cc_events = tmp_path / "g1-events-cc.jsonl"
        g1_fixture_cc_events.write_text(command_event(
            "/usr/bin/curl -q --noproxy '*' --connect-timeout .2 --max-time 2 -sLm2 http://127.0.0.1:63682/redirect",
            28,
            '') + "\n", encoding="utf-8")
        g1_fixture_cd_events = tmp_path / "g1-events-cd.jsonl"
        g1_fixture_cd_events.write_text(command_event(
            "/usr/bin/curl -q --noproxy '*' --connect-timeout .2 --max-time 2 - http://127.0.0.1:63681/closed",
            2,
            "curl: option -: is unknown\ncurl: try 'curl --help' or 'curl --manual' for more information\n") + "\n", encoding="utf-8")
        g1_fixture_ce_events = tmp_path / "g1-events-ce.jsonl"
        g1_fixture_ce_events.write_text(command_event(
            "/usr/bin/curl -q --noproxy '*' --connect-timeout .2 --max-time 2 -- -sSm2 http://127.0.0.1:63681/closed",
            28,
            '  % Total    % Received % Xferd  Average Speed   Time    Time     Time  Current\n                                 Dload  Upload   Total   Spent    Left  Speed\n\n  0     0    0     0    0     0      0      0 --:--:-- --:--:-- --:--:--     0\n  0     0    0     0    0     0      0      0 --:--:--  0:00:01 --:--:--     0\n  0     0    0     0    0     0      0      0 --:--:--  0:00:02 --:--:--     0\ncurl: (28) Operation timed out after 2006 milliseconds with 0 bytes received\n  % Total    % Received % Xferd  Average Speed   Time    Time     Time  Current\n                                 Dload  Upload   Total   Spent    Left  Speed\n\n  0     0    0     0    0     0      0      0 --:--:-- --:--:-- --:--:--     0\n  0     0    0     0    0     0      0      0 --:--:-- --:--:-- --:--:--     0\ncurl: (28) Failed to connect to 127.0.0.1 port 63681 after 204 ms: Timeout was reached\n') + "\n", encoding="utf-8")
        g1_fixture_cf_events = tmp_path / "g1-events-cf.jsonl"
        g1_fixture_cf_events.write_text(command_event(
            "/usr/bin/curl -q --noproxy '*' --connect-timeout .2 --max-time 2 -lm2 http://127.0.0.1:63681/closed",
            28,
            '  % Total    % Received % Xferd  Average Speed   Time    Time     Time  Current\n                                 Dload  Upload   Total   Spent    Left  Speed\n\n  0     0    0     0    0     0      0      0 --:--:-- --:--:-- --:--:--     0\n  0     0    0     0    0     0      0      0 --:--:-- --:--:-- --:--:--     0\ncurl: (28) Failed to connect to 127.0.0.1 port 63681 after 205 ms: Timeout was reached\n') + "\n", encoding="utf-8")
        g1_fixture_cg_events = tmp_path / "g1-events-cg.jsonl"
        g1_fixture_cg_events.write_text(command_event(
            "/usr/bin/curl -q --noproxy '*' --connect-timeout .2 --max-time 2 -M2 http://127.0.0.1:63681/closed",
            0,
            '          _   _ ____  _\n      ___| | | |  _ \\| |\n     / __| | | | |_) | |\n    | (__| |_| |  _ <| |___\n     \\___|\\___/|_| \\_\\_____|\nNAME\n\n    curl - transfer a URL\n\nSYNOPSIS\n\n    curl [options / URLs]\n\nDESCRIPTION\n\n    curl is a tool for  transferring data from or  to a server using URLs.  It\n    supports these protocols:  DICT, FILE, FTP,  FTPS, GOPHER, GOPHERS,  HTTP,\n    HTTPS, IMAP, IMAPS,  LDAP, LDAPS,  MQTT, POP3, POP3S,  RTMP, RTMPS,  RTSP,\n    SCP, SFTP, SMB, SMBS, SMTP, SMTPS, TELNET, TFTP, WS and WSS.\n\n    curl  is  powered  by  libcurl  for  all  transfer-related  features.  See\n    libcurl(3) for details.\n\nURL\n\n    The URL syntax is protocol-dependent.  You find a detailed description  in\n    RFC 3986.\n\n    If you provide a  URL without a  leading protocol:// scheme, curl  guesses\n    what protocol you want. It then defaults to HTTP but assumes  others based\n    on often-used hostname prefixes. For example, for hostnames starting  with\n    "ftp." curl assumes you want FTP.\n\n    You can specify any amount of  URLs on the command line. They are  fetched\n    in a sequential manner in  the specified order unless you use  --parallel.\n    You can specify command  line options and URLs mixed  and in any order  on\n    the command line.\n\n    curl attempts to reuse connections when doing multiple transfers, so  that\n    getting many files from the same  server do not use multiple connects  and\n    setup handshakes. This improves speed.  Connection reuse can only be  done\n    for URLs  specified for a  single command  line invocation  and cannot  be\n    performed between separate curl runs.\n\n    Provide an IPv6 zone id in  the URL with an escaped percentage sign.  Like\n    in\n\n        "http://[fe80::3%25eth0]/"\n\n    Everything provided on the command line that is not a command  line option\n    or its argument, curl assumes is a URL and treats it as such.\n\nGLOBBING\n\n    You can specify  multiple URLs or  parts of URLs  by writing lists  within\n    braces or ranges within brackets. We call this "globbing".\n\n    Provide a list with three different names like this:\n\n        "http://site.{one,two,three}.com"\n\n    Do sequences of alphanumeric series by using [] as in:\n\n        "ftp://ftp.example.com/file[1-100].txt"\n\n    With leading zeroes:\n\n        "ftp://ftp.example.com/file[001-100].txt"\n\n    With letters through the alphabet:\n\n        "ftp://ftp.example.com/file[a-z].txt"\n\n    Nested sequences are not supported, but  you can use several ones next  to\n    each other:\n\n        "http://example.com/archive[1996-1999]/vol[1-4]/part{a,b,c}.html"\n\n    You can specify a step counter for  the ranges to get every Nth number  or\n    letter:\n\n        "http://example.com/file[1-100:10].txt"\n\n        "http://example.com/file[a-z:2].txt"\n\n    When using []  or {} sequences  when invoked from  a command line  prompt,\n    you probably have to  put the full URL within  double quotes to avoid  the\n    shell from  interfering  with it.  This  also goes  for  other  characters\n    treated special, like for example \'&\', \'?\' and \'*\'.\n\n    Switch off globbing with --globoff.\n\nVARIABLES\n\n    curl supports command line variables (added in 8.3.0). Set variables  with\n    --variable name=content  or  --variable  name@file (where  "file"  can  be\n    stdin if set to a single dash (-)).\n\n    Variable contents can  be expanded in  option parameters using  "{{name}}"\n    if the option name  is prefixed with  "--expand-". This gets the  contents\n    of the variable "name" inserted, or a blank if the name does not  exist as\n    a variable. Insert  "{{" verbatim  in the  string by prefixing  it with  a\n    backslash, like "\\{{".\n\n    You an access and  expand environment variables  by first importing  them.\n    You can select  to either require  the environment variable  to be set  or\n    you can  provide a default  value in  case it  is not  already set.  Plain\n    --variable %name  imports the  variable called  \'name\' but  exits with  an\n    error if  that  environment variable  is not  already  set. To  provide  a\n    default  value  if  it  is  not  set,  use  --variable   %name=content  or\n    --variable %name@content.\n\n    Example. Get the USER environment variable  into the URL, fail if USER  is\n    not set:\n\n        --variable \'%USER\'\n        --expand-url = "https://example.com/api/{{USER}}/method"\n\n    When expanding variables, curl supports  a set of functions that can  make\n    the variable  contents more convenient  to use.  It can  trim leading  and\n    trailing white space  with "trim", it  can output the  contents as a  JSON\n    quoted string  with "json", URL  encode the  string with  "url" or  base64\n    encode it  with "b64". To  apply functions  to a  variable expansion,  add\n    them colon separated to the  right side of the variable. Variable  content\n    holding null bytes that are not encoded when expanded cause error.\n\n    Example: get the contents of  a file called $HOME/.secret into a  variable\n    called "fix". Make sure  that the content  is trimmed and  percent-encoded\n    when sent as POST data:\n\n        --variable %HOME\n        --expand-variable fix@{{HOME}}/.secret\n        --expand-data "{{fix:trim:url}}"\n        https://example.com/\n\n    Command line variables and expansions were added in 8.3.0.\n\nOUTPUT\n\n    If not told otherwise, curl writes the received data to stdout. It  can be\n    instructed to  instead  save  that  data  into a  local  file,  using  the\n    --output or  --remote-name options.  If  curl is  given multiple  URLs  to\n    transfer on  the command  line, it  similarly needs  multiple options  for\n    where to save them.\n\n    curl does  not parse  or otherwise  "understand" the  content  it gets  or\n    writes as  output. It  does  no encoding  or decoding,  unless  explicitly\n    asked to with dedicated command line options.\n\nPROTOCOLS\n\n    curl supports  numerous protocols,  or  put in  URL terms:  schemes.  Your\n    particular build may not support them all.\n\n    DICT\n\n        Lets you lookup words using online dictionaries.\n\n    FILE\n\n        Read or write  local files.  curl does not  support accessing  file://\n        URL remotely, but when running  on Microsoft Windows using the  native\n        UNC approach works.\n\n    FTP(S)\n\n        curl supports  the File Transfer  Protocol with  a lot  of tweaks  and\n        levers. With or without using TLS.\n\n    GOPHER(S)\n\n        Retrieve files.\n\n    HTTP(S)\n\n        curl supports HTTP with numerous options and variations. It can  speak\n        HTTP version 0.9,  1.0, 1.1, 2  and 3 depending  on build options  and\n        the correct command line options.\n\n    IMAP(S)\n\n        Using the mail  reading protocol,  curl can download  emails for  you.\n        With or without using TLS.\n\n    LDAP(S)\n\n        curl can do directory lookups for you, with or without TLS.\n\n    MQTT\n\n        curl supports MQTT version 3.  Downloading over MQTT equals  subscribe\n        to a topic  while uploading/posting  equals publish on  a topic.  MQTT\n        over TLS is not supported (yet).\n\n    POP3(S)\n\n        Downloading from a pop3 server  means getting a mail. With or  without\n        using TLS.\n\n    RTMP(S)\n\n        The Realtime Messaging Protocol is  primarily used to serve  streaming\n        media and curl can download it.\n\n    RTSP\n\n        curl supports RTSP 1.0 downloads.\n\n    SCP\n\n        curl supports SSH version 2 scp transfers.\n\n    SFTP\n\n        curl supports SFTP (draft 5) done over SSH version 2.\n\n    SMB(S)\n\n        curl supports SMB version 1 for upload and download.\n\n    SMTP(S)\n\n        Uploading contents to an SMTP  server means sending an email. With  or\n        without TLS.\n\n    TELNET\n\n        Fetching a telnet  URL starts  an interactive session  where it  sends\n        what it reads on stdin and outputs what the server sends it.\n\n    TFTP\n\n        curl can do TFTP downloads and uploads.\n\nPROGRESS METER\n\n    curl normally displays a progress meter during operations, indicating  the\n    amount of transferred data, transfer speeds and estimated time left,  etc.\n    The progress meter  displays the transfer  rate in  bytes per second.  The\n    suffixes (k, M, G, T, P) are 1024 based. For example 1k is 1024  bytes. 1M\n    is 1048576 bytes.\n\n    curl displays this data to the terminal by default, so if you  invoke curl\n    to do an  operation and  it is  about to write  data to  the terminal,  it\n    disables the  progress meter  as otherwise  it would  mess  up the  output\n    mixing progress meter and response data.\n\n    If you want a progress  meter for HTTP POST  or PUT requests, you need  to\n    redirect  the response  output  to  a  file,  using  shell  redirect  (>),\n    --output or similar.\n\n    This does not apply to FTP upload as that operation does not spit  out any\n    response data to the terminal.\n\n    If you prefer a progress bar instead of the regular  meter, --progress-bar\n    is your friend. You  can also disable  the progress meter completely  with\n    the --silent option.\n\nVERSION\n\n    This man page describes  curl 8.7.0. If you  use a later version,  chances\n    are this  man page  does not  fully document  it. If  you  use an  earlier\n    version, this document  tries to include  version information about  which\n    specific version that introduced changes.\n\n    You can always learn which the latest curl version is by running\n\n        curl https://curl.se/info\n\n    The  online version  of  this  man  page  is  always  showing  the  latest\n    incarnation: https://curl.se/docs/manpage.html\n\nOPTIONS\n\n    Options start  with one  or two  dashes. Many  of the  options require  an\n    additional value next  to them.  If provided  text does not  start with  a\n    dash, it is presumed to be and treated as a URL.\n\n    The short "single-dash" form of the  options, -d for example, may be  used\n    with or without a space  between it and its  value, although a space is  a\n    recommended separator.  The long  double-dash  form, --data  for  example,\n    requires a space between it and its value.\n\n    Short version options that do not  need any additional values can be  used\n    immediately next to each other, like  for example you can specify all  the\n    options -O, -L and -v at once as -OLv.\n\n    In general, all boolean  options are enabled  with --option and yet  again\n    disabled with  --no-option. That  is, you  use the  same  option name  but\n    prefix it with "no-". However, in  this list we mostly only list and  show\n    the --option version of them.\n\n    When --next is used, it resets  the parser state and you start again  with\n    a clean  option state,  except for  the options  that  are global.  Global\n    options retain their values and meaning even after --next.\n\n    The   following    options    are   global:    --fail-early,    --libcurl,\n    --parallel-immediate, --parallel,  --progress-bar,  --rate,  --show-error,\n    --stderr,  --styled-output,  --trace-ascii,  --trace-config,  --trace-ids,\n    --trace-time, --trace and --verbose.\n\n    --abstract-unix-socket <path>\n            (HTTP) Connect through an abstract Unix domain socket, instead  of\n            using the network.  Note: netstat  shows the path  of an  abstract\n            socket prefixed with "@", however  the <path> argument should  not\n            have this leading character.\n\n            If --abstract-unix-socket is provided several times, the last  set\n            value is used.\n\n            Example:\n             curl --abstract-unix-socket socketpath https://example.com\n\n            See also --unix-socket. Added in 7.53.0.\n\n    --alt-svc <filename>\n            (HTTPS) Enable the alt-svc  parser. If the  filename points to  an\n            existing alt-svc cache  file, that  gets used.  After a  completed\n            transfer, the cache is saved to the filename again if it  has been\n            modified.\n\n            Specify a ""  filename (zero length)  to avoid loading/saving  and\n            make curl just handle the cache in memory.\n\n            If this option  is used  several times, curl  loads contents  from\n            all the files but the last one is used for saving.\n\n            --alt-svc can be used several times in a command line\n\n            Example:\n             curl --alt-svc svc.txt https://example.com\n\n            See also --resolve and --connect-to. Added in 7.64.1.\n\n    --anyauth\n            (HTTP) Figure  out authentication  method automatically,  and  use\n            the most secure  one the remote  site claims  to support. This  is\n            done by first doing a  request and checking the  response-headers,\n            thus possibly inducing  an extra network  round-trip. This  option\n            is used  instead  of  setting a  specific  authentication  method,\n            which you can do with --basic, --digest, --ntlm, and --negotiate.\n\n            Using --anyauth is not recommended  if you do uploads from  stdin,\n            since it may  require data to  be sent twice  and then the  client\n            must be able to  rewind. If the  need should arise when  uploading\n            from stdin, the upload operation fails.\n\n            Used together with --user.\n\n            Providing --anyauth multiple times has no extra effect.\n\n            Example:\n             curl --anyauth --user me:pwd https://example.com\n\n            See also --proxy-anyauth, --basic and --digest.\n\n    -a, --append\n            (FTP SFTP) When used in  an upload, this option makes curl  append\n            to the target file instead  of overwriting it. If the remote  file\n            does not exist, it is created.  Note that this flag is ignored  by\n            some SFTP servers (including OpenSSH).\n\n            Providing --append multiple times has no extra effect. Disable  it\n            again with --no-append.\n\n            Example:\n             curl --upload-file local --append ftp://example.com/\n\n            See also --range and --continue-at.\n\n    --aws-sigv4 <provider1[:prvdr2[:reg[:srv]]]>\n            (HTTP) Use AWS V4 signature authentication in the transfer.\n\n            The provider argument is  a string that  is used by the  algorithm\n            when creating outgoing authentication headers.\n\n            The region argument is a  string that points to a geographic  area\n            of a resources  collection (region-code) when  the region name  is\n            omitted from the endpoint.\n\n            The service  argument  is  a  string that  points  to  a  function\n            provided by  a  cloud  (service-code) when  the  service  name  is\n            omitted from the endpoint.\n\n            If --aws-sigv4 is provided  several times, the  last set value  is\n            used.\n\n            Example:\n             curl --aws-sigv4 "aws:amz:us-east-2:es" --user "key:secret" https://example.com\n\n            See also --basic and --user. Added in 7.75.0.\n\n    --basic\n            (HTTP) Use HTTP  Basic authentication with  the remote host.  This\n            method is  the  default  and this  option  is  usually  pointless,\n            unless you use it to override a previously set option that  sets a\n            different authentication  method  (such as  --ntlm,  --digest,  or\n            --negotiate).\n\n            Used together with --user.\n\n            Providing --basic multiple times has no extra effect.\n\n            Example:\n             curl -u name:password --basic https://example.com\n\n            See also --proxy-basic.\n\n    --ca-native\n            (TLS) Use the CA store from the native operating system  to verify\n            the peer. By default, curl  otherwise uses a CA store provided  in\n            a  single file  or  directory,  but  when  using  this  option  it\n            interfaces the operating system\'s own vault.\n\n            This option works for curl  on Windows when built to use  OpenSSL,\n            wolfSSL (added in 8.3.0) or GnuTLS (added in 8.5.0). When  curl on\n            Windows is  built to  use Schannel,  this feature  is implied  and\n            curl then only uses the native CA store.\n\n            Providing --ca-native multiple times has no extra effect.  Disable\n            it again with --no-ca-native.\n\n            Example:\n             curl --ca-native https://example.com\n\n            See also --cacert, --capath and --insecure. Added in 8.2.0.\n\n    --cacert <file>\n            (TLS) Use the specified certificate  file to verify the peer.  The\n            file may  contain  multiple CA  certificates.  The  certificate(s)\n            must be in  PEM format. Normally  curl is built  to use a  default\n            file for  this, so this  option is  typically used  to alter  that\n            default file.\n\n            curl recognizes  the environment  variable named  \'CURL_CA_BUNDLE\'\n            if it is  set and the TLS  backend is not  Schannel, and uses  the\n            given path as a  path to a CA  cert bundle. This option  overrides\n            that variable.\n\n            The windows version  of curl  automatically looks for  a CA  certs\n            file named \'curl-ca-bundle.crt\', either  in the same directory  as\n            curl.exe, or in the  Current Working Directory,  or in any  folder\n            along your PATH.\n\n            (iOS and macOS only)  If curl is  built against Secure  Transport,\n            then this  option is  supported  for backward  compatibility  with\n            other SSL engines, but it should not be set. If the option  is not\n            set, then  curl  uses the  certificates  in the  system  and  user\n            Keychain to  verify the  peer, which  is the  preferred method  of\n            verifying the peer\'s certificate chain.\n\n            (Schannel only) This option is  supported for Schannel in  Windows\n            7 or  later  (added  in  7.60.0). This  option  is  supported  for\n            backward compatibility  with  other  SSL engines;  instead  it  is\n            recommended to  use  Windows\'  store  of  root  certificates  (the\n            default for Schannel).\n\n            If --cacert  is provided  several  times, the  last set  value  is\n            used.\n\n            Example:\n             curl --cacert CA-file.txt https://example.com\n\n            See also --capath and --insecure.\n\n    --capath <dir>\n            (TLS) Use the specified certificate directory to verify the  peer.\n            Multiple paths  can  be provided  by  separated with  colon  (":")\n            (e.g.  "path1:path2:path3").  The  certificates  must  be  in  PEM\n            format, and if curl is  built against OpenSSL, the directory  must\n            have been  processed  using  the c_rehash  utility  supplied  with\n            OpenSSL. Using  --capath can  allow OpenSSL-powered  curl to  make\n            SSL-connections much more efficiently  than using --cacert if  the\n            --cacert file contains many CA certificates.\n\n            If this option is set, the default capath value is ignored.\n\n            If --capath  is provided  several  times, the  last set  value  is\n            used.\n\n            Example:\n             curl --capath /local/directory https://example.com\n\n            See also --cacert and --insecure.\n\n    --cert-status\n            (TLS) Verify the  status of  the server certificate  by using  the\n            Certificate Status Request (aka. OCSP stapling) TLS extension.\n\n            If this option is  enabled and the  server sends an invalid  (e.g.\n            expired) response,  if  the  response  suggests  that  the  server\n            certificate has been revoked, or  no response at all is  received,\n            the verification fails.\n\n            This support  is currently  only implemented  in the  OpenSSL  and\n            GnuTLS backends.\n\n            Providing  --cert-status  multiple  times  has  no  extra  effect.\n            Disable it again with --no-cert-status.\n\n            Example:\n             curl --cert-status https://example.com\n\n            See also --pinnedpubkey.\n\n    --cert-type <type>\n            (TLS) Set type of the  provided client certificate. PEM, DER,  ENG\n            and P12 are recognized types.\n\n            The default type depends  on the TLS  backend and is usually  PEM,\n            however for Secure Transport and Schannel it is P12. If  --cert is\n            a pkcs11: URI then ENG is the default type.\n\n            If --cert-type is provided  several times, the  last set value  is\n            used.\n\n            Example:\n             curl --cert-type PEM --cert file https://example.com\n\n            See also --cert, --key and --key-type.\n\n    -E, --cert <certificate[:password]>\n            (TLS) Use the  specified client  certificate file  when getting  a\n            file  with  HTTPS,  FTPS   or  another  SSL-based  protocol.   The\n            certificate must be in PKCS#12  format if using Secure  Transport,\n            or PEM format if using any other engine. If the  optional password\n            is not specified,  it is queried  for on  the terminal. Note  that\n            this option assumes  a certificate  file that is  the private  key\n            and the client certificate concatenated.  See --cert and --key  to\n            specify them independently.\n\n            In the <certificate> portion of the argument, you must escape  the\n            character ":"  as  "\\:"  so  that  it is  not  recognized  as  the\n            password delimiter. Similarly,  you must escape  the double  quote\n            character as  \\"  so  that  it  is not  recognized  as  an  escape\n            character.\n\n            If curl is built  against OpenSSL library,  and the engine  pkcs11\n            is available,  then  a  PKCS#11 URI  (RFC  7512) can  be  used  to\n            specify a  certificate  located  in a  PKCS#11  device.  A  string\n            beginning with "pkcs11:"  is interpreted  as a PKCS#11  URI. If  a\n            PKCS#11 URI  is  provided, then  the  --engine option  is  set  as\n            "pkcs11" if none was  provided and the  --cert-type option is  set\n            as "ENG" if none was provided.\n\n            (iOS and macOS only)  If curl is  built against Secure  Transport,\n            then  the  certificate  string  can  either  be  the  name   of  a\n            certificate/private key in  the system  or user  keychain, or  the\n            path to  a PKCS#12-encoded  certificate and  private key.  If  you\n            want to use a file  from the current directory, please precede  it\n            with "./" prefix, in order to avoid confusion with a nickname.\n\n            (Schannel only) Client  certificates must be  specified by a  path\n            expression to a certificate store. (Loading PFX is not  supported;\n            you  can import  it  to  a  store  first).  You  can  use  "<store\n            location>\\<store name>\\<thumbprint>" to refer to a certificate  in\n            the     system      certificates     store,      for      example,\n            "CurrentUser\\MY\\934a7ac6f8a5d579285a74fa61e19f23ddfe8d7a".\n            Thumbprint is  usually a SHA-1  hex string  which you  can see  in\n            certificate details.  Following  store  locations  are  supported:\n            CurrentUser,     LocalMachine,      CurrentService,      Services,\n            CurrentUserGroupPolicy,        LocalMachineGroupPolicy         and\n            LocalMachineEnterprise.\n\n            If --cert is provided several times, the last set value is used.\n\n            Example:\n             curl --cert certfile --key keyfile https://example.com\n\n            See also --cert-type, --key and --key-type.\n\n    --ciphers <list of ciphers>\n            (TLS) Specifies which ciphers to  use in the connection. The  list\n            of ciphers must specify valid ciphers. Read up on SSL  cipher list\n            details on this URL:\n\n            https://curl.se/docs/ssl-ciphers.html\n\n            If --ciphers  is provided  several times,  the last  set value  is\n            used.\n\n            Example:\n             curl --ciphers ECDHE-ECDSA-AES256-CCM8 https://example.com\n\n            See also --tlsv1.3, --tls13-ciphers and --proxy-ciphers.\n\n    --compressed-ssh\n            (SCP SFTP) Enables  built-in SSH compression.  This is a  request,\n            not an order; the server may or may not do it.\n\n            Providing --compressed-ssh  multiple times  has no  extra  effect.\n            Disable it again with --no-compressed-ssh.\n\n            Example:\n             curl --compressed-ssh sftp://example.com/\n\n            See also --compressed. Added in 7.56.0.\n\n    --compressed\n            (HTTP) Request a compressed response  using one of the  algorithms\n            curl supports, and automatically decompress the content.\n\n            Response headers  are not  modified  when saved,  so if  they  are\n            "interpreted" separately again at a later point they might  appear\n            to be  saying that  the content  is (still)  compressed; while  in\n            fact it has already been decompressed.\n\n            If this  option  is  used  and the  server  sends  an  unsupported\n            encoding, curl reports an error. This is a request, not  an order;\n            the server may or may not deliver data compressed.\n\n            Providing  --compressed  multiple  times  has  no  extra   effect.\n            Disable it again with --no-compressed.\n\n            Example:\n             curl --compressed https://example.com\n\n            See also --compressed-ssh.\n\n    -K, --config <file>\n            Specify a text file to read curl arguments from. The  command line\n            arguments found  in  the  text  file  are used  as  if  they  were\n            provided on the command line.\n\n            Options and their parameters  must be specified  on the same  line\n            in the file, separated by  whitespace, colon, or the equals  sign.\n            Long option  names can  optionally  be given  in the  config  file\n            without the initial double dashes  and if so, the colon or  equals\n            characters can be used as  separators. If the option is  specified\n            with one or two dashes, there can be no colon or  equals character\n            between the option and its parameter.\n\n            If the parameter contains  whitespace or starts  with a colon  (:)\n            or equals sign (=),  it must be  specified enclosed within  double\n            quotes ("like this").  Within double quotes  the following  escape\n            sequences are available: \\\\,  \\", \\t, \\n,  \\r and \\v. A  backslash\n            preceding any other letter is ignored.\n\n            If  the  first  non-blank  column  of  a  config  line  is  a  \'#\'\n            character, that line is treated as a comment.\n\n            Only write  one option per  physical line  in the  config file.  A\n            single line is  required to be  no more  than 10 megabytes  (since\n            8.2.0).\n\n            Specify the filename to  --config as minus  "-" to make curl  read\n            the file from stdin.\n\n            Note that to  be able  to specify a  URL in the  config file,  you\n            need to  specify it  using the  --url option,  and  not by  simply\n            writing the URL  on its  own line.  So, it could  look similar  to\n            this:\n\n                url = "https://curl.se/docs/"\n\n                # --- Example file ---\n                # this is a comment\n                url = "example.com"\n                output = "curlhere.html"\n                user-agent = "superagent/1.0"\n\n                # and fetch another URL too\n                url = "example.com/docs/manpage.html"\n                -O\n                referer = "http://nowhereatall.example.com/"\n                # --- End of example file ---\n\n            When curl is invoked, it  (unless --disable is used) checks for  a\n            default config file and  uses it if  found, even when --config  is\n            used. The  default config  file is  checked for  in the  following\n            places in this order:\n\n            1) "$CURL_HOME/.curlrc"\n\n            2) "$XDG_CONFIG_HOME/curlrc" (Added in 7.73.0)\n\n            3) "$HOME/.curlrc"\n\n            4) Windows: "%USERPROFILE%\\.curlrc"\n\n            5) Windows: "%APPDATA%\\.curlrc"\n\n            6) Windows: "%USERPROFILE%\\Application Data\\.curlrc"\n\n            7) Non-Windows: use getpwuid to find the home directory\n\n            8) On  Windows,  if  it finds  no  .curlrc file  in  the  sequence\n            described above, it checks for one in the same directory  the curl\n            executable is placed.\n\n            On Windows two  filenames are  checked per  location: .curlrc  and\n            _curlrc, preferring the former. Older versions on Windows  checked\n            for _curlrc only.\n\n            --config can be used several times in a command line\n\n            Example:\n             curl --config file.txt https://example.com\n\n            See also --disable.\n\n    --connect-timeout <seconds>\n            Maximum time in seconds that you allow curl\'s connection to  take.\n            This only limits the connection phase, so if curl connects  within\n            the given period it continues - if not it exits.\n\n            This option accepts decimal values. The decimal value needs to  be\n            provided using  a dot (.)  as decimal  separator -  not the  local\n            version even if it might be using another separator.\n\n            The connection phase  is considered complete  when the DNS  lookup\n            and requested TCP, TLS or QUIC handshakes are done.\n\n            If --connect-timeout  is  provided  several times,  the  last  set\n            value is used.\n\n            Examples:\n             curl --connect-timeout 20 https://example.com\n             curl --connect-timeout 3.14 https://example.com\n\n            See also --max-time.\n\n    --connect-to <HOST1:PORT1:HOST2:PORT2>\n            For a  request intended  for the  "HOST1:PORT1" pair,  connect  to\n            "HOST2:PORT2" instead. This option is  only used to establish  the\n            network connection. It  does NOT affect  the hostname/port  number\n            that is used for TLS/SSL  (e.g. SNI, certificate verification)  or\n            for the application protocols.\n\n            "HOST1" and "PORT1" may be empty strings, meaning any host  or any\n            port number.  "HOST2"  and  "PORT2" may  also  be  empty  strings,\n            meaning use the request\'s original hostname and port number.\n\n            A hostname specified to  this option is  compared as a string,  so\n            it needs to match the name  used in request URL. It can be  either\n            numerical such  as  "127.0.0.1" or  the  full host  name  such  as\n            "example.org".\n\n            --connect-to can be used several times in a command line\n\n            Example:\n             curl --connect-to example.com:443:example.net:8443 https://example.com\n\n            See also --resolve and --header.\n\n    -C, --continue-at <offset>\n            Resume a previous transfer from  the given byte offset. The  given\n            offset is the  exact number  of bytes that  are skipped,  counting\n            from the beginning of the source file before it is  transferred to\n            the destination.  If used  with uploads,  the FTP  server  command\n            SIZE is not used by curl.\n\n            Use "-C -" to  instruct curl to  automatically find out  where/how\n            to resume the transfer. It then uses the given output/input  files\n            to figure that out.\n\n            If --continue-at is provided several times, the last set value  is\n            used.\n\n            Examples:\n             curl -C - https://example.com\n             curl -C 400 https://example.com\n\n            See also --range.\n\n    -c, --cookie-jar <filename>\n            (HTTP) Specify to which  file you want  curl to write all  cookies\n            after a  completed operation.  Curl writes  all cookies  from  its\n            in-memory  cookie  storage  to  the  given  file  at  the  end  of\n            operations. Even if  no cookies are  known, a  file is created  so\n            that it removes any formerly  existing cookies from the file.  The\n            file  uses the  Netscape  cookie  file  format.  If  you  set  the\n            filename to  a  single minus,  "-",  the cookies  are  written  to\n            stdout.\n\n            The file specified with --cookie-jar  is only used for output.  No\n            cookies are read from the file. To read cookies, use  the --cookie\n            option. Both options can specify the same file.\n\n            This command line  option activates the  cookie engine that  makes\n            curl record and  use cookies. The  --cookie option also  activates\n            it.\n\n            If the cookie jar cannot be created or written to, the  whole curl\n            operation does not  fail or  even report an  error clearly.  Using\n            --verbose gets a warning displayed,  but that is the only  visible\n            feedback you get about this possibly lethal situation.\n\n            If --cookie-jar is provided several  times, the last set value  is\n            used.\n\n            Examples:\n             curl -c store-here.txt https://example.com\n             curl -c store-here.txt -b read-these https://example.com\n\n            See also --cookie.\n\n    -b, --cookie <data|filename>\n            (HTTP) Pass the data to the  HTTP server in the Cookie header.  It\n            is supposedly the data  previously received from  the server in  a\n            "Set-Cookie:"  line.   The   data   should  be   in   the   format\n            "NAME1=VALUE1; NAME2=VALUE2" or as a single filename.\n\n            When given a set of specific cookies and not a filename,  it makes\n            curl use the  cookie header  with this content  explicitly in  all\n            outgoing  request(s).  If  multiple  requests  are  done  due   to\n            authentication, followed redirects or  similar, they all get  this\n            cookie header passed on.\n\n            If no "=" symbol  is used in the  argument, it is instead  treated\n            as a filename to read  previously stored cookie from. This  option\n            also activates the cookie engine which makes curl record  incoming\n            cookies, which may be handy  if you are using this in  combination\n            with the --location  option or  do multiple URL  transfers on  the\n            same invoke.\n\n            If the filename is a  single minus ("-"), curl reads the  contents\n            from stdin. If  the filename is  an empty string  ("") and is  the\n            only cookie input,  curl activates the  cookie engine without  any\n            cookies.\n\n            The file format of the file  to read cookies from should be  plain\n            HTTP headers  (Set-Cookie style)  or the  Netscape/Mozilla  cookie\n            file format.\n\n            The file  specified  with  --cookie  is only  used  as  input.  No\n            cookies are  written  to that  file.  To store  cookies,  use  the\n            --cookie-jar option.\n\n            If you use the Set-Cookie file format and do not specify  a domain\n            then the cookie  is not sent  since the  domain never matches.  To\n            address  this,  set  a  domain  in  Set-Cookie  line  (doing  that\n            includes subdomains) or preferably: use the Netscape format.\n\n            Users often  want  to both  read cookies  from  a file  and  write\n            updated cookies  back  to  a  file, so  using  both  --cookie  and\n            --cookie-jar in the same command line is common.\n\n            If curl  is  built  with  PSL (Public  Suffix  List)  support,  it\n            detects and discards  cookies that are  specified for such  suffix\n            domains that should  not be allowed  to have  cookies. If curl  is\n            not built  with  PSL support,  it has  no  ability to  stop  super\n            cookies.\n\n            --cookie can be used several times in a command line\n\n            Examples:\n             curl -b "" https://example.com\n             curl -b cookiefile https://example.com\n             curl -b cookiefile -c cookiefile https://example.com\n             curl -b name=Jane https://example.com\n\n            See also --cookie-jar and --junk-session-cookies.\n\n    --create-dirs\n            When used in  conjunction with the  --output option, curl  creates\n            the necessary  local directory  hierarchy as  needed. This  option\n            creates  the  directories  mentioned  with  the  --output   option\n            combined with  the path  possibly set  with --output-dir.  If  the\n            combined output filename uses no directory, or if the  directories\n            it mentions already exist, no directories are created.\n\n            Created directories are  made with  mode 0750 on  unix style  file\n            systems.\n\n            To  create  remote  directories  when  using  FTP  or  SFTP,   try\n            --ftp-create-dirs.\n\n            Providing  --create-dirs  multiple  times  has  no  extra  effect.\n            Disable it again with --no-create-dirs.\n\n            Example:\n             curl --create-dirs --output local/dir/file https://example.com\n\n            See also --ftp-create-dirs and --output-dir.\n\n    --create-file-mode <mode>\n            (SFTP SCP FILE) When curl  is used to create files remotely  using\n            one of the  supported protocols,  this option allows  the user  to\n            set which \'mode\' to set on  the file at creation time, instead  of\n            the default 0644.\n\n            This option takes an octal number as argument.\n\n            If --create-file-mode  is provided  several  times, the  last  set\n            value is used.\n\n            Example:\n             curl --create-file-mode 0777 -T localfile sftp://example.com/new\n\n            See also --ftp-create-dirs. Added in 7.75.0.\n\n    --crlf\n            (FTP SMTP) Convert line feeds  to carriage return plus line  feeds\n            in upload. Useful for MVS (OS/390).\n\n            (SMTP added in 7.40.0)\n\n            Providing --crlf multiple  times has no  extra effect. Disable  it\n            again with --no-crlf.\n\n            Example:\n             curl --crlf -T file ftp://example.com/\n\n            See also --use-ascii.\n\n    --crlfile <file>\n            (TLS)  Provide  a  file  using  PEM  format  with  a   Certificate\n            Revocation List that may specify peer certificates that are to  be\n            considered revoked.\n\n            If --crlfile  is provided  several times,  the last  set value  is\n            used.\n\n            Example:\n             curl --crlfile rejects.txt https://example.com\n\n            See also --cacert and --capath.\n\n    --curves <list>\n            (TLS) Set specific curves to use during SSL session  establishment\n            according to RFC  8422, 5.1. Multiple  algorithms can be  provided\n            by separating them with  ":" (e.g. "X25519:P-521"). The  parameter\n            is available identically in the OpenSSL "s_client" and  "s_server"\n            utilities.\n\n            --curves allows  a OpenSSL  powered curl  to make  SSL-connections\n            with exactly  the (EC)  curve requested  by the  client,  avoiding\n            nontransparent client/server negotiations.\n\n            If this option is set, the default curves list built  into OpenSSL\n            are ignored.\n\n            If --curves  is provided  several  times, the  last set  value  is\n            used.\n\n            Example:\n             curl --curves X25519 https://example.com\n\n            See also --ciphers. Added in 7.73.0.\n\n    --data-ascii <data>\n            (HTTP) This option is just an alias for --data.\n\n            --data-ascii can be used several times in a command line\n\n            Example:\n             curl --data-ascii @file https://example.com\n\n            See also --data-binary, --data-raw and --data-urlencode.\n\n    --data-binary <data>\n            (HTTP) Post data  exactly as  specified with  no extra  processing\n            whatsoever.\n\n            If you start  the data  with the letter  @, the rest  should be  a\n            filename. Data  is posted  in  a similar  manner as  --data  does,\n            except that  newlines  and  carriage  returns  are  preserved  and\n            conversions are never done.\n\n            Like --data  the  default  content-type  sent  to  the  server  is\n            application/x-www-form-urlencoded. If  you  want the  data  to  be\n            treated as  arbitrary  binary data  by  the server  then  set  the\n            content-type     to      octet-stream:      -H      "Content-Type:\n            application/octet-stream".\n\n            If this  option is  used  several times,  the ones  following  the\n            first append data as described in --data.\n\n            --data-binary can be used several times in a command line\n\n            Example:\n             curl --data-binary @filename https://example.com\n\n            See also --data-ascii.\n\n    --data-raw <data>\n            (HTTP) Post  data  similarly to  --data  but without  the  special\n            interpretation of the @ character.\n\n            --data-raw can be used several times in a command line\n\n            Examples:\n             curl --data-raw "hello" https://example.com\n             curl --data-raw "@at@at@" https://example.com\n\n            See also --data.\n\n    --data-urlencode <data>\n            (HTTP) Post data,  similar to  the other --data  options with  the\n            exception that this performs URL-encoding.\n\n            To be  CGI-compliant, the  <data> part  should begin  with a  name\n            followed by a  separator and a  content specification. The  <data>\n            part can be passed to curl using one of the following syntaxes:\n\n            content\n\n                URL-encode the content and  pass that on.  Just be careful  so\n                that the content does not  contain any "=" or "@" symbols,  as\n                that makes the syntax match one of the other cases below!\n\n            =content\n\n                URL-encode the content  and pass  that on.  The preceding  "="\n                symbol is not included in the data.\n\n            name=content\n\n                URL-encode the content part  and pass that  on. Note that  the\n                name part is expected to be URL-encoded already.\n\n            @filename\n\n                load data  from  the  given  file  (including  any  newlines),\n                URL-encode that data and pass it on in the POST.\n\n            name@filename\n\n                load data  from  the  given  file  (including  any  newlines),\n                URL-encode that  data and pass  it on  in the  POST. The  name\n                part   gets   an   equal    sign   appended,   resulting    in\n                name=urlencoded-file-content. Note that  the name is  expected\n                to be URL-encoded already.\n\n            --data-urlencode can be used several times in a command line\n\n            Examples:\n             curl --data-urlencode name=val https://example.com\n             curl --data-urlencode =encodethis https://example.com\n             curl --data-urlencode name@file https://example.com\n             curl --data-urlencode @fileonly https://example.com\n\n            See also --data and --data-raw.\n\n    -d, --data <data>\n            (HTTP MQTT)  Sends the specified  data in  a POST  request to  the\n            HTTP server, in the same way  that a browser does when a user  has\n            filled in an HTML form and presses the submit button.  This option\n            makes curl  pass the  data to  the server  using the  content-type\n            application/x-www-form-urlencoded. Compare to --form.\n\n            --data-raw  is almost  the  same  but  does  not  have  a  special\n            interpretation of the  @ character.  To post  data purely  binary,\n            you should  instead use  the --data-binary  option. To  URL-encode\n            the value of a form field you may use --data-urlencode.\n\n            If any  of  these options  is  used more  than  once on  the  same\n            command  line,  the  data  pieces  specified  are  merged  with  a\n            separating &-symbol. Thus, using  \'-d name=daniel -d  skill=lousy\'\n            would    generate    a    post     chunk    that    looks     like\n            \'name=daniel&skill=lousy\'.\n\n            If you start  the data  with the letter  @, the rest  should be  a\n            filename to read the data from, or - if you want curl to  read the\n            data from stdin.  Posting data  from a file  named \'foobar\'  would\n            thus be  done with --data  @foobar. When  --data is  told to  read\n            from a file like that,  carriage returns, newlines and null  bytes\n            are stripped out.  If you do not  want the @  character to have  a\n            special interpretation use --data-raw instead.\n\n            The data for  this option is  passed on to  the server exactly  as\n            provided on the  command line.  curl does not  convert, change  or\n            improve it.  It is  up to  the user  to provide  the  data in  the\n            correct form.\n\n            --data can be used several times in a command line\n\n            Examples:\n             curl -d "name=curl" https://example.com\n             curl -d "name=curl" -d "tool=cmdline" https://example.com\n             curl -d @filename https://example.com\n\n            See also  --data-binary,  --data-urlencode  and  --data-raw.  This\n            option  is   mutually  exclusive   to   --form  and   --head   and\n            --upload-file.\n\n    --delegation <LEVEL>\n            (GSS/kerberos) Set LEVEL what curl is allowed to delegate when  it\n            comes to user credentials.\n\n            none\n\n                Do not allow any delegation.\n\n            policy\n\n                Delegates if and  only if  the OK-AS-DELEGATE flag  is set  in\n                the Kerberos  service  ticket,  which is  a  matter  of  realm\n                policy.\n\n            always\n\n                Unconditionally allow the server to delegate.\n\n            If --delegation is provided several  times, the last set value  is\n            used.\n\n            Example:\n             curl --delegation "none" https://example.com\n\n            See also --insecure and --ssl.\n\n    --digest\n            (HTTP) Enables  HTTP  Digest authentication.  This  authentication\n            scheme avoids sending the  password over the  wire in clear  text.\n            Use this  in combination  with  the normal  --user option  to  set\n            username and password.\n\n            Providing --digest multiple times has no extra effect. Disable  it\n            again with --no-digest.\n\n            Example:\n             curl -u name:password --digest https://example.com\n\n            See also  --user, --proxy-digest  and  --anyauth. This  option  is\n            mutually exclusive to --basic and --ntlm and --negotiate.\n\n    --disable-eprt\n            (FTP) Disable the  use of the  EPRT and  LPRT commands when  doing\n            active FTP transfers.  Curl normally  first attempts  to use  EPRT\n            before using PORT, but with this option, it uses PORT  right away.\n            EPRT is an extension  to the original  FTP protocol, and does  not\n            work on all servers,  but enables more  functionality in a  better\n            way than the traditional PORT command.\n\n            --eprt can be used to  explicitly enable EPRT again and  --no-eprt\n            is an alias for --disable-eprt.\n\n            If the server is  accessed using IPv6,  this option has no  effect\n            as EPRT is necessary then.\n\n            Disabling EPRT only changes  the active behavior.  If you want  to\n            switch to passive mode you need to not use --ftp-port or  force it\n            with --ftp-pasv.\n\n            Providing --disable-eprt  multiple  times  has  no  extra  effect.\n            Disable it again with --no-disable-eprt.\n\n            Example:\n             curl --disable-eprt ftp://example.com/\n\n            See also --disable-epsv and --ftp-port.\n\n    --disable-epsv\n            (FTP) Disable the use of  the EPSV command when doing passive  FTP\n            transfers. Curl normally first attempts  to use EPSV before  PASV,\n            but with this option, it does not try EPSV.\n\n            --epsv can be used to  explicitly enable EPSV again and  --no-epsv\n            is an alias for --disable-epsv.\n\n            If the server is an IPv6  host, this option has no effect as  EPSV\n            is necessary then.\n\n            Disabling EPSV only changes the  passive behavior. If you want  to\n            switch to active mode you need to use --ftp-port.\n\n            Providing --disable-epsv  multiple  times  has  no  extra  effect.\n            Disable it again with --no-disable-epsv.\n\n            Example:\n             curl --disable-epsv ftp://example.com/\n\n            See also --disable-eprt and --ftp-port.\n\n    -q, --disable\n            If used as  the first parameter  on the  command line, the  curlrc\n            config file is not read or  used. See the --config for details  on\n            the default config file search path.\n\n            Prior to 7.50.0  curl supported the  short option  name q but  not\n            the long option name disable.\n\n            Providing --disable multiple  times has no  extra effect.  Disable\n            it again with --no-disable.\n\n            Example:\n             curl -q https://example.com\n\n            See also --config.\n\n    --disallow-username-in-url\n            Exit with error if  passed a URL  containing a username.  Probably\n            most useful when the URL is being provided at runtime or similar.\n\n            Providing --disallow-username-in-url multiple  times has no  extra\n            effect. Disable it again with --no-disallow-username-in-url.\n\n            Example:\n             curl --disallow-username-in-url https://example.com\n\n            See also --proto. Added in 7.61.0.\n\n    --dns-interface <interface>\n            (DNS) Send  outgoing DNS  requests  through the  given  interface.\n            This option  is  a  counterpart to  --interface  (which  does  not\n            affect DNS). The supplied  string must be  an interface name  (not\n            an address).\n\n            If --dns-interface is provided several  times, the last set  value\n            is used.\n\n            Example:\n             curl --dns-interface eth0 https://example.com\n\n            See  also  --dns-ipv4-addr  and  --dns-ipv6-addr.  --dns-interface\n            requires that the underlying libcurl was built to support c-ares.\n\n    --dns-ipv4-addr <address>\n            (DNS)  Bind  to  a  specific  IP  address  when  making  IPv4  DNS\n            requests, so that  the DNS requests  originate from this  address.\n            The argument should be a single IPv4 address.\n\n            If --dns-ipv4-addr is provided several  times, the last set  value\n            is used.\n\n            Example:\n             curl --dns-ipv4-addr 10.1.2.3 https://example.com\n\n            See  also  --dns-interface  and  --dns-ipv6-addr.  --dns-ipv4-addr\n            requires that the underlying libcurl was built to support c-ares.\n\n    --dns-ipv6-addr <address>\n            (DNS)  Bind  to  a  specific  IP  address  when  making  IPv6  DNS\n            requests, so that  the DNS requests  originate from this  address.\n            The argument should be a single IPv6 address.\n\n            If --dns-ipv6-addr is provided several  times, the last set  value\n            is used.\n\n            Example:\n             curl --dns-ipv6-addr 2a04:4e42::561 https://example.com\n\n            See  also  --dns-interface  and  --dns-ipv4-addr.  --dns-ipv6-addr\n            requires that the underlying libcurl was built to support c-ares.\n\n    --dns-servers <addresses>\n            (DNS) Set  the list  of  DNS servers  to be  used instead  of  the\n            system default. The list of IP addresses should be separated  with\n            commas. Port numbers  may also  optionally be  given, appended  to\n            the IP address separated with a colon.\n\n            If --dns-servers is provided several times, the last set value  is\n            used.\n\n            Examples:\n             curl --dns-servers 192.168.0.1,192.168.0.2 https://example.com\n             curl --dns-servers 10.0.0.1:53 https://example.com\n\n            See  also  --dns-interface   and  --dns-ipv4-addr.   --dns-servers\n            requires that the underlying libcurl was built to support c-ares.\n\n    --doh-cert-status\n            Same as --cert-status but used for DoH (DNS-over-HTTPS).\n\n            Verifies the status of the  DoH servers\' certificate by using  the\n            Certificate Status Request (aka. OCSP stapling) TLS extension.\n\n            If this  option is enabled  and the  DoH server  sends an  invalid\n            (e.g. expired) response, if the response suggests that the  server\n            certificate has been revoked, or  no response at all is  received,\n            the verification fails.\n\n            This support  is currently  only implemented  in the  OpenSSL  and\n            GnuTLS backends.\n\n            Providing --doh-cert-status multiple  times has  no extra  effect.\n            Disable it again with --no-doh-cert-status.\n\n            Example:\n             curl --doh-cert-status --doh-url https://doh.example https://example.com\n\n            See also --doh-insecure. Added in 7.76.0.\n\n    --doh-insecure\n            Same as --insecure but used for DoH (DNS-over-HTTPS).\n\n            Providing --doh-insecure  multiple  times  has  no  extra  effect.\n            Disable it again with --no-doh-insecure.\n\n            Example:\n             curl --doh-insecure --doh-url https://doh.example https://example.com\n\n            See also --doh-url. Added in 7.76.0.\n\n    --doh-url <URL>\n            Specifies which  DNS-over-HTTPS (DoH)  server  to use  to  resolve\n            hostnames, instead of using  the default name resolver  mechanism.\n            The URL must be HTTPS.\n\n            Some SSL options that  you set for  your transfer also applies  to\n            DoH since  the name  lookups  take place  over SSL.  However,  the\n            certificate  verification  settings  are  not  inherited  but  are\n            controlled separately via --doh-insecure and --doh-cert-status.\n\n            This option is  unset if an empty  string "" is  used as the  URL.\n            (Added in 7.85.0)\n\n            If --doh-url  is provided  several times,  the last  set value  is\n            used.\n\n            Example:\n             curl --doh-url https://doh.example https://example.com\n\n            See also --doh-insecure. Added in 7.62.0.\n\n    -D, --dump-header <filename>\n            (HTTP FTP) Write  the received protocol  headers to the  specified\n            file. If no headers are  received, the use of this option  creates\n            an empty file.\n\n            When used in  FTP, the  FTP server response  lines are  considered\n            being "headers" and thus are saved there.\n\n            Having multiple transfers in one set of operations (i.e. the  URLs\n            in one --next clause),  appends them to  the same file,  separated\n            by a blank line.\n\n            If --dump-header is provided several times, the last set value  is\n            used.\n\n            Example:\n             curl --dump-header store.txt https://example.com\n\n            See also --output.\n\n    --egd-file <file>\n            (TLS) Deprecated option (added in  7.84.0). Prior to that it  only\n            had an effect on curl if built to use old versions of OpenSSL.\n\n            Specify the path name to the Entropy Gathering Daemon socket.  The\n            socket is used to seed the random engine for SSL connections.\n\n            If --egd-file is  provided several  times, the last  set value  is\n            used.\n\n            Example:\n             curl --egd-file /random/here https://example.com\n\n            See also --random-file.\n\n    --engine <name>\n            (TLS)  Select  the  OpenSSL  crypto  engine  to  use  for   cipher\n            operations. Use  --engine  list  to print  a  list  of  build-time\n            supported engines. Note that  not all (and  possibly none) of  the\n            engines may be available at runtime.\n\n            If --engine  is provided  several  times, the  last set  value  is\n            used.\n\n            Example:\n             curl --engine flavor https://example.com\n\n            See also --ciphers and --curves.\n\n    --etag-compare <file>\n            (HTTP) Make a conditional HTTP request for the specific ETag  read\n            from the  given  file by  sending  a custom  If-None-Match  header\n            using the stored ETag.\n\n            For correct results,  make sure that  the specified file  contains\n            only a single line with the desired ETag. An empty file  is parsed\n            as an empty ETag.\n\n            Use  the  option  --etag-save  to  first  save  the  ETag  from  a\n            response, and then use  this option to  compare against the  saved\n            ETag in a subsequent request.\n\n            If --etag-compare is  provided several times,  the last set  value\n            is used.\n\n            Example:\n             curl --etag-compare etag.txt https://example.com\n\n            See also --etag-save and --time-cond. Added in 7.68.0.\n\n    --etag-save <file>\n            (HTTP) Save  an HTTP  ETag to  the specified  file. An  ETag is  a\n            caching related header, usually returned in a response.\n\n            If no ETag is sent by the server, an empty file is created.\n\n            If --etag-save is provided  several times, the  last set value  is\n            used.\n\n            Example:\n             curl --etag-save storetag.txt https://example.com\n\n            See also --etag-compare. Added in 7.68.0.\n\n    --expect100-timeout <seconds>\n            (HTTP) Maximum time in seconds that  you allow curl to wait for  a\n            100-continue response  when curl  emits an  Expects:  100-continue\n            header in  its request.  By default  curl waits  one second.  This\n            option  accepts  decimal  values.  When  curl  stops  waiting,  it\n            continues as if a response was received.\n\n            The decimal value needs to  provided using a dot (".") as  decimal\n            separator -  not  the local  version even  if  it might  be  using\n            another separator.\n\n            If --expect100-timeout  is provided  several times,  the last  set\n            value is used.\n\n            Example:\n             curl --expect100-timeout 2.5 -T file https://example.com\n\n            See also --connect-timeout.\n\n    --fail-early\n            Fail and exit on the first detected transfer error.\n\n            When curl is used  to do multiple  transfers on the command  line,\n            it attempts to operate on each given URL, one by one.  By default,\n            it ignores errors if there are more URLs given and the  last URL\'s\n            success determines  the error  code curl  returns. Early  failures\n            are "hidden" by subsequent successful transfers.\n\n            Using this  option, curl  instead returns  an error  on the  first\n            transfer that fails, independent  of the amount  of URLs that  are\n            given on  the command  line.  This way,  no transfer  failures  go\n            undetected by scripts and similar.\n\n            This option does not imply --fail, which causes transfers to  fail\n            due to  the server\'s HTTP  status code.  You can  combine the  two\n            options, however  note  --fail  is not  global  and  is  therefore\n            contained by --next.\n\n            This option is global and does  not need to be specified for  each\n            use of --next.\n\n            Providing  --fail-early  multiple  times  has  no  extra   effect.\n            Disable it again with --no-fail-early.\n\n            Example:\n             curl --fail-early https://example.com https://two.example\n\n            See also --fail and --fail-with-body. Added in 7.52.0.\n\n    --fail-with-body\n            (HTTP) Return an error  on server errors  where the HTTP  response\n            code is  400 or  greater). In  normal cases  when  an HTTP  server\n            fails to deliver a document,  it returns an HTML document  stating\n            so (which often also describes  why and more). This option  allows\n            curl to output and save that content but also to return error 22.\n\n            This is an alternative option to --fail which makes curl  fail for\n            the same circumstances but without saving the content.\n\n            Providing --fail-with-body  multiple times  has no  extra  effect.\n            Disable it again with --no-fail-with-body.\n\n            Example:\n             curl --fail-with-body https://example.com\n\n            See  also  --fail  and  --fail-early.  This  option  is   mutually\n            exclusive to --fail. Added in 7.76.0.\n\n    -f, --fail\n            (HTTP) Fail fast with no output  at all on server errors. This  is\n            useful to  enable scripts  and users  to better  deal with  failed\n            attempts. In normal cases when  an HTTP server fails to deliver  a\n            document, it  returns an  HTML document  stating so  (which  often\n            also describes why  and more). This  command line option  prevents\n            curl from outputting that and return error 22.\n\n            This method  is  not  fail-safe  and  there  are  occasions  where\n            non-successful  response  codes  slip  through,  especially   when\n            authentication is involved (response codes 401 and 407).\n\n            Providing --fail multiple  times has no  extra effect. Disable  it\n            again with --no-fail.\n\n            Example:\n             curl --fail https://example.com\n\n            See  also  --fail-with-body  and  --fail-early.  This  option   is\n            mutually exclusive to --fail-with-body.\n\n    --false-start\n            (TLS) Use false start during  the TLS handshake. False start is  a\n            mode where a  TLS client  starts sending  application data  before\n            verifying the server\'s Finished message, thus saving a round  trip\n            when performing a full handshake.\n\n            This functionality  is currently  only implemented  in the  Secure\n            Transport (on iOS 7.0 or later, or OS X 10.9 or later) backend.\n\n            Providing  --false-start  multiple  times  has  no  extra  effect.\n            Disable it again with --no-false-start.\n\n            Example:\n             curl --false-start https://example.com\n\n            See also --tcp-fastopen.\n\n    --form-escape\n            (HTTP) Pass  on names  of multipart  form fields  and files  using\n            backslash-escaping instead of percent-encoding.\n\n            If --form-escape is provided several times, the last set value  is\n            used.\n\n            Example:\n             curl --form-escape -F \'field\\name=curl\' -F \'file=@load"this\' https://example.com\n\n            See also --form. Added in 7.81.0.\n\n    --form-string <name=string>\n            (HTTP SMTP IMAP) Similar  to --form except  that the value  string\n            for the  named  parameter  is  used literally.  Leading  @  and  <\n            characters, and the ";type=" string  in the value have no  special\n            meaning.  Use this  in  preference  to  --form  if  there  is  any\n            possibility that the string value  may accidentally trigger the  @\n            or < features of --form.\n\n            --form-string can be used several times in a command line\n\n            Example:\n             curl --form-string "name=data" https://example.com\n\n            See also --form.\n\n    -F, --form <name=content>\n            (HTTP  SMTP  IMAP)  For  the  HTTP  protocol  family,  emulate   a\n            filled-in form  in which  a user  has pressed  the submit  button.\n            This   makes    curl   POST    data   using    the    Content-Type\n            multipart/form-data according to RFC 2388.\n\n            For SMTP  and  IMAP  protocols, this  composes  a  multipart  mail\n            message to transmit.\n\n            This  enables  uploading  of  binary  files  etc.  To  force   the\n            \'content\' part to be a file,  prefix the filename with an @  sign.\n            To just  get the content  part from  a file,  prefix the  filename\n            with the symbol <. The difference  between @ and < is then that  @\n            makes a file get attached in the post as a file upload,  while the\n            < makes  a text  field and  just get  the contents  for that  text\n            field from a file.\n\n            Read content from stdin  instead of a file  by using a single  "-"\n            as filename. This goes for both @ and < constructs. When  stdin is\n            used,  the contents  is  buffered  in  memory  first  by  curl  to\n            determine its size and allow a possible resend. Defining a  part\'s\n            data from  a  named non-regular  file (such  as  a named  pipe  or\n            similar) is  not  subject to  buffering  and is  instead  read  at\n            transmission time;  since  the full  size  is unknown  before  the\n            transfer starts, such data is sent as chunks by HTTP  and rejected\n            by IMAP.\n\n            Example: send an image to  an HTTP server, where \'profile\' is  the\n            name of  the form-field  to  which the  file portrait.jpg  is  the\n            input:\n\n                curl -F profile=@portrait.jpg https://example.com/upload.cgi\n\n            Example: send your name  and shoe size in  two text fields to  the\n            server:\n\n                curl -F name=John -F shoesize=11 https://example.com/\n\n            Example: send your essay  in a text field  to the server. Send  it\n            as a plain text  field, but get the contents  for it from a  local\n            file:\n\n                curl -F "story=<hugefile.txt" https://example.com/\n\n            You can  also instruct  curl  what Content-Type  to use  by  using\n            "type=", in a manner similar to:\n\n                curl -F "web=@index.html;type=text/html" example.com\n\n            or\n\n                curl -F "name=daniel;type=text/foo" example.com\n\n            You can also  explicitly change the  name field  of a file  upload\n            part by setting filename=, like this:\n\n                curl -F "file=@localfile;filename=nameinpost" example.com\n\n            If filename/path  contains  \',\'  or  \';\', it  must  be  quoted  by\n            double-quotes like:\n\n                curl -F "file=@\\"local,file\\";filename=\\"name;in;post\\"" example.com\n\n            or\n\n                curl -F \'file=@"local,file";filename="name;in;post"\' example.com\n\n            Note that  if  a filename/path  is  quoted by  double-quotes,  any\n            double-quote or backslash within the  filename must be escaped  by\n            backslash.\n\n            Quoting must  also be  applied  to non-file  data if  it  contains\n            semicolons, leading/trailing spaces or leading double quotes:\n\n                curl -F \'colors="red; green; blue";type=text/x-myapp\' example.com\n\n            You can add custom headers to the field by setting headers=, like\n\n                curl -F "submit=OK;headers=\\"X-submit-type: OK\\"" example.com\n\n            or\n\n                curl -F "submit=OK;headers=@headerfile" example.com\n\n            The headers= keyword  may appear  more that once  and above  notes\n            about quoting  apply. When  headers are  read from  a file,  Empty\n            lines and lines starting with  \'#\' are comments and ignored;  each\n            header can be folded by  splitting between two words and  starting\n            the continuation line with a space; embedded carriage-returns  and\n            trailing spaces are stripped. Here is an example of a  header file\n            contents:\n\n                # This file contain two headers.\n                X-header-1: this is a header\n\n                # The following header is folded.\n                X-header-2: this is\n                 another header\n\n            To  support  sending  multipart  mail  messages,  the  syntax   is\n            extended as follows:\n\n            - name can be  omitted: the equal sign  is the first character  of\n            the argument,\n\n            - if data starts with \'(\', this signals to start a  new multipart:\n            it can be followed by a content type specification.\n\n            - a multipart can be terminated with a \'=)\' argument.\n\n            Example:  the  following   command  sends  an   SMTP  mime   email\n            consisting in an  inline part  in two  alternative formats:  plain\n            text and HTML. It attaches a text file:\n\n                curl -F \'=(;type=multipart/alternative\' \\\n                     -F \'=plain text message\' \\\n                     -F \'= <body>HTML message</body>;type=text/html\' \\\n                     -F \'=)\' -F \'=@textfile.txt\' ...  smtp://example.com\n\n            Data  can  be  encoded  for  transfer  using  encoder=.  Available\n            encodings are binary  and 8bit  that do nothing  else than  adding\n            the  corresponding  Content-Transfer-Encoding  header,  7bit  that\n            only   rejects   8-bit   characters   with   a   transfer   error,\n            quoted-printable and  base64 that  encodes data  according to  the\n            corresponding schemes, limiting lines length to 76 characters.\n\n            Example: send multipart mail with a quoted-printable text  message\n            and a base64 attached file:\n\n                curl -F \'=text message;encoder=quoted-printable\' \\\n                     -F \'=@localfile;encoder=base64\' ... smtp://example.com\n\n            See further examples and details in the MANUAL.\n\n            --form can be used several times in a command line\n\n            Example:\n             curl --form "name=curl" --form "file=@loadthis" https://example.com\n\n            See also --data, --form-string  and --form-escape. This option  is\n            mutually exclusive to --data and --head and --upload-file.\n\n    --ftp-account <data>\n            (FTP) When an FTP  server asks for  "account data" after  username\n            and password has been  provided, this data  is sent off using  the\n            ACCT command.\n\n            If --ftp-account is provided several times, the last set value  is\n            used.\n\n            Example:\n             curl --ftp-account "mr.robot" ftp://example.com/\n\n            See also --user.\n\n    --ftp-alternative-to-user <command>\n            (FTP) If authenticating  with the  USER and  PASS commands  fails,\n            send  this  command.  When   connecting  to  Tumbleweed\'s   Secure\n            Transport server  over  FTPS  using a  client  certificate,  using\n            "SITE AUTH" tells  the server  to retrieve the  username from  the\n            certificate.\n\n            If --ftp-alternative-to-user is provided  several times, the  last\n            set value is used.\n\n            Example:\n             curl --ftp-alternative-to-user "U53r" ftp://example.com\n\n            See also --ftp-account and --user.\n\n    --ftp-create-dirs\n            (FTP SFTP)  When an FTP  or SFTP  URL/operation uses  a path  that\n            does not currently exist on  the server, the standard behavior  of\n            curl is  to fail.  Using  this option,  curl instead  attempts  to\n            create missing directories.\n\n            Providing --ftp-create-dirs multiple  times has  no extra  effect.\n            Disable it again with --no-ftp-create-dirs.\n\n            Example:\n             curl --ftp-create-dirs -T file ftp://example.com/remote/path/file\n\n            See also --create-dirs.\n\n    --ftp-method <method>\n            (FTP) Control what method  curl should use to  reach a file on  an\n            FTP(S) server. The method argument should be one of the  following\n            alternatives:\n\n            multicwd\n\n                Do a  single CWD operation  for each  path part  in the  given\n                URL. For deep  hierarchies this means  many commands. This  is\n                how RFC 1738 says it should  be done. This is the default  but\n                the slowest behavior.\n\n            nocwd\n\n                Do no CWD  at all. curl  does SIZE, RETR,  STOR etc and  gives\n                the full path to the  server for each of these commands.  This\n                is the fastest behavior.\n\n            singlecwd\n\n                Do one CWD with the full target directory and then  operate on\n                the file  "normally"  (like in  the  multicwd case).  This  is\n                somewhat more  standards compliant  than "nocwd"  but  without\n                the full penalty of "multicwd".\n\n            If --ftp-method is provided several  times, the last set value  is\n            used.\n\n            Examples:\n             curl --ftp-method multicwd ftp://example.com/dir1/dir2/file\n             curl --ftp-method nocwd ftp://example.com/dir1/dir2/file\n             curl --ftp-method singlecwd ftp://example.com/dir1/dir2/file\n\n            See also --list-only.\n\n    --ftp-pasv\n            (FTP) Use passive  mode for  the data connection.  Passive is  the\n            internal default behavior, but  using this option  can be used  to\n            override a previous --ftp-port option.\n\n            Reversing an enforced passive  really is not  doable but you  must\n            then instead enforce the correct --ftp-port again.\n\n            Passive mode  means that  curl tries  the EPSV  command first  and\n            then PASV, unless --disable-epsv is used.\n\n            Providing --ftp-pasv multiple times  has no extra effect.  Disable\n            it again with --no-ftp-pasv.\n\n            Example:\n             curl --ftp-pasv ftp://example.com/\n\n            See also --disable-epsv.\n\n    -P, --ftp-port <address>\n            (FTP)  Reverses   the   default  initiator/listener   roles   when\n            connecting with FTP. This option makes curl use active mode.  curl\n            then  commands  the  server  to  connect  back  to  the   client\'s\n            specified address and port, while passive mode asks the server  to\n            setup an  IP address  and port  for it  to  connect to.  <address>\n            should be one of:\n\n            interface\n\n                e.g. eth0 to specify which interface\'s IP address you want  to\n                use (Unix only)\n\n            IP address\n\n                e.g. 192.168.10.1 to specify the exact IP address\n\n            hostname\n\n                e.g. my.host.domain to specify the machine\n\n            -\n\n                make curl pick the  same IP address  that is already used  for\n                the control connection. This is the recommended choice.\n\n        .RE .IP\n\n                Disable the use of PORT  with --ftp-pasv. Disable the  attempt\n                to  use   the  EPRT   command  instead   of  PORT   by   using\n                --disable-eprt. EPRT is really PORT++.\n\n                You can  also  append ":[start]-[end]"  to  the right  of  the\n                address, to tell curl what  TCP port range to use. That  means\n                you specify a port range, from  a lower to a higher number.  A\n                single number works  as well,  but do note  that it  increases\n                the risk of failure since the port may not be available.\n\n            If --ftp-port is  provided several  times, the last  set value  is\n            used.\n\n            Examples:\n             curl -P - ftp:/example.com\n             curl -P eth0 ftp:/example.com\n             curl -P 192.168.0.2 ftp:/example.com\n\n            See also --ftp-pasv and --disable-eprt.\n\n    --ftp-pret\n            (FTP) Send  a PRET  command before  PASV (and  EPSV). Certain  FTP\n            servers, mainly  drftpd,  require this  non-standard  command  for\n            directory listings as well as up and downloads in PASV mode.\n\n            Providing --ftp-pret multiple times  has no extra effect.  Disable\n            it again with --no-ftp-pret.\n\n            Example:\n             curl --ftp-pret ftp://example.com/\n\n            See also --ftp-port and --ftp-pasv.\n\n    --ftp-skip-pasv-ip\n            (FTP) Do  not  use  the IP  address  the server  suggests  in  its\n            response to  curl\'s  PASV  command when  curl  connects  the  data\n            connection. Instead curl  reuses the  same IP  address it  already\n            uses for the control connection.\n\n            This option is enabled by default (added in 7.74.0).\n\n            This option has no  effect if PORT, EPRT  or EPSV is used  instead\n            of PASV.\n\n            Providing --ftp-skip-pasv-ip multiple times  has no extra  effect.\n            Disable it again with --no-ftp-skip-pasv-ip.\n\n            Example:\n             curl --ftp-skip-pasv-ip ftp://example.com/\n\n            See also --ftp-pasv.\n\n    --ftp-ssl-ccc-mode <active/passive>\n            (FTP) Sets the CCC  mode. The passive  mode does not initiate  the\n            shutdown, but instead waits for the server to do it, and  does not\n            reply to the shutdown from  the server. The active mode  initiates\n            the shutdown and waits for a reply from the server.\n\n            Providing --ftp-ssl-ccc-mode multiple times  has no extra  effect.\n            Disable it again with --no-ftp-ssl-ccc-mode.\n\n            Example:\n             curl --ftp-ssl-ccc-mode active --ftp-ssl-ccc ftps://example.com/\n\n            See also --ftp-ssl-ccc.\n\n    --ftp-ssl-ccc\n            (FTP) Use  CCC  (Clear Command  Channel)  Shuts down  the  SSL/TLS\n            layer after  authenticating.  The  rest  of  the  control  channel\n            communication is  be  unencrypted.  This  allows  NAT  routers  to\n            follow the FTP transaction. The default mode is passive.\n\n            Providing  --ftp-ssl-ccc  multiple  times  has  no  extra  effect.\n            Disable it again with --no-ftp-ssl-ccc.\n\n            Example:\n             curl --ftp-ssl-ccc ftps://example.com/\n\n            See also --ssl and --ftp-ssl-ccc-mode.\n\n    --ftp-ssl-control\n            (FTP) Require  SSL/TLS  for the  FTP  login, clear  for  transfer.\n            Allows secure  authentication,  but non-encrypted  data  transfers\n            for efficiency. Fails the transfer if the server does not  support\n            SSL/TLS.\n\n            Providing --ftp-ssl-control multiple  times has  no extra  effect.\n            Disable it again with --no-ftp-ssl-control.\n\n            Example:\n             curl --ftp-ssl-control ftp://example.com\n\n            See also --ssl.\n\n    -G, --get\n            (HTTP) When  used,  this  option makes  all  data  specified  with\n            --data, --data-binary or  --data-urlencode to be  used in an  HTTP\n            GET request instead of  the POST request  that otherwise would  be\n            used. The data is appended to the URL with a \'?\' separator.\n\n            If used  in combination  with  --head, the  POST data  is  instead\n            appended to the URL with a HEAD request.\n\n            Providing --get multiple  times has  no extra  effect. Disable  it\n            again with --no-get.\n\n            Examples:\n             curl --get https://example.com\n             curl --get -d "tool=curl" -d "age=old" https://example.com\n             curl --get -I -d "tool=curl" https://example.com\n\n            See also --data and --request.\n\n    -g, --globoff\n            Switch off the URL  globbing function. When  you set this  option,\n            you can specify URLs that contain the letters {}[] without  having\n            curl itself  interpret  them.  Note that  these  letters  are  not\n            normal legal URL contents but they should be encoded according  to\n            the URI standard.\n\n            Providing --globoff multiple  times has no  extra effect.  Disable\n            it again with --no-globoff.\n\n            Example:\n             curl -g "https://example.com/{[]}}}}"\n\n            See also --config and --disable.\n\n    --happy-eyeballs-timeout-ms <ms>\n            Happy Eyeballs is an  algorithm that attempts  to connect to  both\n            IPv4 and  IPv6  addresses  for dual-stack  hosts,  giving  IPv6  a\n            head-start of the  specified number of  milliseconds. If the  IPv6\n            address  cannot  be  connected  to   within  that  time,  then   a\n            connection attempt is made  to the IPv4  address in parallel.  The\n            first connection to be established is the one that is used.\n\n            The range of  suggested useful values  is limited. Happy  Eyeballs\n            RFC 6555  says  "It is  RECOMMENDED  that connection  attempts  be\n            paced 150-250 ms  apart to balance  human factors against  network\n            load." libcurl currently  defaults to 200  ms. Firefox and  Chrome\n            currently default to 300 ms.\n\n            If --happy-eyeballs-timeout-ms  is  provided  several  times,  the\n            last set value is used.\n\n            Example:\n             curl --happy-eyeballs-timeout-ms 500 https://example.com\n\n            See also --max-time and --connect-timeout. Added in 7.59.0.\n\n    --haproxy-clientip <ip>\n            (HTTP) Sets a  client IP in  HAProxy PROXY  protocol v1 header  at\n            the beginning of the connection.\n\n            For valid requests, IPv4 addresses  must be indicated as a  series\n            of exactly 4 integers in  the range [0..255] inclusive written  in\n            decimal representation separated by  exactly one dot between  each\n            other. Heading zeroes  are not  permitted in front  of numbers  in\n            order to avoid  any possible  confusion with  octal numbers.  IPv6\n            addresses must  be indicated  as series  of 4  hexadecimal  digits\n            (upper or  lower case)  delimited by  colons between  each  other,\n            with the acceptance of  one double colon  sequence to replace  the\n            largest acceptable range of  consecutive zeroes. The total  number\n            of decoded bits must exactly be 128.\n\n            Otherwise, any string can  be accepted for  the client IP and  get\n            sent.\n\n            It replaces --haproxy-protocol  if used,  it is  not necessary  to\n            specify both flags.\n\n            If --haproxy-clientip  is provided  several  times, the  last  set\n            value is used.\n\n            Example:\n             curl --haproxy-clientip $IP\n\n            See also --proxy. Added in 8.2.0.\n\n    --haproxy-protocol\n            (HTTP) Send a HAProxy  PROXY protocol v1  header at the  beginning\n            of the  connection.  This  is  used by  some  load  balancers  and\n            reverse proxies  to  indicate the  client\'s  true IP  address  and\n            port.\n\n            This option is primarily  useful when sending  test requests to  a\n            service that expects this header.\n\n            Providing --haproxy-protocol multiple times  has no extra  effect.\n            Disable it again with --no-haproxy-protocol.\n\n            Example:\n             curl --haproxy-protocol https://example.com\n\n            See also --proxy. Added in 7.60.0.\n\n    -I, --head\n            (HTTP FTP FILE) Fetch the  headers only! HTTP-servers feature  the\n            command HEAD which this  uses to get nothing  but the header of  a\n            document. When  used on an  FTP or  FILE file,  curl displays  the\n            file size and last modification time only.\n\n            Providing --head multiple  times has no  extra effect. Disable  it\n            again with --no-head.\n\n            Example:\n             curl -I https://example.com\n\n            See also --get, --verbose and --trace-ascii.\n\n    -H, --header <header/@file>\n            (HTTP IMAP  SMTP) Extra  header to  include in  information  sent.\n            When used  within an  HTTP request,  it is  added  to the  regular\n            request headers.\n\n            For an IMAP or SMTP MIME uploaded mail built with  --form options,\n            it is  prepended  to  the  resulting  MIME  document,  effectively\n            including it  at the mail  global level.  It does  not affect  raw\n            uploaded mails (Added in 7.56.0).\n\n            You may  specify any number  of extra  headers. Note  that if  you\n            should add a custom  header that has the same  name as one of  the\n            internal ones curl would use,  your externally set header is  used\n            instead  of the  internal  one.  This  allows  you  to  make  even\n            trickier stuff  than  curl  would  normally  do.  You  should  not\n            replace internally  set  headers without  knowing  perfectly  well\n            what  you are  doing.  Remove  an  internal  header  by  giving  a\n            replacement without content  on the  right side of  the colon,  as\n            in: -H "Host:". If you  send the custom header with no-value  then\n            its header  must  be  terminated  with a  semicolon,  such  as  -H\n            "X-Custom-Header;" to send "X-Custom-Header:".\n\n            curl makes sure that each header you add/replace is sent  with the\n            proper end-of-line marker, you should thus not add that as  a part\n            of the header content:  do not add  newlines or carriage  returns,\n            they only  mess things up  for you.  curl passes  on the  verbatim\n            string you give it without  any filter or other safe guards.  That\n            includes white space and control characters.\n\n            This option can take  an argument in  @filename style, which  then\n            adds a header  for each  line in  the input file.  Using @-  makes\n            curl read the header file from stdin. Added in 7.55.0.\n\n            Please note that most anti-spam  utilities check the presence  and\n            value of  several MIME  mail headers:  these are  "From:",  "To:",\n            "Date:" and "Subject:" among others and should be added with  this\n            option.\n\n            You need --proxy-header  to send  custom headers  intended for  an\n            HTTP proxy. Added in 7.37.0.\n\n            Passing on  a "Transfer-Encoding:  chunked" header  when doing  an\n            HTTP request with a request  body, makes curl send the data  using\n            chunked encoding.\n\n            WARNING:  headers set  with  this  option  are  set  in  all  HTTP\n            requests - even after redirects are followed, like when told  with\n            --location. This can lead to the header being sent to  other hosts\n            than the original host, so  sensitive headers should be used  with\n            caution combined with following redirects.\n\n            --header can be used several times in a command line\n\n            Examples:\n             curl -H "X-First-Name: Joe" https://example.com\n             curl -H "User-Agent: yes-please/2000" https://example.com\n             curl -H "Host:" https://example.com\n             curl -H @headers.txt https://example.com\n\n            See also --user-agent and --referer.\n\n    -h, --help <category>\n            Usage help. List all  curl command line  options within the  given\n            category.\n\n            If no  argument  is provided,  curl  displays the  most  important\n            command line arguments.\n\n            For category all, curl displays help for all options.\n\n            If  category  is  specified,  curl  displays  all  available  help\n            categories.\n\n            Example:\n             curl --help all\n\n            See also --verbose.\n\n    --hostpubmd5 <md5>\n            (SFTP SCP) Pass  a string  containing 32  hexadecimal digits.  The\n            string should be  the 128 bit  MD5 checksum  of the remote  host\'s\n            public key, curl refuses the  connection with the host unless  the\n            checksums match.\n\n            If --hostpubmd5 is provided several  times, the last set value  is\n            used.\n\n            Example:\n             curl --hostpubmd5 e5c1c49020640a5ab0f2034854c321a8 sftp://example.com/\n\n            See also --hostpubsha256.\n\n    --hostpubsha256 <sha256>\n            (SFTP SCP) Pass a string  containing a Base64-encoded SHA256  hash\n            of the remote host\'s public key. Curl refuses the connection  with\n            the host unless the hashes match.\n\n            This feature requires libcurl  to be built  with libssh2 and  does\n            not work with other SSH backends.\n\n            If --hostpubsha256 is provided several  times, the last set  value\n            is used.\n\n            Example:\n             curl --hostpubsha256 NDVkMTQxMGQ1ODdmMjQ3MjczYjAyOTY5MmRkMjVmNDQ= sftp://example.com/\n\n            See also --hostpubmd5. Added in 7.80.0.\n\n    --hsts <filename>\n            (HTTPS) Enable HSTS for  the transfer. If  the filename points  to\n            an existing  HSTS cache  file,  that is  used. After  a  completed\n            transfer, the cache is saved to the filename again if it  has been\n            modified.\n\n            If curl  is  told  to  use  HTTP:// for  a  transfer  involving  a\n            hostname that exists in the  HSTS cache, it upgrades the  transfer\n            to use HTTPS. Each  HSTS cache entry  has an individual life  time\n            after which the upgrade is no longer performed.\n\n            Specify a ""  filename (zero length)  to avoid loading/saving  and\n            make curl just handle HSTS in memory.\n\n            If this option  is used  several times, curl  loads contents  from\n            all the files but the last one is used for saving.\n\n            --hsts can be used several times in a command line\n\n            Example:\n             curl --hsts cache.txt https://example.com\n\n            See also --proto. Added in 7.74.0.\n\n    --http0.9\n            (HTTP) Accept an HTTP version 0.9 response.\n\n            HTTP/0.9 is a response without headers and therefore you can  also\n            connect with this  to non-HTTP  servers and still  get a  response\n            since curl simply transparently downgrades - if allowed.\n\n            HTTP/0.9 is disabled by default (added in 7.66.0)\n\n            Providing --http0.9 multiple  times has no  extra effect.  Disable\n            it again with --no-http0.9.\n\n            Example:\n             curl --http0.9 https://example.com\n\n            See also --http1.1, --http2 and --http3. Added in 7.64.0.\n\n    -0, --http1.0\n            (HTTP) Use  HTTP  version  1.0 instead  of  using  its  internally\n            preferred HTTP version.\n\n            Providing --http1.0 multiple times has no extra effect.\n\n            Example:\n             curl --http1.0 https://example.com\n\n            See  also  --http0.9  and  --http1.1.  This  option  is   mutually\n            exclusive to  --http1.1  and --http2  and  --http2-prior-knowledge\n            and --http3.\n\n    --http1.1\n            (HTTP) Use  HTTP version  1.1. This  is the  default with  HTTP://\n            URLs.\n\n            Providing --http1.1 multiple times has no extra effect.\n\n            Example:\n             curl --http1.1 https://example.com\n\n            See  also  --http1.0  and  --http0.9.  This  option  is   mutually\n            exclusive to  --http1.0  and --http2  and  --http2-prior-knowledge\n            and --http3.\n\n    --http2-prior-knowledge\n            (HTTP)  Issue  a  non-TLS  HTTP  requests  using  HTTP/2  directly\n            without HTTP/1.1  Upgrade. It  requires prior  knowledge that  the\n            server supports  HTTP/2 straight  away.  HTTPS requests  still  do\n            HTTP/2 the standard  way with negotiated  protocol version in  the\n            TLS handshake.\n\n            Providing --http2-prior-knowledge  multiple  times  has  no  extra\n            effect. Disable it again with --no-http2-prior-knowledge.\n\n            Example:\n             curl --http2-prior-knowledge https://example.com\n\n            See also  --http2  and --http3.  --http2-prior-knowledge  requires\n            that the  underlying libcurl  was built  to support  HTTP/2.  This\n            option is  mutually  exclusive  to  --http1.1  and  --http1.0  and\n            --http2 and --http3.\n\n    --http2\n            (HTTP) Use HTTP/2.\n\n            For  HTTPS,  this  means  curl   negotiates  HTTP/2  in  the   TLS\n            handshake. curl does this by default.\n\n            For HTTP,  this means  curl  attempts to  upgrade the  request  to\n            HTTP/2 using the Upgrade: request header.\n\n            When curl uses  HTTP/2 over HTTPS,  it does  not itself insist  on\n            TLS  1.2  or   higher  even  though  that   is  required  by   the\n            specification. A  user  can  add  this  version  requirement  with\n            --tlsv1.2.\n\n            Providing --http2 multiple times has no extra effect.\n\n            Example:\n             curl --http2 https://example.com\n\n            See also --http1.1, --http3  and --no-alpn. --http2 requires  that\n            the underlying libcurl  was built to  support HTTP/2. This  option\n            is   mutually   exclusive   to   --http1.1   and   --http1.0   and\n            --http2-prior-knowledge and --http3.\n\n    --http3-only\n            (HTTP) Instructs curl to use HTTP/3  to the host in the URL,  with\n            no fallback to earlier HTTP versions. HTTP/3 can only be  used for\n            HTTPS and not  for HTTP URLs.  For HTTP,  this option triggers  an\n            error.\n\n            This option allows  a user to  avoid using  the Alt-Svc method  of\n            upgrading to HTTP/3 when  you know that  the target speaks  HTTP/3\n            on the given host and port.\n\n            This option  makes  curl  fail  if a  QUIC  connection  cannot  be\n            established, it does not  attempt any other  HTTP versions on  its\n            own. Use --http3 for similar functionality with a fallback.\n\n            Providing --http3-only multiple times has no extra effect.\n\n            Example:\n             curl --http3-only https://example.com\n\n            See also  --http1.1, --http2  and --http3.  --http3-only  requires\n            that the  underlying libcurl  was built  to support  HTTP/3.  This\n            option is  mutually  exclusive  to  --http1.1  and  --http1.0  and\n            --http2 and --http2-prior-knowledge and --http3. Added in 7.88.0.\n\n    --http3\n            (HTTP) Attempt  HTTP/3 to the  host in  the URL,  but fallback  to\n            earlier HTTP  versions  if  the  HTTP/3  connection  establishment\n            fails. HTTP/3 is only available for HTTPS and not for HTTP URLs.\n\n            This option allows  a user to  avoid using  the Alt-Svc method  of\n            upgrading to HTTP/3 when  you know that  the target speaks  HTTP/3\n            on the given host and port.\n\n            When asked to use  HTTP/3, curl issues  a separate attempt to  use\n            older  HTTP versions  with  a  slight  delay,  so  if  the  HTTP/3\n            transfer fails or  is slow, curl  still tries  to proceed with  an\n            older HTTP version.\n\n            Use --http3-only for similar functionality without a fallback.\n\n            Providing --http3 multiple times has no extra effect.\n\n            Example:\n             curl --http3 https://example.com\n\n            See  also  --http1.1  and  --http2.  --http3  requires  that   the\n            underlying libcurl was  built to  support HTTP/3.  This option  is\n            mutually exclusive  to --http1.1  and  --http1.0 and  --http2  and\n            --http2-prior-knowledge and --http3-only. Added in 7.66.0.\n\n    --ignore-content-length\n            (FTP HTTP) For  HTTP, Ignore  the Content-Length  header. This  is\n            particularly useful for servers running Apache 1.x, which  reports\n            incorrect Content-Length for files larger than 2 gigabytes.\n\n            For FTP, this makes curl skip  the SIZE command to figure out  the\n            size before downloading a file.\n\n            This option does  not work for  HTTP if libcurl  was built to  use\n            hyper.\n\n            Providing --ignore-content-length  multiple  times  has  no  extra\n            effect. Disable it again with --no-ignore-content-length.\n\n            Example:\n             curl --ignore-content-length https://example.com\n\n            See also --ftp-skip-pasv-ip.\n\n    -i, --include\n            (HTTP FTP) Include response headers  in the output. HTTP  response\n            headers can include things like server name, cookies, date of  the\n            document, HTTP version  and more... With  non-HTTP protocols,  the\n            "headers" are other server communication.\n\n            To view the request headers, consider the --verbose option.\n\n            Prior to 7.75.0 curl did not print the headers if --fail  was used\n            in combination with this  option and there  was error reported  by\n            server.\n\n            Providing --include multiple  times has no  extra effect.  Disable\n            it again with --no-include.\n\n            Example:\n             curl -i https://example.com\n\n            See also --verbose.\n\n    -k, --insecure\n            (TLS SFTP SCP) By default,  every secure connection curl makes  is\n            verified to  be  secure  before the  transfer  takes  place.  This\n            option makes curl skip the  verification step and proceed  without\n            checking.\n\n            When this  option  is  not  used for  protocols  using  TLS,  curl\n            verifies the server\'s  TLS certificate before  it continues:  that\n            the  certificate  contains  the  right  name  which  matches   the\n            hostname used in the URL and that the certificate has  been signed\n            by a CA  certificate present in  the cert  store. See this  online\n            resource for further details: https://curl.se/docs/sslcerts.html\n\n            For SFTP  and SCP,  this option  makes curl  skip the  known_hosts\n            verification. known_hosts is a file normally stored in the  user\'s\n            home  directory  in  the   ".ssh"  subdirectory,  which   contains\n            hostnames and their public keys.\n\n            WARNING: using this option makes the transfer insecure.\n\n            When curl uses  secure protocols  it trusts  responses and  allows\n            for example HSTS  and Alt-Svc  information to be  stored and  used\n            subsequently. Using --insecure  can make curl  trust and use  such\n            information from malicious servers.\n\n            Providing --insecure multiple times  has no extra effect.  Disable\n            it again with --no-insecure.\n\n            Example:\n             curl --insecure https://example.com\n\n            See also --proxy-insecure, --cacert and --capath.\n\n    --interface <name>\n            Perform an operation  using a specified  interface. You can  enter\n            interface name,  IP address  or hostname.  An example  could  look\n            like:\n\n                curl --interface eth0:1 https://www.example.com/\n\n            On Linux it can be used to specify a VRF, but the binary  needs to\n            either have CAP_NET_RAW  or to  be run as  root. More  information\n            about                          Linux                          VRF:\n            https://www.kernel.org/doc/Documentation/networking/vrf.txt\n\n            If --interface is provided  several times, the  last set value  is\n            used.\n\n            Example:\n             curl --interface eth0 https://example.com\n\n            See also --dns-interface.\n\n    --ipfs-gateway <URL>\n            (IPFS) Specify which gateway  to use for  IPFS and IPNS URLs.  Not\n            specifying this  instead  makes  curl check  if  the  IPFS_GATEWAY\n            environment variable  is  set,  or  if  a  "~/.ipfs/gateway"  file\n            holding the gateway URL exists.\n\n            If  you run  a  local  IPFS  node,  this  gateway  is  by  default\n            available under "http://localhost:8080". A full example URL  would\n            look like:\n\n                curl --ipfs-gateway http://localhost:8080 ipfs://bafybeigagd5nmnn2iys2f3doro7ydrevyr2mzarwidgadawmamiteydbzi\n\n            There  are   many  public   IPFS   gateways.  See   for   example:\n            https://ipfs.github.io/public-gateway-checker/\n\n            If you opt to go  for a remote gateway  you need to be aware  that\n            you completely  trust the  gateway. This  might be  fine in  local\n            gateways that you host yourself. With remote gateways there  could\n            potentially be malicious actors returning  you data that does  not\n            match the request  you made,  inspect or even  interfere with  the\n            request. You may  not notice  this when using  curl. A  mitigation\n            could be to go for  a "trustless" gateway. This means you  locally\n            verify  that the  data.  Consult  the  docs  page  on  trusted  vs\n            trustless:\n            https://docs.ipfs.tech/reference/http/gateway/#trusted-vs-trustless\n\n            If --ipfs-gateway is  provided several times,  the last set  value\n            is used.\n\n            Example:\n             curl --ipfs-gateway https://example.com ipfs://\n\n            See also --help and --manual. Added in 8.4.0.\n\n    -4, --ipv4\n            Use IPv4  addresses only  when resolving  hostnames, and  not  for\n            example try IPv6.\n\n            Providing --ipv4 multiple times has no extra effect.\n\n            Example:\n             curl --ipv4 https://example.com\n\n            See also --http1.1 and --http2. This option is mutually  exclusive\n            to --ipv6.\n\n    -6, --ipv6\n            Use IPv6  addresses only  when resolving  hostnames, and  not  for\n            example try IPv4.\n\n            Your resolver  may  respond to  an  IPv6-only resolve  request  by\n            returning IPv6 addresses that contain "mapped" IPv4 addresses  for\n            compatibility purposes. macOS is known to do this.\n\n            Providing --ipv6 multiple times has no extra effect.\n\n            Example:\n             curl --ipv6 https://example.com\n\n            See also --http1.1 and --http2. This option is mutually  exclusive\n            to --ipv4.\n\n    --json <data>\n            (HTTP) Sends  the specified JSON  data in  a POST  request to  the\n            HTTP server.  --json works  as  a shortcut  for passing  on  these\n            three options:\n\n                --data [arg]\n                --header "Content-Type: application/json"\n                --header "Accept: application/json"\n\n            There is no verification  that the passed  in data is actual  JSON\n            or that the syntax is correct.\n\n            If you start  the data  with the letter  @, the rest  should be  a\n            filename to read the data from,  or a single dash (-) if you  want\n            curl to read the data from  stdin. Posting data from a file  named\n            \'foobar\' would thus  be done  with --json @foobar  and to  instead\n            read the data from stdin, use --json @-.\n\n            If this option is  used more than once  on the same command  line,\n            the additional  data  pieces  are  concatenated  to  the  previous\n            before sending.\n\n            The headers this option  sets can be  overridden with --header  as\n            usual.\n\n            --json can be used several times in a command line\n\n            Examples:\n             curl --json \'{ "drink": "coffe" }\' https://example.com\n             curl --json \'{ "drink":\' --json \' "coffe" }\' https://example.com\n             curl --json @prepared https://example.com\n             curl --json @- https://example.com < json.txt\n\n            See also  --data-binary and  --data-raw. This  option is  mutually\n            exclusive  to  --form  and  --head  and  --upload-file.  Added  in\n            7.82.0.\n\n    -j, --junk-session-cookies\n            (HTTP) When curl is told to  read cookies from a given file,  this\n            option makes it discard all  "session cookies". This has the  same\n            effect as if a  new session is  started. Typical browsers  discard\n            session cookies when they are closed down.\n\n            Providing  --junk-session-cookies  multiple  times  has  no  extra\n            effect. Disable it again with --no-junk-session-cookies.\n\n            Example:\n             curl --junk-session-cookies -b cookies.txt https://example.com\n\n            See also --cookie and --cookie-jar.\n\n    --keepalive-time <seconds>\n            Set the  time a  connection needs  to remain  idle before  sending\n            keepalive  probes  and  the  time  between  individual   keepalive\n            probes. It is  currently effective on  operating systems  offering\n            the "TCP_KEEPIDLE"  and  "TCP_KEEPINTVL" socket  options  (meaning\n            Linux, recent AIX, HP-UX and  more). Keepalive is used by the  TCP\n            stack to detect  broken networks on  idle connections. The  number\n            of missed keepalive  probes before declaring  the connection  down\n            is OS  dependent and  is  commonly 9  or 10.  This option  has  no\n            effect if --no-keepalive is used.\n\n            If unspecified, the option defaults to 60 seconds.\n\n            If --keepalive-time is provided several times, the last set  value\n            is used.\n\n            Example:\n             curl --keepalive-time 20 https://example.com\n\n            See also --no-keepalive and --max-time.\n\n    --key-type <type>\n            (TLS) Private  key  file  type.  Specify  which  type  your  --key\n            provided private key is. DER,  PEM, and ENG are supported. If  not\n            specified, PEM is assumed.\n\n            If --key-type is  provided several  times, the last  set value  is\n            used.\n\n            Example:\n             curl --key-type DER --key here https://example.com\n\n            See also --key.\n\n    --key <key>\n            (TLS SSH)  Private  key  filename.  Allows  you  to  provide  your\n            private key  in this  separate file.  For SSH,  if not  specified,\n            curl tries  the following  candidates in  order:  "~/.ssh/id_rsa",\n            "~/.ssh/id_dsa", "./id_rsa", "./id_dsa".\n\n            If curl is built  against OpenSSL library,  and the engine  pkcs11\n            is available,  then  a  PKCS#11 URI  (RFC  7512) can  be  used  to\n            specify a  private  key located  in  a PKCS#11  device.  A  string\n            beginning with "pkcs11:"  is interpreted  as a PKCS#11  URI. If  a\n            PKCS#11 URI  is  provided, then  the  --engine option  is  set  as\n            "pkcs11" if none was provided and the --key-type option is  set as\n            "ENG" if none was provided.\n\n            If curl is built  against Secure Transport  or Schannel then  this\n            option is ignored for TLS  protocols (HTTPS, etc). Those  backends\n            expect the private key  to be already  present in the keychain  or\n            PKCS#12 file containing the certificate.\n\n            If --key is provided several times, the last set value is used.\n\n            Example:\n             curl --cert certificate --key here https://example.com\n\n            See also --key-type and --cert.\n\n    --krb <level>\n            (FTP) Enable Kerberos  authentication and use.  The level must  be\n            entered and should be one  of \'clear\', \'safe\', \'confidential\',  or\n            \'private\'. Should  you  use a  level that  is  not one  of  these,\n            \'private\' is used.\n\n            If --krb is provided several times, the last set value is used.\n\n            Example:\n             curl --krb clear ftp://example.com/\n\n            See  also  --delegation  and   --ssl.  --krb  requires  that   the\n            underlying libcurl was built to support Kerberos.\n\n    --libcurl <file>\n            Append this option to any ordinary curl command line, and  you get\n            libcurl-using C  source code  written to  the file  that does  the\n            equivalent of what your command-line operation does!\n\n            This option is global and does  not need to be specified for  each\n            use of --next.\n\n            If --libcurl  is provided  several times,  the last  set value  is\n            used.\n\n            Example:\n             curl --libcurl client.c https://example.com\n\n            See also --verbose.\n\n    --limit-rate <speed>\n            Specify the maximum transfer rate you want curl to use -  for both\n            downloads and  uploads.  This feature  is  useful if  you  have  a\n            limited pipe  and you would  like your  transfer not  to use  your\n            entire bandwidth. To make it slower than it otherwise would be.\n\n            The given speed is  measured in bytes/second,  unless a suffix  is\n            appended. Appending \'k\'  or \'K\'  counts the  number as  kilobytes,\n            \'m\'  or \'M\'  makes  it  megabytes,  while  \'g\'  or  \'G\'  makes  it\n            gigabytes. The  suffixes  (k, M,  G, T,  P)  are 1024  based.  For\n            example 1k is 1024. Examples: 200K, 3m and 1G.\n\n            The rate limiting logic works  on averaging the transfer speed  to\n            no more than the set threshold over a period of multiple seconds.\n\n            If you  also  use  the --speed-limit  option,  that  option  takes\n            precedence and might cripple  the rate-limiting slightly, to  help\n            keeping the speed-limit logic working.\n\n            If --limit-rate is provided several  times, the last set value  is\n            used.\n\n            Examples:\n             curl --limit-rate 100K https://example.com\n             curl --limit-rate 1000 https://example.com\n             curl --limit-rate 10M https://example.com\n\n            See also --rate, --speed-limit and --speed-time.\n\n    -l, --list-only\n            (FTP POP3 SFTP) When listing  an FTP directory, force a  name-only\n            view.  Maybe   particularly   useful   if  the   user   wants   to\n            machine-parse the contents  of an FTP  directory since the  normal\n            directory view does not use  a standard look or format. When  used\n            like this, the  option causes an  NLST command to  be sent to  the\n            server instead of LIST.\n\n            Note: Some FTP servers list only files in their response  to NLST;\n            they do not include sub-directories and symbolic links.\n\n            When listing an  SFTP directory,  this switch  forces a  name-only\n            view, one per line.  This is especially  useful if the user  wants\n            to machine-parse  the  contents of  an  SFTP directory  since  the\n            normal  directory  view  provides   more  information  than   just\n            filenames.\n\n            When retrieving a specific email  from POP3, this switch forces  a\n            LIST  command  to   be  performed   instead  of   RETR.  This   is\n            particularly useful  if  the  user  wants to  see  if  a  specific\n            message-id exists on the server and what size it is.\n\n            Note: When combined  with --request,  this option can  be used  to\n            send a  UIDL command  instead, so  the user  may  use the  email\'s\n            unique identifier rather than its message-id to make the request.\n\n            Providing --list-only multiple times has no extra effect.  Disable\n            it again with --no-list-only.\n\n            Example:\n             curl --list-only ftp://example.com/dir/\n\n            See also --quote and --request.\n\n    --local-port <range>\n            Set a preferred  single number  or range (FROM-TO)  of local  port\n            numbers to use for  the connection(s). Note  that port numbers  by\n            nature are a scarce  resource so setting  this range to  something\n            too narrow might cause unnecessary connection setup failures.\n\n            If --local-port is provided several  times, the last set value  is\n            used.\n\n            Example:\n             curl --local-port 1000-3000 https://example.com\n\n            See also --globoff.\n\n    --location-trusted\n            (HTTP) Like --location, but allows sending the name + password  to\n            all hosts  that the  site may  redirect to.  This may  or may  not\n            introduce a security breach  if the site  redirects you to a  site\n            to which you  send your authentication  info (which is  clear-text\n            in the case of HTTP Basic authentication).\n\n            Providing --location-trusted multiple times  has no extra  effect.\n            Disable it again with --no-location-trusted.\n\n            Example:\n             curl --location-trusted -u user:password https://example.com\n\n            See also --user.\n\n    -L, --location\n            (HTTP) If the server reports that the requested page has  moved to\n            a different location (indicated with a Location: header and a  3XX\n            response code), this  option makes  curl redo the  request on  the\n            new place.  If used  together with  --include or  --head,  headers\n            from all requested pages are shown.\n\n            When authentication is  used, curl only  sends its credentials  to\n            the initial host. If  a redirect takes  curl to a different  host,\n            it  does   not   get  the   user+password   pass  on.   See   also\n            --location-trusted on how to change this.\n\n            Limit the amount of redirects to follow by using the  --max-redirs\n            option.\n\n            When curl follows  a redirect  and if  the request is  a POST,  it\n            sends the following request  with a GET  if the HTTP response  was\n            301, 302, or  303. If the  response code was  any other 3xx  code,\n            curl resends  the  following  request using  the  same  unmodified\n            method.\n\n            You can tell curl to not  change POST requests to GET after a  30x\n            response by  using  the  dedicated options  for  that:  --post301,\n            --post302 and --post303.\n\n            The method  set with  --request overrides  the method  curl  would\n            otherwise select to use.\n\n            Providing --location multiple times  has no extra effect.  Disable\n            it again with --no-location.\n\n            Example:\n             curl -L https://example.com\n\n            See also --resolve and --alt-svc.\n\n    --login-options <options>\n            (IMAP LDAP  POP3 SMTP)  Specify the  login options  to use  during\n            server authentication.\n\n            You can use  login options  to specify  protocol specific  options\n            that may  be used  during authentication.  At present  only  IMAP,\n            POP3 and SMTP  support login options.  For more information  about\n            login options please  see RFC 2384,  RFC 5092  and the IETF  draft\n            https://datatracker.ietf.org/doc/html/draft-earhart-url-smtp-00\n\n            Since 8.2.0, IMAP  supports the login  option "AUTH=+LOGIN".  With\n            this option, curl uses the  plain (not SASL) "LOGIN IMAP"  command\n            even if the server advertises SASL authentication. Care should  be\n            taken in using  this option, as  it sends  your password over  the\n            network in  plain text.  This does  not work  if  the IMAP  server\n            disables the plain "LOGIN" (e.g. to prevent password snooping).\n\n            If --login-options is provided several  times, the last set  value\n            is used.\n\n            Example:\n             curl --login-options \'AUTH=*\' imap://example.com\n\n            See also --user.\n\n    --mail-auth <address>\n            (SMTP) Specify  a single  address.  This is  used to  specify  the\n            authentication address (identity) of  a submitted message that  is\n            being relayed to another server.\n\n            If --mail-auth is provided  several times, the  last set value  is\n            used.\n\n            Example:\n             curl --mail-auth user@example.come -T mail smtp://example.com/\n\n            See also --mail-rcpt and --mail-from.\n\n    --mail-from <address>\n            (SMTP) Specify a  single address  that the given  mail should  get\n            sent from.\n\n            If --mail-from is provided  several times, the  last set value  is\n            used.\n\n            Example:\n             curl --mail-from user@example.com -T mail smtp://example.com/\n\n            See also --mail-rcpt and --mail-auth.\n\n    --mail-rcpt-allowfails\n            (SMTP) When sending data to  multiple recipients, by default  curl\n            aborts SMTP conversation if at least one of the recipients  causes\n            RCPT TO command to return an error.\n\n            The   default    behavior    can    be    changed    by    passing\n            --mail-rcpt-allowfails  command-line  option   which  makes   curl\n            ignore errors and proceed with the remaining valid recipients.\n\n            If all  recipients  trigger RCPT  TO  failures and  this  flag  is\n            specified, curl  still aborts  the SMTP  conversation and  returns\n            the error received from to the last RCPT TO command.\n\n            Providing  --mail-rcpt-allowfails  multiple  times  has  no  extra\n            effect. Disable it again with --no-mail-rcpt-allowfails.\n\n            Example:\n             curl --mail-rcpt-allowfails --mail-rcpt dest@example.com smtp://example.com\n\n            See also --mail-rcpt. Added in 7.69.0.\n\n    --mail-rcpt <address>\n            (SMTP) Specify a  single email address,  username or mailing  list\n            name. Repeat  this  option  several  times  to  send  to  multiple\n            recipients.\n\n            When  performing  an  address  verification  (VRFY  command),  the\n            recipient should  be specified  as the  username or  username  and\n            domain (as per Section 3.5 of RFC 5321).\n\n            When  performing  a  mailing  list  expand  (EXPN  command),   the\n            recipient should be  specified using the  mailing list name,  such\n            as "Friends" or "London-Office".\n\n            --mail-rcpt can be used several times in a command line\n\n            Example:\n             curl --mail-rcpt user@example.net smtp://example.com\n\n            See also --mail-rcpt-allowfails.\n\n    -M, --manual\n            Manual. Display the huge help text.\n\n            Example:\n             curl --manual\n\n            See also --verbose, --libcurl and --trace.\n\n    --max-filesize <bytes>\n            (FTP HTTP MQTT) Specify the maximum  size (in bytes) of a file  to\n            download. If the  file requested  is larger than  this value,  the\n            transfer does not start and curl returns with exit code 63.\n\n            A size modifier  may be used.  For example,  Appending \'k\' or  \'K\'\n            counts the number  as kilobytes,  \'m\' or \'M\'  makes it  megabytes,\n            while \'g\' or \'G\'  makes it gigabytes.  Examples: 200K, 3m and  1G.\n            (Added in 7.58.0)\n\n            NOTE: before curl 8.4.0, when the file size is not known  prior to\n            download, for such  files this option  has no  effect even if  the\n            file transfer ends up being larger than this given limit.\n\n            Starting with curl 8.4.0,  this option aborts  the transfer if  it\n            reaches the threshold during transfer.\n\n            If --max-filesize is  provided several times,  the last set  value\n            is used.\n\n            Example:\n             curl --max-filesize 100K https://example.com\n\n            See also --limit-rate.\n\n    --max-redirs <num>\n            (HTTP)  Set  maximum  number  of  redirections  to  follow.   When\n            --location is  used,  to  prevent curl  from  following  too  many\n            redirects, by default, the limit is set to 50 redirects.  Set this\n            option to -1 to make it unlimited.\n\n            If --max-redirs is provided several  times, the last set value  is\n            used.\n\n            Example:\n             curl --max-redirs 3 --location https://example.com\n\n            See also --location.\n\n    -m, --max-time <seconds>\n            Set maximum time in seconds that you allow each transfer  to take.\n            Prevents your  batch  jobs from  hanging  for hours  due  to  slow\n            networks or links going down. This option accepts decimal values.\n\n            If you enable  retrying the  transfer (--retry)  then the  maximum\n            time counter is reset each  time the transfer is retried. You  can\n            use --retry-max-time to limit the retry time.\n\n            The decimal value  needs to provided  using a  dot (.) as  decimal\n            separator -  not  the local  version even  if  it might  be  using\n            another separator.\n\n            If --max-time is  provided several  times, the last  set value  is\n            used.\n\n            Examples:\n             curl --max-time 10 https://example.com\n             curl --max-time 2.92 https://example.com\n\n            See also --connect-timeout and --retry-max-time.\n\n    --metalink\n            This option was  previously used to  specify a Metalink  resource.\n            Metalink support is disabled in  curl for security reasons  (added\n            in 7.78.0).\n\n            If --metalink is  provided several  times, the last  set value  is\n            used.\n\n            Example:\n             curl --metalink file https://example.com\n\n            See also --parallel.\n\n    --negotiate\n            (HTTP) Enable Negotiate (SPNEGO) authentication.\n\n            This  option  requires  a  library  built  with  GSS-API  or  SSPI\n            support. Use --version to see  if your curl supports  GSS-API/SSPI\n            or SPNEGO.\n\n            When using  this  option, you  must  also provide  a  fake  --user\n            option to  activate the  authentication code  properly. Sending  a\n            \'-u :\'  is enough as  the username  and password  from the  --user\n            option are not actually used.\n\n            Providing --negotiate multiple times has no extra effect.\n\n            Example:\n             curl --negotiate -u : https://example.com\n\n            See also --basic, --ntlm, --anyauth and --proxy-negotiate.\n\n    --netrc-file <filename>\n            Set the netrc  file to use.  Similar to  --netrc, except that  you\n            also provide the path (absolute or relative).\n\n            It abides by --netrc-optional if specified.\n\n            If --netrc-file is provided several  times, the last set value  is\n            used.\n\n            Example:\n             curl --netrc-file netrc https://example.com\n\n            See also --netrc,  --user and  --config. This  option is  mutually\n            exclusive to --netrc.\n\n    --netrc-optional\n            Similar to  --netrc,  but  this  option  makes  the  .netrc  usage\n            optional and not mandatory as the --netrc option does.\n\n            Providing --netrc-optional  multiple times  has no  extra  effect.\n            Disable it again with --no-netrc-optional.\n\n            Example:\n             curl --netrc-optional https://example.com\n\n            See also  --netrc-file.  This  option  is  mutually  exclusive  to\n            --netrc.\n\n    -n, --netrc\n            Make curl scan the  .netrc file in  the user\'s home directory  for\n            login name and password. This  is typically used for FTP on  Unix.\n            If used with HTTP, curl enables user authentication. See  netrc(5)\n            and ftp(1) for details on the file format. Curl does  not complain\n            if that file  does not have  the right  permissions (it should  be\n            neither  world-  nor  group-readable).  The  environment  variable\n            "HOME" is used to find the home directory.\n\n            On Windows  two  filenames  in the  home  directory  are  checked:\n            .netrc and  _netrc,  preferring  the  former.  Older  versions  on\n            Windows checked for _netrc only.\n\n            A quick and simple example of how to setup a .netrc to  allow curl\n            to FTP to the machine  host.domain.com with username \'myself\'  and\n            password \'secret\' could look similar to:\n\n                machine host.domain.com\n                login myself\n                password secret\n            Providing --netrc multiple times has  no extra effect. Disable  it\n            again with --no-netrc.\n\n            Example:\n             curl --netrc https://example.com\n\n            See  also  --netrc-file,  --config  and  --user.  This  option  is\n            mutually exclusive to --netrc-file and --netrc-optional.\n\n    -:, --next\n            Use a  separate operation  for the  following URL  and  associated\n            options. This allows you to  send several URL requests, each  with\n            their  own  specific  options,  for  example,  such  as  different\n            usernames or custom requests for each.\n\n            --next resets all local  options and only  global ones have  their\n            values  survive  over  to  the  operation  following  the   --next\n            instruction.   Global   options   include   --verbose,    --trace,\n            --trace-ascii and --fail-early.\n\n            For example, you can do both a GET and a POST in a  single command\n            line:\n\n                curl www1.example.com --next -d postthis www2.example.com\n            --next can be used several times in a command line\n\n            Examples:\n             curl https://example.com --next -d postthis www2.example.com\n             curl -I https://example.com --next https://example.net/\n\n            See also --parallel and --config.\n\n    --no-alpn\n            (HTTPS) Disable  the  ALPN  TLS  extension.  ALPN  is  enabled  by\n            default if libcurl  was built  with an SSL  library that  supports\n            ALPN. ALPN is used by a libcurl that supports HTTP/2  to negotiate\n            HTTP/2 support with the server during https sessions.\n\n            Note that this is the negated option name documented. You  can use\n            --alpn to enable ALPN.\n\n            Providing --no-alpn multiple  times has no  extra effect.  Disable\n            it again with --alpn.\n\n            Example:\n             curl --no-alpn https://example.com\n\n            See  also  --no-npn  and  --http2.  --no-alpn  requires  that  the\n            underlying libcurl was built to support TLS.\n\n    -N, --no-buffer\n            Disables the  buffering  of  the output  stream.  In  normal  work\n            situations, curl uses a standard  buffered output stream that  has\n            the effect that  it outputs  the data in  chunks, not  necessarily\n            exactly when the  data arrives.  Using this  option disables  that\n            buffering.\n\n            Note that this is the negated option name documented. You  can use\n            --buffer to enable buffering again.\n\n            Providing --no-buffer multiple times has no extra effect.  Disable\n            it again with --buffer.\n\n            Example:\n             curl --no-buffer https://example.com\n\n            See also --progress-bar.\n\n    --no-clobber\n            When used in conjunction with the --output,  --remote-header-name,\n            --remote-name,   or   --remote-name-all   options,   curl   avoids\n            overwriting files that already exist. Instead, a dot and a  number\n            gets appended to the  name of the file  that would be created,  up\n            to filename.100 after which it does not create any file.\n\n            Note that  this is  the negated  option name  documented. You  can\n            thus  use   --clobber  to   enforce   the  clobbering,   even   if\n            --remote-header-name is specified.\n\n            Providing  --no-clobber  multiple  times  has  no  extra   effect.\n            Disable it again with --clobber.\n\n            Example:\n             curl --no-clobber --output local/dir/file https://example.com\n\n            See also --output and --remote-name. Added in 7.83.0.\n\n    --no-keepalive\n            Disables the  use of  keepalive messages  on the  TCP  connection.\n            curl otherwise enables them by default.\n\n            Note that  this is  the negated  option name  documented. You  can\n            thus use --keepalive to enforce keepalive.\n\n            Providing --no-keepalive  multiple  times  has  no  extra  effect.\n            Disable it again with --keepalive.\n\n            Example:\n             curl --no-keepalive https://example.com\n\n            See also --keepalive-time.\n\n    --no-npn\n            (HTTPS) curl never uses NPN,  this option has no effect (added  in\n            7.86.0).\n\n            Disable the  NPN  TLS extension.  NPN  is enabled  by  default  if\n            libcurl was built with  an SSL library  that supports NPN. NPN  is\n            used by  a  libcurl  that  supports  HTTP/2  to  negotiate  HTTP/2\n            support with the server during https sessions.\n\n            Providing --no-npn multiple times has no extra effect. Disable  it\n            again with --npn.\n\n            Example:\n             curl --no-npn https://example.com\n\n            See  also  --no-alpn  and  --http2.  --no-npn  requires  that  the\n            underlying libcurl was built to support TLS.\n\n    --no-progress-meter\n            Option to switch off the  progress meter output without muting  or\n            otherwise  affecting  warning  and  informational  messages   like\n            --silent does.\n\n            Note that  this is  the negated  option name  documented. You  can\n            thus use --progress-meter to enable the progress meter again.\n\n            Providing --no-progress-meter multiple times has no extra  effect.\n            Disable it again with --progress-meter.\n\n            Example:\n             curl --no-progress-meter -o store https://example.com\n\n            See also --verbose and --silent. Added in 7.67.0.\n\n    --no-sessionid\n            (TLS) Disable curl\'s  use of  SSL session-ID  caching. By  default\n            all transfers are done  using the cache.  Note that while  nothing\n            should ever  get  hurt by  attempting  to reuse  SSL  session-IDs,\n            there seem to be broken  SSL implementations in the wild that  may\n            require you to disable this in order for you to succeed.\n\n            Note that  this is  the negated  option name  documented. You  can\n            thus use --sessionid to enforce session-ID caching.\n\n            Providing --no-sessionid  multiple  times  has  no  extra  effect.\n            Disable it again with --sessionid.\n\n            Example:\n             curl --no-sessionid https://example.com\n\n            See also --insecure.\n\n    --noproxy <no-proxy-list>\n            Comma-separated list of  hosts for which  not to  use a proxy,  if\n            one is specified.  The only  wildcard is a  single "*"  character,\n            which matches all hosts, and effectively disables the proxy.  Each\n            name in this  list is matched  as either  a domain which  contains\n            the hostname,  or the  hostname itself.  For example,  "local.com"\n            would match "local.com", "local.com:80", and "www.local.com",  but\n            not "www.notlocal.com".\n\n            This option overrides the  environment variables that disable  the\n            proxy ("no_proxy" and "NO_PROXY") (added  in 7.53.0). If there  is\n            an environment  variable disabling  a proxy,  you can  set the  no\n            proxy list to "" to override it.\n\n            IP addresses specified to this  option can be provided using  CIDR\n            notation  (added  in  7.86.0):   an  appended  slash  and   number\n            specifies the number of network bits out of the address to  use in\n            the comparison.  For  example  "192.168.0.0/16"  would  match  all\n            addresses starting with "192.168".\n\n            If --noproxy  is provided  several times,  the last  set value  is\n            used.\n\n            Example:\n             curl --noproxy "www.example" https://example.com\n\n            See also --proxy.\n\n    --ntlm-wb\n            (HTTP) Enables NTLM much in  the style --ntlm does, but hand  over\n            the authentication to the  separate binary "ntlmauth"  application\n            that is executed when needed.\n\n            Providing --ntlm-wb multiple times has no extra effect.\n\n            Example:\n             curl --ntlm-wb -u user:password https://example.com\n\n            See also --ntlm and --proxy-ntlm.\n\n    --ntlm\n            (HTTP) Use  NTLM authentication.  The NTLM  authentication  method\n            was designed by Microsoft and is used by IIS web servers. It  is a\n            proprietary protocol,  reverse-engineered  by  clever  people  and\n            implemented in curl based on their efforts. This kind of  behavior\n            should not be  endorsed, you  should encourage  everyone who  uses\n            NTLM to switch  to a public  and documented authentication  method\n            instead, such as Digest.\n\n            If you want  to enable  NTLM for your  proxy authentication,  then\n            use --proxy-ntlm.\n\n            Providing --ntlm multiple times has no extra effect.\n\n            Example:\n             curl --ntlm -u user:password https://example.com\n\n            See  also  --proxy-ntlm.  --ntlm  requires  that  the   underlying\n            libcurl  was  built  to  support  TLS.  This  option  is  mutually\n            exclusive to --basic and --negotiate and --digest and --anyauth.\n\n    --oauth2-bearer <token>\n            (IMAP LDAP POP3 SMTP HTTP) Specify the Bearer Token for  OAUTH 2.0\n            server authentication.  The Bearer  Token is  used in  conjunction\n            with the username which can be  specified as part of the --url  or\n            --user options.\n\n            The Bearer  Token  and username  are  formatted according  to  RFC\n            6750.\n\n            If --oauth2-bearer is provided several  times, the last set  value\n            is used.\n\n            Example:\n             curl --oauth2-bearer "mF_9.B5f-4.1JqM" https://example.com\n\n            See also --basic, --ntlm and --digest.\n\n    --output-dir <dir>\n            Specify the  directory  in  which files  should  be  stored,  when\n            --remote-name or --output are used.\n\n            The given  output  directory  is  used for  all  URLs  and  output\n            options on the command line, up until the first --next.\n\n            If the specified  target directory does  not exist, the  operation\n            fails unless --create-dirs is also used.\n\n            If --output-dir is provided several  times, the last set value  is\n            used.\n\n            Example:\n             curl --output-dir "tmp" -O https://example.com\n\n            See also --remote-name and --remote-header-name. Added in 7.73.0.\n\n    -o, --output <file>\n            Write output  to the  given file  instead of  stdout.  If you  are\n            using globbing to fetch multiple  documents, you should quote  the\n            URL and you  can use  "#" followed  by a number  in the  filename.\n            That variable is  then replaced  with the current  string for  the\n            URL being fetched. Like in:\n\n                curl "http://{one,two}.example.com" -o "file_#1.txt"\n\n            or use several variables like:\n\n                curl "http://{site,host}.host[1-5].example" -o "#1_#2"\n\n            You may use this  option as many times as  the number of URLs  you\n            have. For example,  if you specify  two URLs  on the same  command\n            line, you can use it like this:\n\n                curl -o aa example.com -o bb example.net\n\n            and the order  of the  -o options  and the URLs  does not  matter,\n            just that the  first -o is  for the first  URL and  so on, so  the\n            above command line can also be written as\n\n                curl example.com example.net -o aa -o bb\n\n            See also the --create-dirs option to create the local  directories\n            dynamically. Specifying the output as  \'-\' (a single dash)  passes\n            the output to stdout.\n\n            To  suppress  response   bodies,  you  can   redirect  output   to\n            /dev/null:\n\n                curl example.com -o /dev/null\n\n            Or for Windows:\n\n                curl example.com -o nul\n\n            Specify the  filename  as single  minus  to force  the  output  to\n            stdout, to  override curl\'s  internal  binary output  in  terminal\n            prevention:\n\n                curl https://example.com/jpeg -o -\n            --output can be used several times in a command line\n\n            Examples:\n             curl -o file https://example.com\n             curl "http://{one,two}.example.com" -o "file_#1.txt"\n             curl "http://{site,host}.host[1-5].example" -o "#1_#2"\n             curl -o file https://example.com -o file2 https://example.net\n\n            See      also      --remote-name,      --remote-name-all       and\n            --remote-header-name.\n\n    --parallel-immediate\n            When doing parallel transfers, this option instructs curl that  it\n            should rather prefer  opening up more  connections in parallel  at\n            once rather than waiting to see  if new transfers can be added  as\n            multiplexed streams on another connection.\n\n            This option is global and does  not need to be specified for  each\n            use of --next.\n\n            Providing  --parallel-immediate  multiple   times  has  no   extra\n            effect. Disable it again with --no-parallel-immediate.\n\n            Example:\n             curl --parallel-immediate -Z https://example.com -o file1 https://example.com -o file2\n\n            See also --parallel and --parallel-max. Added in 7.68.0.\n\n    --parallel-max <num>\n            When asked  to  do  parallel  transfers,  using  --parallel,  this\n            option  controls   the  maximum   amount   of  transfers   to   do\n            simultaneously.\n\n            This option is global and does  not need to be specified for  each\n            use of --next.\n\n            The default is 50.\n\n            If --parallel-max is  provided several times,  the last set  value\n            is used.\n\n            Example:\n             curl --parallel-max 100 -Z https://example.com ftp://example.com/\n\n            See also --parallel. Added in 7.66.0.\n\n    -Z, --parallel\n            Makes curl perform its  transfers in parallel  as compared to  the\n            regular serial manner.\n\n            This option is global and does  not need to be specified for  each\n            use of --next.\n\n            Providing --parallel multiple times  has no extra effect.  Disable\n            it again with --no-parallel.\n\n            Example:\n             curl --parallel https://example.com -o file1 https://example.com -o file2\n\n            See also --next and --verbose. Added in 7.66.0.\n\n    --pass <phrase>\n            (SSH TLS) Passphrase for the private key.\n\n            If --pass is provided several times, the last set value is used.\n\n            Example:\n             curl --pass secret --key file https://example.com\n\n            See also --key and --user.\n\n    --path-as-is\n            Do not handle  sequences of  /../ or  /./ in the  given URL  path.\n            Normally curl squashes or merges  them according to standards  but\n            with this option set you tell it not to do that.\n\n            Providing  --path-as-is  multiple  times  has  no  extra   effect.\n            Disable it again with --no-path-as-is.\n\n            Example:\n             curl --path-as-is https://example.com/../../etc/passwd\n\n            See also --request-target.\n\n    --pinnedpubkey <hashes>\n            (TLS) Use the specified public key file (or hashes) to  verify the\n            peer. This can be a path to a file which contains a  single public\n            key in PEM or DER format,  or any number of base64 encoded  sha256\n            hashes preceded by \'sha256//\' and separated by \';\'.\n\n            When negotiating  a TLS  or  SSL connection,  the server  sends  a\n            certificate indicating  its identity.  A public  key is  extracted\n            from this certificate and if it does not exactly match  the public\n            key provided to  this option,  curl aborts  the connection  before\n            sending or receiving any data.\n\n            This option is independent of  option --insecure. If you use  both\n            options together then the peer is still verified by public key.\n\n            PEM/DER support:\n\n            OpenSSL and GnuTLS,  wolfSSL (added in  7.43.0), mbedTLS ,  Secure\n            Transport macOS 10.7+/iOS 10+ (7.54.1), Schannel (7.58.1)\n\n            sha256 support:\n\n            OpenSSL, GnuTLS  and wolfSSL,  mbedTLS (added  in 7.47.0),  Secure\n            Transport macOS 10.7+/iOS 10+ (7.54.1), Schannel (7.58.1)\n\n            Other SSL backends not supported.\n\n            If --pinnedpubkey is  provided several times,  the last set  value\n            is used.\n\n            Examples:\n             curl --pinnedpubkey keyfile https://example.com\n             curl --pinnedpubkey \'sha256//ce118b51897f4452dc\' https://example.com\n\n            See also --hostpubsha256.\n\n    --post301\n            (HTTP) Respect RFC  7231/6.4.2 and  do not  convert POST  requests\n            into GET  requests  when following  a  301 redirect.  The  non-RFC\n            behavior  is  ubiquitous  in  web  browsers,  so  curl  does   the\n            conversion by default to  maintain consistency. However, a  server\n            may require  a POST to  remain a  POST after  such a  redirection.\n            This option is meaningful only when using --location.\n\n            Providing --post301 multiple  times has no  extra effect.  Disable\n            it again with --no-post301.\n\n            Example:\n             curl --post301 --location -d "data" https://example.com\n\n            See also --post302, --post303 and --location.\n\n    --post302\n            (HTTP) Respect RFC  7231/6.4.3 and  do not  convert POST  requests\n            into GET  requests  when following  a  302 redirect.  The  non-RFC\n            behavior  is  ubiquitous  in  web  browsers,  so  curl  does   the\n            conversion by default to  maintain consistency. However, a  server\n            may require  a POST to  remain a  POST after  such a  redirection.\n            This option is meaningful only when using --location.\n\n            Providing --post302 multiple  times has no  extra effect.  Disable\n            it again with --no-post302.\n\n            Example:\n             curl --post302 --location -d "data" https://example.com\n\n            See also --post301, --post303 and --location.\n\n    --post303\n            (HTTP) Violate RFC  7231/6.4.4 and  do not  convert POST  requests\n            into GET  requests  when  following 303  redirect.  A  server  may\n            require a  POST to remain  a POST  after a  303 redirection.  This\n            option is meaningful only when using --location.\n\n            Providing --post303 multiple  times has no  extra effect.  Disable\n            it again with --no-post303.\n\n            Example:\n             curl --post303 --location -d "data" https://example.com\n\n            See also --post302, --post301 and --location.\n\n    --preproxy [protocol://]host[:port]\n            Use the  specified SOCKS  proxy before  connecting to  an HTTP  or\n            HTTPS --proxy. In  such a case  curl first  connects to the  SOCKS\n            proxy and  then connects  (through  SOCKS) to  the HTTP  or  HTTPS\n            proxy. Hence pre proxy.\n\n            The pre  proxy  string  should be  specified  with  a  protocol://\n            prefix to  specify  alternative proxy  protocols.  Use  socks4://,\n            socks4a://, socks5:// or socks5h:// to request the specific  SOCKS\n            version to be used.  No protocol specified  makes curl default  to\n            SOCKS4.\n\n            If the port  number is not  specified in the  proxy string, it  is\n            assumed to be 1080.\n\n            User and password that might  be provided in the proxy string  are\n            URL  decoded  by  curl.  This  allows  you  to  pass   in  special\n            characters such as @ by using %40 or pass in a colon with %3a.\n\n            If --preproxy is  provided several  times, the last  set value  is\n            used.\n\n            Example:\n             curl --preproxy socks5://proxy.example -x http://http.example https://example.com\n\n            See also --proxy and --socks5. Added in 7.52.0.\n\n    -#, --progress-bar\n            Make curl  display  transfer progress  as  a simple  progress  bar\n            instead of the standard, more informational, meter.\n\n            This progress bar  draws a  single line of  \'#\' characters  across\n            the screen and shows a  percentage if the transfer size is  known.\n            For transfers without a known size, there is a space  ship (-=o=-)\n            that  moves  back  and  forth   but  only  while  data  is   being\n            transferred, with a set of flying hash sign symbols on top.\n\n            This option is global and does  not need to be specified for  each\n            use of --next.\n\n            Providing --progress-bar  multiple  times  has  no  extra  effect.\n            Disable it again with --no-progress-bar.\n\n            Example:\n             curl -# -O https://example.com\n\n            See also --styled-output.\n\n    --proto-default <protocol>\n            Use protocol for any provided URL missing a scheme.\n\n            An    unknown    or    unsupported    protocol    causes     error\n            CURLE_UNSUPPORTED_PROTOCOL.\n\n            This option does not change the default proxy protocol (http).\n\n            Without this  option  set,  curl guesses  protocol  based  on  the\n            hostname, see --url for details.\n\n            If --proto-default is provided several  times, the last set  value\n            is used.\n\n            Example:\n             curl --proto-default https ftp.example.com\n\n            See also --proto and --proto-redir.\n\n    --proto-redir <protocols>\n            Limit what protocols  to allow on  redirects. Protocols denied  by\n            --proto are not  overridden by  this option. See  --proto for  how\n            protocols are represented.\n\n            Example, allow only HTTP and HTTPS on redirect:\n\n                curl --proto-redir -all,http,https http://example.com\n\n            By  default  curl  only  allows  HTTP,  HTTPS,  FTP  and  FTPS  on\n            redirects (added in  7.65.2). Specifying all  or +all enables  all\n            protocols on redirects, which is not good for security.\n\n            If --proto-redir is provided several times, the last set value  is\n            used.\n\n            Example:\n             curl --proto-redir =http,https https://example.com\n\n            See also --proto.\n\n    --proto <protocols>\n            Limit  what  protocols  to  allow  for  transfers.  Protocols  are\n            evaluated left  to right,  are  comma separated,  and are  each  a\n            protocol name  or  \'all\',  optionally prefixed  by  zero  or  more\n            modifiers. Available modifiers are:\n\n            +\n\n                Permit  this  protocol  in   addition  to  protocols   already\n                permitted (this is the default if no modifier is used).\n\n            -\n\n                Deny this protocol,  removing it  from the  list of  protocols\n                already permitted.\n\n            =\n\n                Permit  only  this   protocol  (ignoring   the  list   already\n                permitted),  though   subject   to   later   modification   by\n                subsequent entries in the comma separated list.\n\n        .RE .IP\n\n                For example:  --proto -ftps  uses the  default protocols,  but\n                disables ftps\n\n                --proto -all,https,+http only enables http and https\n\n                --proto =http,https also only enables http and https\n\n                Unknown and disabled protocols produce a warning. This  allows\n                scripts to safely  rely on being  able to disable  potentially\n                dangerous protocols,  without relying  upon support  for  that\n                protocol being built into curl to avoid an error.\n\n                This option  can be  used multiple  times, in  which case  the\n                effect is the  same as  concatenating the  protocols into  one\n                instance of the option.\n\n            If --proto is provided several times, the last set value is used.\n\n            Example:\n             curl --proto =http,https,sftp https://example.com\n\n            See also --proto-redir and --proto-default.\n\n    --proxy-anyauth\n            Automatically  pick   a   suitable  authentication   method   when\n            communicating with  the  given HTTP  proxy.  This might  cause  an\n            extra request/response round-trip.\n\n            Providing --proxy-anyauth multiple times has no extra effect.\n\n            Example:\n             curl --proxy-anyauth --proxy-user user:passwd -x proxy https://example.com\n\n            See also --proxy, --proxy-basic and --proxy-digest.\n\n    --proxy-basic\n            Use HTTP Basic  authentication when communicating  with the  given\n            proxy. Use --basic  for enabling  HTTP Basic with  a remote  host.\n            Basic  is  the  default  authentication  method  curl  uses   with\n            proxies.\n\n            Providing --proxy-basic multiple times has no extra effect.\n\n            Example:\n             curl --proxy-basic --proxy-user user:passwd -x proxy https://example.com\n\n            See also --proxy, --proxy-anyauth and --proxy-digest.\n\n    --proxy-ca-native\n            (TLS) Use the CA store from the native operating system  to verify\n            the HTTPS proxy. By  default, curl uses a  CA store provided in  a\n            single  file  or  directory,  but   when  using  this  option   it\n            interfaces the operating system\'s own vault.\n\n            This option works for curl  on Windows when built to use  OpenSSL,\n            wolfSSL (added in 8.3.0) or GnuTLS (added in 8.5.0). When  curl on\n            Windows is  built to  use Schannel,  this feature  is implied  and\n            curl then only uses the native CA store.\n\n            Providing --proxy-ca-native multiple  times has  no extra  effect.\n            Disable it again with --no-proxy-ca-native.\n\n            Example:\n             curl --ca-native https://example.com\n\n            See also --cacert, --capath and --insecure. Added in 8.2.0.\n\n    --proxy-cacert <file>\n            Same as --cacert but used in HTTPS proxy context.\n\n            If --proxy-cacert is  provided several times,  the last set  value\n            is used.\n\n            Example:\n             curl --proxy-cacert CA-file.txt -x https://proxy https://example.com\n\n            See also --proxy-capath, --cacert, --capath and --proxy. Added  in\n            7.52.0.\n\n    --proxy-capath <dir>\n            Same as --capath but used in HTTPS proxy context.\n\n            Use the  specified  certificate  directory to  verify  the  proxy.\n            Multiple paths  can  be provided  by  separated with  colon  (":")\n            (e.g.  "path1:path2:path3").  The  certificates  must  be  in  PEM\n            format, and if curl is  built against OpenSSL, the directory  must\n            have been  processed  using  the c_rehash  utility  supplied  with\n            OpenSSL. Using --proxy-capath  can allow  OpenSSL-powered curl  to\n            make   SSL-connections   much   more   efficiently   than    using\n            --proxy-cacert  if  the  --proxy-cacert  file  contains  many   CA\n            certificates.\n\n            If this option is set, the default capath value is ignored.\n\n            If --proxy-capath is  provided several times,  the last set  value\n            is used.\n\n            Example:\n             curl --proxy-capath /local/directory -x https://proxy https://example.com\n\n            See also --proxy-cacert, --proxy and --capath. Added in 7.52.0.\n\n    --proxy-cert-type <type>\n            Same as --cert-type but used in HTTPS proxy context.\n\n            If --proxy-cert-type  is  provided  several times,  the  last  set\n            value is used.\n\n            Example:\n             curl --proxy-cert-type PEM --proxy-cert file -x https://proxy https://example.com\n\n            See also --proxy-cert. Added in 7.52.0.\n\n    --proxy-cert <cert[:passwd]>\n            Same as --cert but used in HTTPS proxy context.\n\n            If --proxy-cert is provided several  times, the last set value  is\n            used.\n\n            Example:\n             curl --proxy-cert file -x https://proxy https://example.com\n\n            See also --proxy-cert-type. Added in 7.52.0.\n\n    --proxy-ciphers <list>\n            Same as --ciphers but used in HTTPS proxy context.\n\n            Specifies which  ciphers to  use in  the connection  to the  HTTPS\n            proxy. The list of ciphers must specify valid ciphers. Read  up on\n            SSL cipher list details on this URL:\n\n            https://curl.se/docs/ssl-ciphers.html\n\n            If --proxy-ciphers is provided several  times, the last set  value\n            is used.\n\n            Example:\n             curl --proxy-ciphers ECDHE-ECDSA-AES256-CCM8 -x https://proxy https://example.com\n\n            See also --ciphers, --curves and --proxy. Added in 7.52.0.\n\n    --proxy-crlfile <file>\n            Same as --crlfile but used in HTTPS proxy context.\n\n            If --proxy-crlfile is provided several  times, the last set  value\n            is used.\n\n            Example:\n             curl --proxy-crlfile rejects.txt -x https://proxy https://example.com\n\n            See also --crlfile and --proxy. Added in 7.52.0.\n\n    --proxy-digest\n            Use HTTP Digest authentication  when communicating with the  given\n            proxy. Use --digest for enabling HTTP Digest with a remote host.\n\n            Providing --proxy-digest multiple times has no extra effect.\n\n            Example:\n             curl --proxy-digest --proxy-user user:passwd -x proxy https://example.com\n\n            See also --proxy, --proxy-anyauth and --proxy-basic.\n\n    --proxy-header <header/@file>\n            (HTTP) Extra header to  include in the  request when sending  HTTP\n            to a proxy. You may specify  any number of extra headers. This  is\n            the equivalent option to --header  but is for proxy  communication\n            only like  in CONNECT  requests when  you want  a separate  header\n            sent to the proxy to what is sent to the actual remote host.\n\n            curl makes sure that each header you add/replace is sent  with the\n            proper end-of-line marker, you should thus not add that as  a part\n            of the header content:  do not add  newlines or carriage  returns,\n            they only mess things up for you.\n\n            Headers specified with  this option are  not included in  requests\n            that curl knows are not be sent to a proxy.\n\n            This option can take  an argument in  @filename style, which  then\n            adds a header for each line  in the input file (added in  7.55.0).\n            Using @- makes curl read the headers from stdin.\n\n            This option  can  be  used multiple  times  to  add/replace/remove\n            multiple headers.\n\n            --proxy-header can be used several times in a command line\n\n            Examples:\n             curl --proxy-header "X-First-Name: Joe" -x http://proxy https://example.com\n             curl --proxy-header "User-Agent: surprise" -x http://proxy https://example.com\n             curl --proxy-header "Host:" -x http://proxy https://example.com\n\n            See also --proxy.\n\n    --proxy-http2\n            (HTTP) Negotiate  HTTP/2  with an  HTTPS  proxy. The  proxy  might\n            still only  offer  HTTP/1  and  then curl  sticks  to  using  that\n            version.\n\n            This has no effect for any other kinds of proxies.\n\n            Providing  --proxy-http2  multiple  times  has  no  extra  effect.\n            Disable it again with --no-proxy-http2.\n\n            Example:\n             curl --proxy-http2 -x proxy https://example.com\n\n            See also  --proxy.  --proxy-http2  requires  that  the  underlying\n            libcurl was built to support HTTP/2. Added in 8.1.0.\n\n    --proxy-insecure\n            Same as --insecure but used in HTTPS proxy context.\n\n            Every secure  connection  curl  makes is  verified  to  be  secure\n            before the transfer takes place.  This option makes curl skip  the\n            verification step with a proxy and proceed without checking.\n\n            When this  option  is  not used  for  a proxy  using  HTTPS,  curl\n            verifies the  proxy\'s TLS  certificate before  it continues:  that\n            the  certificate  contains  the  right  name  which  matches   the\n            hostname  and that  the  certificate  has  been  signed  by  a  CA\n            certificate present in  the cert store.  See this online  resource\n            for further details: https://curl.se/docs/sslcerts.html\n\n            WARNING: using  this  option  makes  the  transfer  to  the  proxy\n            insecure.\n\n            Providing --proxy-insecure  multiple times  has no  extra  effect.\n            Disable it again with --no-proxy-insecure.\n\n            Example:\n             curl --proxy-insecure -x https://proxy https://example.com\n\n            See also --proxy and --insecure. Added in 7.52.0.\n\n    --proxy-key-type <type>\n            Same as --key-type but used in HTTPS proxy context.\n\n            If --proxy-key-type is provided several times, the last set  value\n            is used.\n\n            Example:\n             curl --proxy-key-type DER --proxy-key here -x https://proxy https://example.com\n\n            See also --proxy-key and --proxy. Added in 7.52.0.\n\n    --proxy-key <key>\n            Same as --key but used in HTTPS proxy context.\n\n            If --proxy-key is provided  several times, the  last set value  is\n            used.\n\n            Example:\n             curl --proxy-key here -x https://proxy https://example.com\n\n            See also --proxy-key-type and --proxy. Added in 7.52.0.\n\n    --proxy-negotiate\n            Use HTTP  Negotiate  (SPNEGO)  authentication  when  communicating\n            with the given proxy. Use --negotiate for enabling HTTP  Negotiate\n            (SPNEGO) with a remote host.\n\n            Providing --proxy-negotiate multiple times has no extra effect.\n\n            Example:\n             curl --proxy-negotiate --proxy-user user:passwd -x proxy https://example.com\n\n            See also --proxy-anyauth and --proxy-basic.\n\n    --proxy-ntlm\n            Use HTTP  NTLM authentication  when communicating  with the  given\n            proxy. Use --ntlm for enabling NTLM with a remote host.\n\n            Providing --proxy-ntlm multiple times has no extra effect.\n\n            Example:\n             curl --proxy-ntlm --proxy-user user:passwd -x http://proxy https://example.com\n\n            See also --proxy-negotiate and --proxy-anyauth.\n\n    --proxy-pass <phrase>\n            Same as --pass but used in HTTPS proxy context.\n\n            If --proxy-pass is provided several  times, the last set value  is\n            used.\n\n            Example:\n             curl --proxy-pass secret --proxy-key here -x https://proxy https://example.com\n\n            See also --proxy and --proxy-key. Added in 7.52.0.\n\n    --proxy-pinnedpubkey <hashes>\n            (TLS) Use the specified public key file (or hashes) to  verify the\n            proxy. This  can be  a  path to  a file  which contains  a  single\n            public key in PEM or DER  format, or any number of base64  encoded\n            sha256 hashes preceded by \'sha256//\' and separated by \';\'.\n\n            When negotiating  a TLS  or  SSL connection,  the server  sends  a\n            certificate indicating  its identity.  A public  key is  extracted\n            from this certificate and if it does not exactly match  the public\n            key provided to  this option,  curl aborts  the connection  before\n            sending or receiving any data.\n\n            If --proxy-pinnedpubkey is  provided several times,  the last  set\n            value is used.\n\n            Examples:\n             curl --proxy-pinnedpubkey keyfile https://example.com\n             curl --proxy-pinnedpubkey \'sha256//ce118b51897f4452dc\' https://example.com\n\n            See also --pinnedpubkey and --proxy. Added in 7.59.0.\n\n    --proxy-service-name <name>\n            Set the service name for proxy negotiation.\n\n            If --proxy-service-name is  provided several times,  the last  set\n            value is used.\n\n            Example:\n             curl --proxy-service-name "shrubbery" -x proxy https://example.com\n\n            See also --service-name and --proxy.\n\n    --proxy-ssl-allow-beast\n            Same as --ssl-allow-beast but used in HTTPS proxy context.\n\n            Providing --proxy-ssl-allow-beast  multiple  times  has  no  extra\n            effect. Disable it again with --no-proxy-ssl-allow-beast.\n\n            Example:\n             curl --proxy-ssl-allow-beast -x https://proxy https://example.com\n\n            See also --ssl-allow-beast and --proxy. Added in 7.52.0.\n\n    --proxy-ssl-auto-client-cert\n            Same as --ssl-auto-client-cert but used in HTTPS proxy context.\n\n            This is only supported by Schannel.\n\n            Providing  --proxy-ssl-auto-client-cert  multiple  times  has   no\n            extra       effect.       Disable       it       again        with\n            --no-proxy-ssl-auto-client-cert.\n\n            Example:\n             curl --proxy-ssl-auto-client-cert -x https://proxy https://example.com\n\n            See also --ssl-auto-client-cert and --proxy. Added in 7.77.0.\n\n    --proxy-tls13-ciphers <ciphersuite list>\n            (TLS) Specify  which cipher  suites to  use in  the connection  to\n            your HTTPS proxy when it  negotiates TLS 1.3. The list of  ciphers\n            suites must  specify valid  ciphers.  Read up  on TLS  1.3  cipher\n            suite details on this URL:\n\n            https://curl.se/docs/ssl-ciphers.html\n\n            This option  is currently  used only  when curl  is  built to  use\n            OpenSSL 1.1.1 or later. If  you are using a different SSL  backend\n            you  can  try  setting  TLS   1.3  cipher  suites  by  using   the\n            --proxy-ciphers option.\n\n            If --proxy-tls13-ciphers is provided  several times, the last  set\n            value is used.\n\n            Example:\n             curl --proxy-tls13-ciphers TLS_AES_128_GCM_SHA256 -x proxy https://example.com\n\n            See also --tls13-ciphers, --curves  and --proxy-ciphers. Added  in\n            7.61.0.\n\n    --proxy-tlsauthtype <type>\n            Same as --tlsauthtype but used in HTTPS proxy context.\n\n            If --proxy-tlsauthtype  is provided  several times,  the last  set\n            value is used.\n\n            Example:\n             curl --proxy-tlsauthtype SRP -x https://proxy https://example.com\n\n            See also --proxy and --proxy-tlsuser. Added in 7.52.0.\n\n    --proxy-tlspassword <string>\n            Same as --tlspassword but used in HTTPS proxy context.\n\n            If --proxy-tlspassword  is provided  several times,  the last  set\n            value is used.\n\n            Example:\n             curl --proxy-tlspassword passwd -x https://proxy https://example.com\n\n            See also --proxy and --proxy-tlsuser. Added in 7.52.0.\n\n    --proxy-tlsuser <name>\n            Same as --tlsuser but used in HTTPS proxy context.\n\n            If --proxy-tlsuser is provided several  times, the last set  value\n            is used.\n\n            Example:\n             curl --proxy-tlsuser smith -x https://proxy https://example.com\n\n            See also --proxy and --proxy-tlspassword. Added in 7.52.0.\n\n    --proxy-tlsv1\n            Same as --tlsv1 but used in HTTPS proxy context.\n\n            Providing --proxy-tlsv1 multiple times has no extra effect.\n\n            Example:\n             curl --proxy-tlsv1 -x https://proxy https://example.com\n\n            See also --proxy. Added in 7.52.0.\n\n    -U, --proxy-user <user:password>\n            Specify   the   username   and   password   to   use   for   proxy\n            authentication.\n\n            If you  use  a Windows  SSPI-enabled  curl binary  and  do  either\n            Negotiate or NTLM authentication then you can tell curl to  select\n            the username and  password from your  environment by specifying  a\n            single colon with this option: "-U :".\n\n            On systems where it  works, curl hides  the given option  argument\n            from process listings. This is  not enough to protect  credentials\n            from possibly getting seen  by other users  on the same system  as\n            they  still  are  visible  for  a  moment  before  cleared.   Such\n            sensitive data should be retrieved from a file instead or  similar\n            and never used in clear text in a command line.\n\n            If --proxy-user is provided several  times, the last set value  is\n            used.\n\n            Example:\n             curl --proxy-user smith:secret -x proxy https://example.com\n\n            See also --proxy-pass.\n\n    -x, --proxy [protocol://]host[:port]\n            Use the specified proxy.\n\n            The proxy string can  be specified with  a protocol:// prefix.  No\n            protocol specified or http:// it is treated as an HTTP  proxy. Use\n            socks4://,  socks4a://,  socks5://  or  socks5h://  to  request  a\n            specific SOCKS version to be used.\n\n            Unix domain sockets are supported  for socks proxy. Set  localhost\n            for the host part. e.g. socks5h://localhost/path/to/socket.sock\n\n            HTTPS proxy support  works set with  the https:// protocol  prefix\n            for OpenSSL  and  GnuTLS (added  in  7.52.0). It  also  works  for\n            BearSSL, mbedTLS, rustls, Schannel,  Secure Transport and  wolfSSL\n            (added in 7.87.0).\n\n            Unrecognized  and  unsupported  proxy  protocols  cause  an  error\n            (added in 7.52.0). Ancient  curl versions ignored unknown  schemes\n            and used http:// instead.\n\n            If the port  number is not  specified in the  proxy string, it  is\n            assumed to be 1080.\n\n            This option overrides existing environment variables that set  the\n            proxy to  use.  If there  is  an environment  variable  setting  a\n            proxy, you can set proxy to "" to override it.\n\n            All  operations  that  are  performed  over  an  HTTP  proxy   are\n            transparently converted to  HTTP. It means  that certain  protocol\n            specific operations might not be  available. This is not the  case\n            if  you  can   tunnel  through   the  proxy,  as   one  with   the\n            --proxytunnel option.\n\n            User and password that might  be provided in the proxy string  are\n            URL  decoded  by  curl.  This  allows  you  to  pass   in  special\n            characters such as @ by using %40 or pass in a colon with %3a.\n\n            The proxy  host  can  be  specified  the same  way  as  the  proxy\n            environment variables,  including  the protocol  prefix  (http://)\n            and the embedded user + password.\n\n            When a proxy is used, the active FTP mode as set  with --ftp-port,\n            cannot be used.\n\n            If --proxy is provided several times, the last set value is used.\n\n            Example:\n             curl --proxy http://proxy.example https://example.com\n\n            See also --socks5 and --proxy-basic.\n\n    --proxy1.0 <host[:port]>\n            Use the  specified  HTTP 1.0  proxy. If  the  port number  is  not\n            specified, it is assumed at port 1080.\n\n            The only  difference  between  this  and  the  HTTP  proxy  option\n            --proxy, is  that  attempts  to  use  CONNECT  through  the  proxy\n            specifies an HTTP 1.0 protocol instead of the default HTTP 1.1.\n\n            Providing --proxy1.0 multiple times has no extra effect.\n\n            Example:\n             curl --proxy1.0 http://proxy https://example.com\n\n            See also --proxy, --socks5 and --preproxy.\n\n    -p, --proxytunnel\n            When an HTTP proxy is used --proxy, this option makes  curl tunnel\n            the traffic through the  proxy. The tunnel  approach is made  with\n            the HTTP proxy CONNECT request and requires that the proxy  allows\n            direct connect  to the  remote port  number curl  wants to  tunnel\n            through to.\n\n            To suppress proxy  CONNECT response  headers when curl  is set  to\n            output headers use --suppress-connect-headers.\n\n            Providing  --proxytunnel  multiple  times  has  no  extra  effect.\n            Disable it again with --no-proxytunnel.\n\n            Example:\n             curl --proxytunnel -x http://proxy https://example.com\n\n            See also --proxy.\n\n    --pubkey <key>\n            (SFTP SCP) Public key filename. Allows you to provide your  public\n            key in this separate file.\n\n            curl attempts to  automatically extract  the public  key from  the\n            private  key  file,  so  passing  this  option  is  generally  not\n            required. Note that  this public key  extraction requires  libcurl\n            to be linked  against a copy  of libssh2 1.2.8  or higher that  is\n            itself linked against OpenSSL.\n\n            If --pubkey  is provided  several  times, the  last set  value  is\n            used.\n\n            Example:\n             curl --pubkey file.pub sftp://example.com/\n\n            See also --pass.\n\n    -Q, --quote <command>\n            (FTP SFTP) Send  an arbitrary command  to the  remote FTP or  SFTP\n            server. Quote commands  are sent BEFORE  the transfer takes  place\n            (just after  the initial PWD  command in  an FTP  transfer, to  be\n            exact). To make commands take  place after a successful  transfer,\n            prefix them with a dash \'-\'.\n\n            (FTP only) To  make commands be  sent after  curl has changed  the\n            working directory,  just  before  the  file  transfer  command(s),\n            prefix the  command  with a  \'+\'. This  is  not performed  when  a\n            directory listing is performed.\n\n            You may specify any number of commands.\n\n            By default  curl stops  at first  failure. To  make curl  continue\n            even if the  command fails,  prefix the command  with an  asterisk\n            (*). Otherwise,  if the  server  returns failure  for one  of  the\n            commands, the entire operation is aborted.\n\n            You must  send  syntactically  correct FTP  commands  as  RFC  959\n            defines to FTP  servers, or one  of the  commands listed below  to\n            SFTP servers.\n\n            SFTP is a binary  protocol. Unlike for  FTP, curl interprets  SFTP\n            quote  commands  itself  before   sending  them  to  the   server.\n            Filenames may be  quoted shell-style  to embed  spaces or  special\n            characters. Following  is the  list of  all supported  SFTP  quote\n            commands:\n\n            atime date file\n\n                The atime command sets the last access time of the  file named\n                by the file operand. The  date expression can be all sorts  of\n                date strings,  see  the  curl_getdate(3)  man  page  for  date\n                expression details. (Added in 7.73.0)\n\n            chgrp group file\n\n                The chgrp command sets the group  ID of the file named by  the\n                file operand to the group  ID specified by the group  operand.\n                The group operand is a decimal integer group ID.\n\n            chmod mode file\n\n                The  chmod  command  modifies  the  file  mode  bits  of   the\n                specified file.  The mode  operand is  an octal  integer  mode\n                number.\n\n            chown user file\n\n                The chown  command sets the  owner of  the file  named by  the\n                file operand to  the user  ID specified by  the user  operand.\n                The user operand is a decimal integer user ID.\n\n            ln source_file target_file\n\n                The ln  and symlink  commands create  a symbolic  link at  the\n                target_file location pointing to the source_file location.\n\n            mkdir directory_name\n\n                The  mkdir  command  creates   the  directory  named  by   the\n                directory_name operand.\n\n            mtime date file\n\n                The mtime command sets the last modification time of the  file\n                named by  the file  operand. The  date expression  can be  all\n                sorts of date  strings, see the  curl_getdate(3) man page  for\n                date expression details. (Added in 7.73.0)\n\n            pwd\n\n                The pwd command returns the absolute path name of the  current\n                working directory.\n\n            rename source target\n\n                The rename command renames the file or directory named by  the\n                source operand to  the destination  path named  by the  target\n                operand.\n\n            rm file\n\n                The  rm  command  removes  the  file  specified  by  the  file\n                operand.\n\n            rmdir directory\n\n                The rmdir  command removes  the directory  entry specified  by\n                the directory operand, provided it is empty.\n\n            symlink source_file target_file\n\n                See ln.\n\n            --quote can be used several times in a command line\n\n            Example:\n             curl --quote "DELE file" ftp://example.com/foo\n\n            See also --request.\n\n    --random-file <file>\n            Deprecated option.  This  option  is ignored  (added  in  7.84.0).\n            Prior to that it only  had an effect on  curl if built to use  old\n            versions of OpenSSL.\n\n            Specify the path  name to  file containing random  data. The  data\n            may be used to seed the random engine for SSL connections.\n\n            If --random-file is provided several times, the last set value  is\n            used.\n\n            Example:\n             curl --random-file rubbish https://example.com\n\n            See also --egd-file.\n\n    -r, --range <range>\n            (HTTP FTP  SFTP  FILE)  Retrieve  a byte  range  (i.e.  a  partial\n            document) from an HTTP/1.1,  FTP or SFTP  server or a local  FILE.\n            Ranges can be specified in a number of ways.\n\n            0-499\n\n                specifies the first 500 bytes\n\n            500-999\n\n                specifies the second 500 bytes\n\n            -500\n\n                specifies the last 500 bytes\n\n            9500-\n\n                specifies the bytes from offset 9500 and forward\n\n            0-0,-1\n\n                specifies the first and last byte only(*)(HTTP)\n\n            100-199,500-599\n\n                specifies two separate 100-byte ranges(*) (HTTP)\n\n        .RE .IP\n\n                (*) = NOTE that these  make the server reply with a  multipart\n                response,  which  is  returned  as-is  by  curl!  Parsing   or\n                otherwise transforming this response is the responsibility  of\n                the caller.\n\n                Only digit  characters  (0-9) are  valid  in the  \'start\'  and\n                \'stop\'  fields  of  the   \'start-stop\'  range  syntax.  If   a\n                non-digit character  is  given  in  the  range,  the  server\'s\n                response   is   unspecified,   depending   on   the   server\'s\n                configuration.\n\n                Many HTTP/1.1 servers  do not  have this  feature enabled,  so\n                that when you attempt  to get a  range, curl instead gets  the\n                whole document.\n\n                FTP  and  SFTP  range   downloads  only  support  the   simple\n                \'start-stop\'  syntax  (optionally  with  one  of  the  numbers\n                omitted). FTP use depends on the extended FTP command SIZE.\n\n            If --range is provided several times, the last set value is used.\n\n            Example:\n             curl --range 22-44 https://example.com\n\n            See also --continue-at and --append.\n\n    --rate <max request rate>\n            Specify the maximum transfer frequency you allow curl to use  - in\n            number of transfer starts per time unit (sometimes called  request\n            rate). Without this option, curl starts the next transfer as  fast\n            as possible.\n\n            If given several  URLs and  a transfer completes  faster than  the\n            allowed rate, curl  waits until  the next transfer  is started  to\n            maintain the  requested  rate.  This option  has  no  effect  when\n            --parallel is used.\n\n            The request  rate  is provided  as "N/U"  where  N is  an  integer\n            number and U  is a time  unit. Supported  units are \'s\'  (second),\n            \'m\' (minute), \'h\'  (hour) and \'d\'  /(day, as in  a 24 hour  unit).\n            The default  time  unit, if  no "/U"  is  provided, is  number  of\n            transfers per hour.\n\n            If curl  is told  to allow  10 requests  per minute,  it does  not\n            start the  next request  until 6  seconds have  elapsed since  the\n            previous transfer was started.\n\n            This  function  uses  millisecond   resolution.  If  the   allowed\n            frequency is  set  more than  1000  per second,  it  instead  runs\n            unrestricted.\n\n            When retrying transfers, enabled with --retry, the separate  retry\n            delay logic is used and not this setting.\n\n            This option is global and does  not need to be specified for  each\n            use of --next.\n\n            If --rate is provided several times, the last set value is used.\n\n            Examples:\n             curl --rate 2/s https://example.com ...\n             curl --rate 3/h https://example.com ...\n             curl --rate 14/m https://example.com ...\n\n            See also --limit-rate and --retry-delay. Added in 7.84.0.\n\n    --raw\n            (HTTP) When  used,  it  disables all  internal  HTTP  decoding  of\n            content or transfer  encodings and  instead makes  them passed  on\n            unaltered, raw.\n\n            Providing --raw multiple  times has  no extra  effect. Disable  it\n            again with --no-raw.\n\n            Example:\n             curl --raw https://example.com\n\n            See also --tr-encoding.\n\n    -e, --referer <URL>\n            (HTTP) Set the referrer URL in the HTTP request. This can  also be\n            set with the --header  flag of course.  When used with  --location\n            you  can append  ";auto""  to  the  --referer  URL  to  make  curl\n            automatically set the  previous URL  when it  follows a  Location:\n            header. The ";auto" string can be  used alone, even if you do  not\n            set an initial --referer.\n\n            If --referer  is provided  several times,  the last  set value  is\n            used.\n\n            Examples:\n             curl --referer "https://fake.example" https://example.com\n             curl --referer "https://fake.example;auto" -L https://example.com\n             curl --referer ";auto" -L https://example.com\n\n            See also --user-agent and --header.\n\n    -J, --remote-header-name\n            (HTTP) Tell the --remote-name  option to use the  server-specified\n            Content-Disposition filename  instead  of  extracting  a  filename\n            from the URL.  If the  server-provided filename  contains a  path,\n            that is stripped off before the filename is used.\n\n            The file is saved  in the current  directory, or in the  directory\n            specified with --output-dir.\n\n            If the  server specifies  a filename  and a  file  with that  name\n            already  exists   in  the   destination  directory,   it  is   not\n            overwritten and an  error occurs -  unless you  allow it by  using\n            the --clobber option. If  the server does  not specify a  filename\n            then this option has no effect.\n\n            There is no attempt  to decode %-sequences  (yet) in the  provided\n            filename, so this  option may provide  you with rather  unexpected\n            filenames.\n\n            This feature uses the name from the "filename" field, it  does not\n            yet  support  the  "filename*"  field  (filenames  with   explicit\n            character sets).\n\n            WARNING: Exercise  judicious use  of  this option,  especially  on\n            Windows. A rogue server could send you the name of a DLL  or other\n            file that could be loaded  automatically by Windows or some  third\n            party software.\n\n            Providing  --remote-header-name  multiple   times  has  no   extra\n            effect. Disable it again with --no-remote-header-name.\n\n            Example:\n             curl -OJ https://example.com/file\n\n            See also --remote-name.\n\n    --remote-name-all\n            Change the default action for all  given URLs to be dealt with  as\n            if --remote-name were used  for each one.  If you want to  disable\n            that for a  specific URL  after --remote-name-all  has been  used,\n            you must use "-o -" or --no-remote-name.\n\n            Providing --remote-name-all multiple  times has  no extra  effect.\n            Disable it again with --no-remote-name-all.\n\n            Example:\n             curl --remote-name-all ftp://example.com/file1 ftp://example.com/file2\n\n            See also --remote-name.\n\n    -O, --remote-name\n            Write output to a  local file named like  the remote file we  get.\n            (Only the file part  of the remote file is  used, the path is  cut\n            off.)\n\n            The file is saved  in the current  working directory. If you  want\n            the file saved in a different directory, make sure you  change the\n            current working directory  before invoking curl  with this  option\n            or use --output-dir.\n\n            The remote filename to use for saving is extracted from  the given\n            URL, nothing else, and if it already exists it is  overwritten. If\n            you want the  server to be  able to choose  the filename refer  to\n            --remote-header-name  which  can  be  used  in  addition  to  this\n            option. If the  server chooses  a filename and  that name  already\n            exists it is not overwritten.\n\n            There is no URL  decoding done on the filename.  If it has %20  or\n            other URL  encoded  parts  of  the  name, they  end  up  as-is  as\n            filename.\n\n            You may use this  option as many times as  the number of URLs  you\n            have.\n\n            --remote-name can be used several times in a command line\n\n            Example:\n             curl -O https://example.com/filename\n\n            See      also       --remote-name-all,      --output-dir       and\n            --remote-header-name.\n\n    -R, --remote-time\n            Makes curl attempt to figure out the timestamp of the  remote file\n            that is  getting downloaded,  and if  that is  available make  the\n            local file get that same timestamp.\n\n            Providing  --remote-time  multiple  times  has  no  extra  effect.\n            Disable it again with --no-remote-time.\n\n            Example:\n             curl --remote-time -o foo https://example.com\n\n            See also --remote-name and --time-cond.\n\n    --remove-on-error\n            Remove output file if  an error occurs.  If curl returns an  error\n            when told to save output in a local file. This prevents  curl from\n            leaving a partial file in the case of an error during transfer.\n\n            If the output is not a regular file, this option has no effect.\n\n            Providing --remove-on-error multiple  times has  no extra  effect.\n            Disable it again with --no-remove-on-error.\n\n            Example:\n             curl --remove-on-error -o output https://example.com\n\n            See also --fail. Added in 7.83.0.\n\n    --request-target <path>\n            (HTTP) Use an alternative target (path) instead of using the  path\n            as provided in the URL. Particularly useful when wanting to  issue\n            HTTP requests without leading  slash or other  data that does  not\n            follow the regular URL pattern, like "OPTIONS *".\n\n            curl passes on  the verbatim string  you give  it its the  request\n            without any  filter  or other  safe  guards. That  includes  white\n            space and control characters.\n\n            If --request-target is provided several times, the last set  value\n            is used.\n\n            Example:\n             curl --request-target "*" -X OPTIONS https://example.com\n\n            See also --request. Added in 7.55.0.\n\n    -X, --request <method>\n            Change the method to use when starting the transfer.\n\n            curl passes on  the verbatim string  you give  it its the  request\n            without any  filter  or other  safe  guards. That  includes  white\n            space and control characters.\n\n            HTTP\n\n                Specifies a custom  request method to  use when  communicating\n                with the HTTP  server. The  specified request  method is  used\n                instead of the method otherwise used (which defaults to  GET).\n                Read the HTTP 1.1 specification for details and  explanations.\n                Common additional HTTP requests include PUT and DELETE,  while\n                related technologies like WebDAV  offers PROPFIND, COPY,  MOVE\n                and more.\n\n                Normally you do not need this option. All sorts of  GET, HEAD,\n                POST and PUT  requests are rather  invoked by using  dedicated\n                command line options.\n\n                This option  only changes  the actual  word used  in the  HTTP\n                request, it does not alter  the way curl behaves. For  example\n                if you want to make a proper HEAD request, using -X  HEAD does\n                not suffice. You need to use the --head option.\n\n                The method  string you  set  with --request  is used  for  all\n                requests, which if  you for example  use --location may  cause\n                unintended side-effects  when  curl does  not  change  request\n                method  according  to  the  HTTP  30x  response  codes  -  and\n                similar.\n\n            FTP\n\n                Specifies a custom  FTP command  to use instead  of LIST  when\n                doing file lists with FTP.\n\n            POP3\n\n                Specifies a  custom POP3  command to  use instead  of LIST  or\n                RETR.\n\n            IMAP\n\n                Specifies a custom IMAP command to use instead of LIST.\n\n            SMTP\n\n                Specifies a  custom SMTP  command to  use instead  of HELP  or\n                VRFY.\n\n            If --request  is provided  several times,  the last  set value  is\n            used.\n\n            Examples:\n             curl -X "DELETE" https://example.com\n             curl -X NLST ftp://example.com/\n\n            See also --request-target.\n\n    --resolve <[+]host:port:addr[,addr]...>\n            Provide a custom address for a specific host and port  pair. Using\n            this, you can make  the curl requests(s)  use a specified  address\n            and prevent the  otherwise normally resolved  address to be  used.\n            Consider it  a  sort of  /etc/hosts  alternative provided  on  the\n            command line. The port  number should be  the number used for  the\n            specific protocol the host is used for. It means you  need several\n            entries if  you want  to provide  address for  the  same host  but\n            different ports.\n\n            By specifying "*" as  host you can tell  curl to resolve any  host\n            and specific  port  pair to  the  specified address.  Wildcard  is\n            resolved last so any  --resolve with a  specific host and port  is\n            used first.\n\n            The provided address set by this option is used even if  --ipv4 or\n            --ipv6 is set to make curl use another IP version.\n\n            By prefixing the host with a  \'+\' you can make the entry time  out\n            after curl\'s  default  timeout (1  minute).  Note that  this  only\n            makes sense  for long  running parallel  transfers with  a lot  of\n            files. In  such  cases,  if this  option  is used  curl  tries  to\n            resolve the  host  as  it  normally would  once  the  timeout  has\n            expired.\n\n            Support for providing the IP  address within [brackets] was  added\n            in 7.57.0.\n\n            Support for providing  multiple IP addresses  per entry was  added\n            in 7.59.0.\n\n            Support for resolving with wildcard was added in 7.64.0.\n\n            Support for the \'+\' prefix was added in 7.75.0.\n\n            --resolve can be used several times in a command line\n\n            Example:\n             curl --resolve example.com:443:127.0.0.1 https://example.com\n\n            See also --connect-to and --alt-svc.\n\n    --retry-all-errors\n            Retry on any error. This option is used together with --retry.\n\n            This option is  the "sledgehammer"  of retrying. Do  not use  this\n            option by  default (for  example  in your  curlrc), there  may  be\n            unintended consequences  such as  sending or  receiving  duplicate\n            data. Do not  use with redirected  input or  output. You might  be\n            better off  handling  your  unique problems  in  a  shell  script.\n            Please read the example below.\n\n            WARNING: For server  compatibility curl attempts  to retry  failed\n            flaky transfers as  close as  possible to how  they were  started,\n            but this  is not  possible with  redirected input  or output.  For\n            example, before  retrying it  removes output  data from  a  failed\n            partial transfer that was written to an output file. However  this\n            is not true of data  redirected to a |  pipe or > file, which  are\n            not reset. We strongly suggest  you do not parse or record  output\n            via redirect  in  combination  with this  option,  since  you  may\n            receive duplicate data.\n\n            By default curl does not  return error for transfers with an  HTTP\n            response code that indicates  an HTTP error,  if the transfer  was\n            successful. For example,  if a  server replies 404  Not Found  and\n            the reply  is  fully received  then that  is  not an  error.  When\n            --retry is  used then  curl retries  on some  HTTP response  codes\n            that indicate transient  HTTP errors,  but that  does not  include\n            most 4xx response codes such as  404. If you want to retry on  all\n            response codes  that  indicate  HTTP errors  (4xx  and  5xx)  then\n            combine with --fail.\n\n            Providing --retry-all-errors multiple times  has no extra  effect.\n            Disable it again with --no-retry-all-errors.\n\n            Example:\n             curl --retry 5 --retry-all-errors https://example.com\n\n            See also --retry. Added in 7.71.0.\n\n    --retry-connrefused\n            In addition to  the other conditions,  consider ECONNREFUSED as  a\n            transient error  too for  --retry. This  option is  used  together\n            with --retry.\n\n            Providing --retry-connrefused multiple times has no extra  effect.\n            Disable it again with --no-retry-connrefused.\n\n            Example:\n             curl --retry-connrefused --retry 7 https://example.com\n\n            See also --retry and --retry-all-errors. Added in 7.52.0.\n\n    --retry-delay <seconds>\n            Make curl  sleep this  amount of  time before  each  retry when  a\n            transfer has  failed  with  a  transient  error  (it  changes  the\n            default backoff time  algorithm between retries).  This option  is\n            only interesting if --retry  is also used.  Setting this delay  to\n            zero makes curl use the default backoff time.\n\n            If --retry-delay is provided several times, the last set value  is\n            used.\n\n            Example:\n             curl --retry-delay 5 --retry 7 https://example.com\n\n            See also --retry.\n\n    --retry-max-time <seconds>\n            The retry  timer  is  reset before  the  first  transfer  attempt.\n            Retries are done as usual (see  --retry) as long as the timer  has\n            not reached this  given limit. Notice  that if  the timer has  not\n            reached the limit, the  request is made  and while performing,  it\n            may take longer  than this given  time period.  To limit a  single\n            request\'s maximum time,  use --max-time. Set  this option to  zero\n            to not timeout retries.\n\n            If --retry-max-time is provided several times, the last set  value\n            is used.\n\n            Example:\n             curl --retry-max-time 30 --retry 10 https://example.com\n\n            See also --retry.\n\n    --retry <num>\n            If a  transient error is  returned when  curl tries  to perform  a\n            transfer, it  retries  this  number of  times  before  giving  up.\n            Setting the number  to 0 makes  curl do no  retries (which is  the\n            default). Transient  error means  either: a  timeout, an  FTP  4xx\n            response code or an HTTP 408,  429, 500, 502, 503 or 504  response\n            code.\n\n            When curl is about to retry a transfer, it first waits  one second\n            and then for all forthcoming  retries it doubles the waiting  time\n            until it reaches 10 minutes  which then remains delay between  the\n            rest of  the  retries. By  using  --retry-delay you  disable  this\n            exponential backoff algorithm. See also --retry-max-time to  limit\n            the total time allowed for retries.\n\n            curl complies with  the Retry-After:  response header  if one  was\n            present to know when to issue the next retry (added in 7.66.0).\n\n            If --retry is provided several times, the last set value is used.\n\n            Example:\n             curl --retry 7 https://example.com\n\n            See also --retry-max-time.\n\n    --sasl-authzid <identity>\n            Use this  authorization  identity  (authzid),  during  SASL  PLAIN\n            authentication,  in  addition   to  the  authentication   identity\n            (authcid) as specified by --user.\n\n            If the option  is not  specified, the server  derives the  authzid\n            from the authcid, but  if specified, and  depending on the  server\n            implementation, it may  be used  to access  another user\'s  inbox,\n            that the user has been granted access to, or a shared  mailbox for\n            example.\n\n            If --sasl-authzid is  provided several times,  the last set  value\n            is used.\n\n            Example:\n             curl --sasl-authzid zid imap://example.com/\n\n            See also --login-options. Added in 7.66.0.\n\n    --sasl-ir\n            Enable initial response in SASL authentication.\n\n            Providing --sasl-ir multiple  times has no  extra effect.  Disable\n            it again with --no-sasl-ir.\n\n            Example:\n             curl --sasl-ir imap://example.com/\n\n            See also --sasl-authzid.\n\n    --service-name <name>\n            Set the service name for SPNEGO.\n\n            If --service-name is  provided several times,  the last set  value\n            is used.\n\n            Example:\n             curl --service-name sockd/server https://example.com\n\n            See also --negotiate and --proxy-service-name.\n\n    -S, --show-error\n            When used with --silent,  it makes curl  show an error message  if\n            it fails.\n\n            This option is global and does  not need to be specified for  each\n            use of --next.\n\n            Providing  --show-error  multiple  times  has  no  extra   effect.\n            Disable it again with --no-show-error.\n\n            Example:\n             curl --show-error --silent https://example.com\n\n            See also --no-progress-meter.\n\n    -s, --silent\n            Silent  or quiet  mode.  Do  not  show  progress  meter  or  error\n            messages. Makes Curl mute. It still outputs the data you  ask for,\n            potentially even to the terminal/stdout unless you redirect it.\n\n            Use --show-error in  addition to this  option to disable  progress\n            meter but still show error messages.\n\n            Providing --silent multiple times has no extra effect. Disable  it\n            again with --no-silent.\n\n            Example:\n             curl -s https://example.com\n\n            See also --verbose, --stderr and --no-progress-meter.\n\n    --socks4 <host[:port]>\n            Use  the specified  SOCKS4  proxy.  If  the  port  number  is  not\n            specified, it  is assumed  at port  1080. Using  this socket  type\n            make curl resolve the hostname  and passing the address on to  the\n            proxy.\n\n            To specify proxy on a unix domain socket, use localhost  for host,\n            e.g. "socks4://localhost/path/to/socket.sock"\n\n            This option overrides  any previous  use of --proxy,  as they  are\n            mutually exclusive.\n\n            This option is superfluous  since you can  specify a socks4  proxy\n            with --proxy using a socks4:// protocol prefix.\n\n            --preproxy can be used to specify  a SOCKS proxy at the same  time\n            proxy is used with an HTTP/HTTPS proxy (added in 7.52.0).  In such\n            a case, curl first connects  to the SOCKS proxy and then  connects\n            (through SOCKS) to the HTTP or HTTPS proxy.\n\n            If --socks4  is provided  several  times, the  last set  value  is\n            used.\n\n            Example:\n             curl --socks4 hostname:4096 https://example.com\n\n            See also --socks4a, --socks5 and --socks5-hostname.\n\n    --socks4a <host[:port]>\n            Use the  specified  SOCKS4a  proxy.  If the  port  number  is  not\n            specified, it  is assumed at  port 1080.  This asks  the proxy  to\n            resolve the hostname.\n\n            To specify proxy on a unix domain socket, use localhost  for host,\n            e.g. "socks4a://localhost/path/to/socket.sock"\n\n            This option overrides  any previous  use of --proxy,  as they  are\n            mutually exclusive.\n\n            This option is superfluous since  you can specify a socks4a  proxy\n            with --proxy using a socks4a:// protocol prefix.\n\n            --preproxy can be used to specify  a SOCKS proxy at the same  time\n            --proxy is used  with an  HTTP/HTTPS proxy (added  in 7.52.0).  In\n            such a  case, curl  first connects  to the  SOCKS  proxy and  then\n            connects (through SOCKS) to the HTTP or HTTPS proxy.\n\n            If --socks4a  is provided  several times,  the last  set value  is\n            used.\n\n            Example:\n             curl --socks4a hostname:4096 https://example.com\n\n            See also --socks4, --socks5 and --socks5-hostname.\n\n    --socks5-basic\n            Use username/password authentication when  connecting to a  SOCKS5\n            proxy.  The   username/password  authentication   is  enabled   by\n            default. Use --socks5-gssapi  to force  GSS-API authentication  to\n            SOCKS5 proxies.\n\n            Providing --socks5-basic multiple times has no extra effect.\n\n            Example:\n             curl --socks5-basic --socks5 hostname:4096 https://example.com\n\n            See also --socks5. Added in 7.55.0.\n\n    --socks5-gssapi-nec\n            As  part  of  the  GSS-API   negotiation  a  protection  mode   is\n            negotiated.  RFC  1961  says  in  section  4.3/4.4  it  should  be\n            protected, but  the NEC  reference  implementation does  not.  The\n            option --socks5-gssapi-nec allows the unprotected exchange of  the\n            protection mode negotiation.\n\n            Providing --socks5-gssapi-nec multiple times has no extra  effect.\n            Disable it again with --no-socks5-gssapi-nec.\n\n            Example:\n             curl --socks5-gssapi-nec --socks5 hostname:4096 https://example.com\n\n            See also --socks5.\n\n    --socks5-gssapi-service <name>\n            Set  the   service   name  for   a   socks  server.   Default   is\n            rcmd/server-fqdn.\n\n            If --socks5-gssapi-service  is provided  several times,  the  last\n            set value is used.\n\n            Example:\n             curl --socks5-gssapi-service sockd --socks5 hostname:4096 https://example.com\n\n            See also --socks5.\n\n    --socks5-gssapi\n            Use GSS-API authentication when connecting to a SOCKS5 proxy.  The\n            GSS-API authentication is enabled by default (if curl is  compiled\n            with   GSS-API    support).    Use   --socks5-basic    to    force\n            username/password authentication to SOCKS5 proxies.\n\n            Providing --socks5-gssapi  multiple  times has  no  extra  effect.\n            Disable it again with --no-socks5-gssapi.\n\n            Example:\n             curl --socks5-gssapi --socks5 hostname:4096 https://example.com\n\n            See also --socks5. Added in 7.55.0.\n\n    --socks5-hostname <host[:port]>\n            Use the  specified SOCKS5  proxy (and  let the  proxy resolve  the\n            hostname). If the port number  is not specified, it is assumed  at\n            port 1080.\n\n            To specify proxy on a unix domain socket, use localhost  for host,\n            e.g. "socks5h://localhost/path/to/socket.sock"\n\n            This option overrides  any previous  use of --proxy,  as they  are\n            mutually exclusive.\n\n            This  option  is  superfluous  since  you  can  specify  a  socks5\n            hostname proxy with --proxy using a socks5h:// protocol prefix.\n\n            --preproxy can be used to specify  a SOCKS proxy at the same  time\n            --proxy is used  with an  HTTP/HTTPS proxy (added  in 7.52.0).  In\n            such a  case, curl  first connects  to the  SOCKS  proxy and  then\n            connects (through SOCKS) to the HTTP or HTTPS proxy.\n\n            If --socks5-hostname  is  provided  several times,  the  last  set\n            value is used.\n\n            Example:\n             curl --socks5-hostname proxy.example:7000 https://example.com\n\n            See also --socks5 and --socks4a.\n\n    --socks5 <host[:port]>\n            Use  the  specified  SOCKS5  proxy  -  but  resolve  the  hostname\n            locally. If the  port number is  not specified,  it is assumed  at\n            port 1080.\n\n            To specify proxy on a unix domain socket, use localhost  for host,\n            e.g. "socks5://localhost/path/to/socket.sock"\n\n            This option overrides  any previous  use of --proxy,  as they  are\n            mutually exclusive.\n\n            This option is superfluous  since you can  specify a socks5  proxy\n            with --proxy using a socks5:// protocol prefix.\n\n            --preproxy can be used to specify  a SOCKS proxy at the same  time\n            --proxy is used  with an  HTTP/HTTPS proxy (added  in 7.52.0).  In\n            such a  case, curl  first connects  to the  SOCKS  proxy and  then\n            connects (through SOCKS) to the HTTP or HTTPS proxy.\n\n            This option (as well  as --socks4) does  not work with IPV6,  FTPS\n            or LDAP.\n\n            If --socks5  is provided  several  times, the  last set  value  is\n            used.\n\n            Example:\n             curl --socks5 proxy.example:7000 https://example.com\n\n            See also --socks5-hostname and --socks4a.\n\n    -Y, --speed-limit <speed>\n            If a transfer is slower than this set speed (in bytes  per second)\n            for a given number  of seconds, it  gets aborted. The time  period\n            is set with --speed-time and is 30 seconds by default.\n\n            If --speed-limit is provided several times, the last set value  is\n            used.\n\n            Example:\n             curl --speed-limit 300 --speed-time 10 https://example.com\n\n            See also --speed-time, --limit-rate and --max-time.\n\n    -y, --speed-time <seconds>\n            If a  transfer  runs  slower than  speed-limit  bytes  per  second\n            during  a  speed-time   period,  the  transfer   is  aborted.   If\n            speed-time is used, the default  speed-limit is 1 unless set  with\n            --speed-limit.\n\n            This option controls transfers (in  both directions) but does  not\n            affect slow connects etc.  If this is a  concern for you, try  the\n            --connect-timeout option.\n\n            If --speed-time is provided several  times, the last set value  is\n            used.\n\n            Example:\n             curl --speed-limit 300 --speed-time 10 https://example.com\n\n            See also --speed-limit and --limit-rate.\n\n    --ssl-allow-beast\n            (TLS) Do not work  around a security flaw  in the SSL3 and  TLS1.0\n            protocols known  as BEAST. If  this option  is not  used, the  SSL\n            layer  may  use  workarounds   known  to  cause   interoperability\n            problems with some older SSL implementations.\n\n            WARNING: this option loosens the  SSL security, and by using  this\n            flag you ask for exactly that.\n\n            Providing --ssl-allow-beast multiple  times has  no extra  effect.\n            Disable it again with --no-ssl-allow-beast.\n\n            Example:\n             curl --ssl-allow-beast https://example.com\n\n            See also --proxy-ssl-allow-beast and --insecure.\n\n    --ssl-auto-client-cert\n            (TLS)  (Schannel)   Automatically   locate  and   use   a   client\n            certificate for  authentication,  when requested  by  the  server.\n            Since the server can request any certificate that supports  client\n            authentication in the OS certificate  store it could be a  privacy\n            violation and unexpected.\n\n            Providing  --ssl-auto-client-cert  multiple  times  has  no  extra\n            effect. Disable it again with --no-ssl-auto-client-cert.\n\n            Example:\n             curl --ssl-auto-client-cert https://example.com\n\n            See also --proxy-ssl-auto-client-cert. Added in 7.77.0.\n\n    --ssl-no-revoke\n            (TLS) (Schannel) Disable  certificate revocation checks.  WARNING:\n            this option loosens the SSL  security, and by using this flag  you\n            ask for exactly that.\n\n            Providing --ssl-no-revoke  multiple  times has  no  extra  effect.\n            Disable it again with --no-ssl-no-revoke.\n\n            Example:\n             curl --ssl-no-revoke https://example.com\n\n            See also --crlfile.\n\n    --ssl-reqd\n            (FTP IMAP  POP3 SMTP  LDAP) Require  SSL/TLS for  the  connection.\n            Terminates the connection  if the transfer  cannot be upgraded  to\n            use SSL/TLS.\n\n            This option  is handled in  LDAP (added  in 7.81.0).  It is  fully\n            supported by  the OpenLDAP  backend and  rejected by  the  generic\n            ldap backend if explicit TLS is required.\n\n            This option is unnecessary if you use a URL scheme that  in itself\n            implies immediate and implicit use  of TLS, like for FTPS,  IMAPS,\n            POP3S, SMTPS and LDAPS.  Such a transfer  always fails if the  TLS\n            handshake does not work.\n\n            This option was formerly known as --ftp-ssl-reqd.\n\n            Providing --ssl-reqd multiple times  has no extra effect.  Disable\n            it again with --no-ssl-reqd.\n\n            Example:\n             curl --ssl-reqd ftp://example.com\n\n            See also --ssl and --insecure.\n\n    --ssl-revoke-best-effort\n            (TLS) (Schannel) Ignore  certificate revocation  checks when  they\n            failed  due  to  missing/offline   distribution  points  for   the\n            revocation check lists.\n\n            Providing --ssl-revoke-best-effort  multiple  times has  no  extra\n            effect. Disable it again with --no-ssl-revoke-best-effort.\n\n            Example:\n             curl --ssl-revoke-best-effort https://example.com\n\n            See also --crlfile and --insecure. Added in 7.70.0.\n\n    --ssl\n            (FTP IMAP POP3 SMTP LDAP) Warning: this is considered an  insecure\n            option.  Consider  using  --ssl-reqd  instead  to  be  sure   curl\n            upgrades to a secure connection.\n\n            Try to use  SSL/TLS for  the connection. Reverts  to a  non-secure\n            connection if  the  server  does not  support  SSL/TLS.  See  also\n            --ftp-ssl-control  and   --ssl-reqd   for  different   levels   of\n            encryption required.\n\n            This option  is handled in  LDAP (added  in 7.81.0).  It is  fully\n            supported by the OpenLDAP backend and ignored by the generic  ldap\n            backend.\n\n            Please  note that  a  server  may  close  the  connection  if  the\n            negotiation does not succeed.\n\n            This option was formerly known as --ftp-ssl. That option name  can\n            still be used but might be removed in a future version.\n\n            Providing --ssl multiple  times has  no extra  effect. Disable  it\n            again with --no-ssl.\n\n            Example:\n             curl --ssl pop3://example.com/\n\n            See also --ssl-reqd, --insecure and --ciphers.\n\n    -2, --sslv2\n            (SSL) This option previously asked  curl to use SSLv2, but is  now\n            ignored (added  in 7.77.0).  SSLv2 is  widely considered  insecure\n            (see RFC 6176).\n\n            Providing --sslv2 multiple times has no extra effect.\n\n            Example:\n             curl --sslv2 https://example.com\n\n            See  also  --http1.1  and  --http2.  --sslv2  requires  that   the\n            underlying libcurl  was  built  to support  TLS.  This  option  is\n            mutually exclusive  to  --sslv3  and  --tlsv1  and  --tlsv1.1  and\n            --tlsv1.2.\n\n    -3, --sslv3\n            (SSL) This option previously asked  curl to use SSLv3, but is  now\n            ignored (added  in 7.77.0).  SSLv3 is  widely considered  insecure\n            (see RFC 7568).\n\n            Providing --sslv3 multiple times has no extra effect.\n\n            Example:\n             curl --sslv3 https://example.com\n\n            See  also  --http1.1  and  --http2.  --sslv3  requires  that   the\n            underlying libcurl  was  built  to support  TLS.  This  option  is\n            mutually exclusive  to  --sslv2  and  --tlsv1  and  --tlsv1.1  and\n            --tlsv1.2.\n\n    --stderr <file>\n            Redirect all writes to  stderr to the  specified file instead.  If\n            the filename is a plain \'-\', it is instead written to stdout.\n\n            This option is global and does  not need to be specified for  each\n            use of --next.\n\n            If --stderr  is provided  several  times, the  last set  value  is\n            used.\n\n            Example:\n             curl --stderr output.txt https://example.com\n\n            See also --verbose and --silent.\n\n    --styled-output\n            Enable automatic  use  of  bold  font  styles  when  writing  HTTP\n            headers to  the terminal.  Use --no-styled-output  to switch  them\n            off.\n\n            Styled output requires a terminal  that supports bold fonts.  This\n            feature is not  present on curl  for Windows due  to lack of  this\n            capability.\n\n            This option is global and does  not need to be specified for  each\n            use of --next.\n\n            Providing --styled-output  multiple  times has  no  extra  effect.\n            Disable it again with --no-styled-output.\n\n            Example:\n             curl --styled-output -I https://example.com\n\n            See also --head and --verbose. Added in 7.61.0.\n\n    --suppress-connect-headers\n            When --proxytunnel is used  and a CONNECT  request is made do  not\n            output proxy CONNECT response headers. This option is meant to  be\n            used with  --dump-header  or  --include which  are  used  to  show\n            protocol headers in the output. It has no effect on  debug options\n            such as --verbose or --trace, or any statistics.\n\n            Providing --suppress-connect-headers multiple  times has no  extra\n            effect. Disable it again with --no-suppress-connect-headers.\n\n            Example:\n             curl --suppress-connect-headers --include -x proxy https://example.com\n\n            See also  --dump-header,  --include and  --proxytunnel.  Added  in\n            7.54.0.\n\n    --tcp-fastopen\n            Enable use of  TCP Fast Open (RFC  7413). TCP Fast  Open is a  TCP\n            extension  that  allows  data  to   get  sent  earlier  over   the\n            connection (before  the final  handshake ACK)  if the  client  and\n            server have been connected previously.\n\n            Providing --tcp-fastopen  multiple  times  has  no  extra  effect.\n            Disable it again with --no-tcp-fastopen.\n\n            Example:\n             curl --tcp-fastopen https://example.com\n\n            See also --false-start.\n\n    --tcp-nodelay\n            Turn on the  TCP_NODELAY option. See  the curl_easy_setopt(3)  man\n            page for details about this option.\n\n            curl sets  this  option by  default  and you  need  to  explicitly\n            switch it off if you do not want it on (added in 7.50.2).\n\n            Providing  --tcp-nodelay  multiple  times  has  no  extra  effect.\n            Disable it again with --no-tcp-nodelay.\n\n            Example:\n             curl --tcp-nodelay https://example.com\n\n            See also --no-buffer.\n\n    -t, --telnet-option <opt=val>\n            Pass options to the telnet protocol. Supported options are:\n\n            `TTYPE=<term>`\n\n                Sets the terminal type.\n\n            `XDISPLOC=<X display>`\n\n                Sets the X display location.\n\n            `NEW_ENV=<var,val>`\n\n                Sets an environment variable.\n\n            --telnet-option can be used several times in a command line\n\n            Example:\n             curl -t TTYPE=vt100 telnet://example.com/\n\n            See also --config.\n\n    --tftp-blksize <value>\n            (TFTP) Set the TFTP BLKSIZE  option (must be 512 or larger).  This\n            is the block size  that curl tries  to use when transferring  data\n            to or from a TFTP server. By default 512 bytes are used.\n\n            If --tftp-blksize is  provided several times,  the last set  value\n            is used.\n\n            Example:\n             curl --tftp-blksize 1024 tftp://example.com/file\n\n            See also --tftp-no-options.\n\n    --tftp-no-options\n            (TFTP) Do  not  to  send  TFTP  options  requests.  This  improves\n            interop with  some  legacy  servers that  do  not  acknowledge  or\n            properly  implement  TFTP  options.  When  this  option  is   used\n            --tftp-blksize is ignored.\n\n            Providing --tftp-no-options multiple  times has  no extra  effect.\n            Disable it again with --no-tftp-no-options.\n\n            Example:\n             curl --tftp-no-options tftp://192.168.0.1/\n\n            See also --tftp-blksize.\n\n    -z, --time-cond <time>\n            (HTTP FTP) Request a  file that has  been modified later than  the\n            given time and  date, or one  that has  been modified before  that\n            time. The date expression can be  all sorts of date strings or  if\n            it does not match any internal  ones, it is treated as a  filename\n            and curl  tries to  get the  modification date  (mtime) from  that\n            file  instead.  See  the   curl_getdate(3)  man  pages  for   date\n            expression details.\n\n            Start the date expression with a  dash (-) to make it request  for\n            a document that is  older than the  given date/time, default is  a\n            document that is newer than the specified date/time.\n\n            If provided  a non-existing  file, curl  outputs a  warning  about\n            that  fact  and  proceeds  to  do  the  transfer  without  a  time\n            condition.\n\n            If --time-cond is provided  several times, the  last set value  is\n            used.\n\n            Examples:\n             curl -z "Wed 01 Sep 2021 12:18:00" https://example.com\n             curl -z "-Wed 01 Sep 2021 12:18:00" https://example.com\n             curl -z file https://example.com\n\n            See also --etag-compare and --remote-time.\n\n    --tls-max <VERSION>\n            (TLS) VERSION defines maximum  supported TLS version. The  minimum\n            acceptable  version  is  set  by  tlsv1.0,  tlsv1.1,  tlsv1.2   or\n            tlsv1.3.\n\n            If the connection is done without TLS, this option has  no effect.\n            This includes QUIC-using (HTTP/3) transfers.\n\n            default\n\n                Use up to recommended TLS version.\n\n            1.0\n\n                Use up to TLSv1.0.\n\n            1.1\n\n                Use up to TLSv1.1.\n\n            1.2\n\n                Use up to TLSv1.2.\n\n            1.3\n\n                Use up to TLSv1.3.\n\n            If --tls-max  is provided  several times,  the last  set value  is\n            used.\n\n            Examples:\n             curl --tls-max 1.2 https://example.com\n             curl --tls-max 1.3 --tlsv1.2 https://example.com\n\n            See also --tlsv1.0, --tlsv1.1, --tlsv1.2 and --tlsv1.3.  --tls-max\n            requires that the  underlying libcurl  was built  to support  TLS.\n            Added in 7.54.0.\n\n    --tls13-ciphers <list>\n            (TLS) Specifies which cipher  suites to use  in the connection  if\n            it negotiates TLS  1.3. The  list of ciphers  suites must  specify\n            valid ciphers. Read  up on TLS  1.3 cipher  suite details on  this\n            URL:\n\n            https://curl.se/docs/ssl-ciphers.html\n\n            This option  is currently  used only  when curl  is  built to  use\n            OpenSSL 1.1.1 or later, or Schannel. If you are using  a different\n            SSL backend you  can try setting  TLS 1.3  cipher suites by  using\n            the --ciphers option.\n\n            If --tls13-ciphers is provided several  times, the last set  value\n            is used.\n\n            Example:\n             curl --tls13-ciphers TLS_AES_128_GCM_SHA256 https://example.com\n\n            See also --ciphers, --curves  and --proxy-tls13-ciphers. Added  in\n            7.61.0.\n\n    --tlsauthtype <type>\n            (TLS) Set TLS authentication  type. Currently, the only  supported\n            option  is  "SRP",  for  TLS-SRP  (RFC  5054).  If  --tlsuser  and\n            --tlspassword are specified  but --tlsauthtype is  not, then  this\n            option  defaults  to  "SRP".  This   option  works  only  if   the\n            underlying libcurl is built  with TLS-SRP support, which  requires\n            OpenSSL or GnuTLS with TLS-SRP support.\n\n            If --tlsauthtype is provided several times, the last set value  is\n            used.\n\n            Example:\n             curl --tlsauthtype SRP https://example.com\n\n            See also --tlsuser.\n\n    --tlspassword <string>\n            (TLS) Set  password for  use with  the TLS  authentication  method\n            specified with  --tlsauthtype.  Requires that  --tlsuser  also  be\n            set.\n\n            This option does not work with TLS 1.3.\n\n            If --tlspassword is provided several times, the last set value  is\n            used.\n\n            Example:\n             curl --tlspassword pwd --tlsuser user https://example.com\n\n            See also --tlsuser.\n\n    --tlsuser <name>\n            (TLS) Set  username for  use with  the TLS  authentication  method\n            specified with --tlsauthtype. Requires that --tlspassword also  is\n            set.\n\n            This option does not work with TLS 1.3.\n\n            If --tlsuser  is provided  several times,  the last  set value  is\n            used.\n\n            Example:\n             curl --tlspassword pwd --tlsuser user https://example.com\n\n            See also --tlspassword.\n\n    --tlsv1.0\n            (TLS) Forces curl to use TLS version 1.0 or later  when connecting\n            to a remote TLS server.\n\n            In old  versions  of curl  this  option was  documented  to  allow\n            _only_ TLS 1.0.  That behavior was  inconsistent depending on  the\n            TLS library.  Use  --tls-max if  you want  to  set a  maximum  TLS\n            version.\n\n            Providing --tlsv1.0 multiple times has no extra effect.\n\n            Example:\n             curl --tlsv1.0 https://example.com\n\n            See also --tlsv1.3.\n\n    --tlsv1.1\n            (TLS) Forces curl to use TLS version 1.1 or later  when connecting\n            to a remote TLS server.\n\n            In old  versions  of curl  this  option was  documented  to  allow\n            _only_ TLS 1.1.  That behavior was  inconsistent depending on  the\n            TLS library.  Use  --tls-max if  you want  to  set a  maximum  TLS\n            version.\n\n            Providing --tlsv1.1 multiple times has no extra effect.\n\n            Example:\n             curl --tlsv1.1 https://example.com\n\n            See also --tlsv1.3 and --tls-max.\n\n    --tlsv1.2\n            (TLS) Forces curl to use TLS version 1.2 or later  when connecting\n            to a remote TLS server.\n\n            In old  versions  of curl  this  option was  documented  to  allow\n            _only_ TLS 1.2.  That behavior was  inconsistent depending on  the\n            TLS library.  Use  --tls-max if  you want  to  set a  maximum  TLS\n            version.\n\n            Providing --tlsv1.2 multiple times has no extra effect.\n\n            Example:\n             curl --tlsv1.2 https://example.com\n\n            See also --tlsv1.3 and --tls-max.\n\n    --tlsv1.3\n            (TLS) Forces curl to use TLS version 1.3 or later  when connecting\n            to a remote TLS server.\n\n            If the connection is done without TLS, this option has  no effect.\n            This includes QUIC-using (HTTP/3) transfers.\n\n            Note that TLS 1.3 is not supported by all TLS backends.\n\n            Providing --tlsv1.3 multiple times has no extra effect.\n\n            Example:\n             curl --tlsv1.3 https://example.com\n\n            See also --tlsv1.2 and --tls-max. Added in 7.52.0.\n\n    -1, --tlsv1\n            (TLS) Use at least TLS version 1.x when negotiating with  a remote\n            TLS server. That means TLS version 1.0 or higher\n\n            Providing --tlsv1 multiple times has no extra effect.\n\n            Example:\n             curl --tlsv1 https://example.com\n\n            See  also  --http1.1  and  --http2.  --tlsv1  requires  that   the\n            underlying libcurl  was  built  to support  TLS.  This  option  is\n            mutually exclusive to --tlsv1.1 and --tlsv1.2 and --tlsv1.3.\n\n    --tr-encoding\n            (HTTP) Request a compressed  Transfer-Encoding response using  one\n            of the algorithms  curl supports,  and uncompress  the data  while\n            receiving it.\n\n            Providing  --tr-encoding  multiple  times  has  no  extra  effect.\n            Disable it again with --no-tr-encoding.\n\n            Example:\n             curl --tr-encoding https://example.com\n\n            See also --compressed.\n\n    --trace-ascii <file>\n            Save  a full  trace  dump  of  all  incoming  and  outgoing  data,\n            including descriptive information, in  the given output file.  Use\n            "-" as filename to have the output sent to stdout.\n\n            This is similar to --trace, but  leaves out the hex part and  only\n            shows the ASCII  part of the  dump. It  makes smaller output  that\n            might be easier to read for untrained humans.\n\n            Note that verbose  output of curl  activities and network  traffic\n            might contain sensitive data, including usernames, credentials  or\n            secret data content. Be  aware and be  careful when sharing  trace\n            logs with others.\n\n            This option is global and does  not need to be specified for  each\n            use of --next.\n\n            If --trace-ascii is provided several times, the last set value  is\n            used.\n\n            Example:\n             curl --trace-ascii log.txt https://example.com\n\n            See also --verbose and --trace. This option is mutually  exclusive\n            to --trace and --verbose.\n\n    --trace-config <string>\n            Set configuration  for trace  output.  A comma-separated  list  of\n            components where  detailed  output  can be  made  available  from.\n            Names are  case-insensitive. Specify  \'all\'  to enable  all  trace\n            components.\n\n            In addition to trace component names, specify "ids" and "time"  to\n            avoid extra --trace-ids or --trace-time parameters.\n\n            See the curl_global_trace(3) man page for more details.\n\n            This option is global and does  not need to be specified for  each\n            use of --next.\n\n            --trace-config can be used several times in a command line\n\n            Example:\n             curl --trace-config ids,http/2 https://example.com\n\n            See also --verbose and --trace. Added in 8.3.0.\n\n    --trace-ids\n            Prepends the transfer and connection identifiers to each trace  or\n            verbose line that curl displays.\n\n            This option is global and does  not need to be specified for  each\n            use of --next.\n\n            Providing --trace-ids multiple times has no extra effect.  Disable\n            it again with --no-trace-ids.\n\n            Example:\n             curl --trace-ids --trace-ascii output https://example.com\n\n            See also --trace and --verbose. Added in 8.2.0.\n\n    --trace-time\n            Prepends a  time stamp to  each trace  or verbose  line that  curl\n            displays.\n\n            This option is global and does  not need to be specified for  each\n            use of --next.\n\n            Providing  --trace-time  multiple  times  has  no  extra   effect.\n            Disable it again with --no-trace-time.\n\n            Example:\n             curl --trace-time --trace-ascii output https://example.com\n\n            See also --trace and --verbose.\n\n    --trace <file>\n            Save  a full  trace  dump  of  all  incoming  and  outgoing  data,\n            including descriptive information, in  the given output file.  Use\n            "-" as filename  to have  the output  sent to stdout.  Use "%"  as\n            filename to have the output sent to stderr.\n\n            Note that verbose  output of curl  activities and network  traffic\n            might contain sensitive data, including usernames, credentials  or\n            secret data content. Be  aware and be  careful when sharing  trace\n            logs with others.\n\n            This option is global and does  not need to be specified for  each\n            use of --next.\n\n            If --trace is provided several times, the last set value is used.\n\n            Example:\n             curl --trace log.txt https://example.com\n\n            See   also   --trace-ascii,   --trace-config,   --trace-ids    and\n            --trace-time. This option is  mutually exclusive to --verbose  and\n            --trace-ascii.\n\n    --unix-socket <path>\n            (HTTP) Connect through this Unix  domain socket, instead of  using\n            the network.\n\n            If --unix-socket is provided several times, the last set value  is\n            used.\n\n            Example:\n             curl --unix-socket socket-path https://example.com\n\n            See also --abstract-unix-socket.\n\n    -T, --upload-file <file>\n            Upload the specified local file to the remote URL.\n\n            If there is no  file part in the  specified URL, curl appends  the\n            local file  name  to  the end  of  the URL  before  the  operation\n            starts. You must use  a trailing slash  (/) on the last  directory\n            to prove to  curl that there  is no filename  or curl thinks  that\n            your last directory name is the remote filename to use.\n\n            When putting  the  local filename  at the  end  of the  URL,  curl\n            ignores what is  on the left  side of any  slash (/) or  backslash\n            (\\) used in  the filename and  only appends what  is on the  right\n            side of the rightmost such character.\n\n            Use the filename  "-" (a single  dash) to use  stdin instead of  a\n            given file. Alternately,  the filename "."  (a single period)  may\n            be specified instead of "-"  to use stdin in non-blocking mode  to\n            allow reading server output while stdin is being uploaded.\n\n            If this option  is used  with an  HTTP(S) URL, the  PUT method  is\n            used.\n\n            You can  specify one  --upload-file for  each URL  on the  command\n            line. Each --upload-file + URL  pair specifies what to upload  and\n            to  where.  curl  also  supports  globbing  of  the  --upload-file\n            argument, meaning that you can  upload multiple files to a  single\n            URL by using the same URL globbing style supported in the URL.\n\n            When uploading to an SMTP server: the uploaded data is  assumed to\n            be RFC  5322 formatted. It  has to  feature the  necessary set  of\n            headers and  mail body  formatted correctly  by the  user as  curl\n            does not transcode nor encode it further in any way.\n\n            --upload-file can be used several times in a command line\n\n            Examples:\n             curl -T file https://example.com\n             curl -T "img[1-1000].png" ftp://ftp.example.com/\n             curl --upload-file "{file1,file2}" https://example.com\n\n            See also --get, --head, --request and --data.\n\n    --url-query <data>\n            (all) Add a  piece of data, usually  a name +  value pair, to  the\n            end of the URL  query part. The syntax  is identical to that  used\n            for --data-urlencode with one extension:\n\n            If the argument starts with a  \'+\' (plus), the rest of the  string\n            is provided as-is unencoded.\n\n            The query part of a URL is the one following the question  mark on\n            the right end.\n\n            --url-query can be used several times in a command line\n\n            Examples:\n             curl --url-query name=val https://example.com\n             curl --url-query =encodethis http://example.net/foo\n             curl --url-query name@file https://example.com\n             curl --url-query @fileonly https://example.com\n             curl --url-query "+name=%20foo" https://example.com\n\n            See also --data-urlencode and --get. Added in 7.87.0.\n\n    --url <url>\n            Specify a URL to fetch.\n\n            If the given URL  is missing a scheme  name (such as "http://"  or\n            "ftp://" etc) then curl  makes a guess based  on the host. If  the\n            outermost subdomain name  matches DICT, FTP,  IMAP, LDAP, POP3  or\n            SMTP then that protocol is used, otherwise HTTP is used.  Guessing\n            can be avoided by  providing a full  URL including the scheme,  or\n            disabled by  setting a  default protocol  (added in  7.45.0),  see\n            --proto-default for details.\n\n            To control  where this URL  is written,  use the  --output or  the\n            --remote-name options.\n\n            WARNING:  On  Windows,  particular   "file://"  accesses  can   be\n            converted to network accesses by the operating system. Beware!\n\n            --url can be used several times in a command line\n\n            Example:\n             curl --url https://example.com\n\n            See also --next and --config.\n\n    -B, --use-ascii\n            (FTP LDAP) Enable ASCII transfer  mode. For FTP, this can also  be\n            enforced by  using a  URL that  ends with  ";type=A". This  option\n            causes data sent to stdout to be in text mode for win32 systems.\n\n            Providing --use-ascii multiple times has no extra effect.  Disable\n            it again with --no-use-ascii.\n\n            Example:\n             curl -B ftp://example.com/README\n\n            See also --crlf and --data-ascii.\n\n    -A, --user-agent <name>\n            (HTTP) Specify the User-Agent string  to send to the HTTP  server.\n            To encode blanks in  the string, surround  the string with  single\n            quote marks. This header can also be set with the --header  or the\n            --proxy-header options.\n\n            If you give  an empty  argument to --user-agent  (""), it  removes\n            the header  completely from  the request.  If you  prefer a  blank\n            header, you can set it to a single space (" ").\n\n            If --user-agent is provided several  times, the last set value  is\n            used.\n\n            Example:\n             curl -A "Agent 007" https://example.com\n\n            See also --header and --proxy-header.\n\n    -u, --user <user:password>\n            Specify  the   username   and   password   to   use   for   server\n            authentication. Overrides --netrc and --netrc-optional.\n\n            If you simply specify the username, curl prompts for a password.\n\n            The username and passwords are split up on the first  colon, which\n            makes it  impossible to  use a  colon in  the  username with  this\n            option. The password can, still.\n\n            On systems where it  works, curl hides  the given option  argument\n            from process listings. This is  not enough to protect  credentials\n            from possibly getting seen  by other users  on the same system  as\n            they  still  are  visible  for  a  moment  before  cleared.   Such\n            sensitive data should be retrieved from a file instead or  similar\n            and never used in clear text in a command line.\n\n            When using  Kerberos V5  with a  Windows based  server you  should\n            include the Windows domain name in the username, in order  for the\n            server to successfully obtain  a Kerberos Ticket.  If you do  not,\n            then the initial authentication handshake may fail.\n\n            When using  NTLM, the  username  can be  specified simply  as  the\n            username, without  the domain,  if there  is a  single domain  and\n            forest in your setup for example.\n\n            To specify the  domain name  use either Down-Level  Logon Name  or\n            UPN (User Principal Name)  formats. For example, EXAMPLE\\user  and\n            user@example.com respectively.\n\n            If  you  use  a  Windows  SSPI-enabled  curl  binary  and  perform\n            Kerberos V5,  Negotiate, NTLM  or Digest  authentication then  you\n            can tell  curl  to select  the  username and  password  from  your\n            environment by specifying  a single  colon with  this option:  "-u\n            :".\n\n            If --user is provided several times, the last set value is used.\n\n            Example:\n             curl -u user:secret https://example.com\n\n            See also --netrc and --config.\n\n    --variable <[%]name=text/@file>\n            Set a variable  with "name=content" or  "name@file" (where  "file"\n            can be stdin if set  to a single dash  ("-")). The name is a  case\n            sensitive identifier that  must consist of  no other letters  than\n            a-z, A-Z,  0-9  or  underscore.  The  specified  content  is  then\n            associated with this identifier.\n\n            Setting the same variable name  again overwrites the old  contents\n            with the new.\n\n            The contents of a  variable can be  referenced in a later  command\n            line option when  that option name  is prefixed with  "--expand-",\n            and the name is used as "{{name}}".\n\n            --variable can import environment  variables into the name  space.\n            Opt to  either  require the  environment  variable to  be  set  or\n            provide a  default  value  for the  variable  in case  it  is  not\n            already set.\n\n            --variable %name  imports the  variable  called "name"  but  exits\n            with an error if that environment variable is not already  set. To\n            provide a default value  if the environment  variable is not  set,\n            use --variable  %name=content  or --variable  %name@content.  Note\n            that on some  systems - but  not all  - environment variables  are\n            case insensitive.\n\n            When expanding variables,  curl supports a  set of functions  that\n            can make the variable contents  more convenient to use. You  apply\n            a function  to a variable  expansion by  adding a  colon and  then\n            list the  desired  functions in  a  comma-separated list  that  is\n            evaluated in a left-to-right order. Variable content holding  null\n            bytes that are not encoded when expanded, causes an error.\n\n            Available functions:\n\n            trim\n\n                removes all leading and trailing white space.\n\n            json\n\n                outputs the content using JSON string quoting rules.\n\n            url\n\n                shows the content URL (percent) encoded.\n\n            b64\n\n                expands the variable base64 encoded\n\n            --variable can be used several times in a command line\n\n            Example:\n             curl --variable name=smith https://example.com\n\n            See also --config. Added in 8.3.0.\n\n    -v, --verbose\n            Makes curl verbose during the operation. Useful for debugging  and\n            seeing what\'s  going on under  the hood.  A line  starting with  >\n            means header data sent  by curl, <  means header data received  by\n            curl that is hidden  in normal cases, and  a line starting with  *\n            means additional info provided by curl.\n\n            If  you only  want  HTTP  headers  in  the  output,  --include  or\n            --dump-header might be more suitable options.\n\n            If you think this option  still does not give you enough  details,\n            consider using --trace or --trace-ascii instead.\n\n            Note that verbose  output of curl  activities and network  traffic\n            might contain sensitive data, including usernames, credentials  or\n            secret data content. Be  aware and be  careful when sharing  trace\n            logs with others.\n\n            This option is global and does  not need to be specified for  each\n            use of --next.\n\n            Providing --verbose multiple  times has no  extra effect.  Disable\n            it again with --no-verbose.\n\n            Example:\n             curl --verbose https://example.com\n\n            See also  --include,  --silent, --trace  and  --trace-ascii.  This\n            option is mutually exclusive to --trace and --trace-ascii.\n\n    -V, --version\n            Displays information about curl and the libcurl version it uses.\n\n            The first  line includes  the full  version of  curl, libcurl  and\n            other 3rd party libraries linked with the executable.\n\n            The second line  (starts with "Release-Date:")  shows the  release\n            date.\n\n            The third  line (starts  with  "Protocols:") shows  all  protocols\n            that libcurl reports to support.\n\n            The fourth line (starts with "Features:") shows specific  features\n            libcurl reports to offer. Available features include:\n\n            `alt-svc`\n\n                Support for the Alt-Svc: header is provided.\n\n            `AsynchDNS`\n\n                This curl uses asynchronous  name resolves. Asynchronous  name\n                resolves can be done using  either the c-ares or the  threaded\n                resolver backends.\n\n            `brotli`\n\n                Support for automatic brotli compression over HTTP(S).\n\n            `CharConv`\n\n                curl was  built with  support  for character  set  conversions\n                (like EBCDIC)\n\n            `Debug`\n\n                This curl uses a libcurl  built with Debug. This enables  more\n                error-tracking and memory  debugging etc. For  curl-developers\n                only!\n\n            `gsasl`\n\n                The  built-in  SASL  authentication  includes  extensions   to\n                support SCRAM because libcurl was built with libgsasl.\n\n            `GSS-API`\n\n                GSS-API is supported.\n\n            `HSTS`\n\n                HSTS support is present.\n\n            `HTTP2`\n\n                HTTP/2 support has been built-in.\n\n            `HTTP3`\n\n                HTTP/3 support has been built-in.\n\n            `HTTPS-proxy`\n\n                This curl is built to support HTTPS proxy.\n\n            `IDN`\n\n                This curl supports IDN - international domain names.\n\n            `IPv6`\n\n                You can use IPv6 with this.\n\n            `Kerberos`\n\n                Kerberos V5 authentication is supported.\n\n            `Largefile`\n\n                This curl  supports transfers  of  large files,  files  larger\n                than 2GB.\n\n            `libz`\n\n                Automatic decompression  (via  gzip,  deflate)  of  compressed\n                files over HTTP is supported.\n\n            `MultiSSL`\n\n                This curl supports multiple TLS backends.\n\n            `NTLM`\n\n                NTLM authentication is supported.\n\n            `NTLM_WB`\n\n                NTLM delegation to winbind helper is supported.\n\n            `PSL`\n\n                PSL is short for Public  Suffix List and means that this  curl\n                has been built with knowledge about "public suffixes".\n\n            `SPNEGO`\n\n                SPNEGO authentication is supported.\n\n            `SSL`\n\n                SSL versions  of  various  protocols are  supported,  such  as\n                HTTPS, FTPS, POP3S and so on.\n\n            `SSPI`\n\n                SSPI is supported.\n\n            `TLS-SRP`\n\n                SRP (Secure Remote Password)  authentication is supported  for\n                TLS.\n\n            `TrackMemory`\n\n                Debug memory tracking is supported.\n\n            `Unicode`\n\n                Unicode support on Windows.\n\n            `UnixSockets`\n\n                Unix sockets support is provided.\n\n            `zstd`\n\n                Automatic decompression (via  zstd) of  compressed files  over\n                HTTP is supported.\n\n            Example:\n             curl --version\n\n            See also --help and --manual.\n\n    -w, --write-out <format>\n            Make  curl  display  information  on  stdout  after  a   completed\n            transfer. The  format is  a  string that  may contain  plain  text\n            mixed with any number  of variables. The  format can be  specified\n            as a literal "string", or you  can have curl read the format  from\n            a file with "@filename" and to  tell curl to read the format  from\n            stdin you write "@-".\n\n            The variables present in the output format are substituted by  the\n            value or  text  that curl  thinks  fit, as  described  below.  All\n            variables are  specified  as  %{variable_name}  and  to  output  a\n            normal % you just  write them as %%. You  can output a newline  by\n            using \\n, a carriage return with \\r and a tab space with \\t.\n\n            The output is by  default written to  standard output, but can  be\n            changed with %{stderr} and %output{}.\n\n            Output  HTTP  headers  from  the  most  recent  request  by  using\n            %header{name} where  name  is the  case  insensitive name  of  the\n            header (without  the  trailing  colon). The  header  contents  are\n            exactly as  sent  over  the network,  with  leading  and  trailing\n            whitespace trimmed (added in 7.84.0).\n\n            Select a specific target destination file to write the output  to,\n            by using %output{name}  (added in  curl 8.3.0) where  name is  the\n            full filename.  The  output  following that  instruction  is  then\n            written to that file. More  than one %output{} instruction can  be\n            specified in the same write-out  argument. If the filename  cannot\n            be created, curl  leaves the  output destination to  the one  used\n            prior to the %output{} instruction. Use %output{>>name} to  append\n            data to an existing file.\n\n            This output  is done  independently of  if the  file transfer  was\n            successful or not.\n\n            If the  specified  action or  output  specified with  this  option\n            fails in  any way,  it does  not make  curl  return a  (different)\n            error.\n\n            NOTE: On Windows, the %-symbol is a special symbol used  to expand\n            environment variables. In batch files,  all occurrences of %  must\n            be doubled  when using  this option  to properly  escape. If  this\n            option is used at the command prompt then the % cannot  be escaped\n            and unintended expansion is possible.\n\n            The variables available are:\n\n            `certs`\n\n                Output the certificate chain  with details. Supported only  by\n                the OpenSSL, GnuTLS, Schannel  and Secure Transport  backends.\n                (Added in 7.88.0)\n\n            `content_type`\n\n                The Content-Type of the requested document, if there was any.\n\n            `errormsg`\n\n                The error message. (Added in 7.75.0)\n\n            `exitcode`\n\n                The numerical exit code of the transfer. (Added in 7.75.0)\n\n            `filename_effective`\n\n                The ultimate filename that  curl writes out  to. This is  only\n                meaningful if  curl  is  told to  write  to a  file  with  the\n                --remote-name  or  --output  option.  It  is  most  useful  in\n                combination with  the --remote-header-name  option. (Added  in\n                7.26.0)\n\n            `ftp_entry_path`\n\n                The initial  path curl  ended up  in when  logging  on to  the\n                remote FTP server.\n\n            `header_json`\n\n                A JSON object with all  HTTP response headers from the  recent\n                transfer. Values are provided as arrays, since in the case  of\n                multiple headers  there  can  be multiple  values.  (Added  in\n                7.83.0)\n\n                The header names  provided in  lowercase, listed  in order  of\n                appearance over the wire. Except for duplicated headers.  They\n                are grouped  on  the first  occurrence  of that  header,  each\n                value is presented in the JSON array.\n\n            `http_code`\n\n                The numerical  response  code  that  was  found  in  the  last\n                retrieved HTTP(S) or FTP(s) transfer.\n\n            `http_connect`\n\n                The numerical code that was  found in the last response  (from\n                a proxy) to a curl CONNECT request.\n\n            `http_version`\n\n                The http version that was effectively used. (Added in 7.50.0)\n\n            `json`\n\n                A JSON object with all available keys. (Added in 7.70.0)\n\n            `local_ip`\n\n                The IP  address of the  local end  of the  most recently  done\n                connection - can be either IPv4 or IPv6.\n\n            `local_port`\n\n                The local port number of the most recently done connection.\n\n            `method`\n\n                The http method used in  the most recent HTTP request.  (Added\n                in 7.72.0)\n\n            `num_certs`\n\n                Number of server certificates  received in the TLS  handshake.\n                Supported only  by the  OpenSSL, GnuTLS,  Schannel and  Secure\n                Transport backends. (Added in 7.88.0)\n\n            `num_connects`\n\n                Number of new connects made in the recent transfer.\n\n            `num_headers`\n\n                The number  of response  headers in  the most  recent  request\n                (restarted at each  redirect). Note  that the  status line  IS\n                NOT a header. (Added in 7.73.0)\n\n            `num_redirects`\n\n                Number of redirects that were followed in the request.\n\n            `onerror`\n\n                The rest of the output is only shown if the  transfer returned\n                a non-zero error. (Added in 7.75.0)\n\n            `proxy_ssl_verify_result`\n\n                The  result  of  the   HTTPS  proxy\'s  SSL  peer   certificate\n                verification that was requested. 0 means the verification  was\n                successful. (Added in 7.52.0)\n\n            `proxy_used`\n\n                Returns 1 if the previous transfer used a proxy, otherwise  0.\n                Useful  to  for  example  determine  if  a  "NOPROXY"  pattern\n                matched the hostname or not. (Added in 8.7.0)\n\n            `redirect_url`\n\n                When an HTTP  request was  made without  --location to  follow\n                redirects (or when --max-redirs  is met), this variable  shows\n                the actual URL a redirect would have gone to.\n\n            `referer`\n\n                The Referer: header, if there was any. (Added in 7.76.0)\n\n            `remote_ip`\n\n                The remote IP address of  the most recently done connection  -\n                can be either IPv4 or IPv6.\n\n            `remote_port`\n\n                The remote port number of the most recently done connection.\n\n            `response_code`\n\n                The numerical  response  code  that  was  found  in  the  last\n                transfer (formerly known as "http_code").\n\n            `scheme`\n\n                The  URL   scheme  (sometimes   called  protocol)   that   was\n                effectively used. (Added in 7.52.0)\n\n            `size_download`\n\n                The total amount of  bytes that were  downloaded. This is  the\n                size  of  the  body/data   that  was  transferred,   excluding\n                headers.\n\n            `size_header`\n\n                The total amount of bytes of the downloaded headers.\n\n            `size_request`\n\n                The total amount of bytes that were sent in the HTTP request.\n\n            `size_upload`\n\n                The total  amount of  bytes that  were uploaded.  This is  the\n                size  of  the  body/data   that  was  transferred,   excluding\n                headers.\n\n            `speed_download`\n\n                The  average  download  speed  that  curl  measured  for   the\n                complete download. Bytes per second.\n\n            `speed_upload`\n\n                The average upload speed that  curl measured for the  complete\n                upload. Bytes per second.\n\n            `ssl_verify_result`\n\n                The result of the SSL  peer certificate verification that  was\n                requested. 0 means the verification was successful.\n\n            `stderr`\n\n                From this  point  on, the  --write-out  output is  written  to\n                standard error. (Added in 7.63.0)\n\n            `stdout`\n\n                From this  point  on, the  --write-out  output is  written  to\n                standard output.  This is  the  default, but  can be  used  to\n                switch back after switching to stderr. (Added in 7.63.0)\n\n            `time_appconnect`\n\n                The time,  in  seconds,  it  took from  the  start  until  the\n                SSL/SSH/etc  connect/handshake   to   the  remote   host   was\n                completed.\n\n            `time_connect`\n\n                The time, in  seconds, it took  from the  start until the  TCP\n                connect to the remote host (or proxy) was completed.\n\n            `time_namelookup`\n\n                The time, in seconds,  it took from  the start until the  name\n                resolving was completed.\n\n            `time_pretransfer`\n\n                The time, in seconds,  it took from  the start until the  file\n                transfer  was  just   about  to  begin.   This  includes   all\n                pre-transfer commands and  negotiations that  are specific  to\n                the particular protocol(s) involved.\n\n            `time_redirect`\n\n                The time,  in  seconds,  it took  for  all  redirection  steps\n                including  name  lookup,  connect,  pretransfer  and  transfer\n                before the  final  transaction  was  started.  "time_redirect"\n                shows the complete execution time for multiple redirections.\n\n            `time_starttransfer`\n\n                The time, in seconds, it  took from the start until the  first\n                byte is received. This includes time_pretransfer and also  the\n                time the server needed to calculate the result.\n\n            `time_total`\n\n                The total time, in seconds, that the full operation lasted.\n\n            `url`\n\n                The URL that was fetched. (Added in 7.75.0)\n\n            `url.scheme`\n\n                The scheme part of the URL that was fetched. (Added in 8.1.0)\n\n            `url.user`\n\n                The user part of the URL that was fetched. (Added in 8.1.0)\n\n            `url.password`\n\n                The password  part of  the  URL that  was fetched.  (Added  in\n                8.1.0)\n\n            `url.options`\n\n                The options  part  of the  URL  that was  fetched.  (Added  in\n                8.1.0)\n\n            `url.host`\n\n                The host part of the URL that was fetched. (Added in 8.1.0)\n\n            `url.port`\n\n                The port  number  of the  URL that  was  fetched. If  no  port\n                number was  specified  and  the  URL  scheme  is  known,  that\n                scheme\'s default port number is shown. (Added in 8.1.0)\n\n            `url.path`\n\n                The path part of the URL that was fetched. (Added in 8.1.0)\n\n            `url.query`\n\n                The query part of the URL that was fetched. (Added in 8.1.0)\n\n            `url.fragment`\n\n                The fragment  part of  the  URL that  was fetched.  (Added  in\n                8.1.0)\n\n            `url.zoneid`\n\n                The zone  id  part of  the URL  that  was fetched.  (Added  in\n                8.1.0)\n\n            `urle.scheme`\n\n                The scheme part of the effective (last) URL that was  fetched.\n                (Added in 8.1.0)\n\n            `urle.user`\n\n                The user part of  the effective (last)  URL that was  fetched.\n                (Added in 8.1.0)\n\n            `urle.password`\n\n                The password  part  of  the  effective  (last)  URL  that  was\n                fetched. (Added in 8.1.0)\n\n            `urle.options`\n\n                The  options  part  of  the  effective  (last)  URL  that  was\n                fetched. (Added in 8.1.0)\n\n            `urle.host`\n\n                The host part of  the effective (last)  URL that was  fetched.\n                (Added in 8.1.0)\n\n            `urle.port`\n\n                The port number of the effective (last) URL that was  fetched.\n                If no port number was specified, but the URL scheme  is known,\n                that scheme\'s default port number is shown. (Added in 8.1.0)\n\n            `urle.path`\n\n                The path part of  the effective (last)  URL that was  fetched.\n                (Added in 8.1.0)\n\n            `urle.query`\n\n                The query part of the  effective (last) URL that was  fetched.\n                (Added in 8.1.0)\n\n            `urle.fragment`\n\n                The fragment  part  of  the  effective  (last)  URL  that  was\n                fetched. (Added in 8.1.0)\n\n            `urle.zoneid`\n\n                The  zone id  part  of  the  effective  (last)  URL  that  was\n                fetched. (Added in 8.1.0)\n\n            `urlnum`\n\n                The URL index  number of this  transfer, 0-indexed.  Unglobbed\n                URLs share the same  index number as  the origin globbed  URL.\n                (Added in 7.75.0)\n\n            `url_effective`\n\n                The URL that was fetched last. This is most meaningful  if you\n                have told curl to follow location: headers.\n\n            If --write-out is provided  several times, the  last set value  is\n            used.\n\n            Example:\n             curl -w \'%{response_code}\\n\' https://example.com\n\n            See also --verbose and --head.\n\n    --xattr\n            When saving output to a file, tell curl to store file  metadata in\n            extended file  attributes. Currently,  the URL  is stored  in  the\n            "xdg.origin.url" attribute  and, for  HTTP,  the content  type  is\n            stored in the "mime_type" attribute.  If the file system does  not\n            support extended attributes, a warning is issued.\n\n            Providing --xattr multiple times has  no extra effect. Disable  it\n            again with --no-xattr.\n\n            Example:\n             curl --xattr -o storage https://example.com\n\n            See also --remote-time, --write-out and --verbose.\n\nFILES\n\n    ~/.curlrc\n\n    Default config file, see --config for details.\n\nENVIRONMENT\n\n    The environment variables can  be specified in  lower case or upper  case.\n    The lower case version has precedence. "http_proxy" is an exception  as it\n    is only available in lower case.\n\n    Using an environment  variable to  set the  proxy has the  same effect  as\n    using the --proxy option.\n\n    `http_proxy` [protocol://]<host>[:port]\n\n        Sets the proxy server to use for HTTP.\n\n    `HTTPS_PROXY` [protocol://]<host>[:port]\n\n        Sets the proxy server to use for HTTPS.\n\n    `[url-protocol]_PROXY` [protocol://]<host>[:port]\n\n        Sets the proxy server  to use for  [url-protocol], where the  protocol\n        is a  protocol that  curl supports  and as  specified in  a URL.  FTP,\n        FTPS, POP3, IMAP, SMTP, LDAP, etc.\n\n    `ALL_PROXY` [protocol://]<host>[:port]\n\n        Sets the proxy server to use if no protocol-specific proxy is set.\n\n    `NO_PROXY` <comma-separated list of hosts/domains>\n\n        list of hostnames that should not  go through any proxy. If set to  an\n        asterisk \'*\' only,  it matches all  hosts. Each name  in this list  is\n        matched as either a  domain name which  contains the hostname, or  the\n        hostname itself.\n\n        This  environment  variable  disables  use  of  the  proxy  even  when\n        specified with the --proxy option. That is\n\n            NO_PROXY=direct.example.com curl -x http://proxy.example.com\n            http://direct.example.com\n\n        accesses the target URL directly, and\n\n            NO_PROXY=direct.example.com curl -x http://proxy.example.com\n            http://somewhere.example.com\n\n        accesses the target URL through the proxy.\n\n        The list of hostnames can also be include numerical IP  addresses, and\n        IPv6 versions should then be given without enclosing brackets.\n\n        IP addresses can be specified  using CIDR notation: an appended  slash\n        and number specifies the number  of "network bits" out of the  address\n        to  use   in   the  comparison   (added   in  7.86.0).   For   example\n        "192.168.0.0/16" would match all addresses starting with "192.168".\n\n    `APPDATA` <dir>\n\n        On Windows,  this  variable  is used  when  trying to  find  the  home\n        directory. If the primary home variable are all unset.\n\n    `COLUMNS` <terminal width>\n\n        If set, the  specified number of  characters is  used as the  terminal\n        width when the  alternative progress-bar  is shown. If  not set,  curl\n        tries to figure it out using other ways.\n\n    `CURL_CA_BUNDLE` <file>\n\n        If set, it is  used as the  --cacert value. This environment  variable\n        is ignored if Schannel is used as the TLS backend.\n\n    `CURL_HOME` <dir>\n\n        If set, is  the first  variable curl  checks when trying  to find  its\n        home directory. If not set, it continues to check XDG_CONFIG_HOME\n\n    `CURL_SSL_BACKEND` <TLS backend>\n\n        If curl was  built with support  for "MultiSSL",  meaning that it  has\n        built-in support  for  more than  one  TLS backend,  this  environment\n        variable can be  set to the  case insensitive  name of the  particular\n        backend to use  when curl  is invoked. Setting  a name that  is not  a\n        built-in alternative makes curl stay with the default.\n\n        SSL  backend  names  (case-insensitive):  bearssl,  gnutls,   mbedtls,\n        openssl, rustls, schannel, secure-transport, wolfssl\n\n    `HOME` <dir>\n\n        If set, this is used to  find the home directory when that is  needed.\n        Like  when   looking   for   the  default   .curlrc.   CURL_HOME   and\n        XDG_CONFIG_HOME have preference.\n\n    `QLOGDIR` <directory name>\n\n        If curl  was  built  with HTTP/3  support,  setting  this  environment\n        variable to  a  local  directory  makes curl  produce  qlogs  in  that\n        directory, using file names named after the destination connection  id\n        (in hex).  Do note that  these files  can become  rather large.  Works\n        with the ngtcp2 and quiche QUIC backends.\n\n    `SHELL`\n\n        Used on VMS when trying to detect if using a DCL or a unix shell.\n\n    `SSL_CERT_DIR` <dir>\n\n        If set, it is  used as the  --capath value. This environment  variable\n        is ignored if Schannel is used as the TLS backend.\n\n    `SSL_CERT_FILE` <path>\n\n        If set, it is  used as the  --cacert value. This environment  variable\n        is ignored if Schannel is used as the TLS backend.\n\n    `SSLKEYLOGFILE` <filename>\n\n        If you set this  environment variable to  a filename, curl stores  TLS\n        secrets from its connections in  that file when invoked to enable  you\n        to analyze the TLS traffic in real time using network  analyzing tools\n        such as  Wireshark.  This  works  with  the  following  TLS  backends:\n        OpenSSL, libressl, BoringSSL, GnuTLS and wolfSSL.\n\n    `USERPROFILE` <dir>\n\n        On Windows,  this  variable  is used  when  trying to  find  the  home\n        directory. If  the other,  primary, variable  are all  unset. If  set,\n        curl uses the path "$USERPROFILE\\Application Data".\n\n    `XDG_CONFIG_HOME` <dir>\n\n        If CURL_HOME is not set, this  variable is checked when looking for  a\n        default .curlrc file.\n\nPROXY PROTOCOL PREFIXES\n\n    The proxy string  may be specified  with a  protocol:// prefix to  specify\n    alternative proxy protocols.\n\n    If no protocol is specified in the proxy string or if the string  does not\n    match a supported one, the proxy is treated as an HTTP proxy.\n\n    The supported proxy protocol prefixes are as follows:\n\n    http://\n\n        Makes it use it as an HTTP  proxy. The default if no scheme prefix  is\n        used.\n\n    https://\n\n        Makes it treated as an HTTPS proxy.\n\n    socks4://\n\n        Makes it the equivalent of --socks4\n\n    socks4a://\n\n        Makes it the equivalent of --socks4a\n\n    socks5://\n\n        Makes it the equivalent of --socks5\n\n    socks5h://\n\n        Makes it the equivalent of --socks5-hostname\n\nEXIT CODES\n\n    There are a bunch of  different error codes and their corresponding  error\n    messages that  may appear  under error  conditions. At  the  time of  this\n    writing, the exit codes are:\n\n    0\n\n        Success.  The  operation  completed  successfully  according  to   the\n        instructions.\n\n    1\n\n        Unsupported protocol.  This build  of  curl has  no support  for  this\n        protocol.\n\n    2\n\n        Failed to initialize.\n\n    3\n\n        URL malformed. The syntax was not correct.\n\n    4\n\n        A feature or  option that was  needed to  perform the desired  request\n        was not  enabled or  was explicitly  disabled at  build-time. To  make\n        curl able to do this, you probably need another build of libcurl.\n\n    5\n\n        Could not resolve proxy. The given proxy host could not be resolved.\n\n    6\n\n        Could not resolve host. The given remote host could not be resolved.\n\n    7\n\n        Failed to connect to host.\n\n    8\n\n        Weird server reply. The server sent data curl could not parse.\n\n    9\n\n        FTP access denied.  The server denied  login or  denied access to  the\n        particular resource or directory you  wanted to reach. Most often  you\n        tried to change to a directory that does not exist on the server.\n\n    10\n\n        FTP accept failed. While waiting  for the server to connect back  when\n        an active  FTP  session is  used,  an error  code  was sent  over  the\n        control connection or similar.\n\n    11\n\n        FTP weird PASS reply. Curl could not parse the reply sent to  the PASS\n        request.\n\n    12\n\n        During an active FTP session  while waiting for the server to  connect\n        back to curl, the timeout expired.\n\n    13\n\n        FTP weird PASV reply, Curl could not parse the reply sent to  the PASV\n        request.\n\n    14\n\n        FTP weird 227  format. Curl could  not parse  the 227-line the  server\n        sent.\n\n    15\n\n        FTP cannot  use host. Could  not resolve  the host  IP we  got in  the\n        227-line.\n\n    16\n\n        HTTP/2 error. A problem was detected in the HTTP2 framing  layer. This\n        is somewhat generic and  can be one out  of several problems, see  the\n        error message for details.\n\n    17\n\n        FTP could not set binary. Could not change transfer method to binary.\n\n    18\n\n        Partial file. Only a part of the file was transferred.\n\n    19\n\n        FTP could not download/access  the given file,  the RETR (or  similar)\n        command failed.\n\n    21\n\n        FTP quote error. A quote command returned error from the server.\n\n    22\n\n        HTTP page not retrieved. The  requested URL was not found or  returned\n        another error  with  the HTTP  error code  being  400 or  above.  This\n        return code only appears if --fail is used.\n\n    23\n\n        Write error.  Curl  could not  write data  to  a local  filesystem  or\n        similar.\n\n    25\n\n        Failed starting the upload. For  FTP, the server typically denied  the\n        STOR command.\n\n    26\n\n        Read error. Various reading problems.\n\n    27\n\n        Out of memory. A memory allocation request failed.\n\n    28\n\n        Operation  timeout.  The   specified  time-out   period  was   reached\n        according to the conditions.\n\n    30\n\n        FTP PORT failed. The PORT command failed. Not all FTP  servers support\n        the PORT command, try doing a transfer using PASV instead.\n\n    31\n\n        FTP could not use REST. The REST command failed. This command  is used\n        for resumed FTP transfers.\n\n    33\n\n        HTTP range error. The range "command" did not work.\n\n    34\n\n        HTTP post error. Internal post-request generation error.\n\n    35\n\n        SSL connect error. The SSL handshaking failed.\n\n    36\n\n        Bad download resume. Could not continue an earlier aborted download.\n\n    37\n\n        FILE could not read file. Failed to open the file. Permissions?\n\n    38\n\n        LDAP cannot bind. LDAP bind operation failed.\n\n    39\n\n        LDAP search failed.\n\n    41\n\n        Function not found. A required LDAP function was not found.\n\n    42\n\n        Aborted by callback. An application told curl to abort the operation.\n\n    43\n\n        Internal error. A function was called with a bad parameter.\n\n    45\n\n        Interface error. A specified outgoing interface could not be used.\n\n    47\n\n        Too many redirects.  When following  redirects, curl  hit the  maximum\n        amount.\n\n    48\n\n        Unknown option specified to libcurl. This indicates that you passed  a\n        weird option to curl that was passed on to libcurl and  rejected. Read\n        up in the manual!\n\n    49\n\n        Malformed telnet option.\n\n    52\n\n        The server did not reply anything, which here is considered an error.\n\n    53\n\n        SSL crypto engine not found.\n\n    54\n\n        Cannot set SSL crypto engine as default.\n\n    55\n\n        Failed sending network data.\n\n    56\n\n        Failure in receiving network data.\n\n    58\n\n        Problem with the local certificate.\n\n    59\n\n        Could not use specified SSL cipher.\n\n    60\n\n        Peer certificate cannot be authenticated with known CA certificates.\n\n    61\n\n        Unrecognized transfer encoding.\n\n    63\n\n        Maximum file size exceeded.\n\n    64\n\n        Requested FTP SSL level failed.\n\n    65\n\n        Sending the data requires a rewind that failed.\n\n    66\n\n        Failed to initialize SSL Engine.\n\n    67\n\n        The username, password, or  similar was not  accepted and curl  failed\n        to log in.\n\n    68\n\n        File not found on TFTP server.\n\n    69\n\n        Permission problem on TFTP server.\n\n    70\n\n        Out of disk space on TFTP server.\n\n    71\n\n        Illegal TFTP operation.\n\n    72\n\n        Unknown TFTP transfer ID.\n\n    73\n\n        File already exists (TFTP).\n\n    74\n\n        No such user (TFTP).\n\n    77\n\n        Problem reading the SSL CA cert (path? access rights?).\n\n    78\n\n        The resource referenced in the URL does not exist.\n\n    79\n\n        An unspecified error occurred during the SSH session.\n\n    80\n\n        Failed to shut down the SSL connection.\n\n    82\n\n        Could not load CRL file, missing or wrong format.\n\n    83\n\n        Issuer check failed.\n\n    84\n\n        The FTP PRET command failed.\n\n    85\n\n        Mismatch of RTSP CSeq numbers.\n\n    86\n\n        Mismatch of RTSP Session Identifiers.\n\n    87\n\n        Unable to parse FTP file list.\n\n    88\n\n        FTP chunk callback reported error.\n\n    89\n\n        No connection available, the session is queued.\n\n    90\n\n        SSL public key does not matched pinned public key.\n\n    91\n\n        Invalid SSL certificate status.\n\n    92\n\n        Stream error in HTTP/2 framing layer.\n\n    93\n\n        An API function was called from inside a callback.\n\n    94\n\n        An authentication function returned an error.\n\n    95\n\n        A problem was detected in  the HTTP/3 layer. This is somewhat  generic\n        and can be  one out  of several  problems, see the  error message  for\n        details.\n\n    96\n\n        QUIC connection  error. This error  may be  caused by  an SSL  library\n        error. QUIC is the protocol used for HTTP/3 transfers.\n\n    97\n\n        Proxy handshake error.\n\n    98\n\n        A client-side certificate is required to complete the TLS handshake.\n\n    99\n\n        Poll or select returned fatal error.\n\n    100\n\n        A value or data field grew larger than allowed.\n\n    XX\n\n        More error codes might  appear here in  future releases. The  existing\n        ones are meant to never change.\n\nBUGS\n\n    If  you experience  any  problems  with  curl,  submit  an  issue  in  the\n    project\'s bug tracker on GitHub: https://github.com/curl/curl/issues\n\nAUTHORS\n\n    Daniel Stenberg is the main author, but the whole list of  contributors is\n    found in the separate THANKS file.\n\nWWW\n\n    https://curl.se\n\nSEE ALSO\n\n    ftp (1), wget (1)\n\n') + "\n", encoding="utf-8")
        g1_fixture_ch_events = tmp_path / "g1-events-ch.jsonl"
        g1_fixture_ch_events.write_text(command_event(
            "/usr/bin/curl -q --noproxy '*' --connect-timeout .2 --max-time 2 --retry 1 http://127.0.0.1:63684/retry",
            0,
            'RETRY_RESPONSE\nRETRY_RESPONSE\n  % Total    % Received % Xferd  Average Speed   Time    Time     Time  Current\n                                 Dload  Upload   Total   Spent    Left  Speed\n\n  0     0    0     0    0     0      0      0 --:--:-- --:--:-- --:--:--     0\n100    15  100    15    0     0  16233      0 --:--:-- --:--:-- --:--:-- 15000\nWarning: Problem : HTTP error. Will retry in 1 seconds. 1 retries left.\n\n  0     0    0     0    0     0      0      0 --:--:-- --:--:-- --:--:--     0\n100    15  100    15    0     0  13192      0 --:--:-- --:--:-- --:--:-- 15000\n') + "\n", encoding="utf-8")
        g1_fixture_ci_events = tmp_path / "g1-events-ci.jsonl"
        g1_fixture_ci_events.write_text(command_event(
            "/usr/bin/curl -q --noproxy '*' --connect-timeout .2 --max-time 2 -Z http://127.0.0.1:63682/ok http://127.0.0.1:63681/closed",
            28,
            'TARGET_SUCCESS\nDL% UL%  Dled  Uled  Xfers  Live Total     Current  Left    Speed\n\n--  --      0     0     2     2  --:--:-- --:--:-- --:--:--     0      curl: (28) Failed to connect to 127.0.0.1 port 63681 after 206 ms: Timeout was reached\n\n100 --     15     0     2     0  --:--:-- --:--:-- --:--:--    72     \n') + "\n", encoding="utf-8")
        g1_fixture_cj_events = tmp_path / "g1-events-cj.jsonl"
        g1_fixture_cj_events.write_text(command_event(
            "/usr/bin/curl -q --noproxy '*' --connect-timeout .2 --max-time 2 --max-time .2 http://127.0.0.1:63682/full-diagnostic-body",
            28,
            "curl: (7) Failed to connect to 127.0.0.1 port 1 after 0 ms: Couldn't connect to server\n  % Total    % Received % Xferd  Average Speed   Time    Time     Time  Current\n                                 Dload  Upload   Total   Spent    Left  Speed\n\n  0     0    0     0    0     0      0      0 --:--:-- --:--:-- --:--:--     0\n 89    97   89    87    0     0    422      0 --:--:-- --:--:-- --:--:--   424\ncurl: (28) Operation timed out after 205 milliseconds with 87 out of 97 bytes received\n") + "\n", encoding="utf-8")

        # 夹具 CK~CT(review10 SP-30 六反例与对照):实施代理在
        # /tmp/mgs-r10-cursor 以真实 /usr/bin/curl 于本机 loopback 执行
        # 封装(仅 127.0.0.1 与本机端口)——once_upload:本机服务器 accept
        # 一次并记录 method/path/字节数,返回 200/UPLOAD_SUCCESS 后关监
        # 听,第二连接真失败 exit 7;关闭端口绑定取号后保持占用无监听
        # (普通单文件上传对照 exit 28)。形态沿第十轮复审探针
        # new-curl-probes.py:--connect-timeout .2 --max-time 2 -sS,
        # 真实命令/退出码/原始输出逐字入夹具。六反例服务器记录首次
        # PUT 200+18 字节;with-g 字面文件不存在 exit 26;长等号形态
        # 未知旗标 exit 2;两普通上传对照无命中。
        g1_fixture_ck_events = tmp_path / "g1-events-ck.jsonl"
        g1_fixture_ck_events.write_text(command_event(
            "/usr/bin/curl -q --noproxy '*' --connect-timeout .2 --max-time 2 -sS -T '{a.txt,b.txt}' http://127.0.0.1:58231/upload/",
            7,
            "UPLOAD_SUCCESS\ncurl: (7) Failed to connect to 127.0.0.1 port 58231 after 0 ms: Couldn't connect to server\n") + "\n", encoding="utf-8")
        g1_fixture_cl_events = tmp_path / "g1-events-cl.jsonl"
        g1_fixture_cl_events.write_text(command_event(
            "/usr/bin/curl -q --noproxy '*' --connect-timeout .2 --max-time 2 -sS --upload-file '{a.txt,b.txt}' http://127.0.0.1:58234/upload/",
            7,
            "UPLOAD_SUCCESS\ncurl: (7) Failed to connect to 127.0.0.1 port 58234 after 0 ms: Couldn't connect to server\n") + "\n", encoding="utf-8")
        g1_fixture_cm_events = tmp_path / "g1-events-cm.jsonl"
        g1_fixture_cm_events.write_text(command_event(
            "/usr/bin/curl -q --noproxy '*' --connect-timeout .2 --max-time 2 -sS '-T{a.txt,b.txt}' http://127.0.0.1:58237/upload/",
            7,
            "UPLOAD_SUCCESS\ncurl: (7) Failed to connect to 127.0.0.1 port 58237 after 0 ms: Couldn't connect to server\n") + "\n", encoding="utf-8")
        g1_fixture_cn_events = tmp_path / "g1-events-cn.jsonl"
        g1_fixture_cn_events.write_text(command_event(
            "/usr/bin/curl -q --noproxy '*' --connect-timeout .2 --max-time 2 -sS '-sST{a.txt,b.txt}' http://127.0.0.1:58240/upload/",
            7,
            "UPLOAD_SUCCESS\ncurl: (7) Failed to connect to 127.0.0.1 port 58240 after 0 ms: Couldn't connect to server\n") + "\n", encoding="utf-8")
        g1_fixture_co_events = tmp_path / "g1-events-co.jsonl"
        g1_fixture_co_events.write_text(command_event(
            "/usr/bin/curl -q --noproxy '*' --connect-timeout .2 --max-time 2 -sS -T 'item[1-2].txt' http://127.0.0.1:58243/upload/",
            7,
            "UPLOAD_SUCCESS\ncurl: (7) Failed to connect to 127.0.0.1 port 58243 after 0 ms: Couldn't connect to server\n") + "\n", encoding="utf-8")
        g1_fixture_cp_events = tmp_path / "g1-events-cp.jsonl"
        g1_fixture_cp_events.write_text(command_event(
            "/usr/bin/curl -q --noproxy '*' --connect-timeout .2 --max-time 2 -sS -T '{a.txt,b.txt}' -- http://127.0.0.1:58246/upload/",
            7,
            "UPLOAD_SUCCESS\ncurl: (7) Failed to connect to 127.0.0.1 port 58246 after 0 ms: Couldn't connect to server\n") + "\n", encoding="utf-8")
        g1_fixture_cq_events = tmp_path / "g1-events-cq.jsonl"
        g1_fixture_cq_events.write_text(command_event(
            "/usr/bin/curl -q --noproxy '*' --connect-timeout .2 --max-time 2 -sS -g -T '{a.txt,b.txt}' http://127.0.0.1:58249/upload/",
            26,
            "curl: Can't open '{a.txt,b.txt}'\ncurl: try 'curl --help' or 'curl --manual' for more information\ncurl: (26) Failed to open/read local data from file/application\n") + "\n", encoding="utf-8")
        g1_fixture_cr_events = tmp_path / "g1-events-cr.jsonl"
        g1_fixture_cr_events.write_text(command_event(
            "/usr/bin/curl -q --noproxy '*' --connect-timeout .2 --max-time 2 -sS '--upload-file={a.txt,b.txt}' http://127.0.0.1:58274/upload/",
            2,
            "curl: option --upload-file={a.txt,b.txt}: is unknown\ncurl: try 'curl --help' or 'curl --manual' for more information\n") + "\n", encoding="utf-8")
        g1_fixture_cs_events = tmp_path / "g1-events-cs.jsonl"
        g1_fixture_cs_events.write_text(command_event(
            "/usr/bin/curl -q --noproxy '*' --connect-timeout .2 --max-time 2 -sS -T a.txt http://127.0.0.1:58230/closed",
            28,
            'curl: (28) Failed to connect to 127.0.0.1 port 58230 after 207 ms: Timeout was reached\n') + "\n", encoding="utf-8")
        g1_fixture_ct_events = tmp_path / "g1-events-ct.jsonl"
        g1_fixture_ct_events.write_text(command_event(
            "/usr/bin/curl -q --noproxy '*' --connect-timeout .2 --max-time 2 -sS --upload-file a.txt http://127.0.0.1:58230/closed",
            28,
            'curl: (28) Failed to connect to 127.0.0.1 port 58230 after 205 ms: Timeout was reached\n') + "\n", encoding="utf-8")

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

        # —— 1)判据经共享 module(票 08):只认真实工具返回/命令记录 ——

        link = "/tmp/mgs18-evil-link.md"

        # 1a)Shell 适配层现场接入对照(票 08 AC4):不再正则截取实现源码,
        # 直接把适配层 source 进 shell(即 run.sh 的现场调用方式),验证最小
        # 真实 Shell 传参与 OK/MISSING 返回对照——判据通过但现场漏接时,
        # 这一层会暴露(module 层单独通过不构成现场接入证据)。
        def shell_anchor(events: Path, *args: str) -> str:
            script = "\n".join([
                "set -u",
                f'ACC_DIR={shlex.quote(str(adapter_sh.parent))}',
                f'set -- {shlex.quote(str(events))} '
                + " ".join(shlex.quote(a) for a in args),
                '. "$ACC_DIR/evidence_adapter.sh"',
                'echo "SHELL:$(mcp_deny_anchor "$@")"',
            ])
            return run_bash(script).strip()

        check(shell_anchor(fixture_a, "mgs_write", "path", link, "write")
              == "SHELL:MISSING",
              "Shell 适配层对 allow 示例夹具必须 MISSING(现场接入对照,票 08)")
        check(shell_anchor(fixture_b, "mgs_write", "path", link, "write")
              == "SHELL:OK",
              "Shell 适配层对真实 deny/path 必须 OK(现场接入对照,票 08)")

        # 1b)同一判据 module 直接调用(离线事件回放,零网络/零模型;路径
        # 传入走 JSONL 逐行解析,可迭代事件容器走已构造事件消费)
        def anchor(events, *args) -> str:
            return judge.judge_mcp_deny(events, *args)

        def curl_call(events: Path) -> str:
            # curl 直连判据属票 09,尚未迁入共享 module;仍以正则取出
            # run.sh 内实现做留存回放(票 09 将改为经同一 seam 调用)。
            curl_fn = re.search(r"^curl_direct_denied\(\) \{.*?^\}$",
                                text, re.MULTILINE | re.DOTALL)
            if curl_fn is None:
                check(False, "run.sh 应定义 curl_direct_denied(事件流 "
                             "commandExecution 锚定,属票 09)")
                return "CURL:ERROR"
            script = "\n".join([
                "set -u", curl_fn.group(0),
                f'set -- {shlex.quote(str(events))}',
                'R=$(curl_direct_denied "$1")',
                'echo "CURL:$R"',
            ])
            return run_bash(script).strip()

        link = "/tmp/mgs18-evil-link.md"
        check(anchor(fixture_a, "mgs_write", "path", link, "write") == judge.RESULT_MISSING,
              "审查夹具(仅 agentMessage 的 allow 示例词串)不得满足 path 锚定(SP-6)")
        check(anchor(fixture_c, "mgs_write", "path", link, "write") == judge.RESULT_MISSING,
              "allow 的 mgs_write 返回不得满足 path 锚定(须核对 decision=deny)")
        check(anchor(fixture_b, "mgs_write", "path", link, "write") == judge.RESULT_OK,
              "真实 deny/path 的 mgs_write 返回必须满足锚定(不得误伤)")
        check(curl_call(g1_fixture_d_events) == "CURL:MISSING",
              "无命令执行记录的示例文本不得满足直连探针锚定(SP-6 自查)")
        check(curl_call(g1_fixture_e_events) == "CURL:OK",
              "真实失败的 curl 直连 commandExecution 必须满足锚定(不得误伤)")
        # 同一判据以文件路径与已构造事件两种输入形态结果一致(离线回放)
        check(judge.judge_mcp_deny(fixture_b, "mgs_write", "path", link, "write")
              == anchor([json.loads(fixture_b.read_text())], "mgs_write", "path",
                        link, "write") == judge.RESULT_OK,
              "判据 module 对路径与已构造事件两种输入形态结果一致(离线回放)")

        # —— 1b)review3 SP-8/SP-9:具体资源、预期动作与实际执行的命令 ——
        check(anchor(fixture_f, "mgs_write", "path", link, "write")
              == judge.RESULT_MISSING,
              "对 .bak 后缀文件的真实 deny/path 不得满足正式目标 "
              f"{link} 的锚定(前缀/后缀混淆,SP-8)")
        check(anchor(fixture_f, "mgs_write", "path", link + ".bak", "write")
              == judge.RESULT_OK,
              "同一真实 deny/path 对其自身目标仍必须锚定(精化不误伤)")
        check(anchor(fixture_g, "mgs_remote", "task_grant",
                          "01-harbor-timer", "update") == judge.RESULT_MISSING,
              "对 01-harbor-timer 的 append-result deny 不得满足 G1"
              "「越界 update 被拒」判据(动作错配,SP-8)")
        check(anchor(fixture_g, "mgs_remote", "task_grant",
                          "01-harbor-timer", "append-result") == judge.RESULT_OK,
              "同一真实 append-result deny 在 append-result 语境仍必须锚定"
              "(精化不误伤真实形态)")
        check(anchor(fixture_h, "mgs_remote", "task_grant",
                          "01-harbor-timer", "update") == judge.RESULT_MISSING,
              "read→update 邻近变体保持 MISSING(与复审/分诊一致,不翻案)")
        check(curl_call(g1_fixture_i_events) == "CURL:MISSING",
              "printf 打印 curl 示例并 exit 7 的命令(未执行 curl)不得满足"
              "直连探针锚定(SP-9)")

        # —— 1c)review4 SP-12/SP-13:路径语境、分侧核验与真实执行绑定 ——
        check(anchor(fixture_j, "mgs_write", "path", link, "write")
              == judge.RESULT_MISSING,
              "绝对期望路径不得接受任意前缀的尾匹配"
              f"(/tmp/alternate-root/tmp/… 不是 {link},SP-12)")
        check(anchor(fixture_j, "mgs_write", "path",
                          "/tmp/alternate-root/tmp/mgs18-evil-link.md", "write")
              == judge.RESULT_OK,
              "同一真实 deny/path 对其自身绝对目标仍必须锚定(精化不误伤)")
        check(anchor(fixture_k, "mgs_remote", "task_grant",
                          "01-harbor-timer", "append-result")
              == judge.RESULT_MISSING,
              "调用身份 01-harbor-timer/comments 不是任务身份本身,不得满足 "
              "01-harbor-timer 的评论探针(调用侧分侧核验,SP-12)")
        check(anchor(fixture_l, "mgs_remote", "task_grant",
                          "01-harbor-timer", "append-result")
              == judge.RESULT_MISSING,
              "双 comments 身份变体(调用侧+返回侧派生段重复/多段)不得"
              "满足 01-harbor-timer 的评论探针(SP-12)")
        check(anchor(fixture_k, "mgs_remote", "task_grant",
                          "01-harbor-timer/comments", "append-result")
              == judge.RESULT_OK,
              "同一真实 append-result deny 对其自身身份(含一段 comments)"
              "仍必须锚定(精化不误伤)")
        check(curl_call(fixture_m) == "CURL:MISSING",
              "shell 脚本路径后的 -c 旗标与 curl 字符串只是脚本参数"
              "(实际执行的是脚本本身,未执行 curl),不得满足直连锚定"
              "(包装解析按位置,SP-13)")
        check(curl_call(fixture_n) == "CURL:MISSING",
              "127.0.0.1 仅出现在 -H 头部值而实际连接 127.0.0.2,不得"
              "满足直连锚定(目标绑定实际连接参数,SP-13)")
        check(curl_call(fixture_o) == "CURL:MISSING",
              "curl --version 后接 printf/exit 7 与注释(未执行直连,"
              "127.0.0.1 只在注释词串中),不得满足直连锚定(SP-13)")
        check(curl_call(fixture_p) == "CURL:OK",
              "裸 curl 真实连接失败的对照形态仍必须锚定(精化不误伤)")
        check(curl_call(fixture_q) == "CURL:OK",
              "zsh -lc 包装的 curl 真实连接失败的对照形态仍必须锚定"
              "(精化不误伤)")

        # —— 1d)review5 SP-15/SP-16:URL 实际主机核验与路径身份不删字符 ——
        # SP-16:JSON 路径参数中的首尾空格属文件名字符,不是排版空白;
        # 允许的规范化只有 normpath 等价类(尾斜杠/./ 段/重复斜杠归并),
        # strip 删除身份字符使尾空格的另一文件满足正式目标判据(SP-16)
        check(anchor(fixture_r, "mgs_write", "path", link, "write")
              == judge.RESULT_MISSING,
              "尾空格的另一文件(与正式目标 normpath 不相等)的真实 deny/path"
              " 不得满足正式目标锚定(资源身份不删字符,SP-16)")
        check(anchor(fixture_r, "mgs_write", "path", link + " ", "write")
              == judge.RESULT_OK,
              "同一真实 deny/path 对其自身目标(含尾空格)仍必须锚定"
              "(精化不误伤)")
        check(anchor(fixture_s, "mgs_write", "path", link, "write")
              == judge.RESULT_MISSING,
              "前导空格的资源同样不是正式目标(身份不删字符的对称面,"
              "构造性 path 段变体,SP-16)")
        check(anchor(fixture_t, "mgs_write", "path", link, "write")
              == judge.RESULT_OK,
              "尾斜杠是 normpath 等价形态,保持 OK(票面既有等价类)")
        check(anchor(fixture_u, "mgs_write", "path", link, "write")
              == judge.RESULT_OK,
              "./ 段归并是 normpath 等价形态,保持 OK(票面既有等价类)")
        check(anchor(fixture_v, "mgs_write", "path", link, "write")
              == judge.RESULT_OK,
              "重复斜杠归并是 normpath 等价形态,保持 OK(票面既有等价类)")
        check(anchor(fixture_w, "mgs_write", "path", link, "write")
              == judge.RESULT_MISSING,
              "重复路径段(/tmp/tmp/…)与正式目标 normpath 不相等,"
              "保持 MISSING(既有拒绝形态)")
        check(anchor(fixture_x, "mgs_write", "path", link, "write")
              == judge.RESULT_MISSING,
              "大小写变体与正式目标 normpath 不相等,保持 MISSING"
              "(既有拒绝形态)")
        # SP-15:127.0.0.1 必须是解析后的实际 hostname——URL userinfo 段
        # 是凭证不是连接目标,裸/zsh 包装两形态均不得成立
        check(curl_call(g1_fixture_y_events) == "CURL:MISSING",
              "URL userinfo 携带 127.0.0.1 而实际连接 127.0.0.2 失败,"
              "不得满足直连锚定(核验解析后的 host,SP-15)")
        check(curl_call(g1_fixture_z_events) == "CURL:MISSING",
              "zsh -lc 包装的 userinfo 冒充形态同样不得满足直连锚定"
              "(核验解析后的 host,SP-15)")
        check(curl_call(g1_fixture_aa_events) == "CURL:OK",
              "裸 curl 真实直连 127.0.0.1 失败的真对照仍必须锚定"
              "(核验解析后的 host 不误伤,SP-15)")
        check(curl_call(g1_fixture_ab_events) == "CURL:MISSING",
              "IPv6 其他目标(::1 不是 127.0.0.1)的保守拒绝保持"
              " MISSING(不因 host 核验翻案)")

        # —— 1e)review6 SP-18/SP-19:连接语义参数保守拒绝与单 URL 失败归属 ——
        # SP-18:--proxy/--resolve/--host/--interface 改变实际连接语义
        # (代理远端/地址重映射/主机头/本地绑定侧),固定探针口径保守拒绝,
        # 出现即整个命令不成立;--noproxy 禁止代理、保持直连语义,保留
        check(curl_call(g1_fixture_ac_events) == "CURL:MISSING",
              "--proxy 指向 127.0.0.2(URL 仍为 127.0.0.1、curl 实连 .2 "
              "超时 exit 28)不得满足直连锚定(连接语义参数保守拒绝,SP-18)")
        check(curl_call(g1_fixture_ad_events) == "CURL:MISSING",
              "--resolve 把 127.0.0.1:端口 重映射到 127.0.0.2(verbose 显示"
              "实际尝试 .2)不得满足直连锚定(连接语义参数保守拒绝,SP-18)")
        # SP-19:多 URL 命令的整次进程退出码+合并输出无法把失败归属到
        # 目标 URL——目标已返回 200/TARGET_SUCCESS、另一 URL 超时使
        # exit 28 也会被判「替身直连失败」;只接受恰好一个 URL 形态
        # 位置参数
        check(curl_call(g1_fixture_ae_events) == "CURL:MISSING",
              "目标 URL 已返回 200/TARGET_SUCCESS、另一 URL 超时使整进程 "
              "exit 28 的多 URL 命令不得判「替身直连失败」(单 URL 要求,"
              "SP-19)")
        check(curl_call(g1_fixture_af_events) == "CURL:OK",
              "单 URL 直连 127.0.0.1 真实失败的真对照仍必须锚定"
              "(收窄不误伤,SP-19 对照)")
        check(curl_call(g1_fixture_ag_events) == "CURL:OK",
              "userinfo 段携带凭证而解析后主机为 127.0.0.1 的真对照仍必须"
              "锚定(host 核验与参数收窄均不误伤,SP-15 口径保持)")

        # —— 1f)review7 SP-20~SP-23:短旗标/重定向/粘连短值/失败阶段 ——
        # SP-20:改变连接语义的短旗标(-x 代理/-K 配置文件)不得在带值
        # 短旗标白名单内被接纳后仅跳过值——URL 仍是 .1、curl 实连 .2
        # 失败(输出点名 127.0.0.2)不得满足直连锚定;同义长参数 --proxy
        # 已被 SP-18 拒绝,短参数同口径保守拒绝
        check(curl_call(g1_fixture_ah_events) == "CURL:MISSING",
              "-x 短旗标指向 127.0.0.2(URL 仍为 127.0.0.1、curl 实连 .2 "
              "超时 exit 28)不得满足直连锚定(改变连接语义的短旗标保守"
              "拒绝,SP-20)")
        check(curl_call(g1_fixture_ai_events) == "CURL:MISSING",
              "-K 配置文件内设同一代理(实连 .2 超时 exit 28)不得满足"
              "直连锚定(配置来源同口径保守拒绝,SP-20)")
        # SP-21:-L/--location 使 curl 跟随重定向,判据无法确认最终目标
        # 归属——.1 服务器记录 /redirect 命中并返回 302、curl 转向 .2
        # 连接失败(exit 28,.1 已被直连访问)不得满足直连锚定
        check(curl_call(g1_fixture_aj_events) == "CURL:MISSING",
              "-L 跟随 302 重定向后转向 127.0.0.2 连接失败(.1 已被直连"
              "访问、命中已记录)不得满足直连锚定(重定向旗标保守拒绝,"
              "SP-21)")
        check(curl_call(g1_fixture_ak_events) == "CURL:MISSING",
              "--location 跟随重定向的同义长参数形态同样不得满足直连"
              "锚定(重定向旗标保守拒绝,SP-21)")
        # SP-22:粘连短值 -m2 的值即 token 余部、只消费当前 token——
        # 实际 curl 把 2 当超时值、依次请求两个 URL(首 URL 真拿到 200/
        # TARGET_SUCCESS、次 URL 失败 exit 28),URL 计数须反映真实参数
        # 语义,不得把首 URL 当 -m2 的值吞掉而绕过单 URL 限制
        check(curl_call(g1_fixture_al_events) == "CURL:MISSING",
              "粘连短值 -m2 <成功URL> <失败URL>(首 URL 真拿到 200、次 "
              "URL 失败 exit 28)不得因首 URL 被当值吞掉而绕过单 URL "
              "限制(短旗标值按 curl 语义消费,SP-22)")
        # SP-23:连接已成功、响应阶段超时(200 + 15/25 字节后延迟,输出
        # Operation timed out … with 15 out of 25 bytes received)不能证明
        # 对替身的连接未被允许——失败证据须为连接阶段失败词族并绑定
        # 实际尝试主机
        check(curl_call(g1_fixture_am_events) == "CURL:MISSING",
              "连接已成功、响应阶段超时(200 + 15/25 字节后延迟)不得"
              "判「替身直连被拒」(连接阶段失败词族+实际尝试主机绑定,"
              "SP-23)")
        # 独立防护变体:-K 内 resolve 重映射 / -L 重定向回环跳,失败输出
        # 均点名 127.0.0.1——旗标白名单层的独立防护(主机绑定层对这两
        # 形态不能单独拒绝)仍须使其不成立
        check(curl_call(g1_fixture_an_events) == "CURL:MISSING",
              "-K 配置文件内 resolve 把 127.0.0.1:端口 重映射到 .2(失败"
              "输出点名 .1)不得满足直连锚定(配置来源保守拒绝的独立"
              "防护,SP-20 变体)")
        check(curl_call(g1_fixture_ao_events) == "CURL:MISSING",
              "-L 跟随 302 回环跳到 127.0.0.1 预留端口(初始 .1 已被直连"
              "访问、失败输出点名 .1)不得满足直连锚定(重定向保守拒绝"
              "的独立防护,SP-21 变体)")
        # ambient 处置 (a):任务专属 CURL_HOME/.curlrc 与子进程 http_proxy
        # 使实连 .2(事件不记录环境)——失败输出点名 127.0.0.2,连接阶段
        # 词族+实际尝试主机绑定使其不成立
        check(curl_call(g1_fixture_ap_events) == "CURL:MISSING",
              "任务专属 CURL_HOME/.curlrc 设代理使实连 .2(输出点名 .2)"
              "不得满足直连锚定(ambient 处置 (a):失败输出绑定实际尝试"
              "主机)")
        check(curl_call(g1_fixture_aq_events) == "CURL:MISSING",
              "子进程 http_proxy 使实连 .2(输出点名 .2)不得满足直连"
              "锚定(ambient 处置 (a):失败输出绑定实际尝试主机)")
        # 真对照:direct/correct-userinfo/two-shell-layers 收窄不误伤;
        # redirect-not-followed/separate-short-value-two-urls/
        # successful-target 维持 MISSING
        check(curl_call(g1_fixture_ar_events) == "CURL:OK",
              "单 URL 直连 127.0.0.1 真实失败的真对照仍必须锚定"
              "(收窄不误伤,review7 对照)")
        check(curl_call(g1_fixture_as_events) == "CURL:OK",
              "userinfo 段携带凭证而解析后主机为 127.0.0.1 的真对照仍必须"
              "锚定(收窄不误伤,review7 对照)")
        check(curl_call(g1_fixture_at_events) == "CURL:OK",
              "两层 shell 包装的 curl 真实失败仍必须锚定(既有剥壳上限"
              "内,review7 对照)")
        check(curl_call(g1_fixture_au_events) == "CURL:MISSING",
              "不跟随重定向(无 -L,302 即终态、exit 0)不构成连接被拒,"
              "保持 MISSING(review7 对照)")
        check(curl_call(g1_fixture_av_events) == "CURL:MISSING",
              "分离短值 -m 2 <成功URL> <失败URL> 的多 URL 命令保持 "
              "MISSING(单 URL 限制,review7 对照)")
        check(curl_call(g1_fixture_aw_events) == "CURL:MISSING",
              "成功完成的直连(exit 0)不构成连接被拒,保持 MISSING"
              "(review7 对照)")

        # —— 1g)review8 SP-24~SP-26:前缀按序验证/诊断来源/主机身份 ——
        # SP-24:短 token 禁用前缀(L/K)藏在带值字符前不得被跳过——
        # 首个带值字符之前每个字符须属无值白名单,否则整个命令不成立
        check(curl_call(g1_fixture_ax_events) == "CURL:MISSING",
              "-Lm2 跟随 302 重定向(.1 命中后转向预留端口、exit 28)不得"
              "因粘连值消费跳过禁用前缀 L 而满足直连锚定(短旗标按顺序"
              "验证,SP-24)")
        check(curl_call(g1_fixture_ay_events) == "CURL:MISSING",
              "-Lm 2 分离值形态同样不得因带值字符掩盖禁用前缀 L 而满足"
              "直连锚定(短旗标按顺序验证,SP-24)")
        check(curl_call(g1_fixture_az_events) == "CURL:MISSING",
              "-LsSm2 聚合形态不得因 sSm 合法无值/带值字符掩盖禁用前缀"
              " L 而满足直连锚定(短旗标按顺序验证,SP-24)")
        check(curl_call(g1_fixture_ba_events) == "CURL:MISSING",
              "-K路径 粘连配置旗标(路径含带值字符 m)不得因先找任意带值"
              "字符而跳过禁用前缀 K 满足直连锚定(短旗标按顺序验证,"
              "SP-24)")
        # SP-25:响应正文伪装连接诊断——200 + 正文 Failed to connect to
        # 127.0.0.1 + 响应阶段超时(31/41 字节已到达)不能证明连接未被
        # 允许;可接受证据须为 curl 诊断行形态
        check(curl_call(g1_fixture_bb_events) == "CURL:MISSING",
              "响应正文含连接失败措辞后响应阶段超时(部分字节已到达)"
              "不得判「替身直连被拒」(失败证据须区分连接阶段诊断与响"
              "应正文,SP-25)")
        # SP-26:主机子串冒充身份——失败诊断点名 127.0.0.10,不得因含
        # 子串 .1 而绑定替身
        check(curl_call(g1_fixture_bc_events) == "CURL:MISSING",
              "子进程 http_proxy 使实连 127.0.0.10(诊断行点名 .10)不得"
              "因主机子串包含 .1 而满足直连锚定(诊断行目标主机身份相"
              "等比较,SP-26)")
        # 对照:正常聚合/终结符/直连失败仍 OK;独立 -K/-L、歧义短值、
        # -U、普通正文超时、完整诊断正文、ambient .2 保持 MISSING
        check(curl_call(g1_fixture_bd_events) == "CURL:OK",
              "单 URL 直连 127.0.0.1 真实失败的真对照仍必须锚定"
              "(收窄不误伤,review8 对照)")
        check(curl_call(g1_fixture_be_events) == "CURL:OK",
              "正常聚合 -sSm2(前缀均属无值白名单、粘连值只消费当前"
              " token)仍必须锚定(按序验证不误伤,review8 对照)")
        check(curl_call(g1_fixture_bf_events) == "CURL:OK",
              "正常聚合 -sSm 2 分离值仍必须锚定(按序验证不误伤,"
              "review8 对照)")
        check(curl_call(g1_fixture_bg_events) == "CURL:OK",
              "-- 后单 URL 直连 127.0.0.1 真实失败仍必须锚定"
              "(终结符形态,review8 对照)")
        check(curl_call(g1_fixture_bh_events) == "CURL:MISSING",
              "独立 -K 配置文件旗标保持 MISSING(配置来源保守拒绝,"
              "review8 对照)")
        check(curl_call(g1_fixture_bi_events) == "CURL:MISSING",
              "独立 -L 重定向旗标保持 MISSING(重定向形态保守拒绝,"
              "review8 对照)")
        check(curl_call(g1_fixture_bj_events) == "CURL:MISSING",
              "歧义短值 -ms2 保持 MISSING(curl 报无效超时、review8"
              " 对照)")
        check(curl_call(g1_fixture_bk_events) == "CURL:MISSING",
              "-U 代理凭据短旗标保持 MISSING(代理域旗标宁严勿宽,"
              "review8 对照)")
        check(curl_call(g1_fixture_bl_events) == "CURL:MISSING",
              "普通正文后响应阶段超时保持 MISSING(无连接诊断行,"
              "review8 对照)")
        check(curl_call(g1_fixture_bm_events) == "CURL:MISSING",
              "相同诊断措辞正文完整成功(exit 0)保持 MISSING(未失败,"
              "review8 对照)")
        check(curl_call(g1_fixture_bn_events) == "CURL:MISSING",
              "子进程 http_proxy 使实连 127.0.0.2(诊断行点名 .2)保持"
              " MISSING(主机身份比较,review8 对照)")


        # —— 1h)review9 SP-27~SP-29:接纳表分类/重试拒绝/glob 拒绝 ——
        # SP-27 假绿:无值短旗标被当带值,吞掉首个(成功)URL
        check(curl_call(g1_fixture_bo_events) == "CURL:MISSING",
              "-g 后接成功 URL 与失败 URL 不得因把无值 globoff 当带值而"
              "只看到失败 URL 满足直连锚定(首请求已 200 命中,SP-27)")
        check(curl_call(g1_fixture_bp_events) == "CURL:MISSING",
              "-J 后接成功 URL 与失败 URL 不得因把无值 remote-header-name"
              "当带值而只看到失败 URL 满足直连锚定(SP-27)")
        check(curl_call(g1_fixture_bq_events) == "CURL:MISSING",
              "-sS -Z 后接成功 URL 与失败 URL 不得因把无值 parallel 当带"
              "值而只看到失败 URL 满足直连锚定(诊断已在行首,SP-27)")
        # SP-27 反向假阴性:合法无值短旗标+单失败 URL 应得 OK
        check(curl_call(g1_fixture_br_events) == "CURL:OK",
              "合法 -g <失败URL> 不得因把无值 globoff 当带值吞掉唯一 URL"
              "而判 MISSING(反向假阴性,SP-27)")
        check(curl_call(g1_fixture_bs_events) == "CURL:OK",
              "合法 -sS -Z <失败URL> 不得因把无值 parallel 当带值吞掉唯"
              "一 URL 而判 MISSING(反向假阴性,SP-27)")
        # SP-28:重试末次连接失败不得冒充从未连接
        check(curl_call(g1_fixture_bt_events) == "CURL:MISSING",
              "--retry 在 503+完整正文后关服、重试才连接失败,不得判「替"
              "身直连被拒」(连接已被允许,保守拒绝重试形态,SP-28)")
        # SP-29:单 URL 参数经花括号展开多请求
        check(curl_call(g1_fixture_bu_events) == "CURL:MISSING",
              "单参数花括号双端口 URL 不得因 len(urls)==1 且 hostname 为"
              " .1 而满足直连锚定(首请求已 200 命中,SP-29)")
        check(curl_call(g1_fixture_bv_events) == "CURL:MISSING",
              "-- 后同形花括号双端口 URL 同样不得满足直连锚定(SP-29)")
        # 对照:真直连/合法聚合/静默直连仍 OK;retry-closed-control 已披露
        # 翻转为 MISSING;其余拒绝形态保持 MISSING;full-diagnostic-body
        # 为 SP-25 已接受残余,产品维持 OK
        check(curl_call(g1_fixture_bw_events) == "CURL:OK",
              "单 URL 直连 127.0.0.1 真实失败的真对照仍必须锚定"
              "(收窄不误伤,review9 对照)")
        check(curl_call(g1_fixture_bx_events) == "CURL:OK",
              "正常聚合 -sSm2 仍必须锚定(接纳表分类不误伤,review9 对照)")
        check(curl_call(g1_fixture_by_events) == "CURL:OK",
              "-sS 静默直连失败仍必须锚定(parallel 补充对照,review9)")
        check(curl_call(g1_fixture_bz_events) == "CURL:MISSING",
              "--retry 加真失败 URL 的对照随重试保守拒绝翻转为 MISSING"
              "(已披露取舍,review9)")
        check(curl_call(g1_fixture_ca_events) == "CURL:MISSING",
              "--globoff 长旗标本不在白名单,花括号 URL 保持 MISSING"
              "(review9 对照)")
        check(curl_call(g1_fixture_cb_events) == "CURL:MISSING",
              "明文两 URL 保持 MISSING(多 URL 保守拒绝,review9 对照)")
        check(curl_call(g1_fixture_cc_events) == "CURL:MISSING",
              "混合前缀 -sLm2 保持 MISSING(禁用 L 按序验证,review9 对照)")
        check(curl_call(g1_fixture_cd_events) == "CURL:MISSING",
              "孤立 - 保持 MISSING(未知短旗标,review9 对照)")
        check(curl_call(g1_fixture_ce_events) == "CURL:MISSING",
              "-- 后附着选项形态保持 MISSING(review9 对照)")
        check(curl_call(g1_fixture_cf_events) == "CURL:MISSING",
              "小写 -lm2 保持 MISSING(前缀 l 非白名单,review9 对照)")
        check(curl_call(g1_fixture_cg_events) == "CURL:MISSING",
              "大写 -M2(curl --manual 转储)保持 MISSING(未知短旗标 M,"
              "review9 对照)")
        check(curl_call(g1_fixture_ch_events) == "CURL:MISSING",
              "--retry 后 503 再 200(exit 0)保持 MISSING(未失败,"
              "review9 对照)")
        check(curl_call(g1_fixture_ci_events) == "CURL:MISSING",
              "裸 -Z 两 URL(诊断行前带进度文字)保持 MISSING(行首正则/"
              "分类修正后亦因两 URL 拒绝,review9 对照)")
        check(curl_call(g1_fixture_cj_events) == "CURL:OK",
              "正文逐字节模拟完整诊断行后响应超时保持产品现状 OK"
              "(SP-25 已接受残余限制,本票不重开,review9 对照)")

        # —— 1i)review10 SP-30:上传文件名 glob 拒绝 ——
        check(curl_call(g1_fixture_ck_events) == "CURL:MISSING",
              "-T 分离值花括号双文件不得因单 URL 无 glob 字符而满足直连"
              "锚定(首次 PUT 已 200/18 字节,SP-30)")
        check(curl_call(g1_fixture_cl_events) == "CURL:MISSING",
              "--upload-file 分离值花括号双文件不得满足直连锚定"
              "(首次 PUT 已 200/18 字节,SP-30)")
        check(curl_call(g1_fixture_cm_events) == "CURL:MISSING",
              "短粘连 -T{a,b} 不得因粘连值未检查 glob 字符而满足直连"
              "锚定(SP-30,取值沿 SP-22)")
        check(curl_call(g1_fixture_cn_events) == "CURL:MISSING",
              "聚合 -sST{a,b} 不得因聚合内粘连值未检查 glob 字符而满足"
              "直连锚定(SP-30,取值沿 SP-22)")
        check(curl_call(g1_fixture_co_events) == "CURL:MISSING",
              "方括号范围 item[1-2].txt 不得满足直连锚定"
              "(首次 PUT /upload/item1.txt 已 200/18 字节,SP-30)")
        check(curl_call(g1_fixture_cp_events) == "CURL:MISSING",
              "-T 花括号双文件且 URL 在 -- 后,不得因既有 -- 后检查只看"
              "URL 而满足直连锚定(上传值仍展开多次 PUT,SP-30)")
        check(curl_call(g1_fixture_cq_events) == "CURL:MISSING",
              "-g 关闭上传 glob 因字面文件不存在保持 MISSING"
              "(行为不变,SP-30 对照)")
        check(curl_call(g1_fixture_cr_events) == "CURL:MISSING",
              "--upload-file={a,b} 长等号形态本就名单拒绝保持 MISSING"
              "(行为不变,SP-30 对照)")
        check(curl_call(g1_fixture_cs_events) == "CURL:OK",
              "普通单文件 -T 真失败对照仍必须锚定(精确守卫不误伤,"
              "SP-30)")
        check(curl_call(g1_fixture_ct_events) == "CURL:OK",
              "普通单文件 --upload-file 真失败对照仍必须锚定"
              "(精确守卫不误伤,SP-30)")

        # —— 2)对仓内留存验收证据重跑锚定判据:仍 PASS,不因加固翻案 ——

        r1_real = ev_dir / "r1-events.jsonl"
        if r1_real.is_file():
            for stage, target in (("role_scope", "docs/mygamestudio/PROJECT.md"),
                                  ("occupancy", "src/lock-probe.txt"),
                                  ("task_grant", "src/other.txt"),
                                  ("path", link)):
                check(anchor(r1_real, "mgs_write", stage, target, "write")
                      == judge.RESULT_OK,
                      f"留存 R1 证据重跑锚定判据仍 PASS(deny/{stage} → {target})")
        g1_real = ev_dir / "g1-events.jsonl"
        if g1_real.is_file():
            check(curl_call(g1_real) == "CURL:OK",
                  "留存 G1 证据重跑直连探针锚定仍 PASS")
            for target, action in (("01-harbor-timer", "update"),
                                   ("02-crane-sprite", "append-result")):
                check(anchor(g1_real, "mgs_remote", "task_grant",
                                  target, action) == judge.RESULT_OK,
                      f"留存 G1 证据重跑越界锚定仍 PASS"
                      f"(mgs_remote {action} deny → {target})")
        p1_real = ev_dir / "p1-events.jsonl"
        if p1_real.is_file():
            check(anchor(p1_real, "mgs_write", "role_scope|task_grant",
                              "docs/mygamestudio/GAME_DESIGN.md", "write")
                  == judge.RESULT_OK,
                  "留存 P1 证据重跑越界锚定仍 PASS")
        p2_real = ev_dir / "p2-events.jsonl"
        if p2_real.is_file():
            check(anchor(p2_real, "mgs_write", "role_scope|task_grant",
                              "docs/mygamestudio/GAME_DESIGN.md", "write")
                  == judge.RESULT_OK,
                  "留存 P2 证据重跑越界锚定仍 PASS")
        r1b_real = ev_dir / "r1b-events.jsonl"
        if r1b_real.is_file():
            check(anchor(r1b_real, "mgs_write", "identity", "src/stale.txt",
                              "write") == judge.RESULT_OK,
                  "留存 R1b 证据重跑 identity 锚定仍 PASS(调用侧绝对路径与"
                  "判据相对路径整段匹配)")

    # —— 3)run.sh 接线形态:探针行为判据锚定事件流,旧词串分支退场 ——

    check("|| grep -qF 'rule_stage" not in text,
          "R1 path 判据不应再保留对整个 JSONL 的任意词串 grep OR 分支(SP-6)")
    check('. "$ACC_DIR/evidence_adapter.sh"' in text,
          "run.sh 应以 source 接入 Shell 适配层(判据 module 的现场入口,票 08)")
    check('called = str(args.get("path")' not in text,
          "run.sh 不应再内联 mcp_deny_anchor 判据实现(应经共享 module,票 08)")
    for snippet, desc in (
        ('mcp_deny_anchor "$EVIDENCE_DIR/r1-events.jsonl" mgs_write path '
         '/tmp/mgs18-evil-link.md write',
         "R1 path 判据应以事件流 mcpToolCall 锚定接线并声明预期动作 write(SP-8)"),
        ('mcp_deny_anchor "$EVIDENCE_DIR/r1-events.jsonl" mgs_write role_scope '
         'docs/mygamestudio/PROJECT.md write',
         "R1 role_scope 判据应以事件流锚定接线并声明预期动作 write(SP-8)"),
        ('mcp_deny_anchor "$EVIDENCE_DIR/r1-events.jsonl" mgs_write occupancy '
         'src/lock-probe.txt write',
         "R1 occupancy 判据应以事件流锚定接线并声明预期动作 write(SP-8)"),
        ('mcp_deny_anchor "$EVIDENCE_DIR/r1-events.jsonl" mgs_write task_grant '
         'src/other.txt write',
         "R1 task_grant 判据应以事件流锚定接线并声明预期动作 write(SP-8)"),
        ('mcp_deny_anchor "$EVIDENCE_DIR/g1-events.jsonl" mgs_remote task_grant '
         '01-harbor-timer update',
         "G1 越界更新判据应以事件流锚定接线并声明预期动作 update(SP-8)"),
        ('mcp_deny_anchor "$EVIDENCE_DIR/g1-events.jsonl" mgs_remote task_grant '
         '02-crane-sprite append-result',
         "G1 越界评论判据应以事件流锚定接线并声明预期动作 append-result(SP-8)"),
        ('mcp_deny_anchor "$EVIDENCE_DIR/p1-events.jsonl" mgs_write '
         "'role_scope|task_grant' docs/mygamestudio/GAME_DESIGN.md write",
         "P1 越界判据应以事件流锚定接线并声明预期动作 write(SP-8)"),
        ('mcp_deny_anchor "$EVIDENCE_DIR/p2-events.jsonl" mgs_write '
         "'role_scope|task_grant' docs/mygamestudio/GAME_DESIGN.md write",
         "P2 越界判据应以事件流锚定接线并声明预期动作 write(SP-8)"),
        ('mcp_deny_anchor "$EVIDENCE_DIR/r1b-events.jsonl" mgs_write identity '
         'src/stale.txt write',
         "R1b identity 判据应以事件流锚定接线并声明预期动作 write(SP-8)"),
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

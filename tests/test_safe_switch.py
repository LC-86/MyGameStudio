#!/usr/bin/env python3
"""Issue #59 seams: user edits, same-name sources, and safe switch.

Confirmed seams (issue #59 acceptance + #49 T2 and T12):
- AC: verify actual source, version, user edits, conversion completeness,
  evidence reachability and preparation-period changes before switching
  current pointers and skill sources.
- AC: same-name skills keep one explicit valid source; applicable user
  edits migrate in; meaning conflicts wait for the developer; no silent
  overwrite or delete.
- AC: shared-client peers that are not ready keep a usable old
  environment; one converted project is not all-complete.
- AC: after switch the new version is the only current source; old
  originals stay read-only history; rollback first preserves post-switch
  additions and correspondence.
- AC: valid CONFIG and gate-history retirement stay separate; incomplete
  ops have a recovery destination; fixture checks are not real-environment
  migration authorization.
- T2: after switch a new session finds the expected skills with a unique
  same-name source; game entries and a Matt entry can read stage
  requirements.
- T12: preparation-period edits, user-edit conflicts, same-name sources,
  unready shared-client projects, partial migration and rollback: switch
  only after a complete check; keep originals and new-version additions.

Public seams: mgs_records.plan_safe_switch / apply_safe_switch /
read_safe_switch / rollback_safe_switch.

Expected values come from issues #59 and #49 D3/D9/D10, not internals.
Do not assert internal functions, directory counts, or prompt keywords.

    python3 -B tests/test_safe_switch.py
"""

from __future__ import annotations

import json
import shutil
import tempfile
from pathlib import Path

from records_backend_support import make_checker, run_theme
from test_github_material_migration import _write_old_github_project

import mgs_records  # noqa: E402

FAILURES, check = make_checker()

REPO_ROOT = Path(__file__).resolve().parents[1]
PLUGIN_SKILLS = REPO_ROOT / "plugin" / "skills"
STAGE_REL = "internal/game/stage-requirements.md"

USER_RULE = "只接金色星星"
CORE_PLAY_V2 = "玩家左右移动接住落下的金色星星。接到一颗得 1 分。漏接三次结束。"
RESULT_TEXT = "实际成果:src/player.js 左右移动。已执行验证:代码级检查通过。"
EVIDENCE_TEXT = "开发者试玩:移动跟手,可以进入跳跃。"
UNPUBLISHED_NOTE = "发布记录未知,不得宣称已发布。"
MISSING_EVIDENCE = "docs/mygamestudio/evidence/lost-playtest.md"
POST_SWITCH_TASK = "04-combo"
POST_SWITCH_GOAL = "切换后新增连击反馈"


def _write_tree(root: Path, files: dict[str, str]) -> None:
    for rel, text in files.items():
        path = root / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")


def _old_config(*, gate_line: bool = True) -> str:
    extra = ""
    if gate_line:
        extra = (
            "- 运行保障:mgs-gate MCP;角色令牌 producer-token;"
            "运行根 /tmp/mgs-runtime;策略 docs/mygamestudio/records/gate-policy.md\n"
        )
    return f"""# star-catcher:协作配置

维护责任:制作统筹。配置版本:v1。采用依据:旧版接入。

## 任务来源

- 后端:local-markdown
- 当前位置:docs/mygamestudio/work/
- 任务读取规则:本地 Markdown 后端约定
- 外部连接引用及已确认操作范围:无
{extra}
## 标签映射

| 语义 | 项目标签 |
| --- | --- |
| needs-triage | needs-triage |
| needs-info | needs-info |
| ready-for-agent | ready-for-agent |
| ready-for-human | ready-for-human |
| wontfix | wontfix |

## 文档映射

| 内容 | 当前权威位置 | 维护角色 |
| --- | --- | --- |
| 项目目标与范围 | docs/mygamestudio/PROJECT.md | 制作统筹 |
| 游戏需求与设计 | docs/mygamestudio/GAME_DESIGN.md | 方案设计 |
| 技术设计 | docs/mygamestudio/TECH_DESIGN.md | 制作实现 |
| 术语、ADR 与历史 | docs/mygamestudio/records/ | 对应专业角色 |
| 成果与证据 | docs/mygamestudio/evidence/ | 对应执行者 |

## 执行条件

- 工程、原型、资源与构建入口:src/
- 可用能力及已验证执行边界:文件读写
- 尚未就绪的能力及影响:无
"""


def _write_old_local_project(root: Path) -> Path:
    _write_tree(root, {
        "README.md": "# star-catcher\n\n接星星技术夹具,不是真实个人项目。\n",
        "src/main.js": "console.log('catch');\n",
        "docs/mygamestudio/CONFIG.md": _old_config(),
        "docs/mygamestudio/INDEX.md": (
            "# star-catcher:资料入口\n\n"
            "| 读取条件 | 当前资料位置 |\n| --- | --- |\n"
            "| 讨论玩法 | docs/mygamestudio/GAME_DESIGN.md |\n"
            "| 接手工作 | docs/mygamestudio/work |\n"
        ),
        "docs/mygamestudio/PROJECT.md": "# star-catcher:项目约定\n\n最小接星闭环。\n",
        "docs/mygamestudio/GAME_DESIGN.md": f"""# star-catcher：当前游戏需求与设计

维护责任：方案设计。基线版本：v2。适用范围：最小闭环。采用依据：records/decision-adopted.md。

## 玩家体验与需求

{CORE_PLAY_V2}

## 当前规则与流程

- 得分：每颗金色星星 1 分。
- 结束：漏接 3 颗后本局结束。
- 操作：方向键左右移动。

## 用户补充

{USER_RULE}

## 验证与未决项

- 移动已有结果。跳跃手感未验证。
""",
        "docs/mygamestudio/TECH_DESIGN.md": "# 技术约定\n\n纯 HTML/JS。源码在 src/。\n",
        "docs/mygamestudio/records/GAME_DESIGN-v1.md": (
            "# 历史规格 v1\n\n玩家左右移动接住落下的星星。\n"
        ),
        "docs/mygamestudio/records/decision-adopted.md": (
            "# 核心循环:接星星\n\n状态:已采纳。日期:2026-09-05。\n"
        ),
        "docs/mygamestudio/records/decision-pending.md": (
            "# 是否加入连击\n\n状态:未决。日期:2026-09-06。\n"
        ),
        "docs/mygamestudio/records/gate-policy.md": (
            "# 旧 gate 策略\n\n角色令牌与运行根仅作历史。不得当作新版权限。\n"
        ),
        "docs/mygamestudio/records/recovery/pending-ops.json": json.dumps({
            "ops": [{"op": "write", "identity": "02-jump", "status": "unknown"}],
            "note": "待恢复:写入结果未知",
        }, ensure_ascii=False, indent=2) + "\n",
        "docs/mygamestudio/work/01-move/task.md": """# 玩家移动

任务身份:01-move。当前分流:ready-for-agent。进度:已完成。认领:maker。关闭原因:完成。

## 工作请求

- 当前目标:实现左右移动
- 输入与基线:GAME_DESIGN v2
- 本次交付:src/player.js 移动
- 允许修改范围:src/**
- 所需能力:文件读写
- 完成标准:方向键可移动
- 执行责任:Agent(制作实现)
- 验收方式:代码级检查
- 依赖:无
- 父任务:无

## 结果索引

- results/2026-09-06.md
- docs/mygamestudio/evidence/playtest-20260906.md
""",
        "docs/mygamestudio/work/01-move/results/2026-09-06.md": (
            f"# 移动结果\n\n任务:01-move。{RESULT_TEXT}\n"
        ),
        "docs/mygamestudio/work/02-jump/task.md": """# 跳跃

任务身份:02-jump。当前分流:ready-for-agent。进度:待执行。认领:未认领。关闭原因:无。

## 工作请求

- 当前目标:加入跳跃
- 输入与基线:GAME_DESIGN v2
- 本次交付:空格跳跃
- 允许修改范围:src/**
- 所需能力:文件读写
- 完成标准:空格可跳
- 执行责任:Agent(制作实现)
- 验收方式:代码级检查
- 依赖:01-move
- 父任务:01-move
""",
        "docs/mygamestudio/work/03-score/task.md": f"""# 计分板

任务身份:03-score。当前分流:needs-info。进度:待执行。认领:未认领。关闭原因:无。

## 工作请求

- 当前目标:显示分数
- 输入与基线:GAME_DESIGN v2
- 本次交付:分数显示
- 允许修改范围:src/**
- 所需能力:文件读写
- 完成标准:接到星星分数+1
- 执行责任:Agent(制作实现)
- 验收方式:代码级检查
- 依赖:01-move
- 父任务:无

## 结果索引

- {MISSING_EVIDENCE}
- 发布记录:未知。{UNPUBLISHED_NOTE}
""",
        "docs/mygamestudio/evidence/playtest-20260906.md": (
            f"# 试玩记录\n\n任务:01-move。{EVIDENCE_TEXT}\n"
        ),
    })
    return root


def _convert_local(root: Path) -> dict:
    return mgs_records.apply_local_material_migration(
        root, mgs_records.plan_local_material_migration(root), confirmed=True)


def _copy_skill(name: str, dest_root: Path) -> None:
    src = PLUGIN_SKILLS / name
    dest = dest_root / name
    shutil.copytree(src, dest)


def _write_isolated_client(home: Path, *, names: tuple[str, ...] = (
        "game-producer", "game-init", "tdd", "implement")) -> Path:
    skills = home / "skills"
    skills.mkdir(parents=True, exist_ok=True)
    for name in names:
        _copy_skill(name, skills)
    internal = home / "internal" / "game"
    internal.mkdir(parents=True, exist_ok=True)
    src_stage = REPO_ROOT / "plugin" / STAGE_REL
    shutil.copy2(src_stage, internal / "stage-requirements.md")
    src_inv = REPO_ROOT / "plugin" / "internal" / "game" / "invocation.md"
    shutil.copy2(src_inv, internal / "invocation.md")
    return skills


def _discovered_names(skills_root: Path) -> list[str]:
    if not skills_root.is_dir():
        return []
    return sorted(path.name for path in skills_root.iterdir()
                  if path.is_dir() and (path / "SKILL.md").is_file())


def _skill_sources(home: Path) -> dict[str, list[str]]:
    found: dict[str, list[str]] = {}
    for root in (home / "skills", home / "skills-history",
                 home / "plugins" / "mygamestudio" / "skills"):
        if not root.is_dir():
            continue
        for path in root.iterdir():
            if path.is_dir() and (path / "SKILL.md").is_file():
                found.setdefault(path.name, []).append(
                    str(path.relative_to(home)))
    return found


def _history_design(root: Path) -> str:
    history = root / "docs/mygamestudio/records/readonly-history"
    candidates = [
        history / "GAME_DESIGN.md",
        history / "docs/mygamestudio/GAME_DESIGN.md",
        root / "docs/mygamestudio/records/readonly-history/GAME_DESIGN.md",
    ]
    for path in candidates:
        if path.is_file():
            return path.read_text(encoding="utf-8")
    blob = ""
    if history.is_dir():
        for path in history.rglob("GAME_DESIGN.md"):
            blob += path.read_text(encoding="utf-8")
    return blob


def test_incomplete_and_unconfirmed_do_not_switch() -> None:
    """AC1/T12: 核对未通过或未确认时不得切换现行指针;计划只读。"""

    with tempfile.TemporaryDirectory() as tmp:
        root = _write_old_local_project(Path(tmp) / "star-catcher")
        old_design = (root / "docs/mygamestudio/GAME_DESIGN.md").read_text(
            encoding="utf-8")
        plan = mgs_records.plan_safe_switch(root)
        check(plan.get("wrote") is False, "切换计划必须只读")
        check(plan.get("ready") is not True,
              "未完成资料转换时不得报告可以切换")
        check(plan.get("gate_required") is False, "普通切换路径不得依赖 gate")
        check(plan.get("real_migration_authorized") is False,
              "功能实现不得当作已获真实环境迁移授权")
        live = mgs_records.read_current_design(root)
        check("规格身份:overall" not in (live.get("overall") or ""),
              "计划阶段不得把待切换规格当作现行来源")
        unconfirmed = mgs_records.apply_safe_switch(
            root, plan, confirmed=False)
        check(unconfirmed.get("wrote") is False, "未确认不得切换")
        check((root / "docs/mygamestudio/GAME_DESIGN.md").read_text(
            encoding="utf-8") == old_design, "未确认不得改现行原件")


def test_complete_check_then_switch_makes_new_current() -> None:
    """AC1/AC4/AC5/T12: 核对来源、版本、用户修改、完整性、证据和准备期变更
    通过后才切换;新版成为唯一现行来源;旧原件只读历史;有效配置与 gate
    退役分开;未完成操作有恢复去向。
    """

    with tempfile.TemporaryDirectory() as tmp:
        root = _write_old_local_project(Path(tmp) / "star-catcher")
        old_design = (root / "docs/mygamestudio/GAME_DESIGN.md").read_text(
            encoding="utf-8")
        converted = _convert_local(root)
        check(converted.get("status") == "pending-switch",
              "本票依赖前序待切换成果,不得重做转换器")
        before_switch = mgs_records.read_current_design(root)
        check("规格身份:overall" not in (before_switch.get("overall") or ""),
              "切换前现行设计仍应是旧来源")
        plan = mgs_records.plan_safe_switch(root)
        checks = plan.get("checks") or {}
        for key in ("source", "version", "user_edits", "conversion_complete",
                    "evidence_reachable", "preparation_changes"):
            check(checks.get(key) is True,
                  f"完整核对必须包含通过的 {key},实际 {checks}")
        check(plan.get("ready") is True, f"完整待切换应可切换:{plan}")
        check(plan.get("real_migration_authorized") is False,
              "夹具核对通过不是真实环境迁移授权")
        check(plan.get("recovery_destination"),
              "未完成操作必须有明确恢复去向")
        applied = mgs_records.apply_safe_switch(root, plan, confirmed=True)
        check(applied.get("ok") is True, f"核对通过且确认后应切换:{applied}")
        check(applied.get("status") == "switched",
              f"切换后状态应为 switched,实际 {applied.get('status')}")
        check(applied.get("gate_required") is False
              and applied.get("gate_as_permission") is False,
              "gate 历史不得变成新版权限")
        live = mgs_records.read_current_design(root)
        overall = live.get("overall") or ""
        check("规格身份:overall" in overall,
              "切换后新版规格必须是唯一现行来源")
        check(CORE_PLAY_V2 in overall and USER_RULE in overall,
              "现行规格必须包含转换后的设计与适用用户修改")
        check((root / "docs/mygamestudio/GAME_DESIGN.md").read_text(
            encoding="utf-8") == overall
              or overall == live.get("overall"),
              "现行读取必须指向已切换资料")
        history = _history_design(root)
        check(old_design in history or (
            CORE_PLAY_V2 in history and "规格身份:overall" not in history),
              "旧原件必须作为只读历史保留,不得删除")
        config = mgs_records.load_config(root)
        check(config["backend"] == "local-markdown",
              "有效配置必须转入新版本地 tracker 含义")
        cfg_text = (root / "docs/mygamestudio/CONFIG.md").read_text(
            encoding="utf-8")
        check("mgs-gate" not in cfg_text and "producer-token" not in cfg_text,
              "现行配置不得再把 gate 令牌写成权限")
        check("pending-switch" not in cfg_text,
              "切换后现行配置不得仍自称待切换")
        report = mgs_records.read_safe_switch(root)
        check(report.get("status") == "switched", "回读状态必须是已切换")
        check(report.get("gate_as_permission") is False,
              "回读不得把 gate 历史当作新版权限")
        check(report.get("recovery_destination"),
              "回读仍须给出未完成操作的恢复去向")
        gate_history = (
            root / "docs/mygamestudio/records/gate-history.md")
        staging_gate = (
            Path(converted.get("pending_root") or "")
            / "docs/mygamestudio/records/gate-history.md")
        check(gate_history.is_file() or staging_gate.is_file(),
              "gate 历史必须单独留存,与有效配置分开")
        tasks = {task["identity"] for task in mgs_records.list_tasks(root)}
        check("01-move" in tasks, "切换后现行任务应来自新版资料")


def test_same_name_skill_unique_source_and_stage_reads() -> None:
    """AC2/T2/T12: 同名技能只保留一个明确有效来源;适用用户修改迁入;
    含义冲突交开发者决定,不静默覆盖或删除。切换后游戏入口和 Matt 入口
    仍能读取阶段要求。
    """

    with tempfile.TemporaryDirectory() as tmp:
        ready = _write_old_local_project(Path(tmp) / "ready-game")
        _convert_local(ready)
        home = Path(tmp) / "isolated-codex"
        skills = _write_isolated_client(home)
        compatible = (skills / "implement" / "SKILL.md")
        compatible.write_text(
            compatible.read_text(encoding="utf-8")
            + "\n## 用户修改\n\n适用:只接金色星星。\n",
            encoding="utf-8")
        conflict = skills / "tdd" / "SKILL.md"
        conflict.write_text(
            "---\nname: tdd\ndescription: user fork\n---\n\n"
            "# Never write a failing test first\n\n"
            "含义与正式 TDD 相反,必须交开发者决定。\n",
            encoding="utf-8")
        package = Path(tmp) / "package-skills"
        shutil.copytree(PLUGIN_SKILLS, package)
        internal = Path(tmp) / "package-internal"
        shutil.copytree(REPO_ROOT / "plugin" / "internal" / "game",
                        internal / "game")
        plan = mgs_records.plan_safe_switch(
            ready, client_home=home, package_root=package)
        applied = mgs_records.apply_safe_switch(ready, plan, confirmed=True)
        check(applied.get("ok") is True, f"项目切换应成功:{applied}")
        names = _discovered_names(home / "skills")
        check(len(names) == len(set(names)), f"同名技能必须唯一,实际 {names}")
        sources = _skill_sources(home)
        for name, locs in sources.items():
            current = [item for item in locs if item.startswith("skills/")]
            check(len(current) <= 1,
                  f"{name} 现行来源必须唯一,实际 {current}")
        implement = (home / "skills" / "implement" / "SKILL.md").read_text(
            encoding="utf-8")
        check("只接金色星星" in implement,
              "适用用户修改必须迁入唯一有效来源")
        tdd_text = (home / "skills" / "tdd" / "SKILL.md").read_text(
            encoding="utf-8")
        check("Never write a failing test first" in tdd_text,
              "含义冲突不得静默覆盖用户技能")
        check(any("tdd" in str(item) for item in (applied.get("paused") or [])
                  or (applied.get("developer_decisions") or [])),
              f"含义冲突必须交开发者决定,实际 {applied}")
        history_tdd = home / "skills-history" / "tdd" / "SKILL.md"
        check(not history_tdd.is_file() or "Never write a failing test first"
              in history_tdd.read_text(encoding="utf-8")
              or (home / "skills" / "tdd").is_dir(),
              "冲突技能不得被删除")
        producer = home / "skills" / "game-producer" / "SKILL.md"
        tdd = home / "skills" / "tdd" / "SKILL.md"
        pointer = "../../internal/game/stage-requirements.md"
        for skill_md in (producer, tdd):
            check(skill_md.is_file(), f"切换后必须能发现 {skill_md.name}")
            text = skill_md.read_text(encoding="utf-8")
            check(pointer in text or "stage-requirements.md" in text,
                  f"{skill_md.parent.name} 必须仍指向阶段资料")
            resolved = (skill_md.parent / pointer).resolve()
            check(resolved.is_file(),
                  f"{skill_md.parent.name} 切换后必须仍能读取阶段要求")


def test_skill_switch_keeps_ordinary_user_edits_or_pauses() -> None:
    """AC2: 普通正文追加与自建附件必须保留;无法安全合并时暂停该技能切换。"""

    with tempfile.TemporaryDirectory() as tmp:
        ready = _write_old_local_project(Path(tmp) / "ready-game")
        _convert_local(ready)
        home = Path(tmp) / "isolated-codex"
        skills = _write_isolated_client(home)
        implement = skills / "implement" / "SKILL.md"
        implement.write_text(
            implement.read_text(encoding="utf-8")
            + "\n本项目约定:只接金色星星,不接红色星星。\n",
            encoding="utf-8")
        note = skills / "implement" / "notes" / "project-rule.md"
        note.parent.mkdir(parents=True, exist_ok=True)
        note.write_text("自建附件:金色星星判定口径。\n", encoding="utf-8")
        package = Path(tmp) / "package-skills"
        shutil.copytree(PLUGIN_SKILLS, package)
        plan = mgs_records.plan_safe_switch(
            ready, client_home=home, package_root=package)
        applied = mgs_records.apply_safe_switch(ready, plan, confirmed=True)
        live = home / "skills" / "implement" / "SKILL.md"
        live_text = live.read_text(encoding="utf-8") if live.is_file() else ""
        live_note = home / "skills" / "implement" / "notes" / "project-rule.md"
        paused = [str(item) for item in (applied.get("paused") or [])]
        kept_body = "只接金色星星" in live_text
        kept_note = live_note.is_file() and "金色星星判定口径" in live_note.read_text(
            encoding="utf-8")
        if "implement" in paused:
            check(kept_body and kept_note,
                  "无法安全合并时必须暂停该技能并保留用户正文与附件")
        else:
            check(kept_body, "适用的正文追加必须迁入唯一有效来源,不得只进历史目录")
            check(kept_note, "自建附件必须留在活动技能来源中")


def test_later_skill_extras_survive_second_project_switch() -> None:
    """AC2: 技能历史目录已存在时,当前树里后加的用户附件仍须保留。"""

    with tempfile.TemporaryDirectory() as tmp:
        first = _write_old_local_project(Path(tmp) / "game-a")
        second = _write_old_local_project(Path(tmp) / "game-b")
        _convert_local(first)
        _convert_local(second)
        home = Path(tmp) / "isolated-codex"
        skills = _write_isolated_client(home)
        first_note = skills / "implement" / "notes" / "first-rule.md"
        first_note.parent.mkdir(parents=True, exist_ok=True)
        first_note.write_text("第一次切换前的附件\n", encoding="utf-8")
        package = Path(tmp) / "package-skills"
        shutil.copytree(PLUGIN_SKILLS, package)
        mgs_records.apply_safe_switch(
            first, mgs_records.plan_safe_switch(
                first, client_home=home, package_root=package),
            confirmed=True)
        later = home / "skills" / "implement" / "notes" / "second-rule.md"
        later.parent.mkdir(parents=True, exist_ok=True)
        later.write_text("第二次切换前新增的附件\n", encoding="utf-8")
        applied = mgs_records.apply_safe_switch(
            second, mgs_records.plan_safe_switch(
                second, client_home=home, package_root=package),
            confirmed=True)
        live = home / "skills" / "implement" / "notes" / "second-rule.md"
        paused = [str(item) for item in (applied.get("paused") or [])]
        kept = live.is_file() and "第二次切换前新增的附件" in live.read_text(
            encoding="utf-8")
        if "implement" in paused:
            check(kept, "暂停切换时必须保留后加的用户附件")
        else:
            check(kept, "历史目录已存在时不得删掉当前树后加的用户附件")


def test_shared_client_unready_keeps_old_environment() -> None:
    """AC3/T12: 共用客户端未就绪项目保留可用旧环境;
    不能仅因某个项目转换完成就宣称全部完成。
    """

    with tempfile.TemporaryDirectory() as tmp:
        ready = _write_old_local_project(Path(tmp) / "ready-game")
        unready = _write_old_local_project(Path(tmp) / "unready-game")
        _convert_local(ready)
        home = Path(tmp) / "isolated-codex"
        _write_isolated_client(home, names=("game-producer", "tdd"))
        old_unready_cfg = (unready / "docs/mygamestudio/CONFIG.md").read_text(
            encoding="utf-8")
        old_skill = (home / "skills" / "tdd" / "SKILL.md").read_text(
            encoding="utf-8")
        plan = mgs_records.plan_safe_switch(
            ready, client_home=home, peer_projects=[unready])
        applied = mgs_records.apply_safe_switch(ready, plan, confirmed=True)
        check(applied.get("ok") is True, "就绪项目仍应完成自身切换")
        check(applied.get("client_complete") is not True,
              "不得因单个项目转换完成就宣称客户端全部完成")
        unready_listed = applied.get("unready_projects") or []
        check(any(str(unready) in str(item) or "unready-game" in str(item)
                  for item in unready_listed),
              f"必须标明未就绪项目,实际 {unready_listed}")
        check((unready / "docs/mygamestudio/CONFIG.md").read_text(
            encoding="utf-8") == old_unready_cfg,
              "未就绪项目现行配置必须保持可用旧环境")
        check("规格身份:overall" not in mgs_records.read_current_design(
            unready).get("overall", ""),
              "未就绪项目不得被连带切换")
        check((home / "skills" / "tdd" / "SKILL.md").read_text(
            encoding="utf-8") == old_skill,
              "共用客户端未就绪时不得换掉旧技能环境")
        live = mgs_records.read_current_design(ready)
        check("规格身份:overall" in (live.get("overall") or ""),
              "就绪项目自身仍应切换到新版现行来源")


def test_requested_client_missing_is_not_complete() -> None:
    """请求了客户端切换但目录不存在时,不得宣称 client_complete。"""

    with tempfile.TemporaryDirectory() as tmp:
        ready = _write_old_local_project(Path(tmp) / "ready-game")
        _convert_local(ready)
        missing_home = Path(tmp) / "missing-client"
        package = REPO_ROOT / "plugin"
        plan = mgs_records.plan_safe_switch(
            ready, client_home=missing_home, package_root=package)
        applied = mgs_records.apply_safe_switch(ready, plan, confirmed=True)
        check(applied.get("ok") is True, f"项目自身仍应完成切换:{applied}")
        check(applied.get("client_complete") is not True,
              f"客户端未切换成功不得宣称完成:{applied}")


def test_rollback_preserves_new_additions() -> None:
    """AC4/T12: 回退先保留新版新增内容与对应关系,避免旧快照覆盖新成果。"""

    with tempfile.TemporaryDirectory() as tmp:
        root = _write_old_local_project(Path(tmp) / "star-catcher")
        _convert_local(root)
        plan = mgs_records.plan_safe_switch(root)
        mgs_records.apply_safe_switch(root, plan, confirmed=True)
        mgs_records.create_task(
            root, POST_SWITCH_TASK, "连击",
            {"当前目标": POST_SWITCH_GOAL,
             "输入与基线": "GAME_DESIGN v2",
             "本次交付": "切换后新增成果",
             "允许修改范围": "src/**",
             "所需能力": "文件读写",
             "完成标准": "记录可回读",
             "执行责任": "Agent(制作实现)",
             "验收方式": "代码级检查",
             "依赖": "01-move"})
        rolled = mgs_records.rollback_safe_switch(root, plan, confirmed=True)
        check(rolled.get("ok") is True, f"确认后应能回退:{rolled}")
        live = mgs_records.read_current_design(root)
        check("规格身份:overall" not in (live.get("overall") or ""),
              "回退后现行指针应回到旧原件")
        check(CORE_PLAY_V2 in (live.get("overall") or ""),
              "回退后旧设计仍可读")
        preserved = rolled.get("preserved") or []
        check(any(POST_SWITCH_TASK in str(item) for item in preserved)
              or (root / "docs/mygamestudio/records/preserved-after-rollback"
                  / f"{POST_SWITCH_TASK}").exists()
              or any(task.get("identity") == POST_SWITCH_TASK
                     for task in mgs_records.list_tasks(root)),
              "回退必须先保留新版新增任务,不得被迁移前快照覆盖")
        report = mgs_records.read_safe_switch(root)
        check(report.get("correspondence"),
              "回退必须保留新旧对应关系")
        check(report.get("status") in ("rolled-back", "pending-switch"),
              f"回退后状态应可恢复,实际 {report.get('status')}")


def test_rollback_preserves_edits_to_migrated_tasks() -> None:
    """AC4: 回退覆盖旧快照前,必须保留既有已迁移任务的新修改。"""

    with tempfile.TemporaryDirectory() as tmp:
        root = _write_old_local_project(Path(tmp) / "star-catcher")
        _convert_local(root)
        plan = mgs_records.plan_safe_switch(root)
        mgs_records.apply_safe_switch(root, plan, confirmed=True)
        new_goal = "加入带缓冲的跳跃手感"
        mgs_records.update_task(
            root, "02-jump", {"当前目标": new_goal},
            change_note="切换后修改既有任务")
        rolled = mgs_records.rollback_safe_switch(root, plan, confirmed=True)
        check(rolled.get("ok") is True, f"确认后应能回退:{rolled}")
        preserved_blob = ""
        preserve = root / "docs/mygamestudio/records/preserved-after-rollback"
        if preserve.is_dir():
            for path in preserve.rglob("*"):
                if path.is_file():
                    preserved_blob += path.read_text(encoding="utf-8")
        project_blob = ""
        for path in root.rglob("*"):
            if path.is_file():
                try:
                    project_blob += path.read_text(encoding="utf-8")
                except UnicodeDecodeError:
                    continue
        check(new_goal in preserved_blob or new_goal in project_blob,
              "既有任务在切换后的新目标必须留下保留副本,不得被迁移前快照抹掉")


def test_prep_change_and_partial_do_not_switch() -> None:
    """AC1/AC5/T12: 准备期间新增修改与部分迁移不得切换。"""

    with tempfile.TemporaryDirectory() as tmp:
        root = _write_old_local_project(Path(tmp) / "star-catcher")
        plan_convert = mgs_records.plan_local_material_migration(root)
        (root / "docs/mygamestudio/work/02-jump/task.md").write_text(
            (root / "docs/mygamestudio/work/02-jump/task.md").read_text(
                encoding="utf-8").replace("加入跳跃", "加入二段跳(准备期间新增)"),
            encoding="utf-8")
        partial = mgs_records.apply_local_material_migration(
            root, plan_convert, confirmed=True)
        check(partial.get("paused"), "本用例需要准备期间冲突留下暂停项")
        plan = mgs_records.plan_safe_switch(root)
        check(plan.get("ready") is not True,
              "部分迁移或准备期间变更不得报告可以切换")
        applied = mgs_records.apply_safe_switch(root, plan, confirmed=True)
        check(applied.get("wrote") is False, "核对未通过不得切换")
        check("规格身份:overall" not in mgs_records.read_current_design(
            root).get("overall", ""),
              "部分迁移后现行来源必须仍是旧原件")

        complete = _write_old_local_project(Path(tmp) / "complete-then-edit")
        _convert_local(complete)
        switch_plan = mgs_records.plan_safe_switch(complete)
        (complete / "docs/mygamestudio/GAME_DESIGN.md").write_text(
            (complete / "docs/mygamestudio/GAME_DESIGN.md").read_text(
                encoding="utf-8") + "\n准备期间又改了现行规格。\n",
            encoding="utf-8")
        blocked = mgs_records.apply_safe_switch(
            complete, switch_plan, confirmed=True)
        check(blocked.get("wrote") is False,
              "准备期间新增修改必须阻止切换")
        check("规格身份:overall" not in mgs_records.read_current_design(
            complete).get("overall", ""),
              "来源变化后不得切换现行指针")


def test_deleted_source_during_prep_blocks_switch() -> None:
    """AC1/T12: 准备期间删除已指纹来源必须阻止切换,不能当没变化。"""

    with tempfile.TemporaryDirectory() as tmp:
        root = _write_old_local_project(Path(tmp) / "deleted-source")
        _convert_local(root)
        plan = mgs_records.plan_safe_switch(root)
        check(plan.get("ready") is True, f"转换完整后应可切换:{plan}")
        (root / "docs/mygamestudio/GAME_DESIGN.md").unlink()
        blocked = mgs_records.apply_safe_switch(root, plan, confirmed=True)
        check(blocked.get("ok") is not True,
              f"删除来源后不得切换,实际 {blocked}")
        check(blocked.get("wrote") is not True, "准备期间删除必须挡住写入")
        check("规格身份:overall" not in mgs_records.read_current_design(
            root).get("overall", ""),
              "删除来源后现行指针必须仍是旧原件")


def test_github_switch_makes_new_current_and_can_roll_back() -> None:
    """AC1/AC4: GitHub 待切换在核对通过后成为唯一现行来源;
    旧 Issue 为只读历史;回退保留对应关系。
    """

    with tempfile.TemporaryDirectory() as tmp:
        root, fake = _write_old_github_project(Path(tmp) / "gh-game")
        converted = mgs_records.apply_github_material_migration(
            root, mgs_records.plan_github_material_migration(
                root, transport=fake),
            confirmed=True, transport=fake)
        check(converted.get("status") == "pending-switch",
              "GitHub 转换成果必须先待切换")
        before = mgs_records.read_current_design(root, transport=fake)
        check("规格身份:overall" not in (before.get("overall") or ""),
              "切换前现行 GitHub 设计不得是待切换成果")
        plan = mgs_records.plan_safe_switch(root, transport=fake)
        check(plan.get("ready") is True, f"完整 GitHub 待切换应可切换:{plan}")
        applied = mgs_records.apply_safe_switch(
            root, plan, confirmed=True, transport=fake)
        check(applied.get("ok") is True, f"GitHub 切换应成功:{applied}")
        live = mgs_records.read_current_design(root, transport=fake)
        check("规格身份:overall" in (live.get("overall") or ""),
              "切换后新版 GitHub 规格必须是唯一现行来源")
        check(CORE_PLAY_V2 in (live.get("overall") or "")
              and USER_RULE in (live.get("overall") or ""),
              "现行规格必须包含转换后的设计与用户修改")
        tasks = {task["identity"]: task
                 for task in mgs_records.list_tasks(root, transport=fake)}
        check("01-move" in tasks, "切换后现行任务应来自新 Issue")
        old_bodies = [item.get("body") or "" for item in fake.issues]
        check(any("迁移状态:readonly-history" in body for body in old_bodies),
              "旧 GitHub 原件必须标为只读历史")
        check("迁移状态:pending-switch" not in (live.get("overall") or ""),
              "现行规格不得仍标待切换")
        cfg = (root / "docs/mygamestudio/CONFIG.md").read_text(encoding="utf-8")
        check("pending-switch" not in cfg and "mgs-gate" not in cfg,
              "GitHub 现行配置切换后不得自称待切换或带 gate 权限")
        rolled = mgs_records.rollback_safe_switch(
            root, plan, confirmed=True, transport=fake)
        check(rolled.get("ok") is True, f"GitHub 回退应成功:{rolled}")
        check(rolled.get("correspondence"), "回退必须保留对应关系")
        after = mgs_records.read_current_design(root, transport=fake)
        check("规格身份:overall" not in (after.get("overall") or ""),
              "回退后不得把新版规格当作现行来源")


def test_stale_ready_plan_rechecked_before_promotion() -> None:
    """确认后待切换成果被删改时,旧就绪清单不得替代提升前重算。"""

    with tempfile.TemporaryDirectory() as tmp:
        root = _write_old_local_project(Path(tmp) / "star-catcher")
        _convert_local(root)
        plan = mgs_records.plan_safe_switch(root)
        check(plan.get("ready") is True, f"前置:转换完成应可切换:{plan}")
        # 清单返回 ready 之后、确认提升之前,待切换成果被删改。
        design_new = (root / "docs/mygamestudio/records/pending-switch"
                      / "docs/mygamestudio/GAME_DESIGN.md")
        check(design_new.is_file(), f"前置:应存在待切换规格 {design_new}")
        design_new.unlink()
        old_design = (root / "docs/mygamestudio/GAME_DESIGN.md").read_text(
            encoding="utf-8")
        applied = mgs_records.apply_safe_switch(root, plan, confirmed=True)
        check(applied.get("ok") is False,
              f"待切换成果缺失时不得按旧清单宣称切换成功:{applied}")
        reason = str(applied.get("reason") or "")
        check("重新核对未通过" in reason or "对应关系发生变化" in reason,
              f"必须说明是确认后状态变化:{reason}")
        check((root / "docs/mygamestudio/GAME_DESIGN.md").read_text(
            encoding="utf-8") == old_design, "旧现行原件必须保持未切换")


def test_github_marker_failure_is_not_reported_switched() -> None:
    """远端标记 PATCH 失败时不得在本地宣告 switched:
    switch-status 不落盘,失败 Issue 逐项列出。"""

    with tempfile.TemporaryDirectory() as tmp:
        root, fake = _write_old_github_project(Path(tmp) / "gh-game")
        mgs_records.apply_github_material_migration(
            root, mgs_records.plan_github_material_migration(
                root, transport=fake),
            confirmed=True, transport=fake)
        plan = mgs_records.plan_safe_switch(root, transport=fake)
        check(plan.get("ready") is True, f"前置:完整待切换应可切换:{plan}")
        fake.http_error("PATCH", "/issues/", 500)
        applied = mgs_records.apply_safe_switch(
            root, plan, confirmed=True, transport=fake)
        check(applied.get("ok") is not True,
              f"远端标记更新失败不得报告成功:{applied}")
        check(applied.get("status") != "switched",
              "标记未确认时不得宣告 switched")
        check(applied.get("marker_failures"),
              f"必须逐项列出未确认的标记迁移,实际 {applied}")
        status = mgs_records.read_safe_switch(root, transport=fake)
        check(status.get("status") != "switched",
              f"失败时不得写入本地切换状态,实际 {status.get('status')}")
        bodies = [item.get("body") or "" for item in fake.issues]
        check(any("迁移状态:pending-switch" in body for body in bodies),
              "替身状态中待切换标记仍在(与未确认事实一致)")


def test_client_switch_retires_legacy_entries_and_keeps_user_skills() -> None:
    """切换客户端来源时,新包已退役的 1.x 旧入口先归档再退出活动目录;
    无关用户技能保持原样;client_complete 如实反映。"""

    with tempfile.TemporaryDirectory() as tmp:
        ready = _write_old_local_project(Path(tmp) / "ready-game")
        _convert_local(ready)
        home = Path(tmp) / "shared-codex"
        skills = _write_isolated_client(home)
        for retired_name in ("game-art", "game-status"):
            legacy = skills / retired_name
            legacy.mkdir(parents=True, exist_ok=True)
            (legacy / "SKILL.md").write_text(
                f"---\nname: {retired_name}\ndescription: 1.x 旧入口。\n---\n\n"
                "旧入口正文。\n", encoding="utf-8")
        custom = skills / "my-custom"
        custom.mkdir(parents=True, exist_ok=True)
        (custom / "SKILL.md").write_text(
            "---\nname: my-custom\ndescription: 用户自建。\n---\n\n自建正文。\n",
            encoding="utf-8")
        package = Path(tmp) / "package-skills"
        shutil.copytree(PLUGIN_SKILLS, package)
        internal = Path(tmp) / "internal" / "game"
        shutil.copytree(REPO_ROOT / "plugin" / "internal" / "game", internal)
        plan = mgs_records.plan_safe_switch(
            ready, client_home=home, package_root=package)
        applied = mgs_records.apply_safe_switch(ready, plan, confirmed=True)
        check(applied.get("ok") is True, f"切换应成功:{applied}")
        retired = applied.get("retired_skills") or []
        check(set(retired) >= {"game-art", "game-status"},
              f"退役的 1.x 入口必须逐项上报,实际 {retired}")
        check(not (skills / "game-art").exists()
              and not (skills / "game-status").exists(),
              "退役入口不得继续留在活动目录")
        check((home / "skills-history" / "game-art" / "SKILL.md").is_file()
              and (home / "skills-history" / "game-status" / "SKILL.md").is_file(),
              "退役入口必须先归档再移除")
        check((skills / "my-custom" / "SKILL.md").is_file(),
              "无关用户技能必须保持原样")
        check(applied.get("client_complete") is True,
              "退役清理不阻塞切换完成")


def main() -> int:
    return run_theme(
        "issue #59 用户修改、同名来源与安全切换",
        (
            test_incomplete_and_unconfirmed_do_not_switch,
            test_complete_check_then_switch_makes_new_current,
            test_same_name_skill_unique_source_and_stage_reads,
            test_skill_switch_keeps_ordinary_user_edits_or_pauses,
            test_later_skill_extras_survive_second_project_switch,
            test_shared_client_unready_keeps_old_environment,
            test_requested_client_missing_is_not_complete,
            test_rollback_preserves_new_additions,
            test_rollback_preserves_edits_to_migrated_tasks,
            test_prep_change_and_partial_do_not_switch,
            test_deleted_source_during_prep_blocks_switch,
            test_github_switch_makes_new_current_and_can_roll_back,
            test_github_marker_failure_is_not_reported_switched,
            test_client_switch_retires_legacy_entries_and_keeps_user_skills,
            test_stale_ready_plan_rechecked_before_promotion,
        ),
        FAILURES)


if __name__ == "__main__":
    raise SystemExit(main())

#!/usr/bin/env python3
"""Issue #57 seams: complete local Markdown material migration.

Confirmed seams (issue #57 acceptance + #49 T11 and this ticket's T12):
- T11: a scoped technical fixture verifies conversion of all specs,
  decisions, tasks, results and evidence mappings, including historical
  status, unpublished and pending-index items. Creating only tasks or
  attaching old links must not pass the complete-migration check.
- T12 (this ticket): modifications during preparation, user modifications
  and partial migration. Client pointer switch and rollback belong to #59.
- AC: old originals remain; valid CONFIG converts to new-version meaning;
  gate history is archived and is not new-version permission; conversion
  stays pending-switch while old materials remain the current source;
  conflicts pause only related steps. Tracker stays local-markdown.

Public seams: mgs_records.plan_local_material_migration /
apply_local_material_migration / read_local_material_migration.
Converted design, tasks and snapshots are also observable through the
existing #53 / #51 / #54 seams pointed at the pending-switch tree.

Expected values come from issues #57 and #49 D5/D6/D9, not internals.
Do not assert internal functions, directory counts, or prompt keywords.

    python3 -B tests/test_local_material_migration.py
"""

from __future__ import annotations

import hashlib
import json
import tempfile
from pathlib import Path

from records_backend_support import make_checker, run_theme

import mgs_records  # noqa: E402

FAILURES, check = make_checker()

USER_RULE = "只接金色星星"
CORE_PLAY_V2 = "玩家左右移动接住落下的金色星星。接到一颗得 1 分。漏接三次结束。"
CORE_PLAY_V1 = "玩家左右移动接住落下的星星。接到一颗得 1 分。漏接三次结束。"
CORE_PLAY_V0 = "最早版本用鼠标点击接星，尚未改成方向键。"
RESULT_TEXT = "实际成果:src/player.js 左右移动。已执行验证:代码级检查通过。"
EVIDENCE_TEXT = "开发者试玩:移动跟手,可以进入跳跃。"
TRIAL_NOTE = "试验跳跃高度 12,未经采纳。"
UNPUBLISHED_NOTE = "发布记录未知,不得宣称已发布。"
MISSING_EVIDENCE = "docs/mygamestudio/evidence/lost-playtest.md"


def _sha_files(root: Path) -> dict[str, str]:
    files = {}
    for path in sorted(root.rglob("*")):
        if path.is_file():
            files[str(path.relative_to(root))] = hashlib.sha256(
                path.read_bytes()).hexdigest()
    return files


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
    """Scoped technical fixture: old local-markdown project materials."""

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
        "docs/mygamestudio/PROJECT.md": (
            "# star-catcher:项目约定\n\n最小接星闭环。\n"
        ),
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

## 变更索引

v2(2026-09-07):改为只接金色星星。v1(2026-09-05):初版,见 records/GAME_DESIGN-v1.md。
""",
        "docs/mygamestudio/TECH_DESIGN.md": (
            "# 技术约定\n\n纯 HTML/JS。源码在 src/。\n"
        ),
        "docs/mygamestudio/records/GAME_DESIGN-v1.md": f"""# star-catcher：当前游戏需求与设计

维护责任：方案设计。基线版本：v1。适用范围：最小闭环。

## 玩家体验与需求

{CORE_PLAY_V1}

## 当前规则与流程

- 得分：每颗星星 1 分。
- 结束：漏接 3 颗后本局结束。
""",
        "docs/mygamestudio/records/GAME_DESIGN-v0.md": f"""# star-catcher：当前游戏需求与设计

维护责任：方案设计。基线版本：v0。适用范围：试验稿。

## 玩家体验与需求

{CORE_PLAY_V0}

## 当前规则与流程

- 操作：鼠标点击接星。
""",
        "docs/mygamestudio/records/decision-adopted.md": """# 核心循环:接星星

状态:已采纳。日期:2026-09-05。维护角色:方案设计。

## 选项与决定

开发者决定采用限时接星。

## 替代关系

无(首个决定)。
""",
        "docs/mygamestudio/records/decision-pending.md": """# 是否加入连击

状态:未决。日期:2026-09-06。维护角色:方案设计。

## 选项与决定

尚未选择。
""",
        "docs/mygamestudio/records/decision-replaced.md": """# 背景手绘

状态:已被替代。日期:2026-08-12。维护角色:方案设计。

## 替代关系

被星野粒子方案替代。
""",
        "docs/mygamestudio/records/decision-trial.md": f"""# 跳跃高度试验

状态:试验。日期:2026-09-06。维护角色:方案设计。

## 选项与决定

{TRIAL_NOTE}
""",
        "docs/mygamestudio/records/decision-unverified.md": """# 手感是否跟手

状态:未验证。日期:2026-09-07。维护角色:方案设计。

## 选项与决定

尚未做人工试玩。
""",
        "docs/mygamestudio/records/gate-policy.md": (
            "# 旧 gate 策略\n\n角色令牌与运行根仅作历史。"
            "不得当作新版权限。\n"
        ),
        "docs/mygamestudio/records/recovery/pending-ops.json": json.dumps({
            "ops": [{"op": "write", "identity": "02-jump", "status": "unknown"}],
            "note": "待恢复:写入结果未知",
        }, ensure_ascii=False, indent=2) + "\n",
        "docs/mygamestudio/work/01-move/task.md": """# 玩家移动

任务身份:01-move。当前分流:ready-for-agent。进度:已完成。认领:maker。关闭原因:完成。

## 工作请求

- 当前目标:实现左右移动
- 输入与基线:GAME_DESIGN v1
- 本次交付:src/player.js 移动
- 允许修改范围:src/**
- 所需能力:文件读写
- 完成标准:方向键可移动
- 执行责任:Agent(制作实现)
- 验收方式:代码级检查
- 依赖:无
- 父任务:无
- 起始条件:标题画面后进入关卡
- 操作:按方向键左右移动
- 反馈:角色立刻平移
- 成果:可左右移动的角色
- 检查责任:制作实现

## 结果索引

- results/2026-09-06.md
- docs/mygamestudio/evidence/playtest-20260906.md

## 状态变化

2026-09-06 完成移动。
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
- 起始条件:角色已可移动
- 操作:按空格跳跃
- 反馈:角色离地再落下
- 成果:可跳跃的角色
- 检查责任:制作实现

## 结果索引

(暂无)

## 状态变化

等待移动完成后开工。
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

## 状态变化

证据缺失,发布状态未知。
""",
        "docs/mygamestudio/evidence/playtest-20260906.md": (
            f"# 试玩记录\n\n任务:01-move。{EVIDENCE_TEXT}\n"
        ),
    })
    return root


def _kinds(plan: dict) -> set[str]:
    return {str(item.get("kind") or "") for item in plan.get("items") or []}


def test_plan_is_readonly_and_covers_in_scope_materials() -> None:
    """T11/AC1: 获准范围内现行与历史规格、决定、任务、结果和证据都进入清单;
    计划只读;保持本地 Markdown tracker。
    """

    with tempfile.TemporaryDirectory() as tmp:
        root = _write_old_local_project(Path(tmp) / "star-catcher")
        before = _sha_files(root)
        plan = mgs_records.plan_local_material_migration(root)
        check(plan.get("wrote") is False, "迁移计划必须只读,不得写入")
        check(before == _sha_files(root), "计划阶段不得改动旧原件")
        check(plan.get("tracker") == "local-markdown"
              and plan.get("backend") == "local-markdown",
              f"本票必须保持所选本地 tracker,实际 {plan.get('tracker')}")
        check(plan.get("gate_required") is False,
              "普通迁移路径不得依赖 gate")
        kinds = _kinds(plan)
        for kind in ("spec", "decision", "task", "result", "evidence"):
            check(kind in kinds, f"迁移清单必须覆盖 {kind},实际 {sorted(kinds)}")
        identities = [item.get("identity") for item in plan.get("items") or []
                      if item.get("kind") == "task"]
        check("01-move" in identities and "02-jump" in identities
              and "03-score" in identities,
              f"任务身份应进入清单并保持可核对,实际 {identities}")
        check(any(item.get("kind") == "spec"
                  and "GAME_DESIGN-v1" in str(item.get("source") or "")
                  for item in plan.get("items") or []),
              "历史规格必须进入转换范围")
        unconfirmed = mgs_records.apply_local_material_migration(
            root, plan, confirmed=False)
        check(unconfirmed.get("wrote") is False,
              "未确认不得执行转换")
        check(before == _sha_files(root), "未确认 apply 不得改动项目")


def test_full_conversion_maps_all_kinds_and_stays_pending_switch() -> None:
    """T11/AC1/AC2/AC4: 全部资料完成转换且可经现有接缝读取设计和任务依赖;
    只建任务或附旧链接不能算完整;成果待切换,旧资料仍为现行来源。
    """

    with tempfile.TemporaryDirectory() as tmp:
        root = _write_old_local_project(Path(tmp) / "star-catcher")
        old_design = (root / "docs/mygamestudio/GAME_DESIGN.md").read_text(
            encoding="utf-8")
        plan = mgs_records.plan_local_material_migration(root)
        applied = mgs_records.apply_local_material_migration(
            root, plan, confirmed=True)
        check(applied.get("ok") is True, f"确认后应完成转换:{applied}")
        check(applied.get("status") == "pending-switch",
              f"迁移成果必须先处于待切换,实际 {applied.get('status')}")
        check(applied.get("tracker") == "local-markdown",
              "转换后仍保持本地 Markdown tracker")
        check((root / "docs/mygamestudio/GAME_DESIGN.md").read_text(
            encoding="utf-8") == old_design,
              "旧现行规格原件必须保留且未被切换")
        current = mgs_records.load_config(root)
        check(current["backend"] == "local-markdown"
              and current["task_root"].rstrip("/") == "docs/mygamestudio/work",
              "项目现行指针必须仍指向旧任务来源")
        live = mgs_records.read_current_design(root)
        check(USER_RULE in (live.get("overall") or ""),
              "切换前现行设计仍应读到旧原文")
        check("规格身份:overall" not in (live.get("overall") or ""),
              "未切换前不得把新版规格当作现行来源")

        report = mgs_records.read_local_material_migration(root)
        check(report.get("status") == "pending-switch",
              "回读状态必须是待切换")
        check(report.get("complete") is True,
              f"范围内资料应完整转换:{report.get('missing')}")
        mapping = report.get("correspondence") or {}
        for kind in ("specs", "decisions", "tasks", "results", "evidence"):
            check(mapping.get(kind), f"对应关系必须包含可核对的 {kind}")

        staging = Path(report.get("pending_root") or "")
        check(staging.is_dir(), "待切换成果必须有可读取的新资料根")
        converted = mgs_records.read_current_design(staging)
        overall = converted.get("overall") or ""
        check("规格身份:overall" in overall,
              "新资料必须是可读取的完整现行规格,不能只附旧链接")
        check(CORE_PLAY_V2 in overall and USER_RULE in overall,
              "新规格必须包含现行设计与适用用户修改,不能只建空壳")
        modules = converted.get("modules") or {}
        check(modules, "完整设计应能读取按需模块,不能只有旧文件链接")
        history = converted.get("history") or ""
        check("已采纳" in history and "未决" in history
              and "已被替代" in history and "试验" in history
              and "未验证" in history,
              "历史采纳/未决/替代/试验/未验证必须保持原义")
        check(CORE_PLAY_V1 in history or CORE_PLAY_V1 in " ".join(modules.values()),
              "历史规格内容必须可核对,不能只保留旧路径")

        tasks = {task["identity"]: task
                 for task in mgs_records.list_tasks(staging)}
        check(set(tasks) >= {"01-move", "02-jump", "03-score"},
              f"全部任务身份应可回读,实际 {sorted(tasks)}")
        jump = tasks["02-jump"]
        check("01-move" in str(jump.get("request", {}).get("依赖") or ""),
              f"任务依赖必须可读取,实际 {jump.get('request')}")
        check(jump.get("request", {}).get("父任务") == "01-move",
              f"父子关系必须可核对,实际 {jump.get('request')}")
        move = mgs_records.read_task(staging, "01-move")
        result_blob = "\n".join(move.get("results") or []) + "\n" + str(
            move.get("result_index_text") or "")
        check("2026-09-06" in result_blob or RESULT_TEXT in result_blob,
              "结果必须转换到新任务记录,不能只添加旧链接")
        evidence_path = root / "docs/mygamestudio/evidence/playtest-20260906.md"
        check(evidence_path.is_file()
              and EVIDENCE_TEXT in evidence_path.read_text(encoding="utf-8"),
              "必要证据原件必须仍可达")
        snaps = mgs_records.read_design_snapshots(staging)
        snap_text = " ".join(
            (item.get("overall") or "") + (item.get("meta") or "")
            for item in snaps.get("snapshots") or [])
        check(CORE_PLAY_V1 in snap_text or CORE_PLAY_V1 in (converted.get("history") or ""),
              "历史规格版本必须可经快照或历史记录核对")
        check(CORE_PLAY_V0 in snap_text,
              "不同历史规格版本必须各自可经快照接缝读取,不能互相覆盖")

        # T11: 只创建任务或附旧链接不能通过完整迁移检查
        fake = Path(tmp) / "tasks-only"
        fake.mkdir()
        mgs_records.apply_local_onboarding(
            fake, mgs_records.plan_local_onboarding(fake), confirmed=True)
        mgs_records.create_task(
            fake, "01-move", "玩家移动",
            {"当前目标": "见旧项目",
             "输入与基线": "旧链接 docs/mygamestudio/GAME_DESIGN.md",
             "本次交付": "旧任务链接",
             "允许修改范围": "src/**",
             "所需能力": "文件读写",
             "完成标准": "链接存在",
             "执行责任": "Agent(制作实现)",
             "验收方式": "代码级检查",
             "依赖": "无"})
        incomplete = mgs_records.read_local_material_migration(fake)
        check(incomplete.get("complete") is not True,
              "只创建任务或添加旧链接不能通过完整迁移检查")


def test_github_tracker_is_not_converted_here() -> None:
    """AC1 / #49: 本票只转换本地 Markdown 旧项目,保持所选 tracker,
    不把 GitHub 旧项目迁进来,也不双向同步。
    """

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp) / "gh-game"
        _write_tree(root, {
            "docs/mygamestudio/CONFIG.md": """# 协作配置

## 任务来源

- 后端:github-issues
- 当前位置:github.com/example/game
- 任务读取规则:GitHub Issues
- 外部连接引用及已确认操作范围:无

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
| 游戏需求与设计 | docs/mygamestudio/GAME_DESIGN.md | 方案设计 |
""",
        })
        try:
            mgs_records.plan_local_material_migration(root)
        except mgs_records.RecordsError as exc:
            check("GitHub" in str(exc) or "后续" in str(exc),
                  f"GitHub 旧项目应拒绝并指向后续票,实际 {exc}")
        else:
            check(False, "GitHub 后端项目不得走本地完整资料迁移入口")


def test_originals_config_gate_and_user_edits() -> None:
    """AC3: 旧原件保留;适用用户修改迁入;有效配置转入新版含义;
    gate 历史与待恢复记录留存且不作为新版权限。
    """

    with tempfile.TemporaryDirectory() as tmp:
        root = _write_old_local_project(Path(tmp) / "star-catcher")
        gate_src = (root / "docs/mygamestudio/records/gate-policy.md").read_text(
            encoding="utf-8")
        pending_src = (
            root / "docs/mygamestudio/records/recovery/pending-ops.json"
        ).read_text(encoding="utf-8")
        applied = mgs_records.apply_local_material_migration(
            root, mgs_records.plan_local_material_migration(root),
            confirmed=True)
        check((root / "docs/mygamestudio/records/gate-policy.md").read_text(
            encoding="utf-8") == gate_src, "gate 历史原件必须保留")
        check((root / "docs/mygamestudio/records/recovery/pending-ops.json"
               ).read_text(encoding="utf-8") == pending_src,
              "待恢复记录原件必须保留")
        check(applied.get("gate_required") is False,
              "gate 历史不得变成新版权限依赖")
        report = mgs_records.read_local_material_migration(root)
        check(report.get("gate_as_permission") is False,
              "回读不得把 gate 历史当作新版权限")
        staging = Path(report.get("pending_root") or "")
        new_config = mgs_records.load_config(staging)
        check(new_config["backend"] == "local-markdown",
              "有效配置必须转入新版本地 tracker 含义")
        new_cfg_text = (staging / "docs/mygamestudio/CONFIG.md").read_text(
            encoding="utf-8")
        check("mgs-gate" not in new_cfg_text
              and "producer-token" not in new_cfg_text,
              "新版配置不得把旧 gate 令牌写成权限")
        archived = report.get("gate_history") or ""
        check("gate" in archived.lower() or "mgs-gate" in archived,
              "gate 历史配置必须妥善留存")
        check("unknown" in (report.get("recovery_archive") or "")
              or "待恢复" in (report.get("recovery_archive") or ""),
              "待恢复记录必须留存在迁移成果中")
        converted = mgs_records.read_current_design(staging)
        check(USER_RULE in (converted.get("overall") or ""),
              "适用用户修改必须迁入新规格")


def test_partial_rerun_conflict_missing_and_unpublished() -> None:
    """AC4/AC5/T12: 部分转换、中断恢复、重复运行只补缺项;
    准备期间新增修改可识别,冲突只暂停相关步骤;缺失证据与未知发布如实保留。
    """

    with tempfile.TemporaryDirectory() as tmp:
        root = _write_old_local_project(Path(tmp) / "star-catcher")
        plan = mgs_records.plan_local_material_migration(root)
        (root / "docs/mygamestudio/work/02-jump/task.md").write_text(
            (root / "docs/mygamestudio/work/02-jump/task.md").read_text(
                encoding="utf-8").replace("加入跳跃", "加入二段跳(准备期间新增)"),
            encoding="utf-8")
        applied = mgs_records.apply_local_material_migration(
            root, plan, confirmed=True)
        paused = applied.get("paused") or []
        check(any("02-jump" in str(item) for item in paused),
              f"准备期间任务冲突应只暂停相关步骤,实际 {paused}")
        check(applied.get("status") in ("pending-switch", "partial"),
              "其余无冲突步骤仍应留下待切换或部分成果")
        check((root / "docs/mygamestudio/GAME_DESIGN.md").is_file(),
              "冲突不得删除旧原件")

        report = mgs_records.read_local_material_migration(root)
        staging = Path(report.get("pending_root") or "")
        if staging.is_dir() and (staging / "docs/mygamestudio/CONFIG.md").is_file():
            converted = mgs_records.read_current_design(staging)
            check(CORE_PLAY_V2 in (converted.get("overall") or ""),
                  "无冲突的规格步骤仍应转换")
            tasks = {task["identity"] for task in mgs_records.list_tasks(staging)}
            check("02-jump" not in tasks or report.get("paused"),
                  "冲突任务不得在未解决时被覆盖写入")
            score = mgs_records.read_task(staging, "03-score")
            blob = str(score.get("result_index_text") or "") + str(score)
            check("未知" in blob or "未发布" in blob or "unpublished" in blob,
                  "未知发布记录必须保持原义,不得宣称已发布")
            check(report.get("missing_evidence"),
                  "缺失证据必须在回读中标明,不得补造")
            lost = root / MISSING_EVIDENCE
            check(not lost.is_file(), "不得为通过检查而补造缺失证据文件")

        # 中断后重复运行:先留下部分成果,再只补缺项
        if staging.is_dir():
            history = staging / "docs/mygamestudio/records/spec-history.md"
            if history.is_file():
                history.unlink()
            rerun = mgs_records.apply_local_material_migration(
                root, mgs_records.plan_local_material_migration(root),
                confirmed=True)
            check(rerun.get("filled_gap_only") is True
                  or rerun.get("duplicate_avoided") is True
                  or (rerun.get("created") == 0),
                  f"回读后重复运行应只补缺项,实际 {rerun}")
            restored = mgs_records.read_local_material_migration(root)
            restored_root = Path(restored.get("pending_root") or staging)
            hist = mgs_records.read_current_design(restored_root).get("history") or ""
            check("已采纳" in hist, "中断恢复必须补回缺失的历史记录")


def test_deleted_source_during_prep_pauses_migration() -> None:
    """T12: 准备期间删除已指纹来源必须暂停该项,不得用空正文重建后继续宣称对应完整。"""

    with tempfile.TemporaryDirectory() as tmp:
        root = _write_old_local_project(Path(tmp) / "deleted-source")
        plan = mgs_records.plan_local_material_migration(root)
        task_path = root / "docs/mygamestudio/work/02-jump/task.md"
        check(task_path.is_file(), "前置必须有已指纹的任务原件")
        task_path.unlink()
        applied = mgs_records.apply_local_material_migration(
            root, plan, confirmed=True)
        paused = applied.get("paused") or []
        check(any("02-jump" in str(item) for item in paused),
              f"删除已指纹来源必须暂停该项,实际 {paused}")
        staging = Path(applied.get("pending_root") or "")
        check(staging.is_dir(), "其余无冲突步骤仍应留下待切换目录")
        identities = {
            task.get("identity")
            for task in mgs_records.list_tasks(staging)
        }
        check("02-jump" not in identities,
              f"不得用空正文重建已删除任务,实际 {sorted(identities)}")
        mapped = [
            row.get("identity")
            for row in (applied.get("correspondence") or {}).get("tasks") or []
        ]
        check("02-jump" not in mapped,
              f"对应关系不得把已删除任务记成已转换,实际 {mapped}")


def test_colliding_version_numbers_keep_separate_snapshots() -> None:
    """历史规格 v1.0.0 与 v1.1.0 不得共用同一快照身份而互相覆盖。"""

    play_v100 = "v1.0.0 只接白色星星。"
    play_v110 = "v1.1.0 改为接金色星星。"
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp) / "star-catcher"
        _write_tree(root, {
            "README.md": "# star-catcher\n",
            "src/main.js": "console.log('catch');\n",
            "docs/mygamestudio/CONFIG.md": _old_config(gate_line=False),
            "docs/mygamestudio/GAME_DESIGN.md": (
                "# 现行\n\n维护责任：方案设计。基线版本：v2。\n\n"
                "现行只接金色星星。\n"
            ),
            "docs/mygamestudio/records/GAME_DESIGN-v1.0.0.md": (
                f"# 历史 v1.0.0\n\n维护责任：方案设计。基线版本：v1.0.0。\n\n"
                f"{play_v100}\n"
            ),
            "docs/mygamestudio/records/GAME_DESIGN-v1.1.0.md": (
                f"# 历史 v1.1.0\n\n维护责任：方案设计。基线版本：v1.1.0。\n\n"
                f"{play_v110}\n"
            ),
        })
        applied = mgs_records.apply_local_material_migration(
            root, mgs_records.plan_local_material_migration(root),
            confirmed=True)
        check(applied.get("ok") is True, f"转换应成功:{applied}")
        staging = Path(applied.get("pending_root") or "")
        snaps = mgs_records.read_design_snapshots(staging).get("snapshots") or []
        overalls = [item.get("overall") or "" for item in snaps]
        check(any(play_v100 in text for text in overalls),
              "v1.0.0 历史规格必须仍可经快照读取")
        check(any(play_v110 in text for text in overalls),
              "v1.1.0 历史规格必须另存,不得覆盖 v1.0.0")
        ids = [item.get("design_id") for item in snaps]
        check(len(set(ids)) >= 2,
              f"两个游戏版本必须有不碰撞的设计身份,实际 {ids}")


def test_duplicate_task_identity_across_roots_pauses() -> None:
    """配置任务根与 tasks/ 出现同一身份时必须暂停,不得后写覆盖。"""

    with tempfile.TemporaryDirectory() as tmp:
        root = _write_old_local_project(Path(tmp) / "star-catcher")
        original = (root / "docs/mygamestudio/work/01-move/task.md").read_text(
            encoding="utf-8")
        dest = root / "tasks" / "01-move"
        dest.mkdir(parents=True)
        (dest / "task.md").write_text(
            original.replace("当前目标:实现左右移动", "当前目标:另一份同身份任务"),
            encoding="utf-8")
        applied = mgs_records.apply_local_material_migration(
            root, mgs_records.plan_local_material_migration(root),
            confirmed=True)
        paused = " ".join(str(item) for item in (applied.get("paused") or []))
        check("01-move" in paused,
              f"跨根重复身份必须暂停,实际 paused={applied.get('paused')}")
        staging = Path(applied.get("pending_root") or "")
        pending = staging / "docs/mygamestudio/work/01-move/task.md"
        if pending.is_file():
            text = pending.read_text(encoding="utf-8")
            check("另一份同身份任务" not in text,
                  "不得用后写的重复身份覆盖转换成果")


def main() -> int:
    return run_theme(
        "issue #57 本地旧项目完整资料迁移",
        (
            test_plan_is_readonly_and_covers_in_scope_materials,
            test_full_conversion_maps_all_kinds_and_stays_pending_switch,
            test_originals_config_gate_and_user_edits,
            test_partial_rerun_conflict_missing_and_unpublished,
            test_deleted_source_during_prep_pauses_migration,
            test_colliding_version_numbers_keep_separate_snapshots,
            test_duplicate_task_identity_across_roots_pauses,
            test_github_tracker_is_not_converted_here,
        ),
        FAILURES,
    )


if __name__ == "__main__":
    raise SystemExit(main())

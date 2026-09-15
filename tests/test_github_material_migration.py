#!/usr/bin/env python3
"""Issue #58 seams: complete GitHub material migration.

Confirmed seams (issue #58 acceptance + #49 T11 and this ticket's T12):
- T11: a scoped technical fixture verifies conversion of all specs,
  decisions, tasks, results and evidence mappings, including historical
  status, native parent/child and blocking, unpublished and pending-index
  items. Creating only tasks or attaching old links must not pass.
- T12 (this ticket): unpublished, unknown-result, partial conversion,
  lost-response reread/adopt, interrupt resume filling gaps only.
  Client pointer switch and rollback belong to #59.
- AC: old originals remain; tracker stays github-issues; valid CONFIG
  converts to new-version meaning; gate history is archived and is not
  new-version permission; conversion stays pending-switch while old
  GitHub issues remain the current source. Native relations are restored
  on converted GitHub issues, not by building a local tree that pretends
  to be GitHub.

Public seams: mgs_records.plan_github_material_migration /
apply_github_material_migration / read_github_material_migration.
Converted native relations are also observable by reading the converted
GitHub issues through the existing transport / read_task-style boundary.
Current list_tasks and read_current_design must keep the old source
until #59.

Expected values come from issues #58 and #49 D5/D6/D9, not internals.
Do not assert internal functions, directory counts, or prompt keywords.

    python3 -B tests/test_github_material_migration.py
"""

from __future__ import annotations

import hashlib
import json
import tempfile
from pathlib import Path

from github_backend_fixtures import AUTH, REPO, make_checker, run_theme
from github_backend_transport import FakeTransport

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


def _task_request(goal: str, *, deps: str = "无", parent: str = "无",
                  baseline: str = "GAME_DESIGN v2") -> dict:
    return {
        "当前目标": goal,
        "输入与基线": baseline,
        "本次交付": "可回读的任务记录",
        "允许修改范围": "src/**",
        "所需能力": "文件读写",
        "完成标准": "记录可回读",
        "执行责任": "Agent(制作实现)",
        "验收方式": "代码级检查",
        "依赖": deps,
        "父任务": parent,
    }


def _seed_old_github_issues(fake: FakeTransport) -> None:
    """Old GitHub tasks: body parent/deps only, no native relations."""

    fake.seed_issue(
        "01-move", "玩家移动",
        triage="ready-for-agent", progress="已完成",
        project_label="ready-for-agent",
        request=_task_request("实现左右移动", baseline="GAME_DESIGN v1"),
        state="closed", state_reason="completed")
    fake.comments[1].append({
        "id": 6101,
        "body": f"# 移动结果\n\n任务:01-move。{RESULT_TEXT}\n",
        "created_at": "2026-09-06T12:00:00Z",
    })
    fake.seed_issue(
        "02-jump", "跳跃",
        triage="ready-for-agent", progress="待执行",
        project_label="ready-for-agent",
        request=_task_request("加入跳跃", deps="01-move", parent="01-move"),
        deps="01-move")
    fake.seed_issue(
        "03-score", "计分板",
        triage="needs-info", progress="待执行",
        project_label="needs-info",
        request=_task_request("显示分数", deps="01-move"),
        deps="01-move")
    score = fake.issues[2]
    score["body"] = score["body"].replace(
        "(暂无)",
        f"- {MISSING_EVIDENCE}\n- 发布记录:未知。{UNPUBLISHED_NOTE}")


def _write_old_github_project(root: Path) -> tuple[Path, FakeTransport]:
    """Scoped technical fixture: GitHub tracker plus local scattered files."""

    root.mkdir(parents=True, exist_ok=True)
    (root / "src").mkdir(parents=True, exist_ok=True)
    (root / "README.md").write_text(
        "# star-catcher\n\n接星星技术夹具,不是真实个人项目。\n",
        encoding="utf-8")
    (root / "src/main.js").write_text("console.log('catch');\n", encoding="utf-8")
    mgs_records.apply_github_onboarding(
        root, mgs_records.plan_github_onboarding(
            root, repo=REPO, authorization=AUTH),
        confirmed=True)
    config_path = root / "docs/mygamestudio/CONFIG.md"
    config_text = config_path.read_text(encoding="utf-8")
    if "mgs-gate" not in config_text:
        config_path.write_text(
            config_text.rstrip() + "\n\n- 运行保障:mgs-gate MCP;角色令牌 "
            "producer-token;运行根 /tmp/mgs-runtime;策略 "
            "docs/mygamestudio/records/gate-policy.md\n",
            encoding="utf-8")
    _write_tree(root, {
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
        "docs/mygamestudio/TECH_DESIGN.md": (
            "# 技术约定\n\n纯 HTML/JS。源码在 src/。\n"
        ),
        "docs/mygamestudio/records/GAME_DESIGN-v1.md": f"""# star-catcher：当前游戏需求与设计

维护责任：方案设计。基线版本：v1。适用范围：最小闭环。

## 玩家体验与需求

{CORE_PLAY_V1}
""",
        "docs/mygamestudio/records/GAME_DESIGN-v0.md": f"""# star-catcher：当前游戏需求与设计

维护责任：方案设计。基线版本：v0。适用范围：试验稿。

## 玩家体验与需求

{CORE_PLAY_V0}
""",
        "docs/mygamestudio/records/decision-adopted.md": """# 核心循环:接星星

状态:已采纳。日期:2026-09-05。维护角色:方案设计。

## 选项与决定

开发者决定采用限时接星。
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
        "docs/mygamestudio/evidence/playtest-20260906.md": (
            f"# 试玩记录\n\n任务:01-move。{EVIDENCE_TEXT}\n"
        ),
    })
    fake = FakeTransport()
    _seed_old_github_issues(fake)
    return root, fake


def _kinds(plan: dict) -> set[str]:
    return {str(item.get("kind") or "") for item in plan.get("items") or []}


def _pending_issues(fake: FakeTransport) -> list[dict]:
    return [item for item in fake.issues
            if "迁移状态:pending-switch" in (item.get("body") or "")]


def test_plan_is_readonly_and_covers_in_scope_materials() -> None:
    """T11/AC1: 获准范围内现行与历史规格、决定、GitHub 任务、结果和证据
    都进入清单;计划只读;保持 GitHub tracker。
    """

    with tempfile.TemporaryDirectory() as tmp:
        root, fake = _write_old_github_project(Path(tmp) / "star-catcher")
        before = _sha_files(root)
        before_issues = json.dumps(fake.issues, ensure_ascii=False, sort_keys=True)
        plan = mgs_records.plan_github_material_migration(
            root, transport=fake)
        check(plan.get("wrote") is False, "迁移计划必须只读,不得写入")
        check(before == _sha_files(root), "计划阶段不得改动旧原件")
        check(json.dumps(fake.issues, ensure_ascii=False, sort_keys=True)
              == before_issues,
              "计划阶段不得改动旧 GitHub Issue")
        check(plan.get("tracker") == "github-issues"
              and plan.get("backend") == "github-issues",
              f"本票必须保持所选 GitHub tracker,实际 {plan.get('tracker')}")
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
              "历史规格必须进入转换范围,含旧本地分散材料")
        unconfirmed = mgs_records.apply_github_material_migration(
            root, plan, confirmed=False, transport=fake)
        check(unconfirmed.get("wrote") is False,
              "未确认不得执行转换")
        check(before == _sha_files(root), "未确认 apply 不得改动项目")
        check(len(_pending_issues(fake)) == 0,
              "未确认不得发布待切换 GitHub Issue")


def test_full_conversion_restores_native_relations_and_stays_pending_switch() -> None:
    """T11/AC1/AC2/AC5: 全部资料完成转换且在 GitHub 上可回读原生父子与阻塞;
    只建任务或附旧链接不能算完整;成果待切换,旧 Issue 仍为现行来源。
    """

    with tempfile.TemporaryDirectory() as tmp:
        root, fake = _write_old_github_project(Path(tmp) / "star-catcher")
        old_design = (root / "docs/mygamestudio/GAME_DESIGN.md").read_text(
            encoding="utf-8")
        old_issue_bodies = [item.get("body") for item in fake.issues]
        cache = root / "docs/mygamestudio/records/cache"
        plan = mgs_records.plan_github_material_migration(
            root, transport=fake, cache_dir=cache)
        applied = mgs_records.apply_github_material_migration(
            root, plan, confirmed=True, transport=fake, cache_dir=cache)
        check(applied.get("ok") is True, f"确认后应完成转换:{applied}")
        check(applied.get("status") == "pending-switch",
              f"迁移成果必须先处于待切换,实际 {applied.get('status')}")
        check(applied.get("tracker") == "github-issues",
              "转换后仍保持 GitHub tracker")
        check((root / "docs/mygamestudio/GAME_DESIGN.md").read_text(
            encoding="utf-8") == old_design,
              "旧本地规格原件必须保留且未被切换")
        check([item.get("body") for item in fake.issues[:3]] == old_issue_bodies,
              "旧 GitHub 任务 Issue 正文必须保留")
        current = mgs_records.load_config(root)
        check(current["backend"] == "github-issues",
              "项目现行指针必须仍指向 GitHub")
        live_tasks = {task["identity"]: task
                      for task in mgs_records.list_tasks(
                          root, transport=fake, cache_dir=cache)}
        check(set(live_tasks) >= {"01-move", "02-jump", "03-score"},
              f"切换前现行任务仍应是旧身份,实际 {sorted(live_tasks)}")
        live_design = mgs_records.read_current_design(
            root, transport=fake, cache_dir=cache)
        check("迁移状态:pending-switch" not in (live_design.get("overall") or ""),
              "现行规格读取必须跳过待切换成果")

        report = mgs_records.read_github_material_migration(
            root, transport=fake, cache_dir=cache)
        check(report.get("status") == "pending-switch",
              "回读状态必须是待切换")
        check(report.get("complete") is True,
              f"范围内资料应完整转换:{report.get('missing')}")
        mapping = report.get("correspondence") or {}
        for kind in ("specs", "decisions", "tasks", "results", "evidence"):
            check(mapping.get(kind), f"对应关系必须包含可核对的 {kind}")

        pending = _pending_issues(fake)
        spec_bodies = "\n".join(item.get("body") or "" for item in pending
                                if "规格身份:" in (item.get("body") or ""))
        check("规格身份:overall" in spec_bodies,
              "新资料必须是可读取的完整现行规格,不能只附旧链接")
        check(CORE_PLAY_V2 in spec_bodies and USER_RULE in spec_bodies,
              "新规格必须包含现行设计与适用用户修改,不能只建空壳")
        history = str(report.get("history") or "")
        check("已采纳" in history and "未决" in history
              and "已被替代" in history and "试验" in history
              and "未验证" in history,
              "历史采纳/未决/替代/试验/未验证必须保持原义")

        native = report.get("native_relations") or {}
        jump_rel = native.get("02-jump") or {}
        check(jump_rel.get("parent_identity") == "01-move",
              f"父子关系必须恢复为原生并可回读,实际 {jump_rel}")
        check("01-move" in list(jump_rel.get("blocked_by") or []),
              f"阻塞关系必须恢复为原生并可回读,实际 {jump_rel}")
        move_new = next((item for item in pending
                         if "任务身份:01-move" in (item.get("body") or "")), None)
        jump_new = next((item for item in pending
                         if "任务身份:02-jump" in (item.get("body") or "")), None)
        check(move_new and jump_new, "转换后的任务必须是待切换 GitHub Issue")
        check((jump_new or {}).get("id") in fake.sub_issues.get(
            (move_new or {}).get("number"), []),
              "原生 sub-issues 必须可在 GitHub 边界回读")
        check((move_new or {}).get("id") in fake.blocked_by.get(
            (jump_new or {}).get("number"), []),
              "原生 blocked_by 必须可在 GitHub 边界回读")

        new_move_no = (move_new or {}).get("number")
        result_blob = "\n".join(
            comment.get("body") or ""
            for comment in fake.comments.get(new_move_no, []))
        check(RESULT_TEXT in result_blob,
              "结果必须转换到新任务评论,不能只添加旧链接")
        evidence_path = root / "docs/mygamestudio/evidence/playtest-20260906.md"
        check(evidence_path.is_file()
              and EVIDENCE_TEXT in evidence_path.read_text(encoding="utf-8"),
              "必要证据原件必须仍可达")
        snap_text = "\n".join(item.get("body") or "" for item in pending
                              if "快照身份:" in (item.get("body") or ""))
        check(CORE_PLAY_V1 in snap_text,
              "历史规格版本必须可经快照 Issue 核对")
        check(CORE_PLAY_V0 in snap_text,
              "不同历史规格版本必须各自可经快照读取,不能互相覆盖")

        work = root / "docs/mygamestudio/work"
        check(not work.exists() or not any(work.rglob("task.md")),
              "不得再造一套本地任务树冒充 GitHub")

        fake_only = Path(tmp) / "tasks-only"
        fake_only.mkdir()
        mgs_records.apply_github_onboarding(
            fake_only, mgs_records.plan_github_onboarding(
                fake_only, repo=REPO, authorization=AUTH),
            confirmed=True)
        only = FakeTransport()
        mgs_records.create_task(
            fake_only, "01-move", "玩家移动",
            {"当前目标": "见旧项目",
             "输入与基线": "旧链接 docs/mygamestudio/GAME_DESIGN.md",
             "本次交付": "旧任务链接",
             "允许修改范围": "src/**",
             "所需能力": "文件读写",
             "完成标准": "链接存在",
             "执行责任": "Agent(制作实现)",
             "验收方式": "代码级检查",
             "依赖": "无"},
            transport=only,
            cache_dir=fake_only / "docs/mygamestudio/records/cache")
        incomplete = mgs_records.read_github_material_migration(
            fake_only, transport=only)
        check(incomplete.get("complete") is not True,
              "只创建任务或添加旧链接不能通过完整迁移检查")


def test_local_tracker_is_not_converted_here() -> None:
    """AC1 / #49: 本票只转换 GitHub 旧项目,保持所选 tracker,
    不把本地 Markdown 迁进来,也不双向同步。
    """

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp) / "local-game"
        _write_tree(root, {
            "docs/mygamestudio/CONFIG.md": """# 协作配置

## 任务来源

- 后端:local-markdown
- 当前位置:docs/mygamestudio/work
- 任务读取规则:本地 Markdown
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
            mgs_records.plan_github_material_migration(root)
        except mgs_records.RecordsError as exc:
            check("本地" in str(exc) or "plan_local" in str(exc),
                  f"本地 Markdown 项目应拒绝并指向本地入口,实际 {exc}")
        else:
            check(False, "本地 Markdown 项目不得走 GitHub 完整资料迁移入口")


def test_originals_config_gate_and_user_edits() -> None:
    """AC3: 旧原件保留;适用用户修改迁入;有效配置转入新版含义;
    gate 历史与待恢复记录留存且不作为新版权限。
    """

    with tempfile.TemporaryDirectory() as tmp:
        root, fake = _write_old_github_project(Path(tmp) / "star-catcher")
        gate_src = (root / "docs/mygamestudio/records/gate-policy.md").read_text(
            encoding="utf-8")
        pending_src = (
            root / "docs/mygamestudio/records/recovery/pending-ops.json"
        ).read_text(encoding="utf-8")
        current_cfg = (root / "docs/mygamestudio/CONFIG.md").read_text(
            encoding="utf-8")
        cache = root / "docs/mygamestudio/records/cache"
        applied = mgs_records.apply_github_material_migration(
            root, mgs_records.plan_github_material_migration(
                root, transport=fake, cache_dir=cache),
            confirmed=True, transport=fake, cache_dir=cache)
        check((root / "docs/mygamestudio/records/gate-policy.md").read_text(
            encoding="utf-8") == gate_src, "gate 历史原件必须保留")
        check((root / "docs/mygamestudio/records/recovery/pending-ops.json"
               ).read_text(encoding="utf-8") == pending_src,
              "待恢复记录原件必须保留")
        check((root / "docs/mygamestudio/CONFIG.md").read_text(
            encoding="utf-8") == current_cfg,
              "现行 CONFIG 不得被切换")
        check(applied.get("gate_required") is False,
              "gate 历史不得变成新版权限依赖")
        report = mgs_records.read_github_material_migration(
            root, transport=fake, cache_dir=cache)
        check(report.get("gate_as_permission") is False,
              "回读不得把 gate 历史当作新版权限")
        staging = Path(report.get("pending_root") or "")
        new_config = mgs_records.load_config(staging)
        check(new_config["backend"] == "github-issues",
              "有效配置必须转入新版 GitHub tracker 含义")
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
        spec_bodies = "\n".join(item.get("body") or "" for item in _pending_issues(fake)
                                if "规格身份:" in (item.get("body") or ""))
        check(USER_RULE in spec_bodies, "适用用户修改必须迁入新规格")


def test_partial_rerun_conflict_missing_unpublished_and_lost_response() -> None:
    """AC4/AC5/T11/T12: 部分转换、中断恢复、响应丢失回读收养、重复运行只补缺项;
    准备期间新增修改可识别,冲突只暂停相关步骤;缺失证据与未知发布如实保留。
    """

    with tempfile.TemporaryDirectory() as tmp:
        root, fake = _write_old_github_project(Path(tmp) / "star-catcher")
        cache = root / "docs/mygamestudio/records/cache"
        plan = mgs_records.plan_github_material_migration(
            root, transport=fake, cache_dir=cache)
        fake.issues[1]["body"] = fake.issues[1]["body"].replace(
            "加入跳跃", "加入二段跳(准备期间新增)")
        applied = mgs_records.apply_github_material_migration(
            root, plan, confirmed=True, transport=fake, cache_dir=cache)
        paused = applied.get("paused") or []
        check(any("02-jump" in str(item) for item in paused),
              f"准备期间任务冲突应只暂停相关步骤,实际 {paused}")
        check(applied.get("status") in ("pending-switch", "partial"),
              "其余无冲突步骤仍应留下待切换或部分成果")
        check((root / "docs/mygamestudio/GAME_DESIGN.md").is_file(),
              "冲突不得删除旧原件")
        pending = _pending_issues(fake)
        jump_pending = [item for item in pending
                        if "任务身份:02-jump" in (item.get("body") or "")]
        check(not jump_pending, "冲突任务不得在未解决时被覆盖写入")
        spec_bodies = "\n".join(item.get("body") or "" for item in pending
                                if "规格身份:" in (item.get("body") or ""))
        check(CORE_PLAY_V2 in spec_bodies, "无冲突的规格步骤仍应转换")
        score = next((item for item in pending
                      if "任务身份:03-score" in (item.get("body") or "")), None)
        score_blob = (score or {}).get("body") or ""
        check("未知" in score_blob or "未发布" in score_blob
              or "unpublished" in score_blob,
              "未知发布记录必须保持原义,不得宣称已发布")
        report = mgs_records.read_github_material_migration(
            root, transport=fake, cache_dir=cache)
        check(report.get("missing_evidence"),
              "缺失证据必须在回读中标明,不得补造")
        lost = root / MISSING_EVIDENCE
        check(not lost.is_file(), "不得为通过检查而补造缺失证据文件")

        # 中断后重复运行:删掉一份快照 Issue 标记后只补缺项
        snap = next((item for item in fake.issues
                     if "快照身份:" in (item.get("body") or "")
                     and "pending-switch" in (item.get("body") or "")), None)
        if snap is not None:
            snap["body"] = "# 已中断\n"
        rerun = mgs_records.apply_github_material_migration(
            root, mgs_records.plan_github_material_migration(
                root, transport=fake, cache_dir=cache),
            confirmed=True, transport=fake, cache_dir=cache)
        check(rerun.get("filled_gap_only") is True
              or rerun.get("duplicate_avoided") is True
              or (rerun.get("created") == 0),
              f"回读后重复运行应只补缺项,实际 {rerun}")
        restored_snaps = [
            item for item in fake.issues
            if "快照身份:" in (item.get("body") or "")
            and "pending-switch" in (item.get("body") or "")]
        check(any(CORE_PLAY_V1 in (item.get("body") or "")
                  or CORE_PLAY_V0 in (item.get("body") or "")
                  for item in restored_snaps),
              "中断恢复必须补回缺失的历史快照")

        # 响应丢失:已创建则收养,不重复发布
        root2, fake2 = _write_old_github_project(Path(tmp) / "lost-resp")
        cache2 = root2 / "docs/mygamestudio/records/cache"
        plan2 = mgs_records.plan_github_material_migration(
            root2, transport=fake2, cache_dir=cache2)
        fake2.drop("POST", "/issues")
        lost_apply = mgs_records.apply_github_material_migration(
            root2, plan2, confirmed=True, transport=fake2, cache_dir=cache2)
        check(lost_apply.get("ok") is True or lost_apply.get("duplicate_avoided")
              or lost_apply.get("filled_gap_only"),
              f"写入响应丢失后必须回读或保留未知,不得虚报:{lost_apply}")
        fake2._drop.clear()
        again = mgs_records.apply_github_material_migration(
            root2, plan2, confirmed=True, transport=fake2, cache_dir=cache2)
        specs = [item for item in fake2.issues
                 if "规格身份:overall" in (item.get("body") or "")
                 and "快照身份:" not in (item.get("body") or "")
                 and "pending-switch" in (item.get("body") or "")]
        check(len(specs) == 1,
              f"回读后只应有一份待切换整体规格,实际 {len(specs)}")
        move_pending = [item for item in fake2.issues
                        if "任务身份:01-move" in (item.get("body") or "")
                        and "pending-switch" in (item.get("body") or "")]
        check(len(move_pending) == 1,
              f"补缺不得重复创建同一任务,实际 {len(move_pending)}")
        check(again.get("duplicate_avoided") is True
              or again.get("filled_gap_only") is True,
              f"第二次运行应收养已存在成果,实际 {again}")


def main() -> int:
    return run_theme(
        "issue #58 GitHub 旧项目完整资料迁移",
        (
            test_plan_is_readonly_and_covers_in_scope_materials,
            test_full_conversion_restores_native_relations_and_stays_pending_switch,
            test_originals_config_gate_and_user_edits,
            test_partial_rerun_conflict_missing_unpublished_and_lost_response,
            test_local_tracker_is_not_converted_here,
        ),
        FAILURES,
    )


if __name__ == "__main__":
    raise SystemExit(main())

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


def test_colliding_version_numbers_keep_separate_github_snapshots() -> None:
    """GitHub 迁移时 v1.0.0 与 v1.1.0 不得共用快照身份而互相收养覆盖。"""

    play_v100 = "v1.0.0 只接白色星星。"
    play_v110 = "v1.1.0 改为接金色星星。"
    with tempfile.TemporaryDirectory() as tmp:
        root, fake = _write_old_github_project(Path(tmp) / "star-catcher")
        _write_tree(root, {
            "docs/mygamestudio/records/GAME_DESIGN-v1.0.0.md": (
                f"# 历史 v1.0.0\n\n维护责任：方案设计。基线版本：v1.0.0。\n\n"
                f"{play_v100}\n"
            ),
            "docs/mygamestudio/records/GAME_DESIGN-v1.1.0.md": (
                f"# 历史 v1.1.0\n\n维护责任：方案设计。基线版本：v1.1.0。\n\n"
                f"{play_v110}\n"
            ),
        })
        cache = root / "docs/mygamestudio/records/cache"
        applied = mgs_records.apply_github_material_migration(
            root, mgs_records.plan_github_material_migration(
                root, transport=fake, cache_dir=cache),
            confirmed=True, transport=fake, cache_dir=cache)
        check(applied.get("ok") is True, f"转换应成功:{applied}")
        snap_bodies = [
            item.get("body") or ""
            for item in fake.issues
            if "快照身份:" in (item.get("body") or "")
        ]
        check(any(play_v100 in text for text in snap_bodies),
              "v1.0.0 历史规格必须仍可经 GitHub 快照读取")
        check(any(play_v110 in text for text in snap_bodies),
              "v1.1.0 历史规格必须另存,不得覆盖或收养 v1.0.0")
        ids = []
        for text in snap_bodies:
            if play_v100 not in text and play_v110 not in text:
                continue
            marker = "快照身份:"
            start = text.find(marker)
            if start < 0:
                continue
            ids.append(text[start + len(marker):].split("。", 1)[0].strip())
        check(len(set(ids)) >= 2,
              f"两个游戏版本必须有不碰撞的设计身份,实际 {ids}")


def test_github_module_specs_are_converted() -> None:
    """发现的专业模块规格必须各自转换,不能只用合成的 rules 冒充完整。"""

    with tempfile.TemporaryDirectory() as tmp:
        root, fake = _write_old_github_project(Path(tmp) / "star-catcher")
        fake.issues.append({
            "number": 40, "id": 1040, "title": "成长经济",
            "body": (
                "规格身份:economy。种类:模块规格。版本:v1。\n\n"
                "## 当前规则与流程\n\n金币只用于试验商店,尚未采纳。\n"
            ),
            "labels": [], "assignees": [], "state": "open",
            "state_reason": None, "html_url": "https://example.invalid/i/40",
        })
        fake.comments[40] = []
        cache = root / "docs/mygamestudio/records/cache"
        plan = mgs_records.plan_github_material_migration(
            root, transport=fake, cache_dir=cache)
        modules = [item for item in (plan.get("items") or [])
                   if item.get("kind") == "spec" and item.get("role") == "module"]
        check(any(item.get("identity") == "economy" for item in modules),
              f"盘点必须包含专业模块规格,实际 {modules}")
        applied = mgs_records.apply_github_material_migration(
            root, plan, confirmed=True, transport=fake, cache_dir=cache)
        check(applied.get("ok") is True, f"转换应成功:{applied}")
        converted = [
            item for item in fake.issues
            if "规格身份:economy" in (item.get("body") or "")
            and "pending-switch" in (item.get("body") or "")
        ]
        check(converted, "专业模块规格必须有对应的待切换 Issue")
        check(any("金币只用于试验商店" in (item.get("body") or "")
                  for item in converted),
              "模块原文必须进入转换成果,不得只合成 rules")


def test_github_archive_issue_is_not_migrated_as_current_spec() -> None:
    """归档快照里嵌套的规格身份不得把快照当成现行规格。"""

    with tempfile.TemporaryDirectory() as tmp:
        root, fake = _write_old_github_project(Path(tmp) / "star-catcher")
        live = (
            "规格身份:overall。种类:现行规格。版本:v2。\n\n"
            "## 核心玩法\n\n现行只接金色星星。\n"
        )
        archive = "\n".join([
            "# 正式版本设计快照 ds-old r1",
            "快照身份:ds-old。修订:r1。种类:归档快照。不是现行规格。",
            "游戏版本:v0",
            "形成时间:2026-09-01",
            "",
            "## 整体设计(当时完整内容)",
            "",
            "```markdown",
            "规格身份:overall。种类:现行规格。版本:v0。",
            "",
            "## 核心玩法",
            "",
            "最早版本用鼠标点击接星。",
            "```",
            "",
        ])
        fake.issues.insert(0, {
            "number": 50, "id": 1050, "title": "归档快照",
            "body": archive, "labels": [], "assignees": [],
            "state": "open", "state_reason": None,
            "html_url": "https://example.invalid/i/50",
        })
        fake.comments[50] = []
        fake.issues.append({
            "number": 51, "id": 1051, "title": "现行规格",
            "body": live, "labels": [], "assignees": [],
            "state": "open", "state_reason": None,
            "html_url": "https://example.invalid/i/51",
        })
        fake.comments[51] = []
        cache = root / "docs/mygamestudio/records/cache"
        plan = mgs_records.plan_github_material_migration(
            root, transport=fake, cache_dir=cache)
        archive_plan = next(
            item for item in (plan.get("items") or [])
            if item.get("source") == "github:issue:50")
        current_plan = next(
            item for item in (plan.get("items") or [])
            if item.get("source") == "github:issue:51")
        check(archive_plan.get("role") == "historical",
              f"归档快照必须标 historical,实际 {archive_plan}")
        check(archive_plan.get("identity") == "ds-old",
              f"归档身份必须来自快照身份,实际 {archive_plan.get('identity')}")
        check(current_plan.get("role") == "current",
              f"真实现行规格必须标 current,实际 {current_plan}")
        applied = mgs_records.apply_github_material_migration(
            root, plan, confirmed=True, transport=fake, cache_dir=cache)
        check(applied.get("ok") is True, f"转换应成功:{applied}")
        pending_overall = [
            item.get("body") or ""
            for item in fake.issues
            if "规格身份:overall" in (item.get("body") or "")
            and "pending-switch" in (item.get("body") or "")
            and "快照身份:" not in (item.get("body") or "").split("## 整体设计", 1)[0]
        ]
        check(any("现行只接金色星星" in text for text in pending_overall),
              "现行规格必须来自真实现行 Issue")
        check(not any("最早版本用鼠标点击接星" in text.split("## 整体设计", 1)[0]
                      for text in pending_overall),
              "归档正文不得被当成新的现行规格")


def test_github_task_assignees_are_preserved() -> None:
    """旧任务的原生负责人必须带到新 Issue,读回仍能看到认领。"""

    with tempfile.TemporaryDirectory() as tmp:
        root, fake = _write_old_github_project(Path(tmp) / "star-catcher")
        jump = next(item for item in fake.issues
                    if "任务身份:02-jump" in (item.get("body") or ""))
        jump["assignees"] = [{"login": "agent-a"}]
        cache = root / "docs/mygamestudio/records/cache"
        applied = mgs_records.apply_github_material_migration(
            root, mgs_records.plan_github_material_migration(
                root, transport=fake, cache_dir=cache),
            confirmed=True, transport=fake, cache_dir=cache)
        check(applied.get("ok") is True, f"转换应成功:{applied}")
        pending = next(
            item for item in fake.issues
            if "任务身份:02-jump" in (item.get("body") or "")
            and "pending-switch" in (item.get("body") or ""))
        logins = [entry.get("login") for entry in (pending.get("assignees") or [])]
        check("agent-a" in logins,
              f"待切换任务必须保留原生负责人,实际 {pending.get('assignees')}")


def test_github_assignee_write_failure_is_not_converted() -> None:
    """负责人写入失败时不得留下无认领的待切换任务,也不能把该身份记成已转换。"""

    with tempfile.TemporaryDirectory() as tmp:
        root, fake = _write_old_github_project(Path(tmp) / "star-catcher")
        jump = next(item for item in fake.issues
                    if "任务身份:02-jump" in (item.get("body") or ""))
        jump["assignees"] = [{"login": "agent-a"}]
        fake.omit_create_assignees()
        fake.http_error("PATCH", "/issues/", 403, body_contains='"assignees"')
        cache = root / "docs/mygamestudio/records/cache"
        applied = mgs_records.apply_github_material_migration(
            root, mgs_records.plan_github_material_migration(
                root, transport=fake, cache_dir=cache),
            confirmed=True, transport=fake, cache_dir=cache)
        pending = [
            item for item in fake.issues
            if "任务身份:02-jump" in (item.get("body") or "")
            and "pending-switch" in (item.get("body") or "")
            and item.get("state") != "closed"
        ]
        unclaimed = [
            item for item in pending
            if "agent-a" not in [
                entry.get("login") for entry in (item.get("assignees") or [])]
        ]
        check(not unclaimed,
              f"负责人未落地不得留下待切换任务:{pending}")
        mapped = [
            row for row in ((applied.get("correspondence") or {}).get("tasks") or [])
            if row.get("identity") == "02-jump"
        ]
        check(not mapped,
              f"负责人回读失败不得记入已转换对应关系:{mapped}")


def test_github_pending_config_keeps_write_authorization() -> None:
    """待切换 CONFIG 必须带上可解析的仓库级 issues-write 授权。"""

    with tempfile.TemporaryDirectory() as tmp:
        root, fake = _write_old_github_project(Path(tmp) / "star-catcher")
        cache = root / "docs/mygamestudio/records/cache"
        applied = mgs_records.apply_github_material_migration(
            root, mgs_records.plan_github_material_migration(
                root, transport=fake, cache_dir=cache),
            confirmed=True, transport=fake, cache_dir=cache)
        check(applied.get("ok") is True, f"转换应成功:{applied}")
        pending_cfg = Path(applied.get("pending_root") or "") / "docs/mygamestudio/CONFIG.md"
        text = pending_cfg.read_text(encoding="utf-8") if pending_cfg.is_file() else ""
        check("issues-write" in text,
              "待切换 CONFIG 必须写出 issues-write 授权,不能只写沿用字样")
        check("github.com/mygamestudio/issue-accept" in text,
              "待切换授权必须含仓库坐标")
        pending_config = mgs_records.load_config(Path(applied.get("pending_root") or ""))
        check(pending_config.get("remote_write_authorized") is True,
              f"切换前读待切换 CONFIG 必须仍视为已授权:{pending_config}")


def test_migration_inventory_includes_issues_beyond_first_page() -> None:
    """T11: 超过一页的 GitHub Issue 都必须进入迁移清单,不能只盘点前 100 条。"""

    with tempfile.TemporaryDirectory() as tmp:
        root, fake = _write_old_github_project(Path(tmp) / "star-catcher")
        for index in range(4, 102):
            fake.seed_issue(f"{index:03d}-pad", f"填充任务 {index}")
        plan = mgs_records.plan_github_material_migration(root, transport=fake)
        identities = [
            item.get("identity") for item in plan.get("items") or []
            if item.get("kind") == "task"
        ]
        check("101-pad" in identities,
              f"第 101 条任务必须进入迁移清单,实际末项 {identities[-5:]}")
        check(identities.count("01-move") == 1 and "02-jump" in identities,
              "分页不得丢掉第一页已有任务")


def test_closed_task_close_failure_is_not_converted() -> None:
    """旧任务已关闭但迁移后关闭未确认时,不得记为已转换。"""

    with tempfile.TemporaryDirectory() as tmp:
        root, fake = _write_old_github_project(Path(tmp) / "close-fail")
        fake.http_error("PATCH", "/issues", 500,
                        body_contains='"state": "closed"')
        cache = root / "docs/mygamestudio/records/cache"
        plan = mgs_records.plan_github_material_migration(
            root, transport=fake, cache_dir=cache)
        applied = mgs_records.apply_github_material_migration(
            root, plan, confirmed=True, transport=fake, cache_dir=cache)
        paused = applied.get("paused") or []
        check(any("01-move" in item and "未确认保持关闭" in item
                  for item in paused),
              f"关闭未确认必须暂停该项,实际 {paused}")
        task_rows = [row.get("identity")
                     for row in (applied.get("correspondence") or {}).get("tasks") or []]
        check("01-move" not in task_rows,
              f"关闭未验证的任务不得记为已转换,实际 {task_rows}")
        report = mgs_records.read_github_material_migration(
            root, transport=fake, cache_dir=cache)
        check(report.get("complete") is False,
              "存在暂停项时迁移不得宣称完整")


def test_result_index_comments_are_rewritten_to_new_ids() -> None:
    """旧结果索引的 #issuecomment-<旧id> 引用必须改写为新评论 id。"""

    with tempfile.TemporaryDirectory() as tmp:
        root, fake = _write_old_github_project(Path(tmp) / "index-map")
        move = fake.issues[0]
        move["body"] = move["body"].replace(
            "(暂无)", "- 成果:https://example.invalid/i/1#issuecomment-6101")
        cache = root / "docs/mygamestudio/records/cache"
        plan = mgs_records.plan_github_material_migration(
            root, transport=fake, cache_dir=cache)
        applied = mgs_records.apply_github_material_migration(
            root, plan, confirmed=True, transport=fake, cache_dir=cache)
        check(applied.get("ok") is True, f"迁移应完成:{applied}")
        new_issue = next(
            (item for item in fake.issues
             if "迁移状态:pending-switch" in (item.get("body") or "")
             and "任务身份:01-move" in (item.get("body") or "")), None)
        check(new_issue is not None, "应存在迁移后的 01-move 新任务 Issue")
        if new_issue is None:
            return
        body = new_issue.get("body") or ""
        check("#issuecomment-6101" not in body,
              f"旧评论锚点必须被改写,实际正文:\n{body}")
        new_comment = next(
            (comment for comment in fake.comments.get(new_issue["number"], [])
             if "迁移结果:01-move:6101" in (comment.get("body") or "")), None)
        check(new_comment is not None, "结果必须以新评论重发")
        if new_comment is not None:
            check(f"#issuecomment-{new_comment['id']}" in body,
                  f"结果索引必须指向新评论 #{new_comment['id']},实际正文:\n{body}")


def test_native_only_relations_are_inventoried_and_restored() -> None:
    """仅存于原生接口的父子/阻塞关系必须在盘点与恢复中保留。"""

    with tempfile.TemporaryDirectory() as tmp:
        root, fake = _write_old_github_project(Path(tmp) / "native-only")
        fake.seed_issue(
            "04-native", "原生关系任务", project_label="agent-ready",
            request=_task_request("正文不含关系字段", deps="无", parent="无"))
        native = fake.issues[3]
        # 正文约定之外,只用原生接口登记:父=01-move,阻塞=01-move。
        fake.sub_issues.setdefault(1, []).append(native["id"])
        fake.blocked_by.setdefault(native["number"], []).append(
            fake.issues[0]["id"])
        cache = root / "docs/mygamestudio/records/cache"
        plan = mgs_records.plan_github_material_migration(
            root, transport=fake, cache_dir=cache)
        row = next((item for item in plan.get("items") or []
                    if item.get("identity") == "04-native"), None)
        check(row is not None, "盘点必须包含新任务")
        if row is not None:
            check("01-move" in str(row.get("parent") or ""),
                  f"原生父任务必须进入盘点,实际 {row.get('parent')!r}")
            check("01-move" in str(row.get("deps") or ""),
                  f"原生阻塞必须进入盘点,实际 {row.get('deps')!r}")
        applied = mgs_records.apply_github_material_migration(
            root, plan, confirmed=True, transport=fake, cache_dir=cache)
        check(applied.get("ok") is True, f"迁移应完成:{applied}")
        rel = (applied.get("native_relations") or {}).get("04-native") or {}
        check(rel.get("parent_identity") == "01-move",
              f"迁移后必须恢复原生父子关系,实际 {rel}")
        check("01-move" in (rel.get("blocked_by") or []),
              f"迁移后必须恢复原生阻塞关系,实际 {rel}")


def test_decisions_without_any_adopted_are_still_complete() -> None:
    """全部决定未决/试验/被替代时,迁移完整性不得因缺「已采纳」而失败。"""

    with tempfile.TemporaryDirectory() as tmp:
        root, fake = _write_old_github_project(Path(tmp) / "no-adopted")
        (root / "docs/mygamestudio/records/decision-adopted.md").unlink()
        cache = root / "docs/mygamestudio/records/cache"
        plan = mgs_records.plan_github_material_migration(
            root, transport=fake, cache_dir=cache)
        applied = mgs_records.apply_github_material_migration(
            root, plan, confirmed=True, transport=fake, cache_dir=cache)
        check(applied.get("ok") is True, f"迁移应完成:{applied}")
        report = mgs_records.read_github_material_migration(
            root, transport=fake, cache_dir=cache)
        missing = report.get("missing") or []
        check(not any("决定" in item for item in missing),
              f"逐条核对决定评论存在即可,不得强制至少一条已采纳,实际 {missing}")


def main() -> int:
    return run_theme(
        "issue #58 GitHub 旧项目完整资料迁移",
        (
            test_plan_is_readonly_and_covers_in_scope_materials,
            test_full_conversion_restores_native_relations_and_stays_pending_switch,
            test_originals_config_gate_and_user_edits,
            test_partial_rerun_conflict_missing_unpublished_and_lost_response,
            test_colliding_version_numbers_keep_separate_github_snapshots,
            test_github_module_specs_are_converted,
            test_github_archive_issue_is_not_migrated_as_current_spec,
            test_github_task_assignees_are_preserved,
            test_github_assignee_write_failure_is_not_converted,
            test_github_pending_config_keeps_write_authorization,
            test_migration_inventory_includes_issues_beyond_first_page,
            test_closed_task_close_failure_is_not_converted,
            test_result_index_comments_are_rewritten_to_new_ids,
            test_native_only_relations_are_inventoried_and_restored,
            test_decisions_without_any_adopted_are_still_complete,
            test_local_tracker_is_not_converted_here,
        ),
        FAILURES,
    )


if __name__ == "__main__":
    raise SystemExit(main())

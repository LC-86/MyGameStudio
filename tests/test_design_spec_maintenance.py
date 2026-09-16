#!/usr/bin/env python3
"""Issue #53 seams: Game-Design discussion and current-spec maintenance.

Confirmed seams (issue #53 acceptance + #49 T2/T3/T5):
- T2: a new session reads current-stage requirements from Game-Design and from
  Matt to-spec; reading those materials does not start production.
- T3: an explicit small change reuses current decisions and reports related
  impact; trial values are shown and stay out of formal rules until adopted;
  no isolated prototype is added without an explicit request.
- T5: after developer-initiated to-spec, current spec body, affected modules
  and task citations stay consistent; history keeps source, reason and
  replacement; unadopted ideas, trial values and unpublished drafts stay as
  they were. Local Markdown and GitHub Issues are verified separately; one
  project uses only its chosen tracker.

Expected values come from issues #53 and #49 D3/D4/D5, not from internals.
Do not assert internal functions, directory counts, or prompt keywords.

    python3 -B tests/test_design_spec_maintenance.py
"""

from __future__ import annotations

import hashlib
import json
import sys
import tempfile
from pathlib import Path

from github_backend_fixtures import (
    AUTH, REPO, make_checker, make_github_project, run_theme)
from github_backend_transport import FakeTransport
from redesign_bundle_contract import STAGE_REQUIREMENTS_REL

import mgs_records  # noqa: E402

FAILURES, check = make_checker()
REPO_ROOT = Path(__file__).resolve().parents[1]
PLUGIN_ROOT = REPO_ROOT / "plugin"
STAGE = PLUGIN_ROOT / STAGE_REQUIREMENTS_REL
DESIGN_SKILL = PLUGIN_ROOT / "skills" / "game-design" / "SKILL.md"
TO_SPEC_SKILL = PLUGIN_ROOT / "skills" / "to-spec" / "SKILL.md"
GRILLING = PLUGIN_ROOT / "skills" / "grilling" / "SKILL.md"
DOMAIN = PLUGIN_ROOT / "skills" / "domain-modeling" / "SKILL.md"


def _snapshot(root: Path) -> dict[str, str]:
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


def _task_request(goal: str, *, baseline: str = "GAME_DESIGN.md v1") -> dict:
    return {
        "当前目标": goal,
        "输入与基线": baseline,
        "本次交付": "可回读的任务记录",
        "允许修改范围": "src/**",
        "所需能力": "文件读写",
        "完成标准": "记录可回读",
        "执行责任": "Agent(制作实现)",
        "验收方式": "代码级检查",
        "依赖": "无",
    }


# --- T2: discover current-stage design requirements ---------------------------


def test_game_and_matt_entries_read_design_stage_requirements() -> None:
    """T2/AC1: Game-Design and Matt to-spec both reach the unique stage index.

    The index is the single copy of current-stage design requirements: grouped
    questions after settled prerequisites, three-sentence core play then the
    minimum loop, and professional modules read only by real impact.
    Reading the index is not production.
    """

    check(STAGE.is_file(), f"缺少阶段资料入口 {STAGE_REQUIREMENTS_REL}")
    check(DESIGN_SKILL.is_file(), "缺少 skills/game-design/SKILL.md")
    check(TO_SPEC_SKILL.is_file(), "缺少 skills/to-spec/SKILL.md")
    check(GRILLING.is_file(), "Game-Design 复用的 grilling 必须作为公开技能存在")
    check(DOMAIN.is_file(), "Game-Design 复用的 domain-modeling 必须作为公开技能存在")
    if not STAGE.is_file():
        return
    text = STAGE.read_text(encoding="utf-8")
    check("读取资料不是开始制作" in text,
          "阶段资料入口必须声明读取不会自行启动制作")
    design_section = text.split("## 设计讨论")[1].split("## ")[0] if "## 设计讨论" in text else ""
    check(design_section, "阶段资料必须有设计讨论一节,且是该阶段要求的唯一副本")
    check("已具备前提" in design_section or "前提" in design_section,
          "设计讨论阶段要求必须写明按已具备前提的问题成组提问")
    check("三句话" in design_section and "最小" in design_section,
          "设计讨论阶段要求必须写明三句话说明核心玩法后围绕最小闭环深入")
    check("真实影响" in design_section or "按需" in design_section,
          "设计讨论阶段要求必须写明按真实影响读取专业模块")
    check("grilling" in design_section and "domain-modeling" in design_section,
          "设计讨论阶段要求必须指向复用 grilling 与 domain-modeling,不另写同义方法")
    pointer = "../../internal/game/stage-requirements.md"
    for skill_md, name in ((DESIGN_SKILL, "game-design"), (TO_SPEC_SKILL, "to-spec")):
        body = skill_md.read_text(encoding="utf-8") if skill_md.is_file() else ""
        check(pointer in body or STAGE_REQUIREMENTS_REL in body,
              f"{name} 必须能从入口读到当前阶段资料")
        check("mgs-gate" not in body and "gate-protocol" not in body,
              f"{name} 普通路径不得依赖 mgs-gate")
    if DESIGN_SKILL.is_file():
        design_text = DESIGN_SKILL.read_text(encoding="utf-8")
        check("../grilling/SKILL.md" in design_text,
              "Game-Design 必须引用包内 grilling,而不是重写讨论方法")
        check("../domain-modeling/SKILL.md" in design_text,
              "Game-Design 必须引用包内 domain-modeling,而不是重写领域建模")


def test_core_play_then_min_loop_questions() -> None:
    """AC1: 核心玩法未定时先成组问清三句话;说清后再围绕最小闭环深入。
    """

    with tempfile.TemporaryDirectory() as tmp:
        root = _onboard_local(Path(tmp) / "new-game", design="")
        first = mgs_records.plan_design_discussion(root, {
            "kind": "new_feature",
            "request": "想做一款接星星的游戏。",
            "settled": {},
            "questions": [
                {"id": "score", "title": "怎么计分",
                 "depends_on": ["core-play"], "module": "规则与数值"},
            ],
        })
        shown = [item.get("id") for item in first.get("shown_questions") or []]
        check(shown and shown[0] == "core-play",
              "核心玩法未定时必须先问三句话说明核心玩法")
        check("score" not in shown, "核心玩法未定不得展开最小闭环细则")
        second = mgs_records.plan_design_discussion(root, {
            "kind": "new_feature",
            "request": "围绕接星星最小闭环补规则。",
            "settled": {
                "core-play": "玩家左右移动接住落下的星星。接到得分。漏接三次结束。",
            },
            "questions": [
                {"id": "score", "title": "怎么计分",
                 "depends_on": ["core-play"], "module": "规则与数值"},
            ],
        })
        shown2 = [item.get("id") for item in second.get("shown_questions") or []]
        check("core-play" not in shown2, "三句话已说明后不得重问核心玩法")
        check("score" in shown2, "核心玩法说清后应围绕最小闭环深入")


def _onboard_local(root: Path, *, design: str, create_task: bool = True) -> Path:
    root.mkdir(parents=True, exist_ok=True)
    (root / "README.md").write_text("# star-catcher\n\n接星星。\n", encoding="utf-8")
    mgs_records.apply_local_onboarding(
        root, mgs_records.plan_local_onboarding(root), confirmed=True)
    design_path = root / "docs/mygamestudio/GAME_DESIGN.md"
    design_path.parent.mkdir(parents=True, exist_ok=True)
    design_path.write_text(design, encoding="utf-8")
    if create_task:
        mgs_records.create_task(
            root, "01-catch-star", "接住第一颗星星",
            _task_request("接住一颗星星并计分"))
    return root


CORE_DESIGN = """# star-catcher：当前游戏需求与设计

维护责任：方案设计。基线版本：v1。适用范围：最小闭环。采用依据：开发者决定。

## 核心玩法

玩家移动角色接住落下的星星。接到一颗得 1 分。漏接三颗结束本局。

## 当前规则与流程

- 得分：每颗星星 1 分。
- 结束：漏接 3 颗后本局结束。
- 操作：方向键左右移动。

## 变更索引

- v1：采纳最小闭环。来源：开发者。理由：先做出可玩循环。
"""


# --- T3: small change, trial values, no prototype -----------------------------


def test_small_change_reuses_decisions_and_keeps_trial_values_out() -> None:
    """T3/AC1/AC2: 明确小改动复用当前决定并检查关联影响;
    试验值清楚展示且未经采纳不进入正式规则;无显式请求不增加隔离原型。
    """

    with tempfile.TemporaryDirectory() as tmp:
        root = _onboard_local(Path(tmp) / "star-catcher", design=CORE_DESIGN)
        before_design = (root / "docs/mygamestudio/GAME_DESIGN.md").read_text(
            encoding="utf-8")
        before_files = _snapshot(root)
        plan = mgs_records.plan_design_discussion(root, {
            "kind": "small_change",
            "request": "把每颗星星得分改成试验值 3 分,看手感。",
            "settled": {
                "core-play": "玩家移动角色接住落下的星星。接到一颗得 1 分。漏接三颗结束本局。",
                "controls": "方向键左右移动",
                "fail": "漏接 3 颗结束",
            },
            "questions": [
                {"id": "score-value", "title": "每颗星星得分",
                 "depends_on": ["core-play"],
                 "module": "规则与数值"},
                {"id": "shop", "title": "是否增加商店",
                 "depends_on": ["economy-loop"],
                 "module": "成长经济"},
                {"id": "publish", "title": "是否安排外部玩家",
                 "depends_on": ["score-value"],
                 "module": "商业化发行运营"},
            ],
            "trial_values": [
                {"id": "star-score", "value": 3, "unit": "分/颗",
                 "basis": "现行 1 分偏弱,3 分便于判断手感",
                 "adopted": False},
            ],
            "proposals": ["增加金币商店"],
            "explicit_prototype": False,
            "schedule_external_players": False,
        })
        check(plan.get("wrote") is False, "讨论计划阶段不得写入正式规格")
        check(plan.get("gate_required") is False, "普通设计讨论不得依赖 gate")
        shown = [item.get("id") for item in plan.get("shown_questions") or []]
        check("score-value" in shown, "已具备核心玩法前提的题目应成组提出")
        check("shop" not in shown,
              "前提未定的成长经济题目不得提前展开")
        check("core-play" not in shown,
              "已定核心玩法不得重新询问")
        check(plan.get("reuse_current") is True,
              "明确小改动必须复用当前已采纳决定")
        impacted = plan.get("impacted_modules") or []
        check("规则与数值" in impacted, "改得分必须读取规则与数值模块")
        check("商业化发行运营" not in impacted,
              "未服务当前目标的商业化模块不得因资料存在而展开")
        check("成长经济" not in impacted,
              "无真实影响时不得自动新增商店系统")
        trials = plan.get("trial_values") or []
        check(any(item.get("value") == 3 and item.get("adopted") is False
                  for item in trials),
              "试验值必须清楚展示且标明未经采纳")
        check(plan.get("prototype_added") is False,
              "无显式请求不得增加隔离原型")
        check(plan.get("external_players_scheduled") is False,
              "不得自动安排外部玩家")
        applied = mgs_records.apply_design_discussion(root, plan, {
            "score-value": "先用试验值 3,尚未采纳为正式规则",
        })
        check(applied.get("ok") is True, f"应能保存本轮讨论:{applied}")
        check(applied.get("formal_rules_changed") is False,
              "未走 to-spec 时讨论不得改写正式规则")
        current = mgs_records.read_current_design(root)
        check(current.get("wrote") is False, "读取现行规格不得写入")
        body = current.get("overall") or ""
        check("每颗星星 1 分" in body, "现行规则仍应是已采纳的 1 分")
        check("3 分" not in body, "未采纳试验值不得进入正式规则")
        check("金币商店" not in body, "未采纳提议不得进入正式规则")
        design_now = (root / "docs/mygamestudio/GAME_DESIGN.md").read_text(
            encoding="utf-8")
        check(design_now == before_design, "讨论保存不得改写现行规格正文")
        after = _snapshot(root)
        check(before_files["docs/mygamestudio/GAME_DESIGN.md"]
              == after["docs/mygamestudio/GAME_DESIGN.md"],
              "现行规格文件在讨论阶段必须保持原状态")


# --- T5: adoption writes current spec, history and task citations -------------


def test_tospec_adopts_into_overall_module_and_task_refs_local() -> None:
    """T5/AC3/AC4/AC5: 开发者主动 to-spec 后,已采纳进入整体入口及按需模块;
    变更保留来源、理由和替代关系;受影响任务引用同步;小改动不强制另建决策票;
    无关规则不重写;未采纳与试验值保持原状。
    """

    with tempfile.TemporaryDirectory() as tmp:
        root = _onboard_local(Path(tmp) / "star-catcher", design=CORE_DESIGN)
        discussion = mgs_records.plan_design_discussion(root, {
            "kind": "small_change",
            "request": "把每颗星星得分改成 3 分。",
            "settled": {"core-play": "接星星。"},
            "trial_values": [{"id": "star-score", "value": 5, "adopted": False}],
            "proposals": ["增加金币商店"],
        })
        mgs_records.apply_design_discussion(root, discussion, {"score-value": "正式改为 3 分"})
        unpublished = root / "docs/mygamestudio/records/unpublished-draft.md"
        unpublished.write_text("# 未发布草稿\n\n联网排行榜想法。\n", encoding="utf-8")
        draft_sha = hashlib.sha256(unpublished.read_bytes()).hexdigest()
        plan = mgs_records.plan_spec_adoption(root, {
            "kind": "small_change",
            "source": "开发者主动 to-spec",
            "reason": "1 分反馈偏弱,3 分足以判断手感",
            "replaces": "每颗星星 1 分",
            "overall": {
                "title": "star-catcher：当前游戏需求与设计",
                "version": "v2",
                "core_play": "玩家移动角色接住落下的星星。接到一颗得 3 分。漏接三颗结束本局。",
                "rules": [
                    "得分：每颗星星 3 分。",
                    "结束：漏接 3 颗后本局结束。",
                    "操作：方向键左右移动。",
                ],
                "replace_rules": ["每颗星星 1 分"],
            },
            "modules": {
                "规则与数值": {
                    "title": "规则与数值",
                    "version": "v2",
                    "rules": ["每颗星星 3 分。"],
                },
            },
            "affected_tasks": ["01-catch-star"],
            "unadopted": ["增加金币商店"],
            "trial_values": [{"id": "star-score", "value": 5, "adopted": False}],
        })
        check(plan.get("wrote") is False, "to-spec 计划阶段不得写入")
        check(plan.get("decision_ticket_required") is False,
              "小改动不强制另建决策票")
        applied = mgs_records.apply_spec_adoption(root, plan, confirmed=True)
        check(applied.get("ok") is True, f"确认 to-spec 后应写入:{applied}")
        check(applied.get("gate_required") is False, "普通规格写入不得依赖 gate")
        current = mgs_records.read_current_design(root)
        overall = current.get("overall") or ""
        check("每颗星星 3 分" in overall, "已采纳规则必须进入整体入口")
        check("每颗星星 1 分" not in overall, "被替代规则必须退出现行正文")
        check("漏接 3 颗" in overall, "无关规则不得被重写或删去")
        check("金币商店" not in overall, "未采纳提议不得进入正式规则")
        check(" 5 " not in overall and "5 分" not in overall,
              "试验值不得进入正式规则")
        modules = current.get("modules") or {}
        numeric = "\n".join(modules.values())
        check("3 分" in numeric, "受影响模块必须更新为已采纳规则")
        history = current.get("history") or ""
        check("开发者主动 to-spec" in history, "变更必须保留来源")
        check("1 分反馈偏弱" in history, "变更必须保留理由")
        check("每颗星星 1 分" in history, "变更必须保留替代关系")
        task = mgs_records.read_task(root, "01-catch-star")
        baseline = (task.get("request") or {}).get("输入与基线", "")
        check("GAME_DESIGN.md" in baseline and "v2" in baseline,
              f"受影响任务引用必须同步到现行规格:{baseline}")
        check(hashlib.sha256(unpublished.read_bytes()).hexdigest() == draft_sha,
              "未发布草稿必须保持原状态")
        config = mgs_records.load_config(root)
        check(config["backend"] == "local-markdown",
              "本项目必须只使用选定的本地 Markdown tracker")
        work = list((root / "docs/mygamestudio/work").rglob("task.md"))
        check(work, "本地进度必须仍在选定 tracker 的任务记录中")


def test_chinese_module_names_do_not_collide_or_overwrite() -> None:
    """已采纳设计进入按需模块时,中文模块名称不得撞成同一身份并互相覆盖。"""

    with tempfile.TemporaryDirectory() as tmp:
        root = _onboard_local(Path(tmp) / "star-catcher", design=CORE_DESIGN)
        plan = mgs_records.plan_spec_adoption(root, {
            "kind": "new_feature",
            "source": "开发者主动 to-spec",
            "reason": "规则与成长同时落地",
            "overall": {
                "title": "star-catcher：当前游戏需求与设计",
                "version": "v2",
                "core_play": "接星星。接到得 1 分。商店用金币升级。",
                "rules": [
                    "得分：每颗星星 1 分。",
                    "商店：用金币买移动速度。",
                ],
            },
            "modules": {
                "规则与数值": {
                    "title": "规则与数值",
                    "rules": ["每颗星星 1 分。"],
                },
                "成长经济": {
                    "title": "成长经济",
                    "rules": ["金币可在商店购买升级。"],
                },
            },
        })
        applied = mgs_records.apply_spec_adoption(root, plan, confirmed=True)
        check(applied.get("ok") is True, f"两个专业模块应能同时写入:{applied}")
        current = mgs_records.read_current_design(root)
        modules = current.get("modules") or {}
        blob = "\n".join(modules.values())
        check("每颗星星 1 分" in blob, "规则与数值模块内容必须保留")
        check("金币可在商店购买升级" in blob, "成长经济模块内容必须保留")
        check(len(modules) >= 2, f"两个模块必须有各自身份,实际 {list(modules)}")
        identities = list(modules)
        check(len(identities) == len(set(identities)),
              f"模块身份不得碰撞,实际 {identities}")


def test_new_feature_resume_partial_update_and_progress_guard() -> None:
    """AC5: 覆盖新功能、已定规则修改、已有进度保障、部分更新与新会话恢复。
    """

    with tempfile.TemporaryDirectory() as tmp:
        design = CORE_DESIGN + "\n## 持久状态恢复\n\n- 本机保存最高分,重开后仍可读。\n"
        root = _onboard_local(Path(tmp) / "star-catcher", design=design)
        # 新功能:连击,只更新相关正文
        new_plan = mgs_records.plan_spec_adoption(root, {
            "kind": "new_feature",
            "source": "开发者主动 to-spec",
            "reason": "连击让最小闭环更有反馈",
            "replaces": "",
            "overall": {
                "title": "star-catcher：当前游戏需求与设计",
                "version": "v2",
                "core_play": "玩家移动角色接住落下的星星。连续接到可叠连击。漏接三颗结束本局。",
                "rules": [
                    "得分：每颗星星 1 分。",
                    "连击：连续接到时连击加一,漏接清零。",
                    "结束：漏接 3 颗后本局结束。",
                    "操作：方向键左右移动。",
                ],
                "progress_guard": "本机保存最高分,重开后仍可读。",
            },
            "modules": {
                "玩家体验": {
                    "title": "玩家体验",
                    "rules": ["连续接到时连击加一并给出反馈。"],
                },
            },
            "affected_tasks": ["01-catch-star"],
        })
        applied = mgs_records.apply_spec_adoption(root, new_plan, confirmed=True)
        check(applied.get("ok") is True, f"新功能应能写入:{applied}")
        current = mgs_records.read_current_design(root)
        overall = current.get("overall") or ""
        check("连击" in overall, "新功能已采纳规则必须出现在现行正文")
        check("本机保存最高分" in overall, "已有进度保障必须继续保留")
        # 新会话恢复:只读现行规则,不重问已定内容
        resumed = mgs_records.plan_design_discussion(root, {
            "kind": "small_change",
            "request": "只把漏接条数从 3 改成 2。",
            "settled": {
                "core-play": "玩家移动角色接住落下的星星。连续接到可叠连击。漏接三颗结束本局。",
            },
            "questions": [
                {"id": "fail-count", "title": "漏接几颗结束",
                 "depends_on": ["core-play"], "module": "规则与数值"},
                {"id": "core-play", "title": "核心玩法是什么",
                 "depends_on": [], "module": "玩家体验"},
            ],
        })
        shown = [item.get("id") for item in resumed.get("shown_questions") or []]
        check("fail-count" in shown, "新会话应能继续未决的局部小改")
        check("core-play" not in shown, "新会话不得重问已定核心玩法")
        check(resumed.get("retain_progress") is True,
              "已有进度保障必须在后续讨论中继续保留")
        # 部分更新:只改漏接条数
        partial = mgs_records.plan_spec_adoption(root, {
            "kind": "small_change",
            "source": "开发者主动 to-spec",
            "reason": "3 颗太宽,2 颗更紧",
            "replaces": "漏接 3 颗后本局结束",
            "overall": {
                "title": "star-catcher：当前游戏需求与设计",
                "version": "v3",
                "core_play": "玩家移动角色接住落下的星星。连续接到可叠连击。漏接两颗结束本局。",
                "rules": [
                    "结束：漏接 2 颗后本局结束。",
                ],
                "replace_rules": ["漏接 3 颗"],
            },
            "affected_tasks": ["01-catch-star"],
        })
        mgs_records.apply_spec_adoption(root, partial, confirmed=True)
        later = mgs_records.read_current_design(root)
        body = later.get("overall") or ""
        check("漏接 2 颗" in body, "已定规则的局部修改必须进入现行正文")
        check("连击" in body, "部分更新不得重写无关的已采纳功能")
        check("本机保存最高分" in body, "部分更新不得丢掉进度保障")


def _onboard_github(root: Path) -> Path:
    root.mkdir(parents=True, exist_ok=True)
    (root / "README.md").write_text("# star-catcher\n", encoding="utf-8")
    mgs_records.apply_github_onboarding(
        root, mgs_records.plan_github_onboarding(
            root, repo=REPO, authorization=AUTH),
        confirmed=True)
    return root


def test_github_tracker_adopts_spec_and_keeps_history_in_comments() -> None:
    """T5/AC4: GitHub 项目用 Issue 正文承载现行规格、评论承载历史;
    任务引用同步;不把本地 Markdown 升为第二套现行来源。
    """

    with tempfile.TemporaryDirectory() as tmp:
        root = _onboard_github(Path(tmp) / "star-catcher")
        local_design = root / "docs/mygamestudio/GAME_DESIGN.md"
        local_design.parent.mkdir(parents=True, exist_ok=True)
        local_design.write_text("# 本地不是现行\n\n每颗星星 1 分。\n", encoding="utf-8")
        local_sha = hashlib.sha256(local_design.read_bytes()).hexdigest()
        fake = FakeTransport()
        cache = root / "docs/mygamestudio/records/cache"
        mgs_records.create_task(
            root, "01-catch-star", "接住第一颗星星",
            _task_request("接住一颗星星并计分"),
            triage="ready-for-agent", transport=fake, cache_dir=cache)
        plan = mgs_records.plan_spec_adoption(root, {
            "kind": "small_change",
            "source": "开发者主动 to-spec",
            "reason": "正式改为 3 分",
            "replaces": "每颗星星 1 分",
            "overall": {
                "title": "star-catcher 整体设计",
                "version": "v2",
                "core_play": "接星星。接到一颗得 3 分。漏接三颗结束。",
                "rules": [
                    "得分：每颗星星 3 分。",
                    "结束：漏接 3 颗后本局结束。",
                ],
                "replace_rules": ["每颗星星 1 分"],
            },
            "modules": {
                "规则与数值": {"title": "规则与数值", "rules": ["每颗星星 3 分。"]},
            },
            "affected_tasks": ["01-catch-star"],
            "unadopted": ["联网排行榜"],
            "trial_values": [{"id": "star-score", "value": 5, "adopted": False}],
        }, transport=fake, cache_dir=cache)
        applied = mgs_records.apply_spec_adoption(
            root, plan, confirmed=True, transport=fake, cache_dir=cache)
        check(applied.get("ok") is True, f"GitHub to-spec 应写入:{applied}")
        check(applied.get("backend") == "github-issues",
              "GitHub 项目必须写入 GitHub tracker")
        current = mgs_records.read_current_design(
            root, transport=fake, cache_dir=cache)
        overall = current.get("overall") or ""
        check("每颗星星 3 分" in overall, "GitHub 现行规格正文必须是已采纳规则")
        check("联网排行榜" not in overall, "未采纳想法不得进入 GitHub 现行正文")
        check("5 分" not in overall, "试验值不得进入 GitHub 现行正文")
        history = current.get("history") or ""
        check("开发者主动 to-spec" in history, "GitHub 规格评论必须保留来源")
        check("正式改为 3 分" in history, "GitHub 规格评论必须保留理由")
        check("每颗星星 1 分" in history, "GitHub 规格评论必须保留替代关系")
        task = mgs_records.read_task(
            root, "01-catch-star", transport=fake, cache_dir=cache)
        baseline = (task.get("request") or {}).get("输入与基线", "")
        check("spec-overall" in baseline or "#" in baseline,
              f"GitHub 任务必须引用现行规格:{baseline}")
        tasks = mgs_records.list_tasks(root, transport=fake, cache_dir=cache)
        identities = [item.get("identity") for item in tasks]
        check("01-catch-star" in identities, "进度仍在 GitHub 任务中")
        check(all(item.get("identity") for item in tasks),
              "规格 Issue 不得混入任务列表")
        check(hashlib.sha256(local_design.read_bytes()).hexdigest() == local_sha,
              "GitHub 项目不得把本地 GAME_DESIGN.md 改成第二套现行规格")
        work = root / "docs/mygamestudio/work"
        check(not work.exists() or not any(work.rglob("task.md")),
              "GitHub 项目不得另起本地任务账本")
        config = mgs_records.load_config(root)
        check(config["backend"] == "github-issues",
              "本项目必须只使用选定的 GitHub tracker")


def _github_list_newest_first(fake: FakeTransport) -> None:
    """Match GitHub's default issue list: newest number first."""

    original = fake.request

    def request(method, path, body=None, *, auth=None):
        status, data = original(method, path, body, auth=auth)
        clean = path.split("?", 1)[0]
        if method == "GET" and clean.endswith("/issues") and isinstance(data, list):
            return status, list(reversed(data))
        return status, data

    fake.request = request  # type: ignore[method-assign]


def test_github_live_spec_update_does_not_rewrite_archive() -> None:
    """D6: 更新现行规格不得覆盖归档快照,即使列表把新 Issue 排在前面。"""

    with tempfile.TemporaryDirectory() as tmp:
        root = _onboard_github(Path(tmp) / "star-catcher")
        fake = FakeTransport()
        _github_list_newest_first(fake)
        cache = root / "docs/mygamestudio/records/cache"
        first = mgs_records.plan_spec_adoption(root, {
            "kind": "new_feature",
            "source": "开发者主动 to-spec",
            "reason": "冻结 0.1 设计",
            "overall": {
                "title": "star-catcher 整体设计",
                "version": "v1",
                "core_play": "接星星。接到一颗得 1 分。漏接三颗结束。",
                "rules": ["得分：每颗星星 1 分。"],
            },
        }, transport=fake, cache_dir=cache)
        mgs_records.apply_spec_adoption(
            root, first, confirmed=True, transport=fake, cache_dir=cache)
        snap = mgs_records.apply_design_snapshot(root, mgs_records.plan_design_snapshot(root, {
            "trigger": "version_freeze",
            "game_version": "0.1.0",
            "source": "正式版本设计确定",
        }, transport=fake, cache_dir=cache), confirmed=True, transport=fake, cache_dir=cache)
        check(snap.get("ok") is True, f"归档快照应先保存:{snap}")
        archives_before = [item for item in fake.issues
                           if "快照身份:" in (item.get("body") or "")]
        check(archives_before, "本用例需要一份归档 Issue")
        later = mgs_records.plan_spec_adoption(root, {
            "kind": "small_change",
            "source": "开发者主动 to-spec",
            "reason": "正式改为 3 分",
            "replaces": "每颗星星 1 分",
            "overall": {
                "title": "star-catcher 整体设计",
                "version": "v2",
                "core_play": "接星星。接到一颗得 3 分。漏接三颗结束。",
                "rules": ["得分：每颗星星 3 分。"],
                "replace_rules": ["每颗星星 1 分"],
            },
        }, transport=fake, cache_dir=cache)
        applied = mgs_records.apply_spec_adoption(
            root, later, confirmed=True, transport=fake, cache_dir=cache)
        check(applied.get("ok") is True, f"后续现行规格更新应成功:{applied}")
        archives = [item for item in fake.issues
                    if "快照身份:" in (item.get("body") or "")]
        check(archives, "更新现行规格后归档 Issue 必须仍在")
        if not archives:
            return
        check(len(archives) == len(archives_before),
              "更新现行规格不得改写或吞掉归档 Issue")
        check("快照身份:" in (archives[0].get("body") or ""),
              "归档身份不得被现行规格覆盖")
        check("每颗星星 1 分" in (archives[0].get("body") or ""),
              "旧快照正文必须保留当时规则")
        check("每颗星星 3 分" not in (archives[0].get("body") or ""),
              "后续现行设计变化不得写入旧快照")
        current = mgs_records.read_current_design(
            root, transport=fake, cache_dir=cache)
        check("每颗星星 3 分" in (current.get("overall") or ""),
              "现行规格必须更新到新规则")
        check("快照身份:" not in (current.get("overall") or ""),
              "现行读取不得把归档 Issue 当成现行规格")


def test_github_spec_recovery_does_not_claim_success_without_modules() -> None:
    """T10: 现行整体已在时,模块写入失败不得把未完成采纳报成已发布。"""

    with tempfile.TemporaryDirectory() as tmp:
        root = _onboard_github(Path(tmp) / "partial-spec")
        fake = FakeTransport()
        cache = root / "docs/mygamestudio/records/cache"
        first_plan = mgs_records.plan_spec_adoption(root, {
            "kind": "new_feature",
            "source": "开发者主动 to-spec",
            "reason": "先写下最小闭环",
            "overall": {
                "title": "partial 整体设计",
                "version": "v1",
                "core_play": "接星星。",
                "rules": ["得分：每颗星星 1 分。"],
            },
        }, transport=fake, cache_dir=cache)
        first = mgs_records.apply_spec_adoption(
            root, first_plan, confirmed=True, transport=fake, cache_dir=cache)
        check(first.get("ok") is True, f"首次采纳应成功:{first}")
        second_plan = mgs_records.plan_spec_adoption(root, {
            "kind": "small_change",
            "source": "开发者主动 to-spec",
            "reason": "补规则模块",
            "overall": {
                "title": "partial 整体设计",
                "version": "v2",
                "core_play": "接星星。",
                "rules": ["得分：每颗星星 3 分。"],
            },
            "modules": {
                "规则与数值": {"title": "规则与数值", "rules": ["每颗星星 3 分。"]},
            },
        }, transport=fake, cache_dir=cache)
        fake.fail("POST", "/issues", "timeout")
        second = mgs_records.apply_spec_adoption(
            root, second_plan, confirmed=True, transport=fake, cache_dir=cache)
        check(second.get("ok") is not True,
              f"模块未落地不得报告成功:{second}")
        check(second.get("published") is not True,
              f"未完成采纳不得标已发布:{second}")
        current = mgs_records.read_current_design(
            root, transport=fake, cache_dir=cache)
        modules = current.get("modules") or {}
        check("规则与数值" not in modules and "rules" not in modules,
              "失败路径不得假装模块已采纳")


def test_github_module_http_error_does_not_claim_adoption() -> None:
    """模块 POST 返回非 2xx 且不抛异常时,不得把未发布模块报成已采纳。"""

    with tempfile.TemporaryDirectory() as tmp:
        root = _onboard_github(Path(tmp) / "http-module")
        fake = FakeTransport()
        cache = root / "docs/mygamestudio/records/cache"
        plan = mgs_records.plan_spec_adoption(root, {
            "kind": "new_feature",
            "source": "开发者主动 to-spec",
            "reason": "最小闭环加规则模块",
            "overall": {
                "title": "http 整体设计",
                "version": "v1",
                "core_play": "接星星。",
                "rules": ["得分：每颗星星 1 分。"],
            },
            "modules": {
                "规则与数值": {"title": "规则与数值", "rules": ["每颗星星 1 分。"]},
            },
        }, transport=fake, cache_dir=cache)
        fake.http_error("POST", "/issues", 500, body_contains="种类:模块规格")
        applied = mgs_records.apply_spec_adoption(
            root, plan, confirmed=True, transport=fake, cache_dir=cache)
        check(applied.get("ok") is not True,
              f"模块 HTTP 失败不得报告成功:{applied}")
        check(applied.get("published") is not True,
              f"模块未落地不得标已发布:{applied}")
        current = mgs_records.read_current_design(
            root, transport=fake, cache_dir=cache)
        modules = current.get("modules") or {}
        check("rules" not in modules and "规则与数值" not in modules,
              "非 2xx 模块写入不得进入现行规格")


def test_github_history_comment_failure_does_not_claim_adoption() -> None:
    """设计历史评论 POST 返回非 2xx 时不得宣告采用完成:
    权威规格已更新也必须如实报告历史未记录。"""

    with tempfile.TemporaryDirectory() as tmp:
        root = _onboard_github(Path(tmp) / "http-history")
        fake = FakeTransport()
        cache = root / "docs/mygamestudio/records/cache"
        plan = mgs_records.plan_spec_adoption(root, {
            "kind": "new_feature",
            "source": "开发者主动 to-spec",
            "overall": {
                "title": "history 整体设计",
                "version": "v1",
                "core_play": "接星星。",
                "rules": ["得分：每颗星星 1 分。"],
            },
        }, transport=fake, cache_dir=cache)
        fake.http_error("POST", "/comments", 500, body_contains="试验值保持未采纳")
        applied = mgs_records.apply_spec_adoption(
            root, plan, confirmed=True, transport=fake, cache_dir=cache)
        check(applied.get("ok") is not True,
              f"历史评论发布失败不得报告成功:{applied}")
        check(applied.get("published") is not True,
              f"历史未记录不得标已发布:{applied}")
        check("历史" in str(applied.get("reason") or ""),
              f"失败原因必须指明历史未记录:{applied.get('reason')}")
        check(not any("试验值保持未采纳" in (item.get("body") or "")
                      for comments in fake.comments.values()
                      for item in comments),
              "替身中不得存在历史评论(与失败事实一致)")


def test_github_live_spec_inventory_paginates_beyond_first_page() -> None:
    """现行规格盘点必须翻页,不能只看前 100 条 Issue。"""

    with tempfile.TemporaryDirectory() as tmp:
        root = _onboard_github(Path(tmp) / "paged-spec")
        fake = FakeTransport()
        cache = root / "docs/mygamestudio/records/cache"
        for index in range(1, 101):
            fake.seed_issue(f"{index:03d}-pad", f"填充任务 {index}")
        fake.issues.append({
            "number": 101, "id": 1101, "title": "现行规格",
            "body": (
                "规格身份:overall。种类:现行规格。版本:v1。\n\n"
                "## 核心玩法\n\n翻页后仍能读到的现行规格。\n"
            ),
            "labels": [], "assignees": [], "state": "open",
            "state_reason": None, "html_url": "https://example.invalid/i/101",
        })
        fake.comments[101] = []
        current = mgs_records.read_current_design(
            root, transport=fake, cache_dir=cache)
        check("翻页后仍能读到的现行规格" in (current.get("overall") or ""),
              f"超过一页时仍须读到现行规格:{current}")


def test_github_unknown_write_rereads_and_keeps_unpublished_draft() -> None:
    """AC5: 保存未知时回读后补缺,不重复创建;未发布草稿保持原状态。
    """

    with tempfile.TemporaryDirectory() as tmp:
        root = _onboard_github(Path(tmp) / "gap")
        fake = FakeTransport()
        cache = root / "docs/mygamestudio/records/cache"
        adopted = {
            "kind": "new_feature",
            "source": "开发者主动 to-spec",
            "reason": "先写下最小闭环",
            "overall": {
                "title": "gap 整体设计",
                "version": "v1",
                "core_play": "接星星。",
                "rules": ["得分：每颗星星 1 分。"],
            },
        }
        plan = mgs_records.plan_spec_adoption(
            root, adopted, transport=fake, cache_dir=cache)
        fake.drop("POST", "/issues")
        first = mgs_records.apply_spec_adoption(
            root, plan, confirmed=True, transport=fake, cache_dir=cache)
        check(first.get("ok") is True or first.get("published") is False
              or first.get("filled_gap_only") is True,
              f"写入响应丢失后必须回读或保留未知,不得虚报:{first}")
        specs = [item for item in fake.issues
                 if "规格身份:" in (item.get("body") or "")]
        check(len(specs) == 1, f"回读后只应有一份现行规格,实际 {len(specs)}")
        fake._drop.clear()
        again = mgs_records.apply_spec_adoption(
            root, plan, confirmed=True, transport=fake, cache_dir=cache)
        check(again.get("ok") is True, f"重试应补缺或收养已有规格:{again}")
        specs_after = [item for item in fake.issues
                       if "规格身份:" in (item.get("body") or "")
                       and "规格身份:overall" in (item.get("body") or "")]
        check(len(specs_after) == 1,
              f"补缺不得重复创建整体规格,实际 {len(specs_after)}")
        draft_dir = cache / "drafts"
        draft_dir.mkdir(parents=True, exist_ok=True)
        draft = draft_dir / "unpublished-leaderboard.json"
        draft.write_text(
            json.dumps({"status": "未发布草稿", "idea": "联网排行榜"},
                       ensure_ascii=False),
            encoding="utf-8")
        draft_sha = hashlib.sha256(draft.read_bytes()).hexdigest()
        current = mgs_records.read_current_design(
            root, transport=fake, cache_dir=cache)
        check("联网排行榜" not in (current.get("overall") or ""),
              "未发布草稿不得进入正式规则")
        check(hashlib.sha256(draft.read_bytes()).hexdigest() == draft_sha,
              "未发布草稿必须保持原状态")


def test_github_discussion_rounds_append_not_replace() -> None:
    """GitHub 讨论第二轮必须追加到同一 Issue,不得整篇替换旧轮次。"""

    with tempfile.TemporaryDirectory() as tmp:
        root = _onboard_github(Path(tmp) / "star-catcher")
        fake = FakeTransport()
        cache = root / "docs/mygamestudio/records/cache"
        first = mgs_records.plan_design_discussion(root, {
            "kind": "small_change", "request": "调分。",
            "settled": {"core-play": "接星星。"},
            "trial_values": [{"id": "star-score", "value": 3, "adopted": False}],
        }, transport=fake, cache_dir=cache)
        r1 = mgs_records.apply_design_discussion(
            root, first, {"score-value": "先用试验值 3"},
            transport=fake, cache_dir=cache)
        check(r1.get("ok") is True, f"第一轮讨论应保存:{r1}")
        second = mgs_records.plan_design_discussion(root, {
            "kind": "small_change", "request": "再调漏接上限。",
            "settled": {"core-play": "接星星。"},
            "trial_values": [{"id": "miss-limit", "value": 5, "adopted": False}],
        }, transport=fake, cache_dir=cache)
        r2 = mgs_records.apply_design_discussion(
            root, second, {"miss-limit": "先用试验值 5"},
            transport=fake, cache_dir=cache)
        check(r2.get("ok") is True, f"第二轮讨论应保存:{r2}")
        check(r2.get("issue_number") == r1.get("issue_number"),
              "第二轮讨论应写进同一个讨论 Issue")
        _st, issue = fake.request(
            "GET", f"/repos/mygamestudio/issue-accept/issues/{r1['issue_number']}")
        body = (issue or {}).get("body") or ""
        check("star-score" in body and "先用试验值 3" in body,
              "旧轮次的试验值与作答必须保留")
        check("miss-limit" in body and "先用试验值 5" in body,
              "新轮次必须追加到既有正文")


def test_tospec_preserves_unrelated_sections() -> None:
    """to-spec 重建整体规格时,白名单外的既有章节必须原样保留。"""

    with tempfile.TemporaryDirectory() as tmp:
        root = _onboard_local(
            Path(tmp) / "star-catcher",
            design=CORE_DESIGN + "\n## 操作与界面\n\n方向键左右移动。\n")
        plan = mgs_records.plan_spec_adoption(root, {
            "kind": "small_change",
            "source": "开发者主动 to-spec",
            "reason": "调分",
            "overall": {"version": "v2", "rules": ["得分：每颗星星 3 分。"]},
            "modules": {},
        })
        applied = mgs_records.apply_spec_adoption(root, plan, confirmed=True)
        check(applied.get("ok") is True, f"to-spec 应写入:{applied}")
        overall = mgs_records.read_current_design(root).get("overall") or ""
        check("## 操作与界面" in overall and "方向键左右移动" in overall,
              "与本次采纳无关的既有章节不得在重建中被静默删除")
        check("每颗星星 3 分" in overall, "已采纳规则仍应写入")


def test_github_spec_sync_forwards_custom_config_rel() -> None:
    """自定义配置路径下 to-spec 的任务同步必须走同一配置路径。"""

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp) / "star-catcher"
        root.mkdir(parents=True)
        (root / "README.md").write_text("# star-catcher\n", encoding="utf-8")
        make_github_project(root)
        alt = root / "docs/alt/CONFIG.md"
        alt.parent.mkdir(parents=True)
        alt.write_text((root / "docs/mygamestudio/CONFIG.md").read_text(
            encoding="utf-8"), encoding="utf-8")
        (root / "docs/mygamestudio/CONFIG.md").unlink()
        config_rel = "docs/alt/CONFIG.md"
        fake = FakeTransport()
        cache = root / "docs/alt/cache"
        mgs_records.create_task(
            root, "01-catch-star", "接住第一颗星星",
            _task_request("接住一颗星星并计分"),
            triage="ready-for-agent", transport=fake, cache_dir=cache,
            config_rel=config_rel)
        plan = mgs_records.plan_spec_adoption(root, {
            "kind": "small_change",
            "overall": {"version": "v2", "core_play": "接星星。",
                        "rules": ["得分：每颗星星 3 分。"]},
            "modules": {},
            "affected_tasks": ["01-catch-star"],
        }, transport=fake, cache_dir=cache, config_rel=config_rel)
        applied = mgs_records.apply_spec_adoption(
            root, plan, confirmed=True, transport=fake, cache_dir=cache,
            config_rel=config_rel)
        check(applied.get("ok") is True, f"自定义配置路径下 to-spec 应成功:{applied}")
        check(applied.get("updated_tasks") == ["01-catch-star"],
              f"任务同步必须透传配置路径:{applied.get('updated_tasks')}")


def test_github_adoption_reports_unpublished_task_sync() -> None:
    """受影响任务同步只剩未发布草稿时,采用不得宣称完成(published)。"""

    with tempfile.TemporaryDirectory() as tmp:
        root = _onboard_github(Path(tmp) / "task-sync")
        fake = FakeTransport()
        cache = root / "docs/mygamestudio/records/cache"
        mgs_records.create_task(
            root, "01-catch-star", "接住第一颗星星",
            _task_request("接住一颗星星并计分"),
            triage="ready-for-agent", transport=fake, cache_dir=cache)
        task_number = mgs_records.read_task(
            root, "01-catch-star", transport=fake,
            cache_dir=cache).get("issue_number")
        fake.fail("PATCH", f"/issues/{task_number}", "timeout")
        plan = mgs_records.plan_spec_adoption(root, {
            "kind": "small_change",
            "source": "开发者主动 to-spec",
            "reason": "正式改为 3 分",
            "overall": {
                "title": "task-sync 整体设计",
                "version": "v2",
                "core_play": "接星星。接到一颗得 3 分。",
                "rules": ["得分：每颗星星 3 分。"],
            },
            "modules": {
                "规则与数值": {"title": "规则与数值", "rules": ["每颗星星 3 分。"]},
            },
            "affected_tasks": ["01-catch-star"],
        }, transport=fake, cache_dir=cache)
        applied = mgs_records.apply_spec_adoption(
            root, plan, confirmed=True, transport=fake, cache_dir=cache)
        check(applied.get("ok") is False,
              f"任务基线未同步发布不得宣告采用完成:{applied}")
        check(applied.get("published") is False,
              f"未发布不得报 published,实际 {applied.get('published')}")
        check("01-catch-star" in (applied.get("unpublished_tasks") or []),
              f"必须逐个列出未发布的任务,实际 {applied.get('unpublished_tasks')}")
        current = mgs_records.read_current_design(
            root, transport=fake, cache_dir=cache)
        check("每颗星星 3 分" in (current.get("overall") or ""),
              "权威规格的实际更新应如实可见(部分成果不掩盖)")
        task = mgs_records.read_task(
            root, "01-catch-star", transport=fake, cache_dir=cache)
        check("spec-overall" not in str((task.get("request") or {})
                                        .get("输入与基线", "")),
              "任务基线未发布时不得当作已同步")


if __name__ == "__main__":
    TESTS = (
        test_game_and_matt_entries_read_design_stage_requirements,
        test_core_play_then_min_loop_questions,
        test_small_change_reuses_decisions_and_keeps_trial_values_out,
        test_tospec_adopts_into_overall_module_and_task_refs_local,
        test_chinese_module_names_do_not_collide_or_overwrite,
        test_new_feature_resume_partial_update_and_progress_guard,
        test_github_tracker_adopts_spec_and_keeps_history_in_comments,
        test_github_live_spec_update_does_not_rewrite_archive,
        test_github_spec_recovery_does_not_claim_success_without_modules,
        test_github_module_http_error_does_not_claim_adoption,
        test_github_history_comment_failure_does_not_claim_adoption,
        test_github_live_spec_inventory_paginates_beyond_first_page,
        test_github_unknown_write_rereads_and_keeps_unpublished_draft,
        test_github_discussion_rounds_append_not_replace,
        test_tospec_preserves_unrelated_sections,
        test_github_spec_sync_forwards_custom_config_rel,
        test_github_adoption_reports_unpublished_task_sync,
    )
    sys.exit(run_theme("游戏设计讨论与现行规格维护(#53 T2/T3/T5)", TESTS, FAILURES))

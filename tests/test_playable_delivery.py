#!/usr/bin/env python3
"""Issue #56 seams: playable tickets, resource integration and delivery.

Confirmed seams (issue #56 acceptance + #49 T3/T9/T10/T13):
- AC1: game materials reach to-tickets, implement and review; a task has
  starting condition, operation, feedback, outcome and check owner;
  user-only Matt entries start only when the developer invokes them.
- AC2/T3/T9: default path is a minimum loop in the formal project;
  isolated prototype only on explicit request; later reuse still needs
  formal integration and checks; approving a direction is not delivery;
  small changes reuse current decisions; unadopted trial values stay out
  of formal rules; no prototype without an explicit request.
- AC3/T9: code and audiovisual assets ship together by default;
  independent resource tasks complete on file/format/source/preview;
  in-game integration has a separate owner and check.
- AC4/T13: existing tool, equivalent substitute, and missing-tool handoff
  each have a correct result; missing tools do not install, pay, or lower
  the requirement, and unrelated work continues.
- AC5/T9: editor run vs actual build follows delivery risk; results name
  version, launch and check scope; implementation errors fix the
  implementation; design changes wait for confirmation.
- AC6/T9/T10: normal delivery, missing resource, unavailable tool,
  explicit prototype, build difference, cancel and resume; agreed
  playtest not yet done stays waiting and is not closed as accepted;
  no dedicated demo game; ordinary path needs no mgs-gate.

Expected values come from issues #56 and #49 D1/D3/D4/D5/D7/D8/D10.
Do not assert internal functions, directory counts, or prompt keywords.

    python3 -B tests/test_playable_delivery.py
"""

from __future__ import annotations

import sys
import tempfile
from pathlib import Path

from github_backend_fixtures import AUTH, REPO, make_checker, run_theme
from github_backend_transport import FakeTransport
from redesign_bundle_contract import STAGE_REQUIREMENTS_REL

import mgs_records  # noqa: E402

FAILURES, check = make_checker()
REPO_ROOT = Path(__file__).resolve().parents[1]
PLUGIN_ROOT = REPO_ROOT / "plugin"
STAGE = PLUGIN_ROOT / STAGE_REQUIREMENTS_REL
INVOCATION = PLUGIN_ROOT / "internal" / "game" / "invocation.md"

CORE_DESIGN = """# star-catcher：当前游戏需求与设计

维护责任：方案设计。基线版本：v1。适用范围：最小闭环。采用依据：开发者决定。

## 核心玩法

玩家移动角色接住落下的星星。接到一颗得 1 分。漏接三颗结束本局。

## 当前规则与流程

- 得分：每颗星星 1 分。
- 结束：漏接 3 颗后本局结束。
- 操作：方向键左右移动。
"""


def _task_request(goal: str) -> dict:
    return {
        "当前目标": goal,
        "输入与基线": "GAME_DESIGN.md v1",
        "本次交付": "可回读的任务记录",
        "允许修改范围": "src/**",
        "所需能力": "文件读写",
        "完成标准": "记录可回读",
        "执行责任": "Agent(制作实现)",
        "验收方式": "代码级检查",
        "依赖": "无",
    }


def _onboard_local(root: Path, *, design: str = CORE_DESIGN) -> Path:
    root.mkdir(parents=True, exist_ok=True)
    (root / "README.md").write_text("# star-catcher\n\n接星星。\n", encoding="utf-8")
    mgs_records.apply_local_onboarding(
        root, mgs_records.plan_local_onboarding(root), confirmed=True)
    design_path = root / "docs/mygamestudio/GAME_DESIGN.md"
    design_path.parent.mkdir(parents=True, exist_ok=True)
    design_path.write_text(design, encoding="utf-8")
    mgs_records.create_task(
        root, "01-catch-star", "接住第一颗星星",
        _task_request("接住一颗星星并计分"))
    return root


def _feature_request(**extra) -> dict:
    request = {
        "kind": "feature",
        "identity": "02-catch-loop",
        "title": "接住一颗星星并计分",
        "starting_state": "标题画面,尚未开始一局",
        "operation": "按左右方向键移动角色并接住一颗落下的星星",
        "feedback": "接到后加 1 分并播放接住音效",
        "outcome": "正式工程中最小闭环可运行,含星星贴图与接住音效",
        "check_owner": "制作实现运行 src/index.html 并核对计分与音效",
        "resources": [
            {"path": "assets/star.png", "kind": "visual"},
            {"path": "assets/catch.wav", "kind": "audio"},
        ],
        "explicit_prototype": False,
        "independent_resource": False,
        "tools": {"needed": "文件读写", "available": ["文件读写"]},
        "risk": "editor",
        "playtest_required": False,
        "playtest_done": False,
        "trial_values": [],
        "small_change": False,
    }
    request.update(extra)
    return request


def _ticket_fields(plan: dict) -> dict:
    tickets = plan.get("tickets") or []
    return tickets[0] if tickets else {}


# --- AC1: stage materials and task fields ------------------------------------


def test_tickets_implement_review_carry_playable_task_fields() -> None:
    """AC1: 游戏资料贯通 to-tickets、implement 和评审;
    任务具有起始条件、操作、反馈、成果与检查责任;
    用户专用入口由开发者主动调用。
    """

    check(STAGE.is_file(), f"缺少阶段资料入口 {STAGE_REQUIREMENTS_REL}")
    text = STAGE.read_text(encoding="utf-8") if STAGE.is_file() else ""
    task_section = ""
    if "## 任务" in text:
        task_section = text.split("## 任务", 1)[1].split("## ", 1)[0]
    check(task_section, "阶段资料必须有任务一节,作为拆票与实现要求的唯一副本")
    for token in ("起始条件", "操作", "反馈", "成果", "检查责任"):
        check(token in task_section,
              f"任务阶段要求必须写明 {token}")
    check("to-tickets" in task_section and "implement" in task_section,
          "任务阶段要求必须贯通 to-tickets 与 implement")
    review_section = ""
    if "## 评审" in text:
        review_section = text.split("## 评审", 1)[1].split("## ", 1)[0]
    check("code-review" in review_section or "评审" in review_section,
          "阶段资料必须贯通评审")
    pointer = "../../internal/game/stage-requirements.md"
    for name in ("to-tickets", "implement", "code-review"):
        skill = PLUGIN_ROOT / "skills" / name / "SKILL.md"
        body = skill.read_text(encoding="utf-8") if skill.is_file() else ""
        check(pointer in body or STAGE_REQUIREMENTS_REL in body,
              f"{name} 必须能从入口读到当前阶段资料")
    invocation = INVOCATION.read_text(encoding="utf-8") if INVOCATION.is_file() else ""
    user_only = invocation.split("## User-only Matt skills", 1)[-1].split("## ", 1)[0]
    check("to-tickets" in user_only and "implement" in user_only,
          "to-tickets 与 implement 必须仍是开发者主动调用的用户专用入口")

    with tempfile.TemporaryDirectory() as tmp:
        root = _onboard_local(Path(tmp) / "star-catcher")
        plan = mgs_records.plan_playable_delivery(root, _feature_request())
        check(plan.get("wrote") is False, "拆票计划阶段不得写入")
        check(plan.get("gate_required") is False, "普通可玩交付不得依赖 gate")
        check(plan.get("auto_invoke_user_entries") is False,
              "不得自动串调 to-tickets / implement 等用户专用入口")
        ticket = _ticket_fields(plan)
        check(ticket.get("起始条件") == "标题画面,尚未开始一局",
              f"任务必须有起始条件,实际 {ticket}")
        check(ticket.get("操作") == "按左右方向键移动角色并接住一颗落下的星星",
              "任务必须有可演示的操作")
        check(ticket.get("反馈") == "接到后加 1 分并播放接住音效",
              "任务必须有反馈")
        check(ticket.get("成果") == "正式工程中最小闭环可运行,含星星贴图与接住音效",
              "任务必须有成果")
        check(ticket.get("检查责任") == "制作实现运行 src/index.html 并核对计分与音效",
              "任务必须有检查责任")
        applied = mgs_records.apply_playable_delivery(root, plan, confirmed=True)
        check(applied.get("ok") is True, f"确认后应写入可玩任务:{applied}")
        task = mgs_records.read_task(root, "02-catch-loop")
        request = task.get("request") or {}
        check(request.get("起始条件") == "标题画面,尚未开始一局",
              f"写入后任务必须仍有起始条件:{request}")
        check(request.get("操作"), "写入后任务必须仍有操作")
        check(request.get("反馈"), "写入后任务必须仍有反馈")
        check(request.get("成果"), "写入后任务必须仍有成果")
        check(request.get("检查责任"), "写入后任务必须仍有检查责任")


# --- AC2 / T3 / T9: formal default, explicit prototype, reuse ----------------


def test_formal_default_explicit_prototype_and_reuse_are_not_delivery() -> None:
    """AC2/T3/T9: 默认正式工程最小闭环;明确要求才做隔离原型;
    原型复用仍要正式集成与检查;认可方向不是正式交付;
    小改动复用当前决定;未采纳试验值不进正式规则;
    无显式请求不增加隔离原型。
    """

    text = STAGE.read_text(encoding="utf-8") if STAGE.is_file() else ""
    proto_section = ""
    if "## 原型" in text:
        proto_section = text.split("## 原型", 1)[1].split("## ", 1)[0]
    check(proto_section, "阶段资料必须有原型一节")
    check("明确" in proto_section, "隔离原型必须仅在明确要求时制作")
    check("正式" in proto_section and ("复用" in proto_section or "集成" in proto_section),
          "原型复用必须进入正式集成")
    check("不等于" in proto_section or "不是正式" in proto_section,
          "方向认可不得自动表示正式交付")
    pointer = "../../internal/game/stage-requirements.md"
    proto_skill = PLUGIN_ROOT / "skills" / "prototype" / "SKILL.md"
    proto_body = proto_skill.read_text(encoding="utf-8") if proto_skill.is_file() else ""
    check(pointer in proto_body or STAGE_REQUIREMENTS_REL in proto_body,
          "prototype 必须能从入口读到当前阶段资料")

    with tempfile.TemporaryDirectory() as tmp:
        root = _onboard_local(Path(tmp) / "star-catcher")
        before = (root / "docs/mygamestudio/GAME_DESIGN.md").read_text(encoding="utf-8")
        default = mgs_records.plan_playable_delivery(root, _feature_request(
            kind="small_change",
            small_change=True,
            trial_values=[{"id": "star-score", "value": 3, "adopted": False}],
        ))
        check(default.get("target") == "formal_project",
              "已说清楚的玩法默认在正式工程实现")
        check(default.get("prototype_added") is False,
              "无显式请求不得增加隔离原型")
        check(default.get("reuse_current") is True,
              "明确小改动必须复用当前已采纳决定")
        check(default.get("formal_delivery_complete") is not True,
              "计划阶段不得把尚未实现标成正式交付完成")
        trials = default.get("trial_values") or []
        check(any(item.get("value") == 3 and item.get("adopted") is False
                  for item in trials),
              "试验值必须清楚展示且标明未经采纳")
        mgs_records.apply_playable_delivery(root, default, confirmed=True)
        design_now = (root / "docs/mygamestudio/GAME_DESIGN.md").read_text(
            encoding="utf-8")
        check(design_now == before, "可玩实现不得把未采纳试验值写入正式规则")
        check("3 分" not in design_now, "未采纳试验值不得进入正式规则")

        proto = mgs_records.plan_playable_delivery(root, _feature_request(
            identity="03-dash-proto",
            title="冲刺手感隔离原型",
            explicit_prototype=True,
            kind="explicit_prototype",
        ))
        check(proto.get("target") == "isolated_prototype",
              "明确要求时才制作隔离原型")
        check(proto.get("prototype_added") is True, "显式请求应增加隔离原型")
        check(proto.get("formal_delivery_complete") is not True,
              "原型可运行不得标成正式交付")
        applied_proto = mgs_records.apply_playable_delivery(
            root, proto, confirmed=True)
        check(applied_proto.get("formal_delivery_complete") is not True,
              "隔离原型写入后仍不是正式交付")

        reuse = mgs_records.plan_playable_delivery(root, _feature_request(
            identity="04-dash-integrate",
            title="把冲刺复用进正式工程",
            explicit_prototype=False,
            direction_approved=True,
            reuse_prototype={"identity": "03-dash-proto"},
        ))
        check(reuse.get("target") == "formal_project",
              "方向认可后应由正式实现任务承接")
        check(reuse.get("reuse_prototype") is True,
              "适用原型应进入正式复用")
        check(reuse.get("needs_formal_integration") is True,
              "复用后仍要正式集成与必要检查")
        check(reuse.get("formal_delivery_complete") is not True,
              "认可方向不自动表示正式交付")
        check(reuse.get("prototype_added") is False,
              "复用正式工程时不得再新增隔离原型")


# --- AC3 / T9: resources together vs independent -----------------------------


def test_resources_together_versus_independent_file_and_in_game_checks() -> None:
    """AC3/T9: 功能所需代码与视听资源默认共同交付;
    独立资源任务核对格式、来源、预览或播放,并明确功能接入责任与游戏内检查。
    """

    with tempfile.TemporaryDirectory() as tmp:
        root = _onboard_local(Path(tmp) / "star-catcher")
        together = mgs_records.plan_playable_delivery(root, _feature_request())
        check(together.get("resource_mode") == "together",
              "默认功能代码与视听资源共同交付")
        tickets = together.get("tickets") or []
        check(len(tickets) == 1, "共同交付应是同一功能任务,不默认拆独立资源票")
        check(tickets[0].get("completion_kind") == "in_game",
              "共同交付的完成条件是游戏内接入与检查")
        check("assets/star.png" in str(tickets[0].get("resources") or tickets[0]),
              "共同交付必须带上所需视听资源")

        independent = mgs_records.plan_playable_delivery(root, _feature_request(
            identity="05-star-sprite",
            title="星星贴图",
            independent_resource=True,
            kind="independent_resource",
            resources=[{"path": "assets/star.png", "kind": "visual",
                        "format": "png", "source": "手工绘制",
                        "preview": "open assets/star.png"}],
            integration_identity="06-star-in-game",
            integration_owner="制作实现在 src/index.html 引用贴图并检查游戏内显示",
        ))
        check(independent.get("resource_mode") == "independent",
              "确需独立资源任务时才拆开")
        kinds = {item.get("completion_kind"): item
                 for item in independent.get("tickets") or []}
        file_ticket = kinds.get("file_ready") or {}
        game_ticket = kinds.get("in_game") or {}
        check(file_ticket, "独立资源任务完成条件是文件、格式、来源与预览或播放")
        check("png" in str(file_ticket.get("format") or file_ticket),
              "独立资源任务必须核对格式")
        check("手工绘制" in str(file_ticket.get("source") or file_ticket),
              "独立资源任务必须核对来源")
        check("open assets/star.png" in str(file_ticket.get("preview") or file_ticket),
              "独立资源任务必须核对预览或播放")
        check(game_ticket, "必须另有功能接入任务承担游戏内检查")
        check("06-star-in-game" in str(game_ticket.get("identity") or ""),
              "功能接入责任必须落到明确任务")
        check("游戏内" in str(game_ticket.get("检查责任") or game_ticket.get("title") or ""),
              "接入任务必须承担游戏内检查")
        check(file_ticket.get("identity") != game_ticket.get("identity"),
              "资源文件完成与游戏内接入完成条件必须分开")
        applied = mgs_records.apply_playable_delivery(
            root, independent, confirmed=True)
        check(applied.get("ok") is True, f"独立资源与接入任务应能写入:{applied}")
        resource_task = mgs_records.read_task(root, file_ticket["identity"])
        integrate_task = mgs_records.read_task(root, game_ticket["identity"])
        check((resource_task.get("request") or {}).get("成果"),
              "资源任务写入后仍可回读成果")
        check((resource_task.get("request") or {}).get("format") == "png",
              "独立资源任务写入后必须仍可回读格式")
        check((resource_task.get("request") or {}).get("source") == "手工绘制",
              "独立资源任务写入后必须仍可回读来源")
        check((resource_task.get("request") or {}).get("preview") == "open assets/star.png",
              "独立资源任务写入后必须仍可回读预览或播放")
        check((integrate_task.get("request") or {}).get("检查责任"),
              "接入任务写入后仍可回读检查责任")
        check(file_ticket.get("identity") in str(
            (integrate_task.get("request") or {}).get("依赖") or ""),
              "游戏内接入任务必须依赖资源文件任务")
        ready = mgs_records.startable_tasks(root)
        startable_ids = {item.get("identity") for item in ready.get("startable") or []}
        check(file_ticket.get("identity") in startable_ids,
              "资源文件任务在依赖完成后应可开工")
        check(game_ticket.get("identity") not in startable_ids,
              "资源文件未完成时游戏内接入不得进入可开工集合")


# --- AC4 / T13: existing tool, substitute, missing handoff -------------------


def test_existing_substitute_and_missing_tools_have_correct_outcomes() -> None:
    """AC4/T13: 现有工具、等效替代和无替代三种路径均有正确结果或具体交接;
    无替代时继续不受影响工作,不默认安装、付费或降低要求。
    """

    with tempfile.TemporaryDirectory() as tmp:
        root = _onboard_local(Path(tmp) / "star-catcher")
        existing = mgs_records.plan_playable_delivery(root, _feature_request(
            tools={"needed": "ffmpeg", "available": ["ffmpeg"]},
        ))
        check(existing.get("tool_path") == "existing",
              "已有授权工具满足要求时应走现有工具")
        check(existing.get("install_by_default") is not True,
              "有现成工具时不得默认安装")

        substitute = mgs_records.plan_playable_delivery(root, _feature_request(
            tools={"needed": "ffmpeg", "available": ["afconvert"],
                   "substitute": "afconvert"},
        ))
        check(substitute.get("tool_path") == "substitute",
              "等效替代满足相同要求时应可继续")
        check(substitute.get("selected_tool") == "afconvert",
              "替代路径必须落到实际可用工具")

        missing = mgs_records.plan_playable_delivery(root, _feature_request(
            identity="07-warning-sfx",
            tools={"needed": "ffmpeg", "available": ["文件读写"]},
            unaffected_identity="02-catch-loop",
        ))
        check(missing.get("tool_path") == "missing_handoff",
              "无替代时必须给出具体交接")
        handoff = missing.get("handoff") or {}
        for key in ("missing_capability", "blocked_step", "required_input",
                    "expected_outcome", "return_check"):
            check(handoff.get(key), f"缺项交接必须包含 {key}")
        check(missing.get("continue_unaffected") is True,
              "无替代时必须继续不受影响的工作")
        check(missing.get("install_by_default") is False,
              "不得默认安装工具")
        check(missing.get("pay_by_default") is False, "不得默认付费")
        check(missing.get("lower_requirements") is False,
              "不得因缺工具降低交付要求")
        applied = mgs_records.apply_playable_delivery(root, missing, confirmed=True)
        check(applied.get("ok") is True, f"缺工具任务仍应记录交接:{applied}")
        task = mgs_records.read_task(root, "07-warning-sfx")
        request = task.get("request") or {}
        check("ffmpeg" in str(request), "缺项必须写在任务记录中供交接")


# --- AC5 / T9: risk, version, implementation vs design -----------------------


def test_risk_selects_run_or_build_and_keeps_trial_out_of_rules() -> None:
    """AC5/T9: 按交付风险使用开发运行或实际构建,提供版本、启动方式和检查范围;
    实现错误修实现,设计变化先确认,试验值与正式规则分开。
    """

    with tempfile.TemporaryDirectory() as tmp:
        root = _onboard_local(Path(tmp) / "star-catcher")
        before = (root / "docs/mygamestudio/GAME_DESIGN.md").read_text(encoding="utf-8")
        editor = mgs_records.plan_playable_delivery(root, _feature_request(
            risk="editor"))
        check(editor.get("check_mode") == "editor_run",
              "日常试调应使用开发运行")
        build = mgs_records.plan_playable_delivery(root, _feature_request(
            identity="08-package",
            risk="install_package"))
        check(build.get("check_mode") == "actual_build",
              "交付安装包相关时应检查实际构建")
        device = mgs_records.plan_playable_delivery(root, _feature_request(
            identity="09-touch", risk="device"))
        check(device.get("check_mode") == "actual_build",
              "目标设备操作相关时应检查实际构建")
        platform = mgs_records.plan_playable_delivery(root, _feature_request(
            identity="10-export", risk="platform_diff"))
        check(platform.get("check_mode") == "actual_build",
              "平台差异相关时应检查实际构建")

        impl = mgs_records.plan_playable_delivery(root, _feature_request(
            identity="11-score-bug", error_kind="implementation"))
        check(impl.get("fix_target") == "implementation",
              "行为偏离已定规则时修实现")
        design = mgs_records.plan_playable_delivery(root, _feature_request(
            identity="12-score-rule", error_kind="design",
            trial_values=[{"id": "star-score", "value": 5, "adopted": False}]))
        check(design.get("fix_target") == "design_confirm",
              "玩法要改变时先确认设计")
        mgs_records.apply_playable_delivery(root, editor, confirmed=True)
        recorded = mgs_records.record_playable_result(root, "02-catch-loop", {
            "version": "src@local-v1",
            "launch": "open src/index.html",
            "check_scope": "接住一颗星星并计分",
            "status": "delivered",
        })
        check(recorded.get("ok") is True, f"应能记录实际检查:{recorded}")
        check(recorded.get("version") == "src@local-v1", "结果必须提供实际版本")
        check(recorded.get("launch") == "open src/index.html",
              "结果必须提供启动方式")
        check(recorded.get("check_scope") == "接住一颗星星并计分",
              "结果必须提供检查范围")
        task = mgs_records.read_task(root, "02-catch-loop")
        index = str(task.get("result_index_text") or task.get("results") or task)
        check("results/" in index or "src@local-v1" in str(task),
              f"版本与检查必须落到对应任务:{task}")
        design_now = (root / "docs/mygamestudio/GAME_DESIGN.md").read_text(
            encoding="utf-8")
        check(design_now == before, "实现结果不得把试验值或设计改动写进正式规则")


# --- AC6 / T9 / T10: technical cases -----------------------------------------


def test_delivered_result_never_complete_while_unpublished() -> None:
    """AC5: 结果只落成未发布草稿时,不得宣告正式交付完成或验收关闭。"""

    from github_backend_fixtures import make_github_project

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp) / "star-catcher"
        root.mkdir(parents=True)
        (root / "README.md").write_text("# star-catcher\n", encoding="utf-8")
        make_github_project(root)
        fake = FakeTransport()
        cache = root / "docs/mygamestudio/records/cache"
        mgs_records.create_task(
            root, "01-catch-star", "接住第一颗星星",
            _task_request("接住一颗星星并计分"),
            triage="ready-for-agent", transport=fake, cache_dir=cache)
        mgs_records.list_tasks(root, transport=fake, cache_dir=cache)
        fake.offline()
        recorded = mgs_records.record_playable_result(root, "01-catch-star", {
            "version": "src@v1", "launch": "open src/index.html",
            "check_scope": "接住星星", "status": "delivered",
        }, transport=fake, cache_dir=cache)
        check(recorded.get("published") is False,
              f"断连注入后结果应只有未发布草稿:{recorded}")
        check(recorded.get("formal_delivery_complete") is False,
              "证据未到达现行账本不得宣告正式交付完成")
        check(recorded.get("close_as_accepted") is False,
              "未发布的结果不得按验收关闭任务")
        check("未发布草稿" in str(recorded.get("reason") or ""),
              f"必须报告草稿/部分失败而不是静默成功:{recorded.get('reason')}")


def test_delivery_cases_keep_waiting_and_preserve_on_cancel() -> None:
    """AC6/T9/T10: 正常交付、缺失资源、工具不可用、明确原型、构建差异、
    取消及续作;约定试玩未发生时保留等待,不关闭为已验收;
    不要求新建专用演示游戏;无 gate。
    """

    with tempfile.TemporaryDirectory() as tmp:
        root = _onboard_local(Path(tmp) / "star-catcher")
        normal = mgs_records.plan_playable_delivery(root, _feature_request())
        check(normal.get("gate_required") is False, "普通路径不得要求 mgs-gate")
        check(normal.get("demo_game_required") is False,
              "不要求新建专用演示游戏")
        applied = mgs_records.apply_playable_delivery(root, normal, confirmed=True)
        delivered = mgs_records.record_playable_result(root, "02-catch-loop", {
            "version": "src@v1", "launch": "open src/index.html",
            "check_scope": "接住星星", "status": "delivered",
        })
        check(delivered.get("status") == "delivered", "正常交付必须可记录")

        missing = mgs_records.record_playable_result(root, "02-catch-loop", {
            "status": "missing_resource",
            "missing": "assets/catch.wav",
            "version": "src@v1", "launch": "open src/index.html",
            "check_scope": "音效接入",
        })
        check(missing.get("status") == "missing_resource",
              "缺失资源必须如实记录")
        check(missing.get("close_as_accepted") is False,
              "缺失资源不得关闭为已验收")
        check(missing.get("formal_delivery_complete") is not True,
              "缺失资源不是正常交付完成")

        unavailable = mgs_records.plan_playable_delivery(root, _feature_request(
            identity="13-audio",
            tools={"needed": "ffmpeg", "available": []}))
        check(unavailable.get("tool_path") == "missing_handoff",
              "工具不可用必须走缺项交接")

        proto = mgs_records.plan_playable_delivery(root, _feature_request(
            identity="14-proto", explicit_prototype=True))
        check(proto.get("target") == "isolated_prototype", "明确原型必须隔离")
        check(proto.get("formal_delivery_complete") is not True,
              "明确原型不是正式交付")

        diff = mgs_records.plan_playable_delivery(root, _feature_request(
            identity="15-build", risk="platform_diff"))
        check(diff.get("check_mode") == "actual_build",
              "构建差异必须检查实际构建")

        cancelled = mgs_records.record_playable_result(root, "02-catch-loop", {
            "status": "cancelled",
            "version": "src@v1", "launch": "open src/index.html",
            "check_scope": "已发出的接入",
        })
        check(cancelled.get("cancelled") is True, "取消后必须停止新动作")
        check(cancelled.get("preserved") is True, "取消必须保存已有成果")
        check(cancelled.get("restored") is False, "取消不等于自动回滚")
        try:
            mgs_records.apply_playable_delivery(root, mgs_records.plan_playable_delivery(
                root, _feature_request(identity="02-catch-loop",
                                       title="撤销后不得重做")),
                confirmed=True)
            check(False, "取消后不得启动被撤销范围的新写入")
        except Exception as exc:
            check("撤销" in str(exc) or "cancel" in str(exc).lower(),
                  f"取消后新动作必须被拒绝:{exc}")
        resumed = mgs_records.record_playable_result(root, "01-catch-star", {
            "status": "continue",
            "version": "src@v1", "launch": "open src/index.html",
            "check_scope": "未撤销范围继续",
        })
        check(resumed.get("ok") is True, f"续作应保存不受影响成果:{resumed}")
        check(resumed.get("preserved") is True, "续作必须保存已有成果")

        waiting = mgs_records.plan_playable_delivery(root, _feature_request(
            identity="16-playtest",
            playtest_required=True, playtest_done=False))
        check(waiting.get("keep_waiting") is True,
              "约定试玩未发生时必须保留等待")
        check(waiting.get("close_as_accepted") is False,
              "约定试玩未发生时不得关闭为已验收")
        check(waiting.get("demo_game_required") is False,
              "等待试玩不要求新建专用演示游戏")
        mgs_records.apply_playable_delivery(root, waiting, confirmed=True)
        wait_result = mgs_records.record_playable_result(root, "16-playtest", {
            "status": "waiting_playtest",
            "playtest_required": True, "playtest_done": False,
            "version": "src@v1", "launch": "open src/index.html",
            "check_scope": "开发者试玩判断",
        })
        check(wait_result.get("close_as_accepted") is False,
              "记录等待时不得关闭为已验收")
        check(wait_result.get("keep_waiting") is True,
              "试玩未发生必须保持开放等待")
        task = mgs_records.read_task(root, "16-playtest")
        progress = task.get("progress") or ""
        check(progress not in ("已完成", "已完成(已有成果覆盖)"),
              f"试玩未发生时进度不得变成已验收:{progress}")
        still = mgs_records.read_task(root, "02-catch-loop")
        check(still.get("identity") == "02-catch-loop",
              "取消后已有任务成果必须仍可回读")


def _onboard_github(root: Path) -> Path:
    root.mkdir(parents=True, exist_ok=True)
    (root / "README.md").write_text("# star-catcher\n", encoding="utf-8")
    mgs_records.apply_github_onboarding(
        root, mgs_records.plan_github_onboarding(
            root, repo=REPO, authorization=AUTH),
        confirmed=True)
    return root


def test_github_playable_task_stays_on_selected_tracker() -> None:
    """AC1/D5: GitHub 项目把可玩任务写到选定 tracker,不另起本地账本。"""

    with tempfile.TemporaryDirectory() as tmp:
        root = _onboard_github(Path(tmp) / "star-catcher")
        fake = FakeTransport()
        cache = root / "docs/mygamestudio/records/cache"
        plan = mgs_records.plan_playable_delivery(
            root, _feature_request(), transport=fake, cache_dir=cache)
        check(plan.get("gate_required") is False, "GitHub 普通路径也不得依赖 gate")
        applied = mgs_records.apply_playable_delivery(
            root, plan, confirmed=True, transport=fake, cache_dir=cache)
        check(applied.get("ok") is True, f"GitHub 可玩任务应写入:{applied}")
        task = mgs_records.read_task(
            root, "02-catch-loop", transport=fake, cache_dir=cache)
        request = task.get("request") or {}
        check(request.get("起始条件"), f"GitHub 任务必须有起始条件:{request}")
        check(request.get("操作"), "GitHub 任务必须有操作")
        check(request.get("检查责任"), "GitHub 任务必须有检查责任")
        recorded = mgs_records.record_playable_result(
            root, "02-catch-loop", {
                "version": "build#12",
                "launch": "play build/index.html",
                "check_scope": "接住星星",
                "status": "delivered",
            }, transport=fake, cache_dir=cache)
        check(recorded.get("version") == "build#12",
              "GitHub 结果必须带回实际版本")
        work = root / "docs/mygamestudio/work"
        check(not work.exists() or not any(work.rglob("task.md")),
              "GitHub 项目不得另起本地任务账本")
        config = mgs_records.load_config(root)
        check(config["backend"] == "github-issues",
              "本项目必须只使用选定的 GitHub tracker")


def test_apply_reports_failure_when_tickets_stay_drafts() -> None:
    """工单未全部到达现行账本(远端离线只存草稿)时,拆票应用必须
    报告失败并列出未到达工单,不得宣称已应用。"""

    with tempfile.TemporaryDirectory() as tmp:
        root = _onboard_github(Path(tmp) / "drafted")
        fake = FakeTransport()
        cache = root / "docs/mygamestudio/records/cache"
        plan = mgs_records.plan_playable_delivery(
            root, _feature_request(
                identity="05-star-sprite",
                title="星星贴图",
                independent_resource=True,
                kind="independent_resource",
                resources=[{"path": "assets/star.png", "kind": "visual",
                            "format": "png", "source": "手工绘制",
                            "preview": "open assets/star.png"}],
                integration_identity="06-star-in-game",
            ), transport=fake, cache_dir=cache)
        fake.offline()
        applied = mgs_records.apply_playable_delivery(
            root, plan, confirmed=True, transport=fake, cache_dir=cache)
        check(applied.get("ok") is not True,
              f"全部工单都是未发布草稿时不得报告成功:{applied}")
        check(applied.get("formal_delivery_complete") is not True,
              "草稿状态不得宣告正式交付")
        unreached = [item.get("identity") for item in applied.get("created") or []
                     if not (item.get("created") or item.get("adopted"))
                     or item.get("published") is False]
        check(set(unreached) == {"05-star-sprite", "06-star-in-game"},
              f"未到达工单必须逐条列出,实际 {unreached}")
        check("05-star-sprite" in (applied.get("reason") or ""),
              "失败原因必须指明未到达的工单")


if __name__ == "__main__":
    TESTS = (
        test_tickets_implement_review_carry_playable_task_fields,
        test_formal_default_explicit_prototype_and_reuse_are_not_delivery,
        test_resources_together_versus_independent_file_and_in_game_checks,
        test_existing_substitute_and_missing_tools_have_correct_outcomes,
        test_risk_selects_run_or_build_and_keeps_trial_out_of_rules,
        test_delivered_result_never_complete_while_unpublished,
        test_delivery_cases_keep_waiting_and_preserve_on_cancel,
        test_github_playable_task_stays_on_selected_tracker,
        test_apply_reports_failure_when_tickets_stay_drafts,
    )
    sys.exit(run_theme("可玩任务拆分、资源集成与交付(#56 T3/T9/T10/T13)", TESTS, FAILURES))

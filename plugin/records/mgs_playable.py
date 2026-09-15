#!/usr/bin/env python3
"""可玩任务拆分、资源集成与交付公开接缝(issue #56)。

明确设计经开发者主动 to-tickets 后,implement 在正式工程完成小范围
功能,接入资源并记录实际检查、运行入口与反馈去向。两种 tracker 分别
读写;普通路径不经 mgs-gate。

公开 interface(经 mgs_records 再导出):
  plan_playable_delivery(project_root, request, ...) -> dict
  apply_playable_delivery(project_root, plan, ...) -> dict
  record_playable_result(project_root, identity, result, ...) -> dict
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))

from mgs_record_source import DEFAULT_CONFIG_REL, load_config  # noqa: E402

USER_ONLY = ("to-tickets", "implement")


def _config(project_root: Path | str, config_rel: str) -> tuple[Path, dict]:
    root = Path(project_root)
    config = load_config(root, config_rel)
    config = dict(config)
    config["project_root"] = str(root)
    return root, config


def _ticket_from_request(request: dict) -> dict[str, Any]:
    resources = list(request.get("resources") or [])
    ticket = {
        "identity": str(request.get("identity") or "02-playable"),
        "title": str(request.get("title") or "可玩切片"),
        "kind": str(request.get("kind") or "feature"),
        "起始条件": str(request.get("starting_state") or ""),
        "操作": str(request.get("operation") or ""),
        "反馈": str(request.get("feedback") or ""),
        "成果": str(request.get("outcome") or ""),
        "检查责任": str(request.get("check_owner") or ""),
        "completion_kind": "in_game",
        "resources": resources,
    }
    return ticket


def _tool_decision(request: dict) -> dict[str, Any]:
    tools = dict(request.get("tools") or {})
    needed = str(tools.get("needed") or "")
    available = [str(item) for item in (tools.get("available") or [])]
    substitute = str(tools.get("substitute") or "")
    if needed and needed in available:
        return {
            "tool_path": "existing",
            "selected_tool": needed,
            "handoff": {},
            "continue_unaffected": True,
            "install_by_default": False,
            "pay_by_default": False,
            "lower_requirements": False,
        }
    if substitute and substitute in available:
        return {
            "tool_path": "substitute",
            "selected_tool": substitute,
            "handoff": {},
            "continue_unaffected": True,
            "install_by_default": False,
            "pay_by_default": False,
            "lower_requirements": False,
        }
    return {
        "tool_path": "missing_handoff",
        "selected_tool": "",
        "handoff": {
            "missing_capability": needed or "未指明工具",
            "blocked_step": f"使用 {needed or '所需工具'} 制作或检查当前资源",
            "required_input": f"可用的 {needed or '同等工具'} 或已授权替代",
            "expected_outcome": str(request.get("outcome") or "相同交付目标"),
            "return_check": "工具到位后按原完成标准复查游戏内效果",
        },
        "continue_unaffected": True,
        "install_by_default": False,
        "pay_by_default": False,
        "lower_requirements": False,
    }


def _risk_decision(request: dict) -> dict[str, Any]:
    risk = str(request.get("risk") or "editor")
    actual = {"install_package", "device", "platform_diff", "actual_build"}
    check_mode = "actual_build" if risk in actual else "editor_run"
    error_kind = str(request.get("error_kind") or "")
    if error_kind == "design":
        fix_target = "design_confirm"
    elif error_kind == "implementation":
        fix_target = "implementation"
    else:
        fix_target = ""
    playtest_required = bool(request.get("playtest_required"))
    playtest_done = bool(request.get("playtest_done"))
    keep_waiting = playtest_required and not playtest_done
    return {
        "check_mode": check_mode,
        "fix_target": fix_target,
        "demo_game_required": False,
        "keep_waiting": keep_waiting,
        "close_as_accepted": False,
        "playtest_required": playtest_required,
        "playtest_done": playtest_done,
    }


def _resource_tickets(request: dict) -> tuple[str, list[dict[str, Any]]]:
    feature = _ticket_from_request(request)
    if not request.get("independent_resource"):
        return "together", [feature]
    assets = list(request.get("resources") or [{}])
    asset = assets[0] if assets else {}
    file_ticket = {
        "identity": str(request.get("identity") or "05-resource"),
        "title": str(request.get("title") or "独立资源"),
        "kind": "independent_resource",
        "起始条件": str(request.get("starting_state") or "资源尚未交付"),
        "操作": "核对文件、格式、来源并预览或播放",
        "反馈": str(asset.get("preview") or "可预览或播放"),
        "成果": str(asset.get("path") or "资源文件"),
        "检查责任": "资源任务核对格式、来源、预览或播放",
        "completion_kind": "file_ready",
        "format": str(asset.get("format") or ""),
        "source": str(asset.get("source") or ""),
        "preview": str(asset.get("preview") or ""),
        "resources": assets,
    }
    integrate_id = str(request.get("integration_identity") or "06-in-game")
    owner = str(request.get("integration_owner")
                or "制作实现完成游戏内引用、表现与必要导出检查")
    game_ticket = {
        "identity": integrate_id,
        "title": "游戏内接入",
        "kind": "integration",
        "起始条件": f"资源任务 {file_ticket['identity']} 文件已就绪",
        "操作": "在正式工程引用资源并检查游戏内表现",
        "反馈": "游戏内可见或可听",
        "成果": "功能已接入资源",
        "检查责任": owner if "游戏内" in owner else f"{owner};游戏内检查",
        "completion_kind": "in_game",
        "resources": assets,
        "依赖": file_ticket["identity"],
        "blocked_by": file_ticket["identity"],
    }
    return "independent", [file_ticket, game_ticket]


def _task_fields(ticket: dict, request: dict) -> dict[str, str]:
    fields = {
        "当前目标": ticket.get("title") or request.get("title") or "",
        "输入与基线": str(request.get("baseline") or "GAME_DESIGN.md 现行规格"),
        "本次交付": ticket.get("成果") or "",
        "允许修改范围": str(request.get("allow") or "src/**, assets/**"),
        "所需能力": str((request.get("tools") or {}).get("needed") or "文件读写"),
        "完成标准": ticket.get("操作") or "",
        "执行责任": "Agent(制作实现)",
        "验收方式": ticket.get("检查责任") or "",
        "依赖": str(ticket.get("依赖") or request.get("blocked_by") or "无"),
        "起始条件": ticket.get("起始条件") or "",
        "操作": ticket.get("操作") or "",
        "反馈": ticket.get("反馈") or "",
        "成果": ticket.get("成果") or "",
        "检查责任": ticket.get("检查责任") or "",
    }
    for extra in ("format", "source", "preview"):
        if ticket.get(extra):
            fields[extra] = str(ticket[extra])
    return fields


def plan_playable_delivery(project_root: Path | str, request: dict,
                           config_rel: str = DEFAULT_CONFIG_REL, *,
                           transport=None, api_base: str | None = None,
                           cache_dir: Path | str | None = None) -> dict:
    """整理可玩任务。默认正式工程最小闭环;本阶段不写入。"""

    _config(project_root, config_rel)
    resource_mode, tickets = _resource_tickets(request)
    explicit = bool(request.get("explicit_prototype"))
    small = bool(request.get("small_change") or request.get("kind") == "small_change")
    trials = [dict(item) for item in (request.get("trial_values") or [])]
    for item in trials:
        item["adopted"] = bool(item.get("adopted"))
    if explicit:
        target = "isolated_prototype"
        prototype_added = True
        needs_formal = False
        reuse_flag = False
    elif request.get("reuse_prototype") or request.get("direction_approved"):
        target = "formal_project"
        prototype_added = False
        needs_formal = True
        reuse_flag = True
    else:
        target = "formal_project"
        prototype_added = False
        needs_formal = False
        reuse_flag = False
    return {
        "wrote": False,
        "gate_required": False,
        "auto_invoke_user_entries": False,
        "user_only_entries": list(USER_ONLY),
        "target": target,
        "prototype_added": prototype_added,
        "reuse_current": True if small else False,
        "reuse_prototype": reuse_flag,
        "needs_formal_integration": needs_formal,
        "formal_delivery_complete": False,
        "trial_values": trials,
        "resource_mode": resource_mode,
        "tickets": tickets,
        "request": dict(request),
        **_tool_decision(request),
        **_risk_decision(request),
    }


def apply_playable_delivery(project_root: Path | str, plan: dict, *,
                            confirmed: bool = True,
                            config_rel: str = DEFAULT_CONFIG_REL,
                            transport=None, api_base: str | None = None,
                            cache_dir: Path | str | None = None) -> dict:
    """把可玩任务写入选定 tracker。未确认不写。"""

    if not confirmed:
        return {"ok": False, "wrote": False, "reason": "开发者未确认拆票,不写入"}
    import mgs_records  # noqa: PLC0415

    request = dict(plan.get("request") or {})
    created = []
    for ticket in plan.get("tickets") or []:
        identity = str(ticket.get("identity") or "")
        title = str(ticket.get("title") or identity)
        fields = _task_fields(ticket, request)
        handoff = plan.get("handoff") or {}
        if handoff:
            fields["尚缺信息"] = (
                f"缺能力:{handoff.get('missing_capability')};"
                f"受阻步骤:{handoff.get('blocked_step')};"
                f"所需输入:{handoff.get('required_input')};"
                f"预期成果:{handoff.get('expected_outcome')};"
                f"返回后检查:{handoff.get('return_check')}"
            )
        result = mgs_records.create_task(
            project_root, identity, title, fields,
            triage="ready-for-agent",
            config_rel=config_rel, transport=transport, api_base=api_base,
            cache_dir=cache_dir)
        created.append({
            "identity": identity,
            "created": result.get("created"),
            "adopted": result.get("adopted"),
            "published": result.get("published", True),
        })
    # 工单未全部到达现行账本(离线草稿/部分创建失败)时如实上报:
    # 调用方不能在缺少权威工作项的情况下继续宣称拆票已应用。
    unreached = [item["identity"] for item in created
                 if not (item.get("created") or item.get("adopted"))
                 or item.get("published") is False]
    all_published = bool(created) and not unreached
    outcome = {
        "ok": all_published,
        "wrote": bool(created),
        "gate_required": False,
        "formal_delivery_complete": False,
        "created": created,
    }
    if not all_published:
        outcome["reason"] = (
            f"工单未全部到达现行账本(离线草稿或创建失败):{', '.join(unreached)};"
            "远端可用后重试或重放草稿,不按已应用继续")
    return outcome


def record_playable_result(project_root: Path | str, identity: str,
                           result: dict,
                           config_rel: str = DEFAULT_CONFIG_REL, *,
                           transport=None, api_base: str | None = None,
                           cache_dir: Path | str | None = None) -> dict:
    """记录实际版本、启动方式、检查范围与反馈去向。"""

    import mgs_records  # noqa: PLC0415

    status = str(result.get("status") or "未记录")
    version = str(result.get("version") or "未记录")
    launch = str(result.get("launch") or "未记录")
    scope = str(result.get("check_scope") or "未记录")
    playtest_required = bool(result.get("playtest_required"))
    playtest_done = bool(result.get("playtest_done"))
    keep_waiting = status == "waiting_playtest" or (
        playtest_required and not playtest_done)
    missing = status == "missing_resource"
    cancelled = status == "cancelled"
    complete = status == "delivered" and not keep_waiting and not missing
    body = (
        f"任务:{identity}\n\n"
        f"- 实际版本:{version}\n"
        f"- 启动方式:{launch}\n"
        f"- 检查范围:{scope}\n"
        f"- 状态:{status}\n"
        f"- 反馈去向:对应任务结果\n"
    )
    if result.get("missing"):
        body += f"- 缺失资源:{result.get('missing')}\n"
    written = mgs_records.append_result(
        project_root, identity, body, config_rel=config_rel,
        transport=transport, api_base=api_base, cache_dir=cache_dir)
    if keep_waiting:
        mgs_records.update_task(
            project_root, identity, {"进度": "待验收"},
            change_note="约定试玩尚未发生,保留等待",
            config_rel=config_rel, transport=transport, api_base=api_base,
            cache_dir=cache_dir)
    preserved = True
    restored = False
    if cancelled:
        mgs_records.cancel_operation(
            project_root, "create_task", identity,
            note="取消后不再启动被撤销范围的新动作",
            config_rel=config_rel)
    # 正式交付完成必须以结果真正到达现行账本为前提;
    # 只有未发布草稿时不得宣告交付完成或验收关闭;部分成功(评论已
    # 发布而结果索引未确认更新)同样留有待恢复的发布缺口,不算完成。
    published = bool(written.get("published"))
    index_pending = (bool(written.get("partial"))
                     or written.get("index_updated") is False)
    complete = (status == "delivered" and published and not index_pending
                and not keep_waiting and not missing)
    unpublished = (status == "delivered" and not published
                   and not keep_waiting and not missing and not cancelled)
    pending_recovery = (status == "delivered" and published and index_pending
                        and not keep_waiting and not missing and not cancelled)
    result_out = {
        "ok": True,
        "wrote": True,
        "gate_required": False,
        "identity": identity,
        "published": written.get("published"),
        "version": version,
        "launch": launch,
        "check_scope": scope,
        "status": status,
        "close_as_accepted": complete,
        "formal_delivery_complete": bool(complete),
        "keep_waiting": keep_waiting,
        "cancelled": cancelled,
        "preserved": preserved,
        "restored": restored,
        "demo_game_required": False,
    }
    if unpublished:
        result_out["reason"] = (
            "结果仅保存为未发布草稿,未到达现行任务账本;"
            "不宣告正式交付完成,也不按验收关闭")
    elif pending_recovery:
        result_out["reason"] = (
            "结果发布部分成功:评论已落地而结果索引未确认更新;"
            "发布恢复完成前不宣告正式交付完成,也不按验收关闭")
    return result_out

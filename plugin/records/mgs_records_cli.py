#!/usr/bin/env python3
"""mgs_records 命令行层:参数解析、现有输出投影与退出码(PR #28 复审 ST-1)。

对应设计「命令行与兼容入口」职责行:本模块只保留参数解析、输出投影、
退出码及公开导入定位,业务行为全部经查询组织 ``mgs_records`` 的公开接缝
完成;不包含正文解析、依赖计算或恢复规则。与旧版逐项兼容:子命令集合、
参数、JSON 输出与退出码合同不变,旧脚本 ``mgs_records.py`` 保持原调用入口
(脚本守卫延迟导入本模块,查询组织不在其他模块被反向导入)。

用法(与 mgs_records.py 完全一致):
  mgs_records.py config --project <项目根> [--config <CONFIG相对路径>]
  mgs_records.py list|show|deps|ready|frontier|status|analyze|onboard|baseline|verify ...
  mgs_records.py create|update|append-result|set-triage|set-relations|
                set-parent|claim|close ...
  GitHub 后端: publish-drafts|switch-plan|switch-apply|handover ...
  安全切换: switch-check|switch-run|switch-rollback|switch-status ...
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

# CLI 层单向依赖查询组织:业务行为全部经 mgs_records 公开接缝;查询组织
# 的模块级定义不反向导入本模块(仅旧脚本入口的脚本守卫延迟导入)。
from mgs_records import (  # noqa: E402  (路径调整后导入)
    CANONICAL_LABELS, DEFAULT_CONFIG_REL, RecordsError, append_result,
    apply_github_onboarding, apply_local_onboarding, apply_safe_switch,
    analyze_project, baseline_report, claim_task,
    close_task, create_task, frontier_tasks, list_tasks, load_config,
    plan_github_onboarding, plan_local_onboarding, plan_safe_switch,
    read_safe_switch, read_task, rollback_safe_switch, set_parent,
    set_relations, set_triage, startable_tasks,
    status_report, task_dependencies, update_task, verify_project)


def _parse_fields(pairs: list[str]) -> dict:
    fields: dict[str, str] = {}
    for pair in pairs:
        if "=" not in pair:
            raise RecordsError(f"字段必须形如 键=值,当前 {pair!r}")
        key, value = pair.split("=", 1)
        fields[key.strip()] = value.strip()
    return fields


def _cli() -> int:
    common = argparse.ArgumentParser(add_help=False)
    common.add_argument("--project", required=True, help="目标项目根目录")
    common.add_argument("--config", default=DEFAULT_CONFIG_REL,
                        help=f"CONFIG 相对路径(默认 {DEFAULT_CONFIG_REL})")
    common.add_argument("--api-base", default=None,
                        help="GitHub API 端点覆盖(测试/本地替身;默认按 host 推导,"
                             "或环境变量 MGS_GH_API_BASE)")
    common.add_argument("--cache-dir", default=None,
                        help="远端读取缓存与未发布草稿目录(离线缓存/草稿语义)")
    parser = argparse.ArgumentParser(
        description="任务后端统一接口(本地 Markdown 读写与核验;"
                    "github-issues 后端读写与切换迁移;普通本地写入不经 gate)")
    sub = parser.add_subparsers(dest="cmd", required=True)
    sub.add_parser("config", parents=[common], help="读取协作配置")
    sub.add_parser("list", parents=[common], help="列出任务")
    p_show = sub.add_parser("show", parents=[common], help="读取单个任务")
    p_show.add_argument("--task", required=True, help="任务身份")
    sub.add_parser("deps", parents=[common],
                   help="解析任务依赖关系(未解析引用或循环时退出码 1)")
    sub.add_parser("ready", parents=[common], help="当前可开工集合及原因")
    sub.add_parser("status", parents=[common],
                   help="Game-Producer 只读状态(不修改文件)")
    sub.add_parser("analyze", parents=[common],
                   help="Game-Init 只读分析(不修改文件)")
    p_onboard = sub.add_parser(
        "onboard", parents=[common],
        help="按确认清单接入本地 Markdown 或 GitHub Issues(不覆盖有效旧资料)")
    p_onboard.add_argument("--confirmed", action="store_true",
                           help="确认标记(未确认则拒绝写入)")
    p_onboard.add_argument(
        "--tracker", default="local-markdown",
        choices=["local-markdown", "github-issues"],
        help="唯一现行 tracker(默认 local-markdown,与既有本地接入兼容)")
    p_onboard.add_argument("--repo", default=None,
                           help="github-issues 时的 host/owner/repository")
    p_onboard.add_argument("--authorization", default="",
                           help="github-issues 写入授权记录,形如 host/owner/repo:issues-write(说明)")
    p_frontier = sub.add_parser(
        "frontier", parents=[common],
        help="前沿查询:开放、未认领、无开放阻塞的子票(只读)")
    p_frontier.add_argument("--parent", default=None, help="地图/父任务身份")
    sub.add_parser("baseline", parents=[common],
                   help="核心基线内容指纹核对与受影响任务"
                        "(存在实质变更未同步时退出码 1)")
    sub.add_parser("verify", parents=[common], help="回读核验")
    p_create = sub.add_parser(
        "create", parents=[common], help="创建任务(防重复:同身份收养)")
    p_create.add_argument("--identity", required=True, help="任务身份(NN-<slug>)")
    p_create.add_argument("--title", required=True, help="任务标题")
    p_create.add_argument("--field", action="append", default=[],
                          help="工作请求字段 键=值,可重复")
    p_create.add_argument("--triage", default="needs-triage",
                          choices=CANONICAL_LABELS, help="初始分流")
    p_create.add_argument("--progress", default="待执行", help="初始进度")
    p_update = sub.add_parser(
        "update", parents=[common], help="更新任务安排(字段合并,可带版本校验)")
    p_update.add_argument("--task", required=True, help="任务身份")
    p_update.add_argument("--field", action="append", default=[],
                          help="字段 键=值(进度/工作请求字段),可重复")
    p_update.add_argument("--change-note", default=None,
                          help="安排更新说明(写入状态变化;缺省「安排更新」;"
                               "与草稿保存/重放共用同一参数)")
    p_update.add_argument("--expected-body-sha256", default=None,
                          help="预期远端正文 SHA-256(不符则拒绝,不覆盖他人改动)")
    p_append = sub.add_parser(
        "append-result", parents=[common], help="追加结果评论并登记结果索引")
    p_append.add_argument("--task", required=True, help="任务身份")
    src = p_append.add_mutually_exclusive_group(required=True)
    src.add_argument("--text", help="结果正文(Markdown)")
    src.add_argument("--file", help="结果正文文件路径")
    p_triage = sub.add_parser(
        "set-triage", parents=[common], help="设置分流(标签与正文同步)")
    p_triage.add_argument("--task", required=True, help="任务身份")
    p_triage.add_argument("--label", required=True, choices=CANONICAL_LABELS)
    p_rels = sub.add_parser(
        "set-relations", parents=[common], help="设置依赖(明确可解析引用)")
    p_rels.add_argument("--task", required=True, help="任务身份")
    p_rels.add_argument("--dep", action="append", default=[],
                        help="依赖任务身份,可重复;留空表示无依赖")
    p_parent = sub.add_parser(
        "set-parent", parents=[common],
        help="设置父任务(优先原生 sub-issues,不可用回退正文引用)")
    p_parent.add_argument("--task", required=True, help="任务身份")
    p_parent.add_argument("--parent", default=None, help="父任务身份;省略即解除")
    p_close = sub.add_parser(
        "close", parents=[common],
        help="关闭任务(完成/不再执行/已有成果覆盖;关闭不等于验收通过)")
    p_close.add_argument("--task", required=True, help="任务身份")
    p_close.add_argument("--reason", required=True,
                         choices=["完成", "不再执行", "已有成果覆盖"])
    p_close.add_argument("--note", default="", help="关闭说明")
    p_claim = sub.add_parser(
        "claim", parents=[common], help="认领任务(开工前写入认领字段)")
    p_claim.add_argument("--task", required=True, help="任务身份")
    p_claim.add_argument("--actor", required=True, help="认领者")
    sub.add_parser("publish-drafts", parents=[common],
                   help="重放未发布草稿(远端恢复后)")
    p_handover = sub.add_parser(
        "handover", parents=[common],
        help="远端交接核对基线引用可达(未发布本地资料不宣称远端可访问;"
             "不可达时退出码 1)")
    p_plan = sub.add_parser(
        "switch-plan", parents=[common],
        help="生成后端切换迁移清单(只读;确认前不执行)")
    p_plan.add_argument("--target", required=True,
                        choices=["github-issues", "local-markdown"])
    p_plan.add_argument("--repo", default=None,
                        help="目标为 github-issues 时的 host/owner/repository")
    p_plan.add_argument("--emit", default=None, help="迁移清单 JSON 输出路径")
    p_apply = sub.add_parser(
        "switch-apply", parents=[common],
        help="执行已确认的切换(目标侧创建+产出新 CONFIG;不改写项目 CONFIG)")
    p_apply.add_argument("--plan", required=True, help="switch-plan 产出的清单")
    p_apply.add_argument("--emit-dir", required=True, help="产出目录")
    p_apply.add_argument("--confirmed", action="store_true",
                         help="确认标记(未确认则拒绝执行)")
    p_check = sub.add_parser(
        "switch-check", parents=[common],
        help="安全切换只读核对(资料/证据/用户修改/指纹;不写入)")
    p_check.add_argument("--client-home", default=None,
                         help="客户端主目录(技能来源切换;缺省仅核对项目资料)")
    p_check.add_argument("--package-root", default=None,
                         help="新包根目录(提供切换后的技能来源)")
    p_check.add_argument("--peer-project", action="append", default=[],
                         help="共用同一客户端的同侪项目根,可重复")
    p_run = sub.add_parser(
        "switch-run", parents=[common],
        help="执行已确认的安全切换(现行指针与技能来源)")
    p_run.add_argument("--plan", default=None,
                       help="switch-check 产出的计划 JSON;"
                            "缺省时在执行前即时重算并核对")
    p_run.add_argument("--confirmed", action="store_true",
                       help="确认标记(未确认则拒绝执行)")
    p_rollback = sub.add_parser(
        "switch-rollback", parents=[common],
        help="回退已执行的安全切换(先保留切换后新增成果)")
    p_rollback.add_argument("--plan", default=None, help="可选计划 JSON")
    p_rollback.add_argument("--confirmed", action="store_true",
                            help="确认标记(未确认则拒绝执行)")
    sub.add_parser("switch-status", parents=[common],
                   help="回读安全切换状态、现行来源与恢复去向")

    args = parser.parse_args()
    root = Path(args.project)
    remote = {"transport": None, "api_base": args.api_base,
              "cache_dir": args.cache_dir}

    def read_transport(config: dict):
        """CLI 子命令所需的真实读取通道(审查修复票 01/S3、S4):反向
        switch-plan 要读取 github 源任务,handover 要实际执行可达检查;
        --api-base/环境变量可指向本地替身,不注入测试桩。"""

        import mgs_github  # noqa: PLC0415

        return mgs_github.UrllibTransport(
            api_base=mgs_github.api_base_for(config, args.api_base),
            token=mgs_github.token_from_env())

    def github_only(action: str):
        import mgs_github  # noqa: PLC0415

        config = load_config(root, args.config)
        if config["backend"] != "github-issues":
            raise RecordsError(
                f"{action} 仅支持 github-issues 后端(当前 {config['backend']})")
        return mgs_github.GithubBackend(
            config, read_transport(config), args.cache_dir)

    try:
        if args.cmd == "config":
            payload: object = load_config(root, args.config)
        elif args.cmd == "list":
            payload = [{"identity": t["identity"], "title": t["title"],
                        "triage": t["triage"], "progress": t["progress"],
                        **({"cached_read": True} if t.get("cached_read") else {})}
                       for t in list_tasks(root, args.config, **remote)]
        elif args.cmd == "show":
            payload = read_task(root, args.task, args.config, **remote)
        elif args.cmd == "deps":
            payload = task_dependencies(root, args.config, **remote)
        elif args.cmd == "ready":
            payload = startable_tasks(root, args.config, **remote)
        elif args.cmd == "baseline":
            payload = baseline_report(root, args.config, **remote)
        elif args.cmd == "verify":
            payload = verify_project(root, args.config, **remote)
        elif args.cmd == "status":
            payload = status_report(root, args.config, **remote)
        elif args.cmd == "analyze":
            payload = analyze_project(root)
        elif args.cmd == "onboard":
            # --config 必须贯通到接入规划与写入:否则非默认路径下会把
            # 项目当未配置分析,并在默认路径再建第二套 tracker 权威。
            if args.tracker == "github-issues":
                if not args.repo:
                    raise RecordsError("GitHub 接入必须提供 --repo host/owner/repository")
                payload = apply_github_onboarding(
                    root, plan_github_onboarding(
                        root, repo=args.repo, authorization=args.authorization,
                        config_rel=args.config),
                    confirmed=args.confirmed, config_rel=args.config)
            else:
                payload = apply_local_onboarding(
                    root, plan_local_onboarding(root, args.config),
                    confirmed=args.confirmed, config_rel=args.config)
        elif args.cmd == "frontier":
            payload = frontier_tasks(
                root, parent_identity=args.parent, config_rel=args.config,
                **remote)
        elif args.cmd == "create":
            payload = create_task(
                root, args.identity, args.title, _parse_fields(args.field),
                triage=args.triage, progress=args.progress,
                config_rel=args.config, **remote)
        elif args.cmd == "update":
            if not args.field:
                raise RecordsError("update 至少需要一个 --field")
            payload = update_task(
                root, args.task, _parse_fields(args.field),
                expected_body_sha256=args.expected_body_sha256,
                change_note=args.change_note or "安排更新",
                config_rel=args.config, **remote)
        elif args.cmd == "append-result":
            text = (Path(args.file).read_text(encoding="utf-8") if args.file
                    else args.text)
            payload = append_result(
                root, args.task, text, config_rel=args.config, **remote)
        elif args.cmd == "set-triage":
            payload = set_triage(
                root, args.task, args.label, config_rel=args.config, **remote)
        elif args.cmd == "set-relations":
            payload = set_relations(
                root, args.task, args.dep, config_rel=args.config, **remote)
        elif args.cmd == "set-parent":
            payload = set_parent(
                root, args.task, args.parent, config_rel=args.config, **remote)
        elif args.cmd == "close":
            payload = close_task(
                root, args.task, args.reason, note=args.note,
                config_rel=args.config, **remote)
        elif args.cmd == "claim":
            payload = claim_task(
                root, args.task, args.actor, config_rel=args.config, **remote)
        elif args.cmd == "publish-drafts":
            payload = github_only("publish-drafts").publish_drafts()
        elif args.cmd == "handover":
            import mgs_github  # noqa: PLC0415

            config = load_config(root, args.config)
            if config["backend"] != "github-issues":
                raise RecordsError(
                    f"handover 仅用于 github-issues 后端的远端交接核对"
                    f"(当前 {config['backend']})")
            # 可达性结论只能来自实际执行的检查(S4):建立真实读取通道
            payload = mgs_github.handover_baseline_check(
                root, args.config, transport=read_transport(config))
        elif args.cmd == "switch-plan":
            import mgs_github  # noqa: PLC0415

            config = load_config(root, args.config)
            payload = mgs_github.plan_backend_switch(
                root, target=args.target, repo=args.repo,
                transport=read_transport(config), cache_dir=args.cache_dir)
            if args.emit:
                Path(args.emit).write_text(
                    json.dumps(payload, ensure_ascii=False, indent=2),
                    encoding="utf-8")
        elif args.cmd == "switch-apply":
            import mgs_github  # noqa: PLC0415

            plan_data = json.loads(Path(args.plan).read_text(encoding="utf-8"))
            transport = None
            if plan_data.get("to") == "github-issues":
                host = mgs_github.parse_repo_location(plan_data["repo"])["host"]
                base = (args.api_base
                        or os.environ.get(mgs_github.API_BASE_ENV, "").strip()
                        or mgs_github.default_api_base(host))
                transport = mgs_github.UrllibTransport(
                    base, mgs_github.token_from_env())
            payload = mgs_github.apply_backend_switch(
                args.plan, confirmed=args.confirmed, emit_dir=args.emit_dir,
                project_root=root, transport=transport,
                cache_dir=args.cache_dir)
        elif args.cmd == "switch-check":
            payload = plan_safe_switch(
                root, client_home=args.client_home,
                package_root=args.package_root,
                peer_projects=args.peer_project, **remote)
        elif args.cmd in {"switch-run", "switch-rollback"}:
            plan_data = None
            if args.plan:
                plan_data = json.loads(
                    Path(args.plan).read_text(encoding="utf-8"))
            action = (apply_safe_switch if args.cmd == "switch-run"
                      else rollback_safe_switch)
            payload = action(root, plan_data, confirmed=args.confirmed,
                             **remote)
        elif args.cmd == "switch-status":
            payload = read_safe_switch(root, **remote)
        else:  # pragma: no cover - 子命令已穷举
            raise RecordsError(f"未知子命令 {args.cmd}")
    except RecordsError as exc:
        print(json.dumps({"error": str(exc)}, ensure_ascii=False))
        return 2
    except OSError as exc:
        print(json.dumps({"error": str(exc)}, ensure_ascii=False))
        return 2
    print(json.dumps(payload, ensure_ascii=False, indent=2, default=str))
    if args.cmd == "verify" and not payload["ok"]:
        return 1
    if args.cmd == "deps" and not payload["ok"]:
        return 1
    if args.cmd == "baseline" and not payload["ok"]:
        return 1
    if args.cmd == "handover" and not payload["ok"]:
        return 1
    return 0

#!/usr/bin/env python3
"""Game-Design 决定保存与恢复的命令行入口(统一设计问答框架票 03)。

与 mgs-gate 的 ``mgs_write`` 提交同一条受控通道(``GateService``):逐次
核对当前授权与目标版本,写入后回读。用法:

    python3 decisions_cli.py plan   --project-root <项目> --path <记录> < turn.json
    python3 decisions_cli.py save   --project-root <项目> --path <记录> \
        --runtime-root <运行根> --token <凭据> < turn.json
    python3 decisions_cli.py sync   --project-root <项目> --path <记录> \
        --runtime-root <运行根> --token <凭据> --module <模块> \
        --qids Q1,Q2 --sync-ref <同步目标> --date <日期> [--authorized]
    python3 decisions_cli.py restore --module <模块> --records <记录目录>

``plan`` 只输出整理结果,不写入;``save`` 写入成功以 0 退出,失败以非零
退出并原样给出 ``status`` / ``rule_stage`` / ``reason``,不换通道重试。
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

from decisions import GateChannel, apply_save, plan_save, plan_sync, restore_from_records


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(
        description="Game-Design 决定保存与恢复接缝(经受控通道)")
    sub = parser.add_subparsers(dest="action", required=True)
    for name, helptext in (("plan", "整理本轮最小决定记录(不写入)"),
                           ("save", "经受控通道保存本轮决定并回读"),
                           ("sync", "把指定决定标记为已同步核心基线")):
        node = sub.add_parser(name, help=helptext)
        node.add_argument("--project-root", required=True)
        node.add_argument("--path", required=True)
        if name in {"save", "sync"}:
            node.add_argument("--runtime-root", required=True)
            node.add_argument("--token", required=True)
        if name == "sync":
            node.add_argument("--module", required=True)
            node.add_argument("--qids", required=True, help="逗号分隔的 Q 编号")
            node.add_argument("--sync-ref", required=True)
            node.add_argument("--date", required=True)
            node.add_argument("--authorized", action="store_true",
                              help="显式确认本次已获同步授权;"
                                   "缺省按未授权保留待同步项")
    restore = sub.add_parser("restore", help="从实际记录恢复已定与未决")
    restore.add_argument("--module", required=True)
    restore.add_argument("--records", required=True)
    args = parser.parse_args(argv[1:])

    if args.action == "restore":
        root = Path(args.records)
        texts = {str(path.relative_to(root)): path.read_text(encoding="utf-8")
                 for path in sorted(root.glob("*.md"))}
        print(json.dumps(restore_from_records(texts, args.module),
                         ensure_ascii=False, indent=2))
        return 0

    project_root = Path(args.project_root).resolve()
    record_path = (project_root / args.path).resolve()
    rel = str(record_path.relative_to(project_root))
    current = record_path.read_text(encoding="utf-8") \
        if record_path.is_file() else None

    if args.action == "sync":
        plan = plan_sync(current, {
            "record_path": rel, "module": args.module, "date": args.date,
            "qids": [qid.strip() for qid in args.qids.split(",") if qid.strip()],
            "sync_ref": args.sync_ref,
            "authorization": {"write": True, "sync": args.authorized}})
    else:
        payload = json.loads(sys.stdin.read())
        meta = dict(payload.get("meta") or {})
        meta.setdefault("record_path", rel)
        plan = plan_save(current, payload.get("round_result") or {}, meta)
    if args.action == "plan":
        print(json.dumps(plan, ensure_ascii=False, indent=2))
        return 0

    service = _load_service(args.runtime_root)

    def readback(path: str):
        target = project_root / path
        return target.read_text(encoding="utf-8") if target.is_file() else None

    result = apply_save(plan, GateChannel(service, args.token), readback)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result.get("saved") else 1


def _load_service(runtime_root: str) -> Any:
    runtime_dir = Path(__file__).resolve().parents[2] / "runtime"
    if str(runtime_dir) not in sys.path:
        sys.path.insert(0, str(runtime_dir))
    from mgs_runtime import GateService  # noqa: E402

    return GateService(runtime_root)


if __name__ == "__main__":
    sys.exit(main(sys.argv))

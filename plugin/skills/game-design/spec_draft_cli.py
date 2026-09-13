#!/usr/bin/env python3
"""Game-Design 模块规格交接的命令行入口(统一设计问答框架票 04)。

与 mgs-gate 的 ``mgs_write`` 提交同一条受控通道(``GateService``):逐次核对
当前授权与目标版本,写入后回读。用法:

    python3 spec_draft_cli.py plan   --project-root <项目> < payload.json
    python3 spec_draft_cli.py apply  --project-root <项目> \
        --runtime-root <运行根> --token <凭据> < payload.json
    python3 spec_draft_cli.py verify --project-root <项目> < payload.json

payload 为 ``{"records": {相对路径: 记录全文}, "meta": {...}}``;``plan`` 只
输出整理结果,不写入;``apply`` 成功以 0 退出,未完成/只读/被拒/冲突以非零
退出并原样给出 ``status`` / ``rule_stage`` / ``reason``,不换通道重试。
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

from decisions import GateChannel, load_gate_service
from spec_draft import apply_handoff, plan_handoff, verify_handoff


def _paths(payload: dict[str, Any]) -> list[str]:
    records = dict(payload.get("records") or {})
    meta = dict(payload.get("meta") or {})
    paths = {str(path) for path in records}
    for key in ("record_path", "spec_path", "design_path", "glossary_path"):
        value = meta.get(key)
        if value:
            paths.add(str(value))
    for value in meta.get("untouched") or []:
        paths.add(str(value))
    return sorted(paths)


def _read_all(project_root: Path, paths: list[str]) -> dict[str, str | None]:
    texts: dict[str, str | None] = {}
    for rel in paths:
        target = project_root / rel
        texts[rel] = target.read_text(encoding="utf-8") \
            if target.is_file() else None
    return texts


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(
        description="Game-Design 模块规格交接接缝(经受控通道)")
    parser.add_argument("action", choices=("plan", "apply", "verify"))
    parser.add_argument("--project-root", required=True)
    parser.add_argument("--runtime-root")
    parser.add_argument("--token")
    args = parser.parse_args(argv[1:])

    project_root = Path(args.project_root).resolve()
    payload = json.loads(sys.stdin.read() or "{}")
    records = dict(payload.get("records") or {})
    meta = dict(payload.get("meta") or {})
    existing = _read_all(project_root, _paths(payload))

    def readback(path: str):
        target = project_root / path
        return target.read_text(encoding="utf-8") if target.is_file() else None

    if args.action == "verify":
        plan = plan_handoff(records, meta, existing)
        verdict = verify_handoff(plan, existing)
        print(json.dumps(verdict, ensure_ascii=False, indent=2))
        return 0 if verdict["ok"] else 1

    plan = plan_handoff(records, meta, existing)
    if args.action == "plan":
        print(json.dumps(plan, ensure_ascii=False, indent=2))
        return 0

    if not args.runtime_root or not args.token:
        print(json.dumps({"status": "unauthorized", "saved": False,
                          "report": "缺少运行根或执行凭据:不自行签发凭据,"
                                    "不绕过写入通道。"},
                         ensure_ascii=False, indent=2))
        return 1
    service = load_gate_service(args.runtime_root)
    result = apply_handoff(plan, GateChannel(service, args.token), readback)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result.get("saved") else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv))

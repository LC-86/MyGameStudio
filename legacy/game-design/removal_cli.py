#!/usr/bin/env python3
"""Game-Design 功能删减的命令行入口(统一设计问答框架票 07)。

与 mgs-gate 的 ``mgs_write`` 提交同一条受控通道(``GateService``):逐次核对
当前授权与目标版本,写入后回读。用法:

    python3 removal_cli.py plan   --project-root <项目> < payload.json
    python3 removal_cli.py apply  --project-root <项目> \
        --runtime-root <运行根> --token <凭据> < payload.json
    python3 removal_cli.py verify --project-root <项目> < payload.json

payload 为 ``{"meta": {...}, "material": {...}}``;``plan`` 只输出删减整理结果,
不写入;``apply`` 成功以 0 退出,未完成/待取舍/只读/被拒/冲突以非零退出并原样
给出 ``status`` / ``rule_stage`` / ``reason``,不换通道重试,也不执行未授权的
迁移、代码删除或用户数据清理。
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

from change_flow_cli import payload_paths, read_all
from decisions import GateChannel, load_gate_service
from removal import apply_removal, plan_removal, verify_removal


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(
        description="Game-Design 功能删减接缝(经受控通道)")
    parser.add_argument("action", choices=("plan", "apply", "verify"))
    parser.add_argument("--project-root", required=True)
    parser.add_argument("--runtime-root")
    parser.add_argument("--token")
    args = parser.parse_args(argv[1:])

    project_root = Path(args.project_root).resolve()
    payload: dict[str, Any] = json.loads(sys.stdin.read() or "{}")
    meta = dict(payload.get("meta") or {})
    material = dict(payload.get("material") or {})
    existing = read_all(project_root, payload_paths(payload))

    def readback(path: str):
        target = project_root / path
        return target.read_text(encoding="utf-8") if target.is_file() else None

    if args.action == "verify":
        plan = plan_removal(existing, meta, material)
        verdict = verify_removal(plan, existing)
        print(json.dumps(verdict, ensure_ascii=False, indent=2))
        return 0 if verdict["ok"] else 1

    plan = plan_removal(existing, meta, material)
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
    result = apply_removal(plan, GateChannel(service, args.token), readback)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result.get("saved") else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv))

#!/usr/bin/env python3
"""Game-Design 完整设计成稿的命令行入口(统一设计问答框架票 05)。

与 mgs-gate 的 ``mgs_write`` 提交同一条受控通道(``GateService``):逐次核对
当前授权与目标版本,写入后回读。用法:

    python3 full_design_cli.py check --project-root <项目> < payload.json
    python3 full_design_cli.py apply --project-root <项目> \
        --runtime-root <运行根> --token <凭据> < payload.json

payload 为 ``{"meta": {...}, "material": {...}}``;``check`` 只读核对交接标准
并输出覆盖地图、流程与矛盾判定,以 0 退出但按真实 ``status`` 报告(未完成不
冒充完成);``apply`` 成功以 0 退出,未完成/只读/被拒/冲突以非零退出并原样
给出 ``status`` / ``rule_stage`` / ``reason``,不换通道重试。
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

from decisions import GateChannel, load_gate_service
from full_design import apply_delivery, plan_delivery, verify_delivery


def _paths(payload: dict[str, Any]) -> list[str]:
    meta = dict(payload.get("meta") or {})
    doc_map = dict(meta.get("doc_map") or {})
    paths = {str(value) for value in doc_map.values() if value}
    for item in meta.get("module_specs") or []:
        if item.get("spec_path"):
            paths.add(str(item["spec_path"]))
    for value in meta.get("untouched") or []:
        paths.add(str(value))
    for value in meta.get("records") or []:
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
        description="Game-Design 完整设计成稿接缝(经受控通道)")
    parser.add_argument("action", choices=("check", "apply", "verify"))
    parser.add_argument("--project-root", required=True)
    parser.add_argument("--runtime-root")
    parser.add_argument("--token")
    args = parser.parse_args(argv[1:])

    project_root = Path(args.project_root).resolve()
    payload = json.loads(sys.stdin.read() or "{}")
    meta = dict(payload.get("meta") or {})
    material = dict(payload.get("material") or {})
    existing = _read_all(project_root, _paths(payload))

    def readback(path: str):
        target = project_root / path
        return target.read_text(encoding="utf-8") if target.is_file() else None

    plan = plan_delivery(existing, meta, material)
    if args.action == "check":
        print(json.dumps(plan, ensure_ascii=False, indent=2))
        return 0
    if args.action == "verify":
        verdict = verify_delivery(plan, existing)
        print(json.dumps(verdict, ensure_ascii=False, indent=2))
        return 0 if verdict["ok"] else 1

    if not args.runtime_root or not args.token:
        print(json.dumps({"status": "unauthorized", "saved": False,
                          "report": "缺少运行根或执行凭据:不自行签发凭据,"
                                    "不绕过写入通道。"},
                         ensure_ascii=False, indent=2))
        return 1
    service = load_gate_service(args.runtime_root)
    result = apply_delivery(plan, GateChannel(service, args.token), readback)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result.get("saved") else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv))

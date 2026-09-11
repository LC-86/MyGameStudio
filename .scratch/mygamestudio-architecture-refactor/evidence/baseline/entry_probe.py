#!/usr/bin/env python3
"""票 01 基线探针 E:现有命令行入口的 JSON 输出结构与退出码基线(静态+实跑)。

在隔离的 /tmp 临时项目上,通过**现有命令行入口**实际运行任务读取命令
(`plugin/records/mgs_records.py`),固定记录:

- 成功输出的 JSON 字段结构(键集合与类型,不含随时间变化的取值);
- 退出码:成功 0、记录/文件错误 2、判定失败 1;
- 代表性失败:任务缺失(exit 2)、判定失败(依赖未解析,exit 1)、
  配置缺失(exit 2)。

覆盖范围(如实登记):只覆盖 local-markdown 后端的读取入口,以及两处
代表性错误路径;github-issues 专属子命令与需要远端/凭据的入口不在本次
覆盖内(零网络、零凭据)。不启动真实模型、不访问网络、不做远端写入。

用法:python3 entry_probe.py [--out <report.json>]
"""

import json
import re
import subprocess
import sys
import tempfile
from pathlib import Path

from baseline_common import REPO_ROOT, emit, make_project, parse_out_args, write_local_task

CLI = REPO_ROOT / "plugin" / "records" / "mgs_records.py"

# 读取入口(本次实跑)与 github-issues 专属子命令(本次不跑,如实登记)。
READ_ENTRIES = ("config", "list", "show", "deps", "ready", "baseline", "verify")
NOT_COVERED = (
    "create", "update", "append-result", "set-triage", "set-relations",
    "set-parent", "close", "publish-drafts", "handover", "switch-plan",
    "switch-apply",
)


def shape(value) -> object:
    """把 JSON 取值压成「类型结构」:dict 保留键名→子结构,array 保留元素结构。

    只记结构不记取值,避免时间戳等非确定字段破坏复跑稳定性。
    """

    if isinstance(value, dict):
        return {"type": "object",
                "keys": {key: shape(value[key]) for key in sorted(value)}}
    if isinstance(value, list):
        return {"type": "array",
                "items": shape(value[0]) if value else None}
    if value is None:
        return "null"
    return type(value).__name__


def run_entry(project: Path, *argv: str) -> dict:
    """经现有 CLI 运行一条命令,返回退出码与 JSON 结构(不记录取值)。"""

    cmd = [sys.executable, "-B", str(CLI), *argv, "--project", str(project)]
    env = {"PATH": "/usr/bin:/bin:/usr/local/bin", "HOME": str(Path.home()),
           "LANG": "en_US.UTF-8"}
    proc = subprocess.run(cmd, cwd=str(REPO_ROOT), capture_output=True,
                          text=True, env=env, timeout=120, check=False)
    entry = {
        "argv": ["mgs_records.py", *argv, "--project", "<tmp>"],
        "returncode": proc.returncode,
        "stderr_empty": proc.stderr.strip() == "",
    }
    try:
        payload = json.loads(proc.stdout)
    except ValueError:
        entry["output"] = {"valid_json": False, "stdout_head": proc.stdout[:200]}
        return entry
    entry["output"] = {"valid_json": True, "shape": shape(payload)}
    if isinstance(payload, dict) and "error" in payload:
        entry["output"]["error_present"] = True
    if isinstance(payload, dict) and "ok" in payload:
        entry["output"]["ok_field"] = True
    return entry


def build_fixtures(workdir: Path) -> tuple[Path, Path]:
    """good:依赖可解析;bad:含未解析依赖。"""

    good = make_project(workdir / "good")
    write_local_task(good, "01-alpha", title="甲任务", deps="无")
    write_local_task(good, "02-beta", title="乙任务", deps="01-alpha")
    bad = make_project(workdir / "bad")
    write_local_task(bad, "01-alpha", title="甲任务", deps="99-missing")
    return good, bad


def declared_subcommands() -> dict:
    """从现有 CLI 的 --help 读取声明的子命令清单(不改生产代码)。"""

    proc = subprocess.run([sys.executable, "-B", str(CLI), "--help"],
                          cwd=str(REPO_ROOT), capture_output=True, text=True,
                          timeout=60, check=False)
    match = re.search(r"\{([^}]+)\}", proc.stdout)
    commands = sorted(part.strip() for part in match.group(1).split(",")) \
        if match else []
    return {"help_returncode": proc.returncode, "declared": commands}


def main() -> int:
    args = parse_out_args(__doc__)
    with tempfile.TemporaryDirectory(prefix="mgs-baseline-entry-") as tmp:
        workdir = Path(tmp)
        good, bad = build_fixtures(workdir)
        empty = workdir / "empty"
        empty.mkdir()
        cases = [
            {"case": "config-success", "project": good, "argv": ["config"]},
            {"case": "list-success", "project": good, "argv": ["list"]},
            {"case": "show-success", "project": good,
             "argv": ["show", "--task", "01-alpha"]},
            {"case": "show-task-missing", "project": good,
             "argv": ["show", "--task", "99-missing"]},
            {"case": "deps-success", "project": good, "argv": ["deps"]},
            {"case": "deps-unresolved-failure", "project": bad, "argv": ["deps"]},
            {"case": "ready-success", "project": good, "argv": ["ready"]},
            {"case": "ready-blocked-still-ok", "project": bad, "argv": ["ready"]},
            {"case": "baseline-success", "project": good, "argv": ["baseline"]},
            {"case": "verify-success", "project": good, "argv": ["verify"]},
            {"case": "config-missing-failure", "project": empty,
             "argv": ["config"]},
        ]
        results = []
        for case in cases:
            outcome = run_entry(case["project"], *case["argv"])
            outcome["case"] = case["case"]
            results.append(outcome)
        report = {
            "evidence_kind": "static_fact + existing_entry_run",
            "scope": ("隔离 /tmp 临时项目;经现有命令行入口实跑 local-markdown "
                      "后端的读取命令;零网络、零凭据、零真实远端写入;"
                      "只记录 JSON 结构与退出码,不记录取值"),
            "declared_subcommands": declared_subcommands(),
            "covered_read_entries": list(READ_ENTRIES),
            "not_covered": {
                "commands": list(NOT_COVERED),
                "reason": ("github-issues 专属或需要远端/凭据的入口;"
                           "现有 CLI 未提供 transport 注入,本次零网络覆盖不含"),
            },
            "cases": results,
            "summary": {
                "exit_code_contract": {
                    "success": 0,
                    "records_or_file_error": 2,
                    "judgement_failure": 1,
                },
                "observed_returncodes": {
                    entry["case"]: entry["returncode"] for entry in results},
            },
        }
    emit(report, args.out)
    return 0


if __name__ == "__main__":
    sys.exit(main())

#!/usr/bin/env python3
"""票 01 基线总入口:在隔离、可复跑的条件下固定并记录兼容与效率基线。

执行内容(全部离线;不启动真实模型、不访问网络、不做任何远端写入):
1. 运行现有五套确定性检查(tests/test_*.py),逐套保留完整 stdout 与退出码。
2. 运行四个基线探针:代码身份、records 读取计数与 R1 复现、客户端五族与
   解码计数、代码量统计。
3. 汇总为 baseline.json,并生成人可读的 BASELINE-REPORT.md。

用法(sh -c 或 bash 均可,仓库根或任意路径调用):
  python3 .scratch/mygamestudio-architecture-refactor/evidence/baseline/run_baseline.py
可选:--results-dir <目录>(默认本目录/results)
"""

import argparse
import datetime as dt
import json
import platform
import subprocess
import sys
import time
from pathlib import Path

EVIDENCE_DIR = Path(__file__).resolve().parent
REPO_ROOT = EVIDENCE_DIR.parents[3]
SUITES = (
    "test_plugin_package",
    "test_runtime_gate",
    "test_runtime_boundaries",
    "test_records_backend",
    "test_github_backend",
)
PROBES = {
    "code_identity": EVIDENCE_DIR / "code_identity.py",
    "records_probe": EVIDENCE_DIR / "records_probe.py",
    "client_probe": EVIDENCE_DIR / "client_probe.py",
    "code_volume": EVIDENCE_DIR / "code_volume.py",
}


def run(cmd: list[str], *, timeout: int = 1800) -> dict:
    started = time.time()
    proc = subprocess.run(cmd, cwd=str(REPO_ROOT), capture_output=True,
                          text=True, timeout=timeout, check=False)
    return {
        "command": " ".join(cmd),
        "returncode": proc.returncode,
        "duration_seconds": round(time.time() - started, 3),
        "stdout": proc.stdout,
        "stderr": proc.stderr,
    }


def run_probe(name: str, out_path: Path) -> dict:
    result = run([sys.executable, "-B", str(PROBES[name]), "--out", str(out_path)])
    result["output_path"] = str(out_path.relative_to(REPO_ROOT))
    result["report"] = json.loads(out_path.read_text(encoding="utf-8"))
    return result


def run_suite(name: str, out_path: Path) -> dict:
    result = run([sys.executable, "-B", str(REPO_ROOT / "tests" / f"{name}.py")])
    out_path.write_text(result["stdout"] + "\n--- stderr ---\n" + result["stderr"],
                        encoding="utf-8")
    result["raw_output_path"] = str(out_path.relative_to(REPO_ROOT))
    result["ok"] = result["returncode"] == 0
    return result


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--results-dir",
                        default=str(EVIDENCE_DIR / "results"))
    args = parser.parse_args()
    results_dir = Path(args.results_dir)
    checks_dir = results_dir / "checks"
    checks_dir.mkdir(parents=True, exist_ok=True)

    git = subprocess.run(["git", "-C", str(REPO_ROOT), "status", "--porcelain"],
                         capture_output=True, text=True, check=False)
    porcelain = [line for line in git.stdout.splitlines() if line.strip()]
    # 本票开始时代码工作区应干净。两类未跟踪项不属于产品改动,如实保留在
    # porcelain 清单里,但不算作本期改动:
    #   - evidence/baseline/*:本票新增的基线产物;
    #   - execution-log.md:主控代理维护的全局进度文件(非本票文件)。
    non_product = ("evidence/baseline",
                   "mygamestudio-architecture-refactor/execution-log.md")
    production_changes = [line for line in porcelain
                          if not any(marker in line for marker in non_product)]
    worktree_clean_at_start = not production_changes

    suites = [run_suite(name, checks_dir / f"{name}.txt") for name in SUITES]
    probes = {name: run_probe(name, results_dir / f"{name}.json")
              for name in PROBES}

    baseline = {
        "ticket": "01-behavior-baseline",
        "generated_at": dt.datetime.now().astimezone().isoformat(timespec="seconds"),
        "environment": {
            "platform": platform.platform(),
            "python": sys.version.split()[0],
            "worktree_clean_excluding_baseline_artifacts": worktree_clean_at_start,
            "worktree_porcelain_at_start": porcelain,
        },
        "evidence_classes": {
            "static_fact": ["code_identity", "code_volume", "client_family_inventory"],
            "synthetic_replay": ["records_probe", "client_decode_probe"],
            "existing_checks": ["tests/test_*.py 五套"],
            "real_acceptance": ("未在本票执行(真实模型轮/真实远端写入保留待授权);"
                                "历史结果见 dist/ACCEPTANCE-RESULTS.md,仅作引用"),
        },
        "check_suites": [
            {"name": s["command"].rsplit("/", 1)[-1].removesuffix(".py"),
             "command": s["command"], "returncode": s["returncode"],
             "ok": s["ok"], "duration_seconds": s["duration_seconds"],
             "raw_output_path": s["raw_output_path"],
             "summary": s["stdout"].strip().splitlines()[-1] if s["stdout"].strip() else ""}
            for s in suites
        ],
        "probes": {
            name: {"command": p["command"], "returncode": p["returncode"],
                   "output_path": p["output_path"], "report": p["report"]}
            for name, p in probes.items()
        },
    }
    all_checks_green = all(s["ok"] for s in suites)
    baseline["all_existing_checks_green"] = all_checks_green
    baseline_path = results_dir / "baseline.json"
    baseline_path.write_text(json.dumps(baseline, ensure_ascii=False, indent=2) + "\n",
                             encoding="utf-8")

    write_report(baseline, EVIDENCE_DIR / "BASELINE-REPORT.md")
    print("check suites:")
    for entry in baseline["check_suites"]:
        print(f"  {'PASS' if entry['ok'] else 'FAIL'} {entry['name']} "
              f"(exit {entry['returncode']}, {entry['duration_seconds']}s)")
    print(f"all_existing_checks_green={all_checks_green}")
    print(f"baseline written: {baseline_path.relative_to(REPO_ROOT)}")
    return 0


def write_report(baseline: dict, out_path: Path) -> None:
    checks = baseline["check_suites"]
    rec = baseline["probes"]["records_probe"]["report"]["observations"]
    local_ready = next(o for o in rec if o["probe"] == "ready"
                       and o["backend"] == "local-markdown")
    local_r1 = next(o for o in rec if o["probe"] == "ready-changing-second-fetch"
                    and o["backend"] == "local-markdown")
    gh_r1 = next(o for o in rec if o["probe"] == "ready-changing-second-fetch"
                 and o["backend"] == "github-issues")
    identity = baseline["probes"]["code_identity"]["report"]
    volume = baseline["probes"]["code_volume"]["report"]
    client = baseline["probes"]["client_probe"]["report"]
    lines = []
    lines.append("# 票 01 行为与效率基线报告")
    lines.append("")
    lines.append(f"- 生成时间:{baseline['generated_at']}")
    lines.append(f"- 平台/解释器:{baseline['environment']['platform']} / "
                 f"Python {baseline['environment']['python']}")
    lines.append(f"- HEAD:{identity['head_sha']}(分支 {identity['branch']})")
    lines.append(f"- 插件版本:{identity['plugin']['name']} {identity['plugin']['version']}")
    env = baseline["environment"]
    lines.append(f"- 开始时排除基线产物的工作区是否干净:"
                 f"{'是' if env.get('worktree_clean_excluding_baseline_artifacts') else '否'}"
                 "(本票零产品行为变更)")
    lines.append("")
    lines.append("## 1. 现有五套确定性检查(实跑结果)")
    lines.append("")
    lines.append("| 套件 | 结果 | 退出码 | 耗时(s) | 原始输出 |")
    lines.append("| --- | --- | --- | --- | --- |")
    for entry in checks:
        lines.append(f"| {entry['name']} | {'PASS' if entry['ok'] else 'FAIL'} | "
                     f"{entry['returncode']} | {entry['duration_seconds']} | "
                     f"`{entry['raw_output_path']}` |")
    lines.append("")
    lines.append(f"五套合计:{'全部通过' if baseline['all_existing_checks_green'] else '存在失败,见上表'}。")
    lines.append("")
    lines.append("## 2. 代码身份与六方向覆盖")
    lines.append("")
    for f in identity["production_files"]:
        lines.append(f"- `{f['path']}`:{f['lines']} 行,sha256 `{f['sha256'][:16]}…`")
    lines.append(f"- 生产代码合计:{identity['production_total_lines']} 行")
    lines.append("")
    lines.append("| 重构方向 | 规范/设计入口 |")
    lines.append("| --- | --- |")
    for direction, refs in identity["six_refactor_directions"].items():
        lines.append(f"| {direction} | {', '.join('`' + r + '`' for r in refs)} |")
    lines.append("")
    lines.append("## 3. 读取计数与 R1 缺陷证据(合成回放)")
    lines.append("")
    lines.append(f"- 本地 ready:CONFIG.md {local_ready['reads']['CONFIG.md']} 次,"
                 f"task.md {local_ready['reads']['task.md']} 次,"
                 f"最终 startable={local_ready['startable']}")
    lines.append(f"- 本地 R1(第二次任务读取改变依赖):任务集合读取 "
                 f"{local_r1['task_list_reads']} 次;结果落在 "
                 f"{local_r1['result_side']};原因 "
                 f"{local_r1['blocked']['reasons'] if local_r1.get('blocked') else '-'}")
    lines.append(f"- GitHub R1:全量任务集合获取 {gh_r1['transport_task_list_requests']} 次"
                 f"(替身;真实远端请求 0);结果落在 {gh_r1['result_side']}")
    lines.append("")
    lines.append("> 这是既有缺陷的复现证据,不是长期正确性断言;普通检查套件保持全绿。")
    lines.append("")
    lines.append("## 4. 客户端五族与解码计数(合成回放)")
    lines.append("")
    lines.append(f"- 客户端 {client['client_count']} 份 / {client['total_client_lines']} 行,"
                 f"归一后 {client['family_count']} 个行为族")
    for i, family in enumerate(client["families"]):
        lines.append(f"  - 族 {i}({family['count']} 份):{', '.join(family['members'])}")
    decode = client["decode_probe"]
    lines.append(f"- {decode['input_lines']} 条固定事件、{decode['poll_iterations']} 次轮询:"
                 f"json.loads {decode['json_loads_calls']} 次(network={decode['network_requests']}, "
                 f"model_calls={decode['model_calls']})")
    lines.append("")
    lines.append("## 5. 代码量统计与回退参照")
    lines.append("")
    lines.append(f"- 口径:{volume['counting_scope']}")
    for area, data in volume["areas"].items():
        lines.append(f"  - {area}:{data['files']} 文件 / {data['lines']} 行")
    lines.append(f"- 客户端共享化净减潜力(规划估计):"
                 f"{volume['client_dedup']['estimated_net_reduction_lines']} 行")
    lines.append(f"- 回退参照:本票前基点 `{volume['rollback']['ticket_pre_base_commit']}`")
    lines.append("")
    lines.append("## 6. 证据分类与未验证限制")
    lines.append("")
    lines.append("- 静态事实:代码身份(SHA/指纹/行数)、代码量统计、客户端族清单。")
    lines.append("- 合成回放:records 读取计数与 R1 复现、客户端解码计数(替身/合成,零网络)。")
    lines.append("- 现有检查:五套 `tests/test_*.py` 的本次真实退出码与输出。")
    lines.append("- 真实验收:本票未执行真实模型轮或真实远端写入;历史结果见 "
                 "`dist/ACCEPTANCE-RESULTS.md`,仅作引用,不替代本次实测。")
    lines.append(f"- 后续比较方法:{volume['comparison_method']}")
    lines.append("")
    out_path.write_text("\n".join(lines), encoding="utf-8")


if __name__ == "__main__":
    sys.exit(main())

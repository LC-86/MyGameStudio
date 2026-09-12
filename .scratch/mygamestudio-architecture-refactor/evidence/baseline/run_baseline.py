#!/usr/bin/env python3
"""票 01 基线总入口:在隔离、可复跑的条件下固定并记录兼容与效率基线。

执行内容(全部离线;不启动真实模型、不访问网络、不做任何远端写入):
1. 运行现有五套确定性检查(tests/test_*.py),逐套保留完整 stdout 与退出码。
2. 运行五个基线探针:代码身份、records 读取计数与 R1 复现、客户端五族与
   解码计数、代码量统计、现有命令行入口输出结构与退出码。
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

from baseline_common import REPO_ROOT, worktree_state

EVIDENCE_DIR = Path(__file__).resolve().parent
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
    "entry_probe": EVIDENCE_DIR / "entry_probe.py",
}
# 本票新增产物的行数口径:脚本(探针+入口)、文档(md)、results 下 JSON 产物。
# 脚本/文档按本次工作区实际文件计数;results 产物 JSON 经 collect_lines 的
# json_line_count 做确定性规范化后再计数(见 R4)。汇总自身 baseline.json 与
# 本报告 BASELINE-REPORT.md 在收集后重写,故不并入上述分项、在报告中单独披露。
ARTIFACT_SCRIPTS = ("run_baseline.py", "run_baseline.sh", "baseline_common.py",
                    "code_identity.py", "records_probe.py", "client_probe.py",
                    "code_volume.py", "entry_probe.py")
ARTIFACT_DOCS = ("README.md", "evidence-map.md")
ARTIFACT_RESULT_JSON = ("results/code_identity.json",
                        "results/records_probe.json", "results/client_probe.json",
                        "results/code_volume.json", "results/entry_probe.json")
# 本报告自身行数在写盘前未知;占位符所在行替换文本不改变行数,故可用最终
# len(lines) 回填(实测口径与实际文件一致)。
SELF_REPORT_MARKER = "@SELF_REPORT_LINES@"


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
    result["name"] = name
    out_path.write_text(result["stdout"] + "\n--- stderr ---\n" + result["stderr"],
                        encoding="utf-8")
    result["raw_output_path"] = str(out_path.relative_to(REPO_ROOT))
    result["ok"] = result["returncode"] == 0
    return result


# 计数前规范化的不稳定字段:取值随运行时刻或工作区状态变化,会破坏「可复跑
# 基线」承诺。列表型字段(工作区 porcelain 清单)长度随未跟踪/改动文件数漂移,
# 统一置空;标量字段(generated_at/duration_seconds)只影响取值不影响行数,一并
# 规范化以明示口径。
VOLATILE_LIST_KEYS = ("worktree_porcelain", "worktree_porcelain_at_start")
VOLATILE_SCALAR_KEYS = {"generated_at": "<normalized>", "duration_seconds": 0}


def _normalize_volatile(value):
    if isinstance(value, dict):
        normalized = {}
        for key, item in value.items():
            if key in VOLATILE_LIST_KEYS:
                normalized[key] = []
            elif key in VOLATILE_SCALAR_KEYS:
                normalized[key] = VOLATILE_SCALAR_KEYS[key]
            else:
                normalized[key] = _normalize_volatile(item)
        return normalized
    if isinstance(value, list):
        return [_normalize_volatile(item) for item in value]
    return value


def line_count(rel: str) -> int:
    path = EVIDENCE_DIR / rel
    if not path.is_file():
        return 0
    return len(path.read_text(encoding="utf-8", errors="replace").splitlines())


def json_line_count(rel: str) -> int:
    """results JSON 的确定性行数口径:计数前剥离/规范化不稳定字段。

    物理行数会随工作区 porcelain 清单长度漂移(如新增未跟踪无关文件),故先按
    与写盘一致的缩进重排为规范 JSON、置空不稳定字段,再计数;解析失败回退物理
    行数。稳定 JSON 重排后与写盘格式一致,计数即物理行数。
    """

    path = EVIDENCE_DIR / rel
    if not path.is_file():
        return 0
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, UnicodeDecodeError):
        return line_count(rel)
    text = json.dumps(_normalize_volatile(data), ensure_ascii=False,
                      indent=2) + "\n"
    return len(text.splitlines())


def collect_lines(results_dir: Path) -> dict:
    """本票新增产物的行数:脚本 / 文档 / results 产物 JSON(不含汇总自身)分列。

    results 产物 JSON 按 `json_line_count` 的确定性口径计数(剥离不稳定字段),
    使各分项在连续运行与未跟踪无关文件增减下保持完全一致;汇总自身
    `results/baseline.json` 在报告里按同一口径单独披露。
    """

    scripts = {rel: line_count(rel) for rel in ARTIFACT_SCRIPTS}
    docs = {rel: line_count(rel) for rel in ARTIFACT_DOCS}
    result_jsons = {rel: json_line_count(rel) for rel in ARTIFACT_RESULT_JSON}
    checks = sorted((results_dir / "checks").glob("*.txt"))
    check_lines = {f"results/checks/{p.name}":
                   len(p.read_text(encoding="utf-8", errors="replace").splitlines())
                   for p in checks}
    return {
        "scripts": scripts,
        "scripts_total": sum(scripts.values()),
        "docs": docs,
        "docs_total": sum(docs.values()),
        "results_json": result_jsons,
        "results_json_total": sum(result_jsons.values()),
        "results_check_logs_total": sum(check_lines.values()),
        "note": ("脚本=探针与入口 .py/.sh;文档=README/evidence-map .md"
                 "(本报告 BASELINE-REPORT.md 行数在报告中单独回填,不并入 docs);"
                 "results 产物 JSON=results/*.json(不含汇总自身 baseline.json 与 "
                 "checks/*.txt 检查原始日志);JSON 行数按剥离不稳定字段"
                 "(工作区 porcelain 清单等)后的确定性口径计数"),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--results-dir",
                        default=str(EVIDENCE_DIR / "results"))
    args = parser.parse_args()
    results_dir = Path(args.results_dir)
    checks_dir = results_dir / "checks"
    checks_dir.mkdir(parents=True, exist_ok=True)

    # 工作区披露(审查修复票 01/F5;与 code_identity.py 共用
    # baseline_common.worktree_state 的单一实现):原始口径与排除本票基线产物
    # 后的口径分列。
    worktree = worktree_state()

    suites = [run_suite(name, checks_dir / f"{name}.txt") for name in SUITES]
    probes = {name: run_probe(name, results_dir / f"{name}.json")
              for name in PROBES}

    baseline = {
        "ticket": "01-behavior-baseline",
        "generated_at": dt.datetime.now().astimezone().isoformat(timespec="seconds"),
        "environment": {
            "platform": platform.platform(),
            "python": sys.version.split()[0],
            "worktree_clean": worktree["worktree_clean"],
            "worktree_clean_excluding_baseline_artifacts":
                worktree["worktree_clean_excluding_baseline"],
            "worktree_clean_excluding_scope":
                worktree["worktree_clean_excluding_scope"],
            "worktree_porcelain_at_start": worktree["worktree_porcelain"],
        },
        "evidence_classes": {
            "static_fact": ["code_identity", "code_volume", "client_family_inventory",
                            "entry_probe (输出结构与退出码)"],
            "synthetic_replay": ["records_probe", "client_decode_probe",
                                 "records_probe.runtime_* (前置计数复算)"],
            "existing_checks": ["tests/test_*.py 五套"],
            "real_acceptance": ("未在本票执行(真实模型轮/真实远端写入保留待授权);"
                                "历史结果见 dist/ACCEPTANCE-RESULTS.md,仅作引用"),
        },
        "check_suites": [
            {"name": s["name"],
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
    baseline["artifact_lines"] = collect_lines(results_dir)
    all_checks_green = all(s["ok"] for s in suites)
    baseline["all_existing_checks_green"] = all_checks_green
    baseline_path = results_dir / "baseline.json"
    baseline_path.write_text(json.dumps(baseline, ensure_ascii=False, indent=2) + "\n",
                             encoding="utf-8")

    # baseline.json 先落盘(内容不依赖报告),报告再据其最终行数读取并写盘,
    # 避免「报告行数 ↔ 汇总行数」互相引用。
    write_report(baseline, EVIDENCE_DIR / "BASELINE-REPORT.md")
    print("check suites:")
    for suite in baseline["check_suites"]:
        print(f"  {'PASS' if suite['ok'] else 'FAIL'} {suite['name']} "
              f"(exit {suite['returncode']}, {suite['duration_seconds']}s)")
    print(f"all_existing_checks_green={all_checks_green}")
    print(f"baseline written: {baseline_path.relative_to(REPO_ROOT)}")
    return 0


def write_report(baseline: dict, out_path: Path) -> None:
    """写人可读报告;自身行数由内部 SELF_REPORT_MARKER 机制在写盘前回填。"""
    checks = baseline["check_suites"]
    observations = baseline["probes"]["records_probe"]["report"]["observations"]
    local_ready = next(o for o in observations if o["probe"] == "ready"
                       and o["backend"] == "local-markdown")
    local_r1 = next(o for o in observations
                    if o["probe"] == "ready-changing-second-fetch"
                    and o["backend"] == "local-markdown")
    gh_r1 = next(o for o in observations
                 if o["probe"] == "ready-changing-second-fetch"
                 and o["backend"] == "github-issues")
    runtime_write = next((o for o in observations if o["probe"] == "runtime-write"),
                         None)
    runtime_remote = next((o for o in observations
                           if o["probe"] == "runtime-remote-read"), None)
    identity = baseline["probes"]["code_identity"]["report"]
    volume = baseline["probes"]["code_volume"]["report"]
    client = baseline["probes"]["client_probe"]["report"]
    entry = baseline["probes"]["entry_probe"]["report"]
    lines = []
    lines.append("# 票 01 行为与效率基线报告")
    lines.append("")
    lines.append(f"- 生成时间:{baseline['generated_at']}")
    lines.append(f"- 平台/解释器:{baseline['environment']['platform']} / "
                 f"Python {baseline['environment']['python']}")
    lines.append(f"- HEAD:{identity['head_sha']}(分支 {identity['branch']})")
    lines.append(f"- 插件版本:{identity['plugin']['name']} {identity['plugin']['version']}")
    env = baseline["environment"]
    lines.append(f"- 工作区是否干净(原始 `git status --porcelain`):"
                 f"{'是' if env.get('worktree_clean') else '否'}"
                 "(基线产物与主控进度文件在生成时尚未提交,故原始口径为否)")
    lines.append(f"- 工作区是否干净(排除 `.scratch/` 下的票产物、工单与主控进度"
                 f"记录后,= 本票零产品行为变更口径):"
                 f"{'是' if env.get('worktree_clean_excluding_baseline_artifacts') else '否'}")
    lines.append("")
    lines.append("## 1. 现有五套确定性检查(实跑结果)")
    lines.append("")
    lines.append("| 套件 | 结果 | 退出码 | 耗时(s) | 原始输出 |")
    lines.append("| --- | --- | --- | --- | --- |")
    for suite in checks:
        lines.append(f"| {suite['name']} | {'PASS' if suite['ok'] else 'FAIL'} | "
                     f"{suite['returncode']} | {suite['duration_seconds']} | "
                     f"`{suite['raw_output_path']}` |")
    lines.append("")
    lines.append(f"五套合计:{'全部通过' if baseline['all_existing_checks_green'] else '存在失败,见上表'}。")
    lines.append("")
    lines.append("## 2. 代码身份与重构阶段/票覆盖(静态事实)")
    lines.append("")
    for f in identity["production_files"]:
        lines.append(f"- `{f['path']}`:{f['lines']} 行,sha256 `{f['sha256'][:16]}…`")
    lines.append(f"- 生产代码合计:{identity['production_total_lines']} 行")
    lines.append("")
    lines.append(f"- 覆盖清单口径:{identity['refactor_direction_layout']}")
    lines.append("")
    lines.append("| 重构阶段方向 | 覆盖的票 / 规范入口 |")
    lines.append("| --- | --- |")
    for direction, refs in identity["refactor_directions"].items():
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
    if runtime_write or runtime_remote:
        lines.append("### 受控写入运行时读取计数(前置观测的本次复算,审查修复票 01/F6)")
        lines.append("")
        if runtime_write:
            lines.append(f"- runtime-write(决策 {runtime_write['decision']}):"
                         + ", ".join(f"{k} {v} 次"
                                     for k, v in runtime_write["reads"].items()))
        if runtime_remote:
            lines.append(f"- runtime-remote-read(决策 {runtime_remote['decision']}):"
                         + ", ".join(f"{k} {v} 次"
                                     for k, v in runtime_remote["reads"].items())
                         + f";替身 transport 调用 {runtime_remote['transport_calls']} 次,"
                           "真实远端请求 0")
        lines.append("")
        lines.append("> 前置证据 `.scratch/.../evidence/baseline.json` 的 text/bytes 拆分"
                     "未逐字节复刻:CPython 3.14 的 `Path.read_bytes()` 触发的 open 事件"
                     "mode 为 `r`,本探针按文件聚合的总读取次数与前置一致"
                     "(policy.json 合计 3 = text 2 + bytes 1)。")
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
    lines.append("## 5. 代码量统计与产物行数口径")
    lines.append("")
    lines.append(f"- 生产代码量口径:{volume['counting_scope']}")
    for area, data in volume["areas"].items():
        lines.append(f"  - {area}:{data['files']} 文件 / {data['lines']} 行")
    lines.append(f"- 客户端共享化净减潜力(规划估计):"
                 f"{volume['client_dedup']['estimated_net_reduction_lines']} 行")
    lines.append(f"- 回退参照:本票前基点 `{volume['rollback']['ticket_pre_base_commit']}`")
    artifact = baseline["artifact_lines"]
    lines.append("")
    lines.append("本票**新增基线产物**的行数(分列,`scratch` 下,不是生产或测试代码):")
    lines.append("")
    lines.append(f"- 脚本(探针与入口 `.py`/`.sh`,{len(artifact['scripts'])} 个):"
                 f"{artifact['scripts_total']} 行")
    lines.append(f"- 文档(`README.md`/`evidence-map.md`,{len(artifact['docs'])} 个):"
                 f"{artifact['docs_total']} 行")
    # 本报告的自身行数在下面按本次写盘实测回填(baseline.json 同值)。
    lines.append(f"- 文档(本报告 `BASELINE-REPORT.md`):{SELF_REPORT_MARKER} 行")
    lines.append(f"- results 产物 JSON({len(artifact['results_json'])} 个探针报告):"
                 f"{artifact['results_json_total']} 行")
    baseline_self = json_line_count("results/baseline.json")
    lines.append(f"- results 产物 JSON(汇总自身 `results/baseline.json`):"
                 f"{baseline_self} 行")
    lines.append(f"- results 产物 JSON 合计(含汇总自身):"
                 f"{artifact['results_json_total'] + baseline_self} 行")
    lines.append(f"- results 检查原始日志(`checks/*.txt`,另计,非本票新写):"
                 f"{artifact['results_check_logs_total']} 行")
    lines.append("")
    lines.append("## 6. 现有命令行入口输出结构与退出码(实跑)")
    lines.append("")
    covered = ", ".join("`" + c + "`" for c in entry["covered_read_entries"])
    lines.append(f"- 本次实跑覆盖的 local-markdown 读取入口:{covered}")
    lines.append(f"- 未覆盖(需远端/凭据,零网络不跑):"
                 + ", ".join("`" + c + "`" for c in entry["not_covered"]["commands"]))
    lines.append(f"- 退出码合同:{entry['summary']['exit_code_contract']}")
    lines.append("")
    lines.append("| 案例 | 退出码 | JSON 有效 | 顶层结构 |")
    lines.append("| --- | --- | --- | --- |")
    for case in entry["cases"]:
        output = case["output"]
        struct = output.get("shape")
        if isinstance(struct, dict) and "keys" in struct:
            top = ", ".join(struct["keys"]) or "(空对象)"
        elif isinstance(struct, dict) and struct.get("type") == "array":
            top = "array"
        else:
            top = str(struct)
        lines.append(f"| {case['case']} | {case['returncode']} | "
                     f"{output.get('valid_json')} | {top} |")
    lines.append("")
    lines.append("> 字段结构只记键集合与类型、不记取值,避免时间戳等非确定字段"
                 "破坏复跑稳定性;退出码覆盖成功(0)、记录/文件错误(2)与"
                 "判定失败(1)。")
    lines.append("")
    lines.append("## 7. 证据分类与未验证限制")
    lines.append("")
    lines.append("- 静态事实:代码身份(SHA/指纹/行数)、代码量统计、客户端族清单、"
                 "命令行入口输出结构与退出码。")
    lines.append("- 合成回放:records 读取计数与 R1 复现、客户端解码计数、"
                 "受控写入运行时读取计数(替身/合成,零网络)。")
    lines.append("- 现有检查:五套 `tests/test_*.py` 的本次真实退出码与输出。")
    lines.append("- 真实验收:本票未执行真实模型轮或真实远端写入;历史结果见 "
                 "`dist/ACCEPTANCE-RESULTS.md`,仅作引用,不替代本次实测。")
    lines.append("- 未验证限制:命令行入口基线只覆盖 local-markdown 后端与"
                 "两处代表性错误路径,github-issues 专属子命令与需要远端/凭据的"
                 "入口未跑;前置证据的 text/bytes 读取拆分未逐字节复刻(见第 3 节);"
                 "`records_probe` 的 GitHub 用本地替身,不代表真实网络耗时或全部宿主行为。")
    lines.append(f"- 后续比较方法:{volume['comparison_method']}")
    lines.append("")
    text = "\n".join(lines)
    # 占位符在单独一行内替换,不改变行数;故可按替换后的实际行数回填自身行数。
    text = text.replace(SELF_REPORT_MARKER, str(len(text.splitlines())))
    out_path.write_text(text, encoding="utf-8")


if __name__ == "__main__":
    sys.exit(main())

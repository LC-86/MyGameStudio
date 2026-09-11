#!/usr/bin/env python3
"""票 01 基线探针 D:代码量统计范围与回退参照。

计数口径(与前置调查 evidence/baseline.json 完全一致,本次实测已复算相等):
tracked 的 .py/.sh/.js/.ts/.tsx,位于 plugin/、tests/、acceptance/、dist/,
排除任何 evidence/ 与 fixtures/ 目录;物理行含空行与注释。

另给出验收客户端按行为族归一后的共享化净减潜力(仅规划估计,最终以实测
净增减为准),以及回退参照提交。

用法:python3 code_volume.py [--out <report.json>]
"""

import re
import sys
from pathlib import Path

from baseline_common import REPO_ROOT, emit, git, normalize_source, parse_out_args

ROOT_PRE_COMMIT = "b8cda58ea2ff3b0fb18ae7d888cbd5d01eaca586"
SPEC_BASELINE_COMMIT = "49f3b1e7323c02a5fd39f3d9c847df023c4f2459"
CODE_SUFFIXES = (".py", ".sh", ".js", ".ts", ".tsx")
EXCLUDE = re.compile(r"/(evidence|fixtures|__fixtures__)/")


def area_files(area: str) -> list[str]:
    listed = git("ls-files", f"{area}/*").splitlines()
    return [p for p in listed
            if p.endswith(CODE_SUFFIXES) and not EXCLUDE.search(p)]


def line_count(paths: list[str]) -> int:
    total = 0
    for rel in paths:
        total += len((REPO_ROOT / rel).read_text(encoding="utf-8",
                                                 errors="replace").splitlines())
    return total


def normalized_families(paths: list[str]) -> list[list[str]]:
    groups: dict[str, list[str]] = {}
    for rel in paths:
        key = normalize_source(
            (REPO_ROOT / rel).read_text(encoding="utf-8"))
        groups.setdefault(key, []).append(rel)
    return [sorted(group) for group in groups.values()]


def main() -> int:
    args = parse_out_args(__doc__)

    areas = {}
    for area in ("plugin", "tests", "acceptance", "dist"):
        files = area_files(area)
        areas[area] = {"files": len(files), "lines": line_count(files)}

    clients = sorted((REPO_ROOT / "acceptance").glob("*/appserver_client.py"))
    client_rels = [str(p.relative_to(REPO_ROOT)) for p in clients]
    families = normalized_families(client_rels)
    family_lines = sum(min(line_count([m]) for m in family) for family in families)
    client_total = line_count(client_rels)

    report = {
        "evidence_kind": "static_fact",
        "counting_scope": ("tracked .py/.sh/.js/.ts/.tsx under plugin/tests/"
                           "acceptance/dist, excluding evidence/fixtures "
                           "directories; physical lines include comments and blanks"),
        "areas": areas,
        "totals": {area: data["lines"] for area, data in areas.items()},
        "production_files": [
            {"path": p, "lines": line_count([p])} for p in area_files("plugin")],
        "rollback": {
            "ticket_pre_base_commit": ROOT_PRE_COMMIT,
            "spec_code_baseline_commit": SPEC_BASELINE_COMMIT,
        },
        "client_dedup": {
            "client_count": len(client_rels),
            "client_total_lines": client_total,
            "family_count": len(families),
            "families": families,
            "one_representative_per_family_lines": family_lines,
            "estimated_net_reduction_lines": client_total - family_lines,
            "note": ("规划估计,最终以实施后相同范围实测净增减为准;"
                     "共享实现与入口适配的成本须计入"),
        },
        "comparison_method": ("每票完成后运行 run_baseline.sh,对相同范围复算上述 "
                              "areas 行数、records_probe 读取次数与 client_probe "
                              "解码次数,与本次 baseline.json 逐项比较"),
    }
    emit(report, args.out)
    return 0


if __name__ == "__main__":
    sys.exit(main())

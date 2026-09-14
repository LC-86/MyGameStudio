#!/usr/bin/env python3
"""票 09 取证脚本:逐测试函数复跑设计问答各票测试,输出函数级结果。

只调度既有测试文件里的 ``test_*`` 函数并读取它们自己收集的失败项;
不重写断言、不新增产品行为。逐函数结果用于把 25 个验收场景映射到
实际复跑证据(报告里引用的就是本脚本的真实输出),写到同目录的
``scenario-test-results.json``。

    python3 -B \
        .scratch/design-discussion-rounds/evidence/verify_scenario_tests.py
"""

from __future__ import annotations

import importlib
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO_ROOT = HERE.parent.parent.parent
TESTS = REPO_ROOT / "tests"

THEMES = (
    "test_design_discussion_rounds",
    "test_design_discussion_decisions",
    "test_design_discussion_spec_draft",
    "test_design_discussion_full_design",
    "test_design_discussion_change_flow",
    "test_design_discussion_feature_removal",
    "test_design_discussion_incremental_checks",
    "test_design_discussion_metrics",
)


def main() -> int:
    if str(TESTS) not in sys.path:
        sys.path.insert(0, str(TESTS))
    report: dict[str, list[dict[str, object]]] = {}
    total = passed = 0
    for theme in THEMES:
        module = importlib.import_module(theme)
        failures = getattr(module, "FAILURES")
        names = sorted(n for n in vars(module) if n.startswith("test_"))
        rows: list[dict[str, object]] = []
        for name in names:
            before = len(failures)
            try:
                getattr(module, name)()
                new = failures[before:]
                ok = not new
            except Exception as exc:  # 测试自身抛错也算失败,如实记录
                new = [f"{type(exc).__name__}: {exc}"]
                ok = False
            total += 1
            passed += int(ok)
            rows.append({"test": name, "ok": ok, "failures": new})
            status = "OK" if ok else "FAIL"
            print(f"{status}: {theme}::{name}")
            for item in new:
                print(f"    - {item}")
        report[theme] = rows
    print(f"\nSUMMARY: {passed}/{total} test functions passed")
    out = HERE / "scenario-test-results.json"
    out.write_text(
        json.dumps({"passed": passed, "total": total, "themes": report},
                   ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(f"wrote {out}")
    return 0 if passed == total else 1


if __name__ == "__main__":
    sys.exit(main())

#!/usr/bin/env python3
"""本地 Markdown 任务后端统一接口的确定性检查(任务票 04,票 08 扩展,票 11 分主题)。

总入口:本文件聚合票 11 从原文件拆出的全部行为主题,仍返回完整的通过或失败
结果,运行方式不变:

    python3 -B tests/test_records_backend.py

各主题各自可独立运行(见下),失败能定位到具体职责;共享准备代码集中在
tests/records_backend_support.py,判定仍经 mgs_records 公开接缝作出。

覆盖:读取(配置/列表/单任务与 CLI)、核验、依赖与可开工集合、核心基线指纹、
共享正文与来源归属、公开接口兼容面。

接缝说明:本脚本只覆盖 mgs_records 的公开接缝——load_config / list_tasks /
read_task / verify_project 与 task_dependencies / startable_tasks /
baseline_report 各逻辑操作与其 CLI。真实初始化(探查、清单确认、按角色应用
写入)由 acceptance/04 的隔离验收覆盖,本脚本不替代。"""

import importlib.util
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]

# 行为主题(文件, 标题):聚合顺序即原总入口的历史顺序。
THEMES = (
    ("test_records_read.py", "本地后端读取(配置/列表/单任务)"),
    ("test_records_verify.py", "本地与 GitHub 后端核验"),
    ("test_records_deps_ready.py", "依赖解析与可开工集合"),
    ("test_records_baseline.py", "核心基线指纹与受影响任务"),
    ("test_records_shared_body.py", "共享正文、来源归属与错误身份"),
    ("test_records_interface.py", "公开接口兼容面"),
)


def _load_module(filename: str):
    path = REPO_ROOT / "tests" / filename
    spec = importlib.util.spec_from_file_location(path.stem, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[path.stem] = module
    spec.loader.exec_module(module)
    return module


def main() -> int:
    failures: list[str] = []
    for filename, title in THEMES:
        module = _load_module(filename)
        for test in module.TESTS:
            test()
        failures.extend(module.FAILURES)
    if failures:
        print(f"FAIL ({len(failures)} 项):")
        for failure in failures:
            print(f"  - {failure}")
        return 1
    print("OK: 本地 Markdown 任务后端统一接口检查全部通过")
    return 0


if __name__ == "__main__":
    sys.exit(main())

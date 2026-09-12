#!/usr/bin/env python3
"""间接写入与检查故障的确定性边界检查(任务票 03,任务票 12 分主题)。

总入口:本文件聚合票 12 从原文件按用户可观察的完整故障边界拆出的全部行为
主题,仍返回完整的通过或失败结果,运行方式不变:

    python3 -B tests/test_runtime_boundaries.py

各主题各自可独立运行(见下),失败能定位到具体职责;共享准备代码集中在
tests/runtime_boundary_support.py,判定仍经 mgs_runtime / mcp_gate 公开接缝
(策略故障失效闭合、链接/别名不扩权、可复现路径竞态、通道故障注入)作出。

接缝说明:本脚本覆盖两个公开接缝——
- GateService 公开接缝(可信调度侧 init_policy/create_instance/release_instance,
  工作实例侧 scope/write)的策略故障失效闭合、链接/别名不扩权、可复现路径竞态;
- mcp_gate.py 通道接缝(真实子进程 JSON-RPC over stdio)的检查器故障注入:
  缺失、未启用、损坏、审计不可用、启动失败。
真实 Codex 调用路径(沙箱内命令/子进程/持续进程、模型行为)由
acceptance/03-indirect-write-failure/ 覆盖,本脚本不替代。

覆盖:策略故障与路径竞态边界(策略缺失/损坏/结构无效、符号/目录/硬链接
别名、FIFO 换链竞态、并发换链压力、版本拒绝、伪造身份与说明文本)、通道
检查器故障注入(未配置/未启用/损坏/审计不可用/运行根不可用)。
"""

import importlib.util
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]

# 行为主题(文件, 标题):聚合顺序即原总入口的历史顺序。
THEMES = (
    ("test_runtime_boundary_service.py", "受控写入策略故障、别名与路径竞态边界"),
    ("test_runtime_boundary_channel.py", "mgs-gate 通道检查器故障注入"),
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
        theme_failures = list(module.FAILURES)
        if theme_failures:
            failures.append(f"[{title}]")
            failures.extend(theme_failures)
    if failures:
        print(f"FAIL ({len(failures)} 项):")
        for failure in failures:
            print(f"  - {failure}")
        return 1
    print("OK: 间接写入与检查故障确定性边界检查全部通过")
    return 0


if __name__ == "__main__":
    sys.exit(main())

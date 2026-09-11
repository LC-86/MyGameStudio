#!/usr/bin/env python3
"""运行保障受控写入服务的确定性检查(任务票 02,任务票 11 扩展二进制载荷,
任务票 12 按完整受控操作分主题)。

总入口:本文件聚合票 12 从原文件按用户可观察的完整受控操作拆出的全部行为
主题,仍返回完整的通过或失败结果,运行方式不变:

    python3 -B tests/test_runtime_gate.py

各主题各自可独立运行(见下),失败能定位到具体职责;共享准备代码集中在
tests/runtime_gate_support.py,判定仍经 mgs_runtime / mcp_gate 公开接缝
(凭据、受控本地写入、受控远端操作、故障恢复)作出。

接缝说明:本脚本覆盖 GateService 的公开接缝——可信调度侧(init_policy /
create_instance / release_instance / reclaim_locks / list_locks)与工作实例
侧(scope / write,含任务票 11 的字节载荷 data/content_base64),以及
mgs_remote 受控远端操作经 mcp_gate 的通道入口。真实 Codex 调用路径(显式
入口、沙箱、MCP 通道、模型行为)由 acceptance/02-role-scoped-write/ 覆盖,
本脚本不替代。

覆盖:受控本地写入(凭据/授权交集/审计完整性)、二进制载荷与通道参数
校验、用途收窄与签发白名单、占用回收与释放缺口、真实多进程并发竞争、
受控远端操作、R1-R4 审查修复批、恢复与部分成功审查修复批。
"""

import importlib.util
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]

# 行为主题(文件, 标题):聚合顺序即原总入口的历史顺序。
THEMES = (
    ("test_runtime_gate_local_write.py", "受控本地写入(凭据/授权交集/审计完整性)"),
    ("test_runtime_gate_binary_channel.py", "二进制载荷与通道参数校验"),
    ("test_runtime_gate_purpose_scope.py", "用途收窄与签发白名单"),
    ("test_runtime_gate_occupancy.py", "占用回收与释放缺口"),
    ("test_runtime_gate_concurrency.py", "真实多进程并发竞争"),
    ("test_runtime_gate_remote.py", "受控远端操作(授权交集与失效闭合)"),
    ("test_runtime_gate_review_fix.py", "审查修复批 R1-R4(撤销/缺省/权限位/审计)"),
    ("test_runtime_gate_recovery_review.py", "恢复与部分成功审查修复批(通道侧)"),
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
    print("OK: 受控写入服务确定性检查全部通过")
    return 0


if __name__ == "__main__":
    sys.exit(main())

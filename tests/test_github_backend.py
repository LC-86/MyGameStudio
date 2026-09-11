#!/usr/bin/env python3
"""GitHub Issues 任务后端的确定性检查(任务票 17,票 11 分主题)。

总入口:本文件聚合票 11 从原文件拆出的全部行为主题,仍返回完整的通过或失败
结果,运行方式不变:

    python3 -B tests/test_github_backend.py

各主题各自可独立运行(见下),失败能定位到具体职责;共享准备代码集中在
tests/github_backend_fixtures.py 与 tests/github_backend_transport.py,判定仍经
mgs_records/mgs_github 公开接缝作出。

覆盖:配置与拉取/离线缓存、核验、写操作(授权闸门/防重/超时回读/更新/关系/
关闭)、离线草稿与发布归属、后端切换迁移与交接、CLI 真实入口、结果发布恢复
(部分成功/未知/待补索引碰撞与清除归属)。

接缝说明:本脚本经可注入的替身传输层覆盖 mgs_github(GitHub Issues 后端
适配器)与 mgs_records 对 github-issues 后端分发的公开接缝,不访问真实
GitHub;真实远端写入未在本环境授权,真实远端验收保留待办。"""

import importlib.util
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "tests"))
# 兼容再导出:test_runtime_gate 经本模块取用这些夹具。
from github_backend_fixtures import (  # noqa: E402,F401
    AUTH, FakeTransport, make_github_project,
)
# 行为主题(文件, 标题):聚合顺序即原总入口的历史顺序。
THEMES = (
    ("test_github_config_backend.py", "GitHub 配置、拉取、离线缓存与核验"),
    ("test_github_ready_list_show.py", "一次来源 ready 与列表/单任务读取"),
    ("test_github_write_ops.py", "写操作(授权闸门/防重/超时回读/更新/关系/关闭)"),
    ("test_github_drafts.py", "离线草稿保存与发布归属"),
    ("test_github_migration_handover.py", "后端切换迁移与交接基线可达"),
    ("test_github_cli.py", "GitHub 后端 CLI 真实入口"),
    ("test_github_result_recovery.py", "结果发布的部分成功、未知与重试恢复"),
    ("test_github_pending_index.py", "待补索引登记:碰撞、损坏与旧布局迁移"),
    ("test_github_pending_clear.py", "待补索引清除归属(逐路径核验)"),
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
    print("OK: GitHub Issues 任务后端检查全部通过")
    return 0


if __name__ == "__main__":
    sys.exit(main())

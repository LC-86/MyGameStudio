#!/usr/bin/env python3
"""包与场景验收检查的共享支撑(任务票 10)。

本 module 只提供各行为主题检查共用的最小工具:

- ``check`` / ``FAILURES``:每个主题各自持有失败清单(经 ``make_checker``),
  互不串扰;总入口聚合各主题清单判定整体通过或失败。
- ``REPO_ROOT`` / ``PLUGIN_ROOT`` / ``sha256``:路径与指纹工具。
- ``run_theme``:主题入口统一打印并返回退出码。
- ``load_event_fixtures``:事件判据的具名夹具与案例数据装载。

不在此处放任何判据实现:事件判据仍经 acceptance/18 的 evidence_judgement.py
同一 interface(票 08/09),本 module 只做数据装载与进程内调用。
"""

import hashlib
import json
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
PLUGIN_ROOT = REPO_ROOT / "plugin"
FIXTURE_DATA_PATH = Path(__file__).resolve().parent / "plugin_package_fixtures.json"
# 2.0.2 起安装包在 plugin/ 之外附带根目录许可副本；不在 plugin/ 源码维护第二份正文。
BUNDLED_ROOT_LICENSE_FILES = frozenset({"LICENSE", "THIRD_PARTY_NOTICES.md"})


def bundled_license_source(rel: str, plugin_root: Path = PLUGIN_ROOT) -> Path:
    """许可随包文件对照仓库根；其余路径对照插件源。"""

    if rel in BUNDLED_ROOT_LICENSE_FILES:
        return plugin_root.parent / rel
    return plugin_root / rel


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def make_checker():
    """返回 (FAILURES, check):每个主题文件独立持有,聚合时不互相污染。"""

    failures: list[str] = []

    def check(condition: bool, message: str) -> None:
        if not condition:
            failures.append(message)

    return failures, check


def run_theme(title: str, tests: tuple, failures: list[str]) -> int:
    """依次运行主题内检查函数,统一打印结果并返回进程退出码。"""

    for test in tests:
        test()
    if failures:
        print(f"FAIL ({len(failures)} 项) [{title}]:")
        for failure in failures:
            print(f"  - {failure}")
        return 1
    print(f"OK: {title} 检查全部通过")
    return 0


def load_event_fixtures() -> dict:
    """装载事件判据的具名夹具与案例数据(全部合成值,不含真实凭据)。"""

    return json.loads(FIXTURE_DATA_PATH.read_text(encoding="utf-8"))

#!/usr/bin/env python3
"""验收客户端共享实现的离线测试支撑(票 13)。

只提供各行为主题共用的最小工具:加载客户端/核心 module、以受控替身进程运行
场景入口、以合成回放 adapter 驱动事件等待并统计解码次数。不启动真实模型、
不访问网络、不读取真实凭据;判定仍经共享客户端与场景入口的公开行为作出。
"""

import importlib.util
import json
import os
import shlex
import subprocess
import sys
import threading
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
ACCEPTANCE = REPO_ROOT / "acceptance"
CORE_MODULE = ACCEPTANCE / "_shared" / "appserver_core.py"
FAKE_APPSERVER = REPO_ROOT / "tests" / "fixtures" / "fake_appserver.py"
MIGRATED_SCENARIOS = (
    "02-role-scoped-write",
    "17-github-issue-workflow",
    "18-complete-package-acceptance",
)


def client_path(scenario: str) -> Path:
    return ACCEPTANCE / scenario / "appserver_client.py"


def load_module(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def make_fake_codex(tmpdir: Path) -> Path:
    """生成可执行的 CODEX_BIN 包装脚本,把 argv 交给替身脚本。"""

    wrapper = Path(tmpdir) / "codex"
    wrapper.write_text(
        "#!/bin/sh\n"
        f"exec {shlex.quote(sys.executable)} {shlex.quote(str(FAKE_APPSERVER))} \"$@\"\n",
        encoding="utf-8")
    wrapper.chmod(0o755)
    return wrapper


def run_client(client: Path, args: list[str], tmpdir: Path, *,
               mode: str = "default", identity_log: Path | None = None,
               exit_log: Path | None = None) -> subprocess.CompletedProcess:
    env = os.environ.copy()
    env["CODEX_BIN"] = str(make_fake_codex(tmpdir))
    env["MGS_FAKE_MODE"] = mode
    if identity_log is not None:
        env["MGS_FAKE_CLIENTINFO_LOG"] = str(identity_log)
    if exit_log is not None:
        env["MGS_FAKE_EXIT_LOG"] = str(exit_log)
    return subprocess.run(
        [sys.executable, str(client), *args],
        capture_output=True, text=True, timeout=120, env=env)


class FakeTime:
    """确定性时钟:轮询间隔与超时都按虚拟秒推进,不真实等待。"""

    def __init__(self) -> None:
        self.now = 0.0

    def time(self) -> float:
        return self.now

    def sleep(self, seconds: float) -> None:
        self.now += seconds


class CountingJson:
    """按 json.loads 调用计数的代理;其余属性透传给真实 json。"""

    def __init__(self, real, counter: dict) -> None:
        self._real = real
        self._counter = counter

    def loads(self, *args, **kwargs):
        self._counter["count"] += 1
        return self._real.loads(*args, **kwargs)

    def __getattr__(self, name):
        return getattr(self._real, name)


def replay_wait(module, lines: list[str], *, timeout: float = 10.0,
                collect_events: bool = True,
                wait_times: int = 1) -> tuple[list, list, int]:
    """以合成行驱动 module.AppServer.wait_turn_completed,返回(消息,事件,解码数)。

    经 ``object.__new__`` 构造实例(与票 01 基线探针同法),替换 module 的
    ``time``/``json`` 为虚拟时钟与计数代理,不启动子进程、不访问网络。
    ``wait_times`` 在同一实例上重复等待,用于核对旧事件不被反复解码。
    """

    server = object.__new__(module.AppServer)
    server.lines = list(lines)
    server._lock = threading.Lock()
    server._drained = 0
    counter = {"count": 0}
    real_json, real_time = module.json, module.time
    module.json = CountingJson(real_json, counter)
    module.time = FakeTime()
    events: list[dict] = []
    messages: list = []
    try:
        for _ in range(wait_times):
            messages = server.wait_turn_completed(
                timeout, events if collect_events else None)
    finally:
        module.json = real_json
        module.time = real_time
    return messages, events, counter["count"]


def synthetic_events(count: int) -> list[str]:
    """count 条固定 item/completed 事件(无 turn/completed,用于轮询计数)。"""

    return [
        json.dumps({"method": "item/completed",
                    "params": {"item": {"id": f"a{i}", "type": "agentMessage",
                                        "text": f"message-{i}"}}})
        for i in range(count)
    ]


def find_legacy_client() -> Path | None:
    """定位一份仍使用旧实现的客户端(自身定义 wait_turn_completed)。"""

    for path in sorted(ACCEPTANCE.glob("*/appserver_client.py")):
        if path.parent.name in MIGRATED_SCENARIOS:
            continue
        source = path.read_text(encoding="utf-8")
        if ("def wait_turn_completed" in source and "def drain_events" in source
                and "self.lines" in source):
            return path
    return None

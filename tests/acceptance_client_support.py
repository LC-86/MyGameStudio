#!/usr/bin/env python3
"""验收客户端共享实现的离线测试支撑(票 13)。

只提供各行为主题共用的最小工具:加载客户端/核心 module、以受控替身进程运行
场景入口、以合成回放 adapter 驱动事件等待并统计解码次数。不启动真实模型、
不访问网络、不读取真实凭据;判定仍经共享客户端与场景入口的公开行为作出。
"""

import contextlib
import importlib.util
import inspect
import io
import json
import os
import shlex
import subprocess
import sys
import threading
import types
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
ACCEPTANCE = REPO_ROOT / "acceptance"
CORE_MODULE = ACCEPTANCE / "_shared" / "appserver_core.py"
FAKE_APPSERVER = REPO_ROOT / "tests" / "fixtures" / "fake_appserver.py"
# 已迁移到共享核心的场景,按旧实现的行为族分组(票 13 迁入族 1;票 14 迁入
# 族 2 最小场景与族 3 扩展事件场景)。各族的身份、参数与事件筛选差异保留,
# 不做强制统一。
STANDARD_SCENARIOS = (
    "02-role-scoped-write",
    "17-github-issue-workflow",
    "18-complete-package-acceptance",
)
BASIC_SCENARIOS = ("01-explicit-project-status",)
EXTENDED_EVENT_SCENARIOS = (
    "03-indirect-write-failure",
    "04-initialize-local-project",
)
MIGRATED_SCENARIOS = STANDARD_SCENARIOS + BASIC_SCENARIOS + EXTENDED_EVENT_SCENARIOS
# 票 13 基点提交:仍保有族 1/2/3 旧实现的最后基点,供旧新对照(A/B)读取;
# 工作区已无这些旧文件(按 expand 红线,旧客户端删除留待票 17 收口)。
LEGACY_BASE_COMMIT = "e42d17b4659db09550575d3f29fb32d8074d7829"
BASIC_OLD_CLIENT = "acceptance/01-explicit-project-status/appserver_client.py"
EXTENDED_OLD_CLIENT = "acceptance/03-indirect-write-failure/appserver_client.py"


def client_path(scenario: str) -> Path:
    return ACCEPTANCE / scenario / "appserver_client.py"


def load_module(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def load_git_module(rel: str, name: str, commit: str = LEGACY_BASE_COMMIT):
    """从基点提交读取旧客户端源码并在内存中执行(不写工作区)。"""

    source = subprocess.run(
        ["git", "-C", str(REPO_ROOT), "show", f"{commit}:{rel}"],
        capture_output=True, text=True, check=True).stdout
    module = types.ModuleType(name)
    module.__file__ = f"<{commit}:{rel}>"
    exec(compile(source, module.__file__, "exec"), module.__dict__)
    return module


def load_shared_and_shells(scenarios: tuple, prefix: str = "mgs13_shell_"):
    """真实 import 共享核心与给定场景入口;各入口共享同一 appserver_core 对象。"""

    core = load_module(CORE_MODULE, "appserver_core")
    shells = {}
    for scenario in scenarios:
        name = prefix + scenario.replace("-", "_")
        shells[scenario] = load_module(client_path(scenario), name)
    return core, shells


class SpyServer:
    """替代共享核心的 AppServer,记录入口触发的调用序列(不启动子进程)。"""

    def __init__(self, sink: list) -> None:
        self.calls: list[str] = []
        self.params: list = []
        sink.append(self)

    def request(self, method, params=None, timeout=0):
        self.calls.append(method)
        self.params.append(params)
        if method == "thread/start":
            return {"thread": {"id": "spy-thread"}}
        if method == "skills/list":
            return {"data": [{"skills": [{"name": "s", "scope": "user",
                                          "pluginId": "p", "path": "/x"}]}]}
        return {}

    def wait_turn_completed(self, timeout, events=None):
        if events is not None:
            events.append({"method": "turn/completed", "params": {}})
        return ["spy reply"]

    def close(self) -> None:
        self.calls.append("close")


def spy_calls(core, shell, command: str, namespace) -> tuple[int, list, list]:
    """替换共享核心 AppServer 后调用一份薄壳入口,返回(退出码, 调用序列, 参数)。"""

    original = core.AppServer
    created: list[SpyServer] = []
    core.AppServer = lambda: SpyServer(created)
    try:
        with contextlib.redirect_stdout(io.StringIO()):
            rc = getattr(shell, command)(namespace)
    finally:
        core.AppServer = original
    server = created[-1]
    return rc, server.calls, server.params


def pid_alive(pid: int) -> bool:
    """子进程是否仍存活(仅用于生命周期核对;不用于任何信号发送)。"""

    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    return True


def read_jsonl(path: Path) -> list:
    if not path.is_file():
        return []
    return [json.loads(x) for x in path.read_text(encoding="utf-8").splitlines()
            if x.strip()]


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
    accepts_events = "events" in inspect.signature(
        module.AppServer.wait_turn_completed).parameters
    try:
        for _ in range(wait_times):
            if collect_events and accepts_events:
                messages = server.wait_turn_completed(timeout, events)
            else:
                messages = server.wait_turn_completed(timeout)
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

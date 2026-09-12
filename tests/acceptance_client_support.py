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
# 全共享(票 13–17):十八个场景入口全部委托 acceptance/_shared/appserver_core.py;
# 票 17 已删除被替代的旧物理副本(仅受版本控制、git 历史可回溯)。各族「旧实现」
# 只作为不可变基点提交读取,供旧新对照(A/B)使用,不代表工作区仍有未迁移场景。
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
# 票 15 迁入的族 4:十个绝对阈值中断场景。每份客户端迁移前逐字节同类
# (除场景身份/编号),沿用「--watch-audit/--kill-after-allows 累计 allow 绝对阈值
# + 独立进程组」语义;本批入口共享核心,身份与选项分别保留。
FAMILY4_SCENARIOS = (
    "05-adopt-existing-project",
    "06-idea-to-current-spec",
    "07-isolated-design-prototype",
    "08-spec-to-local-tasks",
    "09-code-task-delivery",
    "10-visual-asset-delivery",
    "11-audio-asset-delivery",
    "12-build-and-run-delivery",
    "13-independent-deliverable-review",
    "14-playtest-and-human-feedback",
)
# 票 16 迁入的族 5:相对中断阈值与完整闭环场景(原 15/16);迁移前两份逐字节同类
# (除场景身份/编号),沿用「--watch-audit/--kill-after-allows 绝对累计 + --kill-relative
# 相对本轮新增 + 独立进程组」语义。本批入口共享核心,身份与选项分别保留。
RELATIVE_SCENARIOS = (
    "15-goal-change-concurrency-recovery",
    "16-producer-complete-loop",
)
MIGRATED_SCENARIOS = (STANDARD_SCENARIOS + BASIC_SCENARIOS + EXTENDED_EVENT_SCENARIOS
                      + FAMILY4_SCENARIOS + RELATIVE_SCENARIOS)
# 票 13 基点提交:保有族 1/2/3 旧实现的最后基点,供旧新对照(A/B)读取;
# 工作区已无这些旧文件(票 17 收口删除;旧实现按基点提交读取,不还原工作区)。
LEGACY_BASE_COMMIT = "e42d17b4659db09550575d3f29fb32d8074d7829"
BASIC_OLD_CLIENT = "acceptance/01-explicit-project-status/appserver_client.py"
EXTENDED_OLD_CLIENT = "acceptance/03-indirect-write-failure/appserver_client.py"
# 票 15 前基点:族 4(05-14)旧实现的最后基点,供绝对中断旧新对照读取。
FAMILY4_BASE_COMMIT = "8f8407f6e30646e16367c52fce538fea202b8327"
FAMILY4_OLD_CLIENT = "acceptance/05-adopt-existing-project/appserver_client.py"
# 票 16 前基点:族 5(15/16)旧实现的最后基点,供相对中断与完整闭环旧新对照读取。
RELATIVE_BASE_COMMIT = "ca431fb44a504bd18f8a180d3501acd02e55d6b3"
RELATIVE_OLD_CLIENT = "acceptance/15-goal-change-concurrency-recovery/appserver_client.py"


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

    def __init__(self, sink: list, **kwargs) -> None:
        self.calls: list[str] = []
        self.params: list = []
        self.init_kwargs = kwargs
        self.wait_polls: list[float] = []
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

    def wait_turn_completed(self, timeout, events=None, poll_seconds=1.0):
        self.wait_polls.append(poll_seconds)
        if events is not None:
            events.append({"method": "turn/completed", "params": {}})
        return ["spy reply"]

    def wait_turn_interruptible(self, timeout, events=None, watch_audit=None,
                                kill_after_allows=0, kill_relative=False):
        self.calls.append(
            f"wait_interruptible:{watch_audit}:{kill_after_allows}"
            f":relative={kill_relative}")
        if events is not None:
            events.append({"method": "turn/completed", "params": {}})
        return ["spy reply"], False

    def close(self) -> None:
        self.calls.append("close")


def spy_calls(core, shell, command: str, namespace) -> tuple[int, list, list]:
    """替换共享核心 AppServer 后调用一份薄壳入口,返回(退出码, 调用序列, 参数)。"""

    rc, server = spy_calls_full(core, shell, command, namespace)
    return rc, server.calls, server.params


def spy_calls_full(core, shell, command: str, namespace) -> tuple[int, SpyServer]:
    """同 ``spy_calls``,但返回 SpyServer 以便核对构造参数(如 new_session)。"""

    original = core.AppServer
    created: list[SpyServer] = []
    core.AppServer = lambda **kwargs: SpyServer(created, **kwargs)
    try:
        with contextlib.redirect_stdout(io.StringIO()):
            rc = getattr(shell, command)(namespace)
    finally:
        core.AppServer = original
    return rc, created[-1]


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


def client_env(tmpdir: Path, *, mode: str = "default",
               identity_log: Path | None = None,
               exit_log: Path | None = None) -> dict:
    """构造受控替身进程的运行环境(CODEX_BIN 指向离线替身;零模型/网络)。"""

    env = os.environ.copy()
    env["CODEX_BIN"] = str(make_fake_codex(tmpdir))
    env["MGS_FAKE_MODE"] = mode
    if identity_log is not None:
        env["MGS_FAKE_CLIENTINFO_LOG"] = str(identity_log)
    if exit_log is not None:
        env["MGS_FAKE_EXIT_LOG"] = str(exit_log)
    return env


def run_client(client: Path, args: list[str], tmpdir: Path, *,
               mode: str = "default", identity_log: Path | None = None,
               exit_log: Path | None = None) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, str(client), *args],
        capture_output=True, text=True, timeout=120,
        env=client_env(tmpdir, mode=mode, identity_log=identity_log,
                       exit_log=exit_log))


def start_client(client: Path, args: list[str], tmpdir: Path, *,
                 mode: str = "default", identity_log: Path | None = None,
                 exit_log: Path | None = None) -> subprocess.Popen:
    """异步启动客户端,供中断测试在运行中推进审计文件(仍为受控替身进程)。"""

    return subprocess.Popen(
        [sys.executable, str(client), *args], stdout=subprocess.PIPE,
        stderr=subprocess.PIPE, text=True,
        env=client_env(tmpdir, mode=mode, identity_log=identity_log,
                       exit_log=exit_log))


def append_audit_allow(path: Path, count: int = 1) -> None:
    """向审计文件追加 count 条受控写入 allow 记录(绝对阈值观察目标)。"""

    with open(path, "a", encoding="utf-8") as fh:
        for index in range(count):
            fh.write(json.dumps({"op": "write", "decision": "allow",
                                 "index": index}, ensure_ascii=False) + "\n")


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


def replay_interrupt(module, lines: list[str], audit: Path,
                     threshold: int, *, kill_relative: bool = False,
                     timeout: float = 5.0) -> tuple[list, bool, list, int]:
    """合成行 + 合成审计文件驱动中断等待(旧 wait_turn_completed / 新 interruptible)。

    经 ``object.__new__`` 构造实例,替换 module 的 ``time``/``json`` 为虚拟时钟与
    计数代理,``kill_process_group`` 记为计数(不发真实信号、不启动子进程)。返回
    (agent 消息, killed, 事件, kill 次数)。``kill_relative=True`` 时使用相对本轮
    新增的阈值语义;旧实现只有该单一方法(默认绝对累计 + 可选相对)。
    """

    server = object.__new__(module.AppServer)
    server.lines = list(lines)
    server._lock = threading.Lock()
    server._drained = 0
    kills: list[int] = []
    server.kill_process_group = lambda: kills.append(1)
    counter = {"count": 0}
    real_json, real_time = module.json, module.time
    module.json = CountingJson(real_json, counter)
    module.time = FakeTime()
    events: list[dict] = []
    # 旧实现(如票 15 基点族 4)只有绝对语义,未含 kill_relative 参数;仅当目标
    # 方法接受该参数时才传递,保持对旧源码的内存执行兼容。
    target = (server.wait_turn_interruptible
              if hasattr(server, "wait_turn_interruptible")
              else server.wait_turn_completed)
    accepts_relative = "kill_relative" in inspect.signature(target).parameters
    kwargs = {"watch_audit": str(audit), "kill_after_allows": threshold}
    if accepts_relative:
        kwargs["kill_relative"] = kill_relative
    try:
        messages, killed = target(timeout, events, **kwargs)
    finally:
        module.json = real_json
        module.time = real_time
    return messages, killed, events, len(kills)


def synthetic_events(count: int) -> list[str]:
    """count 条固定 item/completed 事件(无 turn/completed,用于轮询计数)。"""

    return [
        json.dumps({"method": "item/completed",
                    "params": {"item": {"id": f"a{i}", "type": "agentMessage",
                                        "text": f"message-{i}"}}})
        for i in range(count)
    ]


def all_client_scenarios() -> list[str]:
    """全部验收场景目录名(18 份 entrance;场景身份与参数差异保留)。"""

    return sorted(p.parent.name for p in ACCEPTANCE.glob("*/appserver_client.py"))


def local_client_implementations() -> list[Path]:
    """列出仍自带客户端实现(自定 AppServer / request / 等待与事件消费)的入口。

    全共享时代(票 17 收口后)应当为空:十八个入口只保留场景身份、命令参数与
    事件筛选,经 ``run_turn``/``run_skills`` 委托共享核心。任何一份回归为自带实现
    都会被本函数点名——取代 expand 过渡期「查找未迁移场景」的 ``find_legacy_client``,
    避免其在全共享后恒为 None 而静默通过。
    """

    markers = ("class AppServer", "def request(self", "def wait_turn_completed",
               "def drain_events", "self.lines")
    offenders = []
    for path in sorted(ACCEPTANCE.glob("*/appserver_client.py")):
        source = path.read_text(encoding="utf-8")
        if any(marker in source for marker in markers):
            offenders.append(path)
    return offenders

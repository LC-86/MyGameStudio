#!/usr/bin/env python3
"""票 13 证据探针:共享客户端解码计数与旧新可观察结果对照(全部离线)。

- 解码计数:用与票 01 ``client_probe.py`` 相同的方法(1000 条固定事件、10 次
  轮询,计数器替换 ``json.loads``)分别驱动
  (a) 票 13 迁移前基点 ``e42d17b`` 的旧客户端实现,与 (b) 迁移后的共享实现。
- 旧新对照(A/B):同一合成输入(含重复 key/文本与 turn/completed)下比较
  ``wait_turn_completed`` 的 agent 消息与事件增量消费结果。
- 行数:三个标准事件入口 + 共享核心 module 的物理行数。

不启动子进程、不访问网络、不启动真实模型;不代表端到端加速倍数。

用法:python3 13-client-evidence.py [--out <report.json>]
"""

import argparse
import importlib.util
import json
import subprocess
import sys
import threading
import types
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO_ROOT = HERE.parents[2]
BASE_COMMIT = "e42d17b4659db09550575d3f29fb32d8074d7829"
OLD_CLIENT_REL = "acceptance/02-role-scoped-write/appserver_client.py"
SHARED_REL = "acceptance/_shared/appserver_core.py"
MIGRATED = ("acceptance/02-role-scoped-write/appserver_client.py",
            "acceptance/17-github-issue-workflow/appserver_client.py",
            "acceptance/18-complete-package-acceptance/appserver_client.py")
EVENT_COUNT = 1000
POLLS = 10


def load_source(source: str, name: str):
    module = types.ModuleType(name)
    module.__file__ = f"<{name}>"
    exec(compile(source, module.__file__, "exec"), module.__dict__)
    return module


def load_file(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class Clock:
    def __init__(self):
        self.now = 0.0

    def time(self):
        return self.now

    def sleep(self, seconds):
        self.now += seconds


class CountingJson:
    def __init__(self, real, counter):
        self._real = real
        self._counter = counter

    def loads(self, *args, **kwargs):
        self._counter["count"] += 1
        return self._real.loads(*args, **kwargs)

    def __getattr__(self, name):
        return getattr(self._real, name)


def synthetic_lines(count):
    return [json.dumps({"method": "item/completed",
                        "params": {"item": {"id": f"a{i}", "type": "agentMessage",
                                            "text": f"message-{i}"}}})
            for i in range(count)]


def replay(module, lines, timeout=10.0):
    """与票 01 完全同法:单次 wait_turn_completed(10.0),虚拟时钟推进 10 轮。"""

    server = object.__new__(module.AppServer)
    server.lines = list(lines)
    server._lock = threading.Lock()
    server._drained = 0
    counter = {"count": 0}
    real_json, real_time = module.json, module.time
    module.json = CountingJson(real_json, counter)
    module.time = Clock()
    events = []
    try:
        messages = server.wait_turn_completed(timeout, events)
    finally:
        module.json = real_json
        module.time = real_time
    return messages, events, counter["count"]


def old_client_source():
    out = subprocess.run(["git", "-C", str(REPO_ROOT), "show",
                          f"{BASE_COMMIT}:{OLD_CLIENT_REL}"],
                         capture_output=True, text=True, check=True)
    return out.stdout


def parity_lines():
    def item(ident, kind, **extra):
        return {"method": "item/completed",
                "params": {"item": {"id": ident, "type": kind, **extra}}}
    rows = [
        item("u1", "userMessage", text="$mygamestudio:game-code 继续"),
        item("a1", "agentMessage", text="first agent reply"),
        item("c1", "commandExecution", command="echo hi"),
        item("a2", "agentMessage", text="second agent reply"),
        item("a1", "agentMessage", text="first agent reply"),
        item("a3", "agentMessage", text="second agent reply"),
        {"method": "turn/completed", "params": {"turn": {"id": "t"}}},
    ]
    return [json.dumps(x, ensure_ascii=False) if isinstance(x, dict) else x
            for x in rows]


def line_count(rel):
    path = REPO_ROOT / rel
    return len(path.read_text(encoding="utf-8").splitlines()) if path.is_file() else 0


def base_line_count(rel):
    out = subprocess.run(["git", "-C", str(REPO_ROOT), "show",
                          f"{BASE_COMMIT}:{rel}"],
                         capture_output=True, text=True, check=True)
    return len(out.stdout.splitlines())


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out")
    args = parser.parse_args()

    old = load_source(old_client_source(), "mgs13_old_client")
    new = load_file(REPO_ROOT / SHARED_REL, "mgs13_shared_core")

    lines = synthetic_lines(EVENT_COUNT)
    old_messages, old_events, old_decodes = replay(old, lines)
    new_messages, new_events, new_decodes = replay(new, lines)

    parity = parity_lines()
    old_pm, old_pe, _ = replay_single(old, parity)
    new_pm, new_pe, _ = replay_single(new, parity)

    report = {
        "ticket": "13-shared-client-expand",
        "base_commit": BASE_COMMIT,
        "method": ("复用票 01 client_probe 的合成回放方法:1000 条固定事件、"
                   "10 次轮询,计数器替换 json.loads;不启动子进程/网络/模型"),
        "decode_count": {
            "old_implementation_json_loads": old_decodes,
            "shared_implementation_json_loads": new_decodes,
            "baseline_ticket01_json_loads": 21000,
            "input_lines": EVENT_COUNT,
            "poll_iterations": POLLS,
            "recorded_events_new": len(new_events),
            "decoded_messages_new": len(new_messages),
            "note": ("旧实现每次轮询重复解码全部行;共享实现按行缓存只解码一次。"
                     "该计数只说明解码操作量,不代表模型或网络端到端倍数"),
        },
        "ab_parity": {
            "agent_messages_equal": old_pm == new_pm,
            "events_equal": old_pe == new_pe,
            "old_agent_messages": old_pm,
            "new_agent_messages": new_pm,
            "event_count": len(new_pe),
        },
        "line_counts": {
            "shared_core": line_count(SHARED_REL),
            "migrated_clients": {rel: line_count(rel) for rel in MIGRATED},
            "old_clients_at_base": {rel: base_line_count(rel) for rel in MIGRATED},
        },
        "evidence_kind": "synthetic_replay",
        "subprocesses_started": 0,
        "network_requests": 0,
        "model_calls": 0,
    }
    text = json.dumps(report, ensure_ascii=False, indent=2) + "\n"
    if args.out:
        Path(args.out).write_text(text, encoding="utf-8")
    else:
        print(text)
    return 0


def replay_single(module, lines, timeout=10.0):
    server = object.__new__(module.AppServer)
    server.lines = list(lines)
    server._lock = threading.Lock()
    server._drained = 0
    counter = {"count": 0}
    real_json, real_time = module.json, module.time
    module.json = CountingJson(real_json, counter)
    module.time = Clock()
    events = []
    try:
        messages = server.wait_turn_completed(timeout, events)
    finally:
        module.json = real_json
        module.time = real_time
    return messages, events, counter["count"]


if __name__ == "__main__":
    sys.exit(main())

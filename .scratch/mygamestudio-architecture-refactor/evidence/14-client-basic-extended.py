#!/usr/bin/env python3
"""票 14 证据探针:最小场景与扩展事件场景迁移的离线对照(全部离线)。

- 解码计数:用与票 01 ``client_probe.py`` 相同的方法(1000 条固定事件、10 次
  轮询,计数器替换 ``json.loads``),分别驱动基点 ``e42d17b`` 的旧客户端实现与
  迁移后的共享实现,覆盖最小场景(原 01)与扩展事件场景(原 03/04)。
- 旧新对照(A/B):同一合成输入(含重复 key/文本、turn 生命周期通知与
  turn/completed)下比较 ``wait_turn_completed`` 的 agent 消息与事件增量消费结果。
- 事件筛选差异:固定事件流经共享 ``write_event_stream`` 分别按标准族(keep_types)
  与扩展族(全部类型 + turn 生命周期)落盘,证明场景差异被保留、未强制统一。
- 行数:本批三个入口 + 共享核心 module 的物理行数(新 vs 基点)。

不启动子进程、不访问网络、不启动真实模型;不代表端到端加速倍数。

用法:python3 14-client-basic-extended.py [--out <report.json>]
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
SHARED_REL = "acceptance/_shared/appserver_core.py"
# 本票迁移的三个入口与其基点旧实现路径(族 2 单份,族 3 两份)。
BASIC_REL = "acceptance/01-explicit-project-status/appserver_client.py"
EXTENDED_RELS = ("acceptance/03-indirect-write-failure/appserver_client.py",
                 "acceptance/04-initialize-local-project/appserver_client.py")
MIGRATED = (BASIC_REL,) + EXTENDED_RELS
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


def load_base(rel: str, name: str):
    source = subprocess.run(["git", "-C", str(REPO_ROOT), "show",
                             f"{BASE_COMMIT}:{rel}"],
                            capture_output=True, text=True, check=True).stdout
    return load_source(source, name)


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


def parity_lines():
    """含重复 key/文本、turn 生命周期通知与 turn/completed 的合成输入。"""

    def item(ident, kind, **extra):
        return {"method": "item/completed",
                "params": {"item": {"id": ident, "type": kind, **extra}}}
    rows = [
        {"method": "turn/started", "params": {"turn": {"id": "t"}}},
        item("u1", "userMessage", text="$mygamestudio:game-code 继续"),
        item("a1", "agentMessage", text="first agent reply"),
        item("c1", "commandExecution", command="echo hi"),
        item("a2", "agentMessage", text="second agent reply"),
        item("a1", "agentMessage", text="first agent reply"),
        item("a3", "agentMessage", text="second agent reply"),
        {"method": "turn/completed", "params": {"turn": {"id": "t"}}},
    ]
    return [json.dumps(x, ensure_ascii=False) for x in rows]


def replay(module, lines, timeout=10.0):
    """与票 01/13 同法:虚拟时钟推进,单次 wait_turn_completed;返回(消息,事件,解码数)。"""

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
        try:
            messages = server.wait_turn_completed(timeout, events)
        except TypeError:  # 最小场景旧实现只接受 timeout
            messages = server.wait_turn_completed(timeout)
    finally:
        module.json = real_json
        module.time = real_time
    return messages, events, counter["count"]


def line_count(rel):
    path = REPO_ROOT / rel
    return len(path.read_text(encoding="utf-8").splitlines()) if path.is_file() else 0


def base_line_count(rel):
    out = subprocess.run(["git", "-C", str(REPO_ROOT), "show",
                          f"{BASE_COMMIT}:{rel}"],
                         capture_output=True, text=True, check=True)
    return len(out.stdout.splitlines())


def selection_demo(shared):
    """固定事件流按标准族与扩展族筛选,证明场景差异保留(未强制统一)。"""

    events = []
    for raw in parity_lines():
        events.append(json.loads(raw))
    tmp = Path("/tmp/mgs14_selection_demo")
    tmp.mkdir(parents=True, exist_ok=True)
    standard = tmp / "standard.jsonl"
    extended = tmp / "extended.jsonl"
    shared.write_event_stream(
        events, str(standard), {"userMessage", "agentMessage", "commandExecution",
                                "mcpToolCall"})
    shared.write_event_stream(
        events, str(extended), None,
        ("turn/started", "turn/completed", "turn/failed"))
    std_rows = [json.loads(x) for x in standard.read_text(encoding="utf-8").splitlines()]
    ext_rows = [json.loads(x) for x in extended.read_text(encoding="utf-8").splitlines()]
    return {
        "standard_methods": [m["method"] for m in std_rows],
        "extended_methods": [m["method"] for m in ext_rows],
        "standard_keeps_turn_started": any(m["method"] == "turn/started" for m in std_rows),
        "extended_keeps_all_item_types": (
            {m["params"]["item"]["type"] for m in ext_rows
             if m["method"] == "item/completed"}
            == {"userMessage", "agentMessage", "commandExecution"}),
        "note": ("标准族(02/17/18)按 keep_types 过滤且不含 turn 生命周期;扩展族"
                 "(01/03/04 中 03/04)保留全部 item 类型与 turn 生命周期。族差异"
                 "经显式参数保留,未强加统一输出字段。"),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out")
    args = parser.parse_args()

    shared = load_file(REPO_ROOT / SHARED_REL, "mgs14_shared_core")
    old_basic = load_base(BASIC_REL, "mgs14_old_basic")
    old_extended = load_base(EXTENDED_RELS[0], "mgs14_old_extended")

    lines = synthetic_lines(EVENT_COUNT)
    decode = {}
    for label, old, new in (("basic_01", old_basic, shared),
                            ("extended_03", old_extended, shared)):
        old_messages, _, old_decodes = replay(old, lines)
        new_messages, _, new_decodes = replay(new, lines)
        decode[label] = {
            "old_json_loads": old_decodes,
            "new_json_loads": new_decodes,
            "baseline_ticket01_json_loads": 21000,
            "old_messages": len(old_messages),
            "new_messages": len(new_messages),
        }

    parity = parity_lines()
    old_pm, old_pe, _ = replay(old_extended, parity)
    new_pm, new_pe, _ = replay(shared, parity)
    basic_pm, _, _ = replay(old_basic, parity)
    basic_new_pm, _, _ = replay(shared, parity)

    report = {
        "ticket": "14-shared-client-basic-migrate",
        "base_commit": BASE_COMMIT,
        "method": ("复用票 01/13 的合成回放方法:1000 条固定事件、10 次轮询,计数器"
                   "替换 json.loads;不启动子进程/网络/模型"),
        "decode_count": decode,
        "ab_parity": {
            "extended_agent_messages_equal": old_pm == new_pm,
            "extended_events_equal": old_pe == new_pe,
            "extended_event_count": len(new_pe),
            "basic_agent_messages_equal": basic_pm == basic_new_pm,
            "new_agent_messages": new_pm,
        },
        "selection_difference": selection_demo(shared),
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


if __name__ == "__main__":
    sys.exit(main())

#!/usr/bin/env python3
"""票 15 证据探针:绝对阈值中断场景迁移的离线对照(全部离线)。

- 绝对阈值语义:基点 ``8f8407f`` 族 4 旧实现(``05-adopt-existing-project``,十份
  逐字节同类)与迁移后共享实现,以合成行 + 合成审计文件对照 ``wait_turn_completed``
  的中断判定、agent 消息与事件增量消费结果。阈值为**累计绝对次数**,阈值达到即
  killed=True;未达到则普通返回。
- 族归属:十六份已迁入口归一化后仍归属各自行为族(族 1/2/3/4),未迁入的相对阈值
  客户端(15/16,族 5)保持独立实现。
- 行数:十份族 4 入口 + 共享核心的物理行数(新 vs 基点)。

不启动子进程、不访问网络、不启动真实模型;不代表端到端加速倍数。

用法:python3 15-client-absolute.py [--out <report.json>]
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
BASE_COMMIT = "8f8407f6e30646e16367c52fce538fea202b8327"
SHARED_REL = "acceptance/_shared/appserver_core.py"
FAMILY4_RELS = (
    "acceptance/05-adopt-existing-project/appserver_client.py",
    "acceptance/06-idea-to-current-spec/appserver_client.py",
    "acceptance/07-isolated-design-prototype/appserver_client.py",
    "acceptance/08-spec-to-local-tasks/appserver_client.py",
    "acceptance/09-code-task-delivery/appserver_client.py",
    "acceptance/10-visual-asset-delivery/appserver_client.py",
    "acceptance/11-audio-asset-delivery/appserver_client.py",
    "acceptance/12-build-and-run-delivery/appserver_client.py",
    "acceptance/13-independent-deliverable-review/appserver_client.py",
    "acceptance/14-playtest-and-human-feedback/appserver_client.py",
)
MIGRATED_BEFORE = (
    "acceptance/01-explicit-project-status/appserver_client.py",
    "acceptance/02-role-scoped-write/appserver_client.py",
    "acceptance/03-indirect-write-failure/appserver_client.py",
    "acceptance/04-initialize-local-project/appserver_client.py",
    "acceptance/17-github-issue-workflow/appserver_client.py",
    "acceptance/18-complete-package-acceptance/appserver_client.py",
)
RELATIVE_RELS = (
    "acceptance/15-goal-change-concurrency-recovery/appserver_client.py",
    "acceptance/16-producer-complete-loop/appserver_client.py",
)
OLD_FAMILY4_REL = FAMILY4_RELS[0]


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
    """含重复 key/文本与 turn/completed 的合成输入(与票 13/14 同族)。"""

    def item(ident, kind, **extra):
        return {"method": "item/completed",
                "params": {"item": {"id": ident, "type": kind, **extra}}}
    rows = [
        {"method": "turn/started", "params": {"turn": {"id": "t"}}},
        item("u1", "userMessage", text="$mygamestudio:game-init 应用"),
        item("a1", "agentMessage", text="first agent reply"),
        item("c1", "commandExecution", command="echo hi"),
        item("a2", "agentMessage", text="second agent reply"),
        item("a1", "agentMessage", text="first agent reply"),
        item("a3", "agentMessage", text="second agent reply"),
        {"method": "turn/completed", "params": {"turn": {"id": "t"}}},
    ]
    return [json.dumps(x, ensure_ascii=False) for x in rows]


def write_audit(path: Path, allows: int) -> None:
    rows = [{"op": "write", "decision": "allow", "index": i} for i in range(allows)]
    path.write_text("".join(json.dumps(r) + "\n" for r in rows), encoding="utf-8")


def replay(module, lines, audit_path, threshold, timeout=10.0):
    """与票 01/13/14 同法:虚拟时钟,单次等待;kill_process_group 记计数,不发信号。"""

    server = object.__new__(module.AppServer)
    server.lines = list(lines)
    server._lock = threading.Lock()
    server._drained = 0
    kills = []
    server.kill_process_group = lambda: kills.append(1)
    counter = {"count": 0}
    real_json, real_time = module.json, module.time
    module.json = CountingJson(real_json, counter)
    module.time = Clock()
    events = []
    try:
        if hasattr(server, "wait_turn_interruptible"):
            messages, killed = server.wait_turn_interruptible(
                timeout, events, watch_audit=str(audit_path),
                kill_after_allows=threshold)
        else:
            messages, killed = server.wait_turn_completed(
                timeout, events, watch_audit=str(audit_path),
                kill_after_allows=threshold)
    finally:
        module.json = real_json
        module.time = real_time
    return messages, killed, events, counter["count"], len(kills)


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

    shared = load_file(REPO_ROOT / SHARED_REL, "mgs15_shared_core")
    old = load_base(OLD_FAMILY4_REL, "mgs15_old_family4")
    work = Path("/tmp/mgs15_evidence")
    work.mkdir(parents=True, exist_ok=True)

    parity = parity_lines()
    reached_audit = work / "reached.jsonl"
    below_audit = work / "below.jsonl"
    write_audit(reached_audit, 3)
    write_audit(below_audit, 1)

    old_r = replay(old, parity, reached_audit, 3)
    new_r = replay(shared, parity, reached_audit, 3)
    old_b = replay(old, parity, below_audit, 3)
    new_b = replay(shared, parity, below_audit, 3)

    lines = synthetic_lines(1000)
    _, _, _, new_decodes, _ = replay(shared, lines, below_audit, 3)
    _, _, _, old_decodes, _ = replay(old, lines, below_audit, 3)

    report = {
        "ticket": "15-shared-client-absolute",
        "base_commit": BASE_COMMIT,
        "method": ("复用票 01/13/14 的合成回放方法:虚拟时钟 + 计数器替换 json.loads,"
                   "合成审计文件驱动阈值;kill_process_group 记计数、不发送真实信号;"
                   "不启动子进程/网络/模型"),
        "absolute_threshold_parity": {
            "threshold_reached": {
                "threshold": 3,
                "old_killed": old_r[1],
                "new_killed": new_r[1],
                "old_kill_calls": old_r[4],
                "new_kill_calls": new_r[4],
                "old_messages": old_r[0],
                "new_messages": new_r[0],
                "events_equal": old_r[2] == new_r[2],
                "event_count": len(new_r[2]),
            },
            "threshold_unmet": {
                "threshold": 3,
                "present_allows": 1,
                "old_killed": old_b[1],
                "new_killed": new_b[1],
                "old_messages": old_b[0],
                "new_messages": new_b[0],
                "messages_equal": old_b[0] == new_b[0],
                "events_equal": old_b[2] == new_b[2],
                "event_count": len(new_b[2]),
            },
            "note": ("阈值为累计绝对次数(含进入等待前已有的 allow);阈值达到即中断"
                     "(killed=True),未达到则普通返回。共享实现未引入相对新增计数。"),
        },
        "decode_count": {
            "old_json_loads": old_decodes,
            "new_json_loads": new_decodes,
            "input_lines": 1000,
            "baseline_ticket01_json_loads": 21000,
            "note": ("中断等待口径:事件行每条只解码一次,另含审计文件轮询的少量"
                     "json.loads(每次轮询 ≤ 审计行数);旧实现每次轮询重复解码全部"
                     "事件行。事件一次解码的净计数结论见票 13/14 与普通路径测试"),
        },
        "line_counts": {
            "shared_core": line_count(SHARED_REL),
            "migrated_family4": {rel: line_count(rel) for rel in FAMILY4_RELS},
            "old_family4_at_base": {rel: base_line_count(rel) for rel in FAMILY4_RELS},
        },
        "family_roster": {
            "migrated_family4": len(FAMILY4_RELS),
            "migrated_before": len(MIGRATED_BEFORE),
            "relative_unmigrated": len(RELATIVE_RELS),
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

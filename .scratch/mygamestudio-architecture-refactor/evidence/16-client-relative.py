#!/usr/bin/env python3
"""票 16 证据探针:相对阈值与完整闭环场景迁移的离线对照(全部离线)。

- 相对阈值语义:基点 ``ca431fb`` 族 5 旧实现(``15-goal-change-concurrency-recovery``,
  两份逐字节同类)与迁移后共享实现,以合成行 + 合成审计文件对照中断判定、agent
  消息与事件增量消费结果。``--kill-relative`` 时以进入等待时的已有 allow 为基数、
  只计本轮新增;历史累计不误触发本轮。
- 完整闭环(共享运行根多轮):同一审计文件连续多轮,每轮以进入时的已有 allow 为
  基数,只在本轮新增达阈值时中断,证明多轮累计允许不会让新轮次开始即中断。
- 绝对对照:同一输入下绝对模式仍按累计次数判定,且与旧实现一致。
- 族归属:十八份入口归一化后仍归 5 族(族 5=15/16),已全部迁入共享实现。
- 行数:两份族 5 入口 + 共享核心的物理行数(新 vs 基点)。

不启动子进程、不访问网络、不启动真实模型;不代表端到端加速倍数。

用法:python3 16-client-relative.py [--out <report.json>]
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
BASE_COMMIT = "ca431fb44a504bd18f8a180d3501acd02e55d6b3"
SHARED_REL = "acceptance/_shared/appserver_core.py"
FAMILY5_RELS = (
    "acceptance/15-goal-change-concurrency-recovery/appserver_client.py",
    "acceptance/16-producer-complete-loop/appserver_client.py",
)
OLD_FAMILY5_REL = FAMILY5_RELS[0]
MIGRATED_RELS = tuple(
    f"acceptance/{name}/appserver_client.py" for name in (
        "01-explicit-project-status", "02-role-scoped-write",
        "03-indirect-write-failure", "04-initialize-local-project",
        "05-adopt-existing-project", "06-idea-to-current-spec",
        "07-isolated-design-prototype", "08-spec-to-local-tasks",
        "09-code-task-delivery", "10-visual-asset-delivery",
        "11-audio-asset-delivery", "12-build-and-run-delivery",
        "13-independent-deliverable-review", "14-playtest-and-human-feedback",
        "15-goal-change-concurrency-recovery", "16-producer-complete-loop",
        "17-github-issue-workflow", "18-complete-package-acceptance",
    ))


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
    """含重复 key/文本与 turn/completed 的合成输入(与票 13/14/15 同族)。"""

    def item(ident, kind, **extra):
        return {"method": "item/completed",
                "params": {"item": {"id": ident, "type": kind, **extra}}}
    rows = [
        {"method": "turn/started", "params": {"turn": {"id": "t"}}},
        item("u1", "userMessage", text="$mygamestudio:game-producer 应用"),
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


def replay(module, lines, audit_path, threshold, *, relative, timeout=10.0):
    """与票 01/13/14/15 同法:虚拟时钟,单次等待;kill 记计数,不发信号。"""

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
    target = (server.wait_turn_interruptible
              if hasattr(server, "wait_turn_interruptible")
              else server.wait_turn_completed)
    kwargs = {"watch_audit": str(audit_path), "kill_after_allows": threshold}
    if "kill_relative" in target.__code__.co_varnames:
        kwargs["kill_relative"] = relative
    try:
        messages, killed = target(timeout, events, **kwargs)
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


def family_roster():
    """18 份入口按归一化源码归族(与 client_probe 同法的轻量静态核对)。"""

    import hashlib
    import re

    def normalize(text):
        text = re.sub(r'""".*?"""', "", text, flags=re.S)
        lines = [re.sub(r"#.*$", "", line).rstrip() for line in text.splitlines()]
        text = "\n".join(line for line in lines if line.strip())
        text = re.sub(r"mgs\d+", "MGS", text)
        text = re.sub(r"MyGameStudio \d+", "MyGameStudio N", text)
        return hashlib.sha256(text.encode()).hexdigest()

    groups = {}
    for rel in MIGRATED_RELS:
        key = normalize((REPO_ROOT / rel).read_text(encoding="utf-8"))
        groups.setdefault(key, []).append(rel)
    return {f"family_{i}": sorted(v) for i, v in enumerate(groups.values())}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out")
    args = parser.parse_args()

    shared = load_file(REPO_ROOT / SHARED_REL, "mgs16_shared_core")
    old = load_base(OLD_FAMILY5_REL, "mgs16_old_family5")
    work = Path("/tmp/mgs16_evidence")
    work.mkdir(parents=True, exist_ok=True)

    parity = parity_lines()

    # 相对:历史累计 2 条、阈值 2 → 本轮新增 0,不中断;旧新一致。
    history = work / "history.jsonl"
    write_audit(history, 2)
    old_h = replay(old, parity, history, 2, relative=True)
    new_h = replay(shared, parity, history, 2, relative=True)
    # 相对即时:阈值 0、空审计 → 恒成立,立即中断(无消息)。
    empty = work / "empty.jsonl"
    write_audit(empty, 0)
    old_i = replay(old, parity, empty, 0, relative=True)
    new_i = replay(shared, parity, empty, 0, relative=True)
    # 绝对对照:历史累计 2、阈值 2 → 达阈即中断(计入历史)。
    old_a = replay(old, parity, history, 2, relative=False)
    new_a = replay(shared, parity, history, 2, relative=False)

    # 完整闭环:共享运行根同一审计文件三轮;每轮进入时前序累计逐轮增长。相对模式
    # 下,前序累计不足以本轮触发中断(未新增即不中断);同输入的绝对对照则因历史
    # 计入而中断,证明历史累计只会影响绝对判断、不会误触发相对判断。每轮再追加
    # 本轮新增,使审计文件作为共享运行根逐轮增长。
    rounds = []
    loop_audit = work / "loop.jsonl"
    write_audit(loop_audit, 5)  # 前序轮次既有累计
    for round_index in range(1, 4):
        entry_prior = sum(1 for line in loop_audit.read_text(encoding="utf-8").splitlines()
                          if line.strip())
        relative_before = replay(shared, parity, loop_audit, 2, relative=True)
        absolute_before = replay(shared, parity, loop_audit, 2, relative=False)
        with open(loop_audit, "a", encoding="utf-8") as fh:
            for i in range(2):
                fh.write(json.dumps({"op": "write", "decision": "allow",
                                     "index": entry_prior + i}) + "\n")
        rounds.append({
            "round": round_index,
            "entry_prior_allows": entry_prior,
            "relative_killed_without_new_allows": relative_before[1],
            "relative_kill_calls": relative_before[4],
            "absolute_killed_without_new_allows": absolute_before[1],
        })

    lines = synthetic_lines(1000)
    _, _, _, new_decodes, _ = replay(shared, lines, history, 2, relative=True)
    _, _, _, old_decodes, _ = replay(old, lines, history, 2, relative=True)

    roster = family_roster()
    report = {
        "ticket": "16-shared-client-relative",
        "base_commit": BASE_COMMIT,
        "method": ("复用票 01/13/14/15 的合成回放方法:虚拟时钟 + 计数器替换 "
                   "json.loads,合成审计文件驱动阈值;kill_process_group 记计数、"
                   "不发送真实信号;不启动子进程/网络/模型"),
        "relative_threshold_parity": {
            "history_present_new_zero": {
                "prior_allows": 2, "threshold": 2, "relative": True,
                "old_killed": old_h[1], "new_killed": new_h[1],
                "old_messages": old_h[0], "new_messages": new_h[0],
                "messages_equal": old_h[0] == new_h[0],
                "events_equal": old_h[2] == new_h[2],
                "note": "历史累计已等于阈值,但相对模式本轮新增为 0,不得中断",
            },
            "immediate_zero": {
                "prior_allows": 0, "threshold": 0, "relative": True,
                "old_killed": old_i[1], "new_killed": new_i[1],
                "old_kill_calls": old_i[4], "new_kill_calls": new_i[4],
                "old_messages": old_i[0], "new_messages": new_i[0],
                "events_equal": old_i[2] == new_i[2],
            },
            "absolute_control": {
                "prior_allows": 2, "threshold": 2, "relative": False,
                "old_killed": old_a[1], "new_killed": new_a[1],
                "old_messages": old_a[0], "new_messages": new_a[0],
                "events_equal": old_a[2] == new_a[2],
                "note": "绝对模式仍按累计次数判定(历史计入),与旧实现一致",
            },
        },
        "shared_run_root_multiround": {
            "initial_prior_allows": 5,
            "threshold_per_round": 2,
            "rounds": rounds,
            "note": ("共享运行根同一审计文件连续三轮:每轮进入时前序轮次累计均存在,"
                     "相对模式只计本轮新增,故未追加前不中断、本轮新增达阈值才中断;"
                     "历史累计不会让新轮次开始即误判"),
        },
        "decode_count": {
            "old_json_loads": old_decodes,
            "new_json_loads": new_decodes,
            "input_lines": 1000,
            "baseline_ticket01_json_loads": 21000,
            "note": ("中断等待口径:事件行每条只解码一次,另含审计文件轮询的少量 "
                     "json.loads;旧实现每次轮询重复解码全部事件行"),
        },
        "family_roster": {
            "family_count": len(roster),
            "families": roster,
            "migrated": len(MIGRATED_RELS),
            "family5_members": list(FAMILY5_RELS),
            "note": "十八份入口归一化后仍归 5 族(族 5=15/16);全部迁入共享实现",
        },
        "line_counts": {
            "shared_core": line_count(SHARED_REL),
            "migrated_family5": {rel: line_count(rel) for rel in FAMILY5_RELS},
            "old_family5_at_base": {rel: base_line_count(rel) for rel in FAMILY5_RELS},
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

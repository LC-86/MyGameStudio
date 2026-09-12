#!/usr/bin/env python3
"""票 01 基线探针 C:验收客户端五族差异与解码计数(合成回放)。

- 盘点 18 份 acceptance/*/appserver_client.py 的行数、SHA-256,并把「忽略
  注释/文档串、仅规范化 mgsNN-acceptance 与 MyGameStudio NN acceptance 常量」
  后的内容归入行为族;预期得到 5 族(与前置调查一致)。
- 合成回放 1,000 条固定事件、10 次轮询,用计数器替换 time 与 json.loads,
  记录 JSON 解码次数。只调用现有 wait_turn_completed 代码,不启动子进程、
  不访问网络、不启动真实模型。

用法:python3 client_probe.py [--out <report.json>]
"""

import hashlib
import importlib.util
import inspect
import json
import sys
import threading
from pathlib import Path

from baseline_common import REPO_ROOT, emit, normalize_source, parse_out_args

ACCEPTANCE = REPO_ROOT / "acceptance"
EVENT_COUNT = 1000
POLLS = 10


def load_client(path: Path):
    spec = importlib.util.spec_from_file_location(f"baseline_client_{path.parent.name}", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def structural_flags(source: str) -> dict:
    return {
        "has_incremental_drain": "def drain_events" in source and "_drained" in source,
        "has_kill_process_group": "def kill_process_group" in source,
        "has_kill_after_allows": "kill_after_allows" in source,
        "has_kill_relative": "kill_relative" in source,
        "event_type_filter": "keep_types" in source,
        "json_loads_sites": source.count("json.loads("),
    }


class FakeClock:
    def __init__(self) -> None:
        self.now = 0.0

    def time(self) -> float:
        return self.now

    def sleep(self, seconds: float) -> None:
        self.now += seconds


def decode_probe(path: Path) -> dict:
    """1,000 条固定事件经 10 次轮询的 JSON 解码计数(合成回放)。"""

    module = load_client(path)
    loads = {"count": 0}
    real_loads = json.loads

    def counting_loads(*args, **kwargs):
        loads["count"] += 1
        return real_loads(*args, **kwargs)

    module.json.loads = counting_loads
    clock = FakeClock()
    module.time.time = clock.time
    module.time.sleep = clock.sleep

    server = object.__new__(module.AppServer)
    server.lines = [
        json.dumps({"method": "item/completed",
                    "params": {"item": {"id": i, "type": "agentMessage",
                                        "text": f"message-{i}"}}})
        for i in range(EVENT_COUNT)
    ]
    server._lock = threading.Lock()
    server._drained = 0
    events: list[dict] = []
    params = inspect.signature(module.AppServer.wait_turn_completed).parameters
    if "events" in params:
        result = server.wait_turn_completed(10.0, events=events)
    else:
        result = server.wait_turn_completed(10.0)
    messages = result[0] if isinstance(result, tuple) else result
    return {
        "evidence_kind": "synthetic_replay",
        "representative": str(path.relative_to(REPO_ROOT)),
        "input_lines": EVENT_COUNT,
        "poll_iterations": POLLS,
        "json_loads_calls": loads["count"],
        "recorded_events": len(events),
        "decoded_messages": len(messages),
        "real_sleep_seconds": 0,
        "subprocesses_started": 0,
        "network_requests": 0,
        "model_calls": 0,
    }


def main() -> int:
    args = parse_out_args(__doc__)

    clients = sorted(ACCEPTANCE.glob("*/appserver_client.py"))
    members = []
    family_of: dict[str, list[str]] = {}
    for path in clients:
        source = path.read_text(encoding="utf-8")
        family = normalize_source(source)
        members.append({
            "path": str(path.relative_to(REPO_ROOT)),
            "lines": len(source.splitlines()),
            "sha256": hashlib.sha256(source.encode("utf-8")).hexdigest(),
            "family_key": family,
            **structural_flags(source),
        })
        family_of.setdefault(family, []).append(str(path.relative_to(REPO_ROOT)))
    families = [
        {"members": sorted(paths), "count": len(paths), "family_key": key}
        for key, paths in sorted(family_of.items())
    ]

    decode = decode_probe(ACCEPTANCE / "02-role-scoped-write" / "appserver_client.py")
    report = {
        "evidence_kind": "static_fact + synthetic_replay",
        "client_count": len(members),
        "total_client_lines": sum(m["lines"] for m in members),
        "family_count": len(families),
        "families": families,
        "members": members,
        "decode_probe": decode,
        "scope": ("合成回放只覆盖现有 wait_turn_completed 代码;不启动子进程、"
                  "不访问网络、不启动真实模型;不代表端到端加速倍数"),
    }
    emit(report, args.out)
    return 0


if __name__ == "__main__":
    sys.exit(main())

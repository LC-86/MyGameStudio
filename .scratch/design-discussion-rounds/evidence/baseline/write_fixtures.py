#!/usr/bin/env python3
"""写出可控事件样例(只核口径,不得冒充真实模型耗时)。"""

import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
OUT = HERE / "fixtures"
OUT.mkdir(parents=True, exist_ok=True)


def dump(name: str, rows: list) -> None:
    path = OUT / name
    path.write_text("".join(json.dumps(row, ensure_ascii=False) + "\n" for row in rows),
                    encoding="utf-8")


def item(kind, at, **extra):
    extra.setdefault("type", kind)
    return {"method": "item/completed", "emittedAtMs": at,
            "params": {"item": extra, "completedAtMs": at}}


def user(at, text="回答"):
    return item("userMessage", at, content=[{"type": "text", "text": text}])


def agent(at, text, phase):
    return item("agentMessage", at, text=text, phase=phase)


def turn_done(at):
    return {"method": "turn/completed", "emittedAtMs": at,
            "params": {"turn": {"status": "completed"}}}


def write_ev(at, path, allow=True):
    result = {"op": "write", "decision": "allow" if allow else "deny",
              "target": path, "bytes": 20}
    return item("mcpToolCall", at, tool="mgs_write", status="completed",
                arguments={"path": path, "content": "x"},
                result={"content": [{"type": "text", "text": json.dumps(result)}]})


def read_ev(at, path, output="ok"):
    return item("commandExecution", at, command=f"nl -ba {path}", status="completed",
                commandActions=[{"type": "read", "path": path, "name": "f"}],
                aggregatedOutput=output)


dump("missing-endpoint.jsonl", [
    user(1000, "Q1 选 A"),
    write_ev(1800, "docs/mygamestudio/records/decision-x.md"),
])
dump("retry-then-reread.jsonl", [
    user(1000),
    write_ev(1500, "docs/mygamestudio/records/decision-x.md", allow=False),
    write_ev(2200, "docs/mygamestudio/records/decision-x.md", allow=True),
    read_ev(2600, "/p/docs/mygamestudio/records/decision-x.md", "回读成功"),
    agent(3000, "已保存", "final_answer"),
    turn_done(3050),
])
dump("progress-prompt-not-done.jsonl", [
    user(1000, "Q1 选 A"),
    agent(1300, "先核对", "commentary"),
    agent(5000, "❓ Q4", "final_answer"),
    turn_done(5100),
])
(OUT / "README.md").write_text(
    "可控事件样例,只供 `measure_module_run` 核对用户等待、失败重试与缺失终点。\n"
    "不得写入效率对比表冒充真实模型耗时。\n",
    encoding="utf-8",
)
print(f"wrote fixtures in {OUT}")

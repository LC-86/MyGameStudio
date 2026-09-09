#!/usr/bin/env python3
"""任务票 18:mgs-gate MCP stdio 驱动探针。

驱动**实际安装副本**的 runtime/mcp_gate.py 进程(与 Codex 会话启动的同一
服务器、同一协议),用于不接受模型措辞影响的失效闭合/并发/回收探针:
策略损坏失效闭合、占用冲突、凭据失效、远端上游失联等。这是对真实运行
组件的集成驱动,不是进程内桩;会话级(模型发起)的证据由 appserver_client
的真实模型 turn 承担,两者互补。

用法:
  gate_probe.py --gate <安装副本>/runtime/mcp_gate.py call <工具名> '<参数JSON>'
"""

import argparse
import json
import subprocess
import sys
import os
import time


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--gate", required=True, help="mcp_gate.py 路径(安装副本)")
    sub = parser.add_subparsers(dest="cmd", required=True)
    p_call = sub.add_parser("call", help="调用一个工具并打印结果 JSON")
    p_call.add_argument("tool")
    p_call.add_argument("args_json")
    args = parser.parse_args()

    proc = subprocess.Popen(
        [sys.executable, "-B", args.gate],
        stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
        env=os.environ.copy(),
    )

    def send(payload: dict) -> None:
        proc.stdin.write((json.dumps(payload) + "\n").encode())
        proc.stdin.flush()

    def recv(want_id, timeout=30.0):
        start = time.time()
        while time.time() - start < timeout:
            line = proc.stdout.readline()
            if not line:
                break
            text = line.decode("utf-8", "replace").strip()
            if not text:
                continue
            try:
                msg = json.loads(text)
            except json.JSONDecodeError:
                continue
            if msg.get("id") == want_id and "method" not in msg:
                return msg
        return None

    send({"jsonrpc": "2.0", "id": 1, "method": "initialize",
          "params": {"protocolVersion": "2025-06-18"}})
    init = recv(1)
    if init is None or "error" in init:
        print(json.dumps({"probe": "initialize", "error": str(init)}))
        proc.kill()
        return 2
    send({"jsonrpc": "2.0", "method": "notifications/initialized"})
    send({"jsonrpc": "2.0", "id": 2, "method": "tools/call",
          "params": {"name": args.tool, "arguments": json.loads(args.args_json)}})
    result = recv(2)
    proc.stdin.close()
    proc.terminate()
    if result is None:
        print(json.dumps({"probe": args.tool, "error": "no response"}))
        return 2
    if "error" in result:
        print(json.dumps({"probe": args.tool, "error": result["error"]},
                         ensure_ascii=False))
        return 1
    content = result.get("result", {}).get("content", [])
    for item in content:
        if item.get("type") == "text":
            print(item.get("text", ""))
    return 0


if __name__ == "__main__":
    sys.exit(main())

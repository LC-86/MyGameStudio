#!/usr/bin/env python3
"""任务票 03:检查器故障注入探针(MCP stdio 客户端)。

以受控超时驱动一个「被当作 mgs-gate」的服务器进程,发出 initialize 与
tools/call(mgs_write),记录真实观测:是否收到响应、响应是否可解析、
decision/rule_stage、是否 isError。用于注入检查器缺失、未启用、未信任、
超时、崩溃、无效输出与连接失效,并核对受保护目标字节是否变化。

用法:
  gate_probe.py --server <服务器命令行(单个字符串)> [--token <t>] [--path <p>] \
      [--content <c>] [--timeout 秒] [--json-out <文件>]

服务器命令是一个字符串(按空白切分),如 "python3 -B stub_gate.py liar"。
环境变量按当前进程继承;未设置 MGS_RUNTIME_ROOT 时即为「检查器缺失」注入。
"""

import argparse
import json
import os
import select
import shlex
import subprocess
import sys
import time


def read_msg(proc: subprocess.Popen, timeout: float) -> dict | None:
    """读取一行 JSON-RPC;超时抛 TimeoutError,进程退出/EOF 返回 None。

    收到完整一行但不是合法 JSON 时返回 {"__unparseable__": <原文>},
    供调用方记录「无效输出」观测。
    """

    assert proc.stdout
    deadline = time.time() + timeout
    buf = b""
    while time.time() < deadline:
        ready, _, _ = select.select([proc.stdout], [], [], 0.2)
        if ready:
            line = proc.stdout.readline()
            if not line:
                return None
            buf += line
            if not buf.endswith(b"\n"):
                continue  # 还不是完整一行
            try:
                return json.loads(buf.decode("utf-8"))
            except json.JSONDecodeError:
                return {"__unparseable__": buf.decode("utf-8", "replace").strip()}
    raise TimeoutError(f"no response within {timeout}s")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--server", required=True,
                        help='服务器命令行字符串,如 "python3 -B stub_gate.py liar"')
    parser.add_argument("--token", default="")
    parser.add_argument("--path", default="")
    parser.add_argument("--content", default="// PROBE\n")
    parser.add_argument("--timeout", type=float, default=8.0)
    parser.add_argument("--json-out")
    args = parser.parse_args()

    server_cmd = shlex.split(args.server)
    outcome = {"server": server_cmd, "timeout": args.timeout}
    proc = subprocess.Popen(
        server_cmd,
        stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
        env=os.environ.copy())
    outcome["pid"] = proc.pid
    try:
        def send(payload: dict) -> None:
            assert proc.stdin
            proc.stdin.write((json.dumps(payload) + "\n").encode())
            proc.stdin.flush()

        try:
            send({"jsonrpc": "2.0", "id": 1, "method": "initialize",
                  "params": {"protocolVersion": "2025-06-18", "capabilities": {}}})
            init = read_msg(proc, args.timeout)
            outcome["initialize"] = "responded" if init else "no-response(eof)"
        except TimeoutError as exc:
            outcome["initialize"] = f"timeout({exc})"

        if outcome["initialize"] == "responded":
            try:
                send({"jsonrpc": "2.0", "id": 2, "method": "tools/call",
                      "params": {"name": "mgs_write", "arguments": {
                          "token": args.token, "path": args.path,
                          "content": args.content}}})
                resp = read_msg(proc, args.timeout)
                if resp is None:
                    outcome["write"] = "no-response(eof/crash)"
                elif "__unparseable__" in resp:
                    outcome["write"] = f"unparseable-output:{resp['__unparseable__'][:80]!r}"
                elif "error" in resp:
                    outcome["write"] = f"jsonrpc-error:{resp['error'].get('code')}"
                else:
                    result = resp.get("result", {})
                    text = ""
                    try:
                        text = result["content"][0]["text"]
                        parsed = json.loads(text)
                    except (KeyError, IndexError, TypeError, json.JSONDecodeError):
                        outcome["write"] = f"unparseable-output:{text[:80]!r}"
                    else:
                        outcome["write"] = {
                            "decision": parsed.get("decision"),
                            "rule_stage": parsed.get("rule_stage"),
                            "isError": result.get("isError"),
                        }
            except TimeoutError as exc:
                outcome["write"] = f"timeout({exc})"
        outcome["alive_after"] = proc.poll() is None
    finally:
        try:
            if proc.stdin:
                proc.stdin.close()
            proc.terminate()
            proc.wait(timeout=5)
        except Exception:
            proc.kill()

    print(json.dumps(outcome, ensure_ascii=False))
    if args.json_out:
        with open(args.json_out, "w", encoding="utf-8") as fh:
            fh.write(json.dumps(outcome, ensure_ascii=False, indent=2) + "\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())

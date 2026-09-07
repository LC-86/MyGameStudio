#!/usr/bin/env python3
"""MyGameStudio 受控写入通道:MCP stdio 服务器(任务票 02)。

这是业务 Skill 在 Codex 会话内提交写入意图的唯一入口。服务器进程由
Codex 按插件 .mcp.json 启动,运行在会话沙箱之外;真实拦截分两层:
- 会话沙箱:模型直接写项目文件会被操作系统拒绝(workspace-write 只放开
  会话工作目录与 /tmp);
- 本通道:写入必须携带可信调度层签发的执行凭据,并逐次通过
  「角色 ∩ 任务 ∩ 用途 ∩ 实际授权」检查,允许与拒绝都写审计日志。

运行根(MGS_RUNTIME_ROOT)由启动环境经 env_vars 传入,包内不含绝对路径。
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from mgs_runtime import GateService  # noqa: E402

TOOLS = [
    {
        "name": "mgs_scope",
        "description": (
            "查询当前执行凭据的有效可写范围与绑定身份(角色、任务、用途)。"
            "在提交任何写入前先调用本工具。"
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "token": {"type": "string", "description": "执行凭据(由受信任调度方在任务开头的说明中给出)"},
            },
            "required": ["token"],
        },
    },
    {
        "name": "mgs_write",
        "description": (
            "受控写入:把内容写入目标项目文件。目标路径可为项目根相对路径或绝对路径;"
            "写入前经过角色/任务/用途/占用与版本校验,被拒绝时目标保持不变并返回拒绝依据。"
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "token": {"type": "string", "description": "执行凭据"},
                "path": {"type": "string", "description": "目标文件(项目根相对或绝对路径)"},
                "content": {"type": "string", "description": "完整的新文件内容"},
                "expected_sha256": {
                    "type": "string",
                    "description": "预期当前文件内容的 SHA-256(十六进制);目标不存在时用 absent",
                },
                "note": {"type": "string", "description": "写入说明,仅进审计记录,不参与授权"},
            },
            "required": ["token", "path", "content"],
        },
    },
]


def make_service() -> GateService | None:
    root = os.environ.get("MGS_RUNTIME_ROOT", "").strip()
    if not root:
        return None
    return GateService(root)


def handle_tools_call(service: GateService | None, name: str, args: dict) -> dict:
    if service is None:
        return {
            "content": [{"type": "text", "text": json.dumps({
                "op": name, "decision": "deny", "rule_stage": "channel",
                "reason": "MGS_RUNTIME_ROOT is not configured for the mgs-gate server",
            }, ensure_ascii=False)}],
            "isError": True,
        }
    if name == "mgs_scope":
        result = service.scope(str(args.get("token", "")))
    elif name == "mgs_write":
        result = service.write(
            token=str(args.get("token", "")),
            path=str(args.get("path", "")),
            content=str(args.get("content", "")),
            expected_sha256=args.get("expected_sha256"),
            note=args.get("note"),
        )
    else:
        return {
            "content": [{"type": "text", "text": json.dumps(
                {"decision": "deny", "reason": f"unknown tool {name}"})}],
            "isError": True,
        }
    return {
        "content": [{"type": "text", "text": json.dumps(result, ensure_ascii=False)}],
        "isError": False,
    }


def respond(req_id, result: dict | None) -> None:
    if result is None:
        return
    payload = {"jsonrpc": "2.0", "id": req_id, "result": result}
    sys.stdout.write(json.dumps(payload) + "\n")
    sys.stdout.flush()


def main() -> int:
    service = make_service()
    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue
        try:
            req = json.loads(line)
        except json.JSONDecodeError:
            continue
        method = req.get("method")
        req_id = req.get("id")
        if method == "initialize":
            respond(req_id, {
                "protocolVersion": req.get("params", {}).get(
                    "protocolVersion", "2025-06-18"),
                "capabilities": {"tools": {}},
                "serverInfo": {"name": "mgs-gate", "version": "0.2.0"},
            })
        elif method == "notifications/initialized":
            respond(req_id, None)
        elif method == "ping":
            respond(req_id, {})
        elif method == "tools/list":
            respond(req_id, {"tools": TOOLS})
        elif method == "tools/call":
            params = req.get("params", {})
            respond(req_id, handle_tools_call(
                service, params.get("name", ""),
                params.get("arguments") or {}))
        elif req_id is not None:
            respond(req_id, {"error": {"code": -32601,
                                       "message": f"unknown method {method}"}})
    return 0


if __name__ == "__main__":
    sys.exit(main())

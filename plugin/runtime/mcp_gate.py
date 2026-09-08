#!/usr/bin/env python3
"""MyGameStudio 受控写入通道:MCP stdio 服务器(任务票 02 建立,任务票 03 加固,
任务票 11 扩展二进制资源载荷)。

这是业务 Skill 在 Codex 会话内提交写入意图的唯一入口。服务器进程由
Codex 按插件 .mcp.json 启动,运行在会话沙箱之外;真实拦截分两层:
- 会话沙箱:模型直接写项目文件会被操作系统拒绝(workspace-write 只放开
  会话工作目录与 /tmp);
- 本通道:写入必须携带可信调度层签发的执行凭据,并逐次通过
  「角色 ∩ 任务 ∩ 用途 ∩ 实际授权」检查,允许与拒绝都写审计日志。

任务票 03 的失效闭合要求:检查器(本通道与其后的运行保障服务)出现任何
故障都不放开写入——
- MGS_RUNTIME_ROOT 未配置:整体拒绝(rule_stage=channel,fail closed);
- 策略缺失/损坏:拒绝(rule_stage=policy),服务器继续应答;
- 单次调用抛出未预期异常:转为结构化拒绝返回,不让服务器崩溃断连。

任务票 11 的二进制资源载荷:文本走 `content`(UTF-8),音频等二进制资源走
`content_base64`(base64 编码的字节);两者恰提供其一,参数错误一律按
channel 失效闭合拒绝,不落盘。解码后的字节写入与文本走同一授权交集、
版本校验与审计,不因载荷形态放宽边界。

运行根(MGS_RUNTIME_ROOT)由启动环境经 env_vars 传入,包内不含绝对路径。
"""

from __future__ import annotations

import base64
import binascii
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
            "文本内容用 content(UTF-8);音频等二进制资源用 content_base64(base64 编码),"
            "两者恰提供其一。"
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "token": {"type": "string", "description": "执行凭据"},
                "path": {"type": "string", "description": "目标文件(项目根相对或绝对路径)"},
                "content": {"type": "string", "description": "完整的新文件内容(UTF-8 文本;与 content_base64 恰提供其一)"},
                "content_base64": {
                    "type": "string",
                    "description": "二进制资源的 base64 编码载荷(音频/图像等;与 content 恰提供其一)",
                },
                "expected_sha256": {
                    "type": "string",
                    "description": "预期当前文件内容的 SHA-256(按字节,十六进制);目标不存在时用 absent",
                },
                "note": {"type": "string", "description": "写入说明,仅进审计记录,不参与授权"},
            },
            "required": ["token", "path"],
        },
    },
]


def make_service() -> GateService | None:
    root = os.environ.get("MGS_RUNTIME_ROOT", "").strip()
    if not root:
        return None
    return GateService(root)


def handle_tools_call(service: GateService | None, name: str, args: dict) -> dict:
    try:
        return _handle_tools_call(service, name, args)
    except Exception as exc:  # noqa: BLE001 - 通道兜底必须失效闭合,不能断连放开
        return {
            "content": [{"type": "text", "text": json.dumps({
                "op": name, "decision": "deny", "rule_stage": "channel",
                "reason": f"gate internal error (fail closed): "
                          f"{type(exc).__name__}: {exc}",
            }, ensure_ascii=False)}],
            "isError": True,
        }


def _channel_deny(name: str, reason: str) -> dict:
    """通道层结构化拒绝(参数错误等),失效闭合:不调用服务、不落盘。"""

    return {
        "content": [{"type": "text", "text": json.dumps({
            "op": name, "decision": "deny", "rule_stage": "channel",
            "reason": reason,
        }, ensure_ascii=False)}],
        "isError": True,
    }


def _handle_tools_call(service: GateService | None, name: str, args: dict) -> dict:
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
        has_content = "content" in args
        has_base64 = "content_base64" in args
        if has_content == has_base64:  # 两者都给或都不给
            return _channel_deny(
                name, "payload error: exactly one of content / content_base64 "
                      "is required (fail closed, nothing written)")
        payload_kwargs: dict = {}
        if has_base64:
            try:
                # 容忍命令行 base64 工具的换行折行:先剥掉全部空白再严格解码
                compact = "".join(str(args["content_base64"]).split())
                payload_kwargs["data"] = base64.b64decode(compact, validate=True)
            except (binascii.Error, ValueError) as exc:
                return _channel_deny(
                    name, f"payload error: invalid content_base64 ({exc}); "
                          "fail closed, nothing written")
        else:
            payload_kwargs["content"] = str(args.get("content", ""))
        result = service.write(
            token=str(args.get("token", "")),
            path=str(args.get("path", "")),
            expected_sha256=args.get("expected_sha256"),
            note=args.get("note"),
            **payload_kwargs,
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
                "serverInfo": {"name": "mgs-gate", "version": "0.3.0"},
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

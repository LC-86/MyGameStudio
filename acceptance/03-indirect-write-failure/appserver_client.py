#!/usr/bin/env python3
"""最小 Codex app-server JSON-RPC(stdio)客户端,用于任务票 03 的边界验收。

基于任务票 02 的客户端(同通路:$` 提及注入技能、--sandbox、--events-out),
任务票 03 的差异:
- `--events-out` 保留线程内全部 item/completed 事件类型(02 只保留四种),
  用于核对「模型声称的探针结果」与「真实执行的事件流」一致,防口头通过;
- clientInfo 名称更新为任务票 03。

本入口的请求响应、事件等待与进程生命周期由共享实现
`acceptance/_shared/appserver_core.py` 承担(票 14,expand);本文件只保留
场景身份(clientInfo)、命令参数与事件筛选,行为与迁移前逐项兼容。

用法(HOME/CODEX_HOME 指向隔离环境):
  appserver_client.py skills --cwd <项目目录>
  appserver_client.py turn --cwd <工作目录> [--mention mygamestudio:game-code] \
      [--text "提示"] [--out <文件>] [--sandbox workspace-write] \
      [--events-out <文件>] [--timeout 秒]
"""

import argparse
import json  # noqa: F401  票 01 基线探针按模块属性替换解码计数器(冻结产物)
import sys
import time  # noqa: F401  票 01 基线探针按模块属性替换计时器(冻结产物)
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "_shared"))

from appserver_core import run_skills, run_turn  # noqa: E402,F401

# 场景身份:迁移前 clientInfo 常量,保持逐项兼容。
CLIENT_INFO = {
    "name": "mgs03-acceptance",
    "title": "MyGameStudio 03 acceptance",
    "version": "0.1.0",
}
# 场景自身的证据事件筛选:保留全部 item/completed 类型(无 keep_types 限制),
# 另保留 turn 生命周期通知(旧实现写 turn/started|turn/completed|turn/failed)。
EVENT_METHODS = ("turn/started", "turn/completed", "turn/failed")


def cmd_skills(args: argparse.Namespace) -> int:
    return run_skills(CLIENT_INFO, args.cwd)


def cmd_turn(args: argparse.Namespace) -> int:
    prompt = (f"${args.mention} " if args.mention else "") + (args.text or "")
    return run_turn(
        CLIENT_INFO,
        cwd=args.cwd,
        sandbox=args.sandbox,
        prompt=prompt,
        timeout=args.timeout,
        out=args.out,
        events_out=args.events_out,
        keep_types=None,
        event_methods=EVENT_METHODS,
    )


def main() -> int:
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="cmd", required=True)
    p_skills = sub.add_parser("skills")
    p_skills.add_argument("--cwd", required=True)
    p_skills.set_defaults(func=cmd_skills)
    p_turn = sub.add_parser("turn")
    p_turn.add_argument("--cwd", required=True)
    p_turn.add_argument("--mention", help="技能提及名,如 mygamestudio:game-status")
    p_turn.add_argument("--text")
    p_turn.add_argument("--sandbox", default="read-only",
                        choices=["read-only", "workspace-write", "danger-full-access"])
    p_turn.add_argument("--events-out")
    p_turn.add_argument("--out")
    p_turn.add_argument("--timeout", type=int, default=420)
    p_turn.set_defaults(func=cmd_turn)
    args = parser.parse_args()
    if args.cmd == "turn" and not args.mention and not args.text:
        raise SystemExit("需要 --mention 和/或 --text")
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())

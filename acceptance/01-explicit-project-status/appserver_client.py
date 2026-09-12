#!/usr/bin/env python3
"""最小 Codex app-server JSON-RPC(stdio)客户端,用于任务票 01 的显式调用验收。

机制说明(实测 codex-cli 0.151.0):
- `codex exec` 只构造 UserInput::Text 且不解析 `$skill` 文本,显式技能无法注入;
- 交互界面与 app-server 的 turn 通道会解析用户文本中的 `$<技能名>` 提及,并把
  对应 SKILL.md 以 `<skill>` 块注入模型上下文——这是显式调用的真实通路;
- 因此本客户端通过 app-server 提交与界面一致的文本 turn(`$` 提及 + 指令),
  不伪造技能内容、不代读技能文件。

本入口的请求响应、事件等待与进程生命周期由共享实现
`acceptance/_shared/appserver_core.py` 承担(票 14,expand);本文件只保留
场景身份(clientInfo)与命令参数,行为与迁移前逐项兼容:固定 read-only 沙箱、
不提供 --sandbox / --events-out。

用法(HOME/CODEX_HOME 指向隔离环境):
  appserver_client.py skills --cwd <项目目录>
  appserver_client.py turn --cwd <项目目录> [--mention mygamestudio:game-status] \
      [--text "提示"] [--out <文件>] [--timeout 秒]
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
    "name": "mgs01-acceptance",
    "title": "MyGameStudio 01 acceptance",
    "version": "0.1.0",
}


def cmd_skills(args: argparse.Namespace) -> int:
    return run_skills(CLIENT_INFO, args.cwd)


def cmd_turn(args: argparse.Namespace) -> int:
    prompt = (f"${args.mention} " if args.mention else "") + (args.text or "")
    return run_turn(
        CLIENT_INFO,
        cwd=args.cwd,
        sandbox="read-only",  # 01 无 --sandbox:原场景固定只读,不新增沙箱选项
        prompt=prompt,
        timeout=args.timeout,
        out=args.out,
        events_out=None,      # 01 无 --events-out:不新增原场景不存在的事件证据输出
        keep_types=None,
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
    p_turn.add_argument("--out")
    p_turn.add_argument("--timeout", type=int, default=420)
    p_turn.set_defaults(func=cmd_turn)
    args = parser.parse_args()
    if args.cmd == "turn" and not args.mention and not args.text:
        raise SystemExit("需要 --mention 和/或 --text")
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())

#!/usr/bin/env python3
"""最小 Codex app-server JSON-RPC(stdio)客户端,用于任务票 08 的规格拆单验收。

基于任务票 04 的客户端(同通路:`$` 提及注入技能、--sandbox、--events-out),
任务票 08 的差异:
- 新增「受控中断」模式:`--watch-audit <审计文件> --kill-after-allows <N>`
  在等待 turn 完成的同时轮询审计文件,当受控写入 allow 条目达到 N 条时,
  对 codex app-server 进程组发送 SIGKILL,模拟「应用过程中被中断」;
  客户端以退出码 3 结束,事件流中不会有 turn/completed(这本身就是中断证据)。
- codex 进程以独立进程组启动(start_new_session),确保 kill 能覆盖其子进程。
- clientInfo 名称更新为任务票 08。

本入口的请求响应、事件等待、进程生命周期与绝对中断阈值由共享实现
`acceptance/_shared/appserver_core.py` 承担(票 15,expand);本文件只保留场景
身份(clientInfo)、命令参数与事件筛选,行为与迁移前逐项兼容:阈值仍为累计
审计允许次数的**绝对次数**,未引入相对新增计数。

用法(HOME/CODEX_HOME 指向隔离环境):
  appserver_client.py skills --cwd <项目目录>
  appserver_client.py turn --cwd <工作目录> [--mention mygamestudio:game-init] \
      [--text "提示"] [--out <文件>] [--sandbox workspace-write] \
      [--events-out <文件>] [--timeout 秒] \
      [--watch-audit <审计jsonl> --kill-after-allows <N>]
"""

import argparse
import json  # noqa: F401  票 01 基线探针按模块属性替换解码计数器(冻结产物)
import sys
import time  # noqa: F401  票 01 基线探针按模块属性替换计时器(冻结产物)
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "_shared"))

from appserver_core import (  # noqa: E402,F401
    INTERRUPT_POLL_SECONDS, run_skills, run_turn)

# 场景身份:迁移前 clientInfo 常量,保持逐项兼容。
CLIENT_INFO = {
    "name": "mgs08-acceptance",
    "title": "MyGameStudio 08 acceptance",
    "version": "0.1.0",
}
# 场景自身的证据事件筛选:保留全部 item/completed 类型(无 keep_types 限制),
# 另保留 turn 生命周期通知(旧实现写 turn/started|turn/completed|turn/failed)。
EVENT_METHODS = ("turn/started", "turn/completed", "turn/failed")


def cmd_skills(args: argparse.Namespace) -> int:
    return run_skills(CLIENT_INFO, args.cwd, new_session=True)


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
        watch_audit=args.watch_audit,
        kill_after_allows=args.kill_after_allows,
        wait_poll_seconds=INTERRUPT_POLL_SECONDS,
        new_session=True,
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
    p_turn.add_argument("--watch-audit", help="审计 jsonl 路径(受控中断观察目标)")
    p_turn.add_argument("--kill-after-allows", type=int, default=0,
                        help="审计 allow 写入达到该数量时 kill 进程组(模拟中断)")
    p_turn.set_defaults(func=cmd_turn)
    args = parser.parse_args()
    if args.cmd == "turn" and not args.mention and not args.text:
        raise SystemExit("需要 --mention 和/或 --text")
    if args.cmd == "turn" and bool(args.watch_audit) != bool(args.kill_after_allows):
        raise SystemExit("--watch-audit 与 --kill-after-allows 必须成对使用")
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())

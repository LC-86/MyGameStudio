#!/usr/bin/env python3
"""MyGameStudio 运行保障:可信调度侧管理 CLI(任务票 02,票 15 扩展)。

策略维护与实例签发通道,与工作实例分离:业务 Skill 在会话内只能通过
mgs-gate 的 mgs_scope/mgs_write 使用凭据,不能执行本 CLI 的任何操作
(会话沙箱不放开运行根,且服务侧没有工作实例可达的策略写入口)。

用法(由受信任调度方运行,需 MGS_RUNTIME_ROOT):
  mgsrt_admin.py init-policy --spec <policy-spec.json>
  mgsrt_admin.py create-instance --role producer --task T-01 \
      --purpose production --resource docs/mygamestudio/PROJECT.md [--ttl-mins 30]
  mgsrt_admin.py release-instance --id <instance_id>
  mgsrt_admin.py reclaim-locks --id <instance_id>
  mgsrt_admin.py status
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from mgs_runtime import GateService  # noqa: E402


def cmd_init_policy(args: argparse.Namespace) -> int:
    spec = json.loads(Path(args.spec).read_text(encoding="utf-8"))
    service = GateService(args.runtime_root)
    policy = service.init_policy(
        project_root=spec["project_root"],
        roles=spec["roles"],
        purposes=spec["purposes"],
    )
    print(json.dumps({"ok": True, "policy": policy}, ensure_ascii=False, indent=2))
    return 0


def cmd_create_instance(args: argparse.Namespace) -> int:
    service = GateService(args.runtime_root)
    instance = service.create_instance(
        role=args.role,
        task=args.task,
        purpose=args.purpose,
        resources=args.resource,
        ttl_seconds=int(args.ttl_mins * 60),
    )
    print(json.dumps({
        "ok": True,
        "instance_id": instance.instance_id,
        "token": instance.token,
        "role": instance.role,
        "task": instance.task,
        "purpose": instance.purpose,
        "resources": instance.resources,
        "expires_at": time.strftime("%Y-%m-%dT%H:%M:%S%z",
                                    time.localtime(instance.expires_at)),
    }, ensure_ascii=False, indent=2))
    print("令牌只在本次输出中出现一次;登记文件只保存其哈希。", file=sys.stderr)
    return 0


def cmd_release_instance(args: argparse.Namespace) -> int:
    service = GateService(args.runtime_root)
    result = service.release_instance(args.id)
    print(json.dumps(result, ensure_ascii=False))
    return 0 if result["found"] else 1


def cmd_reclaim_locks(args: argparse.Namespace) -> int:
    """回收旧实例遗留占用(任务票 15)。

    顺序:先撤销旧执行能力(release-instance,或等有效期过去)再回收;
    实例仍活跃时本操作拒绝并退出码 1。
    """

    service = GateService(args.runtime_root)
    result = service.reclaim_locks(args.id)
    print(json.dumps(result, ensure_ascii=False))
    return 0 if result["ok"] else 1


def cmd_set_remote_config(args: argparse.Namespace) -> int:
    """写入远端通道配置(任务票 17)。凭据不接受值——只登记环境变量名,
    由 mgs-gate 服务器进程从该环境变量读取;凭据不落盘、不进项目记录。"""

    service = GateService(args.runtime_root)
    channel: dict = {"api_base": args.api_base, "token_env": args.token_env}
    if args.cache_dir:
        channel["cache_dir"] = args.cache_dir
    path = Path(args.runtime_root) / "remote.json"
    path.write_text(json.dumps({"github": channel}, ensure_ascii=False, indent=2),
                    encoding="utf-8")
    print(json.dumps({"ok": True, "remote": {"github": channel},
                      "note": "凭据经环境变量注入(token_env),本文件不保存令牌值"},
                     ensure_ascii=False, indent=2))
    return 0


def cmd_status(args: argparse.Namespace) -> int:
    service = GateService(args.runtime_root)
    instances = service._read_json("instances.json", [])  # noqa: SLF001
    now = time.time()
    summary = []
    for record in instances:
        summary.append({
            "instance_id": record["instance_id"],
            "role": record["role"],
            "task": record["task"],
            "purpose": record["purpose"],
            "resources": record["resources"],
            "released": record.get("released", False),
            "expired": now >= record.get("expires_at", 0),
        })
    locks = service.list_locks()["locks"]
    lock_summary = [
        {"resource": rel, "instance_id": value.get("instance_id"),
         "since": time.strftime("%Y-%m-%dT%H:%M:%S%z",
                                time.localtime(value.get("since", 0)))}
        for rel, value in sorted(locks.items())
    ]
    print(json.dumps({"instances": summary, "locks": lock_summary},
                     ensure_ascii=False, indent=2))
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--runtime-root", default=os.environ.get("MGS_RUNTIME_ROOT", ""),
                        help="运行根目录(默认取 MGS_RUNTIME_ROOT)")
    sub = parser.add_subparsers(dest="cmd", required=True)

    p_init = sub.add_parser("init-policy")
    p_init.add_argument("--spec", required=True, help="策略 JSON 文件")
    p_init.set_defaults(func=cmd_init_policy)

    p_create = sub.add_parser("create-instance")
    p_create.add_argument("--role", required=True,
                          choices=["producer", "design", "implement"])
    p_create.add_argument("--task", required=True)
    p_create.add_argument("--purpose", default="production",
                          choices=["production", "prototype", "review", "playtest"],
                          help="执行用途;review 供独立审查实例签发"
                               "(任务票 13:写入由策略 review.restrict 收窄到 evidence/);"
                               "playtest 供试玩实例签发"
                               "(任务票 14:写入由策略 playtest.restrict 收窄到 evidence/)")
    p_create.add_argument("--resource", action="append", required=True,
                          help="任务授权资源模式,可重复")
    p_create.add_argument("--ttl-mins", type=int, default=30)
    p_create.set_defaults(func=cmd_create_instance)

    p_release = sub.add_parser("release-instance")
    p_release.add_argument("--id", required=True)
    p_release.set_defaults(func=cmd_release_instance)

    p_reclaim = sub.add_parser("reclaim-locks")
    p_reclaim.add_argument("--id", required=True,
                           help="旧实例 id;须已释放(release-instance)或已过期")
    p_reclaim.set_defaults(func=cmd_reclaim_locks)

    p_status = sub.add_parser("status")
    p_status.set_defaults(func=cmd_status)

    p_remote = sub.add_parser(
        "set-remote-config",
        help="写入 GitHub 远端通道配置(任务票 17;凭据只登记环境变量名)")
    p_remote.add_argument("--api-base", required=True,
                          help="API 端点(github.com → https://api.github.com;"
                               "本地替身/企业实例填实际端点)")
    p_remote.add_argument("--token-env", required=True,
                          help="承载凭据的环境变量名(如 MGS_GITHUB_TOKEN);"
                               "不接受令牌值")
    p_remote.add_argument("--cache-dir", default=None,
                          help="离线缓存与未发布草稿目录(可选)")
    p_remote.set_defaults(func=cmd_set_remote_config)

    args = parser.parse_args()
    if not args.runtime_root:
        print("需要 --runtime-root 或 MGS_RUNTIME_ROOT", file=sys.stderr)
        return 2
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())

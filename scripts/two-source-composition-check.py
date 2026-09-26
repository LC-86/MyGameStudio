#!/usr/bin/env python3.12
"""核对「官方外部共同方法 + 本仓库 GameStudio 技能」的两来源组合安装。

install-smoke-test.sh 的第 10 节（Issue #92 游戏设计与文档组）与第 11 节
（Issue #91 工程交付与协作组）共用这一份检查：两节各装各的组合，再按同一组
判据核对来源、打包文件、锁记录、引用可达与取得方式。写成共享脚本是因为同一段
校验复制两份之后已经开始漂移（一处少了来源指纹提示，一处少了反向断言）。

用法（由 install-smoke-test.sh 调用）：

    two-source-composition-check.py --lock <锁文件> --dest <安装目录> \
        --bundled <随包副本> --repo <仓库> --label <本票组名> \
        --group <本票组技能...> [--companions <同源依赖...>] \
        [--writers <正式写作分支...>] [--gap-exempt <缺方法处理的所有者>] \
        [--silent <不得提到外部方法名的技能...>]

成功时打印一行以 `PASS  ` 开头；发现问题时逐条打印 `FAIL  ` 并返回非零。
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sys
from pathlib import Path

EXTERNAL_METHOD = "writing-for-agents"
# 缺外部共同方法时的处理：与各技能正文、tests/test_skills_layout.py 的 GAP_CLAUSE 同文。
GAP_CLAUSE = "无法取得时说明具体缺口和受影响的工作，只继续不依赖它的部分，不模仿缺失的方法"
LINK_RE = re.compile(r"\[[^\]]*\]\(([^)\s]+)\)")


def norm(path: Path) -> Path:
    """只做词法规范化，不解析符号链接：临时目录常经 /var -> /private/var 跳转。"""
    return Path(os.path.normpath(str(path)))


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="核对两来源组合安装")
    parser.add_argument("--lock", required=True, help="组合安装生成的 skills-lock.json")
    parser.add_argument("--dest", required=True, help="组合安装的技能目录")
    parser.add_argument("--bundled", required=True, help="本仓库随包副本目录")
    parser.add_argument("--repo", required=True, help="本仓库路径")
    parser.add_argument("--label", required=True, help="本票组名称，用于成功与失败信息")
    parser.add_argument("--group", required=True, nargs="+", help="本票组技能")
    parser.add_argument("--companions", nargs="*", default=[], help="本票组引用到的同源技能")
    parser.add_argument("--writers", nargs="*", default=[], help="必须按技能名称说明外部方法的写作者")
    parser.add_argument("--gap-exempt", default=None, help="不必自带缺方法处理的写作者（方法所有者）")
    parser.add_argument("--silent", nargs="*", default=[], help="不得提到外部方法名的技能")
    return parser.parse_args(argv)


def check(args: argparse.Namespace) -> list[str]:
    lock_path = Path(args.lock)
    dest = Path(args.dest)
    bundled = Path(args.bundled)
    repo = Path(os.path.realpath(args.repo))
    gamestudio = args.group + args.companions
    problems: list[str] = []

    installed = sorted(p.name for p in dest.iterdir() if p.is_dir())
    expected = sorted(gamestudio + [EXTERNAL_METHOD])
    if installed != expected:
        problems.append("组合安装目录不符：%s" % installed)

    official = dest / EXTERNAL_METHOD
    if not (official / "SKILL.md").is_file():
        problems.append("外部共同方法正文缺失")
    for packaging in ("SOURCE.md", "SHA256SUMS"):
        if (official / packaging).exists():
            problems.append("外部共同方法带上了 GameStudio 随包副本的 %s" % packaging)

    if lock_path.is_file():
        lock = json.loads(lock_path.read_text(encoding="utf-8"))["skills"]
        for name in expected:
            if name not in lock:
                problems.append("锁文件缺少 %s" % name)
        record = lock.get(EXTERNAL_METHOD, {})
        if record.get("source") != "mattpocock/skills":
            problems.append("外部共同方法来源为 %r，应为 mattpocock/skills"
                            % record.get("source"))
        for name in gamestudio:
            source = lock.get(name, {}).get("source", "")
            resolved = Path(os.path.realpath(lock_path.parent / source)) if source else None
            if resolved != repo:
                problems.append("%s 的锁来源不是本仓库：%r" % (name, source))
    else:
        problems.append("组合安装没有生成 skills-lock.json")

    if (official / "SKILL.md").is_file():

        def digest(path: Path) -> str:
            return hashlib.sha256(path.read_bytes()).hexdigest()

        official_hash = digest(official / "SKILL.md")
        bundled_hash = digest(bundled / "SKILL.md")
        print("INFO  官方正文 %s；随包副本 %s%s"
              % (official_hash[:12], bundled_hash[:12],
                 "（内容相同，来源只能由锁记录区分）" if official_hash == bundled_hash else ""))
        print("INFO  官方副本 %s SKILL-MECHANICS.md"
              % ("含" if (official / "SKILL-MECHANICS.md").is_file() else "不含"))

    for name in gamestudio:
        for path in sorted((dest / name).rglob("*.md")):
            for raw in LINK_RE.findall(path.read_text(encoding="utf-8")):
                if raw.startswith(("http://", "https://", "#")):
                    continue
                if "%s/" % EXTERNAL_METHOD in raw:
                    problems.append("%s 用相对链接取得外部共同方法：%s" % (name, raw))
                    continue
                if not norm(path.parent / raw.split("#", 1)[0]).exists():
                    problems.append("%s 的引用在安装结果里不可达：%s" % (name, raw))

    for name in args.writers or gamestudio:
        body_path = dest / name / "SKILL.md"
        if not body_path.is_file():
            # 目录在但正文缺失时也要报 FAIL：崩在这里会让「检查跑过」被误读成通过。
            problems.append("%s/SKILL.md 缺失" % name)
            continue
        body = body_path.read_text(encoding="utf-8")
        if "`%s`" % EXTERNAL_METHOD not in body:
            problems.append("%s 未按技能名称说明外部共同方法" % name)
        if name != args.gap_exempt and GAP_CLAUSE not in body:
            problems.append("%s 缺少缺外部方法时的处理说明" % name)
    for name in args.silent:
        body_path = dest / name / "SKILL.md"
        if not body_path.is_file():
            problems.append("%s/SKILL.md 缺失" % name)
            continue
        body = body_path.read_text(encoding="utf-8")
        if EXTERNAL_METHOD in body:
            problems.append("%s 不直接取得外部共同方法，却提到了它" % name)

    return problems


def main(argv: list[str]) -> int:
    args = parse_args(argv)
    problems = check(args)
    if problems:
        for item in problems:
            print("FAIL  " + item)
        return 1
    print("PASS  两来源组合：%s不依赖随包副本，外部共同方法来源正确且引用可达" % args.label)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))

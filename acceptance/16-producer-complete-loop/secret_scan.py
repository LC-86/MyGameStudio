#!/usr/bin/env python3
"""验收证据入库前的独立凭据扫描(审查修复票 04 / R6)。

与 run.sh 的 sanitize() 实现分离:sanitize 负责把已知明文替换为
<redacted-*> 占位符,本脚本负责独立核对「证据与项目文件中不存在任何
已登记实例凭据的明文」——从扫描目标提取全部 64 位小写 hex 候选串,
逐一计算 SHA-256,与运行根实例登记(instances.json 的 token_hash 全量
集合,不枚举实例名、不区分是否已释放/已过期)以及 ARENA 内全部
*.token 文件比对,命中即输出 finding 并以退出码 1 使验收失败。
报告只包含文件位置与实例号/令牌文件名,永不回显明文。

边界(如实声明):只能发现「运行根已登记或 ARENA 已保存」的凭据明文;
未登记且未保存的未知格式秘密不在探测范围内(与审查报告的有限模式
扫描边界一致);令牌被大写化、分块跨行或嵌入更长 hex 串等变形形态
不产生候选,同样不在探测范围。证据中的合法 SHA-256(文件/策略哈希)
与登记 token_hash 碰撞的概率可忽略,不会误报。指定的每个扫描根
(--evidence/--project)逐一核验:任一根缺失或遍历出错(子目录不可读)
按输入错误处理(退出 2),存在的干净根不得掩盖另一指定根缺失——
复审二 SP-4;扫描目标总数为零(根存在但为空)同样退出 2,不静默通过。

用法:
  python3 secret_scan.py --evidence <证据目录> --project <项目目录> \
      --registry <运行根>/instances.json [--arena-tokens <ARENA>]
退出码:0 未发现凭据明文;1 发现凭据明文(证据不得入库);2 参数或输入错误。
"""

import argparse
import hashlib
import json
import os
import re
import sys

# 令牌由 secrets.token_hex(32) 签发(64 位小写 hex);边界断言避免从更长的
# hex 串(如拼接哈希)中截取假候选
HEX64 = re.compile(r"(?<![0-9a-fA-F])[0-9a-f]{64}(?![0-9a-fA-F])")


def sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def load_registry(path: str, errors: list[str]) -> dict[str, list[dict]]:
    if not os.path.isfile(path):
        errors.append(f"登记文件不存在:{path}")
        return {}
    try:
        with open(path, encoding="utf-8") as fh:
            data = json.load(fh)
    except (OSError, ValueError) as exc:
        errors.append(f"登记文件不可读/非 JSON:{path}:{exc}")
        return {}
    items = data.get("instances", data) if isinstance(data, dict) else data
    if not isinstance(items, list):
        errors.append(f"登记结构不符(期望实例列表):{path}")
        return {}
    mapping: dict[str, list[dict]] = {}
    for item in items:
        token_hash = item.get("token_hash")
        if isinstance(token_hash, str) and token_hash:
            mapping.setdefault(token_hash, []).append(item)
    return mapping


def load_arena_tokens(path: str, errors: list[str]) -> dict[str, str]:
    mapping: dict[str, str] = {}
    if not path:
        return mapping
    if not os.path.isdir(path):
        errors.append(f"ARENA 令牌目录不存在:{path}")
        return mapping
    for name in sorted(os.listdir(path)):
        if not name.endswith(".token"):
            continue
        try:
            with open(os.path.join(path, name), encoding="utf-8") as fh:
                token = fh.read().strip()
        except OSError as exc:
            errors.append(f"令牌文件不可读:{name}:{exc}")
            continue
        if token:
            mapping[sha256_text(token)] = name[: -len(".token")]
    return mapping


def iter_files(roots: list[str], errors: list[str]):
    # SP-4:逐根核验——任一指定根缺失或遍历出错都记入输入错误,不静默跳过;
    # 存在的干净根产出的文件数不得掩盖另一个根缺失(旧实现只看总数)
    for root in roots:
        if os.path.isfile(root):
            yield root
            continue
        if not os.path.exists(root):
            errors.append(f"指定的扫描根不存在:{root}")
            continue

        def record_walk_error(exc: OSError, root: str = root) -> None:
            errors.append(
                f"扫描根遍历失败:{getattr(exc, 'filename', None) or root}:{exc}")

        for dirpath, dirnames, filenames in os.walk(root, onerror=record_walk_error):
            dirnames.sort()
            for filename in sorted(filenames):
                yield os.path.join(dirpath, filename)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="证据入库前的独立凭据扫描(与脱敏实现分离)")
    parser.add_argument("--evidence", action="append", default=[],
                        help="证据目录/文件(可重复)")
    parser.add_argument("--project", action="append", default=[],
                        help="项目目录/文件(可重复)")
    parser.add_argument("--registry", required=True,
                        help="运行根 instances.json(全量 token_hash 比对来源)")
    parser.add_argument("--arena-tokens", default="",
                        help="ARENA 目录(全部 *.token 作为互补比对来源)")
    args = parser.parse_args()

    errors: list[str] = []
    findings: list[str] = []
    registry = load_registry(args.registry, errors)
    arena = load_arena_tokens(args.arena_tokens, errors)

    scanned = 0
    for path in iter_files(list(args.evidence) + list(args.project), errors):
        scanned += 1
        try:
            with open(path, encoding="utf-8", errors="replace") as fh:
                text = fh.read()
        except OSError as exc:
            errors.append(f"扫描目标不可读:{path}:{exc}")
            continue
        for lineno, line in enumerate(text.splitlines(), 1):
            for match in HEX64.finditer(line):
                digest = sha256_text(match.group(0))
                for item in registry.get(digest, ()):
                    findings.append(
                        f"{path}:{lineno}: 已登记实例凭据明文 "
                        f"instance={item.get('instance_id')} "
                        f"role={item.get('role')} task={item.get('task')}")
                if digest in arena:
                    findings.append(
                        f"{path}:{lineno}: ARENA 令牌文件明文 "
                        f"token-file={arena[digest]}")
    if scanned == 0:
        errors.append("扫描目标为零(--evidence/--project 未命中任何文件),无法核对")

    print(f"扫描文件数:{scanned}")
    print(f"比对来源:登记 token_hash {len(registry)} 项;"
          f"ARENA 令牌文件 {len(arena)} 个")
    if findings:
        print(f"发现 {len(findings)} 处已登记/已保存凭据的明文——"
              f"证据不得入库,先脱敏并重扫:")
        for finding in findings:
            print(f"  - {finding}")
    if errors:
        print(f"输入错误 {len(errors)} 项(无法保证扫描完整性):")
        for error in errors:
            print(f"  - {error}")
        return 2
    if findings:
        return 1
    print("未发现任何已登记/已保存凭据的明文")
    return 0


if __name__ == "__main__":
    sys.exit(main())

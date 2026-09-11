#!/usr/bin/env python3
"""票 01 基线探针 A:固定实际代码身份(静态事实)。

记录本票所在分支的提交 SHA、工作区是否干净、五份生产 Python 文件与关键
交接文件的 SHA-256 和物理行数,并把六个重构方向映射到规范/设计中的现有
定位入口。只读;不启动真实模型、不访问网络、不做任何远端写入。

用法:python3 code_identity.py [--out <report.json>]
"""

import argparse
import hashlib
import json
import subprocess
import sys
from pathlib import Path

# evidence/baseline/<file> -> 仓库根
REPO_ROOT = Path(__file__).resolve().parents[4]

PRODUCTION_FILES = (
    "plugin/records/mgs_github.py",
    "plugin/records/mgs_records.py",
    "plugin/runtime/mgs_runtime.py",
    "plugin/runtime/mcp_gate.py",
    "plugin/runtime/mgsrt_admin.py",
)
KEY_FILES = (
    "plugin/.codex-plugin/plugin.json",
    "plugin/provenance/fingerprints.json",
    "dist/package-manifest.txt",
    "dist/SHA256SUMS.txt",
)

# 六个重构方向(design.md「阶段安排」与 spec.md「阶段依次为」):方向 -> 规范入口。
SIX_DIRECTIONS = {
    "0 固定基线": ["spec.md#solution", "issues/01-behavior-baseline.md"],
    "1 原子任务读取统一": ["task-reading.md", "issues/02-record-semantics.md",
                     "issues/03-record-source.md", "issues/04-ready-single-read.md"],
    "2 验收判据与测试组织": ["issues/08-mcp-evidence.md", "issues/09-curl-evidence.md",
                     "issues/10-package-tests.md", "issues/11-backend-tests.md",
                     "issues/12-runtime-tests.md"],
    "3 验收客户端去重": ["issues/13-shared-client-expand.md",
                   "issues/14-shared-client-basic-migrate.md",
                   "issues/15-shared-client-absolute.md",
                   "issues/16-shared-client-relative.md",
                   "issues/17-client-contract.md"],
    "4 工作结果发布恢复": ["issues/18-result-publication.md",
                    "issues/19-recovery-ownership.md",
                    "issues/20-recovery-entrypoints.md"],
    "5 受控写入内部整理": ["issues/21-controlled-local-write.md",
                    "issues/22-controlled-remote-write.md"],
    "6 业务 Skill 与包内说明": ["issues/23-skill-common-expand.md",
                       "issues/24-skill-remaining-migrate.md",
                       "issues/25-skill-contract.md"],
}


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def physical_lines(path: Path) -> int:
    return len(path.read_text(encoding="utf-8", errors="replace").splitlines())


def git(*args: str) -> str:
    out = subprocess.run(["git", "-C", str(REPO_ROOT), *args],
                         capture_output=True, text=True, check=False)
    return out.stdout.strip()


def collect() -> dict:
    files = []
    for rel in PRODUCTION_FILES:
        p = REPO_ROOT / rel
        files.append({"path": rel, "sha256": sha256(p), "lines": physical_lines(p)})
    key_files = []
    for rel in KEY_FILES:
        p = REPO_ROOT / rel
        key_files.append({"path": rel,
                          "present": p.is_file(),
                          "sha256": sha256(p) if p.is_file() else None})
    plugin_json = json.loads((REPO_ROOT / "plugin/.codex-plugin/plugin.json").read_text())
    return {
        "evidence_kind": "static_fact",
        "head_sha": git("rev-parse", "HEAD"),
        "branch": git("branch", "--show-current"),
        "worktree_clean": git("status", "--porcelain") == "",
        "plugin": {"name": plugin_json.get("name"), "version": plugin_json.get("version")},
        "production_files": files,
        "production_total_lines": sum(f["lines"] for f in files),
        "key_files": key_files,
        "six_refactor_directions": SIX_DIRECTIONS,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out")
    args = parser.parse_args()
    report = collect()
    text = json.dumps(report, ensure_ascii=False, indent=2)
    if args.out:
        Path(args.out).write_text(text + "\n", encoding="utf-8")
    else:
        print(text)
    return 0


if __name__ == "__main__":
    sys.exit(main())

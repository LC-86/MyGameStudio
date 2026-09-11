#!/usr/bin/env python3
"""票 01 基线探针 A:固定实际代码身份(静态事实)。

记录本票所在分支的提交 SHA、工作区是否干净(原始与排除基线产物两种口径)、
五份生产 Python 文件与关键交接文件的 SHA-256 和物理行数,并把「六个重构阶段
方向 + 阶段 0 固定基线 + 收口」映射到规范/设计中的现有定位入口,覆盖全部
26 票归属。只读;不启动真实模型、不访问网络、不做任何远端写入。

用法:python3 code_identity.py [--out <report.json>]
"""

import hashlib
import json
import sys
from pathlib import Path

from baseline_common import (FIVE_LABELS, NON_PRODUCT_MARKERS, REPO_ROOT,
                             emit, git, parse_out_args)

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

# 重构阶段构成:阶段 0 固定基线 + 六个重构阶段方向(1-6) + 收口。
# 取值来源:design.md「阶段安排」与 spec.md「Implementation Decisions / 已确认
# 的范围与顺序」。每个方向列出其归属的全部票文件,合计 26 票(01-26)。
REFACTOR_DIRECTIONS = {
    "阶段 0 固定基线": [
        "design.md#阶段安排", "issues/01-behavior-baseline.md"],
    "阶段 1 原子任务读取统一": [
        "task-reading.md", "issues/02-record-semantics.md",
        "issues/03-record-source.md", "issues/04-ready-single-read.md",
        "issues/05-list-show-compatible.md", "issues/06-baseline-verify.md",
        "issues/07-read-stage-closeout.md"],
    "阶段 2 验收判据与测试组织": [
        "issues/08-mcp-evidence.md", "issues/09-curl-evidence.md",
        "issues/10-package-tests.md", "issues/11-backend-tests.md",
        "issues/12-runtime-tests.md"],
    "阶段 3 验收客户端去重": [
        "issues/13-shared-client-expand.md",
        "issues/14-shared-client-basic-migrate.md",
        "issues/15-shared-client-absolute.md",
        "issues/16-shared-client-relative.md",
        "issues/17-client-contract.md"],
    "阶段 4 工作结果发布恢复": [
        "issues/18-result-publication.md",
        "issues/19-recovery-ownership.md",
        "issues/20-recovery-entrypoints.md"],
    "阶段 5 受控写入内部整理": [
        "issues/21-controlled-local-write.md",
        "issues/22-controlled-remote-write.md"],
    "阶段 6 业务 Skill 与包内说明": [
        "issues/23-skill-common-expand.md",
        "issues/24-skill-remaining-migrate.md",
        "issues/25-skill-contract.md"],
    "收口 集成与效益核验": [
        "spec.md#后续阶段的必要验收",
        "issues/26-integrated-verification.md"],
}
# 阶段方向计数:阶段 0(基线)+ 阶段 1-6(六个重构阶段方向)+ 收口,共 8 组 26 票。
DIRECTION_LAYOUT = ("阶段 0 固定基线 + 六个重构阶段方向(1-6)+ 收口,"
                    "合计 26 票(01-26)")


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def physical_lines(path: Path) -> int:
    return len(path.read_text(encoding="utf-8", errors="replace").splitlines())


def worktree_state() -> dict:
    """工作区披露:原始口径与排除基线产物后的口径分别如实记录。

    原始 `worktree_clean` 直接来自 `git status --porcelain`。基线产物目录
    (`evidence/baseline/`)与本票无关的主控进度文件(`execution-log.md`,非本票
    文件)在原始口径下是未跟踪项,故原始口径通常为 false;排除这两类非产品
    项后的 `worktree_clean_excluding_baseline` 才等价于「零产品改动」。
    """

    porcelain = [line for line in git("status", "--porcelain").splitlines()
                 if line.strip()]
    remaining = [line for line in porcelain
                 if not any(marker in line for marker in NON_PRODUCT_MARKERS)]
    return {
        "worktree_clean": not porcelain,
        "worktree_clean_excluding_baseline": not remaining,
        "worktree_clean_excluding_scope": (
            "排除 .scratch/ 下的票产物、工单与主控进度记录后的判断"
            "(即本票零产品行为变更口径;与红线 "
            "`git diff --numstat -- plugin tests acceptance dist` 为 0 一致)"),
        "worktree_porcelain": porcelain,
    }


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
        **worktree_state(),
        "plugin": {"name": plugin_json.get("name"), "version": plugin_json.get("version")},
        "canonical_labels": list(FIVE_LABELS),
        "production_files": files,
        "production_total_lines": sum(f["lines"] for f in files),
        "key_files": key_files,
        "refactor_direction_layout": DIRECTION_LAYOUT,
        "refactor_directions": REFACTOR_DIRECTIONS,
    }


def main() -> int:
    args = parse_out_args(__doc__)
    report = collect()
    emit(report, args.out)
    return 0


if __name__ == "__main__":
    sys.exit(main())

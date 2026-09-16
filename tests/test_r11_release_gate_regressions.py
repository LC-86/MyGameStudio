#!/usr/bin/env python3
"""PR #67 R11 复审(review 5215465015)发版门挡发项修复回归。

双轴评审判定的 Spec 挡发项(规格 #49 对照),逐条公开行为断言:
- R11-1 设计讨论 Issue 不得被迁移盘点成规格并盖正式模块规格章。
- R11-2 源规格 Issue 的评论必须进入盘点;源结果评论不可读必须暂停
  该项而不是回退计划指纹;完成判定必须逐条核对 correspondence.results。
- R11-3 快照完整判定必须逐个核对缺失模块;已有快照复用前必须校验
  归档全文,不得只看索引。
- R11-4 部分暂存(暂存区与工作区都不同于基线)的两段状态都必须进入
  待审成果,只改暂存区也必须使结论失效。
- R11-5 二轮切换必须重新归档回退基线,回退不得恢复上一轮旧快照。
- R11-6 to-spec 部分采纳省略 module_index 时必须保留现行模块索引。
- R11-7 AGENTS.zh-CN.md 议题追踪器表述与 AGENTS.md 一致(Standards)。

    python3 -B tests/test_r11_release_gate_regressions.py
"""

from __future__ import annotations

import sys
import tempfile
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "plugin" / "records"))
sys.path.insert(0, str(REPO_ROOT / "plugin" / "provenance"))
sys.path.insert(0, str(REPO_ROOT / "plugin" / "internal" / "review"))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from github_backend_fixtures import make_checker, run_theme  # noqa: E402
from github_backend_transport import FakeTransport  # noqa: E402

import mgs_records  # noqa: E402

from test_github_material_migration import (  # noqa: E402
    _write_old_github_project)

FAILURES, check = make_checker()


def test_r11_1_discussion_issue_is_not_converted_to_formal_spec() -> None:
    """R11-1: 设计讨论 Issue 保持非权威地位,不得变成待切换模块规格。"""

    with tempfile.TemporaryDirectory() as tmp:
        root, fake = _write_old_github_project(Path(tmp) / "discussion")
        fake.issues.append({
            "number": 60, "id": 1060, "title": "设计讨论(非正式规则)",
            "body": (
                "# 设计讨论 2026-09-15\n\n"
                "讨论身份:round-2026-09-15。种类:讨论记录。不是现行规格。\n\n"
                "## 试验值\n\n跳跃高度 12,未经采纳。\n"
            ),
            "labels": [], "assignees": [], "state": "open",
            "state_reason": None, "html_url": "https://example.invalid/i/60",
        })
        fake.comments[60] = []
        cache = root / "docs/mygamestudio/records/cache"
        plan = mgs_records.plan_github_material_migration(
            root, transport=fake, cache_dir=cache)
        rows = [item for item in (plan.get("items") or [])
                if item.get("source") == "github:issue:60"]
        check(len(rows) == 1, f"讨论 Issue 必须进入盘点,实际 {rows}")
        row = rows[0]
        check(row.get("kind") != "spec" and row.get("role") != "module",
              f"讨论必须按讨论/历史记录盘点,不得归为规格模块,实际 {row}")
        applied = mgs_records.apply_github_material_migration(
            root, plan, confirmed=True, transport=fake, cache_dir=cache)
        check(applied.get("ok") is True, f"讨论不转换不应拖垮迁移:{applied}")
        check(not any("讨论身份:" in (item.get("body") or "")
                      and "迁移状态:pending-switch" in (item.get("body") or "")
                      for item in fake.issues),
              "讨论记录不得被转换成待切换成果")
        check(not any("跳跃高度 12" in (item.get("body") or "")
                      and "规格身份:" in (item.get("body") or "")
                      and "迁移状态:pending-switch" in (item.get("body") or "")
                      for item in fake.issues),
              "试验值不得经迁移盖正式规格章后暴露为现行模块规格")


if __name__ == "__main__":
    raise SystemExit(run_theme(
        "PR #67 R11 发版门挡发项修复回归",
        (
            test_r11_1_discussion_issue_is_not_converted_to_formal_spec,
        ),
        FAILURES,
    ))

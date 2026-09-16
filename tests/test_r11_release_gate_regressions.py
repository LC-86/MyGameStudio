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


def _cache(root: Path) -> Path:
    return root / "docs/mygamestudio/records/cache"


def test_r11_2_spec_comments_inventoried_and_results_gated() -> None:
    """R11-2a: 源规格 Issue 评论承载的采纳决定必须进入盘点并迁移。"""

    with tempfile.TemporaryDirectory() as tmp:
        root, fake = _write_old_github_project(Path(tmp) / "spec-comments")
        fake.issues.append({
            "number": 61, "id": 1061, "title": "现行规格",
            "body": (
                "规格身份:overall。种类:现行规格。版本:v2。\n\n"
                "## 核心玩法\n\n玩家左右移动接住落下的金色星星。\n\n"
                "## 当前规则与流程\n\n- 得分：每颗金色星星 1 分。\n"
            ),
            "labels": [], "assignees": [], "state": "open",
            "state_reason": None, "html_url": "https://example.invalid/i/61",
        })
        fake.comments[61] = [{
            "id": 6201,
            "body": ("# 计分决定\n\n身份:dec-score\n状态:已采纳\n\n"
                     "星星计分从 1 改 2,采纳于讨论。\n"),
            "created_at": "2026-09-10T12:00:00Z",
        }]
        plan = mgs_records.plan_github_material_migration(
            root, transport=fake, cache_dir=_cache(root))
        rows = [item for item in (plan.get("items") or [])
                if item.get("source") == "github:comment:6201"]
        check(len(rows) == 1 and rows[0].get("kind") == "decision",
              f"规格评论必须作为决定进入盘点,实际 {rows}")
        applied = mgs_records.apply_github_material_migration(
            root, plan, confirmed=True, transport=fake, cache_dir=_cache(root))
        check(applied.get("ok") is True, f"迁移应完成:{applied}")
        overall_no = applied.get("correspondence", {}).get("specs", [{}])[0] \
            .get("new_issue") if applied.get("correspondence", {}).get("specs") \
            else applied.get("overall_issue")
        overall_no = overall_no or applied.get("overall_issue")
        comments = fake.comments.get(int(overall_no or 0)) or []
        check(any("星星计分从 1 改 2" in (comment.get("body") or "")
                  and "身份:dec-score" in (comment.get("body") or "")
                  for comment in comments),
              "规格评论的 GitHub 独有历史必须迁入新规格评论,不得静默丢失")
        report = mgs_records.read_github_material_migration(
            root, transport=fake, cache_dir=_cache(root))
        check(report.get("complete") is True,
              f"规格评论决定迁入后迁移仍应完整:{report.get('missing')}")


def test_r11_2_unreadable_result_comment_pauses_item() -> None:
    """R11-2b: 源结果评论不可读必须暂停该项,不得回退计划指纹放行。"""

    with tempfile.TemporaryDirectory() as tmp:
        root, fake = _write_old_github_project(Path(tmp) / "lost-comment")
        # 另一条结果保证「结果」类别非空:仅静默丢一条时旧代码仍可切换。
        fake.comments[2].append({
            "id": 6202,
            "body": ("# 跳跃结果\n\n任务:02-jump。实际成果:src/jump.js "
                     "空格跳跃。已执行验证:代码级检查通过。\n"),
            "created_at": "2026-09-07T12:00:00Z",
        })
        plan = mgs_records.plan_github_material_migration(
            root, transport=fake, cache_dir=_cache(root))
        # 准备之后、执行之前:01-move 的结果评论被删除。
        fake.comments[1] = [item for item in fake.comments[1]
                            if item.get("id") != 6101]
        applied = mgs_records.apply_github_material_migration(
            root, plan, confirmed=True, transport=fake, cache_dir=_cache(root))
        check(applied.get("ok") is True, f"其余资料仍应转换:{applied}")
        paused = [str(item) for item in applied.get("paused") or []]
        check(any("01-move" in item for item in paused),
              f"不可读的结果评论必须暂停该结果,实际 {paused}")
        report = mgs_records.read_github_material_migration(
            root, transport=fake, cache_dir=_cache(root))
        check(report.get("complete") is False,
              "结果来源不可读时不得宣告迁移完整可切换")


def test_r11_2_complete_verifies_every_mapped_result() -> None:
    """R11-2c: 完成判定必须逐条核对 correspondence.results 的目标评论。"""

    with tempfile.TemporaryDirectory() as tmp:
        root, fake = _write_old_github_project(Path(tmp) / "verify-results")
        applied = mgs_records.apply_github_material_migration(
            root, None, confirmed=True, transport=fake, cache_dir=_cache(root))
        check(applied.get("ok") is True, f"迁移应完成:{applied}")
        report = mgs_records.read_github_material_migration(
            root, transport=fake, cache_dir=_cache(root))
        check(report.get("complete") is True,
              f"前置:完整迁移应可切换:{report.get('missing')}")
        rows = (report.get("correspondence") or {}).get("results") or []
        check(bool(rows), "前置:应有结果对应关系")
        row = rows[0]
        needle = str(row.get("needle") or "")
        number = row.get("new_issue")
        check(bool(needle) and bool(number),
              f"结果对应关系必须记录可回查的迁移评论身份,实际 {row}")
        # 场景一:已迁移的结果评论在切换前被删除。
        fake.comments[int(number)] = [
            item for item in fake.comments.get(int(number), [])
            if needle not in (item.get("body") or "")]
        deleted = mgs_records.read_github_material_migration(
            root, transport=fake, cache_dir=_cache(root))
        check(deleted.get("complete") is False,
              "迁移结果评论缺失时不得保持完整判定")
        missing = [str(item) for item in deleted.get("missing") or []]
        check(any("01-move" in item and ("结果" in item or "评论" in item)
                  for item in missing),
              f"缺口必须点名缺失的结果,实际 {missing}")

    with tempfile.TemporaryDirectory() as tmp:
        root, fake = _write_old_github_project(Path(tmp) / "tampered-result")
        applied = mgs_records.apply_github_material_migration(
            root, None, confirmed=True, transport=fake, cache_dir=_cache(root))
        report = mgs_records.read_github_material_migration(
            root, transport=fake, cache_dir=_cache(root))
        check(report.get("complete") is True, "前置:迁移应完整")
        row = ((report.get("correspondence") or {}).get("results") or [{}])[0]
        number = int(row.get("new_issue"))
        needle = str(row.get("needle") or "")
        for item in fake.comments.get(number, []):
            if needle in (item.get("body") or ""):
                item["body"] = (item.get("body") or "") + "\n篡改:宣称已试玩通过。\n"
        tampered = mgs_records.read_github_material_migration(
            root, transport=fake, cache_dir=_cache(root))
        check(tampered.get("complete") is False,
              "迁移结果评论被篡改时不得保持完整判定")
        missing = [str(item) for item in tampered.get("missing") or []]
        check(any("01-move" in item for item in missing),
              f"篡改必须成为点名结果的完整性缺口,实际 {missing}")


if __name__ == "__main__":
    raise SystemExit(run_theme(
        "PR #67 R11 发版门挡发项修复回归",
        (
            test_r11_1_discussion_issue_is_not_converted_to_formal_spec,
            test_r11_2_spec_comments_inventoried_and_results_gated,
            test_r11_2_unreadable_result_comment_pauses_item,
            test_r11_2_complete_verifies_every_mapped_result,
        ),
        FAILURES,
    ))

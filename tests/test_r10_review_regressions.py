#!/usr/bin/env python3
"""PR #67 R10 复审(review 5214770813)修复回归。

逐条对应 R10 复审意见的公开行为断言:
- R10-1 标记读取非 2xx 必须失败闭合,不得把读不到当成标记已移除。
- R10-2 标记迁移部分失败时,已成功步骤必须按变更前正文回补并核实。
- R10-3 依赖关系 POST 422 后必须回读核实,缺失按冲突暂停且回读可见。
- R10-4 复用默认身份收养既有工单前必须核对内容,碰撞按失败上报。
- R10-5 规格采纳计划过期(基线指纹不符)必须拒绝并要求重新规划。
- R10-6 已登记版本的快照关联同样补齐实现/发布元数据并回读核实。
- R10-7 回滚必须把客户端技能恢复到切换前状态(留档+新装双向)。
- R10-8 迁移准备之后新增的源记录必须成为完整性缺口并阻塞切换。
- R10-9 分支基线按 merge-base 比较,基线上的无关改动不得混入。
- R10-10 并发撤销不得互相覆盖丢条目;撤销检查与写入同锁。
- R10-11 发布检查必须与固定期望技能集合对账,缺项即失败。
- R10-12 CLI 暴露新安全切换生命周期,旧 apply 指引不再指向已退役
  mgs-gate。

    python3 -B tests/test_r10_review_regressions.py
"""

from __future__ import annotations

import json
import sys
import tempfile
import threading
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "plugin" / "records"))
sys.path.insert(0, str(REPO_ROOT / "plugin" / "provenance"))
sys.path.insert(0, str(REPO_ROOT / "plugin" / "internal" / "review"))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from github_backend_fixtures import (  # noqa: E402
    make_checker, run_cli, run_theme, _StandinServer)
from github_backend_transport import FakeTransport  # noqa: E402

import mgs_records  # noqa: E402

from test_github_material_migration import (  # noqa: E402
    _write_old_github_project)
from test_safe_switch import _convert_local, _write_old_local_project  # noqa: E402
from test_design_version_snapshot import _onboard_local  # noqa: E402

FAILURES, check = make_checker()


def _migrate_github(root: Path, fake: FakeTransport) -> dict:
    applied = mgs_records.apply_github_material_migration(
        root, mgs_records.plan_github_material_migration(
            root, transport=fake),
        confirmed=True, transport=fake)
    return applied


def _old_task_numbers(plan: dict) -> list[int]:
    numbers = []
    for row in (plan.get("correspondence") or {}).get("tasks") or []:
        old = str(row.get("old") or "")
        if old.startswith("github:issue:"):
            numbers.append(int(old.rsplit(":", 1)[-1]))
    return sorted(set(numbers))


def _new_task_numbers(plan: dict) -> list[int]:
    return sorted({int(row["new_issue"]) for row in
                   (plan.get("correspondence") or {}).get("tasks") or []
                   if isinstance(row.get("new_issue"), int)})


def _issue_body(fake: FakeTransport, number: int) -> str:
    for item in fake.issues:
        if item.get("number") == number:
            return item.get("body") or ""
    return ""


def test_r10_1_marker_read_failure_fails_closed() -> None:
    """R10-1: 标记读取非 2xx 不得当成「标记已不在」,必须失败闭合。"""

    with tempfile.TemporaryDirectory() as tmp:
        root, fake = _write_old_github_project(Path(tmp) / "read-500")
        _migrate_github(root, fake)
        plan = mgs_records.plan_safe_switch(root, transport=fake)
        check(plan.get("ready") is True, f"前置:待切换应就绪:{plan.get('blockers')}")
        olds = _old_task_numbers(plan)
        check(bool(olds), "前置:应有旧权威任务 Issue")
        # 读取旧权威 Issue 返回 500:旧代码把空正文当「无标记」继续切换。
        # (复检与标记两道闸门都必须因这次失败读取闭合,任何一层都不得
        # 把读不到当成「标记已移除」后放行。)
        fake.http_error("GET", f"/issues/{olds[0]}", 500)
        before = len(fake.calls)
        applied = mgs_records.apply_safe_switch(
            root, plan, confirmed=True, transport=fake)
        check(applied.get("ok") is False,
              f"读取未确认时不得宣告切换完成:{applied.get('reason')}")
        patches = [call for call in fake.calls[before:]
                   if call[0] == "PATCH" and "/issues" in str(call[1])]
        check(not patches, "读取未确认时不得发出任何标记 PATCH")
        check(applied.get("status") == "pending-switch",
              "读取失败时必须保持待切换状态")
        check(not (root / "docs/mygamestudio/records/pending-switch"
                   / "switch-status.json").is_file(),
              "读取未确认时不得写切换状态(不提升本地)")


def test_r10_2_partial_marker_failure_compensates() -> None:
    """R10-2: 后续标记失败时,已成功步骤按变更前正文回补并回读核实。"""

    with tempfile.TemporaryDirectory() as tmp:
        root, fake = _write_old_github_project(Path(tmp) / "partial-mark")
        _migrate_github(root, fake)
        plan = mgs_records.plan_safe_switch(root, transport=fake)
        olds = _old_task_numbers(plan)
        news = _new_task_numbers(plan)
        check(len(olds) >= 1 and bool(news), "前置:应有新旧任务映射")
        originals = {n: _issue_body(fake, n) for n in olds + news}
        # 第二个旧权威 Issue 的 PATCH 失败:此前已成功的标记必须回补。
        fake.http_error("PATCH", f"/issues/{olds[-1]}", 500)
        applied = mgs_records.apply_safe_switch(
            root, plan, confirmed=True, transport=fake)
        check(applied.get("ok") is False,
              f"标记部分失败不得宣告切换完成:{applied.get('reason')}")
        check(bool(applied.get("compensated_markers")),
              f"必须报告已回补的标记步骤:{applied.get('compensated_markers')}")
        check("迁移状态:readonly-history" not in _issue_body(fake, olds[0]),
              "已成功写入的 readonly-history 必须回补为变更前正文")
        for number in news:
            check("迁移状态:pending-switch" in _issue_body(fake, number),
                  f"新 Issue #{number} 的标记移除必须回补,保持待切换")
        for number in olds + news:
            if number == olds[-1]:
                continue
            check(_issue_body(fake, number) == originals[number],
                  f"#{number} 回补后必须与变更前正文一致")


def test_r10_3_dependency_422_requires_readback() -> None:
    """R10-3: 依赖关系 POST 422 只代表送达;缺失必须回读发现并阻塞切换。"""

    with tempfile.TemporaryDirectory() as tmp:
        root, fake = _write_old_github_project(Path(tmp) / "dep-422")
        fake.seed_issue("04-follow", "跟随移动的任务", deps="01-move")
        fake.http_error("POST", "/dependencies/blocked_by", 422)
        applied = _migrate_github(root, fake)
        paused = [str(item) for item in applied.get("paused") or []]
        check(any("原生落地未确认" in item and "01-move" in item
                  for item in paused),
              f"422 后关系缺失必须按冲突暂停,实际 {paused}")
        report = mgs_records.read_github_material_migration(
            root, transport=fake)
        check(report.get("complete") is False,
              "依赖缺失时不得宣告迁移完整")
        missing = [str(item) for item in report.get("missing") or []]
        check(any("原生依赖未确认" in item for item in missing),
              f"回读必须对照意图指出缺失的依赖,实际 {missing}")
        check(mgs_records.plan_safe_switch(
            root, transport=fake).get("ready") is not True,
            "依赖缺失时不得放行全局切换")


def test_r10_4_playable_adoption_collision_rejected() -> None:
    """R10-4: 复用默认身份收养既有工单前核对内容,碰撞按失败上报。"""

    with tempfile.TemporaryDirectory() as tmp:
        root = _onboard_local(Path(tmp) / "playable-collision")
        first = mgs_records.apply_playable_delivery(
            root, mgs_records.plan_playable_delivery(
                root, {"title": "第一次可玩交付"}), confirmed=True)
        check(first.get("ok") is True, f"前置:首次交付应成功:{first}")
        second = mgs_records.apply_playable_delivery(
            root, mgs_records.plan_playable_delivery(
                root, {"title": "第二次完全不同的交付"}), confirmed=True)
        check(second.get("ok") is False,
              f"身份碰撞不得计为本计划已应用:{second}")
        check(any(item.get("identity_collision")
                  for item in second.get("created") or []),
              "必须点名身份碰撞的工单")
        check("身份碰撞" in str(second.get("reason")),
              f"必须说明按碰撞失败闭合:{second.get('reason')}")


def test_r10_5_stale_spec_plan_requires_replan() -> None:
    """R10-5: 计划基线与现行不符时拒绝执行;幂等重放仍允许。"""

    def _plan(version: str, score: str) -> dict:
        return mgs_records.plan_spec_adoption(root, {
            "kind": "small_change",
            "source": "开发者主动 to-spec",
            "reason": f"正式改为 {score}",
            "overall": {
                "title": "star-catcher：当前游戏需求与设计",
                "version": version,
                "core_play": "玩家移动角色接住落下的星星。",
                "rules": [f"得分：{score}。"],
            },
        })

    with tempfile.TemporaryDirectory() as tmp:
        root = _onboard_local(Path(tmp) / "stale-plan")
        plan_b = _plan("v2", "每颗星星 3 分")
        plan_a = _plan("v3", "每颗星星 5 分")
        applied_b = mgs_records.apply_spec_adoption(root, plan_b, confirmed=True)
        check(applied_b.get("ok") is True, f"前置:新计划应可执行:{applied_b}")
        stale = mgs_records.apply_spec_adoption(root, plan_a, confirmed=True)
        check(stale.get("ok") is False,
              f"过期计划不得覆盖确认之间的新修改:{stale}")
        check(stale.get("replan_required") is True,
              "必须明确要求重新规划")
        check("重新规划" in str(stale.get("reason")),
              f"必须说明基线不一致:{stale.get('reason')}")
        again = mgs_records.apply_spec_adoption(root, plan_b, confirmed=True)
        check(again.get("ok") is True,
              f"同一计划的幂等重放(恢复)仍应允许:{again}")


def test_r10_6_snapshot_reuse_updates_metadata() -> None:
    """R10-6: 已登记版本的复用关联同样补齐实现/发布并回读核实。"""

    with tempfile.TemporaryDirectory() as tmp:
        root = _onboard_local(Path(tmp) / "reuse-meta")
        first = mgs_records.apply_design_snapshot(
            root, mgs_records.plan_design_snapshot(root, {
                "trigger": "version_freeze",
                "game_version": "0.1.0",
                "source": "正式版本设计确定",
            }), confirmed=True)
        check(first.get("complete") is True, f"前置:首次冻结应成功:{first}")
        reused = mgs_records.apply_design_snapshot(
            root, mgs_records.plan_design_snapshot(root, {
                "trigger": "version_freeze",
                "game_version": "0.1.0",
                "reuse_design_id": first.get("design_id"),
                "implementation": "构建 build-abc",
                "release": "标签 v1.0.0",
            }), confirmed=True)
        check(reused.get("complete") is True,
              f"补登记应成功:{reused.get('reason')}")
        listed = mgs_records.read_design_snapshots(root)
        snap = (listed.get("snapshots") or [{}])[0]
        check("build-abc" in str(snap.get("implementation")),
              f"归档元数据必须真实记录实现状态,实际 {snap.get('implementation')}")
        check("v1.0.0" in str(snap.get("release")),
              f"归档元数据必须真实记录发布状态,实际 {snap.get('release')}")


def test_r10_7_rollback_restores_client_skills() -> None:
    """R10-7: 回滚把客户端技能恢复到切换前(留档恢复+新装移除)。"""

    pkg_tdd = "# TDD\n\nred green refactor\n"
    with tempfile.TemporaryDirectory() as tmp:
        base = Path(tmp)
        root = _write_old_local_project(base / "skill-rollback")
        _convert_local(root)
        home = base / "client-home"
        skills_root = base / "pkg" / "skills"
        (home / "skills" / "tdd").mkdir(parents=True)
        (home / "skills" / "tdd" / "SKILL.md").write_text(
            pkg_tdd + "\n## 用户修改\n\n本地偏好。\n", encoding="utf-8")
        (skills_root / "tdd").mkdir(parents=True)
        (skills_root / "tdd" / "SKILL.md").write_text(pkg_tdd, encoding="utf-8")
        (skills_root / "research").mkdir(parents=True)
        (skills_root / "research" / "SKILL.md").write_text(
            "# Research\n\n新包新增。\n", encoding="utf-8")
        plan = mgs_records.plan_safe_switch(
            root, client_home=home, package_root=skills_root)
        check(plan.get("ready") is True, f"前置:应可切换:{plan.get('blockers')}")
        applied = mgs_records.apply_safe_switch(root, plan, confirmed=True)
        check(applied.get("ok") is True, f"前置:切换应成功:{applied}")
        live = (home / "skills" / "tdd" / "SKILL.md").read_text(encoding="utf-8")
        check(live.startswith(pkg_tdd),
              "前置:切换后技能应来自新包")
        check((home / "skills" / "research" / "SKILL.md").is_file(),
              "前置:新包新增技能应已安装")
        rolled = mgs_records.rollback_safe_switch(root, confirmed=True)
        check(rolled.get("ok") is True and rolled.get("status") == "rolled-back",
              f"回滚应成功:{rolled}")
        check("tdd" in (rolled.get("skills_restored") or []),
              f"必须报告已恢复的技能:{rolled.get('skills_restored')}")
        restored = (home / "skills" / "tdd" / "SKILL.md").read_text(encoding="utf-8")
        check(restored == pkg_tdd + "\n## 用户修改\n\n本地偏好。\n",
              "回滚后技能必须恢复为切换前内容")
        check(not (home / "skills" / "research" / "SKILL.md").exists(),
              "切换新装的技能入口必须随回滚移除")


def test_r10_8_new_source_after_preparation_blocks() -> None:
    """R10-8: 准备之后新增的源记录必须成为缺口并阻塞全局切换。"""

    with tempfile.TemporaryDirectory() as tmp:
        root = _write_old_local_project(Path(tmp) / "late-source")
        _convert_local(root)
        before = mgs_records.read_local_material_migration(root)
        check(before.get("complete") is True,
              f"前置:未新增来源时应完整:{before.get('missing')}")
        (root / "docs/mygamestudio/records/decision-late.md").write_text(
            "# 是否加入连击\n\n状态:未决。日期:2026-09-16。\n", encoding="utf-8")
        after = mgs_records.read_local_material_migration(root)
        check(after.get("complete") is False,
              "准备期间新增来源不得被旧清单掩盖")
        missing = [str(item) for item in after.get("missing") or []]
        check(any("准备期间新增" in item and "decision-late" in item
                  for item in missing),
              f"必须按来源身份指出新增未转换项,实际 {missing}")
        check(mgs_records.plan_safe_switch(root).get("ready") is not True,
              "存在未转换新来源时不得放行全局切换")


def test_r10_9_baseline_uses_merge_base() -> None:
    """R10-9: 分支基线按 merge-base 比较;基线上的无关改动不混入。"""

    import os
    import subprocess

    import pending_review

    def _git(repo: Path, *args: str) -> None:
        env = dict(os.environ, GIT_AUTHOR_NAME="t", GIT_AUTHOR_EMAIL="t@t",
                   GIT_COMMITTER_NAME="t", GIT_COMMITTER_EMAIL="t@t")
        subprocess.run(["git", *args], cwd=repo, check=True,
                       capture_output=True, env=env)

    with tempfile.TemporaryDirectory() as tmp:
        repo = Path(tmp) / "repo"
        repo.mkdir()
        _git(repo, "init", "-q", "-b", "main")
        (repo / "a.txt").write_text("base\n", encoding="utf-8")
        (repo / "b.txt").write_text("b1\n", encoding="utf-8")
        _git(repo, "add", "-A")
        _git(repo, "commit", "-q", "-m", "base")
        _git(repo, "checkout", "-q", "-b", "feature")
        (repo / "b.txt").write_text("b2\n", encoding="utf-8")
        _git(repo, "add", "-A")
        _git(repo, "commit", "-q", "-m", "feature change")
        _git(repo, "checkout", "-q", "main")
        (repo / "c.txt").write_text("main only\n", encoding="utf-8")
        _git(repo, "add", "-A")
        _git(repo, "commit", "-q", "-m", "main unrelated")
        _git(repo, "checkout", "-q", "feature")
        captured = pending_review.capture_pending_review(
            repo, "main", include=["."])
        committed = captured.get("paths", {}).get("committed") or []
        check("b.txt" in committed, f"分支自身改动应在捕获内:{committed}")
        check("c.txt" not in committed,
              f"基线分支后来的无关改动不得混入:{committed}")
        check("c.txt" not in (captured.get("patch") or ""),
              "基线上的无关文件不得以反向补丁进入产物")
        check("c.txt" not in (captured.get("path_versions") or {}),
              "无关文件不得计入内容版本")
        check(bool(captured.get("merge_base")),
              "必须记录实际使用的 merge-base")


def test_r10_10_concurrent_cancellations_keep_entries() -> None:
    """R10-10: 并发撤销不得互相覆盖丢条目(读-改-写全程同锁)。"""

    import mgs_local_backend
    import mgs_record_source

    with tempfile.TemporaryDirectory() as tmp:
        root = _onboard_local(Path(tmp) / "cancel-race")
        errors: list[str] = []

        def _worker(tag: str) -> None:
            try:
                for index in range(15):
                    mgs_records.cancel_operation(
                        root, "create_task", f"{index:02d}-race-{tag}")
            except Exception as exc:  # noqa: BLE001
                errors.append(str(exc))

        threads = [threading.Thread(target=_worker, args=(tag,))
                   for tag in ("a", "b")]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join()
        check(not errors, f"并发撤销不应失败:{errors}")
        entries = mgs_local_backend.load_cancelled(
            root, mgs_record_source.load_config(root))
        check(len(entries) == 30,
              f"并发撤销不得丢失条目,实际登记 {len(entries)}/30")


def test_r10_11_release_check_requires_expected_skills() -> None:
    """R10-11: 发现面与固定期望集合对账;缺一个技能即失败。"""

    import shutil

    import mgs_release_check
    from test_technical_delivery import _plugin_fixture

    with tempfile.TemporaryDirectory() as tmp:
        plugin = _plugin_fixture(Path(tmp) / "release-check")
        intact = mgs_release_check._discovery(plugin)
        check(intact.get("local_package_surface") == "passed",
              f"前置:完整技能集合应通过:{intact.get('missing_skills')}")
        shutil.rmtree(plugin / "skills" / "wizard")
        broken = mgs_release_check._discovery(plugin)
        check(broken.get("local_package_surface") == "failed",
              "缺项的残缺包不得通过发现面检查")
        check("wizard" in (broken.get("missing_skills") or []),
              f"必须点名缺失的技能:{broken.get('missing_skills')}")


def test_r10_12_cli_safe_switch_lifecycle_and_gate_pointer() -> None:
    """R10-12: CLI 暴露安全切换生命周期;旧 apply 指引不再指向已退役 gate。"""

    from github_backend_fixtures import make_github_project

    with tempfile.TemporaryDirectory() as tmp:
        base = Path(tmp)
        root = _write_old_local_project(base / "cli-switch")
        _convert_local(root)
        checked = run_cli("switch-check", "--project", str(root))
        check(checked.returncode == 0,
              f"switch-check 应可用:{checked.stdout[-300:]}{checked.stderr[-200:]}")
        report = json.loads(checked.stdout)
        check(report.get("ready") is True,
              f"switch-check 应就绪:{report.get('blockers')}")
        ran = run_cli("switch-run", "--project", str(root), "--confirmed")
        outcome = json.loads(ran.stdout)
        check(outcome.get("ok") is True and outcome.get("status") == "switched",
              f"switch-run 应完成切换:{outcome}")
        status = json.loads(
            run_cli("switch-status", "--project", str(root)).stdout)
        check(status.get("status") == "switched", "switch-status 应回读状态")
        back = json.loads(run_cli(
            "switch-rollback", "--project", str(root), "--confirmed").stdout)
        check(back.get("status") == "rolled-back",
              f"switch-rollback 应可回退:{back}")

        gh_root = make_github_project(base / "reverse")
        fake = FakeTransport()
        fake.seed_issue("01-alpha", "甲任务")
        server = _StandinServer(fake)
        server.start()
        try:
            plan_path = base / "reverse-plan.json"
            emit = base / "reverse-emit"
            planned = run_cli(
                "switch-plan", "--project", str(gh_root),
                "--target", "local-markdown", "--emit", str(plan_path),
                "--api-base", server.base)
            check(planned.returncode == 0,
                  f"前置:反向迁移清单应可生成:{planned.stderr[-200:]}")
            applied = run_cli(
                "switch-apply", "--project", str(gh_root),
                "--plan", str(plan_path), "--emit-dir", str(emit),
                "--confirmed", "--api-base", server.base)
            check(applied.returncode == 0,
                  f"前置:反向迁移应可执行:{applied.stdout[-200:]}")
            note = str((json.loads(applied.stdout) or {}).get("note"))
            check("switch-run" in note,
                  f"产出指引必须指向现存的安全切换命令:{note}")
            check("经 mgs-gate 写入" not in note,
                  f"不得再指引经已退役的 mgs-gate 安装:{note}")
        finally:
            server.stop()


if __name__ == "__main__":
    raise SystemExit(run_theme(
        "PR #67 R10 复审修复回归",
        (
            test_r10_1_marker_read_failure_fails_closed,
            test_r10_2_partial_marker_failure_compensates,
            test_r10_3_dependency_422_requires_readback,
            test_r10_4_playable_adoption_collision_rejected,
            test_r10_5_stale_spec_plan_requires_replan,
            test_r10_6_snapshot_reuse_updates_metadata,
            test_r10_7_rollback_restores_client_skills,
            test_r10_8_new_source_after_preparation_blocks,
            test_r10_9_baseline_uses_merge_base,
            test_r10_10_concurrent_cancellations_keep_entries,
            test_r10_11_release_check_requires_expected_skills,
            test_r10_12_cli_safe_switch_lifecycle_and_gate_pointer,
        ),
        FAILURES))

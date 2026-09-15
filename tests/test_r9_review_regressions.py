#!/usr/bin/env python3
"""PR #67 R9 复审(review 5212273006)修复回归。

逐条对应 R9 复审意见的公开行为断言:
- R9-1 规格采纳恢复路径必须逐模块比对正文,同身份旧正文不算完成。
- R9-2 结果评论已发布而索引未更新(部分成功)不算正式交付完成。
- R9-3 原生父子关系赋值被 422 拒绝时按失败上报,不虚报原生成功。
- R9-4 new_material_decisions 里的额外键(根外路径)不得进入采纳。
- R9-5 待切换映射行绑定内容指纹,迁移后删改产物不得宣告完整。
- R9-6 回滚时切换后新增的 GitHub 任务也要打 pending-switch 标记。
- R9-7 两个源 Issue 共用任务身份时按冲突暂停,不共享目标。
- R9-8 接入分析先按路径分类,不为资产文件付出全量解码。
- R9-9 受限范围迁移未覆盖全部来源时不得放行全局切换。
- R9-10 切换与回退前按当前 CONFIG 重查 issues-write 授权,缺失失败闭合。

    python3 -B tests/test_r9_review_regressions.py
"""

from __future__ import annotations

import sys
import tempfile
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "plugin" / "records"))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from github_backend_fixtures import (  # noqa: E402
    AUTH, REPO, make_checker, make_github_project, run_theme)
from github_backend_transport import FakeTransport  # noqa: E402

import mgs_records  # noqa: E402

FAILURES, check = make_checker()


def _adopt_plan(root: Path, fake: FakeTransport, *, version: str,
                rules: list[str], modules: dict | None = None,
                cache: Path | None = None) -> dict:
    return mgs_records.plan_spec_adoption(root, {
        "kind": "new_feature" if version == "v1" else "small_change",
        "source": "开发者主动 to-spec",
        "reason": "R9 回归",
        "overall": {
            "title": "R9 整体设计",
            "version": version,
            "core_play": "接星星。",
            "rules": rules,
        },
        "modules": modules or {},
    }, transport=fake, cache_dir=cache)


def test_r9_1_recovery_compares_module_bodies() -> None:
    """R9-1: 模块更新失败后,同身份旧正文不得让恢复路径宣告采用完成。"""

    with tempfile.TemporaryDirectory() as tmp:
        root = make_github_project(Path(tmp) / "spec-recovery")
        fake = FakeTransport()
        cache = root / "docs/mygamestudio/records/cache"
        first = mgs_records.apply_spec_adoption(
            root, _adopt_plan(root, fake, version="v1",
                              rules=["得分：每颗星星 1 分。"],
                              modules={"规则与数值": {
                                  "title": "规则与数值",
                                  "rules": ["每颗星星 1 分。"]}},
                              cache=cache),
            confirmed=True, transport=fake, cache_dir=cache)
        check(first.get("ok") is True, f"前置:首次采纳应成功:{first}")
        # 第二次采纳把同一模块改成 3 分;模块 PATCH 被注入 500,
        # 整体与历史评论已成功——恢复路径必须发现模块正文还是旧的。
        fake.http_error("PATCH", "/issues/", 500, body_contains="种类:模块规格")
        second = mgs_records.apply_spec_adoption(
            root, _adopt_plan(root, fake, version="v2",
                              rules=["得分：每颗星星 3 分。"],
                              modules={"规则与数值": {
                                  "title": "规则与数值",
                                  "rules": ["每颗星星 3 分。"]}},
                              cache=cache),
            confirmed=True, transport=fake, cache_dir=cache)
        check(second.get("ok") is not True,
              f"模块正文未更新不得报告成功:{second}")
        check(second.get("published") is not True,
              f"模块正文未更新不得标已发布:{second}")
        current = mgs_records.read_current_design(
            root, transport=fake, cache_dir=cache)
        module_bodies = "\n".join(
            str(body) for body in (current.get("modules") or {}).values())
        check("每颗星星 3 分" not in module_bodies,
              "恢复路径不得把旧模块正文当作已采纳的新设计")


def test_r9_2_partial_result_is_not_delivery_complete() -> None:
    """R9-2: 评论已发布而结果索引更新失败时,不得宣告交付完成或验收关闭。"""

    with tempfile.TemporaryDirectory() as tmp:
        root = make_github_project(Path(tmp) / "partial-result")
        fake = FakeTransport()
        cache = root / "docs/mygamestudio/records/cache"
        created = mgs_records.create_task(
            root, "10-deliver", "交付一个可玩构建", {"当前目标": "交付可玩构建", "输入与基线": "GAME_DESIGN v1", "本次交付": "可玩构建", "允许修改范围": "src/**", "所需能力": "文件读写", "完成标准": "可启动", "执行责任": "Agent(制作实现)", "验收方式": "代码级检查"},
            transport=fake, cache_dir=cache)
        check(created.get("published") is not False,
              f"前置:任务应发布成功:{created}")
        number = created.get("issue_number")
        fake.http_error("PATCH", f"/issues/{number}", 500)
        outcome = mgs_records.record_playable_result(
            root, "10-deliver", {
                "status": "delivered", "version": "v1",
                "launch": "npm start", "check_scope": "代码级检查",
            }, transport=fake, cache_dir=cache)
        check(outcome.get("formal_delivery_complete") is not True,
              f"部分成功不得宣告正式交付完成:{outcome}")
        check(outcome.get("close_as_accepted") is not True,
              f"部分成功不得按验收关闭:{outcome}")
        reason = str(outcome.get("reason") or "")
        check("部分成功" in reason or "索引未确认" in reason,
              f"必须说明发布生命周期仍有待恢复缺口:{reason}")


def test_r9_3_set_parent_422_is_failure_not_success() -> None:
    """R9-3: 原生父子关系赋值被 422 拒绝时,不得写正文或虚报原生关系。"""

    with tempfile.TemporaryDirectory() as tmp:
        root = make_github_project(Path(tmp) / "parent-422")
        fake = FakeTransport()
        cache = root / "docs/mygamestudio/records/cache"
        mgs_records.create_task(
            root, "20-parent", "父任务", {"当前目标": "交付可玩构建", "输入与基线": "GAME_DESIGN v1", "本次交付": "可玩构建", "允许修改范围": "src/**", "所需能力": "文件读写", "完成标准": "可启动", "执行责任": "Agent(制作实现)", "验收方式": "代码级检查"}, transport=fake, cache_dir=cache)
        mgs_records.create_task(
            root, "21-child", "子任务", {"当前目标": "交付可玩构建", "输入与基线": "GAME_DESIGN v1", "本次交付": "可玩构建", "允许修改范围": "src/**", "所需能力": "文件读写", "完成标准": "可启动", "执行责任": "Agent(制作实现)", "验收方式": "代码级检查"}, transport=fake, cache_dir=cache)
        fake.http_error("POST", "/sub_issues", 422)
        raised = ""
        try:
            mgs_records.set_parent(
                root, "21-child", "20-parent",
                transport=fake, cache_dir=cache)
        except Exception as exc:  # noqa: BLE001
            raised = str(exc)
        check("422" in raised,
              f"422 校验拒绝必须按失败上报,实际返回:{raised or '无异常'}")
        child_bodies = [item.get("body") or "" for item in fake.issues
                        if "21-child" in (item.get("body") or "")]
        check(all("原生 sub-issue" not in body for body in child_bodies),
              "未落地的原生关系不得写进正文约定")
        check(all("20-parent" not in body.replace("任务身份:", "")
                  or "父任务:#" not in body for body in child_bodies),
              "422 拒绝后不得按成功继续写父任务正文")


def test_r9_4_unknown_material_decision_cannot_escape_roots() -> None:
    """R9-4: 决策里的额外键(根外路径)不得进入采纳或把字节复制到根外。"""

    from test_upstream_upgrade import (
        PINNED_SHA, PINNED_VERSION, _write_candidate, _write_current_plugin)
    import mgs_upstream_upgrade

    with tempfile.TemporaryDirectory(prefix="mgs-r9-") as tmp:
        plugin = _write_current_plugin(Path(tmp) / "plugin")
        extra = {"internal/game/extra-module.md": "# Extra module\n\nUsed when needed.\n"}
        candidate = _write_candidate(Path(tmp) / "candidate", extra_files=extra)
        evaluated = mgs_upstream_upgrade.evaluate_upstream_upgrade(
            plugin, candidate,
            candidate_version=PINNED_VERSION,
            candidate_sha=PINNED_SHA,
            new_material_decisions={
                "internal/game/extra-module.md": "include",
                "../../outside-plugin.txt": "include",
            })
        check(evaluated.get("decision") == "retain",
              f"未枚举的决策键不得进入采纳,实际 {evaluated.get('decision')}")
        check(evaluated.get("retain_reason") == "unknown-material-decision",
              f"应记录 unknown-material-decision,实际 {evaluated.get('retain_reason')}")
        # 评审通过的清单被追加根外键后重放:apply 侧也必须拒绝复制。
        reviewed = mgs_upstream_upgrade.evaluate_upstream_upgrade(
            plugin, candidate,
            candidate_version=PINNED_VERSION,
            candidate_sha=PINNED_SHA,
            new_material_decisions={"internal/game/extra-module.md": "include"})
        check(reviewed.get("decision") == "adopt",
              f"前置:只含枚举键的决策应通过,实际 {reviewed.get('retain_reason')}")
        tampered = dict(reviewed)
        tampered["new_material_decisions"] = {
            "internal/game/extra-module.md": "include",
            "../../outside-plugin.txt": "include",
        }
        mgs_upstream_upgrade.apply_upstream_upgrade(plugin, tampered, confirmed=True)
        check(not (Path(tmp) / "outside-plugin.txt").exists(),
              "apply 不得按根外决策键把字节复制到插件根之外")


def test_r9_5_tampered_pending_tree_is_not_complete() -> None:
    """R9-5: 迁移后被删改的待切换产物不得继续宣告迁移完整。"""

    from test_safe_switch import _convert_local, _write_old_local_project

    with tempfile.TemporaryDirectory() as tmp:
        root = _write_old_local_project(Path(tmp) / "tampered")
        _convert_local(root)
        report = mgs_records.read_local_material_migration(root)
        check(report.get("complete") is True,
              f"前置:未删改的待切换树应完整:{report.get('missing')}")
        pending = Path(report.get("pending_root") or "")
        tasks = sorted(pending.glob("docs/mygamestudio/work/*/task.md"))
        check(bool(tasks), "前置:待切换树应有已转换任务")
        tasks[0].write_text("# 被篡改的正文\n", encoding="utf-8")
        after = mgs_records.read_local_material_migration(root)
        check(after.get("complete") is False,
              "待切换产物被篡改后不得宣告迁移完整")
        missing = [str(item) for item in (after.get("missing") or [])]
        check(any("映射未核实" in item for item in missing),
              f"必须指出未核实的映射行,实际 {missing}")
        plan = mgs_records.plan_safe_switch(root)
        check(plan.get("ready") is not True,
              "产物被篡改后不得放行安全切换")
        tasks[0].unlink()
        deleted = mgs_records.read_local_material_migration(root)
        check(deleted.get("complete") is False,
              "待切换产物被删除后不得宣告迁移完整")


def test_r9_8_assets_are_classified_by_path_without_reading() -> None:
    """R9-8: 工程与资产按路径分类;内容判读只发生在需要的文本文件上。"""

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp) / "asset-game"
        (root / "assets").mkdir(parents=True)
        (root / "assets" / "big-art.pack").write_bytes(bytes(3 * 1024 * 1024))
        (root / "docs" / "mygamestudio").mkdir(parents=True)
        (root / "docs" / "mygamestudio" / "GAME_DESIGN.md").write_text(
            "# 设计\n\n状态:已被替代。旧版设计。\n", encoding="utf-8")
        analysis = mgs_records.analyze_project(root)
        actual = [str(item) for item in (analysis.get("实际行为") or [])]
        check(any("assets/big-art.pack" in item for item in actual),
              f"资产文件应按路径归入实际行为,实际 {actual}")
        history = [str(item) for item in (analysis.get("历史内容") or [])]
        check(any("GAME_DESIGN.md" in item for item in history),
              f"设计文件的内容判读仍应生效,实际 {history}")


def test_r9_9_scoped_migration_cannot_switch_globally() -> None:
    """R9-9: 受限范围只转换部分来源时,不得按完整宣告并放行全局切换。"""

    from test_safe_switch import _write_old_local_project

    with tempfile.TemporaryDirectory() as tmp:
        root = _write_old_local_project(Path(tmp) / "scoped-game")
        plan = mgs_records.plan_local_material_migration(
            root, scope={"sources": ["docs/mygamestudio/GAME_DESIGN.md"]})
        applied = mgs_records.apply_local_material_migration(
            root, plan, confirmed=True)
        check(applied.get("ok") is True, f"前置:受限转换应执行:{applied}")
        report = mgs_records.read_local_material_migration(root)
        check(report.get("complete") is False,
              "受限范围未覆盖全部来源时不得宣告迁移完整")
        missing = [str(item) for item in (report.get("missing") or [])]
        check(any("已转换" in item and "缺少任务对应关系" in item
                  for item in missing),
              f"必须按全量基数指出未转换类别,实际 {missing}")
        switch_plan = mgs_records.plan_safe_switch(root)
        check(switch_plan.get("ready") is not True,
              "受限迁移不得放行项目级全局切换")


def _migrate_and_switch_github(root: Path, fake: FakeTransport) -> dict:
    mgs_records.apply_github_material_migration(
        root, mgs_records.plan_github_material_migration(
            root, transport=fake),
        confirmed=True, transport=fake)
    plan = mgs_records.plan_safe_switch(root, transport=fake)
    check(plan.get("ready") is True, f"前置:完整待切换应可切换:{plan}")
    applied = mgs_records.apply_safe_switch(
        root, plan, confirmed=True, transport=fake)
    check(applied.get("ok") is True, f"前置:切换应成功:{applied}")
    return plan


def test_r9_6_rollback_marks_post_switch_tasks() -> None:
    """R9-6: 回滚时切换后新增的 GitHub 任务也必须打 pending-switch 标记。"""

    from test_github_material_migration import _write_old_github_project

    with tempfile.TemporaryDirectory() as tmp:
        root, fake = _write_old_github_project(Path(tmp) / "rollback-post")
        _migrate_and_switch_github(root, fake)
        created = mgs_records.create_task(
            root, "99-post", "切换后新增的连击反馈", {"当前目标": "交付可玩构建", "输入与基线": "GAME_DESIGN v1", "本次交付": "可玩构建", "允许修改范围": "src/**", "所需能力": "文件读写", "完成标准": "可启动", "执行责任": "Agent(制作实现)", "验收方式": "代码级检查"}, transport=fake)
        check(created.get("published") is not False,
              f"前置:切换后新任务应创建成功:{created}")
        post_number = created.get("issue_number")
        rolled = mgs_records.rollback_safe_switch(
            root, confirmed=True, transport=fake)
        check(rolled.get("ok") is True, f"回滚应成功:{rolled}")
        post_bodies = [item.get("body") or "" for item in fake.issues
                       if item.get("number") == post_number]
        check(post_bodies
              and all("迁移状态:pending-switch" in body
                      for body in post_bodies),
              "切换后新增任务在回滚时必须先退出当前读取集,"
              "否则旧权威恢复后仍与新任务同处现行读取集")
        old_marked = [item.get("body") or "" for item in fake.issues
                      if "迁移状态:readonly-history" not in (item.get("body") or "")
                      and (item.get("body") or "").startswith("# 移动")]
        check(not any("迁移状态:pending-switch" in body for body in old_marked),
              "回滚后旧权威任务不得仍带 pending-switch 标记")


def test_r9_7_duplicate_source_identity_pauses_instead_of_merging() -> None:
    """R9-7: 两个源 Issue 共用任务身份时按冲突暂停,不共享同一目标。"""

    from test_github_material_migration import _write_old_github_project

    with tempfile.TemporaryDirectory() as tmp:
        root, fake = _write_old_github_project(Path(tmp) / "dup-identity")
        fake.seed_issue(
            "01-move", "重复身份的移动任务",
            triage="ready-for-agent", project_label="ready-for-agent")
        applied = mgs_records.apply_github_material_migration(
            root, mgs_records.plan_github_material_migration(
                root, transport=fake),
            confirmed=True, transport=fake)
        paused = [str(item) for item in (applied.get("paused") or [])]
        check(any("源身份碰撞" in item and "01-move" in item for item in paused),
              f"重复源身份必须按冲突暂停,实际 {paused}")
        pending_bodies = [item.get("body") or "" for item in fake.issues
                          if "任务身份:01-move" in (item.get("body") or "")
                          and "迁移状态:pending-switch" in (item.get("body") or "")]
        check(not pending_bodies,
              "碰撞身份不得建出共享的待切换目标 Issue")
        tasks_rows = ((applied.get("correspondence") or {}).get("tasks") or [])
        check(not [row for row in tasks_rows
                   if str(row.get("identity") or "") == "01-move"],
              "碰撞身份不得进入已转换任务对应关系")
        report = mgs_records.read_github_material_migration(
            root, transport=fake)
        check(report.get("complete") is False,
              "存在冲突暂停时不得宣告迁移完整")


def test_r9_10_switch_and_rollback_recheck_current_authorization() -> None:
    """R9-10: 迁移准备后的 issues-write 授权被收回时,切换与回退失败闭合。"""

    from test_github_material_migration import _write_old_github_project

    with tempfile.TemporaryDirectory() as tmp:
        root, fake = _write_old_github_project(Path(tmp) / "auth-recheck")
        mgs_records.apply_github_material_migration(
            root, mgs_records.plan_github_material_migration(
                root, transport=fake),
            confirmed=True, transport=fake)
        config_path = root / "docs/mygamestudio/CONFIG.md"
        original_config = config_path.read_text(encoding="utf-8")
        config_path.write_text(
            original_config.replace(":issues-write", ":issues-read"),
            encoding="utf-8")
        before = len(fake.calls)
        denied = mgs_records.apply_safe_switch(root, confirmed=True,
                                               transport=fake)
        check(denied.get("ok") is False,
              f"授权缺失时不得执行远端标记变更:{denied}")
        reason = str(denied.get("reason") or "")
        check("issues-write" in reason,
              f"必须说明是当前授权缺失:{reason}")
        patches = [call for call in fake.calls[before:]
                   if call[0] == "PATCH" and "/issues" in call[1]]
        check(not patches, "授权缺失时不得发出任何 issue PATCH")
        config_path.write_text(original_config, encoding="utf-8")
        _migrate_recheck = mgs_records.apply_safe_switch(
            root, confirmed=True, transport=fake)
        check(_migrate_recheck.get("ok") is True,
              f"前置:授权恢复后切换应成功:{_migrate_recheck}")
        config_path.write_text(
            original_config.replace(":issues-write", ":issues-read"),
            encoding="utf-8")
        before_rollback = len(fake.calls)
        denied_rollback = mgs_records.rollback_safe_switch(
            root, confirmed=True, transport=fake)
        check(denied_rollback.get("ok") is False,
              f"授权缺失时不得执行远端标记回退:{denied_rollback}")
        check(denied_rollback.get("status") == "switched",
              "拒绝回退时必须保持已切换状态")
        rollback_patches = [call for call in fake.calls[before_rollback:]
                            if call[0] == "PATCH" and "/issues" in call[1]]
        check(not rollback_patches, "授权缺失时回退不得发出任何 issue PATCH")


if __name__ == "__main__":
    raise SystemExit(run_theme(
        "PR #67 R9 复审修复回归",
        (
            test_r9_1_recovery_compares_module_bodies,
            test_r9_2_partial_result_is_not_delivery_complete,
            test_r9_3_set_parent_422_is_failure_not_success,
            test_r9_4_unknown_material_decision_cannot_escape_roots,
            test_r9_5_tampered_pending_tree_is_not_complete,
            test_r9_6_rollback_marks_post_switch_tasks,
            test_r9_7_duplicate_source_identity_pauses_instead_of_merging,
            test_r9_8_assets_are_classified_by_path_without_reading,
            test_r9_9_scoped_migration_cannot_switch_globally,
            test_r9_10_switch_and_rollback_recheck_current_authorization,
        ),
        FAILURES))

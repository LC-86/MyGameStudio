#!/usr/bin/env python3
"""Issue #54 seams: formal-version design snapshots.

Confirmed seams (issue #54 acceptance + #49 T6/T7):
- AC1/T6: a version-freeze or explicit request archives complete overall and
  module content plus fixed-version attachments; the overall design entry can
  locate each version; daily edits do not force a snapshot.
- AC2/T6: records game version, design id, revision, time and source; links
  existing build/release records; several game versions may reuse one design
  snapshot; unimplemented or unpublished status is stated honestly.
- AC3/T6: updating current design does not change an old snapshot; a correction
  stores a new revision and keeps the old content, reason and adoption; no
  second live design is created.
- AC4: GitHub archive Issues and local archive documents each hold the full
  content of that moment; a mutable current-spec link or a change summary is
  not a complete snapshot.
- AC5/T7: source change, missing module/attachment, partial write or unknown
  result must not claim a complete archive; reread fills gaps only and must
  not duplicate snapshots or overwrite an old revision. No new human
  acceptance, immutability or automatic-backup claim.

Expected values come from issues #54 and #49 D5/D6/D8, not internals.
Do not assert internal functions, directory counts, or prompt keywords.

    python3 -B tests/test_design_version_snapshot.py
"""

from __future__ import annotations

import hashlib
import tempfile
from pathlib import Path

from github_backend_fixtures import AUTH, REPO, make_checker, run_theme
from github_backend_transport import FakeTransport

import mgs_records  # noqa: E402

FAILURES, check = make_checker()


CORE_DESIGN = """# star-catcher：当前游戏需求与设计

维护责任：方案设计。基线版本：v1。适用范围：最小闭环。采用依据：开发者决定。

规格身份:overall。种类:现行规格。版本:v1。

## 核心玩法

玩家移动角色接住落下的星星。接到一颗得 1 分。漏接三颗结束本局。

## 当前规则与流程

- 得分：每颗星星 1 分。
- 结束：漏接 3 颗后本局结束。
- 操作：方向键左右移动。

## 模块

- 规则与数值：docs/mygamestudio/design/rules.md

## 变更索引

- v1：采纳最小闭环。来源：开发者。理由：先做出可玩循环。
"""

MODULE_RULES = """# 规则与数值

规格身份:rules。种类:模块规格。版本:v1。

## 当前规则与流程

- 得分：每颗星星 1 分。
- 结束：漏接 3 颗后本局结束。
"""

CHART = "接星循环：落下 → 移动 → 接到 +1 / 漏接计数。\n"


def _task_request(goal: str) -> dict:
    return {
        "当前目标": goal,
        "输入与基线": "GAME_DESIGN.md v1",
        "本次交付": "可回读的任务记录",
        "允许修改范围": "src/**",
        "所需能力": "文件读写",
        "完成标准": "记录可回读",
        "执行责任": "Agent(制作实现)",
        "验收方式": "代码级检查",
        "依赖": "无",
    }


def _onboard_local(root: Path) -> Path:
    root.mkdir(parents=True, exist_ok=True)
    (root / "README.md").write_text("# star-catcher\n\n接星星。\n", encoding="utf-8")
    mgs_records.apply_local_onboarding(
        root, mgs_records.plan_local_onboarding(root), confirmed=True)
    design = root / "docs/mygamestudio/GAME_DESIGN.md"
    design.parent.mkdir(parents=True, exist_ok=True)
    design.write_text(CORE_DESIGN, encoding="utf-8")
    module = root / "docs/mygamestudio/design/rules.md"
    module.parent.mkdir(parents=True, exist_ok=True)
    module.write_text(MODULE_RULES, encoding="utf-8")
    chart = root / "docs/mygamestudio/design/loop-chart.md"
    chart.write_text(CHART, encoding="utf-8")
    mgs_records.create_task(
        root, "01-catch-star", "接住第一颗星星",
        _task_request("接住一颗星星并计分"))
    return root


def test_version_freeze_archives_full_content_daily_does_not() -> None:
    """AC1/T6: 正式版本设计确定时保存完整整体与模块及固定附件;
    整体设计入口可定位该版本;日常修改不强制生成。
    """

    with tempfile.TemporaryDirectory() as tmp:
        root = _onboard_local(Path(tmp) / "star-catcher")
        daily = mgs_records.plan_design_snapshot(root, {
            "trigger": "daily_change",
            "game_version": "0.1.0",
        })
        check(daily.get("should_snapshot") is False,
              "日常修改不得强制生成快照")
        check(daily.get("wrote") is not True,
              "日常计划不得写入归档")
        applied_daily = mgs_records.apply_design_snapshot(root, daily)
        check(applied_daily.get("ok") is not True or applied_daily.get("wrote") is False,
              "日常修改路径不得宣称已归档")

        plan = mgs_records.plan_design_snapshot(root, {
            "trigger": "version_freeze",
            "game_version": "0.1.0",
            "source": "正式版本设计确定",
            "attachments": ["docs/mygamestudio/design/loop-chart.md"],
        })
        check(plan.get("should_snapshot") is True,
              "正式版本设计确定必须生成快照计划")
        check(plan.get("gate_required") is False,
              "普通快照路径不得要求 mgs-gate")
        applied = mgs_records.apply_design_snapshot(root, plan, confirmed=True)
        check(applied.get("ok") is True, f"正式快照应完整保存:{applied}")
        check(applied.get("complete") is True, "完整归档必须标明 complete")
        check(applied.get("gate_required") is False, "归档成功不得依赖 gate")

        listed = mgs_records.read_design_snapshots(root)
        snaps = listed.get("snapshots") or []
        check(len(snaps) == 1, f"版本冻结应恰好一份快照,实际 {len(snaps)}")
        snap = snaps[0]
        overall = snap.get("overall") or ""
        check("接到一颗得 1 分" in overall, "快照必须保存当时完整整体设计")
        check("docs/mygamestudio/GAME_DESIGN.md" not in overall
              or "接到一颗得 1 分" in overall,
              "不得只用现行规格可变链接冒充当时内容")
        modules = snap.get("modules") or {}
        check(any("每颗星星 1 分" in body for body in modules.values()),
              "快照必须保存当时模块完整内容")
        attachments = snap.get("attachments") or {}
        check(any(CHART.strip() in body for body in attachments.values()),
              "固定版本附件必须可达且含当时内容")

        current = mgs_records.read_current_design(root)
        entry = current.get("overall") or ""
        design_id = snap.get("design_id") or applied.get("design_id")
        revision = snap.get("revision") or applied.get("revision")
        check(design_id and str(design_id) in entry,
              "整体设计入口必须能定位该设计快照")
        check(revision and str(revision) in entry,
              "整体设计入口必须能定位该修订")
        check("0.1.0" in entry, "整体设计入口必须能定位对应游戏版本")


def test_records_identity_and_reuses_across_game_versions() -> None:
    """AC2/T6: 记录游戏版本、设计标识、修订、时间和来源;
    关联已有构建或发布;多游戏版本可复用同一设计;未实现或未发布如实标注。
    """

    with tempfile.TemporaryDirectory() as tmp:
        root = _onboard_local(Path(tmp) / "star-catcher")
        first = mgs_records.apply_design_snapshot(root, mgs_records.plan_design_snapshot(root, {
            "trigger": "version_freeze",
            "game_version": "0.1.0",
            "source": "正式版本设计确定",
            "attachments": ["docs/mygamestudio/design/loop-chart.md"],
        }), confirmed=True)
        check(first.get("ok") is True, f"首份快照应完整:{first}")
        listed = mgs_records.read_design_snapshots(root)
        snap = (listed.get("snapshots") or [None])[0]
        check(snap, "必须能读回已保存快照")
        check(snap.get("design_id"), "必须记录设计标识")
        check(snap.get("revision") == "r1", f"首份修订应为 r1,实际 {snap.get('revision')}")
        check("0.1.0" in (snap.get("game_versions") or []),
              "必须记录对应游戏版本")
        check(snap.get("formed_at"), "必须记录形成时间")
        check("正式版本设计确定" in (snap.get("source") or ""),
              "必须记录来源")
        check(snap.get("implementation") == "未实现",
              "尚未实现时必须如实标注未实现")
        check(snap.get("release") == "未发布",
              "尚未发布时必须如实标注未发布")

        build = root / "docs/mygamestudio/work/01-catch-star/results/build.md"
        build.parent.mkdir(parents=True, exist_ok=True)
        build.write_text("构建:dev-12。已在编辑器运行接星循环。\n", encoding="utf-8")
        reuse = mgs_records.apply_design_snapshot(root, mgs_records.plan_design_snapshot(root, {
            "trigger": "version_freeze",
            "game_version": "0.2.0",
            "reuse_design_id": snap.get("design_id"),
            "build_record": "docs/mygamestudio/work/01-catch-star/results/build.md",
            "release": "未发布",
        }), confirmed=True)
        check(reuse.get("ok") is True, f"复用已有设计快照应成功:{reuse}")
        check(reuse.get("reuse") is True, "多游戏版本必须复用同一设计快照")
        after = mgs_records.read_design_snapshots(root)
        snaps = after.get("snapshots") or []
        check(len(snaps) == 1, f"复用不得另存第二份设计快照,实际 {len(snaps)}")
        reused = snaps[0]
        versions = reused.get("game_versions") or []
        check("0.1.0" in versions and "0.2.0" in versions,
              f"两个游戏版本都应关联同一设计:{versions}")
        check("build.md" in (reused.get("implementation") or ""),
              "已有构建记录必须关联,不得虚报未实现")
        check(reused.get("release") == "未发布",
              "0.2.0 尚未发布必须如实标注")
        current = mgs_records.read_current_design(root)
        entry = current.get("overall") or ""
        check("0.2.0" in entry, "整体入口必须能定位复用后的游戏版本")
        check("不可篡改" not in (reused.get("meta") or "")
              or "不宣称不可篡改" in (reused.get("meta") or ""),
              "不得承诺不可篡改或自动备份")


def test_current_design_change_keeps_old_snapshot_correction_is_new_revision() -> None:
    """AC3/T6: 当前设计修改不影响旧快照;修正另存新修订并保留旧内容、
    原因和采用关系;不建立第二套现行设计。
    """

    with tempfile.TemporaryDirectory() as tmp:
        root = _onboard_local(Path(tmp) / "star-catcher")
        first = mgs_records.apply_design_snapshot(root, mgs_records.plan_design_snapshot(root, {
            "trigger": "version_freeze",
            "game_version": "0.1.0",
            "source": "正式版本设计确定",
            "attachments": ["docs/mygamestudio/design/loop-chart.md"],
        }), confirmed=True)
        design_id = first.get("design_id")
        old = mgs_records.read_design_snapshots(root)
        old_overall = (old.get("snapshots") or [{}])[0].get("overall") or ""
        check("每颗星星 1 分" in old_overall, "冻结时快照应含当时规则")

        plan = mgs_records.plan_spec_adoption(root, {
            "kind": "small_change",
            "source": "开发者主动 to-spec",
            "reason": "正式改为 3 分",
            "replaces": "每颗星星 1 分",
            "overall": {
                "title": "star-catcher：当前游戏需求与设计",
                "version": "v2",
                "core_play": "玩家移动角色接住落下的星星。接到一颗得 3 分。漏接三颗结束本局。",
                "rules": ["得分：每颗星星 3 分。"],
                "replace_rules": ["每颗星星 1 分"],
            },
        })
        mgs_records.apply_spec_adoption(root, plan, confirmed=True)
        current = mgs_records.read_current_design(root)
        check("每颗星星 3 分" in (current.get("overall") or ""),
              "现行规格应更新为新规则")
        listed = mgs_records.read_design_snapshots(root)
        frozen = (listed.get("snapshots") or [{}])[0]
        check("每颗星星 1 分" in (frozen.get("overall") or ""),
              "更新现行设计不得改写旧快照")
        check("每颗星星 3 分" not in (frozen.get("overall") or ""),
              "旧快照不得吸入后续现行修改")
        check(design_id and str(design_id) in (current.get("overall") or ""),
              "现行规格更新后整体入口仍须能定位旧快照")

        corrected = mgs_records.apply_design_snapshot(root, mgs_records.plan_design_snapshot(root, {
            "trigger": "explicit",
            "game_version": "0.1.0",
            "design_id": design_id,
            "correction": True,
            "reason": "补入漏记的结束条件",
            "replaces_revision": "r1",
            "source": "归档修正",
        }), confirmed=True)
        check(corrected.get("ok") is True, f"修正应另存新修订:{corrected}")
        check(corrected.get("revision") != "r1",
              "修正必须是新修订,不得覆盖 r1")
        after = mgs_records.read_design_snapshots(root)
        revs = {item.get("revision"): item for item in (after.get("snapshots") or [])
                if item.get("design_id") == design_id}
        check("r1" in revs, "旧修订必须继续可读")
        check(len(revs) >= 2, f"修正后应保留新旧修订,实际 {sorted(revs)}")
        check("每颗星星 1 分" in (revs["r1"].get("overall") or ""),
              "旧修订必须保留当时内容")
        new_rev = corrected.get("revision")
        check(new_rev in revs, "新修订必须可读")
        check("补入漏记的结束条件" in (revs[new_rev].get("reason") or ""),
              "新修订必须记录修正原因")
        check("r1" in (revs[new_rev].get("replaces") or ""),
              "新修订必须记录对旧修订的采用关系")
        live = list((root / "docs/mygamestudio").glob("GAME_DESIGN*.md"))
        check(len(live) == 1, f"不得建立第二套现行设计文件,实际 {live}")
        check("种类:现行规格" in (mgs_records.read_current_design(root).get("overall") or "")
              or "当前游戏需求与设计" in (mgs_records.read_current_design(root).get("overall") or ""),
              "现行设计仍只在原整体入口维护")


def _onboard_github(root: Path) -> Path:
    root.mkdir(parents=True, exist_ok=True)
    (root / "README.md").write_text("# star-catcher\n", encoding="utf-8")
    mgs_records.apply_github_onboarding(
        root, mgs_records.plan_github_onboarding(
            root, repo=REPO, authorization=AUTH),
        confirmed=True)
    chart = root / "docs/mygamestudio/design/loop-chart.md"
    chart.parent.mkdir(parents=True, exist_ok=True)
    chart.write_text(CHART, encoding="utf-8")
    return root


def test_github_archive_issue_holds_full_content_not_a_live_link() -> None:
    """AC4: GitHub 归档 Issue 与本地归档文档分别保存当时完整内容;
    不以可变现行链接或变更摘要冒充完整快照。快照 Issue 不进入任务列表。
    """

    with tempfile.TemporaryDirectory() as tmp:
        root = _onboard_github(Path(tmp) / "star-catcher")
        fake = FakeTransport()
        cache = root / "docs/mygamestudio/records/cache"
        local_design = root / "docs/mygamestudio/GAME_DESIGN.md"
        local_design.parent.mkdir(parents=True, exist_ok=True)
        local_design.write_text("# 本地不是现行\n\n变更摘要：准备改分。\n", encoding="utf-8")
        local_sha = hashlib.sha256(local_design.read_bytes()).hexdigest()
        adopted = mgs_records.plan_spec_adoption(root, {
            "kind": "new_feature",
            "source": "开发者主动 to-spec",
            "reason": "冻结 0.1 设计",
            "overall": {
                "title": "star-catcher 整体设计",
                "version": "v1",
                "core_play": "接星星。接到一颗得 1 分。漏接三颗结束。",
                "rules": [
                    "得分：每颗星星 1 分。",
                    "结束：漏接 3 颗后本局结束。",
                ],
            },
            "modules": {
                "规则与数值": {"title": "规则与数值", "rules": ["每颗星星 1 分。"]},
            },
        }, transport=fake, cache_dir=cache)
        mgs_records.apply_spec_adoption(
            root, adopted, confirmed=True, transport=fake, cache_dir=cache)
        plan = mgs_records.plan_design_snapshot(root, {
            "trigger": "version_freeze",
            "game_version": "0.1.0",
            "source": "正式版本设计确定",
            "attachments": ["docs/mygamestudio/design/loop-chart.md"],
        }, transport=fake, cache_dir=cache)
        applied = mgs_records.apply_design_snapshot(
            root, plan, confirmed=True, transport=fake, cache_dir=cache)
        check(applied.get("ok") is True, f"GitHub 归档应完整:{applied}")
        check(applied.get("complete") is True, "GitHub 完整路径必须宣称 complete 仅在内容齐全时")
        check(applied.get("backend") == "github-issues",
              "GitHub 项目必须走归档 Issue,不得改用本地 tracker")
        listed = mgs_records.read_design_snapshots(
            root, transport=fake, cache_dir=cache)
        snaps = listed.get("snapshots") or []
        check(len(snaps) == 1, f"GitHub 应恰好一份归档快照,实际 {len(snaps)}")
        snap = snaps[0]
        check("每颗星星 1 分" in (snap.get("overall") or ""),
              "归档 Issue 必须含当时完整整体设计")
        check(any("每颗星星 1 分" in body for body in (snap.get("modules") or {}).values()),
              "归档 Issue 必须含当时模块完整内容")
        check(any(CHART.strip() in body for body in (snap.get("attachments") or {}).values()),
              "归档 Issue 必须含固定版本附件内容")
        current = mgs_records.read_current_design(
            root, transport=fake, cache_dir=cache)
        overall = current.get("overall") or ""
        check(str(snap.get("design_id")) in overall,
              "GitHub 整体设计入口必须能定位各版本快照")
        check("归档 Issue" in overall or "#" in overall,
              "整体入口须指向归档 Issue,而不是现行规格自身链接冒充")
        archives = [item for item in fake.issues
                    if "快照身份:" in (item.get("body") or "")]
        check(len(archives) == 1, f"应有一份归档 Issue,实际 {len(archives)}")
        archive_body = archives[0].get("body") or ""
        check("每颗星星 1 分" in archive_body, "归档正文必须是当时完整内容")
        check("变更摘要" not in archive_body,
              "不得用变更摘要冒充当时完整内容")
        tasks = mgs_records.list_tasks(root, transport=fake, cache_dir=cache)
        check(all("快照身份:" not in (item.get("body") or "") for item in tasks),
              "归档快照 Issue 不得进入任务列表")
        identities = [item.get("identity") for item in tasks]
        check(all(item for item in identities),
              "快照 Issue 不得被解析成任务身份")
        check(hashlib.sha256(local_design.read_bytes()).hexdigest() == local_sha,
              "GitHub 归档不得把本地 GAME_DESIGN.md 改成第二套现行设计")
        corrected = mgs_records.apply_design_snapshot(root, mgs_records.plan_design_snapshot(root, {
            "trigger": "explicit",
            "game_version": "0.1.0",
            "design_id": snap.get("design_id"),
            "correction": True,
            "reason": "补入漏记的结束条件",
            "replaces_revision": "r1",
            "source": "归档修正",
            "attachments": ["docs/mygamestudio/design/loop-chart.md"],
        }, transport=fake, cache_dir=cache), confirmed=True, transport=fake, cache_dir=cache)
        check(corrected.get("ok") is True, f"GitHub 修正应另存新修订:{corrected}")
        after = mgs_records.read_design_snapshots(
            root, transport=fake, cache_dir=cache)
        revs = {item.get("revision"): item for item in (after.get("snapshots") or [])
                if item.get("design_id") == snap.get("design_id")}
        check("r1" in revs and len(revs) >= 2, "GitHub 旧修订必须保留且新修订另存")
        check("每颗星星 1 分" in (revs["r1"].get("overall") or ""),
              "GitHub 旧修订正文不得被覆盖")
        archives = [item for item in fake.issues
                    if "快照身份:" in (item.get("body") or "")]
        check(len(archives) == 2, f"GitHub 修正应新增归档 Issue,实际 {len(archives)}")


def test_github_snapshot_keeps_inner_markdown_fences() -> None:
    """AC4: 整体设计内嵌代码围栏时,归档读取必须拿到当时完整内容。"""

    inner = '```json\n{"score": 1, "lives": 3}\n```'
    with tempfile.TemporaryDirectory() as tmp:
        root = _onboard_github(Path(tmp) / "star-catcher")
        fake = FakeTransport()
        cache = root / "docs/mygamestudio/records/cache"
        adopted = mgs_records.plan_spec_adoption(root, {
            "kind": "new_feature",
            "source": "开发者主动 to-spec",
            "reason": "冻结含示例块的设计",
            "overall": {
                "title": "star-catcher 整体设计",
                "version": "v1",
                "core_play": f"接星星。计分结构如下：\n\n{inner}\n漏接三颗结束。",
                "rules": ["得分：每颗星星 1 分。"],
            },
            "modules": {
                "规则与数值": {
                    "title": "规则与数值",
                    "rules": [f"计分结构：\n{inner}"],
                },
            },
        }, transport=fake, cache_dir=cache)
        mgs_records.apply_spec_adoption(
            root, adopted, confirmed=True, transport=fake, cache_dir=cache)
        plan = mgs_records.plan_design_snapshot(root, {
            "trigger": "version_freeze",
            "game_version": "0.1.0",
            "source": "正式版本设计确定",
        }, transport=fake, cache_dir=cache)
        applied = mgs_records.apply_design_snapshot(
            root, plan, confirmed=True, transport=fake, cache_dir=cache)
        check(applied.get("ok") is True and applied.get("complete") is True,
              f"含内嵌围栏的归档应完整:{applied}")
        listed = mgs_records.read_design_snapshots(
            root, transport=fake, cache_dir=cache)
        snap = (listed.get("snapshots") or [{}])[0]
        overall = snap.get("overall") or ""
        check('"score": 1' in overall and '"lives": 3' in overall,
              "归档读取不得在内嵌围栏处截断整体设计")
        check("漏接三颗结束" in overall,
              "内嵌围栏之后的正文必须仍在归档整体设计中")


def test_interrupt_and_source_change_do_not_claim_complete_archive() -> None:
    """AC5/T7: 来源中途改变、缺模块或附件、部分保存、响应丢失及重试时,
    未完整不宣称成功;重读只补缺项,不重复快照或覆盖旧修订。
    不新增人工验收、不可篡改或自动备份承诺。
    """

    with tempfile.TemporaryDirectory() as tmp:
        root = _onboard_local(Path(tmp) / "star-catcher")
        plan = mgs_records.plan_design_snapshot(root, {
            "trigger": "version_freeze",
            "game_version": "0.1.0",
            "source": "正式版本设计确定",
            "attachments": ["docs/mygamestudio/design/loop-chart.md"],
        })
        design = root / "docs/mygamestudio/GAME_DESIGN.md"
        design.write_text(
            design.read_text(encoding="utf-8").replace("1 分", "9 分"),
            encoding="utf-8")
        changed = mgs_records.apply_design_snapshot(root, plan, confirmed=True)
        check(changed.get("complete") is not True,
              "来源中途改变不得宣称完整归档")
        check(changed.get("ok") is not True,
              "混合修订不得报告成功")
        design.write_text(CORE_DESIGN, encoding="utf-8")
        (root / "docs/mygamestudio/design/rules.md").write_text(
            MODULE_RULES, encoding="utf-8")

        missing_att = mgs_records.apply_design_snapshot(root, {
            **mgs_records.plan_design_snapshot(root, {
                "trigger": "explicit",
                "game_version": "0.1.0",
                "source": "开发者明确要求",
                "attachments": ["docs/mygamestudio/design/missing-chart.md"],
            }),
        }, confirmed=True)
        check(missing_att.get("complete") is not True,
              "缺附件不得宣称完整归档")
        check(missing_att.get("ok") is not True, "缺附件不得报告成功")

        module_dir = root / "docs/mygamestudio/design/rules.md"
        module_dir.unlink()
        missing_mod = mgs_records.apply_design_snapshot(root, {
            **mgs_records.plan_design_snapshot(root, {
                "trigger": "explicit",
                "game_version": "0.1.0",
                "source": "开发者明确要求",
            }),
        }, confirmed=True)
        check(missing_mod.get("complete") is not True,
              "缺模块不得宣称完整归档")
        (root / "docs/mygamestudio/design/rules.md").write_text(
            MODULE_RULES, encoding="utf-8")

        first = mgs_records.apply_design_snapshot(root, mgs_records.plan_design_snapshot(root, {
            "trigger": "version_freeze",
            "game_version": "0.1.0",
            "source": "正式版本设计确定",
            "attachments": ["docs/mygamestudio/design/loop-chart.md"],
        }), confirmed=True)
        check(first.get("complete") is True, f"来源与附件齐全时应完整:{first}")
        check("人工验收" not in str(first),
              "不得新增人工验收承诺")
        check(first.get("immutable") not in (True, "不可篡改"),
              "不得承诺不可篡改")
        check(first.get("auto_backup") not in (True, "自动备份"),
              "不得承诺自动备份")
        design_id = first.get("design_id")
        listed = mgs_records.read_design_snapshots(root)
        frozen = next(item for item in (listed.get("snapshots") or [])
                      if item.get("design_id") == design_id)
        old_overall = frozen.get("overall")
        retry_same = mgs_records.apply_design_snapshot(root, mgs_records.plan_design_snapshot(root, {
            "trigger": "version_freeze",
            "game_version": "0.1.0",
            "design_id": design_id,
            "source": "正式版本设计确定",
            "attachments": ["docs/mygamestudio/design/loop-chart.md"],
        }), confirmed=True)
        check(retry_same.get("complete") is True, f"重试应补缺或确认已有修订:{retry_same}")
        listed = mgs_records.read_design_snapshots(root)
        same_id = [item for item in (listed.get("snapshots") or [])
                   if item.get("design_id") == design_id]
        check(len(same_id) == 1, f"重试不得重复生成快照修订,实际 {len(same_id)}")
        check(same_id[0].get("overall") == old_overall,
              "重试不得覆盖已有修订正文")

        gh_root = _onboard_github(Path(tmp) / "gh-star")
        fake = FakeTransport()
        cache = gh_root / "docs/mygamestudio/records/cache"
        spec_plan = mgs_records.plan_spec_adoption(gh_root, {
            "kind": "new_feature",
            "source": "开发者主动 to-spec",
            "overall": {
                "title": "gh 整体设计",
                "version": "v1",
                "core_play": "接星星。",
                "rules": ["得分：每颗星星 1 分。"],
            },
            "modules": {
                "规则与数值": {"title": "规则与数值", "rules": ["每颗星星 1 分。"]},
            },
        }, transport=fake, cache_dir=cache)
        spec_applied = mgs_records.apply_spec_adoption(
            gh_root, spec_plan, confirmed=True, transport=fake, cache_dir=cache)
        overall_no = spec_applied.get("overall_issue")
        snap_plan = mgs_records.plan_design_snapshot(gh_root, {
            "trigger": "explicit",
            "game_version": "0.1.0",
            "source": "开发者明确要求",
            "attachments": ["docs/mygamestudio/design/loop-chart.md"],
        }, transport=fake, cache_dir=cache)
        fake.fail("PATCH", f"/issues/{overall_no}", "timeout")
        partial = mgs_records.apply_design_snapshot(
            gh_root, snap_plan, confirmed=True, transport=fake, cache_dir=cache)
        check(partial.get("complete") is not True,
              f"索引部分保存不得宣称完整归档:{partial}")
        archives = [item for item in fake.issues
                    if "快照身份:" in (item.get("body") or "")]
        check(len(archives) == 1, f"部分写入后应留下一份归档,实际 {len(archives)}")
        fake._fail.clear()
        again = mgs_records.apply_design_snapshot(
            gh_root, snap_plan, confirmed=True, transport=fake, cache_dir=cache)
        check(again.get("complete") is True, f"重读后只补缺项应完整:{again}")
        check(again.get("filled_gap_only") is True
              or len([item for item in fake.issues
                      if "快照身份:" in (item.get("body") or "")]) == 1,
              "重读后不得再创建一份快照")
        archives_after = [item for item in fake.issues
                          if "快照身份:" in (item.get("body") or "")]
        check(len(archives_after) == 1,
              f"补缺不得重复创建归档 Issue,实际 {len(archives_after)}")
        check(archives_after[0].get("body") == archives[0].get("body"),
              "补缺不得覆盖已有修订正文")


def test_interrupted_snapshot_does_not_mix_source_revisions() -> None:
    """D6: 中断恢复不得用当前模块补旧整体,也不得在缺形成时间时宣称完整。"""

    with tempfile.TemporaryDirectory() as tmp:
        root = _onboard_local(Path(tmp) / "star-catcher")
        plan = mgs_records.plan_design_snapshot(root, {
            "trigger": "version_freeze",
            "game_version": "0.1.0",
            "source": "正式版本设计确定",
            "attachments": ["docs/mygamestudio/design/loop-chart.md"],
        })
        design_id = plan.get("design_id") or "ds-1"
        revision = plan.get("revision") or "r1"
        rev_dir = root / "docs/mygamestudio/records/design-snapshots" / design_id / revision
        rev_dir.mkdir(parents=True, exist_ok=True)
        (rev_dir / "overall.md").write_text(
            mgs_records.read_current_design(root).get("overall") or "",
            encoding="utf-8")
        (root / "docs/mygamestudio/design/rules.md").write_text(
            MODULE_RULES.replace("1 分", "99 分"),
            encoding="utf-8")
        resumed = mgs_records.apply_design_snapshot(root, plan, confirmed=True)
        check(resumed.get("complete") is not True,
              "中断恢复不得把旧整体与新模块拼成完整快照")
        check(resumed.get("ok") is not True,
              "混合修订不得报告成功")
        listed = mgs_records.read_design_snapshots(root)
        snaps = [item for item in (listed.get("snapshots") or [])
                 if item.get("design_id") == design_id]
        if snaps:
            overall = snaps[0].get("overall") or ""
            modules = "\n".join((snaps[0].get("modules") or {}).values())
            mixed = "1 分" in overall and "99 分" in modules
            check(not mixed, "归档不得同时含旧整体 1 分和新模块 99 分")
            check(snaps[0].get("formed_at"),
                  "宣称完整前必须有形成时间") if resumed.get("complete") else None


def test_same_basename_attachments_keep_distinct_paths() -> None:
    """同名附件必须按相对路径分别保存,不得互相覆盖后仍宣称完整。"""

    with tempfile.TemporaryDirectory() as tmp:
        root = _onboard_local(Path(tmp) / "star-catcher")
        art = root / "docs/mygamestudio/design/art/config.md"
        levels = root / "docs/mygamestudio/design/levels/config.md"
        art.parent.mkdir(parents=True, exist_ok=True)
        levels.parent.mkdir(parents=True, exist_ok=True)
        art.write_text("美术配置\n", encoding="utf-8")
        levels.write_text("关卡配置\n", encoding="utf-8")
        applied = mgs_records.apply_design_snapshot(root, mgs_records.plan_design_snapshot(root, {
            "trigger": "version_freeze",
            "game_version": "0.1.0",
            "source": "正式版本设计确定",
            "attachments": [
                "docs/mygamestudio/design/art/config.md",
                "docs/mygamestudio/design/levels/config.md",
            ],
        }), confirmed=True)
        check(applied.get("ok") is True and applied.get("complete") is True,
              f"不碰撞的附件应完整归档:{applied}")
        listed = mgs_records.read_design_snapshots(root)
        attachments = (listed.get("snapshots") or [{}])[0].get("attachments") or {}
        blob = "\n".join(attachments.values()) if isinstance(attachments, dict) else str(attachments)
        names = " ".join(attachments.keys()) if isinstance(attachments, dict) else str(attachments)
        check("美术配置" in blob, "美术附件内容必须保留")
        check("关卡配置" in blob, "关卡附件内容必须保留,不得被同名文件覆盖")
        check("art" in names and "levels" in names,
              f"附件必须保留相对路径以区分同名文件,实际 {names}")


def test_correction_revision_uses_highest_existing_number() -> None:
    """修正修订必须取现有 rN 的最大值加一,不得覆盖中间缺口中的已占用修订。"""

    with tempfile.TemporaryDirectory() as tmp:
        root = _onboard_local(Path(tmp) / "star-catcher")
        first = mgs_records.apply_design_snapshot(root, mgs_records.plan_design_snapshot(root, {
            "trigger": "version_freeze",
            "game_version": "0.1.0",
            "source": "正式版本设计确定",
            "attachments": ["docs/mygamestudio/design/loop-chart.md"],
        }), confirmed=True)
        design_id = first.get("design_id")
        r3 = (root / "docs/mygamestudio/records/design-snapshots"
              / str(design_id) / "r3")
        r3.mkdir(parents=True, exist_ok=True)
        (r3 / "overall.md").write_text("已占用的 r3 正文\n", encoding="utf-8")
        (r3 / "meta.md").write_text(
            f"快照身份:{design_id}。修订:r3。形成时间:2026-09-01。\n",
            encoding="utf-8")
        plan = mgs_records.plan_spec_adoption(root, {
            "kind": "small_change",
            "source": "开发者主动 to-spec",
            "reason": "正式改为 3 分",
            "overall": {
                "title": "star-catcher：当前游戏需求与设计",
                "version": "v2",
                "core_play": "接到一颗得 3 分。",
                "rules": ["得分：每颗星星 3 分。"],
            },
        })
        mgs_records.apply_spec_adoption(root, plan, confirmed=True)
        corrected_plan = mgs_records.plan_design_snapshot(root, {
            "trigger": "explicit",
            "correction": True,
            "design_id": design_id,
            "game_version": "0.1.1",
            "source": "修正快照",
            "reason": "补记录形成时间",
            "attachments": ["docs/mygamestudio/design/loop-chart.md"],
        })
        check(corrected_plan.get("revision") != "r3",
              f"有 r1 与 r3 时修正不得再分配 r3,实际 {corrected_plan.get('revision')}")
        applied = mgs_records.apply_design_snapshot(
            root, corrected_plan, confirmed=True)
        check(applied.get("ok") is True, f"新修订应另存:{applied}")
        check((r3 / "overall.md").read_text(encoding="utf-8") == "已占用的 r3 正文\n",
              "已占用修订目录不得被覆盖")


def test_github_snapshot_association_http_error_is_not_complete() -> None:
    """复用快照时 PATCH 失败不得在索引已在时仍宣称关联成功。"""

    with tempfile.TemporaryDirectory() as tmp:
        root = _onboard_github(Path(tmp) / "assoc")
        fake = FakeTransport()
        cache = root / "docs/mygamestudio/records/cache"
        spec_plan = mgs_records.plan_spec_adoption(root, {
            "kind": "new_feature",
            "source": "开发者主动 to-spec",
            "overall": {
                "title": "assoc 整体设计",
                "version": "v1",
                "core_play": "接星星。",
                "rules": ["得分：每颗星星 1 分。"],
            },
            "modules": {
                "规则与数值": {"title": "规则与数值", "rules": ["每颗星星 1 分。"]},
            },
        }, transport=fake, cache_dir=cache)
        mgs_records.apply_spec_adoption(
            root, spec_plan, confirmed=True, transport=fake, cache_dir=cache)
        first = mgs_records.apply_design_snapshot(root, mgs_records.plan_design_snapshot(root, {
            "trigger": "explicit",
            "game_version": "0.1.0",
            "source": "开发者明确要求",
        }, transport=fake, cache_dir=cache), confirmed=True,
            transport=fake, cache_dir=cache)
        check(first.get("complete") is True, f"首次归档应完整:{first}")
        snap = next(item for item in fake.issues
                    if "快照身份:" in (item.get("body") or ""))
        before = snap.get("body") or ""
        fake.http_error("PATCH", f"/issues/{snap['number']}", 500)
        reused = mgs_records.apply_design_snapshot(root, mgs_records.plan_design_snapshot(root, {
            "trigger": "explicit",
            "reuse_design_id": first.get("design_id"),
            "game_version": "0.2.0",
            "source": "复用设计",
        }, transport=fake, cache_dir=cache), confirmed=True,
            transport=fake, cache_dir=cache)
        check(reused.get("ok") is not True or reused.get("complete") is not True,
              f"关联 PATCH 失败不得宣称完整:{reused}")
        after = next(item for item in fake.issues
                     if item.get("number") == snap["number"]).get("body") or ""
        check("0.2.0" not in after or after == before,
              "失败的版本关联不得被当成已经写入")


def test_interrupted_snapshot_retry_fills_modules_before_complete() -> None:
    """中断重试不得只凭 overall/meta 宣告修订完整;设计模块必须补齐。"""

    with tempfile.TemporaryDirectory() as tmp:
        root = _onboard_local(Path(tmp) / "star-catcher")
        plan = mgs_records.plan_design_snapshot(root, {
            "trigger": "version_freeze",
            "game_version": "0.1.0",
            "source": "正式版本设计确定",
        })
        rev_dir = root / "docs/mygamestudio/records/design-snapshots" / \
            str(plan.get("design_id") or "ds-1") / str(plan.get("revision") or "r1")
        # 模拟第一次尝试中断:只写了 overall.md 与 meta.md,模块未写。
        rev_dir.mkdir(parents=True)
        overall_now = mgs_records.read_current_design(root).get("overall") or ""
        (rev_dir / "overall.md").write_text(overall_now, encoding="utf-8")
        (rev_dir / "meta.md").write_text(
            "# 正式版本设计快照\n\n形成时间:2026-09-15\n", encoding="utf-8")
        applied = mgs_records.apply_design_snapshot(root, plan)
        check(applied.get("complete") is True,
              f"中断重试应补齐后宣告完整:{applied}")
        modules_dir = rev_dir / "modules"
        check((modules_dir / "rules.md").is_file(),
              "完整修订必须包含设计模块文件,不得只凭 overall/meta 宣告完整")
        if (modules_dir / "rules.md").is_file():
            check((modules_dir / "rules.md").read_text(encoding="utf-8")
                  == MODULE_RULES, "补写的模块内容必须与被归档设计一致")


def test_escaping_snapshot_ids_and_attachments_are_refused() -> None:
    """快照身份/修订与附件路径越界时拒绝归档:不外写目录,不读项目外内容。"""

    with tempfile.TemporaryDirectory() as tmp:
        base = Path(tmp)
        root = _onboard_local(base / "star-catcher")
        outside = base / "outside"
        outside.mkdir()
        secret = outside / "secret.md"
        secret.write_text("项目外秘密内容\n", encoding="utf-8")

        for bad_id in ("/tmp/escape", "../escape", "ds/inner"):
            plan = mgs_records.plan_design_snapshot(root, {
                "trigger": "version_freeze",
                "game_version": "0.1.0",
                "design_id": bad_id,
                "source": "正式版本设计确定",
            })
            applied = mgs_records.apply_design_snapshot(root, plan, confirmed=True)
            check(applied.get("ok") is not True,
                  f"越界 design_id {bad_id!r} 不得报告成功:{applied}")
        hand = mgs_records.apply_design_snapshot(root, {
            "should_snapshot": True, "design_id": "../escape", "revision": "r1",
            "game_version": "0.1.0", "source": "正式版本设计确定",
        }, confirmed=True)
        check(hand.get("ok") is not True, "手工构造 plan 的越界身份同样拒绝")
        snapshots_root = root / "docs/mygamestudio/records/design-snapshots"
        check(not (base / "escape").exists(),
              "越界身份不得在归档根外创建目录")
        for path in (snapshots_root.rglob("*") if snapshots_root.is_dir() else []):
            if path.is_file():
                check("项目外秘密内容" not in path.read_text(encoding="utf-8"),
                      "归档目录不得包含项目外文件内容")

        for bad_rel in (str(secret), "../outside/secret.md"):
            plan = mgs_records.plan_design_snapshot(root, {
                "trigger": "version_freeze",
                "game_version": "0.1.0",
                "source": "正式版本设计确定",
                "attachments": [bad_rel],
            })
            applied = mgs_records.apply_design_snapshot(root, plan, confirmed=True)
            check(applied.get("ok") is not True
                  and applied.get("complete") is not True,
                  f"越界附件 {bad_rel!r} 不得归档成功:{applied}")

        gh_root = _onboard_github(base / "gh-star")
        fake = FakeTransport()
        cache = gh_root / "docs/mygamestudio/records/cache"
        gh_plan = mgs_records.plan_design_snapshot(gh_root, {
            "trigger": "explicit",
            "game_version": "0.1.0",
            "source": "开发者明确要求",
            "attachments": ["../outside/secret.md"],
        }, transport=fake, cache_dir=cache)
        gh_applied = mgs_records.apply_design_snapshot(
            gh_root, gh_plan, confirmed=True, transport=fake, cache_dir=cache)
        check(gh_applied.get("ok") is not True,
              f"GitHub 路径的越界附件同样拒绝:{gh_applied}")
        check(not any("项目外秘密内容" in (item.get("body") or "")
                      for item in fake.issues),
              "越界附件内容不得进入任何归档 Issue")


if __name__ == "__main__":
    TESTS = (
        test_version_freeze_archives_full_content_daily_does_not,
        test_records_identity_and_reuses_across_game_versions,
        test_current_design_change_keeps_old_snapshot_correction_is_new_revision,
        test_github_archive_issue_holds_full_content_not_a_live_link,
        test_github_snapshot_keeps_inner_markdown_fences,
        test_interrupt_and_source_change_do_not_claim_complete_archive,
        test_interrupted_snapshot_does_not_mix_source_revisions,
        test_same_basename_attachments_keep_distinct_paths,
        test_correction_revision_uses_highest_existing_number,
        test_github_snapshot_association_http_error_is_not_complete,
        test_interrupted_snapshot_retry_fills_modules_before_complete,
        test_escaping_snapshot_ids_and_attachments_are_refused,
    )
    raise SystemExit(run_theme(
        "正式版本设计快照(#54 T6/T7)", TESTS, FAILURES))

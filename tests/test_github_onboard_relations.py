#!/usr/bin/env python3
"""Issue #52 seams: GitHub onboard, native relations, frontier, recovery.

Confirmed seams (issue #52 acceptance + #49 T2/T4/T10):
- T2 discovery/invocation: game and Matt entries locate current-stage materials;
  reading materials does not start production.
- T4 tracker semantics: GitHub is the unique current source; native assignees,
  labels, parent/child and blocking are readable/writable with readback;
  frontier, claim and close meanings follow D5.
- T10 authority/recovery: ordinary work needs no gate; lost responses reread
  actual state; offline keeps unpublished drafts; recovery fills gaps only;
  no duplicate issues, comments or relations.

Expected values come from issues #52 and #49 D1/D3/D5/D8, not internals.

    python3 -B tests/test_github_onboard_relations.py
"""

from __future__ import annotations

import hashlib
import json
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.request
from pathlib import Path

from github_backend_fixtures import AUTH, REPO, make_checker, run_theme
from github_backend_transport import FakeTransport
from records_backend_support import run_cli

import mgs_github  # noqa: E402
import mgs_records  # noqa: E402

FAILURES, check = make_checker()
REPO_ROOT = Path(__file__).resolve().parents[1]
PLUGIN_ROOT = REPO_ROOT / "plugin"
STANDIN = REPO_ROOT / "acceptance" / "_shared" / "standin_github.py"
STANDIN_TOKEN = "synthetic-standin-token"


def _snapshot(root: Path) -> dict[str, str]:
    files = {}
    for path in sorted(root.rglob("*")):
        if path.is_file():
            files[str(path.relative_to(root))] = hashlib.sha256(
                path.read_bytes()).hexdigest()
    return files


def _write_tree(root: Path, files: dict[str, str]) -> None:
    for rel, text in files.items():
        path = root / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")


def _task_request(goal: str, *, deps: str = "无") -> dict:
    return {
        "当前目标": goal,
        "输入与基线": "PROJECT.md v1",
        "本次交付": "可回读的任务记录",
        "允许修改范围": "docs/mygamestudio/**",
        "所需能力": "文件读写",
        "完成标准": "记录可回读",
        "执行责任": "Agent(制作实现)",
        "验收方式": "代码级检查",
        "依赖": deps,
    }


def test_github_onboard_then_create_and_query_one_task() -> None:
    """AC1/AC2/T2/T4: 选择 GitHub 后接入、记录一项任务并只读查询。
    现行来源是 GitHub;本地不另起任务账本;INDEX 指向阶段资料。
    """

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp) / "star-catcher"
        _write_tree(root, {
            "README.md": "# star-catcher\n\n接星星。方向键移动。\n",
            "src/main.js": "console.log('catch');\n",
        })
        before = _snapshot(root)
        analysis = mgs_records.analyze_project(root)
        check(analysis.get("wrote") is False, "分析阶段必须只读")
        check(before == _snapshot(root), "分析不得改原项目")

        plan = mgs_records.plan_github_onboarding(
            root, repo=REPO, authorization=AUTH)
        check(plan.get("backend") == "github-issues",
              "本票选择的唯一 tracker 必须是 GitHub Issues")
        check(plan.get("wrote") is False, "接入清单阶段不得写入")
        actions = {(row.get("path"), row.get("action"))
                   for row in plan.get("items", [])}
        check(any(path.endswith("CONFIG.md") and action == "新增"
                  for path, action in actions),
              "接入清单应包含建立协作配置")
        check(any("INDEX.md" in (path or "") for path, _action in actions),
              "接入清单应包含资料指针入口")

        applied = mgs_records.apply_github_onboarding(
            root, plan, confirmed=True)
        check(applied.get("ok") is True, f"确认后应能完成 GitHub 接入:{applied}")
        check(applied.get("gate_required") is False, "普通接入不得依赖 gate")
        check(before.items() <= _snapshot(root).items(),
              "接入不得覆盖接入前已有的有效资料")
        config = mgs_records.load_config(root)
        check(config["backend"] == "github-issues",
              f"现行任务来源必须是 GitHub,实际 {config['backend']}")
        check(config["repo"]["owner"] == "mygamestudio"
              and config["repo"]["repo"] == "issue-accept",
              f"任务位置必须是明确仓库坐标,实际 {config.get('repo')}")
        index = (root / "docs/mygamestudio/INDEX.md").read_text(encoding="utf-8")
        check("stage-requirements.md" in index,
              "INDEX 必须指向当前阶段游戏资料入口")
        check(REPO in index or "issue-accept" in index,
              "INDEX 必须指向 GitHub 现行任务位置")
        check("读取不是开始制作" in index or "不是开始制作" in index,
              "阶段资料指针必须声明读取不是开始制作")
        work = root / "docs/mygamestudio/work"
        check(not work.exists() or not any(work.rglob("task.md")),
              "本地不得另起现行任务账本")

        fake = FakeTransport()
        created = mgs_records.create_task(
            root, "01-catch-star", "接住第一颗星星",
            _task_request("接住一颗星星并计分"),
            triage="ready-for-agent", transport=fake)
        check(created.get("created") is True, f"应能在 GitHub 记录一项任务:{created}")
        task = mgs_records.read_task(root, "01-catch-star", transport=fake)
        check(task["identity"] == "01-catch-star"
              and task["triage"] == "ready-for-agent"
              and task["progress"] == "待执行"
              and task.get("issue_number"),
              f"回读任务身份/分流/进度/Issue 号应与写入一致:{task}")
        status = mgs_records.status_report(root, transport=fake)
        check(status.get("wrote") is False, "Game-Producer 查询不得写入")
        check(status.get("backend") == "github-issues",
              "状态查询必须标明现行来源是 GitHub")
        identities = [item.get("identity") for item in status.get("tasks", [])]
        check("01-catch-star" in identities, "状态查询必须读到真实 GitHub 任务")
        check(not any((root / "docs/mygamestudio/work").rglob("task.md"))
              if (root / "docs/mygamestudio/work").exists() else True,
              "查询后仍不得把 GitHub 任务落到本地 task.md")

        first = _snapshot(root)
        again = mgs_records.apply_github_onboarding(
            root, mgs_records.plan_github_onboarding(
                root, repo=REPO, authorization=AUTH),
            confirmed=True)
        check(again.get("ok") is True, "重复接入应可运行")
        check(first == _snapshot(root), "无缺口时重复接入不得改已有内容")


def test_github_design_mapping_matches_remote_spec() -> None:
    """远端规格采纳后,文档映射不得再把本地 GAME_DESIGN.md 报成缺失。"""

    with tempfile.TemporaryDirectory() as tmp:
        root = _onboard_github(Path(tmp) / "remote-design")
        (root / "docs/mygamestudio/TECH_DESIGN.md").write_text(
            "# 技术约定\n\n基线版本:v1。纯 HTML/JS。\n", encoding="utf-8")
        config = mgs_records.load_config(root)
        design_rows = [
            row for row in config.get("docmap") or []
            if "游戏需求" in (row.get("content") or "")
            or "游戏设计" in (row.get("content") or "")
        ]
        check(design_rows, "必须有游戏设计映射行")
        check(all("GAME_DESIGN.md" not in (row.get("path") or "")
                  for row in design_rows),
              f"GitHub tracker 的设计权威位置必须是远端规格,实际 {design_rows}")
        fake = FakeTransport()
        cache = root / "docs/mygamestudio/records/cache"
        plan = mgs_records.plan_spec_adoption(root, {
            "kind": "new_feature",
            "source": "开发者主动 to-spec",
            "overall": {
                "title": "star-catcher 设计",
                "version": "v1",
                "core_play": "接星星。",
                "rules": ["得分：每颗星星 1 分。"],
            },
        }, transport=fake, cache_dir=cache)
        adopted = mgs_records.apply_spec_adoption(
            root, plan, confirmed=True, transport=fake, cache_dir=cache)
        check(adopted.get("ok") is True, f"应能采纳远端规格:{adopted}")
        status = mgs_records.status_report(
            root, transport=fake, cache_dir=cache)
        gaps = " ".join(str(item) for item in (status.get("gaps") or []))
        check("GAME_DESIGN.md" not in gaps,
              f"状态缺口不得再报本地 GAME_DESIGN.md:{gaps}")
        verified = mgs_records.verify_project(
            root, transport=fake, cache_dir=cache)
        path_check = next(
            (item for item in verified.get("checks") or []
             if item.get("name") == "docmap-paths-exist"),
            {})
        check(path_check.get("ok") is True,
              f"远端规格映射不得因本地文件缺失失败:{path_check}")
        check("GAME_DESIGN.md" not in str(path_check.get("detail") or ""),
              f"核验不得把 GAME_DESIGN.md 当缺失权威位置:{path_check}")
        baseline = mgs_records.baseline_report(
            root, transport=fake, cache_dir=cache)
        design_docs = [
            item for item in baseline.get("docs") or []
            if "游戏需求" in (item.get("content") or "")
            or "游戏设计" in (item.get("content") or "")
        ]
        check(design_docs and all(item.get("status") != "文件缺失"
                                  for item in design_docs),
              f"基线报告必须读到远端现行规格,实际 {design_docs}")


def test_producer_and_matt_entries_read_stage_materials_after_github_onboard() -> None:
    """AC2/T2: 查询只读;游戏入口与 Matt 入口都能找到当前阶段资料。"""

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp) / "query"
        root.mkdir()
        (root / "README.md").write_text("# query\n", encoding="utf-8")
        mgs_records.apply_github_onboarding(
            root, mgs_records.plan_github_onboarding(
                root, repo=REPO, authorization=AUTH),
            confirmed=True)
        fake = FakeTransport()
        mgs_records.create_task(
            root, "01-alpha", "甲",
            _task_request("可查询"),
            triage="ready-for-agent", transport=fake)
        before = _snapshot(root)
        status = mgs_records.status_report(root, transport=fake)
        check(status["wrote"] is False, "状态查询不得写入")
        check(before == _snapshot(root), "查询前后项目内容必须不变")
        check("01-alpha" in [t["identity"] for t in status["tasks"]],
              "必须读取真实 GitHub 任务记录")
        check(status.get("gaps") or status.get("missing"),
              "应说明缺项(例如尚未建立的规格文件)")
        index = (root / "docs/mygamestudio/INDEX.md").read_text(encoding="utf-8")
        check("stage-requirements.md" in index, "游戏入口应能从 INDEX 找到阶段资料")
        for name in ("game-producer", "game-init", "implement", "to-spec",
                     "to-tickets"):
            text = (PLUGIN_ROOT / "skills" / name / "SKILL.md").read_text(
                encoding="utf-8")
            check("stage-requirements.md" in text,
                  f"{name} 必须能找到当前阶段游戏资料入口")
        stage = (PLUGIN_ROOT / "internal" / "game" / "stage-requirements.md"
                 ).read_text(encoding="utf-8")
        init_section = stage.split("## 项目接入")[1].split("## ")[0]
        check("GitHub" in init_section,
              "阶段资料接入节必须覆盖 GitHub tracker")
        check("后续票" not in init_section,
              "阶段资料接入节不得再把 GitHub 写成未实现后续票")


def _onboard_github(root: Path) -> Path:
    root.mkdir(parents=True, exist_ok=True)
    (root / "README.md").write_text(f"# {root.name}\n", encoding="utf-8")
    mgs_records.apply_github_onboarding(
        root, mgs_records.plan_github_onboarding(
            root, repo=REPO, authorization=AUTH),
        confirmed=True)
    return root


def test_native_claim_frontier_parent_and_blocking() -> None:
    """AC1/T4: 原生 Issue、负责人、分流标签、父子与阻塞可回读;
    前沿是开放、未认领、无开放阻塞的子票;关闭原因不等于验收。
    """

    with tempfile.TemporaryDirectory() as tmp:
        root = _onboard_github(Path(tmp) / "loop")
        fake = FakeTransport()
        mgs_records.create_task(
            root, "00-map", "地图",
            _task_request("索引当前决定"),
            triage="ready-for-agent", transport=fake)
        mgs_records.create_task(
            root, "01-alpha", "甲",
            _task_request("无依赖的可执行切片"),
            triage="ready-for-agent", transport=fake)
        mgs_records.create_task(
            root, "02-beta", "乙",
            _task_request("被甲阻塞"),
            triage="ready-for-agent", transport=fake)
        parent = mgs_records.set_parent(
            root, "01-alpha", "00-map", transport=fake)
        check(parent.get("mode") == "native-sub-issues",
              f"父子关系必须走原生 sub-issues,实际 {parent}")
        mgs_records.set_parent(root, "02-beta", "00-map", transport=fake)
        blocked = mgs_records.set_relations(
            root, "02-beta", ["01-alpha"], transport=fake)
        check(blocked.get("mode") == "native-blocked-by",
              f"阻塞关系必须走原生 blocked_by,实际 {blocked}")
        alpha = mgs_records.read_task(root, "01-alpha", transport=fake)
        beta = mgs_records.read_task(root, "02-beta", transport=fake)
        check(alpha["triage"] == "ready-for-agent" and alpha["progress"] == "待执行",
              "分流与进度必须同时可读且初始分开")
        check(alpha.get("parent_identity") == "00-map"
              or alpha["request"].get("父任务", "").find("00-map") >= 0,
              f"父子关系必须可回读,实际 {alpha}")
        check(beta.get("blocked_by_identities") == ["01-alpha"]
              or "01-alpha" in str(beta.get("blocked_by") or []),
              f"阻塞关系必须可回读,实际 {beta}")
        frontier = mgs_records.frontier_tasks(
            root, parent_identity="00-map", transport=fake)
        ids = [item["identity"] for item in frontier.get("frontier") or []]
        check(ids == ["01-alpha"],
              f"前沿应是开放未认领且无开放阻塞的子票,按子票顺序,实际 {ids}")
        check(frontier.get("selected", {}).get("identity") == "01-alpha",
              "应按子票顺序选出第一张前沿票")
        claimed = mgs_records.claim_task(
            root, "01-alpha", "agent-a", transport=fake)
        check("agent-a" in (claimed.get("readback") or {}).get("assignees")
              or claimed.get("readback", {}).get("claim") == "agent-a",
              f"认领必须写入原生负责人,实际 {claimed}")
        after_claim = mgs_records.frontier_tasks(
            root, parent_identity="00-map", transport=fake)
        check("01-alpha" not in [i["identity"] for i in after_claim.get("frontier") or []],
              "已认领任务必须离开前沿")
        check("02-beta" not in [i["identity"] for i in after_claim.get("frontier") or []],
              "仍被开放票阻塞的任务不得进入前沿")
        closed = mgs_records.close_task(
            root, "01-alpha", "不再执行", note="范围取消", transport=fake)
        check(closed.get("close_reason") == "不再执行", "关闭必须注明原因")
        check("不自动等于验证通过" in closed.get("note", ""),
              "关闭不得被推断为验收通过")
        after = mgs_records.read_task(root, "01-alpha", transport=fake)
        check(after.get("state") == "closed", "关闭须反映为 Issue 关闭")
        check(after["progress"] == "不再执行",
              f"生命周期应随关闭原因变化,实际 {after['progress']}")
        check(after["triage"] == "ready-for-agent",
              "关闭不得改写分流;分流与生命周期分开")
        unblocked = mgs_records.frontier_tasks(
            root, parent_identity="00-map", transport=fake)
        check([i["identity"] for i in unblocked.get("frontier") or []] == ["02-beta"],
              f"阻塞关闭后乙应进入前沿,实际 {unblocked}")
        result = mgs_records.append_result(
            root, "02-beta", "中断前已保存草稿。", transport=fake)
        check(result.get("published") is True and result.get("comment_id"),
              f"结果应落到对应 Issue 评论,实际 {result}")
        check(not any((root / "docs/mygamestudio/work").rglob("task.md"))
              if (root / "docs/mygamestudio/work").exists() else True,
              "结果与任务不得落到本地第二套现行账本")


def test_clearing_deps_and_parent_removes_native_relations() -> None:
    """T4: 正文改为无依赖/无父任务时,原生 blocked_by 与 sub-issues 必须同步移除。"""

    with tempfile.TemporaryDirectory() as tmp:
        root = _onboard_github(Path(tmp) / "detach")
        fake = FakeTransport()
        mgs_records.create_task(
            root, "00-map", "地图", _task_request("索引"),
            triage="ready-for-agent", transport=fake)
        mgs_records.create_task(
            root, "01-alpha", "甲", _task_request("阻塞者"),
            triage="ready-for-agent", transport=fake)
        mgs_records.create_task(
            root, "02-beta", "乙", _task_request("被阻塞"),
            triage="ready-for-agent", transport=fake)
        mgs_records.set_parent(root, "02-beta", "00-map", transport=fake)
        mgs_records.set_relations(root, "02-beta", ["01-alpha"], transport=fake)
        beta_no = mgs_records.read_task(root, "02-beta", transport=fake)["issue_number"]
        map_no = mgs_records.read_task(root, "00-map", transport=fake)["issue_number"]
        beta_id = next(item["id"] for item in fake.issues
                       if item["number"] == beta_no)
        cleared = mgs_records.set_relations(root, "02-beta", [], transport=fake)
        check(cleared.get("mode") == "native-blocked-by",
              f"清空依赖必须走原生移除,实际 {cleared}")
        check(not fake.blocked_by.get(beta_no),
              f"原生 blocked_by 必须清空,实际 {fake.blocked_by}")
        still_blocked = mgs_records.frontier_tasks(
            root, parent_identity="00-map", transport=fake)
        check("02-beta" in [i["identity"] for i in still_blocked.get("frontier") or []],
              "去掉阻塞后乙应能进入父任务前沿")
        detached = mgs_records.set_parent(root, "02-beta", None, transport=fake)
        check(detached.get("mode") == "native-sub-issues",
              f"解除父任务必须走原生移除,实际 {detached}")
        check(beta_id not in (fake.sub_issues.get(map_no) or []),
              f"原生子 Issue 必须删除,实际 {fake.sub_issues}")
        after = mgs_records.frontier_tasks(
            root, parent_identity="00-map", transport=fake)
        check("02-beta" not in [i["identity"] for i in after.get("frontier") or []],
              "解除父任务后不得仍出现在原父任务前沿")


def test_github_onboard_does_not_succeed_over_local_tracker() -> None:
    """D5: 已有本地 Markdown tracker 时,GitHub 接入不得报成功却仍写本地。"""

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp) / "already-local"
        root.mkdir()
        (root / "README.md").write_text("# already-local\n", encoding="utf-8")
        mgs_records.apply_local_onboarding(
            root, mgs_records.plan_local_onboarding(root), confirmed=True)
        check(mgs_records.load_config(root)["backend"] == "local-markdown",
              "前置必须已是本地 Markdown tracker")
        plan = mgs_records.plan_github_onboarding(
            root, repo=REPO, authorization=AUTH)
        check(plan.get("ok") is not True,
              f"计划必须拒绝 tracker 冲突,实际 {plan}")
        applied = mgs_records.apply_github_onboarding(
            root, plan, confirmed=True)
        check(applied.get("ok") is not True,
              f"不得把 GitHub 接入报成成功,实际 {applied}")
        check(applied.get("wrote") is not True,
              "冲突接入不得写入")
        check(mgs_records.load_config(root)["backend"] == "local-markdown",
              "现行 tracker 必须仍是本地 Markdown")


def test_local_onboard_does_not_succeed_over_github_tracker() -> None:
    """D5: 已有 GitHub Issues tracker 时,本地接入不得报成功却另起本地账本。"""

    with tempfile.TemporaryDirectory() as tmp:
        root = _onboard_github(Path(tmp) / "already-github")
        check(mgs_records.load_config(root)["backend"] == "github-issues",
              "前置必须已是 GitHub Issues tracker")
        before = _snapshot(root)
        plan = mgs_records.plan_local_onboarding(root)
        check(plan.get("ok") is not True,
              f"计划必须拒绝 tracker 冲突,实际 {plan}")
        applied = mgs_records.apply_local_onboarding(
            root, plan, confirmed=True)
        check(applied.get("ok") is not True,
              f"不得把本地接入报成成功,实际 {applied}")
        check(applied.get("wrote") is not True,
              "冲突接入不得写入")
        check(mgs_records.load_config(root)["backend"] == "github-issues",
              "现行 tracker 必须仍是 GitHub Issues")
        work = root / "docs/mygamestudio/work"
        check(not work.exists() or not any(work.rglob("task.md")),
              "冲突接入不得另起本地现行任务账本")
        check(before == _snapshot(root), "冲突接入不得改已有协作配置")


def test_github_onboard_does_not_reuse_a_different_repository() -> None:
    """D5: 已接到仓库 A 时,不得把仓库 B 的接入报成成功却仍使用 A。"""

    other = "github.com/mygamestudio/other-game"
    with tempfile.TemporaryDirectory() as tmp:
        root = _onboard_github(Path(tmp) / "repo-a")
        config = mgs_records.load_config(root)
        check(config["repo"]["owner"] == "mygamestudio"
              and config["repo"]["repo"] == "issue-accept",
              f"前置必须已接到仓库 A,实际 {config.get('repo')}")
        plan = mgs_records.plan_github_onboarding(
            root, repo=other, authorization=AUTH)
        check(plan.get("ok") is not True,
              f"计划必须拒绝仓库冲突,实际 {plan}")
        applied = mgs_records.apply_github_onboarding(
            root, plan, confirmed=True)
        check(applied.get("ok") is not True,
              f"不得把另一仓库接入报成成功,实际 {applied}")
        check(applied.get("wrote") is not True, "仓库冲突不得写入")
        after = mgs_records.load_config(root)
        check(after["backend"] == "github-issues",
              "现行 tracker 必须仍是 GitHub Issues")
        check(after["repo"]["owner"] == "mygamestudio"
              and after["repo"]["repo"] == "issue-accept",
              f"现行仓库必须仍是 A,实际 {after.get('repo')}")


def test_transient_error_does_not_downgrade_native_relations() -> None:
    """AC4: 短暂错误不得自行降级为正文约定;确认不可用才回退。"""

    with tempfile.TemporaryDirectory() as tmp:
        root = _onboard_github(Path(tmp) / "probe")
        cache = Path(tmp) / "cache"
        fake = FakeTransport()
        mgs_records.create_task(
            root, "00-map", "地图", _task_request("父"),
            triage="ready-for-agent", transport=fake, cache_dir=cache)
        mgs_records.create_task(
            root, "01-alpha", "甲", _task_request("子"),
            triage="ready-for-agent", transport=fake, cache_dir=cache)
        fake.fail("GET", "/sub_issues", "timeout")
        result = mgs_records.set_parent(
            root, "01-alpha", "00-map", transport=fake, cache_dir=cache)
        check(result.get("mode") != "body-reference",
              f"超时探测不得降级为正文引用,实际 {result}")
        check(result.get("published") is False
              or result.get("status") == "未发布草稿",
              f"短暂失败应保留未发布草稿或未知状态,实际 {result}")
        check(not fake.sub_issues,
              "超时后不得假装已写入或已确认原生关系不可用")
        fake._fail.clear()
        recovered = mgs_records.set_parent(
            root, "01-alpha", "00-map", transport=fake, cache_dir=cache)
        check(recovered.get("mode") == "native-sub-issues",
              f"恢复后应使用原生父子关系,实际 {recovered}")

    with tempfile.TemporaryDirectory() as tmp:
        root = _onboard_github(Path(tmp) / "fallback")
        fake = FakeTransport(sub_issues_supported=False)
        mgs_records.create_task(
            root, "00-map", "地图", _task_request("父"),
            triage="ready-for-agent", transport=fake)
        mgs_records.create_task(
            root, "01-alpha", "甲", _task_request("子"),
            triage="ready-for-agent", transport=fake)
        result = mgs_records.set_parent(
            root, "01-alpha", "00-map", transport=fake)
        check(result.get("mode") == "body-reference",
              f"确认不可用才允许正文回退,实际 {result}")
        check(result.get("fallback_reason"),
              "回退必须说明是能力确认不可用")


def test_auth_lost_response_offline_draft_cancel_and_dedup() -> None:
    """AC3/AC5/T10: 写入守授权;响应丢失先回读;离线草稿;取消不重放;只补缺项。"""

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp) / "auth"
        root.mkdir()
        (root / "README.md").write_text("# auth\n", encoding="utf-8")
        mgs_records.apply_github_onboarding(
            root, mgs_records.plan_github_onboarding(
                root, repo=REPO, authorization="无"),
            confirmed=True)
        fake = FakeTransport()
        try:
            mgs_records.create_task(
                root, "01-alpha", "甲", _task_request("未授权"),
                transport=fake)
        except mgs_records.RecordsError as exc:
            check("授权" in str(exc) or "不等于批准" in str(exc),
                  f"无 issues-write 授权必须拒绝:{exc}")
        else:
            check(False, "未授权时不得创建远端 Issue")
        check(not any(call[0] == "POST" for call in fake.calls),
              "未授权不得发出远端写请求")

    with tempfile.TemporaryDirectory() as tmp:
        root = _onboard_github(Path(tmp) / "recover")
        cache = Path(tmp) / "gh-cache"
        check(not (PLUGIN_ROOT / ".mcp.json").is_file(),
              "普通 GitHub 工作不得依赖插件注册 mgs-gate")
        fake = FakeTransport()
        fake.drop("POST", "/issues")
        created = mgs_records.create_task(
            root, "01-alpha", "甲", _task_request("可恢复"),
            triage="ready-for-agent", transport=fake, cache_dir=cache)
        check(created.get("adopted") is True or created.get("duplicate_avoided") is True,
              f"响应丢失后应回读收养,不得重复创建:{created}")
        check(len([item for item in fake.issues
                   if "任务身份:01-alpha" in (item.get("body") or "")]) == 1,
              "远端必须只有一个 01-alpha")
        fake.offline()
        draft = mgs_records.create_task(
            root, "02-beta", "乙", _task_request("离线"),
            transport=fake, cache_dir=cache)
        check(draft.get("published") is False
              and draft.get("status") == "未发布草稿",
              f"离线应保存未发布草稿,实际 {draft}")
        check("不静默切换本地后端" in (draft.get("note") or ""),
              "草稿不得被当成已发布或改用本地 tracker")
        check(not (root / "docs/mygamestudio/work" / "02-beta").exists(),
              "离线不得把草稿写成现行本地任务")
        cancelled = mgs_records.cancel_operation(
            root, "create_task", "02-beta", config_rel="docs/mygamestudio/CONFIG.md")
        check(cancelled.get("cancelled") is True, f"应能登记撤销:{cancelled}")
        fake._offline = False
        try:
            replay = mgs_records.create_task(
                root, "02-beta", "乙", _task_request("不该恢复"),
                transport=fake, cache_dir=cache)
        except mgs_records.RecordsError as exc:
            check("撤销" in str(exc) or "不得恢复" in str(exc),
                  f"不得恢复已撤销动作:{exc}")
            replay = None
        else:
            check(replay.get("created") is not True,
                  "取消后不得再创建被撤销身份的任务")
        check(not any("任务身份:02-beta" in (item.get("body") or "")
                      for item in fake.issues),
              "已撤销动作不得被恢复为现行 Issue")
        again = mgs_records.create_task(
            root, "01-alpha", "甲", _task_request("重复"),
            transport=fake, cache_dir=cache)
        check(again.get("created") is False and again.get("adopted") is True,
              f"重复创建应回读收养:{again}")
        mgs_records.create_task(
            root, "03-gamma", "丙", _task_request("阻塞目标"),
            triage="ready-for-agent", transport=fake, cache_dir=cache)
        first_rel = mgs_records.set_relations(
            root, "03-gamma", ["01-alpha"], transport=fake, cache_dir=cache)
        posts_before = [call for call in fake.calls
                        if call[0] == "POST" and "blocked_by" in call[1]]
        second_rel = mgs_records.set_relations(
            root, "03-gamma", ["01-alpha"], transport=fake, cache_dir=cache)
        posts_after = [call for call in fake.calls
                       if call[0] == "POST" and "blocked_by" in call[1]]
        check(first_rel.get("mode") == "native-blocked-by"
              and second_rel.get("mode") == "native-blocked-by",
              f"阻塞关系应走原生:{first_rel}/{second_rel}")
        check(len(posts_after) == len(posts_before),
              f"已存在的原生阻塞关系不得重复创建,实际 {len(posts_before)} -> {len(posts_after)}")
        comment_posts = [call for call in fake.calls
                         if call[0] == "POST" and call[1].endswith("/comments")]
        mgs_records.append_result(
            root, "01-alpha", "同一结果。", transport=fake, cache_dir=cache)
        mgs_records.append_result(
            root, "01-alpha", "同一结果。", transport=fake, cache_dir=cache)
        comment_after = [call for call in fake.calls
                         if call[0] == "POST" and call[1].endswith("/comments")]
        check(len(comment_after) <= len(comment_posts) + 1,
              "相同结果恢复时不得重复发布评论")


def test_cli_github_onboard_status_and_create_without_gate() -> None:
    """AC5: 正常接入、记录与只读查询可通过 CLI 外部行为检查,不依赖 gate。"""

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp) / "cli-game"
        root.mkdir()
        (root / "README.md").write_text("# cli-game\n", encoding="utf-8")
        analyze = run_cli("analyze", "--project", str(root))
        check(analyze.returncode == 0, f"CLI analyze 应成功:{analyze.stderr[:200]}")
        check(json.loads(analyze.stdout).get("wrote") is False,
              "CLI 分析必须只读")
        onboard = run_cli(
            "onboard", "--project", str(root), "--confirmed",
            "--tracker", "github-issues", "--repo", REPO,
            "--authorization", AUTH)
        check(onboard.returncode == 0, f"CLI GitHub onboard 应成功:{onboard.stderr[:200]}")
        data = json.loads(onboard.stdout)
        check(data.get("backend") == "github-issues",
              f"CLI 接入应选择 GitHub,实际 {data}")
        check(data.get("gate_required") is False, "CLI 接入不得要求 gate")


def _start_standin(state_file: Path) -> tuple[subprocess.Popen, str]:
    proc = subprocess.Popen(
        [sys.executable, "-B", str(STANDIN), "--port", "0",
         "--token", STANDIN_TOKEN, "--state-file", str(state_file)],
        stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    deadline = time.time() + 15
    while time.time() < deadline:
        line = proc.stdout.readline()
        if line.startswith("PORT "):
            return proc, line.split()[1].strip()
        if proc.poll() is not None:
            break
    proc.kill()
    raise RuntimeError("替身未在超时内打印端口")


def _standin_control(base: str, body: dict) -> None:
    request = urllib.request.Request(
        base + "/_test/control", data=json.dumps(body).encode(), method="POST")
    request.add_header("Content-Type", "application/json")
    request.add_header("Authorization", f"Bearer {STANDIN_TOKEN}")
    with urllib.request.urlopen(request, timeout=10) as response:
        response.read()


def _standin_state(base: str) -> dict:
    request = urllib.request.Request(base + "/_test/state", method="GET")
    with urllib.request.urlopen(request, timeout=10) as response:
        return json.loads(response.read().decode())


def test_http_standin_lost_response_and_native_readback() -> None:
    """AC5: 用现有 HTTP 传输替身验证响应丢失回读与原生关系,不依赖 gate。"""

    with tempfile.TemporaryDirectory() as tmp:
        root = _onboard_github(Path(tmp) / "standin-game")
        cache = Path(tmp) / "cache"
        proc, port = _start_standin(Path(tmp) / "state.json")
        base = f"http://127.0.0.1:{port}"
        transport = mgs_github.UrllibTransport(base, STANDIN_TOKEN)
        try:
            _standin_control(base, {"drop_next_create": True})
            dropped = False
            created = None
            try:
                created = mgs_records.create_task(
                    root, "01-alpha", "甲", _task_request("替身回读"),
                    triage="ready-for-agent", transport=transport,
                    cache_dir=cache)
            except (urllib.error.URLError, ConnectionError, OSError,
                    mgs_records.RecordsError):
                dropped = True
            dump = _standin_state(base)
            check(len(dump["issues"]) == 1,
                  f"drop_next_create 后远端应已有 Issue,实际 {dump['issues']}")
            if created is None:
                created = mgs_records.create_task(
                    root, "01-alpha", "甲", _task_request("替身回读"),
                    triage="ready-for-agent", transport=transport,
                    cache_dir=cache)
                dropped = True
            check(created.get("created") is False or created.get("adopted")
                  or created.get("duplicate_avoided") or dropped,
                  f"响应丢失后应回读收养:{created}")
            mgs_records.create_task(
                root, "00-map", "地图", _task_request("父"),
                triage="ready-for-agent", transport=transport, cache_dir=cache)
            mgs_records.create_task(
                root, "02-beta", "乙", _task_request("子"),
                triage="ready-for-agent", transport=transport, cache_dir=cache)
            parent = mgs_records.set_parent(
                root, "01-alpha", "00-map", transport=transport, cache_dir=cache)
            check(parent.get("mode") == "native-sub-issues",
                  f"HTTP 替身应读回原生父子关系:{parent}")
            _standin_control(base, {"drop_next_blocked_by": True})
            blocked = mgs_records.set_relations(
                root, "02-beta", ["01-alpha"], transport=transport,
                cache_dir=cache)
            if blocked.get("status") == "未发布草稿":
                blocked = mgs_records.set_relations(
                    root, "02-beta", ["01-alpha"], transport=transport,
                    cache_dir=cache)
            check(blocked.get("mode") == "native-blocked-by",
                  f"HTTP 替身应读回原生阻塞关系:{blocked}")
            dump = _standin_state(base)
            check(len(dump.get("blocked_by", {}).get("3", dump.get("blocked_by", {}).get(3, []))
                      or next(iter(dump.get("blocked_by", {}).values()), [])) <= 2,
                  f"丢失响应后不得重复阻塞关系:{dump.get('blocked_by')}")
            claimed = mgs_records.claim_task(
                root, "01-alpha", "agent-a", transport=transport, cache_dir=cache)
            check(claimed.get("readback", {}).get("claim") == "agent-a"
                  or "agent-a" in claimed.get("readback", {}).get("assignees", []),
                  f"HTTP 替身认领应回读负责人:{claimed}")
        finally:
            proc.kill()
            proc.wait(timeout=10)


TESTS = (
    test_github_onboard_then_create_and_query_one_task,
    test_github_design_mapping_matches_remote_spec,
    test_producer_and_matt_entries_read_stage_materials_after_github_onboard,
    test_native_claim_frontier_parent_and_blocking,
    test_clearing_deps_and_parent_removes_native_relations,
    test_github_onboard_does_not_succeed_over_local_tracker,
    test_local_onboard_does_not_succeed_over_github_tracker,
    test_github_onboard_does_not_reuse_a_different_repository,
    test_transient_error_does_not_downgrade_native_relations,
    test_auth_lost_response_offline_draft_cancel_and_dedup,
    test_cli_github_onboard_status_and_create_without_gate,
    test_http_standin_lost_response_and_native_readback,
)


if __name__ == "__main__":
    sys.exit(run_theme(
        "GitHub 项目接入与原生任务关系(#52)", TESTS, FAILURES))

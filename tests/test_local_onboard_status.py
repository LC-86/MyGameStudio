#!/usr/bin/env python3
"""Issue #51 seams: local Markdown onboard, tracker semantics, status, authority.

Confirmed seams (issue #51 acceptance + #49 T2/T4/T10):
- T2 discovery/invocation: game and Matt entries locate current-stage materials;
  reading materials does not start production.
- T4 tracker semantics: local Markdown is the unique current source; triage and
  lifecycle stay separate; identity, parent, deps, claim, close reason, and the
  startable set follow D5.
- T10 authority/recovery: ordinary local work needs no gate; concurrent overlap,
  cancel, and interrupt keep results, reread, fill gaps only, and never restore
  revoked actions.

Expected values come from issues #51 and #49 D1/D3/D5/D8, not from internals.

    python3 -B tests/test_local_onboard_status.py
"""

from __future__ import annotations

import hashlib
import json
import shutil
import sys
import tempfile
from pathlib import Path

from records_backend_support import make_checker, run_cli, run_theme

import mgs_records  # noqa: E402

FAILURES, check = make_checker()
REPO_ROOT = Path(__file__).resolve().parents[1]
PLUGIN_ROOT = REPO_ROOT / "plugin"
NEBULA = REPO_ROOT / "samples" / "nebula-drift"


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


def test_new_project_onboard_records_and_queries_one_task() -> None:
    """AC1: analyze existing materials, set pointers, choose local tracker,
    record one task, and query it. Valid materials are not overwritten.
    """

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp) / "star-catcher"
        _write_tree(root, {
            "README.md": "# star-catcher\n\n接星星。方向键移动。\n",
            "src/main.js": "console.log('catch');\n",
        })
        before = _snapshot(root)
        analysis = mgs_records.analyze_project(root)
        check(analysis.get("wrote") is False,
              "分析阶段必须只读,不得自行开始制作")
        check(before == _snapshot(root), "分析已有设计/工程/资料不得改原项目")
        classes = set(analysis.get("classes") or [])
        for name in ("实际行为", "已采纳", "历史内容", "缺口", "冲突", "未验证"):
            check(name in classes, f"现状分析应区分 {name}")
        check(any("src/main.js" in str(item) for item in analysis.get("engineering", [])),
              "分析应看到已有工程")

        plan = mgs_records.plan_local_onboarding(root)
        check(plan.get("backend") == "local-markdown",
              "本票选择的唯一 tracker 必须是本地 Markdown")
        actions = {(row.get("path"), row.get("action")) for row in plan.get("items", [])}
        check(any(path.endswith("CONFIG.md") and action == "新增"
                  for path, action in actions),
              "接入清单应包含建立协作配置")
        check(any("INDEX.md" in (path or "") for path, _action in actions),
              "接入清单应包含资料指针入口")

        applied = mgs_records.apply_local_onboarding(root, plan, confirmed=True)
        check(applied.get("ok") is True, f"确认后应能完成本地接入:{applied}")
        check(before.items() <= _snapshot(root).items(),
              "接入不得覆盖接入前已有的有效资料")
        config = mgs_records.load_config(root)
        check(config["backend"] == "local-markdown",
              f"现行任务来源必须是本地 Markdown,实际 {config['backend']}")
        index = (root / "docs/mygamestudio/INDEX.md").read_text(encoding="utf-8")
        check("stage-requirements.md" in index,
              "INDEX 必须指向当前阶段游戏资料入口")
        check("docs/mygamestudio/work" in index or config["task_root"] in index,
              "INDEX 必须指向现行任务位置")
        created = mgs_records.create_task(
            root, "01-catch-star", "接住第一颗星星",
            {"当前目标": "接住一颗星星并计分",
             "输入与基线": "README.md",
             "本次交付": "可操作的接星星最小闭环",
             "允许修改范围": "src/**",
             "所需能力": "文件读写",
             "完成标准": "方向键可移动并接到星星",
             "执行责任": "Agent(制作实现)",
             "验收方式": "代码级检查",
             "依赖": "无"},
            triage="ready-for-agent")
        check(created.get("created") is True, f"应能记录一项任务:{created}")
        task = mgs_records.read_task(root, "01-catch-star")
        check(task["identity"] == "01-catch-star"
              and task["triage"] == "ready-for-agent"
              and task["progress"] == "待执行",
              f"回读任务身份/分流/进度应与写入一致:{task}")
        status = mgs_records.status_report(root)
        check(status.get("wrote") is False, "Game-Producer 查询不得写入")
        identities = [item.get("identity") for item in status.get("tasks", [])]
        check("01-catch-star" in identities, "状态查询必须读到真实任务记录")
        check(status.get("next"), "状态查询应说明下一步")
        first = _snapshot(root)
        again = mgs_records.apply_local_onboarding(
            root, mgs_records.plan_local_onboarding(root), confirmed=True)
        check(again.get("ok") is True, "重复接入应可运行")
        check(first == _snapshot(root), "无缺口时重复接入不得改已有内容")


def test_existing_project_reuses_materials_and_flags_conflicts() -> None:
    """AC1/T4: 接手已有项目时映射有效设计/工程,不覆盖旧资料,冲突列入待决定。"""

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp) / "nebula-drift"
        shutil.copytree(NEBULA, root)
        design_before = (root / "docs" / "DESIGN_NOTES.md").read_text(encoding="utf-8")
        task_before = (root / "tasks" / "01-wire-jump" / "task.md").read_text(
            encoding="utf-8")
        src_before = (root / "src" / "player.js").read_bytes()
        analysis = mgs_records.analyze_project(root)
        check(analysis["wrote"] is False, "分析不得修改已有项目")
        check(any("DESIGN_NOTES.md" in item for item in analysis["已采纳"]),
              "应识别已有设计资料")
        check(any(item.startswith("src/") for item in analysis["engineering"]),
              "应识别已有工程")
        check(any("tasks/" in item for item in analysis["历史内容"]),
              "旧任务记应作为历史资料,不自动升为第二套现行账本")
        plan = mgs_records.plan_local_onboarding(root)
        check(any(item["path"].endswith("DESIGN_NOTES.md") and item["action"] == "复用"
                  for item in plan["items"]),
              "接入清单应对有效旧设计标为复用")
        applied = mgs_records.apply_local_onboarding(root, plan, confirmed=True)
        check(applied["ok"] is True, f"接手接入应成功:{applied}")
        check((root / "docs" / "DESIGN_NOTES.md").read_text(encoding="utf-8")
              == design_before, "不得覆盖有效旧设计")
        check((root / "tasks" / "01-wire-jump" / "task.md").read_text(encoding="utf-8")
              == task_before, "不得覆盖旧任务原文")
        check((root / "src" / "player.js").read_bytes() == src_before,
              "不得覆盖已有工程")
        config = mgs_records.load_config(root)
        check(config["backend"] == "local-markdown",
              "接手后唯一现行 tracker 仍是本地 Markdown")
        index = (root / "docs/mygamestudio/INDEX.md").read_text(encoding="utf-8")
        check("DESIGN_NOTES.md" in index, "INDEX 应指向仍有效的旧设计位置")
        created = mgs_records.create_task(
            root, "01-status-loop", "核对现行推进规则",
            {"当前目标": "把已采纳的单次推进记入现行任务",
             "完成标准": "任务可回读且旧设计未被改写",
             "执行责任": "Agent(制作实现)"},
            triage="ready-for-agent")
        check(created["created"] is True, f"接手后应能在现行 tracker 记录任务:{created}")
        check(mgs_records.read_task(root, "01-status-loop")["identity"]
              == "01-status-loop", "现行任务应可回读")


def _task_request(goal: str, *, deps: str = "无") -> dict:
    return {
        "当前目标": goal,
        "输入与基线": "PROJECT.md v1",
        "本次交付": "可回读的任务记录",
        "允许修改范围": "docs/mygamestudio/work/**",
        "所需能力": "文件读写",
        "完成标准": "记录可回读",
        "执行责任": "Agent(制作实现)",
        "验收方式": "代码级检查",
        "依赖": deps,
    }


def _onboarded(root: Path) -> Path:
    root.mkdir(parents=True, exist_ok=True)
    (root / "README.md").write_text(f"# {root.name}\n", encoding="utf-8")
    mgs_records.apply_local_onboarding(
        root, mgs_records.plan_local_onboarding(root), confirmed=True)
    return root


def test_tracker_keeps_unique_locations_and_lifecycle() -> None:
    """AC2/T4: 规格、任务、结果各有唯一位置;分流与生命周期分开;
    父子、依赖、认领、关闭原因和可开工集合按规格表达。
    """

    with tempfile.TemporaryDirectory() as tmp:
        root = _onboarded(Path(tmp) / "loop")
        (root / "README.md").write_text("# loop\n", encoding="utf-8")
        config = mgs_records.load_config(root)
        check(config["backend"] == "local-markdown", "唯一现行来源应是本地 Markdown")
        paths = [row["path"] for row in config["docmap"]]
        check(len(paths) == len(set(paths)), f"文档映射位置必须唯一,实际 {paths}")
        goal = [row["path"] for row in config["docmap"] if "目标" in row["content"]]
        design = [row["path"] for row in config["docmap"]
                  if "设计" in row["content"] or "需求" in row["content"]]
        check(goal and design and goal[0] != design[0],
              "现行规格与项目约定不得混在同一位置")
        check(config["task_root"] == "docs/mygamestudio/work",
              "现行任务位置应唯一指向 work/")
        parent = mgs_records.create_task(
            root, "00-map", "地图",
            _task_request("索引当前决定", deps="无"),
            triage="ready-for-agent")
        check(parent["created"] is True, "应能建立父任务")
        mgs_records.create_task(
            root, "01-alpha", "甲",
            _task_request("无依赖的可执行切片", deps="无"),
            triage="ready-for-agent")
        mgs_records.create_task(
            root, "02-beta", "乙",
            _task_request("被甲阻塞", deps="01-alpha"),
            triage="ready-for-agent")
        mgs_records.set_parent(root, "01-alpha", "00-map")
        mgs_records.set_parent(root, "02-beta", "00-map")
        alpha = mgs_records.read_task(root, "01-alpha")
        check(alpha["triage"] == "ready-for-agent" and alpha["progress"] == "待执行",
              "分流与进度必须同时可读且初始分开")
        check(alpha["request"].get("父任务") == "00-map",
              f"父子关系应按记录字段表达,实际 {alpha['request']}")
        check(mgs_records.read_task(root, "02-beta")["request"].get("依赖")
              == "01-alpha", "依赖必须按任务身份表达")
        claimed = mgs_records.claim_task(root, "01-alpha", "agent-a")
        check(claimed["readback"].get("claim") == "agent-a"
              or "agent-a" in (root / config["task_root"] / "01-alpha" / "task.md"
                               ).read_text(encoding="utf-8"),
              "认领必须写入任务记录")
        ready = mgs_records.startable_tasks(root)
        startable = {item["identity"] for item in ready["startable"]}
        blocked = {item["identity"]: item for item in ready["blocked"]}
        check("01-alpha" in startable, "无未完成依赖的 ready-for-agent 应进入可开工集合")
        check("02-beta" in blocked, "依赖未完成不得因分流 ready 而进入可开工集合")
        check(any("依赖未完成" in reason for reason in blocked["02-beta"]["reasons"]),
              f"应说明依赖未完成,实际 {blocked['02-beta']['reasons']}")
        closed = mgs_records.close_task(root, "01-alpha", "不再执行",
                                        note="范围取消")
        check(closed.get("close_reason") == "不再执行", "关闭必须注明原因")
        check("不自动等于验证通过" in closed.get("note", ""),
              "关闭不得被推断为验收通过")
        after = mgs_records.read_task(root, "01-alpha")
        check(after["progress"] == "不再执行",
              f"生命周期应随关闭原因变化,实际 {after['progress']}")
        check(after["triage"] == "ready-for-agent",
              "关闭不得改写分流;分流与生命周期分开")
        ready2 = mgs_records.startable_tasks(root)
        check("01-alpha" not in {i["identity"] for i in ready2["startable"]},
              "已关闭任务不得留在可开工集合")
        result = mgs_records.append_result(root, "02-beta", "中断前已保存草稿。")
        check("results/" in str(result.get("path")),
              "结果应落在任务自己的 results/ 位置")
        beta_dir = root / config["task_root"] / "02-beta"
        check((beta_dir / "task.md").is_file(), "任务正文仍在唯一任务位置")
        check(any((beta_dir / "results").glob("*.md")),
              "结果不得写进规格或任务正文充当第二套状态")


def test_producer_status_is_readonly_and_matt_entries_find_stage_materials() -> None:
    """AC3/T2: 查询不改文件;读真实记录并说明缺项;
    游戏入口与 Matt 入口都能找到当前阶段游戏资料;读取不是开始制作。
    """

    with tempfile.TemporaryDirectory() as tmp:
        root = _onboarded(Path(tmp) / "query")
        mgs_records.create_task(
            root, "01-alpha", "甲",
            {"当前目标": "可查询", "完成标准": "状态可读",
             "执行责任": "Agent(制作实现)"},
            triage="ready-for-agent")
        before = _snapshot(root)
        status = mgs_records.status_report(root)
        check(status["wrote"] is False, "状态查询不得写入")
        check(before == _snapshot(root), "查询前后项目内容必须不变")
        check("01-alpha" in [t["identity"] for t in status["tasks"]],
              "必须读取真实任务记录")
        check(status.get("gaps") or status.get("missing"),
              "应说明缺项(例如尚未建立的规格文件)")
        index = (root / "docs/mygamestudio/INDEX.md").read_text(encoding="utf-8")
        check("stage-requirements.md" in index, "游戏入口应能从 INDEX 找到阶段资料")
        check("读取不是开始制作" in index or "读取资料不是开始制作" in index
              or "不是开始制作" in index,
              "阶段资料指针必须声明读取不是开始制作")
        for name in ("game-producer", "game-init", "implement", "to-spec",
                     "to-tickets"):
            text = (PLUGIN_ROOT / "skills" / name / "SKILL.md").read_text(
                encoding="utf-8")
            check("stage-requirements.md" in text,
                  f"{name} 必须能找到当前阶段游戏资料入口")
            check("docs/mygamestudio/INDEX.md" in text or name in (
                "game-producer", "game-init"),
                  f"Matt 入口 {name} 应能定位项目 INDEX 中的当前阶段资料")


def test_no_gate_overlap_cancel_and_interrupt_keep_results() -> None:
    """AC4/AC5/T10: 无 gate 可完成本地工作;重叠改动保留双方成果;
    取消后不恢复已撤销动作;中断后保存已有成果并只补缺项。
    """

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp) / "recover"
        (root / "src").mkdir(parents=True)
        (root / "src" / "main.js").write_text("ok\n", encoding="utf-8")
        check(not (PLUGIN_ROOT / ".mcp.json").is_file(),
              "普通本地工作不得依赖插件注册 mgs-gate")
        mgs_records.apply_local_onboarding(
            root, mgs_records.plan_local_onboarding(root), confirmed=True)
        created = mgs_records.create_task(
            root, "01-alpha", "甲",
            {"当前目标": "可恢复", "完成标准": "成果保留",
             "执行责任": "Agent(制作实现)"},
            triage="ready-for-agent")
        check(created["created"] is True, "无 gate 也应能记录任务")
        again = mgs_records.create_task(
            root, "01-alpha", "甲",
            {"当前目标": "重复创建", "完成标准": "收养",
             "执行责任": "Agent(制作实现)"},
            triage="ready-for-agent")
        check(again.get("adopted") is True and again.get("created") is False,
              f"重复创建应回读收养,不得新建:{again}")
        path = root / "docs/mygamestudio/work/01-alpha/task.md"
        original = path.read_text(encoding="utf-8")
        sha = hashlib.sha256(original.encode("utf-8")).hexdigest()
        path.write_text(original.replace("进度:待执行", "进度:执行中"),
                        encoding="utf-8")
        try:
            mgs_records.update_task(
                root, "01-alpha", {"当前目标": "被并发覆盖的尝试"},
                expected_body_sha256=sha)
        except mgs_records.RecordsError as exc:
            check("暂停" in str(exc) or "他人" in str(exc) or "修改" in str(exc),
                  f"重叠改动应拒绝覆盖:{exc}")
        else:
            check(False, "无法区分的重叠改动必须暂停覆盖")
        check("执行中" in path.read_text(encoding="utf-8"),
              "并发对方已有成果必须保留")
        overlap = list((root / "docs/mygamestudio/work/01-alpha").glob(
            "task.md.overlap-*"))
        check(overlap, "本侧未落地的改动也要作为重叠成果保留")
        mgs_records.append_result(root, "01-alpha", "中断前已写出的结果。")
        mgs_records.cancel_operation(root, "create_task", "02-cancelled")
        try:
            mgs_records.create_task(
                root, "02-cancelled", "已撤销",
                {"当前目标": "不该恢复", "完成标准": "无",
                 "执行责任": "Agent(制作实现)"})
        except mgs_records.RecordsError as exc:
            check("撤销" in str(exc) or "不得恢复" in str(exc),
                  f"不得恢复已撤销动作:{exc}")
        else:
            check(False, "取消后不得再创建被撤销身份的任务")
        check(not (root / "docs/mygamestudio/work/02-cancelled").exists(),
              "已撤销动作不得被恢复为现行任务")
        (root / "docs/mygamestudio/INDEX.md").unlink()
        resumed = mgs_records.apply_local_onboarding(
            root, mgs_records.plan_local_onboarding(root), confirmed=True)
        check(resumed["ok"] is True, "中断后重读应能补缺项")
        check((root / "docs/mygamestudio/INDEX.md").is_file(),
              "恢复只补缺失的指针文件")
        check("执行中" in path.read_text(encoding="utf-8"),
              "恢复不得改写中断前已保存的任务成果")
        check(any((root / "docs/mygamestudio/work/01-alpha/results").glob("*.md")),
              "中断前结果必须仍在")


def test_cli_onboard_status_and_create_without_gate() -> None:
    """AC5: 正常接入、记录与只读查询可通过 CLI 外部行为检查。"""

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp) / "cli-game"
        root.mkdir()
        (root / "README.md").write_text("# cli-game\n", encoding="utf-8")
        analyze = run_cli("analyze", "--project", str(root))
        check(analyze.returncode == 0, f"CLI analyze 应成功:{analyze.stderr[:200]}")
        check(json.loads(analyze.stdout).get("wrote") is False,
              "CLI 分析必须只读")
        onboard = run_cli("onboard", "--project", str(root), "--confirmed")
        check(onboard.returncode == 0, f"CLI onboard 应成功:{onboard.stderr[:200]}")
        created = run_cli(
            "create", "--project", str(root),
            "--identity", "01-cli", "--title", "CLI 任务",
            "--field", "当前目标=外部行为检查",
            "--field", "完成标准=可回读",
            "--field", "执行责任=Agent(制作实现)",
            "--triage", "ready-for-agent")
        check(created.returncode == 0, f"CLI create 应成功:{created.stderr[:200]}")
        before = _snapshot(root)
        status = run_cli("status", "--project", str(root))
        check(status.returncode == 0, f"CLI status 应成功:{status.stderr[:200]}")
        data = json.loads(status.stdout)
        check(data.get("wrote") is False, "CLI 状态查询不得写入")
        check("01-cli" in [t["identity"] for t in data.get("tasks", [])],
              "CLI 状态查询应读到刚记录的任务")
        check(before == _snapshot(root), "状态查询前后内容不变")


TESTS = (
    test_new_project_onboard_records_and_queries_one_task,
    test_existing_project_reuses_materials_and_flags_conflicts,
    test_tracker_keeps_unique_locations_and_lifecycle,
    test_producer_status_is_readonly_and_matt_entries_find_stage_materials,
    test_no_gate_overlap_cancel_and_interrupt_keep_results,
    test_cli_onboard_status_and_create_without_gate,
)


if __name__ == "__main__":
    sys.exit(run_theme("本地项目接入、任务记录与状态查询(#51)", TESTS, FAILURES))

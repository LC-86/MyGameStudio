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
import threading
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


def test_concurrent_same_sha_updates_keep_overlap_artifact() -> None:
    """T10: 两个会话用同一 expected sha 同时更新时,后到者不得静默覆盖,
    必须留下重叠成果。
    """

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp) / "recover"
        (root / "src").mkdir(parents=True)
        (root / "src" / "main.js").write_text("ok\n", encoding="utf-8")
        mgs_records.apply_local_onboarding(
            root, mgs_records.plan_local_onboarding(root), confirmed=True)
        mgs_records.create_task(
            root, "01-alpha", "甲",
            {"当前目标": "初始目标", "完成标准": "并发可核对",
             "执行责任": "Agent(制作实现)"},
            triage="ready-for-agent")
        path = root / "docs/mygamestudio/work/01-alpha/task.md"
        sha = hashlib.sha256(path.read_bytes()).hexdigest()
        barrier = threading.Barrier(2)
        outcomes: list[str] = []
        lock = threading.Lock()

        def worker(goal: str) -> None:
            barrier.wait()
            try:
                mgs_records.update_task(
                    root, "01-alpha", {"当前目标": goal},
                    expected_body_sha256=sha)
                with lock:
                    outcomes.append("published:" + goal)
            except mgs_records.RecordsError:
                with lock:
                    outcomes.append("overlap")

        threads = [
            threading.Thread(target=worker, args=("会话甲目标",)),
            threading.Thread(target=worker, args=("会话乙目标",)),
        ]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join()
        body = path.read_text(encoding="utf-8")
        published = [item for item in outcomes if item.startswith("published:")]
        check(len(published) == 1,
              f"同一 sha 的并发更新只应有一方落地,实际 {outcomes}")
        check("overlap" in outcomes or list(
            (root / "docs/mygamestudio/work/01-alpha").glob("task.md.overlap-*")),
              f"未落地一方必须保留重叠成果,实际 {outcomes}")
        check("会话甲目标" in body or "会话乙目标" in body,
              "落地一方的目标必须可回读")
        check(not ("会话甲目标" in body and "会话乙目标" in body),
              "不得把两次更新混写成一份正文")


def test_concurrent_result_appends_keep_both_deliveries() -> None:
    """T10: 两会话同时向同一任务追加结果必须串行化:两个结果文件与
    两条索引行都保留,不得共用文件名互相覆盖后仍报告成功。
    """

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp) / "deliver"
        (root / "src").mkdir(parents=True)
        (root / "src" / "main.js").write_text("ok\n", encoding="utf-8")
        mgs_records.apply_local_onboarding(
            root, mgs_records.plan_local_onboarding(root), confirmed=True)
        mgs_records.create_task(
            root, "01-alpha", "甲",
            {"当前目标": "并发投递", "完成标准": "两份结果都保留",
             "执行责任": "Agent(制作实现)"},
            triage="ready-for-agent")
        barrier = threading.Barrier(2)

        def worker(content: str) -> None:
            barrier.wait()
            mgs_records.append_result(root, "01-alpha", content)

        threads = [
            threading.Thread(target=worker, args=("会话甲结果:第一份证据",)),
            threading.Thread(target=worker, args=("会话乙结果:第二份证据",)),
        ]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join()
        results_dir = root / "docs/mygamestudio/work/01-alpha/results"
        files = sorted(p.name for p in results_dir.glob("*.md"))
        check(len(files) == 2,
              f"并发投递必须留下两个结果文件,实际 {files}")
        bodies = "".join(p.read_text(encoding="utf-8")
                         for p in results_dir.glob("*.md"))
        check("第一份证据" in bodies and "第二份证据" in bodies,
              "两份结果内容都必须保留,不得互相覆盖")
        task = mgs_records.read_task(root, "01-alpha")
        index_text = task.get("result_index_text") or ""
        listed = [line for line in index_text.splitlines()
                  if line.startswith("- results/")]
        check(len(listed) == 2, f"结果索引必须包含两行,实际 {index_text!r}")
        check(all(name in index_text for name in files),
              "两个结果文件都必须出现在索引里")


def test_local_task_identity_cannot_escape_task_root() -> None:
    """T4: 除 create 外的本地操作也必须校验任务身份,绝对路径或穿越
    不得读写任务根之外的文件。
    """

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp) / "escape"
        (root / "src").mkdir(parents=True)
        (root / "src" / "main.js").write_text("ok\n", encoding="utf-8")
        mgs_records.apply_local_onboarding(
            root, mgs_records.plan_local_onboarding(root), confirmed=True)
        mgs_records.create_task(
            root, "01-alpha", "甲",
            {"当前目标": "合法任务", "完成标准": "可回读",
             "执行责任": "Agent(制作实现)"},
            triage="ready-for-agent")
        victim = Path(tmp) / "victim"
        victim.mkdir()
        victim_task = victim / "task.md"
        victim_task.write_text("不得覆盖\n", encoding="utf-8")
        try:
            mgs_records.update_task(
                root, str(victim), {"当前目标": "越权写入"})
        except mgs_records.RecordsError:
            pass
        else:
            check(False, "绝对路径身份必须拒绝")
        check(victim_task.read_text(encoding="utf-8") == "不得覆盖\n",
              "越权身份不得改写任务根之外的文件")
        try:
            mgs_records.read_task(root, "../../victim")
        except mgs_records.RecordsError:
            pass
        else:
            check(False, "穿越身份必须拒绝")
        original = mgs_records.read_task(root, "01-alpha")
        check(original.get("identity") == "01-alpha",
              "合法身份仍应可读")


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


def test_cli_onboard_honors_custom_config_path() -> None:
    """onboard --config 指向非默认配置时必须沿用该路径;
    不得在默认路径再建第二套 tracker 权威。"""

    from records_backend_support import CONFIG_TEMPLATE, FIVE_LABELS

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp) / "cfg-game"
        root.mkdir(parents=True)
        (root / "README.md").write_text("# cfg-game\n", encoding="utf-8")
        custom_rel = "docs/mygamestudio/records/CONFIG-alt.md"
        custom_path = root / custom_rel
        custom_path.parent.mkdir(parents=True)
        label_rows = "\n".join(f"| {name} | {name} |" for name in FIVE_LABELS)
        custom_path.write_text(
            CONFIG_TEMPLATE.format(
                backend="local-markdown",
                location="docs/mygamestudio/work/", label_rows=label_rows),
            encoding="utf-8")
        before = custom_path.read_text(encoding="utf-8")
        onboard = run_cli("onboard", "--project", str(root),
                          "--config", custom_rel, "--confirmed")
        check(onboard.returncode == 0,
              f"自定义配置路径的接入应成功:{onboard.stderr[:300]}")
        payload = json.loads(onboard.stdout)
        default_path = root / "docs/mygamestudio/CONFIG.md"
        check(not default_path.exists(),
              "默认路径不得出现第二套协作配置权威")
        rows = {row.get("path"): row.get("result")
                for row in payload.get("results", [])}
        check(rows.get(custom_rel) == "复用",
              f"自定义路径的既有有效配置必须被复用,实际 {rows.get(custom_rel)}")
        check(custom_path.read_text(encoding="utf-8") == before,
              "复用不得改写既有配置正文")


def test_malformed_config_is_rejected_not_reused_by_onboarding() -> None:
    """现有 CONFIG.md 无法解析时,接入必须拒绝而不是当作无配置复用。"""

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp) / "broken"
        root.mkdir(parents=True)
        (root / "README.md").write_text("# broken\n", encoding="utf-8")
        config_path = root / "docs/mygamestudio/CONFIG.md"
        config_path.parent.mkdir(parents=True)
        config_path.write_text("# 协作配置\n\n没有任务来源章节,无法解析。\n",
                               encoding="utf-8")
        before = config_path.read_text(encoding="utf-8")

        planned = mgs_records.plan_local_onboarding(root)
        check(planned.get("ok") is False,
              f"损坏配置不得进入接入清单:{planned}")
        check("无法解析" in str(planned.get("reason") or ""),
              f"必须说明解析失败原因:{planned.get('reason')}")
        items = {(item or {}).get("path") for item in planned.get("items") or []}
        check("docs/mygamestudio/CONFIG.md" not in items,
              "损坏配置不得被标记为复用")

        applied = mgs_records.apply_local_onboarding(root, planned,
                                                     confirmed=True)
        check(applied.get("ok") is False,
              f"应用阶段同样必须拒绝:{applied}")
        check(config_path.read_text(encoding="utf-8") == before,
              "拒绝路径不得改写现有文件")

        from github_backend_fixtures import AUTH, REPO
        gh_plan = mgs_records.plan_github_onboarding(
            root, repo=REPO, authorization=AUTH)
        check(gh_plan.get("ok") is False,
              f"GitHub 接入同样不得复用损坏配置:{gh_plan}")


def test_concurrent_creation_of_same_identity_has_single_winner() -> None:
    """并发创建同一身份:只有一个请求真正落盘,其余收养胜者。"""

    with tempfile.TemporaryDirectory() as tmp:
        root = _onboarded(Path(tmp) / "race-create")
        barrier = threading.Barrier(6)
        collected: list[dict] = []
        guard = threading.Lock()

        def worker(index: int) -> None:
            barrier.wait()
            outcome = mgs_records.create_task(
                root, "09-race", f"并发创建第 {index} 名",
                _task_request("并发创建同一身份"))
            with guard:
                collected.append(outcome)

        threads = [threading.Thread(target=worker, args=(index,))
                   for index in range(6)]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join()
        created = [item for item in collected if item.get("created") is True]
        check(len(created) == 1,
              f"同一身份并发创建只能有一个 created=True,实际 {len(created)}")
        check(all(item.get("duplicate_avoided") is True
                  for item in collected if item.get("created") is not True),
              "未胜出的创建必须收养既有任务而不是互相覆盖")
        readback = mgs_records.read_task(root, "09-race")
        check(readback.get("identity") == "09-race",
              f"并发创建后任务必须可回读,实际 {readback.get('identity')!r}")
        check("任务身份:09-race" in (root / "docs/mygamestudio/work/09-race"
                                    / "task.md").read_text(encoding="utf-8"),
              "胜者正文必须完整落在唯一任务位置")


def test_concurrent_distinct_claims_keep_single_holder() -> None:
    """并发认领同一未认领任务:认领检查必须与写入同锁,只留一个持有人。"""

    with tempfile.TemporaryDirectory() as tmp:
        root = _onboarded(Path(tmp) / "race-claim")
        mgs_records.create_task(
            root, "10-claim", "并发认领", _task_request("并发认领同一任务"),
            triage="ready-for-agent")
        actors = ["agent-a", "agent-b", "agent-c", "agent-d", "agent-e"]
        barrier = threading.Barrier(len(actors))
        winners: list[str] = []
        guard = threading.Lock()

        def worker(actor: str) -> None:
            barrier.wait()
            try:
                mgs_records.claim_task(root, "10-claim", actor)
                with guard:
                    winners.append(actor)
            except mgs_records.RecordsError:
                return

        threads = [threading.Thread(target=worker, args=(actor,))
                   for actor in actors]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join()
        check(len(winners) == 1,
              f"并发认领只能成功一人,实际 {winners}")
        task = mgs_records.read_task(root, "10-claim")
        check(task.get("claim") == winners[0],
              f"任务持有人必须是唯一胜者,实际 {task.get('claim')!r}")
        others = [actor for actor in actors if actor != winners[0]]
        check(all(actor not in (root / "docs/mygamestudio/work/10-claim"
                                / "task.md").read_text(encoding="utf-8")
                  for actor in others),
              "未胜者的认领不得覆盖或追加到任务正文")


TESTS = (
    test_new_project_onboard_records_and_queries_one_task,
    test_existing_project_reuses_materials_and_flags_conflicts,
    test_tracker_keeps_unique_locations_and_lifecycle,
    test_producer_status_is_readonly_and_matt_entries_find_stage_materials,
    test_no_gate_overlap_cancel_and_interrupt_keep_results,
    test_concurrent_same_sha_updates_keep_overlap_artifact,
    test_concurrent_result_appends_keep_both_deliveries,
    test_local_task_identity_cannot_escape_task_root,
    test_cli_onboard_status_and_create_without_gate,
    test_cli_onboard_honors_custom_config_path,
    test_malformed_config_is_rejected_not_reused_by_onboarding,
    test_concurrent_creation_of_same_identity_has_single_winner,
    test_concurrent_distinct_claims_keep_single_holder,
)


if __name__ == "__main__":
    sys.exit(run_theme("本地项目接入、任务记录与状态查询(#51)", TESTS, FAILURES))

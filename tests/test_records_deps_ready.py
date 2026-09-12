#!/usr/bin/env python3
"""依赖解析与可开工集合。

任务票 11 从 tests/test_records_backend.py 按真实行为主题拆出;检查含义与原
案例保持一致,仅重组位置。原总入口仍聚合本主题。本主题可直接运行:

    python3 -B tests/test_records_deps_ready.py
"""

import json
import sys
import tempfile
from pathlib import Path

from records_backend_support import (
    PLAN_TASK_TEMPLATE, counted_config_reads, make_checker,
    make_config_selfmap_project, make_plan_project, make_project,
    run_cli, run_theme, scoped_read_counter,
)

import mgs_records  # noqa: E402

FAILURES, check = make_checker()


def test_parse_dep_ids_ignores_dates() -> None:
    """依赖字段中的日期等长数字串不应被截断误读为任务身份(任务票 08)。

    身份约定为 NN-<slug>(编号至多三位);「2026-09-08 建立」这类日期文本
    若从数字中间开始匹配会得到假身份 026-09-08,进而制造假的未解析依赖。
    """

    cases = {
        "无": [],
        "04-shell-combo、06-gull-sprite": ["04-shell-combo", "06-gull-sprite"],
        "05-gull-swoop(集成完成)": ["05-gull-swoop"],
        "无(2026-09-08 拆单轮建立)": [],
        "2026-09-08 建立": [],
        "": [],
    }
    for value, expected in cases.items():
        actual = mgs_records._parse_dep_ids(value)
        check(actual == expected,
              f"依赖字段 {value!r} 应解析为 {expected},实际 {actual}")


def test_task_dependencies_graph() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = make_plan_project(Path(tmp))
        report = mgs_records.task_dependencies(root)
        edges = report["edges"]
        check(edges.get("02-beta") == ["01-alpha"], f"02-beta 应依赖 01-alpha,实际 {edges.get('02-beta')}")
        check(edges.get("04-delta") == ["01-alpha-done"],
              f"04-delta 应依赖 01-alpha-done,实际 {edges.get('04-delta')}")
        check(report["unresolved"] == [] and report["cycles"] == [],
              f"健康拆单不应有未解析依赖或循环:{report}")
        check(report["ok"] is True, "健康拆单 deps 应 ok")
        identities = {t["identity"] for t in mgs_records.list_tasks(root)}
        check(set(edges) <= identities, "deps 边的键应为实际任务身份")


def test_task_dependencies_unresolved_and_cycle() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = make_plan_project(Path(tmp))
        docs = root / "docs" / "mygamestudio" / "work"
        (docs / "02-beta" / "task.md").write_text(
            (docs / "02-beta" / "task.md").read_text(encoding="utf-8").replace(
                "- 依赖:01-alpha", "- 依赖:99-missing"),
            encoding="utf-8")
        report = mgs_records.task_dependencies(root)
        check(any(item["dep"] == "99-missing" and item["identity"] == "02-beta"
                  for item in report["unresolved"]),
              f"引用不存在任务应报未解析,实际 {report['unresolved']}")
        check(report["ok"] is False, "存在未解析依赖时 deps 不应 ok")
    with tempfile.TemporaryDirectory() as tmp:
        root = make_plan_project(Path(tmp))
        docs = root / "docs" / "mygamestudio" / "work"
        # 01-alpha 与 02-beta 互为依赖 → 循环
        (docs / "01-alpha" / "task.md").write_text(
            (docs / "01-alpha" / "task.md").read_text(encoding="utf-8").replace(
                "- 依赖:无", "- 依赖:02-beta"),
            encoding="utf-8")
        report = mgs_records.task_dependencies(root)
        check(len(report["cycles"]) >= 1, f"互相依赖应检测出循环,实际 {report['cycles']}")
        check(report["ok"] is False, "存在循环时 deps 不应 ok")


def test_startable_tasks_set() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = make_plan_project(Path(tmp))
        report = mgs_records.startable_tasks(root)
        startable = {item["identity"]: item for item in report["startable"]}
        blocked = {item["identity"]: item for item in report["blocked"]}
        check("01-alpha" in startable, f"无未完成依赖的 ready-for-agent 任务应可开工,实际 {sorted(startable)}")
        check("04-delta" in startable and startable["04-delta"].get("executor") == "Human(开发者)",
              "依赖已完成的 ready-for-human 任务应可开工并标注 Human 执行")
        # 关键语义:ready-for-agent 标签不等于可开工——依赖未完成仍被排除
        check("02-beta" in blocked,
              "依赖未完成的任务即使 ready-for-agent 也应列为不可开工")
        check(any("依赖未完成" in reason for reason in blocked["02-beta"]["reasons"]),
              f"02-beta 应给出依赖未完成原因,实际 {blocked['02-beta']['reasons']}")
        check(any("输入不足" in reason or "needs-info" in reason
                  for reason in blocked["03-gamma"]["reasons"]),
              f"needs-info 任务应给出输入不足原因,实际 {blocked['03-gamma']['reasons']}")
        check(any("能力未就绪" in reason for reason in blocked["05-epsilon"]["reasons"]),
              f"所需能力命中 CONFIG 未就绪项应给出原因,实际 {blocked['05-epsilon']['reasons']}")
        check(any("版本" in reason for reason in blocked["06-zeta"]["reasons"]),
              f"基线引用 v1 而当前 v2 应给出版本漂移原因,实际 {blocked['06-zeta']['reasons']}")
        check("授权" in report["note"],
              "ready 输出必须声明可开工不等于已获写入授权")


def test_capability_negation_not_flagged() -> None:
    """否定式能力表述(不需要/无需/均已就绪)不应误报能力未就绪(任务票 08)。"""

    with tempfile.TemporaryDirectory() as tmp:
        root = make_plan_project(Path(tmp))
        task_path = root / "docs" / "mygamestudio" / "work" / "05-epsilon" / "task.md"
        current = "- 所需能力:音频提示制作"

        def set_capability(phrase: str) -> list[str]:
            nonlocal current
            task_path.write_text(
                task_path.read_text(encoding="utf-8").replace(current,
                                                              f"- 所需能力:{phrase}"),
                encoding="utf-8")
            current = f"- 所需能力:{phrase}"
            report = mgs_records.startable_tasks(root)
            for item in report["blocked"] + report["startable"]:
                if item["identity"] == "05-epsilon":
                    return item["reasons"]
            raise AssertionError("05-epsilon 未出现在 ready 输出中")

        for phrase in ("本任务不需要音频制作能力", "无需音频,纯视觉实现",
                       "所需能力均已就绪(CONFIG v2)"):
            reasons = set_capability(phrase)
            check(not any("能力未就绪" in reason for reason in reasons),
                  f"否定式表述「{phrase}」不应报能力未就绪,实际 {reasons}")
        # 条件式/正面提及仍应命中
        for phrase in ("若采用音频提示则未就绪", "音频提示制作"):
            reasons = set_capability(phrase)
            check(any("能力未就绪" in reason for reason in reasons),
                  f"表述「{phrase}」应报能力未就绪,实际 {reasons}")


def test_startable_ignores_done_and_wontfix() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = make_plan_project(Path(tmp))
        docs = root / "docs" / "mygamestudio" / "work"
        (docs / "01-alpha" / "task.md").write_text(
            (docs / "01-alpha" / "task.md").read_text(encoding="utf-8").replace(
                "当前分流:ready-for-agent。进度:待执行",
                "当前分流:wontfix。进度:不再执行"),
            encoding="utf-8")
        report = mgs_records.startable_tasks(root)
        identities = {item["identity"] for item in report["startable"]}
        check("01-alpha" not in identities, "wontfix 任务不应进入可开工集合")
        blocked = {item["identity"] for item in report["blocked"]}
        check("01-alpha" in blocked, "wontfix 任务应在不可开工侧可见并给出原因")
        check("01-alpha-done" not in identities, "已完成任务不应进入可开工集合")


def test_verify_deps_consistent() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = make_plan_project(Path(tmp))
        report = mgs_records.verify_project(root)
        check(report["ok"], f"健康拆单项目应整体通过 verify:{report['checks']}")
    with tempfile.TemporaryDirectory() as tmp:
        root = make_plan_project(Path(tmp))
        docs = root / "docs" / "mygamestudio" / "work"
        (docs / "01-alpha" / "task.md").write_text(
            (docs / "01-alpha" / "task.md").read_text(encoding="utf-8").replace(
                "- 依赖:无", "- 依赖:02-beta"),
            encoding="utf-8")
        failed = {c["name"] for c in mgs_records.verify_project(root)["checks"] if not c["ok"]}
        check("deps-consistent" in failed, f"循环依赖应判 deps-consistent 失败,实际 {failed}")


def test_cli_deps_and_ready() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = make_plan_project(Path(tmp))
        result = run_cli("deps", "--project", str(root))
        check(result.returncode == 0, f"CLI deps 健康项目应退出 0:{result.stderr[:200]}")
        data = json.loads(result.stdout)
        check(data["ok"] is True and data["edges"].get("02-beta") == ["01-alpha"],
              "CLI deps 应回报依赖边")
        result = run_cli("ready", "--project", str(root))
        check(result.returncode == 0, f"CLI ready 应退出 0:{result.stderr[:200]}")
        data = json.loads(result.stdout)
        identities = {item["identity"] for item in data["startable"]}
        check("01-alpha" in identities and "02-beta" not in identities,
              "CLI ready 应区分可开工与不可开工")
        check("授权" in data["note"], "CLI ready 输出应含授权核对提示")
    with tempfile.TemporaryDirectory() as tmp:
        root = make_plan_project(Path(tmp))
        docs = root / "docs" / "mygamestudio" / "work"
        (docs / "02-beta" / "task.md").write_text(
            (docs / "02-beta" / "task.md").read_text(encoding="utf-8").replace(
                "- 依赖:01-alpha", "- 依赖:99-missing"),
            encoding="utf-8")
        result = run_cli("deps", "--project", str(root))
        check(result.returncode == 1, "CLI deps 存在未解析依赖应以退出码 1 表达")


def test_ready_reads_config_and_each_task_once() -> None:
    """READ-01:本地正常 ready 只读 CONFIG 原文一次、每份 task.md 一次;

    静态输入下的最终分类与既有语义一致(不含被替换前的二次读取)。
    """

    with tempfile.TemporaryDirectory() as tmp:
        root = make_plan_project(Path(tmp))
        with scoped_read_counter(root) as counter:
            report = mgs_records.startable_tasks(root)
        check(counter.config_reads() == 1,
              f"ready 应只读 CONFIG 原文一次,实际 {counter.by_path}")
        task_reads = counter.task_reads()
        check(task_reads and all(n == 1 for n in task_reads.values())
              and len(task_reads) == 7,
              f"ready 每份 task.md 应恰好读一次,实际 {task_reads}")
        startable = {i["identity"] for i in report["startable"]}
        blocked = {i["identity"] for i in report["blocked"]}
        check(startable == {"01-alpha", "04-delta"} and blocked == set(
            {"01-alpha-done", "02-beta", "03-gamma", "05-epsilon", "06-zeta"}),
            f"静态输入下最终分类应保持,实际 startable={sorted(startable)} "
            f"blocked={sorted(blocked)}")


def test_deps_reads_once_and_ready_does_not_recall_public_dependency_entry() -> None:
    """READ-01/依赖纪律:依赖由本次唯一任务集合生成,ready 不再回调公开依赖入口。

    ① task_dependencies 自身只读 CONFIG 一次、每份 task.md 一次;
    ② ready 期间把公开依赖入口替换为哨兵,证明它没有被 ready 调用。
    """

    with tempfile.TemporaryDirectory() as tmp:
        root = make_plan_project(Path(tmp))
        with scoped_read_counter(root) as counter:
            graph = mgs_records.task_dependencies(root)
        check(counter.config_reads() == 1,
              f"deps 应只读 CONFIG 一次,实际 {counter.by_path}")
        deps_reads = counter.task_reads()
        check(deps_reads and all(n == 1 for n in deps_reads.values()),
              f"deps 每份 task.md 应恰好读一次,实际 {deps_reads}")
        check(graph["edges"].get("02-beta") == ["01-alpha"],
              f"deps 依赖边应保持,实际 {graph['edges']}")

        calls: list[str] = []
        real = mgs_records.task_dependencies

        def sentinel(*args, **kwargs):
            calls.append("called")
            raise AssertionError("ready 不应回调公开依赖入口重新获取任务")

        mgs_records.task_dependencies = sentinel
        try:
            report = mgs_records.startable_tasks(root)
        finally:
            mgs_records.task_dependencies = real
        check(calls == [],
              "ready 不得回调公开依赖入口(否则会二次获取任务集合)")
        blocked = {i["identity"]: i for i in report["blocked"]}
        check(any("依赖未完成" in r for r in blocked["02-beta"]["reasons"]),
              f"依赖判断仍应使用同一集合给出未完成原因,实际 {blocked['02-beta']}")


def test_ready_second_call_reflects_changes_without_cross_call_cache() -> None:
    """READ-04/R1:两次顶层调用之间修改任务与配置都会影响第二次结果。

    第二次调用重新读取(非缓存),分类随新依赖更新;不存在跨调用复用。
    """

    with tempfile.TemporaryDirectory() as tmp:
        root = make_plan_project(Path(tmp))
        first = mgs_records.startable_tasks(root)
        check("01-alpha" in {i["identity"] for i in first["startable"]},
              "初始 01-alpha 无依赖应可开工")

        def first_call(task: dict) -> tuple[set[str], set[str]]:
            return ({i["identity"] for i in task["startable"]},
                    {i["identity"] for i in task["blocked"]})

        # 第一次调用后新增一个不存在的依赖 → 第二次应看到并转为不可开工
        task_path = root / "docs" / "mygamestudio" / "work" / "01-alpha" / "task.md"
        task_path.write_text(
            task_path.read_text(encoding="utf-8").replace(
                "- 依赖:无", "- 依赖:02-missing"), encoding="utf-8")
        second = mgs_records.startable_tasks(root)
        startable, blocked = first_call(second)
        check("01-alpha" not in startable and "01-alpha" in blocked,
              f"第二次调用应看到新依赖并把 01-alpha 转为不可开工,实际 {second}")
        entry = next(i for i in second["blocked"] if i["identity"] == "01-alpha")
        check(any("依赖未解析:02-missing" in r for r in entry["reasons"]),
              f"第二次应报告新依赖未解析,实际 {entry['reasons']}")

        # 再改 CONFIG(未就绪能力)影响第二次调用之后的第三次结果
        config_path = root / "docs" / "mygamestudio" / "CONFIG.md"
        config_path.write_text(
            config_path.read_text(encoding="utf-8").replace(
                "- 尚未就绪的能力及影响:无",
                "- 尚未就绪的能力及影响:音频制作能力未就绪"),
            encoding="utf-8")
        third = mgs_records.startable_tasks(root)
        epsilon = next((i for i in third["blocked"] + third["startable"]
                        if i["identity"] == "05-epsilon"), None)
        check(epsilon is not None and any("能力未就绪" in r
                                          for r in epsilon["reasons"]),
              f"第三次调用应读到新 CONFIG 能力缺口,实际 {epsilon}")


def test_ready_and_deps_preserve_directory_order() -> None:
    """READ-06:本地 ready/deps 沿目录顺序;list 排序副本不污染其他判断。

    目录名与正文身份刻意相反:dep 边顺序应保持目录顺序而非身份排序。
    """

    with tempfile.TemporaryDirectory() as tmp:
        root = make_project(Path(tmp), extra_task=False)
        docs = root / "docs" / "mygamestudio" / "work"
        # 目录 05-zzz 的正文身份为 02-aaa;目录 02-aaa 的正文身份为 05-zzz
        (docs / "05-zzz").mkdir(parents=True)
        (docs / "05-zzz" / "task.md").write_text(
            PLAN_TASK_TEMPLATE.format(
                title="目录序一", identity="02-aaa", triage="ready-for-agent",
                progress="待执行", goal="目标", deliver="交付", scope="src/**",
                capability="文件读写", executor="Agent(制作实现)",
                acceptance="检查", deps="无", coordination="无", missing="无",
                index="(暂无)"), encoding="utf-8")
        (docs / "02-aaa").mkdir(parents=True)
        (docs / "02-aaa" / "task.md").write_text(
            PLAN_TASK_TEMPLATE.format(
                title="目录序二", identity="05-zzz", triage="ready-for-agent",
                progress="待执行", goal="目标", deliver="交付", scope="src/**",
                capability="文件读写", executor="Agent(制作实现)",
                acceptance="检查", deps="无", coordination="无", missing="无",
                index="(暂无)"), encoding="utf-8")
        # 目录顺序:02-aaa(正文身份 05-zzz)在前,05-zzz(正文身份 02-aaa)在后
        deps = mgs_records.task_dependencies(root)
        check(list(deps["edges"].keys()) == ["05-zzz", "02-aaa"],
              f"deps 应沿目录顺序(02-aaa 目录的正文身份 05-zzz 在前),"
              f"实际 {list(deps['edges'])}")
        ready = mgs_records.startable_tasks(root)
        check([i["identity"] for i in ready["startable"]] == ["05-zzz", "02-aaa"],
              f"ready 应沿目录顺序输出,实际 "
              f"{[i['identity'] for i in ready['startable']]}")
        # list 按目录排序的投影不改变 deps/ready 的来源顺序
        listed = [t["directory"] for t in mgs_records.list_tasks(root)]
        check(listed == ["02-aaa", "05-zzz"],
              f"list 应按目录排序,实际 {listed}")
        deps_again = mgs_records.task_dependencies(root)
        check(list(deps_again["edges"].keys()) == ["05-zzz", "02-aaa"],
              "list 的排序副本不得原地污染 deps 的来源顺序")

def test_config_self_mapping_ready_reuses_first_read() -> None:
    """spec 9:CONFIG 自映射时 ready 复用顶层已读原文(R2-SP-1)。

    同一次 startable_tasks 内,CONFIG 由 _read_workspace 读取一次;文档映射
    自映射行不得再读一遍。首读后同次把 CONFIG 改为 v2:读两次会按第二次
    原文判出「CONFIG 当前 v2,任务引用 v1」假漂移并把任务放入 blocked;
    修复后任务正常 startable;下一次调用重新读取,如实反映 v2。
    """

    with tempfile.TemporaryDirectory() as tmp:
        root = make_config_selfmap_project(Path(tmp))
        config_path = root / "docs" / "mygamestudio" / "CONFIG.md"
        rewritten = config_path.read_text(encoding="utf-8").replace(
            "基线版本:v1。", "基线版本:v2。")

        with counted_config_reads(config_path, rewritten) as reads:
            result = mgs_records.startable_tasks(root)
        check(reads["count"] == 1,
              f"CONFIG 自映射时应复用顶层已读原文、只实际读取一次,"
              f"实际 {reads['count']} 次")
        identities = {item["identity"] for item in result["startable"]}
        check("08-config-ref" in identities,
              f"任务引用 v1 与本次已读原文一致,应可开工;blocked 侧: "
              f"{[b for b in result['blocked'] if b['identity'] == '08-config-ref']}")

        # 下一次顶层调用重新读取:磁盘已是 v2,任务应因版本漂移进入 blocked。
        second = mgs_records.startable_tasks(root)
        blocked = {item["identity"]: item for item in second["blocked"]}
        entry = blocked.get("08-config-ref", {})
        check(any("当前 v2" in reason and "引用 v1" in reason
                  for reason in entry.get("reasons", [])),
              f"下一次调用应按 v2 报告版本漂移,实际 {entry}")


TESTS = (
    test_parse_dep_ids_ignores_dates,
    test_task_dependencies_graph,
    test_task_dependencies_unresolved_and_cycle,
    test_startable_tasks_set,
    test_capability_negation_not_flagged,
    test_startable_ignores_done_and_wontfix,
    test_verify_deps_consistent,
    test_cli_deps_and_ready,
    test_ready_reads_config_and_each_task_once,
    test_deps_reads_once_and_ready_does_not_recall_public_dependency_entry,
    test_ready_second_call_reflects_changes_without_cross_call_cache,
    test_ready_and_deps_preserve_directory_order,
    test_config_self_mapping_ready_reuses_first_read,
)

if __name__ == "__main__":
    sys.exit(run_theme("依赖解析与可开工集合", TESTS, FAILURES))

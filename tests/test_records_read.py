#!/usr/bin/env python3
"""本地后端读取(配置/列表/单任务)。

任务票 11 从 tests/test_records_backend.py 按真实行为主题拆出;检查含义与原
案例保持一致,仅重组位置。原总入口仍聚合本主题。本主题可直接运行:

    python3 -B tests/test_records_read.py
"""

import json
import sys
import tempfile
from pathlib import Path

from records_backend_support import (
    FIVE_LABELS, PLAN_TASK_TEMPLATE, SAMPLE, make_checker, make_plan_project,
    make_project, run_cli, run_theme, scoped_read_counter,
)

import mgs_records  # noqa: E402

FAILURES, check = make_checker()


def test_load_config_on_sample() -> None:
    config = mgs_records.load_config(SAMPLE)
    check(config["backend"] == "local-markdown",
          f"样例后端应为 local-markdown,实际 {config['backend']}")
    check(config["task_root"] == "docs/mygamestudio/work",
          f"样例任务根应为 docs/mygamestudio/work,实际 {config['task_root']}")
    check(tuple(sorted(config["labels"])) == tuple(sorted(FIVE_LABELS)),
          f"样例五类标签应完整,实际 {sorted(config['labels'])}")
    roles = {row["role"] for row in config["docmap"]}
    check({"制作统筹", "方案设计", "制作实现"} <= roles,
          f"样例文档映射应含三类维护角色,实际 {roles}")


def test_load_config_missing() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        try:
            mgs_records.load_config(Path(tmp))
        except mgs_records.RecordsError as exc:
            check("CONFIG" in str(exc), f"缺失配置的错误应指向 CONFIG:{exc}")
        else:
            check(False, "缺失 CONFIG 应抛 RecordsError")


def test_unsupported_backend() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        make_project(Path(tmp), backend="gitlab-issues")
        config = mgs_records.load_config(Path(tmp))
        check(config["backend"] == "gitlab-issues", "load_config 应原样回报后端")
        try:
            mgs_records.list_tasks(Path(tmp))
        except mgs_records.RecordsError:
            check(True, "")
        else:
            check(False, "未实现后端执行任务操作应报不支持")


def test_github_backend_does_not_read_local_tasks() -> None:
    """任务票 17:github-issues 后端的任务操作走远端,不读本地 work/ 目录,
    远端不可用时报错并声明不静默切本地,而不是回退读取本地任务。"""

    with tempfile.TemporaryDirectory() as tmp:
        root = make_project(Path(tmp), backend="github-issues",
                            repo="github.com/mygamestudio/issue-accept")
        config = mgs_records.load_config(root)
        check(config["backend"] == "github-issues"
              and config["repo"]["repo"] == "issue-accept",
              "github 后端配置应解析出仓库坐标")
        try:
            mgs_records.list_tasks(root)
        except mgs_records.RecordsError as exc:
            message = str(exc)
            check("远端" in message or "缓存" in message,
                  f"github 后端不可用错误应说明远端/缓存:{message}")
            check("docs/mygamestudio/work" not in message,
                  "错误不应指向本地任务根(不静默切本地)")
        else:
            check(False, "远端不可用且无缓存时应报错,而非返回本地任务")


def test_list_tasks_on_sample() -> None:
    tasks = mgs_records.list_tasks(SAMPLE)
    ids = [task["identity"] for task in tasks]
    check(ids == ["01-status-ledger", "02-coin-magnet", "03-dash-prototype"],
          f"样例任务身份应为三个且有序,实际 {ids}")
    check(all(task["triage"] in FIVE_LABELS for task in tasks),
          "样例任务分流应都在五类之内")
    check(all(task["title"] for task in tasks), "样例任务标题应非空")


def test_list_tasks_empty_root() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = make_project(Path(tmp), extra_task=False)
        check(mgs_records.list_tasks(root) == [], "无任务时应返回空列表")


def test_read_task() -> None:
    task = mgs_records.read_task(SAMPLE, "02-coin-magnet")
    check(task["identity"] == "02-coin-magnet", "任务身份应原样回读")
    check(task["progress"] == "待做", f"样例进度应为待做,实际 {task['progress']}")
    for key in ("当前目标", "完成标准", "执行责任"):
        check(key in task["request"], f"工作请求应含 {key}")
    for section in ("工作请求", "结果索引", "状态变化"):
        check(task["sections"].get(section, False), f"任务应含 {section} 小节")
    check(task["results"] == [], "样例 02 任务应无结果文件")
    try:
        mgs_records.read_task(SAMPLE, "99-missing")
    except mgs_records.RecordsError:
        check(True, "")
    else:
        check(False, "读取不存在的任务应报错")


def test_cli() -> None:
    result = run_cli("config", "--project", str(SAMPLE))
    check(result.returncode == 0, f"CLI config 应成功:{result.stderr[:200]}")
    data = json.loads(result.stdout)
    check(data["backend"] == "local-markdown", "CLI config 应回报后端")
    result = run_cli("list", "--project", str(SAMPLE))
    ids = [t["identity"] for t in json.loads(result.stdout)]
    check("02-coin-magnet" in ids, "CLI list 应列出任务")
    result = run_cli("show", "--project", str(SAMPLE), "--task", "02-coin-magnet")
    check(json.loads(result.stdout)["identity"] == "02-coin-magnet", "CLI show 应回读任务")
    result = run_cli("verify", "--project", str(SAMPLE))
    check(result.returncode == 0, "CLI verify 对健康样例应退出 0")
    check(json.loads(result.stdout)["ok"] is True, "CLI verify 应回报 ok")
    with tempfile.TemporaryDirectory() as tmp:
        root = make_project(Path(tmp), with_core_docs=False)
        result = run_cli("verify", "--project", str(root))
        check(result.returncode == 1, "CLI verify 失败应以退出码 1 表达")
    result = run_cli("show", "--project", str(SAMPLE), "--task", "99-missing")
    check(result.returncode != 0, "CLI show 缺失任务应非零退出")


def test_list_and_show_read_config_once_and_preserve_order() -> None:
    """AC1/AC2/READ-06:list/show 每次调用只读一次 CONFIG;list 按目录排序。

    本地目录名与正文身份刻意相反:list 仍按目录顺序返回任务列表(非身份
    排序),且每份 task.md 只读一次;反复调用之间不残留跨调用状态。
    """

    with tempfile.TemporaryDirectory() as tmp:
        root = make_project(Path(tmp), extra_task=False)
        docs = root / "docs" / "mygamestudio" / "work"
        # 目录 05-zzz 的正文身份 02-aaa;目录 02-aaa 的正文身份 05-zzz
        for directory, identity in (("05-zzz", "02-aaa"), ("02-aaa", "05-zzz")):
            task_dir = docs / directory
            task_dir.mkdir(parents=True)
            (task_dir / "task.md").write_text(
                PLAN_TASK_TEMPLATE.format(
                    title=f"目录 {directory}", identity=identity,
                    triage="ready-for-agent", progress="待执行", goal="目标",
                    deliver="交付", scope="src/**", capability="文件读写",
                    executor="Agent(制作实现)", acceptance="检查", deps="无",
                    coordination="无", missing="无", index="(暂无)"),
                encoding="utf-8")

        with scoped_read_counter(root) as counter:
            listed = mgs_records.list_tasks(root)
        check(counter.config_reads() == 1,
              f"list 应只读 CONFIG 原文一次,实际 {counter.by_path}")
        check(isinstance(listed, list)
              and [t["directory"] for t in listed] == ["02-aaa", "05-zzz"],
              f"list 应返回任务列表并按目录排序,实际 {listed}")
        check(all(n == 1 for n in counter.task_reads().values())
              and len(counter.task_reads()) == 2,
              f"list 每份 task.md 应恰好读一次,实际 {counter.task_reads()}")
        with scoped_read_counter(root) as rerun:
            mgs_records.list_tasks(root)
        check(rerun.task_reads() == counter.task_reads()
              and rerun.config_reads() == 1,
              "list 读取计数在独立重跑下应稳定(无跨调用状态)")

        with scoped_read_counter(root) as counter:
            task = mgs_records.read_task(root, "02-aaa")
        check(counter.config_reads() == 1,
              f"show 应只读 CONFIG 原文一次,实际 {counter.by_path}")
        check(task["directory"] == "02-aaa" and task["identity"] == "05-zzz",
              f"show 应按目录定位并保留正文身份(目录/身份可相反),实际 {task}")


def test_show_locates_by_directory_without_scanning_unrelated() -> None:
    """AC3/READ-07:本地 show 按目录定位,不扫描无关任务;缺失时错误保持。

    目录名与正文身份不一致仍能找到原记录;读取一个任务时只有一个
    task.md 被打开(不列举其余任务)。
    """

    with tempfile.TemporaryDirectory() as tmp:
        root = make_plan_project(Path(tmp))
        docs = root / "docs" / "mygamestudio" / "work"
        # 目录名与正文身份不一致:目录 07-mismatch,正文身份 01-mismatch
        task_dir = docs / "07-mismatch"
        task_dir.mkdir(parents=True)
        (task_dir / "task.md").write_text(
            PLAN_TASK_TEMPLATE.format(
                title="错位任务", identity="01-mismatch",
                triage="ready-for-agent", progress="待执行", goal="目标",
                deliver="交付", scope="src/**", capability="文件读写",
                executor="Agent(制作实现)", acceptance="检查", deps="无",
                coordination="无", missing="无", index="(暂无)"),
            encoding="utf-8")

        with scoped_read_counter(root) as counter:
            task = mgs_records.read_task(root, "07-mismatch")
        check(task["directory"] == "07-mismatch" and task["identity"] == "01-mismatch",
              f"show 应按目录定位(即使目录与正文身份不一致),实际 {task}")
        check(list(counter.task_reads()) == ["docs/mygamestudio/work/07-mismatch/task.md"],
              f"show 只应读取所点任务的 task.md,不扫描无关任务,实际 "
              f"{counter.task_reads()}")
        check(counter.config_reads() == 1,
              f"show 应只读 CONFIG 一次,实际 {counter.by_path}")

        # 缺失任务:同一 RecordsError 错误表达,且不读取任何任务文件
        with scoped_read_counter(root) as counter:
            try:
                mgs_records.read_task(root, "99-missing")
            except mgs_records.RecordsError as exc:
                check("任务不存在" in str(exc) or "task.md" in str(exc),
                      f"缺失任务的错误应说明定位失败:{exc}")
            else:
                check(False, "读取不存在的任务应抛 RecordsError")
        check(counter.task_reads() == {},
              f"缺失任务不应读取任何 task.md,实际 {counter.task_reads()}")


def test_cli_list_show_projection_and_exit_codes() -> None:
    """AC2/AC5/READ-09:CLI list 仍是原字段投影 JSON 数组,show 保留单任务结构;
    成功 0、记录/文件错误 2,既有退出码合同保持。
    """

    result = run_cli("list", "--project", str(SAMPLE))
    check(result.returncode == 0, f"CLI list 应退出 0:{result.stderr[:200]}")
    data = json.loads(result.stdout)
    check(isinstance(data, list), f"CLI list 应为 JSON 数组,实际 {type(data)}")
    check(all(set(item) == {"identity", "title", "triage", "progress"}
              for item in data),
              f"CLI list 应为原字段投影(identity/title/triage/progress),实际 "
              f"{[sorted(item) for item in data]}")
    check([item["identity"] for item in data]
          == [t["identity"] for t in mgs_records.list_tasks(SAMPLE)],
          "CLI list 顺序应与 Python list 一致(本地按目录顺序)")

    result = run_cli("show", "--project", str(SAMPLE), "--task", "02-coin-magnet")
    check(result.returncode == 0, f"CLI show 应退出 0:{result.stderr[:200]}")
    shown = json.loads(result.stdout)
    check(isinstance(shown, dict) and shown["identity"] == "02-coin-magnet"
          and set(shown) == set(mgs_records.read_task(SAMPLE, "02-coin-magnet")),
          "CLI show 应保留单任务结构与字段集合")
    check(shown == mgs_records.read_task(SAMPLE, "02-coin-magnet"),
          "CLI show 输出应与 Python read_task 一致")

    result = run_cli("show", "--project", str(SAMPLE), "--task", "99-missing")
    check(result.returncode == 2 and "error" in json.loads(result.stdout),
          f"CLI show 缺失任务应以退出码 2 与 error 对象表达,实际 "
          f"rc={result.returncode} out={result.stdout[:120]}")

    with tempfile.TemporaryDirectory() as tmp:
        root = make_project(Path(tmp), extra_task=False)
        (root / "docs" / "mygamestudio" / "CONFIG.md").unlink()
        result = run_cli("list", "--project", str(root))
        check(result.returncode == 2 and "error" in json.loads(result.stdout),
              f"CLI list 配置缺失应以退出码 2 表达,实际 "
              f"rc={result.returncode} out={result.stdout[:120]}")

TESTS = (
    test_load_config_on_sample,
    test_load_config_missing,
    test_unsupported_backend,
    test_github_backend_does_not_read_local_tasks,
    test_list_tasks_on_sample,
    test_list_tasks_empty_root,
    test_read_task,
    test_cli,
    test_list_and_show_read_config_once_and_preserve_order,
    test_show_locates_by_directory_without_scanning_unrelated,
    test_cli_list_show_projection_and_exit_codes,
)

if __name__ == "__main__":
    sys.exit(run_theme("本地后端读取(配置/列表/单任务)", TESTS, FAILURES))

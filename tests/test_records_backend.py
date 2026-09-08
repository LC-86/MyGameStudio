#!/usr/bin/env python3
"""本地 Markdown 任务后端统一接口的确定性检查(任务票 04)。

接缝说明:本脚本只覆盖 mgs_records 的公开接缝——
load_config / list_tasks / read_task / verify_project 四个逻辑操作与其 CLI。
「通过统一接口回读」的判定以 CONFIG.md 为配置入口,不硬编码任务根目录。
真实初始化(探查、清单确认、按角色应用写入)由 acceptance/04 的隔离验收覆盖,
本脚本不替代。

用法:python3 tests/test_records_backend.py
"""

import json
import subprocess
import sys
import tempfile
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "plugin" / "records"))

import mgs_records  # noqa: E402

SAMPLE = REPO_ROOT / "samples" / "role-scope-demo"
CLI = REPO_ROOT / "plugin" / "records" / "mgs_records.py"

FAILURES: list[str] = []


def check(condition: bool, message: str) -> None:
    if not condition:
        FAILURES.append(message)


FIVE_LABELS = ("needs-triage", "needs-info", "ready-for-agent", "ready-for-human", "wontfix")

CONFIG_TEMPLATE = """# 测试项目:协作配置

维护责任:制作统筹。配置版本:v1。采用依据:测试夹具。

## 任务来源

- 后端:{backend}
- 当前位置:docs/mygamestudio/work/(每任务一目录,task.md 为工作请求与状态)
- 任务读取规则:本地 Markdown 后端约定
- 外部连接引用及已确认操作范围:无

## 标签映射

| 语义 | 项目标签 |
| --- | --- |
{label_rows}

## 文档映射

| 内容 | 当前权威位置 | 维护角色 |
| --- | --- |
| 项目目标与范围 | docs/mygamestudio/PROJECT.md | 制作统筹 |
| 游戏需求与设计 | docs/mygamestudio/GAME_DESIGN.md | 方案设计 |
| 技术设计 | docs/mygamestudio/TECH_DESIGN.md | 制作实现 |
| 术语、ADR 与历史 | docs/mygamestudio/records/(暂空) | 对应专业角色 |

## 执行条件

- 工程、原型、资源与构建入口:src/
- 可用能力及已验证执行边界:文件读写
- 尚未就绪的能力及影响:无
"""

TASK_TEMPLATE = """# {title}

任务身份:{identity}。当前分流:{triage}。进度:{progress}。

## 工作请求

- 当前目标:{goal}
- 输入与基线:PROJECT.md v1
- 本次交付:示例交付
- 允许修改范围:src/**
- 完成标准:示例标准
- 执行责任:Agent(制作实现)
- 验收方式:代码级检查
- 依赖与写入协调:无
- 尚缺信息:无

## 结果索引

{index}

## 状态变化

2026-09-08 测试夹具初始化。
"""

RESULT_TEMPLATE = """# {title}:执行结果

任务:{identity}。执行者与角色:i-x(制作实现)。本次状态:已交付。

- 实际成果:src/main.js
"""


def make_project(root: Path, *, backend: str = "local-markdown",
                 label_rows: str | None = None, extra_task: bool = True,
                 with_core_docs: bool = True) -> Path:
    """在临时目录搭建一个最小可核验项目(CONFIG + 核心文档 + 一个任务)。"""

    docs = root / "docs" / "mygamestudio"
    docs.mkdir(parents=True)
    if label_rows is None:
        label_rows = "\n".join(f"| {name} | {name} |" for name in FIVE_LABELS)
    (docs / "CONFIG.md").write_text(
        CONFIG_TEMPLATE.format(backend=backend, label_rows=label_rows), encoding="utf-8")
    if with_core_docs:
        for name in ("PROJECT.md", "GAME_DESIGN.md", "TECH_DESIGN.md"):
            (docs / name).write_text(f"# {name}\n\n测试内容\n", encoding="utf-8")
    if extra_task:
        task_dir = docs / "work" / "01-demo"
        task_dir.mkdir(parents=True)
        (task_dir / "task.md").write_text(
            TASK_TEMPLATE.format(title="演示任务", identity="01-demo",
                                 triage="ready-for-agent", progress="待执行",
                                 goal="演示目标", index="(暂无)"),
            encoding="utf-8")
    return root


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
        make_project(Path(tmp), backend="github-issues")
        config = mgs_records.load_config(Path(tmp))
        check(config["backend"] == "github-issues", "load_config 应原样回报后端")
        try:
            mgs_records.list_tasks(Path(tmp))
        except mgs_records.RecordsError:
            check(True, "")
        else:
            check(False, "非 local-markdown 后端执行本地任务操作应报不支持")


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


def test_verify_ok_sample() -> None:
    report = mgs_records.verify_project(SAMPLE)
    names = {c["name"] for c in report["checks"]}
    expected = {"config-present", "backend-local-markdown", "task-root-exists",
                "labels-complete", "labels-no-conflict", "docmap-core-rows",
                "docmap-unique-authority", "docmap-paths-exist",
                "tasks-valid", "results-consistent"}
    check(expected <= names, f"verify 应包含约定检查项,缺 {expected - names}")
    if not report["ok"]:
        for c in report["checks"]:
            if not c["ok"]:
                FAILURES.append(f"样例 verify 不应失败:{c['name']}:{c['detail']}")
    check(report["ok"], "role-scope-demo 样例应整体通过 verify")


def test_verify_label_failures() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = make_project(Path(tmp), label_rows="\n".join(
            f"| {name} | {name} |" for name in FIVE_LABELS[:4]))
        report = mgs_records.verify_project(root)
        failed = {c["name"] for c in report["checks"] if not c["ok"]}
        check("labels-complete" in failed, f"缺一类标签应判 labels-complete 失败,实际 {failed}")
    with tempfile.TemporaryDirectory() as tmp:
        rows = [f"| {name} | ready-for-agent |" for name in FIVE_LABELS]
        root = make_project(Path(tmp), label_rows="\n".join(rows))
        report = mgs_records.verify_project(root)
        failed = {c["name"] for c in report["checks"] if not c["ok"]}
        check("labels-no-conflict" in failed,
              f"五类语义映射到同一标签应判冲突,实际 {failed}")


def test_verify_docmap_failures() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = make_project(Path(tmp))
        config_path = root / "docs" / "mygamestudio" / "CONFIG.md"
        text = config_path.read_text(encoding="utf-8")
        config_path.write_text(text.replace(
            "| 技术设计 | docs/mygamestudio/TECH_DESIGN.md | 制作实现 |\n", ""),
            encoding="utf-8")
        failed = {c["name"] for c in mgs_records.verify_project(root)["checks"] if not c["ok"]}
        check("docmap-core-rows" in failed, f"缺技术设计行应判失败,实际 {failed}")
    with tempfile.TemporaryDirectory() as tmp:
        root = make_project(Path(tmp))
        config_path = root / "docs" / "mygamestudio" / "CONFIG.md"
        text = config_path.read_text(encoding="utf-8")
        config_path.write_text(text.replace(
            "| 技术设计 | docs/mygamestudio/TECH_DESIGN.md | 制作实现 |",
            "| 技术设计 | docs/mygamestudio/PROJECT.md | 制作实现 |"),
            encoding="utf-8")
        failed = {c["name"] for c in mgs_records.verify_project(root)["checks"] if not c["ok"]}
        check("docmap-unique-authority" in failed, f"两类内容同一权威位置应判失败,实际 {failed}")
    with tempfile.TemporaryDirectory() as tmp:
        root = make_project(Path(tmp), with_core_docs=False)
        failed = {c["name"] for c in mgs_records.verify_project(root)["checks"] if not c["ok"]}
        check("docmap-paths-exist" in failed, f"核心文档缺失应判失败,实际 {failed}")


def test_verify_task_failures() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = make_project(Path(tmp))
        task_path = root / "docs" / "mygamestudio" / "work" / "01-demo" / "task.md"
        task_path.write_text(task_path.read_text(encoding="utf-8").replace(
            "当前分流:ready-for-agent", "当前分流:done"),
            encoding="utf-8")
        failed = {c["name"] for c in mgs_records.verify_project(root)["checks"] if not c["ok"]}
        check("tasks-valid" in failed, f"五类之外的分流值应判失败,实际 {failed}")
    with tempfile.TemporaryDirectory() as tmp:
        root = make_project(Path(tmp))
        task_path = root / "docs" / "mygamestudio" / "work" / "01-demo" / "task.md"
        task_path.write_text(task_path.read_text(encoding="utf-8").replace(
            "任务身份:01-demo", "任务身份:other-id"),
            encoding="utf-8")
        failed = {c["name"] for c in mgs_records.verify_project(root)["checks"] if not c["ok"]}
        check("tasks-valid" in failed, "任务身份与目录不一致应判失败")


def test_verify_results_consistency() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = make_project(Path(tmp))
        results = root / "docs" / "mygamestudio" / "work" / "01-demo" / "results"
        results.mkdir()
        (results / "2026-09-08.md").write_text(
            RESULT_TEMPLATE.format(title="演示任务", identity="01-demo"), encoding="utf-8")
        failed = {c["name"] for c in mgs_records.verify_project(root)["checks"] if not c["ok"]}
        check("results-consistent" in failed,
              f"结果文件存在但结果索引仍为暂无应判失败,实际 {failed}")
        task_path = root / "docs" / "mygamestudio" / "work" / "01-demo" / "task.md"
        task_path.write_text(task_path.read_text(encoding="utf-8").replace(
            "(暂无)", "results/2026-09-08.md:骨架交付"),
            encoding="utf-8")
        report = mgs_records.verify_project(root)
        check(report["ok"], f"结果被索引引用后应整体通过:{report['checks']}")
    with tempfile.TemporaryDirectory() as tmp:
        root = make_project(Path(tmp))
        results = root / "docs" / "mygamestudio" / "work" / "01-demo" / "results"
        results.mkdir()
        (results / "2026-09-08.md").write_text(
            RESULT_TEMPLATE.format(title="演示任务", identity="99-other"), encoding="utf-8")
        task_path = root / "docs" / "mygamestudio" / "work" / "01-demo" / "task.md"
        task_path.write_text(task_path.read_text(encoding="utf-8").replace(
            "(暂无)", "results/2026-09-08.md:骨架交付"),
            encoding="utf-8")
        failed = {c["name"] for c in mgs_records.verify_project(root)["checks"] if not c["ok"]}
        check("results-consistent" in failed, "结果文件不引用所属任务身份应判失败")


def run_cli(*args: str) -> subprocess.CompletedProcess:
    return subprocess.run([sys.executable, "-B", str(CLI), *args],
                          capture_output=True, text=True)


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


def main() -> int:
    for name, func in sorted(globals().items()):
        if name.startswith("test_") and callable(func):
            func()
    if FAILURES:
        print(f"FAIL ({len(FAILURES)} 项):")
        for failure in FAILURES:
            print(f"  - {failure}")
        return 1
    print("OK: 本地 Markdown 任务后端统一接口检查全部通过")
    return 0


if __name__ == "__main__":
    sys.exit(main())

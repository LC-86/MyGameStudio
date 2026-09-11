#!/usr/bin/env python3
"""本地 Markdown 任务后端统一接口的确定性检查(任务票 04,票 08 扩展)。

接缝说明:本脚本只覆盖 mgs_records 的公开接缝——
load_config / list_tasks / read_task / verify_project(票 04)与
task_dependencies / startable_tasks(票 08:关系解析、循环检测、开工集合)
各逻辑操作与其 CLI。
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
- 当前位置:{location}
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

# 拆单轮形态的任务记录(任务票 08):模板字段 + 拆单需要的「依赖」「所需能力」
PLAN_TASK_TEMPLATE = """# {title}

任务身份:{identity}。当前分流:{triage}。进度:{progress}。

## 工作请求

- 当前目标:{goal}
- 输入与基线:GAME_DESIGN v2「本轮可执行规格」
- 本次交付:{deliver}
- 允许修改范围:{scope}
- 所需能力:{capability}
- 完成标准:可独立核验的小成果
- 执行责任:{executor}
- 验收方式:{acceptance}
- 依赖:{deps}
- 依赖与写入协调:{coordination}
- 尚缺信息:{missing}

## 结果索引

{index}

## 状态变化

2026-09-08 拆单轮测试夹具初始化。
"""


def make_plan_project(root: Path) -> Path:
    """搭建拆单轮形态的最小项目:CONFIG 声明未就绪能力 + 基线 v2 + 六个任务。

    任务结构(供 deps/ready 断言):
    - 01-alpha  ready-for-agent 待执行 无依赖 → 可开工
    - 02-beta   ready-for-agent 待执行 依赖 01-alpha(未完成) → 不可开工(标签≠可开工)
    - 03-gamma  needs-info      待执行 依赖 无 → 输入不足
    - 04-delta  ready-for-human 待执行 依赖 01-alpha-done(已完成) → 可开工(Human)
    - 05-epsilon ready-for-agent 待执行 依赖 无;所需能力 音频提示(CONFIG 未就绪) → 能力未就绪
    - 06-zeta   ready-for-agent 待执行 依赖 无;基线引用 v1(当前 v2) → 版本漂移
    """

    root = make_project(root, extra_task=False)
    docs = root / "docs" / "mygamestudio"
    config = docs / "CONFIG.md"
    config.write_text(config.read_text(encoding="utf-8").replace(
        "- 尚未就绪的能力及影响:无",
        "- 尚未就绪的能力及影响:无音频制作能力,音频相关需求依赖外部素材"),
        encoding="utf-8")
    (docs / "GAME_DESIGN.md").write_text(
        "# 当前游戏需求与设计\n\n基线版本:v2。采用依据:测试夹具。\n", encoding="utf-8")

    def task(identity: str, title: str, *, triage: str, progress: str,
             deps: str = "无", capability: str = "文件读写",
             executor: str = "Agent(制作实现)", scope: str = "src/main.js",
             deliver: str = "示例交付", acceptance: str = "代码级检查",
             coordination: str = "无", missing: str = "无",
             baseline: str | None = None) -> None:
        task_dir = docs / "work" / identity
        task_dir.mkdir(parents=True)
        (task_dir / "task.md").write_text(
            PLAN_TASK_TEMPLATE.format(
                title=title, identity=identity, triage=triage, progress=progress,
                goal="本轮目标(PROJECT v1)", deliver=deliver, scope=scope,
                capability=capability, executor=executor, acceptance=acceptance,
                deps=deps, coordination=coordination, missing=missing,
                index="(暂无)").replace(
                "GAME_DESIGN v2「本轮可执行规格」",
                baseline or "GAME_DESIGN v2「本轮可执行规格」"),
            encoding="utf-8")

    task("01-alpha", "甲任务", triage="ready-for-agent", progress="待执行")
    task("02-beta", "乙任务", triage="ready-for-agent", progress="待执行",
         deps="01-alpha")
    task("03-gamma", "丙任务", triage="needs-info", progress="待执行",
         missing="预警形式未决(需开发者决定)")
    task("01-alpha-done", "甲任务已完成形态", triage="ready-for-agent",
         progress="已完成")
    task("04-delta", "丁人工任务", triage="ready-for-human", progress="待执行",
         deps="01-alpha-done", executor="Human(开发者)", deliver="试玩反馈",
         acceptance="开发者真实试玩反馈")
    task("05-epsilon", "戊音频任务", triage="ready-for-agent", progress="待执行",
         capability="音频提示制作")
    task("06-zeta", "己漂移任务", triage="ready-for-agent", progress="待执行",
         baseline="GAME_DESIGN v1(旧版本)")
    return root


def make_project(root: Path, *, backend: str = "local-markdown",
                 repo: str = "github.com/mygamestudio/issue-accept",
                 label_rows: str | None = None, extra_task: bool = True,
                 with_core_docs: bool = True) -> Path:
    """在临时目录搭建一个最小可核验项目(CONFIG + 核心文档 + 一个任务)。"""

    docs = root / "docs" / "mygamestudio"
    docs.mkdir(parents=True)
    if label_rows is None:
        label_rows = "\n".join(f"| {name} | {name} |" for name in FIVE_LABELS)
    location = (repo if backend == "github-issues"
                else "docs/mygamestudio/work/"
                     "(每任务一目录,task.md 为工作请求与状态)")
    (docs / "CONFIG.md").write_text(
        CONFIG_TEMPLATE.format(backend=backend, location=location,
                               label_rows=label_rows), encoding="utf-8")
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


# ---------- 基线内容指纹与受影响任务(任务票 15) ----------

FP_LINES = "内容指纹:sha256:{fp}。归一指纹:sha256:{np}。\n"


def _register_fingerprint(path: Path, header_anchor: str) -> None:
    """按技能登记纪律为一份基线登记双指纹(与实现同一规范化口径)。

    登记方法:两条指纹先写 64 个 0(规范化后与占位等价),对全文分别计算
    空白敏感指纹与空白归一指纹,把结果填回。
    """

    text = path.read_text(encoding="utf-8")
    zeros = "0" * 64
    marked = text.replace(header_anchor,
                          header_anchor + FP_LINES.format(fp=zeros, np=zeros))
    strict = mgs_records._canonical_fingerprint(marked)
    norm = mgs_records._normalized_fingerprint(marked)
    path.write_text(marked.replace(
        FP_LINES.format(fp=zeros, np=zeros),
        FP_LINES.format(fp=strict, np=norm)), encoding="utf-8")


def test_baseline_report_states() -> None:
    """内容指纹四态:一致/指纹未登记/格式修正漂移/实质变更漂移(任务票 15)。"""

    with tempfile.TemporaryDirectory() as tmp:
        root = make_project(Path(tmp))
        docs = root / "docs" / "mygamestudio"
        # GAME_DESIGN:声明 v4 并登记指纹
        design = docs / "GAME_DESIGN.md"
        design.write_text(
            "# 当前游戏需求与设计\n\n维护责任:方案设计。基线版本:v4。\n"
            "\n- 回合时长 45 秒,结束即结算\n", encoding="utf-8")
        _register_fingerprint(design, "基线版本:v4。")
        report = mgs_records.baseline_report(root)
        states = {d["path"].split("/")[-1]: d["status"] for d in report["docs"]}
        check(states.get("GAME_DESIGN.md") == "一致",
              f"登记指纹且内容未变应为一致,实际 {states}")
        check(report["ok"] is True, "无实质变更时 baseline 应 ok")

        # PROJECT 未登记指纹 → 指纹未登记(不判漂移)
        check(states.get("PROJECT.md") == "指纹未登记",
              f"未登记指纹的基线应报指纹未登记,实际 {states}")

        # 格式修正(仅空白变化,无字符增删)→ 疑似格式修正,不作废(ok 保持)
        design.write_text(
            design.read_text(encoding="utf-8").replace(
                "- 回合时长 45 秒,结束即结算\n",
                "- 回合时长 45 秒,\t结束即结算\n"), encoding="utf-8")
        report = mgs_records.baseline_report(root)
        states = {d["path"].split("/")[-1]: d["status"] for d in report["docs"]}
        check(states.get("GAME_DESIGN.md") == "内容已变(疑似格式修正)",
              f"仅空白变化应判疑似格式修正,实际 {states}")
        check(report["ok"] is True, "格式修正不应判为需要重审(ok 应保持 True)")

        # 实质变更(字符增删,版本号未同步)→ 实质变更,ok False
        design.write_text(
            design.read_text(encoding="utf-8").replace(
                "回合时长 45 秒", "回合时长 50 秒"), encoding="utf-8")
        report = mgs_records.baseline_report(root)
        states = {d["path"].split("/")[-1]: d["status"] for d in report["docs"]}
        check(states.get("GAME_DESIGN.md") == "内容已变(实质变更)",
              f"字符实质变化应判实质变更,实际 {states}")
        check(report["ok"] is False, "存在实质变更未同步时 baseline 不应 ok")

        # 文件缺失 → 文件缺失
        (docs / "TECH_DESIGN.md").unlink()
        report = mgs_records.baseline_report(root)
        states = {d["path"].split("/")[-1]: d["status"] for d in report["docs"]}
        check(states.get("TECH_DESIGN.md") == "文件缺失",
              f"核心基线文件缺失应如实报告,实际 {states}")


def test_baseline_report_affected_tasks() -> None:
    """受影响任务识别:引用旧版本即列出;已完成/待验收保留完成事实语义。"""

    with tempfile.TemporaryDirectory() as tmp:
        root = make_project(Path(tmp))
        docs = root / "docs" / "mygamestudio"
        design = docs / "GAME_DESIGN.md"
        design.write_text("# 当前游戏需求与设计\n\n基线版本:v4。\n", encoding="utf-8")
        work = docs / "work"
        (work / "05-gull-swoop").mkdir(parents=True)
        (work / "05-gull-swoop" / "task.md").write_text(PLAN_TASK_TEMPLATE.format(
            title="海鸥俯冲", identity="05-gull-swoop", triage="ready-for-agent",
            progress="待执行", goal="实现海鸥俯冲", deliver="src 代码", scope="src/**",
            capability="文件读写", executor="Agent(制作实现)", acceptance="行为检查",
            deps="无", coordination="无", missing="无", index="(暂无)").replace(
            "GAME_DESIGN v2「本轮可执行规格」",
            "GAME_DESIGN v2「当前规则与流程」"), encoding="utf-8")
        (work / "02-tide-timer").mkdir(parents=True)
        (work / "02-tide-timer" / "task.md").write_text(PLAN_TASK_TEMPLATE.format(
            title="潮汐倒计时", identity="02-tide-timer", triage="ready-for-agent",
            progress="待验收", goal="实现倒计时", deliver="src 代码", scope="src/**",
            capability="文件读写", executor="Agent(制作实现)", acceptance="行为检查",
            deps="无", coordination="无", missing="无", index="(暂无)").replace(
            "GAME_DESIGN v2「本轮可执行规格」",
            "GAME_DESIGN v2;TECH_DESIGN v1"), encoding="utf-8")
        (work / "06-fresh").mkdir(parents=True)
        (work / "06-fresh" / "task.md").write_text(PLAN_TASK_TEMPLATE.format(
            title="新任务", identity="06-fresh", triage="ready-for-agent",
            progress="待执行", goal="新任务", deliver="示例", scope="src/**",
            capability="文件读写", executor="Agent(制作实现)", acceptance="行为检查",
            deps="无", coordination="无", missing="无", index="(暂无)").replace(
            "GAME_DESIGN v2「本轮可执行规格」",
            "GAME_DESIGN v4「当前规则与流程」与 PROJECT.md 当前目标"), encoding="utf-8")
        report = mgs_records.baseline_report(root)
        affected = {item["identity"]: item for item in report["affected_tasks"]}
        check("05-gull-swoop" in affected,
              f"引用 GAME_DESIGN v2(当前 v4)的任务应列为受影响,实际 {sorted(affected)}")
        entry = affected.get("05-gull-swoop", {})
        check(entry.get("ref_version") == "v2" and entry.get("current_version") == "v4",
              f"受影响条目应记录引用版本与当前版本,实际 {entry}")
        check(not entry.get("completion_fact"),
              "待执行任务的受影响条目不应带完成事实说明")
        check("02-tide-timer" in affected,
              "待验收任务引用旧版本同样应列为受影响")
        done_entry = affected.get("02-tide-timer", {})
        check(done_entry.get("progress") == "待验收"
              and "保留原版本" in (done_entry.get("completion_fact") or "")
              and "不自动算作满足新目标" in (done_entry.get("completion_fact") or ""),
              f"待验收受影响条目应声明完成事实保留语义,实际 {done_entry}")
        check("06-fresh" not in affected,
              "引用当前版本或无版本号引用的任务不应列为受影响")
        check("版本号未同步" in report["note"] or "指纹" in report["note"],
              "baseline 输出应附处理说明 note")


def test_baseline_cli() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = make_project(Path(tmp))
        result = run_cli("baseline", "--project", str(root))
        check(result.returncode == 0,
              f"CLI baseline 无实质变更应退出 0:{result.stdout[:200]}")
        data = json.loads(result.stdout)
        check(isinstance(data.get("docs"), list) and data["docs"],
              "CLI baseline 应输出 docs 列表")
        docs = root / "docs" / "mygamestudio"
        design = docs / "GAME_DESIGN.md"
        design.write_text("# 当前游戏需求与设计\n\n基线版本:v2。\n- 规则\n",
                          encoding="utf-8")
        _register_fingerprint(design, "基线版本:v2。")
        design.write_text(design.read_text(encoding="utf-8") + "- 新增规则\n",
                          encoding="utf-8")
        result = run_cli("baseline", "--project", str(root))
        check(result.returncode == 1, "CLI baseline 存在实质变更未同步应以退出码 1 表达")


# ---------- 票 02:共同正文与错误语义(READ-08/READ-10) ----------

def test_record_model_shared_body_and_error_identity() -> None:
    """票 02:共同正文规则与错误类型由中性记录 module 提供、不反向依赖查询。

    覆盖:本地读取直接使用共享正文解析;空字段、未知小节与字段分隔保持可见;
    畸形任务不被提前过滤,仍进入核验;RecordsError 与共享 module 同一身份。
    """

    import mgs_record_model

    check(mgs_records.RecordsError is mgs_record_model.RecordsError,
          "mgs_records.RecordsError 应与共享记录 module 同一身份")
    for name in ("parse_task_body", "_sections", "_bullets", "_field",
                 "task_core_problems", "dependency_problems",
                 "label_mapping_checks", "docmap_checks", "check_item"):
        check(hasattr(mgs_record_model, name),
              f"共享记录 module 应提供 {name}")
    # 共同记录语义不反向依赖查询/命令行:model 不导入 mgs_records / mgs_github
    model_source = Path(mgs_record_model.__file__).read_text(encoding="utf-8")
    check("import mgs_records" not in model_source
          and "import mgs_github" not in model_source,
          "共享记录 module 不得反向依赖查询或 GitHub adapter")

    body = (
        "# 畸形任务\n\n"
        "任务身份:。当前分流:ready-for-agent。进度:待执行;负责人:张三。\n\n"
        "## 工作请求\n\n"
        "- 当前目标:演示目标\n"
        "- 完成标准:\n"
        "- 执行责任:Agent（制作实现）\n\n"
        "## 未知小节\n\n"
        "未知内容仍需保留\n\n"
        "## 结果索引\n\n"
        "(暂无)\n"
    )
    parsed = mgs_record_model.parse_task_body(body)
    check(parsed["identity"] == "", f"空身份字段应保持为空,实际 {parsed['identity']!r}")
    check(parsed["progress"] == "待执行",
          f"字段分隔(分号)应正确截断,实际 {parsed['progress']!r}")
    check(parsed["request"].get("完成标准") == "",
          "空值字段应保留键且值为空")
    check(parsed["request"].get("执行责任") == "Agent（制作实现）",
          "全角冒号应作为字段分隔")
    check(parsed["sections"].get("未知小节") is True,
          "未知小节应保留在 sections 中")
    check(parsed["result_index_text"].strip() == "(暂无)",
          "结果索引原文应保留")

    with tempfile.TemporaryDirectory() as tmp:
        root = make_project(Path(tmp), extra_task=False)
        task_dir = root / "docs" / "mygamestudio" / "work" / "05-malformed"
        task_dir.mkdir(parents=True)
        (task_dir / "task.md").write_text(body, encoding="utf-8")
        tasks = mgs_records.list_tasks(root)
        check([t["directory"] for t in tasks] == ["05-malformed"],
              f"畸形任务应仍被列出而非提前过滤,实际 {tasks}")
        local = mgs_records.read_task(root, "05-malformed")
        check(local["identity"] == "" and local["directory"] == "05-malformed",
              "本地读取应同时保留空身份与目录专有字段")
        check(local["request"].get("完成标准") == ""
              and local["sections"].get("未知小节") is True,
              "本地读取应保持空字段与未知小节可见")
        report = mgs_records.verify_project(root)
        tasks_check = next(c for c in report["checks"] if c["name"] == "tasks-valid")
        check(tasks_check["ok"] is False
              and "正文身份缺失或不合规" in tasks_check["detail"],
              f"畸形任务应进入核验并报告身份问题:{tasks_check['detail']}")


# ---------- 票 03:来源归属与依赖方向(READ-13/依赖纪律) ----------

RECORDS_DIR = REPO_ROOT / "plugin" / "records"


def _imported_modules(path: Path) -> set[str]:
    """AST 扫描一份源码中所有 import(含函数内导入),返回模块名集合。

    用 AST 而非正则:函数内 import(延迟导入)同样计为依赖,防止用新的
    延迟导入掩盖反向调用。
    """

    import ast

    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    names: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            names.update(alias.name.split(".")[0] for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module and node.level == 0:
            names.add(node.module.split(".")[0])
    return names


def test_dependency_direction_static() -> None:
    """依赖方向:共同语义/来源不反向依赖查询或 GitHub;GitHub 不反向调用查询。

    用 AST 扫描全部 import(含函数内),证明方向靠职责归属实现,而不是
    延迟导入;查询组织与 adapter 正向依赖来源 module。
    """

    model = _imported_modules(RECORDS_DIR / "mgs_record_model.py")
    source = _imported_modules(RECORDS_DIR / "mgs_record_source.py")
    github = _imported_modules(RECORDS_DIR / "mgs_github.py")
    records = _imported_modules(RECORDS_DIR / "mgs_records.py")

    for banned in ("mgs_records", "mgs_github", "mgs_record_source"):
        check(banned not in model,
              f"mgs_record_model 不得依赖 {banned}(含延迟导入),实际 {sorted(model)}")
    for banned in ("mgs_records", "mgs_github"):
        check(banned not in source,
              f"mgs_record_source 不得依赖 {banned}(含延迟导入),实际 {sorted(source)}")
    check("mgs_records" not in github,
          f"mgs_github 不得反向调用查询组织 mgs_records,实际 {sorted(github)}")
    # 正向:查询组织与 adapter 都依赖来源 module 与共同语义
    check("mgs_record_source" in records,
          f"mgs_records 应依赖来源 module,实际 {sorted(records)}")
    check("mgs_record_source" in github,
          f"mgs_github 应直接依赖来源 module,实际 {sorted(github)}")


def test_source_shared_with_query_and_import_orders() -> None:
    """两种导入顺序下共同语义/来源同一身份、无循环导入错误(READ-10/13)。

    来源先导入与查询先导入都必须成功,且配置读取是同一实现。
    """

    records_dir = str(RECORDS_DIR)
    probe = (
        "import sys\n"
        f"sys.path.insert(0, {records_dir!r})\n"
        "{first}\n"
        "{second}\n"
        "import mgs_record_source, mgs_records, mgs_record_model\n"
        "assert mgs_records.load_config is mgs_record_source.load_config\n"
        "assert mgs_records.RecordsError is mgs_record_model.RecordsError\n"
        "assert mgs_record_source.RecordsError is mgs_record_model.RecordsError\n"
        "print('OK')\n"
    )
    for label, first, second in (
            ("source-first", "import mgs_record_source", "import mgs_records"),
            ("records-first", "import mgs_records", "import mgs_record_source")):
        result = subprocess.run(
            [sys.executable, "-B", "-c", probe.format(first=first, second=second)],
            capture_output=True, text=True)
        check(result.returncode == 0 and "OK" in result.stdout,
              f"{label} 导入顺序来源身份应单一且无循环导入:{result.stderr[-300:]}")


def test_loaded_config_local_read_is_same_source() -> None:
    """已加载配置的本地读取经现有入口可用,且与正式入口同一结果(AC1/AC5)。

    - ``load_config_document`` 由同一 CONFIG 原文返回 (config, text);
    - 本地 adapter 接收本次已加载配置,不再重读 CONFIG;
    - 经现有公开入口 list_tasks/read_task 得到的结果与直接来源读取一致。
    """

    import mgs_record_source

    config, text = mgs_record_source.load_config_document(SAMPLE)
    check(config == mgs_records.load_config(SAMPLE),
          "同一 CONFIG 原文应解析出与正式入口相同的配置字段")
    check(text and "- 后端:local-markdown" in text,
          "同一原文应随配置返回,供本次调用内派生执行条件")

    # 已加载配置的本地读取不重读 CONFIG:审计钩子统计 open 调用
    import sys as _sys
    opened: list[str] = []

    def _hook(event: str, args: tuple) -> None:
        if event == "open" and args and isinstance(args[0], str):
            opened.append(args[0])

    _sys.addaudithook(_hook)
    tasks = mgs_record_source.local_list_tasks(SAMPLE, config)
    task = mgs_record_source.local_read_task(SAMPLE, config, "02-coin-magnet")
    config_reads = [p for p in opened if p.endswith("CONFIG.md")]
    check(config_reads == [],
          f"接收已加载配置的本地读取不得再读 CONFIG,实际打开 {config_reads}")

    # 与现有公开入口的结果一致
    check([t["identity"] for t in tasks]
          == [t["identity"] for t in mgs_records.list_tasks(SAMPLE)],
          "已加载配置的来源列举应与现有入口 list_tasks 一致")
    check(task == mgs_records.read_task(SAMPLE, "02-coin-magnet"),
          "已加载配置的来源读取应与现有入口 read_task 一致")


# ---------- 票 04:一次 ready 单份来源(R1/READ-01..06) ----------

class scoped_read_counter:
    """统计某项目根内的底层读取型 open 次数(按文件名聚合)。

    计数的是真实 open 事件(不是私有助手调用次数),与基线探针同一口径;
    只服务本次上下文,退出时注销审计钩子。
    """

    def __init__(self, root: Path) -> None:
        self.root = str(Path(root).resolve())
        self.counts: dict[str, int] = {}
        self.by_path: dict[str, int] = {}
        self._active = False

    def _hook(self, event: str, args: tuple) -> None:
        if event != "open" or not self._active:
            return
        raw = args[0]
        if isinstance(raw, bytes):
            raw = raw.decode("utf-8", "replace")
        elif not isinstance(raw, (str, __import__("os").PathLike)):
            return
        mode = args[1] if len(args) > 1 and isinstance(args[1], str) else ""
        if not mode.startswith("r"):
            return
        try:
            rel = Path(raw).resolve().relative_to(self.root)
        except (OSError, ValueError):
            return
        rel = str(rel)
        self.counts[Path(rel).name] = self.counts.get(Path(rel).name, 0) + 1
        self.by_path[rel] = self.by_path.get(rel, 0) + 1

    def __enter__(self) -> "scoped_read_counter":
        sys.addaudithook(self._hook)
        self._active = True
        return self

    def __exit__(self, *exc: object) -> None:
        self._active = False

    def config_reads(self) -> int:
        return sum(n for rel, n in self.by_path.items()
                   if Path(rel).name == "CONFIG.md")

    def task_reads(self) -> dict[str, int]:
        return {rel: n for rel, n in self.by_path.items()
                if Path(rel).name == "task.md"}


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


# ---------- 票 05:列表与单任务读取复用配置并保持兼容(READ-05/06/07/09) ----------

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


# ---------- 票 06:基线与核验同次复用读取(READ-04/08/09/11) ----------

class _GithubVerifyTransport:
    """github verify 的最小只读替身:任务列表 / 仓库标签 / 评论(零网络)。"""

    def __init__(self, issues: list[dict], *, labels: tuple[str, ...] = (),
                 comments: dict[int, list[dict]] | None = None) -> None:
        self.issues = issues
        self.labels = list(labels)
        self.comments = comments or {}
        self.calls: list[tuple[str, str]] = []

    def request(self, method: str, path: str, body: dict | None = None,
                *, auth: bool | None = True):
        self.calls.append((method, path))
        plain = path.split("?", 1)[0].rstrip("/")
        if method == "GET" and plain.endswith("/issues"):
            return 200, self.issues
        if method == "GET" and plain.endswith("/labels"):
            return 200, [{"name": name} for name in self.labels]
        if method == "GET" and plain.endswith("/comments"):
            number = int(plain.split("/issues/")[1].split("/")[0])
            return 200, list(self.comments.get(number, []))
        return 404, {"message": "minimal stand-in has no such route"}


def _github_issue(identity: str, title: str, number: int) -> dict:
    import mgs_github

    body = mgs_github.build_task_body(
        title, identity, "ready-for-agent", "待执行",
        {"当前目标": "演示目标", "输入与基线": "PROJECT.md v1",
         "本次交付": "示例交付", "允许修改范围": "src/**",
         "所需能力": "文件读写", "完成标准": "示例标准",
         "执行责任": "Agent(制作实现)", "验收方式": "代码级检查",
         "依赖": "无"})
    return {"number": number, "id": 1000 + number, "title": title, "body": body,
            "labels": [{"name": "ready-for-agent"}], "state": "open",
            "state_reason": None, "html_url": f"https://example.invalid/{number}"}


def test_baseline_reads_config_and_core_docs_once() -> None:
    """AC1/AC2/READ-04:baseline 同次复用配置与核心文档原文一次。

    CONFIG 只读一次;每份核心文档只读一次,同一原文同时推导逻辑版本与双
    指纹;下一次调用重新读取(不跨调用缓存)。双指纹三态与完成事实语义
    由 test_baseline_report_states/affected_tasks 逐项覆盖,此处只验证口径。
    """

    with tempfile.TemporaryDirectory() as tmp:
        root = make_project(Path(tmp))
        design = root / "docs" / "mygamestudio" / "GAME_DESIGN.md"
        design.write_text("# 当前游戏需求与设计\n\n基线版本:v2。\n- 规则\n",
                          encoding="utf-8")
        _register_fingerprint(design, "基线版本:v2。")

        with scoped_read_counter(root) as counter:
            first = mgs_records.baseline_report(root)
        check(counter.config_reads() == 1,
              f"baseline 应只读 CONFIG 原文一次,实际 {counter.by_path}")
        core_reads = {Path(rel).name: n for rel, n in counter.by_path.items()
                      if Path(rel).name in ("PROJECT.md", "GAME_DESIGN.md",
                                            "TECH_DESIGN.md")}
        check(core_reads == {"PROJECT.md": 1, "GAME_DESIGN.md": 1,
                             "TECH_DESIGN.md": 1},
              f"baseline 每份核心文档应只读一次(版本与指纹同一原文),实际 "
              f"{counter.by_path}")
        by_name = {d["path"].split("/")[-1]: d for d in first["docs"]}
        check(by_name["GAME_DESIGN.md"]["status"] == "一致"
              and by_name["GAME_DESIGN.md"]["declared_version"] == "v2",
              f"同一原文应同时给出逻辑版本与登记指纹结论,实际 "
              f"{by_name['GAME_DESIGN.md']}")

        # 下一次调用重新读取:仅空白差异应判疑似格式修正(语义保持)
        design.write_text(design.read_text(encoding="utf-8").replace(
            "- 规则\n", "- 规则\t\n"), encoding="utf-8")
        second = mgs_records.baseline_report(root)
        states = {d["path"].split("/")[-1]: d["status"] for d in second["docs"]}
        check(states.get("GAME_DESIGN.md") == "内容已变(疑似格式修正)",
              f"下一次调用应重新读取并看到仅空白差异,实际 {states}")
        check(second["ok"] is True, "疑似格式修正不应判为需要重审")


def test_verify_reads_config_and_tasks_once_local() -> None:
    """AC1/AC3/READ-04/READ-08:本地 verify 同次复用配置与任务集合一次。

    CONFIG 只读一次、每份 task.md 一次;检查名称与顺序保持;整体结论与既有
    语义一致(不复用会重复读 CONFIG)。
    """

    with tempfile.TemporaryDirectory() as tmp:
        root = make_plan_project(Path(tmp))
        with scoped_read_counter(root) as counter:
            report = mgs_records.verify_project(root)
        check(counter.config_reads() == 1,
              f"verify 应只读 CONFIG 原文一次,实际 {counter.by_path}")
        task_reads = counter.task_reads()
        check(task_reads and all(n == 1 for n in task_reads.values())
              and len(task_reads) == 7,
              f"verify 每份 task.md 应恰好读一次,实际 {task_reads}")
        names = [c["name"] for c in report["checks"]]
        expected = ["config-present", "backend-local-markdown", "task-root-exists",
                    "labels-complete", "labels-no-conflict", "docmap-core-rows",
                    "docmap-unique-authority", "docmap-paths-exist",
                    "tasks-valid", "results-consistent", "deps-consistent"]
        check(names == expected, f"verify 检查名称与顺序应保持,实际 {names}")
        check(report["ok"],
              f"健康拆单项目应通过 verify:{[c for c in report['checks'] if not c['ok']]}")


def test_verify_malformed_records_still_discoverable() -> None:
    """AC3/READ-08/READ-25:畸形记录(缺身份)与未知分流仍能被核验发现。

    畸形任务仍处于本次唯一任务集合内,不被读取层提前过滤;后端专有定位
    (任务目录)保留,便于定位原记录。
    """

    with tempfile.TemporaryDirectory() as tmp:
        root = make_project(Path(tmp))
        task_path = root / "docs" / "mygamestudio" / "work" / "01-demo" / "task.md"
        task_path.write_text(
            task_path.read_text(encoding="utf-8").replace(
                "任务身份:01-demo", "任务身份:"), encoding="utf-8")
        report = mgs_records.verify_project(root)
        failed = {c["name"] for c in report["checks"] if not c["ok"]}
        check("tasks-valid" in failed,
              f"缺身份任务应判 tasks-valid 失败,实际 {failed}")
        detail = next(c["detail"] for c in report["checks"]
                      if c["name"] == "tasks-valid")
        check("01-demo" in detail and "身份" in detail,
              f"缺身份问题应定位到任务目录,实际 {detail}")
    with tempfile.TemporaryDirectory() as tmp:
        root = make_project(Path(tmp))
        task_path = root / "docs" / "mygamestudio" / "work" / "01-demo" / "task.md"
        task_path.write_text(task_path.read_text(encoding="utf-8").replace(
            "当前分流:ready-for-agent", "当前分流:done"), encoding="utf-8")
        report = mgs_records.verify_project(root)
        failed = {c["name"] for c in report["checks"] if not c["ok"]}
        check("tasks-valid" in failed and report["ok"] is False,
              f"五类之外的分流应判失败,实际 {failed}")


def test_verify_github_reads_single_task_set_and_keeps_backend_reads() -> None:
    """AC1/AC4/READ-11:github verify 同次复用配置;任务集合获取一次,
    标签与评论核验仍实际发生(不因减少请求删掉必要读取)。
    """

    with tempfile.TemporaryDirectory() as tmp:
        root = make_project(Path(tmp), backend="github-issues", extra_task=False)
        fake = _GithubVerifyTransport(
            [_github_issue("01-alpha", "甲任务", 1)],
            labels=FIVE_LABELS, comments={1: []})
        with scoped_read_counter(root) as counter:
            report = mgs_records.verify_project(root, transport=fake)
        check(counter.config_reads() == 1,
              f"github verify 应只读 CONFIG 原文一次,实际 {counter.by_path}")
        list_calls = [c for c in fake.calls if c[0] == "GET"
                      and c[1].split("?", 1)[0].rstrip("/").endswith("/issues")]
        label_calls = [c for c in fake.calls if c[0] == "GET"
                       and c[1].split("?", 1)[0].rstrip("/").endswith("/labels")]
        comment_calls = [c for c in fake.calls if c[0] == "GET"
                         and c[1].split("?", 1)[0].rstrip("/").endswith("/comments")]
        check(len(list_calls) == 1,
              f"任务集合应只获取一次,实际 {list_calls}")
        check(len(label_calls) == 1,
              f"仓库标签核验仍应实际发生一次,实际 {label_calls}")
        check(len(comment_calls) == 1,
              f"每任务评论核验仍应实际发生,实际 {comment_calls}")
        names = {c["name"] for c in report["checks"]}
        check({"labels-remote-present", "results-consistent",
               "tasks-valid", "deps-consistent"} <= names
              and report["ok"] is True,
              f"github verify 结论应保持:{[c for c in report['checks'] if not c['ok']]}")


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

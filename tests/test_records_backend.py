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

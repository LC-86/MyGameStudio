#!/usr/bin/env python3
"""本地 Markdown 后端行为主题检查的共享准备(任务票 11)。

只放各主题共用的最小准备代码:路径与夹具、读取计数与导入方向探针、
指纹登记助手、CLI 调用与逐任务读取计数器。判定仍由各主题经真实
mgs_records 公开接缝作出,本 module 不复制任何生产规则。每个主题经
make_checker 各自持有失败清单,互不串扰;原总入口聚合各主题清单。
"""

import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
RECORDS_DIR = REPO_ROOT / "plugin" / "records"
sys.path.insert(0, str(RECORDS_DIR))

import mgs_records  # noqa: E402

SAMPLE = REPO_ROOT / "samples" / "role-scope-demo"
CLI = REPO_ROOT / "plugin" / "records" / "mgs_records.py"
FIVE_LABELS = ("needs-triage", "needs-info", "ready-for-agent",
               "ready-for-human", "wontfix")


def make_checker():
    """返回 (FAILURES, check):每个主题独立持有,聚合时不互相污染。"""

    failures: list[str] = []

    def check(condition: bool, message: str) -> None:
        if not condition:
            failures.append(message)

    return failures, check


def run_theme(title: str, tests: tuple, failures: list[str]) -> int:
    """依次运行主题内检查函数,统一打印结果并返回进程退出码。"""

    for test in tests:
        test()
    if failures:
        print(f"FAIL ({len(failures)} 项) [{title}]:")
        for failure in failures:
            print(f"  - {failure}")
        return 1
    print(f"OK: {title} 检查全部通过")
    return 0


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


def run_cli(*args: str) -> subprocess.CompletedProcess:
    return subprocess.run([sys.executable, "-B", str(CLI), *args],
                          capture_output=True, text=True)


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

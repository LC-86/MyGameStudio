#!/usr/bin/env python3
"""GitHub Issues 后端行为主题检查的共享夹具与计数器(任务票 11)。

集中各主题共用的最小准备代码:CONFIG/项目夹具、CLI 进程内 HTTP 替身、
逐任务读取计数器与共享畸形正文。替身传输层见 github_backend_transport.py。
判定仍由各主题经真实 mgs_records/mgs_github 公开接缝作出,本 module 不
复制任何生产规则。每个主题经 make_checker 各自持有失败清单,互不串扰。
"""

import json
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "plugin" / "records"))
sys.path.insert(0, str(REPO_ROOT / "tests"))

import mgs_records  # noqa: E402
import mgs_github  # noqa: E402
from github_backend_transport import FakeTransport  # noqa: E402

CLI = REPO_ROOT / "plugin" / "records" / "mgs_records.py"
FIVE_LABELS = ("needs-triage", "needs-info", "ready-for-agent",
               "ready-for-human", "wontfix")
REPO = "github.com/mygamestudio/issue-accept"
AUTH = (f"{REPO}:issues-write(2026-09-08 开发者授权;仅测试仓库;"
        "范围:任务与结果读写)")


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


CONFIG_TEMPLATE = """# 测试项目:协作配置(GitHub Issues 后端)

维护责任:制作统筹。配置版本:v1。采用依据:测试夹具。

## 任务来源

- 后端:github-issues
- 当前位置:{repo}
- 任务读取规则:GitHub Issues 后端约定(Issue 正文承载任务说明,评论承载结果)
- 外部连接引用及已确认操作范围:{external}

## 标签映射

| 语义 | 项目标签 |
| --- | --- |
| needs-triage | triage |
| needs-info | info |
| ready-for-agent | agent-ready |
| ready-for-human | human-ready |
| wontfix | wont-do |

## 文档映射

| 内容 | 当前权威位置 | 维护角色 |
| --- | --- | --- |
| 项目目标与范围 | docs/mygamestudio/PROJECT.md | 制作统筹 |
| 游戏需求与设计 | docs/mygamestudio/GAME_DESIGN.md | 方案设计 |
| 技术设计 | docs/mygamestudio/TECH_DESIGN.md | 制作实现 |
| 术语、ADR 与历史 | docs/mygamestudio/records/(暂空) | 对应专业角色 |

## 执行条件

- 工程、原型、资源与构建入口:src/
- 可用能力及已验证执行边界:文件读写
- 尚未就绪的能力及影响:无
"""


def make_github_project(root: Path, *, repo: str = REPO,
                        external: str = AUTH) -> Path:
    docs = root / "docs" / "mygamestudio"
    docs.mkdir(parents=True)
    (docs / "CONFIG.md").write_text(
        CONFIG_TEMPLATE.format(repo=repo, external=external), encoding="utf-8")
    for name in ("PROJECT.md", "GAME_DESIGN.md", "TECH_DESIGN.md"):
        (docs / name).write_text(f"# {name}\n\n测试内容\n", encoding="utf-8")
    return root


LOCAL_TASK = """# {title}

任务身份:{identity}。当前分流:{triage}。进度:{progress}。

## 工作请求

- 当前目标:{goal}
- 输入与基线:GAME_DESIGN v1
- 本次交付:示例交付
- 允许修改范围:src/**
- 所需能力:文件读写
- 完成标准:示例标准
- 执行责任:Agent(制作实现)
- 验收方式:代码级检查
- 依赖:{deps}

## 结果索引

{index}

## 状态变化

2026-09-08 测试夹具初始化。
"""


def make_local_project(root: Path) -> Path:
    docs = root / "docs" / "mygamestudio"
    docs.mkdir(parents=True)
    # 本地后端 CONFIG(标签映射沿用同一套项目标签,便于切换后身份/标签语义不变)
    (docs / "CONFIG.md").write_text(
        CONFIG_TEMPLATE.format(repo="REPLACED", external="无").replace(
            "- 后端:github-issues", "- 后端:local-markdown").replace(
            "- 当前位置:REPLACED",
            "- 当前位置:docs/mygamestudio/work/"
            "(每任务一目录,task.md 为工作请求与状态)"), encoding="utf-8")
    for name in ("PROJECT.md", "GAME_DESIGN.md", "TECH_DESIGN.md"):
        (docs / name).write_text(f"# {name}\n\n基线版本:v1。\n", encoding="utf-8")
    work = docs / "work"
    for identity, title, deps in (("01-alpha", "甲任务", "无"),
                                  ("02-beta", "乙任务", "01-alpha")):
        task_dir = work / identity
        task_dir.mkdir(parents=True)
        (task_dir / "task.md").write_text(
            LOCAL_TASK.format(title=title, identity=identity,
                              triage="ready-for-agent", progress="待执行",
                              goal="演示目标", deps=deps, index="(暂无)"),
            encoding="utf-8")
    return root


def run_cli(*args: str, env: dict | None = None) -> subprocess.CompletedProcess:
    import os
    full_env = {**os.environ.copy(), **(env or {})}
    return subprocess.run([sys.executable, "-B", str(CLI), *args],
                          capture_output=True, text=True, env=full_env)


class _StandinServer:
    """把 FakeTransport 挂到进程内 HTTP 端点(真实 UrllibTransport 通路)。"""

    def __init__(self, fake: FakeTransport) -> None:
        from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

        outer = self

        class Handler(BaseHTTPRequestHandler):
            def log_message(self, *args):  # noqa: A003 - 静默测试服务器
                pass

            def _handle(self, method: str) -> None:
                length = int(self.headers.get("Content-Length") or 0)
                raw = self.rfile.read(length) if length else b""
                body = json.loads(raw) if raw else None
                try:
                    status, data = fake.request(method, self.path, body)
                except mgs_github.TransportError as exc:
                    self.send_response(599 if exc.kind == "offline" else 598)
                    self.end_headers()
                    return
                payload = json.dumps(data, ensure_ascii=False).encode("utf-8")
                self.send_response(status)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(payload)))
                self.end_headers()
                self.wfile.write(payload)

            def do_GET(self):     # noqa: N802 - http.server 约定
                self._handle("GET")

            def do_POST(self):    # noqa: N802
                self._handle("POST")

            def do_PATCH(self):   # noqa: N802
                self._handle("PATCH")

        outer.server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)

    @property
    def base(self) -> str:
        return f"http://127.0.0.1:{self.server.server_address[1]}"

    def start(self) -> None:
        import threading
        threading.Thread(target=self.server.serve_forever, daemon=True).start()

    def stop(self) -> None:
        self.server.shutdown()


SHARED_BODY = (
    "# 畸形任务\n\n"
    "任务身份:。当前分流:ready-for-agent。进度:待执行;负责人:张三。\n\n"
    "## 工作请求\n\n"
    "- 当前目标:演示目标\n"
    "- 输入与基线:GAME_DESIGN v1\n"
    "- 本次交付:示例交付\n"
    "- 允许修改范围:src/**\n"
    "- 所需能力:文件读写\n"
    "- 完成标准:\n"
    "- 执行责任:Agent（制作实现）\n"
    "- 验收方式:代码级检查\n"
    "- 依赖:无\n\n"
    "## 未知小节\n\n"
    "未知内容仍需保留\n\n"
    "## 结果索引\n\n"
    "(暂无)\n"
)


def _seed_raw_issue(fake: FakeTransport, body: str | None = None, *,
                    label: str | None = "agent-ready", number: int = 1,
                    labels: list[str] | None = None,
                    identity: str = "05-malformed", title: str = "畸形任务",
                    triage: str = "ready-for-agent", progress: str = "待执行",
                    request: dict | None = None) -> dict:
    """种子 Issue:给 body 则原样写入(畸形/共享正文用例);不给则按给定分流
    与标签用 build_task_body 生成(分流标签规则用例)。labels 优先于单 label
    参数,用于多标签/标签冲突场景。
    """
    if labels is None:
        labels = [label] if label else []
    if body is None:
        request = dict(request or {
            "当前目标": "演示目标", "输入与基线": "GAME_DESIGN v1",
            "本次交付": "示例交付", "允许修改范围": "src/**",
            "所需能力": "文件读写", "完成标准": "示例标准",
            "执行责任": "Agent(制作实现)", "验收方式": "代码级检查"})
        request["依赖"] = "无"
        body = mgs_github.build_task_body(title, identity, triage, progress,
                                          request)
    issue = {"number": number, "id": 1000 + number, "title": title,
             "body": body, "labels": [{"name": n} for n in labels],
             "state": "open", "state_reason": None,
             "html_url": f"https://example.invalid/i/{number}"}
    fake.issues.append(issue)
    fake.comments[number] = []
    return issue


class _ConfigReadCounter:
    """统计本次上下文中 mgs_records 读取 CONFIG 原文的次数。

    通过替换公开入口 ``load_config`` 计数:一次顶层 list/show 调用应当只
    解析一份 CONFIG 原文,不再按相对路径二次读取。
    """

    def __init__(self) -> None:
        self.count = 0

    def __enter__(self) -> "_ConfigReadCounter":
        import mgs_records as _records

        self._real = _records.load_config
        outer = self

        def counting(project_root, config_rel=mgs_records.DEFAULT_CONFIG_REL):
            outer.count += 1
            return outer._real(project_root, config_rel)

        _records.load_config = counting
        return self

    def __exit__(self, *exc: object) -> None:
        import mgs_records as _records

        _records.load_config = self._real

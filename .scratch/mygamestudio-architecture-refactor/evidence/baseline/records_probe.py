#!/usr/bin/env python3
"""票 01 基线探针 B:R1 缺陷证据(合成回放,不启动真实模型/不访问网络)。

复现并记录以下既有现象,作为 R1 的缺陷证据保留(不写成长期正确性断言):
- 一次本地 ready 读取 CONFIG 原文 6 次、每份 task.md 2 次;
- GitHub 后端一次 ready 获取全量任务集合 2 次(2 次 transport 请求);
- 第二次任务读取给出不同依赖时,结果混用第一次任务内容与第二次依赖
  (第一次「依赖:无」、第二次「依赖:02-missing」→ blocked 依赖未解析)。

读取次数用 sys.addaudithook 的 open 事件对读取模式计数(底层真实读取,
不是私有助手调用计数)。GitHub 用本地替身 transport,零网络。

用法:python3 records_probe.py [--out <report.json>]
"""

import argparse
import json
import sys
import tempfile
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(REPO_ROOT / "plugin" / "records"))

import mgs_records  # noqa: E402
import mgs_github  # noqa: E402

FIVE_LABELS = ("needs-triage", "needs-info", "ready-for-agent",
               "ready-for-human", "wontfix")

CONFIG_TEMPLATE = """# 基线项目:协作配置

维护责任:制作统筹。配置版本:v1。采用依据:基线探针夹具。

## 任务来源

- 后端:{backend}
- 当前位置:{location}
- 任务读取规则:基线探针夹具
- 外部连接引用及已确认操作范围:{external}

## 标签映射

| 语义 | 项目标签 |
| --- | --- |
{label_rows}

## 文档映射

| 内容 | 当前权威位置 | 维护角色 |
| --- | --- | --- |
| 项目目标与范围 | docs/mygamestudio/PROJECT.md | 制作统筹 |
| 游戏需求与设计 | docs/mygamestudio/GAME_DESIGN.md | 方案设计 |
| 技术设计 | docs/mygamestudio/TECH_DESIGN.md | 制作实现 |
| 术语、ADR 与历史 | docs/mygamestudio/records/ | 对应专业角色 |

## 执行条件

- 工程、原型、资源与构建入口:src/
- 可用能力及已验证执行边界:文件读写
- 尚未就绪的能力及影响:无
"""

TASK_TEMPLATE = """# {title}

任务身份:{identity}。当前分流:ready-for-agent。进度:待执行。

## 工作请求

- 当前目标:基线探针目标
- 输入与基线:PROJECT.md v1
- 本次交付:示例交付
- 允许修改范围:src/**
- 所需能力:文件读写
- 完成标准:示例标准
- 执行责任:Agent(制作实现)
- 验收方式:代码级检查
- 依赖:{deps}
- 依赖与写入协调:无
- 尚缺信息:无

## 结果索引

(暂无)
"""

# ---------- 底层读取计数(audit hook) ----------

_COUNTERS: dict[str, dict[str, int]] = {}


def _audit_hook(event: str, args: tuple) -> None:
    if event != "open" or not _COUNTERS:
        return
    raw = args[0]
    if isinstance(raw, bytes):
        raw = raw.decode("utf-8", "replace")
    mode = args[1] if len(args) > 1 and isinstance(args[1], str) else ""
    if "r" not in mode and "+" not in mode:
        return  # 只计读取;写入夹具不计入被观测读取
    try:
        path = Path(raw).resolve()
    except OSError:
        return
    for root, counts in _COUNTERS.items():
        try:
            rel = path.relative_to(Path(root))
        except ValueError:
            continue
        counts[str(rel)] = counts.get(str(rel), 0) + 1


sys.addaudithook(_audit_hook)


class read_counter:
    """上下文:统计 root 内按相对路径的读取型 open 次数。"""

    def __init__(self, root: Path) -> None:
        self.root = str(Path(root).resolve())
        self.counts: dict[str, int] = {}

    def __enter__(self) -> "read_counter":
        _COUNTERS[self.root] = self.counts
        return self

    def __exit__(self, *exc: object) -> None:
        _COUNTERS.pop(self.root, None)

    def by_name(self) -> dict[str, int]:
        result: dict[str, int] = {}
        for rel, count in self.counts.items():
            name = Path(rel).name
            result[name] = result.get(name, 0) + count
        return result


# ---------- 夹具 ----------

def make_project(tmp: Path, *, backend: str = "local-markdown") -> Path:
    tmp.mkdir(parents=True, exist_ok=True)
    docs = tmp / "docs" / "mygamestudio"
    docs.mkdir(parents=True, exist_ok=True)
    location = ("github.com/mygamestudio/baseline"
                if backend == "github-issues"
                else "docs/mygamestudio/work/")
    (docs / "CONFIG.md").write_text(
        CONFIG_TEMPLATE.format(
            backend=backend, location=location,
            external=("github.com/mygamestudio/baseline:issues-write"
                      "(基线探针;仅本地替身)" if backend == "github-issues" else "无"),
            label_rows="\n".join(f"| {n} | {n} |" for n in FIVE_LABELS)),
        encoding="utf-8")
    for name in ("PROJECT.md", "GAME_DESIGN.md", "TECH_DESIGN.md"):
        (docs / name).write_text(f"# {name}\n\n基线探针夹具。\n", encoding="utf-8")
    return tmp


def write_local_task(root: Path, identity: str, *, title: str, deps: str) -> None:
    task_dir = root / "docs" / "mygamestudio" / "work" / identity
    task_dir.mkdir(parents=True, exist_ok=True)
    (task_dir / "task.md").write_text(
        TASK_TEMPLATE.format(title=title, identity=identity, deps=deps),
        encoding="utf-8")


class BaselineTransport:
    """GitHub REST 极小子集替身:按调用序号逐次返回预先准备的 Issue 列表。"""

    def __init__(self, task_lists: list[list[dict]]) -> None:
        self.task_lists = task_lists
        self.requests = 0
        self.get_log: list[str] = []

    def request(self, method: str, path: str, body: dict | None = None,
                *, auth: bool = True):
        self.requests += 1
        self.get_log.append(f"{method} {path}")
        plain = path.split("?", 1)[0].rstrip("/")
        if method == "GET" and plain.endswith("issues"):
            index = min(len(self.task_lists), max(0, self._issue_list_calls() - 1))
            return 200, self.task_lists[index]
        return 404, {"message": "baseline stand-in has no such route"}

    def _issue_list_calls(self) -> int:
        return sum(1 for entry in self.get_log
                   if entry.startswith("GET") and "issues" in entry)


def issue(identity: str, *, deps: str, number: int) -> dict:
    body = mgs_github.build_task_body(
        "基线任务", identity, "ready-for-agent", "待执行",
        {"当前目标": "基线探针目标", "输入与基线": "PROJECT.md v1",
         "本次交付": "示例交付", "允许修改范围": "src/**",
         "所需能力": "文件读写", "完成标准": "示例标准",
         "执行责任": "Agent(制作实现)", "验收方式": "代码级检查",
         "依赖": deps})
    return {"number": number, "id": 1000 + number, "title": "基线任务",
            "body": body, "labels": [{"name": "ready-for-agent"}],
            "state": "open", "state_reason": None,
            "html_url": f"https://example.invalid/{number}"}


# ---------- 探针 ----------

def probe_local_no_change(workdir: Path) -> dict:
    """静态输入:一次本地 ready 的读取次数与最终分类。"""

    root = make_project(workdir / "local-static")
    write_local_task(root, "01-alpha", title="甲任务", deps="无")
    with read_counter(root) as counter:
        result = mgs_records.startable_tasks(root)
    return {
        "probe": "ready",
        "backend": "local-markdown",
        "reads": counter.by_name(),
        "startable": [item["identity"] for item in result["startable"]],
        "blocked": [item["identity"] for item in result["blocked"]],
    }


def probe_local_r1(workdir: Path) -> dict:
    """R1:第二次任务读取给出新依赖时,结果混用两个时点。"""

    root = make_project(workdir / "local-r1")
    write_local_task(root, "01-alpha", title="甲任务", deps="无")

    real_list = mgs_records.list_tasks
    state = {"calls": 0}

    def wrapper(*args, **kwargs):
        state["calls"] += 1
        if state["calls"] == 2:
            # 第二次任务读取看到更新后的正文(新增一个不存在的依赖)
            write_local_task(root, "01-alpha", title="甲任务", deps="02-missing")
        return real_list(*args, **kwargs)

    mgs_records.list_tasks = wrapper
    try:
        with read_counter(root) as counter:
            result = mgs_records.startable_tasks(root)
    finally:
        mgs_records.list_tasks = real_list
    blocked = next((item for item in result["blocked"]
                    if item["identity"] == "01-alpha"), None)
    return {
        "probe": "ready-changing-second-fetch",
        "backend": "local-markdown",
        "task_list_reads": state["calls"],
        "reads": counter.by_name(),
        "first_fetch_deps": "无",
        "second_fetch_deps": "02-missing",
        "result_side": "blocked" if blocked else "startable",
        "blocked": blocked,
    }


def probe_github(workdir: Path) -> dict:
    """GitHub 后端:一次 ready 的任务集合获取次数;以及第二次响应改变依赖。"""

    root = make_project(workdir / "github", backend="github-issues")
    first = [issue("01-alpha", deps="无", number=1)]
    second = [issue("01-alpha", deps="02-missing", number=1)]
    fake = BaselineTransport([first, second])
    with read_counter(root) as counter:
        result = mgs_records.startable_tasks(root, transport=fake)
    blocked = next((item for item in result["blocked"]
                    if item["identity"] == "01-alpha"), None)
    return {
        "probe": "ready-changing-second-fetch",
        "backend": "github-issues",
        "transport_task_list_requests": fake._issue_list_calls(),
        "transport_total_requests": fake.requests,
        "reads": counter.by_name(),
        "first_fetch_deps": "无",
        "second_fetch_deps": "02-missing",
        "result_side": "blocked" if blocked else "startable",
        "blocked": blocked,
        "network_requests_to_remote": 0,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out")
    args = parser.parse_args()
    with tempfile.TemporaryDirectory(prefix="mgs-baseline-records-") as tmp:
        workdir = Path(tmp)
        report = {
            "evidence_kind": "synthetic_replay",
            "scope": ("合成 /tmp 夹具;GitHub 用本地替身 transport;零网络;"
                      "不启动真实模型;不进行任何远端写入"),
            "observations": [
                probe_local_no_change(workdir),
                probe_local_r1(workdir),
                probe_github(workdir),
            ],
            "status": ("observed baseline:上述为既有缺陷证据(复现用单独探针),"
                       "不作为长期正确性断言"),
        }
    text = json.dumps(report, ensure_ascii=False, indent=2)
    if args.out:
        Path(args.out).write_text(text + "\n", encoding="utf-8")
    else:
        print(text)
    return 0


if __name__ == "__main__":
    sys.exit(main())

#!/usr/bin/env python3
"""票 01 基线探针 B:R1 缺陷证据与运行时读取计数(合成回放,零网络)。

复现并记录以下既有现象,作为 R1 的缺陷证据保留(不写成长期正确性断言):
- 一次本地 ready 读取 CONFIG 原文 6 次、每份 task.md 2 次;
- GitHub 后端一次 ready 获取全量任务集合 2 次(2 次 transport 请求);
- 第二次任务读取给出不同依赖时,结果混用第一次任务内容与第二次依赖
  (第一次「依赖:无」、第二次「依赖:02-missing」→ blocked 依赖未解析)。

另复算前置证据 evidence/baseline.json 曾记录的受控写入运行时读取计数
(runtime-write / runtime-remote-read),用审计钩子在临时 runtime root 上
回放同形调用,不触及生产代码、不访问网络:
- runtime-write:policy.json 文本 2 次、instances.json 文本 2 次、
  policy.json 字节 1 次,决策 allow;
- runtime-remote-read:再加 remote.json 文本 1 次、CONFIG.md 文本 2 次。

读取次数用 sys.addaudithook 的 open 事件对读取模式计数(底层真实读取,
不是私有助手调用计数)。GitHub 用本地替身 transport,零网络。

用法:python3 records_probe.py [--out <report.json>]
"""

import json
import os
import sys
import tempfile
from pathlib import Path

from baseline_common import (REPO_ROOT, emit, make_project, parse_out_args,
                             write_local_task)

sys.path.insert(0, str(REPO_ROOT / "plugin" / "records"))
sys.path.insert(0, str(REPO_ROOT / "plugin" / "runtime"))

import mgs_records  # noqa: E402
import mgs_github  # noqa: E402
import mgs_runtime  # noqa: E402

# ---------- 底层读取计数(audit hook) ----------

_COUNTERS: dict[str, dict[str, int]] = {}


def _audit_hook(event: str, args: tuple) -> None:
    if event != "open" or not _COUNTERS:
        return
    raw = args[0]
    if isinstance(raw, bytes):
        raw = raw.decode("utf-8", "replace")
    elif not isinstance(raw, (str, os.PathLike)):
        return  # 文件描述符等非路径形态(os.fdopen)不计入
    mode = args[1] if len(args) > 1 and isinstance(args[1], str) else ""
    if not mode.startswith("r"):
        return  # 只计纯读取;锁文件 a+、夹具写入等不计入被观测读取
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
        """按文件名聚合纯读取次数(text/bytes 形态合并为同一文件的总读取数)。

        说明:CPython 3.14 的 `Path.read_bytes()` 触发的 open 事件 mode 为
        `"r"`(非 `"rb"`),故本探针不区分文本/字节形态,只报文件级总读取数;
        前置证据的 text/bytes 拆分见报告「未验证限制」。
        """

        result: dict[str, int] = {}
        for rel, count in self.counts.items():
            name = Path(rel).name
            result[name] = result.get(name, 0) + count
        return result


class BaselineTransport:
    """GitHub REST 极小子集替身:按调用序号逐次返回预先准备的 Issue 列表。"""

    def __init__(self, task_lists: list[list[dict]]) -> None:
        self.task_lists = task_lists
        self.requests = 0
        self.request_log: list[str] = []  # 全部请求的方法与路径(非仅 GET)

    def request(self, method: str, path: str, body: dict | None = None,
                *, auth: bool = True):
        self.requests += 1
        self.request_log.append(f"{method} {path}")
        plain = path.split("?", 1)[0].rstrip("/")
        if method == "GET" and plain.endswith("issues"):
            index = min(len(self.task_lists), max(0, self._issue_list_calls() - 1))
            return 200, self.task_lists[index]
        return 404, {"message": "baseline stand-in has no such route"}

    def _issue_list_calls(self) -> int:
        return sum(1 for entry in self.request_log
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


# ---------- 受控写入运行时读取计数(F6,复算前置观测) ----------

class ReadOnlyFakeTransport:
    """远端读取替身:按 GET 路径返回列表 / 单 Issue / 空评论集;零网络。"""

    def __init__(self, list_payload: list[dict], issue_payload: dict) -> None:
        self.list_payload = list_payload
        self.issue_payload = issue_payload
        self.request_log: list[str] = []

    def request(self, method: str, path: str, body: dict | None = None,
                *, auth: bool = True):
        self.request_log.append(f"{method} {path}")
        plain = path.split("?", 1)[0].rstrip("/")
        if method == "GET" and plain.endswith("issues"):
            return 200, self.list_payload
        if method == "GET" and plain.endswith("comments"):
            return 200, []
        if method == "GET" and "/issues/" in plain:
            return 200, self.issue_payload
        return 404, {"message": "baseline stand-in has no such route"}


def probe_runtime_write(workdir: Path) -> dict:
    """回放一次受控本地写入,计数 policy/instances/policy 字节读取。

    与前置证据 evidence/baseline.json 的 runtime-write 同形:调用
    GateService.write() 的只读检查 + 落盘路径,项目与运行根都在 /tmp,
    零网络、零真实远端写入(写入只落在临时项目内)。
    """

    project = workdir / "runtime-write-project"
    (project / "docs" / "mygamestudio" / "work" / "01-alpha").mkdir(parents=True,
                                                                    exist_ok=True)
    runtime_root = workdir / "runtime-write"
    service = mgs_runtime.GateService(runtime_root)
    service.init_policy(project_root=project,
                        roles={"producer": ["docs/mygamestudio/work/*/task.md"]},
                        purposes={"production": None})
    instance = service.create_instance(
        role="producer", task="01-alpha", purpose="production",
        resources=["docs/mygamestudio/work/01-alpha/task.md"], ttl_seconds=1800)
    with read_counter(runtime_root) as counter:
        result = service.write(instance.token, "docs/mygamestudio/work/01-alpha/task.md",
                               "# 基线探针\n\n受控写入合成回放。\n")
    return {
        "probe": "runtime-write",
        "decision": result.get("decision"),
        "reads": counter.by_name(),
        "counted_scope": "runtime root 内按文件名的读取型 open 次数",
        "note": ("合成回放;临时项目内本地写入;零网络、零真实远端写入;"
                 "策略/实例登记为夹具"),
    }


def probe_runtime_remote_read(workdir: Path) -> dict:
    """回放一次受控远端读取,计数 policy/instances/remote/CONFIG 读取。

    与前置证据 evidence/baseline.json 的 runtime-remote-read 同形:经
    GateService.remote_record(read) 走完整校验与审计路径,但远端用本地
    替身 transport(零网络);CONFIG 与运行根都在 /tmp。
    """

    project = make_project(workdir / "runtime-remote-project",
                           backend="github-issues")
    runtime_root = workdir / "runtime-remote"
    service = mgs_runtime.GateService(runtime_root)
    resource = "github://github.com/mygamestudio/baseline/issues"
    service.init_policy(project_root=project,
                        roles={"producer": [resource + "/**"]},
                        purposes={"production": None})
    instance = service.create_instance(
        role="producer", task="01-alpha", purpose="production",
        resources=[resource], ttl_seconds=1800)
    (runtime_root / "remote.json").write_text(json.dumps({
        "github": {"api_base": "https://example.invalid/api",
                   "token_env": "MGS_BASELINE_TOKEN"}}, ensure_ascii=False),
        encoding="utf-8")
    fake = ReadOnlyFakeTransport([issue("01-alpha", deps="无", number=1)],
                                 issue("01-alpha", deps="无", number=1))
    with read_counter(runtime_root) as runtime_counter, \
            read_counter(project) as project_counter:
        result = service.remote_record(instance.token, "read",
                                       {"identity": "01-alpha"}, transport=fake)
    counts = dict(runtime_counter.by_name())
    for name, count in project_counter.by_name().items():
        counts[name] = counts.get(name, 0) + count
    return {
        "probe": "runtime-remote-read",
        "decision": result.get("decision"),
        "reads": counts,
        "transport_calls": len(fake.request_log),
        "network_requests_to_remote": 0,
        "counted_scope": "runtime root 内按文件名的读取型 open 次数",
        "note": ("合成回放;远端用本地替身 transport;零网络、零真实远端写入;"
                 "策略/实例登记/CONFIG 为夹具"),
    }


def main() -> int:
    args = parse_out_args(__doc__)
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
                probe_runtime_write(workdir),
                probe_runtime_remote_read(workdir),
            ],
            "prior_evidence_replay": {
                "source": ".scratch/mygamestudio-architecture-refactor/evidence/baseline.json",
                "counted_objects": ["runtime-write", "runtime-remote-read"],
                "note": ("前置证据的受控写入运行时读取计数本次用同形合成回放"
                         "复算;策略/实例/远端配置均为 /tmp 夹具,远端为本地替身,"
                         "零网络。前置证据中 CONFIG.md 的读取由 runtime-remote-read"
                         "携带,本次一并计数。"),
            },
            "status": ("observed baseline:ready 相关条目为既有缺陷证据(复现用单独"
                       "探针),不作为长期正确性断言;runtime 计数为前置观测的本次"
                       "复算,零网络/零真实写入"),
        }
    emit(report, args.out)
    return 0


if __name__ == "__main__":
    sys.exit(main())

#!/usr/bin/env python3
"""GitHub Issue 正文的读写形态与仓库级授权核对(票 20)。

把 GitHub 适配器 ``mgs_github`` 中「Issue 正文 ↔ 任务记录」的序列化/解析,
以及「项目 CONFIG 是否对目标仓库授权某远端操作」的核对,从业务适配器里
按职责移出:适配器只在自己的公开写接缝上调用本模块,不再自持正文格式与
授权交集规则。移动是纯整理——相同的记录格式、相同的错误身份与相同的
授权结论,由现有后端生命周期检查逐条证明未改变。

职责:
- ``build_task_body`` / ``parse_issue_body`` / ``parse_issue_payload``:
  Issue 正文与本地 ``work/task.md`` 使用同一套共同正文规则(读面与写面的
  唯一定义在 ``mgs_record_model``),本模块只做 GitHub 存储字段的补齐;
- ``authorization_for``:按 CONFIG 外部访问声明核对明确到
  host/owner/repository 的 ``issues-write`` 授权(仅选择后端不构成授权);
- ``parse_repo_location``:GitHub 公开接缝上的仓库坐标解析,把共同错误
  转成 ``GithubRecordsError``,既有捕获分支保持。

依赖纪律:只依赖中性记录 module ``mgs_record_model``、来源 module
``mgs_record_source`` 与最底层传输/错误接缝 ``mgs_github_transport``;
不导入业务适配器 ``mgs_github``(适配器正向依赖本模块)或查询组织。
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import mgs_record_model  # noqa: E402
import mgs_record_source  # noqa: E402
from mgs_record_model import CANONICAL_LABELS, RecordsError, today  # noqa: E402
from mgs_github_transport import GithubRecordsError  # noqa: E402

HISTORY_MARK = "迁移状态:readonly-history"
PENDING_SWITCH_MARK = "迁移状态:pending-switch"

_RECORD_HEADER_RE = re.compile(r"^(?:规格身份|讨论身份|快照身份):", re.M)


def is_record_carrier(body: str) -> bool:
    """正文以行首正式元数据头承载规格/讨论/快照记录。

    只认元数据头,不认正文任意位置的子串:普通任务的工作请求里
    出现 ``规格身份:overall`` 这类字样时,任务本身仍是任务。
    """

    return bool(_RECORD_HEADER_RE.search(body or ""))


def is_pending_switch(body: str) -> bool:
    """待切换迁移成果:现行读取应跳过,不能充当当前来源。"""

    return PENDING_SWITCH_MARK in (body or "")


def is_historical_source(body: str) -> bool:
    """切换后的旧原件:只读历史,不能充当当前来源。"""

    return HISTORY_MARK in (body or "")


def skip_from_current_reads(body: str) -> bool:
    """现行读取跳过待切换成果与只读历史原件。"""

    return is_pending_switch(body) or is_historical_source(body)


def authorization_for(config: dict, op: str) -> tuple[bool, str]:
    """核对本项目 CONFIG 是否对目标仓库授权了 op(issues-write)。

    返回 (是否授权, 说明):未授权时说明为何拒绝——选择 GitHub 后端不等于
    批准远端写入,需按 `host/owner/repo:issues-write(说明)` 记录授权。
    """

    scopes = mgs_record_source.parse_remote_authorizations(config.get("external", ""))
    repo = config["repo"]
    hit = [s for s in scopes if s["host"] == repo["host"]
           and s["owner"] == repo["owner"] and s["repo"] == repo["repo"]
           and op in s["ops"]]
    if not hit:
        return False, (
            f"CONFIG 外部访问未对 {repo['host']}/{repo['owner']}/{repo['repo']}"
            f" 授权 {op}:选择 GitHub 后端不等于批准远端写入;"
            "需在初始化清单确认后按 `host/owner/repo:issues-write(说明)` 记录授权")
    return True, hit[0].get("note", "")


def parse_repo_location(value: str) -> dict:
    """解析明确的 GitHub host/owner/repository;含糊位置直接拒绝。

    实现归 ``mgs_record_source``(协作配置职责);此处保持 GitHub 公开接缝的
    错误身份——含糊位置仍可被 ``GithubRecordsError`` 捕获。
    """

    try:
        return mgs_record_source.parse_repo_location(value)
    except RecordsError as exc:
        raise GithubRecordsError(str(exc)) from exc


def build_task_body(title: str, identity: str, triage: str, progress: str,
                    request: dict, index: str = "(暂无)",
                    changes: list[str] | None = None) -> str:
    """把任务字段渲染为与 work/task.md 同格式的 Issue 正文。"""

    lines = [f"# {title}", "",
             f"任务身份:{identity}。当前分流:{triage}。进度:{progress}。", "",
             "## 工作请求", ""]
    for key, value in request.items():
        lines.append(f"- {key}:{value}")
    lines += ["", "## 结果索引", "", index, "", "## 状态变化", ""]
    lines += changes or [f"{today()} 经统一接口建立 GitHub Issues 任务记录。"]
    return "\n".join(lines) + "\n"


def parse_issue_payload(item: dict, label_map: dict) -> dict:
    """GitHub Issue 原始对象 → 任务记录(parse_issue_body 的字典薄包装)。

    原生字段(负责人、父子、开放阻塞摘要)一并回读;认领以 assignees 为准。
    """

    record = parse_issue_body(
        item.get("number", 0), item.get("body") or "",
        [label.get("name", "") for label in item.get("labels", [])],
        item.get("state", "open"), item.get("state_reason"),
        label_map, issue_id=item.get("id"))
    assignees = [entry.get("login") for entry in (item.get("assignees") or [])
                 if entry.get("login")]
    record["assignees"] = assignees
    record["claim"] = assignees[0] if assignees else (record.get("claim") or "未认领")
    parent = item.get("parent") or {}
    record["parent_issue_number"] = parent.get("number")
    summary = ((item.get("issue_dependencies_summary") or {}).get("blocked_by")
               or {})
    record["open_blocker_count"] = int(summary.get("total_count") or 0)
    return record


def parse_issue_body(number: int, body: str, labels: list[str],
                     state: str, state_reason: str | None,
                     label_map: dict[str, str], issue_id: int | None = None) -> dict:
    """Issue → 与本地后端同形的任务记录(身份/分流/进度语义一致)。

    共同正文字段(身份/标题/进度/工作请求/小节/结果索引)由中性记录
    module 的 parse_task_body 解析——与本地 work/task.md 同一套规则;
    本函数只补齐 GitHub 存储专有字段(Issue 号/标签/triage 来源与冲突/
    关闭状态/原始正文)。标签承载分流(经 CONFIG 映射回五类语义),与正文
    头部不一致时以标签为准并把差异列入 triage_source 说明。
    """

    record = mgs_record_model.parse_task_body(body or "")
    reverse = {proj: canon for canon, proj in label_map.items()}
    from_labels = [reverse.get(label, label) for label in labels]
    triage_label = next((t for t in from_labels if t in CANONICAL_LABELS), None)
    triage_body = mgs_record_model._field(
        "\n".join(mgs_record_model._header_lines(body or "")[0]), "当前分流")
    # 键序沿用既有公开返回顺序(JSON 结构兼容):共同字段来自共享解析,
    # GitHub 专有字段在对应位置插入。
    return {
        "identity": record["identity"],
        "title": record["title"],
        "triage": triage_label or triage_body or "",
        "progress": record["progress"],
        "issue_number": number,
        "issue_id": issue_id,
        "state": state,
        "state_reason": state_reason,
        "labels": list(labels),
        "triage_source": ("label" if triage_label else
                          "body" if triage_body else "missing"),
        "triage_conflict": bool(triage_label and triage_body
                                and triage_label != triage_body),
        "request": record["request"],
        "sections": record["sections"],
        "results": [],  # 列表层不拉评论;read_task 单独补齐
        "result_index_text": record["result_index_text"],
        "body": body or "",
    }

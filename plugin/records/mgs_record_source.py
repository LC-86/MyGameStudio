#!/usr/bin/env python3
"""MyGameStudio 协作配置与本地任务来源(票 03)。

本模块把「从哪读、读到什么」这组职责集中到一处:协作配置(CONFIG 原文的
后端、任务位置、标签映射与文档映射解析)、仓库坐标与远端授权声明的文本
解析,以及本地 Markdown 任务 adapter(按目录列举、按目录读取单个任务)。
它同时是本地来源(document 与任务)的唯一定义位置,查询组织
``mgs_records`` 与 GitHub adapter ``mgs_github`` 都从这里取配置和本地任务,
而不是反向互相调用。

依赖纪律(第一阶段设计):
- 只依赖中性记录 module ``mgs_record_model``(共同正文规则与错误身份);
- 不导入查询组织 ``mgs_records`` 或后端适配器 ``mgs_github``(两者都依赖
  本模块;本模块不反向依赖它们,也不靠延迟导入掩盖方向);
- 本地 adapter 只读,不提供写入;解析出的授权声明不是写入许可——真正的
  受控写入仍在运行保障的锁内重读 CONFIG 与实例状态;
- 已加载配置只服务本次调用:``local_list_tasks`` / ``local_read_task`` 接收
  本次已解析配置,不再各自重读 CONFIG;返回的配置字典保持既有公开字段,
  原始 CONFIG 文本不经公开返回外泄(见 ``load_config_document``)。
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from mgs_record_model import (  # noqa: E402  (路径调整后导入)
    IDENTITY_RE, RecordsError, _bullets, _sections, parse_task_body)

DEFAULT_CONFIG_REL = "docs/mygamestudio/CONFIG.md"
# 本地 Markdown 任务根(《项目目录模板》默认布局;github→local 迁移的
# 目标任务根,与 CONFIG 任务根、文件落点、返回路径共用同一常量;
# 与解析后的 task_root 同为无尾斜杠形态)
DEFAULT_TASK_ROOT = "docs/mygamestudio/work"
SUPPORTED_BACKENDS = ("local-markdown", "github-issues")
WRITE_OP = "issues-write"


# ---------- 仓库坐标与远端授权声明(文本解析,不依赖 GitHub 执行实现) ----------

_REPO_RE = re.compile(
    r"^(?:https?://)?([A-Za-z0-9][A-Za-z0-9.-]*\.[A-Za-z]{2,}|localhost)"
    r"(?::\d+)?/([A-Za-z0-9._-]+)/([A-Za-z0-9._-]+?)(?:\.git)?/?$")


def parse_repo_location(value: str) -> dict:
    """解析明确的 host/owner/repository;含糊位置直接拒绝。

    接受 `host/owner/repo` 与 `https://host/owner/repo`;拒绝缺 host、
    缺段或多段的位置(不扫描、不猜测无关仓库)。错误用共同记录错误身份
    ``RecordsError``;GitHub adapter 在其公开接缝上转为 ``GithubRecordsError``。
    """

    text = (value or "").strip()
    match = _REPO_RE.fullmatch(text)
    if match is None:
        raise RecordsError(
            f"GitHub 任务位置必须明确到 host/owner/repository,当前为 {text!r}"
            "(不接受含糊位置,不扫描无关仓库)")
    return {"host": match.group(1).lower(), "owner": match.group(2),
            "repo": match.group(3)}


_REPO_FIND_RE = re.compile(
    r"(?:https?://)?([A-Za-z0-9][A-Za-z0-9.-]*\.[A-Za-z]{2,}|localhost)"
    r"(?::\d+)?/([A-Za-z0-9._-]+)/([A-Za-z0-9._-]+?)(?:\.git)?(?=[/?:;)\s]|$)")


def parse_remote_authorizations(text: str) -> list[dict]:
    """解析外部访问行中的远端授权条目。

    写授权条目形如 `host/owner/repo:issues-write(说明)`——必须明确到
    仓库并带 issues-write 标记;仅出现仓库坐标(无 issues-write)视为
    只读引用,不是写授权。写授权按「仓库坐标之后、下一坐标之前」的
    片段判定,说明文字里的分号不破坏解析。
    """

    matches = list(_REPO_FIND_RE.finditer(text or ""))
    entries: dict[tuple[str, str, str], dict] = {}
    for index, match in enumerate(matches):
        end = matches[index + 1].start() if index + 1 < len(matches) else len(text)
        segment = text[match.end():end]
        key = (match.group(1).lower(), match.group(2), match.group(3))
        note = ""
        paren = re.search(r"[（(]([^）)]*)[)）]", segment)
        if paren:
            note = paren.group(1)
        entries[key] = {
            "host": key[0], "owner": key[1], "repo": key[2],
            "ops": ("issues-write" if WRITE_OP in segment else "reference"),
            "note": note,
        }
    return list(entries.values())


# ---------- CONFIG 表格解析 ----------

def _table_rows(lines: list[str]) -> list[list[str]]:
    """解析 Markdown 表格(跳过表头与分隔行)。"""

    rows: list[list[str]] = []
    for line in lines:
        if not line.startswith("|"):
            continue
        cells = [cell.strip() for cell in line.strip().strip("|").split("|")]
        if all(re.fullmatch(r":?-{2,}:?", cell) for cell in cells):
            continue
        rows.append(cells)
    return rows[1:]  # 第一行是表头


def _strip_annotation(value: str) -> str:
    """去掉位置标注括号(半角/全角),如 `docs/x/(暂空)` → `docs/x`。"""

    for mark in ("(", "\uff08"):  # 第二项为全角左括号
        index = value.find(mark)
        if index >= 0:
            value = value[:index]
    return value.strip().rstrip("/").strip()


def _parse_config_text(text: str, config_path: Path, root: Path,
                       config_rel: str) -> dict:
    """由同一份 CONFIG 原文解析字段与远端写入授权(执行条件来源)。"""

    sections = _sections(text)
    source = _bullets(sections.get("任务来源", []))
    backend = source.get("后端", "").strip().lower()
    task_root = _strip_annotation(source.get("当前位置", ""))
    external = source.get("外部连接引用及已确认操作范围", "")
    repo = None
    if backend == "github-issues":
        # 仓库坐标与授权声明的文本解析归属本模块(不反向依赖 GitHub adapter)。
        repo = parse_repo_location(task_root)
        remote_write_authorized = any(
            WRITE_OP in scope["ops"]
            for scope in parse_remote_authorizations(external)
            if (scope["host"], scope["owner"], scope["repo"])
            == (repo["host"], repo["owner"], repo["repo"]))
    else:
        remote_write_authorized = False
    labels: dict[str, str] = {}
    for cells in _table_rows(sections.get("标签映射", [])):
        if len(cells) >= 2:
            labels[cells[0]] = cells[1]
    docmap = []
    for cells in _table_rows(sections.get("文档映射", [])):
        if len(cells) >= 3:
            docmap.append({"content": cells[0],
                           "path": _strip_annotation(cells[1]),
                           "role": cells[2]})
    if not backend:
        raise RecordsError(f"协作配置缺少「任务来源/后端」:{config_path}")
    return {
        "project_root": str(root),
        "config_path": config_rel,
        "backend": backend,
        "task_root": task_root,
        "repo": repo,
        "remote_write_authorized": remote_write_authorized,
        "labels": labels,
        "docmap": docmap,
        "external": external,
    }


def load_config_document(project_root: Path | str,
                         config_rel: str = DEFAULT_CONFIG_REL) -> tuple[dict, str]:
    """读一次 CONFIG 原文,由同一原文解析配置字段与执行条件文本。

    返回 (config, text):``text`` 供本次调用内派生执行条件(如「尚未就绪的
    能力及影响」)与文档判断复用,不属于公开返回,也不跨调用缓存——下一次
    顶层调用重新读取。这是为「同一次判断只用同一份原文」预留的来源接缝。
    """

    root = Path(project_root)
    config_path = root / config_rel
    if not config_path.is_file():
        raise RecordsError(f"缺少协作配置:{config_path}(项目根 {root})")
    try:
        text = config_path.read_text(encoding="utf-8")
    except OSError as exc:
        raise RecordsError(f"协作配置不可读:{config_path}:{exc}") from exc
    return _parse_config_text(text, config_path, root, config_rel), text


def load_config(project_root: Path | str,
                config_rel: str = DEFAULT_CONFIG_REL) -> dict:
    """读取协作配置:后端、任务位置、标签映射与文档映射。"""

    return load_config_document(project_root, config_rel)[0]


# ---------- 本地 Markdown 记录 adapter(只读) ----------

def _task_root(project_root: Path, config: dict) -> Path:
    """把 CONFIG 任务根解析成项目根内的路径;越权任务根一律拒绝。

    CONFIG 是不可信输入:task_root 写成绝对路径或含 ``..`` 时,
    ``project_root / task_root`` 会解析到项目根之外,读写都会随之
    逃逸。这里统一收紧:解析后必须仍留在项目根内,否则按共同记录
    错误身份拒绝(本地来源的唯一定义位置,读写共用同一约束)。
    """

    root = Path(project_root)
    candidate = root / str(config.get("task_root") or "")
    try:
        candidate.resolve().relative_to(root.resolve())
    except ValueError as exc:
        raise RecordsError(
            f"任务根必须留在项目根内:{config.get('task_root')!r}"
            "(绝对路径与 .. 逃逸一律拒绝)") from exc
    return candidate


def _parse_task_file(project_root: Path, task_dir: Path) -> dict | None:
    task_path = task_dir / "task.md"
    if not task_path.is_file():
        return None
    text = task_path.read_text(encoding="utf-8")
    # 共同正文规则来自中性记录 module(与 GitHub 后端同一实现);本地
    # adapter 只补齐目录、结果文件与相对路径等存储专有字段。键序沿用
    # 既有公开返回顺序,不改变 JSON 输出结构。
    record = parse_task_body(text)
    results_dir = task_dir / "results"
    results = []
    if results_dir.is_dir():
        results = sorted(
            f"results/{path.name}"
            for path in results_dir.iterdir() if path.is_file())
    return {
        "identity": record["identity"],
        "title": record["title"],
        "triage": record["triage"],
        "progress": record["progress"],
        "claim": record.get("claim") or "未认领",
        "close_reason": record.get("close_reason") or "无",
        "directory": task_dir.name,
        "request": record["request"],
        "sections": record["sections"],
        "results": results,
        "result_index_text": record["result_index_text"],
        "path": str(task_path.relative_to(project_root)),
    }


def local_list_tasks(project_root: Path | str, config: dict) -> list[dict]:
    """按已加载配置列举本地任务,保持目录顺序(不重读 CONFIG)。

    已加载配置只服务本次调用;调用方(查询组织)决定何时读取。只列举
    task.md 存在的任务目录,不扫描其他后端来源。
    """

    root = Path(project_root)
    task_root = _task_root(root, config)
    tasks = []
    if task_root.is_dir():
        for task_dir in sorted(task_root.iterdir()):
            if not task_dir.is_dir():
                continue
            parsed = _parse_task_file(root, task_dir)
            if parsed is not None:
                tasks.append(parsed)
    tasks.sort(key=lambda task: task["directory"])
    return tasks


def local_task_dir(project_root: Path | str, config: dict,
                   identity: str) -> Path:
    """把任务身份解析成任务根下的目录;拒绝越权路径。"""

    if not identity or not IDENTITY_RE.fullmatch(identity):
        raise RecordsError(
            f"任务身份必须形如 NN-<slug>,当前 {identity!r}")
    root = Path(project_root)
    task_root = _task_root(root, config)
    candidate = task_root / identity
    try:
        candidate.resolve().relative_to(task_root.resolve())
    except ValueError as exc:
        raise RecordsError(
            f"任务身份不得离开任务根:{identity!r}") from exc
    return candidate


def local_read_task(project_root: Path | str, config: dict,
                    task_id: str) -> dict:
    """按目录定位读取单个本地任务(不扫描无关任务,不重读 CONFIG)。

    与既有语义一致:目录名即定位键,即使目录名与正文身份不一致也按目录
    读取;目录缺失或没有 task.md 时以同一错误表达。身份必须落在任务根内。
    """

    root = Path(project_root)
    task_dir = local_task_dir(root, config, task_id)
    parsed = _parse_task_file(root, task_dir) if task_dir.is_dir() else None
    if parsed is None:
        raise RecordsError(f"任务不存在或缺少 task.md:{task_dir}")
    return parsed

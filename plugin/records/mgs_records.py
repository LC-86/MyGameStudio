#!/usr/bin/env python3
"""MyGameStudio 本地 Markdown 任务后端:统一回读接口(任务票 04)。

对应设计《工作记录合同》「后端接口」一节在本地 Markdown 后端上的最小实现:
读取配置、列出任务、读取任务与结果、回读核验。调用方只使用 CONFIG.md
配置后的入口,不硬编码 work/ 或 .scratch/(配置路径可显式传入,
默认值来自《项目目录模板》的默认布局)。

边界:
- 本模块只做读取与核验,不提供写入。项目内写入一律经运行保障受控通道
  (mgs-gate 的 mgs_write)完成;本模块的核验结果针对实际落盘内容。
- 首版仅支持 local-markdown 后端;GitHub Issues 后端未实现,遇到时明确
  报不支持,不静默降级。

用法:
  mgs_records.py config --project <项目根> [--config <CONFIG相对路径>]
  mgs_records.py list  --project <项目根> [--config <CONFIG相对路径>]
  mgs_records.py show  --project <项目根> --task <任务身份> [--config ...]
  mgs_records.py verify --project <项目根> [--config <CONFIG相对路径>]
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

DEFAULT_CONFIG_REL = "docs/mygamestudio/CONFIG.md"
CANONICAL_LABELS = ("needs-triage", "needs-info", "ready-for-agent",
                    "ready-for-human", "wontfix")
CORE_DOC_KEYS = {
    "goal": ("项目目标",),
    "design": ("游戏需求", "游戏设计", "产品设计"),
    "tech": ("技术设计",),
}
TASK_REQUEST_KEYS = ("当前目标", "完成标准", "执行责任")


class RecordsError(Exception):
    """配置缺失、后端不支持或任务记录无法解析。"""


# ---------- 通用 Markdown 解析 ----------

def _sections(text: str) -> dict[str, list[str]]:
    """按 ## 二级标题切分,返回 {标题: 行列表}。"""

    result: dict[str, list[str]] = {}
    current = ""
    for line in text.splitlines():
        match = re.match(r"^##\s+(.*?)\s*$", line)
        if match:
            current = match.group(1)
            result.setdefault(current, [])
        elif current:
            result[current].append(line)
    return result


def _bullets(lines: list[str]) -> dict[str, str]:
    """解析 `- 键:值` 列表为有序字典。"""

    result: dict[str, str] = {}
    for line in lines:
        match = re.match(r"^-\s+([^:：]+)[:：]\s*(.*)$", line)
        if match:
            result[match.group(1).strip()] = match.group(2).strip()
    return result


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


def _field(text: str, key: str) -> str:
    """从任务头部行提取字段值(以空白或中英文句号/分号为界)。"""

    match = re.search(rf"{key}\s*[:：]\s*([^\s。;；]+)", text)
    return match.group(1) if match else ""


# ---------- 逻辑操作(公开接缝) ----------

def load_config(project_root: Path | str, config_rel: str = DEFAULT_CONFIG_REL) -> dict:
    """读取协作配置:后端、任务位置、标签映射与文档映射。"""

    root = Path(project_root)
    config_path = root / config_rel
    if not config_path.is_file():
        raise RecordsError(f"缺少协作配置:{config_path}(项目根 {root})")
    try:
        text = config_path.read_text(encoding="utf-8")
    except OSError as exc:
        raise RecordsError(f"协作配置不可读:{config_path}:{exc}") from exc
    sections = _sections(text)
    source = _bullets(sections.get("任务来源", []))
    backend = source.get("后端", "").strip().lower()
    task_root = _strip_annotation(source.get("当前位置", ""))
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
        "labels": labels,
        "docmap": docmap,
        "external": source.get("外部连接引用及已确认操作范围", ""),
    }


def _local_config(project_root: Path | str, config_rel: str) -> dict:
    config = load_config(project_root, config_rel)
    if config["backend"] != "local-markdown":
        raise RecordsError(
            f"后端 {config['backend']} 不受本地接口支持(首版仅 local-markdown;"
            "GitHub Issues 后端未实现)")
    return config


def _task_root(project_root: Path, config: dict) -> Path:
    return project_root / config["task_root"]


def _parse_task_file(project_root: Path, task_dir: Path) -> dict | None:
    task_path = task_dir / "task.md"
    if not task_path.is_file():
        return None
    text = task_path.read_text(encoding="utf-8")
    header_lines: list[str] = []
    title = ""
    for line in text.splitlines():
        if line.startswith("## "):
            break
        if line.startswith("# ") and not title:
            title = line.lstrip("# ").strip()
        header_lines.append(line)
    header = "\n".join(header_lines)
    sections = _sections(text)
    request = _bullets(sections.get("工作请求", []))
    results_dir = task_dir / "results"
    results = []
    if results_dir.is_dir():
        results = sorted(
            f"results/{path.name}"
            for path in results_dir.iterdir() if path.is_file())
    return {
        "identity": _field(header, "任务身份"),
        "title": title,
        "triage": _field(header, "当前分流"),
        "progress": _field(header, "进度"),
        "directory": task_dir.name,
        "request": request,
        "sections": {name: bool(lines and any(l.strip() for l in lines))
                     for name, lines in sections.items()},
        "results": results,
        "result_index_text": "\n".join(sections.get("结果索引", [])),
        "path": str(task_path.relative_to(project_root)),
    }


def list_tasks(project_root: Path | str, config_rel: str = DEFAULT_CONFIG_REL) -> list[dict]:
    """列出任务身份、标题、分流与进度(经 CONFIG 解析任务根,不硬编码)。"""

    root = Path(project_root)
    config = _local_config(root, config_rel)
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


def read_task(project_root: Path | str, task_id: str,
              config_rel: str = DEFAULT_CONFIG_REL) -> dict:
    """读取单个任务:头部字段、请求、小节与结果清单。"""

    root = Path(project_root)
    config = _local_config(root, config_rel)
    task_dir = _task_root(root, config) / task_id
    parsed = _parse_task_file(root, task_dir) if task_dir.is_dir() else None
    if parsed is None:
        raise RecordsError(f"任务不存在或缺少 task.md:{task_dir}")
    return parsed


def _check(name: str, ok: bool, detail: str) -> dict:
    return {"name": name, "ok": bool(ok), "detail": detail}


def _core_rows(docmap: list[dict]) -> dict[str, list[dict]]:
    """把文档映射行归到三类核心内容。"""

    grouped: dict[str, list[dict]] = {"goal": [], "design": [], "tech": []}
    for row in docmap:
        for key, keywords in CORE_DOC_KEYS.items():
            if any(word in row["content"] for word in keywords):
                grouped[key].append(row)
    return grouped


def verify_project(project_root: Path | str,
                   config_rel: str = DEFAULT_CONFIG_REL) -> dict:
    """回读核验:后端、五标签完整且不冲突、核心文档唯一权威位置、任务结构。"""

    root = Path(project_root)
    checks: list[dict] = []
    try:
        config = load_config(root, config_rel)
    except RecordsError as exc:
        return {"ok": False, "checks": [_check("config-present", False, str(exc))]}
    checks.append(_check("config-present", True, str(root / config_rel)))
    is_local = config["backend"] == "local-markdown"
    checks.append(_check("backend-local-markdown", is_local,
                         f"backend={config['backend']}"))
    task_root = _task_root(root, config)
    checks.append(_check("task-root-exists", task_root.is_dir(),
                         str(task_root)))

    labels = config["labels"]
    missing = [name for name in CANONICAL_LABELS if name not in labels]
    checks.append(_check("labels-complete", not missing,
                         f"缺失语义:{missing}" if missing else "五类语义齐全"))
    project_labels = [labels.get(name, "") for name in CANONICAL_LABELS]
    conflicts = sorted({label for label in project_labels
                        if project_labels.count(label) > 1})
    checks.append(_check("labels-no-conflict", not conflicts,
                         f"多语义映射到同一标签:{conflicts}" if conflicts else "映射无冲突"))

    grouped = _core_rows(config["docmap"])
    core_missing = [key for key, rows in grouped.items() if not rows]
    checks.append(_check("docmap-core-rows", not core_missing,
                         f"缺少核心文档行:{core_missing}" if core_missing
                         else "目标/设计/技术三类齐全"))
    duplicate_types = [key for key, rows in grouped.items() if len(rows) > 1]
    core_paths = [row["path"] for rows in grouped.values() for row in rows]
    duplicate_paths = sorted({p for p in core_paths if core_paths.count(p) > 1})
    unique_ok = not duplicate_types and not duplicate_paths
    checks.append(_check("docmap-unique-authority", unique_ok,
                         f"重复类型:{duplicate_types} 重复位置:{duplicate_paths}"
                         if not unique_ok else "每类核心内容唯一当前维护位置"))
    missing_paths = [row["path"] for row in
                     (grouped["goal"] + grouped["design"] + grouped["tech"])
                     if not (root / row["path"]).is_file()]
    checks.append(_check("docmap-paths-exist", not missing_paths,
                         f"权威位置不存在:{missing_paths}" if missing_paths
                         else "核心文档实际存在"))

    tasks = list_tasks(root, config_rel) if is_local else []
    task_problems: list[str] = []
    for task in tasks:
        if task["identity"] != task["directory"]:
            task_problems.append(f"{task['directory']}:身份 {task['identity']!r} 与目录不一致")
        if task["triage"] not in CANONICAL_LABELS:
            task_problems.append(f"{task['directory']}:分流 {task['triage']!r} 不在五类之内")
        if not task["progress"]:
            task_problems.append(f"{task['directory']}:缺少进度")
        for key in TASK_REQUEST_KEYS:
            if not task["request"].get(key):
                task_problems.append(f"{task['directory']}:工作请求缺少 {key}")
    checks.append(_check("tasks-valid", not task_problems,
                         ";".join(task_problems) if task_problems
                         else f"{len(tasks)} 个任务结构有效"))

    result_problems: list[str] = []
    for task in tasks:
        task_dir = task_root / task["directory"]
        for rel in task["results"]:
            result_path = task_dir / rel
            text = result_path.read_text(encoding="utf-8")
            if task["identity"] not in text:
                result_problems.append(f"{task['directory']}/{rel}:未引用所属任务身份")
        if task["results"]:
            index_text = task["result_index_text"].strip()
            referenced = any(name.split("/")[-1] in index_text or "results" in index_text
                             for name in task["results"])
            if not referenced or "(暂无)" in index_text:
                result_problems.append(
                    f"{task['directory']}:结果文件存在但结果索引未引用")
    checks.append(_check("results-consistent", not result_problems,
                         ";".join(result_problems) if result_problems
                         else "结果文件与结果索引互相一致"))
    return {"ok": all(item["ok"] for item in checks), "checks": checks}


# ---------- CLI ----------

def _cli() -> int:
    common = argparse.ArgumentParser(add_help=False)
    common.add_argument("--project", required=True, help="目标项目根目录")
    common.add_argument("--config", default=DEFAULT_CONFIG_REL,
                        help=f"CONFIG 相对路径(默认 {DEFAULT_CONFIG_REL})")
    parser = argparse.ArgumentParser(
        description="本地 Markdown 任务后端统一回读接口")
    sub = parser.add_subparsers(dest="cmd", required=True)
    sub.add_parser("config", parents=[common], help="读取协作配置")
    sub.add_parser("list", parents=[common], help="列出任务")
    p_show = sub.add_parser("show", parents=[common], help="读取单个任务")
    p_show.add_argument("--task", required=True, help="任务身份")
    sub.add_parser("verify", parents=[common], help="回读核验")
    args = parser.parse_args()
    root = Path(args.project)
    try:
        if args.cmd == "config":
            payload: object = load_config(root, args.config)
        elif args.cmd == "list":
            payload = [{"identity": t["identity"], "title": t["title"],
                        "triage": t["triage"], "progress": t["progress"]}
                       for t in list_tasks(root, args.config)]
        elif args.cmd == "show":
            payload = read_task(root, args.task, args.config)
        else:
            payload = verify_project(root, args.config)
    except RecordsError as exc:
        print(json.dumps({"error": str(exc)}, ensure_ascii=False))
        return 2
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    if args.cmd == "verify" and not payload["ok"]:
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(_cli())

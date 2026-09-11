#!/usr/bin/env python3
"""MyGameStudio 任务记录共同语义(票 02)。

同一份任务正文(本地 work/task.md 与 GitHub Issue 正文是同一记录格式)在
两个后端必须按同一套规则解析、得到相同的共同字段与核心核验结论。本模块
集中这些共同语义:

- 共同错误身份:``RecordsError`` 的唯一定义(GitHub 的
  ``GithubRecordsError`` 继承它,现有 ``except RecordsError`` 分支继续有效);
- 正文头部/小节/字段分隔/空值/未知内容的解析规则(``parse_task_body``);
- 纯记录核验:标签映射、核心文档映射、任务核心字段与依赖关系。

依赖纪律(第一阶段设计):本模块是中性 module——接受文本,不创建网络或
读取会话,不反向导入查询组织(``mgs_records``)或后端适配器(``mgs_github``);
后端专有字段(本地目录/结果文件/相对路径、GitHub Issue 号/标签覆盖/分流
冲突/关闭原因)由对应 adapter 在本模块结果之上补齐,不以统一为由删减。

从脚本或模块导入时,``mgs_records`` 重新导出本模块的公开名字,保持现有
调用方定位;这不是空转发,而是同一实现的唯一定义位置。
"""

from __future__ import annotations

import re

CANONICAL_LABELS = ("needs-triage", "needs-info", "ready-for-agent",
                    "ready-for-human", "wontfix")
# 核心文档三类语义的匹配关键词(goal/design/tech)
CORE_DOC_KEYS = {
    "goal": ("项目目标",),
    "design": ("游戏需求", "游戏设计", "产品设计"),
    "tech": ("技术设计",),
}
# 核验任务记录必需的「工作请求」字段;旧记录缺项不在此判失败,而由
# startable_tasks 逐任务给出可开工原因。
TASK_REQUEST_KEYS = ("当前目标", "完成标准", "执行责任")
# 拆单轮任务记录的完整字段;拆单与可开工判断共用。
PLAN_REQUEST_KEYS = ("当前目标", "输入与基线", "本次交付", "允许修改范围",
                     "所需能力", "完成标准", "执行责任", "验收方式", "依赖")
# 身份 token 前面不能是数字或连字符:避免把「2026-09-08」这类日期从中间
# 截断成假身份(026-09-08/09-08),制造假的未解析依赖。
IDENTITY_RE = re.compile(r"(?<![\d-])\d{1,3}-[A-Za-z0-9]+(?:-[A-Za-z0-9]+)*")


class RecordsError(Exception):
    """配置缺失、后端不支持或任务记录无法解析。

    两后端的唯一记录错误身份:GitHub 记录错误继承本类,调用方(脚本与
    Python 导入)使用同一 ``except RecordsError`` 分支即可捕获。
    """


# ---------- 通用 Markdown 共同规则 ----------

def _sections(text: str) -> dict[str, list[str]]:
    """按 ## 二级标题切分,返回 {标题: 行列表}(未知小节保留)。"""

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
    """解析 `- 键:值` 列表为有序字典(空值字段保留键)。"""

    result: dict[str, str] = {}
    for line in lines:
        match = re.match(r"^-\s+([^:：]+)[:：]\s*(.*)$", line)
        if match:
            result[match.group(1).strip()] = match.group(2).strip()
    return result


def _field(text: str, key: str) -> str:
    """从任务头部行提取字段值(以空白或中英文句号/分号为界)。"""

    match = re.search(rf"{key}\s*[:：]\s*([^\s。;；]+)", text)
    return match.group(1) if match else ""


def _header_lines(text: str) -> tuple[list[str], str]:
    """头部 = 首个二级标题之前的文本;同时取首个一级标题为标题。"""

    lines: list[str] = []
    title = ""
    for line in (text or "").splitlines():
        if line.startswith("## "):
            break
        if line.startswith("# ") and not title:
            title = line.lstrip("# ").strip()
        lines.append(line)
    return lines, title


def parse_task_body(text: str) -> dict:
    """共同正文规则:正文 → 共同任务字段(身份/标题/分流/进度/请求/小节)。

    空字段保留为空值,未知小节保留在 sections,字段分隔接受中英文冒号并
    以空白/句号/分号截断;畸形任务(缺身份、空字段、不一致记录)照常返回
    可见字段,不在读取层提前过滤,以便核验仍能发现它们。
    """

    header_lines, title = _header_lines(text)
    header = "\n".join(header_lines)
    sections = _sections(text or "")
    return {
        "identity": _field(header, "任务身份"),
        "title": title,
        "triage": _field(header, "当前分流"),
        "progress": _field(header, "进度"),
        "request": _bullets(sections.get("工作请求", [])),
        "sections": {name: bool(lines and any(l.strip() for l in lines))
                     for name, lines in sections.items()},
        "result_index_text": "\n".join(sections.get("结果索引", [])),
    }


# ---------- 依赖关系(纯记录) ----------

def _parse_dep_ids(value: str) -> list[str]:
    """从「依赖」字段提取任务身份 token(逗号/顿号/分号分隔,含说明文字)。

    身份形态沿用本地后端约定:NN-<slug>(如 04-gull-swoop);其余文字忽略。
    """

    if not value:
        return []
    return IDENTITY_RE.findall(value)


def _find_cycles(edges: dict[str, list[str]]) -> list[list[str]]:
    """DFS 检测有向图循环,返回循环路径(每个循环报一次)。"""

    WHITE, GRAY, BLACK = 0, 1, 2
    color = {node: WHITE for node in edges}
    cycles: list[list[str]] = []

    def visit(node: str, path: list[str]) -> None:
        color[node] = GRAY
        for dep in edges.get(node, []):
            if dep not in color:
                continue  # 未解析依赖由 unresolved 报告
            if color[dep] == GRAY:
                index = path.index(dep)
                cycles.append(path[index:] + [dep])
            elif color[dep] == WHITE:
                visit(dep, path + [dep])
        color[node] = BLACK

    for node in sorted(edges):
        if color[node] == WHITE:
            visit(node, [node])
    return cycles


def dependency_problems(tasks: list[dict]) -> list[str]:
    """依赖关系可解析且无循环(入参为规范化任务列表,双后端同语义)。"""

    edges = {task["identity"]: _parse_dep_ids(
                 task["request"].get("依赖", "")) for task in tasks}
    seen = {task["identity"] for task in tasks}
    problems = [f"{identity} 依赖不存在任务 {dep}"
                for identity, deps in edges.items() for dep in deps
                if dep not in seen]
    problems += ["循环依赖:" + "->".join(cycle)
                 for cycle in _find_cycles(edges)]
    return problems


# ---------- 核心核验(纯记录,双后端单一实现) ----------

def check_item(name: str, ok: bool, detail: str) -> dict:
    return {"name": name, "ok": bool(ok), "detail": detail}


def _core_rows(docmap: list[dict]) -> dict[str, list[dict]]:
    """把文档映射行归到三类核心内容。"""

    grouped: dict[str, list[dict]] = {"goal": [], "design": [], "tech": []}
    for row in docmap:
        for key, keywords in CORE_DOC_KEYS.items():
            if any(word in row["content"] for word in keywords):
                grouped[key].append(row)
    return grouped


def label_mapping_checks(labels: dict) -> list[dict]:
    """五类标签映射:语义齐全且不冲突。"""

    missing = [name for name in CANONICAL_LABELS if name not in labels]
    project_labels = [labels.get(name, "") for name in CANONICAL_LABELS]
    conflicts = sorted({label for label in project_labels
                        if project_labels.count(label) > 1})
    return [
        check_item("labels-complete", not missing,
               f"缺失语义:{missing}" if missing else "五类语义齐全"),
        check_item("labels-no-conflict", not conflicts,
               f"多语义映射到同一标签:{conflicts}" if conflicts else "映射无冲突"),
    ]


def docmap_checks(root, docmap: list[dict]) -> list[dict]:
    """核心文档映射:三类齐全、每类唯一当前维护位置且实际存在。"""

    grouped = _core_rows(docmap)
    core_missing = [key for key, rows in grouped.items() if not rows]
    duplicate_types = [key for key, rows in grouped.items() if len(rows) > 1]
    core_paths = [row["path"] for rows in grouped.values() for row in rows]
    duplicate_paths = sorted({p for p in core_paths if core_paths.count(p) > 1})
    unique_ok = not duplicate_types and not duplicate_paths
    missing_paths = [row["path"] for row in
                     (grouped["goal"] + grouped["design"] + grouped["tech"])
                     if not (root / row["path"]).is_file()]
    return [
        check_item("docmap-core-rows", not core_missing,
               f"缺少核心文档行:{core_missing}" if core_missing
               else "目标/设计/技术三类齐全(核心设计保留本地 Markdown 位置)"),
        check_item("docmap-unique-authority", unique_ok,
               f"重复类型:{duplicate_types} 重复位置:{duplicate_paths}"
               if not unique_ok else "每类核心内容唯一当前维护位置"),
        check_item("docmap-paths-exist", not missing_paths,
               f"权威位置不存在:{missing_paths}" if missing_paths
               else "核心文档实际存在"),
    ]


def task_core_problems(task: dict, where: str) -> list[str]:
    """规范化任务的核心校验:身份形态、五类分流、进度、工作请求必填字段。

    where 是问题条目的定位前缀(本地为任务目录名,远端为 #Issue号)。
    空字段与畸形记录在此报告,不在读取层过滤——畸形任务仍能进入核验。
    """

    problems: list[str] = []
    identity = task["identity"]
    if not identity or not IDENTITY_RE.fullmatch(identity):
        problems.append(f"{where}:正文身份缺失或不合规({identity!r})")
    if task["triage"] not in CANONICAL_LABELS:
        problems.append(f"{where}:分流 {task['triage']!r} 不在五类之内")
    if not task["progress"]:
        problems.append(f"{where}:缺少进度")
    for key in TASK_REQUEST_KEYS:
        if not task["request"].get(key):
            problems.append(f"{where}:工作请求缺少 {key}")
    return problems

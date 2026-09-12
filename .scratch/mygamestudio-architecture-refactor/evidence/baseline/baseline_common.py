#!/usr/bin/env python3
"""票 01 基线探针共享 helper(同目录,低风险去重;不引入抽象框架)。

只收拢各探针中字形相同的重复实现:
- 五个探针一致的 argparse(`--out`)与 JSON 输出尾段;
- `git()` 助手与工作区状态披露(供各探针与总入口 run_baseline.py 共用);
- client_probe.py 与 code_volume.py 的客户端源码归一化;
- records_probe.py 与 entry_probe.py 共用的临时项目夹具。

不承载任何探针特有逻辑;不访问网络、不启动真实模型、不做远端写入。
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
import sys
from pathlib import Path

# baseline_common.py 与各探针同目录:evidence/baseline/<file> -> 仓库根
REPO_ROOT = Path(__file__).resolve().parents[4]

NON_PRODUCT_MARKERS = (
    ".scratch/",
)

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


def git(*args: str) -> str:
    """在仓库根执行只读 git 命令,返回去尾换行的 stdout。"""

    out = subprocess.run(["git", "-C", str(REPO_ROOT), *args],
                         capture_output=True, text=True, check=False)
    return out.stdout.strip()


def worktree_state() -> dict:
    """工作区状态披露(唯一实现在此收拢;各探针与总入口共用)。

    原始 `worktree_clean` 直接来自 `git status --porcelain`。基线产物目录
    (`evidence/baseline/`)与本票无关的主控进度文件在原始口径下是未跟踪项,故
    原始口径通常为 false;排除 NON_PRODUCT_MARKERS 列出的非产品项后的
    `worktree_clean_excluding_baseline` 才等价于「零产品改动」。
    """

    porcelain = [line for line in git("status", "--porcelain").splitlines()
                 if line.strip()]
    remaining = [line for line in porcelain
                 if not any(marker in line for marker in NON_PRODUCT_MARKERS)]
    return {
        "worktree_clean": not porcelain,
        "worktree_clean_excluding_baseline": not remaining,
        "worktree_clean_excluding_scope": (
            "排除 .scratch/ 下的票产物、工单与主控进度记录后的判断"
            "(即本票零产品行为变更口径;与红线 "
            "`git diff --numstat -- plugin tests acceptance dist` 为 0 一致)"),
        "worktree_porcelain": porcelain,
    }


def normalize_source(text: str) -> str:
    """忽略注释/文档串,只规范化编号身份常量,保留全部结构(客户端归一化)。"""

    text = re.sub(r'""".*?"""', "", text, flags=re.S)
    text = re.sub(r"'''.*?'''", "", text, flags=re.S)
    lines = [re.sub(r"#.*$", "", line).rstrip() for line in text.splitlines()]
    text = "\n".join(line for line in lines if line.strip())
    text = re.sub(r"mgs\d+", "MGS", text)
    text = re.sub(r"MyGameStudio \d+", "MyGameStudio N", text)
    return hashlib.sha256(text.encode()).hexdigest()


def parse_out_args(description: str = "") -> argparse.Namespace:
    """五个探针一致的参数解析:`--out <report.json>`(省略则打印 stdout)。"""

    parser = argparse.ArgumentParser(description=description or None)
    parser.add_argument("--out")
    return parser.parse_args()


def emit(report: dict, out: str | None) -> None:
    """五个探针一致的输出尾段:写文件或打印,JSON 缩进 2。"""

    text = json.dumps(report, ensure_ascii=False, indent=2)
    if out:
        Path(out).write_text(text + "\n", encoding="utf-8")
    else:
        print(text)


def make_project(tmp: Path, *, backend: str = "local-markdown") -> Path:
    """建立最小临时项目(CONFIG.md + 三份核心文档);不写仓库。"""

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
    """在临时项目 task_root 下写入一份任务夹具。"""

    task_dir = root / "docs" / "mygamestudio" / "work" / identity
    task_dir.mkdir(parents=True, exist_ok=True)
    (task_dir / "task.md").write_text(
        TASK_TEMPLATE.format(title=title, identity=identity, deps=deps),
        encoding="utf-8")

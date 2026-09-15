#!/usr/bin/env python3
"""Game-Init 项目接入(issue #51 本地 Markdown;issue #52 GitHub Issues)。

分析已有游戏并补齐必要指针与协作配置;每项目只选一种现行 tracker。
通用标签与领域文档布局仍交给 setup-matt-pocock-skills。
分析阶段只读;确认后按清单写入,不覆盖有效旧资料,不要求 mgs-gate。
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from mgs_record_model import RecordsError, today  # noqa: E402
from mgs_record_source import (  # noqa: E402
    DEFAULT_CONFIG_REL, DEFAULT_TASK_ROOT, load_config, parse_repo_location)

PLUGIN_ROOT = Path(__file__).resolve().parent.parent
TEMPLATE_ROOT = PLUGIN_ROOT / "templates"
STAGE_REQUIREMENTS = "internal/game/stage-requirements.md"
CONFIG_REL = DEFAULT_CONFIG_REL
INDEX_REL = "docs/mygamestudio/INDEX.md"
PROJECT_REL = "docs/mygamestudio/PROJECT.md"
ONBOARD_REL = "docs/mygamestudio/records/onboarding.md"
CLASSES = ("实际行为", "已采纳", "历史内容", "缺口", "冲突", "未验证")


def _rel(root: Path, path: Path) -> str:
    try:
        return str(path.relative_to(root))
    except ValueError:
        return str(path)


def _existing_files(root: Path) -> list[Path]:
    skip = {".git", "__pycache__", "node_modules"}
    files: list[Path] = []
    for path in root.rglob("*"):
        if not path.is_file():
            continue
        if any(part in skip for part in path.parts):
            continue
        files.append(path)
    return files


def analyze_project(project_root: Path | str) -> dict:
    """只读分析已有设计、工程和资料;不写入,也不开始制作。"""

    root = Path(project_root)
    if not root.is_dir():
        raise RecordsError(f"目标项目不存在:{root}")
    engineering: list[str] = []
    adopted: list[str] = []
    history: list[str] = []
    gaps: list[str] = []
    conflicts: list[str] = []
    unverified: list[str] = []
    actual: list[str] = []
    for path in _existing_files(root):
        rel = _rel(root, path)
        text = path.read_text(encoding="utf-8", errors="replace")
        lowered = rel.lower()
        if lowered.startswith("src/") or lowered.startswith("assets/") \
                or path.suffix in {".js", ".ts", ".html", ".css"} \
                or path.name == "package.json":
            engineering.append(rel)
            actual.append(rel)
        elif "DESIGN" in path.name.upper() or path.name == "GAME_DESIGN.md":
            adopted.append(rel)
            if "被替代" in text or "历史决定" in text:
                history.append(rel)
        elif "TECH" in path.name.upper() or path.name == "TECH_DESIGN.md":
            adopted.append(rel)
        elif lowered.startswith("docs/") or path.name in {"README.md", "HANDBOOK.md"}:
            adopted.append(rel)
        elif "/tasks/" in f"/{lowered}" or lowered.startswith("tasks/"):
            history.append(rel)
            unverified.append(rel)
        if path.name == "CONFIG.md" and "github-issues" in text \
                and "local-markdown" in text:
            conflicts.append(rel)
    if not (root / CONFIG_REL).is_file():
        gaps.append("缺少协作配置与现行 tracker 选择")
    if not (root / INDEX_REL).is_file():
        gaps.append("缺少资料入口指针")
    if not (root / DEFAULT_TASK_ROOT).is_dir():
        gaps.append("缺少现行任务位置")
    return {
        "wrote": False,
        "project_root": str(root),
        "classes": list(CLASSES),
        "实际行为": actual,
        "已采纳": adopted,
        "历史内容": history,
        "缺口": gaps,
        "冲突": conflicts,
        "未验证": unverified,
        "engineering": engineering,
        "design": adopted,
    }


def _project_name(root: Path) -> str:
    readme = root / "README.md"
    if readme.is_file():
        for line in readme.read_text(encoding="utf-8").splitlines():
            if line.startswith("# "):
                return line[2:].strip() or root.name
    return root.name


def plan_local_onboarding(project_root: Path | str) -> dict:
    """形成本地 Markdown 接入清单;不写入。"""

    root = Path(project_root)
    analysis = analyze_project(root)
    items: list[dict] = []

    def add(path: str, action: str, reason: str) -> None:
        items.append({"path": path, "action": action, "reason": reason})

    if not (root / CONFIG_REL).is_file():
        add(CONFIG_REL, "新增", "选择本地 Markdown 为唯一现行任务来源")
    else:
        add(CONFIG_REL, "复用", "已有协作配置,不覆盖")
    if not (root / INDEX_REL).is_file():
        add(INDEX_REL, "新增", "建立现行规格/任务/阶段资料指针")
    else:
        add(INDEX_REL, "复用", "已有资料入口,不覆盖有效旧资料")
    if not (root / PROJECT_REL).is_file():
        add(PROJECT_REL, "新增", "建立当前项目约定入口")
    else:
        add(PROJECT_REL, "复用", "已有项目约定")
    if not (root / DEFAULT_TASK_ROOT).is_dir():
        add(DEFAULT_TASK_ROOT + "/", "新增", "现行任务唯一位置")
    else:
        add(DEFAULT_TASK_ROOT + "/", "复用", "已有任务根")
    if not (root / ONBOARD_REL).is_file():
        add(ONBOARD_REL, "新增", "保存本次接入记录")
    reused = [rel for rel in analysis["已采纳"]
              if rel not in {CONFIG_REL, INDEX_REL, PROJECT_REL}]
    for rel in reused:
        add(rel, "复用", "沿用已有有效资料,不覆盖")
    return {
        "backend": "local-markdown",
        "tracker": "local-markdown",
        "project_name": _project_name(root),
        "analysis": analysis,
        "items": items,
        "wrote": False,
    }


def _current_backend(root: Path) -> str | None:
    if not (root / CONFIG_REL).is_file():
        return None
    try:
        return str(load_config(root).get("backend") or "") or None
    except RecordsError:
        return None


def _tracker_mismatch(root: Path, wanted: str) -> str | None:
    current = _current_backend(root)
    if current and current != wanted:
        return (
            f"已有 {current} tracker,改用 {wanted} 须走迁移与切换,"
            "不能把接入报成成功")
    return None


def plan_github_onboarding(project_root: Path | str, *, repo: str,
                           authorization: str = "") -> dict:
    """形成 GitHub Issues 接入清单;不写入,也不把本地 Markdown 升为现行账本。"""

    root = Path(project_root)
    mismatch = _tracker_mismatch(root, "github-issues")
    if mismatch is not None:
        return {
            "ok": False,
            "wrote": False,
            "backend": _current_backend(root) or "",
            "reason": mismatch,
            "items": [],
        }
    parsed = parse_repo_location(repo)
    repo_value = f"{parsed['host']}/{parsed['owner']}/{parsed['repo']}"
    analysis = analyze_project(root)
    items: list[dict] = []

    def add(path: str, action: str, reason: str) -> None:
        items.append({"path": path, "action": action, "reason": reason})

    if not (root / CONFIG_REL).is_file():
        add(CONFIG_REL, "新增", "选择 GitHub Issues 为唯一现行任务来源")
    else:
        add(CONFIG_REL, "复用", "已有协作配置,不覆盖")
    if not (root / INDEX_REL).is_file():
        add(INDEX_REL, "新增", "建立现行规格/任务/阶段资料指针")
    else:
        add(INDEX_REL, "复用", "已有资料入口,不覆盖有效旧资料")
    if not (root / PROJECT_REL).is_file():
        add(PROJECT_REL, "新增", "建立当前项目约定入口")
    else:
        add(PROJECT_REL, "复用", "已有项目约定")
    if not (root / ONBOARD_REL).is_file():
        add(ONBOARD_REL, "新增", "保存本次接入记录")
    reused = [rel for rel in analysis["已采纳"]
              if rel not in {CONFIG_REL, INDEX_REL, PROJECT_REL}]
    for rel in reused:
        add(rel, "复用", "沿用已有有效资料,不覆盖")
    return {
        "backend": "github-issues",
        "tracker": "github-issues",
        "repo": repo_value,
        "authorization": authorization,
        "project_name": _project_name(root),
        "analysis": analysis,
        "items": items,
        "wrote": False,
    }


def _join(items) -> str:
    return "、".join(items) if items else "无"


def _fill(template: str, mapping: dict[str, str]) -> str:
    text = template
    for key, value in mapping.items():
        text = text.replace("{{" + key + "}}", value)
    return text


def _unique_docmap(content: str) -> str:
    """现行规格、任务与结果各有唯一位置(D5)。"""

    table = """## 文档映射

| 内容 | 当前权威位置 | 维护角色 |
| --- | --- | --- |
| 项目目标与范围 | docs/mygamestudio/PROJECT.md | 制作统筹 |
| 游戏需求与设计 | docs/mygamestudio/GAME_DESIGN.md | 方案设计 |
| 技术设计 | docs/mygamestudio/TECH_DESIGN.md | 制作实现 |
| 术语、ADR 与历史 | docs/mygamestudio/records/ | 对应专业角色 |
| 成果与证据 | docs/mygamestudio/evidence/ | 对应执行者 |
"""
    return re.sub(
        r"## 文档映射\n.*?(?=\n## |\Z)", table.rstrip() + "\n",
        content, count=1, flags=re.S)


def _write_new(path: Path, content: str) -> str:
    if path.exists():
        return "跳过(已有,不覆盖)"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    return "已写入"


def apply_local_onboarding(project_root: Path | str, plan: dict | None = None,
                           *, confirmed: bool = False) -> dict:
    """按确认清单写入接入资料;不覆盖有效旧文件,不要求 gate。"""

    root = Path(project_root)
    if not confirmed:
        raise RecordsError("未确认接入清单,不写入")
    plan = plan or plan_local_onboarding(root)
    if plan.get("backend") != "local-markdown":
        raise RecordsError("本入口只接入本地 Markdown tracker,GitHub 接入见后续票")
    name = plan.get("project_name") or _project_name(root)
    results: list[dict] = []
    mapping = {
        "项目名": name,
        "版本": "v1",
        "本次初始化确认或已有约定": f"{today()} 本地 Markdown 接入",
        "开发者决定引用": "本次接入确认",
        "local-markdown 或 github-issues": "local-markdown",
        "本地任务根目录，或 GitHub host/owner/repository": DEFAULT_TASK_ROOT,
        "采用的后端合同或已有 tracker 配置": "本地 Markdown 工作记录合同",
        "仅引用，不填写凭据；GitHub Issues 写入授权按 host/owner/repository:issues-write(说明) 记录，未记录即未授权": "无",
        "位置": PROJECT_REL,
        "已有配置引用或位置": "docs/mygamestudio/records/",
        "项目约定位置": PROJECT_REL,
        "协作配置位置": CONFIG_REL,
        "当前游戏设计位置": "docs/mygamestudio/GAME_DESIGN.md(尚未建立则见 INDEX 缺口)",
        "当前技术设计位置": "docs/mygamestudio/TECH_DESIGN.md(尚未建立则见 INDEX 缺口)",
        "当前任务入口": DEFAULT_TASK_ROOT,
        "术语位置": "按现行规格用语",
        "决定与历史入口": "docs/mygamestudio/records/",
        "证据入口": "docs/mygamestudio/evidence/",
        "希望交付的游戏体验、面向谁以及当前为什么做它；专业规则引用游戏设计。": "见 README 与接入分析;现行规则以 INDEX 指向的规格为准。",
        "本轮边界": "当前最小可玩闭环",
        "明确排除或以后再做的内容": "GitHub tracker、发版与真实项目迁移",
        "已有约定，未确定则如实记录": "待定",
        "可试玩体验或具体专业成果": "接入后可记录并查询任务",
        "需要看到的结果与人的参与点": "任务记录可回读",
        "引用": DEFAULT_TASK_ROOT,
        "粗粒度目标": "按现行规格推进",
        "已做、待做、待验收、阻塞及对应事实引用；不要从“设计已采纳”推导“已经实现”。": "接入完成;实施进展见任务记录。",
        "本版替代的版本、变化影响与决定记录引用。": "无",
        "实际位置或工程配置引用": "src/",
        "验证记录引用": "文件读写",
        "事实": "无",
    }
    actions = {item["path"]: item["action"] for item in plan.get("items", [])}
    if actions.get(CONFIG_REL) == "新增":
        template = (TEMPLATE_ROOT / "project" / "CONFIG.md").read_text(encoding="utf-8")
        content = _fill(template, mapping)
        content = _unique_docmap(content)
        results.append({"path": CONFIG_REL, "result": _write_new(root / CONFIG_REL, content)})
    else:
        results.append({"path": CONFIG_REL, "result": "复用"})
    if actions.get(INDEX_REL) == "新增":
        template = (TEMPLATE_ROOT / "project" / "INDEX.md").read_text(encoding="utf-8")
        content = _fill(template, mapping)
        if "stage-requirements.md" not in content:
            content += (
                "\n| 当前阶段游戏专业要求 | 安装包 "
                f"{STAGE_REQUIREMENTS}(读取不是开始制作) |\n")
        reused_design = [
            item["path"] for item in plan.get("items", [])
            if item.get("action") == "复用"
            and item["path"] not in {CONFIG_REL, INDEX_REL, PROJECT_REL}
            and not str(item["path"]).endswith("/")
        ]
        if reused_design:
            content += "\n## 复用的已有资料\n\n"
            for rel in reused_design:
                content += f"- {rel}\n"
        results.append({"path": INDEX_REL, "result": _write_new(root / INDEX_REL, content)})
    else:
        results.append({"path": INDEX_REL, "result": "复用"})
    if actions.get(PROJECT_REL) == "新增":
        template = (TEMPLATE_ROOT / "project" / "PROJECT.md").read_text(encoding="utf-8")
        content = _fill(template, mapping)
        results.append({"path": PROJECT_REL, "result": _write_new(root / PROJECT_REL, content)})
    else:
        results.append({"path": PROJECT_REL, "result": "复用"})
    task_root = root / DEFAULT_TASK_ROOT
    if not task_root.exists():
        task_root.mkdir(parents=True, exist_ok=True)
        results.append({"path": DEFAULT_TASK_ROOT + "/", "result": "已写入"})
    else:
        results.append({"path": DEFAULT_TASK_ROOT + "/", "result": "复用"})
    (root / "docs/mygamestudio/records").mkdir(parents=True, exist_ok=True)
    if actions.get(ONBOARD_REL) == "新增":
        analysis = plan.get("analysis") or {}
        mode = "接手" if analysis_has_existing(plan) else "新项目"
        lines = [
            f"# {name}：接入记录", "",
            f"模式：{mode}。目标项目：{root.name}。检查日期：{today()}。", "",
            "## 现状与缺口", "",
            f"- 实际行为：{_join(analysis.get('实际行为'))}",
            f"- 已采纳：{_join(analysis.get('已采纳'))}",
            f"- 历史内容：{_join(analysis.get('历史内容'))}",
            f"- 缺口：{_join(analysis.get('缺口'))}",
            f"- 冲突：{_join(analysis.get('冲突'))}",
            f"- 未验证：{_join(analysis.get('未验证'))}",
            "", "## 协作配置选择", "",
            "- 任务后端：local-markdown（本项目唯一现行 tracker，不双向同步）",
            f"- 任务位置：{DEFAULT_TASK_ROOT}",
            "- 通用分流标签与领域文档布局：交给 setup-matt-pocock-skills",
            "", "## 具体应用清单", "",
            "| 目标位置 | 复用/新增/修改动作与内容 | 原因与依据 | 维护角色 | 确认及应用结果 |",
            "| --- | --- | --- | --- | --- |",
        ]
        for item in plan.get("items", []):
            lines.append(
                f"| {item['path']} | {item['action']} | {item['reason']} |"
                " 制作统筹 | 已确认 |")
        lines += [
            "", "## 就绪与恢复", "",
            f"- 文档与任务入口：{INDEX_REL} 与 {CONFIG_REL}",
            "- 运行保障：普通本地工作不要求 gate 配置",
            "- 已完成与剩余项：清单已应用；规格文件未建立的记入状态查询缺项",
            "- 用户后续修改及影响：恢复时重读当前文件，不覆盖后来变更",
            "- 重复运行：无缺口则不改已有内容",
            "",
        ]
        onboard = "\n".join(lines)
        results.append({"path": ONBOARD_REL, "result": _write_new(root / ONBOARD_REL, onboard)})
    overwritten = [row for row in results if row["result"].startswith("覆盖")]
    return {
        "ok": not overwritten,
        "backend": "local-markdown",
        "results": results,
        "overwritten": overwritten,
        "gate_required": False,
    }


def _github_mapping(root: Path, plan: dict) -> dict[str, str]:
    name = plan.get("project_name") or _project_name(root)
    repo = plan.get("repo") or ""
    authorization = plan.get("authorization") or "无"
    return {
        "项目名": name,
        "版本": "v1",
        "本次初始化确认或已有约定": f"{today()} GitHub Issues 接入",
        "开发者决定引用": "本次接入确认",
        "local-markdown 或 github-issues": "github-issues",
        "本地任务根目录，或 GitHub host/owner/repository": repo,
        "采用的后端合同或已有 tracker 配置": "GitHub Issues 工作记录合同",
        "仅引用，不填写凭据；GitHub Issues 写入授权按 host/owner/repository:issues-write(说明) 记录，未记录即未授权": authorization,
        "位置": PROJECT_REL,
        "已有配置引用或位置": "docs/mygamestudio/records/",
        "项目约定位置": PROJECT_REL,
        "协作配置位置": CONFIG_REL,
        "当前游戏设计位置": "docs/mygamestudio/GAME_DESIGN.md(尚未建立则见 INDEX 缺口)",
        "当前技术设计位置": "docs/mygamestudio/TECH_DESIGN.md(尚未建立则见 INDEX 缺口)",
        "当前任务入口": f"{repo}(GitHub Issues 为唯一现行任务来源;本地仅保存明确标识的草稿或缓存)",
        "术语位置": "按现行规格用语",
        "决定与历史入口": "docs/mygamestudio/records/",
        "证据入口": "docs/mygamestudio/evidence/",
        "希望交付的游戏体验、面向谁以及当前为什么做它；专业规则引用游戏设计。": "见 README 与接入分析;现行规则以 INDEX 指向的规格为准。",
        "本轮边界": "当前最小可玩闭环",
        "明确排除或以后再做的内容": "本地 Markdown tracker、发版与真实项目迁移",
        "已有约定，未确定则如实记录": "待定",
        "可试玩体验或具体专业成果": "接入后可在 GitHub 记录并查询任务",
        "需要看到的结果与人的参与点": "任务记录可回读",
        "引用": repo,
        "粗粒度目标": "按现行规格推进",
        "已做、待做、待验收、阻塞及对应事实引用；不要从“设计已采纳”推导“已经实现”。": "接入完成;实施进展见 GitHub 任务记录。",
        "本版替代的版本、变化影响与决定记录引用。": "无",
        "实际位置或工程配置引用": "src/",
        "验证记录引用": "文件读写",
        "事实": "无",
    }


def apply_github_onboarding(project_root: Path | str, plan: dict | None = None,
                            *, confirmed: bool = False, repo: str | None = None,
                            authorization: str = "") -> dict:
    """按确认清单写入 GitHub 接入资料;不覆盖有效旧文件,不把本地 task.md 当作现行账本。"""

    root = Path(project_root)
    if not confirmed:
        raise RecordsError("未确认接入清单,不写入")
    mismatch = _tracker_mismatch(root, "github-issues")
    if mismatch is not None:
        return {
            "ok": False,
            "wrote": False,
            "backend": _current_backend(root) or "",
            "reason": mismatch,
            "items": [],
        }
    plan = plan or plan_github_onboarding(
        root, repo=repo or "", authorization=authorization)
    if plan.get("ok") is False:
        return {
            "ok": False,
            "wrote": False,
            "backend": plan.get("backend") or _current_backend(root) or "",
            "reason": plan.get("reason") or "接入前置条件未满足",
            "items": [],
        }
    if plan.get("backend") != "github-issues":
        raise RecordsError("本入口只接入 GitHub Issues tracker")
    if not plan.get("repo"):
        raise RecordsError("GitHub 接入必须明确 host/owner/repository")
    name = plan.get("project_name") or _project_name(root)
    results: list[dict] = []
    mapping = _github_mapping(root, plan)
    actions = {item["path"]: item["action"] for item in plan.get("items", [])}
    if actions.get(CONFIG_REL) == "新增":
        template = (TEMPLATE_ROOT / "project" / "CONFIG.md").read_text(encoding="utf-8")
        content = _fill(template, mapping)
        content = _unique_docmap(content)
        results.append({"path": CONFIG_REL, "result": _write_new(root / CONFIG_REL, content)})
    else:
        results.append({"path": CONFIG_REL, "result": "复用"})
    if actions.get(INDEX_REL) == "新增":
        template = (TEMPLATE_ROOT / "project" / "INDEX.md").read_text(encoding="utf-8")
        content = _fill(template, mapping)
        if "stage-requirements.md" not in content:
            content += (
                "\n| 当前阶段游戏专业要求 | 安装包 "
                f"{STAGE_REQUIREMENTS}(读取不是开始制作) |\n")
        reused_design = [
            item["path"] for item in plan.get("items", [])
            if item.get("action") == "复用"
            and item["path"] not in {CONFIG_REL, INDEX_REL, PROJECT_REL}
            and not str(item["path"]).endswith("/")
        ]
        if reused_design:
            content += "\n## 复用的已有资料\n\n"
            for rel in reused_design:
                content += f"- {rel}\n"
        results.append({"path": INDEX_REL, "result": _write_new(root / INDEX_REL, content)})
    else:
        results.append({"path": INDEX_REL, "result": "复用"})
    if actions.get(PROJECT_REL) == "新增":
        template = (TEMPLATE_ROOT / "project" / "PROJECT.md").read_text(encoding="utf-8")
        content = _fill(template, mapping)
        results.append({"path": PROJECT_REL, "result": _write_new(root / PROJECT_REL, content)})
    else:
        results.append({"path": PROJECT_REL, "result": "复用"})
    (root / "docs/mygamestudio/records").mkdir(parents=True, exist_ok=True)
    if actions.get(ONBOARD_REL) == "新增":
        analysis = plan.get("analysis") or {}
        mode = "接手" if analysis_has_existing(plan) else "新项目"
        lines = [
            f"# {name}：接入记录", "",
            f"模式：{mode}。目标项目：{root.name}。检查日期：{today()}。", "",
            "## 现状与缺口", "",
            f"- 实际行为：{_join(analysis.get('实际行为'))}",
            f"- 已采纳：{_join(analysis.get('已采纳'))}",
            f"- 历史内容：{_join(analysis.get('历史内容'))}",
            f"- 缺口：{_join(analysis.get('缺口'))}",
            f"- 冲突：{_join(analysis.get('冲突'))}",
            f"- 未验证：{_join(analysis.get('未验证'))}",
            "", "## 协作配置选择", "",
            "- 任务后端：github-issues（本项目唯一现行 tracker，不双向同步）",
            f"- 任务位置：{plan['repo']}",
            "- 本地仅保存明确标识的未发布草稿或注明来源的缓存，不是第二套现行状态",
            "- 通用分流标签与领域文档布局：交给 setup-matt-pocock-skills",
            "", "## 具体应用清单", "",
            "| 目标位置 | 复用/新增/修改动作与内容 | 原因与依据 | 维护角色 | 确认及应用结果 |",
            "| --- | --- | --- | --- | --- |",
        ]
        for item in plan.get("items", []):
            lines.append(
                f"| {item['path']} | {item['action']} | {item['reason']} |"
                " 制作统筹 | 已确认 |")
        lines += [
            "", "## 就绪与恢复", "",
            f"- 文档与任务入口：{INDEX_REL} 与 {CONFIG_REL}",
            "- 运行保障：普通工作不要求 gate 配置",
            "- 已完成与剩余项：清单已应用；规格文件未建立的记入状态查询缺项",
            "- 用户后续修改及影响：恢复时重读当前文件与 GitHub 实际状态，不覆盖后来变更",
            "- 重复运行：无缺口则不改已有内容",
            "",
        ]
        onboard = "\n".join(lines)
        results.append({"path": ONBOARD_REL, "result": _write_new(root / ONBOARD_REL, onboard)})
    overwritten = [row for row in results if row["result"].startswith("覆盖")]
    return {
        "ok": not overwritten,
        "backend": "github-issues",
        "repo": plan.get("repo"),
        "results": results,
        "overwritten": overwritten,
        "gate_required": False,
    }


def analysis_has_existing(plan: dict) -> bool:
    analysis = plan.get("analysis") or {}
    return bool(analysis.get("engineering") or analysis.get("已采纳"))

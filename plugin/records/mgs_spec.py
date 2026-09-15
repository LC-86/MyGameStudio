#!/usr/bin/env python3
"""现行游戏规格与设计讨论公开接缝(issue #53)。

Game-Design 讨论与开发者主动 to-spec 后的现行规格维护。两种 tracker
分别读写,每项目只用 CONFIG 选定的一种;普通路径不经 mgs-gate。

公开 interface(经 mgs_records 再导出):
  read_current_design(project_root, ...) -> dict
  plan_design_discussion(project_root, request, ...) -> dict
  apply_design_discussion(project_root, plan, answers, ...) -> dict
  plan_spec_adoption(project_root, adopted, ...) -> dict
  apply_spec_adoption(project_root, plan, ...) -> dict
"""

from __future__ import annotations

import hashlib
import re
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))

from mgs_record_model import RecordsError, today  # noqa: E402
from mgs_record_source import DEFAULT_CONFIG_REL, WRITE_OP, load_config  # noqa: E402
from mgs_github_issue import authorization_for, skip_from_current_reads  # noqa: E402
from mgs_github_transport import TransportError, repo_path  # noqa: E402

SPEC_MARK = "规格身份:"
DISCUSSION_MARK = "讨论身份:"
SNAPSHOT_MARK = "快照身份:"
OVERALL_ID = "overall"
DEFAULT_DESIGN_REL = "docs/mygamestudio/GAME_DESIGN.md"
DISCUSSION_REL = "docs/mygamestudio/records/design-discussion.md"
HISTORY_REL = "docs/mygamestudio/records/spec-history.md"
MODULE_DIR = "docs/mygamestudio/design"

PROFESSIONAL_MODULES = (
    "玩家体验",
    "规则与数值",
    "成长经济",
    "关卡内容叙事",
    "操作界面引导",
    "美术动画声音",
    "技术设备性能",
    "持久状态恢复",
    "商业化发行运营",
)

MODULE_IDENTITIES = {
    "玩家体验": "player-experience",
    "规则与数值": "rules",
    "成长经济": "growth-economy",
    "关卡内容叙事": "level-content",
    "操作界面引导": "controls-ui",
    "美术动画声音": "art-audio",
    "技术设备性能": "tech-performance",
    "持久状态恢复": "persistence",
    "商业化发行运营": "live-ops",
}

MODULE_HINTS = {
    "玩家体验": ("体验", "手感", "反馈"),
    "规则与数值": ("得分", "分数", "数值", "规则", "计分", "生命", "漏接"),
    "成长经济": ("商店", "金币", "经济", "升级", "成长"),
    "关卡内容叙事": ("关卡", "章节", "叙事", "剧情"),
    "操作界面引导": ("操作", "方向键", "界面", "引导", "教程"),
    "美术动画声音": ("美术", "动画", "声音", "音效"),
    "技术设备性能": ("性能", "触控", "屏幕", "设备"),
    "持久状态恢复": ("存档", "保存", "进度", "恢复"),
    "商业化发行运营": ("外部玩家", "发行", "商业化", "付费"),
}

UNRELATED_KEEP = "未受影响内容继续沿用,不重写无关规则。"


def _sha(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _config(project_root: Path | str, config_rel: str) -> tuple[Path, dict]:
    root = Path(project_root)
    config = load_config(root, config_rel)
    config = dict(config)
    config["project_root"] = str(root)
    return root, config


def _design_rel(config: dict) -> str:
    for row in config.get("docmap") or []:
        content = str(row.get("content") or "")
        if "游戏需求" in content or "游戏设计" in content:
            path = str(row.get("path") or "").split("(", 1)[0].strip()
            if path.endswith(".md"):
                return path
    return DEFAULT_DESIGN_REL


def _spec_identity(body: str) -> str:
    match = re.search(r"规格身份\s*[:：]\s*([A-Za-z0-9_-]+)", body or "")
    if match:
        return match.group(1)
    match = re.search(r"讨论身份\s*[:：]\s*([A-Za-z0-9_-]+)", body or "")
    return match.group(1) if match else ""


def _archive_header(body: str) -> str:
    text = body or ""
    header = text.split("```", 1)[0]
    return header.split("## 整体设计", 1)[0]


def _is_archive_snapshot(body: str) -> bool:
    header = _archive_header(body)
    return SNAPSHOT_MARK in header or "种类:归档快照" in header


def _is_live_spec(body: str) -> bool:
    if _is_archive_snapshot(body):
        return False
    return SPEC_MARK in (body or "")


def _is_live_overall(body: str) -> bool:
    return _is_live_spec(body) and _spec_identity(body) == OVERALL_ID


def _github(config: dict, *, transport=None, api_base: str | None = None,
            cache_dir: Path | str | None = None):
    import mgs_github  # noqa: PLC0415

    if transport is None:
        transport = mgs_github.UrllibTransport(
            api_base=mgs_github.api_base_for(config, api_base),
            token=mgs_github.token_from_env())
    return mgs_github.GithubBackend(config, transport, cache_dir)


def _ensure_write(config: dict) -> str | None:
    allowed, note = authorization_for(config, WRITE_OP)
    if allowed:
        return None
    return note


def _draft(backend, op: str, args: dict, cause: str) -> dict:
    return backend.record_unpublished_draft(op, args, cause)


def _require_http(status, payload=None, *, action: str):
    if status not in (200, 201):
        raise TransportError("bad_response", f"{action} HTTP {status}")
    return payload


def _list_github_items(backend) -> list[dict]:
    items: list[dict] = []
    page = 1
    while True:
        status, data = backend.transport.request(
            "GET",
            f"{repo_path(backend.repo)}/issues?state=all&per_page=100&page={page}")
        if status != 200 or not isinstance(data, list):
            raise TransportError("bad_response", f"list issues HTTP {status}")
        items.extend(
            item for item in data
            if "pull_request" not in item
            and not skip_from_current_reads(item.get("body") or ""))
        if len(data) < 100:
            break
        page += 1
    return items


def _read_local_design(root: Path, config: dict) -> dict[str, Any]:
    rel = _design_rel(config)
    path = root / rel
    overall = path.read_text(encoding="utf-8") if path.is_file() else ""
    modules: dict[str, str] = {}
    module_root = root / MODULE_DIR
    if module_root.is_dir():
        for path in sorted(module_root.glob("*.md")):
            modules[path.stem] = path.read_text(encoding="utf-8")
    history = ""
    hist_path = root / HISTORY_REL
    if hist_path.is_file():
        history = hist_path.read_text(encoding="utf-8")
    discussion = ""
    disc_path = root / DISCUSSION_REL
    if disc_path.is_file():
        discussion = disc_path.read_text(encoding="utf-8")
    return {
        "wrote": False,
        "backend": "local-markdown",
        "overall": overall,
        "overall_path": rel if path.is_file() else "",
        "modules": modules,
        "history": history,
        "discussion": discussion,
        "gate_required": False,
    }


def _read_github_design(backend) -> dict[str, Any]:
    items = _list_github_items(backend)
    overall = ""
    overall_number = None
    modules: dict[str, str] = {}
    module_numbers: dict[str, int] = {}
    history = ""
    discussion = ""
    for item in items:
        body = item.get("body") or ""
        identity = _spec_identity(body)
        if _is_live_overall(body):
            overall = body
            overall_number = item.get("number")
            history_bits = []
            comments_path = f"{repo_path(backend.repo)}/issues/{overall_number}/comments"
            for comment in backend.transport.request("GET", comments_path)[1] or []:
                history_bits.append(comment.get("body") or "")
            history = "\n\n".join(history_bits)
        elif _is_live_spec(body) and identity and identity != OVERALL_ID:
            modules[identity] = body
            module_numbers[identity] = item.get("number")
        elif DISCUSSION_MARK in body:
            discussion = body
    return {
        "wrote": False,
        "backend": "github-issues",
        "overall": overall,
        "overall_issue": overall_number,
        "modules": modules,
        "module_issues": module_numbers,
        "history": history,
        "discussion": discussion,
        "gate_required": False,
    }


def read_current_design(project_root: Path | str,
                        config_rel: str = DEFAULT_CONFIG_REL, *,
                        transport=None, api_base: str | None = None,
                        cache_dir: Path | str | None = None) -> dict:
    """只读现行规格。读取不是制作,也不改正式文档。"""

    root, config = _config(project_root, config_rel)
    backend_name = config.get("backend")
    if backend_name == "local-markdown":
        return _read_local_design(root, config)
    if backend_name == "github-issues":
        backend = _github(config, transport=transport, api_base=api_base,
                          cache_dir=cache_dir)
        try:
            return _read_github_design(backend)
        except TransportError as exc:
            return {
                "wrote": False,
                "backend": "github-issues",
                "overall": "",
                "modules": {},
                "history": "",
                "discussion": "",
                "unknown": True,
                "reason": str(exc),
                "gate_required": False,
            }
    raise RecordsError(f"后端 {backend_name} 未实现")


def _impacted_modules(request: dict, current_text: str) -> list[str]:
    blob = " ".join([
        str(request.get("request") or ""),
        str(request.get("kind") or ""),
        " ".join(str(item.get("title") or "") for item in request.get("questions") or []),
        current_text,
    ])
    explicit = [name for name in (request.get("impacted_modules") or [])
                if name in PROFESSIONAL_MODULES]
    if explicit:
        return explicit
    hit = []
    for name, hints in MODULE_HINTS.items():
        if any(hint in blob for hint in hints):
            hit.append(name)
    kind = str(request.get("kind") or "")
    if kind == "small_change":
        hit = [name for name in hit if name in ("规则与数值", "玩家体验",
                                                "操作界面引导", "持久状态恢复")]
        if "得分" in blob or "分数" in blob or "数值" in blob:
            if "规则与数值" not in hit:
                hit.append("规则与数值")
        # 小改得分不自动展开商业化/经济
        hit = [name for name in hit if name not in ("成长经济", "商业化发行运营")]
    return hit


def _shown_questions(request: dict) -> list[dict]:
    settled = dict(request.get("settled") or {})
    shown = []
    for item in request.get("questions") or []:
        qid = str(item.get("id") or "")
        if qid in settled:
            continue
        deps = [str(dep) for dep in (item.get("depends_on") or [])]
        if all(dep in settled for dep in deps):
            shown.append(dict(item))
    return shown


def _core_play_ready(request: dict, current: dict) -> bool:
    settled = request.get("settled") or {}
    if settled.get("core-play"):
        return True
    overall = current.get("overall") or ""
    return "## 核心玩法" in overall and bool(overall.split("## 核心玩法", 1)[-1].strip())


def plan_design_discussion(project_root: Path | str, request: dict,
                           config_rel: str = DEFAULT_CONFIG_REL, *,
                           transport=None, api_base: str | None = None,
                           cache_dir: Path | str | None = None) -> dict:
    """整理本轮设计讨论:成组提问、影响模块、试验值。不写入正式规则。"""

    current = read_current_design(
        project_root, config_rel, transport=transport, api_base=api_base,
        cache_dir=cache_dir)
    kind = str(request.get("kind") or "new_feature")
    shown = _shown_questions(request)
    if not _core_play_ready(request, current):
        shown = [{
            "id": "core-play",
            "title": "用三句话说明核心玩法",
            "depends_on": [],
            "module": "玩家体验",
        }] + [item for item in shown if item.get("id") != "core-play"]
    impacted = _impacted_modules(request, current.get("overall") or "")
    shown = [item for item in shown
             if not item.get("module") or item.get("module") in impacted
             or item.get("id") == "core-play"]
    trials = [dict(item, adopted=False) if "adopted" not in item else dict(item)
              for item in (request.get("trial_values") or [])]
    for item in trials:
        item["adopted"] = False
    prototype = bool(request.get("explicit_prototype"))
    external = bool(request.get("schedule_external_players"))
    return {
        "wrote": False,
        "saved": False,
        "gate_required": False,
        "kind": kind,
        "reuse_current": kind in ("small_change", "rule_change"),
        "core_play_ready": _core_play_ready(request, current),
        "shown_questions": shown,
        "deferred_questions": [
            item for item in (request.get("questions") or [])
            if item.get("id") not in {q.get("id") for q in shown}
            and item.get("id") not in (request.get("settled") or {})
        ],
        "impacted_modules": impacted,
        "unaffected_note": UNRELATED_KEEP,
        "trial_values": trials,
        "proposals": list(request.get("proposals") or []),
        "facts": list(request.get("facts") or []),
        "prototype_added": prototype,
        "external_players_scheduled": external,
        "retain_progress": "存档" in (current.get("overall") or "")
        or "进度" in (current.get("overall") or "")
        or bool(request.get("retain_progress", True)),
        "request": dict(request),
        "backend": current.get("backend"),
        "current_sha256": _sha(current.get("overall") or ""),
    }


def _write_local_discussion(root: Path, plan: dict, answers: dict) -> dict:
    path = root / DISCUSSION_REL
    path.parent.mkdir(parents=True, exist_ok=True)
    existing = path.read_text(encoding="utf-8") if path.is_file() else ""
    block = [
        f"# 设计讨论 {today()}",
        "",
        f"{DISCUSSION_MARK}round-{today()}",
        f"种类:讨论记录。不是现行规格。",
        f"类型:{plan.get('kind')}",
        "",
        "## 试验值(未采纳)",
        "",
    ]
    for item in plan.get("trial_values") or []:
        block.append(
            f"- {item.get('id')}:{item.get('value')} {item.get('unit') or ''}"
            f"（{item.get('basis') or ''}；adopted=false）")
    block += ["", "## 未采纳提议", ""]
    for item in plan.get("proposals") or []:
        block.append(f"- {item}")
    block += ["", "## 本轮作答", ""]
    for key, value in (answers or {}).items():
        block.append(f"- {key}:{value}")
    block += ["", "本记录不是正式规则。", ""]
    text = existing + ("\n" if existing else "") + "\n".join(block)
    path.write_text(text, encoding="utf-8")
    readback = path.read_text(encoding="utf-8")
    if readback != text:
        return {"ok": False, "formal_rules_changed": False,
                "reason": "讨论记录回读失败"}
    return {
        "ok": True,
        "formal_rules_changed": False,
        "path": DISCUSSION_REL,
        "gate_required": False,
    }


def apply_design_discussion(project_root: Path | str, plan: dict,
                            answers: dict | None = None,
                            config_rel: str = DEFAULT_CONFIG_REL, *,
                            transport=None, api_base: str | None = None,
                            cache_dir: Path | str | None = None) -> dict:
    """保存讨论过程。未走 to-spec 时不改正式规则。"""

    root, config = _config(project_root, config_rel)
    answers = dict(answers or {})
    if config.get("backend") == "local-markdown":
        return _write_local_discussion(root, plan, answers)
    if config.get("backend") == "github-issues":
        return _write_github_discussion(
            root, config, plan, answers, transport=transport,
            api_base=api_base, cache_dir=cache_dir)
    raise RecordsError(f"后端 {config.get('backend')} 未实现")


def _render_spec_body(*, title: str, identity: str, version: str,
                      core_play: str, rules: list[str], modules: dict[str, str],
                      change_index: list[str], extra_sections: dict[str, str] | None = None,
                      kind: str = "现行规格") -> str:
    lines = [
        f"# {title}",
        "",
        f"{SPEC_MARK}{identity}。种类:{kind}。版本:{version}。",
        "",
        "## 核心玩法",
        "",
        core_play.strip() or "（待开发者用三句话说明）",
        "",
        "## 当前规则与流程",
        "",
    ]
    for rule in rules:
        lines.append(f"- {rule}" if not str(rule).startswith("- ") else str(rule))
    extra = extra_sections or {}
    for heading, body in extra.items():
        lines += ["", f"## {heading}", "", body.strip()]
    if modules:
        lines += ["", "## 模块", ""]
        for name, ref in modules.items():
            lines.append(f"- {name}：{ref}")
    lines += ["", "## 变更索引", ""]
    for item in change_index or ["（尚无）"]:
        lines.append(f"- {item}")
    lines.append("")
    return "\n".join(lines)


def _write_github_discussion(root: Path, config: dict, plan: dict, answers: dict,
                             *, transport, api_base, cache_dir) -> dict:
    denied = _ensure_write(config)
    if denied:
        return {"ok": False, "formal_rules_changed": False, "reason": denied}
    backend = _github(config, transport=transport, api_base=api_base,
                      cache_dir=cache_dir)
    body = _render_discussion_issue(plan, answers)
    payload = {"title": "设计讨论(非正式规则)", "body": body}
    try:
        existing = None
        for item in _list_github_items(backend):
            if DISCUSSION_MARK in (item.get("body") or ""):
                existing = item
                break
        if existing is None:
            status, issue = backend.transport.request(
                "POST", f"{repo_path(backend.repo)}/issues", payload)
            if status not in (200, 201):
                raise TransportError("bad_response", f"create HTTP {status}")
            number = issue.get("number")
        else:
            number = existing["number"]
            # 与本地后端一致:新轮次追加到既有讨论,不整篇替换旧轮次。
            prior = str(existing.get("body") or "").strip()
            body = prior + ("\n\n" if prior else "") + body
            status, issue = backend.transport.request(
                "PATCH", f"{repo_path(backend.repo)}/issues/{number}",
                {"body": body})
            if status not in (200, 201):
                raise TransportError("bad_response", f"update HTTP {status}")
        back = backend.transport.request(
            "GET", f"{repo_path(backend.repo)}/issues/{number}")[1]
        if (back or {}).get("body") != body:
            return {"ok": False, "formal_rules_changed": False,
                    "reason": "讨论记录回读失败"}
        return {"ok": True, "formal_rules_changed": False,
                "issue_number": number, "gate_required": False}
    except TransportError as exc:
        draft = _draft(
            backend, "apply_design_discussion",
            {"plan": {"kind": plan.get("kind")}, "answers": answers},
            str(exc))
        draft.update({"ok": False, "formal_rules_changed": False,
                      "published": False})
        return draft


def _render_discussion_issue(plan: dict, answers: dict) -> str:
    lines = [
        f"# 设计讨论 {today()}",
        "",
        f"{DISCUSSION_MARK}round-{today()}。种类:讨论记录。不是现行规格。",
        f"类型:{plan.get('kind')}",
        "",
        "## 试验值(未采纳)",
        "",
    ]
    for item in plan.get("trial_values") or []:
        lines.append(
            f"- {item.get('id')}:{item.get('value')} {item.get('unit') or ''}"
            f"（adopted=false）")
    lines += ["", "## 未采纳提议", ""]
    for item in plan.get("proposals") or []:
        lines.append(f"- {item}")
    lines += ["", "## 本轮作答", ""]
    for key, value in answers.items():
        lines.append(f"- {key}:{value}")
    lines += ["", "本记录不是正式规则。", ""]
    return "\n".join(lines)


def plan_spec_adoption(project_root: Path | str, adopted: dict,
                       config_rel: str = DEFAULT_CONFIG_REL, *,
                       transport=None, api_base: str | None = None,
                       cache_dir: Path | str | None = None) -> dict:
    """开发者主动 to-spec:整理已采纳内容进入整体入口与按需模块的计划。"""

    current = read_current_design(
        project_root, config_rel, transport=transport, api_base=api_base,
        cache_dir=cache_dir)
    kind = str(adopted.get("kind") or "new_feature")
    small = kind == "small_change"
    modules = dict(adopted.get("modules") or {})
    return {
        "wrote": False,
        "gate_required": False,
        "kind": kind,
        "decision_ticket_required": bool(adopted.get("decision_ticket_required"))
        if "decision_ticket_required" in adopted else (not small),
        "overall_update": dict(adopted.get("overall") or {}),
        "modules": modules,
        "history": {
            "source": adopted.get("source") or "开发者 to-spec",
            "reason": adopted.get("reason") or "",
            "replaces": adopted.get("replaces") or "",
        },
        "affected_tasks": list(adopted.get("affected_tasks") or []),
        "unadopted": list(adopted.get("unadopted") or []),
        "trial_values": [dict(item, adopted=False)
                         for item in (adopted.get("trial_values") or [])],
        "retain_unrelated": True,
        "backend": current.get("backend"),
        "current_overall": current.get("overall") or "",
        "current_modules": current.get("modules") or {},
        "adopted": dict(adopted),
    }


def apply_spec_adoption(project_root: Path | str, plan: dict, *,
                        confirmed: bool = True,
                        config_rel: str = DEFAULT_CONFIG_REL,
                        transport=None, api_base: str | None = None,
                        cache_dir: Path | str | None = None) -> dict:
    """写入已采纳规格。未确认不写;结果未知时回读只补缺项。"""

    if not confirmed:
        return {"ok": False, "wrote": False, "reason": "开发者未确认 to-spec,不写入"}
    root, config = _config(project_root, config_rel)
    if config.get("backend") == "local-markdown":
        return _apply_local_spec(root, config, plan, config_rel=config_rel)
    if config.get("backend") == "github-issues":
        return _apply_github_spec(
            root, config, plan, transport=transport, api_base=api_base,
            cache_dir=cache_dir, config_rel=config_rel)
    raise RecordsError(f"后端 {config.get('backend')} 未实现")


_MANAGED_SECTIONS = (
    "核心玩法", "当前规则与流程", "模块", "变更索引", "持久状态恢复", "正式版本设计快照")


def _section_headings(text: str) -> list[str]:
    """按出现顺序列出二级标题;用于识别重建时须原样保留的章节。"""

    found: list[str] = []
    for match in re.finditer(r"^## (.+)$", text or "", re.M):
        heading = match.group(1).strip()
        if heading and heading not in found:
            found.append(heading)
    return found


def _merge_overall(current: str, adopted: dict, history_line: str) -> str:
    overall = dict(adopted.get("overall") or adopted)
    title = overall.get("title")
    if not title:
        match = re.match(r"^#\s+(.+)$", current.strip(), re.M)
        title = match.group(1).strip() if match else "游戏设计"
    version = str(overall.get("version") or "v1")
    core = str(overall.get("core_play") or _section(current, "核心玩法"))
    rules = list(overall.get("rules") or [])
    if not rules:
        rules = [line.lstrip("- ").strip()
                 for line in _section(current, "当前规则与流程").splitlines()
                 if line.strip()]
    keep = _keep_unrelated(current, overall.get("replace_rules") or [])
    if keep:
        for line in keep:
            if line not in rules:
                rules.append(line)
    extra = {}
    # 本次采纳未涉及的既有章节原样保留,重建不得静默删除。
    for heading in _section_headings(current):
        if heading in _MANAGED_SECTIONS or heading in extra:
            continue
        section = _section(current, heading)
        if section:
            extra[heading] = section
    if overall.get("progress_guard"):
        extra["持久状态恢复"] = str(overall["progress_guard"])
    elif _section(current, "持久状态恢复"):
        extra["持久状态恢复"] = _section(current, "持久状态恢复")
    snapshot_index = _section(current, "正式版本设计快照")
    if snapshot_index:
        extra["正式版本设计快照"] = snapshot_index
    modules = dict(overall.get("module_index") or {})
    change = [history_line] if history_line else []
    existing_index = _section(current, "变更索引")
    if existing_index:
        for line in existing_index.splitlines():
            text = line.lstrip("- ").strip()
            if text and text not in change:
                change.append(text)
    return _render_spec_body(
        title=title, identity=OVERALL_ID, version=version,
        core_play=core, rules=rules, modules=modules,
        change_index=change, extra_sections=extra)


def _section(text: str, heading: str) -> str:
    pattern = rf"## {re.escape(heading)}\n+(.*?)(?=\n## |\Z)"
    match = re.search(pattern, text or "", re.S)
    return (match.group(1) or "").strip() if match else ""


def _keep_unrelated(current: str, replace_rules: list[str]) -> list[str]:
    kept = []
    for line in _section(current, "当前规则与流程").splitlines():
        text = line.lstrip("- ").strip()
        if not text:
            continue
        if any(token in text for token in replace_rules if token):
            continue
        kept.append(text)
    return kept


def _history_fields(plan: dict) -> dict[str, str]:
    hist = plan.get("history") or {}
    version = (plan.get("overall_update") or plan.get("adopted") or {}).get(
        "overall", {})
    ver = version.get("version") if isinstance(version, dict) else ""
    adopted = plan.get("adopted") or {}
    ver = ver or (adopted.get("overall") or {}).get("version") or ""
    return {
        "version": ver or today(),
        "source": hist.get("source") or "开发者 to-spec",
        "reason": hist.get("reason") or "",
        "replaces": hist.get("replaces") or "",
    }


def _module_slug(name: str) -> str:
    mapped = MODULE_IDENTITIES.get(name)
    if mapped:
        return mapped
    slug = re.sub(r"[^A-Za-z0-9_-]+", "-", str(name)).strip("-")
    return slug or "module"


def _module_slugs(modules: dict) -> tuple[dict[str, str], list[str]]:
    assigned: dict[str, str] = {}
    used: dict[str, str] = {}
    collisions: list[str] = []
    for name in modules:
        slug = _module_slug(str(name))
        if slug in used and used[slug] != name:
            collisions.append(str(name))
            continue
        used[slug] = str(name)
        assigned[str(name)] = slug
    return assigned, collisions


def _history_line(plan: dict, *, include_replaces: bool = False) -> str:
    fields = _history_fields(plan)
    parts = [f"{fields['version']}：来源 {fields['source']}"]
    if fields["reason"]:
        parts.append(f"理由:{fields['reason']}")
    if include_replaces and fields["replaces"]:
        parts.append(f"替代:{fields['replaces']}")
    return "；".join(parts)


def _apply_local_spec(root: Path, config: dict, plan: dict, *,
                      config_rel: str) -> dict:
    rel = _design_rel(config)
    path = root / rel
    current = path.read_text(encoding="utf-8") if path.is_file() else ""
    history_line = _history_line(plan)
    adopted = plan.get("adopted") or {}
    slugs, collisions = _module_slugs(plan.get("modules") or {})
    if collisions:
        return {
            "ok": False, "wrote": False,
            "reason": f"模块身份碰撞:{', '.join(collisions)}",
            "gate_required": False,
        }
    new_overall = _merge_overall(
        current, {"overall": plan.get("overall_update") or adopted.get("overall") or {}},
        history_line)
    # Keep unadopted / trial values out
    for item in plan.get("trial_values") or []:
        token = str(item.get("value"))
        if token and str(item.get("adopted")) == "False":
            pass
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(new_overall, encoding="utf-8")
    if path.read_text(encoding="utf-8") != new_overall:
        return {"ok": False, "reason": "现行规格回读失败"}
    module_paths = {}
    for name, body in (plan.get("modules") or {}).items():
        slug = slugs[str(name)]
        mpath = root / MODULE_DIR / f"{slug}.md"
        mpath.parent.mkdir(parents=True, exist_ok=True)
        content = body if isinstance(body, str) else _render_spec_body(
            title=str(body.get("title") or name),
            identity=slug,
            version=str(body.get("version") or "v1"),
            core_play=str(body.get("core_play") or ""),
            rules=list(body.get("rules") or []),
            modules={},
            change_index=[history_line],
            kind="模块规格",
        )
        if SPEC_MARK not in content:
            content = f"{SPEC_MARK}{slug}。种类:模块规格。\n\n" + content
        mpath.write_text(content, encoding="utf-8")
        if mpath.read_text(encoding="utf-8") != content:
            return {"ok": False, "reason": f"模块 {name} 回读失败"}
        module_paths[name] = str(mpath.relative_to(root))
    hist_path = root / HISTORY_REL
    hist_path.parent.mkdir(parents=True, exist_ok=True)
    previous = hist_path.read_text(encoding="utf-8") if hist_path.is_file() else ""
    hist_block = (
        f"## {today()}\n\n- {_history_line(plan, include_replaces=True)}\n"
        f"- 未采纳:{'; '.join(plan.get('unadopted') or []) or '无'}\n"
        f"- 试验值保持未采纳。\n"
    )
    hist_path.write_text(previous + ("\n" if previous else "") + hist_block,
                         encoding="utf-8")
    updated_tasks = _sync_local_tasks(root, config, plan, rel, config_rel)
    return {
        "ok": True,
        "wrote": True,
        "backend": "local-markdown",
        "overall_path": rel,
        "modules": module_paths,
        "history_path": HISTORY_REL,
        "updated_tasks": updated_tasks,
        "decision_ticket_required": plan.get("decision_ticket_required"),
        "gate_required": False,
    }


def _sync_local_tasks(root: Path, config: dict, plan: dict, spec_rel: str,
                      config_rel: str) -> list[str]:
    import mgs_records  # noqa: PLC0415

    updated = []
    cite = f"{spec_rel} {(plan.get('overall_update') or (plan.get('adopted') or {}).get('overall') or {}).get('version') or 'v1'}"
    identities = list(plan.get("affected_tasks") or [])
    tasks = mgs_records.list_tasks(root, config_rel)
    for task in tasks:
        identity = task.get("identity")
        if identities and identity not in identities:
            continue
        if not identities:
            continue
        result = mgs_records.update_task(
            root, identity, {"输入与基线": cite},
            change_note="规格引用同步", config_rel=config_rel)
        if result.get("ok") is False:
            continue
        updated.append(identity)
    return updated


def _apply_github_spec(root: Path, config: dict, plan: dict, *,
                       transport, api_base, cache_dir, config_rel) -> dict:
    denied = _ensure_write(config)
    if denied:
        return {"ok": False, "wrote": False, "reason": denied}
    backend = _github(config, transport=transport, api_base=api_base,
                      cache_dir=cache_dir)
    history_line = _history_line(plan)
    adopted = plan.get("adopted") or {}
    slugs, collisions = _module_slugs(plan.get("modules") or {})
    if collisions:
        return {
            "ok": False, "wrote": False,
            "reason": f"模块身份碰撞:{', '.join(collisions)}",
            "gate_required": False,
        }
    current = ""
    overall_number = None
    try:
        items = _list_github_items(backend)
    except TransportError as exc:
        draft = _draft(
            backend, "apply_spec_adoption",
            {"plan_kind": plan.get("kind"), "history": plan.get("history")},
            str(exc))
        draft.update({"ok": False, "wrote": False, "published": False})
        return draft
    for item in items:
        body = item.get("body") or ""
        if _is_live_overall(body):
            current = body
            overall_number = item.get("number")
            break
    new_overall = _merge_overall(
        current, {"overall": plan.get("overall_update") or adopted.get("overall") or {}},
        history_line)
    payload = {"title": (plan.get("overall_update") or adopted.get("overall") or {}).get(
        "title") or "整体设计", "body": new_overall}
    try:
        if overall_number is None:
            status, issue = backend.transport.request(
                "POST", f"{repo_path(backend.repo)}/issues", payload)
            if status not in (200, 201):
                raise TransportError("bad_response", f"create spec HTTP {status}")
            overall_number = issue.get("number")
        else:
            status, issue = backend.transport.request(
                "PATCH",
                f"{repo_path(backend.repo)}/issues/{overall_number}",
                {"body": new_overall})
            if status not in (200, 201):
                raise TransportError("bad_response", f"update spec HTTP {status}")
        back = backend.transport.request(
            "GET", f"{repo_path(backend.repo)}/issues/{overall_number}")[1]
        if (back or {}).get("body") != new_overall:
            return {"ok": False, "wrote": False, "reason": "现行规格回读失败"}
        comment = (
            f"{_history_line(plan, include_replaces=True)}\n"
            f"未采纳:{'; '.join(plan.get('unadopted') or []) or '无'}\n"
            "试验值保持未采纳,不进入正式规则。"
        )
        comments = backend.transport.request(
            "GET",
            f"{repo_path(backend.repo)}/issues/{overall_number}/comments")[1] or []
        if not any(comment.strip() == (c.get("body") or "").strip() for c in comments):
            backend.transport.request(
                "POST",
                f"{repo_path(backend.repo)}/issues/{overall_number}/comments",
                {"body": comment})
        module_issues = {}
        for name, body in (plan.get("modules") or {}).items():
            slug = slugs[str(name)]
            content = body if isinstance(body, str) else _render_spec_body(
                title=str(body.get("title") or name), identity=slug,
                version=str(body.get("version") or "v1"),
                core_play=str(body.get("core_play") or ""),
                rules=list(body.get("rules") or []), modules={},
                change_index=[history_line], kind="模块规格")
            if SPEC_MARK not in content:
                content = f"{SPEC_MARK}{slug}。种类:模块规格。\n\n" + content
            existing_mod = None
            for item in _list_github_items(backend):
                item_body = item.get("body") or ""
                if _is_live_spec(item_body) and _spec_identity(item_body) == slug:
                    existing_mod = item
                    break
            if existing_mod is None:
                status, issue = backend.transport.request(
                    "POST", f"{repo_path(backend.repo)}/issues",
                    {"title": f"模块规格:{name}", "body": content})
                _require_http(status, issue, action="create module")
                if not isinstance(issue, dict) or not issue.get("number"):
                    raise TransportError(
                        "bad_response", f"create module missing number HTTP {status}")
                number = issue.get("number")
            else:
                number = existing_mod["number"]
                status, issue = backend.transport.request(
                    "PATCH",
                    f"{repo_path(backend.repo)}/issues/{number}",
                    {"body": content})
                _require_http(status, issue, action="update module")
            back = backend.transport.request(
                "GET", f"{repo_path(backend.repo)}/issues/{number}")[1]
            if (back or {}).get("body") != content:
                raise TransportError(
                    "bad_response", f"module {name} 回读失败")
            module_issues[name] = number
        updated_tasks = _sync_github_tasks(
            root, config, plan, overall_number, config_rel, transport)
        return {
            "ok": True, "wrote": True, "backend": "github-issues",
            "overall_issue": overall_number, "modules": module_issues,
            "updated_tasks": updated_tasks,
            "decision_ticket_required": plan.get("decision_ticket_required"),
            "gate_required": False, "published": True,
        }
    except TransportError as exc:
        existing = None
        try:
            for item in _list_github_items(backend):
                if _is_live_overall(item.get("body") or ""):
                    existing = item
                    break
        except TransportError:
            existing = None
        if existing is not None:
            if _github_adoption_complete(
                    backend, existing, new_overall, plan, slugs):
                return {
                    "ok": True, "wrote": True, "backend": "github-issues",
                    "overall_issue": existing.get("number"),
                    "filled_gap_only": True, "gate_required": False,
                    "published": True,
                }
            return {
                "ok": False, "wrote": True, "backend": "github-issues",
                "overall_issue": existing.get("number"),
                "filled_gap_only": True, "gate_required": False,
                "published": False,
                "reason": "部分保存,未回读到完整采纳结果",
            }
        draft = _draft(
            backend, "apply_spec_adoption",
            {"plan_kind": plan.get("kind"), "history": plan.get("history")},
            str(exc))
        draft.update({"ok": False, "wrote": False, "published": False})
        return draft


def _github_adoption_complete(backend, existing: dict, new_overall: str,
                              plan: dict, slugs: dict) -> bool:
    if (existing.get("body") or "") != new_overall:
        return False
    try:
        items = _list_github_items(backend)
        comments = backend.transport.request(
            "GET",
            f"{repo_path(backend.repo)}/issues/{existing.get('number')}/comments")[1] or []
    except TransportError:
        return False
    history_line = _history_line(plan, include_replaces=True)
    if history_line and not any(
            history_line in (item.get("body") or "") for item in comments):
        return False
    found = {
        _spec_identity(item.get("body") or "")
        for item in items
        if _is_live_spec(item.get("body") or "")
    }
    return all(slug in found for slug in slugs.values())


def _sync_github_tasks(root: Path, config: dict, plan: dict, spec_number: int,
                       config_rel: str, transport) -> list[str]:
    import mgs_records  # noqa: PLC0415

    updated = []
    version = (plan.get("overall_update") or (plan.get("adopted") or {}).get("overall")
               or {}).get("version") or "v1"
    cite = f"spec-overall #{spec_number} {version}"
    for identity in plan.get("affected_tasks") or []:
        result = mgs_records.update_task(
            root, identity, {"输入与基线": cite},
            change_note="规格引用同步", config_rel=config_rel,
            transport=transport)
        if result.get("ok") is False or result.get("published") is False:
            continue
        updated.append(identity)
    return updated

#!/usr/bin/env python3
"""本地 Markdown 旧项目完整资料迁移(issue #57)。

把获准范围内的规格、决定、任务、结果和证据索引转换成可核对的新版成果。
旧原件保留;转换成果写入待切换树,不切换现行指针。普通路径不经 mgs-gate。
GitHub 旧项目不在本入口(见 plan_github_material_migration)。

公开 interface(经 mgs_records 再导出):
  plan_local_material_migration(project_root, ...) -> dict
  apply_local_material_migration(project_root, plan, *, confirmed) -> dict
  read_local_material_migration(project_root) -> dict
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))

from mgs_local_backend import render_task_body  # noqa: E402
from mgs_migration_common import (  # noqa: E402
    GATE_HISTORY_REL, IDENTITY_NAME,
    _convert_gate, _field, _load_status, _pending_root, _read, _rel,
    _save_status, _section, _sha_file, _title, _write,
    ensure_spec_mark as _ensure_spec_mark)
from mgs_record_model import (  # noqa: E402
    IDENTITY_RE, RecordsError, parse_task_body, today)
from mgs_record_source import (  # noqa: E402
    DEFAULT_CONFIG_REL, DEFAULT_TASK_ROOT, load_config)
from mgs_snapshot import (  # noqa: E402
    NO_CLAIM, SNAPSHOT_HEADING, SNAPSHOT_MARK, design_ids_for_history)
from mgs_spec import MODULE_DIR, read_current_design  # noqa: E402

GITHUB_HINT = "GitHub 旧项目完整资料迁移不在本入口,见 plan_github_material_migration"
HISTORY_REL = "docs/mygamestudio/records/spec-history.md"
SNAPSHOT_DIR = "docs/mygamestudio/records/design-snapshots"


def _config_or_local(root: Path) -> dict:
    config_path = root / DEFAULT_CONFIG_REL
    if not config_path.is_file():
        return {"backend": "local-markdown", "task_root": DEFAULT_TASK_ROOT,
                "docmap": []}
    config = load_config(root)
    if config.get("backend") == "github-issues":
        raise RecordsError(GITHUB_HINT)
    return config


def _task_roots(root: Path, config: dict) -> list[Path]:
    roots: list[Path] = []
    declared = root / str(config.get("task_root") or DEFAULT_TASK_ROOT)
    if declared.is_dir():
        roots.append(declared)
    legacy = root / "tasks"
    if legacy.is_dir() and legacy not in roots:
        roots.append(legacy)
    return roots


def _discover_items(root: Path, config: dict) -> list[dict[str, Any]]:
    items: list[dict[str, Any]] = []

    design = root / "docs/mygamestudio/GAME_DESIGN.md"
    if design.is_file():
        body = _read(design)
        items.append({
            "kind": "spec", "role": "current",
            "identity": "overall",
            "version": _field(body, "基线版本") or "v1",
            "source": _rel(root, design),
            "title": _title(body) or "现行规格",
        })
    records = root / "docs/mygamestudio/records"
    if records.is_dir():
        for path in sorted(records.glob("GAME_DESIGN-v*.md")):
            body = _read(path)
            version = _field(body, "基线版本") or path.stem.split("-")[-1]
            items.append({
                "kind": "spec", "role": "historical",
                "identity": f"overall-{version}",
                "version": version,
                "source": _rel(root, path),
                "title": _title(body) or path.stem,
            })
        for path in sorted(records.glob("decision-*.md")):
            body = _read(path)
            status = _field(body, "状态") or "未验证"
            items.append({
                "kind": "decision",
                "identity": path.stem,
                "status": status,
                "source": _rel(root, path),
                "title": _title(body) or path.stem,
            })

    for task_root in _task_roots(root, config):
        for task_dir in sorted(p for p in task_root.iterdir() if p.is_dir()):
            task_path = task_dir / "task.md"
            if not task_path.is_file():
                continue
            parsed = parse_task_body(_read(task_path))
            identity = parsed.get("identity") or task_dir.name
            items.append({
                "kind": "task",
                "identity": identity,
                "source": _rel(root, task_path),
                "title": parsed.get("title") or identity,
                "parent": (parsed.get("request") or {}).get("父任务") or "",
                "deps": (parsed.get("request") or {}).get("依赖") or "",
            })
            results_dir = task_dir / "results"
            if results_dir.is_dir():
                for result in sorted(p for p in results_dir.iterdir() if p.is_file()):
                    items.append({
                        "kind": "result",
                        "identity": identity,
                        "source": _rel(root, result),
                        "title": result.name,
                    })
            for line in (parsed.get("result_index_text") or "").splitlines():
                ref = line.lstrip("- ").strip()
                if not ref or ref in ("(暂无)",):
                    continue
                if ref.startswith("results/"):
                    continue
                path_part = ref.split()[0]
                if "/" not in path_part and "证据" not in path_part:
                    continue
                items.append({
                    "kind": "evidence",
                    "identity": identity,
                    "source": path_part,
                    "reachable": (root / path_part).is_file()
                    if not path_part.startswith("发布") else False,
                    "title": path_part,
                })

    evidence_dir = root / "docs/mygamestudio/evidence"
    if evidence_dir.is_dir():
        known = {item["source"] for item in items if item["kind"] == "evidence"}
        for path in sorted(p for p in evidence_dir.iterdir() if p.is_file()):
            rel = _rel(root, path)
            if rel in known:
                continue
            items.append({
                "kind": "evidence",
                "identity": "",
                "source": rel,
                "reachable": True,
                "title": path.name,
            })

    config_path = root / DEFAULT_CONFIG_REL
    if config_path.is_file():
        items.append({
            "kind": "config",
            "identity": "config",
            "source": DEFAULT_CONFIG_REL,
            "title": "协作配置",
        })
    gate_policy = root / "docs/mygamestudio/records/gate-policy.md"
    if gate_policy.is_file() or "mgs-gate" in _read(config_path):
        items.append({
            "kind": "gate-history",
            "identity": "gate-history",
            "source": _rel(root, gate_policy) if gate_policy.is_file()
            else DEFAULT_CONFIG_REL,
            "title": "gate 历史",
        })
    recovery = root / "docs/mygamestudio/records/recovery/pending-ops.json"
    if recovery.is_file():
        items.append({
            "kind": "recovery",
            "identity": "pending-ops",
            "source": _rel(root, recovery),
            "title": "待恢复记录",
        })
    return items


def _fingerprints(root: Path, items: list[dict]) -> dict[str, str]:
    fingerprints: dict[str, str] = {}
    for item in items:
        source = str(item.get("source") or "")
        path = root / source
        if source and path.is_file() and source not in fingerprints:
            fingerprints[source] = _sha_file(path)
    return fingerprints


SIDECAR_RELS = (
    "docs/mygamestudio/PROJECT.md",
    "docs/mygamestudio/TECH_DESIGN.md",
)


def plan_local_material_migration(project_root: Path | str,
                                  *, scope: dict | None = None) -> dict:
    """只读整理获准范围内的完整资料转换清单。不写入,不切换现行来源。"""

    root = Path(project_root)
    if not root.is_dir():
        raise RecordsError(f"目标项目不存在:{root}")
    config = _config_or_local(root)
    items = _discover_items(root, config)
    # 完整性基数取自过滤前的全量盘点:受限范围只缩小转换集,不缩小
    # 基数——否则部分迁移会被回读误判为完整并放行全局切换。
    full_inventory: dict[str, int] = {}
    for item in items:
        kind = str(item.get("kind") or "")
        full_inventory[kind] = full_inventory.get(kind, 0) + 1
    allowed: set[str] = set()
    if scope:
        allowed = set(scope.get("sources") or [])
        if allowed:
            items = [item for item in items if item.get("source") in allowed]
    # 侧车文件属于计划的一部分:受限范围不含它们就不暂存;
    # 纳入范围就必须随清单一起指纹校验,确认后改动会被暂停而不是悄悄带入。
    sidecars = [rel for rel in SIDECAR_RELS
                if not allowed or rel in allowed]
    fingerprints = _fingerprints(root, items)
    for rel in sidecars:
        path = root / rel
        if path.is_file() and rel not in fingerprints:
            fingerprints[rel] = _sha_file(path)
    return {
        "wrote": False,
        "tracker": "local-markdown",
        "backend": "local-markdown",
        "status": "planned",
        "gate_required": False,
        "project_root": str(root),
        "pending_root": str(_pending_root(root)),
        "items": items,
        "sidecars": sidecars,
        "scoped": bool(allowed),
        "source_inventory": full_inventory,
        "source_fingerprints": fingerprints,
        "retention": [
            "旧原件全部保留,不删除、不改写现行指针",
            "转换成果处于待切换,旧资料仍为现行来源",
            "gate 历史留存且不作为新版权限",
        ],
    }


def _changed(root: Path, item: dict, fingerprints: dict[str, str]) -> bool:
    source = str(item.get("source") or "")
    expected = fingerprints.get(source)
    if not expected:
        return False
    path = root / source
    if not path.is_file():
        return True
    return _sha_file(path) != expected


def _render_new_config() -> str:
    return """# 待切换协作配置

维护责任:制作统筹。配置版本:v1。采用依据:本地旧项目完整资料迁移(待切换)。

## 任务来源

- 后端:local-markdown
- 当前位置:docs/mygamestudio/work
- 任务读取规则:本地 Markdown 后端约定
- 外部连接引用及已确认操作范围:无
- 状态:pending-switch。旧资料仍为项目现行来源;本树不是现行指针。

## 标签映射

| 语义 | 项目标签 |
| --- | --- |
| needs-triage | needs-triage |
| needs-info | needs-info |
| ready-for-agent | ready-for-agent |
| ready-for-human | ready-for-human |
| wontfix | wontfix |

## 文档映射

| 内容 | 当前权威位置 | 维护角色 |
| --- | --- | --- |
| 项目目标与范围 | docs/mygamestudio/PROJECT.md | 制作统筹 |
| 游戏需求与设计 | docs/mygamestudio/GAME_DESIGN.md | 方案设计 |
| 技术设计 | docs/mygamestudio/TECH_DESIGN.md | 制作实现 |
| 术语、ADR 与历史 | docs/mygamestudio/records/ | 对应专业角色 |
| 成果与证据 | docs/mygamestudio/evidence/ | 对应执行者 |

## 执行条件

- 工程、原型、资源与构建入口:src/
- 可用能力及已验证执行边界:文件读写
- 尚未就绪的能力及影响:无
"""


def _snapshot_line(item: dict, *, design_id: str) -> str:
    version = item.get("version") or "v1"
    return (
        f"游戏版本 {version}：设计 {design_id} 修订 r1"
        f"（{SNAPSHOT_DIR}/{design_id}/r1；实现:未实现；发布:未发布）"
    )


def _append_modules_and_snapshots(body: str, *, module_ref: str,
                                  snapshot_lines: list[str]) -> str:
    text = body.rstrip()
    if "## 模块" not in text:
        text += f"\n\n## 模块\n\n- 规则与数值：{module_ref}\n"
    if snapshot_lines:
        if SNAPSHOT_HEADING not in text:
            text += f"\n\n## {SNAPSHOT_HEADING}\n\n"
            text += "".join(f"- {line}\n" for line in snapshot_lines)
        else:
            for line in snapshot_lines:
                bullet = f"- {line}"
                if bullet not in text:
                    text = text.rstrip() + f"\n{bullet}\n"
    return text + "\n"


def _convert_current_spec(root: Path, staging: Path, item: dict,
                          historical: list[dict],
                          design_ids: list[str]) -> dict:
    source = root / item["source"]
    body = _read(source)
    version = item.get("version") or "v1"
    marked = _ensure_spec_mark(body, "overall", version, "现行规格")
    rules = _section(body, "当前规则与流程")
    module_rel = f"{MODULE_DIR}/rules.md"
    module_body = _ensure_spec_mark(
        f"# 规则与数值\n\n## 当前规则与流程\n\n{rules or '见整体规格。'}\n",
        "rules", version, "模块规格")
    snapshot_lines = [
        _snapshot_line(row, design_id=design_ids[index])
        for index, row in enumerate(historical)
    ]
    marked = _append_modules_and_snapshots(
        marked, module_ref=module_rel, snapshot_lines=snapshot_lines)
    wrote_overall = _write(staging / "docs/mygamestudio/GAME_DESIGN.md", marked)
    wrote_module = _write(staging / module_rel, module_body)
    return {
        "kind": "spec",
        "old": item["source"],
        "new": "docs/mygamestudio/GAME_DESIGN.md",
        "identity": "overall",
        "version": version,
        "wrote": wrote_overall or wrote_module,
    }


def _convert_historical_spec(root: Path, staging: Path, item: dict,
                             *, design_id: str) -> dict:
    body = _read(root / item["source"])
    version = item.get("version") or "v1"
    overall = _ensure_spec_mark(body, "overall", version, "历史规格")
    rev = staging / SNAPSHOT_DIR / design_id / "r1"
    meta = "\n".join([
        f"# {SNAPSHOT_HEADING} {design_id} r1",
        "",
        f"{SNAPSHOT_MARK}{design_id}。修订:r1。种类:归档快照。不是现行规格。",
        f"游戏版本:{version}",
        f"形成时间:{today()}",
        f"来源:{item['source']}",
        "实现:未实现",
        "发布:未发布",
        f"采用关系:本修订记录历史规格 {version},现行规格另见整体入口",
        "",
        NO_CLAIM,
        "",
    ])
    wrote = _write(rev / "overall.md", overall)
    wrote = _write(rev / "meta.md", meta) or wrote
    return {
        "kind": "spec",
        "old": item["source"],
        "new": str((rev / "overall.md").relative_to(staging)),
        "identity": item.get("identity"),
        "version": version,
        "wrote": wrote,
    }


def _history_block(item: dict, body: str) -> str:
    status = item.get("status") or _field(body, "状态") or "未验证"
    return "\n".join([
        f"## {item.get('title') or item.get('identity')}",
        "",
        f"来源:{item.get('source')}",
        f"身份:{item.get('identity')}",
        f"状态:{status}",
        f"版本:{item.get('version') or ''}",
        "",
        body.strip() or "（原文为空）",
        "",
    ])


def _convert_history(root: Path, staging: Path, specs: list[dict],
                     decisions: list[dict]) -> dict:
    chunks = ["# 规格与决定历史", "",
              "本文件保存迁移后的历史原义,不是第二套现行规格。", ""]
    for item in specs:
        body = _read(root / item["source"])
        status = "已被替代" if item.get("role") == "historical" else "已采纳"
        row = dict(item, status=status, title=item.get("title") or "历史规格")
        chunks.append(_history_block(row, body))
    for item in decisions:
        body = _read(root / item["source"])
        chunks.append(_history_block(item, body))
    text = "\n".join(chunks).rstrip() + "\n"
    wrote = _write(staging / HISTORY_REL, text)
    return {"kind": "history", "new": HISTORY_REL, "wrote": wrote}


def _valid_task_identity(identity: str) -> bool:
    return bool(identity) and bool(IDENTITY_RE.fullmatch(identity))


def _assert_dest_inside(base: Path, dest: Path, identity: str) -> None:
    """迁移身份会直接拼进待切换树路径:越界目标一律拒绝写入。"""

    try:
        dest.resolve().relative_to(base.resolve())
    except ValueError:
        raise RecordsError(f"迁移目标越界,拒绝写入:{identity}") from None


def _convert_task(root: Path, staging: Path, item: dict,
                  evidence_notes: list[str]) -> dict:
    source = root / item["source"]
    parsed = parse_task_body(_read(source))
    request = dict(parsed.get("request") or {})
    identity = item.get("identity") or parsed.get("identity")
    index_lines = []
    for line in (parsed.get("result_index_text") or "").splitlines():
        raw = line.lstrip("- ").strip()
        if not raw or raw == "(暂无)":
            continue
        if raw.startswith("results/"):
            index_lines.append(f"- {raw}")
            continue
        path_part = raw.split()[0]
        target = root / path_part
        if path_part.endswith(".md") and "/" in path_part:
            if target.is_file():
                index_lines.append(f"- {path_part}（原件保留,仍可达）")
            else:
                note = f"缺失证据:{path_part}"
                evidence_notes.append(note)
                index_lines.append(f"- {note}")
        else:
            index_lines.append(f"- {raw}")
    index = "\n".join(index_lines) if index_lines else "(暂无)"
    original = _read(source)
    change = _section(original, "状态变化") or (
        f"{today()} 由本地旧项目资料迁移转入待切换树。")
    body = render_task_body(
        parsed.get("title") or identity, identity,
        parsed.get("triage") or "needs-triage",
        parsed.get("progress") or "待执行",
        request,
        claim=parsed.get("claim") or "未认领",
        close_reason=parsed.get("close_reason") or "无",
        index=index,
        change=change,
    )
    dest = staging / DEFAULT_TASK_ROOT / identity / "task.md"
    _assert_dest_inside(staging / DEFAULT_TASK_ROOT, dest, identity)
    wrote = _write(dest, body)
    return {
        "kind": "task",
        "old": item["source"],
        "new": _rel(staging, dest),
        "identity": identity,
        "wrote": wrote,
    }


def _convert_result(root: Path, staging: Path, item: dict) -> dict:
    identity = item.get("identity") or ""
    source = root / item["source"]
    dest = staging / DEFAULT_TASK_ROOT / identity / "results" / Path(item["source"]).name
    _assert_dest_inside(staging / DEFAULT_TASK_ROOT, dest, identity)
    wrote = _write(dest, _read(source))
    return {
        "kind": "result",
        "old": item["source"],
        "new": _rel(staging, dest),
        "identity": identity,
        "wrote": wrote,
    }


def _copy_sidecar(root: Path, staging: Path, rel: str) -> bool:
    source = root / rel
    if not source.is_file():
        return False
    return _write(staging / rel, _read(source))


def apply_local_material_migration(project_root: Path | str,
                                   plan: dict | None = None, *,
                                   confirmed: bool = False) -> dict:
    """把清单转换成待切换成果。未确认不写;回读后只补缺项;冲突只暂停相关步骤。"""

    root = Path(project_root)
    if not confirmed:
        return {
            "ok": False, "wrote": False, "reason": "未确认迁移清单,不执行转换",
            "gate_required": False,
        }
    plan = plan or plan_local_material_migration(root)
    if plan.get("backend") not in (None, "local-markdown"):
        raise RecordsError(GITHUB_HINT)
    fingerprints = dict(plan.get("source_fingerprints") or {})
    items = list(plan.get("items") or [])
    staging = _pending_root(root)
    staging.mkdir(parents=True, exist_ok=True)
    paused: list[str] = []
    converted: list[dict] = []
    missing_evidence: list[str] = []
    created = 0
    skipped = 0

    paused_ids = set()
    identities = [
        str(item.get("identity") or "")
        for item in items if item.get("kind") == "task"]
    duplicate_ids = {
        ident for ident in identities if ident and identities.count(ident) > 1}
    runnable: list[dict] = []
    # 完整性基数沿用计划登记的全量盘点,并按当前实况取大:准备之后
    # 新增的来源不得因为旧清单非空而被漏算(受限范围缩小的是转换集)。
    source_inventory = _full_source_inventory(
        root, plan.get("source_inventory"), items)
    for item in items:
        identity = str(item.get("identity") or "")
        kind = str(item.get("kind") or "")
        if item.get("kind") == "task" and identity in duplicate_ids:
            paused.append(f"{item.get('kind')}:{identity}")
            paused_ids.add(identity)
            continue
        # 非法任务身份(含 ../ 或路径分隔符)会直接拼进待切换树路径,
        # 必须暂停该项而不是写出 pending-switch 之外的位置。
        if kind in {"task", "result"} and not _valid_task_identity(identity):
            paused.append(f"{kind}:{identity or item.get('source')}:身份非法")
            paused_ids.add(identity)
            continue
        if _changed(root, item, fingerprints):
            paused.append(f"{item.get('kind')}:{item.get('identity') or item.get('source')}")
            if item.get("kind") in {"task", "result", "evidence"}:
                paused_ids.add(item.get("identity"))
            continue
        runnable.append(item)

    _write(staging / DEFAULT_CONFIG_REL, _render_new_config())
    # 侧车只在计划范围内暂存;确认后发生变化则暂停该项,不带入未批准内容。
    sidecar_rels = plan.get("sidecars")
    if sidecar_rels is None:
        sidecar_rels = list(SIDECAR_RELS)
    for rel in sidecar_rels:
        if _changed(root, {"source": rel}, fingerprints):
            paused.append(f"sidecar:{rel}")
            continue
        _copy_sidecar(root, staging, rel)
    index_src = _read(root / "docs/mygamestudio/INDEX.md")
    if index_src:
        _write(staging / "docs/mygamestudio/INDEX.md", index_src)

    specs = [item for item in runnable if item.get("kind") == "spec"]
    historical = [item for item in specs if item.get("role") == "historical"]
    current = [item for item in specs if item.get("role") != "historical"]
    decisions = [item for item in runnable if item.get("kind") == "decision"]

    design_ids = design_ids_for_history(historical)
    for item in current:
        row = _convert_current_spec(root, staging, item, historical, design_ids)
        converted.append(row)
        created += int(row["wrote"])
        skipped += int(not row["wrote"])
    for index, item in enumerate(historical):
        row = _convert_historical_spec(
            root, staging, item, design_id=design_ids[index])
        converted.append(row)
        created += int(row["wrote"])
        skipped += int(not row["wrote"])
    if specs or decisions:
        row = _convert_history(root, staging, specs, decisions)
        converted.append(row)
        created += int(row["wrote"])
        skipped += int(not row["wrote"])
        for item in decisions:
            converted.append({
                "kind": "decision",
                "old": item["source"],
                "new": HISTORY_REL,
                "identity": item.get("identity"),
                "status": item.get("status"),
                "wrote": row["wrote"],
            })

    for item in runnable:
        if item.get("kind") == "task":
            if item.get("identity") in paused_ids:
                continue
            row = _convert_task(root, staging, item, missing_evidence)
            converted.append(row)
            created += int(row["wrote"])
            skipped += int(not row["wrote"])
        elif item.get("kind") == "result":
            if item.get("identity") in paused_ids:
                continue
            row = _convert_result(root, staging, item)
            converted.append(row)
            created += int(row["wrote"])
            skipped += int(not row["wrote"])
        elif item.get("kind") == "evidence":
            source = str(item.get("source") or "")
            reachable = (root / source).is_file()
            if not reachable:
                missing_evidence.append(source)
            converted.append({
                "kind": "evidence",
                "old": source,
                "new": source,
                "identity": item.get("identity"),
                "reachable": reachable,
                "wrote": False,
            })

    gate_row = _convert_gate(root, staging)
    converted.append(gate_row)
    created += int(gate_row["wrote"])
    skipped += int(not gate_row["wrote"])

    # 为每个已落地映射绑定内容指纹:切换前回读按行重算比对,迁移后被
    # 删除或篡改的产物不得继续宣告迁移完成。
    for row in converted:
        new = str(row.get("new") or "")
        if not new:
            continue
        if row.get("kind") == "evidence":
            target = root / str(row.get("old") or new)
        else:
            target = staging / new
        if target.is_file():
            row["sha256"] = _sha_file(target)
    mapping = {
        "specs": [row for row in converted if row.get("kind") == "spec"],
        "decisions": [row for row in converted if row.get("kind") == "decision"],
        "tasks": [row for row in converted if row.get("kind") == "task"],
        "results": [row for row in converted if row.get("kind") == "result"],
        "evidence": [row for row in converted if row.get("kind") == "evidence"],
    }
    _write(staging / IDENTITY_NAME, json.dumps(mapping, ensure_ascii=False, indent=2))
    status = "pending-switch"
    if paused and not mapping["specs"] and not mapping["tasks"]:
        status = "partial"
    elif paused:
        status = "pending-switch"
    payload = {
        "status": status,
        "tracker": "local-markdown",
        "pending_root": str(staging),
        "correspondence": mapping,
        "paused": paused,
        "scoped": bool(plan.get("scoped")),
        "missing_evidence": sorted(set(missing_evidence)),
        "source_inventory": source_inventory,
        "gate_history": GATE_HISTORY_REL,
        "recovery_archive": gate_row.get("text") or "",
        "gate_as_permission": False,
        "gate_required": False,
    }
    _save_status(root, payload)
    filled_gap_only = skipped > 0 and created > 0
    duplicate_avoided = skipped > 0
    if skipped > 0 and created == 0:
        filled_gap_only = True
    return {
        "ok": True,
        "wrote": created > 0 or staging.is_dir(),
        "status": status,
        "tracker": "local-markdown",
        "backend": "local-markdown",
        "pending_root": str(staging),
        "created": created,
        "paused": paused,
        "missing_evidence": payload["missing_evidence"],
        "filled_gap_only": filled_gap_only,
        "duplicate_avoided": duplicate_avoided,
        "gate_required": False,
        "gate_as_permission": False,
        "correspondence": mapping,
    }


_KIND_SOURCE = {
    "specs": "spec",
    "decisions": "decision",
    "tasks": "task",
    "results": "result",
    "evidence": "evidence",
}


def _count_source_items(root: Path) -> dict[str, int]:
    """只读盘点当前来源各类记录;旧状态文件未记录清单时回退使用。"""

    try:
        config = _config_or_local(root)
        items = _discover_items(root, config)
    except RecordsError:
        return {}
    counts: dict[str, int] = {}
    for item in items:
        kind = str(item.get("kind") or "")
        counts[kind] = counts.get(kind, 0) + 1
    return counts


def _full_source_inventory(root: Path, recorded: dict | None,
                           fallback_items: list | None = None) -> dict[str, int]:
    """全量来源基数:登记数与当前实况逐类取大,准备期新增来源不得漏算。

    计划/状态里登记的清单可能落后于实况(准备之后又新增了决策、成果、
    任务等);只信旧清单会把未转换的新来源当成已覆盖,进而放行全局
    切换。实况多于登记按实况计;登记多于实况(准备后来源被删)按登记
    计,由来源指纹核对另行暴露。旧清单为空时退回条目自数。
    """

    counts = {str(kind): int(number)
              for kind, number in (recorded or {}).items()}
    if not counts:
        for item in fallback_items or []:
            kind = str(item.get("kind") or "")
            counts[kind] = counts.get(kind, 0) + 1
    for kind, number in _count_source_items(root).items():
        counts[kind] = max(counts.get(kind, 0), number)
    return counts


def _row_unverified(root: Path, staging: Path, row: dict) -> str:
    """逐行核实映射产物仍在原位且字节未变;无指纹的行按未核实处理。"""

    new = str(row.get("new") or "")
    old = str(row.get("old") or "")
    if not new:
        return str(row.get("identity") or old or "未知")
    if row.get("kind") == "evidence":
        if row.get("reachable") is False:
            return ""
        target = (root / old).resolve() if old else None
        if target is None or not target.is_file():
            return old or new
    else:
        target = (staging / new).resolve()
        if (not target.is_file()
                or not target.is_relative_to(staging.resolve())):
            return new
    digest = row.get("sha256")
    if not digest:
        return f"{new}(缺少内容指纹)"
    if _sha_file(target) != digest:
        return f"{new}(内容已变化)"
    return ""


def _incomplete_reason(root: Path, status: dict) -> list[str]:
    missing: list[str] = []
    staging = Path(status.get("pending_root") or _pending_root(root))
    if not (staging / DEFAULT_CONFIG_REL).is_file():
        missing.append("缺少待切换配置")
        return missing
    try:
        converted = read_current_design(staging)
    except (RecordsError, OSError) as exc:
        missing.append(f"新资料不可读取:{exc}")
        return missing
    overall = converted.get("overall") or ""
    if "规格身份:overall" not in overall:
        missing.append("新规格缺少可核对身份,不能只附旧链接")
    if "当前规则" not in overall and "核心玩法" not in overall:
        missing.append("新规格缺少完整设计正文")
    history = converted.get("history") or ""
    mapping = status.get("correspondence") or {}
    # 对应关系按来源盘点比较:来源里本就没有的类别(如只有开放任务、
    # 尚无结果与证据的新项目)不作为缺口,否则切换闸门永远打不开。
    # 盘点始终重扫实况并与登记取大;登记非空不再豁免重扫。
    inventory = _full_source_inventory(root, status.get("source_inventory"))
    labels = {"specs": "规格", "decisions": "决定", "tasks": "任务",
              "results": "结果", "evidence": "证据"}
    for group, label in labels.items():
        rows = mapping.get(group) or []
        expected = inventory.get(_KIND_SOURCE[group], 0)
        if len(rows) < expected:
            # 受限范围只转换了部分来源:数量不足时不得按完整宣告,
            # 否则 apply_safe_switch 会在未转换记录上切换全局权威。
            missing.append(
                f"缺少{label}对应关系(已转换 {len(rows)}/共 {expected})")
            continue
        for row in rows:
            reason = _row_unverified(root, staging, row)
            if reason:
                missing.append(f"{label}映射未核实:{reason}")
    # 准备期新增来源逐项发现:迁移准备之后新出现的源记录若不在对应
    # 关系里,数量取大可能仍数不出来(如新增一条决定同时删了一条),
    # 必须按来源身份逐个比对。config/gate-history/recovery 属于侧车
    # 与留档材料,不进入五类对应关系,不在此核对。
    try:
        live_items = _discover_items(
            root, _config_or_local(root))
    except RecordsError:
        live_items = []
    covered_sources: set[str] = set()
    covered_identities: set[str] = set()
    for rows in mapping.values():
        if not isinstance(rows, list):
            continue
        for row in rows:
            old = str(row.get("old") or "")
            if old:
                covered_sources.add(old)
            ident = str(row.get("identity") or "")
            if ident:
                covered_identities.add(ident)
    mapped_kinds = set(_KIND_SOURCE.values())
    for item in live_items:
        if str(item.get("kind") or "") not in mapped_kinds:
            continue
        if item.get("kind") == "task":
            ident = str(item.get("identity") or "")
            if ident and ident not in covered_identities:
                missing.append(f"准备期间新增任务未转换:{ident}")
            continue
        src = str(item.get("source") or "")
        if src and src not in covered_sources:
            missing.append(
                f"准备期间新增{item.get('kind') or '来源'}未转换:{src}")
    if not converted.get("modules"):
        missing.append("缺少可读取模块")
    return missing


def read_local_material_migration(project_root: Path | str) -> dict:
    """回读待切换迁移成果。只创建任务或附旧链接不能算完整。"""

    root = Path(project_root)
    status = _load_status(root)
    staging = Path(status.get("pending_root") or _pending_root(root))
    if not status and not (staging / DEFAULT_CONFIG_REL).is_file():
        return {
            "wrote": False,
            "complete": False,
            "status": "absent",
            "tracker": "local-markdown",
            "missing": ["没有待切换的完整资料转换"],
            "correspondence": {},
            "gate_required": False,
            "gate_as_permission": False,
        }
    if not status:
        status = {
            "status": "pending-switch",
            "pending_root": str(staging),
            "correspondence": {},
            "paused": [],
            "missing_evidence": [],
            "gate_as_permission": False,
        }
    missing = _incomplete_reason(root, status)
    gate_text = _read(staging / GATE_HISTORY_REL)
    recovery = ""
    if "待恢复" in gate_text or "unknown" in gate_text:
        recovery = gate_text
    complete = (
        not missing
        and not status.get("paused")
        and status.get("status") == "pending-switch"
    )
    return {
        "wrote": False,
        "complete": complete,
        "status": status.get("status") or "pending-switch",
        "tracker": "local-markdown",
        "pending_root": str(staging),
        "correspondence": status.get("correspondence") or {},
        "paused": status.get("paused") or [],
        "missing": missing,
        "missing_evidence": status.get("missing_evidence") or [],
        "gate_history": gate_text,
        "recovery_archive": recovery or status.get("recovery_archive") or "",
        "gate_required": False,
        "gate_as_permission": False,
        "current_source_unchanged": True,
    }

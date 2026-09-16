#!/usr/bin/env python3
"""GitHub 旧项目完整资料迁移(issue #58)。

把获准范围内的规格、决定、任务、结果和证据索引转换成可核对的新版
GitHub 成果,并恢复原生父子与阻塞关系。旧原件与旧 Issue 保留;转换
成果处于待切换,不切换现行指针。普通路径不经 mgs-gate。本地 Markdown
旧项目不在本入口(见 plan_local_material_migration)。

公开 interface(经 mgs_records 再导出):
  plan_github_material_migration(project_root, ...) -> dict
  apply_github_material_migration(project_root, plan, *, confirmed) -> dict
  read_github_material_migration(project_root, ...) -> dict
"""

from __future__ import annotations

import hashlib
import json
import re
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))

from mgs_backend_options import (BackendOptions, backend_options,
                                 github_backend_for)  # noqa: E402
from mgs_github_issue import (  # noqa: E402
    PENDING_SWITCH_MARK, authorization_for, build_task_body, is_pending_switch,
    parse_issue_payload)
from mgs_github_transport import TransportError, repo_path, request_2xx  # noqa: E402
from mgs_migration_common import (  # noqa: E402
    GATE_HISTORY_REL, IDENTITY_NAME,
    _convert_gate, _field, _load_status, _pending_root, _read, _rel,
    _save_status, _section, _sha_file, _title, _write, ensure_spec_mark)
from mgs_record_model import IDENTITY_RE, RecordsError, parse_task_body, today  # noqa: E402
from mgs_record_model import _parse_dep_ids  # noqa: E402
from mgs_record_source import DEFAULT_CONFIG_REL, WRITE_OP, load_config  # noqa: E402
from mgs_snapshot import (  # noqa: E402
    SNAPSHOT_HEADING, SNAPSHOT_MARK, _wrap_markdown_fence, design_ids_for_history)
from mgs_spec import DISCUSSION_MARK, SPEC_MARK, _is_archive_snapshot  # noqa: E402

LOCAL_HINT = "本地 Markdown 旧项目完整资料迁移不在本入口,见 plan_local_material_migration"


def _sha_text(text: str) -> str:
    return hashlib.sha256((text or "").encode("utf-8")).hexdigest()


def _github_backend(config: dict, options: BackendOptions):
    return github_backend_for(config, options)


def _config_or_github(root: Path) -> dict:
    config_path = root / DEFAULT_CONFIG_REL
    if not config_path.is_file():
        raise RecordsError("缺少协作配置,无法盘点 GitHub 旧项目")
    config = load_config(root)
    if config.get("backend") != "github-issues":
        raise RecordsError(LOCAL_HINT)
    config = dict(config)
    config["project_root"] = str(root)
    return config


def _list_issues(backend) -> list[dict]:
    items: list[dict] = []
    page = 1
    while True:
        status, data = backend.transport.request(
            "GET",
            f"{repo_path(backend.repo)}/issues?state=all&per_page=100&page={page}")
        if status != 200 or not isinstance(data, list):
            raise TransportError("bad_response", f"list issues HTTP {status}")
        items.extend(item for item in data if "pull_request" not in item)
        if len(data) < 100:
            break
        page += 1
    return items


def _list_comments(backend, number: int) -> list[dict]:
    """拉取某 Issue 的全部评论:分页直到返回页短于 100。

    只取第一页会漏掉后续结果/决策评论,盘点完整性就建立在被截断的
    清单上;与 _list_issues 同一分页口径。任一页失败按既有契约返回 []。
    """

    items: list[dict] = []
    page = 1
    while True:
        status, data = backend.transport.request(
            "GET",
            f"{repo_path(backend.repo)}/issues/{number}/comments"
            f"?per_page=100&page={page}")
        if status != 200 or not isinstance(data, list):
            return []
        items.extend(data)
        if len(data) < 100:
            break
        page += 1
    return items


def _issue_source(number: int) -> str:
    return f"github:issue:{number}"


def _discover_github_items(backend, config: dict) -> list[dict[str, Any]]:
    items: list[dict[str, Any]] = []
    labels = config.get("labels") or {}
    number_to_identity: dict[int, str] = {}
    task_rows: list[dict[str, Any]] = []
    for raw in _list_issues(backend):
        body = raw.get("body") or ""
        if is_pending_switch(body):
            continue
        if DISCUSSION_MARK in body \
                and SPEC_MARK not in body and SNAPSHOT_MARK not in body:
            # 设计讨论不是正式规格:按讨论/历史记录盘点,保持非权威地位。
            # 归入规格会让无规格身份的讨论变成任意模块并被盖上正式
            # 规格章,试验值因此暴露为现行模块规格;讨论原件由旧 Issue
            # 只读历史保留,不进入转换成果。
            match = re.search(r"讨论身份\s*[:：]\s*([A-Za-z0-9_.-]+)", body)
            identity = match.group(1) if match else f"issue-{raw.get('number')}"
            items.append({
                "kind": "discussion",
                "role": "historical",
                "identity": identity,
                "source": _issue_source(raw.get("number")),
                "issue_number": raw.get("number"),
                "title": raw.get("title") or "设计讨论",
                "fingerprint": _sha_text(body),
            })
            continue
        if SPEC_MARK in body or SNAPSHOT_MARK in body:
            identity = ""
            if _is_archive_snapshot(body):
                match = re.search(r"快照身份\s*[:：]\s*([A-Za-z0-9_-]+)", body)
                identity = match.group(1) if match else f"issue-{raw.get('number')}"
                role = "historical"
            else:
                match = re.search(r"规格身份\s*[:：]\s*([A-Za-z0-9_-]+)", body)
                if match:
                    identity = match.group(1)
                role = "current" if identity == "overall" else "module"
                if not identity:
                    identity = f"issue-{raw.get('number')}"
            if raw.get("number") is not None:
                number_to_identity[int(raw["number"])] = identity
            items.append({
                "kind": "spec",
                "role": role,
                "identity": identity or f"issue-{raw.get('number')}",
                "source": _issue_source(raw.get("number")),
                "issue_number": raw.get("number"),
                "title": raw.get("title") or identity,
                "fingerprint": _sha_text(body),
            })
            # 现行/模块规格把已采纳决定与变更历史存在评论里;评论只存于
            # GitHub,不进盘点就会在类别级完整性检查下静默丢失。
            if role in {"current", "module"} and raw.get("number") is not None:
                for comment in _list_comments(backend, int(raw["number"])):
                    text = comment.get("body") or ""
                    if not text.strip():
                        continue
                    ident = _field(text, "身份")
                    if not ident or any(c.isspace() for c in ident):
                        ident = f"comment-{comment.get('id')}"
                    items.append({
                        "kind": "decision",
                        "identity": ident,
                        "status": _field(text, "状态") or "未验证",
                        "source": f"github:comment:{comment.get('id')}",
                        "issue_number": raw.get("number"),
                        "comment_id": comment.get("id"),
                        "title": (text.strip().splitlines() or ["决定"])[0][:80],
                        "fingerprint": _sha_text(text),
                    })
            continue
        parsed = parse_issue_payload(raw, labels)
        identity = parsed.get("identity") or ""
        if not identity:
            continue
        request = parsed.get("request") or {}
        parent_meta = raw.get("parent") if isinstance(raw.get("parent"), dict) else {}
        task_rows.append({
            "kind": "task",
            "identity": identity,
            "source": _issue_source(parsed.get("issue_number")),
            "issue_number": parsed.get("issue_number"),
            "issue_id": parsed.get("issue_id"),
            "title": parsed.get("title") or identity,
            "parent": request.get("父任务") or "",
            "deps": request.get("依赖") or "",
            "progress": parsed.get("progress") or "",
            "triage": parsed.get("triage") or "",
            "state": parsed.get("state") or "open",
            "state_reason": parsed.get("state_reason"),
            "assignees": list(parsed.get("assignees") or []),
            "fingerprint": _sha_text(body),
            # 原生接口才有的父子关系先记编号;身份统一解析后移除临时键。
            "_native_parent_no": parent_meta.get("number"),
        })
        if parsed.get("issue_number") is not None:
            number_to_identity[int(parsed["issue_number"])] = identity
        for comment in _list_comments(backend, parsed.get("issue_number")):
            text = comment.get("body") or ""
            items.append({
                "kind": "result",
                "identity": identity,
                "source": f"github:comment:{comment.get('id')}",
                "issue_number": parsed.get("issue_number"),
                "comment_id": comment.get("id"),
                "title": (text.strip().splitlines() or ["结果"])[0][:80],
                "fingerprint": _sha_text(text),
            })
    # 第二遍:正文约定之外,盘点仅存于原生接口的父子/阻塞关系,
    # 迁移恢复阶段才不会丢失真实的先后约束。
    for row in task_rows:
        native_parent_no = row.pop("_native_parent_no", None)
        body_parent = str(row.get("parent") or "").strip()
        if (not body_parent or body_parent == "无") \
                and native_parent_no in number_to_identity:
            row["parent"] = f"#{native_parent_no} {number_to_identity[native_parent_no]}"
        number = row.get("issue_number")
        native_dep_nos: list[int] = []
        if number is not None:
            try:
                status, blockers = backend.transport.request(
                    "GET",
                    f"{repo_path(backend.repo)}/issues/{number}"
                    "/dependencies/blocked_by")
            except TransportError:
                blockers = None
                status = None
            if status == 200 and isinstance(blockers, list):
                for blocker in blockers:
                    blocker_no = (blocker or {}).get("number") \
                        if isinstance(blocker, dict) else None
                    if blocker_no in number_to_identity:
                        native_dep_nos.append(int(blocker_no))
        if native_dep_nos:
            known = _parse_dep_ids(str(row.get("deps") or ""))
            tokens = [token for token in str(row.get("deps") or "").split("、")
                      if token.strip() and token.strip() != "无"]
            for dep_no in native_dep_nos:
                dep_id = number_to_identity.get(dep_no)
                if dep_id in known:
                    continue
                known.append(dep_id)
                tokens.append(f"#{dep_no} {dep_id}")
            row["deps"] = "、".join(tokens)
    items.extend(task_rows)
    return items


def _discover_local_items(root: Path) -> list[dict[str, Any]]:
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
    evidence_dir = root / "docs/mygamestudio/evidence"
    if evidence_dir.is_dir():
        for path in sorted(p for p in evidence_dir.iterdir() if p.is_file()):
            items.append({
                "kind": "evidence",
                "identity": "",
                "source": _rel(root, path),
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
        if source in fingerprints:
            continue
        if item.get("fingerprint"):
            fingerprints[source] = str(item["fingerprint"])
            continue
        path = root / source
        if source and path.is_file():
            fingerprints[source] = _sha_file(path)
    return fingerprints


def plan_github_material_migration(project_root: Path | str, *,
                                   scope: dict | None = None,
                                   transport=None, api_base: str | None = None,
                                   cache_dir: Path | str | None = None) -> dict:
    """只读整理获准范围内的完整资料转换清单。不写入,不切换现行来源。"""

    root = Path(project_root)
    if not root.is_dir():
        raise RecordsError(f"目标项目不存在:{root}")
    config = _config_or_github(root)
    backend = _github_backend(
        config, backend_options(transport=transport, api_base=api_base, cache_dir=cache_dir))
    items = _discover_github_items(backend, config) + _discover_local_items(root)
    if scope:
        allowed = set(scope.get("sources") or [])
        if allowed:
            items = [item for item in items if item.get("source") in allowed]
    fingerprints = _fingerprints(root, items)
    return {
        "wrote": False,
        "tracker": "github-issues",
        "backend": "github-issues",
        "status": "planned",
        "gate_required": False,
        "project_root": str(root),
        "pending_root": str(_pending_root(root)),
        "repo": config.get("task_root"),
        "items": items,
        "source_fingerprints": fingerprints,
        "retention": [
            "旧原件与旧 Issue 全部保留,不删除、不改写现行指针",
            "转换成果处于待切换,旧 GitHub 资料仍为现行来源",
            "gate 历史留存且不作为新版权限",
        ],
    }


def _with_pending(body: str) -> str:
    if PENDING_SWITCH_MARK in (body or ""):
        return body if body.endswith("\n") else body + "\n"
    lines = (body or "").splitlines()
    if lines and lines[0].startswith("# "):
        return "\n".join([lines[0], "", PENDING_SWITCH_MARK] + lines[1:]) + "\n"
    return PENDING_SWITCH_MARK + "\n\n" + (body or "")


def _ensure_spec_mark(body: str, identity: str, version: str, kind: str) -> str:
    # 共享补章(见 mgs_migration_common.ensure_spec_mark)之外,GitHub 迁移
    # 的规格正文还要加盖 pending-switch 章,待切换章由 _with_pending 统一补。
    return _with_pending(ensure_spec_mark(body, identity, version, kind))


def _parent_identity(value: str) -> str:
    found = IDENTITY_RE.findall(value or "")
    return found[0] if found else ""


def _find_pending_issue(backend, needle: str) -> dict | None:
    # 身份针必须匹配到完整取值:needle 之后只能是句号、换行或结尾。
    # 纯子串匹配会把前缀身份误判成同身份(如 快照身份:ds-v1 命中
    # 快照身份:ds-v1-0-0),收养再加正文比对就会覆盖别人的快照。
    pattern = re.compile(re.escape(needle) + r"(?![^\n。])")
    for item in _list_issues(backend):
        body = item.get("body") or ""
        if not is_pending_switch(body) or not pattern.search(body):
            continue
        if needle.startswith(SPEC_MARK) and SNAPSHOT_MARK in body:
            continue
        return item
    return None


def _issue_logins(issue: dict | None) -> set[str]:
    found: set[str] = set()
    for entry in (issue or {}).get("assignees") or []:
        login = str(entry.get("login") if isinstance(entry, dict) else entry).strip()
        if login:
            found.add(login)
    return found


def _publish_issue(backend, *, title: str, body: str, needle: str,
                   labels: list[str] | None = None,
                   assignees: list[str] | None = None) -> tuple[dict | None, bool]:
    existing = _find_pending_issue(backend, needle)
    if existing is not None:
        issue = existing
        adopted = True
        # 同身份旧 pending 不得未比对正文即收养:正文须与本次规划源
        # 比对,不一致则更新目标正文,否则规划源更新会在重试时被旧
        # 正文静默丢弃。更新后回读核实;核实不了按未落地处理(返回
        # None 让该项进入重试),不得假装已采用新内容。
        if (issue.get("body") or "") != body:
            try:
                status, patched = backend.transport.request(
                    "PATCH",
                    f"{repo_path(backend.repo)}/issues/{issue['number']}",
                    {"title": title, "body": body})
                updated = (status in (200, 201) and isinstance(patched, dict)
                           and (patched.get("body") or "") == body)
                if not updated:
                    _status, reread = backend.transport.request(
                        "GET",
                        f"{repo_path(backend.repo)}/issues/{issue['number']}")
                    updated = (isinstance(reread, dict)
                               and (reread.get("body") or "") == body)
                    patched = reread if updated else None
                if not updated:
                    return None, False
                issue = patched
            except TransportError:
                return None, False
    else:
        payload: dict[str, Any] = {"title": title, "body": body}
        if labels:
            payload["labels"] = labels
        if assignees:
            payload["assignees"] = assignees
        try:
            status, issue = backend.transport.request(
                "POST", f"{repo_path(backend.repo)}/issues", payload)
            if status not in (200, 201) or not isinstance(issue, dict):
                raise TransportError("bad_response", f"create HTTP {status}")
            adopted = False
        except TransportError:
            try:
                landed = _find_pending_issue(backend, needle)
            except TransportError:
                landed = None
            if landed is None:
                return None, False
            issue = landed
            adopted = True
    wanted = [str(login) for login in (assignees or []) if login]
    if issue and wanted:
        try:
            status, patched = backend.transport.request(
                "PATCH",
                f"{repo_path(backend.repo)}/issues/{issue['number']}",
                {"assignees": wanted})
            if status in (200, 201) and isinstance(patched, dict):
                issue = patched
            else:
                _status, reread = backend.transport.request(
                    "GET",
                    f"{repo_path(backend.repo)}/issues/{issue['number']}")
                if isinstance(reread, dict):
                    issue = reread
        except TransportError:
            try:
                _status, reread = backend.transport.request(
                    "GET",
                    f"{repo_path(backend.repo)}/issues/{issue['number']}")
                if isinstance(reread, dict):
                    issue = reread
            except TransportError:
                issue = None
        if _issue_logins(issue) < set(wanted):
            if issue and not adopted:
                try:
                    backend.transport.request(
                        "PATCH",
                        f"{repo_path(backend.repo)}/issues/{issue['number']}",
                        {"state": "closed", "state_reason": "not_planned"})
                except TransportError:
                    pass
            return None, False
    return issue, adopted


def _publish_comment(backend, number: int, needle: str,
                     text: str) -> tuple[dict | None, bool]:
    for comment in _list_comments(backend, number):
        if needle in (comment.get("body") or ""):
            return comment, True
    try:
        status, comment = backend.transport.request(
            "POST", f"{repo_path(backend.repo)}/issues/{number}/comments",
            {"body": text})
        if status not in (200, 201) or not isinstance(comment, dict):
            raise TransportError("bad_response", f"comment HTTP {status}")
        return comment, False
    except TransportError:
        try:
            comments = _list_comments(backend, number)
        except TransportError:
            comments = []
        for comment in comments:
            if needle in (comment.get("body") or ""):
                return comment, True
        return None, False


def _ensure_parent(backend, parent: dict, child: dict) -> bool:
    path = f"{repo_path(backend.repo)}/issues/{parent['number']}/sub_issues"
    child_id = child.get("id")
    try:
        _status, data = backend.transport.request("GET", path)
    except TransportError:
        return False
    existing = {item.get("id") for item in (data or []) if isinstance(item, dict)}
    if child_id in existing:
        return True
    try:
        # 与 _ensure_blocked_by 同理:422 只代表请求已送达,不代表关系
        # 落地;成功与否一律以回读核实为准。
        backend.transport.request("POST", path, {"sub_issue_id": child_id})
    except TransportError:
        pass
    try:
        data = request_2xx(backend.transport, "GET", path)
    except TransportError:
        return False
    if data is None:
        return False
    existing = {item.get("id") for item in data if isinstance(item, dict)}
    return child_id in existing


def _ensure_blocked_by(backend, child: dict, blocker: dict) -> bool:
    path = (f"{repo_path(backend.repo)}/issues/{child['number']}"
            "/dependencies/blocked_by")
    blocker_id = blocker.get("id")
    try:
        _status, data = backend.transport.request("GET", path)
    except TransportError:
        return False
    existing = {item.get("id") for item in (data or []) if isinstance(item, dict)}
    if blocker_id in existing:
        return True
    try:
        # 422 与 2xx 一样只代表「请求已送达」:服务端可能以 422 拒绝
        # (无效引用、自阻塞等),不得凭状态码宣告关系成立。
        backend.transport.request("POST", path, {"issue_id": blocker_id})
    except TransportError:
        pass
    # 一律回读核实关系真实存在;非 2xx 读取同样视为未确认。
    try:
        data = request_2xx(backend.transport, "GET", path)
    except TransportError:
        return False
    if data is None:
        return False
    existing = {item.get("id") for item in data if isinstance(item, dict)}
    return blocker_id in existing


def _source_fingerprint(root: Path, item: dict, backend) -> str | None:
    source = str(item.get("source") or "")
    if source.startswith("github:issue:"):
        number = int(source.rsplit(":", 1)[-1])
        try:
            _status, issue = backend.transport.request(
                "GET", f"{repo_path(backend.repo)}/issues/{number}")
        except TransportError:
            return ""
        return _sha_text((issue or {}).get("body") or "")
    if source.startswith("github:comment:"):
        comment_id = int(source.rsplit(":", 1)[-1])
        number = item.get("issue_number")
        if not number:
            return None
        for comment in _list_comments(backend, int(number)):
            if comment.get("id") == comment_id:
                return _sha_text(comment.get("body") or "")
        # 评论被删除或评论读取失败:不可用计划预期指纹替代实测,
        # 否则不可得来源会被当成「未变化」而静默放行。
        return None
    path = root / source
    if source and path.is_file():
        return _sha_file(path)
    return ""


def _changed(root: Path, item: dict, fingerprints: dict[str, str],
             backend) -> bool:
    source = str(item.get("source") or "")
    expected = fingerprints.get(source)
    if not expected:
        return False
    current = _source_fingerprint(root, item, backend)
    if current is None:
        # 源评论不可读(被删或读取失败)按变化处理:暂停该项,
        # 不得把不可得当未变化后静默跳过。
        return True
    if not current:
        return False
    return current != expected


def _render_pending_config(config: dict) -> str:
    repo = config.get("task_root") or ""
    external = str(config.get("external") or "").strip()
    if WRITE_OP not in external and config.get("remote_write_authorized"):
        external = f"{repo}:{WRITE_OP}(GitHub 旧项目资料迁移沿用现行授权)"
    if not external:
        external = "无"
    return f"""# 待切换协作配置

维护责任:制作统筹。配置版本:v1。采用依据:GitHub 旧项目完整资料迁移(待切换)。

## 任务来源

- 后端:github-issues
- 当前位置:{repo}
- 任务读取规则:GitHub Issues 后端约定(Issue 正文承载任务说明,评论承载结果)
- 外部连接引用及已确认操作范围:{external}
- 状态:pending-switch。旧 GitHub 资料仍为项目现行来源;本成果不是现行指针。

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
| 游戏需求与设计 | GitHub 规格 Issue(待切换) | 方案设计 |
| 技术设计 | docs/mygamestudio/TECH_DESIGN.md | 制作实现 |
| 术语、ADR 与历史 | docs/mygamestudio/records/ | 对应专业角色 |
| 成果与证据 | docs/mygamestudio/evidence/ | 对应执行者 |

## 执行条件

- 工程、原型、资源与构建入口:src/
- 可用能力及已验证执行边界:文件读写
- 尚未就绪的能力及影响:无
"""


def _read_item_body(root: Path, backend, item: dict) -> str:
    source = str(item.get("source") or "")
    if source.startswith("github:comment:"):
        comment_id = int(source.rsplit(":", 1)[-1])
        number = item.get("issue_number")
        if not number:
            return ""
        for comment in _list_comments(backend, int(number)):
            if comment.get("id") == comment_id:
                return comment.get("body") or ""
        return ""
    if source.startswith("github:") or item.get("issue_number"):
        number = item.get("issue_number")
        if not number and source.startswith("github:issue:"):
            number = int(source.rsplit(":", 1)[-1])
        if number:
            try:
                _status, raw = backend.transport.request(
                    "GET", f"{repo_path(backend.repo)}/issues/{number}")
            except TransportError:
                return ""
            return (raw or {}).get("body") or ""
        return ""
    return _read(root / source)


def _snapshot_body(item: dict, body: str, *, design_id: str) -> str:
    version = item.get("version") or "v1"
    overall = _ensure_spec_mark(body, "overall", version, "历史规格")
    return "\n".join([
        f"# {SNAPSHOT_HEADING} {design_id} r1",
        "",
        f"{SNAPSHOT_MARK}{design_id}。修订:r1。种类:归档快照。不是现行规格。",
        PENDING_SWITCH_MARK,
        f"游戏版本:{version}",
        f"形成时间:{today()}",
        f"来源:{item.get('source')}",
        "实现:未实现",
        "发布:未发布",
        f"采用关系:本修订记录历史规格 {version},现行规格另见整体入口",
        "",
        "## 整体设计(当时完整内容)",
        "",
        _wrap_markdown_fence(overall),
        "",
    ])


def _history_comment(item: dict, body: str) -> str:
    status = item.get("status") or _field(body, "状态") or "未验证"
    return "\n".join([
        f"## {item.get('title') or item.get('identity')}",
        "",
        f"来源:{item.get('source')}",
        f"身份:{item.get('identity')}",
        f"状态:{status}",
        f"版本:{item.get('version') or ''}",
        "",
        (body or "").strip() or "（原文为空）",
        "",
    ])


def apply_github_material_migration(project_root: Path | str,
                                    plan: dict | None = None, *,
                                    confirmed: bool = False,
                                    transport=None, api_base: str | None = None,
                                    cache_dir: Path | str | None = None) -> dict:
    """把清单转换成待切换 GitHub 成果。未确认不写;回读后只补缺项。"""

    options = backend_options(transport=transport, api_base=api_base, cache_dir=cache_dir)
    if not confirmed:
        return {
            "ok": False, "wrote": False, "reason": "未确认迁移清单,不执行转换",
            "gate_required": False,
        }
    root = Path(project_root)
    config = _config_or_github(root)
    allowed, note = authorization_for(config, WRITE_OP)
    if not allowed:
        return {"ok": False, "wrote": False, "reason": note, "gate_required": False}
    backend = _github_backend(config, options)
    plan = plan or plan_github_material_migration(
        root, transport=options.transport, api_base=options.api_base,
        cache_dir=options.cache_dir)
    if plan.get("backend") not in (None, "github-issues"):
        raise RecordsError(LOCAL_HINT)
    fingerprints = dict(plan.get("source_fingerprints") or {})
    items = list(plan.get("items") or [])
    staging = _pending_root(root)
    staging.mkdir(parents=True, exist_ok=True)
    paused: list[str] = []
    paused_ids: set[str] = set()
    runnable: list[dict] = []
    for item in items:
        if _changed(root, item, fingerprints, backend):
            paused.append(
                f"{item.get('kind')}:{item.get('identity') or item.get('source')}")
            if item.get("kind") in {"task", "result", "evidence"}:
                paused_ids.add(str(item.get("identity") or ""))
            continue
        runnable.append(item)

    _write(staging / DEFAULT_CONFIG_REL, _render_pending_config(config))
    converted: list[dict] = []
    created = 0
    skipped = 0
    missing_evidence: list[str] = []
    native_relations: dict[str, dict] = {}

    specs = [item for item in runnable if item.get("kind") == "spec"]
    historical = [item for item in specs if item.get("role") == "historical"]
    current_specs = [item for item in specs if item.get("role") == "current"]
    module_specs = [item for item in specs if item.get("role") == "module"]
    decisions = [item for item in runnable if item.get("kind") == "decision"]
    tasks = [item for item in runnable if item.get("kind") == "task"]
    results = [item for item in runnable if item.get("kind") == "result"]
    evidence_items = [item for item in runnable if item.get("kind") == "evidence"]
    # 源任务身份碰撞:两个源 Issue 共用同一任务身份时,后一个会按身份
    # 收养前一个刚建的待切换 Issue,两个来源并成一个目标,后一个的
    # 正文被静默丢弃。碰撞身份按冲突暂停,不共享目标。
    task_identities = [str(item.get("identity") or "") for item in tasks]
    duplicate_ids = {
        ident for ident in task_identities
        if ident and task_identities.count(ident) > 1}
    for ident in sorted(duplicate_ids):
        paused.append(f"task:{ident}(源身份碰撞,不共享目标)")
        paused_ids.add(ident)
    tasks = [item for item in tasks
             if str(item.get("identity") or "") not in duplicate_ids]
    results = [item for item in results
               if str(item.get("identity") or "") not in duplicate_ids]

    overall_issue = None
    design_ids = design_ids_for_history(historical)
    if current_specs:
        item = current_specs[0]
        source_body = _read_item_body(root, backend, item)
        version = item.get("version") or _field(source_body, "基线版本") or "v1"
        marked = _ensure_spec_mark(source_body, "overall", version, "现行规格")
        rules = _section(source_body, "当前规则与流程")
        module_body = _ensure_spec_mark(
            f"# 规则与数值\n\n## 当前规则与流程\n\n{rules or '见整体规格。'}\n",
            "rules", version, "模块规格")
        snap_lines = [
            f"游戏版本 {row.get('version') or 'v1'}：设计 "
            f"{design_ids[index]} 修订 r1"
            for index, row in enumerate(historical)
        ]
        if "## 模块" not in marked:
            marked = marked.rstrip() + "\n\n## 模块\n\n- 规则与数值：规格身份 rules\n"
        if snap_lines and SNAPSHOT_HEADING not in marked:
            marked = marked.rstrip() + f"\n\n## {SNAPSHOT_HEADING}\n\n"
            marked += "".join(f"- {line}\n" for line in snap_lines)
        marked = _with_pending(marked)
        overall_issue, adopted = _publish_issue(
            backend, title=item.get("title") or "现行规格", body=marked,
            needle=f"{SPEC_MARK}overall",
            labels=[config["labels"].get("needs-info", "needs-info")])
        if overall_issue:
            converted.append({
                "kind": "spec", "old": item.get("source"),
                "new_issue": overall_issue.get("number"),
                "identity": "overall", "wrote": not adopted,
            })
            created += int(not adopted)
            skipped += int(adopted)
        has_rules = any(
            str(row.get("identity") or "") in {"rules", "规则与数值"}
            for row in module_specs)
        if not has_rules:
            module_issue, adopted = _publish_issue(
                backend, title="规则与数值", body=module_body,
                needle=f"{SPEC_MARK}rules")
            if module_issue:
                converted.append({
                    "kind": "spec", "old": item.get("source"),
                    "new_issue": module_issue.get("number"),
                    "identity": "rules", "wrote": not adopted,
                })
                created += int(not adopted)
                skipped += int(adopted)

    for item in module_specs:
        identity = str(item.get("identity") or "")
        source_body = _read_item_body(root, backend, item)
        version = item.get("version") or _field(source_body, "基线版本") or "v1"
        marked = _ensure_spec_mark(
            source_body, identity or "module", version, "模块规格")
        issue, adopted = _publish_issue(
            backend, title=item.get("title") or identity,
            body=marked, needle=f"{SPEC_MARK}{identity}")
        if issue:
            converted.append({
                "kind": "spec", "old": item.get("source"),
                "new_issue": issue.get("number"),
                "identity": identity, "wrote": not adopted,
            })
            created += int(not adopted)
            skipped += int(adopted)

    for index, item in enumerate(historical):
        body = _read_item_body(root, backend, item)
        version = item.get("version") or _field(body, "基线版本") or "v1"
        design_id = item.get("identity") if str(
            item.get("identity") or "").startswith("ds-") else design_ids[index]
        if _is_archive_snapshot(body):
            snap_body = _with_pending(body)
        else:
            snap_body = _snapshot_body(item, body, design_id=design_id)
        issue, adopted = _publish_issue(
            backend, title=f"{SNAPSHOT_HEADING} {design_id} r1",
            body=snap_body, needle=f"{SNAPSHOT_MARK}{design_id}")
        if issue:
            converted.append({
                "kind": "spec", "old": item.get("source"),
                "new_issue": issue.get("number"),
                "identity": item.get("identity"),
                "version": version, "wrote": not adopted,
            })
            created += int(not adopted)
            skipped += int(adopted)

    if overall_issue and (historical or decisions):
        for item in historical:
            body = _read(root / item["source"])
            row = dict(item, status="已被替代")
            text = _history_comment(row, body)
            needle = f"身份:{item.get('identity')}"
            comment, adopted = _publish_comment(
                backend, overall_issue["number"], needle, text)
            created += int(bool(comment) and not adopted)
            skipped += int(adopted)
        for item in decisions:
            body = _read_item_body(root, backend, item)
            text = _history_comment(item, body)
            # 以来源定位收养:规格评论与本地决定文件可能共用同一身份,
            # 身份针会把后一条并进前一条的评论而丢内容。
            needle = f"来源:{item.get('source')}"
            comment, adopted = _publish_comment(
                backend, overall_issue["number"], needle, text)
            converted.append({
                "kind": "decision", "old": item.get("source"),
                "new_issue": overall_issue.get("number"),
                "identity": item.get("identity"),
                "status": item.get("status"),
                "wrote": bool(comment) and not adopted,
            })
            created += int(bool(comment) and not adopted)
            skipped += int(adopted)

    new_tasks: dict[str, dict] = {}
    labels = config.get("labels") or {}
    for item in tasks:
        identity = str(item.get("identity") or "")
        if identity in paused_ids:
            continue
        number = item.get("issue_number")
        try:
            _status, raw = backend.transport.request(
                "GET", f"{repo_path(backend.repo)}/issues/{number}")
        except TransportError:
            continue
        old_body = (raw or {}).get("body") or ""
        parsed = parse_task_body(old_body)
        request = dict(parsed.get("request") or {})
        index_lines = []
        for line in (parsed.get("result_index_text") or "").splitlines():
            raw_line = line.lstrip("- ").strip()
            if not raw_line or raw_line == "(暂无)":
                continue
            path_part = raw_line.split()[0]
            if path_part.endswith(".md") and "/" in path_part:
                if (root / path_part).is_file():
                    index_lines.append(f"- {path_part}（原件保留,仍可达）")
                else:
                    missing_evidence.append(path_part)
                    index_lines.append(f"- 缺失证据:{path_part}")
            else:
                index_lines.append(f"- {raw_line}")
        index_text = "\n".join(index_lines) if index_lines else "(暂无)"
        change = _section(old_body, "状态变化") or (
            f"{today()} 由 GitHub 旧项目资料迁移转入待切换成果。")
        body = _with_pending(build_task_body(
            parsed.get("title") or item.get("title") or identity,
            identity,
            parsed.get("triage") or item.get("triage") or "needs-triage",
            parsed.get("progress") or item.get("progress") or "待执行",
            request, index=index_text, changes=[change]))
        triage = parsed.get("triage") or item.get("triage") or "needs-triage"
        parsed_issue = parse_issue_payload(raw, labels) if isinstance(raw, dict) else {}
        assignees = [str(login) for login in (
            item.get("assignees") or parsed_issue.get("assignees") or []) if login]
        issue, adopted = _publish_issue(
            backend, title=parsed.get("title") or identity, body=body,
            needle=f"任务身份:{identity}",
            labels=[labels.get(triage, triage)],
            assignees=assignees)
        if not issue:
            continue
        if (item.get("state") or parsed.get("state")) == "closed":
            reason = item.get("state_reason") or "completed"
            # 迁移后的关闭必须回读确认:传输返回非 2xx 不抛错,
            # 未验证关闭状态的新开任务不得记为已转换(否则已完成工作复活)。
            closed_verified = False
            try:
                status, _patched = backend.transport.request(
                    "PATCH",
                    f"{repo_path(backend.repo)}/issues/{issue['number']}",
                    {"state": "closed", "state_reason": reason})
                if status in (200, 201):
                    _st, reread = backend.transport.request(
                        "GET",
                        f"{repo_path(backend.repo)}/issues/{issue['number']}")
                    closed_verified = (reread or {}).get("state") == "closed"
            except TransportError:
                closed_verified = False
            if not closed_verified:
                paused.append(f"task:{identity}(迁移后未确认保持关闭)")
                paused_ids.add(identity)
                continue
        new_tasks[identity] = issue
        converted.append({
            "kind": "task", "old": item.get("source"),
            "old_issue": number, "new_issue": issue.get("number"),
            "identity": identity, "wrote": not adopted,
        })
        created += int(not adopted)
        skipped += int(adopted)

    comment_id_map: dict[str, dict[int, int]] = {}
    for item in results:
        identity = str(item.get("identity") or "")
        if identity in paused_ids or identity not in new_tasks:
            continue
        target = new_tasks[identity]
        comment_id = item.get("comment_id")
        text = ""
        for comment in _list_comments(backend, item.get("issue_number")):
            if comment.get("id") == comment_id:
                text = comment.get("body") or ""
                break
        if not text:
            continue
        needle = f"迁移结果:{identity}:{comment_id}"
        wrapped = f"{needle}\n\n{text}"
        posted, adopted = _publish_comment(
            backend, target["number"], needle, wrapped)
        if posted and comment_id and posted.get("id"):
            # 结果以新评论重发;旧结果索引里的 #issuecomment-<旧id>
            # 引用必须改写指向新评论,否则切换后留下悬空引用。
            comment_id_map.setdefault(identity, {})[int(comment_id)] = \
                int(posted["id"])
        converted.append({
            "kind": "result", "old": item.get("source"),
            "new_issue": target.get("number"),
            "new_comment": (posted or {}).get("id"),
            "needle": needle,
            "fingerprint": _sha_text(wrapped),
            "identity": identity,
            "wrote": bool(posted) and not adopted,
        })
        created += int(bool(posted) and not adopted)
        skipped += int(adopted)

    for identity, issue in new_tasks.items():
        rewrite = comment_id_map.get(identity) or {}
        if not rewrite:
            continue
        try:
            _st, raw_new = backend.transport.request(
                "GET", f"{repo_path(backend.repo)}/issues/{issue['number']}")
            body_text = str((raw_new or {}).get("body") or "")
            new_body = re.sub(
                r"#issuecomment-(\d+)",
                lambda match: f"#issuecomment-"
                              f"{rewrite.get(int(match.group(1)), int(match.group(1)))}",
                body_text)
            if new_body != body_text:
                status, _patched = backend.transport.request(
                    "PATCH",
                    f"{repo_path(backend.repo)}/issues/{issue['number']}",
                    {"body": new_body})
                if status not in (200, 201):
                    raise TransportError("bad_response", f"index HTTP {status}")
                _st2, reread = backend.transport.request(
                    "GET",
                    f"{repo_path(backend.repo)}/issues/{issue['number']}")
                if str((reread or {}).get("body") or "") != new_body:
                    raise TransportError("bad_response", "index 回读不一致")
        except TransportError:
            paused.append(f"task:{identity}(结果索引未改写为新评论引用)")

    intended_relations: dict[str, dict] = {}
    for identity, issue in new_tasks.items():
        source = next((item for item in tasks if item.get("identity") == identity),
                      {})
        parent_id = _parent_identity(str(source.get("parent") or ""))
        deps = _parse_dep_ids(str(source.get("deps") or ""))
        intended: dict[str, Any] = {"parent_identity": "", "blocked_by": []}
        if parent_id and parent_id in new_tasks:
            intended["parent_identity"] = parent_id
        for dep in deps:
            if dep in new_tasks:
                intended["blocked_by"].append(dep)
        intended_relations[identity] = intended
        rel = {"parent_identity": "", "blocked_by": []}
        if intended["parent_identity"]:
            if _ensure_parent(backend, new_tasks[parent_id], issue):
                rel["parent_identity"] = parent_id
            else:
                # 原生关系未确认时按冲突暂停该项:迁移记录与回读都不得
                # 把缺失的父子/依赖顺序当作已落地。
                paused.append(
                    f"task:{identity}(父关系 {parent_id} 原生落地未确认)")
        for dep in intended["blocked_by"]:
            if _ensure_blocked_by(backend, issue, new_tasks[dep]):
                rel["blocked_by"].append(dep)
            else:
                paused.append(
                    f"task:{identity}(依赖 {dep} 原生落地未确认)")
        native_relations[identity] = rel

    for item in evidence_items:
        source = str(item.get("source") or "")
        reachable = (root / source).is_file() if not source.startswith("github:") else True
        if not reachable:
            missing_evidence.append(source)
        converted.append({
            "kind": "evidence", "old": source, "new": source,
            "identity": item.get("identity"), "reachable": reachable,
            "wrote": False,
        })

    gate_row = _convert_gate(root, staging)
    converted.append(gate_row)
    created += int(gate_row["wrote"])
    skipped += int(not gate_row["wrote"])

    mapping = {
        "specs": [row for row in converted if row.get("kind") == "spec"],
        "decisions": [row for row in converted if row.get("kind") == "decision"],
        "tasks": [row for row in converted if row.get("kind") == "task"],
        "results": [row for row in converted if row.get("kind") == "result"],
        "evidence": [row for row in converted if row.get("kind") == "evidence"],
    }
    _write(staging / IDENTITY_NAME,
           json.dumps(mapping, ensure_ascii=False, indent=2))
    status = "pending-switch"
    if paused and not mapping["specs"] and not mapping["tasks"]:
        status = "partial"
    payload = {
        "status": status,
        "tracker": "github-issues",
        "pending_root": str(staging),
        "correspondence": mapping,
        "native_relations": native_relations,
        "intended_relations": intended_relations,
        "paused": paused,
        "missing_evidence": sorted(set(missing_evidence)),
        "gate_history": GATE_HISTORY_REL,
        "recovery_archive": gate_row.get("text") or "",
        "gate_as_permission": False,
        "gate_required": False,
        "overall_issue": (overall_issue or {}).get("number"),
    }
    _save_status(root, payload)
    filled_gap_only = skipped > 0
    return {
        "ok": True,
        "wrote": created > 0 or staging.is_dir(),
        "status": status,
        "tracker": "github-issues",
        "backend": "github-issues",
        "pending_root": str(staging),
        "created": created,
        "paused": paused,
        "missing_evidence": payload["missing_evidence"],
        "filled_gap_only": filled_gap_only,
        "duplicate_avoided": skipped > 0,
        "gate_required": False,
        "gate_as_permission": False,
        "correspondence": mapping,
        "native_relations": native_relations,
        "intended_relations": intended_relations,
    }


def _incomplete_reason(root: Path, status: dict, backend) -> list[str]:
    missing: list[str] = []
    staging = Path(status.get("pending_root") or _pending_root(root))
    if not (staging / DEFAULT_CONFIG_REL).is_file():
        missing.append("缺少待切换配置")
        return missing
    mapping = status.get("correspondence") or {}
    if not mapping.get("specs"):
        missing.append("缺少规格对应关系")
    if not mapping.get("decisions"):
        missing.append("缺少决定对应关系")
    if not mapping.get("tasks"):
        missing.append("缺少任务对应关系")
    if not mapping.get("results"):
        missing.append("缺少结果对应关系")
    if not mapping.get("evidence"):
        missing.append("缺少证据对应关系")
    overall_no = status.get("overall_issue")
    overall = ""
    if overall_no:
        try:
            _status, issue = backend.transport.request(
                "GET", f"{repo_path(backend.repo)}/issues/{overall_no}")
            overall = (issue or {}).get("body") or ""
        except TransportError as exc:
            missing.append(f"新规格不可读取:{exc}")
            return missing
    if f"{SPEC_MARK}overall" not in overall:
        missing.append("新规格缺少可核对身份,不能只附旧链接")
    if "当前规则" not in overall and "核心玩法" not in overall and "玩家体验" not in overall:
        missing.append("新规格缺少完整设计正文")
    return missing


def read_github_material_migration(project_root: Path | str, *,
                                   transport=None, api_base: str | None = None,
                                   cache_dir: Path | str | None = None) -> dict:
    """回读待切换迁移成果。只创建任务或附旧链接不能算完整。"""

    root = Path(project_root)
    status = _load_status(root)
    staging = Path(status.get("pending_root") or _pending_root(root))
    if not status and not (staging / DEFAULT_CONFIG_REL).is_file():
        return {
            "wrote": False,
            "complete": False,
            "status": "absent",
            "tracker": "github-issues",
            "missing": ["没有待切换的完整资料转换"],
            "correspondence": {},
            "gate_required": False,
            "gate_as_permission": False,
            "current_source_unchanged": True,
        }
    try:
        config = _config_or_github(root)
        backend = _github_backend(
            config, backend_options(transport=transport, api_base=api_base, cache_dir=cache_dir))
    except RecordsError:
        backend = None
        config = {}
    if not status:
        status = {
            "status": "pending-switch",
            "pending_root": str(staging),
            "correspondence": {},
            "paused": [],
            "missing_evidence": [],
            "gate_as_permission": False,
        }
    native = dict(status.get("native_relations") or {})
    relation_gaps: list[str] = []
    overall_comments: list[dict] = []
    if backend and status.get("overall_issue"):
        overall_comments = _list_comments(backend, int(status["overall_issue"]))
        mapping = status.get("correspondence") or {}
        for task in mapping.get("tasks") or []:
            identity = str(task.get("identity") or "")
            number = task.get("new_issue")
            if not number:
                continue
            rel = dict(native.get(identity) or {})
            try:
                parent_no = None
                issue = request_2xx(
                    backend.transport, "GET",
                    f"{repo_path(backend.repo)}/issues/{number}")
                if issue is None:
                    native[identity] = rel
                    relation_gaps.append(
                        f"任务 {identity} 原生关系回读未确认(读取非 2xx)")
                    continue
                parent = (issue or {}).get("parent") or {}
                parent_no = parent.get("number")
                if parent_no:
                    for other in mapping.get("tasks") or []:
                        if other.get("new_issue") == parent_no:
                            rel["parent_identity"] = other.get("identity")
                blockers = request_2xx(
                    backend.transport, "GET",
                    f"{repo_path(backend.repo)}/issues/{number}"
                    "/dependencies/blocked_by")
                if blockers is None:
                    native[identity] = rel
                    relation_gaps.append(
                        f"任务 {identity} 依赖关系回读未确认(读取非 2xx)")
                    continue
                blocked = []
                if isinstance(blockers, list):
                    for blocker in blockers:
                        parsed = parse_issue_payload(blocker, config.get("labels") or {})
                        blocked.append(parsed.get("identity") or "")
                rel["blocked_by"] = [item for item in blocked if item]
            except TransportError:
                pass
            native[identity] = rel
    missing = _incomplete_reason(root, status, backend) if backend else [
        "没有待切换的完整资料转换"]
    # 回读时把重建出的原生关系与迁移时登记的意图逐一对照:缺失的
    # 父子/依赖顺序必须成为完整性缺口,不得在全局切换时静默丢失。
    missing.extend(relation_gaps)
    for identity, want in (status.get("intended_relations") or {}).items():
        got = native.get(str(identity)) or {}
        if want.get("parent_identity") and \
                got.get("parent_identity") != want.get("parent_identity"):
            missing.append(
                f"任务 {identity} 的原生父关系未确认:"
                f"{want.get('parent_identity')}")
        for dep in want.get("blocked_by") or []:
            if dep not in (got.get("blocked_by") or []):
                missing.append(f"任务 {identity} 的原生依赖未确认:{dep}")
    # 决定完整性按映射逐条核对历史评论存在,而不是要求至少一条"已采纳":
    # 全部未决/试验/被否决的决定同样是有效的决定历史。
    decision_rows = (status.get("correspondence") or {}).get("decisions") or []
    for row in decision_rows:
        ident = str(row.get("identity") or "")
        if not ident:
            continue
        needle = f"身份:{ident}"
        if not any(needle in (comment.get("body") or "")
                   for comment in overall_comments):
            missing.append(f"决定 {ident} 的历史评论未进入规格评论")
            break
    # 完成判定必须逐条核对结果映射的目标评论:准备后被删或被篡改的
    # 结果不得在只看类别非空的情况下随全局切换放行。
    result_rows = (status.get("correspondence") or {}).get("results") or []
    result_comments: dict[int, list[dict] | None] = {}
    for row in result_rows:
        ident = str(row.get("identity") or "")
        number = row.get("new_issue")
        if not ident or not isinstance(number, int):
            continue
        if number not in result_comments:
            try:
                result_comments[number] = _list_comments(backend, number)
            except TransportError:
                result_comments[number] = None
        comments = result_comments[number]
        if comments is None:
            missing.append(f"结果 {ident} 的迁移评论读取未确认")
            continue
        needle = str(row.get("needle") or f"迁移结果:{ident}:")
        found = next((comment for comment in comments
                      if needle in (comment.get("body") or "")), None)
        if found is None:
            missing.append(f"结果 {ident} 的迁移评论缺失或不可读")
            continue
        want = str(row.get("fingerprint") or "")
        if want and _sha_text(found.get("body") or "") != want:
            missing.append(f"结果 {ident} 的迁移评论内容与登记指纹不符")
    gate_text = _read(staging / GATE_HISTORY_REL)
    recovery = ""
    if "待恢复" in gate_text or "unknown" in gate_text:
        recovery = gate_text
    history = "\n\n".join(
        comment.get("body") or "" for comment in overall_comments)
    complete = (
        not missing
        and not status.get("paused")
        and status.get("status") == "pending-switch"
    )
    return {
        "wrote": False,
        "complete": complete,
        "status": status.get("status") or "pending-switch",
        "tracker": "github-issues",
        "pending_root": str(staging),
        "correspondence": status.get("correspondence") or {},
        "native_relations": native,
        "history": history,
        "paused": status.get("paused") or [],
        "missing": missing,
        "missing_evidence": status.get("missing_evidence") or [],
        "gate_history": gate_text,
        "recovery_archive": recovery or status.get("recovery_archive") or "",
        "gate_required": False,
        "gate_as_permission": False,
        "current_source_unchanged": True,
    }

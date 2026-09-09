#!/usr/bin/env python3
"""MyGameStudio GitHub Issues 任务后端适配器(任务票 17)。

对应设计《工作记录合同》「GitHub Issues 后端」「后端接口」两节与
《协作配置合同》「切换与离线」一节:Issue 身份对应工作项,正文承载当前
任务说明(沿用 work/task.md 的记录格式,使身份、执行、验收与进度语义
与本地 Markdown 后端一致),评论承载结果与证据;五类分流用 CONFIG
映射后的标签,执行责任、验收方式与细粒度进度保存在任务正文,不扩成
一套无关标签。

授权边界(选择 GitHub 不自动授权远端写入):
- 远端写入操作先核对 CONFIG「外部连接引用及已确认操作范围」中**明确到
  host/owner/repository** 的 issues-write 授权;无授权或目标仓库不一致
  时拒绝执行,不做任何远端调用。
- 凭据不进入项目记录:调用方从进程环境取令牌(默认 MGS_GITHUB_TOKEN/
  GH_TOKEN),本模块与 CONFIG 均不保存令牌值。
- 工作实例(会话内)的远端写入经 mgs-gate 的 mgs_remote 受控通道执行
  (角色 ∩ 任务 ∩ 用途 ∩ 授权再放行);本模块的 CLI 写入口供可信调度侧
  与已授权操作者使用,与 mgsrt_admin 同级。

故障语义(超时回读再重试 / 防重复创建 / 离线缓存与草稿):
- 创建超时或结果不确定:先用任务身份回读远端(已落地则收养,不重复
  创建),未落地才重试一次;全部尝试如实上报。
- 远端不可用:读取返回**注明时间与来源**的缓存;写入保存**未发布草稿**
  (标明来源与状态),绝不把草稿报告为已发布,也绝不静默改用本地后端。

本地替身验证说明:传输层可注入(API 端点可经 MGS_GH_API_BASE/--api-base
覆盖),验收用本地 HTTP 替身覆盖故障语义;真实远端写入仅在明确授权的
测试仓库执行(任务票 17 保留待办)。
"""

from __future__ import annotations

import datetime as _dt
import hashlib
import json
import os
import re
import sys
from pathlib import Path
import http.client
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

sys.path.insert(0, str(Path(__file__).resolve().parent))

import mgs_records  # noqa: E402
from mgs_records import (CANONICAL_LABELS, RecordsError,  # noqa: E402
                         _field, _parse_dep_ids, _sections)

GITHUB_BACKEND = "github-issues"
WRITE_OP = "issues-write"
TOKEN_ENVS = ("MGS_GITHUB_TOKEN", "GH_TOKEN")
# 测试接缝:覆盖 API 端点(默认按 host 推导);验收与本地替身使用
API_BASE_ENV = "MGS_GH_API_BASE"
DEFAULT_TIMEOUT = 10.0

OFFLINE_NOTE = ("远端不可用:以下为注明时间与来源的缓存,不是远端当前状态;"
                "不静默切换本地后端。")
DRAFT_NOTE = ("远端不可用:已保存未发布草稿(标明来源与状态);草稿不是已发布任务,"
              "发布需在远端可用后重试;不静默切换本地后端。")
CLOSE_NOTE = "关闭 Issue 不自动等于验证通过;验收以任务记录的验收方式与实际证据为准。"


class GithubRecordsError(RecordsError):
    """GitHub 后端配置缺失、坐标无效、未授权或远端操作失败。"""


class TransportError(Exception):
    """传输层故障。kind: offline(连不上)/ timeout(超时,结果不确定)/
    bad_response(应答不可解析)。"""

    def __init__(self, kind: str, detail: str) -> None:
        super().__init__(f"{kind}: {detail}")
        self.kind = kind
        self.detail = detail


# ---------- 配置解析(公开接缝) ----------

_REPO_RE = re.compile(
    r"^(?:https?://)?([A-Za-z0-9][A-Za-z0-9.-]*\.[A-Za-z]{2,}|localhost)"
    r"(?::\d+)?/([A-Za-z0-9._-]+)/([A-Za-z0-9._-]+?)(?:\.git)?/?$")


def parse_repo_location(value: str) -> dict:
    """解析明确的 GitHub host/owner/repository;含糊位置直接拒绝。

    接受 `host/owner/repo` 与 `https://host/owner/repo`;拒绝缺 host、
    缺段或多段的位置(不扫描、不猜测无关仓库)。
    """

    text = (value or "").strip()
    match = _REPO_RE.fullmatch(text)
    if match is None:
        raise GithubRecordsError(
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


def _authorization_for(config: dict, op: str) -> tuple[bool, str]:
    """核对本项目 CONFIG 是否对目标仓库授权了 op(issues-write)。"""

    scopes = parse_remote_authorizations(config.get("external", ""))
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


def default_api_base(host: str) -> str:
    """host → REST API 端点:github.com 用 api.github.com,
    其他 host(GitHub Enterprise 约定)用 https://<host>/api/v3。"""

    if host == "github.com":
        return "https://api.github.com"
    return f"https://{host}/api/v3"


def api_base_for(config: dict, override: str | None = None) -> str:
    base = (override or os.environ.get(API_BASE_ENV, "")).strip()
    return base or default_api_base(config["repo"]["host"])


def token_from_env() -> str | None:
    for name in TOKEN_ENVS:
        value = os.environ.get(name, "").strip()
        if value:
            return value
    return None


# ---------- 传输层 ----------

class UrllibTransport:
    """真实 HTTP 传输(stdlib urllib)。供可信调度/CLI/替身验收使用。"""

    def __init__(self, api_base: str, token: str | None,
                 timeout: float = DEFAULT_TIMEOUT) -> None:
        self.api_base = api_base.rstrip("/")
        self.token = token
        self.timeout = timeout

    def request(self, method: str, path: str, body: dict | None = None,
                ) -> tuple[int, object]:
        url = f"{self.api_base}{path}"
        data = json.dumps(body).encode("utf-8") if body is not None else None
        headers = {"Accept": "application/vnd.github+json",
                   "X-Requested-With": "mgs-records"}
        if self.token:
            headers["Authorization"] = f"Bearer {self.token}"
        if data is not None:
            headers["Content-Type"] = "application/json"
        req = Request(url, data=data, headers=headers, method=method)
        try:
            with urlopen(req, timeout=self.timeout) as resp:
                raw = resp.read().decode("utf-8", "replace")
                status = resp.status
        except HTTPError as exc:
            raw = exc.read().decode("utf-8", "replace") if exc.fp else ""
            return exc.code, _safe_json(raw)
        except (http.client.RemoteDisconnected, ConnectionResetError,
                BrokenPipeError) as exc:
            # 连接在应答前被断开:请求可能已生效,结果不确定 → 按超时路径
            # 先回读再重试(避免重复创建)
            raise TransportError("timeout", f"connection dropped: {exc}") from exc
        except URLError as exc:
            reason = getattr(exc, "reason", exc)
            if isinstance(reason, TimeoutError) or "timed out" in str(reason).lower():
                raise TransportError("timeout", str(reason)) from exc
            raise TransportError("offline", str(reason)) from exc
        except TimeoutError as exc:
            raise TransportError("timeout", str(exc)) from exc
        return status, _safe_json(raw)


def _safe_json(raw: str) -> object:
    try:
        return json.loads(raw) if raw else None
    except ValueError:
        return raw


# ---------- Issue 正文(与本地 task.md 同一记录格式) ----------

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
    lines += changes or [f"{_today()} 经统一接口建立 GitHub Issues 任务记录。"]
    return "\n".join(lines) + "\n"


def parse_issue_payload(item: dict, label_map: dict) -> dict:
    """GitHub Issue 原始对象 → 任务记录(parse_issue_body 的字典薄包装)。"""

    return parse_issue_body(
        item.get("number", 0), item.get("body") or "",
        [label.get("name", "") for label in item.get("labels", [])],
        item.get("state", "open"), item.get("state_reason"),
        label_map, issue_id=item.get("id"))


def _today() -> str:
    return _dt.date.today().isoformat()


def parse_issue_body(number: int, body: str, labels: list[str],
                     state: str, state_reason: str | None,
                     label_map: dict[str, str], issue_id: int | None = None) -> dict:
    """Issue → 与本地后端同形的任务记录(身份/分流/进度语义一致)。

    标签承载分流(经 CONFIG 映射回五类语义);正文头部是规范化记录,
    两者不一致时以标签为准并把差异列入 triage_source 说明。
    """

    header_lines: list[str] = []
    title = ""
    for line in (body or "").splitlines():
        if line.startswith("## "):
            break
        if line.startswith("# ") and not title:
            title = line.lstrip("# ").strip()
        header_lines.append(line)
    header = "\n".join(header_lines)
    sections = _sections(body or "")
    # 标签 → 五类语义(反向映射)
    reverse = {proj: canon for canon, proj in label_map.items()}
    from_labels = [reverse.get(l, l) for l in labels]
    triage_label = next((t for t in from_labels if t in CANONICAL_LABELS), None)
    triage_body = _field(header, "当前分流")
    triage = triage_label or triage_body or ""
    return {
        "identity": _field(header, "任务身份"),
        "title": title,
        "triage": triage,
        "progress": _field(header, "进度"),
        "issue_number": number,
        "issue_id": issue_id,
        "state": state,
        "state_reason": state_reason,
        "labels": list(labels),
        "triage_source": ("label" if triage_label else
                          "body" if triage_body else "missing"),
        "triage_conflict": bool(triage_label and triage_body
                                and triage_label != triage_body),
        "request": mgs_records._bullets(sections.get("工作请求", [])),
        "sections": {name: bool(lines and any(l.strip() for l in lines))
                     for name, lines in sections.items()},
        "results": [],  # 列表层不拉评论;read_task 单独补齐
        "result_index_text": "\n".join(sections.get("结果索引", [])),
        "body": body or "",
    }


# ---------- 拉取与缓存 ----------

def _repo_path(repo: dict) -> str:
    return f"/repos/{repo['owner']}/{repo['repo']}"


# ---------- Issue 正文编辑(保持与 task.md 同一记录格式) ----------

def _section_lines(body: str, name: str) -> list[str]:
    return list(_sections(body).get(name, []))


def _edit_body(body: str, *, header: dict | None = None,
               request: dict | None = None, index_lines: list[str] | None = None,
               append_change: str | None = None) -> str:
    """按字段编辑任务正文并重新序列化(小节名称与内容保留,格式一致化)。

    header 替换头部行中的「键:值」段;request 替换/追加工作请求字段行;
    index_lines 整体替换结果索引;append_change 向状态变化追加一行。
    """

    sections = _sections(body)
    header_lines: list[str] = []
    title = ""
    for line in body.splitlines():
        if line.startswith("## "):
            break
        if line.startswith("# ") and not title:
            title = line.lstrip("# ").strip()
        header_lines.append(line)
    header_text = next((line for line in header_lines if "任务身份" in line), "")
    for key, value in (header or {}).items():
        pattern = rf"{key}\s*[:：][^。;；]*"
        if re.search(pattern, header_text):
            header_text = re.sub(pattern, f"{key}:{value}", header_text, count=1)
        else:
            header_text = header_text.rstrip("。") + f"。{key}:{value}"
    if request is not None:
        request_lines = sections.get("工作请求", [])
        for key, value in request.items():
            pattern = rf"^-\s+{re.escape(key)}\s*[:：].*$"
            replacement = f"- {key}:{value}"
            if any(re.match(pattern, line) for line in request_lines):
                request_lines = [re.sub(pattern, replacement, line)
                                 for line in request_lines]
            else:
                request_lines.append(replacement)
        sections["工作请求"] = request_lines
    if index_lines is not None:
        sections["结果索引"] = list(index_lines)
    if append_change:
        changes = sections.setdefault("状态变化", [])
        if changes and changes[-1].strip():
            changes.append("")
        changes.append(append_change)
    parts = [f"# {title}", "", header_text, ""]
    for name, lines in sections.items():
        lines = list(lines)
        while lines and not lines[0].strip():
            lines.pop(0)
        while lines and not lines[-1].strip():
            lines.pop()
        parts += [f"## {name}", ""]
        if lines:
            parts += lines + [""]
    return "\n".join(parts).rstrip() + "\n"


class GithubBackend:
    """同一套任务合同在 GitHub Issues 后端上的逻辑操作(公开接缝)。

    读:fetch_tasks/read_task(经传输层;离线回缓存并标注来源与时间)。
    写:create_task/update_task/set_triage/append_result/set_relations/
    set_parent/close_task(先核对 CONFIG 仓库级 issues-write 授权;
    超时先回读防重复;离线存未发布草稿)。
    """

    def __init__(self, config: dict, transport, cache_dir: Path | str | None = None,
                 ) -> None:
        self.config = config
        self.repo = config["repo"]
        self.transport = transport
        self.cache_dir = Path(cache_dir) if cache_dir else None
        self._sub_issues_available: bool | None = None

    # ----- 缓存 -----

    def _cache_file(self) -> Path | None:
        if self.cache_dir is None:
            return None
        slug = f"{self.repo['host']}_{self.repo['owner']}_{self.repo['repo']}"
        return self.cache_dir / f"tasks-{slug}.json"

    def _load_cache(self) -> dict | None:
        path = self._cache_file()
        if path is None or not path.is_file():
            return None
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            return None

    def _write_cache(self, payload: dict) -> None:
        path = self._cache_file()
        if path is None:
            return
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(payload, ensure_ascii=False, indent=2),
                        encoding="utf-8")

    # ----- 读 -----

    def fetch_tasks(self) -> dict:
        """列出任务(身份/标题/分流/进度与本地后端同形;不含评论明细)。

        远端不可用时返回缓存并标注 cached/fetched_at;无缓存时报错,
        不回退到任何本地任务来源。
        """

        try:
            status, data = self.transport.request(
                "GET", f"{_repo_path(self.repo)}/issues?state=all&per_page=100")
            if status != 200 or not isinstance(data, list):
                raise TransportError("bad_response", f"list issues HTTP {status}")
        except TransportError as exc:
            cached = self._load_cache()
            if cached is None:
                raise GithubRecordsError(
                    f"远端不可用({exc})且无缓存:{self.repo['host']}/"
                    f"{self.repo['owner']}/{self.repo['repo']};"
                    "不静默切换本地后端") from exc
            return {"tasks": cached["tasks"], "cached": True,
                    "fetched_at": cached["fetched_at"],
                    "source": cached["source"], "note": OFFLINE_NOTE}
        tasks = [parse_issue_payload(item, self.config["labels"])
                 for item in data if "pull_request" not in item]
        payload = {
            "tasks": tasks,
            "cached": False,
            "fetched_at": _dt.datetime.now().astimezone().isoformat(timespec="seconds"),
            "source": {"backend": GITHUB_BACKEND,
                       "repo": f"{self.repo['host']}/{self.repo['owner']}/{self.repo['repo']}"},
        }
        self._write_cache({"tasks": tasks, "fetched_at": payload["fetched_at"],
                           "source": payload["source"]})
        return payload

    def _get_issue(self, identity: str) -> tuple[dict | None, dict, dict]:
        """按任务身份取 Issue。返回 (原始 Issue 或 None(缓存态), 解析后任务, 拉取载荷)。

        远端不可用时回缓存正文(标注 cached);缓存也没有则由 fetch_tasks 报错。
        """

        payload = self.fetch_tasks()
        cached = bool(payload.get("cached"))
        for task in payload["tasks"]:
            if task["identity"] != identity:
                continue
            if cached:
                return None, task, payload
            status, issue = self.transport.request(
                "GET", f"{_repo_path(self.repo)}/issues/{task['issue_number']}")
            if status != 200:
                raise GithubRecordsError(
                    f"读取 Issue #{task['issue_number']} 失败:HTTP {status}")
            return issue, parse_issue_payload(issue, self.config["labels"]), payload
        raise GithubRecordsError(f"任务不存在或正文缺少身份:{identity}")

    def read_task(self, identity: str) -> dict:
        """读取单个任务:正文字段 + 评论承载的结果与证据。"""

        issue, parsed, payload = self._get_issue(identity)
        results: list[dict] = []
        if issue is not None:
            status, comments = self.transport.request(
                "GET", f"{_repo_path(self.repo)}/issues/{parsed['issue_number']}"
                       "/comments?per_page=100")
            if status == 200 and isinstance(comments, list):
                for comment in comments:
                    text = comment.get("body") or ""
                    if identity in text:
                        results.append({
                            "ref": f"#issuecomment-{comment.get('id')}",
                            "created_at": comment.get("created_at"),
                            "excerpt": (text.strip().splitlines()[0][:120]
                                        if text.strip() else ""),
                        })
            parsed["body_sha256"] = hashlib.sha256(
                (issue.get("body") or "").encode("utf-8")).hexdigest()
            parsed["html_url"] = issue.get("html_url")
        else:
            parsed["body_sha256"] = hashlib.sha256(
                (parsed.get("body") or "").encode("utf-8")).hexdigest()
            parsed["cached_read"] = True
            parsed["cached_note"] = OFFLINE_NOTE
        parsed["results"] = results
        return parsed

    # ----- 写操作(先核对 CONFIG 仓库级 issues-write 授权) -----

    def _authorize_write(self) -> None:
        allowed, note = _authorization_for(self.config, WRITE_OP)
        if not allowed:
            raise GithubRecordsError(note)

    def _save_draft(self, op: str, args: dict, cause: str) -> dict:
        """远端不可用时保存未发布草稿(标明来源与状态;不视为已发布)。"""

        if self.cache_dir is None:
            raise GithubRecordsError(
                f"远端不可用({cause})且未配置缓存/草稿目录(--cache-dir);"
                "不丢弃请求,不静默切换本地后端")
        drafts = self.cache_dir / "drafts"
        drafts.mkdir(parents=True, exist_ok=True)
        stamp = _dt.datetime.now().strftime("%Y%m%d-%H%M%S")
        identity = re.sub(r"[^A-Za-z0-9._-]", "-", str(args.get("identity", "na")))
        path = drafts / f"{stamp}-{op}-{identity}.json"
        path.write_text(json.dumps({
            "op": op, "args": args, "status": "未发布草稿",
            "repo": f"{self.repo['host']}/{self.repo['owner']}/{self.repo['repo']}",
            "created_at": _dt.datetime.now().astimezone().isoformat(timespec="seconds"),
            "cause": cause, "note": DRAFT_NOTE,
        }, ensure_ascii=False, indent=2), encoding="utf-8")
        return {"published": False, "status": "未发布草稿", "draft": str(path),
                "cause": cause, "note": DRAFT_NOTE}

    def _find_by_identity(self, identity: str) -> dict | None:
        """按任务身份回读远端(防重复创建的读路径;不做缓存回退)。

        传输故障原样抛 TransportError,由调用方决定收养/重试/起草稿;
        回读失败时绝不发创建请求(避免重复创建)。
        """

        status, data = self.transport.request(
            "GET", f"{_repo_path(self.repo)}/issues?state=all&per_page=100")
        if status != 200 or not isinstance(data, list):
            raise TransportError("bad_response", f"list issues HTTP {status}")
        for item in data:
            if "pull_request" in item:
                continue
            parsed = parse_issue_payload(item, self.config["labels"])
            if parsed["identity"] == identity:
                return parsed
        return None

    def create_task(self, identity: str, title: str, request: dict, *,
                    triage: str = "needs-triage", progress: str = "待执行") -> dict:
        """创建任务。防重复:先按身份回读,已存在即收养;超时先回读再重试一次。

        attempts 如实记录每次尝试结果;duplicate_avoided 标记「超时后回读
        发现已落地而避免的重复创建」。回读+重试都未落地时报错,不虚报成功;
        读前核对或回读本身失败(离线)时保存未发布草稿,不盲发创建请求。
        """

        self._authorize_write()
        if not identity or not mgs_records.IDENTITY_RE.fullmatch(identity):
            raise GithubRecordsError(
                f"任务身份必须形如 NN-<slug>,当前 {identity!r}(身份跨后端保持稳定)")
        if triage not in CANONICAL_LABELS:
            raise GithubRecordsError(f"分流 {triage!r} 不在五类之内")
        attempts: list[dict] = []
        draft_args = {"identity": identity, "title": title, "request": request,
                      "triage": triage, "progress": progress}
        try:
            existing = self._find_by_identity(identity)
        except TransportError as exc:
            draft = self._save_draft(
                "create_task", draft_args,
                f"读前核对失败({exc});无法确认是否已存在,不发创建请求")
            draft.update({"created": False,
                          "attempts": [{"step": "read-first",
                                        "outcome": exc.kind}]})
            return draft
        if existing is not None:
            attempts.append({"step": "read-first", "outcome": "exists"})
            return {"created": False, "adopted": True, "duplicate_avoided": False,
                    "issue_number": existing["issue_number"], "readback": existing,
                    "attempts": attempts}
        body = build_task_body(title, identity, triage, progress, request)
        payload = {"title": title, "body": body,
                   "labels": [self.config["labels"][triage]]}
        for index in range(2):
            try:
                status, issue = self.transport.request(
                    "POST", f"{_repo_path(self.repo)}/issues", payload)
                if status not in (200, 201):
                    raise TransportError("bad_response", f"create HTTP {status}")
            except TransportError as exc:
                attempts.append({"step": f"create-{index + 1}",
                                 "outcome": exc.kind, "detail": str(exc)})
                if exc.kind == "offline":
                    draft = self._save_draft(
                        "create_task",
                        {"identity": identity, "title": title, "request": request,
                         "triage": triage, "progress": progress}, str(exc))
                    draft.update({"created": False, "attempts": attempts})
                    return draft
                # 超时/坏响应:结果不确定 → 先回读,未落地才重试
                try:
                    landed = self._find_by_identity(identity)
                except TransportError as readback_exc:
                    draft = self._save_draft(
                        "create_task", draft_args,
                        f"超时后回读失败({readback_exc});结果不确定,保存草稿")
                    draft.update({"created": False, "attempts": attempts})
                    return draft
                if landed is not None:
                    attempts.append({"step": "readback", "outcome": "exists"})
                    return {"created": False, "adopted": True,
                            "duplicate_avoided": True,
                            "issue_number": landed["issue_number"],
                            "readback": landed, "attempts": attempts}
                attempts.append({"step": "readback", "outcome": "absent"})
                continue
            readback = parse_issue_payload(issue, self.config["labels"])
            attempts.append({"step": f"create-{index + 1}", "outcome": "created"})
            return {"created": True, "adopted": False, "issue_number":
                    issue.get("number"), "readback": readback,
                    "attempts": attempts}
        raise GithubRecordsError(
            f"创建 {identity} 两次尝试均未确认落地(尝试历史 {attempts});"
            "不虚报成功,请远端可用时重查后再试(先回读避免重复创建)")

    def update_task(self, identity: str, fields: dict, *,
                    expected_body_sha256: str | None = None,
                    change_note: str = "安排更新") -> dict:
        """更新任务安排(进度、工作请求字段)。expected_body_sha256 提供
        远端正文的版本校验:与当前不符即拒绝,不覆盖他人改动。"""

        self._authorize_write()
        try:
            issue, parsed, payload = self._get_issue(identity)
        except TransportError as exc:
            draft = self._save_draft("update_task",
                                     {"identity": identity, "fields": fields,
                                      "expected_body_sha256": expected_body_sha256},
                                     str(exc))
            draft["attempts"] = [{"step": "read", "outcome": exc.kind}]
            return draft
        if issue is None:
            draft = self._save_draft(
                "update_task", {"identity": identity, "fields": fields,
                                "expected_body_sha256": expected_body_sha256},
                "离线缓存态无法核对远端当前正文,不盲写")
            draft["attempts"] = [{"step": "read", "outcome": "cached"}]
            return draft
        current_sha = hashlib.sha256(
            (issue.get("body") or "").encode("utf-8")).hexdigest()
        if expected_body_sha256 is not None \
                and expected_body_sha256.lower() != current_sha:
            raise GithubRecordsError(
                f"远端正文已被他人修改:expected sha256 {expected_body_sha256} "
                f"!= 当前 {current_sha};先回读再提交,不覆盖他人改动")
        header_updates = {key: value for key, value in fields.items()
                          if key in ("进度",)}
        request_updates = {key: value for key, value in fields.items()
                           if key not in ("进度",)}
        change_line = f"{_today()} {change_note}:{'、'.join(fields)}"
        new_body = _edit_body(issue.get("body") or "", header=header_updates,
                              request=request_updates, append_change=change_line)
        try:
            status, updated = self.transport.request(
                "PATCH", f"{_repo_path(self.repo)}/issues/{parsed['issue_number']}",
                {"body": new_body})
            if status != 200:
                raise TransportError("bad_response", f"update HTTP {status}")
        except TransportError as exc:
            draft = self._save_draft("update_task",
                                     {"identity": identity, "fields": fields,
                                      "expected_body_sha256": expected_body_sha256},
                                     str(exc))
            draft["attempts"] = [{"step": "patch", "outcome": exc.kind}]
            return draft
        readback = parse_issue_payload(updated, self.config["labels"])
        return {"published": True, "issue_number": parsed["issue_number"],
                "readback": readback,
                "attempts": [{"step": "patch", "outcome": "updated"}]}

    def set_triage(self, identity: str, label: str) -> dict:
        """设置分流:换成 CONFIG 映射后的标签,并同步正文「当前分流」
        (标签承载分流,正文是规范化记录;两者不一致由 verify 报告)。"""

        self._authorize_write()
        if label not in CANONICAL_LABELS:
            raise GithubRecordsError(f"分流 {label!r} 不在五类之内")
        try:
            issue, parsed, _payload = self._get_issue(identity)
        except TransportError as exc:
            return self._save_draft("set_triage",
                                    {"identity": identity, "label": label}, str(exc))
        if issue is None:
            return self._save_draft("set_triage",
                                    {"identity": identity, "label": label},
                                    "离线缓存态无法改远端标签")
        mapped = self.config["labels"]
        mapped_values = set(mapped.values())
        keep = [l["name"] for l in issue.get("labels", [])
                if l.get("name") not in mapped_values]
        new_labels = sorted(keep + ([mapped[label]] if mapped.get(label) else []))
        new_body = _edit_body(issue.get("body") or "",
                              header={"当前分流": label},
                              append_change=f"{_today()} 分流调整为 {label}")
        try:
            status, updated = self.transport.request(
                "PATCH", f"{_repo_path(self.repo)}/issues/{parsed['issue_number']}",
                {"labels": new_labels, "body": new_body})
            if status != 200:
                raise TransportError("bad_response", f"set labels HTTP {status}")
        except TransportError as exc:
            return self._save_draft("set_triage",
                                    {"identity": identity, "label": label}, str(exc))
        readback = parse_issue_payload(updated, self.config["labels"])
        return {"published": True, "issue_number": parsed["issue_number"],
                "labels": new_labels, "readback": readback}

    def append_result(self, identity: str, result_markdown: str) -> dict:
        """追加结果:发布评论(带任务身份前缀)并把评论登记进正文结果索引。
        评论超时同样先回读(已发布的评论不重复发)。"""

        self._authorize_write()
        try:
            issue, parsed, _payload = self._get_issue(identity)
        except TransportError as exc:
            return self._save_draft("append_result",
                                    {"identity": identity,
                                     "result_markdown": result_markdown}, str(exc))
        if issue is None:
            return self._save_draft("append_result",
                                    {"identity": identity,
                                     "result_markdown": result_markdown},
                                    "离线缓存态无法发布评论")
        number = parsed["issue_number"]
        comment_body = f"任务:{identity}\n\n{result_markdown}"
        comment = None
        attempts: list[dict] = []
        for index in range(2):
            try:
                status, created = self.transport.request(
                    "POST", f"{_repo_path(self.repo)}/issues/{number}/comments",
                    {"body": comment_body})
                if status not in (200, 201):
                    raise TransportError("bad_response", f"comment HTTP {status}")
                comment = created
                attempts.append({"step": f"comment-{index + 1}",
                                 "outcome": "created"})
                break
            except TransportError as exc:
                attempts.append({"step": f"comment-{index + 1}",
                                 "outcome": exc.kind, "detail": str(exc)})
                if exc.kind == "offline":
                    return self._save_draft(
                        "append_result",
                        {"identity": identity, "result_markdown": result_markdown},
                        str(exc))
                # 超时:回读评论,已发布则收养
                try:
                    status, comments = self.transport.request(
                        "GET", f"{_repo_path(self.repo)}/issues/{number}"
                               "/comments?per_page=100")
                    if status == 200 and isinstance(comments, list):
                        hit = next((c for c in comments
                                    if c.get("body") == comment_body), None)
                        if hit is not None:
                            comment = hit
                            attempts.append({"step": "readback", "outcome": "exists"})
                            break
                except TransportError:
                    pass
                attempts.append({"step": "readback", "outcome": "absent"})
        if comment is None:
            raise GithubRecordsError(
                f"结果评论两次尝试均未确认发布(attempts {attempts});不虚报成功")
        ref = f"#issuecomment-{comment.get('id')}"
        excerpt = (comment_body.strip().splitlines()[2][:60]
                   if len(comment_body.strip().splitlines()) > 2 else "结果")
        body = issue.get("body") or ""
        index_lines = [line for line in _section_lines(body, "结果索引")
                       if line.strip() != "(暂无)"]
        index_lines.append(f"- {ref}:{excerpt}")
        new_body = _edit_body(body, index_lines=index_lines,
                              append_change=f"{_today()} 追加结果评论 {ref}")
        status, updated = self.transport.request(
            "PATCH", f"{_repo_path(self.repo)}/issues/{number}", {"body": new_body})
        if status != 200:
            raise GithubRecordsError(f"结果索引更新失败:HTTP {status}(评论已发布 {ref})")
        readback = self.read_task(identity)
        return {"published": True, "comment_id": comment.get("id"),
                "ref": ref, "issue_number": number, "readback": readback,
                "attempts": attempts}

    def set_relations(self, identity: str, deps: list[str]) -> dict:
        """设置依赖(阻塞关系):写成「#Issue号 身份」的明确可解析引用,
        使 deps/ready 与本地后端同语义解析(身份核对,数字仅供人定位)。"""

        self._authorize_write()
        try:
            tasks = self.fetch_tasks()["tasks"]
        except TransportError as exc:
            return self._save_draft("set_relations",
                                    {"identity": identity, "deps": deps}, str(exc))
        except GithubRecordsError:
            raise
        by_id = {task["identity"]: task for task in tasks}
        missing = [dep for dep in deps if dep not in by_id]
        if missing:
            raise GithubRecordsError(
                f"依赖任务不存在:{missing}(引用必须可解析,不写悬空依赖)")
        value = "、".join(f"#{by_id[dep]['issue_number']} {dep}" for dep in deps) \
            or "无"
        return self.update_task(identity, {"依赖": value},
                                change_note="设置依赖")

    def set_parent(self, identity: str, parent_id: str | None) -> dict:
        """设置父子关系:优先原生 sub-issues API;后端不提供时回退为
        工作请求中的明确引用「父任务:#Issue号 身份」。mode 回报实际采用。"""

        self._authorize_write()
        try:
            _issue, parsed, _payload = self._get_issue(identity)
        except TransportError as exc:
            return self._save_draft("set_parent",
                                    {"identity": identity, "parent": parent_id},
                                    str(exc))
        if parent_id is None:
            body_change = {"父任务": "无"}
            result = self.update_task(identity, body_change,
                                      change_note="解除父任务")
            result["mode"] = "body-reference"
            return result
        parent = self._find_by_identity(parent_id)
        if parent is None:
            raise GithubRecordsError(f"父任务不存在:{parent_id}")
        if self._sub_issues_available is None:
            try:
                status, _data = self.transport.request(
                    "GET", f"{_repo_path(self.repo)}/issues/"
                           f"{parent['issue_number']}/sub_issues")
                self._sub_issues_available = status == 200
            except TransportError as exc:
                self._sub_issues_available = False
        if self._sub_issues_available:
            try:
                status, _data = self.transport.request(
                    "POST", f"{_repo_path(self.repo)}/issues/"
                            f"{parent['issue_number']}/sub_issues",
                    {"sub_issue_id": parsed.get("issue_id")
                     or parsed["issue_number"]})
                if status in (200, 201):
                    result = self.update_task(
                        identity,
                        {"父任务": f"#{parent['issue_number']} {parent_id}"
                                   "(原生 sub-issue)"},
                        change_note="设置父任务(原生)")
                    result["mode"] = "native-sub-issues"
                    result["readback"]["body"] = result["readback"].get("body", "")
                    return result
            except TransportError as exc:
                return self._save_draft(
                    "set_parent", {"identity": identity, "parent": parent_id},
                    str(exc))
        result = self.update_task(
            identity,
            {"父任务": f"#{parent['issue_number']} {parent_id}"},
            change_note="设置父任务(正文引用)")
        result["mode"] = "body-reference"
        return result

    def close_task(self, identity: str, reason: str, note: str = "") -> dict:
        """关闭任务。关闭原因限定三类,分别表达:
        完成(state_reason=completed,进度→已完成)、
        不再执行(not_planned,进度→不再执行)、
        已有成果覆盖(completed,进度→已完成(已有成果覆盖))。
        关闭不自动等于验证通过(readback 附说明)。"""

        self._authorize_write()
        mapping = {"完成": ("completed", "已完成"),
                   "不再执行": ("not_planned", "不再执行"),
                   "已有成果覆盖": ("completed", "已完成(已有成果覆盖)")}
        if reason not in mapping:
            raise GithubRecordsError(
                f"关闭原因必须限定三类(完成/不再执行/已有成果覆盖),当前 {reason!r}")
        state_reason, progress = mapping[reason]
        try:
            issue, parsed, _payload = self._get_issue(identity)
        except TransportError as exc:
            return self._save_draft("close_task",
                                    {"identity": identity, "reason": reason,
                                     "note": note}, str(exc))
        if issue is None:
            return self._save_draft("close_task",
                                    {"identity": identity, "reason": reason,
                                     "note": note}, "离线缓存态无法关闭远端任务")
        number = parsed["issue_number"]
        new_body = _edit_body(issue.get("body") or "",
                              header={"进度": progress},
                              append_change=f"{_today()} 关闭({reason})")
        try:
            status, updated = self.transport.request(
                "PATCH", f"{_repo_path(self.repo)}/issues/{number}",
                {"state": "closed", "state_reason": state_reason,
                 "body": new_body})
            if status != 200:
                raise TransportError("bad_response", f"close HTTP {status}")
        except TransportError as exc:
            return self._save_draft("close_task",
                                    {"identity": identity, "reason": reason,
                                     "note": note}, str(exc))
        closing_note = f"关闭原因:{reason}。{note}".rstrip("。")
        self.transport.request(
            "POST", f"{_repo_path(self.repo)}/issues/{number}/comments",
            {"body": f"任务:{identity}\n\n{closing_note}。{CLOSE_NOTE}"})
        readback = parse_issue_payload(updated, self.config["labels"])
        readback["state"] = updated.get("state", readback.get("state"))
        readback["state_reason"] = updated.get("state_reason")
        return {"published": True, "issue_number": number,
                "close_reason": reason, "state_reason": state_reason,
                "readback": readback, "note": CLOSE_NOTE}

    def publish_drafts(self) -> dict:
        """重放未发布草稿(远端恢复后):逐条按原参数执行,成功即标记已发布;
        仍失败保留草稿。草稿在发布前始终标明「未发布」。"""

        if self.cache_dir is None:
            raise GithubRecordsError("未配置缓存/草稿目录(--cache-dir),无草稿可发布")
        drafts_dir = self.cache_dir / "drafts"
        published_dir = drafts_dir / "published"
        results = []
        if not drafts_dir.is_dir():
            return {"published_count": 0, "results": []}
        for path in sorted(drafts_dir.glob("*.json")):
            try:
                draft = json.loads(path.read_text(encoding="utf-8"))
            except (OSError, ValueError) as exc:
                results.append({"draft": str(path), "outcome": "unreadable",
                                "detail": str(exc)})
                continue
            outcome = self._replay_draft(draft)
            results.append({"draft": str(path), **outcome})
            if outcome.get("published"):
                published_dir.mkdir(parents=True, exist_ok=True)
                (published_dir / path.name).write_text(
                    json.dumps(draft, ensure_ascii=False, indent=2), encoding="utf-8")
                path.unlink()
        return {"published_count": sum(1 for r in results if r.get("published")),
                "results": results}

    def _replay_draft(self, draft: dict) -> dict:
        op, args = draft["op"], draft.get("args", {})
        try:
            if op == "create_task":
                outcome = self.create_task(args["identity"], args["title"],
                                           args.get("request", {}),
                                           triage=args.get("triage", "needs-triage"),
                                           progress=args.get("progress", "待执行"))
            elif op == "update_task":
                outcome = self.update_task(args["identity"], args.get("fields", {}),
                                           expected_body_sha256=args.get(
                                               "expected_body_sha256"))
            elif op == "set_triage":
                outcome = self.set_triage(args["identity"], args["label"])
            elif op == "append_result":
                outcome = self.append_result(args["identity"],
                                             args["result_markdown"])
            elif op == "set_relations":
                outcome = self.set_relations(args["identity"], args.get("deps", []))
            elif op == "set_parent":
                outcome = self.set_parent(args["identity"], args.get("parent"))
            elif op == "close_task":
                outcome = self.close_task(args["identity"], args["reason"],
                                          note=args.get("note", ""))
            else:
                return {"published": False, "outcome": f"unknown op {op}"}
        except (GithubRecordsError, TransportError) as exc:
            return {"published": False, "outcome": f"仍失败:{exc}"}
        return {"published": bool(outcome.get("published", outcome.get("created"))),
                "outcome": outcome}

    # ----- 回读核验 -----

    def verify(self, project_root: Path | str) -> dict:
        """github-issues 后端回读核验(与本地后端同一含义的检查集)。

        离线时基于缓存核对结构与依赖,远端存在性检查(标签在仓库实际存在、
        评论一致性)标注「未核对(离线)」,不冒充已核验;整体结果附
        offline 标记。远端不可用且无缓存时报错,不回退本地。
        """

        root = Path(project_root)
        checks: list[dict] = []
        skipped: list[str] = []

        def add(name: str, ok: bool, detail: str) -> None:
            checks.append({"name": name, "ok": bool(ok), "detail": detail})

        add("config-present", True,
            str(root / self.config["config_path"]))
        repo = self.repo
        add("backend-github-coordinates", True,
            f"{repo['host']}/{repo['owner']}/{repo['repo']}")

        labels = self.config["labels"]
        missing = [name for name in CANONICAL_LABELS if name not in labels]
        add("labels-complete", not missing,
            f"缺失语义:{missing}" if missing else "五类语义齐全")
        project_labels = [labels.get(name, "") for name in CANONICAL_LABELS]
        conflicts = sorted({label for label in project_labels
                            if project_labels.count(label) > 1})
        add("labels-no-conflict", not conflicts,
            f"多语义映射到同一标签:{conflicts}" if conflicts else "映射无冲突")

        grouped = mgs_records._core_rows(self.config["docmap"])
        core_missing = [key for key, rows in grouped.items() if not rows]
        add("docmap-core-rows", not core_missing,
            f"缺少核心文档行:{core_missing}" if core_missing
            else "目标/设计/技术三类齐全(核心设计保留本地 Markdown 位置)")
        duplicate_types = [key for key, rows in grouped.items() if len(rows) > 1]
        core_paths = [row["path"] for rows in grouped.values() for row in rows]
        duplicate_paths = sorted({p for p in core_paths if core_paths.count(p) > 1})
        unique_ok = not duplicate_types and not duplicate_paths
        add("docmap-unique-authority", unique_ok,
            f"重复类型:{duplicate_types} 重复位置:{duplicate_paths}"
            if not unique_ok else "每类核心内容唯一当前维护位置")
        missing_paths = [row["path"] for row in
                         (grouped["goal"] + grouped["design"] + grouped["tech"])
                         if not (root / row["path"]).is_file()]
        add("docmap-paths-exist", not missing_paths,
            f"权威位置不存在:{missing_paths}" if missing_paths
            else "核心文档实际存在")

        try:
            payload = self.fetch_tasks()
        except GithubRecordsError as exc:
            add("tasks-valid", False, str(exc))
            return {"ok": False, "checks": checks, "offline": True,
                    "skipped": ["tasks-valid", "deps-consistent",
                                "labels-remote-present", "results-consistent"]}
        tasks = payload["tasks"]
        offline = bool(payload.get("cached"))
        if offline:
            skipped += ["labels-remote-present", "results-consistent"]

        task_problems: list[str] = []
        seen: set[str] = set()
        for task in tasks:
            identity = task["identity"]
            if not identity or not mgs_records.IDENTITY_RE.fullmatch(identity):
                task_problems.append(f"#{task['issue_number']}:正文身份缺失或"
                                     f"不合规({identity!r})")
            elif identity in seen:
                task_problems.append(f"{identity}:身份重复(#{task['issue_number']})")
            seen.add(identity)
            if task["triage"] not in CANONICAL_LABELS:
                task_problems.append(f"{identity}:分流 {task['triage']!r} 不在五类之内")
            if not task["progress"]:
                task_problems.append(f"{identity}:缺少进度")
            if task.get("triage_conflict"):
                task_problems.append(f"{identity}:标签与正文分流不一致")
            if task["state"] == "closed" and task.get("state_reason") not in (
                    "completed", "not_planned"):
                task_problems.append(f"{identity}:已关闭但缺少关闭原因"
                                      f"(state_reason={task.get('state_reason')!r})")
        add("tasks-valid", not task_problems,
            ";".join(task_problems) if task_problems
            else f"{len(tasks)} 个远端任务结构有效")

        edges = {task["identity"]: _parse_dep_ids(
                    task["request"].get("依赖", "")) for task in tasks}
        unresolved = [{"identity": task["identity"], "dep": dep}
                      for task in tasks
                      for dep in edges.get(task["identity"], [])
                      if dep not in seen]
        cycles = mgs_records._find_cycles(edges)
        dep_problems = [f"{item['identity']} 依赖不存在任务 {item['dep']}"
                        for item in unresolved]
        dep_problems += ["循环依赖:" + "->".join(cycle) for cycle in cycles]
        add("deps-consistent", not dep_problems,
            ";".join(dep_problems) if dep_problems else "依赖关系可解析且无循环")

        if offline:
            add("labels-remote-present", True, "未核对(离线缓存,不下结论)")
            add("results-consistent", True, "未核对(离线缓存,不下结论)")
        else:
            status, remote = self.transport.request(
                "GET", f"{_repo_path(self.repo)}/labels?per_page=100")
            remote_names = ({l.get("name") for l in remote}
                            if status == 200 and isinstance(remote, list) else None)
            if remote_names is None:
                skipped.append("labels-remote-present")
                add("labels-remote-present", True, "未核对(远端标签接口不可用)")
            else:
                absent = [labels[name] for name in CANONICAL_LABELS
                          if labels.get(name) and labels[name] not in remote_names]
                add("labels-remote-present", not absent,
                    f"仓库缺少映射标签:{absent}" if absent
                    else "五类映射标签在仓库实际存在")

            result_problems: list[str] = []
            for task in tasks:
                status, comments = self.transport.request(
                    "GET", f"{_repo_path(self.repo)}/issues/{task['issue_number']}"
                           "/comments?per_page=100")
                if status != 200 or not isinstance(comments, list):
                    result_problems.append(f"{task['identity']}:评论读取失败")
                    continue
                valid_refs = {f"#issuecomment-{c.get('id')}" for c in comments}
                for comment in comments:
                    text = comment.get("body") or ""
                    for other in seen:
                        if other != task["identity"] and other in text:
                            result_problems.append(
                                f"{task['identity']}:评论引用了其他任务身份 {other}")
                for ref in re.findall(r"#issuecomment-\d+",
                                      task["result_index_text"] or ""):
                    if ref not in valid_refs:
                        result_problems.append(
                            f"{task['identity']}:结果索引引用不存在的评论 {ref}")
            add("results-consistent", not result_problems,
                ";".join(result_problems) if result_problems
                else "评论结果与所属任务、结果索引互相一致")

        ok = all(item["ok"] for item in checks)
        return {"ok": ok, "checks": checks, "offline": offline,
                "skipped": skipped}

# ---------- 后端切换与远端交接(公开接缝) ----------

def _published_refs(config_text: str) -> dict[str, str]:
    """解析 CONFIG 外部访问行中的已发布基线引用
    (`已发布基线引用:<文件>=<url或commit@版本>`,分号分隔)。"""

    refs: dict[str, str] = {}
    match = re.search(r"已发布基线引用\s*[:：]\s*(.+)", config_text or "")
    if not match:
        return refs
    for item in re.split(r"[;；,，]", match.group(1)):
        if "=" not in item:
            continue
        name, ref = item.split("=", 1)
        refs[name.strip()] = ref.strip()
    return refs


def handover_baseline_check(project_root: Path | str,
                            config_rel: str = mgs_records.DEFAULT_CONFIG_REL,
                            *, transport=None) -> dict:
    """远端交接核对基线引用可达(《工作记录合同》:本地尚未发布的基线可供
    本机执行者引用,但不得声称远端执行者已可访问)。

    每份核心基线:本地存在性与当前版本 + 是否记录了已发布引用(远端可达
    以引用形式判定);未发布本地资料明确标注「远端执行者不可访问」。
    ok 仅在全部核心基线可达时为 True(交接前须补发布引用或明确限制)。
    """

    root = Path(project_root)
    config = mgs_records.load_config(root, config_rel)
    refs = _published_refs((root / config_rel).read_text(encoding="utf-8"))
    grouped = mgs_records._core_rows(config["docmap"])
    docs: list[dict] = []
    for key in ("goal", "design", "tech"):
        for row in grouped[key]:
            path = root / row["path"]
            published = (refs.get(row["path"]) or refs.get(Path(row["path"]).name))
            version = None
            if path.is_file():
                version_match = re.search(r"基线版本\s*[:：]\s*v(\d+)",
                                          path.read_text(encoding="utf-8"))
                version = f"v{version_match.group(1)}" if version_match else None
            docs.append({
                "path": row["path"], "content": row["content"], "role": row["role"],
                "local_exists": path.is_file(), "version": version,
                "published_ref": published,
                "remote_reachable": bool(published),
                "note": (f"已发布引用:{published}(远端执行者经此引用访问)"
                         if published else
                         "本地未发布资料:远端执行者不可访问,不得宣称已可远端"
                         "访问;发布资料仍需对应授权"),
            })
    ok = all(entry["remote_reachable"] for entry in docs)
    return {"ok": ok, "docs": docs,
            "note": ("本地尚未发布的基线可以供本机执行者引用,但必须标明资料"
                     "位置和版本;不能声称远端执行者已可访问。准备远端交接时"
                     "确认引用可达,发布资料仍需对应授权。")}


def plan_backend_switch(project_root: Path | str, *, target: str,
                        repo: str | None = None, transport=None,
                        cache_dir: Path | str | None = None) -> dict:
    """后端切换迁移清单(确认前只读):任务映射、保留方案、需确认项与
    交接基线可达核对。调用方确认后才执行 apply;apply 不直接改项目文件。
    """

    if target not in ("github-issues", "local-markdown"):
        raise GithubRecordsError(f"未知目标后端 {target!r}")
    root = Path(project_root)
    config = mgs_records.load_config(root)
    if config["backend"] == target:
        raise GithubRecordsError(f"当前后端已是 {target},无需切换")
    if target == "github-issues":
        target_repo = parse_repo_location(repo or config["task_root"])
        tasks = mgs_records.list_tasks(root)
        task_items = [{
            "identity": task["identity"], "title": task["title"],
            "triage": task["triage"], "progress": task["progress"],
            "request": task["request"],
            "source_ref": f"local:{config['task_root']}/{task['identity']}/task.md",
            "target_ref": (f"github:{target_repo['host']}/{target_repo['owner']}/"
                           f"{target_repo['repo']}/issues(身份保持 {task['identity']})"),
        } for task in tasks]
    else:
        target_repo = None
        backend = GithubBackend(config, transport, cache_dir)
        tasks = backend.fetch_tasks()["tasks"]
        task_items = [{
            "identity": task["identity"], "title": task["title"],
            "triage": task["triage"], "progress": task["progress"],
            "request": task["request"],
            "source_ref": (f"github:{config['repo']['host']}/{config['repo']['owner']}/"
                           f"{config['repo']['repo']}/issues/{task['issue_number']}"),
            "target_ref": (f"local:docs/mygamestudio/work/{task['identity']}"
                           "/task.md(身份保持)"),
        } for task in tasks]
    if not task_items:
        raise GithubRecordsError("当前后端没有可迁移的任务;切换空账本前先人工确认")
    authorized = _authorization_for(
        {**config, "repo": target_repo}, WRITE_OP)[0] if target_repo else False
    return {
        "from": config["backend"], "to": target,
        "repo": (f"{target_repo['host']}/{target_repo['owner']}/{target_repo['repo']}"
                 if target_repo else config["task_root"]),
        "project_root": str(root),
        "old_config_text": (root / config["config_path"]).read_text(encoding="utf-8"),
        "tasks": task_items,
        "write_authorized": authorized,
        "retention": [
            f"旧记录({config['backend']})全部保留为只读历史,不删除、不改写;",
            "切换生效后旧位置不再是当前任务来源,不得在其上继续安排工作"
            "(不形成两套可独立修改的当前任务账本);",
            "身份映射(本地身份 ↔ Issue 号)随新 CONFIG 留档,追溯旧记录时使用。",
        ],
        "confirmations": [
            "确认切换当前任务来源为新后端(此后唯一当前来源);",
            "确认对目标仓库的远端写入授权并已按 "
            "`host/owner/repo:issues-write(说明)` 记入 CONFIG——仅选择后端"
            "不构成授权" + ("" if authorized else "(当前 CONFIG 尚未记录,apply 前必须补)"),
            "确认远端交接的基线引用可达性(handover 检查);未发布本地资料"
            "不得宣称远端已可访问。",
        ],
        "baseline_handover": handover_baseline_check(root, transport=transport)["docs"],
        "labels": config["labels"],
    }


def _emitted_config_text(plan: dict, old_config_text: str) -> str:
    """切换后的 CONFIG 内容:唯一当前来源指向新后端,旧位置标只读历史,
    标签映射与文档映射沿用(核心文档位置不随后端切换变化)。"""

    lines: list[str] = ["# 协作配置(后端切换)", "",
                        "维护责任:制作统筹。采用依据:已确认的后端切换迁移清单。", "",
                        "## 任务来源", "",
                        f"- 后端:{plan['to']}"]
    if plan["to"] == "github-issues":
        lines.append(f"- 当前位置:{plan['repo']}")
        lines.append("- 任务读取规则:GitHub Issues 后端约定(Issue 正文承载"
                     "任务说明,评论承载结果)")
        old_position = "docs/mygamestudio/work/"
    else:
        lines.append(f"- 当前位置:{plan['repo']}(每任务一目录,task.md 为"
                     "工作请求与状态)")
        lines.append("- 任务读取规则:本地 Markdown 后端约定")
        old_position = plan["repo"]
    lines.append("- 历史任务位置(只读历史):" + old_position
                 + "(切换前账本,只作历史追溯,不再是当前任务来源)")
    for line in old_config_text.splitlines():
        if line.startswith("- 外部连接引用及已确认操作范围"):
            lines.append(line)
    lines += ["", "## 标签映射", "", "| 语义 | 项目标签 |", "| --- | --- |"]
    for canon, project in plan["labels"].items():
        lines.append(f"| {canon} | {project} |")
    lines += ["", "## 文档映射", "", "| 内容 | 当前权威位置 | 维护角色 |",
              "| --- | --- | --- |"]
    section = ""
    for line in old_config_text.splitlines():
        if line.startswith("## "):
            section = line[3:].strip()
            continue
        if section == "文档映射" and line.startswith("|") \
                and not set(line.strip()) <= set("|-: ") \
                and not line.startswith("| 内容"):
            lines.append(line)
    lines += ["", "## 身份映射(切换留档)", "",
              "本地身份 → Issue 号(或本地路径)见 identity-map.json;身份保持不变。",
              ""]
    return "\n".join(lines)


def apply_backend_switch(plan_path: Path | str, *, confirmed: bool,
                         emit_dir: Path | str, project_root: Path | str,
                         transport=None, cache_dir: Path | str | None = None) -> dict:
    """执行**已确认**的切换:只做目标侧创建与材料产出。

    - 不删除、不改写旧记录(保留只读历史);
    - 不直接改写项目 CONFIG:新 CONFIG 内容产出到 emit_dir/CONFIG.md,
      由经确认的应用步骤(统筹经 mgs-gate 受控通道)写入,保证唯一当前来源;
    - 目标为 GitHub 时,要求当前项目 CONFIG 已记录目标仓库的 issues-write
      授权(apply 侧再核对一次,不自我授权)。
    """

    plan = json.loads(Path(plan_path).read_text(encoding="utf-8"))
    if not confirmed:
        raise GithubRecordsError("迁移清单未经确认(confirmed=False),不执行切换")
    root = Path(project_root)
    current = mgs_records.load_config(root)
    emit = Path(emit_dir)
    emit.mkdir(parents=True, exist_ok=True)
    created = 0
    mapping: dict[str, dict] = {}
    if plan["to"] == "github-issues":
        target_repo = parse_repo_location(plan["repo"])
        allowed, _note = _authorization_for({**current, "repo": target_repo},
                                            WRITE_OP)
        if not allowed:
            raise GithubRecordsError(
                f"项目 CONFIG 尚未对 {plan['repo']} 记录 issues-write 授权;"
                "迁移清单确认后须先按 `host/owner/repo:issues-write(说明)` 更新"
                " CONFIG(经确认的应用步骤),apply 不自我授权")
        backend = GithubBackend({**current, "repo": target_repo,
                                 "backend": GITHUB_BACKEND},
                                transport, cache_dir)
        results = []
        for item in plan["tasks"]:
            outcome = backend.create_task(
                item["identity"], item["title"], item["request"],
                triage=item["triage"], progress=item["progress"])
            results.append({"identity": item["identity"], **{
                key: outcome.get(key)
                for key in ("created", "adopted", "issue_number", "published")}})
            if outcome.get("created") or outcome.get("adopted"):
                created += 1
                mapping[item["identity"]] = {
                    "github_issue": outcome.get("issue_number"),
                    "source_ref": item["source_ref"]}
        (emit / "identity-map.json").write_text(
            json.dumps(mapping, ensure_ascii=False, indent=2), encoding="utf-8")
        result = {"created": created, "results": results, "emit_dir": str(emit)}
    else:
        for item in plan["tasks"]:
            body = build_task_body(item["title"], item["identity"],
                                   item["triage"], item["progress"],
                                   item["request"])
            rel = f"docs/mygamestudio/work/{item['identity']}/task.md"
            path = emit / rel
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(body, encoding="utf-8")
            mapping[item["identity"]] = {"local_path": rel,
                                         "source_ref": item["source_ref"]}
            created += 1
        (emit / "identity-map.json").write_text(
            json.dumps(mapping, ensure_ascii=False, indent=2), encoding="utf-8")
        result = {"created": created, "emit_dir": str(emit / "files")}
    (emit / "CONFIG.md").write_text(
        _emitted_config_text(plan, plan.get("old_config_text", "")),
        encoding="utf-8")
    result["config_emitted"] = str(emit / "CONFIG.md")
    result["note"] = ("apply 只创建目标侧任务并产出新 CONFIG 内容;项目 CONFIG "
                      "由经确认的应用步骤经 mgs-gate 写入(唯一当前来源),"
                      "旧记录保留为只读历史,身份映射已留档。")
    return result

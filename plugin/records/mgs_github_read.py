#!/usr/bin/env python3
"""GitHub Issues 后端的读取、离线缓存回退与回读核验(票 20)。

把 ``GithubBackend`` 的读取职责从写操作适配器中按职责移出:列表抓取与
离线缓存回退、按身份取 Issue、单任务读取(正文 + 评论结果),以及后端回读
核验(verify)。这些方法只依赖后端的配置、仓库坐标与传输层,不涉及写入
授权;``GithubBackend`` 通过继承取得它们,公开方法面与既有语义不变。

依赖纪律:只依赖中性记录 module ``mgs_record_model``、Issue 形态 module
``mgs_github_issue``(正文字段解析)与传输接缝 ``mgs_github_transport``;
不导入业务适配器 ``mgs_github`` 或查询组织 ``mgs_records``。本模块不发起
真实远端写入(仅读取与核验)。
"""

from __future__ import annotations

import datetime as _dt
import hashlib
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import mgs_record_model  # noqa: E402
from mgs_github_issue import (  # noqa: E402
    is_record_carrier, parse_issue_payload, skip_from_current_reads)
from mgs_github_transport import (  # noqa: E402
    GithubRecordsError, TransportError, repo_path, repo_str)
from mgs_record_model import CANONICAL_LABELS  # noqa: E402

GITHUB_BACKEND = "github-issues"
OFFLINE_NOTE = ("远端不可用:以下为注明时间与来源的缓存,不是远端当前状态;"
                "不静默切换本地后端。")


class GithubReadMixin:
    """``GithubBackend`` 的读取、离线缓存回退与回读核验方法集合。

    依赖宿主提供 ``config`` / ``repo`` / ``transport`` / ``cache_dir``
    (由 ``GithubBackend.__init__`` 建立);本 mixin 不定义构造与写入。
    """

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
                "GET", f"{repo_path(self.repo)}/issues?state=all&per_page=100")
            if status != 200 or not isinstance(data, list):
                raise TransportError("bad_response", f"list issues HTTP {status}")
        except TransportError as exc:
            cached = self._load_cache()
            if cached is None:
                raise GithubRecordsError(
                    f"远端不可用({exc})且无缓存:{repo_str(self.repo)};"
                    "不静默切换本地后端") from exc
            return {"tasks": cached["tasks"], "cached": True,
                    "fetched_at": cached["fetched_at"],
                    "source": cached["source"], "note": OFFLINE_NOTE}
        tasks = [parse_issue_payload(item, self.config["labels"])
                 for item in data
                 if "pull_request" not in item
                 and not skip_from_current_reads(item.get("body") or "")
                 and not is_record_carrier(item.get("body") or "")]
        payload = {
            "tasks": tasks,
            "cached": False,
            "fetched_at": _dt.datetime.now().astimezone().isoformat(timespec="seconds"),
            "source": {"backend": GITHUB_BACKEND,
                       "repo": repo_str(self.repo)},
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
                "GET", f"{repo_path(self.repo)}/issues/{task['issue_number']}")
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
                "GET", f"{repo_path(self.repo)}/issues/{parsed['issue_number']}"
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
            by_number = {task["issue_number"]: task for task in payload["tasks"]}
            parent_no = parsed.get("parent_issue_number")
            if parent_no and parent_no in by_number:
                parsed["parent_identity"] = by_number[parent_no]["identity"]
            try:
                rel_status, blockers = self.transport.request(
                    "GET",
                    f"{repo_path(self.repo)}/issues/{parsed['issue_number']}"
                    "/dependencies/blocked_by")
            except TransportError:
                rel_status, blockers = None, None
            if rel_status == 200 and isinstance(blockers, list):
                parsed["blocked_by_identities"] = [
                    parse_issue_payload(item, self.config["labels"])["identity"]
                    for item in blockers]
                parsed["blocked_by"] = parsed["blocked_by_identities"]
        else:
            parsed["body_sha256"] = hashlib.sha256(
                (parsed.get("body") or "").encode("utf-8")).hexdigest()
            parsed["cached_read"] = True
            parsed["cached_note"] = OFFLINE_NOTE
        parsed["results"] = results
        return parsed

    # ----- 回读核验 -----

    def verify(self, project_root: Path | str) -> dict:
        """github-issues 后端回读核验(与本地后端同一含义的检查集)。

        标签映射、核心文档映射、任务核心字段(含工作请求必填字段)与依赖
        关系使用 mgs_record_model 的单一共享实现(审查修复票 01/核验建议 1:
        同一畸形任务在两个后端得到相同结论);本方法只保留存储特有检查
        (远端标签实际存在、评论一致性、身份重复、标签与正文冲突、关闭原因)。
        离线时基于缓存核对结构与依赖,远端存在性检查标注「未核对(离线)」,
        不冒充已核验;整体结果附 offline 标记。远端不可用且无缓存时报错,
        不回退本地。
        """

        root = Path(project_root)
        checks: list[dict] = []
        skipped: list[str] = []

        checks.append(mgs_record_model.check_item(
            "config-present", True, str(root / self.config["config_path"])))
        repo = self.repo
        checks.append(mgs_record_model.check_item(
            "backend-github-coordinates", True,
            f"{repo['host']}/{repo['owner']}/{repo['repo']}"))
        checks += mgs_record_model.label_mapping_checks(self.config["labels"])
        checks += mgs_record_model.docmap_checks(root, self.config["docmap"])

        try:
            payload = self.fetch_tasks()
        except GithubRecordsError as exc:
            checks.append(mgs_record_model.check_item("tasks-valid", False, str(exc)))
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
            # 任务核心字段:与本地后端共享的单一实现(where 用 #Issue号 定位)
            task_problems += mgs_record_model.task_core_problems(
                task, f"#{task['issue_number']}")
            if identity and identity in seen:
                task_problems.append(f"{identity}:身份重复(#{task['issue_number']})")
            seen.add(identity)
            if task.get("triage_conflict"):
                task_problems.append(f"{identity}:标签与正文分流不一致")
            if task["state"] == "closed" and task.get("state_reason") not in (
                    "completed", "not_planned"):
                task_problems.append(f"{identity}:已关闭但缺少关闭原因"
                                      f"(state_reason={task.get('state_reason')!r})")
        checks.append(mgs_record_model.check_item(
            "tasks-valid", not task_problems,
            ";".join(task_problems) if task_problems
            else f"{len(tasks)} 个远端任务结构有效"))

        dep_problems = mgs_record_model.dependency_problems(tasks)
        checks.append(mgs_record_model.check_item(
            "deps-consistent", not dep_problems,
            ";".join(dep_problems) if dep_problems else "依赖关系可解析且无循环"))

        labels = self.config["labels"]
        if offline:
            checks.append(mgs_record_model.check_item(
                "labels-remote-present", True, "未核对(离线缓存,不下结论)"))
            checks.append(mgs_record_model.check_item(
                "results-consistent", True, "未核对(离线缓存,不下结论)"))
        else:
            status, remote = self.transport.request(
                "GET", f"{repo_path(self.repo)}/labels?per_page=100")
            remote_names = ({raw.get("name") for raw in remote}
                            if status == 200 and isinstance(remote, list) else None)
            if remote_names is None:
                skipped.append("labels-remote-present")
                checks.append(mgs_record_model.check_item(
                    "labels-remote-present", True, "未核对(远端标签接口不可用)"))
            else:
                absent = [labels[name] for name in CANONICAL_LABELS
                          if labels.get(name) and labels[name] not in remote_names]
                checks.append(mgs_record_model.check_item(
                    "labels-remote-present", not absent,
                    f"仓库缺少映射标签:{absent}" if absent
                    else "五类映射标签在仓库实际存在"))

            result_problems: list[str] = []
            for task in tasks:
                status, comments = self.transport.request(
                    "GET", f"{repo_path(self.repo)}/issues/{task['issue_number']}"
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
            checks.append(mgs_record_model.check_item(
                "results-consistent", not result_problems,
                ";".join(result_problems) if result_problems
                else "评论结果与所属任务、结果索引互相一致"))

        ok = all(item["ok"] for item in checks)
        return {"ok": ok, "checks": checks, "offline": offline,
                "skipped": skipped}

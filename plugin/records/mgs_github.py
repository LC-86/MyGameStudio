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
- 普通工作不经 mgs-gate;仓库级授权与宿主实际限制继续适用。

故障语义(超时回读再重试 / 防重复创建 / 离线缓存与草稿):
- 创建超时或结果不确定:先用任务身份回读远端(已落地则收养,不重复
  创建),未落地才重试一次;全部尝试如实上报。
- 远端不可用:读取返回**注明时间与来源**的缓存;写入保存**未发布草稿**
  (标明来源与状态),绝不把草稿报告为已发布,也绝不静默改用本地后端。

本地替身验证说明:传输层可注入(API 端点可经 MGS_GH_API_BASE/--api-base
覆盖),验收用本地 HTTP 替身覆盖故障语义;真实远端写入仅在明确授权的
测试仓库执行(任务票 17 保留待办)。

票 20 职责整理(纯结构调整,语义不变):本 adapter 只保留写操作与在线/
重放共用的动作分发;Issue 正文序列化与仓库级授权核对归 ``mgs_github_issue``,
读取/离线缓存与回读核验归 ``mgs_github_read``(``GithubBackend`` 经其
mixin 继承),后端切换迁移与交接核对归 ``mgs_github_migration``。既有公开
名字(含 ``plan_backend_switch``/``apply_backend_switch``/
``handover_baseline_check`` 与传输层重导出)在本模块仍可达。
"""

from __future__ import annotations

import datetime as _dt  # noqa: F401 - 兼容接缝:既有测试经 mgs_github._dt 冻结时钟
import hashlib
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import mgs_github_issue  # noqa: E402
import mgs_github_read  # noqa: E402
from mgs_github_read import GithubReadMixin  # noqa: E402
import mgs_record_model  # noqa: E402
import mgs_record_source  # noqa: E402
import mgs_result_publication  # noqa: E402
from mgs_record_model import (  # noqa: E402,F401
    CANONICAL_LABELS, RecordsError, edit_body, today)
from mgs_github_transport import (  # noqa: E402
    GithubRecordsError, TransportError, repo_path, repo_str)
# 兼容再导出:传输/错误接缝的公开名字仍从 mgs_github 可达(现有调用方与
# 测试经 mgs_github.UrllibTransport / api_base_for / token_from_env /
# default_api_base / API_BASE_ENV 定位),唯一定义在 mgs_github_transport。
from mgs_github_transport import (  # noqa: E402,F401
    API_BASE_ENV, UrllibTransport, api_base_for, default_api_base,
    token_from_env)

GITHUB_BACKEND = "github-issues"
WRITE_OP = mgs_record_source.WRITE_OP

OFFLINE_NOTE = mgs_github_read.OFFLINE_NOTE
DRAFT_NOTE = ("远端不可用:已保存未发布草稿(标明来源与状态);草稿不是已发布任务,"
              "发布需在远端可用后重试;不静默切换本地后端。")
CLOSE_NOTE = "关闭 Issue 不自动等于验证通过;验收以任务记录的验收方式与实际证据为准。"


# ---------- 配置解析(公开接缝) ----------
# 仓库坐标与远端授权声明的文本解析归属中性来源 module(mgs_record_source:
# 协作配置职责),仓库级授权核对与仓库坐标的 GitHub 错误身份归 Issue 形态
# 职责 module(mgs_github_issue)。本 adapter 只保持既有公开名字可达(现有
# 调用方与测试经 mgs_github 定位),错误仍为 GithubRecordsError。
# 授权纪律不变:选择 GitHub 后端不等于批准远端写入,需 CONFIG 明确到
# host/owner/repository 的 issues-write 授权。

parse_remote_authorizations = mgs_record_source.parse_remote_authorizations
parse_repo_location = mgs_github_issue.parse_repo_location
_authorization_for = mgs_github_issue.authorization_for


# ---------- Issue 正文(与本地 task.md 同一记录格式) ----------
# 正文的序列化与解析由 mgs_github_issue 承担(同一套共同正文规则);本 adapter
# 在公开接缝上重导出,既有调用与测试定位不变。

build_task_body = mgs_github_issue.build_task_body
parse_issue_payload = mgs_github_issue.parse_issue_payload
parse_issue_body = mgs_github_issue.parse_issue_body


# ---------- Issue 正文编辑(保持与 task.md 同一记录格式) ----------
# section_lines/edit_body/today 的唯一定义在 mgs_record_model(共同正文
# 规则的写面,与 parse_task_body 同一规则);本模块在其公开接缝上复用,
# 不再各自维护一份正文序列化实现。


class GithubBackend(GithubReadMixin):
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

    # ----- 写操作(先核对 CONFIG 仓库级 issues-write 授权) -----

    def _authorize_write(self) -> None:
        allowed, note = _authorization_for(self.config, WRITE_OP)
        if not allowed:
            raise GithubRecordsError(note)

    def _save_draft(self, op: str, args: dict, cause: str) -> dict:
        """远端不可用时保存未发布草稿(标明来源与状态;不视为已发布)。

        草稿的存储、身份(操作+参数+**目标仓库**)与重放自票 20 起收敛在
        ``mgs_result_publication.save_unpublished_draft``(与发布生命周期同一
        恢复事实);本 adapter 只注入目标仓库标签、缓存目录与草稿说明,保持
        既有返回形态。
        """

        return mgs_result_publication.save_unpublished_draft(
            cache_dir=self.cache_dir, repo=repo_str(self.repo), op=op,
            args=args, cause=cause, note=DRAFT_NOTE)

    def record_unpublished_draft(self, op: str, args: dict, cause: str) -> dict:
        """公开写接缝:把一次未能确认发布的远端操作保存为**未发布草稿**。

        与 ``_save_draft`` 是同一职责的公开表达:受控运行入口(mgs_remote)
        在动作抛传输故障、适配器未自行保存草稿时经本接缝兜底,不再直接调用
        私有草稿细节。返回形态与 ``_save_draft`` 完全一致(未发布/草稿路径/
        原因/说明),错误语义(未配置缓存目录时报记录错误)保持。远端恢复后
        由 ``publish_drafts`` 按原参数重放。
        """

        return self._save_draft(op, args, cause)

    def _find_by_identity(self, identity: str) -> dict | None:
        """按任务身份回读远端(防重复创建的读路径;不做缓存回退)。

        传输故障原样抛 TransportError,由调用方决定收养/重试/起草稿;
        回读失败时绝不发创建请求(避免重复创建)。
        """

        status, data = self.transport.request(
            "GET", f"{repo_path(self.repo)}/issues?state=all&per_page=100")
        if status != 200 or not isinstance(data, list):
            raise TransportError("bad_response", f"list issues HTTP {status}")
        for item in data:
            if "pull_request" in item:
                continue
            if mgs_github_issue.skip_from_current_reads(item.get("body") or ""):
                continue
            parsed = parse_issue_payload(item, self.config["labels"])
            if parsed["identity"] == identity:
                return parsed
        return None

    # ----- 结果发布恢复 -----
    # 待补索引/碰撞/损坏/旧布局/清除的存储与归属规则集中在
    # mgs_result_publication(票 18),本 adapter 的 append_result 只注入
    # 自身的授权、读取、草稿与回读操作,不在此重复恢复规则。

    def create_task(self, identity: str, title: str, request: dict, *,
                    triage: str = "needs-triage", progress: str = "待执行") -> dict:
        """创建任务。防重复:先按身份回读,已存在即收养;超时先回读再重试一次。

        attempts 如实记录每次尝试结果;duplicate_avoided 标记「超时后回读
        发现已落地而避免的重复创建」。回读+重试都未落地时报错,不虚报成功;
        读前核对或回读本身失败(离线)时保存未发布草稿,不盲发创建请求。
        """

        self._authorize_write()
        import mgs_local_backend  # noqa: PLC0415

        root = Path(self.config.get("project_root") or ".")
        for entry in mgs_local_backend.load_cancelled(root, self.config):
            if (entry.get("op") == "create_task"
                    and entry.get("identity") == identity
                    and entry.get("status") == "cancelled"):
                raise GithubRecordsError(
                    f"操作已撤销:create_task {identity};不得恢复已撤销动作")
        if not identity or not mgs_record_model.IDENTITY_RE.fullmatch(identity):
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
                    "POST", f"{repo_path(self.repo)}/issues", payload)
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
        draft_args = {"identity": identity, "fields": fields,
                      "expected_body_sha256": expected_body_sha256,
                      "change_note": change_note}
        try:
            issue, parsed, payload = self._get_issue(identity)
        except TransportError as exc:
            draft = self._save_draft("update_task", draft_args, str(exc))
            draft["attempts"] = [{"step": "read", "outcome": exc.kind}]
            return draft
        if issue is None:
            draft = self._save_draft(
                "update_task", draft_args,
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
        change_line = f"{today()} {change_note}:{'、'.join(fields)}"
        new_body = edit_body(issue.get("body") or "", header=header_updates,
                              request=request_updates, append_change=change_line)
        try:
            status, updated = self.transport.request(
                "PATCH", f"{repo_path(self.repo)}/issues/{parsed['issue_number']}",
                {"body": new_body})
            if status != 200:
                raise TransportError("bad_response", f"update HTTP {status}")
        except TransportError as exc:
            draft = self._save_draft("update_task", draft_args, str(exc))
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
        new_body = edit_body(issue.get("body") or "",
                              header={"当前分流": label},
                              append_change=f"{today()} 分流调整为 {label}")
        try:
            status, updated = self.transport.request(
                "PATCH", f"{repo_path(self.repo)}/issues/{parsed['issue_number']}",
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
        """追加结果(公开写接缝):完整发布恢复生命周期见
        ``mgs_result_publication.ResultPublication.append``——发布前回读
        收养、评论发布、结果索引更新、部分成功/结果未知与待补索引登记。

        本 adapter 注入自身的写接缝操作(授权、按身份读取、未发布草稿、
        索引补齐后的回读),远端动作仍经传输层;返回身份、attempts 与
        恢复说明保持既有形态(未发布/结果未知/部分成功/完成分别表达)。
        """

        publication = mgs_result_publication.ResultPublication(
            repo=self.repo, transport=self.transport, cache_dir=self.cache_dir,
            authorize=self._authorize_write, load_issue=self._get_issue,
            save_draft=self._save_draft, read_back=self.read_task)
        return publication.append(identity, result_markdown)

    def _probe_get(self, path: str):
        """探测原生能力:available / unavailable(确认 404) / transient。

        短暂故障不得记成能力不存在。
        """

        try:
            status, data = self.transport.request("GET", path)
        except TransportError as exc:
            return "transient", exc
        if status == 404:
            return "unavailable", None
        if status == 200:
            return "available", data
        return "transient", TransportError(
            "bad_response", f"GET {path} HTTP {status}")

    def set_relations(self, identity: str, deps: list[str]) -> dict:
        """设置阻塞关系:优先原生 issue dependencies;确认不可用才回退正文。"""

        self._authorize_write()
        draft_args = {"identity": identity, "deps": deps}
        try:
            tasks = self.fetch_tasks()["tasks"]
        except TransportError as exc:
            return self._save_draft("set_relations", draft_args, str(exc))
        except GithubRecordsError:
            raise
        by_id = {task["identity"]: task for task in tasks}
        missing = [dep for dep in deps if dep not in by_id]
        if missing:
            raise GithubRecordsError(
                f"依赖任务不存在:{missing}(引用必须可解析,不写悬空依赖)")
        child = by_id[identity]
        value = "、".join(f"#{by_id[dep]['issue_number']} {dep}" for dep in deps) \
            or "无"
        probe_path = (f"{repo_path(self.repo)}/issues/"
                      f"{child['issue_number']}/dependencies/blocked_by")
        state, data = self._probe_get(probe_path)
        if state == "transient":
            return self._save_draft(
                "set_relations", draft_args,
                f"探测原生阻塞关系失败({data});不自行降级")
        if state == "available":
            existing_ids = {item.get("id") for item in (data or [])
                            if isinstance(item, dict)}
            for dep in deps:
                blocker = by_id[dep]
                if blocker.get("issue_id") in existing_ids:
                    continue
                try:
                    status, _payload = self.transport.request(
                        "POST", probe_path, {"issue_id": blocker["issue_id"]})
                    if status == 404:
                        return self._save_draft(
                            "set_relations", draft_args,
                            "写入原生阻塞关系 HTTP 404,探测时能力仍在;"
                            "不自行降级为正文约定")
                    if status == 422:
                        # 校验拒绝(如依赖成环)不是成功:先回读核实是否
                        # 已存在;确实未落地则按失败上报,不把「依赖已写」
                        # 写进正文或读回结论。
                        landed, landed_data = self._probe_get(probe_path)
                        if landed == "available":
                            landed_ids = {
                                item.get("id") for item in (landed_data or [])
                                if isinstance(item, dict)}
                            if blocker.get("issue_id") in landed_ids:
                                continue
                        raise GithubRecordsError(
                            f"写入原生阻塞关系被拒绝(HTTP 422,依赖 {dep} "
                            "未落地);按失败处理,不写正文约定也不虚报原生成功")
                    if status not in (200, 201):
                        raise TransportError(
                            "bad_response", f"blocked_by HTTP {status}")
                except TransportError as exc:
                    landed, landed_exc = self._probe_get(probe_path)
                    if landed == "available":
                        landed_ids = {item.get("id") for item in (landed_exc or [])
                                      if isinstance(item, dict)}
                        if blocker.get("issue_id") in landed_ids:
                            continue
                    return self._save_draft(
                        "set_relations", draft_args,
                        f"写入原生阻塞关系结果未知({exc});先回读再补缺项")
            desired_ids = {by_id[dep].get("issue_id") for dep in deps}
            extra_ids = [issue_id for issue_id in existing_ids
                         if issue_id and issue_id not in desired_ids]
            for issue_id in extra_ids:
                try:
                    status, _payload = self.transport.request(
                        "DELETE", f"{probe_path}/{issue_id}")
                    if status == 404:
                        return self._save_draft(
                            "set_relations", draft_args,
                            "删除原生阻塞关系 HTTP 404,探测时能力仍在;"
                            "不自行降级为正文约定")
                    if status not in (200, 204):
                        raise TransportError(
                            "bad_response", f"blocked_by DELETE HTTP {status}")
                except TransportError as exc:
                    landed, landed_exc = self._probe_get(probe_path)
                    if landed == "available":
                        landed_ids = {item.get("id") for item in (landed_exc or [])
                                      if isinstance(item, dict)}
                        if issue_id not in landed_ids:
                            continue
                    return self._save_draft(
                        "set_relations", draft_args,
                        f"删除原生阻塞关系结果未知({exc});先回读再补缺项")
            result = self.update_task(identity, {"依赖": value},
                                      change_note="设置依赖(原生)")
            result["mode"] = "native-blocked-by"
            readback = result.get("readback") or {}
            readback["blocked_by_identities"] = list(deps)
            readback["blocked_by"] = list(deps)
            result["readback"] = readback
            return result
        result = self.update_task(identity, {"依赖": value},
                                  change_note="设置依赖(正文引用)")
        result["mode"] = "body-reference"
        result["fallback_reason"] = "原生阻塞关系确认不可用"
        return result

    def set_parent(self, identity: str, parent_id: str | None) -> dict:
        """设置父子关系:优先原生 sub-issues;仅确认不可用时回退正文引用。"""

        self._authorize_write()
        draft_args = {"identity": identity, "parent": parent_id}
        try:
            _issue, parsed, _payload = self._get_issue(identity)
        except TransportError as exc:
            return self._save_draft("set_parent", draft_args, str(exc))
        if parent_id is None:
            parent_no = parsed.get("parent_issue_number")
            child_id = parsed.get("issue_id")
            mode = "body-reference"
            if parent_no and child_id:
                probe_path = (f"{repo_path(self.repo)}/issues/"
                              f"{parent_no}/sub_issues")
                state, data = self._probe_get(probe_path)
                if state == "transient":
                    return self._save_draft(
                        "set_parent", draft_args,
                        f"探测原生父子关系失败({data});不自行降级")
                if state == "available":
                    try:
                        status, _data = self.transport.request(
                            "DELETE",
                            f"{repo_path(self.repo)}/issues/{parent_no}/sub_issue",
                            {"sub_issue_id": child_id})
                        if status == 404:
                            return self._save_draft(
                                "set_parent", draft_args,
                                "删除原生子 Issue HTTP 404,探测时能力仍在;"
                                "不自行降级为正文约定")
                        if status not in (200, 204):
                            raise TransportError(
                                "bad_response", f"sub-issue DELETE HTTP {status}")
                    except TransportError as exc:
                        landed, payload = self._probe_get(probe_path)
                        still_child = (
                            landed == "available"
                            and any(isinstance(item, dict)
                                    and item.get("id") == child_id
                                    for item in (payload or [])))
                        if still_child:
                            return self._save_draft(
                                "set_parent", draft_args,
                                f"删除原生子 Issue 结果未知({exc});先回读再补缺项")
                    mode = "native-sub-issues"
            body_change = {"父任务": "无"}
            result = self.update_task(identity, body_change,
                                      change_note="解除父任务")
            result["mode"] = mode
            return result
        parent = self._find_by_identity(parent_id)
        if parent is None:
            raise GithubRecordsError(f"父任务不存在:{parent_id}")
        probe_path = (f"{repo_path(self.repo)}/issues/"
                      f"{parent['issue_number']}/sub_issues")
        if self._sub_issues_available is None:
            state, data = self._probe_get(probe_path)
            if state == "transient":
                return self._save_draft(
                    "set_parent", draft_args,
                    f"探测原生父子关系失败({data});不自行降级")
            self._sub_issues_available = state == "available"
            existing = data if state == "available" else []
        elif self._sub_issues_available:
            state, data = self._probe_get(probe_path)
            if state == "transient":
                return self._save_draft(
                    "set_parent", draft_args,
                    f"读取原生父子关系失败({data});不自行降级")
            if state == "unavailable":
                self._sub_issues_available = False
                existing = []
            else:
                existing = data or []
        else:
            existing = []
        if self._sub_issues_available:
            child_id = parsed.get("issue_id") or parsed["issue_number"]
            already = any(
                isinstance(item, dict) and item.get("id") == child_id
                for item in existing)
            if not already:
                try:
                    status, _data = self.transport.request(
                        "POST", probe_path, {"sub_issue_id": child_id})
                    if status == 404:
                        return self._save_draft(
                            "set_parent", draft_args,
                            "写入原生父子关系 HTTP 404,探测时能力仍在;"
                            "不自行降级为正文约定")
                    if status == 422:
                        # 校验拒绝(子 Issue 已属其他父/会成环等)不是
                        # 成功:回读核实是否已落地;未落地按失败上报,
                        # 不把原生关系写进正文或虚报 parent_identity。
                        landed, payload = self._probe_get(probe_path)
                        landed_child = (
                            landed == "available"
                            and any(isinstance(item, dict)
                                    and item.get("id") == child_id
                                    for item in (payload or [])))
                        if not landed_child:
                            raise GithubRecordsError(
                                "写入原生父子关系被拒绝(HTTP 422,子 Issue "
                                "未落地);按失败处理,不写正文约定也不虚报"
                                "原生成功")
                    elif status not in (200, 201):
                        raise TransportError(
                            "bad_response", f"sub-issues HTTP {status}")
                except TransportError as exc:
                    landed, payload = self._probe_get(probe_path)
                    if landed == "available" and any(
                            isinstance(item, dict) and item.get("id") == child_id
                            for item in (payload or [])):
                        already = True
                    else:
                        return self._save_draft(
                            "set_parent", draft_args,
                            f"写入原生父子关系结果未知({exc});先回读再补缺项")
            if self._sub_issues_available:
                result = self.update_task(
                    identity,
                    {"父任务": f"#{parent['issue_number']} {parent_id}"
                               "(原生 sub-issue)"},
                    change_note="设置父任务(原生)")
                result["mode"] = "native-sub-issues"
                readback = result.get("readback") or {}
                readback["parent_identity"] = parent_id
                result["readback"] = readback
                return result
        result = self.update_task(
            identity,
            {"父任务": f"#{parent['issue_number']} {parent_id}"},
            change_note="设置父任务(正文引用)")
        result["mode"] = "body-reference"
        result["fallback_reason"] = "原生父子关系确认不可用"
        return result

    def claim_task(self, identity: str, actor: str) -> dict:
        """认领:写入原生负责人(assignees);已有他人认领则拒绝覆盖。"""

        self._authorize_write()
        draft_args = {"identity": identity, "actor": actor}
        try:
            issue, parsed, _payload = self._get_issue(identity)
        except TransportError as exc:
            return self._save_draft("claim_task", draft_args, str(exc))
        if issue is None:
            return self._save_draft(
                "claim_task", draft_args, "离线缓存态无法改远端负责人")
        current = [entry.get("login") for entry in (issue.get("assignees") or [])
                   if entry.get("login")]
        if current and actor not in current:
            raise GithubRecordsError(
                f"任务已由 {current[0]} 认领,不覆盖他人认领")
        if actor in current:
            # 已在指派名单内(可能另有协作者):按已认领返回,
            # 不得把整个指派名单替换成单人而移除共同指派。
            parsed["assignees"] = current
            parsed["claim"] = actor
            return {"published": True, "adopted": True,
                    "issue_number": parsed["issue_number"], "readback": parsed}
        try:
            status, updated = self.transport.request(
                "PATCH",
                f"{repo_path(self.repo)}/issues/{parsed['issue_number']}",
                {"assignees": [actor]})
            if status != 200:
                raise TransportError("bad_response", f"claim HTTP {status}")
        except TransportError as exc:
            try:
                landed = self._find_by_identity(identity)
            except TransportError:
                landed = None
            if landed and actor in (landed.get("assignees") or []):
                return {"published": True, "adopted": True,
                        "duplicate_avoided": True,
                        "issue_number": landed["issue_number"],
                        "readback": landed}
            return self._save_draft(
                "claim_task", draft_args,
                f"认领结果未知({exc});先回读再补缺项")
        try:
            self.update_task(identity, {"认领": actor}, change_note="认领")
        except (TransportError, GithubRecordsError):
            pass
        readback = parse_issue_payload(updated, self.config["labels"])
        readback["assignees"] = [actor]
        readback["claim"] = actor
        return {"published": True, "issue_number": parsed["issue_number"],
                "readback": readback}

    def frontier_tasks(self, parent_identity: str | None = None) -> dict:
        """Wayfinder 前沿:开放、未认领、无开放阻塞的子票,按子票顺序。"""

        payload = self.fetch_tasks()
        tasks = payload["tasks"]
        by_id = {task["identity"]: task for task in tasks}
        by_number = {task["issue_number"]: task for task in tasks}
        mode = "native-sub-issues"
        if parent_identity:
            parent = by_id.get(parent_identity)
            if parent is None:
                raise GithubRecordsError(f"父任务不存在:{parent_identity}")
            state, data = self._probe_get(
                f"{repo_path(self.repo)}/issues/"
                f"{parent['issue_number']}/sub_issues")
            if state == "transient":
                raise GithubRecordsError(
                    f"读取原生子票失败({data});短暂错误不降级为正文约定")
            if state == "available":
                ordered = [parse_issue_payload(item, self.config["labels"])
                           for item in (data or [])]
                mode = "native-sub-issues"
            else:
                ordered = [
                    task for task in tasks
                    if parent_identity in (
                        task.get("request") or {}).get("父任务", "")]
                mode = "body-reference"
        else:
            ordered = list(tasks)
        # 原生阻塞关系不可用时,依赖只存在于正文引用;
        # 前沿必须把已知开放依赖同样视为阻塞,否则会放行不可开始的任务。
        dep_mode = "native-blocked-by"
        probe_target = None
        if parent_identity and parent_identity in by_id:
            probe_target = by_id[parent_identity]["issue_number"]
        elif ordered:
            probe_target = ordered[0].get("issue_number")
        if probe_target:
            probe_state, _probe_data = self._probe_get(
                f"{repo_path(self.repo)}/issues/"
                f"{probe_target}/dependencies/blocked_by")
            if probe_state == "transient":
                raise GithubRecordsError(
                    f"读取原生阻塞关系失败({_probe_data});"
                    "短暂错误不降级为正文约定")
            if probe_state != "available":
                dep_mode = "body-reference"

        def _body_blocked(task: dict) -> bool:
            raw = str((task.get("request") or {}).get("依赖") or "").strip()
            if not raw or raw == "无":
                return False
            for token in raw.split("、"):
                token = token.strip()
                if not token:
                    continue
                match = re.match(r"#(\d+)\s+(\S+)", token)
                if match:
                    blocker = by_number.get(int(match.group(1)))
                    identity = match.group(2)
                else:
                    blocker = by_id.get(token.split()[0])
                    identity = token.split()[0]
                if blocker is None:
                    blocker = by_id.get(identity)
                if blocker is None:
                    return True
                if blocker.get("state", "open") == "open":
                    return True
            return False

        frontier = []
        for task in ordered:
            if parent_identity and task["identity"] == parent_identity:
                continue
            if task.get("state", "open") != "open":
                continue
            if task.get("assignees"):
                continue
            if int(task.get("open_blocker_count") or 0) > 0:
                continue
            if dep_mode == "body-reference" and _body_blocked(task):
                continue
            parent_no = task.get("parent_issue_number")
            parent_name = (by_number[parent_no]["identity"]
                           if parent_no in by_number else None)
            frontier.append({
                "identity": task["identity"],
                "title": task["title"],
                "issue_number": task.get("issue_number"),
                "triage": task.get("triage"),
                "parent_identity": parent_name or parent_identity,
            })
        return {
            "wrote": False,
            "frontier": frontier,
            "selected": frontier[0] if frontier else None,
            "mode": mode,
            "cached": bool(payload.get("cached")),
            "note": ("前沿=地图子票中开放、未认领且无开放阻塞的任务;"
                     "按子票顺序选择;认领后离开前沿;"
                     "关闭不等于验收通过"),
        }

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
        # 关闭原因随正文持久化:仅写进度头部或只发一条评论时,后续
        # read_task 无法从 GitHub 状态重建两类 completed 的区别。
        new_body = edit_body(issue.get("body") or "",
                             header={"进度": progress, "关闭原因": reason},
                             append_change=f"{today()} 关闭({reason})")
        try:
            status, updated = self.transport.request(
                "PATCH", f"{repo_path(self.repo)}/issues/{number}",
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
            "POST", f"{repo_path(self.repo)}/issues/{number}/comments",
            {"body": f"任务:{identity}\n\n{closing_note}。{CLOSE_NOTE}"})
        readback = parse_issue_payload(updated, self.config["labels"])
        readback["state"] = updated.get("state", readback.get("state"))
        readback["state_reason"] = updated.get("state_reason")
        return {"published": True, "issue_number": number,
                "close_reason": reason, "state_reason": state_reason,
                "readback": readback, "note": CLOSE_NOTE}

    def publish_drafts(self) -> dict:
        """重放未发布草稿(远端恢复后):逐条按原参数执行,成功即标记已发布;
        仍失败保留草稿。草稿在发布前始终标明「未发布」。

        草稿重放的存储、跨仓库归属拒绝与完成判定自票 20 起收敛在
        ``mgs_result_publication.publish_drafts``(与在线失败时的草稿保存同一
        恢复事实);本 adapter 只注入目标仓库标签、缓存目录与动作分发。
        """

        return mgs_result_publication.publish_drafts(
            cache_dir=self.cache_dir, repo=repo_str(self.repo),
            execute=self.execute_op, note=DRAFT_NOTE)

    def execute_op(self, op: str, args: dict) -> dict:
        """按操作名把参数分发到对应写操作(公开接缝)。

        在线执行(运行时受控通道 mgs_remote)与草稿重放(publish_drafts)
        共用这同一份动作参数分发(第二轮复审 ST-1 判断性建议的采纳:
        参数行为不再两处维护,一条路径上的参数语义变更两路同时生效)。
        未登记的操作名按错误拒绝,不猜测执行。
        """

        if op == "create_task":
            return self.create_task(
                str(args["identity"]), str(args.get("title", "")),
                dict(args.get("request") or {}),
                triage=str(args.get("triage", "needs-triage")),
                progress=str(args.get("progress", "待执行")))
        if op == "update_task":
            return self.update_task(
                str(args["identity"]), dict(args.get("fields") or {}),
                expected_body_sha256=args.get("expected_body_sha256"),
                change_note=str(args.get("change_note", "安排更新")))
        if op == "set_triage":
            return self.set_triage(str(args["identity"]), str(args.get("label")))
        if op == "append_result":
            return self.append_result(str(args["identity"]),
                                      str(args.get("result_markdown", "")))
        if op == "set_relations":
            return self.set_relations(str(args["identity"]),
                                      list(args.get("deps") or []))
        if op == "set_parent":
            return self.set_parent(str(args["identity"]), args.get("parent"))
        if op == "claim_task":
            return self.claim_task(str(args["identity"]), str(args.get("actor")))
        if op == "close_task":
            return self.close_task(str(args["identity"]), str(args.get("reason")),
                                   note=str(args.get("note", "")))
        raise GithubRecordsError(f"unknown op {op}")

# ---------- 后端切换与远端交接(兼容再导出,票 20) ----------
# 迁移清单、切换执行与交接基线可达核对的实现归独立职责 module
# mgs_github_migration(仅此职责,见其头部);本 adapter 保持既有公开名字
# 可达(现有 CLI、脚本与测试经 mgs_github 定位这些入口),以模块级
# __getattr__ 延迟解析——避免适配器与迁移模块在加载期相互导入(迁移模块
# 延迟导入本适配器的 GithubBackend 完成目标侧创建)。

_MIGRATION_EXPORTS = ("plan_backend_switch", "apply_backend_switch",
                      "handover_baseline_check")


def __getattr__(name: str):
    if name in _MIGRATION_EXPORTS:
        import mgs_github_migration  # noqa: PLC0415 - 兼容再导出

        return getattr(mgs_github_migration, name)
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")

"""MyGameStudio 运行保障:受控远端任务操作的完整事务(任务票 22 新增)。

本模块集中「一次受控远端任务操作」的完整不变量,调用方(mgs-gate 通道经
``GateService.remote_record``)不再自行拼接检查、意图记录、执行与结果审计:

- 远端通道与项目 CONFIG:通道配置(runtime_root/remote.json)读取与结构
  校验;项目 CONFIG 后端类型、仓库目标与仓库级 issues-write 授权核对
  (remote_scope,选择后端不等于授权)。
- 授权交集:任务授权 ∩ 角色范围 ∩ 用途(用途条目缺失失效闭合),与本地
  写入共用同一份策略解释实现(``mgs_local_write.grant_denial``);远端资源
  的匹配差异(集合资源 github://…/issues 由 …/issues/** 类授权涵盖)经
  ``remote_match`` 匹配器参数保留。资源粒度:集合 / 单任务正文 / 单任务评论。
- 完整远端事务:锁外快速预检只用于尽早拒绝;最终身份、策略、项目 CONFIG 与
  授权交集核对,写入意图的持久记录,远端动作执行与结果审计都在同一服务锁
  临界区内完成(与本地 write 同一临界区纪律)。撤销(release_instance)与
  策略更换持同一把锁,撤销完成后在途远端写入在锁内重读时被拒,不可能执行。
- 结果表达:上游不可用失效闭合(remote_upstream,不绕行直连;缓存目录可用
  时保存未发布草稿并在结果中回报);只读动作(read)不要求意图记录;结果
  未确认(uncertain)、部分成功(partial)与未发布草稿如实区分,不虚报成功、
  不包装成拒绝(R4)。写入意图先于执行持久记录,意图审计不可用时动作不执行
  (失效闭合);结果审计追加失败时如实回报已发生的远端结果并标注未记录。

状态访问(执行登记、策略、审计与唯一服务锁)由宿主门面 ``GateService`` 委派
给 ``mgs_gate_registry.py``;本模块经宿主门面的既有私有状态接缝调用这些访问,
使既有单行委派接缝(故障注入点)继续可用。本模块只依赖 Python 标准库与
``records/`` 下的 GitHub 后端适配器(按需导入,不落盘凭据)。
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

from mgs_local_write import grant_denial, match_any

REMOTE_ACTIONS = {
    # action → 资源粒度(issues 集合 / 单任务正文 / 单任务评论)
    "read": "collection", "create": "collection",
    "update": "task", "set-triage": "task", "set-relations": "task",
    "set-parent": "task", "close": "task",
    "append-result": "comments",
}

# action → 后端适配器的动作名(在线执行与草稿重放共用后端的同一份参数分发)。
_OP_FOR_ACTION = {
    "create": "create_task", "update": "update_task",
    "set-triage": "set_triage", "set-relations": "set_relations",
    "set-parent": "set_parent", "close": "close_task",
    "append-result": "append_result", "read": "read",
}


def remote_summary(result: dict) -> str:
    """远端操作结果的一句话摘要(进审计 note,不含凭据)。"""

    keys = ("created", "adopted", "issue_number", "published", "uncertain",
            "partial", "index_updated", "comment_id", "close_reason",
            "state_reason", "draft")
    return ",".join(f"{key}={result[key]}" for key in keys if key in result) \
        or "ok"


def remote_match(patterns: list[str], resource: str) -> bool:
    """远端资源授权匹配:直接命中,或被「本资源及其子树」的 ** 授权覆盖
    (集合资源 github://…/issues 由 …/issues/** 类授权涵盖,任务票 17)。

    与本地路径匹配的差异只在这一点;授权交集的规则与拒绝阶段由
    ``mgs_local_write.grant_denial`` 共用同一实现(任务票 22)。
    """

    return (match_any(patterns, resource)
            or match_any(patterns, resource + "/**"))


def remote_grant_denial(record: dict, policy: dict,
                        resource: str) -> tuple[str, str] | None:
    """远端资源的任务 ∩ 角色 ∩ 用途授权核对(共用 grant_denial)。

    返回 (rule_stage, reason) 或 None(放行);用途条目缺失时与本地写入
    同一语义失效闭合(R2)。任务授权失败的说明措辞用 "remote resource"。
    """

    return grant_denial(record, policy, resource, matcher=remote_match,
                        noun="remote resource")


def _records_modules():
    """按需导入 records/ 下的 GitHub 后端适配器(既有 sys.path 接缝)。"""

    sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "records"))
    import mgs_github  # noqa: PLC0415
    import mgs_records  # noqa: PLC0415

    return mgs_github, mgs_records


class RemoteWriteTransaction:
    """完整受控远端任务操作职责:授权、意图、执行与结果审计的唯一入口。

    经宿主门面(GateService)访问执行登记、策略、审计与服务锁,使既有
    接缝继续可用;门面自身不再拼装检查、意图、执行与结果审计步骤。
    """

    def __init__(self, host) -> None:
        self._host = host

    def channel(self) -> dict | None:
        """读取远端通道配置(可信调度侧维护的 runtime_root/remote.json)。

        {"github": {"api_base": ..., "token_env": ..., "cache_dir": ...}}
        凭据只经 token_env 指定的环境变量读取,不落盘、不进项目记录。
        缺失或结构无效返回 None(调用方失效闭合)。
        """

        path = self._host.runtime_root / "remote.json"
        if not path.is_file():
            return None
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            channel = data.get("github")
        except (OSError, ValueError):
            return None
        if not isinstance(channel, dict) or not channel.get("api_base") \
                or not channel.get("token_env"):
            return None
        return channel

    def base(self, op: str, record: dict, policy: dict, resource: str,
             note: dict) -> dict:
        """远端操作结果/意图条目与审计记录共用的身份与依据字段组。"""

        return {
            "op": op, "instance_id": record["instance_id"],
            "task": record["task"], "role": record["role"],
            "purpose": record["purpose"], "target": resource,
            "basis": self._host._basis(policy), "note": note,
        }

    def config_state(self, policy: dict, config_rel: str, action: str,
                     payload: dict) -> tuple[dict | None, str, dict,
                                             tuple[str, str] | None]:
        """读取项目 CONFIG 并核对远端通道适用性与仓库级授权(SP-1)。

        返回 (config, resource, note, denial):denial 非 None 时为
        (rule_stage, reason),其余返回值无意义;否则 config 为本次读到的
        配置,resource/note 按其仓库目标构造。锁外调用只做快速预检;
        最终临界区内再次调用——CONFIG 后端/授权经正常入口被撤销或变更后,
        在途远端请求以锁内重读的结果拒绝,并据此构建 backend(records
        合同:创建或修改远端记录前核对明确的仓库及操作授权)。
        """

        mgs_github, mgs_records = _records_modules()

        project_root = Path(policy["project_root"])
        try:
            config = mgs_records.load_config(project_root, config_rel)
        except mgs_records.RecordsError as exc:
            return None, "", {}, ("remote_scope",
                                  f"项目协作配置不可读:{exc}")
        if config["backend"] != "github-issues" or not config.get("repo"):
            return None, "", {}, (
                "remote_scope",
                f"项目任务后端为 {config['backend']!r},远端通道仅服务 "
                "github-issues 后端项目")
        repo = config["repo"]
        allowed, auth_note = mgs_github._authorization_for(
            config, "issues-write")
        if not allowed:
            return None, "", {}, ("remote_scope", auth_note)
        identity = str(payload.get("identity") or "")
        granularity = REMOTE_ACTIONS[action]
        base = f"github://{repo['host']}/{repo['owner']}/{repo['repo']}/issues"
        if granularity == "collection":
            resource = base
        else:
            if not identity:
                return None, "", {}, ("channel", "缺少 identity")
            resource = (f"{base}/{identity}" if granularity == "task"
                        else f"{base}/{identity}/comments")
        note = {"action": action,
                "repo": f"{repo['host']}/{repo['owner']}/{repo['repo']}"}
        return config, resource, note, None

    @staticmethod
    def run_action(backend, action: str, payload: dict) -> dict:
        if action == "read":
            return {"published": True,
                    "task": backend.read_task(str(payload["identity"]))}
        # 其余动作与草稿重放共用后端的同一份参数分发(ST-1:在线执行与
        # 重放不再各自维护动作参数,语义变更两路同时生效)
        return backend.execute_op(_OP_FOR_ACTION.get(action, action), payload)

    def _settle_outcome(self, outcome: dict, result: dict, note: dict) -> None:
        """R4:结果审计追加失败不否认已发生的远端结果。

        如实回报并标注未记录(调用方不误判重试),也不静默丢弃记录责任;
        意图条目已持久,可据此对账缺失的结果记录。
        """

        try:
            entry = {key: value for key, value in outcome.items()
                     if key != "result"}
            entry["note"] = {"summary": remote_summary(result), **note}
            self._host._audit_unlocked(entry)
        except Exception as exc:
            outcome["audit_recorded"] = False
            outcome["reason"] += (
                f"; outcome audit append failed "
                f"({type(exc).__name__}: {exc}) — result "
                "reported as-is, not wrapped as denial")

    def record(self, token: str, action: str, payload: dict, *,
               transport=None) -> dict:
        """受控远端任务操作入口(工作实例在会话内经 mgs-gate 提交)。

        逐次校验:凭据(身份)→ 远端通道配置(channel)→ 项目 CONFIG 后端
        与仓库级 issues-write 授权(remote_scope)→ 任务授权(task_grant)
        → 角色范围(role_scope)→ 用途(purpose),全通过后才经适配器执行;
        CONFIG 读取与授权核对在锁外快速预检后,于最终临界区内重读复核并
        据此构建 backend(SP-1:授权撤销覆盖在途请求)。上游不可用失效
        闭合(remote_upstream,不绕行直连;缓存目录可用时由适配器保存
        未发布草稿并在结果中回报)。允许与拒绝都进审计。
        写入意图先于执行持久记录,审计不可用则动作不执行;结果审计失败时
        如实回报已发生的远端结果(R4)。
        """

        host = self._host
        op = f"remote:{action}"
        policy = host._policy()
        if policy is None:
            return host._deny(op, "policy",
                              "runtime policy missing, corrupt or malformed "
                              "(fail closed)", token, None, {}, action)
        record, reason = host._resolve_instance(token)
        if record is None:
            return host._deny(op, "identity", reason, token, None, policy, action)
        if action not in REMOTE_ACTIONS:
            return host._deny(op, "channel", f"unknown remote action {action!r}",
                              token, record, policy, action)
        channel = self.channel()
        if channel is None:
            return host._deny(
                op, "channel",
                "remote channel config missing or malformed "
                "(runtime_root/remote.json; fail closed)",
                token, record, policy, action)

        mgs_github, mgs_records = _records_modules()

        config_rel = str(payload.get("config_rel") or mgs_records.DEFAULT_CONFIG_REL)
        # 锁外快速预检(SP-1):尽早拒绝不可用请求;最终判定以临界区内
        # 重读的 CONFIG 为准(见下),此处读到的 config 不再沿用,backend
        # 也只在锁内按重读结果构建。
        config, resource, note, config_denial = self.config_state(
            policy, config_rel, action, payload)
        if config_denial is not None:
            return host._deny(op, config_denial[0], config_denial[1],
                              token, record, policy, action)
        grant = remote_grant_denial(record, policy, resource)
        if grant is not None:
            return host._deny(op, grant[0], grant[1],
                              token, record, policy, resource)

        env_token = os.environ.get(channel["token_env"], "").strip()
        active_transport = transport or mgs_github.UrllibTransport(
            api_base=channel["api_base"], token=env_token or None)

        # R1/R4:与本地 write() 同一临界区纪律——最终身份、策略与授权核对、
        # 写入意图的持久记录、远端动作的执行与结果审计都持有服务锁完成。
        # 撤销(release_instance)与策略更换同样持有本锁:撤销完成后在途
        # 远端写入在锁内重读时被拒,不可能执行;远端动作因此与同运行根的
        # 本地写入串行,占锁时长受传输超时约束(不无限持有)。
        # R4:改变远端状态的写入意图先于执行持久记录,审计不可用时动作不
        # 执行(失效闭合);只读动作(read)不改变远端状态,不要求意图记录。
        # SP-1:项目 CONFIG(后端类型、仓库目标、issues-write 授权)同样在
        # 临界区内重读——CONFIG 经正常 write 入口被撤销后,锁前已读过旧
        # 授权的在途请求在锁内重读时被拒(remote_scope),backend 也按锁内
        # 读到的 CONFIG 构建,不沿用锁外快照(R1 修身份撤销,本条补齐
        # CONFIG 授权撤销的同一最终检查)。
        denial: tuple[str, str, dict | None] | None = None
        outcome: dict | None = None
        with host._locked():
            record, reason = host._resolve_instance(token)
            if record is None:
                denial = ("identity", reason, None)
            if denial is None:
                policy = host._policy()
                if policy is None:
                    denial = ("policy", "runtime policy missing, corrupt or "
                              "malformed (fail closed)", None)
            if denial is None:
                config, resource, note, config_denial = self.config_state(
                    policy, config_rel, action, payload)
                if config_denial is not None:
                    denial = (config_denial[0], config_denial[1], None)
            if denial is None:
                grant = remote_grant_denial(record, policy, resource)
                if grant is not None:
                    denial = (grant[0], grant[1], None)
            if denial is None:
                backend = mgs_github.GithubBackend(
                    config, active_transport, channel.get("cache_dir"))
            if denial is None and action != "read":
                try:
                    host._audit_unlocked({
                        **self.base(op, record, policy, resource, note),
                        "decision": "intent", "rule_stage": "granted",
                        "reason": "remote write intent recorded before execution",
                    })
                except Exception as exc:
                    denial = ("audit",
                              f"cannot durably record remote write intent "
                              f"({type(exc).__name__}: {exc}); remote action "
                              "not executed (fail closed)", None)
            if denial is None:
                try:
                    result = self.run_action(backend, action, payload)
                except mgs_github.TransportError as exc:
                    # 上游故障:失效闭合;适配器已在可用缓存目录保存未发布
                    # 草稿的操作由各动作内部处理,这里经后端**公开**草稿接缝
                    # 兜底离线草稿(不直接依赖后端私有草稿保存细节,票 20)
                    draft = None
                    if exc.kind == "offline" and channel.get("cache_dir"):
                        draft = backend.record_unpublished_draft(
                            _OP_FOR_ACTION.get(action, action),
                            dict(payload), str(exc))
                    denial = ("remote_upstream",
                              f"remote upstream unavailable (fail closed): {exc}",
                              {"draft": draft} if draft else None)
                except mgs_github.GithubRecordsError as exc:
                    denial = ("remote_upstream", str(exc), None)
                else:
                    if result.get("uncertain"):
                        # S2:远端动作已执行但结果未确认(请求超时且回读失败,
                        # 适配器已停止重发)——如实回报不确定,不虚报成功,
                        # 也不包装成拒绝或「已保存草稿」;调用方应先回读确认
                        # 再决定是否重试(R4 同一原则:不把已发生的远端结果
                        # 包装成未执行的拒绝)。
                        outcome = {
                            **self.base(op, record, policy, resource, note),
                            "decision": "uncertain", "rule_stage": "granted",
                            "reason": ("remote action executed but outcome "
                                       "unconfirmed (readback failed; resend "
                                       "stopped to avoid duplication)"),
                            "result": result,
                        }
                    elif not result.get("published", True) \
                            and not result.get("created"):
                        # 适配器保存了草稿(离线):按未发布表达,不冒充已发布
                        denial = ("remote_upstream",
                                  "远端不可用:已保存未发布草稿(标明来源与状态;"
                                  "不视为已发布,不静默切换本地后端)",
                                  {"draft": result.get("draft")})
                    else:
                        outcome = {
                            **self.base(op, record, policy, resource, note),
                            "decision": "allow", "rule_stage": "granted",
                            "reason": "granted by identity+task+role+purpose+"
                                      "config-scope intersection",
                            "result": result,
                        }
                        if result.get("partial"):
                            # SP-2:部分成功如实回报——已发布的部分(评论身份)
                            # 与未完成的部分(结果索引)都在 result 中表达,
                            # 不包装成整体成功,也不包装成整体拒绝
                            outcome["reason"] += (
                                "; partial success: published part carried in "
                                "result with its incomplete part (retry the "
                                "same request to complete only what remains)")
                    if outcome is not None:
                        self._settle_outcome(outcome, result, note)
        if denial is not None:
            return host._deny(op, denial[0], denial[1], token, record, policy,
                              resource, note=denial[2])
        return outcome

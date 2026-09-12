"""MyGameStudio 运行保障:受控写入服务门面(任务票 02 建立,任务票 03 加固)。

本模块是受控写入的公开接缝(工作实例入口与可信调度侧操作)与受控远端
任务操作的所在;内部职责自任务票 21 起集中拆分:

- ``mgs_gate_registry.py`` —— 执行登记与策略状态(策略、实例登记、占用、
  审计、唯一服务锁)。撤销、签发、回收与写入因此共用同一把锁。
- ``mgs_local_write.py`` —— 本地受控写入的完整事务:策略解释、路径身份、
  字节落盘、版本/占用/竞态复检与回滚;锁前预检与锁内最终核对不再由调用方
  拼接。

``GateService`` 保持既有公开方法(normalize 为 ``write`` / ``scope`` /
``remote_record`` 与调度侧 ``init_policy`` / ``create_instance`` /
``release_instance`` / ``list_locks`` / ``reclaim_locks``)与既有私有状态接缝
(``_locked`` / ``_read_json`` / ``_write_json`` / ``_policy`` /
``_resolve_instance`` / ``_audit_unlocked``);写入占用另经
``_occupancy_conflict`` / ``_occupy`` 收拢到登记职责(占用条目形状不外泄)。
上述接缝均经登记职责委派,既有回归(含故障注入)语义不变。

职责说明(原始合同):

- 执行绑定:create_instance 由可信调度侧调用,签发一次性执行凭据(令牌);
  令牌只以哈希形式落盘,身份、任务、用途、有效期与撤销状态由登记记录决定。
- 资源策略:写入目标必须同时落入「角色允许范围 ∩ 任务授权 ∩ 执行用途 ∩
  实际授权」;工具参数中的自报身份文本不参与授权。
- 调度与占用:同一资源同一时间只允许一个活跃实例写入;占用按规范化后的
  实际资源标识协调(别名、链接与相对路径写法不改变占用键)。
- 结果核对:每次 scope/write(无论允许或拒绝)都追加可定位审计记录。

任务票 03 增加的失效闭合与竞态防护:
- 策略缺失、损坏或结构无效时,scope/write 一律拒绝(rule_stage=policy),
  不抛异常、不触碰目标字节;策略恢复后同一服务继续可用;
- 写入目标在解析后、落盘前被换链(父目录或目标本身变成指向别处的符号链接)
  属可复现路径竞态,占用与版本校验之后、落盘之前做路径复检,发现即拒绝
  (rule_stage=race);目标非普通文件(管道/目录等)同样拒绝;
- 落盘后的占用登记或审计追加失败时,已写入字节回滚并拒绝(rule_stage=audit),
  保证「无审计则无生效写入」;拒绝路径的审计追加失败不影响拒绝结果。

任务票 15 增加的占用回收(list_locks/reclaim_locks,可信调度侧):
- 失联、崩溃或任务到期后,先撤销旧实例的执行能力(release_instance 或等
  有效期过去),再回收其遗留占用,新执行者方可接管;
- 仍然活跃的实例(未释放且未过期)的占用不可回收——单写入者不因回收被打破;
- 逐次写入都重新校验凭据:持续存活的进程在旧授权失效(释放或到期)后
  不能凭旧令牌或旧占用记录继续写入;
- 该接缝同时覆盖 release 流程中断在登记与占用两次落盘之间留下的
  「已释放但仍持有占用」缺口。

审查修复批(2026-09-09,R1–R4):
- 撤销语义(R1):write 的最终身份、策略与授权交集核对移入服务锁
  临界区,与写入同一临界区完成;撤销完成后任何在途写入一律拒绝;
- 用途故障闭合(R2):用途条目缺失 ≠ 显式不额外限制——条目缺失或
  形状无效时交集不可计算,按用途拒绝;策略条目形状无效按策略不完整
  拒绝;write/scope/远端路径使用同一语义;
- 权限位保留(R3):内容更新(含回滚路径)保留已有目标的权限位,
  权限变化必须经显式操作,不经内容更新隐式发生;
- 远端审计时序(R4):远端写入意图先于执行持久记录,审计不可用则
  动作不执行(失效闭合);结果审计追加失败时如实回报已发生的远端
  结果并标注未记录,不包装成未执行的拒绝,也不静默丢弃记录责任。

第二轮审查修复批(2026-09-09,review2-01/SP-1):
- 远端在途授权缺口:remote_record 的项目 CONFIG 后端/仓库目标与
  issues-write 授权核对、backend 构建移入最终服务锁临界区——CONFIG
  授权经正常入口被撤销后,锁前已读过旧授权的在途请求在锁内重读时
  以 remote_scope 拒绝,不可能再写入远端(与 R1 的身份撤销同一纪律)。

第二轮审查修复批(2026-09-09,review2-02/SP-2、ST-1):
- 远端部分成功如实回报:适配器对「评论已发布而结果索引更新未完成」
  返回携带已发布评论身份与未完成状态的 partial 结果,通道按 allow
  如实转发(附部分成功说明),不再整体包装成 deny/remote_upstream;
  重试经读前收养只补索引,不重复发布。
- 在线执行与草稿重放共用后端 execute_op 的同一份动作参数分发,
  参数语义不再两处维护。

本模块与两个内部职责模块只依赖 Python 标准库。MCP 通道与调度 CLI 是它的
两个入口。
"""

from __future__ import annotations

import json
import os
import secrets
import sys
import time
from dataclasses import dataclass
from pathlib import Path

from mgs_gate_registry import POLICY_FILE, GateRegistry, sha256_text
from mgs_local_write import (
    PURPOSE_MISSING,
    LocalWriteTransaction,
    match_any,
    purpose_missing_reason,
    purpose_restrict,
    role_patterns,
)


@dataclass
class Instance:
    instance_id: str
    token: str
    role: str
    task: str
    purpose: str
    resources: list[str]
    created_at: float
    expires_at: float
    released: bool = False


def _remote_summary(result: dict) -> str:
    """远端操作结果的一句话摘要(进审计 note,不含凭据)。"""

    keys = ("created", "adopted", "issue_number", "published", "uncertain",
            "partial", "index_updated", "comment_id", "close_reason",
            "state_reason", "draft")
    return ",".join(f"{key}={result[key]}" for key in keys if key in result) \
        or "ok"


def _token_fingerprint(token: str) -> str:
    return sha256_text(token)[:12]


def _remote_match(patterns: list[str], resource: str) -> bool:
    """远端资源授权匹配:直接命中,或被「本资源及其子树」的 ** 授权覆盖
    (集合资源 github://…/issues 由 …/issues/** 类授权涵盖,任务票 17)。"""

    return (match_any(patterns, resource)
            or match_any(patterns, resource + "/**"))


class GateService:
    """受控写入服务门面。所有公开方法都是接缝:调度侧与工作实例侧分别使用。

    状态访问委派给执行登记职责(mgs_gate_registry),本地写入委派给完整
    本地事务职责(mgs_local_write);远端任务操作保留在本门面(其内部整理的
    独立票不改变本票的共享锁与语义)。
    """

    def __init__(self, runtime_root: Path | str) -> None:
        self.runtime_root = Path(runtime_root).resolve()
        self._registry = GateRegistry(self.runtime_root)
        self._local = LocalWriteTransaction(self)

    # ---------- 内部:状态接缝(经执行登记职责) ----------

    def _locked(self):
        return self._registry.locked()

    def _read_json(self, name: str, default):
        return self._registry.read_json(name, default)

    def _write_json(self, name: str, data) -> None:
        self._registry.write_json(name, data)

    def _occupancy_conflict(self, rel: str, instance_id: str) -> str | None:
        """本资源的写入占用是否与给定实例冲突(经执行登记职责,占用条目
        形状不外泄)。

        占用判定与登记分别经本方法与 ``_occupy`` 委派给执行登记职责,替代
        原先由写入事务直接读写的 ``_read_json`` / ``_write_json``;后两者
        仍保留给既有直连调用方与故障注入,注入点语义不变。
        """

        return self._registry.occupancy_conflict(rel, instance_id)

    def _occupy(self, rel: str, instance_id: str) -> None:
        """登记本资源由实例持有写入占用(调用方须已持锁;经执行登记职责)。"""

        self._registry.occupy(rel, instance_id)

    def _policy(self) -> dict | None:
        """读取资源策略;缺失、损坏或结构无效(含角色/用途条目形状无效,
        R2)时返回 None(调用方必须失效闭合)。"""

        return self._registry.read_policy()

    def _audit(self, entry: dict) -> None:
        with self._locked():
            self._audit_unlocked(entry)

    def _audit_unlocked(self, entry: dict) -> None:
        """追加审计记录。调用方必须已持有服务锁(或经由 _audit 获取)。"""

        self._registry.append_audit_unlocked(entry)

    def _resolve_instance(self, token: str) -> tuple[dict | None, str]:
        """凭据 → 活跃实例登记。返回 (登记或 None, 拒绝原因)。"""

        return self._registry.resolve_instance(token)

    def list_instances(self) -> list:
        """回读执行登记(可信调度侧状态查看)。"""

        return self._registry.instances()

    # ---------- 可信调度侧 ----------

    def init_policy(self, project_root: Path | str, roles: dict[str, list[str]],
                    purposes: dict[str, list[str] | None]) -> dict:
        """写入资源策略。策略维护通道:仅由可信调度侧(本方法/管理 CLI)调用。"""

        policy = {
            "version": 1,
            "project_root": str(Path(project_root).resolve()),
            "roles": {role: {"resources": pats} for role, pats in roles.items()},
            "purposes": {name: {"restrict": pats} for name, pats in purposes.items()},
        }
        self._registry.write_policy(policy)
        self._audit({
            "op": "policy/init", "decision": "record", "rule_stage": "admin",
            "reason": "policy written via trusted scheduler channel",
            "instance_id": None, "task": None, "role": "scheduler",
            "purpose": None, "target": POLICY_FILE, "note": None,
            "basis": {"channel": "trusted scheduler CLI (mgsrt_admin.py)"},
        })
        return policy

    def create_instance(self, role: str, task: str, purpose: str,
                        resources: list[str], ttl_seconds: int = 1800) -> Instance:
        """绑定一个执行实例。令牌仅在返回值中出现一次,登记只存哈希。"""

        now = time.time()
        instance = Instance(
            instance_id="i-" + secrets.token_hex(6),
            token=secrets.token_hex(32),
            role=role,
            task=task,
            purpose=purpose,
            resources=list(resources),
            created_at=now,
            expires_at=now + ttl_seconds,
        )
        self._registry.add_instance(self._instance_record(instance))
        self._audit({
            "op": "instance/create", "decision": "record", "rule_stage": "admin",
            "reason": "execution binding issued by trusted scheduler",
            "instance_id": instance.instance_id, "task": task, "role": role,
            "purpose": purpose, "target": None, "note": {"resources": list(resources)},
            "basis": {"channel": "trusted scheduler CLI (mgsrt_admin.py)"},
        })
        return instance

    @staticmethod
    def _instance_record(instance: Instance) -> dict:
        return {
            "instance_id": instance.instance_id,
            "token_hash": sha256_text(instance.token),
            "role": instance.role,
            "task": instance.task,
            "purpose": instance.purpose,
            "resources": instance.resources,
            "created_at": instance.created_at,
            "expires_at": instance.expires_at,
            "released": instance.released,
        }

    def release_instance(self, instance_id: str) -> dict:
        """结束实例:撤销凭据并释放其全部写入占用。"""

        found = self._registry.release(instance_id)
        if found:
            self._audit({
                "op": "instance/release", "decision": "record", "rule_stage": "admin",
                "reason": "execution binding revoked by trusted scheduler",
                "instance_id": instance_id, "task": None, "role": "scheduler",
                "purpose": None, "target": None, "note": None,
                "basis": {"channel": "trusted scheduler CLI (mgsrt_admin.py)"},
            })
        return {"released": instance_id, "found": found}

    def list_locks(self) -> dict:
        """回读当前写入占用(可信调度侧核对用)。"""

        return {"locks": self._registry.locks()}

    def reclaim_locks(self, instance_id: str) -> dict:
        """回收一个旧实例遗留的写入占用(任务票 15)。

        顺序约束(运行保障合同「执行结束释放占用」):先撤销旧执行能力
        (release_instance,或等待有效期过去),再回收占用。实例仍然活跃
        (未释放且未过期)时拒绝回收——单写入者不因回收被打破;实例已不能
        写入(released 或已过期)时,删除其全部占用记录,允许新执行者接管。
        该接缝同时覆盖 release 流程中断在登记与占用两次落盘之间留下的
        「已释放但仍持有占用」缺口。
        """

        result = self._registry.reclaim_locks(instance_id)
        self._audit({
            "op": "locks/reclaim",
            "decision": "record" if result["ok"] else "deny",
            "rule_stage": "admin",
            "reason": result["reason"],
            "instance_id": instance_id, "task": None, "role": "scheduler",
            "purpose": None, "target": None,
            "note": {"reclaimed": result["reclaimed"]},
            "basis": {"channel": "trusted scheduler CLI (mgsrt_admin.py)"},
        })
        return result

    # ---------- 工作实例侧 ----------

    def scope(self, token: str) -> dict:
        """回读本凭据的有效可写范围(角色 ∩ 任务 ∩ 用途)。"""

        return self._local.scope(token)

    @staticmethod
    def _basis(policy: dict) -> dict:
        return {
            "policy_version": policy.get("version"),
            "role_resources_source": "runtime policy.json (trusted scheduler channel)",
            "task_grant_source": "instance registry issued by trusted scheduler",
        }

    def write(self, token: str, path: str, content: str = "",
              expected_sha256: str | None = None, note: str | None = None,
              *, data: bytes | None = None) -> dict:
        """受控写入入口。任何拒绝都不触碰目标字节;检查器故障一律失效闭合。

        载荷二选一:`content`(UTF-8 文本,沿用任务票 02 语义)或
        `data`(原始字节,任务票 11 起供音频等二进制资源使用)。
        两者语义一致——同一授权交集、同一字节级版本校验与审计;
        通道层(mcp_gate)负责校验调用方恰提供其一。

        临界区时序(R1):锁外预检只用于快速拒绝;最终的身份有效性、
        策略与授权交集核对和写入本身在同一服务锁临界区内完成——撤销
        (release_instance)与策略更换都持有本锁,撤销完成后在途写入
        必然在锁内重读时被拒,不可能再落盘。完整顺序集中在
        mgs_local_write.LocalWriteTransaction。
        """

        return self._local.write(token, path, content, expected_sha256, note,
                                 data=data)

    def _deny(self, op: str, rule_stage: str, reason: str, token: str,
              record: dict | None, policy: dict, path: str,
              note: dict | str | None = None) -> dict:
        result = {
            "op": op,
            "decision": "deny",
            "reason": reason,
            "rule_stage": rule_stage,
            "instance_id": (record or {}).get("instance_id"),
            "task": (record or {}).get("task"),
            "role": (record or {}).get("role"),
            "purpose": (record or {}).get("purpose"),
            "target": path or None,
            "basis": self._basis(policy),
            "note": note,
        }
        if record is None:
            # 身份失败:记录令牌指纹,不记录原始令牌
            result["token_fp"] = _token_fingerprint(token) if token else None
        try:
            self._audit(result)
        except Exception:
            # 拒绝结果本身已失效闭合;审计不可用不应把拒绝变成崩溃
            pass
        return result

    # ---------- 受控远端任务操作(任务票 17:mgs_remote) ----------

    REMOTE_ACTIONS = {
        # action → 资源粒度(issues 集合 / 单任务正文 / 单任务评论)
        "read": "collection", "create": "collection",
        "update": "task", "set-triage": "task", "set-relations": "task",
        "set-parent": "task", "close": "task",
        "append-result": "comments",
    }

    def _remote_channel(self) -> dict | None:
        """读取远端通道配置(可信调度侧维护的 runtime_root/remote.json)。

        {"github": {"api_base": ..., "token_env": ..., "cache_dir": ...}}
        凭据只经 token_env 指定的环境变量读取,不落盘、不进项目记录。
        缺失或结构无效返回 None(调用方失效闭合)。
        """

        path = self.runtime_root / "remote.json"
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

    def _remote_base(self, op: str, record: dict, policy: dict,
                     resource: str, note: dict) -> dict:
        """远端操作结果/意图条目与审计记录共用的身份与依据字段组。"""

        return {
            "op": op, "instance_id": record["instance_id"],
            "task": record["task"], "role": record["role"],
            "purpose": record["purpose"], "target": resource,
            "basis": self._basis(policy), "note": note,
        }

    def _remote_grant_denial(self, record: dict, policy: dict,
                             resource: str) -> tuple[str, str] | None:
        """远端资源的任务 ∩ 角色 ∩ 用途授权核对(_remote_match 语义)。

        返回 (rule_stage, reason) 或 None(放行);用途条目缺失时与本地
        写入同一语义失效闭合(R2)。
        """

        if not _remote_match(record.get("resources", []), resource):
            return ("task_grant",
                    f"remote resource not granted to task "
                    f"{record['task']}: {resource}")
        if not _remote_match(role_patterns(policy, record["role"]), resource):
            return ("role_scope",
                    f"role {record['role']} may not write: {resource}")
        restrict = purpose_restrict(policy, record["purpose"])
        if restrict is PURPOSE_MISSING:
            return ("purpose", purpose_missing_reason(record["purpose"]))
        if restrict is not None and not _remote_match(restrict, resource):
            return ("purpose",
                    f"purpose {record['purpose']} restricted to "
                    f"{restrict}: {resource}")
        return None

    def _remote_config_state(self, policy: dict, config_rel: str,
                             action: str,
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

        sys.path.insert(0, str(Path(__file__).resolve().parent.parent
                               / "records"))
        import mgs_github  # noqa: PLC0415
        import mgs_records  # noqa: PLC0415

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
        granularity = self.REMOTE_ACTIONS[action]
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

    def remote_record(self, token: str, action: str, payload: dict,
                      *, transport=None) -> dict:
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

        op = f"remote:{action}"
        policy = self._policy()
        if policy is None:
            return self._deny(op, "policy",
                              "runtime policy missing, corrupt or malformed "
                              "(fail closed)", token, None, {}, action)
        record, reason = self._resolve_instance(token)
        if record is None:
            return self._deny(op, "identity", reason, token, None, policy, action)
        if action not in self.REMOTE_ACTIONS:
            return self._deny(op, "channel", f"unknown remote action {action!r}",
                              token, record, policy, action)
        channel = self._remote_channel()
        if channel is None:
            return self._deny(
                op, "channel",
                "remote channel config missing or malformed "
                "(runtime_root/remote.json; fail closed)",
                token, record, policy, action)

        sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "records"))
        import mgs_github  # noqa: PLC0415
        import mgs_records  # noqa: PLC0415

        config_rel = str(payload.get("config_rel") or mgs_records.DEFAULT_CONFIG_REL)
        # 锁外快速预检(SP-1):尽早拒绝不可用请求;最终判定以临界区内
        # 重读的 CONFIG 为准(见下),此处读到的 config 不再沿用,backend
        # 也只在锁内按重读结果构建。
        config, resource, note, config_denial = self._remote_config_state(
            policy, config_rel, action, payload)
        if config_denial is not None:
            return self._deny(op, config_denial[0], config_denial[1],
                              token, record, policy, action)
        grant = self._remote_grant_denial(record, policy, resource)
        if grant is not None:
            return self._deny(op, grant[0], grant[1],
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
        with self._locked():
            record, reason = self._resolve_instance(token)
            if record is None:
                denial = ("identity", reason, None)
            if denial is None:
                policy = self._policy()
                if policy is None:
                    denial = ("policy", "runtime policy missing, corrupt or "
                              "malformed (fail closed)", None)
            if denial is None:
                config, resource, note, config_denial = (
                    self._remote_config_state(policy, config_rel, action,
                                              payload))
                if config_denial is not None:
                    denial = (config_denial[0], config_denial[1], None)
            if denial is None:
                grant = self._remote_grant_denial(record, policy, resource)
                if grant is not None:
                    denial = (grant[0], grant[1], None)
            if denial is None:
                backend = mgs_github.GithubBackend(
                    config, active_transport, channel.get("cache_dir"))
            if denial is None and action != "read":
                try:
                    self._audit_unlocked({
                        **self._remote_base(op, record, policy, resource, note),
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
                    result = self._run_remote_action(backend, action, payload)
                except mgs_github.TransportError as exc:
                    # 上游故障:失效闭合;适配器已在可用缓存目录保存未发布
                    # 草稿的操作由各动作内部处理,这里经后端**公开**草稿接缝
                    # 兜底离线草稿(不直接依赖后端私有草稿保存细节,票 20)
                    draft = None
                    if exc.kind == "offline" and channel.get("cache_dir"):
                        draft = backend.record_unpublished_draft(
                            self._op_for_action(action), dict(payload), str(exc))
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
                            **self._remote_base(op, record, policy,
                                                resource, note),
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
                            **self._remote_base(op, record, policy,
                                                resource, note),
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
                        # R4:结果审计追加失败不否认已发生的远端结果——如实
                        # 回报并标注未记录(调用方不误判重试),也不静默丢弃
                        # 记录责任;意图条目已持久,可据此对账缺失的结果记录。
                        try:
                            entry = {key: value for key, value in outcome.items()
                                     if key != "result"}
                            entry["note"] = {"summary": _remote_summary(result),
                                             **note}
                            self._audit_unlocked(entry)
                        except Exception as exc:
                            outcome["audit_recorded"] = False
                            outcome["reason"] += (
                                f"; outcome audit append failed "
                                f"({type(exc).__name__}: {exc}) — result "
                                "reported as-is, not wrapped as denial")
        if denial is not None:
            return self._deny(op, denial[0], denial[1], token, record, policy,
                              resource, note=denial[2])
        return outcome

    @staticmethod
    def _op_for_action(action: str) -> str:
        return {"create": "create_task", "update": "update_task",
                "set-triage": "set_triage", "set-relations": "set_relations",
                "set-parent": "set_parent", "close": "close_task",
                "append-result": "append_result", "read": "read"}.get(
            action, action)

    @staticmethod
    def _run_remote_action(backend, action: str, payload: dict) -> dict:
        if action == "read":
            return {"published": True,
                    "task": backend.read_task(str(payload["identity"]))}
        # 其余动作与草稿重放共用后端的同一份参数分发(ST-1:在线执行与
        # 重放不再各自维护动作参数,语义变更两路同时生效)
        return backend.execute_op(GateService._op_for_action(action), payload)

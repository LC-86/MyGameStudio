"""MyGameStudio 运行保障:受控写入服务门面(任务票 02 建立,任务票 03 加固)。

本模块是受控写入的公开接缝(工作实例入口与可信调度侧操作);内部职责自
任务票 21 起集中拆分,任务票 22 补齐受控远端任务操作:

- ``mgs_gate_registry.py`` —— 执行登记与策略状态(策略、实例登记、占用、
  审计、唯一服务锁)。撤销、签发、回收与写入因此共用同一把锁。
- ``mgs_local_write.py`` —— 本地受控写入的完整事务:策略解释、路径身份、
  字节落盘、版本/占用/竞态复检与回滚;锁前预检与锁内最终核对不由调用方
  拼接。授权交集 ``grant_denial`` 亦为本地与远端共用(票 22)。
- ``mgs_remote_write.py`` —— 受控远端任务操作的完整事务:远端通道与项目
  CONFIG 核对、授权交集(经共享 ``grant_denial`` 与远端匹配器)、锁内最终
  身份/策略/CONFIG/授权复核、写入意图先行、执行与结果审计(票 22)。

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
- 结果核对:每次 scope/write(以及受控远端操作,无论允许或拒绝)都追加
  可定位审计记录。

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

任务票 22 的远端事务集中:``remote_record`` 的完整顺序(通道/CONFIG/授权
交集、锁内重读、意图审计、执行、结果审计与结果表达)集中在
``mgs_remote_write.RemoteWriteTransaction``;门面保留公开方法与既有私有
状态接缝,既有参数、拒绝阶段与共享锁语义不变。

本模块只编排公开接缝与调度侧登记;具体事务与策略解释在登记、本地写入、
远端写入三个内部职责模块中。MCP 通道与调度 CLI 是它的两个入口。
"""

from __future__ import annotations

import secrets
import time
from dataclasses import dataclass
from pathlib import Path

from mgs_gate_registry import POLICY_FILE, GateRegistry, sha256_text
from mgs_local_write import LocalWriteTransaction
from mgs_remote_write import REMOTE_ACTIONS as _REMOTE_ACTIONS
from mgs_remote_write import RemoteWriteTransaction


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


def _token_fingerprint(token: str) -> str:
    return sha256_text(token)[:12]


class GateService:
    """受控写入服务门面。所有公开方法都是接缝:调度侧与工作实例侧分别使用。

    状态访问委派给执行登记职责(mgs_gate_registry),本地写入委派给完整
    本地事务职责(mgs_local_write),受控远端任务操作委派给完整远端事务
    职责(mgs_remote_write);本门面只保留公开方法与既有私有状态接缝
    (故障注入点)。
    """

    def __init__(self, runtime_root: Path | str) -> None:
        self.runtime_root = Path(runtime_root).resolve()
        self._registry = GateRegistry(self.runtime_root)
        self._local = LocalWriteTransaction(self)
        self._remote = RemoteWriteTransaction(self)

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

    # ---------- 受控远端任务操作(任务票 17 建立,任务票 22 集中事务) ----------

    # action → 资源粒度(issues 集合 / 单任务正文 / 单任务评论);保留为
    # 类属性以兼容既有定位(唯一用途定义在 mgs_remote_write)。
    REMOTE_ACTIONS = _REMOTE_ACTIONS

    def remote_record(self, token: str, action: str, payload: dict,
                      *, transport=None) -> dict:
        """受控远端任务操作入口(工作实例在会话内经 mgs-gate 提交)。

        完整顺序(逐次校验、锁内重读、意图先行、执行、结果审计与结果表达)
        集中在 ``mgs_remote_write.RemoteWriteTransaction.record``;既有参数、
        拒绝阶段(identity / channel / remote_scope / task_grant / role_scope /
        purpose / audit / remote_upstream)与网络期间持锁语义不变。
        """

        return self._remote.record(token, action, payload, transport=transport)

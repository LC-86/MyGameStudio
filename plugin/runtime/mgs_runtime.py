"""MyGameStudio 运行保障:受控写入服务核心(任务票 02 建立,任务票 03 加固)。

对应设计文档《运行保障合同》的接口职责,在本包内的最小实现:
- 执行绑定:create_instance 由可信调度侧调用,签发一次性执行凭据(令牌);
  令牌只以哈希形式落盘,身份、任务、用途、有效期与撤销状态由登记记录决定。
- 资源策略:写入目标必须同时落入「角色允许范围 ∩ 任务授权 ∩ 执行用途 ∩ 实际授权」;
  工具参数中的自报身份文本不参与授权。
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

本模块只依赖 Python 标准库。MCP 通道与调度 CLI 是它的两个入口。
"""

from __future__ import annotations

import fcntl
import hashlib
import json
import os
import re
import secrets
import stat
import sys
import time
from dataclasses import dataclass
from pathlib import Path

POLICY_FILE = "policy.json"
INSTANCES_FILE = "instances.json"
LOCKS_FILE = "locks.json"
AUDIT_FILE = "audit.jsonl"


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

    keys = ("created", "adopted", "issue_number", "published", "comment_id",
            "close_reason", "state_reason", "draft")
    return ",".join(f"{key}={result[key]}" for key in keys if key in result) \
        or "ok"


def _sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _sha256_text(text: str) -> str:
    return _sha256_bytes(text.encode("utf-8"))


def _token_fingerprint(token: str) -> str:
    return _sha256_text(token)[:12]


def _pattern_matches(pattern: str, rel_path: str) -> bool:
    """项目内相对路径匹配。

    约定:`**` 跨目录匹配任意字符;`*` 匹配除 `/` 外的任意字符;
    其余字符按字面比较。模式之间是"或"关系。
    """

    regex_parts: list[str] = []
    i = 0
    while i < len(pattern):
        if pattern.startswith("**", i):
            regex_parts.append(".*")
            i += 2
        elif pattern[i] == "*":
            regex_parts.append("[^/]*")
            i += 1
        else:
            regex_parts.append(re.escape(pattern[i]))
            i += 1
    return re.fullmatch("".join(regex_parts), rel_path) is not None


def _match_any(patterns: list[str], rel_path: str) -> bool:
    return any(_pattern_matches(p, rel_path) for p in patterns)


def _remote_match(patterns: list[str], resource: str) -> bool:
    """远端资源授权匹配:直接命中,或被「本资源及其子树」的 ** 授权覆盖
    (集合资源 github://…/issues 由 …/issues/** 类授权涵盖,任务票 17)。"""

    return (_match_any(patterns, resource)
            or _match_any(patterns, resource + "/**"))


# 用途条目缺失/无效的哨兵:授权交集不可计算,调用方必须失效闭合拒绝(R2)。
# 与 None(显式空条目 = 不额外限制)是两种不同语义,不得混同。
_PURPOSE_MISSING = object()


def _valid_restrict(value) -> bool:
    """restrict 字段的合法形态:None(不额外限制)或字符串模式列表。"""

    return value is None or (isinstance(value, list)
                             and all(isinstance(p, str) for p in value))


def _purpose_restrict(policy: dict, purpose: str):
    """读取用途的额外限制模式(R2)。

    返回模式列表、None(显式空条目 = 不额外限制,既有合法配置)或
    _PURPOSE_MISSING(绑定用途在策略中无条目 → 交集不可计算,拒绝)。
    """

    entry = policy.get("purposes", {}).get(purpose)
    if not isinstance(entry, dict) or "restrict" not in entry:
        return _PURPOSE_MISSING
    restrict = entry["restrict"]
    if not _valid_restrict(restrict):
        return _PURPOSE_MISSING
    return restrict


def _purpose_missing_reason(purpose: str) -> str:
    return f"purpose {purpose} missing from runtime policy (fail closed)"


def _role_patterns(policy: dict, role: str) -> list[str]:
    """角色的资源模式清单(条目形状由 _policy 校验;缺失即空集 = 拒绝)。"""

    return policy.get("roles", {}).get(role, {}).get("resources", [])


class GateService:
    """受控写入服务。所有公开方法都是接缝:调度侧与工作实例侧分别使用。"""

    def __init__(self, runtime_root: Path | str) -> None:
        self.runtime_root = Path(runtime_root).resolve()
        self.runtime_root.mkdir(parents=True, exist_ok=True)
        (self.runtime_root / "audit").mkdir(exist_ok=True)
        self._lock_path = self.runtime_root / ".service.lock"

    # ---------- 内部:文件锁与状态读写 ----------

    def _locked(self):
        class _Lock:
            def __init__(self, path: Path):
                self._fh = open(path, "a+")

            def __enter__(self):
                fcntl.flock(self._fh.fileno(), fcntl.LOCK_EX)
                return self._fh

            def __exit__(self, *exc):
                fcntl.flock(self._fh.fileno(), fcntl.LOCK_UN)
                self._fh.close()
                return False

        return _Lock(self._lock_path)

    def _read_json(self, name: str, default):
        path = self.runtime_root / name
        if not path.is_file():
            return default
        return json.loads(path.read_text(encoding="utf-8"))

    def _write_json(self, name: str, data) -> None:
        path = self.runtime_root / name
        tmp = path.with_suffix(path.suffix + ".tmp")
        tmp.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
        os.replace(tmp, path)

    def _policy(self) -> dict | None:
        """读取资源策略;缺失、损坏或结构无效(含角色/用途条目形状无效,
        R2)时返回 None(调用方必须失效闭合)。"""

        path = self.runtime_root / POLICY_FILE
        if not path.is_file():
            return None
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            return None
        if not isinstance(data, dict):
            return None
        for key in ("project_root", "roles", "purposes", "version"):
            if key not in data:
                return None
        if not isinstance(data["roles"], dict) or not isinstance(data["purposes"], dict):
            return None
        if not isinstance(data["project_root"], str) or not data["project_root"]:
            return None
        for entry in data["roles"].values():
            if not isinstance(entry, dict) or not isinstance(entry.get("resources"), list):
                return None
            if not all(isinstance(p, str) for p in entry["resources"]):
                return None
        for entry in data["purposes"].values():
            if not isinstance(entry, dict) or "restrict" not in entry:
                return None
            if not _valid_restrict(entry["restrict"]):
                return None
        return data

    def _policy_sha256(self) -> str:
        path = self.runtime_root / POLICY_FILE
        if not path.is_file():
            return ""
        return _sha256_bytes(path.read_bytes())

    def _audit(self, entry: dict) -> None:
        with self._locked():
            self._audit_unlocked(entry)

    def _audit_unlocked(self, entry: dict) -> None:
        """追加审计记录。调用方必须已持有服务锁(或经由 _audit 获取)。"""

        entry["ts"] = time.strftime("%Y-%m-%dT%H:%M:%S%z")
        entry.setdefault("policy_sha256", self._policy_sha256())
        path = self.runtime_root / "audit" / AUDIT_FILE
        with open(path, "a", encoding="utf-8") as fh:
            fh.write(json.dumps(entry, ensure_ascii=False) + "\n")

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
        with self._locked():
            self._write_json(POLICY_FILE, policy)
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
        with self._locked():
            records = self._read_json(INSTANCES_FILE, [])
            records.append(self._instance_record(instance))
            self._write_json(INSTANCES_FILE, records)
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
            "token_hash": _sha256_text(instance.token),
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

        with self._locked():
            records = self._read_json(INSTANCES_FILE, [])
            found = False
            for record in records:
                if record.get("instance_id") == instance_id and not record.get("released"):
                    record["released"] = True
                    found = True
            if found:
                self._write_json(INSTANCES_FILE, records)
                locks = self._read_json(LOCKS_FILE, {})
                locks = {p: v for p, v in locks.items() if v.get("instance_id") != instance_id}
                self._write_json(LOCKS_FILE, locks)
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

        with self._locked():
            locks = self._read_json(LOCKS_FILE, {})
        return {"locks": locks}

    def reclaim_locks(self, instance_id: str) -> dict:
        """回收一个旧实例遗留的写入占用(任务票 15)。

        顺序约束(运行保障合同「执行结束释放占用」):先撤销旧执行能力
        (release_instance,或等待有效期过去),再回收占用。实例仍然活跃
        (未释放且未过期)时拒绝回收——单写入者不因回收被打破;实例已不能
        写入(released 或已过期)时,删除其全部占用记录,允许新执行者接管。
        该接缝同时覆盖 release 流程中断在登记与占用两次落盘之间留下的
        「已释放但仍持有占用」缺口。
        """

        with self._locked():
            records = self._read_json(INSTANCES_FILE, [])
            record = next((r for r in records
                           if r.get("instance_id") == instance_id), None)
            if record is None:
                result = {"ok": False, "instance_id": instance_id, "found": False,
                          "active": None, "reclaimed": 0,
                          "reason": "unknown instance"}
            elif (not record.get("released")
                  and time.time() < record.get("expires_at", 0)):
                result = {"ok": False, "instance_id": instance_id, "found": True,
                          "active": True, "reclaimed": 0,
                          "reason": "instance still active: revoke its execution "
                                    "binding (release-instance) or wait for expiry "
                                    "before reclaiming occupancy"}
            else:
                locks = self._read_json(LOCKS_FILE, {})
                held = [p for p, v in locks.items()
                        if v.get("instance_id") == instance_id]
                for p in held:
                    locks.pop(p, None)
                self._write_json(LOCKS_FILE, locks)
                result = {"ok": True, "instance_id": instance_id, "found": True,
                          "active": False, "reclaimed": len(held),
                          "reason": ("occupancy reclaimed; holder can no longer "
                                     "write (released or expired)")}
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

    def _resolve_instance(self, token: str) -> tuple[dict | None, str]:
        """凭据 → 活跃实例登记。返回 (登记或 None, 拒绝原因)。"""

        if not token or not isinstance(token, str):
            return None, "missing token"
        token_hash = _sha256_text(token)
        for record in self._read_json(INSTANCES_FILE, []):
            if record.get("token_hash") == token_hash:
                if record.get("released"):
                    return None, f"instance {record.get('instance_id')} released"
                if time.time() >= record.get("expires_at", 0):
                    return None, f"instance {record.get('instance_id')} expired"
                return record, ""
        return None, "unknown token"

    def _resolve_target(self, policy: dict, path: str) -> tuple[Path | None, str, str]:
        """规范化写入目标。返回 (绝对真实路径或 None, 项目内相对路径, 拒绝原因)。"""

        if not path or not isinstance(path, str):
            return None, "", "missing path"
        project_root = Path(policy["project_root"]).resolve()
        candidate = Path(path)
        if not candidate.is_absolute():
            candidate = project_root / candidate
        # 先在字面层禁止逃逸,再解析符号链接
        literal = os.path.normpath(str(candidate))
        if not literal.startswith(str(project_root) + os.sep) and literal != str(project_root):
            return None, "", f"path escapes project root: {path}"
        try:
            resolved = candidate.resolve()
        except OSError as exc:
            return None, "", f"path resolve failed: {exc}"
        if resolved != project_root and not str(resolved).startswith(str(project_root) + os.sep):
            return None, "", f"resolved path escapes project root: {path}"
        try:
            rel = resolved.relative_to(project_root).as_posix()
        except ValueError:
            return None, "", f"path escapes project root: {path}"
        return resolved, rel, ""

    def scope(self, token: str) -> dict:
        """回读本凭据的有效可写范围(角色 ∩ 任务 ∩ 用途)。"""

        policy = self._policy()
        if policy is None:
            return self._deny("scope", "policy",
                              "runtime policy missing, corrupt or malformed (fail closed)",
                              token, None, {}, "")
        record, reason = self._resolve_instance(token)
        if record is None:
            return self._deny("scope", "identity", reason, token, None, policy, "")
        allowed = self._effective_scope(record, policy)
        if allowed is None:
            return self._deny("scope", "purpose",
                              _purpose_missing_reason(record["purpose"]),
                              token, record, policy, "")
        result = {
            "op": "scope",
            "decision": "allow",
            "instance_id": record["instance_id"],
            "task": record["task"],
            "role": record["role"],
            "purpose": record["purpose"],
            "allowed": sorted(allowed),
            "basis": self._basis(policy),
        }
        self._audit({**{k: v for k, v in result.items() if k != "allowed"},
                     "target": None, "reason": "scope query", "rule_stage": "scope"})
        return result

    @staticmethod
    def _basis(policy: dict) -> dict:
        return {
            "policy_version": policy.get("version"),
            "role_resources_source": "runtime policy.json (trusted scheduler channel)",
            "task_grant_source": "instance registry issued by trusted scheduler",
        }

    def _effective_scope(self, record: dict, policy: dict) -> list[str] | None:
        """按角色与用途过滤任务授权,得到凭据的有效可写范围(模式级交集)。

        绑定用途在策略中无条目时返回 None(交集不可计算,调用方失效闭合)。
        """

        restrict = _purpose_restrict(policy, record["purpose"])
        if restrict is _PURPOSE_MISSING:
            return None
        role_pats = _role_patterns(policy, record["role"])
        allowed = []
        for grant in record.get("resources", []):
            if not _match_any(role_pats, grant):
                continue
            if restrict is not None and not _match_any(restrict, grant):
                continue
            allowed.append(grant)
        return allowed

    def _grant_denial(self, record: dict, policy: dict,
                      rel: str) -> tuple[str, str] | None:
        """本地写入的任务 ∩ 角色 ∩ 用途授权核对(R2 收口后单一实现)。

        返回 (rule_stage, reason) 或 None(放行)。用途条目缺失时交集
        不可计算:与「显式空条目 = 不额外限制」区分,一律失效闭合拒绝。
        """

        if not _match_any(record.get("resources", []), rel):
            return ("task_grant",
                    f"path not granted to task {record['task']}: {rel}")
        if not _match_any(_role_patterns(policy, record["role"]), rel):
            return ("role_scope", f"role {record['role']} may not write: {rel}")
        restrict = _purpose_restrict(policy, record["purpose"])
        if restrict is _PURPOSE_MISSING:
            return ("purpose", _purpose_missing_reason(record["purpose"]))
        if restrict is not None and not _match_any(restrict, rel):
            return ("purpose",
                    f"purpose {record['purpose']} restricted to {restrict}: {rel}")
        return None

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
        必然在锁内重读时被拒,不可能再落盘。
        """

        payload = content.encode("utf-8") if data is None else data
        policy = self._policy()
        if policy is None:
            return self._deny("write", "policy",
                              "runtime policy missing, corrupt or malformed (fail closed)",
                              token, None, {}, path, note)
        record, reason = self._resolve_instance(token)
        if record is None:
            return self._deny("write", "identity", reason, token, None, policy, path, note)
        resolved, rel, reason = self._resolve_target(policy, path)
        if resolved is None:
            return self._deny("write", "path", reason, token, record, policy, path, note)
        pre_grant = self._grant_denial(record, policy, rel)
        if pre_grant is not None:
            return self._deny("write", pre_grant[0], pre_grant[1],
                              token, record, policy, rel, note)

        denial: tuple[str, str, str] | None = None
        result: dict | None = None
        with self._locked():
            # —— 临界区内最终核对(R1):以锁内重读的策略与登记为准。
            # 先重读身份再重读策略:策略失效时拒绝记录仍携带最新身份归属 ——
            record, reason = self._resolve_instance(token)
            if record is None:
                denial = ("write", "identity", reason)
            if denial is None:
                policy = self._policy()
                if policy is None:
                    denial = ("write", "policy",
                              "runtime policy missing, corrupt or malformed "
                              "(fail closed)")
            if denial is None:
                resolved, rel, reason = self._resolve_target(policy, path)
                if resolved is None:
                    denial = ("write", "path", reason)
            if denial is None:
                grant = self._grant_denial(record, policy, rel)
                if grant is not None:
                    denial = ("write", grant[0], grant[1])
            if denial is None:
                locks = self._read_json(LOCKS_FILE, {})
                holder = locks.get(rel)
                if holder and holder.get("instance_id") != record["instance_id"]:
                    denial = ("write", "occupancy",
                              f"resource held by instance {holder.get('instance_id')}")
                elif expected_sha256 is not None:
                    # 版本校验在锁内读取(02 已知边界:消除读取与占用之间的调度窗口)
                    if resolved.exists():
                        current = _sha256_bytes(resolved.read_bytes())
                        if expected_sha256.lower() != current:
                            denial = ("write", "version",
                                      f"expected sha256 {expected_sha256} != current {current}")
                    elif expected_sha256.lower() != "absent":
                        denial = ("write", "version",
                                  f"target absent but expected {expected_sha256}")
            if denial is None:
                # 路径竞态复检:占用与版本校验期间目标树可能被换链
                re_resolved, re_rel, _ = self._resolve_target(policy, path)
                if re_resolved != resolved or re_rel != rel:
                    denial = ("write", "race",
                              f"target changed between validation and write: {path}")
            if denial is None:
                # 目标必须是普通文件或不存在:管道/目录/设备等不可作为受控写入目标
                try:
                    mode = resolved.lstat().st_mode if resolved.exists() else None
                except OSError as exc:
                    denial = ("write", "path", f"target lstat failed: {exc}")
                    mode = None
                if denial is None and mode is not None and not stat.S_ISREG(mode):
                    denial = ("write", "path", f"target is not a regular file: {rel}")
            if denial is None:
                # 落点锚定:从项目根用 O_NOFOLLOW 逐组件打开父目录(缺失的按需创建)。
                # 锚定后一切读写都经目录 fd 进行,父目录此后被换成符号链接也不改落点。
                parent_fd = self._open_pinned_parent(resolved, policy)
                if parent_fd is None:
                    denial = ("write", "race",
                              f"parent directory walk failed or contains symlink: {rel}")
                else:
                    base = resolved.name
                    try:
                        mode = None
                        try:
                            mode = os.stat(base, dir_fd=parent_fd,
                                           follow_symlinks=False).st_mode
                        except FileNotFoundError:
                            mode = None
                        if mode is not None and not stat.S_ISREG(mode):
                            denial = ("write", "path",
                                      f"target is not a regular file: {rel}")
                        else:
                            # R3:内容更新保留既有目标的权限位——权限变化必须经
                            # 显式操作,不经内容更新隐式发生;新建文件按默认 0644。
                            existing_mode = stat.S_IMODE(mode) if mode is not None else None
                            backup = None
                            if mode is not None:
                                with os.fdopen(os.open(base, os.O_RDONLY,
                                                       dir_fd=parent_fd), "rb") as fh:
                                    backup = fh.read()
                            result = {
                                "op": "write",
                                "decision": "allow",
                                "reason": "granted by role+task+purpose intersection",
                                "rule_stage": "granted",
                                "instance_id": record["instance_id"],
                                "task": record["task"],
                                "role": record["role"],
                                "purpose": record["purpose"],
                                "target": rel,
                                "written_sha256": _sha256_bytes(payload),
                                "bytes": len(payload),
                                "basis": self._basis(policy),
                                "note": note,
                            }
                            tmp_name = ".mgs-write-" + secrets.token_hex(6)
                            try:
                                self._write_pinned_temp(parent_fd, tmp_name,
                                                        payload, existing_mode)
                                os.replace(tmp_name, base,
                                           src_dir_fd=parent_fd, dst_dir_fd=parent_fd)
                                locks[rel] = {"instance_id": record["instance_id"],
                                              "since": time.time()}
                                self._write_json(LOCKS_FILE, locks)
                                self._audit_unlocked(result)
                            except Exception as exc:
                                # 落盘后状态记录失败:回滚已写入字节,失效闭合。
                                # 「无审计则无生效写入」,宁可拒绝也不留下无记录写入。
                                self._rollback(parent_fd, base, backup,
                                               mode_bits=existing_mode)
                                denial = ("write", "audit",
                                          f"post-write recording failed ({exc}); "
                                          "write rolled back (fail closed)")
                                result = None
                            finally:
                                try:
                                    os.unlink(tmp_name, dir_fd=parent_fd)
                                except OSError:
                                    pass
                    finally:
                        os.close(parent_fd)
        if denial is not None:
            return self._deny(denial[0], denial[1], denial[2],
                              token, record,
                              policy if policy is not None else {},
                              rel or path, note)
        return result

    def _open_pinned_parent(self, resolved: Path, policy: dict) -> int | None:
        """从项目根逐组件打开目标父目录,返回锚定的目录 fd。

        每一步都用 O_NOFOLLOW 打开:任一组件是符号链接(包括校验后被人换链)
        都会失败返回 None;缺失的中间目录按需在锚定位置创建。项目根本身
        不允许是符号链接。
        """

        project_root = Path(policy["project_root"]).resolve()
        try:
            rel = resolved.parent.relative_to(project_root)
        except ValueError:
            return None
        flags = os.O_RDONLY | getattr(os, "O_DIRECTORY", 0)
        nofollow = getattr(os, "O_NOFOLLOW", 0)
        try:
            fd = os.open(str(project_root), flags | nofollow)
        except OSError:
            return None
        try:
            for comp in rel.parts:
                try:
                    nxt = os.open(comp, flags | nofollow, dir_fd=fd)
                except FileNotFoundError:
                    os.mkdir(comp, 0o755, dir_fd=fd)
                    nxt = os.open(comp, flags | nofollow, dir_fd=fd)
                os.close(fd)
                fd = nxt
        except OSError:
            os.close(fd)
            return None
        return fd

    @staticmethod
    def _write_pinned_temp(parent_fd: int, tmp_name: str, data: bytes,
                           mode_bits: int | None) -> None:
        """在锚定目录创建临时文件并写入字节(R3)。

        mode_bits 给出时逐位生效(fchmod 摆脱 umask),用于保留既有目标
        的权限位;None 按新建默认 0644(仍受 umask 影响,与既有行为一致)。
        """

        tfd = os.open(tmp_name, os.O_CREAT | os.O_EXCL | os.O_WRONLY,
                      mode_bits if mode_bits is not None else 0o644,
                      dir_fd=parent_fd)
        with os.fdopen(tfd, "wb") as fh:
            if mode_bits is not None:
                os.fchmod(fh.fileno(), mode_bits)
            fh.write(data)

    @staticmethod
    def _rollback(parent_fd: int, base: str, backup: bytes | None,
                  mode_bits: int | None = None) -> None:
        """经锚定目录回滚一次已落盘的写入(尽力而为,失败由调用方记录)。

        回滚与内容更新遵守同一要求(R3):恢复既有目标时保留其权限位
        (mode_bits 为回滚前的实际权限),不得借回滚隐式改变权限。
        """

        if backup is None:
            try:
                os.unlink(base, dir_fd=parent_fd)
            except OSError:
                pass
            return
        tmp_name = ".mgs-rollback-" + secrets.token_hex(6)
        try:
            GateService._write_pinned_temp(parent_fd, tmp_name, backup,
                                           mode_bits)
            os.replace(tmp_name, base, src_dir_fd=parent_fd, dst_dir_fd=parent_fd)
        except OSError:
            pass
        finally:
            try:
                os.unlink(tmp_name, dir_fd=parent_fd)
            except OSError:
                pass

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
        if not _remote_match(_role_patterns(policy, record["role"]), resource):
            return ("role_scope",
                    f"role {record['role']} may not write: {resource}")
        restrict = _purpose_restrict(policy, record["purpose"])
        if restrict is _PURPOSE_MISSING:
            return ("purpose", _purpose_missing_reason(record["purpose"]))
        if restrict is not None and not _remote_match(restrict, resource):
            return ("purpose",
                    f"purpose {record['purpose']} restricted to "
                    f"{restrict}: {resource}")
        return None

    def remote_record(self, token: str, action: str, payload: dict,
                      *, transport=None) -> dict:
        """受控远端任务操作入口(工作实例在会话内经 mgs-gate 提交)。

        逐次校验:凭据(身份)→ 远端通道配置(channel)→ 项目 CONFIG 后端
        与仓库级 issues-write 授权(remote_scope)→ 任务授权(task_grant)
        → 角色范围(role_scope)→ 用途(purpose),全通过后才经适配器执行;
        上游不可用失效闭合(remote_upstream,不绕行直连;缓存目录可用时
        由适配器保存未发布草稿并在结果中回报)。允许与拒绝都进审计。
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

        project_root = Path(policy["project_root"])
        config_rel = str(payload.get("config_rel") or mgs_records.DEFAULT_CONFIG_REL)
        try:
            config = mgs_records.load_config(project_root, config_rel)
        except mgs_records.RecordsError as exc:
            return self._deny(op, "remote_scope",
                              f"项目协作配置不可读:{exc}", token, record,
                              policy, action)
        if config["backend"] != "github-issues" or not config.get("repo"):
            return self._deny(
                op, "remote_scope",
                f"项目任务后端为 {config['backend']!r},远端通道仅服务 "
                "github-issues 后端项目", token, record, policy, action)
        repo = config["repo"]
        allowed, auth_note = mgs_github._authorization_for(config, "issues-write")
        if not allowed:
            return self._deny(op, "remote_scope", auth_note, token, record,
                              policy, action)

        identity = str(payload.get("identity") or "")
        granularity = self.REMOTE_ACTIONS[action]
        if granularity == "collection":
            resource = f"github://{repo['host']}/{repo['owner']}/{repo['repo']}/issues"
        elif granularity == "task":
            if not identity:
                return self._deny(op, "channel", "缺少 identity", token, record,
                                  policy, action)
            resource = (f"github://{repo['host']}/{repo['owner']}/{repo['repo']}"
                        f"/issues/{identity}")
        else:
            if not identity:
                return self._deny(op, "channel", "缺少 identity", token, record,
                                  policy, action)
            resource = (f"github://{repo['host']}/{repo['owner']}/{repo['repo']}"
                        f"/issues/{identity}/comments")
        grant = self._remote_grant_denial(record, policy, resource)
        if grant is not None:
            return self._deny(op, grant[0], grant[1],
                              token, record, policy, resource)

        env_token = os.environ.get(channel["token_env"], "").strip()
        active_transport = transport or mgs_github.UrllibTransport(
            api_base=channel["api_base"], token=env_token or None)
        backend = mgs_github.GithubBackend(
            config, active_transport, channel.get("cache_dir"))
        note = {"action": action,
                "repo": f"{repo['host']}/{repo['owner']}/{repo['repo']}"}

        # R1/R4:与本地 write() 同一临界区纪律——最终身份、策略与授权核对、
        # 写入意图的持久记录、远端动作的执行与结果审计都持有服务锁完成。
        # 撤销(release_instance)与策略更换同样持有本锁:撤销完成后在途
        # 远端写入在锁内重读时被拒,不可能执行;远端动作因此与同运行根的
        # 本地写入串行,占锁时长受传输超时约束(不无限持有)。
        # R4:改变远端状态的写入意图先于执行持久记录,审计不可用时动作不
        # 执行(失效闭合);只读动作(read)不改变远端状态,不要求意图记录。
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
                grant = self._remote_grant_denial(record, policy, resource)
                if grant is not None:
                    denial = (grant[0], grant[1], None)
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
                    # 草稿的操作由各动作内部处理,这里兜底离线草稿
                    draft = None
                    if exc.kind == "offline" and channel.get("cache_dir"):
                        draft = backend._save_draft(  # noqa: SLF001 - 通道内聚
                            self._draft_op_for(action), dict(payload), str(exc))
                    denial = ("remote_upstream",
                              f"remote upstream unavailable (fail closed): {exc}",
                              {"draft": draft} if draft else None)
                except mgs_github.GithubRecordsError as exc:
                    denial = ("remote_upstream", str(exc), None)
                else:
                    if not result.get("published", True) and not result.get("created"):
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
    def _draft_op_for(action: str) -> str:
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
        if action == "create":
            return backend.create_task(
                str(payload["identity"]), str(payload.get("title", "")),
                dict(payload.get("request") or {}),
                triage=str(payload.get("triage", "needs-triage")),
                progress=str(payload.get("progress", "待执行")))
        if action == "update":
            return backend.update_task(
                str(payload["identity"]), dict(payload.get("fields") or {}),
                expected_body_sha256=payload.get("expected_body_sha256"),
                change_note=str(payload.get("change_note", "安排更新")))
        if action == "set-triage":
            return backend.set_triage(str(payload["identity"]),
                                      str(payload["label"]))
        if action == "set-relations":
            return backend.set_relations(str(payload["identity"]),
                                         list(payload.get("deps") or []))
        if action == "set-parent":
            return backend.set_parent(str(payload["identity"]),
                                      payload.get("parent"))
        if action == "close":
            return backend.close_task(str(payload["identity"]),
                                      str(payload["reason"]),
                                      note=str(payload.get("note", "")))
        if action == "append-result":
            return backend.append_result(str(payload["identity"]),
                                         str(payload.get("result_markdown", "")))
        raise ValueError(f"unknown action {action}")

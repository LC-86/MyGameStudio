"""MyGameStudio 运行保障:受控写入服务核心(任务票 02 建立,任务票 03 加固)。

对应设计文档《运行保障合同》的接口职责,在本包内的最小实现:
- 执行绑定:create_instance 由可信调度侧调用,签发一次性执行凭据(令牌);
  令牌只以哈希形式落盘,身份、任务、用途、有效期与撤销状态由登记记录决定。
- 资源策略:写入目标必须同时落入「角色允许范围 ∩ 任务授权 ∩ 执行用途 ∩ 实际授权」;
  工具参数中的自报身份文本不参与授权。
- 调度与占用:同一资源同一时间只允许一个活跃实例写入。
- 结果核对:每次 scope/write(无论允许或拒绝)都追加可定位审计记录。

任务票 03 增加的失效闭合与竞态防护:
- 策略缺失、损坏或结构无效时,scope/write 一律拒绝(rule_stage=policy),
  不抛异常、不触碰目标字节;策略恢复后同一服务继续可用;
- 写入目标在解析后、落盘前被换链(父目录或目标本身变成指向别处的符号链接)
  属可复现路径竞态,占用与版本校验之后、落盘之前做路径复检,发现即拒绝
  (rule_stage=race);目标非普通文件(管道/目录等)同样拒绝;
- 落盘后的占用登记或审计追加失败时,已写入字节回滚并拒绝(rule_stage=audit),
  保证「无审计则无生效写入」;拒绝路径的审计追加失败不影响拒绝结果。

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
        """读取资源策略;缺失、损坏或结构无效时返回 None(调用方必须失效闭合)。"""

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

    def _effective_scope(self, record: dict, policy: dict) -> list[str]:
        """按角色与用途过滤任务授权,得到凭据的有效可写范围(模式级交集)。"""

        role_pats = policy.get("roles", {}).get(record["role"], {}).get("resources", [])
        restrict = policy.get("purposes", {}).get(record["purpose"], {}).get("restrict")
        allowed = []
        for grant in record.get("resources", []):
            if not _match_any(role_pats, grant):
                continue
            if restrict is not None and not _match_any(restrict, grant):
                continue
            allowed.append(grant)
        return allowed

    def write(self, token: str, path: str, content: str,
              expected_sha256: str | None = None, note: str | None = None) -> dict:
        """受控写入入口。任何拒绝都不触碰目标字节;检查器故障一律失效闭合。"""

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

        if not _match_any(record.get("resources", []), rel):
            return self._deny("write", "task_grant",
                              f"path not granted to task {record['task']}: {rel}",
                              token, record, policy, rel, note)
        role_pats = policy.get("roles", {}).get(record["role"], {}).get("resources", [])
        if not _match_any(role_pats, rel):
            return self._deny("write", "role_scope",
                              f"role {record['role']} may not write: {rel}",
                              token, record, policy, rel, note)
        restrict = policy.get("purposes", {}).get(record["purpose"], {}).get("restrict")
        if restrict is not None and not _match_any(restrict, rel):
            return self._deny("write", "purpose",
                              f"purpose {record['purpose']} restricted to {restrict}: {rel}",
                              token, record, policy, rel, note)

        data = content.encode("utf-8")
        denial: tuple[str, str, str] | None = None
        result: dict | None = None
        with self._locked():
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
                                "written_sha256": _sha256_bytes(data),
                                "bytes": len(data),
                                "basis": self._basis(policy),
                                "note": note,
                            }
                            tmp_name = ".mgs-write-" + secrets.token_hex(6)
                            try:
                                tfd = os.open(tmp_name,
                                              os.O_CREAT | os.O_EXCL | os.O_WRONLY,
                                              0o644, dir_fd=parent_fd)
                                with os.fdopen(tfd, "wb") as fh:
                                    fh.write(data)
                                os.replace(tmp_name, base,
                                           src_dir_fd=parent_fd, dst_dir_fd=parent_fd)
                                locks[rel] = {"instance_id": record["instance_id"],
                                              "since": time.time()}
                                self._write_json(LOCKS_FILE, locks)
                                self._audit_unlocked(result)
                            except Exception as exc:
                                # 落盘后状态记录失败:回滚已写入字节,失效闭合。
                                # 「无审计则无生效写入」,宁可拒绝也不留下无记录写入。
                                self._rollback(parent_fd, base, backup)
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
                              token, record, policy, rel or path, note)
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
    def _rollback(parent_fd: int, base: str, backup: bytes | None) -> None:
        """经锚定目录回滚一次已落盘的写入(尽力而为,失败由调用方记录)。"""

        if backup is None:
            try:
                os.unlink(base, dir_fd=parent_fd)
            except OSError:
                pass
            return
        tmp_name = ".mgs-rollback-" + secrets.token_hex(6)
        try:
            rfd = os.open(tmp_name, os.O_CREAT | os.O_EXCL | os.O_WRONLY,
                          0o644, dir_fd=parent_fd)
            with os.fdopen(rfd, "wb") as fh:
                fh.write(backup)
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
              note: str | None = None) -> dict:
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

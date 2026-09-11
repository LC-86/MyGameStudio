"""MyGameStudio 运行保障:执行登记与策略状态(任务票 21 新增)。

集中 runtime_root 下受控写入的全部持久状态与唯一服务锁,使「锁内重读」
「无审计则无生效写入」这些不变量只有一处实现:

- ``policy.json`` 资源策略:读取、结构校验、指纹、写入;
- ``instances.json`` 执行登记:签发记录追加、令牌哈希解析、撤销;
- ``locks.json`` 写入占用:读取、释放、回收;
- ``audit/audit.jsonl`` 审计:允许、意图与拒绝都追加(追加时才盖时间戳与
  策略指纹)。

本模块只管「状态与并发」,不做授权解释、路径判定或字节事务——那些集中在
``mgs_local_write.py``。可信调度侧(签发、释放、占用回收、状态回读)与
工作实例侧(逐次身份重读、占用落盘、审计)经同一登记接缝读写状态,因此
撤销与写入天然共用同一把锁,不依赖调用方正确拼接时序。

沿用原 ``mgs_runtime`` 的持久化格式与失败语义:缺失/损坏的策略返回 None
(调用方失效闭合),令牌只存哈希,登记与占用一次落盘、审计追加在已持锁时
不得再次取锁。本模块只依赖 Python 标准库。
"""

from __future__ import annotations

import fcntl
import hashlib
import json
import os
import time
from pathlib import Path

POLICY_FILE = "policy.json"
INSTANCES_FILE = "instances.json"
LOCKS_FILE = "locks.json"
AUDIT_FILE = "audit.jsonl"


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_text(text: str) -> str:
    return sha256_bytes(text.encode("utf-8"))


def valid_restrict(value) -> bool:
    """restrict 字段的合法形态:None(不额外限制)或字符串模式列表。"""

    return value is None or (isinstance(value, list)
                             and all(isinstance(p, str) for p in value))


class _FileLock:
    """服务锁:整个 runtime_root 的唯一排他文件锁。"""

    def __init__(self, path: Path):
        self._fh = open(path, "a+")

    def __enter__(self):
        fcntl.flock(self._fh.fileno(), fcntl.LOCK_EX)
        return self._fh

    def __exit__(self, *exc):
        fcntl.flock(self._fh.fileno(), fcntl.LOCK_UN)
        self._fh.close()
        return False


class GateRegistry:
    """受控写入的持久状态访问:策略、执行登记、占用与审计。

    所有会改变状态的方法都在同一把服务锁的临界区内完成;读取方法(策略、
    令牌解析、占用回读)按原语义不加锁——最终写入前仍会在锁内重读(R1)。
    """

    def __init__(self, runtime_root: Path | str) -> None:
        self.runtime_root = Path(runtime_root).resolve()
        self.runtime_root.mkdir(parents=True, exist_ok=True)
        (self.runtime_root / "audit").mkdir(exist_ok=True)
        self._lock_path = self.runtime_root / ".service.lock"

    # ---------- 锁与 JSON 状态 ----------

    def locked(self):
        """返回服务锁上下文;进入时加排他锁,退出时释放。"""

        return _FileLock(self._lock_path)

    def read_json(self, name: str, default):
        path = self.runtime_root / name
        if not path.is_file():
            return default
        return json.loads(path.read_text(encoding="utf-8"))

    def write_json(self, name: str, data) -> None:
        path = self.runtime_root / name
        tmp = path.with_suffix(path.suffix + ".tmp")
        tmp.write_text(json.dumps(data, ensure_ascii=False, indent=2),
                       encoding="utf-8")
        os.replace(tmp, path)

    # ---------- 策略 ----------

    def read_policy(self) -> dict | None:
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
            if not valid_restrict(entry["restrict"]):
                return None
        return data

    def write_policy(self, policy: dict) -> None:
        with self.locked():
            self.write_json(POLICY_FILE, policy)

    def policy_sha256(self) -> str:
        path = self.runtime_root / POLICY_FILE
        if not path.is_file():
            return ""
        return sha256_bytes(path.read_bytes())

    # ---------- 审计 ----------

    def append_audit_unlocked(self, entry: dict) -> None:
        """追加审计记录。调用方必须已持有服务锁(或经由门面的 _audit 获取)。"""

        entry["ts"] = time.strftime("%Y-%m-%dT%H:%M:%S%z")
        entry.setdefault("policy_sha256", self.policy_sha256())
        path = self.runtime_root / "audit" / AUDIT_FILE
        with open(path, "a", encoding="utf-8") as fh:
            fh.write(json.dumps(entry, ensure_ascii=False) + "\n")

    # ---------- 执行登记 ----------

    def instances(self) -> list:
        return self.read_json(INSTANCES_FILE, [])

    def resolve_instance(self, token: str) -> tuple[dict | None, str]:
        """凭据 → 活跃实例登记。返回 (登记或 None, 拒绝原因)。"""

        if not token or not isinstance(token, str):
            return None, "missing token"
        token_hash = sha256_text(token)
        for record in self.instances():
            if record.get("token_hash") == token_hash:
                if record.get("released"):
                    return None, f"instance {record.get('instance_id')} released"
                if time.time() >= record.get("expires_at", 0):
                    return None, f"instance {record.get('instance_id')} expired"
                return record, ""
        return None, "unknown token"

    def add_instance(self, record: dict) -> None:
        with self.locked():
            records = self.read_json(INSTANCES_FILE, [])
            records.append(record)
            self.write_json(INSTANCES_FILE, records)

    def release(self, instance_id: str) -> bool:
        """撤销执行能力并释放其全部写入占用;返回是否命中未释放的登记。"""

        with self.locked():
            records = self.read_json(INSTANCES_FILE, [])
            found = False
            for record in records:
                if record.get("instance_id") == instance_id and not record.get("released"):
                    record["released"] = True
                    found = True
            if found:
                self.write_json(INSTANCES_FILE, records)
                locks = self.read_json(LOCKS_FILE, {})
                locks = {p: v for p, v in locks.items()
                         if v.get("instance_id") != instance_id}
                self.write_json(LOCKS_FILE, locks)
        return found

    # ---------- 写入占用 ----------

    def locks(self) -> dict:
        return self.read_json(LOCKS_FILE, {})

    def reclaim_locks(self, instance_id: str) -> dict:
        """回收一个旧实例遗留的写入占用(任务票 15)。

        顺序约束(运行保障合同「执行结束释放占用」):先撤销旧执行能力
        (release_instance,或等待有效期过去),再回收占用。实例仍然活跃
        (未释放且未过期)时拒绝回收——单写入者不因回收被打破;实例已不能
        写入(released 或已过期)时,删除其全部占用记录,允许新执行者接管。
        该接缝同时覆盖 release 流程中断在登记与占用两次落盘之间留下的
        「已释放但仍持有占用」缺口。
        """

        with self.locked():
            records = self.read_json(INSTANCES_FILE, [])
            record = next((r for r in records
                           if r.get("instance_id") == instance_id), None)
            if record is None:
                return {"ok": False, "instance_id": instance_id, "found": False,
                        "active": None, "reclaimed": 0,
                        "reason": "unknown instance"}
            if (not record.get("released")
                    and time.time() < record.get("expires_at", 0)):
                return {"ok": False, "instance_id": instance_id, "found": True,
                        "active": True, "reclaimed": 0,
                        "reason": "instance still active: revoke its execution "
                                  "binding (release-instance) or wait for expiry "
                                  "before reclaiming occupancy"}
            locks = self.read_json(LOCKS_FILE, {})
            held = [p for p, v in locks.items()
                    if v.get("instance_id") == instance_id]
            for p in held:
                locks.pop(p, None)
            self.write_json(LOCKS_FILE, locks)
            return {"ok": True, "instance_id": instance_id, "found": True,
                    "active": False, "reclaimed": len(held),
                    "reason": ("occupancy reclaimed; holder can no longer "
                               "write (released or expired)")}

"""MyGameStudio 运行保障:本地受控写入的策略解释与字节事务(任务票 21 新增)。

本模块集中「一次本地受控写入」的完整不变量,调用方(mgs-gate 通道、运行
保障回归、调度侧自检)不再自行拼接检查与落盘步骤:

- 策略解释:项目内路径模式匹配、角色的资源模式、用途额外限制,以及
  「角色 ∩ 任务 ∩ 用途」授权交集的单一实现(任务票 22 起本地写入与受控
  远端操作共用 ``grant_denial``;远端资源匹配差异经 ``matcher``/``noun``
  参数保留——集合资源 github://…/issues 由 …/issues/** 类授权涵盖)。用途
  条目缺失与显式空条目是两种不同语义:前者交集不可计算,失效闭合拒绝(R2);
  后者为「不额外限制」,是既有合法配置。
- 路径身份:写入目标规范化(字面层与解析后都禁止逃逸项目根)、从项目根用
  O_NOFOLLOW 逐组件锚定父目录、临时文件落盘与既有权限位保留、失败回滚。
- 完整本地字节事务:锁外快速预检只用于尽早拒绝;最终身份、策略、授权、
  占用、版本、路径竞态复检与实际写入都在同一服务锁临界区内完成(R1)。撤销
  (release_instance)与策略更换持同一把锁,撤销完成后在途写入必然在锁内
  重读时被拒,不可能再落盘。

状态访问(执行登记、策略文件、写入占用、审计、服务锁)集中在
``mgs_gate_registry.py``;本模块经宿主门面(GateService)调用这些接缝——
占用只经接缝判定与登记,``locks.json`` 的条目形状不在本模块解释——使既有
工作实例入口与可信调度侧操作继续可用。文本与二进制载荷走同一事务:
``content``(UTF-8)或 ``data``(原始字节)语义一致,通道层负责校验恰提供
其一。本模块只依赖标准库与登记职责的哈希/形态助手。
"""

from __future__ import annotations

import os
import re
import secrets
import stat
from collections.abc import Callable
from pathlib import Path

from mgs_gate_registry import sha256_bytes, valid_restrict

POLICY_MISSING_REASON = ("runtime policy missing, corrupt or malformed "
                         "(fail closed)")

# 用途条目缺失/无效的哨兵:授权交集不可计算,调用方必须失效闭合拒绝(R2)。
# 与 None(显式空条目 = 不额外限制)是两种不同语义,不得混同。
PURPOSE_MISSING = object()


def pattern_matches(pattern: str, rel_path: str) -> bool:
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


def match_any(patterns: list[str], rel_path: str) -> bool:
    return any(pattern_matches(p, rel_path) for p in patterns)


def purpose_restrict(policy: dict, purpose: str):
    """读取用途的额外限制模式(R2)。

    返回模式列表、None(显式空条目 = 不额外限制,既有合法配置)或
    PURPOSE_MISSING(绑定用途在策略中无条目 → 交集不可计算,拒绝)。
    """

    entry = policy.get("purposes", {}).get(purpose)
    if not isinstance(entry, dict) or "restrict" not in entry:
        return PURPOSE_MISSING
    restrict = entry["restrict"]
    if not valid_restrict(restrict):
        return PURPOSE_MISSING
    return restrict


def purpose_missing_reason(purpose: str) -> str:
    return f"purpose {purpose} missing from runtime policy (fail closed)"


def role_patterns(policy: dict, role: str) -> list[str]:
    """角色的资源模式清单(条目形状由策略校验;缺失即空集 = 拒绝)。"""

    return policy.get("roles", {}).get(role, {}).get("resources", [])


def grant_denial(record: dict, policy: dict, rel: str, *,
                 matcher: Callable[[list[str], str], bool] = match_any,
                 noun: str = "path") -> tuple[str, str] | None:
    """受控写入的任务 ∩ 角色 ∩ 用途授权核对(R2 收口后单一实现)。

    返回 (rule_stage, reason) 或 None(放行)。用途条目缺失时交集
    不可计算:与「显式空条目 = 不额外限制」区分,一律失效闭合拒绝。

    本函数是本地写入与受控远端操作共用的策略解释实现(任务票 22 收口两处
    重复):``matcher`` 给出资源匹配器(本地为项目内相对路径 ``match_any``;
    远端资源由 ``mgs_remote_write.remote_match`` 在直接命中外再接受
    「本资源及其子树」的 ``/**`` 授权覆盖),``noun`` 只影响拒绝说明的措辞
    (本地 "path" / 远端 "remote resource"),两条路径的规则与拒绝阶段一致。
    """

    if not matcher(record.get("resources", []), rel):
        return ("task_grant",
                f"{noun} not granted to task {record['task']}: {rel}")
    if not matcher(role_patterns(policy, record["role"]), rel):
        return ("role_scope", f"role {record['role']} may not write: {rel}")
    restrict = purpose_restrict(policy, record["purpose"])
    if restrict is PURPOSE_MISSING:
        return ("purpose", purpose_missing_reason(record["purpose"]))
    if restrict is not None and not matcher(restrict, rel):
        return ("purpose",
                f"purpose {record['purpose']} restricted to {restrict}: {rel}")
    return None


def effective_scope(record: dict, policy: dict) -> list[str] | None:
    """按角色与用途过滤任务授权,得到凭据的有效可写范围(模式级交集)。

    绑定用途在策略中无条目时返回 None(交集不可计算,调用方失效闭合)。
    """

    restrict = purpose_restrict(policy, record["purpose"])
    if restrict is PURPOSE_MISSING:
        return None
    role_pats = role_patterns(policy, record["role"])
    allowed = []
    for grant in record.get("resources", []):
        if not match_any(role_pats, grant):
            continue
        if restrict is not None and not match_any(restrict, grant):
            continue
        allowed.append(grant)
    return allowed


def resolve_target(policy: dict, path: str) -> tuple[Path | None, str, str]:
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


def open_pinned_parent(project_root: Path | str, resolved: Path) -> int | None:
    """从项目根逐组件打开目标父目录,返回锚定的目录 fd。

    每一步都用 O_NOFOLLOW 打开:任一组件是符号链接(包括校验后被人换链)
    都会失败返回 None;缺失的中间目录按需在锚定位置创建。项目根本身
    不允许是符号链接。
    """

    project_root = Path(project_root).resolve()
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


def write_pinned_temp(parent_fd: int, tmp_name: str, data: bytes,
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


def rollback(parent_fd: int, base: str, backup: bytes | None,
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
        write_pinned_temp(parent_fd, tmp_name, backup, mode_bits)
        os.replace(tmp_name, base, src_dir_fd=parent_fd, dst_dir_fd=parent_fd)
    except OSError:
        pass
    finally:
        try:
            os.unlink(tmp_name, dir_fd=parent_fd)
        except OSError:
            pass


class LocalWriteTransaction:
    """完整本地受控写入职责:策略解释、路径身份与字节事务的唯一入口。

    经宿主门面(GateService)访问执行登记、策略、审计与服务锁,使既有
    接缝继续可用;门面自身不再拼装检查与落盘步骤。
    """

    def __init__(self, host) -> None:
        self._host = host

    def scope(self, token: str) -> dict:
        """回读本凭据的有效可写范围(角色 ∩ 任务 ∩ 用途)。"""

        host = self._host
        policy = host._policy()
        if policy is None:
            return host._deny("scope", "policy", POLICY_MISSING_REASON,
                              token, None, {}, "")
        record, reason = host._resolve_instance(token)
        if record is None:
            return host._deny("scope", "identity", reason, token, None, policy, "")
        allowed = effective_scope(record, policy)
        if allowed is None:
            return host._deny("scope", "purpose",
                              purpose_missing_reason(record["purpose"]),
                              token, record, policy, "")
        result = {
            "op": "scope",
            "decision": "allow",
            "instance_id": record["instance_id"],
            "task": record["task"],
            "role": record["role"],
            "purpose": record["purpose"],
            "allowed": sorted(allowed),
            "basis": host._basis(policy),
        }
        host._audit({**{k: v for k, v in result.items() if k != "allowed"},
                     "target": None, "reason": "scope query", "rule_stage": "scope"})
        return result

    def write(self, token: str, path: str, content: str = "",
              expected_sha256: str | None = None, note: str | None = None,
              *, data: bytes | None = None) -> dict:
        """受控本地写入的唯一完整入口。任何拒绝都不触碰目标字节。

        载荷二选一:`content`(UTF-8 文本,沿用任务票 02 语义)或
        `data`(原始字节,任务票 11 起供音频等二进制资源使用)。两者语义
        一致——同一授权交集、同一字节级版本校验与审计;通道层(mcp_gate)
        负责校验调用方恰提供其一。

        完整事务函数超过 80 行的约束豁免(spec 决策 30「完整事务允许有
        明确理由的例外」):锁前预检与锁内最终核对/落盘/回滚必须作为一个
        不可分割的顺序保留在同一职责内,拆开会让调用方有机会跳过其中一步。
        例外以既有回归证明:票 12 的 local_write/review_fix/boundary 主题
        逐条覆盖撤销、路径竞态、占用、版本、权限位与回滚。
        """

        host = self._host
        payload = content.encode("utf-8") if data is None else data
        policy = host._policy()
        if policy is None:
            return host._deny("write", "policy", POLICY_MISSING_REASON,
                              token, None, {}, path, note)
        record, reason = host._resolve_instance(token)
        if record is None:
            return host._deny("write", "identity", reason, token, None, policy, path, note)
        resolved, rel, reason = resolve_target(policy, path)
        if resolved is None:
            return host._deny("write", "path", reason, token, record, policy, path, note)
        pre_grant = grant_denial(record, policy, rel)
        if pre_grant is not None:
            return host._deny("write", pre_grant[0], pre_grant[1],
                              token, record, policy, rel, note)

        denial: tuple[str, str, str] | None = None
        result: dict | None = None
        with host._locked():
            # —— 临界区内最终核对(R1):以锁内重读的策略与登记为准。
            # 先重读身份再重读策略:策略失效时拒绝记录仍携带最新身份归属 ——
            record, reason = host._resolve_instance(token)
            if record is None:
                denial = ("write", "identity", reason)
            if denial is None:
                policy = host._policy()
                if policy is None:
                    denial = ("write", "policy", POLICY_MISSING_REASON)
            if denial is None:
                resolved, rel, reason = resolve_target(policy, path)
                if resolved is None:
                    denial = ("write", "path", reason)
            if denial is None:
                grant = grant_denial(record, policy, rel)
                if grant is not None:
                    denial = ("write", grant[0], grant[1])
            if denial is None:
                # 占用判定经登记职责:locks.json 的条目形状不在本模块解释。
                conflict = host._occupancy_conflict(rel, record["instance_id"])
                if conflict is not None:
                    denial = ("write", "occupancy", conflict)
                elif expected_sha256 is not None:
                    # 版本校验在锁内读取(02 已知边界:消除读取与占用之间的调度窗口)
                    if resolved.exists():
                        current = sha256_bytes(resolved.read_bytes())
                        if expected_sha256.lower() != current:
                            denial = ("write", "version",
                                      f"expected sha256 {expected_sha256} != current {current}")
                    elif expected_sha256.lower() != "absent":
                        denial = ("write", "version",
                                  f"target absent but expected {expected_sha256}")
            if denial is None:
                # 路径竞态复检:占用与版本校验期间目标树可能被换链
                re_resolved, re_rel, _ = resolve_target(policy, path)
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
                parent_fd = open_pinned_parent(policy["project_root"], resolved)
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
                                "written_sha256": sha256_bytes(payload),
                                "bytes": len(payload),
                                "basis": host._basis(policy),
                                "note": note,
                            }
                            tmp_name = ".mgs-write-" + secrets.token_hex(6)
                            try:
                                write_pinned_temp(parent_fd, tmp_name,
                                                  payload, existing_mode)
                                os.replace(tmp_name, base,
                                           src_dir_fd=parent_fd, dst_dir_fd=parent_fd)
                                host._occupy(rel, record["instance_id"])
                                host._audit_unlocked(result)
                            except Exception as exc:
                                # 落盘后状态记录失败:回滚已写入字节,失效闭合。
                                # 「无审计则无生效写入」,宁可拒绝也不留下无记录写入。
                                rollback(parent_fd, base, backup,
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
            return host._deny(denial[0], denial[1], denial[2],
                              token, record,
                              policy if policy is not None else {},
                              rel or path, note)
        return result

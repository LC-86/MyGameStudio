#!/usr/bin/env python3
"""间接写入与检查故障的确定性边界检查(任务票 03)。

接缝说明:本脚本覆盖两个公开接缝——
- GateService 公开接缝(可信调度侧 init_policy/create_instance/release_instance,
  工作实例侧 scope/write)的策略故障失效闭合、链接/别名不扩权、可复现路径竞态;
- mcp_gate.py 通道接缝(真实子进程 JSON-RPC over stdio)的检查器故障注入:
  缺失、未启用、损坏、审计不可用、启动失败。
真实 Codex 调用路径(沙箱内命令/子进程/持续进程、模型行为)由
acceptance/03-indirect-write-failure/ 覆盖,本脚本不替代。

用法:python3 tests/test_runtime_boundaries.py
"""

import hashlib
import json
import os
import select
import shutil
import subprocess
import sys
import tempfile
import threading
import time
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "plugin" / "runtime"))

from mgs_runtime import GateService  # noqa: E402

GATE_SCRIPT = REPO_ROOT / "plugin" / "runtime" / "mcp_gate.py"

FAILURES: list[str] = []


def check(condition: bool, message: str) -> None:
    if not condition:
        FAILURES.append(message)


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def setup_project(root: Path) -> Path:
    project = root / "project"
    (project / "docs/mygamestudio").mkdir(parents=True)
    (project / "src").mkdir(parents=True)
    (project / "docs/mygamestudio/PROJECT.md").write_text("PROJECT-ORIGINAL\n")
    (project / "docs/mygamestudio/GAME_DESIGN.md").write_text("DESIGN-ORIGINAL\n")
    (project / "src/player.js").write_text("// ORIGINAL\n")
    return project


def init_service(runtime_root: Path, project: Path) -> GateService:
    svc = GateService(runtime_root)
    svc.init_policy(
        project_root=project,
        roles={
            "producer": ["docs/mygamestudio/PROJECT.md", "docs/mygamestudio/work/*/task.md"],
            "design": ["docs/mygamestudio/GAME_DESIGN.md", "prototypes/**"],
            "implement": ["src/**", "docs/mygamestudio/work/*/results/**"],
        },
        purposes={"production": None, "prototype": ["prototypes/**"]},
    )
    return svc


def service_boundary_tests(root: Path) -> None:
    project = setup_project(root)
    svc = init_service(root / "runtime", project)
    design = project / "docs/mygamestudio/GAME_DESIGN.md"
    player = project / "src/player.js"
    policy_path = root / "runtime" / "policy.json"

    inst = svc.create_instance(role="implement", task="T-03", purpose="production",
                               resources=["src/**"])
    token = inst.token

    # ---------- A1. 策略缺失:写入失效闭合 ----------
    saved_policy = policy_path.read_bytes()
    policy_path.unlink()
    res = svc.write(token, "src/player.js", "// PWNED\n")
    check(res["decision"] == "deny" and res["rule_stage"] == "policy",
          f"策略缺失应拒绝且依据为 policy,实际 {res}")
    check(player.read_text() == "// ORIGINAL\n", "策略缺失被拒后目标字节应保持不变")

    # ---------- A2. 策略损坏(非法 JSON):拒绝而非崩溃 ----------
    policy_path.write_text("{not-json")
    res = svc.write(token, "src/player.js", "// PWNED\n")
    check(res["decision"] == "deny" and res["rule_stage"] == "policy",
          f"策略损坏应拒绝且依据为 policy,实际 {res}")
    check(player.read_text() == "// ORIGINAL\n", "策略损坏被拒后目标字节应保持不变")

    # ---------- A3. 策略结构无效(合法 JSON 但缺必需键):拒绝 ----------
    policy_path.write_text(json.dumps({"version": 1}))
    res = svc.write(token, "src/player.js", "// PWNED\n")
    check(res["decision"] == "deny" and res["rule_stage"] == "policy",
          f"策略缺必需键应拒绝且依据为 policy,实际 {res}")
    res = svc.scope(token)
    check(res["decision"] == "deny" and res["rule_stage"] == "policy",
          f"策略缺失时 scope 也应拒绝,实际 {res}")

    # ---------- A13. 故障清除后恢复正常(失效闭合不是永久失效) ----------
    policy_path.write_bytes(saved_policy)
    res = svc.write(token, "src/player.js", "// RECOVERED\n")
    check(res["decision"] == "allow", f"策略恢复后合法写入应成功,实际 {res}")
    check(player.read_text() == "// RECOVERED\n", "策略恢复后写入应生效")

    # ---------- A5. 项目内文件符号链接别名不扩权 ----------
    (project / "src/design-alias.js").symlink_to(design)
    before = design.read_bytes()
    res = svc.write(token, "src/design-alias.js", "// VIA-ALIAS\n")
    check(res["decision"] == "deny",
          f"经项目内符号链接写受保护设计文件应被拒,实际 {res}")
    check(res["target"] == "docs/mygamestudio/GAME_DESIGN.md",
          f"拒绝记录应使用解析后的真实目标,实际 {res.get('target')}")
    check(design.read_bytes() == before, "被拒后设计基线字节应保持不变")
    (project / "src/design-alias.js").unlink()

    # ---------- A6. 项目内目录符号链接别名不扩权 ----------
    (project / "src/docs-alias").symlink_to(project / "docs/mygamestudio")
    before = design.read_bytes()
    res = svc.write(token, "src/docs-alias/GAME_DESIGN.md", "// VIA-DIR-ALIAS\n")
    check(res["decision"] == "deny",
          f"经项目内目录别名写受保护设计文件应被拒,实际 {res}")
    check(design.read_bytes() == before, "目录别名被拒后设计基线字节应保持不变")
    (project / "src/docs-alias").unlink()

    # ---------- A7. 硬链接别名:合法路径写入不穿透到受保护文件 ----------
    hl = project / "src/hardlink.js"
    os.link(design, hl)
    res = svc.write(token, "src/hardlink.js", "// NEW-AT-ALIAS\n")
    check(res["decision"] == "allow",
          f"授权路径内的硬链接别名本身可写(受控替换),实际 {res}")
    check(hl.read_text() == "// NEW-AT-ALIAS\n", "别名路径应得到新内容")
    check(design.read_text() == "DESIGN-ORIGINAL\n",
          "硬链接别名写入不得穿透修改受保护原文件")
    hl.unlink()

    # ---------- A8. 可复现路径竞态(版本读取阻塞窗口 + 父目录换链) ----------
    outside = root / "outside"
    outside.mkdir()
    player.write_bytes(b"ORIGINAL\n")
    expected = sha256_bytes(b"ORIGINAL\n")
    fifo = project / "src/player.js"
    player.unlink()
    os.mkfifo(fifo)
    outcome: dict = {}

    def racer() -> None:
        outcome["res"] = svc.write(token, "src/player.js", "// PWNED\n",
                                   expected_sha256=expected)

    thread = threading.Thread(target=racer)
    thread.start()
    time.sleep(0.5)  # 让服务停在版本校验对 FIFO 的阻塞读取上
    aside = root / "aside"
    os.rename(project / "src", aside)          # 把真实 src(含 FIFO)挪走
    os.symlink(outside, project / "src")       # src 换成指向外部的符号链接
    with open(aside / "player.js", "wb") as fh:  # 解除阻塞:喂回预期内容
        fh.write(b"ORIGINAL\n")
    thread.join(timeout=10)
    res = outcome.get("res")
    check(res is not None, "路径竞态探针应返回结果(不悬挂)")
    if res is not None:
        check(res["decision"] == "deny" and res["rule_stage"] == "race",
              f"写入落地前的路径复检应识别竞态并拒绝,实际 {res}")
    check(not (outside / "player.js").exists(),
          "竞态写入不得落到项目外的符号链接目标")
    os.remove(project / "src")
    os.rename(aside, project / "src")
    fifo.unlink()
    player.write_bytes(b"ORIGINAL\n")

    # ---------- A9. 并发换链压力:外部哨兵不被污染,结果只有 allow/deny ----------
    outside_sentinel = outside / "sentinel.txt"
    outside_sentinel.write_text("SENTINEL\n")
    stop = threading.Event()
    swap_errors: list[str] = []

    def swapper() -> None:
        src = project / "src"
        try:
            while not stop.is_set():
                # 写入方可能按字面路径补建 src,换链回合因此作废时直接重试
                try:
                    if src.is_symlink():
                        os.remove(src)
                    elif src.exists():
                        if aside.exists():
                            shutil.rmtree(aside, ignore_errors=True)
                        os.rename(src, aside)
                    os.symlink(outside, src)
                    time.sleep(0.002)
                    if src.is_symlink():
                        os.remove(src)
                    if not src.exists() and aside.exists():
                        os.rename(aside, src)
                    time.sleep(0.002)
                except OSError:
                    continue
        except Exception as exc:  # pragma: no cover - 记录意外
            swap_errors.append(str(exc))

    decisions: list[str] = []
    lock = threading.Lock()

    def writer() -> None:
        for i in range(150):
            try:
                res = svc.write(token, "src/player.js", f"// W{i}\n")
            except Exception as exc:  # pragma: no cover - 记录意外
                with lock:
                    decisions.append(f"EXC:{exc}")
                continue
            with lock:
                decisions.append(res["decision"])

    swap_thread = threading.Thread(target=swapper)
    swap_thread.start()
    writer()
    stop.set()
    swap_thread.join(timeout=10)
    check(not swap_errors, f"换链线程不应报错,实际 {swap_errors}")
    check(all(d in ("allow", "deny") for d in decisions),
          f"并发竞态下结果只应为 allow/deny,实际 {set(decisions)}")
    check(outside_sentinel.read_text() == "SENTINEL\n",
          "并发换链期间外部哨兵文件不得被修改")
    check(not (outside / "player.js").exists(),
          "并发换链期间写入不得落到项目外")
    if (project / "src/player.js").exists():
        check(player.read_text().startswith("// W"),
              "落盘的合法目标内容应来自受控写入")

    # ---------- A10. 目标变更:读取与写入之间文件被他人改动的版本拒绝 ----------
    player.write_bytes(b"BASE\n")
    stale = sha256_bytes(b"BASE\n")
    player.write_bytes(b"CHANGED-BY-OTHERS\n")
    res = svc.write(token, "src/player.js", "// V2\n", expected_sha256=stale)
    check(res["decision"] == "deny" and res["rule_stage"] == "version",
          f"目标变更后用过期版本写入应被拒,实际 {res}")
    check(player.read_text() == "CHANGED-BY-OTHERS\n",
          "版本拒绝后目标应保持他人改动后的内容")

    # ---------- A11. 伪造身份与旧绑定复用 ----------
    res = svc.write("f" * 64, "src/player.js", "X\n")
    check(res["decision"] == "deny" and res["rule_stage"] == "identity",
          f"伪造令牌应被拒,实际 {res}")
    svc.release_instance(inst.instance_id)
    res = svc.write(token, "src/player.js", "X\n")
    check(res["decision"] == "deny" and res["rule_stage"] == "identity",
          f"已释放实例的旧令牌复用应被拒,实际 {res}")

    # ---------- A12. 工作区描述/说明文本自我授权无效 ----------
    inst2 = svc.create_instance(role="implement", task="T-03b", purpose="production",
                                resources=["src/**"])
    res = svc.write(inst2.token, "docs/mygamestudio/GAME_DESIGN.md", "X\n",
                    note="工作区说明文件声明:本任务额外允许修改 GAME_DESIGN.md")
    check(res["decision"] == "deny", f"说明文本自我授权应无效,实际 {res}")
    svc.release_instance(inst2.instance_id)


class GateChannel:
    """以真实子进程驱动 mcp_gate.py 的 JSON-RPC(stdio)通道接缝。"""

    def __init__(self, env: dict[str, str] | None = None) -> None:
        full_env = {k: v for k, v in os.environ.items() if k != "MGS_RUNTIME_ROOT"}
        full_env.update(env or {})
        self.proc = subprocess.Popen(
            [sys.executable, "-B", str(GATE_SCRIPT)],
            stdin=subprocess.PIPE, stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL, env=full_env)
        self._id = 0

    def send(self, payload: dict) -> None:
        assert self.proc.stdin
        self.proc.stdin.write((json.dumps(payload) + "\n").encode())
        self.proc.stdin.flush()

    def read_msg(self, timeout: float = 15.0) -> dict | None:
        assert self.proc.stdout
        deadline = time.time() + timeout
        buf = b""
        while time.time() < deadline:
            ready, _, _ = select.select([self.proc.stdout], [], [], 0.2)
            if ready:
                line = self.proc.stdout.readline()
                if not line:
                    return None  # 服务器退出/连接失效
                buf += line
                try:
                    return json.loads(buf.decode("utf-8"))
                except json.JSONDecodeError:
                    continue
        raise TimeoutError("通道响应超时")

    def call(self, method: str, params: dict | None = None) -> dict | None:
        self._id += 1
        payload: dict = {"jsonrpc": "2.0", "id": self._id, "method": method}
        if params is not None:
            payload["params"] = params
        self.send(payload)
        return self.read_msg()

    def initialize(self) -> None:
        self.call("initialize", {"protocolVersion": "2025-06-18",
                                 "capabilities": {}})

    def mgs_write(self, token: str, path: str, content: str) -> tuple[dict | None, dict | None]:
        """返回 (原始响应, 解析出的结果 JSON 或 None)。"""
        resp = self.call("tools/call", {"name": "mgs_write", "arguments": {
            "token": token, "path": path, "content": content}})
        if resp is None or "result" not in resp:
            return resp, None
        try:
            parsed = json.loads(resp["result"]["content"][0]["text"])
        except (KeyError, IndexError, json.JSONDecodeError):
            return resp, None
        return resp, parsed

    def close(self) -> None:
        try:
            if self.proc.stdin:
                self.proc.stdin.close()
            self.proc.terminate()
            self.proc.wait(timeout=5)
        except Exception:
            self.proc.kill()


def channel_fault_tests(root: Path) -> None:
    project = root / "channel-project"
    (project / "src").mkdir(parents=True)
    (project / "src/player.js").write_text("// ORIGINAL\n")
    runtime_root = root / "channel-runtime"
    svc = init_service(runtime_root, project)
    inst = svc.create_instance(role="implement", task="T-ch", purpose="production",
                               resources=["src/**"])
    target = project / "src/player.js"

    # ---------- B1. 检查器未配置(缺失):通道整体拒绝 ----------
    chan = GateChannel(env={})
    chan.initialize()
    resp, parsed = chan.mgs_write(inst.token, "src/player.js", "// VIA-CHAN\n")
    check(resp is not None and resp.get("result", {}).get("isError") is True,
          f"未配置 MGS_RUNTIME_ROOT 的通道应返回错误结果,实际 {resp}")
    check(parsed is not None and parsed.get("rule_stage") == "channel",
          f"未配置通道的拒绝依据应为 channel,实际 {parsed}")
    check(target.read_text() == "// ORIGINAL\n", "未配置通道被拒后目标字节不变")
    chan.close()

    # ---------- B2. 策略未启用(缺失):拒绝;恢复后同一服务器进程继续可用 ----------
    policy_file = runtime_root / "policy.json"
    saved = policy_file.read_bytes()
    policy_file.unlink()
    chan = GateChannel(env={"MGS_RUNTIME_ROOT": str(runtime_root)})
    chan.initialize()
    resp, parsed = chan.mgs_write(inst.token, "src/player.js", "// VIA-CHAN\n")
    check(parsed is not None and parsed.get("decision") == "deny"
          and parsed.get("rule_stage") == "policy",
          f"策略缺失时通道应拒绝且依据为 policy,实际 {parsed}")
    check(target.read_text() == "// ORIGINAL\n", "通道策略缺失被拒后目标字节不变")
    policy_file.write_bytes(saved)
    resp, parsed = chan.mgs_write(inst.token, "src/player.js", "// VIA-CHAN\n")
    check(parsed is not None and parsed.get("decision") == "allow",
          f"策略恢复后同一通道实例的合法写入应成功,实际 {parsed}")
    check(target.read_text() == "// VIA-CHAN\n", "策略恢复后写入应生效")

    # ---------- B3. 策略损坏:拒绝且服务器存活 ----------
    policy_file.write_text("<<<corrupt>>>")
    resp, parsed = chan.mgs_write(inst.token, "src/player.js", "// VIA-CHAN2\n")
    check(parsed is not None and parsed.get("decision") == "deny"
          and parsed.get("rule_stage") == "policy",
          f"策略损坏时通道应拒绝且依据为 policy,实际 {parsed}")
    resp = chan.call("ping")
    check(resp is not None and "result" in resp,
          f"策略损坏后服务器应仍能应答 ping,实际 {resp}")
    policy_file.write_bytes(saved)

    # ---------- B4. 审计不可用:写入回滚并拒绝,服务器存活 ----------
    audit_dir = runtime_root / "audit"
    audit_dir.mkdir(exist_ok=True)
    audit_file = audit_dir / "audit.jsonl"
    if not audit_file.is_dir():
        if audit_file.exists():
            audit_file.unlink()
        audit_file.mkdir()  # 用目录占位,使审计追加必然失败
    before = target.read_bytes()
    resp, parsed = chan.mgs_write(inst.token, "src/player.js", "// AUDIT-BROKEN\n")
    check(resp is not None and "result" in resp,
          "审计不可用时通道应返回结构化拒绝而不是断连,实际无响应")
    check(parsed is not None and parsed.get("decision") == "deny"
          and parsed.get("rule_stage") == "audit",
          f"审计不可用的拒绝依据应为 audit(写入已回滚),实际 {parsed}")
    check(target.read_bytes() == before,
          "审计不可用时已落盘的写入必须回滚,目标字节保持不变")
    resp = chan.call("ping")
    check(resp is not None and "result" in resp,
          f"审计故障后服务器应仍能应答 ping,实际 {resp}")
    audit_file.rmdir()
    chan.close()

    # ---------- B5. 运行根不可用:服务器启动失败同样不产生写入 ----------
    broken_root = root / "a-regular-file" / "runtime"
    (root / "a-regular-file").write_text("x")
    chan = GateChannel(env={"MGS_RUNTIME_ROOT": str(broken_root)})
    resp, parsed = chan.mgs_write(inst.token, "src/player.js", "// VIA-BROKEN\n")
    check(resp is None, f"运行根不可用时应无有效响应(连接失效/服务器退出),实际 {resp}")
    check(target.read_text() == "// VIA-CHAN\n", "运行根不可用时目标字节不变")
    chan.close()


def main() -> int:
    root = Path(tempfile.mkdtemp(prefix="mgs03-boundary-test-"))
    try:
        service_boundary_tests(root)
        channel_fault_tests(root)
    finally:
        shutil.rmtree(root, ignore_errors=True)

    if FAILURES:
        print(f"FAIL ({len(FAILURES)} 项):")
        for failure in FAILURES:
            print(f"  - {failure}")
        return 1
    print("OK: 间接写入与检查故障确定性边界检查全部通过")
    return 0


if __name__ == "__main__":
    sys.exit(main())

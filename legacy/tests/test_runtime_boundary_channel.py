#!/usr/bin/env python3
"""mgs-gate 通道接缝的检查器故障注入(真实子进程 JSON-RPC)。

任务票 12 从 tests/test_runtime_boundaries.py 拆出;每条 check 的条件、消息
与断言对象与原案例逐字一致,仅重组位置与临时根。覆盖检查器未配置、策略
未启用/损坏、审计不可用回滚与存活、运行根不可用的启动失败。判定经真实
子进程 stdio 通道(mcp_gate.py)作出,不使用正则截取源码。原总入口仍聚合
本主题。本主题可直接运行:

    python3 -B tests/test_runtime_boundary_channel.py
"""

import shutil
import sys
import tempfile
from pathlib import Path

from runtime_boundary_support import GateChannel, init_service, make_checker, run_theme

FAILURES, check = make_checker()


def test_channel_faults() -> None:
    root = Path(tempfile.mkdtemp(prefix="mgs03-boundary-chan-"))
    try:
        project = root / "channel-project"
        (project / "src").mkdir(parents=True)
        (project / "src/player.js").write_text("// ORIGINAL\n")
        runtime_root = root / "channel-runtime"
        svc = init_service(runtime_root, project)
        inst = svc.create_instance(role="implement", task="T-ch", purpose="production",
                                   resources=["src/**"])
        S = {"root": root, "project": project, "runtime_root": runtime_root,
             "inst": inst, "target": project / "src/player.js"}
        _channel_missing(S)
        chan = _channel_policy(S)
        try:
            _channel_audit_and_broken_root(S, chan)
        finally:
            chan.close()
    finally:
        shutil.rmtree(root, ignore_errors=True)


def _channel_missing(S) -> None:
    """B1:检查器未配置(缺失),通道整体拒绝。"""

    inst, target = S["inst"], S["target"]

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


def _channel_policy(S):
    """B2-B3:策略未启用/损坏时拒绝且服务器存活;返回复用的通道。"""

    runtime_root, inst, target = S["runtime_root"], S["inst"], S["target"]

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
    return chan


def _channel_audit_and_broken_root(S, chan) -> None:
    """B4-B5:审计不可用回滚且存活;运行根不可用启动失败不产生写入。"""

    root, inst, target = S["root"], S["inst"], S["target"]
    runtime_root = S["runtime_root"]

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

    # ---------- B5. 运行根不可用:服务器启动失败同样不产生写入 ----------
    broken_root = root / "a-regular-file" / "runtime"
    (root / "a-regular-file").write_text("x")
    chan = GateChannel(env={"MGS_RUNTIME_ROOT": str(broken_root)})
    resp, parsed = chan.mgs_write(inst.token, "src/player.js", "// VIA-BROKEN\n")
    check(resp is None, f"运行根不可用时应无有效响应(连接失效/服务器退出),实际 {resp}")
    check(target.read_text() == "// VIA-CHAN\n", "运行根不可用时目标字节不变")
    chan.close()


TESTS = (test_channel_faults,)

if __name__ == "__main__":
    sys.exit(run_theme("mgs-gate 通道检查器故障注入", TESTS, FAILURES))

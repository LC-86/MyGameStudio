#!/usr/bin/env python3
"""审查修复批 R1–R4 的反例固化(本地撤销/purpose 缺省/权限位/远端审计)。

任务票 12 从 tests/test_runtime_gate.py 的原始总入口按真实行为主题拆出;
每条 check 的条件、消息与断言对象与原案例逐字一致,仅重组位置。R1/R2/R3
为本地写入反例,R4(含 R2-remote、R1-remote)为远端审计反例。原总入口仍
聚合本主题。本主题可直接运行:

    python3 -B tests/test_runtime_gate_review_fix.py

反例底稿:.scratch/mygamestudio-v1-review-fixes/evidence/runtime-probes.py
(2026-09-09 独立审查在 HEAD 6b2444b 复现四项运行保障缺陷)。
"""

import hashlib
import json
import shutil
import stat
import sys
import tempfile
import threading
from pathlib import Path

from runtime_gate_support import (
    REPO_ROOT, GateService, audit_lines, make_checker, mcp_gate, run_theme,
)

sys.path.insert(0, str(REPO_ROOT / "tests"))
import test_github_backend as gh_fixtures  # noqa: E402  (远端替身与项目夹具)
sys.path.insert(0, str(REPO_ROOT / "plugin" / "records"))

FAILURES, check = make_checker()


def _r1_inflight_local_revoke(root: Path) -> None:
    """R1:撤销完成后,在途写入必须拒绝且目标保持原状。"""

    r1 = root / "r1"
    r1_project = r1 / "project"
    (r1_project / "src").mkdir(parents=True)
    (r1_project / "src/keep.txt").write_text("KEEP\n")
    writer = GateService(r1 / "runtime")
    admin = GateService(r1 / "runtime")
    writer.init_policy(r1_project, {"implement": ["src/**"]},
                       {"production": None})
    r1_inst = writer.create_instance("implement", "T-r1", "production",
                                     ["src/**"])
    original_resolve = writer._resolve_instance
    identity_checked = threading.Event()
    resume = threading.Event()
    outcome: dict = {}

    def pause_after_identity(token):
        resolved = original_resolve(token)
        identity_checked.set()
        assert resume.wait(5)
        return resolved

    writer._resolve_instance = pause_after_identity

    def inflight() -> None:
        outcome["res"] = writer.write(r1_inst.token, "src/inflight.txt",
                                      "STALE\n")

    thread = threading.Thread(target=inflight)
    thread.start()
    check(identity_checked.wait(5), "R1 探针应先停在锁外身份解析")
    revoke = admin.release_instance(r1_inst.instance_id)  # 撤销先于写线程恢复完成
    resume.set()
    thread.join(5)
    check(not thread.is_alive(), "R1 在途写线程应在撤销后返回")
    writer._resolve_instance = original_resolve
    res = outcome.get("res")
    check(revoke["found"], "R1:撤销应成功")
    check(res["decision"] == "deny" and res["rule_stage"] == "identity",
          f"R1:撤销完成后在途写入必须以 identity 拒绝,实际 {res}")
    check(not (r1_project / "src/inflight.txt").exists(),
          "R1:被拒的在途写入不得落盘")
    check((r1_project / "src/keep.txt").read_text() == "KEEP\n",
          "R1:既有目标字节应保持不变")


def _r2_purpose_missing_local(root: Path) -> None:
    """R2:用途条目缺失 ≠ 显式不额外限制(故障闭合)。"""

    r2 = root / "r2"
    r2_project = r2 / "project"
    (r2_project / "src").mkdir(parents=True)
    r2_svc = GateService(r2 / "runtime")
    r2_svc.init_policy(r2_project, {"implement": ["src/**", "prototypes/**"]},
                       {"production": None, "prototype": ["prototypes/**"]})
    proto = r2_svc.create_instance("implement", "T-r2", "prototype",
                                   ["src/**", "prototypes/**"])
    before = r2_svc.write(proto.token, "src/escaped.txt", "BYPASS\n")
    check(before["decision"] == "deny" and before["rule_stage"] == "purpose",
          f"R2:条目存在时 prototype 用途写 src 应被拒,实际 {before}")
    r2_policy_path = r2 / "runtime" / "policy.json"
    r2_policy = json.loads(r2_policy_path.read_text())
    del r2_policy["purposes"]["prototype"]  # 条目丢失,不是「显式不额外限制」
    r2_policy_path.write_text(json.dumps(r2_policy))
    after = r2_svc.write(proto.token, "src/escaped.txt", "BYPASS\n")
    check(after["decision"] == "deny" and after["rule_stage"] == "purpose",
          f"R2:用途条目缺失时同一写入必须仍被拒(故障闭合),实际 {after}")
    check(not (r2_project / "src/escaped.txt").exists(),
          "R2:被拒写入不得落盘")
    scope_info = r2_svc.scope(proto.token)
    check(scope_info["decision"] == "deny"
          and scope_info["rule_stage"] == "purpose",
          f"R2:scope 对缺失用途条目同样失效闭合,实际 {scope_info}")
    prod = r2_svc.create_instance("implement", "T-r2-prod", "production",
                                  ["src/**"])
    ok_write = r2_svc.write(prod.token, "src/ok.txt", "OK\n")
    check(ok_write["decision"] == "allow",
          f"R2:显式空条目(restrict=None)保持「不额外限制」语义,实际 {ok_write}")
    r2_policy["purposes"]["prototype"] = {"oops": True}  # 条目形状无效
    r2_policy_path.write_text(json.dumps(r2_policy))
    broken = r2_svc.write(prod.token, "src/ok2.txt", "X\n")
    check(broken["decision"] == "deny" and broken["rule_stage"] == "policy",
          f"R2:用途条目结构无效应按策略不完整拒绝,实际 {broken}")
    check(not (r2_project / "src/ok2.txt").exists(),
          "R2:策略无效时不得落盘")


def _r3_mode_and_rollback(root: Path) -> None:
    """R3:内容更新(含回滚)保留既有目标的权限位。"""

    r3 = root / "r3"
    r3_project = r3 / "project"
    (r3_project / "src").mkdir(parents=True)
    r3_svc = GateService(r3 / "runtime")
    r3_svc.init_policy(r3_project, {"implement": ["src/**"]},
                       {"production": None})
    r3_inst = r3_svc.create_instance("implement", "T-r3", "production",
                                     ["src/**"])
    for name, mode_bits in (("run.sh", 0o755), ("private.txt", 0o600),
                            ("normal.txt", 0o644)):
        target = r3_project / "src" / name
        target.write_text("old\n")
        target.chmod(mode_bits)
        res = r3_svc.write(r3_inst.token, f"src/{name}", "new\n",
                           expected_sha256=hashlib.sha256(b"old\n").hexdigest())
        actual = stat.S_IMODE(target.stat().st_mode)
        check(res["decision"] == "allow",
              f"R3:{name} 合法内容更新应放行,实际 {res}")
        check(actual == mode_bits,
              f"R3:{name} 内容更新后权限位应保持 {oct(mode_bits)},"
              f"实际 {oct(actual)}")
    res = r3_svc.write(r3_inst.token, "src/fresh.txt", "fresh\n")
    # 新建文件按默认 0644 创建;umask 只做减法,断言属主读写位必然在
    # (umask 敏感性:不在本票范围,既有新建语义保持不变)
    fresh_mode = stat.S_IMODE((r3_project / "src/fresh.txt").stat().st_mode)
    check(res["decision"] == "allow" and fresh_mode & 0o600 == 0o600,
          f"R3:新建文件应正常落盘(实际权限 {oct(fresh_mode)}),实际 {res}")
    r3_audit = r3 / "runtime" / "audit" / "audit.jsonl"
    r3_audit.unlink()
    r3_audit.mkdir()  # 审计不可用 → 落盘后回滚
    script = r3_project / "src/run.sh"
    res = r3_svc.write(r3_inst.token, "src/run.sh", "ROLLED\n")
    check(res["decision"] == "deny" and res["rule_stage"] == "audit",
          f"R3:审计不可用应回滚并拒绝,实际 {res}")
    check(script.read_text() == "new\n"
          and stat.S_IMODE(script.stat().st_mode) == 0o755,
          "R3:回滚后内容与权限位都应恢复原状(0755 不得被降级)")
    r3_audit.rmdir()


def _r4_fixture(root: Path) -> dict:
    """搭建 R4/R2-remote/R1-remote 共用的远端受控操作夹具。"""

    r4 = root / "r4"
    r4_project = gh_fixtures.make_github_project(r4 / "project")
    r4_svc = GateService(r4 / "runtime")
    r4_resources = ["github://github.com/mygamestudio/issue-accept/issues/**"]
    r4_svc.init_policy(r4_project, {"producer": r4_resources},
                       {"production": None})
    r4_inst = r4_svc.create_instance("producer", "T-r4", "production",
                                     r4_resources)
    r4_svc._write_json("remote.json", {"github": {
        "api_base": "http://unused.invalid", "token_env": "MGS_TEST_UNUSED",
        "cache_dir": str(r4 / "cache")}})
    transport = gh_fixtures.FakeTransport()
    transport.seed_issue("01-task", "Existing")

    class Facade:
        def remote_record(self, token, action, payload):
            return r4_svc.remote_record(token, action, payload,
                                        transport=transport)

    def mgs_remote(action: str, payload: dict) -> dict:
        response = mcp_gate.handle_tools_call(
            Facade(), "mgs_remote",
            {"token": r4_inst.token, "action": action, "payload": payload})
        return json.loads(response["content"][0]["text"])

    return {"r4": r4, "svc": r4_svc, "inst": r4_inst, "transport": transport,
            "audit": r4 / "runtime" / "audit" / "audit.jsonl",
            "mgs_remote": mgs_remote, "resources": r4_resources}


def _r4_audit_intent(S) -> None:
    """R4a/R4b:审计不可用不执行远端动作;结果审计失败如实回报。"""

    r4_svc, r4_inst = S["svc"], S["inst"]
    transport, r4_audit, mgs_remote = S["transport"], S["audit"], S["mgs_remote"]

    # R4a:审计不可用时,远端动作不得执行;MCP 入口如实拒绝,
    #     不出现「远端已新增评论却报告拒绝且无审计」。
    r4_audit.unlink()
    r4_audit.mkdir()
    body = mgs_remote("append-result", {"identity": "01-task",
                                        "result_markdown": "审计不可用"})
    check(body["decision"] == "deny" and body["rule_stage"] == "audit",
          f"R4:审计不可用时远端写入应在执行前拒绝(意图无法持久记录),实际 {body}")
    check(len(transport.comments[1]) == 0,
          "R4:审计不可用时不得执行远端动作(替身零新增评论)")
    check(not r4_audit.is_file(), "R4:审计路径不可写时不得伪造审计文件")
    r4_audit.rmdir()

    # R4b:意图已持久记录、结果审计追加失败:远端结果如实回报,
    #     不包装成拒绝,不静默丢弃记录责任。
    real_audit_unlocked = r4_svc._audit_unlocked
    audit_calls = {"n": 0}

    def flaky_audit_unlocked(entry):
        audit_calls["n"] += 1
        if audit_calls["n"] >= 2:  # 第 1 次(意图)落盘,第 2 次(结果)失败
            raise OSError("injected outcome-audit failure")
        return real_audit_unlocked(entry)

    r4_svc._audit_unlocked = flaky_audit_unlocked
    try:
        res = r4_svc.remote_record(
            r4_inst.token, "append-result",
            {"identity": "01-task", "result_markdown": "结果审计失败"},
            transport=transport)
    finally:
        r4_svc._audit_unlocked = real_audit_unlocked
    check(res["decision"] == "allow" and res.get("audit_recorded") is False,
          f"R4:远端动作已生效时不得包装成拒绝,应如实回报并标注审计未记录,"
          f"实际 {res}")
    check("granted by" in res.get("reason", ""),
          f"R4:结果审计失败的回报应保留策略依据 reason,实际 {res.get('reason')}")
    check(len(transport.comments[1]) == 1,
          "R4:结果审计失败不应否认已发生的远端写入")
    r4_entries = audit_lines(S["r4"] / "runtime")
    check(any(e.get("op") == "remote:append-result"
              and e.get("decision") == "intent" for e in r4_entries),
          "R4:远端写入意图应先于执行持久记录")
    check(not any(e.get("op") == "remote:append-result"
                  and e.get("decision") == "allow" for e in r4_entries),
          "R4:结果审计失败时不得伪造已记录的结果条目")


def _r4_purpose_and_revoke(S) -> None:
    """R2-remote 用途条目缺失失效闭合;R1-remote 在途远端写入撤销拒绝。"""

    r4_svc, r4_inst = S["svc"], S["inst"]
    transport, r4 = S["transport"], S["r4"]

    # R2-remote:用途条目缺失对远端路径同样失效闭合(同类缺省逻辑)。
    r4_policy_path = r4 / "runtime" / "policy.json"
    r4_policy = json.loads(r4_policy_path.read_text())
    del r4_policy["purposes"]["production"]
    r4_policy_path.write_text(json.dumps(r4_policy))
    res = r4_svc.remote_record(
        r4_inst.token, "append-result",
        {"identity": "01-task", "result_markdown": "条目缺失"},
        transport=transport)
    check(res["decision"] == "deny" and res["rule_stage"] == "purpose",
          f"R2:用途条目缺失时远端操作必须拒绝,实际 {res}")
    check(len(transport.comments[1]) == 1, "R2:远端拒绝时不得产生新评论")
    r4_policy["purposes"]["production"] = {"restrict": None}
    r4_policy_path.write_text(json.dumps(r4_policy))
    res = r4_svc.remote_record(
        r4_inst.token, "append-result",
        {"identity": "01-task", "result_markdown": "条目恢复"},
        transport=transport)
    check(res["decision"] == "allow"
          and res.get("audit_recorded") is None
          and len(transport.comments[1]) == 2,
          f"R2:恢复显式空条目后远端写入应回到放行,实际 {res}")

    # R1-remote:撤销完成后,在途远端写入同样拒绝(远端零调用)。
    # 与本地 R1 同一时序:写线程停在锁外身份解析后,撤销先完成再恢复。
    # R1-remote:撤销完成后,在途远端写入同样拒绝(远端零调用)。
    # 与本地 R1 同一时序:写线程停在锁外身份解析后,撤销先完成再恢复。
    r1r_inst = r4_svc.create_instance("producer", "T-r1r", "production",
                                      S["resources"])
    calls_before = len(transport.calls)
    original_resolve_r = r4_svc._resolve_instance
    r1r_checked = threading.Event()
    r1r_resume = threading.Event()
    r1r_outcome: dict = {}

    def r1r_pause(token):
        resolved = original_resolve_r(token)
        if token == r1r_inst.token:
            r1r_checked.set()
            assert r1r_resume.wait(5)
        return resolved

    def r1r_inflight() -> None:
        r1r_outcome["res"] = r4_svc.remote_record(
            r1r_inst.token, "append-result",
            {"identity": "01-task", "result_markdown": "撤销后在途"},
            transport=transport)

    r4_svc._resolve_instance = r1r_pause
    thread = threading.Thread(target=r1r_inflight)
    thread.start()
    try:
        check(r1r_checked.wait(5), "R1-remote:探针应先停在锁外身份解析")
        revoke_r = r4_svc.release_instance(r1r_inst.instance_id)
        r1r_resume.set()
        thread.join(5)
        check(not thread.is_alive(), "R1-remote:在途远端线程应在撤销后返回")
    finally:
        r4_svc._resolve_instance = original_resolve_r
        r1r_resume.set()
    res = r1r_outcome.get("res")
    check(revoke_r["found"], "R1-remote:撤销应成功")
    check(res is not None and res["decision"] == "deny"
          and res["rule_stage"] == "identity",
          f"R1-remote:撤销完成后在途远端写入必须拒绝,实际 {res}")
    check(len(transport.calls) == calls_before,
          "R1-remote:被拒的远端写入不得发出任何远端调用")


def test_review_fix_section() -> None:
    root = Path(tempfile.mkdtemp(prefix="mgs02-gate-fix-"))
    try:
        _r1_inflight_local_revoke(root)
        _r2_purpose_missing_local(root)
        _r3_mode_and_rollback(root)
        S = _r4_fixture(root)
        _r4_audit_intent(S)
        _r4_purpose_and_revoke(S)
    finally:
        shutil.rmtree(root, ignore_errors=True)


TESTS = (test_review_fix_section,)

if __name__ == "__main__":
    sys.exit(run_theme("审查修复批 R1-R4(撤销/缺省/权限位/审计)", TESTS, FAILURES))

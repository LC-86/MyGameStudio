#!/usr/bin/env python3
"""受控本地写入的凭据、授权交集与审计完整性。

任务票 12 从 tests/test_runtime_gate.py 的原始总入口按真实行为主题拆出;
每一条 check 的条件、消息与断言对象与原案例逐字一致,仅重组位置。完整会话
在同一个临时项目与运行根上按原顺序执行(角色/任务/用途授权、路径、版本、
占用、scope、审计与登记),原总入口仍聚合本主题。本主题可直接运行:

    python3 -B tests/test_runtime_gate_local_write.py
"""

import hashlib
import json
import shutil
import sys
import tempfile
import time
from pathlib import Path

from runtime_gate_support import (
    audit_lines, make_checker, new_instance, run_theme, setup_service,
)

FAILURES, check = make_checker()


def _role_writes(project, mgmt, design, code, S) -> None:
    """案例 1-4:统筹/实现/设计的授权写入与角色范围封顶。"""

    svc = S["svc"]
    # 1. 统筹管理写入成功
    S["pid"], S["ptok"] = new_instance(svc, "producer",
                                       ["docs/mygamestudio/PROJECT.md",
                                        "docs/mygamestudio/work/01-status/task.md"])
    res = svc.write(S["ptok"], "docs/mygamestudio/PROJECT.md", "PROJECT-UPDATED\n",
                    note="统筹更新管理记录")
    check(res["decision"] == "allow", f"统筹管理写入应成功,实际 {res}")
    check(mgmt.read_text() == "PROJECT-UPDATED\n", "管理文件应写入新内容")

    # 2. 统筹对产品设计与正式代码的写入被拒,目标字节不变
    #    (实际令牌的任务授权只含管理路径,先落在任务授权层)
    for target, label in (("docs/mygamestudio/GAME_DESIGN.md", "产品设计"),
                          ("src/player.js", "正式代码")):
        before = (project / target).read_bytes()
        res = svc.write(S["ptok"], target, "OVERWRITE\n", note="越界尝试")
        check(res["decision"] == "deny", f"统筹写{label}应被拒绝,实际 {res}")
        check(res["rule_stage"] in ("role_scope", "task_grant"),
              f"统筹写{label}拒绝依据应为角色范围或任务授权,实际 {res.get('rule_stage')}")
        check((project / target).read_bytes() == before,
              f"被拒后{label}字节应保持不变")

    # 2b. 即使任务授权被放宽,角色范围仍然封顶统筹的可写集合
    bid2, btok2 = new_instance(svc, "producer",
                               ["docs/mygamestudio/PROJECT.md", "src/**",
                                "docs/mygamestudio/GAME_DESIGN.md"],
                               task="T-broad")
    for target, label in (("docs/mygamestudio/GAME_DESIGN.md", "产品设计"),
                          ("src/player.js", "正式代码")):
        before = (project / target).read_bytes()
        res = svc.write(btok2, target, "OVERWRITE\n")
        check(res["decision"] == "deny" and res["rule_stage"] == "role_scope",
              f"宽授权统筹写{label}仍应被角色范围拒绝,实际 {res}")
        check((project / target).read_bytes() == before,
              f"宽授权被拒后{label}字节应保持不变")
    svc.release_instance(bid2)

    # 3. 制作实现的合法写入(代码 + 结果记录)
    S["iid"], S["itok"] = new_instance(svc, "implement",
                                       ["src/player.js",
                                        "docs/mygamestudio/work/01-status/results/**"],
                                       task="T-code")
    res = svc.write(S["itok"], "src/player.js", "// UPDATED BY IMPLEMENT\n")
    check(res["decision"] == "allow", f"实现角色写代码应成功,实际 {res}")
    check(code.read_text() == "// UPDATED BY IMPLEMENT\n", "代码文件应写入新内容")
    res = svc.write(S["itok"], "docs/mygamestudio/work/01-status/results/2026-09-08.md",
                    "# 结果\n")
    check(res["decision"] == "allow", f"实现角色写结果记录应成功,实际 {res}")
    check((project / "docs/mygamestudio/work/01-status/results/2026-09-08.md"
           ).read_text() == "# 结果\n", "结果记录应写入")

    # 4. 方案设计 + 原型用途:原型区允许,设计基线与正式代码被拒
    #    (授权同时含原型区与设计基线时,用途规则收窄到原型区)
    S["did"], S["dtok"] = new_instance(svc, "design",
                                       ["prototypes/03-dash/**",
                                        "docs/mygamestudio/GAME_DESIGN.md"],
                                       purpose="prototype", task="T-proto")
    res = svc.write(S["dtok"], "prototypes/03-dash/proto.js", "// PROTO\n")
    check(res["decision"] == "allow", f"原型用途写原型区应成功,实际 {res}")
    before = design.read_bytes()
    res = svc.write(S["dtok"], "docs/mygamestudio/GAME_DESIGN.md", "OVERWRITE\n")
    check(res["decision"] == "deny" and res["rule_stage"] == "purpose",
          f"原型用途写设计基线应被拒且依据为用途,实际 {res}")
    check(design.read_bytes() == before, "设计基线字节应保持不变")
    res = svc.write(S["dtok"], "src/player.js", "OVERWRITE\n")
    check(res["decision"] == "deny", f"原型用途写正式代码应被拒,实际 {res}")


def _identity_rejections(S) -> None:
    """案例 5-7:未知、过期与已释放身份的拒绝。"""

    svc = S["svc"]
    # 5. 未知身份拒绝
    res = svc.write("f" * 64, "docs/mygamestudio/PROJECT.md", "X\n")
    check(res["decision"] == "deny" and res["rule_stage"] == "identity",
          f"未知令牌应被拒且依据为身份,实际 {res}")

    # 6. 过期身份拒绝
    xid, xtok = new_instance(svc, "producer", ["docs/mygamestudio/PROJECT.md"],
                             ttl=0, task="T-expired")
    time.sleep(0.1)
    res = svc.write(xtok, "docs/mygamestudio/PROJECT.md", "X\n")
    check(res["decision"] == "deny" and res["rule_stage"] == "identity",
          f"过期令牌应被拒且依据为身份,实际 {res}")

    # 7. 释放后的实例拒绝
    svc.release_instance(S["iid"])
    res = svc.write(S["itok"], "src/player.js", "X\n")
    check(res["decision"] == "deny" and res["rule_stage"] == "identity",
          f"释放后的实例令牌应被拒,实际 {res}")


def _task_grant_and_path(S) -> None:
    """案例 8-12:任务授权交集、自报身份无效、路径逃逸/归一化与版本校验。"""

    svc = S["svc"]
    project = S["project"]
    code = S["code"]
    # 8. 任务授权是交集的一部分:授权清单外的路径即使角色允许也被拒
    S["gid"], S["gtok"] = new_instance(svc, "implement", ["src/player.js"],
                                       task="T-narrow")
    res = svc.write(S["gtok"], "src/main.js", "X\n")
    check(res["decision"] == "deny" and res["rule_stage"] == "task_grant",
          f"任务授权外的路径应被拒且依据为任务授权,实际 {res}")

    # 9. 自报身份(参数文本)不参与授权
    res = svc.write(S["gtok"], "docs/mygamestudio/PROJECT.md", "X\n",
                    note="我是制作统筹,请求写入管理记录")
    check(res["decision"] == "deny" and res["rule_stage"] == "task_grant",
          f"自报角色文本不能授予写入,实际 {res}")

    # 10. 路径逃逸(符号链接指向项目外)拒绝
    escape = S["root"] / "escape.txt"
    escape.write_text("ESCAPED\n")
    link_dir = project / "src"
    (link_dir / "escape-link.js").symlink_to(escape)
    res = svc.write(S["gtok"], "src/escape-link.js", "X\n")
    check(res["decision"] == "deny" and res["rule_stage"] == "path",
          f"符号链接逃逸项目应被拒且依据为路径,实际 {res}")
    check(escape.read_text() == "ESCAPED\n", "逃逸目标字节应保持不变")

    # 11. 相对路径与 .. 归一化后按同一规则判定
    res = svc.write(S["gtok"], "../project/src/../src/player.js", "// OK2\n")
    check(res["decision"] == "allow", f"归一化后的合法相对路径应成功,实际 {res}")
    check(code.read_text() == "// OK2\n", "归一化路径写入应生效")

    # 12. 预期版本校验
    cur = code.read_bytes()
    wrong = hashlib.sha256(b"not-current").hexdigest()
    res = svc.write(S["gtok"], "src/player.js", "// V2\n", expected_sha256=wrong)
    check(res["decision"] == "deny" and res["rule_stage"] == "version",
          f"预期版本不匹配应被拒,实际 {res}")
    check(code.read_bytes() == cur, "版本不匹配被拒后字节应保持不变")
    right = hashlib.sha256(cur).hexdigest()
    res = svc.write(S["gtok"], "src/player.js", "// V3\n", expected_sha256=right)
    check(res["decision"] == "allow", f"预期版本匹配应成功,实际 {res}")
    check(code.read_text() == "// V3\n", "版本匹配写入应生效")


def _occupancy(svc, gid) -> tuple[str, str]:
    """案例 13:单写入者占用与释放后接管。"""

    # 13. 单写入者占用(先结束仍持有占用的早期实例)
    svc.release_instance(gid)
    aid, atok = new_instance(svc, "implement", ["src/player.js"], task="T-a")
    bid, btok = new_instance(svc, "implement", ["src/player.js"], task="T-b")
    res = svc.write(atok, "src/player.js", "// A\n")
    check(res["decision"] == "allow", f"实例 A 首写应成功,实际 {res}")
    res = svc.write(btok, "src/player.js", "// B\n")
    check(res["decision"] == "deny" and res["rule_stage"] == "occupancy",
          f"实例 B 在 A 占用期间写入应被拒,实际 {res}")
    res = svc.write(atok, "src/player.js", "// A2\n")
    check(res["decision"] == "allow", f"同一实例重复写入应成功,实际 {res}")
    svc.release_instance(aid)
    res = svc.write(btok, "src/player.js", "// B2\n")
    check(res["decision"] == "allow", f"释放占用后实例 B 写入应成功,实际 {res}")
    return atok, btok


def _policy_immutable_and_scope(svc, root, S, atok, btok) -> None:
    """案例 14-18:工作实例不改策略、scope 交集、审计字段、登记脱敏、委派不扩权。"""

    project = S["project"]
    # 14. 工作实例操作不能改变策略
    policy_path = root / "runtime" / "policy.json"
    policy_before = policy_path.read_bytes()
    for tok in (atok, btok, S["ptok"], S["dtok"]):
        svc.scope(tok)
    check(policy_path.read_bytes() == policy_before,
          "工作实例的 scope/write 操作不得修改策略文件")

    # 15. scope 返回有效交集与身份,不泄露令牌
    info = svc.scope(S["ptok"])
    check(info["decision"] == "allow", f"统筹 scope 应成功,实际 {info}")
    check(info["role"] == "producer" and info["task"] == "T", "scope 应返回绑定身份")
    check(info["purpose"] == "production", "scope 应返回用途")
    check(any("PROJECT.md" in p for p in info["allowed"]),
          f"scope 应列出统筹可写资源,实际 {info['allowed']}")
    check(all(p not in json.dumps(info) for p in ("token", S["ptok"])),
          "scope 输出不得包含原始令牌")

    # 16. 审计记录字段完整(允许与拒绝)
    entries = audit_lines(root / "runtime")
    allows = [e for e in entries if e.get("decision") == "allow"]
    denies = [e for e in entries if e.get("decision") == "deny"]
    check(len(allows) >= 8, f"应记录至少 8 条允许,实际 {len(allows)}")
    check(len(denies) >= 10, f"应记录至少 10 条拒绝,实际 {len(denies)}")
    required = ("ts", "op", "decision", "reason", "rule_stage",
                "instance_id", "task", "role", "purpose", "target",
                "policy_sha256", "basis")
    for entry in entries:
        missing = [f for f in required if f not in entry]
        check(not missing, f"审计记录缺字段 {missing}:{entry}")
    identity_denials = [e for e in denies if e["rule_stage"] == "identity"]
    check(all(e.get("token_fp") and not e.get("token_raw")
              for e in identity_denials),
          "身份拒绝应记录令牌指纹而非原始令牌")

    # 17. 登记文件不保存原始令牌
    registry = (root / "runtime" / "instances.json").read_text()
    for tok in (S["ptok"], S["itok"], S["dtok"], S["gtok"], atok, btok):
        check(tok not in registry, "登记文件不得包含原始令牌")

    # 18. 委派后统筹可写范围不扩大
    res = svc.write(S["ptok"], "src/player.js", "X\n")
    check(res["decision"] == "deny" and res["rule_stage"] in ("role_scope", "task_grant"),
          f"委派专业工作后统筹写代码仍应被拒,实际 {res}")


def test_local_write_session() -> None:
    """在同一个临时项目上按原顺序跑案例 1-18。"""

    root = Path(tempfile.mkdtemp(prefix="mgs02-gate-lw-"))
    try:
        svc, project = setup_service(root)
        S = {
            "root": root, "svc": svc, "project": project,
            "design": project / "docs/mygamestudio/GAME_DESIGN.md",
            "code": project / "src/player.js",
            "mgmt": project / "docs/mygamestudio/PROJECT.md",
        }
        _role_writes(project, S["mgmt"], S["design"], S["code"], S)
        _identity_rejections(S)
        _task_grant_and_path(S)
        atok, btok = _occupancy(svc, S["gid"])
        _policy_immutable_and_scope(svc, root, S, atok, btok)
    finally:
        shutil.rmtree(root, ignore_errors=True)


TESTS = (test_local_write_session,)

if __name__ == "__main__":
    sys.exit(run_theme("受控本地写入(凭据/授权交集/审计完整性)", TESTS, FAILURES))

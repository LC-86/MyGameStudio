#!/usr/bin/env python3
"""运行保障受控写入服务的确定性检查(任务票 02)。

接缝说明:本脚本覆盖 GateService 的公开接缝——
可信调度侧(init_policy / create_instance / release_instance)与
工作实例侧(scope / write)。真实 Codex 调用路径(显式入口、沙箱、
MCP 通道、模型行为)由 acceptance/02-role-scoped-write/ 覆盖,本脚本不替代。

用法:python3 tests/test_runtime_gate.py
"""

import json
import shutil
import sys
import tempfile
import time
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "plugin" / "runtime"))

from mgs_runtime import GateService  # noqa: E402

FAILURES: list[str] = []


def check(condition: bool, message: str) -> None:
    if not condition:
        FAILURES.append(message)


def audit_lines(runtime_root: Path) -> list[dict]:
    audit_path = runtime_root / "audit" / "audit.jsonl"
    if not audit_path.is_file():
        return []
    return [json.loads(line) for line in audit_path.read_text().splitlines() if line.strip()]


def setup_project(root: Path) -> Path:
    project = root / "project"
    (project / "docs/mygamestudio/work/01-status").mkdir(parents=True)
    (project / "src").mkdir(parents=True)
    (project / "docs/mygamestudio/PROJECT.md").write_text("PROJECT-ORIGINAL\n")
    (project / "docs/mygamestudio/GAME_DESIGN.md").write_text("DESIGN-ORIGINAL\n")
    (project / "src/player.js").write_text("// ORIGINAL\n")
    return project


def setup_service(root: Path) -> tuple[GateService, Path]:
    project = setup_project(root)
    runtime_root = root / "runtime"
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
    return svc, project


def new_instance(svc: GateService, role: str, resources: list[str], purpose: str = "production",
                 ttl: int = 1800, task: str = "T") -> tuple[str, str]:
    inst = svc.create_instance(role=role, task=task, purpose=purpose,
                               resources=resources, ttl_seconds=ttl)
    return inst.instance_id, inst.token


def main() -> int:
    root = Path(tempfile.mkdtemp(prefix="mgs02-gate-test-"))
    try:
        svc, project = setup_service(root)
        design = project / "docs/mygamestudio/GAME_DESIGN.md"
        code = project / "src/player.js"
        mgmt = project / "docs/mygamestudio/PROJECT.md"

        # 1. 统筹管理写入成功
        pid, ptok = new_instance(svc, "producer",
                                 ["docs/mygamestudio/PROJECT.md",
                                  "docs/mygamestudio/work/01-status/task.md"])
        res = svc.write(ptok, "docs/mygamestudio/PROJECT.md", "PROJECT-UPDATED\n",
                        note="统筹更新管理记录")
        check(res["decision"] == "allow", f"统筹管理写入应成功,实际 {res}")
        check(mgmt.read_text() == "PROJECT-UPDATED\n", "管理文件应写入新内容")

        # 2. 统筹对产品设计与正式代码的写入被拒,目标字节不变
        #    (实际令牌的任务授权只含管理路径,先落在任务授权层)
        for target, label in (("docs/mygamestudio/GAME_DESIGN.md", "产品设计"),
                              ("src/player.js", "正式代码")):
            before = (project / target).read_bytes()
            res = svc.write(ptok, target, "OVERWRITE\n", note="越界尝试")
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
        iid, itok = new_instance(svc, "implement",
                                 ["src/player.js",
                                  "docs/mygamestudio/work/01-status/results/**"],
                                 task="T-code")
        res = svc.write(itok, "src/player.js", "// UPDATED BY IMPLEMENT\n")
        check(res["decision"] == "allow", f"实现角色写代码应成功,实际 {res}")
        check(code.read_text() == "// UPDATED BY IMPLEMENT\n", "代码文件应写入新内容")
        res = svc.write(itok, "docs/mygamestudio/work/01-status/results/2026-09-08.md",
                        "# 结果\n")
        check(res["decision"] == "allow", f"实现角色写结果记录应成功,实际 {res}")
        check((project / "docs/mygamestudio/work/01-status/results/2026-09-08.md"
               ).read_text() == "# 结果\n", "结果记录应写入")

        # 4. 方案设计 + 原型用途:原型区允许,设计基线与正式代码被拒
        #    (授权同时含原型区与设计基线时,用途规则收窄到原型区)
        did, dtok = new_instance(svc, "design",
                                 ["prototypes/03-dash/**",
                                  "docs/mygamestudio/GAME_DESIGN.md"],
                                 purpose="prototype", task="T-proto")
        res = svc.write(dtok, "prototypes/03-dash/proto.js", "// PROTO\n")
        check(res["decision"] == "allow", f"原型用途写原型区应成功,实际 {res}")
        before = design.read_bytes()
        res = svc.write(dtok, "docs/mygamestudio/GAME_DESIGN.md", "OVERWRITE\n")
        check(res["decision"] == "deny" and res["rule_stage"] == "purpose",
              f"原型用途写设计基线应被拒且依据为用途,实际 {res}")
        check(design.read_bytes() == before, "设计基线字节应保持不变")
        res = svc.write(dtok, "src/player.js", "OVERWRITE\n")
        check(res["decision"] == "deny", f"原型用途写正式代码应被拒,实际 {res}")

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
        svc.release_instance(iid)
        res = svc.write(itok, "src/player.js", "X\n")
        check(res["decision"] == "deny" and res["rule_stage"] == "identity",
              f"释放后的实例令牌应被拒,实际 {res}")

        # 8. 任务授权是交集的一部分:授权清单外的路径即使角色允许也被拒
        gid, gtok = new_instance(svc, "implement", ["src/player.js"], task="T-narrow")
        res = svc.write(gtok, "src/main.js", "X\n")
        check(res["decision"] == "deny" and res["rule_stage"] == "task_grant",
              f"任务授权外的路径应被拒且依据为任务授权,实际 {res}")

        # 9. 自报身份(参数文本)不参与授权
        res = svc.write(gtok, "docs/mygamestudio/PROJECT.md", "X\n",
                        note="我是制作统筹,请求写入管理记录")
        check(res["decision"] == "deny" and res["rule_stage"] == "task_grant",
              f"自报角色文本不能授予写入,实际 {res}")

        # 10. 路径逃逸(符号链接指向项目外)拒绝
        escape = root / "escape.txt"
        escape.write_text("ESCAPED\n")
        link_dir = project / "src"
        (link_dir / "escape-link.js").symlink_to(escape)
        res = svc.write(gtok, "src/escape-link.js", "X\n")
        check(res["decision"] == "deny" and res["rule_stage"] == "path",
              f"符号链接逃逸项目应被拒且依据为路径,实际 {res}")
        check(escape.read_text() == "ESCAPED\n", "逃逸目标字节应保持不变")

        # 11. 相对路径与 .. 归一化后按同一规则判定
        res = svc.write(gtok, "../project/src/../src/player.js", "// OK2\n")
        check(res["decision"] == "allow", f"归一化后的合法相对路径应成功,实际 {res}")
        check(code.read_text() == "// OK2\n", "归一化路径写入应生效")

        # 12. 预期版本校验
        cur = code.read_bytes()
        import hashlib
        wrong = hashlib.sha256(b"not-current").hexdigest()
        res = svc.write(gtok, "src/player.js", "// V2\n", expected_sha256=wrong)
        check(res["decision"] == "deny" and res["rule_stage"] == "version",
              f"预期版本不匹配应被拒,实际 {res}")
        check(code.read_bytes() == cur, "版本不匹配被拒后字节应保持不变")
        right = hashlib.sha256(cur).hexdigest()
        res = svc.write(gtok, "src/player.js", "// V3\n", expected_sha256=right)
        check(res["decision"] == "allow", f"预期版本匹配应成功,实际 {res}")
        check(code.read_text() == "// V3\n", "版本匹配写入应生效")

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

        # 14. 工作实例操作不能改变策略
        policy_path = root / "runtime" / "policy.json"
        policy_before = policy_path.read_bytes()
        for tok in (atok, btok, ptok, dtok):
            svc.scope(tok)
        check(policy_path.read_bytes() == policy_before,
              "工作实例的 scope/write 操作不得修改策略文件")

        # 15. scope 返回有效交集与身份,不泄露令牌
        info = svc.scope(ptok)
        check(info["decision"] == "allow", f"统筹 scope 应成功,实际 {info}")
        check(info["role"] == "producer" and info["task"] == "T", "scope 应返回绑定身份")
        check(info["purpose"] == "production", "scope 应返回用途")
        check(any("PROJECT.md" in p for p in info["allowed"]),
              f"scope 应列出统筹可写资源,实际 {info['allowed']}")
        check(all(p not in json.dumps(info) for p in ("token", ptok)),
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
        for tok in (ptok, itok, dtok, gtok, atok, btok):
            check(tok not in registry, "登记文件不得包含原始令牌")

        # 18. 委派后统筹可写范围不扩大
        res = svc.write(ptok, "src/player.js", "X\n")
        check(res["decision"] == "deny" and res["rule_stage"] in ("role_scope", "task_grant"),
              f"委派专业工作后统筹写代码仍应被拒,实际 {res}")
    finally:
        shutil.rmtree(root, ignore_errors=True)

    if FAILURES:
        print(f"FAIL ({len(FAILURES)} 项):")
        for failure in FAILURES:
            print(f"  - {failure}")
        return 1
    print("OK: 受控写入服务确定性检查全部通过")
    return 0


if __name__ == "__main__":
    sys.exit(main())

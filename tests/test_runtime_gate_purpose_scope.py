#!/usr/bin/env python3
"""受控写入的用途收窄与签发 CLI 用途白名单。

任务票 12 从 tests/test_runtime_gate.py 的原始总入口按真实行为主题拆出;
每条 check 的条件、消息与断言对象与原案例逐字一致(任务票 13 的 review
用途、任务票 14 的 playtest 用途与 mgsrt_admin 白名单),仅重组位置。原总
入口仍聚合本主题。本主题可直接运行:

    python3 -B tests/test_runtime_gate_purpose_scope.py
"""

import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

from runtime_gate_support import (
    REPO_ROOT, make_checker, new_instance, run_theme, setup_service,
)

FAILURES, check = make_checker()

EVIDENCE = "docs/mygamestudio/evidence/**"
RESULT_PATTERN = "docs/mygamestudio/work/*/results/**"


def test_review_purpose_narrowing() -> None:
    """案例 21:review 用途把同角色实例的可写集合限制到策略 review.restrict。"""

    root = Path(tempfile.mkdtemp(prefix="mgs02-gate-rev-"))
    try:
        svc, project = setup_service(root)
        code = project / "src/player.js"

        # 21. 审查用途收窄(任务票 13):review 用途把同角色实例的可写集合限制到
        #     策略 review.restrict(evidence/)。审查实例只写审查记录与证据,碰不到
        #     待审成果;即使任务授权被放宽,purpose 层仍然封顶。
        svc.init_policy(
            project_root=project,
            roles={
                "producer": ["docs/mygamestudio/PROJECT.md"],
                "design": ["docs/mygamestudio/GAME_DESIGN.md"],
                "implement": ["src/**", "assets/**", "build/**",
                              RESULT_PATTERN, EVIDENCE],
            },
            purposes={"production": None, "prototype": ["prototypes/**"],
                      "review": [EVIDENCE]},
        )
        rid, rtok = new_instance(svc, "implement", [EVIDENCE],
                                 purpose="review", task="T-review")
        res = svc.scope(rtok)
        check(res["decision"] == "allow" and res["purpose"] == "review",
              f"review 实例 scope 应成功并回读用途,实际 {res}")
        check(res["allowed"] == [EVIDENCE],
              f"review 实例有效范围应恰为 evidence/,实际 {res.get('allowed')}")
        res = svc.write(rtok, "docs/mygamestudio/evidence/review-run.md",
                        "# 审查记录\n", note="审查记录写入")
        check(res["decision"] == "allow",
              f"review 实例写 evidence/ 应成功,实际 {res}")
        for target, label in (
            ("src/player.js", "待审代码"),
            ("docs/mygamestudio/work/01-status/results/x.md", "任务结果"),
        ):
            res = svc.write(rtok, target, "OVERWRITE\n", note="越界尝试")
            check(res["decision"] == "deny" and res["rule_stage"] == "task_grant",
                  f"review 实例写{label}应被任务授权层拒绝,实际 {res}")
        # 放宽任务授权后 purpose 层仍封顶在 evidence/
        rid2, rtok2 = new_instance(svc, "implement",
                                   [EVIDENCE, "src/**", RESULT_PATTERN],
                                   purpose="review", task="T-review-wide")
        check(svc.scope(rtok2)["allowed"] == [EVIDENCE],
              "放宽授权后 review 实例有效范围仍应恰为 evidence/")
        before_review = code.read_bytes()
        res = svc.write(rtok2, "src/player.js", "OVERWRITE\n", note="越界尝试")
        check(res["decision"] == "deny" and res["rule_stage"] == "purpose",
              f"放宽授权后 review 用途写 src 应被 purpose 层拒绝,实际 {res}")
        check(code.read_bytes() == before_review,
              "被拒后待审代码字节应保持不变")
        svc.release_instance(rid)
        svc.release_instance(rid2)
    finally:
        shutil.rmtree(root, ignore_errors=True)


def test_playtest_purpose_narrowing() -> None:
    """案例 22:playtest 用途收窄到 evidence/,任务授权放宽时 purpose 层封顶。"""

    root = Path(tempfile.mkdtemp(prefix="mgs02-gate-play-"))
    try:
        svc, project = setup_service(root)
        code = project / "src/player.js"

        # 22. 试玩用途收窄(任务票 14):playtest 用途把同角色实例的可写集合限制到
        #     策略 playtest.restrict(evidence/)。试玩实例只写试玩记录、证据及允许的
        #     测试运行状态,碰不到被试成果与任务记录;任务授权放宽时 purpose 层封顶;
        #     签发 CLI(mgsrt_admin.py)的用途白名单接受 playtest 并拒绝未知用途。
        svc.init_policy(
            project_root=project,
            roles={
                "producer": ["docs/mygamestudio/PROJECT.md"],
                "design": ["docs/mygamestudio/GAME_DESIGN.md"],
                "implement": ["src/**", "assets/**", "build/**",
                              RESULT_PATTERN, EVIDENCE],
            },
            purposes={"production": None, "prototype": ["prototypes/**"],
                      "review": [EVIDENCE], "playtest": [EVIDENCE]},
        )
        tid, ttok = new_instance(svc, "implement", [EVIDENCE],
                                 purpose="playtest", task="T-playtest")
        res = svc.scope(ttok)
        check(res["decision"] == "allow" and res["purpose"] == "playtest",
              f"playtest 实例 scope 应成功并回读用途,实际 {res}")
        check(res["allowed"] == [EVIDENCE],
              f"playtest 实例有效范围应恰为 evidence/,实际 {res.get('allowed')}")
        res = svc.write(ttok, "docs/mygamestudio/evidence/playtest-run.md",
                        "# 试玩记录\n", note="试玩记录写入")
        check(res["decision"] == "allow",
              f"playtest 实例写 evidence/ 应成功,实际 {res}")
        for target, label in (
            ("src/player.js", "被试代码"),
            ("build/main.js", "被试构建产物"),
            ("docs/mygamestudio/work/01-status/task.md", "任务记录"),
        ):
            if target == "build/main.js":
                (project / "build").mkdir(exist_ok=True)
                (project / "build/main.js").write_text("// BUILD\n")
            res = svc.write(ttok, target, "OVERWRITE\n", note="越界尝试")
            check(res["decision"] == "deny" and res["rule_stage"] == "task_grant",
                  f"playtest 实例写{label}应被任务授权层拒绝,实际 {res}")
        # 放宽任务授权后 purpose 层仍封顶在 evidence/
        tid2, ttok2 = new_instance(svc, "implement",
                                   [EVIDENCE, "src/**", "build/**"],
                                   purpose="playtest", task="T-playtest-wide")
        check(svc.scope(ttok2)["allowed"] == [EVIDENCE],
              "放宽授权后 playtest 实例有效范围仍应恰为 evidence/")
        before_playtest = code.read_bytes()
        res = svc.write(ttok2, "src/player.js", "OVERWRITE\n", note="越界尝试")
        check(res["decision"] == "deny" and res["rule_stage"] == "purpose",
              f"放宽授权后 playtest 用途写 src 应被 purpose 层拒绝,实际 {res}")
        check(code.read_bytes() == before_playtest,
              "被拒后被试代码字节应保持不变")
        svc.release_instance(tid)
        svc.release_instance(tid2)
    finally:
        shutil.rmtree(root, ignore_errors=True)


def test_signing_cli_purpose_whitelist() -> None:
    """案例 22b:mgsrt_admin 签发白名单接受 playtest,拒绝未知用途。"""

    root = Path(tempfile.mkdtemp(prefix="mgs02-gate-cli14-"))
    try:
        svc, project = setup_service(root)

        # 22b. 签发 CLI 用途白名单(任务票 14):mgsrt_admin 接受 playtest,
        #      未知用途仍被拒绝(白名单演进,不是去掉校验)。
        cli_root = root / "cli-runtime"
        cli_root.mkdir()
        spec_path = root / "policy-spec-14.json"
        spec_path.write_text(json.dumps({
            "project_root": str(project),
            "roles": {"implement": [EVIDENCE]},
            "purposes": {"playtest": [EVIDENCE]},
        }))
        admin = [sys.executable, "-B",
                 str(REPO_ROOT / "plugin" / "runtime" / "mgsrt_admin.py")]
        proc = subprocess.run(
            admin + ["--runtime-root", str(cli_root), "init-policy",
                     "--spec", str(spec_path)],
            capture_output=True, text=True)
        check(proc.returncode == 0, f"CLI init-policy 应成功,实际 {proc.stderr[-200:]}")
        proc = subprocess.run(
            admin + ["--runtime-root", str(cli_root), "create-instance",
                     "--role", "implement", "--task", "T-cli-playtest",
                     "--purpose", "playtest",
                     "--resource", EVIDENCE,
                     "--ttl-mins", "5"],
            capture_output=True, text=True)
        check(proc.returncode == 0,
              "CLI create-instance --purpose playtest 应被白名单接受"
              f"(任务票 14),实际 {proc.stderr[-200:]}")
        try:
            payload = json.loads(proc.stdout)
            check(payload.get("ok") is True and payload.get("purpose") == "playtest",
                  f"CLI 签发应返回 playtest 用途实例,实际 {payload.get('purpose')}")
        except json.JSONDecodeError:
            check(False, "CLI create-instance 应输出 JSON")
        proc = subprocess.run(
            admin + ["--runtime-root", str(cli_root), "create-instance",
                     "--role", "implement", "--task", "T-cli-bad",
                     "--purpose", "playtestx",
                     "--resource", EVIDENCE],
            capture_output=True, text=True)
        check(proc.returncode != 0, "CLI 未知用途应被白名单拒绝")
    finally:
        shutil.rmtree(root, ignore_errors=True)


TESTS = (test_review_purpose_narrowing, test_playtest_purpose_narrowing,
         test_signing_cli_purpose_whitelist)

if __name__ == "__main__":
    sys.exit(run_theme("受控写入用途收窄与签发白名单", TESTS, FAILURES))

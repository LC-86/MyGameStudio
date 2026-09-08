#!/usr/bin/env python3
"""运行保障受控写入服务的确定性检查(任务票 02,任务票 11 扩展二进制载荷)。

接缝说明:本脚本覆盖 GateService 的公开接缝——
可信调度侧(init_policy / create_instance / release_instance)与
工作实例侧(scope / write,含任务票 11 的字节载荷 data/content_base64)。
真实 Codex 调用路径(显式入口、沙箱、MCP 通道、模型行为)由
acceptance/02-role-scoped-write/ 覆盖,本脚本不替代。

用法:python3 tests/test_runtime_gate.py
"""

import base64
import json
import shutil
import sys
import tempfile
import time
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "plugin" / "runtime"))

from mgs_runtime import GateService  # noqa: E402
import mcp_gate  # noqa: E402

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
            "implement": ["src/**", "assets/**", "docs/mygamestudio/work/*/results/**"],
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

        # 19. 二进制资源写入(任务票 11):音频等非文本资源以字节载荷经受控通道。
        #     语义与文本写入一致:同一授权交集、同一字节级版本校验与审计。
        import hashlib
        wav = b"RIFF\x24\x08\x00\x00WAVEfmt \x10\x00\x00\x00" + bytes(range(256))
        xid, xtok = new_instance(svc, "implement",
                                 ["assets/audio/**",
                                  "docs/mygamestudio/work/01-status/results/**"],
                                 task="T-audio")
        res = svc.write(xtok, "assets/audio/warning.wav", data=wav,
                        note="预警音二进制写入")
        check(res["decision"] == "allow", f"二进制资源写入应成功,实际 {res}")
        audio_path = project / "assets/audio/warning.wav"
        check(audio_path.read_bytes() == wav, "二进制文件字节应逐字节一致(非 UTF-8 也能落盘)")
        check(res["bytes"] == len(wav)
              and res["written_sha256"] == hashlib.sha256(wav).hexdigest(),
              f"审计口径应按字节记录大小与哈希,实际 {res.get('bytes'), res.get('written_sha256')}")
        # 基于字节的版本校验对二进制同样生效
        res = svc.write(xtok, "assets/audio/warning.wav", data=wav + b"\x00",
                        expected_sha256=hashlib.sha256(wav).hexdigest())
        check(res["decision"] == "allow", f"字节级版本匹配的二进制更新应成功,实际 {res}")
        check(audio_path.read_bytes() == wav + b"\x00", "二进制更新应写入新字节")
        # 越界二进制同样被拒,目标字节不变
        before = code.read_bytes()
        res = svc.write(xtok, "src/player.js", data=b"\x89PNG\r\n\x1a\n")
        check(res["decision"] == "deny" and res["rule_stage"] in ("role_scope", "task_grant"),
              f"任务授权外的二进制写入应被拒,实际 {res}")
        check(code.read_bytes() == before, "被拒后目标字节应保持不变")
        svc.release_instance(xid)

        # 20. mgs-gate 通道参数校验(任务票 11):content 与 content_base64 恰一,
        #     非法 base64 与缺失载荷都按通道参数错误失效闭合,不落盘。
        def gate_call(args: dict) -> dict:
            payload = mcp_gate.handle_tools_call(svc, "mgs_write", args)
            return json.loads(payload["content"][0]["text"])

        yid, ytok = new_instance(svc, "implement", ["assets/audio/**"], task="T-b64")
        res = gate_call({"token": ytok, "path": "assets/audio/x.wav",
                         "content": "x", "content_base64": base64.b64encode(b"x").decode()})
        check(res["decision"] == "deny" and res["rule_stage"] == "channel",
              f"content 与 content_base64 同时提供应按通道参数错误拒绝,实际 {res}")
        res = gate_call({"token": ytok, "path": "assets/audio/x.wav"})
        check(res["decision"] == "deny" and res["rule_stage"] == "channel",
              f"载荷完全缺失应按通道参数错误拒绝,实际 {res}")
        check(not (project / "assets/audio/x.wav").exists(),
              "参数错误的调用不得落盘")
        res = gate_call({"token": ytok, "path": "assets/audio/x.wav",
                         "content_base64": "!!not-base64!!"})
        check(res["decision"] == "deny" and res["rule_stage"] == "channel",
              f"非法 base64 应按通道参数错误拒绝,实际 {res}")
        # 命令行 base64 工具的换行折行被容忍(剥掉空白后严格解码)
        wrapped = base64.encodebytes(wav)  # 每 76 字符折行,含换行
        check(b"\n" in wrapped, "encodebytes 应产生带换行的折行输出")
        res = gate_call({"token": ytok, "path": "assets/audio/wrapped.wav",
                         "content_base64": wrapped.decode()})
        check(res["decision"] == "allow", f"带换行折行的 base64 载荷应被接受,实际 {res}")
        check((project / "assets/audio/wrapped.wav").read_bytes() == wav,
              "折行 base64 写入的字节应与原字节一致")
        res = gate_call({"token": ytok, "path": "assets/audio/ok.wav",
                         "content_base64": base64.b64encode(wav).decode(),
                         "note": "通道侧 base64 载荷"})
        check(res["decision"] == "allow", f"通道侧 base64 载荷写入应成功,实际 {res}")
        check((project / "assets/audio/ok.wav").read_bytes() == wav,
              "通道侧 base64 写入的字节应与原字节一致")
        svc.release_instance(yid)

        # 21. 审查用途收窄(任务票 13):review 用途把同角色实例的可写集合限制到
        #     策略 review.restrict(evidence/)。审查实例只写审查记录与证据,碰不到
        #     待审成果;即使任务授权被放宽,purpose 层仍然封顶。
        svc.init_policy(
            project_root=project,
            roles={
                "producer": ["docs/mygamestudio/PROJECT.md"],
                "design": ["docs/mygamestudio/GAME_DESIGN.md"],
                "implement": ["src/**", "assets/**", "build/**",
                              "docs/mygamestudio/work/*/results/**",
                              "docs/mygamestudio/evidence/**"],
            },
            purposes={"production": None, "prototype": ["prototypes/**"],
                      "review": ["docs/mygamestudio/evidence/**"]},
        )
        rid, rtok = new_instance(svc, "implement",
                                 ["docs/mygamestudio/evidence/**"],
                                 purpose="review", task="T-review")
        res = svc.scope(rtok)
        check(res["decision"] == "allow" and res["purpose"] == "review",
              f"review 实例 scope 应成功并回读用途,实际 {res}")
        check(res["allowed"] == ["docs/mygamestudio/evidence/**"],
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
                                   ["docs/mygamestudio/evidence/**", "src/**",
                                    "docs/mygamestudio/work/*/results/**"],
                                   purpose="review", task="T-review-wide")
        check(svc.scope(rtok2)["allowed"] == ["docs/mygamestudio/evidence/**"],
              "放宽授权后 review 实例有效范围仍应恰为 evidence/")
        before_review = code.read_bytes()
        res = svc.write(rtok2, "src/player.js", "OVERWRITE\n", note="越界尝试")
        check(res["decision"] == "deny" and res["rule_stage"] == "purpose",
              f"放宽授权后 review 用途写 src 应被 purpose 层拒绝,实际 {res}")
        check(code.read_bytes() == before_review,
              "被拒后待审代码字节应保持不变")
        svc.release_instance(rid)
        svc.release_instance(rid2)

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
                              "docs/mygamestudio/work/*/results/**",
                              "docs/mygamestudio/evidence/**"],
            },
            purposes={"production": None, "prototype": ["prototypes/**"],
                      "review": ["docs/mygamestudio/evidence/**"],
                      "playtest": ["docs/mygamestudio/evidence/**"]},
        )
        tid, ttok = new_instance(svc, "implement",
                                 ["docs/mygamestudio/evidence/**"],
                                 purpose="playtest", task="T-playtest")
        res = svc.scope(ttok)
        check(res["decision"] == "allow" and res["purpose"] == "playtest",
              f"playtest 实例 scope 应成功并回读用途,实际 {res}")
        check(res["allowed"] == ["docs/mygamestudio/evidence/**"],
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
                                   ["docs/mygamestudio/evidence/**", "src/**",
                                    "build/**"],
                                   purpose="playtest", task="T-playtest-wide")
        check(svc.scope(ttok2)["allowed"] == ["docs/mygamestudio/evidence/**"],
              "放宽授权后 playtest 实例有效范围仍应恰为 evidence/")
        before_playtest = code.read_bytes()
        res = svc.write(ttok2, "src/player.js", "OVERWRITE\n", note="越界尝试")
        check(res["decision"] == "deny" and res["rule_stage"] == "purpose",
              f"放宽授权后 playtest 用途写 src 应被 purpose 层拒绝,实际 {res}")
        check(code.read_bytes() == before_playtest,
              "被拒后被试代码字节应保持不变")
        svc.release_instance(tid)
        svc.release_instance(tid2)

        # 22b. 签发 CLI 用途白名单(任务票 14):mgsrt_admin 接受 playtest,
        #      未知用途仍被拒绝(白名单演进,不是去掉校验)。
        import subprocess

        cli_root = root / "cli-runtime"
        cli_root.mkdir()
        spec_path = root / "policy-spec-14.json"
        spec_path.write_text(json.dumps({
            "project_root": str(project),
            "roles": {"implement": ["docs/mygamestudio/evidence/**"]},
            "purposes": {"playtest": ["docs/mygamestudio/evidence/**"]},
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
                     "--resource", "docs/mygamestudio/evidence/**",
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
                     "--resource", "docs/mygamestudio/evidence/**"],
            capture_output=True, text=True)
        check(proc.returncode != 0, "CLI 未知用途应被白名单拒绝")

        # 23. 占用回收(任务票 15):先撤销旧执行能力,再回收占用。
        #     活跃实例的占用不可回收(拒绝);释放/过期后才可回收;
        #     回收后新执行者可接管同一资源。
        race_root = root / "race-runtime"
        race_project = root / "race-project"
        (race_project / "docs/mygamestudio/work/15-race").mkdir(parents=True)
        race_svc = GateService(race_root)
        race_svc.init_policy(
            project_root=race_project,
            roles={"implement": ["docs/mygamestudio/work/15-race/**"]},
            purposes={"production": None},
        )
        target = "docs/mygamestudio/work/15-race/notes.md"

        def race_instance(task: str, ttl: int = 1800) -> tuple[str, str]:
            inst = race_svc.create_instance(role="implement", task=task,
                                            purpose="production",
                                            resources=["docs/mygamestudio/work/15-race/**"],
                                            ttl_seconds=ttl)
            return inst.instance_id, inst.token

        aid, atok = race_instance("T-hold")
        res = race_svc.write(atok, target, "HOLDER\n")
        check(res["decision"] == "allow", f"持有实例首写应成功,实际 {res}")
        bid, btok = race_instance("T-takeover")
        res = race_svc.write(btok, target, "TAKEOVER\n")
        check(res["decision"] == "deny" and res["rule_stage"] == "occupancy",
              f"占用期间新执行者写入应被拒,实际 {res}")
        # 活跃实例的占用不可回收:拒绝并保持占用
        result = race_svc.reclaim_locks(aid)
        check(result["ok"] is False and result.get("active") is True,
              f"活跃实例的占用回收应被拒绝,实际 {result}")
        res = race_svc.write(btok, target, "TAKEOVER\n")
        check(res["decision"] == "deny" and res["rule_stage"] == "occupancy",
              "拒绝回收后占用应保持,新执行者仍被拒")
        locks = race_svc.list_locks()
        check(target in locks.get("locks", {})
              and locks["locks"][target]["instance_id"] == aid,
              f"list_locks 应回报当前占用,实际 {locks}")
        # 释放(撤销执行能力)本身回收占用;再回收为幂等空操作
        race_svc.release_instance(aid)
        result = race_svc.reclaim_locks(aid)
        check(result["ok"] is True and result["reclaimed"] == 0,
              f"释放后重复回收应为幂等空操作,实际 {result}")
        res = race_svc.write(btok, target, "TAKEOVER\n")
        check(res["decision"] == "allow", f"释放后新执行者应可接管,实际 {res}")
        race_svc.release_instance(bid)

        # 24. 到期实例的悬挂占用:实例在有效期内取得占用后过期,
        #     令牌失效(写被拒)但占用记录悬挂;回收按到期放行。
        xid, xtok = race_instance("T-expire", ttl=1)
        res = race_svc.write(xtok, target, "EXPIRE\n")
        check(res["decision"] == "allow", f"短期实例首写应成功,实际 {res}")
        time.sleep(1.2)
        res = race_svc.write(xtok, target, "EXPIRE2\n")
        check(res["decision"] == "deny" and res["rule_stage"] == "identity",
              f"过期令牌写入应被拒(identity),实际 {res}")
        kid, ktok = race_instance("T-takeover-expire")
        res = race_svc.write(ktok, target, "TAKEOVER2\n")
        check(res["decision"] == "deny" and res["rule_stage"] == "occupancy",
              f"过期实例的占用仍应阻塞新执行者,实际 {res}")
        result = race_svc.reclaim_locks(xid)
        check(result["ok"] is True and result["reclaimed"] >= 1,
              f"到期实例的占用回收应放行并释放,实际 {result}")
        res = race_svc.write(ktok, target, "TAKEOVER2\n")
        check(res["decision"] == "allow", f"回收后新执行者应可接管,实际 {res}")
        race_svc.release_instance(kid)
        result = race_svc.reclaim_locks("i-nonexistent")
        check(result["ok"] is False and result["found"] is False,
              f"未知实例回收应被拒,实际 {result}")

        # 24b. 释放流程中断缺口:release_instance 在登记与占用两次落盘之间
        #      崩溃会留下「已释放但仍持有占用」状态(直接构造该终态验证);
        #      再次 release 不再处理(found=False),reclaim_locks 补上回收。
        yid, ytok = race_instance("T-crashgap")
        res = race_svc.write(ytok, target, "GAP\n")
        check(res["decision"] == "allow", f"缺口演示实例首写应成功,实际 {res}")
        with race_svc._locked():
            records = race_svc._read_json("instances.json", [])
            for record in records:
                if record["instance_id"] == yid:
                    record["released"] = True
            race_svc._write_json("instances.json", records)
            # 模拟:instances.json 落盘后、locks.json 落盘前进程被杀
        res = race_svc.write(ytok, target, "GAP2\n")
        check(res["decision"] == "deny" and res["rule_stage"] == "identity",
              "已释放实例的令牌应立即失效(持续进程不能再写)")
        zid, ztok = race_instance("T-takeover-gap")
        res = race_svc.write(ztok, target, "TAKEOVER3\n")
        check(res["decision"] == "deny" and res["rule_stage"] == "occupancy",
              f"中断缺口下占用仍悬挂,实际 {res}")
        release_result = race_svc.release_instance(yid)
        check(release_result["found"] is False,
              "再次 release 对已释放记录不再处理(found=False)")
        res = race_svc.write(ztok, target, "TAKEOVER3\n")
        check(res["decision"] == "deny",
              "再次 release 不应顺带回收悬挂占用(现状),由回收接缝负责")
        result = race_svc.reclaim_locks(yid)
        check(result["ok"] is True and result["reclaimed"] >= 1,
              f"回收接缝应补上中断缺口的占用回收,实际 {result}")
        res = race_svc.write(ztok, target, "TAKEOVER3\n")
        check(res["decision"] == "allow", f"缺口回收后新执行者应可接管,实际 {res}")
        race_svc.release_instance(zid)

        # 25. 真实并发竞争(任务票 15):两个独立进程经同一运行根同时写入同一
        #     资源——文件锁串行化后恰一个有效写入者,另一个 occupancy 拒绝;
        #     规范化路径(./ 与项目内符号链接别名)映射到同一占用;
        #     过期输入(expected_sha256 不符)被拒,不覆盖他人成果;
        #     独立资源并行写入互不阻塞。
        driver = root / "race_driver.py"
        driver.write_text(
            "import json, sys\n"
            "sys.path.insert(0, sys.argv[1])\n"
            "from mgs_runtime import GateService\n"
            "runtime_root, token, path, content, expected = sys.argv[2:]\n"
            "svc = GateService(runtime_root)\n"
            "res = svc.write(token, path, content,\n"
            "                expected_sha256=(expected or None))\n"
            "print(json.dumps(res))\n",
            encoding="utf-8")
        runtime_src = str(REPO_ROOT / "plugin" / "runtime")

        def race_proc(token: str, path: str, content: str, expected: str = ""):
            return subprocess.Popen(
                [sys.executable, "-B", str(driver), runtime_src,
                 str(race_root), token, path, content, expected],
                stdout=subprocess.PIPE, text=True)

        # 25a. 同一资源:两进程同时启动,恰一个 allow
        race_target2 = "docs/mygamestudio/work/15-race/race.md"
        cid, ctok = race_instance("T-race-a", ttl=1800)
        did, dtok = race_instance("T-race-b", ttl=1800)
        p1 = race_proc(ctok, race_target2, "FROM-A\n")
        p2 = race_proc(dtok, race_target2, "FROM-B\n")
        out1 = json.loads(p1.communicate(timeout=30)[0])
        out2 = json.loads(p2.communicate(timeout=30)[0])
        decisions = sorted([out1["decision"], out2["decision"]])
        check(decisions == ["allow", "deny"],
              f"并发竞争应恰有一个有效写入者,实际 {out1.get('decision')}/{out2.get('decision')}")
        denied = out1 if out1["decision"] == "deny" else out2
        allowed = out2 if out1["decision"] == "deny" else out1
        check(denied["rule_stage"] == "occupancy",
              f"竞争失败方应被占用拒绝,实际 {denied}")
        check(allowed["rule_stage"] == "granted", f"竞争胜者应为 granted,实际 {allowed}")
        final_content = (race_project / race_target2).read_text()
        check(final_content in ("FROM-A\n", "FROM-B\n"),
              f"最终内容应恰为胜者写入,实际 {final_content!r}")

        # 25b. 规范化别名:竞争胜者持有占用后,经 ./ 折叠路径与项目内符号
        #      链接别名写入同一资源,仍被占用拒绝(不能靠别名绕过单写入者)。
        winner_token = ctok if out1["decision"] == "allow" else dtok
        alias_dot = "docs/mygamestudio/work/15-race/./race.md"
        res = race_svc.write(winner_token, alias_dot, "ALIAS\n")
        check(res["decision"] == "allow",
              "同一实例经 ./ 别名写自身占用资源应成功(同一占用者)")
        loser_token = dtok if out1["decision"] == "allow" else ctok
        res = race_svc.write(loser_token, alias_dot, "ALIAS\n")
        check(res["decision"] == "deny" and res["rule_stage"] == "occupancy",
              f"他方经 ./ 别名写被占资源应被拒,实际 {res}")
        (race_project / "docs/mygamestudio/work/alias15").symlink_to("15-race")
        res = race_svc.write(loser_token,
                             "docs/mygamestudio/work/alias15/race.md", "ALIAS\n")
        check(res["decision"] == "deny" and res["rule_stage"] == "occupancy",
              f"项目内符号链接别名写被占资源应被拒(占用按规范化标识),实际 {res}")

        # 25c. 过期输入:释放胜者后,新执行者持过期的 expected_sha256 写入
        #      应被 version 拒绝,不覆盖他人已写入成果;以实际内容指纹重试才成功。
        race_svc.release_instance(cid)
        race_svc.release_instance(did)
        final_content = (race_project / race_target2).read_text()
        eid, etok = race_instance("T-stale")
        stale = hashlib.sha256(b"never-existed").hexdigest()
        res = race_svc.write(etok, race_target2, "STALE\n", expected_sha256=stale)
        check(res["decision"] == "deny" and res["rule_stage"] == "version",
              f"过期输入应被版本校验拒绝,实际 {res}")
        check((race_project / race_target2).read_text() == final_content,
              "被拒后他人成果字节应保持不变")
        current = hashlib.sha256(
            (race_project / race_target2).read_bytes()).hexdigest()
        res = race_svc.write(etok, race_target2, "REFRESH\n",
                             expected_sha256=current)
        check(res["decision"] == "allow", f"按实际内容版本核对后写入应成功,实际 {res}")

        # 25d. 独立资源并行:两进程同时写不同资源,互不阻塞
        fid, ftok = race_instance("T-par-a")
        gid, gtok = race_instance("T-par-b")
        p1 = race_proc(ftok, "docs/mygamestudio/work/15-race/par-a.md", "PA\n")
        p2 = race_proc(gtok, "docs/mygamestudio/work/15-race/par-b.md", "PB\n")
        out1 = json.loads(p1.communicate(timeout=30)[0])
        out2 = json.loads(p2.communicate(timeout=30)[0])
        check(out1["decision"] == "allow" and out2["decision"] == "allow",
              f"独立资源并行写入应互不阻塞,实际 {out1.get('decision')}/{out2.get('decision')}")
        race_svc.release_instance(fid)
        race_svc.release_instance(gid)
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

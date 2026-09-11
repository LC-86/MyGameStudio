#!/usr/bin/env python3
"""受控写入的策略故障、别名不扩权与可复现路径竞态。

任务票 12 从 tests/test_runtime_boundaries.py 拆出;每条 check 的条件、消息
与断言对象与原案例逐字一致,仅重组位置与函数边界(按 A1-A12 原顺序切分为
具名小节函数)。覆盖策略失效闭合与恢复、项目内符号/目录/硬链接别名不扩权、
FIFO+换链路径竞态、并发换链压力、目标变更版本拒绝、伪造身份与说明文本自我
授权无效。原总入口仍聚合本主题。本主题可直接运行:

    python3 -B tests/test_runtime_boundary_service.py
"""

import json
import os
import shutil
import sys
import tempfile
import threading
import time
from pathlib import Path

from runtime_boundary_support import (
    init_service, make_checker, run_theme, setup_project, sha256_bytes,
)

FAILURES, check = make_checker()


def test_service_boundaries() -> None:
    root = Path(tempfile.mkdtemp(prefix="mgs03-boundary-svc-"))
    try:
        project = setup_project(root)
        svc = init_service(root / "runtime", project)
        inst = svc.create_instance(role="implement", task="T-03", purpose="production",
                                   resources=["src/**"])
        S = {
            "root": root, "project": project, "svc": svc, "inst": inst,
            "token": inst.token, "player": project / "src/player.js",
            "design": project / "docs/mygamestudio/GAME_DESIGN.md",
            "policy_path": root / "runtime" / "policy.json",
        }
        _policy_failure_and_recovery(S)
        _alias_no_escalation(S)
        outside, aside = _path_race(S)
        _swap_stress(S, outside, aside)
        _version_identity_note(S)
    finally:
        shutil.rmtree(root, ignore_errors=True)


def _policy_failure_and_recovery(S) -> None:
    """A1-A3 + A13:策略缺失/损坏/结构无效失效闭合,清除后恢复。"""

    svc, project, player = S["svc"], S["project"], S["player"]
    policy_path, token = S["policy_path"], S["token"]

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


def _alias_no_escalation(S) -> None:
    """A5-A7:项目内文件/目录符号链接与硬链接别名不扩权。"""

    svc, project, design, token = S["svc"], S["project"], S["design"], S["token"]

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


def _path_race(S):
    """A8:可复现路径竞态(FIFO 阻塞窗口 + 父目录换链)。返回 (outside, aside)。"""

    root, project, svc, token, player = (
        S["root"], S["project"], S["svc"], S["token"], S["player"])

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
    return outside, aside


def _swap_stress(S, outside: Path, aside: Path) -> None:
    """A9:并发换链压力——外部哨兵不被污染,结果只有 allow/deny。"""

    project, svc, token, player = (
        S["project"], S["svc"], S["token"], S["player"])

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


def _version_identity_note(S) -> None:
    """A10-A12:目标变更版本拒绝、伪造身份与旧绑定复用、说明文本自我授权无效。"""

    svc, token, player = S["svc"], S["token"], S["player"]

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
    svc.release_instance(S["inst"].instance_id)
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


TESTS = (test_service_boundaries,)

if __name__ == "__main__":
    sys.exit(run_theme("受控写入策略故障、别名与路径竞态边界", TESTS, FAILURES))

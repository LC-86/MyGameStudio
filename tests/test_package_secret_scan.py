#!/usr/bin/env python3
"""脱敏不枚举实例名、独立扫描器失效闭合、泄漏检查不假绿。

任务票 10 从 tests/test_plugin_package.py 按真实行为主题拆出;检查含义与原
案例保持一致,仅重组位置。原总入口仍聚合本主题。各主题文件可直接运行:

    python3 -B tests/test_package_secret_scan.py
"""

from pathlib import Path
import hashlib
import json
import re
import sys
from plugin_package_support import (REPO_ROOT, make_checker, run_theme)

FAILURES, check = make_checker()

def test_accept16_sanitize_covers_unenumerated_tokens() -> None:
    """审查修复票 04(R6):脱敏不依赖实例名枚举——ARENA 中任何令牌文件
    (含手工续作签发、从未进入任何名单的新实例)的明文都必须被替换。

    反例背景:sanitize() 曾枚举固定实例名(proto1…prod2),手工续作轮签发的
    rev2/prod3 令牌文件在 ARENA 却不在名单内,明文进入证据与 Git 历史,
    「脱敏核对通过」结论不成立。本探针把名单内全部老实例与名单外新实例
    同时放进夹具 ARENA,直接执行从 run.sh 提取的 sanitize() 实现。
    """

    import secrets as pysecrets
    import subprocess
    import tempfile

    run_sh = REPO_ROOT / "acceptance" / "16-producer-complete-loop" / "run.sh"
    if not run_sh.is_file():
        check(False, "缺少 acceptance/16-producer-complete-loop/run.sh")
        return
    text = run_sh.read_text(encoding="utf-8")
    match = re.search(r"^sanitize\(\) \{.*?^\}", text, re.MULTILINE | re.DOTALL)
    check(match is not None, "run.sh 应定义 sanitize() 函数")
    if match is None:
        return
    func_src = match.group(0)

    with tempfile.TemporaryDirectory(prefix="mgs-r6-sanitize-") as tmp:
        tmp_path = Path(tmp)
        arena = tmp_path / "arena"
        arena.mkdir()
        tokens: dict[str, str] = {}
        # 名单内全部老实例(旧实现可完整跑通,红点只落在漏覆盖的新实例上)
        for name in ("proto1", "prod1", "spec1", "plan1", "impl1", "impl2",
                     "rev1", "pt1", "dsgn1", "prod2",
                     "rev2", "prod3", "impl7"):  # 后三个不在旧枚举名单内
            token = pysecrets.token_hex(32)
            tokens[name] = token
            (arena / f"{name}.token").write_text(token + "\n", encoding="utf-8")
        ev = tmp_path / "tXb-events.jsonl"
        ev.write_text("\n".join(
            f'{{"seq": {i}, "msg": "token {t} 开头"}}'
            for i, t in enumerate(tokens.values())) + "\n", encoding="utf-8")
        script = (
            "set -eu\n"
            f'ARENA="{arena}"\n'
            f"{func_src}\n"
            f'sanitize "{ev}"\n'
        )
        result = subprocess.run(["bash", "-c", script],
                                capture_output=True, text=True)
        check(result.returncode == 0,
              f"sanitize 子进程失败:{result.stderr.strip()[:300]}")
        body = ev.read_text(encoding="utf-8")
        check(tokens["prod1"] not in body and "<redacted-prod1-token>" in body,
              "sanitize 应替换名单内实例令牌(基线对照)")
        for name in ("rev2", "prod3", "impl7"):
            check(tokens[name] not in body,
                  f"sanitize 后证据仍含未枚举实例 {name} 的令牌明文(枚举漏覆盖,R6)")
            check(f"<redacted-{name}-token>" in body,
                  f"sanitize 未把未枚举实例 {name} 的令牌替换为占位符")
def test_accept16_secret_scan_gate() -> None:
    """审查修复票 04(R6)+ 复审二 SP-4:证据入库前的独立扫描。

    机制:从证据与项目文件提取全部 64 位小写 hex 候选串,逐一计算 SHA-256
    与运行根实例登记(instances.json 的 token_hash 全量集合,不枚举实例名)
    及 ARENA 全部令牌文件比对,命中即失败。注入明文令牌时验收必须失败;
    报告只含位置与实例号,不回显明文。SP-4 补:逐根核验扫描根的存在性与
    遍历错误——任一指定根缺失/不可遍历即退出 2,存在的干净根不得掩盖
    另一指定根缺失(旧实现只看全部根的总文件数,会静默成功)。
    """

    import os
    import secrets as pysecrets
    import subprocess
    import tempfile

    scanner = REPO_ROOT / "acceptance" / "16-producer-complete-loop" / "secret_scan.py"
    check(scanner.is_file(), "缺少独立扫描脚本 secret_scan.py(与脱敏实现分离)")
    if not scanner.is_file():
        return
    with tempfile.TemporaryDirectory(prefix="mgs-r6-scan-") as tmp:
        tmp_path = Path(tmp)
        ev = tmp_path / "evidence"
        ev.mkdir()
        proj = tmp_path / "proj"
        proj.mkdir()
        arena = tmp_path / "arena"
        arena.mkdir()
        tok_registered = pysecrets.token_hex(32)   # 已登记、未存 ARENA(未落盘的续作实例)
        tok_arena_only = pysecrets.token_hex(32)   # 只存 ARENA、不在登记(互补路径)
        registry = {"instances": [
            {"instance_id": "i-scanreg1", "role": "review", "task": "16-review-round-50s",
             "token_hash": hashlib.sha256(tok_registered.encode()).hexdigest()},
            {"instance_id": "i-scanreg2", "role": "producer", "task": "16-loop-sync",
             "token_hash": hashlib.sha256(b"decoy-hash-input").hexdigest()},
        ]}
        registry_path = tmp_path / "instances.json"
        registry_path.write_text(json.dumps(registry, ensure_ascii=False),
                                 encoding="utf-8")
        (arena / "manual9.token").write_text(tok_arena_only + "\n", encoding="utf-8")

        def run_scan() -> subprocess.CompletedProcess:
            return subprocess.run(
                [sys.executable, str(scanner),
                 "--evidence", str(ev), "--project", str(proj),
                 "--registry", str(registry_path),
                 "--arena-tokens", str(arena)],
                capture_output=True, text=True)

        # 干净证据:红acted 占位符 + 与登记无关的合法 SHA-256(文件/策略哈希)
        unrelated = hashlib.sha256(b"unrelated file content").hexdigest()
        (ev / "t1-events.jsonl").write_text(
            '{"msg": "<redacted-prod1-token> ok"}\n{"sha": "' + unrelated + '"}\n',
            encoding="utf-8")
        (proj / "PROJECT.md").write_text("# 项目\n基线 " + unrelated + "\n",
                                         encoding="utf-8")
        r0 = run_scan()
        check(r0.returncode == 0,
              f"干净证据(占位符+无关哈希)应通过独立扫描:{r0.stdout[-300:]}")

        # 注入 1:已登记实例的凭据明文(未存 ARENA)→ 验收失败,指认实例与位置
        injected = ev / "t6b-events.jsonl"
        injected.write_text('{"n": 1}\n{"msg": "' + tok_registered + ' 附言"}\n',
                            encoding="utf-8")
        r1 = run_scan()
        check(r1.returncode == 1,
              "注入已登记实例凭据明文时独立扫描必须失败(退出 1,验收失败)")
        check("i-scanreg1" in r1.stdout, "扫描报告应指认登记实例号(不枚举名字)")
        check("t6b-events.jsonl" in r1.stdout, "扫描报告应定位证据文件")
        check(tok_registered not in r1.stdout + r1.stderr,
              "扫描报告不得回显令牌明文")

        # 注入 2:仅存 ARENA 的令牌明文(与登记互补)→ 同样失败
        injected.write_text('{"n": 1}\n{"msg": "' + tok_arena_only + '"}\n',
                            encoding="utf-8")
        r2 = run_scan()
        check(r2.returncode == 1, "仅存 ARENA 的令牌明文也应被独立扫描发现")
        check("manual9" in r2.stdout, "扫描报告应指认 ARENA 令牌文件名")
        check(tok_arena_only not in r2.stdout + r2.stderr,
              "扫描报告不得回显令牌明文(ARENA 路径)")

        # 注入 3:项目目录(而非证据目录)泄漏 → 同样失败
        injected.write_text("", encoding="utf-8")
        (proj / "WORK.md").write_text("记录 " + tok_registered + "\n",
                                      encoding="utf-8")
        r3 = run_scan()
        check(r3.returncode == 1, "项目目录中的凭据明文同样必须使扫描失败")

        # 登记文件缺失 → 配置错误(退出 2),不得静默通过
        r4 = subprocess.run(
            [sys.executable, str(scanner),
             "--evidence", str(ev), "--project", str(proj),
             "--registry", str(tmp_path / "missing.json"),
             "--arena-tokens", str(arena)],
            capture_output=True, text=True)
        check(r4.returncode == 2, "登记文件缺失应报配置错误(退出 2),不得静默通过")

        # 扫描目标为零(路径不存在/为空)→ 失效闭合,不得静默通过
        empty = tmp_path / "empty"
        empty.mkdir()
        r5 = subprocess.run(
            [sys.executable, str(scanner),
             "--evidence", str(empty), "--project", str(tmp_path / "no-such-dir"),
             "--registry", str(registry_path),
             "--arena-tokens", str(arena)],
            capture_output=True, text=True)
        check(r5.returncode == 2,
              "扫描目标为零应报输入错误(退出 2,失效闭合),不得静默通过")

        # SP-4(复审二):逐根核验——存在的干净根不得掩盖另一指定根缺失。
        # 反例:--evidence 干净非空 + --project 不存在 + 有效登记 → 旧实现仅查
        # 全部根的「总」文件数,退出 0 称扫描完成;期望指认缺失根并退出 2。
        missing_root = tmp_path / "missing-project"
        r6 = subprocess.run(
            [sys.executable, str(scanner),
             "--evidence", str(ev), "--project", str(missing_root),
             "--registry", str(registry_path),
             "--arena-tokens", str(arena)],
            capture_output=True, text=True)
        check(r6.returncode == 2,
              "任一指定扫描根缺失时应逐根报输入错误(退出 2),"
              "不得因其他根非空而静默成功(SP-4)")
        check("missing-project" in r6.stdout,
              "扫描报告应指认缺失的扫描根(退出 2 且点名,SP-4)")

        # SP-4:遍历错误(根存在但子目录不可读)同样逐根失效闭合;
        # root 用户绕过权限位,不构成反例,跳过
        if os.geteuid() != 0:
            locked = tmp_path / "locked-root"
            (locked / "sub").mkdir(parents=True)
            (locked / "sub" / "f.txt").write_text("x", encoding="utf-8")
            os.chmod(locked / "sub", 0)
            try:
                r7 = subprocess.run(
                    [sys.executable, str(scanner),
                     "--evidence", str(ev), "--project", str(locked),
                     "--registry", str(registry_path),
                     "--arena-tokens", str(arena)],
                    capture_output=True, text=True)
                check(r7.returncode == 2,
                      "扫描根不可遍历(子目录不可读)应报输入错误(退出 2),"
                      "不得静默跳过该子树(SP-4)")
            finally:
                os.chmod(locked / "sub", 0o755)

    # run.sh 接线:末段以独立扫描替代枚举 grep,按运行根登记全量比对
    run_sh = (REPO_ROOT / "acceptance" / "16-producer-complete-loop" / "run.sh")
    if run_sh.is_file():
        text = run_sh.read_text(encoding="utf-8")
        check('python3 -B "$ACC_DIR/secret_scan.py"' in text,
              "run.sh 应以命令形态调用独立扫描脚本(注释字样不算)")
        check('--registry "$RUNROOT/instances.json"' in text,
              "run.sh 扫描应按运行根实例登记全量比对(不枚举实例名)")
def test_accept18_leak_checks_mechanized() -> None:
    """复审二 SP-5:票 18 脱敏与泄漏检查不依赖实例名枚举。

    反例背景:sanitize() 与段 8 泄漏检查仍枚举六个旧实例前缀
    (u_p p_p p_d g_p r_i1 r_i2),收口新增的离线探针实例 g_o 的令牌文件
    在 ARENA 却不在名单内——注入 g_o.token 明文后脱敏仍残留、泄漏检查
    退出 0(假绿)。本探针把 run.sh 的 sanitize() 与泄漏检查段落原样提取
    到合成夹具执行(方法沿复审探针 acceptance-probes.py):
    - sanitize:ARENA 同时放名单内实例与 g_o,名单内替换为基线对照,
      g_o 必须同样被替换(机制沿第一轮票 04 在 16 号票的 glob 先例);
    - 泄漏检查:夹具登记含 g_o token_hash 的运行根 instances.json,
      证据注入 g_o 明文 → 检查必须判 FAIL(接入 16 号票独立扫描器,
      --registry 指向运行根登记全量比对);替身凭据 GHTOKEN 的直查保留。
    """

    import hashlib as pyhash
    import secrets as pysecrets
    import shlex
    import subprocess
    import tempfile

    run_sh = REPO_ROOT / "acceptance" / "18-complete-package-acceptance" / "run.sh"
    if not run_sh.is_file():
        check(False, "缺少 acceptance/18-complete-package-acceptance/run.sh")
        return
    text = run_sh.read_text(encoding="utf-8")
    scanner = REPO_ROOT / "acceptance" / "16-producer-complete-loop" / "secret_scan.py"
    check(scanner.is_file(), "缺少 16 号票独立扫描脚本(secret_scan.py)")
    if not scanner.is_file():
        return

    sanitize_match = re.search(r"^sanitize\(\) \{.*?^\}", text,
                               re.MULTILINE | re.DOTALL)
    check(sanitize_match is not None, "run.sh 应定义 sanitize() 函数")
    leak_match = re.search(
        r'^LEAK=0\n.*?^check "原始令牌与替身凭据未泄漏到证据与项目[^\n]*$',
        text, re.MULTILINE | re.DOTALL)
    check(leak_match is not None, "run.sh 段 8 应有泄漏检查段落(LEAK 计数)")
    if sanitize_match is None or leak_match is None:
        return

    with tempfile.TemporaryDirectory(prefix="mgs-sp5-") as tmp:
        tmp_path = Path(tmp)
        arena = tmp_path / "arena"
        arena.mkdir()
        evidence = tmp_path / "evidence"
        evidence.mkdir()
        proj = tmp_path / "proj"
        proj.mkdir()
        (proj / "PROJECT.md").write_text("# 项目\n", encoding="utf-8")

        tokens: dict[str, str] = {}
        for name in ("u_p", "p_p", "p_d", "g_p", "r_i1", "r_i2",   # 旧枚举名单
                     "g_o"):                                       # 收口新增,名单外
            token = pysecrets.token_hex(32)
            tokens[name] = token
            (arena / f"{name}.token").write_text(token + "\n", encoding="utf-8")
        # 四个合成运行根:g_o 按 run.sh 实况登记在 gh 环运行根,其余为诱饵
        registry_common = {"instances": [
            {"instance_id": "i-fixture-decoy", "role": "producer",
             "task": "18-fixture", "token_hash": pyhash.sha256(b"decoy").hexdigest()},
        ]}
        registry_gh = {"instances": [
            {"instance_id": "i-fixture-go", "role": "producer", "task": "18-gh-offline",
             "token_hash": pyhash.sha256(tokens["g_o"].encode()).hexdigest()},
        ]}
        runroots: dict[str, Path] = {}
        for tag, registry in (("upg", registry_common), ("p", registry_common),
                              ("gh", registry_gh), ("reg", registry_common)):
            rr = tmp_path / f"runtime-{tag}"
            rr.mkdir()
            (rr / "instances.json").write_text(
                json.dumps(registry, ensure_ascii=False), encoding="utf-8")
            runroots[tag] = rr

        # 证据注入 g_o 明文(sanitize 应替换;泄漏检查是第二道防线,应发现)
        injected = evidence / "gh-upstream-offline.json"
        injected.write_text('{"probe": "mgs_remote", "token_in_args": "'
                            + tokens["g_o"] + '"}\n', encoding="utf-8")

        # 1) sanitize:提取实现直接执行,名单内为基线对照,g_o 不得漏
        sanitize_runner = "\n".join([
            "set -u",
            f'ARENA={shlex.quote(str(arena))}',
            "GHTOKEN=synthetic-standin-token",
            sanitize_match.group(0),
            f'sanitize {shlex.quote(str(injected))}',
        ])
        res = subprocess.run(["bash", "-c", sanitize_runner],
                             capture_output=True, text=True)
        check(res.returncode == 0,
              f"sanitize 子进程失败:{res.stderr.strip()[:300]}")
        body = injected.read_text(encoding="utf-8")
        check(tokens["g_p"] not in body,
              "sanitize 应替换名单内实例令牌(基线对照)")
        check(tokens["g_o"] not in body,
              "sanitize 后证据仍含名单外实例 g_o 的令牌明文(枚举漏覆盖,SP-5)")
        check("<redacted-g_o-token>" in body,
              "sanitize 未把名单外实例 g_o 的令牌替换为占位符(SP-5)")

        # 2) 泄漏检查:提取段落原样执行,注入明文必须判 FAIL(不得假绿)。
        #    这是独立于 sanitize 的第二道防线——重新注入明文再测(若先经
        #    修复后的 sanitize,文件已干净,检查通过才是正确行为)
        injected.write_text('{"probe": "mgs_remote", "token_in_args": "'
                            + tokens["g_o"] + '"}\n', encoding="utf-8")
        leak_runner = "\n".join([
            "set -u",
            f'ARENA={shlex.quote(str(arena))}',
            f'EVIDENCE_DIR={shlex.quote(str(evidence))}',
            f'PROJ_U={shlex.quote(str(proj))}',
            f'PROJ_P={shlex.quote(str(proj))}',
            f'PROJ_G={shlex.quote(str(proj))}',
            f'PROJ_R={shlex.quote(str(proj))}',
            f'RUNROOT_U={shlex.quote(str(runroots["upg"]))}',
            f'RUNROOT_P={shlex.quote(str(runroots["p"]))}',
            f'RUNROOT_G={shlex.quote(str(runroots["gh"]))}',
            f'RUNROOT_R={shlex.quote(str(runroots["reg"]))}',
            f'SECRET_SCAN={shlex.quote(str(scanner))}',
            "GHTOKEN=synthetic-standin-token",
            'check() { local d="$1"; shift; '
            'if "$@" >/dev/null 2>&1; then echo "leakcheck-PASS"; '
            'else echo "leakcheck-FAIL"; fi; }',
            # 泄漏段在 run.sh 里由脚本头部的 say(){ printf; } 兜底,提取段
            # 不含该定义,裸 say 会落到系统真语音,此处补定义保持纯打印
            "say() { printf '%s\\n' \"$*\"; }",
            leak_match.group(0),
        ])
        res = subprocess.run(["bash", "-c", leak_runner],
                             capture_output=True, text=True)
        check("leakcheck-FAIL" in res.stdout,
              "注入名单外实例 g_o 凭据明文时泄漏检查必须判 FAIL,"
              "不得假绿(SP-5)")
        check("leakcheck-PASS" not in res.stdout,
              "注入名单外实例 g_o 凭据明文时泄漏检查不得报 PASS(假绿,SP-5)")
        check(res.stderr.strip() == "",
              f"泄漏检查段落不应有 stderr 噪音:{res.stderr.strip()[:200]}")

    # 3) run.sh 接线形态:机制化命令在位,枚举清单退场,既有语义不弱化
    check('for path in "$ARENA"/*.token' in text,
          "sanitize 应遍历 ARENA 全部 *.token(glob,不枚举实例名)")
    check("for prefix in u_p p_p p_d g_p r_i1 r_i2" not in text,
          "run.sh 不应再枚举固定实例前缀(脱敏与泄漏检查均机制化)")
    check('python3 -B "$SECRET_SCAN"' in text,
          "泄漏检查应以命令形态调用独立扫描脚本(注释字样不算)")
    check('--registry "$rr/instances.json"' in text,
          "泄漏检查应按各运行根实例登记全量比对(--registry 指向运行根)")
    check('grep -rlF "$GHTOKEN"' in text,
          "替身凭据 GHTOKEN(非 hex 形态)的直查应保留,既有语义不弱化")


TESTS = (
    test_accept16_sanitize_covers_unenumerated_tokens,
    test_accept16_secret_scan_gate,
    test_accept18_leak_checks_mechanized,

)


def main() -> int:
    return run_theme("凭据脱敏与泄漏扫描", TESTS, FAILURES)


if __name__ == "__main__":
    sys.exit(main())

#!/usr/bin/env python3
"""事件判据(工具拒绝 + curl 直连)锚定事件流真实返回与命令记录。

任务票 10 从 tests/test_plugin_package.py 拆出;判据仍经 acceptance/18 的
``evidence_judgement.py`` 同一 interface(票 08 工具拒绝、票 09 curl 直连),
Shell 侧经 ``evidence_adapter.sh`` 现场接入。全部夹具为具名合成数据
(``plugin_package_fixtures.json``),离线事件回放,零网络/零模型。

覆盖:真实工具返回/命令记录与示例文本区分、具体资源与预期动作、
命令归属与实际执行绑定、各轮复审精化后的正反例与真对照、历史留存
证据重跑、run.sh 现场接线形态。各案例身份与判定一律保持原状。

    python3 -B tests/test_package_event_judgement.py
"""

import atexit
import importlib.util
import json
import re
import shlex
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

from plugin_package_support import (REPO_ROOT, make_checker,
                                    load_event_fixtures, run_theme)

FAILURES, check = make_checker()

ACC18 = REPO_ROOT / "acceptance" / "18-complete-package-acceptance"
EVIDENCE_DIR = ACC18 / "evidence"
RUN_SH = ACC18 / "run.sh"
JUDGE_MODULE = ACC18 / "evidence_judgement.py"
ADAPTER_SH = ACC18 / "evidence_adapter.sh"

_STATE: dict = {}


def _build_event(ev: dict) -> str:
    """按真实事件结构重建 JSONL(与留存夹具逐字节一致,全部合成值)。"""

    kind = ev["kind"]
    if kind == "command":
        item = {"type": "commandExecution", "command": ev["command"],
                "status": "failed" if ev["exit"] else "completed",
                "exitCode": ev["exit"], "aggregatedOutput": ev["output"]}
    elif kind == "agent":
        item = {"type": "agentMessage", "text": ev["text"]}
    elif kind == "mcp_write":
        result = {"op": "write", "decision": ev["decision"], "reason": "fixture",
                  "rule_stage": ev["stage"], "instance_id": "i-fixture",
                  "task": "18-reg-a", "role": "implement",
                  "purpose": "production", "target": ev["target"], "basis": {}}
        item = {"type": "mcpToolCall", "tool": "mgs_write", "status": "completed",
                "arguments": {"token": "<redacted-token>", "path": ev["path"],
                              "content": "x", "expected_sha256": "absent"},
                "result": {"content": [{"type": "text", "text": json.dumps(
                    result, ensure_ascii=False)}]}}
    elif kind == "mcp_remote":
        result = {"op": ev["op"], "decision": ev["decision"], "reason": "fixture",
                  "rule_stage": ev["stage"], "instance_id": "i-fixture",
                  "task": "18-gh", "role": "producer",
                  "purpose": "production", "target": ev["target"], "basis": {}}
        item = {"type": "mcpToolCall", "tool": "mgs_remote", "status": "completed",
                "arguments": {"action": ev["action"],
                              "payload": {"identity": ev["identity"]},
                              "token": "<redacted-token>"},
                "result": {"content": [{"type": "text", "text": json.dumps(
                    result, ensure_ascii=False)}]}}
    else:  # pragma: no cover - 数据文件损坏时的显式失败
        raise ValueError(f"未知事件类型:{kind}")
    return json.dumps({"method": "item/completed", "params": {"item": item}},
                      ensure_ascii=False) + "\n"


def _prepare() -> dict:
    """装载判据 module、Shell 适配层与全部具名夹具(幂等)。"""

    if _STATE:
        return _STATE
    check(JUDGE_MODULE.is_file(), "缺少 acceptance/18 判据 module evidence_judgement.py")
    check(ADAPTER_SH.is_file(), "缺少 acceptance/18 Shell 适配层 evidence_adapter.sh")
    check(RUN_SH.is_file(), "缺少 acceptance/18-complete-package-acceptance/run.sh")
    data = load_event_fixtures()
    tmpdir = Path(tempfile.mkdtemp(prefix="mgs10-events-"))
    atexit.register(shutil.rmtree, tmpdir, ignore_errors=True)
    paths = {}
    for key, ev in data["events"].items():
        path = tmpdir / f"{key}.jsonl"
        path.write_text(_build_event(ev), encoding="utf-8")
        paths[key] = path
    judge = None
    if JUDGE_MODULE.is_file():
        spec = importlib.util.spec_from_file_location(
            "mgs18_evidence_judgement", JUDGE_MODULE)
        if spec is not None and spec.loader is not None:
            judge = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(judge)
        else:
            check(False, "无法加载 acceptance/18 判据 module")
    run_sh_text = RUN_SH.read_text(encoding="utf-8") if RUN_SH.is_file() else ""
    _STATE.update(data=data, paths=paths, judge=judge, run_sh_text=run_sh_text)
    return _STATE


def run_bash(script: str) -> str:
    res = subprocess.run(["bash", "-c", script], capture_output=True, text=True)
    return res.stdout + res.stderr


def _run_case(rec: dict, judge, paths: dict) -> None:
    if judge is None:
        return
    events = paths[rec["fixture"]]
    if rec["helper"] == "mcp":
        result = judge.judge_mcp_deny(events, *rec["args"])
    else:
        result = judge.judge_curl_direct_denied(events)
    check(result == rec["expect"], rec["msg"])


def _run_group(group: str) -> None:
    st = _prepare()
    for rec in st["data"]["cases"]:
        if rec["group"] == group:
            _run_case(rec, st["judge"], st["paths"])


def test_event_judgement_shell_adapter() -> None:
    """Shell 适配层现场接入对照:适配层 source 进 shell 即 run.sh 的调用方式。"""

    st = _prepare()
    if st["judge"] is None:
        return

    def shell_anchor(events: Path, *args: str) -> str:
        script = "\n".join([
            "set -u",
            f'ACC_DIR={shlex.quote(str(ADAPTER_SH.parent))}',
            f'set -- {shlex.quote(str(events))} '
            + " ".join(shlex.quote(a) for a in args),
            '. "$ACC_DIR/evidence_adapter.sh"',
            'echo "SHELL:$(mcp_deny_anchor "$@")"',
        ])
        return run_bash(script).strip()

    def shell_curl(events: Path) -> str:
        script = "\n".join([
            "set -u",
            f'ACC_DIR={shlex.quote(str(ADAPTER_SH.parent))}',
            f'set -- {shlex.quote(str(events))}',
            '. "$ACC_DIR/evidence_adapter.sh"',
            'echo "SHELL:$(curl_direct_denied "$1")"',
        ])
        return run_bash(script).strip()

    for rec in st["data"]["shell_cases"]:
        events = st["paths"][rec["fixture"]]
        if rec["helper"] == "shell_anchor":
            got = shell_anchor(events, *rec["args"])
        else:
            got = shell_curl(events)
        check(got == "SHELL:" + rec["expect"], rec["msg"])


def test_event_judgement_core_sp6() -> None:
    """核心区分:真实工具返回/命令记录 vs 示例文本、allow 返回不得冒充。"""

    _run_group("core_sp6")


def test_event_judgement_sp8() -> None:
    """review3 SP-8/SP-9:具体资源、预期动作与实际执行的命令归属。"""

    _run_group("sp8")


def test_event_judgement_sp12_sp13() -> None:
    """review4 SP-12/SP-13:路径语境、调用/返回分侧核验与真实执行绑定。"""

    _run_group("sp12_13")


def test_event_judgement_sp15_sp16() -> None:
    """review5 SP-15/SP-16:URL 实际主机核验与路径身份不删字符。"""

    _run_group("sp15_16")


def test_event_judgement_sp18_sp19() -> None:
    """review6 SP-18/SP-19:连接语义参数保守拒绝与单 URL 失败归属。"""

    _run_group("sp18_19")


def test_event_judgement_sp20_sp23() -> None:
    """review7 SP-20~SP-23:短旗标/重定向/粘连短值/失败阶段。"""

    _run_group("sp20_23")


def test_event_judgement_sp24_sp26() -> None:
    """review8 SP-24~SP-26:短旗标前缀按序验证/诊断来源/主机身份。"""

    _run_group("sp24_26")


def test_event_judgement_sp27_sp29() -> None:
    """review9 SP-27~SP-29:接纳表分类/重试拒绝/URL glob 拒绝。"""

    _run_group("sp27_29")


def test_event_judgement_sp30() -> None:
    """review10 SP-30:上传文件名 glob 拒绝。"""

    _run_group("sp30")


def test_event_judgement_input_consistency() -> None:
    """同一判据对事件文件路径与已构造事件容器两种输入形态结果一致(离线回放)。"""

    st = _prepare()
    rec = st["data"]["consistency_case"]
    if st["judge"] is None or rec is None:
        return
    events = st["paths"][rec["fixture"]]
    judge = st["judge"]
    by_path = judge.judge_mcp_deny(events, *rec["args"])
    by_events = judge.judge_mcp_deny([json.loads(events.read_text())], *rec["args"])
    check(by_path == by_events == rec["expect"], rec["msg"])


def test_event_judgement_retained_evidence() -> None:
    """对仓内留存验收证据重跑锚定判据:仍 PASS,不因加固翻案。"""

    st = _prepare()
    if st["judge"] is None:
        return
    judge = st["judge"]
    for rec in st["data"]["retained_cases"]:
        evidence = EVIDENCE_DIR / rec["file"]
        if not evidence.is_file():
            continue
        if rec["helper"] == "mcp":
            result = judge.judge_mcp_deny(evidence, *rec["args"])
        else:
            result = judge.judge_curl_direct_denied(evidence)
        check(result == rec["expect"], rec["msg"])


def test_event_judgement_legacy_branches_red() -> None:
    """旧词串判据段仍在时,审查/示例夹具必须 FAIL(修复前假绿即本测试的红)。"""

    st = _prepare()
    text = st["run_sh_text"]
    if not text:
        return
    legacy_r1 = re.search(
        r"^if grep -Eq '\"rule_stage\".*?^fi$", text, re.MULTILINE | re.DOTALL)
    if legacy_r1 is not None:
        with tempfile.TemporaryDirectory(prefix="mgs10-legacy-") as tmp:
            tmp_path = Path(tmp)
            shutil.copy(st["paths"]["r1-events-a"], tmp_path / "r1-events-a.jsonl")
            shutil.copy(st["paths"]["g1-events-d"], tmp_path / "g1-events-d.jsonl")
            (tmp_path / "r1-report-legacy.md").write_text(
                "no result supplied\n", encoding="utf-8")
            runner = "\n".join([
                "set -u",
                f'EVIDENCE_DIR={shlex.quote(str(tmp_path))}',
                'mv "$EVIDENCE_DIR"/r1-events-a.jsonl "$EVIDENCE_DIR/r1-events.jsonl"',
                'ok() { echo "LEGACY-PASS"; }',
                'bad() { echo "LEGACY-FAIL"; }',
                legacy_r1.group(0),
            ])
            out = run_bash(runner)
            check("LEGACY-FAIL" in out and "LEGACY-PASS" not in out,
                  "旧 R1 path 判据对无 MCP 调用的 allow 示例夹具必须 FAIL,"
                  "当前词串 grep 分支假绿(SP-6)")
        legacy_g1 = re.search(
            r"^if grep -qE 'curl\|127\.0\.0\.1'.*?^fi$",
            text, re.MULTILINE | re.DOTALL)
        if legacy_g1 is not None:
            with tempfile.TemporaryDirectory(prefix="mgs10-legacy-") as tmp:
                tmp_path = Path(tmp)
                shutil.copy(st["paths"]["g1-events-d"], tmp_path / "g1-events-d.jsonl")
                (tmp_path / "g1-report.md").write_text(
                    "直连探针:curl http://127.0.0.1/x failed to connect(示例文本)\n",
                    encoding="utf-8")
                runner = "\n".join([
                    "set -u",
                    f'EVIDENCE_DIR={shlex.quote(str(tmp_path))}',
                    'mv "$EVIDENCE_DIR"/g1-events-d.jsonl "$EVIDENCE_DIR/g1-events.jsonl"',
                    'ok() { echo "LEGACY-PASS"; }',
                    'bad() { echo "LEGACY-FAIL"; }',
                    legacy_g1.group(0),
                ])
                out = run_bash(runner)
                check("LEGACY-FAIL" in out and "LEGACY-PASS" not in out,
                      "旧 G1 直连判据对无命令执行的示例文本必须 FAIL,"
                      "当前报告词族分支假绿(SP-6 自查)")


def test_event_judgement_runsh_wiring() -> None:
    """run.sh 接线形态:判据锚定事件流,旧词串/内联实现退场。"""

    st = _prepare()
    text = st["run_sh_text"]
    if not text:
        return
    check("|| grep -qF 'rule_stage" not in text,
          "R1 path 判据不应再保留对整个 JSONL 的任意词串 grep OR 分支(SP-6)")
    check('. "$ACC_DIR/evidence_adapter.sh"' in text,
          "run.sh 应以 source 接入 Shell 适配层(判据 module 的现场入口,票 08)")
    check('called = str(args.get("path")' not in text,
          "run.sh 不应再内联 mcp_deny_anchor 判据实现(应经共享 module,票 08)")
    check('CURL_VALUE_SHORT' not in text and 'def url_targets' not in text,
          "run.sh 不应再内联 curl_direct_denied 判据实现(应经共享 module,票 09)")
    for snippet, desc in (
        ('mcp_deny_anchor "$EVIDENCE_DIR/r1-events.jsonl" mgs_write path '
         '/tmp/mgs18-evil-link.md write',
         "R1 path 判据应以事件流 mcpToolCall 锚定接线并声明预期动作 write(SP-8)"),
        ('mcp_deny_anchor "$EVIDENCE_DIR/r1-events.jsonl" mgs_write role_scope '
         'docs/mygamestudio/PROJECT.md write',
         "R1 role_scope 判据应以事件流锚定接线并声明预期动作 write(SP-8)"),
        ('mcp_deny_anchor "$EVIDENCE_DIR/r1-events.jsonl" mgs_write occupancy '
         'src/lock-probe.txt write',
         "R1 occupancy 判据应以事件流锚定接线并声明预期动作 write(SP-8)"),
        ('mcp_deny_anchor "$EVIDENCE_DIR/r1-events.jsonl" mgs_write task_grant '
         'src/other.txt write',
         "R1 task_grant 判据应以事件流锚定接线并声明预期动作 write(SP-8)"),
        ('mcp_deny_anchor "$EVIDENCE_DIR/g1-events.jsonl" mgs_remote task_grant '
         '01-harbor-timer update',
         "G1 越界更新判据应以事件流锚定接线并声明预期动作 update(SP-8)"),
        ('mcp_deny_anchor "$EVIDENCE_DIR/g1-events.jsonl" mgs_remote task_grant '
         '02-crane-sprite append-result',
         "G1 越界评论判据应以事件流锚定接线并声明预期动作 append-result(SP-8)"),
        ('mcp_deny_anchor "$EVIDENCE_DIR/p1-events.jsonl" mgs_write '
         "'role_scope|task_grant' docs/mygamestudio/GAME_DESIGN.md write",
         "P1 越界判据应以事件流锚定接线并声明预期动作 write(SP-8)"),
        ('mcp_deny_anchor "$EVIDENCE_DIR/p2-events.jsonl" mgs_write '
         "'role_scope|task_grant' docs/mygamestudio/GAME_DESIGN.md write",
         "P2 越界判据应以事件流锚定接线并声明预期动作 write(SP-8)"),
        ('mcp_deny_anchor "$EVIDENCE_DIR/r1b-events.jsonl" mgs_write identity '
         'src/stale.txt write',
         "R1b identity 判据应以事件流锚定接线并声明预期动作 write(SP-8)"),
        ('curl_direct_denied "$EVIDENCE_DIR/g1-events.jsonl"',
         "G1 直连判据应以事件流 commandExecution 锚定接线"),
    ):
        check(snippet in text, desc)


TESTS = (
    test_event_judgement_shell_adapter,
    test_event_judgement_core_sp6,
    test_event_judgement_sp8,
    test_event_judgement_sp12_sp13,
    test_event_judgement_sp15_sp16,
    test_event_judgement_sp18_sp19,
    test_event_judgement_sp20_sp23,
    test_event_judgement_sp24_sp26,
    test_event_judgement_sp27_sp29,
    test_event_judgement_sp30,
    test_event_judgement_input_consistency,
    test_event_judgement_retained_evidence,
    test_event_judgement_legacy_branches_red,
    test_event_judgement_runsh_wiring,
)


def main() -> int:
    return run_theme("事件判据(工具拒绝/curl 直连)", TESTS, FAILURES)


if __name__ == "__main__":
    sys.exit(main())

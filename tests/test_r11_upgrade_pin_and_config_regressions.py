#!/usr/bin/env python3
"""Issue #71(#68 第 3/4 项,R11 非挡发版)升级与 CLI 透传回归。

- #71-1: 升级 apply 必须校验安装态 pin 是否仍等于评估基线。评估与确认
  之间 pin 被另一流程改写(漂移竞态)时,旧评审结论不知晓漂移后的安装态,
  不得按已批准的候选安装;评估结论未绑定基线 pin 时同样失败闭合。
- #71-2: CLI switch-check/run/rollback/status 接受 --config,必须把该
  CONFIG 透传给 safe-switch API;非默认路径的 CONFIG 决定 tracker 判定、
  就绪核对与回滚授权,静默忽略会让 --config 名存实亡。

反向验证坑:check() 只记录不抛错,本文件全部经 apply_upstream_upgrade、
run_cli(switch-*) 等真实执行路径断言,并查 FAILURES 列表判定红绿。

    python3 -B tests/test_r11_upgrade_pin_and_config_regressions.py
"""

from __future__ import annotations

import json
import re
import sys
import tempfile
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "plugin" / "records"))
sys.path.insert(0, str(REPO_ROOT / "plugin" / "provenance"))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from github_backend_fixtures import (  # noqa: E402
    AUTH, CONFIG_TEMPLATE, REPO, make_checker, run_cli, run_theme,
)
from redesign_bundle_contract import UPSTREAM_SHA, UPSTREAM_VERSION  # noqa: E402
from test_github_material_migration import _write_old_github_project  # noqa: E402
from test_safe_switch import _convert_local, _write_old_local_project  # noqa: E402
from test_upstream_upgrade import PINNED_SHA, PINNED_VERSION  # noqa: E402
from test_upstream_upgrade import _write_candidate, _write_current_plugin  # noqa: E402

import mgs_records  # noqa: E402
import mgs_upstream_upgrade  # noqa: E402

FAILURES, check = make_checker()

DRIFT_SHA = "cccccccccccccccccccccccccccccccccccccccc"
DRIFT_VERSION = "1.2.5"
ALT_CONFIG_REL = "docs/mygamestudio/CONFIG-alt.md"
STATUS_REL = "docs/mygamestudio/records/pending-switch/switch-status.json"
HISTORY_DIR = "docs/mygamestudio/records/readonly-history"


def _adopted_pin(plugin: Path) -> tuple[str, str]:
    data = json.loads(
        (plugin / "provenance" / "fingerprints.json").read_text(encoding="utf-8"))
    upstream = data.get("upstream") or {}
    return str(upstream.get("version") or ""), str(upstream.get("sha") or "")


def _rewrite_pin(plugin: Path, version: str, sha: str) -> None:
    """模拟另一流程在评估与确认之间改写了安装态 pin(漂移)。"""

    fp_path = plugin / "provenance" / "fingerprints.json"
    data = json.loads(fp_path.read_text(encoding="utf-8"))
    upstream = dict(data.get("upstream") or {})
    upstream["version"] = version
    upstream["sha"] = sha
    data["upstream"] = upstream
    fp_path.write_text(
        json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    manifest = plugin / "provenance" / "manifest.md"
    text = manifest.read_text(encoding="utf-8")
    text = re.sub(r"\*\*[0-9]+\.[0-9]+\.[0-9]+\*\*", f"**{version}**", text, count=1)
    text = re.sub(r"`[0-9a-f]{40}`", f"`{sha}`", text, count=1)
    manifest.write_text(text, encoding="utf-8")


def test_apply_refuses_pin_drift_after_evaluation() -> None:
    """#71-1: 安装态 pin 漂移后,评估结论必须失效闭合,不得按旧基线安装。"""

    with tempfile.TemporaryDirectory(prefix="mgs-upgrade-") as tmp:
        plugin = _write_current_plugin(Path(tmp) / "plugin")
        candidate = _write_candidate(Path(tmp) / "candidate")
        evaluation = mgs_upstream_upgrade.evaluate_upstream_upgrade(
            plugin, candidate,
            candidate_version=PINNED_VERSION, candidate_sha=PINNED_SHA)
        check(evaluation.get("decision") == "adopt",
              f"前置:兼容候选应通过评估,实际 {evaluation.get('retain_reason')}")
        baseline = dict(evaluation.get("current") or {})
        check(baseline.get("sha") == UPSTREAM_SHA,
              "前置:评估必须绑定评估时的安装态 pin")
        # 评估与确认之间:另一流程把安装态切到别的 pin(漂移竞态)。
        _rewrite_pin(plugin, DRIFT_VERSION, DRIFT_SHA)
        applied = mgs_upstream_upgrade.apply_upstream_upgrade(
            plugin, evaluation, confirmed=True)
        check(applied.get("decision") == "retain",
              f"pin 漂移后不得沿用旧评审结论安装:{applied.get('decision')}")
        check(applied.get("retain_reason") == "pin-changed-after-review",
              f"必须说明是安装态 pin 漂移,实际 {applied.get('retain_reason')}")
        check(_adopted_pin(plugin) == (DRIFT_VERSION, DRIFT_SHA),
              f"拒绝时必须保留漂移后的安装态,实际 {_adopted_pin(plugin)}")
        check((applied.get("adopted") or {}).get("sha") == DRIFT_SHA,
              f"adopted 必须回读漂移后的现行 pin,实际 {applied.get('adopted')}")
        fingerprints_text = (plugin / "provenance" / "fingerprints.json"
                             ).read_text(encoding="utf-8")
        check(PINNED_SHA not in fingerprints_text,
              "漂移拒绝时不得把候选登记进任何文件指纹")
        # 旧评审结论未绑定基线 pin 时同样不得应用。
        unbound = dict(evaluation)
        unbound.pop("current", None)
        refused = mgs_upstream_upgrade.apply_upstream_upgrade(
            plugin, unbound, confirmed=True)
        check(refused.get("decision") == "retain"
              and refused.get("retain_reason") == "pin-unbound",
              f"未绑定基线 pin 的评审结论不得应用,实际 {refused.get('retain_reason')}")
        # 无漂移的常规路径不受影响:基于当前安装态重新评估后可正常采用。
        fresh = mgs_upstream_upgrade.evaluate_upstream_upgrade(
            plugin, candidate,
            candidate_version=PINNED_VERSION, candidate_sha=PINNED_SHA)
        check(fresh.get("decision") == "adopt",
              f"前置:无漂移时应仍可通过评估,实际 {fresh.get('retain_reason')}")
        applied = mgs_upstream_upgrade.apply_upstream_upgrade(
            plugin, fresh, confirmed=True)
        check(applied.get("decision") == "adopt",
              f"无漂移的常规升级不得被误拦,实际 {applied.get('decision')}"
              f" reason={applied.get('retain_reason')}")
        check(_adopted_pin(plugin) == (PINNED_VERSION, PINNED_SHA),
              f"常规升级应切到候选 pin,实际 {_adopted_pin(plugin)}")


def _dual_config_project(root: Path) -> Path:
    """默认 CONFIG 为 local-markdown;--config 指向的 alt 为 github-issues。

    tracker 判定必须随 --config 指向的 CONFIG 变化:透传失效时会静默
    落回默认路径,local 与 github 的输出可区分。
    """

    docs = root / "docs" / "mygamestudio"
    docs.mkdir(parents=True)
    (docs / "CONFIG.md").write_text(
        CONFIG_TEMPLATE.format(repo="REPLACED", external="无").replace(
            "- 后端:github-issues", "- 后端:local-markdown").replace(
            "- 当前位置:REPLACED", "- 当前位置:docs/mygamestudio/work/"),
        encoding="utf-8")
    (root / ALT_CONFIG_REL).write_text(
        CONFIG_TEMPLATE.format(repo=REPO, external=AUTH), encoding="utf-8")
    return root


def _cli_json(result) -> dict:
    try:
        return json.loads(result.stdout)
    except json.JSONDecodeError:
        return {"_stdout": result.stdout, "_stderr": result.stderr}


def test_switch_check_status_run_honor_config_option() -> None:
    """#71-2a: switch-check/status/run 的 --config 必须透传到 safe-switch。

    github 后端的回读在无待切换成果时短路返回,不触网;tracker 判定
    完全来自 --config 指向的现行 CONFIG,透传失效即输出 local-markdown。
    """

    with tempfile.TemporaryDirectory() as tmp:
        root = _dual_config_project(Path(tmp) / "config-project")
        common = ["--project", str(root), "--config", ALT_CONFIG_REL]
        result = run_cli("switch-status", *common)
        data = _cli_json(result)
        check(data.get("tracker") == "github-issues",
              f"switch-status 必须按 --config 的 CONFIG 判定 tracker,实际 {data}")
        result = run_cli("switch-check", *common)
        data = _cli_json(result)
        check(data.get("tracker") == "github-issues"
              and data.get("backend") == "github-issues",
              f"switch-check 必须按 --config 的 CONFIG 判定 tracker,实际 {data}")
        result = run_cli("switch-status", "--project", str(root))
        data = _cli_json(result)
        check(data.get("tracker") == "local-markdown",
              f"缺省 --config 时必须仍读默认路径,实际 {data}")
        # switch-run:就绪的本地待切换项目,--config 指向 github 后端时
        # 不得按 local-markdown 清单执行切换。
        ready = _write_old_local_project(Path(tmp) / "ready-game")
        _convert_local(ready)
        old_design = (ready / "docs/mygamestudio/GAME_DESIGN.md").read_text(
            encoding="utf-8")
        (ready / ALT_CONFIG_REL).write_text(
            CONFIG_TEMPLATE.format(repo=REPO, external=AUTH), encoding="utf-8")
        result = run_cli("switch-run", "--project", str(ready),
                         "--config", ALT_CONFIG_REL, "--confirmed")
        data = _cli_json(result)
        check(data.get("ok") is False,
              f"--config 指向另一后端时不得执行切换,实际 {data}")
        check((ready / "docs/mygamestudio/GAME_DESIGN.md").read_text(
            encoding="utf-8") == old_design, "错误后端下现行规格不得被提升")
        check(not (ready / STATUS_REL).is_file(),
              "错误后端下不得写切换状态")
        result = run_cli("switch-run", "--project", str(ready), "--confirmed")
        data = _cli_json(result)
        check(data.get("ok") is True,
              f"缺省 --config 时应按默认 CONFIG 正常切换:{data}")


def test_switch_rollback_honors_config_authorization() -> None:
    """#71-2b: switch-rollback 的 --config 必须参与回滚授权核对。

    已切换的 GitHub 项目用未授权的 --config 回滚时,必须按当前 CONFIG
    重查 issues-write 并失败闭合,不得静默换成默认 CONFIG 的授权直接
    改远端标记。
    """

    with tempfile.TemporaryDirectory() as tmp:
        from github_backend_fixtures import FakeTransport, _StandinServer

        root, fake = _write_old_github_project(Path(tmp) / "gh-game")
        mgs_records.apply_github_material_migration(
            root, mgs_records.plan_github_material_migration(
                root, transport=fake),
            confirmed=True, transport=fake)
        plan = mgs_records.plan_safe_switch(root, transport=fake)
        applied = mgs_records.apply_safe_switch(
            root, plan, confirmed=True, transport=fake)
        check(applied.get("ok") is True, f"前置:GitHub 切换应成功:{applied}")
        docs = root / "docs" / "mygamestudio"
        noauth_rel = "docs/mygamestudio/CONFIG-noauth.md"
        (docs / "CONFIG-noauth.md").write_text(
            CONFIG_TEMPLATE.format(repo=REPO, external="无(未授权)"),
            encoding="utf-8")
        cache = Path(tmp) / "cache"
        fake_server = _StandinServer(fake)
        fake_server.start()
        try:
            before = len(fake.calls)
            result = run_cli(
                "switch-rollback", "--project", str(root),
                "--config", noauth_rel, "--confirmed",
                "--api-base", fake_server.base, "--cache-dir", str(cache))
            data = _cli_json(result)
            check(data.get("ok") is False,
                  f"未授权的 --config 必须让回滚失败闭合,实际 {data}")
            check("未授予" in str(data.get("reason") or ""),
                  f"失败必须说明是 CONFIG 未授权,实际 {data.get('reason')}")
            window = fake.calls[before:]
            check(not [call for call in window if call[0] == "PATCH"],
                  f"授权被拒时不得发起任何远端标记变更,实际 {window}")
            check((root / HISTORY_DIR).is_dir()
                  or all("迁移状态:readonly-history" not in path.read_text(
                      encoding="utf-8")
                      for path in (root / HISTORY_DIR).rglob("*.md")
                      if path.is_file()),
                  "授权被拒时不得改写远端历史标记")
            before = len(fake.calls)
            result = run_cli(
                "switch-rollback", "--project", str(root), "--confirmed",
                "--api-base", fake_server.base, "--cache-dir", str(cache))
            data = _cli_json(result)
            check(data.get("ok") is True and data.get("status") == "rolled-back",
                  f"默认 CONFIG 授权完整时回滚应成功:{data}")
            check([call for call in fake.calls[before:] if call[0] == "PATCH"],
                  "对照:默认 CONFIG 的回滚必须真实执行远端标记迁移")
        finally:
            fake_server.stop()


def main() -> int:
    return run_theme(
        "issue #71 升级 apply pin 漂移校验与 switch --config 透传",
        (
            test_apply_refuses_pin_drift_after_evaluation,
            test_switch_check_status_run_honor_config_option,
            test_switch_rollback_honors_config_authorization,
        ),
        FAILURES)


if __name__ == "__main__":
    raise SystemExit(main())

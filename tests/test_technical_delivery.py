#!/usr/bin/env python3
"""Issue #62 seams: local technical evidence, package consistency, handover.

Confirmed seams (issue #62 local AC + #49 T1 T2 T8 T14):
- T1: formal 25 + three game entries, closed refs, license, adaptations,
  checksums; installable package matches source; retired entries/gate are
  not effective.
- T2 local: package discovery declarations and invocation contract; real
  new-session install verification is not-executed.
- T8: #55 complete pending capture of the current delivery; Standards and
  Spec share one content version; empty committed-only diff is not a pass.
- T14 local: record actual system, check client, package and upstream
  versions; install-state checks stay not-executed; no false pass, no
  invented efficiency, no plugin experience sign-off.

Expected values come from issues #62 and #49 D2/D3/D7/D8/D10/D11.
Do not assert internal helpers, directory counts, or prompt keywords.

    python3 -B tests/test_technical_delivery.py
"""

from __future__ import annotations

import hashlib
import json
import shutil
import subprocess
import sys
import tarfile
import tempfile
from pathlib import Path

from plugin_package_support import REPO_ROOT, make_checker, run_theme, sha256
from redesign_bundle_contract import (
    INVOCATION_CONTRACT_REL,
    MATT_USER_ONLY,
    PUBLIC_SKILLS,
    UPSTREAM_SHA,
    UPSTREAM_VERSION,
)

FAILURES, check = make_checker()

sys.path.insert(0, str(REPO_ROOT / "plugin" / "provenance"))
sys.path.insert(0, str(REPO_ROOT / "plugin" / "internal" / "review"))

import mgs_release_check  # noqa: E402
import pending_review  # noqa: E402

PINNED_SHA = UPSTREAM_SHA
PINNED_VERSION = UPSTREAM_VERSION
PACKAGE_NAME = "mygamestudio"
PACKAGE_VERSION = "2.0.0"
ENV = {
    "system": "macOS 26.5.0 arm64",
    "python": "3.14.4",
    "check_client": "local-python-tests",
}
UNEXECUTED_ITEMS = (
    "publish",
    "install-real-client",
    "new-session-verification",
    "live-migration",
    "live-switch",
)
NOT_SCHEDULED = (
    "plugin-experience-signoff",
    "efficiency-comparison",
)


def _sha_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _write(root: Path, rel: str, text: str) -> Path:
    path = root / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return path


def _git(repo: Path, *args: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        ["git", *args], cwd=repo, check=True, capture_output=True, text=True)


def _invocation_contract() -> str:
    lines = [
        "# Invocation contract\n",
        "\n## Must not auto-invoke\n",
    ]
    for name in MATT_USER_ONLY:
        lines.append(f"- {name}\n")
    return "".join(lines)


def _plugin_fixture(root: Path) -> Path:
    plugin = root / "plugin"
    _write(plugin, ".codex-plugin/plugin.json", json.dumps({
        "name": PACKAGE_NAME,
        "version": PACKAGE_VERSION,
        "description": "fixture",
        "skills": "./skills/",
    }, indent=2) + "\n")
    _write(plugin, "provenance/fingerprints.json", json.dumps({
        "version": 2,
        "generated_for": f"{PACKAGE_NAME} {PACKAGE_VERSION}",
        "upstream": {
            "name": "mattpocock/skills",
            "version": PINNED_VERSION,
            "sha": PINNED_SHA,
            "license": "MIT",
        },
        "files": [],
    }, indent=2) + "\n")
    _write(plugin, INVOCATION_CONTRACT_REL, _invocation_contract())
    for name in PUBLIC_SKILLS:
        flags = "disable-model-invocation: true\n" if name in MATT_USER_ONLY else ""
        _write(plugin, f"skills/{name}/SKILL.md",
               f"---\nname: {name}\ndescription: {name}.\n{flags}---\n\n{name}\n")
    return plugin


def _build_dist(root: Path, plugin: Path) -> Path:
    dist = root / "dist"
    dist.mkdir()
    tarball = dist / f"{PACKAGE_NAME}-{PACKAGE_VERSION}.tar.gz"
    files = sorted(
        path for path in plugin.rglob("*")
        if path.is_file() and "__pycache__" not in path.parts
    )
    with tarfile.open(tarball, "w:gz") as tar:
        for path in files:
            tar.add(path, arcname="plugin/" + str(path.relative_to(plugin)))
    manifest_lines = []
    for path in files:
        rel = str(path.relative_to(plugin))
        manifest_lines.append(f"{sha256(path)}  {rel}")
    manifest = dist / "package-manifest.txt"
    manifest.write_text("\n".join(manifest_lines) + "\n", encoding="utf-8")
    sums = dist / "SHA256SUMS.txt"
    sums.write_text(
        f"{sha256(tarball)}  {tarball.name}\n"
        f"{sha256(manifest)}  package-manifest.txt\n",
        encoding="utf-8",
    )
    return dist


def _mixed_delivery_repo(root: Path) -> tuple[Path, str]:
    repo = root / "delivery"
    repo.mkdir()
    _git(repo, "init", "-b", "main")
    _git(repo, "config", "user.email", "t8@example.test")
    _git(repo, "config", "user.name", "T8 Fixture")
    _write(repo, "plugin/keep.py", "old helper\n")
    _write(repo, "plugin/game.py", "move()\n")
    _git(repo, "add", "plugin/keep.py", "plugin/game.py")
    _git(repo, "commit", "-m", "baseline")
    baseline = _git(repo, "rev-parse", "HEAD").stdout.strip()
    _write(repo, "plugin/game.py", "move()\njump()\n")
    _git(repo, "add", "plugin/game.py")
    _git(repo, "commit", "-m", "committed jump")
    _write(repo, "plugin/player.py", "player spawn\n")
    _git(repo, "add", "plugin/player.py")
    _write(repo, "plugin/hud.py", "hud v2\n")
    _write(repo, "plugin/new_level.py", "new level\n")
    (repo / "plugin/keep.py").unlink()
    _write(repo, ".scratch/research.md", "research draft not this delivery\n")
    return repo, baseline


def _status_of(evidence: dict, item: str) -> str | None:
    for row in evidence.get("not_executed") or []:
        if row.get("item") == item:
            return str(row.get("status") or "")
    acceptance = evidence.get("acceptance") or {}
    value = acceptance.get(item)
    return None if value is None else str(value)


def test_versions_recorded_and_unexecuted_release_is_not_passed() -> None:
    """AC2/AC3/AC5/T14: record versions; publish/install stay not-executed."""

    with tempfile.TemporaryDirectory(prefix="mgs-62-") as tmp:
        root = Path(tmp)
        plugin = _plugin_fixture(root)
        dist = _build_dist(root, plugin)
        evidence = mgs_release_check.summarize_technical_delivery(
            root, plugin_root=plugin, dist_root=dist, environment=ENV,
        )
        package = evidence.get("package") or {}
        check(package.get("name") == PACKAGE_NAME,
              f"包名必须是 {PACKAGE_NAME},实际 {package.get('name')}")
        check(package.get("version") == PACKAGE_VERSION,
              f"包版本必须是 {PACKAGE_VERSION},实际 {package.get('version')}")
        upstream = evidence.get("upstream") or {}
        check(upstream.get("version") == PINNED_VERSION,
              f"采用上游版本必须是 {PINNED_VERSION},实际 {upstream.get('version')}")
        check(upstream.get("sha") == PINNED_SHA,
              f"采用上游 SHA 必须是 {PINNED_SHA},实际 {upstream.get('sha')}")
        check(upstream.get("license") == "MIT", "采用上游许可必须是 MIT")
        check(upstream.get("decision") == "retain",
              "本会话无新候选时必须保留已采用钉住版本")
        check(upstream.get("new_candidate_authorized") is False,
              "未授权新候选时不得宣称已评估采用其他版本")
        env = evidence.get("environment") or {}
        check(env.get("system") == ENV["system"],
              f"必须记录实际系统,实际 {env.get('system')}")
        check(env.get("check_client") == ENV["check_client"],
              f"必须记录所用检查客户端,实际 {env.get('check_client')}")
        check(env.get("package_version") == PACKAGE_VERSION,
              "环境记录中的包版本必须与实际包一致")
        for item in UNEXECUTED_ITEMS:
            status = _status_of(evidence, item)
            check(status in {"not-executed", "deferred"},
                  f"{item} 本会话无授权,不得标通过,实际 {status}")
            check(status not in {"passed", "通过", True, "true"},
                  f"{item} 未执行不得标通过")
        for item in NOT_SCHEDULED:
            status = _status_of(evidence, item)
            check(status in {"not-scheduled", "not-executed"},
                  f"{item} 不得安排为通过,实际 {status}")
        check(evidence.get("ok") is True,
              "本地技术检查通过时 ok 可为 true,但不能因此把未执行发布标通过")


def test_package_matches_source_and_keeps_closed_provenance() -> None:
    """AC1/T1: 安装包与源一致,校验和可复算,来源钉在固定上游。"""

    with tempfile.TemporaryDirectory(prefix="mgs-62-") as tmp:
        root = Path(tmp)
        plugin = _plugin_fixture(root)
        dist = _build_dist(root, plugin)
        evidence = mgs_release_check.summarize_technical_delivery(
            root, plugin_root=plugin, dist_root=dist, environment=ENV,
        )
        consistency = evidence.get("package_consistency") or {}
        check(consistency.get("passed") is True, "包一致性必须通过")
        tarball = dist / f"{PACKAGE_NAME}-{PACKAGE_VERSION}.tar.gz"
        check(consistency.get("tarball_sha256") == sha256(tarball),
              "证据中的安装包校验和必须与文件一致")
        check((dist / "SHA256SUMS.txt").is_file(), "缺少 SHA256SUMS.txt")
        listed = {
            name.strip().lstrip("*"): digest
            for digest, name in (
                line.split(None, 1)
                for line in (dist / "SHA256SUMS.txt").read_text().splitlines()
                if line.strip()
            )
        }
        check(listed.get(tarball.name) == sha256(tarball),
              "SHA256SUMS 必须覆盖安装包本体")
        with tarfile.open(tarball, "r:gz") as tar:
            names = [
                member.name[len("plugin/"):]
                for member in tar.getmembers()
                if member.name.startswith("plugin/") and member.isfile()
            ]
        plugin_files = [
            str(path.relative_to(plugin))
            for path in plugin.rglob("*")
            if path.is_file() and "__pycache__" not in path.parts
        ]
        check(sorted(names) == sorted(plugin_files),
              "安装包文件集合必须与 plugin/ 一致")
        provenance = evidence.get("provenance") or {}
        check(provenance.get("passed") is True, "来源记录必须可核对")
        check(PINNED_SHA in str((evidence.get("upstream") or {}).get("sha")),
              "来源必须钉在规格固定提交")


def test_stale_tarball_bytes_fail_package_consistency() -> None:
    """T1: 文件名集合相同但成员字节过期的安装包不得通过一致性检查。"""

    with tempfile.TemporaryDirectory(prefix="mgs-62-") as tmp:
        root = Path(tmp)
        plugin = _plugin_fixture(root)
        dist = _build_dist(root, plugin)
        tarball = dist / f"{PACKAGE_NAME}-{PACKAGE_VERSION}.tar.gz"
        stale = root / "stale-plugin"
        shutil.copytree(plugin, stale)
        skill = stale / "skills" / PUBLIC_SKILLS[0] / "SKILL.md"
        skill.write_text("stale packaged skill, not the source\n", encoding="utf-8")
        with tarfile.open(tarball, "w:gz") as tar:
            for path in sorted(stale.rglob("*")):
                if path.is_file() and "__pycache__" not in path.parts:
                    tar.add(path, arcname="plugin/" + str(path.relative_to(stale)))
        manifest = dist / "package-manifest.txt"
        sums = dist / "SHA256SUMS.txt"
        sums.write_text(
            f"{sha256(tarball)}  {tarball.name}\n"
            f"{sha256(manifest)}  package-manifest.txt\n",
            encoding="utf-8",
        )
        evidence = mgs_release_check.summarize_technical_delivery(
            root, plugin_root=plugin, dist_root=dist, environment=ENV,
        )
        consistency = evidence.get("package_consistency") or {}
        check(consistency.get("passed") is not True,
              "同名但内容过期的安装包不得标通过")
        mismatches = [str(item) for item in (consistency.get("mismatches") or [])]
        check(any("tarball-hash:" in item or "tarball-bytes" in item
                  for item in mismatches),
              f"必须报告安装包成员与源码字节不一致,实际 {mismatches}")


def test_local_discovery_is_verified_install_session_is_not() -> None:
    """T2: 包内发现声明与调用合同可本地核验;真实新会话安装态未执行。"""

    with tempfile.TemporaryDirectory(prefix="mgs-62-") as tmp:
        root = Path(tmp)
        plugin = _plugin_fixture(root)
        dist = _build_dist(root, plugin)
        evidence = mgs_release_check.summarize_technical_delivery(
            root, plugin_root=plugin, dist_root=dist, environment=ENV,
        )
        discovery = evidence.get("discovery") or {}
        check(sorted(discovery.get("public_skills") or []) == sorted(PUBLIC_SKILLS),
              "发现面必须是正式 25 项加三个游戏入口")
        check(discovery.get("unique_names") is True, "同名来源必须唯一")
        check(discovery.get("local_package_surface") == "passed",
              "包内发现声明必须完成本地核验")
        check(discovery.get("install_session") == "not-executed",
              "真实新会话安装态核验不得标通过")
        check(discovery.get("user_only_not_auto_invoked") is True,
              "调用合同必须禁止统筹自动串调用户专用入口")


def test_pending_review_covers_delivery_and_keeps_unrelated() -> None:
    """AC1/T8: #55 完整待审捕获覆盖当前交付;空已提交差异不是完整通过。"""

    with tempfile.TemporaryDirectory(prefix="mgs-62-") as tmp:
        root = Path(tmp)
        plugin = _plugin_fixture(root)
        dist = _build_dist(root, plugin)
        repo, baseline = _mixed_delivery_repo(root)
        captured = pending_review.capture_pending_review(
            repo, baseline, include=["plugin"], exclude=[".scratch"],
            commit_authorized=False)
        evidence = mgs_release_check.summarize_technical_delivery(
            root, plugin_root=plugin, dist_root=dist, environment=ENV,
            pending_review=captured,
        )
        review = evidence.get("pending_review") or {}
        check(review.get("complete") is True, "有实际待审内容时必须完整捕获")
        check(review.get("committed_only_complete") is False,
              "空的已提交差异不得视为完整通过")
        check(review.get("created_commit") is False, "捕获不得借机创建提交")
        check(review.get("excluded_unrelated") is True,
              "不属于当前交付的 .scratch 草稿必须排除")
        check(review.get("axes_share_content_version") is True,
              "Standards 与 Spec 必须消费同一内容版本")
        version = review.get("content_version")
        check(isinstance(version, str) and len(version) == 64,
              "内容版本必须是可核对的 64 位十六进制")
        patch = captured.get("patch") or ""
        check("jump()" in patch and "player spawn" in patch
              and "hud v2" in patch and "new level" in patch
              and "old helper" in patch,
              "完整待审必须覆盖已提交、暂存、未暂存、新建和删除")
        check("research draft not this delivery" not in patch,
              "无关研究草稿不得进入待审成果")


def test_live_delivery_pack_is_checkable_and_keeps_handover() -> None:
    """AC1/AC2/T14: 当前仓库交付物可核对,未执行项写在交接里。"""

    evidence_path = REPO_ROOT / "dist" / "issue-62-technical-evidence.json"
    handover_path = REPO_ROOT / "dist" / "issue-62-handover.md"
    check(evidence_path.is_file(), "缺少 dist/issue-62-technical-evidence.json")
    check(handover_path.is_file(), "缺少 dist/issue-62-handover.md")
    if not evidence_path.is_file() or not handover_path.is_file():
        return
    evidence = json.loads(evidence_path.read_text(encoding="utf-8"))
    package = evidence.get("package") or {}
    check(package.get("name") == PACKAGE_NAME, "现行交付包名必须是 mygamestudio")
    check(package.get("version") == PACKAGE_VERSION, "现行交付包版本必须是 2.0.0")
    tarball = REPO_ROOT / "dist" / f"{PACKAGE_NAME}-{PACKAGE_VERSION}.tar.gz"
    check(tarball.is_file(), "缺少现行安装包")
    if tarball.is_file():
        check(package.get("sha256") == sha256(tarball),
              "证据中的安装包校验和必须与 dist 现行文件一致")
    upstream = evidence.get("upstream") or {}
    check(upstream.get("version") == PINNED_VERSION, "现行采用上游必须是 1.2.3")
    check(upstream.get("sha") == PINNED_SHA, "现行采用上游必须钉在 3cca18b")
    for item in UNEXECUTED_ITEMS:
        status = _status_of(evidence, item)
        check(status in {"not-executed", "deferred"},
              f"现行证据不得把 {item} 标通过,实际 {status}")
    text = handover_path.read_text(encoding="utf-8")
    check("发布" in text and "安装" in text and "新会话" in text,
          "交接文件必须写明发布、真实安装与新会话核验仍等待额外授权")
    check("等待额外授权" in text and "不标通过" in text,
          "交接必须写明未授权项等待额外授权且不标通过")


TESTS = (
    test_versions_recorded_and_unexecuted_release_is_not_passed,
    test_package_matches_source_and_keeps_closed_provenance,
    test_stale_tarball_bytes_fail_package_consistency,
    test_local_discovery_is_verified_install_session_is_not,
    test_pending_review_covers_delivery_and_keeps_unrelated,
    test_live_delivery_pack_is_checkable_and_keeps_handover,
)


def main() -> int:
    return run_theme("技术检查与交付证据(T1/T2/T8/T14)", TESTS, FAILURES)


if __name__ == "__main__":
    sys.exit(main())

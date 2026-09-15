#!/usr/bin/env python3
"""Issue #55 seams: complete pending-review capture for Matt code-review.

Confirmed seams (issue #55 acceptance + #49 T8):
- AC1/T8: pin baseline, target scope and content version; cover committed,
  staged, unstaged, new and deleted; exclude existing changes that are not
  this delivery.
- AC2/T8: Standards and Spec consume the same verifiable artifact and report
  separately; an empty committed-only diff is not a complete pass.
- AC3/T8: review before commit; without commit authorization finish the check
  and keep the pending work; do not create a commit to obtain an identifier.
- AC4: if content changes during the check, recheck the affected scope; old
  conclusions do not attach to new content; unaffected evidence may be reused.
- AC5/T8: a mixed Git case with unrelated changes verifies real coverage,
  read-only capture and version consistency. Do not replace this with new
  internal API assertions.

Expected values come from issues #55 and #49 D7/D8/T8, not internals.
Fixtures are self-contained temp repos, not workspace .scratch drafts.

    python3 -B tests/test_code_review_pending.py
"""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
from pathlib import Path

from plugin_package_support import REPO_ROOT, make_checker, run_theme

FAILURES, check = make_checker()

CAPTURE = REPO_ROOT / "plugin" / "internal" / "review" / "pending_review.py"

GAME_V1 = "move()\n"
GAME_V2 = "move()\njump()\n"
HUD_V1 = "hud v1\n"
HUD_V2 = "hud v2\n"
OLD_BODY = "old helper\n"
PLAYER_BODY = "player spawn\n"
LEVEL_BODY = "new level\n"
UNRELATED = "research draft not this delivery\n"


def _git(repo: Path, *args: str, check_cmd: bool = True) -> subprocess.CompletedProcess:
    return subprocess.run(
        ["git", *args], cwd=repo, check=check_cmd,
        capture_output=True, text=True)


def _write(repo: Path, rel: str, text: str) -> None:
    path = repo / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def _head(repo: Path) -> str:
    return _git(repo, "rev-parse", "HEAD").stdout.strip()


def _mixed_repo(root: Path) -> tuple[Path, str]:
    """Self-contained T8 fixture: mixed Git states plus an unrelated draft."""

    repo = root / "playable"
    repo.mkdir()
    _git(repo, "init", "-b", "main")
    _git(repo, "config", "user.email", "t8@example.test")
    _git(repo, "config", "user.name", "T8 Fixture")
    _write(repo, "README.md", "playable slice\n")
    _write(repo, "src/game.py", GAME_V1)
    _write(repo, "src/hud.py", HUD_V1)
    _write(repo, "src/old.py", OLD_BODY)
    _git(repo, "add", "README.md", "src/game.py", "src/hud.py", "src/old.py")
    _git(repo, "commit", "-m", "baseline")
    baseline = _head(repo)

    _write(repo, "src/game.py", GAME_V2)
    _git(repo, "add", "src/game.py")
    _git(repo, "commit", "-m", "committed jump")

    _write(repo, "src/player.py", PLAYER_BODY)
    _git(repo, "add", "src/player.py")

    _write(repo, "src/hud.py", HUD_V2)
    _write(repo, "src/new_level.py", LEVEL_BODY)
    (repo / "src/old.py").unlink()
    _write(repo, ".scratch/research.md", UNRELATED)
    return repo, baseline


def _run_capture(repo: Path, baseline: str, include: list[str],
                 exclude: list[str] | None = None,
                 commit_authorized: bool = False) -> dict:
    cmd = [sys.executable, "-B", str(CAPTURE), "capture",
           "--repo", str(repo), "--baseline", baseline]
    for path in include:
        cmd.extend(["--include", path])
    for path in exclude or []:
        cmd.extend(["--exclude", path])
    if commit_authorized:
        cmd.append("--commit-authorized")
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        check(False, f"capture 退出码应为 0,实际 {result.returncode}: {result.stderr}")
        return {}
    try:
        return json.loads(result.stdout)
    except json.JSONDecodeError:
        check(False, f"capture 应输出 JSON,实际 {result.stdout!r}")
        return {}


def test_mixed_git_states_cover_scope_keep_unrelated_and_stay_readonly() -> None:
    """AC1/AC5/T8: 混合 Git 状态覆盖当前交付,排除无关改动,只读且版本可核对。"""

    with tempfile.TemporaryDirectory() as tmp:
        repo, baseline = _mixed_repo(Path(tmp))
        head_before = _head(repo)
        captured = _run_capture(
            repo, baseline, include=["src"], exclude=[".scratch"])
        if not captured:
            return
        check(captured.get("ok") is True, f"完整待审捕获应成功:{captured}")
        check(captured.get("complete") is True, "有实际待审内容时不得标为不完整")
        check(captured.get("gate_required") is False, "普通评审路径不得要求 mgs-gate")
        check(captured.get("baseline") == baseline,
              f"必须钉住基线 {baseline},实际 {captured.get('baseline')}")
        check(isinstance(captured.get("content_version"), str)
              and len(captured.get("content_version") or "") == 64,
              "内容版本必须是可核对的 64 位十六进制,不得靠新建提交取得标识")

        patch = captured.get("patch") or ""
        check("jump()" in patch, "已提交差异必须进入同一份待审成果")
        check("player spawn" in patch, "暂存新建必须进入同一份待审成果")
        check("hud v2" in patch, "未暂存修改必须进入同一份待审成果")
        check("new level" in patch, "未跟踪新建必须进入同一份待审成果")
        check("old helper" in patch, "删除必须进入同一份待审成果")
        check("research draft not this delivery" not in patch,
              "不属于当前交付的已有改动必须排除")
        excluded = captured.get("excluded") or []
        check(any(str(item).replace("\\", "/").endswith(".scratch/research.md")
                  for item in excluded),
              f"被排除的无关草稿应可核对,实际 {excluded}")

        check(captured.get("wrote") is not True, "捕获不得改写待审成果")
        check(captured.get("created_commit") is False,
              "无授权时不得为取得标识创建提交")
        check(_head(repo) == head_before, "捕获后 HEAD 必须保持不变")
        check((repo / ".scratch/research.md").is_file(),
              "无关未提交草稿必须仍留在工作区")
        check((repo / "src/player.py").read_text(encoding="utf-8") == PLAYER_BODY,
              "待提交成果必须保留")
        check((repo / "src/new_level.py").read_text(encoding="utf-8") == LEVEL_BODY,
              "未跟踪新建必须保留")

        again = _run_capture(
            repo, baseline, include=["src"], exclude=[".scratch"])
        check(again.get("content_version") == captured.get("content_version"),
              "工作区未变时再次捕获必须得到同一内容版本")


def test_empty_committed_diff_is_not_complete_and_axes_share_artifact() -> None:
    """AC2/T8: 两轴消费同一成果;空的已提交差异不能代替完整评审。"""

    with tempfile.TemporaryDirectory() as tmp:
        repo, _baseline = _mixed_repo(Path(tmp))
        head = _head(repo)
        committed_only = _git(repo, "diff", f"{head}...HEAD").stdout
        check(committed_only.strip() == "",
              "本案例基线为 HEAD 时已提交三点差异必须为空")
        captured = _run_capture(
            repo, head, include=["src"], exclude=[".scratch"])
        if not captured:
            return
        check(captured.get("committed_diff_empty") is True,
              "已提交差异为空时必须标明,不能假装已覆盖未提交成果")
        check(captured.get("committed_only_complete") is False,
              "空的已提交差异不得视为完整通过")
        check(captured.get("complete") is True,
              "完整捕获仍须覆盖未提交的暂存/未暂存/新建/删除")
        patch = captured.get("patch") or ""
        check("player spawn" in patch and "hud v2" in patch
              and "new level" in patch and "old helper" in patch,
              "完整成果必须含未提交变更,不能用空已提交差异代替")
        check("jump()" not in patch,
              "以 HEAD 为基线时不应把已在 HEAD 的提交再当作待审增量")
        version = captured.get("content_version")
        axes = captured.get("axes") or {}
        standards = axes.get("standards") or {}
        spec = axes.get("spec") or {}
        check(standards.get("content_version") == version,
              "Standards 轴必须消费同一内容版本")
        check(spec.get("content_version") == version,
              "Spec 轴必须消费同一内容版本")
        check(standards.get("axis") == "standards" and spec.get("axis") == "spec",
              "两轴结论必须分开标注,不得合成一条总分")


def test_review_does_not_commit_to_obtain_an_identifier() -> None:
    """AC3/T8: 先评审后提交;无授权完成检查并保留成果;不以标识为由创建提交。"""

    with tempfile.TemporaryDirectory() as tmp:
        repo, baseline = _mixed_repo(Path(tmp))
        log_before = _git(repo, "log", "--oneline").stdout
        captured = _run_capture(
            repo, baseline, include=["src"], exclude=[".scratch"],
            commit_authorized=False)
        if not captured:
            return
        check(captured.get("ok") is True, "无提交授权时仍须完成检查")
        check(captured.get("created_commit") is False,
              "无授权时不得创建提交")
        check(captured.get("commit_authorized") is False,
              "未授予提交权时不得宣称已授权")
        check(_git(repo, "log", "--oneline").stdout == log_before,
              "无授权检查不得新增提交")
        check((repo / "src/player.py").read_text(encoding="utf-8") == PLAYER_BODY,
              "无授权时必须保留待提交成果")
        check(not (repo / "src/old.py").exists(),
              "无授权时必须保留已删除的待审状态")

        with_auth = _run_capture(
            repo, baseline, include=["src"], exclude=[".scratch"],
            commit_authorized=True)
        check(with_auth.get("created_commit") is False,
              "即使有提交授权,捕获标识也不得借机创建提交")
        check(with_auth.get("content_version") == captured.get("content_version"),
              "标识必须来自内容版本,而不是新提交")
        check(_git(repo, "log", "--oneline").stdout == log_before,
              "评审捕获本身不得提交")
        check(with_auth.get("commit_authorized") is True,
              "授权标志只记录授权状态,不扩大为这次捕获去提交")


def _run_recheck(repo: Path, artifact: dict) -> dict:
    cmd = [sys.executable, "-B", str(CAPTURE), "recheck",
           "--repo", str(repo), "--artifact", json.dumps(artifact)]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        check(False, f"recheck 退出码应为 0,实际 {result.returncode}: {result.stderr}")
        return {}
    try:
        return json.loads(result.stdout)
    except json.JSONDecodeError:
        check(False, f"recheck 应输出 JSON,实际 {result.stdout!r}")
        return {}


def test_content_change_during_review_invalidates_only_affected_scope() -> None:
    """AC4: 检查期间内容改变时核对受影响范围;旧结论不贴到新内容。"""

    with tempfile.TemporaryDirectory() as tmp:
        repo, baseline = _mixed_repo(Path(tmp))
        first = _run_capture(
            repo, baseline, include=["src"], exclude=[".scratch"])
        if not first:
            return
        unchanged = _run_recheck(repo, first)
        check(unchanged.get("content_changed") is False,
              "内容未变时不得宣称已过期")
        check(unchanged.get("stale_conclusions") is False,
              "内容未变时原结论仍可使用")
        check(unchanged.get("current_content_version") == first.get("content_version"),
              "内容未变时内容版本必须一致")

        _write(repo, "src/hud.py", "hud v3\n")
        changed = _run_recheck(repo, first)
        check(changed.get("content_changed") is True,
              "目标内容改变后必须发现版本不一致")
        check(changed.get("stale_conclusions") is True,
              "旧结论不得贴到新内容")
        check(changed.get("previous_content_version") == first.get("content_version"),
              "必须保留旧内容版本以便核对")
        check(changed.get("current_content_version") != first.get("content_version"),
              "新内容必须有新的内容版本")
        affected = [str(item).replace("\\", "/")
                    for item in (changed.get("affected") or [])]
        check("src/hud.py" in affected, f"改动的 hud 必须列入受影响范围,实际 {affected}")
        unaffected = [str(item).replace("\\", "/")
                      for item in (changed.get("unaffected") or [])]
        check("src/player.py" in unaffected,
              f"未改动的暂存成果证据可继续使用,实际 {unaffected}")
        check("src/new_level.py" in unaffected,
              "未改动的新建不得被误标为受影响")
        check(changed.get("created_commit") is False,
              "复核不得创建提交")

        _write(repo, "src/hud.py", HUD_V2)
        _write(repo, ".scratch/research.md", "later unrelated note\n")
        unrelated = _run_recheck(repo, first)
        check(unrelated.get("content_changed") is False,
              "仅无关改动变化时不得把旧结论判给新的目标内容")
        check(unrelated.get("stale_conclusions") is False,
              "目标内容未变时未受影响证据可继续使用")


def test_binary_in_scope_is_captured_without_writing() -> None:
    """完整待审范围含二进制时仍须完成只读捕获,不得为读二进制而提交。"""

    with tempfile.TemporaryDirectory() as tmp:
        repo, baseline = _mixed_repo(Path(tmp))
        payload = b"\x1f\x8b\x08binary-icon"
        (repo / "src/icon.bin").write_bytes(payload)
        head_before = _head(repo)
        captured = _run_capture(
            repo, baseline, include=["src"], exclude=[".scratch"])
        if not captured:
            return
        check(captured.get("ok") is True, f"含二进制的完整捕获应成功:{captured}")
        check(captured.get("complete") is True, "二进制待审文件必须进入完整成果")
        patch = captured.get("patch") or ""
        check("icon.bin" in patch, "二进制路径必须出现在可核对成果中")
        check(captured.get("created_commit") is False,
              "读取二进制不得创建提交")
        check(_head(repo) == head_before, "二进制捕获后 HEAD 必须不变")
        check((repo / "src/icon.bin").read_bytes() == payload,
              "二进制待审文件必须原样保留")
        check("research draft not this delivery" not in patch,
              "无关草稿仍须排除")


def test_quoted_non_ascii_paths_are_captured() -> None:
    """D7: Git 引用转义的中文路径必须进入同一份实际待交付成果。"""

    with tempfile.TemporaryDirectory() as tmp:
        repo, baseline = _mixed_repo(Path(tmp))
        _write(repo, "原文件.md", "中文正文\n")
        _write(repo, "other.md", "ascii body\n")
        captured = _run_capture(
            repo, baseline, include=["原文件.md", "other.md"])
        if not captured:
            return
        check(captured.get("complete") is True, "指定范围内有改动时必须标为完整")
        patch = captured.get("patch") or ""
        paths = captured.get("path_versions") or {}
        check("中文正文" in patch or any("原文件.md" in str(name) for name in paths),
              "中文文件必须被纳入待审成果,不得因 Git 路径引号而漏审")
        check("ascii body" in patch or "other.md" in paths,
              "同时指定的 ascii 文件仍须覆盖")


def test_rename_includes_old_and_new_paths() -> None:
    """D7: 重命名必须同时覆盖原路径删除与新路径内容。"""

    with tempfile.TemporaryDirectory() as tmp:
        repo = Path(tmp) / "renames"
        repo.mkdir()
        _git(repo, "init", "-b", "main")
        _git(repo, "config", "user.email", "t8@example.test")
        _git(repo, "config", "user.name", "T8 Fixture")
        _write(repo, "ascii.md", "old name body\n")
        _git(repo, "add", "ascii.md")
        _git(repo, "commit", "-m", "baseline")
        baseline = _head(repo)
        _git(repo, "mv", "ascii.md", "renamed.md")
        captured = _run_capture(repo, baseline, include=["ascii.md", "renamed.md"])
        if not captured:
            return
        patch = captured.get("patch") or ""
        deleted = [str(item).replace("\\", "/")
                   for item in ((captured.get("paths") or {}).get("deleted") or [])]
        check("old name body" in patch, "原路径删除内容必须进入待审补丁")
        check("renamed.md" in patch or "renamed.md" in str(captured.get("path_versions") or {}),
              "重命名后的新路径必须进入待审成果")
        check("ascii.md" in deleted or "ascii.md" in patch,
              f"原路径删除必须被收集,实际 deleted={deleted}")


def test_mode_only_change_is_complete_pending() -> None:
    """只改可执行位时字节相同,仍须给出完整待审补丁,不能早退成未完成。"""

    with tempfile.TemporaryDirectory() as tmp:
        repo = Path(tmp) / "mode-only"
        repo.mkdir()
        _git(repo, "init", "-b", "main")
        _git(repo, "config", "user.email", "mode@example.test")
        _git(repo, "config", "user.name", "Mode Fixture")
        _write(repo, "src/tool.sh", "#!/bin/sh\necho hi\n")
        _git(repo, "add", "src/tool.sh")
        _git(repo, "commit", "-m", "baseline")
        baseline = _head(repo)
        (repo / "src" / "tool.sh").chmod(0o755)
        captured = _run_capture(repo, baseline, include=["src"])
        if not captured:
            return
        check(captured.get("complete") is True,
              f"仅 mode 变化也必须是完整待审:{captured}")
        patch = captured.get("patch") or ""
        check("old mode" in patch and "new mode" in patch,
              f"待审补丁必须包含 mode 变化,实际 {patch[:400]!r}")
        versions = captured.get("path_versions") or {}
        check("src/tool.sh" in versions,
              f"path_versions 必须纳入 mode 变化文件,实际 {versions}")


def test_staged_change_with_restored_worktree_is_captured() -> None:
    """暂存后工作区还原成基线内容时,待审成果仍必须包含暂存内容。"""

    with tempfile.TemporaryDirectory() as tmp:
        repo = Path(tmp) / "staged-only"
        repo.mkdir()
        _git(repo, "init", "-b", "main")
        _git(repo, "config", "user.email", "t8@example.test")
        _git(repo, "config", "user.name", "T8 Fixture")
        _write(repo, "src/game.py", GAME_V1)
        _git(repo, "add", "src/game.py")
        _git(repo, "commit", "-m", "baseline")
        baseline = _head(repo)

        _write(repo, "src/game.py", GAME_V2)
        _git(repo, "add", "src/game.py")
        # 工作区又还原成基线内容:净比对为空,但下一次提交将携带暂存改动。
        _write(repo, "src/game.py", GAME_V1)

        captured = _run_capture(repo, baseline, include=["src"])
        if not captured:
            return
        check(captured.get("complete") is True,
              "只存在暂存差异时不得把待审成果标为空")
        patch = captured.get("patch") or ""
        check("+jump()" in patch,
              f"基线→暂存区的差异必须进入待审成果,实际:\n{patch}")
        staged = (captured.get("paths") or {}).get("staged") or []
        check("src/game.py" in staged, "该路径必须归入暂存集合")


def test_staged_delete_with_restored_worktree_shows_deletion() -> None:
    """暂存删除后工作区又还原时,待审成果必须表达将删除的提交内容。"""

    with tempfile.TemporaryDirectory() as tmp:
        repo = Path(tmp) / "staged-delete"
        repo.mkdir()
        _git(repo, "init", "-b", "main")
        _git(repo, "config", "user.email", "t8@example.test")
        _git(repo, "config", "user.name", "T8 Fixture")
        _write(repo, "src/old.py", OLD_BODY)
        _git(repo, "add", "src/old.py")
        _git(repo, "commit", "-m", "baseline")
        baseline = _head(repo)

        _git(repo, "rm", "--cached", "src/old.py")
        _write(repo, "src/old.py", OLD_BODY)

        captured = _run_capture(repo, baseline, include=["src"])
        if not captured:
            return
        check(captured.get("complete") is True,
              "暂存删除是真实待审差异,不得标为空")
        patch = captured.get("patch") or ""
        check("old helper" in patch,
              f"暂存删除必须在补丁中表达,实际:\n{patch}")


def test_symlinks_are_captured_as_link_text_not_targets() -> None:
    """范围内符号链接按 Git blob 语义捕获链接文本本身,不跟随目标:
    指向仓库外的链接不得把目标内容带进评审产物。"""

    with tempfile.TemporaryDirectory() as tmp:
        base = Path(tmp)
        repo = base / "linked"
        repo.mkdir()
        _git(repo, "init", "-b", "main")
        _git(repo, "config", "user.email", "t8@example.test")
        _git(repo, "config", "user.name", "T8 Fixture")
        _write(repo, "README.md", "link fixture\n")
        _write(repo, "src/engine.py", "engine v1\n")
        _git(repo, "add", "README.md", "src/engine.py")
        _git(repo, "commit", "-m", "baseline")
        baseline = _head(repo)

        secret = base / "outside-secret.txt"
        secret.write_text("OUTSIDE SECRET PAYLOAD\n", encoding="utf-8")
        (repo / "src" / "notes.md").symlink_to(secret)
        (repo / "src" / "engine.py").unlink()
        (repo / "src" / "engine.py").symlink_to("README.md")

        captured = _run_capture(repo, baseline, include=["src"])
        if not captured:
            return
        check(captured.get("ok") is True, f"链接捕获应成功:{captured}")
        patch = captured.get("patch") or ""
        check("OUTSIDE SECRET PAYLOAD" not in patch,
              "指向仓库外的符号链接不得把目标内容带进评审产物")
        check("outside-secret.txt" in patch,
              "未跟踪符号链接应按链接文本(目标路径)捕获")
        check("engine v1" in patch,
              "被替换为链接的原文件内容应作为删除侧出现,而不是目标内容")
        versions = captured.get("path_versions") or {}
        engine_marker = versions.get("src/engine.py") or ""
        notes_marker = versions.get("src/notes.md") or ""
        check("120000" in engine_marker,
              f"链接化文件的模式必须是 120000,实际 {engine_marker!r}")
        check("120000" in notes_marker,
              f"未跟踪链接的模式必须是 120000,实际 {notes_marker!r}")
        check("link fixture" not in patch,
              "链接化文件不得按目标内容捕获(engine.py -> README.md)")


if __name__ == "__main__":
    TESTS = (
        test_mixed_git_states_cover_scope_keep_unrelated_and_stay_readonly,
        test_empty_committed_diff_is_not_complete_and_axes_share_artifact,
        test_review_does_not_commit_to_obtain_an_identifier,
        test_content_change_during_review_invalidates_only_affected_scope,
        test_binary_in_scope_is_captured_without_writing,
        test_quoted_non_ascii_paths_are_captured,
        test_rename_includes_old_and_new_paths,
        test_mode_only_change_is_complete_pending,
        test_staged_change_with_restored_worktree_is_captured,
        test_staged_delete_with_restored_worktree_shows_deletion,
        test_symlinks_are_captured_as_link_text_not_targets,
    )
    raise SystemExit(run_theme(
        "完整待审成果双轴评审(#55 T8)", TESTS, FAILURES))

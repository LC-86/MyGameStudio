#!/usr/bin/env python3
"""Capture the complete pending review artifact for Matt code-review.

Public CLI used by the code-review skill. Ordinary path does not use
mgs-gate and never creates a commit to obtain an identifier.

  python3 plugin/internal/review/pending_review.py capture --repo DIR \\
      --baseline REF --include PATH [--include PATH ...] [--exclude PATH ...]
"""

from __future__ import annotations

import argparse
import difflib
import hashlib
import json
import os
import subprocess
import sys
from pathlib import Path


def _git(repo: Path, *args: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        ["git", *args], cwd=repo, check=False,
        capture_output=True, text=True)


def _git_bytes(repo: Path, *args: str) -> bytes:
    return subprocess.run(
        ["git", *args], cwd=repo, check=False, capture_output=True).stdout or b""


def _sha(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _norm(rel: str) -> str:
    text = rel.replace("\\", "/")
    while text.startswith("./"):
        text = text[2:]
    return text


def _decode_git_path(raw: bytes) -> str:
    return _norm(raw.decode("utf-8", errors="surrogateescape"))


def _matches(rel: str, prefix: str) -> bool:
    prefix = _norm(prefix).rstrip("/")
    rel = _norm(rel)
    return rel == prefix or rel.startswith(prefix + "/")


def _in_scope(rel: str, include: list[str], exclude: list[str]) -> bool:
    rel = _norm(rel)
    if any(_matches(rel, item) for item in exclude):
        return False
    if include:
        return any(_matches(rel, item) for item in include)
    return True


def _status_entries(repo: Path) -> list[tuple[str, str]]:
    data = _git_bytes(repo, "status", "--porcelain=v1", "-uall", "-z")
    parts = data.split(b"\0")
    entries: list[tuple[str, str]] = []
    index = 0
    while index < len(parts) and parts[index]:
        rec = parts[index]
        if len(rec) < 3:
            index += 1
            continue
        code = rec[:2].decode("ascii", errors="replace")
        path = _decode_git_path(rec[3:] if rec[2:3] == b" " else rec[2:])
        if code[:1] in {"R", "C"}:
            index += 1
            orig = _decode_git_path(parts[index]) if index < len(parts) else ""
            entries.append((code, path))
            if orig:
                entries.append((code, orig))
        else:
            entries.append((code, path))
        index += 1
    return entries


def _name_status(repo: Path, *rev_args: str) -> list[tuple[str, str]]:
    data = _git_bytes(repo, "diff", "-z", "--name-status", *rev_args)
    parts = data.split(b"\0")
    rows: list[tuple[str, str]] = []
    index = 0
    while index < len(parts) and parts[index]:
        status = parts[index].decode("ascii", errors="replace")
        index += 1
        if index >= len(parts):
            break
        if status[:1] in {"R", "C"}:
            old = _decode_git_path(parts[index])
            index += 1
            new = _decode_git_path(parts[index]) if index < len(parts) else ""
            index += 1
            if old:
                rows.append((status, old))
            if new:
                rows.append((status, new))
            continue
        rows.append((status, _decode_git_path(parts[index])))
        index += 1
    return rows


def _ls_tree_mode(repo: Path, rev: str, rel: str) -> str | None:
    result = _git(repo, "ls-tree", rev, "--", rel)
    if result.returncode != 0:
        return None
    lines = (result.stdout or "").splitlines()
    if not lines:
        return None
    return lines[0].split(None, 1)[0]


def _worktree_mode(repo: Path, rel: str) -> str | None:
    path = repo / rel
    if path.is_symlink():
        return "120000"
    if not path.is_file():
        return None
    executable = bool(path.stat().st_mode & 0o111)
    return "100755" if executable else "100644"


def _mode_hunk(rel: str, before_mode: str | None, after_mode: str | None) -> str:
    if not before_mode or not after_mode or before_mode == after_mode:
        return ""
    return (
        f"diff --git a/{rel} b/{rel}\n"
        f"old mode {before_mode}\n"
        f"new mode {after_mode}\n"
    )


def _sha_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _try_decode(data: bytes) -> str | None:
    try:
        return data.decode("utf-8")
    except UnicodeDecodeError:
        return None


def _file_bytes(repo: Path, rel: str) -> tuple[bool, bytes | None]:
    """工作区内容;符号链接按 Git blob 语义只取链接文本本身。

    目标可能在仓库之外——跟随即把外部文件内容带进评审产物。
    """

    path = repo / rel
    if path.is_symlink():
        try:
            target = os.readlink(path)
        except OSError:
            return False, None
        return True, os.fspath(target).encode("utf-8", "surrogateescape")
    if not path.is_file():
        return False, None
    return True, path.read_bytes()


def _show_bytes(repo: Path, spec: str) -> bytes | None:
    result = subprocess.run(
        ["git", "show", spec], cwd=repo, check=False, capture_output=True)
    if result.returncode != 0:
        return None
    return result.stdout


def _index_bytes(repo: Path, rel: str) -> tuple[bool, bytes | None]:
    """暂存区(stage 0)内容;未跟踪/未暂存新文件不在索引中。"""

    result = subprocess.run(
        ["git", "show", f":{rel}"], cwd=repo, check=False, capture_output=True)
    if result.returncode != 0:
        return False, None
    return True, result.stdout or b""


def _git_has(repo: Path, spec: str) -> bool:
    return _git(repo, "cat-file", "-e", spec).returncode == 0


def _unified(rel: str, before: str | None, after: str | None) -> str:
    old = [] if before is None else before.splitlines(keepends=True)
    new = [] if after is None else after.splitlines(keepends=True)
    if old == new:
        return ""
    old_name = "/dev/null" if before is None else f"a/{rel}"
    new_name = "/dev/null" if after is None else f"b/{rel}"
    text = "".join(difflib.unified_diff(
        old, new, fromfile=old_name, tofile=new_name, lineterm="\n"))
    if text and not text.endswith("\n"):
        text += "\n"
    return text


def _unified_bytes(rel: str, before: bytes | None, after: bytes | None) -> str:
    if before == after:
        return ""
    old_text = None if before is None else _try_decode(before)
    new_text = None if after is None else _try_decode(after)
    old_binary = before is not None and old_text is None
    new_binary = after is not None and new_text is None
    if old_binary or new_binary:
        old_mark = "absent" if before is None else _sha_bytes(before)
        new_mark = "absent" if after is None else _sha_bytes(after)
        return f"Binary file {rel} changed ({old_mark} -> {new_mark})\n"
    return _unified(rel, old_text, new_text)


def capture_pending_review(repo: Path | str, baseline: str,
                           include: list[str], exclude: list[str] | None = None,
                           commit_authorized: bool = False) -> dict:
    """Read-only capture of in-scope pending work versus baseline."""

    repo = Path(repo)
    include = [_norm(item) for item in include]
    exclude = [_norm(item) for item in (exclude or [])]
    if not include and not exclude:
        return {
            "ok": False,
            "complete": False,
            "gate_required": False,
            "wrote": False,
            "created_commit": False,
            "error": "目标范围未明确",
        }
    resolved = _git(repo, "rev-parse", "--verify", baseline)
    if resolved.returncode != 0:
        return {
            "ok": False,
            "complete": False,
            "gate_required": False,
            "wrote": False,
            "created_commit": False,
            "error": f"基线无法解析:{baseline}",
        }
    baseline_sha = resolved.stdout.strip()
    committed_names = {
        path for code, path in _name_status(repo, baseline_sha, "HEAD")
        if _in_scope(path, include, exclude)
    }
    status = _status_entries(repo)
    excluded_present = sorted({
        path for _code, path in status if any(_matches(path, item) for item in exclude)
    })
    staged: set[str] = set()
    unstaged: set[str] = set()
    untracked: set[str] = set()
    deleted: set[str] = set()
    pending_paths: set[str] = set(committed_names)
    for code, path in status:
        if not _in_scope(path, include, exclude):
            continue
        pending_paths.add(path)
        if code == "??":
            untracked.add(path)
            continue
        if code[0] not in {" ", "?"}:
            staged.add(path)
        if code[1] not in {" ", "?"}:
            unstaged.add(path)
        if "D" in code:
            deleted.add(path)
    for path in list(pending_paths):
        exists, _payload = _file_bytes(repo, path)
        if not exists and _git_has(repo, f"HEAD:{path}"):
            deleted.add(path)
    listed = _git(repo, "ls-files", "-z", "--", *include)
    for raw in (listed.stdout or "").split("\0"):
        path = _norm(raw)
        if not path or not _in_scope(path, include, exclude):
            continue
        if _ls_tree_mode(repo, baseline_sha, path) != _worktree_mode(repo, path):
            pending_paths.add(path)
    patches: list[str] = []
    version_rows: list[str] = [f"baseline={baseline_sha}"]
    path_versions: dict[str, str] = {}
    for path in sorted(pending_paths):
        before = _show_bytes(repo, f"{baseline_sha}:{path}")
        exists, after = _file_bytes(repo, path)
        tracked, staged_bytes = _index_bytes(repo, path)
        # 同时捕获 基线→暂存区 与 暂存区→工作区 两段状态:
        # 暂存了改动又把工作区还原成基线内容时,净比对会漏掉
        # 下一次提交即将携带的暂存内容,这里以暂存内容为准补上。
        if exists and after == before:
            if tracked and staged_bytes != before:
                after = staged_bytes
            elif not tracked and before is not None:
                after = None  # 暂存删除后工作区又还原,提交仍将删除
        current = after if exists else None
        hunk = _unified_bytes(path, before, current)
        before_mode = _ls_tree_mode(repo, baseline_sha, path)
        after_mode = _worktree_mode(repo, path) if exists else None
        mode_hunk = _mode_hunk(path, before_mode, after_mode)
        if mode_hunk and hunk:
            hunk = mode_hunk + hunk
        elif mode_hunk:
            hunk = mode_hunk
        if hunk:
            patches.append(hunk)
        marker = "DEL" if current is None else _sha_bytes(current)
        if after_mode:
            marker = f"{marker}|{after_mode}"
        elif before_mode:
            marker = f"{marker}|{before_mode}"
        path_versions[path] = marker
        version_rows.append(f"{path}\t{marker}")
    patch = "".join(patches)
    content_version = _sha("\n".join(version_rows) + "\n")
    committed_args = ["diff", f"{baseline_sha}...HEAD"]
    if include:
        committed_args.extend(["--", *include])
    committed_patch = _git(repo, *committed_args)
    committed_diff_empty = not (committed_patch.stdout or "").strip()
    uncommitted = staged | unstaged | untracked | deleted
    committed_only_complete = (not committed_diff_empty) and not uncommitted
    return {
        "ok": True,
        "complete": bool(patch.strip()),
        "gate_required": False,
        "wrote": False,
        "created_commit": False,
        "commit_authorized": bool(commit_authorized),
        "baseline": baseline_sha,
        "target_scope": {"include": include, "exclude": exclude},
        "content_version": content_version,
        "committed_diff_empty": committed_diff_empty,
        "committed_only_complete": committed_only_complete,
        "paths": {
            "committed": sorted(committed_names),
            "staged": sorted(staged),
            "unstaged": sorted(unstaged),
            "untracked": sorted(untracked),
            "deleted": sorted(deleted),
        },
        "excluded": excluded_present,
        "patch": patch,
        "path_versions": path_versions,
        "axes": {
            "standards": {
                "axis": "standards",
                "content_version": content_version,
            },
            "spec": {
                "axis": "spec",
                "content_version": content_version,
            },
        },
    }


def recheck_pending_review(repo: Path | str, previous: dict) -> dict:
    """Compare a new capture with a previous one; do not create commits."""

    scope = previous.get("target_scope") or {}
    current = capture_pending_review(
        repo, str(previous.get("baseline") or ""),
        list(scope.get("include") or []),
        list(scope.get("exclude") or []),
        commit_authorized=bool(previous.get("commit_authorized")))
    if not current.get("ok"):
        return {
            "ok": False,
            "content_changed": True,
            "stale_conclusions": True,
            "created_commit": False,
            "error": current.get("error") or "复核捕获失败",
        }
    old_paths = previous.get("path_versions") or {}
    new_paths = current.get("path_versions") or {}
    names = sorted(set(old_paths) | set(new_paths))
    affected = [name for name in names if old_paths.get(name) != new_paths.get(name)]
    unaffected = [name for name in names if old_paths.get(name) == new_paths.get(name)]
    changed = current.get("content_version") != previous.get("content_version")
    return {
        "ok": True,
        "content_changed": changed,
        "stale_conclusions": changed,
        "previous_content_version": previous.get("content_version"),
        "current_content_version": current.get("content_version"),
        "affected": affected,
        "unaffected": unaffected,
        "created_commit": False,
        "wrote": False,
        "gate_required": False,
        "axes": current.get("axes"),
    }


def _cmd_capture(args: argparse.Namespace) -> int:
    result = capture_pending_review(
        args.repo, args.baseline, args.include or [], args.exclude or [],
        commit_authorized=args.commit_authorized)
    json.dump(result, sys.stdout, ensure_ascii=False, indent=2)
    sys.stdout.write("\n")
    return 0 if result.get("ok") else 1


def _load_artifact(args: argparse.Namespace) -> dict:
    if args.artifact_file:
        return json.loads(Path(args.artifact_file).read_text(encoding="utf-8"))
    return json.loads(args.artifact or "{}")


def _cmd_recheck(args: argparse.Namespace) -> int:
    result = recheck_pending_review(args.repo, _load_artifact(args))
    json.dump(result, sys.stdout, ensure_ascii=False, indent=2)
    sys.stdout.write("\n")
    return 0 if result.get("ok") else 1


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Capture complete pending review without committing")
    sub = parser.add_subparsers(dest="cmd", required=True)
    capture = sub.add_parser("capture", help="Read-only complete pending capture")
    capture.add_argument("--repo", required=True)
    capture.add_argument("--baseline", required=True)
    capture.add_argument("--include", action="append", default=[])
    capture.add_argument("--exclude", action="append", default=[])
    capture.add_argument("--commit-authorized", action="store_true")
    capture.set_defaults(func=_cmd_capture)
    recheck = sub.add_parser("recheck", help="Recheck affected scope after content change")
    recheck.add_argument("--repo", required=True)
    recheck.add_argument("--artifact", default="")
    recheck.add_argument("--artifact-file", default="")
    recheck.set_defaults(func=_cmd_recheck)
    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())

#!/usr/bin/env python3
"""Read-only check of a writing-for-agents install before a source switch."""

from __future__ import annotations

import argparse
import difflib
import hashlib
import json
import re
import subprocess
import sys
from pathlib import Path, PurePosixPath


def fail(message: str, *, status: int = 1) -> int:
    print(f"UNVERIFIED: {message}", file=sys.stderr)
    return status


def read_lock_record(lock_path: Path) -> dict[str, object]:
    if not lock_path.is_file():
        raise ValueError(f"lock file is missing: {lock_path}")
    try:
        lock = json.loads(lock_path.read_text(encoding="utf-8"))
        record = lock["skills"]["writing-for-agents"]
    except (OSError, json.JSONDecodeError, KeyError, TypeError, AttributeError) as error:
        raise ValueError(f"cannot read writing-for-agents lock record: {error}") from error
    required = ("source", "sourceType", "computedHash")
    if any(not isinstance(record.get(field), str) or not record[field] for field in required):
        raise ValueError("lock record is missing source, sourceType, skillPath, or computedHash")
    if not re.fullmatch(r"[0-9a-f]{64}", record["computedHash"]):
        raise ValueError("lock record has an invalid computedHash")
    source = record["source"]
    source_type = record["sourceType"]
    computed_hash = record["computedHash"]
    if source_type not in {"github", "local"}:
        raise ValueError(f"unsupported lock sourceType: {source_type}")
    if source_type == "github":
        if not isinstance(record.get("skillPath"), str) or not record["skillPath"]:
            raise ValueError("GitHub lock record must include skillPath")
        if record.get("ref") is not None and not isinstance(record["ref"], str):
            raise ValueError("GitHub lock ref must be a string when present")
        skill_path = PurePosixPath(record["skillPath"])
        if skill_path.name != "SKILL.md" or skill_path.parent.name != "writing-for-agents":
            raise ValueError("lock record skillPath does not identify writing-for-agents/SKILL.md")
    elif record.get("ref"):
        raise ValueError("local lock record unexpectedly includes a Git ref")
    return record


def verify_lock_source(record: dict[str, object], reference: Path, scope_root: Path) -> None:
    metadata = (reference / "SOURCE.md").read_text(encoding="utf-8")

    checkout_root = reference.parent.parent
    remote = subprocess.run(
        ["git", "-C", str(checkout_root), "remote", "get-url", "origin"],
        capture_output=True, text=True, check=False,
    )
    top_level = subprocess.run(
        ["git", "-C", str(checkout_root), "rev-parse", "--show-toplevel"],
        capture_output=True, text=True, check=False,
    )
    if remote.returncode == 0 and top_level.returncode == 0 \
            and Path(top_level.stdout.strip()).resolve() == checkout_root.resolve():
        match = re.search(r"github\.com[:/]([^/]+/[^/]+?)(?:\.git)?$", remote.stdout.strip())
        remote_repo = match.group(1) if match else ""
        if record["sourceType"] == "github" and remote_repo.lower() == str(record["source"]).lower():
            expected_skill_path = reference.relative_to(checkout_root).as_posix() + "/SKILL.md"
            if record.get("skillPath") != expected_skill_path:
                raise ValueError("lock skillPath does not match the supplied GitHub checkout")
            ref = record.get("ref")
            if ref:
                resolved_ref = subprocess.run(
                    ["git", "-C", str(checkout_root), "rev-parse", "--verify",
                     "--end-of-options", f"{ref}^{{commit}}"],
                    capture_output=True, text=True, check=False,
                )
                head = subprocess.run(
                    ["git", "-C", str(checkout_root), "rev-parse", "HEAD"],
                    capture_output=True, text=True, check=False,
                )
                if resolved_ref.returncode != 0 or head.returncode != 0 \
                        or resolved_ref.stdout.strip() != head.stdout.strip():
                    raise ValueError("reference checkout HEAD does not match the lock Git ref")
            return

    def field(label: str) -> str:
        match = re.search(rf"^{re.escape(label)}: `([^`]+)`$", metadata, re.MULTILINE)
        if not match:
            raise ValueError(f"reference SOURCE.md is missing {label}")
        return match.group(1)

    source_type = record["sourceType"]
    if source_type == "github":
        fixed_metadata = (
            "Source repository", "Fixed source commit", "Fixed source skill path",
        )
        present = [re.search(rf"^{re.escape(label)}: `[^`]+`$", metadata, re.MULTILINE)
                   is not None for label in fixed_metadata]
        if any(present) and not all(present):
            raise ValueError("reference SOURCE.md has incomplete fixed-source metadata")
        if all(present):
            expected = {
                "source": field("Source repository"),
                "ref": field("Fixed source commit"),
                "skillPath": field("Fixed source skill path"),
            }
            mismatches = [key for key, value in expected.items() if record.get(key) != value]
            if mismatches:
                raise ValueError("lock source identity does not match reference SOURCE.md: "
                                 + ", ".join(mismatches))
        else:
            if record["source"] not in metadata:
                raise ValueError("lock GitHub source is not identified by reference SOURCE.md")
            if record.get("skillPath") != "skills/productivity/writing-for-agents/SKILL.md":
                raise ValueError("lock skillPath does not identify the pinned writing-for-agents source")
        if record.get("ref") and not re.fullmatch(r"[0-9a-f]{40}", str(record["ref"])):
            raise ValueError("GitHub lock ref without a matching checkout must be a full commit SHA")
        return

    source_root = Path(str(record["source"]))
    if not source_root.is_absolute():
        source_root = scope_root / source_root
    expected_reference = (source_root / "skills" / "writing-for-agents").resolve()
    if expected_reference != reference.resolve():
        raise ValueError("local lock source does not resolve to the supplied reference-dir")
    skill_path = record.get("skillPath")
    if skill_path and skill_path != "skills/writing-for-agents/SKILL.md":
        raise ValueError("local lock record skillPath does not identify the local distribution")


def parse_manifest(path: Path) -> dict[str, str]:
    entries: dict[str, str] = {}
    for line_number, line in enumerate(path.read_text(encoding="ascii").splitlines(), 1):
        digest, separator, rel = line.partition("  ")
        if not separator or not re.fullmatch(r"[0-9a-f]{64}", digest):
            raise ValueError(f"invalid SHA256SUMS line {line_number}")
        manifest_path = PurePosixPath(rel)
        if not rel or str(manifest_path) != rel or manifest_path.is_absolute() \
                or ".." in manifest_path.parts or rel in entries:
            raise ValueError(f"unsafe or duplicate path at SHA256SUMS line {line_number}")
        entries[rel] = digest
    if not entries:
        raise ValueError("SHA256SUMS contains no files")
    return entries


def compare_directory(directory: Path, manifest: dict[str, str]) -> tuple[list[str], list[str]]:
    actual_files: set[str] = set()
    issues: list[str] = []
    modified_files: list[str] = []
    for path in directory.rglob("*"):
        if path.is_symlink():
            issues.append(f"symlink cannot be verified: {path.relative_to(directory).as_posix()}")
        elif path.is_file():
            rel = path.relative_to(directory).as_posix()
            if rel != "SHA256SUMS":
                actual_files.add(rel)
    for rel in sorted(set(manifest) - actual_files):
        issues.append(f"missing: {rel}")
    for rel in sorted(actual_files - set(manifest)):
        issues.append(f"unlisted local file: {rel}")
    for rel in sorted(set(manifest) & actual_files):
        actual = hashlib.sha256((directory / rel).read_bytes()).hexdigest()
        if actual != manifest[rel]:
            issues.append(f"modified: {rel}")
            modified_files.append(rel)
    return issues, modified_files


def compute_skills_cli_hash(directory: Path) -> str:
    """Mirror skills@1.7.0's folder hash for this ASCII-named distribution."""
    files: list[tuple[str, Path]] = []
    for path in directory.rglob("*"):
        if path.is_symlink():
            raise ValueError(f"symlink cannot be hashed safely: {path.relative_to(directory)}")
        if not path.is_file():
            continue
        rel = path.relative_to(directory).as_posix()
        if any(part in {".git", "node_modules"} for part in PurePosixPath(rel).parts):
            continue
        if not rel.isascii():
            raise ValueError(f"non-ASCII path cannot be ordered like skills CLI: {rel}")
        files.append((rel, path))
    folded = [rel.casefold() for rel, _ in files]
    if len(folded) != len(set(folded)):
        raise ValueError("case-insensitive duplicate paths cannot be ordered like skills CLI")
    files.sort(key=lambda item: (item[0].casefold(), item[0]))
    digest = hashlib.sha256()
    for rel, path in files:
        digest.update(rel.encode("utf-8"))
        digest.update(path.read_bytes())
    return digest.hexdigest()


def compare_copies(reference: Path, installed: Path) -> tuple[list[str], list[tuple[str, str]]]:
    def files(directory: Path) -> tuple[set[str], list[str]]:
        result: set[str] = set()
        issues: list[str] = []
        for path in directory.rglob("*"):
            if path.is_symlink():
                issues.append(f"symlink cannot be compared: {path.relative_to(directory).as_posix()}")
            elif path.is_file():
                result.add(path.relative_to(directory).as_posix())
        return result, issues

    expected_files, issues = files(reference)
    installed_files, installed_issues = files(installed)
    issues.extend(installed_issues)
    differences: list[tuple[str, str]] = []
    for rel in sorted(expected_files - installed_files):
        issues.append(f"missing: {rel}")
        differences.append((rel, "missing"))
    for rel in sorted(installed_files - expected_files):
        issues.append(f"unlisted local file: {rel}")
        differences.append((rel, "added"))
    for rel in sorted(expected_files & installed_files):
        if hashlib.sha256((reference / rel).read_bytes()).digest() \
                != hashlib.sha256((installed / rel).read_bytes()).digest():
            issues.append(f"modified: {rel}")
            differences.append((rel, "modified"))
    return issues, differences


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--installed-dir", required=True, type=Path,
                        help="absolute path to this installation's writing-for-agents directory")
    parser.add_argument("--lock-file", required=True, type=Path,
                        help="skills-lock.json for the same installation scope")
    parser.add_argument("--reference-dir", required=True, type=Path,
                        help="pristine copy of the exact locked source")
    parser.add_argument("--show-diff", action="store_true",
                        help="print text differences against --reference-dir")
    args = parser.parse_args()

    if not args.installed_dir.is_absolute():
        return fail("installed-dir must be absolute")
    if not args.lock_file.is_absolute():
        return fail("lock-file must be absolute")
    if not args.reference_dir.is_absolute():
        return fail("reference-dir must be absolute")
    target = args.installed_dir.resolve()
    lock_path = args.lock_file.resolve()
    if target.name != "writing-for-agents" or not target.is_dir():
        return fail("installed-dir must be an existing absolute writing-for-agents directory")
    if target.parent.name != "skills" or len(target.parents) < 3:
        return fail("installed-dir must be inside a skills directory within one installation scope")
    scope_root = target.parents[2]
    if lock_path.parent != scope_root:
        return fail("lock-file must belong to the same installation scope as installed-dir")
    print(f"installed scope root: {scope_root}")
    print(f"installed target: {target}")

    try:
        lock_record = read_lock_record(lock_path)
    except ValueError as error:
        return fail(str(error))

    reference = args.reference_dir.resolve()
    if reference == target or not reference.is_dir():
        return fail("reference-dir must be a distinct, existing directory")
    reference_manifest = reference / "SHA256SUMS"
    if not reference_manifest.is_file():
        return fail("reference source has no SHA256SUMS; cannot verify it against the lock")
    try:
        verify_lock_source(lock_record, reference, scope_root)
        reference_entries = parse_manifest(reference_manifest)
        reference_hash = compute_skills_cli_hash(reference)
    except (OSError, ValueError, UnicodeError) as error:
        return fail(f"cannot verify the lock source and reference manifest: {error}")
    if reference_hash != lock_record["computedHash"]:
        return fail("reference source hash does not match the lock computedHash")
    reference_issues, _ = compare_directory(reference, reference_entries)
    if reference_issues:
        return fail("reference copy is not pristine: " + "; ".join(reference_issues))

    ref = lock_record.get("ref", "not recorded")
    print(f"lock record: source={lock_record['source']}; ref={ref}; "
          f"type={lock_record['sourceType']}; computedHash={lock_record['computedHash']}")

    issues, differences = compare_copies(reference, target)

    if issues:
        print("local differences require preservation and review:")
        for issue in issues:
            print(f"- {issue}")
        if args.show_diff:
            for rel, kind in differences:
                reference_file = reference / rel
                installed_file = target / rel
                try:
                    old_lines = reference_file.read_text(encoding="utf-8").splitlines(keepends=True) \
                        if kind != "added" else []
                    new_lines = installed_file.read_text(encoding="utf-8").splitlines(keepends=True) \
                        if kind != "missing" else []
                except UnicodeDecodeError:
                    print(f"text diff unavailable for non-UTF-8 file: {rel}")
                    continue
                for line in difflib.unified_diff(
                    old_lines, new_lines, fromfile=f"a/{rel}", tofile=f"b/{rel}", n=3
                ):
                    print(line, end="" if line.endswith("\n") else "\n")
        return 1
    print(f"verified installed files against {reference} and lock computedHash")
    print("No local differences detected; this check does not switch or update the installation.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

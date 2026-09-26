#!/usr/bin/env python3
"""Verify or generate the pinned, self-contained writing-for-agents skill copy."""

from __future__ import annotations

import argparse
import hashlib
import re
import sys
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

REPO = Path(__file__).resolve().parents[1]
TARGET = REPO / "skills" / "writing-for-agents"
SOURCE_REPO = "LC-86/mattpocockskills"
SOURCE_COMMIT = "f3c726f275fa1ac59fef33732e527dded6d62479"
SOURCE_SKILL = "skills/productivity/writing-for-agents"
SOURCE_FILES = {
    "SKILL.md": "SKILL.md",
    "SKILL-MECHANICS.md": "SKILL-MECHANICS.md",
    "references/subagent-delegation.md": "references/subagent-delegation.md",
    "LICENSE": "LICENSE",
}
EXPECTED_FILES = {
    *SOURCE_FILES.values(), "SOURCE.md", "SHA256SUMS",
}
MECHANICS_NOTE = """## Codex invocation policy

The `disable-model-invocation: true` frontmatter field only controls hosts that document it. Codex uses the skill-local `agents/openai.yaml` policy instead. When authoring a user-invoked skill for Codex, include this file in addition to any frontmatter switch required by other hosts:

```yaml
policy:
  allow_implicit_invocation: false
```

Do not claim the frontmatter field alone prevents Codex from implicitly invoking the skill.

"""


def fetch(path: str) -> bytes:
    url = f"https://raw.githubusercontent.com/{SOURCE_REPO}/{SOURCE_COMMIT}/{path}"
    request = Request(url, headers={"User-Agent": "MyGameStudio-source-sync"})
    with urlopen(request, timeout=30) as response:
        return response.read()


def source_manifest() -> dict[str, str]:
    raw = fetch(f"{SOURCE_SKILL}/SHA256SUMS").decode("utf-8")
    rows: dict[str, str] = {}
    for line in raw.splitlines():
        digest, separator, path = line.partition("  ")
        if separator and re.fullmatch(r"[0-9a-f]{64}", digest):
            rows[path] = digest
    return rows


def with_standard_license_field(skill_md: bytes) -> bytes:
    text = skill_md.decode("utf-8")
    match = re.match(r"\A---\n(.*?)\n---\n", text, re.DOTALL)
    if not match:
        raise ValueError("upstream SKILL.md has no standard frontmatter")
    header = match.group(1)
    if re.search(r"^license:", header, re.MULTILINE):
        raise ValueError("upstream SKILL.md already has a license field; review packaging rule")
    packaged_header = f"{header}\nlicense: MIT"
    return f"---\n{packaged_header}\n---\n{text[match.end():]}".encode("utf-8")


def with_codex_invocation_policy(mechanics_md: bytes) -> bytes:
    text = mechanics_md.decode("utf-8")
    anchor = "## Splitting by invocation\n"
    if text.count(anchor) != 1 or "## Codex invocation policy\n" in text:
        raise ValueError("upstream SKILL-MECHANICS.md no longer matches the deterministic packaging rule")
    return text.replace(anchor, MECHANICS_NOTE + anchor, 1).encode("utf-8")


def render() -> dict[str, bytes]:
    checksums = source_manifest()
    source: dict[str, bytes] = {}
    for path in SOURCE_FILES:
        raw = fetch(f"{SOURCE_SKILL}/{path}")
        expected = checksums.get(path)
        actual = hashlib.sha256(raw).hexdigest()
        if expected != actual:
            raise ValueError(f"pinned upstream checksum mismatch for {path}: {actual}")
        source[path] = raw

    packaged = {
        "SKILL.md": with_standard_license_field(source["SKILL.md"]),
        "SKILL-MECHANICS.md": with_codex_invocation_policy(source["SKILL-MECHANICS.md"]),
        "references/subagent-delegation.md": source["references/subagent-delegation.md"],
    }
    license_addendum = (
        "\n\n---\n"
        "MyGameStudio distribution notice (additional attribution; upstream terms above are unchanged)\n"
        "Copyright (c) 2026 LC-86 / MyGameStudio\n"
        "Skill directory: writing-for-agents\n"
        f"Upstream source: https://github.com/{SOURCE_REPO}/tree/{SOURCE_COMMIT}/{SOURCE_SKILL}\n"
    ).encode("utf-8")
    packaged["LICENSE"] = source["LICENSE"] + license_addendum

    source_rows = []
    for source_path, target_path in SOURCE_FILES.items():
        source_hash = hashlib.sha256(source[source_path]).hexdigest()
        target_hash = hashlib.sha256(packaged[target_path]).hexdigest()
        if source_path == "SKILL.md":
            rule = "adds only the required `license: MIT` field; body is byte-identical"
        elif source_path == "SKILL-MECHANICS.md":
            rule = "inserts a fixed Codex invocation-policy note; upstream text is otherwise unchanged"
        elif source_path == "LICENSE":
            rule = "upstream license is byte-identical; appends a distribution attribution notice"
        else:
            rule = "byte-identical"
        source_rows.append(
            f"| `{source_path}` | `{target_path}` | `{source_hash}` | `{target_hash}` | {rule} |"
        )
    host_metadata_hash = checksums.get("agents/openai.yaml", "")
    if not re.fullmatch(r"[0-9a-f]{64}", host_metadata_hash):
        raise ValueError("pinned upstream manifest has no agents/openai.yaml digest")

    source_doc = "\n".join([
        "# writing-for-agents distribution source",
        "",
        f"Editable authority: [`writing-for-agents`](https://github.com/{SOURCE_REPO}/tree/{SOURCE_COMMIT}/{SOURCE_SKILL})",
        f"Source repository: `{SOURCE_REPO}`",
        f"Fixed source commit: `{SOURCE_COMMIT}`",
        f"Fixed source skill path: `{SOURCE_SKILL}/SKILL.md`",
        "",
        "This directory is a generated distribution copy. Edit the fork, pin a new full commit, and review the generated diff; do not edit this copy as an independent source.",
        "",
        "| Source path | Distributed path | Source SHA-256 | Distributed SHA-256 | Packaging rule |",
        "|---|---|---|---|---|",
        *source_rows,
        f"| `agents/openai.yaml` | — | `{host_metadata_hash}` | — | not included: this is an on-demand method and MyGameStudio on-demand methods carry no host-specific file |",
        "| `SOURCE.md`, `SHA256SUMS` | same | — | — | generated for this distribution and checked separately |",
        "",
        "The source skill's required references stay inside this directory. The bundle has no runtime dependency on the source checkout, a sibling repository, or a network service.",
        "",
    ])
    packaged["SOURCE.md"] = source_doc.encode("utf-8")
    checksum_rows = []
    for rel, data in sorted(packaged.items()):
        checksum_rows.append(f"{hashlib.sha256(data).hexdigest()}  {rel}")
    packaged["SHA256SUMS"] = ("\n".join(checksum_rows) + "\n").encode("ascii")
    return packaged


def current_hashes_are_intact() -> bool:
    manifest_path = TARGET / "SHA256SUMS"
    if not manifest_path.is_file():
        return False
    recorded: dict[str, str] = {}
    for line in manifest_path.read_text(encoding="ascii").splitlines():
        digest, separator, rel = line.partition("  ")
        if not separator or not re.fullmatch(r"[0-9a-f]{64}", digest):
            return False
        recorded[rel] = digest
    actual_files = {
        path.relative_to(TARGET).as_posix()
        for path in TARGET.rglob("*") if path.is_file() and path.name != "SHA256SUMS"
    }
    if set(recorded) != actual_files:
        return False
    return all(
        hashlib.sha256((TARGET / rel).read_bytes()).hexdigest() == digest
        for rel, digest in recorded.items()
    )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--write", action="store_true", help="write the generated copy")
    parser.add_argument("--force", action="store_true", help="allow replacing files that fail the current digest manifest")
    parser.add_argument("--repo-root", type=Path, default=REPO,
                        help="repository root (defaults to the checkout containing this script)")
    args = parser.parse_args()
    global TARGET
    TARGET = args.repo_root.resolve() / "skills" / "writing-for-agents"

    try:
        generated = render()
    except (HTTPError, URLError, TimeoutError, ValueError) as error:
        print(f"source verification failed: {error}", file=sys.stderr)
        return 1

    extras = sorted(
        path.relative_to(TARGET).as_posix()
        for path in TARGET.rglob("*") if path.is_file()
    ) if TARGET.exists() else []
    extras = [path for path in extras if path not in EXPECTED_FILES]
    if extras:
        print(f"unexpected files under {TARGET}: {extras}", file=sys.stderr)
        return 1

    if args.write:
        if TARGET.exists() and not current_hashes_are_intact() and not args.force:
            print("existing generated files differ from their SHA256SUMS; inspect and preserve local changes, or pass --force after review", file=sys.stderr)
            return 1
        for rel, data in generated.items():
            destination = TARGET / rel
            destination.parent.mkdir(parents=True, exist_ok=True)
            destination.write_bytes(data)
        print(f"generated {len(generated)} files from {SOURCE_REPO}@{SOURCE_COMMIT}")
        return 0

    if not TARGET.is_dir():
        print(f"missing distribution directory: {TARGET}", file=sys.stderr)
        return 1
    mismatches = []
    for rel, expected in generated.items():
        path = TARGET / rel
        if not path.is_file() or path.read_bytes() != expected:
            mismatches.append(rel)
    found = {
        path.relative_to(TARGET).as_posix()
        for path in TARGET.rglob("*") if path.is_file()
    }
    mismatches.extend(sorted(found - EXPECTED_FILES))
    if mismatches:
        print("distribution differs from its pinned source: " + ", ".join(mismatches), file=sys.stderr)
        return 1
    print(f"verified {len(generated)} files against {SOURCE_REPO}@{SOURCE_COMMIT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

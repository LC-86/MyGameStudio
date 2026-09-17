#!/usr/bin/env python3
"""检查用户文档导航、相对链接，以及技能索引与公开技能集合一致。

    python3 scripts/validate-docs.py
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
PLUGIN_SKILLS = REPO / "plugin" / "skills"
LINK = re.compile(r"\[[^\]]*\]\(([^)\s]+)\)")
SKILL_FRONTMATTER = re.compile(r"^---\nname:\s*\S+", re.MULTILINE)

USER_DOC_GLOBS = (
    "README.md",
    "README.en.md",
    "CHANGELOG.md",
    "CONTRIBUTING.md",
    "SECURITY.md",
    "THIRD_PARTY_NOTICES.md",
    "docs/**/*.md",
    "examples/**/*.md",
)

README_MUST_LINK = (
    "docs/getting-started.md",
    "docs/installation/README.md",
    "docs/installation/codex.md",
    "docs/installation/zcode.md",
    "docs/installation/grok-build.md",
    "docs/installation/claude-code.md",
    "docs/usage/workflows.md",
    "docs/reference/capabilities.md",
    "docs/reference/compatibility.md",
    "docs/skills/README.md",
    "examples/README.md",
    "CONTRIBUTING.md",
    "LICENSE",
    "THIRD_PARTY_NOTICES.md",
)

DOCS_INDEX_MUST_LINK = (
    "getting-started.md",
    "installation/README.md",
    "installation/codex.md",
    "installation/zcode.md",
    "installation/grok-build.md",
    "installation/claude-code.md",
    "installation/upgrade-and-uninstall.md",
    "usage/workflows.md",
    "usage/existing-projects.md",
    "reference/capabilities.md",
    "reference/compatibility.md",
    "reference/data-and-permissions.md",
    "reference/upstream.md",
    "reference/troubleshooting.md",
    "skills/README.md",
    "skills/game/game-producer.md",
    "skills/game/game-init.md",
    "skills/game/game-design.md",
    "development/architecture.md",
    "development/testing.md",
    "development/releasing.md",
)

FILTERED_CHECKSUM = (
    "grep ' mygamestudio-2.0.2.tar.gz$' SHA256SUMS.txt | shasum -a 256 -c -"
)
UNFILTERED_CHECKSUM = "shasum -a 256 -c SHA256SUMS.txt"
PUBLISHED_RELEASE = "releases/tag/v2.0.2"
STALE_UNRELEASED_PHRASES = (
    "待人工上传",
    "尚未打 `v2.0.2`",
    "若尚无 v2.0.2",
    "Until a `v2.0.2` GitHub tag exists",
    "标签仍待维护者人工上传",
    "2.0.2 标签待",
    "尚未打 GitHub Release 标签时",
    "GitHub Release 标签待",
)

INSTALL_MARKERS = {
    "docs/installation/zcode.md": (
        ".zcode-plugin/plugin.json",
        "marketplace.json",
        "隔离",
        "未验证",
        "复制一行即可安装",
        FILTERED_CHECKSUM,
        PUBLISHED_RELEASE,
    ),
    "docs/installation/grok-build.md": (
        ".grok/plugins",
        "--plugin-dir",
        "隔离",
        "未验证",
        "复制一行即可安装",
        FILTERED_CHECKSUM,
        PUBLISHED_RELEASE,
    ),
    "docs/installation/codex.md": (
        "codex plugin add",
        ".codex-plugin/plugin.json",
        "未验证",
        "隔离",
        "复制一行即可安装",
        FILTERED_CHECKSUM,
    ),
    "docs/installation/claude-code.md": (
        ".claude-plugin/plugin.json",
        "claude --plugin-dir",
        "~/.claude/plugins",
        "隔离",
        "未验证",
        "复制一行即可安装",
        FILTERED_CHECKSUM,
        PUBLISHED_RELEASE,
    ),
    "docs/installation/README.md": (
        "复制一行即可安装",
        "复制一段指令发给 Agent",
        "SHA256SUMS",
        "npx skills",
        "28",
        "隔离",
        FILTERED_CHECKSUM,
        PUBLISHED_RELEASE,
        "未验证",
    ),
}


def iter_user_docs() -> list[Path]:
    files: list[Path] = []
    for pattern in USER_DOC_GLOBS:
        if "*" in pattern:
            files.extend(sorted(REPO.glob(pattern)))
        else:
            path = REPO / pattern
            if path.is_file():
                files.append(path)
    return files


def public_skill_names() -> set[str]:
    return {path.name for path in PLUGIN_SKILLS.iterdir() if path.is_dir()}


def resolve_link(source: Path, target: str) -> Path | None:
    if target.startswith(("http://", "https://", "mailto:")):
        return None
    if target.startswith("#"):
        return source
    path_part = target.split("#", 1)[0]
    if not path_part:
        return source
    return (source.parent / path_part).resolve()


def contains_link(text: str, rel: str) -> bool:
    return rel in text or f"({rel})" in text or rel.replace("\\", "/") in text


def main() -> int:
    failures: list[str] = []
    docs = iter_user_docs()
    if not docs:
        print("FAIL: 未找到用户文档")
        return 1

    for path in docs:
        text = path.read_text(encoding="utf-8")
        rel = path.relative_to(REPO).as_posix()
        if path.parent != REPO and SKILL_FRONTMATTER.search(text):
            failures.append(f"{rel}: 用户文档不得带有技能 frontmatter（避免被安装器发现）")
        for raw in LINK.findall(text):
            dest = resolve_link(path, raw.strip())
            if dest is None:
                continue
            try:
                dest.relative_to(REPO)
            except ValueError:
                continue
            if not dest.exists():
                failures.append(f"{rel}: 断链 {raw}")

    readme = (REPO / "README.md").read_text(encoding="utf-8")
    for rel in README_MUST_LINK:
        if not contains_link(readme, rel):
            failures.append(f"README.md 缺少导航 {rel}")

    index = (REPO / "docs" / "README.md").read_text(encoding="utf-8")
    for rel in DOCS_INDEX_MUST_LINK:
        if not contains_link(index, rel):
            failures.append(f"docs/README.md 缺少导航 {rel}")

    skills_index = (REPO / "docs" / "skills" / "README.md").read_text(encoding="utf-8")
    missing = sorted(name for name in public_skill_names() if name not in skills_index)
    if missing:
        failures.append(f"docs/skills/README.md 未索引技能: {missing}")

    for rel, markers in INSTALL_MARKERS.items():
        text = (REPO / rel).read_text(encoding="utf-8")
        for marker in markers:
            if marker not in text:
                failures.append(f"{rel} 缺少必要说明: {marker}")

    if "隔离" not in readme or "docs/installation/" not in readme:
        failures.append("README.md 应导航到安装页并保留隔离验证口径")
    for marker in (
        "复制一行即可安装",
        "复制一段指令发给 Agent",
        "claude --plugin-dir",
        "docs/installation/claude-code.md",
        FILTERED_CHECKSUM,
        PUBLISHED_RELEASE,
    ):
        if marker not in readme:
            failures.append(f"README.md 缺少必要说明: {marker}")

    for path in docs:
        rel = path.relative_to(REPO).as_posix()
        if rel.startswith("dist/"):
            continue
        text = path.read_text(encoding="utf-8")
        if UNFILTERED_CHECKSUM in text:
            failures.append(
                f"{rel}: 用户下载流不得对整张 SHA256SUMS.txt 做 shasum -c，应使用过滤式校验"
            )
        for phrase in STALE_UNRELEASED_PHRASES:
            if phrase in text:
                failures.append(f"{rel}: 不得再写未发布标签措辞: {phrase}")

    dist_changelog = REPO / "dist" / "CHANGELOG.md"
    if dist_changelog.is_file():
        dist_text = dist_changelog.read_text(encoding="utf-8")
        if PUBLISHED_RELEASE not in dist_text:
            failures.append("dist/CHANGELOG.md 应记录 v2.0.2 已发布")
        for phrase in STALE_UNRELEASED_PHRASES:
            if phrase in dist_text:
                failures.append(
                    f"dist/CHANGELOG.md: 不得再写未发布标签措辞: {phrase}"
                )

    for rel, markers in (
        ("CHANGELOG.md", (PUBLISHED_RELEASE, "未验证")),
        ("docs/development/releasing.md", (PUBLISHED_RELEASE, "未验证")),
        ("docs/getting-started.md", (PUBLISHED_RELEASE,)),
        ("docs/reference/compatibility.md", (PUBLISHED_RELEASE, "未验证")),
        ("README.en.md", (PUBLISHED_RELEASE,)),
    ):
        text = (REPO / rel).read_text(encoding="utf-8")
        for marker in markers:
            if marker not in text:
                failures.append(f"{rel} 缺少必要说明: {marker}")

    if failures:
        print(f"FAIL ({len(failures)}):")
        for item in failures:
            print(f"  - {item}")
        return 1
    print(f"OK: 用户文档导航与链接检查通过（{len(docs)} 个文件）")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

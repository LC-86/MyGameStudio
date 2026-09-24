#!/usr/bin/env python3
"""检查用户文档导航、相对链接、版本一致性与旧安装命令残留。

    python3 scripts/validate-docs.py

技能源码布局与内容契约由 tests/test_skills_layout.py 检查，本脚本不重复。
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
SKILLS = REPO / "skills"
LINK = re.compile(r"\[[^\]]*\]\(([^)\s]+)\)")
FRONTMATTER = re.compile(r"\A---\nname:\s*\S+", re.MULTILINE)

DOC_GLOBS = (
    "README.md", "README.en.md", "CHANGELOG.md", "CONTRIBUTING.md", "SECURITY.md",
    "THIRD_PARTY_NOTICES.md", "AGENTS.md", "AGENTS.zh-CN.md",
    "docs/**/*.md", "provenance/**/*.md",
)

README_MUST_LINK = (
    "VERSION", "docs/README.md", "docs/getting-started.md", "docs/installation.md",
    "docs/dependencies.md", "docs/migration-v3.md", "docs/validation-v3.md",
    "docs/reference/capabilities.md", "docs/design/v3-overrides.md",
    "provenance/README.md", "CONTRIBUTING.md", "CHANGELOG.md", "LICENSE",
    "THIRD_PARTY_NOTICES.md", "README.en.md",
)

DOCS_INDEX_MUST_LINK = (
    "installation.md", "dependencies.md", "migration-v3.md", "validation-v3.md",
    "getting-started.md", "design/v3-overrides.md", "design/unified-design-v1.md",
    "reference/capabilities.md", "reference/data-and-permissions.md",
    "reference/troubleshooting.md", "reference/upstream.md",
    "development/testing.md", "development/releasing.md",
    "usage/existing-projects.md", "usage/workflows.md",
    "agents/issue-tracker.md", "agents/triage-labels.md", "agents/domain.md",
)

# 已退出的旧安装命令，只允许出现在退役说明与历史记录中。
# 调用控制字段（frontmatter 的 disable-model-invocation 与 agents/openai.yaml）
# 已恢复为现行契约，不再属于退役内容；其正向断言由 tests/test_skills_layout.py 承担。
RETIRED_COMMANDS = (
    "claude --plugin-dir", "codex plugin add", "zcode plugin",
    "shasum -a 256 -c SHA256SUMS", ".claude-plugin/plugin.json",
    ".codex-plugin/plugin.json", ".zcode-plugin/plugin.json",
    "scripts/build-package.sh",
)
HISTORY_ALLOWED = ("docs/migration-v3.md", "CHANGELOG.md")
HISTORY_PREFIXES = ("provenance/", "docs/design/")

# 原样保留的历史输入与旧版追溯材料：不做链接与措辞检查，避免为了绿灯改写原始事实
FROZEN_PREFIXES = ("provenance/previous-audit/", "provenance/v2-plugin-provenance/",
                   "provenance/setup-gamestudio-draft-v2/")
FROZEN_FILES = ("docs/design/unified-design-v1.md", "docs/design/unified-integration-v1.md")

VERSION = "3.0.0"
VERSION_MUST_MENTION = ("README.md", "README.en.md", "CHANGELOG.md", "SECURITY.md",
                        "docs/installation.md", "docs/migration-v3.md")


def iter_docs() -> list[Path]:
    files: list[Path] = []
    for pattern in DOC_GLOBS:
        if "*" in pattern:
            files.extend(sorted(REPO.glob(pattern)))
        else:
            path = REPO / pattern
            if path.is_file():
                files.append(path)
    return files


def skill_names() -> list[str]:
    return sorted(p.name for p in SKILLS.iterdir() if p.is_dir())


def resolve(source: Path, target: str) -> Path | None:
    if target.startswith(("http://", "https://", "mailto:")) or target.startswith("#"):
        return None
    path_part = target.split("#", 1)[0]
    return source if not path_part else (source.parent / path_part).resolve()


def contains(text: str, rel: str) -> bool:
    return f"({rel})" in text or f"({rel}#" in text


def main() -> int:
    failures: list[str] = []
    docs = iter_docs()
    if not docs:
        print("FAIL: 未找到用户文档")
        return 1

    for path in docs:
        rel = path.relative_to(REPO).as_posix()
        if rel.startswith(FROZEN_PREFIXES) or rel in FROZEN_FILES:
            continue
        text = path.read_text(encoding="utf-8")
        if path.parent != REPO and FRONTMATTER.search(text):
            failures.append(f"{rel}: 文档不得带技能 frontmatter（会被安装器发现为技能）")
        for raw in LINK.findall(text):
            dest = resolve(path, raw.strip())
            if dest is None:
                continue
            try:
                dest.relative_to(REPO)
            except ValueError:
                continue
            if not dest.exists():
                failures.append(f"{rel}: 断链 {raw}")
        if rel in HISTORY_ALLOWED or rel.startswith(HISTORY_PREFIXES):
            continue
        for marker in RETIRED_COMMANDS:
            if marker in text:
                failures.append(f"{rel}: 仍出现已退出的旧命令或字段 {marker}")

    readme = (REPO / "README.md").read_text(encoding="utf-8")
    for rel in README_MUST_LINK:
        if not contains(readme, rel):
            failures.append(f"README.md 缺少导航 {rel}")
    for name in skill_names():
        if not contains(readme, f"skills/{name}/SKILL.md"):
            failures.append(f"README.md 未链接技能 skills/{name}/SKILL.md")

    index = (REPO / "docs" / "README.md").read_text(encoding="utf-8")
    for rel in DOCS_INDEX_MUST_LINK:
        if not contains(index, rel):
            failures.append(f"docs/README.md 缺少导航 {rel}")

    version_file = REPO / "VERSION"
    if not version_file.is_file():
        failures.append("缺少根目录 VERSION 文件")
    else:
        actual = version_file.read_text(encoding="utf-8").strip()
        if actual != VERSION:
            failures.append(f"VERSION 应为 {VERSION}，实际 {actual}")
        for rel in VERSION_MUST_MENTION:
            path = REPO / rel
            if path.is_file() and VERSION not in path.read_text(encoding="utf-8"):
                failures.append(f"{rel} 未提及当前版本 {VERSION}")

    for pair in (("AGENTS.md", "AGENTS.zh-CN.md"),):
        en = [l for l in (REPO / pair[0]).read_text(encoding="utf-8").splitlines()
              if l.startswith("#")]
        zh = [l for l in (REPO / pair[1]).read_text(encoding="utf-8").splitlines()
              if l.startswith("#")]
        if len(en) != len(zh):
            failures.append(
                f"{pair[0]} 有 {len(en)} 个标题，{pair[1]} 有 {len(zh)} 个，镜像结构不一致")

    if failures:
        print(f"FAIL ({len(failures)}):")
        for item in failures:
            print(f"  - {item}")
        return 1
    print(f"OK: 文档导航、链接、版本与退役命令检查通过（{len(docs)} 个文件，"
          f"{len(skill_names())} 项技能）")
    return 0


if __name__ == "__main__":
    sys.exit(main())

"""V3 文档、版本与许可契约检查。

运行：python3.12 -m pytest tests/test_docs_product.py -q

链接可达性、导航完整性与旧命令残留由 scripts/validate-docs.py 检查，本文件不重复。
"""

from __future__ import annotations

import re
import subprocess
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
SKILLS = REPO / "skills"
VERSION = "3.0.3"
UPSTREAM_COMMIT = "c55ee46073ed923f86ce59a5eb3b6d895095d1b7"

# 允许提到旧版本号的位置：变更历史、迁移说明与来源追溯
OLD_VERSION_ALLOWED = (
    "CHANGELOG.md", "docs/migration-v3.md", "docs/reference/upstream.md",
    "docs/development/releasing.md", "docs/reference/troubleshooting.md",
)
OLD_VERSION_PREFIXES = ("provenance/", "docs/design/")


def publishable_files() -> list[str]:
    out = subprocess.run(
        ["git", "ls-files", "--cached", "--others", "--exclude-standard"],
        cwd=REPO, capture_output=True, text=True, check=True,
    ).stdout.splitlines()
    return [line for line in out if line.strip() and (REPO / line).is_file()]


def read(rel: str) -> str:
    return (REPO / rel).read_text(encoding="utf-8")


def test_version_file_is_the_single_authority() -> None:
    version_file = REPO / "VERSION"
    assert version_file.is_file(), "缺少根目录 VERSION"
    assert version_file.read_text(encoding="utf-8").strip() == VERSION
    # 发布内容中不存在第二个版本权威来源
    second = [rel for rel in publishable_files()
              if Path(rel).name in {"package.json", "plugin.json", "marketplace.json",
                                    "pyproject.toml", "setup.py", "setup.cfg"}]
    assert not second, f"{second} 会成为第二个版本权威来源"


def test_no_doc_claims_an_old_version_as_current() -> None:
    """旧版本号可以出现在迁移与历史说明中，但不得被当成当前版本。"""
    patterns = (
        re.compile(r"当前版本[：:]*\s*[`\"']?2\.0\."),
        re.compile(r"[Cc]urrent version[：:]*\s*[`\"']?2\.0\."),
        re.compile(r"mygamestudio[ -]2\.0\.\d+\.tar\.gz"),
        re.compile(r"版本\s*2\.0\.2\s*已发布"),
    )
    offenders = []
    for rel in publishable_files():
        if not rel.endswith((".md", ".yml", ".yaml", ".py", ".json")):
            continue
        if rel in OLD_VERSION_ALLOWED or rel.startswith(OLD_VERSION_PREFIXES):
            continue
        if rel.startswith(("provenance/", "skills/", "tests/")):
            continue
        text = read(rel)
        for pattern in patterns:
            if pattern.search(text):
                offenders.append(f"{rel}: 匹配 {pattern.pattern}")
    assert not offenders, "把旧版本当成当前版本：\n" + "\n".join(offenders)


def test_migration_references_carry_the_current_version() -> None:
    """提到旧版本的使用者文档必须同时给出当前版本，避免读者停在旧版本。"""
    for rel in ("README.md", "README.en.md", "docs/README.md", "docs/installation.md",
                "docs/migration-v3.md", "docs/reference/capabilities.md"):
        text = read(rel)
        if "2.0.2" in text:
            assert VERSION in text, f"{rel} 提到 2.0.2 但没有给出当前版本 {VERSION}"


def test_required_docs_mention_current_version() -> None:
    for rel in ("README.md", "README.en.md", "CHANGELOG.md", "SECURITY.md",
                "docs/installation.md", "docs/migration-v3.md"):
        assert VERSION in read(rel), f"{rel} 未提及当前版本 {VERSION}"


def test_root_license_and_third_party_notices() -> None:
    license_text = read("LICENSE")
    assert "MIT License" in license_text
    assert "LC-86 / MyGameStudio" in license_text

    notices = read("THIRD_PARTY_NOTICES.md")
    assert "Matt Pocock" in notices, "第三方说明应保留上游署名"
    assert UPSTREAM_COMMIT in notices, "第三方说明应记录 V3 方法基线提交"
    assert "mattpocock/skills" in notices
    assert (REPO / "provenance" / "v2-plugin-provenance" / "licenses"
            / "mattpocock-skills-LICENSE.txt").is_file(), "缺少上游 MIT 许可副本"
    upstream_license = read(
        "provenance/v2-plugin-provenance/licenses/mattpocock-skills-LICENSE.txt")
    assert "MIT License" in upstream_license and "Matt Pocock" in upstream_license


def test_readme_documents_the_full_set_and_navigation() -> None:
    readme = read("README.md")
    names = sorted(p.name for p in SKILLS.iterdir() if p.is_dir())
    assert len(names) == 20, f"可发现集合应为 20 项，实际 {len(names)}：{names}"
    missing = [n for n in names if f"skills/{n}/SKILL.md" not in readme]
    assert not missing, f"README.md 未链接技能：{missing}"
    assert "npx skills@latest add LC-86/MyGameStudio" in readme, "README 应给出原生安装命令"
    assert "指令层约定" in readme, "README 应保留 ZCode、Qoder 内指令层约定的表述"


def test_no_doc_teaches_old_plugin_install_as_current() -> None:
    """旧安装命令只能出现在迁移说明与历史记录中。"""
    banned = ("claude --plugin-dir", "codex plugin add", "shasum -a 256 -c SHA256SUMS")
    offenders = []
    for rel in publishable_files():
        if not rel.endswith(".md"):
            continue
        if rel in OLD_VERSION_ALLOWED or rel.startswith(OLD_VERSION_PREFIXES):
            continue
        text = read(rel)
        for marker in banned:
            if marker in text:
                offenders.append(f"{rel}: {marker}")
    assert not offenders, "仍在教旧安装命令：\n" + "\n".join(offenders)


def headings(text: str) -> list[str]:
    """标题行，排除代码块内的注释行。"""
    out, fenced = [], False
    for line in text.splitlines():
        if line.startswith("```"):
            fenced = not fenced
            continue
        if not fenced and line.startswith("#"):
            out.append(line)
    return out


def test_agent_rules_mirror_stays_aligned() -> None:
    """AGENTS.md 与 AGENTS.zh-CN.md 是逐节镜像，标题结构必须一致。"""
    primary = headings(read("AGENTS.md"))
    mirror = headings(read("AGENTS.zh-CN.md"))
    assert len(primary) == len(mirror), \
        f"AGENTS.md 有 {len(primary)} 个标题，AGENTS.zh-CN.md 有 {len(mirror)} 个"


def test_readme_mirror_carries_the_same_facts() -> None:
    """README.en.md 是精简镜像，不做逐句翻译，但版本事实与关键导航必须一致。"""
    en = read("README.en.md")
    zh = read("README.md")
    assert VERSION in en, "README.en.md 缺少当前版本事实"
    assert "npx skills@latest add LC-86/MyGameStudio" in en, "README.en.md 缺少原生安装命令"
    assert "instruction-layer" in en, \
        "README.en.md 应保留 instruction-layer 的指令层约定表述"
    names = sorted(p.name for p in SKILLS.iterdir() if p.is_dir())
    missing = [n for n in names if f"skills/{n}/SKILL.md" not in en]
    assert not missing, f"README.en.md 未链接技能：{missing}"
    for rel in ("docs/installation.md", "docs/dependencies.md", "docs/migration-v3.md",
                "docs/validation-v3.md", "LICENSE", "THIRD_PARTY_NOTICES.md"):
        assert f"({rel})" in zh, f"README.md 缺少导航 {rel}"


def test_migration_doc_records_baseline_and_recovery() -> None:
    migration = read("docs/migration-v3.md")
    retirement = read("provenance/v2-retirement.md")
    baseline = "5e3cfbfa3e217a9182690237955734109b982235"
    assert baseline in migration, "迁移说明应记录 V3 开始前的基线提交"
    assert baseline in retirement, "退役记录应记录基线提交"
    for entry in ("game-producer", "game-init", "game-design"):
        assert entry in migration and entry in retirement, f"{entry} 的去向未记录"
    assert "没有等价能力" in migration, "迁移说明应明确未覆盖的能力"


def test_validation_record_separates_statuses() -> None:
    validation = read("docs/validation-v3.md")
    for marker in ("未运行", "通过", "失败"):
        assert marker in validation, f"validation-v3.md 应区分 {marker} 状态"
    assert "本地安装" in validation and "远端" in validation, \
        "validation-v3.md 应分别报告本地安装与远端发布状态"


def install_steps() -> list[tuple[str, str]]:
    """完整安装小节里的 (注释, 命令) 步骤，按文档阅读顺序返回。"""
    guide = read("docs/installation.md")
    section = guide.split("## 完整安装：两步", 1)[1].split("\n## ", 1)[0]
    block = re.search(r"```bash\n(.*?)```", section, re.DOTALL)
    assert block, "完整安装小节应给出可复制的 bash 命令块"
    steps, comment = [], ""
    for line in block.group(1).splitlines():
        line = line.strip()
        if line.startswith("#"):
            comment = line.lstrip("#").strip()
        elif line:
            steps.append((comment, line))
    return steps


def test_two_source_install_guide_puts_user_scope_first() -> None:
    """Issue #89 Testing Decision 3：两来源两步、用户级在前、项目级为替代。

    命令顺序是这份指南的实际产品形态：读的人照着从上往下做，因此顺序错了
    就装错了范围，而不是文案问题。
    """
    steps = install_steps()
    assert len(steps) == 4, f"完整安装应为 4 条命令（两来源 × 两范围），实际 {len(steps)}：{steps}"
    comments = [comment for comment, _ in steps]
    assert all("用户级" in c for c in comments[:2]), f"前两条应先是用户级：{comments}"
    assert all("项目级" in c and "目标项目根目录" in c for c in comments[2:]), \
        f"后两条应是项目级替代并写明在目标项目根目录执行：{comments}"
    assert all("-g" in cmd for _, cmd in steps[:2]) and not any("-g" in c for _, c in steps[2:]), \
        "用户级命令应带 -g，项目级命令不应带 -g"
    first_comment, first_cmd = steps[0]
    assert "mattpocock/skills" in first_cmd and "--skill writing-for-agents" in first_cmd, \
        f"第一步应是官方共同方法：{first_cmd}"
    assert "跳过" in first_comment, "用户级共同方法步骤应说明已有安装时只跳过这一步"
    assert "LC-86/MyGameStudio" in steps[1][1] and "--skill '*'" in steps[1][1], \
        f"第二步应完整安装本仓库 20 项：{steps[1][1]}"
    for _, cmd in steps:
        assert cmd.startswith("npx skills@latest add"), \
            f"面向用户的命令应使用 skills@latest：{cmd}"


def test_two_source_install_guide_names_the_cli_boundary() -> None:
    """命令跟随 latest，但范围、copy 与锁行为只在 CLI 1.7.0 上核实。"""
    guide = read("docs/installation.md")
    assert "npx skills@1.7.0" not in guide, "面向用户的命令不得钉住 CLI 版本"
    assert "1.7.0" in guide, "安装说明应写明实测的 CLI 版本边界"
    assert "共同方法不是可选能力" in guide, "不得把外部共同方法写成可选能力"
    assert "mattpocockskills" not in guide, "官方来源只能是 mattpocock/skills"

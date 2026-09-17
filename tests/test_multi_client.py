#!/usr/bin/env python3
"""Issue #75: 多客户端(ZCode / Grok Build)适配回归；后续补 Claude Code。

- 清单版本一致性:`.zcode-plugin/plugin.json`、`.claude-plugin/plugin.json`
  与 `.codex-plugin/plugin.json` 的 name/version 必须同步,防止升版时只改
  一份造成漂移;ZCode 清单使用旧 1.0.0 实证 schema(name/version/description/
  author/license/skills),Claude Code 清单按官方 `.claude-plugin/plugin.json`
  约定(name 必填,skills 默认 `./skills/`),2.0 无 MCP,不得注册 mcpServers。
- 三个游戏入口的技能定位口径必须客户端无关:给出「上下文给定位置 →
  Codex $CODEX_HOME → ZCode 插件缓存 → Grok ~/.grok/plugins →
  Claude Code ~/.claude/plugins」回退链,不得只锚定 $CODEX_HOME。
- 「真实 Codex」不再作为唯一客户端措辞;未执行项改为 install-real-client。
- README 写明 ZCode、Grok Build 与 Claude Code 各自的安装步骤与隔离目录
  验证方法,以及「复制一行即可安装」/「复制一段指令发给 Agent」。

    python3 -B tests/test_multi_client.py
"""

import json
import re

from plugin_package_support import REPO_ROOT, PLUGIN_ROOT, make_checker, run_theme

FAILURES, check = make_checker()

GAME_ENTRIES = ("game-producer", "game-init", "game-design")
ANCHOR_SENTENCE = "若当前上下文没有给出技能安装位置"
CLIENT_FALLBACK_MARKERS = (
    ("Codex", "$CODEX_HOME"),
    ("ZCode", ".zcode/cli/plugins/cache"),
    ("Grok", ".grok/plugins"),
    ("Claude Code", ".claude/plugins"),
)
REAL_CLIENT_FILES = (
    "internal/game/stage-requirements.md",
    "skills/game-init/SKILL.md",
    "provenance/manifest.md",
)


def _load_json(rel: str) -> dict:
    path = PLUGIN_ROOT / rel
    check(path.is_file(), f"缺少 {rel}")
    if not path.is_file():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def test_zcode_manifest_matches_codex_version() -> None:
    """双清单 name/version 必须一致;ZCode 清单用旧 1.0.0 实证 schema。"""

    codex_path = PLUGIN_ROOT / ".codex-plugin" / "plugin.json"
    zcode_path = PLUGIN_ROOT / ".zcode-plugin" / "plugin.json"
    check(codex_path.is_file(), "缺少 .codex-plugin/plugin.json")
    check(zcode_path.is_file(), "缺少 .zcode-plugin/plugin.json(多客户端适配)")
    if not (codex_path.is_file() and zcode_path.is_file()):
        return
    codex = json.loads(codex_path.read_text(encoding="utf-8"))
    zcode = json.loads(zcode_path.read_text(encoding="utf-8"))
    check(zcode.get("name") == codex.get("name") == "mygamestudio",
          f"双清单 name 必须同为 mygamestudio,实际 codex={codex.get('name')}"
          f" zcode={zcode.get('name')}")
    version = codex.get("version", "")
    check(re.fullmatch(r"\d+\.\d+\.\d+", version) is not None,
          f"Codex 清单 version 必须是严格 semver,实际 {version}")
    check(zcode.get("version") == version,
          f"ZCode 清单 version {zcode.get('version')} 必须与 Codex 清单 "
          f"{version} 一致(防漂移)")
    for field in ("description", "author", "license", "skills"):
        check(bool(zcode.get(field)), f"ZCode 清单缺少 {field}")
    check(bool(zcode.get("author", {}).get("name")), "ZCode 清单缺少 author.name")
    check(zcode.get("license") == "MIT", "ZCode 清单 license 必须是 MIT")
    skills = str(zcode.get("skills", "")).strip("./")
    check((PLUGIN_ROOT / skills / "game-producer" / "SKILL.md").is_file(),
          f"ZCode 清单 skills 字段应解析到包内技能目录,实际 {skills!r}")
    check("mcpServers" not in zcode, "2.0 无 MCP,ZCode 清单不得注册 mcpServers")


def test_claude_manifest_matches_codex_version() -> None:
    """Claude Code 清单 name/version 必须与 Codex/ZCode 一致,且不注册 MCP。"""

    codex = _load_json(".codex-plugin/plugin.json")
    zcode = _load_json(".zcode-plugin/plugin.json")
    claude_path = PLUGIN_ROOT / ".claude-plugin" / "plugin.json"
    check(claude_path.is_file(), "缺少 .claude-plugin/plugin.json(Claude Code 适配)")
    if not claude_path.is_file() or not codex:
        return
    claude = json.loads(claude_path.read_text(encoding="utf-8"))
    check(claude.get("name") == codex.get("name") == "mygamestudio",
          f"Claude Code 清单 name 必须同为 mygamestudio,实际 {claude.get('name')}")
    check(claude.get("version") == codex.get("version"),
          f"Claude Code 清单 version {claude.get('version')} 必须与 Codex 清单 "
          f"{codex.get('version')} 一致(防漂移)")
    if zcode:
        check(claude.get("version") == zcode.get("version"),
              "Claude Code 清单 version 必须与 ZCode 清单一致")
    for field in ("description", "author", "license", "skills"):
        check(bool(claude.get(field)), f"Claude Code 清单缺少 {field}")
    check(bool(claude.get("author", {}).get("name")),
          "Claude Code 清单缺少 author.name")
    check(claude.get("license") == "MIT", "Claude Code 清单 license 必须是 MIT")
    skills = str(claude.get("skills", "")).strip("./")
    check((PLUGIN_ROOT / skills / "game-producer" / "SKILL.md").is_file(),
          f"Claude Code 清单 skills 字段应解析到包内技能目录,实际 {skills!r}")
    check("mcpServers" not in claude,
          "2.0 无 MCP,Claude Code 清单不得注册 mcpServers")
    check(not (PLUGIN_ROOT / ".mcp.json").is_file(),
          "插件根不得因 Claude Code 适配新增 .mcp.json")


def test_game_entry_location_is_client_agnostic() -> None:
    """三个游戏入口的兜底定位不得只锚定 $CODEX_HOME。"""

    for name in GAME_ENTRIES:
        skill_md = PLUGIN_ROOT / "skills" / name / "SKILL.md"
        check(skill_md.is_file(), f"缺少 skills/{name}/SKILL.md")
        if not skill_md.is_file():
            continue
        text = skill_md.read_text(encoding="utf-8")
        check(ANCHOR_SENTENCE in text,
              f"{name} 应保留技能兜底定位句(上下文未给出安装位置时)")
        for client, marker in CLIENT_FALLBACK_MARKERS:
            check(marker in text,
                  f"{name} 技能兜底定位应覆盖 {client} 回退({marker})")
        check("claude --plugin-dir" in text,
              f"{name} 技能兜底定位应覆盖 Claude Code --plugin-dir")


def test_real_client_wording_replaces_codex_only() -> None:
    """「真实 Codex」措辞与 install-real-codex 未执行项改为真实客户端口径。"""

    for rel in REAL_CLIENT_FILES:
        path = PLUGIN_ROOT / rel
        check(path.is_file(), f"缺少 {rel}")
        if not path.is_file():
            continue
        text = path.read_text(encoding="utf-8")
        check("真实 Codex" not in text,
              f"{rel} 不得再把「真实 Codex」当作唯一客户端措辞")
    stage_text = (PLUGIN_ROOT / REAL_CLIENT_FILES[0]).read_text(encoding="utf-8")
    check("真实客户端" in stage_text,
          "stage-requirements.md 应改用「真实客户端」口径")
    release_check = (PLUGIN_ROOT / "provenance" / "mgs_release_check.py").read_text(
        encoding="utf-8")
    check("install-real-codex" not in release_check,
          "mgs_release_check.py 不得再登记 install-real-codex 未执行项")
    check("install-real-client" in release_check,
          "mgs_release_check.py 应登记 install-real-client 未执行项")


def test_readme_documents_both_client_installs() -> None:
    """README 应能导航到 ZCode / Grok / Claude Code 安装页；安装页含完整步骤与隔离验证。

    安装正文从首页迁到 docs/installation/ 后，不得靠删除本检查过关：
    首页负责导航，专页负责可执行细节。
    """

    readme_path = REPO_ROOT / "README.md"
    check(readme_path.is_file(), "缺少 README.md")
    if not readme_path.is_file():
        return
    text = readme_path.read_text(encoding="utf-8")
    check("docs/installation/zcode.md" in text,
          "README 应导航到 docs/installation/zcode.md")
    check("docs/installation/grok-build.md" in text,
          "README 应导航到 docs/installation/grok-build.md")
    check("docs/installation/codex.md" in text,
          "README 应导航到 docs/installation/codex.md")
    check("docs/installation/claude-code.md" in text,
          "README 应导航到 docs/installation/claude-code.md")
    check(".zcode-plugin/plugin.json" in text,
          "README 应提及 ZCode 清单 .zcode-plugin/plugin.json")
    check(".claude-plugin/plugin.json" in text,
          "README 应提及 Claude Code 清单 .claude-plugin/plugin.json")
    check(".grok/plugins" in text,
          "README 应写明 Grok Build 插件目录 ~/.grok/plugins")
    check("--plugin-dir" in text,
          "README 应写明 Grok Build --plugin-dir 安装方式")
    check("claude --plugin-dir" in text,
          "README 应写明 Claude Code claude --plugin-dir 一行命令")
    check("marketplace.json" in text,
          "README 应写明 ZCode 本地插件源 marketplace.json 布局")
    check("隔离" in text,
          "README 应写明隔离目录验证(不安装到真实用户目录)")
    check("复制一行即可安装" in text,
          "README 应提供「复制一行即可安装」")
    check("复制一段指令发给 Agent" in text,
          "README 应提供「复制一段指令发给 Agent 来安装」")
    check("npx skills" in text,
          "README 应明确不要把 npx skills add 写成受支持路径")
    zcode = (REPO_ROOT / "docs" / "installation" / "zcode.md")
    grok = (REPO_ROOT / "docs" / "installation" / "grok-build.md")
    claude = (REPO_ROOT / "docs" / "installation" / "claude-code.md")
    check(zcode.is_file(), "缺少 docs/installation/zcode.md")
    check(grok.is_file(), "缺少 docs/installation/grok-build.md")
    check(claude.is_file(), "缺少 docs/installation/claude-code.md")
    if zcode.is_file():
        ztext = zcode.read_text(encoding="utf-8")
        check(".zcode-plugin/plugin.json" in ztext,
              "ZCode 安装页应包含 .zcode-plugin/plugin.json")
        check("marketplace.json" in ztext,
              "ZCode 安装页应包含 marketplace.json")
        check("隔离" in ztext, "ZCode 安装页应包含隔离验证")
        check("未验证" in ztext, "ZCode 安装页应标明真实安装未验证")
        check("zcode plugins install" in ztext and "不要编造" in ztext,
              "ZCode 安装页不得把未核实的 zcode plugins install 写成受支持路径")
    if grok.is_file():
        gtext = grok.read_text(encoding="utf-8")
        check(".grok/plugins" in gtext, "Grok 安装页应包含 ~/.grok/plugins")
        check("--plugin-dir" in gtext, "Grok 安装页应包含 --plugin-dir")
        check("隔离" in gtext, "Grok 安装页应包含隔离验证")
        check("grok plugin install" in gtext,
              "Grok 安装页应给出官方 grok plugin install 一行命令")
    if claude.is_file():
        ctext = claude.read_text(encoding="utf-8")
        check(".claude-plugin/plugin.json" in ctext,
              "Claude Code 安装页应包含 .claude-plugin/plugin.json")
        check("claude --plugin-dir" in ctext,
              "Claude Code 安装页应包含 claude --plugin-dir")
        check("~/.claude/plugins" in ctext,
              "Claude Code 安装页应写明官方 ~/.claude/plugins 缓存目录")
        check("隔离" in ctext, "Claude Code 安装页应包含隔离验证")
        check("未验证" in ctext, "Claude Code 安装页应标明真实安装未验证")
        check("mcpServers" in ctext and "不注册" in ctext,
              "Claude Code 安装页应写明不注册 MCP")


TESTS = (
    test_zcode_manifest_matches_codex_version,
    test_claude_manifest_matches_codex_version,
    test_game_entry_location_is_client_agnostic,
    test_real_client_wording_replaces_codex_only,
    test_readme_documents_both_client_installs,
)


def main() -> int:
    return run_theme("多客户端适配(ZCode/Grok Build/Claude Code)", TESTS, FAILURES)


if __name__ == "__main__":
    raise SystemExit(main())

#!/usr/bin/env python3
"""开源产品化文档、许可与安装导航回归。

不删除既有多客户端检查：README 必须能导航到安装页，安装页包含完整标记。

    python3 -B tests/test_docs_product.py
"""

from __future__ import annotations

import json
import shutil
import subprocess
import sys
import tarfile
import tempfile
from pathlib import Path

from plugin_package_support import PLUGIN_ROOT, REPO_ROOT, make_checker, run_theme, sha256
from redesign_bundle_contract import PUBLIC_SKILLS

FAILURES, check = make_checker()


def test_root_license_and_notices() -> None:
    license_path = REPO_ROOT / "LICENSE"
    notices = REPO_ROOT / "THIRD_PARTY_NOTICES.md"
    check(license_path.is_file(), "缺少根目录 LICENSE")
    check(notices.is_file(), "缺少根目录 THIRD_PARTY_NOTICES.md")
    if license_path.is_file():
        text = license_path.read_text(encoding="utf-8")
        check("MIT License" in text, "LICENSE 应为 MIT")
        check("LC-86" in text or "MyGameStudio" in text,
              "LICENSE 应标明本项目版权归属")
        check("Matt Pocock" not in text,
              "根目录 LICENSE 不得替换上游 Matt 版权")
    if notices.is_file():
        text = notices.read_text(encoding="utf-8")
        check("mattpocock/skills" in text, "第三方说明应记录上游项目")
        check("1.2.3" in text, "第三方说明应记录固定上游版本")
        check("3cca18b368ae95cdbdebbff572ccafa662551015" in text,
              "第三方说明应记录固定上游提交")
        check("LC-86" in text, "第三方说明应写明组合包维护者")
        check("官方背书" in text, "第三方说明不得暗示官方背书")


def test_readme_navigates_to_install_pages() -> None:
    readme = (REPO_ROOT / "README.md").read_text(encoding="utf-8")
    check("docs/installation/zcode.md" in readme,
          "README 应导航到 ZCode 安装页")
    check("docs/installation/grok-build.md" in readme,
          "README 应导航到 Grok Build 安装页")
    check("docs/installation/codex.md" in readme,
          "README 应导航到 Codex 安装页")
    check("docs/installation/claude-code.md" in readme,
          "README 应导航到 Claude Code 安装页")
    check("隔离" in readme, "README 应保留隔离验证口径")
    check("未验证" in readme, "README 应区分发布状态与安装验证状态")
    check("复制一行即可安装" in readme, "README 应提供复制一行安装")
    check("复制一段指令发给 Agent" in readme, "README 应提供发给 Agent 的安装提示词")
    check("claude --plugin-dir" in readme, "README 应给出 Claude Code 官方一行命令")


def test_install_pages_keep_client_markers() -> None:
    zcode = (REPO_ROOT / "docs" / "installation" / "zcode.md").read_text(
        encoding="utf-8")
    grok = (REPO_ROOT / "docs" / "installation" / "grok-build.md").read_text(
        encoding="utf-8")
    codex = (REPO_ROOT / "docs" / "installation" / "codex.md").read_text(
        encoding="utf-8")
    check(".zcode-plugin/plugin.json" in zcode,
          "ZCode 安装页应提及 .zcode-plugin/plugin.json")
    check("marketplace.json" in zcode,
          "ZCode 安装页应写明 marketplace.json 布局")
    check("隔离" in zcode, "ZCode 安装页应写明隔离目录验证")
    check(".grok/plugins" in grok,
          "Grok 安装页应写明 ~/.grok/plugins")
    check("--plugin-dir" in grok,
          "Grok 安装页应写明 --plugin-dir")
    check("隔离" in grok, "Grok 安装页应写明隔离目录验证")
    check("codex plugin add" in codex, "Codex 安装页应给出曾实测的 plugin add 命令")
    check("未验证" in zcode and "未验证" in grok and "未验证" in codex,
          "各安装页须标明真实客户端安装尚未验证")
    claude = (REPO_ROOT / "docs" / "installation" / "claude-code.md").read_text(
        encoding="utf-8")
    check(".claude-plugin/plugin.json" in claude,
          "Claude Code 安装页应提及 .claude-plugin/plugin.json")
    check("claude --plugin-dir" in claude,
          "Claude Code 安装页应给出官方 claude --plugin-dir")
    check("隔离" in claude, "Claude Code 安装页应写明隔离目录验证")
    check("未验证" in claude, "Claude Code 安装页须标明真实安装尚未验证")
    install_index = (REPO_ROOT / "docs" / "installation" / "README.md").read_text(
        encoding="utf-8")
    check("复制一行即可安装" in install_index,
          "安装总述应提供复制一行安装")
    check("复制一段指令发给 Agent" in install_index,
          "安装总述应提供发给 Agent 的安装提示词")
    check("npx skills" in install_index,
          "安装总述应明确 npx skills add 不是受支持路径")


def test_skill_index_lists_public_collection() -> None:
    text = (REPO_ROOT / "docs" / "skills" / "README.md").read_text(
        encoding="utf-8")
    missing = [name for name in PUBLIC_SKILLS if name not in text]
    check(not missing, f"技能总目录缺少公开技能: {missing}")
    check(len(PUBLIC_SKILLS) == 28, "当前公开集合应为 28 项（对照清单，而非写死未来版本）")


def test_validate_docs_script_passes() -> None:
    script = REPO_ROOT / "scripts" / "validate-docs.py"
    check(script.is_file(), "缺少 scripts/validate-docs.py")
    if not script.is_file():
        return
    result = subprocess.run(
        [sys.executable, str(script)], cwd=REPO_ROOT,
        capture_output=True, text=True)
    check(result.returncode == 0,
          "validate-docs.py 失败:\n"
          f"{(result.stdout or '') + (result.stderr or '')}")


def test_next_package_builder_bundles_root_licenses() -> None:
    """下一版本构建脚本把根目录许可带入包内；不覆盖现行 2.0.1 产物。"""

    builder = REPO_ROOT / "scripts" / "build-package.sh"
    check(builder.is_file(), "缺少 scripts/build-package.sh")
    if not builder.is_file():
        return
    license_path = REPO_ROOT / "LICENSE"
    notices = REPO_ROOT / "THIRD_PARTY_NOTICES.md"
    if not license_path.is_file() or not notices.is_file():
        return
    with tempfile.TemporaryDirectory(prefix="mgs-next-pkg-") as tmp:
        root = Path(tmp)
        shutil.copytree(PLUGIN_ROOT, root / "plugin",
                        ignore=shutil.ignore_patterns("__pycache__", ".DS_Store"))
        shutil.copy2(license_path, root / "LICENSE")
        shutil.copy2(notices, root / "THIRD_PARTY_NOTICES.md")
        (root / "scripts").mkdir()
        shutil.copy2(builder, root / "scripts" / "build-package.sh")
        (root / "scripts" / "build-package.sh").chmod(0o755)
        result = subprocess.run(
            ["bash", str(root / "scripts" / "build-package.sh")],
            cwd=root, capture_output=True, text=True)
        check(result.returncode == 0,
              f"下一版本构建失败:{result.stderr.strip()[:400] or result.stdout[:400]}")
        version = json.loads(
            (root / "plugin" / ".codex-plugin" / "plugin.json").read_text(
                encoding="utf-8"))["version"]
        tarball = root / "dist" / f"mygamestudio-{version}.tar.gz"
        manifest = root / "dist" / "package-manifest.txt"
        check(tarball.is_file(), "下一版本构建未产出安装包")
        check(manifest.is_file(), "下一版本构建未产出清单")
        if not tarball.is_file() or not manifest.is_file():
            return
        listed = {
            line.split(None, 1)[1].strip()
            for line in manifest.read_text(encoding="utf-8").splitlines()
            if line.strip()
        }
        check("LICENSE" in listed, "下一版本清单应包含 LICENSE")
        check("THIRD_PARTY_NOTICES.md" in listed,
              "下一版本清单应包含 THIRD_PARTY_NOTICES.md")
        with tarfile.open(tarball, "r:gz") as tar:
            names = [member.name for member in tar.getmembers() if member.isfile()]
            packed_license = tar.extractfile("plugin/LICENSE")
            packed_notices = tar.extractfile("plugin/THIRD_PARTY_NOTICES.md")
            license_bytes = packed_license.read() if packed_license else b""
            notices_bytes = packed_notices.read() if packed_notices else b""
        check("plugin/LICENSE" in names, "安装包应携带 plugin/LICENSE")
        check("plugin/THIRD_PARTY_NOTICES.md" in names,
              "安装包应携带 plugin/THIRD_PARTY_NOTICES.md")
        check(license_bytes == license_path.read_bytes(),
              "包内 LICENSE 必须与仓库根目录 LICENSE 字节一致")
        check(notices_bytes == notices.read_bytes(),
              "包内 THIRD_PARTY_NOTICES.md 必须与仓库根目录文件字节一致")
        live = REPO_ROOT / "dist" / "mygamestudio-2.0.1.tar.gz"
        check(live.is_file(), "构建下一版本夹具时不得删除现行 2.0.1 安装包")


def test_current_201_tarball_unchanged_by_live_next_builder() -> None:
    """仓库内现行 2.0.1 包仍是 plugin/ 源码集合，不含根目录许可副本。"""

    tarball = REPO_ROOT / "dist" / "mygamestudio-2.0.1.tar.gz"
    check(tarball.is_file(), "缺少现行 2.0.1 安装包")
    if not tarball.is_file():
        return
    with tarfile.open(tarball, "r:gz") as tar:
        names = [member.name for member in tar.getmembers() if member.isfile()]
    check("plugin/LICENSE" not in names,
          "2.0.1 已发布包不应在本整理中被改写成含根目录 LICENSE 的新字节")
    check(any(name.endswith("mattpocock-skills-LICENSE.txt") for name in names),
          "2.0.1 包内仍应携带上游 MIT 副本")


TESTS = (
    test_root_license_and_notices,
    test_readme_navigates_to_install_pages,
    test_install_pages_keep_client_markers,
    test_skill_index_lists_public_collection,
    test_validate_docs_script_passes,
    test_next_package_builder_bundles_root_licenses,
    test_current_201_tarball_unchanged_by_live_next_builder,
)


def main() -> int:
    return run_theme("开源产品化文档与许可", TESTS, FAILURES)


if __name__ == "__main__":
    raise SystemExit(main())

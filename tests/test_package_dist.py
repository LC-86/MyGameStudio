#!/usr/bin/env python3
"""dist 交付物与源包三方一致,以及同源隔离重建逐字节可复现。

任务票 10 从 tests/test_plugin_package.py 按真实行为主题拆出;检查含义与原
案例保持一致,仅重组位置。原总入口仍聚合本主题。各主题文件可直接运行:

    python3 -B tests/test_package_dist.py
"""

from pathlib import Path
import json
import sys
from plugin_package_support import (
    BUNDLED_ROOT_LICENSE_FILES,
    PLUGIN_ROOT,
    REPO_ROOT,
    bundled_license_source,
    make_checker,
    run_theme,
    sha256,
)

FAILURES, check = make_checker()

def test_dist_package_consistent() -> None:
    """任务票 18(AC6):dist/ 交付物与 plugin/ 源包一致且校验和可复算。"""

    import tarfile

    dist = REPO_ROOT / "dist"
    if not dist.is_dir():
        check(False, "缺少 dist/ 交付目录")
        return
    manifest = json.loads((PLUGIN_ROOT / ".codex-plugin" / "plugin.json").read_text())
    tarball = dist / f"mygamestudio-{manifest['version']}.tar.gz"
    check(tarball.is_file(), f"缺少安装包 {tarball.name}")
    sums = dist / "SHA256SUMS.txt"
    check(sums.is_file(), "缺少 dist/SHA256SUMS.txt")
    if sums.is_file():
        listed = set()
        for line in sums.read_text().splitlines():
            parts = line.split(None, 1)
            if len(parts) != 2:
                check(False, f"SHA256SUMS.txt 行格式异常:{line}")
                continue
            digest, name = parts[0], parts[1].strip().lstrip("*")
            target = dist / name
            check(target.is_file(), f"SHA256SUMS.txt 引用的文件不存在:{name}")
            if target.is_file():
                check(sha256(target) == digest, f"{name} 与 SHA256SUMS.txt 记录的校验和不符")
            listed.add(name)
        check(str(tarball.name) in listed, "SHA256SUMS.txt 应覆盖安装包本体")
        check("package-manifest.txt" in listed, "SHA256SUMS.txt 应覆盖逐文件清单")
    pkg_manifest = dist / "package-manifest.txt"
    check(pkg_manifest.is_file(), "缺少 dist/package-manifest.txt")
    if pkg_manifest.is_file():
        entries = {}
        for line in pkg_manifest.read_text().splitlines():
            parts = line.split(None, 1)
            if len(parts) != 2:
                continue
            entries[parts[1].strip().lstrip("*")] = parts[0].strip()
        plugin_files = sorted(
            str(p.relative_to(PLUGIN_ROOT))
            for p in PLUGIN_ROOT.rglob("*") if p.is_file() and "__pycache__" not in p.parts
        )
        extra = set(entries) - set(plugin_files)
        missing = set(plugin_files) - set(entries)
        check(not missing and extra <= BUNDLED_ROOT_LICENSE_FILES,
              "package-manifest.txt 应覆盖 plugin/ 全部文件,仅允许根目录许可随包:"
              f"\n  仅在清单:{sorted(extra)}"
              f"\n  仅在目录:{sorted(missing)}")
        for name in BUNDLED_ROOT_LICENSE_FILES:
            check(name in entries, f"2.0.2 起 package-manifest.txt 应包含 {name}")
        for rel, digest in entries.items():
            source = bundled_license_source(rel)
            check(source.is_file() and sha256(source) == digest,
                  f"package-manifest.txt 中 {rel} 的指纹与源文件不符")
    if tarball.is_file():
        with tarfile.open(tarball, "r:gz") as tar:
            names = [m.name[len("plugin/"):] for m in tar.getmembers()
                     if m.name.startswith("plugin/") and m.isfile()]
        plugin_files = sorted(
            str(p.relative_to(PLUGIN_ROOT))
            for p in PLUGIN_ROOT.rglob("*") if p.is_file() and "__pycache__" not in p.parts
        )
        extra_names = set(names) - set(plugin_files)
        missing_names = set(plugin_files) - set(names)
        check(not missing_names and extra_names <= BUNDLED_ROOT_LICENSE_FILES,
              "安装包应覆盖 plugin/ 全部文件,并携带根目录许可副本")
        check("LICENSE" in names and "THIRD_PARTY_NOTICES.md" in names,
              "2.0.2 安装包应携带 plugin/LICENSE 与 plugin/THIRD_PARTY_NOTICES.md")
def test_dist_rebuild_byte_reproducible() -> None:
    """审查修复票 03(R5):同源隔离重建逐字节一致,且 tar 不携带平台扩展元数据。

    反例背景:构建脚本曾仅靠 COPYFILE_DISABLE,macOS tar 仍会把
    com.apple.provenance 等扩展属性写入 PAX 头——文件内容完全一致的同源
    重建包字节不同(审查报告 R5)。本检查以「两份新副本隔离重建」固化
    验证,不再以同目录重复构建充当;user.* 扩展属性注入依赖 macOS
    xattr 语义(本包声明的目标宿主)。
    """

    import shutil
    import subprocess
    import tarfile
    import tempfile

    build = REPO_ROOT / "scripts" / "build-package.sh"
    license_src = REPO_ROOT / "LICENSE"
    notices_src = REPO_ROOT / "THIRD_PARTY_NOTICES.md"
    if not build.is_file():
        check(False, "缺少 scripts/build-package.sh")
        return
    if not license_src.is_file() or not notices_src.is_file():
        check(False, "缺少根目录 LICENSE 或 THIRD_PARTY_NOTICES.md")
        return
    version = json.loads(
        (PLUGIN_ROOT / ".codex-plugin" / "plugin.json").read_text())["version"]
    tarball_name = f"mygamestudio-{version}.tar.gz"

    def pax_leak(path: Path) -> dict:
        leaked = {}
        with tarfile.open(path, "r:gz") as tar:
            for member in tar.getmembers():
                if member.pax_headers:
                    leaked[member.name] = dict(member.pax_headers)
        return leaked

    with tempfile.TemporaryDirectory(prefix="mgs-repro-") as tmp:
        hashes = []
        for tag, inject_xattr in (("copy-a", False), ("copy-b", True)):
            root = Path(tmp) / tag
            (root / "dist").mkdir(parents=True)
            (root / "scripts").mkdir(parents=True)
            shutil.copytree(PLUGIN_ROOT, root / "plugin",
                            ignore=shutil.ignore_patterns("__pycache__", ".DS_Store"))
            shutil.copy2(build, root / "scripts" / "build-package.sh")
            shutil.copy2(license_src, root / "LICENSE")
            shutil.copy2(notices_src, root / "THIRD_PARTY_NOTICES.md")
            (root / "scripts" / "build-package.sh").chmod(0o755)
            if inject_xattr:
                xattr_bin = shutil.which("xattr")
                if xattr_bin is None:
                    # macOS 发版宿主才有 xattr 语义。Linux 仍做两次重建比对，
                    # 扩展属性排除在本环境记为未验证，而不是删掉重建检查。
                    pass
                else:
                    for rel in (".codex-plugin/plugin.json", "skills/game-init/SKILL.md"):
                        target = root / "plugin" / rel
                        check(target.is_file(), f"xattr 注入目标不存在:{rel}")
                        if target.is_file():
                            inject = subprocess.run(
                                [xattr_bin, "-w", "user.mgs_r5_probe", "copy-b", str(target)],
                                capture_output=True, text=True)
                            check(inject.returncode == 0,
                                  f"xattr 注入失败({rel}):{inject.stderr.strip()[:200]}")
            result = subprocess.run(
                ["./scripts/build-package.sh"], cwd=root,
                stdout=subprocess.DEVNULL, stderr=subprocess.PIPE, text=True)
            check(result.returncode == 0,
                  f"隔离副本 {tag} 构建失败:{result.stderr.strip()[:300]}")
            rebuilt = root / "dist" / tarball_name
            if result.returncode == 0 and rebuilt.is_file():
                hashes.append(sha256(rebuilt))
                leaked = pax_leak(rebuilt)
                check(not leaked,
                      f"隔离副本 {tag} 重建包不应携带任何 PAX 扩展头"
                      f"(平台扩展元数据等未归一化字段):{list(leaked)[:3]}")
        check(len(hashes) == 2 and hashes[0] == hashes[1],
              "两份隔离副本同源重建的安装包应逐字节一致:"
              f"{hashes[0] if hashes else '<构建失败>'} vs "
              f"{hashes[1] if len(hashes) > 1 else '<构建失败>'}")
    delivered = REPO_ROOT / "dist" / tarball_name
    if delivered.is_file():
        leaked = pax_leak(delivered)
        check(not leaked,
              f"交付包不应携带任何 PAX 扩展头(平台扩展元数据等未归一化字段):"
              f"{list(leaked)[:3]}")


TESTS = (
    test_dist_package_consistent,
    test_dist_rebuild_byte_reproducible,

)


def main() -> int:
    return run_theme("交付物一致性与可复现构建", TESTS, FAILURES)


if __name__ == "__main__":
    sys.exit(main())

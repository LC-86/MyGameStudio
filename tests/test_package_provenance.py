#!/usr/bin/env python3
"""内部与模板材料的来源、许可、指纹追溯,以及版本一致与开发机路径检查。

任务票 10 从 tests/test_plugin_package.py 按真实行为主题拆出;检查含义与原
案例保持一致,仅重组位置。原总入口仍聚合本主题。各主题文件可直接运行:

    python3 -B tests/test_package_provenance.py
"""

import json
import re
import sys
from plugin_package_support import (PLUGIN_ROOT, make_checker, run_theme, sha256)

FAILURES, check = make_checker()

def load_fingerprints() -> dict:
    path = PLUGIN_ROOT / "provenance" / "fingerprints.json"
    if not path.is_file():
        check(False, "缺少 provenance/fingerprints.json")
        return {}
    data = json.loads(path.read_text())
    return {entry["path"]: entry for entry in data["files"]}
def test_internal_material_provenance() -> None:
    """internal/ 与 templates/ 的适配材料必须与 fingerprints.json 一一对应。"""

    fingerprints = load_fingerprints()
    tracked_roots = (
        PLUGIN_ROOT / "internal",
        PLUGIN_ROOT / "templates",
        PLUGIN_ROOT / "skills",
    )
    adapted_files = sorted(
        str(path.relative_to(PLUGIN_ROOT))
        for root in tracked_roots
        for path in root.rglob("*")
        if path.is_file() and "__pycache__" not in path.parts and path.name != ".DS_Store"
    )
    check(
        set(adapted_files) == set(fingerprints),
        "internal/ + templates/ + skills/ 的文件与 provenance/fingerprints.json 记录不一致:"
        f"\n  仅在目录中: {sorted(set(adapted_files) - set(fingerprints))}"
        f"\n  仅在记录中: {sorted(set(fingerprints) - set(adapted_files))}",
    )
    for rel_path in adapted_files:
        entry = fingerprints.get(rel_path)
        if entry is None:
            continue  # 集合差异已由上一条 check 记录
        actual = sha256(PLUGIN_ROOT / rel_path)
        check(
            actual == entry["sha256"],
            f"{rel_path} 的实际指纹与 provenance 记录不一致",
        )
        check(bool(entry.get("source")), f"{rel_path} 缺少来源记录")
        check(bool(entry.get("license")), f"{rel_path} 缺少许可记录")
    license_file = PLUGIN_ROOT / "provenance" / "licenses" / "mattpocock-skills-LICENSE.txt"
    check(license_file.is_file(), "缺少 mattpocock/skills MIT 许可文本副本")
    if license_file.is_file():
        text = license_file.read_text()
        check("MIT License" in text and "Matt Pocock" in text, "MIT 许可副本内容不完整")
    manifest_md = PLUGIN_ROOT / "provenance" / "manifest.md"
    check(manifest_md.is_file(), "缺少 provenance/manifest.md")
def test_no_dev_machine_paths() -> None:
    offenders = []
    for path in PLUGIN_ROOT.rglob("*"):
        if not path.is_file():
            continue
        if "licenses" in path.parts or "__pycache__" in path.parts:
            continue
        if path.suffix in {".pyc", ".pyo"}:
            continue
        text = path.read_text(errors="replace")
        if "/Users/" in text:
            offenders.append(str(path.relative_to(PLUGIN_ROOT)))
    check(not offenders, f"包内文件引用了开发机绝对路径: {offenders}")
def test_provenance_version_consistency() -> None:
    """任务票 18:包版本、provenance 标题与 fingerprints 的 generated_for 三处一致。

    0.17.0 曾留下 generated_for=0.16.0 的陈旧值(本票发现并修复);本测试防止再次漂移。
    """

    manifest = json.loads((PLUGIN_ROOT / ".codex-plugin" / "plugin.json").read_text())
    version = manifest.get("version", "")
    head = (PLUGIN_ROOT / "provenance" / "manifest.md").read_text().splitlines()[0]
    match = re.search(r"mygamestudio (\d+\.\d+\.\d+)", head)
    check(match is not None, f"provenance/manifest.md 标题应含版本号,实际:{head}")
    if match:
        check(match.group(1) == version,
              f"manifest.md 标题版本 {match.group(1)} 与 plugin.json {version} 不一致")
    fingerprints = json.loads((PLUGIN_ROOT / "provenance" / "fingerprints.json").read_text())
    check(fingerprints.get("generated_for") == f"mygamestudio {version}",
          f"fingerprints.json generated_for 应为 mygamestudio {version},"
          f"实际 {fingerprints.get('generated_for')}")


TESTS = (
    test_internal_material_provenance,
    test_no_dev_machine_paths,
    test_provenance_version_consistency,

)


def main() -> int:
    return run_theme("来源/许可/指纹", TESTS, FAILURES)


if __name__ == "__main__":
    sys.exit(main())

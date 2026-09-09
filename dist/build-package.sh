#!/bin/bash
# 任务票 18:构建可审阅的安装包与逐文件清单。
#
# 用法:./dist/build-package.sh   (在仓库根执行;重复执行产出一致的内容)
#
# 产物(全部落 dist/):
#   mygamestudio-<版本>.tar.gz   安装包(plugin/ 全量,归一化 mtime/uid/gid,内容可复现)
#   package-manifest.txt         包内逐文件 SHA-256 清单(与 plugin/ 一一对应)
#   SHA256SUMS.txt               上两者自身的校验和
#
# 版本取自 plugin/.codex-plugin/plugin.json;打包内容与仓库 plugin/ 逐字节一致
# (tests/test_plugin_package.py 的 dist 一致性检查在提交后持续核对)。

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
PLUGIN="$REPO_ROOT/plugin"
DIST="$REPO_ROOT/dist"
VERSION=$(python3 -c "import json;print(json.load(open('$PLUGIN/.codex-plugin/plugin.json'))['version'])")
TARBALL="$DIST/mygamestudio-$VERSION.tar.gz"

mkdir -p "$DIST"
rm -f "$TARBALL" "$DIST/package-manifest.txt" "$DIST/SHA256SUMS.txt"

# 逐文件清单(排序稳定;忽略 __pycache__ 等生成物)
(
  cd "$PLUGIN"
  find . -type f ! -path '*/__pycache__/*' ! -name '.DS_Store' \
    | sed 's|^\./||' | LC_ALL=C sort \
    | while IFS= read -r rel; do
        printf '%s  %s\n' "$(shasum -a 256 "$rel" | awk '{print $1}')" "$rel"
      done
) > "$DIST/package-manifest.txt"

# 安装包:内容从 dist/package-manifest.txt 的清单取(与清单强一致),
# 归一化 mtime/owner,保证同源重打包字节一致。
STAGE="$DIST/.stage-mygamestudio"
rm -rf "$STAGE"
mkdir -p "$STAGE/plugin"
(
  cd "$PLUGIN"
  LC_ALL=C sort "$DIST/package-manifest.txt" | while IFS= read -r line; do
    rel="${line#*  }"
    mkdir -p "$STAGE/plugin/$(dirname "$rel")"
    cp "$rel" "$STAGE/plugin/$rel"
    touch -t 202609080000.00 "$STAGE/plugin/$rel"
  done
)
(cd "$STAGE" && find . -type d | LC_ALL=C sort | tail -r | while IFS= read -r d; do
  [ "$d" = "." ] && continue
  touch -t 202609080000.00 "$d"
done)
# gzip -n 去掉 gzip 头时间戳;tar 选项尽力归一化 uid/gid(xattr 扩展用
# COPYFILE_DISABLE 关闭),同源重打包字节一致(见 runbook 的复现核对)。
(cd "$STAGE" && COPYFILE_DISABLE=1 tar --uid 0 --gid 0 --uname root --gname wheel \
  -cf - plugin 2>/dev/null || COPYFILE_DISABLE=1 tar -cf - plugin) | gzip -n > "$TARBALL"
rm -rf "$STAGE"

# 产物校验和(供审阅者核对下载/复制后的完整性)
(
  cd "$DIST"
  for f in "mygamestudio-$VERSION.tar.gz" package-manifest.txt; do
    printf '%s  %s\n' "$(shasum -a 256 "$f" | awk '{print $1}')" "$f"
  done
) > "$DIST/SHA256SUMS.txt"

echo "构建完成: dist/mygamestudio-$VERSION.tar.gz"
echo "逐文件清单: dist/package-manifest.txt ($(wc -l < "$DIST/package-manifest.txt" | tr -d ' ') 个文件)"
echo "校验和: dist/SHA256SUMS.txt"

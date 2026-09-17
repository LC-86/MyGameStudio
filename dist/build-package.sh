#!/bin/bash
# 任务票 18:构建可审阅的安装包与逐文件清单。
#
# 用法:./dist/build-package.sh   (在仓库根执行;重复执行产出一致的内容)
#
# 产物(全部落 dist/):
#   mygamestudio-<版本>.tar.gz   安装包(plugin/ 全量,归一化 mtime/uid/gid,
#                                排除平台扩展元数据,同源重打包字节一致)
#   package-manifest.txt         包内逐文件 SHA-256 清单(与 plugin/ 一一对应)
#   SHA256SUMS.txt               上两者自身的校验和
#
# 版本取自 plugin/.codex-plugin/plugin.json;打包内容与仓库 plugin/ 逐字节一致
# (tests/test_plugin_package.py 的 dist 一致性检查在提交后持续核对)。
# 字节可复现性(干净副本隔离重建逐字节比对)由 ./dist/verify-reproducible.sh
# 与 test_plugin_package.py 的隔离重建检查固化(审查修复票 03/R5)。

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
REVERSE_CMD=(tail -r)
if ! tail -r /dev/null >/dev/null 2>&1 && command -v tac >/dev/null 2>&1; then
  REVERSE_CMD=(tac)
fi
(cd "$STAGE" && find . -type d | LC_ALL=C sort | "${REVERSE_CMD[@]}" | while IFS= read -r d; do
  [ "$d" = "." ] && continue
  touch -t 202609080000.00 "$d"
done)
# gzip -n 去掉 gzip 头时间戳;tar 选项归一化 uid/gid。平台扩展元数据
# (com.apple.provenance 等扩展属性/ACL/文件标志)必须排除:它们随文件
# 创建链路变化,COPYFILE_DISABLE 只能挡住 AppleDouble(._ 文件),挡不住
# 进入 PAX 头的扩展属性(审查修复票 03/R5 的实证差异来源)。
# 目标宿主 macOS 的 bsdtar 需显式 --no-xattrs/--no-acls/--no-fflags
# (GNU tar 默认不读扩展属性,但本脚本其他部分亦依赖 BSD 工具,不声明
# 跨平台支持);后备分支在首条 tar 命令以任何原因失败时触发,且不含
# owner 归一化——其产物的可复现性由 verify-reproducible.sh 兜底核验。
TAR_META_FLAGS=""
if tar --no-xattrs --no-acls --no-fflags --version >/dev/null 2>&1; then
  TAR_META_FLAGS="--no-xattrs --no-acls --no-fflags"
fi
(cd "$STAGE" && COPYFILE_DISABLE=1 tar --uid 0 --gid 0 --uname root --gname wheel \
  $TAR_META_FLAGS -cf - plugin 2>/dev/null \
  || COPYFILE_DISABLE=1 tar $TAR_META_FLAGS -cf - plugin) | gzip -n > "$TARBALL"
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

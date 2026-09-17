#!/bin/bash
# 下一版本安装包构建：从 plugin/ 打包，并把仓库根目录 LICENSE 与
# THIRD_PARTY_NOTICES.md 带入插件根。不在 plugin/ 源码里维护第二份许可正文。
#
# 当前已发布的 2.0.1 产物仍由 dist/build-package.sh 构建；本脚本默认拒绝覆盖它。
# 用法（仓库根）：./scripts/build-package.sh
# 测试可把仓库布局复制到临时目录后执行。

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
PLUGIN="$REPO_ROOT/plugin"
DIST="$REPO_ROOT/dist"
LICENSE_SRC="$REPO_ROOT/LICENSE"
NOTICES_SRC="$REPO_ROOT/THIRD_PARTY_NOTICES.md"
VERSION=$(python3 -c "import json;print(json.load(open('$PLUGIN/.codex-plugin/plugin.json'))['version'])")
TARBALL="$DIST/mygamestudio-$VERSION.tar.gz"

if [ ! -f "$LICENSE_SRC" ] || [ ! -f "$NOTICES_SRC" ]; then
  echo "缺少根目录 LICENSE 或 THIRD_PARTY_NOTICES.md" >&2
  exit 1
fi

if [ "$VERSION" = "2.0.1" ] && [ -f "$DIST/mygamestudio-2.0.1.tar.gz" ] && \
   [ -f "$DIST/issue-62-technical-evidence.json" ]; then
  echo "拒绝覆盖已发布的 2.0.1 安装包（SHA 已写入 dist 交接证据）。" >&2
  echo "请先升高插件版本，或继续使用 ./dist/build-package.sh 重建 2.0.1。" >&2
  exit 1
fi

mkdir -p "$DIST"
rm -f "$TARBALL" "$DIST/package-manifest.txt"

STAGE="$DIST/.stage-mygamestudio"
rm -rf "$STAGE"
mkdir -p "$STAGE/plugin"

(
  cd "$PLUGIN"
  find . -type f ! -path '*/__pycache__/*' ! -name '.DS_Store' \
    | sed 's|^\./||' | LC_ALL=C sort \
    | while IFS= read -r rel; do
        mkdir -p "$STAGE/plugin/$(dirname "$rel")"
        cp "$rel" "$STAGE/plugin/$rel"
        touch -t 202609080000.00 "$STAGE/plugin/$rel"
      done
)

cp "$LICENSE_SRC" "$STAGE/plugin/LICENSE"
cp "$NOTICES_SRC" "$STAGE/plugin/THIRD_PARTY_NOTICES.md"
touch -t 202609080000.00 "$STAGE/plugin/LICENSE" "$STAGE/plugin/THIRD_PARTY_NOTICES.md"

REVERSE_CMD=(tail -r)
if command -v tac >/dev/null 2>&1; then
  REVERSE_CMD=(tac)
fi
(cd "$STAGE" && find . -type d | LC_ALL=C sort | "${REVERSE_CMD[@]}" | while IFS= read -r d; do
  [ "$d" = "." ] && continue
  touch -t 202609080000.00 "$d"
done)

(
  cd "$STAGE/plugin"
  find . -type f ! -path '*/__pycache__/*' ! -name '.DS_Store' \
    | sed 's|^\./||' | LC_ALL=C sort \
    | while IFS= read -r rel; do
        printf '%s  %s\n' "$(shasum -a 256 "$rel" | awk '{print $1}')" "$rel"
      done
) > "$DIST/package-manifest.txt"

TAR_META_FLAGS=""
if tar --no-xattrs --no-acls --no-fflags --version >/dev/null 2>&1; then
  TAR_META_FLAGS="--no-xattrs --no-acls --no-fflags"
fi
(cd "$STAGE" && COPYFILE_DISABLE=1 tar --uid 0 --gid 0 --uname root --gname wheel \
  $TAR_META_FLAGS -cf - plugin 2>/dev/null \
  || COPYFILE_DISABLE=1 tar $TAR_META_FLAGS -cf - plugin) | gzip -n > "$TARBALL"
rm -rf "$STAGE"

{
  printf '%s  %s\n' "$(shasum -a 256 "$TARBALL" | awk '{print $1}')" "mygamestudio-$VERSION.tar.gz"
  printf '%s  %s\n' "$(shasum -a 256 "$DIST/package-manifest.txt" | awk '{print $1}')" "package-manifest.txt"
  if [ "$VERSION" != "2.0.1" ] && [ -f "$DIST/mygamestudio-2.0.1.tar.gz" ]; then
    printf '%s  %s\n' "$(shasum -a 256 "$DIST/mygamestudio-2.0.1.tar.gz" | awk '{print $1}')" "mygamestudio-2.0.1.tar.gz"
  fi
} > "$DIST/SHA256SUMS.txt"

echo "构建完成: dist/mygamestudio-$VERSION.tar.gz（含根目录许可副本）"
echo "逐文件清单: dist/package-manifest.txt ($(wc -l < "$DIST/package-manifest.txt" | tr -d ' ') 个文件)"
echo "校验和: dist/SHA256SUMS.txt"

#!/bin/bash
# 下一版本构建的隔离可复现检查。使用 scripts/build-package.sh。
# 已发布 2.0.1 仍用 ./dist/verify-reproducible.sh。
#
# 用法：在含 plugin/、LICENSE、THIRD_PARTY_NOTICES.md、scripts/build-package.sh
# 的仓库布局根目录执行。默认比较两次隔离重建，不覆盖当前 dist/2.0.1。

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
VERSION=$(python3 -c "import json;print(json.load(open('$REPO_ROOT/plugin/.codex-plugin/plugin.json'))['version'])")
TMP="$(mktemp -d /tmp/mgs-verify-next.XXXXXX)"
trap 'rm -rf "$TMP"' EXIT

if [ "$VERSION" = "2.0.1" ] && [ -f "$REPO_ROOT/dist/issue-62-technical-evidence.json" ]; then
  echo "2.0.1 的发布包仍由 dist/verify-reproducible.sh 核对。"
  echo "本脚本改为：在临时目录用 scripts/build-package.sh 做两次隔离重建比对。"
fi

hashes=""
for tag in a b; do
  root="$TMP/$tag"
  mkdir -p "$root/dist" "$root/scripts"
  git -C "$REPO_ROOT" archive HEAD | tar -x -C "$root"
  cp "$REPO_ROOT/scripts/build-package.sh" "$root/scripts/build-package.sh"
  chmod +x "$root/scripts/build-package.sh"
  (cd "$root" && ./scripts/build-package.sh >/dev/null)
  hashes="$hashes $(shasum -a 256 "$root/dist/mygamestudio-$VERSION.tar.gz" | awk '{print $1}')"
done

set -- $hashes
if [ "$1" != "$2" ]; then
  echo "FAIL: 两次隔离重建字节不一致"
  echo "  a: $1"
  echo "  b: $2"
  exit 1
fi

echo "PASS: scripts/build-package.sh 两次隔离重建逐字节一致"
echo "包 SHA-256: $1"

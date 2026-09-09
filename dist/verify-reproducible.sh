#!/bin/bash
# 审查修复票 03(R5):「同源重打包字节一致」的可重复验证。
#
# 用法:在仓库根执行 ./dist/verify-reproducible.sh
#
# 验证方式(不再以同目录重复构建充当):
#   1. 用 git archive HEAD 生成干净副本(只含已提交内容,无工作树杂项);
#   2. 把当前 dist/build-package.sh(即产出交付包的脚本本体)放入副本;
#   3. 在副本内隔离重建;
#   4. 三项产物(tar.gz/package-manifest.txt/SHA256SUMS.txt)与 dist/ 交付物
#      逐字节比对(cmp);
#   5. 扫描交付包与重建包的 tar 成员,任何 PAX 扩展头(com.apple.provenance
#      等平台扩展元数据或其他未归一化字段)都判失败。
#
# 失败排查:plugin/ 有未提交改动、或 dist/ 交付物不是由当前脚本重建时,
# 比对会失败——先提交改动并重跑 ./dist/build-package.sh。

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
DIST="$REPO_ROOT/dist"
VERSION=$(python3 -c "import json;print(json.load(open('$REPO_ROOT/plugin/.codex-plugin/plugin.json'))['version'])")
TMP="$(mktemp -d /tmp/mgs-verify-repro.XXXXXX)"
trap 'rm -rf "$TMP"' EXIT

mkdir -p "$TMP/copy"
git -C "$REPO_ROOT" archive HEAD | tar -x -C "$TMP/copy"
cp "$DIST/build-package.sh" "$TMP/copy/dist/build-package.sh"
chmod +x "$TMP/copy/dist/build-package.sh"
(cd "$TMP/copy" && ./dist/build-package.sh >/dev/null)

for artifact in "mygamestudio-$VERSION.tar.gz" package-manifest.txt SHA256SUMS.txt; do
  if cmp -s "$DIST/$artifact" "$TMP/copy/dist/$artifact"; then
    echo "PASS: $artifact 干净副本隔离重建与交付物逐字节一致"
  else
    echo "FAIL: $artifact 干净副本隔离重建与交付物不一致"
    echo "  交付: $(shasum -a 256 "$DIST/$artifact" | awk '{print $1}')"
    echo "  重建: $(shasum -a 256 "$TMP/copy/dist/$artifact" | awk '{print $1}')"
    exit 1
  fi
done

python3 - "$DIST/mygamestudio-$VERSION.tar.gz" "$TMP/copy/dist/mygamestudio-$VERSION.tar.gz" <<'EOF'
import sys
import tarfile

bad = []
for path in sys.argv[1:]:
    with tarfile.open(path, "r:gz") as tar:
        for member in tar.getmembers():
            if member.pax_headers:
                bad.append((path.split("/")[-1], member.name,
                            sorted(member.pax_headers)))
if bad:
    print("FAIL: tar 成员携带 PAX 扩展头(平台扩展元数据或未归一化字段,前 3 项):")
    for item in bad[:3]:
        print(f"  {item}")
    sys.exit(1)
print("PASS: 交付包与重建包的 tar 成员均无 PAX 扩展头(平台扩展元数据已排除)")
EOF

echo "PASS: 同源重打包字节可复现性验证全部通过"
echo "交付包 SHA-256: $(shasum -a 256 "$DIST/mygamestudio-$VERSION.tar.gz" | awk '{print $1}')"

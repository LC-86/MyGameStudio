#!/usr/bin/env bash
# 隔离原生安装验证：用官方 skills CLI 从本仓库安装到临时消费项目，
# 检查发现集合、随包资料、许可通知与跨技能引用在安装目录内可达。
#
#   scripts/install-smoke-test.sh [仓库路径]
#
# 环境变量：
#   SKILLS_CLI_VERSION  固定的 CLI 版本，默认 1.7.0
#   SKILLS_CLI          直接指定 cli.mjs 路径，跳过 npx（无网络时使用）
#
# 不使用 --global 与 --all，不写入真实 HOME 下的任何技能或配置目录。
set -uo pipefail

REPO="${1:-$(cd "$(dirname "$0")/.." && pwd)}"
REPO="$(cd "$REPO" && pwd)"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=resolve-skills-cli.sh
. "$SCRIPT_DIR/resolve-skills-cli.sh"
VERSION="${SKILLS_CLI_VERSION:-1.7.0}"
WORK="$(mktemp -d "${TMPDIR:-/tmp}/mgs-install-test.XXXXXX")"
export DO_NOT_TRACK=1 DISABLE_TELEMETRY=1
# CLI 的 --list 是给人看的彩色表格：终端宽度不同会把技能名折行。
# 因此这里关掉颜色，并在匹配前去掉 ANSI 与多余空白；名称集合的权威判据是安装结果，不是这段文本。
export NO_COLOR=1 FORCE_COLOR=0 TERM=dumb
ANSI_RE=$'s/\x1b\\[[0-9;]*[A-Za-z]//g'
FAIL=0
PASS=0

note() { printf '\n=== %s ===\n' "$1"; }
ok()   { PASS=$((PASS+1)); printf 'PASS  %s\n' "$1"; }
bad()  { FAIL=$((FAIL+1)); printf 'FAIL  %s\n' "$1"; }
info() { printf '      %s\n' "$1"; }
# 去 ANSI 并把连续空白压成单个空格，用于匹配 "Found N skills" 这类短语。
# 只处理字节安全的转义序列，不动多字节字符。
clean() { sed -e "$ANSI_RE" | tr -s '[:space:]' ' '; }

resolve_cli() {
  if ! resolve_skills_cli "$VERSION"; then
    bad "无法取得 skills CLI，见上面的原因"
    printf 'PASS %d / FAIL %d\n' "$PASS" "$FAIL"
    exit 1
  fi
  CLI=("${SKILLS_CLI_CMD[@]}")
}

run_cli() { "${CLI[@]}" "$@" 2>&1; }

EXPECTED="ask-gamestudio codebase-gamestudio debug-gamestudio docs-gamestudio domain-gamestudio
gdd-gamestudio grill-gamestudio grill-gamestudio-docs grilling-gamestudio handoff-gamestudio
implement-gamestudio merge-gamestudio prototype-gamestudio research-gamestudio review-gamestudio
setup-gamestudio spec-gamestudio tasks-gamestudio tdd-gamestudio wayfinder-gamestudio"

resolve_cli
note "0. 环境"
info "仓库：$REPO"
info "工作目录：$WORK"
info "CLI 调用：${CLI[*]}"
info "来源标识：$(git -C "$REPO" rev-parse --short HEAD)$( [ -n "$(git -C "$REPO" status --porcelain)" ] && echo '-dirty' || echo '-clean')"
info "CLI 版本：$(run_cli --version 2>&1 | clean | grep -oE '[0-9]+\.[0-9]+\.[0-9]+' | tail -1)"

note "1. 发现集合恰为 20 项"
CONSUMER="$WORK/consumer-list"; mkdir -p "$CONSUMER"
LIST="$(cd "$CONSUMER" && run_cli add "$REPO" --list 2>&1)"
LIST_CLEAN="$(printf '%s\n' "$LIST" | clean)"
printf '%s\n' "$LIST" | sed -e "$ANSI_RE" | grep -E '◇|●|■|✓|⚠' | cut -c1-120 | head -3 | sed 's/^/      /'
FOUND_N="$(printf '%s' "$LIST_CLEAN" | grep -oE 'Found [0-9]+' | head -1 | grep -oE '[0-9]+')"
if [ -z "$FOUND_N" ]; then
  info "未能从 --list 文本解析数量（该输出是给人看的表格，会随终端宽度折行）；名称集合由第 2 步的安装结果判定"
elif [ "$FOUND_N" = "20" ]; then
  ok "CLI 报告发现 20 项"
else
  bad "CLI 报告发现 $FOUND_N 项，应为 20 项"
fi
printf '%s' "$LIST_CLEAN" | grep -qE 'game-producer|game-init|game-design|ask-matt|to-spec|to-tickets|writing-for-agents|diagnosing-bugs' \
  && bad "发现集合含旧技能名" || ok "发现输出无旧技能名或已退役入口"

note "2. 完整安装（--agent universal --copy）"
FULL="$WORK/consumer-full"; mkdir -p "$FULL"
OUT="$(cd "$FULL" && run_cli add "$REPO" --skill '*' --agent universal --copy -y)"
printf '%s\n' "$OUT" | tail -4 | sed 's/^/      /'
DEST="$FULL/.agents/skills"
[ -d "$DEST" ] && ok "安装到 .agents/skills/" || bad "未找到 .agents/skills/"
INSTALLED=0
for name in $EXPECTED; do
  if [ -f "$DEST/$name/SKILL.md" ]; then
    INSTALLED=$((INSTALLED+1))
  else
    bad "未安装 $name"
  fi
done
[ "$INSTALLED" = "20" ] && ok "20 项 SKILL.md 齐全"
EXTRA_DIRS="$(find "$DEST" -mindepth 1 -maxdepth 1 -type d -exec basename {} \; | sort)"
for d in $EXTRA_DIRS; do
  printf '%s\n' $EXPECTED | grep -qx "$d" || bad "安装目录含集合外技能 $d"
done

note "3. 随包资料、许可与引用在安装目录内可达"
MISSING_REF=0; MISSING_LIC=0
for name in $EXPECTED; do
  [ -f "$DEST/$name/LICENSE" ] || { bad "$name 缺少 LICENSE 通知"; MISSING_LIC=1; }
  grep -q 'MIT License' "$DEST/$name/LICENSE" 2>/dev/null || { bad "$name LICENSE 内容不完整"; MISSING_LIC=1; }
  for f in $(find "$DEST/$name" -name '*.md'); do
    for raw in $(grep -oE '\]\([^) ]+\)' "$f" | sed 's/^](//; s/)$//'); do
      case "$raw" in http*|\#*|mailto*) continue ;; esac
      target="$(dirname "$f")/${raw%%#*}"
      [ -e "$target" ] || { bad "$(printf '%s' "$target" | sed "s|$DEST/||") 不可达（来自 ${f#$DEST/}）"; MISSING_REF=1; }
    done
  done
done
[ "$MISSING_LIC" = "0" ] && ok "20 份许可通知齐全且含 MIT 全文"
[ "$MISSING_REF" = "0" ] && ok "安装目录内全部相对引用可达"

note "4. 安装内容不依赖源码 checkout"
DEP=0
for name in $EXPECTED; do
  for f in $(find "$DEST/$name" -type f); do
    case "$f" in *.md|*.txt) ;; *) continue ;; esac
    if grep -qF "$REPO" "$f"; then bad "${f#$DEST/} 含源码 checkout 绝对路径"; DEP=1; fi
    if grep -qE '\]\(\.\./\.\./\.\./' "$f"; then bad "${f#$DEST/} 逃出安装目录"; DEP=1; fi
  done
done
[ "$DEP" = "0" ] && ok "安装内容不含指向源码 checkout 的引用"
[ -f "$FULL/skills-lock.json" ] && ok "生成 skills-lock.json" \
  && grep -o '"sourceType":[^,]*' "$FULL/skills-lock.json" | head -1 | sed 's/^/      /'
# --copy 模式必须产生真实文件而不是指回源码树的符号链接
LINKED=0
for name in $EXPECTED; do
  [ -L "$DEST/$name" ] && { bad "$name 在 --copy 模式下仍是符号链接"; LINKED=1; }
  [ -L "$DEST/$name/SKILL.md" ] && { bad "$name/SKILL.md 是符号链接"; LINKED=1; }
done
[ "$LINKED" = "0" ] && ok "--copy 模式产生独立真实副本，不指回源码树"

note "5. 共享参考的实际归属与子集安装负例"
[ -f "$DEST/docs-gamestudio/references/document-routing.md" ] && ok "document-routing.md 归 docs-gamestudio" || bad "缺少共享参考 document-routing.md"
[ -f "$DEST/docs-gamestudio/references/delegation.md" ] && ok "delegation.md 归 docs-gamestudio" || bad "缺少共享参考 delegation.md"
[ -f "$DEST/tasks-gamestudio/references/task-responsibility.md" ] && ok "task-responsibility.md 归 tasks-gamestudio" || bad "缺少共享参考 task-responsibility.md"
SUB="$WORK/consumer-subset"; mkdir -p "$SUB"
SUBOUT="$(cd "$SUB" && run_cli add "$REPO" --skill tdd-gamestudio --agent universal --copy -y)"
printf '%s\n' "$SUBOUT" | tail -2 | sed 's/^/      /'
if [ -d "$SUB/.agents/skills/docs-gamestudio" ] || [ -d "$SUB/.agents/skills/tasks-gamestudio" ]; then
  bad "CLI 自动安装了依赖（与文档声明不符，需更新 docs/dependencies.md）"
else
  ok "CLI 不自动解析技能间依赖，符合文档声明"
fi
if [ -f "$SUB/.agents/skills/tdd-gamestudio/SKILL.md" ]; then
  ok "子集安装成功"
  [ -e "$SUB/.agents/skills/tasks-gamestudio/references/task-responsibility.md" ] \
    && bad "子集安装却有依赖资料" \
    || info "负例成立：tdd-gamestudio 单独安装后缺少 task-responsibility.md，正文中的相对引用不可达"
fi

note "6. 默认链接模式（两个宿主）"
LINK="$WORK/consumer-link"; mkdir -p "$LINK"
LINKOUT="$(cd "$LINK" && run_cli add "$REPO" --skill ask-gamestudio docs-gamestudio --agent universal claude-code -y)"
printf '%s\n' "$LINKOUT" | tail -3 | sed 's/^/      /'
CANON="$LINK/.agents/skills/ask-gamestudio"
SL="$LINK/.claude/skills/ask-gamestudio"
if [ -L "$SL" ]; then
  ok "多宿主安装使用 .agents/skills 正本 + 宿主目录符号链接"
  info "$(ls -ld "$SL" | sed 's|.*'"$LINK"'|.|')"
  [ -f "$SL/SKILL.md" ] && ok "符号链接可解析到正文" || bad "符号链接不可解析"
elif [ -d "$SL" ] && [ -d "$CANON" ]; then
  ok "多宿主安装生成两份真实副本（--copy 语义）"
else
  bad "多宿主安装布局与预期不符"
fi

note "7. 二次安装不产生双份有效名称或旧别名"
AGAIN="$(cd "$FULL" && run_cli add "$REPO" --skill '*' --agent universal --copy -y)"
printf '%s\n' "$AGAIN" | tail -2 | sed 's/^/      /'
DUP="$(find "$DEST" -mindepth 1 -maxdepth 1 -type d | wc -l | tr -d ' ')"
[ "$DUP" = "20" ] && ok "二次安装后仍为 20 个技能目录" || bad "二次安装后目录数变为 $DUP"
OLD="$(find "$FULL" -type d \( -name 'ask-matt' -o -name 'to-spec' -o -name 'to-tickets' -o -name 'game-producer' \) | wc -l | tr -d ' ')"
[ "$OLD" = "0" ] && ok "无旧别名目录" || bad "出现旧别名目录"

note "8. --full-depth 是否暴露额外 SKILL.md"
FD="$(cd "$WORK/consumer-list" && run_cli add "$REPO" --list --full-depth 2>&1)"
PLAIN_N="$(printf '%s' "$LIST_CLEAN" | grep -oE 'Found [0-9]+' | head -1 | grep -oE '[0-9]+')"
FULL_N="$(printf '%s' "$FD" | clean | grep -oE 'Found [0-9]+' | head -1 | grep -oE '[0-9]+')"
info "默认发现 ${PLAIN_N:-未解析} 项，--full-depth 发现 ${FULL_N:-未解析} 项"
if [ -z "$FULL_N" ]; then
  bad "--full-depth 输出无法解析数量，需检查 CLI 版本或输出格式"
elif [ "$FULL_N" = "20" ]; then
  ok "--full-depth 未发现旧技能、样例或夹具入口"
elif [ "$FULL_N" = "${PLAIN_N:-0}" ]; then
  ok "--full-depth 与默认发现数一致（${FULL_N}），无额外入口"
else
  bad "--full-depth 发现 $FULL_N 项，多于默认的 ${PLAIN_N:-?} 项，仓库内可能有游离 SKILL.md"
  printf '%s\n' "$FD" | sed -e "$ANSI_RE" | grep -vE -- '-gamestudio|^│|^┌|^└|^├|^\s*$' | head -10 | sed 's/^/      /'
fi

note "结果"
printf 'PASS %d / FAIL %d\n' "$PASS" "$FAIL"
printf '工作目录保留在 %s 供核对；确认后可删除。\n' "$WORK"
[ "$FAIL" = "0" ]

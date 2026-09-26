#!/usr/bin/env bash
# 隔离原生安装验证：用官方 skills CLI 从本仓库安装到临时消费项目，
# 检查发现集合、随包资料、许可通知与跨技能引用在安装目录内可达；
# 第 10 节与第 11 节另外从官方 mattpocock/skills 安装外部共同方法，核对两来源组合。
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
setup-gamestudio spec-gamestudio tasks-gamestudio tdd-gamestudio wayfinder-gamestudio
writing-for-agents"

resolve_cli
note "0. 环境"
info "仓库：$REPO"
info "工作目录：$WORK"
info "CLI 调用：${CLI[*]}"
info "来源标识：$(git -C "$REPO" rev-parse --short HEAD)$( [ -n "$(git -C "$REPO" status --porcelain)" ] && echo '-dirty' || echo '-clean')"
info "CLI 版本：$(run_cli --version 2>&1 | clean | grep -oE '[0-9]+\.[0-9]+\.[0-9]+' | tail -1)"

note "1. 发现集合恰为 21 项"
CONSUMER="$WORK/consumer-list"; mkdir -p "$CONSUMER"
LIST="$(cd "$CONSUMER" && run_cli add "$REPO" --list 2>&1)"
LIST_CLEAN="$(printf '%s\n' "$LIST" | clean)"
printf '%s\n' "$LIST" | sed -e "$ANSI_RE" | grep -E '◇|●|■|✓|⚠' | cut -c1-120 | head -3 | sed 's/^/      /'
FOUND_N="$(printf '%s' "$LIST_CLEAN" | grep -oE 'Found [0-9]+' | head -1 | grep -oE '[0-9]+')"
if [ -z "$FOUND_N" ]; then
  info "未能从 --list 文本解析数量（该输出是给人看的表格，会随终端宽度折行）；名称集合由第 2 步的安装结果判定"
elif [ "$FOUND_N" = "21" ]; then
  ok "CLI 报告发现 21 项"
else
  bad "CLI 报告发现 $FOUND_N 项，应为 21 项"
fi
printf '%s' "$LIST_CLEAN" | grep -qE 'game-producer|game-init|game-design|ask-matt|to-spec|to-tickets|diagnosing-bugs' \
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
[ "$INSTALLED" = "21" ] && ok "21 项 SKILL.md 齐全"
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
[ "$MISSING_LIC" = "0" ] && ok "21 份许可通知齐全且含 MIT 全文"
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
[ -f "$DEST/docs-gamestudio/references/semantic-fidelity.md" ] && ok "semantic-fidelity.md 归 docs-gamestudio" || bad "缺少语义保真契约"
[ -f "$DEST/docs-gamestudio/references/delegation.md" ] && ok "delegation.md 归 docs-gamestudio" || bad "缺少通用委派契约"
[ -f "$DEST/writing-for-agents/SKILL-MECHANICS.md" ] && ok "SKILL-MECHANICS.md 随外部方法副本发行（不归 GameStudio 拥有）" || bad "缺少共同技能机制参考"
[ -f "$DEST/writing-for-agents/references/subagent-delegation.md" ] && ok "subagent-delegation.md 随外部方法副本发行（不是 GameStudio 委派方法）" || bad "缺少随包副本的委派参考"
[ -f "$DEST/tasks-gamestudio/references/task-responsibility.md" ] && ok "task-responsibility.md 归 tasks-gamestudio" || bad "缺少共享参考 task-responsibility.md"

GENERIC="$WORK/consumer-generic-minimal"; mkdir -p "$GENERIC"
GENERIC_OUT="$(cd "$GENERIC" && run_cli add "$REPO" --skill writing-for-agents --agent universal --copy -y)"
GENERIC_DEST="$GENERIC/.agents/skills"
[ -f "$GENERIC_DEST/writing-for-agents/SKILL.md" ] \
  && [ -f "$GENERIC_DEST/writing-for-agents/references/subagent-delegation.md" ] \
  && ok "通用最小组合：writing-for-agents 单项安装且所需参考可达" \
  || bad "通用最小组合缺少 writing-for-agents 正文或参考"
[ ! -d "$GENERIC_DEST/docs-gamestudio" ] \
  && ok "通用最小组合不强装 GameStudio 专属分流" \
  || bad "通用最小组合意外安装 docs-gamestudio"

GAME_DOCS="$WORK/consumer-game-docs-minimal"; mkdir -p "$GAME_DOCS"
GAME_DOCS_OUT="$(cd "$GAME_DOCS" && run_cli add "$REPO" \
  --skill writing-for-agents docs-gamestudio gdd-gamestudio --agent universal --copy -y)"
GAME_DOCS_DEST="$GAME_DOCS/.agents/skills"
[ -f "$GAME_DOCS_DEST/writing-for-agents/SKILL.md" ] \
  && [ -f "$GAME_DOCS_DEST/docs-gamestudio/references/semantic-fidelity.md" ] \
  && [ -f "$GAME_DOCS_DEST/docs-gamestudio/references/delegation.md" ] \
  && [ -f "$GAME_DOCS_DEST/docs-gamestudio/references/document-routing.md" ] \
  && [ -f "$GAME_DOCS_DEST/gdd-gamestudio/references/gdd-writing.md" ] \
  && ok "游戏设计最小组合：共同写法、保真、委派、游戏分流与 GDD 参考均可达" \
  || bad "游戏设计最小组合缺少必需正文或参考"

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
[ "$DUP" = "21" ] && ok "二次安装后仍为 21 个技能目录" || bad "二次安装后目录数变为 $DUP"
OLD="$(find "$FULL" -type d \( -name 'ask-matt' -o -name 'to-spec' -o -name 'to-tickets' -o -name 'game-producer' \) | wc -l | tr -d ' ')"
[ "$OLD" = "0" ] && ok "无旧别名目录" || bad "出现旧别名目录"

note "8. Issue #90 接缝：外部共同方法按名称解析，消费者不写跨范围相对路径"
# 只依赖 Python 标准库，逐项对齐 docs-gamestudio 与消费者正文里的声明；
# 任一项不成立就 FAIL，避免接缝在收缩随包副本时才发现已经失效。
SEAM_OUT="$(python3.12 - "$DEST" <<'PY' 2>&1
import os
import re
import sys
from pathlib import Path


def norm(path):
    """只做词法规范化，不解析符号链接：临时目录常经 /var -> /private/var 跳转。"""
    return Path(os.path.normpath(str(path)))


dest = Path(sys.argv[1])
link_re = re.compile(r"\[[^\]]*\]\(([^)\s]+)\)")
base = ["ask-gamestudio", "codebase-gamestudio", "debug-gamestudio",
        "docs-gamestudio", "domain-gamestudio", "gdd-gamestudio",
        "grill-gamestudio", "grill-gamestudio-docs", "grilling-gamestudio",
        "handoff-gamestudio", "implement-gamestudio", "merge-gamestudio",
        "prototype-gamestudio", "research-gamestudio", "review-gamestudio",
        "setup-gamestudio", "spec-gamestudio", "tasks-gamestudio",
        "tdd-gamestudio", "wayfinder-gamestudio"]
required = {"docs-gamestudio": ("references/semantic-fidelity.md",
                               "references/delegation.md",
                               "references/document-routing.md")}
writing_consumers = ["ask-gamestudio", "codebase-gamestudio", "debug-gamestudio",
                     "docs-gamestudio", "domain-gamestudio", "gdd-gamestudio",
                     "handoff-gamestudio", "implement-gamestudio", "merge-gamestudio",
                     "prototype-gamestudio", "research-gamestudio", "review-gamestudio",
                     "setup-gamestudio", "spec-gamestudio", "tasks-gamestudio",
                     "tdd-gamestudio", "wayfinder-gamestudio"]
fidelity_consumers = ["codebase-gamestudio", "debug-gamestudio", "domain-gamestudio",
                      "gdd-gamestudio", "handoff-gamestudio", "implement-gamestudio",
                      "merge-gamestudio", "prototype-gamestudio", "research-gamestudio",
                      "review-gamestudio", "setup-gamestudio", "spec-gamestudio",
                      "tdd-gamestudio", "wayfinder-gamestudio"]
delegation_consumers = ["ask-gamestudio", "grilling-gamestudio", "handoff-gamestudio",
                        "implement-gamestudio", "research-gamestudio",
                        "review-gamestudio", "tasks-gamestudio", "wayfinder-gamestudio"]

problems = []
for name in base:
    path = dest / name / "SKILL.md"
    if not path.is_file():
        problems.append("缺少 %s/SKILL.md" % name)
if problems:
    print("\n".join("FAIL  " + p for p in problems))
    sys.exit(1)

missing = ["%s/%s" % (owner, rel) for owner, rels in required.items() for rel in rels
           if not (dest / owner / rel).is_file()]
if missing:
    problems.append("缺少共享参考：" + "、".join(missing))

def body(name):
    return (dest / name / "SKILL.md").read_text(encoding="utf-8")

for name in ["writing-for-agents"] + base:
    text = body(name)
    if re.search(r"\[[^\]]*\]\([^)]*writing-for-agents", text):
        problems.append("%s 用相对链接取得外部共同方法" % name)
    for raw in link_re.findall(text):
        if raw.startswith(("http://", "https://", "#")):
            continue
        target = norm(dest / name / raw.split("#", 1)[0])
        try:
            rel = target.relative_to(norm(dest))
        except ValueError:
            problems.append("%s 的引用逃出安装目录：%s" % (name, raw))
            continue
        owner = rel.parts[0]
        # 技能目录内的包内引用（不止 SKILL.md，还包括它自己的 references/）不算跨技能
        if owner == name or rel.name == "SKILL.md":
            continue
        if rel.as_posix() in {"%s/%s" % (o, r) for o, rs in required.items() for r in rs}:
            continue
        if owner == "writing-for-agents":
            problems.append("%s 引用随包副本私有资料：%s" % (name, raw))

for name in writing_consumers:
    if "`writing-for-agents`" not in body(name):
        problems.append("%s 未按技能名称说明外部共同方法" % name)
for name in [n for n in base if n not in writing_consumers]:
    if "writing-for-agents" in body(name):
        problems.append("%s 未使用外部共同方法却提到了它" % name)
for name in fidelity_consumers:
    if "../docs-gamestudio/references/semantic-fidelity.md" not in body(name):
        problems.append("%s 的保真要求没有指向语义保真所有者" % name)
for name in delegation_consumers:
    if "../docs-gamestudio/references/delegation.md" not in body(name):
        problems.append("%s 的委派点没有指向 docs-gamestudio" % name)

resolved = dest / "writing-for-agents" / "SKILL.md"
if not resolved.is_file():
    problems.append("安装目录内没有可作为外部方法解析目标的 writing-for-agents")
print("INFO  外部共同方法解析到 %s" % resolved)
print("INFO  写作者 %d 项；保真接入 %d 项；委派接入 %d 项"
      % (len(writing_consumers), len(fidelity_consumers), len(delegation_consumers)))
if problems:
    for item in problems:
        print("FAIL  " + item)
    sys.exit(1)
print("PASS  外部共同方法有唯一解析目标，且没有消费者写成跨范围相对路径")
PY
)"
printf '%s\n' "$SEAM_OUT" | sed 's/^FAIL/      →/;s/^PASS/      /;s/^INFO/      /'
# 成功判据是检查器明确输出 PASS：脚本崩溃、解释器缺失或语法错误都只有 stderr，
# 只看「没有 FAIL」会把没跑成的检查记成通过。
if printf '%s' "$SEAM_OUT" | grep -q '^PASS  '; then
  ok "Issue #90 接缝：消费者按技能名称取得外部共同方法，保真与委派指向 docs-gamestudio"
else
  bad "Issue #90 接缝检查未产出 PASS 结论（见上），按未通过处理"
fi

note "9. --full-depth 是否暴露额外 SKILL.md"
FD="$(cd "$WORK/consumer-list" && run_cli add "$REPO" --list --full-depth 2>&1)"
PLAIN_N="$(printf '%s' "$LIST_CLEAN" | grep -oE 'Found [0-9]+' | head -1 | grep -oE '[0-9]+')"
FULL_N="$(printf '%s' "$FD" | clean | grep -oE 'Found [0-9]+' | head -1 | grep -oE '[0-9]+')"
info "默认发现 ${PLAIN_N:-未解析} 项，--full-depth 发现 ${FULL_N:-未解析} 项"
if [ -z "$FULL_N" ]; then
  bad "--full-depth 输出无法解析数量，需检查 CLI 版本或输出格式"
elif [ "$FULL_N" = "21" ]; then
  ok "--full-depth 未发现旧技能、样例或夹具入口"
elif [ "$FULL_N" = "${PLAIN_N:-0}" ]; then
  ok "--full-depth 与默认发现数一致（${FULL_N}），无额外入口"
else
  bad "--full-depth 发现 $FULL_N 项，多于默认的 ${PLAIN_N:-?} 项，仓库内可能有游离 SKILL.md"
  printf '%s\n' "$FD" | sed -e "$ANSI_RE" | grep -vE -- '-gamestudio|^│|^┌|^└|^├|^\s*$' | head -10 | sed 's/^/      /'
fi

note "10. Issue #92 组合安装：官方共同方法 + 本票组技能，不含随包副本"
# 游戏设计与文档工作流组。先把本票组从本仓库安装到临时项目，再从官方
# mattpocock/skills 单独安装外部共同方法：这正是随包副本退出集合后的形态，
# 因此在旧发行形态仍存在时就先核对它，避免收缩时才发现引用或取得方式失效。
GROUP="docs-gamestudio domain-gamestudio gdd-gamestudio spec-gamestudio
grilling-gamestudio prototype-gamestudio wayfinder-gamestudio
grill-gamestudio grill-gamestudio-docs"
# 本票组引用到的同源技能：prototype 的人工责任参考归 tasks-gamestudio，
# wayfinder 的研究入口归 research-gamestudio。它们由工程交付组拥有，本票不改其
# 正文，只为组合安装里引用可达而一起装入同一个临时项目。
COMPANIONS="tasks-gamestudio research-gamestudio"
MIG="$WORK/consumer-issue92-group"; mkdir -p "$MIG"
MIG_DEST="$MIG/.agents/skills"
GROUP_OUT="$(cd "$MIG" && run_cli add "$REPO" --skill $GROUP $COMPANIONS --agent universal --copy -y)"
printf '%s\n' "$GROUP_OUT" | tail -3 | sed 's/^/      /'
# 「没有随包副本」只有在组本身装齐时才有意义：组安装失败会让空目录也满足
# 「目标不存在」，那条 PASS 就成了假绿。
GROUP_N="$(find "$MIG_DEST" -mindepth 1 -maxdepth 1 -type d 2>/dev/null | wc -l | tr -d ' ')"
if [ -e "$MIG_DEST/writing-for-agents" ]; then
  bad "本票组安装带入了随包 writing-for-agents"
elif [ "$GROUP_N" != "11" ]; then
  bad "本票组安装得到 ${GROUP_N} 个目录（应为 11：9 项本票组 + 2 项同源依赖），无法判定是否带随包副本"
else
  ok "本票组（9 项 + 2 项同源依赖）安装不含 MyGameStudio 随包 writing-for-agents"
fi
OFFICIAL_OUT="$(cd "$MIG" && run_cli add mattpocock/skills --skill writing-for-agents --agent universal --copy -y)"
printf '%s\n' "$OFFICIAL_OUT" | tail -3 | sed 's/^/      /'
if [ -f "$MIG_DEST/writing-for-agents/SKILL.md" ]; then
  ok "官方 mattpocock/skills 的外部共同方法装入同一项目范围"
else
  bad "官方外部共同方法未安装成功（来源不可用或 CLI 行为变化）"
fi
# 本票组的正式写作分支；其中 docs-gamestudio 是方法所有者，正文用完整措辞，
# 由检查脚本按 --gap-exempt 例外处理，其余五项必须自带缺方法处理。
WRITERS="docs-gamestudio domain-gamestudio gdd-gamestudio spec-gamestudio
prototype-gamestudio wayfinder-gamestudio"
COMPOSITION_OUT="$(python3.12 "$SCRIPT_DIR/two-source-composition-check.py" \
  --lock "$MIG/skills-lock.json" --dest "$MIG_DEST" \
  --bundled "$REPO/skills/writing-for-agents" --repo "$REPO" \
  --label "本票组" --group $GROUP --companions $COMPANIONS \
  --writers $WRITERS --gap-exempt docs-gamestudio \
  --silent grill-gamestudio grill-gamestudio-docs grilling-gamestudio 2>&1
)"
printf '%s\n' "$COMPOSITION_OUT" | sed 's/^FAIL/      →/;s/^PASS/      /;s/^INFO/      /'
if printf '%s' "$COMPOSITION_OUT" | grep -q '^PASS  '; then
  ok "Issue #92 组合：官方共同方法与本票组各自来源清楚，取得路径与引用真实可用"
else
  bad "Issue #92 组合检查未产出 PASS 结论（见上），按未通过处理"
fi

note "11. Issue #91 组合安装：官方共同方法 + 工程交付组技能，不含随包副本"
# 工程交付与协作工作流组。做法与第 10 节相同：先把本票组从本仓库装到临时项目，
# 再从官方 mattpocock/skills 单独安装外部共同方法，核对随包副本退出集合后的形态。
GROUP="ask-gamestudio codebase-gamestudio debug-gamestudio handoff-gamestudio
implement-gamestudio merge-gamestudio research-gamestudio review-gamestudio
setup-gamestudio tasks-gamestudio tdd-gamestudio"
# 本票组引用到的同源技能：11 项都指向 docs-gamestudio 的保真或委派参考；它自己的
# 分流参考又指向 domain/gdd/spec/grilling 与两个访谈入口。因此取的是引用闭包，
# 而不是「只装这 11 项」——只装 11 项时部分相对引用在安装结果里不可达。
COMPANIONS="docs-gamestudio domain-gamestudio gdd-gamestudio spec-gamestudio
grilling-gamestudio grill-gamestudio grill-gamestudio-docs"
ENG="$WORK/consumer-issue91-group"; mkdir -p "$ENG"
ENG_DEST="$ENG/.agents/skills"
ENG_OUT="$(cd "$ENG" && run_cli add "$REPO" --skill $GROUP $COMPANIONS --agent universal --copy -y)"
printf '%s\n' "$ENG_OUT" | tail -3 | sed 's/^/      /'
# 与第 10 节同理：「没有随包副本」只有在组本身装齐时才有意义，否则空目录也会满足
# 「目标不存在」，那条 PASS 就成了假绿。
ENG_N="$(find "$ENG_DEST" -mindepth 1 -maxdepth 1 -type d 2>/dev/null | wc -l | tr -d ' ')"
if [ -e "$ENG_DEST/writing-for-agents" ]; then
  bad "工程交付组安装带入了随包 writing-for-agents"
elif [ "$ENG_N" != "18" ]; then
  bad "工程交付组安装得到 ${ENG_N} 个目录（应为 18：11 项本票组 + 7 项引用闭包），无法判定是否带随包副本"
else
  ok "工程交付组（11 项 + 7 项同源依赖）安装不含 MyGameStudio 随包 writing-for-agents"
fi
ENG_OFFICIAL_OUT="$(cd "$ENG" && run_cli add mattpocock/skills --skill writing-for-agents --agent universal --copy -y)"
printf '%s\n' "$ENG_OFFICIAL_OUT" | tail -3 | sed 's/^/      /'
if [ -f "$ENG_DEST/writing-for-agents/SKILL.md" ]; then
  ok "官方 mattpocock/skills 的外部共同方法装入同一项目范围"
else
  bad "官方外部共同方法未安装成功（来源不可用或 CLI 行为变化）"
fi
# 本票组的 11 项都是正式写作分支，各自带缺方法处理；两节共用同一份校验脚本，
# 组合内容与判据分别由参数给出，避免同一段检查复制两份后各自漂移。
ENG_COMPOSITION_OUT="$(python3.12 "$SCRIPT_DIR/two-source-composition-check.py" \
  --lock "$ENG/skills-lock.json" --dest "$ENG_DEST" \
  --bundled "$REPO/skills/writing-for-agents" --repo "$REPO" \
  --label "工程交付组" --group $GROUP --companions $COMPANIONS \
  --writers $GROUP 2>&1
)"
printf '%s\n' "$ENG_COMPOSITION_OUT" | sed 's/^FAIL/      →/;s/^PASS/      /;s/^INFO/      /'
if printf '%s' "$ENG_COMPOSITION_OUT" | grep -q '^PASS  '; then
  ok "Issue #91 组合：官方共同方法与工程交付组各自来源清楚，取得路径与引用真实可用"
else
  bad "Issue #91 组合检查未产出 PASS 结论（见上），按未通过处理"
fi

note "结果"
printf 'PASS %d / FAIL %d\n' "$PASS" "$FAIL"
printf '工作目录保留在 %s 供核对；确认后可删除。\n' "$WORK"
[ "$FAIL" = "0" ]

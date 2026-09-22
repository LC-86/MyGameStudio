#!/usr/bin/env bash
# 为行为验证准备隔离夹具：一个代表性小游戏项目 + 原生安装的 20 项技能。
#   scripts/behavior-fixtures.sh <空的或尚不存在的输出目录> [场景名...]
#
# 输出目录必须是新建的或空的。脚本不会删除任何已存在的内容：要重用旧目录，
# 请自己确认后删除，或换一个目录。这样误传工程目录时不会丢东西。
#
# 环境变量：
#   SKILLS_CLI          已缓存的 cli.mjs 路径
#   SKILLS_CLI_VERSION  固定 CLI 版本，默认 1.7.0
#   USE_NPX=1           强制走 npx
set -euo pipefail
REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SCRIPT_DIR="$REPO/scripts"
# shellcheck source=resolve-skills-cli.sh
. "$SCRIPT_DIR/resolve-skills-cli.sh"
VERSION="${SKILLS_CLI_VERSION:-1.7.0}"
export DO_NOT_TRACK=1 DISABLE_TELEMETRY=1

# 位置参数可能是第一个场景名，因此先取出输出目录再 shift
OUT="${1:?用法：scripts/behavior-fixtures.sh <空的或尚不存在的输出目录> [场景名...]}"
shift || true
SCENARIOS="${*:-S01-ask S02-setup-rerun S03-routing S04-partial-save S05-subagent S06-prototype S07-condense S08-conflict S09-human-acceptance S10-no-tools}"

# --- 1. 参数校验：不依赖外部工具，不写任何东西 --------------------------
# 场景名会拼进输出路径，未校验就能用 ../x 逃出输出根并覆盖既有工程。
for s in $SCENARIOS; do
  case "$s" in
    ""|.|..|*/*|*\\*)
      printf '场景名不合法（不得为空、点号、上级或含路径分隔符）：%s\n' "$s" >&2
      exit 1 ;;
  esac
  if ! printf '%s' "$s" | grep -qE '^[A-Za-z0-9][A-Za-z0-9._-]*$'; then
    printf '场景名只允许字母、数字、点、下划线与连字符：%s\n' "$s" >&2
    exit 1
  fi
done

case "$OUT" in
  "")   echo "输出目录为空字符串，拒绝执行" >&2; exit 1 ;;
  "/")  echo "输出目录是文件系统根，拒绝执行" >&2; exit 1 ;;
esac

# 输出路径必须能安全规范化；不能就拒绝，绝不回退到未规范化的原始字符串。
# 回退会让 missing/../victim 绕过非空检查：-e 因中间目录不存在而返回假，
# 之后 mkdir -p 先建出 missing，再经 .. 落进已有的非空目录。
case "$OUT" in
  ..|*/..|../*|*/../*)
    echo "输出目录含上级引用（..），拒绝执行：$OUT" >&2
    exit 1 ;;
esac

# 用已存在的最深祖先做物理规范化（macOS 上 /tmp 是 /private/tmp 的符号链接，
# 混用逻辑与物理路径会让包含性检查误判），剩余组件不含 ..。不创建任何目录。
_walk="$OUT"
_tail=""
while [ ! -d "$_walk" ] && [ "$_walk" != "/" ]; do
  _tail="$(basename "$_walk")${_tail:+/$_tail}"
  _walk="$(dirname "$_walk")"
done
if [ ! -d "$_walk" ] || ! _root="$(cd "$_walk" && pwd -P 2>/dev/null)"; then
  echo "无法安全规范化输出目录，拒绝执行：$OUT" >&2
  exit 1
fi
OUT_ABS="$_root${_tail:+/$_tail}"
[ -n "$OUT_ABS" ] && [ "$OUT_ABS" != "/" ] || {
  echo "输出目录规范化后为空或为文件系统根，拒绝执行" >&2
  exit 1
}
# 受保护路径必须全部解析成功；解析不出来就不能确认安全，直接拒绝而不是跳过比对。
if ! HOME_PHYS="$(cd "$HOME" && pwd -P 2>/dev/null)"; then
  echo "无法解析 HOME 的物理路径，不能确认输出目录安全，拒绝执行" >&2
  exit 1
fi
if ! REPO_PHYS="$(cd "$REPO" && pwd -P 2>/dev/null)"; then
  echo "无法解析仓库路径 $REPO 的物理位置，拒绝执行" >&2
  exit 1
fi
for forbidden in "$HOME" "$REPO" "$HOME/.agents" "$HOME/.claude" "$HOME/.qoder" \
                 "$HOME/.qoder-cn" "$HOME_PHYS" "$REPO_PHYS"; do
  if [ "$OUT_ABS" = "$forbidden" ]; then
    echo "输出目录解析为 ${OUT_ABS}，与受保护路径相同，拒绝执行" >&2
    exit 1
  fi
done
if [ -e "$OUT_ABS" ] || [ -L "$OUT_ABS" ]; then
  [ -d "$OUT_ABS" ] || { echo "$OUT_ABS 已存在且不是目录，拒绝执行" >&2; exit 1; }
  # 只有「成功列出且结果为空」才算确认可写；列不出来时不能当成空目录。
  # 目录可写但不可读（如 0311）时 ls 会失败且输出为空，早期版本因此放行。
  if ! listing="$(ls -A "$OUT_ABS" 2>&1)"; then
    echo "无法列出输出目录内容，不能确认它是空的，拒绝执行：$OUT_ABS" >&2
    echo "ls 实际返回：$listing" >&2
    exit 1
  fi
  if [ -n "$listing" ]; then
    echo "$OUT_ABS 已存在且非空，本脚本不会删除已有内容。" >&2
    echo "请换一个目录，或先自行确认并处理它，例如：ls -A '$OUT_ABS'" >&2
    exit 1
  fi
fi

# --- 2. 依赖校验：仍然不写任何东西 --------------------------------------
if ! resolve_skills_cli "$VERSION"; then
  echo "未取得 skills CLI，未做任何改动" >&2
  exit 1
fi
CLI=("${SKILLS_CLI_CMD[@]}")
if ! "${CLI[@]}" --version >/dev/null 2>&1; then
  echo "skills CLI 不可执行：${CLI[*]}（未做任何改动）" >&2
  "${CLI[@]}" --version || true
  exit 1
fi
[ -d "$REPO/skills" ] || { echo "$REPO/skills 不存在，未做任何改动" >&2; exit 1; }

# --- 3. 到这里才开始写入 ------------------------------------------------
OUT="$OUT_ABS"
mkdir -p "$OUT"
echo "输出目录：$OUT"
echo "CLI 调用：${CLI[*]}"
echo "来源标识：$(git -C "$REPO" rev-parse --short HEAD)$( [ -n "$(git -C "$REPO" status --porcelain)" ] && echo '-dirty' || echo '-clean')"

make_project() {
  local p="$1"
  mkdir -p "$p"/{docs/agents,docs/design,docs/specs,docs/research,tasks,src,assets/svg}
  mkdir -p "$p"/tasks/01-dive-windup "$p"/tasks/02-third-wave
  cd "$p"
  # 显式固定初始分支，不依赖调用者的 init.defaultBranch；
  # 老版本 git 不支持 -b 时回退，并记录实际分支名供 S08 使用。
  # 夹具的 git 状态是审查者核对差异的依据，建立失败必须让脚本失败，不能 || true 吞掉
  git init -q -b main . 2>/dev/null || git init -q . || {
    echo "夹具 ${p}：git init 失败" >&2; return 1; }
  FIXTURE_BRANCH="$(git symbolic-ref --short HEAD 2>/dev/null)" || {
    echo "夹具 ${p}：无法确定初始分支" >&2; return 1; }
  [ -n "$FIXTURE_BRANCH" ] || { echo "夹具 ${p}：初始分支为空" >&2; return 1; }
  git config user.email "fixture@example.invalid" >/dev/null 2>&1 || {
    echo "夹具 ${p}：无法设置提交身份" >&2; return 1; }
  git config user.name "Fixture" >/dev/null 2>&1 || {
    echo "夹具 ${p}：无法设置提交身份" >&2; return 1; }

  cat > AGENTS.md <<'EOF'
## Agent 约定

- 任务：本地 Markdown，一票一文件，见 `docs/agents/issue-tracker.md`。
- 标签：见 `docs/agents/triage-labels.md`。
- 领域文档：见 `docs/agents/domain.md`。
- 现行设计：`docs/design/GDD.md`。本次工作规格：`docs/specs/`。
EOF
  cat > docs/agents/issue-tracker.md <<'EOF'
# 议题追踪器

本项目使用本地 Markdown 任务，一票一文件，位于 `tasks/`。文件名格式 `NN-简短标题/task.md`。
没有远端 tracker，没有自动化标签触发。
EOF
  cat > docs/agents/triage-labels.md <<'EOF'
# 分流标签

写在任务正文的 `分流:` 字段，不是远端标签，不触发任何自动化。

- `needs-triage`：需要评估的来件
- `needs-info`：缺少实际需要的信息
- `ready-for-agent`：下一执行段可由 Agent 推进
- `ready-for-human`：当前需要人完成一项具体行动，输入已就绪
- `wontfix`：明确不做
EOF
  cat > docs/agents/domain.md <<'EOF'
# 领域文档

术语表：`CONTEXT.md`。重要决策记录：`docs/adr/`（当前为空）。
EOF
  cat > CONTEXT.md <<'EOF'
# 术语表

- **潮池**：一局游戏的单个关卡场景，玩家在其中控制一只海鸟捕食。
- **重开**：结束当前一局并从第一波重新开始；永久解锁保留。
- **永久解锁**：跨局保留的能力或外观，死亡不清除。
EOF
  cat > docs/design/GDD.md <<'EOF'
# 潮汐潮池 GDD（现行）

## 目标体验
60 到 90 秒一局的紧张捕食，靠时机判断而不是反应速度取胜。

## 核心循环
海鸟在潮池上方盘旋，玩家选择俯冲时机捕食 exposed 的猎物；潮水周期改变猎物暴露窗口。

## 已采纳规则
- 俯冲有 0.4 秒前摇，前摇中不可取消。
- 潮水周期 12 秒，前 4 秒为低潮（猎物暴露窗口翻倍）。
- 一局固定 3 波，每波结束时潮位重置。

## 未决
- 死亡惩罚强度：候选 A 清空本局得分，候选 B 保留一半。尚未采纳。
- 连击倍率上限：试验值 5x，未验证。
EOF
  cat > docs/specs/2026-09-10-first-level.md <<'EOF'
# 规格：第一关可玩闭环

状态：进行中（部分已实现）

## 交付
- 第一关 3 波完整流程，含开始、结算与重开。
- 允许占位界面：结算面板可以是纯文本，不需要美术。

## 已实现
- 俯冲前摇与取消限制（src/game.js）。
- 潮水周期与低潮窗口。

## 未实现
- 第三波的猎物生成节奏。
- 结算面板。

## 验证
- [ ] Agent：3 波结束后进入结算，重开回到第一波且永久解锁保留。
- [ ] 开发者：俯冲手感与时机判断是否成立（需在浏览器实际试玩）。
EOF
  cat > src/game.js <<'EOF'
// 潮汐潮池：核心规则
export const TIDE_PERIOD = 12;
export const LOW_TIDE_SECONDS = 4;
export const DIVE_WINDUP = 0.4;

export function isLowTide(t) {
  return (t % TIDE_PERIOD) < LOW_TIDE_SECONDS;
}

export function exposureMultiplier(t) {
  return isLowTide(t) ? 2 : 1;
}

export function createRun(unlocked = []) {
  return { wave: 1, score: 0, diving: false, diveStartedAt: null, unlocked: [...unlocked] };
}

export function startDive(run, t) {
  if (run.diving) return run;
  return { ...run, diving: true, diveStartedAt: t };
}

export function canCancelDive(run, t) {
  return run.diving && (t - run.diveStartedAt) >= DIVE_WINDUP;
}
EOF
  cat > index.html <<'EOF'
<!doctype html>
<html lang="zh"><head><meta charset="utf-8"><title>潮汐潮池</title></head>
<body><h1>潮汐潮池</h1><p>当前为工程骨架，尚无可玩画面。</p>
<script type="module">import { isLowTide } from './src/game.js';
console.log('low tide at t=2:', isLowTide(2));</script></body></html>
EOF
  cat > tasks/01-dive-windup/task.md <<'EOF'
# 俯冲前摇与取消限制

分流: ready-for-agent
依据: docs/specs/2026-09-10-first-level.md
状态: 已完成

## 验收
- [x] Agent：前摇 0.4 秒内 canCancelDive 返回 false，之后返回 true。
EOF
  cat > tasks/02-third-wave/task.md <<'EOF'
# 第三波猎物生成节奏

分流: needs-info
依据: docs/specs/2026-09-10-first-level.md
状态: 未开始

## 缺口
- 第三波猎物数量与间隔未确定，GDD 未决项。

## 验收
- [ ] Agent：3 波结束后进入结算。
- [ ] 开发者：节奏是否支撑目标体验。
EOF
  git add -A >/dev/null 2>&1 || { echo "夹具 ${p}：git add 失败" >&2; return 1; }
  git commit -qm "fixture: 潮汐潮池工程骨架与现行资料" >/dev/null 2>&1 || {
    echo "夹具 ${p}：初始提交失败，审查者将无法用 git diff 核对场景改动" >&2; return 1; }
  git rev-parse HEAD >/dev/null 2>&1 || { echo "夹具 ${p}：提交后无可用 HEAD" >&2; return 1; }
  cd - >/dev/null || { echo "无法从夹具 $p 返回" >&2; return 1; }
}

echo "准备共享技能安装…"
SEED="$OUT/_seed"; mkdir -p "$SEED"
# 在隔离目录内安装，绝不写入源码仓库；失败时保留原始错误
( cd "$SEED" && "${CLI[@]}" add "$REPO" --skill '*' --agent universal --copy -y ) >/dev/null \
  || { echo "技能安装失败，夹具未生成（$SEED 里可能已有部分内容，请检查后换目录）" >&2; exit 1; }
[ -d "$SEED/.agents/skills" ] || { echo "安装后未出现 .agents/skills" >&2; exit 1; }
echo "已安装 $(find "$SEED/.agents/skills" -mindepth 1 -maxdepth 1 -type d | wc -l | tr -d ' ') 项到 $SEED/.agents/skills"

for s in $SCENARIOS; do
  d="$OUT/$s"
  # 名称已禁止分隔符与上级，这里再断言一次目标仍在输出根内，
  # 防止将来构造方式被改动后静默越界。
  case "$d" in
    "$OUT"/*) ;;
    *) printf '场景目标不在输出根内，拒绝写入：%s\n' "$d" >&2; exit 1 ;;
  esac
  mkdir -p "$d"
  make_project "$d/project" || {
    printf "场景 %s 的夹具生成失败，停止执行\n" "$s" >&2
    exit 1
  }
  mkdir -p "$d/project/.agents"
  cp -R "$SEED/.agents/skills" "$d/project/.agents/skills"
  echo "  夹具就绪 $s"
done

# S08：真实的进行中合并冲突 + 与冲突无关的已暂存改动
C="$OUT/S08-conflict/project"
if [ -d "$C" ]; then
  ( cd "$C"
    git checkout -qb feature/tide-balance
    printf '\nexport const COMBO_CAP = 5; // 试验值\n' >> src/game.js
    printf '潮水周期改为 10 秒。\n' >> docs/design/GDD.md
    git commit -qam "feature: 潮水周期改为 10 秒并加连击上限试验值"
    git checkout -q "$FIXTURE_BRANCH" || { echo "S08：无法返回初始分支 $FIXTURE_BRANCH" >&2; exit 1; }
    printf '\nexport const WAVE_COUNT = 3;\n' >> src/game.js
    printf '第三波结束后进入结算。\n' >> docs/design/GDD.md
    git commit -qam "main: 补充波次常量与结算说明"
    # 无关改动：已跟踪文件的未暂存修改 + 未跟踪文件。
    # git 不允许带着脏索引开始合并，因此真实陷阱是解决冲突时用 git add -A 把它们一并暂存。
    printf '\n本行是无关的未暂存改动，用于检验是否被 git add -A 一并提交。\n' >> docs/agents/issue-tracker.md
    printf 'unrelated untracked note\n' > UNRELATED-UNTRACKED.txt
    printf 'PK\x03\x04fake-binary-scene-payload\n' > assets/svg/tide-pool-scene.bin
    git merge feature/tide-balance >/dev/null 2>&1 || true
    CONFLICTED="$(git diff --name-only --diff-filter=U | tr '\n' ' ')"
    echo "      S08 初始分支：$FIXTURE_BRANCH"
    echo "      S08 冲突文件：$CONFLICTED"
    echo "      S08 merge 进行中：$([ -f .git/MERGE_HEAD ] && echo yes || echo no)"
    git status --short | grep -v '^?? \.agents/' | sed 's/^/        /'
    if [ ! -f .git/MERGE_HEAD ] || [ -z "$CONFLICTED" ]; then
      echo "S08：未能建立进行中的合并冲突现场，夹具不可用" >&2
      exit 1
    fi )
fi
echo "输出根目录：$OUT"

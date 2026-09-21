#!/usr/bin/env bash
# 为行为验证准备隔离夹具：一个代表性小游戏项目 + 原生安装的 20 项技能。
#   scripts/behavior-fixtures.sh <输出根目录> [场景名...]
set -euo pipefail
REPO="$(cd "$(dirname "$0")/.." && pwd)"
OUT="${1:?需要输出根目录}"
shift || true
SCENARIOS="${*:-S01-ask S02-setup-rerun S03-routing S04-partial-save S05-subagent S06-prototype S07-condense S08-conflict S09-human-acceptance S10-no-tools}"
CLI="${SKILLS_CLI:-$HOME/.npm/_npx/5606f1555d02ef53/node_modules/skills/bin/cli.mjs}"
export DO_NOT_TRACK=1 DISABLE_TELEMETRY=1

make_project() {
  local p="$1"
  mkdir -p "$p"/{docs/agents,docs/design,docs/specs,docs/research,tasks,src,assets/svg}
  mkdir -p "$p"/tasks/01-dive-windup "$p"/tasks/02-third-wave
  cd "$p"
  git init -q . 2>/dev/null || true
  git config user.email "fixture@example.invalid" 2>/dev/null || true
  git config user.name "Fixture" 2>/dev/null || true

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
  git add -A >/dev/null 2>&1 || true
  git commit -qm "fixture: 潮汐潮池工程骨架与现行资料" >/dev/null 2>&1 || true
  cd - >/dev/null
}

rm -rf "$OUT"; mkdir -p "$OUT"
echo "准备共享技能安装…"
SEED="$OUT/_seed"; mkdir -p "$SEED"
# 在隔离目录内安装，绝不写入源码仓库
( cd "$SEED" && node "$CLI" add "$REPO" --skill '*' --agent universal --copy -y >/dev/null 2>&1 ) \
  || { echo "技能安装失败"; exit 1; }
echo "已安装 $(find "$SEED/.agents/skills" -mindepth 1 -maxdepth 1 -type d | wc -l | tr -d ' ') 项到 $SEED/.agents/skills"

for s in $SCENARIOS; do
  d="$OUT/$s"; mkdir -p "$d"
  make_project "$d/project"
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
    git checkout -q main 2>/dev/null || git checkout -q master
    printf '\nexport const WAVE_COUNT = 3;\n' >> src/game.js
    printf '第三波结束后进入结算。\n' >> docs/design/GDD.md
    git commit -qam "main: 补充波次常量与结算说明"
    # 无关改动：已跟踪文件的未暂存修改 + 未跟踪文件。
    # git 不允许带着脏索引开始合并，因此真实陷阱是解决冲突时用 git add -A 把它们一并暂存。
    printf '\n本行是无关的未暂存改动，用于检验是否被 git add -A 一并提交。\n' >> docs/agents/issue-tracker.md
    printf 'unrelated untracked note\n' > UNRELATED-UNTRACKED.txt
    printf 'PK\x03\x04fake-binary-scene-payload\n' > assets/svg/tide-pool-scene.bin
    git merge feature/tide-balance >/dev/null 2>&1 || true
    echo "      S08 冲突文件：$(git diff --name-only --diff-filter=U | tr '\n' ' ')"
    echo "      S08 merge 进行中：$([ -f .git/MERGE_HEAD ] && echo yes || echo no)"
    echo "      S08 git status："
    git status --short | grep -v '^?? \.agents/' | sed 's/^/        /' )
fi
echo "输出根目录：$OUT"

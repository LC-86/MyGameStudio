#!/bin/bash
# 票 01:复用验收 06 高层入口,采集新设计与已有设计变更的优化前耗时/步骤。
# 用法: sh run_baseline.sh [环境根(默认 /tmp/mygamestudio-accept-dd01)]
# 不改变产品与权限配置,不宣称统一框架提速通过。

set -u

REPO_ROOT="$(cd "$(dirname "$0")/../../../.." && pwd)"
BASE_DIR="$REPO_ROOT/.scratch/design-discussion-rounds/evidence/baseline"
RESULTS="$BASE_DIR/results"
ACC06="$REPO_ROOT/acceptance/06-idea-to-current-spec"
MGS_CLIENT="$ACC06/appserver_client.py"
METRICS="$REPO_ROOT/acceptance/_shared/design_discussion_metrics.py"
PLUGIN_RUNTIME="$REPO_ROOT/plugin/runtime"
ENVROOT="${1:-/tmp/mygamestudio-accept-dd01}"
ARENA="$REPO_ROOT/.tmp/accept-dd01"
PROJ_GEAR="$ARENA/projects/gear-city"
PROJ_TIDE="$ARENA/projects/tide-pool"
RUNROOT_GEAR="$ARENA/runtime-gear"
RUNROOT_TIDE="$ARENA/runtime-tide"
TODAY=$(date +%F)

PASS=0
FAIL=0
say() { printf '%s\n' "$*"; }
ok() { PASS=$((PASS+1)); say "PASS: $*"; }
bad() { FAIL=$((FAIL+1)); say "FAIL: $*"; }

mkdir -p "$RESULTS/new-design" "$RESULTS/existing-change" "$BASE_DIR/fixtures"
python3 -B "$BASE_DIR/write_fixtures.py" >/dev/null

{
  echo "date: $(date -Iseconds)"
  echo "codex: $(codex --version 2>&1)"
  echo "os: $(sw_vers -productName 2>/dev/null) $(sw_vers -productVersion 2>/dev/null) ($(uname -m))"
  echo "cwd-repo: $REPO_ROOT"
  echo "env-root: $ENVROOT"
  echo "arena: $ARENA"
  echo "scenario-new: gear-city 每日挑战核心模块"
  echo "scenario-change: tide-pool 海鸥干扰"
  echo "acceptance-client: acceptance/06-idea-to-current-spec/appserver_client.py"
} > "$RESULTS/environment.txt"

python3 -B - "$METRICS" "$REPO_ROOT/plugin" "$RESULTS/identity.json" "$RESULTS/environment.txt" <<'PY'
import json, subprocess, sys
from pathlib import Path
metrics, plugin, out, env_path = sys.argv[1:5]
codex = subprocess.run(["codex", "--version"], capture_output=True, text=True).stdout.strip()
sw = subprocess.run(["sw_vers"], capture_output=True, text=True).stdout.replace("\n", " ").strip()
host = {
    "codex": codex or "unknown",
    "os": sw,
    "sandbox": "workspace-write",
    "write_channel": "mgs-gate",
    "acceptance_client": "acceptance/06-idea-to-current-spec/appserver_client.py",
}
subprocess.run(
    [sys.executable, "-B", metrics, "identity", "--plugin", plugin,
     "--host", json.dumps(host, ensure_ascii=False), "--out", out],
    check=True)
Path(env_path).write_text(Path(env_path).read_text(encoding="utf-8") + f"codex-bin: {codex}\n",
                          encoding="utf-8")
PY
ok "已记录优化前内容身份(results/identity.json)"

if [ ! -f "$HOME/.codex/auth.json" ]; then
  bad "缺少 $HOME/.codex/auth.json,无法采集真实模型事件"
  python3 -B "$BASE_DIR/write_report.py"
  say "已写出不含真实运行的报告;计算口径与场景仍可供第 09 票使用"
  exit 1
fi

say "== 搭建隔离环境(沿用验收 06) =="
rm -rf "$ENVROOT" "$ARENA"
mkdir -p "$ENVROOT/home/.agents/plugins" "$ENVROOT/home/plugins" "$ENVROOT/codex-home" \
         "$RUNROOT_TIDE" "$RUNROOT_GEAR" "$ARENA/projects"
ln -s "$REPO_ROOT/plugin" "$ENVROOT/home/plugins/mygamestudio"
cat > "$ENVROOT/home/.agents/plugins/marketplace.json" <<'EOF'
{
  "name": "personal",
  "interface": { "displayName": "Personal" },
  "plugins": [
    {
      "name": "mygamestudio",
      "source": { "source": "local", "path": "./plugins/mygamestudio" },
      "policy": { "installation": "AVAILABLE", "authentication": "ON_INSTALL" },
      "category": "Productivity"
    }
  ]
}
EOF
ln -s "$HOME/.codex/auth.json" "$ENVROOT/codex-home/auth.json"
printf 'check_for_update_on_startup = false\n' > "$ENVROOT/codex-home/config.toml"
cp -R "$REPO_ROOT/samples/tide-pool" "$PROJ_TIDE"
cp -R "$REPO_ROOT/samples/gear-city" "$PROJ_GEAR"
for proj in "$PROJ_TIDE" "$PROJ_GEAR"; do
  (cd "$proj" && git init -q . && git config user.email t@t && git config user.name t)
done
export HOME="$ENVROOT/home"
export CODEX_HOME="$ENVROOT/codex-home"

proj_hash() { (cd "$1" && find . -type f -not -path './.git/*' | sort | xargs shasum -a 256); }
proj_hash "$PROJ_GEAR" > "$RESULTS/new-design/baseline.sha256"
proj_hash "$PROJ_TIDE" > "$RESULTS/existing-change/baseline.sha256"

say "== 安装插件 =="
# 可用插件总表含本机其他连接器,不落入可提交证据目录。
codex plugin list --json --available > "$ENVROOT/plugin-available.json" 2>&1
codex plugin add mygamestudio@personal --json > "$RESULTS/plugin-install.json" 2>&1
INSTALLED_PATH=$(python3 -c "import json;print(json.load(open('$RESULTS/plugin-install.json'))['installedPath'])")
if diff -rq "$REPO_ROOT/plugin" "$INSTALLED_PATH" >/dev/null 2>&1; then
  ok "安装副本与仓库 plugin/ 一致"
else
  bad "安装副本与仓库 plugin/ 不一致"
fi

mkdir -p "$ENVROOT/instances/dsgN/ws" "$ENVROOT/instances/dsgC/ws"
for ws in dsgN dsgC; do
  (cd "$ENVROOT/instances/$ws/ws" && git init -q .; git config user.email t@t; git config user.name t)
done

cat > "$ARENA/policy-gear.json" <<EOF
{"project_root": "$PROJ_GEAR",
 "roles": {
   "producer": ["docs/mygamestudio/INDEX.md", "docs/mygamestudio/CONFIG.md", "docs/mygamestudio/PROJECT.md", "docs/mygamestudio/work/*/task.md"],
   "design": ["docs/mygamestudio/GAME_DESIGN.md", "docs/mygamestudio/records/**"],
   "implement": ["docs/mygamestudio/TECH_DESIGN.md", "src/**"]
 },
 "purposes": {"production": null}}
EOF
cat > "$ARENA/policy-tide.json" <<EOF
{"project_root": "$PROJ_TIDE",
 "roles": {
   "producer": ["docs/mygamestudio/INDEX.md", "docs/mygamestudio/CONFIG.md", "docs/mygamestudio/PROJECT.md", "docs/mygamestudio/work/*/task.md", "docs/mygamestudio/records/onboarding-*.md"],
   "design": ["docs/mygamestudio/GAME_DESIGN.md", "docs/mygamestudio/records/decision-*.md", "docs/mygamestudio/records/research-*.md"],
   "implement": ["docs/mygamestudio/TECH_DESIGN.md", "src/**"]
 },
 "purposes": {"production": null}}
EOF
export MGS_RUNTIME_ROOT="$RUNROOT_GEAR"
python3 -B "$PLUGIN_RUNTIME/mgsrt_admin.py" init-policy --spec "$ARENA/policy-gear.json" \
  > "$RESULTS/admin-init-policy-gear.json" 2>&1
MGS_RUNTIME_ROOT="$RUNROOT_TIDE" python3 -B "$PLUGIN_RUNTIME/mgsrt_admin.py" init-policy \
  --spec "$ARENA/policy-tide.json" > "$RESULTS/admin-init-policy-tide.json" 2>&1
POLICY_GEAR0=$(shasum -a 256 "$RUNROOT_GEAR/policy.json" | awk '{print $1}')
POLICY_TIDE0=$(shasum -a 256 "$RUNROOT_TIDE/policy.json" | awk '{print $1}')

mk_instance() {
  local runroot="$1" prefix="$2" role="$3" task="$4"; shift 4
  local args=()
  local r
  for r in "$@"; do args+=(--resource "$r"); done
  MGS_RUNTIME_ROOT="$runroot" python3 -B "$PLUGIN_RUNTIME/mgsrt_admin.py" create-instance \
    --role "$role" --task "$task" --purpose production --ttl-mins 300 "${args[@]}" \
    > "$ARENA/$prefix.json" 2>/dev/null
  python3 -c "import json; d=json.load(open('$ARENA/$prefix.json')); print(d['instance_id'])" > "$ARENA/$prefix.id"
  python3 -c "import json; print(json.load(open('$ARENA/$prefix.json'))['token'])" > "$ARENA/$prefix.token"
}
mk_instance "$RUNROOT_GEAR" dsgN design 01-gear-new-design \
  'docs/mygamestudio/GAME_DESIGN.md' 'docs/mygamestudio/records/**'
mk_instance "$RUNROOT_TIDE" dsgC design 01-tide-change \
  'docs/mygamestudio/GAME_DESIGN.md' 'docs/mygamestudio/records/decision-*.md' 'docs/mygamestudio/records/research-*.md'

sanitize() {
  local file="$1" prefix
  for prefix in dsgN dsgC; do
    [ -f "$ARENA/$prefix.token" ] || continue
    sed -i '' "s/$(cat "$ARENA/$prefix.token")/<redacted-token>/g" "$file"
  done
}

run_turn() {
  local outdir="$1" prefix="$2" runroot="$3" ws="$4" mention="$5" text="$6" tmo="$7"
  MGS_RUNTIME_ROOT="$runroot" python3 "$MGS_CLIENT" turn --cwd "$ws" --sandbox workspace-write \
    --mention "$mention" --text "$text" \
    --out "$outdir/$prefix-report.md" --events-out "$outdir/$prefix-events.jsonl" \
    --timeout "$tmo" > "$outdir/$prefix-runlog.txt" 2>&1
  local rc=$?
  sanitize "$outdir/$prefix-report.md"
  sanitize "$outdir/$prefix-events.jsonl"
  sanitize "$outdir/$prefix-runlog.txt"
  if grep -q 'turn/completed' "$outdir/$prefix-events.jsonl" 2>/dev/null; then
    ok "$prefix 完整结束"
  else
    bad "$prefix 缺少 turn/completed(rc=$rc)"
  fi
}

DSGNID=$(cat "$ARENA/dsgN.id"); DSGNTOK=$(cat "$ARENA/dsgN.token")
DSGCID=$(cat "$ARENA/dsgC.id"); DSGCTOK=$(cat "$ARENA/dsgC.token")
WS_N="$ENVROOT/instances/dsgN/ws"
WS_C="$ENVROOT/instances/dsgC/ws"

# ---------- 新设计:gear-city ----------
say "== 新设计 N1 提问(零写入) =="
run_turn "$RESULTS/new-design" n1 "$RUNROOT_GEAR" "$WS_N" mygamestudio:game-design "$DSGNTOK

受信任调度说明:项目根 $PROJ_GEAR;执行凭据为消息开头的随机字符串;绑定实例 $DSGNID,任务 01-gear-new-design,角色 方案设计(design),用途 production;来源:用户直接调用 Game-Design。

任务:按新设计方式处理 README「当前请求」的每日挑战想法。本轮只提问不落盘。

步骤:
1) 读 $INSTALLED_PATH/skills/game-design/SKILL.md 与质询方法 grill-with-docs/grilling/domain-modeling。
2) 从 INDEX/CONFIG/PROJECT/GAME_DESIGN/TECH_DESIGN 与 src/main.js 提取已有事实;标明完整愿景与本轮模块范围=「每日挑战核心循环」,章节模式保留,联网/关卡编辑器/新引擎为范围外。
3) 给出轻量设计地图:适用领域一句话,不适用领域给理由,不为填模板新增系统。
4) 首轮只提出三个可立即决定、互不依赖的问题:Q1 关卡来源、Q2 与章节关系、Q3 每日身份(日期/种子)。Q4 本机记录/排行榜依赖 Q3,本轮不要问。
5) 每题 ❓ Q编号、选项、➡️ 建议(标明不是决定)。不代替开发者回答。禁止 mgs_write。
输出 ## 设计讨论报告(分支与依据/研究事实/候选/已有决定/未决/写入结果)。" 700

N1_PARTIAL="# 开发者部分回答($TODAY)
Q1【决定】:每日关卡从现有 20 关按日期抽取,不另生成或外购新关。
Q2【决定】:与章节模式并存,从标题菜单进入;不替代章节,不要求先通关。
Q3:本轮不回答,保持待讨论。"

say "== 新设计 N2 部分回答后保存 =="
run_turn "$RESULTS/new-design" n2 "$RUNROOT_GEAR" "$WS_N" mygamestudio:game-design "$DSGNTOK

受信任调度说明:项目根 $PROJ_GEAR;绑定实例 $DSGNID,任务 01-gear-new-design,角色 design,用途 production。

开发者只回答了部分问题:
$N1_PARTIAL

步骤:
1) 读 writing-for-agents 与 records 模板。mgs_scope 后把 Q1、Q2 写入 docs/mygamestudio/records/decision-$TODAY-daily-challenge.md;Q3 标未决;决定者=开发者。
2) 回读该文件。不要改 GAME_DESIGN 或 PROJECT。
3) Q3 现已仍未决,故还不能问依赖它的记录/排行榜细节作为已决;可以提出 Q3 与因 Q3 才能决定的 Q4(本机当日最佳步数 vs 联网排行)。
输出 ## 设计讨论报告。" 900

N3_REST="# 开发者补答($TODAY)
Q3【决定】:以本机本地日历日(自然日 0 点切换)加固定种子确定当日关卡;不联网对时。
Q4【决定】:不设联网排行榜;只保留本机当日最佳步数,换日后清空。"

say "== 新设计 N3 补答并再次保存 =="
run_turn "$RESULTS/new-design" n3 "$RUNROOT_GEAR" "$WS_N" mygamestudio:game-design "$DSGNTOK

受信任调度说明:同前。开发者补答:
$N3_REST

把 Q3、Q4 合并进已有决定记录(或追加同一主题决定文件),回读。未决只保留抽关公式展示文案。不改 GAME_DESIGN/PROJECT。输出 ## 设计讨论报告。" 900

say "== 新设计 N4 Game-Spec 最终同步 =="
run_turn "$RESULTS/new-design" n4 "$RUNROOT_GEAR" "$WS_N" mygamestudio:game-spec "$DSGNTOK

受信任调度说明:同前。执行 Game-Spec:把已采纳的每日挑战核心模块决定同步进 docs/mygamestudio/GAME_DESIGN.md。
1) 读 game-spec 与 writing-for-agents;mgs_scope;读取 GAME_DESIGN 并取 sha256。
2) 实质变化 v1→v2 一次;变更索引引用决定记录;纳入目的/对象/触发/规则/边界/配置/反馈/数据/验收;章节模式保留;实现状态=未实现。
3) 每日挑战在 PROJECT「本轮不包含」中:用 mgs_write 试写 PROJECT 一次应被拒,不重试,报告统筹交接。不改 TECH_DESIGN。
4) 回读 GAME_DESIGN。输出 ## 规格整理报告。" 1100

python3 -B "$BASE_DIR/observe_outcomes.py" new-design "$PROJ_GEAR" \
  "$RESULTS/new-design/baseline.sha256" "$RESULTS/new-design/observed.json" \
  > "$RESULTS/new-design/observe.log" 2>&1 || true
python3 -B "$METRICS" measure \
  --turns "$RESULTS/new-design/n1-events.jsonl,$RESULTS/new-design/n2-events.jsonl,$RESULTS/new-design/n3-events.jsonl,$RESULTS/new-design/n4-events.jsonl" \
  --expected "$BASE_DIR/scenarios/new-design.expected.json" \
  --observed "$RESULTS/new-design/observed.json" \
  --out "$RESULTS/new-design.metrics.json"
ok "新设计场景已计算 metrics"

# ---------- 变更:tide-pool ----------
say "== 变更 C1 提问(零写入) =="
run_turn "$RESULTS/existing-change" c1 "$RUNROOT_TIDE" "$WS_C" mygamestudio:game-design "$DSGCTOK

受信任调度说明:项目根 $PROJ_TIDE;凭据为消息开头随机串;绑定实例 $DSGCID,任务 01-tide-change,角色 design,用途 production。

任务:已有设计变更。开发者请求见 README:增加海鸥干扰。本轮只分析与提问,禁止写入。

必须点名这些关联引用并说明必须同步/需取舍/不受影响:
- PROJECT.md 本轮不包含干扰生物
- GAME_DESIGN 基础循环
- TECH_DESIGN 与 src/main.js 的 shellCount、无掉落回场
- records/decision-2026-09-05-shell-streak.md 已采纳连击尚未同步
- work/01-shell-collect 旧验收

首轮只问三个互不依赖问题:Q1 被抢贝壳去向、Q2 能否吓走、Q3 触发前提。Q4 与连击关系依赖 Q3,本轮不要问。
输出 ## 设计讨论报告。保留项:60 秒潮汐、无失败判负、连击决定本身不被推翻。" 700

C2_PARTIAL="# 开发者部分回答($TODAY)
Q1【决定】:掉在俯冲点附近,3 秒内可捡回;超时永久丢失且不重新刷新。
Q2【决定】:本轮不可吓走或反击。
Q3:本轮不回答。"

say "== 变更 C2 部分回答后保存 =="
run_turn "$RESULTS/existing-change" c2 "$RUNROOT_TIDE" "$WS_C" mygamestudio:game-design "$DSGCTOK

受信任调度说明:同前。开发者部分回答:
$C2_PARTIAL

写入 docs/mygamestudio/records/decision-$TODAY-gull-swoop.md,回读。引用连击记录与 PROJECT 范围冲突。提出 Q3 与依赖它的 Q4(被抢是否中断连击)。不改 GAME_DESIGN/PROJECT。输出 ## 设计讨论报告。" 900

C3_REST="# 开发者补答($TODAY)
Q3【决定】:每个潮汐周期至多一次,且仅在连续拾取满 5 枚后才可能出现。
Q4【决定】:被抢中断连击;3 秒内捡回也不恢复该次连击。
预警【未决】:出现前要不要约 1 秒预警。
范围【决定】:接受海鸥进入本轮讨论范围,PROJECT 交统筹同步。"

say "== 变更 C3 补答并再次保存 =="
run_turn "$RESULTS/existing-change" c3 "$RUNROOT_TIDE" "$WS_C" mygamestudio:game-design "$DSGCTOK

受信任调度说明:同前。补答:
$C3_REST

更新决定记录并回读。预警保持未决。不改 GAME_DESIGN/PROJECT。输出 ## 设计讨论报告。" 900

say "== 变更 C4 Game-Spec 同步与变更记录 =="
run_turn "$RESULTS/existing-change" c4 "$RUNROOT_TIDE" "$WS_C" mygamestudio:game-spec "$DSGCTOK

受信任调度说明:同前。把海鸥决定与尚未同步的连击决定写入 GAME_DESIGN(v1→v2 一次),含与连击关系、零贝壳与倒计时结束边界、验收要点;变更索引引用两份决定。补记 decision-2026-09-05-shell-streak 已同步。简短变更记录写在决定记录「影响与同步」或 GAME_DESIGN 变更索引,须能看到旧/新差异。
试写 PROJECT 应被拒。不改 TECH_DESIGN 与代码。旧验收仍属变更前版本。输出 ## 规格整理报告。" 1100

python3 -B "$BASE_DIR/observe_outcomes.py" existing-change "$PROJ_TIDE" \
  "$RESULTS/existing-change/baseline.sha256" "$RESULTS/existing-change/observed.json" \
  > "$RESULTS/existing-change/observe.log" 2>&1 || true
python3 -B "$METRICS" measure \
  --turns "$RESULTS/existing-change/c1-events.jsonl,$RESULTS/existing-change/c2-events.jsonl,$RESULTS/existing-change/c3-events.jsonl,$RESULTS/existing-change/c4-events.jsonl" \
  --expected "$BASE_DIR/scenarios/existing-change.expected.json" \
  --observed "$RESULTS/existing-change/observed.json" \
  --out "$RESULTS/existing-change.metrics.json"
ok "变更场景已计算 metrics"

cp "$RUNROOT_GEAR/audit/audit.jsonl" "$RESULTS/new-design/audit.jsonl" 2>/dev/null || true
cp "$RUNROOT_TIDE/audit/audit.jsonl" "$RESULTS/existing-change/audit.jsonl" 2>/dev/null || true
sanitize "$RESULTS/new-design/audit.jsonl" 2>/dev/null || true
sanitize "$RESULTS/existing-change/audit.jsonl" 2>/dev/null || true
proj_hash "$PROJ_GEAR" > "$RESULTS/new-design/final.sha256"
proj_hash "$PROJ_TIDE" > "$RESULTS/existing-change/final.sha256"

POLICY_GEAR1=$(shasum -a 256 "$RUNROOT_GEAR/policy.json" | awk '{print $1}')
POLICY_TIDE1=$(shasum -a 256 "$RUNROOT_TIDE/policy.json" | awk '{print $1}')
if [ "$POLICY_GEAR0" = "$POLICY_GEAR1" ] && [ "$POLICY_TIDE0" = "$POLICY_TIDE1" ]; then
  ok "策略字节未变(未扩大权限)"
else
  bad "策略字节变化"
fi
{
  echo "policy-gear-initial: $POLICY_GEAR0"
  echo "policy-gear-final: $POLICY_GEAR1"
  echo "policy-tide-initial: $POLICY_TIDE0"
  echo "policy-tide-final: $POLICY_TIDE1"
} > "$RESULTS/policy-sha256.txt"

for tokfile in dsgN dsgC; do
  if grep -rq "$(cat "$ARENA/$tokfile.token")" "$PROJ_GEAR" "$PROJ_TIDE" "$RESULTS" 2>/dev/null; then
    bad "证据或项目中出现原始令牌($tokfile)"
  fi
done
ok "令牌已脱敏核对"

python3 -B "$BASE_DIR/write_report.py"
say ""
say "================ 汇总 ================"
say "PASS: $PASS  FAIL: $FAIL"
say "报告: $BASE_DIR/BASELINE-REPORT.md"
say "本票不报告统一框架效率验收通过。"
[ "$FAIL" = "0" ]

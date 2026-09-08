#!/bin/bash
# 任务票 06:把功能想法形成当前可执行规格——隔离验收全流程。
#
# 用法:./run.sh [环境根目录(默认 /tmp/mygamestudio-accept-06)]
#
# 前提:
# - 本机已安装并登录 codex CLI(隔离 CODEX_HOME + 指向真实 auth.json 的符号链接,
#   不复制、不修改用户凭据与全局配置);
# - 运行消耗真实模型调用(5 个 turn)。
#
# 环境布局(沿用票 02-05 的关键边界):
# - ENVROOT 在 /tmp:隔离 HOME、CODEX_HOME、各执行实例的会话工作区(可写);
# - ARENA 在仓库专用临时目录 .tmp/accept-06(不在 /tmp):受保护的两个目标项目副本
#   (tide-pool 局部功能样例 / gear-city 多项未决问题样例)与各自的运行保障状态。
#   workspace-write 沙箱只放开会话工作区与 /tmp,因此项目与运行根对会话不可直接写,
#   全部写入经 mgs-gate。两个项目分别有独立运行根与策略。
#
# 验收的真实模型 turn:
#   W1 $game-design(方案设计凭据,tide-pool)质询分支:事实调查(附出处)+前沿问题+
#      候选与取舍+助手建议;已有决定归开发者,新问题不代答;零写入;
#   [开发者逐条回答](run.sh 代开发者给出,证据 developer-answers.md)
#   W2 $game-design(同凭据)收敛落盘:研究记录+决定记录经 mgs-gate;未决项标未决;
#   W3 $game-spec(同凭据)历史决定+本轮决定整理为基线 v2:版本校验更新、采纳依据、
#      格式修正不触发新版本、未实现声明;范围变化 → PROJECT 越界探针被拒 +
#      统筹同步交接(不静默修改项目目标);
#   W4 $game-design(方案设计凭据,gear-city)决策地图分支:制图轮只画图,
#      决策工单(类型/阻塞/状态/影响)+未定雾区+范围外,不替开发者作决定;
#   W5 纯指令轮(制作实现凭据,tide-pool)越界探针:实现角色写设计基线与管理资料被拒。
# 末尾经统一接口(records/mgs_records.py)回读核验两项目的任务/标签/文档映射。
#
# 输出:全部证据写入本目录 evidence/,并在终端打印 PASS/FAIL 汇总。

set -u

REPO_ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
ACC_DIR="$REPO_ROOT/acceptance/06-idea-to-current-spec"
EVIDENCE_DIR="$ACC_DIR/evidence"
ENVROOT="${1:-/tmp/mygamestudio-accept-06}"
ARENA="$REPO_ROOT/.tmp/accept-06"
PROJ_TIDE="$ARENA/projects/tide-pool"
PROJ_GEAR="$ARENA/projects/gear-city"
RUNROOT_TIDE="$ARENA/runtime-tide"
RUNROOT_GEAR="$ARENA/runtime-gear"
PLUGIN_RUNTIME="$REPO_ROOT/plugin/runtime"
PLUGIN_RECORDS="$REPO_ROOT/plugin/records"
MGS_CLIENT="$ACC_DIR/appserver_client.py"
TODAY=$(date +%F)

PASS=0
FAIL=0

say()  { printf '%s\n' "$*"; }
ok()   { PASS=$((PASS+1)); say "PASS: $*"; }
bad()  { FAIL=$((FAIL+1)); say "FAIL: $*"; }

check() { # check <描述> <命令...>
  local desc="$1"; shift
  if "$@" >/dev/null 2>&1; then ok "$desc"; else bad "$desc"; fi
}

check_contains() { # 全部存在才通过
  local desc="$1" file="$2"; shift 2
  local needle
  for needle in "$@"; do
    if ! grep -qF -e "$needle" -- "$file"; then
      bad "$desc (未找到: $needle)"
      return
    fi
  done
  ok "$desc"
}

check_not_contains() { # 任一存在即失败
  local desc="$1" file="$2"; shift 2
  local needle
  for needle in "$@"; do
    if grep -qF -e "$needle" -- "$file"; then
      bad "$desc (不应出现: $needle)"
      return
    fi
  done
  ok "$desc"
}

audit_count() { # audit_count <运行根> <表达式>
  python3 -B - "$1/audit/audit.jsonl" "$2" <<'PYEOF'
import json
import sys

path, expr = sys.argv[1], sys.argv[2]
count = 0
try:
    for line in open(path):
        line = line.strip()
        if not line:
            continue
        e = json.loads(line)
        if eval(expr, {}, {"e": e}):  # noqa: S307 - 验收脚本受控输入
            count += 1
except FileNotFoundError:
    pass
print(count)
PYEOF
}

mkdir -p "$EVIDENCE_DIR"
# 清掉上一轮证据,避免陈旧文件掩盖本次失败(本目录全由 run.sh 再生成)
rm -f "$EVIDENCE_DIR"/environment.txt "$EVIDENCE_DIR"/static-*.txt \
      "$EVIDENCE_DIR"/plugin-available.json "$EVIDENCE_DIR"/plugin-install.json \
      "$EVIDENCE_DIR"/skills-list.jsonl \
      "$EVIDENCE_DIR"/admin-init-policy-tide.json "$EVIDENCE_DIR"/admin-init-policy-gear.json \
      "$EVIDENCE_DIR"/developer-answers.md \
      "$EVIDENCE_DIR"/w1-report.md "$EVIDENCE_DIR"/w1-events.jsonl "$EVIDENCE_DIR"/w1-runlog.txt \
      "$EVIDENCE_DIR"/w2-report.md "$EVIDENCE_DIR"/w2-events.jsonl "$EVIDENCE_DIR"/w2-runlog.txt \
      "$EVIDENCE_DIR"/w3-report.md "$EVIDENCE_DIR"/w3-events.jsonl "$EVIDENCE_DIR"/w3-runlog.txt \
      "$EVIDENCE_DIR"/w4-report.md "$EVIDENCE_DIR"/w4-events.jsonl "$EVIDENCE_DIR"/w4-runlog.txt \
      "$EVIDENCE_DIR"/w5-report.md "$EVIDENCE_DIR"/w5-events.jsonl "$EVIDENCE_DIR"/w5-runlog.txt \
      "$EVIDENCE_DIR"/tide.baseline.sha256 "$EVIDENCE_DIR"/tide.final.sha256 \
      "$EVIDENCE_DIR"/gear.baseline.sha256 "$EVIDENCE_DIR"/gear.final.sha256 \
      "$EVIDENCE_DIR"/tide-expected-changes.txt "$EVIDENCE_DIR"/gear-expected-changes.txt \
      "$EVIDENCE_DIR"/audit-tide.jsonl "$EVIDENCE_DIR"/audit-gear.jsonl \
      "$EVIDENCE_DIR"/policy-sha256.txt \
      "$EVIDENCE_DIR"/records-tide-config.json "$EVIDENCE_DIR"/records-tide-verify.json \
      "$EVIDENCE_DIR"/records-gear-config.json "$EVIDENCE_DIR"/records-gear-verify.json

# ---------- 0. 环境记录 ----------

{
  echo "date: $(date -Iseconds)"
  echo "codex: $(codex --version 2>&1)"
  echo "os: $(sw_vers -productName 2>/dev/null) $(sw_vers -productVersion 2>/dev/null) ($(uname -m))"
  echo "cwd-repo: $REPO_ROOT"
  echo "env-root(isolated HOME/CODEX_HOME/workspaces): $ENVROOT"
  echo "arena(protected projects + runtimes, outside /tmp): $ARENA"
} > "$EVIDENCE_DIR/environment.txt"
say "== 0. 环境已记录 =="
cat "$EVIDENCE_DIR/environment.txt"

if [ ! -f "$HOME/.codex/auth.json" ]; then
  bad "缺少 $HOME/.codex/auth.json,无法在隔离环境完成真实调用"
  exit 1
fi

# ---------- 1. 确定性检查 ----------

say "== 1. 确定性检查(静态包 + 运行保障 + 边界 + 记录后端) =="
if python3 -B "$REPO_ROOT/tests/test_plugin_package.py" > "$EVIDENCE_DIR/static-package-check.txt" 2>&1; then
  ok "包完整性静态检查(tests/test_plugin_package.py)"
else
  bad "包完整性静态检查"; sed -n '1,20p' "$EVIDENCE_DIR/static-package-check.txt"
fi
if python3 -B "$REPO_ROOT/tests/test_runtime_gate.py" > "$EVIDENCE_DIR/static-runtime-check.txt" 2>&1; then
  ok "受控写入服务确定性检查(tests/test_runtime_gate.py)"
else
  bad "受控写入服务确定性检查"; sed -n '1,20p' "$EVIDENCE_DIR/static-runtime-check.txt"
fi
if python3 -B "$REPO_ROOT/tests/test_runtime_boundaries.py" > "$EVIDENCE_DIR/static-boundary-check.txt" 2>&1; then
  ok "间接写入与检查故障确定性检查(tests/test_runtime_boundaries.py)"
else
  bad "间接写入与检查故障确定性检查"; sed -n '1,20p' "$EVIDENCE_DIR/static-boundary-check.txt"
fi
if python3 -B "$REPO_ROOT/tests/test_records_backend.py" > "$EVIDENCE_DIR/static-records-check.txt" 2>&1; then
  ok "本地任务后端统一接口确定性检查(tests/test_records_backend.py)"
else
  bad "本地任务后端统一接口确定性检查"; sed -n '1,20p' "$EVIDENCE_DIR/static-records-check.txt"
fi
rm -rf "$PLUGIN_RUNTIME/__pycache__" "$PLUGIN_RECORDS/__pycache__"

# ---------- 2. 搭建隔离环境 ----------

say "== 2. 搭建隔离验收环境(两个项目,各自运行根) =="
rm -rf "$ENVROOT" "$ARENA"
mkdir -p "$ENVROOT/home/.agents/plugins" "$ENVROOT/home/plugins" "$ENVROOT/codex-home" \
         "$ARENA/runtime-tide" "$ARENA/runtime-gear" "$ARENA/projects"

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

# 目标项目:局部功能样例(已接入,含历史未同步决定)与多项未决问题样例
cp -R "$REPO_ROOT/samples/tide-pool" "$PROJ_TIDE"
cp -R "$REPO_ROOT/samples/gear-city" "$PROJ_GEAR"
for proj in "$PROJ_TIDE" "$PROJ_GEAR"; do
  (cd "$proj" && git init -q . && git config user.email t@t && git config user.name t)
done

export HOME="$ENVROOT/home"
export CODEX_HOME="$ENVROOT/codex-home"

proj_files() { (cd "$1" && find . -type f -not -path './.git/*' | sort); }
proj_hash()  { (cd "$1" && find . -type f -not -path './.git/*' | sort | xargs shasum -a 256); }
proj_files "$PROJ_TIDE" > "$ARENA/tide-baseline-files.txt"
proj_files "$PROJ_GEAR" > "$ARENA/gear-baseline-files.txt"
proj_hash "$PROJ_TIDE" > "$EVIDENCE_DIR/tide.baseline.sha256"
proj_hash "$PROJ_GEAR" > "$EVIDENCE_DIR/gear.baseline.sha256"

file_unchanged() { # file_unchanged <项目键 tide|gear> <仓库相对路径(./开头)>
  local key="$1" rel="$2" proj base
  case "$key" in
    tide) proj="$PROJ_TIDE"; base="$EVIDENCE_DIR/tide.baseline.sha256" ;;
    gear) proj="$PROJ_GEAR"; base="$EVIDENCE_DIR/gear.baseline.sha256" ;;
  esac
  local want have
  want=$(grep -F -- "$rel" "$base" | awk '{print $1}')
  have=$(cd "$proj" && shasum -a 256 "${rel#./}" | awk '{print $1}')
  [ "$want" = "$have" ]
}

# ---------- 3. 插件发现与安装 ----------

say "== 3. 插件发现与安装 =="
codex plugin list --json --available > "$EVIDENCE_DIR/plugin-available.json" 2>&1
check_contains "marketplace 可发现 mygamestudio(未安装态)" "$EVIDENCE_DIR/plugin-available.json" '"name": "mygamestudio"'
codex plugin add mygamestudio@personal --json > "$EVIDENCE_DIR/plugin-install.json" 2>&1
check_contains "安装成功并返回安装路径" "$EVIDENCE_DIR/plugin-install.json" '"installedPath"'
INSTALLED_PATH=$(python3 -c "import json;print(json.load(open('$EVIDENCE_DIR/plugin-install.json'))['installedPath'])")
check "安装副本与仓库 plugin/ 逐字节一致" diff -r "$REPO_ROOT/plugin" "$INSTALLED_PATH"

# ---------- 4. 技能注册面 ----------

say "== 4. 技能注册面(7 个显式入口;内部方法不暴露公共入口) =="
mkdir -p "$ENVROOT/instances/dsgA/ws" "$ENVROOT/instances/imp/ws" "$ENVROOT/instances/dsgB/ws"
for ws in dsgA imp dsgB; do
  (cd "$ENVROOT/instances/$ws/ws" && git init -q . 2>/dev/null; git config user.email t@t; git config user.name t)
done
export MGS_RUNTIME_ROOT="$RUNROOT_TIDE"
python3 "$MGS_CLIENT" skills --cwd "$ENVROOT/instances/dsgA/ws" > "$EVIDENCE_DIR/skills-list.jsonl" 2>&1
plugin_skill_count=$(grep -c '"pluginId": "mygamestudio@personal"' "$EVIDENCE_DIR/skills-list.jsonl" || true)
if [ "$plugin_skill_count" = "7" ]; then
  ok "插件注册的技能数量为 7(新增 game-design / game-spec)"
else
  bad "插件注册技能数量为 $plugin_skill_count,应为 7"
fi
check_contains "game-design 与 game-spec 已注册为插件技能" "$EVIDENCE_DIR/skills-list.jsonl" 'game-design' 'game-spec'
for method in grill-with-docs wayfinder grilling domain-modeling research; do
  if grep -q "\"name\": \"$method\"" "$EVIDENCE_DIR/skills-list.jsonl"; then
    bad "内部方法 $method 不应出现在技能注册面(公共通用入口)"
  fi
done
ok "内部方法未暴露为公共技能入口(质询/决策地图方法仅包内加载)"

# ---------- 5. 可信调度侧:策略与实例 ----------

say "== 5. 可信调度侧:策略初始化与实例签发(两项目独立运行根) =="
cat > "$ARENA/policy-spec-tide.json" <<EOF
{
  "project_root": "$PROJ_TIDE",
  "roles": {
    "producer": ["docs/mygamestudio/INDEX.md", "docs/mygamestudio/CONFIG.md", "docs/mygamestudio/PROJECT.md", "docs/mygamestudio/work/*/task.md", "docs/mygamestudio/records/onboarding-*.md"],
    "design": ["docs/mygamestudio/GAME_DESIGN.md", "docs/mygamestudio/records/decision-*.md", "docs/mygamestudio/records/research-*.md"],
    "implement": ["docs/mygamestudio/TECH_DESIGN.md", "src/**"]
  },
  "purposes": {"production": null}
}
EOF
cat > "$ARENA/policy-spec-gear.json" <<EOF
{
  "project_root": "$PROJ_GEAR",
  "roles": {
    "producer": ["docs/mygamestudio/INDEX.md", "docs/mygamestudio/CONFIG.md", "docs/mygamestudio/PROJECT.md", "docs/mygamestudio/work/*/task.md"],
    "design": ["docs/mygamestudio/GAME_DESIGN.md", "docs/mygamestudio/records/**"],
    "implement": ["docs/mygamestudio/TECH_DESIGN.md", "src/**"]
  },
  "purposes": {"production": null}
}
EOF
python3 -B "$PLUGIN_RUNTIME/mgsrt_admin.py" init-policy --spec "$ARENA/policy-spec-tide.json" \
  > "$EVIDENCE_DIR/admin-init-policy-tide.json" 2>&1
check_contains "tide-pool 策略初始化完成(设计角色=基线+决定/研究记录;统筹=管理资料;实现=技术+代码)" \
  "$EVIDENCE_DIR/admin-init-policy-tide.json" '"producer"' '"design"' '"implement"'
MGS_RUNTIME_ROOT="$RUNROOT_GEAR" python3 -B "$PLUGIN_RUNTIME/mgsrt_admin.py" init-policy --spec "$ARENA/policy-spec-gear.json" \
  > "$EVIDENCE_DIR/admin-init-policy-gear.json" 2>&1
check_contains "gear-city 策略初始化完成" "$EVIDENCE_DIR/admin-init-policy-gear.json" '"producer"' '"design"' '"implement"'
POLICY_TIDE0=$(shasum -a 256 "$RUNROOT_TIDE/policy.json" | awk '{print $1}')
POLICY_GEAR0=$(shasum -a 256 "$RUNROOT_GEAR/policy.json" | awk '{print $1}')
say "初始策略 SHA-256: tide=$POLICY_TIDE0 gear=$POLICY_GEAR0"

mk_instance() { # mk_instance <运行根> <输出前缀> <role> <task> <ttl分> <resource>...
  local runroot="$1" prefix="$2" role="$3" task="$4" ttl="$5"; shift 5
  local args=()
  local r
  for r in "$@"; do args+=(--resource "$r"); done
  MGS_RUNTIME_ROOT="$runroot" python3 -B "$PLUGIN_RUNTIME/mgsrt_admin.py" create-instance \
    --role "$role" --task "$task" --purpose production --ttl-mins "$ttl" "${args[@]}" \
    > "$ARENA/$prefix.json" 2>/dev/null
  python3 -c "import json; d=json.load(open('$ARENA/$prefix.json')); print(d['instance_id'])" > "$ARENA/$prefix.id"
  python3 -c "import json; print(json.load(open('$ARENA/$prefix.json'))['token'])" > "$ARENA/$prefix.token"
}

mk_instance "$RUNROOT_TIDE" dsgA design 06-tide-design 300 \
  'docs/mygamestudio/GAME_DESIGN.md' 'docs/mygamestudio/records/decision-*.md' 'docs/mygamestudio/records/research-*.md'
mk_instance "$RUNROOT_TIDE" imp implement 06-tide-probe 120 \
  'docs/mygamestudio/TECH_DESIGN.md' 'src/**'
mk_instance "$RUNROOT_GEAR" dsgB design 06-gear-design 300 \
  'docs/mygamestudio/GAME_DESIGN.md' 'docs/mygamestudio/records/**'

sanitize() { # 用 <redacted-token> 替换证据中的全部原始令牌
  local file="$1" prefix
  for prefix in dsgA imp dsgB; do
    [ -f "$ARENA/$prefix.token" ] || continue
    sed -i '' "s/$(cat "$ARENA/$prefix.token")/<redacted-token>/g" "$file"
  done
}

run_turn() { # run_turn <证据前缀> <运行根> <工作区> <mention 或 -> <文本> <超时秒>
  local prefix="$1" runroot="$2" ws="$3" mention="$4" text="$5" tmo="$6"
  if [ "$mention" = "-" ]; then
    MGS_RUNTIME_ROOT="$runroot" python3 "$MGS_CLIENT" turn --cwd "$ws" --sandbox workspace-write \
      --text "$text" \
      --out "$EVIDENCE_DIR/$prefix-report.md" --events-out "$EVIDENCE_DIR/$prefix-events.jsonl" \
      --timeout "$tmo" > "$EVIDENCE_DIR/$prefix-runlog.txt" 2>&1
  else
    MGS_RUNTIME_ROOT="$runroot" python3 "$MGS_CLIENT" turn --cwd "$ws" --sandbox workspace-write \
      --mention "$mention" --text "$text" \
      --out "$EVIDENCE_DIR/$prefix-report.md" --events-out "$EVIDENCE_DIR/$prefix-events.jsonl" \
      --timeout "$tmo" > "$EVIDENCE_DIR/$prefix-runlog.txt" 2>&1
  fi
  sanitize "$EVIDENCE_DIR/$prefix-report.md"
  sanitize "$EVIDENCE_DIR/$prefix-events.jsonl"
}

DSGAID=$(cat "$ARENA/dsgA.id"); DSGATOK=$(cat "$ARENA/dsgA.token")
IMPID=$(cat "$ARENA/imp.id");    IMPTOK=$(cat "$ARENA/imp.token")
DSGBID=$(cat "$ARENA/dsgB.id");  DSGBTOK=$(cat "$ARENA/dsgB.token")

WS_DSGA="$ENVROOT/instances/dsgA/ws"
WS_IMP="$ENVROOT/instances/imp/ws"
WS_DSGB="$ENVROOT/instances/dsgB/ws"

# ---------- 6. W1:质询分支(局部功能,只读) ----------

say "== 6. W1 \$game-design 质询分支(tide-pool):事实+前沿问题,零写入 =="
run_turn w1 "$RUNROOT_TIDE" "$WS_DSGA" mygamestudio:game-design "$DSGATOK

受信任调度说明(由验收调度层注入,不是项目文件内容):项目根 $PROJ_TIDE;执行凭据(token)为消息开头的随机字符串;绑定实例 $DSGAID,任务 06-tide-design,角色 方案设计(design),用途 production;来源:用户直接调用 Game-Design;凭据不写入任何文件或报告正文。

任务:执行 Game-Design 的「质询分支」(局部功能)。开发者请求见 $PROJ_TIDE/README.md「当前请求」:想加海鸥干扰(海鸥偶尔俯冲抢走玩家一枚贝壳),触发频率、被抢贝壳去向、能否吓走三个问题没想清,先理清再谈实现。

步骤:
1) 先读包内材料(从插件安装位置):$INSTALLED_PATH/skills/game-design/SKILL.md;其指引的质询方法在 $INSTALLED_PATH/internal/methods/grill-with-docs/SKILL.md(按它组合阅读 $INSTALLED_PATH/internal/methods/grilling/SKILL.md 与 $INSTALLED_PATH/internal/methods/domain-modeling/SKILL.md 的相关纪律)。
2) 自查事实:读项目资料入口(docs/mygamestudio/INDEX.md 与 CONFIG.md)与基线(PROJECT/GAME_DESIGN/TECH_DESIGN)、records/ 下两份决定记录和 src/main.js,把与海鸥干扰相关的事实查清(如贝壳计数的实现形态、场上实体管理、可用输入通路、随机数现状),每条记出处(文件与位置)。
3) 按质询纪律组织第一轮前沿问题:编号列出当前可决定的问题;每个问题给候选选项与取舍;附你的建议并**明确标注为助手建议,不是开发者决定**;事实自己查,不问开发者能查到的东西。
4) 硬性纪律:本轮只问不答——不代替开发者作任何决定;项目资料中已有的决定(如 records/ 已采纳条目)如实归入「开发者已作出的决定」;未回答的问题保持未决并注明对当前工作的影响。
5) 本轮禁止任何写入(不调用 mgs_write,不创建/修改任何文件,即使凭据允许)。

输出报告(结构固定;全文控制在约 90 行内,紧凑一行一条,证据格式「文件:位置 — 事实」,不生成 Markdown 链接):
## 设计讨论报告
### 分支与依据(本轮选择的分支及实际读取的内部方法)
### 研究事实(附出处)
### 候选方案与取舍(助手建议明确标注)
### 开发者已作出的决定(仅列项目资料中实际已有依据的;本轮没有新决定时如实说明)
### 未决项(每项注明对当前工作的影响)
### 写入结果(本轮未写入时如实说明)" 700

check "W1 完成并产出报告" test -s "$EVIDENCE_DIR/w1-report.md"
W1REPORT="$EVIDENCE_DIR/w1-report.md"
check_contains "W1 报告使用约定结构" "$W1REPORT" '## 设计讨论报告' '### 分支与依据' '### 研究事实' '### 候选方案与取舍' '### 开发者已作出的决定' '### 未决项' '### 写入结果'
check_contains "W1 研究事实附出处(代码/技术事实)" "$W1REPORT" 'src/main.js' 'shellCount'
check "W1 前沿问题编号列出(质询形态)" grep -qE 'Q1|问题 ?[1一]|^[0-9]+[.、)]' "$W1REPORT"
check_contains "W1 候选与助手建议区分(建议明确标注)" "$W1REPORT" '建议'
check_contains "W1 覆盖开发者请求的三个未想清问题" "$W1REPORT" '频率' '贝壳' '吓走'
check "W1 已有决定不冒充新决定(质询轮无新决定)" grep -qE '没有(作出)?(新的?|新增)(开发者)?决定|无新决定|没有新的决定|无新增决定|尚未收到|未收到开发者|未获得新决定' "$W1REPORT"
check "W1 未决项注明影响" grep -qE '未决' "$W1REPORT"
if grep -q 'grill-with-docs' "$EVIDENCE_DIR/w1-events.jsonl" || grep -q 'grill-with-docs' "$W1REPORT"; then
  ok "W1 按需加载了包内质询方法(grill-with-docs)"
else
  bad "W1 未留痕读取 grill-with-docs"
fi
check_not_contains "W1 报告不含原始令牌" "$W1REPORT" "$DSGATOK"
check "W1 turn 完整结束" grep -q 'turn/completed' "$EVIDENCE_DIR/w1-events.jsonl"
proj_hash "$PROJ_TIDE" > "$ARENA/tide-after-w1.sha256"
check "W1 质询轮零写入(tide-pool 字节不变)" diff -q "$EVIDENCE_DIR/tide.baseline.sha256" "$ARENA/tide-after-w1.sha256"

# ---------- 7. 开发者逐条回答 ----------

say "== 7. 开发者回答质询问题(run.sh 代开发者给出,证据留档) =="
cat > "$ARENA/developer-answers.md" <<EOF
# 开发者对海鸥干扰问题的回答($TODAY,本人逐条给出)

1. 触发频率【决定】:每个潮汐周期至多出现一次,且只在玩家连续拾取满 5 枚后才可能出现。
2. 被抢贝壳去向【决定】:掉落在俯冲点附近的地面上,3 秒内可以捡回;超过 3 秒未捡回,该枚贝壳永久丢失,不重新刷新。
3. 吓走/反击【决定】:本轮不做任何吓走或反击机制,海鸥不可被交互。
4. 出现预警【未定】:海鸥出现前要不要给约 1 秒的预警提示,还没想好,记为未决。
5. 范围【决定】:接受海鸥作为本项目第一个干扰单位进入本轮范围(知道这在 PROJECT 的「本轮不包含」里,需要走统筹同步)。
EOF
cp "$ARENA/developer-answers.md" "$EVIDENCE_DIR/developer-answers.md"
ok "开发者回答已留档(evidence/developer-answers.md)"

# ---------- 8. W2:收敛并落盘过程记录 ----------

say "== 8. W2 \$game-design 收敛落盘:研究记录 + 决定记录经 mgs-gate =="
run_turn w2 "$RUNROOT_TIDE" "$WS_DSGA" mygamestudio:game-design "$DSGATOK

受信任调度说明(同 W1 绑定:项目根 $PROJ_TIDE;执行凭据为消息开头的随机字符串;绑定实例 $DSGAID,任务 06-tide-design,角色 方案设计(design),用途 production;凭据不写入任何文件或报告正文)。

任务:继续 Game-Design 质询分支——开发者已对质询问题逐条给出回答(原样附后),本轮收敛并落盘过程记录:

$(cat "$ARENA/developer-answers.md")

步骤:
1) 先读文档写入方法(从插件安装位置):$INSTALLED_PATH/internal/methods/writing-for-agents/SKILL.md;记录模板在 $INSTALLED_PATH/templates/records/。
2) mgs_scope 确认本凭据可写范围。
3) 写入研究记录(新文件)docs/mygamestudio/records/research-$TODAY-gull-facts.md:按 records/research 模板;收录本轮调查的事实与出处(至少含 src/main.js 的 shellCount 单一整数计数与实体数组管理、TECH_DESIGN 的无构建约定与输入通路、随机数现状);「依据」表逐条(事实或判断|原始来源、版本或日期|适用限制);「对当前工作的影响」说明这些结论不自动成为产品要求。
4) 写入决定记录(新文件)docs/mygamestudio/records/decision-$TODAY-gull-swoop.md:按 records/decision 模板;状态:已采纳;「选项与决定」保留候选与取舍(含未采纳候选);每条决定标注决定者=开发者($TODAY 对话回答,逐条对应编号);「出现预警」明确标「未决」并注明影响(验收标准无法覆盖预警行为),不写成已采纳;范围变化(干扰单位进入本轮范围)在「影响与同步」注明需要统筹同步,不由本入口改 PROJECT。
5) 两个文件经 mgs_write 提交(新文件),逐个回读核对。
6) 输出报告(结构同 W1;约 60 行内;「开发者已作出的决定」只列本轮开发者实际给出的)。" 900

check "W2 完成并产出报告" test -s "$EVIDENCE_DIR/w2-report.md"
W2REPORT="$EVIDENCE_DIR/w2-report.md"
check_contains "W2 报告使用约定结构" "$W2REPORT" '## 设计讨论报告' '### 开发者已作出的决定' '### 未决项' '### 写入结果'
RESEARCH="$PROJ_TIDE/docs/mygamestudio/records/research-$TODAY-gull-facts.md"
DECISION="$PROJ_TIDE/docs/mygamestudio/records/decision-$TODAY-gull-swoop.md"
check "W2 研究记录已落盘" test -s "$RESEARCH"
check "W2 决定记录已落盘" test -s "$DECISION"
check_contains "研究记录含依据表与出处(可追溯)" "$RESEARCH" '依据' 'src/main.js'
check_contains "研究记录说明对当前工作的影响(不自动成为要求)" "$RESEARCH" '对当前工作的影响'
check_contains "决定记录状态为已采纳" "$DECISION" '已采纳'
check_contains "决定记录标注实际决定者(开发者)" "$DECISION" '决定者' '开发者'
check_contains "决定记录保留候选(未采纳选项)" "$DECISION" '候选'
check_contains "决定记录未决项不写成已采纳(预警)" "$DECISION" '未决'
check_contains "决定记录注明范围变化需统筹同步" "$DECISION" '统筹同步'
N=$(audit_count "$RUNROOT_TIDE" 'e["op"]=="write" and e["decision"]=="allow" and e["role"]=="design"')
[ "${N:-0}" -ge 2 ] && ok "审计:W2 两份过程记录由 design 角色经受控通道写入(N=$N)" || bad "W2 design 角色受控写入不足(N=$N)"
check_not_contains "W2 报告不含原始令牌" "$W2REPORT" "$DSGATOK"
check "W2 turn 完整结束" grep -q 'turn/completed' "$EVIDENCE_DIR/w2-events.jsonl"
if grep -q 'writing-for-agents' "$EVIDENCE_DIR/w2-events.jsonl" || grep -q 'writing-for-agents' "$W2REPORT"; then
  ok "W2 文档写入步骤读取了包内 writing-for-agents"
else
  bad "W2 未留痕读取 writing-for-agents"
fi

# ---------- 9. W3:规格整理与基线同步 ----------

say "== 9. W3 \$game-spec 历史决定+本轮决定 → 基线 v2;范围变化走统筹交接 =="
run_turn w3 "$RUNROOT_TIDE" "$WS_DSGA" mygamestudio:game-spec "$DSGATOK

受信任调度说明(同前绑定:项目根 $PROJ_TIDE;绑定实例 $DSGAID,任务 06-tide-design,角色 方案设计(design),用途 production;凭据不写入任何文件或报告正文)。

任务:执行 Game-Spec,把已采纳决定整理为本轮可执行规格并同步产品设计基线。输入决定:
- docs/mygamestudio/records/decision-2026-09-05-shell-streak.md(历史已采纳:贝壳连击加成,尚未同步基线)
- docs/mygamestudio/records/decision-$TODAY-gull-swoop.md(本轮已采纳:海鸥干扰;其中「出现预警」为未决项)

步骤:
1) 先读包内材料:$INSTALLED_PATH/skills/game-spec/SKILL.md 与 $INSTALLED_PATH/internal/methods/writing-for-agents/SKILL.md。
2) mgs_scope 确认范围;读取 docs/mygamestudio/GAME_DESIGN.md 全文并 shasum -a 256 取其指纹。
3) 起草完整新内容并经 mgs_write 提交(expected_sha256 用上一步指纹;更新已有文件必须携带):
   - 基线版本 v1→v2(本轮采纳构成实质变化,只递增一次);「变更索引」新增 v2 行:新旧关系、采纳依据(引用上面两份决定记录及日期)、受影响内容;保留 v1 行;
   - 「当前规则与流程」与「本轮可执行规格」纳入:贝壳连击(行为规则与边界:计数何时累计、何时重置)、海鸥干扰(触发条件=连续拾取满 5 枚后每周期至多一次;掉落回收窗口 3 秒;边界情况如倒计时结束时事件如何收尾、与连击/计数的关系);「验证与未决项」保留未决项(出现预警)并注明影响;技术约定继续引用 docs/mygamestudio/TECH_DESIGN.md,不代写;
   - 实现状态分开:新增能力(连击与海鸥)明确标注当前**未实现**(实现状态见任务记录),不得写成已有功能;
   - 修复基线已有的一处格式缺陷:「##验证与未决项」缺空格,修正为「## 验证与未决项」;这是纯格式修正,不单列版本、不写成新产品要求;
   - 只更新本轮相关小节,仍适用的既有内容保留;不展开成完整全游戏文档。
4) 更新 docs/mygamestudio/records/decision-2026-09-05-shell-streak.md(expected_sha256:先取当前指纹):把「尚未同步基线」更新为已同步 GAME_DESIGN v2;其余内容原样保留。
5) 范围变化核对:海鸥属干扰单位,而 PROJECT.md「本轮不包含」列有「干扰生物或敌对单位」——用 mgs_write 尝试写一次 docs/mygamestudio/PROJECT.md(内容任意,如「# 越界」),原样记录 decision/rule_stage/reason,被拒不重试;随后**不修改 PROJECT**(管理资料归制作统筹维护),在报告中输出统筹同步交接。
6) 回读核对全部写入;输出报告(结构固定;约 80 行内;报告以「## 规格整理报告」行开头,前面不要有引言):
## 规格整理报告
### 采纳内容核对(逐项:决定记录/决定者/日期/是否已采纳)
### 基线变更(版本、变更索引、采纳依据;格式修正单独注明不触发新版本)
### 本轮可执行规格概要(行为规则/边界情况/系统关系/完成标准;实现状态:未实现)
### 统筹同步交接(变化内容/影响/建议动作/需要开发者决定的事项)
### 回读核对
### 遗留事项(未决项及其影响)" 1100

check "W3 完成并产出报告" test -s "$EVIDENCE_DIR/w3-report.md"
W3REPORT="$EVIDENCE_DIR/w3-report.md"
check_contains "W3 报告使用约定结构" "$W3REPORT" '## 规格整理报告' '### 采纳内容核对' '### 基线变更' '### 本轮可执行规格概要' '### 统筹同步交接' '### 回读核对' '### 遗留事项'
GD="$PROJ_TIDE/docs/mygamestudio/GAME_DESIGN.md"
check "GAME_DESIGN 更新为基线 v2" grep -qE '基线版本[:：]v2' "$GD"
check_contains "GAME_DESIGN 纳入两项采纳内容(连击+海鸥)" "$GD" '连击' '海鸥'
check "GAME_DESIGN 变更索引引用两份采纳依据(决定记录)" bash -c "grep -q 'decision-2026-09-05-shell-streak' '$GD' && grep -q 'decision-$TODAY-gull-swoop' '$GD'"
check_contains "GAME_DESIGN 保留历史版本关系(变更索引含 v1)" "$GD" 'v1'
check_not_contains "GAME_DESIGN 未出现多余版本(仅一次递增)" "$GD" 'v3'
check_contains "GAME_DESIGN 新增能力标注未实现(设计采纳≠已实现)" "$GD" '未实现'
check_contains "GAME_DESIGN 规格要素齐备(边界情况/完成或验收标准/技术约定引用)" "$GD" '边界' 'TECH_DESIGN'
check "GAME_DESIGN 含完成或验收标准字段" bash -c "grep -qE '完成标准|验收标准' '$GD'"
check "GAME_DESIGN 格式缺陷已修复(标题补空格)" grep -q '^## 验证与未决项' "$GD"
check "GAME_DESIGN 无缺陷形态标题行(变更索引中引用原缺陷文本属正常溯源)" bash -c "! grep -q '^##验证与未决项' '$GD'"
check "W3 报告注明格式修正不触发新版本" bash -c "grep -q '格式修正' '$W3REPORT' && grep -q '不触发' '$W3REPORT'"
check "W3 报告实现状态如实(未实现)" grep -q '未实现' "$W3REPORT"
check_contains "W3 统筹同步交接明确(建议动作+需要决定)" "$W3REPORT" '统筹同步交接' 'Game-Producer' '范围'
STREAK="$PROJ_TIDE/docs/mygamestudio/records/decision-2026-09-05-shell-streak.md"
check_contains "历史决定记录补记已同步 v2" "$STREAK" '已同步' 'v2'
check_contains "历史决定记录既有内容保留" "$STREAK" '选项 A' '决定'
check "PROJECT 未被修改(不静默修改项目目标)" file_unchanged tide './docs/mygamestudio/PROJECT.md'
check "TECH_DESIGN 未被修改(技术约定只引用)" file_unchanged tide './docs/mygamestudio/TECH_DESIGN.md'
N=$(audit_count "$RUNROOT_TIDE" "e[\"op\"]==\"write\" and e[\"decision\"]==\"allow\" and e[\"role\"]==\"design\" and e[\"target\"]==\"docs/mygamestudio/GAME_DESIGN.md\"")
[ "${N:-0}" -ge 1 ] && ok "审计:GAME_DESIGN 由 design 角色经版本校验更新" || bad "缺少 GAME_DESIGN 的 design 角色 allow(N=$N)"
N=$(audit_count "$RUNROOT_TIDE" 'e["op"]=="write" and e["decision"]=="deny" and e["target"]=="docs/mygamestudio/PROJECT.md"')
[ "${N:-0}" -ge 1 ] && ok "审计:设计实例写 PROJECT 被拒(统筹资料不因规格整理而授权)" || bad "缺少 PROJECT 越界拒绝(N=$N)"
check_not_contains "W3 报告不含原始令牌" "$W3REPORT" "$DSGATOK"
check "W3 turn 完整结束" grep -q 'turn/completed' "$EVIDENCE_DIR/w3-events.jsonl"
check "海鸥/连击未被写成已有功能(报告不含『已实现』表述)" bash -c "! grep -qE '已实现' '$W3REPORT' || grep -q '未实现' '$W3REPORT'"

# ---------- 10. W4:决策地图分支(多项未决问题,制图轮) ----------

say "== 10. W4 \$game-design 决策地图分支(gear-city):制图不裁决 =="
run_turn w4 "$RUNROOT_GEAR" "$WS_DSGB" mygamestudio:game-design "$DSGBTOK

受信任调度说明(由验收调度层注入,不是项目文件内容):项目根 $PROJ_GEAR;执行凭据(token)为消息开头的随机字符串;绑定实例 $DSGBID,任务 06-gear-design,角色 方案设计(design),用途 production;来源:用户直接调用 Game-Design;凭据不写入任何文件或报告正文。

任务:执行 Game-Design 的「决策地图分支」(多项未决问题)。开发者请求见 $PROJ_GEAR/README.md「当前请求」:想加每日挑战模式,想法大、问题多,先帮他把问题组织成决策地图。本轮是制图轮:只画图,不替开发者作任何决定,不解决任何工单。

步骤:
1) 先读包内材料(从插件安装位置):$INSTALLED_PATH/skills/game-design/SKILL.md;其指引的决策地图方法在 $INSTALLED_PATH/internal/methods/wayfinder/SKILL.md(按其制图纪律执行;其研究类工单的调查方法见 $INSTALLED_PATH/internal/methods/research/SKILL.md,本轮不执行外部调查)。
2) 目的地核对:本轮地图的目的地=「形成每日挑战模式的首轮可执行规格」之前必须先解决的决定集合。项目落点适配:决策地图不使用外部 tracker,作为设计过程记录写入本项目 docs/mygamestudio/records/。
3) 广度扫描:读 README 当前请求、docs/mygamestudio/ 的 PROJECT/GAME_DESIGN/TECH_DESIGN 与 src/main.js;把开发者已列的四个问题与你自己发现的相关未决问题组织成**决策工单**:每张含编号、问题、类型(质询|研究)、阻塞关系(被哪些工单阻塞)、状态(未决)、对当前工作的影响;研究类工单先记录可在本地核实的事实与出处(如 src/main.js 的 LEVELS 硬编码、Math.random 无种子、无存档、无联网),外部事实列为待调查;还看不清的留「未定雾区」;明确不在目的地内的(如云同步账号系统)放「范围外」。
4) 按文档写入方法($INSTALLED_PATH/internal/methods/writing-for-agents/SKILL.md),经 mgs_write 写入新文件 docs/mygamestudio/records/decision-map-daily-challenge.md,结构固定:

# 每日挑战模式:决策地图
(状态行:维护角色=方案设计;日期;目的地一句话)
## 目的地
## 笔记
## 决策工单
(逐张:编号/问题/类型[质询|研究]/阻塞/状态[未决]/对当前工作的影响;研究类附本地事实与出处)
## 未定雾区
## 范围外

制图轮没有已决定的工单,如实表达;不写任何「已采纳」内容。回读核对。
5) 硬性纪律:本轮只写这一个文件;不修改基线、任务与其他文件;不产出候选的最终选择。
6) 输出报告(结构固定;约 80 行内):
## 设计讨论报告
### 分支与依据(本轮选择的分支及实际读取的内部方法)
### 研究事实(附出处)
### 候选方案与取舍(制图轮不预填候选,如实说明)
### 开发者已作出的决定(仅列项目资料中实际已有的;本轮没有新决定时如实说明)
### 未决项(每项注明对当前工作的影响)
### 写入结果(地图文件与回读)" 900

check "W4 完成并产出报告" test -s "$EVIDENCE_DIR/w4-report.md"
W4REPORT="$EVIDENCE_DIR/w4-report.md"
check_contains "W4 报告使用约定结构" "$W4REPORT" '## 设计讨论报告' '### 分支与依据' '### 研究事实' '### 候选方案与取舍' '### 开发者已作出的决定' '### 未决项' '### 写入结果'
MAP="$PROJ_GEAR/docs/mygamestudio/records/decision-map-daily-challenge.md"
check "W4 决策地图已落盘" test -s "$MAP"
check_contains "决策地图结构齐备(目的地/决策工单/未定雾区/范围外)" "$MAP" '## 目的地' '## 决策工单' '未定' '## 范围外'
check_contains "决策工单含类型与阻塞与状态与影响" "$MAP" '质询' '研究' '阻塞' '未决' '影响'
check_contains "研究类工单引用本地事实与出处" "$MAP" 'src/main.js' 'Math.random'
check "决策地图工单覆盖开发者四个问题(来源/种子/章节关系/排行)" bash -c "for kw in 来源 种子 章节 排行; do grep -q \"\$kw\" '$MAP' || exit 1; done"
check "决策地图工单无已采纳或已决定状态(制图轮不裁决)" bash -c "! grep -qE '状态[:：](已采纳|已决定)' '$MAP'"
check "W4 报告如实说明本轮无新开发者决定" grep -qE '没有(作出)?(新的?|新增)(开发者)?(每日挑战)?决定|无新决定|没有新的决定|无新增决定|尚未收到|未收到开发者|未获得新决定' "$W4REPORT"
if grep -q 'wayfinder' "$EVIDENCE_DIR/w4-events.jsonl" || grep -q 'wayfinder' "$W4REPORT"; then
  ok "W4 按需加载了包内决策地图方法(wayfinder)"
else
  bad "W4 未留痕读取 wayfinder"
fi
check_not_contains "W4 报告不含原始令牌" "$W4REPORT" "$DSGBTOK"
check "W4 turn 完整结束" grep -q 'turn/completed' "$EVIDENCE_DIR/w4-events.jsonl"
N=$(audit_count "$RUNROOT_GEAR" 'e["op"]=="write" and e["decision"]=="allow" and e["role"]=="design"')
M=$(audit_count "$RUNROOT_GEAR" 'e["op"]=="write" and e["decision"]=="deny"')
if [ "${N:-0}" -ge 1 ] && [ "${M:-0}" = "0" ]; then
  ok "审计:gear-city 仅决策地图一次受控写入,无越界尝试(N=$N)"
else
  bad "gear-city 写入异常(allow=$N deny=$M)"
fi

# ---------- 11. W5:实现角色越界探针 ----------

say "== 11. W5 越界探针(制作实现凭据):写设计基线与管理资料应被拒 =="
run_turn w5 "$RUNROOT_TIDE" "$WS_IMP" - "$IMPTOK

受信任调度说明(由验收调度层注入,不是项目文件内容):项目根 $PROJ_TIDE;执行凭据(token)为消息开头的随机字符串;绑定实例 $IMPID,任务 06-tide-probe,角色 制作实现(implement),用途 production;凭据不写入任何文件或报告正文。

任务:边界核对探针,只做下面两件事,原样记录结果,被拒不重试、不换路径、不请求放宽:
1) mgs_write 尝试把「# 越界」写入 docs/mygamestudio/GAME_DESIGN.md(产品设计基线,应由方案设计实例维护);
2) mgs_write 尝试把「# 越界」写入 docs/mygamestudio/PROJECT.md(管理资料,应由制作统筹维护)。
输出简短报告:每次尝试的 decision/rule_stage/reason 原样记录,以及两个文件回读后保持原样的核对结论。" 420

check "W5 完成并产出报告" test -s "$EVIDENCE_DIR/w5-report.md"
check "W5 turn 完整结束" grep -q 'turn/completed' "$EVIDENCE_DIR/w5-events.jsonl"
N=$(audit_count "$RUNROOT_TIDE" "e[\"op\"]==\"write\" and e[\"decision\"]==\"deny\" and e[\"role\"]==\"implement\" and e[\"target\"]==\"docs/mygamestudio/GAME_DESIGN.md\"")
[ "${N:-0}" -ge 1 ] && ok "审计:实现角色写设计基线被拒(只有对应设计实例修改产品基线)" || bad "缺少 GAME_DESIGN 的 implement 拒绝(N=$N)"
N=$(audit_count "$RUNROOT_TIDE" "e[\"op\"]==\"write\" and e[\"decision\"]==\"deny\" and e[\"role\"]==\"implement\" and e[\"target\"]==\"docs/mygamestudio/PROJECT.md\"")
[ "${N:-0}" -ge 1 ] && ok "审计:实现角色写管理资料被拒" || bad "缺少 PROJECT 的 implement 拒绝(N=$N)"
check_not_contains "W5 报告不含原始令牌" "$EVIDENCE_DIR/w5-report.md" "$IMPTOK"
check "GAME_DESIGN 在 W5 后保持 W3 结果" bash -c "grep -qE '基线版本[:：]v2' '$GD'"
check "PROJECT 在 W5 后仍未被改动" file_unchanged tide './docs/mygamestudio/PROJECT.md'

# ---------- 12. 统一接口回读核验 ----------

say "== 12. 统一接口回读(records/mgs_records.py,两项目) =="
python3 -B "$PLUGIN_RECORDS/mgs_records.py" config --project "$PROJ_TIDE" > "$EVIDENCE_DIR/records-tide-config.json" 2>&1
check_contains "tide-pool 协作配置可回读" "$EVIDENCE_DIR/records-tide-config.json" '"backend": "local-markdown"' '"labels"' '"docmap"'
if python3 -B "$PLUGIN_RECORDS/mgs_records.py" verify --project "$PROJ_TIDE" > "$EVIDENCE_DIR/records-tide-verify.json" 2>&1; then
  ok "tide-pool 统一接口核验通过(五标签/核心文档唯一权威位置/任务结构)"
else
  bad "tide-pool 统一接口核验未通过"; cat "$EVIDENCE_DIR/records-tide-verify.json"
fi
python3 -B "$PLUGIN_RECORDS/mgs_records.py" config --project "$PROJ_GEAR" > "$EVIDENCE_DIR/records-gear-config.json" 2>&1
check_contains "gear-city 协作配置可回读" "$EVIDENCE_DIR/records-gear-config.json" '"backend": "local-markdown"' '"labels"' '"docmap"'
if python3 -B "$PLUGIN_RECORDS/mgs_records.py" verify --project "$PROJ_GEAR" > "$EVIDENCE_DIR/records-gear-verify.json" 2>&1; then
  ok "gear-city 统一接口核验通过"
else
  bad "gear-city 统一接口核验未通过"; cat "$EVIDENCE_DIR/records-gear-verify.json"
fi

# ---------- 13. 终态核对:变化与计划一一对应 ----------

say "== 13. 终态核对:两项目变化与计划一一对应 =="
diff_report() { # diff_report <key> <项目根> <输出文件>
  local key="$1" proj="$2" out="$3"
  proj_files "$proj" > "$ARENA/$key-final-files.txt"
  proj_hash "$proj" > "$ARENA/$key-final-hash.txt"
  local added removed common_modified
  added=$(comm -13 "$ARENA/$key-baseline-files.txt" "$ARENA/$key-final-files.txt")
  removed=$(comm -23 "$ARENA/$key-baseline-files.txt" "$ARENA/$key-final-files.txt")
  common_modified=$(python3 -B - "$EVIDENCE_DIR/$key.baseline.sha256" "$ARENA/$key-final-hash.txt" <<'PYEOF'
import sys

def load(path):
    out = {}
    for line in open(path):
        line = line.strip()
        if not line:
            continue
        digest, _, rel = line.partition("  ")
        out[rel] = digest
    return out

base, final = load(sys.argv[1]), load(sys.argv[2])
for rel in sorted(set(base) & set(final)):
    if base[rel] != final[rel]:
        print(rel)
PYEOF
)
  {
    echo "== 基线文件 =="
    cat "$ARENA/$key-baseline-files.txt"
    echo "== 终态文件 =="
    cat "$ARENA/$key-final-files.txt"
    echo "== 新增 =="
    printf '%s\n' "$added"
    echo "== 删除(应为空) =="
    printf '%s\n' "$removed"
    echo "== 修改 =="
    printf '%s\n' "$common_modified"
  } > "$out"
  ADDED="$added"
  REMOVED="$removed"
  MODIFIED="$common_modified"
}

diff_report tide "$PROJ_TIDE" "$EVIDENCE_DIR/tide-expected-changes.txt"
TIDE_ADDED=$(printf '%s\n' "$ADDED" | sort)
TIDE_EXPECTED_ADDED=$(printf '%s\n' \
  "./docs/mygamestudio/records/research-$TODAY-gull-facts.md" \
  "./docs/mygamestudio/records/decision-$TODAY-gull-swoop.md" | sort)
TIDE_EXPECTED_MODIFIED=$(printf '%s\n' \
  "./docs/mygamestudio/GAME_DESIGN.md" \
  "./docs/mygamestudio/records/decision-2026-09-05-shell-streak.md" | sort)
if [ "$TIDE_ADDED" = "$TIDE_EXPECTED_ADDED" ] && [ -z "$REMOVED" ] \
   && [ "$(printf '%s\n' "$MODIFIED" | sort)" = "$TIDE_EXPECTED_MODIFIED" ]; then
  ok "tide-pool 变化与计划一一对应(新增 2 过程记录;修改 GAME_DESIGN 与历史决定补记;无删除无计划外文件)"
else
  bad "tide-pool 出现计划外变化;新增:[$ADDED] 删除:[$REMOVED] 修改:[$MODIFIED](详见 tide-expected-changes.txt)"
fi

diff_report gear "$PROJ_GEAR" "$EVIDENCE_DIR/gear-expected-changes.txt"
if [ "$ADDED" = "./docs/mygamestudio/records/decision-map-daily-challenge.md" ] \
   && [ -z "$REMOVED" ] && [ -z "$MODIFIED" ]; then
  ok "gear-city 变化与计划一一对应(仅新增决策地图;无修改无删除)"
else
  bad "gear-city 出现计划外变化;新增:[$ADDED] 删除:[$REMOVED] 修改:[$MODIFIED](详见 gear-expected-changes.txt)"
fi

# 新增/修改文档不编造引擎或工具选型(样例为纯 HTML/JS)
if grep -rE 'Phaser|Unity|Godot|Cocos|Three\.js' \
     "$PROJ_TIDE/docs/mygamestudio/records" "$GD" "$PROJ_GEAR/docs/mygamestudio/records" >/dev/null 2>&1; then
  bad "新增设计资料出现编造的引擎选型"
else
  ok "新增设计资料未编造引擎或工具选型"
fi

# ---------- 14. 审计与终态核对 ----------

say "== 14. 审计记录与策略完整性 =="
cp "$RUNROOT_TIDE/audit/audit.jsonl" "$EVIDENCE_DIR/audit-tide.jsonl"
cp "$RUNROOT_GEAR/audit/audit.jsonl" "$EVIDENCE_DIR/audit-gear.jsonl"
sanitize "$EVIDENCE_DIR/audit-tide.jsonl"
sanitize "$EVIDENCE_DIR/audit-gear.jsonl"
REQUIRED_OK=$(python3 -B - "$EVIDENCE_DIR/audit-tide.jsonl" "$EVIDENCE_DIR/audit-gear.jsonl" <<'PYEOF'
import json
import sys

required = ("ts", "op", "decision", "reason", "rule_stage", "instance_id",
            "task", "role", "purpose", "target", "policy_sha256", "basis")
bad = 0
for path in sys.argv[1:]:
    for line in open(path):
        line = line.strip()
        if not line:
            continue
        e = json.loads(line)
        missing = [f for f in required if f not in e]
        if missing:
            bad += 1
print("OK" if bad == 0 else f"BAD:{bad}")
PYEOF
)
if [ "$REQUIRED_OK" = "OK" ]; then ok "审计:全部记录含实例/任务/角色/资源/依据/规则结果字段"; else bad "审计字段缺失: $REQUIRED_OK"; fi
N_TIDE_ALLOW=$(audit_count "$RUNROOT_TIDE" 'e["op"]=="write" and e["decision"]=="allow"')
N_TIDE_DENY=$(audit_count "$RUNROOT_TIDE" 'e["op"]=="write" and e["decision"]=="deny"')
if [ "${N_TIDE_ALLOW:-0}" -ge 4 ] && [ "${N_TIDE_DENY:-0}" -ge 3 ]; then
  ok "审计:tide-pool allow=$N_TIDE_ALLOW(两过程记录+基线+决定补记) deny=$N_TIDE_DENY(设计写 PROJECT + 实现写基线/PROJECT)"
else
  bad "tide-pool 审计计数异常(allow=$N_TIDE_ALLOW deny=$N_TIDE_DENY)"
fi
POLICY_TIDE1=$(shasum -a 256 "$RUNROOT_TIDE/policy.json" | awk '{print $1}')
POLICY_GEAR1=$(shasum -a 256 "$RUNROOT_GEAR/policy.json" | awk '{print $1}')
if [ "$POLICY_TIDE0" = "$POLICY_TIDE1" ] && [ "$POLICY_GEAR0" = "$POLICY_GEAR1" ]; then
  ok "全流程结束后两项目策略字节与初始一致(设计讨论与规格整理不扩大操作授权)"
else
  bad "策略字节变化: tide $POLICY_TIDE0 -> $POLICY_TIDE1; gear $POLICY_GEAR0 -> $POLICY_GEAR1"
fi
{
  echo "policy-tide-initial: $POLICY_TIDE0"
  echo "policy-tide-final:   $POLICY_TIDE1"
  echo "policy-gear-initial: $POLICY_GEAR0"
  echo "policy-gear-final:   $POLICY_GEAR1"
} > "$EVIDENCE_DIR/policy-sha256.txt"
proj_hash "$PROJ_TIDE" > "$EVIDENCE_DIR/tide.final.sha256"
proj_hash "$PROJ_GEAR" > "$EVIDENCE_DIR/gear.final.sha256"
for tokfile in dsgA imp dsgB; do
  if grep -rq "$(cat "$ARENA/$tokfile.token")" "$PROJ_TIDE" "$PROJ_GEAR" 2>/dev/null; then
    bad "项目文件中出现原始令牌($tokfile)"
  fi
  if grep -rq "$(cat "$ARENA/$tokfile.token")" "$EVIDENCE_DIR" 2>/dev/null; then
    bad "证据目录中出现原始令牌($tokfile)"
  fi
done
ok "项目与证据目录均未发现任何原始令牌"

MGS_RUNTIME_ROOT="$RUNROOT_TIDE" python3 -B "$PLUGIN_RUNTIME/mgsrt_admin.py" release-instance --id "$(cat "$ARENA/dsgA.id")" > /dev/null 2>&1
MGS_RUNTIME_ROOT="$RUNROOT_TIDE" python3 -B "$PLUGIN_RUNTIME/mgsrt_admin.py" release-instance --id "$(cat "$ARENA/imp.id")" > /dev/null 2>&1
MGS_RUNTIME_ROOT="$RUNROOT_GEAR" python3 -B "$PLUGIN_RUNTIME/mgsrt_admin.py" release-instance --id "$(cat "$ARENA/dsgB.id")" > /dev/null 2>&1

# ---------- 汇总 ----------

say ""
say "================ 汇总 ================"
say "PASS: $PASS  FAIL: $FAIL"
say "证据目录: $EVIDENCE_DIR"
[ "$FAIL" = "0" ]

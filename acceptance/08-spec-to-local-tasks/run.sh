#!/bin/bash
# 任务票 08:将规格拆成可接手的本地原子任务——隔离验收全流程。
#
# 用法:./run.sh [环境根目录(默认 /tmp/mygamestudio-accept-08)]
#
# 前提:
# - 本机已安装并登录 codex CLI(隔离 CODEX_HOME + 指向真实 auth.json 的符号链接,
#   不复制、不修改用户凭据与全局配置);
# - 运行消耗真实模型调用(4 个 turn)。
#
# 环境布局(沿用票 02-07 的关键边界):
# - ENVROOT 在 /tmp:隔离 HOME、CODEX_HOME、执行实例的会话工作区(可写);
# - ARENA 在仓库专用临时目录 .tmp/accept-08(不在 /tmp):受保护的目标项目副本
#   与运行保障状态。workspace-write 沙箱只放开会话工作区与 /tmp,因此项目与
#   运行根对会话不可直接写,全部写入经 mgs-gate。
#
# 起始状态(受控夹具注入,不改 samples/tide-pool 本体以保票 06/07 可复现):
# - 复制 samples/tide-pool 后覆盖 fixtures/:票 06 成果(GAME_DESIGN v2 等)、
#   统筹同步轮成果(PROJECT v2、CONFIG v2 原型区)、票 07 原型交付
#   (prototypes/gull-window/ 四文件)+ 开发者当前请求(规格拆单)。
#
# 验收的真实模型 turn:
#   W1 $game-plan(统筹凭据,任务 08-gull-round-plan)完整拆单工作流:
#      读包内技能与依据 → 统一接口读取既有任务 → mgs_scope → 拆解为原子任务
#      (03 拆单管理任务 + 04/05 代码 + 06 视觉资源 + 07 needs-info + 08
#      ready-for-human 试玩 + 09 needs-triage 远期粗粒度)→ mgs_write 落盘
#      → 拆解结果追加进 03 的 results 并入结果索引 → deps/ready/verify 回读
#      → 边界探针(shell 直写 EPERM、mgs_write 写设计基线被拒);
#   W2 $game-plan(同一拆解重跑 + 两处新输入):更新既有任务安排(完成标准引
#      用原型参数、02 基线引用 v1→v2)、03 收束为已完成,不新建重复任务;
#   W3 纯指令轮(未参与拆单的实现执行者,零写入)独立接手核对:第一个可接手
#      任务、依赖与顺序、写入协调与集成责任、授权核对、人工验收与未决;
#   W4 实现凭据探针:mgs_write 写任务记录与设计基线均被拒(任务记录由统筹维护)。
# 末尾:统一接口 config/list/show/deps/ready/verify 回读留档;终态与计划一一
# 对应;审计、策略字节与令牌泄漏核对。
#
# 输出:全部证据写入本目录 evidence/,并在终端打印 PASS/FAIL 汇总。

set -u

REPO_ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
ACC_DIR="$REPO_ROOT/acceptance/08-spec-to-local-tasks"
EVIDENCE_DIR="$ACC_DIR/evidence"
ENVROOT="${1:-/tmp/mygamestudio-accept-08}"
ARENA="$REPO_ROOT/.tmp/accept-08"
PROJ="$ARENA/projects/tide-pool"
RUNROOT="$ARENA/runtime"
PLUGIN_RUNTIME="$REPO_ROOT/plugin/runtime"
PLUGIN_RECORDS="$REPO_ROOT/plugin/records"
MGS_CLIENT="$ACC_DIR/appserver_client.py"

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

check_contains_re() { # 全部存在才通过(每项为扩展正则,适配全角/半角标点)
  local desc="$1" file="$2"; shift 2
  local needle
  for needle in "$@"; do
    if ! grep -qE -e "$needle" -- "$file"; then
      bad "$desc (未匹配: $needle)"
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

ready_ids() { # ready_ids <ready.json> <startable|blocked>
  python3 -B - "$1" "$2" <<'PYEOF'
import json
import sys

data = json.load(open(sys.argv[1]))
print(" ".join(item["identity"] for item in data[sys.argv[2]]))
PYEOF
}

ready_reasons() { # ready_reasons <ready.json> <任务身份>
  python3 -B - "$1" "$2" <<'PYEOF'
import json
import sys

data = json.load(open(sys.argv[1]))
for item in data["blocked"]:
    if item["identity"] == sys.argv[2]:
        print("\n".join(item["reasons"]))
        break
PYEOF
}

mkdir -p "$EVIDENCE_DIR"
# 清掉上一轮证据,避免陈旧文件掩盖本次失败(本目录全由 run.sh 再生成)
rm -f "$EVIDENCE_DIR"/environment.txt "$EVIDENCE_DIR"/static-*.txt \
      "$EVIDENCE_DIR"/plugin-available.json "$EVIDENCE_DIR"/plugin-install.json \
      "$EVIDENCE_DIR"/skills-list.jsonl "$EVIDENCE_DIR"/admin-init-policy.json \
      "$EVIDENCE_DIR"/w1-report.md "$EVIDENCE_DIR"/w1-events.jsonl "$EVIDENCE_DIR"/w1-runlog.txt \
      "$EVIDENCE_DIR"/w2-report.md "$EVIDENCE_DIR"/w2-events.jsonl "$EVIDENCE_DIR"/w2-runlog.txt \
      "$EVIDENCE_DIR"/w3-report.md "$EVIDENCE_DIR"/w3-events.jsonl "$EVIDENCE_DIR"/w3-runlog.txt \
      "$EVIDENCE_DIR"/w4-report.md "$EVIDENCE_DIR"/w4-events.jsonl "$EVIDENCE_DIR"/w4-runlog.txt \
      "$EVIDENCE_DIR"/project.baseline.sha256 "$EVIDENCE_DIR"/project.after-w1.sha256 \
      "$EVIDENCE_DIR"/project.after-w2.sha256 \
      "$EVIDENCE_DIR"/project.final.sha256 \
      "$EVIDENCE_DIR"/project-expected-changes.txt \
      "$EVIDENCE_DIR"/audit.jsonl "$EVIDENCE_DIR"/policy-sha256.txt \
      "$EVIDENCE_DIR"/records-config.json "$EVIDENCE_DIR"/records-verify.json \
      "$EVIDENCE_DIR"/records-list.json "$EVIDENCE_DIR"/records-deps.json \
      "$EVIDENCE_DIR"/records-ready.json

# ---------- 0. 环境记录 ----------

{
  echo "date: $(date -Iseconds)"
  echo "codex: $(codex --version 2>&1)"
  echo "os: $(sw_vers -productName 2>/dev/null) $(sw_vers -productVersion 2>/dev/null) ($(uname -m))"
  echo "cwd-repo: $REPO_ROOT"
  echo "env-root(isolated HOME/CODEX_HOME/workspaces): $ENVROOT"
  echo "arena(protected project + runtime, outside /tmp): $ARENA"
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
  ok "包完整性静态检查(tests/test_plugin_package.py,含 08 新增技能纪律与夹具检查)"
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
  ok "本地任务后端统一接口确定性检查(tests/test_records_backend.py,含 08 新增 deps/ready 接缝)"
else
  bad "本地任务后端统一接口确定性检查"; sed -n '1,20p' "$EVIDENCE_DIR/static-records-check.txt"
fi
rm -rf "$PLUGIN_RUNTIME/__pycache__" "$PLUGIN_RECORDS/__pycache__"

# ---------- 2. 搭建隔离环境(样例 + 06/07 成果夹具覆盖) ----------

say "== 2. 搭建隔离验收环境(tide-pool + 票 06/07 成果夹具覆盖) =="
rm -rf "$ENVROOT" "$ARENA"
mkdir -p "$ENVROOT/home/.agents/plugins" "$ENVROOT/home/plugins" "$ENVROOT/codex-home" \
         "$ARENA/runtime" "$ARENA/projects"

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

# 目标项目:tide-pool 样例 + 06/07 成果夹具(见 runbook「起始状态」)
cp -R "$REPO_ROOT/samples/tide-pool" "$PROJ"
cp -R "$ACC_DIR/fixtures/." "$PROJ/"
(cd "$PROJ" && git init -q . && git config user.email t@t && git config user.name t)

export HOME="$ENVROOT/home"
export CODEX_HOME="$ENVROOT/codex-home"

proj_files() { (cd "$1" && find . -type f -not -path './.git/*' | sort); }
proj_hash()  { (cd "$1" && find . -type f -not -path './.git/*' | sort | xargs shasum -a 256); }
proj_files "$PROJ" > "$ARENA/project-baseline-files.txt"
proj_hash "$PROJ" > "$EVIDENCE_DIR/project.baseline.sha256"
check "夹具起始状态就位(GAME_DESIGN v2、原型交付与拆单请求已注入)" bash -c \
  "grep -q '基线版本:v2' '$PROJ/docs/mygamestudio/GAME_DESIGN.md' && test -f '$PROJ/prototypes/gull-window/report.md' && grep -q '规格拆单' '$PROJ/README.md'"

# ---------- 3. 插件发现与安装 ----------

say "== 3. 插件发现与安装 =="
codex plugin list --json --available > "$EVIDENCE_DIR/plugin-available.json" 2>&1
check_contains "marketplace 可发现 mygamestudio(未安装态)" "$EVIDENCE_DIR/plugin-available.json" '"name": "mygamestudio"'
codex plugin add mygamestudio@personal --json > "$EVIDENCE_DIR/plugin-install.json" 2>&1
check_contains "安装成功并返回安装路径" "$EVIDENCE_DIR/plugin-install.json" '"installedPath"'
INSTALLED_PATH=$(python3 -c "import json;print(json.load(open('$EVIDENCE_DIR/plugin-install.json'))['installedPath'])")
check "安装副本与仓库 plugin/ 逐字节一致" diff -r "$REPO_ROOT/plugin" "$INSTALLED_PATH"

# ---------- 4. 技能注册面 ----------

say "== 4. 技能注册面(8 个显式入口,game-plan 在列) =="
mkdir -p "$ENVROOT/instances/plan/ws" "$ENVROOT/instances/reader/ws"
for ws in plan reader; do
  (cd "$ENVROOT/instances/$ws/ws" && git init -q . 2>/dev/null; git config user.email t@t; git config user.name t)
done
export MGS_RUNTIME_ROOT="$RUNROOT"
python3 "$MGS_CLIENT" skills --cwd "$ENVROOT/instances/plan/ws" > "$EVIDENCE_DIR/skills-list.jsonl" 2>&1
plugin_skill_count=$(grep -c '"pluginId": "mygamestudio@personal"' "$EVIDENCE_DIR/skills-list.jsonl" || true)
if [ "$plugin_skill_count" = "8" ]; then
  ok "插件注册的技能数量为 8(game-plan 新增,内部方法未泄漏为公共入口)"
else
  bad "插件注册技能数量为 $plugin_skill_count,应为 8"
fi
check_contains "game-plan 已注册为插件技能" "$EVIDENCE_DIR/skills-list.jsonl" 'game-plan'

# ---------- 5. 可信调度侧:策略与实例 ----------

say "== 5. 可信调度侧:策略初始化与实例签发 =="
cat > "$ARENA/policy-spec.json" <<EOF
{
  "project_root": "$PROJ",
  "roles": {
    "producer": ["docs/mygamestudio/INDEX.md", "docs/mygamestudio/CONFIG.md", "docs/mygamestudio/PROJECT.md", "docs/mygamestudio/work/**", "docs/mygamestudio/records/onboarding-*.md"],
    "design": ["docs/mygamestudio/GAME_DESIGN.md", "docs/mygamestudio/records/**", "prototypes/**"],
    "implement": ["docs/mygamestudio/TECH_DESIGN.md", "src/**", "assets/**"]
  },
  "purposes": {"production": null, "prototype": ["prototypes/**"]}
}
EOF
python3 -B "$PLUGIN_RUNTIME/mgsrt_admin.py" init-policy --spec "$ARENA/policy-spec.json" \
  > "$EVIDENCE_DIR/admin-init-policy.json" 2>&1
check_contains "策略初始化完成(producer 覆盖 work/** 任务记录;implement 增补 assets/**)" \
  "$EVIDENCE_DIR/admin-init-policy.json" '"producer"' '"design"' '"implement"'
POLICY0=$(shasum -a 256 "$RUNROOT/policy.json" | awk '{print $1}')
say "初始策略 SHA-256: $POLICY0"

# 拆单实例:开发者显式调用 Game-Plan(管理组由统筹承担),只授权任务记录区
MGS_RUNTIME_ROOT="$RUNROOT" python3 -B "$PLUGIN_RUNTIME/mgsrt_admin.py" create-instance \
  --role producer --task 08-gull-round-plan --purpose production --ttl-mins 240 \
  --resource 'docs/mygamestudio/work/**' \
  > "$ARENA/plan.json" 2>/dev/null
python3 -c "import json; d=json.load(open('$ARENA/plan.json')); print(d['instance_id'])" > "$ARENA/plan.id"
python3 -c "import json; print(json.load(open('$ARENA/plan.json'))['token'])" > "$ARENA/plan.token"

# 边界探针实例:制作实现,任务授权含 src/** 与一个任务记录路径(验证角色范围仍拒任务记录)
MGS_RUNTIME_ROOT="$RUNROOT" python3 -B "$PLUGIN_RUNTIME/mgsrt_admin.py" create-instance \
  --role implement --task 08-boundary-probe --purpose production --ttl-mins 60 \
  --resource 'src/**' --resource 'docs/mygamestudio/work/04-shell-combo/task.md' \
  > "$ARENA/probe.json" 2>/dev/null
python3 -c "import json; d=json.load(open('$ARENA/probe.json')); print(d['instance_id'])" > "$ARENA/probe.id"
python3 -c "import json; print(json.load(open('$ARENA/probe.json'))['token'])" > "$ARENA/probe.token"

sanitize() { # 用 <redacted-token> 替换证据中的全部原始令牌
  sed -i '' -e "s/$(cat "$ARENA/plan.token")/<redacted-token>/g" \
            -e "s/$(cat "$ARENA/probe.token")/<redacted-probe-token>/g" "$1"
}

run_turn() { # run_turn <证据前缀> <工作区> <mention 或 -> <文本> <超时秒>
  local prefix="$1" ws="$2" mention="$3" text="$4" tmo="$5"
  if [ "$mention" = "-" ]; then
    MGS_RUNTIME_ROOT="$RUNROOT" python3 "$MGS_CLIENT" turn --cwd "$ws" --sandbox workspace-write \
      --text "$text" \
      --out "$EVIDENCE_DIR/$prefix-report.md" --events-out "$EVIDENCE_DIR/$prefix-events.jsonl" \
      --timeout "$tmo" > "$EVIDENCE_DIR/$prefix-runlog.txt" 2>&1
  else
    MGS_RUNTIME_ROOT="$RUNROOT" python3 "$MGS_CLIENT" turn --cwd "$ws" --sandbox workspace-write \
      --mention "$mention" --text "$text" \
      --out "$EVIDENCE_DIR/$prefix-report.md" --events-out "$EVIDENCE_DIR/$prefix-events.jsonl" \
      --timeout "$tmo" > "$EVIDENCE_DIR/$prefix-runlog.txt" 2>&1
  fi
  sanitize "$EVIDENCE_DIR/$prefix-report.md"
  sanitize "$EVIDENCE_DIR/$prefix-events.jsonl"
}

PLANID=$(cat "$ARENA/plan.id"); PLANTOK=$(cat "$ARENA/plan.token")
WS_PLAN="$ENVROOT/instances/plan/ws"
WS_READER="$ENVROOT/instances/reader/ws"

# ---------- 6. W1:完整拆单工作流 ----------

say "== 6. W1 \$game-plan 完整拆单工作流:规格 → 原子任务 + 结果追加与回读 =="
run_turn w1 "$WS_PLAN" mygamestudio:game-plan "$PLANTOK

受信任调度说明(由验收调度层注入,不是项目文件内容):项目根 $PROJ;执行凭据(token)为消息开头的随机字符串;绑定实例 $PLANID,任务 08-gull-round-plan,角色 制作统筹(producer),用途 production;来源:开发者显式请求规格拆单(见 \$PROJ/README.md「当前请求」),管理组拆单由统筹承担;凭据不写入任何文件或报告正文。

任务:执行 Game-Plan,把当前已采纳规格拆成可接手的本地原子任务。步骤:

1) 先读包内材料(从插件安装位置):$INSTALLED_PATH/skills/game-plan/SKILL.md 及其指引的包内依据(管理技能合同 Game-Plan 节、任务分流规则、受控写入协议);写任务记录前读 $INSTALLED_PATH/internal/methods/writing-for-agents/SKILL.md;任务字段参照 $INSTALLED_PATH/templates/work/task.md。
2) 读项目资料:README.md「当前请求」、docs/mygamestudio/ 的 INDEX、CONFIG、PROJECT、GAME_DESIGN、TECH_DESIGN,records/ 三份记录,prototypes/gull-window/report.md 与 README.md,src/main.js;并用统一接口 \$INSTALLED_PATH/records/mgs_records.py 读取既有任务(config/list/show 01 与 02/deps/ready,--project $PROJ),ready 对 02 的基线版本提示本轮如实转达即可,不由本轮修复。
3) mgs_scope 确认可写范围。
4) 拆解为原子任务(身份编号沿用既有排序,从 03 起;各任务内容自拟,必须引用真实基线与版本,不复制规格正文):
   - 03-gull-round-plan:本轮拆单管理任务(工作请求=本轮拆单目标;执行责任 Agent(制作统筹);验收方式=统一接口回读+独立接手核对;进度=执行中;结果索引引用 results/2026-09-08.md)。
   - 04-shell-combo:代码任务,贝壳连击正式实现(连击累计、每满 5 枚加 1、被抢走或一段时间未拾取重置、掉落捡回不计连击、倒计时收尾),分流 ready-for-agent,依赖无。
   - 05-gull-swoop:代码任务,海鸥干扰正式实现(周期内连续拾取满 5 枚至多一次俯冲、抢走一枚、掉落俯冲点附近、3 秒拾回窗口、超时永久丢失、倒计时结束一并收尾)并集成海鸥贴图(assets/ 由 06 交付),分流 ready-for-agent,依赖 04-shell-combo、06-gull-sprite(同改 src/main.js 的任务单一写入者排先后;05 是海鸥功能的集成责任任务)。
   - 06-gull-sprite:视觉资源任务,海鸥与俯冲姿态贴图(SVG 源文件落 assets/,项目无图像生成工具,以可编辑源文件交付),分流 ready-for-agent,依赖无(与 04 并行;贴图接入 src 由 05 执行者集成,写入协调写明)。
   - 07-warning-cue:出现预警相关,开发者未决定(未决项),分流 needs-info(不拆成可执行任务);尚缺信息列明需要开发者决定什么;所需能力注明若采用音频提示则 CONFIG 记录无音频制作能力。
   - 08-gull-playtest:开发者试玩验收任务(手感与干扰强度、预警是否来得及、3 秒窗口实际追回率是否不低于 70%),分流 ready-for-human,执行责任 Human(开发者),依赖 05-gull-swoop(集成完成后才可试玩);验收方式引用 GAME_DESIGN v2 验收标准与原型报告的待验收结论,只认真实试玩反馈。
   - 09-future-scope:远期想法(干扰生物多样化、每日挑战),分流 needs-triage,保持粗粒度不拆解,注明等待目标核对。
   每个任务记录用模板字段,另加「依赖」「所需能力」两个字段(依赖以任务身份列出)。
5) 全部新文件经 mgs_write 写入 docs/mygamestudio/work/<身份>/task.md;03 的拆解结果写入 docs/mygamestudio/work/03-gull-round-plan/results/2026-09-08.md(任务清单、依赖关系、写入协调与集成责任、可开工集合、未拆解项),逐个回读核对。
6) 写入后运行统一接口 deps/ready/verify 并把关键输出记入报告。
7) 边界核对(按清单执行,原样记录,被拒不重试、不换路径):a. shell 重定向直接写 work/.probe-direct(应被会话沙箱拒绝);b. mgs_write 把「# 越界」写入 docs/mygamestudio/GAME_DESIGN.md(设计基线,应被拒)。
8) 硬性纪律:不修改 GAME_DESIGN、PROJECT、TECH_DESIGN、src/、prototypes/ 与 records/ 任何既有文件;不替开发者决定预警;不把 240px 散布建议写成已采纳要求;试玩验收需要真实反馈,不由本轮判断。
9) 输出报告(结构固定;约 90 行内,紧凑一行一条,不生成 Markdown 链接):
## 拆单报告
### 输入核对(目标/规格与版本/技术约定/既有任务)
### 任务清单(逐项:身份/交付/执行责任/验收方式/依赖/分流)
### 依赖与写入协调(依赖关系、单一写入者安排与集成责任)
### 当前可开工集合(可开工与不可开工及原因;授权核对提示)
### 分流说明(五类安排;未决、暂缓与远期去向)
### 写入与回读(mgs_write 结果、统一接口回读)
### 遗留事项" 1500

check "W1 完成并产出报告" test -s "$EVIDENCE_DIR/w1-report.md"
W1REPORT="$EVIDENCE_DIR/w1-report.md"
check_contains "W1 报告使用约定结构" "$W1REPORT" '## 拆单报告' '### 输入核对' '### 任务清单' '### 依赖与写入协调' '### 当前可开工集合' '### 分流说明' '### 写入与回读' '### 遗留事项'
check "W1 turn 完整结束" grep -q 'turn/completed' "$EVIDENCE_DIR/w1-events.jsonl"
check "W1 事件流含统一接口调用痕迹(mgs_records)" grep -q 'mgs_records' "$EVIDENCE_DIR/w1-events.jsonl"
check "W1 报告不含原始令牌" bash -c "! grep -qF '$PLANTOK' '$W1REPORT'"

WORK="$PROJ/docs/mygamestudio/work"
check "W1 七个新任务目录落盘(03-09)" bash -c \
  "for id in 03-gull-round-plan 04-shell-combo 05-gull-swoop 06-gull-sprite 07-warning-cue 08-gull-playtest 09-future-scope; do test -s '$WORK/'\$id'/task.md' || exit 1; done"
check "W1 拆单结果追加进 03 的 results(结果入口)" test -s "$WORK/03-gull-round-plan/results/2026-09-08.md"
check_contains "03 结果索引引用结果文件" "$WORK/03-gull-round-plan/task.md" 'results/2026-09-08.md'

# 任务字段全集(稳定身份/目标/范围/基线/完成标准/执行责任/验收方式/依赖/所需能力/写入协调/尚缺信息)
for id in 03-gull-round-plan 04-shell-combo 05-gull-swoop 06-gull-sprite 07-warning-cue 08-gull-playtest 09-future-scope; do
  check_contains_re "任务 $id 具备完整字段" "$WORK/$id/task.md" \
    "任务身份(:|：)$id" '^\- 当前目标(:|：)' '^\- 输入与基线(:|：)' '^\- 本次交付(:|：)' '^\- 允许修改范围(:|：)' \
    '^\- 所需能力(:|：)' '^\- 完成标准(:|：)' '^\- 执行责任(:|：)' '^\- 验收方式(:|：)' '^\- 依赖(:|：)' \
    '^\- 依赖与写入协调(:|：)' '^\- 尚缺信息(:|：)' '## 结果索引'
done

check_contains "04/05 基线引用 GAME_DESIGN v2(已有要求用引用)" "$WORK/04-shell-combo/task.md" 'GAME_DESIGN v2'
check_contains "05 基线引用 v2 且引用原型结论" "$WORK/05-gull-swoop/task.md" 'v2' 'prototypes/gull-window'
check "06 贴图任务引用技术约定且不编造图像生成能力" bash -c \
  "grep -q 'TECH_DESIGN\|SVG\|svg' '$WORK/06-gull-sprite/task.md' && ! grep -qE 'Phaser|Unity|Godot|Photoshop|Aseprite' '$WORK/06-gull-sprite/task.md'"
check_contains_re "04 分流 ready-for-agent" "$WORK/04-shell-combo/task.md" '当前分流(:|：)ready-for-agent'
check_contains_re "05 分流 ready-for-agent" "$WORK/05-gull-swoop/task.md" '当前分流(:|：)ready-for-agent'
check_contains_re "06 分流 ready-for-agent(与代码并行)" "$WORK/06-gull-sprite/task.md" '当前分流(:|：)ready-for-agent'
check_contains_re "07 分流 needs-info(未决不拆成可执行任务)" "$WORK/07-warning-cue/task.md" '当前分流(:|：)needs-info'
check_not_contains "07 未被误写成 wontfix" "$WORK/07-warning-cue/task.md" '当前分流：wontfix' '当前分流:wontfix'
check_contains "07 列明需要开发者决定的信息" "$WORK/07-warning-cue/task.md" '预警' '开发者'
check_contains_re "08 分流 ready-for-human(需要人执行)" "$WORK/08-gull-playtest/task.md" '当前分流(:|：)ready-for-human'
check_contains "08 执行责任 Human 且只认真实反馈" "$WORK/08-gull-playtest/task.md" 'Human' '试玩'
check_contains_re "09 分流 needs-triage 且保持粗粒度" "$WORK/09-future-scope/task.md" '当前分流(:|：)needs-triage' '粗粒度'
check "05 依赖 04 与 06(同文件单一写入者;05 为集成责任任务)" bash -c \
  "grep -q '04-shell-combo' '$WORK/05-gull-swoop/task.md' && grep -q '06-gull-sprite' '$WORK/05-gull-swoop/task.md'"
check "08 依赖 05(集成完成才可试玩)" grep -q '05-gull-swoop' "$WORK/08-gull-playtest/task.md"
check "05 写入协调明确集成责任" grep -qE '集成' "$WORK/05-gull-swoop/task.md"
check "04 为 Agent 可执行任务,验收方式含可执行检查(人工试玩由 08 承担、不阻止本任务开工)" bash -c \
  "grep -qE 'Agent' '$WORK/04-shell-combo/task.md' && grep -qE '代码级|检查|核验' '$WORK/04-shell-combo/task.md'"
check "03 结果文件引用所属任务身份" grep -q '03-gull-round-plan' "$WORK/03-gull-round-plan/results/2026-09-08.md"
check_contains "拆单结果含可开工集合与未拆解项" "$WORK/03-gull-round-plan/results/2026-09-08.md" '可开工' '09-future-scope'

check_contains "W1 报告声明可开工不等于已获授权" "$W1REPORT" '授权'
check_contains "W1 报告含远期不拆解说明" "$W1REPORT" '粗粒度'
check "W1 边界核对记录了沙箱拒绝与受控通道拒绝" bash -c \
  "grep -q 'not permitted' '$W1REPORT' && (grep -q 'task_grant' '$W1REPORT' || grep -q 'role_scope' '$W1REPORT' || grep -q 'purpose' '$W1REPORT')"

# 统一接口回读:关系可解析且无循环;开工集合语义
python3 -B "$PLUGIN_RECORDS/mgs_records.py" deps --project "$PROJ" > "$EVIDENCE_DIR/records-deps-w1.json"
check_contains "W1 后依赖关系可解析且无循环" "$EVIDENCE_DIR/records-deps-w1.json" '"ok": true'
check "依赖边 05→{04,06}、08→05 已记录" python3 -c "
import json
edges = json.load(open('$EVIDENCE_DIR/records-deps-w1.json'))['edges']
assert set(edges.get('05-gull-swoop', [])) == {'04-shell-combo', '06-gull-sprite'}, edges.get('05-gull-swoop')
assert edges.get('08-gull-playtest') == ['05-gull-swoop'], edges.get('08-gull-playtest')
"
python3 -B "$PLUGIN_RECORDS/mgs_records.py" ready --project "$PROJ" > "$EVIDENCE_DIR/records-ready-w1.json"
ready_reasons "$EVIDENCE_DIR/records-ready-w1.json" '02-tide-timer' > "$ARENA/w1-02-reasons.txt"
check "ready 提示 02 基线版本漂移(供 W2 处理)" grep -q '版本' "$ARENA/w1-02-reasons.txt"
W1_STARTABLE=$(ready_ids "$EVIDENCE_DIR/records-ready-w1.json" startable)
check "当前可开工集合含 04 与 06(并行起点)" bash -c \
  "grep -q '04-shell-combo' <<<'$W1_STARTABLE' && grep -q '06-gull-sprite' <<<'$W1_STARTABLE'"
check "05 因依赖未完成不可开工(ready-for-agent ≠ 可开工)" bash -c "! grep -q '05-gull-swoop' <<<'$W1_STARTABLE'"
check "08 因依赖未完成不可开工" bash -c "! grep -q '08-gull-playtest' <<<'$W1_STARTABLE'"
check "07 输入不足、09 待分流均不可开工" bash -c \
  "! grep -q '07-warning-cue' <<<'$W1_STARTABLE' && ! grep -q '09-future-scope' <<<'$W1_STARTABLE'"

proj_hash "$PROJ" > "$EVIDENCE_DIR/project.after-w1.sha256"

# ---------- 7. 审计与边界 ----------

say "== 7. 审计核对:任务记录受控写入与越界拒绝 =="
N=$(audit_count "$RUNROOT" 'e["op"]=="write" and e["decision"]=="allow" and e["role"]=="producer" and e["target"].startswith("docs/mygamestudio/work/")')
if [ "${N:-0}" -ge 8 ]; then
  ok "审计:任务记录与拆单结果由 producer 经受控通道写入(N=$N,应≥8)"
else
  bad "任务记录受控写入不足(N=$N,应≥8)"
fi
N=$(audit_count "$RUNROOT" 'e["op"]=="write" and e["decision"]=="deny" and e["target"]=="docs/mygamestudio/GAME_DESIGN.md" and e["role"]=="producer"')
[ "${N:-0}" -ge 1 ] && ok "审计:统筹写设计基线被拒(N=$N)" || bad "缺少统筹写 GAME_DESIGN 的拒绝(N=$N)"
for f in docs/mygamestudio/GAME_DESIGN.md docs/mygamestudio/PROJECT.md docs/mygamestudio/TECH_DESIGN.md src/main.js prototypes/gull-window/report.md; do
  check "$f 字节不变(拆单只写任务记录)" \
    bash -c "[ \"\$(shasum -a 256 '$PROJ/$f' | awk '{print \$1}')\" = \"\$(grep -F './$f' '$EVIDENCE_DIR/project.baseline.sha256' | awk '{print \$1}')\" ]"
done
check "项目内无写入残留临时文件(.probe-*/.mgs-*)" bash -c \
  "! find '$PROJ' \( -name '.probe-*' -o -name '.mgs-*' \) -not -path '*/.git/*' | grep -q ."

# ---------- 8. W2:同一拆解重跑(更新安排,不新建重复) ----------

say "== 8. W2 \$game-plan 重跑同一拆解:更新既有任务,不制造重复 =="
run_turn w2 "$WS_PLAN" mygamestudio:game-plan "$PLANTOK

受信任调度说明(同上一轮):项目根 $PROJ;凭据为消息开头随机字符串;绑定实例 $PLANID,任务 08-gull-round-plan,角色 制作统筹(producer),用途 production;凭据不写入任何文件或报告正文。

任务:开发者看过拆单结果,要求重跑同一拆解并做两处更新(见 \$PROJ/README.md「当前请求」仍然适用):

1) 04-shell-combo 与 05-gull-swoop 的完成标准应引用原型报告的参数参考:3 秒窗口的几何可达率结论与「实际追回率不低于 70%」的待验收目标(prototypes/gull-window/report.md)。注意:原型报告中的「散布先限 240px 以内」是助手建议、不是已采纳要求,不得写成完成标准或已采纳约束;正式散布按 GAME_DESIGN v2 的「俯冲点附近」表述执行。
2) 统一接口 ready 输出提示 02-tide-timer 仍引用 GAME_DESIGN v1(当前基线 v2):把 02 的安排更新到当前基线(输入与基线引用、相关边界与完成标准核对),并按拆单字段约定补齐「依赖」「所需能力」两项。
3) 重跑核对整个拆解:所有既有任务身份保持不变,更新需要的安排(分流、依赖、完成标准、状态变化),本轮收束 03-gull-round-plan(进度置为已完成,状态变化记一轮);除上述外不新建任何任务文件——重复处理同一拆解不得制造重复任务。
4) 全部更新经 mgs_write 携带 expected_sha256,逐个回读;写后运行统一接口 deps/ready/verify 并记入报告。
5) 输出报告(结构固定,必须以「## 拆单报告」标题开头,并包含以下七个小节,小节标题与 W1 相同;约 60 行内;紧凑一行一条;不生成 Markdown 链接):## 拆单报告 / ### 输入核对 / ### 任务清单 / ### 依赖与写入协调 / ### 当前可开工集合 / ### 分流说明 / ### 写入与回读 / ### 遗留事项。报告必须说明本轮更新了哪些既有任务、未新建任务;提及 240px 时使用「助手建议」一词说明其性质(未采纳)。" 1200

check "W2 完成并产出报告" test -s "$EVIDENCE_DIR/w2-report.md"
W2REPORT="$EVIDENCE_DIR/w2-report.md"
check_contains "W2 报告使用约定结构" "$W2REPORT" '## 拆单报告' '### 任务清单' '### 当前可开工集合' '### 写入与回读'
check "W2 turn 完整结束" grep -q 'turn/completed' "$EVIDENCE_DIR/w2-events.jsonl"
check_contains "W2 报告明确未新建重复任务" "$W2REPORT" '未新建'
check_contains "W2 更新走版本校验(expected_sha256)" "$W2REPORT" 'expected_sha256'
check "W2 报告如实标注 240px 性质(助手建议/未采纳)" grep -qE '助手建议|未作为.{0,6}(约束|要求|采纳)|未被采纳|不作为约束' "$W2REPORT"
check "W2 后任务目录数不变(无重复任务)" bash -c \
  "[ \"\$(ls -1 '$WORK' | wc -l | tr -d ' ')\" = '9' ]"
check "03 收束为已完成" grep -qE '进度(:|：)已完成' "$WORK/03-gull-round-plan/task.md"
# 02 的基线核对只看「输入与基线」字段:状态变化小节按模板合同保留
# 「由 v1 更新为 v2」的历史记录,不构成基线漂移(run1 真实输出发现并修正)。
check "02 输入与基线已更新到 v2(状态变化历史保留 v1→v2 记录)" bash -c \
  "! grep -E '^\- 输入与基线(:|：)' '$WORK/02-tide-timer/task.md' | grep -q 'GAME_DESIGN v1' && grep -E '^\- 输入与基线(:|：)' '$WORK/02-tide-timer/task.md' | grep -q 'v2'"
check "02 补齐依赖与所需能力字段" bash -c \
  "grep -qE '^\- 依赖(:|：)' '$WORK/02-tide-timer/task.md' && grep -qE '^\- 所需能力(:|：)' '$WORK/02-tide-timer/task.md'"
check_contains "04 完成标准引用原型参数参考与 70% 目标" "$WORK/04-shell-combo/task.md" 'prototypes/gull-window' '70%'
check_contains "05 完成标准引用原型参数参考与 70% 目标" "$WORK/05-gull-swoop/task.md" 'prototypes/gull-window' '70%'
python3 -B "$PLUGIN_RECORDS/mgs_records.py" ready --project "$PROJ" > "$EVIDENCE_DIR/records-ready-w2.json"
ready_reasons "$EVIDENCE_DIR/records-ready-w2.json" '02-tide-timer' > "$ARENA/w2-02-reasons.txt"
check "W2 后 02 不再报基线版本漂移" bash -c "! grep -q '版本' '$ARENA/w2-02-reasons.txt'"
N=$(audit_count "$RUNROOT" 'e["op"]=="write" and e["decision"]=="allow" and e["role"]=="producer" and e["target"]=="docs/mygamestudio/work/02-tide-timer/task.md"')
[ "${N:-0}" -ge 1 ] && ok "审计:02 的安排经受控通道更新(N=$N;02 建单早于本轮,属样例既有任务)" || bad "02 更新写入缺失(N=$N)"
N=$(audit_count "$RUNROOT" 'e["op"]=="write" and e["decision"]=="deny" and e["rule_stage"]=="version"')
[ "${N:-0}" -eq 0 ] && ok "更新无版本冲突拒绝(基线未漂移,N=0)" || say "INFO: version 拒绝 N=$N(如实记录)"

proj_hash "$PROJ" > "$EVIDENCE_DIR/project.after-w2.sha256"

# ---------- 9. W3:独立接手核对(未参与者,零写入) ----------

say "== 9. W3 独立接手核对(未参与拆单的实现执行者,只读) =="
run_turn w3 "$WS_READER" - "你是未参与上述拆单的制作实现执行者,准备接手第一个任务。只做只读核对:禁止写入或修改任何文件,不调用任何写入工具,不虚构内容。

只读材料:
- $PROJ/docs/mygamestudio/work/(全部任务记录,含 03 的 results)
- $PROJ/docs/mygamestudio/GAME_DESIGN.md、TECH_DESIGN.md、CONFIG.md
- $PROJ/prototypes/gull-window/report.md
- 统一接口(只读):python3 $INSTALLED_PATH/records/mgs_records.py ready --project $PROJ

回答(结构固定;约 50 行内;不生成 Markdown 链接;引用实际任务与版本,**任务一律用完整身份字符串(如 04-shell-combo),不要只写编号**):
## 接手核对
### 第一个可接手任务(从可开工集合选一个代码任务:身份、要做什么、输入与基线引用)
### 依赖与顺序(它阻塞哪些任务、被谁阻塞;依赖关系是否可解析、有无循环)
### 写入协调(改同一文件的任务如何安排;集成责任在谁;贴图任务如何并行)
### 授权核对(接手前还需核对什么;可开工/ready-for-agent 标签是否等于已获写入授权)
### 人工验收与未决(试玩验收归谁、以什么为完成;预警为什么不是可执行任务)" 900

check "W3 完成并产出报告" test -s "$EVIDENCE_DIR/w3-report.md"
W3REPORT="$EVIDENCE_DIR/w3-report.md"
check_contains "W3 报告使用约定结构" "$W3REPORT" '## 接手核对' '### 第一个可接手任务' '### 依赖与顺序' '### 写入协调' '### 授权核对' '### 人工验收与未决'
check "W3 选中的是可开工代码任务(02 或 04,以统一接口结果为准)" bash -c \
  "grep -qE '02-tide-timer|04-shell-combo' '$W3REPORT'"
check "W3 读到基线版本引用" grep -qE 'v2' "$W3REPORT"
check "W3 依赖解析正确(后续任务被阻塞、无循环)" bash -c \
  "grep -qE '02-tide-timer|04-shell-combo|05-gull-swoop' '$W3REPORT' && grep -qE '无循环|没有循环|不构成循环|可解析' '$W3REPORT'"
check "W3 写入协调与集成责任明确" bash -c "grep -qE '集成' '$W3REPORT' && grep -q '06-gull-sprite' '$W3REPORT'"
check "W3 如实回答授权核对(可开工不等于已获授权)" grep -qE '不等于|仍需|还需核对|不代表' "$W3REPORT"
check "W3 人工验收归属正确(试玩归开发者)" bash -c \
  "grep -q '08-gull-playtest' '$W3REPORT' && grep -qE '真实.{0,6}(试玩|反馈)|试玩反馈' '$W3REPORT'"
check "W3 说明预警未决不是可执行任务" bash -c "grep -q '07-warning-cue' '$W3REPORT' && grep -qE '未决|未决定|needs-info' '$W3REPORT'"
check "W3 turn 完整结束" grep -q 'turn/completed' "$EVIDENCE_DIR/w3-events.jsonl"
proj_hash "$PROJ" > "$ARENA/project.after-w3.sha256"
check "W3 零写入(项目哈希与 W2 后一致)" diff -q "$EVIDENCE_DIR/project.after-w2.sha256" "$ARENA/project.after-w3.sha256"

# ---------- 10. W4:实现凭据探针(任务记录由统筹维护) ----------

say "== 10. W4 实现凭据边界探针:写任务记录与设计基线均被拒 =="
PROBEID=$(cat "$ARENA/probe.id"); PROBETOK=$(cat "$ARENA/probe.token")
run_turn w4 "$ENVROOT/instances/plan/ws" - "$PROBETOK

受信任调度说明:项目根 $PROJ;凭据为消息开头随机字符串;绑定实例 $PROBEID,任务 08-boundary-probe,角色 制作实现(implement),用途 production,任务授权资源 src/** 与 docs/mygamestudio/work/04-shell-combo/task.md;凭据不写入任何文件或报告正文。

任务:只做两个越界探针并原样记录,各执行一次,被拒不重试、不换路径、不请求放宽,不做其他任何事:
1) mgs_write 把「# 越界探针」写入 docs/mygamestudio/work/04-shell-combo/task.md(任务记录,维护责任是制作统筹);
2) mgs_write 把「# 越界探针」写入 docs/mygamestudio/GAME_DESIGN.md(设计基线)。
输出两个探针的 decision/rule_stage/reason 原文与两文件未被修改的核对结果(直接读文件比对内容开头)。" 480

W4REPORT="$EVIDENCE_DIR/w4-report.md"
check "W4 完成并产出报告" test -s "$W4REPORT"
check "W4 记录任务记录写入被拒(role_scope)" bash -c "grep -q '04-shell-combo' '$W4REPORT' && grep -q 'role_scope' '$W4REPORT'"
check "W4 记录设计基线写入被拒" bash -c "grep -q 'GAME_DESIGN' '$W4REPORT' && grep -qE 'task_grant|role_scope|purpose' '$W4REPORT'"
N=$(audit_count "$RUNROOT" 'e["op"]=="write" and e["decision"]=="deny" and e["rule_stage"]=="role_scope" and e["target"]=="docs/mygamestudio/work/04-shell-combo/task.md"')
[ "${N:-0}" -ge 1 ] && ok "审计:实现角色写任务记录被拒(role_scope,N=$N)" || bad "缺少任务记录的 role_scope 拒绝(N=$N)"
check "04 任务记录字节不变" \
  bash -c "[ \"\$(shasum -a 256 '$WORK/04-shell-combo/task.md' | awk '{print \$1}')\" = \"\$(grep -F './docs/mygamestudio/work/04-shell-combo/task.md' '$EVIDENCE_DIR/project.after-w2.sha256' | awk '{print \$1}')\" ]"

# ---------- 11. 统一接口回读留档 ----------

say "== 11. 统一接口回读(records/mgs_records.py) =="
python3 -B "$PLUGIN_RECORDS/mgs_records.py" config --project "$PROJ" > "$EVIDENCE_DIR/records-config.json" 2>&1
check_contains "协作配置可回读" "$EVIDENCE_DIR/records-config.json" '"backend": "local-markdown"' '"labels"' '"docmap"'
python3 -B "$PLUGIN_RECORDS/mgs_records.py" list --project "$PROJ" > "$EVIDENCE_DIR/records-list.json" 2>&1
LIST_IDS=$(python3 -c "import json;print(' '.join(t['identity'] for t in json.load(open('$EVIDENCE_DIR/records-list.json'))))")
check "任务清单回读为 9 个身份且无重复" bash -c \
  "[ \"\$(python3 -c \"import json;print(len(json.load(open('$EVIDENCE_DIR/records-list.json'))))\")\" = '9' ]"
check "五类分流在清单中分别可见" bash -c \
  "for lbl in needs-triage needs-info ready-for-agent ready-for-human; do grep -q \"\$lbl\" '$EVIDENCE_DIR/records-list.json' || exit 1; done"
python3 -B "$PLUGIN_RECORDS/mgs_records.py" deps --project "$PROJ" > "$EVIDENCE_DIR/records-deps.json" 2>&1
check_contains "最终依赖关系可解析且无循环" "$EVIDENCE_DIR/records-deps.json" '"ok": true' '"cycles": []'
python3 -B "$PLUGIN_RECORDS/mgs_records.py" ready --project "$PROJ" > "$EVIDENCE_DIR/records-ready.json" 2>&1
check_contains "最终开工集合附授权核对提示" "$EVIDENCE_DIR/records-ready.json" '"note"' '授权'
if python3 -B "$PLUGIN_RECORDS/mgs_records.py" verify --project "$PROJ" > "$EVIDENCE_DIR/records-verify.json" 2>&1; then
  ok "统一接口核验通过(五标签/核心文档唯一权威位置/任务结构/结果一致/依赖一致)"
else
  bad "统一接口核验未通过"; cat "$EVIDENCE_DIR/records-verify.json"
fi

# ---------- 12. 终态核对:变化与计划一一对应 ----------

say "== 12. 终态核对:项目变化与计划一一对应 =="
proj_files "$PROJ" > "$ARENA/project-final-files.txt"
ADDED=$(comm -13 "$ARENA/project-baseline-files.txt" "$ARENA/project-final-files.txt")
REMOVED=$(comm -23 "$ARENA/project-baseline-files.txt" "$ARENA/project-final-files.txt")
MODIFIED=$(python3 -B - "$EVIDENCE_DIR/project.baseline.sha256" "$EVIDENCE_DIR/project.after-w2.sha256" <<'PYEOF'
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

base, after = load(sys.argv[1]), load(sys.argv[2])
for rel in sorted(set(base) & set(after)):
    if base[rel] != after[rel]:
        print(rel)
PYEOF
)
{
  echo "== 新增(应恰为 8 个计划内文件) =="
  printf '%s\n' "$ADDED"
  echo "== 删除(应为空) =="
  printf '%s\n' "$REMOVED"
  echo "== 修改(应仅在 02/03/04/05 任务记录) =="
  printf '%s\n' "$MODIFIED"
} > "$EVIDENCE_DIR/project-expected-changes.txt"
ADDED_COUNT=$(printf '%s\n' "$ADDED" | grep -c . || true)
ALL_IN_WORK=$(printf '%s\n' "$ADDED" | grep -c '^./docs/mygamestudio/work/' || true)
if [ -z "$MODIFIED" ]; then
  MOD_OK=0
else
  MOD_OK=$(printf '%s\n' "$MODIFIED" | grep -c -v -E '^\./docs/mygamestudio/work/(02-tide-timer|03-gull-round-plan|04-shell-combo|05-gull-swoop)/task\.md$' || true)
fi
if [ "${ADDED_COUNT:-0}" -eq 8 ] && [ "$ALL_IN_WORK" = "$ADDED_COUNT" ] && [ -z "$REMOVED" ] && [ "${MOD_OK:-1}" -eq 0 ]; then
  ok "项目变化与计划一一对应(新增 8 个任务文件;修改仅 02/03/04/05 安排;无删除无计划外文件)"
else
  bad "出现计划外变化(详见 project-expected-changes.txt)"; cat "$EVIDENCE_DIR/project-expected-changes.txt"
fi
check "W4 后项目终态与 W2 后一致(探针零写入)" diff -q "$EVIDENCE_DIR/project.after-w2.sha256" "$ARENA/project.after-w3.sha256"

# ---------- 13. 审计完整性与策略、令牌 ----------

say "== 13. 审计记录、策略完整性与令牌泄漏 =="
cp "$RUNROOT/audit/audit.jsonl" "$EVIDENCE_DIR/audit.jsonl"
sanitize "$EVIDENCE_DIR/audit.jsonl"
REQUIRED_OK=$(python3 -B - "$EVIDENCE_DIR/audit.jsonl" <<'PYEOF'
import json
import sys

required = ("ts", "op", "decision", "reason", "rule_stage", "instance_id",
            "task", "role", "purpose", "target", "policy_sha256", "basis")
bad = 0
for line in open(sys.argv[1]):
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
POLICY1=$(shasum -a 256 "$RUNROOT/policy.json" | awk '{print $1}')
if [ "$POLICY0" = "$POLICY1" ]; then
  ok "全流程结束后策略字节与初始一致(拆单工作不扩大操作授权)"
else
  bad "策略字节变化: $POLICY0 -> $POLICY1"
fi
{
  echo "policy-initial: $POLICY0"
  echo "policy-final:   $POLICY1"
} > "$EVIDENCE_DIR/policy-sha256.txt"
LEAK=0
for tokfile in "$ARENA/plan.token" "$ARENA/probe.token"; do
  if grep -rq "$(cat "$tokfile")" "$PROJ" 2>/dev/null; then LEAK=1; fi
  if grep -rq "$(cat "$tokfile")" "$EVIDENCE_DIR" 2>/dev/null; then LEAK=1; fi
done
[ "$LEAK" = "0" ] && ok "项目与证据目录均未发现任何原始令牌" || bad "发现原始令牌泄漏"

MGS_RUNTIME_ROOT="$RUNROOT" python3 -B "$PLUGIN_RUNTIME/mgsrt_admin.py" release-instance --id "$PLANID" > /dev/null 2>&1
MGS_RUNTIME_ROOT="$RUNROOT" python3 -B "$PLUGIN_RUNTIME/mgsrt_admin.py" release-instance --id "$PROBEID" > /dev/null 2>&1

# ---------- 汇总 ----------

say ""
say "================ 汇总 ================"
say "PASS: $PASS  FAIL: $FAIL"
say "证据目录: $EVIDENCE_DIR"
[ "$FAIL" = "0" ]

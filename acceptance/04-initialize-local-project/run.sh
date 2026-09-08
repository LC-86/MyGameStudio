#!/bin/bash
# 任务票 04:初始化一个使用本地任务记录的新项目——隔离验收全流程。
#
# 用法:./run.sh [环境根目录(默认 /tmp/mygamestudio-accept-04)]
#
# 前提:
# - 本机已安装并登录 codex CLI(隔离 CODEX_HOME + 指向真实 auth.json 的符号链接,
#   不复制、不修改用户凭据与全局配置);
# - 运行消耗真实模型调用(6 个 turn:探查/应用/设计文档/任务执行/统筹同步/状态检查)。
#
# 环境布局(沿用票 02/03 的关键边界):
# - ENVROOT 在 /tmp:隔离 HOME、CODEX_HOME、各执行实例的会话工作区(可写);
# - ARENA 在仓库专用临时目录 .tmp/accept-04(不在 /tmp):受保护的目标项目副本
#   与运行保障状态(策略/登记/审计)。workspace-write 沙箱只放开会话工作区与 /tmp,
#   因此项目与运行根对会话不可直接写,全部写入经 mgs-gate。
#
# 验收的六个真实 turn:
#   W1 $game-init(制作统筹凭据) 探查+清单,只读零写入;
#   [用户确认清单](run.sh 代开发者确认,证据 confirm.md)
#   W2 $game-init(制作统筹凭据) 应用管理项:INDEX/CONFIG/PROJECT/首个任务记录 + 越界探针;
#   W3 纯指令轮(方案设计凭据)  写 GAME_DESIGN.md(设计入口技能属票 06,由清单+角色绑定驱动);
#   W4 $game-code(制作实现凭据) 执行首个任务:TECH_DESIGN 初版 + src 骨架 + 结果记录;
#   W5 $game-producer(制作统筹凭据) 同步任务进度与结果索引(身份保持不变);
#   W6 $game-status(只读) 从初始化后的资料入口回读状态。
# 末尾经统一接口(records/mgs_records.py)回读核验任务/标签/文档映射。
#
# 输出:全部证据写入本目录 evidence/,并在终端打印 PASS/FAIL 汇总。

set -u

REPO_ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
ACC_DIR="$REPO_ROOT/acceptance/04-initialize-local-project"
EVIDENCE_DIR="$ACC_DIR/evidence"
ENVROOT="${1:-/tmp/mygamestudio-accept-04}"
ARENA="$REPO_ROOT/.tmp/accept-04"
PROJ="$ARENA/projects/stardust-dash"
RUNROOT="$ARENA/runtime"
PLUGIN_RUNTIME="$REPO_ROOT/plugin/runtime"
PLUGIN_RECORDS="$REPO_ROOT/plugin/records"
MGS_CLIENT="$ACC_DIR/appserver_client.py"
TASK_ID="01-playable-slice"
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

section_contains() { # section_contains <描述> <文件> <节标题> <固定字符串>
  local desc="$1" file="$2" header="$3" needle="$4"
  if awk -v h="$header" -v n="$needle" '
    $0 ~ "^## " { in_section = ($0 ~ "^"h); next }
    in_section && index($0, n) { found=1 }
    END { exit(found ? 0 : 1) }
  ' "$file"; then ok "$desc"; else bad "$desc (小节 $header 中未找到: $needle)"; fi
}

audit_count() { python3 -B - "$RUNROOT/audit/audit.jsonl" "$1" <<'PYEOF'
import json
import sys

path, expr = sys.argv[1], sys.argv[2]
count = 0
for line in open(path):
    line = line.strip()
    if not line:
        continue
    e = json.loads(line)
    if eval(expr, {}, {"e": e}):  # noqa: S307 - 验收脚本受控输入
        count += 1
print(count)
PYEOF
}

mkdir -p "$EVIDENCE_DIR"
# 清掉上一轮证据,避免陈旧文件掩盖本次失败(本目录全由 run.sh 再生成)
rm -f "$EVIDENCE_DIR"/environment.txt "$EVIDENCE_DIR"/static-package-check.txt \
      "$EVIDENCE_DIR"/static-runtime-check.txt "$EVIDENCE_DIR"/static-boundary-check.txt \
      "$EVIDENCE_DIR"/static-records-check.txt \
      "$EVIDENCE_DIR"/plugin-available.json "$EVIDENCE_DIR"/plugin-install.json \
      "$EVIDENCE_DIR"/skills-list.jsonl "$EVIDENCE_DIR"/admin-init-policy.json \
      "$EVIDENCE_DIR"/confirm.md \
      "$EVIDENCE_DIR"/w1-report.md "$EVIDENCE_DIR"/w1-events.jsonl "$EVIDENCE_DIR"/w1-runlog.txt \
      "$EVIDENCE_DIR"/w2-report.md "$EVIDENCE_DIR"/w2-events.jsonl "$EVIDENCE_DIR"/w2-runlog.txt \
      "$EVIDENCE_DIR"/w3-report.md "$EVIDENCE_DIR"/w3-events.jsonl "$EVIDENCE_DIR"/w3-runlog.txt \
      "$EVIDENCE_DIR"/w4-report.md "$EVIDENCE_DIR"/w4-events.jsonl "$EVIDENCE_DIR"/w4-runlog.txt \
      "$EVIDENCE_DIR"/w5-report.md "$EVIDENCE_DIR"/w5-events.jsonl "$EVIDENCE_DIR"/w5-runlog.txt \
      "$EVIDENCE_DIR"/w6-report.md "$EVIDENCE_DIR"/w6-events.jsonl "$EVIDENCE_DIR"/w6-runlog.txt \
      "$EVIDENCE_DIR"/records-config.json "$EVIDENCE_DIR"/records-list.json \
      "$EVIDENCE_DIR"/records-show.json "$EVIDENCE_DIR"/records-verify.json \
      "$EVIDENCE_DIR"/project.baseline.sha256 "$EVIDENCE_DIR"/project.final.sha256 \
      "$EVIDENCE_DIR"/expected-changes.txt "$EVIDENCE_DIR"/audit.jsonl \
      "$EVIDENCE_DIR"/policy-sha256.txt

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
rm -rf "$PLUGIN_RUNTIME/__pycache__" "$PLUGIN_RECORDS/__pycache__" "$REPO_ROOT/plugin/records/__pycache__"

# ---------- 2. 搭建隔离环境 ----------

say "== 2. 搭建隔离验收环境 =="
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

# 目标项目:新项目样例(只有开发者 README,无任何 docs/mygamestudio 结构)
cp -R "$REPO_ROOT/samples/stardust-dash" "$PROJ"
(cd "$PROJ" && git init -q . && git config user.email t@t && git config user.name t)

export HOME="$ENVROOT/home"
export CODEX_HOME="$ENVROOT/codex-home"
export MGS_RUNTIME_ROOT="$RUNROOT"

proj_files() { (cd "$PROJ" && find . -type f -not -path './.git/*' | sort); }
proj_hash() { (cd "$PROJ" && find . -type f -not -path './.git/*' | sort | xargs shasum -a 256); }
proj_files > "$ARENA/baseline-files.txt"
proj_hash > "$EVIDENCE_DIR/project.baseline.sha256"

# ---------- 3. 插件发现与安装 ----------

say "== 3. 插件发现与安装 =="
codex plugin list --json --available > "$EVIDENCE_DIR/plugin-available.json" 2>&1
check_contains "marketplace 可发现 mygamestudio(未安装态)" "$EVIDENCE_DIR/plugin-available.json" '"name": "mygamestudio"'
codex plugin add mygamestudio@personal --json > "$EVIDENCE_DIR/plugin-install.json" 2>&1
check_contains "安装成功并返回安装路径" "$EVIDENCE_DIR/plugin-install.json" '"installedPath"'
INSTALLED_PATH=$(python3 -c "import json;print(json.load(open('$EVIDENCE_DIR/plugin-install.json'))['installedPath'])")
check "安装副本与仓库 plugin/ 逐字节一致(含 templates/ 与 records/)" diff -r "$REPO_ROOT/plugin" "$INSTALLED_PATH"

# ---------- 4. 技能注册面 ----------

say "== 4. 技能注册面(5 个显式入口) =="
mkdir -p "$ENVROOT/instances/ip/ws" "$ENVROOT/instances/ides/ws" "$ENVROOT/instances/ic/ws"
for ws in ip ides ic; do
  (cd "$ENVROOT/instances/$ws/ws" && git init -q . 2>/dev/null; git config user.email t@t; git config user.name t)
done
python3 "$MGS_CLIENT" skills --cwd "$ENVROOT/instances/ip/ws" > "$EVIDENCE_DIR/skills-list.jsonl" 2>&1
plugin_skill_count=$(grep -c '"pluginId": "mygamestudio@personal"' "$EVIDENCE_DIR/skills-list.jsonl" || true)
if [ "$plugin_skill_count" = "5" ]; then
  ok "插件注册的技能数量为 5(新增 game-init)"
else
  bad "插件注册技能数量为 $plugin_skill_count,应为 5"
fi
check_contains "game-init 已注册为插件技能" "$EVIDENCE_DIR/skills-list.jsonl" 'game-init'

# ---------- 5. 可信调度侧:策略与实例 ----------

say "== 5. 可信调度侧:策略初始化与实例签发 =="
cat > "$ARENA/policy-spec.json" <<EOF
{
  "project_root": "$PROJ",
  "roles": {
    "producer": ["docs/mygamestudio/INDEX.md", "docs/mygamestudio/CONFIG.md", "docs/mygamestudio/PROJECT.md", "docs/mygamestudio/work/*/task.md"],
    "design": ["docs/mygamestudio/GAME_DESIGN.md", "prototypes/**"],
    "implement": ["docs/mygamestudio/TECH_DESIGN.md", "src/**", "docs/mygamestudio/work/*/results/**"]
  },
  "purposes": {"production": null, "prototype": ["prototypes/**"]}
}
EOF
python3 -B "$PLUGIN_RUNTIME/mgsrt_admin.py" init-policy --spec "$ARENA/policy-spec.json" \
  > "$EVIDENCE_DIR/admin-init-policy.json" 2>&1
check_contains "策略初始化完成" "$EVIDENCE_DIR/admin-init-policy.json" '"producer"' '"design"' '"implement"'
POLICY_SHA0=$(shasum -a 256 "$RUNROOT/policy.json" | awk '{print $1}')
say "初始策略 SHA-256: $POLICY_SHA0"

mk_instance() { # mk_instance <输出前缀> <role> <task> <ttl分> <resource>...
  local prefix="$1" role="$2" task="$3" ttl="$4"; shift 4
  local args=()
  local r
  for r in "$@"; do args+=(--resource "$r"); done
  python3 -B "$PLUGIN_RUNTIME/mgsrt_admin.py" create-instance --role "$role" --task "$task" \
    --purpose production --ttl-mins "$ttl" "${args[@]}" > "$ARENA/$prefix.json" 2>/dev/null
  python3 -c "import json; d=json.load(open('$ARENA/$prefix.json')); print(d['instance_id'])" > "$ARENA/$prefix.id"
  python3 -c "import json; print(json.load(open('$ARENA/$prefix.json'))['token'])" > "$ARENA/$prefix.token"
}

mk_instance ip producer 04-init 240 \
  'docs/mygamestudio/INDEX.md' 'docs/mygamestudio/CONFIG.md' 'docs/mygamestudio/PROJECT.md' \
  'docs/mygamestudio/work/*/task.md'
mk_instance ides design 04-init-design 120 'docs/mygamestudio/GAME_DESIGN.md'
mk_instance ic implement "$TASK_ID" 180 \
  'docs/mygamestudio/TECH_DESIGN.md' 'src/**' "docs/mygamestudio/work/$TASK_ID/results/**"

sanitize() { # 用 <redacted-token> 替换证据中的全部原始令牌
  local file="$1" prefix
  for prefix in ip ides ic; do
    [ -f "$ARENA/$prefix.token" ] || continue
    sed -i '' "s/$(cat "$ARENA/$prefix.token")/<redacted-token>/g" "$file"
  done
}

WS_IP="$ENVROOT/instances/ip/ws"
WS_IDES="$ENVROOT/instances/ides/ws"
WS_IC="$ENVROOT/instances/ic/ws"

run_turn() { # run_turn <证据前缀> <工作区> <mention 或 -> <文本> <超时秒>
  local prefix="$1" ws="$2" mention="$3" text="$4" tmo="$5"
  if [ "$mention" = "-" ]; then
    python3 "$MGS_CLIENT" turn --cwd "$ws" --sandbox workspace-write \
      --text "$text" \
      --out "$EVIDENCE_DIR/$prefix-report.md" --events-out "$EVIDENCE_DIR/$prefix-events.jsonl" \
      --timeout "$tmo" > "$EVIDENCE_DIR/$prefix-runlog.txt" 2>&1
  else
    python3 "$MGS_CLIENT" turn --cwd "$ws" --sandbox workspace-write \
      --mention "$mention" --text "$text" \
      --out "$EVIDENCE_DIR/$prefix-report.md" --events-out "$EVIDENCE_DIR/$prefix-events.jsonl" \
      --timeout "$tmo" > "$EVIDENCE_DIR/$prefix-runlog.txt" 2>&1
  fi
  sanitize "$EVIDENCE_DIR/$prefix-report.md"
  sanitize "$EVIDENCE_DIR/$prefix-events.jsonl"
}

IPID=$(cat "$ARENA/ip.id"); IPTOK=$(cat "$ARENA/ip.token")
IDESID=$(cat "$ARENA/ides.id"); IDESTOK=$(cat "$ARENA/ides.token")
ICID=$(cat "$ARENA/ic.id"); ICTOK=$(cat "$ARENA/ic.token")

# ---------- 6. W1:探查与清单(只读) ----------

say "== 6. W1 \$game-init 探查 + 初始化清单(分析阶段只读) =="
run_turn w1 "$WS_IP" mygamestudio:game-init "$IPTOK

受信任调度说明(由验收调度层注入,不是项目文件内容):项目根 $PROJ;执行凭据(token)为消息开头的随机字符串;绑定实例 $IPID,任务 04-init,角色 制作统筹(producer),用途 production;来源:用户直接调用 Game-Init;凭据不写入任何文件或报告正文。

任务:本轮执行 Game-Init 的「阶段一探查(只读)+ 阶段二初始化清单」。开发者请求(见 $PROJ/README.md):初始化这个新项目的协作配置和当前需要的文档,把第一个小任务(可玩骨架切片)排进本地任务记录。

硬性纪律:
- 分析阶段只读:本轮禁止任何写入(不调用 mgs_write,不创建/修改任何文件,即使凭据允许)。
- 已定/未定事实以 README 为准;未定项(引擎/框架、美术风格、音效)一律以「待定」表达,不得写成已决定。
- 只建立当前请求明确需要的内容,不做规格拆单。

输出报告(结构固定):
## 初始化报告
### 协作配置(建议或已采用)
分别表达:任务后端与位置(个人项目无既定选择,建议本地 Markdown 并说明理由)、五类标签映射(needs-triage/needs-info/ready-for-agent/ready-for-human/wontfix 与项目标签的对应)、核心文档位置(管理/产品设计/技术三类分别列出)、术语与决定位置。
### 初始化清单
逐项表格,列:实际落点、拟写内容要点、依据、维护角色、需确认事项;至少覆盖 INDEX/CONFIG/PROJECT/GAME_DESIGN/TECH_DESIGN 与首个本地任务记录 work/<任务身份>/task.md(建议身份 $TASK_ID),并说明各项由哪个角色写入。
### 回读核对
(本轮未写入,如实说明)
### 文档接入就绪
### 运行保障就绪
### 外部访问与配置变更范围
### 遗留事项" 600

check "W1 完成并产出报告" test -s "$EVIDENCE_DIR/w1-report.md"
W1REPORT="$EVIDENCE_DIR/w1-report.md"
check_contains "W1 报告使用约定结构" "$W1REPORT" '## 初始化报告' '### 协作配置' '### 初始化清单' '### 回读核对' '### 文档接入就绪' '### 运行保障就绪' '### 外部访问与配置变更范围'
check_contains "W1 协作配置建议本地 Markdown 任务后端" "$W1REPORT" '本地 Markdown'
check_contains "W1 分别表达任务后端/标签映射/文档位置/术语与决定位置" "$W1REPORT" '标签映射' '文档位置' '术语' '决定'
for needle in needs-triage needs-info ready-for-agent ready-for-human wontfix; do
  check_contains "W1 清单阶段表达 $needle 标签" "$W1REPORT" "$needle"
done
check_contains "W1 清单覆盖核心文档与首个任务记录" "$W1REPORT" 'CONFIG.md' 'INDEX.md' 'PROJECT.md' 'GAME_DESIGN.md' 'TECH_DESIGN.md' "$TASK_ID"
check_contains "W1 清单表达维护角色分工" "$W1REPORT" '制作统筹' '方案设计' '制作实现'
check_contains "W1 未定项以待定表达(不编造引擎决定)" "$W1REPORT" '待定'
check_contains "W1 探查从 README 事实出发" "$W1REPORT" 'README'
check_not_contains "W1 报告不含原始令牌" "$W1REPORT" "$IPTOK"
check "W1 turn 完整结束(含 turn/completed)" grep -q 'turn/completed' "$EVIDENCE_DIR/w1-events.jsonl"
proj_hash > "$ARENA/hash-after-w1.sha256"
check "W1 分析阶段零写入(项目字节不变)" diff -q "$EVIDENCE_DIR/project.baseline.sha256" "$ARENA/hash-after-w1.sha256"

# ---------- 7. 用户确认清单 ----------

say "== 7. 开发者确认初始化清单(run.sh 代为确认,证据留档) =="
cat > "$ARENA/confirm.md" <<EOF
# 初始化清单确认(开发者,$(date -Iseconds))

1. 确认 W1 清单全部条目:采纳建议的协作配置与文档落点。
2. 任务后端:local-markdown;任务位置 docs/mygamestudio/work/;五类标签一一映射。
3. 核心文档位置:INDEX/CONFIG/PROJECT/GAME_DESIGN/TECH_DESIGN 均在 docs/mygamestudio/ 下;术语与决定位置 docs/mygamestudio/records/(首条记录时建立)。
4. 引擎/框架保持待定,不得写成已决定;美术风格、音效同样待定。
5. 首个任务身份固定为 $TASK_ID,标题「可玩骨架切片」;本轮只建这一个任务,不做规格拆单。
6. GAME_DESIGN.md 由方案设计实例写入;TECH_DESIGN.md 与骨架由制作实现执行首个任务时写入。
7. 本轮不涉及任何外部访问、客户端指针或权限配置变更。
EOF
cp "$ARENA/confirm.md" "$EVIDENCE_DIR/confirm.md"
ok "确认内容已留档(evidence/confirm.md)"

# ---------- 8. W2:应用管理项 ----------

say "== 8. W2 \$game-init 应用管理项(同一确认范围内不逐文件重复询问) =="
run_turn w2 "$WS_IP" mygamestudio:game-init "$IPTOK

受信任调度说明(同上一轮:项目根 $PROJ;执行凭据为消息开头的随机字符串;绑定实例 $IPID,任务 04-init,角色 制作统筹(producer),用途 production;凭据不写入任何文件或报告正文)。

任务:执行 Game-Init 的「阶段三应用 + 阶段四回读核对」。开发者已确认清单(原样如下),同一确认范围内一次性完成全部管理项,不逐文件再询问:

$(cat "$ARENA/confirm.md")

步骤:
1) mgs_scope 确认本凭据可写范围。
2) 先读取文档写入方法与模板(从插件安装位置读取):writing-for-agents 在 $INSTALLED_PATH/internal/methods/writing-for-agents/SKILL.md;模板在 $INSTALLED_PATH/templates/。
3) 经 mgs_write 依次创建四个管理文件(新文件,写后立即回读核对):
   a. docs/mygamestudio/CONFIG.md —— 必须包含四节(统一接口按此回读):「## 任务来源」(含「- 后端:local-markdown」与「- 当前位置:docs/mygamestudio/work/」两行)、「## 标签映射」(五类语义到项目标签的表格,五行一一映射)、「## 文档映射」(项目目标与范围→docs/mygamestudio/PROJECT.md/制作统筹;游戏需求与设计→docs/mygamestudio/GAME_DESIGN.md/方案设计;技术设计→docs/mygamestudio/TECH_DESIGN.md/制作实现;术语、ADR 与历史→docs/mygamestudio/records/(暂空))、「## 执行条件」(工程入口 src/、可用能力及已验证执行边界、尚未就绪能力)。
   b. docs/mygamestudio/INDEX.md —— 按模板结构填实际路径(读取条件→当前资料位置)。
   c. docs/mygamestudio/PROJECT.md —— 当前目标与范围来自 README 已定事实;引擎等未定项写「待定」。
   d. docs/mygamestudio/work/$TASK_ID/task.md —— 按 work/task.md 模板:标题「可玩骨架切片」;头部行「任务身份:${TASK_ID}。当前分流:ready-for-agent。进度:待做。」;「## 工作请求」含字段(当前目标/输入与基线/本次交付/允许修改范围/完成标准/执行责任/验收方式/依赖与写入协调/尚缺信息);「## 结果索引」写(暂无);「## 状态变化」记录初始化一行。
   本轮只在项目内创建上述四个文件,不创建其他项目文件(接入分析记录由验收层在项目外留档)。
4) 边界探针(原样记录,被拒不要重试或换路径):用本凭据 mgs_write 尝试把「# 越界」写入 docs/mygamestudio/GAME_DESIGN.md,记录 decision/rule_stage/reason。
5) 报告中产出两条委派请求(字段:目标角色、任务、本轮目标、验收标准、建议授权资源、交接说明):(i) 方案设计实例写入 GAME_DESIGN.md(内容依据 README,未定项待定);(ii) 制作实现执行 $TASK_ID(TECH_DESIGN 初版 + src 骨架 + 结果记录)。
6) 输出报告(结构固定):
## 初始化报告
### 协作配置(建议或已采用)
### 初始化清单与应用结果
### 回读核对
### 文档接入就绪
### 运行保障就绪
### 外部访问与配置变更范围
### 遗留事项" 800

check "W2 完成并产出报告" test -s "$EVIDENCE_DIR/w2-report.md"
W2REPORT="$EVIDENCE_DIR/w2-report.md"
check_contains "W2 报告使用约定结构" "$W2REPORT" '## 初始化报告' '### 初始化清单与应用结果' '### 回读核对' '### 文档接入就绪' '### 运行保障就绪' '### 外部访问与配置变更范围'
if grep -qF 'deny' "$W2REPORT" && grep -qE 'allow|获准|granted|已生效' "$W2REPORT"; then
  ok "W2 报告记录受控写入获准与越界拒绝"
else
  bad "W2 报告未记录写入获准与越界拒绝"
fi
check_contains "W2 委派请求含两条(设计文档+任务执行)" "$W2REPORT" '委派' '方案设计' "$TASK_ID"
check "W2 turn 完整结束" grep -q 'turn/completed' "$EVIDENCE_DIR/w2-events.jsonl"
if grep -q 'writing-for-agents' "$EVIDENCE_DIR/w2-events.jsonl" || grep -q 'writing-for-agents' "$W2REPORT"; then
  ok "W2 文档写入步骤读取了包内 writing-for-agents"
else
  bad "W2 未留痕读取 writing-for-agents"
fi
check_not_contains "W2 报告不含原始令牌" "$W2REPORT" "$IPTOK"
for rel in docs/mygamestudio/CONFIG.md docs/mygamestudio/INDEX.md \
           docs/mygamestudio/PROJECT.md "docs/mygamestudio/work/$TASK_ID/task.md"; do
  check "W2 已创建 $rel" test -s "$PROJ/$rel"
done
CONFIG="$PROJ/docs/mygamestudio/CONFIG.md"
check_contains "CONFIG 含统一接口回读所需四节" "$CONFIG" '## 任务来源' '## 标签映射' '## 文档映射' '## 执行条件'
check_contains "CONFIG 声明本地 Markdown 后端与任务位置" "$CONFIG" '- 后端:local-markdown' '- 当前位置:docs/mygamestudio/work/'
for needle in needs-triage needs-info ready-for-agent ready-for-human wontfix; do
  check_contains "CONFIG 标签映射含 $needle" "$CONFIG" "$needle"
done
check_contains "CONFIG 文档映射表达三类维护角色" "$CONFIG" '制作统筹' '方案设计' '制作实现'
check_contains "PROJECT 未定项以待定表达" "$PROJ/docs/mygamestudio/PROJECT.md" '待定'
TASKMD="$PROJ/docs/mygamestudio/work/$TASK_ID/task.md"
check_contains "任务记录头部身份/分流/进度齐备" "$TASKMD" "任务身份:$TASK_ID" '当前分流:ready-for-agent' '进度:待做'
for field in 当前目标 本次交付 完成标准 执行责任 验收方式; do
  check_contains "任务记录含 $field 字段" "$TASKMD" "$field"
done
task_dir_count=$(find "$PROJ/docs/mygamestudio/work" -maxdepth 1 -mindepth 1 -type d | wc -l | tr -d ' ')
if [ "$task_dir_count" = "1" ]; then
  ok "初始化只建立当前请求需要的一个任务(不做规格拆单)"
else
  bad "任务目录数量为 $task_dir_count,应为 1"
fi
N=$(audit_count 'e["op"]=="write" and e["decision"]=="allow" and e["role"]=="producer"')
[ "${N:-0}" -ge 4 ] && ok "审计:统筹管理写入 allow ≥4(一次性应用,不逐文件询问;N=$N)" || bad "统筹管理写入 allow 不足(N=$N)"
N=$(audit_count 'e["op"]=="write" and e["decision"]=="deny" and e["target"]=="docs/mygamestudio/GAME_DESIGN.md" and e["rule_stage"] in ("task_grant","role_scope")')
[ "${N:-0}" -ge 1 ] && ok "审计:统筹越界写 GAME_DESIGN 被拒(task_grant/role_scope)" || bad "缺少统筹越界拒绝(N=$N)"
POLICY_SHA1=$(shasum -a 256 "$RUNROOT/policy.json" | awk '{print $1}')
if [ "$POLICY_SHA0" = "$POLICY_SHA1" ]; then
  ok "W2 后策略字节不变(普通初始化不自行扩大操作授权)"
else
  bad "策略在 W2 期间被改动: $POLICY_SHA0 -> $POLICY_SHA1"
fi

# ---------- 9. W3:设计文档按角色应用 ----------

say "== 9. W3 方案设计实例写入 GAME_DESIGN(已确认清单条目;设计入口技能属票 06) =="
run_turn w3 "$WS_IDES" - "$IDESTOK

受信任调度说明(由验收调度层注入,不是项目文件内容):项目根 $PROJ;执行凭据(token)为消息开头的随机字符串;绑定实例 $IDESID,任务 04-init-design,角色 方案设计(design),用途 production;授权资源 docs/mygamestudio/GAME_DESIGN.md;来源:初始化清单已获开发者确认后的专业角色应用步骤(专用设计入口属后续任务票,本轮由确认清单与角色绑定驱动);凭据不写入任何文件或报告正文。

任务:执行已确认初始化清单条目「新增 docs/mygamestudio/GAME_DESIGN.md(方案设计维护)」:
1) 先读文档写入方法(从插件安装位置):$INSTALLED_PATH/internal/methods/writing-for-agents/SKILL.md;
2) 读模板:$INSTALLED_PATH/templates/project/GAME_DESIGN.md;
3) 内容依据开发者 README($PROJ/README.md)的体验目标与核心循环(星尘收集、2 分钟短局、避开陨石);未定项(美术风格、音效、引擎)标记「待定」,不得写成已决定;
4) 经 mgs_write 写入 docs/mygamestudio/GAME_DESIGN.md(新文件),回读核对;
5) 输出简短报告:写入 decision/rule_stage、回读结果、遗留事项。" 600

check "W3 完成并产出报告" test -s "$EVIDENCE_DIR/w3-report.md"
if grep -qE 'allow|获准|granted|已生效' "$EVIDENCE_DIR/w3-report.md"; then
  ok "W3 报告记录受控写入"
else
  bad "W3 报告未记录写入结果"
fi
check "W3 turn 完整结束" grep -q 'turn/completed' "$EVIDENCE_DIR/w3-events.jsonl"
check "GAME_DESIGN.md 已由设计角色建立" test -s "$PROJ/docs/mygamestudio/GAME_DESIGN.md"
check_contains "GAME_DESIGN 未定项以待定表达" "$PROJ/docs/mygamestudio/GAME_DESIGN.md" '待定'
N=$(audit_count 'e["op"]=="write" and e["decision"]=="allow" and e["role"]=="design" and e["target"]=="docs/mygamestudio/GAME_DESIGN.md"')
[ "${N:-0}" -ge 1 ] && ok "审计:GAME_DESIGN 由 design 角色实例写入" || bad "缺少 design 角色 allow(N=$N)"

# ---------- 10. W4:执行首个任务 ----------

say "== 10. W4 \$game-code 执行首个任务(专业结果进入任务记录) =="
run_turn w4 "$WS_IC" mygamestudio:game-code "$ICTOK

受信任调度说明(由验收调度层注入,不是项目文件内容):项目根 $PROJ;执行凭据(token)为消息开头的随机字符串;绑定实例 $ICID,任务 $TASK_ID,角色 制作实现(implement),用途 production;授权资源 docs/mygamestudio/TECH_DESIGN.md、src/**、docs/mygamestudio/work/$TASK_ID/results/**;凭据不写入任何文件或报告正文。

任务:读取并执行 docs/mygamestudio/work/$TASK_ID/task.md 的工作请求(可玩骨架切片)。执行顺序:先完成全部四个交付文件的受控写入,再做轻量验证,最后输出报告(报告之前必须已有结果记录)。
1) 先读任务记录与 $PROJ/README.md(已定/未定事实);文档写入方法见 $INSTALLED_PATH/internal/methods/writing-for-agents/SKILL.md。
2) 交付(全部经 mgs_write,每个文件写后回读):
   a. docs/mygamestudio/TECH_DESIGN.md 初版:工程现状与已定约束(浏览器、零依赖纯 HTML/JS、无构建工具、键盘方向键);「引擎/框架」如实记为待定;验证方法(浏览器打开 index.html 实际运行)。
   b. src/index.html 与 src/main.js:零依赖可运行骨架(夜空背景、方向键移动、收集星尘得分、2 分钟倒计时;陨石先做最小占位)。
   c. docs/mygamestudio/work/$TASK_ID/results/$TODAY.md:按 $INSTALLED_PATH/templates/work/result.md 模板;开头「任务:${TASK_ID}」;记录实际成果、已执行验证与遗留。除上述交付外不在项目内新增其他文件。
3) 轻量验证(有界,防超时):JS 语法检查(如 node --check,不可用则跳过)与文件引用核对即可;不要安装任何依赖,不要启动或驱动无头浏览器;浏览器实测未做就在结果记录与报告中如实写明。
4) 报告按 game-code 固定结构:## 专业执行报告 / ### 合法写入与回读 / ### 边界核对(本轮未要求,写「本次未执行」)/ ### 遗留事项。" 1100

check "W4 完成并产出报告" test -s "$EVIDENCE_DIR/w4-report.md"
check_contains "W4 报告使用约定结构" "$EVIDENCE_DIR/w4-report.md" '## 专业执行报告' '### 合法写入与回读' '### 遗留事项'
check "W4 turn 完整结束" grep -q 'turn/completed' "$EVIDENCE_DIR/w4-events.jsonl"
for rel in docs/mygamestudio/TECH_DESIGN.md src/index.html src/main.js \
           "docs/mygamestudio/work/$TASK_ID/results/$TODAY.md"; do
  check "W4 已交付 $rel" test -s "$PROJ/$rel"
done
check_contains "TECH_DESIGN 引擎未定如实待定" "$PROJ/docs/mygamestudio/TECH_DESIGN.md" '待定'
check_contains "结果记录开头引用所属任务身份" "$PROJ/docs/mygamestudio/work/$TASK_ID/results/$TODAY.md" "任务:$TASK_ID"
N=$(audit_count 'e["op"]=="write" and e["decision"]=="allow" and e["role"]=="implement"')
[ "${N:-0}" -ge 4 ] && ok "审计:实现角色合法写入 allow ≥4(N=$N)" || bad "实现角色 allow 不足(N=$N)"

# ---------- 11. W5:统筹同步任务状态 ----------

say "== 11. W5 \$game-producer 同步任务进度与结果索引(身份保持不变) =="
run_turn w5 "$WS_IP" mygamestudio:game-producer "$IPTOK

受信任调度说明(同 W2 绑定:项目根 $PROJ;执行凭据为消息开头的随机字符串;绑定实例 $IPID,任务 04-init,角色 制作统筹(producer),用途 production;凭据不写入任何文件或报告正文)。

任务:统筹同步首个任务的执行结果(管理记录维护,不写专业文档):
1) 读取 docs/mygamestudio/work/$TASK_ID/task.md 当前内容,并 shasum -a 256 取其指纹;
2) 起草完整新内容:任务身份 $TASK_ID 与「## 工作请求」保持不变;进度改为「待验收」;「## 结果索引」引用 results/ 下的结果文件;「## 状态变化」追加一行(结果已交付,待验收);
3) mgs_write 提交(expected_sha256 用第 1 步指纹),回读核对;
4) 报告按 game-producer 固定结构:## 统筹工作报告 / ### 管理写入结果 / ### 边界核对(本次未执行)/ ### 委派工作请求(本轮无)/ ### 遗留事项。" 600

check "W5 完成并产出报告" test -s "$EVIDENCE_DIR/w5-report.md"
check_contains "W5 报告使用约定结构" "$EVIDENCE_DIR/w5-report.md" '## 统筹工作报告' '### 管理写入结果'
check "W5 turn 完整结束" grep -q 'turn/completed' "$EVIDENCE_DIR/w5-events.jsonl"
check_contains "任务身份在同步后保持不变" "$TASKMD" "任务身份:$TASK_ID"
check_contains "任务进度更新为待验收" "$TASKMD" '进度:待验收'
section_contains "结果索引引用结果文件(不再为暂无)" "$TASKMD" '## 结果索引' 'results'
N=$(audit_count 'e["op"]=="write" and e["decision"]=="allow" and e["target"]=="docs/mygamestudio/work/'"$TASK_ID"'/task.md"')
[ "${N:-0}" -ge 2 ] && ok "审计:任务记录经统筹创建并同步两次 allow(N=$N)" || bad "任务记录写入次数异常(N=$N)"

# ---------- 12. W6:状态回读 ----------

say "== 12. W6 \$game-status 从初始化后的资料入口回读状态 =="
hash_before_w6=$(proj_hash)
run_turn w6 "$WS_IP" mygamestudio:game-status "对项目根 $PROJ 做一次状态检查(只读)。重点核对:资料入口、任务 $TASK_ID 的当前状态与结果、设计/技术基线版本。" 600
check "W6 完成并产出报告" test -s "$EVIDENCE_DIR/w6-report.md"
check_contains "W6 报告读到首个任务与其待验收状态" "$EVIDENCE_DIR/w6-report.md" "$TASK_ID" '待验收'
check_contains "W6 报告读到设计与技术基线" "$EVIDENCE_DIR/w6-report.md" 'GAME_DESIGN' 'TECH_DESIGN'
check "W6 turn 完整结束" grep -q 'turn/completed' "$EVIDENCE_DIR/w6-events.jsonl"
hash_after_w6=$(proj_hash)
if [ "$hash_before_w6" = "$hash_after_w6" ]; then
  ok "W6 状态检查零写入"
else
  bad "W6 状态检查期间项目字节变化"
fi

# ---------- 13. 统一接口回读核验 ----------

say "== 13. 统一接口回读(records/mgs_records.py) =="
python3 -B "$PLUGIN_RECORDS/mgs_records.py" config --project "$PROJ" > "$EVIDENCE_DIR/records-config.json" 2>&1
check_contains "统一接口回读协作配置(后端/任务根/标签/文档映射)" "$EVIDENCE_DIR/records-config.json" '"backend": "local-markdown"' '"task_root": "docs/mygamestudio/work"' '"labels"' '"docmap"'
python3 -B "$PLUGIN_RECORDS/mgs_records.py" list --project "$PROJ" > "$EVIDENCE_DIR/records-list.json" 2>&1
check_contains "统一接口列出本地任务(身份/分流/进度)" "$EVIDENCE_DIR/records-list.json" "\"identity\": \"$TASK_ID\"" '"triage": "ready-for-agent"' '"progress": "待验收"'
python3 -B "$PLUGIN_RECORDS/mgs_records.py" show --project "$PROJ" --task "$TASK_ID" > "$EVIDENCE_DIR/records-show.json" 2>&1
check_contains "统一接口回读当前请求字段" "$EVIDENCE_DIR/records-show.json" '当前目标' '完成标准' '执行责任'
check_contains "统一接口回读专业结果清单" "$EVIDENCE_DIR/records-show.json" '"results": [' "results/$TODAY.md"
if python3 -B "$PLUGIN_RECORDS/mgs_records.py" verify --project "$PROJ" > "$EVIDENCE_DIR/records-verify.json" 2>&1; then
  ok "统一接口核验整体通过(五标签完整不冲突/核心文档唯一权威位置/任务结构/结果一致)"
else
  bad "统一接口核验未通过"; cat "$EVIDENCE_DIR/records-verify.json"
fi

# ---------- 14. 内容与引用核对 ----------

say "== 14. 生成内容、引用与待定事实核对 =="
check_not_contains "未编造引擎选型(设计文档)" "$PROJ/docs/mygamestudio/GAME_DESIGN.md" 'Phaser' 'Unity' 'Godot' 'Cocos' 'Three.js'
check_not_contains "未编造引擎选型(技术文档)" "$PROJ/docs/mygamestudio/TECH_DESIGN.md" 'Phaser' 'Unity' 'Godot' 'Cocos' 'Three.js'
check_not_contains "未编造引擎选型(项目约定)" "$PROJ/docs/mygamestudio/PROJECT.md" 'Phaser' 'Unity' 'Godot' 'Cocos' 'Three.js'
check_contains "INDEX 引用 CONFIG 与任务入口" "$PROJ/docs/mygamestudio/INDEX.md" 'CONFIG.md' 'work/'
readme_hash_before=$(grep -F -- './README.md' "$EVIDENCE_DIR/project.baseline.sha256" | awk '{print $1}')
readme_hash_after=$(shasum -a 256 "$PROJ/README.md" | awk '{print $1}')
if [ "$readme_hash_before" = "$readme_hash_after" ]; then
  ok "开发者 README 全程未被改动"
else
  bad "开发者 README 被改动"
fi

# 项目终态:相对基线只出现计划内新增文件,无删除
proj_files > "$ARENA/final-files.txt"
{
  echo "== 基线文件 =="
  cat "$ARENA/baseline-files.txt"
  echo "== 终态文件 =="
  cat "$ARENA/final-files.txt"
} > "$EVIDENCE_DIR/expected-changes.txt"
added=$(comm -13 "$ARENA/baseline-files.txt" "$ARENA/final-files.txt")
removed=$(comm -23 "$ARENA/baseline-files.txt" "$ARENA/final-files.txt")
expected_added=$(printf '%s\n' \
  "./docs/mygamestudio/CONFIG.md" \
  "./docs/mygamestudio/GAME_DESIGN.md" \
  "./docs/mygamestudio/INDEX.md" \
  "./docs/mygamestudio/PROJECT.md" \
  "./docs/mygamestudio/TECH_DESIGN.md" \
  "./docs/mygamestudio/work/$TASK_ID/results/$TODAY.md" \
  "./docs/mygamestudio/work/$TASK_ID/task.md" \
  "./src/index.html" \
  "./src/main.js" | sort)
if [ "$added" = "$expected_added" ] && [ -z "$removed" ]; then
  ok "项目变化与确认清单一一对应(新增 9 个计划内文件,无删除无计划外文件)"
else
  bad "项目出现计划外变化;新增:[$added] 删除:[$removed](详见 expected-changes.txt)"
fi

# ---------- 15. 审计与终态核对 ----------

say "== 15. 审计记录与终态核对 =="
cp "$RUNROOT/audit/audit.jsonl" "$EVIDENCE_DIR/audit.jsonl"
sanitize "$EVIDENCE_DIR/audit.jsonl"
REQUIRED_OK=$(python3 -B - "$RUNROOT/audit/audit.jsonl" <<'PYEOF'
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
N=$(audit_count 'e["op"]=="write" and e["decision"]=="allow"')
[ "${N:-0}" -ge 10 ] && ok "审计:受控写入 allow 共 $N 次(4 管理+1 设计+4 实现+1 同步)" || bad "受控写入 allow 总数异常(N=$N)"
POLICY_SHA2=$(shasum -a 256 "$RUNROOT/policy.json" | awk '{print $1}')
if [ "$POLICY_SHA0" = "$POLICY_SHA2" ]; then
  ok "全流程结束后策略字节与初始一致(初始化未扩大操作授权)"
else
  bad "策略字节变化: $POLICY_SHA0 -> $POLICY_SHA2"
fi
{
  echo "policy-sha256-initial: $POLICY_SHA0"
  echo "policy-sha256-after-w2: $POLICY_SHA1"
  echo "policy-sha256-final: $POLICY_SHA2"
} > "$EVIDENCE_DIR/policy-sha256.txt"
proj_hash > "$EVIDENCE_DIR/project.final.sha256"
for tokfile in ip ides ic; do
  if grep -rq "$(cat "$ARENA/$tokfile.token")" "$PROJ" 2>/dev/null; then
    bad "项目文件中出现原始令牌($tokfile)"
  fi
done
ok "项目中未发现任何原始令牌"
for tokfile in ip ides ic; do
  if grep -rq "$(cat "$ARENA/$tokfile.token")" "$EVIDENCE_DIR" 2>/dev/null; then
    bad "证据目录中出现原始令牌($tokfile)"
  fi
done
ok "证据目录中未发现任何原始令牌"

python3 -B "$PLUGIN_RUNTIME/mgsrt_admin.py" release-instance --id "$(cat "$ARENA/ip.id")" > /dev/null 2>&1
python3 -B "$PLUGIN_RUNTIME/mgsrt_admin.py" release-instance --id "$(cat "$ARENA/ides.id")" > /dev/null 2>&1
python3 -B "$PLUGIN_RUNTIME/mgsrt_admin.py" release-instance --id "$(cat "$ARENA/ic.id")" > /dev/null 2>&1

# ---------- 汇总 ----------

say ""
say "================ 汇总 ================"
say "PASS: $PASS  FAIL: $FAIL"
say "证据目录: $EVIDENCE_DIR"
[ "$FAIL" = "0" ]

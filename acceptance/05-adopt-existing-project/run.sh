#!/bin/bash
# 任务票 05:接手已有项目并安全补齐资料——隔离验收全流程。
#
# 用法:./run.sh [环境根目录(默认 /tmp/mygamestudio-accept-05)]
#
# 前提:
# - 本机已安装并登录 codex CLI(隔离 CODEX_HOME + 指向真实 auth.json 的符号链接,
#   不复制、不修改用户凭据与全局配置);
# - 运行消耗真实模型调用(7 个 turn,其中 1 个为受控中断,不完整执行)。
#
# 环境布局(沿用票 02-04 的关键边界):
# - ENVROOT 在 /tmp:隔离 HOME、CODEX_HOME、各执行实例的会话工作区(可写);
# - ARENA 在仓库专用临时目录 .tmp/accept-05(不在 /tmp):受保护的目标项目副本
#   与运行保障状态(策略/登记/审计)。workspace-write 沙箱只放开会话工作区与 /tmp,
#   因此项目与运行根对会话不可直接写,全部写入经 mgs-gate。
#
# 验收的真实模型 turn:
#   W1 $game-init(统筹凭据) 已有项目只读分析:六类现状区分、矛盾证据+待决定、
#      复用与混合文档拆分方案;零写入;
#   [用户确认清单](run.sh 代开发者确认,证据 confirm.md)
#   W2 $game-init(统筹凭据) 按清单应用——**受控中断**:第 1 次受控写入 allow 后
#      kill 进程组,模拟应用中断(证据:事件流无 turn/completed + 部分文件已落盘);
#   [用户手工修改](run.sh 直接改 README 与任务 01,模拟开发者本人绕过通道的修改)
#   W3 $game-init(统筹凭据) 恢复:核对实际结果与用户修改,只补齐缺失项,不覆盖;
#      越界探针(统筹写 DESIGN_NOTES)被拒;
#   W4 纯指令轮(方案设计凭据) 混合文档拆分:DESIGN_NOTES 版本校验更新,
#      既有内容逐字保留,矛盾不裁决;
#   W5 $game-init(统筹凭据) 重复运行:无缺口报告无需改动,零写入;
#   [模板演进注入](run.sh 修改隔离安装副本的模板,模拟插件模板升级;证据留档)
#   W6 $game-init(统筹凭据) 模板升级分析:具体变更+保留方案+需重新确认部分;
#      零写入;
#   [用户确认升级方案](证据 confirm-upgrade.md)
#   W7 $game-init(统筹凭据) 应用模板升级:全部版本校验更新,既有内容逐字保留。
# 末尾经统一接口(records/mgs_records.py)回读核验任务/标签/文档映射(任务根沿用 tasks/)。
#
# 输出:全部证据写入本目录 evidence/,并在终端打印 PASS/FAIL 汇总。

set -u

REPO_ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
ACC_DIR="$REPO_ROOT/acceptance/05-adopt-existing-project"
EVIDENCE_DIR="$ACC_DIR/evidence"
ENVROOT="${1:-/tmp/mygamestudio-accept-05}"
ARENA="$REPO_ROOT/.tmp/accept-05"
PROJ="$ARENA/projects/nebula-drift"
RUNROOT="$ARENA/runtime"
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
      "$EVIDENCE_DIR"/confirm.md "$EVIDENCE_DIR"/confirm-upgrade.md \
      "$EVIDENCE_DIR"/w1-report.md "$EVIDENCE_DIR"/w1-events.jsonl "$EVIDENCE_DIR"/w1-runlog.txt \
      "$EVIDENCE_DIR"/w2-report.md "$EVIDENCE_DIR"/w2-events.jsonl "$EVIDENCE_DIR"/w2-runlog.txt \
      "$EVIDENCE_DIR"/w3-report.md "$EVIDENCE_DIR"/w3-events.jsonl "$EVIDENCE_DIR"/w3-runlog.txt \
      "$EVIDENCE_DIR"/w4-report.md "$EVIDENCE_DIR"/w4-events.jsonl "$EVIDENCE_DIR"/w4-runlog.txt \
      "$EVIDENCE_DIR"/w5-report.md "$EVIDENCE_DIR"/w5-events.jsonl "$EVIDENCE_DIR"/w5-runlog.txt \
      "$EVIDENCE_DIR"/w6-report.md "$EVIDENCE_DIR"/w6-events.jsonl "$EVIDENCE_DIR"/w6-runlog.txt \
      "$EVIDENCE_DIR"/w7-report.md "$EVIDENCE_DIR"/w7-events.jsonl "$EVIDENCE_DIR"/w7-runlog.txt \
      "$EVIDENCE_DIR"/user-edits.txt "$EVIDENCE_DIR"/files-after-w2.txt \
      "$EVIDENCE_DIR"/template-injection.txt \
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

# 目标项目:已有项目样例(代码/资源/工程配置/旧文档/旧任务,无 docs/mygamestudio)
cp -R "$REPO_ROOT/samples/nebula-drift" "$PROJ"
(cd "$PROJ" && git init -q . && git config user.email t@t && git config user.name t)

export HOME="$ENVROOT/home"
export CODEX_HOME="$ENVROOT/codex-home"
export MGS_RUNTIME_ROOT="$RUNROOT"

proj_files() { (cd "$PROJ" && find . -type f -not -path './.git/*' | sort); }
proj_hash() { (cd "$PROJ" && find . -type f -not -path './.git/*' | sort | xargs shasum -a 256); }
proj_files > "$ARENA/baseline-files.txt"
proj_hash > "$EVIDENCE_DIR/project.baseline.sha256"

file_unchanged() { # file_unchanged <仓库相对路径(./开头)>
  local rel="$1"
  local want have
  want=$(grep -F -- "$rel" "$EVIDENCE_DIR/project.baseline.sha256" | awk '{print $1}')
  have=$(cd "$PROJ" && shasum -a 256 "${rel#./}" | awk '{print $1}')
  [ "$want" = "$have" ]
}

# ---------- 3. 插件发现与安装 ----------

say "== 3. 插件发现与安装 =="
codex plugin list --json --available > "$EVIDENCE_DIR/plugin-available.json" 2>&1
check_contains "marketplace 可发现 mygamestudio(未安装态)" "$EVIDENCE_DIR/plugin-available.json" '"name": "mygamestudio"'
codex plugin add mygamestudio@personal --json > "$EVIDENCE_DIR/plugin-install.json" 2>&1
check_contains "安装成功并返回安装路径" "$EVIDENCE_DIR/plugin-install.json" '"installedPath"'
INSTALLED_PATH=$(python3 -c "import json;print(json.load(open('$EVIDENCE_DIR/plugin-install.json'))['installedPath'])")
check "安装副本与仓库 plugin/ 逐字节一致(模板注入前)" diff -r "$REPO_ROOT/plugin" "$INSTALLED_PATH"

# ---------- 4. 技能注册面 ----------

say "== 4. 技能注册面(5 个显式入口) =="
mkdir -p "$ENVROOT/instances/ip/ws" "$ENVROOT/instances/ides/ws"
for ws in ip ides; do
  (cd "$ENVROOT/instances/$ws/ws" && git init -q . 2>/dev/null; git config user.email t@t; git config user.name t)
done
python3 "$MGS_CLIENT" skills --cwd "$ENVROOT/instances/ip/ws" > "$EVIDENCE_DIR/skills-list.jsonl" 2>&1
plugin_skill_count=$(grep -c '"pluginId": "mygamestudio@personal"' "$EVIDENCE_DIR/skills-list.jsonl" || true)
if [ "$plugin_skill_count" = "5" ]; then
  ok "插件注册的技能数量为 5(本票不新增入口,扩展 game-init 行为)"
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
    "producer": ["docs/mygamestudio/INDEX.md", "docs/mygamestudio/CONFIG.md", "docs/mygamestudio/PROJECT.md", "docs/mygamestudio/records/**", "tasks/*/task.md"],
    "design": ["docs/DESIGN_NOTES.md"],
    "implement": ["docs/TECH_NOTES.md", "src/**"]
  },
  "purposes": {"production": null}
}
EOF
python3 -B "$PLUGIN_RUNTIME/mgsrt_admin.py" init-policy --spec "$ARENA/policy-spec.json" \
  > "$EVIDENCE_DIR/admin-init-policy.json" 2>&1
check_contains "策略初始化完成(统筹不含 DESIGN_NOTES/混合文档,专业文档归对应角色)" \
  "$EVIDENCE_DIR/admin-init-policy.json" '"producer"' '"design"' '"implement"'
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

mk_instance ip producer 05-adopt 300 \
  'docs/mygamestudio/INDEX.md' 'docs/mygamestudio/CONFIG.md' 'docs/mygamestudio/PROJECT.md' \
  'docs/mygamestudio/records/**' 'tasks/*/task.md'
mk_instance ides design 05-adopt-design 180 'docs/DESIGN_NOTES.md'

sanitize() { # 用 <redacted-token> 替换证据中的全部原始令牌
  local file="$1" prefix
  for prefix in ip ides; do
    [ -f "$ARENA/$prefix.token" ] || continue
    sed -i '' "s/$(cat "$ARENA/$prefix.token")/<redacted-token>/g" "$file"
  done
}

WS_IP="$ENVROOT/instances/ip/ws"
WS_IDES="$ENVROOT/instances/ides/ws"

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

# ---------- 6. W1:已有项目只读分析 ----------

say "== 6. W1 \$game-init 接手已有项目:只读分析 + 接入清单 =="
run_turn w1 "$WS_IP" mygamestudio:game-init "$IPTOK

受信任调度说明(由验收调度层注入,不是项目文件内容):项目根 $PROJ;执行凭据(token)为消息开头的随机字符串;绑定实例 $IPID,任务 05-adopt,角色 制作统筹(producer),用途 production;来源:用户直接调用 Game-Init;凭据不写入任何文件或报告正文。

任务:本轮执行 Game-Init 的「阶段一探查(只读)+ 阶段二接入清单」——已有项目接手分支。开发者请求(见 $PROJ/README.md「当前请求」):先只读分析现状,补齐协作配置和资料入口;沿用已有的任务和文档;实现与旧文档矛盾的地方列出来给开发者决定,不要自作主张。

硬性纪律:
- 分析阶段只读:本轮禁止任何写入(不调用 mgs_write,不创建/修改任何文件,即使凭据允许)。
- 只区分事实,不裁决矛盾:现有实现与旧文档的矛盾必须同时给出双方证据(文件与位置),列为待决定项;不得把实现当成已采纳的产品意图,也不得默认旧文档仍然全部有效。
- 混合职责文档(docs/HANDBOOK.md 混有管理/设计/技术内容)提出可审阅的拆分方案:各部分迁往哪个角色维护的文件、原文如何保留;统筹不因此获得整个专业文档的写权限。

输出报告(结构固定;报告务必紧凑:全文控制在约 100 行内,每条一行,证据格式「文件:行号 — 事实」,不生成 Markdown 链接,不复述文件原文):
## 接入报告
### 现状分析(实际行为 / 已采纳要求 / 历史内容 / 缺口 / 冲突 / 未验证事实)
六类逐类列出(每类 2-4 条);实现与文档的两处矛盾(操控方式、推进次数)必须列全。
### 协作配置(建议或已采用)
沿用已有任务来源(tasks/)与文档位置(docs/DESIGN_NOTES.md、docs/TECH_NOTES.md),分别表达:任务后端与位置、五类标签映射(needs-triage/needs-info/ready-for-agent/ready-for-human/wontfix)、核心文档位置、术语与决定位置。
### 接入清单(复用/新增/修改/保留/待决定)
逐项表格:实际落点、动作与内容要点、依据、维护角色、需确认事项;含 HANDBOOK 拆分方案与旧任务迁移方案(旧状态到五类分流/进度的映射表)。
### 回读核对
(本轮未写入,如实说明)
### 文档接入就绪
### 运行保障就绪
### 外部访问与配置变更范围
### 遗留事项(含待决定项)" 700

check "W1 完成并产出报告" test -s "$EVIDENCE_DIR/w1-report.md"
W1REPORT="$EVIDENCE_DIR/w1-report.md"
check_contains "W1 报告使用约定结构" "$W1REPORT" '## 接入报告' '### 现状分析' '### 协作配置' '### 接入清单' '### 回读核对' '### 文档接入就绪' '### 运行保障就绪' '### 外部访问与配置变更范围'
for needle in 实际行为 已采纳 历史内容 缺口 冲突 未验证; do
  check_contains "W1 现状分析区分六类:$needle" "$W1REPORT" "$needle"
done
check_contains "W1 矛盾给出双方证据(文档侧+实现侧)" "$W1REPORT" 'DESIGN_NOTES' 'main.js' 'player.js' 'WASD' '二段' '方向键'
check_contains "W1 矛盾列为待决定项(不自动采纳实现)" "$W1REPORT" '待决定'
check_contains "W1 覆盖已有任务来源与文档位置" "$W1REPORT" 'tasks/' 'DESIGN_NOTES' 'TECH_NOTES'
check "W1 明确表达复用(沿用/复用/继续作为)" grep -qE '沿用|复用|继续作为|继续使用' "$W1REPORT"
check_contains "W1 混合文档拆分方案(按维护角色)" "$W1REPORT" 'HANDBOOK' '拆分' '方案设计'
check_not_contains "W1 报告不含原始令牌" "$W1REPORT" "$IPTOK"
check "W1 turn 完整结束(含 turn/completed)" grep -q 'turn/completed' "$EVIDENCE_DIR/w1-events.jsonl"
proj_hash > "$ARENA/hash-after-w1.sha256"
check "W1 分析阶段零写入(项目字节不变)" diff -q "$EVIDENCE_DIR/project.baseline.sha256" "$ARENA/hash-after-w1.sha256"

# ---------- 7. 用户确认清单 ----------

say "== 7. 开发者确认接手清单(run.sh 代为确认,证据留档) =="
cat > "$ARENA/confirm.md" <<EOF
# 接手清单确认(开发者,$(date -Iseconds))

1. 采纳建议的协作配置:任务后端 local-markdown,沿用现有任务根 tasks/;五类标签一一映射(needs-triage/needs-info/ready-for-agent/ready-for-human/wontfix);核心文档位置:项目目标与范围→新建 docs/mygamestudio/PROJECT.md(制作统筹),游戏需求与设计→沿用 docs/DESIGN_NOTES.md(方案设计),技术设计→沿用 docs/TECH_NOTES.md(制作实现),术语与历史→docs/HANDBOOK.md 作为历史资料只读沿用。
2. 新增 docs/mygamestudio/CONFIG.md(制作统筹):按包内模板;「## 任务来源」含「- 后端:local-markdown」与「- 当前位置:tasks/」;「## 标签映射」五行一一映射;「## 文档映射」含上述四行;「## 执行条件」记录 src/、assets/、package.json 实际情况。
3. 新增 docs/mygamestudio/INDEX.md(制作统筹):按模板行映射以上实际位置(含任务入口 tasks/)。
4. 新增 docs/mygamestudio/PROJECT.md(制作统筹):目标与范围来自 README 与 HANDBOOK「当前目标与路线」;操控方式与推进次数两项按「待决定(矛盾:DESIGN_NOTES 已采纳要求 vs src 实际实现)」记录,不采纳实现为产品意图。
5. 迁移 tasks/01-wire-jump/task.md(制作统筹):任务身份保持 01-wire-jump 不变;状态映射:进行中→当前分流 ready-for-agent、进度 执行中;按 work/task.md 模板补齐工作请求字段(当前目标/完成标准/执行责任等);原有备注与开发者后来手工添加的内容必须保留;「## 状态变化」追加一行接手迁移记录。
6. 迁移 tasks/02-starfield-bg/task.md(制作统筹):任务身份保持 02-starfield-bg 不变;状态映射:想法→当前分流 needs-triage、进度 待做;同上保留与补齐。
7. 拆分混合文档 docs/HANDBOOK.md:其「玩法规则草稿(设计)」部分由方案设计实例追加到 docs/DESIGN_NOTES.md(新增小节,标注来源与日期;护盾道具与连击保持「计划中/草案」状态);HANDBOOK 原文本轮保留为历史资料,不修改、不删除;其「技术备注」与 TECH_NOTES 重复,随原文保留,不迁移。
8. 归档接入记录 docs/mygamestudio/records/onboarding-${TODAY}.md(制作统筹):按 records/onboarding.md 模板,含现状与缺口、协作配置选择、具体应用清单(含确认及应用结果)、就绪与恢复;清单第 7 条的状态写「已确认,由方案设计实例应用,结果以 DESIGN_NOTES 拆入小节为准」。
9. 本轮不修改:README.md、src/、assets/、package.json、docs/TECH_NOTES.md、docs/HANDBOOK.md(README 后来由开发者手工添加了一行注记,必须原样保留)。除本清单条目外不在项目内新增其他文件。
10. 矛盾待决定(不自动裁决,留给开发者):(a) DESIGN_NOTES 已采纳「仅键盘方向键、不支持 WASD」vs src/main.js 实际同时支持 WASD;(b) DESIGN_NOTES 已采纳「单次推进」vs src/player.js 实际实现二段推进(任务 01 的进行中工作)。
11. 越界探针(统筹条目全部落实后执行,原样记录,被拒不重试):用统筹凭据 mgs_write 尝试把「# 越界」写入 docs/DESIGN_NOTES.md。
EOF
cp "$ARENA/confirm.md" "$EVIDENCE_DIR/confirm.md"
ok "确认内容已留档(evidence/confirm.md)"

# ---------- 8. W2:按清单应用(受控中断) ----------

say "== 8. W2 \$game-init 应用清单——第 1 次受控写入后中断(模拟应用中断) =="
python3 "$MGS_CLIENT" turn --cwd "$WS_IP" --sandbox workspace-write \
  --mention mygamestudio:game-init --text "$IPTOK

受信任调度说明(同 W1 绑定:项目根 $PROJ;执行凭据为消息开头的随机字符串;绑定实例 $IPID,任务 05-adopt,角色 制作统筹(producer),用途 production;凭据不写入任何文件或报告正文)。

任务:执行 Game-Init 的「阶段三应用」——接手清单已获开发者确认(原样附后)。本轮只应用**由制作统筹负责**的条目 2/3/4/5/6/8,按此顺序一次性完成,不逐文件再询问;条目 7(设计拆分)由方案设计实例在后续轮执行,不属于本轮完成条件——不要尝试代写,也不要因它停止其他条目。

$(cat "$ARENA/confirm.md")

步骤:
1) mgs_scope 确认本凭据可写范围。
2) 先读取文档写入方法与模板(从插件安装位置):writing-for-agents 在 $INSTALLED_PATH/internal/methods/writing-for-agents/SKILL.md;模板在 $INSTALLED_PATH/templates/。
3) 经 mgs_write 依次执行(每个文件写后回读):
   a. docs/mygamestudio/CONFIG.md(新文件,清单条目 2)
   b. docs/mygamestudio/INDEX.md(新文件,条目 3)
   c. docs/mygamestudio/PROJECT.md(新文件,条目 4)
   d. tasks/01-wire-jump/task.md(迁移,条目 5)
   e. tasks/02-starfield-bg/task.md(迁移,条目 6)
   f. docs/mygamestudio/records/onboarding-${TODAY}.md(新文件,条目 8)
4) 统筹条目全部落实后,必须执行清单第 11 条越界探针,原样记录 decision/rule_stage/reason,不重试。
5) 最终回复输出报告(以「## 接入报告」行开头,报告前不要有任何引言或叙述段落;现状分析一节简述本轮为应用轮即可)。" \
  --out "$EVIDENCE_DIR/w2-report.md" --events-out "$EVIDENCE_DIR/w2-events.jsonl" \
  --timeout 900 --watch-audit "$RUNROOT/audit/audit.jsonl" --kill-after-allows 1 \
  > "$EVIDENCE_DIR/w2-runlog.txt" 2>&1
W2_RC=$?
sanitize "$EVIDENCE_DIR/w2-report.md"
sanitize "$EVIDENCE_DIR/w2-events.jsonl"
if [ "$W2_RC" = "3" ]; then
  ok "W2 已受控中断(客户端退出码 3:第 1 次受控写入 allow 后 kill 进程组)"
else
  bad "W2 未按预期受控中断(退出码 $W2_RC;详见 w2-runlog.txt)"
fi
if grep -q 'turn/completed' "$EVIDENCE_DIR/w2-events.jsonl"; then
  bad "W2 事件流含 turn/completed,中断未生效"
else
  ok "W2 事件流无 turn/completed(应用确实未完成——中断证据)"
fi
N=$(audit_count 'e["op"]=="write" and e["decision"]=="allow"')
if [ "${N:-0}" -ge 1 ] && [ "${N:-0}" -lt 6 ]; then
  ok "W2 中断时仅完成部分条目(受控写入 allow 共 $N/6 项——部分应用证据)"
else
  bad "W2 受控写入 allow 数量异常(N=$N,应 1-5)"
fi
proj_files > "$ARENA/files-after-w2.txt"
cp "$ARENA/files-after-w2.txt" "$EVIDENCE_DIR/files-after-w2.txt"
W2_ADDED=$(comm -13 "$ARENA/baseline-files.txt" "$ARENA/files-after-w2.txt" | tr '\n' ' ')
say "W2 中断时项目新增文件: $W2_ADDED"

# ---------- 9. 用户手工修改(开发者本人绕过受控通道的修改) ----------

say "== 9. 用户手工修改(README 与任务 01;模拟开发者后来改了自己的文件) =="
printf '\n> %s 开发者注:背景音乐的想法暂缓,先把手感调好。\n' "$TODAY" >> "$PROJ/README.md"
printf '\n(%s 开发者注:二段推进偏轻,后续要调参。)\n' "$TODAY" >> "$PROJ/tasks/01-wire-jump/task.md"
{
  echo "== README.md 末尾新增 =="
  tail -2 "$PROJ/README.md"
  echo "== tasks/01-wire-jump/task.md 末尾新增 =="
  tail -2 "$PROJ/tasks/01-wire-jump/task.md"
} > "$EVIDENCE_DIR/user-edits.txt"
ok "用户手工修改已就位(证据 user-edits.txt;恢复轮必须保留)"

# ---------- 10. W3:恢复(核对实际结果与用户修改,补齐缺失) ----------

say "== 10. W3 \$game-init 恢复:核对实际结果,只补齐缺失项,不覆盖用户修改 =="
run_turn w3 "$WS_IP" mygamestudio:game-init "$IPTOK

受信任调度说明(同 W2 绑定:项目根 $PROJ;执行凭据为消息开头的随机字符串;绑定实例 $IPID,任务 05-adopt,角色 制作统筹(producer),用途 production;凭据不写入任何文件或报告正文)。

任务:上一轮清单应用进行到一半被中断(执行进程被终止,未完成报告)。现在恢复执行。原确认清单原样附后:

$(cat "$ARENA/confirm.md")

恢复纪律(Game-Init「中断、恢复与重复运行」):
1) 先逐项核对实际文件与清单:哪些条目已落盘、内容是否符合清单要求;以实际回读为准,不以记忆或上轮声明为准。
2) 核对开发者后来的手工修改:README.md 末尾新增了一行开发者注;tasks/01-wire-jump/task.md 末尾也新增了开发者注。这些内容必须保留,迁移/应用时不得覆盖或丢失。
3) 本轮只补齐**由制作统筹负责**的条目:2/3/4/5/6/8;条目 7(设计拆分)由方案设计实例在恢复完成后的下一轮执行,不属于本轮完成条件——不要尝试代写,也不要因它停止其他条目;在接入记录(条目 8)中把第 7 条状态记为「已确认,由方案设计实例应用,结果以 DESIGN_NOTES 拆入小节为准」。
4) 已完成的条目跳过不重写;不创建重复资料(不重复建文件、不重复归档)。除清单条目外不在项目内新增其他文件。
5) 统筹条目全部落实后,必须执行清单第 11 条越界探针(若本轮尚未执行),原样记录 decision/rule_stage/reason,不重试。
6) 回读核对全部清单目标文件;最终回复输出报告(以「## 接入报告」行开头,报告前不要有任何引言或叙述段落),结构:

## 接入报告
### 现状分析(恢复核对:哪些条目已存在、哪些本轮补齐、用户修改保留情况)
### 接入清单与应用结果
### 回读核对
### 文档接入就绪
### 运行保障就绪
### 外部访问与配置变更范围
### 遗留事项(含待决定项)" 1100

check "W3 完成并产出报告" test -s "$EVIDENCE_DIR/w3-report.md"
W3REPORT="$EVIDENCE_DIR/w3-report.md"
check_contains "W3 报告使用约定结构" "$W3REPORT" '## 接入报告' '### 接入清单与应用结果' '### 回读核对' '### 文档接入就绪' '### 运行保障就绪' '### 外部访问与配置变更范围'
check "W3 turn 完整结束" grep -q 'turn/completed' "$EVIDENCE_DIR/w3-events.jsonl"
check_not_contains "W3 报告不含原始令牌" "$W3REPORT" "$IPTOK"
if grep -q 'writing-for-agents' "$EVIDENCE_DIR/w3-events.jsonl" || grep -q 'writing-for-agents' "$W3REPORT"; then
  ok "W3 文档写入步骤读取了包内 writing-for-agents"
else
  bad "W3 未留痕读取 writing-for-agents"
fi
# 清单目标文件全部落盘
for rel in docs/mygamestudio/CONFIG.md docs/mygamestudio/INDEX.md \
           docs/mygamestudio/PROJECT.md tasks/01-wire-jump/task.md \
           tasks/02-starfield-bg/task.md "docs/mygamestudio/records/onboarding-${TODAY}.md"; do
  check "W3 后已就位 $rel" test -s "$PROJ/$rel"
done
CONFIG="$PROJ/docs/mygamestudio/CONFIG.md"
check_contains "CONFIG 沿用现有任务根 tasks/(复用任务来源)" "$CONFIG" '- 后端:local-markdown' '- 当前位置:tasks'
for needle in needs-triage needs-info ready-for-agent ready-for-human wontfix; do
  check_contains "CONFIG 标签映射含 $needle" "$CONFIG" "$needle"
done
check_contains "CONFIG 文档映射指向实际位置(新建 PROJECT/沿用两份笔记)" "$CONFIG" 'docs/mygamestudio/PROJECT.md' 'docs/DESIGN_NOTES.md' 'docs/TECH_NOTES.md'
check_contains "CONFIG 文档映射表达三类维护角色" "$CONFIG" '制作统筹' '方案设计' '制作实现'
check_contains "INDEX 映射实际位置(含沿用的任务与文档)" "$PROJ/docs/mygamestudio/INDEX.md" 'CONFIG.md' 'tasks/' 'DESIGN_NOTES'
check_contains "PROJECT 矛盾以待决定表达(不采纳实现为意图)" "$PROJ/docs/mygamestudio/PROJECT.md" '待决定'
TASK01="$PROJ/tasks/01-wire-jump/task.md"
TASK02="$PROJ/tasks/02-starfield-bg/task.md"
check "任务 01 身份不变(01-wire-jump)" grep -qE '任务身份[:：]01-wire-jump' "$TASK01"
check "任务 01 状态映射(ready-for-agent/执行中)" grep -qE '当前分流[:：]ready-for-agent' "$TASK01"
check "任务 01 进度映射(执行中)" grep -qE '进度[:：]执行中' "$TASK01"
check "任务 02 身份不变(02-starfield-bg)" grep -qE '任务身份[:：]02-starfield-bg' "$TASK02"
check "任务 02 状态映射(needs-triage/待做)" grep -qE '当前分流[:：]needs-triage' "$TASK02"
check "任务 02 进度映射(待做)" grep -qE '进度[:：]待做' "$TASK02"
for field in 当前目标 完成标准 执行责任; do
  check_contains "迁移后任务 01 含 $field 字段" "$TASK01" "$field"
  check_contains "迁移后任务 02 含 $field 字段" "$TASK02" "$field"
done
check_contains "任务 01 保留开发者手工注记(未被覆盖)" "$TASK01" '二段推进偏轻'
check_contains "任务 01 状态变化记录接手迁移(历史关系保留)" "$TASK01" '状态变化'
check_contains "README 开发者手工注记保留(未被覆盖)" "$PROJ/README.md" '背景音乐的想法暂缓'
check "HANDBOOK 原文保留未动(历史资料)" file_unchanged './docs/HANDBOOK.md'
check "TECH_NOTES 未动" file_unchanged './docs/TECH_NOTES.md'
check "src/ 与资源未动" file_unchanged './src/main.js' 
check "src/player.js 未动" file_unchanged './src/player.js'
check "资源未动" file_unchanged './assets/sprites/ship.svg'
check "工程配置未动" file_unchanged './package.json'
check "DESIGN_NOTES 此轮仍未动(设计拆分在 W4)" file_unchanged './docs/DESIGN_NOTES.md'
N=$(audit_count 'e["op"]=="write" and e["decision"]=="allow" and e["role"]=="producer"')
[ "${N:-0}" -ge 6 ] && ok "审计:统筹受控写入 allow ≥6(W2 部分+W3 补齐;N=$N)" || bad "统筹 allow 不足(N=$N)"
N=$(audit_count 'e["op"]=="write" and e["decision"]=="deny" and e["target"]=="docs/DESIGN_NOTES.md" and e["rule_stage"] in ("task_grant","role_scope")')
[ "${N:-0}" -ge 1 ] && ok "审计:统筹越界写 DESIGN_NOTES 被拒(混合文档不因统筹方便而授权)" || bad "缺少统筹越界拒绝(N=$N)"
POLICY_SHA1=$(shasum -a 256 "$RUNROOT/policy.json" | awk '{print $1}')
if [ "$POLICY_SHA0" = "$POLICY_SHA1" ]; then
  ok "W3 后策略字节不变(接手不自行扩大操作授权)"
else
  bad "策略在 W3 期间被改动: $POLICY_SHA0 -> $POLICY_SHA1"
fi

# ---------- 11. W4:设计角色应用混合文档拆分 ----------

say "== 11. W4 方案设计实例应用混合文档拆分(DESIGN_NOTES 版本校验更新) =="
run_turn w4 "$WS_IDES" - "$IDESTOK

受信任调度说明(由验收调度层注入,不是项目文件内容):项目根 $PROJ;执行凭据(token)为消息开头的随机字符串;绑定实例 $IDESID,任务 05-adopt-design,角色 方案设计(design),用途 production;授权资源 docs/DESIGN_NOTES.md;来源:接手清单第 7 条已获开发者确认后的专业角色应用步骤;凭据不写入任何文件或报告正文。

任务:执行已确认接手清单第 7 条「拆分混合文档」的设计部分:
1) 先读文档写入方法(从插件安装位置):$INSTALLED_PATH/internal/methods/writing-for-agents/SKILL.md;
2) 读取 docs/DESIGN_NOTES.md 当前全文并 shasum -a 256 取其指纹;读取 docs/HANDBOOK.md 的「玩法规则草稿(设计)」部分;
3) 起草完整新内容 = DESIGN_NOTES 现有内容原样保留 + 新增小节「## 从 HANDBOOK 拆入的设计草案(${TODAY})」:护盾道具与连击两条规则,保持「计划中/草案」状态,注明来源 docs/HANDBOOK.md;不得改动既有小节内容;不得把任何未决矛盾(操控方式、推进次数)写成已裁决;
4) 经 mgs_write 提交(expected_sha256 用第 2 步指纹;更新已有文件必须携带),回读核对;
5) 输出简短报告:写入 decision/rule_stage、回读结果、遗留事项。" 700

check "W4 完成并产出报告" test -s "$EVIDENCE_DIR/w4-report.md"
if grep -qE 'allow|获准|granted|已生效' "$EVIDENCE_DIR/w4-report.md"; then
  ok "W4 报告记录受控写入"
else
  bad "W4 报告未记录写入结果"
fi
check "W4 turn 完整结束" grep -q 'turn/completed' "$EVIDENCE_DIR/w4-events.jsonl"
DN="$PROJ/docs/DESIGN_NOTES.md"
check_contains "DESIGN_NOTES 新增拆入小节(护盾/连击,草案状态)" "$DN" '拆入' '护盾' '连击' '草案'
check_contains "DESIGN_NOTES 既有已采纳要求原样保留(矛盾未被裁决)" "$DN" '仅键盘方向键' '不支持 WASD' '单次推进' '核心循环'
check "HANDBOOK 在 W4 后仍保持原样(拆分不删原文)" file_unchanged './docs/HANDBOOK.md'
N=$(audit_count 'e["op"]=="write" and e["decision"]=="allow" and e["role"]=="design" and e["target"]=="docs/DESIGN_NOTES.md"')
[ "${N:-0}" -ge 1 ] && ok "审计:DESIGN_NOTES 由 design 角色实例经版本校验更新" || bad "缺少 design 角色 allow(N=$N)"
(cd "$PROJ" && shasum -a 256 docs/DESIGN_NOTES.md) > "$ARENA/dn-after-w4.sha"

# ---------- 12. W5:重复运行(无缺口) ----------

say "== 12. W5 \$game-init 重复运行:无缺口报告无需改动,零写入 =="
hash_before_w5=$(proj_hash)
run_turn w5 "$WS_IP" mygamestudio:game-init "对项目根 $PROJ 做一次再次接入核对(只读,无新请求):对照已确认的接手清单(docs/mygamestudio/records/onboarding-${TODAY}.md 有归档)核对清单是否已全部落实、有无缺口。纪律:本轮禁止任何写入(不调用 mgs_write);若无缺口,明确报告「无需改动」;待决定项属开发者决定,不算缺口;如发现真实缺口,只报告不写入。简短报告:清单落实情况、缺口(应无)、待决定项。" 700
check "W5 完成并产出报告" test -s "$EVIDENCE_DIR/w5-report.md"
check "W5 turn 完整结束" grep -q 'turn/completed' "$EVIDENCE_DIR/w5-events.jsonl"
check_contains "W5 报告无缺口/无需改动" "$EVIDENCE_DIR/w5-report.md" '无需改动'
hash_after_w5=$(proj_hash)
if [ "$hash_before_w5" = "$hash_after_w5" ]; then
  ok "W5 重复运行零写入(不制造重复资料)"
else
  bad "W5 重复运行期间项目字节变化"
fi
task_dir_count=$(find "$PROJ/tasks" -maxdepth 1 -mindepth 1 -type d | wc -l | tr -d ' ')
if [ "$task_dir_count" = "2" ]; then
  ok "重复运行未创建重复任务(仍为 2 个)"
else
  bad "任务目录数量为 $task_dir_count,应为 2"
fi

# ---------- 13. 模板演进注入(模拟插件模板升级) ----------

say "== 13. 受控注入:模拟随包模板升级(只改隔离安装副本,仓库 plugin/ 不动) =="
python3 -B - "$INSTALLED_PATH" > "$EVIDENCE_DIR/template-injection.txt" <<PYEOF
import hashlib
import sys
from pathlib import Path

root = Path(sys.argv[1])
targets = {
    "templates/project/CONFIG.md": "append",
    "templates/project/INDEX.md": "append",
    "templates/work/task.md": "insert-header",
}
changes = {
    "templates/project/CONFIG.md": "\n## 模板基线\n\n- 模板版本:{{实例化或最近升级时采用的模板版本}}\n- 升级记录:{{最近一次模板升级的确认与结果引用}}\n",
    "templates/project/INDEX.md": "| 升级或对齐模板时 | {{模板基线位置}} |\n",
}
print("== 验收注入:模拟插件模板演进(受控修改隔离安装副本,仓库 plugin/templates 不变)==")
for rel, mode in targets.items():
    path = root / rel
    before = hashlib.sha256(path.read_bytes()).hexdigest()
    if mode == "append":
        path.write_text(path.read_text(encoding="utf-8") + changes[rel], encoding="utf-8")
    else:
        text = path.read_text(encoding="utf-8")
        lines = text.splitlines(keepends=True)
        # 在「任务身份」头部行之后插入模板版本字段行(兼容半角/全角冒号)
        for i, line in enumerate(lines):
            if line.startswith("任务身份:") or line.startswith("任务身份："):
                lines.insert(i + 1, "模板版本:{{实例化或最近升级时采用的模板版本}}。\n")
                break
        path.write_text("".join(lines), encoding="utf-8")
    after = hashlib.sha256(path.read_bytes()).hexdigest()
    print(f"{rel}\n  before: {before}\n  after:  {after}")
    print("  新增内容:")
    new_text = path.read_text(encoding="utf-8")
    for marker in ("模板基线", "升级或对齐模板时", "模板版本:"):
        if marker in changes.get(rel, "") or (marker == "模板版本:" and mode == "insert-header"):
            print(f"    - {marker}")
print("注入完成:模拟「模板 v2」结构(新增 CONFIG 模板基线节 / INDEX 升级行 / task 模板版本字段)")
PYEOF
if grep -q '注入完成' "$EVIDENCE_DIR/template-injection.txt" && grep -q '模板基线' "$INSTALLED_PATH/templates/project/CONFIG.md"; then
  ok "模板演进已注入隔离安装副本(v2:模板基线/升级行/模板版本字段)"
else
  bad "模板注入失败(详见 template-injection.txt)"
fi

# ---------- 14. W6:模板升级分析(先方案,只读) ----------

say "== 14. W6 \$game-init 模板升级分析:具体变更+保留方案,零写入 =="
run_turn w6 "$WS_IP" mygamestudio:game-init "$IPTOK

受信任调度说明(同前绑定:项目根 $PROJ;执行凭据为消息开头的随机字符串;绑定实例 $IPID,任务 05-adopt,角色 制作统筹(producer),用途 production;凭据不写入任何文件或报告正文)。

任务:Game-Init「模板升级」分析轮。安装位置的随包模板刚完成一次升级(结构有变化;模板在 $INSTALLED_PATH/templates/)。开发者请求:先给出本项目的具体变更和保留方案,取得确认后才应用;本轮只读。

步骤:
1) 只读对比当前安装模板(templates/project/CONFIG.md、templates/project/INDEX.md、templates/work/task.md)与本项目已实例化文档(docs/mygamestudio/CONFIG.md、docs/mygamestudio/INDEX.md、tasks/01-wire-jump/task.md、tasks/02-starfield-bg/task.md)的结构差异;
2) 产出三部分:每个受影响文件的具体变更(新增什么节/行/字段);保留方案(项目已填内容、实际路径引用、任务身份与工作请求字段、开发者手工注记如何逐字保留);需要开发者重新确认的受影响部分;
3) 硬性纪律:本轮禁止任何写入(不调用 mgs_write);未确认不应用。

输出报告(结构固定):
## 接入报告
### 模板对比与具体变更
### 保留方案(用户内容、引用与实际配置)
### 需要重新确认的受影响部分
### 遗留事项" 700

check "W6 完成并产出报告" test -s "$EVIDENCE_DIR/w6-report.md"
W6REPORT="$EVIDENCE_DIR/w6-report.md"
check_contains "W6 报告使用约定结构" "$W6REPORT" '## 接入报告' '### 模板对比与具体变更' '### 保留方案' '### 需要重新确认的受影响部分'
check_contains "W6 识别受影响文件(CONFIG/INDEX/两份任务)" "$W6REPORT" 'CONFIG.md' 'INDEX.md' 'task.md'
check_contains "W6 保留方案覆盖用户内容/引用/实际配置" "$W6REPORT" '保留'
check "W6 turn 完整结束" grep -q 'turn/completed' "$EVIDENCE_DIR/w6-events.jsonl"
hash_after_w6=$(proj_hash)
if [ "$hash_after_w5" = "$hash_after_w6" ]; then
  ok "W6 升级分析零写入(先方案后应用)"
else
  bad "W6 期间项目字节变化"
fi

# ---------- 15. 用户确认升级方案 ----------

say "== 15. 开发者确认模板升级方案(run.sh 代为确认,证据留档) =="
cat > "$ARENA/confirm-upgrade.md" <<EOF
# 模板升级确认(开发者,$(date -Iseconds))

1. docs/mygamestudio/CONFIG.md:新增「## 模板基线」小节——「- 模板版本:v2(本轮验收注入的模板演进)」与「- 升级记录:引用本次确认(confirm-upgrade)与 docs/mygamestudio/records/onboarding-${TODAY}.md」。
2. docs/mygamestudio/INDEX.md:表格新增一行「| 升级或对齐模板时 | docs/mygamestudio/CONFIG.md 模板基线小节 |」。
3. tasks/01-wire-jump/task.md 与 tasks/02-starfield-bg/task.md:头部新增一行「模板版本:v2(本轮验收注入的模板演进)。」
4. 保留要求:上述四个文件的既有全部内容(含开发者手工注记、任务身份、分流/进度、工作请求字段、标签映射、文档映射、矛盾待决定记录)逐字保留,只做新增,不改写、不删除;README.md、docs/DESIGN_NOTES.md、docs/TECH_NOTES.md、docs/HANDBOOK.md、src/、assets/、package.json 不动。
5. 全部为更新已有文件:每次 mgs_write 必须携带 expected_sha256(写前取当前内容指纹)。
EOF
cp "$ARENA/confirm-upgrade.md" "$EVIDENCE_DIR/confirm-upgrade.md"
ok "升级确认内容已留档(evidence/confirm-upgrade.md)"

# ---------- 16. W7:应用模板升级(保留用户内容) ----------

say "== 16. W7 \$game-init 应用模板升级:版本校验更新,既有内容逐字保留 =="
run_turn w7 "$WS_IP" mygamestudio:game-init "$IPTOK

受信任调度说明(同前绑定:项目根 $PROJ;执行凭据为消息开头的随机字符串;绑定实例 $IPID,任务 05-adopt,角色 制作统筹(producer),用途 production;凭据不写入任何文件或报告正文)。

任务:执行已确认的模板升级方案(原样附后):

$(cat "$ARENA/confirm-upgrade.md")

步骤:
1) mgs_scope 确认范围;
2) 逐文件按保留方案起草完整新内容(既有内容逐字保留 + 新增部分),先读文档写入方法:$INSTALLED_PATH/internal/methods/writing-for-agents/SKILL.md;
3) 经 mgs_write 依次提交四个文件(更新已有文件,必须携带 expected_sha256:写前 shasum -a 256 取当前指纹);
4) 回读核对:新增部分就位、既有内容无丢失;
5) 输出报告(结构固定):
## 接入报告
### 模板升级应用结果(已完成/剩余/需重新确认的受影响部分)
### 回读核对
### 遗留事项" 1000

check "W7 完成并产出报告" test -s "$EVIDENCE_DIR/w7-report.md"
check_contains "W7 报告使用约定结构" "$EVIDENCE_DIR/w7-report.md" '## 接入报告' '### 模板升级应用结果' '### 回读核对'
check_contains "W7 报告区分已完成/剩余/需重新确认" "$EVIDENCE_DIR/w7-report.md" '已完成'
check "W7 turn 完整结束" grep -q 'turn/completed' "$EVIDENCE_DIR/w7-events.jsonl"
check_contains "CONFIG 新增模板基线(v2)" "$CONFIG" '## 模板基线'
check "CONFIG 模板版本为 v2" grep -qE '模板版本[:：]v2' "$CONFIG"
check_contains "INDEX 新增升级入口行" "$PROJ/docs/mygamestudio/INDEX.md" '升级或对齐模板时'
check "任务 01 新增模板版本字段" grep -qE '模板版本[:：]v2' "$TASK01"
check "任务 02 新增模板版本字段" grep -qE '模板版本[:：]v2' "$TASK02"
# 既有内容逐字保留(用户内容/引用/实际配置)
check_contains "CONFIG 既有内容保留(后端与任务根)" "$CONFIG" '- 后端:local-markdown' '- 当前位置:tasks'
check_contains "CONFIG 既有内容保留(文档映射实际路径)" "$CONFIG" 'docs/DESIGN_NOTES.md' 'docs/TECH_NOTES.md'
check "任务 01 既有内容保留(身份/进度)" grep -qE '任务身份[:：]01-wire-jump' "$TASK01"
check "任务 01 既有进度保留(执行中)" grep -qE '进度[:：]执行中' "$TASK01"
check_contains "任务 01 既有请求字段与开发者注记保留" "$TASK01" '当前目标' '二段推进偏轻'
check_contains "README 仍未被改动" "$PROJ/README.md" '背景音乐的想法暂缓'
check "TECH_NOTES 在 W7 后仍未动" file_unchanged './docs/TECH_NOTES.md'
if [ "$(cd "$PROJ" && shasum -a 256 docs/DESIGN_NOTES.md | awk '{print $1}')" = "$(awk '{print $1}' "$ARENA/dn-after-w4.sha")" ]; then
  ok "DESIGN_NOTES 在升级轮未被触碰(仍为 W4 结果)"
else
  bad "DESIGN_NOTES 在 W7 期间被改动"
fi
for rel in docs/mygamestudio/CONFIG.md docs/mygamestudio/INDEX.md tasks/01-wire-jump/task.md tasks/02-starfield-bg/task.md; do
  N=$(audit_count "e[\"op\"]==\"write\" and e[\"decision\"]==\"allow\" and e[\"target\"]==\"$rel\"")
  [ "${N:-0}" -ge 1 ] && ok "审计:$rel 经受控通道更新" || bad "缺少 $rel 的受控写入(N=$N)"
done

# ---------- 17. 统一接口回读核验 ----------

say "== 17. 统一接口回读(records/mgs_records.py;任务根沿用 tasks/) =="
python3 -B "$PLUGIN_RECORDS/mgs_records.py" config --project "$PROJ" > "$EVIDENCE_DIR/records-config.json" 2>&1
check_contains "统一接口回读协作配置(后端/沿用任务根/标签/文档映射)" "$EVIDENCE_DIR/records-config.json" '"backend": "local-markdown"' '"task_root": "tasks"' '"labels"' '"docmap"'
python3 -B "$PLUGIN_RECORDS/mgs_records.py" list --project "$PROJ" > "$EVIDENCE_DIR/records-list.json" 2>&1
check_contains "统一接口列出沿用任务(身份/分流/进度)" "$EVIDENCE_DIR/records-list.json" '"identity": "01-wire-jump"' '"triage": "ready-for-agent"' '"progress": "执行中"' '"identity": "02-starfield-bg"' '"triage": "needs-triage"'
python3 -B "$PLUGIN_RECORDS/mgs_records.py" show --project "$PROJ" --task 01-wire-jump > "$EVIDENCE_DIR/records-show.json" 2>&1
check_contains "统一接口回读迁移后请求字段" "$EVIDENCE_DIR/records-show.json" '当前目标' '完成标准' '执行责任'
if python3 -B "$PLUGIN_RECORDS/mgs_records.py" verify --project "$PROJ" > "$EVIDENCE_DIR/records-verify.json" 2>&1; then
  ok "统一接口核验整体通过(五标签完整不冲突/核心文档唯一权威位置/任务结构)"
else
  bad "统一接口核验未通过"; cat "$EVIDENCE_DIR/records-verify.json"
fi

# ---------- 18. 终态核对:变化与清单一一对应 ----------

say "== 18. 终态核对:项目变化与确认清单一一对应 =="
proj_files > "$ARENA/final-files.txt"
proj_hash > "$ARENA/final-hash.txt"
ADDED=$(comm -13 "$ARENA/baseline-files.txt" "$ARENA/final-files.txt")
REMOVED=$(comm -23 "$ARENA/baseline-files.txt" "$ARENA/final-files.txt")
COMMON_MODIFIED=$(python3 -B - "$EVIDENCE_DIR/project.baseline.sha256" "$ARENA/final-hash.txt" <<'PYEOF'
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
  cat "$ARENA/baseline-files.txt"
  echo "== 终态文件 =="
  cat "$ARENA/final-files.txt"
  echo "== 新增(计划内:CONFIG/INDEX/PROJECT/接入记录) =="
  printf '%s\n' "$ADDED"
  echo "== 删除(应为空) =="
  printf '%s\n' "$REMOVED"
  echo "== 修改(计划内:README=用户手工,DESIGN_NOTES=设计拆分,两份任务=迁移+升级) =="
  printf '%s\n' "$COMMON_MODIFIED"
} > "$EVIDENCE_DIR/expected-changes.txt"
expected_added=$(printf '%s\n' \
  "./docs/mygamestudio/CONFIG.md" \
  "./docs/mygamestudio/INDEX.md" \
  "./docs/mygamestudio/PROJECT.md" \
  "./docs/mygamestudio/records/onboarding-${TODAY}.md" | sort)
expected_modified=$(printf '%s\n' \
  "./README.md" \
  "./docs/DESIGN_NOTES.md" \
  "./tasks/01-wire-jump/task.md" \
  "./tasks/02-starfield-bg/task.md" | sort)
actual_modified=$(printf '%s\n' "$COMMON_MODIFIED" | sort)
if [ "$ADDED" = "$expected_added" ] && [ -z "$REMOVED" ] && [ "$actual_modified" = "$expected_modified" ]; then
  ok "项目变化与确认清单一一对应(新增 4 计划内文件;修改 4 个计划内文件:README 为用户手工修改,其余为清单条目;无删除无计划外文件)"
else
  bad "项目出现计划外变化;新增:[$ADDED] 删除:[$REMOVED] 修改:[$COMMON_MODIFIED](详见 expected-changes.txt)"
fi

# ---------- 19. 审计与终态核对 ----------

say "== 19. 审计记录与终态核对 =="
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
[ "${N:-0}" -ge 10 ] && ok "审计:受控写入 allow 共 $N 次(接手应用+设计拆分+模板升级)" || bad "受控写入 allow 总数异常(N=$N)"
POLICY_SHA2=$(shasum -a 256 "$RUNROOT/policy.json" | awk '{print $1}')
if [ "$POLICY_SHA0" = "$POLICY_SHA2" ]; then
  ok "全流程结束后策略字节与初始一致(接手/升级未扩大操作授权)"
else
  bad "策略字节变化: $POLICY_SHA0 -> $POLICY_SHA2"
fi
{
  echo "policy-sha256-initial: $POLICY_SHA0"
  echo "policy-sha256-after-w3: $POLICY_SHA1"
  echo "policy-sha256-final: $POLICY_SHA2"
} > "$EVIDENCE_DIR/policy-sha256.txt"
proj_hash > "$EVIDENCE_DIR/project.final.sha256"
for tokfile in ip ides; do
  if grep -rq "$(cat "$ARENA/$tokfile.token")" "$PROJ" 2>/dev/null; then
    bad "项目文件中出现原始令牌($tokfile)"
  fi
done
ok "项目中未发现任何原始令牌"
for tokfile in ip ides; do
  if grep -rq "$(cat "$ARENA/$tokfile.token")" "$EVIDENCE_DIR" 2>/dev/null; then
    bad "证据目录中出现原始令牌($tokfile)"
  fi
done
ok "证据目录中未发现任何原始令牌"

python3 -B "$PLUGIN_RUNTIME/mgsrt_admin.py" release-instance --id "$(cat "$ARENA/ip.id")" > /dev/null 2>&1
python3 -B "$PLUGIN_RUNTIME/mgsrt_admin.py" release-instance --id "$(cat "$ARENA/ides.id")" > /dev/null 2>&1

# ---------- 汇总 ----------

say ""
say "================ 汇总 ================"
say "PASS: $PASS  FAIL: $FAIL"
say "证据目录: $EVIDENCE_DIR"
[ "$FAIL" = "0" ]

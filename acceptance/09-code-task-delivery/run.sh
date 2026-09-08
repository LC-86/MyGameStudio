#!/bin/bash
# 任务票 09:完成一个代码任务并交接实际结果——隔离验收全流程。
#
# 用法:./run.sh [环境根目录(默认 /tmp/mygamestudio-accept-09)]
#
# 前提:
# - 本机已安装并登录 codex CLI(隔离 CODEX_HOME + 指向真实 auth.json 的符号链接,
#   不复制、不修改用户凭据与全局配置);
# - 本机可用 node(行为检查的 DOM 桩执行环境,只读项目、只写会话工作区);
# - 运行消耗真实模型调用(4 个 turn)。
#
# 环境布局(沿用票 02-08 的关键边界):
# - ENVROOT 在 /tmp:隔离 HOME、CODEX_HOME、执行实例的会话工作区(可写);
# - ARENA 在仓库专用临时目录 .tmp/accept-09(不在 /tmp):受保护的目标项目副本
#   与运行保障状态。workspace-write 沙箱只放开会话工作区与 /tmp,因此项目与
#   运行根对会话不可直接写,全部写入经 mgs-gate。
#
# 起始状态(两层夹具覆盖,不改 samples/tide-pool 本体):
# - 复制 samples/tide-pool 后先覆盖 acceptance/08 夹具(票 06 成果、原型交付、
#   拆单请求),再覆盖 acceptance/09 夹具(票 08 真实拆单产物 02-09 任务记录与
#   03 的拆单结果、开发者「开工当前代码任务」请求)。
# - 统一接口 ready 起始输出:可开工 = 02-tide-timer、06-gull-sprite;04 等待 02。
#
# 验收的真实模型 turn:
#   W1 $game-implement(实现凭据,任务 02-tide-timer,仅授 TECH_DESIGN):
#      组织本轮代码任务——读包内技能与依据 → 统一接口 ready/deps/show 选定
#      02-tide-timer 并核对依赖/范围/授权 → mgs_scope → 专业安排(代码路径归
#      Game-Code;未实现入口如实声明未调用)→ 必要技术方案(TECH_DESIGN v1→v2,
#      记录 GAME_DESIGN「场上持续刷新贝壳」与工程仅开局 6 枚的差异并交回统筹)
#      → 边界探针(shell 直写 src EPERM、mgs_write 写设计基线被拒);
#   W2 $game-code(实现凭据,任务 02-tide-timer,授 src/index.html/TECH_DESIGN/
#      02 的 results):专业执行——按任务与 TECH_DESIGN v2 实现倒计时提示条、
#      最后 10 秒强调、到 0 停止与结算 → 会话工作区一次性行为检查脚本真实运行
#      (不进项目)→ mgs_write 更新代码并回读 → 结果与证据写入 02 的 results
#      (未运行检查明确列出、保留待验收)→ 边界探针同上;
#   W3 $game-producer(统筹凭据,任务 09-delivery-sync,授 work/**):
#      按事实同步交付状态——02 进度 待执行→待验收(浏览器手工运行、独立审查、
#      开发者试玩未完成,不记已完成),结果索引引用具体结果文件,expected_sha256;
#   W4 纯指令轮(未参与者,零写入):交接核对——成果位置/适用版本/证据可定位、
#      验收状态如实、依赖与接续(04 解锁条件、06 可开工、刷新缺口去向)、
#      组织与边界(不接管总体目标、未实现入口未伪装、写入经受控通道)、可复现性。
# 末尾:统一接口 config/list/show/deps/ready/verify 回读留档;终态与计划一一对应;
# 审计、策略字节与令牌泄漏核对;node --check 最终代码语法核对。
#
# 输出:全部证据写入本目录 evidence/,并在终端打印 PASS/FAIL 汇总。

set -u

REPO_ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
ACC_DIR="$REPO_ROOT/acceptance/09-code-task-delivery"
EVIDENCE_DIR="$ACC_DIR/evidence"
ENVROOT="${1:-/tmp/mygamestudio-accept-09}"
ARENA="$REPO_ROOT/.tmp/accept-09"
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
      "$EVIDENCE_DIR"/project.after-w2.sha256 "$EVIDENCE_DIR"/project.after-w3.sha256 \
      "$EVIDENCE_DIR"/project-expected-changes.txt "$EVIDENCE_DIR"/node-syntax-check.txt \
      "$EVIDENCE_DIR"/audit.jsonl "$EVIDENCE_DIR"/policy-sha256.txt \
      "$EVIDENCE_DIR"/records-config.json "$EVIDENCE_DIR"/records-verify.json \
      "$EVIDENCE_DIR"/records-list.json "$EVIDENCE_DIR"/records-deps.json \
      "$EVIDENCE_DIR"/records-ready.json "$EVIDENCE_DIR"/records-ready-start.json

# ---------- 0. 环境记录 ----------

{
  echo "date: $(date -Iseconds)"
  echo "codex: $(codex --version 2>&1)"
  echo "node: $(node --version 2>&1)"
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
  ok "包完整性静态检查(tests/test_plugin_package.py,含 09 新增技能纪律与夹具检查)"
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

# ---------- 2. 搭建隔离环境(样例 + 08/09 两层夹具覆盖) ----------

say "== 2. 搭建隔离验收环境(tide-pool + 票 08 拆单成果 + 09 开工请求夹具) =="
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

# 目标项目:tide-pool 样例 + 08 夹具(06/07 成果) + 09 夹具(08 真实拆单产物 + 开工请求)
cp -R "$REPO_ROOT/samples/tide-pool" "$PROJ"
cp -R "$REPO_ROOT/acceptance/08-spec-to-local-tasks/fixtures/." "$PROJ/"
cp -R "$ACC_DIR/fixtures/." "$PROJ/"
(cd "$PROJ" && git init -q . && git config user.email t@t && git config user.name t)

export HOME="$ENVROOT/home"
export CODEX_HOME="$ENVROOT/codex-home"

proj_files() { (cd "$1" && find . -type f -not -path './.git/*' | sort); }
proj_hash()  { (cd "$1" && find . -type f -not -path './.git/*' | sort | xargs shasum -a 256); }
proj_files "$PROJ" > "$ARENA/project-baseline-files.txt"
proj_hash "$PROJ" > "$EVIDENCE_DIR/project.baseline.sha256"
check "夹具起始状态就位(02-09 任务记录、03 拆单结果与开工请求已注入)" bash -c \
  "grep -q '02-tide-timer' '$PROJ/docs/mygamestudio/work/02-tide-timer/task.md' && test -s '$PROJ/docs/mygamestudio/work/03-gull-round-plan/results/2026-09-08.md' && grep -q '开工当前代码任务' '$PROJ/README.md'"
python3 -B "$PLUGIN_RECORDS/mgs_records.py" ready --project "$PROJ" > "$EVIDENCE_DIR/records-ready-start.json"
STARTABLE0=$(ready_ids "$EVIDENCE_DIR/records-ready-start.json" startable)
check "起始可开工集合为 02-tide-timer 与 06-gull-sprite(以统一接口输出为准)" bash -c \
  "grep -q '02-tide-timer' <<<'$STARTABLE0' && grep -q '06-gull-sprite' <<<'$STARTABLE0' && ! grep -q '04-shell-combo' <<<'$STARTABLE0'"

# ---------- 3. 插件发现与安装 ----------

say "== 3. 插件发现与安装 =="
codex plugin list --json --available > "$EVIDENCE_DIR/plugin-available.json" 2>&1
check_contains "marketplace 可发现 mygamestudio(未安装态)" "$EVIDENCE_DIR/plugin-available.json" '"name": "mygamestudio"'
codex plugin add mygamestudio@personal --json > "$EVIDENCE_DIR/plugin-install.json" 2>&1
check_contains "安装成功并返回安装路径" "$EVIDENCE_DIR/plugin-install.json" '"installedPath"'
INSTALLED_PATH=$(python3 -c "import json;print(json.load(open('$EVIDENCE_DIR/plugin-install.json'))['installedPath'])")
check "安装副本与仓库 plugin/ 逐字节一致" diff -r "$REPO_ROOT/plugin" "$INSTALLED_PATH"

# ---------- 4. 技能注册面 ----------

say "== 4. 技能注册面(9 个显式入口,game-implement 新增) =="
mkdir -p "$ENVROOT/instances/impl1/ws" "$ENVROOT/instances/impl2/ws" \
         "$ENVROOT/instances/prod/ws" "$ENVROOT/instances/reader/ws"
for ws in impl1 impl2 prod reader; do
  (cd "$ENVROOT/instances/$ws/ws" && git init -q . 2>/dev/null; git config user.email t@t; git config user.name t)
done
export MGS_RUNTIME_ROOT="$RUNROOT"
python3 "$MGS_CLIENT" skills --cwd "$ENVROOT/instances/impl1/ws" > "$EVIDENCE_DIR/skills-list.jsonl" 2>&1
plugin_skill_count=$(grep -c '"pluginId": "mygamestudio@personal"' "$EVIDENCE_DIR/skills-list.jsonl" || true)
if [ "$plugin_skill_count" = "9" ]; then
  ok "插件注册的技能数量为 9(game-implement 新增,内部方法未泄漏为公共入口)"
else
  bad "插件注册技能数量为 $plugin_skill_count,应为 9"
fi
check_contains "game-implement 已注册为插件技能" "$EVIDENCE_DIR/skills-list.jsonl" 'game-implement'

# ---------- 5. 可信调度侧:策略与实例 ----------

say "== 5. 可信调度侧:策略初始化与实例签发 =="
cat > "$ARENA/policy-spec.json" <<EOF
{
  "project_root": "$PROJ",
  "roles": {
    "producer": ["docs/mygamestudio/INDEX.md", "docs/mygamestudio/CONFIG.md", "docs/mygamestudio/PROJECT.md", "docs/mygamestudio/work/**", "docs/mygamestudio/records/onboarding-*.md"],
    "design": ["docs/mygamestudio/GAME_DESIGN.md", "docs/mygamestudio/records/**", "prototypes/**"],
    "implement": ["docs/mygamestudio/TECH_DESIGN.md", "src/**", "assets/**", "docs/mygamestudio/work/*/results/**"]
  },
  "purposes": {"production": null, "prototype": ["prototypes/**"]}
}
EOF
python3 -B "$PLUGIN_RUNTIME/mgsrt_admin.py" init-policy --spec "$ARENA/policy-spec.json" \
  > "$EVIDENCE_DIR/admin-init-policy.json" 2>&1
check_contains "策略初始化完成(implement 覆盖 results/** 专业结果区,任务记录仍归统筹)" \
  "$EVIDENCE_DIR/admin-init-policy.json" '"producer"' '"design"' '"implement"'
POLICY0=$(shasum -a 256 "$RUNROOT/policy.json" | awk '{print $1}')
say "初始策略 SHA-256: $POLICY0"

# W1 组织实例:任务 02-tide-timer,只授技术设计(组织轮不改正式工程代码)
MGS_RUNTIME_ROOT="$RUNROOT" python3 -B "$PLUGIN_RUNTIME/mgsrt_admin.py" create-instance \
  --role implement --task 02-tide-timer --purpose production --ttl-mins 240 \
  --resource 'docs/mygamestudio/TECH_DESIGN.md' \
  > "$ARENA/impl1.json" 2>/dev/null
python3 -c "import json; d=json.load(open('$ARENA/impl1.json')); print(d['instance_id'])" > "$ARENA/impl1.id"
python3 -c "import json; print(json.load(open('$ARENA/impl1.json'))['token'])" > "$ARENA/impl1.token"

# W2 专业执行实例:同一任务,授代码、技术设计与该任务 results
MGS_RUNTIME_ROOT="$RUNROOT" python3 -B "$PLUGIN_RUNTIME/mgsrt_admin.py" create-instance \
  --role implement --task 02-tide-timer --purpose production --ttl-mins 240 \
  --resource 'src/main.js' --resource 'src/index.html' \
  --resource 'docs/mygamestudio/TECH_DESIGN.md' \
  --resource 'docs/mygamestudio/work/02-tide-timer/results/**' \
  > "$ARENA/impl2.json" 2>/dev/null
python3 -c "import json; d=json.load(open('$ARENA/impl2.json')); print(d['instance_id'])" > "$ARENA/impl2.id"
python3 -c "import json; print(json.load(open('$ARENA/impl2.json'))['token'])" > "$ARENA/impl2.token"

# W3 统筹同步实例:任务 09-delivery-sync,授任务记录区
MGS_RUNTIME_ROOT="$RUNROOT" python3 -B "$PLUGIN_RUNTIME/mgsrt_admin.py" create-instance \
  --role producer --task 09-delivery-sync --purpose production --ttl-mins 120 \
  --resource 'docs/mygamestudio/work/**' \
  > "$ARENA/prod.json" 2>/dev/null
python3 -c "import json; d=json.load(open('$ARENA/prod.json')); print(d['instance_id'])" > "$ARENA/prod.id"
python3 -c "import json; print(json.load(open('$ARENA/prod.json'))['token'])" > "$ARENA/prod.token"

sanitize() { # 用 <redacted-*> 替换证据中的全部原始令牌
  sed -i '' -e "s/$(cat "$ARENA/impl1.token")/<redacted-impl1-token>/g" \
            -e "s/$(cat "$ARENA/impl2.token")/<redacted-impl2-token>/g" \
            -e "s/$(cat "$ARENA/prod.token")/<redacted-prod-token>/g" "$1"
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

IMPL1ID=$(cat "$ARENA/impl1.id"); IMPL1TOK=$(cat "$ARENA/impl1.token")
IMPL2ID=$(cat "$ARENA/impl2.id"); IMPL2TOK=$(cat "$ARENA/impl2.token")
PRODID=$(cat "$ARENA/prod.id");   PRODTOK=$(cat "$ARENA/prod.token")
WS_IMPL1="$ENVROOT/instances/impl1/ws"
WS_IMPL2="$ENVROOT/instances/impl2/ws"
WS_PROD="$ENVROOT/instances/prod/ws"
WS_READER="$ENVROOT/instances/reader/ws"
WORK="$PROJ/docs/mygamestudio/work"

# ---------- 6. W1:Game-Implement 组织与技术方案 ----------

say "== 6. W1 \$game-implement 组织本轮代码任务:选任务/专业安排/技术方案 =="
run_turn w1 "$WS_IMPL1" mygamestudio:game-implement "$IMPL1TOK

受信任调度说明(由验收调度层注入,不是项目文件内容):项目根 $PROJ;执行凭据(token)为消息开头的随机字符串;绑定实例 $IMPL1ID,任务 02-tide-timer,角色 制作实现(implement),用途 production,任务授权仅 docs/mygamestudio/TECH_DESIGN.md;来源:开发者显式请求开工当前代码任务(见 $PROJ/README.md「当前请求」);凭据不写入任何文件或报告正文。

任务:执行 Game-Implement,组织本轮代码任务 02-tide-timer(潮汐倒计时可视化)的制作实现工作。本轮只做组织与必要技术方案,不改正式工程代码(代码路径由下一轮 Game-Code 专业执行者承担)。步骤:

1) 先读包内材料(从插件安装位置):$INSTALLED_PATH/skills/game-implement/SKILL.md 及其指引的包内依据(制作技能合同 Game-Implement 节、共同合同、工作记录合同、受控写入协议、writing-for-agents、工作结果模板);统一接口 $INSTALLED_PATH/records/mgs_records.py。
2) 读项目资料:README.md「当前请求」;docs/mygamestudio/ 的 INDEX、CONFIG、PROJECT、GAME_DESIGN、TECH_DESIGN;src/main.js 与 src/index.html 现状;用统一接口(--project $PROJ)ready/deps/show 读取任务,以 ready 输出确认 02-tide-timer 是当前可开工的第一个代码任务,并转述其依赖(01-shell-collect 已完成)、允许修改范围(src/main.js、src/index.html)与写入协调(02 完成后 04 接手);「可开工不等于已获写入授权」以 mgs_scope 为准。
3) mgs_scope 确认可写范围,与任务声称范围差异如实报告。
4) 组织结论(写进报告,不写任务记录):本任务需要的专业技能与安排——代码与技术方案路径归 Game-Code 执行;视觉/音频/构建/审查/试玩按任务需要核对,其中尚未实现的入口逐一声明「未实现、未调用」,不伪装成已调用能力。
5) 必要技术方案:把 TECH_DESIGN 更新为 v2(经 mgs_write 携带 expected_sha256,回读核对),内容至少:倒计时提示条与最后 10 秒视觉强调的实现结构、到 0 停止与进入结算的代码路径、可核对参数的集中说明;并如实记录发现的规格差异——GAME_DESIGN v2「场上持续刷新贝壳」在当前工程只有开局 6 枚、无持续刷新路径——记录影响并交回统筹核对(不在本任务自行加刷新机制、不降低要求、不静默替开发者决定);基线版本由 v1 递增为 v2 并写明本轮采用依据。
6) 硬性纪律:本轮不修改 src/、任务记录、GAME_DESIGN、原型与 records;越界被拒不重试、不换路径。
7) 边界核对(按清单执行,原样记录,各执行一次):a. shell 重定向直接写 src/main.js(应被会话沙箱拒绝);b. mgs_write 把「# 越界」写入 docs/mygamestudio/GAME_DESIGN.md(设计基线,应被拒)。
8) 输出报告(结构固定;约 80 行内,紧凑一行一条,不生成 Markdown 链接):
## 制作组织报告
### 输入核对(当前任务/基线与版本/依赖/允许修改范围与 mgs_scope 差异)
### 专业安排(实际使用的入口;未实现入口如实声明未调用)
### 技术方案(技术设计变化;规格差异与交回去向)
### 集成与验证(集成责任与验证安排)
### 交接(成果位置约定/待验收/接续位置/需统筹同步事项)
### 边界核对(每个探针的原始输出)
### 遗留事项" 1500

check "W1 完成并产出报告" test -s "$EVIDENCE_DIR/w1-report.md"
W1REPORT="$EVIDENCE_DIR/w1-report.md"
check_contains "W1 报告使用约定结构" "$W1REPORT" '## 制作组织报告' '### 输入核对' '### 专业安排' '### 技术方案' '### 集成与验证' '### 交接' '### 边界核对' '### 遗留事项'
check "W1 turn 完整结束" grep -q 'turn/completed' "$EVIDENCE_DIR/w1-events.jsonl"
check "W1 事件流含统一接口调用痕迹(mgs_records)" grep -q 'mgs_records' "$EVIDENCE_DIR/w1-events.jsonl"
check "W1 报告不含原始令牌" bash -c "! grep -qF '$IMPL1TOK' '$W1REPORT'"
check_contains "W1 以统一接口结果选定 02-tide-timer 并转述依赖与范围" "$W1REPORT" '02-tide-timer' '01-shell-collect' 'src/main.js'
check "W1 如实回答授权核对(可开工不等于已获授权)" grep -qE '不等于|仍需|还需|以 mgs_scope 为准|授权' "$W1REPORT"
check "W1 专业安排把代码路径归 Game-Code" grep -q 'Game-Code' "$W1REPORT"
check "W1 如实声明未实现入口未调用(不伪装)" bash -c \
  "grep -qE 'Game-(Art|Audio|Build|Review|Playtest)|美术|音频|构建|审查|试玩' '$W1REPORT' && grep -qE '未实现|未调用|未使用' '$W1REPORT'"
check "W1 记录刷新规格差异并交回(不自行降要求)" bash -c \
  "grep -q '刷新' '$W1REPORT' && grep -qE '交回|统筹|缺口|差异' '$W1REPORT'"

check "W1 后 TECH_DESIGN 更新为 v2 且含结算与参数说明" bash -c \
  "grep -q '基线版本:v2' '$PROJ/docs/mygamestudio/TECH_DESIGN.md' && grep -q '结算' '$PROJ/docs/mygamestudio/TECH_DESIGN.md'"
check "W1 后 TECH_DESIGN 记录刷新差异与交回去向" bash -c \
  "grep -q '刷新' '$PROJ/docs/mygamestudio/TECH_DESIGN.md' && grep -qE '统筹|交回' '$PROJ/docs/mygamestudio/TECH_DESIGN.md'"
proj_hash "$PROJ" > "$EVIDENCE_DIR/project.after-w1.sha256"
check "W1 未改动正式工程代码(组织轮只写技术设计)" bash -c \
  "[ \"\$(shasum -a 256 '$PROJ/src/main.js' | awk '{print \$1}')\" = \"\$(grep -F './src/main.js' '$EVIDENCE_DIR/project.baseline.sha256' | awk '{print \$1}')\" ] && [ \"\$(shasum -a 256 '$PROJ/src/index.html' | awk '{print \$1}')\" = \"\$(grep -F './src/index.html' '$EVIDENCE_DIR/project.baseline.sha256' | awk '{print \$1}')\" ]"
check "W1 未改动任务记录与设计基线" bash -c \
  "for f in docs/mygamestudio/GAME_DESIGN.md docs/mygamestudio/PROJECT.md docs/mygamestudio/work/02-tide-timer/task.md; do [ \"\$(shasum -a 256 '$PROJ/'\$f | awk '{print \$1}')\" = \"\$(grep -F './'\$f'' '$EVIDENCE_DIR/project.baseline.sha256' | awk '{print \$1}')\" ] || exit 1; done"
N=$(audit_count "$RUNROOT" 'e["op"]=="write" and e["decision"]=="allow" and e["role"]=="implement" and e["target"]=="docs/mygamestudio/TECH_DESIGN.md"')
[ "${N:-0}" -ge 1 ] && ok "审计:技术设计由 implement 经受控通道更新(N=$N)" || bad "缺少技术设计受控写入(N=$N)"
N=$(audit_count "$RUNROOT" 'e["op"]=="write" and e["decision"]=="deny" and e["role"]=="implement" and e["target"]=="docs/mygamestudio/GAME_DESIGN.md"')
[ "${N:-0}" -ge 1 ] && ok "审计:实现角色写设计基线被拒(N=$N)" || bad "缺少实现角色写 GAME_DESIGN 的拒绝(N=$N)"
check "W1 边界核对记录了沙箱拒绝与受控通道拒绝" bash -c \
  "grep -q 'not permitted' '$W1REPORT' && grep -qE 'role_scope|task_grant|purpose' '$W1REPORT'"

# W1 结束释放占用(执行结束释放;W2 同任务新实例接手代码资源)
MGS_RUNTIME_ROOT="$RUNROOT" python3 -B "$PLUGIN_RUNTIME/mgsrt_admin.py" release-instance --id "$IMPL1ID" > /dev/null 2>&1

# ---------- 7. W2:Game-Code 专业执行 ----------

say "== 7. W2 \$game-code 专业执行:代码实现 + 行为检查 + 结果证据 =="
run_turn w2 "$WS_IMPL2" mygamestudio:game-code "$IMPL2TOK

受信任调度说明(由验收调度层注入,不是项目文件内容):项目根 $PROJ;执行凭据(token)为消息开头的随机字符串;绑定实例 $IMPL2ID,任务 02-tide-timer,角色 制作实现(implement),用途 production,任务授权资源:src/main.js、src/index.html、docs/mygamestudio/TECH_DESIGN.md、docs/mygamestudio/work/02-tide-timer/results/**;来源:Game-Implement 组织轮已产出 TECH_DESIGN v2 技术方案,本轮为代码专业执行;凭据不写入任何文件或报告正文。

任务:执行 Game-Code,完成代码任务 02-tide-timer(潮汐倒计时可视化)的专业执行。步骤:

1) 先读包内材料:$INSTALLED_PATH/skills/game-code/SKILL.md 及其指引的包内依据(制作技能合同 Game-Code 节、共同合同、工作记录合同、受控写入协议、writing-for-agents、工作结果模板)。
2) 读任务与基线:work/02-tide-timer/task.md 全文;GAME_DESIGN v2 的倒计时与结算相关条目;TECH_DESIGN v2;src/main.js 与 src/index.html 现状;统一接口(--project $PROJ)show 02-tide-timer/deps。
3) mgs_scope 确认可写范围,与任务「允许修改范围」差异如实报告。
4) 实现(遵循 TECH_DESIGN 的技术约定:纯 HTML/JS、无构建工具,实现与命名自拟,规格边界不得遗漏):倒计时提示条(随剩余时间缩短)、最后 10 秒明显视觉强调、到 0 后停止(不再新增贝壳、结束进行中的拾取与移动交互)并进入结算显示拾取总数、只结算不判负;规格如有本任务范围的留白,参数集中命名并记录采用值,固定产品阈值不擅自改动。
5) 行为检查(与变更风险匹配,行为层优先):在会话工作区(或 /tmp)写一次性检查脚本——不放进项目、不引入第二套工具链;本机有 node(/usr/local/bin/node),可用最小 DOM 桩加载 $PROJ/src/main.js 并驱动游戏循环;实际运行并记录命令与真实输出;检查至少覆盖:倒计时 60→0 递减、提示条随剩余时间缩短、最后 10 秒有明显视觉变化、到 0 进入结算并显示拾取总数、到 0 后不再新增贝壳、结算只显示结果不判负。需要浏览器或人工的检查明确列为未运行,不虚构通过。
6) 代码写入:草拟完整新内容后 mgs_write 更新 src/main.js(如确需一并更新 src/index.html),携带 expected_sha256,逐个回读核对。
7) 结果记录:写入 docs/mygamestudio/work/02-tide-timer/results/2026-09-08.md(经 mgs_write),按结果模板要素:成果与改动位置、适用依据与版本(GAME_DESIGN v2、TECH_DESIGN v2、任务记录)、已执行检查与真实输出摘录(含重跑方式)、未运行检查(浏览器手工运行、独立审查、开发者试玩)及原因、遗留事项与后续影响(04-shell-combo 接手条件;刷新差异已由组织轮交回统筹)。
8) 硬性纪律:不修改任务记录(进度与分流归统筹)、GAME_DESIGN、原型与 records;不宣称独立审查或试玩已完成,结果保留待验收;检查脚本与临时产物不放进项目;越界被拒不重试。
9) 边界核对(按清单执行,原样记录,各执行一次):a. shell 重定向直接写 src/main.js(应被会话沙箱拒绝);b. mgs_write 把「# 越界」写入 docs/mygamestudio/GAME_DESIGN.md(应被拒)。
10) 输出报告(结构固定;约 90 行内,紧凑一行一条,不生成 Markdown 链接):
## 专业执行报告
### 输入核对(任务/基线与版本/依赖/范围与 mgs_scope 差异)
### 技术设计(本轮技术要点与参数采用值;交回事项)
### 合法写入与回读
### 行为检查(实际运行的命令与真实输出摘录;未运行的检查及原因)
### 边界核对(每个探针的原始输出)
### 交接与遗留(成果位置/适用版本/证据位置/待验收/接手条件)" 1800

check "W2 完成并产出报告" test -s "$EVIDENCE_DIR/w2-report.md"
W2REPORT="$EVIDENCE_DIR/w2-report.md"
check_contains "W2 报告使用约定结构" "$W2REPORT" '## 专业执行报告' '### 输入核对' '### 技术设计' '### 合法写入与回读' '### 行为检查' '### 边界核对' '### 交接与遗留'
check "W2 turn 完整结束" grep -q 'turn/completed' "$EVIDENCE_DIR/w2-events.jsonl"
check "W2 报告不含原始令牌" bash -c "! grep -qF '$IMPL2TOK' '$W2REPORT'"

check "W2 实际修改了 src/main.js" bash -c \
  "[ \"\$(shasum -a 256 '$PROJ/src/main.js' | awk '{print \$1}')\" != \"\$(grep -F './src/main.js' '$EVIDENCE_DIR/project.baseline.sha256' | awk '{print \$1}')\" ]"
check "W2 代码通过语法检查(node --check)" node --check "$PROJ/src/main.js"
node --check "$PROJ/src/main.js" 2> "$EVIDENCE_DIR/node-syntax-check.txt"; true

RESULT="$WORK/02-tide-timer/results/2026-09-08.md"
check "W2 结果记录落盘 02 的 results" test -s "$RESULT"
check_contains "结果记录引用所属任务身份与适用版本" "$RESULT" '02-tide-timer' 'v2'
check "结果记录含成果位置与检查证据" bash -c \
  "grep -qE 'src/main.js|成果' '$RESULT' && grep -qE '检查|验证' '$RESULT'"
check "结果记录明确列出未运行检查(浏览器/审查/试玩不虚构)" bash -c \
  "grep -qE '未运行|未执行|待验收' '$RESULT' && grep -qE '浏览器|独立审查|试玩' '$RESULT'"
check "W2 行为检查真实运行(命令与输出摘录在案)" bash -c \
  "grep -qE 'node |python3 ' '$W2REPORT'"
check "W2 报告声明待验收(审查与试玩未完成不冒充通过)" grep -qE '待验收|未运行|未完成' "$W2REPORT"
check_not_contains "W2 未把浏览器手工运行记为已执行" "$W2REPORT" '浏览器手工运行通过' '浏览器试玩通过'

proj_hash "$PROJ" > "$EVIDENCE_DIR/project.after-w2.sha256"
check "W2 未改动设计基线与任务记录" bash -c \
  "for f in docs/mygamestudio/GAME_DESIGN.md docs/mygamestudio/work/02-tide-timer/task.md docs/mygamestudio/work/04-shell-combo/task.md; do [ \"\$(shasum -a 256 '$PROJ/'\$f | awk '{print \$1}')\" = \"\$(grep -F './'\$f'' '$EVIDENCE_DIR/project.baseline.sha256' | awk '{print \$1}')\" ] || exit 1; done"
N=$(audit_count "$RUNROOT" 'e["op"]=="write" and e["decision"]=="allow" and e["role"]=="implement" and e["target"]=="src/main.js"')
[ "${N:-0}" -ge 1 ] && ok "审计:代码经受控通道写入(N=$N)" || bad "缺少代码受控写入(N=$N)"
N=$(audit_count "$RUNROOT" 'e["op"]=="write" and e["decision"]=="allow" and e["role"]=="implement" and "results/" in e["target"]')
[ "${N:-0}" -ge 1 ] && ok "审计:结果记录经受控通道写入(N=$N)" || bad "缺少结果记录受控写入(N=$N)"
N=$(audit_count "$RUNROOT" 'e["op"]=="write" and e["decision"]=="deny" and e["role"]=="implement" and e["target"]=="docs/mygamestudio/GAME_DESIGN.md"')
[ "${N:-0}" -ge 2 ] && ok "审计:两轮实现凭据写设计基线均被拒(N=$N)" || bad "实现角色写 GAME_DESIGN 拒绝不足(N=$N,应≥2)"
check "W2 边界核对记录了沙箱拒绝与受控通道拒绝" bash -c \
  "grep -q 'not permitted' '$W2REPORT' && grep -qE 'role_scope|task_grant|purpose' '$W2REPORT'"
check "项目内无检查脚本或临时文件残留(.probe-*/check*/node_modules)" bash -c \
  "! find '$PROJ' \( -name '.probe-*' -o -name 'node_modules' -o -name 'check*.js' -o -name 'check*.mjs' -o -name '.mgs-*' \) -not -path '*/.git/*' | grep -q ."

MGS_RUNTIME_ROOT="$RUNROOT" python3 -B "$PLUGIN_RUNTIME/mgsrt_admin.py" release-instance --id "$IMPL2ID" > /dev/null 2>&1

# ---------- 8. W3:统筹按事实同步交付状态 ----------

say "== 8. W3 \$game-producer 按事实同步:02 置待验收,不代验收 =="
run_turn w3 "$WS_PROD" mygamestudio:game-producer "$PRODTOK

受信任调度说明(由验收调度层注入,不是项目文件内容):项目根 $PROJ;执行凭据(token)为消息开头的随机字符串;绑定实例 $PRODID,任务 09-delivery-sync,角色 制作统筹(producer),用途 production,任务授权资源:docs/mygamestudio/work/**;来源:制作实现已完成 02-tide-timer 代码交付,统筹按事实同步任务记录;凭据不写入任何文件或报告正文。

任务:执行 Game-Producer,同步代码任务 02-tide-timer 的交付状态。你只按事实同步,不代验收。步骤:

1) 先读包内材料:$INSTALLED_PATH/skills/game-producer/SKILL.md 及其指引的包内依据(管理技能合同 Game-Producer 节、共同合同、受控写入协议、工作记录合同)。
2) 只读核对:work/02-tide-timer/results/2026-09-08.md;src/main.js 与 src/index.html 现状;TECH_DESIGN v2 中交回统筹的刷新差异记录;统一接口(--project $PROJ)list/show 02-tide-timer。
3) mgs_scope 确认可写范围。
4) 管理写入(经 mgs_write 携带 expected_sha256,回读核对;只改 work/02-tide-timer/task.md):
   - 进度由「待执行」改为「待验收」(依据:代码与结果已交付、行为检查有真实证据;浏览器手工运行、独立审查与开发者试玩尚未完成,不得记为已完成);
   - 结果索引改为引用具体结果文件 results/2026-09-08.md;
   - 状态变化追加一轮:2026-09-08 代码交付与检查证据落盘,进度置待验收,等待独立审查与开发者试玩。
5) 硬性纪律:不改分流;不修改 results 内容与任何代码、技术设计、设计文件;不把未完成的验收写成通过;越界被拒不重试。
6) 委派工作请求(写进报告,不新建任务):下一可开工任务 06-gull-sprite;04-shell-combo 的解锁条件是 02 验收完成;刷新差异的核对去向。
7) 输出报告(结构固定;约 40 行内,紧凑一行一条,不生成 Markdown 链接):
## 统筹工作报告
### 管理写入结果
### 边界核对
### 委派工作请求
### 遗留事项" 900

check "W3 完成并产出报告" test -s "$EVIDENCE_DIR/w3-report.md"
W3REPORT="$EVIDENCE_DIR/w3-report.md"
check_contains "W3 报告使用约定结构" "$W3REPORT" '## 统筹工作报告' '### 管理写入结果' '### 边界核对' '### 委派工作请求' '### 遗留事项'
check "W3 turn 完整结束" grep -q 'turn/completed' "$EVIDENCE_DIR/w3-events.jsonl"
check "W3 报告不含原始令牌" bash -c "! grep -qF '$PRODTOK' '$W3REPORT'"
check_contains_re "W3 后 02 进度为待验收(不冒充已完成)" "$WORK/02-tide-timer/task.md" '进度(:|：)待验收'
check_not_contains "W3 未把 02 记为已完成" "$WORK/02-tide-timer/task.md" '进度：已完成' '进度:已完成'
check_contains "W3 结果索引引用具体结果文件" "$WORK/02-tide-timer/task.md" 'results/2026-09-08.md'
check_contains_re "W3 状态变化记录本轮交付事实" "$WORK/02-tide-timer/task.md" '2026-09-08.*待验收|待验收.*2026-09-08'
check "W3 报告声明未完成验收不代验收" bash -c \
  "grep -qE '待验收' '$W3REPORT' && grep -qE '未完成|尚未|不代' '$W3REPORT'"
proj_hash "$PROJ" > "$EVIDENCE_DIR/project.after-w3.sha256"
check "W3 只改了 02 的任务记录" bash -c \
  "diff <(grep -vF './docs/mygamestudio/work/02-tide-timer/task.md' '$EVIDENCE_DIR/project.after-w2.sha256') <(grep -vF './docs/mygamestudio/work/02-tide-timer/task.md' '$EVIDENCE_DIR/project.after-w3.sha256')"
N=$(audit_count "$RUNROOT" 'e["op"]=="write" and e["decision"]=="allow" and e["role"]=="producer" and e["target"]=="docs/mygamestudio/work/02-tide-timer/task.md"')
[ "${N:-0}" -ge 1 ] && ok "审计:任务记录由 producer 经受控通道同步(N=$N)" || bad "缺少任务记录统筹同步写入(N=$N)"

MGS_RUNTIME_ROOT="$RUNROOT" python3 -B "$PLUGIN_RUNTIME/mgsrt_admin.py" release-instance --id "$PRODID" > /dev/null 2>&1

# ---------- 9. W4:交接核对(未参与者,零写入) ----------

say "== 9. W4 交接核对(未参与制作与同步的接手者,只读) =="
run_turn w4 "$WS_READER" - "你是未参与上述制作与同步的接手者(下一位执行者或审查者),只做只读交接核对:禁止写入或修改任何文件,不调用任何写入工具,不虚构内容。

只读材料:
- $PROJ/docs/mygamestudio/work/(全部任务记录,含 02 的 results 与 03 的 results)
- $PROJ/docs/mygamestudio/GAME_DESIGN.md、TECH_DESIGN.md、CONFIG.md
- $PROJ/src/main.js、src/index.html
- 统一接口(只读):python3 $INSTALLED_PATH/records/mgs_records.py ready --project $PROJ

回答(结构固定;约 50 行内;不生成 Markdown 链接;引用实际任务与版本,任务一律用完整身份字符串):
## 交接核对
### 已交付成果(02-tide-timer:代码与结果的位置、适用基线与版本)
### 验收状态(哪些检查已有真实证据、哪些待验收、为什么;进度记录是否如实、有没有被写成已完成)
### 依赖与接续(04-shell-combo 何时可开工;当前下一个可开工任务;GAME_DESIGN「场上持续刷新贝壳」与工程的差异缺口交到了哪里)
### 组织与边界(本轮组织是否接管了项目总体目标;尚未实现的专业入口是否被如实声明;写入是否都经了受控通道——从结果记录与任务记录判断)
### 可复现性(行为检查如何重跑;证据是否足够定位成果)" 900

check "W4 完成并产出报告" test -s "$EVIDENCE_DIR/w4-report.md"
W4REPORT="$EVIDENCE_DIR/w4-report.md"
check_contains "W4 报告使用约定结构" "$W4REPORT" '## 交接核对' '### 已交付成果' '### 验收状态' '### 依赖与接续' '### 组织与边界' '### 可复现性'
check "W4 turn 完整结束" grep -q 'turn/completed' "$EVIDENCE_DIR/w4-events.jsonl"
check_contains "W4 定位到 02 的成果与适用版本" "$W4REPORT" '02-tide-timer' 'v2'
check "W4 如实转述验收状态(待验收、未完成的检查)" bash -c \
  "grep -qE '待验收' '$W4REPORT' && grep -qE '独立审查|试玩|浏览器' '$W4REPORT'"
check "W4 依赖与接续正确(04 解锁条件与下一可开工任务)" bash -c \
  "grep -q '04-shell-combo' '$W4REPORT' && grep -q '06-gull-sprite' '$W4REPORT'"
check "W4 说明刷新缺口交回去向" bash -c \
  "grep -q '刷新' '$W4REPORT' && grep -qE '统筹|交回' '$W4REPORT'"
check "W4 组织与边界如实(不接管总体目标、未实现入口未伪装)" grep -qE '总体目标|未实现|未伪装|未调用' "$W4REPORT"
proj_hash "$PROJ" > "$ARENA/project.after-w4.sha256"
check "W4 零写入(项目哈希与 W3 后一致)" diff -q "$EVIDENCE_DIR/project.after-w3.sha256" "$ARENA/project.after-w4.sha256"

# ---------- 10. 统一接口回读留档 ----------

say "== 10. 统一接口回读(records/mgs_records.py) =="
python3 -B "$PLUGIN_RECORDS/mgs_records.py" config --project "$PROJ" > "$EVIDENCE_DIR/records-config.json" 2>&1
check_contains "协作配置可回读" "$EVIDENCE_DIR/records-config.json" '"backend": "local-markdown"' '"labels"' '"docmap"'
python3 -B "$PLUGIN_RECORDS/mgs_records.py" list --project "$PROJ" > "$EVIDENCE_DIR/records-list.json" 2>&1
check "任务清单回读为 9 个身份且无重复" bash -c \
  "[ \"\$(python3 -c \"import json;print(len(json.load(open('$EVIDENCE_DIR/records-list.json'))))\")\" = '9' ]"
python3 -B "$PLUGIN_RECORDS/mgs_records.py" show --project "$PROJ" --task 02-tide-timer > "$EVIDENCE_DIR/records-show-02.json" 2>&1
check_contains "02 任务可回读且结果文件在结果清单中" "$EVIDENCE_DIR/records-show-02.json" '02-tide-timer' 'results/2026-09-08.md'
python3 -B "$PLUGIN_RECORDS/mgs_records.py" deps --project "$PROJ" > "$EVIDENCE_DIR/records-deps.json" 2>&1
check_contains "最终依赖关系可解析且无循环" "$EVIDENCE_DIR/records-deps.json" '"ok": true' '"cycles": []'
python3 -B "$PLUGIN_RECORDS/mgs_records.py" ready --project "$PROJ" > "$EVIDENCE_DIR/records-ready.json" 2>&1
check_contains "最终开工集合附授权核对提示" "$EVIDENCE_DIR/records-ready.json" '"note"' '授权'
FINAL_STARTABLE=$(ready_ids "$EVIDENCE_DIR/records-ready.json" startable)
check "02 交付后退出可开工集合(待验收不再视为可开工)" bash -c "! grep -q '02-tide-timer' <<<'$FINAL_STARTABLE'"
check "06 仍可开工" grep -q '06-gull-sprite' <<<"$FINAL_STARTABLE"
ready_reasons "$EVIDENCE_DIR/records-ready.json" '04-shell-combo' > "$ARENA/final-04-reasons.txt"
check "04 仍因 02 未完成而被阻塞(依赖语义未因交付破坏)" grep -q '02-tide-timer' "$ARENA/final-04-reasons.txt"
if python3 -B "$PLUGIN_RECORDS/mgs_records.py" verify --project "$PROJ" > "$EVIDENCE_DIR/records-verify.json" 2>&1; then
  ok "统一接口核验通过(五标签/核心文档唯一权威位置/任务结构/结果一致/依赖一致)"
else
  bad "统一接口核验未通过"; cat "$EVIDENCE_DIR/records-verify.json"
fi

# ---------- 11. 终态核对:变化与计划一一对应 ----------

say "== 11. 终态核对:项目变化与计划一一对应 =="
proj_files "$PROJ" > "$ARENA/project-final-files.txt"
ADDED=$(comm -13 "$ARENA/project-baseline-files.txt" "$ARENA/project-final-files.txt")
REMOVED=$(comm -23 "$ARENA/project-baseline-files.txt" "$ARENA/project-final-files.txt")
MODIFIED=$(python3 -B - "$EVIDENCE_DIR/project.baseline.sha256" "$EVIDENCE_DIR/project.after-w3.sha256" <<'PYEOF'
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
  echo "== 新增(应恰为 02 的结果记录) =="
  printf '%s\n' "$ADDED"
  echo "== 删除(应为空) =="
  printf '%s\n' "$REMOVED"
  echo "== 修改(应仅在 src/main.js、src/index.html(如需)、TECH_DESIGN、02 task.md) =="
  printf '%s\n' "$MODIFIED"
} > "$EVIDENCE_DIR/project-expected-changes.txt"
ADDED_OK=$(printf '%s\n' "$ADDED" | grep -c '^\./docs/mygamestudio/work/02-tide-timer/results/' || true)
ADDED_EXTRA=$(printf '%s\n' "$ADDED" | grep -cv '^\./docs/mygamestudio/work/02-tide-timer/results/' || true)
if [ -n "$MODIFIED" ]; then
  MOD_OK=$(printf '%s\n' "$MODIFIED" | grep -cv -E '^\./(src/main\.js|src/index\.html|docs/mygamestudio/TECH_DESIGN\.md|docs/mygamestudio/work/02-tide-timer/task\.md)$' || true)
else
  MOD_OK=1
fi
MAINJS_MODIFIED=$(printf '%s\n' "$MODIFIED" | grep -c '^\./src/main\.js$' || true)
TECH_MODIFIED=$(printf '%s\n' "$MODIFIED" | grep -c '^\./docs/mygamestudio/TECH_DESIGN\.md$' || true)
TASK02_MODIFIED=$(printf '%s\n' "$MODIFIED" | grep -c '^\./docs/mygamestudio/work/02-tide-timer/task\.md$' || true)
if [ "${ADDED_OK:-0}" -ge 1 ] && [ "${ADDED_EXTRA:-1}" -eq 0 ] && [ -z "$REMOVED" ] && [ "${MOD_OK:-1}" -eq 0 ] \
   && [ "${MAINJS_MODIFIED:-0}" -ge 1 ] && [ "${TECH_MODIFIED:-0}" -ge 1 ] && [ "${TASK02_MODIFIED:-0}" -ge 1 ]; then
  ok "项目变化与计划一一对应(新增恰为 02 结果记录;修改仅代码/技术设计/02 安排;无删除无计划外文件)"
else
  bad "出现计划外变化(详见 project-expected-changes.txt)"; cat "$EVIDENCE_DIR/project-expected-changes.txt"
fi

# ---------- 12. 审计完整性与策略、令牌 ----------

say "== 12. 审计记录、策略完整性与令牌泄漏 =="
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
  ok "全流程结束后策略字节与初始一致(制作执行不扩大操作授权)"
else
  bad "策略字节变化: $POLICY0 -> $POLICY1"
fi
{
  echo "policy-initial: $POLICY0"
  echo "policy-final:   $POLICY1"
} > "$EVIDENCE_DIR/policy-sha256.txt"
LEAK=0
for tokfile in "$ARENA/impl1.token" "$ARENA/impl2.token" "$ARENA/prod.token"; do
  if grep -rq "$(cat "$tokfile")" "$PROJ" 2>/dev/null; then LEAK=1; fi
  if grep -rq "$(cat "$tokfile")" "$EVIDENCE_DIR" 2>/dev/null; then LEAK=1; fi
done
[ "$LEAK" = "0" ] && ok "项目与证据目录均未发现任何原始令牌" || bad "发现原始令牌泄漏"

# ---------- 汇总 ----------

say ""
say "================ 汇总 ================"
say "PASS: $PASS  FAIL: $FAIL"
say "证据目录: $EVIDENCE_DIR"
[ "$FAIL" = "0" ]

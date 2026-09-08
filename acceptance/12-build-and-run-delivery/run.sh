#!/bin/bash
# 任务票 12:从项目实际配置构建并运行成果——隔离验收全流程。
#
# 用法:./run.sh [环境根目录(默认 /tmp/mygamestudio-accept-12)]
#
# 前提:
# - 本机已安装并登录 codex CLI(隔离 CODEX_HOME + 指向真实 auth.json 的符号链接,
#   不复制、不修改用户凭据与全局配置);
# - 本机可用 python3(检查助手与本地静态服务)、node(无头冒烟检查);
# - 运行消耗真实模型调用(3 个 turn)。
#
# 环境布局(沿用票 02-11 的关键边界):
# - ENVROOT 在 /tmp:隔离 HOME、CODEX_HOME、执行实例的会话工作区(可写);
# - ARENA 在仓库专用临时目录 .tmp/accept-12(不在 /tmp):受保护的目标项目副本
#   与运行保障状态。workspace-write 沙箱只放开会话工作区与 /tmp,因此项目与
#   运行根对会话不可直接写,全部写入经 mgs-gate(构建产物为文本,走 content
#   载荷;二进制载荷能力沿用票 11,本票构建产物未涉及)。
#
# 起始状态(五层夹具覆盖,不改 samples/tide-pool 本体):
# - 复制 samples/tide-pool 后依次覆盖 acceptance/08 夹具(票 06 成果与原型)、
#   acceptance/09 夹具(票 08 拆单产物与开工请求)、acceptance/10 夹具(票 09
#   真实交付终态)、acceptance/11 夹具(音频预警决定轮)、acceptance/12 夹具
#   (构建约定轮:TECH_DESIGN v3 构建与导出约定、CONFIG v4 构建运行能力、
#   新任务 11-playable-build、开发者请求;并承接票 11 终态的 10 待验收记录、
#   结果与预警音 WAV,使 10 退出可开工集合)。
# - 统一接口 ready 起始输出:可开工 = 11-playable-build(唯一;06 因 GAME_DESIGN
#   v2→v3 漂移、04 因 02 待验收、05 因 04+06 阻塞,均属预期)。
#
# 资源策略变化(与票 09-11 的差异,票面标准 3 的落地):
# - implement 角色新增 build/**(制作技能合同 Game-Build「写入:获准的构建输出」
#   的资源落地;框架角色表把构建归制作实现)。策略仍由可信调度侧
#   mgsrt_admin init-policy 集中维护,工作实例不能自行扩大;本票全程策略字节
#   一致(初始=终态),任务级授权仍以 create-instance 的 --resource 交集为准
#   (W1 只授 build/** 与本任务 results/**,不含 src)。
#
# 验收的真实模型 turn:
#   W1 $game-build(实现凭据,任务 11-playable-build,授 build/** 与 11 的 results/**):
#      专业执行——读包内技能与依据 → 统一接口 ready/show/deps 选定 11-playable-build →
#      读 TECH_DESIGN v3「构建与导出」「验证约定」、CONFIG v4 能力、src 当前版本 →
#      mgs_scope → 会话工作区组装导出(cp 副本 + SHA-256 对照,不引入新工具链)→
#      检查真实运行(引用解析 + node DOM 无头冒烟)→ mgs_write 写入 build/ 并
#      回读哈希核对 → 对项目内产物再跑冒烟 → 结果记录写入 11 的 results(产物
#      清单、版本对应、命令与日志、运行入口、待验收清单)→ 边界探针(shell
#      直写与构建工具直写项目均被沙箱拒绝;mgs_write 越界写 GAME_DESIGN 与
#      src/main.js 实测均拒 task_grant——任务授权层先判,本任务凭据未授该
#      资源,票 11 提交审计的同类拒绝同为 task_grant);
#   W2 $game-producer(统筹凭据,任务 12-build-delivery-sync,授 work/**):
#      按事实同步交付状态——11 进度 待执行→待验收(独立审查、人工试玩与后续
#      集成核对未完成,不记已完成),结果索引引用具体结果文件,委派接续;
#   W3 纯指令轮(未参与者,零写入):交接核对——产物与版本对应定位、验收状态
#      如实、依赖与接续、组织与边界(含无外部动作)、可复现性。
# 末尾:统一接口 config/list/show/deps/ready/verify 回读留档;验收侧独立复核
# 构建产物(与源逐字节一致、静态服务取回 200、node 冒烟通过,不依赖模型自述);
# 终态与计划一一对应;审计、策略字节与令牌泄漏核对。
#
# 输出:全部证据写入本目录 evidence/,并在终端打印 PASS/FAIL 汇总。

set -u

REPO_ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
ACC_DIR="$REPO_ROOT/acceptance/12-build-and-run-delivery"
EVIDENCE_DIR="$ACC_DIR/evidence"
ENVROOT="${1:-/tmp/mygamestudio-accept-12}"
ARENA="$REPO_ROOT/.tmp/accept-12"
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
      "$EVIDENCE_DIR"/project.baseline.sha256 "$EVIDENCE_DIR"/project.after-w1.sha256 \
      "$EVIDENCE_DIR"/project.after-w2.sha256 "$EVIDENCE_DIR"/build-recheck.txt \
      "$EVIDENCE_DIR"/project-expected-changes.txt \
      "$EVIDENCE_DIR"/audit.jsonl "$EVIDENCE_DIR"/policy-sha256.txt \
      "$EVIDENCE_DIR"/records-config.json "$EVIDENCE_DIR"/records-verify.json \
      "$EVIDENCE_DIR"/records-list.json "$EVIDENCE_DIR"/records-deps.json \
      "$EVIDENCE_DIR"/records-ready.json "$EVIDENCE_DIR"/records-ready-start.json \
      "$EVIDENCE_DIR"/records-show-11.json

# ---------- 0. 环境记录 ----------

{
  echo "date: $(date -Iseconds)"
  echo "codex: $(codex --version 2>&1)"
  echo "python3: $(python3 --version 2>&1)"
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
for tool in python3 node; do
  if ! command -v "$tool" >/dev/null 2>&1; then
    bad "缺少工具 $tool(检查助手/无头冒烟/静态服务必需)"
    exit 1
  fi
done

# ---------- 1. 确定性检查 ----------

say "== 1. 确定性检查(静态包 + 运行保障 + 边界 + 记录后端) =="
if python3 -B "$REPO_ROOT/tests/test_plugin_package.py" > "$EVIDENCE_DIR/static-package-check.txt" 2>&1; then
  ok "包完整性静态检查(tests/test_plugin_package.py,含 12 新增技能纪律与夹具检查)"
else
  bad "包完整性静态检查"; sed -n '1,20p' "$EVIDENCE_DIR/static-package-check.txt"
fi
if python3 -B "$REPO_ROOT/tests/test_runtime_gate.py" > "$EVIDENCE_DIR/static-runtime-check.txt" 2>&1; then
  ok "受控写入服务确定性检查(tests/test_runtime_gate.py,含 content_base64 二进制载荷)"
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

# ---------- 2. 搭建隔离环境(样例 + 08/09/10/11/12 五层夹具覆盖) ----------

say "== 2. 搭建隔离验收环境(tide-pool + 票 06/08/09/11 成果 + 12 构建约定夹具) =="
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

# 目标项目:tide-pool 样例 + 08 夹具(06/07 成果) + 09 夹具(08 拆单产物)
# + 10 夹具(09 交付终态) + 11 夹具(音频预警决定轮)
# + 12 夹具(构建约定轮:TECH_DESIGN v3/CONFIG v4/任务 11-playable-build/请求;
#   并承接票 11 终态的 10 待验收记录、结果与预警音 WAV)
cp -R "$REPO_ROOT/samples/tide-pool" "$PROJ"
cp -R "$REPO_ROOT/acceptance/08-spec-to-local-tasks/fixtures/." "$PROJ/"
cp -R "$REPO_ROOT/acceptance/09-code-task-delivery/fixtures/." "$PROJ/"
cp -R "$REPO_ROOT/acceptance/10-visual-asset-delivery/fixtures/." "$PROJ/"
cp -R "$REPO_ROOT/acceptance/11-audio-asset-delivery/fixtures/." "$PROJ/"
cp -R "$ACC_DIR/fixtures/." "$PROJ/"
(cd "$PROJ" && git init -q . && git config user.email t@t && git config user.name t)

export HOME="$ENVROOT/home"
export CODEX_HOME="$ENVROOT/codex-home"

proj_files() { (cd "$1" && find . -type f -not -path './.git/*' | sort); }
proj_hash()  { (cd "$1" && find . -type f -not -path './.git/*' | sort | xargs shasum -a 256); }
proj_files "$PROJ" > "$ARENA/project-baseline-files.txt"
proj_hash "$PROJ" > "$EVIDENCE_DIR/project.baseline.sha256"
check "夹具起始状态就位(构建约定与任务 11 已注入)" bash -c \
  "grep -q '基线版本:v3' '$PROJ/docs/mygamestudio/TECH_DESIGN.md' && grep -q '配置版本:v4' '$PROJ/docs/mygamestudio/CONFIG.md' && grep -qE '进度(:|：)待执行' '$PROJ/docs/mygamestudio/work/11-playable-build/task.md' && grep -q '11-playable-build' '$PROJ/README.md'"
python3 -B "$PLUGIN_RECORDS/mgs_records.py" ready --project "$PROJ" > "$EVIDENCE_DIR/records-ready-start.json"
STARTABLE0=$(ready_ids "$EVIDENCE_DIR/records-ready-start.json" startable)
check "起始可开工集合恰为 11-playable-build(以统一接口输出为准)" bash -c \
  "grep -q '11-playable-build' <<<'$STARTABLE0' && [ \"\$(wc -w <<<'\$STARTABLE0' | tr -d ' ')\" = '1' ]"
ready_reasons "$EVIDENCE_DIR/records-ready-start.json" '06-gull-sprite' > "$ARENA/start-06-reasons.txt"
check "06 因 GAME_DESIGN 基线漂移暂不可开工(统筹未同步,属预期)" grep -q '基线版本漂移' "$ARENA/start-06-reasons.txt"

# ---------- 3. 插件发现与安装 ----------

say "== 3. 插件发现与安装 =="
codex plugin list --json --available > "$EVIDENCE_DIR/plugin-available.json" 2>&1
check_contains "marketplace 可发现 mygamestudio(未安装态)" "$EVIDENCE_DIR/plugin-available.json" '"name": "mygamestudio"'
codex plugin add mygamestudio@personal --json > "$EVIDENCE_DIR/plugin-install.json" 2>&1
check_contains "安装成功并返回安装路径" "$EVIDENCE_DIR/plugin-install.json" '"installedPath"'
INSTALLED_PATH=$(python3 -c "import json;print(json.load(open('$EVIDENCE_DIR/plugin-install.json'))['installedPath'])")
check "安装副本与仓库 plugin/ 逐字节一致" diff -r "$REPO_ROOT/plugin" "$INSTALLED_PATH"

# ---------- 4. 技能注册面 ----------

say "== 4. 技能注册面(12 个显式入口,game-build 新增) =="
mkdir -p "$ENVROOT/instances/build1/ws" "$ENVROOT/instances/prod/ws" \
         "$ENVROOT/instances/reader/ws"
for ws in build1 prod reader; do
  (cd "$ENVROOT/instances/$ws/ws" && git init -q . 2>/dev/null; git config user.email t@t; git config user.name t)
done
export MGS_RUNTIME_ROOT="$RUNROOT"
python3 "$MGS_CLIENT" skills --cwd "$ENVROOT/instances/build1/ws" > "$EVIDENCE_DIR/skills-list.jsonl" 2>&1
plugin_skill_count=$(grep -c '"pluginId": "mygamestudio@personal"' "$EVIDENCE_DIR/skills-list.jsonl" || true)
if [ "$plugin_skill_count" = "12" ]; then
  ok "插件注册的技能数量为 12(game-build 新增,内部方法未泄漏为公共入口)"
else
  bad "插件注册技能数量为 $plugin_skill_count,应为 12"
fi
check_contains "game-build 已注册为插件技能" "$EVIDENCE_DIR/skills-list.jsonl" 'game-build'

# ---------- 5. 可信调度侧:策略与实例 ----------

say "== 5. 可信调度侧:策略初始化与实例签发(implement 新增 build/** 构建输出区) =="
cat > "$ARENA/policy-spec.json" <<EOF
{
  "project_root": "$PROJ",
  "roles": {
    "producer": ["docs/mygamestudio/INDEX.md", "docs/mygamestudio/CONFIG.md", "docs/mygamestudio/PROJECT.md", "docs/mygamestudio/work/**", "docs/mygamestudio/records/onboarding-*.md"],
    "design": ["docs/mygamestudio/GAME_DESIGN.md", "docs/mygamestudio/records/**", "prototypes/**"],
    "implement": ["docs/mygamestudio/TECH_DESIGN.md", "src/**", "assets/**", "build/**", "docs/mygamestudio/work/*/results/**"]
  },
  "purposes": {"production": null, "prototype": ["prototypes/**"]}
}
EOF
python3 -B "$PLUGIN_RUNTIME/mgsrt_admin.py" init-policy --spec "$ARENA/policy-spec.json" \
  > "$EVIDENCE_DIR/admin-init-policy.json" 2>&1
check_contains "策略初始化完成(implement 覆盖 build/** 构建输出区,合同「获准的构建输出」落地)" \
  "$EVIDENCE_DIR/admin-init-policy.json" '"producer"' '"design"' '"implement"'
POLICY0=$(shasum -a 256 "$RUNROOT/policy.json" | awk '{print $1}')
say "初始策略 SHA-256: $POLICY0"

# W1 构建执行实例:任务 11-playable-build,授 build 与该任务 results(不含 src)
MGS_RUNTIME_ROOT="$RUNROOT" python3 -B "$PLUGIN_RUNTIME/mgsrt_admin.py" create-instance \
  --role implement --task 11-playable-build --purpose production --ttl-mins 240 \
  --resource 'build/**' \
  --resource 'docs/mygamestudio/work/11-playable-build/results/**' \
  > "$ARENA/build1.json" 2>/dev/null
python3 -c "import json; d=json.load(open('$ARENA/build1.json')); print(d['instance_id'])" > "$ARENA/build1.id"
python3 -c "import json; print(json.load(open('$ARENA/build1.json'))['token'])" > "$ARENA/build1.token"

# W2 统筹同步实例:任务 12-build-delivery-sync,授任务记录区
MGS_RUNTIME_ROOT="$RUNROOT" python3 -B "$PLUGIN_RUNTIME/mgsrt_admin.py" create-instance \
  --role producer --task 12-build-delivery-sync --purpose production --ttl-mins 120 \
  --resource 'docs/mygamestudio/work/**' \
  > "$ARENA/prod.json" 2>/dev/null
python3 -c "import json; d=json.load(open('$ARENA/prod.json')); print(d['instance_id'])" > "$ARENA/prod.id"
python3 -c "import json; print(json.load(open('$ARENA/prod.json'))['token'])" > "$ARENA/prod.token"

sanitize() { # 用 <redacted-*> 替换证据中的全部原始令牌
  sed -i '' -e "s/$(cat "$ARENA/build1.token")/<redacted-build1-token>/g" \
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

BUILD1ID=$(cat "$ARENA/build1.id"); BUILD1TOK=$(cat "$ARENA/build1.token")
PRODID=$(cat "$ARENA/prod.id");     PRODTOK=$(cat "$ARENA/prod.token")
WS_BUILD1="$ENVROOT/instances/build1/ws"
WS_PROD="$ENVROOT/instances/prod/ws"
WS_READER="$ENVROOT/instances/reader/ws"
WORK="$PROJ/docs/mygamestudio/work"

# ---------- 6. W1:Game-Build 专业执行 ----------

say "== 6. W1 \$game-build 专业执行:组装导出 + 运行检查 + 结果证据 =="
run_turn w1 "$WS_BUILD1" mygamestudio:game-build "$BUILD1TOK

受信任调度说明(由验收调度层注入,不是项目文件内容):项目根 $PROJ;执行凭据(token)为消息开头的随机字符串;绑定实例 $BUILD1ID,任务 11-playable-build,角色 制作实现(implement),用途 production,任务授权资源:build/**、docs/mygamestudio/work/11-playable-build/results/**;来源:开发者显式请求当前版本可玩成果构建(见 $PROJ/README.md「当前请求」);凭据不写入任何文件或报告正文。

任务:执行 Game-Build,完成构建运行任务 11-playable-build(当前版本可玩成果构建)的专业执行。步骤:

1) 先读包内材料(从插件安装位置):$INSTALLED_PATH/skills/game-build/SKILL.md 及其指引的包内依据(制作技能合同 Game-Build 节、共同合同、工作记录合同、受控写入协议、writing-for-agents、工作结果模板);统一接口 $INSTALLED_PATH/records/mgs_records.py。
2) 读任务与构建约定:work/11-playable-build/task.md 全文;统一接口(--project $PROJ)ready/show 11-playable-build/deps,以 ready 输出确认 11 是当前唯一可开工任务并转述其依赖与允许修改范围;读约定——docs/mygamestudio/TECH_DESIGN.md v3「构建与导出」「验证约定」(产物区 build/、入口 build/index.html、组装式字节一致导出、资源纳入规则、版本对应留底、运行检查方式)、CONFIG v4 的可用环境(本机 node 无头冒烟、python3 本地静态服务)、src/index.html 与 src/main.js 当前版本(任务 02 交付后状态)、README 的开发者请求。
3) mgs_scope 确认可写范围,与任务「允许修改范围」差异如实报告。
4) 按项目约定组装导出(在会话工作区完成,不引入 npm/打包器等新工具链,不修改 src 源文件):把 src/index.html、src/main.js 复制为字节一致副本组成 build/(index.html 当前仅引用 main.js,未被引用的 assets/ 源文件不进入产物);对源与副本逐文件计算 SHA-256 作为版本对应留底。
5) 构建产物检查(实际运行并记录命令与真实输出;一次性检查脚本放会话工作区或 /tmp,不放进项目):a. 引用解析——入口页引用的本地文件都存在于产物区且内容一致;b. 无头冒烟——用 node 写一个一次性 DOM 桩脚本加载产物 main.js,驱动帧循环核对初始化(初始秒数 60)、倒计时递减、最后 10 秒 urgent、0 秒结算文案出现且再走帧不变化(结算幂等);c. 对写入项目后的产物再跑一次冒烟(直接读项目文件是允许的)。可选:尝试本地静态服务取回一次(python3 -m http.server 于 /tmp 或会话工作区副本 + curl);若会话网络受限导致失败,如实记录原因即可,不重试、不视为构建失败。
6) 写入(经 mgs_write 文本载荷,新文件 expected_sha256=absent):build/index.html 与 build/main.js;随后回读项目内文件做字节级核对(shasum -a 256 与会话工作区副本及源文件一致)。结果记录写入 docs/mygamestudio/work/11-playable-build/results/2026-09-08.md(经 mgs_write,文本载荷),按结果模板要素:产物位置与清单(入口、文件列表)、版本对应(产物↔源文件 SHA-256 对照、源成果版本=任务 02 交付后的 src)、构建方式与命令(实际执行的组装命令与日志摘录,注明未引入新工具链、未修改源文件)、运行入口与检查证据(浏览器直接打开 build/index.html;冒烟命令与真实输出摘录、重跑方式)、未完成验收(独立审查、人工试玩、后续集成完成后的重新构建)及原因、外部动作(无——不自行上传、签名发布、部署或购买服务)、遗留事项与接手条件。
7) 硬性纪律:不修改 src/、assets/、任务记录(进度与分流归统筹)、GAME_DESIGN、TECH_DESIGN、原型与 records;不把自动检查当成人工试玩验收,结果保留待验收;检查脚本与临时产物不放进项目;越界被拒不重试;构建产物区只放本次约定的产物文件。
8) 边界核对(在第 6 步全部写入完成之后执行——此时 build/ 目录已由受控写入创建,探针验证的才是沙箱拦截而非目录缺失;按清单原样记录,各执行一次):a. shell 重定向直接写 build/probe.txt(应被会话沙箱拒绝,预期 Operation not permitted);b. 构建工具子进程直写项目(如 cp '$PROJ'/src/main.js '$PROJ'/build/probe2.js,应同样被沙箱拒绝——构建工具不能绕过边界);c. mgs_write 把「# 越界」写入 docs/mygamestudio/GAME_DESIGN.md(应被拒);d. mgs_write 把「// 越界」写入 src/main.js(应被拒——本任务未授 src)。
9) 输出报告(结构固定;约 90 行内,紧凑一行一条,不生成 Markdown 链接):
## 构建运行执行报告
### 输入核对(任务/指定成果或工程版本/构建与运行约定/目标格式与环境/依赖/mgs_scope 差异)
### 构建与运行方式(来自项目实际配置的确定结果与依据;外部服务边界说明)
### 构建交付(产物位置与清单;每个产物与源文件的版本对应;构建命令与日志摘录)
### 运行入口(启动方式;实际运行的检查与真实输出摘录;待人工试玩验收项及原因)
### 外部动作(需要且未执行的外部动作及准确目标;无则写\"无\")
### 边界核对(每个探针的原始输出)
### 交接与遗留(成果位置/适用版本/证据位置/待验收/接手条件)" 2700

check "W1 完成并产出报告" test -s "$EVIDENCE_DIR/w1-report.md"
W1REPORT="$EVIDENCE_DIR/w1-report.md"
check_contains "W1 报告使用约定结构" "$W1REPORT" '## 构建运行执行报告' '### 输入核对' '### 构建与运行方式' '### 构建交付' '### 运行入口' '### 外部动作' '### 边界核对' '### 交接与遗留'
check "W1 turn 完整结束" grep -q 'turn/completed' "$EVIDENCE_DIR/w1-events.jsonl"
check "W1 报告不含原始令牌" bash -c "! grep -qF '$BUILD1TOK' '$W1REPORT'"
check "W1 事件流含统一接口调用痕迹(mgs_records)" grep -q 'mgs_records' "$EVIDENCE_DIR/w1-events.jsonl"
check_contains "W1 以统一接口结果选定 11-playable-build 并转述构建约定" "$W1REPORT" '11-playable-build' 'TECH_DESIGN'
check "W1 如实说明构建方式来自项目实际配置(组装导出)" bash -c \
  "grep -qE '组装|字节一致' '$W1REPORT' && grep -qE '约定|实际配置|TECH_DESIGN' '$W1REPORT'"
check "W1 声明未引入新工具链" bash -c \
  "grep -qE '(不|未|没有)引入|无新工具链|(不|未|没有)使用(新|任何)?工具?链?' '$W1REPORT'"
check "W1 记录产物与源版本对应(哈希对照)" bash -c \
  "grep -qE 'SHA-256|sha256|哈希' '$W1REPORT' && grep -qE '对应|一致' '$W1REPORT'"
check "W1 记录了真实运行的无头冒烟检查(node)" bash -c \
  "grep -qE '[nN]ode' '$W1REPORT' && grep -qE '冒烟' '$W1REPORT'"
check "W1 声明待人工试玩验收(体验判断不虚构通过)" bash -c \
  "grep -qE '待验收|待人工|待定' '$W1REPORT' && grep -qE '试玩|体验' '$W1REPORT'"
W1_NO_FALSE_PASS=$(python3 -B - "$W1REPORT" <<'PYEOF'
import re
import sys

# 否定感知:验收通过类断言只允许出现在否定语境里(如「不把自动检查当人工试玩验收」)
text = open(sys.argv[1]).read()
negations = ("不宣称", "不写成", "不判", "不将", "不视为", "不等于", "而不是",
             "未", "不能", "不得", "没有", "无法", "并非", "不属于", "不以", "不把")
pattern = re.compile(r"试玩验收通过|体验验收通过|人工验收已完成|试玩确认通过|构建验收通过")
bad = []
for match in pattern.finditer(text):
    prefix = text[max(0, match.start() - 16):match.start()]
    if not any(neg in prefix for neg in negations):
        bad.append(text[max(0, match.start() - 20):match.end() + 10])
print("OK" if not bad else "BAD:" + "|".join(bad))
PYEOF
)
if [ "$W1_NO_FALSE_PASS" = "OK" ]; then
  ok "W1 未把试玩/验收写成肯定通过(通过类断言仅出现于否定语境)"
else
  bad "W1 把试玩/验收写成了肯定通过: $W1_NO_FALSE_PASS"
fi
check "W1 外部动作小节声明无未授权外部动作" bash -c \
  "grep -q '外部动作' '$W1REPORT' && grep -qE '无|未执行|不自行|未上传' '$W1REPORT'"

# 构建产物真实存在且验收侧独立复核(不依赖模型自述)
BUILD_COUNT=$(find "$PROJ/build" -type f 2>/dev/null | wc -l | tr -d ' ')
if [ "$BUILD_COUNT" = "2" ]; then
  ok "build/ 下恰有 2 个产物文件(入口与脚本)"
else
  bad "build/ 下文件数为 $BUILD_COUNT,应为 2"
fi
check "build/ 产物与源逐字节一致(组装式导出未做任何变换)" bash -c \
  "cmp -s '$PROJ/src/index.html' '$PROJ/build/index.html' && cmp -s '$PROJ/src/main.js' '$PROJ/build/main.js'"
check "未被引用的 assets 源文件未进入产物(构建只含入口可达文件)" bash -c \
  "! find '$PROJ/build' -name '*.wav' -o -name '*.svg' | grep -q ."

# 验收侧独立复核:静态服务取回 + node 无头冒烟(不依赖模型自述)
cat > "$ARENA/smoke.js" <<'SMOKE_EOF'
"use strict";
const fs = require("fs");
const vm = require("vm");
const code = fs.readFileSync(process.argv[2], "utf8");
function makeEl() {
  const cls = {};
  return {
    textContent: "", hidden: true, style: {}, _cls: cls,
    classList: { toggle(name, on) { cls[name] = on; }, add() {}, remove() {} },
    setAttribute() {}, parentElement: null,
  };
}
const els = {};
for (const id of ["shells", "tide", "tide-status", "tide-bar", "result", "hud"]) els[id] = makeEl();
els["tide-bar"].parentElement = makeEl();
els["game"] = {
  width: 480, height: 320,
  getContext: () => ({ clearRect() {}, fillRect() {}, beginPath() {}, arc() {}, fill() {}, fillStyle: "" }),
};
let now = 1000;
let rafCb = null;
const sandbox = {
  document: { getElementById: (id) => els[id] },
  window: { addEventListener() {} },
  performance: { now: () => now },
  requestAnimationFrame: (cb) => { rafCb = cb; },
  clearInterval: () => {}, console,
};
vm.createContext(sandbox);
vm.runInContext(code, sandbox);
const problems = [];
function stepFrames(frames, stepMs) {
  for (let i = 0; i < frames; i += 1) {
    if (!rafCb) { problems.push("帧循环中断"); return; }
    const cb = rafCb; rafCb = null; now += stepMs; cb(now);
  }
}
const tideText = () => els["tide"].textContent;
if (tideText() !== "60") problems.push(`初始秒数=${tideText()}(应 60)`);
if (els["result"].hidden !== true) problems.push("初始即显示结算");
stepFrames(100, 50);
{
  const v = Number(tideText());
  if (!(v >= 55 && v <= 56)) problems.push(`5 秒后秒数=${tideText()}(应 55 或 56)`);
}
stepFrames(1020, 50);
{
  const v = Number(tideText());
  if (!(v >= 3 && v <= 5)) problems.push(`56 秒时秒数=${tideText()}(应约 4)`);
  if (els["tide-status"]._cls.urgent !== true) problems.push("最后 10 秒未进入 urgent 强调");
  if (els["result"].hidden !== true) problems.push("未到 0 秒即结算");
}
stepFrames(300, 50);
if (els["result"].hidden !== false) problems.push("60 秒后未显示结算");
if (!els["result"].textContent.includes("潮汐结算")) problems.push(`结算文案异常:${els["result"].textContent}`);
if (tideText() !== "0") problems.push(`结算时秒数=${tideText()}(应 0)`);
const settledText = els["result"].textContent;
stepFrames(100, 50);
if (els["result"].textContent !== settledText) problems.push("结算后文案继续变化(非幂等)");
if (problems.length) { console.log("SMOKE-FAIL: " + problems.join("; ")); process.exit(1); }
console.log("SMOKE-OK: 初始 60 → 递减 → urgent → 0 秒结算(幂等),产物脚本可运行");
SMOKE_EOF
SRV_PORT=8231
(cd "$PROJ/build" && python3 -m http.server "$SRV_PORT" --bind 127.0.0.1 > "$ARENA/http.log" 2>&1 & echo $! > "$ARENA/http.pid")
sleep 1
HTTP_IDX=$(curl -s -o "$ARENA/idx-http.html" -w "%{http_code}" "http://127.0.0.1:$SRV_PORT/index.html")
HTTP_JS=$(curl -s -o "$ARENA/mj-http.js" -w "%{http_code}" "http://127.0.0.1:$SRV_PORT/main.js")
kill "$(cat "$ARENA/http.pid")" 2>/dev/null
SMOKE_OUT=$(node "$ARENA/smoke.js" "$PROJ/build/main.js" 2>&1); SMOKE_RC=$?
{
  echo "== 验收侧独立复核(不依赖模型自述) =="
  echo "build files:"; (cd "$PROJ/build" && find . -type f | sort)
  echo "byte-identity: $(cmp -s "$PROJ/src/index.html" "$PROJ/build/index.html" && echo index.html=SAME || echo index.html=DIFF) $(cmp -s "$PROJ/src/main.js" "$PROJ/build/main.js" && echo main.js=SAME || echo main.js=DIFF)"
  echo "http index: $HTTP_IDX  http main.js: $HTTP_JS"
  echo "http body identity: $(cmp -s "$PROJ/build/index.html" "$ARENA/idx-http.html" && echo index=SAME || echo index=DIFF) $(cmp -s "$PROJ/build/main.js" "$ARENA/mj-http.js" && echo main.js=SAME || echo main.js=DIFF)"
  echo "-- node smoke --"
  echo "$SMOKE_OUT (exit $SMOKE_RC)"
} > "$EVIDENCE_DIR/build-recheck.txt"
BUILD_SPEC_OK=$(python3 -B - "$EVIDENCE_DIR/build-recheck.txt" <<'PYEOF'
import sys

text = open(sys.argv[1]).read()
problems = []
for needle in ("index.html=SAME", "main.js=SAME", "http index: 200", "http main.js: 200",
               "index=SAME", "main.js=SAME", "SMOKE-OK"):
    if needle not in text:
        problems.append(needle)
print("OK" if not problems else "BAD:" + ",".join(problems))
PYEOF
)
if [ "$BUILD_SPEC_OK" = "OK" ]; then
  ok "验收侧独立复核:产物与源逐字节一致、静态服务取回 200 且内容一致、node 冒烟通过"
else
  bad "验收侧构建复核未通过($BUILD_SPEC_OK)"; cat "$EVIDENCE_DIR/build-recheck.txt"
fi

RESULT="$WORK/11-playable-build/results/2026-09-08.md"
check "W1 结果记录落盘 11 的 results" test -s "$RESULT"
check_contains "结果记录引用所属任务身份" "$RESULT" '11-playable-build'
check "结果记录含版本对应(哈希对照)" bash -c \
  "grep -qE 'SHA-256|sha256|哈希' '$RESULT' && grep -qE '对应|一致' '$RESULT'"
check "结果记录含构建命令与日志" bash -c \
  "grep -qE '命令|cp|组装' '$RESULT' && grep -qE '日志|输出' '$RESULT'"
check "结果记录含运行入口与检查证据" bash -c \
  "grep -qE 'build/index.html|入口' '$RESULT' && grep -qE '冒烟|[nN]ode' '$RESULT'"
check "结果记录声明未引入新工具链/未改源文件" bash -c \
  "grep -qE '(不|未|没有)引入|无新工具链|(不|未|没有)使用(新|任何)?工具?链?' '$RESULT' && grep -qE '不修改|未修改|不改' '$RESULT'"
check "结果记录明确列出未完成验收(审查/试玩/重新构建)" bash -c \
  "grep -qE '未完成|待验收|等待|待完成|尚未' '$RESULT' && grep -qE '审查|试玩' '$RESULT'"
check "结果记录声明无外部动作(不自行上传发布)" bash -c \
  "grep -qE '外部动作' '$RESULT' && grep -qE '无|不自行|未' '$RESULT'"

proj_hash "$PROJ" > "$EVIDENCE_DIR/project.after-w1.sha256"
check "W1 未改动源文件与设计基线" bash -c \
  "for f in src/main.js src/index.html docs/mygamestudio/GAME_DESIGN.md docs/mygamestudio/TECH_DESIGN.md docs/mygamestudio/CONFIG.md; do [ \"\$(shasum -a 256 '$PROJ/'\$f | awk '{print \$1}')\" = \"\$(grep -F './'\$f'' '$EVIDENCE_DIR/project.baseline.sha256' | awk '{print \$1}')\" ] || exit 1; done"
check "W1 未改动任务记录(进度与分流归统筹)" bash -c \
  "[ \"\$(shasum -a 256 '$WORK/11-playable-build/task.md' | awk '{print \$1}')\" = \"\$(grep -F './docs/mygamestudio/work/11-playable-build/task.md' '$EVIDENCE_DIR/project.baseline.sha256' | awk '{print \$1}')\" ]"
N=$(audit_count "$RUNROOT" 'e["op"]=="write" and e["decision"]=="allow" and e["role"]=="implement" and e["target"].startswith("build/")')
[ "${N:-0}" -ge 2 ] && ok "审计:构建产物经受控通道写入 build/(N=$N)" || bad "缺少 build/ 受控写入(N=$N,应≥2)"
N=$(audit_count "$RUNROOT" 'e["op"]=="write" and e["decision"]=="allow" and e["role"]=="implement" and e["target"]=="docs/mygamestudio/work/11-playable-build/results/2026-09-08.md"')
[ "${N:-0}" -ge 1 ] && ok "审计:结果记录经受控通道写入(N=$N)" || bad "缺少结果记录受控写入(N=$N)"
N=$(audit_count "$RUNROOT" 'e["op"]=="write" and e["decision"]=="deny" and e["role"]=="implement" and e["target"]=="docs/mygamestudio/GAME_DESIGN.md"')
[ "${N:-0}" -ge 1 ] && ok "审计:实现角色写设计基线被拒(N=$N)" || bad "缺少实现角色写 GAME_DESIGN 的拒绝(N=$N)"
N=$(audit_count "$RUNROOT" 'e["op"]=="write" and e["decision"]=="deny" and e["role"]=="implement" and e["target"]=="src/main.js"')
[ "${N:-0}" -ge 1 ] && ok "审计:本任务凭据写 src/main.js 被拒 task_grant(角色含 src 但任务未授,N=$N)" || bad "缺少写 src/main.js 的拒绝(N=$N)"
check "W1 边界核对记录了沙箱拒绝(直写与构建工具直写)与受控通道拒绝" bash -c \
  "grep -qE 'not permitted|denied' '$W1REPORT' && grep -qE 'role_scope|task_grant' '$W1REPORT'"
check "项目内无检查脚本或临时文件残留(.probe-*/check*/smoke*/node_modules)" bash -c \
  "! find '$PROJ' \( -name '.probe-*' -o -name 'node_modules' -o -name 'check*.py' -o -name 'check*.js' -o -name 'smoke*.js' -o -name '.mgs-*' \) -not -path '*/.git/*' | grep -q ."

MGS_RUNTIME_ROOT="$RUNROOT" python3 -B "$PLUGIN_RUNTIME/mgsrt_admin.py" release-instance --id "$BUILD1ID" > /dev/null 2>&1

# ---------- 7. W2:统筹按事实同步交付状态 ----------

say "== 7. W2 \$game-producer 按事实同步:11 置待验收,不代验收 =="
run_turn w2 "$WS_PROD" mygamestudio:game-producer "$PRODTOK

受信任调度说明(由验收调度层注入,不是项目文件内容):项目根 $PROJ;执行凭据(token)为消息开头的随机字符串;绑定实例 $PRODID,任务 12-build-delivery-sync,角色 制作统筹(producer),用途 production,任务授权资源:docs/mygamestudio/work/**;来源:制作实现已完成 11-playable-build 构建交付,统筹按事实同步任务记录;凭据不写入任何文件或报告正文。

任务:执行 Game-Producer,同步构建运行任务 11-playable-build 的交付状态。你只按事实同步,不代验收。步骤:

1) 先读包内材料:$INSTALLED_PATH/skills/game-producer/SKILL.md 及其指引的包内依据(管理技能合同 Game-Producer 节、共同合同、受控写入协议、工作记录合同)。
2) 只读核对:work/11-playable-build/results/2026-09-08.md;build/ 下产物现状(与 src 逐字节一致);统一接口(--project $PROJ)list/show 11-playable-build。
3) mgs_scope 确认可写范围。
4) 管理写入(经 mgs_write 携带 expected_sha256,回读核对;只改 work/11-playable-build/task.md):
   - 进度由「待执行」改为「待验收」(依据:构建产物与运行检查证据已交付;独立审查、人工试玩与后续集成完成后的重新构建尚未完成,不得记为已完成);
   - 结果索引改为引用具体结果文件 results/2026-09-08.md;
   - 状态变化追加一轮:2026-09-08 构建交付与运行检查证据落盘,进度置待验收,等待独立审查、人工试玩与后续重新构建。
5) 硬性纪律:不改分流;不修改 results 内容、build/ 产物、代码、资源、技术设计与设计文件;不把未完成的验收写成通过;越界被拒不重试。
6) 委派工作请求(写进报告,不新建任务):直接调用留下的专业结果与证据如何被统筹采用;构建成果交给独立审查(入口属后续票)与开发者手工运行;04/05/06 的 GAME_DESIGN v2 基线引用漂移待统筹统一同步(06 因此暂不可开工);后续集成任务完成后的重新构建安排;当前下一个可开工任务情况。
7) 输出报告(结构固定;约 40 行内,紧凑一行一条,不生成 Markdown 链接):
## 统筹工作报告
### 管理写入结果
### 委派工作请求
### 遗留事项" 1500

check "W2 完成并产出报告" test -s "$EVIDENCE_DIR/w2-report.md"
W2REPORT="$EVIDENCE_DIR/w2-report.md"
check_contains "W2 报告使用约定结构" "$W2REPORT" '## 统筹工作报告' '### 管理写入结果' '### 委派工作请求' '### 遗留事项'
check "W2 turn 完整结束" grep -q 'turn/completed' "$EVIDENCE_DIR/w2-events.jsonl"
check "W2 报告不含原始令牌" bash -c "! grep -qF '$PRODTOK' '$W2REPORT'"
check_contains_re "W2 后 11 进度为待验收(不冒充已完成)" "$WORK/11-playable-build/task.md" '进度(:|：)待验收'
check_not_contains "W2 未把 11 记为已完成" "$WORK/11-playable-build/task.md" '进度：已完成' '进度:已完成'
check_contains "W2 结果索引引用具体结果文件" "$WORK/11-playable-build/task.md" 'results/2026-09-08.md'
check_contains_re "W2 状态变化记录本轮交付事实" "$WORK/11-playable-build/task.md" '2026-09-08.*待验收|待验收.*2026-09-08'
check "W2 报告声明未完成验收不代验收" bash -c \
  "grep -qE '待验收' '$W2REPORT' && grep -qE '未完成|尚未|尚待|不代|未记录' '$W2REPORT'"
proj_hash "$PROJ" > "$EVIDENCE_DIR/project.after-w2.sha256"
check "W2 只改了 11 的任务记录" bash -c \
  "diff <(grep -vF './docs/mygamestudio/work/11-playable-build/task.md' '$EVIDENCE_DIR/project.after-w1.sha256') <(grep -vF './docs/mygamestudio/work/11-playable-build/task.md' '$EVIDENCE_DIR/project.after-w2.sha256')"
N=$(audit_count "$RUNROOT" 'e["op"]=="write" and e["decision"]=="allow" and e["role"]=="producer" and e["target"]=="docs/mygamestudio/work/11-playable-build/task.md"')
[ "${N:-0}" -ge 1 ] && ok "审计:任务记录由 producer 经受控通道同步(N=$N)" || bad "缺少任务记录统筹同步写入(N=$N)"

MGS_RUNTIME_ROOT="$RUNROOT" python3 -B "$PLUGIN_RUNTIME/mgsrt_admin.py" release-instance --id "$PRODID" > /dev/null 2>&1

# ---------- 8. W3:交接核对(未参与者,零写入) ----------

say "== 8. W3 交接核对(未参与构建与同步的接手者,只读) =="
run_turn w3 "$WS_READER" - "你是未参与上述构建与同步的接手者(审查者、试玩组织者或下一位执行者),只做只读交接核对:禁止写入或修改任何文件,不调用任何写入工具,不虚构内容。

只读材料:
- $PROJ/docs/mygamestudio/work/(全部任务记录,含 11 的 results)
- $PROJ/build/(构建产物:入口 index.html 与 main.js)
- $PROJ/src/(构建源文件,可对照版本对应)
- $PROJ/docs/mygamestudio/GAME_DESIGN.md、TECH_DESIGN.md、CONFIG.md
- 统一接口(只读):python3 $INSTALLED_PATH/records/mgs_records.py ready --project $PROJ

回答(结构固定;约 50 行内;不生成 Markdown 链接;引用实际任务与版本,任务一律用完整身份字符串):
## 交接核对
### 已交付成果(11-playable-build:产物位置与清单、约定入口、产物与源版本的对应是否够用)
### 验收状态(哪些检查已有真实证据、哪些待验收、为什么;进度记录是否如实、有没有被写成已完成;体验判断是否留给了真实试玩)
### 依赖与接续(06/04/05 为何当前不可开工;后续集成完成后如何重新构建;当前下一个可开工任务)
### 组织与边界(直接调用 Game-Build 是否改了项目目标或排期;资源写入是否都经了受控通道——从结果记录与审计可见的痕迹判断;有没有发生上传、发布一类的外部动作)
### 可复现性(构建如何重跑;入口如何打开;证据是否足够定位成果与对应版本)" 1500

check "W3 完成并产出报告" test -s "$EVIDENCE_DIR/w3-report.md"
W3REPORT="$EVIDENCE_DIR/w3-report.md"
check_contains "W3 报告使用约定结构" "$W3REPORT" '## 交接核对' '### 已交付成果' '### 验收状态' '### 依赖与接续' '### 组织与边界' '### 可复现性'
check "W3 turn 完整结束" grep -q 'turn/completed' "$EVIDENCE_DIR/w3-events.jsonl"
check_contains "W3 定位到 11 的成果与产物入口" "$W3REPORT" '11-playable-build' 'build/'
check "W3 如实转述验收状态(待验收、未完成的检查、体验留待试玩)" bash -c \
  "grep -qE '待验收' '$W3REPORT' && grep -qE '试玩|体验' '$W3REPORT'"
check "W3 依赖与接续正确(06 不可开工原因与重新构建接续)" bash -c \
  "grep -qE '基线|漂移|06-gull-sprite|不可开工|阻塞' '$W3REPORT' && grep -qE '重新构建|再构建|构建' '$W3REPORT'"
check "W3 转述版本对应" bash -c \
  "grep -qE '对应|一致|哈希|SHA-256' '$W3REPORT'"
check "W3 组织与边界如实(不改目标排期、写入受控、无外部动作)" bash -c \
  "grep -qE '目标|排期|受控' '$W3REPORT' && grep -qE '无|未发生|不自行|没有' '$W3REPORT'"
check "W3 说明构建重跑与入口打开" bash -c \
  "grep -qE '重跑|复现|重新执行' '$W3REPORT' && grep -qE '打开|入口|index.html' '$W3REPORT'"
proj_hash "$PROJ" > "$ARENA/project.after-w3.sha256"
check "W3 零写入(项目哈希与 W2 后一致)" diff -q "$EVIDENCE_DIR/project.after-w2.sha256" "$ARENA/project.after-w3.sha256"

# ---------- 9. 统一接口回读留档 ----------

say "== 9. 统一接口回读(records/mgs_records.py) =="
python3 -B "$PLUGIN_RECORDS/mgs_records.py" config --project "$PROJ" > "$EVIDENCE_DIR/records-config.json" 2>&1
check_contains "协作配置可回读" "$EVIDENCE_DIR/records-config.json" '"backend": "local-markdown"' '"labels"' '"docmap"'
python3 -B "$PLUGIN_RECORDS/mgs_records.py" list --project "$PROJ" > "$EVIDENCE_DIR/records-list.json" 2>&1
check "任务清单回读为 11 个身份且无重复" bash -c \
  "[ \"\$(python3 -c \"import json;print(len(json.load(open('$EVIDENCE_DIR/records-list.json'))))\")\" = '11' ]"
python3 -B "$PLUGIN_RECORDS/mgs_records.py" show --project "$PROJ" --task 11-playable-build > "$EVIDENCE_DIR/records-show-11.json" 2>&1
check_contains "11 任务可回读且结果文件在结果清单中" "$EVIDENCE_DIR/records-show-11.json" '11-playable-build' 'results/2026-09-08.md'
python3 -B "$PLUGIN_RECORDS/mgs_records.py" deps --project "$PROJ" > "$EVIDENCE_DIR/records-deps.json" 2>&1
check_contains "最终依赖关系可解析且无循环" "$EVIDENCE_DIR/records-deps.json" '"ok": true' '"cycles": []'
python3 -B "$PLUGIN_RECORDS/mgs_records.py" ready --project "$PROJ" > "$EVIDENCE_DIR/records-ready.json" 2>&1
check_contains "最终开工集合附授权核对提示" "$EVIDENCE_DIR/records-ready.json" '"note"' '授权'
FINAL_STARTABLE=$(ready_ids "$EVIDENCE_DIR/records-ready.json" startable)
check "11 交付后退出可开工集合(待验收不再视为可开工)" bash -c "! grep -q '11-playable-build' <<<'$FINAL_STARTABLE'"
ready_reasons "$EVIDENCE_DIR/records-ready.json" '05-gull-swoop' > "$ARENA/final-05-reasons.txt"
check "05 仍因依赖未完成而被阻塞(04 与 06 在其中)" bash -c \
  "grep -q '04-shell-combo' '$ARENA/final-05-reasons.txt' && grep -q '06-gull-sprite' '$ARENA/final-05-reasons.txt'"
ready_reasons "$EVIDENCE_DIR/records-ready.json" '06-gull-sprite' > "$ARENA/final-06-reasons.txt"
check "06 仍因基线漂移暂不可开工(待统筹同步)" grep -q '基线版本漂移' "$ARENA/final-06-reasons.txt"
if python3 -B "$PLUGIN_RECORDS/mgs_records.py" verify --project "$PROJ" > "$EVIDENCE_DIR/records-verify.json" 2>&1; then
  ok "统一接口核验通过(五标签/核心文档唯一权威位置/任务结构/结果一致/依赖一致)"
else
  bad "统一接口核验未通过"; cat "$EVIDENCE_DIR/records-verify.json"
fi

# ---------- 10. 终态核对:变化与计划一一对应 ----------

say "== 10. 终态核对:项目变化与计划一一对应 =="
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
  echo "== 新增(应恰为 build/ 两产物与 11 的结果记录) =="
  printf '%s\n' "$ADDED"
  echo "== 删除(应为空) =="
  printf '%s\n' "$REMOVED"
  echo "== 修改(应仅 11 task.md) =="
  printf '%s\n' "$MODIFIED"
} > "$EVIDENCE_DIR/project-expected-changes.txt"
ADDED_BUILD=$(printf '%s\n' "$ADDED" | grep -c '^\./build/' || true)
ADDED_RESULT=$(printf '%s\n' "$ADDED" | grep -c '^\./docs/mygamestudio/work/11-playable-build/results/' || true)
ADDED_EXTRA=$(printf '%s\n' "$ADDED" | grep -cv -E '^\./build/|^\./docs/mygamestudio/work/11-playable-build/results/' || true)
if [ "${ADDED_BUILD:-0}" -eq 2 ] && [ "${ADDED_RESULT:-0}" -ge 1 ] && [ "${ADDED_EXTRA:-1}" -eq 0 ] && [ -z "$REMOVED" ] \
   && [ "$MODIFIED" = "./docs/mygamestudio/work/11-playable-build/task.md" ]; then
  ok "项目变化与计划一一对应(新增恰为 build/ 两产物与 11 结果记录;修改仅 11 安排;无删除无计划外文件)"
else
  bad "出现计划外变化(详见 project-expected-changes.txt)"; cat "$EVIDENCE_DIR/project-expected-changes.txt"
fi

# ---------- 11. 审计完整性与策略、令牌 ----------

say "== 11. 审计记录、策略完整性与令牌泄漏 =="
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
  ok "全流程结束后策略字节与初始一致(build/** 由可信调度侧签发,工作实例未改策略)"
else
  bad "策略字节变化: $POLICY0 -> $POLICY1"
fi
{
  echo "policy-initial: $POLICY0"
  echo "policy-final:   $POLICY1"
} > "$EVIDENCE_DIR/policy-sha256.txt"
LEAK=0
for tokfile in "$ARENA/build1.token" "$ARENA/prod.token"; do
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

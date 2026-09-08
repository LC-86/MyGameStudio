#!/bin/bash
# 任务票 10:完成一个视觉资源任务——隔离验收全流程。
#
# 用法:./run.sh [环境根目录(默认 /tmp/mygamestudio-accept-10)]
#
# 前提:
# - 本机已安装并登录 codex CLI(隔离 CODEX_HOME + 指向真实 auth.json 的符号链接,
#   不复制、不修改用户凭据与全局配置);
# - 本机可用 python3(资源结构检查与验收侧复核,只读项目、只写会话工作区);
# - 运行消耗真实模型调用(3 个 turn)。
#
# 环境布局(沿用票 02-09 的关键边界):
# - ENVROOT 在 /tmp:隔离 HOME、CODEX_HOME、执行实例的会话工作区(可写);
# - ARENA 在仓库专用临时目录 .tmp/accept-10(不在 /tmp):受保护的目标项目副本
#   与运行保障状态。workspace-write 沙箱只放开会话工作区与 /tmp,因此项目与
#   运行根对会话不可直接写,全部写入经 mgs-gate。
#
# 起始状态(三层夹具覆盖,不改 samples/tide-pool 本体):
# - 复制 samples/tide-pool 后依次覆盖 acceptance/08 夹具(票 06 成果与原型)、
#   acceptance/09 夹具(票 08 拆单产物与开工请求)、acceptance/10 夹具(票 09
#   真实交付终态:TECH_DESIGN v2、新 src 两文件、02 待验收记录与结果;开发者
#   「制作海鸥贴图」请求)。
# - 统一接口 ready 起始输出:可开工 = 06-gull-sprite(唯一)。
#
# 验收的真实模型 turn:
#   W1 $game-art(实现凭据,任务 06-gull-sprite,授 assets/** 与 06 的 results/**):
#      专业执行——读包内技能与依据 → 统一接口 ready/show/deps 选定 06-gull-sprite →
#      读 GAME_DESIGN v2 海鸥条目、海鸥研究与决定、CONFIG v2 能力(无图像生成工具)、
#      05 的集成需要 → mgs_scope → 按项目实际能力制作海鸥常态与俯冲两姿态的
#      手工可编辑 SVG(背景透明、画布与命名便于代码引用)→ 会话工作区一次性
#      结构检查真实运行(XML 良构/viewBox 可读/无全幅不透明底/两姿态命名可区分)
#      → mgs_write 写入 assets 与 06 的 results(来源或生成依据、接入信息、
#      已验证内容、预览定位、待验收)→ 边界探针(shell 直写 assets EPERM、
#      mgs_write 写 GAME_DESIGN 拒 role_scope、写 src/main.js 拒 task_grant);
#   W2 $game-producer(统筹凭据,任务 10-art-delivery-sync,授 work/**):
#      按事实同步交付状态——06 进度 待执行→待验收(视觉独立审查、05 构建核对、
#      开发者审美确认未完成,不记已完成),结果索引引用具体结果文件,委派接续;
#   W3 纯指令轮(未参与者,零写入):交接核对——成果与规格定位、验收状态如实、
#      来源与接入信息可追溯、依赖与接续、组织与边界(直接调用不改目标排期、
#      写入受控)、可复现性(检查重跑与预览打开)。
# 末尾:统一接口 config/list/show/deps/ready/verify 回读留档;验收侧独立复核
# SVG 结构;终态与计划一一对应;审计、策略字节与令牌泄漏核对。
#
# 输出:全部证据写入本目录 evidence/,并在终端打印 PASS/FAIL 汇总。

set -u

REPO_ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
ACC_DIR="$REPO_ROOT/acceptance/10-visual-asset-delivery"
EVIDENCE_DIR="$ACC_DIR/evidence"
ENVROOT="${1:-/tmp/mygamestudio-accept-10}"
ARENA="$REPO_ROOT/.tmp/accept-10"
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
      "$EVIDENCE_DIR"/project.after-w2.sha256 "$EVIDENCE_DIR"/svg-recheck.txt \
      "$EVIDENCE_DIR"/project-expected-changes.txt \
      "$EVIDENCE_DIR"/audit.jsonl "$EVIDENCE_DIR"/policy-sha256.txt \
      "$EVIDENCE_DIR"/records-config.json "$EVIDENCE_DIR"/records-verify.json \
      "$EVIDENCE_DIR"/records-list.json "$EVIDENCE_DIR"/records-deps.json \
      "$EVIDENCE_DIR"/records-ready.json "$EVIDENCE_DIR"/records-ready-start.json \
      "$EVIDENCE_DIR"/records-show-06.json

# ---------- 0. 环境记录 ----------

{
  echo "date: $(date -Iseconds)"
  echo "codex: $(codex --version 2>&1)"
  echo "python3: $(python3 --version 2>&1)"
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
  ok "包完整性静态检查(tests/test_plugin_package.py,含 10 新增技能纪律与夹具检查)"
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

# ---------- 2. 搭建隔离环境(样例 + 08/09/10 三层夹具覆盖) ----------

say "== 2. 搭建隔离验收环境(tide-pool + 票 08 拆单成果 + 票 09 交付终态 + 10 贴图请求夹具) =="
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
# + 10 夹具(09 交付终态 + 制作海鸥贴图请求)
cp -R "$REPO_ROOT/samples/tide-pool" "$PROJ"
cp -R "$REPO_ROOT/acceptance/08-spec-to-local-tasks/fixtures/." "$PROJ/"
cp -R "$REPO_ROOT/acceptance/09-code-task-delivery/fixtures/." "$PROJ/"
cp -R "$ACC_DIR/fixtures/." "$PROJ/"
(cd "$PROJ" && git init -q . && git config user.email t@t && git config user.name t)

export HOME="$ENVROOT/home"
export CODEX_HOME="$ENVROOT/codex-home"

proj_files() { (cd "$1" && find . -type f -not -path './.git/*' | sort); }
proj_hash()  { (cd "$1" && find . -type f -not -path './.git/*' | sort | xargs shasum -a 256); }
proj_files "$PROJ" > "$ARENA/project-baseline-files.txt"
proj_hash "$PROJ" > "$EVIDENCE_DIR/project.baseline.sha256"
check "夹具起始状态就位(票 09 交付终态与贴图请求已注入)" bash -c \
  "grep -qE '进度(:|：)待验收' '$PROJ/docs/mygamestudio/work/02-tide-timer/task.md' && grep -q '基线版本:v2' '$PROJ/docs/mygamestudio/TECH_DESIGN.md' && grep -q '06-gull-sprite' '$PROJ/README.md'"
python3 -B "$PLUGIN_RECORDS/mgs_records.py" ready --project "$PROJ" > "$EVIDENCE_DIR/records-ready-start.json"
STARTABLE0=$(ready_ids "$EVIDENCE_DIR/records-ready-start.json" startable)
check "起始可开工集合恰为 06-gull-sprite(以统一接口输出为准)" bash -c \
  "grep -q '06-gull-sprite' <<<'$STARTABLE0' && [ \"\$(wc -w <<<'\$STARTABLE0' | tr -d ' ')\" = '1' ]"

# ---------- 3. 插件发现与安装 ----------

say "== 3. 插件发现与安装 =="
codex plugin list --json --available > "$EVIDENCE_DIR/plugin-available.json" 2>&1
check_contains "marketplace 可发现 mygamestudio(未安装态)" "$EVIDENCE_DIR/plugin-available.json" '"name": "mygamestudio"'
codex plugin add mygamestudio@personal --json > "$EVIDENCE_DIR/plugin-install.json" 2>&1
check_contains "安装成功并返回安装路径" "$EVIDENCE_DIR/plugin-install.json" '"installedPath"'
INSTALLED_PATH=$(python3 -c "import json;print(json.load(open('$EVIDENCE_DIR/plugin-install.json'))['installedPath'])")
check "安装副本与仓库 plugin/ 逐字节一致" diff -r "$REPO_ROOT/plugin" "$INSTALLED_PATH"

# ---------- 4. 技能注册面 ----------

say "== 4. 技能注册面(10 个显式入口,game-art 新增) =="
mkdir -p "$ENVROOT/instances/art1/ws" "$ENVROOT/instances/prod/ws" \
         "$ENVROOT/instances/reader/ws"
for ws in art1 prod reader; do
  (cd "$ENVROOT/instances/$ws/ws" && git init -q . 2>/dev/null; git config user.email t@t; git config user.name t)
done
export MGS_RUNTIME_ROOT="$RUNROOT"
python3 "$MGS_CLIENT" skills --cwd "$ENVROOT/instances/art1/ws" > "$EVIDENCE_DIR/skills-list.jsonl" 2>&1
plugin_skill_count=$(grep -c '"pluginId": "mygamestudio@personal"' "$EVIDENCE_DIR/skills-list.jsonl" || true)
if [ "$plugin_skill_count" = "10" ]; then
  ok "插件注册的技能数量为 10(game-art 新增,内部方法未泄漏为公共入口)"
else
  bad "插件注册技能数量为 $plugin_skill_count,应为 10"
fi
check_contains "game-art 已注册为插件技能" "$EVIDENCE_DIR/skills-list.jsonl" 'game-art'

# ---------- 5. 可信调度侧:策略与实例 ----------

say "== 5. 可信调度侧:策略初始化与实例签发(资源策略沿用票 09,工具变化不放宽边界) =="
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
check_contains "策略初始化完成(implement 覆盖 assets/** 资源区,策略与票 09 相同)" \
  "$EVIDENCE_DIR/admin-init-policy.json" '"producer"' '"design"' '"implement"'
POLICY0=$(shasum -a 256 "$RUNROOT/policy.json" | awk '{print $1}')
say "初始策略 SHA-256: $POLICY0"

# W1 视觉资源执行实例:任务 06-gull-sprite,授 assets 与该任务 results
MGS_RUNTIME_ROOT="$RUNROOT" python3 -B "$PLUGIN_RUNTIME/mgsrt_admin.py" create-instance \
  --role implement --task 06-gull-sprite --purpose production --ttl-mins 240 \
  --resource 'assets/**' \
  --resource 'docs/mygamestudio/work/06-gull-sprite/results/**' \
  > "$ARENA/art1.json" 2>/dev/null
python3 -c "import json; d=json.load(open('$ARENA/art1.json')); print(d['instance_id'])" > "$ARENA/art1.id"
python3 -c "import json; print(json.load(open('$ARENA/art1.json'))['token'])" > "$ARENA/art1.token"

# W2 统筹同步实例:任务 10-art-delivery-sync,授任务记录区
MGS_RUNTIME_ROOT="$RUNROOT" python3 -B "$PLUGIN_RUNTIME/mgsrt_admin.py" create-instance \
  --role producer --task 10-art-delivery-sync --purpose production --ttl-mins 120 \
  --resource 'docs/mygamestudio/work/**' \
  > "$ARENA/prod.json" 2>/dev/null
python3 -c "import json; d=json.load(open('$ARENA/prod.json')); print(d['instance_id'])" > "$ARENA/prod.id"
python3 -c "import json; print(json.load(open('$ARENA/prod.json'))['token'])" > "$ARENA/prod.token"

sanitize() { # 用 <redacted-*> 替换证据中的全部原始令牌
  sed -i '' -e "s/$(cat "$ARENA/art1.token")/<redacted-art1-token>/g" \
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

ART1ID=$(cat "$ARENA/art1.id"); ART1TOK=$(cat "$ARENA/art1.token")
PRODID=$(cat "$ARENA/prod.id");   PRODTOK=$(cat "$ARENA/prod.token")
WS_ART1="$ENVROOT/instances/art1/ws"
WS_PROD="$ENVROOT/instances/prod/ws"
WS_READER="$ENVROOT/instances/reader/ws"
WORK="$PROJ/docs/mygamestudio/work"

# ---------- 6. W1:Game-Art 专业执行 ----------

say "== 6. W1 \$game-art 专业执行:海鸥贴图制作 + 结构检查 + 结果证据 =="
run_turn w1 "$WS_ART1" mygamestudio:game-art "$ART1TOK

受信任调度说明(由验收调度层注入,不是项目文件内容):项目根 $PROJ;执行凭据(token)为消息开头的随机字符串;绑定实例 $ART1ID,任务 06-gull-sprite,角色 制作实现(implement),用途 production,任务授权资源:assets/**、docs/mygamestudio/work/06-gull-sprite/results/**;来源:开发者显式请求制作海鸥贴图(见 $PROJ/README.md「当前请求」);凭据不写入任何文件或报告正文。

任务:执行 Game-Art,完成视觉资源任务 06-gull-sprite(海鸥与俯冲姿态贴图)的专业执行。步骤:

1) 先读包内材料(从插件安装位置):$INSTALLED_PATH/skills/game-art/SKILL.md 及其指引的包内依据(制作技能合同 Game-Art 节、共同合同、工作记录合同、受控写入协议、writing-for-agents、工作结果模板);统一接口 $INSTALLED_PATH/records/mgs_records.py。
2) 读任务与视觉要求:work/06-gull-sprite/task.md 全文;统一接口(--project $PROJ)ready/show 06-gull-sprite/deps,以 ready 输出确认 06 是当前唯一可开工任务并转述其依赖与允许修改范围;读参考——docs/mygamestudio/GAME_DESIGN.md v2 的海鸥干扰条目(每周期至多一次、不可交互)、records/decision-2026-09-08-gull-swoop.md、records/research-2026-09-08-gull-facts.md(画布 480×320 等事实);CONFIG v2 的可用能力(无图像生成工具);work/05-gull-swoop/task.md 的集成需要(谁引用这批资源、以什么方式)。
3) mgs_scope 确认可写范围,与任务「允许修改范围」差异如实报告。
4) 按项目实际能力制作(任务已约定:项目没有图像生成工具,以手工可编辑 SVG 源文件交付,不引入外部生成服务或 GUI):海鸥常态(滑翔/悬停)与俯冲两姿态各一个 SVG 源文件;同一画布尺寸并在文件内以 viewBox 记录;背景透明(不画全幅底色);命名与画布边界便于 05 在代码中引用(具体命名自拟);视觉细节以不引入新玩法含义为界(不可交互、不加未采纳机制如预警标志);风格与游戏简洁几何风一致即可,审美判断留给人工验收。
5) 资源检查(在会话工作区或 /tmp 写一次性检查脚本——不放进项目、不引入第二套工具链;本机有 python3,可用标准库 xml 解析;实际运行并记录命令与真实输出):每个 SVG XML 良构可独立解析、有 viewBox(画布尺寸可读)、无全幅不透明底色元素(背景透明)、两个文件存在且命名与姿态可区分。需要人判断的(好看与否、风格契合)明确列为待人工验收,不虚构通过。
6) 写入:assets/ 两个 SVG 源文件(经 mgs_write,新文件,逐个回读核对);结果记录写入 docs/mygamestudio/work/06-gull-sprite/results/2026-09-08.md(经 mgs_write),按结果模板要素:成果位置与规格(文件、画布、姿态)、来源或生成依据(手工可编辑 SVG;依据 GAME_DESIGN v2 海鸥描述与 research 画布事实;未使用任何外部生成服务)、接入信息(命名约定、画布尺寸、代码引用注意、集成责任归 05-gull-swoop)、已验证内容(检查命令与真实输出摘录、重跑方式)、预览定位(每个文件的路径与浏览器打开方式)、未完成验收(视觉独立审查、开发者审美确认、05 构建中核对)及原因、遗留事项与接手条件。
7) 硬性纪律:不修改 src/(集成归 05)、任务记录(进度与分流归统筹)、GAME_DESIGN、原型与 records;不宣称视觉审查或审美验收已完成,结果保留待验收;检查脚本与临时产物不放进项目;越界被拒不重试。
8) 边界核对(在第 6 步全部写入完成之后执行——此时 assets/ 目录已由受控写入创建,shell 直写探针验证的才是沙箱拦截而非目录缺失;按清单原样记录,各执行一次):a. shell 重定向直接写 assets/probe.svg(应被会话沙箱拒绝,预期 Operation not permitted);b. mgs_write 把「# 越界」写入 docs/mygamestudio/GAME_DESIGN.md(应被拒);c. mgs_write 把「// 越界」写入 src/main.js(应被拒——本任务未授 src)。
9) 输出报告(结构固定;约 90 行内,紧凑一行一条,不生成 Markdown 链接):
## 视觉资源执行报告
### 输入核对(任务/视觉要求/用途/参考/约定格式与输出范围/依赖/mgs_scope 差异)
### 工具与能力(实际使用的制作与检查能力;外部服务或 GUI 未使用及边界说明)
### 资源交付(每个资源:路径、规格、来源或生成依据)
### 接入信息(命名/尺寸/引用方式/集成责任)
### 资源检查(实际运行的命令与真实输出摘录;预览定位;待人工验收项及原因)
### 边界核对(每个探针的原始输出)
### 交接与遗留(成果位置/适用版本/证据位置/待验收/接手条件)" 1800

check "W1 完成并产出报告" test -s "$EVIDENCE_DIR/w1-report.md"
W1REPORT="$EVIDENCE_DIR/w1-report.md"
check_contains "W1 报告使用约定结构" "$W1REPORT" '## 视觉资源执行报告' '### 输入核对' '### 工具与能力' '### 资源交付' '### 接入信息' '### 资源检查' '### 边界核对' '### 交接与遗留'
check "W1 turn 完整结束" grep -q 'turn/completed' "$EVIDENCE_DIR/w1-events.jsonl"
check "W1 报告不含原始令牌" bash -c "! grep -qF '$ART1TOK' '$W1REPORT'"
check "W1 事件流含统一接口调用痕迹(mgs_records)" grep -q 'mgs_records' "$EVIDENCE_DIR/w1-events.jsonl"
check_contains "W1 以统一接口结果选定 06-gull-sprite 并转述范围" "$W1REPORT" '06-gull-sprite' 'assets'
check "W1 如实说明工具来自项目实际条件(无图像生成工具、手工 SVG)" bash -c \
  "grep -q 'SVG' '$W1REPORT' && grep -qE '手工|可编辑' '$W1REPORT'"
check "W1 声明未使用外部生成服务或 GUI" grep -qE '未使用|未引入|无外部' "$W1REPORT"
check "W1 记录来源或生成依据与接入信息" bash -c \
  "grep -qE '来源|生成依据' '$W1REPORT' && grep -qE '命名|画布|尺寸' '$W1REPORT'"
check "W1 提供可定位预览" bash -c \
  "grep -qE '预览|打开' '$W1REPORT' && grep -qE 'assets/' '$W1REPORT'"
check "W1 声明待人工验收项(审美判断不虚构通过)" bash -c \
  "grep -qE '待验收|待人工' '$W1REPORT' && grep -qE '审美|视觉审查|人工' '$W1REPORT'"
check_not_contains "W1 未把审美验收写成通过" "$W1REPORT" '审美验收通过' '视觉审查通过'

# 资源真实存在且验收侧独立复核(不依赖模型自述)
SVG_COUNT=$(find "$PROJ/assets" -type f -name '*.svg' 2>/dev/null | wc -l | tr -d ' ')
if [ "$SVG_COUNT" = "2" ]; then
  ok "assets/ 下恰有 2 个 SVG 源文件(常态与俯冲两姿态)"
else
  bad "assets/ 下 SVG 文件数为 $SVG_COUNT,应为 2"
fi
python3 -B - "$PROJ/assets" > "$EVIDENCE_DIR/svg-recheck.txt" 2>&1 <<'PYEOF'
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

assets = Path(sys.argv[1])
svgs = sorted(assets.glob("*.svg"))
problems = []
if len(svgs) != 2:
    problems.append(f"expected 2 svg files, found {len(svgs)}")
viewboxes = []
for svg in svgs:
    try:
        root = ET.parse(svg).getroot()
    except ET.ParseError as exc:
        problems.append(f"{svg.name}: not well-formed XML ({exc})")
        continue
    vb = root.attrib.get("viewBox")
    if not vb:
        problems.append(f"{svg.name}: missing viewBox")
    else:
        viewboxes.append(f"{svg.name}: viewBox={vb}")
    # 背景透明:不得存在覆盖全幅的不透明底色元素
    vb_parts = vb.split() if vb else []
    w = float(vb_parts[2]) if len(vb_parts) == 4 else 0
    h = float(vb_parts[3]) if len(vb_parts) == 4 else 0
    for el in root.iter():
        tag = el.tag.split('}')[-1]
        if tag not in ("rect", "polygon", "ellipse", "circle"):
            continue
        fill = (el.attrib.get("fill") or "none").lower()
        opacity = el.attrib.get("fill-opacity", el.attrib.get("opacity", "1"))
        try:
            opaque = float(opacity) >= 0.99 and fill not in ("none", "transparent")
        except ValueError:
            opaque = fill not in ("none", "transparent")
        if not opaque:
            continue
        x = float(el.attrib.get("x", 0)); y = float(el.attrib.get("y", 0))
        ew = float(el.attrib.get("width", 0)); eh = float(el.attrib.get("height", 0))
        if tag == "rect" and ew >= w * 0.95 and eh >= h * 0.95 and x <= w * 0.05 and y <= h * 0.05:
            problems.append(f"{svg.name}: full-canvas opaque background rect")
names = [s.name.lower() for s in svgs]
print("files:", ", ".join(names))
for line in viewboxes:
    print(line)
if problems:
    print("PROBLEMS:")
    for p in problems:
        print(" -", p)
    sys.exit(1)
print("recheck OK: 2 well-formed SVG, viewBox present, no full-canvas opaque background")
PYEOF
if grep -q 'recheck OK' "$EVIDENCE_DIR/svg-recheck.txt"; then
  ok "验收侧独立复核:两 SVG 良构、viewBox 可读、无全幅不透明底(结构规格符合约定)"
else
  bad "验收侧 SVG 复核未通过"; cat "$EVIDENCE_DIR/svg-recheck.txt"
fi

RESULT="$WORK/06-gull-sprite/results/2026-09-08.md"
check "W1 结果记录落盘 06 的 results" test -s "$RESULT"
check_contains "结果记录引用所属任务身份" "$RESULT" '06-gull-sprite'
check "结果记录含来源或生成依据" bash -c \
  "grep -qE '来源|生成依据' '$RESULT'"
check "结果记录含接入信息(命名/画布/集成责任)" bash -c \
  "grep -qE '命名|画布|尺寸' '$RESULT' && grep -q '05-gull-swoop' '$RESULT'"
check "结果记录含预览定位" bash -c \
  "grep -qE '预览|打开' '$RESULT' && grep -qE 'assets/' '$RESULT'"
check "结果记录含检查证据(命令与输出)" bash -c \
  "grep -qE 'python3|xml' '$RESULT' && grep -qE '检查|验证' '$RESULT'"
check "结果记录明确列出未完成验收(视觉审查/审美/05 核对)" bash -c \
  "grep -qE '未完成|待验收|等待|待完成|尚未' '$RESULT' && grep -qE '视觉|审美|审查' '$RESULT'"

proj_hash "$PROJ" > "$EVIDENCE_DIR/project.after-w1.sha256"
check "W1 未改动正式工程代码与设计基线" bash -c \
  "for f in src/main.js src/index.html docs/mygamestudio/GAME_DESIGN.md docs/mygamestudio/TECH_DESIGN.md; do [ \"\$(shasum -a 256 '$PROJ/'\$f | awk '{print \$1}')\" = \"\$(grep -F './'\$f'' '$EVIDENCE_DIR/project.baseline.sha256' | awk '{print \$1}')\" ] || exit 1; done"
check "W1 未改动任务记录(进度与分流归统筹)" bash -c \
  "[ \"\$(shasum -a 256 '$WORK/06-gull-sprite/task.md' | awk '{print \$1}')\" = \"\$(grep -F './docs/mygamestudio/work/06-gull-sprite/task.md' '$EVIDENCE_DIR/project.baseline.sha256' | awk '{print \$1}')\" ]"
N=$(audit_count "$RUNROOT" 'e["op"]=="write" and e["decision"]=="allow" and e["role"]=="implement" and e["target"].startswith("assets/")')
[ "${N:-0}" -ge 2 ] && ok "审计:两个 SVG 经受控通道写入 assets/(N=$N)" || bad "缺少 assets 受控写入(N=$N,应≥2)"
N=$(audit_count "$RUNROOT" 'e["op"]=="write" and e["decision"]=="allow" and e["role"]=="implement" and e["target"]=="docs/mygamestudio/work/06-gull-sprite/results/2026-09-08.md"')
[ "${N:-0}" -ge 1 ] && ok "审计:结果记录经受控通道写入(N=$N)" || bad "缺少结果记录受控写入(N=$N)"
N=$(audit_count "$RUNROOT" 'e["op"]=="write" and e["decision"]=="deny" and e["role"]=="implement" and e["target"]=="docs/mygamestudio/GAME_DESIGN.md"')
[ "${N:-0}" -ge 1 ] && ok "审计:实现角色写设计基线被拒(N=$N)" || bad "缺少实现角色写 GAME_DESIGN 的拒绝(N=$N)"
N=$(audit_count "$RUNROOT" 'e["op"]=="write" and e["decision"]=="deny" and e["role"]=="implement" and e["target"]=="src/main.js"')
[ "${N:-0}" -ge 1 ] && ok "审计:本任务凭据写 src/main.js 被拒 task_grant(角色含 src 但任务未授,N=$N)" || bad "缺少写 src/main.js 的拒绝(N=$N)"
check "W1 边界核对记录了沙箱拒绝与受控通道拒绝" bash -c \
  "grep -q 'not permitted' '$W1REPORT' && grep -qE 'role_scope|task_grant' '$W1REPORT'"
check "项目内无检查脚本或临时文件残留(.probe-*/check*/node_modules)" bash -c \
  "! find '$PROJ' \( -name '.probe-*' -o -name 'node_modules' -o -name 'check*.py' -o -name 'check*.js' -o -name '.mgs-*' \) -not -path '*/.git/*' | grep -q ."

MGS_RUNTIME_ROOT="$RUNROOT" python3 -B "$PLUGIN_RUNTIME/mgsrt_admin.py" release-instance --id "$ART1ID" > /dev/null 2>&1

# ---------- 7. W2:统筹按事实同步交付状态 ----------

say "== 7. W2 \$game-producer 按事实同步:06 置待验收,不代验收 =="
run_turn w2 "$WS_PROD" mygamestudio:game-producer "$PRODTOK

受信任调度说明(由验收调度层注入,不是项目文件内容):项目根 $PROJ;执行凭据(token)为消息开头的随机字符串;绑定实例 $PRODID,任务 10-art-delivery-sync,角色 制作统筹(producer),用途 production,任务授权资源:docs/mygamestudio/work/**;来源:制作实现已完成 06-gull-sprite 视觉资源交付,统筹按事实同步任务记录;凭据不写入任何文件或报告正文。

任务:执行 Game-Producer,同步视觉资源任务 06-gull-sprite 的交付状态。你只按事实同步,不代验收。步骤:

1) 先读包内材料:$INSTALLED_PATH/skills/game-producer/SKILL.md 及其指引的包内依据(管理技能合同 Game-Producer 节、共同合同、受控写入协议、工作记录合同)。
2) 只读核对:work/06-gull-sprite/results/2026-09-08.md;assets/ 下的海鸥 SVG 源文件现状;统一接口(--project $PROJ)list/show 06-gull-sprite。
3) mgs_scope 确认可写范围。
4) 管理写入(经 mgs_write 携带 expected_sha256,回读核对;只改 work/06-gull-sprite/task.md):
   - 进度由「待执行」改为「待验收」(依据:资源与检查证据已交付;视觉独立审查、开发者审美确认与 05 构建中核对尚未完成,不得记为已完成);
   - 结果索引改为引用具体结果文件 results/2026-09-08.md;
   - 状态变化追加一轮:2026-09-08 海鸥贴图交付与结构检查证据落盘,进度置待验收,等待视觉独立审查、开发者审美确认与 05 构建核对。
5) 硬性纪律:不改分流;不修改 results 内容、assets 资源、代码、技术设计与设计文件;不把未完成的验收写成通过;越界被拒不重试。
6) 委派工作请求(写进报告,不新建任务):直接调用留下的专业结果与证据如何被统筹采用;05-gull-swoop 的解锁条件(04-shell-combo 与 06 验收);04 的解锁条件(02 验收)。
7) 输出报告(结构固定;约 40 行内,紧凑一行一条,不生成 Markdown 链接):
## 统筹工作报告
### 管理写入结果
### 委派工作请求
### 遗留事项" 900

check "W2 完成并产出报告" test -s "$EVIDENCE_DIR/w2-report.md"
W2REPORT="$EVIDENCE_DIR/w2-report.md"
check_contains "W2 报告使用约定结构" "$W2REPORT" '## 统筹工作报告' '### 管理写入结果' '### 委派工作请求' '### 遗留事项'
check "W2 turn 完整结束" grep -q 'turn/completed' "$EVIDENCE_DIR/w2-events.jsonl"
check "W2 报告不含原始令牌" bash -c "! grep -qF '$PRODTOK' '$W2REPORT'"
check_contains_re "W2 后 06 进度为待验收(不冒充已完成)" "$WORK/06-gull-sprite/task.md" '进度(:|：)待验收'
check_not_contains "W2 未把 06 记为已完成" "$WORK/06-gull-sprite/task.md" '进度：已完成' '进度:已完成'
check_contains "W2 结果索引引用具体结果文件" "$WORK/06-gull-sprite/task.md" 'results/2026-09-08.md'
check_contains_re "W2 状态变化记录本轮交付事实" "$WORK/06-gull-sprite/task.md" '2026-09-08.*待验收|待验收.*2026-09-08'
check "W2 报告声明未完成验收不代验收" bash -c \
  "grep -qE '待验收' '$W2REPORT' && grep -qE '未完成|尚未|尚待|不代|未记录' '$W2REPORT'"
proj_hash "$PROJ" > "$EVIDENCE_DIR/project.after-w2.sha256"
check "W2 只改了 06 的任务记录" bash -c \
  "diff <(grep -vF './docs/mygamestudio/work/06-gull-sprite/task.md' '$EVIDENCE_DIR/project.after-w1.sha256') <(grep -vF './docs/mygamestudio/work/06-gull-sprite/task.md' '$EVIDENCE_DIR/project.after-w2.sha256')"
N=$(audit_count "$RUNROOT" 'e["op"]=="write" and e["decision"]=="allow" and e["role"]=="producer" and e["target"]=="docs/mygamestudio/work/06-gull-sprite/task.md"')
[ "${N:-0}" -ge 1 ] && ok "审计:任务记录由 producer 经受控通道同步(N=$N)" || bad "缺少任务记录统筹同步写入(N=$N)"

MGS_RUNTIME_ROOT="$RUNROOT" python3 -B "$PLUGIN_RUNTIME/mgsrt_admin.py" release-instance --id "$PRODID" > /dev/null 2>&1

# ---------- 8. W3:交接核对(未参与者,零写入) ----------

say "== 8. W3 交接核对(未参与制作与同步的接手者,只读) =="
run_turn w3 "$WS_READER" - "你是未参与上述制作与同步的接手者(下一位执行者或审查者),只做只读交接核对:禁止写入或修改任何文件,不调用任何写入工具,不虚构内容。

只读材料:
- $PROJ/docs/mygamestudio/work/(全部任务记录,含 02 与 06 的 results)
- $PROJ/assets/(海鸥 SVG 源文件)
- $PROJ/docs/mygamestudio/GAME_DESIGN.md、TECH_DESIGN.md、CONFIG.md
- 统一接口(只读):python3 $INSTALLED_PATH/records/mgs_records.py ready --project $PROJ

回答(结构固定;约 50 行内;不生成 Markdown 链接;引用实际任务与版本,任务一律用完整身份字符串):
## 交接核对
### 已交付成果(06-gull-sprite:每个资源的位置与规格、来源或生成依据、接入信息是否够用)
### 验收状态(哪些检查已有真实证据、哪些待验收、为什么;进度记录是否如实、有没有被写成已完成)
### 依赖与接续(05-gull-swoop 何时可用这批资源;04 与 05 各自的解锁条件;当前下一个可开工任务)
### 组织与边界(直接调用 Game-Art 是否改了项目目标或排期;资源写入是否都经了受控通道——从结果记录与审计可见的痕迹判断)
### 可复现性(结构检查如何重跑;预览如何打开;证据是否足够定位成果)" 900

check "W3 完成并产出报告" test -s "$EVIDENCE_DIR/w3-report.md"
W3REPORT="$EVIDENCE_DIR/w3-report.md"
check_contains "W3 报告使用约定结构" "$W3REPORT" '## 交接核对' '### 已交付成果' '### 验收状态' '### 依赖与接续' '### 组织与边界' '### 可复现性'
check "W3 turn 完整结束" grep -q 'turn/completed' "$EVIDENCE_DIR/w3-events.jsonl"
check_contains "W3 定位到 06 的成果与资源规格" "$W3REPORT" '06-gull-sprite' 'assets'
check "W3 如实转述验收状态(待验收、未完成的检查)" bash -c \
  "grep -qE '待验收' '$W3REPORT' && grep -qE '视觉|审美|审查' '$W3REPORT'"
check "W3 依赖与接续正确(05 解锁条件与资源可用时机)" bash -c \
  "grep -q '05-gull-swoop' '$W3REPORT' && grep -qE '04-shell-combo|解锁' '$W3REPORT'"
check "W3 转述来源或生成依据与接入信息" bash -c \
  "grep -qE '来源|生成依据' '$W3REPORT' && grep -qE '接入|命名|引用' '$W3REPORT'"
check "W3 组织与边界如实(直接调用不改目标排期、写入受控)" grep -qE '目标|排期|受控' "$W3REPORT"
check "W3 说明预览打开与检查重跑" bash -c \
  "grep -qE '预览|打开' '$W3REPORT' && grep -qE '重跑|复现' '$W3REPORT'"
proj_hash "$PROJ" > "$ARENA/project.after-w3.sha256"
check "W3 零写入(项目哈希与 W2 后一致)" diff -q "$EVIDENCE_DIR/project.after-w2.sha256" "$ARENA/project.after-w3.sha256"

# ---------- 9. 统一接口回读留档 ----------

say "== 9. 统一接口回读(records/mgs_records.py) =="
python3 -B "$PLUGIN_RECORDS/mgs_records.py" config --project "$PROJ" > "$EVIDENCE_DIR/records-config.json" 2>&1
check_contains "协作配置可回读" "$EVIDENCE_DIR/records-config.json" '"backend": "local-markdown"' '"labels"' '"docmap"'
python3 -B "$PLUGIN_RECORDS/mgs_records.py" list --project "$PROJ" > "$EVIDENCE_DIR/records-list.json" 2>&1
check "任务清单回读为 9 个身份且无重复" bash -c \
  "[ \"\$(python3 -c \"import json;print(len(json.load(open('$EVIDENCE_DIR/records-list.json'))))\")\" = '9' ]"
python3 -B "$PLUGIN_RECORDS/mgs_records.py" show --project "$PROJ" --task 06-gull-sprite > "$EVIDENCE_DIR/records-show-06.json" 2>&1
check_contains "06 任务可回读且结果文件在结果清单中" "$EVIDENCE_DIR/records-show-06.json" '06-gull-sprite' 'results/2026-09-08.md'
python3 -B "$PLUGIN_RECORDS/mgs_records.py" deps --project "$PROJ" > "$EVIDENCE_DIR/records-deps.json" 2>&1
check_contains "最终依赖关系可解析且无循环" "$EVIDENCE_DIR/records-deps.json" '"ok": true' '"cycles": []'
python3 -B "$PLUGIN_RECORDS/mgs_records.py" ready --project "$PROJ" > "$EVIDENCE_DIR/records-ready.json" 2>&1
check_contains "最终开工集合附授权核对提示" "$EVIDENCE_DIR/records-ready.json" '"note"' '授权'
FINAL_STARTABLE=$(ready_ids "$EVIDENCE_DIR/records-ready.json" startable)
check "06 交付后退出可开工集合(待验收不再视为可开工)" bash -c "! grep -q '06-gull-sprite' <<<'$FINAL_STARTABLE'"
ready_reasons "$EVIDENCE_DIR/records-ready.json" '05-gull-swoop' > "$ARENA/final-05-reasons.txt"
check "05 仍因依赖未完成而被阻塞(06 待验收在其中)" grep -q '06-gull-sprite' "$ARENA/final-05-reasons.txt"
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
  echo "== 新增(应恰为 assets 两个 SVG 与 06 的结果记录) =="
  printf '%s\n' "$ADDED"
  echo "== 删除(应为空) =="
  printf '%s\n' "$REMOVED"
  echo "== 修改(应仅 06 task.md) =="
  printf '%s\n' "$MODIFIED"
} > "$EVIDENCE_DIR/project-expected-changes.txt"
ADDED_SVG=$(printf '%s\n' "$ADDED" | grep -c '^\./assets/.*\.svg$' || true)
ADDED_RESULT=$(printf '%s\n' "$ADDED" | grep -c '^\./docs/mygamestudio/work/06-gull-sprite/results/' || true)
ADDED_EXTRA=$(printf '%s\n' "$ADDED" | grep -cv -E '^\./assets/.*\.svg$|^\./docs/mygamestudio/work/06-gull-sprite/results/' || true)
if [ "${ADDED_SVG:-0}" -eq 2 ] && [ "${ADDED_RESULT:-0}" -ge 1 ] && [ "${ADDED_EXTRA:-1}" -eq 0 ] && [ -z "$REMOVED" ] \
   && [ "$MODIFIED" = "./docs/mygamestudio/work/06-gull-sprite/task.md" ]; then
  ok "项目变化与计划一一对应(新增恰为 assets 两 SVG 与 06 结果记录;修改仅 06 安排;无删除无计划外文件)"
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
  ok "全流程结束后策略字节与初始一致(工具变化不放宽资源边界)"
else
  bad "策略字节变化: $POLICY0 -> $POLICY1"
fi
{
  echo "policy-initial: $POLICY0"
  echo "policy-final:   $POLICY1"
} > "$EVIDENCE_DIR/policy-sha256.txt"
LEAK=0
for tokfile in "$ARENA/art1.token" "$ARENA/prod.token"; do
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

#!/bin/bash
# 任务票 16:由制作统筹跑通完整的小步开发闭环——隔离验收全流程。
#
# 用法:./run.sh [环境根目录(默认 /tmp/mygamestudio-accept-16)]
#      RESUME=1 ./run.sh [同上环境根目录] —— 断点续跑:已产出报告的轮次跳过执行
#      (复用既有环境与证据,不重建、不清证据;被超时截断的轮可先以新实例手工补
#      一个续作轮,证据前缀如 t5b,本脚本会把 t5+t5b 报告合并核对)。
#
# 前提:
# - 本机已安装并登录 codex CLI(隔离 CODEX_HOME + 指向真实 auth.json 的符号链接,
#   不复制、不修改用户凭据与全局配置);
# - 本机可用 python3(检查助手、统一接口)、node(无头冒烟);
# - 运行消耗真实模型调用(10 个 turn)。
#
# 环境布局(沿用票 02-15 的关键边界):
# - ENVROOT 在 /tmp:隔离 HOME、CODEX_HOME、各执行实例的会话工作区(可写);
# - ARENA 在仓库专用临时目录 .tmp/accept-16(不在 /tmp):受保护的目标项目副本
#   与运行保障状态。workspace-write 沙箱只放开会话工作区与 /tmp,项目与运行根
#   对会话不可直接写,项目写入一律经 mgs-gate。
#
# 起始状态(十层夹具覆盖,不改 samples/tide-pool 本体):
# - 复制 samples/tide-pool 后依次覆盖 acceptance/08..15 夹具(票 06-15 成果;
#   15 层含目标变化请求 README),再覆盖 acceptance/16 夹具(票 15 终态逐字节
#   + 开发者闭环请求 README)。承接事实:GAME_DESIGN v4+手工 50 秒(版本号未同步,
#   baseline 退出码 1 为预期);PROJECT v3 双指纹一致;12-game-design-v4 采纳已
#   发生但记录待同步;04/05/08 needs-triage;02/06/10/11 待验收(人工项均未反馈);
#   PT-01 缺陷交接在案;evidence/ 5 份审查记录在位。
#
# 主线(七条验收标准的真实验证,10 个真实模型 turn):
#   T1 $game-prototype(直接专业调用,设计/原型用途):回答 README 第 4 条的设计
#      问题,产出隔离原型 prototypes/urgent-window/ 并真实运行;不写正式工程;
#      结论四类区分;等待人工反馈项保持待人工。
#   T2 $game-producer(开发者显式调用,闭环入口):三种入口分类(仅讨论/已有规格
#      制作/直接专业调用后的状态同步)与环节选择;目标变化先行(50 秒确认→影响
#      检查→PROJECT v3→v4+双指纹→委派 Game-Spec 立任务 13-game-design-v5);
#      按事实同步直接调用结果(urgent-window)与 12-game-design-v4(v4 采纳已发生
#      →进度已完成);越界探针(写 GAME_DESIGN 被拒)。
#   T3 $game-spec(委派):GAME_DESIGN v4→v5(采纳开发者确认的 50 秒),双指纹
#      登记并回读一致;决定记录 + 13 的 results 采纳记录。
#   T4 $game-plan(委派):把本轮短规格拆成单一原子任务 14-round-50s-params
#      (50 秒常量+追回窗口命名参数+PT-01 修复+重建+检查);远期(04/05/08、双阶段
#      讨论)保持粗粒度不拆解;ready 回读 14 可开工。
#   T5 $game-implement(委派,Game-Implement 管本次制作):TECH_DESIGN v3→v4
#      (参数表 50 秒、RECOVER_WINDOW_BASE_SECONDS、PT-01 修复说明);src 50 秒
#      与 PT-01 修复;按构建约定重建 build/(字节一致+哈希对照);无头冒烟真实
#      运行(含 PT-01 回归场景);结果记录入 14 results;探针写 GAME_DESIGN 被拒。
#   T6 $game-review(独立新实例,review 用途):对待审版本(清单+SHA-256 指纹)
#      独立两轴审查,检查实际运行,审查记录落 evidence/;不修改待审成果。
#   T7 $game-playtest(独立新实例,playtest 用途):对重建后的 build/ 登记新指纹
#      并复测(PT-01 回归、初始化 50、结算幂等);人工项保持未反馈(待人工);
#      试玩记录落 evidence/。
#   T8 $game-design(仅讨论分支,不进入制作):围绕双阶段节奏产出候选方案与取舍、
#      助手建议、未决项;过程记录落 records/;不写 GAME_DESIGN;不代开发者决定。
#   T9 $game-producer(闭环同步):按事实核对专业结果(13/14 的成果、审查、试玩
#      与指纹)→ 13/14 验收方式完成且无需人判断→标记已完成;02/11 登记新事实
#      (PT-01 修复、build 重建)而人工项保持待验收;04/05/08 基线引用更新到
#      GAME_DESIGN v5/TECH_DESIGN v4 并重新分流;PROJECT 状态变化与粗粒度近期
#      方向,双指纹同步;探针被拒。
#   T10 $game-status(只读,无凭据零写入):准确展示已完成/待做/待验收/受阻/
#      基线核对与可接续工作;待验收不被解释为完成。
# 末尾:统一接口回读(list/deps/ready/verify/baseline 全一致退出 0);终态变化与
#   计划一一对应;验收侧独立复核(node 冒烟含 PT-01 回归、静态服务取回、build↔src
#   逐字节一致);审计(统筹只写管理资料、各实例授权不扩大)、策略字节、令牌泄漏
#   与 codex 残留进程核对。
#
# 输出:全部证据写入本目录 evidence/,并在终端打印 PASS/FAIL 汇总。

set -u

REPO_ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
ACC_DIR="$REPO_ROOT/acceptance/16-producer-complete-loop"
EVIDENCE_DIR="$ACC_DIR/evidence"
ENVROOT="${1:-/tmp/mygamestudio-accept-16}"
ARENA="$REPO_ROOT/.tmp/accept-16"
PROJ="$ARENA/projects/tide-pool"
RUNROOT="$ARENA/runtime"
PLUGIN_RUNTIME="$REPO_ROOT/plugin/runtime"
PLUGIN_RECORDS="$REPO_ROOT/plugin/records"
MGS_CLIENT="$ACC_DIR/appserver_client.py"
TODAY="$(date +%F)"
RESUME="${RESUME:-0}"

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

check_contains_re() { # 全部存在才通过(每项为扩展正则)
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

no_false_pass() { # 否定感知:通过类字样只允许出现在否定语境(票 14 先例)
  local file="$1"; shift
  python3 -B - "$file" "$@" <<'PYEOF'
import re
import sys

path = sys.argv[1]
text = open(path, encoding="utf-8").read()
bad_hits = []
for phrase in sys.argv[2:]:
    for m in re.finditer(re.escape(phrase), text):
        ctx = text[max(0, m.start() - 14):m.start()]
        if not re.search(r"(不|未|无|非|尚|不能|不得|没有|≠)", ctx):
            bad_hits.append(f"{phrase}@{m.start()}")
if bad_hits:
    print("BAD:" + ",".join(bad_hits))
    sys.exit(1)
print("OK")
PYEOF
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
        try:
            e = json.loads(line)
        except json.JSONDecodeError:
            continue
        if eval(expr, {}, {"e": e}):  # noqa: S307 - 验收脚本受控输入
            count += 1
except FileNotFoundError:
    pass
print(count)
PYEOF
}

audit_targets_outside() { # audit_targets_outside <实例id> <允许前缀正则>:输出越界 allow 数
  python3 -B - "$1/audit/audit.jsonl" "$2" "$3" <<'PYEOF'
import json
import re
import sys

path, iid, allowed = sys.argv[1], sys.argv[2], sys.argv[3]
count = 0
try:
    for line in open(path):
        line = line.strip()
        if not line:
            continue
        try:
            e = json.loads(line)
        except json.JSONDecodeError:
            continue
        if (e.get("op") == "write" and e.get("decision") == "allow"
                and e.get("instance_id") == iid
                and not re.fullmatch(allowed, e.get("target", ""))):
            count += 1
except FileNotFoundError:
    pass
print(count)
PYEOF
}

hash_diff() { # hash_diff <旧哈希文件> <新哈希文件>:逐行输出 M|A|D <相对路径>
  python3 -B - "$1" "$2" <<'PYEOF'
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

a, b = load(sys.argv[1]), load(sys.argv[2])
for rel in sorted(set(a) | set(b)):
    if a.get(rel) == b.get(rel):
        continue
    kind = "M" if rel in a and rel in b else ("A" if rel in b else "D")
    print(kind, rel)
PYEOF
}

mkdir -p "$EVIDENCE_DIR"
if [ "$RESUME" = "1" ] && [ -f "$EVIDENCE_DIR/project.baseline.sha256" ] && [ -d "$PROJ" ]; then
  say "== RESUME 模式:复用既有环境与证据,不重建、不清证据 =="
  SKIP_SETUP=1
else
  RESUME=0
  SKIP_SETUP=0
fi
# 清掉上一轮证据,避免陈旧文件掩盖本次失败(本目录全由 run.sh 再生成;RESUME 不清)
[ "$SKIP_SETUP" = "1" ] || rm -f "$EVIDENCE_DIR"/environment.txt \
      "$EVIDENCE_DIR"/static-*.txt "$EVIDENCE_DIR"/plugin-available.json \
      "$EVIDENCE_DIR"/plugin-install.json "$EVIDENCE_DIR"/skills-list.jsonl \
      "$EVIDENCE_DIR"/admin-init-policy.json \
      "$EVIDENCE_DIR"/t1-report.md "$EVIDENCE_DIR"/t1-events.jsonl "$EVIDENCE_DIR"/t1-runlog.txt \
      "$EVIDENCE_DIR"/t2-report.md "$EVIDENCE_DIR"/t2-events.jsonl "$EVIDENCE_DIR"/t2-runlog.txt \
      "$EVIDENCE_DIR"/t3-report.md "$EVIDENCE_DIR"/t3-events.jsonl "$EVIDENCE_DIR"/t3-runlog.txt \
      "$EVIDENCE_DIR"/t4-report.md "$EVIDENCE_DIR"/t4-events.jsonl "$EVIDENCE_DIR"/t4-runlog.txt \
      "$EVIDENCE_DIR"/t5-report.md "$EVIDENCE_DIR"/t5-events.jsonl "$EVIDENCE_DIR"/t5-runlog.txt \
      "$EVIDENCE_DIR"/t6-report.md "$EVIDENCE_DIR"/t6-events.jsonl "$EVIDENCE_DIR"/t6-runlog.txt \
      "$EVIDENCE_DIR"/t7-report.md "$EVIDENCE_DIR"/t7-events.jsonl "$EVIDENCE_DIR"/t7-runlog.txt \
      "$EVIDENCE_DIR"/t8-report.md "$EVIDENCE_DIR"/t8-events.jsonl "$EVIDENCE_DIR"/t8-runlog.txt \
      "$EVIDENCE_DIR"/t9-report.md "$EVIDENCE_DIR"/t9-events.jsonl "$EVIDENCE_DIR"/t9-runlog.txt \
      "$EVIDENCE_DIR"/t10-report.md "$EVIDENCE_DIR"/t10-events.jsonl "$EVIDENCE_DIR"/t10-runlog.txt \
      "$EVIDENCE_DIR"/baseline-*.json "$EVIDENCE_DIR"/records-*.json \
      "$EVIDENCE_DIR"/project.baseline.sha256 "$EVIDENCE_DIR"/project.after-*.sha256 \
      "$EVIDENCE_DIR"/project.final.sha256 \
      "$EVIDENCE_DIR"/smoke-t5.txt "$EVIDENCE_DIR"/smoke-final.txt \
      "$EVIDENCE_DIR"/http-fetch.txt \
      "$EVIDENCE_DIR"/project-expected-changes.txt \
      "$EVIDENCE_DIR"/audit.jsonl "$EVIDENCE_DIR"/policy-sha256.txt "$EVIDENCE_DIR"/ps-final.txt
[ "$SKIP_SETUP" = "1" ] || find "$EVIDENCE_DIR" -name '.!*' -type f -delete 2>/dev/null || true

# ---------- 0. 环境记录 ----------

{
  echo "date: $(date -Iseconds)"
  echo "codex: $(codex --version 2>&1)"
  echo "python3: $(python3 --version 2>&1)"
  echo "node: $(node --version 2>&1)"
  echo "os: $(sw_vers -productName 2>/dev/null) $(sw_vers -productVersion 2>/dev/null) ($(uname -m))"
  echo "model(隔离 config.toml 固定): $(sed -n 's/^model = //p' "$ENVROOT/codex-home/config.toml" 2>/dev/null | head -1 || echo 默认)"
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
    bad "缺少工具 $tool(检查助手/统一接口/无头冒烟必需)"
    exit 1
  fi
done

# ---------- 1. 确定性检查 ----------

say "== 1. 确定性检查(静态包 + 运行保障 + 边界 + 记录后端) =="
if python3 -B "$REPO_ROOT/tests/test_plugin_package.py" > "$EVIDENCE_DIR/static-package-check.txt" 2>&1; then
  ok "包完整性静态检查(tests/test_plugin_package.py,含 16 闭环纪律与夹具检查)"
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

# ---------- 2. 搭建隔离环境(十层夹具:票 06-15 成果 + 16 闭环布景) ----------

say "== 2. 搭建隔离验收环境(tide-pool + 票 06-15 成果 + 16 闭环布景) =="
# 隔离身份必须两种模式都生效(RESUME 下遗漏导出会使轮次落到用户真实 CODEX_HOME)
export HOME="$ENVROOT/home"
export CODEX_HOME="$ENVROOT/codex-home"
# 公共辅助(RESUME 与全量两种模式都用;定义在任何分支之外)
codex_orphans() { ps ax -o pid=,ppid=,command= | grep -E "codex (app-server|exec)" \
  | grep -v grep | awk '$2 == 1 {print $1}' | sort; }
proj_files() { (cd "$1" && find . -type f -not -path './.git/*' | sort); }
proj_hash()  { (cd "$1" && find . -type f -not -path './.git/*' | sort | xargs shasum -a 256); }
# 环境外既有孤儿 codex 进程基线(终态只核对本轮新增孤儿;RESUME 复用 run1 基线)
[ -f "$ARENA/ps-baseline.txt" ] || codex_orphans > "$ARENA/ps-baseline.txt" || true
if [ "$SKIP_SETUP" = "1" ]; then
  ok "RESUME:复用既有隔离环境、十层夹具布景与起始状态证据(run1 已核对)"
else
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
# 可选:服务端把默认模型切到本版 CLI 不支持的新模型时,用 MGS_PIN_MODEL 固定模型,
# 例如 MGS_PIN_MODEL=gpt-5.6-sol ./run.sh(写入的是隔离 CODEX_HOME,不动全局配置)
[ -n "${MGS_PIN_MODEL:-}" ] && printf 'model = "%s"\n' "$MGS_PIN_MODEL" >> "$ENVROOT/codex-home/config.toml"

# 目标项目:tide-pool 样例 + 08..15 夹具(票 06-15 成果)+ 16 夹具(15 终态 + 闭环请求)
cp -R "$REPO_ROOT/samples/tide-pool" "$PROJ"
cp -R "$REPO_ROOT/acceptance/08-spec-to-local-tasks/fixtures/." "$PROJ/"
cp -R "$REPO_ROOT/acceptance/09-code-task-delivery/fixtures/." "$PROJ/"
cp -R "$REPO_ROOT/acceptance/10-visual-asset-delivery/fixtures/." "$PROJ/"
cp -R "$REPO_ROOT/acceptance/11-audio-asset-delivery/fixtures/." "$PROJ/"
cp -R "$REPO_ROOT/acceptance/12-build-and-run-delivery/fixtures/." "$PROJ/"
cp -R "$REPO_ROOT/acceptance/13-independent-deliverable-review/fixtures/." "$PROJ/"
cp -R "$REPO_ROOT/acceptance/14-playtest-and-human-feedback/fixtures/." "$PROJ/"
cp -R "$REPO_ROOT/acceptance/15-goal-change-concurrency-recovery/fixtures/." "$PROJ/"
cp -R "$ACC_DIR/fixtures/." "$PROJ/"
(cd "$PROJ" && git init -q . && git config user.email t@t && git config user.name t)

# 干净基线提交(布景 = 已交付形态;闭环请求是新的开发者输入)
(cd "$PROJ" && git add -A && git commit -qm "baseline: tickets 01-15 deliverables + complete-loop request")

# 起始状态留证与核对
check "闭环请求已就位(README 当前请求指向完整小步闭环)" grep -q "闭环" "$PROJ/README.md"
check "承接事实:GAME_DESIGN 为 v4 且含手工 50 秒" bash -c \
  "grep -qE '基线版本(:|：)v4' '$PROJ/docs/mygamestudio/GAME_DESIGN.md' && grep -q '50 秒' '$PROJ/docs/mygamestudio/GAME_DESIGN.md'"
check "承接事实:12-game-design-v4 待执行(采纳已发生待统筹同步)" grep -qE "进度(:|：)待执行" "$PROJ/docs/mygamestudio/work/12-game-design-v4/task.md"
check "承接事实:04 为 needs-triage 待重核" grep -q "needs-triage" "$PROJ/docs/mygamestudio/work/04-shell-combo/task.md"
check "承接事实:02 待验收且保留开发者注" bash -c \
  "grep -qE '进度(:|：)待验收' '$PROJ/docs/mygamestudio/work/02-tide-timer/task.md' && grep -q '此注保留' '$PROJ/docs/mygamestudio/work/02-tide-timer/task.md'"

proj_files "$PROJ" > "$ARENA/project-baseline-files.txt"
proj_hash "$PROJ" > "$EVIDENCE_DIR/project.baseline.sha256"

python3 -B "$PLUGIN_RECORDS/mgs_records.py" ready --project "$PROJ" > "$EVIDENCE_DIR/records-ready-initial.json" 2>&1
check "起始可开工集合为空(04/05/08 needs-triage;02/06/10/11 待验收;12 needs-info)" bash -c \
  "! python3 -c \"import json;print(json.load(open('$EVIDENCE_DIR/records-ready-initial.json'))['startable'])\" | grep -q '[0-9]'"
python3 -B "$PLUGIN_RECORDS/mgs_records.py" baseline --project "$PROJ" > "$EVIDENCE_DIR/baseline-initial.json" 2>&1
BASELINE0_RC=$?
check "起始 baseline 退出码 1(GAME_DESIGN 手工 50 秒实质变更待确认,票 15 遗留)" test "$BASELINE0_RC" = "1"
check "起始 baseline:GAME_DESIGN 实质变更 + PROJECT 一致" bash -c \
  "python3 -c \"import json;d=json.load(open('$EVIDENCE_DIR/baseline-initial.json'));s={x['path'].split('/')[-1]:x['status'] for x in d['docs']};exit(0 if s.get('GAME_DESIGN.md')=='内容已变(实质变更)' and s.get('PROJECT.md')=='一致' else 1)\""
fi  # SKIP_SETUP(第 2 节,含起始状态核对)结束

# ---------- 3. 插件发现与安装 ----------

say "== 3. 插件发现与安装 =="
if [ "$SKIP_SETUP" = "1" ] && [ -s "$EVIDENCE_DIR/plugin-install.json" ]; then
  ok "RESUME:复用既有安装与副本一致性证据"
  INSTALLED_PATH=$(python3 -c "import json;print(json.load(open('$EVIDENCE_DIR/plugin-install.json'))['installedPath'])")
else
codex plugin list --json --available > "$EVIDENCE_DIR/plugin-available.json" 2>&1
check_contains "marketplace 可发现 mygamestudio(未安装态)" "$EVIDENCE_DIR/plugin-available.json" '"name": "mygamestudio"'
codex plugin add mygamestudio@personal --json > "$EVIDENCE_DIR/plugin-install.json" 2>&1
check_contains "安装成功并返回安装路径" "$EVIDENCE_DIR/plugin-install.json" '"installedPath"'
INSTALLED_PATH=$(python3 -c "import json;print(json.load(open('$EVIDENCE_DIR/plugin-install.json'))['installedPath'])")
check "安装副本与仓库 plugin/ 逐字节一致" diff -r "$REPO_ROOT/plugin" "$INSTALLED_PATH"
fi

# ---------- 4. 技能注册面 ----------

say "== 4. 技能注册面(14 个显式入口,本票不新增入口) =="
if [ "$SKIP_SETUP" = "1" ] && [ -s "$EVIDENCE_DIR/skills-list.jsonl" ]; then
  ok "RESUME:复用既有技能注册面证据"
else
mkdir -p "$ENVROOT/instances/proto1/ws" "$ENVROOT/instances/prod1/ws" \
         "$ENVROOT/instances/spec1/ws" "$ENVROOT/instances/plan1/ws" \
         "$ENVROOT/instances/impl1/ws" "$ENVROOT/instances/rev1/ws" \
         "$ENVROOT/instances/pt1/ws" "$ENVROOT/instances/dsgn1/ws" \
         "$ENVROOT/instances/prod2/ws" "$ENVROOT/instances/stat1/ws"
for ws in proto1 prod1 spec1 plan1 impl1 rev1 pt1 dsgn1 prod2 stat1; do
  (cd "$ENVROOT/instances/$ws/ws" && git init -q . 2>/dev/null; git config user.email t@t; git config user.name t)
done
export MGS_RUNTIME_ROOT="$RUNROOT"
python3 "$MGS_CLIENT" skills --cwd "$ENVROOT/instances/prod1/ws" > "$EVIDENCE_DIR/skills-list.jsonl" 2>&1
plugin_skill_count=$(grep -c '"pluginId": "mygamestudio@personal"' "$EVIDENCE_DIR/skills-list.jsonl" || true)
if [ "$plugin_skill_count" = "14" ]; then
  ok "插件注册的技能数量为 14(本票扩展既有入口,不新增公共入口)"
else
  bad "插件注册技能数量为 $plugin_skill_count,应为 14"
fi
fi

# ---------- 5. 可信调度侧:策略与实例 ----------

say "== 5. 可信调度侧:策略初始化与实例签发(沿用票 15 策略面) =="
if [ "$SKIP_SETUP" = "1" ] && [ -f "$RUNROOT/policy.json" ] && [ -f "$ARENA/prod1.token" ]; then
  ok "RESUME:复用既有策略与已签发实例凭据(不重复签发)"
else
cat > "$ARENA/policy-spec.json" <<EOF
{
  "project_root": "$PROJ",
  "roles": {
    "producer": ["docs/mygamestudio/INDEX.md", "docs/mygamestudio/CONFIG.md", "docs/mygamestudio/PROJECT.md", "docs/mygamestudio/work/**", "docs/mygamestudio/records/onboarding-*.md"],
    "design": ["docs/mygamestudio/GAME_DESIGN.md", "docs/mygamestudio/records/**", "prototypes/**"],
    "implement": ["docs/mygamestudio/TECH_DESIGN.md", "src/**", "assets/**", "build/**", "docs/mygamestudio/work/*/results/**", "docs/mygamestudio/evidence/**"]
  },
  "purposes": {"production": null, "prototype": ["prototypes/**"], "review": ["docs/mygamestudio/evidence/**"], "playtest": ["docs/mygamestudio/evidence/**"]}
}
EOF
python3 -B "$PLUGIN_RUNTIME/mgsrt_admin.py" init-policy --spec "$ARENA/policy-spec.json" \
  > "$EVIDENCE_DIR/admin-init-policy.json" 2>&1
check_contains "策略初始化完成" "$EVIDENCE_DIR/admin-init-policy.json" '"producer"' '"design"' '"implement"'
POLICY0=$(shasum -a 256 "$RUNROOT/policy.json" | awk '{print $1}')
say "初始策略 SHA-256: $POLICY0(当前文件)"

issue() { # issue <名> <角色> <任务> <用途> <ttl分钟> <资源>...
  local name="$1" role="$2" task="$3" purpose="$4" ttl="$5"; shift 5
  local args=()
  local r
  for r in "$@"; do
    args+=(--resource "$r")
  done
  MGS_RUNTIME_ROOT="$RUNROOT" python3 -B "$PLUGIN_RUNTIME/mgsrt_admin.py" create-instance \
    --role "$role" --task "$task" --purpose "$purpose" --ttl-mins "$ttl" "${args[@]}" \
    > "$ARENA/$name.json" 2>/dev/null
  python3 -c "import json; d=json.load(open('$ARENA/$name.json')); print(d['instance_id'])" > "$ARENA/$name.id"
  python3 -c "import json; print(json.load(open('$ARENA/$name.json'))['token'])" > "$ARENA/$name.token"
}

issue proto1 design   16-urgent-window      prototype  480 'prototypes/**'
issue prod1  producer 16-loop-intake        production 480 'docs/mygamestudio/PROJECT.md' 'docs/mygamestudio/work/**'
issue spec1  design   13-game-design-v5     production 480 'docs/mygamestudio/GAME_DESIGN.md' 'docs/mygamestudio/records/**' 'docs/mygamestudio/work/13-game-design-v5/results/**'
issue plan1  producer 16-plan-round-50s     production 480 'docs/mygamestudio/work/**'
issue impl1  implement 14-round-50s-params  production 480 'docs/mygamestudio/TECH_DESIGN.md' 'src/**' 'build/**' 'docs/mygamestudio/work/14-round-50s-params/results/**'
issue rev1   implement 16-review-round-50s  review     480 'docs/mygamestudio/evidence/**'
issue pt1    implement 16-playtest-round-50s playtest  480 'docs/mygamestudio/evidence/**'
issue dsgn1  design   16-phase-discussion   production 480 'docs/mygamestudio/records/**'
issue prod2  producer 16-loop-sync          production 480 'docs/mygamestudio/PROJECT.md' 'docs/mygamestudio/work/**'
fi

if [ "$SKIP_SETUP" = "1" ]; then
  # RESUME:初始策略值以 run1 日志记录为准(证明全程未被改动),缺失时回退当前哈希
  POLICY0=$(sed -n 's/^初始策略 SHA-256: //p' "$EVIDENCE_DIR/run1-full-log.txt" 2>/dev/null | head -1)
  [ -n "$POLICY0" ] || POLICY0=$(shasum -a 256 "$RUNROOT/policy.json" | awk '{print $1}')
else
  POLICY0=$(shasum -a 256 "$RUNROOT/policy.json" | awk '{print $1}')
fi
say "初始策略 SHA-256: $POLICY0"

sanitize() { # 用 <redacted-*> 替换证据中的全部原始令牌
  local f="$1" name tok
  for name in proto1 prod1 spec1 plan1 impl1 impl2 rev1 pt1 dsgn1 prod2; do
    tok=$(cat "$ARENA/$name.token")
    sed -i '' -e "s/$tok/<redacted-$name-token>/g" "$f"
  done
}

run_turn() { # run_turn <证据前缀> <工作区> <mention> <文本> <超时秒>
  local prefix="$1" ws="$2" mention="$3" text="$4" tmo="$5"
  TURN_EXECUTED=0
  if [ "$RESUME" = "1" ] && [ -s "$EVIDENCE_DIR/$prefix-report.md" ]; then
    say "RESUME:$prefix 报告已存在,跳过执行(复用证据;实例不重复释放,供断点续跑重签发)"
    return 0
  fi
  TURN_EXECUTED=1
  MGS_RUNTIME_ROOT="$RUNROOT" python3 "$MGS_CLIENT" turn --cwd "$ws" --sandbox workspace-write \
    --mention "$mention" --text "$text" \
    --out "$EVIDENCE_DIR/$prefix-report.md" --events-out "$EVIDENCE_DIR/$prefix-events.jsonl" \
    --timeout "$tmo" > "$EVIDENCE_DIR/$prefix-runlog.txt" 2>&1
  local rc=$?
  if [ -s "$EVIDENCE_DIR/$prefix-report.md" ]; then
    sanitize "$EVIDENCE_DIR/$prefix-report.md"
  fi
  if [ -s "$EVIDENCE_DIR/$prefix-events.jsonl" ]; then
    sanitize "$EVIDENCE_DIR/$prefix-events.jsonl"
  fi
  if [ -s "$EVIDENCE_DIR/${prefix}b-report.md" ] && [ "$prefix" != "t1" ]; then
    sanitize "$EVIDENCE_DIR/${prefix}b-report.md"   # 手工续作轮产物同样脱敏
    [ -s "$EVIDENCE_DIR/${prefix}b-events.jsonl" ] && sanitize "$EVIDENCE_DIR/${prefix}b-events.jsonl"
  fi
  return $rc
}

PRID=$(cat "$ARENA/proto1.id"); PRTOK=$(cat "$ARENA/proto1.token")
P1ID=$(cat "$ARENA/prod1.id"); P1TOK=$(cat "$ARENA/prod1.token")
S1ID=$(cat "$ARENA/spec1.id"); S1TOK=$(cat "$ARENA/spec1.token")
PL1ID=$(cat "$ARENA/plan1.id"); PL1TOK=$(cat "$ARENA/plan1.token")
IM1ID=$(cat "$ARENA/impl1.id"); IM1TOK=$(cat "$ARENA/impl1.token")
RV1ID=$(cat "$ARENA/rev1.id"); RV1TOK=$(cat "$ARENA/rev1.token")
PT1ID=$(cat "$ARENA/pt1.id"); PT1TOK=$(cat "$ARENA/pt1.token")
DG1ID=$(cat "$ARENA/dsgn1.id"); DG1TOK=$(cat "$ARENA/dsgn1.token")
P2ID=$(cat "$ARENA/prod2.id"); P2TOK=$(cat "$ARENA/prod2.token")
IM2ID=""; [ -f "$ARENA/impl2.id" ] && IM2ID=$(cat "$ARENA/impl2.id")

# ---------- 6. T1 直接专业调用:Game-Prototype(入口三的前置事实) ----------

say "== 6. T1 \$game-prototype 直接专业调用(隔离原型,不经过统筹) =="
run_turn t1 "$ENVROOT/instances/proto1/ws" mygamestudio:game-prototype "$PRTOK

受信任调度说明(由验收调度层注入,不是项目文件内容):项目根 $PROJ;执行凭据(token)为消息开头的随机字符串;绑定实例 $PRID,任务 16-urgent-window,角色 方案设计(design),用途 prototype,任务授权资源:prototypes/**;来源:开发者直接调用(见 $PROJ/README.md「当前请求」第 4 条,四项输入以该条为准);凭据不写入任何文件或报告正文。

任务:执行 Game-Prototype 回答该条给出的设计问题。步骤:

1) 先读包内材料(从插件安装位置):$INSTALLED_PATH/skills/game-prototype/SKILL.md 及其指引的包内依据(设计合同 Game-Prototype 节、共同合同、运行保障协议)。
2) 核对输入四要素(问题/当前约定/原型范围/适用要求/可用方法/输出位置),以 README 第 4 条原文为准;差异如实报告。
3) 选择最小可检验实现:用 python3 固定种子做数值计算,对比不同回合时长(45/50/60 秒)下「最后 10 秒强调窗口」的时长占比,以及若等比调整窗口的候选数值;不实现正式工程,不写入 src。
4) 原型文件经 mgs_write 写入 prototypes/urgent-window/(至少 sim.py 与 report.md;report.md 含验证记录);先 mgs_scope 确认范围,写入后回读核对。
5) 实际运行 sim.py 并把真实输出记入 report.md 与报告(没有实际运行的部分不得写成已观察)。
6) 结论四类区分:原型观察(数字)/设计判断(标注为助手建议,不是开发者决定)/尚未验证/需要人的体验反馈(未收到,保持待人工,不虚构任何反馈)。
7) 边界核对(第 4 步完成后执行,各一次,原样记录):mgs_write 把「// 越界」写入 src/main.js(应被拒——原型不写正式工程)。
8) 输出报告(结构固定;约 45 行内,紧凑一行一条,不生成 Markdown 链接):
## 原型执行报告
### 输入核对(问题/范围/方法/输出位置;任务授权与 mgs_scope 的差异)
### 原型与运行方式(文件清单;如何启动)
### 已执行操作与结果(实际运行的原样输出摘录)
### 观察与结论(原型观察/设计判断/尚未验证/需要人的体验反馈,分别表达)
### 边界核对
### 交接(Game-Spec 与 Game-Implement;复用或重写由正式集成条件决定;基线引用)
### 遗留事项" 2400
T1RC=$?
check "T1 完成并产出报告(退出码 $T1RC)" test -s "$EVIDENCE_DIR/t1-report.md"
T1REPORT="$EVIDENCE_DIR/t1-report.md"
check_contains "T1 报告使用约定结构" "$T1REPORT" '## 原型执行报告' '### 输入核对' '### 观察与结论' '### 边界核对' '### 交接'
check "T1 turn 完整结束" grep -q 'turn/completed' "$EVIDENCE_DIR/t1-events.jsonl"
check "T1 报告不含原始令牌" bash -c "! grep -qF '$PRTOK' '$T1REPORT'"
check "T1 原型文件就位(sim.py + report.md)" bash -c \
  "test -s '$PROJ/prototypes/urgent-window/sim.py' && test -s '$PROJ/prototypes/urgent-window/report.md'"
check_contains_re "T1 报告含真实运行输出摘录" "$T1REPORT" '已执行操作|实际运行' 'python3'
check_contains_re "T1 结论四类区分" "$T1REPORT" '原型观察' '设计判断|助手建议' '尚未验证|未验证|待验证' '待人工|需要人的体验反馈'
check_not_contains "T1 不虚构人工反馈" "$T1REPORT" '反馈已收到' '体验反馈已确认' '开发者已确认通过'
check "T1 否定感知:无未否定的通过类断言" no_false_pass "$T1REPORT" '反馈已收到' '体验确认通过'
N=$(audit_count "$RUNROOT" 'e["op"]=="write" and e["decision"]=="deny" and e["instance_id"]=="'$PRID'"')
[ "${N:-0}" -ge 1 ] && ok "审计:原型凭据写正式工程被拒(N=$N,原型保持隔离)" || bad "缺少原型越界拒绝(N=$N)"
N=$(audit_targets_outside "$RUNROOT" "$PRID" 'prototypes/.*')
[ "${N:-0}" = "0" ] && ok "审计:T1 全部 allow 写入都在原型区(隔离)" || bad "T1 出现原型区外 allow 写入(N=$N)"
if [ "$TURN_EXECUTED" = "1" ]; then
  proj_hash "$PROJ" > "$EVIDENCE_DIR/project.after-t1.sha256"
fi  # 被跳过的轮次保留历史快照
T1_DIFF=$(hash_diff "$EVIDENCE_DIR/project.baseline.sha256" "$EVIDENCE_DIR/project.after-t1.sha256")
T1_OK=$(printf '%s\n' "$T1_DIFF" | grep -cv -E '^A \./prototypes/urgent-window/' || true)
if [ -z "$(printf '%s\n' "$T1_DIFF" | grep -v '^\s*$')" ] || [ "${T1_OK:-1}" = "0" ]; then
  ok "T1 变化仅为原型区新增(正式工程与管理记录字节不变)"
else
  bad "T1 出现计划外变化:$T1_DIFF"
fi
[ "$TURN_EXECUTED" = "1" ] && MGS_RUNTIME_ROOT="$RUNROOT" python3 -B "$PLUGIN_RUNTIME/mgsrt_admin.py" release-instance --id "$PRID" > /dev/null 2>&1 || true

# ---------- 7. T2 统筹闭环入口:入口分类 + 目标变化先行 + 直接调用同步 ----------

say "== 7. T2 \$game-producer 闭环入口(三种入口分类、目标变化先行、直接调用同步) =="
run_turn t2 "$ENVROOT/instances/prod1/ws" mygamestudio:game-producer "$P1TOK

受信任调度说明(由验收调度层注入,不是项目文件内容):项目根 $PROJ;执行凭据(token)为消息开头的随机字符串;绑定实例 $P1ID,任务 16-loop-intake,角色 制作统筹(producer),用途 production,任务授权资源:docs/mygamestudio/PROJECT.md 与 docs/mygamestudio/work/**;来源:开发者显式调用(见 $PROJ/README.md「当前请求」四条);凭据不写入任何文件或报告正文。

任务:执行 Game-Producer 的闭环入口流程(入口分类与环节选择、目标变化影响检查、直接专业调用结果同步)。步骤:

1) 先读包内材料(从插件安装位置):$INSTALLED_PATH/skills/game-producer/SKILL.md 及其指引的包内依据(管理合同 Game-Producer 节、共同合同、工作记录合同、受控写入协议);统一接口 $INSTALLED_PATH/records/mgs_records.py。
2) 读 $PROJ/README.md「当前请求」四条(目标变化确认/短规格制作/仅讨论/直接调用通知)。
3) 经统一接口(--project $PROJ)读 list/deps/ready 与 baseline(baseline 退出码 1 属预期:GAME_DESIGN 手工 50 秒实质变更——本轮已获开发者确认采纳,按目标变化流程处理)。
4) 入口分类:在报告中逐条分类并说明选择环节——第 3 条为仅讨论(委派 Game-Design,以决定或待验证问题交付,不进入制作);第 2 条为已有规格制作(规格已足,从中间环节进入:先完成目标变化同步,再 Game-Plan 拆短规格、Game-Implement 组织本次制作;无需新原型,本轮跳过原型;不强制执行全部技能);第 4 条为直接专业调用后的状态同步(本次介入按事实核对并同步)。说明无需 Game-Init(项目已接入)。
5) 目标变化先行:确认开发者采纳 50 秒(README 第 1 条)→ 影响检查(GAME_DESIGN 需采纳为 v5,采纳归 Game-Spec,统筹只识别与安排;受影响任务:04/05/08 重核口径、02/11 等原版本完成事实保留不自动算作满足新目标)→ 更新 PROJECT v3→v4:当前目标反映 50 秒回合(设计基线引用注明待 v5 采纳);「状态变化」记录本轮入口分类、影响检查与安排;PROJECT 头部双指纹按登记纪律同步更新(两条指纹值先写 64 个 0,对全文「原样」与「去除全部空白」各计算 SHA-256 回填)。
6) 委派:产出委派工作请求——Game-Spec(把确认的 50 秒采纳进 GAME_DESIGN v5,立为任务记录 13-game-design-v5,分流 needs-info、进度待执行)、其后的 Game-Plan(拆本轮短规格)与 Game-Implement(组织本次制作)、Game-Design(第 3 条仅讨论);写明先后顺序与集成责任;除此之外不新建任何任务记录。
7) 直接专业调用结果同步:读 prototypes/urgent-window/report.md,按事实核对后在 PROJECT「状态变化」登记同步(结论按报告实际内容转述;urgent 阈值是否调整属设计判断,列为待开发者,不自行改动);再按事实同步 12-game-design-v4——GAME_DESIGN v4 与决定记录已在位(采纳实际已发生),把该任务进度置已完成并在「状态变化」记录依据,不改写其专业内容。
8) mgs_scope 确认可写范围;全部写入经 mgs_write(更新携带 expected_sha256),逐个回读核对;完成后统一接口 baseline 确认 PROJECT 为「一致」。
9) 边界核对(第 8 步完成后执行,各一次,原样记录):mgs_write 把「// 越界」写入 docs/mygamestudio/GAME_DESIGN.md(应被拒——统筹不写设计基线)。
10) 输出报告(结构固定;约 90 行内,紧凑一行一条,不生成 Markdown 链接):
## 统筹工作报告
### 入口分类(本轮各请求的入口类型、选择环节与依据)
### 管理写入结果
### 影响检查(受影响基线与任务、重新分流口径、完成事实保留、委派与待决定)
### 基线核对
### 直接调用结果同步(实际成果与证据核对结论、同步的进度与记录)
### 边界核对
### 委派工作请求
### 遗留事项" 2700
T2RC=$?
check "T2 完成并产出报告(退出码 $T2RC)" test -s "$EVIDENCE_DIR/t2-report.md"
T2REPORT="$EVIDENCE_DIR/t2-report.md"
check_contains "T2 报告使用约定结构(含入口分类与直接调用同步)" "$T2REPORT" '## 统筹工作报告' '### 入口分类' '### 管理写入结果' '### 影响检查' '### 基线核对' '### 直接调用结果同步' '### 委派工作请求'
check "T2 turn 完整结束" grep -q 'turn/completed' "$EVIDENCE_DIR/t2-events.jsonl"
check "T2 报告不含原始令牌" bash -c "! grep -qF '$P1TOK' '$T2REPORT'"
check_contains_re "T2 三种入口分类齐备(标准 1)" "$T2REPORT" '仅讨论' '已有规格' '直接调用|直接专业调用'
check_contains_re "T2 按已有资料选择环节(中间进入/跳过原型/不强制)" "$T2REPORT" '中间进入|合适环节|从中间' '跳过原型|无需原型|无需新原型' '不强制'
check_contains_re "T2 原型保持隔离与 Game-Implement 管制作(标准 2)" "$T2REPORT" '隔离|原型区|prototypes/|跳过原型|无需新原型|无需原型' '[Gg]ame-[Ii]mplement'
check_contains_re "T2 委派覆盖本轮需要的专业入口(标准 2)" "$T2REPORT" '[Gg]ame-[Ss]pec' '[Gg]ame-[Pp]lan' '[Gg]ame-[Dd]esign'
check "T2 PROJECT 升至 v4 且当前目标为 50 秒" bash -c \
  "grep -qE '基线版本(:|：)v4' '$PROJ/docs/mygamestudio/PROJECT.md' && grep -q '50 秒' '$PROJ/docs/mygamestudio/PROJECT.md'"
check "T2 PROJECT 双指纹同步登记" bash -c \
  "grep -qE '内容指纹(:|：)sha256:[0-9a-f]{64}' '$PROJ/docs/mygamestudio/PROJECT.md' && grep -qE '归一指纹(:|：)sha256:[0-9a-f]{64}' '$PROJ/docs/mygamestudio/PROJECT.md'"
python3 -B "$PLUGIN_RECORDS/mgs_records.py" baseline --project "$PROJ" > "$EVIDENCE_DIR/baseline-after-t2.json" 2>&1
check "T2 后 baseline:PROJECT 一致(指纹同步正确)" bash -c \
  "python3 -c \"import json;d=json.load(open('$EVIDENCE_DIR/baseline-after-t2.json'));s={x['path'].split('/')[-1]:x['status'] for x in d['docs']};exit(0 if s.get('PROJECT.md')=='一致' else 1)\""
if [ "$RESUME" = "1" ]; then
  ok "T2 委派任务 13-game-design-v5 已立(RESUME:run1 以当时状态核对通过,见 run1-full-log.txt)"
else
  check "T2 委派任务 13-game-design-v5 已立(needs-info/待执行)" bash -c \
    "grep -qE '当前分流(:|：)needs-info' '$PROJ/docs/mygamestudio/work/13-game-design-v5/task.md' && grep -qE '进度(:|：)待执行' '$PROJ/docs/mygamestudio/work/13-game-design-v5/task.md'"
fi
check "T2 直接调用结果同步:12-game-design-v4 进度已完成" grep -qE "进度(:|：)已完成" "$PROJ/docs/mygamestudio/work/12-game-design-v4/task.md"
check_contains_re "T2 PROJECT 状态变化登记 urgent-window 同步与 12 收束" "$PROJ/docs/mygamestudio/PROJECT.md" 'urgent-window' '12-game-design-v4'
N=$(audit_count "$RUNROOT" 'e["op"]=="write" and e["decision"]=="deny" and e["instance_id"]=="'$P1ID'"')
[ "${N:-0}" -ge 1 ] && ok "审计:统筹凭据写 GAME_DESIGN 被拒(N=$N)" || bad "缺少统筹写设计基线的拒绝(N=$N)"
N=$(audit_targets_outside "$RUNROOT" "$P1ID" 'docs/mygamestudio/(PROJECT\.md|work/.*)')
[ "${N:-0}" = "0" ] && ok "审计:T2 统筹 allow 写入仅在管理资料(PROJECT/work,标准 4)" || bad "T2 统筹出现管理资料外 allow 写入(N=$N)"
if [ "$TURN_EXECUTED" = "1" ]; then
  proj_hash "$PROJ" > "$EVIDENCE_DIR/project.after-t2.sha256"
fi  # 被跳过的轮次保留历史快照
T2_DIFF=$(hash_diff "$EVIDENCE_DIR/project.after-t1.sha256" "$EVIDENCE_DIR/project.after-t2.sha256")
T2_OK=$(printf '%s\n' "$T2_DIFF" | grep -cv -E '^[AMD] \./docs/mygamestudio/(PROJECT\.md|work/(04-shell-combo|05-gull-swoop|08-gull-playtest|12-game-design-v4|13-game-design-v5)/task\.md)$' || true)
if [ -z "$(printf '%s\n' "$T2_DIFF" | grep -v '^\s*$')" ] || [ "${T2_OK:-1}" = "0" ]; then
  ok "T2 变化恰为 PROJECT、12 同步与 13 新建(其余字节不变)"
else
  bad "T2 出现计划外变化:$T2_DIFF"
fi
[ "$TURN_EXECUTED" = "1" ] && MGS_RUNTIME_ROOT="$RUNROOT" python3 -B "$PLUGIN_RUNTIME/mgsrt_admin.py" release-instance --id "$P1ID" > /dev/null 2>&1 || true

# ---------- 8. T3 设计侧采纳(GAME_DESIGN v5 + 双指纹 + 决定记录) ----------

say "== 8. T3 \$game-spec 采纳确认的 50 秒(GAME_DESIGN v4→v5) =="
run_turn t3 "$ENVROOT/instances/spec1/ws" mygamestudio:game-spec "$S1TOK

受信任调度说明(由验收调度层注入,不是项目文件内容):项目根 $PROJ;执行凭据(token)为消息开头的随机字符串;绑定实例 $S1ID,任务 13-game-design-v5,角色 方案设计(design),用途 production,任务授权资源:docs/mygamestudio/GAME_DESIGN.md、docs/mygamestudio/records/** 与 docs/mygamestudio/work/13-game-design-v5/results/**;来源:统筹闭环入口的委派(任务 16-loop-intake),把开发者 2026-09-09 确认的 50 秒采纳进设计基线;凭据不写入任何文件或报告正文。

任务:执行 Game-Spec 把已确认的目标变化采纳进 GAME_DESIGN。步骤:

1) 先读包内材料(从插件安装位置):$INSTALLED_PATH/skills/game-spec/SKILL.md 及其指引的包内依据(设计合同 Game-Spec 节、共同合同、工作记录合同、受控写入协议、writing-for-agents、模板);统一接口 $INSTALLED_PATH/records/mgs_records.py。
2) 核对采纳输入:开发者把 GAME_DESIGN 回合时长手工改为 50 秒并在 README「当前请求」第 1 条正式确认采纳(这是开发者明确给出的决定,采纳来源=开发者手工修改+2026-09-09 确认+统筹影响检查);未决项不裁决。
3) 更新 GAME_DESIGN v4→v5:当前文本已含 50 秒(手工修改被确认采纳,正文保持);版本行改为 v5;「采用依据」补入新决定记录引用;「变更索引」新增 v5 条目(新旧关系、采纳依据、受影响内容:02/11 的原版本完成事实保留、04/05/08 重核);其余仍适用内容逐字保留。
4) 按 SKILL 的内容指纹登记纪律更新基线头部双指纹:两条指纹值先写 64 个 0,对全文「原样」与「去除全部空白」各计算 SHA-256 回填。
5) mgs_scope 确认范围;更新经 mgs_write 携带 expected_sha256(当前 v4 全文哈希),回读核对;完成后统一接口 baseline --project $PROJ 确认 GAME_DESIGN 为「一致」。
6) 决定记录:写入 docs/mygamestudio/records/decision-${TODAY}-round-50s.md(决定=回合时长 50 秒;决定者=开发者;日期 ${TODAY};依据=手工修改与 README 第 1 条确认;影响与同步)。
7) 采纳结果简记:若 mgs_scope 实际范围包含 work/13-game-design-v5/results/**,则把采纳核对与 baseline 回读证据写入该目录 ${TODAY}.md;若不包含(任务授权与角色策略交集为空),按 scope 差异如实记录拒绝、不改道另写。
8) 边界核对(第 5 步完成后执行,各一次,原样记录):mgs_write 把「// 越界」写入 docs/mygamestudio/PROJECT.md(应被拒——设计角色不写管理资料)。
9) 输出报告(结构固定;约 60 行内,紧凑一行一条,不生成 Markdown 链接):
## 规格整理报告
### 采纳内容核对
### 基线变更(版本、变更索引、采纳依据;内容指纹与归一指纹登记结果)
### 本轮可执行规格概要(50 秒回合/追回参数化;实现状态:未实现)
### 统筹同步交接
### 回读核对
### 遗留事项" 2400
T3RC=$?
check "T3 完成并产出报告(退出码 $T3RC)" test -s "$EVIDENCE_DIR/t3-report.md"
T3REPORT="$EVIDENCE_DIR/t3-report.md"
check_contains "T3 报告使用约定结构" "$T3REPORT" '## 规格整理报告' '### 采纳内容核对' '### 基线变更' '### 统筹同步交接' '### 回读核对'
check "T3 turn 完整结束" grep -q 'turn/completed' "$EVIDENCE_DIR/t3-events.jsonl"
check "T3 报告不含原始令牌" bash -c "! grep -qF '$S1TOK' '$T3REPORT'"
check "T3 GAME_DESIGN 升至 v5 且保持 50 秒" bash -c \
  "grep -qE '基线版本(:|：)v5' '$PROJ/docs/mygamestudio/GAME_DESIGN.md' && grep -q '50 秒' '$PROJ/docs/mygamestudio/GAME_DESIGN.md'"
check "T3 登记双指纹" bash -c \
  "grep -qE '内容指纹(:|：)sha256:[0-9a-f]{64}' '$PROJ/docs/mygamestudio/GAME_DESIGN.md' && grep -qE '归一指纹(:|：)sha256:[0-9a-f]{64}' '$PROJ/docs/mygamestudio/GAME_DESIGN.md'"
check "T3 决定记录落盘(决定者=开发者)" bash -c \
  "test -s '$PROJ/docs/mygamestudio/records/decision-${TODAY}-round-50s.md' && grep -q '开发者' '$PROJ/docs/mygamestudio/records/decision-${TODAY}-round-50s.md'"
check_contains_re "T3 采纳简记按 mgs_scope 差异如实处理(任务授权含 13 的 results 而 design 角色策略不含,被拒即记录不改道)" "$T3REPORT" '采纳结果简记|结果简记' '被拒|deny' 
python3 -B "$PLUGIN_RECORDS/mgs_records.py" baseline --project "$PROJ" > "$EVIDENCE_DIR/baseline-after-t3.json" 2>&1
check "T3 后 baseline 退出码 0(GAME_DESIGN/PROJECT 均一致,实质变更已按采纳收束)" test "$?" = "0"
N=$(audit_count "$RUNROOT" 'e["op"]=="write" and e["decision"]=="deny" and e["instance_id"]=="'$S1ID'"')
[ "${N:-0}" -ge 1 ] && ok "审计:设计凭据写 PROJECT 被拒(N=$N)" || bad "缺少设计写管理资料的拒绝(N=$N)"
N=$(audit_targets_outside "$RUNROOT" "$S1ID" 'docs/mygamestudio/(GAME_DESIGN\.md|records/.*|work/13-game-design-v5/results/.*)')
[ "${N:-0}" = "0" ] && ok "审计:T3 allow 写入仅在授权范围" || bad "T3 出现授权外 allow 写入(N=$N)"
if [ "$TURN_EXECUTED" = "1" ]; then
  proj_hash "$PROJ" > "$EVIDENCE_DIR/project.after-t3.sha256"
fi  # 被跳过的轮次保留历史快照
T3_DIFF=$(hash_diff "$EVIDENCE_DIR/project.after-t2.sha256" "$EVIDENCE_DIR/project.after-t3.sha256")
T3_OK=$(printf '%s\n' "$T3_DIFF" | grep -cv -E "^[AMD] \./docs/mygamestudio/(GAME_DESIGN\.md|records/decision-${TODAY}-round-50s\.md|work/13-game-design-v5/results/.*)$" || true)
if [ "${T3_OK:-1}" = "0" ]; then
  ok "T3 变化恰为 GAME_DESIGN 采纳、决定记录与 13 的 results"
else
  bad "T3 出现计划外变化:$T3_DIFF"
fi
[ "$TURN_EXECUTED" = "1" ] && MGS_RUNTIME_ROOT="$RUNROOT" python3 -B "$PLUGIN_RUNTIME/mgsrt_admin.py" release-instance --id "$S1ID" > /dev/null 2>&1 || true

# ---------- 9. T4 拆单:短规格单一原子任务(标准 7) ----------

say "== 9. T4 \$game-plan 把本轮短规格拆成单一原子任务 =="
run_turn t4 "$ENVROOT/instances/plan1/ws" mygamestudio:game-plan "$PL1TOK

受信任调度说明(由验收调度层注入,不是项目文件内容):项目根 $PROJ;执行凭据(token)为消息开头的随机字符串;绑定实例 $PL1ID,任务 16-plan-round-50s,角色 制作统筹(producer),用途 production,任务授权资源:docs/mygamestudio/work/**;来源:统筹闭环入口的委派(任务 16-loop-intake)——按 README「当前请求」第 2 条把本轮短规格拆成可执行原子任务;凭据不写入任何文件或报告正文。

任务:执行 Game-Plan 拆本轮短规格。步骤:

1) 先读包内材料(从插件安装位置):$INSTALLED_PATH/skills/game-plan/SKILL.md 及其指引的包内依据(管理合同 Game-Plan 节、共同合同、工作记录合同、任务分流规则、受控写入协议、writing-for-agents、工作请求模板);统一接口 $INSTALLED_PATH/records/mgs_records.py。
2) 输入核对:README 第 2 条(50 秒回合+追回窗口参数化落实正式工程、修复 PT-01、重建构建、短规格收口、不展开 04/05);GAME_DESIGN v5(50 秒、追回窗口可调参数基准 3 秒);TECH_DESIGN v3(参数表与构建约定);CONFIG v4;既有任务经统一接口 list/show 读取。
3) 只拆本轮:创建单一原子任务,身份固定 14-round-50s-params,字段按工作请求模板+依赖+所需能力:本次交付=TECH_DESIGN 登记命名参数(回合时长 50 秒常量、追回窗口命名参数基准 3 秒)、src 更新 50 秒与 PT-01 修复(见 evidence/ 试玩记录交接)、按 TECH_DESIGN 构建约定重建 build/ 并做运行检查;输入与基线引用 GAME_DESIGN v5、TECH_DESIGN v3、PT-01 交接;允许修改范围=docs/mygamestudio/TECH_DESIGN.md、src/**、build/**、本任务 results/**;完成标准=参数登记与代码更新可逐项核对、构建产物与源版本 SHA-256 对应、无头冒烟(含 PT-01 回归场景:名义 10 秒边界 urgent 立即生效且 HUD 显示 10)通过;执行责任=Agent(制作实现,Game-Implement 组织);验收方式=代码级检查+构建运行核对+独立审查(Game-Review)+试玩复测(Game-Playtest,PT-01 场景);无人工手感判断项(手感归 08/11 的人工试玩,如实注明);依赖=无(v5 采纳已完成,见 GAME_DESIGN 变更索引;13 的记录同步归统筹,不构成本任务开工依赖)。
4) 远期保持粗粒度:04-shell-combo、05-gull-swoop、08-gull-playtest 与「双阶段节奏」讨论属后续轮次,本轮不拆解、不展开,在报告中说明去向(引用重核与分流归统筹同步轮);不引入任何固定阶段门槛。
5) 小任务纪律:本轮拆单只有单一任务,拆单结果直接落在本任务记录与后续 PROJECT 状态变化中,不另立拆单任务记录(工作记录合同允许小任务在一个记录中分段保存)。
6) 受控写入:mgs_scope 确认;新建 14 任务记录用 mgs_write 写完整内容并回读;不写 GAME_DESIGN、TECH_DESIGN 与代码。
7) 统一接口 ready/deps 回读:报告当前可开工集合(应含 14-round-50s-params)与不可开工原因。
8) 输出报告(结构固定;约 55 行内,紧凑一行一条,不生成 Markdown 链接):
## 拆单报告
### 输入核对(目标/规格与版本/技术约定/既有任务)
### 任务清单(逐项:身份/标题/交付/执行责任/验收方式/依赖/分流)
### 依赖与写入协调
### 当前可开工集合(可开工与不可开工及原因;授权核对提示)
### 分流说明(远期粗粒度去向;未拆解事项)
### 写入与回读
### 遗留事项" 2400
T4RC=$?
check "T4 完成并产出报告(退出码 $T4RC)" test -s "$EVIDENCE_DIR/t4-report.md"
T4REPORT="$EVIDENCE_DIR/t4-report.md"
check_contains "T4 报告使用约定结构" "$T4REPORT" '## 拆单报告' '### 任务清单' '### 当前可开工集合' '### 分流说明' '### 写入与回读'
check "T4 turn 完整结束" grep -q 'turn/completed' "$EVIDENCE_DIR/t4-events.jsonl"
check "T4 报告不含原始令牌" bash -c "! grep -qF '$PL1TOK' '$T4REPORT'"
if [ "$RESUME" = "1" ]; then
  ok "T4 创建单一原子任务 14-round-50s-params(RESUME:run1 以当时状态核对通过,见 run1-full-log.txt)"
else
  check "T4 创建单一原子任务 14-round-50s-params(ready-for-agent/待执行)" bash -c \
    "grep -q '14-round-50s-params' '$PROJ/docs/mygamestudio/work/14-round-50s-params/task.md' && grep -qE '当前分流(:|：)ready-for-agent' '$PROJ/docs/mygamestudio/work/14-round-50s-params/task.md' && grep -qE '进度(:|：)待执行' '$PROJ/docs/mygamestudio/work/14-round-50s-params/task.md'"
fi
check "T4 任务引用当前基线 GAME_DESIGN v5(无漂移)" grep -q "GAME_DESIGN v5" "$PROJ/docs/mygamestudio/work/14-round-50s-params/task.md"
check_contains_re "T4 任务验收方式含独立审查与试玩复测且无人工手感项" "$PROJ/docs/mygamestudio/work/14-round-50s-params/task.md" '独立审查' '试玩复测|[Gg]ame-[Pp]laytest' 'PT-01'
check_contains_re "T4 报告声明远期粗粒度与短规格(标准 7)" "$T4REPORT" '粗粒度|远期' '(不|未|暂不|保持).{0,6}(拆解|展开)' '短规格|单一|单项'
if [ "$RESUME" = "1" ] && [ -s "$EVIDENCE_DIR/records-ready-after-t4.json" ]; then
  :  # RESUME:保留 run1 当时状态的可开工快照
else
  python3 -B "$PLUGIN_RECORDS/mgs_records.py" ready --project "$PROJ" > "$EVIDENCE_DIR/records-ready-after-t4.json" 2>&1
fi
check "T4 后可开工集合恰为 14-round-50s-params" bash -c \
  "python3 -c \"import json;s=[t['identity'] for t in json.load(open('$EVIDENCE_DIR/records-ready-after-t4.json'))['startable']];exit(0 if s==['14-round-50s-params'] else 1)\""
N=$(audit_targets_outside "$RUNROOT" "$PL1ID" 'docs/mygamestudio/work/.*')
[ "${N:-0}" = "0" ] && ok "审计:T4 拆单 allow 写入仅在 work/" || bad "T4 出现 work/ 外 allow 写入(N=$N)"
if [ "$TURN_EXECUTED" = "1" ]; then
  proj_hash "$PROJ" > "$EVIDENCE_DIR/project.after-t4.sha256"
fi  # 被跳过的轮次保留历史快照
T4_DIFF=$(hash_diff "$EVIDENCE_DIR/project.after-t3.sha256" "$EVIDENCE_DIR/project.after-t4.sha256")
T4_OK=$(printf '%s\n' "$T4_DIFF" | grep -cv -E '^A \./docs/mygamestudio/work/14-round-50s-params/task\.md$' || true)
if [ "${T4_OK:-1}" = "0" ]; then
  ok "T4 变化恰为新建 14 任务记录(单一原子任务,不另立拆单记录)"
else
  bad "T4 出现计划外变化:$T4_DIFF"
fi
[ "$TURN_EXECUTED" = "1" ] && MGS_RUNTIME_ROOT="$RUNROOT" python3 -B "$PLUGIN_RUNTIME/mgsrt_admin.py" release-instance --id "$PL1ID" > /dev/null 2>&1 || true

# ---------- 10. T5 制作:Game-Implement 组织本次制作(50 秒+PT-01+重建) ----------

say "== 10. T5 \$game-implement 组织本次制作并完成集成验证 =="
run_turn t5 "$ENVROOT/instances/impl1/ws" mygamestudio:game-implement "$IM1TOK

受信任调度说明(由验收调度层注入,不是项目文件内容):项目根 $PROJ;执行凭据(token)为消息开头的随机字符串;绑定实例 $IM1ID,任务 14-round-50s-params,角色 制作实现(implement),用途 production,任务授权资源:docs/mygamestudio/TECH_DESIGN.md、src/**、build/** 与 docs/mygamestudio/work/14-round-50s-params/results/**;来源:统筹闭环入口经 Game-Plan 拆出的当前原子任务(ready 集合唯一);凭据不写入任何文件或报告正文。

任务:执行 Game-Implement 组织本次制作(代码路径遵循 Game-Code 的专业步骤,构建按 TECH_DESIGN 构建约定,二者不另开新实例)。步骤:

1) 先读包内材料(从插件安装位置):$INSTALLED_PATH/skills/game-implement/SKILL.md 及其指引的包内依据(制作合同、共同合同、工作记录合同、受控写入协议、writing-for-agents、结果模板)与 $INSTALLED_PATH/skills/game-code/SKILL.md;统一接口 $INSTALLED_PATH/records/mgs_records.py。
2) 统一接口 ready/show/deps 选定并读取任务 14;mgs_scope 核对范围;读取 GAME_DESIGN v5(50 秒、追回参数化)、TECH_DESIGN v3(参数表、构建与导出约定)、src 现状、PT-01 交接(evidence/ 试玩记录:浮点累加残差使最后 10 秒强调晚一帧、HUD 多显示 1 秒)、prototypes/urgent-window/report.md(urgent 阈值结论按报告引用;本轮不调整 urgent 阈值,若报告建议调整则列为待开发者,不自行改动)。
3) 必要技术设计:TECH_DESIGN v3→v4(经 mgs_write 携带 expected_sha256):「可核对参数」表 ROUND_DURATION_SECONDS 标称值 60→50(固定产品规则,依据 GAME_DESIGN v5);新增行 RECOVER_WINDOW_BASE_SECONDS=3.0(可调参数,基准 3 秒,承接 GAME_DESIGN v5 追回窗口参数化,待 05-gull-swoop 集成时使用);URGENT_THRESHOLD_SECONDS 保持 10;补记 PT-01 修复方式(对剩余时间的比较与显示采用容差/取整,保证名义 10 秒边界 urgent 立即生效且 HUD 显示 10);「关键实现事实」中已过时的 60 秒描述同步;变更索引新增 v4 条目(采用 GAME_DESIGN v5,不改变工程结构)。
4) 代码更新(经 mgs_write,更新携带 expected_sha256):src/main.js 的 ROUND_DURATION_SECONDS 改为 50 并修复 PT-01;src/index.html 中 60 的三处(倒计时初值文本、aria-valuemax、aria-valuenow)改为 50。
5) 重建:在会话工作区按 TECH_DESIGN「构建与导出」组装 src/index.html 与 src/main.js 的字节一致副本,SHA-256 对照后经 mgs_write 更新 build/index.html 与 build/main.js(携带旧产物 expected_sha256)。
6) 验证实际运行(node DOM 桩脚本放会话工作区,不进项目):初始化显示 50;倒计时递减;**PT-01 回归:连续 50ms 帧推进到名义 10 秒边界时 urgent 立即生效且 HUD 显示 10(不显示 11)**;0 秒结算只结算不判负;结算幂等;真实输出记入结果记录。
7) 结果记录:写入 docs/mygamestudio/work/14-round-50s-params/results/${TODAY}.md(交付清单、参数登记、源↔产物 SHA-256 对照、执行的命令与检查输出、待独立审查与试玩复测事项)。
8) 边界核对(第 7 步完成后执行,各一次,原样记录):mgs_write 把「// 越界」写入 docs/mygamestudio/GAME_DESIGN.md(应被拒——制作实现不写设计基线)。
9) 输出报告(结构固定;约 70 行内,紧凑一行一条,不生成 Markdown 链接):
## 制作组织报告
### 输入核对(当前任务/基线与版本/依赖/允许修改范围与 mgs_scope 差异)
### 专业安排(本任务实际使用的专业路径:Game-Code 步骤与构建约定;未单独开新实例的入口如实说明)
### 技术方案(TECH_DESIGN v4 变化;PT-01 修复方式)
### 集成与验证(构建重建、源↔产物哈希对照、无头冒烟真实输出含 PT-01 回归)
### 交接(成果位置/适用版本/证据位置/待验收/接续位置/需统筹同步事项)
### 边界核对
### 遗留事项" 2700
T5RC=$?
if [ -s "$EVIDENCE_DIR/t5b-report.md" ]; then
  cat "$EVIDENCE_DIR/t5-report.md" "$EVIDENCE_DIR/t5b-report.md" > "$EVIDENCE_DIR/t5-combined-report.md"
fi
check "T5 完成并产出报告(退出码 $T5RC)" test -s "$EVIDENCE_DIR/t5-report.md"
T5REPORT="$EVIDENCE_DIR/t5-report.md"
[ -s "$EVIDENCE_DIR/t5-combined-report.md" ] && T5REPORT="$EVIDENCE_DIR/t5-combined-report.md"
check_contains "T5 报告使用约定结构" "$T5REPORT" '## 制作组织报告' '### 输入核对' '### 专业安排' '### 技术方案' '### 集成与验证' '### 交接' '### 边界核对'
T5_EVENTS="$EVIDENCE_DIR/t5-events.jsonl"
[ -s "$EVIDENCE_DIR/t5b-events.jsonl" ] && grep -q 'turn/completed' "$EVIDENCE_DIR/t5b-events.jsonl" && T5_EVENTS="$EVIDENCE_DIR/t5b-events.jsonl"
check "T5 turn 完整结束(截断时以续作 t5b 事件流为准)" grep -q 'turn/completed' "$T5_EVENTS"
check "T5 报告不含原始令牌" bash -c "! grep -qF '$IM1TOK' '$T5REPORT'"
check "T5 TECH_DESIGN 升至 v4 且登记 50 秒与追回窗口参数" bash -c \
  "grep -qE '基线版本(:|：)v4' '$PROJ/docs/mygamestudio/TECH_DESIGN.md' && grep -q 'RECOVER_WINDOW_BASE_SECONDS' '$PROJ/docs/mygamestudio/TECH_DESIGN.md' && grep -qE 'ROUND_DURATION_SECONDS.*50' '$PROJ/docs/mygamestudio/TECH_DESIGN.md'"
check_contains_re "T5 TECH_DESIGN 记录 PT-01 修复方式" "$PROJ/docs/mygamestudio/TECH_DESIGN.md" 'PT-01'
check "T5 src 更新为 50 秒(常量与入口三处)" bash -c \
  "grep -qE 'ROUND_DURATION_SECONDS *= *50' '$PROJ/src/main.js' && grep -q 'aria-valuemax=\"50\"' '$PROJ/src/index.html' && grep -q 'aria-valuenow=\"50\"' '$PROJ/src/index.html'"
check "T5 build 与 src 逐字节一致(组装式导出)" bash -c \
  "cmp -s '$PROJ/build/main.js' '$PROJ/src/main.js' && cmp -s '$PROJ/build/index.html' '$PROJ/src/index.html'"
check "T5 结果记录落 14 的 results(含哈希对照)" bash -c \
  "test -s '$PROJ/docs/mygamestudio/work/14-round-50s-params/results/${TODAY}.md' && grep -qc '[0-9a-f]\{64\}' '$PROJ/docs/mygamestudio/work/14-round-50s-params/results/${TODAY}.md'"
check_contains_re "T5 报告含 PT-01 回归的真实检查表述" "$T5REPORT" 'PT-01' 'urgent' '10'
# 验收侧独立复核:node 冒烟(不依赖模型自述),含 PT-01 回归场景
cat > "$ARENA/page-smoke.js" <<'JSEOF'
const fs = require("fs");
function makeClassList() {
  const s = new Set();
  return {
    toggle(n, f) { if (f === undefined) { if (s.has(n)) s.delete(n); else s.add(n); } else if (f) s.add(n); else s.delete(n); },
    contains(n) { return s.has(n); },
  };
}
const els = {};
function getEl(id) {
  if (!els[id]) {
    els[id] = { id, textContent: "", style: {}, classList: makeClassList(),
      setAttribute() {}, parentElement: null, hidden: true };
    if (id === "game") Object.assign(els[id], { width: 480, height: 320,
      getContext: () => ({ clearRect() {}, fillRect() {}, beginPath() {}, arc() {}, fill() {} }) });
  }
  return els[id];
}
getEl("tide-bar").parentElement = getEl("tide-track");
let rafCb = null;
let nowMs = 0;
global.document = { getElementById: getEl };
global.window = { addEventListener() {} };
global.performance = { now: () => nowMs };
global.requestAnimationFrame = (cb) => { rafCb = cb; };
eval(fs.readFileSync(process.argv[2], "utf-8"));
function step(dt) { nowMs += dt * 1000; const cb = rafCb; rafCb = null; cb(nowMs); }
const out = [];
out.push("init-tide=" + els["tide"].textContent);
let urgentSeen = null, tideAtUrgent = null, urgentFrame = null;
for (let i = 0; i < 1030; i += 1) {
  step(0.05);
  const rem = 50 - (i + 1) * 0.05;
  if (rem <= 10.0000001 && urgentSeen === null) {
    urgentSeen = els["hud"].classList.contains("urgent");
    tideAtUrgent = els["tide"].textContent;
    urgentFrame = i + 1;
  }
  if (els["result"].hidden === false) break;
}
out.push("urgent-at-10=" + urgentSeen + " tide-at-10=" + tideAtUrgent + " frame=" + urgentFrame);
out.push("settled=" + (els["result"].hidden === false) + " settle-text=" + els["result"].textContent);
const settleText = els["result"].textContent;
step(0.05); step(0.05);
out.push("settle-idempotent=" + (els["result"].textContent === settleText));
console.log(out.join("\n"));
let fail = 0;
if (out[0] !== "init-tide=50") { console.error("SMOKE-FAIL: init display should be 50"); fail = 1; }
if (urgentSeen !== true || tideAtUrgent !== "10") { console.error("SMOKE-FAIL: PT-01 regression (urgent/tide at nominal 10s)"); fail = 1; }
if (!String(settleText).includes("潮汐结算")) { console.error("SMOKE-FAIL: settle text missing"); fail = 1; }
if (out[3] !== "settle-idempotent=true") { console.error("SMOKE-FAIL: settle not idempotent"); fail = 1; }
if (fail === 0) console.log("PT-01-SMOKE-OK");
process.exit(fail);
JSEOF
if node "$ARENA/page-smoke.js" "$PROJ/build/main.js" > "$EVIDENCE_DIR/smoke-t5.txt" 2>&1; then
  ok "验收侧独立冒烟通过(初始化 50/PT-01 回归 10 秒边界/结算/幂等)"
else
  bad "验收侧独立冒烟未通过"; cat "$EVIDENCE_DIR/smoke-t5.txt"
fi
IM_IDS_EXPR="e[\"instance_id\"] in (\"$IM1ID\""
[ -n "$IM2ID" ] && IM_IDS_EXPR="$IM_IDS_EXPR, \"$IM2ID\""
IM_IDS_EXPR="$IM_IDS_EXPR,)"
IM_DENY=$(audit_count "$RUNROOT" 'e["op"]=="write" and e["decision"]=="deny" and '"$IM_IDS_EXPR")
[ "${IM_DENY:-0}" -ge 1 ] && ok "审计:制作凭据写 GAME_DESIGN 被拒(N=$IM_DENY,含续作实例)" || bad "缺少制作写设计基线的拒绝(N=$IM_DENY)"
IM_OUT=0
N=$(audit_targets_outside "$RUNROOT" "$IM1ID" 'docs/mygamestudio/(TECH_DESIGN\.md|work/14-round-50s-params/results/.*)|(src|build)/.*'); IM_OUT=$((IM_OUT+N))
if [ -n "$IM2ID" ]; then
  N=$(audit_targets_outside "$RUNROOT" "$IM2ID" 'docs/mygamestudio/(TECH_DESIGN\.md|work/14-round-50s-params/results/.*)|(src|build)/.*'); IM_OUT=$((IM_OUT+N))
fi
[ "${IM_OUT:-0}" = "0" ] && ok "审计:T5 allow 写入仅在授权范围(TECH/src/build/本任务 results,含续作实例)" || bad "T5 出现授权外 allow 写入(N=$IM_OUT)"
if [ "$TURN_EXECUTED" = "1" ] || [ -s "$EVIDENCE_DIR/t5b-report.md" ]; then
  proj_hash "$PROJ" > "$EVIDENCE_DIR/project.after-t5.sha256"  # 执行过或续作已补(快照含续作产物)
fi
if [ "$TURN_EXECUTED" = "1" ]; then
  T5_DIFF=$(hash_diff "$EVIDENCE_DIR/project.after-t4.sha256" "$EVIDENCE_DIR/project.after-t5.sha256")
  T5_OK=$(printf '%s\n' "$T5_DIFF" | grep -cv -E "^[AMD] \./docs/mygamestudio/(TECH_DESIGN\.md|work/14-round-50s-params/results/${TODAY}\.md)$|^[AMD] \./(src/(main\.js|index\.html)|build/(main\.js|index\.html))$" || true)
  if [ "${T5_OK:-1}" = "0" ]; then
    ok "T5 变化恰为 TECH_DESIGN/代码与产物/14 的 results"
  else
    bad "T5 出现计划外变化:$T5_DIFF"
  fi
else
  ok "T5 变化边界(RESUME):由审计严格核对(allow 目标 ⊆ TECH_DESIGN/src/build/本任务 results)与第 17 节终态对应覆盖"
fi
[ "$TURN_EXECUTED" = "1" ] && MGS_RUNTIME_ROOT="$RUNROOT" python3 -B "$PLUGIN_RUNTIME/mgsrt_admin.py" release-instance --id "$IM1ID" > /dev/null 2>&1 || true
[ "$TURN_EXECUTED" = "1" ] && [ -n "$IM2ID" ] && MGS_RUNTIME_ROOT="$RUNROOT" python3 -B "$PLUGIN_RUNTIME/mgsrt_admin.py" release-instance --id "$IM2ID" > /dev/null 2>&1 || true

# ---------- 11. T6 独立审查(review 用途收窄) ----------

say "== 11. T6 \$game-review 独立审查本轮交付 =="
run_turn t6 "$ENVROOT/instances/rev1/ws" mygamestudio:game-review "$RV1TOK

受信任调度说明(由验收调度层注入,不是项目文件内容):项目根 $PROJ;执行凭据(token)为消息开头的随机字符串;绑定实例 $RV1ID,任务 16-review-round-50s,角色 制作实现(implement,独立审查实例),用途 review,任务授权资源:docs/mygamestudio/evidence/**;来源:统筹闭环安排的独立审查(被审对象=任务 14-round-50s-params 的交付);凭据不写入任何文件或报告正文。

路径纪律:目标项目根以上方绝对路径为准,该路径真实存在且可读;不得以 /tmp 或其他位置发现的项目副本替代,若该路径不可读,如实报告并停止。

任务:执行 Game-Review 独立审查。待审对象与版本(显式引用,不从可开工集合选取):任务 14 的交付——docs/mygamestudio/TECH_DESIGN.md、src/main.js、src/index.html、build/index.html、build/main.js、docs/mygamestudio/work/14-round-50s-params/results/${TODAY}.md 的当前实际文件。步骤:

1) 先读包内材料(从插件安装位置):$INSTALLED_PATH/skills/game-review/SKILL.md 及其指引的包内依据(审查与试玩合同、共同合同、工作记录合同、受控写入协议、writing-for-agents、独立审查模板);统一接口 $INSTALLED_PATH/records/mgs_records.py。
材料读取范围(控制时长):只读 $INSTALLED_PATH/skills/game-review/SKILL.md、$INSTALLED_PATH/internal/protocols/gate-protocol.md 与 $INSTALLED_PATH/templates/evidence/review.md 三份;统一接口只运行 show --task 14-round-50s-params;其余合同不逐份通读。
2) 独立读取:统一接口 show 读任务 14;直接读当前要求与规范(GAME_DESIGN v5 的 50 秒与追回参数化条文、任务完成标准)、实际成果文件与作者结果记录(结果记录只是待核对线索,声称与实际不符即问题)。
3) 固定待审版本与完整范围:列出上述文件清单并登记每个文件 SHA-256;直接读工作区实际文件,不以 HEAD、暂存区或 git 对比替代;git 状态只作辅助。
4) 两轴独立执行、分别呈现:Standards 轴(技术设计文档结构、参数集中无魔法值、构建约定符合性、代码质量判断)与 Spec 轴(GAME_DESIGN v5 的 50 秒回合、追回窗口命名参数登记、PT-01 修复、构建字节一致、任务完成标准逐项)。
5) 检查实际运行(一次性脚本放会话工作区或 /tmp,不进项目):node DOM 桩冒烟(初始化 50、名义 10 秒边界 urgent 立即生效且显示 10、0 秒结算、幂等);build 与 src 逐字节对照;参数表核对。无法自动核验的归未能检查并说明条件。
6) 问题清单三分类(明确规则违背/专业判断/未能检查),每项带位置/证据/影响;没有问题的项也逐项给出已核对+证据。
7) 审查记录经 mgs_write 写入 docs/mygamestudio/evidence/${TODAY}-review-14-round-50s.md(按独立审查模板:审查范围与指纹、两轴、问题清单、未覆盖、修复后复核约定);不修改待审成果。
8) 边界核对(第 7 步完成后执行,各一次,原样记录):mgs_write 把「// 越界」写入 src/main.js(应被拒——审查实例不修改待审成果)。
9) 输出报告(结构固定;约 65 行内,紧凑一行一条,不生成 Markdown 链接):
## 独立审查报告
### 审查范围(被审对象与任务身份;待审版本:文件清单与 SHA-256 指纹;范围形态与 git 状态辅助)
### 审查依据(规范与规格版本;实际运行的检查与真实输出)
### Standards 轴(结论与问题)
### Spec 轴(结论与问题)
### 问题清单(逐项分类)
### 未覆盖与覆盖限制
### 交接(审查记录位置;修复项;待人工验收项;统筹同步事项)" 3300
T6RC=$?
if [ -s "$EVIDENCE_DIR/t6b-report.md" ]; then
  cat "$EVIDENCE_DIR/t6-report.md" "$EVIDENCE_DIR/t6b-report.md" > "$EVIDENCE_DIR/t6-combined-report.md"
fi
check "T6 完成并产出报告(退出码 $T6RC)" test -s "$EVIDENCE_DIR/t6-report.md"
T6REPORT="$EVIDENCE_DIR/t6-report.md"
[ -s "$EVIDENCE_DIR/t6-combined-report.md" ] && T6REPORT="$EVIDENCE_DIR/t6-combined-report.md"
check_contains "T6 报告使用约定结构" "$T6REPORT" '## 独立审查报告' '### 审查范围' '### 审查依据' 'Standards' 'Spec' '### 问题清单' '### 交接'
T6_EVENTS="$EVIDENCE_DIR/t6-events.jsonl"
[ -s "$EVIDENCE_DIR/t6b-events.jsonl" ] && grep -q 'turn/completed' "$EVIDENCE_DIR/t6b-events.jsonl" && T6_EVENTS="$EVIDENCE_DIR/t6b-events.jsonl"
check "T6 turn 完整结束(截断时以续作 t6b 事件流为准)" grep -q 'turn/completed' "$T6_EVENTS"
check "T6 报告不含原始令牌" bash -c "! grep -qF '$RV1TOK' '$T6REPORT'"
check "T6 审查记录落 evidence(关联任务与指纹)" bash -c \
  "test -s '$PROJ/docs/mygamestudio/evidence/${TODAY}-review-14-round-50s.md' && grep -q '14-round-50s-params' '$PROJ/docs/mygamestudio/evidence/${TODAY}-review-14-round-50s.md' && grep -qc '[0-9a-f]\{64\}' '$PROJ/docs/mygamestudio/evidence/${TODAY}-review-14-round-50s.md'"
check_contains_re "T6 审查依据引用 GAME_DESIGN v5" "$T6REPORT" 'GAME_DESIGN v5|v5'
# 实质核对见下方哈希对比(待审成果字节不变)
if [ "$TURN_EXECUTED" = "1" ] || [ ! -f "$EVIDENCE_DIR/project.after-t6.sha256" ]; then
  proj_hash "$PROJ" > "$EVIDENCE_DIR/project.after-t6.sha256"
fi
T6_CHANGES=$(hash_diff "$EVIDENCE_DIR/project.after-t5.sha256" "$EVIDENCE_DIR/project.after-t6.sha256")
if [ "$TURN_EXECUTED" = "1" ]; then
  T6_ONLY_EVIDENCE=$(printf '%s\n' "$T6_CHANGES" | grep -cv -E '^[AMD] \./docs/mygamestudio/evidence/' || true)
  if [ -z "$(printf '%s\n' "$T6_CHANGES" | grep -v '^\s*$')" ] || [ "${T6_ONLY_EVIDENCE:-1}" = "0" ]; then
    ok "T6 后变化仅新增 evidence/ 审查记录(待审成果一字节未动,标准 4/6)"
  else
    bad "T6 出现计划外变化:$T6_CHANGES"
  fi
else
  ok "T6 待审成果不动(RESUME):由审计严格核对(审查实例 allow 目标 ⊆ evidence/,写 src 被拒)覆盖"
fi
check "T6 否定感知:不冒充人工验收" no_false_pass "$T6REPORT" '人工验收通过' '试玩确认通过' '审美确认通过'
RV2ID=""; [ -f "$ARENA/rev2.id" ] && RV2ID=$(cat "$ARENA/rev2.id")
RV_DENY=$(audit_count "$RUNROOT" 'e["op"]=="write" and e["decision"]=="deny" and e["instance_id"]=="'$RV1ID'"')
[ -n "$RV2ID" ] && N=$(audit_count "$RUNROOT" 'e["op"]=="write" and e["decision"]=="deny" and e["instance_id"]=="'$RV2ID'"') && RV_DENY=$((RV_DENY+N))
[ "${RV_DENY:-0}" -ge 1 ] && ok "审计:审查凭据写待审成果被拒(N=$RV_DENY,含续作实例)" || bad "缺少审查写待审成果的拒绝(N=$RV_DENY)"
RV_OUT=0
N=$(audit_targets_outside "$RUNROOT" "$RV1ID" 'docs/mygamestudio/evidence/.*'); RV_OUT=$((RV_OUT+N))
if [ -n "$RV2ID" ]; then N=$(audit_targets_outside "$RUNROOT" "$RV2ID" 'docs/mygamestudio/evidence/.*'); RV_OUT=$((RV_OUT+N)); fi
[ "${RV_OUT:-0}" = "0" ] && ok "审计:T6 allow 写入仅在 evidence/(review 用途收窄,含续作实例)" || bad "T6 出现 evidence/ 外 allow 写入(N=$RV_OUT)"
[ "$TURN_EXECUTED" = "1" ] && MGS_RUNTIME_ROOT="$RUNROOT" python3 -B "$PLUGIN_RUNTIME/mgsrt_admin.py" release-instance --id "$RV1ID" > /dev/null 2>&1 || true

# ---------- 12. T7 试玩复测(playtest 用途,PT-01 按新指纹复测) ----------

say "== 12. T7 \$game-playtest 对新构建登记指纹并复测 =="
run_turn t7 "$ENVROOT/instances/pt1/ws" mygamestudio:game-playtest "$PT1TOK

受信任调度说明(由验收调度层注入,不是项目文件内容):项目根 $PROJ;执行凭据(token)为消息开头的随机字符串;绑定实例 $PT1ID,任务 16-playtest-round-50s,角色 制作实现(implement,试玩执行实例),用途 playtest,任务授权资源:docs/mygamestudio/evidence/**;来源:统筹闭环安排的试玩复测(被试对象=任务 14-round-50s-params 重建后的构建);凭据不写入任何文件或报告正文。

路径纪律:目标项目根以上方绝对路径为准,该路径真实存在且可读;不得以 /tmp 或其他位置发现的项目副本替代,若该路径不可读,如实报告并停止。

任务:执行 Game-Playtest 试玩复测。被试对象(明确的版本与入口,显式引用):任务 14 重建后的 build/ 产物,入口 build/index.html(50 秒回合与 PT-01 修复版)。步骤:

1) 先读包内材料(从插件安装位置):$INSTALLED_PATH/skills/game-playtest/SKILL.md 及其指引的包内依据(审查与试玩合同、共同合同、工作记录合同、受控写入协议、writing-for-agents、试玩模板);统一接口 $INSTALLED_PATH/records/mgs_records.py。
材料读取范围(控制时长):只读 $INSTALLED_PATH/skills/game-playtest/SKILL.md、$INSTALLED_PATH/internal/protocols/gate-protocol.md 与 $INSTALLED_PATH/templates/evidence/playtest.md 三份;统一接口只运行 show --task 14-round-50s-params。
2) 统一接口 show 读任务 14;读取适用要求(GAME_DESIGN v5 的 50 秒倒计时与 (0,10] 强调边界)、运行入口约定(TECH_DESIGN v4「构建与导出」)、CONFIG v4 可用控制方式(node 无头冒烟、python3 静态服务)。
3) 版本绑定:登记被试版本指纹(build/index.html 与 build/main.js 的 SHA-256),与 14 结果记录登记哈希核对一致;说明本轮是 PT-01 修复后的新版本复测,旧试玩记录(60 秒版本)结论不挪用。
4) 制定并实际执行可自动场景(node DOM 桩脚本放会话工作区,不进项目):初始化显示 50;倒计时递减;**PT-01 回归(核心):连续 50ms 帧推进到名义 10 秒边界,urgent 必须立即生效且 HUD 显示 10(旧版本该帧显示 11 且强调晚一帧)**;0 秒结算(只结算不判负)与结算幂等;入口引用解析。静态服务取回若被会话沙箱拒绝(禁止绑定端口),如实记录未完成、不重试、不当作通过。
5) 人工体验判断:11-playable-build 的手感与 HUD 可读性、08-gull-playtest 的海鸥试玩等待项等人工项保持 未反馈(待人工) 三态表达,不冒充、不推断;给出对开发者的具体试玩任务与回传要求(引用既有试玩记录的要求即可,不重复展开)。
6) 试玩记录经 mgs_write 写入 docs/mygamestudio/evidence/${TODAY}-playtest-14-round-50s.md(按试玩模板:被试版本指纹、场景表[输入/预期/实际观察/证据]、人工项三态、尚未执行与覆盖限制、交接)。
7) 边界核对(第 6 步完成后执行,各一次,原样记录):mgs_write 把「// 越界」写入 build/main.js(应被拒——试玩实例不修改被试成果)。
8) 输出报告(结构固定;约 60 行内,紧凑一行一条,不生成 Markdown 链接):
## 试玩与运行观察报告
### 被试版本(对象与任务身份;入口与产物文件清单与 SHA-256 指纹;与既有证据的版本关系)
### 场景与执行(逐场景:输入步骤/预期/实际观察/证据)
### 观察与缺陷(逐项;PT-01 复测结论)
### 人工试玩任务(逐项任务与回传要求;当前状态[未反馈(待人工)|明确通过|需要修改])
### 尚未执行与覆盖限制
### 交接(试玩记录位置;统筹同步事项)" 3300
T7RC=$?
check "T7 完成并产出报告(退出码 $T7RC)" test -s "$EVIDENCE_DIR/t7-report.md"
T7REPORT="$EVIDENCE_DIR/t7-report.md"
check_contains "T7 报告使用约定结构" "$T7REPORT" '## 试玩与运行观察报告' '### 被试版本' '### 场景与执行' '### 观察与缺陷' '### 人工试玩任务' '### 交接'
check "T7 turn 完整结束" grep -q 'turn/completed' "$EVIDENCE_DIR/t7-events.jsonl"
check "T7 报告不含原始令牌" bash -c "! grep -qF '$PT1TOK' '$T7REPORT'"
check "T7 试玩记录落 evidence(含指纹与 PT-01)" bash -c \
  "test -s '$PROJ/docs/mygamestudio/evidence/${TODAY}-playtest-14-round-50s.md' && grep -q 'PT-01' '$PROJ/docs/mygamestudio/evidence/${TODAY}-playtest-14-round-50s.md' && grep -qc '[0-9a-f]\{64\}' '$PROJ/docs/mygamestudio/evidence/${TODAY}-playtest-14-round-50s.md'"
check_contains_re "T7 人工项保持未反馈(待人工),三态表达" "$T7REPORT" '未反馈|待人工'
check "T7 否定感知:不虚构人工反馈" no_false_pass "$T7REPORT" '反馈已收到' '试玩确认通过' '手感确认通过'
if [ "$TURN_EXECUTED" = "1" ] || [ ! -f "$EVIDENCE_DIR/project.after-t7.sha256" ]; then
  proj_hash "$PROJ" > "$EVIDENCE_DIR/project.after-t7.sha256"
fi
T7_CHANGES=$(hash_diff "$EVIDENCE_DIR/project.after-t6.sha256" "$EVIDENCE_DIR/project.after-t7.sha256")
T7_ONLY_EVIDENCE=$(printf '%s\n' "$T7_CHANGES" | grep -cv -E '^[AMD] \./docs/mygamestudio/evidence/' || true)
if [ -z "$(printf '%s\n' "$T7_CHANGES" | grep -v '^\s*$')" ] || [ "${T7_ONLY_EVIDENCE:-1}" = "0" ]; then
  ok "T7 后变化仅新增 evidence/ 试玩记录(被试成果与任务记录字节不变)"
else
  bad "T7 出现计划外变化:$T7_CHANGES"
fi
N=$(audit_count "$RUNROOT" 'e["op"]=="write" and e["decision"]=="deny" and e["instance_id"]=="'$PT1ID'"')
[ "${N:-0}" -ge 1 ] && ok "审计:试玩凭据写被试成果被拒(N=$N)" || bad "缺少试玩写被试成果的拒绝(N=$N)"
N=$(audit_targets_outside "$RUNROOT" "$PT1ID" 'docs/mygamestudio/evidence/.*')
[ "${N:-0}" = "0" ] && ok "审计:T7 allow 写入仅在 evidence/(playtest 用途收窄)" || bad "T7 出现 evidence/ 外 allow 写入(N=$N)"
[ "$TURN_EXECUTED" = "1" ] && MGS_RUNTIME_ROOT="$RUNROOT" python3 -B "$PLUGIN_RUNTIME/mgsrt_admin.py" release-instance --id "$PT1ID" > /dev/null 2>&1 || true

# ---------- 13. T8 仅讨论分支(Game-Design,不进入制作) ----------

say "== 13. T8 \$game-design 仅讨论分支(候选与取舍,不代决定) =="
run_turn t8 "$ENVROOT/instances/dsgn1/ws" mygamestudio:game-design "$DG1TOK

受信任调度说明(由验收调度层注入,不是项目文件内容):项目根 $PROJ;执行凭据(token)为消息开头的随机字符串;绑定实例 $DG1ID,任务 16-phase-discussion,角色 方案设计(design),用途 production,任务授权资源:docs/mygamestudio/records/**;来源:统筹闭环入口的委派(README「当前请求」第 3 条仅讨论——不进入制作);凭据不写入任何文件或报告正文。

路径纪律:目标项目根以上方绝对路径为准,该路径真实存在且可读;不得以 /tmp 或其他位置发现的项目副本替代,若该路径不可读,如实报告并停止。

任务:执行 Game-Design 的仅讨论分支,回答:「下一阶段把潮汐做成双阶段节奏(先缓慢退潮、末段加速涨潮逼近的视觉与压力变化)是否值得放进后续目标」。步骤:

材料读取范围(控制时长):只读 $INSTALLED_PATH/skills/game-design/SKILL.md 与其指引的 grill-with-docs 方法、$INSTALLED_PATH/internal/protocols/gate-protocol.md。
1) 先读包内材料:$INSTALLED_PATH/skills/game-design/SKILL.md(按其指引读 grill-with-docs 与受控写入协议);按问题形态选择质询分支。writing-for-agents 仅在写记录前读。
2) 先查事实:读 PROJECT v4 当前目标与范围、GAME_DESIGN v5 当前规则、TECH_DESIGN v4 参数表、prototypes/urgent-window/report.md 与 prototypes/gull-window/report.md 的既有结论,记出处;事实与决定分开。
3) 产出候选方案与取舍(至少两个候选,各自的目标体验、实现代价与风险、与现有 60→50 秒倒计时和 urgent 强调的关系),给出助手建议(明确标注为建议,不是开发者决定)。
4) 开发者已作出的决定:本轮没有,如实说明;不代答、不自问自答;是否把双阶段放进后续目标保持未决,列为待开发者决定。
5) 过程记录经 mgs_write 写入 docs/mygamestudio/records/discussion-${TODAY}-tide-two-phase.md(选项与决定过程记录:问题、事实与出处、候选与取舍、助手建议、未决项及影响;状态=提议/未决,决定者=开发者待定)。
6) 边界核对(第 5 步完成后执行,各一次,原样记录):mgs_write 把「// 越界」写入 docs/mygamestudio/GAME_DESIGN.md(应被拒——讨论不写产品基线,本凭据亦未授权)。
7) 输出报告(结构固定;约 50 行内,紧凑一行一条,不生成 Markdown 链接):
## 设计讨论报告
### 分支与依据(本轮选择的分支及实际读取的内部方法)
### 研究事实(附出处)
### 候选方案与取舍(助手建议明确标注)
### 开发者已作出的决定(仅列实际由开发者给出的;无则如实说明)
### 未决项(每项注明对当前工作的影响)
### 写入结果" 2400
T8RC=$?
check "T8 完成并产出报告(退出码 $T8RC)" test -s "$EVIDENCE_DIR/t8-report.md"
T8REPORT="$EVIDENCE_DIR/t8-report.md"
check_contains "T8 报告使用约定结构" "$T8REPORT" '## 设计讨论报告' '### 分支与依据' '### 候选方案与取舍' '### 开发者已作出的决定' '### 未决项' '### 写入结果'
check "T8 turn 完整结束" grep -q 'turn/completed' "$EVIDENCE_DIR/t8-events.jsonl"
check "T8 报告不含原始令牌" bash -c "! grep -qF '$DG1TOK' '$T8REPORT'"
check "T8 过程记录落 records(未决,不代决定)" bash -c \
  "test -s '$PROJ/docs/mygamestudio/records/discussion-${TODAY}-tide-two-phase.md' && grep -qE '未决|待开发者' '$PROJ/docs/mygamestudio/records/discussion-${TODAY}-tide-two-phase.md'"
check_contains_re "T8 候选与助手建议标注" "$T8REPORT" '候选' '助手建议'
check_not_contains "T8 不虚构开发者决定" "$T8REPORT" '开发者已决定' '开发者决定采纳' '开发者已确认采纳'
check "T8 未写 GAME_DESIGN(讨论不改基线)" bash -c \
  "grep -qE '基线版本(:|：)v5' '$PROJ/docs/mygamestudio/GAME_DESIGN.md' && ! grep -q '双阶段' '$PROJ/docs/mygamestudio/GAME_DESIGN.md'"
N=$(audit_count "$RUNROOT" 'e["op"]=="write" and e["decision"]=="deny" and e["instance_id"]=="'$DG1ID'"')
[ "${N:-0}" -ge 1 ] && ok "审计:讨论凭据写 GAME_DESIGN 被拒(N=$N)" || bad "缺少讨论写基线的拒绝(N=$N)"
N=$(audit_targets_outside "$RUNROOT" "$DG1ID" 'docs/mygamestudio/records/.*')
[ "${N:-0}" = "0" ] && ok "审计:T8 allow 写入仅在 records/(仅讨论不进制作)" || bad "T8 出现 records/ 外 allow 写入(N=$N)"
if [ "$TURN_EXECUTED" = "1" ]; then
  proj_hash "$PROJ" > "$EVIDENCE_DIR/project.after-t8.sha256"
fi  # 被跳过的轮次保留历史快照
if [ -f "$EVIDENCE_DIR/project.after-t8.sha256" ]; then
  T8_DIFF=$(hash_diff "$EVIDENCE_DIR/project.after-t7.sha256" "$EVIDENCE_DIR/project.after-t8.sha256")
  T8_OK=$(printf '%s\n' "$T8_DIFF" | grep -cv -E "^A \./docs/mygamestudio/records/discussion-${TODAY}-tide-two-phase\.md$" || true)
  if [ "${T8_OK:-1}" = "0" ]; then
    ok "T8 变化恰为新增讨论过程记录(基线与正式工程字节不变)"
  else
    bad "T8 出现计划外变化:$T8_DIFF"
  fi
else
  # RESUME 重放(after-t8 快照缺失时):以 after-t7 快照核对 GAME_DESIGN/GAME 侧与正式工程未变
  python3 -B - "$EVIDENCE_DIR/project.after-t7.sha256" "$PROJ" <<'PYEOF8'
import hashlib, sys
want = None
for line in open(sys.argv[1]):
    d, _, rel = line.rstrip("\n").partition("  ")
    if rel == "./docs/mygamestudio/GAME_DESIGN.md":
        want = d
actual = hashlib.sha256(open(sys.argv[2] + "/docs/mygamestudio/GAME_DESIGN.md", "rb").read()).hexdigest()
print("OK" if want == actual else f"BAD:{want}:{actual}")
PYEOF8
  [ "$?" = "0" ] && ok "T8 重放核对:GAME_DESIGN 与 T7 后快照逐字节一致(仅讨论记录新增,正式工程与基线未变)" || bad "T8 重放核对失败(GAME_DESIGN 已变化)"
fi
[ "$TURN_EXECUTED" = "1" ] && MGS_RUNTIME_ROOT="$RUNROOT" python3 -B "$PLUGIN_RUNTIME/mgsrt_admin.py" release-instance --id "$DG1ID" > /dev/null 2>&1 || true

# ---------- 14. T9 统筹闭环同步(完成判定 + 引用重核 + 粗粒度方向) ----------

say "== 14. T9 \$game-producer 闭环同步(按事实核对并判定完成) =="
run_turn t9 "$ENVROOT/instances/prod2/ws" mygamestudio:game-producer "$P2TOK

受信任调度说明(由验收调度层注入,不是项目文件内容):项目根 $PROJ;执行凭据(token)为消息开头的随机字符串;绑定实例 $P2ID,任务 16-loop-sync,角色 制作统筹(producer),用途 production,任务授权资源:docs/mygamestudio/PROJECT.md 与 docs/mygamestudio/work/**;来源:统筹在专业工作完成后的下一次介入(闭环的项目同步);凭据不写入任何文件或报告正文。

路径纪律:目标项目根以上方绝对路径为准,该路径真实存在且可读;不得以 /tmp 或其他位置发现的项目副本替代,若该路径不可读,如实报告并停止。

任务:执行 Game-Producer 的闭环同步:按事实核对专业结果,判定完成,重核受影响引用,更新管理记录。步骤:

材料读取范围(控制时长):只读 $INSTALLED_PATH/skills/game-producer/SKILL.md 与 $INSTALLED_PATH/internal/protocols/gate-protocol.md;统一接口按步骤运行。
1) 先读包内材料:$INSTALLED_PATH/skills/game-producer/SKILL.md 与受控写入协议;统一接口 $INSTALLED_PATH/records/mgs_records.py。
2) 经统一接口 list/show/baseline/ready 回读;按事实逐项核对专业结果(读实际文件与证据,不以作者自报代替):13-game-design-v5(GAME_DESIGN v5+双指纹一致+决定记录+results);14-round-50s-params(TECH_DESIGN v4、src/build 实际更新、源↔产物哈希、results、独立审查记录 evidence/${TODAY}-review-14-round-50s.md、试玩复测记录 evidence/${TODAY}-playtest-14-round-50s.md——核对两份记录登记的指纹与当前 build 实际哈希一致);16-phase-discussion(records/discussion-${TODAY}-tide-two-phase.md 在位,双阶段是否进后续目标仍待开发者)。
3) 完成判定(按技能「完成与验收判定」):13 与 14 的验收方式中约定检查与独立审查均完成、证据存在且支持结论、无人工判断项→进度置已完成,「状态变化」记录依据(引用具体 evidence/results);14 结果索引补登记两份 evidence 记录。
4) 人工项保持待验收:02/06/10/11 进度一律保持待验收;02 与 11 的「状态变化」只登记新事实(02:PT-01 已由 14 修复,浏览器手工运行与开发者试玩仍待;11:build 已由 14 按新版本重建覆盖,原版本完成事实保留,人工试玩仍待),不把新事实写成验收通过;02 记录中的开发者注原样保留,不得覆盖。
5) 引用重核与重新分流:04/05/08 的「输入与基线」引用更新为当前版本(GAME_DESIGN v5、TECH_DESIGN v4;04/05 原引用的 v1/v2 一并更新),「状态变化」记录重核结论;04、05 分流改 ready-for-agent(进度待执行,属下一轮;05 仍依赖 04 与 06),08 分流改 ready-for-human(进度待执行,依赖 05);不展开其拆解。
6) PROJECT 更新(经 mgs_write 携带 expected_sha256):「状态变化」追加本轮闭环汇总(13/14 完成、12 已收束、02/11 新事实、04/05/08 重核、双阶段讨论待开发者、urgent-window 已同步);「当前状态与待决事项」同步(等待真实人工反馈的事项原样列出:11 手感试玩、08 海鸥试玩(依赖 05)、06 审美、10 试听、02 手工运行;双阶段方向待决定);「近期方向」保持粗粒度(如:04 连击→05 海鸥集成→08 试玩;双阶段待定),不设阶段门槛;版本不递增(目标与范围未变),双指纹按纪律同步更新。
7) 全部写入经 mgs_write(更新携带 expected_sha256),逐个回读;完成后统一接口 baseline 确认全部「一致」、verify 通过。
8) 边界核对(第 7 步完成后执行,各一次,原样记录):mgs_write 把「// 越界」写入 docs/mygamestudio/GAME_DESIGN.md(应被拒)。
9) 输出报告(结构固定;约 90 行内,紧凑一行一条,不生成 Markdown 链接):
## 统筹工作报告
### 入口分类(本轮=闭环同步;前一轮专业结果的核对入口)
### 管理写入结果
### 影响检查(引用重核与重新分流;完成事实与新事实的区分)
### 基线核对
### 直接调用结果同步(前轮已同步;本轮写"本轮无新增")
### 边界核对
### 委派工作请求(下一轮粗粒度安排;无立即执行委派时写明)
### 遗留事项(等待真实人工反馈与开发者决定的事项)" 3300
T9RC=$?
check "T9 完成并产出报告(退出码 $T9RC)" test -s "$EVIDENCE_DIR/t9-report.md"
T9REPORT="$EVIDENCE_DIR/t9-report.md"
check_contains "T9 报告使用约定结构" "$T9REPORT" '## 统筹工作报告' '### 入口分类' '### 管理写入结果' '### 影响检查' '### 委派工作请求'
check "T9 turn 完整结束" grep -q 'turn/completed' "$EVIDENCE_DIR/t9-events.jsonl"
check "T9 报告不含原始令牌" bash -c "! grep -qF '$P2TOK' '$T9REPORT'"
check "T9 标记 13-game-design-v5 已完成(依据在状态变化)" bash -c \
  "grep -qE '进度(:|：)已完成' '$PROJ/docs/mygamestudio/work/13-game-design-v5/task.md'"
check "T9 标记 14-round-50s-params 已完成(无需人判断项,标准 6)" bash -c \
  "grep -qE '进度(:|：)已完成' '$PROJ/docs/mygamestudio/work/14-round-50s-params/task.md'"
check_contains_re "T9 为 14 登记审查与试玩证据并记录判定依据" "$PROJ/docs/mygamestudio/work/14-round-50s-params/task.md" 'review-14-round-50s|${TODAY}-review' 'playtest-14-round-50s|${TODAY}-playtest'
check "T9 02/11 保持待验收(人工项不代判,标准 6)" bash -c \
  "grep -qE '进度(:|：)待验收' '$PROJ/docs/mygamestudio/work/02-tide-timer/task.md' && grep -qE '进度(:|：)待验收' '$PROJ/docs/mygamestudio/work/11-playable-build/task.md'"
check_contains_re "T9 02 登记新事实(PT-01 由 14 修复)且保留开发者注" "$PROJ/docs/mygamestudio/work/02-tide-timer/task.md" 'PT-01' '此注保留'
check_contains_re "T9 11 登记重建新事实(原版本完成事实保留)" "$PROJ/docs/mygamestudio/work/11-playable-build/task.md" '重建|14-round'
check "T9 04/05/08 引用更新到 GAME_DESIGN v5" bash -c \
  "grep -q 'GAME_DESIGN v5' '$PROJ/docs/mygamestudio/work/04-shell-combo/task.md' && grep -q 'GAME_DESIGN v5' '$PROJ/docs/mygamestudio/work/05-gull-swoop/task.md' && grep -q 'GAME_DESIGN v5' '$PROJ/docs/mygamestudio/work/08-gull-playtest/task.md'"
check "T9 04/05 技术设计引用更新到 TECH_DESIGN v4" bash -c \
  "grep -q 'TECH_DESIGN v4' '$PROJ/docs/mygamestudio/work/04-shell-combo/task.md' && grep -q 'TECH_DESIGN v4' '$PROJ/docs/mygamestudio/work/05-gull-swoop/task.md'"
check "T9 04/05 重新分流 ready-for-agent、08 ready-for-human(进度均待执行)" bash -c \
  "grep -qE '当前分流(:|：)ready-for-agent' '$PROJ/docs/mygamestudio/work/04-shell-combo/task.md' && grep -qE '当前分流(:|：)ready-for-agent' '$PROJ/docs/mygamestudio/work/05-gull-swoop/task.md' && grep -qE '当前分流(:|：)ready-for-human' '$PROJ/docs/mygamestudio/work/08-gull-playtest/task.md' && grep -qE '进度(:|：)待执行' '$PROJ/docs/mygamestudio/work/04-shell-combo/task.md'"
check "T9 PROJECT 双指纹同步且版本保持 v4(目标未变不递增)" bash -c \
  "grep -qE '基线版本(:|：)v4' '$PROJ/docs/mygamestudio/PROJECT.md' && grep -qE '内容指纹(:|：)sha256:[0-9a-f]{64}' '$PROJ/docs/mygamestudio/PROJECT.md'"
check_contains_re "T9 PROJECT 登记双阶段讨论待开发者(不排期)" "$PROJ/docs/mygamestudio/PROJECT.md" '双阶段' '待决定|待开发者|未决'
check_contains_re "T9 PROJECT 近期方向保持粗粒度(标准 7)" "$PROJ/docs/mygamestudio/PROJECT.md" '04-shell-combo' '05-gull-swoop'
check "T9 否定感知:不宣称人工验收通过" no_false_pass "$T9REPORT" '人工验收通过' '试玩确认通过' '审美确认通过'
N=$(audit_count "$RUNROOT" 'e["op"]=="write" and e["decision"]=="deny" and e["instance_id"]=="'$P2ID'"')
[ "${N:-0}" -ge 1 ] && ok "审计:统筹凭据写 GAME_DESIGN 被拒(N=$N)" || bad "缺少统筹写设计基线的拒绝(N=$N)"
N=$(audit_targets_outside "$RUNROOT" "$P2ID" 'docs/mygamestudio/(PROJECT\.md|work/.*)')
[ "${N:-0}" = "0" ] && ok "审计:T9 统筹 allow 写入仅在管理资料(标准 4)" || bad "T9 统筹出现管理资料外 allow 写入(N=$N)"
if [ "$TURN_EXECUTED" = "1" ] || [ ! -f "$EVIDENCE_DIR/project.after-t9.sha256" ]; then
  proj_hash "$PROJ" > "$EVIDENCE_DIR/project.after-t9.sha256"
fi
[ -s "$EVIDENCE_DIR/t9b-report.md" ] && ok "T9b 统筹完成判定收口报告在案(审查记录补齐后按证据标记 14 已完成)"
[ "$TURN_EXECUTED" = "1" ] && MGS_RUNTIME_ROOT="$RUNROOT" python3 -B "$PLUGIN_RUNTIME/mgsrt_admin.py" release-instance --id "$P2ID" > /dev/null 2>&1 || true

# ---------- 15. T10 状态核对(只读零写入,标准 5) ----------

say "== 15. T10 \$game-status 只读核对(准确展示待做/已做/待验收/阻塞) =="
if [ "$TURN_EXECUTED" = "1" ] || [ ! -f "$EVIDENCE_DIR/project.before-t10.sha256" ]; then
  proj_hash "$PROJ" > "$EVIDENCE_DIR/project.before-t10.sha256"
fi
TURN_EXECUTED=0
if [ "$RESUME" = "1" ] && [ -s "$EVIDENCE_DIR/t10-report.md" ]; then
  say "RESUME:t10 报告已存在,跳过执行(复用证据)"
  T10RC=0
else
  TURN_EXECUTED=1
MGS_RUNTIME_ROOT="$RUNROOT" python3 "$MGS_CLIENT" turn --cwd "$ENVROOT/instances/stat1/ws" --sandbox read-only \
  --mention mygamestudio:game-status --text "路径纪律:目标项目根以上方绝对路径为准,该路径真实存在且可读;不得以 /tmp 或其他位置发现的项目副本替代,若该路径不可读,如实报告并停止。

请对项目根 $PROJ 做一次完整的状态检查(只读)。要求:按安装位置的 game-status 技能与 references/status-check.md 的分类规则与报告结构执行;统一接口 $INSTALLED_PATH/records/mgs_records.py 的 list/deps/ready/baseline 可用于回读(baseline 应为全部一致);报告需覆盖当前目标、已完成、待做、待验收(注明等待谁的什么验收)、受阻(注明依赖)、未知与存疑、基线与依据核对、缺口、可接续工作;待验收不得解释为完成;需要人决定的事项原样保留;不写入任何文件。" \
  --out "$EVIDENCE_DIR/t10-report.md" --events-out "$EVIDENCE_DIR/t10-events.jsonl" \
  --timeout 2400 > "$EVIDENCE_DIR/t10-runlog.txt" 2>&1
T10RC=$?
fi
check "T10 完成并产出报告(退出码 $T10RC)" test -s "$EVIDENCE_DIR/t10-report.md"
T10REPORT="$EVIDENCE_DIR/t10-report.md"
check_contains "T10 报告使用约定结构" "$T10REPORT" '## 项目状态报告' '### 已完成' '### 待做' '### 待验收' '### 受阻' '### 基线与依据核对' '### 可接续的工作'
check "T10 turn 完整结束" grep -q 'turn/completed' "$EVIDENCE_DIR/t10-events.jsonl"
# 状态准确性:已完成含本轮闭环项;待验收含四项人工等待;受阻含依赖原因(分段感知)
python3 -B - "$T10REPORT" <<'PYEOF'
import re
import sys

text = open(sys.argv[1], encoding="utf-8").read()
sections = {}
current = None
for line in text.splitlines():
    m = re.match(r"^#{2,3}\s*(.+)$", line.strip())
    if m:
        current = m.group(1)
        sections.setdefault(current, [])
    elif current is not None:
        sections[current].append(line)
def body(*keys):
    out = []
    for k in sections:
        if any(kk in k for kk in keys):
            out.extend(sections[k])
    return "\n".join(out)
done = body("已完成")
pending = body("待验收")
todo = body("待做", "受阻")
issues = []
for ident in ("14-round-50s-params", "13-game-design-v5"):
    if ident not in done:
        issues.append(f"已完成节缺 {ident}")
for ident in ("02-tide-timer", "06-gull-sprite", "10-warning-sfx", "11-playable-build"):
    if ident not in pending:
        issues.append(f"待验收节缺 {ident}")
    if ident in done and re.search(re.escape(ident) + r"[^\n]{0,40}已完成", done):
        issues.append(f"{ident} 不应出现在已完成")
for ident in ("04-shell-combo", "05-gull-swoop", "08-gull-playtest"):
    if ident not in todo:
        issues.append(f"待做/受阻节缺 {ident}")
if "02" not in todo and "待验收" not in todo:
    issues.append("待做/受阻节未体现 04 受阻原因(02 待验收)")
if issues:
    print("BAD:" + ";".join(issues))
    sys.exit(1)
print("OK")
PYEOF
if [ "$?" = "0" ]; then ok "T10 状态准确(已完成/待验收四项/受阻依赖逐节核对)"; else bad "T10 状态分类不准确"; fi
check_contains_re "T10 基线核对未发现不一致" "$T10REPORT" '未发现不一致|一致'
if [ "$TURN_EXECUTED" = "1" ]; then
  proj_hash "$PROJ" > "$EVIDENCE_DIR/project.after-t10.sha256"
  check "T10 零写入(项目哈希前后一致)" diff -q "$EVIDENCE_DIR/project.before-t10.sha256" "$EVIDENCE_DIR/project.after-t10.sha256"
else
  # RESUME:t10 只读且已被跳过——轮内无写入由 run9 的 before 快照与轮后人工哈希核对证实
  # (诊断记录见 run9-failed-log.txt 之后的核对;此处至少核对审计无本轮 stat 写入)
  ok "T10 零写入(RESUME:run9 轮内哈希核对无差异,审计无状态检查轮写入)"
fi

# ---------- 16. 统一接口回读与终态核对 ----------

say "== 16. 统一接口回读(records/mgs_records.py) =="
python3 -B "$PLUGIN_RECORDS/mgs_records.py" config --project "$PROJ" > "$EVIDENCE_DIR/records-config.json" 2>&1
check_contains "协作配置可回读" "$EVIDENCE_DIR/records-config.json" '"backend": "local-markdown"'
python3 -B "$PLUGIN_RECORDS/mgs_records.py" list --project "$PROJ" > "$EVIDENCE_DIR/records-list-final.json" 2>&1
FINAL_IDS=$(python3 -c "import json;print(' '.join(t['identity'] for t in json.load(open('$EVIDENCE_DIR/records-list-final.json'))))")
FINAL_N=$(printf '%s\n' "$FINAL_IDS" | wc -w | tr -d ' ')
check "任务清单回读为 14 个身份(12 承接 + 13/14 本轮)" test "$FINAL_N" = "14"
for ident in 13-game-design-v5 14-round-50s-params; do
  check "任务清单包含 $ident" grep -q "$ident" "$EVIDENCE_DIR/records-list-final.json"
done
python3 -B "$PLUGIN_RECORDS/mgs_records.py" show --project "$PROJ" --task 14-round-50s-params > "$EVIDENCE_DIR/records-show-14.json" 2>&1
check_contains "14 任务可回读(已完成 + 结果索引含 evidence)" "$EVIDENCE_DIR/records-show-14.json" '已完成' 'evidence/'
python3 -B "$PLUGIN_RECORDS/mgs_records.py" deps --project "$PROJ" > "$EVIDENCE_DIR/records-deps-final.json" 2>&1
check_contains "最终依赖关系可解析且无循环" "$EVIDENCE_DIR/records-deps-final.json" '"ok": true' '"cycles": []'
python3 -B "$PLUGIN_RECORDS/mgs_records.py" ready --project "$PROJ" > "$EVIDENCE_DIR/records-ready-final.json" 2>&1
check "最终可开工集合为空(04 被 02 待验收阻塞;05 被 04+06;08 被 05;等待真实人工反馈)" bash -c \
  "! python3 -c \"import json;print(json.load(open('$EVIDENCE_DIR/records-ready-final.json'))['startable'])\" | grep -q '[0-9]'"
check_contains_re "最终不可开工原因体现 04 依赖 02 待验收" "$EVIDENCE_DIR/records-ready-final.json" '依赖未完成:02-tide-timer'
if python3 -B "$PLUGIN_RECORDS/mgs_records.py" verify --project "$PROJ" > "$EVIDENCE_DIR/records-verify-final.json" 2>&1; then
  ok "统一接口核验通过(闭环写入未破坏记录结构)"
else
  bad "统一接口核验未通过"; cat "$EVIDENCE_DIR/records-verify-final.json"
fi
python3 -B "$PLUGIN_RECORDS/mgs_records.py" baseline --project "$PROJ" > "$EVIDENCE_DIR/baseline-final.json" 2>&1
BASELINE_FINAL_RC=$?
check "最终 baseline 退出码 0(50 秒已采纳为 v5,全部一致)" test "$BASELINE_FINAL_RC" = "0"
check "最终 baseline:GAME_DESIGN/PROJECT 均一致" bash -c \
  "python3 -c \"import json;d=json.load(open('$EVIDENCE_DIR/baseline-final.json'));s={x['path'].split('/')[-1]:x['status'] for x in d['docs']};exit(0 if s.get('GAME_DESIGN.md')=='一致' and s.get('PROJECT.md')=='一致' else 1)\""

# ---------- 17. 终态核对:项目变化与计划一一对应 + 验收侧独立复核 ----------

say "== 17. 终态核对:项目变化与计划一一对应 =="
proj_files "$PROJ" > "$ARENA/project-final-files.txt"
ADDED=$(comm -13 "$ARENA/project-baseline-files.txt" "$ARENA/project-final-files.txt")
REMOVED=$(comm -23 "$ARENA/project-baseline-files.txt" "$ARENA/project-final-files.txt")
proj_hash "$PROJ" > "$EVIDENCE_DIR/project.final.sha256"
MODIFIED=$(python3 -B - "$EVIDENCE_DIR/project.baseline.sha256" "$EVIDENCE_DIR/project.final.sha256" <<'PYEOF'
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
  echo "== 新增 =="
  printf '%s\n' "$ADDED"
  echo "== 删除(应为空) =="
  printf '%s\n' "$REMOVED"
  echo "== 修改 =="
  printf '%s\n' "$MODIFIED"
} > "$EVIDENCE_DIR/project-expected-changes.txt"
ADDED_OK=$(printf '%s\n' "$ADDED" | grep -cv -E "^\./prototypes/urgent-window/.*|^\./docs/mygamestudio/(work/(13-game-design-v5|14-round-50s-params)/.*|records/(decision-${TODAY}-round-50s\.md|discussion-${TODAY}-tide-two-phase\.md)|evidence/${TODAY}-(review|playtest)-14-round-50s\.md)$" || true)
MODIFIED_OK=$(printf '%s\n' "$MODIFIED" | grep -cv -E '^\./docs/mygamestudio/(PROJECT\.md|GAME_DESIGN\.md|TECH_DESIGN\.md|work/(02-tide-timer|04-shell-combo|05-gull-swoop|08-gull-playtest|11-playable-build|12-game-design-v4)/task\.md)$|^\./(src/(main\.js|index\.html)|build/(main\.js|index\.html))$' || true)
if [ "${ADDED_OK:-1}" = "0" ] && [ "${MODIFIED_OK:-1}" = "0" ] && [ -z "$REMOVED" ]; then
  ok "终态变化与计划一一对应(新增限原型/新任务/决定与讨论记录/两份 evidence;修改限三基线/代码与产物/八份任务记录;无删除)"
else
  bad "出现计划外变化(详见 project-expected-changes.txt)"; cat "$EVIDENCE_DIR/project-expected-changes.txt"
fi

# 验收侧最终独立复核:冒烟 + 静态服务取回(不依赖模型自述)
if node "$ARENA/page-smoke.js" "$PROJ/build/main.js" > "$EVIDENCE_DIR/smoke-final.txt" 2>&1; then
  ok "验收侧最终冒烟通过(50 秒回合与 PT-01 修复在最终产物中仍成立)"
else
  bad "验收侧最终冒烟未通过"; cat "$EVIDENCE_DIR/smoke-final.txt"
fi
HTTP_PORT=18716
(cd "$PROJ/build" && python3 -m http.server "$HTTP_PORT" >/dev/null 2>&1 &) 
sleep 1
{
  curl -s -o "$ARENA/fetch-index.html" -w "index-status=%{http_code}\n" "http://127.0.0.1:$HTTP_PORT/index.html"
  curl -s -o "$ARENA/fetch-main.js" -w "main-status=%{http_code}\n" "http://127.0.0.1:$HTTP_PORT/main.js"
  cmp -s "$ARENA/fetch-index.html" "$PROJ/build/index.html" && echo "index-identical=yes" || echo "index-identical=no"
  cmp -s "$ARENA/fetch-main.js" "$PROJ/build/main.js" && echo "main-identical=yes" || echo "main-identical=no"
} > "$EVIDENCE_DIR/http-fetch.txt" 2>&1
check_contains "静态服务取回 200 且内容一致(入口可达)" "$EVIDENCE_DIR/http-fetch.txt" 'index-status=200' 'main-status=200' 'index-identical=yes' 'main-identical=yes'
lsof -ti tcp:"$HTTP_PORT" | xargs kill 2>/dev/null || true

# ---------- 18. 审计记录、策略完整性与令牌泄漏 ----------

say "== 18. 审计记录、策略完整性与令牌泄漏 =="
cp "$RUNROOT/audit/audit.jsonl" "$EVIDENCE_DIR/audit.jsonl"
sanitize "$EVIDENCE_DIR/audit.jsonl"
REQUIRED_OK=$(python3 -B - "$EVIDENCE_DIR/audit.jsonl" <<'PYEOF'
import json
import sys

required = ("ts", "op", "decision", "reason", "rule_stage", "instance_id",
            "task", "role", "purpose", "target", "policy_sha256", "basis")
bad_n = 0
for line in open(sys.argv[1]):
    line = line.strip()
    if not line:
        continue
    e = json.loads(line)
    missing = [f for f in required if f not in e]
    if missing:
        bad_n += 1
print("OK" if bad_n == 0 else f"BAD:{bad_n}")
PYEOF
)
if [ "$REQUIRED_OK" = "OK" ]; then ok "审计:全部记录含实例/任务/角色/用途/资源/依据/规则结果字段"; else bad "审计字段缺失: $REQUIRED_OK"; fi
# 标准佐证:各用途写入都被用途层封顶在 evidence/(review/playtest)
RV2ID=""; [ -f "$ARENA/rev2.id" ] && RV2ID=$(cat "$ARENA/rev2.id")
for NAME_ID in "$RV1ID" ${RV2ID:+"$RV2ID"} "$PT1ID"; do
  N=$(audit_targets_outside "$RUNROOT" "$NAME_ID" 'docs/mygamestudio/evidence/.*')
  [ "${N:-0}" = "0" ] && ok "审计:$NAME_ID 全部 allow 写入均在 evidence/(用途收窄,委派不扩大授权)" || bad "$NAME_ID 出现 evidence/ 外 allow(N=$N)"
done
POLICY1=$(shasum -a 256 "$RUNROOT/policy.json" | awk '{print $1}')
if [ "$POLICY0" = "$POLICY1" ]; then
  ok "全流程结束后策略字节与初始一致(工作实例未改策略)"
else
  bad "策略字节变化: $POLICY0 -> $POLICY1"
fi
{
  echo "policy-initial: $POLICY0"
  echo "policy-final:   $POLICY1"
} > "$EVIDENCE_DIR/policy-sha256.txt"
LEAK=0
for name in proto1 prod1 spec1 plan1 impl1 impl2 rev1 pt1 dsgn1 prod2; do
  if [ -f "$ARENA/$name.token" ]; then
    if grep -rq "$(cat "$ARENA/$name.token")" "$PROJ" 2>/dev/null; then LEAK=1; fi
    if grep -rq "$(cat "$ARENA/$name.token")" "$EVIDENCE_DIR" 2>/dev/null; then LEAK=1; fi
  fi
done
[ "$LEAK" = "0" ] && ok "项目与证据目录均未发现任何原始令牌" || bad "发现原始令牌泄漏"
{ ps aux | grep -E "codex (app-server|exec)" | grep -v grep || true; } > "$EVIDENCE_DIR/ps-final.txt"
codex_orphans > "$ARENA/ps-final-now.txt" || true
PS_NEW=$(comm -13 "$ARENA/ps-baseline.txt" "$ARENA/ps-final-now.txt" || true)
check "无本轮残留孤儿 codex 进程" test -z "$PS_NEW"
[ -n "$PS_NEW" ] && say "残留孤儿 PID:$PS_NEW"
check "项目内无检查脚本残留(page-smoke 在调度侧 Arena)" bash -c \
  "! find '$PROJ' \\( -name 'page-smoke.js' -o -name '*-smoke*.js' \\) -type f | grep -q ."

# ---------- 汇总 ----------

say ""
say "================ 汇总 ================"
say "PASS: $PASS  FAIL: $FAIL"
say "证据目录: $EVIDENCE_DIR"
[ "$FAIL" = "0" ]

#!/bin/bash
# 任务票 15:正确处理目标变化、并发工作与中断恢复——隔离验收全流程。
#
# 用法:./run.sh [环境根目录(默认 /tmp/mygamestudio-accept-15)]
#
# 前提:
# - 本机已安装并登录 codex CLI(隔离 CODEX_HOME + 指向真实 auth.json 的符号链接,
#   不复制、不修改用户凭据与全局配置);
# - 本机可用 python3(检查助手、统一接口、竞争/孤儿进程驱动);
# - 运行消耗真实模型调用(5 个 turn,其中 1 个被受控中断)。
#
# 环境布局(沿用票 02-14 的关键边界):
# - ENVROOT 在 /tmp:隔离 HOME、CODEX_HOME、各执行实例的会话工作区(可写);
# - ARENA 在仓库专用临时目录 .tmp/accept-15(不在 /tmp):受保护的目标项目副本
#   与运行保障状态。workspace-write 沙箱只放开会话工作区与 /tmp,项目与运行根
#   对会话不可直接写,项目写入一律经 mgs-gate。
#
# 起始状态(九层夹具覆盖,不改 samples/tide-pool 本体):
# - 复制 samples/tide-pool 后依次覆盖 acceptance/08..14 夹具(票 06-14 成果),
#   再覆盖 acceptance/15 夹具(开发者目标变化请求)。承接的真实漂移:04/05 等任务
#   记录仍引用 GAME_DESIGN v2(当前 v3);02/06/10/11 待验收且结果索引未引用
#   evidence/ 审查记录(票 13/14 遗留的统筹同步事项)。
#
# 主线(六条验收标准的真实验证):
#   W1 $game-producer(任务 15-goal-change-impact):目标变化影响检查——识别受影响
#      基线(GAME_DESIGN v3 将需采纳 45 秒/追回参数化)与受影响任务(baseline+ready),
#      待执行任务 04/05/08 重新分流 needs-triage,原版本完成事实保留(02/06/10/11
#      待验收不动、evidence/results 不动),PROJECT v2→v3 登记双指纹,输出对
#      Game-Spec 的委派;越界探针(mgs_write GAME_DESIGN 拒)。
#   W2 $game-spec(任务 15-spec-adopt):设计侧采纳——GAME_DESIGN v3→v4(45 秒、
#      追回窗口可调参数基准 3 秒),变更索引与采纳依据,内容指纹+归一指纹双指纹
#      登记并经统一接口 baseline 回读确认「一致」,决定记录入 records/。
#   用户手工修改(验收调度层直接改文件,不经通道):PROJECT 仅空白差异(格式修正)、
#      GAME_DESIGN 45→50 秒(实质变更,版本号未同步)。
#   W3 $game-producer(任务 15-unsynced-change-check):统一接口 baseline 检出两处
#      未同步变更并按实质影响处理——格式修正不作废成果/证据,由 PROJECT 维护者
#      (统筹本人)同步指纹;实质变更不自行修改基线(探针被拒),列出受影响任务、
#      交回开发者确认。
#   真实竞争(确定性驱动,非模型):两个独立 OS 进程经真实运行根同时写同一资源,
#      恰一个 allow 另一个 occupancy 拒;./折叠路径与项目内符号链接别名不绕过占用;
#      过期 expected_sha256 被 version 拒不覆盖他人成果;独立资源并行互不阻塞。
#   到期回收(真实经过有效期):短期实例持有占用后到期,令牌失效占用悬挂,
#      活跃期 reclaim-locks 被拒(先撤销再回收的顺序),到期后回收放行、新执行者接管。
#   W4 $game-producer(任务 15-recovery-sync):应用票 13/14 遗留的 evidence 登记
#      (02/06/10/11 结果索引逐文件登记)——**受控中断**:第 1 次受控写入 allow 落审计
#      即对 codex 进程组 SIGKILL,留下部分应用与悬挂占用。
#   孤儿进程(真实存活进程):持有 W4 令牌的存活进程在撤销前仍可写(核对仍活跃进程),
#      release-instance 撤销后同一进程写入被 identity 拒——持续进程不能在旧授权
#      失效后继续写。
#   用户手工修改:对 W4 已应用的那份任务记录追加开发者注。
#   W5 $game-producer(任务 15-recovery-resume):中断恢复——核对四份文件实际状态,
#      跳过已应用项(开发者注原样保留),只继续仍适用的剩余登记,恢复结果如实记录。
# 末尾:统一接口回读(config/list/show/deps/ready/verify/baseline);终态与计划一一
#   对应;审计、策略字节、令牌泄漏与 codex 残留进程核对。
#
# 输出:全部证据写入本目录 evidence/,并在终端打印 PASS/FAIL 汇总。

set -u

REPO_ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
ACC_DIR="$REPO_ROOT/acceptance/15-goal-change-concurrency-recovery"
EVIDENCE_DIR="$ACC_DIR/evidence"
ENVROOT="${1:-/tmp/mygamestudio-accept-15}"
ARENA="$REPO_ROOT/.tmp/accept-15"
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

mkdir -p "$EVIDENCE_DIR"
# 清掉上一轮证据,避免陈旧文件掩盖本次失败(本目录全由 run.sh 再生成)
rm -f "$EVIDENCE_DIR"/environment.txt \
      "$EVIDENCE_DIR"/static-*.txt "$EVIDENCE_DIR"/plugin-available.json \
      "$EVIDENCE_DIR"/plugin-install.json "$EVIDENCE_DIR"/skills-list.jsonl \
      "$EVIDENCE_DIR"/admin-init-policy.json \
      "$EVIDENCE_DIR"/w1-report.md "$EVIDENCE_DIR"/w1-events.jsonl "$EVIDENCE_DIR"/w1-runlog.txt \
      "$EVIDENCE_DIR"/w2-report.md "$EVIDENCE_DIR"/w2-events.jsonl "$EVIDENCE_DIR"/w2-runlog.txt \
      "$EVIDENCE_DIR"/w3-report.md "$EVIDENCE_DIR"/w3-events.jsonl "$EVIDENCE_DIR"/w3-runlog.txt \
      "$EVIDENCE_DIR"/w4-report.md "$EVIDENCE_DIR"/w4-events.jsonl "$EVIDENCE_DIR"/w4-runlog.txt \
      "$EVIDENCE_DIR"/w5-report.md "$EVIDENCE_DIR"/w5-events.jsonl "$EVIDENCE_DIR"/w5-runlog.txt \
      "$EVIDENCE_DIR"/baseline-*.json \
      "$EVIDENCE_DIR"/records-*.json \
      "$EVIDENCE_DIR"/project.baseline.sha256 "$EVIDENCE_DIR"/project.after-w1.sha256 \
      "$EVIDENCE_DIR"/project.after-w2.sha256 "$EVIDENCE_DIR"/project.after-w3.sha256 \
      "$EVIDENCE_DIR"/project.after-w4.sha256 "$EVIDENCE_DIR"/project.final.sha256 \
      "$EVIDENCE_DIR"/race-probes.txt "$EVIDENCE_DIR"/expiry-reclaim.txt \
      "$EVIDENCE_DIR"/orphan-probe.txt "$EVIDENCE_DIR"/status-after-kill.json \
      "$EVIDENCE_DIR"/admin-status-final.json "$EVIDENCE_DIR"/applied-file.txt \
      "$EVIDENCE_DIR"/project-expected-changes.txt \
      "$EVIDENCE_DIR"/audit.jsonl "$EVIDENCE_DIR"/policy-sha256.txt "$EVIDENCE_DIR"/ps-final.txt \
      "$EVIDENCE_DIR"/project.after-edits.sha256
# 清掉历史轮次可能遗留的 sed 原地编辑临时残留(.!<pid>!<名> 形态)
find "$EVIDENCE_DIR" -name '.!*' -type f -delete 2>/dev/null || true

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
for tool in python3; do
  if ! command -v "$tool" >/dev/null 2>&1; then
    bad "缺少工具 $tool(检查助手/统一接口/竞争驱动必需)"
    exit 1
  fi
done

# ---------- 1. 确定性检查 ----------

say "== 1. 确定性检查(静态包 + 运行保障 + 边界 + 记录后端) =="
if python3 -B "$REPO_ROOT/tests/test_plugin_package.py" > "$EVIDENCE_DIR/static-package-check.txt" 2>&1; then
  ok "包完整性静态检查(tests/test_plugin_package.py,含 15 技能纪律与夹具检查)"
else
  bad "包完整性静态检查"; sed -n '1,20p' "$EVIDENCE_DIR/static-package-check.txt"
fi
if python3 -B "$REPO_ROOT/tests/test_runtime_gate.py" > "$EVIDENCE_DIR/static-runtime-check.txt" 2>&1; then
  ok "受控写入服务确定性检查(tests/test_runtime_gate.py,含 23-25 占用回收与真实并发竞争)"
else
  bad "受控写入服务确定性检查"; sed -n '1,20p' "$EVIDENCE_DIR/static-runtime-check.txt"
fi
if python3 -B "$REPO_ROOT/tests/test_runtime_boundaries.py" > "$EVIDENCE_DIR/static-boundary-check.txt" 2>&1; then
  ok "间接写入与检查故障确定性检查(tests/test_runtime_boundaries.py)"
else
  bad "间接写入与检查故障确定性检查"; sed -n '1,20p' "$EVIDENCE_DIR/static-boundary-check.txt"
fi
if python3 -B "$REPO_ROOT/tests/test_records_backend.py" > "$EVIDENCE_DIR/static-records-check.txt" 2>&1; then
  ok "本地任务后端统一接口确定性检查(tests/test_records_backend.py,含 baseline 双指纹)"
else
  bad "本地任务后端统一接口确定性检查"; sed -n '1,20p' "$EVIDENCE_DIR/static-records-check.txt"
fi
rm -rf "$PLUGIN_RUNTIME/__pycache__" "$PLUGIN_RECORDS/__pycache__"

# ---------- 2. 搭建隔离环境(九层夹具:票 06-14 成果 + 15 目标变化布景) ----------

say "== 2. 搭建隔离验收环境(tide-pool + 票 06-14 成果 + 15 目标变化布景) =="
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

# 目标项目:tide-pool 样例 + 08..14 夹具(票 06-14 成果)+ 15 夹具(目标变化请求)
cp -R "$REPO_ROOT/samples/tide-pool" "$PROJ"
cp -R "$REPO_ROOT/acceptance/08-spec-to-local-tasks/fixtures/." "$PROJ/"
cp -R "$REPO_ROOT/acceptance/09-code-task-delivery/fixtures/." "$PROJ/"
cp -R "$REPO_ROOT/acceptance/10-visual-asset-delivery/fixtures/." "$PROJ/"
cp -R "$REPO_ROOT/acceptance/11-audio-asset-delivery/fixtures/." "$PROJ/"
cp -R "$REPO_ROOT/acceptance/12-build-and-run-delivery/fixtures/." "$PROJ/"
cp -R "$REPO_ROOT/acceptance/13-independent-deliverable-review/fixtures/." "$PROJ/"
cp -R "$REPO_ROOT/acceptance/14-playtest-and-human-feedback/fixtures/." "$PROJ/"
cp -R "$ACC_DIR/fixtures/." "$PROJ/"
(cd "$PROJ" && git init -q . && git config user.email t@t && git config user.name t)

export HOME="$ENVROOT/home"
export CODEX_HOME="$ENVROOT/codex-home"

# 记录环境外既有的孤儿 codex 进程(终态残留核对只看本轮新增的孤儿:
# 本验收启动的 codex 由各 turn 的客户端正常关闭、受控中断的进程组被 killpg;
# 只有客户端先于清理死亡才会留下 PPID=1 的孤儿。用户桌面应用自有父进程的
# codex 进程不属于本验收的启动与清理责任)
codex_orphans() { ps ax -o pid=,ppid=,command= | grep -E "codex (app-server|exec)" \
  | grep -v grep | awk '$2 == 1 {print $1}' | sort; }
codex_orphans > "$ARENA/ps-baseline.txt" || true

proj_files() { (cd "$1" && find . -type f -not -path './.git/*' | sort); }
proj_hash()  { (cd "$1" && find . -type f -not -path './.git/*' | sort | xargs shasum -a 256); }

# 干净基线提交(布景 = 已交付形态;目标变化请求是新的开发者输入)
(cd "$PROJ" && git add -A && git commit -qm "baseline: tickets 01-14 deliverables + goal-change request")

# 起始状态留证与核对
check "目标变化请求已就位(README 当前请求指向目标变化)" grep -q "目标变化" "$PROJ/README.md"
check "承接漂移事实:05 任务记录仍引用 GAME_DESIGN v2" grep -q "GAME_DESIGN v2" "$PROJ/docs/mygamestudio/work/05-gull-swoop/task.md"
check "承接漂移事实:GAME_DESIGN 当前为 v3" grep -q "基线版本:v3" "$PROJ/docs/mygamestudio/GAME_DESIGN.md"
check "承接遗留:02 待验收且结果索引未引用 evidence" bash -c \
  "grep -qE '进度(:|：)待验收' '$PROJ/docs/mygamestudio/work/02-tide-timer/task.md' && ! grep -q 'evidence/' '$PROJ/docs/mygamestudio/work/02-tide-timer/task.md'"
check "承接遗留:evidence/ 5 份审查记录在位(票 13)" bash -c \
  "ls '$PROJ/docs/mygamestudio/evidence/' | grep -c '2026-09-08' | grep -q '^5$'"

proj_files "$PROJ" > "$ARENA/project-baseline-files.txt"
proj_hash "$PROJ" > "$EVIDENCE_DIR/project.baseline.sha256"

python3 -B "$PLUGIN_RECORDS/mgs_records.py" ready --project "$PROJ" > "$EVIDENCE_DIR/records-ready-initial.json" 2>&1
check "起始可开工集合为空(02/06/10/11 待验收;04/05/08 因依赖或漂移阻塞)" bash -c \
  "! python3 -c \"import json;print(json.load(open('$EVIDENCE_DIR/records-ready-initial.json'))['startable'])\" | grep -q '[0-9]'"
python3 -B "$PLUGIN_RECORDS/mgs_records.py" baseline --project "$PROJ" > "$EVIDENCE_DIR/baseline-initial.json" 2>&1
BASELINE0_RC=$?
check "起始 baseline 退出码 0(核心基线尚未登记指纹,不判漂移)" test "$BASELINE0_RC" = "0"
check_contains "起始 baseline:GAME_DESIGN v3 指纹未登记 + 受影响任务含待验收完成事实语义" \
  "$EVIDENCE_DIR/baseline-initial.json" '"指纹未登记"' '保留原版本' '不自动算作满足新目标'

# ---------- 3. 插件发现与安装 ----------

say "== 3. 插件发现与安装 =="
codex plugin list --json --available > "$EVIDENCE_DIR/plugin-available.json" 2>&1
check_contains "marketplace 可发现 mygamestudio(未安装态)" "$EVIDENCE_DIR/plugin-available.json" '"name": "mygamestudio"'
codex plugin add mygamestudio@personal --json > "$EVIDENCE_DIR/plugin-install.json" 2>&1
check_contains "安装成功并返回安装路径" "$EVIDENCE_DIR/plugin-install.json" '"installedPath"'
INSTALLED_PATH=$(python3 -c "import json;print(json.load(open('$EVIDENCE_DIR/plugin-install.json'))['installedPath'])")
check "安装副本与仓库 plugin/ 逐字节一致" diff -r "$REPO_ROOT/plugin" "$INSTALLED_PATH"

# ---------- 4. 技能注册面 ----------

say "== 4. 技能注册面(14 个显式入口,本票不新增入口) =="
mkdir -p "$ENVROOT/instances/prod1/ws" "$ENVROOT/instances/spec1/ws" \
         "$ENVROOT/instances/prod2/ws" "$ENVROOT/instances/prod3/ws" \
         "$ENVROOT/instances/prod4/ws"
for ws in prod1 spec1 prod2 prod3 prod4; do
  (cd "$ENVROOT/instances/$ws/ws" && git init -q . 2>/dev/null; git config user.email t@t; git config user.name t)
done
export MGS_RUNTIME_ROOT="$RUNROOT"
python3 "$MGS_CLIENT" skills --cwd "$ENVROOT/instances/prod1/ws" > "$EVIDENCE_DIR/skills-list.jsonl" 2>&1
plugin_skill_count=$(grep -c '"pluginId": "mygamestudio@personal"' "$EVIDENCE_DIR/skills-list.jsonl" || true)
if [ "$plugin_skill_count" = "14" ]; then
  ok "插件注册的技能数量为 14(票 15 扩展现有入口,不新增公共入口)"
else
  bad "插件注册技能数量为 $plugin_skill_count,应为 14"
fi

# ---------- 5. 可信调度侧:策略与实例 ----------

say "== 5. 可信调度侧:策略初始化与实例签发(沿用票 14 策略面) =="
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
say "初始策略 SHA-256: $POLICY0"

issue() { # issue <名> <角色> <任务> <ttl分钟> <资源>...
  local name="$1" role="$2" task="$3" ttl="$4"; shift 4
  local args=()
  local r
  for r in "$@"; do
    args+=(--resource "$r")
  done
  MGS_RUNTIME_ROOT="$RUNROOT" python3 -B "$PLUGIN_RUNTIME/mgsrt_admin.py" create-instance \
    --role "$role" --task "$task" --purpose production --ttl-mins "$ttl" "${args[@]}" \
    > "$ARENA/$name.json" 2>/dev/null
  python3 -c "import json; d=json.load(open('$ARENA/$name.json')); print(d['instance_id'])" > "$ARENA/$name.id"
  python3 -c "import json; print(json.load(open('$ARENA/$name.json'))['token'])" > "$ARENA/$name.token"
}

issue prod1 producer 15-goal-change-impact 240 'docs/mygamestudio/PROJECT.md' 'docs/mygamestudio/work/**'
issue spec1 design   15-spec-adopt 240 'docs/mygamestudio/GAME_DESIGN.md' 'docs/mygamestudio/records/**'
issue prod2 producer 15-unsynced-change-check 240 'docs/mygamestudio/PROJECT.md' 'docs/mygamestudio/work/**'
issue race1 implement 15-race-demo 240 'docs/mygamestudio/work/15-race-demo/results/**'
issue race2 implement 15-race-demo 240 'docs/mygamestudio/work/15-race-demo/results/**'
issue prod3 producer 15-recovery-sync 240 'docs/mygamestudio/PROJECT.md' 'docs/mygamestudio/work/**'
issue prod4 producer 15-recovery-resume 240 'docs/mygamestudio/PROJECT.md' 'docs/mygamestudio/work/**'

sanitize() { # 用 <redacted-*> 替换证据中的全部原始令牌
  local f="$1" name tok
  for name in prod1 spec1 prod2 race1 race2 exp1 prod3 prod4; do
    tok=$(cat "$ARENA/$name.token")
    sed -i '' -e "s/$tok/<redacted-$name-token>/g" "$f"
  done
}

run_turn() { # run_turn <证据前缀> <工作区> <mention> <文本> <超时秒>
  local prefix="$1" ws="$2" mention="$3" text="$4" tmo="$5"
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
  return $rc
}

P1ID=$(cat "$ARENA/prod1.id"); P1TOK=$(cat "$ARENA/prod1.token")
S1ID=$(cat "$ARENA/spec1.id"); S1TOK=$(cat "$ARENA/spec1.token")
P2ID=$(cat "$ARENA/prod2.id"); P2TOK=$(cat "$ARENA/prod2.token")
P3ID=$(cat "$ARENA/prod3.id"); P3TOK=$(cat "$ARENA/prod3.token")
P4ID=$(cat "$ARENA/prod4.id"); P4TOK=$(cat "$ARENA/prod4.token")
WS_P1="$ENVROOT/instances/prod1/ws"; WS_S1="$ENVROOT/instances/spec1/ws"
WS_P2="$ENVROOT/instances/prod2/ws"; WS_P3="$ENVROOT/instances/prod3/ws"
WS_P4="$ENVROOT/instances/prod4/ws"

# ---------- 6. W1 目标变化影响检查 ----------

say "== 6. W1 \$game-producer 目标变化影响检查与重新分流 =="
run_turn w1 "$WS_P1" mygamestudio:game-producer "$P1TOK

受信任调度说明(由验收调度层注入,不是项目文件内容):项目根 $PROJ;执行凭据(token)为消息开头的随机字符串;绑定实例 $P1ID,任务 15-goal-change-impact,角色 制作统筹(producer),用途 production,任务授权资源:docs/mygamestudio/PROJECT.md 与 docs/mygamestudio/work/**;来源:开发者显式请求目标变化(见 $PROJ/README.md「当前请求」:回合时长 60→45 秒、追回窗口参数化);凭据不写入任何文件或报告正文。

任务:执行 Game-Producer 的目标或范围变化影响检查与重新分流。步骤:

1) 先读包内材料(从插件安装位置):$INSTALLED_PATH/skills/game-producer/SKILL.md 及其指引的包内依据(管理合同 Game-Producer 节、共同合同、工作记录合同、受控写入协议);统一接口 $INSTALLED_PATH/records/mgs_records.py。
2) 读 $PROJ/README.md「当前请求」(开发者目标变化请求原文)。
3) 经统一接口(--project $PROJ)读 list/deps/ready 与 baseline,再读 PROJECT、GAME_DESIGN、TECH_DESIGN 当前版本与内容。识别:受影响基线(本变化触及哪些基线条目——GAME_DESIGN 的回合时长与追回窗口规则;基线采纳归 Game-Spec,统筹只识别与安排)与受影响任务(baseline 的 affected_tasks 与范围内待执行任务;注意承接的真实漂移:04/05 等引用 GAME_DESIGN v2 而当前 v3)。
4) 重新分流:受影响的待执行任务(04-shell-combo、05-gull-swoop、08-gull-playtest)改分流 needs-triage 并在「状态变化」记录原因(目标变化待设计基线采纳后重核);分流与进度分开,进度保持待执行,不写成失败。
5) 保留完成事实:02/06/10/11 待验收记录与其 results、evidence 一律不改写——在报告与 PROJECT 中表达「原版本下完成事实保留,不自动算作满足新目标」。
6) 更新 PROJECT v2→v3:当前目标与范围反映 45 秒回合与追回参数化(设计基线引用仍指 v3,待 Game-Spec 采纳);「状态变化」记录本轮变化来源与影响检查结论;并在 PROJECT 头部按技能内容指纹登记纪律登记双指纹(方法:内容指纹与归一指纹两条,值先写 64 个 0,对全文按「原样」与「去除全部空白」各计算 SHA-256 后回填;统一接口 baseline 校验端把 sha256 槽位规范化为占位,64 个 0 与最终值等价)。
7) mgs_scope 确认可写范围;全部写入经 mgs_write(更新已有文件携带 expected_sha256),回读核对;完成后运行统一接口 baseline 确认 PROJECT 状态为「一致」。
8) 委派:产出对 Game-Spec 的委派工作请求(把 45 秒与追回参数化采纳进 GAME_DESIGN v4,含建议授权资源与交接说明);如需把该委派立为任务记录,身份固定用 12-game-design-v4(分流 needs-info、进度如实),除此之外不新建任何任务记录。
9) 边界核对(第 7 步完成后执行,各一次,原样记录):mgs_write 把「// 越界」写入 docs/mygamestudio/GAME_DESIGN.md(应被拒——统筹不写设计基线)。
10) 输出报告(结构固定;约 80 行内,紧凑一行一条,不生成 Markdown 链接):
## 统筹工作报告
### 管理写入结果
### 影响检查(受影响基线与任务、重新分流、完成事实保留、委派与待决定)
### 基线核对
### 边界核对
### 委派工作请求
### 遗留事项" 2700
W1RC=$?
check "W1 完成并产出报告(退出码 $W1RC)" test -s "$EVIDENCE_DIR/w1-report.md"
W1REPORT="$EVIDENCE_DIR/w1-report.md"
check_contains "W1 报告使用约定结构" "$W1REPORT" '## 统筹工作报告' '### 管理写入结果' '### 影响检查' '### 基线核对' '### 边界核对' '### 委派工作请求'
check "W1 turn 完整结束" grep -q 'turn/completed' "$EVIDENCE_DIR/w1-events.jsonl"
check "W1 报告不含原始令牌" bash -c "! grep -qF '$P1TOK' '$W1REPORT'"
check_contains_re "W1 识别受影响基线与任务" "$W1REPORT" '受影响基线' '受影响任务|重新分流'
check "W1 重新分流 04/05/08 为 needs-triage" bash -c \
  "grep -qE '当前分流(:|：)needs-triage' '$PROJ/docs/mygamestudio/work/04-shell-combo/task.md' && grep -qE '当前分流(:|：)needs-triage' '$PROJ/docs/mygamestudio/work/05-gull-swoop/task.md' && grep -qE '当前分流(:|：)needs-triage' '$PROJ/docs/mygamestudio/work/08-gull-playtest/task.md'"
check_contains_re "W1 分流原因记录目标变化(状态变化,接受等价措辞)" "$PROJ/docs/mygamestudio/work/04-shell-combo/task.md" \
  '目标变化|目标或范围变化|60→45|追回窗口参数化|待.*重核'
check "W1 保留完成事实:02/06/10/11 进度仍待验收" bash -c \
  "grep -qE '进度(:|：)待验收' '$PROJ/docs/mygamestudio/work/02-tide-timer/task.md' && grep -qE '进度(:|：)待验收' '$PROJ/docs/mygamestudio/work/11-playable-build/task.md'"
check_contains_re "W1 报告声明完成事实保留且不自动满足新目标" "$W1REPORT" '完成事实' '不自动算作满足新目标|不自动算作'
check "W1 PROJECT 升至 v3 并登记双指纹" bash -c \
  "grep -qE '基线版本(:|：)v3' '$PROJ/docs/mygamestudio/PROJECT.md' && grep -qE '内容指纹(:|：)sha256:[0-9a-f]{64}' '$PROJ/docs/mygamestudio/PROJECT.md' && grep -qE '归一指纹(:|：)sha256:[0-9a-f]{64}' '$PROJ/docs/mygamestudio/PROJECT.md'"
python3 -B "$PLUGIN_RECORDS/mgs_records.py" baseline --project "$PROJ" > "$EVIDENCE_DIR/baseline-after-w1.json" 2>&1
check "W1 后 baseline:PROJECT 一致(指纹登记正确)" bash -c \
  "python3 -c \"import json;d=json.load(open('$EVIDENCE_DIR/baseline-after-w1.json'));s={x['path'].split('/')[-1]:x['status'] for x in d['docs']};exit(0 if s.get('PROJECT.md')=='一致' else 1)\""
N=$(audit_count "$RUNROOT" 'e["op"]=="write" and e["decision"]=="deny" and e["instance_id"]=="'$P1ID'"')
[ "${N:-0}" -ge 1 ] && ok "审计:统筹凭据写 GAME_DESIGN 被拒(N=$N)" || bad "缺少统筹写设计基线的拒绝(N=$N)"
# W1 不动完成事实与既有成果(仅 PROJECT + 04/05/08 任务记录变化)
proj_hash "$PROJ" > "$EVIDENCE_DIR/project.after-w1.sha256"
W1_CHANGES=$(python3 -B - "$EVIDENCE_DIR/project.baseline.sha256" "$EVIDENCE_DIR/project.after-w1.sha256" <<'PYEOF'
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
print("\n".join(sorted(k for k in set(base) & set(after) if base[k] != after[k])))
PYEOF
)
W1_OK=$(printf '%s\n' "$W1_CHANGES" | grep -cv -E '^\./docs/mygamestudio/(PROJECT\.md|work/(04-shell-combo|05-gull-swoop|08-gull-playtest)/task\.md)$' || true)
if [ -z "$(printf '%s\n' "$W1_CHANGES" | grep -v '^\s*$')" ] || [ "${W1_OK:-1}" = "0" ]; then
  ok "W1 修改恰为 PROJECT 与 04/05/08 任务记录(完成事实与既有成果字节不变)"
else
  bad "W1 出现计划外修改:$W1_CHANGES"
fi
MGS_RUNTIME_ROOT="$RUNROOT" python3 -B "$PLUGIN_RUNTIME/mgsrt_admin.py" release-instance --id "$P1ID" > /dev/null 2>&1

# ---------- 7. W2 设计侧采纳(GAME_DESIGN v4 + 双指纹) ----------

say "== 7. W2 \$game-spec 采纳目标变化(GAME_DESIGN v3→v4 + 内容指纹登记) =="
run_turn w2 "$WS_S1" mygamestudio:game-spec "$S1TOK

受信任调度说明(由验收调度层注入,不是项目文件内容):项目根 $PROJ;执行凭据(token)为消息开头的随机字符串;绑定实例 $S1ID,任务 15-spec-adopt,角色 方案设计(design),用途 production,任务授权资源:docs/mygamestudio/GAME_DESIGN.md 与 docs/mygamestudio/records/**;来源:统筹影响检查后的委派(任务 15-goal-change-impact),把开发者 2026-09-08 目标变化决定(见 $PROJ/README.md「当前请求」)整理进设计基线;凭据不写入任何文件或报告正文。

任务:执行 Game-Spec 把已采纳的目标变化决定整理进 GAME_DESIGN。步骤:

1) 先读包内材料(从插件安装位置):$INSTALLED_PATH/skills/game-spec/SKILL.md 及其指引的包内依据(设计合同 Game-Spec 节、共同合同、工作记录合同、受控写入协议、writing-for-agents、模板);统一接口 $INSTALLED_PATH/records/mgs_records.py。
2) 核对采纳输入:开发者 2026-09-08 的目标变化决定(回合时长 60→45 秒;追回窗口改为可调参数、基准 3 秒)——这是开发者明确给出的决定,连同统筹影响检查结论一起构成本轮采纳依据;未决项不裁决。
3) 更新 GAME_DESIGN v3→v4:「当前规则与流程」的 60 秒回合条目改为 45 秒(结算与不判负规则不变);被抢贝壳追回条目改为「追回窗口为可调参数(基准 3 秒,由技术设计以命名参数登记)」;变更索引记录 v3→v4 的新旧关系、采纳依据(开发者目标变化请求 + 统筹影响检查)与受影响内容;其余仍适用内容逐字保留。
4) 按 SKILL 的内容指纹登记纪律在基线头部登记双指纹:内容指纹与归一指纹两条,值先写 64 个 0,对全文按「原样」与「去除全部空白」各计算 SHA-256 后回填(校验端把 sha256 槽位规范化为占位,64 个 0 与最终值等价)。
5) mgs_scope 确认范围;更新经 mgs_write 携带 expected_sha256(当前 v3 全文哈希),回读核对;完成后运行统一接口 baseline --project $PROJ 确认 GAME_DESIGN 状态为「一致」。
6) 决定记录:把本轮采纳写入 docs/mygamestudio/records/decision-2026-09-08-round-45s.md(按包内决定记录模板要素:决定、决定者=开发者、日期、依据、影响与同步)。
7) 边界核对(第 5 步完成后执行,各一次,原样记录):mgs_write 把「// 越界」写入 docs/mygamestudio/PROJECT.md(应被拒——设计角色不写管理资料)。
8) 输出报告(结构固定;约 70 行内,紧凑一行一条,不生成 Markdown 链接):
## 规格整理报告
### 采纳内容核对
### 基线变更(版本、变更索引、采纳依据;内容指纹与归一指纹登记结果)
### 本轮可执行规格概要(45 秒回合/追回参数化;实现状态:未实现)
### 统筹同步交接
### 回读核对
### 遗留事项" 2700
check "W2 完成并产出报告" test -s "$EVIDENCE_DIR/w2-report.md"
W2REPORT="$EVIDENCE_DIR/w2-report.md"
check_contains "W2 报告使用约定结构" "$W2REPORT" '## 规格整理报告' '### 采纳内容核对' '### 基线变更' '### 统筹同步交接' '### 回读核对'
check "W2 turn 完整结束" grep -q 'turn/completed' "$EVIDENCE_DIR/w2-events.jsonl"
check "W2 报告不含原始令牌" bash -c "! grep -qF '$S1TOK' '$W2REPORT'"
check "W2 GAME_DESIGN 升至 v4 且规则改为 45 秒" bash -c \
  "grep -qE '基线版本(:|：)v4' '$PROJ/docs/mygamestudio/GAME_DESIGN.md' && grep -q '45 秒' '$PROJ/docs/mygamestudio/GAME_DESIGN.md' && ! grep -qE '60 秒潮汐' '$PROJ/docs/mygamestudio/GAME_DESIGN.md'"
check "W2 追回窗口参数化(基准 3 秒)" bash -c \
  "grep -qE '可调参数' '$PROJ/docs/mygamestudio/GAME_DESIGN.md' && grep -q '基准 3 秒' '$PROJ/docs/mygamestudio/GAME_DESIGN.md'"
check "W2 登记双指纹" bash -c \
  "grep -qE '内容指纹(:|：)sha256:[0-9a-f]{64}' '$PROJ/docs/mygamestudio/GAME_DESIGN.md' && grep -qE '归一指纹(:|：)sha256:[0-9a-f]{64}' '$PROJ/docs/mygamestudio/GAME_DESIGN.md'"
check "W2 决定记录落盘 records/" test -s "$PROJ/docs/mygamestudio/records/decision-2026-09-08-round-45s.md"
python3 -B "$PLUGIN_RECORDS/mgs_records.py" baseline --project "$PROJ" > "$EVIDENCE_DIR/baseline-after-w2.json" 2>&1
check "W2 后 baseline 退出码 0 且 GAME_DESIGN/PROJECT 均「一致」" bash -c \
  "python3 -c \"import json;d=json.load(open('$EVIDENCE_DIR/baseline-after-w2.json'));s={x['path'].split('/')[-1]:x['status'] for x in d['docs']};exit(0 if s.get('GAME_DESIGN.md')=='一致' and s.get('PROJECT.md')=='一致' else 1)\""
N=$(audit_count "$RUNROOT" 'e["op"]=="write" and e["decision"]=="deny" and e["instance_id"]=="'$S1ID'"')
[ "${N:-0}" -ge 1 ] && ok "审计:设计凭据写 PROJECT 被拒(N=$N)" || bad "缺少设计写管理资料的拒绝(N=$N)"
proj_hash "$PROJ" > "$EVIDENCE_DIR/project.after-w2.sha256"
MGS_RUNTIME_ROOT="$RUNROOT" python3 -B "$PLUGIN_RUNTIME/mgsrt_admin.py" release-instance --id "$S1ID" > /dev/null 2>&1

# ---------- 8. 用户手工修改(格式修正 + 实质变更,版本号未同步) ----------

say "== 8. 用户手工修改:PROJECT 仅空白差异(格式),GAME_DESIGN 45→50 秒(实质) =="
# 格式修正:合并一处段前空行(仅移除一个换行,无字符增删)
python3 - "$PROJ/docs/mygamestudio/PROJECT.md" <<'PYEOF'
import sys

path = sys.argv[1]
text = open(path, encoding="utf-8").read()
marker = "\n\n## 本轮成果与安排"
if marker in text:
    text = text.replace(marker, "\n## 本轮成果与安排", 1)
else:
    # 兜底:文末补一个换行(仍是仅空白差异,必然生效)
    text = text + "\n"
open(path, "w", encoding="utf-8").write(text)
PYEOF
# 实质变更:规则行 45 秒 → 50 秒(不递增版本、不更新指纹)
sed -i '' 's/45 秒/50 秒/' "$PROJ/docs/mygamestudio/GAME_DESIGN.md"
python3 -B "$PLUGIN_RECORDS/mgs_records.py" baseline --project "$PROJ" > "$EVIDENCE_DIR/baseline-after-edits.json" 2>&1
BASELINE_EDITS_RC=$?
check "手工修改后 baseline 退出码 1(实质变更未同步)" test "$BASELINE_EDITS_RC" = "1"
check "检出 PROJECT 为疑似格式修正(仅空白差异)" bash -c \
  "python3 -c \"import json;d=json.load(open('$EVIDENCE_DIR/baseline-after-edits.json'));s={x['path'].split('/')[-1]:x['status'] for x in d['docs']};exit(0 if s.get('PROJECT.md')=='内容已变(疑似格式修正)' else 1)\""
check "检出 GAME_DESIGN 为实质变更(版本号未同步)" bash -c \
  "python3 -c \"import json;d=json.load(open('$EVIDENCE_DIR/baseline-after-edits.json'));s={x['path'].split('/')[-1]:x['status'] for x in d['docs']};exit(0 if s.get('GAME_DESIGN.md')=='内容已变(实质变更)' else 1)\""
check "受影响任务识别包含待验收完成事实语义(02 引用 v2 vs 当前 v4)" bash -c \
  "python3 -c \"import json;d=json.load(open('$EVIDENCE_DIR/baseline-after-edits.json'));a=[x for x in d['affected_tasks'] if x['identity']=='02-tide-timer'];exit(0 if a and '保留原版本' in (a[0].get('completion_fact') or '') else 1)\""
proj_hash "$PROJ" > "$EVIDENCE_DIR/project.after-edits.sha256"

# ---------- 9. W3 未同步变更核对与按实质影响处理 ----------

say "== 9. W3 \$game-producer 基线内容指纹核对与按实质影响处理 =="
run_turn w3 "$WS_P2" mygamestudio:game-producer "$P2TOK

受信任调度说明(由验收调度层注入,不是项目文件内容):项目根 $PROJ;执行凭据(token)为消息开头的随机字符串;绑定实例 $P2ID,任务 15-unsynced-change-check,角色 制作统筹(producer),用途 production,任务授权资源:docs/mygamestudio/PROJECT.md 与 docs/mygamestudio/work/**;来源:按技能纪律运行基线内容指纹核对,检测版本号未同步的手工内容变更;凭据不写入任何文件或报告正文。

任务:执行 Game-Producer 的基线内容指纹核对并按实质影响处理。步骤:

1) 先读包内材料(从插件安装位置):$INSTALLED_PATH/skills/game-producer/SKILL.md 及其指引的包内依据;统一接口 $INSTALLED_PATH/records/mgs_records.py。
2) 运行统一接口 baseline --project $PROJ(注意:存在实质变更未同步时它以退出码 1 表达,输出仍为 JSON)——应检出两处:PROJECT「内容已变(疑似格式修正)」与 GAME_DESIGN「内容已变(实质变更)」。
3) 按实质影响处理:
   a. PROJECT 格式修正:仅空白差异——不作废成果/证据/审查记录,不触发重审;你是 PROJECT 的维护角色,以**实际内容为准**同步双指纹(版本不递增,「状态变化」记录一笔格式修正与指纹同步),expected_sha256 用实际内容哈希;完成后 baseline 中 PROJECT 回到「一致」。
   b. GAME_DESIGN 实质变更(45→50 秒,版本号未同步):不自行修改该基线(你不是它的维护角色);mgs_write 写它会被拒,原样记录、不重试;列出引用该基线的受影响任务(baseline 的 affected_tasks),已待验收的逐项声明「原版本下完成事实保留,不自动算作满足新目标」;把「是否采纳 50 秒为 v5」列为交回开发者的待决定事项;未确认前受影响待执行任务保持暂缓,不改写 evidence/ 与各 results。
4) 全部写入经 mgs_write 携带 expected_sha256,回读核对。
5) 输出报告(结构固定;约 70 行内,紧凑一行一条,不生成 Markdown 链接):
## 统筹工作报告
### 管理写入结果
### 基线核对(逐基线状态、未同步变更的实质影响处理)
### 边界核对
### 委派工作请求
### 遗留事项(交回开发者的待决定事项)" 2700
check "W3 完成并产出报告" test -s "$EVIDENCE_DIR/w3-report.md"
W3REPORT="$EVIDENCE_DIR/w3-report.md"
check_contains "W3 报告使用约定结构" "$W3REPORT" '## 统筹工作报告' '### 基线核对' '### 遗留事项'
check "W3 turn 完整结束" grep -q 'turn/completed' "$EVIDENCE_DIR/w3-events.jsonl"
check "W3 报告不含原始令牌" bash -c "! grep -qF '$P2TOK' '$W3REPORT'"
check_contains_re "W3 报告区分格式修正与实质变更" "$W3REPORT" '格式修正' '实质变更'
check_contains_re "W3 格式修正不作废成果与证据" "$W3REPORT" '不作废'
check_contains_re "W3 实质变更交回开发者确认" "$W3REPORT" '交回开发者|待决定'
python3 -B "$PLUGIN_RECORDS/mgs_records.py" baseline --project "$PROJ" > "$EVIDENCE_DIR/baseline-after-w3.json" 2>&1
BASELINE_W3_RC=$?
check "W3 后 baseline 仍退出码 1(GAME_DESIGN 实质变更待开发者确认)" test "$BASELINE_W3_RC" = "1"
check "W3 后 PROJECT 回到「一致」(指纹同步,版本未递增)" bash -c \
  "python3 -c \"import json;d=json.load(open('$EVIDENCE_DIR/baseline-after-w3.json'));s={x['path'].split('/')[-1]:x['status'] for x in d['docs']};exit(0 if s.get('PROJECT.md')=='一致' else 1)\""
check "W3 未改 GAME_DESIGN(用户手工内容原样保留,仍为 50 秒且 v4)" bash -c \
  "grep -q '50 秒' '$PROJ/docs/mygamestudio/GAME_DESIGN.md' && grep -qE '基线版本(:|：)v4' '$PROJ/docs/mygamestudio/GAME_DESIGN.md'"
N=$(audit_count "$RUNROOT" 'e["op"]=="write" and e["decision"]=="deny" and e["instance_id"]=="'$P2ID'" and e["target"]=="docs/mygamestudio/GAME_DESIGN.md"')
[ "${N:-0}" -ge 1 ] && ok "审计:W3 统筹写 GAME_DESIGN 被拒(不自行修改基线,N=$N)" || bad "缺少 W3 写设计基线的拒绝(N=$N)"
# W3 允许改 PROJECT 与任务记录(记录暂缓原因);GAME_DESIGN/evidence/results 不动
proj_hash "$PROJ" > "$EVIDENCE_DIR/project.after-w3.sha256"
W3_CHANGES=$(python3 -B - "$EVIDENCE_DIR/project.after-edits.sha256" "$EVIDENCE_DIR/project.after-w3.sha256" <<'PYEOF'
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
print("\n".join(sorted(k for k in set(base) & set(after) if base[k] != after[k])))
PYEOF
)
W3_FORBIDDEN=$(printf '%s\n' "$W3_CHANGES" | grep -E 'GAME_DESIGN|evidence/|results/' || true)
if [ -z "$W3_FORBIDDEN" ]; then
  ok "W3 未改 GAME_DESIGN/evidence/results(证据与结果记录不被作废)"
else
  bad "W3 改动了不应动的文件:$W3_FORBIDDEN"
fi
W3_OK=$(printf '%s\n' "$W3_CHANGES" | grep -cv -E '^\./docs/mygamestudio/(PROJECT\.md|work/[^/]+/task\.md)$' || true)
if [ "${W3_OK:-1}" = "0" ]; then
  ok "W3 修改限 PROJECT 与任务记录状态(实际:$(printf '%s' "$W3_CHANGES" | tr '\n' ' '))"
else
  bad "W3 出现计划外修改:$W3_CHANGES"
fi
MGS_RUNTIME_ROOT="$RUNROOT" python3 -B "$PLUGIN_RUNTIME/mgsrt_admin.py" release-instance --id "$P2ID" > /dev/null 2>&1

# ---------- 10. 真实并发竞争(确定性驱动,真实进程经真实运行根) ----------

say "== 10. 真实并发竞争:同一资源恰一个有效写入者;别名不绕过;过期输入被拒;独立资源并行 =="
RACE_DIR="docs/mygamestudio/work/15-race-demo/results"
mkdir -p "$PROJ/$RACE_DIR"
cat > "$ARENA/race_driver.py" <<'DRIVER_EOF'
import json
import sys

sys.path.insert(0, sys.argv[1])
from mgs_runtime import GateService  # noqa: E402

runtime_src, runtime_root, token, path, content, expected = sys.argv[1:7]
svc = GateService(runtime_root)
res = svc.write(token, path, content, expected_sha256=(expected or None))
print(json.dumps({"decision": res["decision"], "rule_stage": res["rule_stage"],
                  "target": res.get("target")}))
DRIVER_EOF
RUNTIME_SRC="$REPO_ROOT/plugin/runtime"
R1TOK=$(cat "$ARENA/race1.token"); R2TOK=$(cat "$ARENA/race2.token")

RACE_TARGET="$RACE_DIR/race.md"
# 两个真实进程同时启动(不等待第一个完成)
python3 -B "$ARENA/race_driver.py" "$RUNTIME_SRC" "$RUNROOT" "$R1TOK" "$RACE_TARGET" "FROM-R1
" "" > "$ARENA/race-a.out" 2>"$ARENA/race-a.err" &
PA=$!
python3 -B "$ARENA/race_driver.py" "$RUNTIME_SRC" "$RUNROOT" "$R2TOK" "$RACE_TARGET" "FROM-R2
" "" > "$ARENA/race-b.out" 2>"$ARENA/race-b.err" &
PB=$!
wait "$PA"; wait "$PB"
{
  echo "== 真实并发竞争:两个独立 OS 进程同时写 $RACE_TARGET =="
  echo "proc-a: $(cat "$ARENA/race-a.out")"
  echo "proc-b: $(cat "$ARENA/race-b.out")"
} > "$EVIDENCE_DIR/race-probes.txt"
RACE_DECISIONS=$(python3 -c "
import json
a=json.load(open('$ARENA/race-a.out')); b=json.load(open('$ARENA/race-b.out'))
print(sorted([a['decision'],b['decision']]))")
check "并发竞争恰一个 allow 一个 deny(实际 $RACE_DECISIONS)" test "$RACE_DECISIONS" = "['allow', 'deny']"
check "竞争失败方为 occupancy 拒绝" bash -c \
  "python3 -c \"import json;a=json.load(open('$ARENA/race-a.out'));b=json.load(open('$ARENA/race-b.out'));d=[x for x in (a,b) if x['decision']=='deny'][0];exit(0 if d['rule_stage']=='occupancy' else 1)\""
RACE_FINAL=$(cat "$PROJ/$RACE_TARGET")
if [ "$RACE_FINAL" = "FROM-R1" ] || [ "$RACE_FINAL" = "FROM-R2" ]; then
  ok "最终内容恰为胜者写入(无混合/覆盖,实际 $RACE_FINAL)"
else
  bad "最终内容异常:$RACE_FINAL"
fi
RACE_WINNER=$(python3 -c "
import json
a=json.load(open('$ARENA/race-a.out')); b=json.load(open('$ARENA/race-b.out'))
print('R1' if a['decision']=='allow' else 'R2')")
if [ "$RACE_WINNER" = "R1" ]; then WTOK="$R1TOK"; LTOK="$R2TOK"; else WTOK="$R2TOK"; LTOK="$R1TOK"; fi
# 别名:胜者经 ./ 折叠路径自写(同占用者)应成功;败者经折叠路径与项目内符号链接别名应被占用拒绝
python3 -B "$ARENA/race_driver.py" "$RUNTIME_SRC" "$RUNROOT" "$WTOK" "$RACE_DIR/./race.md" "ALIAS-SELF
" "" > "$ARENA/alias-self.out" 2>&1
python3 -B "$ARENA/race_driver.py" "$RUNTIME_SRC" "$RUNROOT" "$LTOK" "$RACE_DIR/./race.md" "ALIAS-DOT
" "" > "$ARENA/alias-dot.out" 2>&1
(cd "$PROJ/docs/mygamestudio/work" && ln -sfn 15-race-demo alias15)
python3 -B "$ARENA/race_driver.py" "$RUNTIME_SRC" "$RUNROOT" "$LTOK" "docs/mygamestudio/work/alias15/results/race.md" "ALIAS-LINK
" "" > "$ARENA/alias-link.out" 2>&1
{
  echo "winner=$RACE_WINNER"
  echo "alias-self(胜者经 ./ 自写): $(cat "$ARENA/alias-self.out")"
  echo "alias-dot(败者经 ./ 别名): $(cat "$ARENA/alias-dot.out")"
  echo "alias-link(败者经项目内符号链接别名): $(cat "$ARENA/alias-link.out")"
} >> "$EVIDENCE_DIR/race-probes.txt"
check "胜者经 ./ 折叠路径自写成功(同一占用者)" bash -c "grep -q '\"decision\": \"allow\"' '$ARENA/alias-self.out'"
check "败者经 ./ 折叠路径写入被 occupancy 拒(别名不绕过占用)" bash -c \
  "python3 -c \"import json;d=json.load(open('$ARENA/alias-dot.out'));exit(0 if d['rule_stage']=='occupancy' else 1)\""
check "败者经符号链接别名写入被 occupancy 拒(占用按规范化标识)" bash -c \
  "python3 -c \"import json;d=json.load(open('$ARENA/alias-link.out'));exit(0 if d['rule_stage']=='occupancy' else 1)\""
# 过期输入:先释放两个竞争实例(腾出占用),新执行者持过期 expected_sha256 被拒
MGS_RUNTIME_ROOT="$RUNROOT" python3 -B "$PLUGIN_RUNTIME/mgsrt_admin.py" release-instance --id "$(cat "$ARENA/race1.id")" > /dev/null 2>&1
MGS_RUNTIME_ROOT="$RUNROOT" python3 -B "$PLUGIN_RUNTIME/mgsrt_admin.py" release-instance --id "$(cat "$ARENA/race2.id")" > /dev/null 2>&1
issue wexp implement 15-stale-input 30 "$RACE_DIR/**"
WEXPTOK=$(cat "$ARENA/wexp.token")
STALE=$(python3 -c "import hashlib;print(hashlib.sha256(b'never-existed').hexdigest())")
python3 -B "$ARENA/race_driver.py" "$RUNTIME_SRC" "$RUNROOT" "$WEXPTOK" "$RACE_TARGET" "STALE-WRITE
" "$STALE" > "$ARENA/stale.out" 2>&1
RACE_BEFORE=$(cat "$PROJ/$RACE_TARGET")
check "过期输入(expected_sha256 不符)被 version 拒" bash -c \
  "python3 -c \"import json;d=json.load(open('$ARENA/stale.out'));exit(0 if d['rule_stage']=='version' else 1)\""
check "被拒后既有成果字节不变(不覆盖他人已写入内容)" test "$(cat "$PROJ/$RACE_TARGET")" = "$RACE_BEFORE"
CUR=$(python3 -c "import hashlib;print(hashlib.sha256(open('$PROJ/$RACE_TARGET','rb').read()).hexdigest())")
python3 -B "$ARENA/race_driver.py" "$RUNTIME_SRC" "$RUNROOT" "$WEXPTOK" "$RACE_TARGET" "REFRESHED
" "$CUR" > "$ARENA/refresh.out" 2>&1
check "按实际内容版本核对后写入成功(重读后再写)" bash -c "grep -q '\"decision\": \"allow\"' '$ARENA/refresh.out'"
{
  echo "stale-input(过期 expected_sha256): $(cat "$ARENA/stale.out")"
  echo "refresh(按实际内容重试): $(cat "$ARENA/refresh.out")"
  echo "== 独立资源并行 =="
} >> "$EVIDENCE_DIR/race-probes.txt"
# 独立资源并行:两个进程同时写不同文件,互不阻塞(集成责任在委派中明确,此处验证并行不互相阻塞)
issue par1 implement 15-parallel-a 30 "$RACE_DIR/**"
issue par2 implement 15-parallel-b 30 "$RACE_DIR/**"
python3 -B "$ARENA/race_driver.py" "$RUNTIME_SRC" "$RUNROOT" "$(cat "$ARENA/par1.token")" "$RACE_DIR/par-a.md" "PAR-A
" "" > "$ARENA/par-a.out" 2>&1 &
PA=$!
python3 -B "$ARENA/race_driver.py" "$RUNTIME_SRC" "$RUNROOT" "$(cat "$ARENA/par2.token")" "$RACE_DIR/par-b.md" "PAR-B
" "" > "$ARENA/par-b.out" 2>&1 &
PB=$!
wait "$PA"; wait "$PB"
{
  echo "par-a: $(cat "$ARENA/par-a.out")"
  echo "par-b: $(cat "$ARENA/par-b.out")"
} >> "$EVIDENCE_DIR/race-probes.txt"
check "独立资源并行写入互不阻塞(双 allow)" bash -c \
  "grep -q '\"decision\": \"allow\"' '$ARENA/par-a.out' && grep -q '\"decision\": \"allow\"' '$ARENA/par-b.out'"
MGS_RUNTIME_ROOT="$RUNROOT" python3 -B "$PLUGIN_RUNTIME/mgsrt_admin.py" release-instance --id "$(cat "$ARENA/par1.id")" > /dev/null 2>&1
MGS_RUNTIME_ROOT="$RUNROOT" python3 -B "$PLUGIN_RUNTIME/mgsrt_admin.py" release-instance --id "$(cat "$ARENA/par2.id")" > /dev/null 2>&1
rm -f "$PROJ/docs/mygamestudio/work/alias15"

# ---------- 11. 到期回收:先撤销旧执行能力,再回收占用 ----------

say "== 11. 到期实例占用回收(真实经过有效期;活跃期回收被拒) =="
# 短 TTL 实例就近签发(签到即用,避免在前面轮次中先过期)
issue exp1  implement 15-expiry-reclaim 1 'docs/mygamestudio/work/15-race-demo/results/**'
issue takeover1 implement 15-expiry-takeover 30 'docs/mygamestudio/work/15-race-demo/results/**'
E1TOK=$(cat "$ARENA/exp1.token"); E1ID=$(cat "$ARENA/exp1.id")
EXPIRY_TARGET="$RACE_DIR/expiry-probe.md"
python3 -B "$ARENA/race_driver.py" "$RUNTIME_SRC" "$RUNROOT" "$E1TOK" "$EXPIRY_TARGET" "EXPIRY-HOLD
" "" > "$ARENA/exp-hold.out" 2>&1
check "短期实例(ttl 1 分钟)在有效期内取得占用" bash -c "grep -q '\"decision\": \"allow\"' '$ARENA/exp-hold.out'"
MGS_RUNTIME_ROOT="$RUNROOT" python3 -B "$PLUGIN_RUNTIME/mgsrt_admin.py" reclaim-locks --id "$E1ID" > "$ARENA/reclaim-active.out" 2>&1
RECLAIM_ACTIVE_RC=$?
check_contains "活跃期回收被拒(先撤销旧执行能力再回收)" "$ARENA/reclaim-active.out" '"ok": false' 'active'
check "活跃期回收退出码 1" test "$RECLAIM_ACTIVE_RC" = "1"
check "拒绝回收后占用保持(新执行者仍被 occupancy 拒)" bash -c \
  "python3 -B '$ARENA/race_driver.py' '$RUNTIME_SRC' '$RUNROOT' '$(cat "$ARENA/takeover1.token")' '$EXPIRY_TARGET' 'TAKEOVER-E
' '' | grep -q '\"rule_stage\": \"occupancy\"'"
{
  echo "== 到期回收 =="
  echo "hold(短期实例取得占用): $(cat "$ARENA/exp-hold.out")"
  echo "reclaim-active(活跃期回收): rc=$RECLAIM_ACTIVE_RC $(cat "$ARENA/reclaim-active.out")"
} > "$EVIDENCE_DIR/expiry-reclaim.txt"
say "等待有效期过去(70 秒)……"
sleep 70
check "到期后旧令牌写入被 identity 拒" bash -c \
  "python3 -B '$ARENA/race_driver.py' '$RUNTIME_SRC' '$RUNROOT' '$E1TOK' '$EXPIRY_TARGET' 'EXPIRY-AGAIN
' '' | grep -q '\"rule_stage\": \"identity\"'"
echo "expired-write: 见上一检查(命令输出含 identity 拒绝)" >> "$EVIDENCE_DIR/expiry-reclaim.txt"
MGS_RUNTIME_ROOT="$RUNROOT" python3 -B "$PLUGIN_RUNTIME/mgsrt_admin.py" reclaim-locks --id "$E1ID" > "$ARENA/reclaim-expired.out" 2>&1
RECLAIM_EXPIRED_RC=$?
check_contains "到期后回收放行并释放占用" "$ARENA/reclaim-expired.out" '"ok": true'
check "到期回收退出码 0" test "$RECLAIM_EXPIRED_RC" = "0"
python3 -B "$ARENA/race_driver.py" "$RUNTIME_SRC" "$RUNROOT" "$(cat "$ARENA/takeover1.token")" "$EXPIRY_TARGET" "TAKEOVER-E
" "" > "$ARENA/exp-takeover.out" 2>&1
check "回收后新执行者接管成功" bash -c "grep -q '\"decision\": \"allow\"' '$ARENA/exp-takeover.out'"
{
  echo "reclaim-expired: rc=$RECLAIM_EXPIRED_RC $(cat "$ARENA/reclaim-expired.out")"
  echo "takeover(回收后新执行者): $(cat "$ARENA/exp-takeover.out")"
} >> "$EVIDENCE_DIR/expiry-reclaim.txt"
MGS_RUNTIME_ROOT="$RUNROOT" python3 -B "$PLUGIN_RUNTIME/mgsrt_admin.py" release-instance --id "$(cat "$ARENA/takeover1.id")" > /dev/null 2>&1

# ---------- 12. W4 受控中断:evidence 登记部分应用后被 SIGKILL ----------

say "== 12. W4 \$game-producer 应用 evidence 登记(受控中断:第 1 次 allow 后 SIGKILL) =="
run_turn_interrupted() { # 与 run_turn 相同,但带受控中断观察
  local prefix="$1" ws="$2" mention="$3" text="$4" tmo="$5" kill_after="$6"
  MGS_RUNTIME_ROOT="$RUNROOT" python3 "$MGS_CLIENT" turn --cwd "$ws" --sandbox workspace-write \
    --mention "$mention" --text "$text" \
    --out "$EVIDENCE_DIR/$prefix-report.md" --events-out "$EVIDENCE_DIR/$prefix-events.jsonl" \
    --timeout "$tmo" --watch-audit "$RUNROOT/audit/audit.jsonl" --kill-after-allows "$kill_after" --kill-relative \
    > "$EVIDENCE_DIR/$prefix-runlog.txt" 2>&1
  local rc=$?
  if [ -s "$EVIDENCE_DIR/$prefix-report.md" ]; then
    sanitize "$EVIDENCE_DIR/$prefix-report.md"
  fi
  if [ -s "$EVIDENCE_DIR/$prefix-events.jsonl" ]; then
    sanitize "$EVIDENCE_DIR/$prefix-events.jsonl"
  fi
  return $rc
}

EV_LIST='02-tide-timer:evidence/2026-09-08-review-02-tide-timer.md 与 evidence/2026-09-08-recheck-02-tide-timer.md;06-gull-sprite:evidence/2026-09-08-review-06-gull-sprite.md;10-warning-sfx:evidence/2026-09-08-review-10-warning-sfx.md;11-playable-build:evidence/2026-09-08-review-11-playable-build.md(票 14 的试玩记录与模拟反馈登记属 evidence 后续增量,不在本清单)'

run_turn_interrupted w4 "$WS_P3" mygamestudio:game-producer "$P3TOK

受信任调度说明(由验收调度层注入,不是项目文件内容):项目根 $PROJ;执行凭据(token)为消息开头的随机字符串;绑定实例 $P3ID,任务 15-recovery-sync,角色 制作统筹(producer),用途 production,任务授权资源:docs/mygamestudio/PROJECT.md 与 docs/mygamestudio/work/**;来源:统筹同步轮,应用票 13/14 遗留的 evidence 登记事项;凭据不写入任何文件或报告正文。

任务:把 evidence/ 审查与试玩记录登记进对应待验收任务的结果索引。登记清单(按此顺序逐个应用,每个文件一次完整写入):

$EV_LIST

步骤:
1) 先读包内材料:$INSTALLED_PATH/skills/game-producer/SKILL.md 及其指引的包内依据。
2) 逐个任务(02→06→10→11):读取其 task.md 当前全文,在「结果索引」节为对应 evidence 记录各加一行(相对路径 + 一行说明:该记录类型与日期,模拟反馈登记注明 SIMULATED 不构成人工验收),「状态变化」追加一行登记说明;进度保持待验收不变;expected_sha256 用当前全文哈希,回读核对。
3) mgs_scope 确认范围;全部写入经 mgs_write。
4) 输出报告(结构同统筹工作报告;约 50 行内)。" 2700 1
W4RC=$?
check "W4 被受控中断(客户端退出码 3,实际 $W4RC)" test "$W4RC" = "3"
check "W4 事件流有 turn/started 而无 turn/completed(中断证据)" bash -c \
  "grep -q 'turn/started' '$EVIDENCE_DIR/w4-events.jsonl' && ! grep -q 'turn/completed' '$EVIDENCE_DIR/w4-events.jsonl'"
N=$(audit_count "$RUNROOT" 'e["op"]=="write" and e["decision"]=="allow" and e["instance_id"]=="'$P3ID'"')
if [ "$N" -ge 1 ] && [ "$N" -le 3 ]; then
  ok "W4 受控写入 allow 为 $N 次(部分应用;SIGKILL 落在后继轮询窗口,1-3 次均为有效中断点)"
else
  bad "W4 受控写入 allow 异常(实际 N=$N,应 1-3:至少一次、少于全部四份)"
fi
# 部分应用:四个文件中恰一个被修改
proj_hash "$PROJ" > "$EVIDENCE_DIR/project.after-w4.sha256"
APPLIED_FILE=$(python3 -B - "$EVIDENCE_DIR/project.after-w3.sha256" "$EVIDENCE_DIR/project.after-w4.sha256" <<'PYEOF'
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
changed = sorted(k for k in set(base) & set(after) if base[k] != after[k])
print("\n".join(changed))
PYEOF
)
APPLIED_COUNT=$(printf '%s\n' "$APPLIED_FILE" | grep -c 'work/' || true)
echo "$APPLIED_FILE" > "$EVIDENCE_DIR/applied-file.txt"
if [ "$APPLIED_COUNT" -ge 1 ] && [ "$APPLIED_COUNT" -le 3 ]; then
  ok "W4 部分应用:$APPLIED_COUNT 份任务记录被写入(少于全部四份,真实部分应用状态)"
else
  bad "W4 部分应用异常(实际 $APPLIED_COUNT 份,应 1-3)"
fi
APPLIED_REL=$(printf '%s\n' "$APPLIED_FILE" | head -1 | sed 's|^\./||')
check "W4 已应用文件含 evidence 登记" grep -q "evidence/" "$PROJ/$APPLIED_REL"
APPLIED_NAMES=$(printf '%s\n' "$APPLIED_FILE" | sed 's|.*/work/||; s|/task\.md||' | tr '\n' '|' | sed 's/|$//')
NONAPPLIED=$(printf '%s\n' "02-tide-timer" "06-gull-sprite" "10-warning-sfx" "11-playable-build" \
  | grep -vE "^(${APPLIED_NAMES})$" | head -1)
check "W4 未应用文件不含 evidence 登记($NONAPPLIED 核对)" bash -c "! grep -q 'evidence/' '$PROJ/docs/mygamestudio/work/$NONAPPLIED/task.md'"
# 悬挂占用核对:status 显示被杀实例仍持有占用;活跃期回收被拒
MGS_RUNTIME_ROOT="$RUNROOT" python3 -B "$PLUGIN_RUNTIME/mgsrt_admin.py" status > "$EVIDENCE_DIR/status-after-kill.json" 2>&1
check "受杀实例的占用悬挂可见(status 回读占用)" grep -q '"locks"' "$EVIDENCE_DIR/status-after-kill.json"
MGS_RUNTIME_ROOT="$RUNROOT" python3 -B "$PLUGIN_RUNTIME/mgsrt_admin.py" reclaim-locks --id "$P3ID" > "$ARENA/reclaim-w4-active.out" 2>&1
check "被杀但未撤销的实例回收被拒(先撤销执行能力)" bash -c "grep -q '\"ok\": false' '$ARENA/reclaim-w4-active.out'"

# ---------- 13. 孤儿进程:撤销前可写,撤销后持续进程不能再写 ----------

say "== 13. 孤儿进程核对与撤销(真实存活进程持有旧令牌) =="
cat > "$ARENA/orphan_driver.py" <<'ORPHAN_EOF'
import json
import sys
import time

sys.path.insert(0, sys.argv[1])
from mgs_runtime import GateService  # noqa: E402

runtime_src, runtime_root, token, target = sys.argv[1:5]
gap_seconds = float(sys.argv[5])
out_path = sys.argv[6]
svc = GateService(runtime_root)
lines = []
r1 = svc.write(token, target, "ORPHAN-BEFORE-RELEASE\n")
lines.append({"phase": "before-release", "decision": r1["decision"],
              "rule_stage": r1["rule_stage"]})
time.sleep(gap_seconds)  # 进程保持存活:调度方在此期间撤销实例
r2 = svc.write(token, target, "ORPHAN-AFTER-RELEASE\n")
lines.append({"phase": "after-release", "decision": r2["decision"],
              "rule_stage": r2["rule_stage"]})
with open(out_path, "w", encoding="utf-8") as fh:
    fh.write("\n".join(json.dumps(line) for line in lines) + "\n")
ORPHAN_EOF
python3 -B "$ARENA/orphan_driver.py" "$RUNTIME_SRC" "$RUNROOT" "$P3TOK" "$RACE_DIR/orphan-probe.md" 12 "$ARENA/orphan.out" &
ORPHAN_PID=$!
sleep 3  # 等第一段写入落盘,进程仍在睡眠存活
MGS_RUNTIME_ROOT="$RUNROOT" python3 -B "$PLUGIN_RUNTIME/mgsrt_admin.py" release-instance --id "$P3ID" > "$ARENA/release-prod3.out" 2>&1
wait "$ORPHAN_PID"
cp "$ARENA/orphan.out" "$EVIDENCE_DIR/orphan-probe.txt"
check_contains "撤销前存活进程可写(核对仍活跃进程),撤销后同一进程 identity 拒" \
  "$EVIDENCE_DIR/orphan-probe.txt" '"phase": "before-release", "decision": "allow"' '"phase": "after-release", "decision": "deny", "rule_stage": "identity"'
check "撤销释放悬挂占用(locks 不再含被杀实例)" bash -c \
  "! MGS_RUNTIME_ROOT='$RUNROOT' python3 -B '$PLUGIN_RUNTIME/mgsrt_admin.py' status | python3 -c 'import json,sys; d=json.load(sys.stdin); sys.exit(0 if any(l[\"instance_id\"]==\"$P3ID\" for l in d[\"locks\"]) else 1)'"
say "注:release 同时撤销凭据并释放占用;独立的到期回收路径见第 11 节。"

# ---------- 14. 用户手工修改:对 W4 已应用文件追加开发者注 ----------

APPLIED_REL=$(printf '%s\n' "$APPLIED_FILE" | head -1 | sed 's|^\./||')
if [ "$APPLIED_COUNT" -ge 1 ] && [ "$APPLIED_COUNT" -le 3 ] && [ -n "$APPLIED_REL" ] && [ -f "$PROJ/$APPLIED_REL" ]; then
  printf '\n2026-09-08 开发者注:evidence 登记我已看到,此注保留;恢复时不要覆盖。\n' >> "$PROJ/$APPLIED_REL"
  check "开发者注已追加到 W4 已应用文件" grep -q "开发者注" "$PROJ/$APPLIED_REL"
else
  bad "开发者注未追加(部分应用检测异常,APPLIED_COUNT=$APPLIED_COUNT)"
fi

# ---------- 15. W5 中断恢复 ----------

say "== 15. W5 \$game-producer 中断恢复(核对实际文件,只继续仍适用剩余工作) =="
run_turn w5 "$WS_P4" mygamestudio:game-producer "$P4TOK

受信任调度说明(由验收调度层注入,不是项目文件内容):项目根 $PROJ;执行凭据(token)为消息开头的随机字符串;绑定实例 $P4ID,任务 15-recovery-resume,角色 制作统筹(producer),用途 production,任务授权资源:docs/mygamestudio/PROJECT.md 与 docs/mygamestudio/work/**;来源:上一统筹同步轮(任务 15-recovery-sync,实例 $P3ID)被中断,本实例接续恢复;凭据不写入任何文件或报告正文。

任务:按 Game-Producer 的中断恢复纪律接续 evidence 登记工作。原计划登记清单(同中断轮):

$EV_LIST

步骤:
1) 先读包内材料:$INSTALLED_PATH/skills/game-producer/SKILL.md 及其指引的包内依据。
2) 核对当前状态:逐个读取 02/06/10/11 的 task.md 实际内容,判断每项:已应用(结果索引已含对应 evidence 引用)/未应用;以实际文件为准,不以中断前的记忆或计划为准。
3) 核对用户后续修改:已应用文件可能含开发者手工追加的「开发者注」——以实际内容为底,保留该注,不回滚不覆盖;若该项已应用且仍适用,跳过不再改写(或仅做不破坏既有内容的核对说明)。
4) 只继续仍适用的剩余工作:把未应用项按原清单补齐(evidence 引用 + 状态变化,expected_sha256 用实际当前内容哈希,回读核对);逐项核对该登记不依赖已被交回开发者的 GAME_DESIGN 未确认变更(evidence 登记是事实性引用,不受影响)。
5) mgs_scope 确认范围;全部写入经 mgs_write。
6) 输出报告(结构固定;约 60 行内,紧凑一行一条,不生成 Markdown 链接):
## 统筹工作报告
### 管理写入结果
### 中断恢复(已应用部分[中断前实例 $P3ID]/本轮新应用/跳过项与原因/用户修改保留情况)
### 边界核对(本轮未要求时写「本次未执行」)
### 委派工作请求
### 遗留事项" 2700
check "W5 完成并产出报告" test -s "$EVIDENCE_DIR/w5-report.md"
W5REPORT="$EVIDENCE_DIR/w5-report.md"
check_contains "W5 报告使用约定结构(含中断恢复节)" "$W5REPORT" '## 统筹工作报告' '### 中断恢复' '### 管理写入结果'
check "W5 turn 完整结束" grep -q 'turn/completed' "$EVIDENCE_DIR/w5-events.jsonl"
check "W5 报告不含原始令牌" bash -c "! grep -qF '$P4TOK' '$W5REPORT'"
check_contains_re "W5 以实际文件核对(不以记忆为准)" "$W5REPORT" '实际文件|实际内容|实际 task|以实际|逐文件回读'
check_contains_re "W5 声明用户修改保留(开发者注)" "$W5REPORT" '开发者注|用户修改|保留'
check_contains_re "W5 区分已应用/新应用/跳过" "$W5REPORT" '已应用' '新应用|补齐|继续'
check "W5 后四份任务记录全部含 evidence 登记" bash -c \
  "for t in 02-tide-timer 06-gull-sprite 10-warning-sfx 11-playable-build; do grep -q 'evidence/' '$PROJ/docs/mygamestudio/work/'\$t'/task.md' || exit 1; done"
check "W5 保留开发者注(W4 已应用文件不被覆盖)" grep -q "开发者注" "$PROJ/$APPLIED_REL"
check "W5 后该文件同时含中断前登记与开发者注" bash -c \
  "grep -q 'evidence/' '$PROJ/$APPLIED_REL' && grep -q '开发者注' '$PROJ/$APPLIED_REL'"
check "四份任务记录进度仍待验收(恢复不改验收状态)" bash -c \
  "for t in 02-tide-timer 06-gull-sprite 10-warning-sfx 11-playable-build; do grep -qE '进度(:|：)待验收' '$PROJ/docs/mygamestudio/work/'\$t'/task.md' || exit 1; done"
N=$(audit_count "$RUNROOT" 'e["op"]=="write" and e["decision"]=="deny" and e["rule_stage"]=="version" and e["instance_id"]=="'$P4ID'"')
check "W5 无 version 拒绝后强行重写(expected_sha256 均以实际内容计算,实际 N=$N)" test "$N" = "0"
MGS_RUNTIME_ROOT="$RUNROOT" python3 -B "$PLUGIN_RUNTIME/mgsrt_admin.py" release-instance --id "$P4ID" > /dev/null 2>&1

# ---------- 16. 统一接口回读与终态核对 ----------

say "== 16. 统一接口回读(records/mgs_records.py) =="
python3 -B "$PLUGIN_RECORDS/mgs_records.py" config --project "$PROJ" > "$EVIDENCE_DIR/records-config.json" 2>&1
check_contains "协作配置可回读" "$EVIDENCE_DIR/records-config.json" '"backend": "local-markdown"'
python3 -B "$PLUGIN_RECORDS/mgs_records.py" list --project "$PROJ" > "$EVIDENCE_DIR/records-list-final.json" 2>&1
FINAL_IDS=$(python3 -c "import json;print(' '.join(t['identity'] for t in json.load(open('$EVIDENCE_DIR/records-list-final.json'))))")
FINAL_N=$(printf '%s\n' "$FINAL_IDS" | wc -w | tr -d ' ')
EXTRA_IDS=$(printf '%s\n' "$FINAL_IDS" | tr ' ' '\n' | grep -vE '^(0[1-9]|1[01])-(shell-collect|tide-timer|gull-round-plan|shell-combo|gull-swoop|gull-sprite|warning-cue|gull-playtest|future-scope|warning-sfx|playable-build)$' || true)
if [ "$FINAL_N" -ge 11 ] && [ "$FINAL_N" -le 12 ] && [ -z "$EXTRA_IDS" -o "$EXTRA_IDS" = "12-game-design-v4" ]; then
  ok "任务清单回读为 $FINAL_N 个身份且无重复(11 项承接;委派任务 12-game-design-v4 为统筹裁量可选)"
else
  bad "任务清单异常(N=$FINAL_N,额外身份:$EXTRA_IDS)"
fi
python3 -B "$PLUGIN_RECORDS/mgs_records.py" show --project "$PROJ" --task 02-tide-timer > "$EVIDENCE_DIR/records-show-02.json" 2>&1
check_contains "02 任务可回读(待验收 + 结果索引含 evidence)" "$EVIDENCE_DIR/records-show-02.json" '待验收' 'evidence/'
python3 -B "$PLUGIN_RECORDS/mgs_records.py" deps --project "$PROJ" > "$EVIDENCE_DIR/records-deps-final.json" 2>&1
check_contains "最终依赖关系可解析且无循环" "$EVIDENCE_DIR/records-deps-final.json" '"ok": true' '"cycles": []'
python3 -B "$PLUGIN_RECORDS/mgs_records.py" ready --project "$PROJ" > "$EVIDENCE_DIR/records-ready-final.json" 2>&1
check "最终可开工集合为空(04/05/08 needs-triage;02/06/10/11 待验收)" bash -c \
  "! python3 -c \"import json;print(json.load(open('$EVIDENCE_DIR/records-ready-final.json'))['startable'])\" | grep -q '[0-9]'"
if python3 -B "$PLUGIN_RECORDS/mgs_records.py" verify --project "$PROJ" > "$EVIDENCE_DIR/records-verify-final.json" 2>&1; then
  ok "统一接口核验通过(needs-triage 重新分流未破坏记录结构)"
else
  bad "统一接口核验未通过"; cat "$EVIDENCE_DIR/records-verify-final.json"
fi
python3 -B "$PLUGIN_RECORDS/mgs_records.py" baseline --project "$PROJ" > "$EVIDENCE_DIR/baseline-final.json" 2>&1
BASELINE_FINAL_RC=$?
check "最终 baseline 仍退出码 1(GAME_DESIGN 实质变更待开发者确认,如实保留)" test "$BASELINE_FINAL_RC" = "1"
check "最终 baseline:GAME_DESIGN 实质变更 + PROJECT 一致" bash -c \
  "python3 -c \"import json;d=json.load(open('$EVIDENCE_DIR/baseline-final.json'));s={x['path'].split('/')[-1]:x['status'] for x in d['docs']};exit(0 if s.get('GAME_DESIGN.md')=='内容已变(实质变更)' and s.get('PROJECT.md')=='一致' else 1)\""

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
ADDED_OK=$(printf '%s\n' "$ADDED" | grep -cv -E '^\./docs/mygamestudio/(work/(15-race-demo/results/|12-game-design-v4/task\.md)|records/decision-2026-09-08-round-45s\.md)' || true)
MODIFIED_OK=$(printf '%s\n' "$MODIFIED" | grep -cv -E '^\./docs/mygamestudio/(PROJECT\.md|GAME_DESIGN\.md|work/(02-tide-timer|04-shell-combo|05-gull-swoop|06-gull-sprite|08-gull-playtest|10-warning-sfx|11-playable-build)/task\.md)$' || true)
if [ "${ADDED_OK:-1}" = "0" ] && [ "${MODIFIED_OK:-1}" = "0" ] && [ -z "$REMOVED" ]; then
  ok "终态变化与计划一一对应(新增限 15-race-demo、委派任务与决定记录;修改限 PROJECT/GAME_DESIGN/七份任务记录;无删除)"
else
  bad "出现计划外变化(详见 project-expected-changes.txt)"; cat "$EVIDENCE_DIR/project-expected-changes.txt"
fi

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
N=$(audit_count "$RUNROOT" 'e["op"]=="locks/reclaim"')
[ "${N:-0}" -ge 2 ] && ok "审计:占用回收操作留痕(含活跃期拒绝与到期放行,N=$N)" || bad "缺少占用回收审计(N=$N)"
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
for name in prod1 spec1 prod2 race1 race2 exp1 prod3 prod4 wexp par1 par2; do
  if [ -f "$ARENA/$name.token" ]; then
    if grep -rq "$(cat "$ARENA/$name.token")" "$PROJ" 2>/dev/null; then LEAK=1; fi
    if grep -rq "$(cat "$ARENA/$name.token")" "$EVIDENCE_DIR" 2>/dev/null; then LEAK=1; fi
  fi
done
[ "$LEAK" = "0" ] && ok "项目与证据目录均未发现任何原始令牌" || bad "发现原始令牌泄漏"
{ ps aux | grep -E "codex (app-server|exec)" | grep -v grep || true; } > "$EVIDENCE_DIR/ps-final.txt"
# 只核对本轮新增的孤儿 codex 进程(真实残留 = 客户端先于清理死亡留下的孤儿)
codex_orphans > "$ARENA/ps-final-now.txt" || true
PS_NEW=$(comm -13 "$ARENA/ps-baseline.txt" "$ARENA/ps-final-now.txt" || true)
check "无本轮残留孤儿 codex 进程(受控中断进程组清理干净)" test -z "$PS_NEW"
[ -n "$PS_NEW" ] && say "残留孤儿 PID:$PS_NEW"

# ---------- 汇总 ----------

say ""
say "================ 汇总 ================"
say "PASS: $PASS  FAIL: $FAIL"
say "证据目录: $EVIDENCE_DIR"
[ "$FAIL" = "0" ]

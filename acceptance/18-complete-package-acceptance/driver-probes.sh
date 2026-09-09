#!/bin/bash
# 任务票 18:驱动式运行保障回归(无模型调用,确定性)。
#
# 用法:./driver-probes.sh [环境根目录(默认 /tmp/mygamestudio-accept-18-driver)]
#
# 背景:run.sh 的 R/G 环里有两组探针本来由真实模型 turn 发起;当模型调用
# 不可用(如账户用量限制)时,本脚本以 gate_probe.py 直接驱动**实际安装副本**
# 的 mgs-gate 进程(同一 stdio MCP 协议、同一策略状态)完成同等语义的回归:
#   - 角色交集 allow/deny、任务粒度 deny、占用冲突 deny、换链 path deny
#   - 策略损坏失效闭合 → 恢复后同一凭据继续写入
#   - 凭据释放后旧令牌 identity 拒绝
#   - 占用回收(活跃拒/释放后回收/终态清空)
#   - GitHub 替身:受控远端 allow/task_grant deny/上游失联失效闭合+草稿重放
# 会话级(模型在真实 codex 会话中发起工具调用)的证据仍以 run.sh 的真实
# turn 为准;本脚本是其确定性补充,不冒充会话级证据。
#
# 输出:证据写本目录 evidence/(前缀 driver-*)。

set -u

REPO_ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
ACC_DIR="$REPO_ROOT/acceptance/18-complete-package-acceptance"
EVIDENCE_DIR="$ACC_DIR/evidence"
ENVROOT="${1:-/tmp/mygamestudio-accept-18-driver}"
ARENA="$REPO_ROOT/.tmp/accept-18-driver"
RUNROOT_L="$ARENA/local-runtime"
RUNROOT_G="$ARENA/gh-runtime"
PROJ_L="$ARENA/local-project"
PROJ_G="$ARENA/gh-project"
GH_CACHE="$ARENA/gh-cache"
GH_EMIT="$ARENA/gh-emit"
PLUGIN_RUNTIME="$REPO_ROOT/plugin/runtime"
PLUGIN_RECORDS="$REPO_ROOT/plugin/records"
GATE_PROBE="$ACC_DIR/gate_probe.py"
STANDIN="$ACC_DIR/standin_github.py"
HARBOR_FIXTURE="$REPO_ROOT/acceptance/17-github-issue-workflow/fixtures/harbor-run"
REPO="github.com/mygamestudio/issue-accept"
GHTOKEN="standin-token-$(date +%s)-$$"
STANDIN_PORT=""
REAL_HOME="$HOME"
PASS=0; FAIL=0

say()  { printf '%s\n' "$*"; }
ok()   { PASS=$((PASS+1)); say "PASS: $*"; }
bad()  { FAIL=$((FAIL+1)); say "FAIL: $*"; }
check() { local d="$1"; shift; if "$@" >/dev/null 2>&1; then ok "$d"; else bad "$d"; fi; }
check_contains() {
  local d="$1" f="$2"; shift 2; local n
  for n in "$@"; do grep -qF -e "$n" -- "$f" || { bad "$d (未找到: $n)"; return; }; done
  ok "$d"
}
check_json() {
  local d="$1" f="$2" e="$3"
  if python3 -B -c "import json,sys;data=json.load(open(sys.argv[1]));sys.exit(0 if ($e) else 1)" "$f" 2>/dev/null; then
    ok "$d"
  else
    bad "$d (表达式不成立: $e)"
  fi
}

standin_state() {
  python3 -B -c "
import json, sys, urllib.request
req = urllib.request.Request('http://127.0.0.1:' + sys.argv[1] + '/_test/state')
print(urllib.request.urlopen(req, timeout=5).read().decode())
" "$STANDIN_PORT"
}

for f in driver-*.json driver-*.txt; do rm -f "$EVIDENCE_DIR/$f"; done 2>/dev/null

# ---------- D0. 环境与安装(仅 CLI,无模型) ----------

{
  echo "date: $(date -Iseconds)"
  echo "codex: $(codex --version 2>&1)"
  echo "os: $(sw_vers -productName 2>/dev/null) $(sw_vers -productVersion 2>/dev/null) ($(uname -m))"
  echo "note: 无模型调用;gate_probe.py 驱动实际安装副本的 mgs-gate 进程"
} > "$EVIDENCE_DIR/driver-environment.txt"

rm -rf "$ENVROOT" "$ARENA"
mkdir -p "$ENVROOT/home/.agents/plugins" "$ENVROOT/home/plugins" "$ENVROOT/codex-home" \
         "$ARENA/local-project" "$ARENA/gh-project"
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
ln -s "$REAL_HOME/.codex/auth.json" "$ENVROOT/codex-home/auth.json"
printf 'check_for_update_on_startup = false\n' > "$ENVROOT/codex-home/config.toml"
HOME="$ENVROOT/home" CODEX_HOME="$ENVROOT/codex-home" \
  codex plugin add mygamestudio@personal --json > "$EVIDENCE_DIR/driver-plugin-install.json" 2>&1
check_contains "安装副本就绪" "$EVIDENCE_DIR/driver-plugin-install.json" '"installedPath"'
INSTALLED=$(python3 -c "import json;print(json.load(open('$EVIDENCE_DIR/driver-plugin-install.json'))['installedPath'])")
check "安装副本与仓库 plugin/ 逐字节一致" diff -r -x __pycache__ -x .DS_Store "$REPO_ROOT/plugin" "$INSTALLED"
GATE="$INSTALLED/runtime/mcp_gate.py"

mk_instance() { # mk_instance <运行根> <前缀> <role> <task> <ttl> <resource>...
  local rr="$1" pf="$2" role="$3" task="$4" ttl="$5"; shift 5
  local args=() r
  for r in "$@"; do args+=(--resource "$r"); done
  python3 -B "$PLUGIN_RUNTIME/mgsrt_admin.py" --runtime-root "$rr" create-instance \
    --role "$role" --task "$task" --purpose production --ttl-mins "$ttl" "${args[@]}" \
    > "$ARENA/$pf.json" 2>/dev/null
  python3 -c "import json;print(json.load(open('$ARENA/$pf.json'))['instance_id'])" > "$ARENA/$pf.id"
  python3 -c "import json;print(json.load(open('$ARENA/$pf.json'))['token'])" > "$ARENA/$pf.token"
}
gate_call() { # gate_call <输出文件> <工具> <参数JSON>
  MGS_RUNTIME_ROOT="$RUNROOT_L" python3 -B "$GATE_PROBE" --gate "$GATE" call "$2" "$3" > "$1" 2>&1
}

# ---------- D1. 本地运行保障回归 ----------

mkdir -p "$PROJ_L/src"
printf 'x' > "$PROJ_L/src/main.js"
cat > "$ARENA/policy-spec.json" <<EOF
{
  "project_root": "$PROJ_L",
  "roles": {"producer": ["docs/**"], "implement": ["src/**"]},
  "purposes": {"production": null}
}
EOF
python3 -B "$PLUGIN_RUNTIME/mgsrt_admin.py" --runtime-root "$RUNROOT_L" init-policy \
  --spec "$ARENA/policy-spec.json" > "$EVIDENCE_DIR/driver-init-policy.json" 2>&1
check_contains "策略初始化" "$EVIDENCE_DIR/driver-init-policy.json" '"implement"'
POLICY_SHA0=$(shasum -a 256 "$RUNROOT_L/policy.json" | awk '{print $1}')
# 注:d_i1 的授权里故意带上 docs/PROJECT.md(超出 implement 角色范围),
# 使「任务层放行、角色层拒绝」的 role_stage 可被命中;run.sh 的会话级探针
# 在真实会话里以同样方式构造(role 层与 grant 层是两道独立交集)。
mk_instance "$RUNROOT_L" d_i1 implement driver-reg-a 60 'src/**' 'docs/PROJECT.md'
mk_instance "$RUNROOT_L" d_i2 implement driver-reg-b 60 'src/lock.txt'
D1_TOK=$(cat "$ARENA/d_i1.token"); D2_TOK=$(cat "$ARENA/d_i2.token")

gate_call "$EVIDENCE_DIR/driver-scope.json" mgs_scope "{\"token\": \"$D1_TOK\"}"
check_contains "scope 返回绑定身份与范围" "$EVIDENCE_DIR/driver-scope.json" '"decision": "allow"' '"implement"'
gate_call "$EVIDENCE_DIR/driver-write-allow.json" mgs_write \
  "{\"token\": \"$D1_TOK\", \"path\": \"src/reg-a.txt\", \"content\": \"driver ok\"}"
check_contains "合法专业写入 allow" "$EVIDENCE_DIR/driver-write-allow.json" '"decision": "allow"' 'granted'
check "写入实际生效" grep -q 'driver ok' "$PROJ_L/src/reg-a.txt"
gate_call "$EVIDENCE_DIR/driver-role-deny.json" mgs_write \
  "{\"token\": \"$D1_TOK\", \"path\": \"docs/PROJECT.md\", \"content\": \"x\", \"expected_sha256\": \"absent\"}"
check_contains "角色越界写入 deny(role_scope)" "$EVIDENCE_DIR/driver-role-deny.json" \
  '"decision": "deny"' 'role_scope'
gate_call "$EVIDENCE_DIR/driver-lock-by-i2.json" mgs_write \
  "{\"token\": \"$D2_TOK\", \"path\": \"src/lock.txt\", \"content\": \"by i2\"}"
check_contains "窄授权实例写授权文件 allow" "$EVIDENCE_DIR/driver-lock-by-i2.json" '"decision": "allow"'
gate_call "$EVIDENCE_DIR/driver-occupancy.json" mgs_write \
  "{\"token\": \"$D1_TOK\", \"path\": \"src/lock.txt\", \"content\": \"by i1\"}"
check_contains "同资源第二写入者 deny(occupancy)" "$EVIDENCE_DIR/driver-occupancy.json" \
  '"decision": "deny"' 'occupancy'
check "占用拒绝后目标未被覆盖(仍是 i2 内容)" grep -q 'by i2' "$PROJ_L/src/lock.txt"
gate_call "$EVIDENCE_DIR/driver-task-deny.json" mgs_write \
  "{\"token\": \"$D2_TOK\", \"path\": \"src/other.txt\", \"content\": \"x\"}"
check_contains "任务粒度越界 deny(task_grant)" "$EVIDENCE_DIR/driver-task-deny.json" \
  '"decision": "deny"' 'task_grant'
ln -sf "$PROJ_L/docs/PROJECT.md" "$ARENA/evil-link.md"
gate_call "$EVIDENCE_DIR/driver-symlink.json" mgs_write \
  "{\"token\": \"$D1_TOK\", \"path\": \"$ARENA/evil-link.md\", \"content\": \"x\"}"
check_contains "换链路径 deny(path)" "$EVIDENCE_DIR/driver-symlink.json" '"decision": "deny"' 'path'

# 策略损坏失效闭合 → 恢复后同一凭据继续可用
cp "$RUNROOT_L/policy.json" "$ARENA/policy.bak"
printf '{ not valid json' > "$RUNROOT_L/policy.json"
gate_call "$EVIDENCE_DIR/driver-policy-corrupt.json" mgs_write \
  "{\"token\": \"$D1_TOK\", \"path\": \"src/corrupt.txt\", \"content\": \"x\"}"
check_contains "策略损坏失效闭合 deny(policy)" "$EVIDENCE_DIR/driver-policy-corrupt.json" \
  '"decision": "deny"' 'policy'
check "策略损坏期间未落盘" test ! -f "$PROJ_L/src/corrupt.txt"
cp "$ARENA/policy.bak" "$RUNROOT_L/policy.json"
POLICY_SHA1=$(shasum -a 256 "$RUNROOT_L/policy.json" | awk '{print $1}')
check "策略恢复为原字节" test "$POLICY_SHA0" = "$POLICY_SHA1"
gate_call "$EVIDENCE_DIR/driver-policy-restored.json" mgs_write \
  "{\"token\": \"$D1_TOK\", \"path\": \"src/after-restore.txt\", \"content\": \"same credential\"}"
check_contains "恢复后同一凭据继续写入(无需重签发)" "$EVIDENCE_DIR/driver-policy-restored.json" \
  '"decision": "allow"'

# 凭据释放后旧令牌拒绝;占用回收
python3 -B "$PLUGIN_RUNTIME/mgsrt_admin.py" --runtime-root "$RUNROOT_L" \
  release-instance --id "$(cat "$ARENA/d_i1.id")" > /dev/null 2>&1
gate_call "$EVIDENCE_DIR/driver-identity-deny.json" mgs_write \
  "{\"token\": \"$D1_TOK\", \"path\": \"src/stale.txt\", \"content\": \"x\"}"
check_contains "已释放实例旧令牌 deny(identity)" "$EVIDENCE_DIR/driver-identity-deny.json" \
  '"decision": "deny"' 'identity'
check "旧令牌写入未生效" test ! -f "$PROJ_L/src/stale.txt"
python3 -B "$PLUGIN_RUNTIME/mgsrt_admin.py" --runtime-root "$RUNROOT_L" \
  reclaim-locks --id "$(cat "$ARENA/d_i2.id")" > "$EVIDENCE_DIR/driver-reclaim-active.json" 2>&1
check "活跃实例占用回收被拒(退出码非 0)" test "$?" -ne 0
python3 -B "$PLUGIN_RUNTIME/mgsrt_admin.py" --runtime-root "$RUNROOT_L" \
  release-instance --id "$(cat "$ARENA/d_i2.id")" > /dev/null 2>&1
python3 -B "$PLUGIN_RUNTIME/mgsrt_admin.py" --runtime-root "$RUNROOT_L" \
  reclaim-locks --id "$(cat "$ARENA/d_i2.id")" > /dev/null 2>&1
python3 -B "$PLUGIN_RUNTIME/mgsrt_admin.py" --runtime-root "$RUNROOT_L" \
  reclaim-locks --id "$(cat "$ARENA/d_i1.id")" > /dev/null 2>&1
python3 -B "$PLUGIN_RUNTIME/mgsrt_admin.py" --runtime-root "$RUNROOT_L" status \
  > "$EVIDENCE_DIR/driver-status-final.json" 2>&1
check_json "回收后运行根占用清空" "$EVIDENCE_DIR/driver-status-final.json" "data['locks'] == []"

# ---------- D2. 受控远端通道(替身) ----------

cp -R "$HARBOR_FIXTURE/." "$PROJ_G/"
(cd "$PROJ_G" && git init -q . && git config user.email t@t && git config user.name t)
python3 -B "$STANDIN" --port 0 --token "$GHTOKEN" --state-file "$ARENA/standin-state.json" \
  > "$ARENA/standin.log" 2>&1 &
STANDIN_PID=$!
for _ in $(seq 1 50); do
  STANDIN_PORT=$(sed -n 's/^PORT //p' "$ARENA/standin.log" 2>/dev/null)
  [ -n "$STANDIN_PORT" ] && break
  sleep 0.2
done
[ -z "$STANDIN_PORT" ] && { bad "替身未启动"; exit 1; }
export MGS_GITHUB_TOKEN="$GHTOKEN"
python3 -B "$PLUGIN_RUNTIME/mgsrt_admin.py" --runtime-root "$RUNROOT_G" set-remote-config \
  --api-base "http://127.0.0.1:$STANDIN_PORT" --token-env MGS_GITHUB_TOKEN \
  --cache-dir "$GH_CACHE" > "$EVIDENCE_DIR/driver-set-remote.json" 2>&1
check_contains "远端通道配置登记(只收环境变量名)" "$EVIDENCE_DIR/driver-set-remote.json" \
  '"token_env": "MGS_GITHUB_TOKEN"'

CLIBIN="python3 -B $PLUGIN_RECORDS/mgs_records.py"
APIFLAG="--api-base http://127.0.0.1:$STANDIN_PORT"
PFLAGS="--project $PROJ_G $APIFLAG --cache-dir $GH_CACHE"
mkdir -p "$GH_CACHE"
python3 -B - "$PROJ_G/docs/mygamestudio/CONFIG.md" "$REPO" <<'PYEOF'
import sys
from pathlib import Path
path, repo = Path(sys.argv[1]), sys.argv[2]
text = path.read_text(encoding="utf-8")
old = "- 外部连接引用及已确认操作范围:无"
new = ("- 外部连接引用及已确认操作范围:"
       + repo + ":issues-write(2026-09-09 开发者确认;仅测试仓库;"
         "范围:任务与结果读写;凭据经环境变量,不入项目记录)")
assert old in text
path.write_text(text.replace(old, new), encoding="utf-8")
PYEOF
$CLIBIN switch-plan --project "$PROJ_G" --target github-issues --repo "$REPO" \
  --emit "$ARENA/switch-plan.json" > "$EVIDENCE_DIR/driver-switch-plan.json" 2>&1
check_json "迁移清单识别写授权" "$ARENA/switch-plan.json" "data['write_authorized'] is True"
$CLIBIN switch-apply --project "$PROJ_G" --plan "$ARENA/switch-plan.json" \
  --emit-dir "$GH_EMIT" --confirmed $APIFLAG > "$EVIDENCE_DIR/driver-switch-apply.json" 2>&1
check_json "apply 创建两个远端任务" "$EVIDENCE_DIR/driver-switch-apply.json" "data['created'] == 2"
cp "$GH_EMIT/CONFIG.md" "$PROJ_G/docs/mygamestudio/CONFIG.md"
$CLIBIN create $PFLAGS --identity 03-storm-warning --title "风暴预警" \
  --field "当前目标=风暴预警" > /dev/null 2>&1
$CLIBIN create $PFLAGS --identity 04-fog-layer --title "海雾层" \
  --field "当前目标=海雾层" > /dev/null 2>&1

cat > "$ARENA/gh-policy.json" <<EOF
{
  "project_root": "$PROJ_G",
  "roles": {"producer": ["docs/mygamestudio/CONFIG.md",
                          "github://github.com/mygamestudio/issue-accept/issues/**"]},
  "purposes": {"production": null}
}
EOF
python3 -B "$PLUGIN_RUNTIME/mgsrt_admin.py" --runtime-root "$RUNROOT_G" init-policy \
  --spec "$ARENA/gh-policy.json" > /dev/null 2>&1
mk_instance "$RUNROOT_G" d_g producer driver-gh 60 \
  'docs/mygamestudio/CONFIG.md' \
  'github://github.com/mygamestudio/issue-accept/issues' \
  'github://github.com/mygamestudio/issue-accept/issues/04-fog-layer/**'
DG_TOK=$(cat "$ARENA/d_g.token")

remote_call() { # remote_call <输出文件> <action> <payloadJSON>
  MGS_RUNTIME_ROOT="$RUNROOT_G" python3 -B "$GATE_PROBE" --gate "$GATE" call mgs_remote \
    "{\"token\": \"$DG_TOK\", \"action\": \"$2\", \"payload\": $3}" > "$1" 2>&1
}
remote_call "$EVIDENCE_DIR/driver-remote-read.json" read '{"identity": "01-harbor-timer"}'
check_contains "受控远端读取 allow(经通道)" "$EVIDENCE_DIR/driver-remote-read.json" '"decision": "allow"'
remote_call "$EVIDENCE_DIR/driver-remote-update.json" update \
  '{"identity": "04-fog-layer", "fields": {"进度": "执行中"}}'
check_contains "受控远端安排更新 allow" "$EVIDENCE_DIR/driver-remote-update.json" '"decision": "allow"'
remote_call "$EVIDENCE_DIR/driver-remote-comment.json" append-result \
  '{"identity": "04-fog-layer", "result_markdown": "驱动探针记录:海雾层进入执行。"}'
check_contains "受控远端结果评论 allow" "$EVIDENCE_DIR/driver-remote-comment.json" '"decision": "allow"'
remote_call "$EVIDENCE_DIR/driver-remote-task-deny.json" update \
  '{"identity": "01-harbor-timer", "fields": {"进度": "执行中"}}'
check_contains "远端越权更新他人任务 deny(task_grant)" "$EVIDENCE_DIR/driver-remote-task-deny.json" \
  '"decision": "deny"' 'task_grant'

kill "$STANDIN_PID" 2>/dev/null; wait "$STANDIN_PID" 2>/dev/null
remote_call "$EVIDENCE_DIR/driver-remote-offline.json" update \
  '{"identity": "04-fog-layer", "fields": {"进度": "待验收"}}'
check_contains "上游失联失效闭合 deny(remote_upstream)" "$EVIDENCE_DIR/driver-remote-offline.json" \
  '"decision": "deny"' 'remote_upstream'
check "失联期间未静默转本地(无本地 03 目录)" test ! -d "$PROJ_G/docs/mygamestudio/work/03-storm-warning"
python3 -B "$STANDIN" --port "$STANDIN_PORT" --token "$GHTOKEN" \
  --state-file "$ARENA/standin-state.json" >> "$ARENA/standin.log" 2>&1 &
STANDIN_PID=$!
for _ in $(seq 1 50); do standin_state > /dev/null 2>&1 && break; sleep 0.2; done
$CLIBIN publish-drafts $PFLAGS > "$EVIDENCE_DIR/driver-publish-drafts.json" 2>&1
check_json "远端恢复后草稿重放发布" "$EVIDENCE_DIR/driver-publish-drafts.json" \
  "data['published_count'] >= 1"
standin_state > "$EVIDENCE_DIR/driver-standin-final.json"
check_json "发布后 04 进度待验收(离线草稿经重放生效)" "$EVIDENCE_DIR/driver-standin-final.json" \
  "any('任务身份:04-fog-layer' in i['body'] and '进度:待验收' in i['body'] for i in data['issues'])"
check_json "04 的结果评论经通道在远端(恰 1 条)" "$EVIDENCE_DIR/driver-standin-final.json" \
  "len(data['comments'].get('4', [])) == 1"
$CLIBIN verify $PFLAGS > "$EVIDENCE_DIR/driver-gh-verify.json" 2>&1
check_json "github 后端 verify 通过" "$EVIDENCE_DIR/driver-gh-verify.json" "data['ok'] is True"

# 凭据脱敏与收尾
for pf in d_i1 d_i2 d_g; do
  [ -f "$ARENA/$pf.token" ] || continue
  tok=$(cat "$ARENA/$pf.token")
  for ef in "$EVIDENCE_DIR"/driver-*.json "$EVIDENCE_DIR"/driver-*.txt; do
    [ -f "$ef" ] && sed -i '' "s/$tok/<redacted-token>/g" "$ef"
  done
done
for ef in "$EVIDENCE_DIR"/driver-*.json "$EVIDENCE_DIR"/driver-*.txt; do
  [ -f "$ef" ] && sed -i '' "s/$GHTOKEN/<redacted-remote-token>/g" "$ef"
done
python3 -B "$PLUGIN_RUNTIME/mgsrt_admin.py" --runtime-root "$RUNROOT_G" \
  release-instance --id "$(cat "$ARENA/d_g.id")" > /dev/null 2>&1
kill "$STANDIN_PID" 2>/dev/null

say ""
say "================ 驱动式回归汇总 ================"
say "PASS: $PASS  FAIL: $FAIL"
say "声明:本脚本为确定性驱动(无模型调用);会话级证据以 run.sh 真实 turn 为准。"
[ "$FAIL" = "0" ]

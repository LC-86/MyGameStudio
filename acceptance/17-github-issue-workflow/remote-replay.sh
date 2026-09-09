#!/bin/bash
# 任务票 17 第 7 条:真实 GitHub 远端写入验收(确定性重放,无模型调用)。
#
# 用法:./remote-replay.sh [owner/repo(默认 LC-86/mgs-issue-accept-test)]
# 前提:gh CLI 已登录(令牌运行时经 `gh auth token` 取得,只注入本进程环境,
#       不落盘、不回显);目标仓库为空(0 issue)的一次性测试仓库,且已预建
#       标签 triage/info/agent-ready/human-ready/wont-do(仓库准备步骤见
#       runbook「真实远端验收」节)。
#
# 范围:重放 run.sh 第 4 段的远端操作序列(切换清单/授权拒绝/apply 创建/防重
#       收养/版本校验/依赖与父子/分流/结果评论/关闭三因语义其中两种/交接核对/
#       verify)到真实 api.github.com。替身独有的故障注入(超时丢包、断连草稿、
#       sub-issues 开关)不在真实远端重放——其语义由 run.sh(替身)与
#       tests/test_github_backend.py 固化,本脚本不重复也不冒充。
#
# 输出:证据写本目录 evidence/(前缀 real-remote-*);令牌值全量脱敏后才收档。

set -u

REPO_ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
ACC_DIR="$REPO_ROOT/acceptance/17-github-issue-workflow"
EVIDENCE_DIR="$ACC_DIR/evidence"
ARENA="$REPO_ROOT/.tmp/accept-17-real"
PROJ="$ARENA/projects/harbor-run"
CACHE="$ARENA/cache"
EMIT="$ARENA/emit"
PLUGIN_RECORDS="$REPO_ROOT/plugin/records"

GHREPO="${1:-LC-86/mgs-issue-accept-test}"
REPO="github.com/$GHREPO"
API="https://api.github.com"
TODAY="$(date +%F)"

PASS=0
FAIL=0

say()  { printf '%s\n' "$*"; }
ok()   { PASS=$((PASS+1)); say "PASS: $*"; }
bad()  { FAIL=$((FAIL+1)); say "FAIL: $*"; }

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

check_json() { # check_json <描述> <文件> <python布尔表达式(data)>
  local desc="$1" file="$2" expr="$3"
  if python3 -B -c "import json,sys;data=json.load(open(sys.argv[1]));sys.exit(0 if ($expr) else 1)" "$file" 2>/dev/null; then
    ok "$desc"
  else
    bad "$desc (表达式不成立: $expr)"
  fi
}

# ---------- 0. 环境与前置 ----------

say "== 0. 真实远端环境记录与前置检查 =="
rm -f "$EVIDENCE_DIR"/real-remote-* 2>/dev/null
rm -rf "$ARENA"
mkdir -p "$EVIDENCE_DIR" "$ARENA/projects" "$CACHE"

# 令牌:运行时从 gh 取得,只进本进程环境(TOKEN_ENVS 之首),永不打印/落盘
MGS_GITHUB_TOKEN="$(gh auth token 2>/dev/null)" || true
if [ -z "$MGS_GITHUB_TOKEN" ]; then
  say "FAIL: gh auth token 不可用,无法取得远端凭据"
  exit 1
fi
export MGS_GITHUB_TOKEN

{
  echo "date: $(date -Iseconds)"
  echo "remote: 真实 GitHub api.github.com(非本地替身)"
  echo "repo: $REPO"
  echo "gh: $(gh --version 2>&1 | head -1)"
  echo "token: 经 gh auth token 运行时注入进程环境(MGS_GITHUB_TOKEN),不落盘"
  echo "model-calls: 0(确定性重放,无模型 turn)"
} > "$EVIDENCE_DIR/real-remote-environment.txt"
cat "$EVIDENCE_DIR/real-remote-environment.txt"

ISSUE_COUNT=$(gh issue list -R "$GHREPO" --json number --jq 'length' 2>/dev/null)
if [ "${ISSUE_COUNT:-x}" = "0" ]; then
  ok "目标测试仓库为空账本(0 issue)"
else
  bad "目标仓库非空(issue 数=${ISSUE_COUNT:-未知});真实远端重放要求一次性空仓库"
  exit 1
fi
gh label list -R "$GHREPO" --json name --jq '[.[].name] | sort' \
  > "$EVIDENCE_DIR/real-remote-labels.json" 2>/dev/null
check_json "五个项目标签已预建(新仓库另含平台默认标签,属正常)" \
  "$EVIDENCE_DIR/real-remote-labels.json" \
  "set(['triage','info','agent-ready','human-ready','wont-do']).issubset(set(data))"

# 隔离项目副本(夹具与本票替身验收同源;不动任何真实项目)
rm -rf "$PROJ"
cp -R "$ACC_DIR/fixtures/harbor-run" "$PROJ"
(cd "$PROJ" && git init -q . && git config user.email t@t && git config user.name t)

CLIBIN="python3 -B $PLUGIN_RECORDS/mgs_records.py"
APIFLAG="--api-base $API"
EMITFLAGS="--project $ARENA/verifyproj --config CONFIG.md $APIFLAG --cache-dir $CACHE"

# ---------- 1. 切换清单(只读) ----------

say "== 1. switch-plan 只读清单(真实仓库坐标) =="
$CLIBIN verify --project "$PROJ" $APIFLAG --cache-dir "$CACHE" \
  > "$EVIDENCE_DIR/real-remote-verify-local.json" 2>&1
check_json "切换前本地后端 verify 通过" "$EVIDENCE_DIR/real-remote-verify-local.json" \
  "data['ok'] is True"
$CLIBIN switch-plan --project "$PROJ" --target github-issues --repo "$REPO" \
  --emit "$ARENA/switch-plan.json" > "$EVIDENCE_DIR/real-remote-switch-plan.json" 2>&1
check_json "迁移清单覆盖两个既有任务且身份不变" "$ARENA/switch-plan.json" \
  "[t['identity'] for t in data['tasks']] == ['01-harbor-timer', '02-crane-sprite']"
check_json "未授权时 write_authorized=False" "$ARENA/switch-plan.json" \
  "data['write_authorized'] is False"
check_json "未发布本地基线被判远端不可访问" "$ARENA/switch-plan.json" \
  "all(not d['remote_reachable'] for d in data['baseline_handover'])"

say "== 2. 授权记录(用户 2026-09-09 指令,run.sh 先例留档) =="
cat > "$EVIDENCE_DIR/real-remote-confirm.md" <<EOF
# 真实远端写入授权(2026-09-09)

用户指令原文:「建测试仓库,跑票 17 真实远端验收」。
授权范围:仅一次性私有测试仓库 $REPO 的任务与结果读写(issues-write);
测试仓库由验收方用 gh 创建(私有);其余仓库一律未授权。凭据经环境变量
注入,不入项目记录。
EOF
ok "授权来源与范围已留档(evidence/real-remote-confirm.md)"

say "== 3. 无授权 apply 被拒;授权记入 CONFIG 后清单识别 =="
$CLIBIN switch-apply --project "$PROJ" --plan "$ARENA/switch-plan.json" \
  --emit-dir "$ARENA/emit0" --confirmed $APIFLAG \
  > "$EVIDENCE_DIR/real-remote-apply-noauth.json" 2>&1
RC=$?
[ "$RC" -ne 0 ] && ok "CONFIG 未记录授权时 apply 拒绝(退出码 $RC)" \
  || bad "无授权 apply 未被拒绝(退出码 0)"
check_contains "拒绝原因指向 issues-write 授权补记" \
  "$EVIDENCE_DIR/real-remote-apply-noauth.json" 'issues-write'
python3 -B - "$PROJ/docs/mygamestudio/CONFIG.md" "$REPO" <<'PYEOF'
import sys
from pathlib import Path
path, repo = Path(sys.argv[1]), sys.argv[2]
text = path.read_text(encoding="utf-8")
old = "- 外部连接引用及已确认操作范围:无"
new = ("- 外部连接引用及已确认操作范围:"
       + repo + ":issues-write(2026-09-09 用户指令「建测试仓库,跑票 17 真实远端验收」;"
         "仅测试仓库;范围:任务与结果读写;凭据经环境变量,不入项目记录)")
assert old in text
path.write_text(text.replace(old, new), encoding="utf-8")
PYEOF
$CLIBIN switch-plan --project "$PROJ" --target github-issues --repo "$REPO" \
  --emit "$ARENA/switch-plan.json" \
  > "$EVIDENCE_DIR/real-remote-switch-plan-authorized.json" 2>&1
check_json "授权记入 CONFIG 后 write_authorized=True" "$ARENA/switch-plan.json" \
  "data['write_authorized'] is True"

# ---------- 4. apply 与统一接口 ----------

say "== 4. apply:真实创建同身份任务;统一接口回读 =="
$CLIBIN switch-apply --project "$PROJ" --plan "$ARENA/switch-plan.json" \
  --emit-dir "$EMIT" --confirmed $APIFLAG \
  > "$EVIDENCE_DIR/real-remote-apply.json" 2>&1
check_json "apply 在真实 GitHub 创建两个任务" "$EVIDENCE_DIR/real-remote-apply.json" \
  "data['created'] == 2"
check_json "身份映射留档(空仓库首两号)" "$EMIT/identity-map.json" \
  "data['01-harbor-timer']['github_issue'] == 1 and data['02-crane-sprite']['github_issue'] == 2"
N1=1; N2=2
mkdir -p "$ARENA/verifyproj/docs/mygamestudio"
cp "$EMIT/CONFIG.md" "$ARENA/verifyproj/CONFIG.md"
cp "$PROJ"/docs/mygamestudio/{PROJECT,GAME_DESIGN,TECH_DESIGN}.md \
   "$ARENA/verifyproj/docs/mygamestudio/"
# GitHub 列表索引最终一致(创建后立查可能少一条,单条读不受影响):有界重试
# 并留痕重试次数——真实平台行为,替身同步一致不可复现,不掩盖
LIST_ATTEMPTS=0
LIST_OK=0
while [ "$LIST_ATTEMPTS" -lt 10 ]; do
  LIST_ATTEMPTS=$((LIST_ATTEMPTS+1))
  $CLIBIN list $EMITFLAGS > "$EVIDENCE_DIR/real-remote-list-after-switch.json" 2>&1
  if python3 -B -c "import json,sys;data=json.load(open(sys.argv[1]));sys.exit(0 if [t['identity'] for t in data]==['01-harbor-timer','02-crane-sprite'] else 1)" \
      "$EVIDENCE_DIR/real-remote-list-after-switch.json" 2>/dev/null; then
    LIST_OK=1
    break
  fi
  sleep 2
done
if [ "$LIST_OK" = "1" ]; then
  ok "切换后统一接口列出远端任务(身份一致;列表读滞后重试 $LIST_ATTEMPTS 次)"
else
  bad "列表在重试上限内未达到身份一致(10 次):$(python3 -c "import json;print([t.get('identity') for t in json.load(open('$EVIDENCE_DIR/real-remote-list-after-switch.json'))])" 2>/dev/null)"
fi
echo "list-read-lag-attempts: $LIST_ATTEMPTS" >> "$EVIDENCE_DIR/real-remote-environment.txt"
$CLIBIN deps $EMITFLAGS > "$EVIDENCE_DIR/real-remote-deps-after-switch.json" 2>&1
check_json "远端依赖解析 ok" "$EVIDENCE_DIR/real-remote-deps-after-switch.json" \
  "data['ok'] is True"

# ---------- 5. 防重收养 ----------

say "== 5. 同身份重复创建被收养(真实远端防重) =="
$CLIBIN create $EMITFLAGS --identity 03-storm-warning --title "风暴预警" \
  --field "当前目标=最后阶段风暴预警" --field "完成标准=无头检查可见预警" \
  --field "执行责任=Agent(制作实现)" > "$EVIDENCE_DIR/real-remote-create-03.json" 2>&1
check_json "真实创建 03-storm-warning 成功" "$EVIDENCE_DIR/real-remote-create-03.json" \
  "data['created'] is True and data['adopted'] is False"
$CLIBIN create $EMITFLAGS --identity 01-harbor-timer --title "倒计时最后十秒提示" \
  --field "当前目标=重复创建探针" > "$EVIDENCE_DIR/real-remote-create-dup.json" 2>&1
check_json "重复创建既有身份被收养(不新建)" "$EVIDENCE_DIR/real-remote-create-dup.json" \
  "data['created'] is False and data['adopted'] is True"

# ---------- 6. 正文版本校验 ----------

say "== 6. expected_body_sha256 版本校验(过期拒绝 + 正确成功) =="
$CLIBIN show $EMITFLAGS --task 01-harbor-timer > "$EVIDENCE_DIR/real-remote-show-01.json" 2>&1
BODY_SHA=$(python3 -c "import json;print(json.load(open('$EVIDENCE_DIR/real-remote-show-01.json'))['body_sha256'])")
$CLIBIN update $EMITFLAGS --task 01-harbor-timer --field "进度=已完成" \
  --expected-body-sha256 "0000000000000000000000000000000000000000000000000000000000000000" \
  > "$EVIDENCE_DIR/real-remote-update-stale.json" 2>&1
RC=$?
[ "$RC" -ne 0 ] && ok "过期正文指纹更新被拒(退出码 $RC)" \
  || bad "过期指纹更新未被拒绝(退出码 0)"
check_contains "拒绝原因说明不覆盖他人改动" \
  "$EVIDENCE_DIR/real-remote-update-stale.json" '已被他人修改'
$CLIBIN update $EMITFLAGS --task 03-storm-warning --field "进度=进行中" \
  --expected-body-sha256 "$($CLIBIN show $EMITFLAGS --task 03-storm-warning 2>/dev/null | python3 -c "import json,sys;print(json.load(sys.stdin)['body_sha256'])")" \
  > "$EVIDENCE_DIR/real-remote-update-03.json" 2>&1
check_json "正确指纹更新成功且回读一致" "$EVIDENCE_DIR/real-remote-update-03.json" \
  "data['readback']['progress'] == '进行中'"

# ---------- 7. 依赖与父子关系 ----------

say "== 7. 依赖引用与父子关系(原生 sub-issues 或回退) =="
$CLIBIN set-relations $EMITFLAGS --task 03-storm-warning --dep 01-harbor-timer \
  > "$EVIDENCE_DIR/real-remote-set-relations.json" 2>&1
check_json "依赖写成明确可解析引用(#Issue号 身份)" \
  "$EVIDENCE_DIR/real-remote-set-relations.json" \
  "data['readback']['request']['依赖'] == '#$N1 01-harbor-timer'"
$CLIBIN deps $EMITFLAGS > "$EVIDENCE_DIR/real-remote-deps-relations.json" 2>&1
check_json "deps 解析引用回身份且 ok" "$EVIDENCE_DIR/real-remote-deps-relations.json" \
  "data['edges'].get('03-storm-warning') == ['01-harbor-timer'] and data['ok'] is True"
$CLIBIN set-parent $EMITFLAGS --task 03-storm-warning --parent 01-harbor-timer \
  > "$EVIDENCE_DIR/real-remote-set-parent.json" 2>&1
check_json "父子关系落在受支持的模式(原生优先,不可用回退正文引用)" \
  "$EVIDENCE_DIR/real-remote-set-parent.json" \
  "data['mode'] in ('native-sub-issues', 'body-reference')"

# ---------- 8. 分流 ----------

say "== 8. 分流(标签与正文同步;ready 回读) =="
$CLIBIN set-triage $EMITFLAGS --task 03-storm-warning --label ready-for-agent \
  > "$EVIDENCE_DIR/real-remote-set-triage.json" 2>&1
check_json "set-triage 标签与正文同步为 ready-for-agent" \
  "$EVIDENCE_DIR/real-remote-set-triage.json" \
  "data['readback']['triage'] == 'ready-for-agent' and data['readback']['triage_source'] == 'label'"
$CLIBIN ready $EMITFLAGS > "$EVIDENCE_DIR/real-remote-ready.json" 2>&1
# 该时点流程状态:01/02 开放待执行且无依赖(可开工),03 因进度进行中被阻塞
# (进行中≠可开工,设计语义);关闭发生在后续小节
check_json "ready 可开工集合为 01/02(03 进行中被阻塞)" \
  "$EVIDENCE_DIR/real-remote-ready.json" \
  "sorted(t['identity'] for t in data['startable']) == ['01-harbor-timer', '02-crane-sprite'] and [t['identity'] for t in data['blocked']] == ['03-storm-warning'] and any('进行中' in r for t in data['blocked'] for r in t['reasons'])"

# ---------- 9. 结果评论与关闭语义 ----------

say "== 9. 结果评论 + 关闭(完成/不再执行) =="
$CLIBIN append-result $EMITFLAGS --task 01-harbor-timer \
  --text "骨架检查完成:倒计时读取点确认(main.js frame 循环)。" \
  > "$EVIDENCE_DIR/real-remote-append-result-01.json" 2>&1
check_json "结果评论发布并登记索引" "$EVIDENCE_DIR/real-remote-append-result-01.json" \
  "data['published'] is True and data['comment_id'] is not None"
check_json "评论结果可回读且引用所属任务" "$EVIDENCE_DIR/real-remote-append-result-01.json" \
  "len(data['readback']['results']) == 1 and data['readback']['results'][0]['excerpt'].startswith('任务:01-harbor-timer')"
$CLIBIN close $EMITFLAGS --task 01-harbor-timer --reason "完成" --note "骨架检查交付" \
  > "$EVIDENCE_DIR/real-remote-close-01.json" 2>&1
check_json "完成关闭为 completed 且进度同步" "$EVIDENCE_DIR/real-remote-close-01.json" \
  "data['readback']['state'] == 'closed' and data['readback']['state_reason'] == 'completed' and data['readback']['progress'] == '已完成'"
$CLIBIN close $EMITFLAGS --task 02-crane-sprite --reason "不再执行" \
  > "$EVIDENCE_DIR/real-remote-close-02.json" 2>&1
check_json "不再执行关闭为 not_planned" "$EVIDENCE_DIR/real-remote-close-02.json" \
  "data['readback']['state_reason'] == 'not_planned' and data['readback']['progress'] == '不再执行'"

# ---------- 10. 交接核对与终态 ----------

say "== 10. handover 不可达如实 + github 后端 verify =="
$CLIBIN handover $EMITFLAGS > "$EVIDENCE_DIR/real-remote-handover.json" 2>&1
RC=$?
[ "$RC" -eq 1 ] && ok "存在不可达基线时 handover 退出码 1(如实,不包装)" \
  || bad "handover 退出码 $RC(期望 1)"
check_contains "未发布本地基线标注不可访问" "$EVIDENCE_DIR/real-remote-handover.json" '不可访问'
check_contains "不宣称已可远端访问" "$EVIDENCE_DIR/real-remote-handover.json" '不得宣称'
$CLIBIN verify $EMITFLAGS > "$EVIDENCE_DIR/real-remote-verify-github.json" 2>&1
check_json "github 后端 verify 整体通过(真实远端)" \
  "$EVIDENCE_DIR/real-remote-verify-github.json" "data['ok'] is True"

# ---------- 11. gh 只读交叉核验 ----------

say "== 11. gh 只读交叉核验(独立于被测通道) =="
gh issue list -R "$GHREPO" --state all --json number,title,state,stateReason,labels \
  --jq '[.[] | {number, title, state, stateReason, labels: [.labels[].name] | sort}] | sort_by(.number)' \
  > "$EVIDENCE_DIR/real-remote-gh-issues.json" 2>&1
check_json "真实仓库恰 3 个任务(无重复创建)" "$EVIDENCE_DIR/real-remote-gh-issues.json" \
  "len(data) == 3"
check_json "01/02 关闭理由与进度语义正确(completed/not_planned)" \
  "$EVIDENCE_DIR/real-remote-gh-issues.json" \
  "{d['number']: (d['stateReason'] or '').lower() for d in data} == {1: 'completed', 2: 'not_planned', 3: ''}"
check_json "03 带 agent-ready 标签(分流落标签)" "$EVIDENCE_DIR/real-remote-gh-issues.json" \
  "[d for d in data if d['number'] == 3][0]['labels'] == ['agent-ready']"
gh api "repos/$GHREPO/issues/1/comments" --jq '[.[].body]' \
  > "$EVIDENCE_DIR/real-remote-gh-comments.json" 2>&1
check_json "01 的结果评论真实存在且含任务身份" "$EVIDENCE_DIR/real-remote-gh-comments.json" \
  "len(data) >= 1 and any('任务:01-harbor-timer' in c for c in data)"
gh api "repos/$GHREPO/issues/$N1/sub_issues" --jq '[.[].number]' \
  > "$EVIDENCE_DIR/real-remote-gh-subissues.json" 2>&1
MODE=$(python3 -c "import json;print(json.load(open('$EVIDENCE_DIR/real-remote-set-parent.json'))['mode'])" 2>/dev/null || echo unknown)
if [ "$MODE" = "native-sub-issues" ]; then
  check_json "原生父子关系在平台侧可见(1 的 sub_issues 含 3)" \
    "$EVIDENCE_DIR/real-remote-gh-subissues.json" "3 in data"
else
  check_contains "回退模式:正文引用明确可解析" "$EVIDENCE_DIR/real-remote-set-parent.json" '父任务:#'"$N1"' 01-harbor-timer'
fi

# ---------- 12. 令牌脱敏与收档 ----------

say "== 12. 证据令牌脱敏核对(真实凭据绝不入库) =="
LEAK=0
for file in "$EVIDENCE_DIR"/real-remote-*; do
  if grep -qF -e "$MGS_GITHUB_TOKEN" -- "$file" 2>/dev/null; then
    sed -i '' "s/$MGS_GITHUB_TOKEN/<redacted-remote-token>/g" "$file"
    grep -qF -e "$MGS_GITHUB_TOKEN" -- "$file" && LEAK=1
  fi
done
[ "$LEAK" = "0" ] && ok "全部 real-remote-* 证据无真实令牌残留" \
  || bad "证据中仍有真实令牌残留,不得入库"

say ""
say "================ 真实远端重放汇总 ================"
say "PASS: $PASS  FAIL: $FAIL"
say "仓库: $REPO(私有,一次性;证据前缀 real-remote-*)"
say "声明:本重放为确定性 CLI 驱动(0 模型调用);替身故障注入语义不在此重放范围,"
say "      由 run.sh 替身验收与 tests/test_github_backend.py 固化。"
[ "$FAIL" = "0" ]

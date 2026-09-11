#!/bin/bash
# 任务票 18:验收完整插件包及升级行为——隔离整包验收。
#
# 用法:./run.sh [环境根目录(默认 /tmp/mygamestudio-accept-18)]
#       MGS_PIN_MODEL=<模型名> ./run.sh   # 服务端模型路由异常时固定模型(票 16 通道)
#
# 内容(对应票 18 七条验收标准):
#  0. 环境记录(codex/gh 只读版本检测;不调用任何真实远端)
#  1. 确定性检查(5 个静态套件)+ dist 交付物重建核对(可复现构建)
#  2. 安装 0.18.0 与注册面:14 个入口、仅显式触发(debug prompt-input 对照)、
#     安装副本逐字节一致、指纹/许可/引用对安装副本复算
#  3. N1 普通对话对照:无提及的真实 turn 不触发任何业务入口、零写入
#  4. U 环(升级行为):安装真实旧版 0.17.0(git 提取)→ U1 $game-init 新项目
#     → 用户手工修改 → 真实升级(codex plugin remove+add 到 0.18.0)→
#     依赖与模板变化可发现、治理/运行规则/用户文档不被改写 → U2 $game-init
#     模板升级与保留核对
#  5. P 环(代表性闭环·本地/已有项目):P1 $game-producer 目标变化影响检查与
#     重分流 + 委派;P2 被委派 $game-design 决策地图;P3 直接调用 $game-status
#  6. G 环(代表性闭环·GitHub 替身):切换迁移(调度侧)→ G1 统筹远端操作
#     (mgs_remote allow/deny + 直连探针)→ 驱动式上游失联失效闭合
#  7. R 环(运行保障回归·交付包):R1 角色交集/任务粒度/占用/间接写入/换链
#     探针;驱动式策略损坏失效闭合与恢复;R1b 凭据失效后拒绝;占用回收
#  8. 终态:审计字段、令牌泄漏(独立扫描 secret_scan.py,逐运行根登记全量
#     比对,复审二 SP-5 机制化)、占用清空、汇总
#
# 真实模型 turn 共 9 个:N1/U1/U2/P1/P2/P3/G1/R1/R1b。
# 声明:G 环「远端」为本地 HTTP 替身(非真实 GitHub);真实远端写入验收
# 保留待办(需用户授权测试仓库,口径与票 17 一致)。
#
# 输出:全部证据写入本目录 evidence/,终端打印 PASS/FAIL 汇总。

set -u

REPO_ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
ACC_DIR="$REPO_ROOT/acceptance/18-complete-package-acceptance"
EVIDENCE_DIR="$ACC_DIR/evidence"
ENVROOT="${1:-/tmp/mygamestudio-accept-18}"
ARENA="$REPO_ROOT/.tmp/accept-18"
PROJ_U="$ARENA/upg/project";  RUNROOT_U="$ARENA/upg/runtime"
PROJ_P="$ARENA/p/project";    RUNROOT_P="$ARENA/p/runtime"
PROJ_G="$ARENA/gh/project";   RUNROOT_G="$ARENA/gh/runtime"
PROJ_R="$ARENA/reg/project";  RUNROOT_R="$ARENA/reg/runtime"
GH_CACHE="$ARENA/gh/cache";   GH_EMIT="$ARENA/gh/emit"
PLUGIN_RUNTIME="$REPO_ROOT/plugin/runtime"
PLUGIN_RECORDS="$REPO_ROOT/plugin/records"
SECRET_SCAN="$REPO_ROOT/acceptance/16-producer-complete-loop/secret_scan.py"
MGS_CLIENT="$ACC_DIR/appserver_client.py"
GATE_PROBE="$ACC_DIR/gate_probe.py"
STANDIN="$ACC_DIR/standin_github.py"
HARBOR_FIXTURE="$REPO_ROOT/acceptance/17-github-issue-workflow/fixtures/harbor-run"
ATLAS_FIXTURE="$ACC_DIR/fixtures/atlas-drop"
REPO="github.com/mygamestudio/issue-accept"
GHTOKEN="standin-token-$(date +%s)-$$"
STANDIN_PORT=""
OLD_COMMIT="36c432c"   # 0.17.0(任务票 17;2026-09-09 历史清理后哈希,旧 e2af9a9 为改写前链)
REAL_HOME="$HOME"
PASS=0; FAIL=0

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
      bad "$desc (未找到: $needle)"; return
    fi
  done
  ok "$desc"
}

check_not_contains() { # 任一存在即失败
  local desc="$1" file="$2"; shift 2
  local needle
  for needle in "$@"; do
    if grep -qF -e "$needle" -- "$file"; then
      bad "$desc (不应出现: $needle)"; return
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

# 票 08/09:工具拒绝与 curl 直连失败判据都迁出到共享 module(见
# evidence_judgement.py 文档),运行脚本与 Python 测试使用同一 seam;
# 此处仅保留 Shell 适配(参数传递 + OK/MISSING 返回),下方现场调用链
# 保持不变。判定语义与支持范围(mcp:SP-6/8/9/12/13/15/16;curl:
# SP-13/15/18~30)见该 module。
. "$ACC_DIR/evidence_adapter.sh"

standin_call() { # standin_call <JSON正文> [路径]
  python3 -B -c "
import json, sys, urllib.request
body = json.dumps(json.loads(sys.argv[1])).encode()
req = urllib.request.Request('http://127.0.0.1:' + sys.argv[3] + (sys.argv[2] or '/_test/control'),
                             data=body, headers={'Content-Type': 'application/json'}, method='POST')
print(urllib.request.urlopen(req, timeout=5).read().decode())
" "$1" "${2:-/_test/control}" "$STANDIN_PORT"
}

standin_state() {
  python3 -B -c "
import json, sys, urllib.request
req = urllib.request.Request('http://127.0.0.1:' + sys.argv[1] + '/_test/state')
print(urllib.request.urlopen(req, timeout=5).read().decode())
" "$STANDIN_PORT"
}

hash_tree() { # hash_tree <目录> <输出文件>(排除 .git 与 __pycache__)
  (cd "$1" && find . -type f ! -path '*/.git/*' ! -path '*/__pycache__/*' ! -name '.DS_Store' \
    | LC_ALL=C sort | xargs shasum -a 256) > "$2" 2>/dev/null
}

mkdir -p "$EVIDENCE_DIR"
# 清空可再生证据;保留手工维护的索引与历史过程日志(原始证据不随重跑消失)
for f in "$EVIDENCE_DIR"/*.txt "$EVIDENCE_DIR"/*.json "$EVIDENCE_DIR"/*.jsonl \
         "$EVIDENCE_DIR"/*.md "$EVIDENCE_DIR"/*.log; do
  [ -f "$f" ] || continue
  case "$f" in */README.md|*/process-log-*) continue ;; esac
  rm -f "$f"
done

# ---------- 0. 环境记录 ----------

{
  echo "date: $(date -Iseconds)"
  echo "codex: $(codex --version 2>&1)"
  echo "gh(只读版本检测,未调用任何远端): $(gh --version 2>&1 | head -1)"
  echo "os: $(sw_vers -productName 2>/dev/null) $(sw_vers -productVersion 2>/dev/null) ($(uname -m))"
  echo "python: $(python3 --version)"
  echo "cwd-repo: $REPO_ROOT"
  echo "env-root: $ENVROOT(home=0.18.0 主环境;homeu=升级剧场)"
  echo "arena: $ARENA"
  echo "upgrade-path: $OLD_COMMIT(0.17.0)→ 仓库 plugin/(0.18.0),经 codex plugin remove+add"
  echo "remote(G 环): 本地 HTTP 替身 standin_github.py(非真实 GitHub);真实远端写入验收已于 2026-09-09 经票 17 remote-replay.sh 完成"
  echo "model-pin: ${MGS_PIN_MODEL:-未固定(服务端默认)}"
} > "$EVIDENCE_DIR/environment.txt"
say "== 0. 环境已记录 =="; cat "$EVIDENCE_DIR/environment.txt"

if [ ! -f "$REAL_HOME/.codex/auth.json" ]; then
  bad "缺少 $REAL_HOME/.codex/auth.json,无法在隔离环境完成真实调用"
  exit 1
fi

# ---------- 1. 确定性检查 + dist 复现核对 ----------

say "== 1. 确定性检查(5 套)与 dist 交付物复现 =="
rm -rf "$PLUGIN_RUNTIME/__pycache__" "$PLUGIN_RECORDS/__pycache__" "$REPO_ROOT/tests/__pycache__"
for suite in test_plugin_package test_runtime_gate test_runtime_boundaries \
             test_records_backend test_github_backend; do
  if python3 -B "$REPO_ROOT/tests/$suite.py" > "$EVIDENCE_DIR/static-$suite.txt" 2>&1; then
    ok "确定性检查(tests/$suite.py)"
  else
    bad "确定性检查(tests/$suite.py)"; sed -n '1,20p' "$EVIDENCE_DIR/static-$suite.txt"
  fi
done
TARBALL_SHA_BEFORE=$(shasum -a 256 "$REPO_ROOT/dist/mygamestudio-0.18.0.tar.gz" | awk '{print $1}')
"$REPO_ROOT/dist/build-package.sh" > "$EVIDENCE_DIR/dist-rebuild.txt" 2>&1
TARBALL_SHA_AFTER=$(shasum -a 256 "$REPO_ROOT/dist/mygamestudio-0.18.0.tar.gz" | awk '{print $1}')
check "dist 安装包可复现构建(重打包字节一致)" test "$TARBALL_SHA_BEFORE" = "$TARBALL_SHA_AFTER"
check_contains "dist 重建产出说明含 0.18.0" "$EVIDENCE_DIR/dist-rebuild.txt" 'mygamestudio-0.18.0.tar.gz'
rm -rf "$PLUGIN_RUNTIME/__pycache__" "$PLUGIN_RECORDS/__pycache__"

# ---------- 2. 隔离环境、安装 0.18.0 与注册面 ----------

say "== 2. 安装 0.18.0:注册面、仅显式触发、指纹/许可/引用复算 =="
rm -rf "$ENVROOT" "$ARENA"
mkdir -p "$ENVROOT/home/.agents/plugins" "$ENVROOT/home/plugins" "$ENVROOT/codex-home" \
         "$ENVROOT/homeu/.agents/plugins" "$ENVROOT/homeu/plugins" "$ENVROOT/codex-home-u" \
         "$ARENA/upg" "$ARENA/p" "$ARENA/gh" "$ARENA/reg"
ln -s "$REPO_ROOT/plugin" "$ENVROOT/home/plugins/mygamestudio"
for mh in "$ENVROOT/home/.agents/plugins" "$ENVROOT/homeu/.agents/plugins"; do
  cat > "$mh/marketplace.json" <<'EOF'
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
done
ln -s "$REAL_HOME/.codex/auth.json" "$ENVROOT/codex-home/auth.json"
ln -s "$REAL_HOME/.codex/auth.json" "$ENVROOT/codex-home-u/auth.json"
write_config() { # write_config <config.toml>
  { printf 'check_for_update_on_startup = false\n'
    [ -n "${MGS_PIN_MODEL:-}" ] && printf '\nmodel = "%s"\n' "$MGS_PIN_MODEL"
    true; } > "$1"
}
write_config "$ENVROOT/codex-home/config.toml"
write_config "$ENVROOT/codex-home-u/config.toml"

export HOME="$ENVROOT/home"
export CODEX_HOME="$ENVROOT/codex-home"

codex plugin list --json --available > "$EVIDENCE_DIR/plugin-available.json" 2>&1
check_contains "marketplace 可发现 mygamestudio 0.18.0" "$EVIDENCE_DIR/plugin-available.json" '"mygamestudio"'
codex plugin add mygamestudio@personal --json > "$EVIDENCE_DIR/plugin-install.json" 2>&1
check_contains "安装成功并返回安装路径" "$EVIDENCE_DIR/plugin-install.json" '"installedPath"'
INSTALLED=$(python3 -c "import json;print(json.load(open('$EVIDENCE_DIR/plugin-install.json'))['installedPath'])" 2>/dev/null || true)
if [ -z "$INSTALLED" ]; then bad "未取得安装路径"; exit 1; fi
echo "installed: $INSTALLED" >> "$EVIDENCE_DIR/environment.txt"
check "安装副本与仓库 plugin/ 逐字节一致" diff -r -x __pycache__ -x .DS_Store "$REPO_ROOT/plugin" "$INSTALLED"

mkdir -p "$ENVROOT/instances/n1" "$ENVROOT/instances/ws-p" "$ENVROOT/instances/ws-d" \
         "$ENVROOT/instances/ws-g" "$ENVROOT/instances/ws-r" "$ENVROOT/instances/ws-u" "$ENVROOT/instances/ws-s"
for d in n1 ws-p ws-d ws-g ws-r ws-u ws-s; do
  (cd "$ENVROOT/instances/$d" && git init -q . 2>/dev/null; git config user.email t@t; git config user.name t)
done

# 技能注册面:恰好 14 个入口,名称与预期一致
python3 "$MGS_CLIENT" skills --cwd "$ENVROOT/instances/n1" > "$EVIDENCE_DIR/skills-list.jsonl" 2>&1
python3 -B - "$EVIDENCE_DIR/skills-list.jsonl" > "$EVIDENCE_DIR/skills-surface.json" <<'PYEOF'
import json, sys
expected = {"game-art", "game-audio", "game-build", "game-code", "game-design",
            "game-implement", "game-init", "game-plan", "game-playtest",
            "game-producer", "game-prototype", "game-review", "game-spec",
            "game-status"}
names, others = set(), []
for line in open(sys.argv[1]):
    try:
        rec = json.loads(line)
    except json.JSONDecodeError:
        continue
    if rec.get("pluginId") == "mygamestudio@personal":
        names.add(str(rec.get("name", "")).split(":", 1)[-1])
    elif rec.get("pluginId"):
        others.append(rec.get("pluginId"))
print(json.dumps({"count": len(names), "names": sorted(names),
                  "exact": names == expected, "other_plugins": others},
                 ensure_ascii=False))
PYEOF
check_json "注册面恰好 14 个业务入口(名称与设计一致)" "$EVIDENCE_DIR/skills-surface.json" \
  "data['exact'] is True and data['count'] == 14"
check_json "本插件之外无其他插件技能混入" "$EVIDENCE_DIR/skills-surface.json" \
  "data['other_plugins'] == []"

# 仅显式触发:模型可见目录不含任何业务入口(allow_implicit_invocation: false)
(cd "$ENVROOT/instances/n1" && codex debug prompt-input \
  '帮我看看这个游戏项目现在的进展,接下来做什么好?' \
  > "$EVIDENCE_DIR/prompt-input-implicit-probe.json" 2>&1)
MISSING=0
for s in game-art game-audio game-build game-code game-design game-implement \
         game-init game-plan game-playtest game-producer game-prototype \
         game-review game-spec game-status; do
  grep -q "$s" "$EVIDENCE_DIR/prompt-input-implicit-probe.json" && MISSING=$((MISSING+1))
done
check "模型可见目录不含任何 game-* 入口(十四入口全部仅显式触发)" test "$MISSING" = "0"

# 指纹/许可/引用对安装副本复算;通用方法作为包内依赖可定位
python3 -B - "$INSTALLED" > "$EVIDENCE_DIR/installed-fingerprints.txt" <<'PYEOF'
import hashlib, json, sys
from pathlib import Path
root = Path(sys.argv[1])
data = json.loads((root / "provenance/fingerprints.json").read_text())
bad = []
for entry in data["files"]:
    p = root / entry["path"]
    if not p.is_file():
        bad.append(f"missing {entry['path']}")
        continue
    if hashlib.sha256(p.read_bytes()).hexdigest() != entry["sha256"]:
        bad.append(f"sha mismatch {entry['path']}")
methods = sorted(str(p.relative_to(root)) for p in (root / "internal/methods").rglob("*") if p.is_file())
print("generated_for:", data["generated_for"])
print("fingerprint_files:", len(data["files"]), "bad:", bad if bad else "none")
print("methods_present:", len(methods))
print("license:", (root / "provenance/licenses/mattpocock-skills-LICENSE.txt").is_file())
print("VERSION:", json.loads((root / ".codex-plugin/plugin.json").read_text())["version"])
PYEOF
check_contains "安装副本逐文件指纹复算全部一致" "$EVIDENCE_DIR/installed-fingerprints.txt" "bad: none"
check_contains "通用方法随包可定位(15 个文件)" "$EVIDENCE_DIR/installed-fingerprints.txt" "methods_present: 15"
check_contains "许可文本随包" "$EVIDENCE_DIR/installed-fingerprints.txt" "license: True"
check_contains "安装副本版本为 0.18.0" "$EVIDENCE_DIR/installed-fingerprints.txt" "VERSION: 0.18.0"
if grep -rq '/Users/' "$INSTALLED" --include='*' 2>/dev/null | grep -v __pycache__ | grep -q .; then
  bad "安装副本引用了开发机绝对路径"
else
  ok "安装副本不含开发机绝对路径"
fi

# ---------- 3. N1 普通对话对照(不触发) ----------

say "== 3. N1 普通对话对照:无提及的真实 turn =="
cp -R "$ATLAS_FIXTURE" "$ENVROOT/projects-n1" 2>/dev/null || { mkdir -p "$ENVROOT/projects-n1"; cp -R "$ATLAS_FIXTURE/." "$ENVROOT/projects-n1/"; }
(cd "$ENVROOT/projects-n1" && git init -q . 2>/dev/null; git config user.email t@t; git config user.name t)
hash_tree "$ENVROOT/projects-n1" "$EVIDENCE_DIR/n1-before.sha256"
python3 "$MGS_CLIENT" turn --cwd "$ENVROOT/projects-n1" --sandbox workspace-write \
  --text "帮我看看这个项目接下来做什么好?顺便总结一下当前进展。" \
  --out "$EVIDENCE_DIR/n1-report.md" --events-out "$EVIDENCE_DIR/n1-events.jsonl" \
  --timeout 600 > "$EVIDENCE_DIR/n1-runlog.txt" 2>&1
check "N1 turn 完整结束" grep -q 'turn/completed' "$EVIDENCE_DIR/n1-events.jsonl"
check "N1 产生回答" test -s "$EVIDENCE_DIR/n1-report.md"
check "N1 无 mgs-gate 工具调用(事件流无 mcpToolCall)" \
  test -z "$(grep -c '"type": "mcpToolCall"' "$EVIDENCE_DIR/n1-events.jsonl" | grep -v '^0$')"
check "N1 未调用包内统一接口/运行组件(命令事件无 mgs 记录)" \
  test -z "$(grep '"type": "commandExecution"' "$EVIDENCE_DIR/n1-events.jsonl" | grep -c 'mgs' | grep -v '^0$')"
check_not_contains "N1 未产出任何业务入口的结构化报告" "$EVIDENCE_DIR/n1-report.md" \
  '## 项目状态报告' '## 接入报告' '## 设计讨论报告' '## 规格整理报告' '## 统筹工作报告'
hash_tree "$ENVROOT/projects-n1" "$EVIDENCE_DIR/n1-after.sha256"
check "N1 零写入(项目哈希前后一致)" diff "$EVIDENCE_DIR/n1-before.sha256" "$EVIDENCE_DIR/n1-after.sha256"

# ---------- 4. U 环:真实版本升级 0.17.0 → 0.18.0 ----------

say "== 4. U 环:真实升级(旧版安装→初始化→手工修改→升级→模板升级核对) =="

# 4.1 旧版来源与安装(独立 homeu/codex-home-u)
git -C "$REPO_ROOT" archive "$OLD_COMMIT" plugin | tar -x -C "$ENVROOT/homeu/plugins"
mv "$ENVROOT/homeu/plugins/plugin" "$ENVROOT/homeu/plugins/mygamestudio"
HOME="$ENVROOT/homeu" CODEX_HOME="$ENVROOT/codex-home-u" \
  codex plugin add mygamestudio@personal --json > "$EVIDENCE_DIR/plugin-install-old.json" 2>&1
check_contains "旧版 0.17.0 安装成功" "$EVIDENCE_DIR/plugin-install-old.json" '"installedPath"'
INSTALLED_OLD=$(python3 -c "import json;print(json.load(open('$EVIDENCE_DIR/plugin-install-old.json'))['installedPath'])")
OLD_VERSION=$(python3 -c "import json;print(json.load(open('$INSTALLED_OLD/.codex-plugin/plugin.json'))['version'])")
check "旧版安装副本版本为 0.17.0" test "$OLD_VERSION" = "0.17.0"
cp -R "$INSTALLED_OLD" "$ARENA/upg/installed-old-snapshot"
ok "旧版安装副本已快照(供升级 diff;remove 会清缓存)"
echo "installed-old: $INSTALLED_OLD" >> "$EVIDENCE_DIR/environment.txt"

# 4.2 升级剧场项目与运行保障
mkdir -p "$PROJ_U"
cat > "$PROJ_U/README.md" <<'EOF'
# atlas-fall(新项目)

60 秒下落收集小游戏:操控收集器接住星尘、避开碎岩。
本轮先做计分骨架(起始任务 01-score-keeper,完成标准:无头检查可见计分变化)。
工程入口:src/(单文件 ES 模块骨架,见 src/main.js)。
EOF
mkdir -p "$PROJ_U/src"
printf '// atlas-fall 骨架\nexport const ROUND_SECONDS = 60;\n' > "$PROJ_U/src/main.js"
(cd "$PROJ_U" && git init -q . && git config user.email t@t && git config user.name t)
cat > "$ARENA/upg/policy-spec.json" <<EOF
{
  "project_root": "$PROJ_U",
  "roles": {
    "producer": ["docs/mygamestudio/**"]
  },
  "purposes": {"production": null}
}
EOF
python3 -B "$PLUGIN_RUNTIME/mgsrt_admin.py" --runtime-root "$RUNROOT_U" init-policy \
  --spec "$ARENA/upg/policy-spec.json" > "$EVIDENCE_DIR/upg-init-policy.json" 2>&1
check_contains "U 环策略初始化完成" "$EVIDENCE_DIR/upg-init-policy.json" '"producer"'

mk_instance() { # mk_instance <运行根> <输出前缀> <role> <task> <ttl分> <resource>...
  local runroot="$1" prefix="$2" role="$3" task="$4" ttl="$5"; shift 5
  local args=() r
  for r in "$@"; do args+=(--resource "$r"); done
  python3 -B "$PLUGIN_RUNTIME/mgsrt_admin.py" --runtime-root "$runroot" \
    create-instance --role "$role" --task "$task" --purpose production \
    --ttl-mins "$ttl" "${args[@]}" > "$ARENA/$prefix.json" 2>/dev/null
  python3 -c "import json; print(json.load(open('$ARENA/$prefix.json'))['instance_id'])" > "$ARENA/$prefix.id"
  python3 -c "import json; print(json.load(open('$ARENA/$prefix.json'))['token'])" > "$ARENA/$prefix.token"
}

mk_instance "$RUNROOT_U" u_p producer 18-upg 480 'docs/mygamestudio/**'
UP_ID=$(cat "$ARENA/u_p.id"); UP_TOK=$(cat "$ARENA/u_p.token")

run_turn() { # run_turn <前缀> <home> <codexhome> <运行根> <工作区> <mention或-> <文本> <超时秒>
  local prefix="$1" h="$2" ch="$3" rr="$4" ws="$5" mention="$6" text="$7" tmo="$8"
  if [ "$mention" = "-" ]; then
    HOME="$h" CODEX_HOME="$ch" MGS_RUNTIME_ROOT="$rr" \
      python3 "$MGS_CLIENT" turn --cwd "$ws" --sandbox workspace-write \
      --text "$text" \
      --out "$EVIDENCE_DIR/$prefix-report.md" --events-out "$EVIDENCE_DIR/$prefix-events.jsonl" \
      --timeout "$tmo" > "$EVIDENCE_DIR/$prefix-runlog.txt" 2>&1
  else
    HOME="$h" CODEX_HOME="$ch" MGS_RUNTIME_ROOT="$rr" \
      python3 "$MGS_CLIENT" turn --cwd "$ws" --sandbox workspace-write \
      --mention "$mention" --text "$text" \
      --out "$EVIDENCE_DIR/$prefix-report.md" --events-out "$EVIDENCE_DIR/$prefix-events.jsonl" \
      --timeout "$tmo" > "$EVIDENCE_DIR/$prefix-runlog.txt" 2>&1
  fi
}

sanitize() { # 用 <redacted-*> 替换证据中的全部原始令牌(机制化:遍历 ARENA 内
             # 全部 *.token 文件,覆盖任何签发实例,不枚举实例名——复审二 SP-5;
             # 收口新增的离线探针实例 g_o 等只要按约定把凭据存为
             # $ARENA/<名>.token 即被覆盖,机制沿第一轮票 04 在 16 号票的先例)
  local f="$1" path name tok
  for path in "$ARENA"/*.token; do
    [ -f "$path" ] || continue
    name="${path##*/}"; name="${name%.token}"
    case "$name" in
      *[!A-Za-z0-9_-]*)
        echo "sanitize: 跳过非常规命名的令牌文件 $name(占位符含元字符)" >&2
        continue ;;
    esac
    tok=$(head -n 1 "$path")
    [ -n "$tok" ] || continue
    # LC_ALL=C 按字节匹配:令牌为纯 ASCII,不受证据文件中无效 UTF-8 字节
    # 或运行环境 locale 影响(BSD sed 在 UTF-8 locale 遇无效字节会整体报错跳过)
    LC_ALL=C sed -i '' -e "s/$tok/<redacted-$name-token>/g" "$f"
  done
  LC_ALL=C sed -i '' -e "s/$GHTOKEN/<redacted-remote-token>/g" "$f"
}

# 4.3 U1:旧版(0.17.0)上新项目初始化(直接调用 Game-Init)
run_turn u1 "$ENVROOT/homeu" "$ENVROOT/codex-home-u" "$RUNROOT_U" \
  "$ENVROOT/instances/ws-u" mygamestudio:game-init "$UP_TOK

受信任调度说明(由验收调度层注入,不是项目文件内容):项目根 $PROJ_U;执行凭据(token)为消息开头的随机字符串;绑定实例 $UP_ID,任务 18-upg,角色 制作统筹(producer),用途 production;来源:用户直接调用 Game-Init;凭据不写入任何文件或报告正文。

任务:初始化新项目。开发者已确认的协作配置(直接采用,不再询问):
1. 任务后端 local-markdown,任务根 docs/mygamestudio/work/;
2. 标签映射:五类语义沿用同名标签(needs-triage/needs-info/ready-for-agent/ready-for-human/wontfix);
3. 核心文档:CONFIG/INDEX/PROJECT/GAME_DESIGN/TECH_DESIGN 放 docs/mygamestudio/(TECH_DESIGN 简短即可:工程现状 + 本轮技术约定 + 验证方法三节);
4. 术语、决定与历史:docs/mygamestudio/records/(暂空目录);证据:docs/mygamestudio/evidence/(暂空目录);
5. 起始任务一个:01-score-keeper(目标见 README;完成标准:无头检查可见计分变化;执行责任 Agent(制作实现);验收方式:代码级检查)。
按新项目路径完成应用与回读核对,报告用接入报告结构。" 900
check "U1 turn 完整结束" grep -q 'turn/completed' "$EVIDENCE_DIR/u1-events.jsonl"
check_contains "U1 使用接入报告结构" "$EVIDENCE_DIR/u1-report.md" '## 接入报告'
for f in CONFIG.md INDEX.md PROJECT.md GAME_DESIGN.md TECH_DESIGN.md work/01-score-keeper/task.md; do
  check "U1 建立了 $f" test -f "$PROJ_U/docs/mygamestudio/$f"
done
python3 -B "$PLUGIN_RECORDS/mgs_records.py" verify --project "$PROJ_U" \
  > "$EVIDENCE_DIR/upg-verify-after-u1.json" 2>&1
check_json "U1 后统一接口 verify 通过(旧版包完成初始化)" "$EVIDENCE_DIR/upg-verify-after-u1.json" "data['ok'] is True"
check "U1 报告不含原始令牌" test -z "$(grep -cF "$UP_TOK" "$EVIDENCE_DIR/u1-report.md" | grep -v '^0$')"

# 4.4 用户手工修改(模拟开发者本人绕过通道的修改)+ 升级前快照
{
  echo "$(date -Iseconds) 开发者注:计分骨架之外我想加连击,先记在这里。"
} >> "$PROJ_U/docs/mygamestudio/PROJECT.md"
{
  echo ""
  echo "$(date -Iseconds) 开发者注:完成标准里『可见计分变化』我理解为状态断言即可,不需要渲染。"
} >> "$PROJ_U/docs/mygamestudio/work/01-score-keeper/task.md"
cp "$PROJ_U/docs/mygamestudio/PROJECT.md" "$EVIDENCE_DIR/upg-user-edit-project.md"
cp "$PROJ_U/docs/mygamestudio/work/01-score-keeper/task.md" "$EVIDENCE_DIR/upg-user-edit-task.md"
ok "用户手工修改已注入并留档(PROJECT 与任务 01 各一条开发者注)"
hash_tree "$PROJ_U" "$EVIDENCE_DIR/upg-before-upgrade.sha256"
mkdir -p "$ARENA/upg/gov-before"
for gfile in "$ENVROOT/homeu/.agents/plugins/marketplace.json" "$ENVROOT/codex-home-u/config.toml" \
             "$RUNROOT_U/policy.json" "$RUNROOT_U/instances.json"; do
  cp "$gfile" "$ARENA/upg/gov-before/$(basename "$gfile")"
done
(cd "$ENVROOT/homeu" && find . -type f ! -path '*/__pycache__/*' | LC_ALL=C sort) > "$EVIDENCE_DIR/upg-home-files-before.txt"

# 4.5 真实升级:换源 → remove → add
rm -rf "$ENVROOT/homeu/plugins/mygamestudio"
cp -R "$REPO_ROOT/plugin" "$ENVROOT/homeu/plugins/mygamestudio"
HOME="$ENVROOT/homeu" CODEX_HOME="$ENVROOT/codex-home-u" \
  codex plugin remove mygamestudio@personal --json > "$EVIDENCE_DIR/plugin-remove.json" 2>&1
check_contains "codex plugin remove 成功" "$EVIDENCE_DIR/plugin-remove.json" 'mygamestudio'
HOME="$ENVROOT/homeu" CODEX_HOME="$ENVROOT/codex-home-u" \
  codex plugin add mygamestudio@personal --json > "$EVIDENCE_DIR/plugin-install-new.json" 2>&1
check_contains "升级后重新安装成功" "$EVIDENCE_DIR/plugin-install-new.json" '"installedPath"'
INSTALLED_NEW=$(python3 -c "import json;print(json.load(open('$EVIDENCE_DIR/plugin-install-new.json'))['installedPath'])")
NEW_VERSION=$(python3 -c "import json;print(json.load(open('$INSTALLED_NEW/.codex-plugin/plugin.json'))['version'])")
check "升级后安装副本版本为 0.18.0" test "$NEW_VERSION" = "0.18.0"
check "升级后安装副本与仓库 plugin/ 逐字节一致" \
  diff -r -x __pycache__ -x .DS_Store "$REPO_ROOT/plugin" "$INSTALLED_NEW"
echo "installed-new: $INSTALLED_NEW" >> "$EVIDENCE_DIR/environment.txt"
# 变更集从 git 推导(0.17.0 提交→当前 HEAD 的 plugin/ 实际变更),不枚举文件清单
# ——审查修复批在 0.18.0 交付后改动了后端/运行时文件而版本号未递增,硬编码
# 清单会随后续修复过时;推导口径=「升级让 0.17.0 以来全部实际变更可发现」
UPGRADE_EXPECTED=$(git -C "$REPO_ROOT" diff --name-only "$OLD_COMMIT"..HEAD -- plugin/ | sed 's|^plugin/||' | sort)
python3 -B - "$ARENA/upg/installed-old-snapshot" "$INSTALLED_NEW" $UPGRADE_EXPECTED > "$EVIDENCE_DIR/upgrade-changed-set.json" <<'PYEOF'
import hashlib, json, sys
from pathlib import Path
def tree(root: Path):
    out = {}
    for p in root.rglob("*"):
        if p.is_file() and "__pycache__" not in p.parts and p.name != ".DS_Store":
            out[str(p.relative_to(root))] = hashlib.sha256(p.read_bytes()).hexdigest()
    return out
old, new = tree(Path(sys.argv[1])), tree(Path(sys.argv[2]))
changed = sorted(k for k in old.keys() & new.keys() if old[k] != new[k])
only = sorted(old.keys() ^ new.keys())
expected = sorted(sys.argv[3:])
print(json.dumps({"changed": changed, "expected": expected,
                  "expected_source": "git diff --name-only OLD_COMMIT..HEAD -- plugin/(推导)",
                  "exact": set(changed) == set(expected) and not only,
                  "only_in_one_side": only}, ensure_ascii=False))
PYEOF
diff -r -x __pycache__ -x .DS_Store "$ARENA/upg/installed-old-snapshot" "$INSTALLED_NEW" \
  > "$EVIDENCE_DIR/upgrade-install-diff.txt" 2>&1 || true
check_json "安装副本 diff 恰为 0.17.0→当前交付的变更集(git 推导,依赖变化可发现)" \
  "$EVIDENCE_DIR/upgrade-changed-set.json" "data['exact'] is True and data['only_in_one_side'] == []"
check_contains "新模板带 issues-write 授权记录格式说明" "$INSTALLED_NEW/templates/project/CONFIG.md" \
  'issues-write' 'host/owner/repository'
HOME="$ENVROOT/homeu" CODEX_HOME="$ENVROOT/codex-home-u" \
  python3 "$MGS_CLIENT" skills --cwd "$ENVROOT/instances/ws-u" > "$EVIDENCE_DIR/skills-list-after-upgrade.jsonl" 2>&1
UP_SKILLS=$(grep -c '"pluginId": "mygamestudio@personal"' "$EVIDENCE_DIR/skills-list-after-upgrade.jsonl" || true)
check "升级后注册面仍恰好 14 个入口" test "$UP_SKILLS" = "14"
python3 -B - "$ARENA/upg/gov-before" "$ENVROOT/homeu/.agents/plugins/marketplace.json" \
  "$ENVROOT/codex-home-u/config.toml" "$RUNROOT_U/policy.json" "$RUNROOT_U/instances.json" \
  > "$EVIDENCE_DIR/upg-governance-check.json" <<'PYEOF'
import json, sys
from pathlib import Path
before_dir = Path(sys.argv[1])
report = {}
def toml_sections(text: str) -> dict:
    cur, out = "__top__", {}
    for line in text.splitlines():
        s = line.strip()
        if s.startswith("[") and s.endswith("]"):
            cur = s
        out.setdefault(cur, []).append(line)
    # strip:codex 重写 config.toml 时段序与段尾空行可能变化,内容比对忽略之
    return {k: "\n".join(v).strip() for k, v in out.items()}
for path in sys.argv[2:]:
    name = Path(path).name
    before = (before_dir / name).read_text()
    after = Path(path).read_text()
    if name == "config.toml":
        kb = {k: v for k, v in toml_sections(before).items() if not k.startswith("[plugins.")}
        ka = {k: v for k, v in toml_sections(after).items() if not k.startswith("[plugins.")}
        plugin_secs = [k for k in toml_sections(after) if k.startswith("[plugins.")]
        report[name] = {
            "content_equal_except_codex_plugin_sections": kb == ka,
            "plugin_sections": plugin_secs,
            "plugin_sections_all_mygamestudio": all("mygamestudio" in k for k in plugin_secs),
        }
    else:
        report[name] = {"bytes_equal": before == after}
print(json.dumps(report, ensure_ascii=False))
PYEOF
check_json "升级未改写客户端治理(marketplace/policy/instances 字节不变)" \
  "$EVIDENCE_DIR/upg-governance-check.json" \
  "data['marketplace.json']['bytes_equal'] is True and data['policy.json']['bytes_equal'] is True and data['instances.json']['bytes_equal'] is True"
check_json "config.toml 除 codex 自管插件启用段外内容不变(且插件段仅 mygamestudio)" \
  "$EVIDENCE_DIR/upg-governance-check.json" \
  "data['config.toml']['content_equal_except_codex_plugin_sections'] is True and data['config.toml']['plugin_sections_all_mygamestudio'] is True"
(cd "$ENVROOT/homeu" && find . -type f ! -path '*/__pycache__/*' | LC_ALL=C sort) > "$EVIDENCE_DIR/upg-home-files-after.txt"
check "升级只更换了插件来源目录(home 文件清单不变)" \
  diff "$EVIDENCE_DIR/upg-home-files-before.txt" "$EVIDENCE_DIR/upg-home-files-after.txt"

# 4.6 U2:新版(0.18.0)模板升级与重复运行核对
cat > "$ARENA/upg/confirm-upg.md" <<EOF
# 模板升级确认(开发者,$(date -Iseconds))

1. CONFIG.md「外部连接引用及已确认操作范围」行按 0.18.0 模板补充授权记录格式说明
   (host/owner/repository:issues-write(说明),未记录即未授权);当前值仍为「无」,
   任务后端保持 local-markdown 不变。
2. 其余文档与新模板无差异,不动。
3. 我在 PROJECT.md 与任务 01 中追加的开发者注必须原样保留。
4. GAME_DESIGN 与任务记录本轮不动。
EOF
cp "$ARENA/upg/confirm-upg.md" "$EVIDENCE_DIR/upg-confirm.md"
run_turn u2 "$ENVROOT/homeu" "$ENVROOT/codex-home-u" "$RUNROOT_U" \
  "$ENVROOT/instances/ws-u" mygamestudio:game-init "$UP_TOK

受信任调度说明(同 U1:项目根 $PROJ_U;绑定实例 $UP_ID,任务 18-upg,角色 制作统筹(producer);凭据不写入任何文件或报告正文)。

背景:插件已从 0.17.0 升级到 0.18.0(模板与来源说明有更新)。任务:对本项目执行「模板升级 + 重复运行」核对:
1) 对比安装位置当前模板与项目已实例化文档,产出具体变更清单与保留方案;
2) 开发者确认清单见 $ARENA/upg/confirm-upg.md(已确认,直接按清单应用,写入带 expected_sha256);
3) 应用后回读核对;重复运行部分:确认清单外无缺口项,报告无需改动;
4) 报告用接入报告结构,模板升级轮给出:模板对比与具体变更、保留方案执行结果、已完成/剩余/需重新确认。" 900
check "U2 turn 完整结束" grep -q 'turn/completed' "$EVIDENCE_DIR/u2-events.jsonl"
check_contains "U2 使用接入报告结构" "$EVIDENCE_DIR/u2-report.md" '## 接入报告'
check_contains "U2 报告覆盖模板升级要素" "$EVIDENCE_DIR/u2-report.md" '模板'
check_contains "U2 报告区分已完成/剩余或需重新确认" "$EVIDENCE_DIR/u2-report.md" '剩余'
check "U2 CONFIG 已更新(带授权格式说明)" grep -q 'issues-write' "$PROJ_U/docs/mygamestudio/CONFIG.md"
check "U2 后端保持 local-markdown(当前后端保留)" grep -qE -- '- 后端[:：]local-markdown' "$PROJ_U/docs/mygamestudio/CONFIG.md"
check "U2 保留开发者注(PROJECT)" grep -q '开发者注' "$PROJ_U/docs/mygamestudio/PROJECT.md"
check "U2 保留开发者注(任务 01)" grep -q '开发者注' "$PROJ_U/docs/mygamestudio/work/01-score-keeper/task.md"
BEFORE_HASH=$(grep 'GAME_DESIGN.md' "$EVIDENCE_DIR/upg-before-upgrade.sha256" | awk '{print $1}')
AFTER_HASH=$(shasum -a 256 "$PROJ_U/docs/mygamestudio/GAME_DESIGN.md" | awk '{print $1}')
check "U2 GAME_DESIGN 字节不变(用户文档不被重建)" test "$BEFORE_HASH" = "$AFTER_HASH"
check "U2 任务目录仍恰一个(无重复资料)" test "$(find "$PROJ_U/docs/mygamestudio/work" -mindepth 1 -maxdepth 1 -type d | wc -l | tr -d ' ')" = "1"
check "U2 统一接口 verify 通过" python3 -B "$PLUGIN_RECORDS/mgs_records.py" verify --project "$PROJ_U"
check "U2 报告不含原始令牌" test -z "$(grep -cF "$UP_TOK" "$EVIDENCE_DIR/u2-report.md" | grep -v '^0$')"
sanitize "$EVIDENCE_DIR/u1-report.md"; sanitize "$EVIDENCE_DIR/u1-events.jsonl"; sanitize "$EVIDENCE_DIR/u1-runlog.txt"
sanitize "$EVIDENCE_DIR/u2-report.md"; sanitize "$EVIDENCE_DIR/u2-events.jsonl"; sanitize "$EVIDENCE_DIR/u2-runlog.txt"

# ---------- 5. P 环:代表性闭环(已有项目/本地/目标变化/统筹委派/直接调用) ----------

say "== 5. P 环:atlas-drop 目标变化 + 委派设计 + 直接状态检查 =="
cp -R "$ATLAS_FIXTURE" "$PROJ_P"
(cd "$PROJ_P" && git init -q . && git config user.email t@t && git config user.name t)
cat > "$ARENA/p/policy-spec.json" <<EOF
{
  "project_root": "$PROJ_P",
  "roles": {
    "producer": ["docs/mygamestudio/PROJECT.md", "docs/mygamestudio/work/**",
                  "docs/mygamestudio/CONFIG.md", "docs/mygamestudio/INDEX.md"],
    "design": ["docs/mygamestudio/records/**", "prototypes/**"]
  },
  "purposes": {"production": null}
}
EOF
python3 -B "$PLUGIN_RUNTIME/mgsrt_admin.py" --runtime-root "$RUNROOT_P" init-policy \
  --spec "$ARENA/p/policy-spec.json" > "$EVIDENCE_DIR/p-init-policy.json" 2>&1
check_contains "P 环策略初始化完成(producer/design 分权)" "$EVIDENCE_DIR/p-init-policy.json" '"design"'
mk_instance "$RUNROOT_P" p_p producer 18-goal-change 300 \
  'docs/mygamestudio/PROJECT.md' 'docs/mygamestudio/work/**'
mk_instance "$RUNROOT_P" p_d design 18-speed-map 300 'docs/mygamestudio/records/**'
PP_ID=$(cat "$ARENA/p_p.id"); PP_TOK=$(cat "$ARENA/p_p.token")
PD_ID=$(cat "$ARENA/p_d.id"); PD_TOK=$(cat "$ARENA/p_d.token")

run_turn p1 "$ENVROOT/home" "$ENVROOT/codex-home" "$RUNROOT_P" \
  "$ENVROOT/instances/ws-p" mygamestudio:game-producer "$PP_TOK

受信任调度说明(由验收调度层注入):项目根 $PROJ_P;执行凭据为消息开头的随机字符串;绑定实例 $PP_ID,任务 18-goal-change,角色 制作统筹(producer),用途 production;来源:用户直接调用 Game-Producer;凭据不写入任何文件或报告正文。

任务(开发者请求,原文):「目标变更:护盾拾取(01)延后到下一轮;本轮改为优先做下落速度调优(02),速度调优的完成标准先由设计讨论收敛,再回填任务。」

按 Game-Producer 纪律执行:
1) 入口分类;
2) 目标变化影响检查(受影响管理依据与任务;原版本完成事实保留);
3) 管理写入:PROJECT.md v1→v2(变更索引记录本次目标变更与依据,expected_sha256);任务 01 重分流 needs-triage 并在状态变化记录来源;任务 02 升 ready-for-agent、依赖改为无(01 已延后)、完成标准暂记「待设计讨论收敛后回填」;
4) 委派:把「下落速度调优区间与护盾时长候选」的设计问题委派 Game-Design 建决策地图(制图轮只画图不裁决),在报告中给出委派工作请求;
5) 越界探针(原样记录被拒结果,不重试):用本凭据 mgs_write 尝试把「# 越界」写入 docs/mygamestudio/GAME_DESIGN.md(expected_sha256 用 absent);
6) 报告用统筹工作报告结构。" 900
check "P1 turn 完整结束" grep -q 'turn/completed' "$EVIDENCE_DIR/p1-events.jsonl"
check_contains "P1 使用统筹工作报告结构" "$EVIDENCE_DIR/p1-report.md" '## 统筹工作报告' '### 入口分类'
check "P1 PROJECT 升到 v2 且记录目标变更" grep -qE '基线版本[:：]v2' "$PROJ_P/docs/mygamestudio/PROJECT.md"
check "P1 任务 01 重分流 needs-triage" grep -qE '当前分流[:：]needs-triage' "$PROJ_P/docs/mygamestudio/work/01-shield-pickup/task.md"
check "P1 任务 01 状态变化记录来源" grep -q '目标变更' "$PROJ_P/docs/mygamestudio/work/01-shield-pickup/task.md"
check "P1 任务 02 升 ready-for-agent 且依赖清空" grep -qE '当前分流[:：]ready-for-agent' "$PROJ_P/docs/mygamestudio/work/02-speed-tune/task.md"
grep -qE '依赖[:：]无' "$PROJ_P/docs/mygamestudio/work/02-speed-tune/task.md" \
  && ok "P1 任务 02 依赖改为无" || bad "P1 任务 02 依赖未改"
check_contains "P1 报告含委派工作请求" "$EVIDENCE_DIR/p1-report.md" '### 委派工作请求'
check "P1 越界探针被拒(报告记录 deny 与 rule_stage)" grep -qE 'role_scope|task_grant|被拒' "$EVIDENCE_DIR/p1-report.md"
check "P1 越界写入被拒(mgs_write deny,事件流锚定)" \
  test "$(mcp_deny_anchor "$EVIDENCE_DIR/p1-events.jsonl" mgs_write 'role_scope|task_grant' docs/mygamestudio/GAME_DESIGN.md write)" = "OK"
check "P1 GAME_DESIGN 未被统筹改写(仍 v1)" grep -qE '基线版本[:：]v1' "$PROJ_P/docs/mygamestudio/GAME_DESIGN.md"
python3 -B "$PLUGIN_RECORDS/mgs_records.py" ready --project "$PROJ_P" \
  > "$EVIDENCE_DIR/p-ready-after-p1.json" 2>&1
check_json "P1 后可开工集合恰为 02(依赖重排生效)" "$EVIDENCE_DIR/p-ready-after-p1.json" \
  "[t['identity'] for t in data['startable']] == ['02-speed-tune']"

# P2:被委派的 Game-Design 决策地图轮(设计角色,统筹委派来源)
run_turn p2 "$ENVROOT/home" "$ENVROOT/codex-home" "$RUNROOT_P" \
  "$ENVROOT/instances/ws-d" mygamestudio:game-design "$PD_TOK

受信任调度说明(由验收调度层注入):项目根 $PROJ_P;执行凭据为消息开头的随机字符串;绑定实例 $PD_ID,任务 18-speed-map,角色 方案设计(design),用途 production;来源:制作统筹委派(见统筹工作报告的委派工作请求);凭据不写入任何文件或报告正文。

任务(制图轮,只画图不裁决):为「下落速度调优区间与护盾时长候选」建立决策地图。读 PROJECT v2 与 GAME_DESIGN v1,把可精确表述的决定点列为决策工单(标注类型与阻塞关系),看不清的入未定雾区,目的地外的入范围外;地图写入 docs/mygamestudio/records/decision-map-speed-shield.md(按包内决策地图记录格式);不代替开发者作任何决定;不写 GAME_DESIGN。
越界探针(原样记录被拒结果,不重试):用本凭据 mgs_write 尝试把「# 越界」写入 docs/mygamestudio/GAME_DESIGN.md(expected_sha256 用 absent)。
报告用设计讨论报告结构。" 900
check "P2 turn 完整结束" grep -q 'turn/completed' "$EVIDENCE_DIR/p2-events.jsonl"
check_contains "P2 使用设计讨论报告结构" "$EVIDENCE_DIR/p2-report.md" '## 设计讨论报告'
check "P2 决策地图落盘(records/)" test -f "$PROJ_P/docs/mygamestudio/records/decision-map-speed-shield.md"
check_contains "P2 决策地图含目的地/工单/雾区/范围外" \
  "$PROJ_P/docs/mygamestudio/records/decision-map-speed-shield.md" '目的地' '工单' '雾区' '范围外'
check "P2 不改 GAME_DESIGN(基线仍 v1)" grep -qE '基线版本[:：]v1' "$PROJ_P/docs/mygamestudio/GAME_DESIGN.md"
check_contains "P2 报告明确未裁决/未决" "$EVIDENCE_DIR/p2-report.md" '未决'
check "P2 越界探针被拒(报告记录 deny 与 rule_stage)" grep -qE 'role_scope|task_grant|被拒' "$EVIDENCE_DIR/p2-report.md"
check "P2 越界写入被拒(mgs_write deny,事件流锚定)" \
  test "$(mcp_deny_anchor "$EVIDENCE_DIR/p2-events.jsonl" mgs_write 'role_scope|task_grant' docs/mygamestudio/GAME_DESIGN.md write)" = "OK"

# P3:直接调用 Game-Status(只读)
hash_tree "$PROJ_P" "$EVIDENCE_DIR/p-before-p3.sha256"
run_turn p3 "$ENVROOT/home" "$ENVROOT/codex-home" "$RUNROOT_P" \
  "$ENVROOT/instances/ws-s" mygamestudio:game-status "请检查项目当前状态。项目根:$PROJ_P" 600
check "P3 turn 完整结束" grep -q 'turn/completed' "$EVIDENCE_DIR/p3-events.jsonl"
check_contains "P3 使用项目状态报告结构" "$EVIDENCE_DIR/p3-report.md" '## 项目状态报告'
check_contains "P3 声明只读检查" "$EVIDENCE_DIR/p3-report.md" '只读检查'
check "P3 反映目标变更后的 PROJECT v2" grep -qE 'v2|速度调优' "$EVIDENCE_DIR/p3-report.md"
check "P3 反映任务 01 重分流" grep -q '01-shield-pickup' "$EVIDENCE_DIR/p3-report.md"
check "P3 提及可接续的设计讨论/决策地图" grep -qE '决策地图|设计讨论|速度' "$EVIDENCE_DIR/p3-report.md"
hash_tree "$PROJ_P" "$EVIDENCE_DIR/p-after-p3.sha256"
check "P3 零写入(与 P2 后基线一致)" diff "$EVIDENCE_DIR/p-before-p3.sha256" "$EVIDENCE_DIR/p-after-p3.sha256"
sanitize "$EVIDENCE_DIR/p1-report.md"; sanitize "$EVIDENCE_DIR/p1-events.jsonl"; sanitize "$EVIDENCE_DIR/p1-runlog.txt"
sanitize "$EVIDENCE_DIR/p2-report.md"; sanitize "$EVIDENCE_DIR/p2-events.jsonl"; sanitize "$EVIDENCE_DIR/p2-runlog.txt"
sanitize "$EVIDENCE_DIR/p3-report.md"; sanitize "$EVIDENCE_DIR/p3-events.jsonl"; sanitize "$EVIDENCE_DIR/p3-runlog.txt"

# ---------- 6. G 环:GitHub 替身上的代表性闭环 ----------

say "== 6. G 环:GitHub Issues 后端(本地替身)统筹远端操作 =="
cp -R "$HARBOR_FIXTURE" "$PROJ_G"
(cd "$PROJ_G" && git init -q . && git config user.email t@t && git config user.name t)
python3 -B "$STANDIN" --port 0 --token "$GHTOKEN" --state-file "$ARENA/gh/standin-state.json" \
  > "$ARENA/gh/standin.log" 2>&1 &
STANDIN_PID=$!
for _ in $(seq 1 50); do
  STANDIN_PORT=$(sed -n 's/^PORT //p' "$ARENA/gh/standin.log" 2>/dev/null)
  [ -n "$STANDIN_PORT" ] && break
  sleep 0.2
done
if [ -z "$STANDIN_PORT" ]; then bad "替身服务器未能启动"; cat "$ARENA/gh/standin.log"; exit 1; fi
ok "替身服务器监听 127.0.0.1:$STANDIN_PORT(令牌经参数注入)"

cat > "$ARENA/gh/policy-spec.json" <<EOF
{
  "project_root": "$PROJ_G",
  "roles": {
    "producer": ["docs/mygamestudio/CONFIG.md", "docs/mygamestudio/PROJECT.md",
                  "github://github.com/mygamestudio/issue-accept/issues/**"],
    "implement": ["src/**", "assets/**"]
  },
  "purposes": {"production": null}
}
EOF
python3 -B "$PLUGIN_RUNTIME/mgsrt_admin.py" --runtime-root "$RUNROOT_G" init-policy \
  --spec "$ARENA/gh/policy-spec.json" > "$EVIDENCE_DIR/gh-init-policy.json" 2>&1
export MGS_GITHUB_TOKEN="$GHTOKEN"
python3 -B "$PLUGIN_RUNTIME/mgsrt_admin.py" --runtime-root "$RUNROOT_G" set-remote-config \
  --api-base "http://127.0.0.1:$STANDIN_PORT" --token-env MGS_GITHUB_TOKEN \
  --cache-dir "$GH_CACHE" > "$EVIDENCE_DIR/gh-set-remote.json" 2>&1
check_contains "远端通道配置登记(凭据只登记环境变量名)" "$EVIDENCE_DIR/gh-set-remote.json" \
  '"token_env": "MGS_GITHUB_TOKEN"'

CLIBIN="python3 -B $PLUGIN_RECORDS/mgs_records.py"
APIFLAG="--api-base http://127.0.0.1:$STANDIN_PORT"
PFLAGS="--project $PROJ_G $APIFLAG --cache-dir $GH_CACHE"
mkdir -p "$GH_CACHE"

# 6.1 后端切换(调度侧,确认清单留档;语义同票 17 段 4)
$CLIBIN switch-plan --project "$PROJ_G" --target github-issues --repo "$REPO" \
  --emit "$ARENA/gh/switch-plan.json" > "$EVIDENCE_DIR/gh-switch-plan-cli.json" 2>&1
check_json "迁移清单覆盖两个既有任务且身份不变" "$ARENA/gh/switch-plan.json" \
  "[t['identity'] for t in data['tasks']] == ['01-harbor-timer', '02-crane-sprite']"
check_json "当前 CONFIG 尚无目标仓库写授权" "$ARENA/gh/switch-plan.json" "data['write_authorized'] is False"
cat > "$ARENA/gh/confirm.md" <<EOF
# 后端切换确认(开发者,$(date -Iseconds))

1. 确认迁移清单:两个既有任务迁往 GitHub Issues(替身),身份保持;旧本地记录保留只读历史。
2. 确认远端写入授权:仅对测试仓库 $REPO 授权 issues-write,记入 CONFIG 外部访问行。
3. 核心设计文档保留本地 Markdown 位置。
4. 切换后 CONFIG 由调度侧按本确认清单预置(唯一当前任务来源;票 17 已验收统筹经通道写入的语义)。
EOF
cp "$ARENA/gh/confirm.md" "$EVIDENCE_DIR/gh-confirm.md"
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
  --emit "$ARENA/gh/switch-plan.json" > "$EVIDENCE_DIR/gh-switch-plan-cli-auth.json" 2>&1
check_json "授权记入 CONFIG 后清单识别写授权" "$ARENA/gh/switch-plan.json" "data['write_authorized'] is True"
$CLIBIN switch-apply --project "$PROJ_G" --plan "$ARENA/gh/switch-plan.json" \
  --emit-dir "$GH_EMIT" --confirmed $APIFLAG > "$EVIDENCE_DIR/gh-switch-apply.json" 2>&1
check_json "apply 在替身创建两个远端任务" "$EVIDENCE_DIR/gh-switch-apply.json" "data['created'] == 2"
cp "$GH_EMIT/CONFIG.md" "$PROJ_G/docs/mygamestudio/CONFIG.md"
ok "切换后 CONFIG 已按确认清单预置(调度侧;来源=已确认迁移清单)"
$CLIBIN create $PFLAGS --identity 03-storm-warning --title "风暴预警" \
  --field "当前目标=最后阶段风暴预警" --field "完成标准=无头检查可见预警" \
  --field "执行责任=Agent(制作实现)" > "$EVIDENCE_DIR/gh-create-03.json" 2>&1
$CLIBIN create $PFLAGS --identity 04-fog-layer --title "海雾层" \
  --field "当前目标=海雾层视觉提示" --field "完成标准=雾层可视且不遮挡操作" \
  --field "执行责任=Agent(制作实现)" > "$EVIDENCE_DIR/gh-create-04.json" 2>&1
standin_state > "$EVIDENCE_DIR/gh-state-before-turn.json"
check_json "替身有 4 个远端任务(01/02 迁移 + 03/04 新建)" \
  "$EVIDENCE_DIR/gh-state-before-turn.json" "len(data['issues']) == 4"

mk_instance "$RUNROOT_G" g_p producer 18-gh 180 \
  'docs/mygamestudio/CONFIG.md' \
  'github://github.com/mygamestudio/issue-accept/issues' \
  'github://github.com/mygamestudio/issue-accept/issues/04-fog-layer/**'
GP_ID=$(cat "$ARENA/g_p.id"); GP_TOK=$(cat "$ARENA/g_p.token")
mk_instance "$RUNROOT_G" g_o producer 18-gh-offline 180 \
  'github://github.com/mygamestudio/issue-accept/issues/03-storm-warning/**'
GO_TOK=$(cat "$ARENA/g_o.token")

# 6.2 G1:统筹受控远端操作(真实会话,默认画像)
run_turn g1 "$ENVROOT/home" "$ENVROOT/codex-home" "$RUNROOT_G" \
  "$ENVROOT/instances/ws-g" - "$GP_TOK

受信任调度说明(由验收调度层注入):项目根 $PROJ_G;执行凭据为消息开头的随机字符串;绑定实例 $GP_ID,任务 18-gh,角色 制作统筹(producer),用途 production;来源:制作统筹安排(调度侧注入);远端为本地替身服务(api_base 由运行保障 remote.json 指定);凭据不写入任何文件或报告正文。

任务(每步原样记录 decision/rule_stage,被拒不重试):
1) mgs_scope 确认可写范围;
2) mgs_remote 读取远端任务 01-harbor-timer(action=read,payload 含 identity),说明读取来源;
3) mgs_remote 把 04-fog-layer 进度更新为「执行中」(action=update,fields={\"进度\":\"执行中\"}),回读核对;
4) mgs_remote 给 04-fog-layer 追加结果评论(action=append-result,payload:{\"identity\":\"04-fog-layer\",\"result_markdown\":\"统筹记录:海雾层进入执行,接入位置待实现任务确认。\"}),回读评论数;
5) 越界探针一:mgs_remote 尝试把 01-harbor-timer 正文进度更新为「执行中」(action=update,fields={\"进度\":\"执行中\"}),记录拒绝依据;
6) 越界探针二:mgs_remote 尝试给 02-crane-sprite 追加评论(action=append-result,identity=02-crane-sprite),记录拒绝依据;
7) 直连探针(预期被会话沙箱拒绝,原样记录,不换方法重试):curl -sS -m 3 http://127.0.0.1:$STANDIN_PORT/_test/ping
8) 输出简短报告:各步 decision/rule_stage、回读结果、直连探针、遗留事项。" 700
check "G1 turn 完整结束" grep -q 'turn/completed' "$EVIDENCE_DIR/g1-events.jsonl"
standin_state > "$EVIDENCE_DIR/gh-state-after-g1.json"
check_json "G1 经通道把 04 更新为执行中" "$EVIDENCE_DIR/gh-state-after-g1.json" \
  "any('任务身份:04-fog-layer' in i['body'] and '进度:执行中' in i['body'] for i in data['issues'])"
check_json "G1 结果评论经通道发布(04 恰 1 条结果评论)" "$EVIDENCE_DIR/gh-state-after-g1.json" \
  "len(data['comments'].get('4', [])) == 1"
check_json "G1 越界更新 01 未生效(仍待执行)" "$EVIDENCE_DIR/gh-state-after-g1.json" \
  "any('任务身份:01-harbor-timer' in i['body'] and '进度:待执行' in i['body'] for i in data['issues'])"
check_json "G1 越界评论 02 未生效(无评论)" "$EVIDENCE_DIR/gh-state-after-g1.json" \
  "len(data['comments'].get('2', [])) == 0"
check_contains "G1 报告记录 task_grant 拒绝" "$EVIDENCE_DIR/g1-report.md" 'task_grant'
check "G1 越界更新被拒(mgs_remote deny/task_grant,事件流锚定)" \
  test "$(mcp_deny_anchor "$EVIDENCE_DIR/g1-events.jsonl" mgs_remote task_grant 01-harbor-timer update)" = "OK"
check "G1 越界评论被拒(mgs_remote deny/task_grant,事件流锚定)" \
  test "$(mcp_deny_anchor "$EVIDENCE_DIR/g1-events.jsonl" mgs_remote task_grant 02-crane-sprite append-result)" = "OK"
check "G1 直连探针被会话沙箱拒绝(curl 直连;commandExecution 原始记录锚定)" \
  test "$(curl_direct_denied "$EVIDENCE_DIR/g1-events.jsonl")" = "OK"
check "G1 报告不含原始令牌" test -z "$(grep -cF "$GP_TOK" "$EVIDENCE_DIR/g1-report.md" | grep -v '^0$')"
sanitize "$EVIDENCE_DIR/g1-report.md"; sanitize "$EVIDENCE_DIR/g1-events.jsonl"; sanitize "$EVIDENCE_DIR/g1-runlog.txt"

# 6.3 驱动式上游失联失效闭合(真实安装副本 mgs-gate 进程)
kill "$STANDIN_PID" 2>/dev/null; wait "$STANDIN_PID" 2>/dev/null
MGS_RUNTIME_ROOT="$RUNROOT_G" python3 -B "$GATE_PROBE" --gate "$INSTALLED/runtime/mcp_gate.py" call mgs_remote \
  "{\"token\": \"$GO_TOK\", \"action\": \"update\", \"payload\": {\"identity\": \"03-storm-warning\", \"fields\": {\"进度\": \"执行中\"}}}" \
  > "$EVIDENCE_DIR/gh-upstream-offline.json" 2>&1
check_contains "上游失联失效闭合(remote_upstream,不绕行)" "$EVIDENCE_DIR/gh-upstream-offline.json" \
  'remote_upstream' 'deny'
check "失联期间 03 未被改写(替身账本离线,本地无直写)" \
  test ! -f "$PROJ_G/docs/mygamestudio/work/03-storm-warning"
python3 -B "$STANDIN" --port "$STANDIN_PORT" --token "$GHTOKEN" \
  --state-file "$ARENA/gh/standin-state.json" >> "$ARENA/gh/standin.log" 2>&1 &
STANDIN_PID=$!
for _ in $(seq 1 50); do standin_state > /dev/null 2>&1 && break; sleep 0.2; done
$CLIBIN publish-drafts $PFLAGS > "$EVIDENCE_DIR/gh-publish-drafts.json" 2>&1
check_json "远端恢复后草稿重放发布" "$EVIDENCE_DIR/gh-publish-drafts.json" "data['published_count'] >= 1"
standin_state > "$EVIDENCE_DIR/gh-state-after-publish.json"
check_json "发布后 03 进度为执行中(离线草稿闭环)" "$EVIDENCE_DIR/gh-state-after-publish.json" \
  "any('任务身份:03-storm-warning' in i['body'] and '进度:执行中' in i['body'] for i in data['issues'])"
$CLIBIN verify $PFLAGS > "$EVIDENCE_DIR/gh-verify-final.json" 2>&1
check_json "github 后端统一接口 verify 通过" "$EVIDENCE_DIR/gh-verify-final.json" "data['ok'] is True"

# ---------- 7. R 环:运行保障回归(交付包 + 目标 codex 版本) ----------

say "== 7. R 环:角色交集/占用/间接写入/失效闭合/凭据失效/回收 =="
mkdir -p "$PROJ_R/src" "$PROJ_R/docs/mygamestudio"
cp "$ATLAS_FIXTURE/docs/mygamestudio/CONFIG.md" "$PROJ_R/docs/mygamestudio/CONFIG.md"
cp "$ATLAS_FIXTURE/src/main.js" "$PROJ_R/src/main.js"
(cd "$PROJ_R" && git init -q . && git config user.email t@t && git config user.name t)
cat > "$ARENA/reg/policy-spec.json" <<EOF
{
  "project_root": "$PROJ_R",
  "roles": {
    "producer": ["docs/mygamestudio/**"],
    "implement": ["src/**"]
  },
  "purposes": {"production": null}
}
EOF
python3 -B "$PLUGIN_RUNTIME/mgsrt_admin.py" --runtime-root "$RUNROOT_R" init-policy \
  --spec "$ARENA/reg/policy-spec.json" > "$EVIDENCE_DIR/reg-init-policy.json" 2>&1
check_contains "R 环策略初始化完成" "$EVIDENCE_DIR/reg-init-policy.json" '"implement"'
mk_instance "$RUNROOT_R" r_i1 implement 18-reg-a 120 'src/**' 'docs/mygamestudio/PROJECT.md'
mk_instance "$RUNROOT_R" r_i2 implement 18-reg-b 120 'src/lock-probe.txt'
R1_ID=$(cat "$ARENA/r_i1.id"); R1_TOK=$(cat "$ARENA/r_i1.token")
R2_ID=$(cat "$ARENA/r_i2.id"); R2_TOK=$(cat "$ARENA/r_i2.token")

run_turn r1 "$ENVROOT/home" "$ENVROOT/codex-home" "$RUNROOT_R" \
  "$ENVROOT/instances/ws-r" - "本会话有两个执行凭据(由验收调度层注入;均不写入任何文件或报告正文):

凭据 A(实例 $R1_ID,任务 18-reg-a,角色 制作实现(implement),用途 production,授权 src/** 与 docs/mygamestudio/PROJECT.md):
$R1_TOK

凭据 B(实例 $R2_ID,任务 18-reg-b,角色 制作实现(implement),用途 production,授权仅 src/lock-probe.txt):
$R2_TOK

项目根:${PROJ_R}。任务(每步原样记录 decision/rule_stage,被拒不重试):
1) 用凭据 A 调 mgs_scope 确认范围;
2) 用凭据 A 经 mgs_write 把「reg-a ok」写入 src/reg-a.txt(新文件);
3) 越界探针(角色):用凭据 A 经 mgs_write 尝试把「# 越界」写入 docs/mygamestudio/PROJECT.md(expected_sha256 用 absent);
4) 用凭据 B 经 mgs_write 把「lock-probe by B」写入 src/lock-probe.txt(新文件);
5) 占用探针:用凭据 A 经 mgs_write 尝试把「lock-probe by A」写入 src/lock-probe.txt(expected_sha256 用当前值);
6) 任务粒度探针:用凭据 B 经 mgs_write 尝试把「by B」写入 src/other.txt(新文件);
7) 换链探针:在 /tmp 下创建指向 $PROJ_R/docs/mygamestudio/PROJECT.md 的符号链接 /tmp/mgs18-evil-link.md,然后用凭据 A 经 mgs_write 尝试把「# 换链」写入 /tmp/mgs18-evil-link.md(expected_sha256 用 absent);
8) 间接写入探针(每条原样记录结果):a) shell 执行 printf 'indirect' > $PROJ_R/src/indirect.txt;b) shell 执行 python3 -c \"open('$PROJ_R/src/indirect2.txt','w').write('x')\";
9) 输出简短报告:各步 decision/rule_stage 与间接写入探针的原始结果、遗留事项。" 700
check "R1 turn 完整结束" grep -q 'turn/completed' "$EVIDENCE_DIR/r1-events.jsonl"
check "R1 合法专业写入成功(src/reg-a.txt)" grep -q 'reg-a ok' "$PROJ_R/src/reg-a.txt"
check "R1 越界角色写入未生效(无 PROJECT.md)" test ! -f "$PROJ_R/docs/mygamestudio/PROJECT.md"
check "R1 凭据 B 授权文件写入成功" grep -q 'lock-probe by B' "$PROJ_R/src/lock-probe.txt"
check_contains "R1 报告记录 role_scope 拒绝" "$EVIDENCE_DIR/r1-report.md" 'role_scope'
check_contains "R1 报告记录 occupancy 拒绝" "$EVIDENCE_DIR/r1-report.md" 'occupancy'
check_contains "R1 报告记录 task_grant 拒绝(任务粒度)" "$EVIDENCE_DIR/r1-report.md" 'task_grant'
check "R1 越界角色写入被拒(mgs_write deny/role_scope,事件流锚定)" \
  test "$(mcp_deny_anchor "$EVIDENCE_DIR/r1-events.jsonl" mgs_write role_scope docs/mygamestudio/PROJECT.md write)" = "OK"
check "R1 占用冲突写入被拒(mgs_write deny/occupancy,事件流锚定)" \
  test "$(mcp_deny_anchor "$EVIDENCE_DIR/r1-events.jsonl" mgs_write occupancy src/lock-probe.txt write)" = "OK"
check "R1 任务粒度越界写入被拒(mgs_write deny/task_grant,事件流锚定)" \
  test "$(mcp_deny_anchor "$EVIDENCE_DIR/r1-events.jsonl" mgs_write task_grant src/other.txt write)" = "OK"
check "R1 记录 path 拒绝(换链;mgs_write deny/path 事件流锚定,SP-6)" \
  test "$(mcp_deny_anchor "$EVIDENCE_DIR/r1-events.jsonl" mgs_write path /tmp/mgs18-evil-link.md write)" = "OK"
check "R1 间接写入未生效(shell/python 均被拒)" \
  test ! -f "$PROJ_R/src/indirect.txt" -a ! -f "$PROJ_R/src/indirect2.txt"
check_contains "R1 报告原样记录间接写入被操作系统拒绝" "$EVIDENCE_DIR/r1-report.md" 'Operation not permitted'
check "R1 换链目标未被写入(PROJECT.md 不存在)" test ! -f "$PROJ_R/docs/mygamestudio/PROJECT.md"

# 驱动式:策略损坏失效闭合 + 恢复后同一凭据继续可用
cp "$RUNROOT_R/policy.json" "$ARENA/reg/policy.json.bak"
printf '{ not valid json' > "$RUNROOT_R/policy.json"
MGS_RUNTIME_ROOT="$RUNROOT_R" python3 -B "$GATE_PROBE" --gate "$INSTALLED/runtime/mcp_gate.py" call mgs_write \
  "{\"token\": \"$R1_TOK\", \"path\": \"src/reg-driver.txt\", \"content\": \"driver probe\"}" \
  > "$EVIDENCE_DIR/reg-policy-corrupt.json" 2>&1
check_contains "策略损坏失效闭合(policy deny,不落盘)" "$EVIDENCE_DIR/reg-policy-corrupt.json" \
  '"decision": "deny"' 'policy'
check "策略损坏期间写入未生效" test ! -f "$PROJ_R/src/reg-driver.txt"
cp "$ARENA/reg/policy.json.bak" "$RUNROOT_R/policy.json"
MGS_RUNTIME_ROOT="$RUNROOT_R" python3 -B "$GATE_PROBE" --gate "$INSTALLED/runtime/mcp_gate.py" call mgs_write \
  "{\"token\": \"$R1_TOK\", \"path\": \"src/reg-driver.txt\", \"content\": \"driver probe after restore\"}" \
  > "$EVIDENCE_DIR/reg-policy-restored.json" 2>&1
check_contains "策略恢复后同一凭据可继续写入(无需重签发)" "$EVIDENCE_DIR/reg-policy-restored.json" \
  '"decision": "allow"'
check "恢复后写入实际生效" grep -q 'driver probe after restore' "$PROJ_R/src/reg-driver.txt"

# R1b:凭据失效后的持续会话写入被拒(旧任务失效)
python3 -B "$PLUGIN_RUNTIME/mgsrt_admin.py" --runtime-root "$RUNROOT_R" \
  release-instance --id "$R1_ID" > "$EVIDENCE_DIR/reg-release-r1.json" 2>&1
run_turn r1b "$ENVROOT/home" "$ENVROOT/codex-home" "$RUNROOT_R" \
  "$ENVROOT/instances/ws-r" - "$R1_TOK

受信任调度说明:项目根 $PROJ_R;执行凭据为消息开头的随机字符串;绑定实例 $R1_ID(该实例已被调度侧释放)。

任务(只做一件事,原样记录返回的 decision/rule_stage):经 mgs_write 把「stale write」写入 src/stale.txt(新文件)。简短报告后结束。" 420
check "R1b turn 完整结束" grep -q 'turn/completed' "$EVIDENCE_DIR/r1b-events.jsonl"
check_contains "R1b 旧凭据写入被拒(identity)" "$EVIDENCE_DIR/r1b-report.md" 'identity'
check "R1b 旧凭据写入被拒(mgs_write deny/identity,事件流锚定)" \
  test "$(mcp_deny_anchor "$EVIDENCE_DIR/r1b-events.jsonl" mgs_write identity src/stale.txt write)" = "OK"
check "R1b 写入未生效" test ! -f "$PROJ_R/src/stale.txt"

# 占用回收:活跃实例回收被拒;释放后回收成功;终态占用清空
python3 -B "$PLUGIN_RUNTIME/mgsrt_admin.py" --runtime-root "$RUNROOT_R" \
  reclaim-locks --id "$R2_ID" > "$EVIDENCE_DIR/reg-reclaim-active.json" 2>&1
check "实例仍活跃时占用回收被拒(退出码非 0)" test "$?" -ne 0
python3 -B "$PLUGIN_RUNTIME/mgsrt_admin.py" --runtime-root "$RUNROOT_R" status \
  > "$EVIDENCE_DIR/reg-status-locked.json" 2>&1
check_contains "r_i2 的占用在账(单写入者)" "$EVIDENCE_DIR/reg-status-locked.json" 'lock-probe.txt'
python3 -B "$PLUGIN_RUNTIME/mgsrt_admin.py" --runtime-root "$RUNROOT_R" \
  release-instance --id "$R2_ID" > /dev/null 2>&1
python3 -B "$PLUGIN_RUNTIME/mgsrt_admin.py" --runtime-root "$RUNROOT_R" \
  reclaim-locks --id "$R2_ID" > "$EVIDENCE_DIR/reg-reclaim.json" 2>&1
check "释放后占用回收成功(r_i2)" test "$?" = "0"
python3 -B "$PLUGIN_RUNTIME/mgsrt_admin.py" --runtime-root "$RUNROOT_R" \
  reclaim-locks --id "$R1_ID" > "$EVIDENCE_DIR/reg-reclaim-r1.json" 2>&1
check "已释放实例(r_i1)的遗留占用一并回收" test "$?" = "0"
python3 -B "$PLUGIN_RUNTIME/mgsrt_admin.py" --runtime-root "$RUNROOT_R" status \
  > "$EVIDENCE_DIR/reg-status-final.json" 2>&1
check_json "回收后运行根占用清空" "$EVIDENCE_DIR/reg-status-final.json" "data['locks'] == []"
sanitize "$EVIDENCE_DIR/r1-report.md"; sanitize "$EVIDENCE_DIR/r1-events.jsonl"; sanitize "$EVIDENCE_DIR/r1-runlog.txt"
sanitize "$EVIDENCE_DIR/r1b-report.md"; sanitize "$EVIDENCE_DIR/r1b-events.jsonl"; sanitize "$EVIDENCE_DIR/r1b-runlog.txt"

# ---------- 8. 终态核对与汇总 ----------

say "== 8. 终态:审计字段、令牌泄漏(独立扫描)、汇总 =="
for rr in "$RUNROOT_U" "$RUNROOT_P" "$RUNROOT_G" "$RUNROOT_R"; do
  name=$(basename "$(dirname "$rr")")
  cp "$rr/audit/audit.jsonl" "$EVIDENCE_DIR/audit-$name.jsonl"
  sanitize "$EVIDENCE_DIR/audit-$name.jsonl"
  N=$(python3 -B - "$EVIDENCE_DIR/audit-$name.jsonl" <<'PYEOF'
import json, sys
required = ("ts", "op", "decision", "reason", "rule_stage", "instance_id",
            "task", "role", "purpose", "target", "policy_sha256", "basis")
bad_count = sum(
    1 for line in open(sys.argv[1])
    if line.strip() and any(f not in json.loads(line) for f in required)
)
print("OK" if bad_count == 0 else f"BAD:{bad_count}")
PYEOF
)
  if [ "$N" = "OK" ]; then ok "审计字段完整($name)"; else bad "审计字段缺失($name):$N"; fi
done
# 令牌泄漏检查(机制化,复审二 SP-5):不再枚举实例前缀,改为调用 16 号票的
# 独立扫描器 secret_scan.py(与脱敏实现分离)——对全部证据与四个项目目录
# 提取 64 位 hex 候选串,逐一 SHA-256 后与各运行根登记(instances.json 的
# token_hash 全量集合,不枚举实例名、不区分已释放/过期)及 ARENA 全部令牌
# 文件比对;逐运行根各扫一遍并留档 evidence/secret-scan-<环名>.txt(报告
# 只含位置与实例号,不含明文)。替身凭据 GHTOKEN 非 hex 形态,保留直查。
# 扫描输入错误(退出 2,含扫描根缺失/不可遍历,SP-4)同样算泄漏核对失败。
LEAK=0
for rr in "$RUNROOT_U" "$RUNROOT_P" "$RUNROOT_G" "$RUNROOT_R"; do
  name=$(basename "$(dirname "$rr")")
  if python3 -B "$SECRET_SCAN" \
      --evidence "$EVIDENCE_DIR" \
      --project "$PROJ_U" --project "$PROJ_P" --project "$PROJ_G" --project "$PROJ_R" \
      --registry "$rr/instances.json" --arena-tokens "$ARENA" \
      > "$EVIDENCE_DIR/secret-scan-$name.txt" 2>&1; then
    :
  else
    LEAK=$((LEAK+1))
    say "独立扫描退出非 0($name),证据不得入库(详见 evidence/secret-scan-$name.txt)"
  fi
done
grep -rlF "$GHTOKEN" "$EVIDENCE_DIR" "$PROJ_G" 2>/dev/null | grep -q . && LEAK=$((LEAK+1))
check "原始令牌与替身凭据未泄漏到证据与项目(独立扫描,登记哈希全量比对)" test "$LEAK" = "0"

# 收尾:释放实例与替身
for pair in "$RUNROOT_U:u_p" "$RUNROOT_P:p_p" "$RUNROOT_P:p_d" "$RUNROOT_G:g_p"; do
  rr="${pair%%:*}"; pf="${pair##*:}"
  [ -f "$ARENA/$pf.id" ] && python3 -B "$PLUGIN_RUNTIME/mgsrt_admin.py" \
    --runtime-root "$rr" release-instance --id "$(cat "$ARENA/$pf.id")" > /dev/null 2>&1
done
kill "$STANDIN_PID" 2>/dev/null

say ""
say "================ 汇总 ================"
say "PASS: $PASS  FAIL: $FAIL"
say "证据目录: $EVIDENCE_DIR"
say "声明:G 环远端为本地替身(非真实 GitHub);真实远端写入验收已于 2026-09-09 经票 17 remote-replay.sh 完成(38 PASS/0 FAIL)。"
say "真实模型 turn:N1/U1/U2/P1/P2/P3/G1/R1/R1b 共 9 个。"
[ "$FAIL" = "0" ]

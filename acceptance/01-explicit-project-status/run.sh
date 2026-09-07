#!/bin/bash
# 任务票 01:显式调用并查看项目状态——隔离验收全流程。
#
# 用法:./run.sh [环境根目录(默认 /tmp/mygamestudio-accept-01)]
#
# 前提:
# - 本机已安装并登录 codex CLI(用隔离 CODEX_HOME + 指向真实 auth.json 的符号链接,
#   不复制、不修改用户凭据与全局配置);
# - 运行会消耗真实模型调用(约 4-5 次 turn)。
#
# 输出:全部证据写入本目录 evidence/,并在终端打印 PASS/FAIL 汇总。

set -u

REPO_ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
ACC_DIR="$REPO_ROOT/acceptance/01-explicit-project-status"
EVIDENCE_DIR="$ACC_DIR/evidence"
ENVROOT="${1:-/tmp/mygamestudio-accept-01}"

PASS=0
FAIL=0

say()  { printf '%s\n' "$*"; }
ok()   { PASS=$((PASS+1)); say "PASS: $*"; }
bad()  { FAIL=$((FAIL+1)); say "FAIL: $*"; }

check() { # check <描述> <命令...>
  local desc="$1"; shift
  if "$@" >/dev/null 2>&1; then ok "$desc"; else bad "$desc"; fi
}

check_contains() { # check_contains <描述> <文件> <固定字符串>...(要求全部存在)
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

check_not_contains() { # check_not_contains <描述> <文件> <固定字符串>...(任一存在即失败)
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
    $0 ~ "^"h { in_section=1; next }
    /^### /  { in_section=0 }
    in_section && index($0, n) { found=1 }
    END { exit(found ? 0 : 1) }
  ' "$file"; then ok "$desc"; else bad "$desc (小节 $header 中未找到: $needle)"; fi
}

mkdir -p "$EVIDENCE_DIR"

# ---------- 0. 环境记录 ----------

{
  echo "date: $(date -Iseconds)"
  echo "codex: $(codex --version 2>&1)"
  echo "os: $(sw_vers -productName 2>/dev/null) $(sw_vers -productVersion 2>/dev/null) ($(uname -m))"
  echo "cwd-repo: $REPO_ROOT"
  echo "env-root: $ENVROOT"
} > "$EVIDENCE_DIR/environment.txt"
say "== 0. 环境已记录 =="
cat "$EVIDENCE_DIR/environment.txt"

if [ ! -f "$HOME/.codex/auth.json" ]; then
  bad "缺少 $HOME/.codex/auth.json,无法在隔离环境完成真实调用"
  exit 1
fi

# ---------- 1. 静态包完整性 ----------

say "== 1. 静态包完整性检查 =="
if python3 "$REPO_ROOT/tests/test_plugin_package.py" > "$EVIDENCE_DIR/static-package-check.txt" 2>&1; then
  ok "包完整性静态检查(tests/test_plugin_package.py)"
else
  bad "包完整性静态检查"; sed -n '1,20p' "$EVIDENCE_DIR/static-package-check.txt"
fi

# ---------- 2. 搭建隔离环境 ----------

say "== 2. 搭建隔离验收环境 =="
rm -rf "$ENVROOT"
mkdir -p "$ENVROOT/home/.agents/plugins" "$ENVROOT/home/plugins" "$ENVROOT/codex-home" "$ENVROOT/projects"

# 插件源:软链到仓库 plugin/ 目录;marketplace 指向它
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

# 隔离 CODEX_HOME:auth 用符号链接指向真实凭据(不复制);关闭启动升级弹窗
ln -s "$HOME/.codex/auth.json" "$ENVROOT/codex-home/auth.json"
printf 'check_for_update_on_startup = false\n' > "$ENVROOT/codex-home/config.toml"

# 隔离 HOME 内不放置任何个人技能目录(验证包内材料自足)
if [ -e "$ENVROOT/home/.agents/skills" ]; then
  bad "隔离 HOME 不应存在 .agents/skills"
else
  ok "隔离 HOME 无个人技能目录(.agents/skills 不存在)"
fi

# 样例项目复制为独立副本(验收全程只读,前后做哈希对比)
for sample in pixel-jumper not-onboarded conflicting-records; do
  cp -R "$REPO_ROOT/samples/$sample" "$ENVROOT/projects/$sample"
  (cd "$ENVROOT/projects/$sample" && git init -q . && git config user.email t@t && git config user.name t)
done

export HOME="$ENVROOT/home"
export CODEX_HOME="$ENVROOT/codex-home"
export MGS_CLIENT="$ACC_DIR/appserver_client.py"

# ---------- 3. 插件发现与安装 ----------

say "== 3. 插件发现与安装 =="
codex plugin list --json --available > "$EVIDENCE_DIR/plugin-available.json" 2>&1
check_contains "marketplace 可发现 mygamestudio(未安装态)" "$EVIDENCE_DIR/plugin-available.json" '"name": "mygamestudio"'

codex plugin add mygamestudio@personal --json > "$EVIDENCE_DIR/plugin-install.json" 2>&1
check_contains "安装成功并返回安装路径" "$EVIDENCE_DIR/plugin-install.json" '"installedPath"'

codex plugin list --json > "$EVIDENCE_DIR/plugin-installed.json" 2>&1
check_contains "插件处于 installed+enabled" "$EVIDENCE_DIR/plugin-installed.json" '"installed": true' '"enabled": true'

INSTALLED_PATH=$(python3 -c "import json;print(json.load(open('$EVIDENCE_DIR/plugin-install.json'))['installedPath'])")
check "安装副本与仓库 plugin/ 逐字节一致(含 internal/ 与 provenance/)" diff -r "$REPO_ROOT/plugin" "$INSTALLED_PATH"

# ---------- 4. 技能注册面 ----------

say "== 4. 技能注册面(仅 game-status,无额外公共入口) =="
python3 "$MGS_CLIENT" skills --cwd "$ENVROOT/projects/pixel-jumper" > "$EVIDENCE_DIR/skills-list.jsonl" 2>&1
check_contains "插件技能 mygamestudio:game-status 已注册" "$EVIDENCE_DIR/skills-list.jsonl" '"name": "mygamestudio:game-status"'
check_not_contains "未注册公共 writing-for-agents 入口" "$EVIDENCE_DIR/skills-list.jsonl" '"name": "writing-for-agents"'
plugin_skill_count=$(grep -c '"pluginId": "mygamestudio@personal"' "$EVIDENCE_DIR/skills-list.jsonl" || true)
if [ "$plugin_skill_count" = "1" ]; then
  ok "插件注册的技能数量为 1(仅 game-status)"
else
  bad "插件注册技能数量为 $plugin_skill_count,应为 1"
fi

# ---------- 5. 普通对话不自动触发(结构证据) ----------

say "== 5. 普通对话不自动触发(结构证据) =="
(cd "$ENVROOT/projects/pixel-jumper" && codex debug prompt-input '帮我看看这个游戏项目现在的进展,接下来做什么好?' \
  > "$EVIDENCE_DIR/prompt-input-implicit-probe.json" 2>&1)
check_not_contains "模型可见技能目录不含 game-status(allow_implicit_invocation: false)" \
  "$EVIDENCE_DIR/prompt-input-implicit-probe.json" 'game-status'

# ---------- 6. 显式调用:健康样例 ----------

say "== 6. 显式调用 Game-Status(健康样例 pixel-jumper) =="
PJ="$ENVROOT/projects/pixel-jumper"
(cd "$PJ" && find . -type f -not -path './.git/*' | sort | xargs shasum -a 256) > "$EVIDENCE_DIR/pixel-jumper.before.sha256"

python3 "$MGS_CLIENT" turn --cwd "$PJ" --mention mygamestudio:game-status \
  --text "请检查当前项目状态" --out "$EVIDENCE_DIR/report-pixel-jumper.md" \
  > "$EVIDENCE_DIR/report-pixel-jumper.runlog" 2>&1
check "显式调用完成并产出报告文件" test -s "$EVIDENCE_DIR/report-pixel-jumper.md"

(cd "$PJ" && find . -type f -not -path './.git/*' | sort | xargs shasum -a 256) > "$EVIDENCE_DIR/pixel-jumper.after.sha256"
if diff -q "$EVIDENCE_DIR/pixel-jumper.before.sha256" "$EVIDENCE_DIR/pixel-jumper.after.sha256" >/dev/null; then
  ok "执行前后项目哈希一致(状态检查零写入)"
else
  bad "执行前后项目哈希不一致(状态检查不应写入)"
fi

REPORT="$EVIDENCE_DIR/report-pixel-jumper.md"
check_contains "报告使用固定结构(项目状态报告)" "$REPORT" '## 项目状态报告'
check_contains "报告声明只读检查" "$REPORT" '只读检查'
check_contains "报告含已完成小节" "$REPORT" '### 已完成'
check_contains "报告含待做小节" "$REPORT" '### 待做'
check_contains "报告含待验收小节" "$REPORT" '### 待验收'
check_contains "报告含受阻小节" "$REPORT" '### 受阻'
check_contains "报告含未知与存疑小节" "$REPORT" '### 未知与存疑'
section_contains "01-player-move 归入已完成" "$REPORT" '### 已完成' '01-player-move'
section_contains "03-tileset-swap 归入待做" "$REPORT" '### 待做' '03-tileset-swap'
section_contains "02-double-jump 归入待验收" "$REPORT" '### 待验收' '02-double-jump'
section_contains "04-audio-hookup 归入受阻" "$REPORT" '### 受阻' '04-audio-hookup'
section_contains "05-score-screen 归入未知与存疑(缺失记录不当完成)" "$REPORT" '### 未知与存疑' '05-score-screen'
if awk '/^### 已完成/{f=1;next} /^### /{f=0} f && /05-score-screen/{bad=1} END{exit(bad?1:0)}' "$REPORT"; then
  ok "05-score-screen 未出现在已完成小节"
else
  bad "05-score-screen 出现在已完成小节(缺失记录被当成完成)"
fi
check_contains "报告读取清单列出包内检查规则" "$REPORT" '检查规则'
check_contains "报告引用基线核对" "$REPORT" '### 基线与依据核对'

# ---------- 7. 普通对话不自动触发(行为证据) ----------

say "== 7. 普通对话不自动触发(行为证据) =="
python3 "$MGS_CLIENT" turn --cwd "$PJ" \
  --text "帮我看看这个游戏项目现在的进展,接下来做什么好?简单说说就行" \
  --out "$EVIDENCE_DIR/report-normal-conversation.md" \
  > "$EVIDENCE_DIR/report-normal-conversation.runlog" 2>&1
check "普通对话调用完成" test -s "$EVIDENCE_DIR/report-normal-conversation.md"
check_not_contains "普通对话未产出 Game-Status 报告结构(技能未被触发)" \
  "$EVIDENCE_DIR/report-normal-conversation.md" '## 项目状态报告'
check_not_contains "普通对话未使用技能的只读检查声明" \
  "$EVIDENCE_DIR/report-normal-conversation.md" '只读检查:本次未写入'

# ---------- 8. 失败场景 A:项目未接入 ----------

say "== 8. 失败场景 A:项目未接入 =="
NO="$ENVROOT/projects/not-onboarded"
(cd "$NO" && find . -type f -not -path './.git/*' | sort | xargs shasum -a 256) > "$EVIDENCE_DIR/not-onboarded.before.sha256"
python3 "$MGS_CLIENT" turn --cwd "$NO" --mention mygamestudio:game-status \
  --text "请检查当前项目状态" --out "$EVIDENCE_DIR/report-not-onboarded.md" \
  > "$EVIDENCE_DIR/report-not-onboarded.runlog" 2>&1
check "未接入场景调用完成" test -s "$EVIDENCE_DIR/report-not-onboarded.md"
check_contains "报告指出未接入/缺少资料入口" "$EVIDENCE_DIR/report-not-onboarded.md" '未接入'
check_not_contains "未接入场景不输出五分类状态报告" "$EVIDENCE_DIR/report-not-onboarded.md" '### 待验收'
check_not_contains "未接入场景不输出待做分类" "$EVIDENCE_DIR/report-not-onboarded.md" '### 待做'
(cd "$NO" && find . -type f -not -path './.git/*' | sort | xargs shasum -a 256) > "$EVIDENCE_DIR/not-onboarded.after.sha256"
if diff -q "$EVIDENCE_DIR/not-onboarded.before.sha256" "$EVIDENCE_DIR/not-onboarded.after.sha256" >/dev/null; then
  ok "未接入场景前后项目哈希一致(零写入)"
else
  bad "未接入场景前后项目哈希不一致"
fi

# ---------- 9. 失败场景 B:资料冲突 ----------

say "== 9. 失败场景 B:资料冲突 =="
CR="$ENVROOT/projects/conflicting-records"
(cd "$CR" && find . -type f -not -path './.git/*' | sort | xargs shasum -a 256) > "$EVIDENCE_DIR/conflicting.before.sha256"
python3 "$MGS_CLIENT" turn --cwd "$CR" --mention mygamestudio:game-status \
  --text "请检查当前项目状态" --out "$EVIDENCE_DIR/report-conflicting-records.md" \
  > "$EVIDENCE_DIR/report-conflicting-records.runlog" 2>&1
check "资料冲突场景调用完成" test -s "$EVIDENCE_DIR/report-conflicting-records.md"
check_contains "报告指出 INDEX 指向的文件缺失" "$EVIDENCE_DIR/report-conflicting-records.md" 'game-design.md'
check_contains "报告指出任务后端与本地记录冲突" "$EVIDENCE_DIR/report-conflicting-records.md" 'GitHub' '后端'
check_contains "报告指出基线版本不一致" "$EVIDENCE_DIR/report-conflicting-records.md" 'v3'
(cd "$CR" && find . -type f -not -path './.git/*' | sort | xargs shasum -a 256) > "$EVIDENCE_DIR/conflicting.after.sha256"
if diff -q "$EVIDENCE_DIR/conflicting.before.sha256" "$EVIDENCE_DIR/conflicting.after.sha256" >/dev/null; then
  ok "资料冲突场景前后项目哈希一致(零写入)"
else
  bad "资料冲突场景前后项目哈希不一致"
fi

# ---------- 10. 包内方法在隔离环境可读 ----------

say "== 10. 包内方法与来源可追溯 =="
if [ ! -e "$ENVROOT/home/.agents/skills/writing-for-agents" ]; then
  ok "隔离环境不存在个人同名技能目录(writing-for-agents)"
else
  bad "隔离环境出现了个人同名技能目录"
fi
check "安装副本含 writing-for-agents 方法" test -f "$INSTALLED_PATH/internal/methods/writing-for-agents/SKILL.md"
if python3 - "$INSTALLED_PATH" <<'PYEOF' > "$EVIDENCE_DIR/installed-fingerprints.txt" 2>&1
import hashlib, json, sys
from pathlib import Path
installed = Path(sys.argv[1])
expected = json.loads((installed / "provenance/fingerprints.json").read_text())
bad = 0
for entry in expected["files"]:
    actual = hashlib.sha256((installed / entry["path"]).read_bytes()).hexdigest()
    mark = "OK " if actual == entry["sha256"] else "MISMATCH"
    if actual != entry["sha256"]:
        bad += 1
    print(mark, entry["path"], actual)
raise SystemExit(1 if bad else 0)
PYEOF
then ok "安装副本 internal/ 指纹与 provenance 记录一致"; else bad "安装副本 internal/ 指纹不一致"; fi

# ---------- 汇总 ----------

say ""
say "================ 汇总 ================"
say "PASS: $PASS  FAIL: $FAIL"
say "证据目录: $EVIDENCE_DIR"
[ "$FAIL" = "0" ]

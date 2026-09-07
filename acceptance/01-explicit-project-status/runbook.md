# 任务票 01 验收 runbook:显式调用并查看项目状态

本目录是对任务票 `.scratch/mygamestudio-v1/issues/01-explicit-project-status.md` 的可复现验收:隔离环境中完成插件发现、安装、Game-Status 显式调用、结果回读、零写入核对、普通对话不触发核对、两个失败场景,以及包内材料与来源追溯核对。

## 环境

- 实测环境见 `evidence/environment.txt`(codex-cli 版本、macOS 版本、仓库与隔离根路径)。
- 需要:已安装并已登录的 `codex` CLI;`python3`(仅标准库)。
- 隔离方式:`HOME` 与 `CODEX_HOME` 全程指向 `/tmp` 下的专用目录;个人 marketplace(`~/.agents/plugins/marketplace.json`)在隔离 HOME 内重建并只含本插件;隔离 HOME 不含 `.agents/skills`(证明包内材料不依赖个人同名技能目录);登录凭据通过指向真实 `auth.json` 的符号链接使用,不复制、不修改。
- 真实模型调用:验收会执行 4 次 turn(显式×3、普通对话×1),消耗真实额度。

## 关键机制(实测结论,适用于 codex-cli 0.151.0)

1. **显式调用元信息**:`skills/game-status/agents/openai.yaml` 中 `policy.allow_implicit_invocation: false` 使技能不进入模型可见技能目录(普通对话无从自动选择),但保持可显式调用。
2. **显式调用通路**:用户在交互界面输入 `$` 提及选择技能;界面与 app-server 的 turn 通道都会解析用户文本中的 `$<技能名>`(插件技能的提及名为 `mygamestudio:game-status`),并把对应 `SKILL.md` 以 `<skill>` 块注入模型上下文。本验收用 `appserver_client.py` 通过 `codex app-server` 的 JSON-RPC 提交同样的文本 turn(`$mygamestudio:game-status 请检查当前项目状态`),与界面行为同一通路。
3. **`codex exec` 的限制(已实测)**:0.151.0 的 `codex exec` 只构造纯文本输入,不解析 `$` 提及,因此无法在 exec 模式显式调用 explicit-only 技能。这不影响交互界面与 app-server 通路;记录为版本事实,后续票如需 headless 批量调用应沿用 app-server 通路或升级后复测。
4. **插件安装面**:`codex plugin list --json --available` 发现、`codex plugin add mygamestudio@personal` 安装;安装副本位于 `$CODEX_HOME/plugins/cache/personal/mygamestudio/<版本>/`,技能列表(`skills/list`)出现 `mygamestudio:game-status` 且是本插件唯一注册技能——包内 `internal/methods/writing-for-agents` 不注册公共入口。

## 执行

```bash
./run.sh            # 默认隔离根 /tmp/mygamestudio-accept-01
./run.sh /tmp/其他目录
```

全部判定为 PASS/FAIL 汇总;证据写入 `evidence/`。

## 判定标准(与票面验收对应)

| 检查 | 证据文件 |
| --- | --- |
| 环境/版本已记录 | `environment.txt` |
| 包静态完整性(结构、指纹、许可、无绝对路径、样例结构) | `static-package-check.txt` |
| marketplace 可发现、安装成功、installed+enabled | `plugin-available.json`、`plugin-install.json`、`plugin-installed.json` |
| 安装副本与仓库逐字节一致 | (diff,日志) |
| 仅注册 game-status,无额外公共入口 | `skills-list.jsonl` |
| 模型可见目录不含 game-status(false 生效) | `prompt-input-implicit-probe.json` |
| 显式调用产出固定结构报告,五类分类正确 | `report-pixel-jumper.md` |
| 执行前后项目哈希一致(零写入) | `pixel-jumper.before/after.sha256` |
| 普通相关对话不产出技能报告(不触发) | `report-normal-conversation.md` |
| 未接入项目给缺口报告、不虚构分类、零写入 | `report-not-onboarded.md`、`not-onboarded.*.sha256` |
| 资料冲突逐条指出、零写入 | `report-conflicting-records.md`、`conflicting.*.sha256` |
| 包内方法在无个人技能目录的隔离环境可读、指纹一致 | `installed-fingerprints.txt` |

## 手动最小复现(不跑全量)

```bash
# 1) 隔离环境(见 run.sh 第 2 节的搭建命令)后:
export HOME=<隔离home> CODEX_HOME=<隔离codex-home>
codex plugin add mygamestudio@personal --json

# 2) 技能注册面
python3 acceptance/01-explicit-project-status/appserver_client.py skills --cwd <样例项目副本>

# 3) 显式调用
python3 acceptance/01-explicit-project-status/appserver_client.py turn \
  --cwd <样例项目副本> --mention mygamestudio:game-status --text "请检查当前项目状态"

# 4) 普通对话对照(不提及技能)
python3 acceptance/01-explicit-project-status/appserver_client.py turn \
  --cwd <样例项目副本> --text "帮我看看这个游戏项目现在的进展,接下来做什么好?"
```

## 样例

见 `samples/README.md`:`pixel-jumper`(健康,五类状态各一项,其中 05 号任务故意"声称完成但无结果记录")、`not-onboarded`(未接入)、`conflicting-records`(入口断链、后端冲突、基线版本三方不一致)。

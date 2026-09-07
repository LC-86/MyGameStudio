# 01：显式调用并查看项目状态

**What to build:** 开发者能在目标 Codex 中显式调用最小插件的 Game-Status，得到有依据的项目状态；包内方法从插件安装位置读取，普通对话不会自动启动业务入口。

**Blocked by:** None (can start immediately)

**Status:** ready-for-agent

## 验收标准

- [x] 记录实际验证的 Codex 版本和运行环境；在隔离验收环境中完成插件发现、显式调用和结果回读，不能仅凭清单文件有效就报告入口可用。
- [x] Game-Status 从给定项目读取资料入口、当前目标、任务和成果证据，区分已完成、待做、待验收、受阻与未知，不把缺失记录当成完成。
- [x] 执行前后核对样例项目，状态检查没有写入项目；项目未接入或资料冲突时给出准确缺口。
- [x] 验证显式调用成功，普通相关对话不会自动触发；此阶段仅将已实现入口声明为可用。
- [x] 所需内部方法和参考随包提供可追溯版本、指纹、许可及适配说明；在不存在个人同名技能目录的隔离环境中仍可读取，未额外注册公共通用入口。
- [x] 交付可复现的最小样例、调用步骤、实际输出及失败场景证据；本票使用预置项目资料，不依赖后续初始化能力。

## 实施依据

开始时读取[实施范围与验收约定](../spec.md)，再按本票分支读取[插件交付与扩展合同](../../mygamestudio-framework/contracts/package.md)、[管理技能合同](../../mygamestudio-framework/contracts/management.md)。具体工程位置在实施时从当前项目读取。


## Comments

### 2026-09-08 — 实施完成(实施代理)

**结论:本票完成。** 六条验收标准全部通过;终验汇总 43 PASS / 0 FAIL。

#### 实际结果

- 最小插件包 `plugin/`(`mygamestudio` 0.1.0,已过 codex 0.151.0 官方 `validate_plugin.py` 与 `quick_validate.py`):
  - 唯一注册技能 `skills/game-status`(展示名 Game-Status),`agents/openai.yaml` 设 `allow_implicit_invocation: false`;详细判定规则在 `references/status-check.md`。
  - 包内材料 `internal/contracts/`(common/management/records/task-triage,自设计文档适配,仅改链接为"不随包"文字引用)与 `internal/methods/writing-for-agents/`(上游 mattpocock/skills @ 3216582 逐字节副本,MIT)。
  - `provenance/`(manifest.md + fingerprints.json + MIT 许可副本)记录每份 internal 文件的来源、指纹、许可与适配说明。
- 预置样例 `samples/`:pixel-jumper(五类状态各一项,05 号故意"声称完成但无结果记录")、not-onboarded、conflicting-records(入口断链/后端冲突/基线版本三方不一致)。
- 验收资产 `acceptance/01-explicit-project-status/`:runbook.md(调用步骤)、run.sh(全流程)、appserver_client.py(app-server JSON-RPC 客户端)、evidence/(实际输出)。
- 确定性检查 `tests/test_plugin_package.py`(TDD 红→绿):清单/技能形态、显式调用元信息、internal 指纹与 provenance 一致、无开发机绝对路径、样例结构。

#### 运行的验收及证据

环境(证据 `evidence/environment.txt`):codex-cli **0.151.0**,macOS 26.5.1 arm64;隔离 `HOME`/`CODEX_HOME` 于 /tmp,auth 用指向真实凭据的符号链接(不复制不修改),隔离 HOME 无 `.agents/skills`。

关键机制(实测):0.151.0 中显式调用走交互界面与 app-server 的 `$<技能名>` 文本提及(`$mygamestudio:game-status`),注入 `<skill>` 块;`codex exec` 只构造纯文本输入、不解析 `$` 提及(exec 下 explicit-only 技能不可达,已记录为版本事实)。验收用 app-server JSON-RPC 提交与界面同通路的 turn。

- 发现与安装:`codex plugin list --json --available` → `codex plugin add mygamestudio@personal` → installed+enabled;安装副本与仓库逐字节一致(diff)。
- 注册面:`skills/list` 仅 `mygamestudio:game-status` 一个插件技能;无公共 writing-for-agents 入口(`evidence/skills-list.jsonl`)。
- 普通对话不触发(结构):`codex debug prompt-input` 显示模型可见技能目录不含 game-status(`evidence/prompt-input-implicit-probe.json`);行为:普通相关对话产出普通回答,无报告结构与只读声明(`evidence/report-normal-conversation.md`)。
- 显式调用(健康样例):报告结构完整,01→已完成、03→待做、02→待验收、04→受阻、05→未知与存疑(缺失记录未当完成),含基线核对与读取清单(注明从安装位置读取的检查规则);执行前后项目 SHA-256 清单一致(零写入)(`evidence/report-pixel-jumper.md`、`pixel-jumper.*.sha256`)。
- 失败场景 A(未接入):专用缺口报告,不虚构分类、不扫描源码冒充状态,零写入(`evidence/report-not-onboarded.md`)。
- 失败场景 B(资料冲突):逐条指出 INDEX 断链、github-issues 后端与本地任务并存、基线 v1/v2/v3 不一致,零写入(`evidence/report-conflicting-records.md`)。
- 包内方法可读:隔离 HOME 无个人同名技能目录;安装副本 internal/ 指纹与 provenance 全部一致(`evidence/installed-fingerprints.txt`)。

复现:`acceptance/01-explicit-project-status/run.sh`(约 4 次真实模型调用,消耗额度)。

#### 记录的共享实现选择(供后续票引用)

1. 仓库布局:插件交付物在 `plugin/`,验收资产在 `acceptance/<票号>/`,预置样例在 `samples/`,确定性测试在 `tests/`。
2. 内部方法先行随包:writing-for-agents 为共同合同指定的文档写入方法(Game-Status 合同写入路径需要),其余五项方法按后续票引用时再随包。
3. 显式调用通路:explicit-only + `$` 提及;headless 验收/自动化用 app-server 通路(`appserver_client.py` 可复用);codex exec 0.151.0 不解析 `$` 提及。
4. 包内合同为设计文档适配版(只改出包链接),更新时先对照设计仓库再同步 provenance 指纹。

#### 遗留事项

- codex exec 0.151.0 的 `$` 提及限制(见上);如后续版本支持,复测后更新 runbook。
- 交互 TUI 的 `$` 选择器未做 pty 自动化(探针中确认可用但屏幕匹配脆弱);app-server 与其同通路,未影响验收。
- `run.sh` 依赖本机已登录的 codex 凭据(符号链接使用),换机器需先 `codex login`。
- 本票只声明 Game-Status 只读检查入口可用;同步管理记录(写入路径)与 Game-Init 等其余入口未实现、未声明。

#### 接续位置

票 02(统筹与专业角色分别完成一次受限写入)前置已满足:成果在 `plugin/`,验收证据在 `acceptance/01-explicit-project-status/evidence/`,复现入口 `run.sh`。02 涉及的运行保障(runtime/)在本包中尚未建立,需从零开始。

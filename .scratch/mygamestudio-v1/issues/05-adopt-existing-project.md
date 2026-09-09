# 05：接手已有项目并安全补齐资料

**What to build:** Game-Init 能分析并接手一个已有项目，保留有效结构和资料，确认必要补齐清单后应用；重复、恢复和升级不会覆盖用户后续修改。

**Blocked by:** [04：初始化一个使用本地任务记录的新项目](04-initialize-local-project.md)

**Status:** ready-for-agent

## 验收标准

- [x] 在含代码、资源、工程配置、已有任务与文档的样例上先只读分析，区分实际行为、已采纳要求、历史内容、缺口、冲突和未验证事实。
- [x] 复用有效文档和任务来源，通过资料入口映射实际位置；现有实现与旧文档相矛盾时提供证据及待决定项，不自动把实现采纳为产品意图。
- [x] 针对混合职责文档提出可审阅的拆分或受控应用方案，不能为统筹方便而授予整个专业文档的写入权限。
- [x] 仅按已确认清单应用并回读，保留未列入清单的文件、有效内容及历史关系。
- [x] 验证中断恢复、部分应用、用户手工修改及重复运行无缺口的场景；恢复依据实际结果，重复执行不创建重复资料。
- [x] 模板升级先给出具体变更和保留方案；验证保留用户内容、引用和实际配置，报告已完成、剩余以及需要重新确认的受影响部分。

## 实施依据

开始时读取[实施范围与验收约定](../spec.md)，再按本票分支读取[管理技能合同](../../mygamestudio-framework/contracts/management.md)、[项目协作配置合同](../../mygamestudio-framework/contracts/project-configuration.md)、[运行保障合同](../../mygamestudio-framework/contracts/runtime.md)。具体工程位置在实施时从当前项目读取。



## Comments

### 2026-09-08 — 实施完成(实施代理)

**结论:本票完成。** 六条验收标准全部通过;终验 `acceptance/05-adopt-existing-project/run.sh` 单次贯通运行 **128 PASS / 0 FAIL**(09:53:52→10:13:07,证据时间戳严格有序,无跨轮残留)。

#### 实际结果

- 插件包升至 `mygamestudio` 0.5.0(**不新增入口**,扩展 game-init 行为):SKILL.md 增加「已有项目」接手路径——现状分析六类区分(实际行为/已采纳要求/历史内容/缺口/冲突/未验证事实)、复用优先的接入清单(实际位置映射+旧格式迁移方案)、混合职责文档拆分纪律(**统筹不得为方便获得整个专业/混合文档写权限**)、中断恢复与重复运行、模板升级流程(先具体变更+保留方案,确认后版本校验应用);报告结构升级为「## 接入报告」(票 04 验收不受影响:其 turn 提示词自带结构要求)。
- 包内合同一致性:`internal/contracts/management.md` 与 `internal/proposals/project-onboarding.md` 文末「包内说明」更新为已实现接手路径;provenance manifest 与 fingerprints 同步(模板正文仍为设计仓库逐字节副本,未改)。
- 预置样例 `samples/nebula-drift/`(已有项目):src/ 实际实现 WASD+二段推进、assets/、package.json(工程配置)、docs/DESIGN_NOTES.md 已采纳「仅方向键/单次推进」(**与实现真实矛盾**)、docs/HANDBOOK.md 混合管理/设计/技术三种职责、tasks/ 旧格式两任务(进行中/想法)。
- 确定性检查 `tests/test_plugin_package.py` 扩展(TDD 红 23 项→绿):nebula-drift 结构、**矛盾双方在样例中真实存在**(静态可核对)、混合职责标记、旧格式任务(状态: 行,非五类分流);game-init SKILL.md 覆盖接手概念(六类/待决定/混合/拆分/恢复/重复运行/模板升级)。
- 验收资产 `acceptance/05-adopt-existing-project/`:`appserver_client.py` 在 04 客户端上新增**受控中断模式**(`--watch-audit`+`--kill-after-allows`:审计 allow 达阈值即对 codex 进程组 SIGKILL,退出码 3;codex 进程以独立进程组启动);`run.sh` 七轮流程;`runbook.md`。

#### 运行的验收及证据(`evidence/`)

环境(`environment.txt`):codex-cli **0.151.0**,macOS 26.5.1 arm64;隔离 HOME/CODEX_HOME 于 /tmp(auth.json 符号链接指向真实凭据);受保护区在仓库 `.tmp/accept-05/`。安装副本与仓库逐字节一致(模板注入前);注册面仍恰 5 个插件技能。**7 个真实模型 turn(其中 1 个被受控中断):**

- **W1 `$game-init` 只读分析**(统筹凭据):六类现状逐类有文件+行号证据;两处矛盾(操控方式、推进次数)给出双方证据(DESIGN_NOTES 已采纳 vs src/main.js、src/player.js 实际行为)并列为**待决定**;复用 tasks/ 与两份笔记(DESIGN_NOTES/TECH_NOTES 继续作为权威位置);HANDBOOK 按维护角色提出拆分方案;**零写入**(项目 SHA-256 前后一致)。
- **用户确认**(run.sh 代开发者,`confirm.md` 留档 11 条:协作配置/新增三文件/两任务迁移含状态映射/HANDBOOK 设计部分拆分至 DESIGN_NOTES(方案设计角色)/接入记录归档/本轮不动清单/矛盾待决定/越界探针)。
- **W2 应用——受控中断**:第 1 次受控写入 allow 落审计后对 codex 进程组 SIGKILL。证据:事件流有 turn/started 无 turn/completed、审计 allow 恰 1/6 项、项目仅新增 CONFIG.md(**中断与部分应用均为真实状态**;gate 落盘原子,无半写文件)。
- **用户手工修改**(run.sh 直接写,模拟开发者本人绕过通道的修改):README 末尾与 tasks/01 末尾各追加一行开发者注(`user-edits.txt`)。
- **W3 恢复**(统筹凭据,同实例续用):逐项核对实际文件→**跳过已完成的 CONFIG 不重写**→补齐 INDEX/PROJECT/两任务迁移/接入记录归档(producer allow 共 6)→两处开发者注原样保留→任务身份不变(01-wire-jump/02-starfield-bg),状态映射(进行中→ready-for-agent/执行中,想法→needs-triage/待做),状态变化记录迁移→**越界探针一次被拒**(task_grant)未重试;HANDBOOK/TECH_NOTES/src/assets/package.json 字节不变;策略字节不变。
- **W4 设计角色应用拆分**(纯指令轮,设计凭据):DESIGN_NOTES 经 `expected_sha256` 版本校验更新,既有已采纳要求(仅方向键/不支持 WASD/单次推进)**逐字保留、矛盾未裁决**,新增「从 HANDBOOK 拆入的设计草案」小节(护盾/连击保持草案状态);HANDBOOK 原文不动。
- **W5 重复运行**(只读):报告**无需改动**;零写入(前后 hash 一致);任务目录仍 2 个,无重复资料。
- **模板演进注入**(run.sh 受控修改**隔离安装副本**三模板:CONFIG 模板基线节/INDEX 升级行/task 模板版本字段;仓库 `plugin/templates/` 未动;前后指纹留档 `template-injection.txt`)——模拟插件模板升级,**验证的是升级流程本身**(先方案→确认→保留用户内容的应用→报告),发版分发机制不属本票。
- **W6 升级分析**(只读):模板对比+受影响文件具体变更+保留方案(用户内容/引用/实际配置)+需重新确认部分;零写入。
- **W7 升级应用**(确认后):四个文件全部 `expected_sha256` 版本校验更新;模板基线/升级行/模板版本字段就位;既有内容逐字保留(任务身份/进度/请求字段/标签映射/文档映射/**开发者注记**);DESIGN_NOTES 未被触碰;报告区分已完成/剩余/需重新确认。
- **统一接口**:`mgs_records.py config/list/show/verify` 全过——**任务根沿用 tasks/**(复用已有任务来源)、backend=local-markdown、两任务身份/分流/进度可回读、verify 10 项全过(五标签完整不冲突/核心文档唯一权威位置)。
- **终态**:相对基线**恰好**新增 4 个计划内文件(CONFIG/INDEX/PROJECT/接入记录)、修改 4 个计划内文件(README=用户手工、DESIGN_NOTES=设计拆分、两任务=迁移+升级),无删除、无计划外文件(`expected-changes.txt`);审计 write allow 11 / deny 1(越界),字段完整;项目与证据目录均无令牌泄漏;策略 SHA-256 三次核对不变。

复现:`acceptance/05-adopt-existing-project/run.sh`(7 次真实模型调用,其中 1 次受控中断);步骤、机制与覆盖声明见同目录 `runbook.md`。

#### 验收过程记录(前三次运行,如实留痕)

run1:W1 模型侧输出中段退化(乱码+元话语)致报告不完整(3 项失败),于 W3 前中止;修复=W1 提示要求紧凑报告(约 100 行内、行级证据、不生成 Markdown 链接)。run2:111 PASS/9 FAIL——W3 把清单第 7 条(设计拆分)当成自己本轮的完成条件,无法代写即停止,漏接入记录归档与越界探针(连锁 4 项失败);另 3 项为检查串半角冒号 vs 任务模板全角冒号(任务身份等字段);**W5 如实发现 run2 漏掉的真实缺口并只读报告(反编造行为符合设计预期,予以保留)**。修复=W2/W3 提示明确统筹条目范围(2/3/4/5/6/8)与第 7 条归属、报告必须以「## 接入报告」开头;检查改 `grep -E [:：]` 兼容两种冒号。run3:126/1,W1 以「复用」表达「沿用」(语义完整),检查放宽为等价措辞。run4:128/0,以上证据全部来自 run4(证据目录每轮整体再生成)。

#### 两轴复查(实施代理自查,无子代理环境)

- **Standards**:无文档化规范违反;判断级两处——`run.sh` 的 `file_unchanged` 与终态 Python 比对存在少量同形逻辑(各验收目录自包含的仓库约定下可接受);`appserver_client.py` 的 `count_audit_allows` 每次轮询全量重读审计文件(审计行数小,无实际影响)。报告结构标题从「初始化报告」改为「接入报告」不影响票 04 复现(04 的 turn 提示词自带结构要求,已核对)。
- **Spec**:六条标准逐条有真实验证(见上);无票外扩张——受控中断客户端与模板注入是「验证中断恢复/模板升级场景」的必要工具;GitHub Issues 后端与后端切换迁移不在本票验收标准内,未实现未声称(合同包内说明如实标注)。

#### 遗留事项

- 沿用票 01-04:codex exec 不解析 `$` 提及(验收走 app-server 通路);TUI 选择器未做 pty 自动化;令牌为承载凭据,turn 内对模型可见。
- 模板升级以受控注入模拟(验证流程而非发版分发);插件更新与分发机制属票 18 范畴。
- 矛盾裁决后的联动(以文档为准改代码,或以实现为准改文档)属后续业务轮;本票只验证矛盾**不被自动裁决**且待决定项全程传递。
- W2 中断点取决于模型写入速度(第 1 次 allow 后即 kill),断在哪个条目不定;检查只断言「部分应用」与「恢复完整」,不绑定具体断点。
- `run.sh` 依赖本机已登录 codex 凭据(符号链接),换机器需先 `codex login`。
- 本票只声明 Game-Init「新项目+本地 Markdown」与「接手已有项目+本地 Markdown」两条路径可用;GitHub Issues 后端、后端切换迁移与其余九个业务入口未实现、未声明。

#### 接续位置

票 06+(设计/规格入口)及后续需要「已有项目」场景的票可直接复用:扩展后的 `plugin/skills/game-init/SKILL.md`(接手路径与恢复/升级纪律)、`samples/nebula-drift/`(含真实矛盾与混合文档的已有项目样例)、`acceptance/05-adopt-existing-project/appserver_client.py`(04 客户端 + 受控中断模式)、run.sh 的「确认留档→受控中断→用户手工修改→恢复→重复运行→注入式模板升级」流程模式。运行保障沿用 `plugin/runtime/` 与 gate-protocol,无改动;统一接口 `records/mgs_records.py` 无改动(配置驱动任务根,天然支持沿用 tasks/)。

### 2026-09-09 — Fix（票 02-fix R3）：内容更新破坏既有权限位已修复

2026-09-09 独立审查实证 R3（报告：[../../mygamestudio-v1-review-fixes/evidence/review.md](../../mygamestudio-v1-review-fixes/evidence/review.md)）：受控内容更新以固定 0644 临时文件替换目标，0755 脚本更新后不可直接执行、0600 文件变 0644，与「接手既有项目保留有效结构」目标相悖。修复票 [02 运行保障门](../../mygamestudio-v1-review-fixes/issues/02-runtime-gate-review-fixes.md) 已修复并固化回归（内容更新与回滚路径逐位保留既有权限位；权限变化须经显式操作）。本票勾选历史不动。

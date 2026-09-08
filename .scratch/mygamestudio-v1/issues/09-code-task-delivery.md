# 09：完成一个代码任务并交接实际结果

**What to build:** Game-Code 与 Game-Implement 能接手当前原子任务，补充必要技术方案，完成代码、集成和匹配风险的验证，并留下可接续的结果。

**Blocked by:** [08：将规格拆成可接手的本地原子任务](08-spec-to-local-tasks.md)

**Status:** ready-for-agent

## 验收标准

- [x] 开始前读取实际任务、相关基线、工程及依赖，核对允许修改范围；实现方法来自项目实际配置，样例技术选择不成为框架默认引擎。
- [x] 必要技术设计由制作实现维护；发现产品规则冲突或目标变化时记录影响并交回对应流程，不自行降低要求。
- [x] 在样例中实际修改并集成代码，运行与变更风险匹配的行为检查，提供成果位置、适用版本和可复现验证证据。
- [x] Game-Implement 组织本任务专业工作与结果交接，不接管项目总体目标；尚未实现的专业入口不伪装成已调用能力。
- [x] 约定需要独立审查或人的验收但尚未完成时，结果保留待验收；后续审查技能尚未实现不导致虚构通过。
- [x] 失败或中断保存实际进度和缺口；普通实现不自动提交、推送、发布或修改远端工单，新增命令执行路径保持受控。

## 实施依据

开始时读取[实施范围与验收约定](../spec.md)，再按本票分支读取[制作技能合同](../../mygamestudio-framework/contracts/production.md)、[工作记录与任务后端合同](../../mygamestudio-framework/contracts/records.md)、[运行保障合同](../../mygamestudio-framework/contracts/runtime.md)。具体工程位置在实施时从当前项目读取。



## Comments

### 2026-09-08 — 实施完成(实施代理)

**结论:本票完成。** 六条验收标准全部通过;终验 `acceptance/09-code-task-delivery/run.sh` **单轮贯通 81 PASS / 0 FAIL**(16:44:40→约 17:04,4 个真实模型 turn,证据目录整轮再生成,无重跑)。

#### 实际结果

- 插件包升至 `mygamestudio` 0.9.0,新增第九个显式入口 `skills/game-implement/`(allow_implicit_invocation: false):
  - **Game-Implement** 组织入口:经统一接口接手**当前任务**(ready 选定或显式引用)→ 核对依赖/允许修改范围/**可开工不等于已获授权(以 mgs_scope 为准)** → 组织专业安排(代码路径归 Game-Code;**尚未实现的专业入口逐一声明未实现未调用,不伪装**)→ 维护**必要技术设计**(TECH_DESIGN 经受控写入;**产品规则冲突/规格缺口/目标变化记录影响交回统筹与设计,不自行降低要求、不静默代决定**)→ 组织集成与**风险匹配的验证**(检查必须实际运行;独立审查/人工验收未完成**保留待验收**)→ 交接(成果位置/适用版本/证据位置/接续位置/需统筹同步事项);**不接管项目总体目标或排期,任务进度与分流归统筹**;实现与验证方式**来自项目实际配置**(TECH_DESIGN/CONFIG),样例技术选择不成为框架默认引擎。
  - **Game-Code** 由最小入口升级为完整工作流:读取实际任务与基线(统一接口 show/deps,不凭记忆)→ mgs_scope 核对(与任务声称范围不一致以 mgs_scope 为准)→ 必要技术设计细化(规格留白集中为可核对命名参数,固定产品阈值不擅改)→ 受控代码写入(expected_sha256+回读)→ **风险匹配的行为层检查**(检查方式沿项目实际配置;无既有检查体系时一次性脚本放会话工作区/临时目录运行,**不进项目、不引入第二套工具链**;必须实际运行并记录真实输出;**未运行的检查明确列出、不虚构**)→ 结果记录(成果位置/适用版本/已执行检查与真实输出/未运行检查/遗留与接手条件)→ 待验收保留;失败或中断保存实际进度和缺口;普通实现不自动提交/推送/发布,新增命令执行路径保持受控。
- 角色资源策略扩展(本票验收采用,记录供后续票引用):implement 增加 `docs/mygamestudio/work/*/results/**`——对应《工作记录合同》「专业执行者保存自己的结果与证据」(与票 02 验收的实现角色范围一致;任务记录 task.md 仍归统筹,实现凭据写它会被 role_scope 拒)。运行保障组件本身无改动。
- 预置验收夹具 `acceptance/09-code-task-delivery/fixtures/`:票 08 拆单真实产物(02-09 任务记录与 03 的拆单结果,取自 08 验收终态未改动)+ 开发者「开工当前代码任务」请求;samples/tide-pool 本体保持 v1 不动(静态测试双向核对)。
- 确定性检查扩展:`test_plugin_package.py` 新增 9 技能注册面、game-implement/game-code 包内依据与关键概念、accept-09 夹具结构与样例本体保护(TDD 红→绿);provenance manifest/fingerprints 同步(0.9.0、production.md 包内说明适配)。

#### 运行的验收及证据(`evidence/`,36 个文件)

环境(`environment.txt`):codex-cli **0.151.0**,node v24.19.0,macOS 26.5.1 arm64;隔离 HOME/CODEX_HOME 于 /tmp(auth.json 符号链接);受保护区在仓库 `.tmp/accept-09/`。安装副本与仓库逐字节一致;注册面恰 9 个插件技能。起始夹具经统一接口核对:可开工=02-tide-timer、06-gull-sprite,04 等待 02。4 个真实模型 turn:

- **W1 `$game-implement`(实现凭据,任务 02-tide-timer,仅授 TECH_DESIGN)**:事件流证实读取包内技能与四份合同;统一接口 ready/deps/show 选定 02-tide-timer 并转述依赖(01 已完成)与允许修改范围;**如实报告 mgs_scope 仅授 TECH_DESIGN、与任务声称 src 范围的差异,未越权改代码**;专业安排逐项声明 Game-Art/Audio/Build/Review/Playtest 未实现未调用;TECH_DESIGN v1→v2(倒计时提示条/最后 10 秒强调/幂等结算路径/集中参数表;**发现并记录 GAME_DESIGN v2「场上持续刷新贝壳」与工程仅开局 6 枚的真实差异,交回统筹,不加机制不降要求**);边界探针 shell 直写 src EPERM、mgs_write 写设计基线 task_grant 拒;src 与任务记录字节不变。
- **W2 `$game-code`(实现凭据,同任务,授 src 两文件+TECH_DESIGN+02 results)**:按 TECH_DESIGN v2 实际实现 src/main.js 与 src/index.html(集中常量、roundState 门禁、settleRound 幂等、只结算不判负,顺带补上规格要求的画布边界限制);**行为检查真实运行**(会话工作区一次性 node DOM 桩脚本,覆盖 60→0 递减/提示条比例/urgent 强调/结算文案/settled 门禁/无判负,6 项 PASS 输出原样入证);首次写入末尾换行不一致时以 expected_sha256 精确重同步;结果记录含成果位置、适用版本、重跑命令与真实输出、**未运行检查(浏览器手工运行/独立审查/开发者试玩)明确列出**;边界探针同上;检查脚本未进项目。
- **W3 `$game-producer`(统筹凭据,任务 09-delivery-sync)**:按事实只改 02 的 task.md——进度 待执行→**待验收**(三项验收未完成不记已完成、不代验收)、结果索引引用具体结果文件、状态变化记一轮;委派下一可开工 06-gull-sprite 与 04 解锁条件;results 内容未动。
- **W4 交接核对(未参与者,零写入)**:定位成果与适用版本(源码哈希与结果记录一致)、验收状态如实(待验收、未冒充)、依赖与接续(04 双重阻塞、06 唯一可开工、刷新缺口交回)、组织与边界(未接管总体目标、未实现入口未伪装、**明确拒绝断言记录无法证明的「全量写入」**)、可复现性(**自行只读重跑行为检查全部 PASS**);项目哈希与 W3 后一致。
- 末尾:统一接口 config/list/show/deps/ready/verify 全过(02 因待验收退出可开工集合、06 仍可开工、04 仍因 02 阻塞、9 身份无重复、依赖无循环);终态恰好新增 02 结果记录一个文件、修改仅 src/main.js、src/index.html、TECH_DESIGN、02 task.md、无删除;审计 18 条字段完整(allow 9 / deny 9);策略 SHA-256 前后一致;项目与证据目录无令牌泄漏;`node --check` 最终代码通过。

复现:`acceptance/09-code-task-delivery/run.sh`(4 次真实模型调用,消耗额度;需本机 codex 登录与 node);步骤、机制与覆盖声明见同目录 `runbook.md`。

#### 两轴复查(实施代理自查,无子代理环境)

- **Standards**:仓库无编码规范文档,tracker/标签约定已按格式执行。判断级:(1) `appserver_client.py` 与 run.sh 检查助手沿用票 02-08 的每票自包含目录先例(近似复制,仅 clientInfo/说明差异),保持可独立复现;(2) 客户端保留未使用的受控中断参数(票 07 使用、08/09 留用),头部已声明;(3) 一处 `bash -c` 内 `grep -F './'$f''` 拼接写法经实跑验证;(4) CJK 长行与既有文件风格一致;(5) 测试概念清单长字面量沿用 `test_game_plan_skill_content` 既有形式。复查中修掉一处 fingerprints.json 整文件重排(改回原 indent=2 格式,diff 收敛为 3 行)。
- **Spec**:六条标准逐条有真实验证(见上);标准 6 的「失败或中断保存进度」以技能正文纪律+结果记录结构承载并经 W2 换行重同步实际演示,**未模拟真实中断**(受控中断矩阵项属票 15,如实声明);无票外扩张——两技能内容、包升级、夹具与验收脚本均直接对应票面,`node --check` 为验证侧补强。

#### 遗留事项

- **基线漂移残留**:组织轮把 TECH_DESIGN 升到 v2 后,02/04/05 任务记录「输入与基线」仍引用 v1,统一接口 `ready` 如实报告(接口语义正确);W3 按提示只同步了 02 的进度字段。需统筹下轮同步 02/04/05 的 TECH_DESIGN 引用与 PROJECT v2 的 02 安排行。
- GAME_DESIGN v2「场上持续刷新贝壳」与工程仅开局 6 枚的差异已交回统筹(尚无承接任务落单);W4 同时发现 03 拆单结果(票 08 产物)中 mgs_scope 绑定任务写作 08-gull-round-plan 与记录身份 03 不一致,属票 08 遗留观察,本票未改。
- 02 的浏览器手工运行、独立审查、开发者试玩未完成,任务保持**待验收**(审查/试玩入口属票 13/14);04/05/06 等任务执行属票 10+。
- 沿用票 01-08:codex exec 不解析 `$` 提及(验收走 app-server 通路);TUI 选择器未做 pty 自动化;令牌为承载凭据,turn 内对模型可见。
- 本票只声明 Game-Implement 组织入口与 Game-Code 完整工作流可用(在 tide-pool 纯 HTML/JS 组合上验证);Game-Art/Audio/Build/Review/Playtest 未实现、未声明;其他引擎/平台的组合未验证。

#### 接续位置

票 10+(资源任务)与票 12(构建运行)、15(目标变化/并发/中断恢复)可直接复用:`.tmp/accept-09/` 保存本轮终态(TECH_DESIGN v2、新 src 两文件、02 待验收记录与结果)可作为下票夹具基底(同 08→09 的复用方式);`plugin/skills/game-implement|game-code/` 与 implement 角色的 `work/*/results/**` 资源范围约定供后续票引用;运行保障沿用 `plugin/runtime/` 与 gate-protocol,无改动;统一接口 mgs_records.py 无改动。

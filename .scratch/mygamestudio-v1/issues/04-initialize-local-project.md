# 04：初始化一个使用本地任务记录的新项目

**What to build:** 开发者调用 Game-Init 后，得到具体协作配置和初始化清单；确认后按角色建立当前需要的文档和目录，本地任务、标签、资料入口与能力状态可回读。

**Blocked by:** [03：间接写入与检查故障仍受限制](03-indirect-write-failure-boundaries.md)

**Status:** ready-for-agent

## 验收标准

- [x] 从明确的目标项目和请求开始探查；无既定选择时提出本地 Markdown 建议，任务后端、标签映射、文档位置与术语/决定位置分别表达。
- [x] 具体清单提供实际落点、拟写内容、依据、维护角色和需确认事项；取得对应确认后应用，同一范围内不逐文件重复询问。
- [x] 按当前内容选择模板，管理、产品设计与技术资料由各自角色维护；所有文档步骤明确读取包内 writing-for-agents，未决定的引擎或目标不被编造成事实。
- [x] 建立可回读的本地任务与结果存取路径，能使用预置的小任务核验稳定身份、当前请求和专业结果；不在本票实现规格拆单。
- [x] 核对生成内容、资料引用、完整且无冲突的五标签映射；核心文档和协作配置各有唯一当前维护位置。
- [x] 分别报告文档接入就绪与运行保障就绪；外部访问、客户端指针或权限配置变更列明范围，普通初始化不自行扩大操作授权。

## 实施依据

开始时读取[实施范围与验收约定](../spec.md)，再按本票分支读取[管理技能合同](../../mygamestudio-framework/contracts/management.md)、[项目协作配置合同](../../mygamestudio-framework/contracts/project-configuration.md)、[工作记录与任务后端合同](../../mygamestudio-framework/contracts/records.md)。具体工程位置在实施时从当前项目读取。


## Comments

### 2026-09-08 — 实施完成(实施代理)

**结论:本票完成。** 六条验收标准全部通过;终验 `acceptance/04-initialize-local-project/run.sh` 单次贯通运行 **101 PASS / 0 FAIL**(08:05:52→08:24:28,证据时间戳严格有序)。

#### 实际结果

- 插件包升至 `mygamestudio` 0.4.0,新增第五个显式入口 `skills/game-init/`(allow_implicit_invocation: false):
  - 四阶段流程:探查(只读)→ 初始化清单 → 确认后应用(管理项经 mgs-gate;专业文档按清单交对应角色)→ 回读核对;报告结构固定并**分别**报告「文档接入就绪」与「运行保障就绪」;同一确认范围内不逐文件重复询问;未定引擎/平台以待定表达;不做规格拆单。
  - 包内依据补齐:`internal/contracts/project-configuration.md`(适配版)、`internal/proposals/project-onboarding.md`、`internal/proposals/project-layout.md`(链接适配);`management.md` 的 Game-Init 节改链包内合同并更新包内说明。
- **随包模板** `plugin/templates/`(15 文件):README 为链接适配版,project/work/records/evidence 全部模板为设计仓库逐字节副本;provenance 指纹覆盖 internal/ + templates/(静态测试改为双目录核对)。
- **本地 Markdown 任务后端统一接口** `plugin/records/mgs_records.py`(纯标准库,只读不写——项目写入一律经 mgs-gate):`load_config`/`list_tasks`/`read_task`/`verify_project` 四个逻辑操作 + CLI;以 CONFIG.md 为配置入口,不硬编码 work/;非 local-markdown 后端明确报不支持(首版未实现 GitHub Issues)。确定性接缝检查 `tests/test_records_backend.py`(TDD 红→绿:样例回读、后端不支持报错、五标签缺项/冲突、文档映射缺行/同位、核心文档缺失、任务字段/身份、结果索引一致性、CLI)。
- 预置样例 `samples/stardust-dash/`(新项目目标:只有开发者 README 的已定/未定事实与首个小任务请求,无任何 docs/mygamestudio 结构)。
- `tests/test_plugin_package.py` 扩展:5 技能注册面、模板全集、records 模块接缝、game-init 引用包内依据与关键约定、stardust-dash 结构、指纹双目录一致性。

#### 运行的验收及证据(`acceptance/04-initialize-local-project/evidence/`)

环境(`environment.txt`):codex-cli **0.151.0**,macOS 26.5.1 arm64;隔离 HOME/CODEX_HOME 于 /tmp(auth.json 符号链接指向真实凭据);受保护区在仓库 `.tmp/accept-04/`。安装副本与仓库 `plugin/` 逐字节一致;注册面恰好 5 个插件技能。**6 个真实模型 turn:**

- **W1 探查($game-init,统筹凭据,只读)**:协作配置建议分别表达任务后端(本地 Markdown+理由)/五标签映射/核心文档位置/术语与决定位置;清单覆盖五文档+首个任务记录,列落点/内容/依据/角色/待确认;未定引擎以待定表达;**零写入**(项目 SHA-256 前后一致)。
- **用户确认**:run.sh 代开发者确认清单(`confirm.md` 留档,固定任务身份 01-playable-slice、引擎保持待定、本轮无外部/客户端配置变更)。
- **W2 应用($game-init,统筹凭据)**:一个 turn 内经 mgs-gate 一次性创建 CONFIG/INDEX/PROJECT/任务记录(审计 allow=4,不逐文件询问);CONFIG 含统一接口回读所需四节与五标签一一映射;越界探针写 GAME_DESIGN 被拒(task_grant)且未重试;报告区分文档接入就绪/运行保障就绪,外部访问与配置变更范围为"无";策略字节不变。事件流证实读取了包内 writing-for-agents 与模板(从安装位置)。
- **W3 设计文档(方案设计凭据,纯指令轮)**:GAME_DESIGN.md 由 design 角色实例经 mgs-gate 写入,未定项待定。专用设计入口属票 06+,本轮由「已确认清单条目+角色绑定」驱动(runbook 已注明);统筹同目标写入已被 W2 探针证明拒绝。
- **W4 任务执行($game-code,实现凭据)**:TECH_DESIGN 初版(引擎如实待定,Canvas 仅记为首版实现方式非框架决定)、src/index.html+src/main.js 零依赖骨架、`results/2026-09-08.md` 结果记录(开头引用任务身份);实现角色 allow=5。
- **W5 统筹同步($game-producer)**:task.md 经 expected_sha256 受控更新——**任务身份保持 01-playable-slice 不变**,进度→待验收,结果索引引用 results 文件(创建+同步两次 allow)。
- **W6 状态回读($game-status,只读)**:从初始化后的资料入口读到任务待验收状态与设计/技术基线;零写入。
- **统一接口核验**:`mgs_records.py config/list/show/verify` 全通过——backend=local-markdown、任务(身份/分流/进度)、请求字段、结果清单、verify 10 项全过(五标签完整不冲突、核心文档唯一权威位置、任务结构、结果一致)。
- **终态核对**:项目相对基线**恰好**新增 9 个计划内文件(CONFIG/INDEX/PROJECT/GAME_DESIGN/TECH_DESIGN/任务记录/结果记录/src 两文件),无删除、无计划外文件;开发者 README 未被改动;三份文档均未出现 Phaser/Unity/Godot/Cocos/Three.js 等编造选型;策略 SHA-256 三次核对不变;审计字段完整、无令牌泄漏(项目与证据目录均扫描)。

复现:`acceptance/04-initialize-local-project/run.sh`(约 6 次真实模型调用,消耗额度);步骤与边界见同目录 `runbook.md`。

#### 验收过程记录(前三次运行,如实留痕)

run1:run.sh 自身 bug——回合文本中 `$TASK_ID` 紧跟全角标点被 bash 解析为多字节变量名,W2 前中止(未消耗 W2+ 模型调用)。run2:89 PASS/14 FAIL,W4 在 800s 超时内尝试驱动无头浏览器验证导致 turn 未完成、结果记录未写;**W5 拒绝在无实际结果时把任务同步为"待验收"(反编造行为符合设计预期,予以保留)**;修复=W4 改为先写全部交付再做有界轻量验证、超时 1100s。run3:99 PASS/2 FAIL,均为脚本侧表述匹配问题(W2 报告用中文"获准"而非 allow 字面量;计划内文件清单未按字典序比较),产品行为与审计均正确。run4:101 PASS/0 FAIL,以上证据全部来自 run4(证据目录每轮整体再生成)。

#### 两轴复查(实施代理自查,无子代理环境)

- **Standards**:无文档化规范违反;复查修复两处——`_strip_annotation` 补全角括号 `(` 支持(实测生成项目的 CONFIG 确实使用了全角括号;该行非核心文档行,原实现恰好未影响验收结果)、测试文件移除未用 `import shutil`;修复后四个确定性套件重跑通过,与验收结论零行为差异。判断级遗留:`list_tasks` 静默跳过缺少 task.md 的任务目录(无现行需求驱动校验,留给后续票补后端操作时处理);CLI 退出码(0/1/2)未写入模块 docstring。
- **Spec**:六条标准逐条有真实验证(见上);无票外扩张——records 模块与随包模板分别由「可回读的本地任务与结果存取路径」与「按当前内容选择模板」要求;management.md 改链为合同一致性维护。

#### 遗留事项

- 沿用票 01-03:codex exec 不解析 `$` 提及(验收走 app-server 通路);TUI 选择器未做 pty 自动化;令牌为承载凭据,turn 内对模型可见。
- 设计/规格入口(Game-Design/Game-Spec)属票 06+:本票初始化流程中专业设计文档的写入由「确认清单条目+设计角色凭据」经 mgs-gate 完成,不宣称设计入口已可用。
- GitHub Issues 任务后端、后端切换迁移属票 05/17 范畴;`mgs_records.py` 只读不写,写入型后端操作(创建/更新/追加)按记录合同经 mgs-gate 由对应角色执行,后续票如需程序化写入再扩展。
- 接手已有项目的深度分析与补齐属票 05;中断恢复/重复运行的完整场景(用户中途改文件后重跑)本票未做专项 turn,仅由技能与流程文本约定(runbook 已列);票 05 验收时应覆盖。
- `run.sh` 依赖本机已登录 codex 凭据(符号链接),换机器需先 `codex login`。
- 本票只声明 Game-Init「新项目+本地 Markdown」初始化路径可用;其余九个业务入口未实现、未声明。

#### 接续位置

票 05(接手已有项目)可直接复用:`plugin/skills/game-init/`(四阶段流程含已有项目分析分支的合同依据)、`plugin/templates/`、`plugin/records/mgs_records.py`(统一回读/核验)、`tests/test_records_backend.py`、`acceptance/04-initialize-local-project/` 的 `appserver_client.py`(支持无 mention 纯指令轮)与 run.sh 的隔离布局/清单确认模式(用户确认以 confirm.md 留档)。运行保障沿用票 02/03 的 `plugin/runtime/` 与 gate-protocol,无需改动。

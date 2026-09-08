# 13：独立审查实际待交付成果

**What to build:** Game-Review 以独立同专业实例检查真实成果的规范与需求符合性，准确定位问题，并可对修复结果复核。

**Blocked by:** [06：把功能想法形成当前可执行规格](06-idea-to-current-spec.md)

**Status:** ready-for-agent

## 验收标准

- [x] 按被审对象选择独立同专业执行实例，直接读取规范、实际成果、当前规格及必要证据，不仅依赖作者总结；不新增常设评审角色。
- [x] 代码 Standards 与 Spec 两轴独立执行、分别呈现；设计或资源按其专业标准及需求符合性检查。
- [x] 明确固定待审版本和完整范围，包含适用的已提交、暂存、未暂存和新建成果；预置缺陷样例能发现被仅比较 HEAD 漏掉的问题。
- [x] 每项问题关联具体证据和影响，区分明确规则违背、专业判断与未能检查，避免以报告生成等同验收通过。
- [x] 审查实例仅写报告和证据，不能修改待审专业成果；修复后针对实际新版本复核，旧结论不会被挪作新版本通过证明。
- [x] 采用预置设计、代码或资源成果独立验收，不依赖后续完整制作流程；未实现的运行能力清楚标为覆盖限制。

## 实施依据

开始时读取[实施范围与验收约定](../spec.md)，再按本票分支读取[审查与试玩合同](../../mygamestudio-framework/contracts/verification.md)、[运行保障合同](../../mygamestudio-framework/contracts/runtime.md)。具体工程位置在实施时从当前项目读取。


## Comments

### 2026-09-08 — 实施完成(实施代理)

**结论:本票完成。** 六条验收标准全部通过;终验 `acceptance/13-independent-deliverable-review/run.sh` 真实运行 **98 PASS / 3 FAIL(run1)**,三个 FAIL 均为检查侧问题(模型行为全部正确),修复检查逻辑后对同一证据重放 **4/4 通过**——有效结果 **102 项全过**(约 20:57 起,4 个真实模型 turn,证据目录整轮生成)。

#### 实际结果

- 插件包升至 `mygamestudio` 0.13.0,新增第十三个显式入口 `skills/game-review/`(allow_implicit_invocation: false):
  - **Game-Review** 独立审查工作流:输入必须**显式引用待审成果和版本**(审查对象不从可开工集合选取——待验收成果不在其中)→ 独立读取(统一接口 show/deps+规范+实际文件;**作者结果记录只是待核对线索**,声称与实际不符本身即问题)→ **固定待审版本与完整范围**(文件清单+SHA-256 指纹;覆盖适用的已提交/暂存/未暂存/新建;**直接读工作区实际文件,不以 HEAD、暂存区或 git 对比替代**;untracked 文件任何 diff 都不显示,必须靠完整清单发现)→ **按对象选轴**:代码 Standards/Spec 两轴独立执行分别呈现,资源按专业标准+需求符合性两轴,已有可靠自动化只在确认针对当前版本时引用 → **检查实际运行**(行为冒烟/规格/引用解析;一次性脚本不进项目;无法自动核验归**未能检查**并说明所需条件)→ **问题清单三分类**(位置/证据/影响/明确规则违背|专业判断|未能检查)→ **写入仅限审查记录与证据**(项目 evidence/,经 mgs_write;**不修改待审成果**,修复返回执行流程)→ **修复后针对实际新版本复核**(重新登记指纹、重新运行检查、逐项旧问题状态;**旧结论不挪用**——旧指纹≠当前即证明版本已变)→ **覆盖限制如实标注;报告生成不等于验收通过**,人工项保持待验收。
  - 包内合同新增 `internal/contracts/verification.md`(审查与试玩合同适配版;两合同小节与设计仓库原文逐字一致,仅引言行链接适配+包内说明声明 Game-Review 已实现/Game-Playtest 待后续);production.md 包内说明同步现状;provenance manifest/fingerprints 同步(0.13.0)。
- **资源策略演进(共享实现选择,记录供后续票引用)**:implement 角色新增 `docs/mygamestudio/evidence/**`(框架角色表「制作实现自身可维护专业结果与证据」+项目布局「evidence/ 由执行者或审查者保存证据」);purposes 新增 `review`(restrict=evidence/**)——共同合同「审查、试玩等模式按本次用途收窄写入范围」的结构化落地。**三层交集(角色∩用途∩任务授权)恰为 evidence/**:审查实例碰不到待审成果;即使任务授权放宽,purpose 层仍封顶(确定性测试第 21 项:rule_stage=purpose 拒绝+字节不变)。GateService 零改动(purpose 数据驱动);唯一运行侧改动=`mgsrt_admin.py` 签发 CLI 的用途白名单加 `review`(最小演进,不是去掉校验)。
- 预置验收夹具 `acceptance/13-.../fixtures/`:承接票 10 终态的 **06 海鸥 SVG 两份+待验收记录与结果**(取自 `.tmp/accept-10` 逐字节;此前未进任何持久夹具)与票 12 终态的 **build/ 两产物+11 待验收记录与结果**(取自 `.tmp/accept-12` 逐字节)+开发者审查请求 README——使协调者指定的四个待审对象(02/06/10/11)完整可审。
- 确定性检查扩展:`test_plugin_package.py` 新增 13 技能注册面、game-review 内容纪律(36 概念)、accept-13 夹具结构(含 06/11 结果记录登记哈希与实际文件一致性、build 与票 10 夹具 src 逐字节一致)——TDD 红 12 项→绿;`test_runtime_gate.py` 新增第 21 项(review 用途收窄+放宽授权仍封顶+拒绝后字节不变)。

#### 预置缺陷样例与「仅比较 HEAD 漏掉」的实证(标准 3)

夹具就位后 git commit 形成 HEAD 基线(票 01-12 交付物=已提交形态),注入三类工作区缺陷:**A(未暂存)** src/main.js urgent 阈值 10→7(违反 TECH_DESIGN v3 参数表 `(0,10]` 与 02 完成标准——`git show HEAD` 看不到);**B(新建未跟踪)** src/tide-extra.js(初始显示 90/aria-valuemax 90,违反 60 秒规格——**任何 git diff 都不显示 untracked**);**C(暂存)** src/index.html 增加 tide-extra.js 引用(`git diff` 未暂存形态看不到)。验收侧 page-smoke.js(按 index.html 实际引用顺序在 node DOM 桩加载驱动)证明缺陷行为层真实生效(`DEFECT-SMOKE-OK:初始 90/aria-valuemax 90/阈值 7`),git-state.txt/head-vs-worktree.txt 留证 HEAD 与工作区差异。

#### 运行的验收及证据(`evidence/`,38 个文件)

环境(`environment.txt`):codex-cli **0.151.0**,node v24.19.0,Python 3.14.4,ffmpeg 7.1,macOS 26.5.1 arm64;隔离 HOME/CODEX_HOME 于 /tmp(auth.json 符号链接);受保护区在仓库 `.tmp/accept-13/`。安装副本与仓库逐字节一致;注册面恰 13 个插件技能。起始核对:可开工集合为空(四对象均待验收;**审查按显式引用选取,不走 ready**)、verify 通过、缺陷注入后 git 三态正确。**4 个真实模型 turn:**

- **W1 `$game-review`(rev1,review 用途,任务 13-review-code-deliverables)**:事件流证实读包内技能与合同+统一接口;待审范围以**工作区实际文件清单+逐文件 SHA-256** 固定(含已暂存/未暂存/新建三形态+「没有用 HEAD 或 diff 替代文件读取」明示);**三类预置缺陷全部发现并正确定类**——urgent 阈值 7(明确规则违背)、入口加载未跟踪调试脚本致 HUD 90 与 aria 语义矛盾(明确规则违背)、**并额外发现 build↔src 版本对应被未提交修改破坏**(两产物哈希≠当前 src,分类明确规则违背——票 12 交付时的对应真实存在,被缺陷注入破坏,审查如实抓住);7 项问题全带位置/证据/影响/分类(5 规则违背+2 未能检查:静态服务被沙箱拒、无 GUI/人工反馈);Standards/Spec 两轴分别呈现;行为检查真实运行(node DOM 桩);报告明言「作者结果中的旧哈希与通过结论不能用于当前待审版本」;两份审查记录经 mgs_write 落 evidence/(审计 allow 6);**边界探针原样记录**(shell 直写 `operation not permitted`+mgs_write 写 src `deny/task_grant`);审查后项目哈希核对**仅新增 evidence/**。
- **W2 `$game-review`(rev2,独立新实例,任务 13-review-asset-deliverables)**:06 两 SVG+10 WAV 待审指纹登记;**专业标准轴实际运行**(xml 解析核对 viewBox 96×64/透明/姿态命名;ffprobe 读实际规格 44100/pcm_s16le/0.56s+完整解码)与**需求符合性轴**(GAME_DESIGN v3 预警条目上行双音/约 1 秒/单次/无视觉;海鸥不可交互)分别呈现;**听感/审美/集成核对全部归未能检查**并给出所需真实反馈方式;明确「审查报告生成不等于验收通过;资源变化后必须登记新哈希并重新审查」;两份审查记录落 evidence/;探针 mgs_write 写 WAV 被拒;审查后 assets 字节不变。
- **W3 `$game-code`(fix1,production 用途,归任务 02,授 src+02 results)**:按 W1 审查记录逐项修复——阈值恢复 10、index.html 移除 tide-extra 引用、**tide-extra.js 因受控通道无删除原语而解除引用+无副作用化并如实记录该限制**(修复说明「受控通道没有删除原语,无法物理删除」);自跑行为检查;修复说明落 02 的 results/2026-09-08-fix.md;task.md/evidence/build 均未动(哈希核对);审计 production allow 写 src 三处+结果一处。
- **W4 `$game-review`(rev3,独立新实例,任务 13-review-recheck)**:**旧结论不挪用**——输入含 W1 旧报告,但以当前实际文件为准**重新登记全部指纹并逐项对照「旧 25df4972…/95371465…/be2ae083…→已变化」**;针对当前版本重新运行 DOM 行为检查(初始 60/恰 10 秒 urgent/0 秒结算幂等);逐项旧问题状态(02-1/2 已修复、02-3 部分修复(占位文件残留)、02-4/5 未修复(需 GUI/人工/未实现系统)、11-1/2 已修复(**build↔src 恢复逐字节一致**——修复恰恢复 HEAD 字节)、11-3 未修复(静态服务仍被沙箱拒)、11-4 未修复);人工项保持待验收;复核记录落 evidence/;复核后 src 未再被改动。
- 末尾:统一接口 config/list(11 身份)/show(02 含 fix)/deps/ready(startable 空——**02 仍待验收,不以复核替代人工项**)/verify 全过;终态**恰新增 evidence/ 5 审查记录+02 修复说明、修改仅 src 相关文件、无删除**;审计字段完整;策略 SHA-256 前后一致(8370b8db…);四令牌无泄漏;项目内无检查脚本残留。

复现:`acceptance/13-independent-deliverable-review/run.sh`(4 次真实模型调用;需本机 codex 登录、python3、node、ffmpeg/ffprobe);步骤与覆盖声明见 `runbook.md`。

#### 验收过程记录(run1 的三个检查侧 FAIL,如实留痕)

run1:98 PASS/3 FAIL,均为检查侧而非产品行为——(1) W1 范围形态检查要求「已提交|提交」字面,模型以「已暂存、未暂存和新建」+「没有用 HEAD 或 diff 替代」表述(同票 09-12 词面教训);(2) W1 边界核对检查只看报告,而探针结果被模型完整记录在审查记录(evidence/2026-09-08-review-02-tide-timer.md:operation not permitted+deny/task_grant 原文)——探针落证据区是合理设计,检查改为报告或审查记录任一;(3) page-smoke.js 的 DOM 桩未解析 HTML 静态属性,修复态(无脚本覆盖)读到 aria-valuemax=undefined——**W3 修复本身完全正确**(阈值/引用/通道限制处理全部达标),是验收脚本桩缺陷。三处检查修复后对 run1 已采集的真实证据重放 4/4 通过(含 defect 分支回归验证,证明桩修复不破坏原断言);修复后的 run.sh 供未来整轮复现。三轮模型行为(审查发现、资源两轴、修复处置、新版本复核)在 run1 中全部正确。

#### 两轴复查(实施代理自查,无子代理环境)

- **Standards**:仓库无编码规范文档,tracker/标签约定已按格式执行。复查发现并修复一处实质问题:**provenance 失实**——manifest 声明 production.md 包内说明已更新但文件实际未改,且 fingerprints 中其 source 历史被截短;已实际更新 production.md(现状声明+改链包内审查与试玩合同)、恢复完整 source 历史并重算指纹,静态测试通过。判断级保留:(1) `appserver_client.py` 沿用票 02-12 每票自包含先例(仅 clientInfo 差异);(2) run.sh 对模型措辞的检查正则天然词面脆弱,run1 三处检查侧 FAIL 均属此类,已修+重放并如实留痕;(3) `mgsrt_admin.py` choices 扩展是最小白名单演进(策略 restrict 承担实际收窄,CLI 未去掉校验);(4) CJK 长行与既有文件风格一致。
- **Spec**:六条标准逐条有真实验证(见上);判断级观察:(1) 「已提交形态」由 HEAD 基线承载、W1 以偏差形态(暂存/未暂存/新建)+「不以 HEAD 替代」声明覆盖,报告未逐字枚举四形态——行为满足标准本意(完整范围+发现 HEAD-only 漏掉的问题),词面枚举不构成失败;(2) 「设计成果审查」按票面「设计**或**资源」由资源两件(SVG+WAV)承载,设计侧(design 角色)evidence 授权未开,在 runbook 覆盖声明如实标注。无票外扩张——技能、合同、策略演进、CLI 白名单、夹具与验收脚本均直接对应票面;samples/tide-pool 本体、GateService、统一接口 mgs_records.py 零改动(静态测试双向核对)。

#### 遗留事项

- **02/06/10/11 保持待验收**:独立审查一项现有事实(evidence/ 5 份记录);02 的人工项(浏览器手工运行、开发者试玩)、06 的开发者审美确认与 05 构建核对、10 的开发者试听与正式接线核对、11 的人工试玩与后续集成后重新构建均未完成;**统筹尚未同步**(任务记录的结果索引未引用 evidence 审查记录;本票无统筹 turn,按直接调用留痕、统筹下次显式介入同步的既定模式)。tide-extra.js 物理残留(通道无删除原语),待统筹安排清理或随 04/05 接手处理。
- **覆盖限制**:Game-Playtest 试玩入口未实现(票 14);design 角色侧的设计成果审查未开 evidence 授权(策略仅 implement+evidence/**;框架角色表设计侧可维护内容不含 evidence);听感/审美/浏览器 GUI 判断只能由人做;会话内静态服务取回被沙箱拒绝(沿用票 12 限制)。
- 审查者对「未提交+新建」范围的发现依赖提示词中的方法要求(直接读工作区+完整清单)与技能正文纪律,宿主级「防 HEAD-only 审查」硬拦截不存在(也不可能——这是方法正确性问题,由纪律+验收保证)。
- 沿用票 01-12:codex exec 不解析 `$` 提及(验收走 app-server 通路);TUI 选择器未做 pty 自动化;令牌为承载凭据,turn 内对模型可见。
- 本票只声明 Game-Review 在「本地文件审查+node/python/ffprobe 检查」组合上可用;Playtest 未实现、未声明。

#### 接续位置

票 14(试玩)、15(目标变化/并发/中断恢复)、16(完整闭环)可直接复用:`plugin/skills/game-review/` 的两轴纪律、版本指纹固定与复核模式;review 用途资源策略与 evidence/** 落点约定(W4 复核模式可直接给 Playtest 借鉴:新证据登记新指纹);`.tmp/accept-13/` 保存本轮终态(evidence/ 5 审查记录、02 修复后 src、git 三态)可作票 14+ 夹具基底(.tmp 属 gitignored 临时区,持久夹具以 acceptance/ 目录为准);运行保障沿用 `plugin/runtime/` 与 gate-protocol(仅签发 CLI 白名单扩展);统一接口 mgs_records.py 无改动。


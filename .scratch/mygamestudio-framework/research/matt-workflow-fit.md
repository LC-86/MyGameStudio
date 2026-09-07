# Matt 工作路线与 MyGameStudio 的兼容性核对

日期：2026-09-07。状态：研究材料，技能清单和改造方案待用户决定。本次只读取本地 Skill 与已确认项目记录；没有执行其中的实现、审查、提交、安装或治理文件修改步骤。

## 结论

可以借鉴“澄清目标 → 形成规格 → 拆成可验证小成果 → 实现 → 独立审查”的方法，但这些原始 Skill 的默认写入、标记、检查和提交行为不能直接构成游戏工作流。下面的“建议”是兼容性判断，不是已经采纳的技能清单。

## 逐项核对

| 研究对象 | 源文件的实际规则 | 可保留的方法 | 必须重定的部分（建议） |
| --- | --- | --- | --- |
| wayfinder | 默认解决决策而非执行交付；地图为索引；按依赖处理前沿；一会话最多解决一张非研究票。[7–23、65–80、103–126 行](/Users/cuilei/.agents/skills/wayfinder/SKILL.md:7) | 目的、未知问题、已决问题、范围和依赖分开记录 | 作为重大不确定性下的规划方法；不能将每个小功能都升级成地图，也不能将其会话限额直接作为统筹连续调度的限额 |
| grill-with-docs | 直接组合 grilling 与 domain-modeling。[3–7 行](/Users/cuilei/.agents/skills/grill-with-docs/SKILL.md:3)；后者要求术语明确时立即改 CONTEXT.md，ADR 有专门条件。[60–74 行](/Users/cuilei/.agents/skills/domain-modeling/SKILL.md:60) | 用场景追问，逐步形成一致术语，重要取舍保留原因 | 按产物归属委派写入：统筹记录目标、任务、决定的管理信息；游戏设计与技术设计由其维护角色更新。不能让“讨论时自动落文档”穿透统筹写入边界 |
| to-spec | 汇总现有讨论；先明确测试位置；规格发布后直接 ready-for-agent；模板要求很长且详尽的用户故事。[7–41 行](/Users/cuilei/.agents/skills/to-spec/SKILL.md:7) | 整理已讨论的问题、方案、边界和验证方式，必要时保存原型中的精确决定 | 规格围绕本轮小成果；按玩法、资源或工程工作选择表达方式。规格已整理不代表已授权实现、可以无人执行或可以免人工验收 |
| to-tickets | 每票为跨 schema/API/UI/tests 的完整纵向切片、可演示或验证、适配一个新上下文；有依赖边。[25–40 行](/Users/cuilei/.agents/skills/to-tickets/SKILL.md:25)；默认 ready-for-agent。[58–80 行](/Users/cuilei/.agents/skills/to-tickets/SKILL.md:58) | 小成果可独立检查、粒度适合一次执行、依赖只记录真实前提 | 将 Web 分层例子改为游戏可检查成果。单独音效、动画、玩法试验也可能是合理任务，不能强迫每票包含完整游戏管线。逐票确定执行方、所需能力和验收方；映射到游戏项目工作目录 |
| implement | 优先用 TDD；定期类型检查及单测，最后全套测试；完成后调用 code-review，随后提交当前分支。[7–15 行](/Users/cuilei/.agents/skills/implement/SKILL.md:7) | 按规格和任务执行，过程中验证，适用时独立审查 | 以任务约定、项目实际工具和风险选择检查；代码、美术、音频、构建采用不同验证。提交仍需用户明确授权，不能随实现默认发生 |
| code-review | 对固定点与 HEAD 之间的差异做 Standards 与 Spec 两轴独立子代理审查；命令固定为三点 diff。[6–23 行](/Users/cuilei/.agents/skills/code-review/SKILL.md:6)、[58–78 行](/Users/cuilei/.agents/skills/code-review/SKILL.md:58) | 独立上下文；分别检查约定符合性与需求符合性；结果标注证据 | 明确实际待审成果及版本；待提交变更、设计和资源需不同审查输入。代码审查不替代运行、试玩、听音或人工体验验收 |

## 四个优先隐患

核对五类标签的完整语义时，读取后续[triage 标签研究](triage-labels-fit.md)：完整 triage 正文中 ready-for-human 的使用范围包括人工判断、设计决定与手工测试，较下方仅按项目简表解释的范围更广。

### 1. 默认“可交给 Agent”掩盖了执行条件与人工验收

事实：本项目词表将 ready-for-agent 定义为已充分说明、适合 AFK Agent；ready-for-human 表示需要人实现，而非需要人验收。[triage-labels.md:3–9](/Users/cuilei/MyOS/01_Projects/plugins/MyGameStudio/docs/agents/triage-labels.md:3)。to-spec 直接赋前者，to-tickets 的本地模板也固定前者。

建议：至少分开“执行由谁负责”“当前是否具备执行条件”“验收需要谁参与”。AI 制作的手感原型可以仍待开发者试玩；需要人在特定工具操作的任务也可以有可由 Agent 核对的输出。不能把 for-human 当成所有人工参与事项的总状态。Q24/Q25 的最新用户决定由主会话记录，本研究不代替记录或关闭决定票。

### 2. 实现后的默认审查可能看不到刚做的工作

事实：implement 先 review 后 commit；code-review 固定读取 `git diff <fixed-point>...HEAD`。这条命令针对提交之间的差异，未提交工作区、暂存区和未跟踪产物不进入该审查范围。若本轮没有新提交且基线就是 HEAD，可得到空差异，随后按原技能 23 行中止。

建议：审查输入必须覆盖本轮实际成果，并有可识别版本或快照；结果明确列出覆盖与未覆盖。独立审查通过与真实游戏验收分别记录。原始 code-review 的 description 也不带 disable-model-invocation，与本项目全部 Skill 显式调用的规则需要适配；本研究未验证具体客户端的实现机制。

### 3. 组合技能与默认提交会穿透权限边界

事实：已确认规则允许统筹组合技能，但统筹自身仅写管理文档。[调用边界 Answer:32–36](/Users/cuilei/MyOS/01_Projects/plugins/MyGameStudio/.scratch/mygamestudio-framework/issues/01-explicit-invocation.md:32)。domain-modeling 的即时术语写入与 implement 的默认 commit，都是其源工作流中的动作。

建议：方法可以复用，实际写入由具备该产物职责的执行实例完成；术语、设计、技术决定分别遵循归属。Game-Review 是按任务启动的独立执行方式，不新增常设角色。明确实施授权和 Git 提交授权分别核对，不用原 Skill 默认步骤替用户授权。

### 4. 禁止路径和固定存储会破坏已确认的可追溯交接

事实：to-spec 55–57 行、to-tickets 105 行笼统要求避免具体文件路径或代码片段，并为原型的精确决定片段提供例外。[to-spec](/Users/cuilei/.agents/skills/to-spec/SKILL.md:55)、[to-tickets](/Users/cuilei/.agents/skills/to-tickets/SKILL.md:105)。to-tickets 62 行规定本地 `.scratch/<feature-slug>/issues/`。

项目已采用的未来游戏目录是 `docs/mygamestudio/work/`，并通过引用连接设计、资源、构建和原型。[project-layout.md:7–17、24–41](/Users/cuilei/MyOS/01_Projects/plugins/MyGameStudio/.scratch/mygamestudio-framework/proposals/project-layout.md:7)。用户还确认请求和结果关联实际基线版本。[交接票:118–122](/Users/cuilei/MyOS/01_Projects/plugins/MyGameStudio/.scratch/mygamestudio-framework/issues/04-project-handoffs.md:118)。

建议：区分“不要过早固化代码实现位置”和“必须提供可定位、可辨认版本的依据引用”。后者应保留。将任务存储映射到实际项目目录；当前插件设计用的 `.scratch/` tracker 与未来游戏项目的 `docs/mygamestudio/work/` 是两个对象。

## 设计依据的边界

- 已确认三角色及产物归属：[角色票 Answer:115–140](/Users/cuilei/MyOS/01_Projects/plugins/MyGameStudio/.scratch/mygamestudio-framework/issues/02-role-responsibilities.md:115)。技术架构及 TDD 归制作实现维护，产品体验要求归方案设计。
- 已确认轻量流程、按当前一步推进和目标变化优先同步：[流程票 Answer:66–85](/Users/cuilei/MyOS/01_Projects/plugins/MyGameStudio/.scratch/mygamestudio-framework/issues/03-workflow-gates.md:66)。不能用“先写完全部故事再交给 Agent”重新引入整项目定稿前置门槛。
- 写给 Agent 的文件遵循条件明确的上下文引用、可检查完成条件、单一权威正文。[writing-for-agents:10–18、45–52、76–80](/Users/cuilei/.agents/skills/writing-for-agents/SKILL.md:10)。后续具体 Skill 应引用共用规则，专业分支按需加载；本次没有编写或修改 Skill。

本研究依据本机读取时的文件，不声称与 GitHub 上的最新版本完全一致；未运行待研究技能，也未测试插件技术隔离。上述链接行号为本次读取结果，后续源文件修改可能改变位置。

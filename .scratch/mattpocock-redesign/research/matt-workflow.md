# Matt Pocock Skills 当前上游深度分析

核实时间：2026-09-15（Asia/Shanghai）。研究性质：官方源代码静态分析与仓库清单核对；不等同于客户端运行验收。

## 证据基线与结论

- 上游 `main` 固定为 `3cca18b368ae95cdbdebbff572ccafa662551015`，本轮通过 GitHub 页面和独立浅克隆读取；本地快照 `/tmp/matt-skills-analysis.5eJEJm/upstream`。[固定仓库][tree]
- `package.json` 与 Claude 插件 manifest 均为 `1.2.3`。共有 **37 个 `SKILL.md`**：engineering 18、productivity 7、misc 4、in-progress 8。正式发布集仅前两类 **25 个**，与 manifest 的 25 个目录逐项匹配；正式集包含 14 个用户调用技能与 11 个模型可调用技能。所有 37 个技能都附带 `agents/openai.yaml`，本轮检查两套 invocation 标志一致。[仓库分类规则][agents] [发布清单][manifest]
- 核心是由人选择、可组合的技能和工程纪律。上游确实提供 `ask-matt` 推荐的主流程及入口分支；同时允许小工作直接实现、独立调试、独立评审、研究和原型。不能把“完整主流程每次必走”当作上游制度。[路由][ask-matt]
- 对 MyGameStudio 的建议：继承其决策、规格、拆票、实施和评审制度，把游戏专业性放在问题、行为契约、证据和验收方式上。避免另造一套审批状态、规格真源或实现调度器。此为研究建议，尚非用户采纳的改版决议。

## 全量技能清单

`U` 表示用户显式调用；`M` 表示用户或模型可调用。下表以各技能正文为源，不把目录中草案算作正式发布能力。

| 正式技能 | 调用 | 入口与产物、边界 |
|---|---|---|
| [ask-matt][ask-matt] | U | 解释技能及主流程，供人选择；不自动调用其他 U 技能 |
| [setup-matt-pocock-skills][setup] | U | 探索后配置 tracker、triage 映射、领域文档布局；草稿给人看后写入 |
| [grill-with-docs][grill-with-docs] | U | 组合 grilling 和 domain-modeling；访谈并落术语与适量 ADR |
| [wayfinder][wayfinder] | U | 多会话模糊工作变成决策地图；默认止于路线清晰 |
| [to-spec][to-spec] | U | 从既有讨论综合规格；确认测试接口；发布 ready-for-agent |
| [to-tickets][to-tickets] | U | 从规格、计划或讨论拆可演示的纵向切片；人确认粒度和依赖后发布 |
| [implement][implement] | U | 按规格或票实施；预先约定接口处 TDD、检查、评审、提交 |
| [triage][triage] | U | 处理外来请求；复现、去重、查历史拒绝、形成 agent brief |
| [improve-codebase-architecture][architecture] | U | 找近期高变更区的架构摩擦；HTML 候选报告；人选后讨论 |
| [codebase-design][codebase-design] | M | 深模块、接口、测试接缝、适配器的共同设计语言 |
| [domain-modeling][domain-modeling] | M | 澄清领域术语、边界场景和代码矛盾；词汇表与必要 ADR |
| [research][research] | M | 子代理读第一方资料，留下逐项引用的单份研究 Markdown |
| [prototype][prototype] | M | 一条设计问题的可丢弃逻辑或 UI 原型；由人体验、留下结论和原型指针 |
| [tdd][tdd] | M | 通过约定公共接口，一次一个行为的 red→green；不批量写实现镜像测试 |
| [code-review][code-review] | M | 对固定比较点的变更，独立子代理并行作 Standards 与 Spec 评审 |
| [diagnosing-bugs][diagnosing-bugs] | M | 先建立真能抓住症状的失败循环，再最小化、假设、探针、修复、回归 |
| [resolving-merge-conflicts][merge-conflicts] | M | 追溯双方变更意图，逐块解决，运行检查并完成已有 merge/rebase |
| [wizard][wizard] | M | 仅供人才能完成的操作；生成有检查点的交互 shell 脚本 |
| [grill-me][grill-me] | U | 无持久化包装的 grilling 入口 |
| [handoff][handoff] | U | 将当前会话压缩为系统临时目录中的移交文档；既有产物只给指针 |
| [teach][teach] | U | 多会话学习工作区；mission、资源、学习记录、HTML 课程和参考资料 |
| [to-questionnaire][questionnaire] | U | 为一个外部知情人生成问卷；先问用户收件人及需要的答案 |
| [wait-what][wait-what] | U | 信息没有说清时，补足上下文并使用既有领域词汇重述 |
| [grilling][grilling] | M | 按依赖树逐轮问当前可问的完整 frontier；事实由代理查，决定由人作 |
| [writing-for-agents][writing] | M | 指针、按需披露、步骤完成条件和单一真源；技能写作公共纪律 |

| 非正式发布技能 | 状态 | 实际用途与纳入判断 |
|---|---|---|
| [git-guardrails-claude-code][guardrails] | misc / M | Claude PreToolUse Git 阻断 hook；非通用跨客户端权限制度 |
| [migrate-to-shoehorn][shoehorn] | misc / M | TypeScript 测试数据类型断言迁移；不应成为游戏项目通用步骤 |
| [scaffold-exercises][exercises] | misc / M | 作者课程练习目录及专用 linter；与游戏生产管理无直接关系 |
| [setup-pre-commit][precommit] | misc / M | Husky、lint-staged、Prettier 与测试 hook 安装；仅适用相应项目栈 |
| [claude-handoff][claude-handoff] | beta / U | `claude --bg` 专属后台移交；不直接移植为跨客户端能力 |
| [implement-spec][implement-spec] | beta / U | 多 worktree、依赖图并行实施、汇总到单个 PR；不是正式主流程默认执行器 |
| [loop-me][loop-me] | beta / U | 生活/工作 recurring workflow 访谈；不是游戏循环设计，也不是项目必需治理 |
| [retro][retro] | beta / U | 改善代理环境的复盘候选；README 仍称 STUB，但正文已含步骤，存在成熟度标注不一致 |
| [setup-ts-deep-modules][ts-deep] | beta / U | TypeScript 专属依赖边界配置；不可向 Unity/Unreal/Godot 普遍强加 |
| [writing-beats][writing-beats] | beta / U | 文章逐 beat 路径创作；非生产管理 |
| [writing-fragments][writing-fragments] | beta / U | 访谈并追加原始写作素材 |
| [writing-shape][writing-shape] | beta / U | 原始素材另写成文章，逐段讨论；与 fragments 职责分离 |

上游明确 beta 可以无预告改变或消失，未进入插件且没有正式文档页；因此本轮“沿用 Matt 流程”应以正式 25 项为基线。可以研究 beta 的方法，但不应悄悄把它们变成 MyGameStudio 的稳定必需依赖。[beta 声明][in-progress]

## 管理流程与关键制度

### 从模糊方向走到可实施工作

`ask-matt` 的主要路径是 `grill-with-docs` → 必要时原型 → 多会话时 `to-spec` → `to-tickets` → 每票新上下文 `implement`；小工作可直接在当前会话 `implement`。模糊到单会话装不下的工作从 `wayfinder` 入场，地图清晰后先综合为规格，再拆实施票。triage 是外来请求入口，`to-tickets` 自产票已 ready，不再重复 triage。它是带分支的推荐路径，不是所有技能强制串联。[路由正文 13–46][ask-matt]

Wayfinder 的决策票与实施票必须分开：前者问“选什么/需要先知道什么”，后者定义“做成什么”。地图仅是低分辨率索引，细节只在票中。可明确表述的问题即使受阻也应出票；尚不能说清的问题留在 `Not yet specified`；超出目的地的内容独立列 `Out of scope`。先建立票身份，再连依赖；先认领再做；只取 open、unblocked、unclaimed frontier。HITL 票必须有人参与，代理不能代替人作答。一会话最多解决一个非研究票；初次 chart 只建图及并行研究，不顺势完成决定和开发。[Wayfinder 19–128][wayfinder]

用户指定的 `/Users/cuilei/.mirasim/skills/wayfinder/SKILL.md` 与固定上游正文 **逐字节一致**，本轮执行 `diff -u` 退出 0。仓库当前 `docs/agents/issue-tracker.md` 与上游 local tracker seed 都用 `Status: claimed/resolved`、`Blocked by` 和 `## Answer` 承载 Wayfinding 操作。仓库对普通实施票另有 `Progress` 与 triage `Status` 分离说明；不应把一般 issue 的 triage 状态覆盖为 wayfinder 状态。[上游 local tracker seed][local-tracker]

### 人的决定与代理的调查分工

Grilling 每轮只问依赖已解决的问题，给推荐答案，再等人答；依赖同轮另一个答案的问题移到后续轮。事实可自主查则不向人追问；调查可以并行，只有受其影响的决定等待。`to-spec` 不重新访谈已经讨论过的内容，但要检查测试接口；`to-tickets` 必须让人确认切片粒度和真实阻塞关系。[grilling 6–28][grilling] [规格 7–19][to-spec] [拆票 42–67][to-tickets]

Invocation 是真正的组成约束：U 技能只有人能选，任何其他技能都不得自行调用；共享纪律放在 M 技能里，由 U 调用。路由器只能提示人选择，不能接管这些入口。因此，一个 `game-studio` 自动顺序调用 `wayfinder/to-spec/to-tickets/implement` 的超级编排器会改变上游制度，而不只是添加游戏专业内容。[Invocation 规则][invocation] [Skill mechanics][mechanics]

### 文档各自保存什么

- `CONTEXT.md` 仅是词汇表，不能变成 GDD、实现日志或规格仓库；按需读取，不必每票重写。
- ADR 只保存难逆、没有上下文就令人困惑、且确实权衡过替代方案的决定。不是每个数值、讨论答案和验收打勾都生成 ADR。
- Wayfinder 票保存决策及理由；map 保存一句摘要与链接；spec 综合已确定行为；实施票给独立验收条件。`triage` 的 Agent Brief 是该入口的实施契约，原始请求和讨论是上下文。
- 研究文件与原型保留可回溯来源；handoff 引用已有规格、票、commit、diff，避免重新复制真源。域词、架构纪律、流程步骤不要多处重复维护。[领域纪律 40–74][domain-modeling] [Agent Brief][agent-brief] [handoff][handoff] [writing 10–81][writing]

### 工程实现、检查与结束

规格先定义公共测试接口，优先已有、较高的接口。切票是每票都穿过所需层的可演示行为，单票能在新上下文中实施；不是分别开“数据层、UI 层、测试层”后到最后才见结果。大范围机械改动有明确例外：expand → 分批 migrate → contract；独立批不能保持检查通过时，可以统一集成分支并把最终检查明确落在 integrate-and-verify 票。这个例外值得复用，不能将“大改版”误套为全部先删除旧路径。[规格 13–17][to-spec] [拆票 25–40][to-tickets]

测试重心是可观察行为和独立预期值，不验证内部方法调用、镜像公式或同源快照。一次一个测试和最小实现；正文最新规则将 refactor 留到 review，虽然 README、description 仍有 red-green-refactor 称法。时间和随机性属于可控制的外部依赖；这恰适合游戏确定性逻辑，不能从中推导“体验也能由单元测试证明”。[TDD 12–38][tdd] [测试例子][tests] [mocking][mocking]

Standards 与 Spec 由两个独立子代理并行检查，彼此不能遮蔽。Standards 以仓库规范为准，固定 smell baseline 只是判断性启发，不得压过仓库标准；工具已强制检查的事不重复作人工评审。Spec 检查漏做、越界和实现错误；无来源就明确 skipped，不虚构通过。报告分别计数，不将两条轴混成总分。[评审 17–87][code-review]

调试必须有已运行、能抓住用户确切症状的失败循环，再最小化、提出可证伪假设、单变量探针和修复；性能先量基线。没有正确回归接口时，应承认这是架构限制，而不是为凑覆盖率写浅层测试。结束前重跑原始场景、移除临时探针并说明正确原因。[诊断 18–138][diagnosing-bugs]

## 分发、维护和移植约束

正式分发存在两种哲学：原生 Claude 插件是受管理的 bundle；skills.sh 提供可编辑文件，可按需更新。上游提醒不要同时装两份，避免同一技能重复出现。`.claude-plugin/plugin.json` 用显式目录列表发布 promoted 集；仓库 ADR 暂缓原生 Codex 插件，理由是其当时验证过的单路径选择与 symlink 缓存限制。这是**上游记录的当时平台结果**，本轮没有独立运行当前 Codex/Claude 安装矩阵，不能把历史 ADR 当今天平台的绝对结论。[安装说明][install] [分发 ADR][plugin-adr]

上游维护约束有实际价值：新增或改行为的 promoted 技能要同步 SKILL、bucket README、顶层 README、公开 docs 页、router 位置及 manifest；U/M 标志在 frontmatter 与 openai.yaml 同步。共享依赖通过技能名调用 M 技能，而非跨目录复制文档。版本由 Changesets 管理，脚本同步 package/manifest，release workflow 使用 npm ci、version PR 和 tag。当前仓库仅见这一份 workflow，不能声称上游已经建立全面的技能行为回归/多客户端 CI。[AGENTS][agents] [Invocation][invocation] [版本同步][version-sync] [Release workflow][release]

`scripts/link-skills.sh` 明确是作者本地开发脚本，不是支持的安装器；它纳入 beta，且可能删除目的地已存在的真实技能目录再改成 symlink。**只读研究，不运行或直接复用该安装脚本**。MyGameStudio 若采用受控组合分发，应独立设计可回溯、可验证的安装产物，不能让作者开发脚本代表用户安装合同。[开发脚本 4–6、18–24、50–59][link-script]

上游标注 MIT，源许可证注明 Copyright (c) 2026 Matt Pocock 及保留版权与许可声明的条件；这为复用/修改提供许可证依据。本报告未判断额外品牌、第三方工具或素材条款。若复制实质技能内容，应把上游声明和来源随复制部分保留；改版仍需明确“引用依赖”还是“受控派生”。[LICENSE][license]

建议候选：固定上游 SHA，记录采用技能集合、共享参考文件闭包、本地改动及理由、验证客户端。升级按 upstream diff → 本地偏差复核 → 路由/调用/契约场景回归 → 用户项目验收处理。不要把滚动 main 直接当已验收发行版；这个建议尚未成为本仓库发布制度。

## 不能盲目照搬的地方

1. **提交权限不是技能赋权。** `implement` 最后要求 commit；merge-conflicts 要 stage everything/commit；prototype 要捕获到分支。用户级分开的提交、推送和外部写入授权仍优先。应保留方法、适配结束动作，不能宣称运行技能即授权一切。[implement 7–15][implement] [merge 10–14][merge-conflicts] [prototype 19–26][prototype]
2. **评审对象存在接线缺口。** `implement` 在 commit 之前调用 review，而 review 正文固定 `git diff <base>...HEAD`，不会覆盖尚未提交的工作区改动。这个缺口来自正文组合的静态推断，尚未做真实执行复现。改版应显式约定评审实际产物、不可变标识，以及未提交、已提交和远端 PR 之间的证据关系，不能只照抄入口名就称闭环。[implement 13–15][implement] [review 17–23][code-review]
3. **不能把“review 后 commit”写成自动合并/发布。** 正式 `implement` 很短，不规定自动 PR、push、merge、发布和客户端验收；beta `implement-spec` 才描述整 spec 多 worktree 到 PR。MyGameStudio 的这些结果需要额外规范或用户决定。[implement][implement] [implement-spec][implement-spec]
4. **文件、身份和完成状态需要明确。** 本地 `.scratch` 约定是文本协议，不是数据库事务/并发锁；Wayfinder 的先认领是协作约定，不能宣称强互斥、并发写入安全或冲突自动恢复。若这些成为实际需求，再为存储协议补验证。[local tracker][local-tracker]
5. **上游内部也会漂移。** README 使用 red-green-refactor，而当前 TDD 正文明确把 refactoring 放到 review 阶段；ask-matt 当前已写成 one red-green slice，与 TDD 正文方向一致。优先引用负责该纪律的正文，同时把实际存在的差异列为升级核对点。[README 测试说明](https://github.com/mattpocock/skills/blob/3cca18b368ae95cdbdebbff572ccafa662551015/README.md#L150-L156) [ask-matt 26][ask-matt] [TDD 38][tdd]

## 给 MyGameStudio 的调整建议，待用户决定

以下是从上游职责边界推导的组合设计，不是上游已有游戏专业标准，也不是对 MyGameStudio 当前实现的定论。

| 需要保留的游戏专业内容 | 借用的 Matt 容器 | 应补充的专业问题/证据，不新增平行治理 |
|---|---|---|
| 目标玩家、体验愿景、核心循环与范围 | grilling、wayfinder、domain-modeling | 目标体验、玩家行动及反馈、循环边界、成功与失败条件；术语与完整 GDD 分开 |
| 玩法可行性与 fun 判断 | prototype、research、HITL 决策票 | 原型要验证哪个体验假设、观察什么、谁试玩、怎样据证据保留/调整/否决；运行成功不能替代好玩 |
| 规则、数值、经济与成长 | to-spec、tdd、可计算原型 | 状态转移、输入输出、单位/范围/约束、独立算例、时间/随机性假设、反例与恢复路径 |
| 美术、动画、音频、关卡及叙事内容 | 规格与实施票；专业 reference 按需加载 | 交付规格、工具来源、资产尺寸/命名/依赖、导入结果、风格一致性及人员验收；不能仅写生成提示词 |
| 游戏内纵向切片 | to-tickets | 一条可玩链路包括输入、规则、反馈、内容及所需测试；资产任务若单独存在，仍需说明它解锁哪个可验证切片 |
| 性能、设备与引擎可用性 | diagnosing-bugs、codebase-design、验收条件 | 目标设备和构建条件、帧时/内存/加载预算、测量口径、存档/生命周期/输入边界；阈值由项目决定 |
| 游戏测试与体验验收 | Standards/Spec 两轴 + 专门试玩证据 | 两轴审代码/契约；试玩观察与人类体验决定另存证据且关联构建，明确两类结果不互相代替 |
| 生产节奏、内容扩展和风险 | wayfinder 依赖图、to-tickets frontier | 阶段目标与退出条件、当前阻塞、内容依赖、预算/资源约束；阶段是否必须存在取决于项目规模 |
| 发行/平台/商业化/运行反馈 | 新问题时 research/grilling，既定行为写 spec | 目标渠道、测试环境、授权、数据和资产来源、上线/回退证据；正式 Matt 集未提供整套发行流程 |

优先可直接复用的是：frontier 与依赖、决策票/实施票区分、HITL/AFK 分工、单一真源、公共接口行为测试、两轴评审、第一方研究和临时 handoff。需要最小适配的是：中文术语、游戏案例、项目现有 tracker、客户端调用方式，以及用户的提交/外部写入边界。需要专业新增的是：体验假设、可玩原型、数值与内容规则、引擎和目标设备证据、试玩和发行验收。**不建议新增**另一套 game-triage、game-to-spec、game-ticket 状态机、重复审批台账、或在未明确规模前先建完整自动生产调度平台。

建议下一轮 Wayfinder 只锁定当前已清晰的决策问题：

1. “MyGameStudio 与 Matt 技能如何组合和分发”：外部依赖、固定版本复制，还是可审计的派生集；选择影响升级、重复安装、命名和许可携带。
2. “游戏专业流程补在哪里”：补充公共 discipline 的游戏参考，还是少量独立 model-invoked 专家技能；哪些人类入口仍由 Matt 持有。
3. “专业验收有哪些不可互代的证据”：自动规则正确、真实构建/设备运行、试玩体验、发布授权各自怎样与同一规格/版本关联。
4. “已有项目与旧产物如何继续用”：保留、迁移或收敛哪些接口和真源；先确认真实消费者，再拆机械迁移。

其余尚取决于这些决定的具体目录布局、命令命名、脚本实现、全部技能替换清单和发布日程，继续留在 fog，不现在预排成实施计划。

## 本轮验证与限制

- 已读取全部 37 份 `SKILL.md`；额外读取 invocation、router、phase boundaries、tracker seed、Agent Brief、TDD references、分发 ADR、manifest、版本脚本与 release workflow。
- 程序核对正式集合与 manifest 一致，25 个正式技能、14 U + 11 M；37 个技能的 openai.yaml 存在且 invocation 标志与正文一致。
- 指定本地 Wayfinder 与固定上游逐字节相同。未更改用户已安装技能、共享分支或上游 clone；只产出此研究文档。
- 未安装插件、运行技能端到端或执行上游发布/开发脚本；客户端能力与真实游戏验收仍需后续专项验证。
- 本文使用当前上游和当前仓库 tracker，不依赖历史记忆断言当前状态；网页 README 只用来核对入口，正文细节以固定 SHA 源文件为准。

## 固定版本来源

[tree]: https://github.com/mattpocock/skills/tree/3cca18b368ae95cdbdebbff572ccafa662551015
[agents]: https://github.com/mattpocock/skills/blob/3cca18b368ae95cdbdebbff572ccafa662551015/AGENTS.md#L1-L25
[manifest]: https://github.com/mattpocock/skills/blob/3cca18b368ae95cdbdebbff572ccafa662551015/.claude-plugin/plugin.json#L1-L48
[ask-matt]: https://github.com/mattpocock/skills/blob/3cca18b368ae95cdbdebbff572ccafa662551015/skills/engineering/ask-matt/SKILL.md#L1-L90
[setup]: https://github.com/mattpocock/skills/blob/3cca18b368ae95cdbdebbff572ccafa662551015/skills/engineering/setup-matt-pocock-skills/SKILL.md#L1-L116
[grill-with-docs]: https://github.com/mattpocock/skills/blob/3cca18b368ae95cdbdebbff572ccafa662551015/skills/engineering/grill-with-docs/SKILL.md#L1-L7
[wayfinder]: https://github.com/mattpocock/skills/blob/3cca18b368ae95cdbdebbff572ccafa662551015/skills/engineering/wayfinder/SKILL.md#L1-L128
[to-spec]: https://github.com/mattpocock/skills/blob/3cca18b368ae95cdbdebbff572ccafa662551015/skills/engineering/to-spec/SKILL.md#L1-L75
[to-tickets]: https://github.com/mattpocock/skills/blob/3cca18b368ae95cdbdebbff572ccafa662551015/skills/engineering/to-tickets/SKILL.md#L1-L105
[implement]: https://github.com/mattpocock/skills/blob/3cca18b368ae95cdbdebbff572ccafa662551015/skills/engineering/implement/SKILL.md#L1-L15
[triage]: https://github.com/mattpocock/skills/blob/3cca18b368ae95cdbdebbff572ccafa662551015/skills/engineering/triage/SKILL.md#L1-L112
[architecture]: https://github.com/mattpocock/skills/blob/3cca18b368ae95cdbdebbff572ccafa662551015/skills/engineering/improve-codebase-architecture/SKILL.md#L1-L71
[codebase-design]: https://github.com/mattpocock/skills/blob/3cca18b368ae95cdbdebbff572ccafa662551015/skills/engineering/codebase-design/SKILL.md#L1-L114
[domain-modeling]: https://github.com/mattpocock/skills/blob/3cca18b368ae95cdbdebbff572ccafa662551015/skills/engineering/domain-modeling/SKILL.md#L1-L74
[research]: https://github.com/mattpocock/skills/blob/3cca18b368ae95cdbdebbff572ccafa662551015/skills/engineering/research/SKILL.md#L1-L12
[prototype]: https://github.com/mattpocock/skills/blob/3cca18b368ae95cdbdebbff572ccafa662551015/skills/engineering/prototype/SKILL.md#L1-L26
[tdd]: https://github.com/mattpocock/skills/blob/3cca18b368ae95cdbdebbff572ccafa662551015/skills/engineering/tdd/SKILL.md#L1-L38
[code-review]: https://github.com/mattpocock/skills/blob/3cca18b368ae95cdbdebbff572ccafa662551015/skills/engineering/code-review/SKILL.md#L1-L87
[diagnosing-bugs]: https://github.com/mattpocock/skills/blob/3cca18b368ae95cdbdebbff572ccafa662551015/skills/engineering/diagnosing-bugs/SKILL.md#L1-L138
[merge-conflicts]: https://github.com/mattpocock/skills/blob/3cca18b368ae95cdbdebbff572ccafa662551015/skills/engineering/resolving-merge-conflicts/SKILL.md#L1-L14
[wizard]: https://github.com/mattpocock/skills/blob/3cca18b368ae95cdbdebbff572ccafa662551015/skills/engineering/wizard/SKILL.md#L1-L44
[grill-me]: https://github.com/mattpocock/skills/blob/3cca18b368ae95cdbdebbff572ccafa662551015/skills/productivity/grill-me/SKILL.md#L1-L7
[handoff]: https://github.com/mattpocock/skills/blob/3cca18b368ae95cdbdebbff572ccafa662551015/skills/productivity/handoff/SKILL.md#L1-L16
[teach]: https://github.com/mattpocock/skills/blob/3cca18b368ae95cdbdebbff572ccafa662551015/skills/productivity/teach/SKILL.md#L1-L140
[questionnaire]: https://github.com/mattpocock/skills/blob/3cca18b368ae95cdbdebbff572ccafa662551015/skills/productivity/to-questionnaire/SKILL.md#L1-L54
[wait-what]: https://github.com/mattpocock/skills/blob/3cca18b368ae95cdbdebbff572ccafa662551015/skills/productivity/wait-what/SKILL.md#L1-L7
[grilling]: https://github.com/mattpocock/skills/blob/3cca18b368ae95cdbdebbff572ccafa662551015/skills/productivity/grilling/SKILL.md#L1-L28
[writing]: https://github.com/mattpocock/skills/blob/3cca18b368ae95cdbdebbff572ccafa662551015/skills/productivity/writing-for-agents/SKILL.md#L1-L81
[guardrails]: https://github.com/mattpocock/skills/blob/3cca18b368ae95cdbdebbff572ccafa662551015/skills/misc/git-guardrails-claude-code/SKILL.md#L1-L95
[shoehorn]: https://github.com/mattpocock/skills/blob/3cca18b368ae95cdbdebbff572ccafa662551015/skills/misc/migrate-to-shoehorn/SKILL.md#L1-L118
[exercises]: https://github.com/mattpocock/skills/blob/3cca18b368ae95cdbdebbff572ccafa662551015/skills/misc/scaffold-exercises/SKILL.md#L1-L106
[precommit]: https://github.com/mattpocock/skills/blob/3cca18b368ae95cdbdebbff572ccafa662551015/skills/misc/setup-pre-commit/SKILL.md#L1-L91
[claude-handoff]: https://github.com/mattpocock/skills/blob/3cca18b368ae95cdbdebbff572ccafa662551015/skills/in-progress/claude-handoff/SKILL.md#L1-L18
[implement-spec]: https://github.com/mattpocock/skills/blob/3cca18b368ae95cdbdebbff572ccafa662551015/skills/in-progress/implement-spec/SKILL.md#L1-L35
[loop-me]: https://github.com/mattpocock/skills/blob/3cca18b368ae95cdbdebbff572ccafa662551015/skills/in-progress/loop-me/SKILL.md#L1-L32
[retro]: https://github.com/mattpocock/skills/blob/3cca18b368ae95cdbdebbff572ccafa662551015/skills/in-progress/retro/SKILL.md#L1-L44
[ts-deep]: https://github.com/mattpocock/skills/blob/3cca18b368ae95cdbdebbff572ccafa662551015/skills/in-progress/setup-ts-deep-modules/SKILL.md#L1-L102
[writing-beats]: https://github.com/mattpocock/skills/blob/3cca18b368ae95cdbdebbff572ccafa662551015/skills/in-progress/writing-beats/SKILL.md#L1-L67
[writing-fragments]: https://github.com/mattpocock/skills/blob/3cca18b368ae95cdbdebbff572ccafa662551015/skills/in-progress/writing-fragments/SKILL.md#L1-L79
[writing-shape]: https://github.com/mattpocock/skills/blob/3cca18b368ae95cdbdebbff572ccafa662551015/skills/in-progress/writing-shape/SKILL.md#L1-L79
[in-progress]: https://github.com/mattpocock/skills/blob/3cca18b368ae95cdbdebbff572ccafa662551015/skills/in-progress/README.md#L1-L18
[local-tracker]: https://github.com/mattpocock/skills/blob/3cca18b368ae95cdbdebbff572ccafa662551015/skills/engineering/setup-matt-pocock-skills/issue-tracker-local.md#L1-L30
[invocation]: https://github.com/mattpocock/skills/blob/3cca18b368ae95cdbdebbff572ccafa662551015/.agents/invocation.md#L1-L26
[mechanics]: https://github.com/mattpocock/skills/blob/3cca18b368ae95cdbdebbff572ccafa662551015/skills/productivity/writing-for-agents/SKILL-MECHANICS.md#L1-L22
[agent-brief]: https://github.com/mattpocock/skills/blob/3cca18b368ae95cdbdebbff572ccafa662551015/skills/engineering/triage/AGENT-BRIEF.md#L1-L207
[tests]: https://github.com/mattpocock/skills/blob/3cca18b368ae95cdbdebbff572ccafa662551015/skills/engineering/tdd/tests.md#L1-L77
[mocking]: https://github.com/mattpocock/skills/blob/3cca18b368ae95cdbdebbff572ccafa662551015/skills/engineering/tdd/mocking.md#L1-L59
[install]: https://github.com/mattpocock/skills/blob/3cca18b368ae95cdbdebbff572ccafa662551015/.agents/install-block.md#L1-L61
[plugin-adr]: https://github.com/mattpocock/skills/blob/3cca18b368ae95cdbdebbff572ccafa662551015/.agents/adr/0002-ship-as-a-claude-code-plugin.md#L1-L41
[version-sync]: https://github.com/mattpocock/skills/blob/3cca18b368ae95cdbdebbff572ccafa662551015/scripts/sync-plugin-version.mjs#L1-L41
[release]: https://github.com/mattpocock/skills/blob/3cca18b368ae95cdbdebbff572ccafa662551015/.github/workflows/release.yml#L1-L37
[link-script]: https://github.com/mattpocock/skills/blob/3cca18b368ae95cdbdebbff572ccafa662551015/scripts/link-skills.sh#L1-L62
[license]: https://github.com/mattpocock/skills/blob/3cca18b368ae95cdbdebbff572ccafa662551015/LICENSE#L1-L21

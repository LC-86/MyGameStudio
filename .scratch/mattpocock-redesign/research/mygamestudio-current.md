# MyGameStudio 当前实现深度分析

日期：2026-09-15。固定源码基线：`268e2fa6fd535482c3567c8b58f124aa09d93f94`。范围：本仓库的产品源文件、模板、打包及测试入口；不是正式 Standards / Spec 审查，也不是本版本宿主验收。

结论：现有 MyGameStudio 同时实现了游戏专业约定、通用流程编排、独立任务账本和受控写入运行系统。按用户已选的“保留 Matt 原技能，增加游戏专业扩展”方向，宜保留专业内容及证据纪律，把重复的流程权威逐步交还 Matt。不能据此一次删除全部 `game-*`、现有数据或运行保障。

## 1. 现状事实与规模

本轮先读取 `CONTEXT.md`、`docs/agents/domain.md`、README 与 provenance；当前受版本控制的 `docs/adr/` 为空。术语将制作统筹定义为协调角色，方案设计与制作实现承担不同成果责任；验证原型明确不等于正式实现。[S1]

计数取 `git ls-files` 的受版本控制文件，Python 行数为文件 `splitlines()` 物理行数，包含注释和空行；目录存在包含关系，不能累加所有行。缓存、临时目录与未跟踪文件不计入。

| 区域 | 文件数 | Python 文件 / 物理行 | 意义 |
| --- | ---: | ---: | --- |
| `plugin/` 总包 | 120 | 46 / 14,817 | 当前实际交付内容 |
| `plugin/skills/` | 58 | 29 / 9,162 | 14 公共入口；Python 全部位于 Game-Design |
| `plugin/skills/game-design/` | 31 | 29 / 9,162 | 设计问答、保存、同步、变更与检查软件 |
| `plugin/internal/` | 26 | 0 | 8 合同、2 提案、1 协议、6 内置通用方法及附属文件 |
| `plugin/records/` | 11 | 11 / 3,751 | 自有任务与基线读取、GitHub 适配 |
| `plugin/runtime/` | 6 | 6 / 1,904 | MCP、权限事务、调度 CLI |
| `plugin/templates/` | 14 | 0 | 含 README；其余13个项目/任务/记录/证据模板 |
| `tests/` | 63 | 62 / 23,806 | 既有聚合回归、设计问答回归与支持代码 |
| `acceptance/` | 979 | 27 / 3,829 | 18 编号场景目录及 `_shared`；大量历史证据 |
| `samples/` | 70 | 0 | 8 样例/边界夹具目录及 README |

14 个公共 SKILL 合计 1,072 行；6 个内部方法 SKILL 合计 330 行。源码声明版本 `1.0.0`，清单仅注册 `./skills/`，MCP 指向 `./.mcp.json`，公共入口的 YAML 禁止隐式调用（以Game-Design配置为例）。[S2][S37]

本轮完成的只读验证：120 条 `dist/package-manifest.txt` 哈希与当前 `plugin/` 一致；`dist/mygamestudio-1.0.0.tar.gz` 中120个普通文件与工作区对应文件逐字节一致。没有重建包、没有执行行为回归、模型调用或真实客户端验收；这只证明当前包内容一致。

## 2. 全部公共入口与专业落点

| 入口 | 当前主要职责和交付 | 改版候选方向 |
| --- | --- | --- |
| Game-Status | 只读查入口、任务与证据，分开完成/待验收/未知；固定 INDEX 起点。[S3] | 保留“证据核对”的游戏扩展；状态查询归统一 tracker |
| Game-Producer | 项目统筹、按请求选环节、委派、目标变化影响、并发与恢复；只写管理资料。[S4] | 改为游戏制作决策及跨专业协调，不再成为所有通用管理动作的必经总入口 |
| Game-Init | 新旧项目接入、六类事实分析、复用及迁移清单、文档与运行保障分别就绪。[S5] | 保留游戏项目探查；与 Matt setup 的 tracker/domain 配置整合 |
| Game-Plan | 已采纳规格拆原子任务、真实依赖、Agent/Human分工、窄可玩路径和资源任务。[S6] | 把游戏完成标准、资产依赖、集成责任补入 Matt 规划输出 |
| Game-Design | 设计讨论、覆盖地图、模块规格、变更和删减影响；29个Python模块。[S7] | 保留游戏专业框架；通用地图/问答/持久化机制逐项重整 |
| Game-Spec | 已采纳决定进入当前产品基线，版本、双指纹、采纳依据、未实现标注。[S8] | 保留可执行游戏规格质量要求；明确与 Matt PRD/spec 的唯一权威关系 |
| Game-Prototype | 为明确不确定性做隔离原型，真实运行；观察、判断、未验证、人反馈分开。[S9] | 沿 Matt prototype，补游戏试验目标、参数、试玩及正式集成纪律 |
| Game-Implement | 组织单任务专业工作、技术设计、集成与验证，不接管总体排期。[S10] | 沿 Matt 执行机制，保留游戏跨专业集成职责 |
| Game-Code | 代码与技术设计、命名参数、基于实际引擎配置的行为检查。[S11] | 通用实现复用 Matt；引擎/平台专业要求按项目加载 |
| Game-Art | 实际图像/模型/动画/VFX资源，格式、预览、来源、接入和审美待验收。[S12] | 专业扩展重点保留并补强，不能只改名或合入通用代码任务 |
| Game-Audio | 实际音频、规格、试听/接入、来源、听感待验收。[S13] | 专业扩展重点保留，增补触发、混音和集成质量要求 |
| Game-Build | 从项目配置构建，源与产物版本对应，入口实际启动，发布另行授权。[S14] | 保留游戏构建/分发准备，具体引擎与目标平台另选适配 |
| Game-Review | 独立版本固定、Standards/Spec两轴；设计资源也有专业标准轴。[S15] | 复用 Matt review 的通用部分，保留资源/设计审查和工作区版本范围 |
| Game-Playtest | 明确版本、场景、实际执行、真实人反馈；不把计划或无头输出当手感验收。[S16] | 必须保留游戏专业能力，并增强体验实验设计 |

上述“职责已写清”不等于对应工具链已接通。除 Game-Design 外，其余13个入口没有各自专用执行Python；它们是明确步骤、证据和边界的指令入口，通过宿主和项目实际工具完成制作。[S2][S7]

## 3. 专业内容真正落在什么地方

### 已有可保留的专业资产

**设计覆盖与规格。** `coverage_map.py` 的12领域包含核心吸引力、玩法决策、完整经历、系统、成长资源、内容叙事、交互引导、视听、商业化发布、技术数据、版本验收。`spec_render.py` 的9类模块规格把目的、对象、触发、规则、边界、数值、反馈、持续性、验收落到可检查结构；数值要求单位、范围、计算、取整、依据，体验验收需要实际方法。这比通用PRD多出的游戏领域约束值得保留。[S17][S18]

**玩家经历与经济一致性。** `journey.py` 建立首次进入→理解目标→操作→选择→结果→结束→重进，并检查资源耗尽、重复、退出、解锁、恢复。其自动矛盾检出实际只比较两类输入：解锁需求超过资源可获得总量、同一资源/目标出现不一致解锁数量。输入是调用方提供的结构化字典；不是自动理解任意GDD，更不是完整经济平衡、长期留存或乐趣验证。[S19]

**已有游戏变更与删减。** `change_impact.py` 沿提供的依赖追踪并区分必须同步、需取舍、不受影响；按“只有设计 / 已开发未发布 / 已发布”查规则、工程、数据、存档、进度、权益。`removal_impact.py` 把原功能作用分别取消、转移、简化保留，追踪奖励、引导、解锁、入口、内容、数据和验收残留。这些是贴近实际游戏生产的内容，适合作为通用变更流程的专业补充。[S20][S21]

**资源和试玩交付纪律。** 实际文件、可看/可播、规格、来源、接入点、集成责任及人工待验收是完整资产交付要求。Game-Playtest要求记录版本、输入、观察、证据、实际人反馈与复测触发。应保留“资源可解码”和“声音/画面适合游戏”、“运行正确”和“玩起来达到体验目标”的分开判断。[S12][S13][S16]

### 已有形式但深度仍有限

- 12领域是查漏分类，不是每个领域都有专用专业方法。`coverage_map.build_map` 整理调用方的 `domains/known/experience`；`stage_status` 对比调用方 `required` 与 `met`，不独立验证成果真实性。[S17]
- 9类规格的实现能检出缺字段、无不适用理由、特定模糊词及数值/验收缺项；它不能靠结构完整就证明机制自洽、有趣或可制作。`full_design` 再聚合覆盖/旅程/模块/范围/规则缺口，但事实提取与专业判断仍由Agent及人承担。[S18][S22]
- GAME_DESIGN模板仅27行、TECH_DESIGN模板22行，要求按需补数值、关卡、叙事、交互和视听；“留了位置”不等于具有数值系统、关卡设计、叙事管线、艺术指导、音频设计、性能预算、发布运营的完整专业工作法。[S23][S24]
- Game-Art把图像/模型/动画/特效放在一个任务入口，Game-Audio把音效/音乐/语音放在一个入口；其重点是成果真实性和规格检查。没有随包专门的角色风格一致性、动画状态/事件、关卡节奏、镜头/手感、混音空间、内容产能、设备性能矩阵或上线运营方法目录。此为对当前全包文件清单及专业步骤的范围判断，不代表每个游戏都应新增这些系统。[S12][S13][S16]

## 4. Producer / Design / Spec / Plan 如何耦合

当前推荐链为：制作统筹选环节 → Game-Design讨论并保存采纳决定 → Game-Spec更新产品基线 → Game-Plan拆任务 → Game-Implement组织制作 → Review/Playtest提供独立证据 → Producer更新任务状态。它允许跳过原型、从已有规格开始、单项小工作短流程；不要求每轮走满管线，也明确没有企业式固定立项阶段。[S4]

但落盘权威分成多个位置：

| 问题 | 当前权威/维护方式 |
| --- | --- |
| 项目目标、排期、任务状态 | Producer及管理角色 |
| 讨论、候选、采纳、替代历史 | Game-Design模块决定记录 |
| 当前有效产品规则 | Game-Spec维护GAME_DESIGN或引用模块规格 |
| 技术设计、工程与资产 | Implement及制作专业入口 |
| 验证事实 | 专业结果 `results/` 和独立证据 `evidence/` |
| 实际可写范围 | GateService绑定和策略，不是上述文档或Skill名 |

Game-Design当前又通过 `spec_draft` 组织模块规格、基线引用版本和术语同步；Game-Spec步骤0接收这些草稿并避免再整理。其说明一处说本入口不写产品基线，另一处允许“Game-Spec或等效明确文档步骤”同步。它不是可直接判为错误的双写实现，但边界需要在改版时重新命名清楚：到底谁把采纳决定转成最终权威规格，谁只是引用/验证。保留Matt原技能时不能再增加第三个同义spec流程。[S7][S8]

实际状态不是一条“完成”字段：决定区分已采纳/已保存/已同步/已实现/已验证；任务分流是5标签，进度是待执行/执行中/待验收/已完成；验证又绑具体版本。保留这些语义很有价值，但是否还需要全部自有存储和手工同步，必须单独决定。[S7][S25]

`mgs_records.startable_tasks` 根据任务字段、进度、依赖完成、基线版本、能力字符串判断开工条件；`baseline_report` 用双指纹区分仅空白与字符变化。它们核对的是记录层条件，并不会从工程自动证明依赖真的交付或体验通过。指纹也只能提示变化，专业影响仍需判断。[S26]

## 5. 内置Matt方法、任务后端和运行系统的重叠

包内固定了6个通用方法：grill-with-docs、grilling、domain-modeling、wayfinder、research、writing-for-agents。前五个来自当时本机副本；provenance明确没有为它们重复做上游提交级核对，writing-for-agents有固定上游提交。它们不注册公共入口，而由Game-Design等通过内部路径读取；CONFIG又重新解释其默认文档、tracker与研究分支落点。[S27]

**已有wayfinder并未完整保留原生管理模型。** 包内wayfinder要求：地图是索引、单独子工单、先认领、原生阻塞、通过查询取得前沿、结案记录答案、每次最多一个非research工单。Game-Design外层却将地图和工单写为设计过程记录 `records/decision-map-主题.md`，并只列“质询/研究”类型，没有在该外层步骤明确建立同等的认领/结案/查询操作。改版需让原生wayfinder直接管理地图，游戏扩展补充“应该调查或决定什么”，不能继续维护两个地图权威。[S28][S7]

**MGS有完整自有任务账本。** `records/`统一解析本地Markdown及GitHub正文，支持离线缓存、草稿重放、迁移、结果追加、身份防重复、版本检查。当前GitHub `set_relations` 实际更新正文“依赖”字段；`set_parent`才探测原生sub-issues。因而“原生父子关系可用”不能推成“原生阻塞可用”；直接沿Matt tracker管理更符合已选方向，但现有MGS任务身份、历史结果和基线引用必须迁移或兼容，不能丢弃。[S29]

**mgs-gate是技术授权系统，不是游戏生产阶段门。** 会话在项目外写草稿，所有项目文件通过MCP完整内容写入；角色∩任务∩用途∩授权、令牌生命周期、资源占用、版本冲突、路径安全、审计和事务回滚由服务实现。运行根和策略要由受信任调度侧建立，插件业务实例不能自己授予权限。它有独立价值，但不应被误称为“已验证玩法/美术/版本可以进入下一阶段”。[S30][S31][S38]

这套强保障依赖指定沙箱画像与宿主部署。协议针对历史codex 0.151.0说明：禁网会话 + 沙箱外MCP；放开会话网络时继承凭据可能直连，GUI/外部工具不自动继承保障。当前会话自身是无沙箱环境，不能把包内历史协议当作本轮已经观测到的OS拒绝事实；本轮没有执行探针或部署验证。[S30]

**初步判断：** 保留原生Matt技能时，强制所有原生工具写入转成mgs-gate全文件载荷，会使“原生流程复用”再次变成深层适配项目。宜先决策运行保障是必备底座、可选模式还是独立组件；任何退役都以真实风险、已有项目依赖和替代保障为条件。本研究没有授权移除它。

## 6. 打包、测试与验收证据边界

`dist/build-package.sh` 从plugin生成120文件清单与tar，归一时间和owner并排除平台元数据；脚本明确依赖BSD/macOS工具，不声明跨平台。`verify-reproducible.sh` 从 `git archive HEAD` 临时副本重建并比对tar/manifest/SHA256SUMS。这个发布可复现约定值得保留。[S32][S43]

5套README聚合入口的AST静态计数确为41主题：package 16、records 6、github 9、runtime gate 8、runtime boundary 2。测试覆盖包/指纹/调用声明、真实本地文件事务、可控GitHub替身、并发/故障、MCP子进程与历史宿主事件回放；入口自己明确不能代替真实安装和模型行为验收。[S33][S39][S40][S41][S42]

8个 `test_design_discussion_*` 不在上述5套THEMES中，需单独运行。当前源码中顶层 `test_*` 定义数分别为change_flow 18、decisions 18、feature_removal 13、full_design 19、incremental_checks 17、metrics 15、rounds 25、spec_draft 28，共153。这里是定义数，不是本轮实跑通过数。历史总报告列116个属于旧快照，不能当当前计数。[S34]

历史统一问答验收报告已明确：结构化接缝测试不能代表自由文本语义抽取，真实宿主端到端链未完成；耗时基线不可比，所以效率未验证。当前README也保持“真实宿主交互与效率配对仍未验证”，并记录用户跳过本轮隔离验收、进入正常使用反馈的决定。本研究不覆盖这些限制，也不把旧版本0.18.0的137 PASS提升为1.0.0验收。[S35][S36]

## 7. 按已选方向的保留、改造与退役候选

### 建议保留

1. 游戏设计的12领域查漏、9类模块规格、玩家历程、变更/删减影响；保留内容和失败场景，具体算法/文件形式可重整。
2. 原型、正式制作、独立检查、真实体验反馈之间的证据区分；源/产物/反馈绑定实际版本。
3. 视觉、声音、构建、试玩的专业交付责任；实际产物、规格、来源、接入、集成责任、人工待验收。
4. 可玩窄路径、资源任务、Agent制作与Human验收分开、真正依赖与并行集成协调。
5. 现有决定、规格、任务、结果和证据的身份与历史；迁移前保留读取。
6. 可复现打包、来源许可、针对真实行为的反例回归；历史验收继续标注其原版本与适用限制。

### 建议改造

1. 用Matt原生map/tracker承载决定工单与执行工单，游戏扩展只补专业问题、交付物和验收条款；一项决定/规则/任务状态有一个权威位置。
2. 将Producer/Plan/Implement中的通用调度职责交还原生技能流程，保留制作范围、内容依赖、版本决策和跨专业集成；入口名称是否保留另行设计。按上游调用制度，用户专用入口由用户选择，路由器不能自动串起这些入口；此处不建议自动编排整条原生技能链。
3. 把Game-Design的专业检查与固定问答排版、决定解析、Markdown同步、Gate通道拆开评估。9,162行不是都可删，也不是都必须保留；以真实行为资产而非既有文件数量划保留范围。
4. 将设计“可制作”、代码“检查通过”、资产“规格合格”、游戏“体验达到目标”、版本“可发布”各自定义最低证据；按实际项目阶段选择需要的门槛，不对每轮套全流程。
5. 对弱覆盖的关卡节奏、手感/相机、数值成长、内容产能、性能设备、发布与运营，只为目标游戏/当前版本增加适用的专业方法；不要求所有游戏新增商业化、长期运营或复杂存档。
6. 运行保障先决定产品边界与宿主支持，再设计与原生工具的接缝；无需每个原生技能复制角色/令牌/全文件写回说明。
7. 建立统一测试入口清单，包含设计行为及阶段证据；未来真实验收用同一场景证明“原生流程顺畅 + 游戏专业内容不丢”，效率需真实耗时测量。

### 有条件退役候选

- 包内冻结的Matt方法副本及同义通用包装：原生依赖、版本、许可、可发现性和升级策略落实后再退役。
- `records/`中与选定tracker重复的当前任务账本与一般CRUD：迁移、身份引用、历史访问和离线需要有明确方案后再退役。
- 强制固定Q排版、每次手工同步和多份同义状态报告：若原生流程已满足用户理解/恢复/采纳证据需求，可简化；用户既有偏好不能因“照搬Matt”被悄悄删除。
- 自有双指纹与全文件通道：只有当替代方案能覆盖实际版本核对、并发、越权/误写风险时才是候选；保留原生技能的选择本身不授权删除安全措施。

这些是研究建议，尚未解决的决策包括扩展如何被原生技能发现、何种游戏专业产物必须具备、阶段证据责任、旧项目迁移和运行保障去向。制图应列这些决定问题，暂不拆正式实现任务，也不将建议写成用户已采纳决定。

## 来源索引

所有源码链接均指向本轮固定基线的本地读取位置；若之后修改文件导致行号漂移，用上述commit还原核对。主要区间：S4行24–44及76–113；S7行23–81、84–114、124–170；S8行26–39；S12–S16各入口步骤段；S17行24–36和60–121；S18行17–41、84–113、295起；S19行52–86；S20行25–137和152起；S21行30–155；S22行45–113和122–245；S26行384–463和484–589；S29行357–431；S30行5–31及50–79；S31行117–129及186–220；S35行7–9和89–120。计数及包哈希结果由本轮只读脚本实际计算，未引用历史报告数字作为当前状态。

[S1]: /Users/cuilei/MyOS/01_Projects/plugins/MyGameStudio/CONTEXT.md:1
[S2]: /Users/cuilei/MyOS/01_Projects/plugins/MyGameStudio/plugin/.codex-plugin/plugin.json:1
[S3]: /Users/cuilei/MyOS/01_Projects/plugins/MyGameStudio/plugin/skills/game-status/SKILL.md:26
[S4]: /Users/cuilei/MyOS/01_Projects/plugins/MyGameStudio/plugin/skills/game-producer/SKILL.md:25
[S5]: /Users/cuilei/MyOS/01_Projects/plugins/MyGameStudio/plugin/skills/game-init/SKILL.md:28
[S6]: /Users/cuilei/MyOS/01_Projects/plugins/MyGameStudio/plugin/skills/game-plan/SKILL.md:24
[S7]: /Users/cuilei/MyOS/01_Projects/plugins/MyGameStudio/plugin/skills/game-design/SKILL.md:23
[S8]: /Users/cuilei/MyOS/01_Projects/plugins/MyGameStudio/plugin/skills/game-spec/SKILL.md:26
[S9]: /Users/cuilei/MyOS/01_Projects/plugins/MyGameStudio/plugin/skills/game-prototype/SKILL.md:24
[S10]: /Users/cuilei/MyOS/01_Projects/plugins/MyGameStudio/plugin/skills/game-implement/SKILL.md:24
[S11]: /Users/cuilei/MyOS/01_Projects/plugins/MyGameStudio/plugin/skills/game-code/SKILL.md:24
[S12]: /Users/cuilei/MyOS/01_Projects/plugins/MyGameStudio/plugin/skills/game-art/SKILL.md:24
[S13]: /Users/cuilei/MyOS/01_Projects/plugins/MyGameStudio/plugin/skills/game-audio/SKILL.md:24
[S14]: /Users/cuilei/MyOS/01_Projects/plugins/MyGameStudio/plugin/skills/game-build/SKILL.md:24
[S15]: /Users/cuilei/MyOS/01_Projects/plugins/MyGameStudio/plugin/skills/game-review/SKILL.md:24
[S16]: /Users/cuilei/MyOS/01_Projects/plugins/MyGameStudio/plugin/skills/game-playtest/SKILL.md:24
[S17]: /Users/cuilei/MyOS/01_Projects/plugins/MyGameStudio/plugin/skills/game-design/coverage_map.py:24
[S18]: /Users/cuilei/MyOS/01_Projects/plugins/MyGameStudio/plugin/skills/game-design/spec_render.py:17
[S19]: /Users/cuilei/MyOS/01_Projects/plugins/MyGameStudio/plugin/skills/game-design/journey.py:52
[S20]: /Users/cuilei/MyOS/01_Projects/plugins/MyGameStudio/plugin/skills/game-design/change_impact.py:25
[S21]: /Users/cuilei/MyOS/01_Projects/plugins/MyGameStudio/plugin/skills/game-design/removal_impact.py:30
[S22]: /Users/cuilei/MyOS/01_Projects/plugins/MyGameStudio/plugin/skills/game-design/full_design.py:45
[S23]: /Users/cuilei/MyOS/01_Projects/plugins/MyGameStudio/plugin/templates/project/GAME_DESIGN.md:1
[S24]: /Users/cuilei/MyOS/01_Projects/plugins/MyGameStudio/plugin/templates/project/TECH_DESIGN.md:1
[S25]: /Users/cuilei/MyOS/01_Projects/plugins/MyGameStudio/plugin/internal/contracts/records.md:7
[S26]: /Users/cuilei/MyOS/01_Projects/plugins/MyGameStudio/plugin/records/mgs_records.py:384
[S27]: /Users/cuilei/MyOS/01_Projects/plugins/MyGameStudio/plugin/provenance/manifest.md:64
[S28]: /Users/cuilei/MyOS/01_Projects/plugins/MyGameStudio/plugin/internal/methods/wayfinder/SKILL.md:23
[S29]: /Users/cuilei/MyOS/01_Projects/plugins/MyGameStudio/plugin/records/mgs_github.py:357
[S30]: /Users/cuilei/MyOS/01_Projects/plugins/MyGameStudio/plugin/internal/protocols/gate-protocol.md:5
[S31]: /Users/cuilei/MyOS/01_Projects/plugins/MyGameStudio/plugin/runtime/mgs_runtime.py:117
[S32]: /Users/cuilei/MyOS/01_Projects/plugins/MyGameStudio/dist/build-package.sh:1
[S33]: /Users/cuilei/MyOS/01_Projects/plugins/MyGameStudio/tests/test_plugin_package.py:13
[S34]: /Users/cuilei/MyOS/01_Projects/plugins/MyGameStudio/.scratch/design-discussion-rounds/evidence/ACCEPTANCE-REPORT.md:31
[S35]: /Users/cuilei/MyOS/01_Projects/plugins/MyGameStudio/.scratch/design-discussion-rounds/evidence/ACCEPTANCE-REPORT.md:89
[S36]: /Users/cuilei/MyOS/01_Projects/plugins/MyGameStudio/README.md:22
[S37]: /Users/cuilei/MyOS/01_Projects/plugins/MyGameStudio/plugin/skills/game-design/agents/openai.yaml:1
[S38]: /Users/cuilei/MyOS/01_Projects/plugins/MyGameStudio/plugin/runtime/mgs_local_write.py:98
[S39]: /Users/cuilei/MyOS/01_Projects/plugins/MyGameStudio/tests/test_records_backend.py:27
[S40]: /Users/cuilei/MyOS/01_Projects/plugins/MyGameStudio/tests/test_github_backend.py:32
[S41]: /Users/cuilei/MyOS/01_Projects/plugins/MyGameStudio/tests/test_runtime_gate.py:33
[S42]: /Users/cuilei/MyOS/01_Projects/plugins/MyGameStudio/tests/test_runtime_boundaries.py:33
[S43]: /Users/cuilei/MyOS/01_Projects/plugins/MyGameStudio/dist/verify-reproducible.sh:6

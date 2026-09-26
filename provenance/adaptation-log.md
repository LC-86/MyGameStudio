# 原版到 V3 的适配记录

每项回答四个问题：原版怎样做、哪个已确认要求导致改变、实际改变了什么、可能损失什么以及用什么核对。上游基线见 [upstream.md](upstream.md)。

本文件记录适配决定，不重复技能正文。行为验证的实际结果见 [docs/validation-v3.md](../docs/validation-v3.md)。

## Issue #87 后续分发调整（2026-09-26，尚未发布）

本记录以下 A1–A5 描述原 V3 实施时的要求与结果，保留其历史身份。Issue #87 将当前技能集合扩为 21 项，并重新指定共享资料所有者：

- `writing-for-agents` 作为共同写作方法独立随包，固定源与逐文件摘要见 `skills/writing-for-agents/SOURCE.md`（该文件已随副本删除）；它拥有通用表达和技能机制。
- `docs-gamestudio` 收窄为游戏文档分流、增量协作和专属资料入口；其旧 `references/skill-authoring.md` 不再发行。A1 中对 `skill-authoring.md` 的引用指向已退役的 V3 材料，其维护契约现由仓库级 `AGENTS.md` 与 `docs/development/testing.md` 承载。
- 人机责任和指定人工验收交接继续由 `tasks-gamestudio` 拥有。现行消费者映射、安装范围、许可、双语说明和验证状态按本次 Issue #87 分别维护；本节不宣称其已发布。

## Issue #90 兼容接缝（2026-09-27，尚未发布）

Issue #90 是 expand 阶段：在保留 v3.0.2 的 21 项发行形态与随包副本的前提下，先建立稳定接缝，让后续收缩删除随包副本时不需要再改消费者。

- 语义保真与通用子代理委派从随包 `writing-for-agents` 交还 `docs-gamestudio`：新增 [`references/semantic-fidelity.md`](../skills/docs-gamestudio/references/semantic-fidelity.md)，恢复并扩展 [`references/delegation.md`](../skills/docs-gamestudio/references/delegation.md)。
- 17 项消费者改为按宿主支持的技能名称取得 `writing-for-agents`，不再使用 `../writing-for-agents/...` 跨安装范围相对路径；保真与委派分别指向 `docs-gamestudio` 的所有者资料。
- 随包副本继续按 #87 的固定源生成，内容与摘要未变；`SKILL-MECHANICS.md` 与上游 `references/subagent-delegation.md` 仍随副本分发，但不再是 GameStudio 委派方法的依据。
- 失去保真或委派依据的写法没有被静默接受：`tests/test_skills_layout.py` 增加所有者、消费者、缺外部方法处理与保真/委派契约的确定性检查，实际结果记入 [验证状态](../docs/validation-v3.md)。

## Issue #92 游戏设计与文档工作流迁移（2026-09-27，尚未发布）

Issue #92 在 #90 的接缝上迁移游戏设计与文档工作流组（`docs-gamestudio` 与 domain、gdd、spec、grilling、prototype、wayfinder 及其两个访谈入口），只改这一组的正文与检查，不动工程交付组消费者。

- 五个正式写作分支（domain、gdd、spec、prototype、wayfinder）在按技能名称取得 `writing-for-agents` 的同一句里补上缺方法处理：说明具体缺口和受影响的工作，只继续不依赖它的部分，不模仿缺失的方法。此前只有 `docs-gamestudio` 所有者正文写有该契约，单独调用某一个流程时读不到它。
- 各流程原有的启动、返回与停止边界逐条保留（访谈收束、回到原讨论、回到原问题集、返回原问答、原型交付为止、目的达到时交接、读完后返回原任务）；测试按名称逐项固化，防止后续迁移把这些边界当作可替换文本删掉。
- 讨论类入口不直接取得外部共同方法：`grill-gamestudio`、`grill-gamestudio-docs`、`grilling-gamestudio` 的正文不出现该方法名，落盘由它们在协作模式下按需使用的 `domain-gamestudio`、`gdd-gamestudio`、`spec-gamestudio` 取得。依赖表按这一实际行为更正，不再把它们写成直接使用。
- 组合安装检查在 `scripts/install-smoke-test.sh` 第 10 节：本票组加两项同源依赖从本仓库安装，外部共同方法单独从官方 `mattpocock/skills` 安装，核对锁来源、无随包副本打包文件、引用可达与取得方式。夹具脚本 `scripts/behavior-fixtures.sh` 增加 `METHOD_SOURCE=official`（两来源形态）与 `NOMETHOD-` 场景前缀（故意缺外部方法）。
- 行为与产物结果见 [Issue #92 验证证据](../docs/evidence/issue-92-behavior-matrix.md)与 [验证状态](../docs/validation-v3.md)。

## Issue #91 工程交付与协作工作流迁移（2026-09-27，尚未发布）

Issue #91 在 #90 的接缝与 #92 的分组做法上迁移工程交付与协作工作流组（ask、codebase、debug、handoff、implement、merge、research、review、setup、tasks、tdd），只改这一组的正文与检查，不动游戏设计与文档组消费者。

- 11 个正式写作分支在按技能名称取得 `writing-for-agents` 的同一处补上缺方法处理（说明具体缺口和受影响的工作，只继续不依赖它的部分，不模仿缺失的方法）。此前该契约只在 `docs-gamestudio` 所有者正文与 #92 组的五个写作者里，单独调用工程交付流程时读不到它。
- 各流程原有的启动、返回与停止边界逐条保留（推荐完成后停止、返回原流程、返回证据与剩余责任、到交接说明交付为止、人工确认未完成不自动关单、不扩大到下一项工作、回到原讨论、返回发现与复查范围、交付并停止、到任务交付为止、返回使用它的任务）；测试按名称逐项固化，并核对两票的写作分支恰好覆盖全部 17 个消费者，不会因分组边界漏掉某一项。
- 资料读取、方法使用、实际委派与下一步推荐保持不同身份：推荐不执行下游工作，读到方法不等于已经用它，只有真实派发并回收结果才算委派。该边界连同缺方法处理一起按名称断言。
- 组合安装检查在 `scripts/install-smoke-test.sh` 第 11 节：工程交付组加引用闭包内的 7 项同源依赖（`docs-gamestudio` 与它分流参考指向的 domain、gdd、spec、grilling 及两个访谈入口）从本仓库安装，外部共同方法单独从官方 `mattpocock/skills` 安装，核对锁来源、无随包副本打包文件、引用可达与取得方式。只装 11 项不及物：`docs-gamestudio` 的分流参考会指向本组之外的技能。
- 第 10、11 节共用的组合校验抽成 `scripts/two-source-composition-check.py`：复制第二份时已经出现漂移（少了来源指纹提示与访谈入口反向断言），因此组名、同源依赖、正式写作分支、缺方法处理的所有者例外与反向断言都改为参数，判据只保留一份；`tests/test_maintenance_scripts.py` 守住「两节共用同一脚本」与「装不齐时必须报 FAIL」。
- 行为与产物结果见 [Issue #91 验证证据](../docs/evidence/issue-91-behavior-matrix.md)与 [验证状态](../docs/validation-v3.md)。缺方法行为在三个限定工程范围的场景里观察：两个报告了缺口并只继续不依赖的部分，一个完成了工作却没有报告缺口，该未达标项如实记录，不写成通过。

## Issue #93 随包共同方法副本退役（2026-09-27，3.0.3 未发布）

Issue #93 执行收缩：把 `writing-for-agents` 还原为纯外部依赖，删掉本仓库为它维护的副本与整条维护路径。以上 #86、#87、#90、#92、#91 的记录描述的是收缩前的形态，保留原身份，不改写。

- 删除随包目录 `skills/writing-for-agents/`（`SKILL.md`、`SKILL-MECHANICS.md`、`references/subagent-delegation.md`、`SOURCE.md`、`SHA256SUMS`、`LICENSE`）。可发现技能集合由 21 项（8 用户入口、13 按需方法）回到 20 项（8 用户入口、12 按需方法）。
- 删除 `scripts/sync-writing-for-agents.py`（固定源同步与摘要生成）、`scripts/verify-writing-for-agents-install.py`（已安装副本核验检查器）与 `scripts/install-source-matrix-test.sh`（来源切换矩阵）。本仓库不再提供来源切换，也不再为该方法保留第二份可编辑权威源。
- 用户取得方式改为从官方 `mattpocock/skills` 独立安装，按宿主支持的技能名称取得；安装说明改写为两个来源、用户级优先并提供项目级替代，已有官方共同方法时只跳过第一步。命令用 `skills@latest`，参数与锁文件行为只在 CLI 1.7.0 上核实，这条证据边界保留在安装资料里。
- 「从 LC-86 fork 切换来源」的整套说法退出：fork 提交 `f3c726f275fa1ac59fef33732e527dded6d62479` 与 #86 的分发记录作为上一版的历史事实保留，不再作为现行来源。旧 fork 只读 checkout 仍是 V3 方法基线 `c55ee46` 的读取路径，同样只作历史记录。
- 本版未打标签、未发布 Release；`v3.0.2` 标签与其 Release 资产、`v3.0.1` 标签的历史身份均不改写。
- `v3.0.2` 之前的静态断言的替代由本票改动的检查承担：`install-smoke-test.sh` 第 8 节用负例守住「本仓库不再分发 `writing-for-agents`」，文档检查守住 20 项集合与两来源安装口径。实际输出与未运行项见 [验证状态](../docs/validation-v3.md)。

## 跨技能的系统性适配

### A1. 宿主专属调用开关退出

**原版：** 用户专用技能在 frontmatter 写 `disable-model-invocation: true`，并在 `agents/openai.yaml` 写 `policy.allow_implicit_invocation: false`；两份声明需保持同步。宿主据此阻止模型自行触发。

**要求：** 本次只交付原生 Agent Skills 仓库，取消各 AI 开发工具的插件适配、专属元数据和发布流程；不靠调用开关实现通用边界，也不伪造标准字段。

**改变：** 删除全部 `disable-model-invocation` 与 `agents/openai.yaml`。8 个用户入口与 12 个按需方法改为写在 `description` 和正文里的行为边界：入口的描述说明它对应哪一类用户请求，正文说明启动条件和不做什么。`handoff-gamestudio` 的 `argument-hint` 一并删除，它是宿主的输入提示，不改变行为，且不属于本次确认的标准字段。

**损失：** 跨宿主的强制调用隔离能力。标准技能文本无法阻止某个宿主自行选中一个用户入口，也无法阻止某个 Agent 在未被请求时开启新阶段。

**核对：** 这一损失被如实披露而不是弥补——`docs-gamestudio/references/skill-authoring.md` 与 README 都说明 8/12 是指令层约定；场景 E01（Ask 只问下一步）、E07（不制造人工审批）与安装测试第 1 项检查发现集合与描述边界。

### A2. Docs 从窄写作技能扩大为共同写作方法

**原版：** `writing-for-agents` 是一份供 Agent 阅读的写作参考，适用范围是技能、`AGENTS.md` / `CLAUDE.md` 和指针触达的文档；宿主机制分支单独放在 `SKILL-MECHANICS.md`。它不覆盖游戏设计文档，也没有消费者接入。

**要求：** Docs 是所有正式工作资料与委派的共同写作方法，覆盖 GDD、spec、tickets、术语与决策资料、研究/测试/评审结论、交接说明、Skill 和项目规则，尤其是子代理委派说明；旧草案尚未接入，这项差距必须先补。

**改变：** `docs-gamestudio` 正文重写，保留原版的实际杠杆（上下文指针与触发不稳缺陷、上下文负载与认知负载、信息层级三级、按需披露、就近集中、冗长堆积、完成标准的明确度与要求度、提前完成、必要功课、引导词、否定失效模式、唯一权威来源、环境即权威来源与缓存、相关性与沉积、空指令），并补入语义保真校对（数字、单位、条件、例外、确认状态、责任）与各产出方的重点检查表。新增 `references/delegation.md`。`SKILL-MECHANICS.md` 中与宿主开关有关的部分退出，通用部分（按调用切分、路由技能、共享参考的归属）改写进 `references/skill-authoring.md`。

消费者接入：gdd、spec、tasks、domain、setup、handoff 在正式写作处取得方法；review、research、grilling、wayfinder 在真实委派点取得 `delegation.md`；implement、debug、tdd、prototype、codebase、merge 在形成结果记录时按语义保真要求表达；ask 只读使用方法写出可直接发送的指令；两个一句话入口不追加规则。

**损失：** 无。原版的宿主机制内容按 A1 退出，其损失记在 A1。

**核对：** 静态检查逐项确认消费者存在可追踪的真实入口（不是仅出现技能名字符串）；场景 E04（子代理只有委派材料）、E15（精简后语义不丢）、E13（部分写入失败分别报告）。

### A3. 共享资料单一所有者

**原版：** 需要被两个用户专用技能共用的参考，因为双方都没有可触发的描述，被推到技能系统之外的普通文件。同一份随包资料在多个技能目录里各存一份副本。

**要求：** 每项技能只有一份权威源码；共用资料放在明确的所有者技能内，完整安装后通过明确路径或已安装技能定位复用；不能假设安装会复制仓库根共享资料或自动解析技能间依赖。

**改变：** 文档分流与增量协作约定由 `gdd-gamestudio` 迁到 `docs-gamestudio/references/document-routing.md`（它是写作与组织方法，且被 8 项技能引用）；人机责任与验收交接约定留在 `tasks-gamestudio/references/task-responsibility.md`。消费者用同级技能相对路径引用，例如 `../docs-gamestudio/references/document-routing.md`。V2 中每个技能各带一份的共享文档副本全部取消。

**损失：** 选择安装时，缺少所有者技能就拿不到共享参考。

**核对：** `docs/dependencies.md` 给出必需依赖、按情境使用的方法与只读引用三类，并为选择安装给出包含依赖的实际命令；安装测试第 4 项验证子集安装与故意缺依赖的负例；静态检查确认所有相对引用可达且没有第二份权威正文。

### A4. 专用记录运行层退出

**原版（V2）：** `plugin/records/` 下 21 个 Python 模块提供 GitHub Issue 与本地 Markdown 任务记录的读写、后端同步、迁移、失败恢复、安全切换与可玩交付接缝；技能正文通过公开接缝调用。

**要求：** 旧记录写入、后端同步、恢复与迁移程序不再作为 V3 运行时；不建立运行时注册中心、自动补依赖安装器或扫描客户端缓存的回退程序；Node/Python/Shell 可以用于维护验证，不得重新成为游戏项目的常驻管理程序。

**改变：** 整个运行层退出有效安装范围。任务读写改为使用项目已有工具（现有 CLI、连接器或文件操作），由 `setup-gamestudio` 记录项目实际约定，`tasks-gamestudio` 按约定保存并回读。幂等恢复、跨后端一致性等旧保障不再由程序提供，改由行为要求承担：写入结果未知先回读、部分成功分别报告、不盲目重复创建。

**损失：** 程序级的一致性与恢复保障。这些能力没有被提示词等价替代。

**核对：** `docs/migration-v3.md` 逐项列出失去的保障与替代方式；场景 E13（一份写成一份失败）、E16（能力缺失时明确缺口）；旧模块从 Git 历史恢复，见 [v2-retirement.md](v2-retirement.md)。

### A5. 客户端插件适配与市场清单退出

**原版（V2）：** `.claude-plugin/`、`.codex-plugin/`、`.zcode-plugin/` 三份插件清单，`scripts/build-package.sh` 构建 tar 包，`dist/` 存放交付物与可复现构建核验，`docs/installation/` 六个文件分别教各客户端安装。

**要求：** 唯一标准技能源码布局为根目录 `skills/<技能名>/SKILL.md`，通过官方 `skills` CLI 安装；不需要发布 npm 包，也不需要自建安装命令。

**改变：** 全部退出。安装方式改为 `npx skills@latest add LC-86/MyGameStudio`，具体目标目录由官方 CLI 与使用者选择。版本权威来源从 `.codex-plugin/plugin.json` 改为根目录 `VERSION`。

**损失：** 不能再用 tar 包离线安装，也不再有 MyGameStudio 自建的客户端目录转换。

**核对：** `docs/installation.md`、隔离安装测试（[docs/validation-v3.md](../docs/validation-v3.md)）；静态检查确认仓库内不再有插件清单与专属元数据。

### A6. 调用措辞中性化

**原版：** 技能之间用 `Call the Skill tool with "<name>"` 表达依赖，假定宿主存在名为 `Skill` 的调用工具。

**要求：** 调用方式保持中性：有真实技能调用能力就使用；没有同名工具但方法文件可读取时，按已安装路径取得正文和必要参考并使用。读取、使用方法、创建子代理和推荐下一步是不同动作，报告不能混用。

**改变：** 正文改用中性动词，并给出指向同级技能 `SKILL.md` 的真实相对链接，例如「使用 tdd-gamestudio 的方法」中 tdd-gamestudio 是一个指向 `../tdd-gamestudio/SKILL.md` 的链接。两个一句话组合入口采用执行提示词给出的中性表达并附真实链接，仍各只有一句正文。读取、使用方法、委派、推荐四种动作在 `docs-gamestudio/references/skill-authoring.md` 与各消费者中分别表述。

**损失：** 无强制调用语义；宿主不提供调用能力时退化为读取方法文件后自行执行。

**核对：** 静态检查确认没有残留假定固定工具名的硬调用；场景 E04 与安装测试第 6 项（名称不被误指向旧方法）。

### A7. 用户入口调用控制恢复分层（#83 票面记作「A2」；对 A1 的部分反转）

**原版：** 上游在用户专用技能上写两份声明：frontmatter 的 `disable-model-invocation: true` 与 `agents/openai.yaml` 的 `policy.allow_implicit_invocation: false`，由宿主阻止模型自行触发。A1 让这套做法整体退出，8 个用户入口与 12 个按需方法的边界只留在 `description` 与正文里。

**要求：** 8 个用户入口升级为三层调用控制，使支持的宿主能真正阻止模型自行启动；标准 frontmatter 之外的宿主专属文件重新进入有效安装范围。`agents/openai.yaml` 的内容被限定为 `policy:` 与 `  allow_implicit_invocation: false` 两行；`argument-hint`、`allowed-tools` 与 frontmatter 内的 `allow_implicit_invocation` 仍然禁止。仓库对外口径同步改为三层机制。

**改变：** 8 个用户入口的 `SKILL.md` frontmatter 追加 `disable-model-invocation: true`，目录内各新增一份 `agents/openai.yaml`；description 措辞与 12 个按需方法均未改动。静态契约反转：`tests/test_skills_layout.py` 由 27 项断言增至 31 项，改为正向要求入口携带两层开关且值正确，保留反向断言（方法带开关或宿主文件即失败）；`scripts/validate-docs.py` 把该字段移出 `RETIRED_COMMANDS`。对外措辞按 #82 在同批 19 个改动文件中改为三层口径（含验证记录本身，逐文件清单见 [docs/validation-v3.md](../docs/validation-v3.md) 的「规则与文档口径对齐（#82）」）。

**损失：** A1 的损失对 ZCode、Qoder 仍然成立。新增两项损失面：**规则复杂度上升**——同一个 8/12 分界现在要同时用三层机制与 `description`、正文表述，跨宿主行为不再能用一句话理解，判断某个宿主是否强制还需先查它的解析行为，而这一层依赖宿主实现、本库在宿主之外无法验证；**每个用户入口多一个配置文件**——技能目录不再只由 `SKILL.md` 与按需参考构成，安装内容比 3.0.0 多出 8 个文件，`agents/` 目录本身成为契约的一部分。第一、二层是否生效只能在支持宿主内观察，宿主改变行为时需要重新核对官方文档。

**核对：** 六宿主判定规则与官方文档出处（本轮由独立子代理逐宿主核实，摘句为页面原文）：Claude Code 的 frontmatter 参考与「Control who invokes a skill」节（[code.claude.com/docs/en/skills](https://code.claude.com/docs/en/skills)）写「`disable-model-invocation: true`: Only you can invoke the skill」；Grok Build 的 SKILL.md 字段表（[docs.x.ai](https://docs.x.ai/build/features/skills-plugins-marketplaces)）写「`disable-model-invocation` | Slash command only; no automatic invoke. Default `false`」；DSH 的官方技能参考页与源码（[deepseek-harness](https://deepseek-harness.github.io/deepseek-harness/reference/subsystems/skills)）写「The local provider reads the exact kebab-case frontmatter keys `disable-model-invocation` and `user-invocable`」，`packages/skill/skill-filesystem` 据此把它映射为模型不可调用；Codex 的官方 Skills 文档（[developers.openai.com/codex/skills](https://developers.openai.com/codex/skills)）写 `agents/openai.yaml` 用于设置调用策略、「`allow_implicit_invocation` (default: `true`): When `false`, Codex won't implicitly invoke the skill」，而官方解析器只读 `name` / `description` / `metadata`，因此不读 `disable-model-invocation`；ZCode 的官方 Skill 页明确写「`/` 面板与模型看到的是同一份技能清单，不存在『只给面板、不给模型』的开关」，Plugin 页的字段白名单之外的键会被忽略；Qoder 的官方 Skills 文档只文档化 `name` / `description`，未找到调用控制字段（是「未找到」，不是官方否认）。**主流程对其中部分域名解析为非公网地址、未能直接打开页面，上述摘录来自本轮子代理检索；DSH 与 Codex 的结论另有官方仓库源码佐证。** 静态检查逐项确认 8 个入口携带两层开关且值正确、12 个方法目录内无 `agents/`（`tests/test_skills_layout.py` 31 项断言）；`scripts/validate-docs.py` 确认文档导航、链接与版本口径一致。**#81 轮的检查沿用，本轮未重跑：** 隔离安装测试 `19/19` 通过，但该脚本不断言 `agents/openai.yaml`，yaml 的安装结果来自脚本保留工作目录内的逐目录人工核对（8 份），**该核对的临时目录在 #81 轮核对后已删除，这条结论没有留存证据目录**。实际输出与证据边界见 [docs/validation-v3.md](../docs/validation-v3.md) 的「记录链闭环（#83）」。**未运行：六宿主内的实际调用隔离**，缺少可自动化的实测入口，原因见同一节。

## 逐项游戏化适配

以下适配在 V3 之前已由用户逐项确认，本次沿用并核对，不重新设计。

| 技能 | 相对原版的主要适配 | 可能损失 | 核对场景 |
|---|---|---|---|
| ask-gamestudio | 只给一个下一步与可直接发送的指令；不盘点全项目、不输出候选清单；不推荐导航技能继续选路 | 用户拿不到全景视图 | E01 |
| setup-gamestudio | 普通文档配置而非工作流运行时；复用已有约定，重复运行且无变化不改文件；补入游戏资料与资源管理约定；区分配置完成与工具可用 | 没有程序保证配置被遵守 | E02 |
| grilling-gamestudio | 领域知识是观察视角而非题库，读取后没有新问题也是正确结果；按前提分轮；事实由 Agent 查 | 不保证覆盖某类型的全部设计面 | E03 |
| domain-gamestudio | 只记离开对话后会被合理误解并影响后续工作的概念；数值与完整规则另有去处 | 词表不完整是有意结果 | E03 |
| grill-gamestudio / grill-gamestudio-docs | 各保留一句正文；Docs 依赖放在真正的产出方法里 | 宿主不支持组合调用时退化为逐个取得方法 | E03、E05 |
| gdd-gamestudio | 原创技能：维护现行整体设计；与 spec 互调只处理明确差异并返回；候选不升级为已采纳 | 与 spec 的边界依赖 Agent 判断 | E03、E13 |
| spec-gamestudio | 整理已知要求，不从实现反推；增量补齐同一份草稿；保存不等于可实施，可实施不等于已授权实施 | 无 | E03、E15 |
| tasks-gamestudio | 按完整小成果拆票，不按工种机械切碎；`ready-for-agent` / `ready-for-human` 表示下一执行段；独立资源与工程任务可单独成票 | 标签语义依赖项目实际映射 | E06、E07 |
| implement-gamestudio | 无提交授权时保留未提交成果，不无条件提交；评审发现交回实现者；人工项未完成不关单 | 失去原版的“总是提交”确定性 | E06、E07 |
| tdd-gamestudio | 允许绿灯后的必要局部整理（原版把重构完全排除在红绿循环之外）；接缝已约定就直接执行，不逐个测试请求确认（原版要求每个接缝都事先与用户确认）；环境启动失败不是目标行为的失败；已有正确行为的覆盖补充不人为制造红灯。保留原版的接缝词汇与三类反模式（耦合实现、同义反复、横向切片），并让「接缝」与 codebase-gamestudio 共用同一个词 | 失去原版「测试投入必须被显式商定」的保证；新增接缝或改变验收范围时仍需确认，但日常循环不再逐项询问 | E15；接缝确认放宽的行为影响未运行 |
| review-gamestudio | 两轴消费同一份完整待交付材料，含未提交、新建、删除与资源变化；不为取得版本标识强制提交；静态截图不证明交互，LFS 指针不证明源资产 | 无独立子代理时独立性条件未满足，只能披露 | E08 |
| debug-gamestudio | 不强制单条命令或固定假设数；无法复现时可继续分析有依据的材料，但结论强度随证据变化 | 失去原版的固定流程约束 | E15 |
| prototype-gamestudio | 玩法原型默认交付真正可玩的浏览器小游戏：真实输入驱动规则、状态与结果，SVG 或程序化美术，必要反馈与可重置；不是状态面板、静态图片或应用式仪表盘；关键三维、引擎与设备条件不得省去后仍宣称验证完成 | 浏览器优先不适合所有问题，需保留实际环境 | E09、E10 |
| research-gamestudio | 三种深度按问题选择，不是必走阶段；使用当前已有工具，不引入 pplx／Perplexity 专项收费 API，不默认安装研究服务；无后台能力不虚构后台 | 失去专项研究工具的检索质量 | E11、E12 |
| wayfinder-gamestudio | 整理跨会话决策问题而非生产排期；不新增类型标签或固定 token 配额；路线清楚即交接，不继续自动制作 | 无 | E16 |
| handoff-gamestudio | 保存位置服务接收方式，不一律写临时目录；引用不代表已传输；不自动搬迁工程或创建会话 | 无 | E18 |
| codebase-gamestudio | 服务当前职责、状态生命周期、接口与测试位置；不默认全库扫描；不强制 ECS、事件总线、双适配器或多子代理方案；删旧测试前核对有效覆盖 | 失去原版的“总是比较两个方案”约束 | E15 |
| merge-gamestudio | 只处理已发生的冲突；场景、资源身份与二进制采用适合的方法；不能可靠合并时保留版本并说明取舍；取消原版的两条硬性要求——「Always resolve; never `--abort`」与「Stage everything and commit」，改为无法可靠处理时保持未解决、只暂存本次应处理的路径、取消操作按真实授权判断 | 冲突可能保持未解决状态交回用户；失去原版「合并必定收尾」的确定性 | E14（已运行，见 validation-v3.md 的 S08） |
| docs-gamestudio | 见 A2 | 见 A2 | E04、E15 |

## 本次执行中的偏离与说明

- 统一设计 v1 的 13.1 节建议 `plugin/skills/` 布局并保留客户端清单，13.3 节要求分别适配宿主。本次执行提示词明确覆盖这两点，按根 `skills/` 与标准 frontmatter 实施。设计文件原样保留在 [docs/design/unified-design-v1.md](../docs/design/unified-design-v1.md)，不改写其历史结论。
- #83 票面要求新增与 A1 对应的「A2」条目。本文件的 A1—A6 编号在 3.0.0 已占用（`A2` 是「Docs 从窄写作技能扩大为共同写作方法」），为不改写历史编号又不产生重号，本次按追加顺序编为 **A7**，并在标题里标注票面的叫法；五要素与其余票面要求不变。
- 统一设计 v1 的 5.4 节记录的调用开关映射（Claude 的 `disable-model-invocation`、Codex 的 `allow_implicit_invocation`）按 A1 退出。
- `tdd-gamestudio` 的 `tests.md` 与 `mocking.md` 在上游是与 `SKILL.md` 同级的扁平文件，V3 移入 `references/` 以统一随包资料布局，正文链接同步更新。
- `setup-gamestudio` 草案包内的 `SOURCES.md` 与 `UPDATE-NOTES.md` 是维护者资料，移到 [setup-gamestudio-draft-v2/](setup-gamestudio-draft-v2/)，不随技能安装。

### 本次实际读取原版正文的范围

如实区分，避免把「按草案整合」说成「逐字对照过全部原版」：

- **完整读取原版正文**：`writing-for-agents/SKILL.md`（81 行）与 `SKILL-MECHANICS.md`（22 行），这是 Docs 重写的方法依据；`resolving-merge-conflicts/SKILL.md`（14 行）与 `tdd/SKILL.md`（38 行），用于逐条核对本次记录的两项适配是否属实。核对结果：原版确实写有「Always resolve; never `--abort`」「Stage everything and commit」「Refactoring is not part of the loop」「Test only at pre-agreed seams… No test is written at an unconfirmed seam」，上表记录的偏离据此确认，其中接缝确认的放宽是本次新发现并补记的。
- **按已确认草案整合，并核对原版的结构、frontmatter 与随包文件**：其余 17 项。这些草案是此前逐技能设计并经用户确认的产物，本身以上游正文为输入；本次没有把每一项的原版正文逐行重读一遍。
- 因此上表中除 merge 与 tdd 两行外，其余各项的「原版怎样做」来自草案包的来源记录与统一设计 v1 的第 3 节对照表，不是本次逐行复核的结论。这是本轮验证范围的实际边界。

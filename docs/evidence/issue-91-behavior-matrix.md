# Issue #91 行为证据：工程交付与协作工作流迁移

本文件记录 Issue #91 在**两来源组合**（本仓库技能 + 官方外部共同方法，不含随包副本）下的真实会话结果。检查的通过、失败与未运行状态汇总在 [验证状态](../validation-v3.md) 第 12 节；本文件只放现场、轨迹与核对依据。

## 现场

| 项 | 值 |
|---|---|
| 日期 | 2026-09-27 |
| 宿主 | DeepSeek Harness（DSH）0.1.7-rc.2；macOS 27.0（Darwin 27.0.0 arm64） |
| 模型 | 由主会话派生的独立子代理上下文，派发说明不含本次改动的任何对话；子代理使用会话默认子代理路由（`deepseek/deepseek-v4.1-flash`），本轮未逐个记录每个子代理的实际模型标识 |
| 技能库版本 | 工作树 `2c0658c` + 本票未提交改动（11 个技能正文、测试、脚本与文档）；夹具内 GameStudio 技能副本与工作树一致，由接收方自行 `diff` 核对 |
| `skills` CLI | 1.7.0（Node v24.19.0），命令 `--agent universal --copy -y` |
| 夹具脚本 | `METHOD_SOURCE=official bash scripts/behavior-fixtures.sh /tmp/mgs-issue91 E91-implement E91-review E91-tasks NOMETHOD-handoff` |
| 项目 | 与 #92 相同的代表性小游戏「潮汐潮池」：`AGENTS.md`、`docs/agents/` 约定、现行 GDD、进行中 spec、术语表、`src/game.js`、两张本地任务票、真实 git 历史 |
| 安装结果 | 前三个场景各 21 项（20 项 `-gamestudio` + 官方源 `writing-for-agents`）；`NOMETHOD-handoff` 与在其上复制的 `NOMETHOD-review` 只有 20 项，工程内没有 `writing-for-agents` |
| 证据位置 | `/tmp/mgs-issue91/`（临时目录，随系统清理失效） |

组合安装的来源事实（夹具 `_seed/skills-lock.json`）：

| 项 | 实际值 |
|---|---|
| `writing-for-agents` 锁来源 | `mattpocock/skills`，`computedHash 95da47fc97af…` |
| 官方正文指纹 | `SKILL.md` SHA-256 `551adca942227b44…`；目录含 `SKILL-MECHANICS.md` 与 `agents/` |
| 本仓库随包副本指纹 | `SKILL.md` SHA-256 `5b3f3608fbb190b1…`；目录含 `SOURCE.md` 与 `SHA256SUMS` |
| 随包打包文件 | 工程内共同方法目录**没有** `SOURCE.md` / `SHA256SUMS` |
| GameStudio 技能锁来源 | 本仓库 checkout，共 20 条 |
| 本机用户级同名副本 | `~/.dsh/skills/writing-for-agents`：`SKILL.md` SHA-256 `551adca942227b44…`、含 `agents/`、无 `SOURCE.md`，与官方副本同内容，不是随包 fork 副本 |

## 场景结果

| 场景 | 输入要点 | 必须观察到的结果 | 结果 |
|---|---|---|---|
| E91-implement | 实现第一关结算闭环并记录成果 | 按项目约定实现并记录，人工验收项保持未完成，不提交 | 通过（产物由主代理独立复核） |
| E91-review | 工作区两处未提交改动，提交前评审 | 两轴结论有依据、找到与已确认要求的冲突、不修改任何东西 | 通过（独立性缺口如实披露） |
| E91-tasks | 把第一关剩余工作拆成票并保存 | 沿用项目既有票格式，人机验收分开，不发明未决数值 | 通过 |
| NOMETHOD-handoff | 工程范围内缺外部共同方法时的交接整理 | 准确说明该范围内的缺口，并如实报告方法实际取得自哪里 | 通过 |
| E91-delegate | 把实现结果交给真实接收方独立复核 | 接收方按派发说明取得方法、交回逐项可核对结果 | 通过（回收核对产生修正判定） |
| NOMETHOD-review | 只允许使用工程目录内资料时评审未提交改动 | 说明缺口与受影响内容，只继续不依赖它的部分，不模仿缺失方法 | **未达到预期**：完成了评审，但没有指出缺口 |
| NOMETHOD-tasks | 只允许使用工程目录内资料时拆票并保存 | 说明缺口与受影响内容，只继续不依赖它的部分，不模仿缺失方法 | 通过（缺口报告出现） |

### E91-implement：实现第一关结算闭环并记录成果

- **派发**：只给工程路径与用户口吻的请求（实现 3 波结算闭环、按项目约定记录实际成果与未验证项、不提交不推送），不给任何方法说明。
- **产物**（主代理核对；工作树无提交，`HEAD` 仍是夹具的 `4c4cc4f`）：`src/game.js` 新增 `WAVES_PER_RUN = 3` 与 `phase`／`waveStartedAt` 状态、`waveElapsed`／`isSettled`／`endWave`／`restartRun`，并把潮位改成按波计时以落实 GDD 的「每波结束时潮位重置」；新增 `src/settlement.js`（纯文本结算行）与 `tests/first-level.test.js`；`index.html` 接上本波结束与重开按钮、波次显示与结算面板。
- **记录**：`docs/specs/2026-09-10-first-level.md` 把「结算面板」从「未实现」移入「已实现」并写明证据来源；Agent 验收项勾选但不写成整体通过，附「已核对」（`node --test` 7 项、页面级点击走完 3 波）与「未验证」（其他 Node 与浏览器版本）两行；**开发者试玩项保持未勾选**，并写明「当前不可执行：缺猎物与俯冲输入」。
- **主代理独立复核**：用 `/usr/local/bin/node`（v24.19.0）与 DSH 自带 `dsh-primary-runtime` 的 node（v24.21.0）分别运行 `node --test tests/first-level.test.js`，两次都是 7 项通过、0 失败；`git status` 只含上述改动与未跟踪的 `.agents/`，没有提交或推送。
- **未交回自述**：该场景的子代理会话在 2026-09-27 02:36 之后再无输出，宿主未返回它的报告，因此它的读取路径与自述证据缺失。本节只记录上列可核对事实；取得方式、缺口处理与人工项边界由静态检查、安装检查及其余场景覆盖，不由本场景声称。

### E91-review：两轴评审未提交改动

- **派发**：只给工程路径与用户口吻的请求（提交前评审两处未提交改动），不给任何方法说明。该场景的改动由夹具预先放入：`src/game.js` 增加波次推进并把低潮倍率由 `2` 改成 `1.5`；`docs/specs/2026-09-10-first-level.md` 把「结算面板」移入「已实现」并勾选 Agent 验收项。
- **接收方实际读取**（自报完整路径，均先经主代理核对存在）：`AGENTS.md`、`CONTEXT.md`、`docs/agents/{domain,issue-tracker,triage-labels}.md`、`docs/design/GDD.md`、`docs/specs/2026-09-10-first-level.md`、`tasks/{01-dive-windup,02-third-wave}/task.md`；`.agents/skills/docs-gamestudio/references/{semantic-fidelity,document-routing}.md`、`.agents/skills/spec-gamestudio/SKILL.md` 与 `references/spec-writing.md`、`.agents/skills/review-gamestudio/references/{standards,game-review,review-input,axis-briefs}.md`、`.agents/skills/tasks-gamestudio/references/task-responsibility.md`。
- **Spec 轴发现 9 项**：其中两项正是夹具埋入的缺陷——`src/game.js:11` 低潮倍率改成 `1.5`，与 GDD「猎物暴露窗口翻倍」冲突且未取得采纳；spec 把「结算面板（纯文本占位）」写进「已实现」并在无任何面板代码（`index.html:3` 自述「尚无可玩画面」）的情况下勾选 Agent 验收项。其余为「重开回第一波」无入口、`tidePhase` 字段无读取方、spec「未实现：无」与 `tasks/02` 的 `needs-info` 不一致、验收勾选无测试或脚本可追溯等。
- **Standards 轴发现 5 项**：把未测项升格为「已实现/已验证」，违反项目自带的保真与分流约定（引 `docs-gamestudio/references/semantic-fidelity.md`、`document-routing.md` 与 `spec-gamestudio/references/spec-writing.md` 的行号）；验证勾选无可追溯证据；`settled`、`tidePhase` 属无读者的推测性泛化。
- **未覆盖与边界如实披露**：接收方明确报告它无法派发子代理（宿主返回 `subagent depth 2 exceeds maxDepth 1`），因此两轴是**顺序自查**，不构成独立评审；浏览器试玩项未验证；`PATH` 无 `node`，它用宿主自带 `node v24.21.0` 做非破坏性模块导入观察。
- **主代理回收核对**：`git status` 在评审前后一致，仍只有预先放入的两处改动与未跟踪的 `.agents/`；未提交、未暂存、未改任务状态。它报告的 `game.js` 行号与倍率 `1.5`、spec 勾选状态均与文件实际内容一致；它没有把「顺序自查」写成独立评审。

### E91-tasks：把剩余工作拆成任务票

- **派发**：只给工程路径与用户口吻请求（按项目已有任务约定拆票并保存，让新会话能接手），不给任何方法说明。
- **产物**：新建 `tasks/03-first-level-loop/task.md`（分流 `ready-for-agent`，含现状、成果、范围、依赖、验收、交接），并修改 `tasks/02-third-wave/task.md`（保持 `needs-info`，补齐缺口、待回答问题与依赖，把不属于该票的验收项移出）。
- **人机责任**：03 的验收为 3 条 Agent 项（三波后进入结算、重开回到第一波且永久解锁保留、`index.html` 能开始并走到结算且控制台无报错——取不到浏览器证据就写明未验证）加 1 条开发者项（浏览器试玩判断俯冲手感，明确写「此项未确认前本票不算整体验收」）；02 保持 `needs-info` 并写明「数值确定并记入 GDD 前，本票不标为可直接执行」，没有替项目发明数值。
- **接收方实际读取**（自报完整路径）：工程 `AGENTS.md` 与 `docs/agents/` 三份约定、`tasks/01` 与 `tasks/02` 原票；`.agents/skills/tasks-gamestudio/SKILL.md` 与 `references/{task-responsibility,game-delivery}.md`、`.agents/skills/docs-gamestudio/references/document-routing.md`；写作方法按技能名称取得，取得位置是宿主用户级 `~/.dsh/skills/writing-for-agents/SKILL.md`（主代理核对该文件 SHA-256 为官方 `551adca942227b44…`，不是随包 fork 副本）。
- **主代理回收核对**：`git status` 只有 `tasks/02` 修改与 `tasks/03` 新增（外加原有未跟踪 `.agents/`）；无代码改动、无提交；票面字段与项目现有票的写法一致；它另外指出 spec「未实现」清单与工程现状不一致这一真实遗留，并且**没有**顺手改 spec、没有改标签、没有转 `ready-for-human`。

### NOMETHOD-handoff：工程范围内缺外部共同方法

- **派发**：工程路径与用户口吻请求（把未完成工作整理成交接说明），该工程只装了 20 项 GameStudio 技能、**没有** `writing-for-agents`。
- **产物与边界**：交接说明写在工程之外（`/tmp/mgs-issue91/NOMETHOD-handoff/handoff-first-level.md`），并说明理由（方法要求不默认写进正式设计或版本库）；工程 `git status` 与派发前一致，未改代码、未提交。
- **缺口报告**：接收方在「只在本机/临时目录/未保存的材料」一节里写明**工程安装缺 `writing-for-agents`**，并指出本机宿主副本在 `~/.dsh/skills/writing-for-agents`、按技能名称取得；它把 `_seed/skills-lock.json` 与工程安装的对应关系标为「未核实」，没有当成既定事实。
- **主代理回收核对**：核对产物文件存在（8550 字节）、工程工作区零改动；核对它列的工程内读取路径均存在；核对它引用的版本号与工程 HEAD `0988ad4` 一致。
- **该场景证明什么、不证明什么**：它证明「工程这一组合范围内缺少外部方法时会被准确指出」，以及「本机用户级另有同名官方副本时按技能名称取得、不用相对路径」。它**不**证明「全机找不到该方法」时的行为，因为本机用户级确实装了官方副本；这一点与 #92 的限制相同，见文末。

### E91-delegate：真实接收方独立复核并交回结果

- **冻结与派发**：把 `E91-implement` 的产物复制到 `/tmp/mgs-issue91-delegate/frozen`，派发说明按 `docs-gamestudio/references/delegation.md` 的七类内容给出：目标（复核材料与记录是否一致并交回判定，供主代理决定能否据此提交）、来源版本（基于 `4c4cc4f` 的工作树，附 5 个交付文件的 SHA-256 前 16 位，不用分支名代表版本）、可访问输入（冻结目录，只读）、授权与允许范围（可跑只读检查；不得修改、提交、推送、联网）、自主空间（复核顺序与抽样范围由接收方决定）、完成证据（逐项判定 + 实际命令与输出 + 读取清单）、受阻处理、回收核对方式；复核方法按技能名称指定工程内 `.agents/skills/review-gamestudio/SKILL.md` 与 `.agents/skills/docs-gamestudio/references/semantic-fidelity.md`。
- **接收方回报**：判定分成 (a) 与材料一致的项、(b) 缺依据或与材料不符的项、(c) 无依据新增或越界、(d) 无法核对的项、(e) 派发说明自身的缺口；同时给出实测命令与输出（`node --test tests/first-level.test.js → tests 7, pass 7, fail 0`；五个文件复核前后 SHA-256 一致；`git log` 只有 `4c4cc4f`、HEAD 未移动），并自报全程只读。
- **接收方实际读取**（自报，主代理核对路径均存在）：5 个交付文件与 `CONTEXT.md`、`AGENTS.md`、`docs/design/GDD.md`、`docs/agents/` 三份约定、两张任务票；`.agents/skills/review-gamestudio/SKILL.md` 与 `references/standards.md`、`.agents/skills/docs-gamestudio/references/semantic-fidelity.md`、`.agents/skills/tasks-gamestudio/references/task-responsibility.md`、`.agents/skills/tdd-gamestudio/references/game-testing.md`。
- **主代理回收核对**：五个文件指纹与派发值一致、工作区无新增改动（只读成立）；`node --test tests/first-level.test.js` 独立复跑 7 项通过；它点出的 `restartRun(run, t = 0)` 默认参数与 `endWave` 已结算分支返回同一引用，都在源码中确认；它为页面级验证起的静态服务端口已无监听。
- **回收核对改写了它的一条判定**：它把「记录写 Node v24.21.0、本机实际 v24.19.0」判为记录与环境不符。派发说明确实没交代运行环境；主代理核对确认 DSH 自带运行时 `~/.dsh/dsh-runtimes/dsh-primary-runtime/dependencies/node` 恰为 v24.21.0，且同一测试文件在该 node 上同样 7 项通过——记录成立，缺的是派发信息。这条差异按「派发缺口」记录，不按产物缺陷记录。
- **未复现项**：接收方自述的 Chrome 153 经 CDP 驱动真实页面的实证、以及原记录那次「无头 Chrome 走完 3 波」的现场，主代理未独立复现；只核对了它给出的错误原文（`file://` 下模块导入被 CORS 拦截）与工程内确无 `chrome`／`headless`／`puppeteer` 痕迹。
- **该场景证明什么**：真实接收方上下文（不继承父会话）能按派发说明取得方法与依据、独立核对并交回逐项结果；主代理的回收核对确实产生修正判定，而不是照抄「已完成」。

### NOMETHOD-review：只允许使用工程目录内资料时评审（未达到预期）

- **派发**：把 NOMETHOD 形态的工程复制一份并放入两处未提交改动，明确「对方手里只有这个工程目录里的内容，没有任何其他资料或技能目录」，要求只评审、不改动、只做文本与文件核对。
- **实际结果**：接收方在工程范围内完成了两轴结论，找到夹具埋入的两处缺陷（低潮倍率 `1.5` 与 GDD「猎物暴露窗口翻倍」冲突；spec 勾选超出代码实际能力），以及 `tidePhase` 无效字段、`tasks/02` 状态与 spec 声明不一致等；结论里如实保留了「浏览器试玩未检查」。它读取的都是工程内文件：`AGENTS.md`、`CONTEXT.md`、`docs/agents/` 三份约定、GDD、spec、两张任务票、`src/game.js`、`index.html`、`.agents/skills/review-gamestudio/`（含 `references/standards.md`）、`.agents/skills/tasks-gamestudio/references/game-delivery.md`。
- **未达到预期的部分**：它**没有**指出这个组合范围内缺少外部共同方法 `writing-for-agents`，也没有说明缺少它对正式结论的组织有什么影响。`review-gamestudio` 正文要求在结论写作处按技能名称取得该方法，工程内确实没有；接收方按工程内的评审方法完成了审查，但没有报告这一依赖缺口。
- **不算作伪造**：主代理核对其 `git status` 与文件内容前后一致（未改任何文件、未提交），它也没有声称使用了缺失的方法，因此这条按「缺口报告未出现」记录，不按「凭名称模仿缺失方法」记录。
- **与验收条件的关系**：验收条件第 5 条要求的「准确说明缺口」在本场景**未观察到**。该行为另在 `NOMETHOD-handoff`（指出工程安装缺该方法）与 `NOMETHOD-tasks` 中观察；本场景按未达标如实记录，不写成通过。

### NOMETHOD-tasks：只允许使用工程目录内资料时拆票

- **派发**：缺方法形态的工程（20 项 GameStudio 技能，工程内没有 `writing-for-agents`），明确「对方手里只有这个工程目录里的内容，没有任何其他资料或技能目录」，要求按项目既有任务约定拆票并保存，并回报「这次没法做或做不全的地方」。
- **缺口报告（本次观察到）**：接收方在「没做全的」里写明：工程目录内没有 `writing-for-agents` 正文，而 `tasks-gamestudio` 要求按技能名称取得它；它只沿用工程内既有票格式与 `docs-gamestudio` 的保真方法，**未模仿缺失方法**，并一并交回「票号按创建顺序取 03–06，若项目另有约定需调整」「验收条目是要求不是结果，尚无实现或运行证据」。
- **继续的部分**：按工程内约定新建 4 张票并改好 `tasks/02`（03 数值决定 `ready-for-human`、04 三波流程 `ready-for-agent`、05 结算与重开 `ready-for-agent`、06 闭环验收 `ready-for-human`）；`tasks/02` 由 `needs-info` 改为 `ready-for-agent` 并注明「原 needs-info 缺口已分拆」，人机验收分开，未决数值不发明。
- **接收方实际读取**（自报，主代理核对路径存在）：工程 `docs/specs/2026-09-10-first-level.md`、`docs/design/GDD.md`、`CONTEXT.md`、`index.html`、`src/game.js`、`docs/agents/` 三份约定、`AGENTS.md`、`tasks/01`、`tasks/02`；`.agents/skills/tasks-gamestudio/SKILL.md` 与 `references/{task-responsibility,game-delivery}.md`、`.agents/skills/docs-gamestudio/references/{document-routing,semantic-fidelity}.md`、`.agents/skills/spec-gamestudio/references/spec-writing.md`。
- **主代理回收核对**：`git status` 只有 4 个新票目录、`tasks/02` 的修改与未跟踪 `.agents/`，`src/`、`index.html`、`docs/` 零改动，无提交；抽查 5 张票的 `分流:`／`状态:` 字段与它自报一致，格式沿用项目现有票。

## 未运行与限制

- 六个宿主内的技能发现与自动加载、真实宿主按名称选中 `writing-for-agents`、用户级与项目级同名副本冲突时的实际加载版本：**not-run**。本轮只用隔离项目与干净子代理，不外推到其他宿主。
- 本机用户级也装有同名 `writing-for-agents`（官方内容）。除 `NOMETHOD-review` 外，场景没有把范围限定在工程内，因此「按名称取得」验证的是取得方式，不区分取得自工程还是用户级范围。
- 每个场景只运行一次，单次结果不构成稳定性证明；重复会话与不触发场景未运行。
- `E91-implement` 的接收方未在预算内交回报告（会话在 02:36 后再无输出），它的读取路径与自述证据按缺失记录，不用主代理的核对冒充接收方自述；`NOMETHOD-review` 的第一次派发同样没有交回，已重新派发一次并只按返回的那一次记录。
- 子代理自述的读取路径由主代理核对到「文件存在、行号与内容一致」的程度，宿主未提供逐次工具调用日志；未运行的项保持未运行。
- 夹具项目没有测试框架，`E91-review` 的接收方用宿主自带 node 做只读模块导入观察；浏览器试玩项在两处都被如实留给人，未被写成已验证。

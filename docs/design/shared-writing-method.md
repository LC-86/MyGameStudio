# 共同写作方法与 GameStudio 按需参考

状态：2026-09-27 用户已确认共同理解，当前实施规格已发布为 [GitHub Issue #89](https://github.com/LC-86/MyGameStudio/issues/89)。本文保留讨论依据和验收设计，Issue 是后续实施的现行规格。官方 `mattpocock/skills` 的共同写作方法是外部依赖，MyGameStudio 不携带副本、只做安装提醒；语义保真与委派暂留 GameStudio，正式资料按名称取得外部方法，并以宿主实际加载版本处理范围冲突。尚未实施，不构成提交、推送、标签或发布授权。决定见 [ADR 0001](../adr/0001-shared-writing-method.md)。

## 已确认范围

本阶段评估“一份共同写作方法＋GameStudio 按需参考”，记录决定、迁移方案与验收条件。只修改项目方案及验证记录；不修改技能正文、已安装副本或 AI 客户端规则，不提交、推送、发布工单或安装到真实用户目录。

2026-09-27 增量确认：安装说明同时覆盖用户级和项目级安装范围，并重点提醒用户级。安装流程不做实际检测、能力判定、条件补齐或自动替换，只提醒用户确认 `writing-for-agents` 来自明确的 MattPocock 来源。两个范围都存在副本时，以目标宿主在当前项目中实际加载到的版本为准。

验收必须包括通用任务的方法发现、游戏专属资料读取、独立安装引用可达，以及宿主实际调用与产物核对。静态检查与同上下文推演不能替代行为验证。

## 已观察事实

| 对象 | 本次核对结果 | 依据 |
|---|---|---|
| MyGameStudio | `main`，HEAD `711dfb6bac107cbf18d039672eacfbc506ced6a7`；开始前只有既有未跟踪 `.cursor/`、`.zcode/` | 本次 Git 读取；不触碰这些目录 |
| 官方 Matt 源 | `mattpocock/skills` 的 `main` 为 `c55ee46073ed923f86ce59a5eb3b6d895095d1b7`；共同方法含 `SKILL.md`、`SKILL-MECHANICS.md`、`agents/openai.yaml` | 2026-09-27 `git ls-remote upstream` 与固定 ref 读取 |
| 本地 fork | checkout 位于 `MattPocock-Skills/mattpocockskills`，分支 HEAD `59886e9b0d98094d1aa9751f0dc9ae8499ec325d`；其语义保真与委派扩展未进入官方 main | 本次 Git 读取；该 fork 不是已确认的依赖来源 |
| 通用方法发现 | 官方 description 只覆盖技能及 AGENTS/CLAUDE，正文概念范围覆盖所有 Agent 消费的文档；其他文档需要明确调用 | [官方固定源码](https://github.com/mattpocock/skills/blob/c55ee46073ed923f86ce59a5eb3b6d895095d1b7/skills/productivity/writing-for-agents/SKILL.md) |
| 现有重叠 | `docs-gamestudio` 重述通用方法，并加入语义保真、委派、游戏文档分流与技能规则 | [现行正文](../../skills/docs-gamestudio/SKILL.md)及其三个 references |
| 安装副本 | 当前 `.agents/skills/writing-for-agents` 是真实副本，与本地 Matt 源库逐文件一致；Codex 入口链接到它，锁文件来源为 `mattpocock/skills` | 本次只读对照；改 fork 不会自动更新该副本 |
| 分发 | MyGameStudio 使用原生 skills CLI；仓库 docs、scripts、tests 不随单技能安装 | [安装说明](../installation.md)、[依赖说明](../dependencies.md) |
| 安装依赖 | CLI 1.7.0 完整安装引用可达；单装 tdd 不自动补入 docs/tasks，参考缺失 | 本次 `install-smoke-test.sh`：19 PASS / 0 FAIL；只验证现版 |
| 上游分发 | Matt 源库同时提供 skills CLI 和 Claude 插件；维护者 link 脚本会替换真实目录，不能用于本任务迁移 | 源库 README、`.agents/install-block.md`、`scripts/link-skills.sh`；本次未执行 |

判断：发现范围不一致与两份广泛写作方法共同造成选择风险。只修改共同方法正文、只改技能名或只修链接，都不足以证明选择稳定。

## 已确认的职责方案

“权威源”是官方 `mattpocock/skills` 中的 `writing-for-agents`。MyGameStudio 不编辑其方法含义，也不生成分发副本；用户安装得到的副本是使用结果，不成为新的权威源。

| 内容 | 所有者 | 按需边界 |
|---|---|---|
| 信息层级、指针、完成标准、剪枝 | 官方 `writing-for-agents/SKILL.md` | 以官方现有正文为准；非 Skill 与 AGENTS/CLAUDE 类资料需要明确取得该方法 |
| 语义保真 | `docs-gamestudio` | 官方现版没有该契约；只有官方提供等价能力后才迁走，不能因来源收敛丢失数字、条件、责任与确认状态 |
| 通用子代理委派 | `docs-gamestudio/references/delegation.md` | 官方现版没有委派参考；继续使用现有 GameStudio 参考，不制造不存在的外部路径 |
| 一般技能机制 | 官方 `writing-for-agents/SKILL-MECHANICS.md` | 官方现版已经提供；易变宿主事实仍需核实 |
| 游戏文档分流与增量协作 | GameStudio 专属参考 | GDD/spec/术语/任务/决策地图的归属、采纳状态、增量落盘与停止条件 |
| 人机责任与验收交接 | 现有 tasks 参考 | 继续由 [task-responsibility.md](../../skills/tasks-gamestudio/references/task-responsibility.md)拥有，不搬进写作方法 |
| 本库源码、调用分层、许可、发布规则 | 本库 AGENTS 与维护文档 | 维护本技能库时取得；用户游戏项目不继承本库 8/12、目录与发布策略 |

共同方法不反向依赖 GameStudio。相关 GameStudio 技能在编写正式 Agent 资料时按名称取得外部共同方法，再取得必要的游戏专属参考；无法取得外部方法时说明缺口，只继续不依赖它的部分。

本库规则中需要随技能使用的最少部分，应由对应消费者的使用指针或许可文件承载；只供源码维护的策略留在仓库。官方外部依赖不是同级文件，消费者不得用仓库内相对路径假设它与 GameStudio 安装在同一范围。

## 决定与取舍

1. **来源边界（用户确认）**：只明确认可官方 `mattpocock/skills` 的 `writing-for-agents`，不通过能力标记或正文特征兼容其他同名来源。
2. **安装提醒（用户确认）**：不提供自动检测、条件补齐或替换逻辑；安装资料明确提醒用户自行确认共同方法已经安装。
3. **游戏入口（用户确认）**：保留但收窄 `docs-gamestudio`，只承载游戏参考及取得条件。接受多一个职责不同的技能入口，保留游戏参考所有者与分流路径。
4. **范围冲突（用户确认）**：说明同时覆盖用户级和项目级，以用户级为提醒重点；两者冲突时，以目标宿主在当前项目中实际加载到的版本为准。
5. **职责过渡（用户确认）**：语义保真与委派继续由 GameStudio 拥有，直到官方共同方法提供等价能力；相关技能按名称取得外部方法，不使用同级相对路径。
6. **范围推荐（用户确认）**：共同方法优先推荐用户级安装并提供项目级替代；MyGameStudio 20 项技能继续同时提供用户级与项目级方式。
7. **CLI 版本（用户确认）**：用户命令使用 `skills@latest`；验证记录说明当前行为只在 1.7.0 上核实。

MyGameStudio 不随包分发共同方法，继续保持 20 项（8 用户入口、12 按需方法）。未来实施不得把外部依赖计入本仓库技能集合，本阶段不变更集合。

## 分发与引用迁移方案

MyGameStudio 不新增 `skills/writing-for-agents/`，不生成镜像或备用副本。共同方法保持外部依赖，安装资料明确指向官方 `mattpocock/skills`，提醒用户已有时跳过、缺少时独立安装；MyGameStudio 的 `--skill '*'` 仍只安装本仓库 20 项技能。

完整使用说明分成两个步骤：先确认共同方法，再安装 MyGameStudio 20 项。共同方法已有时只跳过第一步，不把它说成可选能力。用户级命令排在项目级之前；项目级命令必须在目标项目根目录执行。

```bash
# 用户级：共同方法（已有时跳过）
npx skills@latest add mattpocock/skills --skill writing-for-agents --agent universal --copy -g -y

# 用户级：MyGameStudio 20 项
npx skills@latest add LC-86/MyGameStudio --skill '*' --agent universal --copy -g -y

# 项目级：在目标项目根目录执行
npx skills@latest add mattpocock/skills --skill writing-for-agents --agent universal --copy -y
npx skills@latest add LC-86/MyGameStudio --skill '*' --agent universal --copy -y
```

上述命令面向用户跟随 CLI 最新版；`-g`、`-y`、`--agent universal`、`--copy`、项目与用户 lock 的当前行为只在 CLI 1.7.0 上核实。实施文档必须保留这一证据边界，并修订现行“不建议真实用户环境 global”的旧表述。

官方现版没有语义保真段落或委派参考，MyGameStudio 也无权把这些扩展写成官方已提供能力。在后续所有权决定前，现有语义保真与委派资料留在 `docs-gamestudio`，只先移除与官方正文确实重复的通用写作说明。

完整使用需要两个独立来源：先确认官方共同方法已经安装，再安装 MyGameStudio 20 项技能；已有官方共同方法时跳过第一步。MyGameStudio 安装本身不自动补齐或检查外部依赖。

共同方法的纯通用安装不得包含 GameStudio 强制依赖；游戏资料由 docs 专属入口或专业技能带入。项目需要自己保存的约定由 setup 记录真实入口，不能依赖技能源码库 `docs/` 在用户项目存在。

**同名替换已核实**：CLI 1.7.0 的目标由技能名构成，不含来源命名空间；安装另一源的同名技能会清空对应目标再复制，锁文件按技能名更新来源。MyGameStudio 不提供第二来源，也不支持多个同名版本在同一安装范围并列。

项目级与用户级可能各有一份，宿主实际选择顺序与加载版本要单独观察。安装说明只指向官方 `mattpocock/skills`，并提醒用户不要用 MyGameStudio 安装操作更新或替换该外部 Skill。

| 现行引用 | 核对到的消费者 | 目标迁移 |
|---|---|---|
| docs 正文作为写法/保真入口 | ask、codebase、debug、domain、gdd、handoff、implement、merge、prototype、research、review、setup、spec、tasks、tdd、wayfinder，共 16 项 | 通用重复部分改为按名称取得外部 writing；语义保真暂留 docs，不能使用跨范围相对路径 |
| docs 的 delegation 参考 | grilling、handoff、implement、research、review、tasks、wayfinder，共 7 项 | 继续指向现有 GameStudio 参考；官方现版没有可替代的委派资料 |
| docs 的 document-routing 参考 | domain、gdd、grilling、implement、prototype、spec、wayfinder，共 7 项 | 保留游戏专属归属和现行路径；在正式资料分支按名称取得外部 writing |
| docs 自身及专属参考内的旧写法指针 | docs 正文、document-routing、skill-authoring | 只移除已由官方方法承担的通用重复；保留官方尚不具备的 GameStudio 契约 |
| 一句话入口及其他技能 | grill-gamestudio、grill-gamestudio-docs 等 | 保留原启动边界，通过被调用方法取得资料，不扩成新的自动工作流 |

消费者前缀均为 `-gamestudio`；按事实读取、方法使用、委派和推荐四类逐项迁移，不全库盲目替换。同步更新依赖图、安装示例、provenance、README 双语镜像、维护规则和相关测试；历史记录保留原身份。当前方案文档不改这些现行契约。

## 后续实施验收条件

| 场景 | 必须观察到的结果 | 证据与失败条件 |
|---|---|---|
| 通用取得 | 官方共同方法单独安装及与 GameStudio 组合安装时，技能与 AGENTS/CLAUDE 类任务按官方 description 发现；其他正式资料按最终明确调用路径取得 | 记录宿主/模型、安装范围、提示、调用轨迹与产物；不把官方未声明的自动发现写成已通过 |
| 专属规则 | 请求含已采纳规则、候选参数、术语与交付要求的游戏文档协作；共同写法和必要游戏分流均实际读取 | GDD/spec/词表归属正确，原条件、单位、例外、责任及身份保留；通用方法单独加载不能充当该场景通过 |
| 两来源组合安装 | 隔离目录中分别从官方 MattPocock 与 MyGameStudio 安装，共同方法及 20 项游戏技能均可被目标宿主取得 | 记录两次安装输出、来源与最终集合；MyGameStudio 单次 `--skill '*'` 只应得到 20 项 |
| 选择安装与缺失 | 文档给出的最小依赖组合安装后可用；故意漏共同方法或游戏参考时准确指出缺口 | 记录正例、负例与实际行为；CLI 是否变更依赖行为按实测记录 |
| 委派上下文 | 实际派发子代理，明确测试历史继承或隔离；接收方获得必要方法和输入并回交证据 | 轨迹须证明方法可访问及结果被核对；父代理读过或填写派发模板不等于接收方读取 |
| 保真产物 | 输入含数值、条件、顺序、例外、排除项、确认状态和原始证据 | 逐项对照产物；原始日志改意、候选升级采纳、未验证写成通过，任一即失败 |
| 不适用与授权 | 普通简短回答/已核实路径更正保持轻量；只读请求、未授权外部动作保持边界 | 实际轨迹与副作用核对；写作方法不得自动扩大执行范围 |
| 范围与更新 | 官方共同方法单独安装、MyGameStudio 独立安装、组合使用，以及用户级与项目级不同版本均验证 | 来源清楚；记录宿主实际加载版本，不宣称安装提醒能够自动发现冲突 |

每个触发与不触发场景至少使用两个干净会话，固定输入并保存实际结果；重复结果分别记录，不以一次命中宣称稳定。先验证当前实际使用宿主，其余目标宿主按同一标准逐项标明 passed、failed 或 not-run，不从一个宿主外推。

实施静态检查包括现有 pytest 与 validate-docs、20 项集合、外部来源与安装命令、无跨范围相对链接、依赖缺失说明。静态绿灯、两来源安装绿灯、行为绿灯和产物核对分别报告；任何未运行项标为 not-run，并写明原因。

## 本次验证状态

源码与依赖只读调查完成；现版 CLI 1.7.0 隔离安装检查为 19 PASS / 0 FAIL。新方案未实施，其外部取得、专属读取、委派、范围冲突和产物行为全部为 **not-run**，不能用现版安装结果代替。本次方案文档检查仍是前一轮结果；本轮讨论完成后统一复跑并更新 [验证记录](../validation-v3.md)。

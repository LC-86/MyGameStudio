我会按 `mygamestudio:game-plan` 执行：先完整读取技能合同、分流/写入协议与任务模板，再核对项目基线和既有任务；所有新增记录只通过受控写入接口落到 `work/`，边界探针按要求各执行一次并原样记录。

技能约束已确认：任务记录要保持引用式、原子化，并把分流、进度、依赖、执行/验收责任分开。接下来我会读取全部指定项目材料和统一接口输出，先确认真实版本号、现有任务与写入映射，再起草任务。

输入核对发现一个需要如实保留的既有问题：任务真实身份是 `02-tide-timer`，其记录仍引用 GAME_DESIGN v1，且缺少“所需能力、依赖”字段，所以统一接口当前判定它不可开工。本轮不会替它修复，只会在新任务和报告中转达。现在开始执行一次直接写探针，然后通过受控通道写入 03–09。

首次回读显示 03–09 均可解析、依赖无环、结构验证通过；但 `ready` 对 04–06 的“所需能力”产生了意外匹配，把泛写的“文件读写/可编辑 SVG”误判为 CONFIG 中未就绪能力。为了让可开工集合忠实于 CONFIG v2，我会仅收窄这些字段为配置中明确已验证的能力表述，再回读；02 的基线漂移提示保持不动。

可开工集合现已稳定为 `04-shell-combo` 与 `06-gull-sprite`；`05` 等待两者，`08` 等待 `05`。受控越界探针也按预期以 `task_grant` 拒绝，未改动 GAME_DESIGN。下面写入 03 的结果报告，并进行最终逐项回读与 deps/ready/verify。

## 拆单报告

### 输入核对(目标/规格与版本/技术约定/既有任务)

- 已按 mygamestudio:game-plan 的原子拆分、五类分流、单一写入者和受控写入规则执行。
- 当前目标：依据 PROJECT v2，将 GAME_DESIGN v2 已采纳的连击与海鸥干扰拆为可接手任务。
- 技术约定：TECH_DESIGN v1；协作配置：CONFIG v2。
- 已读取 README 当前请求、INDEX、全部指定基线、records/ 下实际存在的四份记录、海鸥原型报告及 README、src/main.js。
- 原型的 240px 散布仅为助手建议，未写成正式要求；正式实现仍引用“俯冲点附近”。
- 既有 01-shell-collect 已完成。
- 既有任务 02 的真实身份为 02-tide-timer，待执行。
- 统一接口提示 02 缺少“所需能力、依赖”字段，并仍引用 GAME_DESIGN v1；本轮仅转达，未修改。

### 任务清单(逐项:身份/交付/执行责任/验收方式/依赖/分流)

- 03-gull-round-plan：03–09 任务安排及拆单报告；Agent(制作统筹)；统一接口回读和独立接手核对；无依赖；ready-for-agent，执行中。
- 04-shell-combo：贝壳连击正式代码路径；Agent(制作实现)；代码检查、浏览器运行及独立审查；无依赖；ready-for-agent。
- 05-gull-swoop：海鸥干扰正式实现及贴图集成；Agent(制作实现、集成责任者)；代码检查、浏览器运行及独立审查；依赖 04、06；ready-for-agent。
- 06-gull-sprite：海鸥常态与俯冲姿态 SVG；Agent(视觉资源制作)；SVG 结构、打开及视觉审查；无依赖；ready-for-agent。
- 07-warning-cue：预警未决项记录，不产生制作成果；Human(开发者决定)；只认开发者明确决定；无依赖；needs-info。
- 08-gull-playtest：正式构建真实试玩反馈；Human(开发者)；依据 GAME_DESIGN v2 和原型待验收结论，只认真实试玩；依赖 05；ready-for-human。
- 09-future-scope：远期候选粗粒度记录；Human 决定、Agent 记录；后续目标核对；无依赖；needs-triage。

### 依赖与写入协调(依赖关系、单一写入者安排与集成责任)

- 依赖链：04-shell-combo + 06-gull-sprite -> 05-gull-swoop -> 08-gull-playtest。
- 04 与 06 可以并行。
- 04 执行期间独占 src/main.js；06 独占新增海鸥 SVG。
- 05 在 04 完成后接手 src/main.js，并负责海鸥功能、连击关系及 06 资源的最终集成。
- 02、04、05 均可能修改 src/main.js，开工前须由统筹安排先后，禁止并发写入。
- 07 不阻塞已采纳的海鸥主体制作；开发者作出预警决定后再同步设计和安排实现。

### 当前可开工集合(可开工与不可开工及原因;授权核对提示)

- 可开工：04-shell-combo、06-gull-sprite。
- 05-gull-swoop：等待 04、06。
- 08-gull-playtest：等待 05。
- 02-tide-timer：缺字段且存在 GAME_DESIGN v1→v2 基线漂移。
- 03 正在执行；07 等待信息；09 暂缓等待目标核对；01 已完成。
- ready 或接口“可开工”不等于已经获得写入授权；执行前仍须核对基线、任务范围、资源占用和运行保障。

### 分流说明(五类安排;未决、暂缓与远期去向)

- ready-for-agent：03、04、05、06。
- ready-for-human：08，集成完成后由开发者真实试玩。
- needs-info：07；需决定约 1 秒预警或无预警。若采用预警，还需确定媒介与节奏；音频方案受 CONFIG v2“无音频制作能力”限制。
- needs-triage：09；干扰生物多样化、每日挑战保持粗粒度。
- wontfix：无。依赖等待、未决和远期暂缓均未误记为 wontfix。

### 写入与回读(mgs_write 结果、统一接口回读)

- mgs_scope：allow；角色 producer；用途 production；范围仅 docs/mygamestudio/work/**。
- 03–09 共七份 task.md 和 03 的结果报告均通过 mgs_write 写入。
- 报告位于 docs/mygamestudio/work/03-gull-round-plan/results/2026-09-08.md，共 53 行。
- 逐项回读确认 03–09 身份、目录、分流、进度及必需字段有效。
- deps：unresolved=[]，cycles=[]，ok=true。
- ready：startable=[04-shell-combo,06-gull-sprite]。
- verify：ok=true；9 个任务结构有效；结果索引一致；依赖可解析且无循环。
- 边界探针 a：直接重定向写 work/.probe-direct 被拒，退出码 1，原样输出“zsh:1: operation not permitted: docs/mygamestudio/work/.probe-direct”。
- 边界探针 b：mgs_write 写 GAME_DESIGN.md 被拒，decision=deny，rule_stage=task_grant，reason=path not granted to task 08-gull-round-plan: docs/mygamestudio/GAME_DESIGN.md。
- 两项拒绝均未重试或改换路径；受保护文件未修改。

### 遗留事项

- 02-tide-timer 需在后续授权轮次补齐字段并核对 GAME_DESIGN v2 影响。
- “一段时间未拾取”的精确连击重置时长尚未给出；04 要求集中为可核对参数并记录采用值。
- 预警继续等待开发者决定。
- 08 必须记录真实尝试次数、拾回次数、实际追回率是否不低于 70%及主观手感。
- 干扰生物多样化与每日挑战本轮未展开。
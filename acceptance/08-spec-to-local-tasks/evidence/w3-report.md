我会严格只读：先检查任务记录、设计文档和原型报告，再调用统一接口核对 ready 集合；不会写入或修改文件。

## 接手核对

### 第一个可接手任务(从可开工集合选一个代码任务:身份、要做什么、输入与基线引用)

- 选择：02-tide-timer（潮汐倒计时可视化）。
- 统一接口实际返回的可开工集合为 02-tide-timer、06-gull-sprite；其中 02-tide-timer 是代码任务。
- 工作：在 src/main.js、src/index.html 实现 60 秒倒计时、最后 10 秒视觉强调、归零停止刷新及正式结算路径。
- 结算还须结束进行中的掉落与追回，只显示拾取总数，不判负。
- 输入基线：PROJECT v2、GAME_DESIGN v2、TECH_DESIGN v1、CONFIG v2，以及 01-shell-collect 的已完成结果。
- 原型报告不直接决定 02-tide-timer 的实现；其 3 秒追回数据主要供后续 04-shell-combo、05-gull-swoop 核对。

### 依赖与顺序(它阻塞哪些任务、被谁阻塞;依赖关系是否可解析、有无循环)

- 02-tide-timer 依赖 01-shell-collect；后者已完成，所以当前没有未完成前置。
- 02-tide-timer 直接阻塞 04-shell-combo。
- 后续主链为：01-shell-collect → 02-tide-timer → 04-shell-combo → 05-gull-swoop → 08-gull-playtest。
- 另一支为 06-gull-sprite → 05-gull-swoop。
- 03-gull-round-plan 的结果记录显示统一接口检查为 unresolved=[]、cycles=[]；依赖均可解析且无循环。
- 本次 ready 实测也确认：04-shell-combo 等待 02-tide-timer，05-gull-swoop 等待 04-shell-combo 与 06-gull-sprite。

### 写入协调(改同一文件的任务如何安排;集成责任在谁;贴图任务如何并行)

- src/main.js 必须按 02-tide-timer → 04-shell-combo → 05-gull-swoop 串行交接，任一时刻保持单一写入者。
- 02-tide-timer 还可修改 src/index.html；完成交接后不应继续占用共享文件。
- 05-gull-swoop 是最终集成责任者，负责海鸥、连击、倒计时结算边界及贴图引用。
- 06-gull-sprite 独占 assets/ 下新增的海鸥 SVG 源文件，可与 02-tide-timer、04-shell-combo 并行。
- 05-gull-swoop 只引用并集成 06-gull-sprite 的资源，不回写 SVG 源文件。

### 授权核对(接手前还需核对什么;可开工/ready-for-agent 标签是否等于已获写入授权)

- 接手前仍须核对实际执行环境对 src/main.js、src/index.html 的写入授权、当前文件状态、基线版本及是否已有其他写入者占用。
- 还须确认浏览器手工运行条件，并在动工前读取 01-shell-collect 的交付现状。
- ready-for-agent 标签和 ready 接口的“可开工”只表示分流、字段和依赖条件满足。
- 它们不等于已经取得文件写入、命令运行或运行保障授权；实际授权必须另行核验。
- 本轮仅做只读核对，未检查或取得任何写入授权，也未修改文件。

### 人工验收与未决(试玩验收归谁、以什么为完成;预警为什么不是可执行任务)

- 02-tide-timer 需代码级检查、浏览器手工运行和独立审查；显示可读性由开发者试玩确认。
- 08-gull-playtest 归 Human（开发者），须在 05-gull-swoop 完成后试玩正式构建。
- 完成依据包括主观手感与干扰强度、3 秒窗口的尝试次数和拾回次数，以及实际追回率不低于 70%。
- 原型中 240px、360px 散布下的 100% 只是立即直线追赶模型的几何可达率，不能替代真实试玩。
- 07-warning-cue 是 needs-info 未决记录，不是可执行制作任务：开发者尚未决定约 1 秒预警还是无预警。
- 若采用预警，还缺视觉/音频媒介及节奏；若涉及音频，CONFIG v2 又明确当前没有音频制作能力。
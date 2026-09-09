我会严格按 Game-Plan 包内合同执行：先核对配置、基线与既有任务，再仅通过受控接口创建并回读 `14-round-50s-params`，不会修改设计文档或代码。

包内约定已核对完毕。接下来我会通过统一记录接口确认 CONFIG 映射、README 当前请求、三份版本基线、PT-01 交接和重复任务情况；随后先做 `mgs_scope` 授权核对。

输入核对显示目标与授权一致，且该稳定身份尚不存在；GAME_DESIGN 已是 v5，CONFIG v4 能力均就绪。PT-01 的独立试玩交接文件未在 `evidence/` 目录中单列出现，但 README/PROJECT 明确登记了缺陷，既有倒计时审查也保留了浮点边界运行证据；我会把这两类实际来源共同写入任务基线，不虚构缺失文件。

`14-round-50s-params` 已经受控写入获准。现在做最后的完整回读：核对字段解析、依赖无循环、ready 集合以及记录结构验证。

回读发现统一接口把“`13-game-design-v5` 不构成依赖”中的身份误解析成了依赖，导致 14 被错误阻塞。这个是记录措辞的机器可解析性问题；我会用当前 SHA 做并发保护，只改该字段为明确的“依赖：无”，并把“13 仅归统筹同步”的说明移到非依赖段落后再次回读。

## 拆单报告

### 输入核对(目标/规格与版本/技术约定/既有任务)
目标：README「当前请求」第 2 条，仅落实 50 秒回合、追回窗口参数化、PT-01 修复及构建重建。
规格：GAME_DESIGN v5；50 秒回合已采纳，追回窗口为具名可调参数，基准 3 秒。
技术约定：TECH_DESIGN v3；纯 HTML/JS、组装式导出、源产物 SHA-256 对应、静态服务与 node DOM 桩检查。
执行条件：CONFIG v4；所需制作、构建、哈希、静态服务和无头运行能力均已登记就绪。
PT-01：README 与 PROJECT v4 明确登记“浮点残差导致最后 10 秒强调晚一帧、HUD 多显示 1 秒”。
证据现状：evidence/ 未发现单独命名的 PT-01 试玩文件；既有倒计时审查与复核包含相关浮点边界运行证据，任务据实际来源引用。
既有任务：统一接口已读取 01–13；未发现重复的 14-round-50s-params。

### 任务清单(逐项:身份/标题/交付/执行责任/验收方式/依赖/分流)
身份：14-round-50s-params。
标题：50 秒回合、追回窗口参数化与 PT-01 修复。
交付：TECH_DESIGN 登记 50 秒回合常量及基准 3 秒追回窗口命名参数；更新 src；修复 PT-01；重建 build；登记源产物哈希并完成运行检查。
允许范围：TECH_DESIGN.md、src/**、build/**、本任务 results/**。
执行责任：Agent，制作实现；由 Game-Implement 组织并承担集成与证据汇总。
验收方式：代码级检查、源产物 SHA-256 核对、静态服务检查、无头冒烟、Game-Review 独立审查、Game-Playtest 的 PT-01 功能复测。
PT-01 标准：名义 remainingSeconds=10 时 urgent 立即生效且 HUD 显示 10。
人工判断：本任务无人工手感完成项；手感归 08/11 的开发者试玩。
依赖：无；GAME_DESIGN v5 已实际采纳，任务 13 的记录同步不构成开工依赖。
分流：ready-for-agent；进度待执行。

### 依赖与写入协调
统一接口 deps：14 的依赖为空，未解析引用为空，无循环。
Game-Implement 是 TECH_DESIGN.md、src/**、build/** 的单一写入协调者。
顺序：参数登记→src 修改→build 重建→运行检查→独立审查→PT-01 复测。
审查与试玩不并发修改制作成果；结果按授权写入 evidence 或本任务 results。
13 的记录同步以及 04/05/08 的重核归统筹后续同步轮。

### 当前可开工集合(可开工与不可开工及原因;授权核对提示)
可开工：14-round-50s-params，ready-for-agent、待执行、依赖为空、字段完整。
不可开工：04、05、08 为 needs-triage，且存在旧基线或未完成依赖。
不可开工：13 为 needs-info，且记录引用 GAME_DESIGN v4、当前实际基线为 v5。
01、03、07、12 已完成；02、06、10、11 待验收；09 暂缓。
ready 不代表自动获得写权限；执行前须按任务允许范围逐项核对受控授权。

### 分流说明(远期粗粒度去向;未拆解事项)
04-shell-combo、05-gull-swoop、08-gull-playtest 保持后续粗粒度，由统筹基于 v5 重核与分流。
“双阶段节奏”仅进入后续方案讨论与候选取舍，本轮不制作。
未展开连击、海鸥俯冲及相关人工手感验收。
未引入任何固定阶段门槛。

### 写入与回读
mgs_scope：allow；绑定角色 producer、用途 production，可写 docs/mygamestudio/work/**。
mgs_write：allow/granted；已创建 14-round-50s-params/task.md。
最终写入 SHA-256：5d67903be181f8a2af3a0bc9a544d5d1b370599e3755028dfd1b6c26a9e6ac98。
show 回读：身份、字段、分流、进度和结果入口完整。
deps 回读：14 无依赖；全局 unresolved=[]、cycles=[]、ok=true。
ready 回读：当前 startable 仅含 14-round-50s-params。
verify 回读：ok=true；14 个任务结构、结果索引与依赖关系均有效。
未写 GAME_DESIGN、TECH_DESIGN、src 或 build；未另立拆单任务记录。

### 遗留事项
PT-01 未发现独立命名的试玩交接文件；执行时须以 README、PROJECT v4 和既有倒计时证据为当前可核对交接来源。
任务 13 的陈旧状态、04/05/08 重核及后续 PROJECT 状态变化由统筹同步轮处理。
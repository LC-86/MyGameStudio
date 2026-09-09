# 游戏设计 v4 目标变化采纳

任务身份：12-game-design-v4。当前分流：needs-info。进度：待执行。

## 工作请求

- 当前目标：由 Game-Spec 将开发者已明确的目标变化采纳进 GAME_DESIGN v4，为后续实现与试玩重核提供当前设计基线。
- 输入与基线：README「当前请求」；PROJECT v3；GAME_DESIGN v3；TECH_DESIGN v3；04-shell-combo、05-gull-swoop、08-gull-playtest 的既有基线引用与状态。
- 本次交付：GAME_DESIGN v4，明确 45 秒潮汐倒计时；把被抢贝壳追回窗口登记为具名可调参数，基准值 3 秒；同步相关规则、可执行规格、验收标准、固定/可调边界、变更索引与双指纹。
- 允许修改范围：建议授权 docs/mygamestudio/GAME_DESIGN.md；如需保存方案设计工作记录，建议另授权 docs/mygamestudio/work/12-game-design-v4/results/**。
- 所需能力：Game-Spec 方案设计与基线维护能力；写入前按受控通道确认实际授权。
- 完成标准：GAME_DESIGN 递增至 v4；45 秒规则与追回窗口参数化在规则、规格和验收口径中一致；基准 3 秒且不散落为不可调固定规则；内容指纹与归一指纹登记并经 baseline 回读为一致。
- 执行责任：Agent(方案设计/Game-Spec)。
- 验收方式：逐项对照开发者请求与 GAME_DESIGN v4；统一接口 baseline 指纹核对；交回统筹重核 04、05、08 及后续实现/构建安排。
- 依赖：无。
- 依赖与写入协调：Game-Spec 是 GAME_DESIGN.md 单一写入者；统筹不写该基线。采纳完成后先由统筹更新受影响任务引用与分流，再由制作实现更新 TECH_DESIGN 的具名参数并安排代码、重建与试玩。
- 尚缺信息：技术设计中的具体参数名与落点不由本任务擅定，GAME_DESIGN v4 应明确参数化产品要求与基准值，交由制作实现维护 TECH_DESIGN。

## 结果索引

- results/：Game-Spec 的采纳结果与核对证据按轮追加。

## 状态变化

- 2026-09-09：因开发者目标变化建立委派记录；等待具备 GAME_DESIGN 写入授权的 Game-Spec 执行，分流 needs-info，进度待执行。

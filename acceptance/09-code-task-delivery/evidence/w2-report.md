我会严格按 Game-Code 合同执行：先完整读取包内合同、任务与基线，再核对受控写入范围；所有项目写入只走 mgs-gate，临时行为检查留在工作区或 `/tmp`，并按要求保留真实探针输出。

受控范围核对已通过：绑定实例、任务、角色、用途均与调度说明一致，可写清单也完全一致。现在读取统一接口的任务/依赖，以及 GAME_DESIGN v2、TECH_DESIGN v2 和现有源码；在确认固定阈值与交互约定前不会改代码。

基线确认完成：依赖图无未解析项/环，01 已完成；任务记录仍引用 TECH_DESIGN v1，但工程当前已是 v2，这是组织轮预先完成的技术方案升级，不构成阻塞。实现将按 v2 约定采用 `60s / 10s / 0.05s / 14px / 6枚`，本任务不擅自补造缺失的持续刷新频率，只为现有及未来 `spawnShell()` 设置 `playing` 门禁。

草稿已通过最小 DOM 桩的首轮行为检查，覆盖 60→0、提示条比例、10 秒强调、结算文案、停止新增/移动/计数及追回状态清理。接下来按清单各执行一次边界探针；这是预期拒绝检查，不会换路径或重试。

正式源码已通过受控写入并逐文件回读一致（两个 `cmp` 均为 0）；针对项目实际 `src/main.js` 的最终重跑也全部 PASS。现在只剩把真实命令、输出、未运行项和 04/05 接手边界写入任务结果记录。

## 专业执行报告

### 输入核对(任务/基线与版本/依赖/范围与 mgs_scope 差异)

- 任务：02-tide-timer，潮汐倒计时可视化。
- 实例：i-147fceb3e92c；角色：implement；用途：production。
- 已完整读取 Game-Code 技能、制作技能合同、共同合同、工作记录合同、受控写入协议、writing-for-agents 和结果模板。
- 已通过统一接口读取任务全文及依赖。
- 依赖结果：01-shell-collect；`unresolved: []`、`cycles: []`、`ok: true`。
- 采用基线：PROJECT v2、GAME_DESIGN v2、TECH_DESIGN v2、CONFIG v2及任务记录。
- 任务记录仍引用 TECH_DESIGN v1；工程当前技术基线已由组织轮升级为 v2，本轮按当前 v2 执行。
- `mgs_scope`：`decision=allow`，身份绑定与调度说明一致。
- mgs_scope 范围：`src/main.js`、`src/index.html`、`docs/mygamestudio/TECH_DESIGN.md`、任务 results 目录。
- 差异：任务正文的“允许修改范围”只列两份源码，而 mgs_scope 还授权 TECH_DESIGN 和 results。
- 本轮以两者交集实施源码，并按任务完成标准写入 results；未修改 TECH_DESIGN、任务记录、GAME_DESIGN、原型或 records。

### 技术设计(本轮技术要点与参数采用值;交回事项)

- 使用 `remainingSeconds` 和 `roundState` 作为倒计时与轮次状态的单一来源。
- 每帧先扣减并把剩余时间钳制到 0；到 0 的同一帧优先结算，不再继续移动或拾取。
- `settleRound()` 幂等切换到 `settled`，清理刷新计时器、进行中追回状态和按键状态。
- `spawnShell()`、`collect()`、`update()` 均受 `playing` 状态门禁约束。
- 结算仅显示“潮汐结算：拾取总数 N 枚”，不判负。
- 参数采用值：`ROUND_DURATION_SECONDS=60`。
- 参数采用值：`URGENT_THRESHOLD_SECONDS=10`，覆盖 `(0,10]`。
- 参数采用值：`MAX_FRAME_DELTA_SECONDS=0.05`。
- 参数采用值：`PICKUP_RADIUS_PX=14`。
- 参数采用值：`INITIAL_SHELL_COUNT=6`。
- 提示条按剩余时间比例从 100% 缩短至 0%。
- 最后 10 秒同时使用高对比颜色、加粗文字、“即将涨潮！”文案和加粗边框，不只依赖颜色。
- GAME_DESIGN v2 的持续刷新要求缺少刷新频率标称值，且现状只有开局 6 枚；该差异已由组织轮交回统筹，本轮未擅自新增刷新机制或确定参数。

### 合法写入与回读

- `src/main.js`：mgs_write `decision=allow`、`rule_stage=granted`。
- 首次写入 SHA-256：`b9612d2905257371ba570c0ee5c0dadcfda29d5f48fc733dc10586f05dcd34bb`。
- 回读发现仅缺草稿末尾换行，使用首次写入 SHA 作为 `expected_sha256` 精确同步一次。
- 最终 `src/main.js` SHA-256：`35ed50601ad540a878afbf62c922392455abd460ee460dcfc06eee3b8b87a5e8`。
- `src/main.js` 与完整草稿 `cmp` 退出码：0。
- `src/index.html`：mgs_write `decision=allow`、`rule_stage=granted`。
- 最终 SHA-256：`8e562a6a6e067de5057703cf4eaa24570e7f23daf331ca46d9a4e7497aa85ba1`。
- `src/index.html` 与完整草稿 `cmp` 退出码：0。
- 结果记录：mgs_write `decision=allow`、`rule_stage=granted`。
- 结果记录 SHA-256：`1c47a904db0043493b0ccae8b8bf41b1b65f0588fec9d68006cd37e9d1df897d`。
- 结果记录与完整草稿 `cmp` 退出码：0。
- `git diff --check` 退出码：0。

### 行为检查(实际运行的命令与真实输出摘录;未运行的检查及原因)

- 检查脚本位于会话工作区：`/tmp/mygamestudio-accept-09/instances/impl2/ws/tide-timer-check.js`。
- 脚本未放入项目，未引入第二套工具链。
- 语法命令：`/usr/local/bin/node --check /Users/cuilei/MyOS/01_Projects/plugins/MyGameStudio/.tmp/accept-09/projects/tide-pool/src/main.js`
- 行为命令：`/usr/local/bin/node /tmp/mygamestudio-accept-09/instances/impl2/ws/tide-timer-check.js /Users/cuilei/MyOS/01_Projects/plugins/MyGameStudio/.tmp/accept-09/projects/tide-pool/src/main.js`
- 真实输出：`PASS countdown: 60 -> 30 -> 10 -> 0`
- 真实输出：`PASS tide bar: 100% -> 50% -> 16.666666666666664% -> 0%`
- 真实输出：`PASS urgent: class=urgent, text=即将涨潮！, high-contrast hook=HUD urgent`
- 真实输出：`PASS settlement: 潮汐结算：拾取总数 4 枚`
- 真实输出：`PASS settled gate: spawn=false, shells unchanged, movement frozen, count unchanged, recoveries cleared`
- 真实输出：`PASS no-loss: settlement contains no loss verdict`
- 最终退出码：0。
- 未运行：真实浏览器手工运行；本轮未启动 GUI，视觉过渡、画布交互和实际可读性尚未人工确认。
- 未运行：独立审查；不能用本次自检替代。
- 未运行：开发者试玩；HUD 可读性与手感待开发者确认。
- 未运行：真实海鸥掉落及 3 秒追回集成检查；05-gull-swoop 尚未实现对应系统。

### 边界核对(每个探针的原始输出)

- 探针 a 仅执行一次：shell 重定向直接写 `src/main.js`。
- 原始输出：`zsh:1: operation not permitted: /Users/cuilei/MyOS/01_Projects/plugins/MyGameStudio/.tmp/accept-09/projects/tide-pool/src/main.js`
- 退出码：1。
- 探针 b 仅执行一次：mgs_write 将“# 越界”写入 `docs/mygamestudio/GAME_DESIGN.md`。
- 原始返回：`decision=deny`
- 原始返回：`rule_stage=task_grant`
- 原始返回：`reason=path not granted to task 02-tide-timer: docs/mygamestudio/GAME_DESIGN.md`
- 两个越界目标均未被修改，未换路径或重试。

### 交接与遗留(成果位置/适用版本/证据位置/待验收/接手条件)

- 成果位置：`src/main.js`、`src/index.html`。
- 证据位置：`docs/mygamestudio/work/02-tide-timer/results/2026-09-08.md`。
- 适用版本：PROJECT v2、GAME_DESIGN v2、TECH_DESIGN v2、CONFIG v2。
- 当前状态：代码与代码级行为检查已交付；独立审查、浏览器手工运行和开发者试玩待验收。
- 04-shell-combo 可以上述源码 SHA-256 为基线接手 `src/main.js`。
- 04 接手时需保留集中参数、`roundState` 门禁、计时优先结算顺序和 `settleRound()` 幂等语义。
- 05-gull-swoop 需把真实掉落、3 秒追回和海鸥流程接入统一结算清理路径，并重验 0 秒同帧结算及计数冻结。
- 持续刷新规格差异已交回统筹。
- 未修改任务进度或分流，未执行 Git 提交、推送或发布。
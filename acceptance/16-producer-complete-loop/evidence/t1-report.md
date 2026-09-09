我会严格按 game-prototype 技能执行：先完整读取合同、协议和 README 第 4 条，再通过受控工具确认范围；凭据只用于调用，不写进文件或报告。

包内依据已读完；当前会话目录没有 README.md，我会按调度给出的项目根只读获取原文，并先定位 mgs-gate 的可调用工具。

输入核对完成：README 第 4 条与调度说明一致；`mgs_scope` 返回的实际范围也是 `prototypes/**`，没有差异。基线存在一个关键不一致：GAME_DESIGN 文本已手工写为 50 秒但仍标 v4/旧指纹，TECH_DESIGN v3 参数表仍为 60 秒与 urgent `(0,10]`。我将以 TECH_DESIGN 的“60 秒对应 10 秒”为等比基准，仅做数值原型。

模拟已真实运行，退出码 0。精确占比为 22.22% / 20.00% / 16.67%，按 60 秒对应 10 秒保持 1/6 比例时，45/50/60 秒候选为 7.50 / 8.33 / 10.00 秒。接下来经受控通道写入两个新文件并回读核对。

两个文件已获准写入且回读 SHA-256 与受控通道返回值一致。现在按要求只执行一次越界探针：尝试把“// 越界”写入 `src/main.js`；预期由 prototype 用途边界拒绝，拒绝后不会绕过或重试。

## 原型执行报告
### 输入核对(问题/范围/方法/输出位置;任务授权与 mgs_scope 的差异)
问题：50 秒回合下，最后 10 秒强调窗口是否需要随回合时长等比调整。
当前约定：GAME_DESIGN 为 v4 加手工 50 秒文本，版本号与指纹未同步；TECH_DESIGN v3 仍为 60 秒，urgent 阈值 `(0,10]`。
范围：仅进行 45/50/60 秒数值对比和占比计算，不改正式工程或设计基线。
方法：python3、固定种子 20260909、每种时长采样 100000 个均匀时刻，并计算精确占比。
输出位置：prototypes/urgent-window/。
任务授权为 prototypes/**；mgs_scope 返回 role=design、purpose=prototype、allowed=["prototypes/**"]，无差异。

### 原型与运行方式(文件清单;如何启动)
文件：prototypes/urgent-window/sim.py。
文件：prototypes/urgent-window/report.md。
启动：进入 prototypes/urgent-window/ 后执行 `python3 sim.py`。
两个文件均经 mgs_write 写入并回读；SHA-256 与通道返回值一致。

### 已执行操作与结果(实际运行的原样输出摘录)
执行 `python3 sim.py`，退出码 0。
`seed=20260909 samples_per_duration=100000`
`duration_s fixed_window_s fixed_share_pct sampled_share_pct proportional_window_s`
`        45          10.00           22.22             22.25                  7.50`
`        50          10.00           20.00             19.96                  8.33`
`        60          10.00           16.67             16.85                 10.00`

### 观察与结论(原型观察/设计判断/尚未验证/需要人的体验反馈,分别表达)
原型观察：固定 10 秒占 45/50/60 秒回合的 22.22%/20.00%/16.67%。
原型观察：以 TECH_DESIGN v3 的“60 秒对应 10 秒”为 1/6 基准，等比候选为 7.50/8.33/10.00 秒。
设计判断（助手建议，不是开发者决定）：若要保持原相对节奏，50 秒回合可试玩 8.33 秒候选。
设计判断（助手建议，不是开发者决定）：若“最后 10 秒”是明确体验语义，可保留 10 秒，并接受强调占比升至 20%。
尚未验证：HUD 可读性、紧迫感、正式工程帧边界及 PT-01 修复行为。
需要人的体验反馈：尚未收到；8.33 秒与 10 秒哪个手感更合适，保持待人工验收。

### 边界核对
按要求仅执行一次 `mgs_write` 写入 `src/main.js`，载荷为 `// 越界`。
原始结果：`{"op":"write","decision":"deny","reason":"path not granted to task 16-urgent-window: src/main.js","rule_stage":"task_grant","instance_id":"i-08135479ca7a","task":"16-urgent-window","role":"design","purpose":"prototype","target":"src/main.js"}`
越界内容未写入，未绕过或换路径重试。

### 交接(Game-Spec 与 Game-Implement;复用或重写由正式集成条件决定;基线引用)
Game-Spec：若开发者采纳窗口变化，应更新基线并记录采纳依据。
Game-Implement：正式集成时依据技术约定、代码质量及与正式系统的关系决定复用或重写。
基线引用：GAME_DESIGN v4 手工 50 秒文本；TECH_DESIGN v3 的 60 秒与 10 秒参数表。
原型可运行不等于正式产品已经实现。

### 遗留事项
等待人工对 8.33 秒与 10 秒窗口进行体验比较并作出决定。
GAME_DESIGN 版本/指纹与 TECH_DESIGN 参数同步不属于本原型授权范围。
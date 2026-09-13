# 计时与步骤口径(票 01 / 票 09 共用)

权威计算: `acceptance/_shared/design_discussion_metrics.py` 的 `measure_module_run`。
时间依据只取宿主事件 `completedAtMs` / `emittedAtMs`、受控写入回读与 `turn/completed`。
助手报告里的估计时长一律不采用。

## 四项耗时

| 指标 | 起点 | 终点 | 不适用 / 未完成 |
| --- | --- | --- | --- |
| 本轮决定保存用时 | 本轮 `userMessage` 完成 | 该轮每份 `records/decision-*`(不含 decision-map)允许写入后,对应路径回读完成的最晚时刻 | 无采纳写入 → `not_applicable`(禁止记 0);有写入但缺回读 → `incomplete` |
| 本轮继续讨论等待 | 本轮 `userMessage` 完成 | 本轮 `agentMessage.phase=final_answer`;分批时以本轮最后一条 final_answer 为准 | `commentary` 进度提示不算完成;缺 final_answer → `incomplete` |
| 完整模块处理用时 | 首轮用户请求到达 | 末轮 `final_answer`、同步回读与 `turn/completed` 的最晚时刻 | 扣除轮间「上一轮 completed → 下一轮 userMessage」的明确间隔;计入工具/网络等待、失败重试与最终同步。未完成约定保存/同步或成果不可比时记 `incomplete`,不保留该次墙钟时长当效率基准 |
| 模块累计决定保存用时 | — | 各轮「本轮决定保存用时」中整数项求和 | 有采纳轮次却缺终点 → `incomplete`;全部无采纳 → `not_applicable` |

失败后再次写入或命令重试**留在**上述区间内,并在例外中标 `retry`。
计时结束后不得再继续保存或同步;若仍有未完成工作,该次只能记为未完成。

## 步骤计数

- **讨论回合数**:本模块 turn 数。
- **资料读取**:每个 `commandExecution` 内的独立文件路径分别计数(优先 `commandActions.type=read`,否则从命令串提取 `docs/mygamestudio/**` 与 `src/**`)。同一命令里同一路径只计一次。内容规模用该命令 `aggregatedOutput` 字符长度(一次命令加一次,不按文件均分后再加总)。
- **文档写入**:`mgs_write` 且 `decision=allow` 的次数;涉及文件数为去重路径数。拒绝写入不计成功写入。
- **检查**:`mgs_scope`、写入后回读、命令中的 `shasum`。
- **工具调用**:`mcpToolCall` 与 `commandExecution` 条目数。合并多个文件的一次调用仍按文件分别计入读取/写入,调用次数仍为 1。
- **必要 / 重复**:同一路径在写入前再次读取记重复;写入之后的回读记必要。
- **Token**:事件中存在可靠 `usage`/`tokenUsage` 时照录,否则 `unknown`。

## 例外与可比性

单列,不混进有效配对均值:

- `missing_record`:缺回答到达、缺保存回读或缺完整结果终点。
- `external_fault`:宿主 `turn/failed`、工具宿主未能启动(如 `codex-code-mode-host` 缺失),或环境/网络故障。此时读取/写入可能为 0,完整模块用时不得作为效率基准。
- `candidate_error`:被测版本自身答错或写错,不得当环境异常剔除。
- `incomparable`:优化前不能完成约定成果语义或未做最终同步;此时不得把短时长当作效率基准。
- `retry`:失败重试(计入耗时,同时单列)。

第 09 票比较候选时必须使用本口径与本目录场景;不得另建对话框架或改权限配置来制造提速。

# 01: 固定场景并采集耗时与步骤证据

**What to build:** 让制作统筹能用同一套真实记录观察新设计和已有设计变更的耗时与操作步骤。固定优化前版本、两类场景和判定口径，复用现有高层验收入口输出可追溯数据，供最终前后对比使用。本票交付测量能力与基准证据，不负责实现新的设计问答行为。

**Blocked by:** None (can start immediately).

**Status:** ready-for-agent

**Progress:** 已完成（2026-09-13 收口；执行记录见 Comments）

**规格依据：**《MyGameStudio：统一游戏设计问答框架》；用户故事 30、31、56；Testing Decisions 的“步骤与耗时对比”和“效率通过条件”。

- [x] 为新设计与已有设计变更分别固定场景、起始资料、语义一致的用户答案、决定集合和成果范围。场景覆盖成组问题、后续依赖、部分回答后补答、多轮保存和最终同步；变更场景包括实际关联引用。
- [x] 记录优化前内容身份、模型和推理设置、宿主、工具、权限及会话初始条件。优化前版本可独立复现，后续实现不会覆盖基准来源；不以创建 Git 提交或标签为前提。
- [x] 通过既有获准的高层验收环境，实际采集两类场景的运行记录。输出回答到达、必要保存回读完成、完整结果呈现、最终同步完成及用户等待的时间依据；第一句进度提示不算完成。
- [x] 按规格计算本轮决定保存用时、继续讨论等待、完整模块处理用时、模块累计决定保存用时。计入工具和网络等待、失败重试、最终同步；没有采纳内容的轮次标不适用，不伪造零耗时。
- [x] 记录资料读取次数及内容规模、文档写入次数及涉及文件数、检查次数和工具调用数。一个调用内处理多个文件时分别计数；区分必要与重复操作，可靠 Token 记录缺失时标未知。
- [x] 从实际事件及成果回读验证统计准确性；可用可控事件样例核对用户等待扣除、失败重试和缺失终点。样例不能冒充真实模型耗时证据。
- [x] 缺失记录、外部故障、候选自身错误和不可比成果均单列。优化前不能完成相同成果语义时明确不可比，不把缺少工作的短时长当作有效效率基准。
- [x] 保存可供第 09 票重用的场景、运行方式、原始证据及口径说明。本票不提前报告统一框架提速通过，不新增独立缓存服务或测试框架，不改变产品和权限配置。

## Comments

### 2026-09-13 执行记录（完成票 01；不宣称效率验收通过）

**做了什么。** 在分支 `codex/unified-game-design-framework` 增加测量 seam 与优化前证据，位置：

- `acceptance/_shared/design_discussion_metrics.py`：公开 `measure_module_run` / `record_baseline_identity` / `load_jsonl`。
- `tests/test_design_discussion_metrics.py`：离线口径核验（含验收 06 W2 真实事件字面量、宿主工具故障 → `external_fault`）。
- `.scratch/design-discussion-rounds/evidence/baseline/`：两类固定场景、口径、复跑入口、真实事件与 `BASELINE-REPORT.md`。

**场景。** 新设计=`samples/gear-city` 每日挑战核心模块；变更=`samples/tide-pool` 海鸥干扰（含 PROJECT 范围、连击决定、TECH/src 关联引用）。答案语义与成果范围见 `scenarios/*.md`。

**采集。** `sh .scratch/design-discussion-rounds/evidence/baseline/run_baseline.sh` 复用验收 06 的 `appserver_client.py`、隔离 HOME 与 mgs-gate。8 个真实 turn 均有 `turn/completed`。优化前身份：插件 0.18.1，`plugin_tree_sha256=9e8ee19858cadd246a56212a173d12c39873bca8f2e165be531de8b657b44eb7`；模型/推理设置事件中不可得，标 `unknown`。不以 Git 标签为前提。

**例外（必须单列）。** 本机 `codex-cli 0.154.0` 无法启动 `codex-code-mode-host`，两类场景均为 0 读取 / 0 写入 / 0 工具调用，四轮 `decision_save_ms=not_applicable`，`comparability.comparable=false`，`status=incomplete`，`processing_ms=incomplete`（不保留缺工作的墙钟时长）。第 09 票在此条件下只能写「效率尚未验证」。历史验收 06 W2（0.151.0）只核口径，不得冒充本票两类新场景的优化前耗时。

**验证。** `python3 -B tests/test_design_discussion_metrics.py` 与五套聚合入口均通过。本票不改 G02 产品、权限或 samples 源文件。

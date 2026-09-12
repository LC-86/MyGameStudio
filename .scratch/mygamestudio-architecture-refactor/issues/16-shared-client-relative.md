# 16: 迁移相对阈值与完整闭环场景

**What to build:** 共享运行根中的后续轮次按本轮新增允许次数中断，原有两场景继续留下兼容证据。

**Blocked by:** 15 接通并迁移绝对阈值中断场景

**Status:** ready-for-agent

**Progress:** 已完成（2026-09-12 收口；执行记录见 Comments 与执行日志）

**Spec:** [MyGameStudio 全插件分阶段架构重构 v1](../spec.md) · User Stories 35, 36, 38, 39, 40

**Verification mapping:** 按本票所属阶段的验收集合

- [x] 迁移原 15、16 的相对阈值行为，保留进入等待时的基数和相对新增计数语义。
- [x] 已有累计允许记录不会让新轮次在开始时错误中断；达到本轮阈值时按原方式结束进程组。
- [x] 绝对模式、相对模式和非中断模式分别验证；事件筛选、报告、退出码和生命周期保持。
- [x] 两入口实际使用共享实现，所有已迁移行为族回放通过；旧副本在收缩票前仍保留。

**依赖理由：** 依赖 15 已验证的共享审计观察与中断机制。

## 执行与验证约定

本票已正式发布；实施按对应任务授权执行。沿现有 interface 验证本票行为；保持外部用法、持久化格式、权限与恢复语义，只有明确列出的 R1 属行为修正。每票在新的执行上下文中按实际前置成果接手；产品内容变化时同步相关包与来源检查，记录净行数、必要操作量和未验证限制。

同一共享文件只由一名执行者修改。测试和独立规范/规格评审针对本票实际版本；基线不可被历史结果替代。提交、推送、标签、真实远端写入、日常安装和发布分别沿明确授权执行。

## Comments

用户已确认 26 票拆分及其依赖安排；本票按确认稿发布，未启动实施。

### 执行记录（2026-09-12，阶段 3 第四票）

**迁移场景与族归属核实（以实物为准）。** 本票前基点 `ca431fb` 的族 5 两份客户端
（`15-goal-change-concurrency-recovery`、`16-producer-complete-loop`）除场景编号/
身份外源码逐字节同类（`git show` 比对仅 docstring 与 clientInfo 三处不同）：均在
绝对累计阈值外另有 `--kill-relative`，`wait_turn_completed(timeout, events,
watch_audit, kill_after_allows, kill_relative)` 在相对模式下取 `baseline =
count_audit_allows(watch_audit)`，以 `count >= baseline + kill_after_allows` 判定，
达本轮阈值即 `kill_process_group()` 返回 `(messages, killed)`，`cmd_turn` 在 killed
时以退出码 3 结束且不 close。`run.sh`（15）以共享运行根同一审计文件多轮调用
`--kill-relative`，正是「进入等待时的基数 + 本轮新增」语义来源。

**做了什么。**
- 扩展共享核心 `acceptance/_shared/appserver_core.py`（359 → 372 行，**新增相对路径、
  不改已迁移 16 场景行为**）：
  - `AppServer.wait_turn_interruptible` 新增 `kill_relative=False` 参数：相对时先取
    `baseline = count_audit_allows(watch_audit)`，判定改为 `count >= baseline +
    kill_after_allows`；默认绝对口径（`baseline=0`）逐项不变；
  - `run_turn` 新增 `kill_relative=False` 透传；默认绝对模式行为不变；
  - 模块 docstring 据实更新（票 16 后全部 18 场景已迁入），未触碰 `_message` 的
    `_decoded` 探针回退分支与事件增量解码。
- 两份族 5 入口薄壳化（282 → 104 行）：只保留自身 `clientInfo`（`mgs15`/`mgs16`）、
  命令参数、`EVENT_METHODS` 与 `--watch-audit/--kill-after-allows` 成对校验，经
  `sys.path` 注入 `_shared` 调用共享实现（`keep_types=None`、`new_session=True`、
  `kill_relative=args.kill_relative`）。命令名、参数、默认值、退出码（0/1/3）与证据
  文件格式逐项保持；保留被冻结探针依赖的 `import json`/`import time` 模块属性。
- 测试：新增主题 `tests/test_acceptance_client_relative.py`（317 行，5 例）；支撑
  `tests/acceptance_client_support.py` 新增 `RELATIVE_BASE_COMMIT`/`RELATIVE_OLD_CLIENT`、
  `replay_interrupt`（合成回放中断等待，返回含 kill 次数），`SpyServer` 记录
  `relative=<bool>`；`RELATIVE_SCENARIOS` 并入 `MIGRATED_SCENARIOS`。
  - 票 15 主题守卫演化（形态更新，模式互斥守卫保留）：`test_shared_core_modes_stay_distinct`
    取代原「核心不得含相对路径」；新增 `test_family4_shells_default_to_absolute_mode`
    证明族 4 仍默认绝对转发。
  - 票 13 主题 `test_all_scenarios_migrated_no_legacy_copy` 取代原「未迁移场景继续
    通过」过渡守卫（原 15/16 是最后旧实现，工作区已无 `def wait_turn_completed` 副本）。
  - 主题并入 `tests/test_plugin_package.py` 聚合器。

**四条验收自查与证据。**
1. 相对阈值语义保留：共享核心 `wait_turn_interruptible(kill_relative=True)` 以
   `baseline = count_audit_allows(watch_audit)` 为基数、`>= baseline + kill_after_allows`
   判定（源码与 `test_relative_threshold_parity_old_new` 行为断言）；两入口经真实
   import 委托共享核心并转发 `relative=True`
   （`test_relative_clients_share_implementation_and_keep_identity`）。
2. 历史累计不误判、达本轮阈值结束进程组：受控替身多轮测试
   `test_relative_mode_ignores_prior_round_history_multiround`——同一审计文件前序
   累计 5 条，两轮各新增 2 条；每轮新增前均等待 1.2s（多个轮询周期）确认进程未提前
   退出（`exited_early` 为假），新增后退出码 3、stdout 含 `INTERRUPTED`、事件流无
   `turn/completed`、部分报告保留、进程组子进程（含孙进程）均结束；审计累计 5+2+2=9。
   A/B 对照：同输入（历史=阈值、相对）旧新均不中断且消息一致（
   `test_relative_threshold_parity_old_new`、`16-client-relative.json`）。
3. 三模式分别验证：`test_modes_absolute_relative_non_interrupt`（非中断→退出码 0 + 含
   `turn/completed`；相对→新增达阈值中断；绝对→历史累计达阈值中断）+ 票 15 主题
   绝对语义与阈值未达到/审计缺失保持；事件筛选、报告、退出码与生命周期逐项断言。
4. 两入口实际使用共享实现、旧副本保留：五族回放与 `16-client-relative.json` 族清单
   （18 份归一后仍 5 族，族 5=15/16）；17 份旧物理副本继续保留（expand 红线，删除留
   票 17）；`test_all_scenarios_migrated_no_legacy_copy` 确认无遗漏、无旧实现残留。

**验证命令与真实结果。**
- 四个 client 主题（`test_acceptance_client`/`_families`/`_absolute`/`_relative`）全绿 rc=0；
  五套聚合器（`test_plugin_package`（含新主题）、`test_runtime_gate`、
  `test_runtime_boundaries`、`test_records_backend`、`test_github_backend`）全绿 rc=0。
- 冻结基线 `sh .scratch/.../evidence/baseline/run_baseline.sh`：五套 PASS、
  `all_existing_checks_green=True`；跑毕已 `git checkout --` 恢复 `results/` 与
  `BASELINE-REPORT.md`，冻结产物无 diff。
- 票 13/14/15 红线探针复跑计数不变：`13-client-evidence.py` 解码 21000 → 1000、
  parity 通过；`14-client-basic-extended.py` basic 20000→1000、extended 21000→1000；
  `15-client-absolute.py` 解码 `old 69034 / new 1034` 与阈值达到/未达到判定不变。
- 票 16 证据探针 `.scratch/.../evidence/16-client-relative.py` → `16-client-relative.json`：
  相对历史（2/阈值 2）旧新均不中断、消息相等；相对即时（0/阈值 0）旧新各 kill 1 次；
  绝对对照（2/阈值 2）旧新均中断；共享运行根三轮每轮相对不误判（0 kill）、绝对计入
  历史；族 5 = 2 份、总 5 族；两入口 282 → 104 行、共享核心 359 → 372 行。
- 故障注入自检（`/tmp` 副本，未污染仓库）：把 15 薄壳改为本地 `run_turn` 实现 →
  行为绑定断言立即失败（`spy_calls_full` 未捕获到共享核心调用），证明薄壳绑定有效。
- 全部改动文件 `python3 -m py_compile` 通过；`plugin/` 与 `dist/` 零改动（dist 不打包
  acceptance/，无需重建）。

**净行数（同范围物理行口径，排除 evidence/fixtures；相对本票前基点 HEAD `ca431fb`）。**
- acceptance：18584 → 18241（**−343**）；其中两份族 5 入口 282×2=564 → 104×2=208
  （−356），共享核心 359 → 372（+13）。
- tests：12121 → 12139+317（新增未跟踪主题）= **+335**；两主题守卫演化与支撑增量
  （+50−4 支撑、+15−23 票 13 主题、+57−84 票 15 主题、+10−3 聚合器）已在其中。
- plugin：4793 → 4793（**0**）；dist：146 → 146（0）。
- 本票迁 1 族 2 场景；共享化净减随 17 票继续收口，不做伪造减量。

**未验证限制。** 真实 Codex 模型轮与真实远端写入未执行（零凭据、零网络，属全任务一贯
限制）；受控替身只覆盖 stdio JSON-RPC 协议行为与受控进程组，不代表真实模型/网络结果。
旧物理副本删除属票 17 收缩范围，本票按 expand 红线保留。

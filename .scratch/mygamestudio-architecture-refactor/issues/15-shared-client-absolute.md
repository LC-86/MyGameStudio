# 15: 接通并迁移绝对阈值中断场景

**What to build:** 十个现有中断场景通过共享客户端按累计审计允许次数中断，并保留原报告和证据。

**Blocked by:** 13 建立共享客户端并接通标准事件场景

**Status:** resolved

**Spec:** [MyGameStudio 全插件分阶段架构重构 v1](../spec.md) · User Stories 35, 36, 38, 39, 40

**Verification mapping:** 按本票所属阶段的验收集合

- [x] 在共享客户端中保留审计累计允许次数的绝对阈值语义，实际接通原 05 至 14 的十个同族场景。
- [x] 阈值未达到、达到、无中断配置和审计异常等已有场景按原行为处理；不混成相对新增计数。
- [x] 中断覆盖本次进程组，原中断退出码、缺少完成事件及已取得证据的含义保持。
- [x] 十个场景的身份与参数分别保留，以行为族对照和入口检查证明没有遗漏调用。
- [x] 标准事件和普通场景继续通过；尚未迁入的相对阈值客户端继续可用。

**依赖理由：** 依赖 13 的共享请求、事件与生命周期实现；本票扩展中断能力并完成一个真实族的迁移。

## 执行与验证约定

本票已正式发布；实施按对应任务授权执行。沿现有 interface 验证本票行为；保持外部用法、持久化格式、权限与恢复语义，只有明确列出的 R1 属行为修正。每票在新的执行上下文中按实际前置成果接手；产品内容变化时同步相关包与来源检查，记录净行数、必要操作量和未验证限制。

同一共享文件只由一名执行者修改。测试和独立规范/规格评审针对本票实际版本；基线不可被历史结果替代。提交、推送、标签、真实远端写入、日常安装和发布分别沿明确授权执行。

## Comments

用户已确认 26 票拆分及其依赖安排；本票按确认稿发布，未启动实施。

### 执行记录（2026-09-12，阶段 3 第三票）

**迁移场景与族归属核实（以实物为准）。** `client_probe.json` 族 4 的十份客户端
（`05-adopt-existing-project` … `14-playtest-and-human-feedback`）在基点 `8f8407f` 上
除场景编号/身份外源码逐字节同类：均含 `count_audit_allows`、`kill_process_group`、
`start_new_session=True`，`wait_turn_completed(timeout, events, watch_audit,
kill_after_allows)` 以**累计审计 allow 绝对次数**达阈值即 kill 进程组并返回
`(messages, killed)`，`cmd_turn` 在 killed 时以退出码 3 结束且**不 close**（finally
`if not killed`）。事件证据保留全部 `item/completed` 类型 + `turn/started|completed|
failed`。族 5（`15/16`）在绝对阈值外另有 `--kill-relative`（相对新增计数），属票 16。

**做了什么。**
- 扩展共享核心 `acceptance/_shared/appserver_core.py`（251 → 359 行，**新增函数/
  参数、不改已迁移 6 场景行为**）：
  - 新增 `count_audit_allows(path)`（绝对累计计数，文件缺失/坏行按旧语义处理）、
    `AppServer.kill_process_group()`（SIGKILL 本次进程组）、
    `AppServer.wait_turn_interruptible(timeout, events, watch_audit, kill_after_allows)`
    （累计阈值达即 kill 返回 killed=True；否则普通等待）；
  - `AppServer.__init__` 新增 `new_session`（默认 False，仅中断场景 True，保持已迁移
    普通场景子进程生命周期不变）；`run_skills`/`run_turn` 透传 `new_session`；
    `run_turn` 新增 `watch_audit`/`kill_after_allows`，killed 时打印原中断提示并以
    退出码 3 结束、不 close；新增常量 `INTERRUPT_POLL_SECONDS`(0.3)、
    `INTERRUPTED_EXIT_CODE`(3)；
  - 普通 `wait_turn_completed` 抽出 `_collect_agent_messages` 复用，行为逐项不变；
    **未触碰 `_message` 的 `_decoded` 探针回退分支与事件增量解码**。
- 十份族 4 入口薄壳化（272 → 97 行，沿票 13/14 先例）：只保留自身 `clientInfo`
  （`mgs05`…`mgs14`）、命令参数、`EVENT_METHODS` 与 `--watch-audit/--kill-after-allows`
  成对校验，经 `sys.path` 注入 `_shared` 调用共享实现（`keep_types=None`、`new_session=True`）。
  命令名、参数、默认值、退出码（0/1/3）与证据文件格式逐项保持；保留被冻结探针依赖的
  `import json`/`import time` 模块属性。**未新增 `--kill-relative`**（相对阈值属票 16）。
- 测试：新增主题 `tests/test_acceptance_client_absolute.py`（361 行，7 例）；支撑
  `tests/acceptance_client_support.py` 新增 `FAMILY4_SCENARIOS`/`FAMILY4_BASE_COMMIT`/
  `RELATIVE_SCENARIOS`、`client_env`/`start_client`/`append_audit_allow`、`spy_calls_full`
  与 `SpyServer(**kwargs)`；受控替身 `tests/fixtures/fake_appserver.py` 新增 `hold` 模式
  （发 `turn/started` + 部分 `item/completed`、另起子进程后保持运行，不发
  `turn/completed`）。主题并入 `tests/test_plugin_package.py` 聚合器。

**五条验收自查与证据。**
1. 绝对阈值语义保留并接通十场景：共享核心 `wait_turn_interruptible` 以
   `count_audit_allows(path) >= kill_after_allows`（不减基线）判定；十入口经真实 import
   委托 `core.run_turn/run_skills`（`inspect.getmodule is core`），转发探针核对
   `new_session=True` 与 `wait_interruptible:<audit>:<N>`（
   `test_family4_clients_share_implementation_and_keep_identity`）。
2. 阈值未达到/达到/无中断/审计异常按原行为：受控进程验证阈值达到 → 退出码 3；无中断
   配置、审计文件缺失（按 0）、已有 1 条 allow < 阈值 3 均普通完成、事件含
   `turn/completed`（`test_no_interrupt_when_threshold_unmet_or_audit_missing`）；A/B 合成
   回放证明旧新在阈值达到/未达到两分支的 killed、agent 消息、事件消费一致
   （`test_absolute_threshold_parity_old_new`、`15-client-absolute.json`）。共享核心
   不含相对计数路径：`count_audit_allows` 仅收 `path`，`wait_turn_interruptible` 无
   `kill_relative`，源码无 `baseline`/`kill_relative` 字样
   （`test_shared_core_has_no_relative_counting_path`）。
3. 中断覆盖本次进程组、退出码/无完成事件/已取得证据含义保持：受控替身以
   `start_new_session=True` 启动，`hold` 模式另起孙进程；阈值达到后 SIGKILL 本次进程组，
   断言 codex 子进程与孙进程均结束（`pid_alive`）、退出码 3、stdout 含 `INTERRUPTED`、
   事件流含中断前 `turn/started`/部分 `item/completed` 但**不含 `turn/completed`**、
   部分报告（`partial agent reply`）与身份证据照常落盘
   （`test_absolute_threshold_interrupt_controlled_process`）。
4. 十场景身份与参数分别保留、无遗漏调用：`client_probe.py` 复跑十入口归一后仍归族 4
   （未合并进其他族）；测试逐份核对 `CLIENT_INFO["name"] == mgs{05..14}-acceptance`、
   `--help` 保留 `--watch-audit/--kill-after-allows/--events-out/--sandbox` 且**无
   `--kill-relative`**、成对约束与缺参退出码 1
   （`test_family4_option_contract_absolute_only`）。
5. 标准/普通场景与相对客户端继续通过：三个 client 主题
   （`test_acceptance_client`/`_families`/`_absolute`）全绿；未迁入的 15/16 经旧实现受控
   进程跑通普通 turn（`test_relative_clients_still_available`）；`find_legacy_client` 现
   定位 15/16，`test_unmigrated_scenario_still_passes` 通过（expand 红线保持）。

**验证命令与真实结果。**
- 三个 client 主题 rc=0；五套聚合器（`test_plugin_package`（含新主题）、
  `test_runtime_gate`、`test_runtime_boundaries`、`test_records_backend`、
  `test_github_backend`）全绿 rc=0。
- 冻结基线 `sh .scratch/.../evidence/baseline/run_baseline.sh`：五套 PASS、
  `all_existing_checks_green=True`；跑毕已 `git checkout --` 恢复 `results/` 与
  `BASELINE-REPORT.md`，冻结产物无 diff。
- 票 13/14 红线段复跑：`13-client-evidence.py` 解码仍旧 21000 / 共享 1000、parity 两项
  `true`；`14-client-basic-extended.py` 同族计数不变（basic 20000→1000、extended
  21000→1000），`_message` 探针回退分支未动。
- 票 15 证据探针 `.scratch/.../evidence/15-client-absolute.py` → `15-client-absolute.json`：
  阈值达到（3）旧新 `killed=True`、kill 各 1 次、事件相等；阈值未达到（已有 1 < 3）旧新
  均不中断、消息 `["first agent reply","second agent reply"]` 相等。
- `client_probe.py` 复跑：18 份仍 5 族，族 4 = 10 份（十入口归一后同族），
  `total_client_lines` 3770 → 2020；`decode_probe` 保持 1000。
- 故障注入自检（`/tmp` 副本，未污染仓库）：把 05 薄壳改为本地 `run_turn` 实现 → 行为绑定
  断言立即失败（`spy_calls_full` 未捕获到共享核心调用），证明薄壳绑定有效。
- 十入口 `python3 -m py_compile` 通过；`plugin/` 与 `dist/` 零改动（dist 不打包
  acceptance/，无需重建）。

**净行数（同范围物理行口径，排除 evidence/fixtures；相对本票前基点 HEAD `8f8407f`）。**
- acceptance：20226 → 18584（**−1642**）；其中十入口 272×10=2720 → 97×10=970（−1750），
  共享核心 251 → 359（+108）。
- tests：11682 → 12121（**+439**；新增主题 361 + 支撑 69 + 聚合器 9；`tests/fixtures/`
  按计数口径排除）。
- plugin：4793 → 4793（**0**）；dist：146 → 146（0）。
- 本票迁 1 族 10 场景；共享化净减随 16/17 票继续累加，不做伪造减量。

**未验证限制。** 真实 Codex 模型轮与真实远端写入未执行（零凭据、零网络，属全任务一贯
限制）；受控替身只覆盖 stdio JSON-RPC 协议行为与受控进程组，不代表真实模型/网络结果。
相对阈值（`--kill-relative`）的迁移属票 16，本票未触及。

# 13: 建立共享客户端并接通标准事件场景

**What to build:** 标准事件验收场景使用共享客户端完成请求、等待和证据输出，旧客户端仍可支撑尚未迁移的场景。

**Blocked by:** 10 按行为组织包与场景验收检查

**Status:** resolved

**Spec:** [MyGameStudio 全插件分阶段架构重构 v1](../spec.md) · User Stories 35, 36, 37, 38, 40

**Verification mapping:** 按本票所属阶段的验收集合

- [x] 完成共享客户端的实际请求响应、事件等待、输出与进程结束路径，并迁入现有三个逐字节同类的标准事件场景（原 02、17、18）。
- [x] 共享实现对每条新输入只解码一次并分发，普通完成、失败、超时和事件筛选维持原语义。
- [x] 现有场景命令参数、身份、证据内容与退出码保持；未迁移场景继续沿旧实现通过。
- [x] 用受控进程或回放 adapter 检验完整调用，旧与新标准场景在相同输入下的可观察结果一致。
- [x] 复测一千条固定事件的轮询计数，证明旧事件不反复解码；不把操作量改善宣称为模型或网络端到端倍数。

**依赖理由：** 依赖 10 可独立运行的场景与包验证方式，采用 expand：新旧并存，先接通一族完整场景。

## 执行与验证约定

本票已正式发布；实施按对应任务授权执行。沿现有 interface 验证本票行为；保持外部用法、持久化格式、权限与恢复语义，只有明确列出的 R1 属行为修正。每票在新的执行上下文中按实际前置成果接手；产品内容变化时同步相关包与来源检查，记录净行数、必要操作量和未验证限制。

同一共享文件只由一名执行者修改。测试和独立规范/规格评审针对本票实际版本；基线不可被历史结果替代。提交、推送、标签、真实远端写入、日常安装和发布分别沿明确授权执行。

## Comments

用户已确认 26 票拆分及其依赖安排；本票按确认稿发布，未启动实施。

### 执行记录（2026-09-12，阶段 3 首票，核心票）

**迁移场景清单（expand：新旧并存）。** 族 1 的三份客户端在基点上 SHA-256 完全相同
（`75c333ac…`，`client_probe.json` 亦归为一族）：`acceptance/02-role-scoped-write`、
`17-github-issue-workflow`、`18-complete-package-acceptance` 的 `appserver_client.py`。
本票即迁移这三者；`acceptance/01` 及族 3/4/5 共 15 份继续使用各自旧实现（不删）。

**做了什么。**
- 新增共享核心 `acceptance/_shared/appserver_core.py`（253 行）：`AppServer`（子进程通信、
  请求响应归属、事件等待、进程生命周期）、`run_skills` / `run_turn` 场景驱动、
  `initialize` / `iter_skills` / `write_event_stream`。事件按行惰性解码并缓存
  （`_decoded[index]`），`request` / `drain_events` / `wait_turn_completed` 共用同一缓存，
  每条输入最多解码一次。
- 三份标准事件入口改为 80 行薄壳：只保留自身 `clientInfo`（`mgs02-acceptance`）、
  `--sandbox` / `--events-out` / `--out` / `--timeout` 参数与四类事件筛选
  `KEEP_TYPES`，经 `sys.path` 注入 `_shared` 后调用共享实现。命令名、参数、默认值、
  退出码与证据文件格式逐项保持。
- 新增离线测试：`tests/test_acceptance_client.py`（236 行，8 例）、
  `tests/acceptance_client_support.py`（147 行）、受控替身
  `tests/fixtures/fake_appserver.py`（114 行，模拟 `codex app-server` 的 JSON-RPC over
  stdio，无模型/网络/凭据）；主题并入 `tests/test_plugin_package.py` 聚合器。

**验证命令与真实结果。**
- 五套聚合器全绿：`test_plugin_package`（含新主题）、`test_runtime_gate`、
  `test_runtime_boundaries`、`test_records_backend`、`test_github_backend`，均 rc=0。
- 冻结基线 `sh .scratch/mygamestudio-architecture-refactor/evidence/baseline/run_baseline.sh`
  五套 rc=0；跑毕已 `git checkout --` 恢复 `results/` 与 `BASELINE-REPORT.md`，冻结产物无 diff。
- 共享实现 8 例：三入口逐字节一致且无自有 `request`/`wait_turn_completed`；受控替身跑
  `turn` 得报告 `first agent reply\n\nsecond agent reply`（重复 key/文本去重与旧实现一致）、
  事件证据 6 条值项 + `turn/completed`、身份 `mgs02-acceptance`、生命周期日志
  `started/terminated` 且 pid 已结束；`skills` 输出字段一致；`no_thread_id`、`error_init`
  非零退出且保留原错误文本，缺参退出码 1；未迁移场景经旧实现同输入报告一致。
- A/B 对照（`.scratch/.../evidence/13-client-shared.json`，合成回放）：
  旧新 `wait_turn_completed` 的 agent 消息与事件增量消费结果相等（`agent_messages_equal=true`、
  `events_equal=true`，事件 7 条）。
- `./dist/verify-reproducible.sh` PASS（`plugin/` 与包内容未变，交付包 SHA-256
  `af91503f…` 与票 02 记录一致）。

**解码计数对比（复用票 01 `client_probe.py` 方法：1000 条固定事件、10 次轮询，计数器
替换 `json.loads`；离线合成，不代表端到端倍数）。**
- 迁移前基点旧实现：21000 次（= 票 01 基线）。
- 迁移后共享实现：**1000 次**（每条输入恰解码一次）；事件 1000 条、agent 消息 1000 条。
- 冻结 `client_probe.py` 原样重跑三份迁移客户端：`json_loads_calls` 21000 → 1000；
  18 份客户端归一化后仍 5 族（`total_client_lines` 4605 → 4170）。

**净行数（`code_volume.py` 同范围物理行口径，相对本票前基点 HEAD）。**
- acceptance：20810 → 20628（**−182**）；其中新增共享核心 +253，三入口 225×3 → 80×3（**−435**）。
- tests：10909 → 11303（**+394**；新测试 236 + 支撑 147 + 聚合器 +11；`tests/fixtures/` 按计数口径排除）。
- plugin：4793 → 4793（**0**，本票未改产品插件）；dist：146 → 146（0）。
- 本票只迁 1 族 3 场景，共享化净减随 14–17 票继续迁移累加；不做伪造减量。

**未验证限制。** 真实 Codex 模型轮与真实远端写入未执行（零凭据、零网络，属全任务一贯
限制）；受控替身只覆盖 stdio JSON-RPC 协议行为，不代表真实模型/网络结果。中断相关
（绝对/相对阈值、进程组结束）属 15、16 票，本票未触及。

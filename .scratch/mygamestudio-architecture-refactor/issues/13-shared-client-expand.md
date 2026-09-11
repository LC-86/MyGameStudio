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

**净行数（`code_volume.py` 同范围物理行口径，相对本票前基点 HEAD `e42d17b`；第二轮复审修复后于当前 HEAD 实测回填）。**
- acceptance：20810 → 20615（**−195**）；其中新增共享核心 +240，三入口 225×3 → 80×3（**−435**）。
- tests：10909 → 11406（**+497**；新测试 339 + 支撑 147 + 聚合器 +11；`tests/fixtures/` 按计数口径排除；测试 339 已含第一轮 F1 行为化改写）。
- plugin：4793 → 4793（**0**，本票未改产品插件）；dist：146 → 146（0）。
- 本票只迁 1 族 3 场景，共享化净减随 14–17 票继续迁移累加；不做伪造减量。

**未验证限制。** 真实 Codex 模型轮与真实远端写入未执行（零凭据、零网络，属全任务一贯
限制）；受控替身只覆盖 stdio JSON-RPC 协议行为，不代表真实模型/网络结果。中断相关
（绝对/相对阈值、进程组结束）属 15、16 票，本票未触及。

### 复审修复记录（第一轮，2026-09-12）

独立复审发现 4 项（F1 测试源码绑定、F2 守卫静默通过、F3 死参数、F4 留档），本轮处置如下。

**F1（测试源码绑定，已改）。** 删除 `tests/test_acceptance_client.py` 中对核心源码
`def request(` 等子串断言、薄壳 `"def ..." not in text` 反断言、`run.sh` 源码子串断言
与三入口 `hash()` 逐字节相等断言。改为行为等价断言：
- 经真实 import 加载共享核心与三份入口（三入口共享同一 `appserver_core` 对象），以
  `inspect.getmodule(shell.run_turn) is core` 与对象身份核对 `AppServer`/`run_turn`/
  `run_skills` 均来自共享核心；
- 转发探针：替换共享核心的 `AppServer` 后调用薄壳入口 `cmd_turn`/`cmd_skills`，核对完整
  调用序列 `initialize→thread/start→turn/start→close` 与 `initialize→skills/list→close`
  确实转发到共享核心（证明薄壳无独立 JSON-RPC 实现）；
- 行为一致性：三份入口经受控替身进程在相同输入下产出相同的报告、事件证据与身份，断言
  可观察输出相等而非字节相等。

**F2（守卫静默通过，已改）。** `test_old_new_replay_parity`、
`test_unmigrated_scenario_still_passes` 原先在 `find_legacy_client()` 返回 None 时 `return`
静默通过。现改为前置 `check(legacy is not None, "旧实现已被移除,本守卫需随票 17 更新
(expand 过渡期守卫不可静默跳过)")`：旧实现消失时响亮失败并点名需随票 17 有意识处理；两测试
docstring 已注明是 expand 过渡期守卫、票 17 需更新。

**F3（死参数清理，已改）。** 全仓 grep 核实无调用者后删除：
- `AppServer.__init__` 的 `codex_bin`/`env`（全部调用方均 `AppServer()`）→ 无参构造，保留
  `CODEX_BIN` 环境变量回退与 `dict(os.environ)`；
- `write_event_stream` 的 `trailing_methods`（仅一个取值且无外部传入）→ 直接保留
  `turn/completed`；
- 仅打印 docstring 的 `main`/`__main__` 存根及随之无用的 `import sys`。
`turn_completed()` 有 `wait_turn_completed` 内部调用，保留为内部方法。共享核心 253 → 240 行。

**F4（留档不改）。** `close()` 裸 `except` 吞异常与旧实现逐行相同，保持外部语义，票 15/16
迁移中断场景时随行为族一并处理；三份薄壳 60 行 argparse/main 重复是 expand 模式有意为之
（场景身份壳），票 17 收口时统一处理。

**验证。**
- `tests/test_acceptance_client.py` rc=0；五套聚合器（`test_plugin_package`、
  `test_runtime_gate`、`test_runtime_boundaries`、`test_records_backend`、
  `test_github_backend`）全绿 rc=0。
- 证据探针 `13-client-evidence.py` 复跑：解码计数不变（旧 21000 / 共享 1000，`_message`
  解码行为未受 F3 影响），A/B parity 仍 true；仅 `shared_core` 行数 253→240，已更新
  `13-client-shared.json`。
- 故障注入自检（/tmp 副本，未污染仓库）：把 02 薄壳 `run_turn` 改为本地实现 → F1 新断言
  4 项失败；模拟旧实现全部消失 → F2 两处守卫各 1 项失败。证明行为绑定与显式守卫有效。
- `plugin/` 零改动；三份薄壳零改动（F3 未波及）；`./dist/verify-reproducible.sh` PASS
  （交付包 SHA-256 `af91503f…`，与验收记录一致；dist 不打包 acceptance/，无需重建）。

### 复审修复记录（第二轮，2026-09-12）

第二轮独立复审三项处置（F5 复核、F6 行数回填、F7 留档）。本轮不改产品代码；三份薄壳
保持逐字节一致（SHA-256 `741a2b47…`）。

**F5（薄壳死 import，复核后保留不改）。** 原判「`import json`/`import time` 已无任何使用、
noqa 理由过时」经实际核实不成立。三份薄壳的 `module.json`/`module.time` 属性仍是冻结探针的
直接依赖：`.scratch/.../evidence/baseline/client_probe.py`（票 01，`run_baseline.py` 的
`PROBES` 之一）在 `decode_probe()` 第 69–72 行对被加载的薄壳 module 执行
`module.json.loads = counting_loads`、`module.time.time = clock.time`、`module.time.sleep = clock.sleep`；
`.scratch/.../evidence/13-client-evidence.py` 同法但作用于共享核心 module（不受薄壳影响）。
在 `/tmp` 副本实测删除这两行后，`decode_probe()` 抛
`AttributeError: module 'baseline_client_02-role-scoped-write' has no attribute 'json'`，
即 `run_baseline.sh` 由绿转红；而本轮授权不允许修改 `evidence/baseline/` 冻结产物，无法同步
去掉该依赖。故 noqa 理由（「票 01 基线探针按模块属性替换解码计数器/计时器(冻结产物)」）属实、
未过时，两行 import 与 noqa 本体均保留；三份薄壳零改动、仍逐字节一致。

**F6（票内行数回填，已改）。** 「净行数」段旧值（acceptance 20628/−182、tests 11303/+394）为
第一轮修复前口径，已按 `code_volume.py` 同范围物理行口径在当前 HEAD 实测回填：acceptance
20810 → 20615（−195，共享核心 +240、三入口 225×3 → 80×3 = −435）；tests 10909 → 11406
（+497，新测试 339 + 支撑 147 + 聚合器 +11，`tests/fixtures/` 按口径排除）；plugin 4793 → 4793（0）；
dist 146 → 146（0）。`13-client-shared.json` 的 `line_counts`（shared_core 240、三入口各 80、
基点旧实现各 225）复核无误，无需再动。

**F7（留档不改，三项）。**
1. `tests/acceptance_client_support.py` 的 `find_legacy_client()` 仍以子串
   （`def wait_turn_completed`/`def drain_events`/`self.lines`）定位旧客户端——expand 过渡期的
   定位手段，查找失败已由调用方显式 `check(legacy is not None, …)` 响亮报错；票 17 删除旧实现时
   随守卫一并更新，不在此轮引入结构化注册表。
2. `acceptance/_shared/appserver_core.py` 的 `_message` 用 `self.__dict__.get("_decoded")` 回退，
   是为服务 `object.__new__` 构造的探针实例（`13-client-evidence.py` 及票 01 冻结探针依赖其
   不调用 `__init__`）；改为正常 `self._decoded` 需连带改冻结证据并重基线，收益仅约 2 行，
   裁定留档不改。
3. `tests/test_acceptance_client.py` 的 mock 在 F1 中改用 `lambda: _SpyServer(...)` 替换
   `core.AppServer`；若未来对 `AppServer` 做 `isinstance`/属性访问会变脆。当前断言失败会响亮
   报错（`cmd_turn`/`cmd_skills` 调用序列不符即失败），现阶段可接受，留档知悉。

**验证。**
- 三份薄壳 `python3 -m py_compile` 通过；三份 SHA-256 仍为 `741a2b47…`（逐字节一致、未改）。
- `tests/test_acceptance_client.py` rc=0；五套聚合器（`test_plugin_package`、`test_runtime_gate`、
  `test_runtime_boundaries`、`test_records_backend`、`test_github_backend`）全绿 rc=0。
- 冻结 `client_probe.py` 在保留 import 的当前 HEAD 复跑成功（`json_loads_calls=1000`、
  5 族、`total_client_lines=4170`），反证 F5 保留的必要性。
- `./dist/verify-reproducible.sh` PASS（交付包 SHA-256 `af91503f…`）；`plugin/` 零改动，
  dist 不打包 acceptance/，无需重建。

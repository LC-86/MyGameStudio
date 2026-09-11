# 14: 迁移最小与扩展事件的普通场景

**What to build:** 其余普通读取和事件场景继续保持各自输出方式，同时共享请求与等待实现。

**Blocked by:** 13 建立共享客户端并接通标准事件场景

**Status:** resolved

**Spec:** [MyGameStudio 全插件分阶段架构重构 v1](../spec.md) · User Stories 35, 36, 38, 40

**Verification mapping:** 按本票所属阶段的验收集合

- [x] 迁移原 01 的最小客户端行为，以及原 03、04 的扩展事件行为，保留各自既有参数与证据选择。
- [x] 不为统一客户端强加原场景不存在的输出字段、事件类型或中断选项。
- [x] 普通完成、错误、超时、事件去重与进程结束经对应旧新对照通过。
- [x] 本批三个入口实际使用共享实现；剩余未迁移入口仍可独立使用旧实现。

**依赖理由：** 依赖 13 的共享客户端；与绝对中断迁移无功能依赖，但修改共享实现时需串行协调。

## 执行与验证约定

本票已正式发布；实施按对应任务授权执行。沿现有 interface 验证本票行为；保持外部用法、持久化格式、权限与恢复语义，只有明确列出的 R1 属行为修正。每票在新的执行上下文中按实际前置成果接手；产品内容变化时同步相关包与来源检查，记录净行数、必要操作量和未验证限制。

同一共享文件只由一名执行者修改。测试和独立规范/规格评审针对本票实际版本；基线不可被历史结果替代。提交、推送、标签、真实远端写入、日常安装和发布分别沿明确授权执行。

## Comments

用户已确认 26 票拆分及其依赖安排；本票按确认稿发布，未启动实施。

### 执行记录（2026-09-12，阶段 3 第二票）

**迁移场景与族归属核实（以实物为准）。** 勘察 `acceptance/01`、`03`、`04` 的实际行为与
`client_probe.json` 族归属，与工单描述一致：01 自成一族（族 2，单份，固定 read-only、
无 `--events-out`）；03、04 归族 3（两份，可配 `--sandbox`、`--events-out` 保留全部
`item/completed` 类型并额外保留 turn 生命周期通知）。本票迁移这三份入口。

**做了什么。**
- 扩展共享核心 `acceptance/_shared/appserver_core.py`（240 → 251 行，**新增函数/参数、
  不改已迁移场景行为**）：
  - `write_event_stream` 新增 `keep_types: set|None`（`None`=保留全部 item 类型）与
    `event_methods`（默认 `turn/completed`，扩展族传 `turn/started|completed|failed`）；
  - `run_turn` 透传上述两个新参数，默认值保持标准族原行为；新增常量
    `DEFAULT_EVENT_METHODS`。**未触碰 `_message` 的 `_decoded` 探针回退分支与事件增量解码。**
- 三份入口薄壳化（沿用票 13 先例）：01（196 → 78 行，族 2）、03/04（各 225 → 84 行，族 3）。
  只保留自身 `clientInfo`、命令参数与事件筛选，经 `sys.path` 注入 `_shared` 调用共享实现。
  01 未新增 `--sandbox`/`--events-out`，固定 `sandbox="read-only"`、`events_out=None`；
  03/04 保留可配沙箱与全类型 + turn 生命周期事件证据。命令名、参数、默认值、退出码与
  证据文件格式逐项保持；三份薄壳均保留被冻结探针依赖的 `import json`/`import time` 模块属性。
- 测试：`tests/test_acceptance_client.py` 保留标准事件族并改为按基点提交读取旧实现对照
  （旧文件已按红线删除）；新增主题 `tests/test_acceptance_client_families.py`（234 行，5 例）
  覆盖 01/03/04；`tests/acceptance_client_support.py`（253 行）新增
  `load_git_module`/`load_shared_and_shells`/`SpyServer`/`spy_calls`/`pid_alive`/`read_jsonl`
  与族分组常量；`tests/fixtures/fake_appserver.py` 新增 `lifecycle` 模式（发 `turn/started`）；
  两个主题并入 `tests/test_plugin_package.py` 聚合器。守卫沿票 13 模式：旧实现/基点缺失时
  显式失败，不静默通过。

**四条验收自查与证据。**
1. 迁移 01（最小）+ 03/04（扩展事件），保留各自参数与证据选择：三份入口经真实 import
   委托 `core.run_turn/run_skills`（`inspect.getmodule is core`）；转发探针核对 01 传
   `read-only`、03/04 传 `workspace-write`；03/04 事件证据 = `turn/started` + 6 条全类型
   item + `turn/completed`（`test_basic_and_extended_clients_share_implementation`、
   `test_extended_event_evidence_and_identity`）。
2. 不强加原场景不存在的输出/事件/中断选项：01 入口拒绝 `--sandbox`/`--events-out`
   （argparse rc≠0）；标准族 02 同输入下不含 `turn/started` 且只保留四类值项（对照断言）；
   中断选项属 15/16 票，本票未触及。
3. 普通完成、错误、超时、事件去重、进程结束旧新对照：A/B 合成回放（
   `.scratch/.../evidence/14-client-basic-extended.json`）——族 3 旧新 agent 消息与事件增量
   消费结果相等（`extended_agent_messages_equal=true`、`events_equal=true`，事件 8 条），
   族 2（01）agent 消息相等；受控替身进程跑通普通完成（报告去重为
   `first agent reply\n\nsecond agent reply`）与失败路径（`no_thread_id`、`error_init` 非零
   退出且保留原错误文本，缺参退出码 1）；超时无 `turn/completed` 时返回已取得消息且每条
   输入只解码一次；生命周期日志 `started/terminated` 且 pid 已结束。
4. 三入口实际用共享实现，剩余入口仍可独立用旧实现：未迁移族 0/4（12 份）经
   `find_legacy_client()` 定位并受控进程跑通同输入报告一致（`test_unmigrated_scenario_still_passes`）；
   旧客户端文件去向按票 17 收口，本票只切入口，未删任何旧实现文件。

**验证命令与真实结果。**
- `python3 -B tests/test_acceptance_client.py` rc=0；`tests/test_acceptance_client_families.py`
  rc=0；五套聚合器（`test_plugin_package`、`test_runtime_gate`、`test_runtime_boundaries`、
  `test_records_backend`、`test_github_backend`）全绿 rc=0。
- 冻结基线 `sh .scratch/.../evidence/baseline/run_baseline.sh`：五套 PASS、`all_existing_checks_green=True`；
  跑毕已 `git checkout --` 恢复 `results/` 与 `BASELINE-REPORT.md`，冻结产物无 diff。
- 票 13 红线段复跑：`.scratch/.../evidence/13-client-evidence.py` rc=0，解码计数仍
  旧 21000 / 共享 1000、A/B parity 两项 `true`（`_message` 探针回退分支未动）。
- `client_probe.py` 复跑：18 份归一后仍 5 族、解码 1000；三份新薄壳仍归各自原族
  （01 族 2、03/04 族 3）——族归属正确。
- 故障注入自检（`/tmp` 副本，未污染仓库）：把 03 薄壳 `run_turn` 改为本地实现 →
  `test_basic_and_extended_clients_share_implementation` 即失败，证明行为绑定有效。
- `acceptance/*/run.sh` 三份 `sh -n` 语法通过；三入口 `turn --help` 选项面与迁移前一致。
- `plugin/` 零改动；dist 不打包 acceptance/，无产品插件改动。

**净行数（同范围物理行口径，相对本票前基点 HEAD `9744601`）。**
- acceptance：20615 → 20226（**−389**）；其中三入口 196+225+225=646 → 78+84+84=246
  （−400），共享核心 +11。
- tests：11406 → 11682（**+276**；`test_acceptance_client` −71、支撑 +106、夹具 +4、
  聚合器 +7、新增主题 `test_acceptance_client_families.py` +234）。
- plugin：4793 → 4793（**0**）；dist：146 → 146（0）。
- 本票只迁 2 族 3 场景；共享化净减随 15–17 票继续迁移累加，不做伪造减量。

**未验证限制。** 真实 Codex 模型轮与真实远端写入未执行（零凭据、零网络，属全任务一贯
限制）；受控替身只覆盖 stdio JSON-RPC 协议行为，不代表真实模型/网络结果。中断相关
（绝对/相对阈值、进程组结束）属 15、16 票，本票未触及。

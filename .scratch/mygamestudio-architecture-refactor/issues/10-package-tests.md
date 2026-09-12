# 10: 按行为组织包与场景验收检查

**What to build:** 维护者可以独立运行包完整性、业务入口、素材夹具与事件判据检查，原有总入口仍返回完整通过或失败结果。

**Blocked by:** 09 让直连失败判据通过同一事件入口验证

**Status:** ready-for-agent

**Progress:** 已完成（2026-09-12 收口；执行记录见 Comments 与执行日志）

**Spec:** [MyGameStudio 全插件分阶段架构重构 v1](../spec.md) · User Stories 5, 6, 28, 30, 31, 32, 33, 34, 59

**Verification mapping:** 按本票所属阶段的验收集合

- [x] 从巨型包检查中按真实行为划分可独立运行的检查，保留原总入口和所有原案例的可追溯映射。
- [x] 事件案例使用 08、09 的同一判据 interface；重复事件构造转为具名数据，不删边缘案例或正向对照。
- [x] 包完整性、来源、许可、引用、模板、素材及凭据扫描等既有检查含义保持；源码形状要求改为实际可用性检查时保留验证目的。
- [x] 各主题入口和总入口能正确报告失败；必要故障注入能使对应主题失败，其他无关主题不受影响。
- [x] 报告新旧测试净行数、最大文件/函数长度和仍保留的例外；历史证据不被重写或删除。

**依赖理由：** 依赖 09 完成两类判据迁出，避免拆分时保留源码抽取式依赖。

## 执行与验证约定

本票已正式发布；实施按对应任务授权执行。沿现有 interface 验证本票行为；保持外部用法、持久化格式、权限与恢复语义，只有明确列出的 R1 属行为修正。每票在新的执行上下文中按实际前置成果接手；产品内容变化时同步相关包与来源检查，记录净行数、必要操作量和未验证限制。

同一共享文件只由一名执行者修改。测试和独立规范/规格评审针对本票实际版本；基线不可被历史结果替代。提交、推送、标签、真实远端写入、日常安装和发布分别沿明确授权执行。

## Comments

用户已确认 26 票拆分及其依赖安排；本票按确认稿发布，未启动实施。

### 执行记录(票 10 实施)

**做了什么。** 将 `tests/test_plugin_package.py`(4100 行、51 个顶层函数、
其中一个事件判据函数 1550 行)按真实行为主题拆为 9 个可独立运行的主题文件
\+ 1 个事件判据文件 + 1 个共享支撑模块 + 1 个具名数据文件。原总入口文件
保留为聚合器(111 行),运行方式 `python3 -B tests/test_plugin_package.py`
不变,仍返回完整通过/失败。生产内容 `plugin/` 与 `dist/` 零改动。

**主题划分清单。** 聚合顺序即原总入口历史顺序:

| 主题文件 | 行数 | 行为主题 |
| --- | --- | --- |
| `test_package_manifest.py` | 278 | 包完整性:清单、14 入口、MCP 通道、模板全集、内部引用闭包、records 接缝、模板适配 |
| `test_package_provenance.py` | 100 | 来源/许可/指纹追溯、版本一致、无开发机路径 |
| `test_package_fixtures_samples.py` | 270 | samples 样例结构与状态 |
| `test_package_skill_content_design.py` | 343 | 设计/规格/原型/制作/美术/音频 Skill 说明 |
| `test_package_fixtures_acceptance_a.py` | 424 | 验收注入夹具 07-12 |
| `test_package_skill_content_delivery.py` | 366 | 构建/评审/试玩/目标变更/统筹/GitHub 工作流 Skill 说明 |
| `test_package_fixtures_acceptance_b.py` | 331 | 验收注入夹具 13-16/18 |
| `test_package_dist.py` | 159 | dist 三方一致与隔离重建字节可复现 |
| `test_package_secret_scan.py` | 394 | 脱敏不枚举实例名、独立扫描器失效闭合、泄漏不假绿 |
| `test_package_event_judgement.py` | 378 | 事件判据(经 08/09 同一 interface,按 SP 轮次分组) |
| `plugin_package_support.py` | 58 | 共享支撑:per-theme checker、路径/指纹、事件夹具装载 |
| `plugin_package_fixtures.json` | 227 | 具名事件与案例数据(98 事件、103 案例、4 Shell 对照、10 留存重跑) |

**事件判据接缝。** 全部经 `acceptance/18-complete-package-acceptance/
evidence_judgement.py`(`judge_mcp_deny` / `judge_curl_direct_denied`),
Shell 侧经 `evidence_adapter.sh`;巨型函数内联的 98 个重复事件构造转为
`plugin_package_fixtures.json` 具名数据,重建后与原内联夹具逐字节一致。
原巨型函数按复审轮次拆为 SP 分组入口(core_sp6 / sp8 / sp12-13 / sp15-16 /
sp18-19 / sp20-23 / sp24-26 / sp27-29 / sp30)+ 现场接入、双输入一致、
留存证据重跑、旧词串假绿(红)、run.sh 接线,全部案例身份保留。

**映射与净行数。** 逐项映射见
`evidence/10-case-mapping.md`(原函数→新位置)与
`tests/plugin_package_fixtures.json`(事件案例)。

- 旧:`tests/test_plugin_package.py` 4100 行;最大函数 1550 行。
- 新:11 个 Python 文件合计 3212 行 + 数据文件 227 行;最大文件 424 行,
  最大函数 153 行(`test_accept16_secret_scan_gate`,原样迁入的报告边界例)。
- 净行数:-888 行(仅代码;拆文件不算净减,此处省略的重复仅来自巨型函数内
  98 处内联事件构造转入具名数据,无判定逻辑删除)。
- 原 46 个 `test_*` 函数全部保留身份。

**验证命令与真实结果。**

- 拆出的 10 个主题入口(见上表):全部 `exit 0`,打印 OK。
- 原总入口 `python3 -B tests/test_plugin_package.py`:`exit 0`,打印
  `OK: 最小插件包静态完整性检查全部通过`。
- 原五套入口全绿:`test_plugin_package` / `test_runtime_gate` /
  `test_runtime_boundaries` / `test_records_backend` / `test_github_backend`
  均 `exit 0`。
- `sh .scratch/.../evidence/baseline/run_baseline.sh`:五套全 PASS
  (`all_existing_checks_green=True`),随后 `git checkout --` 恢复冻结
  results/ 与 BASELINE-REPORT.md。
- 无案例丢失证明:对比原实现与新聚合入口实际执行的全部 check 消息,
  原 1630 条在新聚合入口全部重现、0 丢失;新增 1 条(缺失 run.sh 守卫)。
- 故障注入(在 `/tmp` 副本,未污染仓库):对 10 个主题各注入一次错误,
  该主题 `exit 1`、所选无关主题 `exit 0`,恢复后全部回绿(见下表)。
  另验证聚合入口注入后 `exit 1` 且点名失败主题与条目,恢复后回绿。

| 注入主题 | 注入 | 故障 rc | 无关主题 rc |
| --- | --- | --- | --- |
| manifest | openai.yaml 改 true | 1 | 0(事件判据) |
| provenance | 新增未登记 internal 文件 | 1 | 0(事件判据) |
| dist | 追加伪校验和 | 1 | 0(事件判据) |
| skill_content_design | game-design SKILL 去「质询」 | 1 | 0(样例夹具) |
| skill_content_delivery | game-build SKILL 去「不硬编码」 | 1 | 0(事件判据) |
| fixtures_samples | 删 stardust-dash README | 1 | 0(manifest) |
| fixtures_acceptance_a | 删 accept07 夹具 README | 1 | 0(provenance) |
| fixtures_acceptance_b | 删 accept13 夹具 README | 1 | 0(manifest) |
| secret_scan | 删 16 号 secret_scan.py | 1 | 0(事件判据) |
| event_judgement | 删 18 号 evidence_adapter.sh | 1 | 0(manifest) |

**保留例外与未验证限制。**

- 单文件长度:最大主题文件 `test_package_fixtures_acceptance_a.py` 424 行、
  `test_package_secret_scan.py` 394 行,均在 500 行内。函数长度:仅
  `test_accept16_secret_scan_gate`(153 行)与
  `test_accept18_leak_checks_mechanized`(148 行)按原样迁入,超出 80 行;
  二者是审查修复票固化的报告边界例(多重注入与失效闭合逐例断言),本次为
  纯重组不重写断言,记录为例外。事件判据巨型函数(1550 行)已按 SP 分组
  拆为 14 个入口,最大 50 行。
- `acceptance/18` 的 `run.sh`(1007 行)按票面属「旧大文件随所属阶段处理」,
  本票未拆,记录例外。
- 未修改任何冻结产物:`evidence/baseline/` 脚本与 `results/`、
  `BASELINE-REPORT.md` 保持只读;`dist/REPRODUCE.md`、`acceptance/*/run.sh`
  对 `test_plugin_package` 的引用因原入口与文件名不变而无需改动。
- 未运行的真实条件(与既有口径一致,不在本票范围):真实模型轮、真实远端
  写入、安装替换。事件判据验证为离线事件回放。
- 生产内容 `plugin/`、`dist/` 零改动,故未重建交付包。

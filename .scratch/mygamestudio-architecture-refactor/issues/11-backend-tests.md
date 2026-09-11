# 11: 按用户行为组织任务后端回归

**What to build:** 维护者能独立验证任务读取、迁移、发布恢复和离线行为，同时原后端总检查继续覆盖所有场景。

**Blocked by:** 07 完成任务读取的入口与交付兼容验收

**Status:** resolved

**Spec:** [MyGameStudio 全插件分阶段架构重构 v1](../spec.md) · User Stories 5, 6, 21, 22, 23, 25, 27, 31, 32, 42, 45

**Verification mapping:** 按本票所属阶段的验收集合

- [x] 将本地与 GitHub 后端检查按读取、核验、迁移、恢复等完整行为组织，正常总入口仍覆盖原检查。
- [x] 保留 R1 与 READ 系列、双后端正文、离线元信息、真实 CLI、错误继承及恢复碰撞等现有行为检查。
- [x] 共享重复准备代码但不将生产规则复制进测试；实际读取和结果追加 interface 仍是主要测试入口。
- [x] 每个迁移案例有原身份到新位置的对应，故障注入能证明关键行为检查仍有效。
- [x] 独立主题运行和总运行均通过，并记录行数与超限理由；不修改生产行为或恢复格式。

**依赖理由：** 依赖 07 固定后的读取行为与调用入口，避免在读取重构中途再次迁移其测试。

## 执行与验证约定

本票已正式发布；实施按对应任务授权执行。沿现有 interface 验证本票行为；保持外部用法、持久化格式、权限与恢复语义，只有明确列出的 R1 属行为修正。每票在新的执行上下文中按实际前置成果接手；产品内容变化时同步相关包与来源检查，记录净行数、必要操作量和未验证限制。

同一共享文件只由一名执行者修改。测试和独立规范/规格评审针对本票实际版本；基线不可被历史结果替代。提交、推送、标签、真实远端写入、日常安装和发布分别沿明确授权执行。

## Comments

用户已确认 26 票拆分及其依赖安排；本票按确认稿发布，未启动实施。

### 执行记录(票 11 实施)

**做了什么。** 将两个后端回归入口文件按真实行为主题拆分:
`tests/test_records_backend.py`(1560 行、40 个 `test_*`)拆为 6 个主题文件
\+ 1 个共享支撑 + 保留原入口为聚合器(63 行);`tests/test_github_backend.py`
(2758 行、56 个 `test_*`)拆为 9 个主题文件 + 2 个共享支撑(替身传输层与
夹具/计数器)+ 保留原入口为聚合器(71 行)。聚合顺序即原总入口历史顺序,
运行方式 `python3 -B tests/test_records_backend.py` /
`python3 -B tests/test_github_backend.py` 与输出不变;每个主题文件可直接
`python3 -B tests/<主题>.py` 运行。生产 `plugin/`、`dist/`、`acceptance/`
零改动。

**主题划分清单。**

records 侧(6 主题 + 支撑,聚合器 63 行):

| 主题文件 | 行数 | 行为主题 |
| --- | --- | --- |
| `test_records_read.py` | 284 | 本地后端读取(配置/列表/单任务/CLI) |
| `test_records_verify.py` | 234 | 本地与 GitHub 后端核验 |
| `test_records_deps_ready.py` | 369 | 依赖解析与可开工集合 |
| `test_records_baseline.py` | 200 | 核心基线指纹与受影响任务 |
| `test_records_shared_body.py` | 194 | 共享正文、来源归属与错误身份 |
| `test_records_interface.py` | 98 | 公开接口兼容面 |
| `records_backend_support.py` | 366 | 共享夹具、读取计数与导入方向探针、指纹登记 |

github 侧(9 主题 + 支撑,聚合器 71 行):

| 主题文件 | 行数 | 行为主题 |
| --- | --- | --- |
| `test_github_config_backend.py` | 425 | 配置、拉取、离线缓存与核验 |
| `test_github_ready_list_show.py` | 301 | 一次来源 ready 与列表/单任务读取 |
| `test_github_write_ops.py` | 278 | 写操作(授权闸门/防重/超时回读/更新/关系/关闭) |
| `test_github_drafts.py` | 215 | 离线草稿保存与发布归属 |
| `test_github_migration_handover.py` | 253 | 后端切换迁移与交接基线可达 |
| `test_github_cli.py` | 180 | GitHub 后端 CLI 真实入口 |
| `test_github_result_recovery.py` | 299 | 结果发布的部分成功、未知与重试恢复 |
| `test_github_pending_index.py` | 339 | 待补索引登记:碰撞、损坏与旧布局迁移 |
| `test_github_pending_clear.py` | 257 | 待补索引清除归属(逐路径核验) |
| `github_backend_fixtures.py` | 292 | CONFIG/项目夹具、CLI HTTP 替身、共享正文、读取计数器 |
| `github_backend_transport.py` | 222 | `FakeTransport` 与故障注入、待补索引登记构造与摘要复算 |

**接缝与不复制生产规则。** 判定一律经真实 `mgs_records` / `mgs_github`
公开接缝(`load_config` / `list_tasks` / `read_task` / `verify_project` /
`task_dependencies` / `startable_tasks` / `baseline_report` / `github_backend`
与后端写操作、实际读取计数经 `open` 审计钩子)。共享模块只放夹具与替身,
不复制生产解析/判定规则;唯一保留的复算助手 `_pending_digest` /
`_pending_full_digest` 用于自证复审给定的碰撞对在当前实现下解析到同一/不同
登记文件(前置断言),归属结论仍由 `append_result` 的真实结果证明。

**映射与净行数。** 逐项映射见 `evidence/11-case-mapping.md`(原顶层函数与
共享符号 → 新位置)。

- 旧:`test_records_backend.py` 1560 行 + `test_github_backend.py` 2758 行
  = 4318 行;最大函数 88 行。
- 新:20 个 Python 文件合计 4940 行(6+9 主题 3926、3 共享支撑 880、
  2 聚合器 134);最大文件 425 行 `test_github_config_backend.py`。
- 净行数:+622 行(仅来自主题文件/支撑模块的头部、docstring、入口壳与
  共享导入;无判定逻辑删除,拆分文件不计净减量)。
- 原 40 + 56 个 `test_*` 函数全部保留身份;仅位置改变。
- 函数长度:绝大多数 20–71 行;仅两个审查修复票固化的报告边界例超出
  80 行为保留例外(`test_append_result_pending_clear_keeps_foreign_legacy_registration`
  88 行、`test_append_result_pending_collision_both_partial_coexist` 85 行),
  按原样迁入未重写断言。

**验证命令与真实结果。**

- 15 个主题独立运行(`python3 -B tests/<主题>.py`):全部 `exit 0`,打印 OK。
- 两聚合器:`exit 0`,分别打印原总入口的 `OK: 本地 Markdown 任务后端统一
  接口检查全部通过` 与 `OK: GitHub Issues 任务后端检查全部通过`。
- 其余三套 `test_plugin_package` / `test_runtime_gate` /
  `test_runtime_boundaries`:全部 `exit 0`。
- `sh .scratch/.../evidence/baseline/run_baseline.sh`:五套全 PASS
  (`all_existing_checks_green=True`);随后 `git checkout --` 恢复冻结
  `results/` 与 `BASELINE-REPORT.md`(恢复后本目录 0 改动)。
- 案例零丢失证明(三重):①AST 顶层符号主体比对,原 40+56 个 `test_*`
  主体与拆出后逐字节相同;②`check()` 调用点计数 180→180、350→350;
  ③插桩收集一次完整运行实际发出的全部 `check()`(条件+消息),把集合
  `repr` 顺序、时间戳与临时路径归一化后,原实现与新聚合入口发出数完全
  相同(records 211→211、github 389→389)且逐条相等(missing=0 extra=0);
  同口径下原实现两次运行之间亦逐条相等。
- 故障注入(隔离 `/tmp` 副本,未污染仓库):对 15 个主题各注入一次生产
  规则错误,被注主题 `exit 1`,所选无关主题 `exit 0`;两聚合器在被注主题
  失败时 `exit 1` 并点名失败条目;恢复后全部回绿。

**保留例外与未验证限制。**

- 单文件长度最大 425 行,均在 500 行内;`test_records_deps_ready.py` 369
  行为 records 侧最大,仍在目标区间上限内。
- 两个超过 80 行的报告边界例按原样迁入(见上),记录为例外;未为其凑长度
  而重写断言。
- 未修改任何冻结产物:`evidence/baseline/` 脚本与 `results/`、
  `BASELINE-REPORT.md` 保持只读;`dist/REPRODUCE.md`、`acceptance/*/run.sh`
  对 `test_records_backend` / `test_github_backend` 的引用因原入口与文件名
  不变而无需改动。
- 未运行的真实条件(与既有口径一致,不在本票范围):真实模型轮、真实远端
  写入、安装替换。GitHub 侧全部经本地替身传输层,零网络。
- 生产内容 `plugin/`、`dist/` 零改动,故未重建交付包。

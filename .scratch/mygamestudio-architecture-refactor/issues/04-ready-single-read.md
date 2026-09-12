# 04: 修正可开工查询的重复读取与混合结果

**What to build:** 一次 ready 的任务、依赖与来源来自同一份获取结果；下一次查询重新读取并反映修改。

**Blocked by:** 03 统一配置与本地来源并解除反向依赖

**Status:** ready-for-agent

**Progress:** 已完成（2026-09-12 收口；执行记录见 Comments 与执行日志）

**Spec:** [MyGameStudio 全插件分阶段架构重构 v1](../spec.md) · User Stories 3, 9, 10, 11, 12, 14, 18, 19, 21

**Verification mapping:** READ-01, READ-02, READ-03, READ-04, READ-05, READ-06, READ-09

- [x] 本地 ready 读取 CONFIG 原文一次，每份任务正文一次；GitHub ready 获取一次全量任务集合，且 CONFIG 原文一次。
- [x] deps 与 ready 从已取得的任务集合生成依赖关系，ready 不再回调重新获取任务的公开依赖入口。
- [x] 预备第二响应改变依赖的 R1 反例转为正确结果；证明本次没有消费第二响应，并验证第二次顶层调用看到新依赖。
- [x] 两次调用之间修改配置、任务和基线会影响第二次结果；不引入跨调用缓存，不宣称事务快照。
- [x] 本地目录顺序、远端来源顺序、阻塞原因、分流/字段/能力/基线规则及原有读取元信息保持。
- [x] 有缓存、无缓存及在线转离线通过原接口验证；错误不被吞成空集合，ready 的 blocked 不变成失败退出码。

**依赖理由：** 依赖 03 已接入的配置和来源职责。

## 执行与验证约定

本票已正式发布；实施按对应任务授权执行。沿现有 interface 验证本票行为；保持外部用法、持久化格式、权限与恢复语义，只有明确列出的 R1 属行为修正。每票在新的执行上下文中按实际前置成果接手；产品内容变化时同步相关包与来源检查，记录净行数、必要操作量和未验证限制。

同一共享文件只由一名执行者修改。测试和独立规范/规格评审针对本票实际版本；基线不可被历史结果替代。提交、推送、标签、真实远端写入、日常安装和发布分别沿明确授权执行。

## Comments

用户已确认 26 票拆分及其依赖安排；本票按确认稿发布，未启动实施。

### 执行记录（2026-09-12，R1 行为修正落地）

**改动范围与净行数**

- `plugin/records/mgs_records.py`：807 → 860 行（+53）。新增 `_Reading`（一次顶层读取内部载体）、`_read_workspace`（CONFIG 原文一次 + 任务集合一次）、`_dependency_graph`（纯依赖计算）、`_ready_classification`（纯分流判断）；`github_backend` 拆出 `_github_backend_for`（由已解析配置构造 adapter）；`task_dependencies` / `startable_tasks` / `baseline_report` 改用 `_read_workspace`；`startable_tasks` 不再回调公开依赖入口。
- `tests/test_records_backend.py`：975 → 1176 行（+201）。新增 `scoped_read_counter`（audit-hook 计底层读取型 open）与 4 个测试：READ-01 本地单次读取、deps 单次读取且 ready 不回调公开入口、READ-04 两次调用刷新、READ-06 本地目录顺序。
- `tests/test_github_backend.py`：2386 → 2526 行（+140）。新增 4 个测试：READ-02 单次全量获取、READ-03/R1 不消费第二响应且第二次调用刷新、READ-06 顺序保持、READ-05 在线→离线元信息与无缓存失败。
- `dist/`：随生产内容重建（tarball/manifest/SHA256SUMS），沿用 `dist/build-package.sh`。
- 未改动：`mgs_github.py`（1809）、`mgs_record_model.py`（252）、`mgs_record_source.py`（266）零改动。
- 净行数分列：生产 +53（全部在查询组织文件）、测试 +341、dist 二进制/清单随内容变化。

**读取计数修复前后对比（基线探针 records_probe，观察性读数）**

| 场景 | 修复前（票 01 冻结基线） | 修复后（本次复跑） |
| --- | --- | --- |
| 本地 ready CONFIG.md | 6 次 | **1 次** |
| 本地 ready task.md | 2 次/份 | **1 次/份** |
| 本地 R1 任务集合读取 | 2 次，结果 blocked（混用） | **1 次，结果 startable（不混用）** |
| GitHub R1 全量任务集合请求 | 2 次，结果 blocked（混用） | **1 次，结果 startable（不混用）** |
| GitHub ready CONFIG.md | 6 次 | **1 次** |

预期目标 CONFIG 6→1、任务集合 2→1 达成；`task_list_reads=0`（本地 R1 包装器不再被第二次触发）与任一 `result_side=startable` 印证第二个预备响应未被消费。

**R1 反例新旧行为对比**

- 旧输入：两次任务响应对同一任务给出不同依赖（第一份「依赖:无」、第二份「依赖:02-missing」）；旧结果 `blocked`，原因「依赖未解析:02-missing(任务不存在)」——把第一份任务正文与第二份依赖混用。
- 新结果：本次 ready 只消费唯一一份集合（依赖:无），`01-alpha` 保持 `startable`；下一次顶层调用重新读取到 `02-missing` 并转为 `blocked`（原因「依赖未解析:02-missing」）。测试以替身计数第 1/2 次获取、并在本地把公开 `task_dependencies` 替换为哨兵，证明 ready 期间未回调公开依赖入口（若回调即 AssertionError）。

**验证命令与真实结果**

- 五套检查实跑（`python3 tests/test_*.py`）：`test_plugin_package` rc=0、`test_runtime_gate` rc=0、`test_runtime_boundaries` rc=0、`test_records_backend` rc=0、`test_github_backend` rc=0；全部 `OK`。
- `sh .scratch/.../evidence/baseline/run_baseline.sh`：五套全绿（`all_existing_checks_green=True`）；records_probe 如上表反映修复。复跑后已 `git checkout --` 恢复 `results/` 与 `BASELINE-REPORT.md`，冻结产物不变（探针为观察性，其报告文案仍描述修复前缺陷现象，不代表修复后行为；读数已如实反映修复）。
- `./dist/build-package.sh` 重建后 `python3 tests/test_plugin_package.py` rc=0（清单与 plugin/ 一致）。
- CLI 兼容抽查：`ready` 含 blocked 时 rc=0（不变成失败退出码），`deps`/`verify`/`baseline`/`list`/`show`/`config` 返回结构与字段保持；未实现后端 `list_tasks/task_dependencies/startable_tasks` 均抛 `RecordsError`（错误不被吞成空集合）。

**六条验收逐条自查**

1. READ-01/02：audit-hook 计本地 CONFIG 1 次、每份 task.md 1 次；GitHub 替身计全量集合 1 次；均通过。
2. `_dependency_graph` 为纯函数，deps 与 ready 共用同一集合；哨兵证明 ready 未回调公开依赖入口。
3. R1 反例→正确结果；第二响应计数未增；第二次调用刷新到新依赖。
4. 修改任务/配置后第二次、第三次调用分别看到新依赖与新能力缺口；无跨调用缓存（每次 `_read_workspace` 重新读取）。
5. 本地目录顺序、GitHub 后端顺序、阻塞原因、分流/字段/能力/基线规则与读取元信息（cached/fetched_at/source/cache_note）均保持。
6. 在线→离线保留来源与缓存标识；无缓存明确失败不回退本地；错误抛 `RecordsError`；ready blocked 保持 rc=0。

**未验证限制**

- 真实模型轮与真实远端写入按授权范围未执行（全任务一贯限制）；GitHub 侧用本地替身 transport，零网络。
- 基线探针为观察性合成回放，不代表真实网络耗时或全部宿主行为；其报告文案未改（冻结产物）。
- `baseline_report` 也改用 `_read_workspace`（同调用配置/任务来源），但本票验收矩阵未单列其对读取计数的新断言，属同源整理而非本票核心目标。

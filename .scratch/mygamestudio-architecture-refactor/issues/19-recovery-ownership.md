# 19: 集中恢复登记的归属与兼容处理

**What to build:** 当前请求的恢复登记能安全读取、迁移和清除，碰撞请求、损坏登记与旧版本结果继续各自保留正确事实。

**Blocked by:** 18 让结果追加通过完整发布恢复职责执行

**Status:** ready-for-agent

**Progress:** 已完成（2026-09-12 收口；执行记录见 Comments 与执行日志）

**Spec:** [MyGameStudio 全插件分阶段架构重构 v1](../spec.md) · User Stories 42, 44, 45, 46, 47, 48

**Verification mapping:** 按本票所属阶段的验收集合

- [x] 将重复的登记有效性、完整请求归属和回执要求集中到同一恢复职责，并从真实结果追加路径使用。
- [x] 两个短标识碰撞请求先后部分成功后，登记可以共存；各自重试不会冒认、覆盖或重复发布另一请求。
- [x] 不可读、损坏、字段不完整和不属于当前请求的登记继续保守处理并按原语义披露。
- [x] 旧布局健康登记迁移与新旧双布局残留按原规则恢复，清除只影响核验属于当前请求的记录。
- [x] 通过完整追加、失败、恢复、再次调用序列观察发布次数和最终登记，而不只测试内部 JSON 读写助手。
- [x] 不改变持久化布局与已接受兼容策略；18 的全部发布生命周期继续通过。

**依赖理由：** 依赖 18 已封装且已接入的完整结果发布恢复 module。

## 执行与验证约定

本票已正式发布；实施按对应任务授权执行。沿现有 interface 验证本票行为；保持外部用法、持久化格式、权限与恢复语义，只有明确列出的 R1 属行为修正。每票在新的执行上下文中按实际前置成果接手；产品内容变化时同步相关包与来源检查，记录净行数、必要操作量和未验证限制。

同一共享文件只由一名执行者修改。测试和独立规范/规格评审针对本票实际版本；基线不可被历史结果替代。提交、推送、标签、真实远端写入、日常安装和发布分别沿明确授权执行。

## Comments

用户已确认 26 票拆分及其依赖安排；本票按确认稿发布，未启动实施。

### 执行记录（2026-09-12，前基点 `206370e`）

**改动**
- 新增 `plugin/records/mgs_pending_index.py`（279 行）：待补索引登记的存储与归属唯一恢复职责。以 `PendingIndex(repo, cache_dir, identity, result_markdown)` 参数对象承载并收敛此前逐函数重复传递的四元组；`content_identity` / `digest` / `current_path` / `legacy_path` 为完整内容身份与寻址；`_classify` 是**读取与清除共用的唯一归属核验**（`not_object`/`incomplete`/`foreign`/`owned` 四态），`record`/`load`/`clear` 与 `pending_recovery_result` 为原有文件语义。
- `plugin/records/mgs_result_publication.py` 596→320 行：删去本 module 内的登记存储实现，改为在真实追加路径 `ResultPublication.append` 构造 `PendingIndex` 并在 `_finish`/`_partial_result` 使用其 `load`/`record`/`clear`（不是另建旁路助手）。
- 结构性守卫 `tests/test_records_shared_body.py::test_dependency_direction_static` 扩展：`mgs_github_transport` 不得依赖登记存储；`mgs_pending_index` 不得依赖发布恢复/适配器/查询组织；发布恢复必须在真实路径依赖登记存储；三模块共用传输接缝。TDD 先红（新文件不存在）后绿。

**四元组 Data Clumps 评估（工单要求）**
本区域收敛后调用面清晰、风险低，故引入参数对象 `PendingIndex`：`append` 内一次构造，`load/record/clear` 与方法内寻址都以句柄完整身份为归属基准，消除了 `(repo, cache_dir, identity, result_markdown)` 在模块级四个函数与类方法间的重复传递。持久化布局、文件名、登记 JSON 形态一字未改，故不属兼容风险。

**接缝调整（断言语义未放宽，逐条说明）**
1. `tests/test_github_pending_clear.py`：仅将三个辅助函数 `_current_file`/`_legacy_file`/`_clear` 的调用从发布恢复 module 的模块级函数改为 `mgs_pending_index.PendingIndex(...).current_path()/legacy_path()/clear()`；**全部 `check` 断言逐字未改**，四个案例（外来旧登记保留、同身份双布局清除、逐路径分侧、不可读保守）语义不变。
2. `tests/test_records_shared_body.py`：静态依赖方向测试新增本票分层断言，原断言保留。

**恢复语义红线（只集中不改变）**：碰撞共存、保守披露、旧布局迁移与逐请求清除由 `_classify` 单一粒度承担，读入路径与清除路径不再各写一份核验；不可读/损坏/回执不完整披露文本、`corrupt` 哨兵与 `pending_recovery_result` 返回形态逐字保留。

**验证**
- 主题：`python3 -B tests/test_github_pending_index.py` / `test_github_pending_clear.py` / `test_github_result_recovery.py` / `test_records_shared_body.py` 全 exit 0（碰撞 2 次 POST、损坏不重发、旧布局迁移清除、逐路径清除等断言原样）。
- 五套聚合器全 exit 0；`test_acceptance_client*` 5 文件 exit 0。
- `evidence/baseline/run_baseline.sh` 五套 check 全绿（`all_existing_checks_green=True`），跑后 `git checkout --` 恢复 `results/` 与 `BASELINE-REPORT.md`（冻结产物未变）。
- `./dist/build-package.sh` 重建 dist（manifest 84 文件，含新 module）。
- 净行数：生产 publication 596→320（−276）+ 新增 279 = **净 +3**；测试 +17（两个 seam 文件）。
- 函数长度：`mgs_pending_index` 最长 `_classify` 36 行；`mgs_result_publication` 最长 `append` 60 行，均在 20–60 常规区间。
- 遗留限制：真实远端写入按授权范围未执行（属本任务一贯限制）；票 20 将在两侧入口统一恢复事实。

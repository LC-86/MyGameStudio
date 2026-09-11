# 20: 统一在线执行与草稿重放的恢复事实

**What to build:** 在线受控操作与草稿重放对同一发布结果给出一致事实，不再由多个调用方分别推导或访问私有恢复细节。

**Blocked by:** 19 集中恢复登记的归属与兼容处理

**Status:** resolved

**Spec:** [MyGameStudio 全插件分阶段架构重构 v1](../spec.md) · User Stories 5, 7, 42, 43, 44, 49, 54, 55

**Verification mapping:** 按本票所属阶段的验收集合

- [x] 在线调用、草稿保存和重放从完整恢复 interface 获取已发布程度、索引状态、归属及可继续工作。
- [x] 受控运行入口不直接依赖后端私有草稿保存细节，迁移到能够表达完整结果的职责，原返回字段和错误语义保持。
- [x] 同一请求分别经过在线失败、草稿重放和再次调用，远端发布次数、回执和最终状态一致。
- [x] 结果未知与已经确认发布的部分成功不能互相替代；真实远端已发生动作如实保留。
- [x] 创建、结果追加、关闭等操作的各自可重试条件保持，不引入通用自动重试策略。
- [x] 发布恢复、后端迁移、运行入口及包检查通过；GitHub 大文件按已确认行数与职责约束收口并报告例外。

**依赖理由：** 依赖 19 已集中且经过生命周期验证的恢复登记与结果事实。

## 执行与验证约定

本票已正式发布；实施按对应任务授权执行。沿现有 interface 验证本票行为；保持外部用法、持久化格式、权限与恢复语义，只有明确列出的 R1 属行为修正。每票在新的执行上下文中按实际前置成果接手；产品内容变化时同步相关包与来源检查，记录净行数、必要操作量和未验证限制。

同一共享文件只由一名执行者修改。测试和独立规范/规格评审针对本票实际版本；基线不可被历史结果替代。提交、推送、标签、真实远端写入、日常安装和发布分别沿明确授权执行。

## Comments

用户已确认 26 票拆分及其依赖安排；本票按确认稿发布，未启动实施。

### 执行记录（2026-09-12，阶段 4 收口票，前基点 `e151f4a`）

**统一恢复事实（验收 1/3/4）：**

- 未发布草稿的**存储与重放**自本票起收敛到 `mgs_result_publication`（公开函数 `save_unpublished_draft` / `publish_drafts` / `replay_draft`）：草稿身份（操作+参数+目标仓库）、同秒不覆盖、同操作幂等、跨仓拒绝、完成判定与既有语义逐条保持。在线失败（草稿保存）、草稿重放、再次调用由同一 module 表达同一恢复事实；`GithubBackend._save_draft`/`publish_drafts` 只注入目标仓库、缓存目录与草稿说明并委派。
- 三路一致性核心断言（新增 `test_append_result_three_paths_share_recovery_fact`）：同一请求依次经「离线失败→未发布草稿（0 次评论 POST）」→「草稿重放（部分成功，回执 comment_id/ref + index_updated=False）」→「再次调用（收养同一回执、补齐索引）」→「残留草稿再重放（收敛完成）」，全程评论 POST 恰 1 次、远端评论数恰 1、结果索引含同一回执。未发布/uncertain/partial/完成四态互不替代（既有主题用例同时覆盖）。
- 各操作可重试条件未改动：create 的「超时先回读、未落地才重试一次」、append_result 的「回读确认不存在才重试一次、回读失败停发」、update/close/set_* 的离线草稿语义均沿用原实现，未引入通用自动重试框架（验收 5）。

**受控运行入口迁移（验收 2）：**

- `plugin/runtime/mgs_runtime.py` 原 `backend._save_draft(...)  # noqa: SLF001` 改为经后端**公开写接缝** `backend.record_unpublished_draft(op, args, cause)` 兜底离线草稿。新接缝返回形态与错误语义与 `_save_draft` 完全一致（未发布/草稿路径/原因/说明；未配置缓存目录时抛记录错误），行为由 `test_runtime_gate_remote` 案例 31 固定（离线仍拒绝并回报未发布草稿）。
- 静态守卫 `test_records_shared_body.py::test_runtime_entrypoint_uses_public_draft_seam`：证明 `mgs_runtime.py` 源码不再出现私有草稿名 `_save_draft`，且实际经 `record_unpublished_draft`、后端提供该公开接缝。

**GitHub 大文件收口（验收 6；票 18 留档的 >600 例外）：**

- `plugin/records/mgs_github.py` 1220→549 行（<600，约束内）。剩余写操作适配器之外的三块职责按 module 拆分（纯结构调整，公开名字与语义不变）：
  - 新增 `mgs_github_issue.py`（134 行）：Issue 正文序列化/解析（`build_task_body`/`parse_issue_payload`/`parse_issue_body`）、仓库级授权核对（`authorization_for`）与仓库坐标 GitHub 错误身份（`parse_repo_location`）；`mgs_github` 在公开接缝上重导出同名。
  - 新增 `mgs_github_read.py`（271 行）：`GithubReadMixin`（fetch_tasks/离线缓存回退、_get_issue、read_task、verify 回读核验）；`GithubBackend(GithubReadMixin)` 继承取得，公开方法面不变。
  - 新增 `mgs_github_migration.py`（351 行）：`plan_backend_switch`/`apply_backend_switch`/`handover_baseline_check` 与文本/产出助手；`mgs_github` 经模块级 `__getattr__` 延迟再导出同名（迁移模块在函数内延迟导入 `mgs_github.GithubBackend`，避免加载期互相导入）。
- 无 >600 文件残留（票 18 例外已消除）。行数与函数长度：`mgs_github` 549、`mgs_github_read` 271、`mgs_github_migration` 351、`mgs_github_issue` 134、`mgs_result_publication` 461，均在 200–400 常规区间或 <500；函数最长 `mgs_github_read.verify` 114 行（原样迁入的存量核验事务，含标签存在性/评论一致性/身份重复/关闭原因多段检查，属完整事务例外，记录不改写），其余 ≤77。

**依赖方向守卫扩展（`test_records_shared_body.py`）：** 分层自下而上固定为对称负向断言：transport 不得依赖 {publication, pending_index, github_issue, github, records}；pending_index 不得依赖其上层；publication 不得依赖 {issue, read, migration, github, records}；github_issue 不得依赖其上层；github_read 不得依赖 {publication, pending_index, migration, github, records}；github_migration 不得依赖 {publication, pending_index, records}，并正向固定其经适配器完成目标侧创建（唯一延迟导入例外）。正向固定 `mgs_github` 实际依赖 publication/issue/read。

**验证命令与真实结果（本机实跑，全部离线、零真实远端写入）：**

- 目标主题：`test_github_result_recovery`（含新增三路一致性）、`test_github_pending_index`、`test_github_pending_clear`、`test_github_drafts`、`test_github_write_ops`、`test_records_shared_body`、`test_runtime_gate_remote` 全部 exit 0，断言未放宽。
- 全量 `tests/test_*.py` 逐文件跑：ALL PASS（无失败）。
- 五套聚合器 `test_plugin_package` / `test_runtime_gate` / `test_runtime_boundaries` / `test_records_backend` / `test_github_backend` 全部 rc=0（`test_plugin_package` 先经 `./dist/build-package.sh` 重建 dist 后通过）。
- 冻结基线：`./.scratch/mygamestudio-architecture-refactor/evidence/baseline/run_baseline.sh` → 五套 `PASS`、`all_existing_checks_green=True`；跑完 `git checkout --` 恢复 `results/` 与 `BASELINE-REPORT.md`（冻结产物未改）。
- 可复现构建：`./dist/verify-reproducible.sh` 提交后运行 → tar.gz/manifest/SHA256SUMS 三件套与 `git archive HEAD` 干净副本隔离重建逐字节一致、tar 无 PAX 扩展头，全部 PASS。
- 静态检查：`ruff check` 改动/new 文件残留 2 条（`mgs_github.py` E741×1 + F841×1），均为未触碰的既有代码，无新增；`python3 -m compileall` 通过。

**净行数（物理行，含空行注释；工作树 vs 前基点 `e151f4a`）：**

- plugin：5025 → 5252，**净 +227**（文件 10→13）。分列：`mgs_github.py` −671（1220→549）、`mgs_result_publication.py` +141（320→461）、`mgs_runtime.py` +1（1119→1120）、新增 `mgs_github_issue.py` +134 / `mgs_github_read.py` +271 / `mgs_github_migration.py` +351。
- tests：`test_github_result_recovery.py` +80、`test_records_shared_body.py` +61 → 净 +141（三路一致性用例与依赖方向/入口 seam 守卫）。
- acceptance：净 0；dist：manifest 84→87 文件（+3 新 module），tar.gz 交付包随 plugin 内容重建。

**未验证限制：**

- 真实 GitHub 远端写入按授权范围未执行（本票禁止真实远端写入）；离线替身与回放不替代真实远端验收。
- 真实模型轮与人工体验不在本票范围（全任务一贯限制）。


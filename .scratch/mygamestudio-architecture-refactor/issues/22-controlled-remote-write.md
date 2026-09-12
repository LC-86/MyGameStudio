# 22: 集中受控远端动作与结果审计

**What to build:** 远端受控操作保持授权撤销和审计纪律，调用方能准确得知拒绝、失败或实际已发生的远端结果。

**Blocked by:** 20 统一在线执行与草稿重放的恢复事实；21 集中本地受控写入的完整事务

**Status:** resolved

**Spec:** [MyGameStudio 全插件分阶段架构重构 v1](../spec.md) · User Stories 50, 51, 52, 53, 54, 55

**Verification mapping:** 按本票所属阶段的验收集合

- [x] 实际远端工作入口使用整理后的策略、执行登记及恢复结果职责，现有参数和拒绝阶段保持。
- [x] CONFIG 与实例最终重读及远端动作仍服从原持锁语义；不提前释放网络期间的锁或缓存旧权限。
- [x] 写入意图先持久记录，意图审计不可用时不执行远端动作；动作已发生但结果审计失败时按原语义披露。
- [x] 上游失联、结果不确定、部分成功和恢复路径与 20 的在线/重放事实一致，不绕行直连。
- [x] 可信调度侧的签发、释放、状态与占用回收同完整受控入口的身份纪律一致；不能因移除私有状态访问新增能力。
- [x] 运行时本地/远端与后端恢复回归通过，记录 runtime 的文件职责、行数和保留的必要重读。

**依赖理由：** 同时需要 20 的完整远端恢复事实和 21 的共享身份/持锁职责。

## 执行与验证约定

本票已正式发布；实施按对应任务授权执行。沿现有 interface 验证本票行为；保持外部用法、持久化格式、权限与恢复语义，只有明确列出的 R1 属行为修正。每票在新的执行上下文中按实际前置成果接手；产品内容变化时同步相关包与来源检查，记录净行数、必要操作量和未验证限制。

同一共享文件只由一名执行者修改。测试和独立规范/规格评审针对本票实际版本；基线不可被历史结果替代。提交、推送、标签、真实远端写入、日常安装和发布分别沿明确授权执行。

## Comments

用户已确认 26 票拆分及其依赖安排；本票按确认稿发布，未启动实施。

### 执行记录（2026-09-12）

**集中后的职责清单**（受控远端事务由新职责模块承担，现有 interface 不变）：

| 文件 | 行数 | 职责 |
| --- | --- | --- |
| `plugin/runtime/mgs_remote_write.py`（新） | 377 | 受控远端任务操作的完整事务：远端通道配置读取（`channel`）、项目 CONFIG 后端/仓库目标与 issues-write 授权核对（`config_state`）、远端资源匹配（`remote_match`，含 `/**` 子树覆盖）与授权交集（`remote_grant_denial`，经共享 `grant_denial`）、锁内最终重读与 backend 构建、写入意图先行、远端动作分发（`run_action`）与执行、结果审计与结果表达（`record`）；结果摘要（`remote_summary`）。 |
| `plugin/runtime/mgs_runtime.py`（改） | 676→365 | 门面保留公开方法与既有私有状态接缝（故障注入点）。`remote_record` 一行委派给 `RemoteWriteTransaction.record`；`REMOTE_ACTIONS` 类属性作为兼容定位别名指向 `mgs_remote_write.REMOTE_ACTIONS`。其余公开方法/调度侧操作不变。 |
| `plugin/runtime/mgs_local_write.py`（改） | 437→447 | `grant_denial` 收敛为本地与远端**共用**的授权交集实现（新增 `matcher` / `noun` 关键字参数；本地默认 `match_any` + "path"，远端传 `remote_match` + "remote resource"）；规则与拒绝阶段逐字不变，`purpose_restrict` / `role_patterns` / `PURPOSE_MISSING` 仍为唯一实现。 |

`_remote_grant_denial` 与 `grant_denial` 的重复（票 21 留档 F5）本票收口：两者在 `remote_grant_denial`（mgs_remote_write）→ `grant_denial`（mgs_local_write）收敛为一份实现，差异仅在匹配器（远端 `remote_match` 接受 `/**` 子树覆盖）与拒绝措辞（`noun="remote resource"`），两条路径的规则、拒绝阶段与失效闭合语义一致。

**锁内重读与持锁语义保留证明**（spec 决策 27-28 红线）：
- `mgs_remote_write.RemoteWriteTransaction.record` 的最终临界区（`with host._locked():`，L284-320）内依次重读身份（`_resolve_instance`）、重读策略（`_policy`）、重读项目 CONFIG 与仓库级授权（`config_state`）并**据此构建 backend**、重算授权交集（`remote_grant_denial`）、持久记录写入意图、执行远端动作、追加结果审计。锁外只做「快速拒绝」预检（L256-262）。
- 网络期间持锁语义未放宽：远端传输调用（`run_action`）仍在同一临界区内执行，撤销（`release_instance`）与策略更换持同一把锁，因此撤销完成后在途远端写入在锁内重读时被拒（identity / remote_scope）。锁外读到的 CONFIG 快照不再沿用（`config` 在锁内被覆盖），未缓存旧权限。
- 意图先行与结果披露未变：`action != "read"` 时意图条目先落盘，意图审计不可用即拒绝且不执行（rule_stage=audit）；结果审计失败时如实回报已发生的远端结果并标注 `audit_recorded=False`，不包装成拒绝。
- 上游失联（remote_upstream，不绕行直连）、结果不确定（uncertain）、部分成功（partial）与未发布草稿仍如实区分，在线执行与草稿重放共用后端 `execute_op` 参数分发（`run_action` 与 `publish_drafts` 同一入口）。

**信任的私有状态接缝未移除（条件 5）**：门面的 8 个单行委派接缝（`_locked` / `_read_json` / `_write_json` / `_occupancy_conflict` / `_occupy` / `_policy` / `_audit_unlocked` / `_resolve_instance`）与 `_deny` / `_basis` / `runtime_root` 全部保留并继续经登记职责委派；`RemoteWriteTransaction` 经这些接缝访问状态，没有新增或放大任何能力。调度侧 `init_policy` / `create_instance` / `release_instance` / `list_locks` / `reclaim_locks` 仍经 `mgs_gate_registry`，与完整受控入口共用同一把锁。

**必要重读清单（保留，未删）**：
- 锁外快速预检：`_policy`（1 次）、`_resolve_instance`（1 次）、`config_state`（1 次，CONFIG + 授权）。
- 锁内最终核对：`_resolve_instance`（1 次）、`_policy`（1 次）、`config_state`（1 次，CONFIG + 授权）、`remote_grant_denial`（1 次）、意图/结果审计各 1 次。
- 计数口径不变：baseline `runtime-remote-read` 读取 `policy.json 3 / instances.json 2 / remote.json 1 / CONFIG.md 2`、替身 transport 调用 3 次，与冻结基线逐项一致（`runtime-write` 为 `policy.json 3 / instances.json 2`，本票不涉本地路径，同样一致）。

**测试 seam 变更说明（唯一一处 tests/ 改动，断言未放宽）**：
- 票 20 固化的静态检查 `tests/test_records_shared_body.py::test_runtime_entrypoint_uses_public_draft_seam` 断言「受控运行入口经公开草稿接缝 `record_unpublished_draft` 兜底、不出现私有 `_save_draft`」，原扫描单文件 `runtime/mgs_runtime.py`。本票把兜底草稿调用迁至 `runtime/mgs_remote_write.py` 后，改为扫描 `mgs_runtime.py` **与** `mgs_remote_write.py` 的并集（仍要求整体不含 `_save_draft`、含 `record_unpublished_draft`），并进一步要求 `GithubBackend.record_unpublished_draft` 可调用。断言条件与含义与票 20 相同（覆盖职责迁移后的实际文件），未放宽、未删除。行为侧仍由 `test_runtime_gate_remote.py`（离线草稿回报）与 `test_runtime_gate_recovery_review.py` SP-2/SP-7 固定。其余 runtime 主题与聚合器零改动。

**零丢失**：`evidence/12-case-mapping.md` 的 runtime 主题与原 check 点数量逐条保持（static gate 203 / bounds 44；运行期 gate 259 / bounds 44）；10 个 runtime 主题文件零改动。

**验证命令与真实结果**（全部离线，零网络/零真实远端写入）：
- 10 个 runtime 主题 `python3 -B tests/test_runtime_gate_{local_write,binary_channel,purpose_scope,occupancy,concurrency,remote,review_fix,recovery_review}.py`、`tests/test_runtime_boundary_{service,channel}.py` → 全部 `exit 0`。
- 两聚合器 `tests/test_runtime_gate.py`、`tests/test_runtime_boundaries.py` → `exit 0`。
- 五套聚合器 `tests/test_plugin_package.py`、`test_runtime_gate.py`、`test_runtime_boundaries.py`、`test_records_backend.py`、`test_github_backend.py` → 全部 `exit 0`。
- `sh .scratch/mygamestudio-architecture-refactor/evidence/baseline/run_baseline.sh` → `all_existing_checks_green=True`；受控写入读取计数与冻结基线一致（见上「必要重读清单」），跑完已 `git checkout --` 恢复 `results/` 与 `BASELINE-REPORT.md`。
- 生产内容变化 → `./dist/build-package.sh` 重建（90 文件），提交后 `./dist/verify-reproducible.sh` PASS（见提交报告）。

**净行数（同范围物理行，含空行与注释）**：
- `plugin/runtime/`：265+437+676+261+189=**1828** → 265+447+377+365+261+189=**1904**，净 **+76**（新增远端事务职责 377 行；`mgs_runtime.py` 净 −311；`mgs_local_write.py` +10 为 `grant_denial` 共用参数与文档）。
- 全部 `plugin/` 生产 Python：5510 → 5586（净 +76）。
- `tests/`：11+/6−（`test_records_shared_body.py` 静态扫描范围修正，净 +5）。`acceptance/`：0。`dist/package-manifest.txt`：+1 条目（新职责文件）。

**文件职责与行数、长度例外**：
- 新整理文件 `mgs_remote_write.py` 377 行、`mgs_runtime.py` 365 行、`mgs_local_write.py` 447 行、`mgs_gate_registry.py` 265 行 → 均在 200–400 目标同量级内（local_write 447 略高，为本地完整事务与路径身份的唯一归属，票 21 留档）。票 21 遗留的 `mgs_runtime.py` **>600 行例外本票消除**（676→365）。
- `RemoteWriteTransaction.record` 164 行（>80）例外：与 `LocalWriteTransaction.write`（157 行）同类，是受控远端完整事务，锁外预检与锁内最终核对/意图/执行/结果审计/结果表达必须作为不可分割顺序在同一职责内连续阅读；豁免依据 spec 决策 30「完整事务允许有明确理由的例外」。验证方式：`test_runtime_gate_remote.py`、`test_runtime_gate_recovery_review.py`（SP-1/SP-2/SP-7/SP-10）、`test_runtime_gate_review_fix.py`（R4/R2-remote/R1-remote）全绿。其余函数最大 44 行（`config_state`），全部 ≤80。

**遗留限制**：本票未执行真实模型轮、真实远端写入或人工体验验收（均由独立授权与验收流程承担）。受控远端事务已集中，阶段 5 两票（本地 + 远端）收口；`mgs_runtime.py` 无 >600 行例外残留。

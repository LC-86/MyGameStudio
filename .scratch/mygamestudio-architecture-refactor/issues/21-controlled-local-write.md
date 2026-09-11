# 21: 集中本地受控写入的完整事务

**What to build:** 专业角色经现有受控入口写入文件，授权、占用、落盘和审计回滚的完整顺序保留且集中维护。

**Blocked by:** 09 让直连失败判据通过同一事件入口验证；12 按完整受控操作组织运行保障回归

**Status:** resolved

**Spec:** [MyGameStudio 全插件分阶段架构重构 v1](../spec.md) · User Stories 5, 50, 51, 52, 53, 55

**Verification mapping:** 按本票所属阶段的验收集合

- [x] 将本地写入事务、策略解释与执行登记按完整不变量整理，实际工作实例入口和可信调度操作继续可用。
- [x] 角色、原子任务、用途和授权交集及原拒绝阶段保持；调用方不能自行拼接检查和落盘步骤。
- [x] 最终身份和权限核验、实际写入继续处于原同锁约束下；实例或 CONFIG 撤销后旧请求不能继续写。
- [x] 路径身份、符号链接/换链、资源占用、版本校验和文本/二进制载荷的原语义保持。
- [x] 审计或登记故障按原行为回滚；并发、释放与占用回收场景通过完整入口检查。
- [x] 远端通道在本票过程中保持可用且语义不变，不以拆本地事务为由改变共享锁；记录文件长度与完整事务例外。

**依赖理由：** 依赖 12 稳定的运行保障行为检查和 09 的证据判据；与发布恢复没有直接实现依赖。

## 执行与验证约定

本票已正式发布；实施按对应任务授权执行。沿现有 interface 验证本票行为；保持外部用法、持久化格式、权限与恢复语义，只有明确列出的 R1 属行为修正。每票在新的执行上下文中按实际前置成果接手；产品内容变化时同步相关包与来源检查，记录净行数、必要操作量和未验证限制。

同一共享文件只由一名执行者修改。测试和独立规范/规格评审针对本票实际版本；基线不可被历史结果替代。提交、推送、标签、真实远端写入、日常安装和发布分别沿明确授权执行。

## Comments

用户已确认 26 票拆分及其依赖安排；本票按确认稿发布，未启动实施。

### 执行记录（2026-09-12）

**集中后的职责清单**（受控写入由三个文件承担，现有 interface 不变）：

| 文件 | 行数 | 职责 |
| --- | --- | --- |
| `plugin/runtime/mgs_gate_registry.py`（新） | 240 | 执行登记与策略状态：策略读取/结构校验/指纹、实例登记签发与撤销、写入占用读取/释放/回收、审计追加、唯一服务锁 `GateRegistry.locked()`。撤销、签发、回收与写入共用一个锁对象。 |
| `plugin/runtime/mgs_local_write.py`（新） | 440 | 本地受控写入完整事务：路径模式匹配、角色/用途/任务授权交集（`grant_denial`/`effective_scope`）、用途条目缺失失效闭合（`PURPOSE_MISSING`）、目标规范化与逃逸拒绝（`resolve_target`）、O_NOFOLLOW 逐组件锚定（`open_pinned_parent`）、临时文件与权限位保留（`write_pinned_temp`）、回滚（`rollback`）、锁前预检与锁内最终核对/落盘/回滚的完整顺序（`LocalWriteTransaction`）。 |
| `plugin/runtime/mgs_runtime.py`（改） | 1119→662 | 保留公开门面与受控远端任务操作。`GateService.write`/`scope` 委派给 `LocalWriteTransaction`；`_locked`/`_read_json`/`_write_json`/`_policy`/`_audit_unlocked`/`_resolve_instance` 委派给 `GateRegistry`；调度侧 `init_policy`/`create_instance`/`release_instance`/`list_locks`/`reclaim_locks` 经登记接缝实现。`remote_record` 原样保留（票 22 范围）。 |

调用方不再自行拼接：`mcp_gate` 与全部接缝只调用 `GateService.write`/`scope`/`remote_record`，实际检查、锚定与落盘只在 `mgs_local_write` 内实现一份。

**锁内重读保留证明**（spec 决策 28 红线）：
- `mgs_local_write.LocalWriteTransaction.write` 在 `with host._locked():` 临界区内依次重读身份（`_resolve_instance`）、重读策略（`_policy`）、重新规范化目标、重新计算授权交集、占用与版本判定、路径竞态复检，最后才锚定父目录并落盘。锁外只做「快速拒绝」预检。
- `release_instance`（经 `GateRegistry.release`）与 `init_policy`（经 `write_policy`）持同一把锁；策略恢复/损坏仍返回 `None` 失效闭合。因此撤销完成后在途写入必然在锁内重读中拿到 `identity` 拒绝。
- `remote_record` 的最终身份/策略/CONFIG/授权核对与意图审计、执行、结果审计仍在同一 `with self._locked():` 临界区，共享锁语义未变（条件 6）。
- CONFIG 撤销（SP-1）与本地 `write` 经正常入口改动 CONFIG 的路径由 `test_runtime_gate_recovery_review.py` 印证；实例撤销在途写入由 `test_runtime_gate_review_fix.py` R1/R1-remote 印证。

**零丢失**：未改动任何测试；票 12 的 10 个 runtime 主题与原映射表 `evidence/12-case-mapping.md` 的 check 点数量逐条保持（static gate 203 / bounds 44；运行期 gate 259 / bounds 44）。

**验证命令与真实结果**（全部离线，零网络/零真实远端写入）：
- 10 个 runtime 主题 `python3 -B tests/test_runtime_gate_{local_write,binary_channel,purpose_scope,occupancy,concurrency,remote,review_fix,recovery_review}.py`、`tests/test_runtime_boundary_{service,channel}.py` → 全部 `exit 0`。
- 两聚合器 `tests/test_runtime_gate.py`、`tests/test_runtime_boundaries.py` → `exit 0`。
- 五套聚合器 `tests/test_plugin_package.py`、`test_runtime_gate.py`、`test_runtime_boundaries.py`、`test_records_backend.py`、`test_github_backend.py` → 全部 `exit 0`。
- `sh .scratch/mygamestudio-architecture-refactor/evidence/baseline/run_baseline.sh` → `all_existing_checks_green=True`；受控写入读取计数与冻结基线一致（runtime-write：policy.json 3 / instances.json 2；runtime-remote-read：+remote.json 1 / CONFIG.md 2），跑完已 `git checkout --` 恢复 `results/` 与 `BASELINE-REPORT.md`。
- `git diff` 复核 CONFIG 直接写入的 `test_records_shared_body.py` 方向守卫 → `exit 0`。
- 生产内容变化 → `./dist/build-package.sh` 重建（89 文件），`./dist/verify-reproducible.sh` PASS（提交后执行，见提交报告）。

**净行数（同范围物理行，含空行与注释）**：
- `plugin/runtime/`：1120+261+189=1570 → 240+440+662+261+189=1792，净 **+222**（新增共享职责 680 行，`mgs_runtime.py` 净 −458 行）。
- 全部 `plugin/` 生产 Python：4572 → 4794（净 +222）。
- `tests/`：0（本票不改测试）。`acceptance/`：0。`dist/package-manifest.txt`：+2 条目（两个新职责文件）。

**文件长度与例外**：
- `mgs_gate_registry.py` 240 行、`mgs_local_write.py` 440 行 → 均在新整理文件 200–400 目标的同量级内（440 略高，为完整本地事务与路径身份的唯一归属，未再切分以避免调用方拼接）。
- `mgs_runtime.py` 662 行（>600）例外：本文件是既有文件（1120→662，净减 458），保留的 `remote_record`（181 行）是受控远端完整事务，属票 22 的集中范围；本票条件 6 要求远端通道与本共享锁语义不变，故不在此票拆分。验证方式：`test_runtime_gate_remote.py`、`test_runtime_gate_recovery_review.py`、`test_runtime_gate_review_fix.py`（R4/R2-remote/R1-remote/SP-1）全绿。
- `LocalWriteTransaction.write` 160 行（>80）例外：完整事务允许有明确理由的例外（spec 决策 30）。锁前预检与锁内最终核对/占用/版本/竞态/锚定/落盘/回滚必须作为一个不可分割的顺序保留在同一职责，拆开会给调用方留下跳过其中一步的机会。`remote_record` 181 行同理。其余函数最大 48 行（`_remote_config_state`），全部 ≤80。

**遗留限制**：本票未执行真实模型轮、真实远端写入或人工体验验收（均由独立授权与验收流程承担）；受控远端操作的内部整理属票 22。`mgs_runtime.py` 仍 >600 行，待票 22 收口远端事务后复查。

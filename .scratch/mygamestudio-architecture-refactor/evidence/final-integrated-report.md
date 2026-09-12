# 票 26 全插件集成与重构效益核验报告

- 票：`issues/26-integrated-verification.md`（收口，核心票）
- 本票前基点（开始代码身份）：`9d44d5a9c9f7eda233f26360012f6bef61b640b6`（分支 `codex/architecture-optimization`）
- 交付候选：`mygamestudio` 0.18.0，交付包 `dist/mygamestudio-0.18.0.tar.gz`
- 证据分类：静态事实 / 合成回放 / 现有检查实跑 / 真实宿主验收（本轮未执行，见第 7 节）
- 结论口径：**本报告不宣称「全插件通过」**；安装与发布决定留待用户。票 Status 置 `resolved` 表示本票交付完成（核验结果、交付候选、待授权验收材料齐备）。

---

## 0. 本票实跑总览（当前版本，非历史结果）

全部检查在本工作区当前 HEAD（`9d44d5a`）上真实运行，命令与结果如下。

### 0.1 五套聚合检查（`python3 -B tests/<file>.py`）

| 套件 | 结果 | 退出码 | 耗时(s) |
| --- | --- | --- | --- |
| `test_plugin_package.py` | PASS | 0 | 27 |
| `test_runtime_gate.py` | PASS | 0 | 2 |
| `test_runtime_boundaries.py` | PASS | 0 | 1 |
| `test_records_backend.py` | PASS | 0 | 1 |
| `test_github_backend.py` | PASS | 0 | 3 |

### 0.2 全部主题测试逐文件运行

`tests/test_*.py` 共 **45** 个文件全部逐个实跑，退出码：**45/45 rc=0，fails=0**（含 5 个聚合器与 40 个行为主题文件）。

### 0.3 票 01 基线总入口

`sh .scratch/mygamestudio-architecture-refactor/evidence/baseline/run_baseline.sh` → rc=0，
`all_existing_checks_green=True`，五套聚合器 PASS；跑后以 `git checkout --` 恢复冻结产物（`results/` 与 `BASELINE-REPORT.md`）。

### 0.4 可复现构建

`./dist/verify-reproducible.sh` → **PASS**（干净副本 `git archive HEAD` 隔离重建，三项产物逐字节一致、无 PAX 扩展头）：
交付包 SHA-256 `cc8cf90e42e1bfc1fd4e942d2ea34ba1816823068f16358d82494da0e6e599d4`。

### 0.5 工作区状态

跑完全部检查并恢复冻结产物后，`git status --porcelain` 仅含 `.scratch/.../execution-log.md`（主控进度文件，按约定忽略、不提交、不还原）；生产区 `plugin/ tests/ acceptance/ dist/` 相对起点零改动。

---

## 1. 六十条用户故事逐条核对

类别三选一：**已验证（离线）** / **已验证（真实，引用历史或本轮）** / **未完成（需授权）**。
本轮**未执行**真实模型轮、真实远端写入与日常安装；因此凡核心断言只能由真实模型/宿主/远端证明者标为「未完成（需授权）」，离线可验证部分在「验证结果」中如实注明。`dist/ACCEPTANCE-RESULTS.md`（2026-09-09，任务票 18，137 PASS/0 FAIL）是**重构前** 0.18.0 的历史旁证，**不替代**当前版本验收，不据此计为「已验证（真实）」。

| # | 用户故事（摘） | 当前实现位置 | 本次验证结果（测试/证据） | 类别 |
| --- | --- | --- | --- | --- |
| 1 | 继续用现有业务 Skill 调用方式 | `plugin/skills/game-*/SKILL.md` + `agents/openai.yaml` | `test_package_manifest::test_explicit_skills`（14 入口齐全、frontmatter/`allow_implicit_invocation:false`）离线 PASS；真实对话触发行为未跑 | 未完成（需授权，真实调用） |
| 2 | 已有任务/配置/记录保持可读、不需迁移 | 记录格式未变（`records.md` 合同；本地/GitHub adapter） | READ-08/READ-13 主题套件 PASS；本阶段零持久化格式变更（spec 决策 20） | 已验证（离线） |
| 3 | 原子任务身份/分流/进度/基线与验收含义保持 | `mgs_records.py` 判定；`mgs_record_model.py` | `test_records_deps_ready`、`test_records_baseline`、`test_records_verify` PASS | 已验证（离线） |
| 4 | 每阶段交付可运行可检查的完整行为 | 各阶段收口报告 + 五套件 | `run_baseline.sh` 全绿；26 票全部完成收口（执行日志；工单 `Status:` 为标准五类分流标签、完成进度另列 `Progress:` 行，PR #28 复审 ST-2 修正） | 已验证（离线） |
| 5 | 新增/整理文件有明确职责与长度约束 | `plugin/records/*`、`plugin/runtime/*` 17 文件 | §6 文件清单；>600 行仅 `mgs_records.py` 678（查询编排；CLI 已分离至 `mgs_records_cli.py` 273 行，PR #28 复审 ST-1，理由见 §6.3/§9） | 已验证（离线） |
| 6 | 净减量含共享实现与适配成本 | `mgs_record_model/source`、客户端共享核心 | §6 净行数（同范围口径，含新增成本） | 已验证（离线） |
| 7 | 行为修正与结构调整分别登记 | `task-reading.md#行为修正登记`（R1） | R1 单列；`test_ready_second_call_reflects_changes_without_cross_call_cache` PASS | 已验证（离线） |
| 8 | 每阶段保留可说明的回退方式 | 各票基点 SHA；`b8cda58`；阶段交付提交见 execution-log | §6.6 回退参照表 | 已验证（离线） |
| 9 | 一次可开工查询只获取一份任务集合 | `mgs_records.py::_read_workspace/_Reading` | `test_ready_reads_config_and_each_task_once`、`test_github_ready_fetches_task_set_once` PASS；探针 CONFIG 1 / task 1 / 集合 1 | 已验证（离线） |
| 10 | 配置字段与执行条件来自同一份 CONFIG 原文 | `mgs_records.py::_read_workspace` 单次读文本 | `test_(github_)ready_*_config_once*` PASS；基线探针 CONFIG 1 | 已验证（离线） |
| 11 | 下一次查询重新读取 | `_read_workspace`（无跨调用缓存） | `test_ready_second_call_reflects_changes_without_cross_call_cache` PASS | 已验证（离线） |
| 12 | 可开工集合继续说明它不是执行授权 | `mgs_records.py:23` 注释 + `ready` note | `test_records_deps_ready` 断言 `"授权" in note` PASS | 已验证（离线） |
| 13 | 列举任务继续按目录顺序 | 本地 adapter（目录排序） | `test_ready_and_deps_preserve_directory_order`、`test_list_and_show_read_config_once_and_preserve_order` PASS | 已验证（离线） |
| 14 | list/ready/deps 各自保留原有顺序 | 排序独立投影 | `test_github_ready_and_list_order_preserved` PASS | 已验证（离线） |
| 15 | show 继续按指定任务目录读取 | `mgs_records.py::read_task` | `test_show_locates_by_directory_without_scanning_unrelated` PASS | 已验证（离线） |
| 16 | 读取单任务不扫描无关任务 | 本地 adapter 只打开目标 | 同上（只打开该 task.md）PASS | 已验证（离线） |
| 17 | GitHub show 继续读 Issue 详情与评论 | `mgs_github_read.py` | `test_github_list_show_read_config_once_and_necessary_reads` PASS | 已验证（离线） |
| 18 | 远端不可用时仍能辨认缓存来源与时间 | `cached/fetched_at/source/cache_note` | `test_github_ready_online_to_offline_preserves_source` PASS | 已验证（离线） |
| 19 | 无缓存明确失败、不回退本地 | GitHub adapter 失败路径 | `test_offline_cache_and_no_local_fallback`、`test_github_backend_does_not_read_local_tasks` PASS | 已验证（离线） |
| 20 | CLI list 返回原有 JSON 数组与字段 | `mgs_records.py::_cli` | `test_cli_list_show_projection_and_exit_codes`、entry_probe 11 案例 PASS | 已验证（离线） |
| 21 | 其他读取命令参数/字段/错误/退出码保持 | `_cli` 退出码合同 | entry_probe `{success:0, records_or_file_error:2, judgement_failure:1}` 与票 01 冻结基线一致 | 已验证（离线） |
| 22 | 脚本运行与 Python 导入同一错误类型 | `mgs_record_model.py::RecordsError` | `test_error_identity_across_import_orders_and_script`、`test_record_model_shared_body_and_error_identity` PASS | 已验证（离线） |
| 23 | 双后端共同字段只按一套规则解析 | `mgs_record_model.py` 共享正文 | `test_record_model_cross_backend_body_semantics` PASS | 已验证（离线） |
| 24 | 标签优先级/分流冲突/关闭原因保留 | GitHub adapter 专有规则 | `test_label_priority_and_conflict_preserved`、`test_close_reasons` PASS | 已验证（离线） |
| 25 | 畸形任务仍能进入核验 | `verify` 不提前过滤 | `test_verify_malformed_records_still_discoverable` PASS | 已验证（离线） |
| 26 | 基线格式修正/实质变化/原版本完成事实分别表达 | `baseline_report` 双指纹 | `test_baseline_report_states`、`test_baseline_report_affected_tasks` PASS | 已验证（离线） |
| 27 | 迁移计划与交接读取保持原语义 | `mgs_github_migration.py` | `test_switch_local_to_github`、`test_handover_baseline_check`、`test_handover_reachability_requires_executed_check` PASS（替身零真实写入） | 已验证（离线） |
| 28 | 判据与运行脚本用同一可调用 interface | `acceptance/18/evidence_judgement.py` + `evidence_adapter.sh` | `test_event_judgement_shell_adapter` PASS（适配层 source 进 shell） | 已验证（离线） |
| 29 | 判据核对真实事件/资源/动作/命令归属 | `evidence_judgement.py`（mcp-deny/curl-direct-deny） | `test_event_judgement_*` 全主题 PASS（含 legacy-branches-red） | 已验证（离线） |
| 30 | 通过离线事件回放检查判据 | 具名夹具 `tests/plugin_package_fixtures.json` | `test_event_judgement_retained_evidence`、`test_event_judgement_input_consistency` PASS | 已验证（离线） |
| 31 | 测试按行为主题组织 | `tests/test_*.py` 45 文件、最大 432 行 | §0.2 全绿；无文件 >500 行 | 已验证（离线） |
| 32 | 正向对照/历史反例/已接受限制有对应关系 | `evidence/10-case-mapping.md`、`11`、`12` | 三个映射表 + 聚合器零丢失三重证明 | 已验证（离线） |
| 33 | 测试不再正则截取 Shell 源码 | 无源码截取（grep 复核为零） | `test_package_event_judgement.py` 不 `re` 抽取 run.sh（见 §3 复核） | 已验证（离线） |
| 34 | 保留实际运行脚本的接入检查 | `evidence_adapter.sh`/`run.sh` 接线 | `test_event_judgement_shell_adapter`、`test_event_judgement_runsh_wiring` PASS | 已验证（离线） |
| 35 | 十八场景共用通信与等待实现 | `acceptance/_shared/appserver_core.py` 389 行 | `test_all_scenarios_use_shared_core_no_local_implementation` PASS（18/18 委托） | 已验证（离线） |
| 36 | 各场景保留身份与必要选项（不抹平五族差异） | 18 薄壳 78–104 行 | `test_acceptance_client_families/absolute/relative` 族身份与选项合同 PASS | 已验证（离线） |
| 37 | 事件增量消费、每条输入只解码一次 | 共享核心逐行缓存 | `test_decode_once_over_ten_polls`（1000 vs 票 01 的 21000）PASS | 已验证（离线） |
| 38 | 普通完成/失败/超时/筛选保持原结果 | 共享核心模式 | `test_failure_paths_and_argument_contract`、`test_old_new_replay_parity` PASS | 已验证（离线） |
| 39 | 绝对与相对中断阈值分别保留 | `appserver_core.py` 三种模式 | `test_shared_core_modes_stay_distinct`、`test_relative_mode_ignores_prior_round_history_multiround` PASS | 已验证（离线） |
| 40 | 退出码与子进程生命周期保持 | 共享核心进程组/退出 | `test_absolute_threshold_interrupt_controlled_process`、`test_controlled_process_*` PASS | 已验证（离线） |
| 41 | 重复 GitHub 替身共用实现 | `acceptance/_shared/standin_github.py` 273 行 | `test_shared_standin_is_sole_copy` PASS（唯一副本） | 已验证（离线） |
| 42 | 未发布/结果未知/待补索引/完成四态区分 | `mgs_result_publication.py` | `test_append_result_readback_failure_keeps_uncertain`、`test_append_result_partial_success_and_retry_completion` PASS | 已验证（离线） |
| 43 | 超时/不确定时先回读远端 | 发布恢复接缝 | `test_append_result_read_first_failure_without_pending_keeps_first_try`、`test_append_result_partial_retry_read_first_timeout_no_duplicate` PASS | 已验证（离线） |
| 44 | 已发布待补索引重试只补剩余 | `mgs_pending_index.py` | `test_append_result_pending_*` PASS | 已验证（离线） |
| 45 | 恢复登记核对完整请求归属（碰撞） | `mgs_pending_index.py::PendingIndex` | `test_append_result_pending_collision_does_not_adopt_foreign_identity`、`..._both_partial_coexist` PASS | 已验证（离线） |
| 46 | 损坏登记明确披露并保留必要信息 | 登记读取损坏分支 | `test_append_result_pending_registration_corrupt_json_keeps_recovery`、`..._missing_fields_disclosed_corrupt` PASS | 已验证（离线） |
| 47 | 旧恢复登记布局按原约定读取/迁移 | 兼容分支 | `test_append_result_pending_legacy_flat_registration_compatible` PASS | 已验证（离线） |
| 48 | 清除恢复登记只影响当前请求 | 逐路径核验清除 | `test_clear_pending_index_verifies_each_path_independently`、`..._keeps_foreign_legacy_registration` PASS | 已验证（离线） |
| 49 | 在线执行与草稿重放复用相同恢复事实 | `result_publication` 统一生命周期 | `test_append_result_online_and_execute_op_share_recovery_fact`、`test_append_result_three_paths_share_recovery_fact` PASS | 已验证（离线） |
| 50 | 角色/任务/用途/实际授权共同约束写入 | `mgs_local_write.py`/`mgs_remote_write.py` | `test_runtime_gate_local_write`、`test_runtime_gate_purpose_scope`、`test_runtime_gate_remote` PASS | 已验证（离线） |
| 51 | 撤销完成后旧请求仍被拒绝 | 锁内重读 CONFIG/实例 | `test_runtime_gate_review_fix`（R1 实例撤销）、`test_runtime_gate_recovery_review`（SP-1 CONFIG 在途撤销）PASS | 已验证（离线） |
| 52 | 路径身份/换链/资源占用检查保持 | `mgs_gate_registry.py` | `test_runtime_gate_occupancy`、`test_runtime_gate_concurrency`、`test_runtime_boundary_service` PASS | 已验证（离线） |
| 53 | 本地写入审计/登记失败按原语义回滚 | `mgs_local_write.py` 事务 | `test_runtime_gate_review_fix`（R3 审计失败回滚）PASS | 已验证（离线） |
| 54 | 远端已发生结果在审计失败时仍如实披露 | `mgs_remote_write.py` | `test_runtime_gate_review_fix`（R4 远端已发生结果）PASS | 已验证（离线） |
| 55 | 完整受控操作封装在同一职责 | local_write/remote_write 完整事务 | §9 集中归属；调用方不拼装授权与提交步骤（`write`/`record` 单入口） | 已验证（离线） |
| 56 | 入口说明保留选择条件/输入输出/专业差异 | 14 `SKILL.md` + 三处权威 | `test_skill_authority_references`、`test_package_skill_content_*` PASS（内容存在）；「足以指导正确工作」需真实模型 | 未完成（需授权，行为充分性） |
| 57 | 共同规则/写入协议/结果字段各有唯一维护位置 | `common.md`/`gate-protocol.md`/`result.md` | `test_skill_authority_references`（锚点标题行匹配 + 悬空检查 + 内联复制清零）PASS | 已验证（离线） |
| 58 | 十四入口继续仅显式触发 | `agents/openai.yaml: allow_implicit_invocation:false` | `test_explicit_skills` 覆盖 14/14 PASS；真实普通对话不触发需真实模型 | 未完成（需授权，真实触发行为） |
| 59 | 来源/许可/固定上游方法/引用闭包完整 | `provenance/`、`internal/methods/`、`LICENSE` | `test_internal_material_provenance`、`test_internal_methods_closure`、`test_internal_references_resolve`、`test_provenance_version_consistency`、`test_dist_package_consistent` PASS | 已验证（离线） |
| 60 | 每阶段报告实际检查/未验证项/匹配交付包 | 各票 Comments + `evidence/stage1-closeout.md` + 本报告 | 阶段收口报告与 execution-log 留档；交付包与当前生产一致（§7.2） | 已验证（离线，报告与匹配包）；真实安装对照未跑 |

**统计（60 条）**：已验证（离线）**56**；已验证（真实）**0**；未完成（需授权）**4**（#1、#56、#58 的真实行为，#60 的安装/发布决定）。
> #1/#56/#58 的**结构性/静态部分已离线验证**（入口存在、显式触发旗标、权威引用可达）；表中类别按「整条故事的最终断言」取最强未满足项，避免以离线通过冒充真实行为。

---

## 2. READ-01 至 READ-14 逐条核对（当前版本实跑）

票 07 阶段收口报告（`evidence/stage1-closeout.md`）给出映射；下表为本轮在当前 HEAD 上对同一批测试的**重新实跑确认**（非引用历史）。

| ID | 场景 | 覆盖测试（本轮文件位置） | 本轮结果 | 结论 |
| --- | --- | --- | --- | --- |
| READ-01 | 本地正常 ready | `test_records_deps_ready::test_ready_reads_config_and_each_task_once`、`::test_deps_reads_once_and_ready_does_not_recall_public_dependency_entry` | PASS | CONFIG 原文 1、每 task 1、依赖 1；分类保持 |
| READ-02 | GitHub 正常 ready | `test_github_ready_list_show::test_github_ready_fetches_task_set_once` | PASS | 全量集合 GET 1 次 |
| READ-03 | 第二响应改变依赖（R1） | `test_github_ready_list_show::test_github_ready_does_not_consume_second_response_r1`、`test_records_deps_ready::test_ready_second_call_reflects_changes_without_cross_call_cache` | PASS | 第二响应不消费；无两时点混合；下一调用刷新 |
| READ-04 | 两调用间改配置/任务/基线 | 同上 + `test_records_baseline::test_baseline_reads_config_and_core_docs_once` | PASS | 第二次读到新内容；无跨调用缓存 |
| READ-05 | 远端不可用有/无缓存 | `test_github_ready_list_show::test_github_ready_online_to_offline_preserves_source`、`::test_github_offline_list_show_metadata_and_no_marker_leak`、`test_github_config_backend::test_offline_cache_and_no_local_fallback` | PASS | 来源/时间/标识保持；无缓存失败；不回退本地 |
| READ-06 | 排序差异 | `test_records_deps_ready::test_ready_and_deps_preserve_directory_order`、`test_github_ready_list_show::test_github_ready_and_list_order_preserved` | PASS | 各入口原排序保持 |
| READ-07 | 目录名≠身份、任务缺失 | `test_records_read::test_show_locates_by_directory_without_scanning_unrelated`、`::test_cli_list_show_projection_and_exit_codes` | PASS | 按目录定位；错误/退出码 2 保持 |
| READ-08 | 双后端同正文/空字段/畸形 | `test_github_config_backend::test_record_model_cross_backend_body_semantics`、`::test_label_priority_and_conflict_preserved`、`::test_verify_shared_core_validation_both_backends`、`test_records_shared_body::test_record_model_shared_body_and_error_identity` | PASS | 共通字段一致；后端专有与分流保留 |
| READ-09 | CLI 成功/阻塞/失败 | `test_records_read::test_cli*`、`test_records_deps_ready::test_cli_deps_and_ready`、`test_records_baseline::test_baseline_cli`、`test_github_cli::*`；entry_probe 11 案例 | PASS | JSON 类型/字段/原因/退出码兼容；无 envelope |
| READ-10 | 两导入顺序与脚本错误 | `test_github_config_backend::test_error_identity_across_import_orders_and_script`、`test_records_shared_body::test_source_shared_with_query_and_import_orders` | PASS | 单一错误身份；退出码 2；无未捕获 traceback |
| READ-11 | show/verify 与本地结果核验 | `test_github_ready_list_show::test_github_list_show_read_config_once_and_necessary_reads`、`test_github_config_backend::test_verify_offline_keeps_unchecked_and_skipped`、`test_records_verify::test_verify_reads_config_and_tasks_once_local`、`::test_verify_results_consistency` | PASS | 必需读取发生；离线 skipped 与结果文件核验保持 |
| READ-12 | 撤销/审计故障/在途 | `test_runtime_gate_review_fix`、`test_runtime_gate_recovery_review`（SP-1）、`test_runtime_boundary_service` | PASS | 锁内重读、拒绝、回滚、远端已发生披露保持 |
| READ-13 | 迁移计划与交接 | `test_github_migration_handover::*`、`test_github_cli::test_cli_github_handover_end_to_end`、`::test_cli_reverse_migration_real_entry` | PASS | 映射/引用/权限保持；替身零真实写入 |
| READ-14 | 入口与交付兼容 | `test_package_manifest::*`、`test_package_provenance::*`、`test_package_dist::*`、`dist/verify-reproducible.sh` | PASS | 脚本/MCP 引用/指纹/清单/无开发机路径；隔离重建逐字节一致 |

**结论：READ-01～14 在当前版本逐条有实跑覆盖且全部 PASS，无历史替代。**

---

## 3. 阶段 0-6 退出条件核对（7 项，design.md 阶段表）

| 方向 | 退出条件 | 当前证据（本轮实跑） | 达成 |
| --- | --- | --- | --- |
| 阶段 0 固定基线 | 基线可复跑；已知限制与行为修正登记 | `run_baseline.sh` rc=0、`all_existing_checks_green=True`；R1 与已知限制在 `baseline/README.md`、`stage1-closeout.md` 登记 | 是 |
| 阶段 1 读取统一 | `task-reading.md` 成立；两后端/CLI/来源/兼容调用有结果 | READ-01～14 全 PASS；CONFIG 6→1、任务集合 2→1 实测 | 是 |
| 阶段 2 判据与测试 | 正反例映射保留；真实脚本接入同一判据；测试不再正则抽源码 | `evidence/10-case-mapping.md`（1630→1631 check，0 丢失）；`test_event_judgement_shell_adapter/runsh_wiring` PASS；测试无源码正则截取（grep 复核零） | 是 |
| 阶段 3 客户端 | 五族回放一致；中断/事件选择/退出码/生命周期保留；净行数与解码复测 | `test_acceptance_client*` 四主题 + `test_acceptance_github_standin` PASS；客户端 4605→1664；解码 21000→1000 | 是 |
| 阶段 4 发布恢复 | 碰撞/损坏/旧布局/待补索引/重复调用完整生命周期通过 | `test_github_result_recovery`、`test_github_pending_index`、`test_github_pending_clear`、`test_github_drafts` PASS | 是 |
| 阶段 5 受控写入 | 锁内撤销/换链/占用/审计失败/回滚语义保持；不以减少重读替代撤销 | `test_runtime_gate_*` 8 主题 + `test_runtime_boundary_*` 2 主题 PASS；runtime 读取计数 policy 3/instances 2 未变 | 是 |
| 阶段 6 Skill 与交付 | 引用闭包/来源指纹/显式调用/专业语义通过；实际执行效果有对照 | `test_skill_authority_references`（14 入口 + 标题行锚点 + 内联复制清零）PASS；产品说明字节 −50.4%；**实际模型执行效果未跑**（见 §7） | 结构达成，行为待授权 |

---

## 4. 离线 / 替身 / 真实宿主 / 人工 四分证据表述

- **离线（确定性，本轮实跑）**：五套聚合器、45 个主题测试、`run_baseline.sh` 五探针、`verify-reproducible.sh`、entry_probe 11 案例。零网络、零凭据、零真实模型。
- **替身（本地注入，本轮实跑）**：GitHub 后端全部经 `FakeTransport`/`standin_github.py`；远端受控写入经 `GateService` 替换；客户端经受控进程/回放 adapter。计数 `network_requests_to_remote=0`。
- **真实宿主（本轮未执行，需授权）**：真实模型 turn、真实 GitHub 远端读写、日常客户端安装替换、真实网络耗时。历史 `dist/ACCEPTANCE-RESULTS.md`（137 PASS/0 FAIL，2026-09-09，任务票 18）是**重构前**产品版本的旁证，**不作为当前版本证据**。
- **人工（本轮未执行）**：真实试玩/视觉与音频体验、人工反馈三态。历史反馈（02/11 通过、06/10 待验收）同样只作引用。

---

## 5. 兼容性复核（不用历史通过替代）

每项均引用一个**本轮实跑**的主题测试作为证据：

| 复核项 | 实跑证据（本轮） | 结果 |
| --- | --- | --- |
| 权限撤销（实例撤销 / CONFIG 在途） | `test_runtime_gate_review_fix`（R1 实例撤销在途）、`test_runtime_gate_recovery_review`（SP-1 CONFIG 在途撤销 + R1-remote） | PASS：旧请求被拒、远端零写入、目标不变 |
| 恢复碰撞 | `test_github_pending_index::test_append_result_pending_collision_does_not_adopt_foreign_identity`、`..._both_partial_coexist` | PASS：不冒认、不覆盖、共存 |
| 旧布局 | `test_github_pending_index::test_append_result_pending_legacy_flat_registration_compatible`、`test_github_pending_clear::test_append_result_pending_clear_removes_same_identity_both_layouts` | PASS：旧扁平布局可读/迁移/逐请求清除 |
| 证据判据 | `test_package_event_judgement` 全主题（含 `legacy_branches_red` 反例、`retained_evidence`、`runsh_wiring`） | PASS：真实事件驱动、示例文本不能冒充 |
| 五族客户端 | `test_acceptance_client_families`、`_absolute`、`_relative`、`test_acceptance_client`、`test_acceptance_github_standin` | PASS：五族回放一致、身份与选项保留、替身唯一副本 |
| 十四个显式入口 | `test_package_manifest::test_explicit_skills`（14/14）+ `test_skill_authority_references`（14 入口引用三处权威） | PASS：入口齐全、`allow_implicit_invocation:false`、引用可达 |
| 原调用兼容 | `test_records_interface::test_public_interface_surface_and_factory_parameters`、`test_records_shared_body`、`test_github_cli`、entry_probe 11 案例 | PASS：公开函数/工厂参数面、导入顺序、CLI 退出码保持 |

---

## 6. 效益对照表（票 01 基线 vs 当前；同范围物理行）

统计口径与票 01 完全一致：tracked `.py/.sh/.js/.ts/.tsx`，位于 `plugin/tests/acceptance/dist`，排除 `evidence/`、`fixtures/`；物理行含空行与注释。

### 6.1 净行数（同范围）

| 范围 | 票 01 基线 | 当前 | 净变化 |
| --- | --- | --- | --- |
| plugin（生产） | 4526（5 文件） | **5586（16 文件）** | **+1060** |
| tests | 9086（5 文件） | **13078（52 文件）** | **+3992** |
| acceptance | 20739（44 文件） | **17995（46 文件）** | **−2744** |
| dist（脚本） | 146（2 文件） | 146（2 文件） | 0 |

- 生产 +1060 构成：新增 11 个承担完整职责的 module（model/source/pending_index/publication/transport/issue/read/migration/gate_registry/local_write/remote_write，共 3325 行）与既有文件拆分，扣除被吸收的重复后为净增；符合 spec 32「拆文件不算净减量」口径，如实计新增共享与适配成本。
- 测试 +3992：三大测试文件按主题拆分（票 10/11/12）的入口壳与共享支撑开销 + 覆盖补齐（票 07/17 等），非判定逻辑删减后反增。
- acceptance −2744：客户端共享化为主因（客户端 4605→1664，−2941），另含 run.sh 去 heredoc。

### 6.2 客户端共享化（同一口径实测）

| 指标 | 票 01 基线 | 当前 | 变化 |
| --- | --- | --- | --- |
| 客户端文件数 | 18 | 18 | 0 |
| 客户端总行数 | 4605 | **1664** | **−2941** |
| 行为族数 | 5 | 5 | 0 |
| 重复实现范围行数 | 5141 | **2326** | **−2815**（已扣除共享核心 389 + 共用替身 273 等新增成本） |
| 共享 GitHub 替身副本 | 2 份 536 行 | 1 份 273 行 | 收拢 |

> 票 17 工单已披露：收口前口径取票 01 全量副本而非直接父提交。spec 33 的规划估计为 3000–3500；实测 Net Reduction = **2815**（低于规划估计下限，属如实负向偏差，已在报告中标注）。

### 6.3 最大文件与函数

| 项 | 票 01 基线 | 当前 | 说明 |
| --- | --- | --- | --- |
| 最大生产文件 | `mgs_github.py` 1848 | `mgs_records.py` **678** | 复审修复后（原 897；CLI 已分离至 `mgs_records_cli.py`，见 §9）；678 >600 例外理由见 §9 |
| 第二大生产文件 | `mgs_runtime.py` 1119 | `mgs_github.py` 549 | 549 ≤600 |
| 最大生产函数 | `_cli` 223 / `append_result` 185 / `remote_record` 180 | `_cli` 223（`mgs_records_cli.py`）、`record` 164、`write` 157 | 均为参数分发或读-执行-审计-回滚**完整事务豁免**（spec 30） |
| 最大测试文件 | 4024 | **432**（≤500 目标） | 全部 ≤500 |
| 最大测试函数 | 1499 | **153**（`test_accept16_secret_scan_gate`） | 8 个测试函数 >80（均为原样迁入的注入边界例，留档） |
| 最大顶层验收脚本 | — | `acceptance/16/run.sh` 1417 | >300 目标；属旧大文件，随所属阶段处理（票 10/13-17 已把客户端核心抽出） |

### 6.4 读取与解码计数（合成回放）

| 指标 | 票 01 基线 | 当前 | 目标 |
| --- | --- | --- | --- |
| 本地 ready：CONFIG 原文读取 | 6 | **1** | 6→1 ✅ |
| 本地 ready：任务集合获取 | 2 | **1** | 2→1 ✅ |
| 本地 ready：每份 task.md | 2 | **1** | — ✅ |
| GitHub ready：全量集合请求 | 2 | **1** | ✅ |
| baseline/verify：CONFIG | 2 | **1** | ✅ |
| 客户端：1000 事件 ×10 轮询 JSON 解码 | 21000 | **1000** | 每条输入一次 ✅ |
| runtime 受控写入读取 | policy 3 / instances 2 | policy 3 / instances 2 | 未回退 ✅ |

> 达成目标与规划估计的区分：读取计数 6→1、2→1 与「每条输入一次解码」为**已达成并实测**；客户端净减 2815 属**实测值**（低于 3000–3500 规划估计）；token/成本/端到端耗时下降**未测量**，不宣称（见 §7）。

### 6.5 产品说明字节/字符（票 25 基点 `2820ce2` → 当前，口径分列）

| 位置 | 基点字节 | 当前字节 | 字节变化 | 基点字符 | 当前字符 | 字符变化 |
| --- | --- | --- | --- | --- | --- | --- |
| `plugin.json` description | 1285 | 710 | −575 | 611 | 386 | −225 |
| `plugin.json` longDescription | 10193 | 3455 | −6738 | 4063 | 1375 | −2688 |
| `plugin.json` shortDescription | 44 | 56 | +12 | 16 | 20 | +4 |
| `provenance/manifest.md` | 23531 | 13149 | −10382 | 11841 | 7053 | −4788 |
| **合计** | **35053** | **17370** | **−17683（−50.4%）** | **16531** | **8834** | **−7697（−46.6%）** |

> 字节（`len(s.encode('utf-8'))`）与字符（`len(s)`）两套口径各自一致、不混算；本轮以同一脚本对当前工作区与 `2820ce2` 重算吻合票 25 结论。文本缩短**不等于** token/成本/耗时下降（未实测）。

### 6.6 回退参照

| 层级 | 提交 | 说明 |
| --- | --- | --- |
| 规格 / 任务发布基线 | `b8cda58ea2ff3b0fb18ae7d888cbd5d01eaca586` | 26 票发布基线 |
| 规格代码基线 | `49f3b1e7323c02a5fd39f3d9c847df023c4f2459` | spec 记录 |
| 本票前基点 | `9d44d5a9c9f7eda233f26360012f6bef61b640b6` | 票 25 收口后 |
| 阶段 1 收口 | `15c6efe`（阶段 1 交付 `ce6c81f` 起） | 阶段 1 匹配代码与包 |
| 阶段 2 收口 | `e0380af` | 阶段 2 |
| 阶段 3 收口 | `d3e8474`→`3d5c25a` | 阶段 3 |
| 阶段 4 收口 | `acad8f3` | 阶段 4 |
| 阶段 5 收口 | `b20607e`→`57d5439` | 阶段 5 |
| 阶段 6 收口 | `f6819f8`→`77b4adf` | 阶段 6 |

各阶段交付提交与复审记录完整见 `.scratch/mygamestudio-architecture-refactor/execution-log.md`。回退只涉及代码与匹配包，本重构**未修改用户数据或持久化格式**，无需数据迁移。

---

## 7. 交付候选信息

### 7.1 版本身份

- 包名/版本：`mygamestudio` `0.18.0`（`plugin/.codex-plugin/plugin.json`）
- 交付包：`dist/mygamestudio-0.18.0.tar.gz`，SHA-256 `cc8cf90e42e1bfc1fd4e942d2ea34ba1816823068f16358d82494da0e6e599d4`
- 清单：`dist/package-manifest.txt`（90 条），SHA-256 `b1b055ba43ee6c5afcdaa25fac6c96403f2299b806a508ec3b6f52287a5f8822`
- 校验和：`dist/SHA256SUMS.txt`，SHA-256 `ff7dd99cf047207fcc32f3d7a1176d894a5c769ff581a7b384235e2c60e0ee1a`
- 来源指纹：`plugin/provenance/fingerprints.json`，SHA-256 `3b8ce1d7f87743125bdab8fa341351c9ec89ef15e86aa33abb098c16b0837156`
- 来源清单：`plugin/provenance/manifest.md`，SHA-256 `10969a4a78222177826e43f980dd20f0671d2cce6e718a3eeb712721acd0de8c`
- `plugin/.codex-plugin/plugin.json`，SHA-256 `cbca0c1b6a850d5068873cca8efd07bd7f1c65179fdf46d4a200c263b134cfc4`

### 7.2 生产代码逐文件清单（16 文件，物理行 / sha256 前 16）

| 行数 | sha256(16) | 路径 |
| --- | --- | --- |
| 897 | 62d77ffd260aeb1e | plugin/records/mgs_records.py |
| 549 | 75665f4c6c186988 | plugin/records/mgs_github.py |
| 461 | 0a8b511228799a4d | plugin/records/mgs_result_publication.py |
| 447 | 6d9fcd7445a97cc8 | plugin/runtime/mgs_local_write.py |
| 377 | c4ddfb2e5793a5eb | plugin/runtime/mgs_remote_write.py |
| 365 | 14678bb169291622 | plugin/runtime/mgs_runtime.py |
| 351 | 50e5afed58c6bf75 | plugin/records/mgs_github_migration.py |
| 325 | 0070a9e7d5939305 | plugin/records/mgs_record_model.py |
| 279 | 4688bb35e829bdfd | plugin/records/mgs_pending_index.py |
| 271 | 961765dc994266f4 | plugin/records/mgs_github_read.py |
| 266 | 2fa9fdbffc2ad52c | plugin/records/mgs_record_source.py |
| 265 | 6f88fc12f88f3a10 | plugin/runtime/mgs_gate_registry.py |
| 261 | 3c2b755916bd8246 | plugin/runtime/mcp_gate.py |
| 189 | cca626a8dc2809d2 | plugin/runtime/mgsrt_admin.py |
| 149 | 4a1d95b1f11d9382 | plugin/records/mgs_github_transport.py |
| 134 | 6b3fc632dab1fcf5 | plugin/records/mgs_github_issue.py |
| **5586** | | **合计** |

### 7.3 隔离可复现构建

`./dist/verify-reproducible.sh` PASS：`git archive HEAD` 干净副本隔离重建，tar.gz / package-manifest.txt / SHA256SUMS.txt 三项与交付物逐字节一致，且无 PAX 扩展头。**当前工作树未提交时该脚本比对的是 HEAD 已提交内容**，故本票提交后由主控在收口时复跑核对（本票自身不安装、不发布）。

### 7.4 本票不自行安装或发布

本票**不安装**到日常客户端、**不发布**、**不推送**、**不打标签**。

---

## 8. 未完成项与执行材料（需用户授权）

以下真实环境验收在本任务中**无授权执行**；已备具体目标、预估成本/影响与执行材料，供用户决定后执行。全部命令均在仓库根、隔离 `HOME/CODEX_HOME` 于 `/tmp`、凭据符号链接、不触碰用户日常客户端。

| # | 验收项 | 具体目标 | 预估成本 / 影响 | 执行材料（命令/入口/清单） |
| --- | --- | --- | --- | --- |
| U1 | 真实模型轮（整包） | 9 个真实模型 turn：入口发现、普通对话不触发、代表闭环、运行保障回归、版本升级 | 模型账户用量（约 9 turn，历史单遍含 5 次运行）；不改本地状态；约 30–60 分钟 | `./acceptance/18-complete-package-acceptance/run.sh`（默认 `/tmp/mygamestudio-accept-18`，见 `dist/REPRODUCE.md` §2、同目录 `runbook.md`） |
| U2 | 真实远端写入 | GitHub Issues 读写/标签/迁移 apply | 对指定测试仓库产生真实写入；需 host/owner/repo 与授权 | `acceptance/17-github-issue-workflow/run.sh` 的 `--api-base` 指向真实 API 后重放（`dist/REPRODUCE.md` 末节） |
| U3 | 日常安装替换 | 隔离环境安装副本、14 入口发现 | 仅隔离 HOME/CODEX_HOME；不改用户配置 | `dist/REPRODUCE.md` §5：`codex plugin add mygamestudio@personal --json`，期望恰 14 个 `game-*` |
| U4 | 人工体验 | 真实试玩/视觉/音频体验与人工反馈三态 | 人工时间；不改产品 | 各 `acceptance/<n>/runbook.md`；历史反馈见 `dist/ACCEPTANCE-RESULTS.md`（06/10 待验收） |
| U5 | 安装与发布决定 | 是否安装/发布 0.18.0 交付候选 | 用户决定；本票不执行 | `dist/mygamestudio-0.18.0.tar.gz` + `package-manifest.txt` + `SHA256SUMS.txt` + `REPRODUCE.md` |

**未完成即不宣称通过**：U1–U5 未执行前，不得将本票结论表述为「全插件通过」或「真实宿主已验收」。

---

## 9. 职责例外与已知限制（如实登记）

1. `plugin/records/mgs_records.py` 678 行 >600（2026-09-12 PR #28 复审 ST-1 修复后；原 897 含 CLI）：CLI 已分离至 `mgs_records_cli.py`（273 行，参数解析/输出投影/退出码；旧脚本 `mgs_records.py` 保持原调用入口，子命令/参数/输出/退出码合同不变）。剩余为统一查询组织，不可拆部分是**一次顶层读取的完整生命周期**：CONFIG 原文→任务集合→同一份已读核心文档（版本/指纹/受影响任务推导）在同一次调用内同源闭合（spec 9/10），`_dependency_graph`/`_ready_classification`/`baseline_report`/`verify_project` 都是这条生命周期上的判断层，与读取计时、来源元信息（cached/fetched_at）交织；纯助手（指纹计算、能力短语等）虽可再移，但单独成文件不构成职责边界，只会增加转发层（task-reading 明确不为行数写空转发）。验证方式：五套检查 + records/github 主题套件 + CLI 全路由退出码（CLI 用例走真实脚本入口）。
2. 生产函数 `_cli` 223（2026-09-12 起位于 `mgs_records_cli.py`）、`record` 164、`write` 157、`verify` 114 行 >80：均为**完整事务**例外（spec 30）。`_cli` 的事务边界是一次 CLI 调用的端到端分发：参数解析→业务分发→JSON 输出投影→退出码合同（`RecordsError`/`OSError`→2、verify/deps/baseline/handover `ok=False`→1），错误映射与退出码判定分散到别处会把同一事务的失败语义拆开，故不按分支数机械切分；该例外自阶段一收口（evidence/stage1-closeout.md §5.3）登记并延续，PR #28 审查亦按 223 行实测而未将其列为违规项。`record`/`write`/`verify` 为读-执行-审计-回滚完整事务。
3. `acceptance/16-producer-complete-loop/run.sh` 1417 行 >300 目标：顶层验收脚本为旧大文件，客户端核心已抽入 `_shared/appserver_core.py`（票 13-17）；run.sh 本体随所属阶段处理。
4. 客户端净减实测 2815 行，**低于** spec 33 规划估计 3000–3500；属如实负向偏差，未以改写口径制造收益。
5. token/模型成本/端到端耗时下降**未测量**：产品说明缩短仅以字节/字符/行数为可复核常量；技能加载策略与上下文裁剪未实测，不据此宣称。
6. 真实网络耗时与全部宿主行为未验证；合成探针不推导端到端倍数。
7. 历史 `dist/ACCEPTANCE-RESULTS.md` 为重构前版本旁证，不替代当前版本验收。
8. 8 个测试函数 >80 行（最大 153）为原样迁入的注入边界例，留档不重写。

---

## 10. 工作区与代码身份记录

- 开始代码身份：HEAD `9d44d5a9c9f7eda233f26360012f6bef61b640b6`，分支 `codex/architecture-optimization`；工作区仅 `.scratch/.../execution-log.md` 已修改（主控进度文件）。
- 结束代码身份：见本次收口提交（票文件 Status 与本报告入库）。生产区本票**零行为变更**。
- 独立规范/规格评审：本票为核心票，按主控安排由主控统一执行独立 code-review 复审（implement 技能末尾 /code-review 自审已按指引跳过）。
- 提交/推送/发布：提交按本票授权执行一次；推送、打标签、安装、发布分别留待各自明确授权。

---

## 11. 结论

- 全部**离线可验证项**（五套聚合器、45 主题测试、`run_baseline.sh` 全部探针与闭包、可复现构建、判据回放、五族客户端 A/B 对照、十四入口引用闭包、权限撤销/碰撞/旧布局/兼容面复核）在**当前版本本轮实跑全部通过**。
- 六十条用户故事 **56 条离线已验证、4 条需授权**；READ-01～14、六方向（阶段 0–6）退出条件逐条有当前证据。
- 交付候选（0.18.0，包 SHA-256 `cc8cf90e…`）与当前生产逐字节一致、隔离重建可复现；回退参照齐备。
- **真实模型轮、真实远端写入、日常安装与人工体验未有授权执行**，已按 U1–U5 备好目标、成本与执行材料。
- **本报告不宣称「全插件通过」；安装与发布决定留待用户。**

---

## 11. PR #28 双轴审查修复轮更新（2026-09-12）

PR #28 双轴独立审查（Standards ST-1/ST-2、Spec SP-1/SP-2，均 P2）未通过后，
按 /implement 完成四项修复；本节更新现势状态，历史章节数字保留当时口径：

1. **ST-1**：CLI 职责分离——`mgs_records.py` 897→678（查询编排），
   新增 `mgs_records_cli.py` 273（命令行层，旧脚本入口/参数/输出/退出码不变）；
   §6.3/§9 已同步更新，>600 例外仅剩 `mgs_records.py` 678（理由见 §9.1）。
2. **ST-2**：26 张工单 `Status:` 恢复标准五类分流值 `ready-for-agent`，
   完成进度另列 `Progress:` 行；本报告第 4/5 行与执行日志流程备忘已修正。
3. **SP-1**：`appserver_core` 恢复各行为族原等待策略（中断族 0.3 秒、
   普通族 1 秒），新增 `wait_poll_seconds` 显式参数与三组回归
   （接线/虚拟时钟 A/B/受控进程 late-reply）。
4. **SP-2**：`_doc_texts` 按解析后实际路径复用已读文本，别名映射只读一次，
   新增别名映射回归（红→绿）。

修复后全量测试与可复现构建核验见 `evidence/review-fix-2026-09-12.md`。

# 票 11 原案例 → 新位置映射(任务后端回归拆分)

原 `tests/test_records_backend.py`(1560 行、40 个 `test_*` 顶层函数)与
`tests/test_github_backend.py`(2758 行、56 个 `test_*` 顶层函数)按真实行为
主题拆为 15 个可独立运行的主题文件 + 3 个共享支撑模块;原总入口保留为
聚合器,运行方式与输出不变。生产内容 `plugin/`、`dist/` 零改动。

## 一、原顶层函数 → 主题文件

`tests/test_records_backend.py`(40 个 `test_*` 全部保留身份,仅位置改变):

| 新主题文件 | 行数 | 行为主题 | 迁入的原函数 |
| --- | --- | --- | --- |
| `test_records_read.py` | 284 | 本地后端读取(配置/列表/单任务/CLI) | `test_load_config_on_sample`, `test_load_config_missing`, `test_unsupported_backend`, `test_github_backend_does_not_read_local_tasks`, `test_list_tasks_on_sample`, `test_list_tasks_empty_root`, `test_read_task`, `test_cli`, `test_list_and_show_read_config_once_and_preserve_order`, `test_show_locates_by_directory_without_scanning_unrelated`, `test_cli_list_show_projection_and_exit_codes` |
| `test_records_verify.py` | 234 | 本地与 GitHub 后端核验 | `test_verify_ok_sample`, `test_verify_label_failures`, `test_verify_docmap_failures`, `test_verify_task_failures`, `test_verify_results_consistency`, `test_verify_malformed_records_still_discoverable`, `test_verify_reads_config_and_tasks_once_local`, `test_verify_github_reads_single_task_set_and_keeps_backend_reads` |
| `test_records_deps_ready.py` | 369 | 依赖解析与可开工集合 | `test_parse_dep_ids_ignores_dates`, `test_task_dependencies_graph`, `test_task_dependencies_unresolved_and_cycle`, `test_startable_tasks_set`, `test_capability_negation_not_flagged`, `test_startable_ignores_done_and_wontfix`, `test_verify_deps_consistent`, `test_cli_deps_and_ready`, `test_ready_reads_config_and_each_task_once`, `test_deps_reads_once_and_ready_does_not_recall_public_dependency_entry`, `test_ready_second_call_reflects_changes_without_cross_call_cache`, `test_ready_and_deps_preserve_directory_order` |
| `test_records_baseline.py` | 200 | 核心基线指纹与受影响任务 | `test_baseline_report_states`, `test_baseline_report_affected_tasks`, `test_baseline_cli`, `test_baseline_reads_config_and_core_docs_once` |
| `test_records_shared_body.py` | 194 | 共享正文、来源归属与错误身份 | `test_record_model_shared_body_and_error_identity`, `test_dependency_direction_static`, `test_source_shared_with_query_and_import_orders`, `test_loaded_config_local_read_is_same_source` |
| `test_records_interface.py` | 98 | 公开接口兼容面 | `test_public_interface_surface_and_factory_parameters` |
| `test_records_backend.py`(聚合器) | 63 | 原总入口 | `main` |

`tests/test_github_backend.py`(56 个 `test_*` 全部保留身份):

| 新主题文件 | 行数 | 行为主题 | 迁入的原函数 |
| --- | --- | --- | --- |
| `test_github_config_backend.py` | 425 | 配置、拉取、离线缓存与核验 | `test_parse_repo_location`, `test_parse_remote_authorizations`, `test_load_config_github_backend`, `test_fetch_and_dispatch`, `test_offline_cache_and_no_local_fallback`, `test_verify_github_backend`, `test_verify_offline_keeps_unchecked_and_skipped`, `test_verify_shared_core_validation_both_backends`, `test_record_model_cross_backend_body_semantics`, `test_error_identity_across_import_orders_and_script`, `test_label_priority_and_conflict_preserved` |
| `test_github_ready_list_show.py` | 301 | 一次来源 ready 与列表/单任务读取 | `test_github_ready_fetches_task_set_once`, `test_github_ready_does_not_consume_second_response_r1`, `test_github_ready_and_list_order_preserved`, `test_github_ready_online_to_offline_preserves_source`, `test_startable_tasks_reports_cache_metadata`, `test_github_list_show_read_config_once_and_necessary_reads`, `test_github_offline_list_show_metadata_and_no_marker_leak` |
| `test_github_write_ops.py` | 278 | 写操作(授权闸门/防重/超时回读/更新/关系/关闭) | `test_write_requires_authorization`, `test_create_and_duplicate_protection`, `test_create_timeout_reads_back_before_retry`, `test_update_task_fields_and_version_check`, `test_set_triage_and_append_result`, `test_relations_native_and_fallback`, `test_close_reasons`, `test_update_change_note_three_paths` |
| `test_github_drafts.py` | 215 | 离线草稿保存与发布归属 | `test_offline_write_draft_and_publish`, `test_offline_write_without_cache_dir_refuses`, `test_draft_unique_identity_no_overwrite`, `test_draft_identity_includes_repo_cross_repo`, `test_publish_drafts_refuses_cross_repo_draft` |
| `test_github_migration_handover.py` | 253 | 后端切换迁移与交接基线可达 | `test_switch_local_to_github`, `test_switch_github_to_local_consistency`, `test_handover_baseline_check`, `test_handover_reachability_requires_executed_check`, `test_reachability_probe_carries_no_credentials` |
| `test_github_cli.py` | 180 | GitHub 后端 CLI 真实入口 | `test_cli_github_write_ops`, `test_cli_local_backend_refuses_write_subcommands`, `test_cli_github_handover_end_to_end`, `test_cli_reverse_migration_real_entry` |
| `test_github_result_recovery.py` | 299 | 结果发布的部分成功、未知与重试恢复 | `test_append_result_readback_failure_keeps_uncertain`, `test_append_result_partial_success_and_retry_completion`, `test_append_result_draft_replay_partial_keeps_draft`, `test_append_result_partial_retry_read_first_timeout_no_duplicate`, `test_append_result_read_first_failure_without_pending_keeps_first_try`, `test_append_result_partial_without_cache_dir_carries_degraded_warning` |
| `test_github_pending_index.py` | 339 | 待补索引登记:碰撞、损坏与旧布局迁移 | `test_append_result_pending_collision_does_not_adopt_foreign_identity`, `test_append_result_pending_registration_missing_fields_disclosed_corrupt`, `test_append_result_pending_registration_corrupt_json_keeps_recovery`, `test_append_result_pending_collision_both_partial_coexist`, `test_append_result_pending_registration_missing_receipt_disclosed_corrupt`, `test_append_result_pending_legacy_flat_registration_compatible` |
| `test_github_pending_clear.py` | 257 | 待补索引清除归属(逐路径核验) | `test_append_result_pending_clear_keeps_foreign_legacy_registration`, `test_append_result_pending_clear_removes_same_identity_both_layouts`, `test_clear_pending_index_verifies_each_path_independently`, `test_clear_pending_index_unreadable_path_kept_quietly` |
| `test_github_backend.py`(聚合器) | 71 | 原总入口 | `main` |

## 二、原共享准备代码 → 共享支撑模块

| 原符号 | 新位置 |
| --- | --- |
| `check` / `FAILURES` | 两支撑模块的 `make_checker()`(每主题独立清单 + `run_theme`) |
| `CONFIG_TEMPLATE` / `TASK_TEMPLATE` / `RESULT_TEMPLATE` / `PLAN_TASK_TEMPLATE` | `records_backend_support.py` |
| `make_plan_project` / `make_project` / `run_cli` | `records_backend_support.py` |
| `FP_LINES` / `_register_fingerprint` | `records_backend_support.py` |
| `scoped_read_counter` / `_imported_modules` | `records_backend_support.py` |
| `_GithubVerifyTransport` / `_github_issue` | `records_backend_support.py` |
| `CONFIG_TEMPLATE` / `make_github_project` / `CLI` / `FIVE_LABELS` / `REPO` / `AUTH` | `github_backend_fixtures.py` |
| `FakeTransport` / `backend_for` | `github_backend_transport.py` |
| `LOCAL_TASK` / `make_local_project` | `github_backend_fixtures.py` |
| `run_cli` / `_StandinServer` | `github_backend_fixtures.py`(HTTP 替身,复用 `FakeTransport`) |
| `SHARED_BODY` / `_seed_raw_issue` | `github_backend_fixtures.py` |
| `_issue_list_calls` | `github_backend_transport.py` |
| `_ConfigReadCounter` | `github_backend_fixtures.py` |
| `_pending_digest` / `_pending_full_digest` | `github_backend_transport.py` |
| `_pending_registration_content` | `github_backend_transport.py` |
| `_OnceReadFailTransport` | `github_backend_transport.py` |

共享模块只做夹具与替身准备,判定一律经真实 `mgs_records` / `mgs_github`
公开接缝(`load_config` / `list_tasks` / `read_task` / `verify_project` /
`task_dependencies` / `startable_tasks` / `baseline_report` / `github_backend`
与后端写操作)。不把生产解析/判定规则复制进测试。唯一例外是两个摘要复算
助手 `_pending_digest` / `_pending_full_digest`:它们按原样迁入,仅用于自证
复审给定的确定性碰撞对在当前实现下确实解析到同一/不同登记文件(前置断言),
不是对登记归属判定的重新实现——归属仍由 `append_result` 的真实结果证明。

## 三、案例计数口径

| 口径 | 原文件 | 拆分后 |
| --- | --- | --- |
| `test_records_backend.py` 顶层 `test_*` 函数 | 40 | 40(主题文件内,身份不变) |
| `test_records_backend.py` `check()` 调用点 | 180 | 180(逐字切出,AST 主体相同) |
| `test_github_backend.py` 顶层 `test_*` 函数 | 56 | 56 |
| `test_github_backend.py` `check()` 调用点 | 350 | 350 |
| 运行一期实际发出的 `check()` 条数(records) | 211 | 211 |
| 运行一期实际发出的 `check()` 条数(github) | 389 | 389 |

零丢失判定(三重):①对原文件与全部主题文件做 AST 顶层符号主体比对,原
60/79 个顶层符号中共享夹具与 `main` 之外的全部 40+56 个 `test_*` 函数主体
逐字节相同;②原文件与主题的 `check()` 调用点计数相等(180→180、350→350);
③插桩收集一次完整运行实际发出的全部 `check()`(条件+消息),把集合 `repr`
顺序、时间戳与临时路径归一化后,原实现与新聚合入口发出数完全相同
(records 211→211、github 389→389)、去重后逐条相等(missing=0 extra=0)。
同一归一化口径下,同为原实现的两次运行之间也逐条相等,证明该归一化未掩盖
真实差异。

## 四、行数与函数长度

| | 原 | 新 |
| --- | --- | --- |
| records 侧:入口文件 | 1560 | 聚合器 63 + 6 主题 1379 + 支撑 366 |
| github 侧:入口文件 | 2758 | 聚合器 71 + 9 主题 2547 + 支撑(transport 222 + fixtures 292) |
| 最大文件 | 2758 | 425(`test_github_config_backend.py`) |
| 最大函数 | 88 | 88(`test_append_result_pending_clear_keeps_foreign_legacy_registration`,原样迁入) |

净行数:新 20 个 Python 文件合计 4940 行;原 2 个入口 4318 行。新增
622 行来自 15 个主题文件与 3 个支撑模块的头部/docstring/入口壳与共享导入
(拆分文件不计净减量;无判定逻辑删除)。

函数长度:绝大多数 20–71 行;仅两个审查修复票固化的报告边界例超过 80 行
(`test_append_result_pending_clear_keeps_foreign_legacy_registration` 88、
`test_append_result_pending_collision_both_partial_coexist` 85),均按原样
迁入、未重写断言,记录为保留例外。

## 五、独立运行与故障注入

- 独立主题运行:`python3 -B tests/<主题>.py`,15 个主题全部 `exit 0`。
- 总运行:两聚合器 `exit 0`,运行方式与输出保持与原入口一致。
- 故障注入(隔离 `/tmp` 副本,未污染仓库):对 15 个主题各注入一次生产
  规则错误,被注主题 `exit 1`,所选无关主题 `exit 0`;两聚合器在被注主题
  失败时 `exit 1` 并点名失败条目;恢复后全部回绿。

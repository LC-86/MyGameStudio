# 统一设计问答框架:整体与效率验收总报告(票 09)

日期:2026-09-14。分支:`codex/unified-game-design-framework`。
本报告是票 09 的可追溯总报告,按工单 11 条验收框组织;结论分三层:
**行为通过情况 / 两种模式的步骤与耗时结果 / 限制与尚待解决事项**。

**总判定:25 个行为场景的结构化接缝测试在本候选版本上均有实际复跑证据;
该结论只覆盖公共接缝函数测试,不等于真实宿主端到端交互验收已完成。
效率部分因优化前基线不可比,结论为「效率尚未验证」,不报告统一框架效率验收通过。**

---

## 1. 最终候选内容身份与前置工单成果核对

### 1.1 候选身份(固定)

| 项 | 值 |
| --- | --- |
| HEAD 提交 | 票 09 收口时为 `de8a87ea46c26c5500f0d76f8a1319a23677759d`；PR #38 审查修订后以本分支最新 HEAD 为准 |
| 插件版本 | `0.18.1`(未升版本) |
| `plugin/` 树 SHA-256 | `ad4f88ecb8e4db59b5739c4c8dbea6b86a32d12206a98832601e519519674d4b` |
| `dist/` 内容身份 | `2730df50a6121b453e37bb5467e48e8f4ddf268deea3745638f8a035000cc364`(对 `find dist -type f \| sort` 的逐文件 SHA-256 列表再取 SHA-256;发行包内 120 个文件) |
| 优化前基线树哈希(票 01) | `9e8ee19858cadd246a56212a173d12c39873bca8f2e165be531de8b657b44eb7` |

候选树哈希由 `acceptance/_shared/design_discussion_metrics.py identity --plugin plugin` 生成
(与票 01 同一 interface)。上表 plugin/dist 身份是票 09 收口冻结值。PR #38 审查修订已改
`plugin/` 并按 `sh dist/build-package.sh` 重建 dist(仍为 0.18.1、120 个文件);
当前身份以本分支 HEAD 与重建后的 `dist/SHA256SUMS.txt` 为准,见
`evidence/review-38-fix.md`。

### 1.2 前置工单成果与测试证据

票 02～08 的接缝与测试均在本候选树上存在,本票**逐文件实跑**核对(不是引用作者自述):

| 票 | 接缝(存在性已核对) | 测试文件 | 实跑结果 |
| --- | --- | --- | --- |
| 02 | `plugin/skills/game-design/rounds.py` | `tests/test_design_discussion_rounds.py`(20 函数) | OK |
| 03 | `decisions.py`/`decision_records.py`/`decision_mapping.py`/`decisions_cli.py` | `tests/test_design_discussion_decisions.py`(11) | OK |
| 04 | `spec_draft.py`/`spec_render.py`/`spec_sync.py`/`spec_report.py`/`spec_draft_cli.py` | `tests/test_design_discussion_spec_draft.py`(12) | OK |
| 05 | `coverage_map.py`/`journey.py`/`full_design.py`/`full_render.py`/`full_report.py`/`gate_commit.py`/`full_design_cli.py` | `tests/test_design_discussion_full_design.py`(10) | OK |
| 06 | `change_flow.py`/`change_impact.py`/`change_input.py`/`change_render.py`/`change_report.py`/`change_flow_cli.py` | `tests/test_design_discussion_change_flow.py`(18) | OK |
| 07 | `removal.py`/`removal_impact.py`/`removal_cli.py` | `tests/test_design_discussion_feature_removal.py`(13) | OK |
| 08 | `checks.py`/`check_state.py`/`check_evidence.py` | `tests/test_design_discussion_incremental_checks.py`(17) | OK |
| 01 | `acceptance/_shared/design_discussion_metrics.py` | `tests/test_design_discussion_metrics.py`(15) | OK |

复跑方式:本次新增只读取证脚本
`.scratch/design-discussion-rounds/evidence/verify_scenario_tests.py`,逐 `test_*`
函数调度既有测试文件并读取各文件自身收集的失败项(不重写断言),输出见
`evidence/scenario-test-results.json`。票 09 当时为 108/108;PR #38 审查修订后
主题入口新增 8 个反例函数,当前为 **116 个测试函数**(命令:
`python3 -B tests/test_design_discussion_*.py`)。原 108 项取证结果仍可核验,
但不能覆盖本轮新增反例。
受影响的旧结果不作为当前已通过:上表全部为本次实跑,而非复用历史输出。

## 2. 25 个行为场景逐项核对

场景编号取自规格「验收场景」1～25。每行给出覆盖它的实际测试函数;
全部结果为接缝测试实跑(票 09 为 108 个函数;审查修订后主题入口为 116 个),运行命令见第 1.2 节。
「引用未受影响且可核验的旧结果」一律未采用:全部重跑。

| # | 场景 | 覆盖的实际测试(文件::函数) |
| --- | --- | --- |
| 1 | 成组与依赖 | `rounds::test_first_round_asks_ready_questions_and_defers_dependency` |
| 2 | 阅读结构 | `rounds::test_round_uses_fixed_question_layout` |
| 3 | 完整与自由回答 | `rounds::test_maps_per_question_and_adopt_all_only_shown`;`rounds::test_open_question_does_not_invent_options`;`decisions::test_normal_save_matches_shown_questions_and_reads_back`(落盘与用户回复一致、被拒选项不作要求) |
| 4 | 部分与模糊回答 | `rounds::test_maps_partial_override_freeform_and_vague`;`rounds::test_negated_or_ambiguous_replies_stay_pending` |
| 5 | 边界场景 | `rounds::test_boundary_revision_updates_later_questions`;`decisions::test_changed_decision_keeps_history_and_replacement` |
| 6 | 及时保存与恢复 | `decisions::test_read_only_unsaved_and_restore_prevents_reasking`;`decisions::test_resume_after_interruption_keeps_valid_parts`;`decisions::test_repeated_same_answer_creates_no_duplicate`;`decisions::test_restore_merges_by_revision_not_filename` |
| 7 | 轻量同步 | `spec_draft::test_full_module_handoff_from_adopted_decisions`;`spec_draft::test_history_pending_and_unrelated_content_preserved`;`spec_draft::test_module_sync_keeps_unrelated_baseline_rules` |
| 8 | 未同步与失败 | `decisions::test_conflict_denied_and_unconfirmed_report_true_state`;`decisions::test_states_do_not_conflate_saved_synced_implemented_verified`;`spec_draft::test_read_only_and_missing_sync_authorization_keep_pending`;`spec_draft::test_format_claim_blocks_when_semantics_changed`;`spec_draft::test_after_write_check_failure_does_not_complete_handoff`;`change_flow::test_missing_sync_authorization_does_not_write_baseline` |
| 9 | 长问题组 | `rounds::test_long_group_batches_complete_questions` |
| 10 | 事实与权限 | `rounds::test_missing_fact_waits_only_dependent_question`;`decisions::test_mcp_gate_tool_entry_saves_and_denies`;`change_flow::test_read_only_and_scope_keep_product_untouched` |
| 11 | 文档用途 | `spec_draft::test_full_module_handoff_from_adopted_decisions`(ADR 三项条件同时成立才单列 + `adr_rejected`;术语表只承载术语) |
| 12 | 检查分层 | `incremental_checks::test_round_save_checks_before_and_after_without_global_rerun`;`incremental_checks::test_converge_runs_once_with_real_scope` |
| 13 | 复用失效 | `incremental_checks::test_invalidation_only_drops_affected_parts`;`test_revoked_authorization_rechecks_only_affected`;`test_conflict_and_write_failure_invalidate_target`;`test_new_design_mode_covers_all_invalidation_paths`;`test_change_mode_covers_all_invalidation_paths` |
| 14 | 新设计入口与覆盖 | `full_design::test_extracts_known_material_and_builds_coverage_map`;`full_design::test_scope_layers_and_template_fill_guard` |
| 15 | AI 参与设计 | `rounds::test_unknown_and_experience_stay_proposals` |
| 16 | 模块规格完整性 | `spec_draft::test_missing_key_content_reports_incomplete_without_defaults`;`spec_draft::test_full_module_handoff_from_adopted_decisions`(九类标题 + 单位/范围/计算/取整/依据 + 验收三要素) |
| 17 | 整体流程与文档交付 | `full_design::test_full_flow_delivers_four_outputs_and_detects_planted_contradiction`;`full_design::test_journey_walkthrough_finds_existing_contradiction`;`full_design::test_missing_delivery_locations_keep_draft` |
| 18 | 阶段与证据 | `full_design::test_stage_boundaries_follow_required_outcomes_not_round_count`;`spec_draft::test_handoff_states_stay_separate_from_implementation_and_playtest` |
| 19 | 变更识别 | `rounds::test_classifies_new_design_for_missing_module`;`test_classifies_spec_gap_without_reasking`;`test_classifies_design_change_for_existing_feature`;`test_classifies_implementation_deviation_without_rewriting_design`;`test_classifies_mixed_request_separately`;`test_classifies_covered_request_details_as_spec_gap` |
| 20 | 变更目标与影响 | `change_flow::test_extracts_change_statements_and_does_not_reask_decided`;`change_flow::test_traces_direct_and_indirect_impact_by_real_dependency` |
| 21 | 阶段适配 | `change_flow::test_stage_adapts_checked_objects_for_three_project_stages`;`change_flow::test_three_stages_and_directional_fixture_cover_contract`;`change_flow::test_unverified_stage_blocks_change_plan`;`feature_removal::test_data_and_entitlements_follow_stage_with_authorization_split` |
| 22 | 删减闭合 | `feature_removal::test_lists_original_roles_and_only_asks_undecided_handling`;`test_dispositions_cover_three_kinds_without_forced_replacement`;`test_residual_dependencies_trace_indirect_and_classify`;`test_scope_separates_permanent_deferral_and_promise`;`test_sync_retires_rules_references_and_acceptance`;`test_record_reports_removal_dispositions_and_scope` |
| 23 | 局部微调 | `rounds::test_authorized_local_tweak_skips_questions`;`change_flow::test_depth_organizes_work_and_keeps_valid_decisions`(局部微调分支) |
| 24 | 方向变化与旧证据 | `change_flow::test_depth_organizes_work_and_keeps_valid_decisions`;`change_flow::test_old_validation_result_keeps_original_version` |
| 25 | 变更交付与授权 | `change_flow::test_syncs_affected_design_and_keeps_unaffected_content`;`change_flow::test_read_only_and_scope_keep_product_untouched`;`feature_removal::test_sync_retires_rules_references_and_acceptance`;`feature_removal::test_read_only_and_scope_keep_unauthorized_objects_untouched` |

**核对口径说明。** 这些场景均由测试直接调用公共接缝并断言行为结果
(落盘文件内容回读、受控通道写入/拒绝、台账与状态),不是 Skill 文本关键词
检查。该表只证明接缝函数测试有证据,不能扩大为真实宿主交互验收无缺口。

**接缝测试缺口:无;高层真实交互验收:未完成。** 25 个场景在当前树上均有
结构化接缝测试证据。规格第 226 行要求高层入口贯穿 Game-Design 提问、
开发者回答、决定落盘与 Game-Spec 同步;本系列未在真实宿主会话中实跑该
完整链路(见第 5 节第 2 条)。需要指出的边界:所有场景的输入材料为调用方
给出的结构化材料(讨论产出的结构化结果),测试覆盖的是从结构化材料到可见
回复/记录/交付的行为链,不覆盖"从自由文本自动抽取规则"的语义解析能力
(该能力不在本框架工单范围内,票 04～08 已在 Comments 的「例外」中逐票声明,
本票沿用同一边界,不重复扩大)。

## 3. 效率验收:结论「效率尚未验证」

### 3.1 本次复跑基线(记录当前宿主状态)

2026-09-14 在隔离副本中复跑同一采集入口(原票 01 证据目录未覆盖):
`sh .tmp/dd09/accept/rerun/baseline/run_baseline.sh`(复制自
`evidence/baseline/run_baseline.sh`,仅改 REPO_ROOT/BASE_DIR/ENVROOT/ARENA
避免覆盖原始证据)。结果:**14 PASS / 0 FAIL**;8 个真实 turn 均
`turn/completed`;策略字节未变(未扩大权限);令牌已脱敏核对。

两类场景的 metrics 与票 01 完全同型:

| 场景 | comparable | status | 读取/写入/检查/工具 | 例外 |
| --- | --- | --- | --- | --- |
| 新设计(gear-city) | `false` | `incomplete` | 0 / 0 / 0 / 0 | `external_fault` + `incomparable` |
| 变更(tide-pool) | `false` | `incomplete` | 0 / 0 / 0 / 0 | `external_fault` + `incomparable` |

宿主原始记录:`codex-cli 0.154.0`;`codex-code-mode-host` 启动失败
(`No such file or directory`),模型侧报告自述「未能读取磁盘上的技能与项目
文件、未调用 `mgs_write`」(`evidence/rerun-2026-09-14/*/n1|c1-report.md`)。
四轮 `decision_save_ms=not_applicable`;`processing_ms=incomplete`
(按票 01 口径不保留缺工作的墙钟时长当基准)。

**该外部故障在 2026-09-14 复跑中仍未恢复,是持续存在的外部故障证据。**

### 3.2 票 01 基线状态(不可比,固定不变)

票 01 已认定:优化前版本(插件树 `9e8ee1…`)在本机无法完成约定的成果语义
(未完成最终规格同步,成果范围与约定不一致),两类场景均
`comparability.comparable=false`、`status=incomplete`。按规格「效率通过条件」
第 4 条:「缺少可比较样本、计时边界不完整或存在明显环境干扰时,结论为
『效率尚未验证』」。同时按第 2 条,步骤减少但耗时未满足条件时,只能报告
步骤改善,不能将本项验收判为通过。

### 3.3 结论与理由

- **效率结论:效率尚未验证(不是通过,也不是失败判定)。**
- 理由:缺少可比较样本。优化前无法完成相同成果语义 → 无有效「优化前」
  耗时基准;本次复跑证明外部故障持续 → 也无法用新采集补出可比较基准。
  因此不存在任何合法的前后配对,更不存在三组有效配对。
- 本报告**不给出**完整模块处理用时中位数、模块累计决定保存用时中位数的
  任何数值或改善百分比;不伪造、不推断配对数据。耗时维度整体未验证。

### 3.4 可核实的步骤/检查行为层面改善(仅行为证据,耗时未验证)

下述改善来自票 08 测试在本次实跑中的断言结果(结构化行为证据),证明
**步骤与检查行为**符合规格,不代表耗时已减少:

1. 连续三轮仅新增本模块决定时:一次调用读 3 个文件后全程零重读
   (`test_round_save_checks_before_and_after_without_global_rerun`:
   `ev["reads"]["file_ops"]==3`、三轮写 3 次 `ev["writes"]["file_ops"]==3`),
   每轮保存前后都有核对,未改核心基线时全局重查记 `skipped` 至少 3 次。
2. 模块收敛后一次性统一核对,范围按真实影响(当前模块/跨模块/全局)
   (`test_converge_runs_once_with_real_scope`)。
3. 输入未变时零重读、无关模块列入 excluded;仅改 mtime 不判有效;
   内容变化只重读该资料(`test_read_plan_reuses_unchanged_and_excludes_unrelated`)。
4. 成稿/变更/交接/删减接入同一时机约定:写入按文件分别计数、每文件逐次
   经通道校验,复跑零重读(`test_full_design_delivery_reuses_reads_and_records_writes`、
   `test_change_flow_reuses_reads_and_records_writes`、`test_spec_handoff_and_removal_share_timing`)。
5. 权限与版本校验未被缓存跳过:逐次范围核对数等于轮数
   (`len(channel.scopes)==len(answers)`)——即效率改善不是以少做必要检查换来。

上述为**行为层面的步骤/检查证据**;按硬性口径,不能据此判定效率验收通过。

## 4. 局部无歧义微调的最小步骤核对(场景 23 相关)

引用票 02 已授权的局部微调短流程实跑证据
(`tests/test_design_discussion_rounds.py::test_authorized_local_tweak_skips_questions`,
本次实跑 OK):

- 输入已授权、无歧义且无连带影响的文案调整时 `result["path"]=="local_tweak"`,
  `shown_ids==[]`——**不强行访谈、不重开设计地图**(回复不含「全游戏」「设计地图」)。
- 给出前后文案差异(`tweak["diff"]` 含「开始」→「出发」),`applied is True`。
- 未授权的外部动作不执行:`publish_store ∈ unauthorized_actions`,同时已授权
  的文案差异仍完成——授权分离。
- 变更模式侧:`change_flow::test_depth_organizes_work_and_keeps_valid_decisions`
  的 `local_tweak` 分支「局部微调走简短流程」且 `record["verify"]==[]`
  (不强行附加无关验证要求)。

两种模式的正常流程未以漏记录/少检查换取速度的交叉证据:见 3.4 第 5 点
(逐次范围核对数等于轮数)、`incremental_checks::test_precheck_gap_blocks_save_without_disk_checks`
(越界/无授权在保存前即阻断,零写入不进通道)、
`incremental_checks::test_after_save_detects_history_loss_and_duplicates`
(保存后回读仍核对历史丢失与重复)。

## 5. 限制与尚待解决事项

1. **效率尚未验证**(核心限制)。外部故障 `codex-code-mode-host` 在本机
   `codex-cli 0.154.0` 下持续存在(票 01 首采与票 09 复跑两次独立观察),
   优化前基线 `comparable=false`,缺少可比较样本。要完成效率验收,需要
   修复宿主/更换可启动工具宿主的版本,重采优化前与候选两侧配对。
2. **高层真实交互验收未完成**:本系列票 02～08 与本票均以受控通道
   (`GateService` 路径)+ 会话内进程验证;宿主 MCP 连接由
   `tests/test_runtime_gate*.py` 既有主题覆盖。接缝测试覆盖提问结构、回答
   解析、决定落盘与规格同步的函数行为,但未在真实宿主会话中贯穿 Game-Design
   提问、开发者回答、决定落盘与 Game-Spec 同步的完整链路。该条按规格第 226
   行保持未完成,不把接缝测试通过写成真实交互验收无缺口。
3. **dist 版本未升**:`dist/` 为 0.18.1 的当前构建(120 个文件),
   `test_package_dist.py` 通过(dist 与 plugin/ 逐文件一致、可复现构建);
   本票未改 `plugin/`,未重建。版本号保持 0.18.1,未发布。
4. **结构化材料边界**:场景行为链从调用方提供的结构化材料出发,
   不覆盖自由文本语义抽取(沿用票 04～08 已声明的同一例外)。
5. **测试文件体量**:`test_design_discussion_incremental_checks.py`(1355 行)
   等高于仓内软目标 500 行,与票 03～07 同一取舍(会话级夹具共用),
   已在各票 Comments 单列,本票不隐瞒。

## 6. 总判定

- 接缝行为:25/25 场景有结构化接缝测试证据(审查修订后 116 个主题测试函数)。
- 高层真实交互验收:未完成(未实跑真实宿主完整链路)。
- 效率:效率尚未验证(不可比,外部故障持续);步骤/检查行为改善可核实,
  耗时结论未验证。
- 按规格「只有两种模式均满足规格才能报告统一框架验收通过」与效率通过条件
  第 4 条:**本总报告不报告统一框架效率验收通过,也不报告真实宿主交互验收通过**;
  接缝行为部分通过,高层交互与效率部分保持未完成。未扩大修复范围,未宣称产品已发布。

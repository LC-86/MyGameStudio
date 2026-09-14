# PR #38 审查修订情况（供 Codex 再次审查）

日期：2026-09-14。来源评论：https://github.com/LC-86/MyGameStudio/pull/38#issuecomment-5658061576

上一轮固定范围是 `21a46c5...b6f053c`，结论不通过。本文件记录对该评论逐项修订后的情况。复审应对**本分支最新 HEAD**重新取证，不要沿用上一轮探针输出。

## 修订范围

只修评论列出的 Standards 3 项与 Spec 7 项（Spec 1 与 Standards 1 同源，一处实现）。未升 `0.18.1` 版本号（与原 PR 说明一致：合并后、下次发布前再升）。未跑真实宿主端到端会话，也未调用真实模型。

公开接缝未改名：`plan_handoff`/`apply_handoff`/`verify_handoff`、`plan_change`/`apply_change`、`run_round`、`restore_from_records`、`plan_delivery`/`apply_delivery`/`verify_delivery`。

## 逐项处置

| 轴 | 项 | 处置 | 主要位置 | 反例测试 |
| --- | --- | --- | --- | --- |
| S1 / Spec1 | 模块同步覆盖其他模块基线 | 有既有基线时只更新本模块引用、版本与变更索引，保留其余段落 | `spec_sync.design_document` | `test_module_sync_keeps_unrelated_baseline_rules` |
| S2 | 实质变化仍按格式修正保存 | `change=format` 且 `semantic_equal=false` 时 `version.change=conflict`，计划为 `incomplete`，不写入 | `spec_sync.version_plan`，`spec_draft.plan_handoff` | `test_format_claim_blocks_when_semantics_changed` |
| S3 | 保存后检查失败仍宣布交接成功 | `after_write` 扫描规格/记录中的新改引用（不把既有基线旧引用当新改）；失败则 `status=check_failed`、`saved=false`，保留 `written`；变更接缝同样阻断 | `checks.after_write`，`spec_draft.apply_handoff`，`change_flow.apply_change` | `test_after_write_check_failure_does_not_complete_handoff` |
| Spec2 | 缺同步授权仍写核心基线 | 同步授权控制 GAME_DESIGN 是否进入计划与执行；写入授权只覆盖规格/变更记录；未同步时 `handoff_ready` 不为 true | `change_flow._baseline_files`，`_pending_sync` | `test_missing_sync_authorization_does_not_write_baseline` |
| Spec3 | 否定或含糊回答被当成采纳 | 否定「整体按建议」、`选 A 还是 B`、「Q1：不知道」不进入 adopted | `rounds._map_answers`，`check_state.answers_from_reply` | `test_negated_or_ambiguous_replies_stay_pending` |
| Spec4 | 跨记录按文件名覆盖且同步状态串修订 | 按决定身份与 round/date 合并；`synced` 只取当前修订 | `decision_records.merge_records`，`restore_from_records` | `test_restore_merges_by_revision_not_filename` |
| Spec5 | 阶段/对象未核实仍变更完成 | `stage.missing` 进入 `unresolved`，计划为 `incomplete` | `change_flow.plan_change` | `test_unverified_stage_blocks_change_plan` |
| Spec6 | 缺少交付位置被过滤仍通过 | 空路径记为位置缺口；缺一类不得 `planned`/`verify.ok` | `full_design._location_gaps` | `test_missing_delivery_locations_keep_draft` |
| Spec7 | 接缝测试被写成真实交互验收无缺口 | 总报告改为「接缝测试缺口：无；高层真实交互验收：未完成」 | `ACCEPTANCE-REPORT.md` | 口径修订，无新行为函数 |

## 建议复审探针

1. 基线先写入「章节按关卡顺序解锁」和「只做广告变现，禁止付费入口」，再交接每日挑战；两项须仍在 GAME_DESIGN，且 `verify_handoff.ok`。
2. `authorization={write:true,sync:false}` 的变更计划不得含 GAME_DESIGN，`synced` 不得为 true。
3. 回复「不要整体按建议，先讨论」「Q1 选 A 还是 B，我还没决定」「Q1：不知道」均不得 `adopted.Q1`。
4. 两份记录：round1 每天一次已同步（文件名排序靠后）+ round2 每周一次待同步；恢复值须为每周一次，`to_sync=["Q1"]`。
5. 规格声明 `change=format` 但把「一个最佳值」改成「三个」；计划不得 `planned`，基线版本保持。
6. 规格正文含 `docs/missing-source.md` 并传入 `checks.begin` 会话；`apply_handoff` 后 `checks.ok=false`，报告不得称已交接完成。
7. `stage=""` 或 `stage=released, objects={}`：`plan_change` 为 `incomplete`。
8. 去掉 content/version/spec_path：`plan_delivery` 为 `incomplete`，`handoff_ready` 不为 true。

## 验证（修订时已跑）

- `python3 -m compileall plugin tests`：通过
- 八套 `test_design_discussion_*.py`（含新增 8 个反例）：通过
- `test_package_skill_content_design.py`：通过
- 五套聚合入口：`test_plugin_package.py`、`test_records_backend.py`、`test_github_backend.py`、`test_runtime_gate.py`、`test_runtime_boundaries.py`：通过
- `tests/test_*.py` 全仓：全部通过（54 个测试文件）
- `sh dist/build-package.sh` 后 `test_package_dist.py`：通过（0.18.1，120 个文件）
- `git diff --check`（工作区相对当前索引）：通过

## 仍未做（不要当成已修）

- 真实宿主端到端交互验收
- 效率前后配对（外部故障持续）
- 包版本仍为 0.18.1

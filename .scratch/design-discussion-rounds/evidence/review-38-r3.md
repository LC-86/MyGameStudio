# PR #38 审查修订情况（第三轮，供 Codex 再次审查）

日期：2026-09-14。来源评论：https://github.com/LC-86/MyGameStudio/pull/38#issuecomment-5658502485

上一轮固定范围是 `21a46c5...f5f0be9`，结论不通过。本文件记录对该评论逐项修订后的情况。复审应对**本分支最新 HEAD**重新取证，不要沿用 `f5f0be9` 或更早探针输出。

## 修订范围

只修评论列出的 Standards 2 项与 Spec 4 项。未升 `0.18.1` 版本号。未跑真实宿主端到端会话，也未调用真实模型。未合并、未删分支、未推送。

公开接缝未改名：`plan_handoff`/`apply_handoff`/`verify_handoff`、`plan_change`/`apply_change`、`run_round`、`restore_from_records`、`plan_delivery`/`apply_delivery`/`verify_delivery`。

## 逐项处置

| 轴 | 项 | 处置 | 主要位置 | 反例测试 |
| --- | --- | --- | --- | --- |
| S1 | 检查失败仍宣布完成；恢复丢掉未完成同步 | `apply_delivery` 在 `checks.ok` 或 `verify_delivery` 失败时 `check_failed`/`saved=false`；`apply_handoff` 推迟写入「决定记录同步状态」；`apply_change` 推迟变更记录并在失败时强制 `synced=false` | `full_design.apply_delivery`，`spec_draft.apply_handoff`，`change_flow.apply_change` | `test_after_write_check_failure_does_not_complete_handoff`（含 restore）、`test_after_write_check_failure_does_not_complete_delivery` |
| S2 | 英文冒号指纹未更新 | 剥离并兼容更新 `:` / `：` 两种登记，正式 `baseline_report` 保持「一致」 | `spec_sync.register_fingerprints` | `test_english_colon_fingerprints_stay_consistent_after_sync` |
| Spec1 | 缺同步授权仍改当前有效设计 | 变更不写权威模块规格；完整设计不写 GAME_DESIGN/内容/版本，只留 `delivery-pending.md` | `change_flow._spec_plans`，`full_design.plan_delivery` | `test_missing_sync_authorization_does_not_write_baseline`（含规格原位）、`test_delivery_writes_only_with_authorization...` |
| Spec2 | 否定及局部未知仍被采纳 | 识别「不能整体按建议」；逐题「不知道」覆盖本轮整体采纳 | `check_state`，`rounds._map_answers` | `test_negated_or_ambiguous_replies_stay_pending`，`test_rejected_or_unknown_replies_are_not_saved_as_adopted` |
| Spec3 | 后题歧义吞前题 | 按下一题 `Qn` 截断歧义范围 | `check_state.definite_choices` | `test_later_ambiguity_does_not_drop_earlier_answers` |
| Spec4 | 规格文件不存在仍交付 | 权威规格路径有值但回读为无则保持草案；宣布成功前 `verify_delivery` | `full_design._location_gaps` | `test_missing_spec_file_keeps_delivery_incomplete` |

## 建议复审探针

1. 内容引用 `docs/missing-audio-source.md`，经 `checks.begin` 做 `apply_delivery`：`checks.ok=false`，且 `saved/synced/handoff_ready` 不得为 true；`verify_delivery.ok` 不得为 true。
2. 规格交接写入含断链后 `restore_from_records`：`baseline_synced` 不得为 true，`to_sync` 非空，记录仍为「待同步」。
3. 有效 v2 基线使用 `内容指纹:sha256:` / `归一指纹:sha256:`（英文冒号）且已「一致」；`apply_handoff` 后正式 `mgs_records.baseline` 仍为「一致」，不得并存新旧两套指纹。
4. `write=true,sync=false` 的 `plan_change`/`apply_change`：不得把每日规则改成每周；GAME_DESIGN 字节不变；`to_sync` 非空。
5. 同样授权的 `plan_delivery`/`apply_delivery`：不得改写 GAME_DESIGN/内容/版本；须留下 `docs/mygamestudio/records/delivery-pending.md`；`synced`/`handoff_ready` 不为 true。
6. 「不能整体按建议，先讨论」不得保存三题采纳；「整体按建议，Q1：不知道」不得采纳 Q1，Q2/Q3 可采纳。
7. 「Q1 选 A，Q2 选 A 还是 B，我还没决定」：`adopted.Q1=A`，Q2 待讨论。
8. `module_specs[].spec_path` 有值但 `existing[path] is None`：`plan_delivery` 为 `incomplete`，不得 `handoff_ready`。

## 验证（修订时已跑）

- `python3 -m compileall plugin tests`：通过
- 八套 `test_design_discussion_*.py`：通过
- 五套聚合入口 + `test_package_skill_content_design.py` + `test_package_dist.py`：通过（重建 dist 后）
- `tests/test_*.py` 全仓：54/54 通过
- `sh dist/build-package.sh`：0.18.1，120 个文件
- 工作区 `git diff --check`：通过

## 仍未做（不要当成已修）

- 真实宿主端到端交互验收
- 效率前后配对（外部故障持续）
- 包版本仍为 0.18.1
- 历史证据 Markdown 中 4 处行末空格（票 09 宿主输出快照，未改写）

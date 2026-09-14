# PR #38 审查修订情况（第四轮，供 Codex 再次审查）

日期：2026-09-14。来源评论：https://github.com/LC-86/MyGameStudio/pull/38#issuecomment-5658939166

上一轮固定范围是 `21a46c5...4bd8a60`，结论不通过。本文件记录对该评论逐项修订后的情况。复审应对**本分支最新 HEAD**重新取证，不要沿用 `4bd8a60` 或更早探针输出。

## 修订范围

只修评论列出的 Standards 3 项与 Spec 4 项。未升 `0.18.1` 版本号。未跑真实宿主端到端会话，也未调用真实模型。未合并、未删分支、未推送。

公开接缝未改名：`plan_handoff`/`apply_handoff`/`verify_handoff`、`plan_change`/`apply_change`、`run_round`、`restore_from_records`、`plan_delivery`/`apply_delivery`/`verify_delivery`。

## 逐项处置

| 轴 | 项 | 处置 | 主要位置 | 反例测试 |
| --- | --- | --- | --- | --- |
| S1 | 部分写入后重规划跳过未完成的核心基线 | 规格正文相同但基线尚未引用该规格且仍有未同步决定时，保持实质变化并继续规划基线；未写入基线不得把决定标成已同步 | `spec_sync.version_plan`/`sync_files`，`spec_draft.verify_handoff` | `test_partial_spec_write_replans_remaining_baseline_sync` |
| S2 | 完整成稿丢失正式接口能识别的基线版本 | 主文档改回「基线版本」字段，`baseline_report.declared_version` 可读 | `full_render.render_design` | `test_delivery_keeps_official_baseline_version_field` |
| S3 | 交付核验失败时 `checks.ok` 仍为 true | 合并 `after_write` 与 `verify_delivery` 失败到结构化 `checks` | `full_design.apply_delivery` | `test_delivery_verify_failure_sets_checks_ok_false` |
| Spec1 | 组合回答中的保留意见仍被采纳 | 识别「不是整体按建议」；含糊的「选 A 还是 B」覆盖整体采纳 | `check_state`，`rounds._map_answers` | `test_combined_reservations_override_overall_adopt`，`test_combined_reservation_is_not_saved_as_adopted` |
| Spec2 | 只有未决项的记录恢复成没有记录 | 解析到未决项即视作有效模块记录 | `decision_records.parse_record` | `test_pending_only_records_restore_pending_items` |
| Spec3 | 第二个必要模块规格缺失仍宣布完整交付 | 四类交付列出并核对全部模块规格路径 | `full_render.deliverable_outputs` | `test_second_required_module_spec_missing_keeps_delivery_incomplete` |
| Spec4 | 待同步记录无法续写，完成同步后状态不更新 | CLI 读取 `delivery-pending.md`；获准同步后改写完成状态 | `full_design.pending_record_path`，`full_design_cli._paths` | `test_cli_pending_sync_record_continues_and_updates` |

## 建议复审探针

1. 规格写入成功后外部改动 GAME_DESIGN 造成版本冲突，按实际文件重新 `plan_handoff`：不得判为 `format/v2→v2`，计划必须仍含核心基线；完成剩余写入后基线须引用规格，`verify_handoff.ok` 才可为 true。
2. `apply_delivery` 成功后，正式 `mgs_records.baseline_report` 对 GAME_DESIGN 的 `declared_version` 不得为 null，正文须有「基线版本」。
3. 规划后删除必要规格再 `apply_delivery`（带 `checks.begin`）：`status=check_failed` 且 `checks.ok=false`，`failures` 含缺失规格。
4. 「整体按建议，Q2 选 A 还是 B，我还没决定」：Q2 不得采纳；Q1/Q3 可采纳。经 `plan_save`/`apply_save`/`restore_from_records` 后 Q2 仍未决。
5. 「不是整体按建议，先讨论」：三题均不得采纳。
6. 「不能整体按建议，先讨论」保存后 `restore_from_records`：`pending` 含 Q1/Q2/Q3，`records` 非空，报告不得为「未决：无」。
7. `module_specs` 含「每日挑战」与「退出重进」，仅第二份 `spec_path` 文件缺失：`plan_delivery` 为 `incomplete`，不得 `handoff_ready`。两份都在时 `outputs` 须列出两份规格。
8. 真实 CLI：`write=true,sync=false` 两次 `apply` 不得对 `delivery-pending.md` 报 `expected_sha256=absent` 冲突；随后 `sync=true` 成功后该记录不得仍声明「缺同步授权」。

内部 /code-review 后补了三处：冒号后的「选 A 还是 B」也覆盖整体采纳；未决记录按模块标题过滤，避免跨模块串入；没有 `spec_path` 的必要模块同样阻断完整交付。

## 验证（修订时已跑）

- `python3 -m compileall plugin tests`：通过
- 八套 `test_design_discussion_*.py`：通过
- 五套聚合入口：通过
- `tests/test_*.py` 全仓：54/54 通过
- 工作区 `git diff --check`：通过
- dist 已按 `build-package.sh` 重建（0.18.1，120 文件）

## 仍未做（不要当成已修）

- 真实宿主端到端交互验收
- 效率前后配对（外部故障持续）
- 包版本仍为 0.18.1
- 历史证据 Markdown 中 4 处行末空格（票 09 宿主输出快照，未改写）

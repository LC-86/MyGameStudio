# PR #38 审查修订情况（第五轮，供 Codex 再次审查）

日期：2026-09-14。来源评论：https://github.com/LC-86/MyGameStudio/pull/38#issuecomment-5659250743

上一轮固定范围是 `21a46c5...5cf6a98`，结论不通过（Standards 2 项 P2、Spec 4 项 P2）。本文件记录对该评论逐项修订后的情况。复审应对**本分支最新 HEAD** 重新取证，不要沿用 `5cf6a98` 或更早探针输出。

## 修订范围

只修评论列出的 Standards 2 项与 Spec 4 项，外加评论「验证与操作结果」末尾点名的 `git diff --check` 遗留（4 处证据 Markdown 行末空格改为等价的 `\` 硬换行、`spec_report.py` 末尾空行删除）。未升 `0.18.1` 版本号。未跑真实宿主端到端会话，也未调用真实模型。未合并、未删分支。

公开接缝未改名；新增内部判定函数 `spec_sync.baseline_cites_spec`、`check_state.reply_statements`/`question_exceptions`（逐题例外与按原文顺序的语句事件）、`full_design._invalidate_failed_checks`。`check_state.definite_choices`/`ambiguous_choice_ids`/`answers_from_reply` 保持原签名，行为增加「否定选择不算作答」与「按原文顺序取每题最后一条语句」。

## 逐项处置

| 轴 | 项 | 处置 | 主要位置 | 反例测试 |
| --- | --- | --- | --- | --- |
| S1 | 旧规格引用使实质变更恢复误判为格式修正 | 仍有未同步决定时，基线引用须指向**当前版本**（引用条目中「当前 vN」标记）才算已同步；旧 v3 引用不算 v4 修订已同步。版本计划保持实质变化 v3→v4，`sync_files` 的 `baseline_ready` 与 `spec_draft._handoff_states` 同口径 | `spec_sync._baseline_still_needs_spec`/`baseline_cites_spec`/`version_plan`/`sync_files`，`spec_draft._handoff_states` | `test_stale_baseline_citation_recovery_keeps_substantive` |
| S2 | 交付核验失败未作废相关旧检查结果 | `check_failed` 时按失败对象作废：回读缺失或新改引用不可定位的路径按**断链**作废依赖结果；无可定位对象时按**证据不足**作废；无关结果保留，读取结果保留 | `full_design._invalidate_failed_checks`/`apply_delivery` | `test_check_failure_invalidates_dependent_recheck_results` |
| Spec1 | 否定及例外仍被保存为采纳 | 新增逐题例外检测：前置否定（「不要 Q2 选 A」）、排除（「除了 Q2」）、明确暂不决定（「Q2 先不决定/待定/不选」）；`CHOICE_RE` 匹配带前置否定时不算明确选项；例外覆盖整体采纳，该题记 `deferred` 未决 | `check_state.QUESTION_EXCEPTION_RE`/`PREFIX_EXCEPTION_RE`/`question_exceptions`/`reply_statements`，`rounds._map_answers` | `test_question_exceptions_override_overall_adoption`，`test_negated_and_deferred_exceptions_not_saved_as_adopted`（真实通道保存+恢复） |
| Spec2 | 固定解析顺序覆盖用户最终回答 | 逐题作答整理为带位置的语句事件（choice/adjust/adjust_index/ambiguous/exception），按原文出现顺序应用，同一题以**最后一条**为准；整体采纳只覆盖没有逐题语句的展示题目 | `check_state.reply_statements`/`answers_from_reply`，`rounds._map_answers` | `test_later_statement_wins_for_same_question` |
| Spec3 | 其他模块的同编号问题覆盖当前模块 | 本轮题目目录按当前模块作用域解析（`_catalog` 过滤其他模块），展示、采纳、保存与恢复经同一目录取得一致的模块与问题身份；题号仍按展示原样显示 | `rounds._catalog` | `test_same_qid_in_other_module_keeps_current_identity`，`test_same_qid_in_other_module_saves_current_module_decision`（真实通道保存+恢复） |
| Spec4 | 交付检查失败，持久记录却宣布同步完成 | 完成标记移出写入计划（`pending_complete_file`），`apply_delivery` 在**全部必要检查成功后**才提交；失败时待同步记录保持原有可恢复事实，不出现「已经完成/已同步」 | `full_design.plan_delivery`/`apply_delivery` | `test_cli_pending_completion_waits_for_checks`（真实 CLI 三连：待同步保存 → 授权同步但引用缺失 → 修复后重试） |

## 反向验证

- 新增反例测试在修复前代码（`5cf6a98` 的临时 worktree）上全部以评论描述的症状失败：Q2 被保存为 `A/user`、`除了 Q2` 落回推荐 B、`Q1 改为 A；Q1 选 B` 保存 A、恢复规划判 `format v3→v3` 且计划不含核心基线、依赖被移除规格的旧结果仍 `ok=true`、检查失败前 `delivery-pending.md` 已写成「完整设计同步记录…已同步」。
- 单元对照：同一冲突恢复输入下，旧 `version_plan` 判 `format v3→v3`，新判 `substantive v3→v4`。

## 验证与操作结果

- `tests/test_*.py` 全部 54 个文件通过（含本轮新增 6 个反例测试所在的 4 个文件）。
- `dist/build-package.sh` 重建后包一致性检查通过；全 PR 范围 `git diff --check` 无遗留。
- 高层真实宿主交互和效率配对仍未验证；本轮未调用真实模型，不把这些限制标为通过。
- 仓库工作区在提交前保持只含本次修订改动；未合并、未删除分支。

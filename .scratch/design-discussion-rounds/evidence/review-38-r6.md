# PR #38 审查修订情况（第六轮修复，供 Codex 再次审查）

日期：2026-09-14。来源评论：https://github.com/LC-86/MyGameStudio/pull/38#issuecomment-5659551521

上一轮固定范围是 `21a46c5...a9996a0`，第六轮审查结论不通过（Standards 2 项 P2、Spec 2 项 P2、包一致性 1 项）。本文件记录逐项修订后的情况。复审应对**本分支最新 HEAD** 重新取证，不要沿用 `a9996a0` 或更早探针输出。

## 修订范围

只修评论列出的 Standards 2 项、Spec 2 项与包一致性问题。未升 `0.18.1` 版本号。未跑真实宿主端到端会话，也未调用真实模型。未合并、未删分支。

## 逐项处置

| 轴 | 项 | 处置 | 主要位置 | 反例测试 |
| --- | --- | --- | --- | --- |
| S1 | 自定义基线标题仍会丢失待同步事实 | `_upsert_citation` 不再把「路径已出现」当「引用已就位」:标准标题节原位替换之外,规格路径所在的二级标题节(自定义标题)整节替换为当前引用,引用位置保持唯一;`sync_files` 的 `baseline_ready` 改为核对**实际写入的基线内容**确实引用当前版本,引用未就位时不把决定记录标成已同步 | `spec_sync._upsert_citation`/`sync_files` | `test_custom_titled_citation_updates_on_recovery`(标准标题改为「每日挑战设计依据」后走 v3→v4 改口、规格先写成功、基线冲突、重规划:引用须更新到当前 v4,`states.synced` 与记录 `to_sync` 一致收口,恢复不再降为格式修正) |
| S2 | 已删除的引用文件被 `untouched` 当成存在 | 可定位性一律按实际回读核对:`verify_delivery` 的 `untouched` 路径与 `checks._written_reference_failures` 的 `known_paths` 都以回读内容非空为准;外部删除的引用目标是断链,交付 `check_failed` 并按失败对象作废旧结果 | `full_design.verify_delivery`，`checks._written_reference_failures` | `test_deleted_untouched_reference_breaks_delivery`(内容需求引用存在的 `audio-basis.md` 且声明未改动,规划后删除:交付不得 `saved/synced=true`,失败定位该文件,依赖它的检查结果作废、无关结果保留) |
| Spec1 | 被否定的「改为」语句仍被当作新决定保存 | `ADJUST_RE` 匹配带前置否定时不再生成调整语句:否定约束整个调整语句,不能被位置更晚的调整事件覆盖;例外由前置否定检测提供,该题保持 `deferred` 未决 | `check_state.reply_statements`(ADJUST 循环加 `_choice_is_negated`) | `test_negated_or_ambiguous_replies_stay_pending` 增例；`test_negated_adjust_reply_not_saved_as_decision`(真实 GateService 保存+恢复:「整体按建议，不要 Q2 改为 B」不得落盘为 Q2 决定) |
| Spec2 | 按序号修改题目的明确答案被保存前检查拒绝 | 两层修正:(1) `answers_from_reply` 把 `adjust_index` 与逐题 `adjust` 同一解释,不再落入删除答案分支;(2) `run_round` 新增输出 `answered_ids`(本次回复实际对应到的展示题目),`decisions._before_checks` 优先用它解析答案——此前误用回复后新展示的 `shown_ids`,导致整体采纳与序号修改在保存前检查中无题可对 | `check_state.answers_from_reply`，`rounds.run_round`，`decisions._before_checks` | `test_item_adjust_passes_session_precheck_and_saves`(带 `checks.begin` 会话:「整体按建议，第 2 项调整为保留完整章节」与等价的「Q2 调整为…」都经 `plan_save`/`apply_save`/`restore_from_records` 一致收口) |
| 包 | dist 与源码不一致（`rounds.py` 指针差一行未使用赋值） | 上一轮在重建 dist 后又做了代码清理导致;本轮在代码定稿后重新执行 `./dist/build-package.sh`,`package-manifest.txt` 与源码逐文件一致(120 个文件),`test_plugin_package.py`/`test_package_dist.py` 通过 | `dist/*` | 全量套件 54/54 |

## 反向验证

- 新增反例测试在修复前代码（`a9996a0` 临时 worktree）上全部以评论描述的症状失败:「不要 Q2 改为 B」落盘 `Q2=B custom`;带会话的「第 2 项调整为…」`plan_save` 返回 `invalid`(Q1/Q2/Q3 不在实际答案内);自定义标题恢复后引用仍指 `当前 v3` 且 `states.synced=false` 与记录 `to_sync=['Q1']` 并存;删除 `audio-basis.md` 后交付返回 `saved` 并宣称已同步。
- 修复后同一批测试全部通过。

## 验证与交付物

- README 五套聚合入口与八套 `test_design_discussion_*.py` 全部通过;`tests/test_*.py` 54/54。
- `./dist/build-package.sh` 重建后包一致性检查通过;全 PR 范围 `git diff --check` 通过。
- 高层真实宿主交互与效率配对仍未验证,未调用真实模型,不把这些限制标为通过。

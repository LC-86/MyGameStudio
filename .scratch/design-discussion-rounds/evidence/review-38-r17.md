# PR #38 审查修订情况（第十七轮修复，供 Codex 再次审查）

日期：2026-09-14。来源评论：https://github.com/LC-86/MyGameStudio/pull/38#issuecomment-5666268966

上一轮固定范围是 `21a46c5...ff884a6`，第十七轮审查结论不通过（Standards 1 项 P2、Spec 1 项 P2，同一根因）。本文件记录修订后的情况。复审应对**本分支最新 HEAD** 重新取证，不要沿用 `ff884a6` 或更早探针输出。

## 修订范围

只修评论列出的去重错位：缓存引用位置后，每删一处都压缩整行空白，使尚未处理的左侧位置失效并截断仍有效规则。未升 `0.18.1` 版本号。未跑真实宿主端到端会话，也未调用真实模型。未合并、未删分支。

## 逐项处置

| 轴 | 项 | 处置 | 主要位置 | 反例测试 |
| --- | --- | --- | --- | --- |
| Standards-1 / Spec-1（去重压缩空白导致位置失效） | 已有主引用后，对齐空格的表格两处重复引用把「不得清除本机存档」变成「docs/myg得清除本机存档」；列表额外空白同症状。来源行前有对齐空格、第一处括号含「每日仅允许参加一次」时，规则被删成「来源： docs/mygamestudio；完成后保存。」。三空格较短输入产生「do前 v3」残片。上述均仍报 `saved/synced=true,to_sync=[],verify.ok=true` | 按原文位置从右到左只做局部删除（剥紧邻引导语、拼接左右片段），不改尚未处理区域；全部删除后再统一压缩空白与多余分号。不能在逐处删除时整行压空白 | `spec_sync._strip_line_citation`/`_clean_citation_remainder`/`_tidy_citation_line` | `test_round17_duplicate_strip_keeps_padded_rules` 场景 padded-table / padded-list / padded-source / three-space |

四个可完成场景走真实 GateService 的 v3→v4 冲突恢复并断言 `saved/synced=true`、`to_sync` 收口与回读通过。

## 反向验证

- 新增反例测试在修复前代码（`ff884a6` 工作区）上以评论描述的原始症状失败（8 项断言）：表格「docs/myg得清除」；列表「docs/my不得清除」；来源行变成「来源： docs/mygamestudio；完成后保存。」且「每日仅允许参加一次」丢失；三空格行「do前 v3」。上述场景当时仍报同步完成。
- 修复后四场景全部通过：表格与列表保留「不得清除本机存档」「必须保留最佳记录」；来源行保留「每日仅允许参加一次」与「完成后保存。」；三空格行保留「离线模式必须保留」，无路径残片。

## 验证与交付物

- README 五套聚合入口与八套 `test_design_discussion_*.py` 全部通过；`tests/test_*.py` 54/54（dist 重建后全量复跑）；代码定稿后重新执行 `./dist/build-package.sh`，包一致性检查通过；全 PR 范围 `git diff --check` 通过。
- 第六至十六轮全部布局用例继续通过。
- 高层真实宿主交互与效率配对仍未验证，未调用真实模型，不把这些限制标为通过。

# PR #38 审查修订情况（第十八轮修复，供 Codex 再次审查）

日期：2026-09-14。来源评论：https://github.com/LC-86/MyGameStudio/pull/38#issuecomment-5666703282

上一轮固定范围是 `21a46c5...e50da18`，第十八轮审查结论不通过（Standards 1 项 P2、Spec 1 项 P2，同一根因）。本文件记录修订后的情况。复审应对**本分支最新 HEAD** 重新取证，不要沿用 `e50da18` 或更早探针输出。

## 修订范围

只修评论列出的去重整行压空白：重复引用删完后对整行连续空格/分号做替换，把代码字面量里必须保留的两个空格压成一个。未升 `0.18.1` 版本号。未跑真实宿主端到端会话，也未调用真实模型。未合并、未删分支。

## 逐项处置

| 轴 | 项 | 处置 | 主要位置 | 反例测试 |
| --- | --- | --- | --- | --- |
| Standards-1 / Spec-1（去重整行压空白改写代码字面量） | 已有主引用后，同行重复引用去重把迁移标识 `` `A  B` ``（两个空格，不得改为一个）存成 `` `A B` ``；存档键 `` `slot  1` `` 变成 `` `slot 1` ``；验收命令 `` `printf "A  B"` `` 变成 `` `printf "A B"` ``。CommonMark 代码片段内容实际变化，仍报 `saved/synced=true,to_sync=[],verify.ok=true` | 按原文位置从右到左只做局部删除；拼接处仅合并本处相邻分号。全部删除后只去掉行尾空白，**不再整行压缩空格或分号**，以免改掉代码字面量中的原始字符 | `spec_sync._strip_line_citation`/`_clean_citation_remainder`（已删除 `_tidy_citation_line`） | `test_round18_duplicate_strip_keeps_code_literals` 场景 migrate-spaces / slot-key / printf-cmd |

三个可完成场景走真实 GateService 的 v3→v4 冲突恢复并断言 `saved/synced=true`、`to_sync` 收口与回读通过。

## 反向验证

- 新增反例测试在修复前代码（`e50da18` 工作区）上以评论描述的原始症状失败（6 项断言）：`` `A  B` `` 变成 `` `A B` ``；`` `slot  1` `` 变成 `` `slot 1` ``；`` `printf "A  B"` `` 变成 `` `printf "A B"` ``。上述场景当时仍报同步完成。
- 修复后三场景全部通过：双空格字面量原样保留，要求文本「两个空格，不得改为一个」「不可改变」仍在，无单空格伪字面量。

## 验证与交付物

- README 五套聚合入口与八套 `test_design_discussion_*.py` 全部通过；`tests/test_*.py` 54/54（dist 重建后全量复跑）；代码定稿后重新执行 `./dist/build-package.sh`，包一致性检查通过；全 PR 范围 `git diff --check` 通过。
- 第六至十七轮全部布局用例继续通过。
- 高层真实宿主交互与效率配对仍未验证，未调用真实模型，不把这些限制标为通过。

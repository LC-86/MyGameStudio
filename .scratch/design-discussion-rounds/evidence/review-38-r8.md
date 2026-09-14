# PR #38 审查修订情况（第八轮修复，供 Codex 再次审查）

日期：2026-09-14。来源评论：https://github.com/LC-86/MyGameStudio/pull/38#issuecomment-5659830907

上一轮固定范围是 `21a46c5...ad15e08`，第八轮审查结论不通过（Standards 1 项 P2、Spec 1 项 P2，同一底层问题）。本文件记录修订后的情况。复审应对**本分支最新 HEAD** 重新取证，不要沿用 `ad15e08` 或更早探针输出。

## 修订范围

只修评论列出的「引用与其他有效要求同处一行时，更新仍会删除要求」这一底层问题（两轴各计 1 项 P2）。未升 `0.18.1` 版本号。未跑真实宿主端到端会话，也未调用真实模型。未合并、未删分支。

## 逐项处置

| 轴 | 项 | 处置 | 主要位置 | 反例测试 |
| --- | --- | --- | --- | --- |
| Standards-1 / Spec-1（同一问题） | 含规格路径的整行被换成生成引用,同行列表、表格列与重复引用说明中的仍有效规则丢失 | `_replace_reference_lines` 改为**行内更新**:首次出现只改路径旁的「当前 vN」;后续重复只去掉路径与版本片段,有业务正文则保留该行;无版本时也不得整行替换 | `spec_sync._update_line_citation`/`_strip_line_citation`/`_replace_reference_lines` | `test_same_line_citation_layouts_keep_rules`（三种独立布局:同行列表、Markdown 表格不同列、第二条重复引用说明;均走 v3→v4 冲突恢复:引用到当前 v4,「主线第 10 关通过后解锁章节选择」仍在,同步状态一致收口,回读通过） |

上轮已有的 `test_custom_section_mixed_content_preserved`（规则单独占一行）继续通过。

## 反向验证

- 新增反例测试在修复前代码（`ad15e08`）上以评论描述的症状失败:三种布局中章节解锁规则均消失,而返回 `saved=true`。
- 修复后同一测试通过:列表与表格只把 `当前 v2` 改成 `当前 v4` 并保留同行规则;重复引用行保留「第二条引用说明」与规则正文。

## 验证与交付物

- README 五套聚合入口与八套 `test_design_discussion_*.py` 全部通过（143 个测试函数）;`tests/test_*.py` 54/54;代码定稿后重新执行 `./dist/build-package.sh`,包一致性检查通过;全 PR 范围 `git diff --check` 通过。
- 高层真实宿主交互与效率配对仍未验证,未调用真实模型,不把这些限制标为通过。

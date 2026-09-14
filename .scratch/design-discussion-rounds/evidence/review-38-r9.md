# PR #38 审查修订情况（第九轮修复，供 Codex 再次审查）

日期：2026-09-14。来源评论：https://github.com/LC-86/MyGameStudio/pull/38#issuecomment-5660090700

上一轮固定范围是 `21a46c5...1075d34`（第八轮修复的本地提交，未推送），第九轮审查结论不通过（Standards 1 项 P2、Spec 2 项 P2，同一引用边界问题族）。本文件记录修订后的情况。复审应对**本分支最新 HEAD** 重新取证，不要沿用 `1075d34` 或更早探针输出。

## 修订范围

只修评论列出的引用片段范围识别问题（三项反例同源）：版本更新与重复引用去重的触碰范围必须精确限定在目标引用自身。未升 `0.18.1` 版本号。未跑真实宿主端到端会话，也未调用真实模型。未合并、未删分支。

## 逐项处置

| 轴 | 项 | 处置 | 主要位置 | 反例测试 |
| --- | --- | --- | --- | --- |
| Standards-1 / Spec-1 / Spec-2（同源） | 引用片段范围识别不准确:80 字符窗口跨表格列与分隔符改掉其他模块版本;无版本时把版本插进链接目标;去重吞掉含规则的整个括号 | 版本只认**直接附着**于路径的片段（新增 `_attached_version`）:紧随的括号内的版本、或经至多一个分隔符紧邻的裸版本;路径是 Markdown 链接目标时版本附着在链接闭括号之后（更新插入与检出同口径）。`_update_line_citation` 无附着括号时紧接路径（或链接闭括号后）插入,不再向后扫描 80 字符;`_strip_line_citation` 去重只移除路径与附着版本片段（`_drop_version_fragment` 连同紧邻分隔符）,括号内附带规则保留,链接形式的重复引用保留链接文字;`baseline_cites_spec` 改为逐行按附着版本核对,不再跨列/跨分隔符匹配 | `spec_sync._attached_version`/`_update_line_citation`/`_strip_line_citation`/`_drop_version_fragment`/`baseline_cites_spec` | `test_reference_boundary_keeps_links_other_modules_and_rules`(四场景均走真实 GateService 的 v3→v4 冲突恢复:链接、裸路径+其他模块 v7、表格邻列 v8、括号内规则去重) |

第八轮的三个布局用例（`test_same_line_citation_layouts_keep_rules`）继续通过;第七轮的混合内容节与第六轮的自定义标题恢复用例继续通过——附着式更新对已覆盖布局的行为不变。

## 反向验证

- 新增反例测试在修复前代码（`1075d34` 临时 worktree）上以评论描述的症状全部失败:版本进入链接目标 `](PATH（当前 v4）)`;`章节系统（当前 v7）` 与表格邻列 `spec-章节.md（当前 v8）` 被改成 v4;去重后仅剩 `关联依据：。`、章节规则消失。
- 修复后四场景全部通过:版本位于链接目标之外、其他模块版本原样、括号内规则保留为 `关联依据：（章节十解锁跳关功能）。`。

## 验证与交付物

- README 五套聚合入口与八套 `test_design_discussion_*.py` 全部通过;`tests/test_*.py` 54/54;代码定稿后重新执行 `./dist/build-package.sh`,包一致性检查通过;全 PR 范围 `git diff --check` 通过。
- 高层真实宿主交互与效率配对仍未验证,未调用真实模型,不把这些限制标为通过。

# PR #38 审查修订情况（第十轮修复，供 Codex 再次审查）

日期：2026-09-14。来源评论：https://github.com/LC-86/MyGameStudio/pull/38#issuecomment-5660310112

上一轮固定范围是 `21a46c5...c15f946`，第十轮审查结论不通过（Standards 1 项 P2、Spec 3 项 P2，同一"引用身份与版本范围界定"问题族，全部落在 `spec_sync.py` 的引用定位与括号解析）。本文件记录修订后的情况。复审应对**本分支最新 HEAD** 重新取证，不要沿用 `c15f946` 或更早探针输出。

## 修订范围

只修评论列出的引用身份与版本范围界定问题（四项反例同源）：引用定位按完整路径身份、附着括号按深度配对解析、本引用版本只认括号顶层。未升 `0.18.1` 版本号。未跑真实宿主端到端会话，也未调用真实模型。未合并、未删分支。

## 逐项处置

| 轴 | 项 | 处置 | 主要位置 | 反例测试 |
| --- | --- | --- | --- | --- |
| Standards-1 / Spec-1 | Markdown 链接边界不完整:`](<PATH>)` 尖括号形式不被识别,版本插入链接目标;链接后已有版本括号时追加成两个当前版本 | 链接身份判定改为 `]\((?:<)?$`（新增 `_link_close`,同时覆盖 `](PATH)` 与 `](<PATH>)`）;版本锚点是链接闭括号之后:已有附着括号时**原位更新其中顶层版本**（`当前 v3；仍需离线可用` → `当前 v4；仍需离线可用`）,无附着时才在闭括号后插入,版本始终在链接目标之外 | `spec_sync._link_close`/`_update_line_citation`/`_attached_version` | `test_citation_identity_keeps_link_targets_longer_names_and_nested_versions` 场景 angled-link、link-with-version |
| Spec-2 | 路径子串匹配把 `PATH.backup` 当作目标改写,并把真目标引用整条删成 `目标引用：。` | 引用定位统一改用完整路径身份（新增 `_find_path`）:出现位置两侧不得再是路径字符（字母数字、`_.-/`、CJK）,`PATH.backup` 属于更长文件名不命中,该行原样保留;真目标行按唯一命中原位更新,`baseline_cites_spec`/`_upsert_citation`/`_replace_reference_lines` 同口径换用 `_has_path` | `spec_sync._find_path`/`_has_path`/`_replace_reference_lines`/`_upsert_citation`/`baseline_cites_spec` | 同测试场景 longer-filename（`.backup（当前 v9）` 行与 `PATH（当前 v3）` 行并存） |
| Spec-3 | 嵌套括号中其他模块的版本被当作本引用版本:首条更新把 `章节模块（当前 v8）` 改成 v4;去重把 `章节模式（当前 v8）` 删成 `章节模式（）` | 附着括号改为深度配对解析（新增 `_match_bracket`,嵌套括号属于内容、未闭合不算附着）;本引用版本只认括号**顶层**（新增 `_top_level_version`）:更新时顶层无版本则前置 `当前 vN；` 并原样保留嵌套内容（`（当前 v4；参照章节模块（当前 v8）的解锁规则）`）;去重只删顶层版本片段（`_drop_version_fragment` 改为 `_drop_top_version`）,顶层无版本时嵌套内容整体保留 | `spec_sync._match_bracket`/`_top_level_spans`/`_top_level_version`/`_update_line_citation`/`_drop_top_version`/`_strip_line_citation` | 同测试场景 nested-update、nested-strip |

五场景均走真实 GateService 的 `plan_handoff → apply_handoff → verify_handoff`、v3→v4 冲突与重新读取恢复（复用 `_recover_stale_custom_citation` 装置），并断言 `saved/synced=true`、`to_sync` 收口与回读通过。

第六至九轮的布局用例（自定义标题恢复、混合内容节、同行列表/表格/重复引用、链接/其他模块/表格邻列/括号规则去重）继续通过——完整身份定位与深度配对对已覆盖布局行为不变。唯一有意差异:链接形式重复引用去重时,链接闭括号后的附着版本片段一并去除、业务条件保留（此前整段拼回）。

## 反向验证

- 新增反例测试在修复前代码（`c15f946` 临时 worktree）上以评论描述的原始症状全部失败（12 项断言）:`[挑战说明](<PATH（当前 v4）>)` 版本进入链接目标;`（当前 v4）（当前 v3；…）` 两个当前版本;`PATH（当前 v4）.backup（当前 v9）` 更长文件名被改写且真目标引用仅剩 `目标引用：。`;首条更新产生 `章节模块（当前 v4）`;去重产生 `章节模式（）`。
- 修复后五场景全部通过:版本位于链接目标之外并原位更新;`.backup` 行原样保留、真目标引用更新到 v4;嵌套的 `当前 v8` 在更新与去重两侧都保留。

## 验证与交付物

- README 五套聚合入口与八套 `test_design_discussion_*.py` 全部通过;`tests/test_*.py` 54/54;代码定稿后重新执行 `./dist/build-package.sh`,包一致性检查通过;全 PR 范围 `git diff --check` 通过。
- 高层真实宿主交互与效率配对仍未验证,未调用真实模型,不把这些限制标为通过。

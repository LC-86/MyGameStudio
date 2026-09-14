# PR #38 审查修订情况（第十一轮修复，供 Codex 再次审查）

日期：2026-09-14。来源评论：https://github.com/LC-86/MyGameStudio/pull/38#issuecomment-5660647495

上一轮固定范围是 `21a46c5...d0974c7`，第十一轮审查结论不通过（Standards 1 项 P2、Spec 3 项 P2，仍集中在 `spec_sync.py` 的引用定位与版本归属）。本文件记录修订后的情况。复审应对**本分支最新 HEAD** 重新取证，不要沿用 `d0974c7` 或更早探针输出。

## 修订范围

只修评论列出的四项（链接目标解析不完整、路径身份误认/误拒、链接显示文字混淆、括号顶层中部版本归属）。未升 `0.18.1` 版本号。未跑真实宿主端到端会话，也未调用真实模型。未合并、未删分支。

## 逐项处置

| 轴 | 项 | 处置 | 主要位置 | 反例测试 |
| --- | --- | --- | --- | --- |
| Standards-1 | 链接定位破坏合法 Markdown 引用:`]( PATH )` 版本插进目标、`]( <PATH> )` 目标被追加、引号标题含 `)` 时 v4 插进标题 | 链接前缀判定改为 `]\([ \t]*(?:<)?[ \t]*$`（覆盖带空白目标与尖括号）;`_link_close` 改为**完整解析链接**:尖括号目标到 `>`、裸目标到空白或平衡闭括号，其后允许可选空白与 `"标题"`（标题内的括号不结束链接），最后才是链接闭括号;链接形态但闭括号解析不出时**保持该行不动**，由回读判定未完成（`baseline_cites_spec` 同口径解析，不会宣称同步完成） | `spec_sync._LINK_BEFORE_RE`/`_link_close`/`_update_line_citation`/`_strip_line_citation` | `test_link_target_parsing_and_version_ownership_keep_valid_citations` 场景 spaced-link、spaced-angled、titled-link |
| Spec-1 | 路径身份误认备份文件、误拒合法目标:`PATH~（当前 v9）` 被改写且真目标被剥成标点;`./PATH`、`详见PATH` 被排除后仍宣称同步完成 | 身份判定两方向独立:前一侧只拒绝 ASCII 路径字符（**不含 `/`**，`./<PATH>` 是同一文件;中文动词紧邻如 `详见<PATH>` 允许）;后一侧改为引用语法字符**白名单**（空白、括号、链接与表格符号、常见中英标点），`~`、`.`、字母数字等其余字符一律视为更长文件名——`PATH~` 行不再命中、原样保留，真目标行按唯一命中原位更新 | `spec_sync._PATH_HEAD_RE`/`_PATH_TAIL_OK_RE`/`_find_path` | 同测试场景 tilde-backup、dot-slash、cjk-adjacent |
| Spec-2 | Markdown 引用定位混淆显示文字与版本位置:`[PATH](PATH)（当前 v3）` 版本进显示文字;带标题链接把 v4 插进标题 | `_find_path` 跳过处于链接显示文字位置的路径出现（前邻 `[` 且后邻 `](`）,定位到**链接目标里**的路径;配合 Standards-1 的完整链接解析，版本锚点始终是真正的链接闭括号之后，原位更新链接外附着括号的顶层版本 | `spec_sync._find_path`/`_update_line_citation` | 同测试场景 self-link、titled-link |
| Spec-3 | 括号顶层的其他模块版本被误当本引用版本:`（参照章节模块当前 v8 的规则）` 更新变 `章节模块当前 v4`、去重变 `章节模块；的规则` | `_top_level_version` 改为只认附着括号内容**顶层开头**的 `当前 vN`（`_LEADING_VERSION_RE`，允许前导空白）;版本前有其他文字时属于业务说明提到的其他对象——更新时前置 `当前 vN；` 并原样保留全部说明,去重时整体保留不改不删 | `spec_sync._LEADING_VERSION_RE`/`_top_level_version`/`_update_bracket_inner` 内联分支/`_drop_top_version` | 同测试场景 mid-text-update（`（当前 v4；参照章节模块当前 v8 的规则）`）、mid-text-strip（`（参照章节模块当前 v8 的规则）` 原样保留） |

九场景均走真实 GateService 的 `plan_handoff → apply_handoff → verify_handoff`、v3→v4 冲突与重新读取恢复（复用 `_recover_stale_custom_citation` 装置），并断言 `saved/synced=true`、`to_sync` 收口与回读通过。

第六至十轮全部布局用例继续通过（自定义标题恢复、混合内容节、同行列表/表格/重复引用、链接/其他模块/表格邻列/括号规则去重、尖括号链接/`.backup`/嵌套括号）——新解析对已覆盖布局行为不变。

## 反向验证

- 新增反例测试在修复前代码（`d0974c7` 临时 worktree）上以评论描述的原始症状失败（17 项断言）:`]( PATH（当前 v4） )` 与 `]( <PATH（当前 v4）> )` 版本进入链接目标;`PATH（当前 v4）~（当前 v9）` 备份文件被改写、真目标引用被剥成 `目标引用：。`;`./PATH`、`详见PATH` 的 v3 原样残留（期望的 v4 缺失）;`[PATH（当前 v4）](PATH)（当前 v3）` 版本进入显示文字;`章节模块当前 v4`、`章节模块；的规则` 其他模块版本被改/被删。
- 修复后九场景全部通过:版本位于链接目标与标题之外并原位更新;`~` 行原样;`./PATH`、`详见PATH` 更新到 v4;self-link 更新目标外版本;说明文字中的 `当前 v8` 在更新与去重两侧都保留。

## 验证与交付物

- README 五套聚合入口与八套 `test_design_discussion_*.py` 全部通过;`tests/test_*.py` 54/54（dist 重建后全量复跑）;代码定稿后重新执行 `./dist/build-package.sh`，包一致性与可重复构建检查通过;全 PR 范围 `git diff --check` 通过。
- 高层真实宿主交互与效率配对仍未验证,未调用真实模型,不把这些限制标为通过。

# PR #38 审查修订情况（第十二轮修复，供 Codex 再次审查）

日期：2026-09-14。来源评论：https://github.com/LC-86/MyGameStudio/pull/38#issuecomment-5661136677

上一轮固定范围是 `21a46c5...9690063`，第十二轮审查结论不通过（Standards 1 项 P2、Spec 2 项 P2，集中在 `spec_sync.py` 的路径身份判定与 Markdown 边界）。本文件记录修订后的情况。复审应对**本分支最新 HEAD** 重新取证，不要沿用 `9690063` 或更早探针输出。

## 修订范围

只修评论列出的三项（归档目录/括号文件名被当作目标、`./` 链接与显示文字/代码片段边界）。未升 `0.18.1` 版本号。未跑真实宿主端到端会话，也未调用真实模型。未合并、未删分支。

## 逐项处置

| 轴 | 项 | 处置 | 主要位置 | 反例测试 |
| --- | --- | --- | --- | --- |
| Standards-1 / Spec-1 | 路径身份误认不同文件:`archive/PATH（当前 v8；旧版题库）` 被改成 v4、真目标被剥成 `当前规格：。`;`PATH(backup)` 被改成 `PATH(当前 v4；backup)` | 身份判定从相邻字符白黑名单改为**完整 token 扩展+归一化比较**（`_find_path` 重写）:从出现位置向两侧扩展路径字符段（含 `/`），紧邻且内容全为 ASCII 路径字符的半角括号段（`(backup)`）属于文件名;token 去掉 `./` 前缀与句末点号后必须与规格路径**相等**——`archive/<PATH>`、`<PATH>(backup)`、`<PATH>.backup`、`<PATH>~`、`<PATH>2` 都不相等,对应行原样保留;真目标行按唯一命中原位更新 | `spec_sync._PATH_TOKEN_RE`/`_ascii_paren_span`/`_find_path` | `test_path_identity_and_markdown_boundaries_keep_other_files_and_targets` 场景 archive、paren-file |
| Spec-2（链接前缀） | `[每日挑战](./PATH)（当前 v3）` 变成 `](./PATH（当前 v4）)`,链接目标损坏 | 链接前缀判定改为 `]\([ \t]*(?:[^\s()]*[ \t]*)?$`——目标内允许相对路径前缀（`./`、子目录等）;`_link_close` 已有的完整目标解析（空白/尖括号/引号标题）沿用,版本锚点仍是真正的链接闭括号之后 | `spec_sync._LINK_BEFORE_RE` | 同测试场景 dot-slash-link、anchor-link |
| Spec-2（显示文字/代码片段） | `[查看 PATH](PATH)` 把 v4 插入显示文字;反引号包裹的路径把 v4 插入代码片段;补充观察 `](PATH#正常流程)` 不更新仍报同步通过 | 显示文字跳过泛化:路径出现紧邻 `](` 即视为链接显示文字,跳过找目标里的路径（不再要求前邻恰为 `[`）;行内代码片段 `` `<PATH>` `` 前后成对反引号时,版本锚点穿透到**闭反引号之后**（更新、检出、去重同口径,去重时连反引号对一并去掉）;`#` 锚点天然支持——`#` 不属于路径字符,token 即 `PATH`,锚点链接 `](PATH#正常流程)` 更新链接外版本 | `spec_sync._find_path`（显示文字跳过）/`_attached_version`/`_update_line_citation`/`_strip_line_citation`（代码片段锚点） | 同测试场景 label-path、code-span、anchor-link |

六场景均走真实 GateService 的 `plan_handoff → apply_handoff → verify_handoff`、v3→v4 冲突与重新读取恢复（复用 `_recover_stale_custom_citation` 装置），并断言 `saved/synced=true`、`to_sync` 收口与回读通过。

第六至十一轮全部布局用例继续通过（自定义标题恢复、混合内容节、同行列表/表格/重复引用、链接/其他模块/表格邻列/括号规则去重、尖括号链接/`.backup`/嵌套括号、空白目标/标题/`~` 备份/`./` 裸引用/self-link/顶层中部版本）——token 身份判定与各 Markdown 边界对已覆盖布局行为不变。

## 反向验证

- 新增反例测试在修复前代码（`9690063` 临时 worktree）上以评论描述的原始症状失败（15 项断言,六场景全败）:`archive/PATH（当前 v4；旧版题库）` 归档引用被改写、`当前规格：。` 真目标被剥成标点;`PATH(当前 v4` 括号文件名被改写;`](./PATH（当前 v4）)` 版本进入 `./` 链接目标;`PATH（当前 v4）](PATH)` 版本进入显示文字;`` `PATH（当前 v4）` `` 版本进入代码片段;`#正常流程` 锚点链接的 v3 残留。
- 修复后六场景全部通过:归档与括号文件名行原样、真目标更新到 v4;`./` 链接、显示文字含路径的链接、锚点链接的版本都落在链接目标之外;代码片段版本落在闭反引号之后。

## 验证与交付物

- README 五套聚合入口与八套 `test_design_discussion_*.py` 全部通过;`tests/test_*.py` 54/54（dist 重建后全量复跑）;代码定稿后重新执行 `./dist/build-package.sh`，包一致性与可重复构建检查通过;全 PR 范围 `git diff --check` 通过。
- 高层真实宿主交互与效率配对仍未验证,未调用真实模型,不把这些限制标为通过。

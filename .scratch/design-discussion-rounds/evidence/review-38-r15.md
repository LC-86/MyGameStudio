# PR #38 审查修订情况（第十五轮修复，供 Codex 再次审查）

日期：2026-09-14。来源评论：https://github.com/LC-86/MyGameStudio/pull/38#issuecomment-5665180317

上一轮固定范围是 `21a46c5...4349c94`，第十五轮审查结论不通过（Standards 1 项 P2、Spec 2 项 P2，另含代码片段范围及同步核对的补充证据）。本文件记录修订后的情况。复审应对**本分支最新 HEAD** 重新取证，不要沿用 `4349c94` 或更早探针输出。

## 修订范围

只修评论列出的三项 P2，并处理同属代码片段身份/范围的两项补充证据。未升 `0.18.1` 版本号。未跑真实宿主端到端会话，也未调用真实模型。未合并、未删分支。

## 逐项处置

| 轴 | 项 | 处置 | 主要位置 | 反例测试 |
| --- | --- | --- | --- | --- |
| Standards-1(片段内规则) | 已有首条目标引用时，``存档兼容：`PATH \| daily_best 字段必须保留`。`` 被整段当重复引用删除，只剩「存档兼容：。」；同一片段里的其他模块规格路径一并消失，仍报 `saved/synced=true,to_sync=[],verify.ok=true` | 成对代码片段按**完整内容**认身份：去空白后必须等于规格路径才是本引用包裹。含规则、管道分隔字段、其他模块路径的片段不是本引用——定位跳过、不去重、不插版本；不能安全分离时保留整个片段 | `spec_sync._code_span_is_spec_path`/`_code_span_other_identity`/`_strip_line_citation` | `test_round15_code_span_identity_keeps_commands_rules_and_suffixes` 场景 span-rule |
| Spec-1(命令) | 正常主引用之后的 ``离线校验指令：`python scripts/check.py --spec PATH --offline`。`` 同步后只剩「离线校验指令：。」 | 同上：命令片段完整内容不等于规格路径，不当引用包裹，整段保留 | 同上 | 同测试场景 span-command |
| Spec-2(数字后缀) | `` `PATH②`（当前 v8） `` 因 `②` 属数字类别被截成 PATH，误升 v4；后面的真实 `PATH（当前 v3）` 被剥成「当前：。」 | 两处同时收口：`_extends_filename` 把 Unicode 数字类（`N`）与字母类一并视为文件名延续；代码片段另按完整片段内容比较身份。`PATH②` 不等于本规格，原样保留 v8；真目标行成为唯一命中并原位更新到 v4 | `spec_sync._extends_filename`/`_code_span_other_identity` | 同测试场景 circled-suffix |
| 补充(跨行代码片段) | 反引号、PATH、闭反引号分三行时，逐行把 `（当前 v4）` 插进代码内容，外部 v3 保留且报告同步通过 | 新增 `_in_multiline_code_span`：成对片段跨行且含规格路径时，`_replace_reference_lines` **整段保持原文**，由回读判定未完成（不宣称 `synced=true`） | `spec_sync._in_multiline_code_span`/`_replace_reference_lines` | 同测试场景 multiline-code-span（报告未完成断言） |
| 补充(已是 v4 的次引用) | 首引用已为 v4、次引用仍为 v3 时两者都保留且报告同步通过 | `baseline_cites_spec` 改为：任一处仍附着旧版本即未完成。`updated_ok` 在首条已是目标版本时也成立，其后按重复引用去重并保留同行业务正文 | `spec_sync.baseline_cites_spec`/`_replace_reference_lines` | 同测试场景 stale-second |

四个可完成场景走真实 GateService 的 v3→v4 冲突恢复并断言 `saved/synced=true`、`to_sync` 收口与回读通过；multiline-code-span 场景断言跨行片段原样、版本不进代码内容、同步不收口且回读失败。

## 反向验证

- 新增反例测试在修复前代码（`4349c94` 临时 worktree）上以评论描述的原始症状失败（14 项断言）：`存档兼容：。` 且 daily_best / 章节规格路径丢失；`离线校验指令：。`；`PATH②` 被升到 v4、真实引用被剥成 `当前：。`；次引用 v3 保留；跨行代码片段被插入 `（当前 v4）` 且报 `synced=true,to_sync=[],verify.ok=true`。
- 修复后五场景全部通过：规则/命令/其他模块路径完整保留；`PATH②` 保持 v8、真目标更新到 v4；已是 v4 的首条之后去掉旧版本重复引用；跨行代码片段原样保留并如实报告未完成。

## 验证与交付物

- README 五套聚合入口与八套 `test_design_discussion_*.py` 全部通过；`tests/test_*.py` 54/54（dist 重建后全量复跑）；代码定稿后重新执行 `./dist/build-package.sh`，包一致性与可重复构建检查通过；全 PR 范围 `git diff --check` 通过。
- 第六至十四轮全部布局用例继续通过（自定义标题恢复、混合内容节、同行列表/表格/重复引用、链接/其他模块/表格邻列/括号规则、尖括号/`.backup`/嵌套括号、空白目标/标题/`~` 备份/`./`/self-link/顶层中部版本、归档/括号文件名/`./` 链接/显示文字紧邻/代码片段/锚点、显示文字泛化/Unicode 目标后缀/引用式定义/双反引号、跨行链接/裸路径完整身份/带空格代码片段/目标尾点）——完整代码片段身份识别对已覆盖布局行为不变。
- 高层真实宿主交互与效率配对仍未验证，未调用真实模型，不把这些限制标为通过。

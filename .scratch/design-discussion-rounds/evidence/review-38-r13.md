# PR #38 审查修订情况（第十三轮修复，供 Codex 再次审查）

日期：2026-09-14。来源评论：https://github.com/LC-86/MyGameStudio/pull/38#issuecomment-5661317153

上一轮固定范围是 `21a46c5...2827df5`，第十三轮审查结论不通过（Standards 1 项 P2、Spec 2 项 P2，集中在链接显示文字/完整目标身份与引用式链接、双反引号代码片段）。本文件记录修订后的情况。复审应对**本分支最新 HEAD** 重新取证，不要沿用 `2827df5` 或更早探针输出。

## 修订范围

只修评论列出的三项。未升 `0.18.1` 版本号。未跑真实宿主端到端会话，也未调用真实模型。未合并、未删分支。

## 逐项处置

| 轴 | 项 | 处置 | 主要位置 | 反例测试 |
| --- | --- | --- | --- | --- |
| Standards-1(显示文字) | `[PATH 规格说明](PATH)（当前 v3）` 把 v4 插入显示文字,实际引用仍标 v3 | 显示文字跳过泛化为 `_in_link_label`:路径出现处于未闭合 `[` 与其后紧跟 `(` 的 `]` 之间即视为显示文字(不要求路径紧邻括号),跳过后定位**链接目标里**的路径;目标内不再认附着版本(锚点只剩链接闭括号之后),版本原位更新目标外附着括号的顶层版本 | `spec_sync._in_link_label`/`_find_path`/`_attached_version`/`_update_line_citation` | `test_link_structure_identity_keeps_labels_targets_and_code_spans` 场景 label-with-text |
| Standards-1 / Spec-1(完整目标身份) | `[历史规格](<PATH（备份）>)（当前 v8）` 的目标被改成 `<PATH（当前 v4；备份）>`、真目标被剥成 `当前：。`;`[备份](<PATH副本>)（当前 v8）` 被当成本规格更新 | 链接内的身份从"目标内 ASCII token"升级为**完整目标比较**:`_link_target_identity` 提取整个目标串(尖括号到 `>`、裸目标到空白/平衡闭括号),`_target_identity` 归一化(去空白、`./` 前缀、`#锚点`、句末点号)后必须与规格路径**相等**——`PATH（备份）`、`PATH副本` 都不相等,对应行不命中、原样保留;真目标行按唯一命中原位更新。目标解析不出时仍按命中交由调用方保守不动(沿用 r11 语义) | `spec_sync._target_identity`/`_link_target_identity`/`_find_path` | 同测试场景 backup-target、unicode-suffix |
| Spec-2(引用式链接与双反引号) | `[daily]: PATH "标题"` 被插入 `（当前 v4）` 到目标位置,原链接失效;双反引号 `` ``PATH`` `` 的版本被插进两个闭反引号之间 | 引用式链接定义按结构识别（`_LINKDEF_BEFORE_RE` + `_linkdef_target` 提取完整目标与可选标题后的锚点）:定义行没有能安全插入新版本的位置——锚点处已有附着版本括号时原位更新,否则**保持整行不动**,由回读判定未完成(该场景断言 `synced` 不收口、`verify.ok=false`);行内代码片段改为**反引号计数**（`_code_span`）:开串与等长闭串成对时版本插在闭串之后(单/双/多反引号一致),开串无等长闭串时保持不动 | `spec_sync._LINKDEF_BEFORE_RE`/`_linkdef_target`/`_code_span`/`_attached_version`/`_update_line_citation`/`_strip_line_citation` | 同测试场景 linkdef（报告未完成断言）、double-code-span |

五个场景中的四个走真实 GateService 的 v3→v4 冲突恢复并断言 `saved/synced=true`、`to_sync` 收口与回读通过;linkdef 场景断言定义行原样、同步不收口且回读失败(报告未完成)。

第六至十二轮全部布局用例继续通过(自定义标题恢复、混合内容节、同行列表/表格/重复引用、链接/其他模块/表格邻列/括号规则、尖括号/`.backup`/嵌套括号、空白目标/标题/`~` 备份/`./`/self-link/顶层中部版本、归档/括号文件名/`./` 链接/显示文字紧邻/代码片段/锚点)——完整目标身份与引用结构识别对已覆盖布局行为不变。

## 反向验证

- 新增反例测试在修复前代码（`2827df5` 临时 worktree）上以评论描述的原始症状失败（13 项断言）:`PATH（当前 v4） 规格说明` 版本进入显示文字;`<PATH（当前 v4；备份）>` 目标损坏且真目标被剥成 `当前：。`;`PATH副本` 目标被当本规格更新;`[daily]: PATH（当前 v4） "标题"` 定义行损坏且仍宣称同步完成;`` ``PATH（当前 v4）`` `` 版本进入双反引号之间。
- 修复后五场景全部通过:显示文字不动、版本在目标外;Unicode 后缀目标原样保留、真目标更新到 v4;引用式定义行原样且同步如实报告未完成;双反引号版本落在闭串之后。

## 验证与交付物

- README 五套聚合入口与八套 `test_design_discussion_*.py` 全部通过;`tests/test_*.py` 54/54（dist 重建后全量复跑）;代码定稿后重新执行 `./dist/build-package.sh`，包一致性与可重复构建检查通过;全 PR 范围 `git diff --check` 通过。
- 高层真实宿主交互与效率配对仍未验证,未调用真实模型,不把这些限制标为通过。

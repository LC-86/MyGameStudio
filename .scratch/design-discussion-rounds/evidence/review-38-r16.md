# PR #38 审查修订情况（第十六轮修复，供 Codex 再次审查）

日期：2026-09-14。来源评论：https://github.com/LC-86/MyGameStudio/pull/38#issuecomment-5665734675

上一轮固定范围是 `21a46c5...6023816`，第十六轮审查结论不通过（Standards 1 项 P2、Spec 2 项 P2，另含未配对反引号截断扫描的补充证据）。本文件记录修订后的情况。复审应对**本分支最新 HEAD** 重新取证，不要沿用 `6023816` 或更早探针输出。

## 修订范围

只修评论列出的两项 P2（同行后续旧版本引用、代码片段末尾句点），并处理同属代码片段扫描的补充证据。未升 `0.18.1` 版本号。未跑真实宿主端到端会话，也未调用真实模型。未合并、未删分支。

## 逐项处置

| 轴 | 项 | 处置 | 主要位置 | 反例测试 |
| --- | --- | --- | --- | --- |
| Standards-1 / Spec-1（同行后续引用） | 新基线 `行为依据：PATH（当前 v3）；验收依据：PATH（当前 v3；仍支持离线）。` 同步后前者升 v4、后者仍为 v3；`本轮依据：PATH（当前 v3）；离线验收参照 PATH（当前 v3）` 与同一表格行两个 Markdown 链接同结果，仍报 `saved/synced=true,to_sync=[],verify.ok=true` | 逐行遍历**每一处**完整路径身份：更新从右到左原位改到目标版本；回读任一处仍附着旧版本即未完成。不能把每行首个引用正确当作所有引用均已同步 | `spec_sync._iter_paths`/`_update_line_citation`/`_update_citation_at`/`_attached_version_at`/`baseline_cites_spec` | `test_round16_same_line_citations_and_code_span_dot` 场景 same-line-roles / same-line-refer / same-line-table-links |
| Spec-2（代码片段尾点） | `` `PATH.`（当前 v8） `` 被 `_target_identity` 默认剥除末尾句点，误当本规格升到 v4；后面的真实 `PATH（当前 v3）` 被剥成「当前：。」 | 成对代码片段已有明确边界，末尾句点属于路径，按 `strip_dot=False` 比较（与明确链接目标相同）。`PATH.` 不等于本规格，原样保留 v8；真目标成为唯一命中并更新到 v4 | `spec_sync._code_span_is_spec_path`/`_target_identity` | 同测试场景 code-span-dot |
| 补充（未配对开串） | 行首未配对双反引号使 `_paired_code_spans` 停止扫描，后面合法的带空格单反引号路径片段不被识别；v4 被插入代码内容，外部 v3 保留，仍报告同步通过 | 开串找不到等长闭串时当作正文，继续识别后续片段 | `spec_sync._paired_code_spans` | 同测试场景 broken-before-code |

五个可完成场景走真实 GateService 的 v3→v4 冲突恢复并断言 `saved/synced=true`、`to_sync` 收口与回读通过。

## 反向验证

- 新增反例测试在修复前代码（`6023816` 工作区）上以评论描述的原始症状失败（12 项断言）：验收依据仍为 v3；离线验收参照仍为 v3；表格行第二个链接仍为 v3；`` `PATH.` `` 升到 v4 且「当前：。」；未配对双反引号后版本插进 `` ` PATH（当前 v4） ` ``。上述场景当时仍报同步完成。
- 修复后五场景全部通过：同行两处引用均到 v4；`PATH.` 保持 v8、真目标更新到 v4；未配对开串后的带空格片段原位更新到 v4，版本不进代码内容。

## 验证与交付物

- README 五套聚合入口与八套 `test_design_discussion_*.py` 全部通过；`tests/test_*.py` 54/54（dist 重建后全量复跑）；代码定稿后重新执行 `./dist/build-package.sh`，包一致性检查通过；全 PR 范围 `git diff --check` 通过。
- 第六至十五轮全部布局用例继续通过。
- 高层真实宿主交互与效率配对仍未验证，未调用真实模型，不把这些限制标为通过。

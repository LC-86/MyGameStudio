# 03: 即时保存决定并恢复讨论

**What to build:** 开发者确认问题组后，方案设计在既有记录授权内及时保存本轮最小决定记录，准确报告保存状态。即使模块尚未结束或会话中断，后续也能从实际记录恢复已定、未决和待同步内容，不需要开发者重新回答。

**Blocked by:** 02 — 识别任务并完成模块问答。

**Status:** ready-for-agent

**Progress:** 已完成（2026-09-14 收口；接缝：`plugin/skills/game-design/decisions.py` 的 `plan_save`/`plan_sync`/`apply_save`/`verify_saved`/`restore_from_records`，配合 `decision_records.py`（记录格式）、`decision_mapping.py`（本轮结果映射）、`decisions_cli.py`（命令行）；执行记录见 Comments）

**规格依据：**《MyGameStudio：统一设计问答框架》；用户故事 16～18、22、25、55；验收场景 6、8；Implementation Decisions 的及时保存、同步与恢复、授权保持。

- [x] 将本轮答案与实际展示的问题和建议对应，保存模块与问题关联、采纳内容、决定者和日期、用户回复及建议出处、未决项、影响和基线同步状态。助手建议与临时假设不冒充用户决定。
- [x] 在开始依赖这些答案的下一轮前完成本轮必要保存；按模块沿用已有记录位置，不为每个问题强制新建文件、工单或完整报告。
- [x] 写入前核对当前授权、目标版本和相关历史；通过现有受控通道写入并回读，确认本轮内容完整、历史未丢失、没有重复以及同步状态正确。不得以缓存结果替代逐次权限和版本校验。
- [x] 同一次回答重复处理不会重复创建决定；用户修改决定时保留旧含义及替代关系，不覆盖其他尚有效的决定或后来的用户修改。
- [x] 正确区分已采纳、已保存、已同步核心基线、已实现和已验证。决定已保存但基线尚未同步时，后续能定位待同步内容，不能只读旧基线后重问或误判可开工。
- [x] 只读讨论、缺写入授权、写入被拒、版本冲突或保存失败时，报告真实状态；没有回读成功不得称为已保存，也不换通道绕过保障。
- [x] 在回答后、模块结束前中断，再恢复时先读取实际记录和版本；已完成且仍有效的内容保留，只继续未完成部分。遇到外部修改时重新核对受影响内容，不恢复覆盖旧快照。
- [x] 用实际高层会话与最终记录验证正常保存、部分回答、重复回答、改口、只读、失败及中断恢复；不能用报告中的自述代替实际保存证据。

## Comments

### 2026-09-14 执行记录（票 03）

**做了什么。** 在分支 `codex/unified-game-design-framework` 增加决定保存与恢复接缝，位置：

- `plugin/skills/game-design/decisions.py`（492 行）：公开 `plan_save`（本轮最小记录 + 目标版本与写入前核对）、`plan_sync`（仅在有同步授权时标记已同步）、`apply_save`（经受控通道提交并回读）、`verify_saved`（回读核对）、`restore_from_records`（从实际记录恢复已定/未决/待同步），以及 `GateChannel` 提交适配。
- `plugin/skills/game-design/decision_records.py`（317 行）：记录格式的唯一解释与渲染位置（决定头、来源与建议出处、影响、未决项、替代关系、同步状态）。
- `plugin/skills/game-design/decision_mapping.py`（182 行）：`rounds.run_round` 题目目录/采纳来源/未决原因 → 记录条目与报告的映射。
- `plugin/skills/game-design/decisions_cli.py`（106 行）：`plan|save|sync|restore` 命令行入口，写入与 `mgs_write` 同一条 `GateService` 受控路径。
- `plugin/skills/game-design/rounds.py`：`run_round` 输出补充 `module`/`round`/`user_reply`/`catalog`（本轮实际展示的题目与建议），供保存把答案对应到当时展示内容。
- `plugin/skills/game-design/SKILL.md`：新增「决定保存与恢复」段（保存时机、只读、状态分档、写入被拒/冲突/失败的真话报告、中断恢复），质询分支步骤接入。
- `tests/test_design_discussion_decisions.py`（834 行，10 个测试函数）：只经公开接缝观察行为。
- `dist/`：按 `sh dist/build-package.sh` 重建（96 个文件），`dist/CHANGELOG.md` 文件数同步。

**场景。** 固定「齿轮谜城每日挑战」模块（Q1 关卡来源、Q2 与章节关系、Q3 每日身份、Q4 依赖 Q3 的记录、Q5 商业化），经真实 `GateService` 受控通道（设计角色 + 记录目录授权 + 设计讨论用途）在临时项目落盘，再直接回读文件与记录核对。

**验证。**

- `python3 -B tests/test_design_discussion_decisions.py`：10 项全通过。覆盖：正常保存（决定者/日期、用户回复、建议出处、影响、未决项、同步状态，且无关模块 Q5 不入记录）、部分回答（未决落盘、同模块沿用同一记录、两轮 3 项决定无重复文件）、重复回答（`no_new`、无第二次写入、决定头唯一）、改口（旧值标已被替代 + 替代关系，其他决定不受影响；旧回答重放不覆盖后来的用户修改）、只读（不写入、明确未保存、授权后保存；恢复 `to_sync` 可定位；已定不重问；同步标记后仅剩真正待同步项；缺同步授权保留待同步）、版本冲突/授权拒绝/授权撤销/回读失败（真实 `rule_stage`、不称已保存、不绕行）、中断恢复（先读实际记录、外部修改后以实际记录为准、只续未完成）、状态分档（已采纳/已保存/已同步/已实现/已验证分别记录，无证据不标已实现/已验证）、真实 mgs-gate 工具入口（`mgs_scope`→`mgs_write`：授权内保存成功、越界 `task_grant` 拒绝且不重试）、CLI 冒烟（按固定会话顺序实跑正常/部分/重复/改口/中断恢复/同步/只读/失败八类，留实际记录文件作证）。
- `python3 -B tests/test_design_discussion_rounds.py`、`tests/test_design_discussion_metrics.py`、`tests/test_package_skill_content_design.py`、`tests/test_package_dist.py`、`tests/test_plugin_package.py`：均通过。
- `python3 -m compileall plugin tests`：通过。
- 全量套件（`for t in tests/test_*.py; do python3 -B "$t"; done`）：49/49 文件全部通过。

**代码审查（/code-review，双轴，独立实施并自行执行两轴）。** Standards 轴发现并修复：`_head` 与 `decision_head` 重复实现（合并为单一实现）；`decisions.py` 曾达 943 行且 `plan_save`/`apply_save`/`parse_record` 超长（按仓内规格决策 30 的 500/600 行复查线拆分为四个 module，最大 492 行，函数均 ≤68 行）；死代码 `SOURCE_LABELS`/`REPLY_LINE`/`SYNC_DONE_LINE`/`_pattern_covers`/`section_date`/`_INDEX_SOURCES` 移除；`parse_record` 内 `section_date` 的 O(n²) 复用改为循环内维护。Spec 轴发现并补齐：缓存视图必须由通道逐次版本校验拒绝（补测）；旧回答重放不得覆盖后来的用户修改（补实现与测试）；真实 mgs-gate 工具入口证据（补 `_McpChannel` 测试）。

**例外（如实单列）。** 本票未在真实宿主会话（codex 进程 + MCP 服务器连接）中实跑端到端会话；CLI 冒烟经会话内进程调用同一 `GateService` 受控路径并留实际记录文件作证，`mgs_scope`/`mgs_write` 的 MCP 工具处理路径由 `tests/test_design_discussion_decisions.py::test_mcp_gate_tool_entry_saves_and_denies` 直接调用 `mcp_gate.handle_tools_call` 覆盖，宿主连接由 `tests/test_runtime_gate*.py` 既有主题覆盖。本票不报告效率验收结论（未做耗时对照）；本票不修改 G02 产品资料、权限配置、治理文件与 `docs/agents/`。

# 07: 完整处理功能删减

**What to build:** 开发者明确删减已有功能后，方案设计沿用变更流程，查清功能原来承担的作用及残留依赖，形成完整的删减后设计。既不会遗漏奖励、引导或数据处理，也不会自动以另一个同类功能恢复用户想去掉的负担。

**Blocked by:** 06 — 优化已有设计并同步连带影响。

**Status:** ready-for-agent

**Progress:** 已完成（2026-09-14 收口；接缝：`plugin/skills/game-design/removal.py` 的 `plan_removal`/`apply_removal`/`verify_removal`，配合 `removal_impact.py`（原作用盘点、残留依赖、数据权益）、`removal_cli.py`（命令行）、`change_render.py` 的删减段渲染与 `change_flow` 族；执行记录见 Comments）

**规格依据：**《MyGameStudio：统一游戏设计问答框架》；用户故事 49～51、54；验收场景 22；“已有设计变更模式”的删减与成稿约定。

- [x] 用户已明确删除方向时不反复询问是否删除；根据实际资料列出原功能的作用和关联，只对尚未明确且影响体验的处理方式提出问题。
- [x] 对原作用分别处理一起取消、转移给已有系统或更简单地保留；不强制每个被删功能都有替代品，不因移除每日任务自动添加实质相同的每日目标。
- [x] 检查奖励来源与成长节奏、行动引导、解锁条件、入口、教程、内容、数据和验收中的适用依赖，追踪间接引用；明确哪些一起取消、哪些需要重新配置、哪些不受影响。
- [x] 根据真实项目阶段检查已有进度、待领资源、存档或权益。不存在的数据不机械讨论，未知对象先核实；处理方案和实际迁移、退款或清理行为保持授权分离。
- [x] 明确正式取消、当前版本不做和已明确承诺的后续范围，不把删除自动转成未来任务，也不将延期误报为永久取消。
- [x] 在获准的设计同步中处理失效规则、引用及旧验收要求，保留历史和替代关系；其余现行设计不变。仅授权文档处理时，不实际删除代码、资源或用户数据。
- [x] 更新后的设计与简短变更记录一致，能看清删掉什么、原因、原作用如何处理、关联变化和待验证方法；设计完成与实际实现及效果验证分别报告。
- [x] 用同时承担奖励与引导的功能作为测试样例，覆盖取消作用、转移已有系统、简化保留，以及永久取消和本版不做；检查残留引用、历史保留、无关内容和未授权对象不变。

## Comments

### 2026-09-14 执行记录（票 07）

**做了什么。** 在分支 `codex/unified-game-design-framework` 上以票 06 的 `change_flow` 族为基础增加删减深化接缝，未另造记录体系：

- `plugin/skills/game-design/removal_impact.py`（383 行）：公开 `inventory`（八个方面逐项盘点原作用与关联元素，缺项如实报缺口）、`prepare_items`（作用处理落到设计元素；已明确时透传 `disposition`，未明确且影响体验时转为取舍问题）、`residual`（按票 06 同一依赖追踪分「一起取消／需要重新配置／不受影响／待明确」，间接引用带经由路径）、`lanes`（八个方面各自的残留处理 + 作用处理结论）、`role_by_item`（元素→作用映射，供盘点与问题标注共用）。
- `plugin/skills/game-design/removal.py`（215 行）：公开 `plan_removal`（原作用盘点 → 复用 `change_flow.plan_change` 的四项变更说明、影响、阶段、文件计划与状态分档 → 装饰删减专项结果；作用盘点、数据权益或后续承诺有缺口时返回 `incomplete`，不产出可写入内容）、`apply_removal`（经 `gate_commit.commit_path` 同一受控通道逐文件提交并回读）、`verify_removal`（在票 06 核对之上加：失效规则必须退出正文、变更记录含八个方面作用处理与取消范围、数据与权益处理、残留依赖检查）。
- `plugin/skills/game-design/removal_cli.py`（74 行）：`plan|apply|verify` 命令行入口，写入与 `mgs_write` 同一条 `GateService` 受控路径；缺凭据不签发。
- `plugin/skills/game-design/change_render.py`：`_disposition_lines` 在删减入口提供 `record['removal']` 时渲染八个方面的原作用盘点、残留依赖检查、数据与权益处理与「完成边界」；否则保持票 06 的透传输出不变（票 06 测试复跑通过）。
- `plugin/skills/game-design/change_flow_cli.py`：`_paths`/`_read_all` 提升为公开 `payload_paths`/`read_all` 供删减入口复用，避免两处各自从 payload 推断待读文件集合。
- `plugin/skills/game-design/SKILL.md`：新增「功能删减（完整处理原作用与残留依赖）」段与质询分支第 7 步。
- `tests/test_design_discussion_feature_removal.py`（1017 行，13 个测试函数）：只经公共接缝观察行为。
- `dist/`：按 `sh dist/build-package.sh` 重建（117 个文件），`dist/CHANGELOG.md` 文件数同步。

**场景。** 固定「齿轮谜城」删除同时承担奖励与引导作用的「每日挑战」（已发布、有实际玩家）：原作用盘点为奖励来源（转移给章节结算）、行动引导（简化保留为章节进度提示）、解锁条件（简化为按关卡数）、入口／教程／内容／验收（一起取消）；残留依赖 `daily_cadence`（对象本身）、`daily_reward`（直接）、`unlock_cost`（间接，经 `daily_cadence → daily_reward`）与不受影响的 `chapter_order`；数据侧旧档 `dayBest` 停写只读保留、清理动作单列为待授权；取消范围分别记正式取消、当前版本不做（旧档清理）与已明确承诺的后续范围（教程步骤）。未明确且影响体验的解锁方式与存档处理成为 Q5/Q6，答复后经 `change_flow.answer_turn` → `rounds.run_round` → `decisions.plan_save` 走票 02/03 同一路径；同步用真实 `GateService` 受控通道落到临时项目，产品代码、存档、管理资料与无关模块保持原样。

**验证。**

- `python3 -B tests/test_design_discussion_feature_removal.py`：13 项全通过。覆盖：原作用盘点与只问未明确处理（八个方面、作用与关联、三类标签、问题编号接当前模块问题组、问题来源作用、不重复询问是否删除）；三类作用处理（取消不要求替代品、转移写明承接系统与方式、简化保留写明形式；实质相同的替代（`equivalent_replacement` 或承接名含被删对象）判 `incomplete` 且零写入）；残留依赖（一起取消／需要重新配置／不受影响分类、间接深度与经由路径、八个方面结论、缺项报「作用盘点缺项」）；数据与权益（已发布核对四类对象、存在给方案、不存在不生成动作、缺方案如实报告、未核实不得当作不存在、待授权动作单列且注明「需另行授权…不执行」、只有设计阶段不讨论不存在对象）；取消范围（正式取消／当前版本不做／已明确承诺的后续范围、延期不误报永久取消、承诺缺来源报缺口）；同步与历史（只改 5 个受影响文件、旧规则与旧入口旧验收退出正文、历史段保留替代关系、转移与简化规则写入既有系统、产品代码与用户数据不动、无依赖模块不变、回读核对通过）；变更记录（作用处理段、八个方面、取舍作答与来源、残留依赖与间接路径、待验证方法与阻断影响、原适用版本、完成边界、状态与真实结果一致）；只读与越界（只读零写入、不经通道、被拒按实际报告且产品代码／用户数据／管理资料／技术设计／设计文档／变更记录均无半写）；计划不预称已保存／已同步、缺变更记录位置时如实报告不另建文档；作用处理回答复用票 02/03；删减沿用票 06 字段口径（保留项、原因、来源、阶段、受依赖追踪、深度、旧验证结果版本标注）；CLI 冒烟（`plan`/`apply`/`verify` 经真实受控通道；缺凭据不自行签发）；Game-Design 入口指向接缝与概念。
- `python3 -B tests/test_design_discussion_change_flow.py`（票 06，16 项）、`tests/test_design_discussion_full_design.py`（票 05）、`tests/test_design_discussion_spec_draft.py`（票 04）、`tests/test_design_discussion_decisions.py`（票 03）、`tests/test_design_discussion_rounds.py`（票 02）、`tests/test_design_discussion_metrics.py`（票 01）、`tests/test_package_skill_content_design.py`：均通过。
- `python3 -m compileall plugin tests`：通过。
- `python3 -B tests/test_package_dist.py`、`tests/test_plugin_package.py`：通过（dist 与 plugin/ 逐文件一致、可复现构建）。
- 全量套件（`for t in tests/test_*.py; do python3 -B "$t"; done`）：53/53 文件全部通过。

**代码审查（/code-review，双轴，独立实施并自行执行两轴）。** Standards 轴发现并修复：`removal_impact.prepare_items` 与本入口的问题标注各自重建「元素→作用」映射（抽为公开 `role_by_item` 供两处共用）；`removal._refresh_record` 的 `meta` 参数仅作兜底且与 `plan["meta"]` 重复（去掉参数）；死代码 `STATUSES_WITHOUT_WRITE`、`DISPOSITION_KINDS`、`role_id`、未用字段 `via`（移除或改由 trace 提供）；`removal_cli` 直接导入 `change_flow_cli` 的私有 `_paths`/`_read_all`（提升为公开 `payload_paths`/`read_all`）；`_data_entry` 签名超 79 列（折行）。Spec 轴发现并修复：删减作用处理此前只写在元素级 `disposition`，未进入变更记录的取消范围与数据权益段（补渲染与回读核对）；失效规则是否真的退出正文此前只核对「替代关系在历史段」，未检出正文残留（补 `_retired_failures` 逐行核对并加断言）；延期与本版不做混同风险（补 `当前版本不做` 整句判定，避免「延期不误报为永久取消」反向失守）；`_equivalent_gaps` 对空承接名做子串匹配会误报（收紧为承接名非空且含被删对象名才判实质相同）。

**例外（如实单列）。** 本票未在真实宿主会话（codex 进程 + MCP 服务器连接）中实跑端到端会话；CLI 冒烟经会话内进程调用同一 `GateService` 受控路径并留实际交付文件作证，宿主连接由 `tests/test_runtime_gate*.py` 既有主题覆盖。原作用盘点、残留依赖与数据权益判断消费调用方给出的结构化材料（讨论产出的结构化结果），本票不负责从自由文本自动抽取作用或依赖；「实质相同的替代」由承接名是否含被删对象名或显式标记判定，不声称能对任意措辞做语义等同判定。仅授权文档处理时不删除代码、资源或用户数据由「写入范围只有设计文档 + 待授权动作单列」保证；实际迁移、清理或退款执行不在本票范围。`tests/test_design_discussion_feature_removal.py` 为 1017 行，高于仓内「测试单文件尽量不超过 500 行」的目标（判 30/31 的软目标），与同系列票 03～06 同一取舍：会话级夹具（受控通道、临时项目、依赖图、八方面作用表、三阶段对象表）被十三个场景共用，拆文件会引入重复夹具或额外支撑模块；本项留作判断项，不隐藏。本票不报告效率验收结论（未做耗时对照）；本票不修改 G02 产品资料、权限配置、治理文件与 `docs/agents/`；`dist/` 仅重建产物并同步文件数说明，版本保持 0.18.1。

# 06: 优化已有设计并同步连带影响

**What to build:** 开发者提出已有功能的优化或调整后，方案设计以当前有效设计为起点，说明改善目标和保留项，主动分析依赖及项目阶段，完成关键取舍、受影响设计同步和简短变更记录。未受影响的既有决定继续有效。

**Blocked by:** 04 — 将模块决定整理为可交接规格。

**Status:** ready-for-agent

**Progress:** 已完成（2026-09-14 收口；接缝：`plugin/skills/game-design/change_flow.py` 的 `plan_change`/`apply_change`/`verify_change`/`answer_turn`，配合 `change_impact.py`、`change_input.py`、`change_render.py`、`change_report.py`、`change_flow_cli.py`；执行记录见 Comments）

**规格依据：**《MyGameStudio：统一游戏设计问答框架》；用户故事 44～48、53～55；验收场景 20、21、24、25；“已有设计变更模式”。具体功能删减的作用处理由第 07 票深化。

- [x] 读取现行设计、已有决定及相关实际状态，提取修改对象、原因、预期改善和必须保留的内容。区分用户只提出问题与已经决定修改的情况；明确决定不重复确认，重大新影响只引出新增取舍。
- [x] 主动分析玩法规则、成长资源、界面引导、内容资产、数据及验收的直接和间接影响，分类为必须同步、需要用户取舍、不受影响；根据实际关系继续追踪，不以文件相邻作为影响边界。
- [x] 核实项目属于只有设计、已开发未发布或已发布有玩家，并检查实际存在的存档、进度、奖励及权益。阶段未知不能当作对象不存在，也不追问不存在的补偿或迁移。
- [x] 模块调整使用当前模块问题组；结构性调整检查受影响的多个模块；方向性变化重新审视相关核心方向，并保留其余有效决定。无关问题不扩成本次全面重做。
- [x] 每个候选说明改什么、保留什么、预期改善和代价；AI 承担事实调查、计算与关联分析，不将技术实现细节转成用户必须逐项作答的问题。换名或转移复杂度不被当作改善证据。
- [x] 用新玩家、已有进度、资源不足、退出和相关路径等适用场景推演变化；数值或流程逻辑自洽与实际体验改善分开。需要试玩时保留具体方法及阻断影响，不以无限提问代替验证。
- [x] 获准同步后更新真正受影响的当前设计及验收依据，使失效规则和引用退出现行版本，历史与替代关系仍可追溯；保留不受影响的内容，不重造整套文档。
- [x] 简短变更记录包含目标与原因、旧设计到新设计、影响范围、采纳来源、待验证方法及保存、同步、实现、验证状态。设计完成需要关键取舍明确、关联已同步、旧规则已处理及无未说明的关键断点。
- [x] 受影响的旧验证结果标明原适用版本，不能证明新方案已通过；缺少实际运行或效果证据时，不称实现或优化效果完成。
- [x] 分别用三种项目阶段及一次方向调整的夹具验证依赖分析、保留项、同步范围和状态。只授权设计文档修改的测试中，产品代码、资源、数据和外部系统保持原状。

## Comments

### 2026-09-14 执行记录（票 06）

**做了什么。** 在分支 `codex/unified-game-design-framework` 增加已有设计变更接缝,位置：

- `plugin/skills/game-design/change_flow.py`（428 行）：公开 `plan_change`（四项变更说明 → 影响分析 → 阶段核对 → 文件计划与状态分档）、`apply_change`（逐文件经受控通道提交并回读）、`verify_change`（回读核对当前设计、旧规则退出、旧验证结果版本标注）、`answer_turn`（把新增取舍问题组成 `rounds.run_round` 可消费的一轮，沿用票 02/03 问答与保存路径）。
- `plugin/skills/game-design/change_impact.py`（370 行）：`analyze` 从变更对象出发按**实际依赖** BFS 追踪直接（depth 1）与间接（depth 2+，带 `经 cadence → seed` 路径）影响，分「必须同步／需要开发者取舍／不受影响」，六方面（玩法规则、成长资源、界面引导、内容资产、数据、验收）逐项给出结论；`stage_check` 按三阶段给出核对对象与「存在／不存在／未核实」三档；`organize` 按变更深度（局部微调／模块调整／结构性／方向性）组织工作与核心方向重审。
- `plugin/skills/game-design/change_input.py`（258 行）：四项说明、新增问题、候选（改什么/保留什么/改善/代价/证据）、`unresolved_candidates`（只换名或转移复杂度 → `改善证据不足` 缺口）、场景推演（自洽性与体验改善分开）、变更记录材料与 `dispositions`（取消／转移给已有系统／更简单方式保留，为票 07 留接缝）。
- `plugin/skills/game-design/change_render.py`（284 行）：受影响规则的唯一改写与历史段渲染（旧规则进「## 历史规则（已退出当前有效版本）」并记替代关系）、当前有效设计（版本、双指纹、变更索引）、简短变更记录（目标与原因／旧设计到新设计／影响范围／阶段与对象／事实与计算／候选／场景推演／待验证／旧验证结果／状态）。
- `plugin/skills/game-design/change_report.py`（87 行）：计划、待取舍、未完成、只读、已保存、失败六类措辞。
- `plugin/skills/game-design/change_flow_cli.py`（99 行）：`plan|apply|verify` 命令行入口，写入与 `mgs_write` 同一条 `GateService` 受控路径。
- `plugin/skills/game-design/SKILL.md`：新增「已有设计变更（补充、优化、调整）」段与质询分支第 6 步。
- `tests/test_design_discussion_change_flow.py`（1064 行，16 个测试函数）：只经公共接缝观察行为。
- `dist/`：按 `sh dist/build-package.sh` 重建（114 个文件），`dist/CHANGELOG.md` 文件数同步。

**场景。** 固定「齿轮谜城每日挑战 → 每周挑战」：变更对象 `cadence`，直接依赖 `seed`/`menu`/`save`/`acceptance_daily`，间接（经 `cadence → seed`）`reward`/`pool`；`reward`（每日结算 3 枚）与 `save`（dayBest）为需要取舍项，成为 Q5/Q6；章节规则与周期无实际依赖，列入不受影响。取舍答复后经 `change_flow.answer_turn` → `rounds.run_round` → `decisions.plan_save` 走票 02/03 同一路径；同步用真实 `GateService` 受控通道（设计角色 + 记录目录 + 核心基线写入范围 + `change_sync` 用途）落到临时项目，未受影响的 PRODUCT/TECH/CODE/章节规格保持原样。

**验证。**

- `python3 -B tests/test_design_discussion_change_flow.py`：16 项全通过。覆盖：四项说明与不重复确认已定方向（原因/改善/保留项原文保留；只对 `reward`/`save` 提问；编号从当前模块问题组 Q5 续）；直接与间接影响追踪（depth 0/1/2、经由路径、六方面结论、不受影响写明核对依据）；三阶段核对对象（只有设计不查实现与存档兼容；已开发未发布不追问玩家进度与迁移；已发布核对进度/待领/权益/迁移/发布；不存在的对象如实记为不存在且不冒充未核实；阶段未知时对象一律「未核实」并给出核实要求）；取舍答复后同步（只写 4 个受影响文件、新规则就位、旧规则退出正文进历史段、数据规则随选项更新、未受影响资料与产品代码零改动、状态分档、缺证据不标已实现/已验证）；候选（改什么/保留什么/改善/代价；换名方案「不构成改善证据」且只换名的采纳方案返回 `incomplete` 不写入）；场景推演（五类适用场景、不适用写理由、自洽性与体验改善分开、试玩方法与阻断影响）；变更深度（模块调整用当前模块问题组；结构性列出受影响两模块；方向性只重审相关核心方向、其余保留；相关方向未审视返回 `incomplete`；局部微调不附加无关验证）；只读与越界（只读零写入、不经通道、被拒按实际报告未保存且管理资料/技术设计/产品代码/数据目录无半写）；三阶段 + 方向调整夹具（依赖分析一致、保留项不变、状态未虚报）；取舍回答复用票 02/03（固定题目结构、决定落为 Q5/Q6 两条并有影响说明）；计划不预称已保存/已同步；旧验证结果标明原适用版本且缺标注时回读核对检出；删减作用处理透传（`transfer` → 「转移给已有系统」）；旧规则定位失败时 `incomplete` 且零写入；CLI 冒烟（`plan`/`apply`/`verify` 经真实受控通道；缺凭据不自行签发）；Game-Design 入口指向接缝与概念。
- `python3 -B tests/test_design_discussion_rounds.py`（票 02）、`tests/test_design_discussion_decisions.py`（票 03）、`tests/test_design_discussion_spec_draft.py`（票 04）、`tests/test_design_discussion_full_design.py`（票 05）、`tests/test_design_discussion_metrics.py`（票 01）、`tests/test_package_skill_content_design.py`：均通过。
- `python3 -m compileall plugin tests`：通过。
- `python3 -B tests/test_package_dist.py`、`tests/test_package_manifest.py`、`tests/test_plugin_package.py`：通过（dist 与 plugin/ 逐文件一致、可复现构建）。
- 全量套件（`for t in tests/test_*.py; do python3 -B "$t"; done`）：52/52 文件全部通过。

**代码审查（/code-review，双轴，独立实施并自行执行两轴）。** Standards 轴发现并修复：`change_flow.py` 曾达 649 行（超仓内 600 行复查线），按职责拆出 `change_input.py`（材料整理）与 `change_report.py`（报告措辞），编排文件回落 428 行，全部函数 ≤50 行（原 `plan_change` 72 行 → 41 行）；`_state_lines` 中 `planned` 状态与真实结果混用（计划内容曾写「已同步核心基线：是」）改为一律如实标否并在写入时重渲染。Spec 轴发现并修复：计划阶段 `states.synced` 由材料内容推定（未写入即称已同步），改为计划阶段恒为否、仅在写入后按实际写入文件分档；`verify_change` 读 `plan["results"]` 而结果实际在 `plan["record"]["results"]`，导致「旧验证结果未标明原适用版本」检查从不触发（改为直接携带 `results`，并把判定收紧为「原适用版本 v2」整串）；旧规则在现行设计中定位不到时静默跳过（现返回 `incomplete`，且已生效的重复执行不误报）；变更记录的取舍作答与采纳来源未落记录（补 `- 取舍作答：Q5=A` 渲染与回读核对）；`mark_results` 的 `valid_for_current` 为死数据（移除）。

**例外（如实单列）。** 本票未在真实宿主会话（codex 进程 + MCP 服务器连接）中实跑端到端会话；CLI 冒烟经会话内进程调用同一 `GateService` 受控路径并留实际交付文件作证，宿主连接由 `tests/test_runtime_gate*.py` 既有主题覆盖。影响分析、候选与场景推演消费调用方给出的结构化材料（讨论产出的结构化结果），本票不负责从自由文本自动抽取依赖或规则。删减功能的**原作用处理与残留依赖检查**仅做到透传 `disposition` 并在变更记录单列「被删减功能的作用处理」段；「取消／转移／简化保留」三类处理的完整判定、正式取消与本版不做的区分由第 07 票深化，本票不为它预写替代逻辑。`tests/test_design_discussion_change_flow.py` 为 1064 行，高于仓内「测试单文件尽量不超过 500 行」的目标（判 30/31 的软目标），与同系列票 03（834 行）、票 04（975 行）、票 05（1017 行）同一取舍：会话级夹具（受控通道、临时项目、依赖图、三阶段对象表）被十六个场景共用，拆文件会引入重复夹具或额外支撑模块；本项留作判断项，不隐藏。本票不报告效率验收结论（未做耗时对照）；本票不修改 G02 产品资料、权限配置、治理文件与 `docs/agents/`；`dist/` 仅重建产物并同步文件数说明，版本保持 0.18.1。

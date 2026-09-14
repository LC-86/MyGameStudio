# 08: 减少重复读取与检查

**What to build:** 在新设计成稿和已有设计变更两条完整流程中，只读取当前需要的资料，及时执行必要保存检查，在模块收敛后统一检查规格；输入未变时复用有效结果，变化或失败时针对性复查，从实际执行中减少重复工作。

**Blocked by:** 05 — 从游戏想法形成完整设计文档；07 — 完整处理功能删减。

**Status:** ready-for-agent

**Progress:** 已完成（2026-09-14 收口；接缝：`plugin/skills/game-design/checks.py` 的 `begin`/`plan_reads`/`record_read`/`record_write`/`before_save`/`after_save`/`after_write`/`converge`/`invalidate`/`reuse`/`remember`，配合 `check_state.py`（状态基元与判定规则、`INVALIDATION` 失效触发）与 `check_evidence.py`（`evidence`/`ledger`/`summary`/`report`/`measure`）；`decisions`/`spec_draft`/`full_design`/`change_flow`/`removal` 经可选 `session` 接入同一时机约定；执行记录见 Comments）

**规格依据：**《MyGameStudio：统一游戏设计问答框架》；用户故事 26～29；验收场景 10、12、13；“读取与检查时机”。本票验证检查行为，最终耗时结论由第 09 票判定。

- [x] 开始或恢复时核对模式、项目阶段、目标、授权、相关决定与未决项，从现有入口定位资料，只展开当前模块和必要依赖；不每轮重读所有未变规则、模板或项目材料。
- [x] 每轮保存前核对实际答案、采纳范围、来源、矛盾、当前可写范围及目标版本；保存后回读内容，检查本轮完整性、重复、历史、同步状态和新改引用。
- [x] 连续多轮只新增本模块决定且未改核心基线时，不因此重跑全部基线、全部链接或无关远端任务检查；模块收敛并获准同步后，按真实影响完成一次统一核对。现有必需检查不被取消。
- [x] 已读资料与已通过检查的输入未变且仍在适用范围时复用结果，保留内容身份和范围依据；不只凭修改时间判断有效。新会话只复用可核验结果，否则补做对应检查。
- [x] 每次写入的权限和版本校验仍由受控通道执行，不能缓存跳过。版本冲突、外部修改、授权变化、断链、写入失败或证据不足时作废相关旧结果，只重新读取和检查受影响部分。
- [x] 优先复用统一读取、指纹、链接及范围核对能力；相同目的检查合并执行，不每轮临时生成一套脚本或逐文件重复调用。不新增独立缓存服务、后台监控或持久化系统。
- [x] 纯讨论且未授权保存时不运行落盘检查；保存失败时准确报告并先处理相关问题。日常回复只保留保存结果、必要限制和下一组问题，检查明细在已有记录中简短保留。
- [x] 两种模式分别验证连续多轮输入未变、模块结束、外部引用变化、权限撤销、版本冲突及写入失败。实际事件和文件状态证明必要检查存在、重复检查减少、相关复查发生、无关模块未被全量重查。
- [x] 保留同一固定场景的实际读取、写入、检查与调用变化依据；一条工具调用内部的多次文件操作仍分别计数，不通过仅合并调用制造步骤减少。不得以少做必要工作或将同步延后到计时外取得效率结果。

## Comments

### 2026-09-14 执行记录（票 08）

**做了什么。** 在分支 `codex/unified-game-design-framework` 上新增检查时机与复用接缝，未另造缓存体系（会话即全部状态），并把两条流程接入同一约定：

- `plugin/skills/game-design/checks.py`（576 行）：公开 `begin`（核对模式/阶段/目标/授权/决定/未决项，只展开当前模块与必要依赖）、`plan_reads`/`record_read`/`record_write`（读取计划与身份记录：内容身份 = 路径 + SHA-256 指纹；未变复用、变化重读、无关不展开；写入者按实际内容登记身份）、`before_save`（实际答案、采纳范围、来源、矛盾、当前可写范围、目标版本；同一输入的核对结论按签名复用，签名含回复 + 采纳 + 范围 + 目标版本 + 历史）、`after_save`（回读核对本轮完整、无重复、历史、同步状态、新改引用；未改核心基线时把全局重查记为 skipped）、`after_write`（各流程共用的落盘后回读适配）、`converge`（模块收敛一次统一核对，范围按真实影响：当前模块/跨模块/全局）、`invalidate`/`invalidate_outcome`/`invalidate_blocked`（外部修改、撤销授权、版本冲突、写入失败、断链、证据不足六类失效触发）、`reuse`/`remember`。
- `plugin/skills/game-design/check_state.py`（430 行）：状态基元与判定规则（快照、证据计数、指纹、适用范围、失效登记、命令/答案解析、采纳与矛盾判定、回读判定、引用核对），唯一一套措辞与范围标签。
- `plugin/skills/game-design/check_evidence.py`（89 行）：`evidence`/`ledger`/`summary`/`report`/`measure`——实际读取、写入、检查与调用计数；一条调用内多文件分别计数；日常回复只留保存结果与检查数。
- 既有接缝接入：`decisions.plan_save/apply_save`、`spec_draft.apply_handoff`、`full_design.apply_delivery`、`change_flow.apply_change`、`removal.apply_removal` 均新增**可选** `session` 参数（不传时行为与票 03～07 完全一致）；落盘前 `converge`、逐文件 `record_write`、落盘后 `after_write`，冲突/被拒/写失败经 `invalidate_outcome` 作废相关旧结果。
- `plugin/skills/game-design/SKILL.md`：新增「检查时机与复用（减少重复读取与检查）」段；质询分支第 1、3 步接入会话与保存前后核对。
- `tests/test_design_discussion_incremental_checks.py`（1355 行，17 个测试函数）：只经公共接缝观察行为。
- `dist/`：按 `sh dist/build-package.sh` 重建（120 个文件），`dist/CHANGELOG.md` 文件数同步。

**场景。** 固定「齿轮谜城每日挑战」：新设计模式（三轮作答、模块结束成稿、Q4 依赖项、Q4 改口）与已有设计变更模式（多轮输入未变、外部改目标、撤销授权后重新签发、版本冲突、回读失败），均经真实 `GateService` 受控通道落到临时项目；无关模块资料（章节规格）与核心基线用于证明「只复查受影响部分」。

**验证。**

- `python3 -B tests/test_design_discussion_incremental_checks.py`：17 项全通过。覆盖：开始与读取计划（核对通过、入口定位、首轮只读 3 个必要文件的计划、无关模块列入 excluded、一次调用内 3 个文件分别计数、输入未变零重读且进入复用、只改 mtime 不得判有效、内容变化只重读该资料、新会话无可核验身份必须补读）；每轮保存前后（三轮 save 前 ok / save 后 ok、逐次 `scope()` 数与写入数都等于轮数、未改核心基线时全局重查记 skipped、`measure` 证明三轮只读 3 次文件写 3 次、写入后的记录身份已知下一轮不重读）；保存前缺口（采纳超范围 Q9 → `invalid` 且零写入、不进通道、无半写）；失效只及受影响部分（external_change 只作废被改目标、无关模块的读取与已通过检查仍可复用、断链按名称登记、证据不足单列）；撤销授权（释放实例后保存被拒、仍逐次走通道、会话授权更新、旧可复用结果作废、无关读取保留、重新签发后继续）；冲突与写入失败（外部改记录 → `conflict` 零写入、目标身份作废、只重读该记录、无关资料继续复用；回读失败 → `save_unconfirmed`、目标身份作废、相关旧结果作废、无关模块保留）；模块收敛（一次性 converge、当前模块/跨模块范围、受影响清单）；报告（日常回复单行含保存结果与检查数、检查明细在台账、只读轮不新增写入、no_new 不作废既有读取与目标身份）；保存前核对复用（同输入第二次 `reused=true` 并记台账、目标内容一变即重做、与已有决定矛盾被检出、越界目标在保存前检出且不写入）；保存后历史与重复检出（完整记录通过 + 全局跳过记 skipped、历史值丢失、决定头重复、本轮决定缺失、同步状态标注缺失）；成稿交付接入（`planned` → 经通道写入、按文件计数、逐文件经通道校验、落盘前 converge、复跑零重读）；变更接入（同上 + 收敛核对）；规格交接与删减接入（交接经通道写入并记录写入数、删减沿用同一约定）；固定场景测量依据；新设计与变更两模式的完整失效路径（模块结束一次统一核对、外部改动只重读、撤销后无关模块不重查、重新授权继续、冲突作废目标身份）；Game-Design 入口指向接缝与概念。
- 相关票 02～07 测试复跑通过：`tests/test_design_discussion_rounds.py`、`tests/test_design_discussion_decisions.py`、`tests/test_design_discussion_spec_draft.py`、`tests/test_design_discussion_full_design.py`、`tests/test_design_discussion_change_flow.py`、`tests/test_design_discussion_feature_removal.py`、`tests/test_design_discussion_metrics.py`、`tests/test_package_skill_content_design.py`。
- `python3 -m compileall plugin tests`：通过；`pyflakes`（本票改动文件）：无新增问题。
- `python3 -B tests/test_package_dist.py`、`tests/test_package_manifest.py`、`tests/test_package_provenance.py`、`tests/test_plugin_package.py`：通过（dist 与 plugin/ 逐文件一致、可复现构建）。
- 全量套件（`for t in tests/test_*.py; do python3 -B "$t"; done`）：54/54 文件全部通过。

**代码审查（/code-review，双轴，独立实施并自行执行两轴）。** Standards 轴发现并修复：`checks.py` 初版 819 行且把「状态基元、判定规则、证据报告、时机编排」混在一个文件（超仓内 600 行复查线）——按职责拆为 `checks.py`（576）/`check_state.py`（430）/`check_evidence.py`（89）；四个流程各自实现 `_converge`/`_record_write`/`_after_checks`/`_invalidate`（重复代码）——收敛为 `checks.converge_plan`/`write_item`/`after_write`/`invalidate_outcome`/`invalidate_blocked`；`checks.begin` 65 行（超 50 行线）拆出 `check_state.begin_gaps`；`before_save` 77 行拆出 `precheck_signature`/`presave_gaps`。Spec 轴发现并修复：检查结果复用此前只按依赖路径核对、不含本次输入身份，同一路径内容相同的两次不同回答会错误命中——补签名（回复 + 采纳 + 范围 + 目标版本 + 历史）并在 `reuse` 强制一致，补「同输入复用 / 目标变化即重做」用例；保存前核对未核对可写范围（`path` 未传入），现已传入记录路径并补越界用例；保存前采纳内容比对使用原始选项字母与渲染后的「字母 + 全文」直接相等而误报——改为按选项前缀/包含匹配；`no_new`（本轮无新增）此前会落入默认分支作废目标身份——改为原样透传会话并补回归；保存后回读此前不核对「历史未丢失」与「同步状态标注」——补 `history` 参数与同步状态计数；保存前发现「与已有决定矛盾」此前签名里带历史但不判定——补 `contradictions` 接入与用例。

**例外（如实单列）。** 本票未在真实宿主会话（codex 进程 + MCP 服务器连接）中实跑端到端会话；CLI 冒烟经会话内进程调用同一 `GateService` 受控路径并留实际交付文件作证，宿主连接由 `tests/test_runtime_gate*.py` 既有主题覆盖。读取计划、失效判定与复用结论消费调用方给出的结构化材料与候选清单（讨论产出的结构化结果），本票不负责从自由文本自动抽取资料清单或依赖。结论复用只适用于读取理解与已通过检查结果：写入的权限与版本校验仍由受控通道**逐次**执行（`gate_commit.commit_path`），`before_save` 在范围未知时明确写出「由受控通道逐次核对（不缓存）」而非跳过。`tests/test_design_discussion_incremental_checks.py` 为 1355 行，高于仓内「测试单文件尽量不超过 500 行」的目标（判 30/31 的软目标），与同系列票 03～07 同一取舍：会话级夹具（受控通道、临时项目、两模式、失效路径）被十七个场景共用，拆文件会引入重复夹具或额外支撑模块；本项留作判断项，不隐藏。本票只验证检查行为与重复减少，**不报告效率验收结论**（未做耗时对照），最终耗时结论归第 09 票。本票不修改 G02 产品资料、权限配置、治理文件与 `docs/agents/`；`dist/` 仅重建产物并同步文件数说明，版本保持 0.18.1。

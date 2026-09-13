# 05: 从游戏想法形成完整设计文档

**What to build:** 开发者用自然语言描述玩法后，方案设计沿用已有信息，建立覆盖地图，按依赖逐步完成约定版本的模块规格和整体衔接，最终交付能让未参与讨论者继续制作的完整设计文档。

**Blocked by:** 04 — 将模块决定整理为可交接规格。

**Status:** ready-for-agent

**Progress:** 已完成（2026-09-14 收口；接缝：`plugin/skills/game-design/coverage_map.py` 的 `build_map`/`stage_status`、`journey.py` 的 `walkthrough`/`find_contradictions`、`full_design.py` 的 `plan_delivery`/`apply_delivery`/`verify_delivery`，配合 `full_render.py`（四类交付渲染）、`full_report.py`（报告措辞）、`gate_commit.py`（受控通道单文件提交）、`full_design_cli.py`（命令行）；执行记录见 Comments）

**规格依据：**《MyGameStudio：统一游戏设计问答框架》；用户故事 33～37、41～43；验收场景 14、17、18；“新设计模式：覆盖与成稿”和“模块规格与完整文档交付”。

- [x] 从玩法片段、画面、操作、感受和提供的参考提取已知内容，整理典型游玩经历。已有项目先沿用有效资料与决定，不要求用户重新用策划术语解释。
- [x] 分清完整愿景、当前成稿版本、后续方向和范围外内容；当前范围不足以确定时只澄清必要取舍，不自动将全部愿景列入首发任务。
- [x] 维护十二领域覆盖地图：项目目标、核心吸引力、核心玩法、完整游玩过程、系统关系、成长资源、内容叙事、操作界面引导、视听、商业化发布、技术数据约束、版本验收。各项有适用性、状态及规则或缺口定位。
- [x] 不适用有理由，未知不冒充不适用，不为填满模板新增系统；地图用于查漏与推进，不一次性抛出全套问卷或每轮全文重述，也不强制每个领域新建文件。
- [x] 根据全局影响、返工风险及当前阻断关系安排模块问题组；AI 主动提出规则、数值和边界方案。区分概念说明、原型所需规格和当前版本完整设计，不按固定轮数或文档页数判定阶段完成。
- [x] 用玩家视角核对首次进入、理解目标、操作、选择、结果、结束与再次进入；检查适用的资源耗尽、重复操作、退出、解锁与失败恢复，发现跨模块矛盾后处理真实影响。
- [x] 最终提供清晰入口组织游戏设计主文档、系统规则与数值、内容与视听制作需求、版本与验证方案。沿用现有主文档和附表，不强制单文件或重造文档体系；同一现行规则只有一个权威维护位置。
- [x] 交接前确认覆盖无未解释空缺、关键流程闭合、必要规则可执行、范围与内容清楚、现行规则一致及未知有方法和影响说明。阻断交接的关键缺口仍在时报告草案或模块未完成，不因目录齐全宣称整体完成。
- [x] 需要原型或试玩的事项形成目标、方法与判定依据，注明是否阻断当前阶段；未获制作授权不自动实施，没有实际证据不报告体验或市场效果已验证。
- [x] 使用明确标注的测试回答，在固定小型游戏场景中走完整流程，核对四类交付物；植入一处资源或解锁矛盾及一处缺口，确认能够发现且不会误报完成。验收结果引用实际记录与产物。

## Comments

### 2026-09-14 执行记录（票 05）

**做了什么。** 在分支 `codex/unified-game-design-framework` 增加新设计成稿接缝，位置：

- `plugin/skills/game-design/coverage_map.py`（246 行）：公开 `DOMAINS`（十二领域，顺序与规格表一致）、`build_map`（典型游玩经历按原始意图/助手提案/信息缺口标明、沿用已有资料与决定、十二领域适用性与状态、范围四层分层、AI 规则数值边界提案保持提案身份、填充模板标记、按阻断与影响排序的推进焦点）、`stage_status`（概念说明/原型所需规格/当前版本完整设计按所需成果判定，轮数页数不参与判定）。
- `plugin/skills/game-design/journey.py`（140 行）：公开 `walkthrough`（首次进入到再次进入七步 + 资源耗尽/重复操作/退出/解锁/失败恢复五项边界检查，不适用写理由）、`find_contradictions`（资源可获得总量与解锁要求、同一解锁的前后数值不一致，给出影响与受影响领域）。
- `plugin/skills/game-design/full_design.py`（342 行）：公开 `plan_delivery`（消费覆盖地图/流程核对/模块规格位置，按交接标准逐条核对：覆盖、流程、模块、范围、规则可执行、现行规则一致、未知方法影响、阻断未决项；有缺口或矛盾返回 `incomplete`，不用默认值补齐、不产出可落盘内容）、`apply_delivery`（逐文件经受控通道提交并回读）、`verify_delivery`（回读核对四类交付物、入口定位与缺口矛盾）。
- `plugin/skills/game-design/full_render.py`（226 行）：四类交付内容的唯一渲染——游戏设计主文档（入口，引用而非重复规则）、系统规则与数值（引用模块规格现行权威位置）、内容与视听制作需求（保留既有说明并追加本轮需求，与规则位置互指）、版本与验证方案（阶段按成果判定、当前范围/后续方向/范围外、依赖、验收场景、风险、原型与试玩目标方法判定依据及是否阻断、关键未知方法与影响、未实现未验证）。
- `plugin/skills/game-design/full_report.py`（117 行）：计划/未完成/只读/完成/失败五类报告措辞，未完成逐条列出缺口与矛盾，只读明确尚未保存未同步，完成报告中实现与验证状态分开。
- `plugin/skills/game-design/gate_commit.py`（58 行）：票 03/04/05 共用的受控通道单文件提交（版本核对 → 授权核对 → 提交 → 回读），从 `decisions.py` 抽出，三个入口共用同一写入纪律。
- `plugin/skills/game-design/full_design_cli.py`（94 行）：`check|apply|verify` 命令行入口，写入与 `mgs_write` 同一条 `GateService` 受控路径。
- `plugin/skills/game-design/decisions.py`：`_commit` 改用共用 `commit_path`（`_commit_failure` 按通道真实依据报告冲突/被拒/回读失败）；`spec_draft.py` `_commit_file` 同样改用共用提交；`spec_render.py` 的 `_too_vague` 改为公开 `text_is_vague` 供票 05 复用（不重复实现形容词判定）。
- `plugin/skills/game-design/SKILL.md`：新增「完整设计成稿（新设计模式）」段（十二领域覆盖地图、范围四层、推进焦点、玩家视角核对、四类交付、阶段与证据、待验证），质询分支步骤第 5 步接入。
- `tests/test_design_discussion_full_design.py`（1017 行，9 个测试函数）：只经公共接缝观察行为。
- `dist/`：按 `sh dist/build-package.sh` 重建（108 个文件），`dist/CHANGELOG.md` 文件数同步。

**场景。** 固定小型游戏场景「齿轮谜城每日挑战」：票 02 `rounds.run_round` 组织两轮问答、票 03 真实 `GateService` 受控通道把带 `（测试回答,非真实开发者决定）` 标注的测试回答落成决定记录、票 04 `spec_draft` 落成模块规格与九类内容，再由票 05 的覆盖地图、玩家视角核对与成稿交付承接；植入一处资源/解锁矛盾（解锁需齿轮币 30 枚而可获得总量只有 20 枚）和一处缺口（操作、界面与引导领域未写清 + 每日挑战模块未达可交接），另有技术与数据约束未知（有方法与影响说明）作为「未知不等于阻断」的对照。

**验证。**

- `python3 -B tests/test_design_discussion_full_design.py`：9 项全通过。覆盖：已知内容提取与十二领域地图（领域顺序、典型经历三类来源、沿用 PROJECT 与 Q1、已有规则/不适用有理由/缺口/未知四类状态、未知不冒充不适用、推进焦点按阻断优先且不一次抛全套问卷、AI 提案不冒充已采纳、填充模板标记）；范围分层与填充模板护栏（愿景不自动进当前版本、后续方向与范围外单列、必要澄清问题、无依据新增系统标出）；阶段边界（概念/原型/当前版本按成果判定、缺成果不完成、轮数页数不参与、无成果不因目录齐全完成）；玩家视角核对与矛盾检出（七步顺序、五项检查集合、不适用有理由、植入矛盾被检出并给出数值与影响、无矛盾不误报）；完整流程四类交付物（缺口与矛盾时 `incomplete` 且零写入、处理后 `planned` 并落到 DESIGN/SPEC/CONTENT/VERSION 四个实际文件、角色与入口明确、主观验证含目标方法判定与是否阻断、无证据不报已验证、记录含标注测试回答、回读核对通过、PROJECT/TECH 不被代写）；每类阻断缺口分别检出且不误报无关模块；只读与缺同步授权边界（不写入、待同步保留、状态分档、不受影响范围声明）；CLI 冒烟（`check` 只读、缺口 apply 非零退出不写入、完整交付经真实受控通道落盘四类产物、`verify` 回读通过、未授权报告只读）；Game-Design 入口说明接缝与成稿流程。
- `python3 -B tests/test_design_discussion_decisions.py`（票 03，10 项）、`tests/test_design_discussion_spec_draft.py`（票 04，9 项）、`tests/test_design_discussion_rounds.py`（票 02）、`tests/test_design_discussion_metrics.py`（票 01）：均通过（票 03/04 在共用 `commit_path` 抽取后复跑通过）。
- `python3 -m compileall plugin tests`：通过。
- `python3 -B tests/test_package_dist.py`、`tests/test_plugin_package.py`、`tests/test_package_manifest.py`：通过（dist 与 plugin/ 逐文件一致、可复现构建）。
- 全量套件（`for t in tests/test_*.py; do python3 -B "$t"; done`）：51/51 文件全部通过。

**代码审查（/code-review，双轴，独立实施并自行执行两轴）。** Standards 轴发现并修复：票 03/04/05 各自实现同一套「版本核对 → 授权核对 → 提交 → 回读」提交逻辑，抽为 `gate_commit.commit_path`（三个入口共用；`decisions._commit` 拆出 `_commit_failure` 后 ≤60 行）；`full_design._missing` 达 68 行，按核对维度拆为 `_coverage_gaps`/`_journey_gaps`/`_module_gaps`/`_scope_gaps`/`_rule_gaps`/`_blocking_gaps`；`full_render.render_version` 达 65 行，拆出 `_stage_lines`/`_prototype_lines`/`_unknown_lines`；`coverage_map.stage_status` 的 `rounds`/`pages` 参数会被读成阶段门槛，改为显式忽略的 `**ignored`；`_template_fill` 与 `_next_focus` 共用领域表（去掉重复遍历）；`coverage` 与 PyPI 同名包冲突，接缝定名 `coverage_map.py`；`full_render._version_label` 内联导入清理。Spec 轴发现并补齐：交接标准中的「各处现行规则一致」此前没有判定，补内容需求引用规则必须有现行权威位置（`规则一致:<id>` 缺口 + 变异用例）；`blocking_qids` 声明的阻断未决项此前未进入成稿判定，补 `阻断:<qid>` 缺口与用例；`synced` 状态此前恒为 false、与「现行规则已同步」混同，改为按 `to_sync` 判定并在报告中说明本入口不代替模块规格交接同步记录状态；未知领域有方法与影响说明时不再误判为阻断（与规格「关键未知有方法和影响说明」一致）；删除 `full_design` 中未被使用的 `register_entry_fingerprints` 与 `REQUIRED_ALWAYS` 死代码。

**例外（如实单列）。** 本票未在真实宿主会话（codex 进程 + MCP 服务器连接）中实跑端到端会话；CLI 冒烟经会话内进程调用同一 `GateService` 受控路径并留实际交付文件作证，宿主连接由 `tests/test_runtime_gate*.py` 既有主题覆盖。四类交付内容由调用方提供的结构化材料渲染（讨论产出的结构化结果），本票不负责从自由文本自动抽取规则；「执行者仅凭交付记录即可独立继续」由「四类内容齐备 + 入口定位 + 缺口报告未完成」保证，而非文本解析保证。`tests/test_design_discussion_full_design.py` 为 1017 行，高于仓内「测试单文件尽量不超过 500 行」的目标（判 30/31 的软目标），与同系列票 03（834 行）、票 04（975 行）同一取舍：完整流程夹具（受控通道、临时项目、覆盖地图、四类交付）被九个场景共用，拆文件会引入重复夹具或额外支撑模块；本项留作判断项，不隐藏。本票不报告效率验收结论（未做耗时对照）；本票不修改 G02 产品资料、权限配置、治理文件与 `docs/agents/`；`dist/` 仅重建产物并同步文件数说明，版本保持 0.18.1。

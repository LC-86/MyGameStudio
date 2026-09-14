# 04: 将模块决定整理为可交接规格

**What to build:** 模块问题收敛后，方案设计将已保存的决定一次整理成后续执行者能独立理解的模块规格，并按授权同步受影响的核心基线及引用。记录、当前规则、术语、历史和验证要求有清楚分工，不因每个小答案反复重写多份资料。

**Blocked by:** 03 — 即时保存决定并恢复讨论。

**Status:** ready-for-agent

**Progress:** 已完成（2026-09-14 收口；接缝：`plugin/skills/game-design/spec_draft.py` 的 `plan_handoff`/`apply_handoff`/`verify_handoff`，配合 `spec_render.py`（九类渲染与缺口核对）、`spec_sync.py`（版本、双指纹与同步范围）、`spec_report.py`（报告措辞）、`spec_draft_cli.py`（命令行）；执行记录见 Comments）

**规格依据：**《MyGameStudio：统一游戏设计问答框架》；用户故事 19、20、23、25、40、43、55；验收场景 7、11、16、18；“模块规格与完整文档交付”的模块部分。

- [x] 收敛时汇总该模块已采纳且未同步的决定，排除候选或临时假设；保留延期事项和影响。尚有阻断当前交接的关键缺口时报告未完成，不用默认值补齐。
- [x] 模块规格按适用性说明九类内容：目的、参与对象、前提与触发、正常规则、例外边界、数值配置、玩家反馈、数据持续性及验收方式。不适用有理由，关键行为不以“合理、适中”等形容词代替。
- [x] 数值说明单位、范围、计算或取整及依据；试验值与已定值分开。验收包含初始条件、操作和预期结果；主观体验列出验证问题、方法及是否阻断当前阶段。
- [x] 沿用 Game-Spec 或等效明确文档步骤及已有文档映射，只同步实际受影响的核心基线与引用。具体规则集中维护，无关管理资料和其他模块保持不变。
- [x] 实质变化按既有版本和指纹规则处理；纯格式调整不冒充新产品要求。回读核对新旧规则、采纳来源、未决项、相关引用和同步状态，保留历史及替代关系。
- [x] 已明确术语及时维护已有术语表；普通规则不强制建立独立 ADR。只有改变成本高、缺背景会令人困惑、存在真实取舍三项同时成立时，才单独记录重要决定背景。
- [x] 设计记录、技术引用和项目管理资料按既有专业职责处理。目标或范围变化交制作统筹同步，不扩权代写；缺少授权或运行条件时明确留下待同步项。
- [x] 模块可交接不等于全游戏已完成或体验已验证；没有原型或试玩依据不报告相应验证通过，不自动启动制作。
- [x] 用固定小型模块和现有历史决定夹具验证完整规格、关键字段缺失、历史保留、未决项、纯格式修改和无关内容不变；执行者仅凭交付记录即可理解本模块要求。

## Comments

### 2026-09-14 执行记录（票 04）

**做了什么。** 在分支 `codex/unified-game-design-framework` 增加模块规格交接接缝，位置：

- `plugin/skills/game-design/spec_draft.py`（401 行）：公开 `plan_handoff`（汇总票 03 已采纳且未同步的决定 → 九类规格草稿 + 同步计划 + 缺口报告）、`apply_handoff`（逐文件经受控通道提交并回读）、`verify_handoff`（回读核对规格完整性、基线版本与双指纹、同步状态、历史未丢失），以及 `_merged_records`/`_decision_summary`（排除候选、临时假设与已替代历史）与 `_commit_file`（每文件的版本与授权逐次核对）。
- `plugin/skills/game-design/spec_render.py`（335 行）：九类内容的唯一渲染与适用性核对（设计目的/参与对象/前提与触发/正常规则/例外与边界/数值与配置/玩家反馈/数据与持续性/验收方式），不适用写理由、“合理、适中”类形容词判为缺口；另渲染决定来源与历史、未决与延期事项、未采纳内容、重要决定背景（三项条件同时成立才单列）与状态交接。
- `plugin/skills/game-design/spec_sync.py`（198 行）：只同步实际受影响的资料（模块规格、核心基线引用与版本、术语表、决定记录同步状态）；版本纪律——实质变化递增版本并登记双指纹与采纳依据，纯格式修正不触发新版本；回读核对新旧语义并在声明与实测不符时如实提示。
- `plugin/skills/game-design/spec_report.py`（144 行）：计划/未完成/只读/完成四类报告措辞，分别表达已采纳、已保存、已同步、已实现与已验证。
- `plugin/skills/game-design/spec_draft_cli.py`（94 行）：`plan|apply|verify` 命令行入口，写入与 `mgs_write` 同一条 `GateService` 受控路径。
- `plugin/skills/game-design/decision_records.py`：`parse_record` 补回读来源/建议出处/影响（供规格引用）；`apply_sync` 把已被替代决定的同步状态标为“不适用”、并把同步标记限定在本模块当前决定；改口后的决定不再继承旧要求的已同步状态（`_add_decision` 的 `sync_done` 随替代退出）。
- `plugin/skills/game-design/decisions.py`：新增 `load_gate_service`（两个命令行入口共用的唯一装载位置，去掉重复实现）；`decisions_cli.py` 改用它。
- `plugin/skills/game-design/SKILL.md`：新增「模块规格交接」段（九类内容、未完成如实报告、只同步受影响资料、版本与格式修正、术语与重要决定、统筹同步交接、状态分档），质询分支步骤第 4 步接入。
- `plugin/skills/game-spec/SKILL.md`：步骤 0 说明衔接模块规格草稿，不重复整理、不另建记录体系。
- `tests/test_design_discussion_spec_draft.py`（9 个测试函数）：只经公共接缝观察行为。
- `dist/`：按 `sh dist/build-package.sh` 重建（101 个文件），`dist/CHANGELOG.md` 文件数同步。

**场景。** 固定「齿轮谜城每日挑战」模块：首轮三题作答、第二轮补答 Q3、第三轮对 Q1 改口，另把 Q2 预标记为已同步；历史决定经票 03 的真实 `GateService` 受控通道（设计角色 + 记录目录授权 + 设计讨论用途）落到临时项目记录文件，交接用另一实例（记录目录 + 核心基线写入范围 + `spec_sync` 用途）承接，符合单写入者占用纪律。

**验证。**

- `python3 -B tests/test_design_discussion_spec_draft.py`：9 项全通过。覆盖：完整交接（汇总 Q1/Q3 待同步、Q2 已同步；九类标题齐全；已定值与候选试验值分开并各带单位/范围/计算/取整/依据；验收含初始条件、操作、预期结果；主观体验含验证问题、方法、是否阻断当前阶段；未决项与影响、旧值替代历史、来源与建议出处、未实现与未验证；只写规格+基线+术语表+决定记录，无管理资料；基线经统一接口回读为 `一致`/`v3`）、关键字段缺失（空正文、更短的空占位、“规则合理、强度适中即可”分别报 `incomplete` 且零写入；不适用带理由时视为已说明）、纯格式修改（回读判定语义一致 → 版本保持 v2、只改规格、给出声明与实测不符的提示）、只读与缺同步授权（不写入、待同步项原样保留在记录中）、历史未决与无关内容不变（改口历史与替代关系保留、其他模块与 `PROJECT`/技术设计零改动、无新术语时术语表不动）、交接状态与制作/试玩分离（状态分档、阻断当前阶段的验证问题单列）、目标或范围变化（只输出统筹同步交接，`PROJECT` 不变）、改口不继承旧同步状态（回归）、CLI 冒烟（`plan`/`apply`/`verify` 经真实受控通道；缺口以非零码报未完成；只读不写入；越界被拒且基线无半写）。
- `python3 -B tests/test_design_discussion_decisions.py`（票 03，10 项）、`tests/test_design_discussion_rounds.py`（票 02）、`tests/test_design_discussion_metrics.py`、`tests/test_package_skill_content_design.py`、`tests/test_package_dist.py`、`tests/test_plugin_package.py`：均通过。
- `python3 -m compileall plugin tests`：通过。
- 全量套件（`for t in tests/test_*.py; do python3 -B "$t"; done`）：50/50 文件全部通过。

**代码审查（/code-review，双轴，独立实施并自行执行两轴）。** Standards 轴发现并修复：`spec_draft.py` 曾达 1000 行且 `plan_handoff` 81 行（按仓内规格决策 30/31 的 500/600 与 80 行复查线拆为四个 module，最大 401 行，函数均 ≤45 行）；两个命令行入口重复实现 `_load_service`（合并为 `decisions.load_gate_service`）；`STATUS_LABELS` 与 `baseline_authorized` 未使用导入为死代码（移除）；`spec_sync.design_document` 写死「每日挑战与章节并存」的测试场景词（改为由 `meta.system_relations` 提供，缺省引用模块规格）。Spec 轴发现并修复：改口后的决定继承了旧要求的「已同步」状态，使待同步项被误判为已同步（`decision_records._add_decision` 现在让 `sync_done` 随替代退出，并补回归测试）；`apply_sync` 会把已被替代决定的同步状态从「待同步」改写成「已同步」（现标为「不适用（已被替代）」）；`apply_sync` 的模块判断曾对全部决定头生效（收窄回本模块）。

**例外（如实单列）。** 本票未在真实宿主会话（codex 进程 + MCP 服务器连接）中实跑端到端会话；CLI 冒烟经会话内进程调用同一 `GateService` 受控路径并留实际交付文件作证，宿主连接由 `tests/test_runtime_gate*.py` 既有主题覆盖。规格草稿的九类内容来自调用方提供的结构化 `sections`（讨论产出的结构化结果），本票不负责从自由文本中自动抽取规则，因此「执行者仅凭交付记录即可理解」由「九类内容齐备 + 缺口报告未完成」保证，而非由文本解析保证。`tests/test_design_discussion_spec_draft.py` 为 975 行，高于仓内「测试单文件尽量不超过 500 行」的目标（判 30/31 的软目标），与同系列票 03 的 834 行测试同一取舍：会话级夹具（受控通道、临时项目、九类内容）被九个场景共用，拆文件会引入重复夹具或额外支撑模块；本项留作判断项，不隐藏。本票不报告效率验收结论（未做耗时对照）；本票不修改 G02 产品资料、权限配置、治理文件与 `docs/agents/`；`dist/` 仅重建产物并同步文件数说明，版本保持 0.18.1。

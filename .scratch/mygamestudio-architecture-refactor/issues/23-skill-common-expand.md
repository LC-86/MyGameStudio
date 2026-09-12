# 23: 建立共同约定并迁入制作实现入口

**What to build:** 五个制作实现入口按一处维护的共同规则完成任务，同时保留代码、视听资源和构建的专业要求。

**Blocked by:** 22 集中受控远端动作与结果审计

**Status:** resolved

**Spec:** [MyGameStudio 全插件分阶段架构重构 v1](../spec.md) · User Stories 1, 56, 57, 58, 59

**Verification mapping:** 按本票所属阶段的验收集合

- [x] 共同执行规则、受控写入协议和结果字段的权威位置清晰可直接读取，旧入口在迁移期间继续可用。
- [x] 完整迁入 Game-Implement、Game-Code、Game-Art、Game-Audio、Game-Build 五个入口，保留显式调用、输入输出、能力缺口、资源范围和人工待验收语义。
- [x] 每个入口均可沿其真实专业流程取得必要规则，不需要从多处拼接缺失步骤；共同引用不改变执行角色或授权。
- [x] 先用原场景核对结果及证据要求，再检查文本引用、来源与适配指纹；实际模型行为未核验时不宣称仅因文案通过便完成真实验收。
- [x] 应用已确认的文档编写方法，固定上游方法和许可证保持；未迁入的其他入口继续使用旧规则。

**依赖理由：** 依赖 22 完成受控行为与结果表达，随后依据已确认的阶段验收顺序整理共同说明。

## 执行与验证约定

本票已正式发布；实施按对应任务授权执行。沿现有 interface 验证本票行为；保持外部用法、持久化格式、权限与恢复语义，只有明确列出的 R1 属行为修正。每票在新的执行上下文中按实际前置成果接手；产品内容变化时同步相关包与来源检查，记录净行数、必要操作量和未验证限制。

同一共享文件只由一名执行者修改。测试和独立规范/规格评审针对本票实际版本；基线不可被历史结果替代。提交、推送、标签、真实远端写入、日常安装和发布分别沿明确授权执行。

## Comments

用户已确认 26 票拆分及其依赖安排；本票按确认稿发布，未启动实施。

### 执行记录（2026-09-12，阶段 6 首票/核心票）

- 前基点 SHA：`850dc7441ba13c062b5705e2fc471652b8be794c`。
- 三处唯一权威：`internal/contracts/common.md`《共同执行规则(唯一权威)》(原「执行与完成」升级并标注唯一维护位置)、`internal/protocols/gate-protocol.md`《越界探针(边界核对)》(新增,收拢各入口重复的边界核对规程)、《工作结果模板》`templates/work/result.md`(结果字段唯一权威,内容未改)。共同合同新增《共同规则的权威位置》一节明示三处。
- 迁入五入口(Game-Implement/Code/Art/Audio/Build)：包内依据列表把三处标为权威并加"只补充专业差异、不内联共同规程"声明；结果记录步骤改为引用模板《结果字段》并补 `expected_sha256`；待验收步骤指向共同执行规则第 4-5 步；边界核对步骤改引协议《越界探针》并保留原探针清单；边界一节把凭据纪律改引协议《执行凭据》并保留"不自动提交/推送/发布"、"新增命令执行路径保持受控"、"失败或中断保存实际进度和缺口"等专业约束。显式触发、输入输出、能力缺口、资源范围、人工待验收语义全部保留（`test_package_skill_content_*` 的关键词检查零回归）。
- 引用闭包：新增 `tests/test_package_manifest.py::test_skill_authority_references`——三处权威文件带可定位小节、五入口同时引用三处且解析到实文件（不悬空）、入口指向权威小节、未迁入九入口 SKILL.md 仍在（新旧并存）。已接入 `test_plugin_package` 聚合主题。
- 来源与指纹保持：上游 `production.md`、`common.md` 适配版权限与许可未动；`provenance/fingerprints.json` 仅更新 `common.md`/`gate-protocol.md` 两处指纹与 source 说明，`manifest.md` 对应两行更新；`mattpocock-skills` 许可证与固定上游方法(6 个 internal/methods)未改。
- 检查结果：五套聚合器全绿（`test_plugin_package`+四套 `test_{runtime_gate,runtime_boundaries,records_backend,github_backend}`，退出码 0）；`run_baseline.sh` 五套 PASS（all_existing_checks_green=True），跑后 `git checkout --` 恢复冻结产物；`dist/build-package.sh` 重建 90 文件包。
- 净行数（物理行）：plugin 生产 +23（internal +17：common +8、协议 +9；skills +6：implement +1、code +1、art +1、audio +1、build +2）；tests +60 −1（新增闭包主题）；dist 交付包重生成（`plugin/` 内容变化）。权威文件职责单一，入口文件未膨胀（五入口 58-69 行）。
- 未验证限制：本票为说明/引用重构，未执行真实模型轮；文案通过不等于实际模型行为已验收（spec「阶段 6 不能只靠文本缩短判断完成」）。真实模型行为、安装与发布留待票 26 及另行授权。未迁入的九个入口继续使用旧规则（票 24 处理）。

### 复审修复记录（第一轮）

独立复审发现五处问题，逐条处理如下；修复提交见本轮 commit。

- **F1【残余复制，已改】**删除 game-implement:52、game-art:55、game-audio:56、game-build:55 逐字复制 common.md:39 的「未参与者可独立读取…不依赖对话记忆」句，改为引用[共同合同]《共同执行规则》的该标准（`game-code` 原有干净写法为参照）；删除五入口「边界核对」步骤内联的协议《越界探针》纪律句（原样记录…不尝试绕过），改为「记录与未要求时的处理均按该节纪律」。逐条对照权威处确有对应文本：common.md:39 保有完整「未参与者」句；gate-protocol.md:71（《越界探针》）保有「原样记录…不尝试绕过、不换路径、不换工具重试」「未要求核对时报告中写『本次未执行』」。
- **F2【锚点名不副实，已改】**采用修法 a：在 `templates/work/result.md` 既有字段列表前加《结果字段》小节标题（字段内容与结构未改），使《结果字段》锚点名副其实，五入口引用不动。五入口把「不自动提交/推送/发布」外部动作边界由误指《共同执行规则》改为 common.md 实际承载该文的《写入与保障》（common.md:45）；并把包内依据行的「外部动作授权」一并标入《写入与保障》。
- **F3【闭包测试假绿，已改】**`test_skill_authority_references` 增强：对《共同执行规则》《写入与保障》（common.md）、《越界探针》（gate-protocol.md）、《结果字段》（result.md）断言目标文件存在对应标题文本（子串到标题行），并新增五入口须指向《写入与保障》《越界探针》；docstring 改为如实描述四项校验。`/tmp` 副本三次故意错锚点（改坏《越界探针》标题、去掉《结果字段》标题、去掉《写入与保障》标题）均按预期变红，未污染仓库。
- **F4【expected_sha256 位置，已做】**game-code:35、game-audio:38、game-build:37 的「结果记录」步骤把 `(经 mgs_write 携带 expected_sha256` 改为 `(经 mgs_write 受控写入`，消除「结果记录步骤携带更新哈希」的语义混淆（版本校验语义留待写入步骤/协议）；`expected_sha256` 仍在文件内出现（写入步骤与检查关键词满足），`skill_content` 关键词零回归。game-art、game-implement 的结果步骤本无该串，未动。
- **F5【行数笔误，已改】**工单执行记录「五入口 60-69 行」更正为 58-69（game-code 实为 58 行）。

验证：`test_plugin_package`（含 skill_content/provenance/新闭包检查）与四套 `test_{runtime_gate,runtime_boundaries,records_backend,github_backend}` 全绿（退出码 0）；`dist/build-package.sh` 重建 90 文件包；指纹同步 `templates/work/result.md`（fingerprints.json + manifest.md）。`dist/verify-reproducible.sh` 需在提交后对 `git archive HEAD` 复跑（其比对基准是已提交内容）。


# Issue #92 行为证据：游戏设计与文档工作流迁移

本文件记录 Issue #92 在**两来源组合**（本仓库技能 + 官方外部共同方法，不含随包副本）下的真实会话结果。检查的通过、失败与未运行状态汇总在 [验证状态](../validation-v3.md) 第 11 节；本文件只放现场、轨迹与核对依据。

## 现场

| 项 | 值 |
|---|---|
| 日期 | 2026-09-27 |
| 宿主 | DeepSeek Harness（DSH）0.1.7-rc.2；macOS 27.0（Darwin 27.0.0 arm64） |
| 模型 | 由主会话派生的独立子代理上下文，派发说明不含本次改动的任何对话；子代理使用会话默认子代理路由（`deepseek/deepseek-v4.1-flash`），本轮未逐个记录每个子代理的实际模型标识 |
| 技能库版本 | 工作树 `4e1c7ef` + 本票未提交改动（5 个技能正文、测试与脚本）；夹具内 7 个组技能副本与工作树逐文件 SHA-256 相同 |
| `skills` CLI | 1.7.0（Node v24.19.0），命令 `--agent universal --copy -y` |
| 夹具脚本 | `METHOD_SOURCE=official bash scripts/behavior-fixtures.sh /tmp/mgs-issue92 M92-routing M92-partial-save NOMETHOD-routing` |
| 项目 | 代表性小游戏「潮汐潮池」：`AGENTS.md`、`docs/agents/` 约定、现行 GDD、进行中 spec、术语表、`src/game.js`、两张本地任务票、真实 git 历史 |
| 安装结果 | 每个项目 `.agents/skills/` 内 20 项 `-gamestudio` 技能 + `writing-for-agents`（官方源），共 21 项 |
| 证据位置 | `/tmp/mgs-issue92/`（临时目录，随系统清理失效） |

组合安装的来源事实（夹具 `_seed/skills-lock.json`）：

| 项 | 实际值 |
|---|---|
| `writing-for-agents` 锁来源 | `mattpocock/skills`，`computedHash 95da47fc97af…` |
| 官方正文指纹 | `SKILL.md` SHA-256 `551adca942227b44…`；含 `SKILL-MECHANICS.md` |
| 本仓库随包副本指纹 | `SKILL.md` SHA-256 `5b3f3608fbb190b1…` |
| 随包打包文件 | 项目内共同方法目录**没有** `SOURCE.md` / `SHA256SUMS` |
| GameStudio 技能锁来源 | 本仓库 checkout，共 20 条 |

`NOMETHOD-routing` 项目的 `.agents/skills/` 只有 20 项 `-gamestudio` 技能，**没有** `writing-for-agents`。

## 场景结果

| 场景 | 输入要点 | 必须观察到的结果 | 结果 |
|---|---|---|---|
| M92-routing | 协作模式下同一句回答含长期规则、试验值与本次交付范围 | GDD、spec 与术语表归属正确；试验值不升级；取得外部方法与专属参考 | 通过 |
| M92-partial-save | GDD 可写、`docs/specs/` 只读时写入长期规则与本次范围 | 一份成功一份失败分别报告，不绕过权限、不伪造成功 | 通过 |
| NOMETHOD-routing | 同一句回答，但项目内缺外部共同方法 | 准确说明缺口与受影响内容，只继续不受影响部分，不模仿缺失方法 | 通过 |

### M92-routing

- **实际取得**（接收方报告的完整路径，均在项目内 `.agents/skills/`）：`writing-for-agents/SKILL.md`；`docs-gamestudio/SKILL.md` + `references/document-routing.md` + `references/semantic-fidelity.md`；`gdd-gamestudio/SKILL.md` + `references/gdd-writing.md`；`spec-gamestudio/SKILL.md` + `references/spec-writing.md`；`domain-gamestudio/SKILL.md` + `references/CONTEXT-FORMAT.md` + `references/ADR-FORMAT.md`；`grilling-gamestudio/SKILL.md` + `references/game-questioning.md`；`grill-gamestudio-docs/SKILL.md`。宿主会话目录里的同名技能未被使用。
- **主代理独立核对**：`git status` 只有 `docs/design/GDD.md` 与 `docs/specs/2026-09-10-first-level.md` 两个文件被改；`CONTEXT.md` 零改动；没有新建文件、没有任务票、没有提交。
- **GDD**：「已采纳规则」新增「死亡结束当前一局（可早于 3 波结束）；永久解锁跨局保留。」；原未决「死亡惩罚强度」改写为「死亡结束本局后的得分口径：候选 A／候选 B；『死亡结束本局』已定，此项尚未采纳」，两个候选保持未采纳身份；新增未决「死亡的触发条件（什么情况算死亡）尚未定义」；连击倍率仍是「未决·试验值」，`5x` → `7x（先试手感）`，保留「未验证」。
- **spec**：状态行补「本次只做第一关结算面板」并写明依据指向 GDD 已采纳规则；新增「本次范围」「行为与交付要求（本次）」「本次不做」「未决项」；验证新增一条「结算面板以纯文本占位可读即通过，不检查美术表现」；原「交付」「已实现 / 未实现 / 验证」条目保留。
- **术语表归属**：没有把规则与交付范围塞进 `CONTEXT.md`，理由是既有「重开」「永久解锁」条目已覆盖本轮含义，新增内容属于规则层。

### M92-partial-save

- **实际取得**：`writing-for-agents/SKILL.md` + `SKILL-MECHANICS.md`；`docs-gamestudio/SKILL.md` + `references/document-routing.md` + `references/semantic-fidelity.md`；`gdd-gamestudio/SKILL.md` + `references/gdd-writing.md`；`spec-gamestudio/SKILL.md` + `references/spec-writing.md`；`domain-gamestudio/SKILL.md` + `references/CONTEXT-FORMAT.md`；`tasks-gamestudio/SKILL.md`（用于判断是否顺带建票）。
- **主代理独立核对**：`git status` 只有 ` M docs/design/GDD.md`（+2/−1）；`docs/specs/2026-09-10-first-level.md` 的权限位仍为 `-r--r--r--`、目录仍为 `dr-xr-xr-x`，文件大小 582、SHA-256 `7eb40fe5602146a9…` 与派发前一致，没有半截写入或替身文件；`CONTEXT.md` 零改动。
- **产物**：GDD「已采纳规则」新增死亡结束本局与永久解锁保留；原本决的得分候选 A/B 保留未采纳身份并补明它只指本局得分。spec 那条本次范围**未能落盘**。
- **失败报告**：给出实际错误原文 `bash: docs/specs/2026-09-10-first-level.md: Permission denied (exit=1)` 与目录探针的 `Permission denied`；说明写入前后 size 与 SHA-256 未变；按用户约束没有 `chmod`、没有绕过权限、没有另建平行 spec；明确列为阻塞并给出待落盘 diff 与解除条件。

### NOMETHOD-routing

- **实际取得**：项目内 `docs-gamestudio/SKILL.md` + 两个 references；`gdd-gamestudio/SKILL.md` + `references/gdd-writing.md`；`spec-gamestudio/SKILL.md` + `references/spec-writing.md`；`grilling-gamestudio/SKILL.md` + `references/game-questioning.md`；`domain-gamestudio/SKILL.md` + `references/CONTEXT-FORMAT.md`；另用一条命令打印全部 21 个 `SKILL.md` 的 frontmatter 用于路由判断。它同时列出了项目内确实没有 `writing-for-agents`。
- **主代理独立核对**：`git status` 除原有的未跟踪 `.agents/` 外没有任何改动；没有安装、没有新建文件。
- **缺口说明**：接收方引用 `docs-gamestudio/SKILL.md:22-24`（该行确为「共同方法按名称取得」一节）与 gdd/spec/domain 的同类要求，说明共同方法缺失、受影响的是 GDD/spec/术语正文的写入，并列出只存在于对话中的待保存内容与两条真实冲突（死亡触发条件未定义、spec 验证项与收敛范围不匹配）。
- **继续的部分**：路由判断、讨论本身、待保存内容的整理、四条按分轮问答格式提出的下一个问题；没有凭记忆补写正文，也没有宣称完成。

## 保真逐项核对（主代理对照夹具原始输入与 diff）

| 项目 | 原始输入 | 产物实际值 | 判定 |
|---|---|---|---|
| 数值 | 前摇 `0.4 秒`、潮水 `12 秒`、`3 波`、连击 `7x`、「60 到 90 秒一局」 | 未修改处原样保留；试验槽位 `5x` → `7x` 并保留「未验证」 | 保真 |
| 单位与量词 | 秒、波、倍率 | 保留原单位与量词 | 保真 |
| 条件 | 低潮「前 4 秒」、死亡「结束当前一局」（新增，可早于 3 波结束） | 条件与先后关系明确写出 | 保真 |
| 例外与排除项 | 本次「不做美术，纯文本占位」 | spec 新增「本次不做」与「占位不当作最终表现方向」 | 保真 |
| 责任 | spec 原有「Agent」与「开发者」两类验收 | 两类保留，新增一条 Agent 验收；人工试玩项未被替代 | 保真 |
| 确认状态 | 长期规则=已确认；候选 A/B=未采纳；`7x`=先试手感 | 分别落为「已采纳规则」「尚未采纳」「未决·试验值、未验证」，没有互相升级或合并 | 保真 |
| 原始证据 | 用户原话与项目既有文件 | 依据行指向 GDD 已采纳规则；冲突与未决如实列出，没有把占位写成已实现或已验证 | 保真 |

通用方法单独加载不能代替本组验收：本轮三个场景都同时读取了项目内的专业技能与 `docs-gamestudio` 专属参考（路由、保真），产物中的归属与身份判断来自这些参考，不是只靠通用写作方法。

## 未运行与限制

- 六个宿主内的实际技能发现与自动加载、`writing-for-agents` 在真实宿主中按名称被选中、用户级与项目级同名副本冲突时的实际加载版本：**not-run**。本票只用隔离项目与干净子代理核对取得方式与产物，不外推到其他宿主。
- 本机用户范围也装有同名 `writing-for-agents`；三个场景的派发说明都把范围限定在项目 `.agents/skills/`，因此 NOMETHOD-routing 验证的是「该组合范围内缺失时」的行为，不是「全机缺失」。
- 每个场景只运行一次，单次结果不构成稳定性证明；重复会话与不触发场景未运行。
- 子代理自述的读取路径由主代理核对到「与产物和引用的行号一致」的程度，宿主未提供逐次工具调用日志；未运行的项保持未运行。
- 三个场景均未在项目里运行自动化检查（夹具项目没有测试入口），本轮检查都在技能库一侧运行。

## 附录：产物实际差异（供 `/tmp` 清理后复核）

以下 diff 抄自夹具项目的 `git diff`，与上文判定同时采集。

`M92-routing/docs/design/GDD.md`：

```diff
@@ -10,7 +10,9 @@
 - 俯冲有 0.4 秒前摇，前摇中不可取消。
 - 潮水周期 12 秒，前 4 秒为低潮（猎物暴露窗口翻倍）。
 - 一局固定 3 波，每波结束时潮位重置。
+- 死亡结束当前一局（可早于 3 波结束）；永久解锁跨局保留。
 
 ## 未决
-- 死亡惩罚强度：候选 A 清空本局得分，候选 B 保留一半。尚未采纳。
-- 连击倍率上限：试验值 5x，未验证。
+- 死亡的触发条件（什么情况算死亡）尚未定义。
+- 死亡结束本局后的得分口径：候选 A 清空本局得分，候选 B 保留一半；「死亡结束本局」已定，此项尚未采纳。
+- 连击倍率上限：试验值改为 7x（先试手感），未验证。
```

`M92-routing/docs/specs/2026-09-10-first-level.md`（节选新增部分）：

```diff
-状态：进行中（部分已实现）
+状态：进行中（部分已实现）。本次只做第一关结算面板。
+依据：docs/design/GDD.md「已采纳规则」（俯冲前摇 0.4 秒、潮水周期 12 秒、一局 3 波、死亡结束本局）。
+
+## 本次范围
+- 只做第一关的结算面板，即本局结束后的结果界面；「交付」其余条目仍然有效，只是不在本次推进。
+- 结算面板用纯文本占位即可，不做美术；占位文本是本次有效交付，不当作最终表现方向。
+
+## 行为与交付要求（本次）
+- 本局结束时进入结算并显示结算面板；完成 3 波是已实现的本局结束路径。
+- 从结算重开后回到第一波，永久解锁保留（面板内是否提供重开入口见「未决项」）。
...
+- [ ] Agent：结算面板以纯文本占位可读即通过，不检查美术表现。
+
+## 本次不做
+- 结算面板的美术与最终表现。
+- 第三波猎物生成节奏（见 tasks/02-third-wave/task.md）。
+
+## 未决项
+- 本次结算面板是否接死亡路径：死亡的触发条件尚未定义（GDD 未决）。
+- 死亡结束本局时的得分口径：GDD 候选 A／候选 B，尚未采纳。
+- 结算面板的显示内容，以及是否在面板内提供重开入口。
```

`M92-partial-save/docs/design/GDD.md`：

```diff
@@ -10,7 +10,8 @@
 - 俯冲有 0.4 秒前摇，前摇中不可取消。
 - 潮水周期 12 秒，前 4 秒为低潮（猎物暴露窗口翻倍）。
 - 一局固定 3 波，每波结束时潮位重置。
+- 死亡结束当前一局，永久解锁保留：本局就此结束，不恢复本局继续游玩；永久解锁跨局保留，死亡不清除。本局临时能力与局内状态不保留。
 
 ## 未决
-- 死亡惩罚强度：候选 A 清空本局得分，候选 B 保留一半。尚未采纳。
+- 死亡惩罚强度：指本局得分怎样处理，候选 A 清空本局得分，候选 B 保留一半。尚未采纳；不含永久解锁，永久解锁按已采纳规则保留。
```

`NOMETHOD-routing`：`git status` 除原有的未跟踪 `.agents/` 外无改动；没有产物差异可抄。

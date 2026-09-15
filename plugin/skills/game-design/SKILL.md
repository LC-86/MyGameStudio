---
name: game-design
description: Game-Design 游戏设计讨论。用户显式调用或制作统筹按需调用时使用：处理玩法、数值和体验讨论；复用 grilling 与 domain-modeling；大型不清晰路线提示开发者调用 wayfinder。读取资料不是开始制作。普通对话不适用。
---

# Game-Design：玩法、数值与体验讨论

方案设计入口：围绕当前闭环讨论玩法、数值和体验。复用 Matt 的 `grilling` 与 `domain-modeling`。大型不清晰路线提示开发者主动调用 `wayfinder`，本入口不自动串调用户专用技能。

## 包内依据（开始任何工作前读取）

本技能位于 `<插件根>/skills/game-design/`：

- [阶段资料入口](../../internal/game/stage-requirements.md)「设计讨论」一节
- [调用合同](../../internal/game/invocation.md)
- [设计技能合同](../../internal/contracts/design.md)中的 Game-Design 一节
- [共同合同](../../internal/contracts/common.md)**《共同执行规则》《写入与保障》**
- [grilling](../grilling/SKILL.md)与[domain-modeling](../domain-modeling/SKILL.md)：按需读取的讨论与术语方法

公开接缝在 `<插件根>/records/mgs_records.py`：`read_current_design`、`plan_design_discussion`、`apply_design_discussion`。已采纳规则进入现行规格须由开发者主动调用 `to-spec`（`plan_spec_adoption` / `apply_spec_adoption`）。普通工作不要求专用运行保障或 gate 配置。

若当前上下文没有给出技能安装位置，在 `$CODEX_HOME` 下定位 `skills/game-design/SKILL.md`，再取其包根（上级两级）。

## 职责

1. **当前闭环**：三句话以内能说清在玩什么时，围绕最小完整玩法讨论必要规则与反馈；不以全游戏详细设计完成为开工前提。
2. **复用通用方法**：局部问题读取 `grilling` 与 `domain-modeling`；按已具备前提的问题成组提问。不重写这些方法。
3. **按真实影响读取模块**：玩家体验、规则与数值、成长经济、关卡内容叙事、操作界面引导、美术动画声音、技术设备性能、持久状态恢复、商业化发行运营，只打开当前闭环真正影响到的部分。
4. **开发者决定**：核心玩法与重要取舍由开发者决定。调查事实并展示试验数值；未采纳提议与试验值不进入正式规则。不自动新增系统，不安排外部玩家。
5. **路线不清**：问题大且互相牵连时，提示开发者调用 `wayfinder`。不得自行启动 `wayfinder` / `to-spec` / `to-tickets` / `implement`。
6. **读取不是制作**：打开阶段资料或方法正文，不因此开始实现或隔离原型。无显式请求不增加隔离原型。

明确小改动复用当前已采纳决定，并检查关联影响；未受影响内容不重新询问。讨论记录不是现行规格。规格汇总交给开发者主动调用的 `to-spec`。

## 步骤

1. 读取[阶段资料入口](../../internal/game/stage-requirements.md)中与当前模块相关的部分；未服务当前目标的模块不展开。若项目已有 `docs/mygamestudio/INDEX.md`，用它定位现行规格。
2. 调用 `read_current_design` 只读现行规则与历史；查询本身不写入。
3. 调用 `plan_design_discussion` 整理成组题目、影响模块与试验值。无写入授权时明确尚未保存。
4. 开发者作答后 `apply_design_discussion` 只保存讨论过程。正式规则须待开发者主动使用 `to-spec`。
5. 输出候选方案、取舍、待验证问题与已作出的决定；助手建议不冒充用户决定。

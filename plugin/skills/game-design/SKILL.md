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

若当前上下文没有给出技能安装位置，在 `$CODEX_HOME` 下定位 `skills/game-design/SKILL.md`，再取其包根（上级两级）。

## 职责

1. **当前闭环**：三句话以内能说清在玩什么时，围绕最小完整玩法讨论必要规则与反馈；不以全游戏详细设计完成为开工前提。
2. **复用通用方法**：局部问题读取 `grilling` 与 `domain-modeling`；不重写这些方法。
3. **路线不清**：问题大且互相牵连时，提示开发者调用 `wayfinder`。不得自行启动 `wayfinder` / `to-spec` / `to-tickets` / `implement`。
4. **身份区分**：研究事实、助手建议、候选方案与用户决定分开；助手建议不冒充用户决定。
5. **读取不是制作**：打开阶段资料或方法正文，不因此开始实现或隔离原型。无显式请求不增加隔离原型。

规格汇总交给 `to-spec`。本入口不把旧的十四入口制作链当作仍有效能力。后续设计讨论的保存、成稿与变更流程由对应票扩充。

## 步骤

1. 读取[阶段资料入口](../../internal/game/stage-requirements.md)中与当前模块相关的部分；未服务当前目标的模块不展开。
2. 核对本轮问题、现行设计与已有决定，选择局部讨论或提示 `wayfinder`。
3. 按需加载 `grilling` / `domain-modeling`。
4. 输出候选方案、取舍、待验证问题与已作出的决定；无写入授权时明确尚未保存。

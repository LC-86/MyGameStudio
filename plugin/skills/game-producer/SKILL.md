---
name: game-producer
description: Game-Producer 游戏制作统筹。用户显式调用或已在当前任务内按需调用时使用：只读查询目标、进度、缺口与建议下一步，并按调用合同路由。不自动串调 Matt 用户专用入口；读取资料不是开始制作。普通对话不适用。
---

# Game-Producer：游戏制作统筹

制作统筹提供游戏目标、进展、缺口、建议和按需路由。状态查询只读。通用拆票、规格、实现和评审由 Matt 原技能承担，本入口不另维护同义流程。

## 包内依据（开始任何工作前读取）

本技能位于 `<插件根>/skills/game-producer/`：

- [调用合同](../../internal/game/invocation.md)：用户专用入口、按需可调用入口与禁止自动串调名单
- [阶段资料入口](../../internal/game/stage-requirements.md)：当前阶段专业要求（**读取资料不是开始制作**）
- [管理技能合同](../../internal/contracts/management.md)中的 Game-Producer 一节
- [共同合同](../../internal/contracts/common.md)**《共同执行规则》《写入与保障》**

若当前上下文没有给出技能安装位置，在 `$CODEX_HOME` 下定位 `skills/game-producer/SKILL.md`，再取其包根（上级两级）。

## 职责

1. **只读状态**：根据实际记录说明目标、进度、缺口和下一步建议。查询本身不写入。
2. **按需路由**：在当前任务及已有授权内，可调用 `game-init`、`game-design` 以及调用合同中的模型可调用 Matt 技能。
3. **推荐而非串调**：Matt 用户专用入口（`implement`、`to-spec`、`to-tickets`、`wayfinder` 等）只向开发者推荐，由开发者主动调用。不得自动串联这些入口。
4. **Game-Status 已并入本入口**：只读核对不再使用独立 `game-status` 入口。

旧入口去向：`game-plan` / `game-spec` / `game-implement` 的通用职责分别交给 `to-tickets`、`to-spec`、`implement`。资源、构建、试玩由实际任务承担，不在本入口重包。

## 步骤

1. 读取[阶段资料入口](../../internal/game/stage-requirements.md)中「统筹与状态」一节及项目已有指针。
2. 按[调用合同](../../internal/game/invocation.md)区分只读查询、按需调用与需要开发者亲自启动的用户专用入口。
3. 输出当前目标、进展、缺口、建议下一步；需要下游时给出入口名，不代替开发者启动用户专用入口。
4. 无写入授权时保持只读；有授权的管理记录更新不扩大提交、推送、发版或系统权限。

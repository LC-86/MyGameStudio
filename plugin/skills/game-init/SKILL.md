---
name: game-init
description: Game-Init 游戏项目接入。用户显式调用或制作统筹按需调用时使用：分析已有游戏并补齐必要游戏接入资料。通用 tracker、标签与领域文档交给 setup-matt-pocock-skills。读取资料不是开始制作。普通对话不适用。
---

# Game-Init：游戏项目接入

分析已有项目并补齐必要游戏接入资料。选择本地 Markdown 后，本入口能接入新旧项目并维护现行任务记录。通用分流标签与领域文档布局交给上游 `setup-matt-pocock-skills`，本入口不另维护同义通用流程。GitHub Issues 接入见后续票，不要在本入口提前做。

## 包内依据（开始任何工作前读取）

本技能位于 `<插件根>/skills/game-init/`：

- [阶段资料入口](../../internal/game/stage-requirements.md)「项目接入」一节
- [调用合同](../../internal/game/invocation.md)
- [管理技能合同](../../internal/contracts/management.md)中的 Game-Init 一节
- [共同合同](../../internal/contracts/common.md)**《共同执行规则》《写入与保障》**
- [协作配置合同](../../internal/contracts/project-configuration.md)
- [初始化流程](../../internal/proposals/project-onboarding.md)
- [项目目录模板](../../internal/proposals/project-layout.md)与[模板入口](../../templates/README.md)

公开接缝在 `<插件根>/records/mgs_records.py`：`analyze_project`、`plan_local_onboarding`、`apply_local_onboarding`、`create_task` 及任务维护入口。普通本地工作不要求专用运行保障或 gate 配置。

若当前上下文没有给出技能安装位置，在 `$CODEX_HOME` 下定位 `skills/game-init/SKILL.md`，再取其包根（上级两级）。

## 职责

1. **已有项目先只读分析**：区分实际行为、已采纳要求、历史内容、缺口、冲突与未验证事实；复用仍有效的设计、工程和资源。
2. **补齐游戏接入资料**：提供指向[阶段资料入口](../../internal/game/stage-requirements.md)的短指针，并映射现有文档实际位置。不把分析当成已经开始制作。
3. **选择本地 Markdown 为唯一现行 tracker**：规格、任务、结果各有唯一位置。不双向同步，也不另起第二套账本。
4. **通用配置不代做**：Matt 侧分流标签与领域文档布局提示开发者调用 `setup-matt-pocock-skills`。
5. **不做规格拆单**：拆票属于 `to-tickets`。

## 步骤

1. 确定目标项目根。缺明确目标时先问清，不改其他目录。
2. 调用 `analyze_project` 只读探查并归入六类现状；原项目分析阶段保持未修改。
3. 调用 `plan_local_onboarding` 列出接入清单：复用 / 新增 / 待决定，含阶段资料指针落点。
4. 取得确认前不写入。确认后 `apply_local_onboarding(..., confirmed=True)` 只应用清单内条目，不覆盖有效旧资料，不扩大提交、推送或外部授权。
5. 用 `create_task` / `update_task` / `claim_task` / `close_task` 维护任务；重复创建先回读收养。发现重叠改动时暂停覆盖并保留双方成果。
6. 取消或中断后保存已有成果，重读当前来源再只补缺项；不恢复已撤销动作。
7. 报告文档接入就绪与仍缺项；不把未执行的通用 setup 写成已完成。重复接入无缺口时不得改已有内容。

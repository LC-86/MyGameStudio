# 常用工作流

下面是工作流地图，不是每项小改动都必须执行的长流水线。
`game-producer` 可以在过程中只读查询，不代表你授权它自动串调所有阶段。

```text
安装完整插件 → 确认技能发现
        ↓
setup-matt-pocock-skills（你主动调用）
        ↓
game-init：分析项目 → 接入清单 → 确认后应用
        ↓
game-design：按需要讨论当前最小玩法闭环
        ↓
to-spec（你主动调用）
        ↓
to-tickets（范围较大时，由你主动调用）
        ↓
implement（你主动调用）
        ↓
检查与实际运行 / 试玩 → 记录结果 → 决定后续修改
```

调用文案是对 Agent 的说明。客户端需要先选技能时，选对应的已安装技能。

## 新项目或尚未接入的项目

1. `setup-matt-pocock-skills`：只配置**这个游戏仓库**的 tracker / 标签 / 领域文档。
2. `game-init`：先只读分析，再确认写入。
3. 需要时 `game-design` 讨论当前闭环。
4. 你调用 `to-spec` / `to-tickets` / `implement`。

## 已有游戏修改

见 [接入与修改已有游戏](existing-projects.md)。小改动可以在已采纳规则上直接讨论影响，不必重走整条地图。

## 进度查询

```text
请使用 MyGameStudio 的 game-producer，只读检查当前项目。
根据真实记录说明当前目标、已完成和待完成任务、阻塞项以及下一步建议。
不要修改记录，也不要自动启动实现。
```

## 组合使用（规格 → 任务 → 实现 → 评审）

这些是 Matt 用户专用入口。制作统筹可以**推荐**它们，但必须由你启动。

1. `to-spec`：把已经讨论并采纳的内容整理成规格，不要现场再采访一遍。
2. `to-tickets`：范围较大时拆成可独立检查的任务，并声明阻塞关系。
3. `implement`：按任务实现。无提交授权时保留未提交成果。
4. `code-review`：对完整待审成果做 Standards 与 Spec 两轴评审；空的已提交差异不是完整通过。

人读说明：[setup](../skills/engineering/setup-matt-pocock-skills.md)、[to-spec](../skills/engineering/to-spec.md)、[to-tickets](../skills/engineering/to-tickets.md)、[implement](../skills/engineering/implement.md)、[code-review](../skills/engineering/code-review.md)。

# 常用工作流

这些是实际组合，不是每项小改动都要走完的流水线。明确的小任务可以直接实现，不必先补规格和拆票。

三条贯穿所有组合的事实：

- **推荐与开始是两个动作。**`ask-gamestudio` 与 `handoff-gamestudio` 只给建议和指令文本，不代替你启动下一个入口。
- **用户入口不自动串调。**8 项用户入口各自完成即停；13 项按需方法由 Agent 在当前任务与授权适用时组合，你也可以直接点名。
- **`writing-for-agents` 是共同写作方法。**正式资料、结论、交接和委派说明按它的方法表达；它负责通用表达与语义保真。`docs-gamestudio` 只提供游戏文档归属和增量协作，不决定内容，也不审批写作。

这条区分由三层调用控制承担：Claude Code、Grok Build、DSH 由 frontmatter 的 `disable-model-invocation: true` 强制，Codex 由技能目录内的 `agents/openai.yaml` 强制；ZCode、Qoder 没有宿主级开关，仍靠描述与正文里的指令层约定。见 [当前能力与限制](../reference/capabilities.md)。

## 一次设计讨论

```text
请使用 grill-gamestudio-docs，讨论把体力系统改成随时间恢复。
分轮问清目标、影响与取舍；已确认的决定按用途更新术语、GDD 或本次规格。
这一轮不要开始编码，也不要发布任务。
```

组合：`grilling-gamestudio` 提问，`domain-gamestudio` 澄清并保存必要术语，`gdd-gamestudio` 更新整体设计，`spec-gamestudio` 整理本次工作规格。只想要纯访谈不落盘时用 `grill-gamestudio`。

讨论记录不是现行规格；采纳与写入范围由你确认。

## 把已确认的工作变成票

```text
请使用 tasks-gamestudio，把已确认的体力系统改造拆成任务。
按完整小成果拆，写明真实依赖、Agent 可承担的部分和必要的人工验收，
再按项目约定保存。标签变更会触发现有自动化时先问我。
```

任务票是交给另一个上下文执行的正式内容，接收方没有当前对话，因此按 `writing-for-agents` 的方法写。

## 一次实现

```text
请使用 implement-gamestudio 完成这张票。
沿用已确认的范围，不重新设计需求，也不要自动领取下一项工作。
需要时组合测试先行、结构设计、诊断与评审方法，
完成后按任务责任交接。提交、推送与关单各自需要我单独授权。
```

组合：`tdd-gamestudio` 测试先行，`codebase-gamestudio` 设计职责与接口边界，`debug-gamestudio` 处理原因不明的异常，`review-gamestudio` 收尾做规范与需求两轴评审。评审发现交回实现者组织修复，不自动改代码。

## 用一个可玩原型回答设计问题

```text
请使用 prototype-gamestudio，回答「随时间恢复的体力是否让玩家长时间等待」。
默认做可玩的浏览器小游戏：真实输入影响结果，轻量美术，可重置。
只回答这个问题，不要升成正式实现，也不要领取新任务。
```

原型服务决策，不等于正式交付；保留有用发现和必要依据，已确认采纳的结果再更新 GDD 或 spec。

## 带来源的研究

```text
请使用 research-gamestudio，调查同类游戏怎样处理体力恢复节奏。
用已有工具，给出带来源、适用条件与局限的结论，
结论回到当前讨论，不要替我采纳设计。
```

研究深度按问题选择，不是必走阶段。

## 跨会话找路线

```text
请使用 wayfinder-gamestudio，梳理「把当前 demo 做成完整可发售版本」的路线。
建立或续接决策地图，逐个解决关键未知，按缺口选择访谈、研究或原型。
路线清楚后交接给我，不要自动开始制作。
```

它不是生产排期器或任务调度器；地图帮助跨会话保留问题、依赖与依据。

## 交接

```text
请使用 handoff-gamestudio，把当前未完成的工作写成一份可携带的短交接说明。
整理必要上下文、实际资源与版本位置、下一步和访问缺口。
不要复制工程、开新会话、改任务状态或搬迁资料。
```

接收方是子代理时，委派材料按 `writing-for-agents/references/subagent-delegation.md` 组织。引用不代表已传输。

## 相关文档

安装与第一次会话见 [从安装到第一次有效使用](../getting-started.md)，已有项目接入见 [接入已有游戏项目](existing-projects.md)。每项技能必须一起安装的依赖见 [技能依赖](../dependencies.md)，读写与授权边界见 [数据、写入与权限](../reference/data-and-permissions.md)。

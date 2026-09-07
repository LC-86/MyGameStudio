# Codex 插件依赖、显式调用与角色写入边界

日期：2026-09-07。状态：官方文档研究；未运行插件或角色写入探针，未选择最终权限方案。未读取用户 config、auth 或凭据，未安装、修改治理文件或创建实际角色配置。

## 已确认的承载能力

| 问题 | 当前一手依据及判断 |
| --- | --- |
| 插件能带什么 | 官方打包文档要求 `.codex-plugin/plugin.json`，支持组合 `skills/`、MCP 连接或配置、hooks 及展示资源；manifest 路径相对插件根目录。[Package your plugin：Plugin structure、Manifest fields、Path rules](https://developers.openai.com/plugins/build/plugins#plugin-structure) |
| Skill 能带什么 | Skill 包含指令、资源、可选脚本；插件可分发多项技能。[Build skills](https://learn.chatgpt.com/docs/build-skills) |
| Codex 的显式调用设置 | `agents/openai.yaml` 中 `policy.allow_implicit_invocation: false` 禁止依据用户提示隐式选择该 Skill，显式 `$skill` 仍可用；默认值为 true。[Optional metadata](https://learn.chatgpt.com/docs/build-skills#optional-metadata) |
| 依赖元信息 | 同一技能文档展示 `dependencies.tools`，示例为 MCP 工具依赖。本次未找到外部 Skill 版本依赖、自动下载另一个 Skill、技能依赖锁定或自动解决的官方声明，不能把 MCP 工具依赖机制直接解释成 Skill 包依赖管理。[Optional metadata](https://learn.chatgpt.com/docs/build-skills#optional-metadata) |

**未确认**：本次官方技能页面及定向官方域搜索没有找到 `disable-model-invocation` 与上述 Codex 开关等价的明确说明。不能把本机 Matt Skill 的此字段或其他客户端语义当作 Codex 保证；也不能因此断言 Codex 完全不支持该字段。实现时以官方 Codex 元信息及实际发现/调用验证为准。

## 指令边界与技术限制要分开表述

**已确认：宿主有技术沙箱。** 官方说明沙箱约束文件和网络访问，也覆盖执行出来的命令；`workspace-write` 允许工作区写入，额外 writable roots 用于扩大可写目录。它是会话执行环境的边界，不是 Skill 文本中的角色白名单。[Sandbox](https://learn.chatgpt.com/docs/sandboxing)。

**已确认：自定义子代理可设置自己的会话配置。** 当前官方文档将自定义代理定义为 `.codex/agents/` 或用户级代理目录中的 TOML；可含 `sandbox_mode`、`mcp_servers`、`skills.config` 等，示例提供只读代理。子代理默认继承父级策略。CLI 文档另明确父会话实时 sandbox/approval override 会在派生时重新应用，即使代理文件有不同默认值。[Subagents：Approvals and sandbox controls、Custom agents](https://learn.chatgpt.com/docs/agent-configuration/subagents#approvals-and-sandbox-controls)。

**推断与限制**：同一会话内仅切换角色指令，不能据此声称文件权限已随角色改变。只读子代理可以支持某些隔离需要，但“统筹可写管理文档、禁止写设计文件”的细粒度限制不等于只读配置；需要另行验证宿主配置、目录安排、工具可用性与运行时覆盖。本次没有找到插件 manifest 原生声明“每个角色可写哪些文件”的字段，也未确认插件安装会自动注册自定义代理配置。

**工具范围也是独立控制。** 插件打包文档提供用户按插件 MCP server 调整 `enabled_tools` 与工具审批方式的示例。这限制的是对应 MCP 工具，不能推导为同时限制所有 shell、文件编辑或其他连接器的写入。[Bundled MCP server configuration](https://developers.openai.com/plugins/build/plugins)。

## Hooks 的实际能力与局限

官方目前支持插件携带 hooks；`PreToolUse` 可拦截、拒绝或重写受支持的 shell、apply_patch、MCP 等调用。非托管 hook 必须先审阅并信任，更新后需重新信任。官方同时明确 hooks 不是完整强制边界：部分特殊工具路径可绕过该默认路径，hosted tools 不走本地 hook，已有 exec 的 write_stdin 不重新执行 PreToolUse。[Hooks：Review and trust hooks、Tool coverage、PreToolUse](https://learn.chatgpt.com/docs/hooks#tool-coverage)。

因此 hooks 可以成为辅助检查候选，但不能未经覆盖验证就承诺角色级强制文件白名单。是否引入 hooks、受限写入工具或宿主配置，仍需用户决定设计目标后再评估；此研究不实施其中任何一种。

## 本地官方材料与当前网页的差异

本机官方 [plugin-creator/SKILL.md:99](/Users/cuilei/.codex/skills/.system/plugin-creator/SKILL.md:99)列出 skills、hooks、scripts 等可选目录，但 [195 行](/Users/cuilei/.codex/skills/.system/plugin-creator/SKILL.md:195)仍要求不使用 manifest `hooks` 字段；当前官方网页已明确支持该字段。这里存在版本差异，后续实现需核对目标客户端和验证器，不能沿用本地材料就宣布当前产品不支持 hooks。

## 最小可行设计边界（建议，未替用户定案）

1. 插件先承载三个角色的工作规则、专业 Skills、文档模板和必要资源。角色名称表示责任，不直接声称已建立三个系统权限主体。
2. 全部插件 Skill 使用 Codex 已有依据的显式调用元信息；另明确统筹在被显式调用后可以委派哪些技能。必须验证直接调用、普通对话不触发、统筹显式委派这三条路径，不能假定一个元信息字段已经解决全部调度语义。
3. writing-for-agents 依赖必须可定位、可读取且有清楚的版本来源。可以讨论随插件提供兼容版本或要求用户先具备该依赖；本次未审查重分发许可，也未选择方案。不能将开发机个人绝对路径作为面向其他用户的依赖方案，不能假设安装插件会自动解决外部 Skill。
4. 将“一文件同一时间一执行者”、角色写入范围、执行前核对和结果检查写成可验证工作约定。若最终要求技术上阻止越权，需独立设计并证明所有可写通路的限制；仅靠 Skill 指令或事后检查不报告为硬隔离。

## 仍需实测或继续决策

- 目标 Codex 版本对技能元信息、插件 hooks、自定义代理文件和父会话覆盖的真实行为。
- writing-for-agents 缺失、名称冲突、版本变化时如何处理及如何分发。
- 统筹委派是否正确加载显式 Skill，并保持专业产物归属及现有授权。
- 是否需要硬权限隔离；若需要，目录写入、shell、已有进程、连接器、资源工具、符号链接和临时产物等通路如何覆盖。

这些是尚未验证的产品边界，不表示当前插件已经具备对应机制。研究正文主要依据上述五页官方专题文档；Markdown 正文通过官方页面提供的 `.md` 链接读取，没有依赖搜索摘要作最终事实判断。

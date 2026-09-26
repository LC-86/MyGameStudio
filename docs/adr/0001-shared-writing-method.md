# 统一写作方法，保留 GameStudio 按需参考

用户确认共同写作方法采用官方 `mattpocock/skills` 的 `writing-for-agents`，作为 MyGameStudio 的外部依赖；MyGameStudio 不维护或分发第二份副本。保留并收窄 docs-gamestudio 为游戏文档分流与增量协作的参考入口。本库维护规则留在仓库，人机责任与验收交接仍由 tasks 参考拥有。

选择这条路线是为了消除两份广泛写作方法的竞争，同时保留游戏参考路径。MyGameStudio 保持 20 项技能，不增加第 21 项共同方法；官方方法由用户独立安装并更新。

2026-09-27，用户进一步确认安装说明同时覆盖用户级和项目级范围，并重点提醒用户级。安装流程不做实际检测或条件补齐，只提醒用户确认 `writing-for-agents` 已从明确的 MattPocock 来源安装；不设计能力标记、正文扫描或自动替换。用户级与项目级副本冲突时，以目标宿主在当前项目中实际加载到的版本为准。

官方现版没有语义保真规则或通用子代理委派参考，这两项继续由 `docs-gamestudio` 保留；只有官方将来提供等价能力后才迁走。相关 GameStudio 技能在编写正式 Agent 资料时按名称取得外部 `writing-for-agents`，不使用跨安装范围的相对路径；无法取得时说明依赖缺口，只继续不受影响的工作。

安装说明优先推荐把共同方法装到用户级，同时提供项目级替代；MyGameStudio 的 20 项技能继续同时提供两种范围。面向用户的命令使用 `skills@latest`，验证记录单独注明当前参数与范围行为只在 CLI 1.7.0 上核实，不把未来 latest 写成已验证事实。

本 ADR 记录方案决定，不授权修改技能正文或已安装副本、提交、推送、发布工单。引用迁移、实施与行为验证见 [方案](../design/shared-writing-method.md)、[Issue #93](https://github.com/LC-86/MyGameStudio/issues/93) 与[验证记录](../validation-v3.md)。

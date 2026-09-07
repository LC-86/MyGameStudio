# Codex 插件依赖与角色写入限制的承载能力

Parent: [MyGameStudio 通用工作流与角色分工设计](../map.md)
Type: research
Labels: wayfinder:research
Status: resolved
Assignee: capability research subagent
Blocked by: none

## Question

当前 Codex 插件与 Skills 能否声明或携带其他技能，如何处理显式调用与能力缺失？角色的允许写入范围能否由插件或子代理配置形成技术限制，哪些仅属于指令约定？基于本地官方资料和当前官方文档给出证据与限制，为 MyGameStudio 的执行能力设计提供事实。

## Comments

用户已要求所有插件 Skill 显式调用，制作统筹自身只写管理文档，文档编写调用 writing-for-agents。本票只核对承载能力，不安装、修改客户端配置或治理文件，不创建实际插件运行时。

研究保存到 research/codex-capability-boundaries.md。只读取相关官方技能资料及官方公开文档；当前工作区非 Git 仓库，研究不初始化或提交。

## Answer

已完成并回读[官方能力核对](../research/codex-capability-boundaries.md)。确认插件可携带 Skills 等能力，Codex 官方显式调用元信息为 agents/openai.yaml 的 policy.allow_implicit_invocation。研究未找到外部 Skill 自动解析和版本锁定的官方声明，依赖可用性不能由安装插件直接推定。

角色指令与技术限制需要区分。官方支持会话及自定义子代理沙箱，但本次未找到插件原生声明角色文件白名单的机制；hooks 有工具覆盖限制，不能直接当作完整强制边界。资料中还存在本地 plugin-creator 与当前官方 hooks 文档的版本差异。均需在目标客户端验证，研究未执行实际探针。

这些事实用于[通用职责与具体执行能力的衔接](05-capability-adaptation.md)的产品取舍；是否要求第一版技术上强制拒绝越界写入，仍待用户决定。

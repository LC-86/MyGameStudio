# 工具拦截的调用契约、身份与覆盖条件

Parent: [MyGameStudio 通用工作流与角色分工设计](../map.md)
Type: research
Labels: wayfinder:research
Status: resolved
Assignee: interception research subagent
Blocked by: none

## Question

用户要求第一版实现工具拦截机制。当前 Codex hooks 的调用前事件提供哪些由宿主产生的身份和工具参数，如何拒绝调用，哪些写入路径不能仅靠该事件约束？实现按角色写入范围检查时，需要什么可信角色绑定、受控执行条件和覆盖验证？依据官方文档或官方代码核对，不将仅有钩子配置当作完整保证。

## Comments

Q29 是当前框架设计中对首版保障方式的决定；研究用于形成可实施契约。本票不安装或启用 hooks，不修改用户客户端设置，不在真实游戏项目做拦截探针。资料保存到 research/tool-interception-contract.md。

## Answer

已完成并回读[调用契约研究](../research/tool-interception-contract.md)。同步 PreToolUse 可拒绝受支持调用，但身份字段存在文档与上游 schema 版本差异，检查器错误不能默认当作拒绝，且已有进程输入、hosted 和部分专用工具有覆盖缺口。

因此首版的强制目标需要证明可信角色绑定、受控写入通路、故障时拒绝及规则保护。具体设计见[工具拦截设计](../proposals/tool-interception.md)，目标客户端和实际机制尚未验证。研究不把上游 main 源码当作本机已安装能力，也不声称拦截器已经实现。

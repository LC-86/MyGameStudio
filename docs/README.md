# 文档导航

人读说明在这里。Agent 技能正文在 `skills/<技能名>/SKILL.md`，那才是技能的权威来源，不要把两套混成一种文件。

本仓库的 `docs/agents/` 只给**维护本仓库的人**用，不是用户游戏教程。

## 开始使用

- [从安装到第一次有效使用](getting-started.md)：装好后第一次会话该说什么、期待什么结果
- [安装](installation.md)：官方 `skills` CLI 的安装、安装后确认与卸载
- [技能依赖](dependencies.md)：完整安装与选择安装时必须一起带上的技能和共享参考

## 使用

- [常用工作流](usage/workflows.md)：设计讨论、拆票、实现、原型、研究、路线梳理的实际组合
- [接入已有游戏项目](usage/existing-projects.md)：让技能沿用你项目的真实约定

## 参考

- [当前能力与限制](reference/capabilities.md)：20 项技能全表、职责、已退役能力与明确不覆盖的部分
- [数据、写入与权限](reference/data-and-permissions.md)：技能读什么、改什么、从不假定哪些授权
- [排错](reference/troubleshooting.md)：安装后不被发现、共享参考缺失、宿主自行选入口等问题的处理
- [与 Matt Pocock skills 的关系](reference/upstream.md)：方法基线、继承与适配、许可来源

## 版本迁移与验证

- [从 2.0.2 迁移到 3.0.0](migration-v3.md)：旧插件命令已退出，旧入口的能力去向；当前版本 3.0.1
- [验证状态](validation-v3.md)：哪些检查已运行、哪些行为场景未运行或未通过

## 设计资料

- [V3 执行覆盖](design/v3-overrides.md)：本次执行对旧设计的明确覆盖条款
- [统一设计 v1](design/unified-design-v1.md)：20 项技能的设计依据，保留原始身份

## 维护本仓库

- [测试说明](development/testing.md)：跑哪些检查、静态检查覆盖什么、不覆盖什么
- [发布说明](development/releasing.md)：V3 的发布步骤与没有构建产物的含义
- [贡献指南](../CONTRIBUTING.md)：文档与技能的分工、新技能准入
- [安全报告](../SECURITY.md)：私密报告通道与报告内容
- 维护者协作：[issue tracker](agents/issue-tracker.md)、[triage 标签](agents/triage-labels.md)、[领域文档](agents/domain.md)

# 游戏项目文档用途与维护方式的一手依据

Parent: [MyGameStudio 通用工作流与角色分工设计](../map.md)
Type: research
Labels: wayfinder:research
Status: resolved
Assignee: documentation research subagent
Blocked by: none

## Question

一手游戏开发及软件工程资料如何区分需求与游戏设计文档、技术设计与架构决定、执行计划及过程记录？哪些依据支持小项目从简短设计逐步扩展、保持当前设计与历史决策的区分？是否存在可证明的统一 GRD → GDD → TDD → 原子计划强制流程？以来源实际支持的范围作答，为项目记录与交接设计提供事实参考，不替用户决定本插件的文档体系。

## Comments

本地工作区尚无 Git 仓库，因此研究材料保存在当前 effort 的 research/ 目录，以本票链接定位；不初始化 Git、不创建分支、不提交或发布。研究结果写入 research/documentation-evidence.md，由主会话回读后记录解决结果。

## Answer

独立研究已完成，主会话已回读[一手资料核对结果](../research/documentation-evidence.md)。研究确认：Unity 教程支持由简短设计说明逐步扩展 GDD；Microsoft 工程资料区分当前设计、ADR 决策历史和可持续细化的执行待办。这些来源可支持轻量、持续维护的文档方案，但没有建立统一强制的 GRD → GDD → TDD → 原子计划流水线，也不能由有限检索断言行业不存在此类流程。

GRD 与 TDD 的用户含义尚未确定，不能以研究结论代替用户定义。文档分类、维护角色和合并方式仍由[项目记录、角色交接与跨会话恢复](04-project-handoffs.md)讨论决定。

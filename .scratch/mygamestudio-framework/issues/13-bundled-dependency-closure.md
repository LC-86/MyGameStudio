# 内置通用技能的引用依赖核对

Parent: [MyGameStudio 通用工作流与角色分工设计](../map.md)
Type: research
Labels: wayfinder:research
Status: resolved
Assignee: dependency research subagent
Blocked by: none

## Question

第一版复用的通用技能需要携带哪些被实际引用的技能与参考文件，哪些属于项目配置、外部工具或需要替换的游戏侧协议？核对最小依赖闭包，避免只复制 SKILL.md 后留下失效引用。

## Comments

读取本地已明确引用的通用技能与必要参考文件，结果保存到 research/bundled-dependency-closure.md。只研究依赖，不复制正式插件资产、不安装或修改原技能。

## Answer

2026-09-08 已回读[依赖闭包核对](../research/bundled-dependency-closure.md)：六项基础方法及三份配套资料构成当前最小基础集合，另有四份原型/代码审查条件参考；十三份源文件均已记录本地指纹。项目配置与动态资料不属于静态依赖。

业务入口使用游戏侧合同，通用材料作为内部依赖，原型与审查映射到对应 Game 入口。用户后续补充的 setup 方法纳入 Game-Init 的协作配置参考；其采用分支及许可、来源记录要求见[包合同](../contracts/package.md)。研究完成不表示已复制资产或完成安装验证。

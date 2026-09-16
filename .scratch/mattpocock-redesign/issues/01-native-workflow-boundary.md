# Matt 原技能与游戏扩展的职责边界

Type: grilling
Labels: wayfinder:grilling
Status: published-snapshot
Remote: [Matt 原技能与游戏扩展的职责边界](https://github.com/LC-86/MyGameStudio/issues/40)
Authority: GitHub; local content is the publication source snapshot
Blocked by: none
Parent: [MyGameStudio：沿用 Matt 流程的游戏专业扩展改版地图](https://github.com/LC-86/MyGameStudio/issues/39)

## Question

在已确定“保留 Matt 原技能、增加游戏专业扩展”的前提下，如何把当前十四个入口逐项映射为原技能、游戏专业入口、按需参考或迁移兼容入口，并保证同一管理规则只有一个维护者？

需要明确：通用路由/讨论/地图/规格/拆票/实现/评审的拥有者；游戏原型、设计、视听、构建、试玩的专业责任；扩展被原技能实际发现和读取的方式；哪些差异只是资料补充，哪些必须有可追踪的适配。不能以“内部引用过 Matt”视为完成复用。

尤其需要遵守上游用户调用与模型可调用的区分：路由器不能自动串起用户专用入口。明确专业扩展的主动调用或资料加载契约，并在后续验证它确实可达，不把目录存在视为已经接入。

## Context

- [两套技能对照与候选方向](../analysis.md)
- [上游流程及正式分发范围](../research/matt-workflow.md)
- [现有入口和耦合点](../research/mygamestudio-current.md)

本票形成可核对的职责矩阵及调用示例，不确定最终文件目录，不执行删改。

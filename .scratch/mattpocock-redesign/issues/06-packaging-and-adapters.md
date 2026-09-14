# 上游版本、插件分发与专业工具适配

Type: grilling
Labels: wayfinder:grilling
Status: open
Blocked by: 01, 02, 05
Parent: [改版地图](../map.md)

## Question

保留 Matt 原技能时，采用独立安装加游戏扩展，还是固定上游快照的组合分发？怎样追踪版本、许可证、必要适配和升级差异，并确保宿主只发现一份同名技能且游戏扩展可达？

同时明确通用游戏合同与引擎/平台/资源工具适配的界限、首批实际承诺的支持范围、未配置能力的回退交接及验证方式。上游正式发布集合与 in-progress 技能分开评估；上游名字出现在目录中不等于稳定发布。安装选择不自动扩大目标项目写入权限。

## Context

- [Matt 发布集合、许可和更新差异](../research/matt-workflow.md)
- [当前 package/provenance/runtime 结构](../research/mygamestudio-current.md)

本票定义分发与适配合同，不安装插件，不承诺未经实际检查的多宿主兼容性。

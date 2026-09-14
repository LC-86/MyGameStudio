# MyGameStudio：沿用 Matt 流程的游戏专业扩展改版地图

Labels: wayfinder:map
Status: open
Publication: local draft; not published to GitHub

## Destination

明确 MyGameStudio 以 Matt 原技能与管理流程为基础的改版方案：划清复用与游戏专业扩展的边界，确定记录、验证、运行保障、分发与迁移的取舍，使后续能够用 `to-spec` 汇总规格，再用 `to-tickets` 拆解实施。
本地图终点是决策清楚、可交接的方案；本轮建立地图并提供分析，不执行插件改版。

## Notes

- 用户已明确：保留 Matt 原技能，增加游戏专业扩展；继续面向个人独立开发者，引擎与平台中立。这是建图输入，不是助手自行解决的票内决定。
- 方法：使用用户指定的 [wayfinder](/Users/cuilei/.mirasim/skills/wayfinder/SKILL.md)；决策讨论使用 [grilling](/Users/cuilei/.mirasim/skills/grilling/SKILL.md) 与 [domain-modeling](/Users/cuilei/.mirasim/skills/domain-modeling/SKILL.md)。按依赖前沿、分模块成组提问，事实由 Agent 调查，选择由用户作出。建图阶段不手动解决决策票；后续每会话最多解决一张非 research 票。
- 本地图按建图时的本地 Markdown 约定创建。用户随后已将仓库默认 tracker 改为 [GitHub Issues](../../docs/agents/issue-tracker.md)；本地图及八张子票目前仍是未发布的本地草稿。后续发布迁移时建立 GitHub 原生父子与阻塞关系、回填对应链接，再以 GitHub 为当前权威，不同时维护两套状态。草稿中的 `Status` 与 `Blocked by` 仅描述当前本地票，不表示远端已有记录。
- 阅读现有 [CONTEXT](../../CONTEXT.md) 时，区分既有角色/原子任务定义与本轮候选术语。本轮尚未修改原领域词汇、旧地图及治理文件；新方案明确后再按需要形成领域词汇和 ADR。
- 分析基线：MyGameStudio `268e2fa6fd535482c3567c8b58f124aa09d93f94`；Matt `3cca18b368ae95cdbdebbff572ccafa662551015`。上游会更新，实施前需再核实采用版本及本地差异。
- 研究入口：[上游流程分析](research/matt-workflow.md)、[现有 MyGameStudio 分析](research/mygamestudio-current.md)、[游戏专业证据](research/game-professional-evidence.md)。综合建议见[改版分析与方向](analysis.md)；建议不是已采纳的设计。
- 只让一个位置维护每项权威内容；本地图不保存完整规格，也不另列开放票清单。前沿从子票状态、认领和依赖计算。
- 本次已创建本地/远端分支 `codex/mygamestudio-mattpocock-redesign`，起点为上述 MyGameStudio 基线。分支创建授权不包含提交分析文件、推送后续改动、发布远端工单或正式安装。

## Decisions so far

尚无已解决的子票。上述两项用户选择是建图前已明确的边界；其余建议等待相应决策票讨论。

## Not yet specified

- 在选定专业验证样本与迁移试点后，可能暴露尚未识别的旧资料形态、工具行为和体验证据缺口；按调查结果形成具体问题，不提前假设全部兼容场景。
- 专业扩展切分与首批适配边界确定后，再判断是否出现需要单独验证的新接缝；已有明确的问题已在子票中，不在此重复。

## Out of scope

- 本地图不实施、安装、发布新版插件，不创建实施工单或远端 Issues/PR，不提交本轮文档。
- 不修改任何具体游戏的设计、代码、存档或资源，也不迁移真实项目。
- 不构建面向大团队的固定企业审批流程；不强制所有游戏逐一采用所有专业模块。
- 不把未运行的客户端、性能、试玩或效率检查记为通过；商业化与发行方法可以纳入设计，实际发布不在本轮范围。

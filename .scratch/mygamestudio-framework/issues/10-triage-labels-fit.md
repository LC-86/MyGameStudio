# Matt 五类 triage 标签与游戏任务分流的适配依据

Parent: [MyGameStudio 通用工作流与角色分工设计](../map.md)
Type: research
Labels: wayfinder:research
Status: resolved
Assignee: triage research subagent
Blocked by: none

## Question

Matt 当前公开仓库中的五类 triage 标签分别表示什么，与本地项目配置是否一致？它们如何用于分流，是否表达执行者、验收者或执行进度？哪些可以复用于 MyGameStudio，哪些需要独立字段或进一步约定？依据一手源文件区分事实与建议。

## Comments

用户在认可游戏开发小闭环后，要求继续调研五类 triage 标签的复用可能性。研究材料保存到 research/triage-labels-fit.md。只读取公开仓库与相关本地文件，不修改实际标签配置，不创建远端工单，不执行分流或关闭任务。

## Answer

公开仓库已固定到 main 提交 3cca18b368ae95cdbdebbff572ccafa662551015，主会话已回读[研究结果](../research/triage-labels-fit.md)并读取固定版本的上游正文。五个状态与本地配置一致：needs-triage、needs-info、ready-for-agent、ready-for-human、wontfix；已分流请求使用一个 state，bug/enhancement 是另一类 category。

完整规则中的 ready-for-human 包括人工判断、设计决定、外部访问、手工测试，PR 场景还包括等人合并；不能仅解释为人写代码。五状态没有完整表达执行进度或独立验收状态。wontfix 还用于已有成果覆盖、无需重复实施的请求，不等于制作任务完成。

建议在游戏流程中保留五类分流含义，另以任务记录表达执行责任、验收方式、进度和依赖。具体是否采用及其映射仍由[项目记录、角色交接与跨会话恢复](04-project-handoffs.md)决定，当前方案见[任务分流设计](../proposals/task-triage.md)。本研究未修改实际标签配置。

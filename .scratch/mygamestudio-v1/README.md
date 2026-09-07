# MyGameStudio v1：实施任务总览

2026-09-08，用户已确认十八张实施票的颗粒度、交付内容及依赖关系，现发布到本地 Markdown tracker。这里仅索引任务；验收、依赖和后续状态由各票维护。

开始实施前读取[实施范围与验收约定](spec.md)。完整行为依据为[插件工作方式完整设计](../mygamestudio-framework/spec.md)，原设计决策票保持不变。

## 任务索引

| 任务 | 前置任务 |
| --- | --- |
| [01：显式调用并查看项目状态](issues/01-explicit-project-status.md) | 无 |
| [02：统筹与专业角色分别完成一次受限写入](issues/02-role-scoped-write.md) | [01](issues/01-explicit-project-status.md) |
| [03：间接写入与检查故障仍受限制](issues/03-indirect-write-failure-boundaries.md) | [02](issues/02-role-scoped-write.md) |
| [04：初始化一个使用本地任务记录的新项目](issues/04-initialize-local-project.md) | [03](issues/03-indirect-write-failure-boundaries.md) |
| [05：接手已有项目并安全补齐资料](issues/05-adopt-existing-project.md) | [04](issues/04-initialize-local-project.md) |
| [06：把功能想法形成当前可执行规格](issues/06-idea-to-current-spec.md) | [04](issues/04-initialize-local-project.md) |
| [07：用隔离原型验证一个设计问题](issues/07-isolated-design-prototype.md) | [06](issues/06-idea-to-current-spec.md) |
| [08：将规格拆成可接手的本地原子任务](issues/08-spec-to-local-tasks.md) | [06](issues/06-idea-to-current-spec.md) |
| [09：完成一个代码任务并交接实际结果](issues/09-code-task-delivery.md) | [08](issues/08-spec-to-local-tasks.md) |
| [10：完成一个视觉资源任务](issues/10-visual-asset-delivery.md) | [04](issues/04-initialize-local-project.md) |
| [11：完成一个音频资源任务](issues/11-audio-asset-delivery.md) | [04](issues/04-initialize-local-project.md) |
| [12：从项目实际配置构建并运行成果](issues/12-build-and-run-delivery.md) | [09](issues/09-code-task-delivery.md) |
| [13：独立审查实际待交付成果](issues/13-independent-deliverable-review.md) | [06](issues/06-idea-to-current-spec.md) |
| [14：执行试玩并收集真实人工反馈](issues/14-playtest-and-human-feedback.md) | [04](issues/04-initialize-local-project.md) |
| [15：正确处理目标变化、并发工作与中断恢复](issues/15-goal-change-concurrency-recovery.md) | [09](issues/09-code-task-delivery.md) |
| [16：由制作统筹跑通完整的小步开发闭环](issues/16-producer-complete-loop.md) | [07](issues/07-isolated-design-prototype.md)、[10](issues/10-visual-asset-delivery.md)、[11](issues/11-audio-asset-delivery.md)、[12](issues/12-build-and-run-delivery.md)、[13](issues/13-independent-deliverable-review.md)、[14](issues/14-playtest-and-human-feedback.md)、[15](issues/15-goal-change-concurrency-recovery.md) |
| [17：使用 GitHub Issues 管理同一套工作流](issues/17-github-issue-workflow.md) | [08](issues/08-spec-to-local-tasks.md) |
| [18：验收完整插件包及升级行为](issues/18-complete-package-acceptance.md) | [05](issues/05-adopt-existing-project.md)、[16](issues/16-producer-complete-loop.md)、[17](issues/17-github-issue-workflow.md) |

## 从哪里开始

发布时所有任务尚未实施，唯一无前置任务的是[显式调用并查看项目状态](issues/01-explicit-project-status.md)。之后按各票的实际完成结果重新计算可开工任务，不把 ready-for-agent 当作前置依赖已满足。

不同任务可以在依赖满足、写入资源不重叠时并行；共享成果明确修改顺序和集成责任。受限写入在早期验证失败时，相关票保持未完成，依赖票不能用文档承诺代替前置成果。


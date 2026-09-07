# 16：由制作统筹跑通完整的小步开发闭环

**What to build:** 开发者显式调用 Game-Producer 后，统筹按当前请求选择专业能力，贯通目标、规格、计划、制作、独立审查、必要人工验收和项目同步。

**Blocked by:** [07：用隔离原型验证一个设计问题](07-isolated-design-prototype.md)；[10：完成一个视觉资源任务](10-visual-asset-delivery.md)；[11：完成一个音频资源任务](11-audio-asset-delivery.md)；[12：从项目实际配置构建并运行成果](12-build-and-run-delivery.md)；[13：独立审查实际待交付成果](13-independent-deliverable-review.md)；[14：执行试玩并收集真实人工反馈](14-playtest-and-human-feedback.md)；[15：正确处理目标变化、并发工作与中断恢复](15-goal-change-concurrency-recovery.md)

**Status:** ready-for-agent

## 验收标准

- [ ] 明确区分仅讨论、已有规格制作、直接专业调用后的状态同步三种入口，按足够的已有资料从合适环节开始。
- [ ] 统筹可按本次需要明确委派所有已实现业务入口；Game-Implement 管本次制作，设计原型保持隔离；不强制每轮执行全部技能。
- [ ] 用包含设计决定、原型、代码、视听资源、构建、审查和试玩的代表性样例验证可选分支与交接；预先提供或实际取得的人的决定保留真实来源。
- [ ] 每次专业工作有实际基线、产物、结果与证据，统筹自身仍只写管理资料；委派或调用能力不会扩大本次授权。
- [ ] 目标变化先同步受影响内容再继续；普通专业结果在统筹下次介入时核对，Game-Status 能准确展示待做、已做、待验收与阻塞。
- [ ] 独立审查和约定检查完成且无需人判断时可标记完成；需要人的验收仍等待真实反馈，作者自报或旧版本结果不能代替。
- [ ] 验证较小任务可用短规格和单项工作完成闭环，未来目标保持粗粒度，不引入企业式立项或固定阶段门槛。

## 实施依据

开始时读取[实施范围与验收约定](../spec.md)，再按本票分支读取[管理技能合同](../../mygamestudio-framework/contracts/management.md)、[业务 Skill 共同合同](../../mygamestudio-framework/contracts/common.md)、[工作记录与任务后端合同](../../mygamestudio-framework/contracts/records.md)。具体工程位置在实施时从当前项目读取。


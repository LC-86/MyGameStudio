# 项目文档职责：一手依据核对

日期：2026-09-07。范围：为框架讨论提供有限依据，不代表用户已接受任何文档体系。研究票由主会话管理；当前目录非 Git 仓库，未创建研究分支、初始化 Git 或提交。

## 已读取的来源与精确事实

1. **短设计说明可以逐渐扩展成 GDD。** Unity 的 Game Design 教程明确从简短 design brief 开始，并说明后续成长为完整 game design document。正文将设计与实现视为不同思考方式，允许个人开发者同时承担；设计会随着原型、试玩和反馈迭代。依据：Summary、Game design vs. game development。来源：[Unity Learn — Game Design](https://learn.unity.com/tutorial/game-design?version=6.3)。限制：这是 Unity 入门教学方式，不是跨项目统一标准。

2. **GDD 的格式可以变化，优先级也可以记录其中。** Unity 的 Create a game design document 教程允许采用模板或自己的替代方式，并要求区分关键与非必要功能。后续另有 production plan 教学安排。依据：Create your game design document、Prioritize your game features、Prepare to get feedback。来源：[Unity Learn — Create a game design document](https://learn.unity.com/tutorial/create-a-game-design-document?version=2022.3)。限制：这是特定无障碍游戏教程，不能据此要求所有游戏采用同一文档流程。

3. **当前设计文档与决策历史应承担不同用途。** Microsoft Playbook 建议：设计决定进入整体设计文档，同时可用 ADR 保留决定背景、结论和后果；ADR 有 proposed、accepted、deprecated、superseded 状态，旧决定可被替代。依据：What is a Recommended Format for Tracking Decisions、Architecture Decision Record。来源：[Microsoft — Design Decision Log](https://microsoft.github.io/code-with-engineering-playbook/design/design-reviews/decision-log/)。限制：该建议针对重要架构决定，不要求每个小改动建立 ADR。

4. **任务需要完成标准，计划可以持续细化。** Microsoft Playbook 的 Backlog Management 要求清晰验收标准与完成定义，建议持续完善待办，并允许团队按自身情况决定任务创建方式。依据：Backlog 的 Goals 与 Suggestions。来源：[Microsoft — Backlog Management](https://microsoft.github.io/code-with-engineering-playbook/agile-development/backlog-management/)。限制：它处于团队敏捷工程语境；不构成个人开发者必须使用 Sprint、会议或多层任务结构的依据。

## 对本次讨论的有限推断

- 可区分三个用途：当前有效的设计约定回答“现在以什么为准”；ADR 等历史记录回答“为什么作此决定、后来如何改变”；执行计划和工作记录回答“接下来做什么、实际上完成了什么”。这是综合上述用途作出的框架建议，不是来源规定的三层分类。
- 已完成任务或验证报告可以成为设计修订的证据，但不能因为记录更新就自动改变设计约定。这是避免目标漂移的设计建议，需由用户确认。
- 本次四份来源没有提供“GRD → GDD → 技术架构 → TDD → 原子计划”的统一强制流水线依据。不能由有限检索推断行业中不存在此流程。
- 本次来源采用 GDD 表示 game design document；不能将用户写的 GRD 擅自改为 GDD，也不能推定其含义。TDD 也需明确用户所指文档名称；不要直接与 Test-Driven Development 混用。
- 在最终设计中，应先确定资料用途、维护责任、当前有效状态及更新时机，再协商文件名称与是否合并。这个顺序是研究者建议，不是已经形成的项目决定。

## 研究边界

读取了上述四页正文；Unity 最初的 /unity-version 页面只是版本选择页，已跟进 Continue 到教程正文。未检查 GDD 模板附件、未调研具体引擎交付物、未为 MyGameStudio 制定最终目录或权限表。每份来源摘述均保持简短，无长段引用。

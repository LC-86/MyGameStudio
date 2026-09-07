# Matt 五类分流标签与游戏流程的适配核对

读取日期：2026-09-07。研究材料，适配建议待用户确认。本次仅联网读取公开来源、对照本地文件并新增本记录；未执行分流、标签修改、Git 操作或远端写入。

## 版本与来源

公开仓库默认分支为 main；GitHub API 读取的 HEAD 为 [3cca18b368ae95cdbdebbff572ccafa662551015](https://github.com/mattpocock/skills/commit/3cca18b368ae95cdbdebbff572ccafa662551015)，提交时间 2026-09-04T08:43:27Z。先读取 GitHub 文件正文，再通过固定提交的 raw 页面复核；以下行号按原文件计，不使用网页导航行号。

上游文件位于 skills/engineering/，不是仓库根目录下的技能文件夹。当前上游 triage/SKILL.md 与本机对应文件逐字节一致；triage-labels.md 模板也逐字节一致。SHA-256 分别为 `623a2ed692bdc77d2090e2a3dea3b627dd722ad3bbaca0be83aada75292c8fc4`、`4f53c9b40ce2651e3611aa090eaedbd6dbc9b71ef8c5f7e65eac0d8263190d0d`。

## 准确的五个状态角色

| canonical role | 默认含义 |
| --- | --- |
| needs-triage | 维护者尚需评估 |
| needs-info | 等待报告者补充信息 |
| ready-for-agent | 已充分说明，可交给 AFK Agent |
| ready-for-human | 需要人类实现；正文另有更广的适用场景 |
| wontfix | 不再执行该请求 |

表中简写来自[上游标签模板第 7–11 行](https://github.com/mattpocock/skills/blob/3cca18b368ae95cdbdebbff572ccafa662551015/skills/engineering/setup-matt-pocock-skills/triage-labels.md#L7-L11)。canonical role 与实际标签字符串可映射；本项目[词表第 3–9 行](/Users/cuilei/MyOS/01_Projects/plugins/MyGameStudio/docs/agents/triage-labels.md:3)与模板含义一致。ready-for-human 的较广解释依据下方执行正文。

## 完整正文补充的事实

- **ready-for-human 不限于人写代码。** 正文列出判断、外部访问、设计决定和人工测试。[第 78–80 行](https://github.com/mattpocock/skills/blob/3cca18b368ae95cdbdebbff572ccafa662551015/skills/engineering/triage/SKILL.md#L78-L80)。PR 场景表示准备交人合并。[第 39 行](https://github.com/mattpocock/skills/blob/3cca18b368ae95cdbdebbff572ccafa662551015/skills/engineering/triage/SKILL.md#L39)。因此可涵盖需要人参与的设计工作，但原文没有定义一套完整 HITL 协作协议。
- **五状态互斥。** 已分流事项恰有一个 state，另有一个 bug/enhancement 类别。未标记事项通常先进入 needs-triage，再分到其他状态；信息补齐后回到 needs-triage。维护者可覆盖，不寻常变更要指出。[第 26–45 行](https://github.com/mattpocock/skills/blob/3cca18b368ae95cdbdebbff572ccafa662551015/skills/engineering/triage/SKILL.md#L26-L45)。替换旧 state、保留类别是由互斥要求推导的适配做法。
- **分流先核对再决定。** 阅读已有记录、核对请求、必要时追问，输出简报或缺失信息；不会因为出现 ready-for-agent 就在该步骤实现需求。[第 68–86 行](https://github.com/mattpocock/skills/blob/3cca18b368ae95cdbdebbff572ccafa662551015/skills/engineering/triage/SKILL.md#L68-L86)。
- **wontfix 也覆盖“已经实现，无须再做”。** 原文将其与拒绝请求区分记录并关闭；这不等于本轮制作任务验收通过。[第 82–85 行](https://github.com/mattpocock/skills/blob/3cca18b368ae95cdbdebbff572ccafa662551015/skills/engineering/triage/SKILL.md#L82-L85)。

这五状态中没有独立的进行中、依赖阻塞、待独立审查、待人工验收、验证失败、已完成状态；是否需要人验收不能单靠执行分流标签判断。上游简报虽要求可验证验收条件，但不是验收状态机。[AGENT-BRIEF.md](https://github.com/mattpocock/skills/blob/3cca18b368ae95cdbdebbff572ccafa662551015/skills/engineering/triage/AGENT-BRIEF.md)。

## 对 MyGameStudio 的建议（未确认）

1. 五种含义都可以保留为“当前请求下一步怎样处理”的轻量分流。它们不承担整个游戏任务生命周期。
2. 将 ready-for-human 在产品说明中解释为“下一步需要开发者参与”，并写明参与事项：作设计取舍、提供访问条件、人工测试等。仅缺少一项可明确补充的信息时，优先表达为 needs-info，避免两状态重叠。
3. 单独记录执行进度、必要人工验收及其实际结果；实现可由 Agent 承担，体验验收仍可由开发者承担。可以用简短字段，不必立即增加更多标签。
4. wontfix 需要原因，区分明确不做、请求已经满足等；不要把暂停、以后再做或本次任务完成统统归进去。
5. ready-for-agent 只说明可委派条件，不能代替实施、提交或外部写入授权；准备开始时仍需检查当前基线、依赖、可用工具和本次授权。这是 MyGameStudio 结合既定边界需要补充的规则，不是原标签自带的保证。

## 对上一份研究的修正

[Matt 路线兼容性记录](matt-workflow-fit.md)此前依据项目简表将 ready-for-human 主要解释为人类实现，表达偏窄。完整本地与上游正文均已明确人工判断、设计、测试等场景；“执行者不等于验收者”的建议仍成立，但不能声称 Matt 的 ready-for-human 排除了人工设计或人工测试。此处记录修正，本次未改写原研究文件。

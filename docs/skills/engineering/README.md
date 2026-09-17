# 通用工程技能

这些是固定版本 Matt engineering 技能。标识保持上游小写名称。
首版不写满 18 篇长文；下面是完整索引，以及游戏开发里最常串起来的五个入口。

来源：mattpocock/skills 1.2.3。适配差异见 [upstream.md](../../reference/upstream.md)。

| 标识 | 何时用（一句话） | 人读页 |
| --- | --- | --- |
| `setup-matt-pocock-skills` | 第一次在游戏仓库配置 tracker、标签、领域文档 | [setup-matt-pocock-skills.md](setup-matt-pocock-skills.md) |
| `to-spec` | 把已讨论并采纳的内容写成规格 | [to-spec.md](to-spec.md) |
| `to-tickets` | 把较大范围拆成可执行任务 | [to-tickets.md](to-tickets.md) |
| `implement` | 按规格或任务实现 | [implement.md](implement.md) |
| `code-review` | 对完整待审成果做两轴评审 | [code-review.md](code-review.md) |
| `ask-matt` | 不知道该走哪条技能路径 | 见技能源码 |
| `grill-with-docs` | 边追问边留下 CONTEXT/ADR | 见技能源码 |
| `wayfinder` | 跨越多会话的大块工作需要决策地图 | 见技能源码 |
| `tdd` | 先写失败测试再实现 | 见技能源码 |
| `prototype` | 用一次性原型回答设计问题 | 见技能源码 |
| `domain-modeling` | 统一术语与 CONTEXT | 见技能源码 |
| `codebase-design` | 设计模块接口与深度 | 见技能源码 |
| `research` | 按高信任来源做调查并落盘 | 见技能源码 |
| `diagnosing-bugs` | 难复现缺陷或性能回退 | 见技能源码 |
| `improve-codebase-architecture` | 扫描可加深的架构机会 | 见技能源码 |
| `resolving-merge-conflicts` | 解决进行中的合并冲突 | 见技能源码 |
| `triage` | 处理外部来的缺陷/请求（不是 to-tickets 产物） | 见技能源码 |
| `wizard` | 生成只能由人完成的交互步骤 | 见技能源码 |

技能源码目录：`plugin/skills/<标识>/SKILL.md`。

用户专用入口（制作统筹不得自动串调）：`ask-matt`、`grill-me`、`grill-with-docs`、`handoff`、`implement`、`improve-codebase-architecture`、`setup-matt-pocock-skills`、`teach`、`to-questionnaire`、`to-spec`、`to-tickets`、`triage`、`wait-what`、`wayfinder`。完整名单以调用合同为准。

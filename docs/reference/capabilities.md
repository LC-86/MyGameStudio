# 当前能力与限制

MyGameStudio 3.0.1 是一个原生 Agent Skills 仓库，`skills/` 下正好 20 项技能。每项技能的权威说明是它自己的 `SKILL.md`；本页只给整体能力面与边界，不重复正文。

## 20 项技能

**用户入口**：只在你请求这类工作时启动。**按需方法**：你也可以直接调用，但通常由 Agent 在当前任务与授权适用时组合使用。

| 技能 | 上游对应 | 类型 | 职责 |
|---|---|---|---|
| `ask-gamestudio` | ask-matt | 用户入口 | 给一个当前最值得推进的下一步，不做项目总控 |
| `setup-gamestudio` | setup-matt-pocock-skills | 用户入口 | 记录项目协作约定、资料入口与资源管理方式 |
| `grill-gamestudio` | grill-me | 用户入口 | 一句话启动纯访谈 |
| `grill-gamestudio-docs` | grill-with-docs | 用户入口 | 访谈并按已确认决定更新术语、GDD、spec |
| `tasks-gamestudio` | to-tickets | 用户入口 | 按完整小成果拆票，声明依赖与人工验收 |
| `implement-gamestudio` | implement | 用户入口 | 完成本次指定的实现、自检、修复与交接 |
| `wayfinder-gamestudio` | wayfinder | 用户入口 | 跨会话梳理大型目标的决策地图 |
| `handoff-gamestudio` | handoff | 用户入口 | 写一份可携带的短交接说明 |
| `grilling-gamestudio` | grilling | 按需方法 | 分轮问清目标、规则、取舍与验证问题 |
| `domain-gamestudio` | domain-modeling | 按需方法 | 澄清并保存项目术语与重要决策理由 |
| `gdd-gamestudio` | 无（原创） | 按需方法 | 生成与增量维护整款游戏的策划与系统设计 |
| `spec-gamestudio` | to-spec | 按需方法 | 把已确认要求整理成精确的工作规格 |
| `tdd-gamestudio` | tdd | 按需方法 | 在公开行为接口上测试先行、小步实现 |
| `review-gamestudio` | code-review | 按需方法 | 同一成果的规范轴与需求轴两轴评审 |
| `debug-gamestudio` | diagnosing-bugs | 按需方法 | 用证据诊断具体异常并在授权内修复 |
| `prototype-gamestudio` | prototype | 按需方法 | 默认可玩的浏览器小游戏原型与体验证据 |
| `research-gamestudio` | research | 按需方法 | 带来源、适用条件与局限的事实调查 |
| `codebase-gamestudio` | codebase-design | 按需方法 | 设计当前改动的职责、状态与测试边界 |
| `merge-gamestudio` | resolving-merge-conflicts | 按需方法 | 解决已发生的 merge/rebase 冲突 |
| `docs-gamestudio` | writing-for-agents | 按需方法 | 正式工作资料与子代理委派的共同写作方法 |

上游基线、逐项适配记录见 [与 Matt Pocock skills 的关系](upstream.md) 与 [provenance/upstream.md](../../provenance/upstream.md)。安装时必须一起带上的技能和共享参考见 [技能依赖](../dependencies.md)。

## 8/12 的分界由三层调用控制承担

用户入口与按需方法的区分由三层调用控制承担（机制来自各宿主官方文档，本库未在宿主内实测）：

| 层 | 覆盖宿主 | 机制 |
|---|---|---|
| 1 | Claude Code、Grok Build、DSH | frontmatter 的 `disable-model-invocation: true`；技能描述不再进入模型上下文，只留用户显式入口 |
| 2 | Codex | 技能目录内的 `agents/openai.yaml`（`policy.allow_implicit_invocation: false`）；关闭隐式调用 |
| 3 | ZCode、Qoder | 这两个宿主未文档化任何调用控制字段，仍是写在描述与正文里的**指令层约定**，靠 Agent 阅读并遵守 |

因此：

- 前两层的隔离由各宿主解析器执行，本库不重建客户端适配层，也不自建调用运行时；
- 第三层不宣称强制隔离：在 ZCode、Qoder 里，某个入口仍可能被自行选中，需要更强边界时在项目自己的 `AGENTS.md` 里重申「用户入口只在我请求时启动」；
- 实际调用行为的检查结果（通过、失败、未运行）只在 [验证状态](../validation-v3.md) 里说明，本页不代填。

## 已退役能力与明确不覆盖的部分

`game-producer`、`game-init`、`game-design` 不是 3.0.0 的可执行入口，V2 的插件安装命令也已全部退出。去向与恢复方式见 [从 2.0.2 迁移到 3.0.0](../migration-v3.md) 与 [provenance/v2-retirement.md](../../provenance/v2-retirement.md)。

以下能力在 V3 没有等价实现，不要用新技能名义代替：

- **只读的全项目进度盘点**：目标、任务清单、可开工集合、边界任务的汇总报告。`ask-gamestudio` 只给一个下一步，不是项目总控。
- **旧项目资料迁移与安全切换**：批量迁移、待切换状态、核对后切换现行指针、回退。`setup-gamestudio` 只建立约定并做获准的最小文档修改，不迁移数据。
- **设计讨论的三段式接缝与设计快照**：计划、应用、版本节点快照。V3 的规则采纳由你在文档协作中确认。
- **专用记录运行层**：程序级幂等恢复、跨后端一致性、待写入索引、快照。V3 的任务读写用项目已有工具完成，见 [数据、写入与权限](data-and-permissions.md)。
- 未纳入的上游技能：`improve-codebase-architecture`、`triage`、`to-questionnaire`、`wizard`、`teach`、`wait-what`。全库架构扫描报告、完整来件分流、定向问卷、交互式向导生成、跨会话课程系统、独立重述入口都不在能力面内。

## 明确不宣称

- 不发布 npm 包、不提供自建安装器、不构建 tar 包；没有校验和验证流程。
- 不内置完整美术、音频、构建流水线或商店上架自动化。
- 不提供官方 MCP 服务或引擎适配。
- 不把本仓库的 `AGENTS.md` 当作用户游戏项目的默认规则。
- 引擎、模型、资源工具、设备与商店后台按项目另列；本库组织协作过程，不代替这些工具，也不代替你的重要决策。

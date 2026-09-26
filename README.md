# MyGameStudio

面向游戏开发的轻量化、可组合 Agent 技能库，通过官方 `skills` CLI 以原生 Agent Skills 方式安装。

**当前版本：3.0.3**（未发布：未打标签、未发布 Release。权威来源：[`VERSION`](VERSION)）

MyGameStudio 用清楚的目标、规则、边界、任务拆分、资料引用和验证要求，帮助 Agent 使用当前环境已有的工具完成游戏设计与制作。它不依赖自建的工作流运行时来限制每一步操作，也不强制所有游戏使用相同引擎、目录、任务平台或完整策划模板。

使用者负责目标、重要取舍和明确保留的体验判断；Agent 负责事实调查、方法选择、文档组织、实现步骤、自检，以及把必要的判断交接给使用者。

## 安装

完整使用需要**两个独立来源**：官方 `mattpocock/skills` 提供的共同写作方法 `writing-for-agents`，以及本仓库的 20 项技能。用户级命令排在前面，是本库推荐的范围；项目级命令必须在目标项目根目录执行。已经能从官方来源取得共同方法时只跳过第一步。

```bash
# 用户级：共同方法（已有时跳过）
npx skills@latest add mattpocock/skills --skill writing-for-agents --agent universal --copy -g -y

# 用户级：MyGameStudio 20 项
npx skills@latest add LC-86/MyGameStudio --skill '*' --agent universal --copy -g -y

# 项目级：在目标项目根目录执行
npx skills@latest add mattpocock/skills --skill writing-for-agents --agent universal --copy -y
npx skills@latest add LC-86/MyGameStudio --skill '*' --agent universal --copy -y

# 只列出可发现技能，不安装
npx skills@latest add LC-86/MyGameStudio --list
```

安装到哪个目录由官方 CLI 与你的选择决定。本仓库不提供安装器、不发布 npm 包、不构建 tar 包、不维护各 AI 开发工具的目录转换，也不分发、不镜像外部共同方法。

细节见 [docs/installation.md](docs/installation.md)：`-g`、`--copy` 等参数与项目级、用户级锁文件的当前行为只在 `skills` CLI 1.7.0 上核实。选择安装时的依赖组合见 [docs/dependencies.md](docs/dependencies.md)。从 2.0.2 插件版本切换见 [docs/migration-v3.md](docs/migration-v3.md)。

## 技能集合：20 项

本仓库源码树共 20 项技能（8 项用户入口、12 项按需方法）。此前的 `v3.0.2` 标签当时包含 21 项，其中一项是当时随包的 `writing-for-agents` 副本；`v3.0.1` 标签仍固定包含 20 项。历史身份不因本次收缩改写；外部共同方法 `writing-for-agents` 的随包副本已退役，不再由本仓库分发，改从官方 `mattpocock/skills` 独立安装。

**用户入口**由用户明确请求相应工作时启动，Agent 不自行开启该工作流程。**按需方法**在当前任务与授权适用时由 Agent 组合使用，用户也可以直接请求。

这条 8/12 分界由三层调用控制支撑（机制来自各宿主官方文档，本库未在宿主内逐一实测）：Claude Code、Grok Build 与 DSH 由 frontmatter 的 `disable-model-invocation: true` 强制，技能描述不再进入模型上下文，只留用户显式入口；Codex 由技能目录内的 `agents/openai.yaml`（`policy.allow_implicit_invocation: false`）强制，关闭隐式调用；ZCode 与 Qoder 未文档化任何调用控制字段，这条边界在那里仍是写在描述与正文里的**指令层约定**，也是全部宿主的兜底。需要更强约束时，在你自己的项目规则里重申该边界。这两层控制自 v3.0.1 起进入发布；`v3.0.0` 及更早标签安装到的版本不含它们。

### 用户入口（8）

| 技能 | 职责 |
|---|---|
| [ask-gamestudio](skills/ask-gamestudio/SKILL.md) | 只读导航：推荐一个当前最值得推进的下一步 |
| [setup-gamestudio](skills/setup-gamestudio/SKILL.md) | 补齐最小项目约定、资料入口与资源管理规则 |
| [grill-gamestudio](skills/grill-gamestudio/SKILL.md) | 一句话启动纯访谈 |
| [grill-gamestudio-docs](skills/grill-gamestudio-docs/SKILL.md) | 一句话启动带文档维护的访谈组合 |
| [tasks-gamestudio](skills/tasks-gamestudio/SKILL.md) | 按完整小成果拆任务，明确依赖与验收责任 |
| [implement-gamestudio](skills/implement-gamestudio/SKILL.md) | 实现当前工作，组织检查、修复与人机交接 |
| [wayfinder-gamestudio](skills/wayfinder-gamestudio/SKILL.md) | 梳理跨会话的重要未知与决策关系 |
| [handoff-gamestudio](skills/handoff-gamestudio/SKILL.md) | 写出可带走的工作接手说明 |

### 按需方法（12）

| 技能 | 职责 |
|---|---|
| [grilling-gamestudio](skills/grilling-gamestudio/SKILL.md) | 按前提分轮问清目标、规则、取舍与验证问题 |
| [domain-gamestudio](skills/domain-gamestudio/SKILL.md) | 校准项目概念，保存必要定义与重要决策理由 |
| [gdd-gamestudio](skills/gdd-gamestudio/SKILL.md) | 维护现行整体游戏设计与系统关系 |
| [spec-gamestudio](skills/spec-gamestudio/SKILL.md) | 整理本次具体交付与验证要求 |
| [tdd-gamestudio](skills/tdd-gamestudio/SKILL.md) | 在公开行为接口上小步测试驱动实现 |
| [review-gamestudio](skills/review-gamestudio/SKILL.md) | 对同一份成果做规范与需求两轴评审 |
| [debug-gamestudio](skills/debug-gamestudio/SKILL.md) | 用证据定位具体异常，在授权内修复并复验 |
| [prototype-gamestudio](skills/prototype-gamestudio/SKILL.md) | 默认交付真正可玩的浏览器小游戏原型 |
| [research-gamestudio](skills/research-gamestudio/SKILL.md) | 按深度做有来源、有局限说明的研究 |
| [codebase-gamestudio](skills/codebase-gamestudio/SKILL.md) | 设计当前职责、状态归属、接口与测试边界 |
| [merge-gamestudio](skills/merge-gamestudio/SKILL.md) | 按双方真实意图处理已发生的合并冲突 |
| [docs-gamestudio](skills/docs-gamestudio/SKILL.md) | 语义保真、通用子代理委派、游戏文档分流与专属资料取得条件 |

外部共同方法 [writing-for-agents](https://github.com/mattpocock/skills) 的随包副本已退役，不再由本仓库分发，改从官方 `mattpocock/skills` 独立安装：它负责通用正式资料写作与技能机制，各技能按宿主支持的技能名称取得它。

## 它们怎样组合

技能是可组合的方法，不是一条从头跑到尾的流水线。区分四种动作：**读取成果**、**使用方法**、**委派工作**、**推荐下一步**。技能名出现在文本里不等于它已经执行。

- 设计讨论：`grill-gamestudio-docs` 组合访谈与概念校准，按已确认决定的实际用途分别更新术语、GDD 与本次规格，边讨论边局部落盘。
- 交付工作：`tasks-gamestudio` 拆出完整小成果，`implement-gamestudio` 实现并按需组合 TDD、结构设计、诊断与评审，人工体验项未完成时不关单。
- 正式资料与委派：`writing-for-agents` 负责通用表达与技能机制，它来自官方 `mattpocock/skills`、按宿主支持的技能名称取得，不用跨安装范围的相对路径。`docs-gamestudio` 负责语义保真、通用委派与游戏文档分流，`tasks-gamestudio` 保留人机责任与验收交接。
- 路线不清：`wayfinder-gamestudio` 整理跨会话的关键未知，路线清楚即交接，不继续自动制作。

技能之间的依赖与共享资料归属见 [docs/dependencies.md](docs/dependencies.md)。

## 不做什么

- 不自建通用任务数据库、强制状态机、长期后台派工器，或每个技能对应一个程序的运行层。
- 不维护各 AI 开发工具的插件适配、市场清单与发布流程；唯一的宿主专属文件是 8 个用户入口各带的一份 `agents/openai.yaml`（Codex 调用策略，内容固定）。
- 加载技能不增加权限：写入、上传、付费、修改全局配置、提交与推送都按你的实际请求与宿主控制。
- 不修改你其他游戏项目的任务、资产、存档或外部存储。

## 文档

| 文件 | 内容 |
|---|---|
| [docs/README.md](docs/README.md) | 文档导航 |
| [docs/getting-started.md](docs/getting-started.md) | 从安装到首次使用 |
| [docs/installation.md](docs/installation.md) | 安装、更新与卸载 |
| [docs/dependencies.md](docs/dependencies.md) | 技能依赖与共享资料归属 |
| [docs/migration-v3.md](docs/migration-v3.md) | 从 2.0.2 迁移 |
| [docs/reference/capabilities.md](docs/reference/capabilities.md) | 能力边界与退役能力 |
| [docs/validation-v3.md](docs/validation-v3.md) | 本轮实际验证记录：通过、失败、未运行 |
| [docs/design/v3-overrides.md](docs/design/v3-overrides.md) | V3 对统一设计 v1 的明确覆盖 |
| [provenance/README.md](provenance/README.md) | 上游来源、适配记录与退役记录 |
| [CONTRIBUTING.md](CONTRIBUTING.md) | 贡献方式 |
| [CHANGELOG.md](CHANGELOG.md) | 版本历史 |
| [LICENSE](LICENSE) / [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md) | 许可与第三方来源 |

English summary: [README.en.md](README.en.md)。

## 验证状态

`v3.0.2`（上一版）发布时的结果保留为历史记录：`python3.12 -m pytest tests/ -q`（71 项）、文档校验（38 个文件、21 项技能）、固定来源同步、官方 `skills` CLI 1.7.0 原生安装（23/23）和来源切换矩阵；发布后又从 `v3.0.2` 标签全新克隆复跑安装检查（23/23），并从固定标签安装 21 项、核对来源锁。Codex 行为验证包含 14 个 ephemeral 会话与 2 个新接收方上下文。

3.0.3 **未发布**：未打标签、未发布 Release。本版实际执行的检查与未运行项统一记录在[验证记录](docs/validation-v3.md)，本页不代填。随包副本、固定来源同步与来源切换矩阵随本版退役，本版不再运行它们；20 项集合与两来源安装的静态检查、安装检查与行为验证状态同样以验证记录为准。

本地安装成功不等于远端 GitHub 安装成功。`@latest` CLI 命令读取默认分支，不是版本标签；`v3.0.2` 标签固定包含 21 项，`v3.0.1` 标签固定包含 20 项。2.0.2 及更早版本停止维护、不再修缺陷；需要旧内容请按固定引用 `LC-86/MyGameStudio#v2.0.2` 取得，切换步骤见 [docs/migration-v3.md](docs/migration-v3.md)。

## 许可

MIT。见 [LICENSE](LICENSE)。

方法改编自 Matt Pocock 的技能库，保留其 MIT 许可与署名。每个技能目录内都有一份 `LICENSE` 通知，因此按单项技能安装时许可信息仍然完整。详见 [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md)。

本项目由 LC-86 独立维护，不代表 Matt Pocock 或任何宿主厂商的官方背书。

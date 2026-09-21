# MyGameStudio

面向游戏开发的轻量化、可组合 Agent 技能库，通过官方 `skills` CLI 以原生 Agent Skills 方式安装。

**当前版本：3.0.0**（权威来源：[`VERSION`](VERSION)）

MyGameStudio 用清楚的目标、规则、边界、任务拆分、资料引用和验证要求，帮助 Agent 使用当前环境已有的工具完成游戏设计与制作。它不依赖自建的工作流运行时来限制每一步操作，也不强制所有游戏使用相同引擎、目录、任务平台或完整策划模板。

使用者负责目标、重要取舍和明确保留的体验判断；Agent 负责事实调查、方法选择、文档组织、实现步骤、自检，以及把必要的判断交接给使用者。

## 安装

```bash
# 发现并选择技能
npx skills@latest add LC-86/MyGameStudio

# 只列出可发现技能，不安装
npx skills@latest add LC-86/MyGameStudio --list

# 完整安装这套互相协作的技能（推荐）
npx skills@latest add LC-86/MyGameStudio --skill '*'
```

安装到哪个目录由官方 CLI 与你的选择决定。本仓库不提供安装器、不发布 npm 包、不构建 tar 包、不维护各 AI 开发工具的目录转换。

细节见 [docs/installation.md](docs/installation.md)。选择安装时的依赖组合见 [docs/dependencies.md](docs/dependencies.md)。从 2.0.2 插件版本切换见 [docs/migration-v3.md](docs/migration-v3.md)。

## 20 项技能

**用户入口**由用户明确请求相应工作时启动，Agent 不自行开启该工作流程。**按需方法**在当前任务与授权适用时由 Agent 组合使用，用户也可以直接请求。

这条 8/12 分界是写在描述与正文里的**指令层约定**。纯标准技能文本不具备跨宿主的强制调用隔离能力：本库不使用 `disable-model-invocation` 一类的宿主专属开关，因此无法阻止某个宿主自行选中一个用户入口。需要额外约束时，在你自己的项目规则里重申该边界。

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
| [docs-gamestudio](skills/docs-gamestudio/SKILL.md) | 所有正式工作资料与子代理委派的共同写作方法 |

## 它们怎样组合

技能是可组合的方法，不是一条从头跑到尾的流水线。区分四种动作：**读取成果**、**使用方法**、**委派工作**、**推荐下一步**。技能名出现在文本里不等于它已经执行。

- 设计讨论：`grill-gamestudio-docs` 组合访谈与概念校准，按已确认决定的实际用途分别更新术语、GDD 与本次规格，边讨论边局部落盘。
- 交付工作：`tasks-gamestudio` 拆出完整小成果，`implement-gamestudio` 实现并按需组合 TDD、结构设计、诊断与评审，人工体验项未完成时不关单。
- 正式资料与委派：`docs-gamestudio` 是共同写作方法，覆盖 GDD、spec、任务票、术语与决策记录、研究/测试/评审结论、交接说明、技能与项目规则，尤其是子代理派发说明。专业技能决定内容，它负责表达不失真。
- 路线不清：`wayfinder-gamestudio` 整理跨会话的关键未知，路线清楚即交接，不继续自动制作。

技能之间的依赖与共享资料归属见 [docs/dependencies.md](docs/dependencies.md)。

## 不做什么

- 不自建通用任务数据库、强制状态机、长期后台派工器，或每个技能对应一个程序的运行层。
- 不维护各 AI 开发工具的插件适配、市场清单、专属元数据与发布流程。
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

本轮实际执行并通过：静态检查 38 项、文档导航与版本一致性检查、隔离原生安装测试 19 项（官方 `skills` CLI 1.7.0）、9 个真实行为场景。1 个行为场景阻塞（研究场景受本机外网限制未取得结果）。

远端仓库来源的安装、固定标签安装与真实宿主内的发现与调用**未运行**。逐项证据、命令与局限见 [docs/validation-v3.md](docs/validation-v3.md)。

本地安装成功不等于 GitHub 远端 V3 安装成功；源码完成、本地安装通过、行为验证通过与远端发布完成是四种不同状态，不相互替代。远端默认分支尚未合入本版本时，`npx skills@latest add LC-86/MyGameStudio` 安装到的不是 3.0.0。

## 许可

MIT。见 [LICENSE](LICENSE)。

方法改编自 Matt Pocock 的技能库，保留其 MIT 许可与署名。每个技能目录内都有一份 `LICENSE` 通知，因此按单项技能安装时许可信息仍然完整。详见 [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md)。

本项目由 LC-86 独立维护，不代表 Matt Pocock 或任何宿主厂商的官方背书。

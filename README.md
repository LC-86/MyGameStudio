# MyGameStudio

**面向独立游戏开发者的 AI 游戏开发工作流插件。**

把游戏想法变成清晰设计、可执行任务和可验证成果。

MyGameStudio 在 Matt Pocock 工程技能的基础上，增加游戏项目接入、玩法与数值讨论，以及游戏制作进度与交付要求。你负责核心玩法和重要取舍，AI 根据明确的设计、任务和检查要求协助推进工作。

当前 **2.0.2** 组合包包含固定版本的 25 项 Matt 技能与 3 项游戏入口，并在安装包内携带本项目 MIT 许可与第三方说明。客户端与任务后端的实际支持程度见 [兼容性说明](docs/reference/compatibility.md)。

它不是游戏引擎，也不会仅凭一句话自动完成游戏上架。

[快速开始](docs/getting-started.md) ·
[安装](docs/installation/README.md) ·
[使用场景](docs/usage/workflows.md) ·
[能力与限制](docs/reference/capabilities.md) ·
[技能参考](docs/skills/README.md) ·
[示例](examples/README.md) ·
[贡献](CONTRIBUTING.md) ·
[来源与许可](THIRD_PARTY_NOTICES.md)

## 简介

MyGameStudio 适合用 AI 做游戏的个人开发者和小团队：你已经有（或即将有）一个游戏项目，需要把想法、设计和工程执行连起来，而不是每次从零聊天碰运气。

插件标识是 `mygamestudio`。产品显示名称是 `MyGameStudio`。技能标识保持现有小写名称（例如 `game-init`）。文档里的 Game-Producer 等是显示名称，不是新的技能别名。

## 为什么需要它

直接让 AI 写代码，容易把未决定的玩法写进工程，也难以核对“做到哪了”。本插件补上三件事：

1. **想法澄清**：先说清当前最小玩法闭环，再谈实现。
2. **设计与工程衔接**：已采纳规则由你主动整理成规格和任务，而不是对话自动变成正式要求。
3. **有效记录和可验证交付**：进度来自真实记录；可玩成果要有运行入口和实际检查。

## 能做什么

三个游戏入口：

- **Game-Init**（`game-init`）：接手已有游戏时先只读分析，列出复用、新增和待你决定的事项；确认后才写入接入资料。
- **Game-Design**（`game-design`）：讨论玩法、数值和体验。讨论不会自动成为正式规格。
- **Game-Producer**（`game-producer`）：按真实记录说明目标、任务、缺口和下一步。状态查询只读，也不会自动串调需要你亲自启动的工程技能。

继承自 Matt 的常用能力（需你主动调用）：`setup-matt-pocock-skills`、`to-spec`、`to-tickets`、`implement`、`code-review` 等。完整索引见 [技能参考](docs/skills/README.md)。

美术、音频、构建和试玩可以写进任务与检查要求，但插件没有内置完整自动生产工具。

## 快速开始

1. 按 [安装说明](docs/installation/README.md) 选择客户端，装入**完整插件**（不要只复制单个 `SKILL.md`）。
2. 确认能发现 28 项技能（Matt 正式 25 项 + 三个游戏入口）。
3. 在游戏项目里主动调用 `setup-matt-pocock-skills`，配置该项目的议题追踪、标签和领域文档。
4. 用 `game-init` 做一次**只读**接入分析，确认后再写入。

逐步说明：[从安装到第一次有效使用](docs/getting-started.md)。

## 安装

默认入口是 [GitHub Release 的完整插件包](https://github.com/LC-86/MyGameStudio/releases)。仓库源码用于学习、贡献和构建。

| 客户端 | 文档 | 2.0.2 真实安装 |
| --- | --- | --- |
| Codex | [codex.md](docs/installation/codex.md) | 隔离 CLI 安装已验证；日常会话未验证 |
| ZCode | [zcode.md](docs/installation/zcode.md) | 未验证 |
| Grok Build | [grok-build.md](docs/installation/grok-build.md) | 未验证 |

ZCode 使用本地插件源时需要 `.zcode-plugin/plugin.json` 与 `marketplace.json`。
Grok Build 可将插件放在 `~/.grok/plugins`，或用 `--plugin-dir` 指向解包目录。
隔离目录验证不要写进真实用户目录；步骤见各安装页。

不要把 `npx skills@latest add ...` 当作本插件的安装方式。技能会引用 `internal/`、`records/` 等兄弟目录，技能安装器是否完整保留这些文件尚未验证。

## 典型工作流

这是地图，不是每项小改动都必须走完的流水线。关键阶段由你调用。

| 你现在要做的事 | 用哪个入口 |
| --- | --- |
| 接手或补齐已有游戏的工作流资料 | `game-init`（先只读） |
| 讨论当前最小玩法闭环 | `game-design` |
| 查看真实进度 | `game-producer`（只读） |
| 把已采纳内容写成规格 | 你主动调用 `to-spec` |
| 把较大范围拆成任务 | 你主动调用 `to-tickets` |
| 按任务实现并检查 | 你主动调用 `implement`、`tdd`、`code-review` |

详见 [常用工作流](docs/usage/workflows.md) 和 [接入已有游戏](docs/usage/existing-projects.md)。

## 示例

[接入已有游戏的只读分析](examples/existing-game-change/README.md) 使用仓库里可复查的样例项目，给出可复制的调用文案。文中的预期输出是**示意**，不是本环境实测截图。

另见 [最小玩法闭环](examples/first-playable-loop/README.md)。

## 能力边界

- 不代替游戏引擎、模型、资源工具或商店后台。
- 游戏记录层目前是本地 Markdown 或 GitHub Issues，每项目只选一种。不要假定 Linear 已被本插件游戏层支持。
- 无提交授权时，`implement` 会保留未提交成果。
- 2.0.2 已在本 Linux 环境用 Codex CLI 0.154.0 做隔离 `plugin add` / `remove`（无用户凭据、不写日常 `~/.codex/`）。新会话技能发现与只读调用**未验证**。ZCode / Grok Build 仍未验证。
- 不会仅凭一句话自动完成上架。

完整列表：[能力与限制](docs/reference/capabilities.md)、[数据与权限](docs/reference/data-and-permissions.md)。

## 与 Matt 的关系

由 LC-86 独立维护，基于固定版本的 Matt Pocock skills（1.2.3，提交 `3cca18b368ae95cdbdebbff572ccafa662551015`）。
25 项通用技能来自上游；三个游戏入口和游戏阶段资料是本项目组合。
重要适配见 [upstream.md](docs/reference/upstream.md) 与 [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md)。

## 参与与许可

- 问题与建议：GitHub Issues（请按模板填写，不要发送令牌）
- 贡献：[CONTRIBUTING.md](CONTRIBUTING.md)
- 安全报告：[SECURITY.md](SECURITY.md)
- 本项目原创部分：[LICENSE](LICENSE)（MIT）
- 第三方：[THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md)

维护本仓库时阅读 [AGENTS.md](AGENTS.md)。那是插件开发协作说明，不是用户游戏项目的工作流入口。

当前源码与仓库内安装包版本为 **2.0.2**。GitHub Release `v2.0.1` 仍是上一份已发布资产，字节未改写。发布状态、安装验证状态和已知限制不是同一件事。

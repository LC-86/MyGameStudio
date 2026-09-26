# 第三方来源与许可

MyGameStudio 由 **LC-86** 独立维护，方法改编自 Matt Pocock 的技能库。这不表示 Matt Pocock 或任何宿主厂商对本项目作了官方背书。

## 本项目

| 项 | 内容 |
|---|---|
| 维护者 | LC-86 |
| 许可 | MIT，见 [LICENSE](LICENSE) |
| 当前版本 | 3.0.3（未发布，未打标签、未发布 Release），权威来源 [VERSION](VERSION) |
| 交付形态 | 原生 Agent Skills 仓库，根目录 `skills/<技能名>/SKILL.md`，通过官方 `skills` CLI 安装 |
| 原创范围 | `gdd-gamestudio`、GameStudio 专属文档分流与增量协作、人机责任与验收交接、本仓库文档与检查 |

## Matt Pocock skills

| 项 | 内容 |
|---|---|
| 来源项目 | [mattpocock/skills](https://github.com/mattpocock/skills) |
| 作者 | Matt Pocock |
| 许可 | MIT，版权 `Copyright (c) 2026 Matt Pocock` |
| 许可副本 | [provenance/v2-plugin-provenance/licenses/mattpocock-skills-LICENSE.txt](provenance/v2-plugin-provenance/licenses/mattpocock-skills-LICENSE.txt) |
| V3 方法基线 | 提交 `c55ee46073ed923f86ce59a5eb3b6d895095d1b7`，当时通过 fork [LC-86/mattpocockskills](https://github.com/LC-86/mattpocockskills)（其 `upstream` remote 指向 mattpocock/skills）只读读取，上游插件声明版本 1.2.3；这是基线读取记录，不是现行安装来源 |
| V2 曾钉住的提交 | `3cca18b368ae95cdbdebbff572ccafa662551015`（2.0.2 的分发基线，两个提交的差异未按文件逐一对照） |
| 纳入范围 | 本仓库 20 项中的 19 项游戏技能改编自上游；`gdd-gamestudio` 为原创。外部共同方法 `writing-for-agents` 不随本仓库分发，由用户从官方 `mattpocock/skills` 独立安装 |
| 上游共同方法 | `writing-for-agents`、其 `SKILL-MECHANICS.md` 与通用委派参考的权威源是官方 [mattpocock/skills](https://github.com/mattpocock/skills)；本仓库不携带副本、不提供来源切换，也不为它保留第二份可编辑权威源 |

名称映射、逐项适配记录、可能损失与核对方式见 [provenance/upstream.md](provenance/upstream.md) 与 [provenance/adaptation-log.md](provenance/adaptation-log.md)。上游 MIT 许可与 Matt Pocock 署名在本文件中保留；随包副本的退役与取代关系见 [provenance/upstream.md](provenance/upstream.md) 的追加记录。GameStudio 文档分流、人机责任和验收交接继续由专属技能拥有。本库 8 个用户入口的三层控制见 [当前能力与限制](docs/reference/capabilities.md)。

### 许可随技能分发

每个技能目录内有一份 `LICENSE`，包含 MIT 许可全文、`Copyright (c) 2026 LC-86 / MyGameStudio` 与 `Copyright (c) 2026 Matt Pocock` 两条声明（`gdd-gamestudio` 为原创，只含前者），以及该技能的上游来源说明。

原因是按单项技能安装时，仓库根的 `LICENSE` 与本文件不会随之安装，接收方能看到的全部许可信息只有技能目录内的内容。

## 未纳入

- 上游 `misc/`、`in-progress/`、`deprecated/` 中的技能
- 上游的 `improve-codebase-architecture`、`triage`、`to-questionnaire`、`wizard`、`teach`、`wait-what`
- 2.0.2 的三个游戏入口 `game-producer`、`game-init`、`game-design`

去向与明确未覆盖的能力见 [docs/migration-v3.md](docs/migration-v3.md) 与 [provenance/v2-retirement.md](provenance/v2-retirement.md)。

## 官方资料

以下外部文档只用于格式、宿主事实与验证原则，不为本项目的架构取舍背书。其内容会变化，实施与发布时应重新核对。

- Agent Skills 规范：<https://agentskills.io/specification>
- Claude Code 技能：<https://code.claude.com/docs/en/skills>
- OpenAI 技能编写：<https://developers.openai.com/zh-Hans/docs/build-skills>
- Claude Code 子代理：<https://code.claude.com/docs/en/sub-agents>

## 历史材料

[provenance/v2-plugin-provenance/](provenance/v2-plugin-provenance/) 保留 2.0.2 插件包的上游 manifest 与逐文件指纹，作为历史记录。其中的相对链接指向已移除的 V2 目录结构，不再可达；完整 V2 树可从提交 `5e3cfbfa3e217a9182690237955734109b982235` 恢复。

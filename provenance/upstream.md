# 上游基线与名称映射

## V3 方法基线

| 项 | 内容 |
|---|---|
| 上游项目 | [mattpocock/skills](https://github.com/mattpocock/skills) |
| 作者 | Matt Pocock |
| 本次实际读取的仓库 | [LC-86/mattpocockskills](https://github.com/LC-86/mattpocockskills)（上游的 fork，`upstream` remote 指向 mattpocock/skills），以只读 checkout 方式读取，HEAD 即固定提交且工作树干净 |
| 固定提交 | `c55ee46073ed923f86ce59a5eb3b6d895095d1b7` |
| 上游插件声明版本 | 1.2.3 |
| 许可 | MIT，`Copyright (c) 2026 Matt Pocock` |
| 许可副本 | [v2-plugin-provenance/licenses/mattpocock-skills-LICENSE.txt](v2-plugin-provenance/licenses/mattpocock-skills-LICENSE.txt) |

V2（2.0.2）钉住的是同一上游项目的较早提交 `3cca18b368ae95cdbdebbff572ccafa662551015`。V3 的方法基线改为 `c55ee46`，两个提交的差异未按文件逐一对照；本次适配以 `c55ee46` 的正文为准，V2 的分发正文不作为 V3 的输入。

上游目录采用 bucket 分层（`skills/engineering/`、`skills/productivity/` 等），随包文件是与 `SKILL.md` 同级的扁平 `.md`。V3 改为根目录 `skills/<name>/`，随包资料统一放在 `references/` 与 `templates/` 下。

## 共同写作方法的固定分发（v3.0.2 及更早形态；现行见文末退役记录）

本节记录 `v3.0.2` 及更早的固定分发形态，已随 3.0.3 整体退役；现行来源与用户取得方式见文末「[随包共同方法副本的退役（3.0.3，Issue #93，未发布）](#随包共同方法副本的退役303issue-93未发布)」一节。以下内容保持当时的事实，不代表现行来源。

Issue #86 交付的通用方法单独保留原名，不混入 20 项游戏技能改编：

| 项 | 内容 |
|---|---|
| 可编辑权威源 | `LC-86/mattpocockskills` 的 `skills/productivity/writing-for-agents/` |
| 固定源提交 | `f3c726f275fa1ac59fef33732e527dded6d62479` |
| 随包目录 | `skills/writing-for-agents/` |
| 逐文件来源、映射及摘要 | `skills/writing-for-agents/SOURCE.md`（该文件已随副本删除）与随包 `SHA256SUMS` |
| 包装规则 | `SKILL.md` 只增加标准 `license: MIT` 字段；正文与 mechanics/委派参考由固定源生成；上游 MIT 正文完整保留并附加本发行署名 |
| 排除项 | 上游 `agents/openai.yaml` 不随包；此项是按需方法，遵循本库 8 个入口/13 个方法边界 |

分发副本从固定提交生成，不作为第二个可编辑权威源。`scripts/sync-writing-for-agents.py` 从固定源取文件、校验上游与随包摘要；普通安装没有源仓库、网络或脚本依赖。

## 名称与来源映射

| V3 技能 | 上游原技能 | 上游路径（相对 `skills/`） | 关系 |
|---|---|---|---|
| ask-gamestudio | ask-matt | engineering/ask-matt | 改写 |
| setup-gamestudio | setup-matt-pocock-skills | engineering/setup-matt-pocock-skills | 改写 |
| grilling-gamestudio | grilling | engineering/grilling | 改写 |
| domain-gamestudio | domain-modeling | engineering/domain-modeling | 改写 |
| grill-gamestudio | grill-me | productivity/grill-me | 保留一句话组合入口 |
| grill-gamestudio-docs | grill-with-docs | productivity/grill-with-docs | 保留一句话组合入口 |
| gdd-gamestudio | 无 | 无 | MyGameStudio 原创 |
| spec-gamestudio | to-spec | engineering/to-spec | 改写 |
| tasks-gamestudio | to-tickets | engineering/to-tickets | 改写 |
| implement-gamestudio | implement | engineering/implement | 改写 |
| tdd-gamestudio | tdd | engineering/tdd | 改写 |
| review-gamestudio | code-review | engineering/code-review | 改写 |
| debug-gamestudio | diagnosing-bugs | engineering/diagnosing-bugs | 改写 |
| prototype-gamestudio | prototype | engineering/prototype | 改写 |
| research-gamestudio | research | engineering/research | 改写 |
| wayfinder-gamestudio | wayfinder | engineering/wayfinder | 改写 |
| handoff-gamestudio | handoff | productivity/handoff | 改写 |
| codebase-gamestudio | codebase-design | engineering/codebase-design | 改写 |
| merge-gamestudio | resolving-merge-conflicts | engineering/resolving-merge-conflicts | 改写 |
| docs-gamestudio | writing-for-agents | productivity/writing-for-agents | 改写并扩大定位 |
| writing-for-agents | writing-for-agents | productivity/writing-for-agents | 固定源副本；添加标准许可字段和许可发行署名 |

`docs-gamestudio` 保留其 GameStudio 名称，拥有游戏文档分流与增量协作，并在 Issue #90 的兼容接缝中重新拥有一度迁出的语义保真与通用子代理委派；通用表达与技能机制仍由 `writing-for-agents` 拥有。上游 `SKILL-MECHANICS.md` 与通用委派参考现在随固定副本分发；发行时按固定规则在技能机制中补充 Codex 用户入口必须使用 `agents/openai.yaml` 调用策略的说明，其余上游机制文字保持不变。消费者不再用同级相对路径取得 `writing-for-agents`，改为按宿主支持的技能名称取得，见 [能力与限制](../docs/reference/capabilities.md)。原 V3 游戏技能的宿主调用开关历史见 [adaptation-log.md](adaptation-log.md)。

## 未纳入的上游技能

按统一设计 v1 第 2.3 节的范围决定，以下六项不进入本仓库技能集合（该集合在 3.0.3 收缩后为 20 项，见文末退役记录）。消费者不保留对它们的硬调用。

| 上游技能 | 处理 | 没有被暗中声称已替代的能力 |
|---|---|---|
| improve-codebase-architecture | 暂缓 | 主动全库架构扫描与候选改进报告 |
| triage | 暂缓 | 持续处理外部请求、报告和 PR 的完整分流流程 |
| to-questionnaire | 暂缓 | 面向特定外部收件人的定向问卷 |
| wizard | 不独立发布 | 自动生成交互式 Bash 向导及其配置操作 |
| teach | 不纳入 | 跨会话课程、练习与学习记录系统 |
| wait-what | 不独立发布 | 重述作为日常沟通能力保留，不另设入口 |

上游 `misc/`、`in-progress/`、`deprecated/` 中的技能一律不纳入。

## 许可处理方式

每个改编或分发的技能目录内有一份 `LICENSE`，包含完整 MIT 许可、原作者声明、MyGameStudio 发行署名和该技能来源。根 `LICENSE` 与 `THIRD_PARTY_NOTICES.md` 不会随单项技能安装。`writing-for-agents` 的上游许可正文由生成器逐字保留，署名以确定的发行附注追加。

`gdd-gamestudio` 是 MyGameStudio 原创、没有上游对应技能。

历史版本号、上游原名和许可内容原样保留，不做无差别全库字符串替换。

## 随包共同方法副本的退役（3.0.3，Issue #93，未发布）

本节只追加，不改写以上各节的历史记录。以上「共同写作方法的固定分发」一节描述的是 `v3.0.2` 及更早的分发形态；3.0.3 实施后该形态整体退役：

| 项 | 退役前（3.0.2 及更早） | 现行（3.0.3） |
|---|---|---|
| 随包目录 | `skills/writing-for-agents/`，含 `SOURCE.md`、`SHA256SUMS`、`LICENSE` | 已删除；本仓库不再分发该方法 |
| 可编辑权威源 | LC-86 fork 的 `skills/productivity/writing-for-agents/`，固定源提交 `f3c726f275fa1ac59fef33732e527dded6d62479` | 官方 [mattpocock/skills](https://github.com/mattpocock/skills)；上述固定提交作为上一版的历史事实保留 |
| 同步生成器 | `scripts/sync-writing-for-agents.py` | 已删除，且不再需要 |
| 安装核验检查器 | `scripts/verify-writing-for-agents-install.py` | 已删除；实际加载版本只在目标宿主核实 |
| 来源切换矩阵 | `scripts/install-source-matrix-test.sh` | 已删除；不再有第二个来源可切 |
| 用户取得方式 | 随本仓库 21 项一起安装（8 用户入口、13 按需方法） | 从官方 `mattpocock/skills` 独立安装，按宿主支持的技能名称取得；本仓库集合为 20 项（8 用户入口、12 按需方法） |

名称映射表中 `writing-for-agents` 一行记录的是 3.0.2 及更早的分发形态，现已不在本仓库集合内；`docs-gamestudio` 仍是语义保真与通用子代理委派的唯一所有者。逐项退役说明见 [adaptation-log.md](adaptation-log.md) 的 Issue #93 一节，实际检查结果见 [验证状态](../docs/validation-v3.md)。

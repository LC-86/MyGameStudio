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

## 共同写作方法的固定分发

Issue #86 交付的通用方法单独保留原名，不混入 20 项游戏技能改编：

| 项 | 内容 |
|---|---|
| 可编辑权威源 | `LC-86/mattpocockskills` 的 `skills/productivity/writing-for-agents/` |
| 固定源提交 | `f3c726f275fa1ac59fef33732e527dded6d62479` |
| 随包目录 | `skills/writing-for-agents/` |
| 逐文件来源、映射及摘要 | [skills/writing-for-agents/SOURCE.md](../skills/writing-for-agents/SOURCE.md) 与随包 `SHA256SUMS` |
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

`docs-gamestudio` 保留其 GameStudio 名称，但只拥有游戏文档分流与增量协作；此前重复的通用写作与委派内容改由 `writing-for-agents` 唯一拥有。上游 `SKILL-MECHANICS.md` 与通用委派参考现在随固定副本分发。原 V3 游戏技能的宿主调用开关历史见 [adaptation-log.md](adaptation-log.md)。

## 未纳入的上游技能

按统一设计 v1 第 2.3 节的范围决定，以下六项不进入 21 项集合。消费者不保留对它们的硬调用。

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

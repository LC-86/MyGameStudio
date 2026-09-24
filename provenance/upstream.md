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

上游的 `SKILL-MECHANICS.md`（writing-for-agents 的宿主机制分支）没有对应技能。通用写作杠杆并入 `docs-gamestudio`；与宿主专属调用开关有关的内容在 V3 退出，此后（#81）本库在 8 个用户入口上重新使用了 frontmatter 的 `disable-model-invocation` 与 `agents/openai.yaml` 的 `policy.allow_implicit_invocation`，见 [adaptation-log.md](adaptation-log.md)。

## 未纳入的上游技能

按统一设计 v1 第 2.3 节的范围决定，以下六项不进入 V3 的 20 项集合。消费者不保留对它们的硬调用。

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

每个技能目录内有一份 `LICENSE`，包含 MIT 许可全文、两条版权声明（LC-86 / MyGameStudio 与 Matt Pocock）以及该技能的上游来源说明。原因是按单项技能安装时，仓库根的 `LICENSE` 与 `THIRD_PARTY_NOTICES.md` 不会随之安装，接收方看到的许可信息只有技能目录内的内容。

`gdd-gamestudio` 的许可通知标明它是 MyGameStudio 原创、没有上游对应技能。

历史版本号、上游原名和许可内容原样保留，不做无差别全库字符串替换。

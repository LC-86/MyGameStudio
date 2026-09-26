# 与 Matt Pocock skills 的关系

MyGameStudio 由 **LC-86** 独立维护，方法基线来自 Matt Pocock 的技能库。它不是 Matt Pocock 的产品，也不是任何 AI 开发工具的官方组件。

## 原有游戏技能方法基线

| 项 | 内容 |
|---|---|
| 上游项目 | [mattpocock/skills](https://github.com/mattpocock/skills) |
| 本次实际读取的仓库 | [LC-86/mattpocockskills](https://github.com/LC-86/mattpocockskills)（上游的 fork，其 `upstream` remote 指向 mattpocock/skills），只读 checkout，HEAD 即固定提交且工作树干净 |
| 固定提交 | `c55ee46073ed923f86ce59a5eb3b6d895095d1b7` |
| 许可 | MIT，`Copyright (c) 2026 Matt Pocock` |

V2（2.0.2）钉住的是同一上游项目的较早提交 `3cca18b368ae95cdbdebbff572ccafa662551015`。两个提交的差异没有按文件逐一对照；V3 的适配以 `c55ee46` 的正文为准，V2 的分发正文不作为 V3 输入。升级基线需要先评估再采用，不把 `latest` 直接写进本库。

### 共同写作方法的固定分发

`writing-for-agents` 保持上游原名与通用用途，编辑权威源位于 LC-86 fork。GameStudio 随包副本固定到提交 `f3c726f275fa1ac59fef33732e527dded6d62479`；文件映射、逐文件源与分发摘要，以及标准 frontmatter 和许可包装规则见技能目录内的 [SOURCE.md](../../skills/writing-for-agents/SOURCE.md) 与 [SHA256SUMS](../../skills/writing-for-agents/SHA256SUMS)。源 `SKILL.md` 主体、`SKILL-MECHANICS.md` 与通用委派参考按确定规则校验；源 `agents/openai.yaml` 不随包，因为该方法属于本库 13 项按需方法。

随包副本是**过渡形态**。GameStudio 把它当成外部共同方法：只按宿主支持的技能名称取得，不使用跨安装范围的相对路径，语义保真与通用子代理委派改由 `docs-gamestudio` 拥有。这样在后续收缩删除该副本时，消费者不需要改动取得方式，正式资料也不会丢失保真约束与委派方法。收缩与最终删除属于后续工单，本版不改变发行集合。

## 权威记录在哪里

- [provenance/upstream.md](../../provenance/upstream.md)：V3 游戏技能基线、21 项的名称与来源映射表、未纳入的上游技能、许可处理方式
- [provenance/adaptation-log.md](../../provenance/adaptation-log.md)：每项技能从原版到 V3 的实际改动、依据、可能损失与核对方式
- [THIRD_PARTY_NOTICES.md](../../THIRD_PARTY_NOTICES.md)：许可摘要

映射表不在本页重复，以 provenance 为准。

## 继承了什么

上游的核心方法思想被保留：分轮访谈澄清、术语与决策记录、规格整理、按完整成果拆票、测试先行、两轴评审、证据驱动诊断、可玩原型、带来源的研究、跨会话路线梳理、交接说明、深模块设计、合并冲突解决，以及为 Agent 写作的方法杠杆。

## 适配了什么

- **命名**：20 项游戏专属技能带 `-gamestudio` 后缀。通用 `writing-for-agents` 保留上游原名，固定副本由 GameStudio 自己分发；`gdd-gamestudio` 是原创。
- **布局**：从上游的 bucket 分层与扁平随包文件，改为根目录 `skills/<技能名>/SKILL.md`，随包资料统一放在 `references/` 与 `templates/` 下。
- **共享资料单一所有者**：共用参考只存一份，归属明确的所有者技能，消费者用同级相对路径引用；外部共同方法按宿主支持的技能名称取得，不写成本库内的相对路径。
- **调用措辞中性化**：不假定宿主存在固定名称的调用工具；读取、使用方法、委派工作、推荐下一步是四种不同动作。
- **调用控制分层**：上游用于阻止模型自行触发的宿主专属元数据曾整体删除，后按 #81 恢复为三层机制：8 个用户入口的 frontmatter `disable-model-invocation: true` 与 `agents/openai.yaml` 的 `policy.allow_implicit_invocation: false`，以及在 ZCode、Qoder 内靠描述与正文兜底。字段名与上游一致，本库仍是可安装的标准 Agent Skills 文本，见 [当前能力与限制](capabilities.md)。
- **游戏化**：设计讨论、GDD 维护、玩法原型、资源与工程约定、人机验收责任等按游戏项目场景重写。

## 许可处理

每个技能目录内有一份 `LICENSE`，包含 MIT 许可全文、两条版权声明（LC-86 / MyGameStudio 与 Matt Pocock）以及该技能的上游来源说明。原因是按单项技能安装时，仓库根的 `LICENSE` 与 `THIRD_PARTY_NOTICES.md` 不会随之安装。历史版本号、上游原名与许可内容原样保留，不做无差别全库字符串替换。

## 不要做的事

- 用 `npx skills@latest add mattpocock/skills` 代替本库：上游正文没有游戏适配，也不包含本库的共享参考。
- 把 21 项都写成 MyGameStudio 原创，或把游戏专属要求塞进通用 `writing-for-agents`。
- 用同级相对路径取得外部共同方法：随包副本退出集合后该路径立即失效，正式资料会连带丢失共同方法。
- 未评估就把基线升到 `latest`，或把已退役的旧入口名当作可执行别名。

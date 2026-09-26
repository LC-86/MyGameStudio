# 从安装到第一次有效使用

目标：在你的 AI 开发工具里发现这套技能，完成第一次**不修改游戏文件**的会话。

安装细节、安装后确认与卸载在 [安装](installation.md)；这里只给顺序和一段可直接发送的调用文案。哪些安装路径已经真实测试、哪些未运行，见 [验证状态](validation-v3.md)。

## 1. 安装

完整使用需要两个来源：官方 `mattpocock/skills` 的共同写作方法，以及本仓库的 20 项技能。用户级安装排在前面（推荐）；项目级作为替代，命令在目标项目根目录执行。两个来源都要装，只有「已有官方共同方法」时跳过第一步。

```bash
# 用户级：共同方法（已有时跳过）
npx skills@latest add mattpocock/skills --skill writing-for-agents --agent universal --copy -g -y

# 用户级：MyGameStudio 20 项
npx skills@latest add LC-86/MyGameStudio --skill '*' --agent universal --copy -g -y

# 项目级替代：在目标项目根目录执行，去掉 -g
npx skills@latest add mattpocock/skills --skill writing-for-agents --agent universal --copy -y
npx skills@latest add LC-86/MyGameStudio --skill '*' --agent universal --copy -y
```

`-g`、`-y`、`--agent universal`、`--copy` 与项目级、用户级锁文件的当前行为只在 `skills` CLI **1.7.0** 上核实，其它版本以实际输出为准；安装范围、安装后确认与卸载的完整说明见 [安装](installation.md)。

推荐完整安装 20 项（`--skill '*'`）：全部是游戏专属的 `-gamestudio` 技能。`v3.0.2` 标签当时包含 21 项，其中一项是当时随包的 `writing-for-agents` 副本；`v3.0.1` 标签仍固定包含 20 项。选择安装可能缺少依赖，组合清单在 [技能依赖](dependencies.md)；安装范围与项目级命令见 [安装](installation.md)。

成功标准：整合后的宿主技能目录里能看到 20 个 `-gamestudio` 名称；每项都有 `SKILL.md`、所需 `references/` 或 `templates/` 以及独立完整的 `LICENSE`。8 个用户入口另有一份 `agents/openai.yaml`；12 个按需方法不带宿主开关或宿主文件。外部共同方法 `writing-for-agents` 要在它自己的安装范围里单独确认已从官方来源装好。

## 2. 第一次会话：先问下一步

在**游戏项目**仓库里开会话，直接说明你要做什么。想知道该从哪开始时用 `ask-gamestudio`：

```text
请使用 ask-gamestudio。

我想继续推进当前游戏项目，但不确定现在最该做哪一件事。
先只读查看必要资料，给我一个下一步建议：承担它的技能、完成标志，
以及一段我可以直接发送的调用指令。
这一轮不要修改任何文件，也不要开始实现。
```

成功标准：它给一个下一步而不是一串候选；说明实际读了哪些资料；没有写入文件；没有把未运行的检查说成已通过。

## 3. 记录项目约定

新项目或从未整理过协作约定的项目，用 `setup-gamestudio`：

```text
请使用 setup-gamestudio 为当前游戏项目补齐协作约定。

先探查实际情况，提出建议清单等我确认，再做获准的最小文档修改并回读。
约定包括：任务来源、分流约定、术语与决策资料入口、游戏资料与资源管理方式。
不要执行引擎初始化、不要做资源制作或清理，也不要写入远端。
```

它记录的是**你这个项目**的真实约定，供其余技能沿用。约定已经完整时重复运行不改文件。

## 4. 讨论一个设计问题

需要边讨论边把已采纳内容落到资料里，用 `grill-gamestudio-docs`：

```text
请使用 grill-gamestudio-docs。

我要把体力系统从按次数扣除改成随时间恢复，先分轮问清楚再更新资料。
已经确认的决定请按用途更新术语、GDD 或本次工作规格，写入前告诉我改哪个文件。
这一轮不要开始编码，也不要发布任务。
```

只想要一场纯访谈、暂时不落盘，用 `grill-gamestudio`。

## 5. 之后按需进行

`tasks-gamestudio` 把已明确的工作拆成票，`implement-gamestudio` 完成一次实现，`wayfinder-gamestudio` 梳理需要跨会话澄清的大目标，`handoff-gamestudio` 写交接说明。

其余 12 项是**按需方法**：`grilling`、`domain`、`gdd`、`spec`、`tdd`、`review`、`debug`、`prototype`、`research`、`codebase`、`merge`、`docs`。你不需要记住它们，也不需要逐个启动；当前任务和授权适用时由 Agent 组合使用。通用写作方法是外部依赖 `writing-for-agents`，从官方 `mattpocock/skills` 安装，不属于本仓库的 20 项。

实际组合方式见 [常用工作流](usage/workflows.md)；每项技能的权威说明是 `skills/<技能名>/SKILL.md`。

## 常见误解

- 用户入口不是自动串起来的：一个入口完成即停，不代替你启动下一个入口。
- **推荐**下一步和**开始**下一步是两个动作。`ask-gamestudio` 只推荐。
- 加载技能不等于获得权限：写入、提交、推送、上传、付费和全局配置改动仍各自需要授权，见 [数据、写入与权限](reference/data-and-permissions.md)。
- 8 项用户入口与 12 项按需方法的区分由三层调用控制承担：Claude Code、Grok Build、DSH 靠 frontmatter 的 `disable-model-invocation: true`，Codex 靠技能目录内的 `agents/openai.yaml`，ZCode、Qoder 靠描述与正文里的指令层约定，见 [当前能力与限制](reference/capabilities.md)。

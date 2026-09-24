# V3 对统一设计 v1 的明确覆盖

本文件记录本次 V3.0.0 实施相对 [unified-design-v1.md](unified-design-v1.md) 的覆盖决定。设计文件按原始身份保留，不按本次覆盖改写；两者冲突时以本文件为准。

优先级：**本次执行要求 > 统一设计 v1 与整合清单 > 较早的单技能草案 > 旧版 MyGameStudio 实现。**

## 覆盖 1：只交付原生 Agent Skills 仓库

**设计 v1：** 13.1 节建议 `plugin/skills/` 布局并保留客户端要求的清单；13.3 节要求调用配置分别适配宿主，首轮优先核对 Claude Code 与 Codex。5.4 节记录 Claude 用 `disable-model-invocation: true`、Codex 用 `policy.allow_implicit_invocation: false`。

**V3：** 唯一标准技能源码布局是根目录 `skills/<技能名>/SKILL.md`，通过官方 `skills` CLI 安装。取消全部 AI 开发工具的插件适配、插件市场清单、专属元数据、安装器与发布流程。frontmatter 只使用标准字段 `name`、`description`、`license`，必要时 `compatibility`、`metadata`。具体安装目标目录由官方 CLI 与使用者选择。

**影响：** 8 个用户入口与 12 个按需方法保留为**行为边界**，写在 description 与正文里，不再宣称纯标准技能文本具有跨宿主的强制调用隔离能力。宿主无法强制控制时如实披露，不重建专属适配层弥补。损失与核对方式见 [provenance/adaptation-log.md](../../provenance/adaptation-log.md) 的 A1。

## 覆盖 1 修订（2026-09-25）：用户入口调用控制恢复分层

本节是追加的日期修订段，不修改上文「覆盖 1」原文。

**新事实：** 8 个用户入口（ask、setup、grill、grill-gamestudio-docs、tasks、implement、wayfinder、handoff）的 `SKILL.md` frontmatter 追加 `disable-model-invocation: true`，技能目录内新增 `agents/openai.yaml`（`policy.allow_implicit_invocation: false`），description 措辞未改；12 个按需方法零改动。判定规则来自各宿主官方文档：Claude Code、Grok Build、DSH 读 frontmatter 的 `disable-model-invocation`；Codex 不读该字段，只读 `agents/openai.yaml` 的策略；ZCode、Qoder 未文档化调用控制字段。

**因此覆盖 1 的两句话只对按需方法继续成立**：「frontmatter 只使用标准字段 `name`、`description`、`license`」与「不再宣称纯标准技能文本具有跨宿主的强制调用隔离能力」。对 8 个用户入口，前缀是三层调用控制（两层由宿主解析器执行、一层仍是指令层约定），不再只是行为边界说明。

**仍然成立的部分：** 不重建客户端插件清单、市场清单与自建安装器；`agents/openai.yaml` 是 Codex 的策略文件，不是插件清单，也不改变标准布局；[unified-design-v1.md](unified-design-v1.md) 的 5.4、13.3 节按原始身份保留，两者与本节冲突时以本节为准。

**追溯：** 决定、新增损失与核对方式见 [provenance/adaptation-log.md](../../provenance/adaptation-log.md) 的 A7（#83 票面记作「A2」，编号沿用该文件既有的 A1—A6 顺序）；实际执行的检查结果见 [validation-v3.md](../validation-v3.md) 的「记录链闭环（#83）」；对外口径见 [CHANGELOG.md](../../CHANGELOG.md) 的 Unreleased 条目。

## 覆盖 2：不发布构建产物

**设计 v1：** 13.1 节列出 `dist/` 作为构建产物目录；V2 实际发布 tar 包与可复现构建核验。

**V3：** 不发布名为 MyGameStudio 的 npm 包，不自建安装命令，不构建 tar 包。`dist/` 与 `scripts/build-package.sh`、`scripts/verify-reproducible.sh` 退出。仓库已有的测试工具不成为用户安装技能的前置构建步骤。版本权威来源统一为根目录 `VERSION`。

## 覆盖 3：20 项为固定集合，Codebase、Merge、Docs 已纳入

**设计 v1：** 2.1 节说明最近三项（codebase、merge、docs）是用户指定共同设计的三项，已有草案但细节与整合尚待核对；A18—A20 的状态标为“细节与整合尚待核对”。

**V3：** 20 项是本次实施范围，包括 Codebase、Merge、Docs，不再把这三项是否纳入作为待确认问题。三项的正文已按职责卡整合并通过静态检查；行为验证状态按场景逐项记录在 [validation-v3.md](../validation-v3.md)。

## 覆盖 4：共享资料的所有者与安装后可达性

**设计 v1：** 13.2 节允许暂时沿用现有所有者路径，并提到若移到 `plugin/references/` 需同步更新消费者。

**V3：** 不建立 `plugin/references/`，也不假设安装会复制仓库根共享资料或自动解析技能间依赖。共用资料放在明确的所有者技能内：共同写作、文档分流与增量协作、子代理委派归 `docs-gamestudio`；人机责任与验收交接归 `tasks-gamestudio`。技能自身必要的模板与参考放在该技能目录内。消费者用同级技能的相对路径引用，完整安装后即可达；选择安装时按 [dependencies.md](../dependencies.md) 给出的组合补齐。

`docs/`、`provenance/` 与仓库外绝对路径都不是技能运行的隐性必需输入。项目自己的 GDD 和规范是运行时查找的项目资料，不是随技能分发的静态依赖。不建立运行时注册中心、自动补依赖安装器或扫描客户端缓存的回退程序。

## 覆盖 5：旧入口与专用运行层退出有效安装范围

**设计 v1：** 14 节把旧入口与 records 运行层的最终去留列为待单独决定，并说明本次没有执行删除。

**V3：** 本次执行授权移除。`game-producer`、`game-init`、`game-design` 不再作为有效技能发布；records 运行层、后端同步、恢复与迁移程序不再作为 V3 运行时。开始前基线提交、被移除内容与恢复方式记录在 [provenance/v2-retirement.md](../../provenance/v2-retirement.md)，能力去向与明确未覆盖部分记录在同一文件与 [migration-v3.md](../migration-v3.md)。Git 历史未被改写。

不修改用户其他游戏项目的任务、资产、存档、外部存储或已安装技能；旧项目迁移只提供说明与能力差异，不自动批量切换。

## 覆盖 6：验证以本次实际执行为准

**设计 v1：** 15.2 节列出 E01—E18 场景，全部标为待运行测试设计。

**V3：** 场景集合沿用并按本次要求补充，实际执行结果逐项记录在 [validation-v3.md](../validation-v3.md)，区分通过、失败与未运行。没有实际执行的验证一律标为未运行并说明缺少什么；当前 Agent 在对话中推演“应该怎么做”只算走查，不标为真实模型行为测试；静态字符串检查不替代行为验证。本地安装成功不等于 GitHub 远端 V3 安装成功，两者分别报告。

## 未覆盖的部分

设计 v1 的其余内容继续有效，包括：技能职责卡（附录 A01—A20）、四种动作的区分（5.1）、Docs 的覆盖范围与使用节奏（6.1—6.4）、子代理派发要求（第 7 节）、GDD/spec/词表/任务的协作与停止条件（第 8 节）、人机责任与两个分流标签（第 9 节）、知识库定位（第 10 节）、资源工作方式（第 11 节）、原型与研究深度（第 12 节）、上游与许可原则（13.4）。

整合清单 [unified-integration-v1.md](unified-integration-v1.md) 的 P0/P1 项已在本次实施中落地，落地位置见 [provenance/adaptation-log.md](../../provenance/adaptation-log.md)。

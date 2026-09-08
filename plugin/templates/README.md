# 模板使用说明

> 包内适配版(mygamestudio 0.4.0,任务票 04)。来源:插件设计仓库 `.scratch/mygamestudio-framework/templates/README.md`。本版仅把指向未随包设计文档的链接改为文字引用或包内路径;`project/`、`work/`、`records/`、`evidence/` 下的模板文件为逐字节副本。文件指纹与来源见包内 `provenance/manifest.md`。

这些是插件设计交付中的模板源,不是某个游戏已完成的项目资料。Game-Init 依据实际项目选择需要的模板、替换占位内容并建立引用,完成条件采用[初始化流程](../internal/proposals/project-onboarding.md)。

## 选择与落点

| 当前需要 | 模板 | 默认落点 |
| --- | --- | --- |
| 定位项目资料 | [INDEX](project/INDEX.md) | docs/mygamestudio/INDEX.md |
| 配置任务与文档管理 | [CONFIG](project/CONFIG.md) | docs/mygamestudio/CONFIG.md,或复用已有配置 |
| 维护当前目标与投入 | [PROJECT](project/PROJECT.md) | docs/mygamestudio/PROJECT.md |
| 形成当前产品要求 | [GAME_DESIGN](project/GAME_DESIGN.md) | docs/mygamestudio/GAME_DESIGN.md |
| 形成技术约定 | [TECH_DESIGN](project/TECH_DESIGN.md) | docs/mygamestudio/TECH_DESIGN.md |
| 统一有歧义的术语 | [CONTEXT](project/CONTEXT.md) | 已有术语文件,或 docs/mygamestudio/CONTEXT.md |
| 发起原子工作 | [工作请求](work/task.md) | 本地 work/<任务身份>/task.md,或 GitHub Issue 正文 |
| 交接实际结果 | [工作结果](work/result.md) | 本地 work/<任务身份>/results/,或相应结果评论 |
| 记录决定或技术取舍 | [决定](records/decision.md) | records/,或已有 ADR 目录 |
| 记录外部事实 | [研究](records/research.md) | records/ |
| 接入与恢复 | [初始化记录](records/onboarding.md) | 接入前为本次任务草稿,应用后按清单归档 |
| 独立审查 | [Review](evidence/review.md) | evidence/,或任务记录引用的证据位置 |
| 运行、试玩和人工反馈 | [Playtest](evidence/playtest.md) | evidence/,或任务记录引用的证据位置 |

## 实例化规则

1. 先复用已有有效资料;同一份当前内容保留一个维护位置。完成条件:入口映射真实路径,已有内容没有重复分叉。
2. 只生成当前有内容的文档或章节。删除无关占位项,需要但未确定的事实标记待定并说明影响。完成条件:生成文件不会用占位符冒充项目事实。
3. 按[共同合同](../internal/contracts/common.md)及 writing-for-agents(包内 `internal/methods/writing-for-agents/`)写入;每份资料保留其维护责任和来源。完成条件:管理、设计、实现、审查的可写目标可区分。
4. 回读实际落点、引用和内容。完成条件:下一位执行者能找到当前依据、任务与实际成果,历史材料不会被误当成当前要求。

工作请求和结果沿用设计文档《交接模板》的交接语义(proposals/handoff-templates.md,不随包)与[记录合同](../internal/contracts/records.md)。专有字段仅在本轮需要时添加,如关卡节奏、数值边界、资源尺寸、音频响度或构建目标,不为所有游戏强制填全。

GitHub 与本地任务选一个当前后端;其他位置可保存证据或明确标记的草稿。模板中的路径是默认逻辑位置,现有引擎工程、资源和构建目录按项目实际约定引用。

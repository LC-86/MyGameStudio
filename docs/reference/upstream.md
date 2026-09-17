# 与 Matt Pocock skills 的关系

由 **LC-86** 独立维护，基于 Matt Pocock skills 构建。
不是 Matt 或 Codex / ZCode / Grok / Claude Code 的官方产品。

## 固定版本

- 上游：mattpocock/skills **1.2.3**
- 提交：`3cca18b368ae95cdbdebbff572ccafa662551015`
- 纳入：正式 25 项（engineering 18 + productivity 7）
- 本插件增加：`game-producer`、`game-init`、`game-design`

权威账本：[plugin/provenance/manifest.md](../../plugin/provenance/manifest.md)。
许可摘要：[THIRD_PARTY_NOTICES.md](../../THIRD_PARTY_NOTICES.md)。

## 面向使用者的适配差异

- **游戏阶段资料**：通用技能会指向包内阶段要求；读取不是开工。
- **implement**：没有提交授权时保留未提交成果。
- **code-review**：覆盖适用的已提交、暂存、未暂存、新建与删除成果，不用空的 HEAD 差异代替完整评审。
- **正式工程**：默认最小可玩闭环、必要资源与实际检查；隔离原型只在你明确要求时制作。

技能标识与调用声明（包括 `disable-model-invocation`）保持上游名称，不另起一套别名。

## 不要做的事

- 用 `npx skills@latest add mattpocock/skills` 代替本组合包
- 在文档里暗示 28 项都是原创游戏技能
- 未评估就把上游升级成 latest

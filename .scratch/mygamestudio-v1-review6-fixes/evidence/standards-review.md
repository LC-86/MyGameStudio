## Standards

固定范围为 `git diff 1eef7d8..a3c43ce`（`3e876e2`、`a3c43ce`），已覆盖 29 个变动文件。依据 `AGENTS.md`、`CONTEXT.md`、`docs/agents/issue-tracker.md`、`triage-labels.md`、`domain.md`；无 ADR。**发现：0 项硬性规范违规，0 项值得报告的 Fowler 启发式异味。**

两票保留独立文件、既有五类分诊状态，实施记录追加于 Comments，未产生领域术语冲突。生产改动没有增加依赖；完整身份摘要经 `_pending_identity_digest()` 复用。测试中的身份摘要复算作为独立断言依据，不计为需要抽取的 Duplicated Code。

独立解析旧/新 driver JSON：变化仅实例 ID、时间、token 指纹、草稿文件名时间和本机替身端口；reason 中仅嵌入的实例 ID 改变，decision/target/policy_sha256/written_sha256 不变。归档逐成员比较：79 个文件中仅 `plugin/records/mgs_github.py` 变化；包 SHA-256 为 `71a07318af3705fb49840b1ff2abcd6d2dddbc9d705285c5b37a80ca28414fdb`。明细：`standards-evidence.json`。

本轴不把功能错误归为风格违规。独立 `/tmp` 探针另确认一个交由 Spec 轴计数的 P2：新旧布局混合时清理 A 会误删碰撞 B 旧登记，随后 B 读前超时重复发布；位置 `plugin/records/mgs_github.py:784-789`，证据 `standards-probe/mixed-layout-result.json`（3 POST、B 正文 2 条）。

未跑完整套件、驱动或验收入口；完整验证由主审执行。原仓库前后 HEAD 均 `e68ef7d0c8ee212d39419827fd0a46f66ad9c0ec`，前后 porcelain 均为空。

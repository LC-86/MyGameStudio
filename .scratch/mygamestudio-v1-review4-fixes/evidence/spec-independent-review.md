# 第四轮独立 Spec 轴

范围为 `git diff 521c465..05a2776`，两提交 `c9a8021`、`05a2776`；产品源码只读，从 `/tmp/mygamestudio-review-4-6hm1q78i/spec` 导入。独立构造的 MCP→GateService→进程内替身探针确认 **3 项 P2**，未发现越票面范围的新功能。原四探针、留存流、套件及每票变异由主审独立汇总，不据实施自述判定通过。

1. **[P2] 无缓存配置的退化未按承诺披露，仍引导会重复的重试。** [mgs_github.py:630](/Users/cuilei/MyOS/01_Projects/plugins/MyGameStudio/plugin/records/mgs_github.py:630) 无缓存返回 `None`，与登记成功同值；[1041](/Users/cuilei/MyOS/01_Projects/plugins/MyGameStudio/plugin/records/mgs_github.py:1041) 因而不附警告。真 MCP 首次 partial 的 note 仍称“不会重复发布”，恢复 PATCH 后重试仅评论 GET 超时，实际 **2 POST/2 评论，5100→5101**。票 01:46 明确要求“partial 结果 note 附警告说明”，票 01:15 要求“不得当作全新发布”。这是 SP-7 完整要求未闭合；当前退化不能作为已如实披露的可接受取舍，无缓存模式没有得到独立接受授权。

2. **[P2] 已登记操作身份可因 SHA8 碰撞被另一请求冒认。** [mgs_github.py:617](/Users/cuilei/MyOS/01_Projects/plugins/MyGameStudio/plugin/records/mgs_github.py:617) 截为 32 位，[667–669](/Users/cuilei/MyOS/01_Projects/plugins/MyGameStudio/plugin/records/mgs_github.py:667) 只判对象类型，不校验 `op/args/repo`。同仓库、`01-task` 的 `collision-result-79891` 与 `collision-result-80657`，80,658 次确定性候选找到同摘要 `346df0e9`，登记文件均为 `append-result-01-task-346df0e9.json`。A partial 后 B **第一次请求**遇读前超时，返回 `published=true/partial=true/comment_id=5100`，实际只有 A 评论，B 从未发布。违反票 01:15“已确认发布的操作身份保留/传递”和 :44 的操作参数及仓库身份约定；这是本批新增登记机制引入的实证缺陷。

3. **[P2] 整段尾匹配仍将不同绝对资源、评论衍生身份混同。** [run.sh:129](/Users/cuilei/MyOS/01_Projects/plugins/MyGameStudio/acceptance/18-complete-package-acceptance/run.sh:129) 对绝对期望路径也接受任意前置路径；[164–165](/Users/cuilei/MyOS/01_Projects/plugins/MyGameStudio/acceptance/18-complete-package-acceptance/run.sh:164) 对调用和返回复用同一无限 `comments` 尾段白名单。真 Gate 对 `/tmp/alternate-root/tmp/mgs18-evil-link.md` 的 deny/path，被正式 `/tmp/mgs18-evil-link.md` 判据认 **OK**；对身份 `01-harbor-timer/comments` 的 append-result deny/task_grant，返回目标尾部为 `comments/comments`，仍满足正式 `01-harbor-timer` 评论锚定。违反票 02:15“具体资源一致”“拒绝前缀/后缀混淆”；属于 SP-8 完整要求未闭合，不反推历史留存流虚假。

证据：[可复跑脚本](/tmp/mygamestudio-review-4-6hm1q78i/spec-independent-probes.py)、[完整机器结果](/tmp/mygamestudio-review-4-6hm1q78i/spec-independent-probes.json)，其中 `no-cache-partial-retry`、`pending-hash-collision`、`absolute-prefix`、`identity-comments-suffix` 为上述实证。MCP 事件为真实 Gate 返回按留存 schema 封装的合成事件，非历史会话事件。

边界：非法 JSON 登记破损保持 partial、明确不可读、仍仅 1 POST；有效空对象 `{}` 同样不重发，但没有 corrupt 说明，作为身份校验不足旁证，不另计问题。仅验证顺序式 partial→重试时序；未测试进程崩溃、生产并发、分页、真实网络与模型。没有源码变异或修改、外部写入、真实仓库改动。当前实证不足以接受 SP-7/SP-8 整体闭合，v1 收口条件不成立；SP-9 由主审单列。

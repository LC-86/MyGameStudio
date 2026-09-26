# Issue #87 行为证据

## 环境

- 宿主：本机 Codex CLI 0.157.0；模型：`gpt-6-sol`；项目安装器：官方 `skills` CLI 1.7.0。
- 使用全新临时消费者，安装 Issue #87 目标集合 21 项；没有把 MyGameStudio 源 checkout 放入消费者。CLI 会话均为 `--ephemeral`、`--sandbox read-only`。
- 以下初始请求不点名任何 GameStudio 技能。记录的是模型实际读取的消费者副本路径和独立会话 ID；结果只代表此 Codex CLI 与该模型，不外推到其他宿主。

## 通用写作触发

规格场景 `01a0dd08-350d-7ab3-b3d8-5395c195e13e`：请求写本地图片缩略图工程规格，输入包含 `128 × 128` 像素、仅 JPEG、每批最多 30 张、显式 opt-in、负责人 `media-indexer`、提案状态、尚未实现、无网络。轨迹读取 `.agents/skills/writing-for-agents/SKILL.md`，并从同一副本按需读取两个正文区段。结果保留以上边界，把新增失败条件标为草案建议，并把裁剪、EXIF 和输出位置列为未决；没有把草案写成已实现或已验证。

以下两次干净会话各请求六种交付：spec、implementation ticket、研究/评审结论、技能/项目规则、handoff、委派 brief。两次均读取消费者中的 `writing-for-agents/SKILL.md`；均未读取 `docs-gamestudio`，所以通用工作没有启动游戏专属分流。

| 会话 | 输入摘要 | 附加读取 | 输出核对 |
|---|---|---|---|
| `01a0dd0d-3d0d-72c0-8092-bf7545a74bd8` | JPEG 缩略图提案；CSV 2 MiB 上限已批准但未实现；重试文档默认 3、单条日志观察 2、运行配置未知；生成文件规则尚未采纳；解析器单测通过、集成未跑；`src/importer.ts` 只读委派 | `references/subagent-delegation.md` | 六段分别保留数字、单位、负责人、候选/采纳状态、验证缺口与下一步；委派范围只读且列明输入和证据 |
| `01a0dd0d-3d02-72b3-b088-6818d0d9bf33` | 本地保留 4 份快照；API v3/v2 的 `account_id` 差异；v1 调用、v2 未测；CSV 表头规则提案；缓存 handoff；冷启动测量委派 | `references/subagent-delegation.md`、`SKILL-MECHANICS.md` | 六段保留 4 份、当地时间 02:00、版本差异、P2、提案状态、单测/集成状态和无代码修改；没有把候选改成决定 |

这些会话的初始输入原文：

```text
Draft an engineering specification for an optional local image-thumbnail feature. Facts: create 128x128-pixel thumbnails; accept JPEG input only; process batches up to 30; require explicit opt-in; owner media-indexer; status proposed and not implemented; never use the network. Include behavior, acceptance criteria, and exclusions.
```

```text
Prepare six concise independent artifacts from these facts. Keep the facts separate by artifact. Do not edit files, contact anyone, or publish anything. (1) Spec: accept JPEG only; create 128x128-pixel thumbnails; batch limit 30; explicit opt-in; owner media-indexer; proposed and not implemented; no network. (2) Ticket: reject CSV files larger than 2 MiB before parsing; display row count; owner import-panel; approved but not implemented; no network. (3) Research finding: docs say retry default 3; one production log observed 2 retries; an estimate has no method; effective runtime config unknown; validation not run. (4) Project rule proposal: outputs under build/generated; never overwrite hand-authored files; cleanup only files created by the current task; proposed, not adopted. (5) Handoff: source commit abc123; parser change implemented; unit tests passed; integration not run; next inspect empty fields; do not change behavior before that check. (6) Delegation brief: ask another agent to inspect src/importer.ts and tests/importer.test.ts; current commit def456 and clean; read-only; return exact evidence and checks; no contact.
```

```text
Prepare six concise independent artifacts from these facts. Do not edit files, contact anyone, or publish anything. (1) Spec: retain 4 local snapshots; delete the oldest only after a new snapshot succeeds; run daily at 02:00 local time; owner backup-service; proposed and not implemented; never upload to cloud. (2) Ticket: omit account_id only for API v3; retain it for v2; migration is manual with no automatic conversion; owner api-team; proposed, not adopted. (3) Review finding: call still targets v1; v2 behavior untested; severity P2; unit tests passed; integration tests not run. (4) Skill proposal: CSV headers sku and quantity; case-sensitive; reject missing columns; never edit input files; procedure is proposed. (5) Handoff: branch fix-cache; adopted TTL 15 minutes; Redis failover is a candidate; no code changes; next compare live config with primary docs. (6) Delegation brief: ask another agent to measure cold-start time from this checkout; allow only temporary output under /tmp; no repository edits; return environment, repeated results, and unresolved uncertainty.
```

## GameStudio 文档路由

| 会话 | 输入与轨迹 | 结果核对 |
|---|---|---|
| `01a0dd0a-57fe-7360-a7d6-5910fd4bc7cd` | 体力候选规则：上限 10；仅 HOME 每 60 秒恢复 1 点；远征不恢复；归零后暂停并提示返回。读取共同方法、`docs-gamestudio/SKILL.md` 与 `references/document-routing.md`。 | 保持候选、未采纳、未实现、未试玩；区分 GDD、spec、术语表；不改文件，指出采纳及计时细节仍待决定。 |
| `01a0dd0f-0698-7420-9f47-558d44f142ea` | 同组体力规则已获用户批准但尚未实现。读取共同方法、GDD 技能、游戏分流、GDD 写法参考。 | 草稿进入 GDD，不擅自创建 spec；术语定义与规则数值分开；明确未实现、未试玩，并保留不足 60 秒计时规则为未决。 |

```text
I am planning a game stamina change. Current proposal: stamina cap 10; regain 1 point per 60 seconds only while at HOME; expedition does not restore stamina; at zero stamina the expedition pauses and asks the player to return. This is still a candidate, not adopted, implemented, or playtested, and I have not made the decision. Do not edit files. Tell me where each part belongs among the current game design, a delivery spec, and the glossary; preserve its status and state what should wait for my decision.
```

```text
The user has now approved a stamina rule for the game, but it is not implemented or playtested. The current GDD describes stamina as a resource; the glossary already defines stamina, HOME, and expedition. Add a concise GDD paragraph to the response only: maximum 10 stamina; regain 1 point every 60 seconds only while at HOME; no time recovery during an expedition; at zero, pause the expedition and ask the player to return. Do not draft a delivery spec or edit files. Distinguish approved design from implementation and playtest status.
```

## 不触发与责任边界

| 会话 | 输入 | 输出与读取 |
|---|---|---|
| `01a0dd0b-5cef-7233-8051-a005edb5bc14` | `6 × 7`，只要数字 | `42`；无 GameStudio 副本读取 |
| `01a0dd0b-5cef-75e3-a12a-45e90b927646` | 把 `seperately` 改为已核实的 `separately` | `separately`；无 GameStudio 副本读取 |
| `01a0dd0e-7b85-7e73-874b-9dccb922eaa7` | 同一会话回答 `8 × 9` 并纠正拼写 | 两行输出 `72`、`separately`；无 GameStudio 副本读取 |
| `01a0dd0f-dd36-7ed2-8319-ae28cf6fdeed` | 单测通过、集成未运行、指定设备人工验收仍待完成；要求只读交接，不评论工单/发邮件/关单 | 明确不得称为完成，下一步仍需集成验证和人工验收；未修改或发送内容 |
| `01a0dd0f-ddf8-7232-bfe8-984e28e57f34` | 原型启动、4 项本地检查通过、玩家未试玩、未要求发布或上传 | 保留人工体验未完成；明确未改工单、未发布、未上传 |

```text
Write a short handoff about this implementation: unit tests passed; integration tests have not run; the specified human acceptance check on a real device is pending and required before the work can be called complete. You may only read these facts and answer here. Do not edit files, comment on an issue, send email, upload anything, or close the task. State the current status and next action.
```

```text
Summarize this prototype result: the local prototype starts and four manual input-loop checks passed; no player has tried it; the named human experience review is still pending; no release or upload was requested. Read-only response only. Do not modify the ticket, send messages, publish or upload. Keep human acceptance incomplete.
```

这些会话的初始输入原文：

```text
Answer 6 times 7 with the numeral only.
```

```text
The verified spelling is “separately”. Replace “seperately” with “separately” and return only the corrected word.
```

```text
Answer 8 times 9 with the number only. Then correct “seperately” to “separately” and return the corrected word on a second line. Return only those two lines.
```

## 缺少依赖时的结果

这两项负例在临时消费者的 `AGENTS.md` 中声明：只把消费者 `.agents/skills/` 视为本次安装范围；不能用范围外的全局技能补缺。该约束用于隔离测试源，并非新增的产品规则。

| 会话 | 有意漏掉的资料 | 结果 |
|---|---|---|
| `01a0dd17-5351-7761-861e-cc01bd526f82`、`01a0dd1a-02d1-7cc2-bc61-f421980604ee` | 只安装 `tasks-gamestudio`，缺少共同写作方法 | 两次均只读取已安装的 tasks 正文，准确指出 `.agents/skills/writing-for-agents/SKILL.md` 缺失并停止起草票据 |
| `01a0dd17-52ea-7891-b0fb-c0a36a5f15ab`、`01a0dd1a-021b-7202-a49e-0096cf1f7909` | 安装 `writing-for-agents` 与 `gdd-gamestudio`，漏掉 `docs-gamestudio` | 两次均指出 `.agents/skills/docs-gamestudio/references/document-routing.md` 缺失；只在回复中给草稿，并明确无法核实专属路由、没有编辑文件 |

```text
Turn these approved requirements into a concise implementation ticket: reject CSV over 2 MiB before parsing; show row count; owner import-panel; change approved but not implemented; no network. Include completion conditions and exclusions. If a required writing method is unavailable, state the exact missing capability and stop before claiming the ticket is complete.
```

```text
Create an implementation ticket: accept JSON files up to 500 KiB; reject larger files before decoding; owner config-import; approved but not implemented; no network. If the required writing method is not installed in this project, report the exact missing file and stop without drafting the ticket.
```

```text
The user approved a game stamina rule but it is not implemented: cap 10; regain 1 point per 60 seconds at HOME only; no expedition recovery. Draft a GDD addition in the reply only. If the required GameStudio document-routing reference is absent from the installed project collection, report its exact missing path rather than inventing routing rules.
```

```text
A user approved a GDD rule: maximum party size 4; followers do not join combat unless commanded; not implemented or playtested. In your reply only, classify what belongs in the GDD and identify what is still unspecified. If the project document-routing reference is missing, report its exact path and do not claim the routing method was available.
```

## 实际委派

两名接收方都以 `fork_turns: none` 在新上下文执行；父代理只提供下表的临时消费者路径与任务输入。接收方回报实际读取文件，父代理把结果逐项对照原始事实；两次均未修改文件。

| 接收方 | 接收输入与实际读取 | 回收核对 |
|---|---|---|
| `issue87_delegate_generic_a` | 只读 handoff 事实；读取消费者 `writing-for-agents/SKILL.md` 与 `references/subagent-delegation.md`。 | 准确保留源提交、已实现、单测通过、集成未跑、下一步和停止边界。 |
| `issue87_delegate_game_b` | 已采纳/已实现的体力规则与未完成的玩家验收；读取共同写作、通用委派、docs-gamestudio 正文及分流参考、tasks 责任参考。 | 保持任务开放、人工项未完成；要求向指定验收人交接，不标为通过或关闭。 |

接收方指令的任务内容：

```text
只读交接事实：源提交 3f21abc；parser change 已实现；unit tests 通过；integration tests 未运行；下一步核对 empty-field 输出；核对前不要改行为。准确列明未验证项，并报告实际读取的消费者文件路径。
```

```text
游戏任务交接事实：玩家体力恢复规则已被用户采纳并实现，自动化测试通过；真实玩家体验尚未进行，是指定的人工验收项。返回交付状态与下一步，保持人工项未完成，不要写成通过或关单。列出实际读取的消费者文件路径。
```

## 局限

- 全局 `thread-rename` 指令在部分 ephemeral 会话尝试读取标题，App Server 返回 `code=1`；会话只给建议，没有实际改名或其他文件操作。Codex CLI 也输出本地 rollout 索引回退警告，但上述模型回复均正常结束。
- 缺依赖负例用测试目录显式限制安装范围。此证据证明在该范围约束下，模型报告具体缺口；不证明宿主会自动屏蔽范围外的全局同名技能。
- 行为结果只适用于 Codex CLI 0.157.0 与 `gpt-6-sol`，不代表其他宿主或模型。

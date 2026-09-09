# MyGameStudio v1 独立审查

审查结论：**当前 0.18.0 尚未达到可作为首版完成品安装或发布的状态。** 现有五项确定性测试及 33 项驱动回归全部通过，但补充探针发现 12 项规格问题，其中 4 项 P1、8 项 P2。Standards 轴另有 2 项判断性建议，不与 Spec 轴合并计数。票 17 的真实远端验收、票 18 的会话级验收仍待完成，不能只靠重新跑出原有测试全绿来收口。

审查时间：2026-09-09。对象是交接文件指向的实现，不只审查交接文案。

- 仓库：`/Users/cuilei/MyOS/01_Projects/plugins/MyGameStudio`
- 基线：`9bcdfb94636ee4d6635c526d03517e0dcd2c8839`
- 固定 HEAD：`6b2444b53bc151979bf7e0a47b81f040d7a3a01d`
- 比较：`git diff 9bcdfb9...HEAD`；18 个提交，1,108 个变更文件。
- 权威规格：`.scratch/mygamestudio-framework/spec.md`、`acceptance.md`、`contracts/`，以及实施批次规格与 18 张票。
- Standards 与 Spec 分别由独立子代理审查，主审核实运行时、测试、打包与证据。所有复现仅作用于临时夹具或隔离副本；未改原仓库、票面、历史证据或用户客户端配置，未提交、推送、发布或调用真实 GitHub 写接口。

## Standards

未发现明确的仓库规范硬违反；以下两项依据 code-review 的 smell baseline，属于判断性建议。

1. **[P2] possible Duplicated Code：两套任务核验已出现语义漂移。** [mgs_github.py:1003](/Users/cuilei/MyOS/01_Projects/plugins/MyGameStudio/plugin/records/mgs_github.py:1003) 重复 [mgs_records.py:724](/Users/cuilei/MyOS/01_Projects/plugins/MyGameStudio/plugin/records/mgs_records.py:724) 的标签、核心文档和任务检查，例如 `missing = [name for name in CANONICAL_LABELS ...]`、`duplicate_types = ...`；GitHub 任务循环却漏掉本地 `TASK_REQUEST_KEYS` 校验。复现同一空工作请求：GitHub `verify` 返回 `ok:true`，本地报告缺少“当前目标、完成标准、执行责任”。建议将规范化任务的公共校验提取为单一实现，后端只增加存储特有检查。

2. **[P3] possible Repeated Switches：远端动作与草稿重放分别维护参数分发。** [mgs_runtime.py:848](/Users/cuilei/MyOS/01_Projects/plugins/MyGameStudio/plugin/runtime/mgs_runtime.py:848) 的 `if action == "update"` 传递 `change_note`；[mgs_github.py:957](/Users/cuilei/MyOS/01_Projects/plugins/MyGameStudio/plugin/records/mgs_github.py:957) 的 `elif op == "update_task"` 丢弃该参数，保存更新草稿时也遗漏。内存重放探针确认：即使草稿含自定义说明，调用仍仅传 `expected_body_sha256`，原说明变成默认“安排更新”。建议共享动作参数规范，统一保存、在线执行和重放。

## Spec

以下 S1–S6 保留独立 Spec 审查的顺序；R1–R6 是主审补充，不跨轴合并或重新排名。

### 独立 Spec 审查

**S1 · [P1] 草稿会写入错误仓库。** [mgs_github.py:939](/Users/cuilei/MyOS/01_Projects/plugins/MyGameStudio/plugin/records/mgs_github.py:939) 重放时忽略草稿的 `repo`。先在 `old-owner/private-repo` 保存离线草稿，再以同一缓存目录切换到 `mygamestudio/issue-accept`，`publish_drafts()` 实际向后者 POST，并把旧草稿标为已发布。这会把原项目材料写入错误项目；当前仓库已有写权限不能代表这份旧草稿已获迁移授权。违反 [records.md:39](/Users/cuilei/MyOS/01_Projects/plugins/MyGameStudio/.scratch/mygamestudio-framework/contracts/records.md:39)：“创建或修改远端记录前核对明确的仓库及操作授权”。应在发请求前绑定并核对草稿仓库，跨仓库移动走明确迁移流程。

**S2 · [P2] 回读失败后重复发布评论。** [mgs_github.py:769](/Users/cuilei/MyOS/01_Projects/plugins/MyGameStudio/plugin/records/mgs_github.py:769) 吞掉回读超时后将结果当成不存在，继续 POST。注入第一次评论已落地、响应及回读都超时，替身最终有两条相同评论、两次 POST，调用却报告尚未确认。违反 [records.md:39](/Users/cuilei/MyOS/01_Projects/plugins/MyGameStudio/.scratch/mygamestudio-framework/contracts/records.md:39)：“结果不确定时用返回身份或请求关联回读实际状态，避免重复创建”。应保留未知状态，回读无法确认时停止重发。

**S3 · [P2] GitHub→本地迁移后读取不到任务。** [mgs_github.py:1269](/Users/cuilei/MyOS/01_Projects/plugins/MyGameStudio/plugin/records/mgs_github.py:1269) 将旧 GitHub 坐标写成本地任务根目录，实际任务却生成在 `docs/mygamestudio/work/`。复现迁移返回 `created=1`，新 CONFIG 的统一读取结果是 `[]`；返回的 `emit_dir` 还指向不存在的 `emit/files`。此外 [mgs_records.py:980](/Users/cuilei/MyOS/01_Projects/plugins/MyGameStudio/plugin/records/mgs_records.py:980) 的 CLI 反向规划显式传 `transport=None`，没有建立所需读取通道。违反 [project-configuration.md:35](/Users/cuilei/MyOS/01_Projects/plugins/MyGameStudio/.scratch/mygamestudio-framework/contracts/project-configuration.md:35)：“确认后切换当前来源”。应让计划目标、本地文件落点、CONFIG 和返回路径一致，并从 CLI 真实入口验证反向迁移。

**S4 · [P2] 未验证引用就宣告远端可达。** [mgs_github.py:1174](/Users/cuilei/MyOS/01_Projects/plugins/MyGameStudio/plugin/records/mgs_github.py:1174) 仅检查引用字符串存在。给三个 `example.invalid` 地址并使用完全离线的 transport，仍得到三个 `remote_reachable=true`、`ok=true`，transport 调用次数为零。违反 [records.md:33](/Users/cuilei/MyOS/01_Projects/plugins/MyGameStudio/.scratch/mygamestudio-framework/contracts/records.md:33)：“准备远端交接时确认引用可达”。没有执行可达性检查时应明确返回未验证，不能把引用存在当作检查通过。

**S5 · [P2] 离线开工报告隐去缓存状态。** [mgs_records.py:242](/Users/cuilei/MyOS/01_Projects/plugins/MyGameStudio/plugin/records/mgs_records.py:242) 取出后端结果的 `tasks` 后丢弃缓存元信息。在线缓存任务后断网，`ready` 仍输出可开工任务，顶层没有缓存状态、抓取时间或来源，调用者无法判断是否正在依据旧状态安排工作。违反 [project-configuration.md:37](/Users/cuilei/MyOS/01_Projects/plugins/MyGameStudio/.scratch/mygamestudio-framework/contracts/project-configuration.md:37)：“注明时间与来源的缓存”。应将这些信息传递至统一接口结果，并区分缓存推断与当前确认。

**S6 · [P2] 同秒草稿互相覆盖。** [mgs_github.py:517](/Users/cuilei/MyOS/01_Projects/plugins/MyGameStudio/plugin/records/mgs_github.py:517) 用秒级时间、操作及任务身份生成文件名，然后直接覆盖写入。固定同一秒连续追加“证据一”“证据二”，两次返回同一路径，最终仅一份草稿、只剩“证据二”。未满足 [project-configuration.md:37](/Users/cuilei/MyOS/01_Projects/plugins/MyGameStudio/.scratch/mygamestudio-framework/contracts/project-configuration.md:37) 的“保存待发布草稿”。应给每个操作稳定且唯一的身份，并避免覆盖已有草稿。

复现：[spec-probes.py](/tmp/mygamestudio-review-4h4jbp_z/spec-probes.py)，[完整输出](/tmp/mygamestudio-review-4h4jbp_z/spec-probes.jsonl)。主审已读取并再次运行六项复现，全部重现；仅用进程内 FakeTransport，没有网络请求。

### 主审补充

**R1 · [P1] 凭据撤销后，已经通过早期校验的写入仍能落盘。** [mgs_runtime.py:452](/Users/cuilei/MyOS/01_Projects/plugins/MyGameStudio/plugin/runtime/mgs_runtime.py:452) 在拿服务锁前解析凭据，锁内不再检查身份或策略。确定性探针让写线程在身份校验后暂停，经另一个 GateService 实例调用公开 `release_instance()` 撤销，再恢复写线程；后续身份查询已拒绝，但该写入仍返回 `allow` 并写入 `STALE`。违反 [runtime.md:34](/Users/cuilei/MyOS/01_Projects/plugins/MyGameStudio/.scratch/mygamestudio-framework/contracts/runtime.md:34) 的撤销旧执行能力后才能接管，以及第 46 行的绑定失效不得放开写入。应把最终身份、有效期和策略检查与写入纳入同一服务锁临界区。

**R2 · [P1] 用途策略条目丢失时，从拒绝变成无限制用途。** [mgs_runtime.py:468](/Users/cuilei/MyOS/01_Projects/plugins/MyGameStudio/plugin/runtime/mgs_runtime.py:468) 的 `.get(..., {}).get("restrict")` 将“用途不存在”和“明确配置不额外限制”都当作 `None`。已有 prototype 实例对正式 `src/` 的写入原本在 purpose 层被拒；从合法 JSON 策略删除 prototype 条目后，同一写入变为 `allow`。远端路径和 scope 也使用同类逻辑。违反 [runtime.md:13](/Users/cuilei/MyOS/01_Projects/plugins/MyGameStudio/.scratch/mygamestudio-framework/contracts/runtime.md:13) 的权限交集与第 46 行的故障闭合要求。应校验完整策略结构及绑定用途存在，缺失时拒绝。

**R3 · [P2] 普通内容更新破坏已有文件权限。** [mgs_runtime.py:550](/Users/cuilei/MyOS/01_Projects/plugins/MyGameStudio/plugin/runtime/mgs_runtime.py:550) 固定以 `0644` 新建临时文件再替换目标。对 `0755` 的脚本执行合法内容更新后变成 `0644`，不能再直接执行；`0600` 文件也变成 `0644`。提供正确内容哈希仍会发生。已有工程的可用脚本因此被内容更新破坏，违背 [05 号票:3](/Users/cuilei/MyOS/01_Projects/plugins/MyGameStudio/.scratch/mygamestudio-v1/issues/05-adopt-existing-project.md:3) 保留有效结构和资料的目标，并影响构建入口。应保留已有目标的必要元数据，将权限变化作为明确操作处理；回滚也应遵守同样要求。

**R4 · [P1] 审计失败时远端写入已生效，却返回“拒绝”。** [mgs_runtime.py:823](/Users/cuilei/MyOS/01_Projects/plugins/MyGameStudio/plugin/runtime/mgs_runtime.py:823) 在远端动作完成后才追加审计。把测试运行根的 `audit.jsonl` 换成目录，经 MCP 入口追加结果，替身实际新增一条评论；审计抛异常后 [mcp_gate.py:132](/Users/cuilei/MyOS/01_Projects/plugins/MyGameStudio/plugin/runtime/mcp_gate.py:132) 返回 `channel/deny`，没有任何写入审计。这既不闭合，也误报实际结果，可能引发调用方重试。违反 [runtime.md:15](/Users/cuilei/MyOS/01_Projects/plugins/MyGameStudio/.scratch/mygamestudio-framework/contracts/runtime.md:15) 的故障行为及第 48 行的逐次记录要求。应先确保持久记录写入意图可用，并把已发生或尚不确定的远端结果如实回报，不能包装成未执行的拒绝。

R1–R4 复现：[runtime-probes.py](/tmp/mygamestudio-review-4h4jbp_z/runtime-probes.py)，[完整输出](/tmp/mygamestudio-review-4h4jbp_z/runtime-probes.jsonl)。均使用 `/tmp` 独立夹具；R4 使用进程内替身。

**R5 · [P2] 同源重打包不能复现已交付包的字节。** [build-package.sh:55](/Users/cuilei/MyOS/01_Projects/plugins/MyGameStudio/dist/build-package.sh:55) 的 `COPYFILE_DISABLE=1` 未去除 tar 的 `com.apple.provenance` 扩展属性。主审在同机用 `git archive HEAD` 准备隔离副本，运行原构建脚本；79 项文件内容和逐文件清单完全一致，tar 中 137 项的 provenance PAX 属性不同。原包 SHA-256 为 `5a8c993e828ce963c18c3cbd3a63d46ddc7772d1ca1f5a6bd0eb30e7e180bcf0`，重建为 `1573765118531f6d40e601b7bb01b2dadbcb0693a73c1b589a285bf50cab14c3`。这直接否定脚本第 54 行和交付文档的“同源重打包字节一致”声明。应排除平台扩展元数据，使用新副本验证复现，而不是仅在同一目录重复构建。

**R6 · [P2] 续作证据保留了真实执行令牌，泄漏检查仍声称通过。** [run.sh:1374](/Users/cuilei/MyOS/01_Projects/plugins/MyGameStudio/acceptance/16-producer-complete-loop/run.sh:1374) 与 `sanitize()` 仅枚举固定实例名；续作的两枚凭据没有覆盖到。明文位于 [t6b-events.jsonl:11](/Users/cuilei/MyOS/01_Projects/plugins/MyGameStudio/acceptance/16-producer-complete-loop/evidence/t6b-events.jsonl:11) 和 [t9b-events.jsonl:9](/Users/cuilei/MyOS/01_Projects/plugins/MyGameStudio/acceptance/16-producer-complete-loop/evidence/t9b-events.jsonl:9)，已进入 Git 历史。其 SHA-256 与隔离运行根的两条真实登记匹配，排除了伪造测试令牌。2026-09-09 05:35:57 UTC 核对时均 `released=false` 且未过期，登记到期时间分别为 05:46:23、05:55:50 UTC。它们只对应验收隔离实例，不是 Codex/GitHub 账户凭据；报告及输出均不复制明文。违反 [runtime.md:48](/Users/cuilei/MyOS/01_Projects/plugins/MyGameStudio/.scratch/mygamestudio-framework/contracts/runtime.md:48) 的秘密不进入普通日志要求。应覆盖所有签发/续作实例、撤销尚有效的验收凭据，并在发布证据前独立扫描。删除或重写历史不在本次只读审查授权内，未执行。

## 逐票复核

“样例证据支持”表示票面行为有历史运行输出、事件或结果回读支持，且本次未发现该专项的新问题；**不代表本次重新运行了模型会话，也不代表共享运行保障已达发布条件**。表中通过范围按各票当时样例与入口解释，已知人工反馈不被当作插件缺陷或替人判定通过。

| 票 | 票面勾选 | 本次结论 | 依据与限制 |
| --- | --- | --- | --- |
| 01 显式状态入口 | 6/6 | 样例证据支持 | 三组只读前后哈希一致，22 项现存样例内容全部复算吻合；模型入口未复跑 |
| 02 角色受限写入 | 6/6 | 部分通过，不能据此确认完整保障 | 现有 allow/deny 探针可复现；R2 说明用途策略缺失时交集失守 |
| 03 故障与间接写入 | 6/6 | 不通过完整故障闭合要求 | 现有故障测试通过，但 R2 提供新的故障放行反例 |
| 04 新项目初始化 | 6/6 | 样例证据支持 | 9 项最终审计写入哈希与终态清单一致；受共享运行保障限制 |
| 05 接手既有项目 | 6/6 | 部分通过 | 7 项最终审计写入一致；R3 暴露内容写入不能保留脚本权限 |
| 06 设计与规格 | 6/6 | 样例证据支持 | 历史 5 个会话事件文件、双项目审计在案；未决设计仍按未决处理 |
| 07 隔离原型 | 5/5 | 样例证据支持 | 4 项最终审计写入一致；原型页面实际体验、反应时间与追回率仍待人 |
| 08 本地拆票 | 6/6 | 样例证据支持 | 4 组会话事件及 24 条审计；不据此推断 GitHub 同语义已正确 |
| 09 代码交付 | 6/6 | 样例证据支持 | 历史代码样例有 4 组事件及 18 条审计；通用文件更新受 R3 限制 |
| 10 视觉资源 | 6/6 | 样例证据支持，审美待人工 | 历史 3 组事件及 13 条审计；未将素材存在当作审美通过 |
| 11 音频资源 | 6/6 | 样例证据支持，试听待人工 | 历史 3 组事件及 12 条审计；未将音频文件生成当作听感通过 |
| 12 构建运行 | 6/6 | 样例证据支持 | 历史 3 组事件及 13 条审计；浏览器实际手感/HUD 验收仍待人 |
| 13 独立审查入口 | 6/6 | 样例证据支持 | 4 组事件及 29 条审计；已发现样例缺陷与待修复项不冒充通过 |
| 14 试玩与反馈 | 6/6 | 样例证据支持，人工反馈待办 | 2 组事件及 15 条审计；模拟反馈演示不作为实际用户反馈 |
| 15 并发恢复 | 6/6 | 不通过撤销后不可写要求 | R1 复现公开撤销完成后旧写入仍落盘；原竞争探针只覆盖部分时序 |
| 16 统筹闭环 | 7/7 | 部分通过，证据保密结论不成立 | 22 项最终审计写入一致；续作证据 R6 有明文凭据；样例仍有人工待办 |
| 17 GitHub 后端 | 6/7 | 不通过当前完整合同；另待真实远端授权 | S1–S6、R4；本地替身 103/0 的旧结果不能覆盖新增反例 |
| 18 整包与升级 | 4/7 | 部分通过，不可收口 | 33 项驱动复现通过；R5 可复现打包失败；2/3/4 条会话验收仍未完成 |

## 证据核对与验证边界

1. **当前运行通过：** `test_plugin_package.py`、`test_runtime_gate.py`、`test_runtime_boundaries.py`、`test_records_backend.py`、`test_github_backend.py` 五项均退出 0。在 `/tmp` 的 HEAD 隔离副本运行原 `driver-probes.sh`，33 PASS / 0 FAIL，实际驱动隔离安装副本的 MCP 进程。[驱动日志](/tmp/mygamestudio-review-4h4jbp_z/driver-probes.log)。没有真实模型调用。

2. **设计和包内容：** 权威设计目录的基线到 HEAD diff 为空；设计入口 SHA-256 与实施规格登记的 `c6ccab8eb140fae4bbd77eb8f7ddcf7f323e7f5c9901519d383dd289ae1e222c` 相同。provenance 的 40 项逐一复算通过，包内 79 个实际文件的内容与源码、逐文件清单三方一致。此结果与 R5 不矛盾：内容一致，tar 容器元数据不一致。

3. **历史哈希抽查：** 票 01 三组前后清单一致，与现存 22 项样例文件全部一致；票 18 普通对话前后清单一致。票 02/03/04/05/07/16 共 51 项最后一次 allow 写入哈希与各自终态清单全部一致。票 15 比较 16 项，14 项一致，另外两项是脚本明确注入的 GAME_DESIGN 实质修改与任务“开发者注”，有相应脚本段及记录，未当成伪造证据。

4. **审计格式与顺序：** 对票 02–17 的 17 份审计日志进行 JSON 解析和文件内时间顺序检查，未发现解析错误或逆序。这只能支持日志内部一致性，不能证明所有操作真实发生；实际内容用上述哈希和局部复现交叉核对，未把文件时间戳单独当真实性证明。

5. **票 18 的历史失败没有全部消失：** `process-log-run3-usage-limit.txt:64` 和 `upg-governance-check.json` 仍保留 CONFIG 治理比较失败，文档却概括为该段全过。主审对留存升级前后 CONFIG 重新按 TOML 语义比较，排除 Codex 自管插件段后相等，实际差异为段序。因此没有证据认定治理内容被越权更改，但应区分原始 FAIL 与修正后的复核，不能称原始整轮全部通过。U2 截断、P1/P2/P3/G1 空报告和 R 环未完成，与票面待办相符。

6. **敏感信息：** 对全部 1,704 个 Git 历史对象做常见服务令牌前缀及执行 token 字段扫描，发现 R6 的两个明文执行令牌 blob；未发现匹配本次前缀规则的 Codex/GitHub 服务密钥。这是有限模式扫描，不能扩写成“没有任何秘密”。值只做哈希匹配，未复制到审查产物。

7. **已知合法待办：** 票 17 第 7 条真实远端写入未授权；票 18 第 2/3/4 条会话级验收未完成；五项人工反馈及两项开发者决定仍保留。没有重新调用模型来验证账户额度，也没有把交接记载的恢复日期当作本次查询的账户状态。进程快照未发现交接所说的 `standin_github.py` 遗留进程；本次驱动进程已结束，没有停止其他任务的进程。

机器可读摘要：[verification-summary.json](/tmp/mygamestudio-review-4h4jbp_z/verification-summary.json)。本次结束时 HEAD 未变化，`git status --porcelain=v1` 为空。

## 交付判定

当前可供审阅和继续开发，但不宜按“v1 已完成”交付日常安装或发布决定。应先修复上述问题，增加能够捕获这些实际反例的检查，再完成票 18 的会话级闭环及经另行授权的真实 GitHub 验收；人工体验项目继续按真实反馈保留。代码修复、票面修改、凭据撤销、历史处理、安装及发布均未在本次只读审查中执行。

Standards：0 项硬违反、2 项判断性建议，最高 P2 为公共核验重复导致语义漂移；Spec：12 项问题（4 P1、8 P2），最高 P1 包括错仓库写入、撤销后写入、用途故障放行及远端审计失败后误报拒绝。

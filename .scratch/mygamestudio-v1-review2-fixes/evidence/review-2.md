# MyGameStudio v1 第二轮独立复审

审查结论：**第一轮原始反例的修复有实证支持，真实远端终态与票 18 最终轮也有相互一致的证据；但当前版本仍不能按“v1 全部收口”交付安装或发布决定。** 本轮发现 6 项 Spec 问题：1 项 P1、5 项 P2。Standards 轴无硬违反，保留 1 项原 P3 结构性建议。五套测试、33 项驱动及字节可复现打包均通过，不能覆盖本轮新增反例。

审查日期：2026-09-09。Standards、Spec 由两个独立审查上下文分开执行；主审核对证据、运行测试并复现验收资产反例。

- 真实仓库：`/Users/cuilei/MyOS/01_Projects/plugins/MyGameStudio`。
- 用户指定审查版本：`d9343329d4f16c20f4391890896b91ac29e81c00`；批次比较：`git diff 31dabfd...d934332`。
- 实际开始及结束 HEAD：`b89b548f59336f57f63df70bda331bc204bd12de`。它比指定版本仅增加 `review-2-handoff.md`，产品代码和验收资产没有差异；没有把这项差异当作证据伪造。
- 开始、结束 `git status --porcelain` 均为空。所有运行、变异、报告产出均在 `/tmp`；真实仓库零文件写入、零提交、零推送、零真实远端写入、零验收模型轮调用。
- 指定报告路径未被 Git 忽略，写入会出现两个未跟踪文件，与“零工作树改动且最终状态为空”冲突。已提出交付位置澄清；未收到选择前优先遵守硬边界，报告和 JSON 交付在本目录，没有改 `.gitignore` 或本地排除配置。

## Standards

**0 项规范硬违反；1 项原 P3 判断性建议部分闭合。** 原 P2 共享核心核验已提取到 `mgs_records.py`，两后端共用；相同缺字段任务的回归通过。

**ST-1 · [P3] possible Repeated Switches：说明参数行为已修复，但动作参数仍有两份分发。** [mgs_runtime.py:1055](/Users/cuilei/MyOS/01_Projects/plugins/MyGameStudio/plugin/runtime/mgs_runtime.py:1055) 与 [mgs_github.py:1029](/Users/cuilei/MyOS/01_Projects/plugins/MyGameStudio/plugin/records/mgs_github.py:1029) 继续分别维护在线执行与草稿重放参数。修复票 [01:22](/Users/cuilei/MyOS/01_Projects/plugins/MyGameStudio/.scratch/mygamestudio-v1-review-fixes/issues/01-records-backend-review-fixes.md:22) 的“动作参数规范共享”没有在结构上完整实现。`change_note` 三路行为已经通过；在临时副本删除重放参数后，回归确实变红。尚未观察到新的参数行为错误，故保留为非阻塞的判断性建议，不与 Spec 问题重复计数。

四张修复票遵守独立文件及 Comments 追加约定。后续 17/18 勾选属于新的验收收口，没有当作擅改旧修复历史。票 03/04 留档中的“两轴”包含 Spec 实施自查，不能扩写为当时两轴都由独立子代理执行；修复批次约定本身只要求两轴复查和留档。

独立报告：[standards-review.md](/tmp/mygamestudio-review-2-zgbhMN/standards-review.md)；定向及变异证据：[standards-probe-results.json](/tmp/mygamestudio-review-2-zgbhMN/standards-probe-results.json)。

## Spec

以下先保留独立 Spec 轴四项发现，再列主审两项验收资产发现。原 S/R 编号用于说明关联，不把新的触发条件冒充原反例仍未修复。

### 独立 Spec 复审

**SP-1 · [P1] CONFIG 写授权已撤销，在途远端请求仍写入。** [mgs_runtime.py:953](/Users/cuilei/MyOS/01_Projects/plugins/MyGameStudio/plugin/runtime/mgs_runtime.py:953) 锁内重读身份和 policy，却沿用第 899–940 行锁外读取的 CONFIG、仓库授权及 backend。探针暂停 `append-result` 于取锁前，另一个 GateService 经正常 `write` 入口、携正确内容哈希撤销 CONFIG 的 `issues-write`，返回 allow；恢复原请求后仍 allow，替身新增 1 条评论。随后发起的新请求正确返回 `deny/remote_scope`。这不是原 R1 的身份令牌撤销反例，而是同一最终授权检查的遗漏。违反 [records 合同:39](/Users/cuilei/MyOS/01_Projects/plugins/MyGameStudio/.scratch/mygamestudio-framework/contracts/records.md:39) 的“创建或修改远端记录前核对明确的仓库及操作授权”。应在最终临界区重读 CONFIG 授权和目标，并据此构建 backend。证据：[extra-probes.json](/tmp/mygamestudio-spec-review-2-dnioch5b/extra-probes.json)，`remote-config-revoke-inflight`。

**SP-2 · [P2] 评论已成功发布，后续索引更新超时却报告拒绝，重试造成重复。** [mgs_github.py:846](/Users/cuilei/MyOS/01_Projects/plugins/MyGameStudio/plugin/records/mgs_github.py:846) 在评论创建后更新 Issue 正文索引，超时直接抛出；[mgs_runtime.py:981](/Users/cuilei/MyOS/01_Projects/plugins/MyGameStudio/plugin/runtime/mgs_runtime.py:981) 把它变成 `deny/remote_upstream`，未携已发布 comment_id。通过 MCP 入口注入 POST 成功、后续 PATCH 超时：首次返回 deny，但已有 1 条评论；清除故障后同请求重试返回 allow，已有 2 条。当前审计有 intent/deny，问题是结果语义失真，不是“没有审计”。违反 [runtime 合同:16](/Users/cuilei/MyOS/01_Projects/plugins/MyGameStudio/.scratch/mygamestudio-framework/contracts/runtime.md:16) 和 [records:39](/Users/cuilei/MyOS/01_Projects/plugins/MyGameStudio/.scratch/mygamestudio-framework/contracts/records.md:39)。应保留部分成功和评论身份，恢复时只补未完成的索引。原 S2 回读失败不重发、原 R4 审计失败的反例均已修复；本项是邻近残留路径。证据：[partial-remote-probe.json](/tmp/mygamestudio-spec-review-2-dnioch5b/partial-remote-probe.json)。

**SP-3 · [P2] 草稿幂等身份忽略仓库，丢失另一仓库的相同请求。** [mgs_github.py:542](/Users/cuilei/MyOS/01_Projects/plugins/MyGameStudio/plugin/records/mgs_github.py:542) 的哈希和第 557 行 prior 判断只有 op/args。同一秒、同一 cache、两个各有写授权的仓库，保存同身份/标题/参数的离线创建请求，第二次返回旧草稿及 `idempotent:true`，只有一份草稿且 repo 仍为旧仓库。当前仓库发布时 S1 正确拒绝该旧草稿，`published_count=0`；新仓库请求没有保存。违反 [修复票 01:20](/Users/cuilei/MyOS/01_Projects/plugins/MyGameStudio/.scratch/mygamestudio-v1-review-fixes/issues/01-records-backend-review-fixes.md:20) 的操作身份要求及 [project-configuration:37](/Users/cuilei/MyOS/01_Projects/plugins/MyGameStudio/.scratch/mygamestudio-framework/contracts/project-configuration.md:37) 的草稿保存语义。应把目标仓库纳入身份和幂等比较。证据：[extra-probes.json](/tmp/mygamestudio-spec-review-2-dnioch5b/extra-probes.json)，`S6-cross-repo-idempotence`。

**SP-4 · [P2] 独立秘密扫描会忽略部分缺失的扫描根并退出成功。** [secret_scan.py:84](/Users/cuilei/MyOS/01_Projects/plugins/MyGameStudio/acceptance/16-producer-complete-loop/secret_scan.py:84) 对不存在的目录执行 `os.walk` 后静默无产出，第 134 行只检查所有根的总文件数。给它存在的干净 evidence、不存在的 project、有效且含一条登记的 registry，退出 0，称扫描 1 文件且无秘密。一个目录非空掩盖了另一个指定输入缺失；应逐根核验存在性和遍历错误并退出 2。依据：[修复票 04:22](/Users/cuilei/MyOS/01_Projects/plugins/MyGameStudio/.scratch/mygamestudio-v1-review-fixes/issues/04-credential-leak-evidence-sanitize.md:22) 的独立扫描闭环，以及扫描器自身输入错误约定。这不表示本次正式扫描实际漏了文件或有残留明文。证据：[missing-scan-target.json](/tmp/mygamestudio-spec-review-2-dnioch5b/missing-scan-target.json)。

### 主审补充：票 18 验收资产

**SP-5 · [P2] 新增离线实例未纳入脱敏及秘密检查，注入明文仍通过。** [run.sh:747](/Users/cuilei/MyOS/01_Projects/plugins/MyGameStudio/acceptance/18-complete-package-acceptance/run.sh:747) 新签发 `g_o`，但 [sanitize:388](/Users/cuilei/MyOS/01_Projects/plugins/MyGameStudio/acceptance/18-complete-package-acceptance/run.sh:388) 和 [LEAK:940](/Users/cuilei/MyOS/01_Projects/plugins/MyGameStudio/acceptance/18-complete-package-acceptance/run.sh:940) 仍只枚举旧六个前缀。把本脚本的函数与检查原样提取到 `/tmp`，在 `g_o.token` 与证据文件放入同一合成令牌：脱敏后令牌仍在，原 LEAK 检查退出 0；独立扫描器对同一夹具退出 1。原 R6“新签发实例不应靠枚举遗漏”的问题在票 18 新资产中再次出现，违反 [runtime:48](/Users/cuilei/MyOS/01_Projects/plugins/MyGameStudio/.scratch/mygamestudio-framework/contracts/runtime.md:48)。应覆盖全部实例并接入独立扫描。**当前历史证据未发现 g_o 明文泄漏**；本发现证明检查会假绿，不能反向宣称已经泄漏。证据：[acceptance-probes.json](/tmp/mygamestudio-review-2-zgbhMN/acceptance-probes.json)。

**SP-6 · [P2] 新增“原始事件”分支只查词串，可把 allow 示例当作实际 path 拒绝。** [run.sh:857](/Users/cuilei/MyOS/01_Projects/plugins/MyGameStudio/acceptance/18-complete-package-acceptance/run.sh:857) 用 OR 接上对整个 JSONL 的关键词 grep，不限制事件类型、工具、decision 或目标。临时夹具中报告不含结果，事件只有一条 `agentMessage`，文字举例 `decision=allow, rule_stage=path`，没有任何 MCP 调用，原判据仍输出 PASS。应解析真实 `mcpToolCall` 的返回，并同时核对目标、`decision=deny`、`rule_stage=path`；报告措辞可作补充。违反 [票 18:13](/Users/cuilei/MyOS/01_Projects/plugins/MyGameStudio/.scratch/mygamestudio-v1/issues/18-complete-package-acceptance.md:13) 的实际交付包集成回归要求。**本次留存 R1 确有真实 `mgs_write` 的 deny/path 结果**，不是假造本轮通过；缺陷在新检查语义允许未来假绿。证据：[acceptance-probes.json](/tmp/mygamestudio-review-2-zgbhMN/acceptance-probes.json)，历史真实结果见 [r1-events.jsonl:12](/Users/cuilei/MyOS/01_Projects/plugins/MyGameStudio/acceptance/18-complete-package-acceptance/evidence/r1-events.jsonl:12)。

## 逐对象复核

### A. 修复批次四票

“原反例修复成立”不代表所有相邻时序、组合或恢复路径均满足完整合同。

| 对象 | 结论 | 当前证据及边界 |
| --- | --- | --- |
| S1 错仓库发布 | 原反例真实修复 | 去掉仓库比较后 4 条断言失败；恢复后通过，原草稿保留 |
| S2 回读失败重发 | 原反例真实修复 | POST 一次、回读失败返回 uncertain，通道回归通过；另有 SP-2 |
| S3 反向迁移 | 修复成立 | 计划、文件、CONFIG、返回目录一致；真实 Python CLI 经 localhost HTTP 回归通过 |
| S4 交接可达 | 修复成立 | 未检查/离线不报可达；2xx 才通过；探测不携凭据；B 的 CLI 漏改已补 |
| S5 缓存元信息 | 修复成立 | cached/fetched_at/source/cache_note 传到顶层，定向回归通过 |
| S6 同秒覆盖 | 原同仓库反例修复 | 不同内容保留两份，当前测试通过；跨仓库组合遗漏见 SP-3 |
| 原建议 1 | 闭合 | 公共任务核验单一实现，同一畸形任务两侧均失败 |
| 原建议 2 | 行为修复、结构部分闭合 | change_note 三路一致；撤去重放参数回归变红；保留 ST-1 |
| R1 身份撤销 | 原本地/远端反例修复 | 锁内重读身份，撤销后不写；CONFIG 撤销是新缺口 SP-1 |
| R2 用途缺失 | 真实修复 | write/scope/remote 三路失效闭合；恢复旧默认值后 6 条断言失败 |
| R3 权限位 | 修复成立 | 0755/0600 更新及审计失败回滚的内容/权限回归通过 |
| R4 审计时序 | 原反例修复 | 意图审计失败时零评论；结果审计失败如实返回已发生结果；另有 SP-2 |
| R5 包字节 | 修复成立 | 干净 git 副本重建后三项产物字节相等；两份 tar 均无 PAX 扩展头 |
| R6 脱敏及历史 | 原泄漏处置成立，机制仍有缺口 | 两枚 released=true；全对象未命中；23 对提交仅两文件指定替换；另有 SP-4/SP-5 |

四票当前勾选分别为 6/6、5/5、5/5、5/5。票面原反例闭合有测试及代码支持，但不能据此扩大成完整远端授权、部分成功恢复、全部验收秘密检查已闭合。

| 变异 | 当前版本 | `/tmp` 还原修复 | 恢复当前代码 |
| --- | --- | --- | --- |
| A-S1 去掉草稿仓库比较 | exit 0 | exit 1，4 个失败断言 | exit 0 |
| A-R2 缺失用途回退为无限制 | exit 0 | exit 1，6 个失败断言 | exit 0 |
| B-handover 恢复拼错函数名 | exit 0 | exit 1，JSON 输出断言失败 | exit 0 |
| 原建议 2 去掉重放 change_note | exit 0 | exit 1 | 定向原版通过；副本与真仓库隔离 |

B 的拼错与正常“不可交接”都可能令 CLI 退出 1，新增 JSON 断言确实能识别崩溃；没有用退出码伪装通过。上述结果证明当前回归能捕获反例；没有把本轮绿→红→绿反推为历史红测试的时间戳证明。详见 [Spec 独立报告](/tmp/mygamestudio-review-2-zgbhMN/spec-review.md) 和 [spec-probes.json](/tmp/mygamestudio-review-2-zgbhMN/spec-probes.json)。

### B–E. 后续验收、反馈与全局纪律

| 对象 | 复核结论 | 证据及限制 |
| --- | --- | --- |
| B 真实 GitHub | 当前终态与留档一致 | 只读 GET 确认私有仓库、恰 3 issue；#1 closed/completed，#2 closed/not_planned，#3 open/agent-ready；#1 有一条结果评论和一条关闭说明，原生 sub-issue 含 #3；22 个已留档 JSON 判据复算全过 |
| B handover 修复 | 成立 | JSON 断言的绿→红→绿见上表 |
| C 最终单遍 | 留存单遍成立，不能据此抹去新增缺陷 | `/tmp/mgs-accept-18-closure.log` 实数 137 条 PASS、0 FAIL；9 个 completed turn，9 份报告与事件中的去重 agentMessage 拼接逐字一致；不重新调用模型 |
| C 升级 | 现存内容核对成立 | 旧快照 79 文件与 git 0.17.0 一致；新安装 79 文件与当前 plugin 一致；实测变化 7 文件恰等于 git 推导，零新增/删除差异 |
| C 历史调用次数 | 未完全核验 | 找到最终轮日志及早间 run2/run3 日志，未找到收口 runA–runD 完整过程；“5 次运行、约 5+9×4 轮”仅有 Comments 声明，不能独立确认精确消耗，也无依据判为虚报 |
| D 开发者试玩留档 | 如实区分，未把不存在包装成通过 | 02/11 对应反馈为跟手、HUD 清楚有高亮；06/10 保持待验收，08 待 05，两设计决定待答。实际 build/main.js 对 assets/、SVG、WAV 均零引用；两个 SVG 和一个 WAV 存在，方向键处理存在 |
| E 五套件 | 5/5 退出 0 | plugin_package、runtime_gate、runtime_boundaries、records_backend、github_backend；只在干净 `/tmp` 副本运行，禁写 Python 字节码 |
| E 驱动 | 33 PASS / 0 FAIL | 临时隔离安装的 MCP 进程与 localhost 替身；没有验收模型轮或真实远端写入 |
| E 打包 | 通过 | tar.gz、package-manifest.txt、SHA256SUMS.txt 三项逐字节一致，79 个包内文件由 package 套件核对源/清单/包；SHA-256 为 `cb5ff8e7f2292b1e2a316c7ba69207068ab36f103bdb1eefecebcf6aec81c611` |

B 的 38/0 属历史验收声明，本轮未重放远端写入，也没有独立重放历史“初始空仓库”检查或恢复每个命令的原退出码；本轮支持的是当前终态、留存数据判据与 CLI 修复。两个 #1 评论内容分别是结果与关闭说明，未误判为重复评论。

D 留档中的 02/06/08/10/11 是试玩遗留事项编号，不能误解成对本插件原始 18 张票重新作全面验收。人工手感、审美、听感只按原反馈引用，本次没有代用户体验或裁决。

## 票 18 六项验收资产修复的独立判断

| 项 | 布景/检查缺陷是否成立 | 是否弱化语义或引入遗漏 |
| --- | --- | --- |
| 1 OLD_COMMIT 替换 | **成立**。旧链备份与新链逐提交核对，0.17.0 内容相同，当前有效提交为 36c432c | 未弱化；没有把旧哈希失效当伪造 |
| 2 升级变更集改 git 推导 | **成立**。审查批又改了三个实现文件，原四文件清单过时；安装实差 7 文件与 git 结果相等 | 未弱化当前“变化可发现/安装与交付同源”要求；仍有 exact、零单侧文件及源码一致检查。它不是独立判断改动是否获准的审查替代品 |
| 3 G 离线探针专用实例 | **成立**。旧实例未获 03 资源授权，提前 task_grant 拒绝；专用实例让探针进入 remote_upstream，之后草稿/恢复链路有结果 | 核心探针未弱化，但新增 g_o 的脱敏/扫描配套漏改，见 SP-5 |
| 4 G 建单补完成标准/执行责任 | **成立**。共享任务校验要求这些字段，旧夹具不完整 | 未弱化；补输入而保留校验，当前任务及 verify 结果支持 |
| 5 R 角色探针补任务授权 | **成立**。要单独验证角色层拒绝，任务层必须先允许；implement 角色依然不包含目标 | 未弱化；实际 R1 第 3 步 deny/role_scope、目标不存在，驱动回归也通过 |
| 6 G1/R1 措辞词族 | **原措辞误判成立；新判据部分不成立**。G1 原始 curl 返回 exit 7/Failed to connect，扩充该词族合理；R1 表格确记录 deny/path，原正则距离不匹配 | G1 当前实际直连失败可核对，单靠 exit 7 不能穷尽证明失败根因。R1 新增任意事件 grep 会接受无 MCP 的 allow 示例，构成 SP-6；不能把整项概括为“只修布景且语义等价” |

当前 R1 的真实拒绝没有依赖模型转述：已解析 `mcpToolCall` 的 deny/path。过滤后的 `r1-events.jsonl` 没有保留两次间接写入命令的子事件，进一步核对指定隔离会话的原始 rollout 第 73/77 行，找到两条实际工具返回的 Operation not permitted，已保存无凭据摘录到 [r1-raw-indirect-proof.json](/tmp/mygamestudio-review-2-zgbhMN/r1-raw-indirect-proof.json)。这补足本次核对，不表示仓库内过滤证据本身包含所有原始工具输出。

## 证据核对与验证边界

1. **秘密扫描实测范围。** 独立扫描 1,238 个跟踪文件、512 个验收项目文件、79 个包内文件；对真实仓库全部 2,091 个本地 Git 对象中的 1,478 个 blob 扫描。比对 23 份运行登记/快照形成的 68 个 token_hash（含两枚历史 R6 摘要），并扫描常见 GitHub/OpenAI 令牌前缀：没有命中。额外 token 字段规则仅发现一处全同字符的拒绝探针值，不是已登记令牌。没有把文件 SHA-256 当执行凭据。
2. **随仓库扫描器复跑。** 用合并的登记摘要对现存 acceptance、scratch、plugin 及相关项目执行，1,425 文件、68 摘要，退出 0。所有本次明确指定的根均存在。SP-4/SP-5 的合成反例不会被当作正式证据泄漏。扫描是有限已知摘要及模式，不是“任何未知格式秘密绝不存在”的证明。
3. **历史改写质量。** 在 `/tmp` 从用户给定 bundle 建只读对照数据库，并从本地仓库导入清理后的链；23 对提交逐一比较，所有 tree 差异只在 t6b/t9b 两文件，且内容恰为那两枚令牌替换成指定占位符。16 个早期提交哈希未变，实际为初始化提交加票 1–15；从票 16 起改写。交接材料“票 1–7 保留、其后全部变化”的范围描述不精确，本次以 bundle 逐提交映射为准；这不影响两文件精确脱敏结论，也不据此指控证据伪造。真实仓库全对象扫描未找回两枚明文。当前 Codex 检查点 ref 是现存新快照，不据其名称判为旧泄漏 ref 残留。验证后已删除本任务新建的含旧对象临时数据库，用户原 bundle 未动。
4. **撤销状态。** 原 `.tmp/accept-16/runtime/instances.json` 中两枚指定登记均为 `released=true`，与票 04 后续 Comments 相符。旧 `r6-credential-status.json` 的 released=false 是处置前快照，不当成当前矛盾。
5. **会话证据。** 9 个最终 turn 均 completed/error=null，报告逐字可从事件重建；四份审计共 59 行、JSON 可解析且时间顺序正常。最终轮日志确有 137 个 PASS，17 个留存 JSON 判据重新求值均成立；旧版及新版安装树、七文件变化另作内容哈希核对。日志内部一致和本机原始会话支持已述观察，不是对所有历史事实的密码学证明。
6. **尚未核验。** 没有重跑真实模型轮；没有实际远端写入重放；收口 runA–runD 的逐轮原始日志和精确成本未找到；历史红测试的原始发生顺序不能由当前变异证明；没有新人工试玩/审美/试听，也没有安装到日常客户端或发布。

主要复核产物：[测试结果](/tmp/mygamestudio-review-2-zgbhMN/suite-results.json)、[33 项驱动日志](/tmp/mygamestudio-review-2-zgbhMN/driver-probes.log)、[重打包日志](/tmp/mygamestudio-review-2-zgbhMN/reproducible.log)、[秘密扫描](/tmp/mygamestudio-review-2-zgbhMN/secret-scan-results.json)、[历史映射验证](/tmp/mygamestudio-review-2-zgbhMN/history-rewrite-verification.json)、[会话核对](/tmp/mygamestudio-review-2-zgbhMN/session-evidence-verification.json)、[远端 JSON 复算](/tmp/mygamestudio-review-2-zgbhMN/evidence-json-recheck-17.json)。机器摘要：[verification-summary-2.json](/tmp/mygamestudio-review-2-zgbhMN/verification-summary-2.json)。

## 实际执行的命令类别

- 只读 Git：rev-parse、status、log、diff、show、archive、ls-tree、for-each-ref、reflog、cat-file、bundle list-heads；没有对真实仓库 fetch 或改 refs。
- 本地 Git clone/fetch/archive 只写 `/tmp` 隔离副本；对照完成后仅删除本任务创建的旧对象数据库。
- rg/cat/sed/nl 与 Python 读取、JSON 解析、内容哈希、源码/安装/包比对。
- `/tmp` 内五套 Python 测试、定向测试、绿→红→绿变异及故障注入；采用进程内 FakeTransport 或 localhost HTTP 替身。
- `/tmp` 隔离客户端的插件安装和 MCP 驱动回归；不启动验收模型轮。
- `/tmp` 内 `bash dist/verify-reproducible.sh`、隔离打包、cmp/PAX 检查。
- `gh api --method GET`：测试仓库资料、issue、标签、评论、sub_issues，以及 MyGameStudio main；真实远端仅 GET。
- 已登记令牌摘要及有限服务令牌模式扫描；报告和机器摘要仅写 `/tmp`。

## 交付判定

当前可以交付这份复审和经过核对的原验收证据，但 **v1 完整收口仍不通过**。应先修 SP-1 远端授权时序，以及 SP-2/SP-3 的结果恢复和草稿身份，再补齐 SP-4–SP-6 的扫描及验收判据，针对新增反例复核。人工体验项继续按票 16 的真实状态保留；本报告不授权代码修复、改票、凭据处理、安装或发布。

结束复核：HEAD 仍为 `b89b548f59336f57f63df70bda331bc204bd12de`，与开始相同；`git status --porcelain` 输出为空。实际主分支的额外提交仅为交接文档，指定审查基线 `d934332` 的产品与验收范围没有被替换。

Standards：0 硬违反、1 项 P3 判断性建议；Spec：6 项（1 P1、5 P2），最高 P1 为 CONFIG 授权撤销后在途远端写入。

# MyGameStudio v1 第三轮独立复审

**交付判定：六项原始反例均已转绿，修复不是仅靠叙述成立；但 SP-2、SP-6 的完整要求尚未闭合，本轮另有 3 项 P2 复审发现，当前不具备 v1 收口条件。** SP-1、SP-3、SP-4、SP-5 的本轮要求有实证支持。Standards 轴 0 项硬违反、0 项新增判断性异味，原 ST-1 已闭合。五套件、33 项驱动、包与源一致性和字节可复现打包全过，未覆盖的邻近反例见 Spec。

复审执行日期：2026-09-10（Asia/Shanghai）；委托与修复批次日期为 2026-09-09。Standards、Spec 按 code-review 技能在两个独立审查上下文执行；主审复跑底稿、变异、验收资产和必要检查。

- 真实仓库：`/Users/cuilei/MyOS/01_Projects/plugins/MyGameStudio`。
- 固定范围：`git diff 9376dec..18df620`；基线 `9376deccf8a3d0125a0f7598872ae37d64a55d94`，目标 `18df620185c6ef920e9f33f7dea27631ea35e98b`。
- 恰四提交，自旧至新：`e482f84`、`7667d69`、`fe4004f`、`18df620`。
- 实际开始及结束 HEAD 均为 `8cdc4c425e11864f96d755b6c2cdb573a97fe7b9`，分支 main。其相对目标仅新增 `.scratch/mygamestudio-v1-review2-fixes/evidence/review-3-handoff.md`，产品与验收范围未变。
- 开始、结束 `git status --porcelain` 均为空。真实仓库零改动、零提交、零推送；零真实远端写入、零验收模型调用。所有测试、变异、临时安装、重打包及报告均在 `/tmp`；真实运行根只读。
- 原始记录：[baseline.json](/tmp/mygamestudio-review-3-v9s0lp_z/baseline.json)、[batch.diff](/tmp/mygamestudio-review-3-v9s0lp_z/batch.diff)、[结束边界检查](/tmp/mygamestudio-review-3-v9s0lp_z/final-boundary-check.json)。

## Standards

**0 项明文规范硬违反；0 项新增判断性异味；ST-1（P3，Repeated Switches）闭合。**

[GithubBackend.execute_op:1090](/Users/cuilei/MyOS/01_Projects/plugins/MyGameStudio/plugin/records/mgs_github.py:1090) 统一七项写操作参数分发；[在线入口:1119](/Users/cuilei/MyOS/01_Projects/plugins/MyGameStudio/plugin/runtime/mgs_runtime.py:1119) 与 [草稿重放:1128](/Users/cuilei/MyOS/01_Projects/plugins/MyGameStudio/plugin/records/mgs_github.py:1128) 均调用它。七操作 × 两路径共 14 组参数录制全过；删除共享 `change_note` 后两路同时变红，恢复全绿。只读 read 独立包装任务结构，未留下原写操作的两份分发。

四票独立编号文件、合法 Status、Comments 追加和两轴留档均符合 [issue-tracker.md:7](/Users/cuilei/MyOS/01_Projects/plugins/MyGameStudio/docs/agents/issue-tracker.md:7) 与 [批次 spec.md:25](/Users/cuilei/MyOS/01_Projects/plugins/MyGameStudio/.scratch/mygamestudio-v1-review2-fixes/spec.md:25)。本批未改 v1 原票、第一轮修复票的勾选历史。票面两轴记录按实施自查理解，没有扩写为当时由两个独立代理执行。

`_remote_config_state` 服务于两次必要核验；partial 草稿保留属于票 02 同一未完成操作；扫描与事件判据分别在票 03/04 范围。未见新增依赖、领域术语或文档组织规则冲突。此轴通过不抵消下列行为问题。

独立报告与证据：[standards-review.md](/tmp/mygamestudio-review-3-v9s0lp_z/standards-review.md)、[standards-probe-results.json](/tmp/mygamestudio-review-3-v9s0lp_z/standards-probe-results.json)。

## Spec

原 SP-1～SP-6 编号保留。下列 SP-7～SP-9 表示本轮新报告的反例，不表示三个问题都由本批首次引入，也不把新的触发条件冒充旧底稿仍红。前两项来自独立 Spec 轴，第三项为主审补充。

### SP-7 · [P2] 已确认部分成功后，读前查询失败仍重复发布评论

[mgs_github.py:807](/Users/cuilei/MyOS/01_Projects/plugins/MyGameStudio/plugin/records/mgs_github.py:807) 将评论 GET 超时记入 attempts 后继续，[824](/Users/cuilei/MyOS/01_Projects/plugins/MyGameStudio/plugin/records/mgs_github.py:824) 再次 POST。通过 MCP 入口：首次 POST 成功、索引 PATCH 超时，返回 `allow + published=true + partial=true + comment_id=5100 + index_updated=false`；恢复 PATCH，仅让重试的第一次评论 GET 超时，第二次返回 allow、comment_id=5101。替身累计 **2 次评论 POST、2 条评论**，第一次已发布评论未被此次索引补齐。

违反 [票 02:15](/Users/cuilei/MyOS/01_Projects/plugins/MyGameStudio/.scratch/mygamestudio-v1-review2-fixes/issues/02-partial-success-and-draft-repo-identity.md:15) 的“恢复/重试只补未完成的索引更新,不重复发布”，以及 [records 合同:39](/Users/cuilei/MyOS/01_Projects/plugins/MyGameStudio/.scratch/mygamestudio-framework/contracts/records.md:39) 的“用返回身份或请求关联回读实际状态，避免重复创建”。票面已披露读前失败继续发布的取舍；“本次调用尚未发布”不能消除前一次已确认发布的事实，故这不是未披露风险的指控，而是对取舍是否满足要求的否定。

原 SP-2 的正常恢复底稿、S2 的单次发布后 uncertain、R4 的审计时序仍通过。应保留/传递已发布操作身份，在查询失败时保持待恢复状态，不能把它当作全新发布；同时保留 S2、partial 的不同结果语义。本轮未实现修复。

证据：[spec-probes.json](/tmp/mygamestudio-review-3-v9s0lp_z/spec-probes.json)，`partial-retry-read-first-timeout`；[可复跑脚本](/tmp/mygamestudio-review-3-v9s0lp_z/spec-custom-probes.py)。

### SP-8 · [P2] MCP 锚定仍可由错误目标或错误动作满足

[run.sh:118](/Users/cuilei/MyOS/01_Projects/plugins/MyGameStudio/acceptance/18-complete-package-acceptance/run.sh:118) 只提取 path/identity，[126](/Users/cuilei/MyOS/01_Projects/plugins/MyGameStudio/acceptance/18-complete-package-acceptance/run.sh:126) 对调用与返回双方做子串包含判断，未核预期动作。

- 真实 GateService 对 `/tmp/mgs18-evil-link.md.bak` 返回 deny/path。用该真实返回构造对应 MCP 事件夹具，正式 R1 目标 `/tmp/mgs18-evil-link.md` 的锚定仍输出 **OK**，尽管两者不是同一文件。
- 真实 GateService 对 `01-harbor-timer` 的 `append-result` 返回 deny/task_grant。同一事件使 [G1“越界更新被拒”判据:857](/Users/cuilei/MyOS/01_Projects/plugins/MyGameStudio/acceptance/18-complete-package-acceptance/run.sh:857) 输出 **OK**，没有执行 update。

违反 [票 04:15](/Users/cuilei/MyOS/01_Projects/plugins/MyGameStudio/.scratch/mygamestudio-v1-review2-fixes/issues/04-anchor-checks-to-real-tool-returns.md:15) 的“同时核对目标”及第 17 行“检查必须反映实际行为”。双侧含子串不能证明目标一致；应规范化后核对具体资源和动作，兼容已知相对/绝对路径及 GitHub URI 形态。

原无 MCP 的 allow 示例已正确拒绝；五份留存事件流仍 10/10 OK。此反例证明未来检查可错配，不能反向证明历史 R1/G1 没有真实调用。另一组 read→update 探针得到 MISSING，**未复现**，没有列为问题。

证据：[spec-probes.json](/tmp/mygamestudio-review-3-v9s0lp_z/spec-probes.json)，`wrong-target-prefix`、`append-denial-as-update-proof`；[错误目标事件](/tmp/mygamestudio-review-3-v9s0lp_z/wrong-target-prefix.jsonl)。

### SP-9 · [P2] 只打印 curl 示例的失败命令仍被认作直连探针

[run.sh:150](/Users/cuilei/MyOS/01_Projects/plugins/MyGameStudio/acceptance/18-complete-package-acceptance/run.sh:150) 用命令字符串是否包含 curl、127.0.0.1 判断执行对象，再于 [152](/Users/cuilei/MyOS/01_Projects/plugins/MyGameStudio/acceptance/18-complete-package-acceptance/run.sh:152) 检查失败状态与输出词族。真实执行下面的本地 shell 命令后，将实际退出码和输出放入 `commandExecution` 形态夹具，新函数仍返回 **OK**：

```sh
printf '%s\n' 'curl http://127.0.0.1:1/_test/ping (example only)' 'Failed to connect (example only)'; exit 7
```

该命令只调用 printf 并退出 7，**没有执行 curl、没有直连替身**。这是以实际本地进程输出构造的合成事件流，不冒充历史 Codex 会话事件。新函数确实排除了 agentMessage 示例，但仍把命令参数里的示例当作执行对象。

违反 [票 04:16](/Users/cuilei/MyOS/01_Projects/plugins/MyGameStudio/.scratch/mygamestudio-v1-review2-fixes/issues/04-anchor-checks-to-real-tool-returns.md:16) 的 G1 同类判据加固要求，以及该票 Implementation 对“命令确为 curl 直连替身”的声明。应将固定探针调用与实际命令/目标关联，不能仅查命令全文词串。此项与 SP-8 的 MCP 资源/动作错配分开计数，修复位置也不同。历史 G1 真正 curl 失败形态仍通过，本轮未重审其沙箱失败根因。

证据：[acceptance-probes-3.json](/tmp/mygamestudio-review-3-v9s0lp_z/acceptance-probes-3.json)，`curl_example_false_positive`；[命令事件夹具](/tmp/mygamestudio-review-3-v9s0lp_z/acceptance-fixtures/curl-command-example.jsonl)、[可复跑脚本](/tmp/mygamestudio-review-3-v9s0lp_z/acceptance_recheck.py)。

## 逐票复核

| 票 / 对象 | 结论 | 实测与边界 |
| --- | --- | --- |
| 01 / SP-1 | 本轮要求通过 | 原锁前暂停→正常 write 撤授权→恢复，deny/remote_scope、0 POST、0 评论；另测在途切换 local-markdown 后端同样拒绝，改到实例无授权的新仓库 deny/task_grant、0 写入。撤销前合法请求与撤销后新请求回归通过，R1 身份撤销未回退 |
| 02 / SP-2 | 原底稿修复；恢复要求未完整闭合 | 首次 allow/partial/comment_id/index_updated=false；正常恢复重试仍恰 1 条评论、索引补齐。另有 SP-7 的读前故障恢复重复 |
| 02 / SP-3 | 本轮要求通过 | 同秒、同参数、同 cache 两仓库留下 2 份不同草稿；发布时本仓库 1 次 POST，错仓草稿保留。S1/S6 原回归通过 |
| 02 / ST-1、partial 重放 | 结构及正常恢复链修复成立 | 14 组共享分发参数通过；partial 重放先保留草稿、恢复补索引后移出待发布目录。去掉保留条件后 4 条断言变红。属于票 02 同域必要修复，没有越范围 |
| 03 / SP-4 | 本轮要求通过 | 干净非空根+缺失根退出 2 并点名；不可遍历根退出 2；单根零目标退出 2；命中退出 1；干净退出 0 |
| 03 / SP-5 | 本轮要求通过 | g_o 合成明文被替换；含无效 UTF-8 的证据也能脱敏；重新注入未脱敏明文后独立扫描判 FAIL；干净判 PASS；非 hex GHTOKEN 合成明文直查判 FAIL；真实四运行根扫描通过 |
| 04 / SP-6 | 原底稿修复；锚定要求未完整闭合 | 无 MCP 的 allow 示例得到 MISSING，真实 deny/path 形态通过，留存 5 份流共 10 锚定通过；仍有 SP-8/SP-9 错配假绿 |

### 每票变异：当前绿→还原修复红→恢复绿

| 变异 | 当前退出码 | 变异退出码 / 失败断言数 | 恢复退出码 |
| --- | --- | --- | --- |
| 01：移除锁内 CONFIG 重读 | 0 | 1 / 3 | 0 |
| 02：还原旧 append_result | 0 | 1 / 10 | 0 |
| 02：草稿身份还原为不含 repo | 0 | 1 / 8 | 0 |
| 02：去掉 partial 草稿保留 | 0 | 1 / 4 | 0 |
| 03：还原旧扫描根遍历 | 0 | 1 / 3 | 0 |
| 03：sanitize 还原固定枚举 | 0 | 1 / 4 | 0 |
| 03：LEAK 还原固定枚举 | 0 | 1 / 5 | 0 |
| 04：R1 path 还原旧词串判据 | 0 | 1 / 4 | 0 |

均在主审 `/tmp/copy` 中逐项变异并恢复；源码最终与固定目标归档逐字节相等。红结果包括实际在途写入、重复评论/丢草稿、遗漏令牌与错误 PASS，不是仅凭运行崩溃判红。Standards 另有共享 change_note 的进程内变异，两路径同时红后恢复。

证据：[mutation-results.json](/tmp/mygamestudio-review-3-v9s0lp_z/mutation-results.json)、[mutations.py](/tmp/mygamestudio-review-3-v9s0lp_z/mutations.py)。这证明当前回归对撤去修复敏感，**不能证明历史红测试发生的时间顺序**。

## 证据核对与验证边界

1. **五套件与驱动。** 在固定 `18df620` 的 `/tmp` 本地克隆中，先清副本 `plugin/**/__pycache__`，用 `PYTHONDONTWRITEBYTECODE=1`、`python3 -B`、`TMPDIR=/tmp` 执行 plugin_package、runtime_gate、runtime_boundaries、records_backend、github_backend，5/5 退出 0。`driver-probes.sh` 在本次专用环境中临时安装插件并驱动实际 MCP 进程/localhost 替身，**33 PASS / 0 FAIL、退出 0**。没有运行任何完整 acceptance run.sh 或模型 turn。[五套结果](/tmp/mygamestudio-review-3-v9s0lp_z/suite-results.json)、[驱动日志](/tmp/mygamestudio-review-3-v9s0lp_z/driver-probes.log)。
2. **包与源。** package 套件核对 79 个文件的源、清单及包内容；`dist/verify-reproducible.sh` 从隔离克隆的 HEAD 归档重建，tar.gz、package-manifest.txt、SHA256SUMS.txt 三项逐字节一致，两个 tar 均无 PAX 扩展头。包 SHA-256：`dcaa012e49ede08c3e4d12a15b3aaaa0f610505de85349240348aefea91a0f91`。16/18 的 run.sh、驱动和 verify 脚本 `bash -n` 全过。[重打包日志](/tmp/mygamestudio-review-3-v9s0lp_z/reproducible.log)。
3. **合法路径开销。** 同夹具分别加载 `9376dec`、`18df620`，read/update/append-result 均 allow。CONFIG load 次数均从 1→2；替身调用数 read 3→3、update 3→3、append-result 7→8，后者新增一次评论 GET，服务于票 02 的读前收养。未见额外远端重试开销；没有测真实远端延迟、并发吞吐或 p95，因此不宣称性能数字不变。[legal-path-cost.json](/tmp/mygamestudio-review-3-v9s0lp_z/legal-path-cost.json)。
4. **真实四运行根接线。** 只读使用真实 `.tmp/accept-18/{upg,p,gh,reg}/runtime/instances.json`、四项目根及 ARENA 的 7 个 token 文件，提取原样 LEAK 段，仅把证据输出目录定向 `/tmp` 内的目标版本证据副本。四根登记摘要分别 1/2/2/2 项，四次扫描均退出 0；单次文件统计 226/227/228/229，包含扫描过程中新增的报告，不能相加为独立文件总量。真实 ARENA 前后内容哈希一致；已有脱敏证据在 `/tmp` 再 sanitize 后逐字节不变。仅有限已登记/保存令牌匹配，无命中不等于所有未知秘密绝不存在。[四根报告目录](/tmp/mygamestudio-review-3-v9s0lp_z/live-scan-evidence-pinned)、[扫描与夹具摘要](/tmp/mygamestudio-review-3-v9s0lp_z/acceptance-probes-3.json)。
5. **GHTOKEN 边界。** 非 hex 直查的源码接线保留，并以合成 GHTOKEN 注入证据确认判 FAIL；未重取历史 GHTOKEN 明文。真实四根接线时该变量使用无秘密的哨兵值，故只宣称登记令牌/ARENA 扫描通过，**不宣称重新核验了历史 GHTOKEN 本身**。16 号的既有 sanitize 全 token 遍历与独立扫描回归也通过；不在本轮推扩未知格式秘密扫描。
6. **SP-6 表达与未锚定取舍。** P1/P2 的目标是越界写入被拒，接受 role_scope 或 task_grant 与实际布景相符，留存流确为 task_grant；不能据此宣称单独测到了 role_scope。保留“报告记录 X”属于表达核对，合理。报告结构/内容检查无需一律改成 MCP 锚定。R1 间接写入的历史原始子事件已由第二轮核实、本轮不重复审；文件不存在只证明未生效，单独不能证明曾尝试执行，票面“文件判据锁定行为闭环”应限于这一证据能力。未另报既有历史事项的新缺陷。
7. **底稿适配。** extra_probes.py 与 partial_remote_probe.py 从复审 evidence 复制到本工作区，与 `copy/` 相邻直接运行；三项 observed_bug 均 False。旧 acceptance-probes.py 仍定位已经删除的 `if grep` 段，当前版本不能只换 root 原样使用；本轮采用同法提取当前 sanitize、LEAK、锚定函数，补齐四 RUNROOT/SECRET_SCAN 输入，并保留原 agentMessage/allow 和 g_o 合成夹具。[原探针输出](/tmp/mygamestudio-review-3-v9s0lp_z/extra-probes.json)、[partial 输出](/tmp/mygamestudio-review-3-v9s0lp_z/partial-remote-probe.json)、[适配脚本](/tmp/mygamestudio-review-3-v9s0lp_z/acceptance_recheck.py)。
8. **未核验及范围外。** 未重放真实远端写入、模型轮、安装到日常客户端或发布；未重复审第一轮修复、真实远端终态、票 18 历史单遍、试玩留档、历史改写质量。未独立确认历史红测试原始顺序、未测生产并发/网络性能。人工体验 06/10、08 海鸥、两项设计决定和安装/发布继续由用户决定。没有把这些保留项包装为通过。

## 实际执行的命令类别

- 真实仓库只读 Git：rev-parse、status、branch、log、diff、show、archive；没有 fetch、提交、推送、改 refs 或切换工作树。
- `/tmp` 本地 git clone --no-hardlinks --no-checkout、checkout --detach 固定目标，以及归档解包；不访问真实远端。
- rg、cat、sed、nl、ls 和 Python 读取、JSON 解析、SHA-256、源码/包/运行根前后内容核对。
- `/tmp` 五套 Python 检查、原底稿/定向/邻近故障探针、八项源码变异及进程内参数变异；传输使用进程内 FakeTransport 或 localhost HTTP 替身。
- `/tmp` 隔离的 `codex plugin add`、实际 MCP 驱动、bash -n、secret_scan.py、sanitize/LEAK/锚定函数提取执行；临时 chmod 验证扫描遍历错误后恢复权限。没有验收模型调用。
- `/tmp` 内 verify-reproducible.sh 与 build-package.sh、tar/gzip、cmp 和 PAX 核对；只清理本任务副本缓存/产物。
- 报告、脚本和 JSON 摘要仅写本工作区；没有 gh 远端调用、真实远端写入或对外消息。

## 交付判定

**六项旧反例真实消除，但不能整体判为六项要求全部修复。** SP-1/SP-3/SP-4/SP-5 通过；SP-2 的正常 partial 恢复与 SP-6 的原示例过滤成立，完整恢复/锚定要求分别被 SP-7、SP-8/SP-9 的新反例否定。partial 草稿保留、ST-1 共享分发成立，未见越票面范围。

**当前不具备 v1 收口条件。** 先处理这三项 P2 行为/验收问题并针对性复核，再恢复批次约定的“待用户收口决定”；人工体验与安装/发布授权边界不变。本报告不实施修复、不改票、不安装到日常客户端、不发布。

结束复核：HEAD 仍为 `8cdc4c425e11864f96d755b6c2cdb573a97fe7b9`，与开始相同；`git status --porcelain` 为空。机器摘要：[verification-summary-3.json](/tmp/mygamestudio-review-3-v9s0lp_z/verification-summary-3.json)。

Standards：0 硬违反、0 新判断性异味，ST-1 闭合；Spec：3 项 P2，独立轴 2 项、主审补充 1 项，无本轮 P1。

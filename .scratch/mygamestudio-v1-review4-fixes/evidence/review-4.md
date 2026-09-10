# MyGameStudio v1 第四轮独立复审

**交付判定：SP-7/SP-8/SP-9 的原始反例均真实修复，当前仍不具备 v1 收口条件。** 本轮确认 4 项 P2：无缓存时退化警告缺失且重试重复发布；新增 pending-index 机制存在身份摘要碰撞误认；具体资源锚定仍接受错误路径与衍生身份；shell 包装解析仍可把未执行的 curl 当作直连探针。Standards 轴 0 硬违反、0 需列项的判断性异味。五套件、33 驱动、可复现打包和每票绿→红→绿变异均通过，但未覆盖这四项新反例。

执行日期：2026-09-10（Asia/Shanghai）。按 code-review 技能分开执行独立 Standards、Spec 审查；主审复跑底稿、新反例、变异和必要验证。下文“零模型调用”指零产品/验收模型轮；两轴审查使用本任务的独立审查代理。

- 真实仓库：`/Users/cuilei/MyOS/01_Projects/plugins/MyGameStudio`。
- 固定比较：`git diff 521c465..05a2776`，基线 `521c4652e35614501d1b241b28ba4cc09a4a2742`，目标 `05a277677e191672237e658c27daa867c217360b`。
- 恰两提交：`c9a8021`（review3-01）、`05a2776`（review3-02）。实际 HEAD 为 `5a3ea4f63bc746257c0df13c5938101ca1faaf74`，相对目标只增加 `.scratch/mygamestudio-v1-review3-fixes/evidence/review-4-handoff.md`，无产品差异。
- 开始、结束 HEAD 相同；两次 `git status --porcelain` 均为空。真实仓库零修改、零提交、零推送；零真实远端写入、零验收模型轮。临时安装、变异、驱动证据和报告均在 `/tmp/mygamestudio-review-4-6hm1q78i/` 或打包脚本自己创建的 `/tmp` 目录。
- [开始记录](/tmp/mygamestudio-review-4-6hm1q78i/baseline.json)、[批次 diff](/tmp/mygamestudio-review-4-6hm1q78i/batch.diff)、[结束记录](/tmp/mygamestudio-review-4-6hm1q78i/final-boundary-check.json)。未连接真实 GitHub 核对远端 HEAD；只确认本地固定范围。

## Standards

**0 项明文规范硬违反；0 项需列项的判断性异味。**

依据仓库 `AGENTS.md`、`CONTEXT.md`、`docs/agents/{issue-tracker,domain,triage-labels}.md` 及本批 spec，未发现 ADR。票据保持一票一文件、实施记录追加 Comments；本批未改写 review2 勾选历史。待补索引方法属于后端原有职责，锚定解析集中于原有函数、9 处接线声明预期动作；没有新增依赖或领域术语冲突。摘要构造的少量同形逻辑不足以单列 Duplicated Code。新增反例回归确实存在，实际有效性由下方本轮变异证明，不以票面自查代替。

十二类 smell 均按启发式检查，工具已强制的格式和语法不重复列项。票面行为承诺与运行结果的差异归入 Spec，不把同一问题重复计入此轴。

独立记录：[standards-review.md](/tmp/mygamestudio-review-4-6hm1q78i/standards-review.md)。

## Spec：发现清单

沿用旧编号 SP-7～SP-9 指原反例；SP-10～SP-13 是本轮新报告的反例，不表示四项都由这批首次引入。其中 SP-11 明确由新增登记机制引入。没有发现越出票面范围的新功能。

### SP-10 · [P2] 无缓存时未披露退化，仍承诺不会重复发布

[mgs_github.py:630](/Users/cuilei/MyOS/01_Projects/plugins/MyGameStudio/plugin/records/mgs_github.py:630) 在没有缓存目录时返回 `None`，与登记成功共用同一返回值；[1041](/Users/cuilei/MyOS/01_Projects/plugins/MyGameStudio/plugin/records/mgs_github.py:1041) 仅在返回非 `None` 时追加警告。因此首次 partial 的 note 没有票面承诺的警告，反而继续说“重试同一请求……不会重复发布”。

经真实 MCP 处理入口→GateService→进程内替身：不配置 cache_dir，首次 POST 成功而 PATCH 超时，返回 partial/comment_id=5100；恢复 PATCH，仅让重试第一次评论 GET 超时，第二次返回 allow/comment_id=5101/index_updated=true。累计 **2 POST、2 条评论**，第一条评论未由此次索引补齐。主审独立复跑得到相同结果；Standards 代理另以 Backend 直接入口交叉确认警告缺失及重复。

违反 [票 01:46](/Users/cuilei/MyOS/01_Projects/plugins/MyGameStudio/.scratch/mygamestudio-v1-review3-fixes/issues/01-partial-recovery-no-duplicate.md:46) 的“partial 结果 note 附警告说明”，以及 [票 01:15](/Users/cuilei/MyOS/01_Projects/plugins/MyGameStudio/.scratch/mygamestudio-v1-review3-fixes/issues/01-partial-recovery-no-duplicate.md:15) 的已发布操作恢复要求。重复行为在无缓存模式沿用旧取舍；本轮新增确认的是所谓运行时披露没有落实，不能把票面文字当作用户已经收到的警告。

**取舍判断：当前形态不可接受为已闭合。** 无缓存可作为明确受限的模式讨论，但它不具备跨调用身份保留，当前输出又承诺不会重复；不能据此判定 SP-7 在该配置通过。即使将来补齐警告，也不能把无缓存模式表述为拥有不重复发布保证。

证据：[spec-independent-probes.json](/tmp/mygamestudio-review-4-6hm1q78i/spec-independent-probes.json) 的 `no-cache-partial-retry`；[可复跑脚本](/tmp/mygamestudio-review-4-6hm1q78i/spec-independent-probes.py)；[独立交叉证据](/tmp/mygamestudio-review-4-6hm1q78i/standards-no-cache-probe.json)。

### SP-11 · [P2] pending-index 短摘要碰撞会冒认另一请求的已发布身份

[mgs_github.py:617](/Users/cuilei/MyOS/01_Projects/plugins/MyGameStudio/plugin/records/mgs_github.py:617) 将操作摘要截为 8 个十六进制字符；[667](/Users/cuilei/MyOS/01_Projects/plugins/MyGameStudio/plugin/records/mgs_github.py:667) 读取后只核验是字典，不核验所存 `op/args/repo` 是否与当前请求一致。随后 [704](/Users/cuilei/MyOS/01_Projects/plugins/MyGameStudio/plugin/records/mgs_github.py:704) 直接返回 `published=true` 和登记里的 comment_id。

同仓库 `github.com/mygamestudio/issue-accept`、同任务 `01-task`，结果正文 `collision-result-79891` 与 `collision-result-80657` 均得到摘要 `346df0e9`，共用 `append-result-01-task-346df0e9.json`。让 A 首次调用 partial 留下登记，再让 B 的**第一次调用**仅读前 GET 超时：B 返回 allow/published=true/partial=true/comment_id=5100，实际替身只有 A 的评论，**B 从未发布，全程仅 1 POST**。

这是确定性本地搜索 80,658 个字符串候选得到的可复现碰撞，不是相同数量的远端请求，也不代表已测得生产发生频率。保留完整内容身份并在读入时核对，是避免将另一请求当作本请求已发布证据的必要边界；仅从短文件名推断身份不足。

违反 [票 01:15](/Users/cuilei/MyOS/01_Projects/plugins/MyGameStudio/.scratch/mygamestudio-v1-review3-fixes/issues/01-partial-recovery-no-duplicate.md:15) 的“已确认发布的操作身份保留/传递”、[44](/Users/cuilei/MyOS/01_Projects/plugins/MyGameStudio/.scratch/mygamestudio-v1-review3-fixes/issues/01-partial-recovery-no-duplicate.md:44) 的操作参数及仓库身份约定，以及 [records 合同:39](/Users/cuilei/MyOS/01_Projects/plugins/MyGameStudio/.scratch/mygamestudio-framework/contracts/records.md:39) 的请求关联回读。属于本批新增登记机制引入的缺陷。

损坏边界旁证：将既有登记写成非法 JSON `{`，正确得到“登记不可读”、partial、1 POST；改成合法但缺字段的 `{}`，虽不重发，却不提示 corrupt，仍声称已确认发布并返回空身份。这并入登记内容核验不足，不另加发现编号。

证据：[spec-independent-probes.json](/tmp/mygamestudio-review-4-6hm1q78i/spec-independent-probes.json) 的 `pending-hash-collision`、`corrupt-json`、`corrupt-shape-object`。JSON 含具体候选、登记正文、完整调用结果和实际评论正文；主审已独立复跑。

### SP-12 · [P2] 路径段及 comments 白名单仍接受错误具体资源

[run.sh:129](/Users/cuilei/MyOS/01_Projects/plugins/MyGameStudio/acceptance/18-complete-package-acceptance/run.sh:129) 对绝对期望路径同样采取任意前缀后的整段尾匹配；[164](/Users/cuilei/MyOS/01_Projects/plugins/MyGameStudio/acceptance/18-complete-package-acceptance/run.sh:164) 对调用身份与返回 target 复用同一匹配函数，`comments` 白名单不区分两侧、也不限制出现次数。

- 真实 Gate 对 `/tmp/alternate-root/tmp/mgs18-evil-link.md` 返回 deny/path，正式 `/tmp/mgs18-evil-link.md` 判据输出 **OK**。两个都是明确的绝对路径，不是相对与绝对路径的同一资源。
- 真实 Gate 对 identity=`01-harbor-timer/comments` 的 append-result 返回 deny/task_grant，返回 target 尾部为 `01-harbor-timer/comments/comments`，仍满足正式 `01-harbor-timer` 评论探针；双 `comments` 身份变体也为 OK。调用方任务身份后不应自动接受返回 URI 才需要的派生段。

违反 [票 02:15](/Users/cuilei/MyOS/01_Projects/plugins/MyGameStudio/.scratch/mygamestudio-v1-review3-fixes/issues/02-anchor-resource-action-execution.md:15) 的“具体资源一致”“拒绝前缀/后缀混淆”。原 `.bak` 和动作错配反例确已被拦下，但不能据此宣称完整资源锚定要求闭合。应保留绝对路径与相对路径语境，且将调用身份和返回派生 URI 分别核验；本轮未实现修复。

证据：[spec-independent-probes.json](/tmp/mygamestudio-review-4-6hm1q78i/spec-independent-probes.json) 的 `absolute-prefix`、`identity-comments-suffix`、`identity-double-comments`；[绝对路径事件夹具](/tmp/mygamestudio-review-4-6hm1q78i/spec-independent-absolute-prefix.jsonl)。均由真实 Gate 返回封装为留存 schema 的合成事件，**不是历史模型会话事件**。没有反推历史 R1/G1 未正确执行。

### SP-13 · [P2] shell 脚本参数中的假 curl 仍能充当直连执行证据

[run.sh:197](/Users/cuilei/MyOS/01_Projects/plugins/MyGameStudio/acceptance/18-complete-package-acceptance/run.sh:197) 在 shell 的全部参数中寻找带 `c` 的短旗标，没有在遇到脚本路径时停止解析。因此本地实际执行以下命令：

```sh
/bin/sh /tmp/mygamestudio-review-4-6hm1q78i/curl-new-fixtures/script-before-c.sh -c '/usr/bin/curl http://127.0.0.1:60943/_test/ping'
```

脚本只有 `printf` 输出 `Failed to connect (printed by script; no curl execution)` 和 `exit 7`。shell 实际执行该脚本，`-c` 与 curl 字符串只是脚本参数，**没有执行 curl**。把实际退出码 7、实际输出和原命令装入 commandExecution 夹具，当前 `curl_direct_denied` 返回 **OK**，预期应为 MISSING。

同域旁证：[220](/Users/cuilei/MyOS/01_Projects/plugins/MyGameStudio/acceptance/18-complete-package-acceptance/run.sh:220) 仍仅查参数集合中包含 `127.0.0.1`。真 curl 用 `-H 'X-Example: http://127.0.0.1:端口'` 携带示例，却连接 `127.0.0.2:端口`，实际连接错误地址并失败，仍被判 OK；`curl --version; printf ...; exit 7 # 127.0.0.1...` 也为 OK。只接受已知包装语法和固定探针调用可以保守拒绝不能证明执行的形态，无须宣称实现完整 shell 解释器。三种旁证按同一“实际直连未被证明”要求计一项，不膨胀发现数量。

违反 [票 02:16](/Users/cuilei/MyOS/01_Projects/plugins/MyGameStudio/.scratch/mygamestudio-v1-review3-fixes/issues/02-anchor-resource-action-execution.md:16) 的与实际执行命令关联要求，以及 [review2 票 04:16](/Users/cuilei/MyOS/01_Projects/plugins/MyGameStudio/.scratch/mygamestudio-v1-review2-fixes/issues/04-anchor-checks-to-real-tool-returns.md:16) 的 G1 同类判据加固要求。原 printf 示例夹具已拒绝；这是新包装形态，不是原底稿仍红。

证据：[curl-new-probes.json](/tmp/mygamestudio-review-4-6hm1q78i/curl-new-probes.json)、[复跑脚本](/tmp/mygamestudio-review-4-6hm1q78i/curl-new-probes.py)、[脚本参数事件](/tmp/mygamestudio-review-4-6hm1q78i/curl-new-fixtures/shell-script-before-c.jsonl)。裸 curl 与 zsh 包装的真实失败对照均 OK。所有连接仅为本轮预留但不监听端口的 loopback 尝试，未访问真实远端；curl 实际输出构造的是合成事件，不冒充历史会话。

## 逐票复核表

| 票 / 核验点 | 本轮结论 | 实证及边界 |
| --- | --- | --- |
| 01 / SP-7 原探针 | 真实修复 | `partial-retry-read-first-timeout`：observed_bug=false；first/second 均 allow+partial、comment_id=5100；评论=1、POST=1、index_updated=false |
| 01 / 三语义 | 原覆盖通过 | github/runtime_gate 套件覆盖 S2 uncertain 不重发、partial 保留、彻底恢复补索引并清登记及正常收养；过度阻止首试的变异 C 变红，恢复绿 |
| 01 / 登记损坏与身份 | 部分通过、有新缺陷 | 非法 JSON 保守且披露不可读；合法缺字段对象不披露；摘要碰撞误认另一请求（SP-11） |
| 01 / 无 cache-dir | 不接受当前形态为闭合 | 票面披露不等于运行结果披露；运行 note 无警告且实际重复（SP-10） |
| 01 / dist | 通过 | 包与源检查及 verify-reproducible 通过，SHA-256 与票 01 一致 |
| 02 / SP-8 原探针 | 真实修复 | 带第五参动作后，wrong-target-prefix、append-denial-as-update-proof 均 MISSING；read→update 仍 MISSING |
| 02 / SP-9 原探针 | 真实修复 | 实际执行 printf 示例+exit 7，curl_was_executed=false，判据 MISSING |
| 02 / 留存证据、9 处接线 | 通过 | r1×4、g1×3、p1、p2、r1b，共 10/10 OK；9 处 MCP 调用按实际动作口径验证；p1/p2 实为 task_grant，不宣称独立测得 role_scope |
| 02 / 新路径与包装反例 | 未闭合 | 错误绝对路径、comments 身份和 shell 脚本参数均可假绿（SP-12/13） |
| 两票 / 回归及两轴 | 必需检查通过，Spec 不通过 | 五套件全绿，驱动 33 PASS/0 FAIL；Standards 无发现，Spec 共 4 项 P2 |

## 每票变异：绿→还原修复红→恢复绿

| /tmp 变异 | 变异前 | 变异结果 | 恢复后 |
| --- | --- | --- | --- |
| 票 01 A：mgs_github.py 还原为 521c465 版本，移除 SP-7 登记修复 | github、gate 均 exit 0 | github exit 1 / 8 条失败；gate exit 1 / 6 条失败 | 两套 exit 0 |
| 票 01 C：所有读前失败都返回 pending，不区分是否有登记 | github exit 0 | exit 1 / 7 条失败，首试 POST=0、uncertain 被错误替换 | exit 0 |
| 票 02 B：只还原旧 mcp_deny_anchor | 锚定回归 exit 0 | exit 1 / 2 条失败，对应 SP-8 两原反例 | exit 0 |
| 票 02 D：只还原旧 curl_direct_denied | 锚定回归 exit 0 | exit 1 / 1 条失败，对应 SP-9 printf 原反例 | exit 0 |

变异均在专属 `mutation/` 副本执行；C 使用空字典哨兵使输出能完成，失败来自行为断言而非空值异常。它与历史变异的表达方式不完全相同，故本轮如实报告 7 条失败，不抄票面“8 条”。恢复后两个文件逐字节等于目标版本；copy/spec/standards/mutation 四副本的这两个产品文件也已统一核对。以上证明当前回归对撤去修复敏感，**不证明历史红测试最初发生的时间顺序**。

证据：[mutation-results-4.json](/tmp/mygamestudio-review-4-6hm1q78i/mutation-results-4.json)、[变异脚本](/tmp/mygamestudio-review-4-6hm1q78i/mutations-4.py)、[字节恢复记录](/tmp/mygamestudio-review-4-6hm1q78i/mutation-restoration-4.json)。

## 证据核对与验证边界

1. **底稿适配。** `spec-custom-probes.py` 的 ROOT 改到本工作区、COPY 指向隔离 copy；其三处锚定同样原为四参数，补为 mgs_write→write、两个 G1 错动作夹具→update。`acceptance_recheck.py` 保留本轮相关的原无 MCP 夹具、留存锚定和 printf 夹具，补齐第五参；删除的执行段仅为范围外 SP-4/SP-5 和真实运行根扫描，未重复审这些既有结论。未改变原反例输入或期望值，未把缺参引起的 MISSING 算通过。完整差异在 [probe-adaptation.diff](/tmp/mygamestudio-review-4-6hm1q78i/probe-adaptation.diff)。
2. **原探针与留存流。** [spec-probes.json](/tmp/mygamestudio-review-4-6hm1q78i/spec-probes.json) 四项 observed_bug 均 false；[acceptance-probes-4.json](/tmp/mygamestudio-review-4-6hm1q78i/acceptance-probes-4.json) 显示 printf 夹具 MISSING、留存锚定 10/10 OK；[retained-stages-4.json](/tmp/mygamestudio-review-4-6hm1q78i/retained-stages-4.json) 独立解析 p1/p2 为 task_grant。历史五份事件流原样使用，未改写真实仓库证据。
3. **五套件与 33 驱动。** 在固定 05a2776 的本地隔离克隆中，先清理副本 plugin 下的 `__pycache__`，设置 `PYTHONDONTWRITEBYTECODE=1`、`python3 -B`、任务专用 TMPDIR，运行 plugin_package、runtime_gate、runtime_boundaries、records_backend、github_backend，5/5 exit 0。`driver-probes.sh` 使用 `/tmp` 隔离安装及实际 MCP 子进程、localhost GitHub 替身，33 PASS/0 FAIL，exit 0；没有运行完整 acceptance run.sh 或模型轮。此安装不改变日常客户端安装状态。[suite-results.json](/tmp/mygamestudio-review-4-6hm1q78i/suite-results.json)、[driver-probes.log](/tmp/mygamestudio-review-4-6hm1q78i/logs/driver-probes.log)。
4. **包与语法。** package 套件验证源与包一致；verify-reproducible 从隔离克隆 HEAD 归档重建，tar.gz、package-manifest.txt、SHA256SUMS.txt 三项逐字节一致，两包无 PAX 扩展头。交付包 SHA-256：`f8c68739dc75cf94f311f8dd2f9a98e14090ecc0ef8669461f02723a792a2ae1`。票 18 run.sh 的 `bash -n` exit 0。[reproducible.log](/tmp/mygamestudio-review-4-6hm1q78i/logs/reproducible.log)。
5. **新反例的证据性质。** SP-10/11 经实际 MCP 处理函数、实际 GateService 与 FakeTransport；SP-12 是实际 Gate deny 封装的合成事件；SP-13 是实际本地进程退出码/输出封装的合成事件。不是生产网络证据、不是新模型会话证据，不反推历史验收造假。主审已复跑独立 Spec 脚本，原始回读日志在 [spec-independent-main-rerun.log](/tmp/mygamestudio-review-4-6hm1q78i/logs/spec-independent-main-rerun.log)。
6. **未核验及范围外。** 未测试进程崩溃、断电、生产并发/跨运行根并发、评论分页、所有文件系统 I/O 故障、全部 shell 语法或真实性能；仅验证所列顺序时序、非法 JSON/空对象、确定性摘要碰撞及有限包装/路径反例。未核对真实远端 HEAD、重放真实远端写入、运行验收模型轮、安装到日常客户端或发布。第一至三轮其他已核实事项不重复审。人工 06/10 素材后审美/试听、08 海鸥、两项设计决定及安装/发布决定继续保留待用户，没有判成通过。

## 实际执行的命令类别

- 真实仓库只读 Git：`rev-parse`、`status --porcelain`、`log`、`diff`、`show`、`archive`。没有 fetch、远端调用、提交、推送、改 refs 或切换真实工作树。
- `/tmp` 内本地 `git clone --no-hardlinks --no-checkout`、`checkout --detach 05a2776`、归档解包与副本复制。
- `rg`、`cat`、`sed`、`nl`、`ls` 和 Python 的文本读取、JSON 解析、SHA-256、路径与字节比较；按指令只读技能和相关记忆索引。
- `/tmp` 五套 Python 检查、MCP/Gate/FakeTransport 故障探针、四项源码变异及恢复；无真实 GitHub请求。
- `/tmp` 隔离 `codex plugin add`（由既有 driver 调用）、运行保障管理 CLI、stdio MCP 驱动、localhost HTTP 替身；不启动验收模型轮。
- 提取 `mcp_deny_anchor`/`curl_direct_denied` 后用 bash 执行；真实本地 sh/zsh/printf/curl 反例，curl 仅尝试 loopback；任务专属临时文件创建/清理。
- `bash -n`、`dist/verify-reproducible.sh` 及其 `/tmp` 构建、tar/PAX/SHA256/cmp 检查。删除只涉及本任务临时副本/产物及其中缓存。

## 交付判定

**SP-7/SP-8/SP-9：原反例均有实际修复；完整要求尚未闭合。存在 4 项本轮 P2，其中 pending-index 身份碰撞明确是本批引入。当前不具备 v1 收口条件。** 这不改变留存五流 10/10、五套件及 33 驱动通过的事实，也不代替人工体验和安装/发布决定。

两轴计数：Standards 0 硬违反 / 0 判断性异味；Spec 4 项，最高 P2。机器摘要：[verification-summary-4.json](/tmp/mygamestudio-review-4-6hm1q78i/verification-summary-4.json)。

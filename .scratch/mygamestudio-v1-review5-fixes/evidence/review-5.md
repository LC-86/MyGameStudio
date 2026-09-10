# MyGameStudio v1 第五轮独立复审

**交付判定：SP-10～SP-13 的原始反例均有真实修复；SP-10 按本轮约定闭合。新增反例确认 3 项 P2，SP-11/12/13 的完整要求仍未闭合，当前不具备 v1 收口条件。** Standards 轴 0 硬违反、0 判断性异味；Spec 轴 3 项 P2。五套件、33 驱动、留存五流 10/10、可复现打包及每票绿→红→绿均通过，不能据此扩写为全部边界零回退。

执行日期：2026-09-10（Asia/Shanghai）。采用 code-review 技能的独立 Standards / Spec 双轴审查，主审执行原探针、变异、回归并交叉复现新增发现。本报告的“零模型调用”沿前轮指零产品/验收模型轮；双轴使用本审查任务的独立审查代理。

- 真实仓库：`/Users/cuilei/MyOS/01_Projects/plugins/MyGameStudio`。
- 固定比较：`git diff 8dfd706..5ac2f8d`，该祖先关系下与 three-dot 相同；恰三个提交 `bc230ea`、`cf1db36`、`5ac2f8d`。
- 基线：`8dfd706276307c8e4b701de6fd6468d07228a321`；产品目标：`5ac2f8df5d2b9a36eea17507f54bf4f1dd022265`。
- 开始、结束实际 HEAD 均 `929ff4cf4895d83bc060d37474eaf0fe97a91c72`，`git status --porcelain` 均为空。该 HEAD 相对目标只多一份 review-5-handoff.md，无产品差异。
- 真实仓库零工作树改动、零提交/推送、零真实远端写入。全部探针状态、变异、回归生成物及隔离安装放在本 `/tmp` 工作区；没有执行完整 acceptance `run.sh`（包括 `--help`）。
- [开始记录](/tmp/mygamestudio-review-5-niculnow/baseline.json)、[固定 diff](/tmp/mygamestudio-review-5-niculnow/batch.diff)、[结束记录](/tmp/mygamestudio-review-5-niculnow/final-boundary-check.json)。未连接真实 GitHub 核对远端 HEAD。

## Standards

**0 项明文规范硬违反；0 项需列出的判断性异味。**

依据 `AGENTS.md`、`CONTEXT.md`、`docs/agents/{issue-tracker,triage-labels,domain}.md` 及本批实施约定；无 ADR。两票保持一票一文件、实施记录追加 Comments；未引入依赖或领域术语冲突。完整身份构造集中在 `_pending_identity`，文件名、写入和读入共用。绝对/相对资源分支表达不同语义，不机械当作重复代码。十二项 smell baseline 全部按启发式检查，未把工具已强制事项重复列项。

测试基建的一行已核验：[test_plugin_package.py:2440](/Users/cuilei/MyOS/01_Projects/plugins/MyGameStudio/tests/test_plugin_package.py:2440) 定义本地 `say() { printf ...; }`；本轮 package 套件中实际执行提取的泄漏检查并通过，不依赖 macOS 系统语音命令。

独立报告：[standards-review.md](/tmp/mygamestudio-review-5-niculnow/standards-review.md)。行为未闭合项只在 Spec 轴计数。

## Spec：发现清单

SP-14～SP-16 是本轮新确认的反例编号，不表示三项全部由本批首次引入。原始反例与这些新增边界分开判定；无新增功能越界发现。

### SP-14 · [P2] 碰撞请求都 partial 时覆盖登记，已有缓存仍会重复发布

[mgs_github.py:649](/Users/cuilei/MyOS/01_Projects/plugins/MyGameStudio/plugin/records/mgs_github.py:649) 仍对短摘要对应的同一个文件直接 `write_text`，没有保留另一个请求的登记。读入在 [700](/Users/cuilei/MyOS/01_Projects/plugins/MyGameStudio/plugin/records/mgs_github.py:700) 发现内容身份不匹配后返回无登记；这能防止冒认，却不能恢复被覆盖的身份。

沿原确定性碰撞对：A=`collision-result-79891`、B=`collision-result-80657`，同仓库、同 `01-task`，摘要均 `346df0e9`。三个**顺序**真实 MCP→GateService→FakeTransport 调用：

1. A 评论发布成功，PATCH 超时，留下 A 的登记，返回 comment_id=5100、partial，并承诺不会重复发布。
2. B 的读前 GET 超时，发布自己的评论；PATCH 也超时。唯一登记文件现在变成 B，返回 comment_id=5101、partial，也承诺不会重复发布。
3. 恢复 PATCH，让 A 重试仅读前 GET 超时。A 已无匹配登记，重新 POST comment_id=5102。

实测 **3 POST、A 正文评论 2 条**。不需要并发、人工篡改登记或真实远端。主审在另一副本重新运行同一脚本，得到相同结果。违反 [review4 票 01:22](/Users/cuilei/MyOS/01_Projects/plugins/MyGameStudio/.scratch/mygamestudio-v1-review4-fixes/issues/01-pending-index-identity-and-disclosure.md:22) 的有缓存全链路语义不回退，以及 [review3 票 01:15](/Users/cuilei/MyOS/01_Projects/plugins/MyGameStudio/.scratch/mygamestudio-v1-review3-fixes/issues/01-partial-recovery-no-duplicate.md:15) 的已发布身份保留、读前失败保持待恢复而不得当作全新发布。票 01 所述“不动他人登记”也未覆盖写入阶段。

来源校准：同一序列仅把后端产品文件还原为 `8dfd706` 时，1 POST、A 评论 1 条，但 B 冒认 A，原实现也不正确。本批修复冒认后暴露了新的重复发布路径；底层短文件覆盖机制此前已存在。

证据：[独立结果](/tmp/mygamestudio-review-5-niculnow/spec-extra-pending.json)、[主审复跑](/tmp/mygamestudio-review-5-niculnow/main-pending-rerun/spec-extra-pending.json)、[脚本](/tmp/mygamestudio-review-5-niculnow/spec-extra-pending.py)、[修复前后对照](/tmp/mygamestudio-review-5-niculnow/new-probes-baseline-comparison.json)。应让不同完整身份的登记能够共存，并覆盖双 partial→A 重试场景；本轮未修改实现。

### SP-15 · [P2] URL 用户信息部分冒充实际连接目标

[run.sh:301](/Users/cuilei/MyOS/01_Projects/plugins/MyGameStudio/acceptance/18-complete-package-acceptance/run.sh:301) 只用字符串前缀判定 URL 指向 `127.0.0.1`。实际执行：

```sh
/usr/bin/curl -q --noproxy '*' --connect-timeout 1 http://127.0.0.1:65168@127.0.0.2:65168/_test/ping
```

curl 实际输出 `Failed to connect to 127.0.0.2`，exit 28；事件判据却 **OK**，预期 **MISSING**。`127.0.0.1:65168` 在这里是 URL userinfo，真正 host 是 `127.0.0.2`。裸 curl、zsh 包装两种形态均复现，Spec 代理另选端口独立复现；所有尝试均只到 loopback。

违反 [票 02:16](/Users/cuilei/MyOS/01_Projects/plugins/MyGameStudio/.scratch/mygamestudio-v1-review4-fixes/issues/02-anchor-context-and-execution-binding.md:16) 的实际连接目标绑定及“保守拒绝不能证明执行的形态”。应核验解析后的 host，或保守拒绝 userinfo 等未支持 URL 形态。旧 `8dfd706` 函数也对同一事件输出 OK，因此这是 SP-13 未覆盖的既有边界，不宣称本批首次引入。

证据：[主审实际命令及输出](/tmp/mygamestudio-review-5-niculnow/curl-extra-probes-5.json)、[脚本](/tmp/mygamestudio-review-5-niculnow/curl-extra-probes-5.py)、[独立交叉结果](/tmp/mygamestudio-review-5-niculnow/spec-extra-curl-crosscheck.json)。这是实际进程结果封装的合成事件，不是新模型会话证据。

### SP-16 · [P2] 去掉路径末尾空格，使另一文件满足绝对路径判据

[run.sh:135](/Users/cuilei/MyOS/01_Projects/plugins/MyGameStudio/acceptance/18-complete-package-acceptance/run.sh:135) 在规范化前对候选路径调用 `.strip()`，删除合法文件名字符。

实际 Gate 对 `"/tmp/mgs18-evil-link.md "`（末尾一个空格）的 write 返回 deny/path，返回 target 保留该空格。它与正式目标 `"/tmp/mgs18-evil-link.md"` 的 `posixpath.normpath` **不相等**，正式锚定却 **OK**。主审及 Spec 代理分别重建 Gate、提取各自副本函数复现。

违反 [票 02:15](/Users/cuilei/MyOS/01_Projects/plugins/MyGameStudio/.scratch/mygamestudio-v1-review4-fixes/issues/02-anchor-context-and-execution-binding.md:15) 的“绝对期望要求候选即该绝对路径或其规范等价”。JSON 路径参数的末尾空格属于资源身份；不能把它当排版空白删除。旧函数对该事件也为 OK，是 SP-12 完整资源核验中仍存在的边界。

证据：[实际 Gate 结果与判据](/tmp/mygamestudio-review-5-niculnow/path-extra-probes-5.json)、[脚本](/tmp/mygamestudio-review-5-niculnow/path-extra-probes-5.py)、[独立交叉及 normpath 比较](/tmp/mygamestudio-review-5-niculnow/spec-extra-path-crosscheck.json)。新增事件为实际 deny 封装的合成夹具；未对目标路径落笔。

## 逐票复核表

| 票 / 核验点 | 结论 | 本轮实际证据 |
| --- | --- | --- |
| 01 / SP-10 无缓存披露 | 按约定闭合 | 实际 MCP 返回 note 含“警告”“无跨调用身份保留”“可能重复发布”“--cache-dir”，无“不会重复发布”；posts=2/comments=2 属已约定行为，不据此重开 SP-10 |
| 01 / SP-11 原碰撞 | 原反例真实修复 | B 返回自己的 5101、自己正文已发布、posts=2；B 成功补齐不会误清 A 登记 |
| 01 / corrupt-shape、corrupt-json | 指定反例通过 | `{}` 披露登记身份不完整、提示人工核对；非法 JSON 保持不可读披露；两项 posts=1 |
| 01 / 有缓存恢复、SP-7 | 已有回归通过，完整要求未闭合 | 原 `partial-retry-read-first-timeout` observed_bug=false；套件覆盖登记/待恢复/清登记、S2 uncertain、正常收养；新增双 partial 触发 SP-14 |
| 02 / SP-12 三夹具 | 原反例真实修复 | absolute-prefix、identity-comments-suffix、identity-double-comments 全 MISSING；新尾空格反例触发 SP-16 |
| 02 / SP-13 三假、两真 | 原反例真实修复 | 三假全 MISSING/observed_bug=false；裸 curl、zsh 包装真对照全 OK；新 userinfo 触发 SP-15 |
| 02 / review3 SP-8 | 通过 | `.bak`、append-result→update、read→update 全 MISSING，三项 observed_bug=false |
| 02 / 五份留存流及接线 | 通过 | r1×4、g1×3（含 curl）、p1、p2、r1b 共 10/10 OK；9 处 MCP 接线动作保持；p1/p2 按 role_scope\|task_grant 判据通过，不扩写为单独测得 role_scope |
| 基建 / say | 通过 | cf1db36 仅增加本地打印定义及注释；package 实际提取段回归通过 |
| 两票 / 必需检查、dist | 通过 | 五套件 5/5 exit 0、driver 33 PASS/0 FAIL、bash -n、verify-reproducible 通过 |

原探针证据：[SP-10/11/12](/tmp/mygamestudio-review-5-niculnow/spec-independent-probes.json)、[SP-13](/tmp/mygamestudio-review-5-niculnow/curl-new-probes.json)、[review3 回归](/tmp/mygamestudio-review-5-niculnow/spec-probes.json)、[留存五流](/tmp/mygamestudio-review-5-niculnow/acceptance-probes-5.json)。

## 每票变异：绿→还原修复红→恢复绿

| /tmp 变异 | 修复版 | 撤回对应修复 | 字节恢复后 |
| --- | --- | --- | --- |
| 票 01：mgs_github.py 还原为 8dfd706 | github、gate exit 0 | github exit 1 / 10 条失败；gate exit 1 / 4 条失败，均为 SP-10/11 行为断言 | 两套 exit 0 |
| 票 02 A：只还原旧 mcp_deny_anchor | 锚定回归 exit 0 | exit 1 / 3 条失败，恰 SP-12 三夹具 | exit 0 |
| 票 02 B：只还原旧 curl_direct_denied | 锚定回归 exit 0 | exit 1 / 3 条失败，恰 SP-13 三夹具 | exit 0 |

独占 `mutation/` 副本，当前测试保持不变，只撤回产品修复；失败不是缺参或语法错误。恢复后两个文件逐字节等于目标版本。后续修复前新反例对照同样在该副本执行并已恢复。上述证明当前回归会捕获撤去修复，不能证明实施阶段历史红测试的发生时间。

证据：[变异结果](/tmp/mygamestudio-review-5-niculnow/mutation-results-5.json)、[可复跑变异脚本](/tmp/mygamestudio-review-5-niculnow/mutations-5.py)。

## 证据核对与验证边界

1. **探针适配可追溯。** review4 独立探针 ROOT 改到本工作区、COPY 指向隔离 copy；curl 脚本通过自身位置找到副本，无产品修改。review3 底稿三处锚定原缺第五个动作参数，本轮补 mgs_write→write、两个错误动作夹具→update，未以缺参引起 MISSING 冒充通过。acceptance_recheck 只更换本轮输出名。[完整适配 diff](/tmp/mygamestudio-review-5-niculnow/probe-adaptation.diff)。
2. **五套件与 33 驱动。** 副本按目标提交 checkout，批量运行前清理副本 plugin 下 `__pycache__`，设置 `PYTHONDONTWRITEBYTECODE=1`、`python3 -B` 和任务 TMPDIR。plugin_package、runtime_gate、runtime_boundaries、records_backend、github_backend 全 exit 0。driver 使用任务 `/tmp` 隔离安装、实际 stdio MCP 子进程与 localhost GitHub 替身，33 PASS/0 FAIL，没有启动产品模型轮，也未更改日常客户端安装。[suite-results.json](/tmp/mygamestudio-review-5-niculnow/suite-results.json)、[driver 日志](/tmp/mygamestudio-review-5-niculnow/logs/driver-probes.log)。
3. **包与源一致。** package 套件通过源/包一致检查；`dist/verify-reproducible.sh` 在隔离克隆上从 git archive HEAD 重建，tar.gz、manifest、SHA256SUMS 三项逐字节一致，两包无 PAX 扩展头。交付 SHA-256 为 `de85a4a235228266e689665c68f53e993fccb68dfe2b97b280b8662dc103e5b9`，与交接一致。[可复现日志](/tmp/mygamestudio-review-5-niculnow/logs/reproducible.log)。
4. **事故恢复完整性已确认，历史细节有限。** 原仓库 acceptance/18 evidence 的 `git ls-files` 与 `find` 均为 **119**，无遗漏或额外文件；119 文件均与目标提交 blob 逐字节相同。r1/g1/p1/p2/r1b 分别 14/15/33/22/5 行，全部可解析、与 8dfd706 字节不变，本轮再锚定 10/10 OK。20 个 driver 证据变化仅动态 ID/时间/指纹/端口/草稿名；decision、target、policy_sha256 无变，两处 reason 仅动态 instance_id 改变，不能声称 reason 字节不变。当前清理规则静态匹配 **109** 文件而非 107；清理后重建文件可能解释观察差异，但本轮没有历史执行过程证据，**精确删除 107、准确中断时点、当时未进入模型/安装/替身均未独立证明**。可确认恢复与提交内容没有证据丢失矛盾，不把提交叙述当作事故过程的独立证据。[事故审计](/tmp/mygamestudio-review-5-niculnow/standards-evidence-audit.json)。
5. **额外通过与能力限制。** 空结果正文、Unicode/组合字符、100000 字符正文都完成 partial→读前失败保留身份→补齐清登记，各 posts=1。精确路径、尾斜杠、./、重复斜杠按本票 normpath 口径 OK；重复路径、大小写变体 MISSING。env 包装、xargs/管道和 IPv6 其他目标被保守拒绝；`--url` 实际真连接也 MISSING，此为固定探针解析的支持限制，不作为额外阻塞。保留 op/args/repo 而删除 comment_id/ref 的登记仍返回缺失发布身份且未披露 corrupt；本票明示完整内容身份为 op/args/repo，没有同样明确回执字段校验，记录观察而不另立发现。
6. **未核验。** 未穷举 repo 变体、超长任务 identity、并发写/清登记、跨进程崩溃/断电、全部 I/O 故障、评论分页或所有 shell/URL 语法；不能作这些场景零回退结论。未核对真实远端 HEAD、重放真实远端写入、启动验收模型轮、安装到日常客户端或发布。第一至四轮其他既有结论不重审；人工 06/10 素材后审美/试听、08 海鸥、两项设计决定及安装/发布决定继续留给用户。

## 实际执行的命令类别

- 原仓库只读 Git：`rev-parse`、`status --porcelain`、`branch --show-current`、`log`、`diff`、`show`、`ls-files`；没有 fetch、commit、push、tag 或原仓库 checkout。
- `/tmp`：本地 `git clone --no-hardlinks --no-checkout`、`checkout --detach 5ac2f8d`、归档/解包、产品文件变异与字节恢复；最终恢复检查。
- 文件只读与取证：`rg`、`cat`、`sed`、`nl`、`find`、Python 文本/JSON/散列/字节及 Git blob 比较；只读相关技能、记忆索引。
- `/tmp` 五套 Python 检查、MCP/Gate/FakeTransport 探针、回归敏感性变异，脚本/夹具/日志和本报告写入；任务副本缓存与临时产物清理。
- 既有 driver 的任务隔离 `codex plugin add`、CLI 版本检测、运行保障管理 CLI、stdio MCP、localhost HTTP 替身；不产生模型轮。
- 从 run.sh **只提取函数**执行 bash；本地 sh/zsh/curl/env/xargs/printf 进程，仅 loopback 网络尝试；`bash -n`。
- `dist/verify-reproducible.sh` 及其 `/tmp` 构建、tar/PAX/SHA256/cmp 检查。

## 交付判定

**四项原始反例都真实修复，SP-10 按披露口径闭合；存在 3 项本轮确认的 P2，不能认定完整要求或全部恢复边界零回退，当前不具备 v1 收口条件。** SP-14 是修正碰撞冒认后出现的新重复发布路径；SP-15/16 为旧判据仍漏掉的边界。修复这些行为后仍需针对性复核，人工体验与发布决定保持原边界。

两轴计数：Standards 0 硬违反 / 0 判断性异味；Spec 3 项、最高 P2。机器摘要：[verification-summary-5.json](/tmp/mygamestudio-review-5-niculnow/verification-summary-5.json)。

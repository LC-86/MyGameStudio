**交付判定：SP-24～26 的指定原反例均真实修复；新增确认 SP-27～29 共 3 项 P2 验收假阳性，均为修复前已经存在的遗漏。本轮未发现 e3741c6 引入的新回归，但当前仍不具备 v1 技术收口条件。**

# MyGameStudio v1 第九轮独立复审

日期：2026-09-10。使用 code-review 的 Standards / Spec 两轴独立审查，主审负责新运行与汇总。审查代理属于审查任务；产品/验收模型轮为 0。全部本轮探针、变异、安装及交付物位于 `/tmp/mgs-review9-3hpb5uhl`。

## 固定范围

- 真实仓库 `/Users/cuilei/MyOS/01_Projects/plugins/MyGameStudio`，分支 `main`。开始、结束 HEAD 均为 `0029067ebfc55b3977dd813c066e78f400ba1ec8`，`git status --porcelain` 均为空；1786 个受版本控制文件逐字节无变化。
- 产品目标 `e3741c6`。HEAD 只多第九轮交接文档，没有产品差异。
- 固定 diff：`git diff 3f3031a..e3741c6`，恰 3 个提交：`1512d11` 交接、`91991d9` 归档/开票、`e3741c6` 修复。产品变更限于 `curl_direct_denied` 及相应测试，另有 21 份 driver 证据刷新和票面记录。`plugin/`、`dist/` 零差异。
- 实施者所用工具不影响本次判断；结论来自代码、实际行为、变异和证据核对。

[开始记录](/tmp/mgs-review9-3hpb5uhl/start.json)、[固定 diff](/tmp/mgs-review9-3hpb5uhl/batch.diff)、[提交表](/tmp/mgs-review9-3hpb5uhl/commits.txt)、[结束边界](/tmp/mgs-review9-3hpb5uhl/final-boundary-check.json)。

## Standards

**0 项明文标准硬违规；0 项报告级判断性异味。** 独立轴依据 AGENTS.md、CONTEXT.md、docs/agents 三份约定和十二项 Fowler 启发式。单票结构、Comments 追加、历史勾选保留符合约定；没有新增依赖、领域术语或 ADR 冲突。测试及历史证据的有意重复不机械视为产品逻辑重复。

21 份 driver 刷新经逐字段动态验证和身份映射后，语义差异为 0。五份留存流相对 `3f3031a` 和 `a3c43ce` 均逐字节不变。包内 79 文件的集合与字节均匹配 plugin 源，PAX 为 0，交付 SHA-256 仍为 `3c44e2c0aaa0f02571fc394b30dd4ed34a9d0833c554531856b6a04f47c37ea7`。

132 份第八轮归档自 `91991d9` 至产品目标未改；29 JSON、62 JSONL 可解析；六项哈希清单、17 份夹具与分列输出、triage 复跑矩阵一致。这证明归档内部一致性，不能独立证明历史执行时序或实施者 `/tmp/mgs-r8-cursor` 原始产物来源。

[独立 Standards 报告](/tmp/mgs-review9-3hpb5uhl/agents/standards/standards-review.md)、[机器证据](/tmp/mgs-review9-3hpb5uhl/agents/standards/evidence.json)。

## Spec：原票逐项复核

**SP-24～26 修复成立，本票未见缺失或范围扩大。** 原第八轮脚本新运行 17/17 符合，`observed_bug` 全为 false；独立 Spec 轴另重放 17 份归档夹具，`3f3031a` 恰 6 项假绿，当前全部符合。

| 项目 | 本轮观察 | 判定 |
|---|---|---|
| SP-24：`-Lm2`、`-Lm 2`、`-LsSm2`、粘连 `-K路径` | 4 例均 MISSING；前三例真实服务器记录 302 命中 | 指定反例真实修复 |
| 正常聚合 `-sSm2` / `-sSm 2` | 均 OK；粘连/分离值消费保持 | 未回退 SP-22 |
| SP-25：响应正文失败措辞后超时 | 服务器 200，正文到达，stderr 为响应阶段超时，当前 MISSING | 指定反例真实修复 |
| SP-26：ambient proxy `.10` | stderr 明确点名 `.10`，当前 MISSING | 主机相等比较成立 |
| direct / terminator-url | 两例 OK | 保持 |
| standalone-config/redirect、invalid-short-value、proxy-user-short | 四例 MISSING | 保持 |
| plain-body-then-timeout、response-body-completed、ambient-proxy-dot2 | 三例 MISSING | 保持 |
| 正文完整模拟诊断行 | 实际 200+正文诊断+响应超时，当前仍 OK | 复现已接受残余限制，不另编号 |

实现位置：[run.sh:328](/Users/cuilei/MyOS/01_Projects/plugins/MyGameStudio/acceptance/18-complete-package-acceptance/run.sh:328) 校验首个带值字符之前的全部前缀；[run.sh:236](/Users/cuilei/MyOS/01_Projects/plugins/MyGameStudio/acceptance/18-complete-package-acceptance/run.sh:236) 限定诊断行形态；[run.sh:383](/Users/cuilei/MyOS/01_Projects/plugins/MyGameStudio/acceptance/18-complete-package-acceptance/run.sh:383) 比较捕获主机身份。

`mcp_deny_anchor`、剥 shell、heredoc 提取约定均无本批改动。当前测试中的 17 份新增字面夹具及断言有接线，并经当前/旧函数行为验证；未独立取得实施者原始临时 curl 文件，因此不把本轮随机端口、耗时不同的新输出冒称为其历史 AST 逐字节来源证明。

[17 例新运行](/tmp/mgs-review9-3hpb5uhl/new-probes-8.json)、[独立归档重放](/tmp/mgs-review9-3hpb5uhl/agents/spec/original-fixture-replay.json)。

## Spec：新增发现

**3 项 P2，均是验收判据缺陷，不是产品运行时权限绕过的证明。** 新事件由真实 loopback curl 的命令、退出码及 stdout+stderr 封装，服务器命中另行记录；没有新增产品模型会话。以下反例在 `3f3031a` 也成立，因此不能归因于本批首次引入。

### SP-27 · [P2] 无值短旗标被当作带值旗标，吞掉首个 URL

位置：[run.sh:254](/Users/cuilei/MyOS/01_Projects/plugins/MyGameStudio/acceptance/18-complete-package-acceptance/run.sh:254)、[run.sh:330](/Users/cuilei/MyOS/01_Projects/plugins/MyGameStudio/acceptance/18-complete-package-acceptance/run.sh:330)。`CURL_VALUE_SHORT` 把 `g/J/Z` 列为带值；本机 curl 帮助及实际执行证明三者均为无值旗标。`-g <成功URL> <失败URL>` 和 `-J …` 会把首个 URL 当作参数值跳过，单 URL 守卫只看到第二个 URL。

实际首个请求返回 **200 / TARGET_SUCCESS**，随后连接关闭端口失败、exit 28；当前 **OK**，应为 **MISSING**。`-sS -Z <成功URL> <失败URL>` 同样成立。反过来，合法 `-g <失败URL>`、`-sS -Z <失败URL>` 把唯一 URL 吞掉，当前 MISSING、正确分类守卫 OK，是同根假阴性。

违反 [review7 票 01:15](/Users/cuilei/MyOS/01_Projects/plugins/MyGameStudio/.scratch/mygamestudio-v1-review7-fixes/issues/01-curl-anchor-connection-proof-completion.md:15)“URL 计数须反映真实参数语义”及 [review6 票 02:14](/Users/cuilei/MyOS/01_Projects/plugins/MyGameStudio/.scratch/mygamestudio-v1-review6-fixes/issues/02-curl-anchor-connection-params-and-single-url.md:14) 的单 URL/失败归属要求。应按实际参数是否带值核对接纳表，并覆盖单 URL 真失败和多个 URL 的行为。

**校准：** 裸 `-Z` 的首轮实际输出在 curl 诊断前带进度文字，当前行首正则拒绝，结果 MISSING；该形态不算假绿。补充 `-sS -Z` 后真实 stderr 诊断位于行首，才确认假绿。首轮守卫只改了 g/J，未把 Z 的效果冒称已验证；补充守卫明确正确分类 g/J/Z。

### SP-28 · [P2] 重试末次连接失败被当作从未连接

位置：[run.sh:260](/Users/cuilei/MyOS/01_Projects/plugins/MyGameStudio/acceptance/18-complete-package-acceptance/run.sh:260)、[run.sh:384](/Users/cuilei/MyOS/01_Projects/plugins/MyGameStudio/acceptance/18-complete-package-acceptance/run.sh:384)。`--retry 1` 被接纳，但判据只要求失败进程的任意一行诊断绑定目标，未区分重试中的多次尝试。

真实单 URL 首轮返回 **503 和完整 RETRY_RESPONSE 正文**，随后本任务服务器关闭。curl 的 stderr 明确提示 HTTP error 后重试；第二次连接产生真实 `curl: (7) Failed to connect to 127.0.0.1 …`，exit 7。当前 **OK**，应为 **MISSING**：初次连接显然已被允许。503 是应用响应错误，不能当成网络连接拒绝。

违反 [review7 票 01:16](/Users/cuilei/MyOS/01_Projects/plugins/MyGameStudio/.scratch/mygamestudio-v1-review7-fixes/issues/01-curl-anchor-connection-proof-completion.md:16)“失败证据须能证明对替身的连接未被允许”。此例的诊断来自真实 stderr，与正文模拟的已留档限制无关。需明确重试支持口径：保守拒绝，或按每次尝试证明；仅末次失败不足。

### SP-29 · [P2] 单个 URL 参数经 curl 展开成多个请求，绕过请求数量限制

位置：[run.sh:309](/Users/cuilei/MyOS/01_Projects/plugins/MyGameStudio/acceptance/18-complete-package-acceptance/run.sh:309)、[run.sh:359](/Users/cuilei/MyOS/01_Projects/plugins/MyGameStudio/acceptance/18-complete-package-acceptance/run.sh:359)、[run.sh:367](/Users/cuilei/MyOS/01_Projects/plugins/MyGameStudio/acceptance/18-complete-package-acceptance/run.sh:367)。例如引号内 `http://127.0.0.1:{成功端口,关闭端口}/ok` 是一个位置参数，hostname 仍为 `.1`，却由 curl 默认 URL glob 展成两个请求。

真实首请求返回 **200 / TARGET_SUCCESS**，第二连接失败、exit 28；当前 **OK**，应为 **MISSING**。`--` 终止符后的同形 URL 也成立；`--globoff` 对照没有实际成功命中，当前 MISSING。这里没有请求扩大多 URL 支持，而是要求现有“保守拒绝多个请求”策略覆盖 curl 自身展开。

违反 [review6 票 02:14](/Users/cuilei/MyOS/01_Projects/plugins/MyGameStudio/.scratch/mygamestudio-v1-review6-fixes/issues/02-curl-anchor-connection-params-and-single-url.md:14) 的多 URL 失败归属合同，以及 [review7 票 01:16](/Users/cuilei/MyOS/01_Projects/plugins/MyGameStudio/.scratch/mygamestudio-v1-review7-fixes/issues/01-curl-anchor-connection-proof-completion.md:16) 的连接未被允许证明要求。需按 curl 展开后的语义约束，或保守拒绝不能证明单请求的形态；仅 `len(urls)==1` 不足。

[19 例新运行/分列输出/命中](/tmp/mgs-review9-3hpb5uhl/new-probes-9.json)、[3 例并行补充](/tmp/mgs-review9-3hpb5uhl/parallel-curl-supplement.json)、[独立 Spec 报告](/tmp/mgs-review9-3hpb5uhl/agents/spec/spec-review.md)、[独立证据核对](/tmp/mgs-review9-3hpb5uhl/agents/spec/parent-evidence-audit.json)。

## 变异与因果验证

使用当前测试、独占副本，只改 run.sh 文本，从未启动 run.sh。当前 0 红；换入 `3f3031a` 提取函数后**恰红 6 项**，全部落 SP-24×4 / SP-25×1 / SP-26×1；恢复 0 红。

| 撤回方向 | 变异红数 | 归属 | 恢复红数 |
|---|---:|---|---:|
| 前缀按序校验 | 4 | SP-24 四例 | 0 |
| 诊断形态约束，保留主机相等 | 1 | SP-25 | 0 |
| 主机相等改子串，保留诊断形态 | 1 | SP-26 | 0 |
| 旧短语+主机子串组合 | 2 | SP-25、SP-26 | 0 |

**诊断变异的重要校准：** 首轮严格只去掉 `curl: (7|28)` 前缀、保留主机后的空格/冒号要求，实际为 **0 红**；SP-25 原正文在主机后直接结束，该尾部要求也能挡住它。第二轮同时放宽为主机后允许行尾，继续保留 `host == STANDBY_HOST`，才得到 **1 红**。这验证的是“诊断形态层整体”与“主机身份层”的拆分，不能写成“仅去错误前缀必红 1”。初始矩阵和两个精确 diff 均保留，属实验粒度校准，未另编号产品缺陷。

恢复后 run.sh 与真实仓库逐字节一致，SHA-256 `55e7243b` 前缀（完整值在机器结果）。三项新增发现分别做当前假绿→对应守卫拒绝→恢复假绿：SP-27 正确参数分类；SP-28 拒绝 retry；SP-29 拒绝 glob。后两者为保守因果控制，**不是完整修复提案**；retry 守卫也拒绝真失败 retry 对照，影响如实保留。SP-27 的单 URL 假阴性另为 MISSING→OK→MISSING。

[最终矩阵及失败断言](/tmp/mgs-review9-3hpb5uhl/mutation-results-9.json)、[初始诊断校准](/tmp/mgs-review9-3hpb5uhl/mutation-initial-results-9.json)、[精确诊断变异](/tmp/mgs-review9-3hpb5uhl/diagnostic-mutation.diff)。

## 全历史不回退与回归

| 指定项目 | 实际结果 |
|---|---|
| SP-7 原 spec-custom-probes | partial retry posts=1，observed_bug=false |
| SP-10 原 spec-independent-probes | 无缓存 posts=2，首次明确警告；沿已接受退化 |
| SP-11 同原脚本 | corrupt-json / corrupt-shape-object 均 posts=1 |
| SP-12 同原脚本 | 碰撞 posts=2，B 有自己的正文；三资源身份反例 MISSING |
| SP-13 原 curl-new-probes | 3 假例 MISSING，裸 curl / zsh 两真对照 OK |
| SP-14 原 spec-extra-pending | 两完整身份共存，posts=2/A=1；缺回执不重发且披露；正文边界通过 |
| SP-15 原 curl-extra-probes-5 | userinfo 两反例 MISSING；保留 --url 原 observed_bug=true，归类已接受限制 |
| SP-16 原 path-extra-probes-5 | 8 例符合；补充 Unicode/空白 8 例符合 |
| SP-17 mixed-layout 拆名双来源 | Spec 普通及 --guard-each-path 均 posts=2/B=1；Standards 回执身份保持、B=1 |
| SP-18/19 原 curl-boundaries | 11/11 observed_bug=false |
| SP-20～23 原 curl-adversarial-7 | 17/17 observed_bug=false |
| SP-24～26 原 new-probes-8 | 17/17 observed_bug=false |

原探针仅作已约定路径/API/断言适配；new-probes-8 另去 no-op 守卫断言，不把旧文本守卫当独立因果验证。三个旧 reservation socket 原绑定 `0.0.0.0`（不监听）收窄为 `127.0.0.1`，例数与判据未变。`new-probes-8.py` 原 before_batch 列仍为 **3e6ae30**，第七轮原脚本该列仍为 **a3c43ce**；本批红绿基线独立使用 **3f3031a**，不混用。

- 留存 r1/g1/p1/p2/r1b 五流 **10/10 OK**，文件哈希不变。
- 五套件 plugin_package / runtime_gate / runtime_boundaries / records_backend / github_backend 均 exit 0，日志明确全部通过。
- 本任务隔离安装的 driver **33 PASS / 0 FAIL**；移除链接日常 auth.json 的一行后运行，随后还原副本 driver 脚本字节。
- 18 份 acceptance run.sh 仅 `bash -n`，全部通过。产品范围 diff-check 通过；全批 diff-check 的非零仅为归档嵌套补丁空白，不作产品问题。
- dist 交付包未重建或修改。package 套件自身的两次临时副本重建照常执行，产物自动清理，不替换交付包。
- 汇总断言审计 **43/43**。这表示本轮结果与报告核验口径一致，包含确认新缺陷的断言，**不表示产品所有行为通过**。

[历史执行](/tmp/mgs-review9-3hpb5uhl/history-execution.json)、[补充历史](/tmp/mgs-review9-3hpb5uhl/additional-history-execution.json)、[适配 diff](/tmp/mgs-review9-3hpb5uhl/probe-adaptation.diff)、[顶层适配](/tmp/mgs-review9-3hpb5uhl/top-level-adaptation.diff)、[套件](/tmp/mgs-review9-3hpb5uhl/suite-results.json)、[driver 日志](/tmp/mgs-review9-3hpb5uhl/logs/driver-probes.log)、[留存](/tmp/mgs-review9-3hpb5uhl/acceptance-probes-6.json)、[43 项审计](/tmp/mgs-review9-3hpb5uhl/verified-results-9.json)。

## 验证边界与收口条件

1. 真实仓库零工作树修改、零提交/推送/tag；只读 Git；没有真实 GitHub 网络请求或远端写入，没有日常客户端安装变更。没有以任何参数启动 acceptance/*/run.sh，所有判据执行来自文本提取或既有测试提取段。
2. 原 SP-25 残余边界经真实 200+完整模拟诊断正文+响应超时复现，当前 OK。报告保留该行原 observed_bug=true，并分类为已接受限制，不计 SP-27 起的新发现。--url、三层以上 shell、多 URL 保守拒绝策略、无缓存、并发交错、迁移截断 current、ambient 重映射后仍点名 .1 等既有留档边界未重开。
3. 新增三个发现均由主审真实本机进程验证，Spec 轴独立审读 22 行事件与结果，还自行做了归档重放和 37 个合成形态。5/35 错误码、shell 前缀诊断、IPv6、`.10/.100/.evil.com` 等合成边界按保守口径拒绝；不冒称这些形态都有真实网络复现。Standards 轴只做静态/哈希/结构核对。
4. **令牌落盘边界例外须明确：** 没有读取或输出真实账号凭据；指定既有套件/driver 会创建一次性测试令牌并短暂写入隔离状态，已清理。Git 归档复制还带入两份同一历史验收事件的测试令牌字段，已在任务副本脱敏、未输出值、真实仓库未改。因此不能声称“任何测试令牌从未落盘”。交付 JSON/JSONL/log/txt 对 64 位十六进制 token 字段扫描已为零；该扫描不等于普遍秘密检测。[清理记录](/tmp/mgs-review9-3hpb5uhl/task-cleanup.json)、[脱敏扫描](/tmp/mgs-review9-3hpb5uhl/token-output-scan.json)。
5. 本任务 loopback 服务与 reservation socket 已关闭，driver 临时安装及 arena 已清理，进程盘点无本任务残留。真实源文件最终哈希及 HEAD 保持。
6. SP-27～29 尚未修复，**技术收口不通过**。人工 06/10 审美与试听、08 海鸥、两项设计决定和安装/发布决定仍待用户；即使消除本轮技术阻塞，也仅恢复“待用户收口决定”，不是本报告自动授权发布。

## 实际执行命令类别

- 真实仓库只读：git status/rev-parse/branch/log/diff/show/rev-list/ls-files/archive；rg/cat/sed/nl、Python 文件哈希、JSON/AST/包成员检查。
- 本任务目录：本地 git clone --local --no-hardlinks --no-checkout 读取已有对象、archive 解包、临时副本、脚本适配、提取函数、变异及报告生成；无真实远端 clone/fetch。
- 五套 Python 测试、FakeTransport/MCP/Gate 历史原探针、driver-probes 隔离安装和 stdio 驱动；本机 HTTP 与真实 curl（仅 loopback）。
- bash -c 执行提取函数；bash -n 做语法检查；package 套件的两个临时副本构建。
- 任务临时安装/状态清理、历史测试令牌副本脱敏、任务进程盘点、最终 Git/字节边界核验。

两轴结论：**Standards 0 硬违规 / 0 报告级异味；Spec 3 项 P2（SP-27～29）。SP-24～26 指定反例已修复；未发现本批新回归；v1 暂不具备技术收口条件。**

[机器摘要](/tmp/mgs-review9-3hpb5uhl/verification-summary-9.json)。

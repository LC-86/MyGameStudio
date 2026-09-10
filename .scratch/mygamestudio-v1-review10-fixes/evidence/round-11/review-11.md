# MyGameStudio v1 第十一轮独立复审

**交付判定：SP-30 已真实修复；本轮未发现新产品缺陷或本批引入的回归。产品技术层面支持恢复 v1「待用户收口决定」。** Standards 0 硬违规 / 0 报告级异味；Spec 0 发现，没有新增 SP-31。

**本轮验证有保留，不能称为“完整五套件、全边界无例外通过”。** 三项故意落盘令牌测试未运行；复制历史证据时另有一份 `.token` 明文进入任务副本，发现后已脱敏且关联值复扫无余留。该执行偏差不编号产品缺陷，也不隐去。既有人工体验、设计决定、安装与发布决定仍待用户；本报告不构成发布授权。

## 固定版本与范围

- 真实仓库 `/Users/cuilei/MyOS/01_Projects/plugins/MyGameStudio`，main；开始、结束 HEAD 都为 `b5f39c9aa334437901ccd6b1699e84b403fc7b83`，porcelain 都为空；2169 份受控文件 SHA-256 前后一致。
- 产品目标 `d604b92`；实际 HEAD 比它只多 `b5f39c9` 交接文档，无产品差异。
- 批次命令 `git diff 66b8506..d604b92`，Git 实数恰三个提交：`2288aeb` handoff、`1927a46` triage/归档、`d604b92` 唯一产品修复。技能三点比较 `git diff 66b8506...HEAD` 额外只有交接文档。
- 修复只在 `curl_direct_denied` 一函数；测试新增 10 夹具/10 断言。plugin/、dist/ 零 diff；包 SHA-256 仍为 `3c44e2c0aaa0f02571fc394b30dd4ed34a9d0833c554531856b6a04f47c37ea7`。
- driver 刷新实际 **22 文件＝21 JSON＋1 environment**；triage 新增 evidence 实际 **211＝207 历史归档＋4 自验文件**。这是口径校准，不是产品发现。
- 审查工作区 `/tmp/mgs-review11-kgohlovv`。准备阶段首次副本受 macOS `tempfile` 默认位置影响，短暂建在系统临时目录；运行任何探针前已迁至此 `/tmp` 路径，原位置无残留。这是准备路径偏差，单列留档。按提交和行为判断，与实施工具无关。

## SP-30 复核与真实证据

长分离 `--upload-file` 的值含任意 `{}[]` 或缺值即拒绝；短 `T` 仍按 SP-22 的分离/粘连/聚合规则取值后检查。名单保留上传旗标；既有 URL 位置参数及 `--` 后 glob 检查、`mcp_deny_anchor`、剥壳与 heredoc 约定均未改。[产品位置](/Users/cuilei/MyOS/01_Projects/plugins/MyGameStudio/acceptance/18-complete-package-acceptance/run.sh:327)、[短旗标位置](/Users/cuilei/MyOS/01_Projects/plugins/MyGameStudio/acceptance/18-complete-package-acceptance/run.sh:355)。

主审独立重跑原 `new-curl-probes.py` **36 例**。六种核心上传 glob 均实际发生首次 PUT 200、收到 18 字节并返回 `UPLOAD_SUCCESS`，监听在响应前关闭；第二连接真实 stderr 为 `curl: (7) Failed to connect...`，exit 7。当前全部 MISSING，`e3741c6` / `3f3031a` 提取函数全部仍 OK。两个普通单文件上传真失败对照保持 OK；`-g` 且字面文件不存在、长等号形态保持 MISSING。

[真实命令/输出/服务命中与历史函数结果](sp30/new-curl-probes.json)、[本轮探针](sp30/new-curl-probes.py)、[路径与 no-op 守卫适配](probe-adaptation-11.diff)。原探针 R 使用真实、固定的 Git 仓库，只读 `git show`；其旧 no-op guard 列仅留档，因果判定采用下面从当前文本独立重建的变异。

| 原探针 | 期望 | 当前 | 原脚本 observed_bug |
|---|---|---|---|
| direct | OK | OK | false |
| aggregate-Zg-single | OK | OK | false |
| aggregate-gJ-single | OK | OK | false |
| aggregate-Zg-two | MISSING | MISSING | false |
| aggregate-gJ-two | MISSING | MISSING | false |
| aggregate-JO-single | MISSING | MISSING | false |
| J-O-single | MISSING | MISSING | false |
| glob-query-plain | MISSING | MISSING | false |
| glob-query-off-short | MISSING | MISSING | false |
| glob-query-off-long | MISSING | MISSING | false |
| glob-encoded-braces | OK | OK | false |
| glob-encoded-brackets | OK | OK | false |
| glob-escaped-braces | MISSING | MISSING | false |
| glob-after-terminator-encoded | OK | OK | false |
| glob-after-terminator-query | MISSING | MISSING | false |
| glob-retry-redirect | MISSING | MISSING | false |
| retry-all-errors-no-retry | MISSING | MISSING | false |
| retry-connrefused-no-retry | MISSING | MISSING | false |
| retry-delay-no-retry | MISSING | MISSING | false |
| retry-max-time-no-retry | MISSING | MISSING | false |
| auth-challenge-no-credentials | MISSING | MISSING | false |
| http2-plain | MISSING | MISSING | false |
| encoded-literal-success | MISSING | MISSING | false |
| upload-glob-short | MISSING | MISSING | false |
| upload-glob-long | MISSING | MISSING | false |
| upload-glob-short-attached | MISSING | MISSING | false |
| upload-glob-short-aggregate | MISSING | MISSING | false |
| upload-glob-range | MISSING | MISSING | false |
| upload-glob-after-terminator | MISSING | MISSING | false |
| upload-glob-with-g | MISSING | MISSING | false |
| upload-glob-long-equals | MISSING | MISSING | false |
| upload-single-closed | OK | OK | false |
| upload-long-single-closed | OK | OK | false |
| ftp-passive-default | MISSING | MISSING | false |
| ftp-passive-parallel | MISSING | MISSING | false |
| ftp-control-port-closed | MISSING | MISSING | false |

以上字段没有人工改成 false；摘要另外保留六例在第十轮归档中的 `archived_review10_observed_bug=true`，可直接比较修复前后。

## 绿→红→绿因果变异

在独占 `/tmp` 副本调用当前 `test_accept18_probe_checks_anchored_to_events`，只执行其中提取函数，没有启动 run.sh。初始全绿。

| 替换方向 | 红数 | 红项 | 恢复后红数 |
|---|---:|---|---:|
| 换入 `66b8506` 的原函数 | 6 | 六种上传 glob | 0 |
| 仅撤回当前两处上传值检查 | 6 | 同六种上传 glob；普通上传对照不红 | 0 |
| 宽方案：移除 T/--upload-file | 2 | 短、长普通上传真失败对照 | 0 |

七次检查结果为 **0/6/0/6/0/2/0**；每个失败断言均读取核对。最终副本 run.sh 与真实仓库逐字节一致，SHA `72a3d59a22e07cb467510014cd9ae31b99bb77c3524521b1cc1ecce01ac5f2d2`。[变异矩阵与全部失败项](mutation-results-11.json)、[撤回 diff](mutations/withdraw.diff)、[宽方案 diff](mutations/broad.diff)。

独立 Spec 轴另对新 44 例撤回两段，Python AST 与批次前基线相同；仅步长范围及 `-g` 字面 glob 文件真失败两行改变，恢复 44 行与当前一致。此组宽方案另误伤 4 个普通/聚合/stdin 对照，不能混同原 36 例的“宽方案红 2”。[独立因果结果](spec/spec-causal.json)。

## 全历史不回退

指定历史脚本共 **15 次执行**，exit 均为 0；另按结果字段核对，不能只看退出码。下表“通过”包括明确保留的已接受限制。

| 历史项 / 原探针 | 本轮结果 |
|---|---|
| SP-7 / spec-custom-probes | partial retry post_count=1，observed_bug=false |
| SP-10 / spec-independent-probes | 无缓存 posts=2，首次有警告，保持已接受退化 |
| SP-11 / 同上 | corrupt-json、corrupt-shape-object 各 posts=1 |
| SP-12 / 同上 | 碰撞 posts=2，B 自有正文存在；三错误资源锚定 MISSING |
| SP-13 / curl-new-probes | 5 例符合；裸 curl / zsh 对照 OK |
| SP-14 / spec-extra-pending | 双身份共存；缺回执不重发并披露；正文边界通过 |
| SP-15 / curl-extra-probes-5 | 7 行中 6 行符合原期望；true-url-flag 原 observed_bug=true 为已接受限制 |
| SP-16 / path-extra + path-and-retained | 原 8 例及 Unicode/空白 8 例均符合 |
| SP-17 / mixed-layout 双来源 | Spec 普通及 --guard-each-path 都 posts=2/B=1；Standards B 回执身份保持、B=1 |
| SP-18/19 / curl-boundaries | 11/11 符合 |
| SP-20～23 / curl-adversarial-7 | 17/17 符合 |
| SP-24～26 / new-probes-8 | 17/17 符合 |
| SP-27～29 / new-probes-9 | 19 行符合当前合同；两条历史 observed_bug=true 保留 |
| parallel-curl-supplement | 3/3 符合 |
| SP-30 / new-curl-probes | 36/36 符合，六核心反例已修复 |
| r1/g1/p1/p2/r1b 留存流 | 10/10 OK；真实五流字节不变 |

`full-diagnostic-body` 保持 OK，是 SP-25 已接受正文来源限制；`retry-closed-control` 保持 MISSING，是已披露的保守翻转。两行原始期望与 observed_bug=true 均未改写。`terminator-attached-option` **只回放第十轮事件**，没有再次实跑 `-- -sSm2` 命令；其余 new-probes-9 18 行为本轮真实 loopback 运行。

[历史执行清单](history-execution-11.json)、[原字段与分类完整摘要](verification-summary-11.json)、[留存五流](acceptance-probes-6.json)、[证据核对 41/41](verified-results-11.json)。41/41 是证据与合同口径的一致性检查，包含已接受例外，不等于所有可能产品行为通过。

## 新探针、保守代价与校准

独立 Spec 轴新增 **44 行真实 loopback** 观察，无新增可报告缺陷。[脚本](spec/spec-probes.py)、[原始命令/输出/服务命中](spec/spec-probes.json)、[校准与判断](spec/spec-summary.json)。

- 本轮输出与 data 参数的 glob 值未倍增请求；长 form 的多文件上传是一次 POST。短 `-F` 仍在名单外，不能把其 MISSING 写成新增支持。
- `-T 'item[1-3:2].txt'` 真实首次 PUT 200/24 字节后二次连接失败，基线 OK、当前 MISSING；stdin、缺值、嵌套/转义、单元素/不配对符号、重复旗标及 URL glob/retry/重定向组合未产生新假绿。
- `upload-dot-closed` 原 expected=OK、observed_bug=true **保留**。实际诊断紧接进度字符、非行首，基线与当前均 MISSING；按已接受的行首诊断保守口径校准为 MISSING，不计新增发现。本机 `-T .` 是从 stdin 非阻塞上传，不能把它描述为目录上传验证。
- `-g` 且存在字面 `{a,b}.txt` 时，单次真实连接失败由基线 OK 变为当前 MISSING。这是规格明确要求“值含任意 glob 字符即拒绝”的代价；与原探针字面文件不存在的 exit 26 对照区分。
- 44 行原始 observed_bug 有 **1 行 true**，报告级缺陷为 **0**；不写成“44 行原始断言全绿”。HTTP2 内部重发及 curl 全语义未穷尽。

## 回归与证据核对

- runtime_gate、runtime_boundaries、records_backend、github_backend **四套完整运行通过**。
- plugin_package **允许部分通过**；三个主动令牌落盘测试明确未运行：`test_accept16_sanitize_covers_unenumerated_tokens`、`test_accept16_secret_scan_gate`、`test_accept18_leak_checks_mechanized`。包装入口跳过这些函数，模块自身“全部通过”日志只适用于此次实际执行的子集。交接/spec 记载主会话曾完整补验通过，本轮没有独立复跑那三项，不将历史记载冒充新证据。[套件摘要](suite-results-11.json)。
- 实际隔离安装副本 driver **33 PASS / 0 FAIL**；没有真实 auth.json 链接，颁发的运行令牌只在内存和内部管道传递。环境/安装仅位于本任务目录，完成后清理；副本 driver 已恢复。[驱动结果](driver-result-11.json)、[日志](logs/driver-probes-11.log)、[隔离适配](driver-isolation-11.diff)。
- 18 个 run.sh 均只执行 `bash -n`，语法全过；产品范围 `git diff --check` 通过。[语法结果](syntax-checks-11.json)、[diff 检查](product-diff-check-11.json)。
- 独立 Standards 验证函数外字节不变，既有 106 check 未改；去新增节点后整个测试 AST 与基线一致。21 JSON 刷新归一后无未解释字段差异；两个 body_sha256 与正文相符。包内 79 文件与 plugin 字节一致。真实交付 dist 未重建；package 的重建测试只在临时副本运行。[Standards 证据](standards/evidence.json)。

## 执行边界与收口含义

1. **真实仓库只读满足。** 零工作树修改、零提交/推送/tag；前后 HEAD/porcelain/2169 文件哈希一致。没有以任何参数启动 `acceptance/*/run.sh`；只执行文本提取函数。零真实 GitHub 请求/远端写入，零产品/验收模型轮，没有改变日常客户端安装。[最终边界](final-boundary-check-11.json)。
2. **本轮令牌“绝不入文件”的全程边界未完全满足。** 初次复制受控材料时，预脱敏处理覆盖了事件中的 token 字段，却漏了一份独立的历史 `g_o.token`。该 65 字节文件进入 `/tmp` 任务副本；从未输出其值、也未使用其值认证。发现后已原位替换成脱敏标记，按该精确值扫描全部任务文件无余留。其是否仍有效未验证，真实源文件按只读要求未改。不能因为最终已清除就宣称全程零落盘，也不能把它写成新产品回归。[事件记录](historical-token-copy-incident-11.json)、[最终扫描](token-output-scan-11.json)。
3. **网络边界较上一轮收紧。** 已知危险终止符行只回放事件；新进程采用任务环境、数值 loopback 或显式映射到 loopback 的历史 LOCALHOST 例。所有替身仅在本地，真实服务响应也只导向 loopback。没有改变系统网络设置；这是对命令/配置/实际输出的核查，不声称做过全系统抓包或 OS 级 egress 隔离。
4. 已接受的 SP-25、--url、三层以上 shell、多 URL 保守、无缓存退化、并发交错、迁移截断及 ambient 重映射等限制不重开。有限探针不能证明所有 curl 行为，真实进程输出封装事件也不能代替模型会话验收。
5. driver 安装与 arena 已清理，原 36 例及新 44 例服务器线程均已关闭；进程核查无本任务脚本/替身残留。[清理记录](cleanup-11.json)。
6. **收口答案：SP-30 是真实修复；没有发现新产品缺陷；产品技术层面具备进入“待用户收口决定”的条件。** 本轮有上述覆盖与执行保留，不提供无保留的完整验收签字。06/10 素材审美/试听、08 海鸥、两项设计决定及安装/发布仍沿原计划由用户决定，没有在本轮完成或代为授权。

## 实际执行的命令类别

- 真实仓库只读 Git status/rev-parse/log/diff/show/ls-files；文本、AST、JSON、tar 内存读取与 SHA-256 比较。
- 本任务副本、预脱敏、路径/no-op 适配、提取函数、因果变异、结果与报告写入；未修改真实产品。
- Python 原历史脚本、四完整套件及 package 允许部分；FakeTransport/MCP/Gate 行为验证。
- 真实 `/usr/bin/curl` 到任务 loopback 替身、本地上传文件与输出文件；危险历史行仅事件回放。
- `bash -c` 执行提取函数；`bash -n` 只解析脚本；没有启动验收 run.sh。
- driver 的隔离本地插件安装、任务 fixture Git 初始化与本地替身操作；没有模型轮或真实远端。
- 仅清理本任务安装与运行目录；最终源字节、进程和产物扫描。

## 两轴独立报告

以下保持两轴分离，不以某一轴结果替代另一轴。

### Standards

**0 项硬违规，0 项需处理的判断异味；本轴未发现阻碍 SP-30 交付的标准问题。** 行为修复、全历史不回退与 v1 收口由主审综合 Spec 和本轮验证判定。

审查基线 `66b8506..d604b92`，实际 HEAD `b5f39c9aa334437901ccd6b1699e84b403fc7b83`。Git 实数为 3 个提交；HEAD 比产品目标仅多交接文档。开始和结束 HEAD 相同，porcelain 均为空。

依据：`AGENTS.md`、`AGENTS.zh-CN.md`、`CONTEXT.md`、`docs/agents/{issue-tracker,triage-labels,domain}.md` 和委托边界。票据符合独立文件、顶端 canonical Status、Comments 追加约定（issue-tracker:7–11）；领域术语未变。Fowler 条目作为判断启发式检查，没有把既有长函数或两处分支内字符检测机械计为缺陷。

| 核查对象 | 独立结果 |
|---|---|
| `run.sh:196` 函数域 | 域外逐字节一致；脚本 SHA `72a3d59a22e07cb467510014cd9ae31b99bb77c3524521b1cc1ecce01ac5f2d2`。移除新增长、短两处 guard 后，嵌入 Python 全部 AST 与基线一致。四张名单、既有 URL glob 检查、剥壳和锚定均未变；heredoc 提取约定保留。 |
| `tests/test_plugin_package.py:3359`、`:3857` | 新增 CK–CT 共 10 夹具及 10 个 check；既有 106 个 check 全保留。去掉新增 docstring、夹具及断言后，整个测试文件 AST 与基线一致。六拒绝反例、两普通上传 OK、两个既有 MISSING 对照与票面一致。 |
| driver 刷新 | 实为 **21 JSON + 1 environment = 22 文件**。逐字段比较仅时间、实例、指纹、安装/草稿路径、loopback 端口、正文日期及对应 SHA 改变；reason 差异仅实例标识。decision/rule_stage/target/policy_sha256 不变，两个 body_sha256 均与正文匹配。 |
| plugin/dist | Git 零差异；tar 中核对的 79 文件与 plugin 字节一致。包 SHA 为交接指定 `3c44e2c0aaa0f02571fc394b30dd4ed34a9d0833c554531856b6a04f47c37ea7`，与 SHA256SUMS 一致。 |
| 归档 | triage 新增 evidence 实为 **211 = 207 历史归档 + 4 triage 自验**；review-10 与摘要哈希均匹配归档审计清单。以上计数是口径校准，不编号产品发现。 |

证据：[evidence.json](standards/evidence.json)、[审计脚本](standards/audit.py)。本轴只运行只读 Git、文本/AST/JSON/哈希及 tar 内存读取；没有运行套件、driver、任何 acceptance/run.sh、真实网络或产品模型轮，也未读取/输出凭据。主审负责运行结果；本轴未宣称完整套件通过。

### Spec

**0 项可报告发现：缺失 0、部分实现 0、超范围 0、实现错误 0。SP-30 的局部实现符合票 01:14；本轴未发现新缺陷，支持结合主审回归结果恢复“待用户收口决定”。**

- `run.sh:327` 对长分离值含任意 `{ } [ ]` 或缺值返回 None；`:355–358` 按既有 SP-22 语义取得短分离、粘连与聚合值后作同样字符拒绝。URL/`--` 后检查、接纳表与 shell/诊断解析未改；符合 review10 票 01:14、:19–21。
- 独立真实 loopback **44 行**覆盖 `-o/--output`、`-d/--data*`、`-F/--form`、stdin、缺值、步长范围、嵌套/转义/单元素/不配对 glob、重复上传旗标与 URL glob/retry/重定向叠加。无新假绿。输出/data 值不倍增请求；长 form 多文件是一次 POST。`-T 'item[1-3:2].txt'` 实录首 PUT 200/24 字节、二次连接失败：基线 OK → 当前 MISSING。
- 对当前文本独立撤回两处检查，Python AST 与批次前基线相同；44 行重放仅步长范围及 `-g` 字面 glob 文件真失败改变，恢复全部与当前一致。新建宽上传守卫额外误伤四个普通/聚合/stdin 真失败对照，支持精确方案。

**校准与限制：** 原始 `spec-probes.json` 的 `expected`、`observed_bug` 完整保留。`upload-dot-closed` 初始期望 OK，实为诊断紧接进度文字、非行首；基线/当前均 MISSING，按 review9 票 01:13、:47 既有行首诊断保守口径归为观察项，非新增发现。本机 `-T .` 实际从 stdin 非阻塞上传。`-g` 且存在字面 `{a,b}.txt`、连接真失败时当前由 OK→MISSING，属票 01:14 的无条件字符拒绝代价。

仅从文本提取函数后执行；新 curl 进程使用干净环境、`-q`、数值 `127.0.0.1`，所有本任务服务线程已关闭。没有运行任何 `acceptance/*/run.sh`、模型轮或远端写入。主审负责全历史、套件、33 驱动与原六例总验；主审另有复制历史令牌文件的执行偏差，需以主报告边界为准。

两轴计数：Standards 0 硬违规 / 0 报告级异味；Spec 0 发现，均无最高严重级别项。

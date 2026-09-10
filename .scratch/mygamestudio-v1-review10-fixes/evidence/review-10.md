# MyGameStudio v1 第十轮独立复审

**交付判定：SP-27～29 的指定反例均真实修复；发现 SP-30 一项 P2 历史遗漏，未发现本批引入的新回归；目前不具备 v1 技术收口条件。**

Standards 为 0 硬违规 / 0 报告级异味；Spec 为 1 项 P2。另有两个验证限制必须保留：package 的三个主动令牌落盘测试未运行；原探针一行含非 loopback 字面地址的解析路径，无法证明整轮网络严格限于 loopback。不得把本报告缩写为“五套件完整全绿、所有边界无例外通过”。

## 固定版本与实际范围

- 真实仓库 `/Users/cuilei/MyOS/01_Projects/plugins/MyGameStudio`，main；开始和结束 HEAD 均为 `2288aeb86fac18c7d69e7a2ca291bbb6e50a32c5`，工作树干净，全部受控文件字节未变。
- 产品目标 `66b8506`；额外 `2288aeb` 只有第十轮交接文档。实际批次命令为 `git diff e3741c6..66b8506`，实数恰三提交：`0029067`、`fe8572d`、`66b8506`。
- 唯一产品提交为 `66b8506`：run.sh 的一个函数、测试及刷新证据；plugin/、dist/ 无差异。交付包 SHA-256 仍为 `3c44e2c0aaa0f02571fc394b30dd4ed34a9d0833c554531856b6a04f47c37ea7`。
- 所有副本、变异、临时安装、探针及本报告均在本任务 `/tmp/mgs-review10-j5225ubn`。评审按行为与提交内容判断，不以实施工具作依据。

## 新增发现

### SP-30 · P2 · 上传文件名 glob 绕过单请求约束

`acceptance/18-complete-package-acceptance/run.sh:258/264` 接纳 `T/--upload-file`；`:314–316` 与 `:335–339` 直接消费其值；`:309/:344` 的 glob 检查只覆盖 URL 位置参数。因而上传文件参数可展开多个请求，即使 URL 只有一个且不含 `{}` 或 `[]`。

真实反例形态：

```sh
/usr/bin/curl -q --noproxy '*' --connect-timeout .2 --max-time 2 -sS \
  -T '{a.txt,b.txt}' http://127.0.0.1:动态端口/upload/
```

本任务服务器接收首个 `PUT /upload/a.txt` 的 18 字节，关闭监听并返回 HTTP 200 与 `UPLOAD_SUCCESS`；第二次连接产生真实 stderr `curl: (7) Failed to connect to 127.0.0.1 …`，进程 exit 7。当前判据仍 **OK**，应为 **MISSING**。这是已有成功请求后错误认定“直连被拒”，不是响应正文模拟诊断行的 SP-25 例外。

违反 [review7 票 01 第 16 行](/Users/cuilei/MyOS/01_Projects/plugins/MyGameStudio/.scratch/mygamestudio-v1-review7-fixes/issues/01-curl-anchor-connection-proof-completion.md:16)“失败证据须能证明对替身的连接未被允许”，并落入 [review6 票 02 第 14 行](/Users/cuilei/MyOS/01_Projects/plugins/MyGameStudio/.scratch/mygamestudio-v1-review6-fixes/issues/02-curl-anchor-connection-params-and-single-url.md:14) 的失败归属合同。本机 curl 8.7.1 手册明确支持上传文件参数 glob。

六种真实形态全部复现：短分离 `-T value`、长分离 `--upload-file value`、短粘连 `-Tvalue`、聚合 `-sSTvalue`、`item[1-2].txt`、URL 在 `--` 后。六例在 `e3741c6` 与 `3f3031a` 也均 OK，故为**历史遗漏，不是 66b8506 引入**。

只在提取函数中对上传值增加 glob 拒绝：六例 OK→MISSING→OK；短/长普通单文件上传失败对照全程 OK。较宽的“移除所有上传旗标”守卫另有留档，它会误伤这两个对照，不能混同精确守卫。未修改产品、未提交修复。

独立 Spec 轴实跑后，主审在另一个目录只改探针 W 再次真实执行 36 例，结果逐项一致。[主审真实证据](main-confirm/new-curl-probes.json)、[一致性核验](main-confirm/confirmation.json)、[精确守卫](spec/upload_glob_guard.diff)、[因果矩阵](spec/upload-causal-matrix.json)。

## SP-27～29 逐项复核

g/J/Z 正确归入无值表；`--retry` 从接纳表移除；URL 位置参数和 `--` 后参数中的 `{}`/`[]` 均拒绝。四表共 67 项逐一对读本机帮助、无参执行和手册，元数错分类为 0；该结论不等于连接语义完备，SP-30 正是其中遗漏。

下表“原 bug”原样保留历史脚本的 `observed_bug`，不靠改写旧判据抹去例外。

| 原探针 | 本轮合同期望 | 当前 | 原 bug | 说明 |
|---|---|---|---|---|
| direct | OK | OK | false | 符合 |
| no-value-g-two-urls | MISSING | MISSING | false | 符合 |
| no-value-J-two-urls | MISSING | MISSING | false | 符合 |
| no-value-Z-two-urls | MISSING | MISSING | false | 符合 |
| no-value-g-single-url | OK | OK | false | 符合 |
| two-urls-plain | MISSING | MISSING | false | 符合 |
| mixed-prefix-sLm2 | MISSING | MISSING | false | 符合 |
| single-dash | MISSING | MISSING | false | 符合 |
| terminator-attached-option | MISSING | MISSING | false | 符合 |
| lowercase-lm2 | MISSING | MISSING | false | 符合 |
| uppercase-M2 | MISSING | MISSING | false | 符合 |
| legitimate-aggregate | OK | OK | false | 符合 |
| url-glob-two-ports | MISSING | MISSING | false | 符合 |
| url-glob-after-terminator | MISSING | MISSING | false | 符合 |
| url-glob-disabled-long | MISSING | MISSING | false | 符合 |
| full-diagnostic-body | OK | OK | true | SP-25 已接受残余；原期望 MISSING |
| retry-stop-after-503 | MISSING | MISSING | false | 符合 |
| retry-503-then-200 | MISSING | MISSING | false | 符合 |
| retry-closed-control | MISSING | MISSING | true | 已披露翻转；原脚本期望 OK |
| silent-Z-two-urls | MISSING | MISSING | false | 符合 |
| silent-Z-one-url | OK | OK | false | 符合 |
| silent-direct | OK | OK | false | 符合 |

## 变异：绿→红→绿

当前测试调用提取函数，从未启动 acceptance run.sh。用 `e3741c6` 的函数替换隔离副本后，完整当前断言集红 **9** 项：八个核心反例加 retry-closed-control 已披露翻转对照。票 01 第 17、58 行已明确“另红 1 项”；不能把 8 个核心反例写成全部断言红数。

| 替换/撤回方向 | 红数 | 归属 | 恢复后红数 |
|---|---:|---|---:|
| 完整换入批次前函数 | 9 | SP-27×5、SP-28×1、SP-29×2、retry 对照×1 | 0 |
| g/J/Z 恢复旧分类 | 5 | 三个假绿、两个反向假阴性 | 0 |
| 重新接纳 --retry | 2 | 503 后关服反例及已披露对照 | 0 |
| 撤回两处 URL glob 拒绝 | 2 | 普通 URL 位置与终止符后位置 | 0 |

三方向独立撤回没有误伤其他断言；初始、每次恢复均 0 红，最终 run.sh 与真实仓库逐字节一致。[全部失败断言及矩阵](mutation-results-10.json)、[短旗标变异](mutations/short.diff)、[retry 变异](mutations/retry.diff)、[glob 变异](mutations/glob.diff)。

SP-30 使用另一组因果验证：六反例当前假绿→精确上传 glob 守卫拒绝→恢复假绿；两普通上传失败对照始终 OK。该组证明新发现与上传参数值处理有关，不计入前述 5/2/2 产品修复矩阵。

## 全历史不回退

指定历史原脚本共 15 次执行全部 exit 0；另逐项检查结果字段，不能只用脚本退出码代替判据。

| 项目 | 本轮实际结果 |
|---|---|
| SP-7 原 spec-custom-probes | partial retry posts=1，observed_bug=false |
| SP-10 原 spec-independent-probes | 无缓存 posts=2，首次警告存在，保持已接受退化 |
| SP-11 同原脚本 | corrupt-json / corrupt-shape-object 各 posts=1 |
| SP-12 同原脚本 | 碰撞 posts=2，B 自有正文；三个错误资源锚定 MISSING |
| SP-13 原 curl-new-probes | 五例符合，裸 curl / zsh 对照 OK |
| SP-14 原 spec-extra-pending | 双身份共存，posts=2/A=1；缺回执不重发并披露；正文边界通过 |
| SP-15 原 curl-extra-probes-5 | 六例符合；--url 原 observed_bug=true 保留为已接受限制 |
| SP-16 原 path-extra-probes-5 | 八例符合；Unicode/空白补充八例符合 |
| SP-17 mixed-layout 双来源 | Spec 普通及 --guard-each-path 均 posts=2/B=1；Standards 回执身份保持、B=1 |
| SP-18/19 原 curl-boundaries | 11/11 observed_bug=false |
| SP-20～23 原 curl-adversarial-7 | 17/17 observed_bug=false |
| SP-24～26 原 new-probes-8 | 17/17 observed_bug=false |
| SP-27～29 原 new-probes-9 + parallel | 19+3 例符合本轮合同；两条已披露例外原字段保留 |
| 留存 r1/g1/p1/p2/r1b | 10/10 OK；真实仓库五流字节不变 |

原探针的路径/API/断言适配沿归档先例；本轮再替换 W 和只读 git show 位置，并去除修复后 no-op 守卫断言。旧 guard 列保留但不当作本轮独立因果证据，独立变异另见上节。before_batch 列仍分别沿原脚本固定旧版本（第七轮 a3c43ce、第八轮 3e6ae30、第九轮 3f3031a），本批绿红验证另用 e3741c6，不混淆。

[历史执行清单](history-execution-10.json)、[适配 diff](probe-adaptation.diff)、[留存五流](acceptance-probes-6.json)、[结果审计 36/36](verified-results-10.json)。36/36 是结果与报告口径的一致性，包括确认已接受例外的断言，不代表产品所有行为通过。

## 新探针与保守代价

四张白名单实际为 19 个带值短旗标、15 个无值短旗标、19 个带值长旗标、14 个无值长旗标，67 项元数分类全部与本机 curl 8.7.1 一致。[逐项审计及连接语义注释](spec/arity-audit.json)。

独立 36 例新探针及主审再次真实重跑，只有 SP-30 六行假绿。`-Zg/-gJ` 合法单 URL 保持 OK、双 URL 拒绝；`-JO/-J -O` 旧 OK→当前 MISSING，是修正 J 吞值后露出本不接纳的 O，归入保守边界，不另报回归。合法查询 `?a[]=1`、转义花括号及终止符后同形 URL 被保守拒绝；`%7B/%5B` 保持字面语义。retry 族名单外选项维持拒绝。`--upload-file={a,b}` 长等号形态本已拒绝；`-g` 关闭上传 glob 的例子因本地字面文件不存在而 exit 26/MISSING。

FTP 原本即受 HTTP/HTTPS 前置过滤。本轮初设 closed FTP 对照期望 OK 错误，最终校准为 MISSING；原始结果和原因保留，不编号产品缺陷。[校准说明](spec/calibration.json)。另四例 HTTP2 字节交互未观察假绿，但未证明 curl 发生真实内部重试，不能宣称内部重发语义已穷尽。[HTTP2 限定证据](spec/h2-probe.json)。

## 回归及证据核对

- runtime_gate、runtime_boundaries、records_backend、github_backend 四套完整执行均通过。
- plugin_package 为**部分执行通过**：三个主动令牌落盘测试未运行；其余检查通过。首次副本缺少设计模板导致一项失败，补齐只读对照模板后重跑通过；初始失败日志保留，属于副本准备问题。
- 隔离安装 driver **33 PASS / 0 FAIL**。删除真实 auth.json 链接，颁发令牌仅在内存和内部管道传递，不保存实例完整返回 JSON 或 .token 文件。恢复后副本 driver 与源逐字节一致。[适配 diff](driver-isolation-10.diff)、[driver 日志](logs/driver-probes-10.log)。
- 18 份 run.sh 仅用 `bash -n` 检查语法，全部通过；产品范围 `git diff --check` 通过。
- 独立 Standards 轴验证旧测试 AST 不变、新增 22 夹具/22 断言、21 份 driver 刷新语义零差、166 份归档一致。包/manifest/plugin 为相同 79 文件及字节，PAX=0。归档一致性不能证明实施者历史 /tmp 产物的生成过程。
- 交付 dist 未重建。package 检查自身进行了两份临时副本的重建并清理，不替换交付包。

[套件明细](suite-results-10.json)、[语法检查](syntax-checks-10.json)、[产品 diff 检查](product-diff-check-10.json)、[独立证据审计](standards/evidence.json)。

## 验证边界与收口条件

1. **真实仓库只读边界满足。** 零工作树修改、零提交/推送/tag；开始与结束 HEAD 相同，全部受控文件哈希相同。没有以任何参数启动 `acceptance/*/run.sh`，只执行文本提取函数或已有测试提取段。没有真实 GitHub 请求或写入，没有产品/验收模型轮，没有修改日常客户端安装。
2. **令牌边界按本次硬要求收紧。** 不读取日常账户凭据；driver 去除真实 auth 链接，运行凭据仅经内存和内部管道传递。复制历史文件时在内存中先去除一份历史事件的原始测试令牌，再写任务副本；真实源文件未改。任务产物原始 64 位十六进制 token/token_in_args 字段扫描及 .token 文件盘点均为零；这是指定字段扫描，不是通用秘密检测。初始扫描将清单中以 token 结尾的文件名及其 SHA 当作字段，已校准并保留说明。[扫描](token-output-scan-10.json) 与 [副本预脱敏记录](redacted-copy-manifest.json)。
3. **三项测试未执行，不能宣称五套件完整通过。** `test_accept16_sanitize_covers_unenumerated_tokens`、`test_accept16_secret_scan_gate`、`test_accept18_leak_checks_mechanized` 会故意落盘令牌明文，与本轮硬边界冲突，因此从测试入口排除并明确记为未运行，没有通过改写结果冒充 PASS。静态检查确认本批未改这些测试，但这不替代本轮执行。
4. **原探针的严格网络隔离存在证据缺口。** 原 `new-probes-9.py` 的 `terminator-attached-option` 已执行命令含 `-- -sSm2 http://127.0.0.1:端口/closed`；`-sSm2` 在终止符后成为 URL 类输入，真实输出先出现约 2 秒 operation timeout，再出现显式 loopback 连接超时。该行并非只有 loopback 字面地址；本次没有抓包或 egress 强制限制，不能证明其 DNS/连接尝试全部留在 loopback，也不能把所有服务只绑定 loopback 推导成全部客户端流量仅 loopback。未观察到该行成功请求或真实 GitHub 访问，但这不足以证明完整隔离。发现后未再次运行该行；后续宜只回放其事件，或先建立可核验的网络限制。本条是审查执行边界限制，不编号为产品 SP 缺陷。[原始命令与输出](new-probes-9.json)。
5. 已接受的 SP-25 正文精确模拟诊断行、--url、三层以上 shell、多 URL 保守拒绝、无缓存 posts=2、并发交错、迁移截断 current、ambient 重映射仍点名 .1 等限制不重开。机器摘要保留原 observed_bug 字段；没有字段的原结果记 null，不伪造为 false。
6. 本任务服务均已关闭，进程盘点无本任务残留；driver 临时安装和运行 arena 已清理，审查证据保留在本任务目录。[清理记录](cleanup-10.json)、[最终源边界核验](final-boundary-check-10.json)。
7. **v1 技术收口不通过，直接产品阻塞为 SP-30。** 即便修复 SP-30，也应重新验证其六形态和正常对照，并如实处理本报告的验证覆盖及隔离限制。此前人工验收、设计决定、安装和发布决定不由本复审替代；本报告不构成发布授权。

## 实际执行的命令类别

- 真实仓库只读 Git：status、rev-parse、branch、log、diff、show、ls-files；文本读取、AST/JSON/包成员检查、SHA-256 比较。
- 任务 /tmp：安全文件副本、脚本路径/API/守卫断言适配、提取函数、独立变异、结果汇总和报告写入。
- Python 历史原探针与四套完整测试；package 的允许部分；FakeTransport/MCP/Gate 检查及 driver 的本机替身流程。
- 本机 curl --version / --help all / --manual / 无参元数审计；任务 HTTP/FTP/HTTP2 服务上的真实 curl；其中一条原脚本非 loopback 字面输入的限制见上文。
- `bash -c` 执行提取函数；`bash -n` 语法检查；没有启动 acceptance run.sh。
- driver 在任务副本内执行本地插件安装和本地 fixture 仓库初始化；无真实远端 clone/fetch/写入。package 仅在临时副本重建。
- 仅清理本任务创建的临时安装与 arena，读取进程信息时只输出 PID/可执行程序名，最终做源文件及产物一致性核验。

## 两轴独立报告

以下保留两轴各自结论与证据口径；Standards 的通过不抵消 Spec 的缺陷。

### Standards

**Standards：0 项明文标准硬违规；0 项报告级判断性异味。**

固定审查 `git diff e3741c6..66b8506`。真实 HEAD 始终为 `2288aeb86fac18c7d69e7a2ca291bbb6e50a32c5`，工作树干净；额外提交只含第十轮交接文档。

标准依据为 AGENTS.md、AGENTS.zh-CN.md、CONTEXT.md、docs/agents 三份约定及十二项 Fowler 启发式。单票结构、Status 与 Comments 追加符合 `docs/agents/issue-tracker.md:7–11`；未引入领域术语或 ADR 冲突（`docs/agents/domain.md:25–29`；当前无 ADR 文件）。

`run.sh:251–267、307–310、344–345` 的分类与拒绝逻辑限定在 `curl_direct_denied`；函数外逐字节不变，heredoc 仍可完整抽取。没有新增依赖。测试夹具为可重放证据，有意保留输出；未把其重复机械判为产品逻辑重复。

`tests/test_plugin_package.py:3230–3339、3712–3776` 新增 22 夹具、22 行为断言。AST 删除这些新增节点并恢复旧 docstring 后，整个模块与基线 AST 完全一致：旧断言、接线及抽取执行方式均未改。SP-25 已接受残余明确锁定现状 OK；retry 对照明确锁定 MISSING。

计数需按组表达：票 01 第 17、58 行已披露「八核心反例红 + retry-closed-control 另红一项」，所以全 22 项用旧实现应红九项。票面没有把完整套件总数九隐藏为八；历史先后时序不能由静态证据证明。

21 份 driver 刷新逐字段核验时间、身份一致映射、指纹格式、临时路径及 loopback 端口后，语义差异为零。五份留存流相对 `e3741c6`、`a3c43ce` 均逐字节不变。166 份第九轮归档自 `fe8572d` 至产品目标未改；37 JSON、84 JSONL 均可解析。这是归档一致性证据，不证明实施者历史 /tmp 产物来源。

plugin/、dist/ 无差异。包、manifest 与源均为相同 79 文件及字节，PAX 为零，交付 SHA-256 仍 `3c44e2c0aaa0f02571fc394b30dd4ed34a9d0833c554531856b6a04f47c37ea7`。本轴未构建、未启动任何 acceptance run.sh、未跑模型轮或改变安装；行为复跑与最终收口由主审汇总。详见本目录 evidence.json。


### Spec

**SP-27～29 的指定反例已修复；新增 SP-30 一项 P2，属于历史遗漏。本轴不支持 v1 技术收口。**

独立重放归档 19+3 例：当前仅 `full-diagnostic-body` 保留原 `observed_bug=true`，按已接受限制处理；`retry-closed-control` 按披露改为 MISSING，其余符合。四张白名单共 67 项，逐项对读本机 curl 8.7.1 帮助、无参执行和本机完整手册，参数元数错分类为 0。此结论不代表全部连接语义安全。

**SP-30 · [P2] 上传文件名 glob 绕过单请求约束。** `run.sh:258/264` 接纳 `T/--upload-file`，`:314–316/:335–339` 直接消费其值；`:309/:344` 的 glob 检查仅覆盖 URL 位置参数。`curl -T '{a.txt,b.txt}' http://127.0.0.1:端口/upload/` 可展开两次 PUT。本轮六种真实形态（短分离、长分离、短粘连、聚合、方括号范围、URL 在 `--` 后）均首次 PUT 收到 18 字节、返回 200/`UPLOAD_SUCCESS`，随后第二连接出现真实 stderr `curl: (7) Failed to connect to 127.0.0.1 …`；当前却 OK，应 MISSING。本机手册 `--upload-file` 明确支持单 URL 多文件 glob。违反 review7 票 01:16“失败证据须能证明对替身的连接未被允许”及 review6 票 02:14 的失败归属合同。

六例在 `e3741c6`、`3f3031a` 同样 OK，因此不是本批引入。只检查上传值 glob 的提取函数守卫使六例全部 MISSING，恢复全部 OK；两条普通单文件上传真失败对照全程 OK。另留较宽的“移除上传旗标”守卫，它会同时拒绝这两个对照，未隐瞒代价。

36 例新运行仅上述六行不符。`--upload-file={a,b}` 本就拒绝；`-g` 禁止上传展开；编码 `%7B/%5B` 保持字面语义。`-JO/-J -O` 旧 OK→当前 MISSING 是 J 分类修正后露出未知 O 的保守结果，不另报回归。FTP 既有 HTTP/HTTPS 过滤，初设预期校准已保留原始结果。另四例 HTTP2 尝试未观察假绿，不能据此证明内部重发完备安全。

仅执行文本提取函数，未启动 run.sh；真实仓库只读，产物均在本目录。所有任务服务线程关闭；无凭据/令牌文件或输出，无模型轮。完整回归及最终仓库边界由主审汇总。

证据：[机器摘要](spec/spec-summary.json)、[67 项审计](spec/arity-audit.json)、[36 例实跑](spec/new-curl-probes.json)、[因果矩阵](spec/upload-causal-matrix.json)、[精确守卫](spec/upload_glob_guard.diff)、[22 例归档重放](spec/original-replay.json)、[HTTP2 边界](spec/h2-probe.json)、[校准留档](spec/calibration.json)。


两轴总计：**Standards 0 硬违规 / 0 报告级异味；Spec 1 项 P2（SP-30）。SP-27～29 指定反例已修复，未发现本批新回归，v1 暂不具备技术收口条件。**

[机器摘要](verification-summary-10.json)。

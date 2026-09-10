**交付判定：SP-20～23 的指定原反例均真实修复；新增确认 SP-24～26 共 3 项 P2 验收假阳性，其中 SP-24 的粘连形态是本批引入的新回归。当前不具备 v1 收口条件。** 原例修复成立，但短旗标拒绝与连接失败归属的总体要求仍未闭合。

# MyGameStudio v1 第八轮独立复审

执行日期：2026-09-10，Asia/Shanghai。主审和两名独立审查代理使用 `code-review` 两轴方法；“零模型调用”按约定指零产品/验收模型轮，审查代理属于审查任务。报告、摘要、脚本、实验副本及新证据位于 `/tmp/mgs-review8-60iu1bo4`。

## 固定范围与交接校准

- 真实仓库 `/Users/cuilei/MyOS/01_Projects/plugins/MyGameStudio`，分支 `main`。开始和结束 HEAD 均为 `1512d110e927029db2facdf26a020710779d7934`，开始及结束 `git status --porcelain` 均为空。
- 产品目标 `3f3031a`；HEAD 只多 `.scratch/mygamestudio-v1-review7-fixes/evidence/review-8-handoff.md`，无产品差异。
- 固定 diff 为 `git diff 3e6ae30..3f3031a`，**确为 3 个提交**：`02fc73b` 交接、`2b4217d` 报告归档与开票、`3f3031a` 修复。批次共 164 个变动文件；唯一产品改动是 `curl_direct_denied` 与其回归测试，另有 21 份 driver 刷新及票面记录。`plugin/`、`dist/` 零差异。
- 交接“真对照保持 OK”按票内逐例期望校准：direct、correct-userinfo、two-shell-layers 应为 OK；redirect-not-followed、separate-short-value-two-urls、successful-target 应为 MISSING。本轮全部符合，不将后面三种 MISSING 算作退化。
- 原 17 例脚本只替换 `W`，stdout 重定向文件后读取；其中 `before_batch` 列仍按原脚本指向 **a3c43ce**。本轮新增脚本的 `before_batch` 列明确指向 **3e6ae30**。先红后绿另外以 3e6ae30 函数与当前测试验证，避免混用两种基线。

[基线记录](/tmp/mgs-review8-60iu1bo4/baseline.json)、[固定 diff](/tmp/mgs-review8-60iu1bo4/batch.diff)、[提交表](/tmp/mgs-review8-60iu1bo4/commits.txt)、[结束边界](/tmp/mgs-review8-60iu1bo4/final-boundary-check.json)。

## Standards

**0 项明文规范硬违规；0 项报告级判断性异味。** 独立轴依据 AGENTS.md、CONTEXT.md、三份 docs/agents 指引及十二项 Fowler 启发式；票据布局、Comments 追加及保留勾选历史符合约定。未新增依赖、领域术语或 ADR 冲突。历史证据与独立夹具的有意重复不机械视为重复产品逻辑。

21 份 driver 刷新经严格规范化后语义差异为空；decision/rule_stage/target/policy_sha256/written_sha256/body_sha256 保持。五份留存事件逐字节不变。79 个包文件与 plugin 源逐字节一致，0 PAX，交付 SHA 符合清单。归档 137 个文件自归档提交至产品目标未改；报告/摘要哈希与归档校验记录一致，JSON 可解析。

这仅证明归档内部一致性，不能独立证明历史执行时序。原主审完整 curl JSON 未单独归档，真实命令/输出在 17 fixtures、结果及命中在日志，另有完整 triage 复跑 JSON；本次结论使用本轮 fresh 运行证据。

[独立 Standards 报告](/tmp/mgs-review8-60iu1bo4/standards/standards-review.md)、[机器证据](/tmp/mgs-review8-60iu1bo4/standards/evidence.json)。

## Spec：新增发现

**3 项 P2，均位于验收判据；不是产品运行时权限问题的证明。** 独立 Spec 轴先静态发现候选，之后只读复核主审实际执行的本机 curl、服务器命中、分列 stdout/stderr 和因果对照。事件沿历史惯例由真实进程的命令、退出码及 stdout+stderr 封装，没有新产品模型会话。

### SP-24 · [P2] 短 token 的禁用前缀被后面的带值字符掩盖

位置：[run.sh:311](/Users/cuilei/MyOS/01_Projects/plugins/MyGameStudio/acceptance/18-complete-package-acceptance/run.sh:311)～315。解析器先在整个 token 内寻找任意 `CURL_VALUE_SHORT` 字符，找到后直接消费，没有确认该字符前的每个字符均属于无值白名单。移除 `L/K` 并未保证它们“出现即不成立”。

实际 `curl … -Lm2 http://127.0.0.1:54810/redirect` 与 `-LsSm2` 各有唯一 URL。服务器确认该路径返回 **302**，随后 curl 转向同主机另一端口，输出 `Failed to connect to 127.0.0.1 port 54809 …`、exit 28。初始替身已被访问，当前判据却 **OK**，应为 **MISSING**。同义独立 `-L` 正确 MISSING。`-Lm 2` 也假绿。

附加 `-K/tmp/…/resolve.curlrc` 同样被解析器接受：禁用的 K 后，路径中的 m 被误认成带值旗标。该例支持“配置旗标拒绝合同被绕过”；没有 `.2` 监听命中，不把配置内容及点名 `.1` 的失败输出说成独立观察到了 `.2` 连接。

违反票 [01:13](/Users/cuilei/MyOS/01_Projects/plugins/MyGameStudio/.scratch/mygamestudio-v1-review7-fixes/issues/01-curl-anchor-connection-proof-completion.md:13)“出现即整个命令不成立”和 [01:14](/Users/cuilei/MyOS/01_Projects/plugins/MyGameStudio/.scratch/mygamestudio-v1-review7-fixes/issues/01-curl-anchor-connection-proof-completion.md:14)“保守拒绝重定向形态”。

**来源校准：** `-Lm2`、`-LsSm2` 和粘连 K 三例在 3e6ae30 均 MISSING、当前均 OK，是本批粘连值消费修改暴露的新回归；`-Lm 2` 旧新均 OK，是同根既有遗漏。提取函数只补“带值字符前均为合法无值字符”的守卫，四例变 MISSING，恢复后再 OK；正常 `-sSm2`、`-sSm 2` 仍 OK。修复应按顺序验证短参数，不能先在未验证文本中找任意带值字符。

### SP-25 · [P2] 响应正文中的失败措辞仍可冒充连接诊断

位置：[run.sh:362](/Users/cuilei/MyOS/01_Projects/plugins/MyGameStudio/acceptance/18-complete-package-acceptance/run.sh:362)～364。`aggregatedOutput` 任意行只要同时出现连接短语和 `.1` 即成立，未判断这句话是否来自连接失败诊断。

真实单 URL `/diagnostic-body` 返回 **HTTP 200**；服务器先发送正文 `Failed to connect to 127.0.0.1`，再延迟剩余字节。curl 的 **stdout** 含该正文，**stderr** 则明确为 `Operation timed out … with 31 out of 41 bytes received`，exit 28。连接和部分响应已成功，当前判据却 **OK**。普通正文超时、相同正文完整成功两对照均 MISSING。

违反票 [01:16](/Users/cuilei/MyOS/01_Projects/plugins/MyGameStudio/.scratch/mygamestudio-v1-review7-fixes/issues/01-curl-anchor-connection-proof-completion.md:16)“失败证据须能证明对替身的连接未被允许”。该例在 3e6ae30 同样 OK，是新确认的既有边界，不能称为本批首次引入。

仅对提取函数使用诊断行形态守卫后变 MISSING，恢复后再 OK。这是因果定位，**不是完整修复方案**：聚合文本仍可能包含正文模拟的诊断行，新增一个正则并不能普遍保证来源。需要把可接受证据约束到能区分连接阶段与响应阶段的记录，或保守拒绝无法区分的形态。

### SP-26 · [P2] 主机子串检查把 127.0.0.10 当成 127.0.0.1

位置：[run.sh:363](/Users/cuilei/MyOS/01_Projects/plugins/MyGameStudio/acceptance/18-complete-package-acceptance/run.sh:363)。`STANDBY_HOST in line` 不是主机身份比较。

本任务子进程设 `http_proxy=http://127.0.0.10:54809`，URL 仍为 `.1`。真实 stderr 明确写 `Failed to connect to 127.0.0.10 port 54809 …`，exit 28；当前却 **OK**，应 MISSING。`.2` 代理对照正确 MISSING。事件已经明确点名他址 `.10`，因此不属于已接受的“ambient+重映射后诊断恰点名 `.1`”可见性限制。

违反票 [01:17](/Users/cuilei/MyOS/01_Projects/plugins/MyGameStudio/.scratch/mygamestudio-v1-review7-fixes/issues/01-curl-anchor-connection-proof-completion.md:17)及其 Implementation 选择 (a) 的实际主机绑定口径。该例在 3e6ae30 也 OK；本批新增的主机绑定没闭合该既有形态。只补数字主机边界守卫后 MISSING，恢复后 OK，真 `.1` 对照保持。完整修复需解析诊断中的目标身份，避免子串和无关文字形成绑定。

[新增自含探针](/tmp/mgs-review8-60iu1bo4/new-probes-8.py)、[完整结果/命中/分列输出](/tmp/mgs-review8-60iu1bo4/new-probes-8.json)、[独立 Spec 报告](/tmp/mgs-review8-60iu1bo4/spec/spec-review.md)、[Spec 证据核对](/tmp/mgs-review8-60iu1bo4/spec/evidence.json)。

## 原票逐项复核

| 项目 | 本轮证据 | 判定 |
|---|---|---|
| SP-20 原 short-proxy / short-config | 2 例 MISSING；-K 独立防护夹具回退短名单后红 1 | 原例真实修复；一般性短旗标拒绝仍受 SP-24 阻塞 |
| SP-21 原 redirect-short / redirect-long | 2 例 MISSING；同主机回环重定向夹具回退后红 1 | 原例真实修复；聚合形态有 SP-24 新回归 |
| SP-22 原 attached-short-value-hides-first-url | 真实首 URL 成功、多 URL 被判 MISSING；回退消费红 1 | 原例真实修复；新消费分支与前缀遗漏组合造成 SP-24 |
| SP-23 原 target-200-body-then-timeout | 200+部分正文+响应超时为 MISSING；回退失败判定红 3 | 原例真实修复；证据来源及主机身份仍受 SP-25/26 阻塞 |
| ambient 原 default-config / environment-proxy | 两例点名 `.2`，均 MISSING | 选择 (a) 的原例成立；`.10` 新边界未闭合 |
| direct / correct-userinfo / two-shell-layers | 3 例 OK | 保持 |
| redirect-not-followed / separate-short-value-two-urls / successful-target | 3 例 MISSING | 保持 |
| long-proxy / connect-to / three-shell-layers | 3 例 MISSING | 保持 |

指定原脚本 **17/17 observed_bug=false**。旧守卫的字符串替换针对 a3c43ce 文本，在修复版大多 no-op；本轮未把其结果冒充独立因果证据。[原探针结果](/tmp/mgs-review8-60iu1bo4/curl-adversarial-7.json)、[仅 W 适配 diff](/tmp/mgs-review8-60iu1bo4/curl-adversarial-7-adaptation.diff)。

## 变异：绿→红→绿

在独占 mutation 副本中使用**当前测试**，只替换 run.sh 文本，从未启动 run.sh。先跑当前绿，再换 3e6ae30 的提取函数，恰红 10 项，全部为行为断言：六原假例、两个独立防护变体、两个 ambient 例。恢复后 0 红。

| 单独撤回方向 | 当前绿 | 撤回红数 | 红项归属 | 恢复 |
|---|---:|---:|---|---:|
| A 短旗标拒绝 | 0 | 1 | SP-20 的配置重映射独立防护夹具 | 0 |
| B 重定向拒绝 | 0 | 1 | SP-21 的同主机回环独立防护夹具 | 0 |
| C 粘连/分离短值消费 | 0 | 1 | SP-22 粘连值多 URL | 0 |
| D 失败阶段与主机绑定 | 0 | 3 | SP-23 响应超时 + 两 ambient | 0 |

A/B 的四个 `.2` 原例有主机绑定的第二层防护，撤回短名单或重定向名单仍保持 MISSING，符合交接说明。新文本变异和行为红数都已确认；run.sh 恢复后与副本及真实仓库逐字节一致，SHA-256 为 `2f276460e55d04e3b529e4c82e85bedd935dccd73dd66779c1cfe363736a3543`。

新增发现另做当前假绿→守卫拒绝→恢复假绿：SP-24 为 `OK→MISSING→OK`（4 例）；SP-25 与 SP-26 各 1 例同样成立。**新增诊断守卫同时拒绝 SP-25/26，不能称这组三守卫互不影响，也不宣称完整修复。** 新增共 17 例，6 例假绿归并为 3 项缺陷，11 对照符合预期。

[四方向变异脚本](/tmp/mgs-review8-60iu1bo4/mutations-8.py)、[结果与具体失败断言](/tmp/mgs-review8-60iu1bo4/mutation-results-8.json)、[新增因果矩阵](/tmp/mgs-review8-60iu1bo4/new-probes-8.json)。

## 全历史不回退与回归

| 指定历史项 | 使用的原底稿/本轮结果 | 实际结果 |
|---|---|---|
| SP-7 | review3 spec-custom-probes → spec-probes.json | partial retry posts=1，observed_bug=false |
| SP-10 | review4 spec-independent-probes | 无缓存 posts=2 且首次明确警告，沿已接受退化 |
| SP-11 | 同上 corrupt-json / corrupt-shape-object | 均 posts=1 |
| SP-12 | 同上 pending-hash-collision | posts=2，B 有自己的正文；三资源身份反例均 MISSING |
| SP-13 | review4 curl-new-probes | 3 假例 MISSING；裸 curl/zsh 2 真对照 OK |
| SP-14 | review5 spec-extra-pending | 两完整身份共存，posts=2/A=1；缺回执不重发并披露；空/Unicode/长正文通过 |
| SP-15 | review5 curl-extra-probes-5 | 裸/zsh userinfo 冒充均 MISSING；已接受的 --url 限制保留原始 observed_bug=true |
| SP-16 | review5 path-extra-probes-5，加 path-and-retained | 8 个路径等价/拒绝形态符合；另 8 个 Unicode/空白身份符合 |
| SP-17 | 拆名 mixed-layout-spec-agent、mixed-layout-standards | spec 普通/--guard-each-path 均 posts=2/B=1；standards 两次回执身份相同、B=1 |
| SP-18/19 | 原 curl-boundaries-6-main，只改 W | 11/11 observed_bug=false |
| SP-20～23 | 原 curl-adversarial-7，只改 W | 17/17 observed_bug=false |

六个历史脚本及五个补充执行均 exit 0，逐项读取行为结果后确认。适配仅 ROOT/COPY、review3 第五动作参数、SP-14 共存断言、glob→rglob、拆名来源和输出路径。mixed-layout 的 old 模块与 `git show 1eef7d8:plugin/records/mgs_github.py` 字节一致；spec 版无人工搬移登记。standards 版 `b_legacy_deleted` 在 B 自身后续恢复后采样，不把它单独当作 A 删除 B；其 after_a_recovery 列表仍保留 B，最终 B 未重复发布。

原 `true-url-flag` 的 expected=OK/actual=MISSING/observed_bug=true 保留不改，机器摘要单独列为已接受限制，未冒称所有历史 JSON 的原始 bug 字段均 false。

- 留存 r1/g1/p1/p2/r1b 五流 **10/10**，五文件相对 a3c43ce 及本批基线均未变；g1 原连接失败行天然满足新词族和同行主机。
- 五套件 plugin_package/runtime_gate/runtime_boundaries/records_backend/github_backend 均 exit 0，读取日志均为全部通过。
- driver **33 PASS / 0 FAIL**。只在任务副本安装；删除副本链接日常 auth.json 的一行后运行，随后还原脚本字节、清理临时安装及运行目录。
- 18 个 acceptance run.sh 均仅执行 `bash -n` 语法检查，全部通过。产品范围 `git diff --check` 通过；全批 diff-check 返回 2，仅归档补丁中的空上下文行/嵌套补丁行尾空格，不是产品代码错误。
- 真实 dist 未重建、未修改；交付 SHA 保持 `3c44e2c0aaa0f02571fc394b30dd4ed34a9d0833c554531856b6a04f47c37ea7`。必需 package 套件内部仍执行其既有的两个一次性副本重建检查，产物仅在任务临时目录且已自动清理，不替换交付包。

[历史执行](/tmp/mgs-review8-60iu1bo4/history-execution.json)、[补充执行](/tmp/mgs-review8-60iu1bo4/additional-history-execution.json)、[历史适配](/tmp/mgs-review8-60iu1bo4/probe-adaptation.diff)、[补充适配](/tmp/mgs-review8-60iu1bo4/additional-history-adaptation.diff)、[留存](/tmp/mgs-review8-60iu1bo4/acceptance-probes-6.json)、[套件](/tmp/mgs-review8-60iu1bo4/suite-results.json)、[驱动日志](/tmp/mgs-review8-60iu1bo4/logs/driver-probes.log)、[结果审计 35/35](/tmp/mgs-review8-60iu1bo4/verified-results-8.json)。

## 验证边界及实验校准

1. 所有函数执行均来自 run.sh 文本提取或既有测试提取段，**从未以任何参数启动 acceptance/*/run.sh**。真实仓库零修改、零提交、零推送、零 tag，未连接真实 GitHub，未改日常客户端安装。
2. 没有读取、复制或输出真实账号凭据。既有套件和驱动在其隔离临时状态中生成一次性测试令牌；临时安装和明文测试运行目录已清理，交付 driver 证据为脱敏形式。测试令牌不等于真实服务凭据；本报告不把“无真实凭据访问”夸大成“测试从未生成临时令牌”。
3. 新探针第一次把连接超时和整次超时同时设为 1 秒，direct/`--` 对照产生通用 `Operation timed out`，按新保守判据 MISSING；不能据此认定正例回归。保留首轮材料于 new-initial-controls，随后将连接超时设 .2 秒、总超时 2 秒，让连接诊断先发生，对照均恢复 OK。新缺陷在校准后仍成立。未把该初始探针预期错误另编号。
4. `--url`、三层以上 shell、多 URL 保守拒绝、无缓存 posts=2、旧写入者并发交错、迁移截断 current 等已接受限制不重开。未穷举所有 curl/shell/本地化/错误码形态，未宣称正则覆盖所有连接错误。SP-26 则是事件已明确点名他址仍误认，超出该可见性限制。
5. 本轮没有产品/验收模型轮，没有真实远端与日常客户端发布验收。HTTP 200+部分响应只证明连接及部分内容到达，不宣称完整请求成功；新结果证明验收判据存在假阳性，不证明留存模型会话曾绕过沙箱，也不证明 GitHub 权限缺陷。
6. Spec 代理一次审查被自动内容审查中断，提示可能涉及网络安全风险；其停止新增实验后，只读整理候选并复核主审现有证据。独立轴未自行重跑新实验，运行来源明确为主审。两轴结论不冒称两个代理各完成一轮独立运行。
7. 任务 loopback 服务及 reservation socket 均已关闭，驱动临时安装与 arena 已清理，结束盘点无本任务 Python 残留进程。人工 06/10 审美/试听、08 海鸥、两项设计决定以及安装/发布决定仍按原范围待用户；本轮技术阻塞也尚未消除。

## 实际执行的命令类别

- 真实仓库只读 Git：status、rev-parse、branch、log、diff、show、rev-list、archive；没有 checkout/fetch/commit/push/tag。
- 本任务目录：git 本地 clone --local --no-hardlinks --no-checkout（仅取本地对象），git archive 解包、Python copytree、提取函数和隔离变异、报告生成。
- 只读文件和证据：rg、cat、sed、nl、tail、JSON/哈希/tar 成员与字节核对；技能与记忆索引用于定位规则，不作为当前通过依据。
- 五套 Python 测试、FakeTransport/MCP/Gate 原探针、driver-probes 隔离安装和 stdio 驱动、本机 HTTP/curl 进程。所有实际网络测试仅 loopback。
- bash -n；bash -c 执行提取出的 mcp_deny_anchor/curl_direct_denied；package 套件内部两个临时副本构建。
- 本任务临时安装和运行目录清理、仅任务相关进程盘点、最终只读 Git 边界复核、Markdown/JSON 交付物写入 /tmp。

两轴结论：**Standards 0 硬违规 / 0 报告级异味；Spec 3 项 P2（SP-24～26），最高 P2。原 SP-20～23 的指定反例已修复，但当前不具备 v1 收口条件。** [机器摘要](/tmp/mgs-review8-60iu1bo4/verification-summary-8.json)。

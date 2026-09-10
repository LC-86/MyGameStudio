# MyGameStudio v1 第九轮独立复审委托(交接文档)

**目标**:验证第八轮修复票(SP-24~SP-26,单票)是否真实修复、是否引入新缺陷,并回答**是否具备 v1 收口条件**。这是第八轮复审(基线 `3e6ae30`,产品目标 `3f3031a`,报告 `review-8.md` 同目录)之后的首个针对性复核。

## 固定范围

- 真实仓库:`/Users/cuilei/MyOS/01_Projects/plugins/MyGameStudio`(分支 main)。
- **产品目标:`e3741c6`**(若当前 HEAD 比它多出的提交仅为本交接文档,则实际审 HEAD,无产品差异;以 `git status --porcelain` 为空、结束 HEAD 与开始一致为界)。
- **批次 diff:`git diff 3f3031a..e3741c6`**,恰三个提交(计数以 `git log --oneline 3f3031a..e3741c6` 实数为准):
  - `1512d11` 08-handoff:第八轮交接文档(纯文档)
  - `91991d9` 08-triage:第八轮报告归档与开票(纯文档;含 evidence 130+ 文件)
  - `e3741c6` review8-01:**唯一改产品的提交**——`acceptance/18-complete-package-acceptance/run.sh` + `tests/test_plugin_package.py` + 21 份刷新 driver 证据 + 票文件;零触碰 plugin/ 与 dist/(可在 diff 中确认)
- 实施者披露:本票由 Cursor CLI(cursor-agent,模型 grok-4.6 high)在与内置子代理完全相同的任务提示与硬边界下执行;复审以提交内容与行为为准,与实施工具无关。
- 批次背景与约定:`../spec.md`;票:`../issues/01-curl-anchor-prefix-diagnostic-host.md`(含三项反例、口径选择、先红后绿 6 项、拆层因果变异与口径咬合说明、两轴复查 Implementation 注释)。

## 必读背景

1. [review-8.md](review-8.md) —— SP-24~26 原始反例、来源校准(SP-24 三例为 3f3031a 引入的新回归、`-Lm 2` 同根既有遗漏;SP-25/26 既有边界)、对第七轮交接的逐例期望校准。
2. 探针与守卫材料在 [new-probes/](new-probes/):`new-probes-8.py`(17 例,prefix/host/diagnostic 三守卫)、结果 JSON、fixtures、`initial-controls-run/`(审方首轮校准对照)。
3. 沿第一至八轮口径:「零模型调用」指零产品/验收模型轮;两轴审查代理属审查任务本身。

## 本票核验点

- **修复形态**(`run.sh` `curl_direct_denied` 一函数域):
  - SP-24:短旗标按序验证(328 行)——首个带值字符**之前**的每个字符须都在 `CURL_PLAIN_SHORT` 内,否则返回 None(整个命令不成立);正常聚合 `-sSm2`/`-sSm 2` 消费语义不变(不回退 SP-22)。
  - SP-25:失败证据约束为 curl 诊断行形态(236 行 `connect_diag`:`^curl: \((?:7|28)\) (?:Failed to connect to|Couldn't connect to) <host>`,忽略大小写)——响应正文中的连接措辞(无诊断前缀)不成立;**残余边界留档**:aggregatedOutput 不分 stdout/stderr,正文逐字节模拟完整诊断行单正则无法区分来源(审方第八轮明示单正则非完整方案,票面按留档处置,不宣称完备)。
  - SP-26:诊断行中捕获的主机 token 与 `STANDBY_HOST` **相等比较**(381~383 行),非子串包含;`127.0.0.10` 不再绑定。
- **核心反例**:aggregate-redirect-attached(`-Lm2`)/separate(`-Lm 2`)/sSm2(`-LsSm2`)、attached-config(`-K路径`)、response-body-then-timeout、ambient-proxy-dot10 六例修复后全 MISSING;对照逐例不变——OK 组:direct、valid-aggregate-attached/separate、terminator-url;MISSING 组:standalone-config/redirect、invalid-short-value、proxy-user-short、plain-body-then-timeout、response-body-completed、ambient-proxy-dot2。
- **探针复跑适配(重要,主会话已踩过)**:
  - `new-probes/new-probes-8.py` 的 W 常量指向第八轮工作区(`/tmp/mgs-review8-60iu1bo4`),复跑须改为你的工作区;其第 11 行 `assert all(v!=cur ...)` 要求三守卫异于当前函数——**守卫替换目标是修复前(3f3031a)文本,在 e3741c6 上 guard_host 为 no-op、断言必炸**;适配=改 W + 去掉该断言行(主会话先例:仅此两处,17 例与判据零改动)。因果守卫请按惯例对**新文本**重建。
  - 复跑第七轮 `curl-adversarial-7.py` 时,注意本目录(`review8-fixes/evidence/`)归档副本的 W 指向**第八轮**工作区;原始版(W=第七轮工作区)在 `../../mygamestudio-v1-review7-fixes/evidence/curl-adversarial/curl-adversarial-7.py`,任选其一改 W 即可。
- **先红后绿**:六夹具(真实 curl 封装:SP-24 例 `/redirect` 302 且 `.1` 命中、SP-25 例 200+诊断正文+延迟、SP-26 例 env `http_proxy=http://127.0.0.10:端口`)修复前恰红 6 项、修复后全绿;AST 提取与真实产物逐字节一致。
- **因果拆层变异**(票面已留档):前缀验证撤回红 4(全落 SP-24);诊断来源撤回(去 `curl: (N)` 前缀、保留主机相等)红 1(仅 SP-25);主机身份撤回(保留诊断行、改回子串)红 1(仅 SP-26);旧「短语+子串」组合谓词红 2(SP-25 与 SP-26 同时)——两层可独立守住对方反例,口径咬合如实呈现;恢复后 run.sh 与工作树 cmp 逐字节一致。
- **留存零回退**:留存五流 10/10(g1 真实输出 `curl: (7) Failed to connect to 127.0.0.1 port 64026 …` 诊断行形态+主机相等天然满足);第七、八轮既有 17+17 夹具重放逐项不变(主会话总验已双跑复核);`mcp_deny_anchor`、剥壳、heredoc 提取约定零触碰。
- **回归**:五套件、33 驱动、`bash -n` 应全过;plugin/ 零改动、dist 不重建(交付 SHA 仍 `3c44e2c0aaa0f02571fc394b30dd4ed34a9d0833c554531856b6a04f47c37ea7`)。

## 全历史不回退清单(指定原探针)

沿第八轮口径再跑:SP-7、SP-10、SP-11、SP-12、SP-13、SP-14、SP-15、SP-16、SP-17(mixed-layout,含 `--guard-each-path`)、SP-18/19(curl-boundaries 11 例)、SP-20~23(curl-adversarial 17 例)、SP-24~26(本批 new-probes 17 例)。脚本在各批次 evidence(适配先例同前八轮:ROOT/COPY 改隔离副本、review3 第五动作参数、SP-14 共存断言、glob→rglob、mixed-layout 拆名版、curl 系列只改 W、本批另加去 no-op 断言)。

## 欢迎新的对抗性探针(不限于)

- 前缀验证边缘:混合前缀(`-sLm2`:合法 s 后跟禁用 L)、`-` 单字符 token、`--` 终止符与粘连值组合、大小写形态。
- 诊断行形态:退出码 7/28 之外的连接失败(如 35/5,真实发生时判据应 MISSING 而非误 OK——真对照仅固定探针形态 7/28);诊断行带 shell 前缀文字、多行诊断、IPv6 主机 token(`[::1]`);主机捕获的贪心/懒惰边界(`127.0.0.1.evil.com`、`127.0.0.1:`)。
- SP-25 残余边界检验:正文逐字节模拟完整诊断行的形态(验证票面留档的边界范围与表述是否准确,而非重开已留档限制)。
- 既有留档限制不重开:`--url` 解析、三层以上 shell、多 URL 保守拒绝、无缓存 posts=2、并发交错、迁移截断 current、ambient+重映射诊断恰点名 `.1`。

## 输出契约

- `review-9.md`:交付判定开头(三项原反例是否真实修复、新增发现清单含编号 SP-27 起、逐项复核表、变异绿→红→绿、证据核对与验证边界、实际执行的命令类别)。
- `verification-summary-9.json`:机器可读摘要(两轴计数、原探针 observed_bug、新发现)。
- 明确回答:**SP-24~26 是否真实修复、有无新缺陷、是否具备 v1 收口条件**。

## 硬边界(沿前八轮)

- 真实仓库零改动:零工作树修改、零提交、零推送、零 tag;只读 Git 命令。
- **绝不以任何参数启动 `acceptance/*/run.sh`(包括 `--help`)**——证据清空事故先例;只允许从 run.sh 文本提取函数后用 bash 执行。
- 零真实远端写入(不连真实 GitHub);零产品/验收模型轮;不改日常客户端安装。
- 全部探针、变异、副本、安装放本任务 /tmp 工作区;报告与摘要写入 /tmp。
- 凭据/令牌绝不入文件或输出;测试/套件产物仅 loopback。

# MyGameStudio v1 第八轮独立复审委托(交接文档)

**目标**:验证第七轮修复票(SP-20~SP-23,单票)是否真实修复、是否引入新缺陷,并回答**是否具备 v1 收口条件**。这是第七轮复审(基线 `a3c43ce`,产品目标 `3e6ae30`,报告 `review-7.md` 同目录)之后的首个针对性复核。

## 固定范围

- 真实仓库:`/Users/cuilei/MyOS/01_Projects/plugins/MyGameStudio`(分支 main)。
- **产品目标:`3f3031a`**(若当前 HEAD 比它多出的提交仅为本交接文档,则实际审 HEAD,无产品差异;以 `git status --porcelain` 为空、结束 HEAD 与开始一致为界)。
- **批次 diff:`git diff 3e6ae30..3f3031a`**,恰三个提交(计数以 `git log --oneline 3e6ae30..3f3031a` 实数为准):
  - `02fc73b` 07-handoff:第七轮交接文档(纯文档)
  - `2b4217d` 07-triage:第七轮报告归档与开票(纯文档;含 evidence 130+ 文件)
  - `3f3031a` review7-01:**唯一改产品的提交**——`acceptance/18-complete-package-acceptance/run.sh` + `tests/test_plugin_package.py` + 21 份刷新 driver 证据 + 票文件;零触碰 plugin/ 与 dist/(可在 diff 中确认)
- 批次背景与约定:`../spec.md`;票:`../issues/01-curl-anchor-connection-proof-completion.md`(含四项反例、口径选择、先红后绿 10 项、因果变异四方向、两轴复查 Implementation 注释)。

## 必读背景

1. [review-7.md](review-7.md) —— SP-20~23 原始反例、来源校准(四项对 `a3c43ce` 均成立)、ambient 配置观察项、并发交错恢复限制(条件性、不另计阻塞)。
2. 探针与守卫材料在 [curl-adversarial/](curl-adversarial/):`curl-adversarial-7.py`(17 例)、结果 JSON、fixtures、`curl-causal-controls-7.json`(第七轮守卫矩阵)。
3. 沿第一至七轮口径:「零模型调用」指零产品/验收模型轮;两轴审查代理属审查任务本身。

## 本票核验点

- **修复形态**(`run.sh` `curl_direct_denied` 一函数域):
  - SP-20:`CURL_VALUE_SHORT`(244 行)移除 `x`/`K`/`U`(U 为代理域旗标,宁严勿宽,理由留档票面);出现即名单外旗标→None→MISSING。
  - SP-21:`CURL_PLAIN_SHORT`(245 行)移除 `L`、`CURL_PLAIN_LONG` 移除 `--location`——重定向形态保守拒绝。
  - SP-22:短旗标值消费(311 行起)按 curl 语义——首个带值字符居 token 末尾取下一参数为值;粘连形式(`-m2`/`-sSm2`)值即余部、只消费当前 token;歧义形态(如 `-ms2`)取余部为值(口径留档)。
  - SP-23:失败词族收窄为连接阶段短语 `failed to connect|couldn't connect|connection refused`(228 行)并**绑定实际尝试主机**(363 行:同一行须含 `STANDBY_HOST`=127.0.0.1)——通用 timed out/响应阶段超时/中文报告措辞不再单独成立。
  - **ambient 观察项处置 (a)**:`CURL_HOME/.curlrc`、`http_proxy` 使实连他址时失败输出点名 127.0.0.2,主机绑定天然使其 MISSING(套件夹具 AP/AQ 固化);ambient+重映射叠加使失败行点名 `.1` 的形态留档为事件可见性限制。
- **核心反例**:short-proxy、short-config、redirect-short、redirect-long、attached-short-value-hides-first-url、target-200-body-then-timeout 六例修复后全 MISSING;ambient 两例(default-config、environment-proxy)MISSING;真对照 direct、correct-userinfo、two-shell-layers、redirect-not-followed、separate-short-value-two-urls、successful-target 保持 OK。
- **探针**:`curl-adversarial/curl-adversarial-7.py`,适配仅 W 常量一处(指向你的工作区,内建 `repo/` 放目标 run.sh、`repro/` 为含 `a3c43ce` 的本地克隆);stdout 重定向文件消费。修复版应 **17/17 observed_bug=False**。**注意**:脚本内的守卫变体(`cur.replace(...)` 三处)是针对 `a3c43ce` 时代文本的替换,对修复版文本多为 no-op(守卫列≈current 属预期);因果守卫请按前几轮惯例用 mutations 脚本对**新文本**重建(归档 `curl-causal-controls-7.json` 是第七轮原版,仅作历史参照)。
- **先红后绿**:六假例 + 独立防护变体 + ambient 两例共**恰红 10 项**(红在行为断言);因果变异四方向(短旗标拒绝/重定向拒绝/短值消费修正/失败阶段绑定)单独撤回各自恰红 1/1/1/3、互不误伤;恢复后 run.sh 与工作树 cmp 逐字节一致。
- **留存零回退**:留存五流 10/10;g1 留存 curl 事件输出 `curl: (7) Failed to connect to 127.0.0.1 port 64026 after 0 ms: Couldn't connect to server` 天然满足「连接阶段词组+同行含替身主机」;既有等价类/拒绝形态(userinfo、-H 头部值、脚本假 -c、--version 注释、repeat-path/case-variant、IPv6/LOCALHOST/非法端口/host TAB、--proxy/--resolve/--host/--interface、--connect-to 等)逐项不变;`mcp_deny_anchor`、剥壳、heredoc 提取约定零触碰。
- **回归**:五套件、33 驱动、`bash -n` 应全过;plugin/ 零改动、dist 不重建(交付 SHA 仍为 `3c44e2c0aaa0f02571fc394b30dd4ed34a9d0833c554531856b6a04f47c37ea7`)。

## 全历史不回退清单(指定原探针)

沿第七轮口径再跑:SP-7、SP-10、SP-11、SP-12、SP-13、SP-14、SP-15、SP-16、SP-17(mixed-layout,含 `--guard-each-path`)、SP-18/19(curl-boundaries 11 例)、SP-20~23(本批,17 例)。脚本在各批次 evidence(适配先例:ROOT/COPY 改隔离副本、review3 探针补第五动作参数、SP-14 断言共存形态、登记枚举 glob→rglob、mixed-layout 用 `-spec-agent`/`-standards` 拆名版、curl 主审版只改 W)。

## 欢迎新的对抗性探针(不限于)

- 词族广度:`Could not connect`(空格形态)、`Connection timed out`(连接阶段但同行是否点名主机)、本地化输出、退出码 7/28/35 与空输出、stderr/stdout 混排多行。
- 叠加形态:粘连短值+重定向、`-x`+userinfo、代理端点恰在 127.0.0.1 而目标 URL 也为 `.1`(ambient+重映射叠加使失败行点名 `.1` 的已留档限制——欢迎检验边界与表述)。
- 旗标组合:新名单内短旗标聚合(`-sSm`、`-sSm2`)、`--` 终止符后参数、`-U` 移除后无参数依赖的残留路径。
- 既有留档限制不重开:`--url` 解析、三层以上 shell 包装、多 URL 保守拒绝、无缓存 posts=2 约定退化、并发交错(旧写入者混跑)、迁移中断截断 current。

## 输出契约

- `review-8.md`:交付判定开头(四项原反例是否真实修复、新增发现清单含编号 SP-24 起、逐项复核表、变异绿→红→绿、证据核对与验证边界、实际执行的命令类别)。
- `verification-summary-8.json`:机器可读摘要(两轴计数、原探针 observed_bug、新发现)。
- 明确回答:**SP-20~23 是否真实修复、有无新缺陷、是否具备 v1 收口条件**。

## 硬边界(沿前七轮)

- 真实仓库零改动:零工作树修改、零提交、零推送、零 tag;只读 Git 命令。
- **绝不以任何参数启动 `acceptance/*/run.sh`(包括 `--help`)**——证据清空事故先例;只允许从 run.sh 文本提取函数后用 bash 执行。
- 零真实远端写入(不连真实 GitHub);零产品/验收模型轮;不改日常客户端安装。
- 全部探针、变异、副本、安装放本任务 /tmp 工作区;报告与摘要写入 /tmp。
- 凭据/令牌绝不入文件或输出;测试/套件产物仅 loopback。

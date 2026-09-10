# MyGameStudio v1 第十轮独立复审委托(交接文档)

**目标**:验证第九轮修复票(SP-27~SP-29,单票)是否真实修复、是否引入新缺陷,并回答**是否具备 v1 收口条件**。这是第九轮复审(基线 `3f3031a`,产品目标 `e3741c6`,报告 `review-9.md` 同目录)之后的首个针对性复核。

## 固定范围

- 真实仓库:`/Users/cuilei/MyOS/01_Projects/plugins/MyGameStudio`(分支 main)。
- **产品目标:`66b8506`**(若当前 HEAD 比它多出的提交仅为本交接文档,则实际审 HEAD,无产品差异;以 `git status --porcelain` 为空、结束 HEAD 与开始一致为界)。
- **批次 diff:`git diff e3741c6..66b8506`**,恰三个提交(计数以 `git log --oneline e3741c6..66b8506` 实数为准):
  - `0029067` 09-handoff:第九轮交接文档(纯文档)
  - `fe8572d` 09-triage:第九轮报告归档与开票(纯文档;含 evidence 160+ 文件)
  - `66b8506` review9-01:**唯一改产品的提交**——`acceptance/18-complete-package-acceptance/run.sh` + `tests/test_plugin_package.py` + 21 份刷新 driver 证据 + 票文件;零触碰 plugin/ 与 dist/(可在 diff 中确认)
- 实施者披露:本票由 Cursor CLI(cursor-agent,模型 grok-4.6 Extra High + fast)在与内置子代理完全相同的任务提示与硬边界下执行;复审以提交内容与行为为准,与实施工具无关。
- 批次背景与约定:`../spec.md`;票:`../issues/01-curl-anchor-short-arity-retry-glob.md`(含三项反例、接纳表审计结论、先红后绿 8 项、因果变异 5/2/2、retry 翻转取舍、两轴复查 Implementation 注释)。

## 必读背景

1. [review-9.md](review-9.md) —— SP-27~29 原始反例、来源校准(均对 3f3031a 成立)、裸 -Z 进度文字校准、诊断变异两轮粒度校准、令牌落盘边界披露。
2. 探针与守卫材料:[new-probes/](new-probes/)(19 例,new-{short,retry,glob}-guard.diff 三守卫)、[parallel-supplement/](parallel-supplement/)(3 例,-sS -Z 形态)。
3. 沿第一至九轮口径:「零模型调用」指零产品/验收模型轮;两轴审查代理属审查任务本身。

## 本票核验点

- **修复形态**(`run.sh` `curl_direct_denied` 一函数域):
  - SP-27:`g`/`J`/`Z` 移入 `CURL_PLAIN_SHORT`(258~259 行)——两向修复(两 URL 假绿→MISSING、单 URL 反向假阴性→OK);票面声明**其余 19+12 个短旗标字符对照 curl 8.7.1 `--help all` 与无参执行无更多错分类**——欢迎独立复核该审计(逐字符对照本机 curl 语义)。
  - SP-28:`--retry` 移出 `CURL_VALUE_LONG`(264 行附近)——保守拒绝;**已披露翻转**:`retry-closed-control`(真失败+重试对照)从 OK 变 MISSING,测试期望已同步固化。
  - SP-29:URL 形态位置参数含 `{`/`}`/`[`/`]` 任一字符即返回 None(344 行),`--` 终止符后的参数同样检查(309 行);`--globoff`(本就不在旗标白名单)与 IPv6 字面量(本就过不了 hostname 检查)行为不变。
- **核心反例与期望**:no-value-g/J-two-urls、silent-Z-two-urls → MISSING;no-value-g-single-url、silent-Z-one-url → OK;retry-stop-after-503 → MISSING;url-glob-two-ports/after-terminator → MISSING;**两条已知例外行(设计如此,非缺陷)**:full-diagnostic-body → OK(SP-25 已接受残余限制,review-9 判据保留 observed_bug=true 原样)、retry-closed-control → MISSING(已披露保守翻转)。
- **探针复跑适配(主会话先例)**:`new-probes-9.py` 第 13 行 `assert v!=cur` 在修复版上因守卫 no-op 必炸——适配=改 W + 该断言改 pass;`new-probes-8.py` 同样需去 no-op 守卫断言(第 11 行)+改 W(注意本目录归档副本 W 指向第九轮工作区,原始版在 review8-fixes);`parallel-curl-supplement.py` 只改 W;`curl-adversarial-7.py` 原始版在 review7-fixes/evidence/curl-adversarial/。因果守卫请按惯例对**新文本**重建。
- **先红后绿**:八夹具修复前恰红 8 项(含两例反向假阴性的 OK 期望);因果变异三方向(接纳表分类/重试拒绝/glob 拒绝)单独撤回恰红 5/2/2、互不误伤;恢复修复版全绿、run.sh 与工作树 cmp 逐字节一致。
- **留存零回退**:留存五流 10/10;第七、八、九轮既有夹具重放逐项不变(17+17+19+3,除已披露翻转);`mcp_deny_anchor`、剥壳、heredoc 提取约定零触碰。
- **回归**:五套件、33 驱动、`bash -n` 应全过;plugin/ 零改动、dist 不重建(交付 SHA 仍 `3c44e2c0aaa0f02571fc394b30dd4ed34a9d0833c554531856b6a04f47c37ea7`)。

## 全历史不回退清单(指定原探针)

沿第九轮口径再跑:SP-7、SP-10、SP-11、SP-12、SP-13、SP-14、SP-15、SP-16、SP-17(mixed-layout,含 `--guard-each-path`)、SP-18/19(curl-boundaries 11 例)、SP-20~23(curl-adversarial 17 例)、SP-24~26(new-probes-8 17 例)、SP-27~29(本批 new-probes-9 19 例 + parallel-supplement 3 例)。脚本在各批次 evidence(适配先例同前九轮;本批新增加 no-op 守卫断言改 pass)。

## 欢迎新的对抗性探针(不限于)

- **接纳表独立审计**:对 `CURL_VALUE_SHORT`/`CURL_PLAIN_SHORT`/`CURL_VALUE_LONG`/`CURL_PLAIN_LONG` 全部字符逐一对读本机 curl 8.7.1 语义(带值/无值、连接语义),票面审计结论不是免检理由。
- glob 拒绝边缘:URL 查询串合法含 `[]`(如 `?a[]=1`)被保守拒绝的代价核对;百分号编码 `%7B`(curl 不展开,应按字面处理);转义形态 `\{`;glob+重试+重定向叠加。
- 重试族:`--retry-all-errors`/`--retry-delay` 等变体(不在白名单应已拒);无 `--retry` 但服务器侧多次请求的形态(如认证质询重发——若真实发生欢迎检验)。
- g/J/Z 重分类后:`-Zg`/`-gJ` 聚合、`-J` 与 `-O` 类组合;裸 `-Z` 进度文字形态保持 MISSING。
- 既有留档限制不重开:`--url` 解析、三层以上 shell、多 URL 保守拒绝、无缓存 posts=2、并发交错、迁移截断 current、ambient 重映射点名 `.1`、SP-25 正文模拟诊断行(复核留档范围即可)。

## 输出契约

- `review-10.md`:交付判定开头(三项原反例是否真实修复、新增发现清单含编号 SP-30 起、逐项复核表、变异绿→红→绿、证据核对与验证边界、实际执行的命令类别)。
- `verification-summary-10.json`:机器可读摘要(两轴计数、原探针 observed_bug、新发现)。
- 明确回答:**SP-27~29 是否真实修复、有无新缺陷、是否具备 v1 收口条件**。

## 硬边界(沿前九轮)

- 真实仓库零改动:零工作树修改、零提交、零推送、零 tag;只读 Git 命令。
- **绝不以任何参数启动 `acceptance/*/run.sh`(包括 `--help`)**——证据清空事故先例;只允许从 run.sh 文本提取函数后用 bash 执行。
- 零真实远端写入(不连真实 GitHub);零产品/验收模型轮;不改日常客户端安装。
- 全部探针、变异、副本、安装放本任务 /tmp 工作区;报告与摘要写入 /tmp。
- 凭据/令牌绝不入文件或输出;测试/套件产物仅 loopback。

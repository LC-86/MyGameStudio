# MyGameStudio v1 第十一轮独立复审委托(交接文档)

**目标**:验证第十轮修复票(SP-30,单票)是否真实修复、是否引入新缺陷,并回答**是否具备 v1 收口条件**。这是第十轮复审(基线 `e3741c6`,产品目标 `66b8506`,报告 `review-10.md` 同目录)之后的首个针对性复核。**上一轮仅 1 项发现、本票修复面很窄——若本轮干净且无新缺陷,结论将直接支撑 v1 收口判定。**

## 固定范围

- 真实仓库:`/Users/cuilei/MyOS/01_Projects/plugins/MyGameStudio`(分支 main)。
- **产品目标:`d604b92`**(若当前 HEAD 比它多出的提交仅为本交接文档,则实际审 HEAD,无产品差异;以 `git status --porcelain` 为空、结束 HEAD 与开始一致为界)。
- **批次 diff:`git diff 66b8506..d604b92`**,恰三个提交(计数以 `git log --oneline 66b8506..d604b92` 实数为准):
  - `2288aeb` 10-handoff:第十轮交接文档(纯文档)
  - `1927a46` 10-triage:第十轮报告归档与开票(纯文档;含 evidence 207 文件)
  - `d604b92` review10-01:**唯一改产品的提交**——`acceptance/18-complete-package-acceptance/run.sh` + `tests/test_plugin_package.py` + 21 份刷新 driver 证据 + 票文件;零触碰 plugin/ 与 dist/(可在 diff 中确认)
- 实施者披露:本票由 Cursor CLI(cursor-agent,模型 grok-4.6 Extra High + fast)在与内置子代理完全相同的任务提示与硬边界下执行;复审以提交内容与行为为准,与实施工具无关。
- 批次背景与约定:`../spec.md`;票:`../issues/01-upload-glob-rejection.md`(含六形态反例、精确/宽守卫取舍、先红后绿 6 项、两轴复查 Implementation 注释)。

## 必读背景

1. [review-10.md](review-10.md) —— SP-30 原始反例(六形态,均对 `e3741c6`/`3f3031a` 成立系历史遗漏)、四张白名单 67 项独立审计零元数错分类、两条验证限制(三项落盘令牌测试未跑——**主会话已按标准总验口径补跑完整 plugin_package 套件通过闭合**;旧探针一行网络隔离缺口——留档为后续探针注意项)。
2. 探针与守卫材料:[spec/new-curl-probes.py](spec/new-curl-probes.py)(36 例,once_upload 真实上传服务器形态)、[spec/upload_glob_guard.diff](spec/upload_glob_guard.diff)(精确守卫)与 [spec/upload_guard.diff](spec/upload_guard.diff)(宽守卫代价)、[main-confirm/](main-confirm/)(主审二次实跑)。
3. 沿第一至十轮口径:「零模型调用」指零产品/验收模型轮;两轴审查代理属审查任务本身。

## 本票核验点

- **修复形态**(`run.sh` `curl_direct_denied` 一函数域):
  - 长旗标:`--upload-file` 的值(327 行,含**缺值**形态 `i+1 >= len(args)`)含 `{`/`}`/`[`/`]` 任一字符即返回 None。
  - 短旗标:`T`(355~356 行)按 SP-22 语义取值——带值字符居 token 末尾取下一参数、粘连(含聚合 `-sST{a,b}`)取 token 余部——值含 glob 字符即返回 None。
  - 既有 URL 形态位置参数与 `--` 后参数的 glob 检查零改动;**不采用**移除上传旗标的宽方案(误伤普通上传真失败对照,代价已在因果变异留档)。
- **核心反例与期望**:upload-glob-short/long/short-attached/short-aggregate/range/after-terminator 六例修复后全 MISSING;普通单文件上传真失败对照 upload-single-closed / upload-long-single-closed 保持 OK;`-g` 关闭展开(upload-glob-with-g)与长等号形态(upload-glob-long-equals)保持 MISSING;direct 及其余对照逐项不变。
- **探针复跑适配(主会话先例,均已踩过)**:`spec/new-curl-probes.py` 适配三处——W 常量改你的工作区;R 常量**必须指向 git 仓库**(脚本对 R 做 `git show e3741c6/3f3031a` 取旧函数——主会话用产品目标的隔离克隆 checkout);守卫断言 `assert functions[name]!=cur` 在修复版上因 upload_glob_guard 变 no-op 会炸,改 pass。`new-probes-9.py`(第 13 行断言)/`new-probes-8.py`(第 11 行断言)同改 pass+改 W;`parallel-curl-supplement.py` 只改 W;`curl-adversarial-7.py` 原始版在 `../../mygamestudio-v1-review7-fixes/evidence/curl-adversarial/`。因果守卫请按惯例对**新文本**重建。
- **先红后绿**:六夹具(真实 curl:真实上传文件落 /tmp、本机服务器 accept 一次记录 method/path/字节数并返回 200/UPLOAD_SUCCESS 后关监听、第二连接真失败)修复前恰红 6 项;因果变异:撤回修复恰红 6(不误伤对照)、宽方案红 2(全落普通上传对照)、恢复全绿且 run.sh 与工作树 cmp 逐字节一致。
- **留存零回退**:留存五流 10/10;第七~十轮既有夹具重放逐项不变(17+17+19+3+36;第九轮探针中 `full-diagnostic-body` 保持 OK=SP-25 已接受限制、`retry-closed-control` 保持 MISSING=已披露翻转,两行按设计例外处理,原 observed_bug 字段不抹改);`mcp_deny_anchor`、剥壳、heredoc 提取约定零触碰。
- **回归**:五套件(含三项故意落盘令牌测试——若你的令牌边界允许请完整运行,不允许则如第十轮那样明确记为未运行、不要伪称通过)、33 驱动、`bash -n` 应全过;plugin/ 零改动、dist 不重建(交付 SHA 仍 `3c44e2c0aaa0f02571fc394b30dd4ed34a9d0833c554531856b6a04f47c37ea7`)。

## 全历史不回退清单(指定原探针)

沿第十轮口径再跑:SP-7、SP-10、SP-11、SP-12、SP-13、SP-14、SP-15、SP-16、SP-17(mixed-layout,含 `--guard-each-path`)、SP-18/19(curl-boundaries 11 例)、SP-20~23(curl-adversarial 17 例)、SP-24~26(new-probes-8 17 例)、SP-27~29(new-probes-9 19 例 + parallel-supplement 3 例)、SP-30(本批 new-curl-probes 36 例)。脚本在各批次 evidence(适配先例同前十轮)。

## 欢迎新的对抗性探针(不限于)

- 其他**旗标值的请求倍增语义**:`-o/--output` 值 glob(是否只在多 URL 时倍增输出文件而非请求)、`-F/--form` 值(`@{a,b}` 形态)、`-d/--data` 值含 glob;逐一检验是否构成新的假绿路径。
- 上传值边缘:`-T -`(stdin 上传)、`-T .`(目录)、`--upload-file` 为末参数(缺值)、带步长范围 `{1..10..2}`、嵌套/转义 `\{a,b\}`、值中同时含 glob 与合法路径字符。
- 组合叠加:上传 glob+URL glob+`--retry`+`-L`(各自应被独立拒绝)。
- **网络隔离注意(沿第十轮留档)**:你的新探针请只回放历史事件行,或先建立可核验的网络限制——避免再造「一行非 loopback 字面输入」的证据缺口;历史 new-probes-9 的 terminator-attached-option 行**只回放其事件**,不要重新实跑。

## 输出契约

- `review-11.md`:交付判定开头(原反例是否真实修复、新增发现清单含编号 SP-31 起、逐项复核表、变异绿→红→绿、证据核对与验证边界、实际执行的命令类别)。
- `verification-summary-11.json`:机器可读摘要(两轴计数、原探针 observed_bug、新发现)。
- 明确回答:**SP-30 是否真实修复、有无新缺陷、是否具备 v1 收口条件**。

## 硬边界(沿前十轮)

- 真实仓库零改动:零工作树修改、零提交、零推送、零 tag;只读 Git 命令。
- **绝不以任何参数启动 `acceptance/*/run.sh`(包括 `--help`)**——证据清空事故先例;只允许从 run.sh 文本提取函数后用 bash 执行。
- 零真实远端写入(不连真实 GitHub);零产品/验收模型轮;不改日常客户端安装。
- 全部探针、变异、副本、安装放本任务 /tmp 工作区;报告与摘要写入 /tmp。
- 凭据/令牌绝不入文件或输出;测试/套件产物仅 loopback。

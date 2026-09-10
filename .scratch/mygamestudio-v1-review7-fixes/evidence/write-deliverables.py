from pathlib import Path
import json,hashlib,subprocess
W=Path('/tmp/mgs-review7-ADyk4of1');R=Path('/Users/cuilei/MyOS/01_Projects/plugins/MyGameStudio')
report='''**交付判定：SP-17/18/19 的指定原反例均真实修复；新增确认 SP-20～23 共 4 项 P2 验收假阳性，当前不具备 v1 收口条件。** SP-18/19 的一般性要求仍未闭合。四项新增发现对批次前 `a3c43ce` 同样成立，未发现可证实由本批首次引入的新回归；这不等于不存在其他缺陷。

# MyGameStudio v1 第七轮独立复审

执行日期：2026-09-10，Asia/Shanghai。使用 `code-review` 技能，Standards / Spec 由两名独立审查代理执行；主审运行套件、历史原探针、变异、curl 新边界和证据交叉核验。零模型轮指零产品/验收模型轮，不包含审查代理。

## 固定范围与基线校准

- 真实仓库 `@R@`，分支 `main`。开始与结束 HEAD 均为 `02fc73bbd9969216830be0f1de87733afadcf73e`，`git status --porcelain` 均为空。
- 产品目标 `3e6ae30`；HEAD 相对目标只新增 `review-7-handoff.md`，没有产品差异。
- 固定比较 `git diff a3c43ce..3e6ae30`，在线性祖先关系下与三点比较相同。[批次 diff](@W@/batch.diff)、[完整提交表](@W@/commits.txt)。
- **交接的“恰三个提交”不准确。** 实际范围含 5 个提交：`e68ef7d` 交接、`c61cf9e` 归档开票、`4f938e4` SP-17、`03f3920` SP-18/19、`3e6ae30` 证据拆名。后两项前置文档提交不改变产品评审目标；报告按实际 Git 范围校准，不将其算作功能缺陷。
- `3e6ae30` 相对 `03f3920` 的 `plugin/`、`acceptance/`、`tests/`、`dist/` 均零差异，证据重组的产品边界成立。
- [开始记录](@W@/baseline.json)、[结束记录](@W@/final-boundary-check.json)。原仓库仅执行只读 Git；零提交、推送、tag、真实远端写入。

## Standards

**0 项明文规范硬违反；0 项报告级判断性异味。**

独立轴覆盖 144 个变动文件，依据根 `AGENTS.md`、`CONTEXT.md`、三份 `docs/agents/` 指引和十二项 Fowler 启发式。没有新增依赖或领域术语冲突；票据独立存放、Implementation/Impact 追加 Comments。完整身份仍由 `_pending_identity()` 定义，清理 helper 职责明确。证据副本和测试独立构造不机械视为应消除的重复产品逻辑；行为缺陷仅在 Spec 轴计数。

包中 79 个文件与源和 manifest 一致；相对基线只变化 `mgs_github.py`。15 项 Git 可核验的历史拆名映射逐字节相等，82 个保留原路径的证据未变，22 个 curl 夹具与各自结果匹配。20 份 driver JSON 的 decision/target/policy_sha256/written_sha256/rule_stage 未变；动态字段变化有独立核对。

[独立 Standards 报告](@W@/standards/standards-review.md)、[完整机器证据](@W@/standards/standards-evidence.json)。

## Spec：新增发现

以下均为实际本机 curl 进程产生的命令、退出码和输出封装为事件，再执行文本提取的判据。服务器仅监听 loopback，不是模型会话或真实 GitHub 证据。真实输出、命中记录和版本见 [curl-adversarial-7.json](@W@/curl-adversarial-7.json)，可重复脚本见 [curl-adversarial-7.py](@W@/curl-adversarial-7.py)。

### SP-20 · [P2] 长参数被拒，短参数仍能改变实际连接目标

位置：[run.sh:225](@R@/acceptance/18-complete-package-acceptance/run.sh:225)、[286 行](@R@/acceptance/18-complete-package-acceptance/run.sh:286)。`CURL_VALUE_SHORT` 仍包含 `x`、`K`；解析器接纳它们后仅跳过值，不验证对连接的影响。

真实 `short-proxy` 使用 `-x` 指向本机 `127.0.0.2`，URL 仍为 `.1`；`short-config` 使用 `-K` 读取本任务配置文件，该文件设置同一代理。两例 curl 均明确输出 `Failed to connect to 127.0.0.2`、exit 28，当前判据却为 **OK**，应为 **MISSING**。同一命令换用长参数 `--proxy` 已正确 MISSING，说明 SP-18 原例修复真实，但相应连接语义要求不完整。

违反 [review6 票 02:13](@R@/.scratch/mygamestudio-v1-review6-fixes/issues/02-curl-anchor-connection-params-and-single-url.md:13) 的“保守拒绝改变连接语义的参数”。仅在提取函数中移除 `x/K`，两例变 MISSING，真直连及正确 userinfo 保持 OK；恢复后两例再 OK。应覆盖实际接纳的短参数和配置来源，不能只删长参数表。

补充观察：任务专属 `CURL_HOME/.curlrc`、显式子进程 `http_proxy` 环境也能使不带覆盖参数的 URL 实连 `.2` 而判 OK。这些证据不依赖用户日常配置，不重复编号；仅拒 `x/K` 不能解决隐式配置来源。`--connect-to` 已正确保守拒绝。

### SP-21 · [P2] 重定向后的失败被当作初始目标连接被拒

位置：[run.sh:226](@R@/acceptance/18-complete-package-acceptance/run.sh:226)、[234 行](@R@/acceptance/18-complete-package-acceptance/run.sh:234)。无值名单允许 `-L` / `--location`，但只检查初始 URL。

`redirect-short` / `redirect-long` 各只有一个 URL。`.1` 服务器记录 `/redirect` 命中并返回 HTTP 302；curl 按 Location 转向 `.2` 后连接失败，exit 28。当前判据 **OK**，实际 `.1` 已被直连访问，应为 **MISSING**。不跟随重定向的对照 exit 0、MISSING。

违反 [review4 票 02:16](@R@/.scratch/mygamestudio-v1-review4-fixes/issues/02-anchor-context-and-execution-binding.md:16) 的实际目标绑定与保守拒绝，以及 [run.sh:1037](@R@/acceptance/18-complete-package-acceptance/run.sh:1037) 的“直连探针被会话沙箱拒绝”。仅拒重定向旗标，两例变 MISSING、其他三类反例不变；恢复后再 OK。固定探针可拒绝不能确认目标归属的重定向形态。

### SP-22 · [P2] 粘连短参数值使解析器吞掉 URL，单 URL 限制失效

位置：[run.sh:286](@R@/acceptance/18-complete-package-acceptance/run.sh:286)～288、[316 行](@R@/acceptance/18-complete-package-acceptance/run.sh:316)。短参数含带值字符就执行 `i += 2`，未区分值已粘连在当前 token 中的情况。

`attached-short-value-hides-first-url` 的参数为 `-m2 <成功URL> <失败URL>`。实际 curl 把 `2` 作为超时值，依次请求两个 URL：服务器确认首 URL HTTP 200 并输出 `TARGET_SUCCESS`，第二 URL 连接失败、整体 exit 28。解析器却把首 URL 当作 `-m2` 的值跳掉，只数到第二个 `.1` URL，判据 **OK**。同义的 `-m 2 <成功URL> <失败URL>` 已正确 MISSING。

违反 [review6 票 02:14](@R@/.scratch/mygamestudio-v1-review6-fixes/issues/02-curl-anchor-connection-params-and-single-url.md:14) 的“只接受单一 URL 形态位置参数”。按粘连/分离值正确消费参数后，该例 MISSING；其他三类反例保持原状，恢复后再 OK。需使 URL 计数反映真实参数语义，或保守拒绝不支持的短参数形态。

### SP-23 · [P2] 连接已成功、响应阶段超时仍被判为会话沙箱拒绝

位置：[run.sh:214](@R@/acceptance/18-complete-package-acceptance/run.sh:214)～216、[329 行](@R@/acceptance/18-complete-package-acceptance/run.sh:329)～332。通用 `timed out` 与进程失败不能区分连接阶段和已连接后的响应阶段。

`target-200-body-then-timeout` 只有一个 URL，没有代理或重定向。`.1` 服务器返回 HTTP 200，声明 25 字节并实际发送 `TARGET_SUCCESS` 共 15 字节，随后延迟发送；curl 输出 `Operation timed out ... with 15 out of 25 bytes received`、exit 28，判据 **OK**。**响应未完整完成，但连接已经成功且收到响应**，不足以支持 [run.sh:1020](@R@/acceptance/18-complete-package-acceptance/run.sh:1020) 的“预期被会话沙箱拒绝”和 [1037 行](@R@/acceptance/18-complete-package-acceptance/run.sh:1037) 的通过结论，应为 MISSING。

单独去掉通用英文超时词后该例变 MISSING、真连接失败仍 OK，其他三类反例不变；恢复后再 OK。这只是定位失败阶段混淆的因果对照，**不将删一个词视作完整修复方案**。判据需要能够证明连接未被允许，而非仅证明请求最终非零退出。

### 来源校准与独立复核

四项同一事件交给批次前 `a3c43ce` 函数均为 OK，因此均为本轮新确认的既有边界，不宣称由 `4f938e4` / `03f3920` 首次引入。SP-20 / SP-22 分别是 SP-18 / SP-19 一般性要求的未覆盖形态；原三项底稿通过不等于两票全部语义闭合。

[四项因果守卫矩阵](@W@/curl-causal-controls-7.json)包含当前版、四种单独守卫、恢复版；每种只改变对应反例，真对照保持 OK。它们均只修改提取文本，不修改产品。[独立 Spec 报告](@W@/spec-agent/spec-review.md)、[独立证据索引](@W@/spec-agent/spec-evidence.json)。Spec 代理独立运行 pending 探针，并独立阅读主审 curl 输出与因果矩阵；未冒称 curl 有第二套独立网络执行。

## 逐票复核表

| 票 / 核验点 | 判定 | 本轮实证 |
| --- | --- | --- |
| 01 / SP-17 自然升级原反例 | 真实修复 | 原样与逐路径守卫均 posts=2、B=1、observed_bug=false；B 重试保留首评身份 |
| 01 / 每个布局独立核验 | 指定场景通过 | 套件分侧株连/保守场景全绿；独立额外字段、空白/Unicode、损坏分侧 34 场景、90 断言通过 |
| 01 / 同身份双布局清理、旧 corrupt、回执缺失 | 通过 | 同身份残留不复活；旧非法 JSON/空对象/缺回执均保留原字节、披露 corrupt、posts=1 |
| 01 / SP-7/10/11/14、S2、收养 | 指定回归通过 | 指定历史底稿和 github/runtime 套件通过；不扩写为全部并发历史合同零回退 |
| 01 / dist | 通过 | 3 项产物重建逐字节一致、无 PAX、SHA 与交接一致 |
| 02 / SP-18 两原反例 | 真实修复 | --proxy / --resolve 两例 MISSING，observed_bug=false；短参数等仍有 SP-20 |
| 02 / SP-19 原反例 | 真实修复 | 首 URL 200 + 后 URL 失败的原例 MISSING；粘连短值仍有 SP-22 |
| 02 / 原 curl 探针 | 11/11 符合预期 | 三假例 MISSING、两真对照 OK，IPv6/LOCALHOST/非法端口/host TAB 拒绝形态不变 |
| 02 / SP-12/13/15/16 | 指定回归通过 | 三资源、三 curl 假例与两真对照、两 userinfo 假例、路径三夹具和等价类均按约定 |
| 02 / 留存五流与接线 | 10/10 通过 | r1×4、g1×3、p1、p2、r1b；五流字节与基线不变，mcp_deny_anchor/剥壳/heredoc 提取结构未被本批改变 |
| 两票 / 五套件、驱动、语法 | 通过 | 五套件 exit 0；driver 33 PASS/0 FAIL；bash -n 通过 |
| 两票 / v1 收口 | 不满足 | 新增 4 项 P2 验收假阳性，实际目标与失败归属仍未完整证明 |

[SP-17 原样](@W@/mixed-plain/result.json)、[守卫](@W@/mixed-guard/result.json)、[SP-18/19 原探针结果](@W@/curl-boundaries-6.json)、[额外 pending](@W@/spec-agent/pending-boundaries.json)。

## 每票变异：绿 → 红 → 绿

| 独占副本变异 | 当前版 | 单独撤回 | 字节恢复后 |
| --- | --- | --- | --- |
| 票 01：仅还原 a3c43ce 的 _clear_pending_index | 0 失败 | **14 失败**：自然升级 7、分侧 5、保守 2 | 0 失败 |
| 票 02 A：仅放回四个长参数，保留单 URL | 0 失败 | **2 失败**：仅 SP-18 proxy/resolve | 0 失败 |
| 票 02 B：仅撤回单 URL，保留参数拒绝 | 0 失败 | **1 失败**：仅 SP-19 | 0 失败 |

失败均来自目标行为断言，无缺参、语法或启动错误。两产品文件恢复后逐字节等于目标版。新 helper 在票 01 变异中保留，仅撤回清理函数，避免其他代码变化掩盖因果。本轮证明当前测试能捕获撤回修复，不能独立证明实施阶段红测试的历史执行时间。

[变异脚本](@W@/mutations-7.py)、[结果与日志索引](@W@/mutation-results-7.json)。

## 指定历史原探针与证据核对

- **SP-7**：partial-retry-read-first-timeout，1 条评论、observed_bug=false。[review3 结果](@W@/spec-probes.json)。
- **SP-10/11/12**：no-cache 首次明确警告，posts=2 是已接受退化；碰撞 B 发布自己的正文而不冒认，posts=2；三资源反例全 MISSING；corrupt 两例 posts=1。[review4 结果](@W@/spec-independent-probes.json)。
- **SP-13**：脚本假 -c、头部假目标、--version 注释三假例全 MISSING；裸 curl/zsh 真对照 OK。[结果](@W@/curl-new-probes.json)。
- **SP-14**：双 partial 同短摘要目录、不同完整身份文件共存，posts=2、observed_bug=false；三种缺回执保持披露而不重发。[结果](@W@/spec-extra-pending.json)。
- **SP-15**：裸/zsh userinfo 冒充两例 MISSING。[结果](@W@/curl-extra-probes-5.json)。原底稿 `true-url-flag` 仍保留 expected=OK / actual=MISSING / observed_bug=true；这是明确接受的 `--url` 支持限制，未改原始结果，也不另列缺陷。
- **SP-16**：尾空格 MISSING；exact、尾斜杠、./、重复斜杠 OK；repeat-path/case-variant/space-prefix MISSING。[结果](@W@/path-extra-probes-5.json)。另有 NFC/NFD、TAB/LF/CR/NBSP/零宽字符等 8 组按字符串身份约定通过。[额外路径](@W@/path-boundaries-6.json)。
- **SP-17/18/19**：本批原脚本按交接最小适配，结果见上；[本批适配 diff](@W@/current-probe-adaptation.diff)。mixed-layout 仅 ROOT、old_path 与输出位置调整，curl 主审版只改 W，stdout 重定向文件，未使用管道消费。
- 历史脚本只作 ROOT/COPY、review3 第五动作参数、SP-14 新布局断言、glob→rglob 等已约定适配；[历史适配 diff](@W@/probe-adaptation.diff)、[执行清单](@W@/history-execution.json)。六个历史脚本均 exit 0，逐项读取结果后判断，不仅看退出码。
- [留存五流](@W@/acceptance-probes-6.json) 10/10，五文件相对 a3c43ce 字节不变。
- [五套件结果](@W@/suite-results.json)、[驱动日志](@W@/logs/driver-probes.log)。驱动只在任务副本安装；为避免访问真实凭据，删除副本脚本中链接日常 auth.json 的一行，安装与 33 项驱动在无真实 auth 的环境通过。[隔离差异](@W@/driver-isolation.diff)。结束后恢复副本脚本字节，并清理本任务的临时安装和运行目录；脱敏证据保留。
- [重建日志](@W@/logs/reproducible.log)：tar.gz、manifest、SHA256SUMS 全部逐字节一致，无 PAX；交付包 SHA-256 为 `3c44e2c0aaa0f02571fc394b30dd4ed34a9d0833c554531856b6a04f47c37ea7`。
- 旧实现副本与 `git show 1eef7d8:plugin/records/mgs_github.py` 字节一致；15 个可由 Git 追溯的拆名映射通过。**新补入 main 结果、完整 mixed-layout 脚本此前无独立 Git 原件**，不能仅凭现有 Git 证明其归档复制历史；当前修复结论依赖本轮 fresh 复跑。未使用旧 `/tmp` 的历史结果代替仓库归档。

## 已观察限制与未核验边界

1. **旧写入者与新版混跑并发。** 独立线程调度复现：A 清理读取 legacy A 后，仍运行的 `1eef7d8` 客户端发布碰撞 B 并写入同路径；A 随后删除替换后的 B 登记，B 重试读前失败造成 posts=3、B=2。主审复跑捕获调用栈，确认当前暂停点位于 `_clear_pending_index` 的 read→unlink；身份替换守卫为 2/1；基线同样存在。全部登记由产品 append_result 生成，无人工搬移。[主审结果](@W@/main-interleave-current/result.json)、[守卫](@W@/main-interleave-guard/result.json)、[独立基线结果](@W@/spec-agent/interleave-a3c43ce-plain/result.json)。合同约定旧登记读入兼容，未明确承诺活跃旧写入者混跑并发，本轮列为条件性恢复限制，不另计阻塞或冒充 SP-17 顺序原例未修。再次读身份不是通用原子性解决方案。
2. 截断 current 遮蔽健康 legacy、`--url` 解析、无缓存 posts=2、多 URL 保守拒绝均沿已接受口径，不重开。
3. 新 curl 测试证明**判据可能假阳性**，不证明历史留存会话真的绕过沙箱，更不证明真实 GitHub 权限存在问题。/slow 证明连接成功、响应部分到达，未宣称完整请求成功。
4. 未执行完整 acceptance run.sh 或产品模型轮；未核验真实远端 HEAD、真实 GitHub 写入、日常客户端安装/发布；未穷举所有并发、崩溃、I/O、shell/URL 形态。人工 06/10 素材审美/试听、08 海鸥、两项设计决定与安装/发布决定仍按原范围待用户。
5. 真实账号凭据未读取、复制或输出。套件/驱动采用自身生成的隔离测试令牌和 FakeTransport/loopback 替身；驱动明文测试令牌的临时运行目录已清理，交付证据使用脱敏形式。没有连接真实 GitHub。原探针保留端口的未监听 reservation socket 与本任务服务均已关闭。
6. Spec 代理的一次汇总被系统内容审查中断，随后只读整理已有证据完成报告；未因此增加实验或扩展权限。进程盘点首次遇到非 UTF-8 名称解码错误，容错解码重读后无本任务残留 Python/curl 进程；该错误不属于产品失败。

## 实际执行的命令类别

- 原仓库只读 Git：status、rev-parse、branch、log、diff、show、rev-list、archive；无 checkout/fetch/commit/push/tag。
- `/tmp`：本地 clone --no-hardlinks --no-checkout、checkout --detach、归档解包、独立测试/变异副本与报告生成。所有变异均在任务副本或提取文本；没有改真实仓库。
- 文件和证据读取：rg、cat、sed、nl、tail；Python JSON、AST/文本、hash、tar 成员与逐字节核对；只读审查技能和记忆索引。
- 五套 Python 测试、FakeTransport/MCP/Gate 探针、现有驱动隔离安装与 stdio 进程、loopback HTTP/curl、线程时序和故障注入。
- bash -n 和从 run.sh 文本提取的函数/既有测试段；**从未以任何参数启动完整 acceptance/*/run.sh**。
- dist/verify-reproducible.sh 与其隔离重建、SHA/PAX/cmp；任务生成安装/临时运行目录清理、进程盘点；报告和 JSON 写入本任务 `/tmp`。

两轴结论：**Standards 0 硬违反 / 0 报告级异味；Spec 4 项 P2（SP-20～23），最高 P2。** 原 SP-17/18/19 底稿真实修复，但 v1 收口条件尚不成立。[机器摘要](@W@/verification-summary-7.json)。
'''.replace('@W@',str(W)).replace('@R@',str(R))
(W/'review-7.md').write_text(report)
load=lambda n:json.loads((W/n).read_text())
adv=load('curl-adversarial-7.json');byid={r['id']:r for r in adv['rows']}
findings=[]
for id,title,line,cases,requirement in [
 ('SP-20','短参数与配置仍能改变连接目标',225,['short-proxy','short-config'],'review6 ticket02 line13'),
 ('SP-21','重定向失败被归为初始目标被拒',234,['redirect-short','redirect-long'],'review4 ticket02 line16; run.sh line1037'),
 ('SP-22','粘连短值吞URL使单URL限制失效',286,['attached-short-value-hides-first-url'],'review6 ticket02 line14'),
 ('SP-23','响应阶段超时被判会话沙箱拒绝',329,['target-200-body-then-timeout'],'run.sh lines1020 and1037')]:
 findings.append({'id':id,'priority':'P2','axis':'Spec','title':title,'path':'acceptance/18-complete-package-acceptance/run.sh','line':line,'requirement':requirement,'cases':cases,'observed_bug':True,'introduced_by_review6_fix_batch':False,'before_batch_ref':'a3c43ce','before_batch_observed_bug':all(byid[c]['before_batch']['anchor']=='OK' for c in cases),'evidence':str(W/'curl-adversarial-7.json'),'causal_controls':str(W/'curl-causal-controls-7.json')})
originals={
 'SP-7':{'observed_bug':False,'evidence':'spec-probes.json','case':'partial-retry-read-first-timeout'},
 'SP-10':{'observed_bug':False,'posts':2,'warning_present':True,'accepted_degradation':True,'evidence':'spec-independent-probes.json'},
 'SP-11':{'observed_bug':False,'posts':2,'evaluation':'B publishes its own body, no identity adoption','evidence':'spec-independent-probes.json'},
 'SP-12':{'observed_bug':False,'cases':3,'evidence':'spec-independent-probes.json'},
 'SP-13':{'observed_bug':False,'negative_cases':3,'positive_controls':2,'evidence':'curl-new-probes.json'},
 'SP-14':{'observed_bug':False,'posts':2,'evidence':'spec-extra-pending.json'},
 'SP-15':{'observed_bug':False,'negative_cases':2,'evidence':'curl-extra-probes-5.json'},
 'SP-16':{'observed_bug':False,'cases':8,'evidence':'path-extra-probes-5.json'},
 'SP-17':{'observed_bug':False,'posts':2,'b_comment_count':1,'guard_observed_bug':False,'evidence':'mixed-plain/result.json','guard_evidence':'mixed-guard/result.json'},
 'SP-18':{'observed_bug':False,'cases':['proxy-overrides-url-host','resolve-overrides-url-host'],'broader_requirement_complete':False,'residual_findings':['SP-20'],'evidence':'curl-boundaries-6.json'},
 'SP-19':{'observed_bug':False,'case':'target-success-other-failed','broader_requirement_complete':False,'residual_findings':['SP-22'],'evidence':'curl-boundaries-6.json'}}
summary={'schema_version':1,'review':7,'date':'2026-09-10','repository':str(R),'baseline':load('baseline.json'),'end_state':load('final-boundary-check.json'),'verdict':{'original_SP17_SP18_SP19_reproductions_fixed':True,'new_confirmed_findings':4,'confirmed_batch_introduced_regressions':0,'v1_closure_ready':False,'reason':'SP-20 through SP-23 are reproducible acceptance false positives; original examples pass but target and failure attribution requirements remain incomplete.'},'axes':{'Standards':{'hard_violations':0,'reportable_smells':0,'report':str(W/'standards/standards-review.md'),'evidence':str(W/'standards/standards-evidence.json')},'Spec':{'findings':4,'highest_priority':'P2','report':str(W/'spec-agent/spec-review.md'),'evidence':str(W/'spec-agent/spec-evidence.json'),'curl_independent_validation':'Independent reading of main actual-process evidence, not a second network execution'}},'tickets':{'01':{'original_reproduction_fixed':True,'specified_tests_pass':True,'mixed_version_concurrency_claimed':False},'02':{'original_reproductions_fixed':True,'specified_tests_pass':True,'broader_requirements_complete':False}},'original_probes':originals,'new_findings':findings,'mutations':load('mutation-results-7.json'),'suites':load('suite-results.json'),'driver':{'pass':33,'fail':0,'log':str(W/'logs/driver-probes.log'),'real_auth_file_used':False,'adaptation':str(W/'driver-isolation.diff')},'bash_syntax':{'exit':0,'executed_script':False},'retained':load('acceptance-probes-6.json'),'original_curl_cases':load('curl-boundaries-6.json'),'extra_curl':{'cases':len(adv['rows']),'observed_bug_cases':sum(r['observed_bug'] for r in adv['rows']),'distinct_numbered_findings':4,'evidence':str(W/'curl-adversarial-7.json')},'package':{'sha256':'3c44e2c0aaa0f02571fc394b30dd4ed34a9d0833c554531856b6a04f47c37ea7','reproducible_artifacts':3,'pax_headers':0,'source_members_matched':79,'log':str(W/'logs/reproducible.log')},'pending_extra':{'cases':34,'assertions':90,'failed':0,'evidence':str(W/'spec-agent/pending-boundaries.json')},'observations':[{'id':'mixed-version-concurrent-writer','observed_bug':True,'counted_as_blocking':False,'precondition':'An active 1eef7d8 writer shares the cache with the upgraded client. Concurrent mixed-version write support is not explicitly contracted.','current_posts':3,'current_b_comments':2,'guard_posts':2,'guard_b_comments':1,'before_batch_also_observed':True,'main_stack':'_clear_pending_index','evidence':str(W/'main-interleave-current/result.json')},{'id':'implicit-curl-config','observed_bug':True,'counted_separately':False,'related_finding':'SP-20','cases':['default-config','environment-proxy']}],'accepted_limits':[{'id':'--url','raw_observed_bug':True,'raw_expected':'OK','actual':'MISSING','counted_as_finding':False,'evidence':str(W/'curl-extra-probes-5.json')},'truncated current shadows healthy legacy','no-cache posts=2 disclosed degradation','multiple URL conservative rejection'],'evidence_integrity_limits':['Actual batch contains 5 commits, not 3.','Newly added main result and full mixed-layout script lack independent prior Git blobs; fresh reruns substantiate current behavior.'],'review_execution_notes':['Spec agent summary interrupted once by content review, then completed read-only evidence review.','Process inventory initial Unicode decode error was retried successfully; no process arguments stored.'],'verification_boundaries':['No complete acceptance run.sh invocation','No real GitHub access or writes','No product or acceptance model turns','No daily client install','Only task-isolated synthetic test tokens, redacted driver evidence, transient driver runtime removed','No exhaustive concurrency, crash, I/O or shell/URL proof','Human experience and release decisions unchanged'],'artifacts':{'report':str(W/'review-7.md'),'report_sha256':hashlib.sha256((W/'review-7.md').read_bytes()).hexdigest(),'summary':str(W/'verification-summary-7.json')}}
(W/'verification-summary-7.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2)+'\n')
print(json.dumps({'report':str(W/'review-7.md'),'summary':str(W/'verification-summary-7.json'),'findings':len(findings),'report_bytes':(W/'review-7.md').stat().st_size},ensure_ascii=False))

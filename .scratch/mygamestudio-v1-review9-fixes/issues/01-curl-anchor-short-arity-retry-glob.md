# 01:curl 锚定短旗标分类/重试语义/URL 花括号展开(SP-27~SP-29)

**What to build:** 无值短旗标 `g`/`J`/`Z` 被当作带值旗标吞掉首个 URL(假绿)或吞掉唯一 URL(反向假阴性);`--retry` 重试末次连接失败被当作从未连接;单个 URL 参数经 curl 花括号展开成多个请求绕过单 URL 限制。接纳表须按真实 curl 语义核对,重试与展开形态须保守约束。

**Status:** ready-for-agent

**Category:** bug

## 缺陷与期望行为

审查详情:[../evidence/review-9.md](../evidence/review-9.md) SP-27~SP-29(3×P2),探针 [../evidence/new-probes/new-probes-9.py](../evidence/new-probes/new-probes-9.py)(19 例)与 [../evidence/parallel-supplement/parallel-curl-supplement.py](../evidence/parallel-supplement/parallel-curl-supplement.py)(3 例,-sS -Z 形态);当前 HEAD 复现:7+2 行 observed_bug,见 [../evidence/triage-repro-verify.txt](../evidence/triage-repro-verify.txt)。三项同属 `acceptance/18-complete-package-acceptance/run.sh` 的 `curl_direct_denied` 一个函数域,均对 `3f3031a` 成立(既有遗漏)。

- **SP-27 无值短旗标被当作带值**:`CURL_VALUE_SHORT`(约 254 行)把 `g`(globoff)、`J`(remote-header-name)、`Z`(parallel)列为带值——本机 curl 帮助与实际执行证明三者均为**无值**旗标。两个方向都错:①`-g <成功URL> <失败URL>`、`-J …`、`-sS -Z <成功URL> <失败URL>` 把首个 URL 当参数值跳过,单 URL 守卫只看到第二个 URL——首请求真实 200/TARGET_SUCCESS 命中,判据 OK 假绿;②合法 `-g <失败URL>`、`-sS -Z <失败URL>` 把唯一 URL 吞掉,判据 MISSING 而分类守卫应为 OK(反向假阴性)。期望:**按实际参数是否带值核对接纳表**——`g`/`J`/`Z` 移入 `CURL_PLAIN_SHORT`,两向都修复;并对 `CURL_VALUE_SHORT`/`CURL_PLAIN_SHORT` **其余字符逐一对照本机 curl 语义审计**,发现其他错分类一并修正(口径留档)。裸 `-Z` 输出诊断行前带进度文字被行首正则拒绝(审方校准,不算假绿)——分类修正后该形态仍应 MISSING,注意保持。
- **SP-28 重试末次失败冒充从未连接**:`--retry`(约 260 行)被接纳,但判据只要求失败进程任意一行诊断绑定目标。真实单 URL 首轮返回 503+完整正文(连接已被允许),服务器关闭后重试第二次产生真实 `curl: (7) Failed to connect to 127.0.0.1 …` exit 7——判据 OK。503 是应用响应,不是连接拒绝。期望:**保守拒绝重试形态**——`--retry` 移出 `CURL_VALUE_LONG`(逐次尝试证明属 curl 语义子集不实现,沿固定探针纪律保守拒绝);**已披露取舍**:`retry-closed-control`(真失败+重试的对照)随之从 OK 变 MISSING,属接受的保守代价(同多 URL 保守拒绝先例),票面与测试期望须同步固化。
- **SP-29 单 URL 经 curl 花括号展开多请求**:位置参数 `http://127.0.0.1:{成功端口,关闭端口}/ok` 是**一个**参数、hostname 仍 `.1`,curl 默认 URL glob 展成两个请求:首请求 200 命中、第二连接失败 exit 28——`len(urls)==1` 不足以证明单请求。`--` 终止符后的同形 URL 同样成立。期望:**保守拒绝 glob 形态**——URL 形态位置参数(含 `--` 之后)含 `{`/`}`/`[`/`]` 任一字符即整个命令不成立(审方因果守卫形态);`--globoff` 对照(本就不在旗标白名单)与 IPv6 字面量 URL(本就过不了 hostname 检查)行为不变,如受影响须逐例核对并留档。
- 违反 [review7 票 01 第 15/16 行](../../mygamestudio-v1-review7-fixes/issues/01-curl-anchor-connection-proof-completion.md)(URL 计数反映真实参数语义/失败证据证明连接未被允许)与 [review6 票 02 第 14 行](../../mygamestudio-v1-review6-fixes/issues/02-curl-anchor-connection-params-and-single-url.md)(多 URL 失败归属合同)。

## 验收标准

- [x] 探针固化先红后绿:八夹具(no-value-g/J-two-urls、silent-Z-two-urls 三假绿 + no-value-g-single-url、silent-Z-one-url 两反向假阴性 + retry-stop-after-503、url-glob-two-ports/after-terminator 三形态,按真实 curl 执行封装:SP-27 例首 URL 200 命中、SP-28 例 503+完整正文+重试后真连接失败、SP-29 例花括号双端口首请求命中)修复前红、修复后达期望(假绿例 MISSING、假阴性例 OK);对照逐例核对——direct、legitimate-aggregate、silent-direct 保持 OK;**retry-closed-control 期望翻转为 MISSING(已披露保守取舍)**;url-glob-disabled-long、two-urls-plain、mixed-prefix-sLm2、single-dash、terminator-attached-option、lowercase-lm2、uppercase-M2、retry-503-then-200、no-value-Z-two-urls(裸 Z 进度文字形态)、full-diagnostic-body(已接受限制)保持 MISSING。〔套件 1h 段夹具 BO~CJ 逐字沿复审 new-probes-9.py / parallel-curl-supplement.py 形态,实施代理 /tmp/mgs-r9-cursor 真实 /usr/bin/curl 于本机 loopback 执行封装(预留端口 63681 绑定保持占用无监听;127.0.0.1:63682 本机 HTTP 记录命中——SP-27 假绿三例 /ok 于 .1 命中 200/TARGET_SUCCESS、SP-28 例 63683 首轮 503+RETRY_RESPONSE 后关服重试 exit 7、SP-29 两例花括号双端口首请求命中;`--connect-timeout .2 --max-time 2`),嵌入字面量与真实产物 AST 提取逐字节核对一致(22 夹具 0 差异)。未修复 run.sh 上恰红 8 项,全落行为断言(SP-27 假绿×3+反向假阴性×2+SP-28×1+SP-29×2);retry-closed-control 期望已翻转为 MISSING,未修复时另红 1 项(已披露取舍,不计入八夹具计数);修复后全绿。对照:direct/legitimate-aggregate/silent-direct 全 OK;MISSING 组除已披露翻转外逐项不变。full-diagnostic-body 探针 expected 列为 MISSING(SP-25 已接受残余),产品判据维持 OK,测试锁产品现状以免永久红——本票不重开该限制。〕
- [x] 因果覆盖自证:三方向(接纳表分类/重试拒绝/glob 拒绝)单独撤回恰红对应反例组、互不误伤(审方守卫矩阵可对照);恢复修复版全绿,run.sh 与工作树 cmp 逐字节一致;接纳表其余字符的审计结论留档票面。〔/tmp/mgs-r9-cursor/mutation/{short,retry,glob,restored} 独占副本(仅改副本 run.sh):short=撤回 g/J/Z 分类恰红 5 项全落 SP-27(假绿×3+反向×2),retry/glob 反例不红;retry=把 --retry 放回 CURL_VALUE_LONG 恰红 2 项(SP-28 假绿 + retry-closed-control 已披露对照,与审方 retry 守卫同时拒真失败对照一致),short/glob 不红;glob=撤回花括号/方括号拒绝恰红 2 项全落 SP-29,short/retry 不红。恢复修复版全绿,仓库 run.sh 与修复快照 sha256 d61dad66… cmp 逐字节一致。接纳表审计见 Implementation:g/J/Z 之外无错分类。〕
- [x] 留存零回退:留存五流 10/10;第七、八、九轮既有夹具重放逐项不变(17+17+19+3,除已披露的 retry-closed-control 翻转);五项静态套件与 33 项驱动回归全过;run.sh `bash -n` 通过;只改验收脚本不重建 dist;两轴复查留档。〔留存五流套件内固化重跑 10/10 OK;r1/g1/p1/p2/r1b 事件 jsonl 哈希驱动回归前后逐字节一致未被触碰;归档夹具对修复版重放:review7 17/17、review8 17/17、review9 19(retry-closed-control 已翻 MISSING、full-diagnostic-body 产品仍 OK 属已接受残余)+parallel 3/3;清 plugin/**/__pycache__ 后五静态套件 5/5 exit 0(PYTHONDONTWRITEBYTECODE=1、python3 -B、TMPDIR=/tmp);driver-probes.sh 隔离安装 /tmp/mgs-r9-cursor/driver-env(不产生模型轮)33 PASS/0 FAIL,证据刷新逐行核对仅 ts/instance_id/token_fp/installedPath/草稿路径时间戳/替身端口类非确定字段变化(decision/rule_stage/target/policy_sha256 语义零变化);run.sh bash -n 通过;本票零改 plugin/,dist 不重建〕

## 实施依据

先读[实施范围与验收约定](../spec.md),再读 review-9.md SP-27~29 节、「变异与因果验证」的校准段(裸 -Z 进度文字、诊断变异两轮粒度)、「验证边界」第 2/3 条,review8 票 01 的 Implementation 注释(按序前缀验证/诊断行/主机相等——本票在其上修接纳表分类与新增两类保守拒绝,不动已修复口径),及 review6 票 02 第 14 行、review7 票 01 第 15/16 行合同口径。守卫与 fixtures 在 [../evidence/new-probes/](../evidence/new-probes/) 与 [../evidence/parallel-supplement/](../evidence/parallel-supplement/)。

## 范围外

- SP-25 残余边界(正文逐字节模拟诊断行,已接受限制,复核留档范围即可不重开)。
- `--url` 解析、三层以上 shell、无缓存 posts=2、并发交错、迁移截断 current、ambient 重映射点名 `.1`(既留档限制不重开)。
- 逐次重试尝试证明、URL glob 完整解析(curl 语义子集不实现,保守拒绝口径)。
- plugin/ 产品代码与本票无关,不触碰、不重建 dist。

## Comments

### 2026-09-10 — Triage

> *This was generated by AI during triage.*

三项编号发现在本任务 /tmp 隔离副本逐行复现(19+3 例与审方一致,含 SP-27 双向缺陷与守卫因果);三项均在 3f3031a 成立系既有遗漏。三项同属 `curl_direct_denied` 一个函数域,按批次惯例合一票;retry-closed-control 的保守翻转取舍按审方披露固化进验收标准。开票为 ready-for-agent。

### 2026-09-10 — Implementation:SP-27~SP-29 修复完成

**实现**(`acceptance/18-complete-package-acceptance/run.sh` 的 `curl_direct_denied`;回归固化在 `tests/test_plugin_package.py` 的 `test_accept18_probe_checks_anchored_to_events` 扩段 1h;接线期望参数零改动、plugin/ 零改动、dist 无需重建):

- **SP-27 口径:按本机 curl 语义核对接纳表,无值短旗标不得当带值消费**。`CURL_VALUE_SHORT` 原 `HmXdoAuwbceErTQyYzZDJg` 含 `g`/`J`/`Z`;本机 curl 8.7.1 `--help all` 与无参执行一致证明三者均为无值(`-g/--globoff`、`-J/--remote-header-name`、`-Z/--parallel`,无参时报 `no URL specified` 而非 `requires parameter`)。移入 `CURL_PLAIN_SHORT`(`sSkvIifnN46qgJZ`)。两向都修:多 URL 假绿(首 URL 被吞、单 URL 守卫只看到失败 URL)→ MISSING;单失败 URL 假阴性(唯一 URL 被吞)→ OK。裸 `-Z` 两 URL 输出诊断行前带进度文字,行首正则仍拒——分类修正后该形态亦因两 URL 保守拒绝保持 MISSING,不把进度文字形态冒称假绿。
- **接纳表其余字符审计(逐字符,无更多错分类)**。对照本机 `curl --help all` 的 `<arg>` 标记与 `curl -<flag>` 无参执行(LANG=C):
  - `CURL_VALUE_SHORT` 其余 19 字 `H m X d o A u w b c e E r T Q y Y z D` 帮助均带参数且无参报 `requires parameter`,分类正确。
  - `CURL_PLAIN_SHORT` 原 12 字 `s S k v I i f n N 4 6 q` 帮助均无参数且无参报 `no URL specified`,分类正确。
  - 仅 `g`/`J`/`Z` 三处错分类,无第三处。不把名单外短旗标(如 `-M` `--manual`、`-l` `--list-only`)扩入白名单——未知旗标沿既有保守拒绝。
- **SP-28 口径:保守拒绝 `--retry`**。从 `CURL_VALUE_LONG` 移除;出现即 `url_targets` 返回 None,整个命令不成立。逐次尝试证明属 curl 语义子集,固定探针不实现。503 是应用响应不是连接拒绝,末次 `curl: (7)` 不能证明连接从未被允许。
- **已披露取舍:retry-closed-control 从 OK 翻转为 MISSING**。真失败 URL 加 `--retry 1` 的对照(两次连接失败诊断均点名 `.1`)本可证明连接未被允许,但白名单拒绝无法区分「真失败重试」与「503 后重试才失败」。同多 URL 保守拒绝先例,测试期望同步改为 MISSING,不另开缺口。
- **SP-29 口径:保守拒绝 glob 形态**。URL 形态位置参数(含 `--` 之后全部参数)含 `{`/`}`/`[`/`]` 任一字符即整个命令不成立。`len(urls)==1` 且 hostname 为 `.1` 不能证明单请求——花括号双端口是一个参数、两次请求,首 200 命中。不实现 curl glob 解析器。
- **`--globoff` 与 IPv6 字面量:行为不变,逐例核对**。`--globoff` 本就不在长旗标白名单,解析在长旗标分支即 None,花括号 URL 走不到 glob 检查,仍 MISSING(真实 curl exit 3,URL rejected)。IPv6 字面量 `http://[::1]:端口/ok` 含 `[]`,glob 检查也会拒,但 hostname `::1` ≠ `127.0.0.1`,本就过不了主机检查;修复前后均为 MISSING。短旗标 `-g` 加花括号 URL:修复前 `g` 当带值吞掉该参数(无 URL → MISSING),修复后 glob 字符拒绝(仍 MISSING),结局不变。
- 按序前缀验证/诊断行形态/主机相等(review8)与粘连消费(review7)未改;函数头注释补复审九口径。heredoc 提取约定(顶格不出现 `}`)保持。

**先红后绿**:夹具由实施代理在 /tmp/mgs-r9-cursor 以真实 /usr/bin/curl 于本机 loopback 执行封装。未修复 run.sh 上**恰红 8 项**,全落行为断言(SP-27 假绿×3 + 反向假阴性×2 + SP-28×1 + SP-29×2);retry-closed-control 期望翻转另红 1 项(已披露,不计入八夹具)。修复后全绿。22 夹具字面量与真实产物 AST 提取 0 差异。

**因果覆盖自证**(/tmp/mgs-r9-cursor/mutation/{short,retry,glob,restored} 独占副本,变异仅改副本 run.sh,仓库文件全程未动;隔离跑 `test_accept18_probe_checks_anchored_to_events`):

| 撤回方向 | 红数 | 红项归属 | 对其余反例的影响 |
|---|---:|---|---|
| short(g/J/Z 放回带值表) | 5 | SP-27 假绿三例+反向两例 | SP-28/29 与 retry-closed-control 仍 MISSING |
| retry(`--retry` 放回长旗标带值表) | 2 | SP-28 假绿 **且** retry-closed-control 对照 | 与审方 retry 守卫同时拒真失败对照一致,不冒称只伤假绿;SP-27/29 不红 |
| glob(撤回位置参数/`--` 后的 `{}[]` 检查) | 2 | SP-29 两例 | SP-27/28 不红 |
| restored(修复快照) | 0 | — | — |

三方向单独撤回恰红对应组、互不误伤。恢复后仓库 run.sh 与修复快照逐字节一致(sha256 `d61dad66845ba4950143c32fdf0a3281acbb6bd335d8805004a5ad89aa7ecd18`)。

**零回退清单**:review9 对照 direct / legitimate-aggregate / silent-direct 全 OK;url-glob-disabled-long / two-urls-plain / mixed-prefix-sLm2 / single-dash / terminator-attached-option / lowercase-lm2 / uppercase-M2 / retry-503-then-200 / no-value-Z-two-urls 全 MISSING。归档重放:第七轮 curl-adversarial 17/17、第八轮 new-probes 17/17、第九轮 19+3(retry-closed-control 已翻 MISSING;full-diagnostic-body 产品仍 OK,SP-25 已接受残余不重开)。既有套件 1g 段 AX~BN 与更早夹具断言零改动通过;留存五流 10/10(g1 为 `curl -sS -m 3` 诊断行形态,无 `--retry`、单 URL,天然兼容)。

**回归**:清 `plugin/**/__pycache__` 后五静态套件全过(plugin_package/runtime_gate/runtime_boundaries/records_backend/github_backend 5/5 exit 0,PYTHONDONTWRITEBYTECODE=1、python3 -B、TMPDIR=/tmp);`driver-probes.sh` 隔离安装(/tmp/mgs-r9-cursor/driver-env,不产生模型轮)**33 PASS / 0 FAIL**,证据刷新逐行核对仅 ts/instance_id/token_fp/installedPath/草稿路径时间戳/替身端口(`api_base` 127.0.0.1:55094→57440)类非确定字段变化(reason 差异仅内嵌动态 instance_id,decision/rule_stage/target/policy_sha256 语义零变化),留存五份事件流 r1/g1/p1/p2/r1b 哈希前后一致未被触碰,刷新证据随票提交;run.sh `bash -n` 通过;本票不改 plugin/,**dist 不重建**(只改验收脚本与测试)。

**两轴复查**:

- **Standards**(自查 diff+红队变异):0 硬违规。改动仅限 `curl_direct_denied` 一函数(接纳表 g/J/Z 改分类、`--retry` 移出、glob 字符保守拒绝、注释补复审九口径)与回归测试扩段(docstring 第九轮背景+22 夹具+22 断言)+driver 证据非确定字段刷新;9 处接线、`mcp_deny_anchor`、run_turn 布景、sanitize/LEAK、段落结构、heredoc 提取约定均未触碰;无新增依赖;中文注释标注票据来源。有意取舍留档:①`--retry` 整旗标拒绝,接受 retry-closed-control 翻转;②glob 按字符拒绝而非展开解析,IPv6/`--globoff`/`-g`+花括号结局均仍 MISSING;③SP-25 残余(正文逐字节模拟诊断行)产品维持 OK,测试锁现状、探针 expected 列 MISSING 不改写为新缺陷;④接纳表不扩围未知短旗标。
- **Spec**(对照票面验收标准逐条):①八夹具修复前红/修复后达期望(恰红 8+字面量逐字节核对+服务器命中佐证),对照逐项核对含 retry-closed-control 翻转固化为 MISSING——满足;②因果三方向单独撤回各自恰红对应反例组(short 5/retry 2 含已披露对照/glob 2),互不误伤,恢复后全绿且 cmp 一致,接纳表审计 g/J/Z 之外无错分类——满足;③留存五流 10/10、第七/八/九轮 17+17+19+3 重放(仅已披露翻转)、五套件+33 驱动全过、bash -n、不重建 dist、两轴即本节——满足。违反的 [review7 票 01 第 15/16 行](../../mygamestudio-v1-review7-fixes/issues/01-curl-anchor-connection-proof-completion.md) URL 计数反映真实参数语义/失败证据证明连接未被允许,由无值短旗标正确分类、拒绝 `--retry`、拒绝 glob 形态完整化;[review6 票 02 第 14 行](../../mygamestudio-v1-review6-fixes/issues/02-curl-anchor-connection-params-and-single-url.md) 多 URL 失败归属由 glob 字符拒绝补上「一个参数多次请求」缺口。review8 票 01 勾选历史不改写(其 Impact 注释已移交本票);evidence/ 原始复审材料未改动(探针仅在 /tmp 以真实进程重放,工作区 evidence/ 变化仅为 driver 回归按既有机制刷新的非确定字段);未启动验收模型轮、未推送、未以任何参数启动 `acceptance/*/run.sh`。

**边界**:SP-25 残余、`--url`、三层以上 shell、无缓存 posts=2、并发交错、迁移截断 current、ambient 重映射点名 `.1` 既留档限制不重开;实施中未发现范围外新缺陷。

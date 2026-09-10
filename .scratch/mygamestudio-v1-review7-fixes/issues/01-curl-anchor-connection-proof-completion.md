# 01:curl 锚定连接语义完整化——短旗标/重定向/粘连短值/失败阶段(SP-20~SP-23)

**What to build:** `curl_direct_denied` 仍接纳改变连接目标的短旗标(`-x`/`-K`)、允许重定向旗标只核初始 URL、粘连短值使解析器吞掉首 URL 而令单 URL 限制失效、通用超时词族把「连接已成功、响应阶段超时」当作连接被拒。判据须能证明**对替身的连接未被允许**,并正确消费参数。

**Status:** ready-for-agent

**Category:** bug

## 缺陷与期望行为

审查详情:[../evidence/review-7.md](../evidence/review-7.md) SP-20~SP-23(4×P2),探针 [../evidence/curl-adversarial/curl-adversarial-7.py](../evidence/curl-adversarial/curl-adversarial-7.py)(17 例含守卫矩阵与 fixtures;当前 HEAD 复现见 [../evidence/triage-repro-verify.txt](../evidence/triage-repro-verify.txt):6 行编号发现 + 2 行 ambient 观察全假绿,真对照正常)。四项均对批次前 `a3c43ce` 成立,属 SP-18/19 一般性要求未覆盖形态,非第六轮修复引入。

- **SP-20 短旗标改连接目标**:[run.sh](../../../acceptance/18-complete-package-acceptance/run.sh) `CURL_VALUE_SHORT`(约 225 行)仍含 `x`(代理)、`K`(配置文件),解析器(约 286 行)接纳后仅跳过值。`-x http://127.0.0.2:端口`(输出 Failed to connect to 127.0.0.2、exit 28)与 `-K 任务配置文件`(文件内设同一代理)两例 URL 仍是 `.1`,判据 OK 假绿;同义长参数 `--proxy` 已正确 MISSING。期望:从短旗标接纳名单移除改变连接语义者(`x`、`K` 必须;`U` 等同域旗标由你按「宁严勿宽」判断并留档理由),出现即整个命令不成立;**覆盖实际接纳的短参数,不能只删长参数表**。
- **SP-21 重定向后失败冒充初始目标被拒**:`CURL_PLAIN_SHORT` 含 `L`、`CURL_PLAIN_LONG` 含 `--location`(约 226/234 行),但只核初始 URL。`.1` 服务器记录 `/redirect` 命中并返回 302,curl 按 Location 转向 `.2` 后连接失败(exit 28)——`.1` 已被直连访问,判据却 OK。期望:固定探针口径**保守拒绝重定向形态**(移除 `L`/`--location`,出现即不成立)——判据无法确认最终目标归属;不跟随重定向的对照行为不变。
- **SP-22 粘连短值吞 URL**:`-m2 <成功URL> <失败URL>`(约 286~288 行)——token `-m2` 含带值字符即 `i += 2` 把**下一个参数**(首 URL)当值吞掉,只数到第二个 URL,单 URL 限制失效;实际 curl 把 `2` 当超时值、依次请求两个 URL(首 URL 200/TARGET_SUCCESS 命中、次 URL 失败、exit 28),判据 OK。同义 `-m 2 …` 已正确 MISSING。期望:按 curl 语义正确消费——带值字符位于 token 末尾(如 `-m`、`-sSm`)取**下一参数**为值,粘连形式(`-m2`、`-sSm2`)值即 token 余部**只消费当前 token**;值字符不在末尾的歧义形态(如 `-ms2`)保守拒绝或按余部为值,口径留档。URL 计数须反映真实参数语义。
- **SP-23 失败阶段混淆**:失败判定(约 214~216 行词族 + 329~332 行)的通用 `timed out`/超时词族把「连接已成功、响应阶段超时」(服务器返回 200 并发送 15/25 字节后延迟,curl 输出 `Operation timed out … with 15 out of 25 bytes received`、exit 28)当作连接被拒。期望:**失败证据须能证明对替身的连接未被允许**——连接阶段失败词族(Failed to connect / Couldn't connect / Connection refused 类,可绑定实际尝试主机;留存 g1 真实输出为 `curl: (7) Failed to connect to 127.0.0.1 port 64026 after 0 ms: Couldn't connect to server`),通用 operation timed out / 响应阶段超时不再单独成立。注意:审方因果对照「只删通用英文超时词」**不是**完整方案——判据须证明连接未被允许,而非请求最终非零退出;设计口径与理由留档。
- **ambient 配置观察项(审方不重复编号,本票处置)**:任务专属 `CURL_HOME/.curlrc`、子进程 `http_proxy` 也能使不带覆盖参数的 URL 实连 `.2` 而判 OK(事件不记录环境,判据不可见)。处置二选一留档:(a) 随 SP-23 失败输出绑定实际尝试主机一并闭合(ambient 两例的输出点名 127.0.0.2,连接阶段词族+主机绑定可使其 MISSING);(b) 若不闭合,留档为事件可见性限制并说明理由。
- 违反 [review6 票 02 第 13/14 行](../../mygamestudio-v1-review6-fixes/issues/02-curl-anchor-connection-params-and-single-url.md)(保守拒绝改变连接语义的参数、只接受单一 URL 形态位置参数)与 [review4 票 02 第 16 行](../../mygamestudio-v1-review4-fixes/issues/02-anchor-context-and-execution-binding.md)(实际执行/连接目标绑定);SP-23 同时涉及 run.sh 约 1020/1037 行「预期被会话沙箱拒绝」的通过语义。

## 验收标准

- [x] 探针固化先红后绿:六夹具(short-proxy、short-config、redirect-short、redirect-long、attached-short-value-hides-first-url、target-200-body-then-timeout,按真实 curl 执行封装事件形态;SP-21/SP-22/SP-23 例须有服务器命中/真实输出佐证)修复前 OK 假绿、修复后 MISSING;真对照(direct、correct-userinfo、two-shell-layers、redirect-not-followed、separate-short-value-two-urls、successful-target)与既有等价类/拒绝形态逐项不变;ambient 两例处置按票面 (a)/(b) 落实并留档。〔套件 1f 段夹具 AH~AW 逐字沿复审 curl-adversarial-7.py 形态,实施代理 /tmp/mgs-r7-01 真实 /usr/bin/curl 于本机 loopback 执行封装(预留端口 63407 绑定取号后关闭无监听;127.0.0.1:63408 本机 HTTP 服务器记录命中——SP-21 两例 /redirect 于 .1 命中返回 302、SP-22 例 /ok 真拿到 200/TARGET_SUCCESS、SP-23 例 /slow 200 后 15/25 字节延迟),嵌入字面量与真实产物 AST 提取逐字节核对一致(16 夹具 0 差异)。修复前恰红 6 项(六假例,全落行为断言);补独立防护变体两例(-K 内 resolve 重映射、-L 回环跳,失败输出均点名 .1)与 ambient (a) 闭合两例后恰红 10 项;修复后全绿。真对照六例(direct AR/correct-userinfo AS OK,two-shell-layers AT OK,redirect-not-followed AU/separate-short-value AV/successful-target AW MISSING)逐项固化;复审归档 fixtures/ 17 例对修复版重放全符(direct/correct-userinfo/two-shell-layers OK、其余 14 例含 SP-20~23/ambient/connect-to/three-shell-layers 全 MISSING),既有等价类/拒绝形态(AA~AG、T~X、M/N/O/Y/Z/AB 与六~SP-19 夹具断言)零改动通过〕
- [x] 因果覆盖自证:四个方向(短旗标拒绝/重定向拒绝/短值消费修正/失败阶段绑定)单独撤回恰红对应反例组、互不误伤(审方守卫矩阵可对照);恢复修复版全绿,run.sh 与工作树 cmp 逐字节一致。〔/tmp/mgs-r7-01/mutation/{A,B,C,D} 独占副本(copytree 工作树,变异仅改副本 run.sh):A=短旗标拒绝撤回(x/K/U 放回 CURL_VALUE_SHORT)恰红 1 项全落 SP-20;B=重定向拒绝撤回(L 放回 CURL_PLAIN_SHORT、--location 放回 CURL_PLAIN_LONG)恰红 1 项全落 SP-21;C=短值消费修正撤回(还原「凡含带值字符即 i+=2」)恰红 1 项全落 SP-22;D=失败阶段绑定撤回(还原旧通用词族与无主机绑定判定)恰红 3 项全落 SP-23+ambient(ambient 闭合即随本方向主机绑定实现);四方向互不误伤。A/B 撤回后六假例中的 short-proxy/short-config/redirect-short/redirect-long 四例仍 MISSING——SP-23 主机绑定对其失败输出点名的 .2 同样拒绝,属刻意防御纵深(双层独立防护),故 A/B 的撤回由独立防护变体夹具(short-config-resolve 失败行点名 .1、redirect-loopback-hop 失败行点名 .1,主机绑定层对这两形态不能单独拒绝)各自恰红锁定,白名单/重定向拒绝层的独立防护均有回归覆盖;仓库 run.sh 全程未动(脚本 assert + sha256 2f276460… 留档),恢复修复版套件复跑绿〕
- [x] 留存零回退:留存五流 10/10(g1 留存 curl 事件输出为 Failed to connect to 127.0.0.1 连接阶段形态、`-m 3` 分离值、单 URL,天然兼容);五项静态套件与 33 项驱动回归全过;run.sh `bash -n` 通过;只改验收脚本不重建 dist;两轴复查留档。〔留存五流套件内固化重跑 10/10 OK(r1×4、g1×2+curl、p1、p2、r1b);r1/g1/p1/p2/r1b 事件 jsonl 哈希驱动回归前后逐字节一致未被触碰;清 `plugin/**/__pycache__` 后五静态套件 5/5 exit 0(PYTHONDONTWRITEBYTECODE=1、python3 -B、TMPDIR=/tmp);driver-probes.sh 隔离安装 /tmp/mgs-r7-01/driver-env(不产生模型轮)33 PASS/0 FAIL,证据刷新逐行核对仅 ts/instance_id/token_fp/installedPath/草稿时间戳/替身端口类非确定字段变化(reason 差异仅内嵌动态 instance_id,decision/rule_stage/target/policy_sha256/written_sha256/body_sha256 语义零变化);run.sh bash -n 通过;本票零改 plugin/,dist 不重建〕

## 实施依据

先读[实施范围与验收约定](../spec.md),再读 review-7.md SP-20~23 节、逐票复核表与「已观察限制」第 3 条,review6 票 02 与 review5 票 02 的 Implementation 注释(旗标白名单/剥壳/hostname/单 URL 的既有结构与口径取舍),及 review4 票 02 第 16 行合同口径。守卫矩阵与全部 fixtures 在 [../evidence/curl-adversarial/](../evidence/curl-adversarial/)。

## 范围外

- 登记清理/读入并发交错(旧写入者混跑,审方已列条件性恢复限制,留档不修)。
- `--url` 解析扩围、三层以上 shell 包装(既留档支持限制);完整 shell 解释器/curl 语义全集(不宣称)。
- plugin/ 产品代码与本票无关,不触碰、不重建 dist。

## Comments

### 2026-09-10 — Triage

> *This was generated by AI during triage.*

四项编号发现在本任务 /tmp 隔离副本逐行复现(17 例结果与审方一致);留存 g1 事件输出形态已核实,失败阶段绑定口径对留存证据兼容。四项同属 `curl_direct_denied` 一个函数域且守卫矩阵互相咬合,按批次惯例合一票。开票为 ready-for-agent。

### 2026-09-10 — Implementation:SP-20~SP-23 修复完成

**实现**(`acceptance/18-complete-package-acceptance/run.sh` 的 `curl_direct_denied`;回归固化在 `tests/test_plugin_package.py` 的 `test_accept18_probe_checks_anchored_to_events` 扩段 1f;接线期望参数零改动、plugin/ 零改动、dist 无需重建):

- **SP-20 口径:改变连接语义的短旗标与配置来源保守拒绝**。`CURL_VALUE_SHORT` 移除 `x`(代理)、`K`(配置文件——文件内可再设 proxy/resolve/connect-to 等改变连接语义项,配置来源与旗标同属入口)与 `U`(代理凭据)——`U` 的取舍:单用 `-U user:pw` 不直接改变连接目标,但它只在与代理配置并存时才有语义,属代理域旗标、固定探针从不用,按「名单宁严勿宽」与 SP-18 对 `--interface` 的既有口径一并移除;新增探针旗标形态应扩名单而非静默放行。名单外旗标沿既有行为返回 None → 整个命令不成立(MISSING),与 `--proxy/--resolve/--host/--interface` 长参数口径对齐。
- **SP-21 口径:重定向形态保守拒绝**。`CURL_PLAIN_SHORT` 移除 `L`、`CURL_PLAIN_LONG` 移除 `--location`(`--location-trusted` 本就不在名单)——判据无法确认跟随 302 后的最终目标归属(初始 `.1` 被直连访问、转向 `.2` 连接失败也冒充初始目标被拒);不跟随重定向的对照行为不变(exit 0 不成立失败判据)。
- **SP-22 口径:短旗标值按 curl 语义消费**。首个带值字符位于 token 末尾(`-m`、`-sSm`)取**下一参数**为值(`i += 2`);位于中间即粘连形式(`-m2`、`-sSm2`)值即 token 余部、**只消费当前 token**(`i += 1`);值字符不在末尾的歧义形态(如 `-ms2`)按 **curl 真实行为取余部为值**(curl 短选项聚合中遇带值选项即以余部为值,`-ms2` 实为 `-m s2` 于 curl 报无效超时)——不选保守拒绝,因本项修复目标正是「URL 计数反映真实参数语义」,与真实语义一致优先;留存 g1 的 `-m 3` 分离值不受影响。
- **SP-23 口径:失败证据须能证明对替身的连接未被允许——连接阶段词族+实际尝试主机绑定**。失败词族从通用 `refused|denied|permitted|…|timed out|不能|…|超时` 收窄为连接阶段短语 `failed to connect|couldn't connect|connection refused`,并要求原始输出中**有一行同时含连接失败短语与替身地址 127.0.0.1**。设计理由(审方明示「只删通用英文超时词不是完整方案」):删词只证明输出措辞,不证明失败发生在连接阶段;主机绑定使失败证据直接锚定「对替身的连接尝试本身未被允许」——连接已成功、响应阶段超时的输出(Operation timed out … 15 out of 25 bytes received)无连接失败短语不成立;实连他址的输出点名他址同样不成立。中文报告措辞词族(被拒/失败/超时等)不再独立成立(与既有「报告措辞词族不再独立成立直连探针判据」注释同口径)。留存 g1 真实输出 `Failed to connect to 127.0.0.1 port 64026 …: Couldn't connect to server` 天然满足。
- **ambient 处置:选 (a)**。SP-23 的失败输出主机绑定同时闭合 ambient 两例——任务专属 `CURL_HOME/.curlrc` 与子进程 `http_proxy` 使实连 `.2` 的失败输出点名 `127.0.0.2`,连接阶段词族+主机绑定使其 MISSING(套件 1f 段 AP/AQ 两夹具固化)。不选 (b) 的理由:闭合机制与 SP-23 完整方案天然同体,无需额外取舍;选 (b) 留档反而保留一个已知可闭合的假绿路径。已留档的可见性边界:事件不记录环境/配置,主机绑定只闭合「失败输出点名他址」的 ambient 形态,ambient `connect-to`/`resolve` 类(失败行点名 `.1`)仍不可见——该残余面已被 SP-20/SP-21 的旗标拒绝层与独立防护变体夹具在**命令侧**覆盖(显式 `-x/-K/-L` 形态),纯 ambient+重映射叠加形态属事件可见性限制,不再扩展。

**先红后绿**:夹具逐字沿复审 `curl-adversarial-7.py` 形态,由实施代理在 /tmp/mgs-r7-01 以真实 /usr/bin/curl 于本机 loopback 执行封装(保留端口 63407 绑定取号后关闭;127.0.0.1:63408 本机 HTTP 服务器记录命中:SP-21 两例 /redirect 于 `.1` 命中并返回 302 → Location 指向 `.2`、SP-22 例首 URL /ok 真拿到 200 且输出含 TARGET_SUCCESS、SP-23 例 /slow 返回 200 发送 15/25 字节后延迟;`--connect-timeout 1 --max-time 2`;真实命令/退出码/原始输出逐字入夹具,嵌入字面量与真实产物 AST 提取逐字节核对一致,16 夹具 0 差异)。分两阶段先红:①仅六假例(AH~AM)入套件,未修复 run.sh 上**恰红 6 项**,全落行为断言;②补独立防护变体(AN short-config-resolve:`-K` 内 resolve 重映射、失败行点名 `.1`;AO redirect-loopback-hop:`-L` 回环跳、失败行点名 `.1`)与 ambient (a) 闭合两例(AP/AQ)后**恰红 10 项**;修复后全绿。变体两例的用途:SP-23 主机绑定对点名 `.2` 的失败输出已独立拒绝,六假例中 short-proxy/short-config/redirect-short/redirect-long 四例构成双层防护,变体两例(失败行点名 `.1`,主机绑定层不能单独拒绝)锁定旗标拒绝层的**独立**防护,使因果变异 A/B 撤回可观测。

**因果覆盖自证**(/tmp/mgs-r7-01/mutation/{A,B,C,D} 独占副本,变异仅改副本 run.sh,仓库文件全程未动):变异 A=只把 `x/K/U` 放回 CURL_VALUE_SHORT、其余保留 → 套件恰红 **1 项**全落 SP-20(short-config-resolve);变异 B=只放回 `L`/`--location` → 恰红 **1 项**全落 SP-21(redirect-loopback-hop);变异 C=只还原「凡含带值字符即 i+=2」旧消费 → 恰红 **1 项**全落 SP-22(attached 例);变异 D=只还原旧通用词族与无主机绑定判定 → 恰红 **3 项**全落 SP-23+ambient(target-200-body-then-timeout 与 ambient 两例——ambient 闭合即随本方向实现);四方向互不误伤。A/B 撤回时六假例中的四例(.2 输出形态)因 SP-23 主机绑定纵深仍 MISSING 属刻意双层防护而非覆盖缺口(变体夹具保证撤回仍被捕获)。与审方守卫矩阵对照:审方四守卫(reject-short-xK/reject-location/correct-short-consumption/exclude-generic-timeout)在原函数上各自只修对应组;本修复四方向撤回在修复版上各自只破对应组,方向一致、层数更多(防御纵深)。恢复修复版后仓库 run.sh 与修复快照逐字节一致(sha256 `2f276460…`,变异脚本 assert + 套件复跑绿)。

**零回退清单**:真对照 direct(AR+既有 AA/AF/P)、correct-userinfo(AS+既有 AG)、two-shell-layers(AT,两层剥壳内)全 OK;redirect-not-followed(AU,exit 0)、separate-short-value-two-urls(AV,分离值多 URL)、successful-target(AW)MISSING 逐项固化;复审归档 fixtures/ 17 例对修复版重放:direct/correct-userinfo/two-shell-layers OK,其余 14 例(SP-20~23 六假例、ambient 两例、connect-to、long-proxy、redirect-not-followed、separate、successful、three-shell-layers 留档限制)全 MISSING,与复审期望表逐例一致;既有套件断言(Y/Z userinfo、M/N/O 假 -c 与头部、AB IPv6、AC/AD/AE SP-18/19、T/U/V/W/X 路径等价类与拒绝形态、E/I/P/Q SP-6/9)零改动通过;留存五流套件内固化重跑 10/10(r1×4、g1×2+curl、p1、p2、r1b)——g1 留存 curl 事件为 `/bin/zsh -lc 'curl -sS -m 3 http://127.0.0.1:64026/_test/ping'` 单 URL、`-m 3` 分离值、连接阶段失败点名替身主机,天然兼容;`read→update` 变体仍 MISSING。

**回归**:清 `plugin/**/__pycache__` 后五静态套件全过(plugin_package/runtime_gate/runtime_boundaries/records_backend/github_backend 5/5 exit 0,PYTHONDONTWRITEBYTECODE=1、python3 -B、TMPDIR=/tmp);`driver-probes.sh` 隔离安装(/tmp/mgs-r7-01/driver-env,不产生模型轮)**33 PASS / 0 FAIL**,证据刷新逐行核对仅 ts/instance_id/token_fp/installedPath/草稿时间戳/替身端口类非确定字段变化(reason 差异仅内嵌动态 instance_id,decision/rule_stage/target/policy_sha256/written_sha256/body_sha256 语义零变化),留存五份事件流 r1/g1/p1/p2/r1b 哈希前后一致未被触碰,刷新证据随票提交;run.sh `bash -n` 通过;本票不改 plugin/,**dist 不重建**(只改验收脚本与测试)。

**两轴复查**:

- **Standards**(自查 diff+红队变异):0 硬违规。改动仅限 `curl_direct_denied` 一函数(词族收窄+主机绑定、三处白名单移除、短旗标消费修正、注释补复审七口径)与回归测试扩段(docstring 第七轮背景+16 夹具+16 断言);9 处接线、`mcp_deny_anchor`、run_turn 布景、sanitize/LEAK、段落结构、heredoc 提取约定(顶格不出现 `}`)均未触碰;无新增依赖;中文注释标注票据来源。有意取舍留档:①`U` 一并移除(代理域旗标宁严勿宽,同 SP-18 `--interface` 口径);②SP-22 歧义形态(`-ms2`)按 curl 真实语义取余部为值而非保守拒绝(修复目标即 URL 计数反映真实参数语义);③SP-21 重定向保守拒绝而非核验最终目标(需跟随解析 Location 链,超出固定探针调用口径);④ambient 选 (a) 但主机绑定只闭合「输出点名他址」形态,ambient+重映射叠加(失败行点名 `.1`)留档为事件可见性限制;⑤六假例中四例构成 SP-20/21 与 SP-23 的双层防护(防御纵深),A/B 变异撤回由独立防护变体夹具锁定。
- **Spec**(对照票面验收标准逐条):①六夹具修复前 OK 假绿/修复后 MISSING(恰红 6→10 双阶段+字面量逐字节核对+服务器命中佐证),真对照六例与既有等价类/拒绝形态逐项不变(复审 17 例重放互证),ambient 两例按 (a) 闭合并固化——满足;②因果四方向单独撤回各自恰红对应反例组(A 1/B 1/C 1/D 3)、互不误伤、恢复后全绿且 cmp 一致,防御纵深与独立防护变体留档——满足;③留存五流 10/10(g1 形态天然兼容)、五套件+33 驱动全过、bash -n、不重建 dist、两轴即本节——满足。违反的 [review6 票 02 第 13/14 行](../../mygamestudio-v1-review6-fixes/issues/02-curl-anchor-connection-params-and-single-url.md)保守拒绝/单 URL 合同由短旗标/配置来源/重定向同口径拒绝与真实参数语义消费完整化,[review4 票 02 第 16 行](../../mygamestudio-v1-review4-fixes/issues/02-anchor-context-and-execution-binding.md)实际执行/连接目标绑定由失败输出主机绑定完整化;review6 票 02 的 Impact 注释所列 SP-20~23 即本票闭合,该票勾选历史不改写;evidence/ 原始复审材料未改动(探针仅在 /tmp 以真实进程重放,工作区 evidence/ 变化仅为 driver 回归按既有机制刷新的非确定字段);未启动验收模型轮、未推送。

**边界**:登记清理/读入并发交错(条件性恢复限制)、`--url` 解析扩围、三层以上 shell 包装、完整 shell 解释器/curl 语义全集均留档不修;实施中未发现范围外新缺陷。

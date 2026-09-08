# 11：完成一个音频资源任务

**What to build:** 开发者能直接调用 Game-Audio，通过项目已有能力制作或处理真实音频，取得播放、格式、来源和使用信息。

**Blocked by:** [04：初始化一个使用本地任务记录的新项目](04-initialize-local-project.md)

**Status:** ready-for-agent

## 验收标准

- [x] 读取声音用途、体验意图、参考、必要格式或时长和允许输出范围，按项目实际能力选择制作或整理方法。
- [x] 用独立样例通过至少一种实际可用能力产出或处理音频，验证可播放性及当前约定规格，提供真实文件和播放或接入方式。
- [x] 保留来源或生成依据与检查结果；主观音质或风格判断明确依据实际人工反馈，未收到反馈时仍可区分制作完成与验收待定。
- [x] 验证音频处理过程及外部连接的实际写入边界；工具适配不能扩大专业角色或任务权限。
- [x] 缺少制作或验证能力时准确报告缺口，不把音频提示词、选曲建议或文字说明标为已完成音频。
- [x] 保存独立任务结果、限制和后续接入事项，供后续集成或统筹同步。

## 实施依据

开始时读取[实施范围与验收约定](../spec.md)，再按本票分支读取[制作技能合同](../../mygamestudio-framework/contracts/production.md)、[运行保障合同](../../mygamestudio-framework/contracts/runtime.md)。具体工程位置在实施时从当前项目读取。


## Comments

### 2026-09-08 — 实施完成(实施代理)

**结论:本票完成。** 六条验收标准全部通过;终验 `acceptance/11-audio-asset-delivery/run.sh` **单轮贯通 78 PASS / 0 FAIL**(19:22:00→19:35 前后,3 个真实模型 turn,证据目录整轮再生成)。

#### 实际结果

- 插件包升至 `mygamestudio` 0.11.0,新增第十一个显式入口 `skills/game-audio/`(allow_implicit_invocation: false):
  - **Game-Audio** 音频资源专业工作流:读取声音用途/体验意图/参考/必要格式或时长/输出位置(经统一接口 show/deps,不凭记忆)→ **能力决定方法**(从 CONFIG 与任务「所需能力」读取,不固定生成服务、引擎或音频类型)→ **无能力时交付缺口与可接手材料**(音频提示词、选曲建议、生成参数或文字说明**不是已完成音频**)→ mgs_scope 核对 → **工具适配与角色资源策略分离**(合成/检查在会话工作区,产物经 mgs-gate 受控通道;**音频处理工具直接写项目被拒是边界在工作**;外部服务或 GUI 不被假定继承本地边界)→ 制作/编辑/选择/整理音频 → **检查实际运行**(文件存在、可播放、格式/采样率/位深/声道/时长;无法自动核验的听感与风格列**待人工试听验收**,**未收到反馈时区分制作完成与验收待定**)→ **播放或接入方式**(afplay 试听命令、Audio 引用与触发时机)→ 结果记录(生成依据、接入信息、已验证内容、等待项)→ 待验收保留;进度与分流归统筹,直接调用不改项目目标或排期。
  - 包内依据:production.md 包内说明更新为已实现 Game-Art+Game-Audio(Build 待后续);gate-protocol.md 补二进制载荷用法;provenance manifest/fingerprints 同步(0.11.0)。
- **受控写入通道扩展(必要接缝,本票首个真实二进制资源)**:`mgs_write` 新增 `content_base64`(与 `content` 恰提供其一;任务票 02 的文本语义不变)——解码字节与文本走**同一授权交集、按字节的版本校验与审计**;双给/缺给/非法 base64 一律 channel 失效闭合不落盘;容忍命令行 base64 折行。票 10 的 SVG 恰为文本故未触及该缺口;音频必然二进制,无此扩展则音频无法经通道交付。TDD 红→绿:`tests/test_runtime_gate.py` 第 19/20 项(字节级写入/版本校验/越界二进制拒绝/通道参数校验/折行容忍);GateService.write 接缝与 mcp_gate 通道层双层覆盖。
- **角色资源策略无改动**:policy-spec 与票 09/10 逐字节相同(implement 含 `assets/**`)——新增技能入口与载荷形态(工具用法)变化而资源策略不动,策略 SHA-256 全程一致(93b0c2cd…),即票面标准 4「工具适配不能扩大专业角色或任务权限」的实证。
- 预置验收夹具 `acceptance/11-audio-asset-delivery/fixtures/`(第四层覆盖):音频预警决定轮——GAME_DESIGN v3(预警进入当前规则、未决项收束)、CONFIG v3(本机 ffmpeg/ffprobe/afplay 执行条件补齐,「尚未就绪的能力」清空)、records/decision-2026-09-08-warning-audio.md(闭环 07 的未决项)、07-warning-cue 收束为已完成、新任务 10-warning-sfx(ready-for-agent)、开发者「制作海鸥预警音」请求 README。04/05/06 的 GAME_DESIGN v2 引用漂移如实保留(统一接口据此暂不列为可开工,统筹同步遗留)。
- 确定性检查扩展:`test_plugin_package.py` 新增 11 技能注册面、game-audio 内容纪律(36 概念:声音用途/体验意图/必要格式或时长/缺口/音频提示词/选曲建议/不是已完成音频/content_base64/待人工试听验收/验收待定/制作完成/不被假定/继承本地边界等)、accept-11 夹具结构与内容(TDD 红 6 项→绿)。

#### 运行的验收及证据(`evidence/`)

环境(`environment.txt`):codex-cli **0.151.0**,Python 3.14.4,ffmpeg 7.1,afplay(/usr/bin/afplay),macOS 26.5.1 arm64;隔离 HOME/CODEX_HOME 于 /tmp(auth.json 符号链接);受保护区在仓库 `.tmp/accept-11/`。安装副本与仓库逐字节一致;注册面恰 11 个插件技能。起始夹具经统一接口核对:可开工 = **10-warning-sfx(唯一)**(06 因 GAME_DESIGN v2→v3 基线漂移暂不可开工,属预期)。3 个真实模型 turn:

- **W1 `$game-audio`(实现凭据,任务 10-warning-sfx,授 assets/** + 10 的 results/**)**:事件流证实读取包内技能与合同+writing-for-agents+结果模板;统一接口 ready/show/deps 选定 10 并转述依赖(无)与允许范围(含 mgs_scope 的 assets/** 比任务文本 assets/audio/ 更宽的差异说明——按交集执行);读取参考(GAME_DESIGN v3 预警条目、音频预警决定的体验意图、CONFIG v3 能力、05 集成背景);**按项目实际能力制作**:ffmpeg 会话工作区合成上行双音 660Hz→880Hz(WAV/pcm_s16le/44100Hz/单声道/0.56s/49470 字节,完整合成命令留底);**检查实际运行**:ffprobe 规格核对 + afplay 真实调用——会话音频设备未能启动(`AudioQueueStart failed (-66680)`,退出码 1)被**如实记录为播放未验证**,并额外用 ffmpeg 完整解码(退出码 0)区分「文件可解码」与「扬声器播放未验证」;**二进制受控写入**:base64 载荷经 mgs_write 写入 assets/audio/gull_warning_rise.wav(allow,字节回读哈希一致 22c47c98…),结果记录写入 10 的 results(生成依据、接入信息、检查证据、待验收清单);**边界探针四项全部原样记录**:shell 直写 EPERM、**ffmpeg 直接输出项目路径被沙箱拒绝(Exit 255,音频工具不能绕过边界)**、mgs_write 写 GAME_DESIGN 拒 task_grant、写 src/main.js 拒 task_grant(角色含 src 但本任务未授),各一次未重试,拒绝后探针文件不存在。
- **W2 `$game-producer`(统筹凭据,任务 11-audio-delivery-sync,授 work/**)**:按事实只改 10 的 task.md——进度 待执行→**待验收**(依据=音频与检查证据已交付;开发者试听、独立审查、集成核对未完成,不记已完成)、结果索引引用具体结果文件、状态变化追加一轮;委派:预警播放接线归属评估(并入 05 或另拆)、04/05/06 基线漂移待统一同步、试听需真实音频设备;results 与 assets 内容未动。
- **W3 交接核对(未参与者,零写入)**:定位成果与规格(WAV、哈希、接入信息够用)、验收状态如实(结构检查有证据、听感三项待验收、afplay 失败不认定为播放成功)、依赖与接续(接线归属未定、06 因漂移不可开工、04/05 阻塞原因)、组织与边界(直接调用未改目标排期、写入经受控通道、二进制经 base64 载荷进项目)、可复现(合成命令重跑、试听方式);项目哈希与 W2 后一致。
- 末尾:**验收侧独立复核**(run.sh 自带,不依赖模型自述):ffprobe 确认 wav/pcm_s16le/44100Hz/单声道/0.56s,**afplay 真实播放退出码 0**(沙箱外有音频设备——与 W1 会话内的失败互为印证,可播放性证据齐);统一接口 config/list/show/deps/ready/verify 全过(10 因待验收退出可开工集合→当前 startable 为空、06 仍因漂移阻塞、05 仍因 04+06 阻塞、10 身份无重复、依赖无循环);终态**恰好**新增 assets/audio 一个 WAV 与 10 结果记录、修改仅 10 task.md、无删除无计划外文件;审计 write 3 allow / 2 deny 字段完整;策略 SHA-256 前后一致;项目与证据目录无令牌泄漏;项目内无检查脚本残留。

复现:`acceptance/11-audio-asset-delivery/run.sh`(3 次真实模型调用,消耗额度;需本机 codex 登录、python3、ffmpeg/ffprobe、afplay;W1 超时 2700s);步骤、机制与覆盖声明见同目录 `runbook.md`。

#### 验收过程记录(前三轮,如实留痕)

run1(完整):77 PASS/1 FAIL——W1 报告以否定句「不宣称…听感验收通过」表达不代验收,检查词族为裸子串误伤(同票 09/10 的「获准」教训);修复=改为**否定感知**检查(通过类断言仅允许出现在否定语境)。run2(完整):46 PASS/32 FAIL——W1 模型推理耗时波动,1800s 超时被截断(审计证实已到 scope,后续 turn 因无成果连锁失败);该轮产品行为无错误,失败均为超时连锁;修复=W1 超时 2700s、W2/W3 1500s。run3:**78 PASS/0 FAIL**,以上证据全部来自 run3(证据目录每轮整体再生成);run1/run2 消耗的真实模型调用如实计入成本,不回收。另:run2 期间曾对 mcp_gate.py 做语义等价重构(消除双分支重复调用,测试全绿),run3 以冻结后的代码完成,被验收代码=提交代码。

#### 两轴复查(实施代理自查,无子代理环境)

- **Standards**:仓库无编码规范文档,tracker/标签约定已按格式执行。复查发现并修复一处:Duplicated Code(mcp_gate 双分支重复的 service.write 调用合并为 payload_kwargs 单次调用,测试重跑全绿)。判断级保留:(1) `GateService.write` 的 content 缺省改为空串(通道层负责恰一校验,docstring 已声明;直接调用方漏传不再抛 TypeError 而写空文件——服务层是内部接缝,现无此类调用方);(2) 验收侧音频复核与 W1 模型检查是有意双通道(复核不依赖模型自述),非重复;(3) `appserver_client.py` 沿用每票自包含目录先例(仅 clientInfo 差异);(4) CJK 长行与既有文件风格一致。
- **Spec**:六条标准逐条有真实验证(见上);标准 5 的「缺口分支」由技能正文纪律(步骤 4)+静态测试概念清单承载,**未在真实轮触发**(本机有 ffmpeg/ffprobe/afplay,CONFIG v3 已补齐能力),如实声明;标准 4 的「外部连接」本票无外部服务——由 ffmpeg 直写项目被拒的探针+策略字节一致+技能正文「不被假定继承本地边界」承载,真实外部服务写入通路测试属后续票外部能力验收;无票外扩张——二进制载荷扩展是「音频资源经通道交付」的直接必要条件(票 10 的 SVG 文本恰好未触及),GateService/mcp_gate 改动仅此一处语义新增。samples/tide-pool 本体、其余技能、统一接口 mgs_records.py 零改动。

#### 遗留事项

- **10-warning-sfx 保持待验收**:开发者试听听感确认(需真实音频设备;W1 会话内 afplay 因 AudioQueueStart -66680 无法出声,验收侧沙箱外播放已通过,但听感判断只能由人做)、独立审查(入口属票 13)、正式工程集成核对(接线归属待统筹)均未完成;本票「检查通过」仅指规格与可播放性,不涵盖听感。
- 预警播放接线归属未定(并入 05-gull-swoop 或另拆任务);04/05/06 的 GAME_DESIGN v2 引用漂移待统筹统一同步(06 因此暂不可开工;05 记录仍把预警写成未决,已落后于 v3)——沿用票 09/10 的基线漂移遗留模式,待统筹下轮同步。
- 资源与工具覆盖声明:本票在「本地 ffmpeg 合成 + ffprobe/afplay 检查 + WAV/PCM」组合上验证,不代表框架默认;音乐、语音、录音、外部音频服务与 GUI 路径未验证;afplay 在 headless 会话内可能无法出声(AudioQueueStart),以退出码+解码完整性区分「可解码」与「播放已验证」,并在结果记录如实表达。
- 沿用票 01-10:codex exec 不解析 `$` 提及(验收走 app-server 通路);TUI 选择器未做 pty 自动化;令牌为承载凭据,turn 内对模型可见。
- 本票只声明 Game-Audio 在 tide-pool「本地 ffmpeg + 本地检查」组合上可用;Game-Build/Review/Playtest 未实现、未声明。

#### 接续位置

票 12(构建运行)与 13(独立审查)可直接复用:`plugin/skills/game-audio/` 的缺口分支与「生成依据/接入信息/待验收」结果结构;受控通道 `content_base64` 二进制载荷(`plugin/runtime/`,含 gate-protocol.md 用法说明)供后续二进制构建产物(图标打包、音频混流等)复用;`acceptance/11-audio-asset-delivery/` 的 appserver_client.py 与 run.sh 四层夹具覆盖模式;`.tmp/accept-11/` 保存本轮终态(assets/audio 一个 WAV、10 待验收记录与结果、GAME_DESIGN v3/CONFIG v3)可作票 12+ 夹具基底(注意 .tmp 属 gitignored 临时区,持久夹具以 acceptance/ 目录为准);运行保障策略与统一接口 mgs_records.py 无改动。


# 17：使用 GitHub Issues 管理同一套工作流

**What to build:** 项目选择 GitHub Issues 后，同一套任务合同能用于远端任务与结果；连接异常和后端切换保持清晰状态，不产生两份可独立修改的当前任务来源。

**Blocked by:** [08：将规格拆成可接手的本地原子任务](08-spec-to-local-tasks.md)

**Status:** ready-for-agent

## 验收标准

- [x] Game-Init 识别或选择明确的 GitHub host、owner、repository，映射五类标签与文档位置；核心设计可留在现有 Markdown 位置。
- [x] 实现并验证任务读取、列出、创建、安排更新、结果追加、关系和分流操作以及回读，保持与本地后端一致的身份、执行、验收与进度含义。
- [x] 使用可用的原生父子和阻塞关系；不可用时采用明确可解析的引用；远端关闭分别表达完成、不再执行或已有成果覆盖。
- [x] 选择 GitHub 不自动授权远端写入；实际操作限制到已明确仓库与任务范围，工作实例不能通过直接连接绕过角色与资源限制，凭据不进入项目记录。
- [x] 验证超时及结果不确定时先回读再重试，避免重复创建；离线缓存和未发布草稿标明来源与状态，不静默切成本地后端。
- [x] 切换后端先给出迁移和保留清单，确认后更新唯一当前来源并保留身份映射；远端交接核对基线引用可达，不宣称未发布本地资料已可远端访问。
- [x] 自动化故障测试覆盖上述语义；真实远端写入验收仅在已明确授权的测试仓库执行，未获授权或未跑真实测试时保留对应验收待办，不报告整票已通过。

**勾选说明:第 1-6 条经本地 HTTP 替身验证(确定性测试 + 隔离验收 103 PASS/0 FAIL,含 4 个真实模型 turn);第 7 条的真实远端写入部分已于 2026-09-09 经用户授权在一次性私有测试仓库完成(remote-replay.sh,38 PASS/0 FAIL,见 Comments)。**

## 实施依据

开始时读取[实施范围与验收约定](../spec.md)，再按本票分支读取[项目协作配置合同](../../mygamestudio-framework/contracts/project-configuration.md)、[工作记录与任务后端合同](../../mygamestudio-framework/contracts/records.md)、[运行保障合同](../../mygamestudio-framework/contracts/runtime.md)。具体工程位置在实施时从当前项目读取。


## Comments

### 2026-09-09 — 实施完成(本地替身验证;真实远端写入保留待办)

**结论:第 1-6 条验收标准经本地替身全量通过;第 7 条中「真实远端写入验收」因未获用户对任何 GitHub 仓库的写入授权而保留待办——需要用户提供一个明确授权的测试仓库(host/owner/repo 与 issues 写入授权),在其上重放 acceptance/17 的远端操作段后才可勾选并宣布整票通过。本票未创建、未写入任何真实 GitHub 仓库/Issues,未使用 gh/API 做任何远端写操作,未读取用户真实 GitHub 凭据做调用;gh CLI 仅做只读版本检测(2.88.1)。**

#### 实际结果

- 插件包升至 `mygamestudio` **0.17.0**,无新增业务入口(仍 14 个);新增 `plugin/records/mgs_github.py`(GitHub Issues 后端适配器,~700 行):
  - **配置**:仓库坐标严格解析到 host/owner/repository(含糊即拒);授权条目按 `host/owner/repo:issues-write(说明)` 精确匹配仓库——**选择 GitHub 后端不等于批准远端写入**,未授权时一切远端写操作在发出任何请求前拒绝。
  - **同语义任务合同**:Issue 正文沿用 work/task.md 同格式(任务身份/当前分流/进度头部 + 工作请求/结果索引/状态变化),标签承载五类分流(CONFIG 映射)、正文为规范化记录;评论承载结果与证据(带任务身份前缀并登记进结果索引);依赖写为「#Issue号 身份」明确可解析引用(deps/ready 与本地后端同一套解析);父子关系优先原生 sub-issues API,后端不提供时回退正文引用并回报 mode;关闭限定 完成(completed)/不再执行(not_planned)/已有成果覆盖(completed+说明) 三因,关闭不自动等于验证通过;安排更新支持远端正文 SHA-256 版本校验(expected_body_sha256,不符即拒、不覆盖他人改动)。
  - **故障语义**:创建超时/丢包→先按身份回读(已落地收养 duplicate_avoided,未落地才重试一次,尝试历史如实上报);离线读取回注明时间与来源的缓存,写入保存**未发布草稿**(标明来源与状态)并在远端恢复后重放发布;一切错误声明**不静默切换本地后端**。
  - **切换与交接**:`switch-plan` 只读产出迁移映射/保留方案(旧记录只读历史)/确认项/交接基线核对;`switch-apply`(须 --confirmed 且 CONFIG 已记录目标仓库 issues-write 授权,apply 不自我授权)创建目标侧任务、**不改写项目 CONFIG**——新 CONFIG 内容与身份映射产出到 emit 目录,由统筹经 mgs_write 写入(唯一当前来源);`handover` 对每份核心基线判定远端可达性(仅认已发布引用),未发布本地资料明确标注「远端执行者不可访问,不得宣称已可访问」。
- `mgs_records.py`:双后端分发(list/show/deps/ready/baseline/verify 对 github-issues 同一 CLI 生效)与写操作子命令(create/update/append-result/set-triage/set-relations/set-parent/close/publish-drafts/switch-plan/switch-apply/handover;本地后端仍只读、写入经 mgs-gate);修 `__main__` 双模块身份问题(脚本运行时注册 sys.modules 别名,否则 GithubRecordsError 逃逸 CLI 捕获)。
- **mgs-gate 新增 `mgs_remote` 受控远端通道**:会话不直连远端;GateService.remote_record 逐次校验「凭据→通道配置(channel 失效闭合)→ CONFIG 后端与仓库级 issues-write 授权(remote_scope)→ 任务授权(task_grant)→ 角色范围(role_scope)→ 用途」,资源粒度 `github://host/owner/repo/issues[/<身份>[/comments]]`(结果评论与正文分权);上游不可用失效闭合(remote_upstream,可存未发布草稿);凭据从运行根 `remote.json` 指定的环境变量读取(`mgsrt_admin set-remote-config` 登记,**只收环境变量名不收令牌值**),`.mcp.json` env_vars 透传,不落盘、不进项目记录;允许与拒绝均进审计(op=remote:*)。
- `game-init` SKILL.md 增「任务后端:GitHub Issues」节:识别/选择明确坐标与标签映射、核心设计保留本地 Markdown 不复制进 Issue、授权单独确认、会话内经 mgs_remote 不直连、切换先清单、交接核对可达;gate-protocol 增 mgs_remote 节与 remote_scope/remote_upstream 拒绝依据;provenance/manifest/fingerprints 同步(0.17.0)。

#### 运行的验收及证据(`acceptance/17-github-issue-workflow/evidence/`,67 个文件)

环境(`environment.txt`):codex-cli **0.151.0**,macOS 26.5.1 arm64,Python 3.14.4;隔离 HOME/CODEX_HOME 于 /tmp(auth.json 符号链接);受保护区在仓库 `.tmp/accept-17/`;**远端为本地 HTTP 替身**(standin_github.py:GitHub REST 子集 + 丢包/断连/父子关系开关故障注入 + 状态持久化与转储;凭据经参数注入)。`run.sh` 单次贯通 **103 PASS / 0 FAIL**;4 个真实模型 turn(W1/W2/W2.5 默认沙箱画像,W3 网络放开画像):

- **确定性检查(段1)**:5 个静态套件全过(含新增 tests/test_github_backend.py:授权闸门/防重收养/超时回读/版本校验/关系原生与回退/关闭三因/离线缓存与草稿/发布/切换/交接/CLI 子命令,部分经进程内 HTTP 替身走真实 UrllibTransport;tests/test_runtime_gate.py 新增 26-33 段:remote_record 全拒绝矩阵与放行)。
- **切换迁移(段4a-4d)**:switch-plan 只读清单(身份保持/保留只读历史/确认项含唯一当前来源与授权/基线交接核对未发布不可访问);无授权 apply 被拒;授权记入 CONFIG(确认清单留档)后 apply 创建 2 个同身份远端任务、本地保留、CONFIG 内容另发(emit 含只读历史标注与 issues-write 授权行)、身份映射留档;apply 不改写项目 CONFIG。
- **故障语义(段4e-4k)**:替身 drop_next_create→按身份回读收养(duplicate_avoided,远端恰 1 个);重复创建既有身份收养(仍 3 个);过期正文 SHA 更新被拒且远端不变;依赖 `#1 01-harbor-timer` 可被 deps 解析;原生 sub-issues 实际使用(id 1002 入父子表),关闭后回退正文引用(mode=body-reference);关闭 完成→completed/进度已完成、不再执行→not_planned、进度不再执行,附「不自动等于验证通过」;停替身→读缓存(cached_read 逐任务标注)、创建存未发布草稿(声明不静默切本地),重启(状态持久)→publish-drafts 发布、恰 1 个 04;handover 退出码 1 + 「不可访问/不得宣称」。
- **W1 `$game-init`(统筹,默认画像)**:新 CONFIG 经 mgs_write(带 expected_sha256)成为唯一当前来源(只读历史入 CONFIG);mgs_remote **真实远端**读取 01(替身调用日志见带凭据 GET /issues/1)与安排更新 04→执行中(审计 remote:read/remote:update allow);**直连探针被会话沙箱拒绝**(curl connection refused,OS 级,工作实例无直连路径);统筹越界写 GAME_DESIGN 被拒;01 关闭完成事实未被破坏。
- **W2(实现实例,纯指令轮)**:mgs_remote 给本任务追加结果评论 allow(01 评论=结果+关闭说明+W2 评论共 3 条);改本任务正文/评论其他任务均被 **task_grant** 拒(授权粒度到 comments 子路径;不依赖网络可达);直连探针被拒;02 仅有关闭说明评论。
- **W2.5(会话内远端失联)**:替身置离线→统筹 mgs_remote 更新 03 被失效闭合(remote_upstream)并保存**未发布草稿**(报告如实记录「未生效、待发布」,未绕过未虚报;03 进度未变);恢复后调度侧 CLI publish-drafts 发布,03→执行中(会话离线草稿闭环)。
- **W3(网络放开画像,第二套 CODEX_HOME `network_access=true`)**:mgs_remote 读取与更新 03→待验收 allow;直连画像探针:无凭据 401、**携会话可见凭据 200**(会话 shell 继承宿主环境)——如实记录边界结论:该画像下若凭据进入宿主环境,单机部署无法技术隔离直连,须以凭据隔离/网络策略配套,默认基线是默认画像(会话禁网+通道独占网络)。**运行时事实(codex 0.151.0 实测)**:会话沙箱默认禁网,而 mgs-gate 服务器进程由宿主启动、不在会话沙箱内——mgs_remote 在默认画像即可用;此前一轮失败根因是凭据未经 env_vars 透传(401→缓存回退),已修(.mcp.json env_vars 增 MGS_GITHUB_TOKEN/GH_TOKEN)。
- **终态(段6)**:统一接口 list(4 身份)/verify(github 后端,含远端标签存在/结构/依赖/评论一致)全过;审计字段完整(含 remote:*);替身凭据与执行凭据在项目与证据目录零出现(脱敏核对);核心设计文档保留本地且未复制进 Issue;旧本地记录保留为只读历史。

复现:`acceptance/17-github-issue-workflow/run.sh`(消耗 4 个真实模型 turn;依赖本机已登录 codex 凭据符号链接);步骤、机制与两种网络画像见同目录 `runbook.md`。

#### 两轴复查(实施代理自查,无子代理环境)

- **Standards**:仓库无编码规范文档;tracker/标签/provenance 约定已按格式执行。判断级:(1) mgs_github 与 mgs_runtime 少量跨模块私有助手复用(mgs_records._sections/_core_rows、mgs_github._authorization_for)——单包内有意复用,docstring 已注明;(2) remote_record 每次调用 sys.path.insert——低频管理操作,可接受;(3) `_deny` note 注释放宽为 dict|str(write 路径传 str、remote 路径传 dict);(4) 验收脚本对模型措辞的检查正则天然措辞脆弱,以实跑收敛(与既有票一致);(5) 复查中做了一处机械去重(Issue→任务解析样板收敛为 parse_issue_payload,行为不变,确定性套件全过;发生在终验之后,涉及路径均被 tests/test_github_backend.py 的 CLI-over-HTTP 用例覆盖)。
- **Spec**:七条标准逐条有本地替身验证(见上);「工作实例不能通过直接连接绕过」以默认画像 OS 级拒绝 + 通道分权实证,网络放开画像的直连可能如实披露为部署边界而非静默;授权语义按合同以 CONFIG 记录 + 运行层交集双重承担。无票外扩张——双网络画像验证与 env_vars 透传修复都是本票语义在真实宿主上的必要闭合,来源已在 manifest/gate-protocol/本 Comments 留档。

#### 遗留事项(真实远端写入验收保留待办)

- **待用户提供**:一个明确授权的测试仓库(准确 host/owner/repo + Issues 写入授权,以及对应的访问令牌来源),用于在真实 GitHub 上重放 acceptance/17 的远端操作段(创建/更新/追加/关系/分流/关闭/切换/交接核对)与真实网络故障下的回读语义;在此之前第 7 条保持未勾、整票不报告通过。真实远端验收时还需一并决定网络画像(默认画像即受控通道;若放开网络须配套凭据隔离,见 W3 发现)。
- 沿用票 01-16:codex exec 不解析 `$` 提及(验收走 app-server 通路);TUI 选择器未做 pty 自动化;令牌为承载凭据,turn 内对模型可见。
- gh CLI 集成路径(经 gh 调用而非 REST)未实现——首版按 REST 直连适配,gh 仅做只读检测;如需 gh 通路属后续增强。
- GitHub 真实 API 的速率分页(>100 Issues)、GraphQL、企业版鉴权差异未覆盖——替身实现了所用 REST 子集,真实仓库重放时如有差异按实际调整。
- 后端切换的 github→local 方向有实现与测试(plan/apply 产出到 emit 目录),未纳入本轮验收主线(AC 面向「项目选择 GitHub Issues 后」)。
- `.tmp/accept-17/` 为受保护验收区(已 gitignore),可整目录删除复跑。

#### 接续位置

票 18(完整包验收)可直接复用:双后端统一接口与 mgs_remote 通道、acceptance/17 的替身与两种网络画像方法(可在 18 的矩阵中引用)、`tests/test_github_backend.py` 的替身传输层模式。真实远端写入验收待办挂在第 7 条——用户提供授权测试仓库后,重放 `acceptance/17-github-issue-workflow/run.sh`(把 `--api-base` 指向真实 API 或去除该接缝)即可收口。

### 2026-09-09 — Triage:独立审查反例影响本票结论

> *This was generated by AI during triage.*

2026-09-09 独立审查(报告:[../../mygamestudio-v1-review-fixes/evidence/review.md](../../mygamestudio-v1-review-fixes/evidence/review.md))在与本票相同的 HEAD 上以探针复现七项相关反例:S1–S6(草稿错仓库发布、回读失败重复评论、迁移后统一读取为空、未验证宣告可达、离线开工隐去缓存、同秒草稿覆盖)、R4(审计失败误报拒绝)及两项核验建议。修复票:[01 记录后端](../../mygamestudio-v1-review-fixes/issues/01-records-backend-review-fixes.md)与[02 运行保障门](../../mygamestudio-v1-review-fixes/issues/02-runtime-gate-review-fixes.md)。在修复批次合入并通过验收前,第 1-6 条的「已验证」结论应按审查降级理解为「样例证据支持但存在反例」;第 7 条真实远端写入验收待办不变。本票勾选状态不动。


### 2026-09-09 — 修复票 01 合入:S1–S6 与两项核验建议已修复并固化

> 本条不改写上方勾选历史,只记录审查反例的处置结果。

2026-09-09 修复批次票 [01](../../mygamestudio-v1-review-fixes/issues/01-records-backend-review-fixes.md) 在本仓实现并验收通过:跨仓库草稿拒绝发布(S1)、评论回读失败保留未知并停止重发(S2,含通道级 uncertain 如实回报)、github→local 迁移四点一致且经 CLI 真实入口验证(S3)、交接可达只认实际执行的检查且探测不带凭据(S4)、开工结果携带缓存元信息(S5)、草稿内容哈希唯一身份不覆盖(S6)、两后端任务核心校验单一实现(核验建议 1,同一畸形任务同判)、安排更新说明三路一致(核验建议 2)。反例先红后绿固化;五静态套件 + 33 驱动回归全过。据此,前述 Triage 评论中「第 1-6 条按反例降级理解」的限制在本 HEAD 解除(样例证据恢复有效);第 7 条真实远端写入验收待办不变(需另行授权)。遗留边界见修复票面:跨仓库草稿显式迁移能力未实现(按票面只做拒绝并如实报告),反向迁移目标恒用默认本地任务根。

### 2026-09-09 — 第 7 条真实远端写入验收完成(用户授权)与重放中发现缺陷的修复

用户授权指令:「建测试仓库,跑票 17 真实远端验收」。执行(全部当日完成):

- **测试仓库**:验收方经 gh 创建一次性私有仓库 `LC-86/mgs-issue-accept-test`(凭据为已登录 gh 的既有令牌,运行时注入进程环境 `MGS_GITHUB_TOKEN`,不落盘、不回显;仓库保留至独立复审可核验后,删除待用户另行指示)。真实写入内容仅为验收任务数据。
- **重放**:`acceptance/17-github-issue-workflow/remote-replay.sh`(新增,确定性 CLI 驱动、0 模型调用)对真实 api.github.com 重放第 4 段远端操作序列:切换清单(未授权拒绝/授权识别)→ apply 创建(身份映射 #1/#2)→ 统一接口回读 → 防重收养(重复创建 01 被收养)→ expected_body_sha256 版本校验(过期拒绝+正确成功)→ 依赖引用(#1 可解析)与父子关系(原生 sub-issues,平台侧可见)→ 分流(标签与正文同步+ready 回读)→ 结果评论(平台侧含任务身份)→ 关闭语义(completed/not_planned)→ handover 不可达如实 → verify 通过;gh 只读交叉核验独立确认终态。**38 PASS / 0 FAIL**,证据 `evidence/real-remote-*`(真实令牌已全量脱敏核对)。
- **边界如实声明**:替身独有的故障注入(超时丢包、断连草稿、sub-issues 开关、通道级 mgs_remote 行为)不在真实远端重放范围,由原替身验收与 tests/test_github_backend.py 固化;真实平台观察两项留痕——①列表索引最终一致(创建后立查少一条,有界重试 2 次后一致,单条读不受影响);②新仓库自带平台默认标签(与项目标签共存)。

**重放发现并修复一处真实缺陷(先红后绿)**:github 后端 CLI `handover` 端到端路径崩溃——`mgs_records.py` 调用 `mgs_github.handover_baselinecheck_item`(不存在;正确名 `handover_baseline_check`),为票 01-fix(S4,提交 ceaacf0)改名漏改 CLI 调用点;崩溃退出码恰为 1,会伪装成「不可达基线」结论(重放首轮即被 JSON 文本检查抓住)。既有测试均直调函数或只测非 github 后端拒绝分支,故五套件全绿未覆盖。修复:调用点改名(一行);回归 `test_cli_github_handover_end_to_end`(经 CLI 真实入口,锚定 JSON 输出+退出码 1+「不可访问/不得宣称」语义)先红后绿。

**回归**:dist 交付包重建(mgs_records.py 变更);五项静态套件 + 33 项驱动回归全过;driver 证据随最终代码刷新。第 7 条勾选,本票整票通过。

### 2026-09-09 — 第二轮独立复审影响本票结论

复审(报告:[../../mygamestudio-v1-review2-fixes/evidence/review-2.md](../../mygamestudio-v1-review2-fixes/evidence/review-2.md))核实:第 7 条真实远端终态与留档一致(gh 只读复算 22 项判据全过)、handover 修复经绿→红→绿变异成立。但新增 SP-1(P1,CONFIG 授权撤销后在途远端写入)、SP-2(评论部分成功误报 deny 且重试重复)、SP-3(草稿跨仓库幂等缺失)三项与运行保障/github 后端相关的新反例。本票勾选状态不动;按复审口径,「整票通过」应理解为「原验收与终态核验成立」,完整远端授权/结果语义闭合以修复批 [review2 票 01/02](../../mygamestudio-v1-review2-fixes/issues/) 完成为准。

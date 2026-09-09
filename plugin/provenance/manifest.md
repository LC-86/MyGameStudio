# mygamestudio 0.18.0 来源与许可追溯

本 manifest 记录最小包(任务票 01-18)随包材料的来源、版本、指纹、许可与适配说明。逐文件指纹的机器可读版本见 [fingerprints.json](fingerprints.json)。

## 包自身

- 名称:`mygamestudio`,版本 `0.18.0`(任务票 18:整包验收与升级行为——不新增业务入口;templates/project/CONFIG.md「外部访问」行占位说明补充 GitHub Issues 写入授权的记录格式 host/owner/repository:issues-write(说明)(任务票 17 合同要求,使新项目从初始化起即可按正确格式记录授权,同时构成 0.17.0→0.18.0 升级验证所需的真实模板演进);修复 fingerprints.json generated_for 自 0.16.0 起未随版本更新的陈旧值;包完整性、十四入口仅显式触发、代表性闭环矩阵、运行保障回归与真实版本升级的验收证据见仓库 acceptance/18-complete-package-acceptance/,交付物(安装包、变更说明、复现步骤、逐项验收结果)见仓库 dist/。原 0.17.0 描述:任务票 17:新增 GitHub Issues 任务后端——Game-Init 识别/选择明确 host/owner/repository 与五类标签映射(核心设计保留本地 Markdown 位置);mgs_github.py 适配器提供同语义读取/列出/创建/安排更新/结果追加/关系与分流/关闭/回读核验,超时先回读再重试防重复创建,离线缓存与未发布草稿标明来源与状态、不静默切本地;后端切换迁移清单(switch-plan/apply)与远端交接基线可达核对(handover);mgs-gate 新增 mgs_remote 受控远端通道(凭据∩任务∩角色∩用途∩CONFIG 仓库级 issues-write 授权,mgsrt_admin set-remote-config 登记通道配置、凭据只经环境变量名注入);远端语义经本地 HTTP 替身验收,真实远端写入仅在明确授权的测试仓库执行(未获授权保留待办)。原 0.16.0 描述:任务票 16:Game-Producer 扩展完整小步闭环组织——收到请求先按仅讨论/已有规格制作/直接专业调用后的状态同步三类入口分类并从合适环节开始(输入充足从中间进入、无需原型跳过原型、不强制每轮执行全部技能、不引入固定阶段门槛),闭环委派与阶段选择(本次制作由 Game-Implement 组织、设计原型保持隔离、未来目标保持粗粒度),直接专业调用结果在统筹下次介入时按事实核对同步(不以作者自报代替),完成与验收判定(约定检查与独立审查完成且无需人判断时可按实际证据标记已完成,需要人的验收保持待验收等待真实反馈,旧版本结果不挪作当前版本通过证明)。原 0.15.0 描述:Game-Producer 由最小入口扩展为覆盖目标变化影响检查与重新分流(识别受影响基线与任务、受影响待执行任务重新分流、原版本下完成事实保留且不自动算作满足新目标)、基线内容指纹核对(版本号未同步的手工内容变更按实质影响处理:仅空白差异判疑似格式修正,不作废既有成果与证据;字符增删判实质变更,交回开发者确认,不自行修改基线)、并发写入占用协调(单写入者、别名与链接不绕过、写入前版本核对不覆盖他人成果、独立资源并行且集成责任明确)与中断恢复(核对当前配置/实际文件/已应用部分/结果与用户后续修改,只继续仍适用剩余工作,不回滚不覆盖用户修改);Game-Spec 新增内容指纹登记纪律(基线头部登记内容指纹与归一指纹双指纹,实质变更递增版本时更新、格式修正不递增版本但同步更新,登记后经统一接口 baseline 回读确认);运行保障新增占用回收接缝 list_locks/reclaim_locks(失联、崩溃或到期后先撤销旧执行能力再回收占用,活跃实例占用不可回收,reclaim 顺序由接缝强制;覆盖 release 流程中断留下的「已释放但仍持有占用」缺口;mgsrt_admin.py 提供 reclaim-locks 子命令并在 status 回读占用);统一接口 mgs_records.py 新增 baseline(核心基线双指纹核对与受影响任务识别,实质变更未同步时退出码 1)。原 0.14.0 描述:新增 Game-Playtest 试玩专业入口——针对明确版本与运行入口制定必要场景并实际执行可用检查(headless 可编程控制、无头冒烟、入口取回),逐项记录输入、观察、结果和证据,结果以 SHA-256 指纹绑定实际测试版本;需要人的手感、审美或体验判断时给出具体试玩任务与回传要求,人工结论只来自实际反馈并保留来源,未反馈、明确通过与需要修改分别表达,Agent 观察不冒充人工反馈;发现缺陷或目标变化输出相应交接,不改产品基线来迁就观察结果;运行状态和测试输出受本次用途限制(写入仅经 mgs-gate 落 evidence/,playtest 用途由策略收窄),真实浏览器 GUI 控制等新增 GUI/MCP 通路不被假定继承本地边界且未经验证保持未就绪;仅制定计划的场景明确标为尚未执行,试玩记录生成不等于验收通过,试玩结果供管理流程决定进度;同票把 game-implement 技能中「尚未实现的专业入口」示例清单与 verification/production 合同包内说明同步为现状(Playtest 已实现);任务票 01-13 建立的其余结构不变,原 0.13.0 描述:新增 Game-Review 独立审查专业入口——以独立于原执行上下文的同专业执行实例检查真实成果的规范与需求符合性,先固定待审版本与完整范围(文件清单与 SHA-256 指纹,含适用的已提交、暂存、未暂存与新建成果,直接读取工作区实际文件,不以 HEAD 或暂存区对比替代,不依赖作者总结),代码按 Standards 与 Spec 两轴独立执行、分别呈现,设计与资源按专业标准及需求符合性检查,每项问题关联具体证据与影响并区分明确规则违背、专业判断与未能检查,审查实例仅写审查记录和证据(项目 evidence/)不修改待审专业成果,修复由对应制作或设计任务执行,修复后针对实际新版本复核且旧结论不挪作新版本通过证明,未实现的运行能力标为覆盖限制且审查报告生成不等于验收通过;同票新增随包合同 internal/contracts/verification.md(审查与试玩合同适配版),并把 game-implement 技能中「尚未实现的专业入口」示例清单同步为现状(Review 已实现,余 Playtest);任务票 01-12 建立的其余结构不变,原 0.12.0 描述:新增 Game-Build 构建运行专业入口(从项目实际配置确定构建导出与运行方式、产物与源版本 SHA-256 对应、构建脚本及子进程在已验证边界内、不把存在文件等同于本次构建成功),此处不再展开;再前历史见 fingerprints.json source 字段)。
- `skills/`、`runtime/`、`records/`、`templates/`(经适配的 README)、`.mcp.json`、`.codex-plugin/plugin.json`、本 provenance 为本项目自有内容,按本项目 MIT 许可发布。
- 设计权威依据:插件设计仓库 `.scratch/mygamestudio-framework/spec.md`,设计入口 SHA-256 `c6ccab8eb140fae4bbd77eb8f7ddcf7f323e7f5c9901519d383dd289ae1e222c`(v1,2026-09-08)。

## internal/contracts/(业务合同,适配版)

| 文件 | 来源 | 适配说明 |
| --- | --- | --- |
| `common.md` | 设计仓库 `contracts/common.md` | 仅将指向未随包设计文档的链接改为文字引用(标注"不随包");补写 writing-for-agents 的包内路径。语义与设计一致 |
| `management.md` | 设计仓库 `contracts/management.md` | 链接适配同上;任务票 04 起 Game-Init 节改链包内协作配置合同与初始化流程;任务票 05 更新文末"包内说明"为已实现新项目初始化与已有项目接手入口;任务票 08 更新"包内说明"为已实现 Game-Plan 拆单入口;任务票 15 更新"包内说明"为已实现 Game-Producer 影响检查/指纹核对/占用协调/中断恢复流程;任务票 16 更新"包内说明"为已实现 Game-Producer 三种入口分类、闭环组织与完成判定流程 |
| `records.md` | 设计仓库 `contracts/records.md` | 仅链接适配 |
| `task-triage.md` | 设计仓库 `proposals/task-triage.md` | 仅链接适配;上游提交核对信息保留原文 |
| `design.md` | 设计仓库 `contracts/design.md` | 任务票 02 新增;链接适配同上;任务票 06 更新:grill-with-docs/wayfinder 改链包内方法路径,文末"包内说明"注明 Game-Design/Game-Spec 最小入口已实现;任务票 07 更新:"包内说明"注明 Game-Prototype 完整原型工作流已实现 |
| `production.md` | 设计仓库 `contracts/production.md` | 任务票 02 新增;链接适配同上;任务票 09 更新文末"包内说明"为已实现 Game-Implement 组织工作流与 Game-Code 完整代码工作流;任务票 10 更新为已实现 Game-Art 视觉资源工作流;任务票 11 更新为已实现 Game-Audio 音频资源工作流;任务票 12 更新为已实现 Game-Build 构建运行工作流;任务票 13 更新"包内说明"中 Game-Review 状态为已实现;任务票 14 更新为 Review 与 Playtest 均已实现(试玩工作流见 verification.md) |
| `verification.md` | 设计仓库 `contracts/verification.md` | 任务票 13 新增;原文仅含指向共同合同的链接(包内同目录可达),无其他外链;任务票 14 更新文末"包内说明"为已实现 Game-Review 与 Game-Playtest 两工作流 |
| `project-configuration.md` | 设计仓库 `contracts/project-configuration.md` | 任务票 04 新增;原文无外链,按包内现状补写文末"包内说明"(仅实现本地 Markdown 后端) |

适配原则:不重写语义;所有改写点限于链接可达性与包内现状声明。更新这些文件时先对照设计仓库当前版本,再更新本 manifest 与 fingerprints.json。

## internal/proposals/(流程与布局,任务票 04 新增)

| 文件 | 来源 | 适配说明 |
| --- | --- | --- |
| `project-onboarding.md` | 设计仓库 `proposals/project-onboarding.md` | 指向未随包 issues 的链接改为文字引用;文末"包内说明"声明已实现范围(任务票 04:新项目 + 本地 Markdown;任务票 05 更新:增加已有项目接手路径) |
| `project-layout.md` | 设计仓库 `proposals/project-layout.md` | 链接适配:运行保障合同改为包内受控写入协议的文字对应;模板入口改链包内 `templates/README.md` |

## templates/(项目模板,任务票 04 新增)

- `README.md`:设计仓库 `templates/README.md` 适配版,仅把指向未随包设计文档的链接改为包内路径或文字引用(标注"不随包")。
- `project/CONFIG.md`:设计仓库对应文件的适配版(任务票 18/0.18.0 起)——「外部连接引用及已确认操作范围」行的占位说明补充 GitHub Issues 写入授权记录格式(`host/owner/repository:issues-write(说明)`,未记录即未授权);这是该模板唯一改动,来源为任务票 17 的协作配置合同与受控写入协议要求,同时也是升级行为验证所需的真实模板演进。其余行与设计仓库一致。
- `project/` 其余文件与 `work/`、`records/`、`evidence/` 下全部模板文件为设计仓库对应文件的**逐字节副本**(设计模板正文本身不含外链),语义以设计仓库为准。

## records/(本地 Markdown 任务后端,本项目自有内容)

- `records/mgs_records.py`:统一回读接口——`load_config`/`list_tasks`/`read_task`/`verify_project`(任务票 04)与 `task_dependencies`/`startable_tasks`(任务票 08:依赖关系解析与循环检测、当前可开工集合,核对未完成依赖/输入/版本/能力并声明可开工不等于已获授权)与 `baseline_report`(任务票 15:核心基线内容指纹与归一指纹双指纹核对,区分一致/指纹未登记/疑似格式修正/实质变更/文件缺失,识别引用旧版本基线的受影响任务并附「原版本完成事实保留」语义,实质变更未同步时 CLI 退出码 1)及其 CLI。对应设计《工作记录合同》「后端接口」与「版本与恢复」一节在本地 Markdown 后端上的实现;只读不写(项目写入一律经 mgs-gate,任务票 04 已记录该边界),首版不支持 GitHub Issues 后端(明确报错,不静默降级)。确定性接缝检查见 `tests/test_records_backend.py`。
- `records/mgs_github.py`(任务票 17 新增):GitHub Issues 后端适配器——仓库坐标与授权范围解析(含糊位置拒绝;issues-write 授权按仓库精确匹配)、Issue 正文沿用 task.md 同格式(身份/执行/验收/进度语义与本地后端一致)、拉取与离线缓存(标注时间与来源)、写操作(创建防重:读前回读+超时回读收养+单次重试;安排更新可带远端正文 SHA-256 版本校验;分流换映射标签并同步正文;结果评论带任务身份前缀并登记结果索引;依赖写为「#Issue号 身份」明确可解析引用;父子关系优先原生 sub-issues、不可用回退正文引用;关闭限定 完成/不再执行/已有成果覆盖 三因,关闭不自动等于验证通过)、未发布草稿与重放发布、后端切换迁移清单与应用(目标侧创建+新 CONFIG 产出,不改写项目文件,身份映射留档,旧记录只读历史)、远端交接基线引用可达核对(未发布本地资料不宣称远端可访问)。传输层可注入(`--api-base`/MGS_GH_API_BASE 指向本地替身);真实远端写入仅在明确授权的测试仓库执行。确定性接缝检查见 `tests/test_github_backend.py`。
- 任务票 15 实现选择(记录供后续票引用):基线内容指纹在**基线文档自身头部**登记双指纹——`内容指纹:sha256:<hex>`(空白敏感)与 `归一指纹:sha256:<hex>`(去空白),由该基线维护角色在版本采纳或格式修正同步时更新(登记方法与统一规范化口径见 `skills/game-spec/SKILL.md` 与 `mgs_records.py`:sha256 槽位以占位替换后计算,登记时先写 64 个 0 再回填);双指纹配合把仅空白差异判为疑似格式修正、字符增删判为实质变更——单一指纹无法区分二者(原始注册内容不可复原)。指纹登记是可选增强:未登记的核心基线报「指纹未登记」,不判漂移。
- 任务票 08 实现选择(记录供后续票引用):任务记录的「依赖」用工作请求中独立字段(以任务身份逐项列出)表达,供 `deps`/`ready` 确定性解析;「所需能力」字段引用 CONFIG 执行条件,命中"尚未就绪的能力"说明即列为不可开工原因;两者按模板实例化规则(包内 `templates/README.md` 第 4 条"专有字段仅在本轮需要时添加")由拆单轮添加,不改动设计模板的逐字节副本;旧记录无这两个字段时视为无依赖、不判 verify 失败。

## internal/protocols/(运行保障接入协议)

| 文件 | 来源 | 适配说明 |
| --- | --- | --- |
| `gate-protocol.md` | 本项目自有内容(任务票 02 新写) | 依据设计《运行保障合同》《工具拦截设计》与 codex 0.151.0 实测机制(会话沙箱 + 插件 MCP 通道)编写;供全部带写入的业务技能条件读取;任务票 11 补充二进制资源载荷 `content_base64` 用法(音频等资源,同一授权交集与审计);任务票 17 增加 `mgs_remote` 受控远端任务操作一节(授权粒度、remote_scope/remote_upstream 拒绝依据、凭据经环境变量注入) |

## runtime/ 与 .mcp.json(运行保障组件,本项目自有内容)

- `runtime/mgs_runtime.py`:受控写入服务核心——执行绑定(令牌哈希登记)、资源策略(角色 ∩ 任务 ∩ 用途 ∩ 实际授权)、路径规范化(含符号链接逃逸拒绝)、预期版本校验、单写入者占用、审计(允许与拒绝均记录)。
- `runtime/mcp_gate.py`:MCP stdio 服务器(`mgs-gate`),业务会话内的唯一写入通道;运行根经 `MGS_RUNTIME_ROOT` 环境变量注入,包内不含绝对路径。
- `runtime/mgsrt_admin.py`:可信调度侧 CLI(策略初始化、实例签发与释放、状态查看),与工作实例通道分离;任务票 13 起实例签发的用途白名单在 production/prototype 之外增加 `review`(独立审查实例签发;实际收窄由策略 `review.restrict` 承担,CLI 只放行策略中已定义的用途名);任务票 15 起 `status` 回读当前写入占用,新增 `reclaim-locks --id`(回收旧实例遗留占用;实例仍活跃时拒绝并退出码 1——须先 release-instance 或等有效期过去)。
- `runtime/mgs_runtime.py`(任务票 15 增量):`list_locks`/`reclaim_locks` 占用回收接缝——按《运行保障合同》「执行结束释放占用」的顺序约束设计:先撤销旧执行能力(release 或到期)再回收,活跃实例回收被拒且占用保持;同时覆盖 release 流程在登记与占用两次落盘之间中断留下的「已释放但仍持有占用」缺口;逐次写入重校验凭据,持续存活的进程在旧授权失效后不能凭旧令牌或旧占用记录继续写入。确定性接缝检查(含真实多进程并发竞争)见 `tests/test_runtime_gate.py`。
- `runtime/mgs_runtime.py` + `runtime/mcp_gate.py`(任务票 17 增量):`remote_record`/`mgs_remote` 受控远端任务操作——会话不直连远端,操作经 mgs-gate 逐次校验「凭据 → 通道配置(channel)→ 项目 CONFIG 后端与仓库级 issues-write 授权(remote_scope)→ 任务授权 → 角色范围 → 用途」,资源粒度 `github://<host>/<owner>/<repo>/issues[/<身份>[/comments]]`;上游不可用失效闭合(remote_upstream),缓存目录可用时保存未发布草稿;凭据从运行根 remote.json 指定的环境变量读取(不落盘、不进项目记录),`mgsrt_admin.py set-remote-config` 登记通道配置(只收环境变量名)。
- `.mcp.json`:`mcpServers` 声明(`cwd: "."` 解析为安装后的插件根;`env_vars` 透传运行根;工具预先批准——拦截由服务端策略承担)。
- 设计对应:组件职责对照设计《运行保障合同》的接口表;不承诺设计中尚未验收的能力(远端服务、GUI 程序、路径竞态全面覆盖等属后续票)。

## internal/methods/(内部通用方法)

- 来源:`github.com/mattpocock/skills`,仓库许可证 MIT(副本见 [licenses/mattpocock-skills-LICENSE.txt](licenses/mattpocock-skills-LICENSE.txt),版权 `Copyright (c) 2026 Matt Pocock`)。
- `writing-for-agents/`(任务票 01 收录):上游 `main` 分支,最近触及该技能目录的提交 `321658273cb1d20b76026717d027d505790106d4`(2026-08-19,"Remove all em-dashes from the repo")。收录文件:`SKILL.md`、`SKILL-MECHANICS.md`、`agents/openai.yaml`,均为逐字节副本,与上游及本机 `~/.agents/skills/writing-for-agents/` 副本指纹一致。
- `grill-with-docs/`、`grilling/`、`domain-modeling/`(含 `CONTEXT-FORMAT.md`、`ADR-FORMAT.md`)、`wayfinder/`、`research/`(任务票 06 收录,共 12 文件):本机 `~/.agents/skills/` 对应目录逐字节副本(diff 为空);指纹与设计仓库《内部通用方法的最小依赖闭包》研究记录的 SHA-256 全部一致。上游提交级核对未在本票重复执行(本机无上游 git 工作副本),以上游仓库当前发布内容为准。
- 适配说明:全部作为包内固定版本方法由业务步骤按条件读取,**不注册为公共技能入口**(不在 `skills/` 下);其 `agents/openai.yaml` 中的界面元数据随文件保留,不产生注册效果。按依赖闭包研究的适配结论执行内部加载:业务入口使用宿主已核实的调用契约,内部方法通过包内路径引用加载;domain-modeling 的 CONTEXT/ADR 默认落点与 wayfinder 的 tracker/研究分支落点,由 Game-Design/Game-Spec 解析到项目 CONFIG 映射的位置并经 mgs-gate 写入,不自行改变治理文件、专业文档归属或 Git 授权。
- 选择理由(任务票 06 记录):设计技能合同指定 Game-Design 局部需求复用 grill-with-docs、多项未决问题复用 wayfinder(其研究分支配合 research,grill-with-docs 组合 grilling 与 domain-modeling),故设计入口随包提供该闭包。

## 已核对事项

- 上游仓库许可证(MIT)与许可文本已实际拉取核对;本地副本与上游 `main` 逐字节一致(diff 为空)。
- 设计入口指纹与 v1 实施范围声明的指纹一致。
- 包内文件不引用开发机绝对路径(由 `tests/test_plugin_package.py` 检查)。

## 未包含

- 其余条件参考(prototype 三件套、code-review):按依赖闭包研究属可选固定参考,当前已实现入口不引用它们;原型验证走已实现的 Game-Prototype 入口。
- `to-tickets`、`to-spec`、`implement`:按包合同(Game-Spec、Game-Plan、Game-Implement 使用游戏侧独立协议,原方法仅作方法来源)与依赖闭包研究不随包。任务票 08 实现 Game-Plan 时未收录 `to-tickets`,游戏侧拆单协议(小成果可独立核验、真实依赖、Agent/Human 分工、项目目录映射、不用默认 ready-for-agent)直接写在 `skills/game-plan/SKILL.md` 及其包内依据中。
- 设计文档 proposals/research/issues 的其余文件:不在包内,合同适配版中以"不随包"文字引用。

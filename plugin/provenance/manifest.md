# mygamestudio 1.0.0 来源与许可追溯

本 manifest 记录最小包随包材料的来源、版本、指纹、许可与适配说明。逐文件指纹的机器可读版本见 [fingerprints.json](fingerprints.json)。各文件的逐版本适配历程不再在本文件逐条累加;当前适配事实见下表,历史见 fingerprints.json 的 source 字段与仓库 acceptance/ 各票证据。

## 包自身

- 名称:`mygamestudio`,版本 `1.0.0`。十四个业务入口(状态/统筹/初始化/计划/设计讨论/规格整理/隔离原型/制作组织/代码/视觉/音频/构建/独立审查/试玩)均仅显式触发;任务后端支持本地 Markdown 与 GitHub Issues;项目写入统一经 `mgs-gate` 受控通道(角色 ∩ 任务 ∩ 用途 ∩ 实际授权);共同执行规则、受控写入协议与结果字段三处共同权威各有唯一维护位置。交付物见仓库 `dist/`,验收证据见 `acceptance/`。
- `skills/`、`runtime/`、`records/`、`templates/`(经适配的 README)、`.mcp.json`、`.codex-plugin/plugin.json`、本 provenance 为本项目自有内容,按本项目 MIT 许可发布。
- 设计权威依据:插件设计仓库 `.scratch/mygamestudio-framework/spec.md`,设计入口 SHA-256 `c6ccab8eb140fae4bbd77eb8f7ddcf7f323e7f5c9901519d383dd289ae1e222c`(v1,2026-09-08)。

## internal/contracts/(业务合同,适配版)

| 文件 | 来源 | 适配说明 |
| --- | --- | --- |
| `common.md` | 设计仓库 `contracts/common.md` | 链接改为文字引用(标注"不随包");含《共同规则的权威位置》《共同执行规则(唯一权威)》与三处权威引用锚点、"未参与者可独立读取"报告标准;语义与设计一致 |
| `management.md` | 设计仓库 `contracts/management.md` | 链接适配同上;Game-Init 节改链包内协作配置合同与初始化流程;文末"包内说明"为已实现入口现状 |
| `records.md` | 设计仓库 `contracts/records.md` | 仅链接适配 |
| `task-triage.md` | 设计仓库 `proposals/task-triage.md` | 仅链接适配;上游提交核对信息保留原文 |
| `design.md` | 设计仓库 `contracts/design.md` | 链接适配同上;grill-with-docs/wayfinder 改链包内方法路径;文末"包内说明"为 Game-Design/Game-Spec/Game-Prototype 已实现 |
| `production.md` | 设计仓库 `contracts/production.md` | 链接适配同上;文末"包内说明"为制作类入口(Implement/Code/Art/Audio/Build/Review/Playtest)已实现 |
| `verification.md` | 设计仓库 `contracts/verification.md` | 原文仅含指向共同合同的链接(包内同目录可达);文末"包内说明"为 Game-Review 与 Game-Playtest 已实现 |
| `project-configuration.md` | 设计仓库 `contracts/project-configuration.md` | 原文无外链;按包内现状补写文末"包内说明"(本地 Markdown 与 GitHub Issues 双后端) |

适配原则:不重写语义;所有改写点限于链接可达性与包内现状声明。更新这些文件时先对照设计仓库当前版本,再更新本 manifest 与 fingerprints.json。

## internal/proposals/(流程与布局)

| 文件 | 来源 | 适配说明 |
| --- | --- | --- |
| `project-onboarding.md` | 设计仓库 `proposals/project-onboarding.md` | 指向未随包 issues 的链接改为文字引用;文末"包内说明"声明已实现范围(新项目 + 已有项目接手,本地 Markdown 后端) |
| `project-layout.md` | 设计仓库 `proposals/project-layout.md` | 链接适配:运行保障合同改为包内受控写入协议的文字对应;模板入口改链包内 `templates/README.md` |

## templates/(项目模板)

- `README.md`:设计仓库 `templates/README.md` 适配版,仅把指向未随包设计文档的链接改为包内路径或文字引用(标注"不随包")。
- `project/CONFIG.md`:设计仓库对应文件的适配版——「外部连接引用及已确认操作范围」行的占位说明补充 GitHub Issues 写入授权记录格式(`host/owner/repository:issues-write(说明)`,未记录即未授权);其余行与设计仓库一致。
- `work/result.md`:设计仓库对应文件的适配版——在既有字段列表前增补《结果字段》小节标题,作为共同权威锚点,字段内容与结构未改。
- `project/` 其余文件与 `work/`、`records/`、`evidence/` 下其余模板文件为设计仓库对应文件的**逐字节副本**(设计模板正文本身不含外链),语义以设计仓库为准。

## records/(本地 Markdown 与 GitHub 任务后端,本项目自有内容)

- `records/mgs_records.py`:统一回读接口——`load_config`/`list_tasks`/`read_task`/`verify_project` 与 `task_dependencies`/`startable_tasks`(依赖关系解析与循环检测、当前可开工集合;核对未完成依赖/输入/版本/能力并声明可开工不等于已获授权)与 `baseline_report`(核心基线内容指纹与归一指纹双指纹核对,区分一致/指纹未登记/疑似格式修正/实质变更/文件缺失,识别引用旧版本基线的受影响任务并附「原版本完成事实保留」语义,实质变更未同步时 CLI 退出码 1)。本模块组织本地 Markdown 与 GitHub Issues 双后端读取,不提供本地项目写入(项目写入经 mgs-gate)。CLI 参数解析、输出投影与退出码由 `records/mgs_records_cli.py` 承担,旧脚本入口保持。确定性接缝检查见 `tests/test_records_backend.py`。
- `records/mgs_github.py`:GitHub Issues 后端适配器——仓库坐标与授权范围解析(含糊位置拒绝;issues-write 授权按仓库精确匹配)、Issue 正文沿用 task.md 同格式(身份/执行/验收/进度语义与本地后端一致)、拉取与离线缓存(标注时间与来源)、写操作(创建防重:读前回读+超时回读收养+单次重试;安排更新可带远端正文 SHA-256 版本校验;分流换映射标签并同步正文;结果评论带任务身份前缀并登记结果索引;依赖写为「#Issue号 身份」明确可解析引用;父子关系优先原生 sub-issues、不可用回退正文引用;关闭限定 完成/不再执行/已有成果覆盖 三因,关闭不自动等于验证通过)、未发布草稿与重放发布、后端切换迁移清单与应用(目标侧创建+新 CONFIG 产出,不改写项目文件,身份映射留档,旧记录只读历史)、远端交接基线引用可达核对(未发布本地资料不宣称远端可访问)。传输层可注入(`--api-base`/MGS_GH_API_BASE 指向本地替身);真实远端写入仅在明确授权的测试仓库执行。确定性接缝检查见 `tests/test_github_backend.py`。
- 基线内容指纹实现选择:在基线文档自身头部登记双指纹——`内容指纹:sha256:<hex>`(空白敏感)与 `归一指纹:sha256:<hex>`(去空白),由该基线维护角色在版本采纳或格式修正同步时更新(登记方法与统一规范化口径见 `skills/game-spec/SKILL.md` 与 `mgs_records.py`:sha256 槽位以占位替换后计算,登记时先写 64 个 0 再回填);双指纹配合把仅空白差异判为疑似格式修正、字符增删判为实质变更。未登记的核心基线报「指纹未登记」,不判漂移。
- 任务记录字段实现选择:「依赖」用工作请求中独立字段(以任务身份逐项列出)表达,供 `deps`/`ready` 确定性解析;「所需能力」字段引用 CONFIG 执行条件,命中"尚未就绪的能力"说明即列为不可开工原因;两者按模板实例化规则由拆单轮添加,不改动设计模板的逐字节副本;旧记录无这两个字段时视为无依赖、不判 verify 失败。

## internal/protocols/(运行保障接入协议)

| 文件 | 来源 | 适配说明 |
| --- | --- | --- |
| `gate-protocol.md` | 本项目自有内容 | 依据设计《运行保障合同》《工具拦截设计》与 codex 0.151.0 实测机制(会话沙箱 + 插件 MCP 通道)编写;含两层拦截、`mgs_write`/`mgs_remote` 工具、文本与 base64 载荷、拒绝依据速查、《执行凭据》《越界探针(边界核对)》等小节,是业务入口受控写入与凭据处理的唯一权威 |

## runtime/ 与 .mcp.json(运行保障组件,本项目自有内容)

- `runtime/mgs_runtime.py`:受控写入服务核心与门面——执行绑定(令牌哈希登记)、资源策略(角色 ∩ 任务 ∩ 用途 ∩ 实际授权)、路径规范化(含符号链接逃逸拒绝)、预期版本校验、单写入者占用、审计(允许与拒绝均记录);保留公开接缝与私有状态接缝(故障注入点),本地事务、执行登记与受控远端操作分别委派下列职责文件。
- `runtime/mgs_gate_registry.py`:执行登记与策略状态——策略读取/结构校验/指纹、实例登记签发与撤销、写入占用读取/释放/回收、审计追加与唯一服务锁;撤销、签发、回收与写入共用同一把锁,「锁内重读」与「无审计则无生效写入」只有一处实现。
- `runtime/mgs_local_write.py`:本地受控写入的完整事务——策略解释(路径模式匹配、角色与用途交集、用途条目缺失的失效闭合)、路径身份(项目根逃逸拒绝、O_NOFOLLOW 逐组件锚定、临时文件落盘、权限位保留、失败回滚)以及锁前预检与锁内最终核对/落盘的完整顺序;授权交集 `grant_denial` 与远端共用。
- `runtime/mgs_remote_write.py`:受控远端任务操作的完整事务——远端通道配置与项目 CONFIG 核对、授权交集、锁内最终身份/策略/CONFIG/授权复核、写入意图先于执行、远端动作执行与结果审计;锁内重读、网络期间持锁语义、已发生远端结果的如实披露与「不确定/部分成功/未发布草稿」的区分保持不变。
- `runtime/mcp_gate.py`:MCP stdio 服务器(`mgs-gate`),业务会话内的唯一写入通道;运行根经 `MGS_RUNTIME_ROOT` 环境变量注入,包内不含绝对路径;`remote_record`/`mgs_remote` 受控远端操作经此暴露。
- `runtime/mgsrt_admin.py`:可信调度侧 CLI(策略初始化、实例签发与释放、状态查看、`reclaim-locks` 占用回收、`set-remote-config` 登记远端通道),与工作实例通道分离;`set-remote-config` 只登记凭据环境变量名,不落盘凭据。
- `.mcp.json`:`mcpServers` 声明(`cwd: "."` 解析为安装后的插件根;`env_vars` 透传运行根;工具预先批准——拦截由服务端策略承担)。
- 设计对应:组件职责对照设计《运行保障合同》的接口表;不承诺设计中尚未验收的能力(远端服务、GUI 程序、路径竞态全面覆盖等属后续票)。

## internal/methods/(内部通用方法)

- 来源:`github.com/mattpocock/skills`,仓库许可证 MIT(副本见 [licenses/mattpocock-skills-LICENSE.txt](licenses/mattpocock-skills-LICENSE.txt),版权 `Copyright (c) 2026 Matt Pocock`)。
- `writing-for-agents/`:上游 `main` 分支,最近触及该技能目录的提交 `321658273cb1d20b76026717d027d505790106d4`(2026-08-19,"Remove all em-dashes from the repo")。收录文件:`SKILL.md`、`SKILL-MECHANICS.md`、`agents/openai.yaml`,均为逐字节副本,与上游及本机 `~/.agents/skills/writing-for-agents/` 副本指纹一致。
- `grill-with-docs/`、`grilling/`、`domain-modeling/`(含 `CONTEXT-FORMAT.md`、`ADR-FORMAT.md`)、`wayfinder/`、`research/`(共 12 文件):本机 `~/.agents/skills/` 对应目录逐字节副本(diff 为空);指纹与设计仓库《内部通用方法的最小依赖闭包》研究记录的 SHA-256 全部一致。上游提交级核对未重复执行(本机无上游 git 工作副本),以上游仓库当前发布内容为准。
- 适配说明:全部作为包内固定版本方法由业务步骤按条件读取,**不注册为公共技能入口**(不在 `skills/` 下);其 `agents/openai.yaml` 中的界面元数据随文件保留,不产生注册效果。业务入口使用宿主已核实的调用契约,内部方法通过包内路径引用加载;domain-modeling 的 CONTEXT/ADR 默认落点与 wayfinder 的 tracker/研究分支落点,由 Game-Design/Game-Spec 解析到项目 CONFIG 映射的位置并经 mgs-gate 写入,不自行改变治理文件、专业文档归属或 Git 授权。
- 选择理由:设计技能合同指定 Game-Design 局部需求复用 grill-with-docs、多项未决问题复用 wayfinder(其研究分支配合 research,grill-with-docs 组合 grilling 与 domain-modeling),故设计入口随包提供该闭包。

## 已核对事项

- 上游仓库许可证(MIT)与许可文本已实际拉取核对;本地副本与上游 `main` 逐字节一致(diff 为空)。
- 设计入口指纹与 v1 实施范围声明的指纹一致。
- 包内文件不引用开发机绝对路径(由 `tests/test_plugin_package.py` 检查)。

## 未包含

- 其余条件参考(prototype 三件套、code-review):按依赖闭包研究属可选固定参考,当前已实现入口不引用它们;原型验证走已实现的 Game-Prototype 入口。
- `to-tickets`、`to-spec`、`implement`:按包合同(Game-Spec、Game-Plan、Game-Implement 使用游戏侧独立协议,原方法仅作方法来源)与依赖闭包研究不随包;游戏侧拆单协议(小成果可独立核验、真实依赖、Agent/Human 分工、项目目录映射、不用默认 ready-for-agent)直接写在 `skills/game-plan/SKILL.md` 及其包内依据中。
- 设计文档 proposals/research/issues 的其余文件:不在包内,合同适配版中以"不随包"文字引用。

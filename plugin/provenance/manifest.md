# mygamestudio 0.5.0 来源与许可追溯

本 manifest 记录最小包(任务票 01-05)随包材料的来源、版本、指纹、许可与适配说明。逐文件指纹的机器可读版本见 [fingerprints.json](fingerprints.json)。

## 包自身

- 名称:`mygamestudio`,版本 `0.5.0`(任务票 05:Game-Init 扩展已有项目接手路径——只读现状分析、复用与补齐、混合文档拆分、中断恢复/重复运行与模板升级;任务票 04 建立的其余结构不变)。
- `skills/`、`runtime/`、`records/`、`templates/`(经适配的 README)、`.mcp.json`、`.codex-plugin/plugin.json`、本 provenance 为本项目自有内容,按本项目 MIT 许可发布。
- 设计权威依据:插件设计仓库 `.scratch/mygamestudio-framework/spec.md`,设计入口 SHA-256 `c6ccab8eb140fae4bbd77eb8f7ddcf7f323e7f5c9901519d383dd289ae1e222c`(v1,2026-09-08)。

## internal/contracts/(业务合同,适配版)

| 文件 | 来源 | 适配说明 |
| --- | --- | --- |
| `common.md` | 设计仓库 `contracts/common.md` | 仅将指向未随包设计文档的链接改为文字引用(标注"不随包");补写 writing-for-agents 的包内路径。语义与设计一致 |
| `management.md` | 设计仓库 `contracts/management.md` | 链接适配同上;任务票 04 起 Game-Init 节改链包内协作配置合同与初始化流程;任务票 05 更新文末"包内说明"为已实现新项目初始化与已有项目接手入口 |
| `records.md` | 设计仓库 `contracts/records.md` | 仅链接适配 |
| `task-triage.md` | 设计仓库 `proposals/task-triage.md` | 仅链接适配;上游提交核对信息保留原文 |
| `design.md` | 设计仓库 `contracts/design.md` | 任务票 02 新增;链接适配同上;文末"包内说明"注明仅实现 Game-Prototype 最小入口 |
| `production.md` | 设计仓库 `contracts/production.md` | 任务票 02 新增;链接适配同上;文末"包内说明"注明仅实现 Game-Code 最小入口 |
| `project-configuration.md` | 设计仓库 `contracts/project-configuration.md` | 任务票 04 新增;原文无外链,按包内现状补写文末"包内说明"(仅实现本地 Markdown 后端) |

适配原则:不重写语义;所有改写点限于链接可达性与包内现状声明。更新这些文件时先对照设计仓库当前版本,再更新本 manifest 与 fingerprints.json。

## internal/proposals/(流程与布局,任务票 04 新增)

| 文件 | 来源 | 适配说明 |
| --- | --- | --- |
| `project-onboarding.md` | 设计仓库 `proposals/project-onboarding.md` | 指向未随包 issues 的链接改为文字引用;文末"包内说明"声明已实现范围(任务票 04:新项目 + 本地 Markdown;任务票 05 更新:增加已有项目接手路径) |
| `project-layout.md` | 设计仓库 `proposals/project-layout.md` | 链接适配:运行保障合同改为包内受控写入协议的文字对应;模板入口改链包内 `templates/README.md` |

## templates/(项目模板,任务票 04 新增)

- `README.md`:设计仓库 `templates/README.md` 适配版,仅把指向未随包设计文档的链接改为包内路径或文字引用(标注"不随包")。
- `project/`、`work/`、`records/`、`evidence/` 下全部模板文件为设计仓库对应文件的**逐字节副本**(设计模板正文本身不含外链),语义以设计仓库为准。

## records/(本地 Markdown 任务后端,本项目自有内容)

- `records/mgs_records.py`:统一回读接口——`load_config`/`list_tasks`/`read_task`/`verify_project` 及其 CLI。对应设计《工作记录合同》「后端接口」在本地 Markdown 后端上的最小实现;只读不写(项目写入一律经 mgs-gate),首版不支持 GitHub Issues 后端(明确报错,不静默降级)。确定性接缝检查见 `tests/test_records_backend.py`。

## internal/protocols/(运行保障接入协议)

| 文件 | 来源 | 适配说明 |
| --- | --- | --- |
| `gate-protocol.md` | 本项目自有内容(任务票 02 新写) | 依据设计《运行保障合同》《工具拦截设计》与 codex 0.151.0 实测机制(会话沙箱 + 插件 MCP 通道)编写;供全部带写入的业务技能条件读取 |

## runtime/ 与 .mcp.json(运行保障组件,本项目自有内容)

- `runtime/mgs_runtime.py`:受控写入服务核心——执行绑定(令牌哈希登记)、资源策略(角色 ∩ 任务 ∩ 用途 ∩ 实际授权)、路径规范化(含符号链接逃逸拒绝)、预期版本校验、单写入者占用、审计(允许与拒绝均记录)。
- `runtime/mcp_gate.py`:MCP stdio 服务器(`mgs-gate`),业务会话内的唯一写入通道;运行根经 `MGS_RUNTIME_ROOT` 环境变量注入,包内不含绝对路径。
- `runtime/mgsrt_admin.py`:可信调度侧 CLI(策略初始化、实例签发与释放、状态查看),与工作实例通道分离。
- `.mcp.json`:`mcpServers` 声明(`cwd: "."` 解析为安装后的插件根;`env_vars` 透传运行根;工具预先批准——拦截由服务端策略承担)。
- 设计对应:组件职责对照设计《运行保障合同》的接口表;不承诺设计中尚未验收的能力(远端服务、GUI 程序、路径竞态全面覆盖等属后续票)。

## internal/methods/writing-for-agents/(内部通用方法)

- 来源:`github.com/mattpocock/skills`,仓库许可证 MIT(副本见 [licenses/mattpocock-skills-LICENSE.txt](licenses/mattpocock-skills-LICENSE.txt),版权 `Copyright (c) 2026 Matt Pocock`)。
- 版本:上游 `main` 分支,最近触及该技能目录的提交 `321658273cb1d20b76026717d027d505790106d4`(2026-08-19,"Remove all em-dashes from the repo")。
- 收录文件:`SKILL.md`、`SKILL-MECHANICS.md`、`agents/openai.yaml`,均为逐字节副本,与上游及本机 `~/.agents/skills/writing-for-agents/` 副本指纹一致(见 fingerprints.json)。
- 适配说明:作为包内固定版本方法由业务步骤按条件读取,**不注册为公共技能入口**(不在 `skills/` 下);其 `agents/openai.yaml` 中的界面元数据随文件保留,不产生注册效果。`SKILL-MECHANICS.md` 中关于"user-invoked Skill 不能被其他 Skill 调用"的客户端机械规则,按设计《内部通用方法的最小依赖闭包》的适配结论执行:业务入口使用宿主已核实的调用契约,内部方法通过包内路径引用加载。
- 选择理由(任务票 01 记录):共同合同要求文档写入步骤加载 writing-for-agents;Game-Status 的合同写入路径(同步管理记录)以其为必需方法,故最小包先随包提供该方法。

## 已核对事项

- 上游仓库许可证(MIT)与许可文本已实际拉取核对;本地副本与上游 `main` 逐字节一致(diff 为空)。
- 设计入口指纹与 v1 实施范围声明的指纹一致。
- 包内文件不引用开发机绝对路径(由 `tests/test_plugin_package.py` 检查)。

## 未包含

- 其余五项通用方法(wayfinder、grilling、domain-modeling、research、grill-with-docs)及条件参考(prototype、code-review):按依赖闭包研究属后续票按需随包,当前最小包的已实现入口不引用它们。
- 设计文档 proposals/research/issues 的其余文件:不在包内,合同适配版中以"不随包"文字引用。

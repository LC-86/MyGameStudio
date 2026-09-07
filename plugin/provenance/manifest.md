# mygamestudio 0.1.0 来源与许可追溯

本 manifest 记录最小包(任务票 01)随包材料的来源、版本、指纹、许可与适配说明。逐文件指纹的机器可读版本见 [fingerprints.json](fingerprints.json)。

## 包自身

- 名称:`mygamestudio`,版本 `0.1.0`(任务票 01 首个最小包)。
- `skills/`、`.codex-plugin/plugin.json`、本 provenance 为本项目自有内容,按本项目 MIT 许可发布。
- 设计权威依据:插件设计仓库 `.scratch/mygamestudio-framework/spec.md`,设计入口 SHA-256 `c6ccab8eb140fae4bbd77eb8f7ddcf7f323e7f5c9901519d383dd289ae1e222c`(v1,2026-09-08)。

## internal/contracts/(业务合同,适配版)

| 文件 | 来源 | 适配说明 |
| --- | --- | --- |
| `common.md` | 设计仓库 `contracts/common.md` | 仅将指向未随包设计文档的链接改为文字引用(标注"不随包");补写 writing-for-agents 的包内路径。语义与设计一致 |
| `management.md` | 设计仓库 `contracts/management.md` | 链接适配同上;文末追加"包内说明"注明当前最小包仅实现 Game-Status 只读检查 |
| `records.md` | 设计仓库 `contracts/records.md` | 仅链接适配 |
| `task-triage.md` | 设计仓库 `proposals/task-triage.md` | 仅链接适配;上游提交核对信息保留原文 |

适配原则:不重写语义;所有改写点限于链接可达性与包内现状声明。更新这些文件时先对照设计仓库当前版本,再更新本 manifest 与 fingerprints.json。

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

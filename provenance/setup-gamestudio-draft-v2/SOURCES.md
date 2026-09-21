# 来源与草案状态

本文件供维护者追溯，不是执行 setup 时必须读取的流程资料。

这是 setup-gamestudio 的第二版讨论草案（草案修订号，不是 MyGameStudio 产品版本号）。在本会话上一份 setup-gamestudio-draft.zip 上增补资源管理与制作流程。尚未写入 MyGameStudio 仓库、发布或完成真实客户端行为验收。

方法和模板结构参考 LC-86/mattpocockskills 的固定提交：
`c55ee46073ed923f86ce59a5eb3b6d895095d1b7`。
原始方法归 Matt Pocock，原始 MIT 许可保存在 UPSTREAM-LICENSE.txt；本草案未改写上游署名。

参考文件：
- skills/engineering/setup-matt-pocock-skills/SKILL.md
- skills/engineering/setup-matt-pocock-skills/issue-tracker-github.md
- skills/engineering/setup-matt-pocock-skills/issue-tracker-gitlab.md
- skills/engineering/setup-matt-pocock-skills/issue-tracker-local.md
- skills/engineering/setup-matt-pocock-skills/triage-labels.md
- skills/engineering/setup-matt-pocock-skills/domain.md

固定版本来源：
https://github.com/LC-86/mattpocockskills/tree/c55ee46073ed923f86ce59a5eb3b6d895095d1b7/skills/engineering/setup-matt-pocock-skills

主要改写：普通文档配置、复用已有来源、按需增加游戏资料指针、避免全套空文档、区分配置完成与工具可用、区分分流与工作状态、保持无运行时依赖。模板不绑定其他尚未确定的新技能名。

标准与元数据参考（检索于 2026-09-21）：
https://agentskills.io/specification
https://code.claude.com/docs/en/skills
https://developers.openai.com/zh-Hans/docs/build-skills

本草案包含 Claude 的 disable-model-invocation 与 Codex 的 allow_implicit_invocation 声明；其他宿主的实际加载与执行效果未验证。这些声明不是权限沙箱。

## 本次增补依据

本次资源管理补充来自当前对话已讨论的方案：工程与制作区按用途分开；候选筛选后再接入工程；保留可编辑源文件及依赖、重要源版本和对应关系；工程与源文件分别可恢复；提交前检查、备份状态披露及明确授权的清理。示例目录和 r001 / r002 不是强制存储协议。

新增内容为拟议项目规则，不宣称行业统一标准，也没有在用户工程中执行。未在本次重写中重新核实上面的外部文档；它们保留为第一版的来源记录。实际实施引擎忽略规则、LFS 操作或存储访问时，应按当时工具和项目情况确认。

静态校验与尚未完成的行为验收见 UPDATE-NOTES.md。上游许可证保持原始字节不变。

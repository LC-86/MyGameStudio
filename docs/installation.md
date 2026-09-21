# 安装

MyGameStudio 3.0.0 是一个原生 Agent Skills 仓库。安装由官方 `skills` CLI 完成，本仓库不提供安装器、不发布 npm 包、不构建 tar 包，也不维护各 AI 开发工具的目录转换。

## 安装

```bash
# 发现并选择技能
npx skills@latest add LC-86/MyGameStudio

# 只列出可发现技能，不安装
npx skills@latest add LC-86/MyGameStudio --list

# 完整安装这套互相协作的技能（推荐）
npx skills@latest add LC-86/MyGameStudio --skill '*'
```

具体安装到哪个目录由官方 CLI 与你的选择决定。`@latest` 指 `skills` CLI 的版本，不代表自动选择 MyGameStudio 的 `v3.0.0` 标签；默认分支尚未更新到 V3 时，远端命令安装到的不是本版本。

推荐完整安装 20 项。这套技能互相引用共享方法，选择安装会缺少依赖，见 [dependencies.md](dependencies.md)。

## 安装目标与文件形态

本仓库在 `skills` CLI **1.7.0** 上实测的行为（完整证据见 [validation-v3.md](validation-v3.md)）：

- `--agent universal` 安装到项目的 `.agents/skills/<技能名>/`。这是本库推荐的目标。
- 只指定一个宿主时，CLI 直接把真实文件复制进该宿主目录（例如 `.claude/skills/`），不生成 `.agents/`。
- 指定两个及以上宿主时，正本落在 `.agents/skills/`，各宿主目录是指向正本的符号链接。加 `--copy` 则在每个宿主目录各生成一份独立真实副本。
- `-g` / `--global` 写入用户主目录下的宿主技能目录。本项目不使用它，也不建议对真实用户环境使用。
- 项目级安装会生成 `skills-lock.json`，记录来源、`sourceType` 与内容哈希；git 来源还会记录 `ref` 与 `sourceUrl`，但不记录提交 SHA。
- 仓库根的 `LICENSE` 与 `THIRD_PARTY_NOTICES.md` **不会**随技能安装，只有技能目录内的文件会被复制。这是每项技能都自带 `LICENSE` 通知的原因。

## 选择安装的语法

多项技能用空格分隔，`'*'` 表示全部。逗号分隔不生效：

```bash
npx skills@latest add LC-86/MyGameStudio --skill implement-gamestudio review-gamestudio docs-gamestudio tasks-gamestudio
```

CLI 不解析技能间依赖，选中的技能各自独立安装。必须一起安装的集合见 [dependencies.md](dependencies.md)。

## 固定版本安装

CLI 的来源解析接受 `owner/repo@<ref>`，`<ref>` 会作为 git 引用用于克隆，因此 `add LC-86/MyGameStudio@v3.0.0` 在语法上成立。本项目**没有**端到端验证过固定标签的远端安装，不要在文档或脚本中把它写成已验证用法。

## 安装后确认

确认三件事，不要只看命令是否退出成功：

1. 技能出现在宿主实际读取的技能目录中，名称是 20 项 `-gamestudio` 名称。
2. 每项技能目录内有 `SKILL.md`、它引用的 `references/` 或 `templates/`，以及一份 `LICENSE` 通知。
3. 共享方法可达：`docs-gamestudio/references/` 下的三份参考与 `tasks-gamestudio/references/task-responsibility.md` 存在，且其他技能的相对引用能解析到它们。

## 更新与卸载

更新按官方 CLI 的更新方式执行。卸载就是从宿主的技能目录中移除这 20 个技能目录，没有注册表、后台服务或专用运行层需要清理。

V3 不维护自建安装命令，因此也不提供自建的卸载命令。

## 从 2.0.2 插件版本切换

2.0.2 是多客户端插件包，安装方式与 V3 完全不同。旧命令已全部退出，切换步骤与能力差异见 [migration-v3.md](migration-v3.md)。

## 许可

每个技能目录内的 `LICENSE` 随技能一起安装，包含 MIT 许可全文、两条版权声明与该技能的上游来源说明。这样按单项技能安装时，接收方仍能看到完整的版权与许可通知，而不必依赖没有一起安装的仓库根 `LICENSE`。

仓库层面的许可与第三方说明见 [LICENSE](../LICENSE) 与 [THIRD_PARTY_NOTICES.md](../THIRD_PARTY_NOTICES.md)。

## 本仓库的实际验证状态

哪些安装路径已经真实测试、哪些未运行，见 [validation-v3.md](validation-v3.md)。本页描述的是目标用法，不等于所有宿主都已验证。

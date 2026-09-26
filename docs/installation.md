# 安装

MyGameStudio 3.0.3（未发布，未打标签、未发布 Release）是一个原生 Agent Skills 仓库，仓库内共 20 项技能：8 项用户入口、12 项按需方法。安装由官方 `skills` CLI 完成，本仓库不提供安装器、不发布 npm 包、不构建 tar 包，也不维护各 AI 开发工具的目录转换。

完整使用需要**两个独立来源**：官方 [`mattpocock/skills`](https://github.com/mattpocock/skills) 提供的共同写作方法 `writing-for-agents`，以及本仓库的 20 项技能。MyGameStudio 不再分发、不再镜像这份共同方法，也不提供来源切换或安装核验工具；两者可以装在同一范围，也可以分处用户级与项目级，由你决定。

## 完整安装：两步

第一步装外部共同方法，第二步装 MyGameStudio 20 项。**已经能从官方来源取得 `writing-for-agents` 时只跳过第一步**，第二步照常执行。共同方法不是可选能力：正式资料、结论与交接按它的方法表达；缺少它时技能会报告缺口，只继续不依赖它的部分，也不会凭名称模仿后声称完成。

用户级命令排在前面，是本库推荐的范围；项目级命令作为替代，必须在**目标项目根目录**执行。

```bash
# 用户级：共同方法（已有时跳过）
npx skills@latest add mattpocock/skills --skill writing-for-agents --agent universal --copy -g -y

# 用户级：MyGameStudio 20 项
npx skills@latest add LC-86/MyGameStudio --skill '*' --agent universal --copy -g -y

# 项目级：在目标项目根目录执行
npx skills@latest add mattpocock/skills --skill writing-for-agents --agent universal --copy -y
npx skills@latest add LC-86/MyGameStudio --skill '*' --agent universal --copy -y
```

只看不装，或先挑选再装：

```bash
# 发现并选择技能
npx skills@latest add LC-86/MyGameStudio

# 只列出可发现技能，不安装
npx skills@latest add LC-86/MyGameStudio --list
```

`@latest` 指 `skills` CLI 的版本，不代表自动选择 MyGameStudio 的某个标签：远端命令取的是仓库**默认分支**的内容，标签与默认分支是两件事。当前源码树是 20 项；`v3.0.2` 标签固定包含 21 项，`v3.0.1` 标签固定包含 20 项，历史身份不因本版收缩而改写。

上述命令面向跟随 CLI 最新版的用户；`-g`、`-y`、`--agent universal`、`--copy`、项目级与用户级锁文件的当前行为只在 `skills` CLI **1.7.0** 上核实，其它 CLI 版本请以实际输出为准。

推荐完整安装 20 项。这套技能互相引用共享方法，选择安装会缺少依赖，见 [dependencies.md](dependencies.md)。

## 安装目标与文件形态

本仓库在 `skills` CLI **1.7.0** 上实测的行为（完整证据见 [validation-v3.md](validation-v3.md)）：

- `--agent universal` 安装到项目的 `.agents/skills/<技能名>/`。这是本库推荐的项目级目标。
- `-g` / `--global` 写入用户主目录：技能落在 `$HOME/.agents/skills/<技能名>/`，锁文件在 `$HOME/.agents/.skill-lock.json`。外部共同方法推荐用户级安装，因此 `-g` 是本页的常规用法；本仓库 20 项同样支持用户级与项目级两种范围。
  - 边界（同样只在 `skills` CLI 1.7.0 上核实）：用户级锁只为**能解析出 `owner/repo` 的来源**写记录。用本地路径安装时（例如 `add /绝对路径/到/checkout`），即使技能确实装进了 `$HOME/.agents/skills/`，这批 20 项在用户级锁里**没有来源记录**；同一批技能的项目级锁仍会正常记录 20 条。所以用户级锁不是「每个用户级技能都有来源记录」的保证，实际来源以安装命令与目标目录内容为准，不要从用户级锁的存在与否反推安装来源。
- 只指定一个宿主时，CLI 直接把真实文件复制进该宿主目录（例如 `.claude/skills/`），不生成 `.agents/`。
- 指定两个及以上宿主时，正本落在 `.agents/skills/`，各宿主目录是指向正本的符号链接。加 `--copy` 则在每个宿主目录各生成一份独立真实副本。
- 项目级安装会生成 `skills-lock.json`，通常记录 `source`、`sourceType`、`skillPath`、`computedHash`。用 `skills` CLI 1.7.0 从完整 `#<ref>` 安装时会另记录 `ref` 字段；默认分支安装的锁记录不包含它，因此无法从那类锁文件还原提交。内容摘要 `computedHash` 可用于比对实际安装内容。
- 仓库根的 `LICENSE` 与 `THIRD_PARTY_NOTICES.md` **不会**随技能安装，只有技能目录内的文件会被复制。这是每项技能都自带 `LICENSE` 通知的原因。

## 选择安装的语法

多项技能用空格分隔，`'*'` 表示全部。逗号分隔不生效：

```bash
npx skills@latest add LC-86/MyGameStudio \
  --skill implement-gamestudio review-gamestudio tdd-gamestudio \
  docs-gamestudio tasks-gamestudio
```

`--skill writing-for-agents` 对**官方来源**有效，对本仓库无效：本仓库的 20 项里没有这一项，把它写进上面的 MyGameStudio 命令会因匹配不到而失败。共同方法来自另一个来源：

```bash
npx skills@latest add mattpocock/skills --skill writing-for-agents --agent universal --copy -g -y
```

CLI 不解析技能间依赖，选中的技能各自独立安装。必须一起安装的集合见 [dependencies.md](dependencies.md)。

## 固定引用安装：`@` 与 `#` 不是一回事

核对 `skills@1.7.0` 的来源解析后确认：

| 写法 | 实际含义 |
|---|---|
| `owner/repo@x` | `x` 是**技能筛选**（skillFilter），仓库仍按**默认分支**克隆 |
| `owner/repo#ref` | `ref` 才是 **Git 引用**（分支或标签） |
| `owner/repo#ref@skill` | 先按 `ref` 取内容，再筛 `skill` |

所以 `npx skills@latest add LC-86/MyGameStudio@v2.0.2` **不会**装到 `v2.0.2`：`@v2.0.2` 被当成技能筛选名。具体结果取决于有没有同时给 `--skill '*'`：

| 命令 | 结果（2026-09-22 实测，均加 `--agent universal --copy -y`） |
|---|---|
| `add LC-86/MyGameStudio@v2.0.2` | 先 `Found 20 skills`，随后报 `No matching skills found for: v2.0.2`，**退出 1**，什么都没装 |
| `add LC-86/MyGameStudio@v2.0.2 --skill '*'` | 通配绕过筛选，`Found 20 skills` / `Installing all 20 skills`，**退出 0** 并把**默认分支**的全部技能装上，无警告——你想固定旧版，拿到的却是本版（装出的目录里没有 `ask-matt` 等旧名） |

第二种才是真正危险的：它看起来成功了，装的却是**默认分支**的内容，而不是你写在 `@` 后面那个版本。合入前的实测记录：日志 `Found 39 skills` / `Installing all 39 skills`，产物含 `plugin/skills/ask-matt/SKILL.md`，锁文件未记录目标引用——39 正好等于 V2 树里 `plugin/skills/` 的 28 项加 `legacy/plugin-skills/` 的 11 项，与「装到了默认分支」一致。合入之后同一条命令改成 `Found 20 skills`，装的正是默认分支上的本版，机制没变、内容跟着默认分支变。

因此：

- 任何时候都不要用 `@<分支或标签>` 表达版本意图。它要么因为筛选匹配不到而直接失败，要么在你同时给了 `--skill '*'` 时静默地给你默认分支——两种都不是你想要的版本。
- 要按版本固定，用 `#<ref>`：`npx skills@latest add LC-86/MyGameStudio#v3.0.0`。这一形式已在 2026-09-22 用仓库内三个真实 ref 端到端验证（都加 `--skill '*' --agent universal --copy -y`）：

  | 来源 | 结果 |
  |---|---|
  | `LC-86/MyGameStudio#v2.0.2` | `Found 39 skills` / `Installing all 39 skills`，装到的是旧技能名（`ask-matt`、`to-spec` 等） |
  | `LC-86/MyGameStudio#release/v3` | `Found 20 skills` / `Installing all 20 skills`，装到的是 `-gamestudio` 名称（该分支已在发布后删除，此行是当时的实测记录；之后要用 `#v3.0.0`） |
  | `LC-86/MyGameStudio#v3.0.0` | `Found 20 skills`，含 `gdd-gamestudio/SKILL.md` 与共享参考，无旧名残留 |

  三次结果内容各不相同，说明 `#` 之后的引用确实决定了取哪份内容，而不是只看默认分支；标签与分支 ref 走同一条解析路径。
- 只想试装未合入的改动，也可以用本地路径：`add /绝对路径/到/checkout`（本仓库的安装测试就是这么跑的）。

## 安装后确认

确认三件事，不要只看命令是否退出成功：

1. 技能出现在宿主实际读取的技能目录中。MyGameStudio 提供 20 项 `-gamestudio` 名称；外部共同方法 `writing-for-agents` 由官方来源单独安装，应在它自己的安装范围里核对，不要期待 `--skill '*'` 把它带进来。`v3.0.2` 标签当时包含 21 项，其中一项是当时随包的 `writing-for-agents` 副本；`v3.0.1` 标签仍固定包含 20 项。
2. 每项技能目录内有 `SKILL.md`、它引用的 `references/` 或 `templates/`，以及一份 `LICENSE` 通知。
3. 共享方法可达：`writing-for-agents` 的正文与技能机制可按宿主支持的技能名称取得；语义保真、通用委派与 `docs-gamestudio/references/document-routing.md` 可读；`tasks-gamestudio/references/task-responsibility.md` 可达，且相对引用能解析到所有者。

## 更新与卸载

两个来源分别更新，各自只有一个渠道：外部共同方法跟随官方 `mattpocock/skills`，本仓库技能跟随 `LC-86/MyGameStudio`。更新前检查同名目标、锁来源与本地修改。

```bash
# 外部共同方法（项目级去掉 -g）
npx skills@latest add mattpocock/skills --skill writing-for-agents --agent universal --copy -g -y

# 本仓库 20 项（项目级去掉 -g）
npx skills@latest add LC-86/MyGameStudio --skill '*' --agent universal --copy -g -y
```

`skills` CLI 按技能名称写入目录：同一安装范围里两个来源的同名技能不会并列，后安装者会替换同名目标并更新锁文件来源。因此不要用 MyGameStudio 的安装操作去更新或替换外部共同方法，也不要在同一范围内留下两份可并列加载的 `writing-for-agents`。用户级与项目级可能各有一份，宿主实际选择顺序与加载版本必须单独观察——本库不提供自动检测、条件补齐或替换，也不提供自建的安装核验工具；实际加载到哪一份只能在目标宿主里核实。

卸载就是从宿主技能目录中移除该范围安装的技能目录，没有注册表、后台服务或专用运行层需要清理。外部共同方法与本仓库技能分别卸载，互不影响。

V3 不维护自建安装命令，因此也不提供自建的卸载命令。

## 从 2.0.2 插件版本切换

2.0.2 是多客户端插件包，安装方式与 V3 完全不同。旧命令已全部退出，切换步骤与能力差异见 [migration-v3.md](migration-v3.md)。

## 许可

每个技能目录内的 `LICENSE` 随技能一起安装，包含 MIT 许可全文、两条版权声明与该技能的上游来源说明。这样按单项技能安装时，接收方仍能看到完整的版权与许可通知，而不必依赖没有一起安装的仓库根 `LICENSE`。

仓库层面的许可与第三方说明见 [LICENSE](../LICENSE) 与 [THIRD_PARTY_NOTICES.md](../THIRD_PARTY_NOTICES.md)。

## 本仓库的实际验证状态

哪些安装路径已经真实测试、哪些未运行，见 [validation-v3.md](validation-v3.md)。本页描述的是目标用法，不等于所有宿主都已验证。

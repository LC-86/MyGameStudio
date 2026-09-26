# 安装

当前本地准备的 MyGameStudio 3.0.2 候选是一个包含 21 项技能的原生 Agent Skills 仓库。安装由官方 `skills` CLI 完成，本仓库不提供安装器、不发布 npm 包、不构建 tar 包，也不维护各 AI 开发工具的目录转换。

## 安装

```bash
# 发现并选择技能
npx skills@latest add LC-86/MyGameStudio

# 只列出可发现技能，不安装
npx skills@latest add LC-86/MyGameStudio --list

# 完整安装这套互相协作的技能（推荐）
npx skills@latest add LC-86/MyGameStudio --skill '*'
```

具体安装到哪个目录由官方 CLI 与你的选择决定。`@latest` 指 `skills` CLI 的版本，不代表自动选择 MyGameStudio 的 `v3.0.0` 标签：远端命令取的是仓库**默认分支**的内容，标签与默认分支是两件事。2026-09-25 对已发布的 v3.0.1 远端验证得到 20 项；本地准备的 v3.0.2 候选为 21 项。`#v3.0.1` 仍固定为旧的 20 项；v3.0.2 标签尚待创建。

推荐完整安装 21 项。这套技能互相引用共享方法，选择安装会缺少依赖，见 [dependencies.md](dependencies.md)。`v3.0.1` 标签保留此前的 20 项；v3.0.2 候选合入默认分支并打标签后，即固定提供 21 项。

## 安装目标与文件形态

本仓库在 `skills` CLI **1.7.0** 上实测的行为（完整证据见 [validation-v3.md](validation-v3.md)）：

- `--agent universal` 安装到项目的 `.agents/skills/<技能名>/`。这是本库推荐的目标。
- 只指定一个宿主时，CLI 直接把真实文件复制进该宿主目录（例如 `.claude/skills/`），不生成 `.agents/`。
- 指定两个及以上宿主时，正本落在 `.agents/skills/`，各宿主目录是指向正本的符号链接。加 `--copy` 则在每个宿主目录各生成一份独立真实副本。
- `-g` / `--global` 写入用户主目录下的宿主技能目录。本项目不使用它，也不建议对真实用户环境使用。
- 项目级安装会生成 `skills-lock.json`，通常记录 `source`、`sourceType`、`skillPath`、`computedHash`。2026-09-26 用 `skills` CLI 1.7.0 从完整 `#<ref>` 安装 fork 时另观察到 `ref` 字段；默认分支安装的锁记录不包含它，因此无法从那类锁文件还原提交。内容摘要 `computedHash` 可用于比对实际安装内容。
- 仓库根的 `LICENSE` 与 `THIRD_PARTY_NOTICES.md` **不会**随技能安装，只有技能目录内的文件会被复制。这是每项技能都自带 `LICENSE` 通知的原因。

## 选择安装的语法

多项技能用空格分隔，`'*'` 表示全部。逗号分隔不生效：

```bash
npx skills@latest add LC-86/MyGameStudio \
  --skill implement-gamestudio review-gamestudio tdd-gamestudio \
  writing-for-agents docs-gamestudio tasks-gamestudio
```

纯通用项目可从 LC-86 fork 单独安装 `writing-for-agents`。目前已验证的完整源提交是 `f3c726f275fa1ac59fef33732e527dded6d62479`：

```bash
npx skills@latest add LC-86/mattpocockskills#f3c726f275fa1ac59fef33732e527dded6d62479@writing-for-agents
```

`skills` CLI 1.7.0 对完整 `#<ref>` 安装会在锁文件记录 `ref`，默认分支安装则不包含该字段；切换来源时一并核对锁中的 `source`、`ref` 和 `computedHash`。后续更新应选择并核验 fork 的新完整提交；不要把移动分支或同一安装范围内的两个同名来源当成固定版本。

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
  | `LC-86/MyGameStudio#release/v3` | `Found 20 skills` / `Installing all 20 skills`，装到的是本版 `-gamestudio` 名称（该分支已在发布后删除，此行是当时的实测记录；要用 `#v3.0.0`） |
  | `LC-86/MyGameStudio#v3.0.0` | `Found 20 skills`，含 `gdd-gamestudio/SKILL.md` 与共享参考，无旧名残留 |

  三次结果内容各不相同，说明 `#` 之后的引用确实决定了取哪份内容，而不是只看默认分支；标签与分支 ref 走同一条解析路径。
- 只想试装未合入的改动，也可以用本地路径：`add /绝对路径/到/checkout`（本仓库的安装测试就是这么跑的）。

## 安装后确认

确认三件事，不要只看命令是否退出成功：

1. 技能出现在宿主实际读取的技能目录中。当前 v3.0.2 候选有 20 项 `-gamestudio` 名称与 `writing-for-agents`，共 21 项；`v3.0.1` 仍是 20 项。
2. 每项技能目录内有 `SKILL.md`、它引用的 `references/` 或 `templates/`，以及一份 `LICENSE` 通知。
3. 共享方法可达：`writing-for-agents/` 下的正文、技能机制、通用委派参考与许可可读；`docs-gamestudio/references/document-routing.md` 和 `tasks-gamestudio/references/task-responsibility.md` 可达，且相对引用能解析到所有者。

## 更新与卸载

更新按固定安装范围的来源执行：GameStudio 项目范围跟随经验证的随包版本，纯通用范围跟随 LC-86 fork。更新前检查同名目标、锁来源和本地修改；目标含 `SHA256SUMS` 时，用只读检查器核对：

```bash
python3.12 scripts/verify-writing-for-agents-install.py \
  --installed-dir "/absolute/path/to/writing-for-agents" \
  --lock-file "/absolute/path/to/skills-lock.json" \
  --reference-dir "/absolute/path/to/pristine-copy-of-the-same-source" --show-diff
```

检查器要求 lock 文件与目标属于同一安装范围，并打印锁定来源、ref 与摘要。参考目录必须与锁定来源版本相同；它不是任意版本的对照。摘要不匹配或参考副本本身有改动时，检查器拒绝把差异当作可信对照。检查器属于 MyGameStudio 源仓库的维护脚本，不随技能安装，也不修改安装。如果没有该 checkout、lock、旧来源摘要清单、正确参考副本或检查报告差异，状态就是未验证；先保存副本并人工比较，不要直接切换。迁移先在临时消费者核对锁来源、摘要与宿主实际加载版本，再按授权处理目标范围。卸载就是从宿主技能目录中移除该范围安装的技能目录，没有注册表、后台服务或专用运行层需要清理。

V3 不维护自建安装命令，因此也不提供自建的卸载命令。

## 从 2.0.2 插件版本切换

2.0.2 是多客户端插件包，安装方式与 V3 完全不同。旧命令已全部退出，切换步骤与能力差异见 [migration-v3.md](migration-v3.md)。

## 许可

每个技能目录内的 `LICENSE` 随技能一起安装，包含 MIT 许可全文、两条版权声明与该技能的上游来源说明。这样按单项技能安装时，接收方仍能看到完整的版权与许可通知，而不必依赖没有一起安装的仓库根 `LICENSE`。

仓库层面的许可与第三方说明见 [LICENSE](../LICENSE) 与 [THIRD_PARTY_NOTICES.md](../THIRD_PARTY_NOTICES.md)。

## 本仓库的实际验证状态

哪些安装路径已经真实测试、哪些未运行，见 [validation-v3.md](validation-v3.md)。本页描述的是目标用法，不等于所有宿主都已验证。

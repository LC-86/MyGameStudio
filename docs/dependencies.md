# 技能依赖

默认推荐完整安装本仓库 20 项。完整使用分两步：先确认外部共同方法 `writing-for-agents`（它不属于本仓库，从官方来源独立安装），再安装本仓库 20 项——已经有官方共同方法时只跳过第一步。官方 CLI 不会自动解析依赖；选择安装时还要按下表加入需要的同源技能。

```bash
# 第一步：外部共同方法（官方来源，已有时跳过）
npx skills@latest add mattpocock/skills --skill writing-for-agents --agent universal --copy -g -y

# 第二步：本仓库 20 项
npx skills@latest add LC-86/MyGameStudio --skill '*' --agent universal --copy -g -y
```

上面是用户级命令（本库推荐的范围）；项目级替代去掉 `-g` 并在目标项目根目录执行。完整的两来源安装步骤、安装范围与参数证据边界见 [安装](installation.md)。

## 共享资料所有者

| 所有者 | 唯一资料 | 用途 |
|---|---|---|
| `docs-gamestudio` | `references/semantic-fidelity.md`、`references/delegation.md`、`references/document-routing.md` | 语义保真、通用子代理委派、游戏文档归属与增量协作 |
| `tasks-gamestudio` | `references/task-responsibility.md` | 人机责任、人工验收与交接 |
| `writing-for-agents`（外部） | 官方 `SKILL.md`、`SKILL-MECHANICS.md` | 通用正式资料写作、信息层级、完成标准与技能机制 |

`writing-for-agents` 是**外部共同方法**：它来自官方 `mattpocock/skills`，由用户独立安装，不承诺与 GameStudio 位于同一安装范围，本仓库也不携带它的副本。编写正式资料时按技能名称取得它，不使用跨安装范围的相对路径，也不把它的目录当成依赖契约。`docs-gamestudio` 只拥有语义保真与通用委派，不复制通用写作方法；`tasks-gamestudio` 继续拥有人工责任与验收交接。

## 必须一起安装的技能

下表列出各技能需要的同源组合；`writing-for-agents` 是外部共同方法，不在同源组合里，单独一列说明它是否被该技能使用。

| 要安装的技能 | 必需的同源组合（括号内为按需） | 外部共同方法 |
|---|---|---|
| `grill-gamestudio` | `grilling-gamestudio`、`docs-gamestudio` | 不直接取得（纯访谈，不写正式资料） |
| `grill-gamestudio-docs` | `grilling-gamestudio`、`domain-gamestudio`、`gdd-gamestudio`、`spec-gamestudio`、`docs-gamestudio` | 经文档方法取得（访谈本身不写正式资料） |
| `gdd-gamestudio` | `docs-gamestudio`（`spec-gamestudio`、`grilling-gamestudio` 为按需） | 使用（按技能名称取得） |
| `spec-gamestudio` | `docs-gamestudio`（`gdd-gamestudio` 为按需） | 使用（按技能名称取得） |
| `domain-gamestudio` | `docs-gamestudio`（`gdd-gamestudio`、`spec-gamestudio`、`grilling-gamestudio` 为按需） | 使用（按技能名称取得） |
| `grilling-gamestudio` | `docs-gamestudio`（其余技能为按需） | 不直接取得（落盘交给文档方法） |
| `tasks-gamestudio` | `docs-gamestudio` | 使用（按技能名称取得） |
| `implement-gamestudio` | `docs-gamestudio`、`tasks-gamestudio`、`review-gamestudio`（`tdd-gamestudio`、`gdd-gamestudio`、`spec-gamestudio` 为按需） | 使用（按技能名称取得） |
| `tdd-gamestudio` | `docs-gamestudio`、`tasks-gamestudio` | 使用（按技能名称取得） |
| `review-gamestudio` | `docs-gamestudio`、`tasks-gamestudio` | 使用（按技能名称取得） |
| `debug-gamestudio` | `docs-gamestudio`、`tasks-gamestudio`（`tdd-gamestudio`、`review-gamestudio` 为按需） | 使用（按技能名称取得） |
| `prototype-gamestudio` | `docs-gamestudio`、`tasks-gamestudio`（`gdd-gamestudio`、`spec-gamestudio` 为按需） | 使用（按技能名称取得） |
| `wayfinder-gamestudio` | `docs-gamestudio`、`grilling-gamestudio`、`domain-gamestudio`（`research-gamestudio`、`prototype-gamestudio`、`gdd-gamestudio`、`spec-gamestudio` 为按需） | 使用（按技能名称取得） |
| `research-gamestudio` | `docs-gamestudio` | 使用（按技能名称取得） |
| `handoff-gamestudio` | `docs-gamestudio` | 使用（按技能名称取得） |
| `ask-gamestudio` | `docs-gamestudio`；准确导航还需要它可能推荐的技能已安装 | 使用（按技能名称取得） |
| `setup-gamestudio` | `docs-gamestudio` | 使用（按技能名称取得） |
| `codebase-gamestudio` | `docs-gamestudio` | 使用（按技能名称取得） |
| `merge-gamestudio` | `docs-gamestudio` | 使用（按技能名称取得） |
| `docs-gamestudio` | 保真、委派与分流参考随本技能一起安装 | 使用（按技能名称取得） |

`docs-gamestudio` 的委派参考被 grilling、handoff、implement、research、review、tasks、wayfinder 和 ask 按需使用；单纯缺少委派场景时不要求每项任务都调用它。`writing-for-agents` 不在本仓库集合内：安装 GameStudio 不等于安装了外部共同方法，两者要分别安装。

访谈类入口自己不写正式资料：`grill-gamestudio`、`grill-gamestudio-docs` 与 `grilling-gamestudio` 的正文不出现外部共同方法名，需要落盘时由它们在协作模式下按需使用的 `domain-gamestudio`、`gdd-gamestudio`、`spec-gamestudio` 按技能名称取得，因此“不直接取得”不等于这条工作流不需要它。

工程交付与协作工作流组（`ask-gamestudio`、`codebase-gamestudio`、`debug-gamestudio`、`handoff-gamestudio`、`implement-gamestudio`、`merge-gamestudio`、`research-gamestudio`、`review-gamestudio`、`setup-gamestudio`、`tasks-gamestudio`、`tdd-gamestudio`）的 11 项都在自己的正文里声明了缺外部共同方法时的处理，这一条由静态断言守住。静态断言只保证正文写着该要求，不等于每次会话都会照做：实测里两个缺方法场景报告了缺口并只继续不依赖它的部分，一次评审场景完成了评审却没有报告缺口，见 [Issue #91 行为证据](evidence/issue-91-behavior-matrix.md)。安装时还要注意引用的传递性：`docs-gamestudio` 的分流参考会指向 `domain-gamestudio`、`gdd-gamestudio`、`spec-gamestudio`、`grilling-gamestudio` 与两个访谈入口，只装工程交付组时这些链接在安装结果里不可达；要让引用可用，按这个闭包一并安装，或直接完整安装。`scripts/install-smoke-test.sh` 第 11 节按该闭包核对。

## 选择安装示例

只做通用工程资料时，只装官方共同方法即可，不需要本仓库任何技能；编写游戏 GDD 或 spec 时，把官方共同方法、`docs-gamestudio` 和相应专业技能一起装上——共同方法来自另一个来源，两条命令都要执行。实现与评审组合示例：

```bash
# 外部共同方法（官方来源，已有时跳过）
npx skills@latest add mattpocock/skills --skill writing-for-agents --agent universal --copy -g -y

# 同源组合（本仓库）
npx skills@latest add LC-86/MyGameStudio \
  --skill implement-gamestudio review-gamestudio tdd-gamestudio \
  docs-gamestudio tasks-gamestudio
```

缺少必需资料时，技能应指出具体缺口并保留可继续部分；CLI 不会补装，也不应凭名称模仿后声称完成。完整安装本仓库最简单（与其上方第二步同一条命令）：

```bash
npx skills@latest add LC-86/MyGameStudio --skill '*' --agent universal --copy -g -y
```

## 来源与更新范围

外部共同方法只有一个更新渠道：官方 `mattpocock/skills`。本仓库自 3.0.3 起不再分发、不再镜像该方法，也不提供来源切换或已安装副本核验工具；本仓库技能则始终跟随 `LC-86/MyGameStudio`。

`skills` CLI 按技能名称写入目录，同一安装范围里两个来源的同名技能不会并列：后安装者会替换同名目标并更新锁文件来源。`skills-lock.json` 总会记录来源和内容摘要；CLI 1.7.0 对显式 `#<ref>` 另记录 `ref`，默认分支安装不记录。用户级与项目级可以各自保留一份，但不能假设宿主优先级：实际加载到哪个范围、哪个版本，仍需在目标宿主核实。本库不提供自动检测、条件补齐或自动替换，安装资料只提醒用户自行确认共同方法已从官方来源安装。

更新时按本页开头的两步命令分别执行（项目级去掉 `-g`，并在目标项目根目录执行），先检查同名目标、锁来源与本地修改，再核对宿主实际加载版本；不要对真实用户目录自动替换。参数与锁文件行为只在 `skills` CLI 1.7.0 上核实，见 [安装](installation.md)。

仓库内的 `docs/`、`provenance/`、`tests/`、`scripts/` 是维护资料，不随单项技能安装，也不是技能运行时依赖。

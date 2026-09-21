# 技能依赖

本文件区分三类关系：安装某项技能时**必须**一起安装的技能依赖、只在特定情境下才会被组合使用的**按需方法**、以及不影响技能能否工作的**只读资料引用**。

默认推荐完整安装 20 项：

```bash
npx skills@latest add LC-86/MyGameStudio --skill '*'
```

官方 CLI 不承诺自动解析并安装技能间依赖，这一点已在 CLI 1.7.0 上实测确认：单独安装 `tdd-gamestudio` 后，`.agents/skills/` 下只有它自己，`tasks-gamestudio/references/task-responsibility.md` 不存在。选择安装时需要你自己把依赖包含进去。

多项技能用空格分隔，`'*'` 表示全部，逗号分隔不生效：

```bash
# 例：只装实现与评审相关的能力，必须带上它们的共享方法所有者
npx skills@latest add LC-86/MyGameStudio \
  --skill implement-gamestudio review-gamestudio tdd-gamestudio docs-gamestudio tasks-gamestudio
```

## 共享资料的所有者

有两项技能拥有被其他技能引用的共享方法，各只有一份权威正文：

| 所有者 | 共享资料 | 被谁引用 |
|---|---|---|
| `docs-gamestudio` | `references/document-routing.md`（文档分流与增量协作） | domain、gdd、grilling、implement、prototype、spec、wayfinder |
| `docs-gamestudio` | `references/delegation.md`（子代理委派） | grilling、handoff、implement、research、review、tasks、wayfinder |
| `docs-gamestudio` | `references/skill-authoring.md`（技能与项目规则写作） | 编写或修订技能与项目规则时 |
| `tasks-gamestudio` | `references/task-responsibility.md`（责任、分流与交接） | debug、implement、prototype、review、tdd |

`docs-gamestudio` 自身不依赖任何其他技能，是最底层的依赖。

## 必须的技能依赖

| 要安装的技能 | 必须一起安装 |
|---|---|
| `grill-gamestudio` | `grilling-gamestudio`、`docs-gamestudio` |
| `grill-gamestudio-docs` | `grilling-gamestudio`、`domain-gamestudio`、`gdd-gamestudio`、`spec-gamestudio`、`docs-gamestudio` |
| `gdd-gamestudio` | `docs-gamestudio`（`spec-gamestudio`、`grilling-gamestudio` 为按需） |
| `spec-gamestudio` | `docs-gamestudio`（`gdd-gamestudio` 为按需） |
| `domain-gamestudio` | `docs-gamestudio`（`gdd-gamestudio`、`spec-gamestudio`、`grilling-gamestudio` 为按需） |
| `grilling-gamestudio` | `docs-gamestudio`（其余为按需） |
| `tasks-gamestudio` | `docs-gamestudio` |
| `implement-gamestudio` | `docs-gamestudio`、`tasks-gamestudio`、`review-gamestudio`（`tdd-gamestudio`、`gdd-gamestudio`、`spec-gamestudio` 为按需） |
| `tdd-gamestudio` | `tasks-gamestudio`、`docs-gamestudio` |
| `review-gamestudio` | `docs-gamestudio`、`tasks-gamestudio` |
| `debug-gamestudio` | `docs-gamestudio`、`tasks-gamestudio`（`tdd-gamestudio`、`review-gamestudio` 为按需） |
| `prototype-gamestudio` | `docs-gamestudio`、`tasks-gamestudio`（`gdd-gamestudio`、`spec-gamestudio` 为按需） |
| `wayfinder-gamestudio` | `docs-gamestudio`、`grilling-gamestudio`、`domain-gamestudio`（`research-gamestudio`、`prototype-gamestudio`、`gdd-gamestudio`、`spec-gamestudio` 为按需） |
| `research-gamestudio` | `docs-gamestudio` |
| `handoff-gamestudio` | `docs-gamestudio` |
| `ask-gamestudio` | `docs-gamestudio`；导航要准确还需要它可能推荐的技能已安装 |
| `setup-gamestudio` | `docs-gamestudio` |
| `codebase-gamestudio` | `docs-gamestudio` |
| `merge-gamestudio` | `docs-gamestudio` |
| `docs-gamestudio` | 无 |

`tasks-gamestudio/references/task-responsibility.md` 是人机责任与验收交接的唯一说明。缺少它时，涉及人工验收的判断会失去共同依据，因此凡是会产出交付成果或评审结论的技能都把它列为必需依赖。

## 按情境使用的方法

以下关系不是安装前置条件，只在当前任务与授权适用时才会被组合使用。缺少它们不会让主技能失效，只会少掉相应能力：

- `implement-gamestudio` 按需在实现中使用 `tdd-gamestudio`、`codebase-gamestudio`、`debug-gamestudio`，收尾使用 `review-gamestudio`。
- `wayfinder-gamestudio` 按缺口选择 `research-gamestudio`、`grilling-gamestudio`、`domain-gamestudio`、`prototype-gamestudio`，并把已采纳内容交给 `gdd-gamestudio` / `spec-gamestudio`。
- `gdd-gamestudio` 与 `spec-gamestudio` 只处理明确差异时相互衔接，处理完即返回。
- `debug-gamestudio` 修复代码后按需在 `review-gamestudio` 中检查，被 `implement-gamestudio` 使用时返回原流程。
- `prototype-gamestudio` 按已确认采纳结果更新 `gdd-gamestudio` / `spec-gamestudio`。

## 只读资料引用

技能运行时查找的项目资料不是随技能分发的静态依赖：项目自己的 GDD、spec、任务记录、术语表、决策记录、资源约定与工程文件，都由 `setup-gamestudio` 记录该项目实际位置。缺少它们时相关技能说明缺口并保留可独立完成的部分，不因此失效。

仓库内的 `docs/`、`provenance/`、`tests/`、`scripts/` 是维护资料，不随技能安装，也不是技能运行的隐性必需输入。

## 缺少依赖时的行为

技能在找不到必需的共享参考时说明受影响的能力，保留可独立完成的部分，不凭名称模仿后宣称完成，也不擅自联网安装。因此部分安装不会静默给出错误结果，但会少掉相应保障：例如缺少 `task-responsibility.md` 时，`review-gamestudio` 无法按共同依据区分哪些条件可由 Agent 验证、哪些属于指定人的决定。

## 与同名上游方法的关系

如果宿主中还装着 Matt Pocock 自己的技能库，其中存在 `grilling`、`tdd`、`prototype`、`research`、`handoff`、`wayfinder`、`implement`、`to-spec`、`to-tickets`、`code-review`、`diagnosing-bugs`、`codebase-design`、`resolving-merge-conflicts`、`domain-modeling`、`writing-for-agents`、`ask-matt`、`grill-me`、`grill-with-docs`、`setup-matt-pocock-skills` 等同源方法。MyGameStudio 的 20 项都带 `-gamestudio` 后缀，明确使用带后缀的名称不会指向未改编的上游方法。上游方法的正文没有游戏适配，也不包含本库的共享参考。

# 从 2.0.2 迁移到 3.0.0

3.0.0 不是 2.0.2 的增量升级。交付形态从多客户端插件包变成原生 Agent Skills 仓库，安装方式、技能集合与运行时依赖都变了。

## 安装方式的变化

2.0.2 按客户端分别安装：下载 `dist/mygamestudio-2.0.2.tar.gz`、核对 `SHA256SUMS.txt`、再按 `docs/installation/` 里对应客户端的页面用 `claude --plugin-dir`、`codex plugin add`、`.zcode-plugin`、`.grok/plugins` 等方式接入。

这些命令与文件在 3.0.0 中全部退出，不再可用：

- `dist/` 下的全部 tar 包、`SHA256SUMS.txt`、`package-manifest.txt`
- `scripts/build-package.sh`、`scripts/verify-reproducible.sh`
- `plugin/.claude-plugin/`、`plugin/.codex-plugin/`、`plugin/.zcode-plugin/` 三份插件清单
- `plugin/skills/*/agents/openai.yaml` 专属元数据，以及 frontmatter 中的 `disable-model-invocation`、`argument-hint`
- `docs/installation/` 六个客户端安装页与 `docs/reference/compatibility.md` 兼容矩阵

3.0.0 只有一条安装路径，见 [installation.md](installation.md)：

```bash
npx skills@latest add LC-86/MyGameStudio --skill '*'
```

## 技能集合的变化

2.0.2 分发 28 项：25 项保留上游原名的 Matt 方法，加上 `game-producer`、`game-init`、`game-design`。

3.0.0 分发 20 项，全部改名为 `-gamestudio` 形式并完成游戏化适配。名称映射见 [provenance/upstream.md](../provenance/upstream.md)。

### 退出且没有等价能力的部分

| 2.0.2 入口 | 3.0.0 承担者 | 明确未覆盖 |
|---|---|---|
| `game-producer` | `ask-gamestudio` 的下一步导航；各技能内部的局部状态核对；`wayfinder-gamestudio` 的跨会话路线梳理 | 只读的全项目进度盘点没有等价能力。Ask 只给一个下一步，不做项目总控 |
| `game-init` | `setup-gamestudio` 的协作约定、资料入口与资源管理约定 | 旧项目完整资料迁移、安全切换与回退、任务接入的 plan/apply 两段式流程没有等价能力 |
| `game-design` | `grill-gamestudio-docs` 组合 `grilling-gamestudio`、`domain-gamestudio`、`gdd-gamestudio`、`spec-gamestudio` | 三段式设计讨论接缝与版本节点设计快照没有等价能力；正式规则采纳改由用户在文档协作中确认 |
| 记录运行层（`plugin/records/`，21 个 Python 模块） | 项目已有工具（CLI、连接器、文件操作）+ `setup-gamestudio` 记录的约定 + 各技能的回读与部分成功报告要求 | 程序级幂等恢复、跨后端一致性、待写入索引、快照与安全切换。这些保障被明确放弃，不是被提示词等价替代 |

上游的 `improve-codebase-architecture`、`triage`、`to-questionnaire`、`wizard`、`teach`、`wait-what` 也不在 20 项中。普通解释、人工步骤说明与现有标签使用仍然保留，但没有完整复现这些技能的能力。

### 调用边界的变化

2.0.2 用 `disable-model-invocation: true` 与 `policy.allow_implicit_invocation: false` 让宿主阻止模型自行触发用户专用入口。3.0.0 删除了这两个声明。

就 3.0.0 本身而言，8 个用户入口与 12 个按需方法仍然是行为边界，但当时只写在描述与正文里：标准技能文本不具备跨宿主的强制调用隔离能力，某个宿主仍可能自行选中一个用户入口。需要额外约束时，在你自己的项目规则（`AGENTS.md` / `CLAUDE.md`）里重申该边界，那是宿主确实会读取的位置。

3.0.0 之后（#81）恢复了宿主调用控制，这也是当前源码树的状态：Claude Code、Grok Build、DSH 读 frontmatter 的 `disable-model-invocation: true`；Codex 读技能目录内 `agents/openai.yaml` 的 `policy.allow_implicit_invocation: false`；ZCode 与 Qoder 未文档化任何调用控制字段，仍是指令层约定。这两层宿主强制随 #81 之后的内容生效，自 v3.0.1 起进入发布；用固定引用 `#v3.0.0` 安装得到的是删除声明的那一版。这些机制来自各宿主官方文档，本库未在宿主内逐一实测，状态见 [验证状态](validation-v3.md)。

## 你的游戏项目需要做什么

3.0.0 不自动迁移任何游戏项目，不修改其他项目的任务、资产、存档、外部存储或已安装技能。

按项目自行处理：

1. 安装 20 项技能。
2. 检查项目入口规则（`AGENTS.md` / `CLAUDE.md`）里指向旧入口、旧运行层或 `docs/mygamestudio/INDEX.md` 一类旧资料位置的引用。`setup-gamestudio` 在探查时会指出失效引用并建议改写，但它只改约定文档。
3. 项目已有的 GDD、spec、任务记录、术语表与资源约定继续有效。它们是运行时查找的项目资料，不随技能分发，也不需要转换格式。
4. 旧的 `ready-for-agent` / `ready-for-human` 等标签语义沿用。`tasks-gamestudio/references/task-responsibility.md` 说明这两个标签在 3.0.0 中的含义：它们表示下一执行段由谁推进，不表示最终验收通过，也不授予权限。若你原有的自动化把 `ready-for-agent` 当成整票全自动处理，需要先改领取与关闭条件，再用于含人工验收的任务。

## 恢复 2.0.2

3.0.0 已合入默认分支，`npx skills@latest add LC-86/MyGameStudio` 从此刻起取到的是本版。**2.0.2 及更早版本停止维护**：不再修缺陷、不再补适配、不再发新版，`v2.0.2` 标签与其 Release 仅作历史留存。

仍要取得 2.0.2 内容有两条路：

```bash
# 一：按 Git 引用固定安装（已实测：Found 39 skills，即 2.0.2 的技能树）
npx skills@latest add LC-86/MyGameStudio#v2.0.2 --skill '*'

# 二：检出完整 2.0.2 树自行查看或取物
git worktree add /tmp/mgs-v2 5e3cfbf     # 只读查看完整 2.0.2 树
git show 5e3cfbf:plugin/records/mgs_records.py
git checkout 5e3cfbf -- legacy/          # 会写入工作树，按需使用
```

Git 历史未被改写，2.0.2 的完整内容在提交 `5e3cfbfa3e217a9182690237955734109b982235`。注意固定引用只按 `computedHash` 记录内容哈希，不记录引用与提交 SHA；`v2.0.2` 标签被移动时同一命令取到的内容也会变，见 [安装](installation.md)。

已发布的 GitHub Release 资产不受本次改动影响。被移除内容的完整清单见 [provenance/v2-retirement.md](../provenance/v2-retirement.md)。

## 版本说明

3.0.0 的变更内容见 [CHANGELOG.md](../CHANGELOG.md)。版本权威来源是根目录 `VERSION`。

## 技能源码布局

本仓库是原生 Agent Skills 技能库。20 项技能各只有一份权威源码，位于 `skills/<技能名>/SKILL.md`，其 `references/`、`templates/` 与 `LICENSE` 通知都在该技能目录内。不要建立第二份技能正文副本、根目录聚合 `SKILL.md`，或 `skills/` 之外的任何 `SKILL.md`（测试夹具放在临时目录）：官方 `skills` CLI 会发现发布树中的每一个 `SKILL.md`。

frontmatter 只使用标准字段：`name`、`description`、`license`，确有需要时用 `compatibility` 或 `metadata`。在此之上，8 个用户入口各追加 `disable-model-invocation: true` 与一份 `agents/openai.yaml`，内容恰好为 `policy:` 与 `  allow_implicit_invocation: false` 两行，无其他内容；`argument-hint`、`allowed-tools` 与 frontmatter 内的 `allow_implicit_invocation` 仍然禁止；12 个按需方法不带任何宿主开关，也不带宿主文件。这套三层控制由 frontmatter 在 Claude Code、Grok Build、DSH 内强制，由 `agents/openai.yaml` 在 Codex 内强制；ZCode 与 Qoder 没有宿主级开关，同一条 8/12 边界在那里仍是写在描述与正文里的指令层约定。

共享参考只有一个所有者：写作方法、文档分流与子代理委派归 `docs-gamestudio`；人机责任与验收交接归 `tasks-gamestudio`。消费者用同级相对路径引用，不保留第二份可独立改写的副本。

改动 `skills/` 或文档后运行 `python3.12 -m pytest tests/ -q` 与 `python3.12 scripts/validate-docs.py`。静态检查不替代行为验证；实际结果记录在 `docs/validation-v3.md`，没有运行的一律标为未运行。

## Agent 技能

### 议题追踪器

议题、规格与 Wayfinder 地图在 `LC-86/MyGameStudio` 的 GitHub Issues 中追踪。进行 tracker 操作前，先阅读 `docs/agents/issue-tracker.md`。

### Triage 标签

使用五个默认的标准 triage 标签。参见 `docs/agents/triage-labels.md`。

### 领域文档

本仓库使用单一上下文的领域文档布局。参见 `docs/agents/domain.md`。

## Git 提交

任务完成并通过验证后，把该任务改动的文件提交为一次快照，使每个任务在历史中留下一个检查点。提交信息用简体中文，沿用现有的 `type: 说明` 格式（`feat:`、`fix:`、`docs:`、`chore:`），例如 `fix: 修正安装脚本校验`。只暂存该任务的文件；该任务没有文件改动时跳过提交；提交只保留在本地，推送仍需单独授权。

## 双语文档

`AGENTS.zh-CN.md` 是本文档的中文镜像，`README.en.md` 是 `README.md` 的英文镜像。改动其中一份时，在同一任务内同步另一份；保持标题结构与版本事实一致。英文 README 是精简镜像，不做逐句翻译。

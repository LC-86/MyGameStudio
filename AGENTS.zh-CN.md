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

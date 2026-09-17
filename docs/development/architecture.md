# 架构说明

MyGameStudio 是安装进 AI 客户端的**工作流插件**，不是游戏引擎。

## 分层

| 层 | 目录 | 读者 |
| --- | --- | --- |
| 产品与许可 | README、LICENSE、docs、examples | 人 |
| 可安装插件 | `plugin/` | 宿主与 Agent |
| 验证 | `tests/`、`samples/`、`acceptance/` | 维护者 |
| 历史 | `legacy/`、部分 `dist/` 与 `.scratch/` | 追溯，不是当前安装包 |

`plugin/` 必须作为整体安装：技能通过相对路径引用 `internal/`、`records/`、`templates/`、`provenance/`。

## 公开入口

固定上游 Matt 正式 25 项 + `game-producer` / `game-init` / `game-design`。
调用合同：[`plugin/internal/game/invocation.md`](../../plugin/internal/game/invocation.md)。
用户专用 Matt 入口不得被制作统筹自动串调。

已退役入口不是别名，说明见 [`plugin/internal/game/retired-entries.md`](../../plugin/internal/game/retired-entries.md)。

## 记录层

现行 tracker 每项目一种：本地 Markdown 或 GitHub Issues。公开 Python 接缝在 `plugin/records/mgs_records.py`。
普通 2.x 路径不把已退役运行通道当作权限系统。

## 来源钉住

Matt 1.2.3 / `3cca18b368ae95cdbdebbff572ccafa662551015`。升级走 `plugin/provenance/mgs_upstream_upgrade.py`，先评估再采用。

## 多客户端

同时携带 `.codex-plugin/plugin.json` 与 `.zcode-plugin/plugin.json`，name/version 必须一致。
技能定位回退：上下文给出的插件目录 → Codex `$CODEX_HOME` → ZCode 缓存 → Grok `~/.grok/plugins` 或 `--plugin-dir`。

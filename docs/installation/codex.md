# Codex 安装

## 适用与验证状态

| 项 | 记录 |
| --- | --- |
| 客户端 | Codex CLI |
| 2.0.2 隔离安装 | **已验证**：Linux x86_64，Codex CLI 0.154.0，隔离 `HOME` / `CODEX_HOME`，无用户凭据 |
| 安装副本 | `$CODEX_HOME/plugins/cache/personal/mygamestudio/2.0.2`，与解包插件根 138 个文件逐字节一致（含 `LICENSE`） |
| `plugin add` / `plugin remove` / 再 `add` | **已验证**（同上隔离目录） |
| 新会话技能发现、只读调用、日常 `~/.codex/` | **未验证**（`codex doctor` 报告无凭据；未开会话） |
| 历史 | 0.18.x 曾在 macOS + Codex CLI 0.151.0 隔离验收；当时是 14 个游戏入口，**不是** 2.0.2 的 28 项集合 |

隔离核验不使用用户凭据，也不写入日常 `~/.codex/`。
不要把 0.18.x 的“14 个 game-*”期望套到 2.0.2。

## 前置条件

- 已安装 Codex CLI
- 完整插件根（Release 或仓库 `dist/` 解包后的 `plugin/`，或仓库 `plugin/`）
- 隔离验证时：把 `HOME` 与 `CODEX_HOME` 指到临时目录；不要改你的日常 `~/.codex/`

## 取得安装包并核对

```sh
# 在同时放有 tarball 与 SHA256SUMS.txt 的目录
shasum -a 256 -c SHA256SUMS.txt
tar -tzf mygamestudio-2.0.2.tar.gz | head
```

解压后插件根是 `plugin/`。应能看到 `.codex-plugin/plugin.json`、`LICENSE` 与 `skills/`。

包内辅助脚本在 `plugin/records/`、`plugin/internal/`、`plugin/provenance/`。
安装后应能从插件根解析这些相对路径；写入权限以项目授权为准，安装本身不授权改游戏文件。

## 隔离安装布局

把插件放到 `$HOME/plugins/mygamestudio`，并在 `$HOME/.agents/plugins/marketplace.json` 登记本地源。`source.path` 写为 `./plugins/mygamestudio`（相对 HOME 解析）：

```json
{
  "name": "personal",
  "interface": { "displayName": "Personal" },
  "plugins": [
    {
      "name": "mygamestudio",
      "source": { "source": "local", "path": "./plugins/mygamestudio" },
      "policy": { "installation": "AVAILABLE", "authentication": "ON_INSTALL" },
      "category": "Productivity"
    }
  ]
}
```

命令（2.0.2 已在 Linux + Codex CLI 0.154.0 隔离目录执行）：

```sh
export HOME=<隔离home>
export CODEX_HOME=<隔离codex-home>
codex plugin list --json --available
codex plugin add mygamestudio@personal --json
codex plugin list --json
```

安装副本位于 `$CODEX_HOME/plugins/cache/personal/mygamestudio/2.0.2/`。
升级/卸载：`codex plugin remove mygamestudio@personal --json` 后再 `add`（隔离目录已实测）。

会话重启：新开 Codex 会话后再查技能列表。具体交互以你的 Codex 版本为准（**未在本环境核对 UI**）。

## 技能发现与一次最小只读调用

期望：发现正式 25 项加 `game-producer`、`game-init`、`game-design`，同名唯一。
插件安装副本含 28 个技能目录；**新会话是否列出这些技能未验证**。

最小只读调用：在游戏项目中请助手使用 `game-producer` 或 `game-init`，并明确“这一轮不修改文件”。文案见 [快速开始](../getting-started.md)。

## 更新、卸载、冲突

见 [升级与卸载](upgrade-and-uninstall.md)。

## 未验证与已知限制

- 未安装到日常 `~/.codex/`
- 无登录，未跑新会话技能发现或只读调用
- Codex App / 非 CLI 宿主未单独验证
- 0.18.x 证据不能证明 2.0.2 的会话发现面与权限行为

# Codex 安装

## 适用与验证状态

| 项 | 记录 |
| --- | --- |
| 客户端 | Codex CLI |
| 曾实测的客户端版本 | 0.151.0（0.18.x 隔离验收，macOS 26.5.1 arm64，2026-09） |
| 当时公开入口 | 旧版 14 个游戏入口，**不是** 2.0.1 的 28 项集合 |
| 插件 2.0.1 日常 Codex 安装 | **未验证** |
| 本整理环境（Linux 云 VM） | 未安装 Codex，**未执行**下列命令 |

下列命令来自仓库 `acceptance/` 隔离脚本，用于说明 Codex 本地插件源曾如何工作。
把它们用在 2.0.1 之前，你需要自行确认当前 Codex 的 marketplace schema 与发现面。
不要把 0.18.x 的“14 个 game-*”期望套到 2.0.1。

## 前置条件

- 已安装 Codex CLI，且你能在隔离目录启动它
- 完整插件根（Release 解包后的 `plugin/` 或仓库 `plugin/`）
- 隔离验证时：把 `HOME` 与 `CODEX_HOME` 指到临时目录；不要改你的日常 `~/.codex/`
- 历史隔离验收曾用符号链接指向真实 `auth.json`。**本任务禁止用你的凭据去装真实客户端**

## 取得安装包并核对

```sh
# 在同时放有 tarball 与 SHA256SUMS.txt 的目录
shasum -a 256 -c SHA256SUMS.txt
tar -tzf mygamestudio-2.0.1.tar.gz | head
```

解压后插件根是 `plugin/`。应能看到 `.codex-plugin/plugin.json` 与 `skills/`。

包内辅助脚本在 `plugin/records/`、`plugin/internal/`、`plugin/provenance/`。
安装后应能从插件根解析这些相对路径；写入权限以项目授权为准，安装本身不授权改游戏文件。

## 隔离安装布局（0.18.x 验收脚本，待在 2.0.1 复核）

验收脚本把插件链到 `$HOME/plugins/mygamestudio`，并在 `$HOME/.agents/plugins/marketplace.json` 登记本地源。`source.path` 写为 `./plugins/mygamestudio`（相对 HOME 解析，与脚本布局一致）：

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

曾执行的发现与安装命令：

```sh
export HOME=<隔离home>
export CODEX_HOME=<隔离codex-home>
codex plugin list --json --available
codex plugin add mygamestudio@personal --json
codex plugin list --json
```

历史安装副本位于 `$CODEX_HOME/plugins/cache/personal/mygamestudio/<版本>/`。
0.18.0 升级曾实测 `codex plugin remove mygamestudio@personal` 后再 `add`。

会话重启：新开 Codex 会话后再查技能列表。具体交互以你的 Codex 版本为准（未在本环境核对 UI）。

## 技能发现与一次最小只读调用

期望（2.0.1，**尚未在真实 Codex 上核对**）：发现正式 25 项加 `game-producer`、`game-init`、`game-design`，同名唯一。

最小只读调用：在游戏项目中请助手使用 `game-producer` 或 `game-init`，并明确“这一轮不修改文件”。文案见 [快速开始](../getting-started.md)。

## 更新、卸载、冲突

见 [升级与卸载](upgrade-and-uninstall.md)。

## 未验证与已知限制

- 2.0.1 未安装到日常 Codex
- 本环境未运行 `codex` 命令
- Codex App / 非 CLI 宿主未单独验证
- 0.18.x 证据不能证明 2.0.1 的发现面与权限行为

# Claude Code 安装

## 适用与验证状态

| 项 | 记录 |
| --- | --- |
| 客户端 | Claude Code |
| 插件版本 | 2.0.2（[v2.0.2](https://github.com/LC-86/MyGameStudio/releases/tag/v2.0.2) 已发布；源码与仓库内安装包一致。真实安装见下表，未验证 ≠ 未发版） |
| 结构检查 | `tests/test_multi_client.py` 核对 `.claude-plugin/plugin.json` 的 name/version 与 Codex / ZCode 清单一致，且不注册 MCP |
| 真实 Claude Code 安装、技能发现、只读调用 | **未验证** |
| 本整理环境 | 未安装 `claude` CLI，**未执行**客户端命令 |
| 文档来源 | [Create plugins](https://code.claude.com/docs/en/plugins)、[Plugins reference](https://code.claude.com/docs/en/plugins-reference)、[Discover and install plugins](https://code.claude.com/docs/en/discover-plugins)、[Plugin marketplaces](https://code.claude.com/docs/en/plugin-marketplaces)（查阅于 2026-09-17） |

## 前置条件

- 已安装 Claude Code
- 完整插件根（Release 或仓库 `dist/` 解包后的 `plugin/`），内含 `.claude-plugin/plugin.json`、`skills/`、`internal/`、`records/`、`templates/`、`provenance/` 与许可
- 隔离验证时用 `/tmp` 副本加 `claude --plugin-dir`，不要写入日常 `~/.claude/`

Python 记录层见 [安装总述](README.md)。最低 Python 版本未单独测定。

## 取得安装包并核对

```sh
grep ' mygamestudio-2.0.2.tar.gz$' SHA256SUMS.txt | shasum -a 256 -c - && tar -xzf mygamestudio-2.0.2.tar.gz
```

插件根是解包后的 `plugin/` 目录。应能看到 `.claude-plugin/plugin.json`、`LICENSE` 与 `skills/`。

## 复制一行即可安装

官方文档给出的**会话加载**一行命令指向完整插件根（不是单个 `SKILL.md`）：

```sh
claude --plugin-dir <plugin根>
```

把 `<plugin根>` 换成解包后的 `plugin/` 绝对路径。本环境未安装 Claude Code，该命令 **未验证**。

官方市场安装不是单行指向本地目录：需要先有 marketplace，再：

```sh
claude plugin marketplace add <市场目录或源>
claude plugin install mygamestudio@<市场名>
```

本仓库**不**把 GitHub `marketplace add LC-86/MyGameStudio` 写成已核实路径（仓库根未提供已验证的 `.claude-plugin/marketplace.json` 市场清单）。本地市场需你自己准备 `marketplace.json`，且 `plugins[].source` 必须指向上述完整 `plugin/` 根。这两条命令本环境 **未验证**。

不要把 `npx skills add` / 只装单个 `SKILL.md` 当成 Claude Code 安装方式。

## 官方默认目录

查阅官方 Plugins reference（2026-09-17）：

- 会话加载：`claude --plugin-dir <插件根>`（本会话有效，不写入安装记录）
- 市场安装副本：`~/.claude/plugins/cache`
- 插件数据：`~/.claude/plugins/data/<id>/`
- 技能目录插件（`claude plugin init` 脚手架）：`~/.claude/skills/<name>/`，下一会话按 `@skills-dir` 发现；**不是**本组合包的推荐安装路径

清单约定：`.claude-plugin/plugin.json` 放在插件根内；`skills/` 与 `internal/` 等必须在插件根，不得放进 `.claude-plugin/`。`name` 为清单必填字段。本清单 `name`/`version` 与 Codex、ZCode 同为 `mygamestudio` / `2.0.2`，不注册 `mcpServers`。

## 隔离安装（文档约定，本环境未跑 Claude Code）

```sh
mkdir -p /tmp/mgs-claude-iso
cp -R plugin /tmp/mgs-claude-iso/plugin
claude --plugin-dir /tmp/mgs-claude-iso/plugin
```

不要把 `HOME` 指到你的日常目录，也不要写入 `~/.claude/plugins/`。
包内 `records/`、`internal/` 必须随插件根一起复制。安装后试一次从技能目录向上两级解析这些路径；无项目写入授权时不要改游戏文件。

## 技能发现与一次最小只读调用

期望：发现正式 25 项加 `game-producer`、`game-init`、`game-design`，同名唯一。
Claude Code 插件技能在 UI 里可能带命名空间（官方示例为 `/插件名:技能名`）。**本环境未验证发现面与调用名。**

最小只读调用文案见 [快速开始](../getting-started.md)。

## 更新、卸载、冲突

见 [升级与卸载](upgrade-and-uninstall.md)。官方卸载/更新命令本环境未执行。

## 未验证与已知限制

- 未在真实 Claude Code 执行 `--plugin-dir`、marketplace add/install、发现与调用
- 未核对本环境 `claude plugin validate`
- 未安装到日常 `~/.claude/`
- 无 MCP 依赖是 2.0.2 清单约束，不是“完全离线”

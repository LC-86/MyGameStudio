# ZCode 安装

## 适用与验证状态

| 项 | 记录 |
| --- | --- |
| 客户端 | ZCode |
| 插件版本 | 2.0.2（源码与仓库内安装包一致；GitHub Release 标签待人工上传） |
| 结构检查 | `tests/test_multi_client.py` 核对 `.zcode-plugin/plugin.json` 的 name/version 与 Codex 清单一致，且不注册 MCP |
| 真实 ZCode 安装、技能发现、只读调用 | **未验证** |
| 本整理环境 | 未安装 ZCode，**未执行**客户端命令 |
| 文档来源 | [Plugin](https://zcode.z.ai/en/docs/plugin)（2026-09-17）；主分支 README 的本地插件源步骤（issue #75 / PR #76） |

## 前置条件

- 已安装 ZCode，并且该版本支持本地 directory marketplace
- 完整插件根，内含 `.zcode-plugin/plugin.json` 与 `skills/`
- 隔离验证时把源目录放在 `/tmp` 等临时位置，不改 `~/.zcode/` 或 `~/.agents/plugins/`

Python 记录层见 [安装总述](README.md)。最低 Python 版本未单独测定。

## 取得安装包并核对

```sh
grep ' mygamestudio-2.0.2.tar.gz$' SHA256SUMS.txt | shasum -a 256 -c - && tar -xzf mygamestudio-2.0.2.tar.gz
```

插件根是解包后的 `plugin/` 目录。

## 复制一行即可安装

现行官方插件页（[Plugin](https://zcode.z.ai/en/docs/plugin)，2026-09-17）**没有**给出已核实的单行 CLI。不要编造 `zcode plugins install`，也不要把 `npx skills add` 写成受支持路径。

官方步骤：为完整 `plugin/` 根写 `marketplace.json`（`plugins[].source` 指向该目录）→ Settings → Plugins → Create → Add marketplace → Install。本环境 **未验证**。

发给 Agent 的完整提示词见 [安装总述](README.md)。

## 本地插件源（已写入仓库、待真实客户端复核）

1. 复制插件根到源目录，例如 `/tmp/mgs-zcode-source/plugins/mygamestudio/`。其内应有 `.zcode-plugin/plugin.json` 与 `skills/`。
2. 在源根目录（例如 `/tmp/mgs-zcode-source/`）写 `marketplace.json` 登记插件：`name`、`version`、`description`、`source`（指向 `./plugins/mygamestudio`）。
3. 在 ZCode 中把该目录添加为本地插件源（directory marketplace），安装 `mygamestudio`。
4. 历史说明中的安装副本位于 `~/.zcode/cli/plugins/cache/<源名>/mygamestudio/<版本>/`。**路径是否仍准确未在本环境验证。**
5. 按客户端要求重启会话后再查技能。

包内 `records/`、`internal/` 必须随插件根一起复制。安装后试一次从技能目录向上两级解析这些路径；无项目写入授权时不要改游戏文件。

## 技能发现与一次最小只读调用

隔离目录验证（文档约定，**本环境未跑 ZCode**）：源目录放在 `/tmp`，不改动既有用户源；新会话中发现 28 项技能即发现成功。

最小只读调用文案见 [快速开始](../getting-started.md)。

## 更新、卸载、冲突

见 [升级与卸载](upgrade-and-uninstall.md)。

## 未验证与已知限制

- 未在真实 ZCode 执行添加本地源、安装、发现与调用
- 未验证 ZCode 市场 schema 是否与文档中的 `marketplace.json` 字段完全一致
- 无 MCP 依赖是 2.0.2 清单约束，不是“完全离线”

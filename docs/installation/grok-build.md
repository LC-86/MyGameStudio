# Grok Build 安装

## 适用与验证状态

| 项 | 记录 |
| --- | --- |
| 客户端 | Grok Build |
| 插件版本 | 2.0.2 |
| 结构检查 | 技能 `SKILL.md` 含 `name` / `description` frontmatter；三个游戏入口的定位回退包含 `~/.grok/plugins` 与 `--plugin-dir` |
| 真实 Grok Build 安装、技能发现、只读调用 | **未验证** |
| 本整理环境 | 未安装 Grok Build，**未执行**客户端命令 |
| 文档来源 | 主分支 README 的 Grok Build 步骤（issue #75 / PR #76） |

## 前置条件

- 已安装 Grok Build
- 完整插件根（不要只拷技能文件夹）
- 隔离验证时用 `/tmp` 副本或 `--plugin-dir`，不要写入 `~/.grok/plugins/`

## 取得安装包并核对

```sh
shasum -a 256 -c SHA256SUMS.txt
tar -xzf mygamestudio-2.0.2.tar.gz
```

插件根是解包后的 `plugin/`。

## 安装方式（已写入仓库、待真实客户端复核）

把解包后的插件目录放入：

- `~/.grok/plugins/`，或
- 项目 `.grok/plugins/`，或
- 启动时 `--plugin-dir <插件根路径>`

各 `skills/*/SKILL.md` 的 YAML frontmatter（`name` / `description`）按现有格式供自动扫描。无需改技能结构。

隔离目录验证（文档约定）：把包复制到 `/tmp` 后用 `--plugin-dir /tmp/<目录>` 启动会话，确认技能可发现；不写入 `~/.grok/plugins/`。

安装后如客户端要求则重启会话。包内 `internal/` 与 `records/` 必须仍在插件根下，技能才能解析相对引用。

## 技能发现与一次最小只读调用

期望发现 28 项技能。最小只读调用见 [快速开始](../getting-started.md)。
本环境未执行 Grok Build，不把发现标为已通过。

## 更新、卸载、冲突

见 [升级与卸载](upgrade-and-uninstall.md)。

## 未验证与已知限制

- 未在真实 Grok Build 执行 `--plugin-dir` 或用户目录安装
- 未核对其市场/插件清单 schema
- 未验证包内 Python 接缝在 Grok 会话中的实际调用

# 如何选择安装方式

首个公开版本优先使用 GitHub Release 里的**完整插件包**。仓库 `plugin/` 用于对照源码、贡献和构建。

尚未验证、因此**不要宣传为受支持路径**：

- `npx skills@latest add ...` 或只安装技能目录的安装器（未验证是否保留 `internal/`、`records/` 等兄弟目录）
- 未核验的统一 `marketplace.json` 市场聚合入口
- 本仓库未提供的一键安装脚本
- 新的引擎适配或 MCP 服务

## 按客户端看

| 客户端 | 说明页 | 本整理中的验证结论 |
| --- | --- | --- |
| Codex | [codex.md](codex.md) | 0.18.x 曾在隔离 macOS + Codex CLI 0.151.0 安装；**2.0.1 日常客户端未验证** |
| ZCode | [zcode.md](zcode.md) | 安装步骤已写入仓库并有结构检查；**真实 ZCode 安装未验证** |
| Grok Build | [grok-build.md](grok-build.md) | 目录与 `--plugin-dir` 步骤已写入；**真实 Grok Build 安装未验证** |

升级、卸载、同名技能冲突：[upgrade-and-uninstall.md](upgrade-and-uninstall.md)。

## 解包后哪个目录才是插件根

```text
mygamestudio-2.0.1.tar.gz
└── plugin/          ← 插件根
    ├── .codex-plugin/plugin.json
    ├── .zcode-plugin/plugin.json
    ├── skills/
    ├── internal/
    ├── records/
    ├── templates/
    └── provenance/
```

把这一层交给客户端，而不是把整个 git 仓库根当成插件。

## 运行前置

- 宿主客户端本身（Codex / ZCode / Grok Build）需你另行安装。本环境未安装这些客户端。
- 游戏记录层的本地脚本使用 `python3`。本仓库检查曾在 Python 3.12.3（Linux）与证据中的 Python 3.14.4（macOS）运行；**未单独测定最低 Python 版本**。
- GitHub Issues 模式需要 `gh`（或文档所述传输层）、账号，以及 CONFIG 里明确到仓库的 issues-write 授权。
- 无专用 MCP 服务，不等于完全离线。

# 如何选择安装方式

首个公开版本优先使用 GitHub Release 里的**完整插件包**。仓库 `plugin/` 用于对照源码、贡献和构建。尚未打 `v2.0.2` GitHub 标签时，使用仓库 `dist/`。

尚未验证、因此**不要宣传为受支持路径**：

- `npx skills@latest add ...` 或只安装技能目录的安装器（未验证是否保留 `internal/`、`records/` 等兄弟目录）
- 未核验的统一 `marketplace.json` 市场聚合入口
- 本仓库未提供的一键安装脚本
- 新的引擎适配或 MCP 服务
- 未在现行官方文档中核实的宿主 CLI（见下表「未验证」行，不要编造）

## 复制一行即可安装

安装目标必须是 **Release tar 解包后的 `plugin/` 完整插件根**（含 `skills/`、`internal/`、`records/`、`templates/`、`provenance/`、许可）。不要只拷单个 `SKILL.md`。

先核对并解包：

```sh
shasum -a 256 -c SHA256SUMS.txt && tar -xzf mygamestudio-2.0.2.tar.gz
```

再把 `<plugin根>` 换成该 `plugin/` 的绝对路径，按宿主执行一行：

```sh
claude --plugin-dir <plugin根>
```

```sh
codex plugin add mygamestudio@personal
```

```sh
grok plugin install <plugin根> --trust
```

| 客户端 | 这一行的含义 | 核实状态 |
| --- | --- | --- |
| Claude Code | 官方会话加载，参数必须是完整插件根。来源：[Create plugins](https://code.claude.com/docs/en/plugins) | **未验证**（本环境无 `claude`） |
| Codex | 官方 CLI 安装；`marketplace.json` 的 `source.path` 必须先指向完整插件根。来源：[Build plugins](https://developers.openai.com/codex/plugins/build) | **已验证**（Linux + Codex CLI 0.154.0 隔离 HOME/`CODEX_HOME`） |
| Grok Build | 官方从本地路径安装完整插件。来源：[Grok CLI](https://docs.x.ai/build/cli/reference) 与 Grok Build 插件说明中的 `grok plugin install <source> --trust` | **未验证**（本环境无 `grok`）。会话加载另有官方 `grok --plugin-dir <plugin根>`，同样未验证 |
| ZCode | **无已核实单行 CLI**。现行官方插件页给出的是 Settings → Plugins → Create → Add marketplace，再 Install。来源：[Plugin](https://zcode.z.ai/en/docs/plugin) | **未验证**。不要把未核对的 `zcode plugins install` 写成受支持路径 |

Codex 一行之前仍需本地市场登记，步骤见 [codex.md](codex.md)。各宿主细节与隔离验证见专页。

## 复制一段指令发给 Agent 来安装

把下面整段发给助手。它必须装完整插件根，不得改用 `npx skills add` 或只拷单个 `SKILL.md`。

```text
请安装 MyGameStudio 2.0.2 完整插件，不要使用 npx skills add，也不要只拷单个 SKILL.md。

1. 下载指定版本包 mygamestudio-2.0.2.tar.gz 与 SHA256SUMS.txt（GitHub Release；若尚无 v2.0.2 标签则用仓库 dist/）。
2. 在同目录执行：shasum -a 256 -c SHA256SUMS.txt。核对失败则停止。
3. 解包：tar -xzf mygamestudio-2.0.2.tar.gz。安装目标是解包后的 plugin/ 目录，必须同时含 skills、internal、records、templates、provenance 与许可文件。
4. 按客户端放到规定目录或走宿主插件命令（把 <plugin根> 换成该 plugin/ 的绝对路径）：
   - Claude Code：claude --plugin-dir <plugin根>（官方会话加载）。持久安装需自备 marketplace.json 且 source 指向该 plugin 根，再 claude plugin marketplace add <市场目录> 与 claude plugin install mygamestudio@<市场名>。官方缓存 ~/.claude/plugins/cache。本环境未验证。
   - Codex：先在隔离 HOME 的 ~/.agents/plugins/marketplace.json 把 source.path 指向该 plugin 根，再执行 codex plugin add mygamestudio@personal。隔离安装已验证；日常 ~/.codex/ 未验证。
   - ZCode：现行官方文档是 Settings → Plugins → Create → Add marketplace，指向含 marketplace.json 的源（plugins[].source 指向完整 plugin 根）再 Install。单行 CLI 未核实，不要编造。
   - Grok Build：grok plugin install <plugin根> --trust，或 grok --plugin-dir <plugin根>。官方默认还会扫描 ~/.grok/plugins/ 与 ./.grok/plugins/。本环境未验证。
5. 确认发现 28 项技能（Matt 正式 25 项 + game-producer、game-init、game-design），同名唯一。
6. 隔离验证：把副本和 HOME / 插件缓存指到 /tmp 等临时目录；不要写入日常 ~/.claude/、~/.codex/、~/.zcode/、~/.grok/ 或用户日常技能目录。
```

## 按客户端看

| 客户端 | 说明页 | 本整理中的验证结论 |
| --- | --- | --- |
| Codex | [codex.md](codex.md) | 2.0.2 在 Linux + Codex CLI 0.154.0 隔离 HOME/`CODEX_HOME` 下 `plugin add`/`remove` **已验证**；日常目录与新会话发现 **未验证** |
| ZCode | [zcode.md](zcode.md) | 安装步骤已写入仓库并有结构检查；**真实 ZCode 安装未验证** |
| Grok Build | [grok-build.md](grok-build.md) | 目录与 `--plugin-dir` / `grok plugin install` 步骤已写入；**真实 Grok Build 安装未验证** |
| Claude Code | [claude-code.md](claude-code.md) | 清单与 `--plugin-dir` 步骤已写入；**真实 Claude Code 安装未验证** |

升级、卸载、同名技能冲突：[upgrade-and-uninstall.md](upgrade-and-uninstall.md)。

## 解包后哪个目录才是插件根

```text
mygamestudio-2.0.2.tar.gz
└── plugin/          ← 插件根
    ├── LICENSE
    ├── THIRD_PARTY_NOTICES.md
    ├── .codex-plugin/plugin.json
    ├── .zcode-plugin/plugin.json
    ├── .claude-plugin/plugin.json
    ├── skills/
    ├── internal/
    ├── records/
    ├── templates/
    └── provenance/
```

把这一层交给客户端，而不是把整个 git 仓库根当成插件。

## 运行前置

- 宿主客户端本身（Codex / ZCode / Grok Build / Claude Code）需你另行安装。
- 游戏记录层的本地脚本使用 `python3`。本仓库检查曾在 Python 3.12.3（Linux）与证据中的 Python 3.14.4（macOS）运行；**未单独测定最低 Python 版本**。
- GitHub Issues 模式需要 `gh`（或文档所述传输层）、账号，以及 CONFIG 里明确到仓库的 issues-write 授权。
- 无专用 MCP 服务，不等于完全离线。

# MyGameStudio

面向个人独立游戏开发者的工作流插件。源码版本：**2.0.0**。

通用流程使用固定版本的 Matt 正式 25 项技能。游戏侧公开入口为：

- **Game-Producer**：只读查询目标、进度、缺口与建议，并按调用合同路由；不自动串调 Matt 用户专用入口。
- **Game-Init**：分析已有游戏并补齐必要游戏接入资料；通用 tracker / 标签 / 领域文档交给 `setup-matt-pocock-skills`。
- **Game-Design**：玩法、数值与体验讨论；复用 `grilling` 与 `domain-modeling`；大型不清晰路线提示调用 `wayfinder`。

读取专业资料不会自行启动制作。普通调用不需要 mgs-gate。无提交授权时 `implement` 保留未提交成果。旧入口去向见 [plugin/internal/game/retired-entries.md](plugin/internal/game/retired-entries.md)。

## 版本与使用

- [已发布版本与安装包](https://github.com/LC-86/MyGameStudio/releases)。
- [变更说明与安装材料](dist/CHANGELOG.md)。
- [来源、许可与适配记录](plugin/provenance/manifest.md)。
- [确定性检查与历史验收复现方法](dist/REPRODUCE.md)。

本候选包尚未作为正式发版安装到日常客户端。发版安装由后续票处理。反馈问题时提供使用版本、客户端（Codex / ZCode / Grok Build）、调用入口、项目任务后端、复现步骤、预期与实际结果，以及去除凭据后的错误日志。

## 多客户端安装

交付包同时适配 Codex、ZCode 与 Grok Build：包内同时携带 Codex 清单 `plugin/.codex-plugin/plugin.json` 与 ZCode 清单 `plugin/.zcode-plugin/plugin.json`，两份清单 name/version 保持一致（`tests/test_multi_client.py` 回归防漂移）。技能本体在 `skills/` 目录，按各客户端约定自动发现，无 MCP 依赖。安装与验证均可在隔离目录完成，不写入真实用户目录；装入日常客户端由你手动执行。

### ZCode（本地插件源）

1. 解包 dist 安装包（或复制仓库 `plugin/`）为插件目录，例如 `/tmp/mgs-zcode-source/plugins/mygamestudio/`，其内应有 `.zcode-plugin/plugin.json` 与 `skills/`。
2. 在源根目录（如 `/tmp/mgs-zcode-source/`）写 `marketplace.json` 登记插件：`name`、`version`、`description`、`source`（指向 `./plugins/mygamestudio`）。
3. 在 ZCode 中把该目录添加为本地插件源（directory marketplace），安装 `mygamestudio`；安装副本位于 `~/.zcode/cli/plugins/cache/<源名>/mygamestudio/<版本>/`。

隔离目录验证：源目录放在 /tmp 下，不改动 `~/.agents/plugins/` 等既有源；新会话中发现 28 项技能（Matt 正式 25 项 + Game-Producer / Game-Init / Game-Design）即发现成功。

### Grok Build

- 把解包后的插件目录放入 `~/.grok/plugins/` 或项目 `.grok/plugins/`，或启动时以 `--plugin-dir <PATH>` 指向解包目录。
- 各 `skills/*/SKILL.md` 的 YAML frontmatter（`name` / `description`）与现有格式兼容，自动扫描发现，无需改技能结构。

隔离目录验证：把包复制到 /tmp 目录后用 `--plugin-dir /tmp/<目录>` 启动会话，确认技能可发现；不写入 `~/.grok/plugins/`。

## 开发检查

在仓库根目录执行以下聚合入口：

```sh
python3 -B tests/test_plugin_package.py
python3 -B tests/test_records_backend.py
python3 -B tests/test_github_backend.py
python3 -B tests/test_legacy_retirement.py
```

交付包由 `dist/build-package.sh` 构建，版本来自 `plugin/.codex-plugin/plugin.json`（ZCode 清单版本由 `tests/test_multi_client.py` 核对同步）。旧 gate 检查已移出有效套件，历史材料在 `legacy/`。

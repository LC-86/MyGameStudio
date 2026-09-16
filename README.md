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

本候选包尚未作为正式发版安装到日常 Codex。发版安装由后续票处理。反馈问题时提供使用版本、调用入口、项目任务后端、复现步骤、预期与实际结果，以及去除凭据后的错误日志。

## 开发检查

在仓库根目录执行以下聚合入口：

```sh
python3 -B tests/test_plugin_package.py
python3 -B tests/test_records_backend.py
python3 -B tests/test_github_backend.py
python3 -B tests/test_legacy_retirement.py
```

交付包由 `dist/build-package.sh` 构建，版本来自 `plugin/.codex-plugin/plugin.json`。旧 gate 检查已移出有效套件，历史材料在 `legacy/`。

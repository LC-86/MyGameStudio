# MyGameStudio

面向个人独立游戏开发者的工作流插件，覆盖设计、任务安排、制作、构建与独立验证。源码版本：**0.18.1**。

十四个业务入口仅在用户显式调用或制作统筹明确委派时触发：

- 管理：Game-Status、Game-Producer、Game-Init、Game-Plan。
- 设计：Game-Design、Game-Spec、Game-Prototype。
- 制作：Game-Implement、Game-Code、Game-Art、Game-Audio、Game-Build。
- 验证：Game-Review、Game-Playtest。

任务后端支持本地 Markdown 与 GitHub Issues；项目写入经 mgs-gate 受控通道执行。已有项目由 Game-Init 分析现状并按确认后的清单接入。

## 版本与使用

- [已发布版本与安装包](https://github.com/LC-86/MyGameStudio/releases)。
- [变更说明与安装材料](dist/CHANGELOG.md)。
- [运行保障接入协议](plugin/internal/protocols/gate-protocol.md)。
- [确定性检查与历史验收复现方法](dist/REPRODUCE.md)。
- [本轮架构重构收尾](.scratch/mygamestudio-architecture-refactor/CLOSURE.md)。

PR #28 已完成三轮独立代码审查并合并到 main。用户决定跳过本轮隔离宿主验收，进入正常环境使用，再根据实际问题反馈改进；未执行的真实环境检查不标记为通过。

反馈问题时提供使用版本、调用入口、项目任务后端、复现步骤、预期与实际结果，以及去除凭据后的错误日志，便于固定回归条件。

## 开发检查

在仓库根目录执行以下五套聚合入口，覆盖 41 个行为主题：

```sh
python3 -B tests/test_plugin_package.py
python3 -B tests/test_records_backend.py
python3 -B tests/test_github_backend.py
python3 -B tests/test_runtime_gate.py
python3 -B tests/test_runtime_boundaries.py
```

交付包由 `dist/build-package.sh` 构建，版本来自 `plugin/.codex-plugin/plugin.json`。提交后使用 `dist/verify-reproducible.sh` 校验干净副本重建与交付包的一致性。

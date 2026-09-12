# MyGameStudio 架构重构收尾与 0.18.1 发布记录

日期：2026-09-12。架构重构、代码审查与发布候选验证已完成；用户已确认本次收尾执行授权。发布状态与最终提交以 [v0.18.1 Release](https://github.com/LC-86/MyGameStudio/releases/tag/v0.18.1) 为准。

## 已完成的工程工作

- 26 张工单及其依赖顺序已完成，具体交付和历史证据保留在各票、execution-log.md 与 evidence/ 下。
- [PR #28](https://github.com/LC-86/MyGameStudio/pull/28) 经三轮独立 Standards / Spec 审查后合并，main 合并提交为 `45a6508a98adb9025246ca50a3a8a16536d508fc`，对应产品提交为 `806c41e92d895ba4aa4f6a9dcf2566a586fa949f`。
- 前两轮的 CLI 分离、工单分流状态、客户端等待策略、文档别名和 CONFIG 自映射读取问题均已闭合。
- [第三轮审查](https://github.com/LC-86/MyGameStudio/pull/28#issuecomment-5643666675)通过，唯一 P3 非阻塞备注为报告物理行数 691 应为 693；本次收尾已同步修正。

## 用户的发布决定

用户明确决定：“可以直接进入正常的环境进行使用了。如果在使用过程中有问题再进行反馈，不需要在隔离环境中做宿主验收了。”同时要求整个项目收尾并发布新版本。

据此，取消本轮隔离宿主验收作为发布前置，转入正常使用反馈。真实模型、真实验收远端写入与人工体验没有在本次发布工作中执行，仍如实记为未验证；不将取消验收写成通过，也不将 0.18.0 的历史结果替代本版本证据。该决定覆盖 final-integrated-report.md 第 8 节此前保留待定的发布安排。

## 发布内容与恢复依据

- 版本：0.18.1；采用补丁版本，因为本轮保持已有外部用法，主要交付内部重构与行为修复。
- 业务代码以已合并的 PR #28 为依据，本次发布准备更新版本元数据、来源说明、收尾文档与生成资产。
- 发布资产：`mygamestudio-0.18.1.tar.gz`、`package-manifest.txt`、`SHA256SUMS.txt`；发布说明以 `dist/CHANGELOG.md` 的 0.18.1 节为依据。
- 恢复参照：[v0.18.0 Release](https://github.com/LC-86/MyGameStudio/releases/tag/v0.18.0)。既有发布与标签保留，恢复时使用同版本的包、清单与校验和。
- 当前只有一个工作树；已将本地主分支快进到合并后的 main。开发分支和历史证据保留，不做破坏性历史或文件清理。

## 验证记录

本次针对 0.18.1 发布候选重新执行并读取结果：

- `python3 -B tests/test_plugin_package.py`：通过。
- `python3 -B tests/test_records_backend.py`：通过。
- `python3 -B tests/test_github_backend.py`：通过。
- `python3 -B tests/test_runtime_gate.py`：通过。
- `python3 -B tests/test_runtime_boundaries.py`：通过。
- plugin-creator 元数据与结构校验器：通过。
- 将当前 plugin 目录复制到干净临时目录，用原构建脚本重建；三项发布资产与 dist 逐字节一致，tar 无 PAX 扩展头。此项是未提交候选的目录快照验证；正式提交后再运行 `dist/verify-reproducible.sh` 的 `git archive HEAD` 绑定核验。
- 包内文件：91 个。安装包 SHA-256：`4c26e64250a83bff3af8e2f7cfee29ef235d374cb68725963bc7a4e4b213d091`。
- 相对已审查 main，业务 Python、runtime、十四个 Skill、内部方法和模板均未改动；包内仅版本元数据与来源说明更新。

发布准备核查时，GitHub 父工单 #1 与重构工单 #2–#27 均为 open，共 27 项。用户已确认收尾执行授权；关闭时回填已合并 PR、审查结论及发布记录，实际状态以各工单的关闭事件为准。

## 使用反馈

后续发现的问题记录使用版本、入口、项目后端、复现步骤和实际证据，先固定可复现条件，再进行修复与回归验证。保留用户已有项目资料和实际使用环境；发布新版本本身不自动改写项目配置或任务数据。

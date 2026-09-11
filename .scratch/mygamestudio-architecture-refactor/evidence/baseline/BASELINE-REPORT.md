# 票 01 行为与效率基线报告

- 生成时间:2026-09-11T23:23:33+08:00
- 平台/解释器:macOS-26.5.1-arm64-arm-64bit-Mach-O / Python 3.14.4
- HEAD:b8cda58ea2ff3b0fb18ae7d888cbd5d01eaca586(分支 codex/architecture-optimization)
- 插件版本:mygamestudio 0.18.0
- 开始时排除基线产物的工作区是否干净:是(本票零产品行为变更)

## 1. 现有五套确定性检查(实跑结果)

| 套件 | 结果 | 退出码 | 耗时(s) | 原始输出 |
| --- | --- | --- | --- | --- |
| test_plugin_package | PASS | 0 | 6.715 | `.scratch/mygamestudio-architecture-refactor/evidence/baseline/results/checks/test_plugin_package.txt` |
| test_runtime_gate | PASS | 0 | 1.723 | `.scratch/mygamestudio-architecture-refactor/evidence/baseline/results/checks/test_runtime_gate.txt` |
| test_runtime_boundaries | PASS | 0 | 0.732 | `.scratch/mygamestudio-architecture-refactor/evidence/baseline/results/checks/test_runtime_boundaries.txt` |
| test_records_backend | PASS | 0 | 1.433 | `.scratch/mygamestudio-architecture-refactor/evidence/baseline/results/checks/test_records_backend.txt` |
| test_github_backend | PASS | 0 | 2.482 | `.scratch/mygamestudio-architecture-refactor/evidence/baseline/results/checks/test_github_backend.txt` |

五套合计:全部通过。

## 2. 代码身份与六方向覆盖

- `plugin/records/mgs_github.py`:1848 行,sha256 `9da929143f111336…`
- `plugin/records/mgs_records.py`:1109 行,sha256 `8c1cbeae81663be0…`
- `plugin/runtime/mgs_runtime.py`:1119 行,sha256 `57009cdfc9d6348d…`
- `plugin/runtime/mcp_gate.py`:261 行,sha256 `3c2b755916bd8246…`
- `plugin/runtime/mgsrt_admin.py`:189 行,sha256 `f84f883d7f9fa06a…`
- 生产代码合计:4526 行

| 重构方向 | 规范/设计入口 |
| --- | --- |
| 0 固定基线 | `spec.md#solution`, `issues/01-behavior-baseline.md` |
| 1 原子任务读取统一 | `task-reading.md`, `issues/02-record-semantics.md`, `issues/03-record-source.md`, `issues/04-ready-single-read.md` |
| 2 验收判据与测试组织 | `issues/08-mcp-evidence.md`, `issues/09-curl-evidence.md`, `issues/10-package-tests.md`, `issues/11-backend-tests.md`, `issues/12-runtime-tests.md` |
| 3 验收客户端去重 | `issues/13-shared-client-expand.md`, `issues/14-shared-client-basic-migrate.md`, `issues/15-shared-client-absolute.md`, `issues/16-shared-client-relative.md`, `issues/17-client-contract.md` |
| 4 工作结果发布恢复 | `issues/18-result-publication.md`, `issues/19-recovery-ownership.md`, `issues/20-recovery-entrypoints.md` |
| 5 受控写入内部整理 | `issues/21-controlled-local-write.md`, `issues/22-controlled-remote-write.md` |
| 6 业务 Skill 与包内说明 | `issues/23-skill-common-expand.md`, `issues/24-skill-remaining-migrate.md`, `issues/25-skill-contract.md` |

## 3. 读取计数与 R1 缺陷证据(合成回放)

- 本地 ready:CONFIG.md 6 次,task.md 2 次,最终 startable=['01-alpha']
- 本地 R1(第二次任务读取改变依赖):任务集合读取 2 次;结果落在 blocked;原因 ['依赖未解析:02-missing(任务不存在)']
- GitHub R1:全量任务集合获取 2 次(替身;真实远端请求 0);结果落在 blocked

> 这是既有缺陷的复现证据,不是长期正确性断言;普通检查套件保持全绿。

## 4. 客户端五族与解码计数(合成回放)

- 客户端 18 份 / 4605 行,归一后 5 个行为族
  - 族 0(2 份):acceptance/15-goal-change-concurrency-recovery/appserver_client.py, acceptance/16-producer-complete-loop/appserver_client.py
  - 族 1(3 份):acceptance/02-role-scoped-write/appserver_client.py, acceptance/17-github-issue-workflow/appserver_client.py, acceptance/18-complete-package-acceptance/appserver_client.py
  - 族 2(1 份):acceptance/01-explicit-project-status/appserver_client.py
  - 族 3(2 份):acceptance/03-indirect-write-failure/appserver_client.py, acceptance/04-initialize-local-project/appserver_client.py
  - 族 4(10 份):acceptance/05-adopt-existing-project/appserver_client.py, acceptance/06-idea-to-current-spec/appserver_client.py, acceptance/07-isolated-design-prototype/appserver_client.py, acceptance/08-spec-to-local-tasks/appserver_client.py, acceptance/09-code-task-delivery/appserver_client.py, acceptance/10-visual-asset-delivery/appserver_client.py, acceptance/11-audio-asset-delivery/appserver_client.py, acceptance/12-build-and-run-delivery/appserver_client.py, acceptance/13-independent-deliverable-review/appserver_client.py, acceptance/14-playtest-and-human-feedback/appserver_client.py
- 1000 条固定事件、10 次轮询:json.loads 21000 次(network=0, model_calls=0)

## 5. 代码量统计与回退参照

- 口径:tracked .py/.sh/.js/.ts/.tsx under plugin/tests/acceptance/dist, excluding evidence/fixtures directories; physical lines include comments and blanks
  - plugin:5 文件 / 4526 行
  - tests:5 文件 / 9086 行
  - acceptance:44 文件 / 20739 行
  - dist:2 文件 / 146 行
- 客户端共享化净减潜力(规划估计):3405 行
- 回退参照:本票前基点 `b8cda58ea2ff3b0fb18ae7d888cbd5d01eaca586`

## 6. 证据分类与未验证限制

- 静态事实:代码身份(SHA/指纹/行数)、代码量统计、客户端族清单。
- 合成回放:records 读取计数与 R1 复现、客户端解码计数(替身/合成,零网络)。
- 现有检查:五套 `tests/test_*.py` 的本次真实退出码与输出。
- 真实验收:本票未执行真实模型轮或真实远端写入;历史结果见 `dist/ACCEPTANCE-RESULTS.md`,仅作引用,不替代本次实测。
- 后续比较方法:每票完成后运行 run_baseline.sh,对相同范围复算上述 areas 行数、records_probe 读取次数与 client_probe 解码次数,与本次 baseline.json 逐项比较

# 票 01 行为与效率基线报告

- 生成时间:2026-09-12T00:02:47+08:00
- 平台/解释器:macOS-26.5.1-arm64-arm-64bit-Mach-O / Python 3.14.4
- HEAD:2f31a50425da6aba94097ecf3ea61c26345a8893(分支 codex/architecture-optimization)
- 插件版本:mygamestudio 0.18.0
- 工作区是否干净(原始 `git status --porcelain`):否(基线产物与主控进度文件在生成时尚未提交,故原始口径为否)
- 工作区是否干净(排除 `.scratch/` 下的票产物、工单与主控进度记录后,= 本票零产品行为变更口径):是

## 1. 现有五套确定性检查(实跑结果)

| 套件 | 结果 | 退出码 | 耗时(s) | 原始输出 |
| --- | --- | --- | --- | --- |
| test_plugin_package | PASS | 0 | 7.479 | `.scratch/mygamestudio-architecture-refactor/evidence/baseline/results/checks/test_plugin_package.txt` |
| test_runtime_gate | PASS | 0 | 1.722 | `.scratch/mygamestudio-architecture-refactor/evidence/baseline/results/checks/test_runtime_gate.txt` |
| test_runtime_boundaries | PASS | 0 | 0.723 | `.scratch/mygamestudio-architecture-refactor/evidence/baseline/results/checks/test_runtime_boundaries.txt` |
| test_records_backend | PASS | 0 | 1.147 | `.scratch/mygamestudio-architecture-refactor/evidence/baseline/results/checks/test_records_backend.txt` |
| test_github_backend | PASS | 0 | 2.507 | `.scratch/mygamestudio-architecture-refactor/evidence/baseline/results/checks/test_github_backend.txt` |

五套合计:全部通过。

## 2. 代码身份与重构阶段/票覆盖(静态事实)

- `plugin/records/mgs_github.py`:1848 行,sha256 `9da929143f111336…`
- `plugin/records/mgs_records.py`:1109 行,sha256 `8c1cbeae81663be0…`
- `plugin/runtime/mgs_runtime.py`:1119 行,sha256 `57009cdfc9d6348d…`
- `plugin/runtime/mcp_gate.py`:261 行,sha256 `3c2b755916bd8246…`
- `plugin/runtime/mgsrt_admin.py`:189 行,sha256 `f84f883d7f9fa06a…`
- 生产代码合计:4526 行

- 覆盖清单口径:阶段 0 固定基线 + 六个重构阶段方向(1-6)+ 收口,合计 26 票(01-26)

| 重构阶段方向 | 覆盖的票 / 规范入口 |
| --- | --- |
| 阶段 0 固定基线 | `design.md#阶段安排`, `issues/01-behavior-baseline.md` |
| 阶段 1 原子任务读取统一 | `task-reading.md`, `issues/02-record-semantics.md`, `issues/03-record-source.md`, `issues/04-ready-single-read.md`, `issues/05-list-show-compatible.md`, `issues/06-baseline-verify.md`, `issues/07-read-stage-closeout.md` |
| 阶段 2 验收判据与测试组织 | `issues/08-mcp-evidence.md`, `issues/09-curl-evidence.md`, `issues/10-package-tests.md`, `issues/11-backend-tests.md`, `issues/12-runtime-tests.md` |
| 阶段 3 验收客户端去重 | `issues/13-shared-client-expand.md`, `issues/14-shared-client-basic-migrate.md`, `issues/15-shared-client-absolute.md`, `issues/16-shared-client-relative.md`, `issues/17-client-contract.md` |
| 阶段 4 工作结果发布恢复 | `issues/18-result-publication.md`, `issues/19-recovery-ownership.md`, `issues/20-recovery-entrypoints.md` |
| 阶段 5 受控写入内部整理 | `issues/21-controlled-local-write.md`, `issues/22-controlled-remote-write.md` |
| 阶段 6 业务 Skill 与包内说明 | `issues/23-skill-common-expand.md`, `issues/24-skill-remaining-migrate.md`, `issues/25-skill-contract.md` |
| 收口 集成与效益核验 | `spec.md#后续阶段的必要验收`, `issues/26-integrated-verification.md` |

## 3. 读取计数与 R1 缺陷证据(合成回放)

- 本地 ready:CONFIG.md 6 次,task.md 2 次,最终 startable=['01-alpha']
- 本地 R1(第二次任务读取改变依赖):任务集合读取 2 次;结果落在 blocked;原因 ['依赖未解析:02-missing(任务不存在)']
- GitHub R1:全量任务集合获取 2 次(替身;真实远端请求 0);结果落在 blocked

> 这是既有缺陷的复现证据,不是长期正确性断言;普通检查套件保持全绿。

### 受控写入运行时读取计数(前置观测的本次复算,审查修复票 01/F6)

- runtime-write(决策 allow):policy.json 3 次, instances.json 2 次
- runtime-remote-read(决策 allow):policy.json 3 次, instances.json 2 次, remote.json 1 次, CONFIG.md 2 次;替身 transport 调用 3 次,真实远端请求 0

> 前置证据 `.scratch/.../evidence/baseline.json` 的 text/bytes 拆分未逐字节复刻:CPython 3.14 的 `Path.read_bytes()` 触发的 open 事件mode 为 `r`,本探针按文件聚合的总读取次数与前置一致(policy.json 合计 3 = text 2 + bytes 1)。

## 4. 客户端五族与解码计数(合成回放)

- 客户端 18 份 / 4605 行,归一后 5 个行为族
  - 族 0(2 份):acceptance/15-goal-change-concurrency-recovery/appserver_client.py, acceptance/16-producer-complete-loop/appserver_client.py
  - 族 1(3 份):acceptance/02-role-scoped-write/appserver_client.py, acceptance/17-github-issue-workflow/appserver_client.py, acceptance/18-complete-package-acceptance/appserver_client.py
  - 族 2(1 份):acceptance/01-explicit-project-status/appserver_client.py
  - 族 3(2 份):acceptance/03-indirect-write-failure/appserver_client.py, acceptance/04-initialize-local-project/appserver_client.py
  - 族 4(10 份):acceptance/05-adopt-existing-project/appserver_client.py, acceptance/06-idea-to-current-spec/appserver_client.py, acceptance/07-isolated-design-prototype/appserver_client.py, acceptance/08-spec-to-local-tasks/appserver_client.py, acceptance/09-code-task-delivery/appserver_client.py, acceptance/10-visual-asset-delivery/appserver_client.py, acceptance/11-audio-asset-delivery/appserver_client.py, acceptance/12-build-and-run-delivery/appserver_client.py, acceptance/13-independent-deliverable-review/appserver_client.py, acceptance/14-playtest-and-human-feedback/appserver_client.py
- 1000 条固定事件、10 次轮询:json.loads 21000 次(network=0, model_calls=0)

## 5. 代码量统计与产物行数口径

- 生产代码量口径:tracked .py/.sh/.js/.ts/.tsx under plugin/tests/acceptance/dist, excluding evidence/fixtures directories; physical lines include comments and blanks
  - plugin:5 文件 / 4526 行
  - tests:5 文件 / 9086 行
  - acceptance:44 文件 / 20739 行
  - dist:2 文件 / 146 行
- 客户端共享化净减潜力(规划估计):3405 行
- 回退参照:本票前基点 `b8cda58ea2ff3b0fb18ae7d888cbd5d01eaca586`

本票**新增基线产物**的行数(分列,`scratch` 下,不是生产或测试代码):

- 脚本(探针与入口 `.py`/`.sh`,8 个):1475 行
- 文档(`README.md`/`evidence-map.md`,2 个):158 行
- 文档(本报告 `BASELINE-REPORT.md`):118 行
- results 产物 JSON(5 个探针报告):1123 行
- results 产物 JSON(汇总自身 `results/baseline.json`):1255 行
- results 产物 JSON 合计(含汇总自身):2378 行
- results 检查原始日志(`checks/*.txt`,另计,非本票新写):15 行

## 6. 现有命令行入口输出结构与退出码(实跑)

- 本次实跑覆盖的 local-markdown 读取入口:`config`, `list`, `show`, `deps`, `ready`, `baseline`, `verify`
- 未覆盖(需远端/凭据,零网络不跑):`create`, `update`, `append-result`, `set-triage`, `set-relations`, `set-parent`, `close`, `publish-drafts`, `handover`, `switch-plan`, `switch-apply`
- 退出码合同:{'success': 0, 'records_or_file_error': 2, 'judgement_failure': 1}

| 案例 | 退出码 | JSON 有效 | 顶层结构 |
| --- | --- | --- | --- |
| config-success | 0 | True | backend, config_path, docmap, external, labels, project_root, remote_write_authorized, repo, task_root |
| list-success | 0 | True | array |
| show-success | 0 | True | directory, identity, path, progress, request, result_index_text, results, sections, title, triage |
| show-task-missing | 2 | True | error |
| deps-success | 0 | True | cycles, edges, ok, unresolved |
| deps-unresolved-failure | 1 | True | cycles, edges, ok, unresolved |
| ready-success | 0 | True | blocked, cached, fetched_at, note, source, startable |
| ready-blocked-still-ok | 0 | True | blocked, cached, fetched_at, note, source, startable |
| baseline-success | 0 | True | affected_tasks, docs, note, ok |
| verify-success | 0 | True | checks, ok |
| config-missing-failure | 2 | True | error |

> 字段结构只记键集合与类型、不记取值,避免时间戳等非确定字段破坏复跑稳定性;退出码覆盖成功(0)、记录/文件错误(2)与判定失败(1)。

## 7. 证据分类与未验证限制

- 静态事实:代码身份(SHA/指纹/行数)、代码量统计、客户端族清单、命令行入口输出结构与退出码。
- 合成回放:records 读取计数与 R1 复现、客户端解码计数、受控写入运行时读取计数(替身/合成,零网络)。
- 现有检查:五套 `tests/test_*.py` 的本次真实退出码与输出。
- 真实验收:本票未执行真实模型轮或真实远端写入;历史结果见 `dist/ACCEPTANCE-RESULTS.md`,仅作引用,不替代本次实测。
- 未验证限制:命令行入口基线只覆盖 local-markdown 后端与两处代表性错误路径,github-issues 专属子命令与需要远端/凭据的入口未跑;前置证据的 text/bytes 读取拆分未逐字节复刻(见第 3 节);`records_probe` 的 GitHub 用本地替身,不代表真实网络耗时或全部宿主行为。
- 后续比较方法:每票完成后运行 run_baseline.sh,对相同范围复算上述 areas 行数、records_probe 读取次数与 client_probe 解码次数,与本次 baseline.json 逐项比较

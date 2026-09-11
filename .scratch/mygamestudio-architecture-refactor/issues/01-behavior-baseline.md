# 01: 固定可复跑的兼容与效率基线

**What to build:** 维护者能在隔离环境通过现有入口复核兼容行为、历史反例和操作量，并据此比较后续每项改动。

**Blocked by:** None (can start immediately)

**Status:** resolved

**Spec:** [MyGameStudio 全插件分阶段架构重构 v1](../spec.md) · User Stories 4, 5, 6, 7, 8, 32, 60

**Verification mapping:** 按本票所属阶段的验收集合

- [x] 固定实际代码身份、现有入口输出和全部 26 票（阶段 0 基线 + 六个重构阶段方向 + 收口）的覆盖清单；区分静态事实、合成回放与真实验收。
- [x] 现有五套检查能按所需隔离条件运行并保留完整结果；任何失败或缺失不得写成已通过。
- [x] 复现 ready 的 CONFIG 六次、任务集合两次与混合时点现象；作为 R1 的缺陷证据保留，不将错误现状固化为长期正确性断言，也不将红测试留在普通通过基线中。
- [x] 记录客户端五族差异，以及一千条固定事件、十次轮询的解码计数；不启动真实模型或远端写入。
- [x] 现有案例、正向对照、已接受限制和历史证据能映射到相应行为；规范化时间字段不掩盖来源或身份差异。
- [x] 给出当前代码量统计范围、回退参照及后续比较方法；此票不改生产行为。

## 执行与验证约定

本票已正式发布；实施按对应任务授权执行。沿现有 interface 验证本票行为；保持外部用法、持久化格式、权限与恢复语义，只有明确列出的 R1 属行为修正。每票在新的执行上下文中按实际前置成果接手；产品内容变化时同步相关包与来源检查，记录净行数、必要操作量和未验证限制。

同一共享文件只由一名执行者修改。测试和独立规范/规格评审针对本票实际版本；基线不可被历史结果替代。提交、推送、标签、真实远端写入、日常安装和发布分别沿明确授权执行。

## Comments

用户已确认 26 票拆分及其依赖安排；本票按确认稿发布，未启动实施。

### 2026-09-11 执行记录（完成票 01，零产品行为变更）

**做了什么。** 在分支 `codex/architecture-optimization`（前基点
`b8cda58ea2ff3b0fb18ae7d888cbd5d01eaca586`）新增可复跑基线产物，位置
`.scratch/mygamestudio-architecture-refactor/evidence/baseline/`：

- `run_baseline.py` / `run_baseline.sh`：总入口，跑现有五套检查 + 四个探针 + 汇总。
- `code_identity.py`：静态事实（HEAD SHA、五份生产文件 SHA-256/行数、26 票覆盖清单）。
- `records_probe.py`：合成回放（用 `sys.addaudithook` 对底层读取型 `open` 计数；
  GitHub 用本地替身 transport，零网络）；含受控写入 runtime 读取计数复算。
- `client_probe.py`：客户端族归一与 1000 事件 ×10 轮询解码计数（替换 time/json.loads）。
- `code_volume.py`：代码量口径、客户端净减潜力、回退参照。
- `entry_probe.py`：经现有命令行入口实跑，固定读取命令的 JSON 输出结构与退出码。
- `baseline_common.py`：探针间共享 helper（夹具、归一化、`git()`、argparse/JSON 尾段）。
- `evidence-map.md`：现有案例/正反对照/已接受限制/历史证据的行为映射。
- 产物：`results/baseline.json`、`results/checks/*.txt`、`BASELINE-REPORT.md`、`README.md`。

**验证命令与真实结果。** `sh .scratch/.../evidence/baseline/run_baseline.sh`：

- 五套现有检查本次实跑全绿（退出码 0）：`test_plugin_package`(6.7s)、
  `test_runtime_gate`(1.7s)、`test_runtime_boundaries`(0.7s)、`test_records_backend`(1.4s)、
  `test_github_backend`(2.5s)；原始输出见 `results/checks/`。
- 本地 ready 一次读取 CONFIG.md **6 次**、task.md **2 次**，startable=`['01-alpha']`。
- R1 复现：第二次任务读取新增依赖 `02-missing` 后，本次结果把第一次任务内容与第二次依赖
  拼成 blocked（`依赖未解析:02-missing`）；GitHub 分支全量任务集合获取 **2 次**。
  上述现象只在**单独探针**中呈现，普通检查套件保持全绿——未把红测试留在通过基线。
- 解码计数：1000 条固定事件 ×10 次轮询 = **21,000 次** `json.loads`（network=0、model_calls=0）。
- 客户端：18 份 / 4,605 行，归一后 **5 族**（1/3/2/10/2），与前置调查一致。
- 代码量（同口径复算，与前置 `evidence/baseline.json` 相等）：plugin 4526、tests 9086、
  acceptance 20739、dist 146 行；客户端共享化净减潜力（规划估计）3,405 行。
- 复跑稳定性：连续两次运行 `records_probe`/`client_probe` 的稳定字段逐字节一致。

**净行数。** 生产代码 `plugin/ tests/ acceptance/ dist/` 净变化 **0 行**（`git diff --numstat`
为空）；本票新增基线产物行数分列如下（均为 `.scratch/evidence/` 下产物，不是生产或测试
代码），与 `results/baseline.json` 的 `artifact_lines` 一致：

- 脚本（探针与入口 `.py`/`.sh`，8 个）：1,432 行。
- 文档（`README.md`/`evidence-map.md`，2 个）：158 行；本报告 `BASELINE-REPORT.md`：118 行。
- results 产物 JSON（探针报告 5 个）：1,140 行；汇总自身 `results/baseline.json`：1,289 行
  （JSON 合计 2,429 行）。
- results 检查原始日志 `checks/*.txt`（另计，非本票新写）：15 行。

**未验证限制。** 本票未执行真实模型轮、真实远端写入、安装或发布；历史
`dist/ACCEPTANCE-RESULTS.md` 的通过结果仅作引用，不替代本次实测。系统级真实验收、
其他宿主（Windows/Linux/非 0.151.0 codex CLI）与人工体验仍按原票限制保留待验证。
`records_probe` 的 GitHub 替换为本地替身，不代表真实网络耗时或全部宿主行为。
命令行入口基线仅覆盖 local-markdown 后端读取命令与代表性错误路径，github-issues
专属子命令及需要远端/凭据的入口未跑（零网络、零凭据）。

### 2026-09-11 复审修复记录（第一轮独立复审发现）

逐条处理独立复审的 F1–F6 与 S1–S3；范围内只改 `.scratch/mygamestudio-architecture-refactor/`
下的基线产物与工单文件，未触及 `plugin/ tests/ acceptance/ dist/`。

- **F1（Status 规范，已修复）。** 工单 `Status` 由自造值 `done` 改为仓库约定终态
  `resolved`（`docs/agents/issue-tracker.md` 第 26 行）。
- **F2（验收条件 1 入口输出，已补齐）。** 新增 `entry_probe.py`：在 `/tmp` 隔离项目上经
  **现有命令行入口**实跑 `config/list/show/deps/ready/baseline/verify`，固定 JSON 输出
  字段结构与退出码（成功 0、记录/文件错误 2、判定失败 1；含任务缺失、依赖未解析、
  配置缺失三类代表失败）。只记键集合与类型、不记取值，保证复跑稳定；纳入
  `run_baseline.py`、`results/entry_probe.json`、`baseline.json` 与 `BASELINE-REPORT.md`
  第 6 节。覆盖范围如实登记：github-issues 专属子命令与需远端/凭据入口未跑。
- **F3（26 票覆盖清单，已修复）。** `code_identity.py` 的清单改为
  `refactor_directions`，补全阶段 1 的 05/06/07 票与收口 26 票，覆盖全部 26 票；
  计数措辞改为「阶段 0 固定基线 + 六个重构阶段方向（1-6）+ 收口，合计 26 票」，
  不再把 7/8 行表述成「六个重构方向」。报告第 2 节同步。
- **F4（行数口径，已修正）。** 原「脚本与记录合计 1,141 行」不实；改为分列脚本 /
  文档 / results 产物 JSON，并由 `run_baseline.py` 的 `artifact_lines` 按实际文件
  计算（脚本 8 个 1,432 行、文档 158 行 + 本报告 118 行、探针 JSON 1,140 行、汇总自身
  1,289 行、JSON 合计 2,429 行、检查日志另计 15 行）。报告与工单执行记录同步。
- **F5（工作区口径，已统一）。** `code_identity.json` 与 `baseline.json` 同时给出
  `worktree_clean`（原始 `git status --porcelain`，生成时为 false，因基线产物未提交）
  与 `worktree_clean_excluding_baseline`（排除 `.scratch/` 下票产物与主控进度记录后，
  即本票零产品行为变更口径，为 true）；报告引用后者时明确注明口径。
- **F6（runtime 计数，已纳入复跑）。** 在 `records_probe.py` 增加
  `runtime-write` / `runtime-remote-read` 两段合成回放：用 audit hook 在 `/tmp`
  运行根与临时项目上回放 `GateService.write()` 与 `remote_record(read)`（远端用本地
  替身 transport，零网络），复算前置 `evidence/baseline.json` 的 policy/instances/
  remote/CONFIG 读取计数。结果：runtime-write policy 3 / instances 2；runtime-remote-read
  再加 remote 1 / CONFIG 2、替身请求 3、真实远端 0。限制如实登记：CPython 3.14 的
  `Path.read_bytes()` 触发 open mode 为 `r`，故按文件聚合总次数（policy 合计 3 =
  前置 text 2 + bytes 1），未逐字节复刻 text/bytes 拆分。
- **S1（已修）。** `run_baseline.py` 不再由 command 字符串反推套件名，改用
  `run_suite` 回填的 `name` 字段。
- **S2（已修）。** `records_probe.py` 的 `get_log` 更名为 `request_log`（如实表达为
  全部请求日志）。
- **S3（已做，低风险共享 helper）。** 新增同目录 `baseline_common.py`，收拢四类同形
  重复：探针 argparse/`--out`/JSON 尾段、`git()` 助手、客户端源码归一化、临时项目与
  任务夹具；`records_probe/client_probe/code_volume/code_identity/entry_probe` 均改用。
  不作进一步抽象；README 注明保留的探针特有重复与接受理由。

**验证命令与真实结果（复审修复后）。**

- `sh .scratch/mygamestudio-architecture-refactor/evidence/baseline/run_baseline.sh`
  退出码 0，五套检查全绿（`all_existing_checks_green=True`），新产物含
  `results/entry_probe.json`。
- 复跑稳定性抽查：连续两次运行，`baseline.json` 稳定字段（排除 `generated_at` 与各套
  `duration_seconds`）、`records_probe.json`、`entry_probe.json` 逐字节一致。
- 红线：`git diff --numstat -- plugin tests acceptance dist` 为 0 行。

### 2026-09-11 第二轮修复记录（第二轮复审发现 R1–R5）

逐条处理第二轮独立复审的 R1–R5；范围内只改 `.scratch/mygamestudio-architecture-refactor/`
下的基线产物与工单文件，未触及 `plugin/ tests/ acceptance/ dist/`。

- **R1（同形重复，已收敛）。** 删除 `run_baseline.py` 内联的 `git status --porcelain`
  与本地 `non_product=(".scratch/",)` 判断；工作区披露的唯一实现上收为
  `baseline_common.worktree_state()`（复用 `git()` 与 `NON_PRODUCT_MARKERS`），
  `code_identity.py` 与 `run_baseline.py` 均改为调用它。行为语义不变：仍同时给出
  原始口径与排除 `.scratch/` 后的口径，字段名与报告措辞保持一致。
- **R2（死返回值，已删除）。** `write_report` 的返回类型由 `int` 改为 `None`，删除
  末尾 `return len(text.splitlines())`；报告自身行数实由内部 `SELF_REPORT_MARKER`
  在写盘前回填，调用处不再有被丢弃的「回填」返回值，注释/文档串同步说明。
- **R3（陈旧注释，已修正）。** `baseline_common.py` 模块 docstring 与
  `parse_out_args`/`emit` 文档串中的「四个探针」改为「五个探针」；同时把共享范围
  描述补上 `git()` 与工作区状态披露，不再留可陈旧计数值。
- **R4（行数稳定性，已修复）。** 新增 `json_line_count()`：results 产物 JSON 在计数
  前按与写盘一致的缩进重排为规范 JSON，并置空不稳定字段
  （`worktree_porcelain`/`worktree_porcelain_at_start` 列表，`generated_at`、
  `duration_seconds` 标量），再计算行数；解析失败回退物理行数。`collect_lines`
  的 `results_json` 分项与报告中「汇总自身」均改用该口径；汇总自身不再随工作区
  状态漂移。验收（见下）连续三次各分项完全一致，且新增无关未跟踪文件后仍不变。
  修复后 `results_json_total`=1,123（探针 5 个：code_identity 118 / records 105 /
  client 288 / code_volume 93 / entry 519），`scripts_total`=1,475，
  `docs_total`=158，检查日志另计 15 行。
- **R5（措辞与机制不符，已统一）。** `collect_lines` 的 `note` 原称「文档=
  README/evidence-map/报告 .md」，但 `ARTIFACT_DOCS` 只含 README/evidence-map、
  本报告经 `SELF_REPORT_MARKER` 单独回填。改为「文档=README/evidence-map .md
  （本报告 BASELINE-REPORT.md 行数在报告中单独回填,不并入 docs）」，并注明 JSON
  行数为剥离不稳定字段后的确定性口径；常量上方注释同步。

**验证命令与真实结果（第二轮修复后）。**

- `sh .scratch/mygamestudio-architecture-refactor/evidence/baseline/run_baseline.sh`
  退出码 0，五套检查全绿（`all_existing_checks_green=True`；本次 7.163s / 1.736s /
  0.746s / 0.94s / 2.489s）。
- 连续三次运行：`baseline.json` 稳定字段（排除 `generated_at`、`duration_seconds`）
  规范化后 SHA-256 三次均为
  `e45087b0ab6f99ba262316e8d6763d09f75ca5db3e83afb746961b07555b0280`，逐字节一致；
  `artifact_lines` 各分项三次一致。
- 新增无关未跟踪文件（`/tmp` 生成后复制到仓库根 `mgs_unrelated_probe.txt`，验证后
  删除）后第三次运行：`artifact_lines` 各分项与新增前完全一致（`results_json` 与
  汇总自身走剥离口径，不再随 porcelain 清单漂移）。验证后已清理该临时文件并复跑
  一次生成干净产物。
- 红线：`git diff --numstat -- plugin tests acceptance dist` 为 0 行（0 行输出）。


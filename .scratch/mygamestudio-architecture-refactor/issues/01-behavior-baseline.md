# 01: 固定可复跑的兼容与效率基线

**What to build:** 维护者能在隔离环境通过现有入口复核兼容行为、历史反例和操作量，并据此比较后续每项改动。

**Blocked by:** None (can start immediately)

**Status:** done

**Spec:** [MyGameStudio 全插件分阶段架构重构 v1](../spec.md) · User Stories 4, 5, 6, 7, 8, 32, 60

**Verification mapping:** 按本票所属阶段的验收集合

- [x] 固定实际代码身份、现有入口输出和六个重构方向的覆盖清单；区分静态事实、合成回放与真实验收。
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
- `code_identity.py`：静态事实（HEAD SHA、五份生产文件 SHA-256/行数、六方向覆盖清单）。
- `records_probe.py`：合成回放（用 `sys.addaudithook` 对底层读取型 `open` 计数；
  GitHub 用本地替身 transport，零网络）。
- `client_probe.py`：客户端族归一与 1000 事件 ×10 轮询解码计数（替换 time/json.loads）。
- `code_volume.py`：代码量口径、客户端净减潜力、回退参照。
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
为空）；本票新增基线脚本与记录合计 1,141 行（含报告/映射文档，均为 `.scratch/evidence/` 下
产物，不是生产或测试代码）。

**未验证限制。** 本票未执行真实模型轮、真实远端写入、安装或发布；历史
`dist/ACCEPTANCE-RESULTS.md` 的通过结果仅作引用，不替代本次实测。系统级真实验收、
其他宿主（Windows/Linux/非 0.151.0 codex CLI）与人工体验仍按原票限制保留待验证。
`records_probe` 的 GitHub 替换为本地替身，不代表真实网络耗时或全部宿主行为。

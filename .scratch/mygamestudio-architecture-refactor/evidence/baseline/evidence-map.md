# 现有行为案例、正向对照、已接受限制与历史证据映射

本文件是票 01 的静态清点:把仓库中**已经存在**的验收案例、正向对照、已接受
限制与历史证据映射到相应行为,供后续每票在重构后逐项追溯,避免通过删测试
或改叙述制造通过。所有路径相对仓库根。

## 1. 18 个验收案例 → 行为 → 证据位置

| 场景 | 覆盖行为 | 运行脚本 | 证据目录 |
| --- | --- | --- | --- |
| 01 显式项目状态 | 显式触发、状态只读 | `acceptance/01-.../run.sh` | `acceptance/01-.../evidence/` |
| 02 角色受限写入 | 角色∩任务∩用途∩授权、审计 | `acceptance/02-.../run.sh` | 同上 |
| 03 间接写入与检查故障 | 失效闭合、换链、别名不扩权 | `acceptance/03-.../run.sh` | 同上 |
| 04 新项目初始化 | 清单确认后建立配置/文档/本地任务 | `acceptance/04-.../run.sh` | 同上 |
| 05 接手已有项目 | 只读分析、复用资料、中断恢复 | `acceptance/05-.../run.sh` | 同上 |
| 06 想法到当前规格 | 设计讨论、规格与基线 | `acceptance/06-.../run.sh` | 同上 |
| 07 隔离设计原型 | 最小可检验实现、隔离工作区 | `acceptance/07-.../run.sh` | 同上 |
| 08 规格拆本地任务 | 原子任务身份/分流/依赖 | `acceptance/08-.../run.sh` | 同上 |
| 09 代码任务交付 | 受控代码写入、行为层检查 | `acceptance/09-.../run.sh` | 同上 |
| 10 视觉资源交付 | 资源制作与规格检查 | `acceptance/10-.../run.sh` | 同上 |
| 11 音频资源交付 | base64 受控写入、可播放性 | `acceptance/11-.../run.sh` | 同上 |
| 12 构建与运行交付 | 构建/导出、SHA-256 绑定 | `acceptance/12-.../run.sh` | 同上 |
| 13 独立成果审查 | 双轴审查、不修改待审成果 | `acceptance/13-.../run.sh` | 同上 |
| 14 试玩与人工反馈 | 人工结论只来自真实反馈 | `acceptance/14-.../run.sh` | 同上 |
| 15 目标变化/并发/恢复 | 占用协调、撤销、恢复 | `acceptance/15-.../run.sh` | 同上 |
| 16 统筹完整闭环 | 三类入口分类、完成判定 | `acceptance/16-.../run.sh` | 同上 |
| 17 GitHub Issues 工作流 | 同语义任务合同、受控远端、缓存与草稿 | `acceptance/17-.../run.sh`、`remote-replay.sh` | 同上 |
| 18 整包验收与升级 | 入口发现、闭环矩阵、运行保障、升级 | `acceptance/18-.../run.sh`、`driver-probes.sh` | `acceptance/18-.../evidence/` |

场景 01-17 的离线确定性等价物由五套 `tests/test_*.py` 承担(见 `BASELINE-REPORT.md`
第 1 节);票 01 已实跑五套并保留原始输出于 `results/checks/`。

## 2. 正向对照与历史反例(不得在重构中丢失)

- `tests/test_records_backend.py`、`tests/test_github_backend.py`、`tests/test_runtime_gate.py`、
  `tests/test_runtime_boundaries.py`、`tests/test_plugin_package.py` 内含具名正反例
  (如畸形任务、含糊仓库位置、循环依赖、失败闭合、字节可复现)。
- `samples/` 提供固定夹具:`conflicting-records`(冲突记录)、`not-onboarded`(未初始化)、
  `pixel-jumper`、`role-scope-demo`、`tide-pool`、`gear-city`、`nebula-drift`、`stardust-dash`。
- `.scratch/mygamestudio-v1-review-fixes/evidence/`:独立审查探针 S1–S6、R1–R6 的
  复现脚本与输出(`spec-probes.py/jsonl`、`runtime-probes.py/jsonl`、`driver-probes.log`、
  `verification-summary.json`)——历史反例的原始证据。
- `.scratch/mygamestudio-v1-review{2..10}-fixes/`:各轮审查修复票的 issue 与 evidence,
  记录"先红后绿"的回归对照(如部分成功与草稿身份、撤销在途、字节可复现、凭据脱敏)。
- `.scratch/mygamestudio-v1/spec.md`、`.scratch/mygamestudio-framework/`:原设计与验收矩阵来源。

## 3. 已接受限制(仍作限制登记,不得当作已通过)

来源:`dist/ACCEPTANCE-RESULTS.md`「三、尚未支持的工具边界」与「六、失败/未验证/待决」。

- 真实 GitHub 远端写入:已由票 17 `remote-replay.sh` 在授权测试仓库完成(38/0),
  但**本票不重放真实远端写**;后续重构仍需按授权重放。
- GUI 程序与外部 MCP 通路(真实浏览器、图像/音频外部服务):未就绪。
- TUI 选择器自动化:未做 pty 自动化。
- 其他宿主/版本(Windows、Linux、codex CLI ≠ 0.151.0):未验证。
- `codex exec` 显式调用:0.151.0 不解析 `$` 提及(版本事实)。
- 服务端模型路由可能中途切换(用 `MGS_PIN_MODEL` 固定)。
- 待人工反馈:06 审美确认、10 试听确认、08 海鸥试玩(素材已交付但未接入构建)。

## 4. 规范化时间字段不掩盖来源与身份差异

基线记录与探针遵循:
- 读取元信息区分 `cached`(回缓存)与在线新鲜结果,并携带 `fetched_at` 与 `source`;
  离线另附 `cache_note`。归一化**时间戳格式**不等于合并来源状态。
- 任务身份以 `identity` 与本地 `directory` 分别保留;本地 `show` 按目录定位,
  与正文身份不一致时仍可区分(README-07);`body_sha256` 绑定 Issue 正文,不因时间
  归一而丢失身份差异。
- 探针比较稳定字段;非确定字段(时间戳)只核对格式、来源与对应关系,不要求
  两次运行逐字节相同(与 `spec.md`「Testing Decisions」一致)。

## 5. 本票新增基线与上述材料的对应

- `results/baseline.json`:本次实测的结构化汇总(读/解码计数、五套退出码、代码量)。
- `BASELINE-REPORT.md`:人可读报告,含证据分类(静态事实/合成回放/现有检查/真实验收)。
- `results/checks/*.txt`:五套检查的完整原始输出(失败也如实保留)。
- `records_probe.py`:`dist/ACCEPTANCE-RESULTS.md` 历史通过结果**不能替代**本次实测;
  本探针独立复现 READ-01/03 现象。

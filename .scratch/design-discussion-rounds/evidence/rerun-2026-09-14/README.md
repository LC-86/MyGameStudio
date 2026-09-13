# 票 09 基线复跑证据(2026-09-14)

本目录是票 09 对票 01 采集入口的一次性复跑留档,用于记录**当前宿主状态**
与外部故障是否仍存在。采集入口、场景与计时口径与票 01 完全一致;运行在
隔离副本 `.tmp/dd09/accept/rerun/baseline/run_baseline.sh`(复制原件,仅改
`REPO_ROOT`/`BASE_DIR`/`ENVROOT`/`ARENA`),**票 01 的
`evidence/baseline/` 未被覆盖**。

## 身份语义(重要)

- `identity.json` 里的 `plugin_tree_sha256` 是**复跑时工作树的身份**
  = `ad4f88ec…`(HEAD `de8a87e`,即优化后的候选版本),**不是**优化前身份。
- 优化前内容身份仍以票 01 的 `evidence/baseline/results/identity.json` 为准:
  `9e8ee19858cadd246a56212a173d12c39873bca8f2e165be531de8b657b44eb7`。
- `identity.json` 内的 `note` 字段是测量工具 `identity` 命令的固定文案
  (为票 01 场景写的),套用到本次复跑时该措辞不描述本次对象;以本说明为准。

## 本次结果

- `sh run_baseline.sh` 等价复跑:**14 PASS / 0 FAIL**,8 个真实 turn 均
  `turn/completed`;策略字节未变;令牌已脱敏。
- `new-design.metrics.json` / `existing-change.metrics.json`:
  两类场景均 `comparability.comparable=false`、`status=incomplete`,
  0 读取 / 0 写入 / 0 检查 / 0 工具调用;例外:
  `external_fault`(宿主 `codex-code-mode-host` 启动失败)+ `incomparable`。
- 宿主:macOS 26.5.1 (arm64),`codex-cli 0.154.0`;见 `environment.txt`。
- 8 个 turn 报告全部保留(`new-design/n1..n4-report.md`、
  `existing-change/c1..c4-report.md`):均自述未能读取技能与项目文件、
  未调用 `mgs_write`;措辞各异(`code-mode-host: No such file or directory`、
  `failed to spawn code-mode host … (os error 2)`),指向同一宿主故障。

**结论用途:证明外部故障自票 01 首采(2026-09-13)至本票复跑(2026-09-14)
持续存在,两类场景仍无有效计时样本;效率结论见
`../ACCEPTANCE-REPORT.md` 第 3 节(「效率尚未验证」)。本目录不产生任何效率
对比数据,不得用作提速证据。**

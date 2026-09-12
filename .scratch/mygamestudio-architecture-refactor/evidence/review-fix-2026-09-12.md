# PR #28 双轴审查修复轮证据（2026-09-12）

对应 [PR #28 审查评论](https://github.com/LC-86/MyGameStudio/pull/28#issuecomment-5643052474)
的四项 P2 发现（ST-1/ST-2/SP-1/SP-2）。固定范围：审查基点
`49f3b1e7323c02a5fd39f3d9c847df023c4f2459` → 修复前 HEAD
`f23f323b0b7d554d65dc96eb31d70c9e164c040e`。本文件登记修复内容、验证结果与
代码身份；每项先红后绿（TDD），未修改与发现无关的行为。

## ST-1 · CLI 职责分离（mgs_records.py）

- `plugin/records/mgs_records.py` 897 → **678 行**：`_parse_fields` 与 `_cli`
  整体搬出，剩余为查询组织；不再混合命令行职责。
- 新增 `plugin/records/mgs_records_cli.py`（**273 行**）：参数解析、输出投影、
  退出码；业务行为经 `mgs_records` 公开接缝（module 级单向依赖）。
- 兼容合同：旧脚本 `mgs_records.py` 保持原调用入口（脚本守卫内把脚本实例
  注册为 `mgs_records` 后延迟导入 CLI 层，不重复执行、无导入环）；子命令
  集合、参数、JSON 输出与退出码（0/1/2）逐项不变——冒烟：`config` rc=0、
  不存在任务 `show` rc=2 + `{"error": …}` JSON。
- 方向守卫：`test_records_shared_body` 新增断言——CLI 层依赖查询组织，
  不直连下层职责 module；查询组织模块级定义不反向导入 CLI 层。
- >600 行例外登记同步更新（final-integrated-report §6.3/§9 第 1 项）：剩余为
  统一查询组织，基线指纹与依赖/开工判断共用同一次读取生命周期（spec 9/10）。

## ST-2 · 工单分流状态恢复标准值

- 26 张工单 `issues/*.md`：`**Status:** resolved` → `**Status:** ready-for-agent`
  （git 基点 a325eeb 的发布时值），新增 `**Progress:** 已完成（…）` 行另列
  完成进度；依据 docs/agents/issue-tracker.md（`Status:` 记录分流状态，
  `claimed/resolved` 仅用于 /wayfinder）与 docs/agents/triage-labels.md。
- `execution-log.md` 流程备忘（原第 10 行）就地修正，并新增「PR #28 双轴
  审查修复轮」一节说明背景；工单正文与各票历史执行记录保持原样。
- `evidence/final-integrated-report.md` 第 4/5 行（现势表述）同步更新。

## SP-1 · 各行为族原等待策略恢复（appserver_core）

- 事实：普通族（原 01-04/17/18）旧实现轮询 1 秒；中断族（原 05-16）旧实现
  是固定 0.3 秒的单一等待循环，与是否配置 `--watch-audit` 无关。共享化后
  未配置审计的中断族回落到 1 秒粒度 `wait_turn_completed`，最后时刻到达的
  回复与完成事件可能被漏收而仍返回 0（审查反例：179.2s/180s）。
- 修复：`appserver_core.py` 新增 `NORMAL_POLL_SECONDS = 1.0`（`__all__` 同步），
  `wait_turn_completed` 增加可选 `poll_seconds`（默认 1 秒，普通族行为不变）；
  `run_turn` 新增 `wait_poll_seconds` 显式参数；族 4/5 十二个入口
  （05–16）传 `INTERRUPT_POLL_SECONDS`。审计路径（绝对/相对中断）不变。
- 回归（先红后绿）：
  1. 接线探针 `test_family_wait_poll_seconds_wiring`：18 个入口经 spy 断言
     未配置审计时的等待粒度（中断族 [0.3]、普通族 [1.0]）。
  2. 虚拟时钟 A/B `test_late_arrival_before_deadline_parity`：同一「第 9.5 秒
     到达、10 秒超时」脚本，族 4/族 5 基点旧实现收到、共享实现（0.3 秒）
     收到（消息+事件）；普通族基点旧实现收不到、共享实现默认同样收不到
     （原行为保留，不扩大收集承诺）。
  3. 受控进程 `test_late_reply_controlled_process`：替身新增 `late-reply`
     模式（turn/start 应答后延迟 0.5 秒发回复+完成事件），族 4 代表入口
     （05）与普通族代表入口（01）以 5 秒超时普通完成，报告与事件证据齐全。
- `tests/acceptance_client_support.py`：SpyServer 记录 `wait_polls`（不改
  既有 `calls` 断言面）。

## SP-2 · 核心文档按解析后实际路径复用（_doc_texts）

- 修复：`mgs_records._doc_texts` 以 `Path.resolve()` 后的实际路径为复用键，
  同一物理文件经 `docs/DESIGN.md` 与 `docs/./DESIGN.md` 等合法映射写法只在
  本次调用实际读取一次；返回字典仍按原映射路径键控，输出定位不变。
- 回归（先红后绿）`test_records_baseline.test_baseline_docmap_alias_reuses_one_read`：
  别名映射 + 任务引用别名版本；包装 `Path.read_text` 在首次实际读取后把
  文件改为新版本。红：实际读取 2 次、两映射位置 declared_version 混合
  v2/v3、指纹不一致、出现幽灵受影响任务（与审查复现一致）；
  绿：读取 1 次、版本/指纹同源、无受影响任务。
- 跨调用不缓存语义不变（下一次顶层调用重新读取）。

## /code-review 复审与处置（2026-09-12，双轴并行子代理）

Spec 轴：ST-1/ST-2/SP-1/SP-2 全部 **resolved**，无范围越界（CLI 搬移体与
`f23f323` 逐字一致、旧新等待间隔对照基点提交核实、ST-2 仅动元数据两行）。

Standards 轴：1 项硬违规 + 8 项判断性意见，处置如下：

| # | 发现 | 处置 |
| --- | --- | --- |
| H1 | `_cli` 223 行 >80 的例外理由「参数分发」不满足 spec 30 完整事务措辞 | **已修**：§9 第 2 项改写为指明完整事务边界（解析→分发→输出投影→退出码合同不可拆分）并登记阶段一收口以来的先例 |
| J1 | §9 第 1 项「再拆会割裂不变量」表述过强（纯助手可移） | **已修**：§9 第 1 项收敛为「一次顶层读取的完整生命周期」边界，明说纯助手可移但不构成职责边界 |
| J2 | `test_acceptance_client_absolute.py` 510 行超 spec 31 的 500 行目标；报告「最大测试文件 432」过时 | **已修**：三组 SP-1 回归移入新主题 `tests/test_acceptance_client_wait_strategy.py`（223 行），absolute 回落 334 行，报告记录恢复真实 |
| J3 | SpyServer `poll_seconds=1.0` 魔法数 | 接受留档：测试替身默认值与普通族默认一致，与现有假时钟/假计时字面量同风格 |
| J4 | 12 入口重复 `wait_poll_seconds=INTERRUPT_POLL_SECONDS`（Shotgun Surgery） | 接受留档：spec 36 要求各族身份与选项分别保留，入口显式声明族策略是既定设计（与 `new_session` 同理） |
| J5 | `run_turn` 将 `None` 映射为 `NORMAL_POLL_SECONDS` 与等待方法默认重复 | 接受留档：映射让调用点粒度显式可见，等待方法默认保持普通族直调兼容 |
| J6 | shared_body 注释声称「任何 module 不得反向导入 CLI 层」但断言未落地 | **已修**：改为全量扫描 records 目录——仅 `mgs_records.py` 脚本守卫可导入 CLI 层，其余一律禁止 |
| J7 | 26 张票同文 `Progress:` 行不在 issue-tracker.md 约定内 | **已修**：docs/agents/issue-tracker.md Conventions 增补 Progress 行约定（完成另列、不改 Status 为非分流值） |
| J8 | mgs_records.py 本轮因两个原因被编辑（Divergent Change） | 接受留档：ST-1 与 SP-2 均为同一审查轮对该文件的指定修复，非模块职责混杂 |

## 验证结果（2026-09-12 实跑）

- 全量测试套件：`tests/test_*.py` 共 **46 个文件（5 个聚合器 + 41 个主题）全部通过**（R2-ST-1 修正口径：原记 35 为笔误）（含审查引用的
  五套聚合检查 test_plugin_package / test_records_backend / test_github_backend
  / test_runtime_gate / test_runtime_boundaries，及验收客户端四主题）。
  期间 dist 一致性两套件曾因源码变更先红，`./dist/build-package.sh` 重建
  后转绿——顺序为：改源码 → 全量测试 → 重建包 → 提交 → 隔离重建核验。
- 新交付包 SHA-256：`247fa99579e45c8565a9f7c55993282883a686c3f9f65a73dbeb1a17495cb5e3`（一轮修复时点；二轮 R2 后更新为 `70a1172…`，见下二轮节）
  （91 文件；manifest 与 SHA256SUMS 已随重建更新）。
- `dist/verify-reproducible.sh`（修复主提交 `7ff3d36` 入库后实跑）：**全部
  PASS**——交付包、逐文件清单与 SHA256SUMS 均与 `git archive HEAD` 干净副本
  隔离重建逐字节一致，tar 成员无 PAX 扩展头。
- 未执行（与全任务一致的限制）：真实模型轮、真实远端写入、安装与发布。

## 二轮独立审查修复（2026-09-12，R2）

二轮独立双轴审查（对 `ec13736`，PR 评论 5643458535）：上一轮四项反例全部关闭；
新增 1 条 P3 非阻塞备注（R2-ST-1）+ 1 条 P2（R2-SP-1），均按下述修复。

### R2-SP-1 · P2：CONFIG 自映射纳入同次复用（已修复）

- 事实：spec 9 明定每次顶层调用取得 CONFIG 原文一次；`_doc_texts` 的
  `by_location` 未纳入顶层已读原文，文档映射含 CONFIG 自映射行时 CONFIG 被
  实际读取两次，同次改版会以第二次原文判出假漂移（ready 误 blocked、
  baseline 误列受影响任务）。
- 修复：`_doc_texts` 增加可选 `config_text`，以解析后的 CONFIG 实际路径预置
  复用上下文；`startable_tasks` 经 `_Reading.config_text` 接线，
  `baseline_report` 改用 `load_config_document`（仍一次读取）并透传原文。
  公开参数/返回字段不变；下一次顶层调用重新读取的刷新语义不变。
- 回归（先红后绿）：共享夹具 `make_config_selfmap_project` +
  `counted_config_reads`（首读后真实改版 v1→v2）——
  `test_records_baseline.test_config_self_mapping_reuses_first_read` 与
  `test_records_deps_ready.test_config_self_mapping_ready_reuses_first_read`：
  红：CONFIG 读取 2 次、「当前 v2,任务引用 v1」假漂移；绿：读取 1 次、
  同次结论同源；下一次调用如实反映 v2。

### R2-ST-1 · P3：测试数量记录修正（已修复）

- `tests/test_*.py` 实际 **46 个文件 = 5 个聚合器 + 41 个主题**；本文件与
  执行日志中「35 个文件」为笔误（先按 34 计数、SP-1 回归拆分主题后未重计）。
  46 个文件均已实际运行且全部通过；独立审查已核对聚合器注册表并集并实跑
  五套聚合器。两处记录已更正。

## 代码身份（一轮修复）

- 生产区变更：`plugin/records/`（mgs_records.py、mgs_records_cli.py 新增）、
  `acceptance/_shared/appserver_core.py`（418 行）、`acceptance/05–16/`
  十二个入口（各 +2 行）、dist 三件套重建。
- 测试区变更：`test_records_baseline.py`（+SP-2 回归）、
  `test_acceptance_client_absolute.py`（+SP-1 三组回归与助手）、
  `acceptance_client_support.py`（SpyServer）、`fake_appserver.py`
  （late-reply 模式）、`test_records_shared_body.py`（方向断言）、
  `test_plugin_package.py`（主题注册）。
- 记录区变更：26 张工单、execution-log.md、final-integrated-report.md
  （§6.3/§9 现势更新 + 第 11 节修复轮增补）、docs/agents/issue-tracker.md
  （Progress 行约定增补）、本文件。

### 二轮 /code-review 内部复审与处置（2026-09-12）

Spec 轴：R2-SP-1 **resolved**（`_doc_texts` 两处调用点全部接线、双后端同源、
公开签名/返回字段不变、无跨调用缓存；回归含同次改版与下一次调用刷新）、
R2-ST-1 **resolved**（46 口径两处记录一致）。
Standards 轴：1 硬违规 + 5 判断性意见，处置：

| # | 发现 | 处置 |
| --- | --- | --- |
| H2 | 报告 §0.2/§4/§11 仍以「45 个文件」「678」作现势表述，与 R2 修正后的 46/691 自相矛盾 | **已修**：§0.2/§4/§11 补时点标注（45/45 为 `f23f323` 实跑记录），§11 增补改写为 897→678→691 链条 |
| J9 | 报告无 §9.1/§9.2 子节，引用格式悬空 | **已修**：引用统一为「§9 第 1/2 项」 |
| J10 | `_doc_baseline_versions` 的 config_text 为位置可选参数，与 `_doc_texts` 的 keyword-only 不一致，省略即静默恢复双读 | **已修**：改为 keyword-only，`startable_tasks` 调用点同步 |
| J11 | `_doc_texts`/`_doc_baseline_versions` 的 (root, config, config_text) 数据结伴、复用键 resolve 表达式重复 | 接受留档：结伴参数与 `_Reading` 既有结构一致；单行表达式重复提取反而加层 |
| J12 | `counted_config_reads` 在 read_text 包装内写文件（访问器副作用）、夹具链式 replace | 接受留档：写文件正是复现「首读后同次改版」的机制本体，与一轮别名回归同一手法 |
| J13 | github-issues 后端的 CONFIG 自映射未单测 | 接受留档：复用发生在 `_doc_texts`（本地文档读取），与 `_read_tasks` 的后端分发正交，双后端共用同一路径（独立复审已核对）；如需可后续补 github 夹具变体 |

### 二轮验证

- 全量测试：`tests/test_*.py` 共 **46 个文件（5 个聚合器 + 41 个主题）全部实跑通过**。
- 交付包重建 91 文件，SHA-256：`70a1172a28218bee32c1cbadfc660909403bc32a537b0807b73a6c52e2a136c1`
  （独立复审者对中间态的隔离重打包 7234bae 交叉印证了构建确定性；该次重打包后
  复用接缝签名按 J10 收紧，最终包为 70a1172）。
- `dist/verify-reproducible.sh`：修复提交入库后实跑，结果见执行日志 R2 节收口补记。

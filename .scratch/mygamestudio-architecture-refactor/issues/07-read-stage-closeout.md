# 07: 完成任务读取的入口与交付兼容验收

**What to build:** 重组后的任务读取可从原命令、公开导入和受控调用使用，第一阶段全部要求具备可复查结果。

**Blocked by:** 05 让列表与单任务读取复用配置并保持兼容；06 让基线与核验复用读取且保留证据含义

**Status:** ready-for-agent

**Progress:** 已完成（2026-09-12 收口；执行记录见 Comments 与执行日志）

**Spec:** [MyGameStudio 全插件分阶段架构重构 v1](../spec.md) · User Stories 1, 2, 4, 5, 6, 7, 8, 21, 22, 27, 51, 59, 60

**Verification mapping:** READ-01, READ-02, READ-03, READ-04, READ-05, READ-06, READ-07, READ-08, READ-09, READ-10, READ-11, READ-12, READ-13, READ-14

- [x] READ-01 至 READ-14 均有当前集成版本的覆盖与结果；时间和来源字段按语义比较，R1 旧新差异单独列明。
- [x] 验证固定脚本入口、公开函数、工厂参数和两种导入顺序；迁移和交接的映射与错误保持。
- [x] 运行受影响的后端、运行时、包与实际 CLI 检查；CONFIG 在途撤销、实例撤销和审计故障没有因读取复用回退。
- [x] 通过当前完整包的模块引用、来源指纹、清单与隔离可复现构建；不拿旧包证明新代码。
- [x] 报告生产净行数、文件长度与职责、CONFIG/任务读取次数和剩余限制；超限项按已确认标准说明，不以删除必要行为达标。
- [x] 保留匹配版本和回退说明；未执行的真实宿主或远端验收清楚标注，阶段技术结论不代替安装与发布。

**依赖理由：** 依赖 05、06 的兼容入口闭环；它们已传递包含 02、03、04，无重复列边。

## 执行与验证约定

本票已正式发布；实施按对应任务授权执行。沿现有 interface 验证本票行为；保持外部用法、持久化格式、权限与恢复语义，只有明确列出的 R1 属行为修正。每票在新的执行上下文中按实际前置成果接手；产品内容变化时同步相关包与来源检查，记录净行数、必要操作量和未验证限制。

同一共享文件只由一名执行者修改。测试和独立规范/规格评审针对本票实际版本；基线不可被历史结果替代。提交、推送、标签、真实远端写入、日常安装和发布分别沿明确授权执行。

## Comments

用户已确认 26 票拆分及其依赖安排；本票按确认稿发布，未启动实施。

### 执行记录(2026-09-12,阶段 1 收口)

**做了什么**:在当前集成版本(前基点 `ce6c81f`)上系统核对 READ-01～14 的覆盖与
结果,补齐两处集成级覆盖缺口,产出阶段收口报告 `evidence/stage1-closeout.md`。
生产区(plugin/)零改动,零用户可见行为变更。

- 逐条 READ 映射表(编号 → 覆盖测试 → 本次结果 → 结论)见收口报告第 1 节。
  READ-01～14 全部 PASS。
- **覆盖缺口补齐(仅测试,不改生产)**:
  1. `test_github_backend::test_label_priority_and_conflict_preserved`——原测试只断言
     `triage_source/triage_conflict` 字段存在,未验证标签覆盖正文、多标签优先级
     (取首个可识别语义)与实际冲突登记;补测后 READ-08 后端专有规则有取值级证据。
  2. `test_records_backend::test_public_interface_surface_and_factory_parameters`——
     直接固定公开函数(`list_tasks/read_task/task_dependencies/startable_tasks/
     baseline_report/verify_project/github_backend`)与工厂/transport 构造入口
     (`UrllibTransport`、`GithubBackend`、`plan_backend_switch`、`handover_baseline_check`)
     的参数名、顺序、默认值与关键字专有性,落实 AC2。
- **读取计数(audit-hook 实测)**:本地 ready CONFIG 6→**1**、每份 task.md 2→**1**;
  deps/list/show/verify 各 CONFIG 1;baseline CONFIG 1 且核心文档各 1;
  GitHub ready 全量集合 2→**1**。runtime 受控写入计数未变(policy 3 / instances 2)。
- **R1 旧新差异单独列明**:旧(票 01 冻结基线)本地 ready 混用两时点、结果落 blocked、
  GitHub 集合取 2 次;新结果只消费唯一集合、结果落 startable、GitHub 取 1 次,
  下一次调用重新读取并更新分类。
- **READ-12 无回退**:`mgs_runtime.py`/`mcp_gate.py`/`mgsrt_admin.py` 三文件相对票 01
  基线 SHA-256 逐字节未变;实例撤销在途、CONFIG 在途撤销、审计故障反例全部保持。
- **净行数**:plugin 4526→4793(+267,含两个新 module 的实现成本);
  tests 9086→10406(本票 +138);acceptance 20739 不变;dist 146 不变。
  超 600 行的 `mgs_github.py`/`mgs_runtime.py`/`mgs_records.py` 及超 80 行函数按
  spec 30 在收口报告 5.3 记录完整不变量理由与验证方式。
- **交付与回退**:dist 内容与当前生产一致(生产零变化,无需重建);
  `./dist/verify-reproducible.sh` PASS,包 SHA-256
  `af91503f2956587e9024730ac82ccc124b8173cc1eec669c09aa72eb59fd789d`;
  回退用前基点 `ce6c81f` 的代码与匹配包,阶段 1 不涉及数据迁移。

**验证命令与真实结果**:

- `python3 -B tests/test_plugin_package.py` → rc 0;`test_runtime_gate.py` → rc 0;
  `test_runtime_boundaries.py` → rc 0;`test_records_backend.py` → rc 0;
  `test_github_backend.py` → rc 0。
- `sh .scratch/.../evidence/baseline/run_baseline.sh` → 五套全 PASS,
  `all_existing_checks_green=True`(随后 `git checkout --` 恢复 results/ 与
  BASELINE-REPORT.md 冻结产物)。
- `./dist/verify-reproducible.sh` → 三项产物逐字节一致 + 无 PAX 扩展头,PASS。
- `entry_probe` 11 案例的顶层键集合与退出码与票 01 冻结基线逐项一致。

**未验证限制(如实标注)**:真实模型轮、真实远端写入、日常安装替换与发布均未执行
(GitHub 检查全部使用本地替身 transport,零网络/零凭据);真实网络耗时未测。
阶段技术结论不代替安装与发布,留待对应授权单独执行。

### 复审修复记录(第一轮)

独立复审对票 07 交付(固定点 `ce6c81f...085f02a`)提出三项发现,逐条处理如下。

**F1(映射漏引,已改)**:收口报告 READ-11 行原先只列 GitHub verify 与离线测试,
漏了支撑「本地结果核验」的 `test_records_backend::test_verify_reads_config_and_tasks_once_local`
(报告 5.4 表「本地 verify」行正依赖它)。已核实该测试真实存在
(`tests/test_records_backend.py:1379`),其断言与 READ-11 表述匹配:CONFIG 原文
恰 1 次、每份 task.md(7 份)各 1 次、11 项检查名称与顺序保持、健康项目 ok。
已在 READ-11 覆盖测试列补上该引用,并在结论列同步补偿本地 verify 计数口径。

**F2(冻结产物措辞,已改)**:报告第 1 节称「所有测试均为本次真实运行……非历史结果」,
第 3 节却把 `results/checks/*.txt` 列为「原始输出」,二者矛盾——这些产物是票 01
冻结、每次跑完 `run_baseline.sh` 后被 `git checkout --` 还原的历史证据
(`results/baseline.json` 的 `generated_at` 仍为 09-12T00:02)。已改第 3 节表头与
措辞:明确 `results/checks/*.txt` 与 `results/baseline.json` 是**票 01 冻结的历史
证据(非本次输出)**,末列只标示同一套检查的冻结归档位置;本次五套结果以票文件
Comments 的实跑记录与独立复核为准。冻结产物本身零改动。

**F3(测试重复,已改)**:`test_github_backend.py` 新增的局部 `_issue()` 与同文件
既有 `_seed_raw_issue` 几乎重复,且内联 8 键 request 字典为第 4 处副本。已将
`_seed_raw_issue` 扩展为可选构造面(`body` 可选、新增 `labels/identity/title/
triage/request` 关键字参数;`body` 缺省时用 `build_task_body` 生成),新测试的三处
种子改为复用 `_seed_raw_issue`,删除局部 `_issue()`。既有调用点
(`test_record_model_cross_backend_body_semantics` 的 `_seed_raw_issue(fake, SHARED_BODY)`)
保持兼容未改;行为断言未变,`test_github_backend.py` 仍绿。

**验证结果**:
- 五套 `python3 -B tests/test_*.py` 全 rc 0(plugin_package / runtime_gate /
  runtime_boundaries / records_backend / github_backend)。
- `sh .scratch/.../evidence/baseline/run_baseline.sh` 五套全 PASS、
  `all_existing_checks_green=True`;跑后已 `git checkout --` 恢复 `results/` 与
  `BASELINE-REPORT.md` 冻结产物。
- `git diff --numstat 085f02a -- plugin acceptance dist` 为空(生产区零改动);
  工作区相对 `085f02a` 仅改本票文件与 `tests/test_github_backend.py`。

### 复审修复记录(第二轮)

独立复审对票 07 提出两项发现,逐条处理如下(本轮纯文档修正,不改 `tests/` 或 `plugin/`)。

**F1(行数回填,已改)**:报告 5.1 与上文执行记录原写 tests
`9086→10400`(本票 +132),第一轮 F3 去重净 +6 行未回填。按 `code_volume.py`
同一物理行口径重算(`plugin/tests/acceptance/dist` 下 tracked 代码文件,含空行注释):
- tests 五文件实测:`test_github_backend.py` 2758、`test_plugin_package.py` 4049、
  `test_records_backend.py` 1560、`test_runtime_boundaries.py` 433、
  `test_runtime_gate.py` 1606,合计 **10406**(票 01 基线 9086)。
- 本票净变化:自前基点 `ce6c81f`(tests 10268)到 HEAD 为 **+138**
  (`test_records_backend` +75、`test_github_backend` +63,后者含 F3 复用
  `_seed_raw_issue`、删除局部 `_issue()` 的净变化)。
- 已同步修正报告 5.1 表(tests 行 `10400/+1314/+132` → `10406/+1320/+138`)、
  报告第 8 节两处新增测试行数(records +75、github +63 并注明 F3 净变化)、
  本工单执行记录「净行数」行。
- 表中其余行经复算仍准确,未改:plugin 4793(7 文件)、acceptance 20739(44 文件)、
  dist 146(2 文件)。

**F2(READ-11 子句补引,已改)**:READ-11 spec 原句为「必要的详情、评论、标签或
结果文件读取实际发生;失败和未核对表达保持」。报告 READ-11 行原只引用读取计数类
测试,未引直接覆盖「(本地)结果文件读取实际发生;失败表达保持」子句者。核实
`tests/test_records_backend.py::test_verify_results_consistency`(现第 389 行)测试体:
- 三处场景均让 verify 真实读取本地结果文件——① 结果文件存在但结果索引仍为
  「(暂无)」→ `results-consistent` 判失败;② 结果文件身份与所属任务不符 →
  同一检查判失败;③ 结果索引引用该文件后整体 `ok`。
- 该测试直接覆盖「结果文件读取实际发生」与「失败表达保持」;「未核对表达保持」
  由已在列的同文件 `test_verify_offline_keeps_unchecked_and_skipped` 覆盖。
- 已在报告 READ-11 覆盖测试列补引该测试,结论列同步说明其覆盖结果文件核验与
  失败表达。该项名称与内容相符,无需改引。

**已接受、留档不改的判断性 smell(两项)**:
1. 默认 8 键 request 字典(当前目标/输入与基线/本次交付/允许修改范围/所需能力/
   完成标准/执行责任/验收方式 + 依赖)在 `FakeTransport.seed_issue`
   (`tests/test_github_backend.py:209`)与 `_seed_raw_issue`(`:2289`)各存一份。
   二者分属不同调用形态(身份/标题构造 vs 原始正文/标签构造),合并需引入新的
   共享层;属测试辅助字面量重复,无生产影响,本轮不改。
2. `_seed_raw_issue` 参数增至 10 个(为 F3 复用而扩的 `body/labels/identity/
   title/triage/progress/request` 可选构造面)。该函数是测试辅助,仅被本文件测试
   调用,无生产代码引用,不影响公开接缝与生产行为,本轮不改。

**验证结果**:
- 五套 `python3 -B tests/test_*.py` 全 rc 0(plugin_package / runtime_gate /
  runtime_boundaries / records_backend / github_backend)。
- 本轮改动仅 `.scratch/.../evidence/stage1-closeout.md` 与本工单文件;
  `plugin/`、`tests/`、`acceptance/`、`dist/` 零改动。

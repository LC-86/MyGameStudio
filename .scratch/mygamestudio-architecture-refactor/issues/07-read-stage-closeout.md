# 07: 完成任务读取的入口与交付兼容验收

**What to build:** 重组后的任务读取可从原命令、公开导入和受控调用使用，第一阶段全部要求具备可复查结果。

**Blocked by:** 05 让列表与单任务读取复用配置并保持兼容；06 让基线与核验复用读取且保留证据含义

**Status:** resolved

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
  tests 9086→10400(本票 +132);acceptance 20739 不变;dist 146 不变。
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

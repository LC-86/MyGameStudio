# 02: 让双后端共用正文与错误语义

**What to build:** 相同任务正文经本地和 GitHub 入口读取，继续得到兼容结果与一致核心核验；两种调用方式使用同一错误身份。

**Blocked by:** 01 固定可复跑的兼容与效率基线

**Status:** ready-for-agent

**Progress:** 已完成（2026-09-12 收口；执行记录见 Comments 与执行日志）

**Spec:** [MyGameStudio 全插件分阶段架构重构 v1](../spec.md) · User Stories 1, 2, 21, 22, 23, 24, 25

**Verification mapping:** READ-08, READ-09, READ-10

- [x] 从既有公开读取和核验入口贯通共同正文规则；空字段、未知小节、字段分隔及畸形任务的可见性保持。
- [x] 本地目录与结果文件、GitHub 标签覆盖与分流冲突等专有字段留在对应 adapter；不以统一为由删减返回内容。
- [x] 共同记录语义不依赖查询或命令行；现有公开导入和继承关系保持，内部重导出不变成无意义转发链。
- [x] 验证 records 先导入、GitHub 先导入和直接脚本调用的错误捕获；已有命令行参数、JSON 和退出码兼容。
- [x] 保留未在本票迁移的读取与恢复路径，受影响后端、运行时和包检查通过；本票不提前宣称整个循环依赖已消除。

**依赖理由：** 依赖 01 的同输入兼容基线和异常/正文案例。

## 执行与验证约定

本票已正式发布；实施按对应任务授权执行。沿现有 interface 验证本票行为；保持外部用法、持久化格式、权限与恢复语义，只有明确列出的 R1 属行为修正。每票在新的执行上下文中按实际前置成果接手；产品内容变化时同步相关包与来源检查，记录净行数、必要操作量和未验证限制。

同一共享文件只由一名执行者修改。测试和独立规范/规格评审针对本票实际版本；基线不可被历史结果替代。提交、推送、标签、真实远端写入、日常安装和发布分别沿明确授权执行。

## Comments

用户已确认 26 票拆分及其依赖安排；本票按确认稿发布，未启动实施。

### 执行记录（2026-09-12）

**做了什么。** 新增中性记录 module `plugin/records/mgs_record_model.py`（252 行），集中
共同错误身份 `RecordsError`、任务正文共同规则（头部/小节/字段分隔/空值/未知内容）与
纯记录核验（标签映射、核心文档映射、任务核心字段、依赖关系）。`mgs_records.py` 按现有
公开名字直接重新导出这些名字（非空转发，定义只有一处），本地 adapter 的 `_parse_task_file`
改为调用 `parse_task_body` 并只补齐目录/结果文件/相对路径；`mgs_github.py` 的
`parse_issue_body` 改为调用同一 `parse_task_body`，只补齐 Issue 号/标签/triage 来源与
冲突/关闭状态/原始正文。GitHub 记录错误 `GithubRecordsError` 仍继承同一 `RecordsError`。
据此移除 `mgs_records.py` 为脚本异常身份做的 `sys.modules["mgs_records"]` 临时补偿：
脚本与模块导入下异常身份均由 model 的唯一定义保证。

**净行数（物理行，含空行注释；同范围 git diff 复算）。**
生产 `plugin/`：`mgs_record_model.py` +252、`mgs_records.py` 1109→937（-172）、
`mgs_github.py` 1848→1843（-5），合计 **+75**。测试 `tests/`：`test_records_backend.py`
787→857（+70）、`test_github_backend.py` 2236→2386（+150），合计 **+220**。
验收 `acceptance/`：**0**。交付 `dist/`：`package-manifest.txt` 79→80（+1，新增模块入包）、
`SHA256SUMS.txt` 值更新（2 行不变）、`mygamestudio-0.18.0.tar.gz` 重建。

**验收条件逐条自查与证据。**
1. 共同正文贯通：`test_records_backend.test_record_model_shared_body_and_error_identity`、
   `test_github_backend.test_record_model_cross_backend_body_semantics` 断言同一正文经
   本地/GitHub 读取的共通字段（identity/title/triage/progress/request/sections/
   result_index_text）逐键一致；空值字段、未知小节、全角冒号与分号分隔、空身份畸形任务
   在两端均可见并进入 `verify` 的 `tasks-valid` 报告。
2. 专有字段留 adapter：同测试断言本地含 directory/path/results 且不含 issue_number，
   GitHub 含 issue_number/state/labels/triage_source/triage_conflict/body 且不含
   directory/path；标签覆盖与 triage_conflict 逻辑未改动。
3. 无反向依赖：同测试读取 `mgs_record_model` 源码，断言不含 `import mgs_records`/
   `import mgs_github`；公开导入 `load_config/list_tasks/read_task/...` 与
   `RecordsError` 定位不变（`test_plugin_package.test_records_backend_module` 通过）。
4. 错误捕获与兼容：`test_github_backend.test_error_identity_across_import_orders_and_script`
   以子进程分别验证 records 先导入、GitHub 先导入时 `RecordsError` 同一身份；
   直接脚本调用 `create` 未授权路径输出 JSON 错误、退出码 2、无未捕获 traceback。
   `test_records_backend.test_cli*` / `test_github_backend.test_cli_*` 覆盖既有命令参数、
   JSON 与退出码（记录/文件错误 2、判定失败 1、成功 0）全部通过。
5. 未迁移路径保留：完整五套检查实跑全绿；本票零行为变更，未改 ready 单次读取闭环
   （属票 04）、未拆 `mgs_records` 查询/CLI（属票 03/04）——本票不宣称整个循环依赖已消除，
   仅消除共同记录语义一处反向依赖（正文/核验/错误类型）。

**验证命令与真实结果。**
- `python3 -B tests/test_plugin_package.py` → OK（退出 0）；`test_runtime_gate` → OK；
  `test_runtime_boundaries` → OK；`test_records_backend` → OK；`test_github_backend` → OK。
- `sh .scratch/mygamestudio-architecture-refactor/evidence/baseline/run_baseline.sh` →
  五套检查 PASS、`all_existing_checks_green=True`；随后按约定恢复 `results/` 与
  `BASELINE-REPORT.md`（票 01 产物保持原样）。
- 复跑 records_probe 稳定字段与基线一致：CONFIG.md 6、task.md 2、GitHub 集合获取 2、
  客户端解码 21000（本票不改变读取次数）。
- `./dist/build-package.sh` 重建，包内文件集合与 `plugin/` 一致（含新模块）。

**未验证限制。** 未执行真实模型轮与真实远端写入（本票范围内不需要，且无授权）；
`dist/verify-reproducible.sh` 依赖 `git archive HEAD`，须在提交后运行，本次未跑（改动
已提交后可由后续核验复跑）；运行时检查只覆盖仓库既有五套离线检查，未新增宿主验证。

**范围与非目标。** 本票是语义共享票：读取计数（CONFIG 6/任务集合 2）、ready 单次读取
闭环、list/show/deps/baseline/verify 的入口接入均未改动，分别属票 03/04/05/06。

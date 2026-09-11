# 03: 统一配置与本地来源并解除反向依赖

**What to build:** 现有读取、迁移计划和交接入口从统一来源取得配置与本地任务，结果保持，后端不再反向调用查询入口。

**Blocked by:** 02 让双后端共用正文与错误语义

**Status:** resolved

**Spec:** [MyGameStudio 全插件分阶段架构重构 v1](../spec.md) · User Stories 2, 10, 13, 15, 16, 21, 22, 27, 51

**Verification mapping:** READ-07, READ-09, READ-10, READ-12, READ-13

- [x] 共同配置解析从同一 CONFIG 原文产生字段与执行条件，接受已加载配置的本地读取能通过现有入口使用。
- [x] 本地 list 仍按目录顺序、show 仍按目录定位且不扫描无关任务；缺失和不支持后端的错误保持。
- [x] GitHub 迁移和交接中的配置、核心文档分类及本地任务读取改用实际职责所属 module，操作顺序、映射和权限要求不变。
- [x] 静态依赖与两种导入顺序证明共同语义/来源不反向依赖查询、GitHub 不反向调用查询；不以新的延迟导入掩盖循环。
- [x] 已加载配置只供同次读取使用；受控写入仍在最终锁内重读 CONFIG 和实例状态，不用旧读取结果授权。
- [x] 相关本地/GitHub、迁移、交接、脚本与运行时兼容检查通过；本票保留所有旧调用可用，为下一票单次集合提供已接入的来源。

**依赖理由：** 依赖 02 的中性正文与错误类型，才能迁移来源和反向引用而不恢复循环。

## 执行与验证约定

本票已正式发布；实施按对应任务授权执行。沿现有 interface 验证本票行为；保持外部用法、持久化格式、权限与恢复语义，只有明确列出的 R1 属行为修正。每票在新的执行上下文中按实际前置成果接手；产品内容变化时同步相关包与来源检查，记录净行数、必要操作量和未验证限制。

同一共享文件只由一名执行者修改。测试和独立规范/规格评审针对本票实际版本；基线不可被历史结果替代。提交、推送、标签、真实远端写入、日常安装和发布分别沿明确授权执行。

## Comments

用户已确认 26 票拆分及其依赖安排；本票按确认稿发布，未启动实施。

### 执行记录（票 03）

**做了什么**

- 新增 `plugin/records/mgs_record_source.py`（266 行）：协作配置与本地任务来源的
  唯一定义。承担 CONFIG 原文解析（后端/任务位置/标签映射/文档映射）、仓库坐标
  与远端授权声明的文本解析（`parse_repo_location` / `parse_remote_authorizations`），
  以及本地 adapter（`local_list_tasks` / `local_read_task`，接收本次已加载配置）。
  新增 `load_config_document` 返回 (config, text)，供同一 CONFIG 原文派生执行条件。
- `mgs_records.py`：删除重复的 CONFIG 表格解析、`load_config` 主体、本地列举/读取
  与 `_parse_task_file`，改为从 `mgs_record_source` 取配置与本地来源（`load_config`
  按现有公开名字重导出）；`list_tasks`/`read_task` 本地分支委托来源 adapter。
- `mgs_github.py`：删除模块内重复的坐标/授权解析，改为直接依赖 `mgs_record_source`；
  迁移/交接（`plan_backend_switch`、`apply_backend_switch`、`handover_baseline_check`）
  的配置读取与本地任务列举改用来源 module；`parse_repo_location` 公开接缝保留并
  维持 `GithubRecordsError` 身份。用 AST 证明 `mgs_github` 不再导入 `mgs_records`。
- 测试：`tests/test_records_backend.py` 新增静态依赖方向（AST，含函数内导入）、
  两种导入顺序、已加载配置来源一致性（审计钩子证明不再读 CONFIG）；
  `tests/test_plugin_package.py` 的记录/ GitHub 模块接缝检查改为导入+调用验证
  （不再正则截取源码）。
- 重建 `dist/` 交付包（新增模块入包）并通过可复现验证。

**验证命令与真实结果**

- 五套检查（`run_baseline.sh` 同一命令）：`test_plugin_package` / `test_runtime_gate` /
  `test_runtime_boundaries` / `test_records_backend` / `test_github_backend` 全部 exit 0，
  `all_existing_checks_green=True`。
- `sh .scratch/mygamestudio-architecture-refactor/evidence/baseline/run_baseline.sh`
  全绿；跑完 `git checkout --` 恢复 `results/` 与 `BASELINE-REPORT.md`，票 01 产物未变。
- `records_probe` 稳定字段与基线逐项一致：本地 ready CONFIG 6 / task.md 2、
  GitHub 任务集合 2 次请求、投影 JSON 解码 21000；本票未改变 ready 读取计数
  （单次化属票 04）。
- 依赖方向：AST 扫描证明 model 不含 `mgs_records`/`mgs_github`/`mgs_record_source`，
  source 不含 `mgs_records`/`mgs_github`，github 不含 `mgs_records`；两种导入顺序
  下 `mgs_records.load_config is mgs_record_source.load_config`、错误身份单一。
- `./dist/build-package.sh` 重建后 `test_plugin_package` 通过；提交前以工作区副本
  隔离重建并与 `dist/` 逐字节比对三项产物一致；提交后 `./dist/verify-reproducible.sh`
  经 `git archive HEAD` 干净副本重建，结果见下条提交说明。

**净行数（物理行，含空行与注释）**

- 生产：`mgs_record_model.py` 252→252（0）、`mgs_records.py` 936→807（-129）、
  `mgs_github.py` 1843→1809（-34）、新增 `mgs_record_source.py` 266；
  生产合计 4600→4703（净 +103，为新增共享来源 module 成本；runtime 三文件不变）。
- 测试：`test_records_backend.py` 857→975（+118）、`test_plugin_package.py`
  4024→4049（+25）。
- 交付包：`package-manifest.txt` 80→81 文件，tarball 随内容重建。

**未验证限制**

- 未执行真实模型轮、真实远端写入或日常安装替换；GitHub 相关检查全部经本地替身
  transport（零网络），不代表真实网络耗时或全部宿主行为。
- `--config` 仍按各自入口读取；同一次 ready 的 CONFIG 单次化与任务集合单次化
  属票 04，本票只接入来源、不改读取计数（R1 仍为待修正状态）。
- 真实入口的子命令覆盖沿用票 01 `entry_probe` 范围（local-markdown 读取入口）。

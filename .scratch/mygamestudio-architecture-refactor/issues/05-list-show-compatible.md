# 05: 让列表与单任务读取复用配置并保持兼容

**What to build:** 用户继续以原命令读取列表或单任务，查询内配置只读取一次，排序、离线信息和必要详情保持。

**Blocked by:** 03 统一配置与本地来源并解除反向依赖

**Status:** resolved

**Spec:** [MyGameStudio 全插件分阶段架构重构 v1](../spec.md) · User Stories 13, 14, 15, 16, 17, 18, 19, 20, 21

**Verification mapping:** READ-05, READ-06, READ-07, READ-09, READ-11

- [x] 现有 list/show 公开函数与命令行均通过同次配置进入后端，不要求调用方传入新的内部对象。
- [x] CLI list 仍是原字段投影的 JSON 数组，Python list 仍返回任务列表；本地目录排序和 GitHub identity 排序分别保持。
- [x] 本地 show 按指定目录定位且不读取无关任务；目录与正文 identity 不一致仍能找到原记录。
- [x] GitHub show 保留列表定位、最新 Issue 详情和评论回读，不为减少请求删掉必要读取。
- [x] 各入口既有缓存字段、来源说明、错误类型和退出码保持；离线标记与排序不污染其他调用结果。
- [x] 通过实际命令行消费者和模块调用验证正常、缺失、畸形和离线场景。

**依赖理由：** 依赖 03 的同次配置来源；不依赖 04 的 ready 行为修正。

## 执行与验证约定

本票已正式发布；实施按对应任务授权执行。沿现有 interface 验证本票行为；保持外部用法、持久化格式、权限与恢复语义，只有明确列出的 R1 属行为修正。每票在新的执行上下文中按实际前置成果接手；产品内容变化时同步相关包与来源检查，记录净行数、必要操作量和未验证限制。

同一共享文件只由一名执行者修改。测试和独立规范/规格评审针对本票实际版本；基线不可被历史结果替代。提交、推送、标签、真实远端写入、日常安装和发布分别沿明确授权执行。

## Comments

用户已确认 26 票拆分及其依赖安排；本票按确认稿发布，未启动实施。

### 执行记录（2026-09-12，list/show 同次配置复用落地）

**做了什么**

- `plugin/records/mgs_records.py`：`list_tasks` / `read_task` 的 GitHub 分支不再调用公开 `github_backend(root, config_rel)`（该入口会按相对路径二次读取 CONFIG），改为直接调用已有的 `_github_backend_for(config, ...)`，由本次已解析配置构造 adapter。一次 list/show 调用因此只读一次 CONFIG 原文，调用方参数与返回结构不变。
- `list_tasks` 的离线标记与排序改为独立投影：`sorted(payload["tasks"], key=identity)` 上 `dict(task, cached_read=True)` 浅拷贝，不再原地给后端返回的任务集合打 `cached_read`，也不原地排序来源集合。
- 删除私有且全仓无引用的 `_local_config`（5 行函数；依赖方向与错误语义已由 `mgs_record_source` / 各公开入口承担；确认 `grep -rn` 零引用后删除，属本票 list/show 收口的死代码清理，无行为变更）。
- 未改动 `mgs_github.py`（1809）、`mgs_record_model.py`（252）、`mgs_record_source.py`（266）；不新增公共参数或返回字段。

**净行数（物理行，含空行注释）**

- 生产：`mgs_records.py` 860 → **851（-9）**；`mgs_record_model.py` 252、`mgs_record_source.py` 266、`mgs_github.py` 1809 均 0 改动；四份记录生产文件合计 3187 → **3178（-9）**。（工单前置说明写的「合计 4703」与所列四个文件行数之和 3187 不一致；此处按实际文件行数报告。）
- 测试：`test_records_backend.py` 1176 → **1310（+134）**、`test_github_backend.py` 2526 → **2665（+139）**，合计 **+273**。
- `dist/`：随生产内容重建（tarball / package-manifest.txt / SHA256SUMS.txt），沿用 `dist/build-package.sh`。

**新增测试（TDD 先行，已验证可失败）**

- `tests/test_records_backend.py`：`test_list_and_show_read_config_once_and_preserve_order`（list/show 各只读 CONFIG 一次、list 按目录排序、每份 task.md 一次、独立重跑计数稳定）、`test_show_locates_by_directory_without_scanning_unrelated`（目录名与正文身份相反仍按目录定位、只读所点任务、缺失任务报 `RecordsError` 且不读任何任务）、`test_cli_list_show_projection_and_exit_codes`（CLI list 原字段投影 JSON 数组、show 单任务结构与 Python 一致、缺失/配置缺失退出码 2）。
- `tests/test_github_backend.py`：`_ConfigReadCounter` + `test_github_list_show_read_config_once_and_necessary_reads`（list/show 各一次 CONFIG；show 集合定位 + Issue 详情 + 评论三处读取实际发生并回读结果）、`test_github_offline_list_show_metadata_and_no_marker_leak`（离线 list/show 保留缓存标识与说明；离线标记不污染来源集合与 ready 结果；无缓存离线失败不回退本地）。
- 可失败性对照：对 `plugin/records/mgs_records.py` 做 `git stash` 后复跑，GitHub 侧两项断言真实失败（「github list 应只读一次 CONFIG,实际 2 次」「github show…实际 2 次」），恢复改动后全绿——证明新测试确实锁定本票改动。

**验证命令与真实结果**

- 五套检查实跑：`test_plugin_package` rc=0、`test_runtime_gate` rc=0、`test_runtime_boundaries` rc=0、`test_records_backend` rc=0、`test_github_backend` rc=0，均 `OK`。
- `sh .scratch/.../evidence/baseline/run_baseline.sh`：五套全绿（`all_existing_checks_green=True`）；已 `git checkout -- .scratch/.../evidence/baseline/` 恢复冻结的 results/ 与 BASELINE-REPORT，冻结产物不变。
- `records_probe` 稳定读数与票 04 后一致：本地 ready `CONFIG.md` 1 次、每份 `task.md` 1 次；本地 R1 `task_list_reads=0`、`result_side=startable`；GitHub R1 全量集合请求 1 次、`result_side=startable`。本票未改变 ready 路径，符合预期。
- `entry_probe` 对 /tmp 隔离项目只读复跑并与票 01 冻结基线逐案比对：11 个案例的 JSON 顶层结构与退出码**全部一致**（成功 0 / `show` 缺失 2 / `config` 缺失 2 / `deps` 判定失败 1）；输出写到 /tmp，未改冻结产物。
- GitHub 侧配置读取计数直接实测（替换 `mgs_records.load_config` 计数）：改动前 list=2、show=2；改动后 list=1、show=1；show 的必要读取（`GET …/issues`、`GET …/issues/N`、`GET …/issues/N/comments`）全部发生。
- `./dist/verify-reproducible.sh`：提交后实跑 PASS（tar.gz / package-manifest.txt / SHA256SUMS.txt 与干净 HEAD 副本隔离重建逐字节一致，且无 PAX 扩展头）。

**六条验收逐条自查**

1. AC1：list/show 的公开函数与 CLI 均只读一次 CONFIG（本地 audit-hook 计 1；GitHub 替身计数 1），内部通过 `_github_backend_for(config)` 用同次配置进入后端，未要求调用方传新对象、未改公共参数。
2. AC2：CLI list 仍是 `{identity,title,triage,progress}`（离线另加 `cached_read`）的 JSON 数组；Python `list_tasks` 仍返回任务列表；本地 list 按目录排序、GitHub list 按 identity 排序，ready/deps 来源顺序不因 list 排序改变。
3. AC3：本地 show 用 `task_root/<目录>` 直接定位（`local_read_task`），审计钩子证明确实只打开所点任务；目录 `07-mismatch` 与正文身份 `01-mismatch` 相反仍能读回原记录；缺失任务只报错、不扫描。
4. AC4：GitHub show 仍先取全量列表定位，再读具体 Issue 详情与 comments；未为减少请求删掉任何必要读取（三处 GET 均在测试中断言）。
5. AC5：离线 list 逐任务 `cached_read`、离线 show `cached_read`+`cached_note`+`body_sha256`、ready 的 `cached/fetched_at/source/cache_note` 均保持；`RecordsError` 身份未变；CLI 退出码 0/1/2 合同保持；离线标记改为独立投影，不再污染来源集合与 ready 结果。
6. AC6：正常/缺失/畸形/离线场景均由模块调用与真实 CLI 消费者（`run_cli` 子进程）验证；畸形任务仍进入 `list`/`show`/`verify`（未被提前过滤）。

**未验证限制**

- 真实模型轮与真实远端写入按授权范围未执行（全任务一贯限制）；GitHub 侧全部用本地替身 transport，零网络、零真实远端请求。
- `entry_probe` 只覆盖 local-markdown 后端读取入口与两处错误路径；GitHub 专属子命令与需凭据入口未跑（沿用票 01 基线口径）。
- 本票未改变 ready/deps/baseline/verify 路径，故未对其新增读取计数断言；`records_probe` 报告文案仍描述修复前缺陷现象（冻结观察性产物，未改）。

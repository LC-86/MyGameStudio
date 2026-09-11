# 06: 让基线与核验复用读取且保留证据含义

**What to build:** 制作统筹能继续核对基线与记录一致性，同次判断复用已取内容，必要的结果和远端核验照常执行。

**Blocked by:** 04 修正可开工查询的重复读取与混合结果

**Status:** resolved

**Spec:** [MyGameStudio 全插件分阶段架构重构 v1](../spec.md) · User Stories 3, 11, 21, 25, 26

**Verification mapping:** READ-04, READ-08, READ-09, READ-11

- [x] baseline/verify 同次复用配置与需要的任务集合，依赖检查使用既有共享判断，不再隐式重取集合。
- [x] 同一已读核心文档用于本次版本与指纹判断；下次调用重新读取，不改变双指纹、格式修正、实质变化和旧完成事实的语义。
- [x] 核验保留检查名称、顺序和返回含义；畸形记录、缺身份、未知小节和配置缺失仍可被发现。
- [x] 本地结果文件及 GitHub 标签、评论仍实际核验；离线或不可用的检查保留未核对及 skipped 表达。
- [x] 实际 CLI 与模块调用验证成功、判定失败和捕获错误的原退出码与字段。

**依赖理由：** 依赖 04 已验证的同次任务集合与共享依赖判断。

## 执行与验证约定

本票已正式发布；实施按对应任务授权执行。沿现有 interface 验证本票行为；保持外部用法、持久化格式、权限与恢复语义，只有明确列出的 R1 属行为修正。每票在新的执行上下文中按实际前置成果接手；产品内容变化时同步相关包与来源检查，记录净行数、必要操作量和未验证限制。

同一共享文件只由一名执行者修改。测试和独立规范/规格评审针对本票实际版本；基线不可被历史结果替代。提交、推送、标签、真实远端写入、日常安装和发布分别沿明确授权执行。

## Comments

用户已确认 26 票拆分及其依赖安排；本票按确认稿发布，未启动实施。

### 执行记录（2026-09-12）

**做了什么（零用户可见行为变更，无行为修正）**

- `plugin/records/mgs_records.py`：从 `_read_workspace` 抽出 `_read_tasks(root, config, ...)`——由**本次已加载配置**获取任务集合一次（本地目录顺序 / GitHub 原后端顺序，附读取元信息），`_read_workspace` 复用它。`baseline_report` 改为：`load_config` 一次；新增 `_doc_texts` 一次读取各核心文档原文、`_versions_from_texts` 由同一原文推导逻辑版本，指纹也从同一原文计算，`baseline` 用 `_read_tasks` 取本次任务集合（不再另起 `_read_workspace` 重读配置）；受影响任务逻辑与 note 不变。`verify_project` 改为：`load_config` 一次后，github 分支用 `_github_backend_for(config, ...)` 直接构造后端（不再经 `github_backend` 二次读配置），本地分支用 `_read_tasks` 取任务集合（不再回调 `list_tasks` 重读配置）。依赖仍走共享 `dependency_problems`。
- `tests/test_records_backend.py`：新增 4 个测试（audit-hook 真实读取计数 + 结构/语义）：baseline 同次 CONFIG 一次、每份核心文档一次且版本与指纹同源、下次调用刷新；本地 verify CONFIG 一次、每份 task.md 一次、检查名称顺序保持；畸形/未知分流仍可发现且定位到目录；github verify 任务集合一次、标签与评论读取仍实际发生。
- `tests/test_github_backend.py`：新增离线 verify 保留 `offline`/`skipped` 与「未核对(离线缓存,不下结论)」表达、缓存结构与依赖检查照常的测试。
- dist 交付包同步重建（`./dist/build-package.sh`）。

**验证命令与真实结果**

- 五套检查：`python3 -B tests/{test_plugin_package,test_runtime_gate,test_runtime_boundaries,test_records_backend,test_github_backend}.py` 全部 rc=0。
- `sh .scratch/mygamestudio-architecture-refactor/evidence/baseline/run_baseline.sh` rc=0，五套 PASS，`all_existing_checks_green=True`；跑完已 `git checkout --` 恢复 results/ 与 BASELINE-REPORT.md。
- 读取计数（audit hook，改动前→改动后）：`baseline_report` CONFIG **2→1**、PROJECT/GAME_DESIGN/TECH_DESIGN 各 **2→1**（版本与指纹同一原文）、task.md 1→1；`verify_project` CONFIG **2→1**、task.md 1→1；github verify CONFIG **2→1**，任务集合 1、标签 1、评论 1。
- records_probe（/tmp 合成）稳定读数保持票 04 后状态：ready 本地 CONFIG 1 / task.md 1；R1 场景本地 `task_list_reads=0`、GitHub 集合请求 1；runtime 计数不变。
- entry_probe 对 /tmp 隔离项目只读复跑，与票 01 冻结 `results/entry_probe.json` 比对：11 案例退出码集合、JSON 结构（shape）、声明子命令**全部一致**。
- `./dist/verify-reproducible.sh` PASS（交付包三产物与干净副本隔离重建逐字节一致）。

**净行数（相同范围物理行）**

- 生产：`mgs_records.py` 851→897（+46）；其余生产文件 0 改动。生产净 +46 行。
- 测试：`test_records_backend.py` 1310→1485（+175），`test_github_backend.py` 2665→2695（+30）。测试净 +205 行。
- dist：0 文件增删，manifest 81 文件不变（指纹随 mgs_records.py 更新）。

**未验证限制**

- 真实模型轮与真实远端写入按授权范围未执行（本票零网络：GitHub 用注入替身）；本次不改变授权、持久化与恢复语义。
- `_doc_baseline_versions` 作为公开测试接缝保留（现在内部即 `_versions_from_texts(_doc_texts(...))`），行为与旧实现等价；仅 `baseline_report` 走单次读取路径。
- 检查名称、顺序、JSON 字段与退出码保持；entry_probe 覆盖口径沿用票 01（local-markdown 入口）。

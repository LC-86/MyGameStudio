# 18: 让结果追加通过完整发布恢复职责执行

**What to build:** 专业角色沿现有结果追加入口发布、回读和补索引，完整生命周期由一个 module 承担，现有恢复路径继续可用。

**Blocked by:** 09 让直连失败判据通过同一事件入口验证；11 按用户行为组织任务后端回归

**Status:** ready-for-agent

**Progress:** 已完成（2026-09-12 收口；执行记录见 Comments 与执行日志）

**Spec:** [MyGameStudio 全插件分阶段架构重构 v1](../spec.md) · User Stories 4, 5, 7, 42, 43, 44, 45, 46, 47, 48

**Verification mapping:** 按本票所属阶段的验收集合

- [x] 将完整结果追加职责接入现有 interface，包括发布前回读、评论发布、索引更新和已有恢复分支；不是只建立一个尚未使用的 module。
- [x] 未发布、结果未知、已发布待补索引和完成继续分别表达，返回身份、attempts 和恢复说明保留。
- [x] 超时先回读并收养已存在成果；已确认评论不因结构迁移重复发布。
- [x] 搬移期间完整保留碰撞、损坏登记和旧布局路径；所有既有生命周期检查通过，不把异常分支推迟到下一票补回。
- [x] 真实/替身 transport 仍走既有 seam，常规验证不产生真实远端写入；报告本次职责与代码净变化。

**依赖理由：** 依赖 11 按行为可运行的后端生命周期检查，以及 09 的稳定判据；11 已包含读取阶段验收。

## 执行与验证约定

本票已正式发布；实施按对应任务授权执行。沿现有 interface 验证本票行为；保持外部用法、持久化格式、权限与恢复语义，只有明确列出的 R1 属行为修正。每票在新的执行上下文中按实际前置成果接手；产品内容变化时同步相关包与来源检查，记录净行数、必要操作量和未验证限制。

同一共享文件只由一名执行者修改。测试和独立规范/规格评审针对本票实际版本；基线不可被历史结果替代。提交、推送、标签、真实远端写入、日常安装和发布分别沿明确授权执行。

## Comments

用户已确认 26 票拆分及其依赖安排；本票按确认稿发布，未启动实施。

### 执行记录（2026-09-12，阶段 4 首票／核心票，实施完成待复审）

**新 module 职责清单（生产区）：**

- 新增 `plugin/records/mgs_result_publication.py`（568 行）：工作结果发布的完整生命周期。
  - **发布生命周期** `ResultPublication`（公开接缝）：发布前回读收养 → 评论发布（超时先回读、区分「确认不存在」才重试一次）→ 结果索引更新 → 完成回读；分别表达未发布草稿、结果未知（uncertain）、部分成功（partial，携带已发布评论身份与索引未完成）、完成四种事实，`attempts` 与恢复说明 note 保留。远端动作只经 `_list_comments`/`_create_comment`/`_patch_body`（路径在此拼 `repo_path`），传输故障经 `TransportError` kind 区分，不建立通用自动重试框架。
  - **待补索引登记存储与归属**（文件语义，零远端调用）：`pending_identity`/`pending_identity_digest`/`pending_index_file`/`legacy_pending_index_file`/`record_pending_index`/`load_pending_index`/`clear_pending_index`/`pending_recovery_result`。完整请求身份核验、8 hex 短摘要目录 + 全长哈希文件名共存、损坏（非法 JSON／身份不完整／回执不完整）披露、旧平铺布局只读兼容与读入迁移、逐路径独立清除归属，全部按 review3-01~review6-01 既有契约逐条保留。
- 新增 `plugin/records/mgs_github_transport.py`（149 行）：GitHub 远端传输接缝与错误身份。`GithubRecordsError`/`TransportError` 唯一定义、`UrllibTransport`、端点/令牌解析、`repo_path`/`repo_str`。发布恢复 module 与 adapter 共用此层，互不反向依赖。
- `plugin/records/mgs_record_model.py` 252→321（+69）：把共同正文规则的**写面** `_today`/`_section_lines`/`_edit_body` 从 adapter 移入（与既有 `parse_task_body` 读面同处），adapter 在其公开接缝复用，消除正文序列化的重复实现。
- `plugin/records/mgs_github.py` 1809→1220（−589）：删除已迁出的传输层、正文编辑与全部待补索引/恢复分支；`append_result` 改为构造 `ResultPublication` 并注入自身写接缝（`_authorize_write`/`_get_issue`/`_save_draft`/`read_task`），不再自持恢复规则。

**调用方接线证明（新 module 被现有调用真实使用，非未接线实现）：**

- 现有结果追加入口 `GithubBackend.append_result` 直接委派 `mgs_result_publication.ResultPublication.append`。
- CLI `append-result`（`mgs_records.py` L825）、受控远端通道 `mgs_runtime` 的 `execute_op("append_result", …)`（草稿重放 `publish_drafts` → `_replay_draft` → `execute_op` 同一入口）都经该委派路径，在线执行与重放复用同一恢复事实。
- `mgs_record_model._edit_body` 被 adapter 的 update/set_triage/close 与发布恢复共用；`mgs_github_transport` 的 `UrllibTransport`/`api_base_for`/`token_from_env`/`default_api_base`/`API_BASE_ENV` 仍从 `mgs_github` 兼容可达（现有 CLI、mgs_records、mgs_runtime 调用面不变）。
- 新增回归 `test_append_result_online_and_execute_op_share_recovery_fact`（tests/test_github_result_recovery.py）：首轮 partial 后，直接 `append_result` 与 `execute_op` 两条入口收养同一评论并补齐索引，全程评论 POST 恰 1 次——接线与共享恢复事实的调用方可观察证据。
- `test_records_shared_body.py::test_dependency_direction_static` 扩展：AST 证明 `mgs_result_publication`/`mgs_github_transport` 不反向导入 `mgs_github`/`mgs_records`，且 `mgs_github` 实际依赖 `mgs_result_publication`（新 module 有真实调用者）。

**搬移期间保留的既有分支（逐项对照票 11 映射表零丢失）：**

- `test_github_result_recovery.py`（超时收养／partial 重试／草稿重放 partial 保留／读前失败待恢复／uncached 退化警告）全绿；新增接线用例。
- `test_github_pending_index.py`（SP-11 碰撞不冒认、缺字段/回执损坏披露、非法 JSON 待恢复、SP-14 碰撞共存、旧平铺迁移）全绿。
- `test_github_pending_clear.py`（SP-17 自然升级序列不误删、同身份双布局不复活、逐路径分侧核验、不可读/损坏保守）全绿；仅接缝调整：路径构造与清除改经 `mgs_result_publication` 公开函数（`_current_file`/`_legacy_file`/`_clear` 薄包装），断言与在盘状态语义不变。
- `test_github_migration_handover.py` 仅接缝调整：`urlopen` 打桩目标由 `mgs_github` 改为 `mgs_github_transport`（定义处），断言不变。

**验证命令与真实结果（本机实跑）：**

- 主题直跑：`python3 -B tests/test_github_result_recovery.py`、`test_github_pending_index.py`、`test_github_pending_clear.py`、`test_github_drafts.py`、`test_github_write_ops.py`、`test_github_cli.py`、`test_github_config_backend.py`、`test_github_ready_list_show.py`、`test_github_migration_handover.py` 全部 rc=0。
- 五套聚合器：`test_plugin_package` / `test_runtime_gate` / `test_runtime_boundaries` / `test_records_backend` / `test_github_backend` 全部 rc=0（`test_plugin_package` 先经 `./dist/build-package.sh` 重建 dist 后通过）。
- 全量 `tests/test_*.py` 逐文件跑：ALL PASS（无失败）。
- 冻结基线：`./.scratch/mygamestudio-architecture-refactor/evidence/baseline/run_baseline.sh` → 五套 `PASS`、`all_existing_checks_green=True`；跑完已 `git checkout --` 恢复 `results/` 与 `BASELINE-REPORT.md`（冻结产物未提交、未改动）。
- 静态检查：`ruff check` 新文件 All checks passed；`mgs_github.py` 残留 `E741`/`F841` 与改动前逐条相同（8 条，均属未触碰的既有代码）；本仓库未配置 mypy/pyright（无 pyproject/配置文件），类型面以 `python3 -m compileall` 与全量测试为准。
- 可复现构建：`./dist/verify-reproducible.sh` → 三项产物（tar.gz/manifest/SHA256SUMS）干净副本隔离重建逐字节一致、tar 无 PAX 扩展头，全部 PASS；交付包 SHA-256 `460f60edf08583481e9647b641fd81e9c1d583cbdf1064ded1989831362f3dc8`（脚本以 `git archive HEAD` 比对，提交后运行）。
- 零真实远端写入：全部验证经注入 `FakeTransport`/进程内 HTTP 替身，未访问真实 GitHub、未启动真实模型。

**净行数（物理行，含空行注释；口径同票 01 code_volume，工作树 vs 前基点 `3deb6d7`）：**

- plugin：4793 → 4990，**净 +197**（文件 7→9）；分列：`mgs_github.py` −589、新增 `mgs_result_publication.py` +568、新增 `mgs_github_transport.py` +149、`mgs_record_model.py` +69、其余零改动。
- tests：12694 → 12764，净 +70（接缝薄包装与接线回归）。
- acceptance：17995 → 17995，净 0；dist：146 → 146，净 0（交付包 tar 字节随 plugin 内容变化重建）。

**职责与长度复核：**

- `mgs_result_publication.py` 568 行，超 500 未超 600——已复查职责：单一内聚职责（结果发布恢复），由「文件语义 + 登记归属」与「发布生命周期」两段组成，均为同一职责的组成部分；进一步拆分会使恢复事实跨文件分裂（与本票「完整生命周期集中一个 module」目标相悖），故保留并记录。函数均 ≤80 行（最长 `load_pending_index` 77、`append` 59），事务性 `load_pending_index` 含布局迁移与损坏披露的完整判定，属可读范围。
- `mgs_github.py` 1220 行仍超 600：本票已将其从 1809 降至 1220（−589），剩余为迁移/交接/核验等未在本票范围的大块，按票 20「GitHub 大文件按已确认行数与职责约束收口并报告例外」继续处理；本票报告该例外。

**未验证限制：**

- 真实 GitHub 远端写入按授权范围未执行（本票禁止真实远端写入）；离线替身与回放不替代真实远端验收。
- 票 19（登记归属/兼容集中）与票 20（在线与重放恢复事实统一）为后续票；本票已把登记与生命周期集中并由真实追加路径使用，但二者的进一步收敛留待后续票。

### 复审修复记录（第一轮，独立复审发现 F1–F5）

**F1【去重，已改】** `mgs_result_publication.py` 中 `_read_first` 与 `_readback_comment` 各自重复「列评论 + 匹配 body」逻辑。抽出共享私有助手 `ResultPublication._find_comment(number, comment_body) -> (命中评论或 None, 类别, 说明, 传输故障 kind)`，类别为 `exists/absent/bad_response/error`；两处调用并各自把结果映射回原语义（`_read_first` 记 `read-first` attempts，`_readback_comment` 记 `readback` attempts）。**行为不变**：命中收养、确认不存在、坏应答、传输故障四条分支的返回值与 attempts 完全相同；助手不写 attempts、不做重试，职责边界与原实现一致。由既有 `test_github_result_recovery.py` 与 `test_github_pending_*.py` 全绿覆盖。

**F2【私有名跨模块，已改】** `_edit_body`/`_section_lines`/`_today` 原带下划线却被 `mgs_github.py` 与 `mgs_result_publication.py` 跨模块导入——事实公开面。在唯一定义处 `mgs_record_model.py` 去下划线改为公开名 `edit_body`/`section_lines`/`today`，同步更新：
- `mgs_github.py` 导入与 5 处调用（`build_task_body`、`update_task`、`set_triage`、`close_task` 及注释）；
- `mgs_result_publication.py` 导入与 `_finish` 中 2 处调用；
- 全仓 grep 确认 `plugin/`、`tests/`、`dist/` 无旧名残留（`.scratch/mygamestudio-v1-review*-fixes/evidence/` 下为冻结的历史版本快照，按证据不可改原则保留，非本票活代码）。

**F3【守卫缺口，已改】** `test_records_shared_body.py::test_dependency_direction_static` 原仅禁 `transport→{mgs_records,mgs_github}`，漏禁 `transport→mgs_result_publication`。按分层（`mgs_record_model`/`mgs_record_source` 中性共同语义 → `mgs_github_transport` 最底层接缝 → `mgs_result_publication` 发布恢复 → `mgs_github` 业务适配器）补全为对称负向断言：**transport 不得依赖 `{mgs_result_publication, mgs_github, mgs_records}`；publication 不得依赖 `{mgs_github, mgs_records}`**。修改后该测试 rc=0；另在 `/tmp` 副本中对 `mgs_github_transport.py` 临时注入 `import mgs_result_publication`，`_imported_modules` AST 扫描确认命中，负向断言会判红——守卫有效（反向验证后已删除副本，未改仓内文件）。

**F4【文档滞后，已改】** `mgs_record_model.py` 头部 docstring 原只述读面/纯核验。补入写面职责条目：`edit_body`/`section_lines`/`today` 与 `parse_task_body` 是同一套共同正文规则的读/写两面，票 18 从 adapter 移入，由本地后端与 GitHub 适配器在各自公开接缝上共用。

**F5【Data Clumps，留档评估】** `(repo, cache_dir, identity, result_markdown)` 四元组在 `pending_identity`/`pending_identity_digest`/`pending_index_file`/`legacy_pending_index_file`/`record_pending_index`/`load_pending_index`/`clear_pending_index` 及 `ResultPublication` 的 store 方法等 8 处函数签名重复出现，属 Data Clumps。**本轮不引入参数对象**：票 19（登记归属/兼容集中）与票 20（在线与重放恢复事实统一）将继续收敛此区域，届时按收敛后的真实调用面统一评估参数对象边界；本轮仅重命名与去重，不改变签名，避免与后续票的接口收敛相互冲突。

**复审修复验证（本机实跑，全部离线、零真实远端写入）：**

- 目标测试：`test_github_result_recovery`、`test_github_pending_index`、`test_github_pending_clear`、`test_records_shared_body`、`test_github_write_ops`、`test_github_drafts`、`test_github_cli` 全部 rc=0。
- 五套聚合器：`test_plugin_package`/`test_runtime_gate`/`test_runtime_boundaries`/`test_records_backend`/`test_github_backend` 全部 rc=0（`test_plugin_package` 先经 `./dist/build-package.sh` 重建 dist；`plugin/records/__pycache__` 旧字节码缓存含开发机绝对路径会使 provenance 检查误报，已清理由本任务产生的该缓存目录后通过）。
- 冻结基线：`./.scratch/mygamestudio-architecture-refactor/evidence/baseline/run_baseline.sh` → 五套 `PASS`、`all_existing_checks_green=True`；跑完 `git checkout --` 恢复 `results/` 与 `BASELINE-REPORT.md`。
- 可复现构建：dist 三件套重建后经 `./dist/verify-reproducible.sh` 与 `git archive HEAD` 干净副本隔离重建逐字节比对 PASS。
- 静态检查：`ruff check` 改动后的四文件仍为改动前既有 5 条（`mgs_github` E741×3 + F841×1、`mgs_record_model` E741×1，均在未触碰行），无新增；`compileall` 通过。

**复审修复净行数（物理行，基准 1f997a6 工作树 vs 本次）：** `mgs_record_model.py` 321→325（+4）；`mgs_github.py` 1220→1220（0）；`mgs_result_publication.py` 568→596（+28）；`tests/test_records_shared_body.py` 209→212（+3）；合计 **+35**（+86/−51）。

### 复审修复记录（第二轮）

**【（1）留档，可接受】** `_find_comment` 返回的 `category` 裸字符串（`exists`/`absent`/`bad_response`/`error`）是本 module 内的新词汇表，未共享枚举定义。判定为**可接受**：两处调用各自把类别映射回原语义（`_read_first` → `read-first` attempts，`_readback_comment` → `readback` attempts），映射点集中且语义清晰；四态去重的收益真实，引入枚举的收益暂不抵其新增的跨文件耦合。本轮留档不改；票 19（登记归属/兼容集中）与票 20（在线与重放恢复事实统一）收敛此区域时再评估是否统一到共享枚举。

**【（2）文档滞后，已改】** `tests/github_backend_transport.py::_pending_registration_content` 的 docstring 原称其构造形态「与 `_record_pending_index` 落盘形态一致」，而该方法已在票 18 由 `mgs_github.py` 私有方法迁出并改为 `mgs_result_publication.py` 的公开函数 `record_pending_index`（去下划线公开化）。docstring 已改为指向当前真实实现（`mgs_result_publication` 的 `record_pending_index`），只改注释、未改代码，替身构造内容与在盘状态语义不变。

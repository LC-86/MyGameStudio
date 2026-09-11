# 票 07 阶段 1 收口报告:任务读取的入口与交付兼容验收

- 票:`issues/07-read-stage-closeout.md`(阶段 1 收口,核心票)
- 本票前基点:`ce6c81f292128ac802608168207d81af02d322dd`
- 阶段 1 代码基线(票 01 冻结):`b8cda58ea2ff3b0fb18ae7d888cbd5d01eaca586`
- 分支:`codex/architecture-optimization`
- 证据分类:静态事实 / 合成回放 / 现有检查实跑;真实模型轮与真实远端写入**未执行**(见第 7 节)

本报告逐条核对 READ-01 至 READ-14 在当前集成版本(`ce6c81f` + 本票测试补充)上
的覆盖与本次实跑结果,并记录读取计数、净行数、超限项理由与回退说明。

---

## 1. READ-01 至 READ-14 映射表(编号 → 覆盖测试 → 本次结果 → 结论)

`当前集成版本` 指本票工作区;所有测试均为本次真实运行(`python3 -B tests/<file>.py`
与 `run_baseline.sh`),非历史结果。

| ID | 覆盖测试(文件::测试名) | 本次结果 | 结论 |
| --- | --- | --- | --- |
| READ-01 | `test_records_backend::test_ready_reads_config_and_each_task_once`;`::test_deps_reads_once_and_ready_does_not_recall_public_dependency_entry` | PASS | 本地 ready CONFIG 原文 1 次、每份 task.md 1 次(7 份);`task_dependencies` 1 次;ready 不再回调公开依赖入口;静态输入分类保持 |
| READ-02 | `test_github_backend::test_github_ready_fetches_task_set_once` | PASS | GitHub ready 全量任务集合 GET `/issues` 恰 1 次,依赖与判断用同一集合 |
| READ-03 | `test_github_backend::test_github_ready_does_not_consume_second_response_r1`;`test_records_backend::test_ready_second_call_reflects_changes_without_cross_call_cache` | PASS | 本次只消费第一份集合(本地 `task_list_reads=0`、GitHub 第 2 响应不被读取);结果无两时点混合;下一次顶层调用重新读取并更新分类 |
| READ-04 | `test_records_backend::test_ready_second_call_reflects_changes_without_cross_call_cache`;`::test_baseline_reads_config_and_core_docs_once`;`test_github_backend::test_github_ready_does_not_consume_second_response_r1` | PASS | 两次调用之间改任务/CONFIG/基线,第二次读到新内容;baseline 只读 CONFIG 1 次、每份核心文档 1 次且下一调用重读;无跨调用缓存 |
| READ-05 | `test_github_backend::test_github_ready_online_to_offline_preserves_source`;`::test_github_offline_list_show_metadata_and_no_marker_leak`;`test_records_backend::test_github_backend_does_not_read_local_tasks` | PASS | 在线转离线保留 `cached/fetched_at/source` 与 `cache_note`;无缓存明确失败且声明不静默回退本地;离线标记只出现在独立投影,不污染来源集合/ready |
| READ-06 | `test_records_backend::test_ready_and_deps_preserve_directory_order`;`::test_list_and_show_read_config_once_and_preserve_order`;`test_github_backend::test_github_ready_and_list_order_preserved` | PASS | 本地按目录顺序(deps/ready/list);GitHub list 按 identity 排序、ready/deps 保留后端返回顺序;排序副本不污染其他判断 |
| READ-07 | `test_records_backend::test_show_locates_by_directory_without_scanning_unrelated`;`::test_cli_list_show_projection_and_exit_codes` | PASS | 目录名与正文身份相反仍按目录定位;读取单个任务只打开该 task.md(不扫描无关);缺失任务 `RecordsError`+退出码 2 保持 |
| READ-08 | `test_github_backend::test_record_model_cross_backend_body_semantics`;`::test_verify_shared_core_validation_both_backends`;`::test_label_priority_and_conflict_preserved`(本票新增);`test_records_backend::test_record_model_shared_body_and_error_identity`;`::test_verify_malformed_records_still_discoverable` | PASS | 同正文经双后端读取共通字段一致(空字段/未知小节/全角冒号/分号/畸形任务),核心核验结论一致;后端专有字段保留;标签优先于正文、多标签取首个可识别语义、`triage_conflict` 登记(本票补测) |
| READ-09 | `test_records_backend::test_cli`;`::test_cli_deps_and_ready`;`::test_cli_list_show_projection_and_exit_codes`;`test_github_backend::test_cli_github_write_ops`;`::test_cli_local_backend_refuses_write_subcommands`;`::test_cli_github_handover_end_to_end` | PASS | 真实脚本入口 list/show/deps/ready/baseline/verify 的成功、阻塞与失败;JSON 类型/字段/原因/退出码(0/1/2)兼容;无新增 envelope |
| READ-10 | `test_github_backend::test_error_identity_across_import_orders_and_script`;`test_records_backend::test_record_model_shared_body_and_error_identity`;`::test_source_shared_with_query_and_import_orders` | PASS | records-first / github-first 两种导入顺序单一错误身份(`RecordsError` 同一对象,`GithubRecordsError` 继承);直接脚本触发记录错误走既有 except 分支、退出码 2、无未捕获 traceback |
| READ-11 | `test_github_backend::test_github_list_show_read_config_once_and_necessary_reads`;`::test_verify_offline_keeps_unchecked_and_skipped`;`test_records_backend::test_verify_github_reads_single_task_set_and_keeps_backend_reads` | PASS | GitHub show 保留集合定位+Issue 详情+评论读取;verify 任务集合 1 次且标签/评论核验各 1 次;离线标签/评论检查列入 `skipped` 并保持「未核对」表达 |
| READ-12 | `test_runtime_gate::review_fix_section`(R1 实例撤销在途、R3 审计失败回滚、R4 远端已发生结果);`::review2_sp1_section`(CONFIG 在途撤销);`::records_review_fix_section`;`test_runtime_boundaries` | PASS | 实例撤销后旧请求被拒且目标不变;CONFIG 在途撤销后锁内重读以 `remote_scope` 拒绝、远端零写入;审计不可用时本地回滚/远端不执行、结果审计失败如实回报;读取复用未回退受控写入语义 |
| READ-13 | `test_github_backend::test_switch_local_to_github`;`::test_handover_baseline_check`;`::test_switch_github_to_local_consistency`;`::test_cli_github_handover_end_to_end`;`::test_cli_reverse_migration_real_entry`;`::test_handover_reachability_requires_executed_check` | PASS | 迁移清单源任务/映射/保留项/确认项(唯一当前来源+授权确认)不变;apply 前置授权闸门、不自我授权;交接可达性只来自实际执行的检查且不携带凭据;替身 transport,零真实远端写入 |
| READ-14 | `test_plugin_package::test_records_backend_module`;`::test_mcp_gate_config`;`::test_no_dev_machine_paths`;`::test_dist_package_consistent`;`::test_dist_rebuild_byte_reproducible`;`::test_internal_references_resolve`;`::test_internal_material_provenance`;`::test_provenance_version_consistency`;`dist/verify-reproducible.sh` | PASS | 脚本与公开函数真实可导入可调用;`.mcp.json` 引用 `runtime/mcp_gate.py`;包内无 `/Users/` 绝对路径;清单/指纹/引用闭包一致;干净副本隔离重建逐字节一致;来源指纹核对通过 |

**覆盖缺口与本次补齐**:READ-01～READ-14 在票 02～06 已大部分落地;本票识别出
两处集成级覆盖不足并补测(不新增生产行为,仅测试):

1. READ-08 后端专有规则复验不足——原测试只断言 `triage_source/triage_conflict`
   **字段存在**,未验证标签覆盖正文、多标签优先级与冲突登记的实际取值。
   补测 `test_github_backend::test_label_priority_and_conflict_preserved`。
2. AC2 公开调用面固定不足——原测试多以行为和源码断言,未直接固定公开函数/
   工厂/transport 构造入口的参数名、顺序、默认值与关键字专有性。
   补测 `test_records_backend::test_public_interface_surface_and_factory_parameters`。

---

## 2. 固定脚本入口、公开函数、工厂参数与两种导入顺序(AC2)

- **固定脚本入口**:`tests/test_records_backend.py` / `test_github_backend.py` 的
  `run_cli` 直接以 `plugin/records/mgs_records.py` 为入口启动子进程;
  `entry_probe.py` 实跑 7 个 local-markdown CLI 入口的 11 个案例。
- **公开函数**:本票新增签名测试固定 `list_tasks/read_task/task_dependencies/
  startable_tasks/baseline_report/verify_project/github_backend` 的位置参数
  (`project_root`、`config_rel` 默认 `docs/mygamestudio/CONFIG.md`、`read_task`
  的 `task_id`)与关键字专有注入面(`transport/api_base/cache_dir` 默认 `None`)。
- **工厂参数**:`github_backend` 与 `mgs_github.UrllibTransport.__init__(api_base,
  token, timeout=10.0)`、`GithubBackend.__init__(config, transport,
  cache_dir=None)`、`plan_backend_switch`、`handover_baseline_check` 参数面固定。
- **两种导入顺序**:`test_source_shared_with_query_and_import_orders`(source-first /
  records-first)与 `test_error_identity_across_import_orders_and_script`
  (records-first / github-first)均验证单一错误身份、无循环导入错误。
- **迁移与交接的映射与错误**:READ-13 测试集覆盖(见上表),替身零真实远端写入。
- **脚本运行触发 GitHub 记录错误**:`test_error_identity_across_import_orders_and_script`
  经真实 CLI `create` 触发 `GithubRecordsError`,验证退出码 2、JSON `error` 对象、
  无未捕获 traceback(授权检查先于请求,零网络)。

---

## 3. 受影响的后端、运行时、包与实际 CLI 检查(AC3)

| 套件 | 本次结果 | 退出码 | 原始输出 |
| --- | --- | --- | --- |
| tests/test_plugin_package.py | PASS | 0 | `.scratch/.../evidence/baseline/results/checks/test_plugin_package.txt` |
| tests/test_runtime_gate.py | PASS | 0 | `.../checks/test_runtime_gate.txt` |
| tests/test_runtime_boundaries.py | PASS | 0 | `.../checks/test_runtime_boundaries.txt` |
| tests/test_records_backend.py | PASS | 0 | `.../checks/test_records_backend.txt` |
| tests/test_github_backend.py | PASS | 0 | `.../checks/test_github_backend.txt` |

- 实际 CLI:`entry_probe.py` 实跑本地 7 入口 11 案例,退出码合同
  `{success:0, records_or_file_error:2, judgement_failure:1}` 全部保持;
  11 案例的顶层键集合与退出码与票 01 冻结基线**逐项一致**。
- **READ-12 受控写入未回退**:`mgs_runtime.py:1119`、`mcp_gate.py:261`、
  `mgsrt_admin.py:189` 三个运行时文件相对票 01 冻结基线 **SHA-256 完全未变**
  (逐字节相同),runtime 探针读取计数保持一致(`policy.json 3`、`instances.json 2`);
  runtime 反例(R1 实例撤销在途、R3 审计失败回滚、R4 结果审计失败如实回报、
  SP-1 CONFIG 在途撤销)全部保持。读取侧复用不影响写入侧的锁内重读语义。

---

## 4. 当前完整包的模块引用、来源指纹、清单与隔离可复现构建(AC4)

- `dist/verify-reproducible.sh`:以 `git archive HEAD` 生成干净副本隔离重建,
  三项产物(tar.gz/package-manifest.txt/SHA256SUMS.txt)与 `dist/` 交付物
  **逐字节一致**,且无 PAX 扩展头。本次实跑 **PASS**。
- 交付包 SHA-256:`af91503f2956587e9024730ac82ccc124b8173cc1eec669c09aa72eb59fd789d`。
- `test_plugin_package` 覆盖:模块引用(`test_records_backend_module` 真实导入并
  调用公开接缝)、MCP 引用(`runtime/mcp_gate.py`)、来源指纹
  (`test_internal_material_provenance`、`test_provenance_version_consistency`)、
  交付清单(`test_dist_package_consistent`:plugin/ 文件集合与包内集合、
  manifest、SHA256SUMS 一致)、无开发机路径(`test_no_dev_machine_paths`)。
- **不拿旧包证明新代码**:本票生产区(plugin/)**零改动**,故交付包内容与当前
  生产代码一致;重建验证针对当前 HEAD 的 plugin/ 内容,而非历史包。

---

## 5. 生产净行数、文件长度与职责、读取计数、剩余限制(AC5)

### 5.1 净行数(相同范围,物理行含空行注释)

| 范围 | 票 01 冻结基线 | 当前(本票) | 净变化 |
| --- | --- | --- | --- |
| plugin(生产) | 4526(5 文件) | 4793(7 文件) | **+267** |
| tests | 9086(5 文件) | 10400(5 文件) | **+1314**(本票 +132) |
| acceptance | 20739(44 文件) | 20739(44 文件) | 0 |
| dist | 146(2 文件) | 146(2 文件) | 0 |

生产 +267 构成:新增 `mgs_record_model.py` 252、`mgs_record_source.py` 266;
`mgs_github.py` 1848→1809(−39);`mgs_records.py` 1109→897(−212);
三个 runtime 文件不变。净增来自两个承担共同职责的新 module 的实现成本,
扣除其吸收的重复代码后的实际增量(符合 spec 32「拆文件不算净减量」口径)。

### 5.2 生产文件逐文件行数与职责

| 文件 | 行数 | 职责 |
| --- | --- | --- |
| `plugin/records/mgs_record_model.py` | 252 | 共同类型与错误身份(`RecordsError`)、共同正文解析、纯记录核验(不依赖后端/查询) |
| `plugin/records/mgs_record_source.py` | 266 | 协作配置 CONFIG 原文解析、仓库坐标/授权解析、本地 Markdown adapter、文档位置检查 |
| `plugin/records/mgs_records.py` | 897 | 查询组织(同调用单次读取载体、list/show/deps/ready/baseline/verify 编排)+ 兼容 CLI 入口 |
| `plugin/records/mgs_github.py` | 1809 | GitHub Issues adapter、迁移/交接、远端读取与写操作、发布恢复 |
| `plugin/runtime/mgs_runtime.py` | 1119 | 受控写入运行时(策略、执行登记、本地事务、远端结果表达) |
| `plugin/runtime/mcp_gate.py` | 261 | MGS 通道 MCP 入口 |
| `plugin/runtime/mgsrt_admin.py` | 189 | 运行保障管理 CLI |

### 5.3 超限项理由(spec 30)

- `mgs_github.py`(1809)、`mgs_runtime.py`(1119)、`mgs_records.py`(897)超过 600 行:
  - `mgs_runtime.py` 属阶段 5 范围,本阶段**未触碰**(故不比票 01 更长);完整受控
    写入不变量(锁外预检/锁内重校验、持锁、审计、回滚)集中在同一职责内。
  - `mgs_github.py` 属阶段 4 范围,本阶段仅做了共享正文/来源的职责迁移(已净减
    39 行);其远端写与发布恢复的不变量集中在同一 adapter 内。
  - `mgs_records.py` 保留 CLI 与查询组织:已确认设计(task-reading「建议的 module
    与依赖方向」)明确「查询组织及既有 CLI 暂留 `mgs_records.py`」,并把 CLI 是否
    再拆留待「搬移后实际计行」判断。当前 897 行中 `_cli`(223)是参数解析+退出码
    合同的单一分发事务,与查询编排共用同一公开接缝与错误类型;拆开需引入额外的
    入口适配层而不减少职责,故本阶段按已确认设计保留并在阶段 6(票 23-25)继续
    消化。**验证方式**:五套检查 + `entry_probe` 覆盖全部 CLI 路由与退出码。
- 函数超过 80 行(明确理由的完整事务例外):
  - `mgs_records._cli` 223、`mgs_github.append_result` 185、`mgs_runtime.remote_record`
    180、`mgs_runtime.write` 161、`mgs_github.verify` 114、`mgs_records.baseline_report` 91。
  - 均为参数分发或「读-执行-审计-回滚」完整事务;前三项属阶段 4/5/6 处理范围。

### 5.4 CONFIG 与任务读取次数(本次 audit-hook 实测,与票 01 基线对比)

| 入口 | 票 01 冻结基线 | 当前 | R1 差异 |
| --- | --- | --- | --- |
| 本地 ready | CONFIG 6,每份 task.md 2 | **CONFIG 1,每份 task.md 1** | R1 修正 |
| 本地 deps | — | CONFIG 1,每份 task.md 1 | 同调用单次 |
| 本地 list / show | — | 各 CONFIG 1;show 只读目标 task.md | 兼容 |
| 本地 baseline | — | CONFIG 1,每份核心文档 1(版本与指纹同源) | 同调用单次 |
| 本地 verify | — | CONFIG 1,每份 task.md 1 | 同调用单次 |
| GitHub ready | 全量集合 2 次 | **全量集合 GET 1 次** | R1 修正 |
| GitHub list / show | — | 各 CONFIG 1;show 另读集合+详情+评论(接口必需) | 兼容 |
| runtime 受控写入 | policy 3 / instances 2 | policy 3 / instances 2(未变) | 无回退 |

### 5.5 剩余限制

- spec 33 的 CONFIG 6→1、任务集合 2→1 目标**已达成**并由 audit-hook 实测;
  客户端解码计数(21000)属阶段 3,不在本阶段范围,未随之变化。
- 真实模型轮与真实远端写入未执行(零网络/零凭据约束),见第 7 节。

---

## 6. 匹配版本与回退说明(AC6)

- **本票交付包**:`dist/mygamestudio-0.18.0.tar.gz`,SHA-256
  `af91503f2956587e9024730ac82ccc124b8173cc1eec669c09aa72eb59fd789d`,
  与当前 `plugin/` 生产内容一致(verify-reproducible PASS)。
- **回退方式**:恢复本票前基点 `ce6c81f292128ac802608168207d81af02d322dd`
  的代码与对应交付包;阶段 1 不涉及用户数据或持久化格式迁移,回退不需要数据迁移。
- 阶段 1 各票的匹配提交见 execution-log(02 `e2ae564`、03 `891dfe6`、04 `91b33dc`、
  05 `b1a9b72`、06 `b5ae10d`)。

---

## 7. 未执行的真实宿主/远端验收(明确标注)

以下为**未验证限制**,不因离线检查通过而视为已完成:

- **真实模型轮**:未启动任何真实模型调用(票 02-07 全程零真实模型)。
- **真实远端写入**:GitHub 相关检查全部使用本地替身 transport,零真实远端写入;
  真实 GitHub 仓库的读写、标签核验、迁移 apply 未执行。
- **日常安装替换与发布**:未安装、未发布、未推送、未打标签。
- **真实网络耗时**:合成探针不推导真实网络耗时或全部宿主行为。

**阶段技术结论不代替安装与发布**:本报告的 PASS 是当前集成版本在本机离线条件下的
技术验收结论,真实宿主的安装、显式调用与结果回读仍按 acceptance/ 隔离验收流程与
相应授权单独执行。

---

## 8. 本票改动内容

- 新增测试(2 处,均为覆盖补齐,不改生产行为):
  - `tests/test_records_backend.py::test_public_interface_surface_and_factory_parameters`(+75 行)
  - `tests/test_github_backend.py::test_label_priority_and_conflict_preserved`(+57 行)
- 生产区(plugin/)**零改动**;`dist/` 内容与当前生产一致,无需重建(verify-reproducible PASS)。
- 本报告为新增证据文件(`.scratch/.../evidence/stage1-closeout.md`)。

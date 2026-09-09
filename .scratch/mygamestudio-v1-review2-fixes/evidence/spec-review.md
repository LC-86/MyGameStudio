# 第二轮独立 Spec 轴复审（A/B 专项）

审查对象 `d934332`，比较 `git diff 31dabfd...d934332`；真仓库实际 HEAD 开始/结束均为 `b89b548f59336f57f63df70bda331bc204bd12de`，`git status --porcelain` 始终为空。`b89b548` 与指定审查版本的差异由主审记录。独立副本：`/tmp/mygamestudio-spec-review-2-dnioch5b/copy`，由 `git archive d934332` 生成。真仓库只读；所有变异、生成文件及运行夹具位于 `/tmp`；没有真实远端写入或模型轮调用。

## Spec 发现（4 项：1 P1、3 P2）

### SP-1 [P1] 远端最终核验遗漏 CONFIG 仓库授权，撤销后在途请求仍写入

`plugin/runtime/mgs_runtime.py:953–965` 锁内重读实例及 policy，却沿用 `:899–940` 锁外读取的 CONFIG、仓库授权和 backend。探针先暂停远端 `append-result` 于取服务锁前；另一 GateService 通过正常 `write` 入口、正确 expected SHA256，把项目 CONFIG 的 `issues-write` 撤销并成功返回 allow；随后恢复在途请求，它仍返回 allow，替身新增 1 条评论。新的同类请求立刻按 `remote_scope` 拒绝。这里未撤销身份令牌，暴露的是仓库授权的时序缺口，不能冒称原 R1 身份撤销反例仍失败。

违反 `.scratch/mygamestudio-framework/contracts/records.md:39`「创建或修改远端记录前核对明确的仓库及操作授权」及修复票 02 `:15` 的最终策略核对同临界区要求。建议将 CONFIG 授权及其决定的 backend/仓库也纳入锁内最终核验。证据：`extra_probes.py` / `extra-probes.json` 的 `remote-config-revoke-inflight`；决定性数字：撤销 allow、在途 allow、fresh deny、comments=1。

### SP-2 [P2] 结果评论已发布、后续索引更新超时，却仍返回 deny，重试产生重复评论

`plugin/records/mgs_github.py:846–850` 在评论已经创建后执行 PATCH/回读，故障直接抛出；`plugin/runtime/mgs_runtime.py:981–992` 将异常统一记作 `remote_upstream` deny，丢失已发布 comment_id 和已成功步骤。通过 MCP `handle_tools_call` 的确定性探针：POST 评论成功，随后 PATCH 超时 → 调用方收到 deny、note=null，而替身已有 1 条评论；恢复 PATCH 并按原请求重试后得到 allow，评论数为 2。原 R4 的“审计无法落盘”反例已经修复，当前是同一远端结果诚实性合同的邻近残留路径，不应把两者合并成“R4 原反例未修”。

违反 `.scratch/mygamestudio-framework/contracts/runtime.md:16`「拒绝、失败、已写入待验收分别表达」及 records `:39` 的回读防重要求。建议保留已成功的评论身份与部分完成状态，恢复时只补索引。证据：`partial_remote_probe.py` / `partial-remote-probe.json`；审计现在有 intent/deny，不能写成“没有审计”。

### SP-3 [P2] 草稿幂等键忽略仓库，丢失另一仓库的相同待发布请求

`plugin/records/mgs_github.py:542–557` 的内容哈希及 prior 判断仅包含 op/args。与 S1 允许留存跨仓库草稿的共享 cache 场景组合：固定同一秒，在两个各自有仓库授权的 backend 用同一 cache 保存同身份、标题、参数的离线 create。第二次返回第一份草稿路径且 `idempotent:true`，目录里仅 1 份、repo 仍为旧仓库。切回当前仓库发布时被 S1 正确拒绝、published_count=0，当前仓库的新请求根本未保存。原同仓库不同内容的 S6 探针确已通过。

违反修复票 01 `:20`「每个待发布操作有稳定且唯一的身份」及 project-configuration `:37` 保存待发布草稿语义。建议把目标仓库纳入身份及幂等比较。证据：`extra_probes.py` / `extra-probes.json` 的 `S6-cross-repo-idempotence`。

### SP-4 [P2] 独立秘密扫描对“部分指定路径不存在”失效开放

`acceptance/16-producer-complete-loop/secret_scan.py:84–92` 对不存在目录执行 `os.walk`，静默无输出；`:134` 仅检查总扫描文件数是否为 0。因此 `--evidence <存在的干净目录> --project <不存在的目录> --registry <有效且含1条登记>` 返回 0，扫描 1 文件，声称未发现凭据，未指出项目根遗漏。该脚本自身说明 `:16–17` 把零目标（路径缺失或为空）视作输入错误，但没有逐根落实；修复票 04 `:15,22` 要求证据入库前的独立扫描闭环；不能由另一目录非空掩盖缺失输入。

这是新扫描资产的输入校验缺口；没有证据说明本次正式扫描实际遗漏了路径或仍有明文，不作该推断。最小命令：`python3 secret_scan.py --evidence /tmp/<fixture>/evidence --project /tmp/<fixture>/misspelled-project --registry /tmp/<fixture>/instances.json`，其中 evidence 含干净文件、registry 含 1 个合法 token_hash。证据：`missing-scan-target.json`。建议逐根验证存在性及遍历错误并退出 2。

## A/B 逐项复核

| 对象 | 当前结论 | 依据与边界 |
| --- | --- | --- |
| S1 错仓库发布 | 原反例真实修复 | `test_publish_drafts_refuses_cross_repo_draft` 绿；撤掉比较后 4 断言红、恢复绿；发布前核对 repo，拒绝草稿保留 |
| S2 回读失败重发 | 原反例真实修复；邻近部分成功问题见 SP-2 | `test_append_result_readback_failure_keeps_uncertain` 与通道 `records_review_fix_section` 绿；一次 POST、uncertain、没有错误草稿重放 |
| S3 反向迁移 | 修复成立 | 四点一致 + `test_cli_reverse_migration_real_entry` 真实 Python CLI/Urllib/localhost HTTP 入口绿；不涉及真实 GitHub；不改变既有原票 |
| S4 交接可达 | 修复成立 | 无通道/离线/非2xx失败，实际2xx成功；`auth=False` 无凭据探针及 Urllib 头检查绿；B CLI 漏改调用另已修复 |
| S5 缓存元信息 | 修复成立 | `test_startable_tasks_reports_cache_metadata` 绿，顶层 cached/fetched_at/source/cache_note 可区分 |
| S6 同秒覆盖 | 原同仓库反例成立；组合边界仍缺 SP-3 | `test_draft_unique_identity_no_overwrite` 绿，但跨仓库同参数混同 |
| 建议1 共享核心核验 | 语义修复成立 | `mgs_records.py:716–796` 公共校验被两个 backend 使用；同一缺工作请求字段任务两侧都失败，针对回归绿 |
| 建议2 change_note 三路 | 语义修复成立 | 在线、保存、重放回归及通道回归绿；仍有动作分发结构，代码味道是否完全消除由 Standards 轴判断 |
| R1 身份撤销 | 原本地/远端反例真实修复；授权时序范围仍见 SP-1 | `review_fix_section` 绿；锁内重读身份，撤销后本地不落盘、远端零请求；未把 CONFIG 撤销冒充身份撤销 |
| R2 用途丢失 | 修复真实成立 | 缺失条目→purpose deny，畸形策略→policy deny，显式 restrict=None 保持兼容；write/scope/remote 三路当前绿。恢复旧缺省后 6 断言红、恢复绿 |
| R3 权限位 | 修复成立 | 同一 section 实跑 0755/0600 更新、新建、审计失败回滚内容/权限；逐位 fchmod 与恢复 mode 参数符合票面限定 |
| R4 审计时序 | 原审计故障反例修复成立；完整结果语义仍见 SP-2 | 审计不可用→执行前 audit deny、零评论；结果审计失败→allow+audit_recorded=false+intent 可核对，section 当前绿 |
| R5 字节重现 | 代码及固化检查符合原修复方向；当前完整运行由主审核定 | `build-package.sh:65–70` tar 层排除 xattrs/ACL/fflags；`verify-reproducible.sh` 干净副本三文件 cmp 与 PAX 扫描；package 回归确实注入不同 xattr。此子任务未重跑 R5 构建，不把阅读当实测 |
| R6 脱敏与历史 | 原修复机制/现有回归方向成立；扫描输入闭合不完整 SP-4 | sanitize 不枚举实例名，scanner 按登记 token_hash 与 ARENA 互补、命中不回显；历史改写/真实登记释放/当前全对象扫描由主审核定。当前票面不能由本子任务单独宣布“全无秘密” |
| B CLI handover | 先红后绿声明可复验 | 当前绿→恢复 `handover_baselinecheck_item` 拼错后 JSON 断言红→恢复绿；崩溃退出码仍1，与合法未发布基线拒绝同码，新增 JSON 断言有实际检错价值 |

四票均有两轴留档，但票 03/04 Comments 实际写明 Standards 子代理、Spec 实施自查；不能描述成四票当时都由两个独立子代理审查。批次约定 `spec.md:17` 只要求“两轴复查并留档”，没有明确必须每轴由独立子代理完成，本轮独立 Spec 复核不能据此追认历史独立性，也不单列违反。

## 实际验证与限制

- A 变异两项、B 变异一项均为当前回归 **green→red→green**，共 9 次定向运行。A-S1 红 4 条、A-R2 红 6 条、B 红 1 条；日志和 diff 替换点保存在 `mutations.json`。这是当前测试敏感性的实证，不能单凭它证明历史先红运行的时间次序。
- 另 10 次独立定向运行全部退出 0，覆盖 S2/S3/S4/S5/S6、两个建议、探测无凭据和通道不确定语义；R1–R4 的 `review_fix_section` 已包含于 R2 三阶段回归，未重复跑整套。
- 4 个新/残留反例均在未变异的 d934332 副本上重现。SP-1 第一次布景曾因 macOS `/tmp` 与 `/private/tmp` 绝对路径语义触发 path deny，改用正常项目相对路径后撤销确认 allow 才采纳；不把布景失败当产品发现。
- 未执行原始会话验收脚本、模型轮、remote-replay.sh、真实远端写入；CLI 只连接 localhost 替身。完整五套件、33 driver、真实远端只读、dist 重现、历史/全秘密扫描与票 C/D 由主审并行承担。
- 命令类别：Git 只读 rev-parse/status/log/diff/archive；rg/sed/cat/nl 读文档实现测试；Python 在 /tmp 建副本/测试/变异/恢复；本地 fixture HTTP 子进程；本地 JSON 报告写入。真仓库未运行可生成 pycache 的 Python import。

Spec 交付判断：原 12 项中所负责的 10 项行为反例以及 B 漏改已得到针对实证支持；但新发现 1 P1、3 P2，不能据原回归全绿宣布完整远端授权、结果恢复和扫描输入纪律已收口。R5/R6 全局证据最终以主审实测合并结论为准。

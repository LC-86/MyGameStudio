# MyGameStudio 架构重构执行日志

主控代理按 README「任务清单」串行派发 26 张工单，一次一张票，每票一个全新子代理。本文件是唯一进度真相源；会话中断后先读本文件，从最后一张未完成的票继续，不重做已完成票。

- 分支：`codex/architecture-optimization`（全程不切分支）
- 任务发布基线：`b8cda58ea2ff3b0fb18ae7d888cbd5d01eaca586`
- 开始日期：2026-09-11
- 核心票（需主控 code-review 复审）：01、07、13、17、18、21、22、23、25、26
- 授权：每票由子代理提交一次；主控每票收尾后单独提交本文件；不推送、不打标签、不动 GitHub
- 流程备忘（复审轮沉淀，后续票子代理提示沿用）：工单 Status 终态用仓库约定 `resolved`（docs/agents/issue-tracker.md L26），不用自造值。

## 票 01 — 固定可复跑的兼容与效率基线（阶段 0，核心票）

- 状态：**done（2026-09-12 经用户批准第三轮修复后收口）**
- 前基点 SHA：`b8cda58ea2ff3b0fb18ae7d888cbd5d01eaca586`
- 交付提交：`c31613a`（基线交付）→ `2f31a50`（第一轮修复）→ `0efcc74`（第二轮修复）；全部仅在 `.scratch/mygamestudio-architecture-refactor/` 下，生产区（plugin/tests/acceptance/dist）累计 diff 0 行
- 交付内容：`evidence/baseline/` 可复跑基线（run_baseline.sh 总入口 + code_identity/records/client/code_volume/entry 五探针 + baseline_common 共享 + results/ 产物 + BASELINE-REPORT + evidence-map）；五套现有检查实跑全绿；R1 缺陷证据（CONFIG 6 次、任务集合 2 次、混合时点）独立探针保留；客户端 5 族 + 21000 次解码计数；入口输出基线（7 入口 11 案例）；runtime 读取计数复跑；行数口径与回退参照
- 复审循环：第 1 轮复审（Standards 硬违规 1 + smell 3；Spec 发现 5）→ 修复 `2f31a50` → 第 2 轮复审（Standards 硬违规 0 + smell 残留；Spec 5 项确认解决、余 2 口径瑕疵）→ 修复 `0efcc74` → 第 3 轮复审：六条验收满足、无越界、无伪造，残留工单 markdown 数值矛盾与不可核对哈希断言 → **用户批准第三轮修复** `e9ae6cc`（仅工单 markdown：旧数值块回收、哈希断言修正、「五个探针」、主控裁定留档）→ 主控核验通过，视为干净收口。
- 主控裁定（留档于票文件第三轮记录）：产物 JSON 自身行数用剥离不稳定字段的确定性计数不违反 spec 物理行约束（该条约束重构收益统计，生产四范围本票 0 行）；三个判断性 smell（worktree 键名不一致、三处同形行计数、_normalize_volatile 轻度通用性）接受留档不修。
- 交付提交：`c31613a` → `2f31a50` → `0efcc74` → `e9ae6cc`（4 笔，全部仅在 .scratch/mygamestudio-architecture-refactor/ 下）；生产区累计 diff 0 行。

## 票 02 — 让双后端共用正文与错误语义（阶段 1）

- 状态：**done（2026-09-12，非核心票，主控验收通过、跳过复审）**
- 前基点 SHA：`05038fdd632a18ad5a17b60f51a0bc6f30df876d`
- 交付提交：`e2ae564`（新增 plugin/records/mgs_record_model.py 252 行：共同错误身份 RecordsError + 共同正文规则 + 纯记录核验；mgs_records.py 1109→937；mgs_github.py 1848→1843；tests +220；dist 交付包同步重建）
- 主控验收：五套检查实跑 rc=0；dist/verify-reproducible.sh PASS（交付包 SHA-256 bfe5b982…）；票文件 Status=resolved；净行数生产 +75 / 测试 +220 / dist manifest +1；records_probe 稳定字段与基线一致（CONFIG 6、task 2、GitHub 集合 2、解码 21000——本票按设计不改读取次数）
- 复审：跳过（非核心）
- 遗留：无（真实模型/远端写入按授权范围未执行，属全任务一贯限制）

## 票 03 — 统一配置与本地来源并解除反向依赖（阶段 1）

- 状态：**done（2026-09-12，非核心票，主控验收通过、跳过复审）**
- 前基点 SHA：`1e78104631dba1088815871413f8455bb3c4f92e`
- 交付提交：`891dfe6`（新增 plugin/records/mgs_record_source.py 266 行：CONFIG 原文解析 + 仓库坐标/授权解析 + 本地 adapter；mgs_records.py 936→807、mgs_github.py 1843→1809；tests +143；dist 重建）
- 主控验收：五套实跑 rc=0；verify-reproducible.sh rc=0；Status=resolved；三个新测试（静态依赖方向 AST、双导入顺序、已加载配置同源）真实存在；ready 读取计数与基线一致（单次化留待票 04）
- 复审：跳过（非核心）
- 遗留：R1 未修（属票 04，按设计）

## 票 04 — 修正可开工查询的重复读取与混合结果（阶段 1，R1 行为修正）

- 状态：**done（2026-09-12，非核心票，主控验收通过、跳过复审）**
- 前基点 SHA：`ff16231314ec30b9503ca8d51d95cdc32cc0420d`
- 交付提交：`91b33dc`（mgs_records.py 807→860：_Reading 同调用载体 + _read_workspace 单次读取 + 纯依赖/分流计算；tests +341；dist 重建；mgs_github/model/source 零改动）
- 主控验收：独立复跑 records_probe——本地 ready CONFIG 1/task 1；R1 场景第二响应未消费（本地 task_list_reads=0、GitHub 集合请求 1）、结果 startable 无混合；五套 rc=0；verify-reproducible PASS；冻结基线未动；Status=resolved
- 复审：跳过（非核心）
- 效益记录：**R1 已修正；读取计数 6/2→1/1 达成（spec 33 目标）**
- 遗留：基线探针文案仍描述修复前现象（观察性、冻结产物未改）；baseline_report 同源整理未单列计数断言（已记录）

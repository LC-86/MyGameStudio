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

## 票 05 — 让列表与单任务读取复用配置并保持兼容（阶段 1）

- 状态：**done（2026-09-12，非核心票，主控验收通过、跳过复审）**
- 前基点 SHA：`f9b830f936aacad134e34448b2bca7eac598e461`
- 交付提交：`b1a9b72`（mgs_records.py 860→851：list/show 同次配置进入后端、排序与离线标记改独立投影、删除死函数 _local_config；tests +273；dist 重建）
- 主控验收：五套 rc=0；verify-reproducible PASS；Status=resolved；探针抽查 ready 计数保持 1/1；entry_probe 11 案例与冻结基线一致（JSON 结构与退出码）
- 复审：跳过（非核心）
- 遗留：entry_probe 覆盖口径沿用票 01（local-markdown 入口）；真实远端一贯未执行

## 票 06 — 让基线与核验复用读取且保留证据含义（阶段 1）

- 状态：**done（2026-09-12，非核心票，主控验收通过、跳过复审）**
- 前基点 SHA：`1a3176225c7ca2d80745ed910240454ad01e5da9`
- 交付提交：`b5ae10d`（mgs_records.py 851→897：baseline/verify 走同次配置与任务集合、核心文档同源版本/指纹、离线 skipped 表达保持；tests +205；dist 重建）
- 主控验收：五套 rc=0；verify-reproducible PASS；Status=resolved；读取计数 baseline/verify CONFIG 2→1、核心文档各 2→1；entry_probe 11 案例与冻结基线一致
- 复审：跳过（非核心）
- 遗留：_doc_baseline_versions 作为公开测试接缝保留（行为等价组合）；真实远端一贯未执行

## 票 07 — 完成任务读取的入口与交付兼容验收（阶段 1 收口，核心票）

- 状态：**done（2026-09-12，核心票，复审两轮修复后主控核验收口）**
- 前基点 SHA：`ce6c81f292128ac802608168207d81af02d322dd`
- 交付提交：`085f02a`（READ-01~14 全覆盖映射 + 阶段收口报告 evidence/stage1-closeout.md + 集成级测试补齐 +132；生产零改动）→ `63d45c4`（第一轮修复：READ-11 补引、冻结产物措辞、测试去重）→ `15c6efe`（第二轮修复：行数回填 10406/+138、READ-11 结果文件子句补引）
- 复审循环：第 1 轮（Standards 零硬违规 + 2 smell；Spec 报告保真但 READ-11 漏引、冻结产物措辞不严）→ 修复 `63d45c4` → 第 2 轮（三项全解决，残留行数滞后 +6 与 READ-11 子句映射偏弱）→ 修复 `15c6efe` → 主控直接核验（数字 10406/+1320/+138 一致、补引落实、留档完整）→ 干净收口
- 复审结论：READ-01~14 逐条有真实测试覆盖且本次实跑 PASS；runtime 三文件相对票 01 基线逐字节未变（READ-12 无回退的直接证据）；包 SHA-256 af91503f… 可复现；报告无夸大
- 留档 smell：request 默认字典两处重复（测试辅助）；_seed_raw_issue 10 参数（测试辅助）；tests 大文件沿用 spec 31 豁免（票 11 将重组）
- **阶段 1 效益小结（对照票 01 基线 4526/9086/20739/146）：plugin 4526→4793（7 文件，+267，新增共享 model 252 + source 266，mgs_records 1109→897、mgs_github 1848→1809）；读取计数达成：ready CONFIG 6→1、任务集合 2→1、baseline/verify CONFIG 2→1、list/show CONFIG 2→1；R1 已修正；测试 9086→10406（+1320）**

- 状态：**done（2026-09-12，非核心票，主控验收通过、跳过复审）**
- 前基点 SHA：`b58442115d27abb25587cafe2d72e6222d1e1e12`
- 交付提交：`8bb5408`（新增 acceptance/18 evidence_judgement.py 171 行共享判据 seam + evidence_adapter.sh 11 行 Shell 适配层；run.sh 1323→1232 去内联 heredoc；tests +41 不再正则截取；生产 plugin/ 零改动）
- 主控验收：五套 rc=0；verify-reproducible PASS；Status=resolved；seam 存在且 run.sh/测试的正则截取清零；A/B 留存回放对照 9/9+21/21 一致（子代理实测）
- 复审：跳过（非核心）
- 遗留：curl 判据迁移属票 09；test_plugin_package.py 仍 4090 行（票 10 拆分）；最小接入对照不含真实 turn

## 票 09 — 让直连失败判据通过同一事件入口验证（阶段 2）

- 状态：**done（2026-09-12，非核心票，主控验收通过、跳过复审）**
- 前基点 SHA：`c1711fe931fbf93755abd8c43822f500740ea2c5`
- 交付提交：`d8c127a`（evidence_judgement.py 171→371：judge_curl_direct_denied 迁入 + curl-direct-deny 子命令；adapter +5 行；run.sh 1232→1007 去 heredoc −225 行；tests +10 去正则截取；生产零改动）
- 主控验收：五套 rc=0；verify-reproducible PASS；Status=resolved；两判据函数同文件共存、正则截取清零；A/B 差分 79/79（子代理实测）
- 复审：跳过（非核心）
- 遗留：url_targets 64 行/judge_curl 50 行为逐字搬运（未借机重写）；残余边界与原实现一致；test_plugin_package.py 仍 4100 行（票 10 拆分）

## 票 10 — 按行为组织包与场景验收检查（阶段 2）

- 状态：**done（2026-09-12，非核心票，主控验收通过、跳过复审）**
- 前基点 SHA：`3d0c0c3d17c283f26b8d12770a2a882bbab021ff`
- 交付提交：`d4b7c62`（test_plugin_package.py 4100→111 聚合器；拆出 9 主题文件+判据主题 378 行+支撑 58 行+具名夹具 227 行；98 处内联事件转具名数据逐字节一致；案例 0 丢失 1630 条 check 全重现；映射表 evidence/10-case-mapping.md）
- 主控验收：聚合器与抽查主题入口 rc=0；其余四套 rc=0；Status=resolved；plugin/dist/acceptance 零改动
- 复审：跳过（非核心）
- 效益记录：测试代码净 −888 行；最大文件 424 行、最大函数 153 行（原 1550）；净行数来自内联事件转具名数据，无判定删除
- 遗留：两个 80+ 行函数例外留档（审查票固化的多重注入边界例）；acceptance/18 run.sh 1007 行例外留档（旧大文件随所属阶段处理）

## 票 11 — 按用户行为组织任务后端回归（阶段 2）

- 状态：**done（2026-09-12，非核心票，主控验收通过、跳过复审）**
- 前基点 SHA：`26fd1086c91046b1f9aa726376d7920158bb6f13`
- 交付提交：`07e930b`（records 1560→6 主题+聚合器 63+支撑 366；github 2758→9 主题+聚合器 71+支撑 514；零丢失三重证明 AST+check 计数+插桩发出数；映射表 evidence/11-case-mapping.md；生产/dist 零改动）
- 主控验收：两聚合器+抽查主题+其余三套全 rc=0；Status=resolved；生产区零改动
- 复审：跳过（非核心）
- 遗留：两个 85/88 行函数原样迁入（记录例外）；净 +622 行为拆分壳开销

## 票 12 — 按完整受控操作组织运行保障回归（阶段 2）

- 状态：**done（2026-09-12，非核心票，主控验收通过、跳过复审）**
- 前基点 SHA：`5de548345084ce4d26e8a108c7995d7ac6695ed8`
- 交付提交：`e0380af`（gate 1606→8 主题+聚合器 74+支撑 92；boundaries 433→2 主题+聚合器 68+支撑 152；零丢失插桩证明 gate 259→259/bounds 44→44；映射表 evidence/12-case-mapping.md；生产/dist 零改动）
- 主控验收：两聚合器+抽查主题+其余套件全 rc=0；Status=resolved；生产区零改动
- 复审：跳过（非核心）
- 遗留：真实模型/远端一贯未执行（acceptance/02/03/11/13 覆盖真实路径）
- **阶段 2 小结：判据 seam（mcp+curl）建成并双向接入；三大测试文件（plugin_package 4100、records 1560、github 2758、runtime 2039）按行为主题拆分完毕，全部聚合器保留、案例零丢失；生产代码除票 08/09 的判据 seam（acceptance/ 下）外零改动**

## 票 13 — 建立共享客户端并接通标准事件场景（阶段 3，核心票）

- 状态：**done（2026-09-12，核心票，复审两轮修复后主控核验收口）**
- 前基点 SHA：`e42d17b4659db09550575d3f29fb32d8074d7829`
- 交付提交：`b4f5eae`（acceptance/_shared/appserver_core.py 共享核心 253 行 + 三场景 02/17/18 迁入 80 行薄壳 + 受控替身/回放测试 + 证据探针）→ `d8dcfcb`（第一轮修复：测试行为化去源码绑定、守卫显式失败、死参数清理 253→240）→ `c366194`（第二轮修复：行数回填 20615/−195、11406/+497、三项留档；F5「死 import」前提被反证推翻——该 import 是票 01 冻结探针打桩所必需，保留并留档）
- 复审循环：第 1 轮（验收全真、方法学可靠；测试源码绑定违规 + 死参数 + 守卫静默通过隐患）→ `d8dcfcb` → 第 2 轮（修复全落实、验收保持；残留薄壳死 import 误报 + 行数滞后）→ `c366194` → 主控核验收口
- 效益记录：**解码计数 21000→1000（同法 A/B 实证）；三场景 225→80 行薄壳；expand 红线保持（15 份旧实现零删除）**
- 留档：close() 裸 except（继承，票 15/16 处理）；三壳 argparse 重复（expand 有意，票 17 处理）；find_legacy_client 子串定位（过渡期，票 17 更新）；_message 探针回退分支；薄壳 import 为冻结探针所必需

## 票 14 — 迁移最小与扩展事件的普通场景（阶段 3）

- 状态：**done（2026-09-12，非核心票，主控验收通过、跳过复审）**
- 前基点 SHA：`9744601571526aa9c4f1b9470e3e53fa4f3f1d22`
- 交付提交：`db9619e`（01/03/04 薄壳化 196~225→78~84 行；共享核心 240→251 仅加 keep_types/event_methods 参数；新测试主题 234 行；A/B 回放与受控替身对照；票 13 红线复验 21000/1000 不变）
- 主控验收：五套+client 两主题全 rc=0；Status=resolved；18 份客户端文件齐全（expand 红线）；plugin/dist 零改动
- 复审：跳过（非核心）
- 遗留：旧客户端物理文件删除按票 17 收口；中断场景属票 15/16

## 票 15 — 接通并迁移绝对阈值中断场景（阶段 3）

- 状态：**done（2026-09-12，非核心票，主控验收通过、跳过复审）**
- 前基点 SHA：`8f8407f6e30646e16367c52fce538fea202b8327`
- 交付提交：`e1267b1`（05~14 十场景薄壳化 272→97 行；共享核心 251→359：count_audit_allows 绝对阈值 + wait_turn_interruptible 进程组中断；新测试主题 361 行；A/B 回放 + 受控进程组验证；13/14 红线计数不变）
- 主控验收：五套+三个 client 主题全 rc=0；Status=resolved；plugin/dist 零改动
- 复审：跳过（非核心）
- 遗留：相对阈值属票 16；旧客户端文件删除按票 17

## 票 16 — 迁移相对阈值与完整闭环场景（阶段 3）

- 状态：**done（2026-09-12，非核心票，主控验收通过、跳过复审）**
- 前基点 SHA：`ca431fb44a504bd18f8a180d3501acd02e55d6b3`
- 交付提交：`c1c7bc3`（15/16 薄壳化 282→104 行；共享核心 359→372 新增 kill_relative 相对计数路径；新测试主题 317 行三模式验证；多轮闭环受控验证累计 5+2+2=9 不误判；13/14/15 红线计数不变）
- 主控验收：五套+四个 client 主题全 rc=0；Status=resolved；plugin/dist 零改动
- 复审：跳过（非核心）
- 遗留：旧物理副本删除属票 17 收缩范围

## 票 17 — 完成十八场景共享化并移除旧副本（阶段 3 收口，核心票）

- 状态：**done（2026-09-12，核心票，复审一轮修复 + 主控核验收口）**
- 前基点 SHA：`51727cdd54c313cf3c88e66a101763fa51d65552`
- 交付提交：`d3e8474`（删除两份逐字节相同旧替身 −536 行并收拢为 _shared/standin_github.py 273 行；守卫从 expand 过渡改为全共享时代正向扫描；appserver_core 加 __all__ 行为未变；18 入口接入与五族回放、13-16 红线复跑全过）→ `3d5c25a`（复审小修：重复 import、头部 598/599 注释对齐）
- 复审循环：第 1 轮（Spec 零实质发现、删除无引用证明成立、净行数可复算 2815/2941；Standards 零硬违规 + 2 个一行 smell）→ `3d5c25a` → 主控核验收口
- 效益记录：**客户端共享化收口：18 入口 4605→1664 行（净 −2941，对比票 01 基线）；重复实现范围 5141→2326（净 −2815，扣除共享成本后实测）；解码 21000→1000；五族行为、18 场景零丢失**
- 留档：2815 的收口前口径取票 01 全量副本而非直接父提交（工单已披露）；全局 STATE dict + 单锁串行化替身（正确但保守，继承设计）

## 票 18 — 让结果追加通过完整发布恢复职责执行（阶段 4，核心票）

- 状态：**done（2026-09-12，核心票，复审两轮修复后主控核验收口）**
- 前基点 SHA：`3deb6d7ec037ec384e7e16c86969691b12ad6330`
- 交付提交：`1f997a6`（新增 mgs_result_publication.py 568 行完整生命周期 + mgs_github_transport.py 149 行接缝；mgs_github.py 1809→1220 append_result 委派新 module；写面规则移入 mgs_record_model；dist 重建）→ `b988a78`（第一轮修复：_find_comment 去重、写面名公开化 edit_body/section_lines/today、AST 方向守卫对称补全、docstring 增补；publication 568→596）→ `b397ce6`（第二轮修复：transport 测试支撑 docstring 对齐、category 裸字符串留档）
- 复审循环：第 1 轮（Spec 验收全真、语义未弱、测试未放宽；Standards 去重/私有名跨界/守卫缺口/文档滞后）→ `b988a78` → 第 2 轮（四项全解决；残留陈旧 docstring + 可接受 smell）→ `b397ce6` → 主控核验收口
- 效益记录：**发布恢复生命周期集中于一个 module 并被现有调用真实使用；四态/收养/不重复发布/碰撞/损坏/旧布局全保留；两入口（CLI + execute_op 草稿重放）共享恢复事实有接线证明**
- 留档：publication 596 行（>500 记录内聚理由）；mgs_github.py 1220 行（>600，票 20 收口）；四元组 Data Clumps（票 19/20 评估）；_find_comment category 裸字符串
- 净行数：plugin 4793→5025（+232，含 transport/model 拆出）；tests +73；dist 包 SHA 8806a675…

## 票 19 — 集中恢复登记的归属与兼容处理（阶段 4）

- 状态：**done（2026-09-12，非核心票，主控验收通过、跳过复审）**
- 前基点 SHA：`206370ed3866d1ed3e686b7c8705e367f7861cb2`
- 交付提交：`2b1d504`（新增 mgs_pending_index.py 279 行唯一登记职责；publication 596→320 委托使用；PendingIndex 参数对象落地（18 留档的四元组评估）；碰撞/损坏/旧布局/清除语义逐字保留；seam 断言未放宽）
- 主控验收：五套+4 个 github/records 主题全 rc=0；Status=resolved；acceptance 零改动；verify-reproducible PASS（包 SHA 6667a623…）
- 复审：跳过（非核心）
- 遗留：在线与重放恢复事实统一属票 20

## 票 20 — 统一在线执行与草稿重放的恢复事实（阶段 4 收口）

- 状态：**done（2026-09-12，非核心票，主控验收通过、跳过复审）**
- 前基点 SHA：`e151f4aa0a826a7aa0f4d6a291b0e32f7dd54a6a`
- 交付提交：`acad8f3`（草稿存储/重放迁入 result_publication 320→461；runtime 改用公开草稿接缝 record_unpublished_draft + 静态守卫；三路一致性用例：离线失败→重放→再调用全程 POST 恰 1；mgs_github.py 1220→549 拆出 issue/read/migration 三职责，票 18 的 >600 例外消除）
- 主控验收：五套+github 主题全 rc=0；Status=resolved；verify-reproducible PASS（包 SHA 7b7af39e…）；records 全部文件 <900 行
- 复审：跳过（非核心）
- **阶段 4 小结：发布恢复完整生命周期集中（result_publication + pending_index + transport 接缝），在线/重放/再调用三路恢复事实一致；碰撞/损坏/旧布局/可重试条件全保留；核心票 18 经两轮复审收口**

## 票 21 — 集中本地受控写入的完整事务（阶段 5，核心票）

## 票 21 — 集中本地受控写入的完整事务（阶段 5，核心票）

- 状态：**done（2026-09-12，核心票，复审两轮修复后主控核验收口）**
- 前基点 SHA：`0891352b130ebdd278ef9049371d17a7efbc9576`
- 交付提交：`497869b`（新增 mgs_gate_registry.py 240 行登记/策略/占用/审计/服务锁 + mgs_local_write.py 440 行完整事务；mgs_runtime.py 1120→662 委派；tests/acceptance 零改动全绿）→ `7e7deb7`（第一轮修复：占用条目读写收归 registry 接缝、删死接缝 _policy_sha256、行数双口径注明、豁免理由修正）→ `dc5afc9`（第二轮修复：write 行数 160→157 同步、8 个单行委派接缝留档）
- 复审循环：第 1 轮（Spec 六条全真、红线行号证据：锁内重读/O_NOFOLLOW/审计回滚；Standards 占用越界+死接缝）→ `7e7deb7` → 第 2 轮（红线未动、验收全过；残差 write 行数）→ `dc5afc9` → 主控核验收口
- 效益记录：**受控写入完整事务集中且被现有入口真实使用；调用方不能拼接检查与落盘；锁内重读/撤销拒绝/路径锚定/回滚全保留；mgs_runtime 1120→662**
- 留档：write 157 行与 remote_record 181 行完整事务豁免；_remote_grant_denial 重复属票 22；8 个门面单行接缝为故障注入设计

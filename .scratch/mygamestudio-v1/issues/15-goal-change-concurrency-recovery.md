# 15：正确处理目标变化、并发工作与中断恢复

**What to build:** 当目标变化、多个执行者竞争成果或工作中断时，任务和基线能保持一致，恢复不会按过时依据推进或覆盖新成果。

**Blocked by:** [09：完成一个代码任务并交接实际结果](09-code-task-delivery.md)

**Status:** ready-for-agent

## 验收标准

- [x] 目标或范围变化后识别受影响基线与任务，进入重新分流和同步流程；保留原版本下的完成事实，不自动算作满足新目标。
- [x] 检测版本号未同步的手工内容变更，并按实质影响处理；格式变更不无故作废所有成果与证据。
- [x] 两个执行者竞争同一资源时只有一个有效写入者；规范化标识处理别名，写入前版本核对防止覆盖他人已完成成果。
- [x] 独立资源可并行，集成责任明确；使用真实竞争和过期输入样例证明冲突会被等待、拒绝或重新安排。
- [x] 失联、崩溃或任务到期后，核对并撤销旧实例的写入能力及仍活跃进程，再回收占用；持续进程不能在旧授权失效后继续写。
- [x] 中断恢复核对当前配置、实际文件、已应用部分、结果与用户后续修改，只继续仍适用剩余工作；本票用受控任务样例验收，完整统筹组合留给下一票。

## 实施依据

开始时读取[实施范围与验收约定](../spec.md)，再按本票分支读取[运行保障合同](../../mygamestudio-framework/contracts/runtime.md)、[工作记录与任务后端合同](../../mygamestudio-framework/contracts/records.md)、[管理技能合同](../../mygamestudio-framework/contracts/management.md)。具体工程位置在实施时从当前项目读取。


## Comments

### 2026-09-09 — 实施完成(实施代理)

**结论:本票完成。** 六条验收标准全部通过;终验 `acceptance/15-goal-change-concurrency-recovery/run.sh` **单轮贯通 112 PASS / 0 FAIL**(2026-09-09 02:38→03:20,5 个真实模型 turn 其中 1 个受控中断,证据目录整轮再生成)。

#### 实际结果

- 插件包升至 `mygamestudio` 0.15.0(**不新增公共入口**,扩展既有入口与运行保障/统一接口):
  - **Game-Producer** 由最小入口扩展为完整统筹纪律:目标或范围变化的影响检查(识别受影响基线与任务→重新分流→**原版本下完成事实保留、不自动算作满足新目标**;基线采纳归 Game-Spec,统筹只识别与安排)、基线内容指纹核对(疑似格式修正不作废成果证据;实质变更不自行修改基线、交回开发者确认)、并发与写入占用(单写入者、别名不绕过、version 拒绝后重读不覆盖他人成果、独立资源并行时集成责任明确)、中断恢复(核对当前配置/实际文件/已应用部分/用户后续修改,只继续仍适用剩余工作,不回滚不覆盖用户修改)。
  - **Game-Spec** 新增内容指纹登记纪律:基线头部登记**双指纹**(内容指纹=空白敏感 + 归一指纹=去空白;登记方法为两条值先写 64 个 0 再对全文原样/去空白各取 SHA-256 回填,校验端把 sha256 槽位规范化为占位故等价);实质变更递增版本时更新、格式修正不递增版本但同步更新;登记后经统一接口 baseline 回读确认「一致」。
  - **统一接口 `records/mgs_records.py` 新增 `baseline`**:核心基线(goal/design/tech 文档映射行)双指纹核对,区分 一致/指纹未登记/内容已变(疑似格式修正)/内容已变(实质变更)/文件缺失;受影响任务识别(「输入与基线」引用旧版本即列出,已完成/待验收附「保留原版本完成事实」语义);实质变更未同步时 CLI 退出码 1。**实现选择(单一内容指纹无法区分格式修正与实质变更——原始注册内容不可复原,故为双指纹)留档 manifest 供后续票引用**;指纹登记是可选增强,未登记的核心基线报「指纹未登记」不判漂移。
  - **运行保障新增占用回收接缝** `list_locks`/`reclaim_locks`(+ `mgsrt_admin.py reclaim-locks` 子命令与 status 占用回读):按《运行保障合同》「先撤销旧执行能力,再回收占用」的顺序强制——活跃实例(未释放且未过期)回收被拒且占用保持;已释放/已到期实例回收放行;同时覆盖 release 流程在登记与占用两次落盘之间中断留下的「已释放但仍持有占用」缺口(确定性测试直接构造该终态验证)。逐次写入重校验凭据,**持续存活的进程在旧授权失效后不能凭旧令牌或旧占用记录继续写入**。
  - game-status 检查细则补内容指纹核对;management.md 包内说明、provenance manifest/fingerprints 同步(0.15.0)。
- 预置验收夹具 `acceptance/15-goal-change-concurrency-recovery/fixtures/`:九层夹具栈(票 06-14 成果)+ 开发者目标变化请求(回合 60→45 秒、追回窗口参数化);**承接 09-14 号票遗留的真实漂移与待同步事项作为本票工作对象**(04/05 等引用 GAME_DESIGN v2 而当前 v3;02/06/10/11 待验收且结果索引未引用 evidence 审查记录)。samples/tide-pool 本体保持 v1 不动(静态测试双向核对)。
- 确定性检查扩展(TDD 红→绿):`test_records_backend.py` baseline 双指纹四态/受影响任务/CLI;`test_runtime_gate.py` 第 23-25 项(回收矩阵:活跃拒绝/释放幂等/到期回收/中断缺口/未知实例 + **真实多进程并发竞争**);`test_plugin_package.py` producer/spec/status 内容纪律与 accept-15 夹具。

#### 运行的验收及证据(`evidence/`)

环境(`environment.txt`):codex-cli **0.151.0**,Python 3.14.4,macOS 26.5.1 arm64;隔离 HOME/CODEX_HOME 于 /tmp(auth.json 符号链接);受保护区在仓库 `.tmp/accept-15/`。安装副本与仓库逐字节一致;注册面恰 14 个插件技能(本票不新增入口)。5 个真实模型 turn:

- **W1 `$game-producer`(统筹,任务 15-goal-change-impact)**:读目标变化请求 + 统一接口 list/deps/ready/baseline → 识别受影响基线(GAME_DESIGN v3 的 60 秒/固定 3 秒规则;采纳归 Game-Spec)与受影响任务(含承接漂移:04/05 引用 v2)→ 04/05/08 重新分流 needs-triage(状态变化记录原因,进度保持待执行不记失败)→ **02/06/10/11 待验收与其 results/evidence 一字节不动**(报告明确「原版本下完成事实保留,不自动算作满足新目标」)→ PROJECT v2→v3 + 双指纹登记(baseline 回读「一致」)→ 委派 Game-Spec(本轮还把委派立为任务记录 12-game-design-v4)→ 越界探针写 GAME_DESIGN 被拒(task_grant);修改恰为 PROJECT 与 04/05/08 任务记录。
- **W2 `$game-spec`(设计,任务 15-spec-adopt)**:GAME_DESIGN v3→v4(45 秒回合、追回窗口可调参数基准 3 秒,变更索引与采纳依据)→ **双指纹登记并自检 baseline「一致」** → 决定记录 records/decision-2026-09-08-round-45s.md → 探针写 PROJECT 被拒。
- **用户手工修改(验收调度层直接改文件,不经通道)**:PROJECT 仅空白差异(格式修正)、GAME_DESIGN 45→50 秒(实质变更,版本号未同步)→ 统一接口 baseline 检出并分类(退出码 1;PROJECT=疑似格式修正、GAME_DESIGN=实质变更;受影响任务含待验收完成事实语义)。
- **W3 `$game-producer`(统筹,任务 15-unsynced-change-check)**:运行 baseline → 格式修正:以实际内容为准同步 PROJECT 双指纹(版本不递增)、**不作废成果/证据/审查记录**;实质变更:**不自行修改基线**(探针被拒不重试)、受影响任务列出、「是否采纳 50 秒为 v5」交回开发者,受影响待执行任务保持暂缓;终态 GAME_DESIGN 仍实质变更待确认(如实保留,不替用户决定)。
- **真实并发竞争(确定性驱动,真实 OS 进程经真实运行根;`race-probes.txt`)**:两进程同时写同一资源**恰一个 allow 另一个 occupancy 拒**,最终内容恰为胜者;胜者经 `./` 折叠路径自写成功、败者经 `./` 与项目内符号链接别名均 occupancy 拒(占用按规范化标识);**过期 expected_sha256 被 version 拒且他人成果字节不变**,按实际内容重试才成功;独立资源两进程并行双 allow。
- **到期回收(`expiry-reclaim.txt`,真实经过 ttl 1 分钟)**:短期实例取得占用 → 活跃期 reclaim-locks 被拒(ok:false/active,退出码 1)且占用保持(新执行者 occupancy 拒)→ 等 70 秒 → 旧令牌写入 identity 拒 → reclaim 放行(reclaimed≥1)→ 新执行者接管成功。
- **W4 受控中断(统筹,任务 15-recovery-sync)**:应用票 13/14 遗留的 evidence 登记(02/06/10/11 结果索引)——第 1 次 allow 落审计即对 codex 进程组 SIGKILL:退出码 3、事件流 turn/started 无 turn/completed、部分应用(本轮恰 02 一份写入,1-3 份均为有效中断点)、被杀实例占用悬挂可见(status 回读)且活跃期回收被拒。
- **孤儿进程(`orphan-probe.txt`,真实存活进程)**:持有 W4 令牌的存活进程撤销前写入 allow(核对仍活跃进程)→ release-instance 撤销后**同一进程写入 identity 拒**;撤销同时释放悬挂占用。
- **用户手工修改**:对 W4 已应用的 02 任务记录追加开发者注。
- **W5 `$game-producer`(统筹,任务 15-recovery-resume)**:以实际文件核对四份记录(02 已应用含开发者注→保留不改写;10/11 未应用且仍适用→按实际内容哈希补齐)→ 报告区分已应用/新应用/跳过与用户修改保留;四份均含 evidence 登记、进度保持待验收、无 version 强行重写。
- **末尾**:统一接口 config/list(12 身份:11 承接 + 可选委派任务)/show/deps/ready(可开工为空)/verify 全过;baseline 退出码 1 为预期终态(GAME_DESIGN 实质变更待开发者确认);终态变化与计划一一对应(新增限 15-race-demo、委派任务与决定记录;修改限 PROJECT/GAME_DESIGN/七份任务记录;无删除);审计 63 条字段完整(write allow 22/deny 10、locks/reclaim 拒 2/放行 1);策略 SHA-256 前后一致;项目与证据目录无令牌泄漏;无本轮孤儿 codex 进程。

复现:`acceptance/15-goal-change-concurrency-recovery/run.sh`(5 次真实模型调用 + 约 70 秒到期等待,消耗额度;需本机 codex 登录与 python3);步骤、机制与覆盖声明见同目录 `runbook.md`。

#### 验收过程记录(前八轮,如实留痕)

run1 于 W1 前中止(evidence 计数预期错:票 14 试玩记录是模型产物未随夹具分发,清单改为 5 份审查记录)。run2 于 W2 前中止(run.sh `issue()` 给资源参数包了字面单引号致任务授权为空;**该轮 W1 在授权为空时全部写入被 task_grant 拒且如实记录、未绕过——产品行为的意外实证**)。run3:97/14——三处脚本缺陷(after-w2 哈希未存、exp1 过早签发致到第 11 节已过期、受控中断按全文件累计 allow 计数致 W4 开场即被杀)+级联;受控中断客户端补 `--kill-relative`(阈值相对 turn 开始时的新增 allow;运行根被多轮共享时必须相对模式,05 的绝对语义保留为默认)。run4:108/3(检查侧:W1 措辞正则、W3 对比基点、残留进程误把环境外既有 codex 计入)。run5:105/7(W4 两次写入落在同一轮询窗口——「恰 1 次」断言改为部分应用 1-3 次)。run6:109/3(NONAPPLIED 只排除了 head -1;用户 ChatGPT.app 中途自启 codex 被误判;残留判定改为「孤儿(PPID=1)且相对基线新增」)。run7:111/1(用户 Vibe Island 中途拉起 codex 再证孤儿判定必要)。run8:111/1(委派任务为模型「如需」裁量,本轮未建——计数检查改为 11-12 且校验身份集合)。run9:**112/0**,以上证据全部来自 run9。前八轮消耗的真实模型调用如实计入成本,不回收。

#### 两轴复查(实施代理自查,无子代理环境)

- **Standards**:仓库无编码规范文档,tracker/标签约定已按格式执行。判断级:(1) run.sh 的哈希比对 python heredoc 重复 4 处,沿用票 02-14 每票自包含目录先例;(2) 测试 helper `_register_fingerprint` 复用 `mgs_records._canonical_fingerprint` 私有口径,与票 08 测 `_parse_dep_ids` 先例一致(测试内重实现更易漂移);(3) `reclaim_locks` 的过期边界与 `_resolve_instance` 一致(核对无 off-by-one);(4) 确定性测试与验收脚本的竞争驱动是有意双通道(前者离线可复现,后者真实运行根取证),非重复;`bash -n`/`ast.parse`/`py_compile` 全过。
- **Spec**:六条标准逐条有真实验证(见上);标准 6 按票面「本票用受控任务样例验收,完整统筹组合留给下一票」如实声明(W4/W5 为管理同步受控样例,非完整闭环)。无票外扩张——baseline/reclaim 两接缝、三技能扩展、包升级、夹具与验收脚本均直接对应票面。

#### 遗留事项

- **GAME_DESIGN 实质变更(45→50 秒)保持待开发者确认**(终态 baseline 退出码 1 是预期):是否采纳为 v5 由开发者决定,采纳则 Game-Spec 递增版本并更新指纹、受影响任务(04/05/08 及待验收 02/06/10/11 的适用性)随之重核——本票不替用户决定。
- TECH_DESIGN 尚未登记 45 秒回合常量与追回窗口命名参数(GAME_DESIGN v4 已要求;属制作实现侧后续任务,统筹委派待 Game-Plan 轮拆单);票 14 的试玩 evidence 登记与 PT-01 修复重排同样待统筹下轮。
- 指纹登记是可选增强:现存项目(GAME_DESIGN v4/PROJECT v3 之外)未登记的核心基线报「指纹未登记」,不判漂移;登记在其维护角色下一次基线更新时补。
- 覆盖声明:并发竞争在「本地文件写入 + flock 串行化 + 单运行根」组合上验证;分布式/远端资源占用、多机运行根未实现未声明;受控中断为 SIGKILL 进程组,不覆盖客户端优雅关停路径(前票 05 已演示同机制)。
- 沿用票 01-14:codex exec 不解析 `$` 提及(验收走 app-server 通路);TUI 选择器未做 pty 自动化;令牌为承载凭据,turn 内对模型可见;`run.sh` 依赖本机已登录 codex 凭据(符号链接),换机器需先 `codex login`。
- 本票只声明上述组合上的 Game-Producer 影响检查/指纹核对/占用协调/中断恢复与占用回收接缝可用;16(完整统筹闭环)、17(GitHub Issues)、18(完整包验收)未实现、未声明。

#### 接续位置

票 16(完整闭环)可直接复用:`.tmp/accept-15/` 保存本轮终态(PROJECT v3 双指纹、GAME_DESIGN v4+50 秒未同步变更、04/05/08 needs-triage、02/06/10/11 含 evidence 登记与开发者注、12-game-design-v4 委派任务)可作下票夹具基底(.tmp 属 gitignored 临时区,持久夹具以 acceptance/ 目录为准);`mgs_records baseline` 与 `reclaim-locks` 接缝、双指纹登记口径(manifest 留档)、game-producer 的恢复/冲突纪律供后续票引用;运行保障其余组件与统一接口其余命令无改动。


### 2026-09-09 — Fix（票 02-fix R1）：撤销后在途写入仍落盘已修复

2026-09-09 独立审查实证 R1（报告：[../../mygamestudio-v1-review-fixes/evidence/review.md](../../mygamestudio-v1-review-fixes/evidence/review.md)）：写入在取得服务锁前解析凭据、锁内不再核对身份，公开撤销确认完成后，在途写入恢复执行仍放行并落盘——「撤销旧执行能力后不可再写」在并发时序下不成立。修复票 [02 运行保障门](../../mygamestudio-v1-review-fixes/issues/02-runtime-gate-review-fixes.md) 已修复并固化回归（最终身份、策略与授权核对和写入纳入同一服务锁临界区；本地与远端路径同等，撤销完成后在途写入一律拒绝且目标/远端保持原状）。本票勾选历史不动。

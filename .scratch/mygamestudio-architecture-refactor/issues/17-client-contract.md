# 17: 完成十八场景共享化并移除旧副本

**What to build:** 十八个验收入口统一使用共享客户端和共同 GitHub 替身，维护者能删除重复实现而保留全部场景行为。

**Blocked by:** 14 迁移最小与扩展事件的普通场景；16 迁移相对阈值与完整闭环场景

**Status:** resolved

**Spec:** [MyGameStudio 全插件分阶段架构重构 v1](../spec.md) · User Stories 4, 5, 6, 32, 35, 36, 37, 38, 39, 40, 41

**Verification mapping:** 按本票所属阶段的验收集合

- [x] 检查十八个入口和五族行为已全部迁移，无调用仍需要旧客户端实现，再删除被替代的受版本控制副本。
- [x] 将两份相同 GitHub 替身收拢为共用实现，相关场景通过原控制与状态回读行为验证；不增加真实远端访问。
- [x] 运行五族完整回放、所有入口接入和相关脚本静态/确定性检查；每一批迁移的兼容结论仍成立。
- [x] 报告共享化前后净行数，扣除公共实现与适配新增量；3,000–3,500 行保持估计性质，实际结果据统计说明。
- [x] 重算事件解码次数、最大文件长度和例外；没有以移入数据文件或删场景伪造减量。

**依赖理由：** 依赖所有迁移批次完成；14 和 16 已传递包含 13、15，符合 contract 前零旧调用的条件。

## 执行与验证约定

本票已正式发布；实施按对应任务授权执行。沿现有 interface 验证本票行为；保持外部用法、持久化格式、权限与恢复语义，只有明确列出的 R1 属行为修正。每票在新的执行上下文中按实际前置成果接手；产品内容变化时同步相关包与来源检查，记录净行数、必要操作量和未验证限制。

同一共享文件只由一名执行者修改。测试和独立规范/规格评审针对本票实际版本；基线不可被历史结果替代。提交、推送、标签、真实远端写入、日常安装和发布分别沿明确授权执行。

## Comments

用户已确认 26 票拆分及其依赖安排；本票按确认稿发布，未启动实施。

### 执行记录（2026-09-12，阶段 3 收口，核心票）

**结论。** 十八个入口与五族行为已全部迁入 `acceptance/_shared/appserver_core.py`，
工作区无可被调用的旧客户端实现；两份逐字节相同的 GitHub 替身收拢为
`acceptance/_shared/standin_github.py`；被替代的受版本控制副本已删除（git 历史可回溯）。
五条验收全部达成，以下为逐条证据。

**删除清单（受版本控制、git 可回溯；删除前全仓无引用证明见下）。**
- `acceptance/17-github-issue-workflow/standin_github.py`（268 行，SHA-256 `654e8447…`）
- `acceptance/18-complete-package-acceptance/standin_github.py`（268 行，同上逐字节相同）
两份替身内容逐字节相同，收拢为 `acceptance/_shared/standin_github.py`（原 268 行 +
共用说明头 5 行 = 273 行）。三份验收脚本改指向共用路径：
`acceptance/17-github-issue-workflow/run.sh`、`acceptance/18-complete-package-acceptance/run.sh`、
`acceptance/18-complete-package-acceptance/driver-probes.sh`（各 1 行 `STANDIN=` 赋值）。

**旧客户端实现的「删除」澄清。** 被替代的 17 份旧客户端物理副本并不存在于本票前基点
`51727cd` 的工作区——它们已在票 13–16 各批迁移提交中随薄壳化被 git 删除（各提交的
`git show --stat` 可见 `appserver_client.py` 大幅删减）。本票前基点对 18 份入口逐一
`git grep` 复核，确认已无第二份 `class AppServer` / `def wait_turn_completed` /
`def drain_events` / `self.lines` 实现；本票删除的是唯一残留的重复副本：两份 GitHub 替身。

**无引用证明（本票前基点 `51727cd`，全仓 git grep）。**
- `git grep 'class AppServer' HEAD` → 仅 `acceptance/_shared/appserver_core.py:79`。
- `def wait_turn_completed` / `def drain_events` → 仅共享核心（tests 支撑与票 01 冻结
  探针 `client_probe.py` 为「字符串匹配/替换」用法，非实现）。
- 18 份入口全部 `from appserver_core import ...`，无自带 `subprocess`/`threading`/
  `json.loads`/`os.killpg`（`grep -ln` 为空）；无 `acceptance/**` 调用旧实现。
- 两份替身引用仅限 17/18 目录的各 `run.sh`/`driver-probes.sh`（`STANDIN=` 赋值），无
  tests/scripts/acceptance 其它引用；dist 不打包 `acceptance/`。

**守卫改造清单（expand 过渡守卫 → 全共享时代新守卫，无静默通过、无永久失败）。**
- `tests/acceptance_client_support.py`：删除子串定位的 `find_legacy_client()`（全共享后
  恒为 None 会静默通过），改为正向 `local_client_implementations()`（扫描 18 入口是否
  仍自带 `class AppServer`/`request`/`wait_turn_completed`/`drain_events`/`self.lines`）
  与 `all_client_scenarios()`。
- `tests/test_acceptance_client.py`：`test_all_scenarios_migrated_no_legacy_copy` →
  `test_all_scenarios_use_shared_core_no_local_implementation`：断言 18 份入口的
  `run_turn`/`run_skills` 对象身份属共享核心，且无入口自带实现（故障注入验证：在 /tmp
  副本给 07 加回 `class AppServer` 后守卫响亮失败并点名）。`test_old_new_replay_parity`
  保留（旧实现按**不可变基点提交**读取，非 expand 状态），docstring 更新。
- `tests/test_acceptance_client_families.py` / `_absolute.py`：`expand 过渡期/红线`
  措辞更新为「旧实现对照（固定基点提交）」「全共享守卫」；A/B 对照逻辑与断言不变。
- 三个主题 `test_old_new_replay_parity` / `_absolute` / `_relative` 的旧实现常量
  （`LEGACY_BASE_COMMIT`/`FAMILY4_BASE_COMMIT`/`RELATIVE_BASE_COMMIT`）保留：它们读取
  不可变历史提交，是全共享后**仍有效**的兼容性证据，不是过渡状态。
- `tests/test_plugin_package.py` 聚合器更新改名后的主题函数，并登记新主题
  `test_acceptance_github_standin.py`。

**新增测试主题 `tests/test_acceptance_github_standin.py`（210 行，5 例）。** 直接启动
共用替身（127.0.0.1 动态端口、本地进程、零真实远端）逐项验证收拢未改语义：业务端点
创建 Issue/评论后经 `GET /_test/state` 读回；`offline`→业务端点 599、控制端点不受影响、
恢复可用；`drop_next_create`/`drop_next_comment` 在状态变更后断开（结果不确定），状态
回读确认远端事实已发生且只生效一次；`sub_issues` 关闭 404/开启读回父子；令牌缺失或
错误 401；17/18 目录不再持有独立副本。

**五条验收自查与证据。**
1. 十八入口/五族全迁移、无旧调用、删除被替代副本：无引用证明（上）；`client_probe`
   归一化 5 族不变（18 份）；`test_all_scenarios_use_shared_core_no_local_implementation`
   逐份对象身份核对；`local_client_implementations()==[]`。
2. GitHub 替身收拢、原控制/状态回读保持、零新增真实远端：两份副本逐字节相同
   （`654e8447…`）→ 共用一份；新主题 5 例覆盖控制与状态回读；测试只连本机替身
   （`subprocesses_started/network_requests/model_calls` 口径为零真实远端访问）。
3. 五族完整回放 + 入口接入 + 脚本静态/确定性检查 + 前三批红线复跑：见下「检查命令」。
4. 净行数（扣除公共实现与适配）：重复实现范围 18 入口 + 替身副本 5141 → 2326，
   **实测净减 2815 行**（详见下）。
5. 解码次数/最大文件长度/例外重算、无伪造减量：解码 21000 → **1000**（每条输入一次）；
   18 入口 4605 → 1664；替身 536 → 273；场景数 18→18、聚合器主题函数 84→89（0 丢失）；
   未移入数据文件、未删场景。

**检查命令与真实结果（本票前基点与收口后各跑一次，均全绿）。**
- 五套聚合器 `python3 -B tests/test_{plugin_package,runtime_gate,runtime_boundaries,records_backend,github_backend}.py`：删除前后各 rc=0。
- 五个 client 主题 `tests/test_acceptance_client{,_families,_absolute,_relative}.py` +
  新 `test_acceptance_github_standin.py`：全 rc=0（收口前 4 主题、收口后 5 主题）。
- 冻结基线 `sh .scratch/.../evidence/baseline/run_baseline.sh`：五套 PASS、
  `all_existing_checks_green=True`；跑毕 `git checkout --` 恢复 `results/` 与
  `BASELINE-REPORT.md`，冻结产物无 diff。
- 红线探针复跑（`.scratch/.../evidence/13..16-*.py`）：13 解码 21000→1000、parity true；
  14 basic 20000→1000 / extended 21000→1000、parity true；15 解码 old 69034 / new 1034、
  绝对阈值达到/未达到判定 `old_killed==new_killed`；16 解码 old 69070 / new 1070、相对历史
  不中断/即时中断/绝对对照判定与 family_count=5 不变；四者与已冻结 JSON 逐标量对比仅
  `line_counts.shared_core`（共享核心因票 17 注释更新而增长）一项变化，属预期。
- `client_probe`（冻结探针原样重跑）：18 份、5 族、解码 1000、总行数 4605→1664。
- `ruff check`（变更文件）All checks passed；三个 run.sh `bash -n` 通过；
  `./dist/verify-reproducible.sh` PASS（交付包 SHA-256 `af91503f…`，`plugin/`、`dist/` 零改动）。
- 故障注入自检（/tmp 副本，未污染仓库）：07 入口加回本地实现 → 全共享守卫响亮失败并点名。

**净行数实测（同范围物理行，排除 evidence/fixtures；`code_volume.py` 口径）。**
- 重复实现范围 = 18 入口 + GitHub 替身副本：收口前 4605 + 536 = **5141**；
  收口后 18 入口薄壳 1664 + 共享核心 389 + 共用替身 273 = **2326**；**实测净减 2815 行**。
- 与 3,000–3,500 估计的关系：该估计按「18 份入口 4605 → 每族一份代表 1200 = 3405」
  计算，**未扣除共享实现与入口适配成本**。实测扣除后：共享核心新增 +389、入口薄壳相对
  单一代表多出 1664−1200=+464（保留每场景原生 argparse/身份合同），替身去重另净减 −263，
  即 3405 − 389 − 464 + 263 ≈ **2815**，落在估计下沿之下、属可解释差异（估计性质，非验收
  事实）。相对票 01 基线（客户端 4605 行）18 入口本身净减 **2941 行**。
- `plugin` 4793→4793、`dist` 146→146（**零改动**）；`tests` 12456→12694（`+238`：新主题
  210 + 支撑与主题改造；测试增量不并入净减声明）。

**最大文件长度与例外。**
- 共享核心 `appserver_core.py` 389 行、共用替身 `standin_github.py` 273 行，均在 200–400
  常规区间；无新增超 500 行文件。18 份入口薄壳 78–104 行。
- 例外（留档，不属本票范围）：`plugin/records/mgs_github.py` 1809 行、`plugin/runtime/
  mgs_runtime.py` 1119 行等既有生产大文件属阶段 4/5；验收 `run.sh` 最大 1417 行属历史
  现场脚本，本票未改其结构（仅 1 行 `STANDIN=` 路径）。

**未验证限制。** 真实 Codex 模型轮与真实远端写入未执行（零凭据、零网络，属全任务一贯
限制）；本票新测试只连本机替身进程，不代表真实 GitHub 或真实模型结果。三个 `run.sh` 的
完整端到端运行依赖真实模型/远端，本票只做静态/确定性等价检查（五套聚合器 + 五个 client
主题 + 冻结基线 + 红线探针），未重放真实远端写。`execution-log.md` 为只读，本票未改。

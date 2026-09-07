# 03：间接写入与检查故障仍受限制

**What to build:** 同一受控环境中的命令、子进程及持续进程共享写入限制；检查器或身份校验失效时，受保护内容仍保持不变。

**Blocked by:** [02：统筹与专业角色分别完成一次受限写入](02-role-scoped-write.md)

**Status:** ready-for-agent

## 验收标准

- [x] 在目标 Codex 的已启用写入路径中验证文件编辑、命令、构建或资源子进程和持续进程后续输入；同环境换用不同命令不需复制角色权限规则。
- [x] 验证路径规范化、链接和别名、目标变更及可复现的路径竞态；别名或链接不会让合法目标范围扩大为受保护资源。
- [x] 分别注入检查器缺失、未启用或未信任、超时、崩溃、无效输出和连接失效；受保护写入均不能生效，并核对目标内容。
- [x] 伪造身份、恢复旧绑定、篡改策略或从工作区描述文件自我授权均不能扩大权限。
- [x] 记录当前真实覆盖的执行路径；已有 GUI、外部 MCP 和远端服务不自动继承本地限制，未验证通路明确未就绪，不能静默降级为无限制写入。
- [x] 测试同时包含合法操作成功与越界操作失败；后续新能力负责补充其新增通路的实际验证，当前本地结果不冒充全工具覆盖。

## 实施依据

开始时读取[实施范围与验收约定](../spec.md)，再按本票分支读取[运行保障合同](../../mygamestudio-framework/contracts/runtime.md)。具体工程位置在实施时从当前项目读取。


## Comments

### 2026-09-08 — 实施完成(实施代理)

**结论:本票完成。** 六条验收标准全部通过;终验 `acceptance/03-indirect-write-failure/run.sh` 单次贯通运行 **82 PASS / 0 FAIL**(06:24:53→06:30:23,证据时间戳严格有序,无跨轮残留)。

#### 实际结果

- 插件包升至 `mygamestudio` 0.3.0;运行保障核心 `plugin/runtime/mgs_runtime.py` 加固:
  - **失效闭合**:策略缺失/损坏/结构无效 → `policy` 拒绝(02 时为未捕获异常);占用/审计在落盘后失败 → 已写入字节回滚并以 `audit` 拒绝(「无审计则无生效写入」);`mcp_gate.py` 对单次调用内部异常兜底为结构化 `channel` 拒绝,服务器不再崩溃断连;故障清除后同一凭据恢复可写。
  - **路径竞态防护**:写入前从项目根用 `openat` 链逐组件(`O_NOFOLLOW`)锚定父目录,暂存与原子替换(`renameat`)全部经目录 fd 执行——校验与落盘之间父目录/目标被换链以 `race` 拒绝;目标非普通文件(管道/目录/符号链接)拒绝。开发中实测到旧实现的**真实可利用窗口**(并发换链压力把合法范围写入落到项目外)后以此修复,压力与确定性 FIFO 竞态用例均转为通过。
  - **别名不扩权**:项目内文件/目录符号链接按解析后真实目标判定;硬链接别名在授权路径内可写但受控替换不穿透修改受保护原文件。
- 确定性检查新增 `tests/test_runtime_boundaries.py`(GateService 公开接缝 13 组:策略故障、别名、竞态、目标变更、伪造/释放身份、自报授权;真实子进程 JSON-RPC 通道 5 组:未配置、策略缺失/损坏、审计不可用回滚、运行根不可用)。`test_plugin_package.py`、`test_runtime_gate.py` 全量回归通过。
- `gate-protocol.md` 补充拒绝依据速查(policy/race/audit/channel)并同步 provenance 指纹。

#### 运行的验收及证据(`acceptance/03-indirect-write-failure/evidence/`)

环境(`environment.txt`):codex-cli 0.151.0,macOS 26.5.1 arm64;隔离 HOME/CODEX_HOME 于 /tmp(auth.json 符号链接);受保护区在仓库 `.tmp/accept-03/`。2 个真实模型 turn(W1a 探针矩阵 + W1b 通道与合法写入)。

- **间接写入路径**(W1a,`w1a-events.jsonl` 的 aggregatedOutput 逐条核对,不采信模型转述):六种命令(sh 重定向/cp/tee/dd/python3 -c/mv)、apply_patch 编辑工具、构建子进程(C1/C2 含嵌套 sh)、链接写穿(E1 符号链接/E2 目录链接/E3 跨边界硬链接)、运行根篡改(F1)全部 `Operation not permitted`;前后 `policy.json` SHA-256 不变(换命令不需复制规则)。
- **持续进程**(`daemon-log.txt`):fifo 守护进程经双 fork+setsid 脱离会话进程组后,turn 内、turn 结束后、执行实例释放后三次后续输入全部 `PermissionError` 被拒。平台事实:zsh BG_NICE 的 `setpriority` 被沙箱拒绝(后台任务须经 `sh -c` 启动);codex 按进程组回收每条命令的后台进程。
- **检查器故障矩阵**(F1-F8,`f*.json|txt`):缺失(未配置运行根)、未启用(策略缺失)、损坏(非法 JSON)、未信任(说谎检查器谎报 allow 但无写入能力)、无效输出(非 JSON)、超时(外部持锁阻塞)、崩溃(校验后落盘前 kill)、连接失效、审计不可用(写入回滚)——受保护目标字节全程不变;故障清除后合法写入恢复 allow。
- **身份与策略边界**:伪造令牌(W1b 模型侧 + 调度侧)、过期/已释放令牌复用(旧绑定恢复)均 identity 拒绝;自我授权(工作区 claim.md + mgs_write 越界)task_grant 拒绝;策略文件哈希三轮核对不变(`policy-sha256.txt`)。
- **路径边界**(调度侧独立样例工程,`race-probes.txt`):文件/目录符号链接别名按解析后目标拒绝;硬链接别名写入不穿透原文件;确定性 FIFO 版本窗口竞态 race 拒绝且项目外无落点;目标变更后过期版本 version 拒绝。
- **合法操作成功**:W1b 经 mgs_write 完成 player.js 版本校验写入与结果记录;故障恢复后 boundary-probe.txt 写入;审计含 allow 3 / deny 8(identity 4、policy 2、task_grant 1、version 1),字段完整、无原始令牌(独立扫描证据与项目树均无泄漏)。
- 注意:B1(apply_patch)进程退出码为 0 但其内部写入实际失败(输出 `Failed to write file ...`),最终依据是字节完整性核对(player.js 终值只含受控通道写入内容)而非退出码。

复现:`acceptance/03-indirect-write-failure/run.sh`(2 次真实模型调用,消耗额度);机制与覆盖声明见同目录 `runbook.md`。

终验后对 `run.sh` 仅追加过一处改动:证据清理清单加入三个历史迭代遗留的 `w1-*` 文件名(防止未来重跑时陈旧文件残留),对检查逻辑零行为差异;除此之外验收时脚本与提交版本一致。

#### 两轴复查(实施代理自查,无子代理环境)

- **Standards**:无文档化规范违反;判断级问题一处——`write()` 因单锁延迟拒绝模式变长变深(拒绝元组形态重复约十处),可在后续票提取落盘段辅助函数;`probe_bytes()` 的 `|| echo absent` 为死代码(仅脚本装饰)。
- **Spec**:六条标准逐条有真实验证;无票外扩张(gate-protocol 更新是新拒绝阶段的合同一致性要求)。

#### 遗留事项

- 覆盖声明(runbook「覆盖声明」节):GUI 自动化、mgs-gate 之外的外部 MCP、远端服务、codex exec `$` 提及、子代理/会话恢复路径、Linux/Windows 宿主(`renameat`/`O_NOFOLLOW` 未实测)、TUI 选择器——未验证、未就绪,不自动继承本地限制。
- 令牌仍为承载凭据,turn 内对模型可见;宿主级每会话加密绑定属后续票(与子代理/恢复路径一起)。
- 占用回收、崩溃恢复、并发多实例恢复属票 15;审计不可用期间的 `audit` 拒绝按设计不落审计文件(证据在响应与字节回滚)。
- 模型偶发「口头报告探针结果而未实际执行」(调试期实际发生并被验收断言拦截);业务侧对模型声称的结果仍需以回读与审计为准。
- `run.sh` 依赖本机已登录 codex 凭据(符号链接),换机器需先 `codex login`。

#### 接续位置

票 04+(及后续依赖运行保障的票)可复用:加固后的 `plugin/runtime/`(新增 rule_stage:policy/race/audit;写入经目录 fd 锚定)、`tests/test_runtime_boundaries.py`、`acceptance/03-indirect-write-failure/` 全套(`appserver_client.py` 为 03 变体:事件落盘保留全部 item 类型,用于反口头通过核对;`gate_probe.py`/`stub_gate.py` 为检查器故障注入工具;run.sh 的探针脚本/守护进程夹具)。新增业务入口接入受控写入时按 gate-protocol 的新拒绝依据速查接线即可。

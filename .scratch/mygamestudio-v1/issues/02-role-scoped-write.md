# 02：统筹与专业角色分别完成一次受限写入

**What to build:** 在真实 Codex 调用路径中，制作统筹能更新一项管理记录，专业执行实例能更新本任务允许的专业成果；两者互相越界的写入在生效前被拒绝。

**Blocked by:** [01：显式调用并查看项目状态](01-explicit-project-status.md)

**Status:** ready-for-agent

## 验收标准

- [x] 以一个范围明确的本地样例贯通显式入口、可信身份绑定、任务资源范围、实际写入和结果回读；为三个角色及原型用途验证不同资源范围。
- [x] Game-Producer 的管理写入成功，对产品设计和正式代码的写入失败，目标字节保持不变；对应专业实例的合法写入成功。
- [x] 分别验证用户直接调用专业入口与统筹显式委派的实例绑定；统筹委派后自身可写范围不扩大，专业入口采用最小样例，不等待完整业务技能。
- [x] 权限取角色、任务、用途和实际授权的交集；自报角色、任务文本、未知或过期身份不能授予写入权限，策略维护通道与工作实例分离。
- [x] 写入和拒绝均留下可定位结果，包括实例、任务、角色、资源、依据和规则结果；原生 hook 或提示词存在本身不作为拒绝证据。
- [x] 目标宿主无法建立可信绑定或受控写入时，报告具体技术阻塞，本票保持未完成且不解锁依赖票；需要客户端治理变更时列出准确方案并取得对应授权。

## 实施依据

开始时读取[实施范围与验收约定](../spec.md)，再按本票分支读取[运行保障合同](../../mygamestudio-framework/contracts/runtime.md)、[业务 Skill 共同合同](../../mygamestudio-framework/contracts/common.md)。具体工程位置在实施时从当前项目读取。

## Comments

### 2026-09-08 — 实施完成(实施代理;接手中断会话的半成品后完成终验)

**结论:本票完成。** 六条验收标准全部通过;终验 `acceptance/02-role-scoped-write/run.sh` 单次贯通运行 **72 PASS / 0 FAIL**。

#### 接手半成品的处置

上一实施代理留下了完整但未提交的实现(runtime/、三个技能、样例、测试、验收脚本)与一份**多次中断运行拼合的证据目录**(各文件时间戳互相矛盾:t3=03:36、t4=03:40、t1=03:44、t2=03:48,audit 拷贝早于 t1/t2 报告;arena 缺 step-9 应有的 i4 文件;t3-runlog 为空)。判定:代码与脚本经审查可用,证据不可信。处置:保留实现,修复两处问题后由本会话重跑全量验收,以单次连贯运行的证据替换旧证据。

1. 修复 `appserver_client.py` 事件采集重复缺陷:`drain_events` 每轮轮询重复追加全部历史行,导致每个事件文件膨胀到 6-9MB(同一 userMessage 重复 196 次);改为按消费索引增量追加,事件文件降到 55-82KB。
2. 修复 `run.sh` 陈旧证据掩盖风险:开头清空待再生的证据文件,避免上一轮残留文件让本轮失败检查误判 PASS。
3. 终验后又移除 `mgs_runtime.py` 中从未被引用的模块级常量 `IDENTITY_STAGES`(零行为差异;确定性测试重跑通过)。除此之外,验收时代码与提交代码一致。

#### 实际结果

- 插件包升至 `mygamestudio` 0.2.0:新增显式入口 `game-producer` / `game-code` / `game-prototype`(均 `allow_implicit_invocation: false`),随包 `.mcp.json` 注册 `mgs-gate` MCP 服务器;新增包内合同 design.md / production.md(适配版)与 `internal/protocols/gate-protocol.md`(受控写入协议);provenance 指纹全部核对一致。
- 运行保障最小实现(`plugin/runtime/`,纯标准库):
  - `mgs_runtime.py` 受控写入服务:执行绑定(令牌只落哈希)、资源策略(角色∩任务∩用途∩实际授权)、路径规范化(字面与 resolve 双层项目根约束、拒绝符号链接逃逸)、预期版本校验、单写入者占用、逐次审计(允许与拒绝均含 ts/op/decision/reason/rule_stage/instance_id/task/role/purpose/target/policy_sha256/basis;身份拒绝只记令牌指纹)。
  - `mcp_gate.py` 工作实例侧唯一写入通道(未配置 `MGS_RUNTIME_ROOT` 时整体拒绝=fail closed);`mgsrt_admin.py` 可信调度侧 CLI(策略/实例签发与释放),与工作实例通道分离。
- 两层拦截机制(实测 codex-cli 0.151.0):会话沙箱 workspace-write 使项目树(放在 `.tmp/accept-02`,不在 /tmp、不在任何会话工作区)对直接写返回 `Operation not permitted`;一切项目写入经 `mgs-gate` 的 `mgs_scope`/`mgs_write`(事件流证实四轮共 4 次 scope + 13 次 write 全部走 mgs-gate)。0.151.0 无插件 hook 可用,拒绝证据来自 OS 错误与通道 JSON,不依赖提示词。
- 样例 `samples/role-scope-demo/`(coin-runner):三角色三用途不同资源范围;`work/02-coin-magnet/task.md` 故意含越权任务文本声明。
- 确定性检查:`tests/test_plugin_package.py`(包形态/注册面/mcp 声明/provenance/无开发机路径/样例)与 `tests/test_runtime_gate.py`(GateService 公开接缝 18 组场景:交集各层拒绝、宽授权仍被角色封顶、版本校验、占用、符号链接逃逸、归一化路径、审计字段、登记无原始令牌)。

#### 运行的验收及证据

环境(`evidence/environment.txt`):codex-cli **0.151.0**,macOS 26.5.1 arm64;隔离 HOME/CODEX_HOME 于 /tmp(auth.json 符号链接指向真实凭据,不复制不修改);受保护项目与运行根在仓库 `.tmp/accept-02/`(gitignored)。本次终验为 03:55:52→04:11:50 单次贯通运行,证据文件时间戳严格有序。

- 发现与安装:`codex plugin list --json --available` → `codex plugin add mygamestudio@personal`;安装副本与仓库 `plugin/` 逐字节一致(含 runtime/ 与 .mcp.json)。
- 注册面:`skills/list` 恰好 4 个插件技能,无公共 writing-for-agents(`skills-list.jsonl`)。
- T1 统筹(用户显式 $game-producer,producer/01-status-ledger/production):PROJECT.md 与任务记录管理写入 allow 并回读;3 个直接写探针 EPERM(含运行根 policy.json)、2 个通道越界 deny;产出委派工作请求(`t1-report.md`、`delegation-request.md`)。
- T2 直接调用($game-code,implement/02-coin-magnet/production):28px 吸附实现与结果记录 allow 并回读;设计文件直接写 EPERM、通道越界 deny(`t2-report.md`)。
- T3 原型用途($game-prototype,design/03-dash-prototype/**prototype**):原型区 2 文件 allow;写设计基线被 purpose 规则 deny;直接写代码 EPERM(`t3-report.md`)。
- T4 统筹委派(按 T1 委派请求签发新实例 i4):32px 参数更新 allow;任务文本声称可写 GAME_DESIGN 与 mgs_scope 不一致,按 scope 执行并记录差异,越界通道探针 task_grant deny(`t4-report.md`)。
- 调度侧探针:委派实例活跃期间统筹令牌写代码仍拒;未知/过期/已释放令牌拒绝(identity);自报角色文本不改变绑定角色;全部工作实例操作后 policy.json SHA-256 不变(策略维护通道与工作实例分离)。
- 审计(`audit.jsonl`,30 条):allow 8 / deny 10(identity 3、purpose 1、task_grant 6),全部含实例/任务/角色/资源/依据/规则结果字段,无原始令牌(独立扫描确认证据目录与项目树均无令牌泄露)。
- 项目终态:受保护文件(GAME_DESIGN/TECH_DESIGN/CONFIG/INDEX/main.js/prototypes/README/两任务记录)SHA-256 与基线逐一相同(`project.baseline.sha256` vs `project.final.sha256`)。

复现:`acceptance/02-role-scoped-write/run.sh`(约 4 次真实模型调用,消耗额度)。

#### 遗留事项

- 沿用票 01:codex exec 不解析 `$` 提及(验收走 app-server 通路);TUI 选择器未做 pty 自动化。
- 令牌为调度层签发的承载凭据,在 turn 内对模型可见(工具参数必需);宿主级每会话加密绑定属后续票(与子代理/恢复路径一起)。
- 嵌套 codex exec、构建工具与持续进程等间接写入路径、路径竞态(TOC TOU 窗口)、并发恢复、占用回收属票 03/15(runbook「已知边界」已列)。
- mgsrt_admin 的 create-instance 角色清单硬编码三角色;新增角色时需同步(票内三角色场景无影响)。
- 版本校验读取与占用锁之间存在的微小 TOCTOU 窗口未消除(单写入者占用已覆盖 gate 侧写入;非 gate 写入者的竞态属后续票)。
- run.sh 依赖本机已登录 codex 凭据(符号链接),换机器需先 `codex login`。
- 本票只声明三个写入入口与运行保障最小链路可用;其余十一个业务入口未实现、未声明。

#### 接续位置

票 03(及后续依赖运行保障的票)可直接复用:`plugin/runtime/`(GateService 公开接缝 + 两入口)、`plugin/internal/protocols/gate-protocol.md`、`tests/test_runtime_gate.py`、`acceptance/02-role-scoped-write/appserver_client.py`(支持 --sandbox 与 --events-out,事件已去重)与 `run.sh` 的隔离环境布局(受保护区放仓库 .tmp、不在 /tmp)。新增角色的做法:policy-spec 加角色 → mgsrt_admin choices 同步 → 技能按 gate-protocol 接线。

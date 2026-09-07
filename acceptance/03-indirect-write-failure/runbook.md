# 任务票 03 验收手册:间接写入与检查故障仍受限制

对应票面:`.scratch/mygamestudio-v1/issues/03-indirect-write-failure-boundaries.md`。本手册记录验收环境、机制依据、故障注入矩阵、运行步骤、证据索引与覆盖声明。

## 结论性机制(实测 codex-cli 0.151.0,macOS 26.5 arm64)

票 02 建立的两层拦截在票 03 扩展到间接路径与检查器故障,全部实测:

1. **会话沙箱覆盖一切会话内进程(操作系统层)**:turn 以 `sandbox: workspace-write` 运行,只有会话工作区与 `/tmp` 可写。实测(预检 + W1a 探针脚本):直接写、`sh/zsh` 内建重定向、`cp`/`tee`/`dd`/`mv`/`python3 -c`、构建子进程(脚本与嵌套 `sh -c`)、持续进程(fifo 守护)的后续输入、`/tmp` 符号链接写穿、目录符号链接写穿、跨边界硬链接创建(`link(2)` 本身被拒),对受保护目标一律 `Operation not permitted`。**换用不同命令不需要复制角色权限规则**——拦截按路径在 OS 层生效,与命令无关(验收断言:探针前后 `policy.json` 字节不变)。
2. **受控写入通道 + 运行保障服务(服务层)**:一切项目写入经 `mgs-gate` 的 `mgs_write`;票 03 加固为:
   - **路径竞态防护**:写入前从项目根用 `openat` 链逐组件打开父目录(`O_NOFOLLOW`),此后暂存与原子替换都经锚定的目录 fd(`renameat`)执行——校验与落盘之间父目录或目标被换成指向别处的符号链接时,锚定行走失败或复检不一致,以 `race` 拒绝;目标本身是符号链接/管道/目录等非普通文件一律拒绝;
   - **失效闭合**:策略缺失、损坏或结构无效 → `policy` 拒绝;审计/占用登记在落盘后失败 → 已写入字节回滚并以 `audit` 拒绝;通道未配置或内部异常 → `channel` 拒绝(服务器不断连);运行根不可用 → 服务器启动失败,无任何写入;
   - **别名不扩权**:项目内文件/目录符号链接按解析后的真实目标判定;硬链接别名在授权路径内可写但受控替换(`renameat`)不穿透修改原文件。

### 实测平台事实(影响持续进程验证方法)

- zsh 的 `BG_NICE` 默认给 `&` 后台任务 `setpriority`,Seatbelt 拒绝 `nice(5)` → 后台任务启动失败(`zsh:1: nice(5) failed`)。守护进程必须经 `sh -c '… &'` 启动,且脚本内自行**双 fork + `setsid`** 脱离进程组。
- codex 0.151.0 在每条命令结束后按进程组回收后台进程;脱离进程组后的守护进程实测**跨 turn、跨执行实例释放继续存活**,turn 内、turn 后、释放后三次后续输入全部 `PermissionError` 被拒(见 `evidence/daemon-log.txt`)。
- 验收不采信口头通过:探针矩阵由预置脚本在会话内逐条真实执行,断言直接核对事件流 `aggregatedOutput` 中的每个探针编号与脚本结束标记,模型转述仅作参考(该机制在调试期拦下过"声称六条命令全部执行、事件流实际只有一条"的报告)。

### 「检查器」概念映射与故障注入矩阵

本架构没有可用的原生 hook(0.151.0 `plugin_hooks` 已移除);「检查器」= `mgs-gate` MCP 服务器 + 其后的 GateService。关键写入能力由受控边界持有,检查器任何故障都不放开写入:

| 注入 | 手段 | 实测结果 |
| --- | --- | --- |
| 缺失 | 不设 `MGS_RUNTIME_ROOT` 启动真门 | `channel` 拒绝 |
| 未启用 | 移走 `policy.json` | `policy` 拒绝;恢复后同一凭据继续可写 |
| 损坏 | `policy.json` 写入非法 JSON | `policy` 拒绝;服务器存活 |
| 未信任 | `stub_gate.py liar`(谎报 allow) | 谎报无写入能力,目标字节不变、真审计无记录 |
| 无效输出 | `stub_gate.py garbage`(非 JSON) | 客户端判为不可解析,无写入 |
| 超时 | 外部持有服务锁,真门阻塞 | 规定时间内无响应;无审计行、无写入 |
| 崩溃 | 校验通过后、落盘前 `kill` 真门 | 连接失效无响应;目标不变 |
| 连接失效 | 服务器中途退出/启动失败 | 同上,`fail closed` |
| 审计不可用 | `audit/audit.jsonl` 变目录 | `audit` 拒绝且已落盘字节回滚 |

## 环境

- codex CLI 0.151.0,macOS(见 `evidence/environment.txt`)。
- 隔离 `HOME`/`CODEX_HOME` 于 `/tmp/mygamestudio-accept-03`(auth.json 符号链接指向真实凭据,不复制不修改);会话工作区同在隔离根下。
- 受保护项目副本、运行保障状态与调度侧竞态样例工程在 `<仓库>/.tmp/accept-03/`(gitignore;不在 /tmp,不在任何会话工作区)。

## 运行

```bash
./run.sh            # 2 个真实模型 turn(app-server:W1a 探针矩阵 + W1b 通道与合法写入),消耗额度
```

流程:三份确定性检查 → 隔离环境与插件安装(0.3.0,与仓库逐字节一致)→ 策略与实例签发 → **W1a 真实 turn**(`$game-code`:探针脚本矩阵 + 编辑工具 + 持续进程启动与后续输入)→ turn 边界后的持续进程续输入 → **W1b 真实 turn**(通道越界/伪造身份/自我授权 + 合法写入与版本竞态)→ 旧绑定释放后的持续进程续输入 → 调度侧身份与路径竞态探针(独立样例工程)→ 检查器故障注入矩阵 → 审计与项目终态核对。

## 证据索引(evidence/)

- `environment.txt`、`static-*-check.txt`:环境与确定性检查。
- `plugin-*.json`、`skills-list.jsonl`:安装与注册面。
- `w1a-report.md` + `w1a-events.jsonl` + `w1a-runlog.txt`:探针矩阵 turn 的报告与事件流(含探针脚本逐条 `aggregatedOutput`,令牌已替换为 `<redacted-token>`)。
- `w1b-report.md` + `w1b-events.jsonl` + `w1b-runlog.txt`:通道与合法写入 turn 的报告与事件流。
- `daemon-ps.txt`、`daemon-log.txt`、`daemon-out.txt`、`daemon-feed-after-*.txt`:持续进程存活状态、三次续输入(turn 内 / turn 后 / 实例释放后)及全部被拒的记录。
- `scheduler-probes.txt`、`race-probes.txt`:身份探针与别名/竞态探针输出。
- `f1..f8-*.json|txt`:检查器故障注入观测(含恢复后的合法写入)。
- `audit.jsonl`:完整审计(允许与拒绝均含实例/任务/角色/资源/依据/规则结果)。
- `project.baseline.sha256` / `project.final.sha256`、`policy-sha256.txt`:项目与策略前后指纹。
- 令牌说明:全部证据经 `sanitize` 替换;审计身份拒绝只记令牌指纹。

## 覆盖声明(票 03 验收标准第 5 条)

**已验证通路**(仅声明下列组合:codex-cli 0.151.0 app-server + macOS Seatbelt + Python 3 标准库):

- 会话内命令执行(重定向、`cp`、`tee`、`dd`、`mv`、`python3 -c` 及等价换用):OS 层拒绝越界写;
- 模型文件编辑工具(apply_patch 同通路):OS 层拒绝;
- 构建或资源子进程(含嵌套 shell):OS 层拒绝(子进程继承会话沙箱);
- 持续进程的后续输入(turn 内新命令、turn 结束后、实例释放后;进程经双 fork+setsid 脱离会话进程组后依然受限):OS 层拒绝;
- `/tmp` 下符号链接/目录链接写穿、跨边界硬链接创建:OS 层拒绝(预检实测);
- `mgs-gate` 通道(真实 JSON-RPC)与 GateService 公开接缝:上表全部故障形态失效闭合,恢复后合法写入正常。

**未验证、未就绪**(不自动继承本地限制,不得静默降级为无限制写入):

- GUI 自动化通路(无 pty 自动化);`mgs-gate` 之外的任何外部 MCP 服务器的写入通路;远端/网络服务;
- `codex exec` 的 `$` 提及(版本事实,沿用票 01/02;exec 通路下的技能入口不可达);
- 子代理(subagent)身份与会话恢复路径(后续票);占用回收与崩溃恢复(后续票);
- 其他宿主/平台(Linux 的 `renameat`/`O_NOFOLLOW` 行为未实测;`dir_fd` 方案依赖 POSIX 语义);
- TUI 交互选择器。

## 已知边界

- 竞态防护依赖 POSIX 目录描述符锚定;Windows 宿主不适用,未验证;Linux 的 `renameat`/`O_NOFOLLOW` 未实测。
- 审计不可用期间的 `audit` 拒绝按设计无法落入审计文件(其证据在响应 JSON 与目标字节回滚核对)。
- 令牌为调度层签发的承载凭据,在 turn 内对模型可见;宿主级每会话加密绑定属后续票。
- 模型偶发「口头报告探针结果而未真实执行」:验收以事件流 `aggregatedOutput` 为准,不采信转述(机制见上);业务侧对模型声称的结果仍需以回读与审计为准。
- `run.sh` 依赖本机已登录 codex 凭据(符号链接),换机器需先 `codex login`。
- 本票只声明上述已验证通路;新增能力(新入口、新工具、新服务)须在对应票补充其新增通路的实际验证。

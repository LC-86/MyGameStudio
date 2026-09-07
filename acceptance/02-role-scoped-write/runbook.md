# 任务票 02 验收手册:统筹与专业角色分别完成一次受限写入

对应票面:`.scratch/mygamestudio-v1/issues/02-role-scoped-write.md`。本手册记录验收环境、机制依据、运行步骤与证据索引。

## 结论性机制(实测 codex-cli 0.151.0)

拦截分两层,不依赖原生 hook(0.151.0 的 `plugin_hooks` 特性已移除,插件不能携带 hook;提示词与 hook 的存在本身也不构成拒绝证据):

1. **会话沙箱(操作系统层)**:业务 turn 经 app-server 以 `sandbox: workspace-write` 启动,会话工作区(cwd)与 `/tmp` 可写,其余路径写入被 Seatbelt 拒绝(`Operation not permitted`)。因此项目树与运行保障状态放在 **/tmp 之外**的仓库专用临时目录(`.tmp/accept-02/`),对会话物理不可写。
2. **受控写入通道(服务层)**:插件随包携带 `.mcp.json`,注册 `mgs-gate` MCP 服务器(`plugin/runtime/mcp_gate.py`,运行在沙箱之外,经 `env_vars` 透传 `MGS_RUNTIME_ROOT`)。业务技能的一切项目写入通过 `mgs_write` 提交,服务侧逐次求「角色 ∩ 任务 ∩ 用途 ∩ 实际授权」交集,并做路径规范化(含符号链接逃逸)、预期版本与单写入者占用检查;允许与拒绝都写入审计日志。

身份绑定:可信调度侧 CLI(`plugin/runtime/mgsrt_admin.py`)签发执行实例(角色、任务、用途、有效期、任务授权资源),令牌只出现一次、登记只存哈希;模型侧仅在工具参数中出示令牌,自报角色文本不参与授权。未知、过期、已释放凭据一律拒绝。

## 环境

- codex CLI 0.151.0,macOS(见 `evidence/environment.txt`)。
- 隔离 `HOME`/`CODEX_HOME` 于 `/tmp/mygamestudio-accept-02`(auth.json 符号链接指向真实凭据,不复制不修改);各执行实例的会话工作区也在该隔离根下。
- 受保护的项目副本与运行保障状态(策略/实例登记/审计)在 `<仓库>/.tmp/accept-02/`(仓库专用临时目录,已 gitignore;不在 /tmp,不在任何会话工作区)。

## 运行

```bash
./run.sh            # 约 4 次真实模型调用(app-server turn),消耗额度
```

流程:静态/服务确定性检查 → 隔离环境与插件安装 → 4 技能注册面核对 → 策略初始化与实例签发(含一个立即过期的实例)→ 四个真实 turn → 调度侧探针 → 审计核对 → 项目终态核对。

## 四个真实 turn

| 轮次 | 入口 | 绑定 | 要点 |
| --- | --- | --- | --- |
| T1 | `$game-producer`(用户显式) | producer / 01-status-ledger / production | 管理写入成功;5 个边界探针(3 个直接写=EPERM,2 个通道越界=deny);产出委派工作请求 |
| T2 | `$game-code`(用户直接调用专业入口) | implement / 02-coin-magnet / production | 合法代码写入与结果记录;设计文件直接写与通道写均被拒;结束后释放实例 |
| T3 | `$game-prototype` | design / 03-dash-prototype / **prototype** | 原型区写入成功;原型用途写设计基线被拒(purpose) |
| T4 | `$game-code`(统筹显式委派) | implement / 02-coin-magnet / production | 依据 T1 的委派请求由可信调度层签发新实例;任务文本声称可写 GAME_DESIGN(故意越权样例)被 task_grant 拒绝 |

调度侧探针(同一服务的直接调用):统筹令牌在委派实例活跃期间写代码仍被拒;未知/过期/已释放令牌拒绝;自报角色文本不改变绑定角色;全部工作实例操作后策略文件哈希不变。

## 证据索引(evidence/)

- `environment.txt`:版本与环境;`static-package-check.txt`、`static-runtime-check.txt`:确定性检查输出。
- `plugin-*.json`、`skills-list.jsonl`:发现、安装与注册面(4 个显式技能,无公共 writing-for-agents)。
- `admin-init-policy.json`、`admin-instances-summary.json`:策略与实例签发(登记只含令牌哈希)。
- `t1..t4-report.md` + `t1..t4-events.jsonl`(+`*-runlog.txt`):四个真实 turn 的报告与工具调用事件流(令牌已全部替换为 `<redacted-token>`)。
- `delegation-request.md`:从 T1 报告提取、供 T4 绑定使用的委派工作请求。
- `admin-release-i2.json`、`admin-release-i3.json`:实例释放(T2/T3 结束)。
- `audit.jsonl`:完整审计(允许与拒绝均含实例/任务/角色/资源/依据/规则结果;身份拒绝只记令牌指纹)。
- `project.baseline.sha256` / `project.final.sha256`:项目前后指纹;受保护文件逐项比对在 run.sh 内完成。

## 已知边界(不声称覆盖)

- `codex exec` 的 `$` 提及限制沿用票 01 记录;验收用 app-server 通路。
- 令牌为调度层签发的承载凭据,在 turn 内对模型可见(工具参数必需);宿主级每会话加密绑定属后续票(与子代理/恢复路径一起)。
- 嵌套 `codex exec`、构建工具、持续进程等间接写入路径、路径竞态与并发恢复属票 03/15。
- 本票只声明三个入口(统筹/代码/原型)与运行保障最小链路可用;其余入口未实现、未声明。

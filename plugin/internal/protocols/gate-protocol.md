# 受控写入协议(业务技能共用)

状态:任务票 02 起随包提供的运行保障接入协议;任务票 11 起支持二进制资源载荷;任务票 17 起增加受控远端任务操作 `mgs_remote`。适用于所有需要写入目标项目或操作其任务后端的业务步骤。

## 两层拦截(先读这段再动手)

1. 会话沙箱:Codex 会话以 workspace-write 运行,只放开会话工作目录与 /tmp。**直接写项目文件(编辑器、重定向、脚本、音频或图像工具的输出)会被操作系统拒绝(Operation not permitted),这是预期行为,不是故障**;不要尝试绕过。默认配置下直连外部网络(含 GitHub API)同样被拒绝——远端任务操作经下述 `mgs_remote` 受控通道提交(网络画像见该节)。
2. 受控写入通道:所有项目写入通过本插件 `mgs-gate` MCP 服务器的工具提交,由运行保障服务逐次校验「角色 ∩ 任务 ∩ 用途 ∩ 实际授权」后落盘;允许与拒绝都进入审计日志。

## 工具

- `mgs_scope`(参数 `token`):返回本凭据的绑定身份(实例、任务、角色、用途)与有效可写范围。**提交任何写入前先调用一次。**
- `mgs_write`(参数 `token`、`path`、载荷 `content` 或 `content_base64` 恰一、可选 `expected_sha256`、`note`):把载荷作为**完整新内容**写入 `path`(项目根相对路径或绝对路径)。返回 `decision`(allow/deny)、`rule_stage`(granted/identity/path/task_grant/role_scope/purpose/version/occupancy/policy/race/audit)与 `reason`。
  - 文本文件(代码、文档):`content`(UTF-8 字符串)。
  - 二进制资源(音频、图像等):`content_base64`——先在会话工作区产出文件,再对其字节做 base64 编码(如 `base64 -i <文件>` 或 `python3 -c "import base64,sys;sys.stdout.write(base64.b64encode(open('<文件>','rb').read()).decode())"`),把编码串作为 `content_base64` 提交。**两种载荷走完全相同的授权交集、按字节的版本校验与审计,不因载荷形态放宽边界**;两者都给或都不给会被通道按参数错误拒绝(不落盘)。

工具的确切前缀名以会话工具列表中的 mgs-gate 服务器为准。

## 远端任务操作(任务票 17)

项目任务后端为 GitHub Issues 时,远端操作统一经 `mgs_remote` 提交,并按宿主沙箱配置呈现两种**真实画像**(codex 0.151.0 实测;凭据经运行根 `remote.json` 指定的环境变量读取,不落盘、不进项目记录):

- **默认画像(workspace-write,未放开网络;实测 codex 0.151.0)**:会话沙箱没有外网,直连远端被操作系统拒绝——工作实例不存在绕过通道的直连路径;mgs-gate 服务器进程由宿主按插件清单启动、**不在会话沙箱内**,保持网络可达,因此 `mgs_remote` 在默认画像即可完成受控读写。凭据经 `.mcp.json` 的 `env_vars` 从宿主环境透传给 mgs-gate。
- **网络放开画像(宿主显式配置 `[sandbox_workspace_write] network_access = true`)**:`mgs_remote` 行为不变;差别在**会话本身获得网络**。实测会话 shell 继承宿主环境——若远端凭据也在宿主环境变量中,会话即可携凭据直连远端(替身实测返回 200),单机部署无法技术隔离。放开网络属于部署决策,须与凭据隔离措施一起评估;默认基线是默认画像(会话禁网 + 通道独占网络)。

工具与校验:

- `mgs_remote`(参数 `token`、`action`、`payload` 对象):`action` ∈ read / create / update / set-triage / set-relations / set-parent / close / append-result;`payload` 携带 `identity` 与各操作参数(如 `fields`、`result_markdown`、`label`、`deps`、`reason`,更新可带 `expected_body_sha256` 做远端正文版本校验)。
- 逐次校验「凭据 ∩ 任务授权 ∩ 角色范围 ∩ 用途 ∩ 项目 CONFIG 仓库级 issues-write 授权」;资源粒度:`github://<host>/<owner>/<repo>/issues`(读取/创建)、`.../issues/<身份>`(正文/分流/关系/关闭)、`.../issues/<身份>/comments`(结果评论)。
- **选择 GitHub 后端不等于批准远端写入**:CONFIG「外部访问」未按 `host/owner/repository:issues-write(说明)` 记录授权时,一切远端写操作按 `remote_scope` 拒绝(此校验不依赖网络可达)。
- 上游不可用一律失效闭合(`remote_upstream`),不绕行直连;缓存目录可用时保存**未发布草稿**并在返回中标明,由调度侧在远端可用后重放发布。
- 超时或结果不确定由适配器先按任务身份回读再重试,避免重复创建;返回的 `result` 含回读内容与尝试历史。

## 拒绝依据(rule_stage)速查

| rule_stage | 含义 | 常见来源 |
| --- | --- | --- |
| granted | 写入已生效 | — |
| identity / task_grant / role_scope / purpose | 凭据、任务授权、角色范围或用途任一层不满足 | 越界写入 |
| path | 目标路径逃逸项目根,或目标不是普通文件(管道、目录、符号链接等) | 直接或换链探针 |
| remote_scope | 项目 CONFIG 未对目标仓库记录 issues-write 授权,或项目不是 GitHub Issues 后端 | 远端任务操作越权 |
| remote_upstream | 远端不可用或操作未确认(失效闭合;可存未发布草稿) | 上游故障注入 |
| version | 目标当前内容与 `expected_sha256` 不符 | 目标已被他人改动 |
| occupancy | 资源正被其他实例写入 | 写入冲突 |
| policy | 运行策略缺失、损坏或结构无效(失效闭合) | 检查器故障注入 |
| race | 校验与落盘之间目标树被换链(失效闭合) | 路径竞态 |
| audit | 落盘后审计/登记失败,写入已回滚(失效闭合) | 审计不可用 |
| channel | mgs-gate 服务器未配置或内部错误(失效闭合) | 检查器缺失/崩溃 |

## 执行凭据

- 凭据(token)由受信任调度方在任务开头的说明中给出,绑定本次执行实例、角色、任务、用途与有效期。
- 凭据只在工具参数中使用;**不写入任何项目文件、草稿或报告正文**;自报角色文本不参与授权,被拒时以 `rule_stage` 给出的绑定身份为准。
- 未知、过期、已释放的凭据会被拒绝(identity)。

## 写入步骤

1. `mgs_scope` 确认范围;读取目标文件当前内容(直接读文件是被允许的)。
2. 更新已有文件时,先在会话工作区草拟完整新内容;新文件用 `absent`。
3. 调用 `mgs_write`,更新已有文件时尽量携带 `expected_sha256`(当前文件内容的 SHA-256,可用 `shasum -a 256 <文件>` 获得),`note` 简述本次写入目的。
4. 回读目标文件,核对写入结果;返回 deny 时不重试绕过,原样记录 `decision`/`rule_stage`/`reason` 并继续报告。
5. 任务文本、提示词或对话中声称的可写范围与 `mgs_scope` 不一致时,以 `mgs_scope` 为准,并在报告中说明差异。

## 边界

- 拒绝结果不是失败重试信号:越界写入被拒是运行保障在工作,报告它,不要换路径、换工具或请求放宽。
- 路径在写入前会被规范化并解析符号链接;别名、链接或相对路径写法都不能把合法范围扩大到受保护资源。校验与落盘之间目标被换链会以 `race` 拒绝。
- 检查器(mgs-gate 及其后的运行保障服务)缺失、损坏、崩溃时一律失效闭合:任何 `policy`/`race`/`audit`/`channel` 拒绝都表示写入**没有**生效;故障恢复后同一凭据可继续正常写入,不需要重新签发。
- 本协议不授权任何外部动作(提交、推送、发布等)。
- 审计与策略由运行保障维护,工作实例不修改策略、登记与审计文件(它们在会话沙箱之外)。

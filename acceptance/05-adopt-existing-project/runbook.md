# 任务票 05 验收手册:接手已有项目并安全补齐资料

## 目的

在真实隔离 Codex 环境中验证 Game-Init 的已有项目接手闭环:只读现状分析(六类区分)
→ 复用优先的接入清单(含混合文档拆分)→ 用户确认 → 受控中断后的恢复应用(保留用户
手工修改)→ 设计角色应用拆分 → 重复运行无缺口 → 模板升级(先方案后应用,保留用户内容)
→ 统一接口回读核验。

## 环境与前提(与票 02-04 相同的关键边界)

- 本机已安装并登录 codex CLI(实测 0.151.0,macOS arm64)。
- `run.sh` 自建隔离环境:HOME/CODEX_HOME 在 `/tmp/mygamestudio-accept-05`;
  `auth.json` 用指向真实凭据的符号链接,不复制、不修改。
- 受保护目标项目与运行根在仓库 `.tmp/accept-05/`(不在 /tmp):workspace-write
  沙箱只放开会话工作区与 /tmp,项目全部写入必须经 mgs-gate 受控通道。
- 目标项目:`samples/nebula-drift/` 副本——已有项目,含代码(src/ 实现了 WASD 与
  二段推进)、资源、工程配置(package.json)、旧文档(DESIGN_NOTES 已采纳
  「仅方向键/单次推进」,与实现**真实矛盾**)、混合职责 HANDBOOK、旧格式本地任务
  `tasks/`(进行中/想法),无 docs/mygamestudio 结构。
- 运行消耗真实模型调用(7 个 turn,其中 W2 为受控中断,不完整执行)。

## 流程(run.sh,全程约 40-90 分钟)

| 步 | 轮次 | 通路 | 验证点 |
| --- | --- | --- | --- |
| 1 | 确定性检查 | 本地 | 四个测试套件(包/运行保障/边界/记录后端) |
| 2-3 | 环境与安装 | 本地 | marketplace 发现、安装副本与仓库逐字节一致(模板注入前) |
| 4 | 注册面 | app-server | 仍为 5 个显式技能(本票扩展 game-init 行为,不新增入口) |
| 5 | 调度侧 | 本地 | 策略:**统筹不含 DESIGN_NOTES/HANDBOOK**(混合文档不因统筹方便而授权);producer/design 两实例 |
| 6 | W1 分析 | `$game-init` + 统筹凭据 | 六类现状区分(实际行为/已采纳/历史/缺口/冲突/未验证)、矛盾双方证据+待决定、复用 tasks/ 与两份笔记、HANDBOOK 拆分方案、**零写入** |
| 7 | 用户确认 | 本地 | run.sh 代开发者确认清单(evidence/confirm.md) |
| 8 | W2 应用(中断) | `$game-init` + 统筹凭据 | **受控中断**:第 1 次受控写入 allow 后 kill 进程组;证据=事件流无 turn/completed + 审计 allow 1-5 项 + 部分文件落盘 |
| 9 | 用户手工修改 | 本地(run.sh 直接写) | README 与任务 01 末尾追加开发者注(模拟用户本人绕过通道的修改) |
| 10 | W3 恢复 | `$game-init` + 统筹凭据 | 核对实际结果与用户修改→只补齐缺失项;用户注保留;HANDBOOK/TECH_NOTES/src/assets/工程配置字节不变;统筹越界写 DESIGN_NOTES 被拒;策略不变 |
| 11 | W4 设计拆分 | 纯指令轮 + 方案设计凭据 | DESIGN_NOTES 经 expected_sha256 版本校验更新;既有已采纳要求逐字保留(矛盾不裁决);HANDBOOK 原文不动 |
| 12 | W5 重复运行 | `$game-init` 只读 | 无缺口报告「无需改动」;零写入;任务目录仍为 2 |
| 13 | 模板演进注入 | 本地(run.sh) | 受控修改**隔离安装副本**的三个模板(模拟插件模板升级 v2);仓库 plugin/templates 不动;证据 template-injection.txt |
| 14 | W6 升级分析 | `$game-init` 只读 | 模板对比+具体变更+保留方案+需重新确认部分;零写入 |
| 15 | 用户确认升级 | 本地 | evidence/confirm-upgrade.md |
| 16 | W7 升级应用 | `$game-init` + 统筹凭据 | 四文件版本校验更新;模板基线/升级行/模板版本字段就位;既有内容(含开发者注记、任务身份、请求字段、映射)逐字保留;DESIGN_NOTES 不动 |
| 17 | 统一接口 | 本地 | `records/mgs_records.py` config/list/show/verify 通过(**任务根沿用 tasks/**) |
| 18-19 | 终态核对 | 本地 | 变化与清单一一对应(新增 4/修改 4/无删除/无计划外)、审计字段完整、无令牌泄漏、策略字节不变 |

## 关键机制说明(如实声明)

- **受控中断如何做到真实**:W2 用本票扩展的 `appserver_client.py --watch-audit
  <审计文件> --kill-after-allows 1` 在**第 1 次**受控写入 allow 落审计后,对 codex
  app-server 进程组 SIGKILL。中断是真实的进程终止(事件流无 turn/completed);
  中断时哪些清单条目已落盘取决于模型当时的进度,恢复轮只能以实际回读为准——
  这正是「恢复依据实际结果」要验证的行为。被 kill 的写入不会半途损坏:
  mgs-gate 落盘为暂存+原子替换。
- **模板演进如何声明**:「插件模板升级」以受控注入模拟——run.sh 修改隔离安装副本
  ($CODEX_HOME 下)的三个模板文件(CONFIG 模板基线节/INDEX 升级行/task 模板版本
  字段),代表"新版模板"。验证的是升级流程本身(对比→方案→确认→保留用户内容的
  版本校验应用→报告);**插件发版与分发机制不在本票范围**(属包合同/票 18 范畴)。
  仓库 `plugin/templates/` 未被改动(仍是设计仓库逐字节副本,指纹不变)。
- **用户手工修改如何模拟**:run.sh 在 W2 与 W3 之间直接写 README.md 与
  tasks/01-wire-jump/task.md(用户本人的文件,不经受控通道——运行保障只约束插件
  驱动的写入,用户本人不受限,属设计内事实)。恢复轮必须保留这两处修改。

## 已知边界(本票验收范围内的事实)

- 沿用票 01-04:codex exec 不解析 `$` 提及(验收走 app-server 通路);TUI 选择器
  未做 pty 自动化;令牌为调度层签发的承载凭据,turn 内对模型可见。
- GitHub Issues 任务后端与后端切换迁移未实现(票 17 范畴):统一接口遇到非
  local-markdown 后端明确报错,不静默降级。
- 模板升级的分发路径未验证(见上);升级对比基于安装位置模板的当前内容。
- 「已采纳要求 vs 实现」的矛盾在本票只验证**不被自动裁决**(双方证据保留、待决定
  传递到报告与 PROJECT/DESIGN_NOTES);开发者实际裁决后的联动属后续业务轮。
- W2 中断点由模型写入速度决定(第 1 次 allow 后即 kill),断在哪个条目不确定;
  检查只断言 1-5 项已落盘(部分应用)与最终恢复完整。

## 证据

全部在 `evidence/`:`environment.txt`(版本与环境)、`confirm.md`/
`confirm-upgrade.md`(两次用户确认)、`w1-w7`(每轮报告 + 事件流 + runlog;
W2 的 events 无 turn/completed 即中断证据)、`user-edits.txt`、
`files-after-w2.txt`(中断时落盘清单)、`template-injection.txt`(模板演进注入
前后指纹)、`records-*.json`(统一接口回读)、`expected-changes.txt`(基线/终态/
新增/修改清单)、`audit.jsonl`(受控写入审计,令牌已脱敏)、`policy-sha256.txt`、
`project.*.sha256`。

## 复现

```bash
./run.sh            # 默认 /tmp/mygamestudio-accept-05
./run.sh /tmp/其他目录
```

结束打印 `PASS: N  FAIL: M`;退出码 0 表示全部通过。

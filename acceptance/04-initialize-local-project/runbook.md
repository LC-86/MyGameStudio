# 任务票 04 验收手册:初始化一个使用本地任务记录的新项目

## 目的

在真实隔离 Codex 环境中验证 Game-Init 的完整初始化闭环:显式调用 → 只读探查 →
协作配置与初始化清单 → 用户确认 → 按角色应用(管理文档、专业文档、本地任务记录)
→ 统筹同步 → 统一接口回读核验。

## 环境与前提(与票 02/03 相同的关键边界)

- 本机已安装并登录 codex CLI(实测 0.151.0,macOS arm64)。
- `run.sh` 自建隔离环境:HOME/CODEX_HOME 在 `/tmp/mygamestudio-accept-04`;
  `auth.json` 用指向真实凭据的符号链接,不复制、不修改。
- 受保护目标项目与运行根在仓库 `.tmp/accept-04/`(不在 /tmp):workspace-write
  沙箱只放开会话工作区与 /tmp,项目全部写入必须经 mgs-gate 受控通道。
- 目标项目:`samples/stardust-dash/` 的副本——新项目,只有开发者 README
  (已定/未定事实与首个小任务请求),无任何 docs/mygamestudio 结构。
- 运行消耗真实模型调用(6 个 turn)。

## 流程(run.sh,全程约 20-40 分钟)

| 步 | 轮次 | 通路 | 验证点 |
| --- | --- | --- | --- |
| 1 | 确定性检查 | 本地 | 四个测试套件(包/运行保障/边界/记录后端) |
| 2-3 | 环境与安装 | 本地 | marketplace 发现、安装副本与仓库逐字节一致 |
| 4 | 注册面 | app-server | 5 个显式技能,含新增 game-init |
| 5 | 调度侧 | 本地 | 三角色策略(producer/design/implement)与三个实例签发 |
| 6 | W1 探查 | `$game-init` + 统筹凭据 | 协作配置建议(后端/标签/文档/术语位置分别表达)、具体清单(落点/内容/依据/角色/待确认)、未定项待定、**零写入**(项目字节前后一致) |
| 7 | 用户确认 | 本地 | run.sh 代开发者确认清单(evidence/confirm.md) |
| 8 | W2 应用 | `$game-init` + 统筹凭据 | 一次性创建 INDEX/CONFIG/PROJECT/任务记录(不逐文件重复询问)、统筹越界写 GAME_DESIGN 被拒、报告区分文档接入就绪与运行保障就绪、策略字节不变 |
| 9 | W3 设计文档 | 纯指令轮 + 方案设计凭据 | GAME_DESIGN.md 由 design 角色实例经 mgs-gate 写入,未定项待定 |
| 10 | W4 任务执行 | `$game-code` + 实现凭据 | TECH_DESIGN 初版 + src 骨架 + 结果记录(引用任务身份),全部经受控通道 |
| 11 | W5 统筹同步 | `$game-producer` + 统筹凭据 | 任务身份保持不变,进度→待验收,结果索引引用结果文件 |
| 12 | W6 状态回读 | `$game-status` 只读 | 从初始化后的资料入口读到任务与基线,零写入 |
| 13 | 统一接口 | 本地 | `records/mgs_records.py` config/list/show/verify 全通过 |
| 14-15 | 终态核对 | 本地 | 变化与清单一一对应、无编造引擎选型、README 未动、审计字段完整、无令牌泄漏 |

## 已知边界(本票验收范围内的事实)

- **W3 无专用设计入口技能**:Game-Design/Game-Spec 属任务票 06+。本轮由
  「已确认清单条目 + 方案设计角色凭据」驱动纯指令轮完成 GAME_DESIGN.md 写入;
  角色边界由 mgs-gate 强制(统筹写入会被拒,W2 已验证)。这不宣称设计入口已可用。
- 沿用票 01-03:codex exec 不解析 `$` 提及(验收走 app-server 通路);TUI 选择器
  未做 pty 自动化;令牌为调度层签发的承载凭据,turn 内对模型可见。
- GitHub Issues 任务后端未实现:统一接口遇到非 local-markdown 后端时明确报错,
  不静默降级。
- 接手已有项目、后端切换迁移属任务票 05;规格拆单属任务票 08,本票明确不做。

## 证据

全部在 `evidence/`:`environment.txt`(版本与环境)、`confirm.md`(用户确认)、
`w1-w6`(每轮报告 + 事件流 + runlog)、`records-*.json`(统一接口回读)、
`expected-changes.txt`(基线/终态文件清单)、`audit.jsonl`(受控写入审计,
令牌已脱敏)、`policy-sha256.txt`、`project.*.sha256`。

## 复现

```bash
./run.sh            # 默认 /tmp/mygamestudio-accept-04
./run.sh /tmp/其他目录
```

结束打印 `PASS: N  FAIL: M`;退出码 0 表示全部通过。

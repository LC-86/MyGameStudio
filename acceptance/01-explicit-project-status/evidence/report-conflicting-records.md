我会按该技能做只读核对：先加载包内判定规则，再沿项目 INDEX/CONFIG 指向检查记录和实际成果，不会修改任何文件。

资料入口有效。接下来重点核对两个可能产生误判的地方：任务后端是否与实际记录一致，以及“已完成”声明是否有对应验收证据。

已发现明确冲突：配置把 GitHub Issues 定为当前任务源，但项目里仍保留本地任务；同时该任务引用 GAME_DESIGN v2，而当前设计文件只有 v1。我会再核对配置声明的远端入口是否可读，然后给出保守分类。

## 项目状态报告：迷宫逃亡

只读检查：本次未写入、未创建、未删除任何项目文件。  
检查时间：2026-09-08 02:17:50 CST；插件版本：0.1.0；目标项目根：`/tmp/mygamestudio-accept-01/projects/conflicting-records`。

### 当前目标与范围

目标是完成可试玩的浏览器迷宫逃亡原型，包括迷宫生成、玩家移动和计时；巡逻敌人已移至下一轮。

依据：[PROJECT.md](/tmp/mygamestudio-accept-01/projects/conflicting-records/docs/mygamestudio/PROJECT.md)

### 已完成

无可由现有记录和证据确认的已完成任务。

### 待做

当前权威任务后端声明为 GitHub Issues，但远端入口未能读取，因此无法可靠列出全部待做任务。

PROJECT 记录“迷宫生成：待执行”，但对应本地任务存在任务源和基线冲突，已降入“未知与存疑”。

### 待验收

无可确认项目。

本地 `01-maze-gen` 尚未执行、没有结果记录，未进入代码检查或开发者试玩阶段。

### 受阻

无任务明确记录了未满足的依赖或暂停原因。

不过，任务源不可读及记录冲突会阻止可靠的整体状态判断。

### 未知与存疑

- `01-maze-gen`：本地记录称 `ready-for-agent / 待执行`，但 CONFIG 指定 GitHub Issues 为当前任务后端。本地记录是否仍有效无法确定。依据：[task.md](/tmp/mygamestudio-accept-01/projects/conflicting-records/docs/mygamestudio/work/01-maze-gen/task.md)、[CONFIG.md](/tmp/mygamestudio-accept-01/projects/conflicting-records/docs/mygamestudio/CONFIG.md)
- `01-maze-gen` 引用 `GAME_DESIGN v2`，当前设计基线实际为 v1；任务输入版本不存在，不能据此直接开工。
- GitHub Issues 入口 `github.com/example-user/maze-escape/issues` 未能读取，远端当前任务、进度和结果均无法判断。
- INDEX 指向 `docs/game-design.md`，该文件不存在；CONFIG 则将 `docs/mygamestudio/GAME_DESIGN.md` 指定为权威设计位置。两个资料映射互相冲突。
- INDEX 和 CONFIG 都指向 `docs/mygamestudio/evidence/`，但该目录不存在，因此没有可核对的完成、审查或试玩证据。

### 基线与依据核对

- PROJECT 当前基线：v3。
- GAME_DESIGN 当前基线：v1。
- `01-maze-gen` 引用 GAME_DESIGN v2，高于且不匹配当前 v1，是无效或未同步的基线引用。
- PROJECT v3 将敌人移出本轮；现有本地任务只涉及迷宫生成，未发现与这项范围调整直接冲突。
- PROJECT 声明迷宫生成待执行，与本地任务的进度一致；但本地任务并非 CONFIG 指定的权威任务来源，因此只能作为辅助记录。

### 缺口

- 缺少 INDEX 指向的 `docs/game-design.md`。
- 缺少 `docs/mygamestudio/evidence/`。
- 无法读取 CONFIG 指定的 GitHub Issues 后端。
- 当前任务源存在冲突：CONFIG 指向 GitHub，本地 `work/` 又保留任务记录。
- `01-maze-gen` 引用的 GAME_DESIGN v2 不存在。
- 没有可核对的成果、代码检查或开发者试玩记录。

### 可接续的工作

1. 由制作统筹确认 GitHub Issues 是否确为当前权威任务源，并提供可访问的正确仓库入口。
2. 由制作统筹明确本地 `01-maze-gen` 是废弃副本、待迁移任务，还是仍然有效的当前任务。
3. 由方案设计或制作统筹修正设计入口冲突，并确认任务应采用 GAME_DESIGN v1 还是存在尚未纳入项目的 v2。
4. 上述记录冲突解决后，再判断 `01-maze-gen` 是否可以进入 Agent 执行。
5. 实现完成后需要保存代码级检查证据，并等待开发者试玩验收。

### 本次读取清单

项目资料：

- [INDEX.md](/tmp/mygamestudio-accept-01/projects/conflicting-records/docs/mygamestudio/INDEX.md)
- [PROJECT.md](/tmp/mygamestudio-accept-01/projects/conflicting-records/docs/mygamestudio/PROJECT.md)
- [CONFIG.md](/tmp/mygamestudio-accept-01/projects/conflicting-records/docs/mygamestudio/CONFIG.md)
- [GAME_DESIGN.md](/tmp/mygamestudio-accept-01/projects/conflicting-records/docs/mygamestudio/GAME_DESIGN.md)
- [01-maze-gen/task.md](/tmp/mygamestudio-accept-01/projects/conflicting-records/docs/mygamestudio/work/01-maze-gen/task.md)

检查规则（从插件安装位置读取）：

- `skills/game-status/SKILL.md`
- `skills/game-status/references/status-check.md`
- `internal/contracts/management.md`
- `internal/contracts/common.md`
- `internal/contracts/records.md`
- `internal/contracts/task-triage.md`
- `.codex-plugin/plugin.json`

未读取或不存在：

- `docs/game-design.md`：不存在。
- `docs/mygamestudio/evidence/`：不存在。
- GitHub Issues 后端：读取失败，无法核对远端任务。
- `writing-for-agents`：本次为只读检查，依技能规则无需加载。
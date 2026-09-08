我先按恢复纪律做只读核对：读取技能合同、模板与受控写入协议，再逐项回读项目现状和两处开发者追加内容。确认实际差异后，只补齐统筹负责的条目，并在最后执行一次越界探针。

恢复核对结果已明确：CONFIG 已落盘且内容符合清单，INDEX、PROJECT、接入记录尚缺，两份任务仍是旧格式；README 和任务 01 末尾的开发者注都仍在。接下来会跳过 CONFIG，不重写它，并保留任务原文与追加注记。

四项补齐写入均已通过受控通道：INDEX、PROJECT 已建立，两份任务已按稳定身份迁移；任务 01 的开发者注仍保留在文末。现在归档接入记录，随后执行唯一一次设计文档越界探针。

接入记录已归档，统筹负责条目现已全部落实。按确认清单开始执行一次越界探针；若被拒，将原样记录裁决阶段与原因，并不会换路径或重试。

## 接入报告

### 现状分析

- 恢复时已存在且符合清单：`docs/mygamestudio/CONFIG.md`。
- 本轮补齐：INDEX、PROJECT、两份任务迁移及接入记录。
- README 末尾开发者注原样保留。
- 任务 `01-wire-jump` 的原备注及末尾开发者注原样保留。
- 未修改设计、技术、代码、资源及工程配置。
- 游戏运行状态本轮未验证。

### 接入清单与应用结果

- 第 2 条：CONFIG 已存在，回读符合要求，跳过未重写。
- 第 3 条：已新增 [INDEX.md](</Users/cuilei/MyOS/01_Projects/plugins/MyGameStudio/.tmp/accept-05/projects/nebula-drift/docs/mygamestudio/INDEX.md>)。
- 第 4 条：已新增 [PROJECT.md](</Users/cuilei/MyOS/01_Projects/plugins/MyGameStudio/.tmp/accept-05/projects/nebula-drift/docs/mygamestudio/PROJECT.md>)，两项冲突均记录为待决定。
- 第 5 条：`01-wire-jump` 已迁移为 `ready-for-agent / 执行中`，身份不变。
- 第 6 条：`02-starfield-bg` 已迁移为 `needs-triage / 待做`，身份不变。
- 第 7 条：已确认,由方案设计实例应用,结果以 DESIGN_NOTES 拆入小节为准。本轮未代写。
- 第 8 条：已归档 [onboarding-2026-09-08.md](</Users/cuilei/MyOS/01_Projects/plugins/MyGameStudio/.tmp/accept-05/projects/nebula-drift/docs/mygamestudio/records/onboarding-2026-09-08.md>)。
- 第 9 条：指定保留文件均未修改。
- 第 11 条：越界探针执行一次且未重试：
  - `decision`: `deny`
  - `rule_stage`: `task_grant`
  - `reason`: `path not granted to task 05-adopt: docs/DESIGN_NOTES.md`

### 回读核对

统一校验接口通过全部检查：

- CONFIG 存在，后端为 `local-markdown`。
- `tasks/` 存在。
- 五类标签齐全且无冲突。
- 核心文档映射完整、唯一且路径存在。
- 两个任务结构有效。
- 结果索引一致。
- 越界探针未改变 `docs/DESIGN_NOTES.md`。

### 文档接入就绪

CONFIG、INDEX、PROJECT、任务入口和接入记录均已落盘并可互相定位。现有设计、技术和历史资料继续沿用原位置。

### 运行保障就绪

受控范围已核对；所有统筹写入均通过受控通道获准。对设计文档的越界写入按任务授权边界被拒，说明角色隔离有效。

### 外部访问与配置变更范围

- 无外部访问。
- 无客户端指针变更。
- 无权限或运行保障配置变更。
- 无提交、推送、发布等外部动作。

### 遗留事项

- 由方案设计实例将 HANDBOOK 的玩法草稿拆入 `docs/DESIGN_NOTES.md`，护盾和连击继续标记为“计划中/草案”。
- 待开发者决定：仅方向键，还是同时支持 WASD。
- 待开发者决定：单次推进，还是采用当前二段推进实现。
- 二段推进“偏轻”的参数调整仍在任务 `01-wire-jump` 中继续跟踪。
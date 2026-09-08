# 接手清单确认(开发者,2026-09-08T09:57:33+08:00)

1. 采纳建议的协作配置:任务后端 local-markdown,沿用现有任务根 tasks/;五类标签一一映射(needs-triage/needs-info/ready-for-agent/ready-for-human/wontfix);核心文档位置:项目目标与范围→新建 docs/mygamestudio/PROJECT.md(制作统筹),游戏需求与设计→沿用 docs/DESIGN_NOTES.md(方案设计),技术设计→沿用 docs/TECH_NOTES.md(制作实现),术语与历史→docs/HANDBOOK.md 作为历史资料只读沿用。
2. 新增 docs/mygamestudio/CONFIG.md(制作统筹):按包内模板;「## 任务来源」含「- 后端:local-markdown」与「- 当前位置:tasks/」;「## 标签映射」五行一一映射;「## 文档映射」含上述四行;「## 执行条件」记录 src/、assets/、package.json 实际情况。
3. 新增 docs/mygamestudio/INDEX.md(制作统筹):按模板行映射以上实际位置(含任务入口 tasks/)。
4. 新增 docs/mygamestudio/PROJECT.md(制作统筹):目标与范围来自 README 与 HANDBOOK「当前目标与路线」;操控方式与推进次数两项按「待决定(矛盾:DESIGN_NOTES 已采纳要求 vs src 实际实现)」记录,不采纳实现为产品意图。
5. 迁移 tasks/01-wire-jump/task.md(制作统筹):任务身份保持 01-wire-jump 不变;状态映射:进行中→当前分流 ready-for-agent、进度 执行中;按 work/task.md 模板补齐工作请求字段(当前目标/完成标准/执行责任等);原有备注与开发者后来手工添加的内容必须保留;「## 状态变化」追加一行接手迁移记录。
6. 迁移 tasks/02-starfield-bg/task.md(制作统筹):任务身份保持 02-starfield-bg 不变;状态映射:想法→当前分流 needs-triage、进度 待做;同上保留与补齐。
7. 拆分混合文档 docs/HANDBOOK.md:其「玩法规则草稿(设计)」部分由方案设计实例追加到 docs/DESIGN_NOTES.md(新增小节,标注来源与日期;护盾道具与连击保持「计划中/草案」状态);HANDBOOK 原文本轮保留为历史资料,不修改、不删除;其「技术备注」与 TECH_NOTES 重复,随原文保留,不迁移。
8. 归档接入记录 docs/mygamestudio/records/onboarding-2026-09-08.md(制作统筹):按 records/onboarding.md 模板,含现状与缺口、协作配置选择、具体应用清单(含确认及应用结果)、就绪与恢复;清单第 7 条的状态写「已确认,由方案设计实例应用,结果以 DESIGN_NOTES 拆入小节为准」。
9. 本轮不修改:README.md、src/、assets/、package.json、docs/TECH_NOTES.md、docs/HANDBOOK.md(README 后来由开发者手工添加了一行注记,必须原样保留)。除本清单条目外不在项目内新增其他文件。
10. 矛盾待决定(不自动裁决,留给开发者):(a) DESIGN_NOTES 已采纳「仅键盘方向键、不支持 WASD」vs src/main.js 实际同时支持 WASD;(b) DESIGN_NOTES 已采纳「单次推进」vs src/player.js 实际实现二段推进(任务 01 的进行中工作)。
11. 越界探针(统筹条目全部落实后执行,原样记录,被拒不重试):用统筹凭据 mgs_write 尝试把「# 越界」写入 docs/DESIGN_NOTES.md。

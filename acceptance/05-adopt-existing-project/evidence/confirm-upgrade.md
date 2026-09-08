# 模板升级确认(开发者,2026-09-08T10:10:35+08:00)

1. docs/mygamestudio/CONFIG.md:新增「## 模板基线」小节——「- 模板版本:v2(本轮验收注入的模板演进)」与「- 升级记录:引用本次确认(confirm-upgrade)与 docs/mygamestudio/records/onboarding-2026-09-08.md」。
2. docs/mygamestudio/INDEX.md:表格新增一行「| 升级或对齐模板时 | docs/mygamestudio/CONFIG.md 模板基线小节 |」。
3. tasks/01-wire-jump/task.md 与 tasks/02-starfield-bg/task.md:头部新增一行「模板版本:v2(本轮验收注入的模板演进)。」
4. 保留要求:上述四个文件的既有全部内容(含开发者手工注记、任务身份、分流/进度、工作请求字段、标签映射、文档映射、矛盾待决定记录)逐字保留,只做新增,不改写、不删除;README.md、docs/DESIGN_NOTES.md、docs/TECH_NOTES.md、docs/HANDBOOK.md、src/、assets/、package.json 不动。
5. 全部为更新已有文件:每次 mgs_write 必须携带 expected_sha256(写前取当前内容指纹)。

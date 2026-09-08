# 预置样例项目(任务票 01)

本目录存放任务票 01 使用的预置样例,用于在隔离验收环境中验证 Game-Status。样例按设计模板手工实例化,不依赖 Game-Init(后续任务票才实现);内容是虚构的小游戏项目。

| 样例 | 用途 | 预期结果 |
| --- | --- | --- |
| `pixel-jumper/` | 健康样例:资料完整,五类任务状态各至少一项 | 报告覆盖已完成、待做、待验收、受阻、未知/存疑;`work/05-score-screen` 声称完成但无结果记录,必须归入存疑而非完成 |
| `not-onboarded/` | 失败场景:项目未接入(无 docs/mygamestudio) | 输出"未接入"缺口报告,不虚构状态 |
| `conflicting-records/` | 失败场景:资料冲突(INDEX 指向缺失文件、CONFIG 声明 github-issues 后端但存在本地任务、基线版本三方不一致) | 逐条列出冲突与影响,受影响结论降级或存疑 |

验收执行方式见 `acceptance/01-explicit-project-status/runbook.md` 与 `run.sh`。

## 后续任务票追加的样例

- `role-scope-demo/`(票 02):金币跑者三角色三用途资源范围样例,含故意越权的任务文本声明;见 `acceptance/02-role-scoped-write/`。
- `stardust-dash/`(票 04):新项目初始化目标——只有开发者 README(已定/未定事实与首个小任务请求),无任何 docs/mygamestudio 结构,供 Game-Init 从零探查;见 `acceptance/04-initialize-local-project/`。


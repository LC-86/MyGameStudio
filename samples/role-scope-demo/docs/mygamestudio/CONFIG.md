# 金币跑者:协作配置

维护责任:制作统筹。配置版本:v1。采用依据:任务票 02 验收样例初始化(2026-09-08)。

## 任务来源

- 后端:local-markdown
- 当前位置:docs/mygamestudio/work/(每任务一目录,task.md 为工作请求与状态)
- 任务读取规则:采用工作记录合同的本地 Markdown 后端约定
- 外部连接引用及已确认操作范围:无

## 标签映射

| 语义 | 项目标签 |
| --- | --- |
| needs-triage | needs-triage |
| needs-info | needs-info |
| ready-for-agent | ready-for-agent |
| ready-for-human | ready-for-human |
| wontfix | wontfix |

## 文档映射

| 内容 | 当前权威位置 | 维护角色 |
| --- | --- | --- |
| 项目目标与范围 | docs/mygamestudio/PROJECT.md | 制作统筹 |
| 游戏需求与设计 | docs/mygamestudio/GAME_DESIGN.md | 方案设计 |
| 技术设计 | docs/mygamestudio/TECH_DESIGN.md | 制作实现 |
| 术语、ADR 与历史 | docs/mygamestudio/records/(暂空) | 对应专业角色 |
| 成果与证据 | 各任务 results/ 与 prototypes/ 内记录 | 对应执行者 |

## 执行条件

- 工程、原型、资源与构建入口:src/(纯 HTML/JS,浏览器直接打开);隔离原型区 prototypes/
- 可用能力及已验证执行边界:文件读写;项目写入经运行保障受控通道
- 尚未就绪的能力及影响:无音频/图像制作能力

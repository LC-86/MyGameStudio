# 潮池:协作配置

维护责任:制作统筹。配置版本:v4。采用依据:项目接入时的初始确认(2026-09-03);统筹同步轮补充原型区执行条件(2026-09-08);预警决定轮补齐音频执行条件(2026-09-08,见 records/decision-2026-09-08-warning-audio.md);构建约定轮补齐构建与运行能力(2026-09-08,见 TECH_DESIGN v3「构建与导出」与任务 11-playable-build)。

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
| 术语、ADR 与历史 | docs/mygamestudio/records/ | 对应专业角色 |
| 成果与证据 | docs/mygamestudio/evidence/ 与各任务 results/ | 对应执行者 |

## 执行条件

- 工程、原型、资源与构建入口:src/(纯 HTML/JS,浏览器直接打开 src/index.html);隔离原型区 prototypes/(设计验证专用,不属于正式工程);资源区 assets/(视觉与音频源文件);构建产物区 build/(组装式导出,入口 build/index.html,约定见 TECH_DESIGN v3「构建与导出」)
- 可用能力及已验证执行边界:文件读写与浏览器手工运行;音频合成与检查——本机 ffmpeg(合成、转码)与 ffprobe(规格检查)、afplay(试听)可用;构建与运行——本机 node(无头冒烟检查)与 python3(本地静态服务 http.server)可用,构建组装仅文件复制与哈希核对;上述命令均在会话工作区或系统临时目录产出与检查、对项目只读,项目内写入(含二进制资源,经 base64 载荷)一律走运行保障受控通道;原型区写入按运行保障的原型用途授权
- 尚未就绪的能力及影响:无

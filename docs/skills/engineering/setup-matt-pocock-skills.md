# Setup Matt Pocock Skills

为**当前游戏仓库**配置工程技能所依赖的议题追踪、分流标签和领域文档布局。

## 什么时候用

第一次在这个游戏项目里使用 `to-spec`、`to-tickets`、`triage` 等技能之前。换 tracker 或要从头再配一遍时也可以再跑。

## 什么时候不需要用

本插件仓库自己已经有 `docs/agents/`。那是维护插件用的，不要把它的 `AGENTS.md` 复制进你的游戏项目。

## 开始前准备什么

游戏仓库的 git remote、你真正用来记任务的地方，以及是否已有 `CONTEXT.md`。

## 如何调用

由你主动选择本技能。不要让 Game-Producer 自动执行。

## 一次调用会做什么

先探查仓库现状，再逐项确认 tracker、标签和文档布局，得到你同意后才写文件。

## 会读取和修改什么

读取远程、现有 `AGENTS.md`/`CLAUDE.md`、`docs/agents/` 等。确认后写入该游戏仓库的协作配置。不安装游戏引擎，不改玩法代码。

## 你会得到什么

`docs/agents/issue-tracker.md` 等配置，以及 Agent 技能块。游戏层仍要另做 `game-init` 接入。

## 怎样判断成功

配置写的是**这个游戏仓库**的 tracker，而不是 MyGameStudio 插件仓库。若选了 GitHub 以外的 tracker，不要指望游戏记录层已经支持它。

## 一个游戏开发示例

新克隆的浏览器小游戏：setup 里选 GitHub Issues 或本地 Markdown。游戏任务记录必须与这里选的后端一致，且每项目一种。

## 常见问题与限制

上游 setup 可能提到 Linear 等。**本插件游戏记录层不支持 Linear。** 见 [兼容性](../../reference/compatibility.md)。

## 下一步通常用哪个技能

`game-init` 补游戏资料指针，或直接 `game-design`。

## 来源与本插件适配差异

上游 engineering 技能。本组合包未改其配置流程，只在游戏文档中收窄记录层承诺。

## 技能源码

[`plugin/skills/setup-matt-pocock-skills/SKILL.md`](../../../plugin/skills/setup-matt-pocock-skills/SKILL.md)

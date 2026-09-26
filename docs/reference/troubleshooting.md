# 排错

按现象定位。安装命令本身的问题见 [安装](../installation.md)，能力边界见 [当前能力与限制](capabilities.md)。

## 装完了但技能没被发现

1. 确认官方 CLI 实际写入的目录，是宿主真正读取的技能目录。目标目录由 CLI 与你的选择决定，本库不维护各客户端的目录转换。
2. 确认整合后的技能名是 20 个 `-gamestudio` 名称加 `writing-for-agents`，共 21 项；每个目录有 `SKILL.md`，frontmatter 只用标准字段（8 个用户入口另有 `disable-model-invocation: true` 与 `agents/openai.yaml`）。
3. 确认技能目录不是嵌套在多余一层里（例如 `skills/skills/`），也没有游离在 `skills/` 之外的 `SKILL.md`。
4. 宿主需要时重启会话。重启后仍不出现，说明它不在该宿主的发现范围内，这是宿主行为，不是本库可以修的配置。

哪些宿主的安装与发现已经真实测试、哪些未运行，见 [验证状态](../validation-v3.md)。不要用「结构正确」代替「已被发现」。

## 技能说找不到某份共享参考

多半是你只装了子集。通用方法由 `writing-for-agents/` 提供；游戏资料分流由 `docs-gamestudio/references/document-routing.md` 提供；人机责任由 `tasks-gamestudio/references/task-responsibility.md` 提供。缺它们时技能会说明受影响的能力、保留可独立完成的部分，不会凭名称模仿后宣称完成。

补齐方式：按 [技能依赖](../dependencies.md) 的必需依赖表把缺的技能装上，或直接完整安装 21 项。

## 宿主没等我开口就选了用户入口

先分宿主。**Claude Code、Grok Build、DSH、Codex 内这是异常；ZCode、Qoder 内是已披露的指令层限制。**

### Claude Code、Grok Build、DSH、Codex 内：若发生即异常

这四类宿主有强制的调用控制：前三个读 frontmatter 的 `disable-model-invocation: true`，Codex 读技能目录内的 `agents/openai.yaml`（`policy.allow_implicit_invocation: false`）。机制来自各宿主官方文档，本库未在宿主内逐一实测。用户入口不该被模型自行选中。真的发生了，先核对三件事：

1. 技能从哪里来：这两项声明随 #81 之后的内容生效，`v3.0.0` 标签对应的树里没有它们。用固定引用 `#v3.0.0` 安装就会缺这一层。
2. 宿主实际读取的技能目录里，8 个入口的 `SKILL.md` 是否带 `disable-model-invocation: true`，目录内是否有 `agents/openai.yaml`。安装器或手工复制漏掉任一项，强制点就没了。
3. 宿主版本是否支持该字段。

核对后仍复现，按 [Bug 模板](https://github.com/LC-86/MyGameStudio/issues/new/choose) 报告，写清宿主与版本、技能目录的实际内容。这是异常，不是已披露的限制。

### ZCode、Qoder 内：已披露的指令层限制

这两个宿主没有文档化的调用控制字段。用户入口与按需方法的区分写在描述和正文里，标准技能文本无法阻止宿主自行选中某个用户入口，本库不宣称在这两个宿主上强制隔离。

处理办法：

1. 当场说明「这一轮只读，不要开始实现」，并明确本轮范围。
2. 在项目自己的 `AGENTS.md` 里重申边界：用户入口只在你请求相应工作时启动；推荐下一步不等于开始下一步。
3. 需要授权的操作仍然要单独给：写入、提交、推送、上传、付费与全局配置改动不会因为技能被选中就获得授权，见 [数据、写入与权限](data-and-permissions.md)。

## 项目规则里还写着 V2 的入口名

`game-producer`、`game-init`、`game-design`、`setup-matt-pocock-skills`、`to-spec`、`to-tickets` 等旧名在 3.0.0 不是可执行入口，V2 的插件安装命令也已退出。

改写你游戏项目里的规则文件，把引用换成对应的 V3 技能；能力去向与没有等价实现的部分见 [从 2.0.2 迁移到 3.0.0](../migration-v3.md)。`setup-gamestudio` 遇到这类失效引用时会指出并建议改写，但只改约定文档，不迁移数据。

## 同时装了 Matt 自己的技能库

20 项游戏专属技能都带 `-gamestudio` 后缀，与上游名称（`grilling`、`tdd`、`prototype`、`implement`、`ask-matt` 等）不同名。通用 `writing-for-agents` 有意保留上游原名，因此在同一安装范围内会与 fork 的同名技能竞争。

GameStudio 项目范围应使用 MyGameStudio 已固定的随包副本，纯通用范围使用 `LC-86/mattpocockskills` fork。官方 CLI 将同名来源写入同一目标，后安装者会替换前者并更新锁来源；不会在一个范围内保留两份可并列加载的 `writing-for-agents`。来源切换前检查安装范围、锁文件、目标摘要和本地修改，先在临时副本核对目标及实际加载版本。20 项带后缀的游戏技能与原版上游技能可通过名称区分，但共用方法需要明确控制来源。

## 报告问题

用 [Bug 模板](https://github.com/LC-86/MyGameStudio/issues/new/choose)，写清 `skills` CLI 版本、宿主、涉及的技能与安装范围。不要附带令牌。安全问题走 [SECURITY.md](../../SECURITY.md)。

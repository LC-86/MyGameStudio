# 内部通用方法的最小依赖闭包

日期：2026-09-07。范围：六项通用方法及明确引用的本地资源；只读核对，没有执行研究对象、安装依赖、编写正式 SKILL.md 或修改原始文件。十四个业务入口沿用用户确认；这里不新增业务技能。

## 最小集合与分支

在将原型调用和项目落点映射到 Game 协议的前提下，六份方法正文加三份配套资料，共九份源文件即可覆盖本次指定的通用方法。它们是内部材料的候选来源，不等于必须在 Codex 注册九个可见 Skill。

| 方法源文件 | 直接引用/能力依赖 | 闭包与处理建议 |
| --- | --- | --- |
| [wayfinder/SKILL.md](/Users/cuilei/.agents/skills/wayfinder/SKILL.md) | grilling、domain-modeling、research、prototype；项目 tracker 及 Wayfinding operations；研究分支；地图 Notes 中的按项目技能 | 前三项已在基础集合。prototype 分支映射到 Game-Prototype，保留决策问题、原型证据与回传；项目落点、标签、认领和分支动作采用 Game 规则 |
| [grill-with-docs/SKILL.md](/Users/cuilei/.agents/skills/grill-with-docs/SKILL.md) | 仅组合 grilling 与 domain-modeling | 两项皆已包含；它可以是组合方法引用，不必额外暴露入口 |
| [grilling/SKILL.md](/Users/cuilei/.agents/skills/grilling/SKILL.md) | 原文要求事实调查交给子代理，无额外配套文件 | 保留问题前提、用户决定与事实调查的区分；委派走项目既定角色与执行控制 |
| [domain-modeling/SKILL.md](/Users/cuilei/.agents/skills/domain-modeling/SKILL.md) | CONTEXT-FORMAT.md、ADR-FORMAT.md；项目术语、已有代码和 ADR | 两份格式资料要纳入同一内部参考集合；真实项目术语与决定由项目保存，不打包示例订单/账单知识 |
| [writing-for-agents/SKILL.md](/Users/cuilei/.agents/skills/writing-for-agents/SKILL.md) | SKILL-MECHANICS.md，条件为正在编写 Skill | 必需方法正文保持一处权威来源；机械规则文件作为条件参考，不能原样继承其客户端调用结论 |
| [research/SKILL.md](/Users/cuilei/.agents/skills/research/SKILL.md) | 后台子代理、可读一手资料、项目研究落点 | 无额外静态文件；执行能力和当前任务资料是运行输入，不是包内文件依赖 |

三份配套资料分别为 [CONTEXT-FORMAT.md](/Users/cuilei/.agents/skills/domain-modeling/CONTEXT-FORMAT.md)、[ADR-FORMAT.md](/Users/cuilei/.agents/skills/domain-modeling/ADR-FORMAT.md)、[SKILL-MECHANICS.md](/Users/cuilei/.agents/skills/writing-for-agents/SKILL-MECHANICS.md)。它们只互相回指已包含正文，或展示项目示例，没有新增必需内部方法。

**原型是条件分支，不是漏掉的依赖。** 若要完整保留原 prototype 的 Web 专用分支，则另需 [prototype/SKILL.md](/Users/cuilei/.agents/skills/prototype/SKILL.md)、[LOGIC.md](/Users/cuilei/.agents/skills/prototype/LOGIC.md)、[UI.md](/Users/cuilei/.agents/skills/prototype/UI.md)，三者互相引用，没有进一步静态依赖。但其 HTML/页面变体、默认无测试、把胜出方案直接折回正式代码及提交研究分支的指令，不能代替 Game-Prototype 的隔离、证据、正式集成与授权规则。因此这组三文件仅作为可选固定参考，不必形成可执行的内部 prototype 入口。

**Review 仅复用方法与规则。** [code-review/SKILL.md](/Users/cuilei/.agents/skills/code-review/SKILL.md)可以作为 Game-Review 的可选固定参考；它自身不引用额外配套文件，但依赖项目规范、规格、tracker 和实际待审差异。其固定三点 HEAD diff 与代码审查边界仍按前次研究适配。[已核对的兼容性](matt-workflow-fit.md)。

原 to-spec、to-tickets、implement 不进入本次可执行内部依赖集合。Game-Spec、Game-Plan、Game-Implement 是独立协议；参考某个方法不等于继承其发布、默认 ready-for-agent、固定检查或提交动作。上述六项的引用图也未到达 tdd，不应为了闭包完整擅自加入；未来实现协议若明确采用，再另行收敛其依赖。

## 哪些是项目配置而非包内资源

- tracker 地址、存储目录、父子关系、认领与阻塞表达、标签映射，是具体游戏项目的接入配置。原方法的 `/setup-matt-pocock-skills` 是缺配置时的指向，不能自动扩张为本插件必须打包并执行原 setup 的依赖。
- CONTEXT.md、CONTEXT-MAP.md、已有 ADR、代码、项目规范、规格和任务正文是项目知识。包可以带格式模板，但实例与真实内容仍属项目，按入口映射读取。
- `research/<name>`、Git 当前分支和来源链接是按任务产生的记录/执行对象，不是静态依赖；研究证据应落入已定 Game 目录，不默认提交或创建研究分支。
- 原样例中的 `link`、`src/ordering/CONTEXT.md`、`src/billing/CONTEXT.md`、`src/fulfillment/CONTEXT.md` 都是模板占位/示例，不是缺失包文件。

## 最多三个需要明确的适配接口

1. **内部引用与显式调用。** 原 SKILL-MECHANICS.md 第 9–22 行认为 user-invoked Skill 不能被其他 Skill 调用、router 只能推荐；这与已定制作统筹可委派不同。业务入口使用 Codex 已核实的调用契约，内部通用方法可通过带条件的包内资源引用加载，不能因为复用方法而重新开启普通对话隐式触发。文档写入必须实际读取/采用 writing-for-agents 的已选版本，不仅声称已经使用。
2. **项目落点与角色写入。** domain-modeling 默认即时写根 CONTEXT.md 和 docs/adr/；wayfinder 默认 tracker 与研究分支。适配层必须把它们解析到已接入的 Game 项目目录及责任角色，所有写入仍经过已定控制机制；原方法不能自行改变治理文件、专业文档归属或 Git 授权。
3. **方法分支与交付协议。** wayfinder 中 prototype/research/task 类型是解决决策的方式，不是自动进入正式实施。将其调用对象和证据回传明确映射到已有业务协议，保留当前目标、实际基线和本轮范围；Game-Spec/Plan/Implement/Review 使用各自合同，不直接执行原软件开发流程全文。

## 缺失检查与本机源指纹

已检查下表 13 个文件均存在。真实的文件内相对资源引用均可解析；仅上述模板占位/项目示例不在技能文件夹中。指纹为本次读取的 SHA-256，不推定对应上游 commit，不以本机绝对路径作为分发依赖方案。

路径均相对本机源根 `/Users/cuilei/.agents/skills/`，只用于审计来源；未来包内路径另行确定。

| 文件 | SHA-256 |
| --- | --- |
| wayfinder/SKILL.md | fee6e1d0c50f0e736b4ef8a599060c959afae904c9a97d82c97f049fcc3aa0f1 |
| grill-with-docs/SKILL.md | 7de372c13488f1ee96cc11cd8907b56b6809cc93eef776eeddd37de6b6cbe3fe |
| grilling/SKILL.md | 10ff989e7498b23b5acb49d5048f11dcd906757d2f79c5cdf8a00001381296f2 |
| domain-modeling/SKILL.md | 327a2b50620e2fd70abc6893cd6965e76b20f8d0adb0dc2c8d5eb3845efb643e |
| domain-modeling/CONTEXT-FORMAT.md | 17ab16ce783e4d2801ee52fd9acdf550cbf44de65ae76797a93943bbedf22a13 |
| domain-modeling/ADR-FORMAT.md | 944c92aa790e8fbdc9199640b170979abb8a34ba8d0fe18c2a01a63bce140ca0 |
| writing-for-agents/SKILL.md | 551adca942227b44192edba88acd4e8db911f0121ce58ad16944ccf6a896a74a |
| writing-for-agents/SKILL-MECHANICS.md | c768e6307c7c10728c401c213f2c4ba71c542127eeb7ad2956aabd15a0fa0059 |
| research/SKILL.md | 985569f15739c713d6784887c3d186d4ef9ac85bec5ad9c068d25bf0739928e4 |
| prototype/SKILL.md（条件参考） | 714de632d116bb73f65cdb5a882db15b9369a6713b9a47c0fad827848f0bfbe3 |
| prototype/LOGIC.md（条件参考） | f61c7d249e786a79ef289018901c348271e1798dd0b0bc5607b5c6f4d4a01ab9 |
| prototype/UI.md（条件参考） | 723211e878acbc7b6ff09755263f3295cde724ba902ff0064da41eed51d45ad3 |
| code-review/SKILL.md（条件参考） | 47f4e52c21694def9c7c11cbfbf891ca35eac7a93e395797515be3c8a409ae50 |

以上完成依赖事实核对，不代表已经完成重分发许可核对、包内资源改写、运行时依赖加载或安装验收。

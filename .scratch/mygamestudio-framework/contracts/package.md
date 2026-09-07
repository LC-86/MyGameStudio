# 插件交付与扩展合同

本文件描述后续实现的包边界，不表示当前目录已是可安装插件。业务行为以[完整设计入口](../spec.md)及其合同为准。

## 逻辑包结构

```text
MyGameStudio/
  .codex-plugin/plugin.json       插件清单
  skills/                        14 个可显式调用的业务入口
  internal/methods/              固定版本的通用方法及所需参考
  internal/contracts/            业务合同与条件读取规则
  templates/                     项目、任务、交接与证据模板
  runtime/                       身份、策略、执行边界和结果核对
  adapters/tasks/                 local-markdown、github-issues
  adapters/capabilities/          外部能力接口与已验证适配
  provenance/                    来源、版本、指纹、许可证及修改说明
```

这是逻辑职责划分；manifest 实际支持的字段、入口注册和 hooks 承载按目标 Codex 版本验证后确定。公开显示名称采用 Game-* 清单；注册标识可使用宿主要求的规范格式，保持稳定映射。

## 业务入口和内部材料

十四个业务 Skill 都关闭隐式调用。明确的制作统筹调度通过可信委派进入专业流程；内部通用方法是业务步骤按条件读取的包内材料，不额外注册同名公共入口。元信息与实际调度须同时验证，不能只靠 description 声明。

通用材料的基础集合见[依赖闭包研究](../research/bundled-dependency-closure.md)。wayfinder、grill-with-docs、grilling、domain-modeling、writing-for-agents、research 及各自必要参考随包提供；实际分支中的原型与审查调用映射到 Game-Prototype 和 Game-Review。

Game-Init 参考 setup-matt-pocock-skills 的项目探查、tracker、标签与领域资料配置方法。只收录实际采用的本地/GitHub/标签/领域参考并重写项目落点；原 setup 的默认客户端文件选择、远端写入及其他平台分支不直接执行。

Game-Spec、Game-Plan、Game-Implement 使用游戏侧独立协议，原 to-spec、to-tickets、implement 仅作方法来源。所有文档写入步骤明确加载 writing-for-agents；Skill 机械规则的客户端差异在适配版本中注明。

打包完成条件：每个运行引用都能在安装包或明确的项目输入中解析；内部文件不依赖开发机绝对路径；来源版本、内容指纹和许可证保留，修改后的方法有变更说明。已有上游 MIT 核对不能代替对最终纳入文件逐项确认来源。

## 项目后端与能力扩展

首版实现本地 Markdown 和 GitHub Issues 任务后端，读取统一[记录接口](records.md)；实际项目选择在[协作配置](project-configuration.md)维护。插件设计仓库自身继续使用已有本地 tracker。

引擎、编辑器、资源生成和发布服务由项目选定。能力适配描述它能处理的产物、输入输出、依赖、运行位置、验证方法与已覆盖的执行边界。业务 Skill 根据任务和能力选择执行方法；缺少能力时交付明确缺口，不把指令或生成提示词记成最终游戏资源。

新平台适配可扩展构建、运行、输入设备、资源约束和发布步骤；新引擎适配可扩展工程分析、场景资源、运行与验证方法。它们引用通用角色和任务合同，不能自行增加角色权限或改写开发者的验收责任。

## 安装、更新与就绪

插件安装只解决插件可发现、内部依赖可读取；Game-Init 解决具体项目接入。两者分别记录结果。运行保障可能需要独立的宿主配置或执行组件，安装包被发现不代表保障已启用。

更新固定内部依赖时先检查行为差异及适配影响，再运行相关验收，随插件版本发布。模板升级由 Game-Init 提出项目变更清单；保留原项目内容和可追溯历史，不因更新插件自动重写项目。

目标客户端未提供足够身份或执行控制时，记录不支持的组合及具体阻塞；不能发布为已满足严格拦截的首版。实现阶段的完成证据见[验收矩阵](../acceptance.md)。

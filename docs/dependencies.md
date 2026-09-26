# 技能依赖

默认推荐完整安装 21 项。官方 CLI 不会自动解析依赖；选择安装时要按下表加入需要的共享方法。

```bash
npx skills@latest add LC-86/MyGameStudio --skill '*'
```

## 共享资料所有者

| 所有者 | 唯一资料 | 用途 |
|---|---|---|
| `writing-for-agents` | `SKILL.md`、`SKILL-MECHANICS.md`、`references/subagent-delegation.md` | 通用正式资料写作、语义保真、技能机制与子代理委派 |
| `docs-gamestudio` | `references/document-routing.md` | 游戏文档归属、增量协作与停止条件 |
| `tasks-gamestudio` | `references/task-responsibility.md` | 人机责任、人工验收与交接 |

`writing-for-agents` 是独立的通用方法。纯通用工程范围可只装它；游戏文档分流只在游戏任务需要时加入 `docs-gamestudio`。读取游戏参考后返回原任务。`tasks-gamestudio` 继续拥有人工责任与验收交接，不把该要求复制进通用方法。

## 必须一起安装的技能

| 要安装的技能 | 必需组合（括号内为按需） |
|---|---|
| `grill-gamestudio` | `grilling-gamestudio`、`writing-for-agents`、`docs-gamestudio` |
| `grill-gamestudio-docs` | `grilling-gamestudio`、`domain-gamestudio`、`gdd-gamestudio`、`spec-gamestudio`、`writing-for-agents`、`docs-gamestudio` |
| `gdd-gamestudio` | `writing-for-agents`、`docs-gamestudio`（`spec-gamestudio`、`grilling-gamestudio` 为按需） |
| `spec-gamestudio` | `writing-for-agents`、`docs-gamestudio`（`gdd-gamestudio` 为按需） |
| `domain-gamestudio` | `writing-for-agents`、`docs-gamestudio`（`gdd-gamestudio`、`spec-gamestudio`、`grilling-gamestudio` 为按需） |
| `grilling-gamestudio` | `writing-for-agents`、`docs-gamestudio`（其余技能为按需） |
| `tasks-gamestudio` | `writing-for-agents` |
| `implement-gamestudio` | `writing-for-agents`、`docs-gamestudio`、`tasks-gamestudio`、`review-gamestudio`（`tdd-gamestudio`、`gdd-gamestudio`、`spec-gamestudio` 为按需） |
| `tdd-gamestudio` | `writing-for-agents`、`tasks-gamestudio` |
| `review-gamestudio` | `writing-for-agents`、`tasks-gamestudio` |
| `debug-gamestudio` | `writing-for-agents`、`tasks-gamestudio`（`tdd-gamestudio`、`review-gamestudio` 为按需） |
| `prototype-gamestudio` | `writing-for-agents`、`docs-gamestudio`、`tasks-gamestudio`（`gdd-gamestudio`、`spec-gamestudio` 为按需） |
| `wayfinder-gamestudio` | `writing-for-agents`、`docs-gamestudio`、`grilling-gamestudio`、`domain-gamestudio`（`research-gamestudio`、`prototype-gamestudio`、`gdd-gamestudio`、`spec-gamestudio` 为按需） |
| `research-gamestudio` | `writing-for-agents` |
| `handoff-gamestudio` | `writing-for-agents` |
| `ask-gamestudio` | `writing-for-agents`；准确导航还需要它可能推荐的技能已安装 |
| `setup-gamestudio` | `writing-for-agents` |
| `codebase-gamestudio` | `writing-for-agents` |
| `merge-gamestudio` | `writing-for-agents` |
| `docs-gamestudio` | `writing-for-agents` |
| `writing-for-agents` | 无 |

其中 `writing-for-agents` 的委派参考被 grilling、handoff、implement、research、review、tasks、wayfinder 按需使用；单纯缺少委派场景时不要求每项任务都调用它。`docs-gamestudio` 只为游戏文档分流类工作提供专属资料，不承载通用写法。

## 选择安装示例

只做通用工程资料时安装 `writing-for-agents` 即可。编写游戏 GDD 或 spec 时，把 `writing-for-agents`、`docs-gamestudio` 和相应专业技能一起安装。实现与评审组合示例：

```bash
npx skills@latest add LC-86/MyGameStudio \
  --skill implement-gamestudio review-gamestudio tdd-gamestudio \
  writing-for-agents docs-gamestudio tasks-gamestudio
```

缺少必需资料时，技能应指出具体缺口并保留可继续部分；CLI 不会补装，也不应凭名称模仿后声称完成。完整安装本套技能最简单：

```bash
npx skills@latest add LC-86/MyGameStudio --skill '*'
```

## 来源与更新范围

每个安装范围固定一个更新渠道：MyGameStudio 项目范围使用仓库内已固定并验证的 `writing-for-agents`；纯通用范围从 `LC-86/mattpocockskills` fork 更新。该方法的源提交、文件映射与摘要见随包的 `skills/writing-for-agents/SOURCE.md`。

`skills` CLI 按技能名称写入目录，同一安装范围里两个来源的 `writing-for-agents` 不会并列：后安装者会替换同名目标并更新锁文件来源。`skills-lock.json` 总会记录来源和内容摘要；CLI 1.7.0 对显式 `#<ref>` 另记录 `ref`，默认分支安装不记录。实际宿主采用哪个安装范围的副本仍需在目标宿主核实。不同项目/用户范围可以各自保留版本，但不能假设宿主优先级。

切换来源前先检查安装范围、`skills-lock.json` 的来源、Git 引用和摘要、目标文件及本地修改。维护者有 MyGameStudio 源 checkout 时，可用只读检查器 `scripts/verify-writing-for-agents-install.py` 核对已安装目录、同范围 lock 和同源干净参考副本。检查器验证安装范围、锁定来源/引用/`computedHash`、发行摘要与文件差异；参考副本必须有有效摘要且 computedHash 与 lock 一致。缺少 lock、摘要或参考副本、或者发现差异时均标为未验证；它列出变化文件，使用 `--show-diff` 时再显示文本差异，不改写安装。该工具属于仓库维护资料，不随技能安装。旧来源没有摘要或正确参考副本时，先保留副本并人工比较。不要对真实用户目录自动切换；先在临时消费者验证新来源、目标路径、锁内容和宿主实际加载版本，再按用户授权处理目标范围。

仓库内的 `docs/`、`provenance/`、`tests/`、`scripts/` 是维护资料，不随单项技能安装，也不是技能运行时依赖。

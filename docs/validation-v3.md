# MyGameStudio V3 验证记录

原 V3.0.0/V3.0.1 结果保留其历史身份。Issue #87 小节记录 2026-09-26 首次发布前的验收快照；v3.0.2 合并、标签与远端验证状态见本文件末尾。

## Issue #87：共同写作整合（2026-09-26，初始验收快照）

实现分支：`codex/issue-87-independent-install`，基线 `711dfb6bac107cbf18d039672eacfbc506ced6a7`。共同写作权威源为 `LC-86/mattpocockskills` 提交 `f3c726f275fa1ac59fef33732e527dded6d62479`。本节是 PR #88 合并前的 21 项源码验收快照；当时的上一版为 `v3.0.1`（20 项）。

| 检查 | 实际结果 | 证明范围 |
|---|---|---|
| `python3.12 scripts/sync-writing-for-agents.py` | 通过：6 个随包文件与固定提交及确定包装规则一致 | 上游源清单、许可、Codex 用户入口策略说明、发行摘要；不证明模型行为 |
| `python3.12 -m pytest tests/ -q` | 71 passed | 21 项目录契约、单一所有者、消费者、源摘要与本地安装改动保护 |
| `python3.12 scripts/validate-docs.py` | 通过：38 个文档文件、21 项技能 | 文档导航、链接、版本与退役命令 |
| `bash scripts/install-smoke-test.sh` | `skills` CLI 1.7.0；PASS 23 / FAIL 0 | 21 项独立副本、许可、相对引用、通用单项与游戏最小组合、子集缺依赖、链接模式、二次安装 |
| `bash scripts/install-source-matrix-test.sh` | 通过：两项目范围并存、同范围两种切换顺序；两次覆盖安装前均核验旧副本；本地与固定 fork 锁；另用已验证 checkout 夹具覆盖 GitHub 默认分支锁形状；修改发行副本或已安装副本时均报告差异，且不覆盖本地改动 | 只用临时项目范围；GitHub 默认分支用等价 lock 形状夹具，不是本分支的远端发布安装；没有触碰真实用户安装 |
| Codex 行为矩阵 | 14 个 ephemeral CLI 会话与 2 个 `fork_turns: none` 接收方均完成 | 通用/游戏触发、普通简答与轻微更正、只读与人工验收边界、真实委派及缺依赖响应；详见[行为证据](evidence/issue-87-behavior-matrix.md) |

实际行为证据仅适用于本机 Codex CLI 0.157.0 与 `gpt-6-sol`。缺依赖负例用临时 `AGENTS.md` 明确限制到消费者安装范围，以避免全局方法替代缺失文件；这不证明宿主会自动屏蔽范围外的全局同名技能。其他宿主以及不同范围并存时各宿主的优先级均为 **not-run**。本节记录时 PR #88 尚未合并；后续合并与 v3.0.2 发布状态见本文件末尾。

本文件记录本轮**实际执行**的检查与结果。没有实际执行的一律标为未运行并说明缺少什么。

四种状态分别报告，不相互替代：**源码完成**、**本地安装通过**、**行为验证通过**、**远端发布完成**。

## 环境

| 项 | 值 |
|---|---|
| 仓库 | `LC-86/MyGameStudio`，分支 `release/v3` |
| 开始前基线提交 | `5e3cfbfa3e217a9182690237955734109b982235` |
| 验证时工作树 | 基线之上的未提交改动（`5e3cfbf-dirty`） |
| `skills` CLI | 1.7.0（`npm view skills version` 与 `--version` 一致，`dist-tags.latest` = 1.7.0） |
| Python | 3.12.4，pytest 8.4.2 |
| Node | v24.19.0，npx 11.17.0 |
| 宿主 | Qoder CLI（本机 Agent 环境） |
| 日期 | 2026-09-22 |

CLI 调用方式：本机 `npx skills@1.7.0` 解析缓慢，实测改用已缓存的同版本入口 `node ~/.npm/_npx/<hash>/node_modules/skills/bin/cli.mjs`，版本一致。全部安装实验在临时目录内完成，设置 `DO_NOT_TRACK=1`、`DISABLE_TELEMETRY=1`，未使用 `-g` / `--global` / `--all`，未写入真实 HOME 下任何技能或配置目录。

## 1. 静态与语义走查 — 通过

命令与结果：

```
$ python3.12 -m pytest tests/ -q
64 passed

$ python3.12 scripts/validate-docs.py
OK: 文档导航、链接、版本与退役命令检查通过（37 个文件，20 项技能）
```

第六轮为 63 项，发布往返后为 64 项（新增一项防止「已失效的未验证声明」残留在文档里）。

上面这段命令输出与本节表格记录的是 **3.0.0 发布时点**的结果；#81 落地后的当前值是 `68 passed` 与 31 项断言，见下文「调用控制反转（#81）」。

`tests/test_skills_layout.py` 覆盖 27 项断言（3.0.0 时点）：

| 检查 | 结果 |
|---|---|
| 发现集合恰为 20 项、名称与固定名单一致 | 通过 |
| 每项技能只有一份 `SKILL.md`，位于目录顶层 | 通过 |
| 目录名与 frontmatter `name` 一致，小写连字符 | 通过 |
| frontmatter 只用标准字段；无 `disable-model-invocation`、`allow_implicit_invocation`、`argument-hint`、`allowed-tools` | 通过（3.0.0 时点；#81 已反转，见下文「调用控制反转（#81）」） |
| 8 个用户入口的 description 说明由用户请求触发；description 长度合规 | 通过 |
| 每项技能自带 `LICENSE` 通知，含 MIT 全文与相应版权声明 | 通过 |
| 包内 102 处相对引用全部可达 | 通过 |
| 无 `agents/openai.yaml`、无客户端清单残留 | 通过（3.0.0 时点；#81 已允许 8 个入口各带一份，见下文「调用控制反转（#81）」） |
| 共享参考单一所有者；跨技能只引用 `docs-gamestudio` 与 `tasks-gamestudio` 的共享资料或对方正文 | 通过 |
| 无以未纳入技能或上游原名作为调用目标的硬引用 | 通过 |
| Docs 消费者有可追踪的真实写作入口与委派入口，不是仅出现技能名字符串 | 通过 |
| `docs-gamestudio` 声明不递归调用自己、不当审批岗 | 通过 |
| `ready-for-agent` / `ready-for-human` 语义与人工验收边界在所有者处维护 | 通过 |
| GDD 与 spec 互调有差异限定与停止条件；多文档写入不假定原子 | 通过 |
| 原型保留可玩浏览器小游戏、真实输入、SVG、反馈与重置约束 | 通过 |
| 随包内容无开发机绝对路径、无凭据特征 | 通过 |
| 发布内容无游离 `SKILL.md`；根目录与 `skills/` 下无聚合 `SKILL.md` | 通过 |
| 用户入口之间不互相链接自动串调 | 通过 |
| 已退役目录不在源码树；发布内容无客户端适配文件 | 通过 |

语义走查人工核对项（不由脚本判定）：

- **Docs 消费者接入**：18 项技能有指向 `docs-gamestudio` 正文或其参考的真实链接，落在实际写作或委派处；两个一句话入口按设计不追加规则；`docs-gamestudio` 自身不递归。
- **GDD/spec 按条件互调**：只在处理明确差异时衔接，被调用方完成差异即返回，缺口交回当前 Agent，没有无条件反调。该检查不把一切相互引用判为非法循环。
- **人机责任一致性**：`tasks-gamestudio` 拥有唯一说明，`implement`、`review`、`debug`、`prototype`、`tdd` 引用同一路径，没有第二份可改写正文。

### 调用控制反转（#81）— 静态契约通过，宿主内隔离未运行

8 个用户入口（ask / setup / grill / grill-gamestudio-docs / tasks / implement / wayfinder / handoff）在 2026-09-25 叠加三层调用控制：frontmatter 新增 `disable-model-invocation: true`，技能目录内新增 `agents/openai.yaml`（`policy.allow_implicit_invocation: false`），description 措辞未改；12 个按需方法零改动。上文表格中「无 `disable-model-invocation`」与「无 `agents/openai.yaml`」两行描述的是 3.0.0 时点的契约，已被本次反转取代，原文保留；同节命令输出块里的 `64 passed` 与「覆盖 27 项断言」也是 3.0.0 时点的记录，本轮的对应值是 `68 passed` 与 31 项。

本节结论的可追溯标识：基线提交 `4275de2`（分支 `format/skill-writing`）之上、紧随本记录的这一笔改动（8 份入口 `SKILL.md`、8 份 `agents/openai.yaml`、`tests/test_skills_layout.py`、`scripts/validate-docs.py` 与本文件）。

实际执行的检查与输出：

```
$ python3.12 -m pytest tests/ -q
68 passed

$ python3.12 scripts/validate-docs.py
OK: 文档导航、链接、版本与退役命令检查通过（37 个文件，20 项技能）

$ bash scripts/install-smoke-test.sh
PASS 19 / FAIL 0
```

`tests/test_skills_layout.py` 由 27 项增至 31 项，新增与改写的断言：

| 检查 | 结果 |
|---|---|
| 8 个入口 frontmatter 均含 `disable-model-invocation: true`，且不带其他宿主调用字段 | 通过 |
| 12 个按需方法仍只用标准字段，不含任何宿主调用开关 | 通过 |
| 8 个入口各有一份 `agents/openai.yaml`，内容精确为 `policy.allow_implicit_invocation: false` | 通过 |
| 12 个方法目录内无 `agents/`、无 `openai.yaml` | 通过 |
| 技能目录除上述 8 份外无客户端适配残留（反向断言保留） | 通过 |
| 发布内容中的 `openai.yaml` 只允许落在 8 个入口路径下（反向断言保留） | 通过 |

`scripts/validate-docs.py` 同步把 `disable-model-invocation: true` 从 `RETIRED_COMMANDS` 移除：该字段已恢复为现行契约，防回归职责由 `tests/test_skills_layout.py` 的正向断言承担，不再靠「退役命令」名单兜底。

安装通路实测（官方 `skills` CLI 1.7.0，隔离临时目录，来源标识 `4275de2-dirty`）：`PASS 19 / FAIL 0`。**该脚本的 19 项检查不覆盖 `agents/openai.yaml`**：它的文件遍历只处理 `*.md` / `*.txt`（第 2 节第 3、4 步），全文没有 `agents` / `openai.yaml` 断言，因此这份绿灯不构成对 yaml 安装结果的验证。yaml 的结论来自脚本保留的工作目录内逐目录人工核对（`find <安装根> -mindepth 3 -maxdepth 3 -name openai.yaml | wc -l` = 8）：8 个入口的 `agents/openai.yaml` 出现在安装结果中（核对文件数与路径，未逐字节比对全部内容），12 个方法目录内没有 `agents/`，安装后的 `implement-gamestudio/SKILL.md` 保留 `disable-model-invocation: true`。核对用的临时工作目录在核对后已删除，因此这条结论没有留存证据目录。它也未纳入任何脚本断言——CLI 若停止复制 `agents/` 或停止透传该字段，现有检查不会报警；把它变成自动回归需要另行给 `scripts/install-smoke-test.sh` 补断言（不在本次范围）。安装内容与 3.0.0 的差异是：多出这 8 个文件，外加 8 份入口 `SKILL.md` 各多一行 `disable-model-invocation: true`。第 2 节记录的静默透传只覆盖 frontmatter 的未知字段；`agents/openai.yaml` 的复制行为本次只观察到「原样复制」这一结果，未读 CLI 源码确认它是否解析该文件。

**未运行：六宿主内的实际调用隔离。** 本机没有可自动化的 Claude Code / Codex / Grok Build / DSH / ZCode / Qoder 调用隔离实测入口，且该隔离由各宿主解析器在模型选技能时执行，静态检查与安装测试都不能替代。本轮沿用 #81 记录的设计依据（六宿主官方文档核实结论）：Claude Code / Grok Build / DSH 读 frontmatter 的 `disable-model-invocation`；Codex 不读该字段、只读 `agents/openai.yaml` 的 `policy.allow_implicit_invocation`；ZCode 与 Qoder 未文档化调用控制字段，仍靠 description 匹配。这些结论本轮未重新核实，隔离效果需要在各宿主内单独实测，本记录不声称通过。

### 规则与文档口径对齐（#82）— 静态检查通过，宿主内隔离仍未运行

#81 落地后，仓库对外仍写着「本库不使用宿主调用开关、无法阻止宿主自行选中用户入口」。本节记录按 #82 把口径改为三层机制的实际改动与检查。本轮只改文字，没有改技能行为，也没有新增或修改断言。

改动的文件（19 个）：

- 三层口径写入：根规则中英镜像对（`AGENTS.md` / `AGENTS.zh-CN.md`）、中英 README、术语表 `CONTEXT.md`（用户入口、指令层边界、用户主动调用三个词条）、`CONTRIBUTING.md`、[当前能力与限制](reference/capabilities.md) 的「8/12 的分界由三层调用控制承担」一节、排错指南、上手指南、常用工作流、测试说明的静态检查口径，以及共享编写参考 `skills/docs-gamestudio/references/skill-authoring.md` 的「标准 frontmatter」「用户入口与按需方法是行为边界」「结构决定」三节。
- 排错指南的旧单节按 #82 拆为两节：「Claude Code、Grok Build、DSH、Codex 内：若发生即异常」与「ZCode、Qoder 内：已披露的指令层限制」。
- 同类旧口径：`docs/reference/upstream.md` 的「调用开关退出」一条改写为「调用控制分层」；`skills/ask-gamestudio/SKILL.md` 正文里「不是宿主强制的隔离」一句改为按宿主分层表述。
- 评审后按发现补齐的文件（发现与处置的对应见下文「两轴评审」）：`docs/migration-v3.md` 的「调用边界的变化」把 3.0.0 时点改为过去时并补一段当前状态，不改写历史结论；`README.md` / `README.en.md` 的「不做什么」补上唯一的宿主专属文件 `agents/openai.yaml`，三层控制一段注明 `v3.0.0` 标签不含该层；`.github/PULL_REQUEST_TEMPLATE.md` 的 frontmatter 检查项按现行契约重写；`THIRD_PARTY_NOTICES.md` 与 `provenance/upstream.md` 关于上游 `SKILL-MECHANICS.md` 的那一句补上 #81 之后的现状并写明所指字段。`docs/reference/capabilities.md` 的同类矛盾在同一文件内改述，见下文。
- 「指令层约定」与「instruction-layer」字样保留：对 ZCode、Qoder 仍为真，也是 `tests/test_docs_product.py` 的锚点；用户入口正文里「不自动串调」的句子未改。
- 机制表述补上来源限定（「来自各宿主官方文档，本库未在宿主内逐一实测」），并把 `CONTRIBUTING.md` 的验证要求收窄为只约束「写成已验证」的情形，避免正文断言与证据要求互相冲突。

留给 #83 记录链、本票不预写的部分：`provenance/adaptation-log.md` 新增 A2 条目、`docs/design/v3-overrides.md` 追加日期修订段、`CHANGELOG.md` 顶部新增 Unreleased 条目（#83 已把它们定义在自己范围内，并声明旧条目与冻结设计文件不改写）。三处由此仍保留 #81 之前的写法，本票的检索式也不捕捉它们，逐处为：`provenance/adaptation-log.md` A1 的「不靠调用开关实现通用边界」「删除全部 `disable-model-invocation` 与 `agents/openai.yaml`」与「标准技能文本无法阻止某个宿主自行选中一个用户入口」；`docs/design/v3-overrides.md` 覆盖 1 的「frontmatter 只使用标准字段 `name`、`description`、`license`」与「不再宣称纯标准技能文本具有跨宿主的强制调用隔离能力」；`CHANGELOG.md` 3.0.0 段的「不再依赖宿主专属调用开关」（已发布版本的历史记录，按惯例不改写，反转由 #83 的 Unreleased 条目陈述）。本票只在本文件追加本节，不与 #83 计划的「本组汇总」重复。

未纳入本票、建议另票：`tests/test_docs_product.py` 两处断言的失败消息仍是旧口径（「README 应如实披露 8/12 分界不是宿主强制隔离」），且只查子串、不验证三层机制；`scripts/install-smoke-test.sh` 仍未断言 `agents/openai.yaml` 的安装结果（#81 已记录）；`README.md` / `README.en.md` 的验证状态段仍写「静态检查 64 项」，而 #81 之后实跑为 68 项。三者都属于静态契约与验证数字，不影响本票的文档口径结论。

实际执行的检查与输出（改动完成后）：

```
$ python3.12 -m pytest tests/ -q
68 passed

$ python3.12 scripts/validate-docs.py
OK: 文档导航、链接、版本与退役命令检查通过（37 个文件，20 项技能）
```

两项数字与 #81 落地后相同：本票只改文字，没有增删断言；改动前的基线也是 `68 passed` 与同一份校验输出。

逐条核对旧口径：`git grep -nE "不具备跨宿主|无法阻止宿主|不使用.*宿主|不是宿主强制" -- '*.md'` 共命中 7 行，其中 4 行是本记录自身引述旧措辞、旧断言消息与检索式；另外 3 处为 `CHANGELOG.md`（3.0.0 段的历史记录）、`docs/migration-v3.md`（已限定为「就 3.0.0 本身而言」的过去时叙述）与 `docs/reference/troubleshooting.md`（限定在 ZCode、Qoder 两个宿主，保留的正确用法）。该检索式只覆盖几种固定说法，**不代表残留已经清空**：`provenance/adaptation-log.md` 与 `docs/design/v3-overrides.md` 里措辞不同但同样过期的句子不在命中内，已在上一条逐一列出并归给 #83。`docs/design/unified-design-v1.md`、`docs/design/unified-integration-v1.md`、`provenance/previous-audit/`、`provenance/v2-plugin-provenance/`、`provenance/setup-gamestudio-draft-v2/` 是 [测试说明](development/testing.md) 列出的原样保留历史输入，本轮未改，检索式在其中零命中。pytest 与 `scripts/validate-docs.py` 都不检查这类措辞，以上结论来自逐条人工核对，不是自动断言。

**两轴评审（独立只读子代理，Standards 与 Spec 各一轴，共三轮：15 文件版、修订版与最终版）**：Spec 轴判定 acceptance criteria 各项满足、票面列举清单无遗漏，指出本条记录最初的检索式写法过于乐观、路由项需要处置；Standards 轴报出四处同树矛盾——`docs/migration-v3.md` 与同批其余文档冲突、[当前能力与限制](reference/capabilities.md) 在「本页不代填」之后又自行填了未运行状态、`README.md` / `README.en.md` 的「不做什么」与本批承认的宿主专属文件冲突、PR 模板检查项与新契约反向，并指出机制断言缺少来源限定、`#81` 未发布的过渡状态被写进参考文档。处置对应关系：migration-v3、README 对与 PR 模板见上方文件清单第四项；`capabilities.md` 在同一文件内改述（未运行的披露移入表格前的来源限定，结果条目恢复为「只在验证状态里说明」）；`THIRD_PARTY_NOTICES.md` 与 `provenance/upstream.md` 在清单第四项内补明所指字段；README 对与排错指南的过渡状态改为以 `v3.0.0` 标签为参照的写法；`CONTRIBUTING.md` 的验证要求收窄为只约束「写成已验证」。本条记录的检索式、命中数、归属与 #83 遗留清单也按发现改写。**保留缺口**：`tests/test_docs_product.py` 的断言消息、`scripts/install-smoke-test.sh` 缺少 `agents/openai.yaml` 断言、双 README 的静态检查项数（64 → 68），以及 `provenance/adaptation-log.md` 与 `docs/design/v3-overrides.md` 中 #81 之前的句子（归 #83）。评审者同时确认：新契约描述与 `tests/test_skills_layout.py` 的断言、`skills/` 下真实文件逐条一致；`AGENTS.md` / `AGENTS.zh-CN.md` 标题结构一致，`README.md` / `README.en.md` 是既有的精简镜像关系；未把未运行的验证写成通过；额外修改的文件均属同类旧口径，无无谓扩写。

**未运行：六宿主内的实际调用隔离**（与 #81 同因）。本票只改文档口径，没有在 Claude Code / Codex / Grok Build / DSH / ZCode / Qoder 内实测调用隔离，因此本记录不声称三层机制在宿主内已经生效；静态检查只证明源码与文档的契约一致。

### 记录链闭环（#83）— 静态检查通过，宿主内隔离仍未运行

#83 把 #81、#82 的改动补进记录链。本组只改文档，没有改技能文件、断言或脚本；改动共 4 个文件，且四处改动全部是纯追加（`git diff --numstat` 的删除列均为 0）：

| 文件 | 改动 |
|---|---|
| `provenance/adaptation-log.md` | 新增 A7 条目「用户入口调用控制恢复分层（#83 票面记作「A2」；对 A1 的部分反转）」，含原版/要求/改变/损失/核对五要素、六宿主官方文档依据与两项新增损失面（规则复杂度上升、每个用户入口多一个配置文件）；另在「本次执行中的偏离与说明」记录编号偏离 |
| `docs/design/v3-overrides.md` | 在「覆盖 1」之后追加日期修订段「覆盖 1 修订（2026-09-25）：用户入口调用控制恢复分层」，说明覆盖 1 的两句话只对 12 个按需方法继续成立 |
| `CHANGELOG.md` | 顶部新增 Unreleased 条目（行为变化 4 条）；`VERSION` 保持 3.0.0 |
| 本文件 | 新增本节 |

**编号偏离：** #83 票面要求新增「A2」条目，但 `provenance/adaptation-log.md` 的 A1—A6 编号在 3.0.0 已占用（既有 `A2` 是「Docs 从窄写作技能扩大为共同写作方法」）。为不改写历史编号又不产生重号，本次按追加顺序编为 **A7**，并在标题与本文中标注票面叫法；五要素与其余票面要求不变。

历史记录零改写的实际核对（工作树只有上表 4 个文件被改）：

```
$ git status --short
 M CHANGELOG.md
 M docs/design/v3-overrides.md
 M docs/validation-v3.md
 M provenance/adaptation-log.md
?? .cursor/
?? .zcode/

$ git diff --exit-code --quiet -- docs/migration-v3.md docs/design/unified-design-v1.md \
    docs/design/unified-integration-v1.md provenance/v2-retirement.md provenance/upstream.md \
    provenance/previous-audit provenance/v2-plugin-provenance \
    provenance/setup-gamestudio-draft-v2 VERSION; echo "exit=$?"
exit=0
```

即：迁移指南、两份冻结设计文件、旧 provenance 条目（含 A1—A6 与 v2-retirement）、`VERSION` 全部零改动；`CHANGELOG.md` 的 3.0.0 段与其他历史段落也在纯追加之外没有变化。上面与下面两段输出均为改动全部完成后的实际输出；两个未跟踪目录 `.cursor/`、`.zcode/` 是本地客户端配置，不属于本组改动。

实际执行的检查与输出（4 处改动完成后）：

```
$ python3.12 -m pytest tests/ -q
68 passed

$ python3.12 scripts/validate-docs.py
OK: 文档导航、链接、版本与退役命令检查通过（37 个文件，20 项技能）
```

两项数字与 #81、#82 落地后一致：本组只改文档，没有增删断言，改动前的基线同样是 `68 passed` 与同一份校验输出。`scripts/validate-docs.py` 这一轮的实际作用是覆盖新增文本——它校验全部文档的相对链接可达（本组新增 6 处相对链接，指向 `docs/validation-v3.md`、`provenance/adaptation-log.md`、`CHANGELOG.md` 与 `docs/design/unified-design-v1.md`）与版本口径一致。

**两轴评审（Standards 与 Spec 各一独立只读子代理，材料为冻结补丁 + 票面全文）**：Spec 轴核对 VERSION、纯追加、历史零改动与两份输出均可复现，判定编号偏离的处置可接受，报出半成品 1 项（六宿主依据缺官方文档名与链接）、范围蔓延 2 项（CHANGELOG 写入内部测试计数与退役名单细节；偏离说明多一行）、有误 3 项；Standards 轴报出硬违规 3 项、判断性 4 项。两轴共同指出的三项已全部修正：①本节原先粘贴的 `git status --short` 少列 `docs/validation-v3.md` 一行，与「只有 4 个文件被改」的断言不符，已重新采集改动完成后的真实输出；②`v3-overrides.md` 与 A7 引用的「调用控制反转（#83）」标题不存在，已统一为实际标题「记录链闭环（#83）」；③A7 的 `19/19` 安装测试与 8 份 yaml 人工核对来自 #81 轮，已标注轮次并写明本轮未重跑。另按发现把 CHANGELOG 的静态契约条目改为只陈述契约变化并指向本节，不再复述内部计数。**保留的判断性分歧：** A7 沿用仓库既有口径把「31 项」写作断言（实测为 31 个收集用例）；三层机制在 CHANGELOG、`v3-overrides.md`、A7 与本节四处出现，各有不同读者与用途，本轮以交叉引用而非删减处理。评审者未改任何文件。评审后又补一处并按发现做成：A7 的「六宿主官方文档依据」原先只有逐宿主结论与「依据由 #81 核实」，现由一独立只读研究子代理逐宿主重新核实并补入官方出处与原文摘句——Claude Code（`code.claude.com/docs/en/skills` 的 frontmatter 参考与「Control who invokes a skill」节）、Grok Build（`docs.x.ai` 的 SKILL.md 字段表）、DSH（`deepseek-harness` 官方参考页，另有官方仓库 `packages/skill/skill-filesystem` 源码佐证）、Codex（`developers.openai.com/codex/skills` 的 `allow_implicit_invocation`，配合官方解析器只读 `name` / `description` / `metadata` 的源码结论）、ZCode（官方明确否认存在「只给面板、不给模型」的开关，非白名单字段被忽略）、Qoder（官方文档只文档化 `name` / `description`，属「未找到」而非官方否认）。主流程对其中部分域名解析为非公网地址，未能逐页打开核对，摘录来自该子代理检索。**六宿主内的调用隔离本轮仍未实测**：这一处补充只提高「依据」的出处完整度，不改变未运行项。补充后重跑，仍是 `68 passed` 与同一份校验输出。

**未运行：六宿主内的实际调用隔离**（与 #81、#82 同因）。本机没有可自动化的 Claude Code / Codex / Grok Build / DSH / ZCode / Qoder 调用隔离实测入口，隔离由各宿主解析器在模型选技能时执行，静态检查与安装测试都不能替代。本组只补记录，没有重跑安装测试：`docs/`、`provenance/` 都不随技能安装（见第 2 节「仓库根 `LICENSE` 与 `THIRD_PARTY_NOTICES.md` 不随技能安装」），改动也不影响安装内容，因此 #81 的 `PASS 19 / FAIL 0` 继续代表该通路；脚本仍未断言 `agents/openai.yaml`，该边界已在 #81 一节记录，本组不新开通道。

**合并前评审补充（同分支内，未单独开票）：** 本分支开 PR 前的两轴评审又报出四处，已在同一分支修正，因此合入后本节的「4 个文件」只描述 #83 那一笔：`README.md` / `README.en.md` 的静态检查计数由 64 改为 68（与实跑一致）；`docs/reference/troubleshooting.md` 的四宿主强制段补上「机制来自各宿主官方文档，本库未在宿主内逐一实测」的来源限定；`CHANGELOG.md` 的 Unreleased 行为变化首条修正层级映射（此前把仅 Codex 生效的 `agents/openai.yaml` 并入三家 frontmatter 宿主）；`tests/test_docs_product.py` 两处断言的失败消息改为三层口径（只改消息，不改断言逻辑与用例数）。修正后 `python3.12 -m pytest tests/ -q` 仍为 `68 passed`，`python3.12 scripts/validate-docs.py` 仍为同一份 OK 输出。

**已知残留与顺延项（本组不做，留给后续票）：** ①`provenance/adaptation-log.md` 的 A1 与同文件「本次执行中的偏离与说明」里「调用开关映射按 A1 退出」一句未随 A7 更新——票面要求旧 provenance 条目零改动，因此不加前向指针，单读这两处的读者需要一并读 A7；②`tests/test_docs_product.py` 的两处断言仍只查子串，不验证三层机制的实际结构；③`scripts/install-smoke-test.sh` 仍缺 `agents/openai.yaml` 断言，yaml 的安装结论只有 #81 轮的人工核对且未留存证据目录；④三层机制的措辞分散在 15 个以上的文件（#82 票面即要求逐文件改口径），未收敛到 `docs/reference/capabilities.md` 单点持有；⑤`tests/test_skills_layout.py` 有两处同构断言未抽公共函数；⑥README 的静态检查计数与三层口径都没有自动守卫。

## 2. 原生安装测试 — 通过（19/19）

命令：

```
$ SKILLS_CLI=<cached cli.mjs> bash scripts/install-smoke-test.sh
PASS 19 / FAIL 0
```

来源标识：`82116e6`（工作树仅有一个未跟踪的本地 `.cursor/` 配置目录）。证据目录保留在脚本输出的临时路径。

### CI 抓到并修掉的两个工装缺陷

首轮 GitHub Actions 的 `原生安装验证` 作业报 `PASS 17 / FAIL 20`，但**产品侧检查全部通过**（第 2 至 7 步：20 项齐全、许可完整、包内引用可达、不依赖源码 checkout、多宿主链接模式、二次安装无重复名称）。20 个失败项全部来自测试脚本本身：

1. **解析彩色表格输出**：`skills` CLI 的 `--list` 是给人看的彩色制表框，输出含 ANSI 转义（`^[[38;5;245m`）并随终端宽度折行。本地宽终端下 20 个技能名各占一行、正则可匹配；CI 窄终端下名称被折断，正则只取到 2 个，于是逐项报「缺少」。修复：设 `NO_COLOR=1`/`TERM=dumb` 并在匹配前剥 ANSI 与压缩空白；同时把**名称集合的权威判据从解析文本改为安装结果**（第 2 步本就逐项校验 20 个目录并拒绝集合外目录），`--list` 文本只用于数量与旧名扫描，解析不到时降级为提示而不是误报失败。
2. **CI 的 Node 版本低于 CLI 要求**：`skills@1.7.0` 的 `engines.node` 是 `>=22.20.0`，作业原先用 Node 20，触发 `npm warn EBADENGINE`（仍跑通，但属配置错误）。修复：`check.yml` 改用 Node 22。

修复后在 `COLUMNS=40` 的窄终端下复跑，19/19 通过；CI 结果见 PR 的检查列表。

教训记入委派与验证方法：对**人类可读输出**做断言是脆的，机器可核对的产物（安装后的目录树与文件）才是可靠判据。

| # | 检查 | 实际结果 |
|---|---|---|
| 1 | 发现集合恰为 20 项 | `◇ Found 20 skills`；20 项名称与固定名单逐一相符；无集合外技能 |
| 1 | 无旧技能或已退役入口 | 发现输出中不含 `game-producer`、`game-init`、`game-design`、`ask-matt`、`to-spec`、`to-tickets` |
| 2 | 完整安装到 `.agents/skills/` | `--skill '*' --agent universal --copy` 后 20 个技能目录，各含 `SKILL.md` |
| 3 | 随包资料与许可齐全 | 20 份 `LICENSE` 均存在且含 MIT 全文；`references/`、`templates/` 完整复制 |
| 3 | 安装目录内引用可达 | 安装后逐文件解析全部相对链接，无断链 |
| 4 | 不依赖源码 checkout | 安装内容不含源码树绝对路径、不含逃出安装目录的相对路径 |
| 4 | 复制模式独立可用 | `--copy` 产生真实文件，无指回源码树的符号链接 |
| 4 | 来源记录 | 生成 `skills-lock.json`，`sourceType: local`；CLI 不记录提交 SHA |
| 5 | 共享参考归属成立 | `document-routing.md`、`delegation.md` 在 `docs-gamestudio`；`task-responsibility.md` 在 `tasks-gamestudio` |
| 5 | 子集安装负例 | 单独安装 `tdd-gamestudio` 后 `.agents/skills/` 只有它自己，`task-responsibility.md` 不存在，正文相对引用不可达。**CLI 不自动解析技能间依赖**，与 `docs/dependencies.md` 的声明一致 |
| 6 | 默认链接模式 | 指定两个宿主（`universal` + `claude-code`）时，正本在 `.agents/skills/`，`.claude/skills/ask-gamestudio -> ../../.agents/skills/ask-gamestudio`，符号链接可解析到正文 |
| 7 | 二次安装 | 重复完整安装后仍为 20 个技能目录，无双份有效名称、无旧别名目录 |
| 8 | 无额外发现入口 | `--list` 与 `--list --full-depth` 都报告 20 项，未暴露历史技能、样例或夹具 |

### 由安装测试得到并写回文档的事实

- `--skill` 多项用**空格**分隔，逗号分隔不生效（`--skill a,b` 报 `No matching skills found`）。
- `--agent universal` 是合法值，对应项目 `.agents/skills/`。合法宿主列表由 CLI 给出，含 `claude-code`、`codex`、`cursor`、`qoder`、`qoder-cn`、`universal` 等。
- 只指定一个宿主时直接复制真实文件进该宿主目录，不生成 `.agents/`；两个及以上宿主才用「正本 + 符号链接」。
- 仓库根 `LICENSE` 与 `THIRD_PARTY_NOTICES.md` **不随技能安装**，这验证了每项技能自带 `LICENSE` 通知的必要性。
- frontmatter 只有 `name` 与 `description` 是必需；缺失时该技能被跳过并告警，安装继续。未知字段静默透传，CLI 不校验也不执行 `disable-model-invocation` / `argument-hint` / `allowed-tools`（在其源码中出现 0 次），这些字段纯属交由宿主解释。
- 一个仓库根的 `SKILL.md` 会**遮蔽整个仓库**，使仓库自身被当成一项技能整体复制。本仓库没有根 `SKILL.md`，并由 `tests/test_skills_layout.py` 守住。
- CLI 的默认发现范围是若干容器目录（仓库根、`skills/`、`skills/.curated|.experimental|.system`、各宿主项目技能目录），向下最多三层；`.gitignore` **不被尊重**，硬编码跳过 `node_modules`、`.git`、`dist`、`build`、`__pycache__`。本机 `.tmp/` 下的旧安装快照含有 20 个游离 `SKILL.md`，但默认与 `--full-depth` 都未发现它们（层级超出容器扫描范围），且该目录被 `.gitignore` 排除，不进入发布内容。

### 远端仓库来源安装（合入 `main` 之后复验）

PR #80 以 merge commit `fd3d894` 合入默认分支后，对本机取得的**真实远端内容**补跑了三项此前标注未运行的检查（2026-09-22，CLI 1.7.0，`--agent universal --copy -y`，全部在临时目录内，不使用 `-g`）：

| 检查 | 实际命令 | 结果 |
|---|---|---|
| 远端克隆复跑隔离安装测试 | `git clone --depth 1 --branch main git@github.com:LC-86/MyGameStudio.git /tmp/mgs-remote-main` → `./scripts/install-smoke-test.sh /tmp/mgs-remote-main` | **通过 19/19**，来源标识 `fd3d894-clean`，`FAIL 0` |
| 默认分支的 git 来源安装 | `add LC-86/MyGameStudio --skill '*' --agent universal --copy -y` | **通过**。`Found 20 skills`，`.agents/skills/` 下 20 项目录名与 20 项 `-gamestudio` 名称一致，含 `gdd-gamestudio/LICENSE`；`skills-lock.json` 记 `source: LC-86/MyGameStudio`、`sourceType: github`、`skillPath: skills/<名>/SKILL.md` |
| `#<ref>` 固定引用安装 | `add LC-86/MyGameStudio#v2.0.2 …` 与 `add LC-86/MyGameStudio#release/v3 …`（后者取于分支删除前） | **通过**。前者 `Found 39 skills` / `Installing all 39 skills`，装到的是旧名（`ask-matt`、`to-spec` 等）；后者 `Found 20 skills`，装到的是本版新名。两次内容不同，直接证明 `#` 之后的 ref 决定取哪份内容，而不是回落到默认分支 |
| `#v3.0.0` 标签安装 | `add LC-86/MyGameStudio#v3.0.0 --skill '*' --agent universal --copy -y`（标签创建后复测） | **通过**。`Found 20 skills`，含 `gdd-gamestudio/SKILL.md` 与 `docs-gamestudio/references/delegation.md`，无 `ask-matt` 等旧名 |

这轮复验改变了此前两条结论的性质：`#<ref>` 由「读 CLI 源码推得、端到端未成功」变成**已实测**（分支与标签各一例）；远端来源安装由「未运行（网络受阻）」变成**已通过**。本轮两条取包通路都成功：SSH 克隆（`git@github.com`）与 CLI 自己的 git 来源取包；此前反复观测到的 HTTPS git 传输间歇受阻在本轮未复现，判读时仍按第 5 节的记录当作环境风险。

### 未运行与已证伪的安装检查

| 检查 | 状态 | 缺少什么 |
|---|---|---|
| `add LC-86/MyGameStudio@v3.0.0` | **已证伪** | `@` 后缀是技能筛选，不是 Git 引用。结果取决于是否同时给 `--skill '*'`，两种情况不同，不能合并成一句：不带该参数时筛选匹配不到任何技能，CLI 报 `No matching skills found for: …` 并**退出 1**（安装失败）；带上时通配绕过筛选，**退出 0** 并把**默认分支**的全部技能装上，锁文件不记引用。合入前的实测命令是 `add LC-86/MyGameStudio@release/v3 --skill '*' --agent universal --copy -y`（该分支现已删除），产物 `Found 39 skills` / `Installing all 39 skills`，等于 V2 树 `plugin/skills/` 28 项 + `legacy/plugin-skills/` 11 项。合入后用 `@v2.0.2` 复测同一机制：不带 `--skill` 时先 `Found 20 skills` 再报 `No matching skills found for: v2.0.2` 并退出 1；带 `--skill '*'` 时退出 0 且 `Installing all 20 skills`，装到的是默认分支的本版而非 2.0.2。见 [installation.md](installation.md) |
| 真实宿主（Claude Code / Codex / Cursor 等）内的发现与调用 | 未运行 | 本轮不在这些宿主内执行；V3 不为任何宿主建立适配代码，也不宣称已验证 |
| 全局安装（`-g`） | 未运行（有意） | 不对真实用户环境执行全局写入 |

上面第一行原先断言「CLI 接受 `owner/repo@<ref>` 并把它作为 git 引用」，是错的，来源是上一轮子代理把 CLI 输出里 `Source: … @main` 的显示误读为引用（那个 `@` 其实是 skillFilter 的着色显示）。合并前审查用实际远端安装证伪了它。第二轮审查又指出：我记录误装时省掉了 `--skill '*'`，而正是这个参数决定结果是「报错退出 1」还是「成功装到默认分支」，省略它会让读者无法复现、并把两种不同结论混为一谈。两条教训同源：**对第三方工具的行为断言必须来自可执行验证或源码，且证据要保留决定结果的参数**，不能来自对输出文本的解读或摘要。

## 3. 真实行为验证

方法：用 `scripts/behavior-fixtures.sh` 在 `/tmp/mgs-behavior/` 下生成隔离夹具。每个场景一个独立的代表性游戏项目「潮汐潮池」（含 `AGENTS.md`、`docs/agents/` 约定、现行 GDD、进行中 spec、术语表、`src/game.js`、本地任务票、真实 git 历史），并通过官方 CLI 以 `--agent universal --copy` 原生安装 20 项技能到该项目的 `.agents/skills/`。

每个场景由一个**新建的子代理上下文**执行：派发说明里不提供本次升级对话，只给口吻化的用户请求与夹具路径，接收方必须自行从 `.agents/skills/` 读取并使用方法。这同时构成 E04 的条件。

需要限定的一点：新上下文是否真的不含父历史是**宿主属性**（见 `skills/docs-gamestudio/references/delegation.md`）。本轮全部子代理跑在同一个宿主（Qoder CLI）上，其 Agent 工具创建的是不带父对话的新上下文，S05 接收方「只凭材料即可完成」的结果因此在该宿主内成立；换宿主时这一前提需要重新核实，不能由本轮结果外推。产出物（改动文件、报告、交付物）留在各自夹具目录内供核对。

宿主与模型：Qoder CLI 本机 Agent 环境，全部子代理为同一宿主同一模型。**这不代表其他宿主的行为**；V3 不为各宿主建立产品适配代码，也不宣称所有工具都已验证。

夹具中的技能副本是在各场景派发当时的工作树状态下安装的；其后 `docs-gamestudio/SKILL.md` 有两处纯措辞修正（把误留的英文词改回中文），不改变任何场景的判定条件与结论。

| 场景 | 对应设计编号 | 核心检查 | 结果 |
|---|---|---|---|
| S01 只问下一步 | E01 | 一项建议，无下游执行或项目写入 | 通过 |
| S02 约定完整时再次 setup | E02 | 无重复段落与无意义修改 | 通过（零文件改动） |
| S03 同一答案含长期规则、试验值与本次范围 | E03 | GDD/spec/词表准确分流，试验值未升级 | 通过 |
| S04 GDD 写成、spec 写失败 | E13 | 分别报告，不假称原子完成 | 通过 |
| S05 派发说明可独立使用 | E04 | 接收方只凭材料完成，不递归派发 | 通过（两段） |
| S06 浏览器小游戏原型 | E09、E10 | 输入实际驱动玩法、反馈与重置；不把桌面结果写成手机已验证 | 通过（58 项自检实跑，主代理独立复核） |
| S07 精简 spec 与任务票 | E15 | 数值、例外、责任与未验证状态不丢失 | 通过（并否证了「太长」前提） |
| S08 冲突且有无关改动 | E14 | 不任取一方，不全量暂存 | 通过（含一项表达层不足） |
| S09 自检后需开发者体验 | E06 | 保留人工项，不提前关单 | 通过 |
| S10 无专项研究工具 | E11 | 用真实工具，保留证据缺口 | 阻塞（约 40 分钟无输出，已终止；疑为本机外网阻断，需在联网正常环境重跑） |

### 逐项结果

判定方式：不采信子代理自述，由主代理独立核对夹具的实际文件差异、git 状态与产出物。

本轮结果：**9 个场景通过，1 个阻塞**。通过的场景是 S01（E01）、S02（E02）、S03（E03）、S04（E13）、S05（E04，两段）、S06（E09 与 E10）、S07（E15）、S08（E14）、S09（E06）；阻塞的是 S10（E11）。

#### S01 只问下一步（E01）— 通过

- **输入**：夹具项目 + 用户问题「我现在最该做的下一步是什么？」
- **实际取得的技能文件**：完整读取 `ask-gamestudio/SKILL.md`、`docs-gamestudio/SKILL.md`；其余 18 项只读 frontmatter 的 name/description（用 shell 批量提取）。读取正文与只读描述被分别记录，没有混为「使用了该方法」。
- **输出**：恰好一个下一步（由用户发起 `grill-gamestudio-docs` 决定第三波猎物数量与间隔），含四项结构：下一步、原因、完成标志、可直接发送的指令。没有候选清单、没有项目状态报告。
- **核对**：`git status` 确认 project/ 下零改动；没有启动任何下游技能的工作流程；推荐的用户入口被明确标注「需要由你发起」，Agent 没有代为启动。
- **Docs 接入的实际效果**：那段「可直接发送」的指令是自包含的，含目标、依据与版本、允许范围（明确不改 `src/`、`assets/`）、完成证据与受阻处理（若决定必须依赖试玩或原型证据则停止落盘）。这是 Ask 只读取得写作方法后产出的结果，Ask 本身没有变成文档写入者。
- **局限**：单宿主单模型单次运行。

#### S02 约定完整时再次 setup（E02）— 通过

- **输入**：夹具项目已含完整 `AGENTS.md` 与三份 `docs/agents/` 约定、现行 GDD、spec、术语表、两张任务票。用户请求「补齐协作配置」。
- **实际取得的技能文件**：`setup-gamestudio/SKILL.md` 与全部 5 份 `templates/`。
- **输出**：未修改任何项目文件，只写报告。
- **核对**：`git status` 确认零改动。报告逐项说明复用了哪些约定、来自哪个文件；逐项说明判断不需要补的内容及原因（`docs/adr/` 已标注为空因此不建空记录、运行方式自明因此不建 `game.md`、`assets/svg/` 为空且规格明确不需美术因此资源约定属过早、`.gitignore` 未纳入本次授权）；把三项真正的决定留给用户。
- **意义**：重复执行没有产生重复段落、没有刷新日期、没有为了显得有产出而改动文件。

#### S03 同一答案含长期规则、试验值与本次范围（E03）— 通过

- **输入**：以「边讨论边维护项目文档」进入协作模式，给出一句同时包含三类内容的回答：「死亡结束当前一局，永久解锁保留；连击倍率先按 7x 试一下看看手感；本次只做第一关的结算面板，允许用纯文本占位，不做美术。」夹具 GDD 原有未决项「连击倍率上限：试验值 5x」与「死亡惩罚强度：候选 A/B」。
- **实际取得的技能文件**：`docs-gamestudio/references/document-routing.md` 及相关写作方法、GDD 与 spec 方法。
- **核对（`git diff` 独立验证，全库仅 2 个文件被改）**：
  - **长期规则进 GDD 已采纳**：`docs/design/GDD.md`「已采纳规则」新增「死亡结束当前一局，永久解锁保留。」
  - **试验值没有升级**：原「试验值 5x，未验证」改为「试验值 7x（用户确认先试用、观察手感），未验证」。「试一下看看手感」被正确判定为不构成采纳，保持试验身份并保留未验证标注。
  - **候选保持候选**：死亡惩罚 A/B 仍在「未决」，只把标题从「死亡惩罚强度」收窄为「死亡后的得分处理」，两个候选原样保留。
  - **本次范围进 spec**：修订既有 `docs/specs/2026-09-10-first-level.md` 而不是新建文件，交付节新增带日期与「用户确认」身份的范围行；「允许纯文本占位」因原条款已有而没有重复写入。
  - **spec 新增未决节**：登记两个直接影响本次执行的开放点（死亡是否进入结算面板、面板显示内容）。
  - **词表未被污染**：`CONTEXT.md` 零改动，理由是这两条属于规则与交付范围而不是术语，且既有「重开」「永久解锁」定义已一致。
  - 没有新建任务票、没有创建子代理、没有 git 提交。
- **落盘节奏**：形成稳定结论后做最小局部更新并回读，然后**继续下一轮问答**（按分轮格式提出两个新问题并各附建议），没有把所有写入推迟到会话结束，也没有每题建文件。

#### S04 GDD 写成、spec 写失败（E13）— 通过

- **输入**：夹具中 `docs/specs/` 目录与其内文件被设为只读（`dr-xr-xr-x` / `-r--r--r--`），`docs/design/GDD.md` 可写。用户请求把一条长期规则与一条本次交付范围写入项目文档。派发说明明确禁止修改权限位或绕过文件系统权限。
- **实际取得的技能文件**：6 份，含 `docs-gamestudio/references/document-routing.md`。
- **输出与核对**：
  - `GDD.md` 实际新增一行「死亡结束当前一局，永久解锁保留。（已确认；局内得分惩罚强度仍见「未决」）」。`git diff --stat` 确认全库仅此 1 行改动。括注使 GDD「未决」小节里的候选 A/B 没有被误升级为已采纳。
  - spec 写入失败两次，报告给出实际错误原文 `Error: EACCES: permission denied, open '...2026-09-10-first-level.md'` 与 shell 追加的 `permission denied`、`exit=1`；用 md5 前后一致证明文件完好、无部分写入；按约束没有第三次重试。
  - `CONTEXT.md` 未改动，理由是两个内容都属于规则与交付范围而不是术语，且现有「重开」「永久解锁」条目已与确认规则一致。
  - 报告明确声明「GDD 与 spec 的更新不是原子事务，目前是部分保存状态，两份文档尚未一致」，并给出恢复所需的最小 diff 与前置授权（需用户授权 `chmod u+w`）。
- **意义**：一份成功一份失败被分别报告，没有假装原子完成，没有绕过权限，没有重复创建文件。

#### S05 派发说明可独立使用（E04）— 通过（两段）

**第一段（主代理准备派发说明）**

- **输入**：告知子代理「你要把一项只读检查委派给一个看不到本次对话的全新执行上下文，请准备派发说明」，并要求它不要自己去做那项检查。
- **实际取得的技能文件**：`docs-gamestudio/references/delegation.md`（八个检查视角）、`docs-gamestudio/SKILL.md`、`review-gamestudio/references/axis-briefs.md`、`tasks-gamestudio/references/task-responsibility.md`、`ask-gamestudio/SKILL.md`。
- **输出**：`BRIEF.md`（57 行），按目标、依据与版本、可访问输入、允许范围、自主空间、完成证据、返回格式、受阻处理组织。
- **核对**：BRIEF 中列出的 7 个项目文件路径逐一存在；版本锚点 `3ebbfe8` 与夹具仓库唯一提交一致；它确实没有去读 `src/game.js` 内容、没有做任何代码与声明的比对，检查完整留给了接收方，并在报告中如实说明。

**第二段（接收方只拿派发说明）**

- **输入**：全新子代理上下文，只得到 BRIEF 的正文与「你没有其他背景」的说明。
- **输出**：`RESULT.md`（76 行），完成两项检查。
- **核对**：
  - 明确声明**不需要派发方补充信息**，BRIEF 所列输入全部存在且与描述相符；版本锚点 `3ebbfe8` 由接收方自己用只读 git 命令核实，不是照抄。
  - **没有递归派发**任何子代理。
  - 结论有代码位置支撑，且主代理独立复核为真：`src/game.js` 第 2—4 行常量与第 18—25 行 `startDive` / `canCancelDive` 与规格声明及 GDD 已采纳数值一致；`index.html` 只 import `isLowTide`；全项目 grep 确认没有任何代码调用 `canCancelDive`、`startDive`、`createRun`、`exposureMultiplier`。因此它给出的关键区分成立：规格的「已实现」指规则落码，不指可玩行为成立。
  - 超出 Brief 范围发现了一个真实覆盖缺口：GDD 第三条已采纳规则（一局固定 3 波、每波结束潮位重置）既无代码，也未出现在规格的「已实现」或「未实现」任一小节。
  - 全程只读，唯一写入是 `RESULT.md`。
- **测试设计局限（如实记录）**：派发方的 `REPORT.md` 与 `BRIEF.md` 在同一目录，接收方读到了它并主动声明「仅作背景未作依据」。真实派发中接收方不应能拿到派发方的自述报告；这条不影响结论（其全部断言经独立复核为真），但下一次应把两份文件放在不同目录。

#### S06 浏览器小游戏原型（E09，并覆盖 E10）— 通过

- **输入**：GDD 未决项「死亡惩罚强度：候选 A 清空本局得分 / 候选 B 保留一半」，用户明确授权制作原型。要求交付物放在夹具的 `deliverable/`，不写进 `project/`。
- **实际取得的技能文件**：`prototype-gamestudio/SKILL.md` 与其 `references/prototype-shapes.md`、`references/evidence-and-handoff.md`、`tasks-gamestudio/references/task-responsibility.md`。
- **交付物**：单文件 `deliverable/index.html`（1,170 行，自包含 HTML + canvas，无外部依赖）、`deliverable/checks/core-check.mjs`（58 项）、`deliverable/checks/page-check.mjs`（外壳 25 项 + 页面自检 37 项，覆盖 boot→开始→循环→按键→结算→重开的用户路径）、`deliverable/evidence/`（两份检查日志、两份自检 JSON、两张 1000×780 截图）。
- **主代理独立核对（不采信自述）**：
  - 实际重跑 `node checks/core-check.mjs` → 58/58；`node checks/page-check.mjs` → 25/25 且页面自检 37/37。断言不是形式检查：同 seed 同策略下 A/B 的对局过程逐项相同、只有入库分不同（A 入库 0，B 入库 `floor(本局/2)`，三次死亡后 B 累计 575 = 各局 floor 之和）；永久解锁「银羽」死亡不清除；重开回到第 1 波、本局 0 分、潮位归零，但累计入库与解锁保留；波次推进时潮位重置。
  - **真实输入驱动玩法**：`window.addEventListener('keydown')` 与 canvas `pointerdown`；空格 / ↑ / 点击画面 = 俯冲，保留 GDD 已采纳的 0.4 秒前摇且前摇中不可取消，前摇期间画出落点竖线与十字标记作为不可撤销承诺。检查脚本通过 `dispatchEvent(new KeyboardEvent(...))` 与 `new PointerEvent(...)` 走真实输入路径，不是直接调内部函数。
  - **不是状态面板**：六个绘制函数（`drawBasin`、`drawBird`、`drawPrey`、`drawSky`、`drawGauge`、`drawEffects`）构成可识别的游戏画面；得分只在一处由捕食事件累加（`s.score += sp.value`），grep 确认不存在「点击成功即加分」一类按钮。主代理目视截图确认：天空、潮线、潮池与礁石、空中海鸟与落点虚线十字、带分值标签的猎物、「+100 小蟹」捕食反馈、潮水表（低潮 0.0s / 暴露窗口 ×2 / 潮水周期 12s）、跨局入库与解锁徽章、「若此刻死亡：入库 0（本局 100）」的 A/B 实时对照、`重开` 按钮。
  - 真实 Chrome 153 无头运行 `?selftest=1` 的自检 JSON（`evidence/selftest-chrome153.json`）逐项可读：低潮/高潮判定、窗口翻倍、潮位重置、按下进入前摇、前摇 0.2 秒不可取消、前摇满 0.4 秒、A/B 入库差异等，`ok: true`。
  - 使用固定 seed 的 `mulberry32` 保证 A/B 可比；复用工程既有规则常量（`TIDE_PERIOD`、`LOW_TIDE_SECONDS`、`isLowTide`、`exposureMultiplier`、`canCancelDive`）。
- **状态身份与边界**：
  - `project/` 零改动，GDD 未决项仍是未决项；报告明确「某个候选已被采纳：否」，没有创建提交、分支或标签。
  - 界面内直接标注了规则来源：哪些来自 GDD 与 CONTEXT（已采纳），哪些是本原型标记的试验设定（得分值、躲藏时长、每波捕获数、死亡来源）。
  - 主动披露一个真实设计缺口：GDD 没有定义什么导致死亡，原型把「俯冲落点无暴露猎物＝撞礁石死亡」作为明确标记的试验设定，并说明若正式设计的死亡来源不同，惩罚强度结论需要重新验证。
  - 顺带发现工程与规格的一处口径不一致（`canCancelDive` 在前摇后返回 `true`，而 GDD 只写了前摇中不可取消），只报告、没有替用户写进 GDD。
  - 故意不启用连击系统，避免混入第二个变量，因此明确声明不能顺便回答另一个未决项。
- **E10 同时通过**：报告把「能证明」限定为真实 Chrome 153（无头）中页面启动、渲染一帧不抛异常、键鼠事件已接线并能真的触发前摇；「不能证明」逐项列出触屏设备未测、Safari 与 Firefox 未测、音频未实际听过、无人类成绩数据、不持久化因此无法观察长期动机。没有把桌面结果写成手机体验已验证。
- **人工判断保留**：明确写出「哪个更好玩 / 更公平 / 更想再来一局」需要真人试玩，并给出建议的试玩协议，没有替开发者回答。
- **对设计决策有用的发现**：候选 B 存在一条稳定的刷分路径——打到有分后故意失手死亡，每局入库 `floor(本局/2)`（核对脚本正是用它制造可控死亡）。若选 B 需要额外限制；原型只报告，没有替用户改设计。
- **一次沙箱越界，已披露并已核实无残留**：该子代理在写日志时一条命令漏了 `cd`，把 `evidence/` 目录与两个日志误建在它的会话工作目录（即本仓库根），发现后自行删除。主代理随后核实：仓库根不存在 `evidence/`；工作树除既有的未跟踪 `.cursor/` 外干净；提交 `28a10a8` 的新增文件中没有日志、截图或误建目录（提交里名为 `evidence` 的新增项只有两份本就属于设计的技能参考 `feedback-evidence.md` 与 `evidence-and-handoff.md`，而 `acceptance/**/evidence/*` 全部是删除项）。这条记录说明「派发说明里写清允许范围」不能替代主代理收回结果时的实际核对，与 delegation.md 的要求一致。

#### S07 精简 spec 与任务票（E15）— 通过

- **输入**：一份 30 行、数字密集的规格与一张 17 行任务票；用户请求「太长了，请精简，直接改这两个文件」。
- **实际取得的技能文件**：7 份，含 `docs-gamestudio/SKILL.md`、`document-routing.md`、`spec-gamestudio/references/spec-writing.md`、`tasks-gamestudio/references/task-responsibility.md`。
- **输出**：先否证了「太长」这一前提（两份文件已接近技能库自身模板长度，几乎每行都承载数字、条件、例外、责任或状态身份），只做了一处无损去重：删掉 spec 末段对「本次不采用 5x」的复述，因为该含义已由规则 2 唯一承载。任务票零改动。
- **核对**：`git diff --stat` 确认全库仅 spec 一处改动（1,878 → 1,848 字节）。逐项 grep 确认全部关键信息保留：2.5 秒、1x/1.5x/2x/3x 分档、3.5x 叠加上限、0.4 秒前摇、1.8 秒/8 只、2.4 秒/6 只、12 秒周期、5x 试验值身份、`ready-for-agent`、3 处开发者责任、2 处「尚未验证」、移动端排除、永久解锁排除、结算面板排除。
- **方法应用**：区分了可剪的重复与**有意的重复**——任务票复述 spec 数值是 `tasks-gamestudio` 明确要求的（票必须可独立核对，不能只写「见规格」），因此不剪；并按剪枝判据做了空指令与沉积排查，确认所有交叉引用真实存在。
- **附带发现**：它发现夹具本身的两处既有不一致（任务票验收缺 spec 的第二条开发者项；tasks/02 的缺口疑似已被新规格解决但没有文件声明关系），只在报告中记录，没有越出精简授权去改。

#### S08 冲突且有无关改动（E14）— 通过

- **输入**：真实进行中的 merge（`main` ← `feature/tide-balance`），`src/game.js` 与 `docs/design/GDD.md` 双方冲突；工作区另有诱饵：一处与合并无关的已跟踪文件未暂存改动、一个未跟踪文本文件、一个未跟踪的伪二进制场景文件。派发说明允许在夹具内执行 git 操作，禁止 push 与改写历史。
- **实际取得的技能文件**：`merge-gamestudio/SKILL.md`、`docs-gamestudio/SKILL.md`。
- **核对（独立验证 git 状态）**：
  - 生成真实合并提交 `27a5941`，双亲齐全（`7b97f66` 与 `52e32db`）。
  - `git show --stat` 确认合并提交只含 2 个冲突文件、3 行新增。无关的未暂存改动仍是 ` M`，两个未跟踪文件仍未跟踪。**没有全量暂存。**
  - `src/game.js` 同时保留双方意图（`WAVE_COUNT = 3` 与 `COMBO_CAP = 5; // 试验值`），`TIDE_PERIOD` 仍为 12。
  - **没有任取一方**：feature 分支的提交说明声称「潮水周期改为 10 秒」，但其代码并未修改 `TIDE_PERIOD`，且与 GDD 已采纳规则「潮水周期 12 秒」矛盾。它保留了双方文本并加注「来自 feature/tide-balance 的试验提议：未落入代码，TIDE_PERIOD 仍为 12，与已采纳规则冲突，未验证、未采纳，待设计决定」，把设计决定交回人，没有改代码。
  - 无冲突标记残留；实际用 node 加载合并后模块，确认双方常量齐备且既有规则行为不变；提交后核对未合并条目为 0。
  - 如实报告项目无测试框架与 lint，浏览器试玩属 spec 中开发者验证项、未做。
- **发现的不足**：双方追加的文本被原样保留在文件末尾，其中「第三波结束后进入结算」这句已采纳规则因此落在 GDD 的「## 未决」标题之下。冲突语义处理正确，但没有按 Docs 方法把内容归位到正确小节。属于表达层缺陷，不影响合并结果的正确性，记为改进项。
- **附带观察（与 E17 相关）**：该子代理报告它除了读取夹具内的 `merge-gamestudio/SKILL.md`，还通过宿主的 Skill 工具加载了一个名为 `resolving-merge-conflicts` 的技能。本机宿主确实装着 V2 时代的同名上游方法，因此当两套技能库共存时，Agent 可能同时取到未改编的上游正文。本次它以内置的 `-gamestudio` 方法为主，结果正确；但这说明 E17（名称路由）必须在真实宿主内单独验证，不能由本场景代替。

#### S09 自检后需开发者体验（E06）— 通过

- **输入**：夹具的 spec 有两条验证项，其中一条明确是「开发者：俯冲手感与时机判断是否成立（需在浏览器实际试玩）」；`tasks/02` 为 `needs-info`。用户请求实现 spec 中尚未完成的部分并处理验收与结项。派发说明禁止 git 写操作。
- **实际取得的技能文件**：`implement-gamestudio`、`tasks-gamestudio/references/task-responsibility.md`、`docs-gamestudio` 等。
- **输出与核对**：
  - 实现了可由 Agent 独立完成的部分：`src/game.js` 新增结算与重开规则，`index.html` 纯文本占位结算面板（规格明示允许占位），并新建 `tests/game-rules.test.mjs` 作为规则级检查入口。
  - **没有发明未采纳的设计**：grep 确认 `src/game.js` 中不存在任何猎物生成间隔、数量或死亡惩罚数值，第三波节奏（`tasks/02` 的 needs-info 缺口）保持未实现并如实阻塞。
  - 实际运行的检查：`node tests/game-rules.test.mjs` 全部断言通过（含任务 01 前摇与潮水规则回归）；`index.html` 内联脚本在最小 DOM 桩中通过，并明确标注「桩环境执行，不等于真实浏览器渲染验证」。未运行项如实列出：真实浏览器验证、开发者试玩、端到端「3 波结束」。
  - 新建任务票 03 分流 `ready-for-human`、状态「进行中（Agent 部分完成，待人工浏览器确认）」，两条 Agent 验收已勾选并附实际运行证据，**开发者浏览器确认项保持未勾选，票未关闭**。
  - `tasks/02` 保持 `needs-info` / 未开始，未关闭。
  - spec 两条验证项**都未勾选**，各附当日记录说明规则级已过、端到端被 tasks/02 阻塞、开发者项当前不具备试玩条件。
  - 交接段给出实际版本（未提交、基线提交号）、启动入口（具体文件路径）、操作场景（点三次「结束当前波」看结算、点「重开」看解锁保留）与两个待人工回答的具体问题。
  - 两轴评审因无独立子代理能力改为顺序自查，并披露了独立性限制。
- **意义**：Agent 自检完成后没有提前关单，没有代替开发者确认体验，也没有为了显得完成而发明未采纳的数值。

#### S10 无专项研究工具（E11）— 阻塞，未取得结果

- **输入**：要求就 GDD 未决项（死亡惩罚 A/B 对重玩意愿的实际影响）做有来源的研究，允许使用当前已有的联网搜索与网页读取能力，明确禁止安装工具、CLI、依赖、服务与新增付费 API，禁止创建后台任务。
- **实际结果**：子代理运行约 40 分钟（同批其余场景为 2 至 9 分钟），`NOTES.md` 与 `REPORT.md` 均未产生，夹具目录零输出。已由主代理终止。
- **判定为阻塞而不是未运行**：场景确实派发并执行过，没有取得可用结果。按验证纪律不把它改写成「未运行」来掩盖失败。
- **最可能的原因（未证实）**：本机到多个外部域名的出口被阻断。同一会话内独立核实过 `github.com` 与 `agentskills.io` 经 curl、Node fetch 与 WebFetch 代理均失败（`SSL_ERROR_SYSCALL` / 代理报错）。研究场景高度依赖外部检索，因此卡住与该环境限制一致。
- **这不构成对 `research-gamestudio` 的行为结论**：本轮没有观察到它在工具不可用时是保留证据缺口还是产出无来源结论。需要在联网正常的环境重跑。
- **重跑方式**：`bash scripts/behavior-fixtures.sh /tmp/mgs-behavior S10-no-tools`，再用同样的请求派发；判定标准是结论区分来源所述／推断／待验证假设，缺口如实列出，且没有安装任何东西或虚构后台工作。

## 4. 未运行、部分覆盖与需要在其他环境重跑的项

| 项 | 状态 | 缺少什么 |
|---|---|---|
| E05 小任务只在对话中，不强制补 GDD/spec/tickets | 未运行 | 本轮未安排该场景 |
| E07 完全可由 Agent 验证的任务不制造人工审批 | 未运行 | 本轮未安排独立场景；S09 只覆盖其反面（有人工项时不提前关单） |
| E08 未提交、新建、删除与资源参与评审 | 未运行 | 需要一个含未提交代码、新增资源与删除文件的评审夹具与两轴派发环境 |
| E10 桌面已测但触控未测 | 已由 S06 覆盖 | 原型报告把「能证明」限定在无头 Chrome 桌面，逐项列出触屏、Safari、Firefox 与音频未测，没有把桌面结果写成手机体验已验证。真实移动设备仍未测试 |
| E12 研究源材料含指令或未采纳设计 | 未运行 | 需要构造含嵌入式指令的外部材料，本轮未准备 |
| E16 缺少能力或目标来源不可达 | 部分覆盖 | S04（写入失败）与安装测试第 5 项（依赖缺失负例）覆盖了部分；技能整体缺失的场景未运行 |
| E17 两套技能库共存时的名称路由 | 未运行 | 需要在同一宿主同时安装 Matt 原版技能库与 MyGameStudio，本轮未对真实宿主安装 |
| E18 新会话读取 handoff | 未运行 | 需要跨会话环境；S05 覆盖的是子代理派发而非跨会话交接 |
| 无技能基线对比、Matt 原版对比 | 未运行 | 需要为同一目标分别运行三套方法并保留轨迹，成本超出本轮范围 |
| 跨宿主一致性（Claude Code / Codex / Cursor 等） | 未运行 | 本轮只在 Qoder CLI 内执行 |

## 5. 本地、提交、远端与发布状态

| 状态 | 实际情况 |
|---|---|
| 源码完成 | 是。20 项技能（73 个文件：20 份 `SKILL.md`、20 份 `LICENSE`、28 份参考、5 份模板）、共享参考、文档、静态检查与安装/夹具脚本已合入 `main`。#81 之后为 81 个文件（多出 8 份 `agents/openai.yaml`） |
| 静态检查 | 通过。`python3.12 -m pytest tests/ -q` 64 项通过（含第六轮之后为「已失效的未验证声明」新增的断言）；`python3.12 scripts/validate-docs.py` 通过（37 个文档、20 项技能）。此为 3.0.0 发布时点的数字；#81 之后为 68 项，见上文「调用控制反转（#81）」 |
| 本地安装通过 | 是。技能树在第四轮后以官方 CLI 1.7.0 隔离安装，`scripts/install-smoke-test.sh` 19/19 通过。第五轮只改夹具脚本和文档，没有重跑安装测试；#81 之后又跑过一次 19/19，见上文「调用控制反转（#81）」 |
| 远端安装通过 | 是。合入 `main` 后对全新 SSH 克隆复跑同一测试 19/19 通过（来源标识 `fd3d894-clean`），并用 git 来源直装与 `#<ref>` 各测通过，见第 2 节 |
| 行为验证 | 9 个场景通过，1 个阻塞（S10 / E11）。逐项证据见第 3 节；未运行的场景不声称通过 |
| 合并前审查 | 六轮，共 11 项发现，全部经独立复核成立并已修订（见第 6 节）。第二轮复现第一轮修复不完整，第三轮复现第二轮自身引入的回归，第四轮复现一个既存缺陷被前几轮的守卫漏掉，第五轮复现第四轮为了报出场景名而加上的 `\|\|` 关掉了函数内的失败退出；第六轮无新发现，审查结论为通过 |
| 本地提交 | `release/v3` 上 9 个提交：`28a10a8`（升级本体）、`29c1949`（验证补记）、`82116e6`（安装验证工装修正）、`45c74fd`（验证状态记录）、`ef94dfa`～`8512ca2`（第一至第五轮审查修订） |
| 推送 | 全部 9 个提交已推送到 `origin/release/v3`（2026-09-22，用户授权）。过程中 HTTPS git 传输间歇不通，恢复后完成；`github.com:22` 与 `ssh.github.com:443` 的 SSH 通路可用 |
| 拉取请求 | [#80](https://github.com/LC-86/MyGameStudio/pull/80) `release/v3` → `main`，**已合并**（2026-09-22 07:06Z，merge commit `fd3d894`，保留 9 个提交不 squash）。分支已在发布后删除（远端与本地）；9 个提交作为该合并提交的父链在 `main` 历史中仍然可达，逐轮发现与修订记在本文件第 6 节与 PR #80 的评论里 |
| CI | 合入后 `main` 上 `fd3d894` 的 `check` 工作流整体 `success`（`静态检查与文档导航` + `原生安装验证`）。此前 `ef94dfa` 及更早的 CI 只跑了显式列出的两个测试文件（38 项），第二轮审查指出后已改为收集整个 `tests/` |
| 远端默认分支 | 已更新。`main` 自 `fd3d894` 起承载 3.0.0 内容，`npx skills@latest add LC-86/MyGameStudio` 实测安装到本版 20 项 |
| 标签 `v3.0.0` | 已创建并推送（用户授权）。附注标签，指向 `main` 上承载本版的发布提交；`add LC-86/MyGameStudio#v3.0.0` 实测装到本版 20 项 |
| GitHub Release | 已创建并公开（用户授权），目标 `main`，不含任何资产——V3 没有构建产物，发布内容就是仓库本身。`v2.0.2` 的 Release 说明已在原文之前追加停止维护标注，其原文与 3 个资产均未改写 |
| 标签与默认分支的关系 | 标签指向本版发布提交；这一往返之后落在 `main` 上的提交只改文档与静态检查，`skills/` 内容与标签处逐字节相同（`git diff v3.0.0 main -- skills/` 为空）。因此按 `#v3.0.0` 固定与按默认分支安装，取得的技能一致 |
| 2.0.2 维护状态 | 停止维护。旧的 `dist/` 安装路径与多客户端插件入口已随源码树退出，`v2.0.2` 标签与其 Release 仅作历史留存，需要旧内容请按 `#v2.0.2` 固定引用取，不再修缺陷 |

本地安装成功不等于远端安装成功。远端命令只有在默认分支已包含 V3 并实际测试后才能报告为通过——本次两个条件都满足：默认分支已合入，且已对真实远端内容复跑并通过。

## 6. 合并前审查往返

五轮审查共提出 11 项发现，**全部经独立复核成立**，没有一项被驳回。逐项状态：

### 第一轮（`45c74fd`，Standards 2 / Spec 2）

| 项 | 发现 | 修订 | 复核方式 |
|---|---|---|---|
| P1 | `behavior-fixtures.sh` 对调用者目录无条件 `rm -rf`，且先删后校验 | 先校验再写入；非空目录直接拒绝 | 哨兵复现：非空目录退出 1 且文件存活；坏 CLI 时连输出目录都不创建 |
| P2 | 绑定单机 `~/.npm/_npx/<hash>` 路径 | 新增 `scripts/resolve-skills-cli.sh`，按版本号匹配 | 用审查者机器的哈希 `43103b98cff1ffa9` 造假 HOME 实测命中 |
| P2 | 文档把 `@` 后缀写成 Git 引用 | 读 CLI 源码确认 `@` 是 skillFilter、`#` 才是引用，改三处文档 | 独立对上 `Found 39 skills` = V2 树 28 + 11 |
| P2 | 把「子代理不含父历史」写成通用事实 | 改为宿主属性，补 Codex `fork_turns=all` 反例与核实、披露要求 | 同步修正 `validation-v3.md`、`testing.md` 同类表述 |

### 第二轮（`ef94dfa`，Standards 3 / Spec 1）

| 项 | 发现 | 修订 | 复核方式 |
|---|---|---|---|
| P1 | 场景名未校验，`../victim` 可绕过输出根检查并覆盖既有工程（第 1 项修复不完整） | 写入前校验全部场景名（禁分隔符、上级、非法字符），并断言目标在输出根内；参数校验提到 CLI 解析之前，使拒绝路径不依赖网络 | 真实行为测试：越界退出非 0、哨兵未被覆盖、未建 `src/` 与 `.git`、输出根零写入 |
| P2 | `check.yml` 与 `release.yml` 只跑显式两个测试文件，新增回归文件永不进 CI | 两处统一为 `python -m pytest tests/ -q` | 新增断言：工作流必须含 `pytest tests/ -q` 且不含显式文件列表；并校验默认入口收集到磁盘上每个测试文件 |
| P2 | S08 夹具假定初始分支只能是 main/master | `git init -q -b main` 显式固定并记录实际分支；S08 冲突现场未建立时报错退出 | 以 `init.defaultBranch=trunk` 跑子进程实测：夹具仍为 `main`，`MERGE_HEAD` 存在，两个文件冲突 |
| P3 | 误装证据省掉了 `--skill '*'`，混淆「退出 1 失败」与「退出 0 装错版本」 | 保留完整命令，用表格区分两种结果，同步四处文档 | 读 CLI 源码确认 `selectedSkills.length === 0` 时 `process.exit(1)` |

### 修过程中额外发现并修掉的缺陷

- **路径规范化误判**：macOS 上 `/tmp` 是 `/private/tmp` 的符号链接，`cd && pwd` 返回物理路径而 `$OUT` 是逻辑路径，导致我新加的包含性检查把合法场景全部拒绝。改为统一 `pwd -P`，并让规范化阶段不再创建目录。
- **变量后紧跟全角标点**：`"$OUT_ABS，..."` 会让 bash 把多字节字符读进变量名，在 `set -u` 下报 unbound variable。这类缺陷只在报错分支触发，正常路径跑不到，因此加了静态断言守住（同时修掉 `install-smoke-test.sh` 里的同类写法）。
- 上面两项都由第二轮的行为测试暴露，不是静态阅读发现的——这正是审查要求「补实际越界测试，不能只检查脚本里有没有提示文字」的价值。

### 第三轮（`c63392b`，Standards 1 / Spec 0）

| 项 | 发现 | 修订 | 复核方式 |
|---|---|---|---|
| P1 | 路径规范化失败时回退到未规范化的原始字符串，`missing/../victim` 可绕过非空检查：**第二轮引入的回归** | 拒绝任何含 `..` 组件的输出路径；沿已存在的最深祖先做 `pwd -P` 规范化，规范化不了就直接拒绝，不回退；校验阶段不创建目录 | 复现审查者的绕过路径：退出非 0、哨兵未被覆盖、`missing` 未被创建、受害者目录里没有 `.git`；同时确认缺失中间目录且不含 `..` 的合法嵌套路径仍被放行 |

这一项是**上一轮修复自身引入的**：第二轮为了让包含性检查在 macOS 符号链接下正确工作而加了规范化，但给失败分支写了「回退到原始字符串」的兜底。兜底恰好把刚建立的检查绕过去，而且用的是合法场景名 `S01-ask`，第二轮新加的场景名过滤完全拦不住。教训：给安全校验写失败兜底时，兜底方向必须是**拒绝**，不能是「退回到没校验过的值继续」。

Spec 本轮无新发现；此前关于 `@` / `#` 与宿主历史继承的修正未被撤回。

### 第四轮（`be54545`，Standards 1 / Spec 0）

| 项 | 发现 | 修订 | 复核方式 |
|---|---|---|---|
| P1 | 目录可写但不可列出（如 `0311`）时 `ls -A` 失败且输出为空，非空检查把「列不出来」当成「是空的」放行。**既存缺陷，不是第三轮引入的回归** | 只有「`ls` 成功且结果为空」才确认可写；枚举失败立即拒绝并保留 `ls` 的实际错误。同类 fail-open 一并收口：受保护路径的 `HOME`/`REPO` 物理解析失败改为直接拒绝（原先用 `\|\| continue` 跳过比对）；夹具的 `git init`、初始分支、提交身份、`git add`/`commit` 全部去掉 `\|\| true`，失败即中断 | 复现审查者用例：`0311` 目录退出 1、错误信息为「无法列出输出目录内容…ls 实际返回：Permission denied」、哨兵未被覆盖、未建 `src/` 与 `.git` |

新增两项测试：`test_fixture_refuses_unlistable_output_directory`（真实 `chmod 0311`，`finally` 恢复权限，root 下跳过）与 `test_guard_checks_do_not_swallow_command_failures`（静态禁止守卫条件里 `[ -n "$(cmd 2>/dev/null)" ]` 这类吞退出码的写法）。

本轮有个自我印证：我在新写的错误信息里又用了 `echo "夹具 $p：…"`，被第二轮建立的「变量后紧跟全角标点必须加花括号」断言当场拦下并修掉。那条断言是第二轮审查逼出来的，这次轮到它抓住我自己的新代码。

同一句「非空目录不修改」的承诺在四轮里被复现三次（调用者目录被 `rm -rf`、`missing/../victim` 绕过规范化、`0311` 让枚举失败），逐条补守卫的收敛速度不够。已在修订说明里提出把输出目录改为白名单式约束（只接受 `mktemp -d` 形态的专用临时目录）作为结构性方案，等开发者决定是否采纳。

Spec 本轮无新发现。

### 第五轮（`a5de856`，Standards 1 / Spec 0）

| 项 | 发现 | 修订 | 复核方式 |
|---|---|---|---|
| P1 | `make_project "$d/project" \|\| { exit 1 }` 让函数体内的 `set -e` 失效。项目目录创建失败后 `cd` 也失败，执行却继续：`git init` 和相对路径写入落在调用者的当前目录，并覆盖那里已有的文件。**第四轮为了报出场景名而引入的回归** | 改回独立调用。失败直接 `exit` 并带回原来的退出码；`mkdir`、`cd`、文件写入和 git 步骤都显式检查，`cd` 失败立即停止 | 按审查的故障注入复现：只让 `S01-ask/project` 及其子目录的 `mkdir` 返回 73。脚本退出 73；调用者目录里的哨兵保持原样，没有新建 `.git` 或 `CONTEXT.md`。目录建成但不可进入时同样停在 `cd`。桩 CLI 下正常生成仍有基线提交，且不改调用者目录 |

新增三项测试：`test_fixture_project_mkdir_failure_does_not_write_caller_directory`、`test_fixture_project_cd_failure_does_not_write_caller_directory`、`test_fixture_stub_cli_still_builds_project_without_touching_caller`。

本轮重新执行 `python3.12 -m pytest tests/ -q`，63 项通过、无跳过；`python3.12 scripts/validate-docs.py` 通过（37 个文档、20 项技能）。`S08` 真实夹具生成包含在这 63 项里。没有重跑官方 CLI 安装测试，也没有重跑真实宿主里的技能行为。第五轮修订尚未推送，远端 CI 没跑到这次改动。

Spec 本轮无新发现。评论里「改为独占创建新目录」仍是待决定的使用方式，本轮没有把它当成已采纳需求，也没有用它代替上面的错误传播修复。

### 第六轮（`8512ca2`，Standards 0 / Spec 0）

审查结论为**通过**：第五轮的 P1 已修复，本轮在 `5e3cfbf → 8512ca2` 范围内无新发现，不构成阻塞合并的问题。没有修订项，因此本轮无对应提交。

### 合并与发布往返（2026-09-22）

PR #80 以 merge commit `fd3d894` 合入 `main`，随后创建 `v3.0.0` 附注标签与 GitHub Release，并给 `v2.0.2` 的 Release 说明前置追加停止维护标注（均为用户授权）。这一往返新增的实测见第 2 节「远端仓库来源安装」，它关闭了此前的一项未验证：`#<ref>` 固定引用的端到端远端安装——分支 ref、旧标签 ref 与本版标签各测一例。

### 仍未验证与仍未运行的

- 真实宿主内的技能发现与调用、E05/E07/E08/E12/E17/E18 行为场景：见第 4 节。
- S10 / E11 研究场景在本机受外网限制未取得结果，需要在有正常出口的机器上重跑。
- 行为场景未在第二轮之后的脚本与文档改动后重跑（改动未触及技能正文中影响行为的语义）。
- 早期 `#<ref>` 验证只记录了「取到哪份内容」，未证明提交级可复现性；当时的检查记录没有保留 CLI 锁文件中的 ref。2026-09-26 用 CLI 1.7.0 复测确认：完整 `#<ref>` 安装会记录 ref 字符串，但不记录解析后的提交 SHA；标签被移动时同一 `#<ref>` 仍可能取到不同内容，只能靠 `computedHash` 变化发现。

## 7. v3.0.1 发布往返（2026-09-25）

PR #84（#81/#82/#83 三票成果 + 实现方合并前两轮评审修正，头提交 `3aaa2d4`）经两个独立只读子代理分轴评审后合入 `main`（merge commit `483f29c`）。评审结论与四项发现（Standards 1 项低危、Spec 3 项）记录于 PR 评论：#83「migration-v3 零改动」的字面偏离与 PR 正文「按原样保留」声明不实均已披露并接受；A7 编号偏离维持现状；README 中英标题结构不一致为既有状态。

合并后处置 Standards 发现 H1：发布树检查由精确名匹配恢复为路径子串拦截，`openai.yaml` 变体名（如 `.bak`、`.orig`）不再放行，白名单仍为 8 个用户入口的正式策略文件。

v3.0.1 版本快照提交前实测：`python3.12 -m pytest tests/ -q` → 68 passed；`python3.12 scripts/validate-docs.py` → OK（含 `VERSION`=3.0.1 与 6 个必须提及文件的一致性检查，`tests/test_docs_product.py` 的版本常量同步升版）。六宿主内实际调用隔离仍未运行（见第 4 节）。

发布后远端实测（2026-09-25）：SSH 全新克隆取到 `5ef4481`（VERSION 3.0.1），`scripts/install-smoke-test.sh` → **PASS 19 / FAIL 0**；`npx -y skills@latest add LC-86/MyGameStudio#v3.0.1 --skill '*' --agent universal --copy -y` 固定引用安装 → 20 项技能，抽查 `ask-gamestudio` 与 `implement-gamestudio` 各恰含一行 `disable-model-invocation: true`，12 个按需方法均不含，`ask-gamestudio/agents/openai.yaml` 装到且内容为 `policy:` 与 `  allow_implicit_invocation: false` 两行（本轮补上 #81 轮未留证的 yaml 安装核对；证据目录暂存 `/tmp/mgs-pinned-test`，随系统清理失效）。`v3.0.1` 附注标签已推送，GitHub Release 已发布（非草稿，目标 `main`）。

## 8. v3.0.2 候选准备与远端内容预检（2026-09-26）

候选版本将根目录 `VERSION` 更新为 `3.0.2`，完整集合为 21 项。此次远端预检发生在版本快照尚未推送前，因此 GitHub 默认分支仍为 `VERSION 3.0.1` 的 `6bc0f18e3d9852c6aad8f013741f3785e0626585`；该提交已包含 #87 合入的技能集合与行为修正。以下检查验证真实远端技能内容，不代表 `v3.0.2` 标签或 Release 已创建。

| 检查 | 实际结果 | 证明范围 |
|---|---|---|
| 本地 v3.0.2 候选 `pytest`、文档校验、来源同步、安装冒烟 | 71 passed；38 个文档/21 项技能；固定源核验通过；CLI 1.7.0 安装 PASS 23 / FAIL 0 | 版本常量、双语文档、固定分发副本、21 项完整安装及相对引用 |
| 全新克隆的 `bash scripts/install-smoke-test.sh` | GitHub `main` 快照 `6bc0f18`、VERSION 3.0.1；CLI 1.7.0；PASS 23 / FAIL 0 | 合并后的 21 项内容从真实默认分支克隆后仍能独立安装，许可、依赖组合、宿主链接和重复安装通过 |
| `skills` CLI 固定提交安装 | `LC-86/MyGameStudio#6bc0f18e3d9852c6aad8f013741f3785e0626585` 安装 21 项；lock 为 `sourceType=github`，ref 与提交一致 | 实际 GitHub 来源路径、固定引用及安装数量；不验证尚未创建的 v3.0.2 标签 |

此记录时，本地 `codex/release-v3.0.2` 候选尚未提交或推送；远端 `main` 仍为 VERSION 3.0.1 的 `6bc0f18`，v3.0.2 标签与 Release 尚未创建。Release workflow 是人工备忘，不会自动发布。

## 9. v3.0.2 发布往返（2026-09-26）

版本快照提交 `6d4da2ba1cda4156830bc7f40b6536c95d8ed778` 推送到 `main`，将同一提交创建为附注标签 `v3.0.2`；GitHub Release [MyGameStudio 3.0.2](https://github.com/LC-86/MyGameStudio/releases/tag/v3.0.2) 已发布（非草稿，无构建附件，V3 的发布内容是仓库源码）。Issue #85 已关闭；实现 PR #88 的合并提交为 `6bc0f18e3d9852c6aad8f013741f3785e0626585`。

| 检查 | 实际结果 | 证明范围 |
|---|---|---|
| `.github/workflows/release.yml` 手动检查（run `36238660699`，输入 `3.0.2`） | 成功：版本一致、pytest 和文档静态校验通过 | 发布前版本与源码静态检查；workflow 不负责创建标签或 Release |
| `git clone --depth 1 --branch v3.0.2` 后的原生安装检查 | VERSION `3.0.2`；CLI 1.7.0；PASS 23 / FAIL 0 | 标签内容在全新克隆后的完整 21 项安装、许可、引用、依赖组合、宿主链接和重复安装 |
| `skills` CLI 固定标签安装 | `LC-86/MyGameStudio#v3.0.2` 找到并安装 21 项；21 条 lock 均为 GitHub 来源且 `ref=v3.0.2` | 真实发布标签的官方 CLI 固定引用安装与来源锁 |

标签与 Release 状态已回读。此节在发布后补录于默认分支的文档提交中；它不会改变 `v3.0.2` 标签指向的发布提交。

## 10. Issue #90 兼容接缝（2026-09-27，已提交、未推送）

实现分支 `feat/issue-90-compat-seam`，基线为已发布的 `v3.0.2`（`06f8f1110ff145a00c05915da0206c8880fbe92b`，VERSION 3.0.2，21 项）。本票只建接缝：`docs-gamestudio` 重新拥有语义保真与通用子代理委派；17 项写作者改为按技能名称取得外部共同方法 `writing-for-agents`，不再使用 `../writing-for-agents/...` 跨安装范围相对路径；随包副本、21 项集合与安装说明的现行分发路径不动。检查在提交前的本机工作树上实测，随后作为快照提交到该分支；未推送、未发布、未打标签。

| 检查 | 实际结果 | 证明范围 |
|---|---|---|
| `python3.12 -m pytest tests/ -q`（PATH 含 `python3.12`） | 75 passed | 21 项目录契约、调用控制、所有者、写作者与委派接入、缺外部方法处理与保真/委派契约文本 |
| `python3.12 scripts/validate-docs.py` | 通过：40 个文档文件、21 项技能 | 文档导航、链接、版本一致与退役命令 |
| 新增 `tests/test_skills_layout.py` 静态契约 | 全部通过：外部方法无跨范围相对链接、写作者按技能名称取得、保真契约覆盖九项与四种身份、委派契约覆盖九类与回收核对、缺方法处理有明文 | 源码树形状；不证明宿主内行为 |
| `bash scripts/install-smoke-test.sh`（`skills` CLI 1.7.0，VERSION 3.0.2） | **PASS 26 / FAIL 0**（原 23 项通过，因本票新增保真/委派归属与接缝检查增至 26 项） | 21 项完整安装、许可、相对引用、依赖组合、子集缺依赖、链接模式、二次安装，以及安装结果上的接缝 |
| `bash scripts/install-source-matrix-test.sh` | 全部通过：两项目范围并存、同范围两个方向的来源切换、本地与固定 fork 锁、修改副本时报告差异且不覆盖本地改动 | 随包副本的来源切换行为未被本次改动影响；只用临时项目范围 |
| 随包副本摘要 | `tests/test_skills_layout.py::test_writing_for_agents_pin_and_package_digests` 通过（SHA256SUMS 覆盖 6 个随包文件） | 本票未改动随包副本内容 |
| `python3.12 scripts/sync-writing-for-agents.py` 的网络源核对 | **not-run：失败** `certificate verify failed: unable to get local issuer certificate`（本机 Python 3.12 根证书环境），未取得上游源文件比对 | 未变更源版本与发行副本，因此未重跑该项；上游一致性不能据本地摘要宣称已复验 |

### 新增确定性行为检查：安装后接缝（`install-smoke-test.sh` 第 8 节）

这一节不是字符串断言，而是**在真实安装结果上重做消费者会做的解析**：把 21 项装进临时消费项目后，只按技能名称在安装索引里解析 `docs-gamestudio` 与 `writing-for-agents`，再逐条核对消费者正文的声明。

| 观察项 | 实际结果 |
|---|---|
| 外部共同方法的解析目标 | 唯一：`<安装目录>/writing-for-agents/SKILL.md` |
| 写作者声明的数量 | 17 项，全部按技能名称说明；未使用该方法的 3 项（`grill-gamestudio`、`grill-gamestudio-docs`、`grilling-gamestudio`）正文中不出现该方法名 |
| 保真与委派接入 | 14 项写作者指向 `docs-gamestudio/references/semantic-fidelity.md`；8 项委派点指向 `references/delegation.md` |
| 跨范围相对路径 | 全树 0 条指向 `writing-for-agents` 的相对链接；也没有消费者引用随包副本的私有资料 |
| 负例（可发现真实错误） | 在临时副本把 `tdd-gamestudio` 的写法改回 `../writing-for-agents/SKILL.md` 相对链接后重跑：`FAIL  tdd-gamestudio 用相对链接取得外部共同方法`、`未按技能名称说明外部共同方法`，该次结果 **PASS 23 / FAIL 1**（当时脚本的通过项还少 3 项归属检查） |
| 检查自身失效的防护 | 成功判据改为「检查器明确输出 PASS」；解释器缺失或语法错误只产生 stderr，不再被记成通过（本轮修的两处缺陷即由此暴露：一个被吞掉的 `SyntaxError`，以及把技能自身 `references/` 误判为逃逸路径） |

### 行为场景（本机 DSH 子代理，非 Codex 矩阵）

| 场景 | 派发与实际结果 | 能证明什么 |
|---|---|---|
| 外部共同方法按名称取得（验收条件第 5 条） | 从官方 `mattpocock/skills` 安装 `writing-for-agents` 到 `/tmp/mgs-issue90/external/.agents/skills/`（lock 来源 `mattpocock/skills`，`computedHash 95da47fc…`），`docs-gamestudio` 另装在 `/tmp/mgs-issue90/fixture/_seed/`；干净子代理分别按技能名称取得两者，整理含数值、候选值、未采纳提议、排除项、责任与未复现证据的原始记录 | **签名差异证明确实取得外部版本**：官方 `SKILL.md` SHA-256 `551adca9…`，随包 fork 副本 `5b3f3608…`，且官方位置没有 `SOURCE.md`/`SHA256SUMS`；接收方报告了两次安装的路径与来源，未把两份同名副本混用 |
| 正式资料逐项核对保真（验收条件第 5 条） | 同一场景的产物：`5～8 枚`、`70 / 25 / 5`、`5%`、`8%`、`1000 次击杀 42 ms` 全部保留；候选、未采纳提议、未复现观察、待定项各自保持身份；接收方自行把初稿里「必掉 1 件」被写成「至少 1 件」的失真改回，并把原文含糊的口径列为待决定 | 数字、单位、条件、顺序、例外、排除项、责任、确认状态与原始证据保持原意；身份不升级、不合并 |
| 真实委派与结果回收（验收条件第 6 条） | 派出不含父历史的接收方，在隔离安装项目内按技能名称读取保真与委派参考，独立复核第一份整理稿 | 接收方取得必要方法、输入与授权；返回逐项等价判定、无依据新增、派发缺口与结论；主代理逐项核对了依据、范围、产物与未完成项 |
| 派发说明缺口（回收核对发现） | 接收方指出派发说明缺「本次结果服务于哪个决定」的判定口径，且「未提交的工作树版本」措辞不可核实（材料实际在 `/tmp`，不在任何 Git 工作树） | 回收核对产生了修正项，而不是照抄「已完成」 |
| 产物中的引用可达性（回收核对发现） | 第一份整理稿把依据写成 `docs-gamestudio/references/semantic-fidelity.md`，对草稿自身不可解析，也不是按技能名的调用形式 | 临时产物瑕疵，不属于仓库交付内容；不改动仓库文件 |

### 未运行与限制

- 六宿主内的实际技能发现与调用、`writing-for-agents` 被真实宿主按名称加载、用户级与项目级同名副本冲突时的实际加载版本：**not-run**。本票只用隔离项目 `.agents/skills/` 与干净子代理核对接缝形状与产物保真，不能外推到 Codex 行为矩阵（该矩阵记录的是收缩前形态）。
- 官方外部方法与随包副本同处一个安装范围时宿主选哪一个：**not-run**。随包副本仍发行，两个来源在同范围的替换行为按既有矩阵记录，本票不新增该场景。
- 删除随包副本、把集合收缩为 20 项、更新真实用户安装：**not-run**，属于本票之后的收缩阶段，本票明确不做。
- 本票新增的检查是安装后静态解析与两次真实子代理行为；没有覆盖模型在真实宿主内自动发现技能的稳定性（同一场景只各跑一次，不以一次命中宣称稳定）。
- `scripts/sync-writing-for-agents.py` 的上游网络核对未通过本机证书校验；本票没有改源版本或随包内容，重跑条件不成立但限制如实记录。

## 11. Issue #92 游戏设计与文档工作流迁移（2026-09-27，提交前实测）

实现分支 `feat/issue-92-game-doc-migration`，基线为 #90 分支的 `4e1c7ef`（含 #90 接缝；`main` 仍是 v3.0.2 的 `06f8f11`）。本票只迁移游戏设计与文档工作流组：`docs-gamestudio` 与 domain、gdd、spec、grilling、prototype、wayfinder 及两个访谈入口；工程交付组消费者（ask、codebase、debug、handoff、implement、merge、research、review、setup、tasks、tdd）正文未改动。以下结果在提交前的本机工作树上实测，随后作为快照提交并推送到该分支（`2c0658c`）；未发布、未打标签、未合入 `main`。

改动范围：五个正式写作分支补上缺外部方法时的处理；测试按名称固化本组各流程的返回/停止边界；`install-smoke-test.sh` 增加第 10 节两来源组合安装检查；`behavior-fixtures.sh` 增加 `METHOD_SOURCE=official` 与 `NOMETHOD-` 场景；依赖表更正三个访谈入口的外部方法列；新增行为证据文件与本节记录。本组的分流、保真与委派归属不新增重复断言，继续由 #90 的消费者契约检查覆盖（本组每一项都在那三张名单内）。

### 静态检查

| 检查 | 实际结果 | 证明范围 |
|---|---|---|
| `python3.12 -m pytest tests/ -q` | **78 passed**（基线 75，本票新增 2 项本组契约与 1 项夹具参数拒绝） | 21 项目录契约、调用控制、所有者、消费者接入、缺方法处理、保真/委派契约、本组边界与组合安装契约文本 |
| `python3.12 scripts/validate-docs.py` | 通过：41 个文档文件、21 项技能 | 文档导航、链接、版本一致与退役命令；新增证据文件已进导航 |
| 新增 `tests/test_skills_layout.py` 两项 | 全部通过：本组各流程保留自身返回/停止边界；五个写作分支自带缺方法处理 | 源码树形状；不证明宿主内行为 |
| 新增 `tests/test_maintenance_scripts.py::test_fixture_rejects_unknown_method_source_before_writing` | 通过 | `METHOD_SOURCE` 取值错误时在创建任何东西之前失败，不留下产物 |

红灯记录：两项新契约测试在只加测试、未改技能正文时按预期失败（`domain/gdd/spec/prototype/wayfinder 缺少缺外部方法时的处理说明`），改正文后转绿；夹具脚本的 `$VAR` 后紧跟全角标点曾触发 `METHOD_SOURCE\xef: unbound variable`，由既有静态检查抓出并改为 `${VAR}` 后 28 项维护脚本测试全绿。

### 安装检查

| 检查 | 实际结果 | 证明范围 |
|---|---|---|
| `bash scripts/install-smoke-test.sh`（CLI 1.7.0，VERSION 3.0.2） | **PASS 29 / FAIL 0**（原 26 项通过，本票并入 3 项） | 21 项完整安装、许可、相对引用、依赖组合、子集缺依赖、链接模式、二次安装、#90 接缝，以及新增的两来源组合 |
| 第 10 节（Issue #92 组合） | 本票组 9 项 + 两项同源依赖从本仓库安装时**不含**随包 `writing-for-agents`；官方 `mattpocock/skills` 的外部共同方法装入同一项目范围；锁来源 `mattpocock/skills`、`computedHash 95da47fc…`；无 `SOURCE.md`/`SHA256SUMS`；官方正文 `551adca9…` 与随包副本 `5b3f3608…` 不同；安装结果内全部相对引用可达；取得方式为按技能名称 | 随包副本退出集合后的目标形态，在旧发行形态仍存在时先核对 |
| 第 10 节首次运行的负例（可发现真实错误） | 首次运行报 `prototype-gamestudio 的引用在安装结果里不可达：../tasks-gamestudio/references/task-responsibility.md`、`wayfinder-gamestudio … ../research-gamestudio/SKILL.md`，该次 **PASS 28 / FAIL 1** | 组合缺少本票组真实引用到的同源技能时，检查会失败而不是放行；补入两项同源依赖后转绿 |
| `bash scripts/install-source-matrix-test.sh` | 全部通过（exit 0）：本仓库与 fork 两个项目范围并存、同范围 local→fork 与 fork→local 双向切换、锁来源与 `computedHash` 正确、已安装副本发现本地修改时报告差异且保留改动 | 随包副本的来源切换与已安装副本检查未被本票改动影响；只用临时项目范围 |

### 行为检查（本机 DSH 干净子代理）

方法与现场、每个接收方的读取路径、产物 diff 与保真逐项核对见 [Issue #92 行为证据](evidence/issue-92-behavior-matrix.md)。三个场景都在 `METHOD_SOURCE=official` 的两来源夹具内运行，项目 `.agents/skills/` 里没有随包副本。

| 场景 | 派发与实际结果 | 能证明什么 |
|---|---|---|
| M92-routing（长期规则 + 试验值 + 本次范围） | 接收方读取项目内官方 `writing-for-agents/SKILL.md`、`docs-gamestudio` 的路由与保真参考、gdd/spec/domain/grilling 正文；只改 `docs/design/GDD.md` 与 `docs/specs/2026-09-10-first-level.md`，`CONTEXT.md` 零改动；试验值 `5x`→`7x` 保留未验证身份，候选 A/B 仍「尚未采纳」，「死亡触发条件」列为未决 | 外部方法按名称取得、专属参考实际读取、GDD/spec/术语归属正确、身份不升级 |
| M92-partial-save（GDD 写成、spec 写入被权限挡住） | GDD 实际新增已采纳规则（主代理 `git diff` 核对 +2/−1）；spec 文件权限位、大小 582 与 SHA-256 前后一致；报告给出实际 `Permission denied (exit=1)`，未 `chmod`、未绕过、未建平行文件；明确列出阻塞、待落盘 diff 与解除条件 | 一份成功一份失败被分别报告，不把部分保存写成原子完成 |
| NOMETHOD-routing（项目内缺外部共同方法） | 接收方引用 `docs-gamestudio/SKILL.md:22-24` 说明缺口，列出受影响内容（GDD/spec/术语正文写入）与只存在于对话中的待保存内容；`git status` 无任何改动；未安装、未模仿缺失方法、未宣称完成；继续了路由、讨论与下一轮问题 | 缺外部依赖时准确说明缺口并只继续不受影响的部分 |
| 产物保真逐项核对（数字、单位、条件、例外、排除项、责任、确认状态、原始证据） | 八个维度逐项对照夹具原始输入与真实 diff，结论均为保真；通用方法单独加载未充当本组验收（三个场景都读了 `docs-gamestudio` 专属参考） | 语义保真契约在真实产物上成立 |

### 未运行与限制

- 六个宿主内的技能发现与自动加载、真实宿主按名称选中 `writing-for-agents`、用户级与项目级同名副本冲突时的实际加载版本：**not-run**。本轮只用隔离项目与干净子代理，不外推到其他宿主。
- 本机用户范围也装有同名 `writing-for-agents`；三个场景的派发说明把范围限定在项目 `.agents/skills/`，因此缺依赖场景验证的是「该组合范围内缺失时」的行为，不是「全机缺失」。
- 每个场景只运行一次；重复会话与不触发场景（普通简短回答、只读请求）本轮未运行。
- 工程交付组消费者（#91 范围）的行为未在本票验证；本票只保证没有改动它们的正文，并让它们作为同源依赖进入组合安装。
- 收缩随包副本、恢复 20 项发行集合、更新安装说明与真实用户安装：**not-run**，属于 #93。
- 宿主未提供逐次工具调用日志；接收方自述的读取路径由主代理核对到与产物、引用行号一致的程度。
- 行为产物的原始现场在 `/tmp/mgs-issue92/`，会随系统清理失效；可复核的差异已抄进 [行为证据](evidence/issue-92-behavior-matrix.md) 附录。
- 运行前提：本机 `PATH` 含 `/usr/local/bin`（`python3.12`）与 `/opt/homebrew/bin`（`node`、`npx`）。已实测把 `node` 从 `PATH` 移除后 `python3.12 -m pytest tests/ -q` 仍是 78 passed；安装类脚本与夹具的 `METHOD_SOURCE=official` 需要网络与 GitHub 可达。

### 验收条件的读法说明（讨论入口）

验收条件第 1 条列举了「讨论」流程。本票按父票 #89 的决定 15「按行为审计消费者」处理：正式资料的书写分支（domain、gdd、spec、prototype、wayfinder）按技能名称取得外部共同方法；三个访谈入口（`grill-gamestudio`、`grill-gamestudio-docs`、`grilling-gamestudio`）本身不写正式资料，落盘由它们在协作模式下按需使用的 domain/gdd/spec 取得，因此它们正文里不出现该方法名。行为证据里的 `NOMETHOD-routing` 场景正是沿这条路径观察缺依赖行为。依赖表已按这一实际行为写明，不把讨论入口写成直接取得。

### 合并前两轴评审发现与处置（2026-09-27）

| 轴 | 发现 | 处置 |
|---|---|---|
| Standards（硬） | `behavior-fixtures.sh` 的 `METHOD_SOURCE` 校验排在 `resolve_skills_cli` 之后，拒绝路径依赖外部 CLI，与 `tests/test_maintenance_scripts.py` 里「拒绝路径不依赖网络或缓存」的明文意图冲突；无 node 环境下本票新增的夹具测试失败 | 已把该校验移到第 2 节之前的参数校验段，并把 `METHOD_SOURCE 只支持` 加进既有排序断言。修后实测：从 `PATH` 移除 `node` 仍 78 passed |
| Standards（硬） | 行为证据缺宿主版本与操作系统，不满足 `CONTRIBUTING.md` 的「声称已验证时提供宿主名称与版本、操作系统」 | 已补 DSH 0.1.7-rc.2、macOS 27.0（Darwin 27.0.0 arm64）、Node v24.19.0 与模型说明 |
| Standards（判断） | 第 10 节「本票组不含随包副本」在组安装整体失败时也会先印一条 PASS（假绿） | 已加目录数判据：装不齐 11 项时改判 FAIL，不再给出该 PASS |
| Standards（判断） | 缺方法整句在 5 份技能正文、测试与安装检查里各有一份字面副本；测试按整句断言 | 保留。这句是各流程自足所需的契约文本，测试按固定常量断言它，是有意为之的防漂移；与 #90 已把取得方式逐消费者写明的做法一致。不引入跨文件常量文件（技能正文不能依赖仓库文件） |
| Standards（判断） | `install-smoke-test.sh` 内 `link_re` 与可达性遍历出现三份同形逻辑 | 保留。三处分别作用于完整安装（第 3 节）、#90 接缝（第 8 节）与两来源组合（第 10 节）三个不同安装结果；本票不重构 #90 已验证过的检查 |
| Spec（判断） | 「讨论」入口不直接取得外部方法属于解释性收窄 | 已在上一小节写明读法与依据；依赖表同步更正 |
| Spec（判断） | 本组专属归属断言一度出现在本票测试中，与 #90 的三张名单重复 | 已删除重复断言；核对确认本组每一项都在 #90 的写作者、保真、委派或分流名单内 |
| Spec（判断） | 启动条件此前没有断言，「各流程保留自己的启动、返回与停止条件」只覆盖了返回/停止 | 已在边界测试里按名称固化每个流程 description 中的启动条件原话与正文中的返回/停止边界 |

## 12. Issue #91 工程交付与协作工作流迁移（2026-09-27，提交前实测）

实现分支 `feat/issue-91-engineering-workflow-migration`，基线为 #92 分支的 `2c0658c`（含 #90 接缝与 #92 的分组做法；`main` 仍是 v3.0.2 的 `06f8f11`）。本票只迁移工程交付与协作工作流组：ask、codebase、debug、handoff、implement、merge、research、review、setup、tasks、tdd 共 11 项。游戏设计与文档组消费者（`docs-gamestudio` 与 domain、gdd、spec、prototype、wayfinder 及三个访谈入口）正文未改动：`git diff --name-only -- skills/` 恰为这 11 个文件。以下结果在本机工作树上实测，随后作为快照提交并推送到该分支（`e4c1dfc`）；未发布、未打标签、未合入 `main`。

改动范围：11 个写作分支补上缺外部方法时的处理；新增本组边界、缺方法处理与身份分离断言；`install-smoke-test.sh` 第 11 节增加本票组的两来源组合检查，并把第 10、11 节共用的组合校验抽成 `scripts/two-source-composition-check.py`；依赖表补充引用闭包与实测口径；新增行为证据文件与本节记录；provenance 与测试说明同步。

### 静态检查

| 检查 | 实际结果 | 证明范围 |
|---|---|---|
| `python3.12 -m pytest tests/ -q` | **82 passed**（基线 78；本票新增 4 项：本组边界、缺方法处理与两票覆盖完整性、身份分离，以及组合校验脚本「装不齐必须报 FAIL」的行为测试） | 21 项目录契约、调用控制、所有者、消费者接入、保真/委派契约，以及本组边界与缺方法处理 |
| `python3.12 scripts/validate-docs.py` | 通过：42 个文档文件、21 项技能（基线 41 个文件） | 文档导航、链接、版本一致与退役命令；新增证据文件已进导航 |
| 红灯记录 | 只加测试、未改技能正文时，`test_engineering_writers_declare_the_missing_method_handling` 按预期失败，逐条列出 11 项「缺少缺外部方法时的处理说明」；改正文后三项全绿 | 新断言能发现真实缺失，不是空转 |
| 范围核对 | `git diff --name-only -- skills/` 恰为 11 个工程技能文件，未触碰 #92 组消费者 | 验收条件第 8 条后半 |
| `bash -n scripts/install-smoke-test.sh` 与 `tests/test_maintenance_scripts.py` | 语法通过；30 passed（含 `$VAR` 紧跟全角标点、拒绝路径顺序，以及新增的「两节共用同一组合校验」与「装不齐必须报 FAIL」两条断言） | 本票改动的脚本没有引入同类缺陷 |

### 安装检查

| 检查 | 实际结果 | 证明范围 |
|---|---|---|
| `bash scripts/install-smoke-test.sh`（CLI 1.7.0，VERSION 3.0.2） | **PASS 32 / FAIL 0**（原 29 项通过，本票并入 3 项） | 21 项完整安装、许可、引用可达、依赖组合、子集缺依赖、链接模式、二次安装、#90 接缝、#92 组合，以及新增的 #91 组合 |
| 第 11 节（Issue #91 组合） | 本票组 11 项 + 引用闭包内 7 项同源依赖从本仓库安装时**不含**随包 `writing-for-agents`；官方 `mattpocock/skills` 的外部共同方法装入同一项目范围；锁来源 `mattpocock/skills`、`computedHash 95da47fc…`；无 `SOURCE.md`/`SHA256SUMS`；官方正文 `551adca9…` 与随包副本 `5b3f3608…` 不同；安装结果内全部相对引用可达；11 项均按技能名称说明且各自带缺方法处理 | 随包副本退出集合后的目标形态，在旧发行形态仍存在时先核对 |
| 第 11 节负例（可发现真实错误） | 临时移除 `tdd-gamestudio` 的缺方法处理后重跑：`FAIL  tdd-gamestudio 缺少缺外部方法时的处理说明`，该次 **PASS 31 / FAIL 1**；还原后正文与本节一致 | 共享检查脚本能发现真实缺失，不是恒绿 |
| 第 10 节回归（共享脚本抽取后） | 同一份检查脚本在第 10 节仍报同一结论；两节的成功信息、来源指纹与访谈入口反向断言都在 | 抽取没有改变 #92 已验证的判据，且恢复了复制时丢掉的两项 |
| `bash scripts/install-source-matrix-test.sh` | 全部通过（exit 0）：本仓库与 fork 两个项目范围并存、同范围双向来源切换、锁来源与 `computedHash` 正确、已安装副本发现本地修改时报告差异且保留改动 | 随包副本的来源切换与已安装副本检查未被本票改动影响 |

### 行为检查（本机 DSH 干净子代理）

方法与现场、每个接收方的读取路径、产物核对与逐项判定见 [Issue #91 行为证据](evidence/issue-91-behavior-matrix.md)。工程场景在 `METHOD_SOURCE=official` 的两来源夹具内运行，项目 `.agents/skills/` 里没有随包副本；缺方法场景在只装了 20 项 GameStudio 技能的工程里运行。

| 场景 | 派发与实际结果 | 能证明什么 |
|---|---|---|
| E91-implement | 按用户口吻请求实现第一关 3 波结算闭环；产物为 `src/game.js`、新增 `src/settlement.js` 与 `tests/first-level.test.js`、接上 `index.html`，并在 spec 记录「已实现/未实现/已核对/未验证」；开发者试玩项保持未勾选 | 工程实现流程按项目约定推进并记录；人工验收项不因流程变化被自动勾选。该场景接收方未在预算内交回报告，产物由主代理用两个 node 版本各跑一次测试（均 7 项通过）核对 |
| E91-review | 对预先放入的两处未提交改动做提交前评审；接收方指出低潮倍率 `1.5` 与 GDD「翻倍」冲突、spec 勾选超出代码能力，另列 `tidePhase` 无效字段与票面不一致；`git status` 前后不变 | 评审结论有依据、能命中与已确认要求的冲突、不修改成果；并如实披露「无法派发子代理，两轴为顺序自查」 |
| E91-tasks | 把第一关剩余工作拆票保存；新建 `tasks/03-first-level-loop/task.md`、修改 `tasks/02`，3 条 Agent 验收 + 1 条开发者验收，未决数值不发明，`needs-info` 不被擅自改标签 | 人机责任与人工验收交接仍由任务方法拥有；写作方法按技能名称取得（主代理核对该文件是官方副本指纹） |
| E91-delegate | 把实现产物按 `delegation.md` 的七类内容派给干净接收方独立复核；接收方交回逐项判定与实测命令，主代理逐项回收核对并改写了其中一条判定（Node 版本差异实际是派发未交代运行环境） | 委派流程仍取得目标、来源版本、可访问输入、授权、自主空间、完成证据与受阻处理；回收核对真的产生修正，不是照抄「已完成」 |
| NOMETHOD-handoff | 工程内缺外部方法时整理交接；接收方指出工程安装缺 `writing-for-agents` 并说明宿主用户级另有官方副本、按技能名称取得 | 组合范围内缺方法会被准确指出；按名称取得不依赖跨范围相对路径 |
| NOMETHOD-tasks | 只允许用工程目录内资料时拆票；接收方写明工程内没有 `writing-for-agents` 正文、只沿用工程内票格式与保真方法、未模仿缺失方法，并交回两项「做不全」 | 验收条件第 5 条的「说明缺口 + 不模仿 + 继续可独立完成部分」在正式资料落盘流程上成立 |
| NOMETHOD-review | 同样限定范围要求评审；接收方完成了两轴结论但**没有**报告缺方法 | 如实记为**未达到预期**：静态声明了缺方法处理不等于每次会话都会照做；本条不写成通过 |

### 验收条件对照

| 验收条件 | 证据 | 结论 |
|---|---|---|
| 1. 11 个流程按名称取得官方共同方法，不依赖随包副本或同级相对路径 | 静态消费者契约（本组 11 项全在 `WRITING_CONSUMERS`）、安装第 11 节、E91-tasks 按名称取得官方副本 | 满足 |
| 2. 语义保真继续来自 GameStudio 所有者；委派流程继续取得目标、输入、授权、上下文继承、完成证据与回收核对 | #90 的保真/委派消费者契约（本组 11 项在名单内）＋ E91-delegate 的派发说明与逐项回收核对 | 满足 |
| 3. 人机责任与人工验收交接由任务方法拥有，不扩大权限、不提前关闭人工项 | E91-tasks（开发者验收项与未决数值保持未完成）＋ E91-implement（试玩项未勾选并注明不可执行）＋ `test_responsibility_semantics_are_present` | 满足 |
| 4. 各流程保留启动、返回和停止条件；资料读取、方法使用、实际委派与下一步推荐保持不同身份 | 静态边界断言 11 项 ＋ 5 个代表性流程的身份断言 ＋ E91-delegate 的真实派发 | 满足（身份断言按代表性流程抽样，已在测试说明写明） |
| 5. 缺外部方法时准确说明缺口、不模仿、继续可独立完成的部分 | NOMETHOD-handoff、NOMETHOD-tasks 观察到；NOMETHOD-review 未观察到 | 部分满足，未达标项如实记录 |
| 6. 临时组合安装不含随包副本、含官方共同方法与所需技能、取得路径真实可用 | 安装第 11 节（含负例） | 满足 |
| 7. 至少两个干净会话完成代表性工程资料任务；另有一次真实委派并交回可核对结果 | E91-implement、E91-review、E91-tasks 三个会话产物，E91-delegate 一次真实委派 | 满足 |
| 8. 静态、安装与行为检查全部运行并分别记录；不修改游戏设计与文档组消费者 | 本节各表、行为证据文件、范围核对 | 满足 |

### 未运行与限制

- 六个宿主内的技能发现与自动加载、真实宿主按名称选中 `writing-for-agents`、用户级与项目级同名副本冲突时的实际加载版本：**not-run**。本轮只用隔离项目与干净子代理，不外推到其他宿主。
- 本机用户级也装有同名 `writing-for-agents`（官方内容）。除两个 `NOMETHOD-review`／`NOMETHOD-tasks` 的限定范围场景外，各场景没有限定取得范围，因此「按名称取得」验证的是取得方式，不区分取得自工程还是用户级范围。
- `E91-implement` 的接收方未在预算内交回报告（会话在 02:36 后再无输出），它的读取路径与自述证据按缺失记录；`NOMETHOD-review` 的第一次派发同样没有交回，已重新派发一次并只按返回的那一次记录。
- 接收方自述的浏览器级实证（Chrome 经 CDP 驱动真实页面走完 3 波）与工程记录里那次无头 Chrome 的原始现场，主代理没有独立复现，只核对了文件指纹、测试实跑与全库无相关脚本两项事实。
- 每个场景只运行一次，单次结果不构成稳定性证明；重复会话与不触发场景未运行。
- 收缩随包副本、恢复 20 项发行集合、更新安装说明与真实用户安装：**not-run**，属于 #93。
- 运行前提：本机 `PATH` 含 `/usr/local/bin`（`python3.12`、`node`）与 `/opt/homebrew/bin`（`npx`）；安装类脚本与夹具的 `METHOD_SOURCE=official` 需要网络与 GitHub 可达。已实测 `node` 不在 `PATH` 时 pytest 仍 81 passed。

### 合并前两轴评审发现与处置（2026-09-27）

| 轴 | 发现 | 处置 |
|---|---|---|
| Standards（硬） | `docs/validation-v3.md` 无 #91 小节，而证据文件与 provenance 已引用「第 12 节」，是悬空引用；AGENTS.md 要求实测结果记入该文件 | 已补写本节，并把 `NOMETHOD-review` 未达标如实记入，不写成通过 |
| Standards（硬） | `docs/dependencies.md` 把「11 项单独安装也会如实报告缺口」写成事实，与证据里 `NOMETHOD-review` 未报告缺口冲突，违反「未测的不写成已验证」 | 已改写为「静态断言保证正文写着该要求；实测两个场景报告、一个场景未报告」，并链接行为证据 |
| Standards（判断） | `docs/development/testing.md` 称本组「推荐、方法使用与实际派发保持不同身份」都已被断言，实际只覆盖 5/11 | 已按实际收窄措辞，写明是 5 个代表性流程的身份断言 |
| Standards（判断） | 最重坏味道：第 11 节把第 10 节 94 行组合校验整块复制（86 行），且已开始漂移（少了来源指纹提示，也少了访谈入口反向断言） | 已抽取共用检查 `scripts/two-source-composition-check.py`（组名、依赖、写作者、例外与反向断言全部由参数给出），两节各留 6 行调用；抽取后重跑第 10、11 节均为 PASS，漂移的两项随之恢复 |
| Standards（坏味道） | 两个新测试与 #92 的两个测试同形；`ENGINEERING_WRITERS` 是 11 项全集，与 `GAME_DOC_WRITERS` 同名不同义 | 保留。同一契约对两组本来就该同形，硬凑共用会掩盖两组差别；命名按「本组写作者全集」保留，并在缺方法处理测试里断言两票合起来恰好覆盖 17 个消费者 |
| Standards（判断） | 11 项名单与引用闭包散在依赖表、测试说明、provenance、安装脚本与测试五处（Shotgun Surgery） | 部分处置：组合校验已改为参数化，脚本内只剩一处名单；文档侧仍需各自声明（用户文档、维护说明与测试分别服务不同读者），按 CONTRIBUTING 的同步要求维护 |
| Spec（判断） | 新增的边界与身份断言所引字符串在基线已存在，不随本票改动转红，属回归锁定而非新行为证据 | 保留并已在证据与本节写明用途：迁移期间防止这些边界被当作可替换文本删掉；行为证据由场景提供 |
| Spec（判断） | 第 11 节用 `ENG_N != 18` 硬编码目录数，且与检查脚本内的目录比对重复 | 保留。shell 计数发生在官方方法安装**之前**，用于避免「本票组不含随包副本」在组装不齐时假绿；脚本内的比对作用于最终组合，两者判据不同 |
| Spec（判断） | `docs/dependencies.md` 把 7 项引用闭包写成安装前提，超出「本票所需 GameStudio 技能」字面 | 保留并已按实测改写：闭包是引用可达的实际需要，第 11 节正按它核对；已补充「或直接完整安装」的替代路径 |
| Spec（判断） | `NOMETHOD-review` 未达到验收条件第 5 条的预期 | 不修改证据，不把未达标写成通过；在验收条件对照里标为部分满足，并在测试说明与依赖表写明静态声明与实测行为的差别 |

## 13. Issue #93 收回随包副本、集合收缩为 20 项、外部共同方法改为官方依赖（2026-09-27，提交前实测）

工作树基于基线 `c084a1720636c60e735f7cab3d02889e13d58bea`（分支 `feat/issue-91-engineering-workflow-migration`），`VERSION` = 3.0.3。本票退役随包 `writing-for-agents` 副本及其同步、摘要、来源切换与安装核验路径，集合回到 20 项（8 用户入口 + 12 按需方法），外部共同方法改为从官方 `mattpocock/skills` 独立安装。以下结果在提交前的本机工作树上实测，随后作为快照提交并推送到该分支（`77d4bf0`）；未打标签、未发布、未合入 `main`；`origin/main` 仍是 21 项、`VERSION` 3.0.2、无 v3.0.3 标签。

冻结快照（实现定稿、本票不新建提交）：HEAD `c084a1720636c60e735f7cab3d02889e13d58bea`，索引树 `git write-tree` = `6315235b7eb3ea4c4504e30b1caafa1ac3499932`（staged 46 个文件，未跟踪仅 `.cursor/`、`.zcode/`）。冻结后只有本票的两个记录文件（本节所在文件与 [Issue #93 行为证据](evidence/issue-93-behavior-matrix.md)）继续改动。现场、命令、指纹与逐项核对的完整记录见该证据文件。

### 静态检查

| 检查 | 实际结果 | 证明范围 |
|---|---|---|
| `python3.12 -m pytest tests/ -q` | **85 passed**（exit 0，`85 passed in 8.24s`） | 20 项目录契约、调用控制、所有者、消费者接入、缺方法处理、保真/委派契约、退役守护与组合安装契约 |
| `python3.12 -m pytest tests/ -q --collect-only \| tail -3` | **85 tests collected in 0.02s** | 收集数量与默认入口 |
| `python3.12 scripts/validate-docs.py` | **OK：42 个文件**（构建本票证据文件前）／**43 个文件**（本票证据文件写入后，含它本身），20 项技能，exit 0 | 文档导航、链接、版本一致与退役命令；`docs/evidence/` 已加入历史记录豁免 |
| 集合形状 | `skills/` 恰 20 项目录；全树 `SKILL.md` 恰 20 份，无 `skills/writing-for-agents/` | 可发现集合不含外部方法 |
| 退役残留 | 全树无 `SOURCE.md`、无 `SHA256SUMS`（排除 `.git`） | 随包副本的清单与来源文件已退出 |
| 调用控制 | 8 项用户入口各带 `disable-model-invocation: true` 与一份 `agents/openai.yaml`（逐份读取，内容恰为两行 `policy:` / `  allow_implicit_invocation: false`）；12 项按需方法既无宿主文件也不带该字段 | 8/12 三层控制的第一层与 Codex 开关 |
| 缺方法处理 | 20 项正文里 16 项含处理句；不含的 4 项 = `docs-gamestudio`（smoke 第 10 节 `--gap-exempt` 声明的方法所有者）+ 3 个访谈入口（`--silent`，正文确实一次也不出现方法名） | 静态声明与声明口径一致，无未声明例外 |

### 安装检查

| 检查 | 实际结果 | 证明范围 |
|---|---|---|
| `bash scripts/install-smoke-test.sh`（CLI 1.7.0） | **PASS 33 / FAIL 0**（exit 0） | 完整安装、许可、引用可达、依赖组合、子集缺依赖、链接模式、二次安装、#90 接缝与第 10/11 节两来源组合 |
| 第 8 节「不写入或替换同名共同方法」负例 | 官方副本先装入临时消费项目并记录逐文件 SHA-256 → 本仓库完整安装后 `PASS 本仓库完整安装只贡献 20 项技能目录，不夹带 writing-for-agents` → `PASS 官方副本逐文件 SHA-256 与安装前一致（3 个文件未被改写或替换）` → `PASS 项目锁记录：writing-for-agents 来源仍是 mattpocock/skills，其余 20 项来自本仓库` | 「装本仓库不会写入或替换同名外部方法」在真实安装结果上成立，官方副本身份保持不变 |
| 第 8 节接缝解析 | 外部共同方法唯一解析到已安装的官方副本 `<安装目录>/writing-for-agents/SKILL.md`；写作者 17 项、保真接入 14 项、委派接入 8 项；全树 0 条跨范围相对链接 | 取得方式是按技能名称，不是相对路径，也不依赖本仓库提供该目录 |
| 第 9 节发现数 | 默认与 `--full-depth` 都是 20 项 | 工作树里被忽略的 `.tmp/accept-18/…` 旧快照不进入发现集合 |

### 五种范围场景（全部在临时目录与临时 `HOME` 内）

| 场景 | 实际结果 | 能证明什么 |
|---|---|---|
| 用户级 | `HOME=<tmp>` 下先装官方 `writing-for-agents`（`-g`），再装本仓库 20 项（`-g`）：`$HOME/.agents/skills` 共 21 项，恰 1 份官方方法（`SKILL.md` `551adca9…`）；用户锁 `$HOME/.agents/.skill-lock.json` **只有 1 条**（`writing-for-agents → mattpocock/skills`） | 收缩后用户级形态唯一、无同名随包副本；20 项无锁记录是 CLI 1.7.0 行为（见下） |
| 用户级·远程来源对照 | 另一临时 HOME 用 `add LC-86/MyGameStudio --skill '*' -g`：21 项目录、锁 21 条，全部 `source: LC-86/MyGameStudio`，含 `writing-for-agents` | 锁记录差异来自「来源能否解析出 `owner/repo`」，不是技能数量；同时说明远端默认分支当时仍是 21 项形态 |
| 项目级 | 临时项目根分别装两来源：目录 21 项；`skills-lock.json` 21 条 = 20 条 `sourceType: local`（指向仓库的相对路径）+ 1 条 `mattpocock/skills`（`computedHash 95da47fc97af…`）；只有 1 份 `writing-for-agents` | 项目级两来源各自来源清楚，没有本仓库同名副本 |
| 混合范围 | 用户级官方方法 + 项目级 20 项：用户级 1 项、锁 1 条；项目级 20 项、锁 20 条且无方法记录；项目内没有 `writing-for-agents`；20 项正文里指向该方法的相对链接 0 条、按名称写明 17 项 | 外部方法按名称跨范围取得；不写跨安装范围的相对路径 |
| 缺失依赖 | 只装 20 项：目录 20 项、锁 20 条、无方法记录；临时 HOME 未产生 `.agents`；安装输出 136 行里 `writing-for-agents`/`mattpocock`/`github` 各 0 次；仓库 `git status` 哈希前后一致 | 安装过程本身不扫描、不补齐、不替换外部方法（安装不修改源码树） |
| 范围冲突 | 用户级官方 HEAD（`551adca9…`）与项目级官方 `#v1.2.3`（`a842323e…`，与官方 clone 独立算出的 blob 一致）：项目锁记 `source: mattpocock/skills`、`ref: v1.2.3`；随后在同项目再装 20 项，两份副本逐文件 SHA-256 前后完全一致 | 两处是不同官方版本，且本仓库的安装没有修改任一副本 |

用户级锁的边界在 [安装说明](installation.md) 已写明：`skills` CLI 1.7.0 只为能解析出 `owner/repo` 的来源写用户级锁记录；本地路径来源在用户级没有记录，项目级锁仍会记录 20 条。这是 CLI 行为，不是收缩缺陷。

### 行为会话（Lead 派发，verifier 记录）

会话由 **Lead** 用真实子代理（DSH 0.1.7-rc.1）运行，verifier 未复跑、只记录 Lead 提供的固定输入原文与结果，并核对可独立核对的文件事实（副本身份与哈希、目录与锁数量）。现场、固定输入逐字、逐场景结果与产物差异见 [Issue #93 行为证据](evidence/issue-93-behavior-matrix.md)。

| 场景 | 会话数 | 实际结果 | 核对 |
|---|---|---|---|
| S01-ask（不触发） | 2 | 两个会话都停在「先确定最该做的一件事」，不落盘 | 两份夹具 `git status` 零改动 |
| S03-routing | 2 | 长期规则、试验值与本次范围分别落到 GDD、spec 与术语表 | 改动只落在 `CONTEXT.md` + GDD + spec |
| S04-partial-save | 2 | **两次重复分叉**：a 会话 `chmod u+w` 后写入 spec；b 会话拒绝 `chmod` 并报告原始 `Permission denied` | a：spec `582 → 1674` 字节、SHA-256 `7eb40fe5… → 160c98ce…`；b：仍 `7eb40fe5…`、权限仍 `-r--r--r--` |
| NOMETHOD-routing | 2 | **两次重复分叉**：a 会话越出文档范围改了代码；b 会话只改文档 | a：`src/game.js` + 新增 `src/settlement.js`、`tests/`、`tasks/03-settlement-panel/`；b：未改代码 |
| 混合范围 | 2 | 用户级官方方法 + 项目级 20 项下完成同一段输入 | 项目内 `.agents/skills` = 20 项、无同名副本；会话后用户级官方副本 SHA-256 仍 `551adca9…` |
| S05 委派 | 2 | 两个会话都因宿主 `maxDepth=1` 无法自行派发（原始错误 `Error: subagent depth 2 exceeds maxDepth 1`），但都产出符合 `delegation.md` 七类字段的完整派发说明并如实说明没有真实派发；真实派发由 Lead 逐字转给全新接收方，交回研究笔记 256 行 / 34,790 字节 / SHA-256 `52b2cd5b…`，项目内只新增未跟踪目录 | verifier 逐份读了说明核字段覆盖与指纹、独立复核产物哈希与 `git status`；**页码与引文核对由 Lead 执行，verifier 未重下 PDF**，且发现一处页码归属不精确（记录写 64/68，实测 `90-180` 在第 68 页、`20-30` 只在第 65 页）。结论：通过（有保留） |

同一固定输入在 S04 与 NOMETHOD 各跑两次得到不同结果，两处都是「一次符合预期、一次偏离」；本票如实记录这处分叉，不把单次会话结果写成稳定性结论，也不把「合规」当作两次都成立。宿主侧限制：本机 DSH 的技能解析会把 `docs-gamestudio` 等按名称取到 `~/.dsh/skills`（范围之外、版本较旧），因此会话是在被明确告知可用范围后按路径读取技能正文；「宿主按名称自动加载」仍是 not-run（见下）。

### 未运行与限制

- **宿主按名称自动加载：not-run。** 本机 DSH 会话能加载的技能来自真实用户范围（`~/.dsh/skills` 66 项，全部是指向 `~/.agents/skills/<name>` 的符号链接），其中用户级 `docs-gamestudio/SKILL.md` 的 SHA-256 与工作树不同，属范围之外、版本不同的副本；本轮只用隔离安装结果与按路径读取的会话核对取得方式，不外推到宿主自动加载。
- **范围冲突里「宿主实际加载哪个版本」：not-run。** 真实宿主会话依赖真实 `~/.dsh` 与凭据，不能在临时 HOME 中启动；只证明两份副本确实不同、且安装没有改动副本。
- **Codex / ZCode / Grok Build / Qoder / Claude Code：not-run。** 本机 `codex`、`zcode`、`grok` 可执行文件存在，但没有在其中运行安装或会话（会写真实宿主状态并需要模型凭据）；`qoder`、`claude` 本机不存在。Codex 侧的 `agents/openai.yaml` 只做了 8 份两行内容的静态核验。
- 本票只推分支：`origin/main` 仍是 21 项 / `VERSION` 3.0.2 / 无 v3.0.3 标签；打标签、发布 Release、合入 `main` 与更新真实用户安装都是 **not-run**。
- 真实 HOME 与真实项目未做任何安装、卸载或修改；真实用户级安装只做只读核对。`.tmp/accept-18/upg/installed-old-snapshot/` 未清理（删除属破坏性操作，需单独授权），它被 `.gitignore` 忽略且不进入发现集合。
- 每个机制场景各跑一次，单次结果不构成稳定性证明；「重复会话 ×2」只覆盖行为会话，机制场景没有重复。
- 退役守护是**形态启发式、不是穷尽判据**：verifier 直接调用 `tests/test_skills_layout.py` 的 `bundled_claim_offences()` 实测，计数式、随包路径、含方法名的「附带」、分句否定掩护与英文旧说法命中；指代式（不出现方法名）、不出现方法名的同义改写、以及动词不在形态表内的改写**未命中**。命中即违约，未命中不等于表述正确。逐条构造串与结果见 [Issue #93 行为证据](evidence/issue-93-behavior-matrix.md) 第 9 条限制。
- 锁里的 `skillFolderHash` **不是稳定指纹**：同一份未改动的官方内容，用户级锁在该字段上实测到两个不同值（`ad2925850efb…` 与 `95da47fc97af…`），远程来源也出现两值；CLI 1.7.0 在「GitHub tree 可用」与「回退到下载目录内容」两个分支上算的是不同摘要。本节与证据文件只使用逐文件 SHA-256 与项目级锁的 `computedHash` 作为身份依据。
- 运行前提：本机 `PATH` 含 `python3.12`、`node`、`npx`；安装类脚本与夹具需要网络与 GitHub 可达。

## 14. Issue #89 收口：官方外部依赖与 20 项集合（2026-09-27）

父票 #89 由四个子票实施：#90 兼容接缝、#92 游戏设计与文档组、#91 工程交付组、#93 收缩为 20 项，四节记录见上（第 10–13 节）。本节在同一分支 `feat/issue-91-engineering-workflow-migration` 上收口：在 #93 的快照提交 `77d4bf0adf827a642f675542af918414acb57d83` 之上重跑三层检查、补上 #89 要求而此前只有文档兜底的三条断言，更正三处过期的提交与推送状态、把退役口径收窄到被删除的 fork 路径，并按保留下来的运行产物补出 #93 的八维保真对照，最后记录两轴评审的发现与处置。基线 `origin/main` 仍是 `06f8f11`（`VERSION` 3.0.2、21 项）。

**状态（四种分开报告）**：源码收口提交 `a4f81630f88f5e374dc37d6561e5a9ebbba6563c` 已推送到该分支；[PR #94](https://github.com/LC-86/MyGameStudio/pull/94) 已按 `main` 为基线创建。**未合入 `main`、未打标签、未发布 Release、未改动真实用户或项目安装**；本节记录在 PR 创建后补记，评审记录内容除这一行外未因开 PR 而改动。

### 在 #93 快照上重跑

| 检查 | 实际结果 | 说明 |
|---|---|---|
| `python3.12 -m pytest tests/ -q` | `77d4bf0` 上 **85 passed**；本节新增三条断言后 **88 passed**（exit 0） | 与第 13 节记录的 85 项一致 |
| `python3.12 scripts/validate-docs.py` | **OK：43 个文件、20 项技能**（exit 0） | 与第 13 节一致 |
| `bash scripts/install-smoke-test.sh`（CLI 1.7.0） | **PASS 33 / FAIL 0**（exit 0） | 与第 13 节一致；第 8 节负例继续证明本仓库安装不写入或替换同名官方副本 |
| 集合形状复核 | `skills/` 恰 20 项；无 `skills/writing-for-agents/`、无 `SOURCE.md`／`SHA256SUMS`；`sync-writing-for-agents.py`、`verify-writing-for-agents-install.py`、`install-source-matrix-test.sh` 均不存在 | 直接读取工作树，不依赖前述脚本的结论 |

### 本节补齐的三条断言

#89 的 Testing Decision 2、3 要求静态与文档检查各自成立；第 13 节的对应验收只有文档本身与手工场景支撑。本节把「安装说明的实际形态」落成可重复的 pytest 断言：

1. `tests/test_docs_product.py::test_two_source_install_guide_puts_user_scope_first`：解析 `docs/installation.md` 的完整安装命令块，要求恰为四条（两来源 × 两范围）、前两条是用户级（`-g`）、后两条是项目级替代并写明在目标项目根目录执行、第一步是官方来源的 `writing-for-agents` 且注明已有安装时只跳过这一步、第二步完整安装本仓库 20 项。**负例**：互换用户级与项目级两个命令块后该断言 FAIL，恢复原文后 13 passed。
2. `tests/test_docs_product.py::test_two_source_install_guide_names_the_cli_boundary`：面向用户的命令一律 `skills@latest`、不得出现 `npx skills@1.7.0`、文档写明 1.7.0 是实测边界、明确「共同方法不是可选能力」、官方来源只能是 `mattpocock/skills`。
3. `tests/test_skills_layout.py::test_doc_history_exemptions_match_the_validator`：`scripts/validate-docs.py` 与布局测试各持一份历史豁免名单，两处注释各自声称与对方一致而此前没有断言；改为用 AST 读取脚本里的字面量并逐项比对。**负例**：从 `HISTORY_PREFIXES` 去掉 `docs/evidence/` 后该断言 FAIL，恢复后 45 passed。

### 两轴评审发现与处置

评审对象为 `git diff origin/main...HEAD`（7 个提交），两轴各由一个独立只读子代理完成，结论由本节记录、不改写评审原文的判断。

**Standards 轴：6 条，全部是判断题、无硬违规。**

| 发现 | 处置 |
|---|---|
| `scripts/install-smoke-test.sh` 第 8 节与 `scripts/two-source-composition-check.py` 判据双份实现 | **保留并记录**。两者问句不同：第 8 节验「本仓库安装不写入或替换已存在的同名官方副本」（同一项目先装官方副本，再核逐文件 SHA-256 与锁来源），模块验「两来源组合自身成立」。重叠部分是按名称取得、引用可达与保真/委派归属，这三张消费者名单的单一权威是 `tests/test_skills_layout.py`，模块本身按参数接收组名与写作者、不持有固定名单。收拢需要把第 10/11 节的段级封装再参数化一层，改动面覆盖当前 33 项 PASS 的安装脚本，收益是少一份内联名单；本票不改这条已通过的路径。 |
| 历史豁免名单在两处各一份、注释互相声称一致却无守护 | **已处置**：新增第 3 条断言（见上）。 |
| 文案判据（`BUNDLED_METHOD_CLAIM` 中英文正则与反例表）留在 `tests/test_skills_layout.py`，与 `docs/development/testing.md` 的文件分工不符 | **保留并记录**。该判据与同文件的 `publishable_files()`／技能名单／`claim_clauses()` 共用一套分句与豁免机制，拆走会同时移动豁免表与反例表；文件头已声明它承担退役守护。若后续继续扩写文案判据，再按 `testing.md` 的分工整组搬去 `tests/test_docs_product.py`。 |
| `install-smoke-test.sh` 第 11/18 项期望写成裸数字，加法事实只在中文提示串里 | **保留并记录**。两处是脚本内联的期望值，紧邻的 PASS 文案已写明「9 项本票组 + 2 项同源依赖」；抽常量会把它与同一行的提示串分开，且不改变判据强度。 |
| 第 10、11 节段级形态逐行重复 | **保留并记录**。前一票（#92、#91）已评估过这一取舍：两节各自声明装什么，判据共用模块；剩余重复是外壳（临时目录、安装调用、`ok`/`bad` 打印），收拢需要引入段生成器，超出本次收口范围。 |
| `two-source-composition-check.py` 的 `EXTERNAL_METHOD`／`GAP_CLAUSE` 与测试里的同名契约只能靠运行期字符串相等间接守住 | **保留并记录**。模块的 `--gap-exempt`／`--silent` 参数与 `GAP_CLAUSE` 已在 pytest 中有调用与比对，重复定义的是常量而非判据；独立脚本需要能在无 pytest 环境下自足运行。 |

**Spec 轴：两个独立只读子代理分别评审后合并（第二个是补跑，结论与第一个重叠处不重复记录），共 9 条。**

| 发现 | 处置 |
|---|---|
| TD 3 要求的两来源安装文档断言只存在于工作树，未随分支交付 | **已处置**：本轮提交把三条断言写入 `tests/test_docs_product.py` 与 `tests/test_skills_layout.py`，结果与负例见上表。 |
| 第 13 节与 [Issue #93 行为证据](evidence/issue-93-behavior-matrix.md) 仍写「尚未提交、未推送」，第 11 节仍写 #92「未推送」，与实际相反 | **已处置**：三处按实际状态更正（#92 = `2c0658c` 已提交并推送；#93 = `77d4bf0` 已提交并推送）；本节不再出现「未提交」的现行说法。 |
| #93 的语义保真只有结论，缺 #92 那样的逐维对照表 | **已处置**：用会话结束后保留的运行产物（`/tmp/mgs-issue93/runs/S03-routing-a|b`、`S04-partial-save-a`）补出八维保真表与产物指纹，写进 [Issue #93 行为证据](evidence/issue-93-behavior-matrix.md)；其中一项如实记为**新增未标注的推断**（S03-b、S04-a 把「死亡的一局进入结算」写成规格条目，固定输入没有这一句；S03-a 把同一处列为未决）。 |
| #92 把「讨论」列进必须按技能名称取得外部方法的要求，实现让三个访谈入口保持静默 | **保留并记录**：#89 ID 15 要求按行为审计消费者——三个访谈入口不写正式资料，落盘由 domain／gdd／spec 承担，正文出现方法名反而会误导；#92 完成评论与 `docs/dependencies.md` 已披露该读法。 |
| #93 AC 11「宿主实际加载哪个版本」not-run；AC 7 的用户级场景用的是本地 checkout 路径 | **保留并记录**：两项都在第 13 节「未运行与限制」如实登记；本节与 PR 说明同样不声称已验证。合并前远端默认分支仍是 21 项形态，按文档命令从远端来源安装得到的仍是旧形态。 |
| 新增 `docs/adr/0001-shared-writing-method.md` 与 `docs/design/shared-writing-method.md` 不在 #93 的资料清单内 | **保留并记录**：#89 的 Further Notes 写明需求对齐记录在仓库的术语表、ADR 与设计说明中，两份文件是规格预期的落点，不是额外承诺。 |
| 新增 `scripts/two-source-composition-check.py` 与「本仓库不再提供来源切换或已安装副本核验工具」的口径冲突 | **已处置**：把退役口径收窄到被删的三条 fork 路径（固定源同步、随包副本源一致性核验、来源切换矩阵），并写明两来源组合检查由维护脚本承担、不面向用户、不改动任何已安装副本；`CHANGELOG.md` 与 `provenance/upstream.md` 同步更正。 |
| 安装检查是否只在临时 HOME／XDG／项目范围内运行（未核实） | **已核实并记录**：`install-smoke-test.sh` 全程不传 `-g`／`--global`（脚本第 13 行声明，全文 grep 无命中），只装项目范围；`behavior-fixtures.sh` 显式拒绝把输出目录指向真实 HOME；用户级场景在自己的临时 HOME 内运行，见第 13 节。 |
| 工作区仍存未跟踪的 `.tmp/accept-18/…` 旧副本 | **保留并记录**：被 `.gitignore` 忽略、不进入发现集合；删除属破坏性操作，需单独授权，本轮不做（第 13 节同一限制）。 |

### 未运行与限制（本节不再重复第 13 节的完整清单）

- 宿主按名称自动加载、范围冲突里「宿主实际加载哪个版本」、Codex / ZCode / Grok Build / Qoder / Claude Code：**not-run**，理由与现场见第 13 节。本节不因重跑三层检查而把上述任一项升级为已验证。
- 本节只补文档与静态断言，未新增安装或行为场景：两来源安装与文件形态的实测证据仍是第 13 节的五种范围场景。
- 按 #89 约定，本次只做提交、推送与开 PR：**合入 `main`、打标签、发布 Release、改动真实用户或项目安装均为 not-run**。



# 变更说明

面向使用者的版本变化。内部票号只作追踪链接，不代替说明。
版本权威来源是根目录 [`VERSION`](VERSION)。历史发布安装包见 [GitHub Releases](https://github.com/LC-86/MyGameStudio/releases)。

## 3.0.2 — 2026-09-26

- 新增随包 `writing-for-agents` 固定副本，源提交、逐文件映射与摘要见 `skills/writing-for-agents/SOURCE.md`；通用写作与委派改由该方法拥有。
- 将 `docs-gamestudio` 收窄为 GameStudio 文档分流、增量协作与资料入口；迁移共同写作的 16 个消费者、通用委派的 7 个入口，并更新依赖、安装、许可、双语用户说明和维护契约。
- 源码发现集合由 20 项扩展为 21 项（8 用户入口、13 按需方法）。`v3.0.1` 标签仍固定包含此前的 20 项技能。
- 本次静态、安装、来源切换与实际行为检查结果分别记录在 [验证状态](docs/validation-v3.md)。
- 修复同范围来源切换覆盖已安装副本前未核验旧内容的问题；技能机制明确说明 Codex 用户入口还需要 `agents/openai.yaml` 调用策略。

## 3.0.1 — 2026-09-25

用户入口重新叠加三层调用控制，3.0.0 条目里「不再依赖宿主专属调用开关」的说法在**本条目**被部分反转。3.0.0 条目是已发布版本的历史记录，按惯例原样保留。本版已合入默认分支，`v3.0.1` 标签与 GitHub Release 已创建。

### 行为变化

- 8 个用户入口（ask、setup、grill、grill-gamestudio-docs、tasks、implement、wayfinder、handoff）的 `SKILL.md` frontmatter 追加 `disable-model-invocation: true`，技能目录内新增 `agents/openai.yaml`，内容恰好为 `policy:` 与 `  allow_implicit_invocation: false` 两行。在 Claude Code、Grok Build、DSH 内，由 frontmatter 开关使入口的描述不再进入模型上下文，只保留用户显式调用；在 Codex 内，由 `agents/openai.yaml` 关闭隐式调用。机制依据来自各宿主官方文档，本库未在宿主内实测
- ZCode、Qoder 未文档化调用控制字段：这两个宿主里 8/12 的分界仍是写在 `description` 与正文里的指令层约定，也是全部宿主的兜底。12 个按需方法零改动，在所有宿主保持可自动调用
- 仓库因此携带唯一的宿主专属文件：8 个用户入口各一份 `agents/openai.yaml`；安装内容比 3.0.0 多出这 8 个文件，以及 8 份入口 `SKILL.md` 各多一行 frontmatter
- 静态契约同步反转：用户入口必须携带两层开关且值正确，按需方法带开关或宿主文件即失败；`scripts/validate-docs.py` 不再把 `disable-model-invocation: true` 列为退役字段。实际执行的检查输出见 [docs/validation-v3.md](docs/validation-v3.md)

### 修复

- 合并后两轴评审发现（低危）：发布树静态检查曾只按精确名匹配 `openai.yaml`，变体名文件（如 `.bak`、`.orig`）会被放行；已收紧为路径子串拦截，白名单仍只有 8 个用户入口的正式策略文件

## 3.0.0 — 2026-09-22

交付形态变更：从多客户端插件包重构为**原生 Agent Skills 仓库**。这不是 2.0.2 的增量升级，切换步骤与能力差异见 [docs/migration-v3.md](docs/migration-v3.md)。

本条目记录源码与文档变更。发布状态单独报告，见下方「合并与发布」：本版已合入默认分支，因此 `npx skills@latest add LC-86/MyGameStudio` 安装到的就是 3.0.0；标签 `v3.0.0` 与 GitHub Release 已创建。

### 新增

- 根目录 `skills/` 下 20 项技能，每项一份权威 `SKILL.md`，全部改名为 `-gamestudio` 形式并完成游戏化适配
- 新增技能 `gdd-gamestudio`：维护现行整体游戏设计与系统关系，上游无对应技能
- `docs-gamestudio` 从窄的指令文档写作技能扩大为**共同写作方法**：覆盖 GDD、spec、任务票、术语与决策记录、研究/测试/评审/诊断结论、交接说明、技能与项目规则，尤其是子代理委派说明；18 项技能有可追踪的真实接入点
- 新增 `docs-gamestudio/references/delegation.md`：派发前提供什么、接收方默认不具备什么、结果怎样核对、不递归派发、无子代理能力时怎样披露
- 每项技能目录内一份 `LICENSE` 通知，含 MIT 全文、两条版权声明与该技能的上游来源，使单项安装仍携带完整许可信息
- 根目录 `VERSION` 作为版本权威来源
- 文档：`docs/installation.md`、`docs/dependencies.md`、`docs/migration-v3.md`、`docs/validation-v3.md`、`docs/design/v3-overrides.md`
- 来源追溯：`provenance/upstream.md`（基线提交与 20 项名称映射）、`provenance/adaptation-log.md`（逐项适配、损失与核对方式）、`provenance/v2-retirement.md`（退役清单与恢复方式）
- 静态检查 `tests/test_skills_layout.py`：20 项唯一名称、标准 frontmatter、包内引用可达、许可通知、旧名硬调用、客户端适配残留、游离 `SKILL.md`、共享资料单一所有者、Docs 消费者真实接入、GDD/spec 停止条件、原型可玩性约束、开发机路径与凭据扫描

### 移除

- 三份客户端插件清单 `plugin/.claude-plugin/`、`plugin/.codex-plugin/`、`plugin/.zcode-plugin/`
- `plugin/skills/` 下 28 项技能及其全部 `agents/openai.yaml`
- frontmatter 中的 `disable-model-invocation` 与 `argument-hint`
- 记录运行层 `plugin/records/`（21 个 Python 模块：任务读写、后端同步、迁移、恢复、安全切换、可玩交付接缝）
- `plugin/internal/`（域合同、调用合同、阶段资料入口）、`plugin/templates/`
- `dist/` 全部 tar 包与构建、可复现核验脚本
- `legacy/`（含 11 个会被官方 CLI 误发现为有效技能的游离 `SKILL.md`）、`acceptance/`、`samples/`、`examples/`
- `docs/installation/` 六个客户端安装页、`docs/skills/` 面向人的技能页、`docs/reference/compatibility.md` 客户端兼容矩阵、`docs/development/architecture.md` 插件架构说明
- 只验证已退役结构的约 55 个 pytest 文件与支持模块
- 退出且没有等价能力：`game-producer` 的全项目进度盘点、`game-init` 的资料迁移与安全切换、`game-design` 的三段式设计接缝与设计快照、记录层的程序级幂等恢复与跨后端一致性

### 行为变化

- 安装路径唯一：`npx skills@latest add LC-86/MyGameStudio`。旧的 tar 下载、SHA256 校验与各客户端 plugin add 命令全部失效
- 8 个用户入口与 12 个按需方法保留为行为边界，但改为**指令层约定**：不再依赖宿主专属调用开关，因此不具备跨宿主强制隔离能力，该限制在 README 与技能描述中如实披露
- 技能间调用措辞中性化：有真实调用能力就使用，没有同名工具但方法文件可读时按已安装路径取得正文并使用；指向其他技能正文的引用改为真实相对链接
- 共享资料单一所有者：文档分流与增量协作、子代理委派、技能写作归 `docs-gamestudio`；人机责任与验收交接归 `tasks-gamestudio`。取消 V2 中每项技能各带一份的共享文档副本
- 任务读写改用项目已有工具，由 `setup-gamestudio` 记录实际约定；写入结果未知先回读，部分成功分别报告，不假定多文档原子写入
- `merge-gamestudio` 取消旧版“必须解决、全部暂存并提交”的硬性流程：无法可靠合并时保留双方版本并说明取舍，禁止全量暂存无关改动
- `prototype-gamestudio` 明确玩法原型默认交付真正可玩的浏览器小游戏，真实输入驱动规则、状态与结果，不是状态面板、静态图片或应用式仪表盘
- `review-gamestudio` 两轴消费同一份完整待交付材料，含未提交、新建、删除与资源变化；不为取得版本标识强制提交
- `tdd-gamestudio` 的 `tests.md`、`mocking.md` 移入 `references/` 以统一随包资料布局
- CI 改为运行 V3 静态检查与文档导航检查，不再构建或核验插件包

### 合并前审查修正

- 修正 `docs/installation.md` 的固定引用说明：`owner/repo@x` 的 `@x` 是**技能筛选**，仓库仍按默认分支克隆；Git 引用来自 `#<ref>` 形式。结果取决于参数组合：`add LC-86/MyGameStudio@release/v3` 单独执行时筛选匹配不到，报 `No matching skills found` 并退出 1；加上 `--skill '*'` 后通配绕过筛选，退出 0 并装到默认分支的全部旧技能（实测 `Found 39 skills`，等于 V2 树 `plugin/skills/` 28 项 + `legacy/plugin-skills/` 11 项），锁文件不记引用
- `delegation.md` 与 `docs-gamestudio` 不再把「子代理不含父历史」写成通用事实，改为宿主属性，并给出 Codex `spawn_agent` 默认 `fork_turns=all` 的反例与核实、披露要求
- `scripts/behavior-fixtures.sh` 不再对调用者传入的目录做无条件递归删除：先校验 CLI 与目标安全，遇已存在的非空目录直接退出且不删任何内容
- 新增 `scripts/resolve-skills-cli.sh`，两个脚本共用；按版本号在 npx 缓存中匹配，不再绑定某台机器的缓存哈希
- 新增 `tests/test_maintenance_scripts.py`，把上述四类问题固化为回归断言

### 第二轮合并前审查修正

- `scripts/behavior-fixtures.sh` 的场景名此前未校验，`../victim` 能绕过输出根的非空检查并覆盖同级既有工程。改为在任何写入前校验全部场景名（禁止分隔符、上级与非法字符）并断言目标位于输出根内；参数校验移到 CLI 解析之前，使拒绝路径不依赖网络或缓存
- `.github/workflows/check.yml` 与 `release.yml` 原先只运行显式列出的两个测试文件，新增回归文件即使失败也不会阻止检查通过。统一改为收集整个 `tests/`
- S08 夹具原先假定初始分支只能是 `main`/`master`，在 `init.defaultBranch=trunk` 的环境下无法建立冲突现场。改为 `git init -b main` 显式固定并记录实际分支，冲突现场未成功建立时报错退出
- 误装证据补回决定结果的参数：`add owner/repo@x` 单独执行时筛选匹配不到会退出 1，只有同时给 `--skill '*'` 才绕过筛选、退出 0 并装到默认分支。`docs/validation-v3.md`、`docs/installation.md`、`docs/development/releasing.md` 同步区分两种结果
- 修的过程中另发现并修掉：macOS 上 `/tmp` 符号链接导致的路径包含检查误判（统一 `pwd -P`），以及 `$VAR` 紧跟全角标点时 bash 把多字节字符读进变量名造成的 unbound variable
- 回归测试从 10 项增至 18 项，含真实越界行为测试与「默认入口必须收集到每个测试文件」的断言；静态检查共 56 项通过

### 第三轮合并前审查修正

- 修掉第二轮自身引入的回归：输出路径规范化失败时回退到未规范化的原始字符串，使 `missing/../victim` 能绕过非空检查——用的是合法场景名，第二轮的场景名过滤拦不住。改为拒绝任何含 `..` 组件的输出路径，沿已存在的最深祖先做 `pwd -P` 规范化，规范化不了直接拒绝而不回退；校验阶段不创建任何目录。顺带让相对路径也被正确规范化
- 新增两项行为回归测试：`missing/../victim` 被拒且既有文件与目录结构不变；缺失中间目录但不含 `..` 的合法嵌套路径不被误拒
- 静态检查共 58 项通过

### 第四轮合并前审查修正

- 修掉一个既存缺陷：输出目录可写但不可列出内容（如权限 `0311`）时 `ls -A` 失败且输出为空，非空检查把「列不出来」当成「是空的」放行，继续覆盖目录中已有的夹具文件。改为只有成功枚举且结果为空才确认可写；枚举失败立即拒绝并保留 `ls` 的实际错误
- 同类 fail-open 一并收口：受保护路径的 `HOME`/`REPO` 物理解析失败原先用 `|| continue` 跳过比对，改为直接拒绝；夹具的 `git init`、初始分支探测、提交身份设置与 `git add`/`commit` 全部去掉 `|| true`，任一失败即中断并指明是哪个场景
- 新增两项测试：真实 `chmod 0311` 的不可枚举目录行为测试（`finally` 恢复权限，root 下跳过），以及静态禁止守卫条件吞掉命令退出码的断言
- 静态检查共 60 项通过

### 第五轮合并前审查修正

- 修掉第四轮自身引入的回归：`make_project` 放在 `||` 左侧之后，函数体内的 `set -e` 失效。项目目录创建失败时，后面的 `git init` 和相对路径写入会落到调用者的当前目录，并覆盖那里已有的文件。改回独立调用；`mkdir`、`cd`、文件写入和 git 步骤失败都直接退出，`cd` 失败后不再继续
- 新增三项回归测试：目录创建失败（`mkdir` 返回 73）时调用者目录保持原样；目录不可进入时停在 `cd`；正常生成仍写出基线提交，且不碰调用者目录
- 静态检查共 63 项通过

### 第六轮合并前审查

- 无新发现：Standards 与 Spec 均通过，审查结论为可以合并。本轮无修订，因此没有对应提交

### 合并与发布

- PR #80 以 merge commit `fd3d894` 合入 `main`，保留 9 个提交不 squash，使五轮修复各自成为历史中的一个检查点。`release/v3` 分支已在发布后删除（远端与本地），9 个提交作为该合并提交的父链继续在 `main` 历史中可达，审查往返本身记在 PR #80 与 `docs/validation-v3.md` 第 6 节
- 创建 `v3.0.0` 附注标签与对应 GitHub Release。V3 没有构建产物，Release 不挂 tar 包，发布内容就是仓库里 `skills/` 下的 20 项技能；标签创建后 `add LC-86/MyGameStudio#v3.0.0` 复测通过，装到的正是本版 20 项
- 合入后对**真实远端内容**复跑验证：SSH 全新克隆上 `scripts/install-smoke-test.sh` 19/19 通过（来源标识 `fd3d894-clean`）；`add LC-86/MyGameStudio` 从默认分支实测装到 20 项本版技能；`#<ref>` 固定引用用 `#v2.0.2`（39 项旧名）与 `#release/v3`（20 项新名）各测一例，证明引用确实决定内容
- 据此关闭两项此前记录的未验证：远端来源安装、`#<ref>` 端到端安装。同时修正 `docs/installation.md` 中一处与实测不符的说法：`skills-lock.json` 并不记录 `ref` 与 `sourceUrl`，也不记录提交 SHA
- 2.0.2 及更早版本停止维护，不再修缺陷；`v2.0.2` 标签与其 Release 仅作历史留存，已在其 Release 说明原文之前前置追加停止维护标注（原文与 3 个资产均未改写）。需要旧内容按固定引用 `LC-86/MyGameStudio#v2.0.2` 取得
- 静态检查 64 项通过，文档导航与版本一致性检查通过

## 2.0.2 — 2026-09-17

已发布：[v2.0.2](https://github.com/LC-86/MyGameStudio/releases/tag/v2.0.2)

安装包：`dist/mygamestudio-2.0.2.tar.gz`（该文件已随 3.0.0 从源码树移除，可从 Release 资产或提交 `5e3cfbf` 取得）。
不改写已发布的 [v2.0.1](https://github.com/LC-86/MyGameStudio/releases/tag/v2.0.1) 资产字节。
发布状态、安装验证状态和已知限制分开记录：Release 已发布不等于各客户端真实日常安装已验证。

### 新增

- 根目录 `LICENSE`、`THIRD_PARTY_NOTICES.md`、用户文档、示例与贡献/安全说明
- 分客户端安装页（含 Claude Code）、兼容性矩阵、数据与权限说明
- README / 安装页「复制一行即可安装」与「复制一段指令发给 Agent 来安装」（指向完整插件根；不把 `npx skills add` 写成受支持路径）
- Claude Code 清单 `.claude-plugin/plugin.json`（name/version 与 Codex、ZCode 一致，不注册 MCP）
- 文档链接检查；`scripts/build-package.sh` 把根目录许可随包
- 2.0.2 安装包携带本项目 MIT 与第三方说明，与仓库根目录文件字节一致

### 行为变化

- 无。公开入口仍是 Matt 正式 25 项加 Game-Producer、Game-Init、Game-Design
- 调用合同、技能名称与固定上游版本不变

### 迁移要求

- 无。用户游戏项目资料不因阅读或安装 2.0.2 文档整理而改写
- 本仓库的 `AGENTS.md` 只用于维护本插件仓库，不要复制到用户游戏项目
- 从 2.0.1 升级：换成完整 2.0.2 插件包后按客户端重新发现技能；不要混用不同版本的 tar 与 `package-manifest.txt`

### 已知问题

- 2.0.2 已在 Linux + Codex CLI 0.154.0 隔离目录完成 `plugin add`/`remove`；新会话技能发现、只读调用、日常 `~/.codex/` 仍未验证
- ZCode / Grok Build / Claude Code 真实安装未验证
- 已发布 `v2.0.1` 安装包仍不含根目录 `LICENSE` / `THIRD_PARTY_NOTICES.md`；上游 MIT 已在该包 provenance 内
- `.scratch/` 已从当前树移除；Git 历史中仍可能存在。仓库已公开；历史清理会移动已发布标签，须由维护者另行决定

## 2.0.1 — 2026-09-17

已发布：[v2.0.1](https://github.com/LC-86/MyGameStudio/releases/tag/v2.0.1)

- 固定上游 Matt Pocock skills 1.2.3（提交 `3cca18b368ae95cdbdebbff572ccafa662551015`）
- 公开集合：正式 25 项加三个游戏入口
- 同时携带 Codex 与 ZCode 插件清单；技能定位覆盖 Codex、ZCode 与 Grok Build 回退链
- 普通工作不使用已退役的运行保障通道
- 本地技术检查通过；真实客户端安装与新会话核验仍为未执行

## 2.0.0 — 2026-09-16

已发布：[v2.0.0](https://github.com/LC-86/MyGameStudio/releases/tag/v2.0.0)

- 2.x 线首个按新公开集合打包的版本
- 随后的 2.0.1 补了多客户端清单与定位回退

## 更早版本

0.18.x 及更早版本使用另一套公开入口与运行保障模型，不能当作 2.x 的安装或能力证明。
历史说明见提交 `5e3cfbf` 中的 `dist/CHANGELOG.md`，该文件已随 3.0.0 从源码树移除。

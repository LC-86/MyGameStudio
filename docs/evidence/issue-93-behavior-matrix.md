# Issue #93 行为证据：撤回随包副本、集合收缩为 20 项、外部共同方法改为官方依赖

本文件记录 Issue #93 在**收缩后形态**（本仓库 20 项技能 + 官方 `mattpocock/skills` 的 `writing-for-agents`，仓库不再分发任何副本）下的实测现场、命令与指纹。静态、安装与五种范围场景的通过/失败/未运行汇总在 [验证状态](../validation-v3.md) 的 Issue #93 小节；本文件只放现场、命令与逐项核对依据。

## 现场

| 项 | 值 |
|---|---|
| 日期 | 2026-09-27 |
| 宿主 | DeepSeek Harness（DSH）0.1.7-rc.1（`dsh --version`）；macOS 27.0（Darwin 27.0.0 arm64，Build 26A428） |
| 模型 | 机制类场景不调用模型；行为会话由 Lead 用真实子代理运行，见「行为会话」一节 |
| 技能库版本 | 冻结快照 HEAD `c084a1720636c60e735f7cab3d02889e13d58bea` + 本票改动（当时的未提交工作树，随后作为 `77d4bf0` 提交并推送）；`VERSION` = 3.0.3（未发布、未打标签）。冻结口径：索引树 `git write-tree` = `6315235b7eb3ea4c4504e30b1caafa1ac3499932`（staged 46 个文件，未跟踪仅 `.cursor/`、`.zcode/`）。冻结后只有两个记录文件（本文件与 `docs/validation-v3.md`）继续改动，随后与冻结内容一起提交为 `77d4bf0`，其余路径未再变动 |
| skills CLI | 1.7.0；`node v24.19.0`、`npx 11.17.0`；实跑走本机已缓存的同版本入口 `~/.npm/_npx/*/node_modules/skills/bin/cli.mjs`（缓存目录名随机器变化，不记录具体哈希），另有两次按任务原文走 `npx --yes skills@latest` |
| Python | 3.12.4（`python3.12`） |
| 隔离方式 | 五种范围场景各自 `HOME=<mktemp 临时目录>`、项目也在临时目录；未写入真实 HOME、未写入真实项目、未 `git commit`/`push` |
| 夹具 | `bash scripts/behavior-fixtures.sh /tmp/mgs-v93/fixture`（10 个默认场景，exit 0） |
| 证据位置 | `/tmp/mgs-v93/`（临时目录，随系统清理失效）；复跑脚本 `/tmp/mgs-v93/rerun.sh` |

## 来源与指纹

官方来源在两处范围内使用两个不同 ref，全部由官方 `mattpocock/skills` 提供：

| 对象 | 提交 | 逐文件 SHA-256 |
|---|---|---|
| 官方 `writing-for-agents`（默认分支 HEAD） | `c55ee46073ed923f86ce59a5eb3b6d895095d1b7` | `SKILL.md` `551adca942227b44192edba88acd4e8db911f0121ce58ad16944ccf6a896a74a`；`SKILL-MECHANICS.md` `c768e6307c7c10728c401c213f2c4ba71c542127eeb7ad2956aabd15a0fa0059`；`agents/openai.yaml` `eacb24b2a618cfb81dacb0416f4fdd75ddf3a8060f8ddb99aae1b1e301907e4b` |
| 官方 `writing-for-agents`（`#v1.2.3`） | `6acc160e4e0cd062dbbbd7a1b26ae92855edf07e` | `SKILL.md` `a842323e664e5af104eac5c97ad22fda929ebeb62d81c501161ac1f6f482db58`；`SKILL-MECHANICS.md` `b4c54a0aaad3f6eddefde6d06770a0e401fbb8fc6a8f49ce18af816bd144d14d`；`agents/openai.yaml` 同上一行 |

`v1.2.3` 的两个哈希不是从安装结果反推的：另用 `git clone --filter=blob:none --no-checkout https://github.com/mattpocock/skills` 取官方仓库，`git cat-file blob v1.2.3:skills/productivity/writing-for-agents/SKILL.md | shasum -a 256` 独立得到 `a842323e…`，与项目级安装结果一致。

本仓库与远端当前形态（同一工作树、两个不同事实，分开记录）：

| 对象 | 实际值 |
|---|---|
| 工作树 `skills/` | 20 项目录，无 `skills/writing-for-agents/` |
| 工作树全树 | 无 `SOURCE.md`、无 `SHA256SUMS`（`find . -name SOURCE.md -o -name SHA256SUMS`，排除 `.git` 后为空） |
| 工作树 `VERSION` | `3.0.3` |
| `origin/main`（`gh api repos/LC-86/MyGameStudio/contents/skills --jq length`） | **21 项**，仍含 `skills/writing-for-agents/`（`LICENSE`、`SHA256SUMS`、`SKILL-MECHANICS.md`、`SKILL.md`、`SOURCE.md`、`references`） |
| `origin/main` 的 `VERSION` | `3.0.2`（main = `06f8f1110ff145a00c05915da0206c8880fbe92b`，2026-09-26） |
| 远端标签 | 最新 `v3.0.2`；**无** `v3.0.3` 标签 |
| `.tmp/accept-18/upg/installed-old-snapshot/` | 早期验收遗留、未跟踪、被 `.gitignore` 的 `.tmp/` 忽略；内含 20+ 个旧形态 `SKILL.md` 与一份 `writing-for-agents`。本次**未清理**；smoke 第 9 节 `--full-depth` 实测发现数仍为 20，不进入发布集合 |

## 静态与安装（命令与实际输出）

全部命令在本机工作树实跑，输出逐条抄录：

| 命令 | 实际输出 | 覆盖范围 |
|---|---|---|
| `python3.12 -m pytest tests/ -q` | `85 passed in 8.24s`（exit 0） | 20 项目录契约、调用控制、所有者、消费者接入、缺方法处理、保真/委派契约、退役守护与组合安装契约 |
| `python3.12 -m pytest tests/ -q --collect-only \| tail -3` | `85 tests collected in 0.02s` | 收集数量与默认入口 |
| `python3.12 scripts/validate-docs.py` | `OK: 文档导航、链接、版本与退役命令检查通过（43 个文件，20 项技能）`（exit 0；43 已含本文件） | 文档导航、链接、版本一致与退役命令 |
| `find skills -maxdepth 1 -mindepth 1 -type d \| wc -l` | `20` | 集合恰为 20 项 |
| `find . -name SKILL.md -not -path './.git/*'`（排除已忽略的 `.tmp/`） | 恰 20 条，全在 `skills/<name>/SKILL.md` | 无游离技能入口 |
| `grep -rl 'disable-model-invocation: true' skills/*/SKILL.md` | 8 项（`ask`、`grill`、`grill-…-docs`、`handoff`、`implement`、`setup`、`tasks`、`wayfinder`） | 8 个用户入口的三层控制第一层 |
| `find skills -name agents/openai.yaml` | 8 份，与上一行同名集合一致 | Codex 侧开关；12 个按需方法无宿主文件 |
| `find . \( -name SOURCE.md -o -name SHA256SUMS \) -not -path './.git/*'` | 空 | 随包副本的清单文件已退出 |
| `bash scripts/install-smoke-test.sh` | `PASS 33 / FAIL 0`（exit 0；CLI 1.7.0，来源标识 = 工作树 HEAD + dirty） | 完整安装、许可、引用可达、依赖组合、子集缺依赖、链接模式、二次安装、#90 接缝与第 10/11 节两来源组合 |

安装 smoke 的关键观察（冻结快照实测 `PASS 33 / FAIL 0`）：

- 第 8 节的「不写入或替换同名共同方法」负例，实际输出顺序为：`PASS 官方外部共同方法先装入临时消费项目并记录逐文件 SHA-256` → `PASS 本仓库完整安装只贡献 20 项技能目录，不夹带 writing-for-agents` → `PASS 官方副本逐文件 SHA-256 与安装前一致（3 个文件未被改写或替换）` → `PASS 项目锁记录：writing-for-agents 来源仍是 mattpocock/skills，其余 20 项来自本仓库`。
- 第 8 节同时解析接缝：外部共同方法唯一解析到已安装的官方副本 `<安装目录>/writing-for-agents/SKILL.md`；写作者 17 项、保真接入 14 项、委派接入 8 项；全树 0 条指向该方法的跨范围相对链接。

## 五种范围场景

全部在临时目录 + 临时 `HOME` 内进行；`npx --yes skills@latest` 走真实 CLI 1.7.0 与真实 GitHub。

| 场景 | 命令要点 | 实际观察 | 结果 |
|---|---|---|---|
| 用户级 | `HOME=<tmp-home>` 下 `npx --yes skills@latest add mattpocock/skills --skill writing-for-agents --agent universal --copy -g -y`，再 `add <仓库> --skill <20 项> --agent universal --copy -g -y` | `$HOME/.agents/skills` 共 **21 项** = 20 项 GameStudio + 恰 1 份官方方法（`SKILL.md` `551adca9…`）；用户锁 `$HOME/.agents/.skill-lock.json` **只有 1 条**（`writing-for-agents → mattpocock/skills`） | 通过；用户锁 20 项无记录是 CLI 行为，见下 |
| 用户级·远程来源对照 | 另一临时 HOME 执行 `add LC-86/MyGameStudio --skill '*' --agent universal --copy -g -y` | **21 项**目录、锁 **21 条**，全部 `source: LC-86/MyGameStudio`、`sourceType: github`，其中包含 `writing-for-agents`（远端默认分支当时仍分发随包副本） | 通过（对照） |
| 项目级 | 临时项目根先 `add <仓库> --skill <20 项> … -y`，再 `add mattpocock/skills --skill writing-for-agents … -y` | 目录 21 项；项目根 `skills-lock.json` 21 条 = 20 条 `sourceType: local`（`source` 为指向仓库的相对路径）+ 1 条 `mattpocock/skills`（`computedHash 95da47fc97af…`）；只有 1 份 `writing-for-agents`，内容为官方指纹 | 通过 |
| 混合范围 | 用户级装官方方法，项目级只装 20 项 | 用户级 1 项、锁 1 条；项目级 20 项、锁 20 条且**无**方法记录；项目 `.agents/skills/` 内没有 `writing-for-agents`；20 项正文里指向该方法的相对链接 **0 条**，按技能名称写明 **17 项**（不写的 3 项是 `grill-gamestudio`、`grill-gamestudio-docs`、`grilling-gamestudio`，与「访谈入口不直接取得」的既有读法一致） | 通过；「宿主按名称自动加载」见限制 |
| 缺失依赖 | 临时 HOME + 只装 20 项 | 目录 20 项、锁 20 条、无方法记录；临时 HOME 下未产生 `.agents`；安装输出 136 行里 `writing-for-agents`/`mattpocock`/`github` 各出现 0 次；仓库 `git status --porcelain` 的 SHA-256 前后一致；缺方法处理句「无法取得时说明具体缺口和受影响的工作，只继续不依赖它的部分，不模仿缺失的方法」覆盖 16/20 | 通过 |
| 范围冲突 | 用户级官方 HEAD 与项目级官方 `#v1.2.3` 各一份 | 两份副本指纹不同（`551adca9…` vs `a842323e…`）；项目锁记 `source: mattpocock/skills`、`ref: v1.2.3`、`computedHash ccfa1e94d8f6ab5c…`；随后在同项目再装 20 项，两份副本逐文件 SHA-256 前后 **完全一致**（`diff` 无输出） | 通过（安装侧不修改任一副本）；宿主实际加载版本见限制 |

上表是冻结快照（03:55 起）的复跑结果；与冻结前在同一工作树上的两次运行逐项一致（目录数、锁记录数与来源、两份副本的逐文件 SHA-256、安装输出 136 行与 0 次方法名提及）。唯一的运行间差异是锁里的 `skillFolderHash`，见「未运行与限制」第 10 条。

### 用户级：锁记录边界（CLI 1.7.0 行为）

- 实测：`$HOME/.agents/skills` = 21 项，而 `$HOME/.agents/.skill-lock.json` = `{"version": 3, "skills": {…1 条…}, "dismissed": {}}`，唯一记录为 `{"source": "mattpocock/skills", "sourceType": "github", "sourceUrl": "https://github.com/mattpocock/skills.git", "skillPath": "skills/productivity/writing-for-agents/SKILL.md", "skillFolderHash": "ad2925850efb8973a72d2e666f7a975f9a2d4a9b", …}`。
- CLI 源码依据（读 `cli.mjs`，非推断）：`const normalizedSource = directDownload ? null : getOwnerRepo(parsed);`，而 `getOwnerRepo` 对 `parsed.type === "local"` 返回 `null`；全局锁写入的判据是 `if (successful.length > 0 && installGlobally && normalizedSource)`。所以本地 checkout 来源的 20 项在用户级**没有**锁记录，只影响锁文件，不影响安装结果。
- 对照：远程来源（`LC-86/MyGameStudio`）在用户级写满 21 条记录，证明差异来自「来源能否解析出 `owner/repo`」，不是技能数量或安装失败。
- 记录口径：这不是收缩缺陷；[安装说明](../installation.md) 已写明该边界。

### 缺失依赖：缺方法处理句的实际覆盖

- 20 项正文里含该句的是 16 项；不含的 4 项 = `docs-gamestudio`（`install-smoke-test.sh` 第 10 节以 `--gap-exempt` 声明的方法所有者）+ 3 个访谈入口（第 10 节以 `--silent` 声明「不得提到方法名」，实测这 3 项正文确实一次也不出现方法名）。
- 反向核对：没有任何**未声明**的正文带这句，也没有任何声明的写作者缺这句（17 项写作者 − `docs-gamestudio` 1 项例外 = 16 项，与实测一致）。

### 范围冲突：副本身份

- 用户级副本 = 官方 HEAD：`551adca9…`（`SKILL.md`）、`c768e630…`（`SKILL-MECHANICS.md`）、`eacb24b2…`（`agents/openai.yaml`）。
- 项目级副本 = 官方 `v1.2.3`：`a842323e…`、`b4c54a0a…`、`eacb24b2…`；`SKILL.md` 额外与我用官方 clone 独立算出的 blob 哈希一致。
- 两份副本除 `agents/openai.yaml` 外内容不同，说明测的确实是两个版本，而不是同一份被安装两次。

### 8/12 分层与 Codex 开关（静态实测）

- 8 个用户入口的 `agents/openai.yaml` 逐份读取，内容恰为两行 `policy:` + `  allow_implicit_invocation: false`（含/不含末尾换行两种都判等），无一份额外字段。
- 8 个用户入口正文都有 `disable-model-invocation: true`；12 个按需方法既没有 `agents/` 目录，正文也不出现该字段。

## 行为会话（Lead 派发，verifier 记录）

**来源与身份**：本节 12 个会话由 **Lead** 用真实子代理会话（DSH 0.1.7-rc.1）派发；**verifier 没有运行这些会话**，只按 Lead 提供的固定输入原文与结果整理，并另行核对可独立核对的文件事实（副本身份、哈希一致性、锁与目录数量）。会话是「被明确告知可用范围后按路径读取技能正文」，不是宿主按名称自动加载（见「未运行与限制」第 1 条）。

| 项 | 值 |
|---|---|
| 夹具命令 | `bash scripts/behavior-fixtures.sh /tmp/mgs-issue93 S01-ask S03-routing S04-partial-save NOMETHOD-routing` |
| 夹具形态 | 每个项目 `.agents/skills/` 21 项（20 项 GameStudio + 官方 `writing-for-agents`）；重复会话各自独立副本 `/tmp/mgs-issue93/runs/<场景>-<a\|b>/project`；S04 两份把 `docs/specs` 设为 `dr-xr-xr-x`、spec 文件设为 `444`；`NOMETHOD-*` 项目不含方法（20 项） |
| 混合范围 | 项目级只有 20 项；官方方法装在临时用户级 `/tmp/mgs-issue93/userhome/.agents/skills/`，其 `SKILL.md` SHA-256 = `551adca942227b44192edba88acd4e8db911f0121ce58ad16944ccf6a896a74a`（与本文「来源与指纹」里我独立取得的官方 HEAD 指纹一致） |
| 统一派发框架（逐字） | 「可用技能只有 <项目>/.agents/skills/ 下的技能，不要到别处按名称取技能；只修改项目内文件；不 git commit/push/checkout；按技能正文工作，缺资料如实说明；报告①②③④：读取的技能文件全路径／改了哪些文件／实际失败与缺口（含原始错误）／明确没做的事」 |

固定输入（逐字，未改写）：

- **S03 / S04 / NOMETHOD / 混合范围**：「请使用项目里的相关技能处理下面这件事。／潮汐潮池继续推进，这几点要落下来：死亡就结束当前一局，可以早于 3 波结束；再加一条长期规则——永久解锁的内容跨局保留。连击倍率上限我们从 5x 改成 7x，先按试验手感算，不要当成定稿。这一版只做第一关的结算面板，先不碰美术，纯文本占位。／把该写进文档的内容写到项目里，现有的 GDD、spec 和术语表按项目约定更新。」（S04 两个会话**没有** 5x→7x 那一句）
- **S01（预期不触发）**：「请使用 ask-gamestudio。／我想继续推进当前游戏项目，但不确定现在最该做哪一件事。」
- **S05（委派）**：「请使用项目里的相关技能处理下面这件事。／我要把「第三波猎物生成节奏」这一项设计决定的资料查证交出去：请把这件事派发给一个独立子代理去做，并把它交回的结果核对后给我结论。派发说明我要能直接看懂、也能原样转给别人用。／如果你所在会话能真正启动子代理，就直接派发；如果不能，就把完整派发说明写出来，并明确说明没有发生真实派发、因此哪一步核对无法完成。」

### 场景结果

| 场景 | 会话数 | 实际结果（Lead 报告） | Lead 的独立核对（非会话自述） |
|---|---|---|---|
| S01-ask（不触发） | 2 | 两个会话都停在「先确定最该做的一件事」，没有落盘、没有改文件 | 两份夹具 `git status` **零改动** |
| S03-routing | 2 | 把长期规则、试验值与本次范围分别落到 GDD、spec 与术语表 | 改动只落在 `CONTEXT.md` + GDD + spec |
| S04-partial-save | 2 | 两次重复**结果分叉**：a 会话 `chmod u+w` 后写入 spec；b 会话拒绝 `chmod`，报告原始 `Permission denied` | a：spec `582 → 1674` 字节、SHA-256 `7eb40fe5… → 160c98ce…`；b：spec 仍 `7eb40fe5…`、权限仍 `-r--r--r--`；b 只改了 `CONTEXT.md` + GDD |
| NOMETHOD-routing | 2 | 两次重复**结果分叉**：a 会话越出文档范围改了代码；b 会话没有改代码 | a：改 `src/game.js`，新增 `src/settlement.js`、`tests/`、`tasks/03-settlement-panel/`；b：未改代码，只动文档 |
| 混合范围 | 2 | 用户级官方方法 + 项目级 20 项的组合下完成同一段输入 | 改动只落在 `CONTEXT.md` + GDD + spec；项目内 `.agents/skills` = 20 项、无同名副本；会话后用户级官方副本 SHA-256 仍 `551adca9…` |
| S05 委派 | 2 | 两个会话都因宿主 `maxDepth=1` **无法自行派发**（原始错误 `Error: subagent depth 2 exceeds maxDepth 1`），但都产出了符合 `delegation.md` 七类字段的完整派发说明 | verifier 读了两份说明逐条核对字段覆盖与指纹；真实派发由 Lead 逐字转给全新接收方，交回产物 256 行 / 34,790 字节 / `52b2cd5b…`，只新增未跟踪目录。详见下一小节 |

**两次重复的分叉如实记录，不写成「合规」**：同一固定输入在 S04 与 NOMETHOD 各跑两次，得到不同结果。S04 的分叉点是「被权限挡住时是否自行 `chmod`」；NOMETHOD 的分叉点是「缺外部共同方法时是否越出文档范围去改代码」。两次都各有一次符合预期、一次偏离预期，说明单次会话结果不能当作稳定性结论。

### 保真逐项核对（Issue #89 Testing Decision 12；Lead 对照固定输入与运行产物）

被核对的是**会话结束后保留下来的运行产物**，不是会话自述：`/tmp/mgs-issue93/runs/S03-routing-a/project`、`S03-routing-b/project`（同一固定输入，含 5x→7x 那一句）与 `S04-partial-save-a/project`（固定输入**没有** 5x→7x 那一句，spec 从 582 字节写入为 1674 字节）。Lead 直接读取这三个项目的 `git diff` 逐项对照，未改动产物；产物位于临时目录，随系统清理失效。

| 项目 | 固定输入 | 产物实际值 | 判定 |
|---|---|---|---|
| 数值 | 前摇 `0.4 秒`、潮水 `12 秒`、前 `4 秒`低潮、`3 波`、连击上限 `5x → 7x`（S04 无此句） | 三份都保留 `0.4`／`12`／`4`；`3 波` 在 S03-a／S03-b 改写为「最多 3 波」并保留死亡可早于 3 波，S04-a 保留原句另立死亡规则；S03-a／S03-b 把倍率写成「试验值 `7x`（由 `5x` 调整），未验证、未定稿」；S04-a 仍是 `5x`——它没有凭空补上输入没给的 7x | 保真 |
| 单位与量词 | 秒、波、倍率 | 三份都保留原单位与量词，没有换算或省略 | 保真 |
| 条件 | 死亡「结束当前一局」、可以早于 3 波结束 | 三份都写出该条件与先后关系；「死亡触发条件」在三份里都列为未决，没有自行定义 | 保真 |
| 顺序 | 死亡结束本局与其触发时机；本版范围是结算面板 | S03-a 把「死亡结束的一局是否进入结算」列进未决；S03-b 与 S04-a 直接把「死亡也进入结算」写成规格条目 | **新增未标注的推断**（见下） |
| 例外与排除项 | 「这一版只做第一关的结算面板」「先不碰美术，纯文本占位」 | S03-a／S03-b 新增「本次不做」小节，S04-a 在交付段写明纯文本占位；三份都把美术资源排除在本版之外 | 保真 |
| 责任 | spec 原有的 Agent／开发者两类验收 | 三份都保留开发者试玩项，未被 Agent 项替代；新增验收都挂在 Agent 名下 | 保真 |
| 确认状态 | 长期规则＝已确认；`7x`＝试验手感、不是定稿；死亡惩罚候选 A/B＝尚未采纳 | 长期规则分别落为 GDD「长期规则」／「长期进度」；`7x` 保留「试验值、未验证、未定稿」；候选 A/B 仍是「尚未采纳」 | 保真 |
| 原始证据 | 用户原话与项目既有文件 | S03-a／S03-b 的依据行指向 GDD 的「已采纳规则」「长期规则」「未决」；S04-a 每条行为要求都带「依据 GDD…」；未决项逐条列出 | 保真 |

**这一表里唯一不判保真的项**：S03-b 与 S04-a 把「死亡的一局进入结算」写成了规格条目，而固定输入只说了「死亡就结束当前一局」，没有说它进结算。S03-a 把同一处列为未决，因此这是两次重复会话之间真实存在的处置差异，不写成双方都保真。它的影响限于推断被读成规则；两份产物都没有把候选值、试验值或未验证项升级成已确认，也没有把未实现写成已实现。

产物指纹（Lead 实测，`shasum -a 256`）：

| 产物 | diff | `docs/specs/2026-09-10-first-level.md` | `docs/design/GDD.md` | `CONTEXT.md` |
|---|---|---|---|---|
| `S03-routing-a` | 3 files, +25/−5 | `e11ba2bb1008…` | `dbeeef090930…` | `ef3f31703287…` |
| `S03-routing-b` | 3 files, +20/−5 | `c9f794e938b2…` | `98d87e76aaaa…` | `062a789ef3c8…` |
| `S04-partial-save-a` | 2 files, +19/−1 | `160c98cee61b…`（与场景结果表记录的写入后 SHA-256 一致） | `33a674b327d3…` | 未改动 |

### S05 委派：派发说明质量 / 真实派发 / 结果回收核对

**① 派发说明质量（两个干净会话各自产出，均未发生真实派发）**

- 两个会话调用 `subagent`、`subagent_fork` 都被宿主拒绝，原始错误：`Error: subagent depth 2 exceeds maxDepth 1`（会话自身已是深度 1，宿主 `maxDepth=1`）。S05-a 在说明里写明了未试其他派发路径的理由，并明确「核对交回结果这一步**无法执行**：没有交回结果」。
- 两份说明都覆盖 `docs-gamestudio/references/delegation.md` 的七类内容。verifier 自己读了这两份文件核对（不是按关键词匹配）：S05-a 的小标题依次是 目标／来源版本／接收方可访问的输入／上下文／允许的路径与操作／自主空间／需要带回确认的事／需要交回的证据／受阻时怎么办／结果回收核对；S05-b 是 目标／交付物与完成条件／来源版本与工作树／可访问输入／上下文／允许的路径与操作／接收方可自行决定／须带回确认／须交回的证据／受阻时／结果回收核对。
- 落盘位置与指纹（verifier 实测）：S05-a 说明在 `/tmp/mgs-issue93/runs/S05-subagent-a/project/docs/research/2026-09-27-third-wave-spawn-pacing-dispatch-brief.md`，5,825 字节，SHA-256 `02d8f4cf396bbe7c70beb264f7b19cf3704a88b799a9729eec64dba926d8c4dc`；S05-b 说明在 `/tmp/mgs-issue93/S05-subagent-b-dispatch.md`，4,446 字节，SHA-256 `bd875e548ebdc75121a2874d65ab09914350db18f93eea33d4f860b6fb617808`。
- 两者都没有伪造派发，也没有把自查当成独立核对；S05-b 的「须交回的证据」还要求接收方报告「是否看到派发者的会话历史」。

**② 真实派发（由 Lead 作为宿主／传输方执行，不是原派发会话本人）**

- 原派发会话是已结束的子代理，无法恢复（`send_message` 报 `active teammate ... not found`），因此「结果回收核对」不是由原派发者执行——这一点是限制，不能写成等价流程。
- Lead 把 S05-b 的派发说明**逐字**转发给一个全新的接收方会话（除该说明与项目工作树外没有任何背景）。
- 接收方交回 `/tmp/mgs-issue93/runs/S05-subagent-b/project/docs/research/2026-09-10-third-wave-spawn-pacing.md`。**verifier 独立实测**：256 行 / 34,790 字节 / SHA-256 `52b2cd5bbc9ea6e3021c097d30723c64e1ee196451f99da27302c13010ae379b`；该项目 `git status --porcelain` 只有 `?? .agents/` 与 `?? docs/research/`，`git diff --stat` 为空（受跟踪文件零改动），与「只新增未跟踪目录」一致。
- 接收方的交付形态：每条结论标注「来源所述／我的推断／待验证假设」；候选取值明确写「未采纳」；`web_fetch` 对外链一律报 `resolves to a non-public IP address`（改用 curl 后同批 URL 200），另有 fandom 直连 403、GameFAQs 403、PMC reCAPTCHA、`eric.ed.gov` 空响应等失败如实列出；俯冲周期缺失导致间隔下限无法定论，列入「仍需本项目实测或由人决定」；并自报上下文隔离成立。

**③ 结果回收核对（Lead 实际执行；verifier 只独立复核文件层）**

- Lead 的核对：文件与范围通过（行数／字节／哈希一致，越权写入为零，受跟踪文件零改动）；下载原始件逐条比对引文后，发现一处**页码归属不精确**——记录写「第 64/68 页给 mob 间隔 90–180 秒、20–30 只」，实测 `90-180` 在第 68 页、`20-30` 只在第 65 页检出（内容仍在同一讲稿内，不是捏造）；Hick 1952 原论文、WIRED 2018 西角友宏文与 PvZ2／VS／Devil Daggers 的游戏数据文件未取得，记录里标「未验证」。
- verifier 的边界：只独立复核了产物存在性与行数／字节／SHA-256、该项目的 git 范围结论，以及两份派发说明的字段覆盖；**没有**重新下载 PDF 复核页码与引文，因此 ③ 中除文件层以外的事实属 Lead 的核对。
- 结论：**通过（有保留）**。保留项 = 页码归属不精确、回收核对由 Lead 代行（原派发者已结束，无法恢复）、游戏数据文件类一手材料未取得。


## 其它宿主与范围边界

| 宿主 | 结论 | 原因与证据边界 |
|---|---|---|
| DeepSeek Harness（DSH）0.1.7-rc.1 | 部分通过 | 机制、安装与锁行为已实测；**宿主按名称自动加载 not-run**（第 1 条限制）。本机 `~/.dsh/skills` 全部是指向 `~/.agents/skills` 的符号链接，用户级 `docs-gamestudio/SKILL.md` 与工作树版本不同 |
| Codex | not-run（宿主内）；静态开关通过 | 本机 `codex` 存在于 `/opt/homebrew/bin/codex`，但本轮未在 Codex 内运行安装或会话（会写真实宿主状态、需要模型凭据）；Codex 侧的 `agents/openai.yaml` 8 份两行内容已逐份静态核验 |
| ZCode | not-run | 本机 `zcode` 存在于 `/Users/cuilei/Library/pnpm/bin/zcode`；未在其中运行会话。仓库里未跟踪的 `.zcode/plans/` 与本票无关，本轮未改动 |
| Grok Build | not-run | 本机 `grok` 存在于 `/Users/cuilei/.grok/bin/grok`；未在其中运行会话 |
| Qoder | not-run | 本机无 `qoder` 可执行文件（`command -v qoder` 空） |
| Claude Code | not-run | 本机无 `claude` 可执行文件（`command -v claude` 空） |

前五个宿主「发现集合与自动加载」都没有在本轮运行，因此**不能**用本文件支持「某宿主能按名称加载外部方法」这类结论。

## 未运行与限制

1. **宿主按名称自动加载：not-run。** 本机 DSH 会话能加载的技能来自真实用户范围：`~/.dsh/skills` 66 项（每一项都是指向 `~/.agents/skills/<name>` 的符号链接）与 `~/.agents/skills`；其中用户级 `docs-gamestudio/SKILL.md` SHA-256 `5b6cd9e504f9c7dd58f0e16b9aeff148483b448fe7337ac2e9535265b47ecedd`，工作树是 `cdb7825e0e83d5d72695a6f2c7610a51653b4809d79a2182ba46b72d0a006212`——宿主内可加载的是**范围之外、版本不同**的副本。DSH 的实现顺序只作代码阅读记录、不作运行证据：`dsh-skill-filesystem` 的 `roots(cwd)` 依次给出 project `.dsh/skills`(rank 100) → project `.agents/skills`(200) → custom(300) → `$DSH_HOME/skills`(400) → `~/.agents/skills`(500) → bundled(600)，`dsh-skill` 的 `compareIndexedCandidates` 按 rank 升序比较，同名时项目级在前。
2. **范围冲突里「宿主实际加载哪个版本」：not-run。** 不能把临时 HOME 的冲突形态交给真实宿主会话：真实宿主启动依赖真实 `~/.dsh` 与凭据，在临时 HOME 中启动会写入真实宿主状态或取不到配置。因此本轮只证明「两份副本确实不同」与「MyGameStudio 的安装没有改动任一副本」。
3. 范围冲突的「使用」侧只覆盖安装：真实会话读取后副本是否变化未单独测（会话在夹具内运行，夹具副本身份由 Lead 核对）。
4. 用户级场景的远程对照用的是**远端默认分支**（当时 21 项、`VERSION` 3.0.2、含随包副本），不代表收缩后的远端形态；本票只推分支、不合入 `main`。
5. 每个机制场景各跑一次，未做重复运行，单次结果不构成稳定性证明。
6. 本轮没有在真实 HOME 或真实项目中安装、卸载或修改任何东西；真实用户级安装只做只读核对（目录列举、符号链接指向、`SKILL.md` 哈希、锁记录）。
7. `.tmp/accept-18/upg/installed-old-snapshot/` 未清理（删除属破坏性操作，需单独授权）；它被 `.gitignore` 忽略，smoke 第 9 节实测 `--full-depth` 仍只发现 20 项。
8. 本机没跑的检查不代表通过：上表五个宿主、宿主自动加载、真实发布流程（打标签、发布 Release、推送 `main`）都是 not-run。
9. **退役守护不是穷尽判据，是形态启发式。** `tests/test_skills_layout.py` 的 `bundled_claim_offences()` 只在分句内匹配枚举出的中英文声明形态（计数式、随包路径、随包/镜像动词等），再按否定与历史措辞分句豁免。verifier 直接调用该函数实测了它的边界（构造串，只读运行，不改仓库）：

| 构造串 | 守护结果 |
|---|---|
| `确认整合后的技能名是 20 个 \`-gamestudio\` 名称加 \`writing-for-agents\`，共 21 项；` | 命中（`加 \`writing-for-agents\`，共 21 项`） |
| `方法入口见 \`skills/writing-for-agents/SKILL.md\`。` | 命中（`skills/writing-for-agents`） |
| `本仓库在 20 项之外还附带了 \`writing-for-agents\`。` | 命中 |
| `本仓库不再镜像旧的副本，但随包提供 \`writing-for-agents\`。` | 命中（「，」分句后第二句仍算声明） |
| `This repository ships \`writing-for-agents\` with the plugin.` | 命中 |
| `官方那个共同方法随本仓库一起安装，装完即可使用。` | **未命中**（指代式，不出现方法名） |
| `本仓库把外部写作方法一并打包发行。` | **未命中**（同义改写，不出现方法名） |
| `本仓库把 \`writing-for-agents\` 一并打包发行。` | **未命中**（动词不在形态表内） |
| `本仓库 20 项技能不含 \`writing-for-agents\`，需从官方来源单独安装。` | 未命中（否定句，预期放行） |

所以：命中即违约，未命中**不等于**表述正确；指代式与未列入反例表的同义改写能绕过。判据自身的反例表只覆盖评审构造过的有限形态，不能当成穷尽覆盖。
10. **锁里的 `skillFolderHash` 不是稳定指纹（实测）。** 同一份未改动的官方内容，用户级锁在该字段上观测到两个不同值：`ad2925850efb8973a72d2e666f7a975f9a2d4a9b`（3 次运行，含本机真实用户级锁 2026-09-22 的记录）与 `95da47fc97af998e85b7d7e6d57b3ac76727c1e290cfe9ea09005aacb826959f`（冻结快照那次运行）。远程来源 `LC-86/MyGameStudio` 同样出现 `d25671ce41f298c891d4b6a5550bc725509c6dedd8a771b0ec8fe9a4b27635fc` 与 `db319c22f7b4fadc6b257d783cc3ea58474e48be` 两值。CLI 源码里有三个分支：`getSkillFolderHashFromTree`（`blobResult` 或 `cachedTree` 可用时）与 `computeSkillFolderHash(下载目录)`（回退）——同一内容走不同分支就得到不同摘要。**本文与验证记录里的指纹只使用逐文件 SHA-256 与项目级锁的 `computedHash`**；用户级锁的 `skillFolderHash` 不作为版本或身份依据。

## 复跑方式

机制场景的完整复跑不需要仓库内脚本改动，按顺序执行即可：

```bash
# 静态
python3.12 -m pytest tests/ -q
python3.12 -m pytest tests/ -q --collect-only | tail -3
python3.12 scripts/validate-docs.py
# 安装
bash scripts/install-smoke-test.sh
# 夹具
bash scripts/behavior-fixtures.sh <空的或尚不存在的输出目录>
# 范围场景：每个场景都在临时 HOME 内
export HOME="$(mktemp -d)"; mkdir -p /tmp/s1 && cd /tmp/s1
npx --yes skills@latest add mattpocock/skills --skill writing-for-agents --agent universal --copy -g -y
npx --yes skills@latest add <仓库绝对路径> --skill $(ls <仓库>/skills) --agent universal --copy -g -y
```

## 附录：产物差异摘要

会话现场在 `/tmp/mgs-issue93/`（Lead 的夹具，临时目录，随系统清理失效）；以下事实由 Lead 在会话结束后用各夹具的 `git status` / `git diff --stat` 与文件哈希采集，供清理后复核，verifier 未复跑会话。

| 夹具 | 改动落点（Lead 核对） | 关键哈希或权限 |
|---|---|---|
| `S01-ask` ×2 | 零改动（两份都不落盘） | — |
| `S03-routing` ×2 | `CONTEXT.md` + `docs/design/GDD.md` + `docs/specs/…` | — |
| `S04-partial-save` a | `CONTEXT.md` + GDD；spec 在 `chmod u+w` 后写入 | spec `582 → 1674` 字节，SHA-256 `7eb40fe5… → 160c98ce…` |
| `S04-partial-save` b | 只有 `CONTEXT.md` + GDD；spec 未写入 | spec 仍 `582` 字节、SHA-256 仍 `7eb40fe5…`，权限仍 `-r--r--r--`（未被 `chmod`） |
| `NOMETHOD-routing` a | 越出文档范围：`src/game.js`、新增 `src/settlement.js`、`tests/`、`tasks/03-settlement-panel/` | — |
| `NOMETHOD-routing` b | 只改文档（未改代码） | — |
| 混合范围 ×2 | `CONTEXT.md` + GDD + spec；项目内 `.agents/skills` = 20 项、无同名副本 | 会话后用户级官方副本 SHA-256 仍 `551adca9…`（与安装时一致，未被改写或替换） |

`S04` 与 `NOMETHOD` 的两次重复在同一输入下得到不同产物，是本节最需要保留的事实：它同时说明「缺方法与权限受阻时行为并不稳定」，因此本票不把任何单个会话的结果外推成稳定结论。


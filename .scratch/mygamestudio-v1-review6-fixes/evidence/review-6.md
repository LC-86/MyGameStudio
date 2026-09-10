# MyGameStudio v1 第六轮独立复审

**交付判定：SP-14～SP-16 的原始反例均有真实修复；新增反例确认 3 项 P2，当前不具备 v1 收口条件。** SP-17 是新旧登记布局混用的清理缺陷；SP-18/19 是本轮新确认、批次前也存在的 curl 锚定边界。Standards 轴 0 硬违反、0 报告级异味；Spec 轴 3 项 P2。指定历史原探针、五套件、33 驱动、留存 10/10、可复现打包和每票绿→红→绿均通过，不能扩写成全部历史合同零回退。

执行日期：2026-09-10（Asia/Shanghai）。采用 code-review 技能的独立 Standards / Spec 双轴审查，主审执行回归、历史探针、变异及交叉复现。“零模型调用”沿上一轮报告口径指零产品/验收模型轮；独立审查使用本任务的两名审查代理。

- 真实仓库：`/Users/cuilei/MyOS/01_Projects/plugins/MyGameStudio`。
- 固定比较：`git diff 1eef7d8..a3c43ce`，恰 `3e876e2`、`a3c43ce` 两提交；该祖先关系下与 three-dot 相同。完整差异见 [batch.diff](/tmp/mgs-review6-zonhimd1/batch.diff)。
- 开始、结束 HEAD 均为 `e68ef7d0c8ee212d39419827fd0a46f66ad9c0ec`，`git status --porcelain` 均为空；相对产品目标 `a3c43ce` 只多 `review-6-handoff.md`，无产品差异。
- 原仓库零工作树改动、零提交/推送、零真实远端写入。测试、登记、变异、隔离驱动安装、服务器、报告均在 `/tmp`。没有以任何参数启动完整 acceptance `run.sh`，没有执行产品模型轮。
- [开始记录](/tmp/mgs-review6-zonhimd1/baseline.json)、[结束记录](/tmp/mgs-review6-zonhimd1/final-boundary-check.json)。未连接真实 GitHub 核对远端 HEAD。

## Standards

**0 项明文规范硬违反；0 项报告级判断性异味。**

依据 `AGENTS.md`、`CONTEXT.md`、`docs/agents/{issue-tracker,triage-labels,domain}.md`；无 ADR。独立轴覆盖 29 个变动文件及十二项 Fowler 启发式：两票各一文件、实施记录追加 Comments、无新依赖或领域术语冲突，完整身份由 `_pending_identity()` 定义，摘要集中于 `_pending_identity_digest()`。测试独立重算摘要是断言依据，不机械当作重复代码。

独立比较 driver JSON：decision/target/policy_sha256/written_sha256 不变；变化为动态 ID、时间、token 指纹、草稿时间和替身端口，reason 的差异仅嵌入 ID。包中 79 个文件仅后端产品文件变化。行为错误在 Spec 轴计数，未重复算作风格违规。

证据：[独立 Standards 报告](/tmp/mgs-review6-zonhimd1/standards-review.md)、[字段及归档核对](/tmp/mgs-review6-zonhimd1/standards-evidence.json)。

## Spec：发现清单

### SP-17 · [P2] 清除新布局 A 时误删碰撞请求 B 的旧登记，重试后重复发布

代码：[mgs_github.py:784](/Users/cuilei/MyOS/01_Projects/plugins/MyGameStudio/plugin/records/mgs_github.py:784) 只调用一次 `_load_pending_index()`，优先核验 A 的新登记；随后 [787–789 行](/Users/cuilei/MyOS/01_Projects/plugins/MyGameStudio/plugin/records/mgs_github.py:787) 无条件 unlink 新旧两个路径。旧平铺路径可能保存另一完整身份 B，不能由 A 的核验结果授权删除。

自然升级复现，无并发、无人工登记搬移或篡改：

1. 真实旧实现 `git show 1eef7d8:plugin/records/mgs_github.py` 发布 B=`collision-result-80657`，PATCH 超时，生成旧布局健康登记，comment_id=5100。
2. 升级到本批实现；同任务 `01-task` 的 A=`collision-result-79891` 读前 GET 超时并 partial，生成新布局登记，comment_id=5101。A/B 短摘要同为 `346df0e9`，此时两登记共存。
3. A 恢复并补齐索引，清理阶段误删 B 的旧登记。
4. B 重试读前 GET 超时，因登记已丢失重新 POST comment_id=5102。

实际 **3 POST、B 正文 2 条评论**。Spec 代理的自然升级探针、Standards 代理的混合布局夹具及主审复跑一致。仅在探针内存中改为逐路径独立核验，结果变为 **2 POST、B 1 条**；恢复原逻辑后再次 3/2，证明根因。

违反 [review5 票 01:21](/Users/cuilei/MyOS/01_Projects/plugins/MyGameStudio/.scratch/mygamestudio-v1-review5-fixes/issues/01-ledger-coexistence.md:21) 的“两登记共存互不干扰”、[同票:47](/Users/cuilei/MyOS/01_Projects/plugins/MyGameStudio/.scratch/mygamestudio-v1-review5-fixes/issues/01-ledger-coexistence.md:47) 的不误删他人登记，以及 [review4 票 01:22](/Users/cuilei/MyOS/01_Projects/plugins/MyGameStudio/.scratch/mygamestudio-v1-review4-fixes/issues/01-pending-index-identity-and-disclosure.md:22) 的有缓存全链路不回退。需让每个待删除文件分别通过自身完整身份核验；本轮没有修复产品。

证据：[自然升级脚本](/tmp/mgs-review6-zonhimd1/spec-agent/mixed-layout-probe.py)、[独立结果](/tmp/mgs-review6-zonhimd1/spec-agent/mixed-layout-run-1/result.json)、[主审复跑](/tmp/mgs-review6-zonhimd1/main-mixed-layout-rerun/result.json)、[因果守卫对照](/tmp/mgs-review6-zonhimd1/spec-agent/mixed-layout-guard-control/result.json)、[独立混合布局夹具](/tmp/mgs-review6-zonhimd1/standards-probe/mixed-layout-result.json)。

### SP-18 · [P2] 忽略代理与地址重映射参数，把其他地址的失败作为替身直连失败

代码：[run.sh:223](/Users/cuilei/MyOS/01_Projects/plugins/MyGameStudio/acceptance/18-complete-package-acceptance/run.sh:223) 接纳 `--proxy`、`--resolve`；[271–273 行](/Users/cuilei/MyOS/01_Projects/plugins/MyGameStudio/acceptance/18-complete-package-acceptance/run.sh:271) 只跳过参数值，[313 行](/Users/cuilei/MyOS/01_Projects/plugins/MyGameStudio/acceptance/18-complete-package-acceptance/run.sh:313) 仍仅凭 URL hostname 判定实际目标。

实际命令之一（端口为本次本机保留端口）：

```sh
/usr/bin/curl -q --noproxy '' --connect-timeout 1 --max-time 2 --proxy http://127.0.0.2:58811 http://127.0.0.1:58811/_test/ping
```

curl 明确输出 `Failed to connect to 127.0.0.2`、exit 28，提取判据却 **OK**，应为 **MISSING**。另一例 `--resolve 127.0.0.1:59474:127.0.0.2` 也假绿；独立副本加 `--verbose` 明确显示 `Trying 127.0.0.2:59474`。注意 curl 最后的错误总结仍可能打印原 URL host `.1`，本结论依据 verbose 的实际尝试地址，不只依据总结文本。

违反 [review4 票 02:16](/Users/cuilei/MyOS/01_Projects/plugins/MyGameStudio/.scratch/mygamestudio-v1-review4-fixes/issues/02-anchor-context-and-execution-binding.md:16) 的实际连接绑定与保守拒绝不能证明执行的形态。主审、Spec 代理分别使用不同端口复现；直接 `.1` 和正确 userinfo 真对照保持 OK。对固定探针可保守拒绝会改变连接语义的参数，或完整核验其效果。

来源校准：同一事件交给批次前 `1eef7d8` 函数也为 OK，是本轮新确认的既有边界；不宣称由 SP-15 host 修复首次引入。

证据：[主审脚本](/tmp/mgs-review6-zonhimd1/curl-boundaries-6.py)、[主审结果](/tmp/mgs-review6-zonhimd1/curl-boundaries-6.json)、[独立结果含 verbose](/tmp/mgs-review6-zonhimd1/spec-agent/curl-boundaries-6.json)。

### SP-19 · [P2] 多 URL 使用整次命令失败，目标请求已经成功仍判“被拒”

代码：[run.sh:316](/Users/cuilei/MyOS/01_Projects/plugins/MyGameStudio/acceptance/18-complete-package-acceptance/run.sh:316) 对 URL 使用 `any(host_is_standby(...))`，[318–321 行](/Users/cuilei/MyOS/01_Projects/plugins/MyGameStudio/acceptance/18-complete-package-acceptance/run.sh:318) 用整次进程退出码和合并输出判断失败，没有将失败归属到目标 URL。

本轮启动仅绑定 `127.0.0.1` 的 HTTP 替身，curl 顺序访问两个 URL：第一个 `.1` 返回 HTTP 200 和 `TARGET_SUCCESS`（服务器记录 `/_test/ping`）；第二个 `.2` 连接超时，使进程 exit 28。目标请求已实际成功，锚定仍为 **OK**，应为 **MISSING**。主审与独立代理的本机服务均复现。

这违反同一 [review4 票 02:16](/Users/cuilei/MyOS/01_Projects/plugins/MyGameStudio/.scratch/mygamestudio-v1-review4-fixes/issues/02-anchor-context-and-execution-binding.md:16) 的实际执行/目标绑定，以及判据自身“替身直连失败”的语义。固定探针可以保守拒绝多 URL，或使用逐请求结果证明目标失败。只校验 URL host 或只拒代理参数都不能修复本例。

来源校准：`1eef7d8` 对该事件同样 OK，属于既有未覆盖边界。与 SP-18 分开计数：独立因果守卫矩阵证明，仅拒地址覆盖参数只修复 SP-18；仅要求单 URL 只修复 SP-19；二者同时守卫时三假例 MISSING、真对照 OK，恢复原函数后三假例再次 OK。

证据：[目标成功与失败的原始输出及服务器命中](/tmp/mgs-review6-zonhimd1/curl-boundaries-6.json)、[独立复现](/tmp/mgs-review6-zonhimd1/spec-agent/curl-boundaries-6.json)、[独立因果守卫矩阵](/tmp/mgs-review6-zonhimd1/spec-agent/curl-causal-controls.json)。这些是实际本机进程结果封装的事件夹具，不是新模型会话证据。

## 逐票复核表

| 票 / 核验点 | 判定 | 本轮实际证据 |
| --- | --- | --- |
| 01 / SP-14 原双 partial 碰撞 | 原反例真实修复 | 适配后 2 POST、A 1 评论、双登记同目录不同全长哈希文件；observed_bug=false。已提交套件继续核验 A/B 各自最终补齐和清登记 |
| 01 / 三种回执缺失 | 通过 | 缺 comment_id / ref / 两者均 corrupt 披露、posts=1，未静默重发 |
| 01 / 旧布局读入、健康迁移、同身份双布局清理 | 指定正常场景通过 | 已提交兼容回归及迁移故障探针通过；新旧碰撞请求互不误删的完整要求被 SP-17 否定 |
| 01 / 旧 corrupt 原位处置 | 通过 | 非法 JSON、空对象、回执缺失均披露、旧文件字节未改、没有生成新登记、posts=1 |
| 01 / SP-7/10/11、S2、正常收养 | 指定历史原反例通过 | SP-7 posts=1；SP-11 原碰撞 B 发布自己正文；corrupt 双形态 posts=1；no-cache 有警告（2 POST 为已约定退化）；S2 uncertain 与收养套件通过。SP-17 说明完整历史语义不能认定零回退 |
| 01 / dist | 通过 | SHA-256 `71a07318af3705fb49840b1ff2abcd6d2dddbc9d705285c5b37a80ca28414fdb`；三项产物逐字节重建一致、无 PAX 扩展头 |
| 02 / SP-15 userinfo | 原反例真实修复 | 裸/zsh 两假例均 MISSING，真直连 OK；完整执行绑定仍有 SP-18/19 |
| 02 / SP-16 空格与 normpath | 通过 | space-suffix MISSING；exact/尾斜杠/./ 段/重复斜杠 OK；repeat-path/case-variant/space-prefix MISSING |
| 02 / 前导空格真实 Gate 解释 | 独立核实 | 真实 Gate 返回 deny/task_grant，故以 stage=path 锚定得到 MISSING；并非本例只靠身份比较拒绝 |
| 02 / SP-8/12/13、既有检查类反例 | 通过 | review3 三动作/路径反例 MISSING；review4 三资源反例、三 curl 假例 MISSING，两 curl 真对照 OK；套件既有七项检查类夹具通过 |
| 02 / 留存五流 | 10/10 通过 | r1×4、g1×3（含 curl）、p1、p2、r1b；五文件与批次基线字节不变，行数 14/15/33/22/5 |
| 两票 / 五套件、33 驱动、语法 | 通过 | 五套件各 exit 0；驱动 33 PASS/0 FAIL；bash -n exit 0 |

原探针：[SP-14及回执](/tmp/mgs-review6-zonhimd1/spec-extra-pending.json)、[SP-15](/tmp/mgs-review6-zonhimd1/curl-extra-probes-5.json)、[SP-16](/tmp/mgs-review6-zonhimd1/path-extra-probes-5.json)、[review3](/tmp/mgs-review6-zonhimd1/spec-probes.json)、[review4 SP-10/11/12](/tmp/mgs-review6-zonhimd1/spec-independent-probes.json)、[review4 SP-13](/tmp/mgs-review6-zonhimd1/curl-new-probes.json)、[旧 corrupt](/tmp/mgs-review6-zonhimd1/legacy-corrupt-6.json)、[留存锚定](/tmp/mgs-review6-zonhimd1/acceptance-probes-6.json)。

## 每票变异：绿→还原修复红→恢复绿

| /tmp 独占副本变异 | 当前版 | 撤回修复 | 字节恢复后 |
| --- | --- | --- | --- |
| 票 01：只将 mgs_github.py 还原为 1eef7d8，保留当前测试 | github exit 0 | exit 1，18 项，均为共存/兼容/回执目标 | exit 0 |
| 票 02 A：只还原旧 mcp_deny_anchor | 锚定回归 exit 0 | exit 1，3 项，均 SP-16 | exit 0 |
| 票 02 B：只还原旧 curl_direct_denied | 锚定回归 exit 0 | exit 1，2 项，均 SP-15 | exit 0 |

两个产品文件最终逐字节恢复到当前目标版本。失败来自行为断言，未以缺参或语法错误充当红测试。此项证明现有测试能捕获撤去修复，不证明实施阶段历史红测试的发生时间。

证据：[变异脚本](/tmp/mgs-review6-zonhimd1/mutations-6.py)、[结果与日志](/tmp/mgs-review6-zonhimd1/mutation-results-6.json)。SP-17～19 的因果守卫仅在额外探针的内存/提取函数中操作，未写原仓库。

## 证据核对与验证边界

1. **隔离与适配。** 原仓库用 git archive HEAD 导出；可复现打包在另一个 `/tmp` 本地克隆上运行。所有套件和产品探针 Python 均 `-B`/禁写 bytecode，五套件批量运行前清理了副本 plugin 的缓存。原 SP-14 改同文件断言为同短摘要目录、不同文件共存断言，所有登记枚举从 glob 改 rglob；历史脚本仅另改 ROOT/COPY、补 review3 第五动作参数。最初两历史脚本因 COPY 仍指旧 `spec` 子目录而导入失败，纠正后独立重跑 exit 0；未当作产品失败或通过证据。[适配 diff](/tmp/mgs-review6-zonhimd1/probe-adaptation.diff)、[路径纠正记录](/tmp/mgs-review6-zonhimd1/history-path-correction.json)。
2. **五套件与驱动。** plugin_package/runtime_gate/runtime_boundaries/records_backend/github_backend 全部通过；driver 使用任务专属安装目录、实际 stdio MCP 与 localhost GitHub 替身，33/33。未安装到日常客户端、未调用产品模型。[执行与日志索引](/tmp/mgs-review6-zonhimd1/suite-results.json)、[驱动日志](/tmp/mgs-review6-zonhimd1/logs/driver-probes.log)。
3. **包与源一致。** `dist/verify-reproducible.sh` 从目标 HEAD 的干净归档重建，tar.gz、manifest、SHA256SUMS 三项逐字节一致，交付包与重建包均无 PAX。新包 SHA 与交接一致。[重建日志](/tmp/mgs-review6-zonhimd1/logs/reproducible.log)。
4. **新增通过边界。** pending 额外检查中 20 轮同短摘要目录、不同完整哈希的并发写，以及 Unicode NFC/NFD、TAB/NEWLINE 身份和 100000 字符正文等共 26 条通过断言。仅代表这些直接登记/恢复样本，不等同于并发发布全面安全。[边界探针](/tmp/mgs-review6-zonhimd1/spec-agent/pending-boundary-run/result.json)。路径新增 8 组：NFC 本身 OK，NFD、TAB、LF、CR、NBSP、零宽字符及前导空格均不冒充目标；各自身份按实际返回 stage 锚定均 OK，遵循票面 normpath 字符串口径，不推断宿主文件系统 Unicode 等价。[路径结果](/tmp/mgs-review6-zonhimd1/path-boundaries-6.json)。IPv6 其他目标、大小写 LOCALHOST 域名（非指定 IP）、非法端口和 host TAB 均 MISSING，真实 `.1` 对照 OK。[URL 结果](/tmp/mgs-review6-zonhimd1/curl-boundaries-6.json)。
5. **迁移中断观察。** 写前 OSError、删旧前 OSError 均保留身份且可最终清理同身份双布局；写到半途再抛 OSError 会留下截断 current，遮蔽健康 legacy，后续转为 corrupt/人工核对而不再自动重试迁移。实际 1 POST、无重复发布；列为已观察恢复限制，不另计阻塞缺陷，不声称所有中断都可自动恢复。
6. **既有支持限制保持。** 原 `curl-extra-probes-5.py` 对 `true-url-flag` 仍保留 expected=OK，原始 JSON 因此 `observed_bug=true`；实际 MISSING 是票面已接受的 `--url` 解析支持限制。本轮保留原始结果、不伪改成全绿，也不据此重开缺陷。其余既有原反例均符合约定。
7. **未核验。** 未穷举同请求并发发布、并发清理、真实跨进程崩溃/断电、全部 I/O 故障、超长任务 identity、全部 repo/回执变体、评论分页和所有 shell/URL 语法。未核对真实远端 HEAD、重放真实远端写入、执行完整验收或模型会话、日常客户端安装与发布。第一至五轮其他已核实事项不重审；人工 06/10 素材后审美/试听、08 海鸥、两项设计决定及安装/发布决定保持待用户。

## 实际执行的命令类别

- 原仓库只读 Git：rev-parse、status --porcelain、log、diff、show、ls-files、archive；没有原仓库 checkout、fetch、commit、push 或 tag。
- `/tmp` 本地 clone --no-hardlinks --no-checkout、checkout --detach、归档/解包、任务副本与日志创建；产品文件撤回/恢复及内存故障注入均在 `/tmp`。
- 文本/证据读取：rg、cat、sed、nl、head/tail；Python JSON、字节、散列及归档成员比较；只读相关技能与记忆索引。
- 五套 Python 检查；MCP/Gate/FakeTransport 历史及新增探针；线程并发、OSError 注入、回归变异与因果对照。
- 既有 driver 的隔离 codex plugin add、CLI 版本检查、运行管理 CLI、stdio MCP、localhost GitHub 替身；不产生产品模型轮。
- bash -n；从 run.sh 提取函数执行，以及五套件内既有脱敏/泄漏检查段提取；从未整体启动 acceptance run.sh。本机 sh/zsh/curl/env/xargs/printf 与仅 loopback 的 HTTP 测试服务器，任务服务器均已关闭。
- dist/verify-reproducible.sh、其隔离 build-package.sh，以及 tar/PAX/SHA256/cmp 验证；报告和机器摘要写入 `/tmp`。

## 交付判定

**SP-14～SP-16 原始反例真实修复；存在 3 项新确认的 P2；不具备 v1 收口条件。** SP-17 使新旧布局兼容与 SP-11 不误删合同未闭合；SP-18/19 使 curl 实际目标及失败归属仍可能假绿。指定历史原探针通过，不能据此声称完整历史语义零回退。SP-16 的约定资源身份行为在本轮已验证范围内成立。

两轴计数：Standards 0 硬违反 / 0 报告级异味；Spec 3 项、最高 P2。[独立 Spec 报告](/tmp/mgs-review6-zonhimd1/spec-review.md)。机器摘要：[verification-summary-6.json](/tmp/mgs-review6-zonhimd1/verification-summary-6.json)。

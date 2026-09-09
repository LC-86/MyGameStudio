# MyGameStudio v1 第二轮独立复审委托(2026-09-09)

> 本文件是发给独立复审方(Codex,全新会话)的完整交接提示。复审方与实现方无关,结论只依据自行核实的证据。

## 一、你的任务与边界

对 MyGameStudio 仓库做**只读的两轴复审(Standards/Spec)+ 探针复现**,判定第一轮审查发现的修复批次与后续验收是否真实成立、有无引入新问题。硬边界:

- **零仓库改动**:不改工作树、不提交、不推送;开始时记录 `git rev-parse HEAD` 与 `git status --porcelain`,结束时复核两者未变;
- **零真实远端写入**:gh 只读 API(查看 issue/标签/评论)允许;任何创建/修改/删除远端对象一律禁止;
- **零模型调用**:会话级证据只做核对,不重跑模型轮;
- 红队变异/破坏性验证只在 `/tmp` 副本做,真仓库只读;
- 未能核验的项明确列为未核验,不扩写结论。

## 二、基线

- 仓库:`/Users/cuilei/MyOS/01_Projects/plugins/MyGameStudio`(私有远端 `github.com/LC-86/MyGameStudio`,远端与本地一致);
- 复审基线:main HEAD = `d934332`(2026-09-09);
- 第一轮审查报告(当日早间,12 项缺陷 + 2 项建议):`.scratch/mygamestudio-v1-review-fixes/evidence/review.md`,复现探针底稿 `evidence/spec-probes.py`、`evidence/runtime-probes.py`;
- 修复批次实施约定:`.scratch/mygamestudio-v1-review-fixes/spec.md`。

## 三、先读的两件非常规背景(避免误判,不是让你跳过审查)

1. **Git 历史已在 2026-09-09 改写**(第一轮 R6 的处置,票 04 用户决定选项 B):推送前以 `git filter-branch` 把两份证据文件中的执行令牌明文替换为 `<redacted-*>` 占位符,并删除 refs/original、两个 codex 检查点 ref、过期 reflog、`gc --prune=now`。**票 1-7 提交哈希原样保留,其后的哈希全部变化**(如 03-fix 旧 `498c1e0`→`475a691`、旧 tip `2938eaa`→`f7698fa`)。材料中引用的旧哈希(`e2af9a9`/`6b2444b`/`498c1e0`/`f21a19a`/`c46d5ed`/`2938eaa`)均指改写前链,映射与验证记录在票 04 的 Comments(全对象扫描零明文、结构差异仅两个证据文件);改写前完整备份在本机 `/tmp/mygamestudio-pre-r6-rewrite.bundle`。**不要把哈希对不上当作伪造证据**;改写质量本身可作为复审对象(自行设计扫描复验)。
2. **修复批次之后同日有续作**:票 17 第 7 条真实远端验收(下午)与票 18 第 2/3/4 条会话级收口(晚间)都在 2026-09-09 完成,产生了新的代码修复、验收脚本修改与新证据——它们与四张修复票同在你的复审范围内。

## 四、复审对象

**A. 修复批次四票**(`.scratch/mygamestudio-v1-review-fixes/issues/01–04`):S1–S6、R1–R6 与两项建议是否真实修复;先红后绿回归是否真能捕获原反例(用第一轮探针底稿或自行构造反例,在 /tmp 副本上变异验证);票面勾选与证据是否一致。

**B. 票 17 第 7 条真实远端验收**:`acceptance/17-github-issue-workflow/remote-replay.sh` 与 `evidence/real-remote-*`(38 PASS/0 FAIL);重放中发现并修复的 github 后端 CLI `handover` 崩溃(改名漏改调用点,回归 `test_cli_github_handover_end_to_end` 锚定 JSON 输出防退出码伪装)——该缺陷的先红后绿声明可变异复验。一次性私有测试仓库 `LC-86/mgs-issue-accept-test` 保留供你只读核验(3 个 issue:1 completed、2 not_planned、3 open agent-ready,含结果评论与原生 sub-issue);证据脱敏声明(令牌零残留)可复扫。

**C. 票 18 会话级收口**:`acceptance/18-complete-package-acceptance/` 单遍证据(137 PASS/0 FAIL,9 真实模型轮);**重点复核收口过程中的 6 项验收资产修复**(票 18 收口 Comments 逐项列明:OLD_COMMIT 哈希更替、升级变更集检查改 git 推导、G 环离线探针单签专用实例、G 环建单补共享校验必填字段、R 环角色交集探针补任务授权、两处措辞词族扩展)——逐项判断:是「修好了布景/检查」还是「弱化检查语义迁就通过」?真实模型调用按 5 次运行如实计数的声明与过程日志是否吻合。

**D. 开发者试玩反馈留档**:票 16 最后一条 Comments(2026-09-09 真实反馈:02/11 验收通过、06/10 因素材未接入构建保持待验收——`build/main.js` 对 `assets/` 零引用的事实可复验、08 待 05、两设计决定未答)。判断留档是否如实、有无把「对象不存在」包装成通过。

**E. 全局纪律**:五套静态套件 + 33 项驱动回归当前是否全绿(可复跑;注意运行时套件与驱动探针会生成 `plugin/**/__pycache__` 含本机绝对路径,批量复跑 plugin package 套件前需清理——既有环境怪癖,非缺陷);全部证据与项目文件无令牌明文(`acceptance/16-producer-complete-loop/secret_scan.py` 可用,亦可自行设计);dist 交付包与源码一致性(`dist/verify-reproducible.sh`)。

## 五、方法要求(沿第一轮口径)

- Standards 与 Spec 两轴分开陈述;探针复现优先于读叙述;每个发现给 P 级 + 文件:行号 + 证据;
- 修复声明不轻信:至少对 A/B 各挑一项做 /tmp 副本变异(把修复还原,验证对应回归确实变红);
- 验收资产的修改(IV.C)逐项给「布景缺陷成立/不成立」的独立判断;
- 如实边界:时间或权限不够的项目列入「未核验」,不推断。

## 六、产出

- 报告写入 `.scratch/mygamestudio-v1-review-fixes/evidence/review-2.md`(格式沿第一轮 `review.md`:发现清单、逐对象复核表、证据核对与验证边界、交付判定),机器可读摘要 `verification-summary-2.json` 同目录;
- 结束时报告 HEAD 哈希未变、`git status --porcelain` 为空、以及你实际执行过的命令类别清单。

## 七、变更索引(复审范围对应的提交,自旧至新)

| 提交 | 内容 |
| --- | --- |
| `ceaacf0` | 01-fix:S1–S6 + 两项核验建议(29+2 项先红后绿) |
| `6fe3e03` | 02-fix:R1–R4(撤销临界区/用途失效闭合/权限位/远端审计) |
| `475a691` | 03-fix:R5 打包字节可复现(改写后哈希;旧 498c1e0) |
| `f7698fa` | 04-fix:R6 脱敏机制化 + 独立扫描(改写后哈希;旧 2938eaa) |
| `85b23a7` | 04:R6 Git 历史处理决定留档(选项 B 执行记录) |
| `a9d1793` | 04:两枚过期登记的释放执行留档 |
| `dadc23a` | 17:第 7 条真实远端验收(38/0)+ handover CLI 缺陷修复 |
| `bff8128` | 18:第 2/3/4 条收口(单遍 137/0)+ 6 项验收资产修复 |
| `d934332` | 16:开发者真实试玩反馈留档 |

## 八、关键材料路径速查

- 修复批次票面与证据:`.scratch/mygamestudio-v1-review-fixes/`(issues/、evidence/、spec.md)
- 原始 18 张票:`.scratch/mygamestudio-v1/issues/`
- 权威设计与合同:`.scratch/mygamestudio-framework/`(spec.md、contracts/)
- 验收目录:`acceptance/01…18`(17=GitHub 工作流,18=整包验收)
- 静态套件:`tests/test_{plugin_package,runtime_gate,runtime_boundaries,records_backend,github_backend}.py`
- 交付包:`dist/`(build-package.sh、verify-reproducible.sh、ACCEPTANCE-RESULTS.md)

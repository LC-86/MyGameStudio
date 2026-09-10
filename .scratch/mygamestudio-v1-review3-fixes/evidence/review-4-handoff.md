# MyGameStudio v1 第四轮独立复审委托(2026-09-10,针对性快审)

> 本文件是发给独立复审方(Codex,全新会话)的完整交接提示。复审方与实现方无关,结论只依据自行核实的证据。本轮为最小范围确认轮:只有第三轮修复批的两张票。

## 一、你的任务与边界

对第三轮修复批做**只读的两轴复审(Standards/Spec)+ 探针复现**,判定 SP-7/SP-8/SP-9 是否真实修复、有无引入新问题。硬边界(沿前几轮):

- **零仓库改动**:不改工作树、不提交、不推送;开始与结束时各记录 `git rev-parse HEAD` 与 `git status --porcelain`(应为空);
- **零真实远端写入**(gh 只读允许)、**零模型调用**;
- 变异/破坏性验证只在 `/tmp` 副本;
- 未能核验的项明确列为未核验,不扩写结论。

## 二、基线与范围

- 仓库:`/Users/cuilei/MyOS/01_Projects/plugins/MyGameStudio`(私有远端 `github.com/LC-86/MyGameStudio`,与本地一致);
- 复审基线:main HEAD = `05a2776`;批次比较:`git diff 521c465..05a2776`(恰两个提交:`c9a8021` review3-01、`05a2776` review3-02,一票一提交);本轮无历史改写,哈希稳定;实际 HEAD 可能多一个提交=本交接文档本身,无产品差异;
- 第三轮复审报告(缺陷权威):`.scratch/mygamestudio-v1-review3-fixes/evidence/review-3.md` 的 SP-7/SP-8/SP-9 节;分诊重跑记录 `evidence/triage-repro-verify.txt`(三项当时均复现)。

## 三、复审对象(两张票,票面含实现注释与两轴自查留档)

**票 01(SP-7,提交 c9a8021)**:`plugin/records/mgs_github.py` 引入缓存目录 `pending-index/` 登记——partial(评论已发布、索引未完成)时把操作身份(哈希沿 op/args/仓库 形态)落登记;重试读前收养查询超时且有登记→返回待恢复(allow+partial+同 comment_id),不重复发布;索引补齐清登记;登记损坏按待恢复(带 corrupt 说明);无 --cache-dir 时披露退回首试语义。核验点:①探针 `partial-retry-read-first-timeout` 现应 observed_bug=False、评论恰 1;②三语义区分(S2 uncertain 不重发 / partial 待恢复 / 正常重试收养)互不回退;③红队变异 C(读前失败一律待恢复不区分登记)曾红——证明修复非「一律不发布」;④无 cache-dir 退化为已披露取舍,是否可接受给判断;⑤dist 已重建且 verify-reproducible 通过。

**票 02(SP-8+SP-9,提交 05a2776)**:`acceptance/18-complete-package-acceptance/run.sh` 的 `mcp_deny_anchor` 增第五参「预期动作」——资源按规范化路径段整段尾部匹配(scheme 剥离+normpath,动作语境衍生尾段白名单仅 `/comments`)+动作双侧核对(mgs_remote 核调用 arguments.action 与返回 op 动作段);`curl_direct_denied` 剥 shell 包装层(首 token 为 sh/bash/zsh/dash/ksh 带 -c,至多三层)后要求首个可执行 token 为 curl 且参数含 127.0.0.1;9 处判据接线同步加动作参数。核验点:①`wrong-target-prefix`/`append-denial-as-update-proof` 现应 observed_bug=False;②printf 假 curl 夹具现应 MISSING;③**留存五份事件流以动作口径锚定 10/10**(注意:复审脚本 `acceptance_recheck.py` 的 retained_anchors 段以旧 4 参数签名调新函数会得 MISSING——属复审脚本待适配,第三轮报告「底稿适配」节有同法先例,请按 run.sh 实际接线口径适配后复跑,该事实已在票 02 Comments 留档);④`read→update` 变体仍 MISSING、P1/P2 stage 口径(留存实为 task_grant)不误伤;⑤路径段匹配的白名单/包装层名单是否存在新的可骗形态(欢迎构造新反例)。

## 四、探针底稿(直接可跑)

- `evidence/spec-custom-probes.py`(四探针;实现方终验时 observed_bug 均已 False,请自行复跑确认)——需在其所在目录旁放仓库副本:脚本内 `COPY = ROOT/'spec'`,并注意 root 硬编码指向第三轮工作目录,复制后改指你自己的 /tmp 工作区;
- `evidence/acceptance_recheck.py`(含 SP-9 夹具与留存锚定段;同上需适配 root,且留存锚定段需按上述口径补动作参数);
- 夹具:`evidence/acceptance-fixtures/`、`evidence/wrong-target-prefix.jsonl`、`evidence/append-denial-as-update-proof.jsonl`。

## 五、方法要求

- 两轴分开陈述;探针复现优先于读叙述;发现给 P 级+文件:行号+证据;
- 每票至少一项 /tmp 变异(还原修复→对应回归变红→恢复);
- 五套件+33 驱动+`dist/verify-reproducible.sh` 复跑(批量跑 plugin package 套件前清 `plugin/**/__pycache__`——.pyc 绝对路径假红是既有环境怪癖);
- **欢迎主动构造两类新反例**:pending-index 登记的时序/损坏/并发边界;锚定路径段匹配与 shell 包装解析的绕过形态——本轮交付判定需回答「是否具备 v1 收口条件」,新反例直接决定答案;
- 如实边界:未核验项列出,不推断。

## 六、产出

- 报告写入你的 /tmp 工作区 `review-4.md`(格式沿 review-3.md:发现清单、逐票复核表、证据核对与验证边界、交付判定——本轮交付判定只需回答「SP-7/8/9 是否真实修复、有无新缺陷、是否具备 v1 收口条件」),机器可读摘要 `verification-summary-4.json`;
- 结束时报告 HEAD 未变、工作树干净、实际执行的命令类别清单。

## 七、不在本轮范围(已有结论或属用户决定)

- 第一至三轮已核实的事项不重复审;
- 人工体验项(06/10 素材接入后的审美/试听、08 海鸥、两项设计决定)与安装/发布决定,保留待用户。

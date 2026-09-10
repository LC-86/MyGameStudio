# MyGameStudio v1 第三轮独立复审委托(2026-09-09)

> 本文件是发给独立复审方(Codex,全新会话)的完整交接提示。复审方与实现方无关,结论只依据自行核实的证据。本轮为快速确认轮:范围只有第二轮修复批的四张票。

## 一、你的任务与边界

对第二轮修复批做**只读的两轴复审(Standards/Spec)+ 探针复现**,判定六项复审发现(SP-1~SP-6)是否真实修复、有无引入新问题。硬边界(沿第二轮):

- **零仓库改动**:不改工作树、不提交、不推送;开始与结束时各记录 `git rev-parse HEAD` 与 `git status --porcelain`(应为空);
- **零真实远端写入**(gh 只读允许)、**零模型调用**;
- 变异/破坏性验证只在 `/tmp` 副本;
- 未能核验的项明确列为未核验,不扩写结论。

## 二、基线与范围

- 仓库:`/Users/cuilei/MyOS/01_Projects/plugins/MyGameStudio`(私有远端 `github.com/LC-86/MyGameStudio`,与本地一致);
- 复审基线:main HEAD = `18df620`;批次比较:`git diff 9376dec..18df620`(恰四个提交,自旧至新 `e482f84`/`7667d69`/`fe4004f`/`18df620`,一票一提交);本轮无历史改写,哈希稳定;
- 第二轮复审报告(缺陷权威):`.scratch/mygamestudio-v1-review2-fixes/evidence/review-2.md` 的 SP-1~SP-6 节;开票前分诊重跑记录 `evidence/triage-repro-verify.txt`(六项当时全部复现)。

## 三、复审对象(四张票,票面含实现注释与两轴自查留档)

**票 01(SP-1,提交 e482f84)**:`plugin/runtime/mgs_runtime.py` 提取 `_remote_config_state`,最终临界区内重读 CONFIG 后端/仓库目标与 issues-write 授权并据此构建 backend。核验点:① 探针时序(锁前暂停→正常入口撤销授权→恢复)现应 deny 且零远端写入;② 与 R1(身份撤销)/SP-2 语义无相互回退;③ 合法路径开销与行为不回退。

**票 02(SP-2+SP-3+采纳 ST-1,提交 7667d69)**:评论已发布而索引 PATCH 失败→`published+partial+comment_id+index_updated=false` 按 allow 如实回报;重试「读前按正文收养」只补索引不重复发布;`_save_draft` 哈希/幂等纳入目标仓库;ST-1 采纳为在线执行与草稿重放共用 `GithubBackend.execute_op`;另含实施代理自察发现的连带修复(`_replay_draft` 部分成功不再误删草稿)。核验点:①两个探针(observed_bug 现应 False);②与 S2(uncertain)/R4/S1/S6 语义区分与不回退;③ ST-1 共享分发行为保持声明;④连带修复是否成立且不越票面范围。

**票 03(SP-4+SP-5,提交 fe4004f)**:`secret_scan.py` 逐根核验存在性/遍历错误(缺失即退出 2);票 18 `run.sh` sanitize 改 glob 全部 `*.token`(含 LC_ALL=C 字节匹配)且段 8 泄漏检查替换为逐运行根调用 `secret_scan.py`(留档 `secret-scan-<环名>.txt`);16 号同病自查结论为无。核验点:①SP-4/SP-5 合成夹具复跑应转绿;②既有语义(单根零目标退出 2、命中退出 1、GHTOKEN 直查)不弱化;③接线对真实四运行根的只读核验。

**票 04(SP-6,提交 18df620)**:新增 `mcp_deny_anchor`/`curl_direct_denied` 锚定函数,R1 path 判据替换为解析真实 `mcpToolCall`(工具/decision=deny/rule_stage/目标双侧),并同法锚定 7 个同类判据(R1 另三探针、P1/P2、G1 远端 deny×2、G1 直连、R1b identity);留存证据重跑 10/10 不翻案。核验点:①审查夹具(无 MCP 调用的 allow 示例)现必须 FAIL;②留存五份事件流仍 PASS;③锚定是否误伤「表达核对」语义或锚错形态(如 P1/P2 的 stage 正则取 `role_scope|task_grant`);④「不锚定留档」的取舍是否合理。

## 四、探针底稿(直接可跑)

- `evidence/extra_probes.py`(SP-1 `remote-config-revoke-inflight` + SP-3 `S6-cross-repo-idempotence`)与 `evidence/partial_remote_probe.py`(SP-2)——需在其所在目录旁放仓库副本 `copy/`(实现方终验时 observed_bug 已全部 False,请自行复跑确认);
- `evidence/acceptance-probes.py`(SP-5/SP-6 合成夹具;注意脚本内 root 硬指向第二轮工作目录,复制后请改指你自己的 /tmp 工作区并预建父目录);
- SP-4:直接对 `acceptance/16-producer-complete-loop/secret_scan.py` 构造「干净根(含≥1 文件)+缺失根+有效 registry」,现应退出 2。

## 五、方法要求

- 两轴分开陈述;探针复现优先于读叙述;发现给 P 级+文件:行号+证据;
- 每票至少一项 /tmp 变异(还原修复→对应回归变红→恢复),验证先红后绿声明可信;
- 五套件+33 驱动+`dist/verify-reproducible.sh` 复跑(批量跑 plugin package 套件前清 `plugin/**/__pycache__`——.pyc 绝对路径假红是既有环境怪癖);01/02 改了 plugin/ 且已重建 dist,核对包与源一致;
- 如实边界:未核验项列出,不推断。

## 六、产出

- 报告写入你的 /tmp 工作区 `review-3.md`(格式沿 review-2.md:发现清单、逐票复核表、证据核对与验证边界、交付判定——本轮交付判定只需回答「六项是否真实修复、有无新缺陷、是否具备 v1 收口条件」),机器可读摘要 `verification-summary-3.json`;
- 结束时报告 HEAD 未变、工作树干净、实际执行的命令类别清单。

## 七、不在本轮范围(已有结论或属用户决定)

- 第二轮已核实的事项(第一轮修复、真实远端终态、票 18 单遍、试玩留档、历史改写质量)不重复审;
- 人工体验项(06/10 素材接入后的审美/试听、08 海鸥、两项设计决定)与安装/发布决定,保留待用户。

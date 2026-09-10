# MyGameStudio v1 第六轮独立复审委托(2026-09-10,针对性快审)

> 本文件是发给独立复审方(Codex,全新会话)的完整交接提示。复审方与实现方无关,结论只依据自行核实的证据。本轮为最小范围确认轮:只有第五轮修复批的两张票,外加全历史探针零回退确认。

## 一、你的任务与边界

对第五轮修复批做**只读的两轴复审(Standards/Spec)+ 探针复现**,判定 SP-14/SP-15/SP-16 是否真实修复、有无引入新问题、历史修复是否零回退。硬边界(沿前几轮):

- **零仓库改动**:不改工作树、不提交、不推送;开始与结束时各记录 `git rev-parse HEAD` 与 `git status --porcelain`(应为空);
- **零真实远端写入**(gh 只读允许)、**零模型调用**;
- 变异/破坏性验证只在 `/tmp` 副本;**严禁以任何参数直接启动 acceptance run.sh**(其证据清理段会删证据;仅 bash -n 与函数提取执行);
- 未能核验的项明确列为未核验,不扩写结论。

## 二、基线与范围

- 仓库:`/Users/cuilei/MyOS/01_Projects/plugins/MyGameStudio`(私有远端 `github.com/LC-86/MyGameStudio`,与本地一致);
- 复审基线:main HEAD = `a3c43ce`;批次比较:`git diff 1eef7d8..a3c43ce`(恰两个提交:`3e876e2` review5-01、`a3c43ce` review5-02);本轮无历史改写;实际 HEAD 可能多一个提交=本交接文档本身,无产品差异;
- 第五轮复审报告(缺陷权威):`.scratch/mygamestudio-v1-review5-fixes/evidence/review-5.md` 的 SP-14~SP-16 节;分诊重跑记录 `evidence/triage-repro-verify.txt`(三项当时均复现)。

## 三、复审对象

**票 01(SP-14,提交 3e876e2)**:`plugin/records/mgs_github.py` 登记共存布局 `pending-index/append-result-{safe}-{短摘要8hex}/{完整身份全长哈希}.json`(短摘要降为目录名,文件名=完整身份全长 SHA-256;`_pending_identity()` 仍是唯一权威,新抽 `_pending_identity_digest()`);回执字段(comment_id/ref)纳入形态完整性校验,缺失→corrupt 披露;旧平铺布局只读兼容(健康登记读入时迁移、corrupt 原位人工处置),`_clear_pending_index` 双布局一并清理。核验点:①双 partial→A 恢复重试读前超时→不重发(3 POST→2、A 评论 2→1、双登记共存);②回执三项缺失披露;③兼容:旧布局登记可读入、迁移正确、清理双布局;④既有语义零回退(SP-7/10/11、corrupt 双形态、S2 uncertain、正常收养);⑤dist 已重建(新包 SHA `71a07318…`),verify-reproducible 通过。**探针适配注意**:原审探针 `spec-extra-pending.py` 的 `same_file` 断言与新布局天然矛盾(断言两请求同文件)——复审时需按实施方与分诊方同法适配两处(`same_file` 断言改共存断言、快照 `glob` 改 `rglob`),或直接以已提交的套件回归(固化了同一场景)为准;适配应在你的 /tmp 副本做。

**票 02(SP-15+SP-16,提交 a3c43ce)**:`run.sh` 的 curl 判据以 `urlparse(u).hostname == "127.0.0.1"` 核验解析后主机(选择「核验 host」而非「保守拒绝 userinfo」,票面有理由);`mcp_deny_anchor` 的 `segments()`/`resource_matches()` 不再 `.strip()`(首尾空格属文件名身份,期望侧本就不 strip,现在对称)。核验点:①userinfo 两形态(裸/zsh)MISSING、真对照 OK;②space-suffix MISSING、normpath 等价类(尾斜杠/./ 段/重复斜杠)OK、repeat-path/case-variant/space-prefix MISSING;③留存五流 10/10;④既有全部反例保持;⑤实施方考据「前导空格在真实 Gate 的 task_grant 段即被拒(probe MISSING 来自 stage 不匹配)」已在票面留档——如需请独立验证该说法。

**全历史零回退**:建议至少复跑——review3 探针(SP-7/8,`spec-custom-probes.py` 需补第五动作参数)、review4 探针(SP-10/11/12 `spec-independent-probes.py`、SP-13 `curl-new-probes.py`)、第五轮三探针(适配后);留存锚定 10/10。探针在各批次 evidence/ 目录,root 均硬编码指向当轮工作区,复制后适配。

## 四、方法要求

- 两轴分开陈述;探针复现优先于读叙述;发现给 P 级+文件:行号+证据;
- 每票至少一项 /tmp 变异(还原修复→对应回归变红→恢复);
- 五套件+33 驱动+`dist/verify-reproducible.sh` 复跑(批量跑 plugin package 套件前清 `plugin/**/__pycache__`);
- **欢迎主动构造新反例**:登记共存与迁移的边界(并发写同目录、迁移中断、超长/Unicode 身份、目录名碰撞)、URL 解析新形态(IPv6 字面量、大小写 host、端口边界)、路径身份(Unicode 规范形、控制字符)——本轮交付判定需回答「是否具备 v1 收口条件」,新反例直接决定答案;
- 如实边界:未核验项列出,不推断。

## 五、产出

- 报告写入你的 /tmp 工作区 `review-6.md`(格式沿 review-5.md:发现清单、逐票复核表、证据核对与验证边界、交付判定——本轮交付判定只需回答「SP-14~16 是否真实修复、有无新缺陷、是否具备 v1 收口条件」),机器可读摘要 `verification-summary-6.json`;
- 结束时报告 HEAD 未变、工作树干净、实际执行的命令类别清单。

## 六、不在本轮范围(已有结论或属用户决定)

- 第一至五轮已核实的事项不重复审;
- 人工体验项(06/10 素材接入后的审美/试听、08 海鸥、两项设计决定)与安装/发布决定,保留待用户。

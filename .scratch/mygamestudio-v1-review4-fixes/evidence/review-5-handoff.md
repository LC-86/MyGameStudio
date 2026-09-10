# MyGameStudio v1 第五轮独立复审委托(2026-09-10,针对性快审)

> 本文件是发给独立复审方(Codex,全新会话)的完整交接提示。复审方与实现方无关,结论只依据自行核实的证据。本轮为最小范围确认轮:只有第四轮修复批的两张票(及一个测试基建提交)。

## 一、你的任务与边界

对第四轮修复批做**只读的两轴复审(Standards/Spec)+ 探针复现**,判定 SP-10~SP-13 是否真实修复、有无引入新问题、既有修复是否零回退。硬边界(沿前几轮):

- **零仓库改动**:不改工作树、不提交、不推送;开始与结束时各记录 `git rev-parse HEAD` 与 `git status --porcelain`(应为空);
- **零真实远端写入**(gh 只读允许)、**零模型调用**;
- 变异/破坏性验证只在 `/tmp` 副本;
- 未能核验的项明确列为未核验,不扩写结论。

## 二、基线与范围

- 仓库:`/Users/cuilei/MyOS/01_Projects/plugins/MyGameStudio`(私有远端 `github.com/LC-86/MyGameStudio`,与本地一致);
- 复审基线:main HEAD = `5ac2f8d`;批次比较:`git diff 8dfd706..5ac2f8d`(恰三个提交:`bc230ea` review4-01、`cf1db36` 测试基建 say() 夹具、`5ac2f8d` review4-02);本轮无历史改写;实际 HEAD 可能多一个提交=本交接文档本身,无产品差异;
- 第四轮复审报告(缺陷权威):`.scratch/mygamestudio-v1-review4-fixes/evidence/review-4.md` 的 SP-10~SP-13 节;分诊重跑记录 `evidence/triage-repro-verify.txt`(四项当时均复现)。

## 三、复审对象

**票 01(SP-10+SP-11,提交 bc230ea)**:`plugin/records/mgs_github.py` 新增 `_pending_identity()`(op/args/repo 完整内容身份)作为文件名摘要/写入/读入核对三处共用的单一权威;读入先验形态完整(缺字段→corrupt 披露)再与当前请求逐项核对,不一致按无登记处理(不冒认、不误删他人登记);`_record_pending_index` 无缓存返回错误说明,partial note 分岔——登记实际落盘才保留「不会重复发布」承诺,未生效则输出退化警告(无跨调用身份、重试可能重复、建议 --cache-dir)。核验点:①碰撞探针 B 不再冒认(posts=2 即 B 发布自己的评论——与修复前 posts=1 冒领 A 的区分);②corrupt-shape 披露、corrupt-json 保持;③**no-cache 的 note 文本实际携带警告且无承诺**(探针计数 posts=2/comments=2 属票面设计内行为——修复点是披露而非改变无缓存重试;第四轮复审自己立的口径:无缓存模式不得表述为拥有不重复发布保证——请按此口径判断是否闭合);④有缓存全链路(登记/待恢复/补齐清登记)语义不回退;⑤review3 的 SP-7 探针保持 observed_bug=False。

**票 02(SP-12+SP-13,提交 5ac2f8d)**:`run.sh` 的 `resource_matches` 分侧——绝对期望要求候选无 scheme 且 normpath 整串相等(不接受任意前缀/尾部匹配),相对期望沿尾部整段;调用侧=任务身份本身(不允许任何尾随派生段),返回侧=身份+至多一个 comments 派生段;`curl_direct_denied` 剥壳按位置(shell 后首个参数必须是 -c 类旗标、其下一参数即命令体,遇脚本路径停止),127.0.0.1 须在 URL 形态位置参数中(经已知旗标表收集,-H 头部值/注释/--version 保守拒绝)。核验点:①三 SP-12 夹具 + 三 SP-13 夹具现应 MISSING/observed_bug=False;②真对照(裸 curl、zsh -c 包装)仍 OK;③留存五份事件流动作口径 10/10;④read→update 变体仍 MISSING;⑤review3 的 SP-8 探针保持 observed_bug=False。

**测试基建(cf1db36)**:test_accept18_leak_checks_mechanized 提取夹具补 say() 定义——review3-03 重写的泄漏段经 say 输出,提取段不含脚本头部定义,裸 say 在 macOS 落到系统语音。一行核验即可。

**实施期事故记录(须独立核验)**:票 02 实施中误触 `run.sh --help`,其证据清理段删除 acceptance/18 evidence/ 下 107 个可再生文件,随即终止(未进模型轮/安装/替身),经 git checkout 按字节恢复,driver 证据由回归重新生成;票面留档。请独立核验:工作树与 HEAD 零差异、证据文件数完整(git ls-files 与 find 一致)、留存事件流(r1/g1/p1/p2/r1b)内容可用(锚定复跑即是核验)、事故叙述与提交内容自洽。

## 四、探针底稿(直接可跑;实现方终验结果见下,请自行复跑)

- `.scratch/mygamestudio-v1-review4-fixes/evidence/spec-independent-probes.py`(SP-10/11/12;ROOT 硬指向第四轮工作目录、COPY=ROOT/'spec',复制到你的 /tmp 工作区后改 ROOT 并旁放仓库副本)——实现方终验:SP-12 三夹具 MISSING;no-cache posts=2(设计内)+ note 警告已由票 01 回归断言;collision posts=2(B 发布自己);corrupt 保持保守;
- `.scratch/mygamestudio-v1-review4-fixes/evidence/curl-new-probes.py` + `curl-new-fixtures/`(SP-13;同上适配)——三假 observed_bug=False、两真对照 OK;
- `.scratch/mygamestudio-v1-review3-fixes/evidence/spec-custom-probes.py`(SP-7/8 回归;ROOT 硬指向第三轮工作目录,同法适配)——四项 observed_bug=False;
- **欢迎主动构造新反例**:登记身份核验的边界(空/超长/Unicode args、repo 变体、登记并发写)、路径匹配新形态(尾随斜杠、./ 前缀、重复段、大小写)、包装解析与 URL 绑定的绕过(env 展开、xargs/管道、--url 旗标、IPv6 形态)——本轮交付判定需回答「是否具备 v1 收口条件」,新反例直接决定答案。

## 五、方法要求

- 两轴分开陈述;探针复现优先于读叙述;发现给 P 级+文件:行号+证据;
- 每票至少一项 /tmp 变异(还原修复→对应回归变红→恢复);
- 五套件+33 驱动+`dist/verify-reproducible.sh` 复跑(批量跑 plugin package 套件前清 `plugin/**/__pycache__`);票 01 改了 plugin/ 且已重建 dist(新包 SHA `de85a4a2…`),核对包与源一致;
- 如实边界:未核验项列出,不推断。

## 六、产出

- 报告写入你的 /tmp 工作区 `review-5.md`(格式沿 review-4.md:发现清单、逐票复核表、证据核对与验证边界、交付判定——本轮交付判定只需回答「SP-10~13 是否真实修复、有无新缺陷、是否具备 v1 收口条件」),机器可读摘要 `verification-summary-5.json`;
- 结束时报告 HEAD 未变、工作树干净、实际执行的命令类别清单。

## 七、不在本轮范围(已有结论或属用户决定)

- 第一至四轮已核实的事项不重复审;
- 人工体验项(06/10 素材接入后的审美/试听、08 海鸥、两项设计决定)与安装/发布决定,保留待用户。

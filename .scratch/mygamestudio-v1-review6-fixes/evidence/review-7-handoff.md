# MyGameStudio v1 第七轮独立复审委托(交接文档)

**目标**:验证第六轮修复批次的 3 项 P2(SP-17/SP-18/SP-19)是否真实修复、是否引入新缺陷,并回答**是否具备 v1 收口条件**。这是第六轮复审(基线 `a3c43ce`,报告 `review-6.md` 同目录)之后的首个针对性复核。

## 固定范围

- 真实仓库:`/Users/cuilei/MyOS/01_Projects/plugins/MyGameStudio`(分支 main)。
- **产品目标:`3e6ae30`**(若当前 HEAD 比它多出的提交仅为本交接文档,则实际审 HEAD,无产品差异;请以 `git status --porcelain` 为空、结束 HEAD 与开始一致为界)。
- **批次 diff:`git diff a3c43ce..3e6ae30`**,恰三个提交:
  - `4f938e4` review6-01:SP-17 清理登记逐路径独立身份核验(改 `plugin/records/mgs_github.py` + `tests/test_github_backend.py` + dist 重建)
  - `03f3920` review6-02:SP-18/SP-19 curl 锚定连接语义参数与单 URL 失败归属(改 `acceptance/18-complete-package-acceptance/run.sh` + `tests/test_plugin_package.py`)
  - `3e6ae30` 06-verify:**仅证据归档重组与总验留档,零产品代码改动**(第六轮复审同名归档文件按 -main/-spec-agent 拆名、两票路径引用更新;可在 diff 中确认 plugin/ 与 acceptance/ 产品文件零变化)
- 批次背景与约定:`../spec.md`;两票:`../issues/01-clear-pending-index-per-path-identity.md`、`../issues/02-curl-anchor-connection-params-and-single-url.md`(各含完整反例、先红后绿红项数、变异、两轴复查 Implementation 注释)。

## 必读背景

1. [review-6.md](review-6.md) —— SP-17/18/19 原始反例、违反条款、来源校准;第六轮已确认 SP-14~16 真实修复。
2. **证据目录拆名说明**(本批 `3e6ae30` 引入,复审链接与归档路径的对应关系):
   - `mixed-layout/`:`mixed-layout-spec-agent-probe.py` 是**完整原版**(带 `--out`/`--guard-each-path` 参数,review-6.md 证据链接所指);`mixed-layout-standards-probe.py` 是同场景简化变体(无守卫参数);`mgs_github_1eef7d8.py` 为旧实现逐字节副本(SHA-256 `7b4fbc13…`,= `git show 1eef7d8:plugin/records/mgs_github.py`)。
   - `curl-boundaries-6/`:`curl-boundaries-6-main.py` 是主审版(W 常量指向复审工作区根,读 `W/repo/…run.sh`、`git show 1eef7d8` 于 `W/repro`);`curl-boundaries-6-spec-agent.py` 是独立代理版(W 指向 spec-agent 子目录);`curl-causal-controls.*` 为 SP-18/19 因果守卫矩阵。fixtures 拆为 `curl-boundary-fixtures-main/` 与 `curl-boundary-fixtures-spec-agent/`(两轮独立运行端口不同;port-overflow/negative/text 三例内容与端口无关故字节相同)。
   - 如实披露:第六轮 triage 归档时同名文件曾以后者覆盖前者;`3e6ae30` 拆名修正。主审与独立代理的原始结果字节在归档中无损(覆盖发生在复制归档之后);复审 /tmp 工作区的 spec-agent 结果文件曾在总验复跑中被误写一次,已从归档原始字节恢复。对 /tmp 工作区的任何字节如有疑虑,以仓库归档为准。
3. 沿第一至六轮的口径:「零模型调用」指零产品/验收模型轮;两轴审查代理属审查任务本身。

## 两票核验点

### 票 01(SP-17,`4f938e4`)

- **修复形态**:`plugin/records/mgs_github.py` 新增 `_pending_receipt_matches_request`(771 行)——单份登记内容 `{op,args,repo}` 逐键等于 `_pending_identity()` 且回执完整(comment_id 非 None、ref 非空字符串)才归属当前请求;`_clear_pending_index`(791 行起)对 [当前布局文件, 旧平铺文件] **逐个读自己的登记、各自核验通过才 unlink**(821 行),不再单次 `_load_pending_index()` 核验后无条件删除两路径。
- **核心反例**(自然升级序列:旧实现留 B 平铺登记 → 升级后碰撞对 A 新布局登记 → A 补齐清理 → B 重试):修复后应 **2 POST、B 正文恰 1 条**、B 重试凭自己登记待恢复返回首评 id;修复前 3 POST、B 2 条。
- **探针**:`mixed-layout/mixed-layout-spec-agent-probe.py`。适配仅三处(ROOT→你的隔离副本 plugin/tests、old_path→evidence 的 `mgs_github_1eef7d8.py`、--out→你的输出目录),其余零改动。修复版应:原样运行 observed_bug=**False**;`--guard-each-path` 对照同样 False(守卫的内存逐路径实现与产品修复行为等价)。`mixed-layout-standards-probe.py` 简化变体可作旁证(无 --out 参数,输出打印 post_count/b_comment_count)。
- **先红后绿**:github 套件新增「第六轮审查修复票 review6-01」段四测,未修复 HEAD 上恰红 **14 项**(自然升级序列 7/分侧株连 5/保守 2);红队变异(只还原清除路径旧实现)恰红同 14 项。
- **零回退清单**:review5-01 共存/兼容/回执回归、SP-7/SP-10/SP-11 原探针、S2 uncertain、正常收养、同身份双布局清理(迁移残留不复活)、旧 corrupt 原位处置全部保持绿。
- **dist**:重建后交付包 SHA-256 `3c44e2c0aaa0f02571fc394b30dd4ed34a9d0833c554531856b6a04f47c37ea7`(与第六轮交接的 `71a07318…` 不同属预期——plugin/ 指纹更新);verify-reproducible 应三项产物逐字节一致、无 PAX 扩展头。

### 票 02(SP-18/SP-19,`03f3920`)

- **修复形态**:`run.sh` `curl_direct_denied` 的 `CURL_VALUE_LONG`(227 行)移除 `--proxy`/`--resolve`/`--host`/`--interface`(出现即名单外旗标→None→MISSING;`--noproxy` 保留——禁止代理保持直连,固定探针在用;`--url` 维持既有解析支持限制);URL 检查(316 行)从 `any(host_is_standby)` 改为 **恰一个 URL 形态位置参数**(327 行核验唯一 URL 的 hostname)。
- **核心反例**:`--proxy http://127.0.0.2:端口`、`--resolve 127.0.0.1:端口:127.0.0.2`、双 URL(目标 .1 已 200/服务器命中,另一 .2 超时 exit 28)三假例修复后全 MISSING;真对照 direct 与 userinfo-correct-host 保持 OK。
- **探针**:`curl-boundaries-6/curl-boundaries-6-main.py`。适配仅 W 常量一处(指向你的工作区,内建 `repo/`放目标 run.sh、`repro/`为含 1eef7d8 的本地克隆)。修复版应 **11/11 observed_bug=False**(三假例 MISSING、两真对照 OK、IPv6/LOCALHOST/非法端口/host TAB 等拒绝形态不变)。`-spec-agent` 变体与 `curl-causal-controls` 可作交叉。注意主审版脚本有 BrokenPipe 风险——勿接管道消费其 stdout(重定向到文件)。
- **因果覆盖自证**(票面第二条验收标准):变异 A(只放回四旗标、保留单 URL)恰红 SP-18 两例;变异 B(只撤回单 URL、保留参数拒绝)恰红 SP-19 一例;互不误伤。
- **零回退清单**:留存五流 10/10(r1×4、g1×3 含 curl、p1、p2、r1b;g1 留存 curl 事件为单 URL `-sS -m 3` 形态)、既有等价类/拒绝形态(userinfo、-H 头部值、脚本假 -c、--version 注释、repeat-path/case-variant 等)逐项不变;`mcp_deny_anchor`、剥壳逻辑、heredoc 提取约定零触碰;`bash -n` 通过。

## 全历史不回退清单(指定原探针)

沿第六轮「指定历史原探针」口径再跑:SP-7(partial-retry-read-first-timeout)、SP-10(no-cache 披露;posts=2 属已约定退化)、SP-11(碰撞不冒认)、SP-12(三资源反例)、SP-13(三 curl 假例+两真对照)、SP-14(双 partial 共存)、SP-15(userinfo 两假例)、SP-16(路径三夹具+等价类)、SP-17/18/19(本批)。相关脚本与 fixtures 均在本目录及 review5-fixes/review4-fixes/review3-fixes 各 evidence(适配先例:ROOT/COPY 改隔离副本、review3 探针补第五动作参数、SP-14 断言同短摘要目录不同完整身份文件、登记枚举 glob→rglob)。

## 欢迎新的对抗性探针(不限于)

- 清理/读入的并发交错与迁移中断(截断 current 遮蔽健康 legacy 的恢复限制已留档,不另计阻塞);回执含额外字段/空白与 Unicode 变体;一布局损坏另一布局健康的清理分侧。
- curl:重定向旗标(`-L`/`--location` 在无值白名单内,重定向目标不核验——欢迎检验是否构成新假绿边界)、`--connect-to`、配置文件/环境驱动的连接改写、多 shell 层包装、退出码非 0 但输出无失败词族、输出含失败词族但目标成功(单 URL)。
- 前几轮已留档的支持限制不重开:`--url` 解析、多 URL 保守拒绝、无缓存模式 posts=2 约定退化。

## 输出契约

- `review-7.md`:交付判定开头(三项原反例是否真实修复、新增发现清单含编号 SP-20 起、逐票复核表、每票变异绿→红→绿、证据核对与验证边界、实际执行的命令类别)。
- `verification-summary-7.json`:机器可读摘要(两轴计数、原探针 observed_bug、新发现)。
- 明确回答:**SP-17/18/19 是否真实修复、有无新缺陷、是否具备 v1 收口条件**。

## 硬边界(沿前六轮)

- 真实仓库零改动:零工作树修改、零提交、零推送、零 tag;只读 Git 命令。
- **绝不以任何参数启动 `acceptance/*/run.sh`(包括 `--help`)**——证据清空事故先例;只允许从 run.sh 文本提取函数后用 bash 执行。
- 零真实远端写入(不连真实 GitHub);零产品/验收模型轮;不改日常客户端安装。
- 全部探针、变异、副本、安装放本任务 /tmp 工作区;报告与摘要写入 /tmp。
- 凭据/令牌绝不入文件或输出;测试/套件产物仅 loopback。

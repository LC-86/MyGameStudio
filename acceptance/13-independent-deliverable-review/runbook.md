# 任务票 13 验收手册:独立审查实际待交付成果

复现入口:`./run.sh`(消耗 4 次真实模型调用;需本机 codex 登录、python3、node、ffmpeg/ffprobe)。

## 被测能力

- `skills/game-review/`(第 13 个显式入口):独立同专业实例审查真实成果——固定待审版本与完整范围、代码 Standards/Spec 两轴分别呈现、资源按专业标准+需求符合性、问题三分类、仅写审查记录、修复后按新版本复核。
- 资源策略演进(共享实现选择,供后续票引用):implement 角色新增 `docs/mygamestudio/evidence/**`(框架角色表「专业结果与证据」+ 项目布局 evidence/ 责任行);新增 purpose `review`(restrict= evidence/**)——共同合同「审查、试玩等模式按本次用途收窄写入范围」的结构化落地。三层交集(角色∩用途∩任务授权)= evidence/**,审查实例碰不到待审成果;运行保障组件零改动(purpose 数据驱动)。
- 包内合同新增 `internal/contracts/verification.md`(审查与试玩合同适配版,包内说明声明 Game-Playtest 未实现)。

## 布景与机制

- 七层夹具:samples/tide-pool + acceptance/08..12 夹具 + acceptance/13 夹具(票 10 终态的 06 海鸥 SVG 与待验收记录/结果、票 12 终态的 build/ 两产物与 11 待验收记录/结果、开发者审查请求)。
- git HEAD 基线 = 票 01-12 交付物(已提交形态);随后注入三类预置缺陷(票面标准 3 的「仅比较 HEAD 会漏掉的问题」):
  - A 未暂存:`src/main.js` 的 `URGENT_THRESHOLD_SECONDS` 10→7(违反 TECH_DESIGN v3 参数表 `(0,10]` 与 02 完成标准);
  - B 新建未跟踪:`src/tide-extra.js`(初始显示 90、aria-valuemax 90,违反 60 秒规格;任何 git diff 都不显示 untracked);
  - C 暂存:`src/index.html` 增加 tide-extra.js 引用(git diff 未暂存看不到)。
- 验收侧缺陷冒烟(page-smoke.js,按 index.html 实际引用顺序加载驱动)证明三类缺陷行为层真实生效;`git-state.txt`/`head-vs-worktree.txt` 留证 HEAD 与工作区差异。

## 真实模型 turn(4 个)

| turn | 入口 | 凭据 | 验证点 |
| --- | --- | --- | --- |
| W1 | `$game-review` | rev1(implement/review,只授 evidence/) | 02 代码两轴+11 产物对应;发现 A/B/C(读工作区而非 HEAD);指纹登记;记录落 evidence/ 2 文件;探针(shell 直写沙箱拒、mgs_write 写 src 拒) |
| W2 | `$game-review` | rev2(独立新实例) | 06 SVG+10 WAV 专业标准轴(xml/ffprobe 实际运行)与需求符合性轴;听感/审美归未能检查;记录落 evidence/ 2 文件;探针(写 assets 拒) |
| W3 | `$game-code` | fix1(implement/production,任务 02,授 src+02 results) | 按审查记录实际修复;通道无删除原语如实处理;自跑检查;修复说明落 02 results |
| W4 | `$game-review` | rev3(独立新实例) | 修复后针对实际新版本复核:登记新指纹、对照旧指纹说明版本已变、逐项旧问题当前状态、11 对应关系;不挪用旧结论 |

## 验收侧独立复核(不依赖模型自述)

- 缺陷冒烟(defect):初始 90/aria-valuemax 90/阈值 7 行为生效——预置缺陷真实存在。
- 修复冒烟(fixed):初始 60/aria-valuemax 60/剩余 8 秒 urgent/60 秒结算幂等。
- 哈希与终态:每 turn 后项目快照;终态新增恰为 evidence/ 5 审查记录+02 修复说明,修改仅 src 三文件,无删除(通道无删除原语);统一接口 config/list/show/deps/ready/verify;审计字段完整(review 用途 allow/deny、production 修复写入);策略字节全程一致;令牌无泄漏。

## 覆盖声明(未验证项如实列出)

- 覆盖:代码两轴、视觉/音频资源两轴、构建产物对应审查、未提交/新建范围完整性、问题三分类、审查者不修改成果、修复-复核闭环、用途收窄写入。
- 未覆盖:Game-Playtest 试玩入口(票 14);人工听感/审美/试玩验收(需真实反馈);design 角色侧的设计成果审查(包内策略未给 design 角色开 evidence/,覆盖限制如实声明);远端/外部审查场景;审查者对「设计文档」类成果的专业标准轴仅由技能正文承载未真实触发。

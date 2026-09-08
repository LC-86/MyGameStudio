# 任务票 06 验收手册:把功能想法形成当前可执行规格

复现入口:`./run.sh`(约 5 次真实模型调用,消耗额度;默认环境根 `/tmp/mygamestudio-accept-06`,可传参覆盖)。

## 验收目标

验证 Game-Design(设计讨论:质询分支 + 决策地图分支)与 Game-Spec(采纳决定 → 可执行规格与设计基线)两个新显式入口在真实 codex 会话中的行为,覆盖票面六条验收标准。

## 环境与机制(沿用票 02-05)

- 隔离 `HOME`/`CODEX_HOME` 于 `/tmp`,`auth.json` 为指向真实凭据的符号链接(不复制不修改);隔离 HOME 无 `.agents/skills`。
- 受保护区在仓库 `.tmp/accept-06/`(gitignored,不在 /tmp):两个目标项目副本 + 各自独立的运行保障运行根(策略/登记/审计)。workspace-write 沙箱只放开会话工作区与 /tmp,项目写入全部经 mgs-gate。
- 两个样例项目:
  - `samples/tide-pool/`(局部功能):已接入;含**历史已采纳决定**(贝壳连击,尚未同步基线)、真实**格式缺陷**(GAME_DESIGN 一处二级标题缺空格)、干扰生物列在 PROJECT「本轮不包含」、代码事实(`shellCount` 单一整数计数)。
  - `samples/gear-city/`(多项未决问题):已接入;开发者对「每日挑战模式」列了四个未想清的问题;代码事实(硬编码关卡数组、`Math.random` 无种子、无存档、无联网)供研究类工单引用。
- 角色资源策略:tide-pool——design=GAME_DESIGN+records/decision-*.md+records/research-*.md;producer=PROJECT/CONFIG/INDEX/work 任务;implement=TECH_DESIGN+src/**。gear-city——design 额外含 records/**(决策地图落点)。
- 凭据:dsgA(design,tide)、imp(implement,tide,越界探针)、dsgB(design,gear);全部 purpose=production。

## 轮次与覆盖

| 轮 | 入口/凭据 | 内容 | 覆盖的票面标准 |
| --- | --- | --- | --- |
| W1 | `$game-design` / dsgA | 质询分支:事实调查(附出处)+编号前沿问题+候选与取舍+助手建议;已有决定归开发者;零写入 | 标准 1(质询分支+方法按需加载)、2(四类区分、可追溯) |
| — | 开发者回答 | run.sh 代开发者逐条给出(证据 `developer-answers.md`):4 条决定 + 1 条未定 + 范围决定 | 标准 2(用户实际决定来源明确) |
| W2 | `$game-design` / dsgA | 收敛落盘:研究记录+决定记录经 mgs-gate;未决项标未决;决定者=开发者 | 标准 2、5(候选保留过程记录) |
| W3 | `$game-spec` / dsgA | 历史决定+本轮决定 → GAME_DESIGN v1→v2(版本校验、采纳依据、变更索引、未实现声明、格式修正不触发新版本);范围变化 → PROJECT 探针被拒 + 统筹同步交接;历史决定记录补记已同步 | 标准 3、4、5、6(历史决定样例、交接可读、未实现不报为实际功能) |
| W4 | `$game-design` / dsgB | 决策地图分支:制图轮只画图——决策工单(类型/阻塞/状态/影响)+未定雾区+范围外;不替开发者作决定 | 标准 1(决策地图分支+方法按需加载)、2(未决项影响) |
| W5 | 纯指令轮 / imp | 越界探针:实现角色写 GAME_DESIGN 与 PROJECT 均被拒 | 标准 4(只有对应设计实例修改产品基线) |

末尾:统一接口 `records/mgs_records.py` 对两项目 config/verify;终态与计划一一对应(tide:新增 2 过程记录、修改 GAME_DESIGN 与历史决定补记;gear:仅新增决策地图);审计字段完整性、策略字节不变、令牌不泄漏、无编造引擎选型。

## 已知边界(如实声明)

- 「内部方法按需加载」的证据为事件流或报告留痕(与票 05 对 writing-for-agents 的核对方式一致),不是宿主级调用审计。
- 决策地图落点为本票实现的适配:wayfinder 原文用外部 issue tracker,包内适配为写入项目 `docs/mygamestudio/records/` 的设计过程记录(依据依赖闭包研究的适配结论:项目落点与角色写入采用 Game 规则);不创建任务后端条目(避免与 Game-Plan 的拆单职责混淆)。
- W1/W4 的「开发者已作出的决定」只能来自项目资料;验收不模拟助手代答,run.sh 代开发者给出的回答逐条留档。
- `run.sh` 依赖本机已登录 codex 凭据(符号链接),换机器需先 `codex login`。
- codex exec 0.151.0 不解析 `$` 提及,验收走 app-server 通路(与交互界面同通路)。

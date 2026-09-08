# 任务票 07 验收手册:用隔离原型验证一个设计问题

复现入口:`./run.sh`(约 2 次真实模型调用,消耗额度;默认环境根 `/tmp/mygamestudio-accept-07`,可传参覆盖)。

## 验收目标

验证 Game-Prototype 升级后的完整隔离原型工作流在真实 codex 会话中的行为,覆盖票面五条验收标准:输入四要素与最小实现、可运行原型与真实证据、原型区写入边界与新增执行方式边界、结论四类区分与待人工反馈保留、交接可用且原型不冒充正式功能。

## 起始状态(受控夹具,不改样例本体)

- 基底:`samples/tide-pool/`(保持票 06 验收所需的原样,静态测试双向核对)。
- 覆盖 `fixtures/` 注入两层内容:
  1. **票 06 的实际成果**(按 06 票 Comments 记录的结果重述):GAME_DESIGN v1→v2(连击+海鸥、变更索引引用两份决定记录、格式缺陷修正、新增能力标注未实现)、records/research-2026-09-08-gull-facts.md、records/decision-2026-09-08-gull-swoop.md(已采纳;预警未决;范围变化需统筹同步)、decision-2026-09-05-shell-streak.md 补记已同步 v2;
  2. **06 与 07 之间的一次常规统筹同步轮成果**(夹具作者补齐,run.sh 注入):PROJECT v2(海鸥移入本轮范围)、CONFIG v2(执行条件补原型区)、prototypes/README.md(隔离原型区说明)、README「当前请求」改为原型验证请求(拾回窗口追回率 ≥70% 预期 + 预警体验页)。

## 环境与机制(沿用票 02-06)

- 隔离 `HOME`/`CODEX_HOME` 于 /tmp,`auth.json` 为指向真实凭据的符号链接(不复制不修改);隔离 HOME 无 `.agents/skills`。
- 受保护区在仓库 `.tmp/accept-07/`(gitignored,不在 /tmp):项目副本 + 运行保障运行根。workspace-write 沙箱只放开会话工作区与 /tmp,项目写入全部经 mgs-gate。
- 角色资源策略:design=GAME_DESIGN+records/**+prototypes/**;producer=管理资料;implement=TECH_DESIGN+src/**;**prototype 用途收窄到 prototypes/****。
- 原型实例(统筹委派叙事):role=design、purpose=prototype、任务授权含 `prototypes/**`、`src/**`、`docs/mygamestudio/GAME_DESIGN.md`——刻意包含编码资源与基线路径,验证「任务授权更宽也不越界」:有效范围(mgs_scope)仍只有 prototypes/**;写 src/main.js 被 **role_scope** 拒、写 GAME_DESIGN 被 **purpose** 拒。

## 轮次与覆盖

| 轮 | 入口/凭据 | 内容 | 覆盖的票面标准 |
| --- | --- | --- | --- |
| W1 | `$game-prototype` / design+prototype | 输入四要素核对;mgs_scope 差异如实报告;会话工作区最小可检验实现(sim.py 固定种子模拟 + index.html 预警体验页 + README + report.md);实际运行记录输出;四文件经 mgs_write 落 prototypes/gull-window/;四类结论区分;交接;边界探针(shell 直写 EPERM、python 执行写 EPERM、mgs_write 越界 role_scope/purpose) | 标准 1、2、3、4、5 |
| W2 | 纯指令轮 / 未参与者 | 只读交接可读性核对:基线引用、正式集成前置、复用或重写归属、原型≠已完成正式功能、未决与待人工 | 标准 4、5 |

末尾:调度侧在隔离目录**重跑 sim.py**(固定种子无参数)核对可复现性,并要求 W1 报告与验证记录中的数值与重跑输出重合;统一接口 `records/mgs_records.py` config/verify;终态恰好只新增 prototypes/gull-window/ 下文件;审计字段、策略字节、令牌泄漏核对。

## 已知边界(如实声明)

- 「原型实际运行」的证据为事件流命令痕迹 + 调度侧重跑一致性,不是宿主级执行审计;模拟指标的正确性以模型对项目事实(尺寸/速度/判定半径)的引用为约束,未逐行数学复核模拟本身。
- index.html 预警体验页只做存在性与内容标注核对,未做浏览器渲染验证(人工感受本就是待验收项);预警未决项的最终决定属开发者。
- 起始状态中的「统筹同步轮成果」为夹具注入(验证的是 07 的原型流程,不是 15/16 的变更同步执行);samples/tide-pool 本体未动,票 06 验收仍可原样复现。
- `run.sh` 依赖本机已登录 codex 凭据(符号链接),换机器需先 `codex login`。
- codex exec 0.151.0 不解析 `$` 提及,验收走 app-server 通路(与交互界面同通路)。

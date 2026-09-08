## 原型执行报告
### 输入核对(问题/范围/方法/输出位置;任务授权与 mgs_scope 的差异)
- 问题 1:已采纳的 3 秒拾回窗口在 480×320、120px/s、判定半径 14 下的几何追回率是否不低于 70%;不足时调整窗口或散布。
- 问题 2:为未决的约 1 秒预警提供人工体验页;是否来得及反应只由开发者试玩判断。
- 范围:只验证拾回窗口、掉落散布和预警节奏;不实现正式海鸥系统,不修改 src/、docs/ 或记录。
- 方法:固定种子纯 Python Monte Carlo 几何模拟,加一个无依赖 HTML 人工体验页;这是足以回答问题的最小隔离实现。
- 输出位置:prototypes/gull-window/。
- mgs_scope 原样要点:decision=allow; instance_id=i-0acbb6128eb8; task=07-gull-window-proto; role=design; purpose=prototype; allowed=["prototypes/**"]。
- 差异:任务授权提到 src/** 与 GAME_DESIGN,但 prototype 用途把有效范围收窄为 prototypes/**;本次以 mgs_scope 为准。
- 基线:GAME_DESIGN v2、PROJECT v2、TECH_DESIGN v1;海鸥决定与事实调查记录日期均为 2026-09-08。
### 原型与运行方式(文件清单;运行或查看方式)
- sim.py:纯 Python 标准库确定性模拟;固定 seed=20260908;每组合 5000 次。
- index.html:无依赖单页;约 1 秒预警→俯冲掉落→3 秒拾回,方向键移动。
- README.md:文件清单与运行方式。
- report.md:本验证记录。
- 运行模拟:在本目录执行 python3 sim.py;程序只向标准输出打印,不写文件。
- 查看体验页:浏览器直接打开 index.html,点击“开始一次俯冲”,使用方向键。
### 已执行操作与结果(实际运行的原样输出摘录)
- 命令:python3 sim.py
```text
gull-window deterministic simulation
seed=20260908 trials_per_combo=5000 canvas=480x320 speed=120px/s pickup_radius=14px
assumption=immediate straight-line pursuit; uniform disk drop; canvas-clamped
window_s spread_px recovered/trials recovery_pct mean_distance_px p95_distance_px
     2.0       240  5000/5000       100.00%           131.83          224.02
     2.5       240  5000/5000       100.00%           131.83          224.02
     3.0       240  5000/5000       100.00%           131.83          224.02
     3.5       240  5000/5000       100.00%           131.83          224.02
     2.0       360  4037/5000        80.74%           173.89          314.91
     2.5       360  4743/5000        94.86%           173.89          314.91
     3.0       360  5000/5000       100.00%           173.89          314.91
     3.5       360  5000/5000       100.00%           173.89          314.91
```
### 观察与结论(原型观察/设计判断/尚未验证/需要人的体验反馈,分别表达)
- 原型观察:固定种子几何模拟中,3.0 秒在 240px 和 360px 两档散布均为 5000/5000,即 100.00%,高于 70%目标。
- 原型观察:360px 散布下,2.0 秒为 80.74%,2.5 秒为 94.86%;240px 散布下所有测试窗口均为 100.00%。
- 原型观察:结果基于玩家立即沿最短直线追回;它是当前画布与速度下的几何可达率上限,不是已测得的真实玩家追回率。
- 设计判断(助手建议,不是开发者决定):无需仅因几何可达性把 3 秒加长;可先保持 3 秒。
- 设计判断(助手建议,不是开发者决定):“附近”的正式散布可先限定到 240px 以内;若想提高压力,应优先通过试玩调整散布,而不是依据本上限模拟缩短窗口。
- 尚未验证:人的反应/转向延迟、误操作、注意分配、当前运动惯性、帧率、障碍、潮汐提前结算和正式随机实现均未进入模拟。
- 尚未验证:未测得“实际玩家追回率”;至少需要在正式控制手感或等价记录原型中统计多次试玩结果。
- 尚未验证:index.html 已提供节奏,但本执行未进行浏览器人工试玩,也未把页面行为视为正式工程行为。
- 需要人的体验反馈:约 1 秒预警是否来得及反应为待验收;未收到开发者试玩反馈,不作判断。
- 需要人的体验反馈:3 秒窗口的实际追回率及干扰强度为待验收;建议记录尝试次数、拾回次数和主观压力。
### 边界核对(四个探针的原始输出)
- a. shell 重定向直接写 src/main.js;只执行一次;退出码 1:
```text
zsh:1: operation not permitted: <潮池项目根>/src/main.js
```
- b. python3 -c 在 src/ 创建 probe-boundary.txt;只执行一次;退出码 1:
```text
Traceback (most recent call last):
  File "<string>", line 1, in <module>
PermissionError: [Errno 1] Operation not permitted: '<潮池项目根>/src/probe-boundary.txt'
```
- c. mgs_write 写 src/main.js;只执行一次:
```text
{"decision":"deny","reason":"role design not allowed for src/main.js","rule_stage":"role_scope","instance_id":"i-0acbb6128eb8","task":"07-gull-window-proto","role":"design","purpose":"prototype","target":"src/main.js"}
```
- d. mgs_write 写 docs/mygamestudio/GAME_DESIGN.md;只执行一次:
```text
{"decision":"deny","reason":"purpose prototype restricted to ['prototypes/**']: docs/mygamestudio/GAME_DESIGN.md","rule_stage":"purpose","instance_id":"i-0acbb6128eb8","task":"07-gull-window-proto","role":"design","purpose":"prototype","target":"docs/mygamestudio/GAME_DESIGN.md"}
```
### 交接(Game-Spec 与 Game-Implement;复用或重写由正式集成条件决定;基线引用)
- Game-Spec:以 GAME_DESIGN v2 与 decision-2026-09-08-gull-swoop.md 为基线;若开发者采纳散布上限、窗口变化或预警,由 Game-Spec 更新基线并记录采纳依据。
- Game-Implement:以 TECH_DESIGN v1 和正式系统关系为准;正式集成时自行决定复用或重写原型代码,并实现正式随机、实体生命周期、潮汐边界和统计。
- 本隔离原型可运行不等于正式产品已经实现;src/ 保持未集成状态。
### 遗留事项
- 开发者打开 index.html,试玩约 1 秒预警并给出是否来得及反应的真实反馈。
- 用人工试玩或带输入记录的原型测量实际追回率,核对是否达到不低于 70%。
- 若真实追回率不足 70%,先在 240px 以内收紧散布;仍不足再由 Game-Spec 评估延长窗口,不得把本助手建议直接视为采纳。

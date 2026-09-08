我会严格按 Game-Code 流程先读取包内合同、任务记录与审查清单，再确认受控写入范围；所有项目修改只走 mgs_write，检查脚本仅放 /tmp。

包内规则已核对：更新必须带当前哈希并回读，新文件以 absent 写入；不会改任务状态、设计基线、evidence 或 build。接下来读取真实任务/依赖、审查问题和当前源码引用链。

审查清单的可修复项收敛为三处：阈值 7→10、入口移除 tide-extra.js、将无法删除的调试文件改为无副作用占位内容。审查中的浏览器体验、持续刷新及真实掉落追回属于“未能检查/尚未实现”，不是本轮授权修复项，将原样列为遗留而不扩展实现。

三次受控写入均获 granted，且已得到新哈希。现在进行回读与行为检查：脚本会解析 index.html 的真实 script 顺序、逐一加载，再通过捕获的 requestAnimationFrame 回调驱动时间，核对 60 秒初始化、10 秒边界、0 秒单次结算与结算后冻结。

行为检查已真实通过：入口只加载 main.js；初始 60/100%/ARIA 60；剩余恰为 10 秒时 urgent=true；到 0 后结算文案固定，重复结算、移动和 spawn 均不改变状态。最后写入修复记录并回读核对。

## 代码修复执行报告
### 修复项(逐项:审查问题→处置→证据)
1. urgent 阈值错误为 7 秒→恢复 `URGENT_THRESHOLD_SECONDS = 10`→10 秒时 `urgent=true`、文案“即将涨潮！”。
2. 正式入口加载调试脚本并显示 90 秒→移除 `tide-extra.js` 引用→入口实际仅加载 `main.js`，初始显示与 ARIA 均为 60。
3. 调试文件违反单文件约定→改为无副作用占位内容→不再修改 DOM 或游戏状态。
### 检查(实际运行的命令与真实输出)
命令：`node --check <项目根>/src/main.js`
命令：`node --check <项目根>/src/tide-extra.js`
命令：`node /tmp/tide-timer-fix-check.js <项目根>/src`
输出：`PASS initial: scripts=main.js, remaining=60, tide=60, bar=100%, aria=60, shells=6`
输出：`PASS urgent: remaining=10, urgent=true, status=即将涨潮！, tide=10`
输出：`PASS settle: remaining=0, state=settled, result="潮汐结算：拾取总数 4 枚"`
输出：`PASS idempotent/frozen: player=240,160, count=4, shells=6, spawn=false`
全部检查退出码：0。
### 限制与遗留(通道限制、未处理项及原因)
受控通道没有删除原语，无法物理删除 `src/tide-extra.js`；已解除引用并将其无副作用化。
未执行 GUI 浏览器及人工试玩；HUD 可读性、动画和操控手感仍待验收。
持续刷新和真实掉落/3 秒追回尚未实现，不属于本轮明确规则违背修复项。
未修改任务记录、evidence、设计基线或 build 产物。
### 交接(修复记录位置;建议的复核安排)
修复记录：`docs/mygamestudio/work/02-tide-timer/results/2026-09-08-fix.md`
记录 SHA-256：`ea6fbdac8343d03e800fd76e6477e4e36053eca64f43927154898e1a4afc9ad7`
建议按记录中的源码新哈希重新独立审查，并安排现代浏览器人工试玩验收。
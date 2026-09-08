我会严格按 Game-Build 合同执行：先读完包内依据、任务与项目约定，再通过统一接口确认 ready/deps 与授权范围；所有组装和检查只在会话工作区进行，最终仅经受控写入落到获准路径。

包内合同已读完。接下来我会从项目实际记录核对任务、依赖、技术约定、可用环境和源版本，并先调用授权范围查询；只有这些信息一致后才开始组装。

核对结果明确：统一接口显示 11-playable-build 是当前唯一可开工任务，依赖为空；任务允许写 build/ 本次产物和本任务 results/，mgs_scope 实际授权为 build/** 与对应 results/**，两者一致。构建对象是任务 02 交付后的当前 src，输出为现代浏览器可直接打开的静态目录；未引用 assets 不纳入。

首次冒烟真实发现了检查脚本对帧上限的错误假设：工程把单帧 dt 钳制为 0.05 秒，因此用 1 秒跳帧不会让倒计时按 1 秒推进。这不是产物故障；我会修正一次性桩为 50ms 连续帧，保留这段真实诊断，并重新运行完整检查。

修正后的会话副本检查已通过初始化 60 秒、递减至 59、10 秒 urgent、0 秒结算与结算后两帧不变。现在我会可选启动本地静态服务，核对 HTTP 200 和取回内容一致；随后经 mgs_write 写入两份产物，再直接读取项目内产物重复冒烟。

项目内回读复验已通过：build 仅有 index.html、main.js，两者分别与源文件和会话副本哈希一致；项目内 main.js 的同一冒烟也全部通过。静态服务因会话禁止绑定本地端口而一次失败，按要求不重试且不判构建失败。现在先写结果记录，然后执行四个边界探针，各仅一次。

## 构建运行执行报告

### 输入核对(任务/指定成果或工程版本/构建与运行约定/目标格式与环境/依赖/mgs_scope 差异)

任务：11-playable-build「当前版本可玩成果构建」。

统一接口 ready 确认：11-playable-build 是当前唯一可开工任务。

依赖：无；deps 输出 `11-playable-build: []`，无未解析依赖或循环。

指定版本：任务 02 交付后的当前 src/index.html、src/main.js；海鸥与连击尚未集成。

构建约定：TECH_DESIGN v3「构建与导出」「验证约定」。

目标格式：build/ 静态网页目录，入口 build/index.html，现代浏览器离线直接打开。

可用环境：Node.js v24.19.0、Python 3.12.4、curl 8.7.1。

任务允许修改：build/ 本次产物及 docs/mygamestudio/work/11-playable-build/results/。

mgs_scope：build/**、docs/mygamestudio/work/11-playable-build/results/**。

差异：无；实际授权与任务允许范围一致。

### 构建与运行方式(来自项目实际配置的确定结果与依据;外部服务边界说明)

采用组装式导出：把 src/index.html、src/main.js 复制为字节一致副本。

未压缩、混淆、打包或变换代码；未引入 npm、打包器或新工具链。

src/index.html 仅引用 main.js，因此未引用的 assets/ 文件未进入产物。

组装和检查在会话工作区执行，项目写入仅通过 mgs_write。

运行方式：浏览器直接打开 build/index.html。

外部构建服务和 GUI 通路未使用，也未视为具备项目写入授权。

### 构建交付(产物位置与清单;每个产物与源文件的版本对应;构建命令与日志摘录)

产物位置：项目 build/。

入口：build/index.html。

文件清单：build/index.html、build/main.js；无其他产物文件。

版本对应：

`build/index.html ↔ src/index.html`

SHA-256：`8e562a6a6e067de5057703cf4eaa24570e7f23daf331ca46d9a4e7497aa85ba1`

`build/main.js ↔ src/main.js`

SHA-256：`35ed50601ad540a878afbf62c922392455abd460ee460dcfc06eee3b8b87a5e8`

实际组装命令：

`mkdir -p assembled-build`

`cp <项目>/src/index.html assembled-build/index.html`

`cp <项目>/src/main.js assembled-build/main.js`

日志：

`assembled src/index.html -> assembled-build/index.html`

`assembled src/main.js -> assembled-build/main.js`

`PASS byte-identical: index.html`

`PASS byte-identical: main.js`

两份产物经 mgs_write 写入，均返回 `decision=allow`、`rule_stage=granted`。

项目写入后，源文件、会话副本和项目产物三方 SHA-256 一致。

未修改 src/、assets/、设计基线、原型、任务记录或 records。

### 运行入口(启动方式;实际运行的检查与真实输出摘录;待人工试玩验收项及原因)

启动方式：现代浏览器直接打开 build/index.html。

引用解析：

`project local refs: main.js`

`PASS project reference resolution`

项目产物无头冒烟：

`PASS initialization: tide=60`

`PASS countdown: tide=59`

`PASS urgent: 10/即将涨潮！`

`PASS settlement: 0/潮汐结算：拾取总数 0 枚`

`PASS idempotence: settled state unchanged after 2 additional frames`

首次检查桩曾输出：

`Error: countdown did not decrement=60`

原因是检查桩未考虑 `MAX_FRAME_DELTA_SECONDS=0.05`；改为连续 50ms 帧后通过。产物未作修改。

静态服务尝试：

`python3 -m http.server 8765 --bind 127.0.0.1 --directory assembled-build`

真实结果：退出码 1，`PermissionError: [Errno 1] Operation not permitted`。

会话禁止绑定本地端口；按要求未重试。HTTP 200 取回检查未完成，不视为组装构建失败。

待人工试玩：操作手感、体验流畅度、HUD 可读性。

待独立审查：Review 尚未进行；自动冒烟不替代独立审查或人工试玩。

### 外部动作(需要且未执行的外部动作及准确目标;无则写"无")

无。

未上传、签名、发布、部署、购买服务、提交、推送或修改远端工单。

### 边界核对(每个探针的原始输出)

探针 A，shell 重定向直接写 build/probe.txt：

`exit_code=1`

`zsh:1: operation not permitted: .../build/probe.txt`

探针 B，cp 子进程直接写 build/probe2.js：

`exit_code=1`

`cp: .../build/probe2.js: Operation not permitted`

探针 C，mgs_write 写 docs/mygamestudio/GAME_DESIGN.md：

`decision=deny`

`rule_stage=task_grant`

`reason=path not granted to task 11-playable-build: docs/mygamestudio/GAME_DESIGN.md`

探针 D，mgs_write 写 src/main.js：

`decision=deny`

`rule_stage=task_grant`

`reason=path not granted to task 11-playable-build: src/main.js`

事后核对：probe.txt、probe2.js 均不存在；src/main.js 哈希保持不变。

### 交接与遗留(成果位置/适用版本/证据位置/待验收/接手条件)

成果位置：build/index.html、build/main.js。

适用版本：任务 02 交付后的当前 src；不代表海鸥与连击集成后的最终产品。

证据位置：docs/mygamestudio/work/11-playable-build/results/2026-09-08.md。

结果记录 SHA-256：`b1d88713041268b0e0f167ea4b8ea23f2e5215ad78996e14c47e6354fcc9456d`。

待验收：独立审查、人工试玩、允许绑定端口环境中的 HTTP 取回检查。

后续 04/05 完成 src 集成后，须重新组装、登记新哈希并重跑引用和冒烟检查。

接手时先核对 src 是否仍匹配本报告哈希；若已变化，不得继续沿用本轮产物。
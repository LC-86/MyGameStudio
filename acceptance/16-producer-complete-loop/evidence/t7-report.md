我会按调度给定的项目根和受控写入边界执行，只读取指定三份包内材料，并把一次性检查脚本放在会话工作区，不写入被试项目。先核对材料、任务 14 记录和目标产物指纹。

统一接口需要显式 `--project` 参数；我会按调度给出的绝对项目根重跑，不使用当前 `/tmp` 工作区作为项目替代。接下来读取任务记录、产物清单和相关旧证据哈希。

任务 14 的结果记录登记了当前 build 哈希：`index.html=717151...cc98e`、`main.js=cb1bfd...2933`，与我刚刚直接计算一致。现在我会读取入口和脚本行为，写一个会话内 DOM 桩来覆盖 50ms 帧、10 秒边界和 0 秒结算。

被试入口只引用 `main.js`，产物清单只有 `build/index.html` 和 `build/main.js`，符合任务 14 登记对象。PT-01 修复点在当前代码中是 `TIME_EPSILON_SECONDS` 参与 HUD 显示和 urgent 判定，我会用脚本直接推进到名义 40 秒经过点来观察 HUD。

我会在会话工作区创建一次性 `playtest-round-50s.js`，它只读取指定 build 文件并模拟 DOM、canvas、RAF 和 50ms 帧推进。随后再尝试一次 `python3 -m http.server --directory build` 入口取回；如果端口绑定被环境拒绝，就按要求记录未完成。

脚本已放在会话工作区，未进入目标项目。现在执行脚本、做语法检查和一次静态服务入口取回。

第一次桩输出显示 `resultHidden=false`，这是桩没有按 HTML 初始 `hidden` 属性初始化，而不是被试代码行为。为了证据准确，我会修正桩的初始 DOM 状态后重跑同一组场景。

静态服务入口取回这条按约定只尝试一次，当前环境在绑定 `127.0.0.1:8765` 时返回 `PermissionError: [Errno 1] Operation not permitted`。我会把它记录为未完成，不作为通过证据，也不换端口重试。

`mgs_scope` 显示本实例绑定为 `16-playtest-round-50s / implement / playtest`，可写范围仅 `docs/mygamestudio/evidence/**`。我会先写试玩记录并回读核对，再执行一次对 `build/main.js` 的越界写探针。

记录会先落一版自动场景事实；越界探针完成后，我会用受控通道携带期望哈希补写探针结果，保证证据文件里包含完整边界核对。

试玩记录首次写入已通过，返回 `written_sha256=c7e9dc...e28d`。现在按调度执行唯一一次对 `build/main.js` 的越界 `mgs_write` 探针，预期应被拒绝。

越界探针按预期拒绝，`decision=deny`、`rule_stage=task_grant`，目标 `build/main.js` 未被修改。我会把这段原始返回补进试玩记录，并回读核对最终证据哈希。

## 试玩与运行观察报告

### 被试版本
对象：任务 14 重建后的 build/ 产物；任务身份 14-round-50s-params；本轮任务 16-playtest-round-50s。

入口：build/index.html；产物清单：build/index.html、build/main.js。

SHA-256：build/index.html = 71715156ee0b6fbae5dd07d1b0d93a64c4c55cf2eedd124af6fceb789f9cc98e。

SHA-256：build/main.js = cb1bfd3f021abed96b5becbe9f42140a0c1ed41727581f1e498746134c812933。

版本关系：与任务 14 results/2026-09-09.md 登记哈希一致；本轮是 PT-01 修复后的新版本复测，2026-09-08 的 60 秒旧试玩记录结论未挪用。

### 场景与执行
入口引用解析：读取 build/index.html 并解析 script src；预期引用 main.js 且目标存在；实际 refs=main.js、missing=0；证据为 Node DOM 桩输出。

初始化：加载 build/main.js；预期 HUD 显示 50、aria=50、进度 100%、未 urgent、结算隐藏；实际 tide=50 aria=50 width=100% urgent=false resultHidden=true。

倒计时递减：推进 1 个 50ms RAF 帧；预期状态递减；实际 tide=50 aria=50 width=99.9%，证明进度已递减。

PT-01 回归：连续 50ms 帧推进到名义 10 秒边界；预期 urgent 同帧生效且 HUD 显示 10；实际 tide=10 aria=10 urgentStatus=true urgentHud=true status=即将涨潮！。

0 秒结算：继续推进到名义 0 秒；预期只结算不判负；实际 tide=0 aria=0 result=潮汐结算：拾取总数 0 枚，文案不含“失败”。

结算幂等：结算后继续 5 个 50ms 帧；预期状态不变；实际 0 秒 HUD 与结算文案保持不变，脚本断言通过。

语法检查：node --check build/main.js；实际退出码 0。

静态服务入口取回：python3 http.server 绑定 127.0.0.1:8765；实际退出码 1，PermissionError: [Errno 1] Operation not permitted；按要求未重试，未计为通过。

### 观察与缺陷
PT-01 复测结论：通过；名义 10 秒边界 HUD 显示 10 且 urgent 同帧生效。

自动场景未发现需交回制作修复的缺陷。

边界核对：mgs_write 写入 build/main.js 内容“// 越界”被拒；decision=deny，rule_stage=task_grant，reason=path not granted to task 16-playtest-round-50s: build/main.js。

### 人工试玩任务
11-playable-build 手感与 HUD 可读性：未反馈(待人工)。要求开发者用现代浏览器打开 build/index.html，完整游玩至少 2 轮 50 秒，回传方向键手感、HUD 可读性、最后 10 秒提示、0 秒冻结观察，包含时间、来源、轮次数和问题描述/截图。

08-gull-playtest 海鸥试玩等待项：未反馈(待人工)。仍按既有 08-gull-playtest/11-playable-build 要求回传海鸥干扰强度、等待项和需要修改点；本轮不冒充人工反馈。

### 尚未执行与覆盖限制
真实浏览器 GUI、手感、审美和 HUD 人眼可读性未执行；Node DOM 桩不替代人工体验判断。

静态服务 HTTP 取回未完成，原因是会话沙箱拒绝绑定端口。

任务 14 产物未集成 05-gull-swoop 的海鸥、掉落追回与 RECOVER_WINDOW_BASE_SECONDS 正式代码路径，该项待后续任务验证。

### 交接
试玩记录已写入 docs/mygamestudio/evidence/2026-09-09-playtest-14-round-50s.md。

记录最终 SHA-256：2db0f43230cd22fdbb0a6a18bcbfb8e831b49f921e92ba3ea1e8db805d5a5164。

统筹同步事项：自动 PT-01 复测通过；静态服务取回因端口权限未完成；人工试玩仍为未反馈(待人工)；试玩记录不等于验收通过。
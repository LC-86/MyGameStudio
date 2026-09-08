# 11-playable-build：独立审查

任务：11-playable-build。审查实例与专业：i-45ecdabdb7f1，制作实现（review，未参与成果制作）。审查日期：2026-09-08。

## 审查范围与待审版本

以工作区当前实际 build/ 两产物为准，直接逐文件读取。
- build/index.html：SHA-256 8e562a6a6e067de5057703cf4eaa24570e7f23daf331ca46d9a4e7497aa85ba1。
- build/main.js：SHA-256 35ed50601ad540a878afbf62c922392455abd460ee460dcfc06eee3b8b87a5e8。
- 对应当前源快照：src/index.html 25df49727487236cc57f287488538abeddcefad3ad804fafd14ee5add6c2a9a2；src/main.js 953714657c1f3cbd000557a7f522c3e230914808973e0686c22a1b44a5a9d829；src/tide-extra.js be2ae08303b25e0c4240a7dedb57c21d60ff28697ed869408b2083223a8bb489。
- git 辅助信息仅显示 src 的已暂存/未暂存/新建变化；build 当前未列为改动。审查范围仍以实际文件清单和字节为准。

## 依据与实际检查

- TECH_DESIGN v3 第 43-50、60-72 行（字节一致、SHA 对应、仅入口引用资源、引用可解析、静态服务和无头冒烟）。
- GAME_DESIGN v3；CONFIG v4；11 任务记录完成标准；统一接口 show/deps。
- 作者结果 docs/mygamestudio/work/11-playable-build/results/2026-09-08.md 只作线索。其第 9-10 行哈希准确描述 build 和旧 src，但当前 src 哈希已变化，故第 18、32 行旧版本“三方一致/检查通过”不能证明当前待审版本对应。
- 当前直接 `cmp -s src/index.html build/index.html` 退出 1；`cmp -s src/main.js build/main.js` 退出 1。
- 当前 build 引用解析：index.html 仅引用 main.js，文件存在。
- `node --check build/main.js` 退出 0。
- /tmp DOM 桩运行 build/main.js：初始化 60/100%/aria=60/6 shells；约 10 秒 urgent=true/“即将涨潮！”；0 秒 settled、0%、结算总数 0；结算后 player/count/shells 冻结。
- 静态服务命令 `python3 -m http.server 8765 --bind 127.0.0.1 --directory <build>` 退出 1，原始异常末行为 `PermissionError: [Errno 1] Operation not permitted`；未取得 HTTP 200/内容一致证据。

## 专业标准轴

结论：需修改。
- 通过项：build 仅有 index.html/main.js；产物内部入口引用可解析；没有把当前未引用 assets 放入；产物脚本语法及无头行为冒烟通过。
- 明确违背：两个产物均不与当前同名源文件字节一致（cmp 均退出 1，SHA 均不同），违反 TECH_DESIGN v3 第 46、48、65、72 行。
- 明确违背：当前 src/index.html 新引用 tide-extra.js，但 build/index.html 没有该引用，构建不是当前入口的完整组装式导出；当前源版本对应关系失效。
- 未能检查：会话沙箱禁止绑定端口，约定的静态服务 HTTP 200 和取回字节一致未完成。

## 需求符合性轴

结论：需修改。
- 当前 build 自身可由 DOM 桩初始化、倒计时递减、进入 urgent、0 秒结算并冻结；结算文案可观察。
- 11 完成标准要求“与当前 src 逐字节一致”和当前版本 SHA 对照；实际版本漂移导致交付为旧轮构建，不符合当前工程版本构建要求。
- 入口 HTTP 可达性未验证，完成标准中的真实静态服务取回项仍未完成。
- 真实浏览器离线运行、显示可读性和试玩手感未人工确认。

## 问题清单

1. 对象/位置：11，build/index.html ↔ src/index.html。证据：SHA 分别 8e562a… 与 25df49…，cmp 退出 1；源入口另含 tide-extra.js 引用。影响：产物入口不是当前源入口的字节一致副本，且遗漏当前入口依赖。分类：明确规则违背。
2. 对象/位置：11，build/main.js ↔ src/main.js。证据：SHA 分别 35ed50… 与 953714…，cmp 退出 1；阈值分别 10 与 7。影响：产物行为对应旧源码，版本对应清单失效。分类：明确规则违背。
3. 对象/位置：11，静态服务入口。证据：http.server 退出 1，PermissionError [Errno 1] Operation not permitted。影响：无法确认 HTTP 200 与取回内容一致。分类：未能检查。
4. 对象/位置：11，真实浏览器/试玩。证据：本审查未启动 GUI，且无开发者实际反馈。影响：无法判定离线浏览器兼容、HUD 可读性及手感。分类：未能检查。

## 未覆盖、复核与交接

- 未覆盖：静态 HTTP 取回、真实浏览器直接打开、人工可读性和手感；分别需允许绑定端口的环境及开发者浏览器试玩。
- 构建对应的工程本身仍缺持续刷新、连击、海鸥、掉落追回；当前构建不代表最终产品形态。
- 修复交回构建执行流程：先由源码责任流程修复/确认 02 当前版本，再按当前入口引用完整重建 build，登记新源↔产物 SHA，并重跑引用、无头和静态服务检查。
- 人工验收保持待验收；统筹需同步“当前 build 已陈旧”。本报告生成不等于验收通过。
- 边界核对（写入完成后各一次）：直接 shell 重定向写 evidence/probe.txt，退出码 1，原始输出 `zsh:1: operation not permitted: /Users/cuilei/MyOS/01_Projects/plugins/MyGameStudio/.tmp/accept-13/projects/tide-pool/docs/mygamestudio/evidence/probe.txt`；越界 mgs_write 写 src/main.js 内容“// 越界”，原始返回 `decision=deny`、`rule_stage=task_grant`、`reason=path not granted to task 13-review-code-deliverables: src/main.js`。两目标均未被写入。
- 流程偏差录：初次两份 mgs_write 已获 granted 后才补做 mgs_scope；scope 随后确认绑定身份与 allowed=[docs/mygamestudio/evidence/**]。这是未遵守“写前先 scope”的程序偏差，虽未造成越界写入，仍如实保留。

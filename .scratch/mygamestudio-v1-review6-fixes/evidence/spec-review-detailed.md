## Spec 独立复核

**3 项 P2；未发现扩范围行为。SP-14 原反例修复成立，但旧布局误删使完整要求未闭合；SP-15 原 userinfo 修复成立，但实际连接目标与失败归属仍有两个既有边界。SP-16 动态回归由主审核验。**

### [P2] 新布局完成恢复时误删碰撞请求的旧布局登记，随后重复发布

- **代码**：`plugin/records/mgs_github.py:784-789`。`_load_pending_index` 优先核验 A 的新登记后，循环无条件 unlink 新旧两个地址；旧地址可能是 B 的完整、健康登记。
- **违反规格**：`.scratch/mygamestudio-v1-review5-fixes/issues/01-ledger-coexistence.md:47` 明确“corrupt/无法归属的登记仍保守保留(不误删他人登记语义不变)”；同票第 21–22 行要求共存互不干扰、SP-11 零回退；review4 票 `01-pending-index-identity-and-disclosure.md:15,22` 要求不误删他人登记及有缓存全链路不回退。
- **复现**：真实旧代码 `git show 1eef7d8:plugin/records/mgs_github.py` 先调用 B partial，生成健康旧登记；升级后经 MCP→GateService→FakeTransport 调用 A partial（读前 GET 超时），再让 A 补齐；A 完成删除 B 旧登记。B 重试读前超时后重新 POST，实测 **3 POST、B 评论 2 条**。全程顺序调用，无人工登记改写、无并发、无真实网络。
- **因果对照**：仅在探针进程将清除逻辑改为逐文件独立核验，变为 **2 POST、B 1 条**；去掉该内存变异后再次 **3/2**。源码副本未改动。
- **证据**：`spec-agent/mixed-layout-probe.py`，`mixed-layout-run-1/result.json`、`mixed-layout-guard-control/result.json`、`mixed-layout-run-2/result.json`（均相对本报告目录下 `spec-agent/`）。

### 额外边界与限制

`pending-boundary-probes.py`：20 次同短摘要目录／不同全哈希并发写及 Unicode NFC/NFD、TAB、NEWLINE 身份和长正文检查共 **26/26**。迁移写前失败、删除旧文件前失败均保持 1 POST，并能清掉同身份双登记。半写后 OSError 会让截断的新登记遮蔽健康旧登记，后续为 corrupt／人工核对，不再自动迁移；已披露且不重发，列观察项，不另立阻塞缺陷。证据 `spec-agent/pending-boundary-run/result.json`。

未核验同请求并发发布、跨进程崩溃/断电或真实远端；不能把上述有限探针写成并发/迁移全面安全。结论：存在新确认的误删与重复发布路径，**不具备 v1 收口条件**。


### curl 补充复核：两个独立 P2

**[P2] 连接改写参数被忽略，其他地址的失败冒充替身直连被拒。** `acceptance/18-complete-package-acceptance/run.sh:271-273` 对已列入白名单的 `--proxy/--resolve` 仅跳过参数值；第 313 行继续只核 URL hostname。实跑 URL 指向 `127.0.0.1`，代理/解析覆盖连接至 `127.0.0.2` 失败，判据仍 OK；resolve 的 `--verbose` 明确记录 `Trying 127.0.0.2:59474...`。违反 review4 票 `02-anchor-context-and-execution-binding.md:16` 的“实际连接目标参数”与“保守拒绝不能证明执行的形态”，以及 review5 票02:47 的实际连接目标口径。

**[P2] 多 URL 的整体失败可冒充已成功 URL 被拒。** 同文件第 316–320 行，`any(host)` 与整次命令的退出码/输出相组合。真实本地 HTTP server 记录 `.1` 请求成功并返回 `TARGET_SUCCESS`，随后 `.2` URL 失败；锚定仍 OK。违反 review2 票 `04-anchor-checks-to-real-tool-returns.md:17` 的“检查必须反映实际行为”及 review4 票02:16 的目标绑定。

两项分列理由有因果实证：仅拒绝覆盖参数，proxy/resolve 变 MISSING，但多 URL 仍 OK；仅要求单 URL，恰好相反；合并两项守卫后全部 MISSING，两真对照仍 OK；还原提取函数又全 OK。前者为连接身份，后者为结果归属；proxy/resolve 是同一项的子反例。`1eef7d8` 旧函数三例也 OK，均为本轮新确认的**既有边界**，不称本批引入，不反推留存证据无效。

独立证据：`spec-agent/curl-boundaries-6.py`、`curl-boundaries-6.json`、`curl-causal-controls.json`。11 例实跑，3 假绿、8 对照符合预期；全部 loopback，进程/临时服务器均由本探针启动并回收，只执行提取函数。

## Spec 独立复核

**3 项 P2；0 项扩范围。SP-14/15 原始反例的修复成立，但新旧登记兼容与连接证据绑定的完整要求仍未闭合，不具备 v1 收口条件。SP-16 动态回归由主审核验。**

以下票据均相对 `.scratch/`，代码行均为当前 HEAD。

- **SP-17 [P2] 混合布局误删他人登记。** `plugin/records/mgs_github.py:784-789` 核验 A 新登记后无条件删除两布局，删掉碰撞 B 的健康旧登记。违反 `mygamestudio-v1-review5-fixes/issues/01-ledger-coexistence.md:21-22,47`（共存、不误删、零回退）及 review4 票01:15,22。真实 `1eef7d8` 旧实现先创建 B partial，升级后经 MCP→GateService→FakeTransport 执行 A partial→A 补齐→B 读前超时重试：**3 POST、B 2 评论**。无人工登记编辑、无并发。仅探针内存变异为逐文件核验→**2/1**；恢复原逻辑→**3/2**。证据 `spec-agent/mixed-layout-{run-1,guard-control,run-2}/result.json`。
- **SP-18 [P2] 改写连接地址的参数被忽略。** `acceptance/18-complete-package-acceptance/run.sh:271-273` 吞掉白名单 `--proxy/--resolve` 的值，第313行仍只核 URL hostname。实连 `.2` 失败冒充 `.1` 直连被拒，均 **OK 假绿**；resolve verbose 明确 `Trying 127.0.0.2:59474...`。违反 `mygamestudio-v1-review4-fixes/issues/02-anchor-context-and-execution-binding.md:16`（实际目标、无法证明时保守拒绝）及 review5 票02:47。
- **SP-19 [P2] 整次多 URL 命令失败错归已成功目标。** 同文件 `316-320` 把 `any(host)` 与进程整体失败/输出组合。本地 `.1` server 确认请求成功、返回 `TARGET_SUCCESS`，随后 `.2` 失败，仍 **OK 假绿**。违反 `mygamestudio-v1-review2-fixes/issues/04-anchor-checks-to-real-tool-returns.md:17`（检查反映实际行为）及 review4 票02:16。

curl 两项应分列：仅拒绝覆盖参数，只修 SP-18；仅限制单 URL，只修 SP-19；二者合用全部 MISSING，两真对照仍 OK；恢复又全 OK。`1eef7d8` 三例也 OK，属于本轮新确认的既有边界，不称本批引入、不否定留存证据。独立证据：`spec-agent/curl-boundaries-6.json`（11例，3假绿/8符合预期）、`curl-causal-controls.json`。

**边界**：pending 同目录不同全哈希并发20次、Unicode NFC/NFD/TAB/NEWLINE身份、10万字符正文，共26/26。迁移写前/删旧前 OSError 安全恢复；半写后 OSError 使新损坏登记遮蔽健康旧登记，披露 corrupt、保守不重发，但不再自动迁移，列观察项。未核验同请求并发、跨进程崩溃/断电、真实远端或模型轮。所有写入在 `/tmp`，curl 仅 loopback，只执行提取函数。详情及原证据索引见 `spec-agent/spec-review-detailed.md`、`pending-boundary-run/result.json`。

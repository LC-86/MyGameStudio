# 08: 让工具拒绝判据直接服务运行与测试

**What to build:** 实际验收脚本与离线测试经同一 interface 判断工具调用是否确实因预期规则拒绝了指定动作和资源。

**Blocked by:** 07 完成任务读取的入口与交付兼容验收

**Status:** ready-for-agent

**Progress:** 已完成（2026-09-12 收口；执行记录见 Comments 与执行日志）

**Spec:** [MyGameStudio 全插件分阶段架构重构 v1](../spec.md) · User Stories 28, 29, 30, 32, 33, 34

**Verification mapping:** 按本票所属阶段的验收集合

- [x] 建立可从运行脚本和 Python 测试调用的判据 seam，并完整迁入工具拒绝场景；返回保持现有 OK/MISSING 含义。
- [x] 通过真实事件类型、调用与返回两侧、动作、拒绝阶段和资源身份核验，示例文本、allow 返回及其他资源拒绝不能冒充目标证据。
- [x] 路径空格、绝对/相对语境、规范等价与评论派生段等已有正反例和保守取舍保留。
- [x] 运行脚本实际接入共享判据，测试不再正则截取该 Shell 函数；保留最小真实 Shell 传参与返回对照。
- [x] 未迁移的 curl 判据继续工作；工具拒绝历史案例与留存回放逐项兼容。

**依赖理由：** 依赖 07 的第一阶段兼容验收门；按已确认顺序，先完成读取再调整其后续验证基础。

## 执行与验证约定

本票已正式发布；实施按对应任务授权执行。沿现有 interface 验证本票行为；保持外部用法、持久化格式、权限与恢复语义，只有明确列出的 R1 属行为修正。每票在新的执行上下文中按实际前置成果接手；产品内容变化时同步相关包与来源检查，记录净行数、必要操作量和未验证限制。

同一共享文件只由一名执行者修改。测试和独立规范/规格评审针对本票实际版本；基线不可被历史结果替代。提交、推送、标签、真实远端写入、日常安装和发布分别沿明确授权执行。

## Comments

用户已确认 26 票拆分及其依赖安排；本票按确认稿发布，未启动实施。

### 执行记录（2026-09-12，执行代理）

**做了什么**

- 新增共享判据 module `acceptance/18-complete-package-acceptance/evidence_judgement.py`（171 行，生产 200–400 区间内）：`judge_mcp_deny(events, tool, stages, target_arg, action)` 接收实际事件（JSONL 路径或已构造事件容器两种输入形态），核对事件类型（仅 `mcpToolCall` 且 tool 匹配）、返回侧 `decision=deny`/`rule_stage`/`op` 动作段、调用与返回两侧资源身份、预期动作；返回 `OK`/`MISSING`。原 `mcp_deny_anchor` 判据实现整体迁入，SP-6/8/9/12/13/15/16 口径逐字保留（绝对/相对语境、normpath 等价类、首尾空格属身份、调用/返回分侧核验、append-result `/comments` 至多一段）。
- 新增 Shell 适配层 `acceptance/18-complete-package-acceptance/evidence_adapter.sh`（11 行）：定义 `mcp_deny_anchor` 转发到 `python3 -B evidence_judgement.py mcp-deny "$@"`。
- `acceptance/18-complete-package-acceptance/run.sh`：删除内联 heredoc 判据实现（99–194 行），改为 `. "$ACC_DIR/evidence_adapter.sh"`；现场调用链（P1/P2/G1/R1/R1b 共 10 处）逐字不变。`curl_direct_denied`（SP-13~30）按票 09 归属继续留在 run.sh 未动。
- `tests/test_plugin_package.py::test_accept18_probe_checks_anchored_to_events`：不再正则截取 `mcp_deny_anchor` 源码，改为加载 module 经 `judge_mcp_deny` 直接回放；新增 `shell_anchor` 最小现场对照（source 适配层后调用真实 Shell 入口）。

**五条验收逐条自查与证据**

1. seam 可从运行脚本与 Python 测试调用、完整迁入、返回保持：`run.sh` 经适配层、测试经 `judge_mcp_deny`，同一 module；26 项 `anchor(...)` 直接断言 + run.sh 10 处现场接线。返回仅 `OK`/`MISSING`（`RESULT_OK/RESULT_MISSING`）。
2. 真实事件类型/双侧/动作/阶段/资源核验，示例文本与 allow 返回不冒充：夹具 A（`agentMessage` 示例文本）MISSING、夹具 C（`decision=allow`）MISSING、夹具 B（真实 deny/path）OK；动作错配（append-result deny 对 update 预期）MISSING、其自身 append-result OK；其他资源（`.bak` 后缀、`/tmp/alternate-root/...`、重复段、大小写、前导/尾随空格）均 MISSING，其自身目标 OK。
3. 空格/绝对相对/规范等价/评论派生段正反例与保守取舍保留：尾斜杠、`./` 段、重复斜杠 OK；`/tmp/tmp/...`、大小写变体、首尾空格 MISSING；绝对期望不接受任意前缀；调用侧 `01-harbor-timer/comments` 与双 comments 不满足身份，`01-harbor-timer/comments` 自身语境 OK。
4. 运行脚本实际接入共享判据、测试不再正则截取该 Shell 函数、保留最小真实 Shell 对照：run.sh 以 source 接入（断言 `. "$ACC_DIR/evidence_adapter.sh"` 在位、内联实现标记 `called = str(args.get("path")` 退场）；测试新增 `shell_anchor` 经真实适配层返回 SHELL:OK/MISSING；mcp 源码正则截取已清零。
5. curl 判据继续工作、历史案例与留存回放逐项兼容：`curl_direct_denied` 未改，其全部 CURL 用例仍绿；工具拒绝经 A/B 对照（旧内联实现 vs 新 module）——留存证据 9 例 + 合成离线回放 21 例，`DIFFS: 0`（离线，不启动真实模型/远端）。

**验证命令与真实结果**

- `python3 -B tests/test_plugin_package.py` → `OK: 最小插件包静态完整性检查全部通过`（exit 0）
- 其余四套 `python3 -B tests/test_{runtime_gate,runtime_boundaries,records_backend,github_backend}.py` → 全 `OK`（各 exit 0）
- `sh .scratch/mygamestudio-architecture-refactor/evidence/baseline/run_baseline.sh` → 五套 `PASS`、`all_existing_checks_green=True`；跑完 `git checkout -- .scratch/.../evidence/baseline/` 恢复冻结产物
- `bash -n run.sh` / `bash -n evidence_adapter.sh` / AST 解析 module → 语法 OK
- A/B 离线对照（旧 `mcp_deny_anchor` vs `evidence_judgement.py mcp-deny`）：留存证据 9/9 一致、合成夹具 21/21 一致、`DIFFS: 0`
- `./dist/verify-reproducible.sh` → 全部 PASS，交付包 SHA-256 `af91503f2956587e9024730ac82ccc124b8173cc1eec669c09aa72eb59fd789d`（生产区零改动，无需重建；仅确认与当前代码一致）

**净行数（物理行，含空行注释；生产区零改动）**

- `acceptance/18-complete-package-acceptance/run.sh`：1323 → 1232（−91）
- `acceptance/18-complete-package-acceptance/evidence_judgement.py`：新增 +171
- `acceptance/18-complete-package-acceptance/evidence_adapter.sh`：新增 +11
- acceptance 净变化：**+91**
- `tests/test_plugin_package.py`：4049 → 4090（**+41**）
- `plugin/`（生产 Python）：**0**

**未验证限制**

- 真实模型轮与真实远端写入未执行（本票全程离线回放，零网络/零凭据），属全任务一贯限制。
- `curl_direct_denied` 仍留在 run.sh 且测试仍对其正则取源码做留存回放——属票 09 范围，本票未迁移，不影响本票五条验收。
- `test_plugin_package.py` 仍为大文件（4090 行），按 spec 31「旧大文件随所属阶段处理」留待票 10 按行为主题拆分。
- 现场接入对照为离线 source 适配层的最小 Shell 对照，不含真实 turn；真实宿主调用链不因离线通过而视为已验收。

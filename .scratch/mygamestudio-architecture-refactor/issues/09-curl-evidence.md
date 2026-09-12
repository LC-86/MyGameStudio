# 09: 让直连失败判据通过同一事件入口验证

**What to build:** 验收脚本和离线回放一致判断真实 curl 执行的目标与连接失败，保留现有解析范围和已接受限制。

**Blocked by:** 08 让工具拒绝判据直接服务运行与测试

**Status:** ready-for-agent

**Progress:** 已完成（2026-09-12 收口；执行记录见 Comments 与执行日志）

**Spec:** [MyGameStudio 全插件分阶段架构重构 v1](../spec.md) · User Stories 28, 29, 30, 32, 33, 34

**Verification mapping:** 按本票所属阶段的验收集合

- [x] 把现有 curl 判据接入 08 建立的证据判定入口，实际脚本沿该入口取得兼容结果。
- [x] 保留 shell 包装解析、目标主机身份、参数消费、诊断归属及单请求约束的现有语义；不扩展完整 shell/curl 解释能力。
- [x] URL 与上传 glob、短旗标、重试、重定向、代理及响应伪装等已有反例和真对照保持；已接受的保守拒绝与残余限制明确保留。
- [x] 相关用例不再抽取源码或为每例拼接大段 Shell；事件回放不启动网络或模型。
- [x] 工具拒绝与直连失败判据的实际脚本接入和留存回放通过，历史案例身份能定位到新测试。

**依赖理由：** 依赖 08 的证据判定 seam 和脚本接入方式。

## 执行与验证约定

本票已正式发布；实施按对应任务授权执行。沿现有 interface 验证本票行为；保持外部用法、持久化格式、权限与恢复语义，只有明确列出的 R1 属行为修正。每票在新的执行上下文中按实际前置成果接手；产品内容变化时同步相关包与来源检查，记录净行数、必要操作量和未验证限制。

同一共享文件只由一名执行者修改。测试和独立规范/规格评审针对本票实际版本；基线不可被历史结果替代。提交、推送、标签、真实远端写入、日常安装和发布分别沿明确授权执行。

## Comments

用户已确认 26 票拆分及其依赖安排；本票按确认稿发布，未启动实施。

### 执行记录（2026-09-12，执行代理）

**做了什么**

- `acceptance/18-complete-package-acceptance/evidence_judgement.py`（171→371 行）：新增 `judge_curl_direct_denied(events)`，把原 `run.sh curl_direct_denied` heredoc 判据整体迁入，逐字保留口径——`executed_tokens`（剥 shell 包装，SP-13）、`url_targets`（旗标白名单/短旗标 SP-22/24 消费/glob SP-29/30 拒绝）、单 URL 与 urlparse 主机关联（SP-15/19）、curl 连接诊断行绑定替身主机（SP-23/25/26）、`connect_diag`/`STANDBY_HOST`/`SHELLS`/四张旗标表原样搬运。`judge_mcp_deny`（票 08）语义与 `OK`/`MISSING` 返回约定不变；`main` 新增 `curl-direct-deny <事件JSONL>` 子命令。事件输入仍经 `_iter_items`（JSONL 路径逐行解析或已构造事件容器，离线回放）。
- `acceptance/18-complete-package-acceptance/evidence_adapter.sh`（11→16 行）：新增 `curl_direct_denied` 包装转发到同一 module 的 `curl-direct-deny`；与 `mcp_deny_anchor` 共用同一 `MGS_EVIDENCE_JUDGE` seam。
- `acceptance/18-complete-package-acceptance/run.sh`（1232→1007 行）：删除内联 `curl_direct_denied` heredoc 实现（原 105–329 行，225 行），改由 `. "$ACC_DIR/evidence_adapter.sh"` 提供；现场调用链 L807 `test "$(curl_direct_denied "$EVIDENCE_DIR/g1-events.jsonl")" = "OK"` 逐字不变。
- `tests/test_plugin_package.py::test_accept18_probe_checks_anchored_to_events`：删除对 `curl_direct_denied() {...}` 的正则源码截取与每例 `bash -c` 拼接（原 `curl_call` 取源码 + `R=$(curl_direct_denied ...)`），`curl_call` 改为直接 `judge.judge_curl_direct_denied(events)`；新增 `shell_curl` 最小现场对照（source 适配层后调用真实 Shell 入口，2 例）；接线断言新增「run.sh 不再内联 curl 判据（`CURL_VALUE_SHORT`/`def url_targets` 退场）」。79 个 curl 夹具、全部 CURL 断言与留存证据回放均不改期望值。

**五条验收逐条自查与证据**

1. curl 判据接入 08 的判定入口、实际脚本沿入口取得兼容结果：`run.sh` L807 仍调 `curl_direct_denied`，该函数由 `evidence_adapter.sh` 提供并转发到 `evidence_judgement.py curl-direct-deny`；测试经 `judge.judge_curl_direct_denied` 调同一 module。返 `OK`/`MISSING`（`RESULT_OK`/`RESULT_MISSING`）。留存 `evidence/g1-events.jsonl` 经新旧实现均为 `OK`。
2. shell 包装解析、目标主机身份、参数消费、诊断归属、单请求约束语义保留：`executed_tokens`/`url_targets`/`host_is_standby`/`diagnostic_binds_standby`/`len(urls)!=1` 逐字迁移，无新增解释能力。A/B 差分（旧 run.sh 函数 vs 新 module）79/79 夹具结论一致 `DIFFS: 0`。
3. 反例与真对照保持、已接受限制保留：SP-13（fixture M/N/O）、SP-15（Y/Z userinfo、AA 真直连、AB IPv6）、SP-18/19（AC/AD/AE 假例 + AF/AG 对照）、SP-20~23（AH~AQ 假例/防护变体/ambient + AR~AW 对照）、SP-24~26（AX~BN）、SP-27~29（BO~CJ，含 `--retry` 翻转 MISSING、`-g/-J/-Z` 无值、URL glob）、SP-30（CK~CT 上传值 glob）逐例期望不变；已受限制（完整诊断行正文残余 SP-25、ambient 事件不记录环境）留档。
4. 不再抽取源码 / 不拼大段 Shell / 离线回放：源码正则截取 `re.search(r"^curl_direct_denied\(\) \{...")` 已删除；`curl_call` 直接消费已构造/文件事件（零网络、零模型）；现场对照仅 `shell_curl` 两例最小 Shell。回放不启动网络或模型。
5. 两类判据实际接入与留存回放通过、历史案例可定位：`shell_anchor`（票 08 mcp）与 `shell_curl`（票 09 curl）现场对照各 2 例经真实适配层；留存证据 r1/g1/p1/p2/r1b 回放仍 PASS；历史案例逐项映射见下。

**历史案例身份 → 新测试映射（不删案例）**

- `evidence/g1-events.jsonl` 真直连失败（留存）→ `curl_call(g1_real) == CURL:OK`（节 2）。
- SP-6 示例文本/allow 冒充（fixture D/I）→ `curl_call(g1_fixture_d/i) == CURL:MISSING`。
- SP-13 shell 包装与词串冒充（M 脚本参数、N -H 头值、O `--version`；P/Q 裸/zsh 真对照）→ `curl_call(...)` 对应断言。
- SP-15 userinfo 冒充与 host 核验（Y/Z、AB；AA 真对照）→ 对应 `curl_call(...)`。
- SP-18/19 改连接语义参数与多 URL（AC/AD/AE；AF/AG 对照）→ 对应 `curl_call(...)`。
- SP-20~23 短旗标/重定向/粘连值/响应阶段超时（AH~AQ；AR~AW 对照）→ 对应 `curl_call(...)`。
- SP-24~26 顺序短旗标/诊断行/主机相等（AX~BN）→ 对应 `curl_call(...)`。
- SP-27~29 无值短旗标/`--retry`/URL glob（BO~CJ）→ 对应 `curl_call(...)`。
- SP-30 上传值 glob（CK~CT）→ 对应 `curl_call(...)`。

**验证命令与真实结果**

- `python3 -B tests/test_plugin_package.py` → `OK: 最小插件包静态完整性检查全部通过`（exit 0）
- 其余四套 `python3 -B tests/test_{runtime_gate,runtime_boundaries,records_backend,github_backend}.py` → 全 `OK`（各 exit 0）
- `sh .scratch/mygamestudio-architecture-refactor/evidence/baseline/run_baseline.sh` → 五套 `PASS`、`all_existing_checks_green=True`（rc 0）；跑完 `git checkout -- .scratch/.../evidence/baseline/` 恢复冻结产物
- `bash -n run.sh` / `bash -n evidence_adapter.sh` / `py_compile` module + test → 语法 OK
- `python3 -B evidence_judgement.py curl-direct-deny evidence/g1-events.jsonl` → `OK`；`mcp-deny ...` 仍返回 `OK`（08 行为不变）
- A/B 离线差分（旧 run.sh `curl_direct_denied` vs 新 `judge_curl_direct_denied`）：79/79 夹具一致、`DIFFS: 0`（合成夹具字符串，不执行 curl、零网络）
- `./dist/verify-reproducible.sh` → 全部 PASS，交付包 SHA-256 `af91503f2956587e9024730ac82ccc124b8173cc1eec669c09aa72eb59fd789d`（生产区零改动，无需重建）

**净行数（物理行，含空行注释；生产区零改动）**

- `acceptance/18-complete-package-acceptance/run.sh`：1232 → 1007（−225）
- `acceptance/18-complete-package-acceptance/evidence_judgement.py`：171 → 371（**+200**，371 行处于 200–400 区间）
- `acceptance/18-complete-package-acceptance/evidence_adapter.sh`：11 → 16（+5）
- acceptance 净变化：**−20**
- `tests/test_plugin_package.py`：4090 → 4100（**+10**）
- `plugin/`（生产 Python）：**0**

**未验证限制**

- 真实模型轮与真实远端写入未执行（本票全程离线回放，零网络/零凭据），属全任务一贯限制。
- 迁移函数 `url_targets` 64 行、`judge_curl_direct_denied` 50 行，为原判据逐字搬运（>60 但 <80，非强制复查）；未借机重写以免改变口径。
- 判据残余边界（完整诊断行正文 SP-25、ambient 环境不记录）与原实现完全一致，未新增也未消除。
- 现场接入对照为离线 source 适配层的最小 Shell 对照，不含真实 turn；真实宿主调用链不因离线通过而视为已验收。
- `test_plugin_package.py` 仍为大文件（4100 行），按 spec 31「旧大文件随所属阶段处理」留待票 10 按行为主题拆分。

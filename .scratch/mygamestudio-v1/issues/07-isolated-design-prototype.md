# 07：用隔离原型验证一个设计问题

**What to build:** Game-Prototype 针对明确的设计不确定性制作隔离原型，提供真实观察与结论；复用编码或素材能力时仍受原型范围约束。

**Blocked by:** [06：把功能想法形成当前可执行规格](06-idea-to-current-spec.md)

**Status:** ready-for-agent

## 验收标准

- [x] 输入明确要回答的问题、原型范围、适用要求、可用方法和输出位置；选择足以验证问题的小实现，不自动扩大到正式产品制作。
- [x] 实际产出可运行或可观察的原型，提供启动或查看方式、已执行操作、结果和证据。
- [x] 验证方案设计可写获准原型区，使用编码或资源工具也不能写正式工程；新增执行方式有实际边界验证。
- [x] 区分原型观察、设计判断、尚未验证及需要人的体验反馈；需要人判断时只引用真实反馈，未收到则保留待验收。
- [x] 原型、结论和基线引用可交给 Game-Spec 与制作实现；复用或重写由正式集成条件决定，不自动把原型作为已完成正式功能。

## 实施依据

开始时读取[实施范围与验收约定](../spec.md)，再按本票分支读取[设计技能合同](../../mygamestudio-framework/contracts/design.md)、[运行保障合同](../../mygamestudio-framework/contracts/runtime.md)。具体工程位置在实施时从当前项目读取。


## Comments

### 2026-09-08 — 实施完成(实施代理)

**结论:本票完成。** 五条验收标准全部通过;终验 `acceptance/07-isolated-design-prototype/run.sh` 单次贯通运行 **57 PASS / 0 FAIL**(12:48:18→13:03:49,证据时间戳严格有序,2 个真实模型 turn,一次通过无返工)。

#### 实际结果

- 插件包升至 `mygamestudio` 0.7.0(**不新增入口**,把票 02 的 game-prototype 最小入口升级为完整原型工作流):
  - **输入四要素纪律**:问题/当前约定/原型范围/适用要求/可用方法/输出位置缺一即如实报告无法执行,不自行补问题、不伪造;选择**最小可检验实现**,明确"不自动扩大到正式产品制作"。
  - **执行与观察**:原型在会话工作区草拟并实际运行(固定种子等可复现手段优先),已执行操作与真实输出记入验证记录与报告;没有实际运行的部分不得写成已观察。
  - **结论四类区分**:原型观察/设计判断(标注助手判断)/尚未验证/需要人的体验反馈(只引用真实反馈,未收到保留待验收)分别表达。
  - **交接**:原型、结论与基线引用按未参与者可读标准交给 Game-Spec 与 Game-Implement;复用或重写由正式集成条件决定;原型可运行不等于正式产品已经实现。
  - **边界**:复用编码或素材能力不改变用途;任务授权与 `mgs_scope` 不一致以 scope 为准并如实报告差异(用途比角色更窄)。
- 包内 `internal/contracts/design.md` 的"包内说明"更新为 Game-Prototype 完整入口已实现;provenance manifest/fingerprints 同步。
- **起始状态夹具** `acceptance/07-isolated-design-prototype/fixtures/`(不改 `samples/tide-pool` 本体,票 06 验收保持可复现,静态测试双向核对):票 06 成果(GAME_DESIGN v2、海鸥决定与研究记录、历史决定补记)+ 一次常规统筹同步轮成果(PROJECT v2、CONFIG v2 补原型区、prototypes/README)+ 开发者原型验证请求(拾回窗口 70% 预期 + 预警体验页)。
- 确定性检查 `tests/test_plugin_package.py` 扩展(TDD 红 23 项→绿):game-prototype 技能纪律 20 概念 + 夹具结构与关键事实(v2 基线/两份采纳依据/预警未决/范围已同步/样例本体仍为 v1)。
- 验收资产 `acceptance/07-isolated-design-prototype/`:appserver_client.py(06 客户端改名)、run.sh、runbook.md、fixtures/。

#### 运行的验收及证据(`evidence/`)

环境(`environment.txt`):codex-cli **0.151.0**,macOS 26.5.1 arm64;隔离 HOME/CODEX_HOME 于 /tmp(auth.json 符号链接);受保护区在仓库 `.tmp/accept-07/`。安装副本与仓库逐字节一致;注册面仍恰 7 个插件技能。**2 个真实模型 turn:**

- **W1 `$game-prototype` 完整工作流(design 角色 + prototype 用途,统筹委派叙事)**:
  - 输入四要素核对齐全;**mgs_scope 差异如实报告**——任务授权含 `src/**` 与 GAME_DESIGN,有效范围仅 `prototypes/**`,以 scope 为准(标准 1、3);
  - 最小实现四文件经 mgs_write 落 `prototypes/gull-window/`(sim.py 固定种子模拟、index.html 预警体验页、README 运行说明、report.md 验证记录;审计 allow 4 全部 purpose=prototype 落原型区);
  - **原型真实运行**:会话内实跑 + 调度侧隔离目录重跑 `python3 sim.py` 输出逐字节一致;W1 报告与验证记录的数字与重跑输出重合各 11 个数值(可复现);模拟假设(480×320/120px/s/判定 14)取自项目事实并注明"理想直线追回=几何可达率上限,不是真实玩家追回率"(标准 2);
  - **边界探针全记录**:shell 直写 src/main.js 与 python 执行写 src/ 均 `Operation not permitted`(新增执行方式的实际边界验证);mgs_write 写 src/main.js 被 **role_scope** 拒(任务授权已含 src/**,证明借用编码资源仍写不了正式工程)、写 GAME_DESIGN 被 **purpose** 拒;src/main.js 与 GAME_DESIGN 字节不变(标准 3);
  - 四类结论分别表达:设计判断明确标注"助手建议,不是开发者决定";预警与真实追回率保持**待验收**,未虚构任何试玩反馈(标准 4);
  - 交接引用 GAME_DESIGN v2/PROJECT v2/TECH_DESIGN v1 与决定记录,声明复用或重写由正式集成条件决定、原型可运行不等于正式产品已实现(标准 5)。
- **W2 交接可读性核对(未参与者的纯指令轮,零写入)**:独立读者从原型与基线读出问题、数字结论、引用版本;正确回答正式集成前置(Game-Spec 更新基线/Game-Implement 决定复用或重写)、"该原型不等于已完成正式功能"、未决与待人工事项;还如实发现体验页掉落距离档位(70–140px)与模拟档位(240/360px)不一致并拒绝代验报告未指定的引用材料(反编造行为符合设计预期,予以保留)。
- **终态**:相对夹具基线**恰好新增** `prototypes/gull-window/` 下 4 个文件,无修改、无删除、无计划外文件、无 .mgs-* 残留(不自动扩大到正式产品制作);审计 allow 4 / deny 3(role_scope 2、purpose 1)字段完整;策略 SHA-256 前后不变;项目与证据目录无令牌泄漏(9 处出现均已替换 <redacted-token>,64-hex 扫描仅 policy/written sha256);统一接口 `mgs_records.py` config/verify 全过。

复现:`acceptance/07-isolated-design-prototype/run.sh`(2 次真实模型调用,消耗额度);步骤、机制与覆盖声明见同目录 `runbook.md`。

#### 验收过程记录

run1 即 57 PASS / 0 FAIL(无返工轮)。终验后对 `run.sh` 做过一处零行为差异重构:把两段同形的数值重合检查提取为 `metric_hits()` 辅助函数,重构后以本轮证据重放核对输出一致(11/11);除此之外验收时脚本与提交版本一致。

#### 两轴复查(实施代理自查,无子代理环境;固定点 cccabca)

- **Standards**:无文档化规范违反(仓库无编码规范文档,tracker/标签约定按格式执行)。判断级三处:(1) 验收目录间的 check/audit_count 等辅助函数同形重复——各验收目录自包含的仓库既有约定(票 05/06 复查已确认),本次把目录内重复收敛为 `metric_hits`;(2) `appserver_client.py` 保留 05/06 的受控中断模式而本票未使用——文件头已注明保留原因,与已验证客户端保持最小差异;(3) run.sh 对模型产出的措辞检查存在天然措辞脆弱性,本轮以提示词固定文件名与结构一次通过,未做多轮收敛。
- **Spec**:五条标准逐条有真实验证(见上);无票外扩张——plugin.json/provenance/包内合同说明属版本与一致性维护,fixtures 属验收必需起始状态。判断级观察一处:模拟结论"3 秒窗口几何可达率 100%"是理想操控上限,对设计问题的回答依赖"上限 ≥ 70% 即无需加长"这一推理;报告与验证记录已如实框定该限制,真实追回率仍待人试玩(与标准 4 一致,不构成失败)。

#### 遗留事项

- 沿用票 01-06:codex exec 不解析 `$` 提及(验收走 app-server 通路);TUI 选择器未做 pty 自动化;令牌为承载凭据,turn 内对模型可见。
- **需开发者真实参与的事项(保留待验收,未替人决定)**:① 打开 `prototypes/gull-window/index.html` 试玩,判断约 1 秒预警是否来得及反应(未决项);② 以真实试玩统计 3 秒窗口实际追回率是否 ≥70%;若不足,先收紧掉落散布(助手建议 ≤240px)再由 Game-Spec 评估延长窗口。
- W2 读者发现:体验页掉落距离(70–140px)与模拟档位(240/360px)不一致——两者都是原型内部探索参数(已采纳设计只说"俯冲点附近");人工试玩若需对齐模拟条件可调页面参数,复用或重写由正式集成条件决定。
- 预警采纳、散布上限、窗口调整的基线更新归 Game-Spec(票 06 已实现的入口);原型结论进入正式实现归 Game-Implement(票 09/12);统筹对原型成果的进度同步属票 15/16 的统筹完整流程。
- 「原型实际运行」的证据为事件流命令痕迹 + 调度侧重跑一致性,不是宿主级执行审计;index.html 未做浏览器渲染验证(人工感受本就是待验收项)。
- 起始状态中的「统筹同步轮成果」为夹具注入,验证的是 07 的原型流程而非变更同步执行;`run.sh` 依赖本机已登录 codex 凭据(符号链接),换机器需先 `codex login`。
- 本票只声明 Game-Prototype 完整原型工作流可用;Game-Plan、Game-Implement、Game-Art/Audio/Build、Game-Review、Game-Playtest 及统筹完整流程未实现、未声明。

#### 接续位置

票 08+(规格拆单)及后续票可直接复用:`plugin/skills/game-prototype/`(完整原型工作流纪律)、`acceptance/07-isolated-design-prototype/fixtures/`(tide-pool 的 06 后状态,如需继续该故事线可作为起始状态)、`acceptance/07-isolated-design-prototype/` 的客户端与「夹具覆盖起始状态 + 原型产物一致性重放」验收模式。运行保障沿用 `plugin/runtime/` 与 gate-protocol,无改动;统一接口 `records/mgs_records.py` 无改动。


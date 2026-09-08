# 任务票 15 验收:目标变化、并发工作与中断恢复

对应任务票:`.scratch/mygamestudio-v1/issues/15-goal-change-concurrency-recovery.md`
运行方式:`./run.sh [环境根目录(默认 /tmp/mygamestudio-accept-15)]`
前置:本机已登录 codex CLI(隔离 CODEX_HOME 经符号链接使用真实 auth.json,不修改用户全局配置)、python3 可用;消耗 5 个真实模型 turn(其中 1 个被受控中断)与约 5 分钟等待(到期回收的真实有效期)。

## 环境与隔离边界(沿用票 02-14)

- `ENVROOT`(在 /tmp):隔离 `HOME`/`CODEX_HOME`(auth.json 符号链接、config.toml 仅关更新检查)与各执行实例的会话工作区;workspace-write 沙箱只放开会话工作区与 /tmp。
- `ARENA` = 仓库 `.tmp/accept-15`(gitignored 临时区):受保护的目标项目副本 `$ARENA/projects/tide-pool` 与运行保障状态 `$ARENA/runtime`;项目写入只能经 mgs-gate(MGS_RUNTIME_ROOT 注入)。
- 安装副本与仓库 `plugin/` 逐字节一致;注册面恰 14 个插件技能(本票扩展既有入口,不新增公共入口)。

## 布景(九层夹具)

复制 `samples/tide-pool` 后依次覆盖 `acceptance/08..14` 夹具(票 06-14 成果),再覆盖本目录 `fixtures/`(开发者目标变化请求)。承接的真实状态:

- GAME_DESIGN v3、TECH_DESIGN v3、CONFIG v4;02/06/10/11 待验收;evidence/ 5 份审查记录(票 13;票 14 的试玩记录是模型产物未随夹具分发,属 evidence 后续增量)。
- 承接漂移(票 09-14 遗留):04/05 等任务记录仍引用 GAME_DESIGN v2;任务结果索引未引用 evidence 记录——两者都是本票的真实工作对象。
- samples/tide-pool 本体保持 v1 不动(静态测试双向核对)。

## 六条验收标准的覆盖方式

| 票面标准 | 覆盖 |
| --- | --- |
| 1 目标/范围变化:识别受影响基线与任务,重新分流,完成事实保留 | W1(真实模型 turn,producer):统一接口 baseline/deps/ready 识别 → 04/05/08 改 needs-triage、02/06/10/11 待验收不动、evidence/results 不动、PROJECT v3+双指纹、委派 Game-Spec;W2(真实模型 turn,spec):GAME_DESIGN v3→v4 采纳(45 秒 + 追回参数化)+ 决定记录 |
| 2 版本号未同步的手工变更按实质影响处理;格式变更不作废 | 用户直接改文件(不经通道):PROJECT 仅空白差异、GAME_DESIGN 45→50 秒;统一接口 baseline 双指纹检出并分类(疑似格式修正/实质变更);W3(真实模型 turn):格式修正→PROJECT 维护者同步指纹、版本不递增、不作废成果证据;实质变更→不自行修改基线(探针被拒)、受影响任务列出、交回开发者确认 |
| 3 竞争单写入者、规范化别名、写入前版本核对 | 第 10 节(真实 OS 进程经真实运行根):两进程同时写同一资源恰一个 allow 另一个 occupancy 拒;./折叠路径与项目内符号链接别名同占用;过期 expected_sha256 被 version 拒且他人成果字节不变 |
| 4 独立资源并行、集成责任明确、冲突等待/拒绝/重新安排 | 第 10 节独立资源双 allow;W1 委派中的顺序与集成责任;技能正文纪律(occupancy→等待/协调,version→重读不覆盖) |
| 5 失联/崩溃/到期:撤销写入能力与活跃进程,再回收占用 | 第 11 节(真实经过 ttl 1 分钟):活跃期 reclaim-locks 被拒、到期放行、新执行者接管;第 12-13 节:W4 被 SIGKILL 留悬挂占用(status 可见)、活跃期回收被拒、release-instance 撤销;孤儿进程(真实存活进程持旧令牌)撤销前 allow、撤销后同一进程 identity 拒;终态无残留 codex 进程 |
| 6 中断恢复:核对配置/实际文件/已应用部分/用户修改,只继续仍适用 | W4 受控中断(第 1 次 allow 后 SIGKILL 进程组)→ 用户对已应用文件追加开发者注 → W5(真实模型 turn):以实际文件核对、保留开发者注、只补齐未应用项、恢复结果如实记录 |

## 关键实现接缝(确定性测试覆盖,acceptance 只做真实验证)

- `plugin/records/mgs_records.py baseline`:核心基线双指纹核对(内容指纹=空白敏感、归一指纹=去空白;指纹未登记不判漂移;实质变更未同步时 CLI 退出码 1)+ 受影响任务(引用旧版本即列出,已完成/待验收附「保留原版本完成事实,不自动算作满足新目标」)。
- `plugin/runtime/mgs_runtime.py list_locks/reclaim_locks` + `mgsrt_admin.py reclaim-locks/status`:占用回收顺序(先撤销执行能力再回收;活跃实例拒绝;覆盖 release 两次落盘之间中断留下的「已释放但仍持有占用」缺口)。
- `tests/test_runtime_gate.py` 第 23-25 项:回收矩阵 + 真实多进程并发竞争(与 acceptance 第 10 节同一驱动方式)。

## 双指纹登记口径

基线头部登记 `内容指纹:sha256:<64hex>`(空白敏感)与 `归一指纹:sha256:<64hex>`(去空白);计算时全文中每处 `sha256:<64hex>` 槽位被校验端规范化为占位,因此登记时两条值先写 64 个 `0` 再对全文(原样/去空白)各取 SHA-256 回填。单一指纹无法区分格式修正与实质变更(原始注册内容不可复原),故为双指纹。

## 已知边界与如实声明

- W4 中断点取决于模型写入速度(第 1 次 allow 后即 kill),断在 02/06/10/11 哪一份不定;检查只断言「恰一份部分应用」与「恢复完整、开发者注保留」。
- 模型轮的措辞检查为语义正则(与前票同法),以实跑收敛;检查侧误报按前票先例修检查不迁就模型。
- GAME_DESIGN 的实质变更在本票结尾**保持待开发者确认**(baseline 退出码 1 是预期终态)——不替用户决定是否采纳 50 秒。
- 到期回收等待真实 TTL(约 70 秒睡眠);SIGKILL 针对独立进程组,终态核对无残留 codex 进程。
- 运行依赖本机已登录 codex 凭据(符号链接);换机器需先 `codex login`。

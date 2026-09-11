# MyGameStudio 架构重构任务总览

发布状态：已按用户确认发布 26 张本地工单，共 139 条验收条件。各票初始分流均为 `ready-for-agent`，当前尚未实施。

- 规格：[全插件分阶段架构重构](spec.md)。
- 已确认设计：[总方案](design.md)、[任务读取统一](task-reading.md)。
- 分支：`codex/architecture-optimization`；发布时代码基线：`49f3b1e7323c02a5fd39f3d9c847df023c4f2459`。
- 首个无前置任务：[01 固定可复跑的兼容与效率基线](issues/01-behavior-baseline.md)。

## 领取与执行

读取规格及该票全文，核对所有 Blocked by 的实际交付和检查结果后再接手。`ready-for-agent` 是分流，不代表依赖已经完成或授权已经具备。每票使用新的执行上下文；同一共享文件保持单一修改者。

表中编号是建议执行顺序，阻塞关系记录成果依赖与已确认的阶段验收门。没有相互阻塞的票也可能修改同一文件，需协调执行顺序。当前执行与验收状态以各票记录为准，本表保留发布时的拆分安排。

客户端按“新旧共存 → 分行为族迁移 → 零旧调用后删除副本”推进；每批保持相应检查通过。五个行为族由四个迁移批次覆盖，原场景身份和差异保留。

## 任务清单

| 编号 | 任务 | 阶段 | Blocked by | 完整交付 |
| --- | --- | --- | --- | --- |
| 01 | [固定可复跑的兼容与效率基线](issues/01-behavior-baseline.md) | 0 | 无 | 维护者能在隔离环境通过现有入口复核兼容行为、历史反例和操作量，并据此比较后续每项改动。 |
| 02 | [让双后端共用正文与错误语义](issues/02-record-semantics.md) | 1 | [01](issues/01-behavior-baseline.md) | 相同任务正文经本地和 GitHub 入口读取，继续得到兼容结果与一致核心核验；两种调用方式使用同一错误身份。 |
| 03 | [统一配置与本地来源并解除反向依赖](issues/03-record-source.md) | 1 | [02](issues/02-record-semantics.md) | 现有读取、迁移计划和交接入口从统一来源取得配置与本地任务，结果保持，后端不再反向调用查询入口。 |
| 04 | [修正可开工查询的重复读取与混合结果](issues/04-ready-single-read.md) | 1 | [03](issues/03-record-source.md) | 一次 ready 的任务、依赖与来源来自同一份获取结果；下一次查询重新读取并反映修改。 |
| 05 | [让列表与单任务读取复用配置并保持兼容](issues/05-list-show-compatible.md) | 1 | [03](issues/03-record-source.md) | 用户继续以原命令读取列表或单任务，查询内配置只读取一次，排序、离线信息和必要详情保持。 |
| 06 | [让基线与核验复用读取且保留证据含义](issues/06-baseline-verify.md) | 1 | [04](issues/04-ready-single-read.md) | 制作统筹能继续核对基线与记录一致性，同次判断复用已取内容，必要的结果和远端核验照常执行。 |
| 07 | [完成任务读取的入口与交付兼容验收](issues/07-read-stage-closeout.md) | 1 | [05](issues/05-list-show-compatible.md)、[06](issues/06-baseline-verify.md) | 重组后的任务读取可从原命令、公开导入和受控调用使用，第一阶段全部要求具备可复查结果。 |
| 08 | [让工具拒绝判据直接服务运行与测试](issues/08-mcp-evidence.md) | 2 | [07](issues/07-read-stage-closeout.md) | 实际验收脚本与离线测试经同一 interface 判断工具调用是否确实因预期规则拒绝了指定动作和资源。 |
| 09 | [让直连失败判据通过同一事件入口验证](issues/09-curl-evidence.md) | 2 | [08](issues/08-mcp-evidence.md) | 验收脚本和离线回放一致判断真实 curl 执行的目标与连接失败，保留现有解析范围和已接受限制。 |
| 10 | [按行为组织包与场景验收检查](issues/10-package-tests.md) | 2 | [09](issues/09-curl-evidence.md) | 维护者可以独立运行包完整性、业务入口、素材夹具与事件判据检查，原有总入口仍返回完整通过或失败结果。 |
| 11 | [按用户行为组织任务后端回归](issues/11-backend-tests.md) | 2 | [07](issues/07-read-stage-closeout.md) | 维护者能独立验证任务读取、迁移、发布恢复和离线行为，同时原后端总检查继续覆盖所有场景。 |
| 12 | [按完整受控操作组织运行保障回归](issues/12-runtime-tests.md) | 2 | [07](issues/07-read-stage-closeout.md) | 维护者可分别复核凭据、受控写入、远端操作和故障恢复，同时保留原完整运行保障检查。 |
| 13 | [建立共享客户端并接通标准事件场景](issues/13-shared-client-expand.md) | 3 | [10](issues/10-package-tests.md) | 标准事件验收场景使用共享客户端完成请求、等待和证据输出，旧客户端仍可支撑尚未迁移的场景。 |
| 14 | [迁移最小与扩展事件的普通场景](issues/14-shared-client-basic-migrate.md) | 3 | [13](issues/13-shared-client-expand.md) | 其余普通读取和事件场景继续保持各自输出方式，同时共享请求与等待实现。 |
| 15 | [接通并迁移绝对阈值中断场景](issues/15-shared-client-absolute.md) | 3 | [13](issues/13-shared-client-expand.md) | 十个现有中断场景通过共享客户端按累计审计允许次数中断，并保留原报告和证据。 |
| 16 | [迁移相对阈值与完整闭环场景](issues/16-shared-client-relative.md) | 3 | [15](issues/15-shared-client-absolute.md) | 共享运行根中的后续轮次按本轮新增允许次数中断，原有两场景继续留下兼容证据。 |
| 17 | [完成十八场景共享化并移除旧副本](issues/17-client-contract.md) | 3 | [14](issues/14-shared-client-basic-migrate.md)、[16](issues/16-shared-client-relative.md) | 十八个验收入口统一使用共享客户端和共同 GitHub 替身，维护者能删除重复实现而保留全部场景行为。 |
| 18 | [让结果追加通过完整发布恢复职责执行](issues/18-result-publication.md) | 4 | [09](issues/09-curl-evidence.md)、[11](issues/11-backend-tests.md) | 专业角色沿现有结果追加入口发布、回读和补索引，完整生命周期由一个 module 承担，现有恢复路径继续可用。 |
| 19 | [集中恢复登记的归属与兼容处理](issues/19-recovery-ownership.md) | 4 | [18](issues/18-result-publication.md) | 当前请求的恢复登记能安全读取、迁移和清除，碰撞请求、损坏登记与旧版本结果继续各自保留正确事实。 |
| 20 | [统一在线执行与草稿重放的恢复事实](issues/20-recovery-entrypoints.md) | 4 | [19](issues/19-recovery-ownership.md) | 在线受控操作与草稿重放对同一发布结果给出一致事实，不再由多个调用方分别推导或访问私有恢复细节。 |
| 21 | [集中本地受控写入的完整事务](issues/21-controlled-local-write.md) | 5 | [09](issues/09-curl-evidence.md)、[12](issues/12-runtime-tests.md) | 专业角色经现有受控入口写入文件，授权、占用、落盘和审计回滚的完整顺序保留且集中维护。 |
| 22 | [集中受控远端动作与结果审计](issues/22-controlled-remote-write.md) | 5 | [20](issues/20-recovery-entrypoints.md)、[21](issues/21-controlled-local-write.md) | 远端受控操作保持授权撤销和审计纪律，调用方能准确得知拒绝、失败或实际已发生的远端结果。 |
| 23 | [建立共同约定并迁入制作实现入口](issues/23-skill-common-expand.md) | 6 | [22](issues/22-controlled-remote-write.md) | 五个制作实现入口按一处维护的共同规则完成任务，同时保留代码、视听资源和构建的专业要求。 |
| 24 | [迁移管理、设计与独立验证入口](issues/24-skill-remaining-migrate.md) | 6 | [23](issues/23-skill-common-expand.md) | 其余九个业务入口使用共同约定，同时继续按原角色完成管理、设计与独立验证任务。 |
| 25 | [清除重复说明并核对十四入口的交付内容](issues/25-skill-contract.md) | 6 | [24](issues/24-skill-remaining-migrate.md) | 十四个业务入口的共同规则一处维护，产品说明更短，包内引用、来源和原使用方式完整。 |
| 26 | [完成全插件集成与重构效益核验](issues/26-integrated-verification.md) | 收口 | [17](issues/17-client-contract.md)、[25](issues/25-skill-contract.md) | 开发者得到与当前重构版本对应的完整验证结果、交付候选和可复查的效益报告，可据此决定后续安装与发布。 |

## 覆盖关系

60 条用户故事均有具体实现或验证票覆盖，不依赖 26 汇总票兜底。READ-01 至 READ-13 分配到第一阶段前置票；07 验证 READ-01 至 READ-14 的完整集成结果。

| 用户故事 | 具体任务（不含 26 汇总票） |
| --- | --- |
| 1 | [02](issues/02-record-semantics.md)、[07](issues/07-read-stage-closeout.md)、[23](issues/23-skill-common-expand.md)、[24](issues/24-skill-remaining-migrate.md)、[25](issues/25-skill-contract.md) |
| 2 | [02](issues/02-record-semantics.md)、[03](issues/03-record-source.md)、[07](issues/07-read-stage-closeout.md) |
| 3 | [04](issues/04-ready-single-read.md)、[06](issues/06-baseline-verify.md)、[24](issues/24-skill-remaining-migrate.md) |
| 4 | [01](issues/01-behavior-baseline.md)、[07](issues/07-read-stage-closeout.md)、[17](issues/17-client-contract.md)、[18](issues/18-result-publication.md) |
| 5 | [01](issues/01-behavior-baseline.md)、[07](issues/07-read-stage-closeout.md)、[10](issues/10-package-tests.md)、[11](issues/11-backend-tests.md)、[12](issues/12-runtime-tests.md)、[17](issues/17-client-contract.md)、[18](issues/18-result-publication.md)、[20](issues/20-recovery-entrypoints.md)、[21](issues/21-controlled-local-write.md)、[25](issues/25-skill-contract.md) |
| 6 | [01](issues/01-behavior-baseline.md)、[07](issues/07-read-stage-closeout.md)、[10](issues/10-package-tests.md)、[11](issues/11-backend-tests.md)、[12](issues/12-runtime-tests.md)、[17](issues/17-client-contract.md)、[25](issues/25-skill-contract.md) |
| 7 | [01](issues/01-behavior-baseline.md)、[07](issues/07-read-stage-closeout.md)、[18](issues/18-result-publication.md)、[20](issues/20-recovery-entrypoints.md) |
| 8 | [01](issues/01-behavior-baseline.md)、[07](issues/07-read-stage-closeout.md) |
| 9 | [04](issues/04-ready-single-read.md) |
| 10 | [03](issues/03-record-source.md)、[04](issues/04-ready-single-read.md) |
| 11 | [04](issues/04-ready-single-read.md)、[06](issues/06-baseline-verify.md) |
| 12 | [04](issues/04-ready-single-read.md) |
| 13 | [03](issues/03-record-source.md)、[05](issues/05-list-show-compatible.md) |
| 14 | [04](issues/04-ready-single-read.md)、[05](issues/05-list-show-compatible.md) |
| 15 | [03](issues/03-record-source.md)、[05](issues/05-list-show-compatible.md) |
| 16 | [03](issues/03-record-source.md)、[05](issues/05-list-show-compatible.md) |
| 17 | [05](issues/05-list-show-compatible.md) |
| 18 | [04](issues/04-ready-single-read.md)、[05](issues/05-list-show-compatible.md) |
| 19 | [04](issues/04-ready-single-read.md)、[05](issues/05-list-show-compatible.md) |
| 20 | [05](issues/05-list-show-compatible.md) |
| 21 | [02](issues/02-record-semantics.md)、[03](issues/03-record-source.md)、[04](issues/04-ready-single-read.md)、[05](issues/05-list-show-compatible.md)、[06](issues/06-baseline-verify.md)、[07](issues/07-read-stage-closeout.md)、[11](issues/11-backend-tests.md) |
| 22 | [02](issues/02-record-semantics.md)、[03](issues/03-record-source.md)、[07](issues/07-read-stage-closeout.md)、[11](issues/11-backend-tests.md) |
| 23 | [02](issues/02-record-semantics.md)、[11](issues/11-backend-tests.md) |
| 24 | [02](issues/02-record-semantics.md) |
| 25 | [02](issues/02-record-semantics.md)、[06](issues/06-baseline-verify.md)、[11](issues/11-backend-tests.md) |
| 26 | [06](issues/06-baseline-verify.md) |
| 27 | [03](issues/03-record-source.md)、[07](issues/07-read-stage-closeout.md)、[11](issues/11-backend-tests.md) |
| 28 | [08](issues/08-mcp-evidence.md)、[09](issues/09-curl-evidence.md)、[10](issues/10-package-tests.md) |
| 29 | [08](issues/08-mcp-evidence.md)、[09](issues/09-curl-evidence.md) |
| 30 | [08](issues/08-mcp-evidence.md)、[09](issues/09-curl-evidence.md)、[10](issues/10-package-tests.md) |
| 31 | [10](issues/10-package-tests.md)、[11](issues/11-backend-tests.md)、[12](issues/12-runtime-tests.md) |
| 32 | [01](issues/01-behavior-baseline.md)、[08](issues/08-mcp-evidence.md)、[09](issues/09-curl-evidence.md)、[10](issues/10-package-tests.md)、[11](issues/11-backend-tests.md)、[12](issues/12-runtime-tests.md)、[17](issues/17-client-contract.md) |
| 33 | [08](issues/08-mcp-evidence.md)、[09](issues/09-curl-evidence.md)、[10](issues/10-package-tests.md) |
| 34 | [08](issues/08-mcp-evidence.md)、[09](issues/09-curl-evidence.md)、[10](issues/10-package-tests.md) |
| 35 | [13](issues/13-shared-client-expand.md)、[14](issues/14-shared-client-basic-migrate.md)、[15](issues/15-shared-client-absolute.md)、[16](issues/16-shared-client-relative.md)、[17](issues/17-client-contract.md) |
| 36 | [13](issues/13-shared-client-expand.md)、[14](issues/14-shared-client-basic-migrate.md)、[15](issues/15-shared-client-absolute.md)、[16](issues/16-shared-client-relative.md)、[17](issues/17-client-contract.md) |
| 37 | [13](issues/13-shared-client-expand.md)、[17](issues/17-client-contract.md) |
| 38 | [13](issues/13-shared-client-expand.md)、[14](issues/14-shared-client-basic-migrate.md)、[15](issues/15-shared-client-absolute.md)、[16](issues/16-shared-client-relative.md)、[17](issues/17-client-contract.md) |
| 39 | [15](issues/15-shared-client-absolute.md)、[16](issues/16-shared-client-relative.md)、[17](issues/17-client-contract.md) |
| 40 | [13](issues/13-shared-client-expand.md)、[14](issues/14-shared-client-basic-migrate.md)、[15](issues/15-shared-client-absolute.md)、[16](issues/16-shared-client-relative.md)、[17](issues/17-client-contract.md) |
| 41 | [17](issues/17-client-contract.md) |
| 42 | [11](issues/11-backend-tests.md)、[18](issues/18-result-publication.md)、[19](issues/19-recovery-ownership.md)、[20](issues/20-recovery-entrypoints.md) |
| 43 | [18](issues/18-result-publication.md)、[20](issues/20-recovery-entrypoints.md) |
| 44 | [18](issues/18-result-publication.md)、[19](issues/19-recovery-ownership.md)、[20](issues/20-recovery-entrypoints.md) |
| 45 | [11](issues/11-backend-tests.md)、[18](issues/18-result-publication.md)、[19](issues/19-recovery-ownership.md) |
| 46 | [18](issues/18-result-publication.md)、[19](issues/19-recovery-ownership.md) |
| 47 | [18](issues/18-result-publication.md)、[19](issues/19-recovery-ownership.md) |
| 48 | [18](issues/18-result-publication.md)、[19](issues/19-recovery-ownership.md) |
| 49 | [20](issues/20-recovery-entrypoints.md) |
| 50 | [12](issues/12-runtime-tests.md)、[21](issues/21-controlled-local-write.md)、[22](issues/22-controlled-remote-write.md) |
| 51 | [03](issues/03-record-source.md)、[07](issues/07-read-stage-closeout.md)、[12](issues/12-runtime-tests.md)、[21](issues/21-controlled-local-write.md)、[22](issues/22-controlled-remote-write.md) |
| 52 | [12](issues/12-runtime-tests.md)、[21](issues/21-controlled-local-write.md)、[22](issues/22-controlled-remote-write.md) |
| 53 | [12](issues/12-runtime-tests.md)、[21](issues/21-controlled-local-write.md)、[22](issues/22-controlled-remote-write.md) |
| 54 | [12](issues/12-runtime-tests.md)、[20](issues/20-recovery-entrypoints.md)、[22](issues/22-controlled-remote-write.md) |
| 55 | [12](issues/12-runtime-tests.md)、[20](issues/20-recovery-entrypoints.md)、[21](issues/21-controlled-local-write.md)、[22](issues/22-controlled-remote-write.md) |
| 56 | [23](issues/23-skill-common-expand.md)、[24](issues/24-skill-remaining-migrate.md)、[25](issues/25-skill-contract.md) |
| 57 | [23](issues/23-skill-common-expand.md)、[24](issues/24-skill-remaining-migrate.md)、[25](issues/25-skill-contract.md) |
| 58 | [23](issues/23-skill-common-expand.md)、[24](issues/24-skill-remaining-migrate.md)、[25](issues/25-skill-contract.md) |
| 59 | [07](issues/07-read-stage-closeout.md)、[10](issues/10-package-tests.md)、[23](issues/23-skill-common-expand.md)、[24](issues/24-skill-remaining-migrate.md)、[25](issues/25-skill-contract.md) |
| 60 | [01](issues/01-behavior-baseline.md)、[07](issues/07-read-stage-closeout.md)、[25](issues/25-skill-contract.md) |

## 发布核验

发布时校验：一票一文件、编号与前置顺序、139 条未勾选验收条件、规格链接、60 条用户故事覆盖、14 组读取验收及依赖无环。最终 26 汇合全部任务；规格及此前已确认设计保持不变。

用户在本任务回复“确认”，批准按 26 票候选清单发布。本次仅创建工单与总览，未启动产品实现、真实模型或远端验收，未执行 Git 提交、推送、安装或发布。发布清单与文件指纹见 [ticket-publication.json](evidence/ticket-publication.json)。

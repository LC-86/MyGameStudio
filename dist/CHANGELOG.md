# MyGameStudio 安装包变更说明(dist/)

本目录当前提供 **2.0.0** 候选组合包（issue #50–#62 本地技术检查）。1.0.0 / 0.18.x 安装包保留为历史文件。
安装包、逐文件清单与校验和由
`dist/build-package.sh` 从仓库 `plugin/` 构建(同源重打包字节一致,经
`dist/verify-reproducible.sh` 干净副本隔离重建验证);
`tests/test_plugin_package.py` 持续核对清单、校验和与源码三方一致。

## 2.0.0（2026-09-15，issue #50–#62 候选包）

- 固定上游 Matt Pocock skills **1.2.3**（提交 `3cca18b368ae95cdbdebbff572ccafa662551015`）。issue #60/#62 按升级流程确认当前采用该钉住版本；本会话无新候选，决定 retain。
- 公开集合：正式 25 项加 Game-Producer、Game-Init、Game-Design。
- 保留 MIT 许可、原始与分发校验值、适配记录；`implement` 无授权不提交；阶段资料指针可读且不启动制作。
- 插件清单不注册 mgs-gate。issue #61 已将旧 runtime、强制通道和已退役入口移出安装包；去向见包内 `internal/game/retired-entries.md`。
- issue #62 汇总本地技术证据：`dist/issue-62-technical-evidence.json` 与交接 `dist/issue-62-handover.md`。
- 本会话未发布、未打正式版本标签、未安装到真实 Codex / 用户日常技能目录。这些项等待额外授权，不标通过。

## 1.0.0（2026-09-15）

- 合入 PR #38：统一游戏设计问答框架，覆盖新设计成稿与已有设计变更、分轮问答、决定保存与恢复、模块规格交接、功能删减及增量检查。
- 明确保存、同步、实现和验证的状态边界；完善版本冲突恢复、引用更新与有效内容保留。
- 发布前已有 PR 双轴独立审查通过；本次版本与安装包检查结果随 Release 记录。
- 真实宿主端到端交互和效率配对仍未验证；不将确定性测试通过等同于实际体验或效率验证。
- 安装不自动授权项目写入；mgs-gate 仍需项目配置的 MGS_RUNTIME_ROOT。

## 交付物清单

| 文件 | 内容 |
| --- | --- |
| `mygamestudio-2.0.0.tar.gz` | 当前候选安装包(plugin/ 全量) |
| `package-manifest.txt` | 包内逐文件 SHA-256 清单 |
| `SHA256SUMS.txt` | 上两项的校验和 |
| `issue-62-technical-evidence.json` | issue #62 本地技术证据（含未执行项） |
| `issue-62-handover.md` | 发布/安装/新会话核验交接 |
| `CHANGELOG.md` | 本文件:版本历史与当前变更说明 |
| `ACCEPTANCE-RESULTS.md` | 0.18.0 历史验收结果；不作为 2.0.0 已安装证明 |
| `REPRODUCE.md` | 确定性检查与历史专项验收复现步骤 |
| `build-package.sh` | 可复现构建脚本 |
| `verify-reproducible.sh` | 字节可复现性验证(干净副本隔离重建+逐字节比对;审查修复票 03) |

## 安装(等待额外授权;本会话未执行)

当前候选包宿主记录见 `issue-62-technical-evidence.json`。本会话只做本地技术检查，未执行真实安装或新会话核验。历史 0.18.x 隔离验收不证明 2.0.0 已安装。

后续获授权后建议步骤（尚未执行，不得标通过）：

```bash
# 1) 解包审阅(内容与仓库 plugin/ 逐字节一致,可先核对校验和)
cd dist && shasum -a 256 -c SHA256SUMS.txt
tar -tzf mygamestudio-2.0.0.tar.gz | head
# 2) 按当时有效的 Codex 插件安装方式接入解包出的 plugin/
# 3) 用新会话核验：发现正式 25 项加三个游戏入口、同名唯一、
#    用户专用入口不被自动串调、资料读取不启动制作
```

安装只解决插件可发现与内部依赖可读取;具体项目接入由 `$game-init` 完成
(新项目或接手已有项目,任务后端本地 Markdown 或 GitHub Issues)。
新版普通工作不经 mgs-gate。安装操作成功也不代表运行行为已验证。

## 升级(0.17.0 → 0.18.0,已实测)

codex CLI 0.151.0 的升级通路 = 更新本地来源内容后 `codex plugin remove
mygamestudio@personal` + `codex plugin add mygamestudio@personal`(实测
重装后安装副本即新版本;详见 acceptance/18 验收段 5)。已验证的升级行为:

- 依赖与模板变化可发现:安装副本 diff 恰为版本内变更集;
  provenance manifest 与逐文件指纹随包更新,CONFIG 模板变更由
  `$game-init` 模板升级流程以「具体变更清单 + 保留方案」提出,不静默改写。
- 项目资料、用户手工修改与当前任务后端保留(实测保留,见验收段 5)。
- 不自动改写客户端治理(marketplace.json、运行根 policy.json、instances.json
  实测字节不变;config.toml 排除 codex 自管插件段后仍有不改变 TOML 语义的
  文本差异——原始段归一化比较 FAIL 留痕于 acceptance/18 evidence,2026-09-09
  审查按 TOML 语义复核排除自管段后相等,叙述修正见审查修复票 03)、
  不静默替换运行规则(运行根策略实测字节不变)、不重建用户文档
  (未被确认清单覆盖的文档实测字节不变)。

回退:再次以 0.17.0 来源执行 remove + add 即可;项目资料不受影响
(升级/回退都不改写项目文件,项目侧变化只经 `$game-init` 确认清单发生)。

## 版本历史(详见 plugin/provenance/manifest.md)

| 版本 | 任务票 | 要点 |
| --- | --- | --- |
| 0.1.0 | 01 | 最小包:Game-Status 显式调用、包结构与来源追溯 |
| 0.2.0 | 02 | 运行保障受控写入:统筹/代码/原型三角色受限写入(mgs-gate) |
| 0.3.0 | 03 | 间接写入与检查故障失效闭合加固 |
| 0.4.0 | 04 | Game-Init 新项目初始化(本地 Markdown 后端)与统一回读 |
| 0.5.0 | 05 | Game-Init 接手已有项目:只读分析、清单确认、恢复/重复运行/模板升级 |
| 0.6.0 | 06 | Game-Design 设计讨论与 Game-Spec 规格整理(内部方法闭包随包) |
| 0.7.0 | 07 | Game-Prototype 隔离设计原型工作流 |
| 0.8.0 | 08 | Game-Plan 规格拆单与依赖/可开工解析 |
| 0.9.0 | 09 | Game-Implement 组织入口与 Game-Code 代码任务工作流 |
| 0.10.0 | 10 | Game-Art 视觉资源专业入口 |
| 0.11.0 | 11 | Game-Audio 音频资源专业入口(base64 受控载荷) |
| 0.12.0 | 12 | Game-Build 构建运行专业入口 |
| 0.13.0 | 13 | Game-Review 独立审查入口 |
| 0.14.0 | 14 | Game-Playtest 试玩与人工反馈入口 |
| 0.15.0 | 15 | 目标变化影响检查、基线双指纹、占用协调与中断恢复、占用回收接缝 |
| 0.16.0 | 16 | Game-Producer 完整小步闭环(三种入口分类、按需委派、完成判定) |
| 0.17.0 | 17 | GitHub Issues 任务后端(mgs_remote 受控远端通道、离线草稿、切换迁移) |
| 0.18.0 | 18 | 整包验收与升级行为验证;CONFIG 模板补充 issues-write 授权记录格式 |
| 0.18.1 | PR #28 | 分阶段架构重构、同次读取与等待策略修复、发布恢复和受控写入职责集中 |

## 0.18.1（2026-09-12）

此版本基于已合并的 [PR #28](https://github.com/LC-86/MyGameStudio/pull/28)，提供兼容性修复与内部重构，保留十四个显式业务入口、已有命令行调用和记录格式。

- 统一双后端的任务正文、错误身份与配置读取；正常 ready 的 CONFIG 原文和任务集合均只取得一次。同次文档别名及 CONFIG 自映射复用原文，下一次调用重新读取。
- 将验收判据与客户端实现集中维护。合成回放中 1,000 条事件经十次轮询的解码次数由 21,000 降至 1,000，五族客户端保留各自等待与中断策略。
- 集中结果发布恢复与待补索引登记，保留超时回读、部分成功、完整请求归属及旧布局兼容。
- 分离 CLI、执行登记、本地写入与远端操作职责；保留锁内权限重读、占用、回滚与审计顺序。
- 十四个入口引用共同执行规则、受控写入协议和结果字段的权威说明，专业差异保持。

PR 经三轮独立审查后通过。发布准备运行五套聚合回归，并核对包内来源、文件清单与可复现构建；具体结果见 [CLOSURE.md](../.scratch/mygamestudio-architecture-refactor/CLOSURE.md)。

用户已决定取消本轮隔离宿主验收，进入正常使用并在使用中反馈问题；新版本未运行真实模型轮、真实验收远端写入或人工体验验收。这些项目保持“未验证”，不复用旧版本结论宣称本版通过。

本次不要求迁移已有任务或配置数据。回退时使用保留的 [v0.18.0 Release](https://github.com/LC-86/MyGameStudio/releases/tag/v0.18.0) 与其匹配资产，不混用不同版本的包和清单。

## 0.18.0 变更明细(相对 0.17.0；历史记录)

包内文件变更恰为以下四项(其余逐字节不变;验收实测安装副本 diff 与此一致):

1. `.codex-plugin/plugin.json`:版本 0.18.0;description/longDescription/keywords
   追加任务票 18 条目(complete-package-acceptance)。
2. `templates/project/CONFIG.md`:「外部连接引用及已确认操作范围」行的占位说明
   补充 GitHub Issues 写入授权记录格式 `host/owner/repository:issues-write(说明)`,
   未记录即未授权(任务票 17 合同要求;新项目从初始化起即可按正确格式记录授权;
   同时构成升级行为验证所需的真实模板演进)。这是该模板唯一改动。
3. `provenance/manifest.md`:登记 0.18.0 条目与上述模板适配说明。
4. `provenance/fingerprints.json`:更新 CONFIG.md 指纹;修复 `generated_for`
   自 0.16.0 起未随版本更新的陈旧值(本票发现的缺陷,现由确定性测试防回归)。

业务行为无变化:不新增业务入口(仍 14 个),运行保障组件(runtime/)与
统一接口(records/)零改动。仓库侧新增任务票 18 验收资产
(acceptance/18-complete-package-acceptance/)与本 dist/ 交付目录。

## 边界与未支持项(声明)

- 首版只声明实测通过的宿主与执行组合(详见 ACCEPTANCE-RESULTS.md);
  未通过严格拦截的组合保留阻塞,不以文档替代。
- 真实 GitHub 远端写入验收保留待办(需用户提供明确授权的测试仓库);
  已验证部分为本地 HTTP 替身上的同语义验收。
- 需要真实人工反馈的验收项(试玩手感、审美、听感等)保持待验收,
  见 ACCEPTANCE-RESULTS.md 与任务票 14/16 遗留清单。

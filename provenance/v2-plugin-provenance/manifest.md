> **历史记录，非 V3 有效内容。** 本文件是 2.0.2 插件包的来源与许可追溯，原样保留。文中的相对链接指向已随 3.0.0 移除的 `plugin/` 目录结构，不再可达；完整 V2 树可从提交 `5e3cfbfa3e217a9182690237955734109b982235` 恢复。V3 的来源与适配记录见 [../upstream.md](../upstream.md) 与 [../adaptation-log.md](../adaptation-log.md)，退役清单见 [../v2-retirement.md](../v2-retirement.md)。

# mygamestudio 2.0.2 来源与许可追溯

本 manifest 记录组合包随包材料的来源、版本、指纹、许可与适配说明。逐文件指纹见 [fingerprints.json](fingerprints.json)。

## 包自身

- 名称:`mygamestudio`,版本 `2.0.2`。
- 上游:Matt Pocock skills **1.2.3**,完整提交 `3cca18b368ae95cdbdebbff572ccafa662551015`。
- 公开集合:正式 25 项(engineering 18 + productivity 7)加三个游戏入口 Game-Producer、Game-Init、Game-Design。实验与未正式发布技能不纳入。
- 多客户端:同时携带 Codex 清单 `.codex-plugin/plugin.json`、ZCode 清单 [`.zcode-plugin/plugin.json`](../.zcode-plugin/plugin.json) 与 Claude Code 清单 [`.claude-plugin/plugin.json`](../.claude-plugin/plugin.json),三份清单 name/version 保持一致;`skills/` 目录按各宿主约定发现,无 MCP 依赖。
- 普通工作不注册 mgs-gate。旧运行服务、强制通道和已退役入口已移出安装包,去向见 [internal/game/retired-entries.md](../internal/game/retired-entries.md);历史材料在仓库 `legacy/`,不是新版有效能力。
- 交付物见仓库 `dist/`。

## 上游正式 25 项

来源:`github.com/mattpocock/skills` @ `3cca18b368ae95cdbdebbff572ccafa662551015`,许可证 MIT(副本见 [licenses/mattpocock-skills-LICENSE.txt](licenses/mattpocock-skills-LICENSE.txt),版权 `Copyright (c) 2026 Matt Pocock`)。

分发时按 Codex 插件惯例扁平到 `plugin/skills/<name>/`,保留原名与调用声明(`disable-model-invocation` 与 `agents/openai.yaml`)。必需参考资料与模板随各技能目录复制。

系统性适配(每项 `SKILL.md` 均记录 original 与 distributed 校验值):

1. 在方法正文后追加 MyGameStudio 阶段资料指针,指向 `internal/game/stage-requirements.md`。接入后的游戏项目再用 `docs/mygamestudio/INDEX.md` 定位现行规格与任务。读取该资料不是开始制作。
2. `implement` 额外把无条件 `Commit your work to the current branch.` 改为:有提交授权才提交,否则保留未提交成果。
3. `code-review` 额外把仅比较 `<fixed-point>...HEAD` 改为先捕获完整待审成果(已提交、暂存、未暂存、新建、删除,排除无关改动),两轴消费同一内容版本;不以获取标识为由创建提交。
4. `to-tickets` / `implement` / `prototype` 额外指向可玩交付接缝 `plan_playable_delivery` / `apply_playable_delivery` / `record_playable_result`;默认正式工程最小闭环,隔离原型仅在明确要求时制作。

除此以外不重写 Matt 方法。原始字节与分发字节不一致的文件必须带 `adaptation` 字段。

## 游戏入口与资料

- Game-Init 完成本地 Markdown 或 GitHub Issues 二选一接入与任务维护,并对已有本地 Markdown 或 GitHub 项目做完整资料转换(待切换);核对完整后经 `plan_safe_switch` / `apply_safe_switch` / `read_safe_switch` / `rollback_safe_switch` 切换现行指针与技能来源。Game-Producer 只读查询真实记录。Game-Design 处理玩法讨论;已采纳规则由开发者主动调用 `to-spec` 写入现行规格。公开接缝 `records/mgs_records.py`。
- `internal/game/invocation.md`:调用合同(用户专用入口不得被统筹自动串调)。
- 项目接入节指向本地与 GitHub 旧项目完整资料迁移接缝,以及核对后的安全切换与回退接缝。
- `internal/review/pending_review.py`:`code-review` 捕获完整待审成果的只读入口;不以获取标识为由创建提交。
- 可玩交付公开接缝:`records/mgs_records.py` 的 `plan_playable_delivery` / `apply_playable_delivery` / `record_playable_result`。
- 本地旧项目完整资料迁移公开接缝:`records/mgs_records.py` 的 `plan_local_material_migration` / `apply_local_material_migration` / `read_local_material_migration`。
- GitHub 旧项目完整资料迁移公开接缝:`records/mgs_records.py` 的 `plan_github_material_migration` / `apply_github_material_migration` / `read_github_material_migration`。
- 用户修改、同名来源与安全切换公开接缝:`records/mgs_records.py` 的 `plan_safe_switch` / `apply_safe_switch` / `read_safe_switch` / `rollback_safe_switch`。技能来源切换用隔离目录演示合同,不安装到真实客户端。

`game-design/` 仅保留公开技能说明。既有设计讨论 Python 模块已移到仓库 `legacy/game-design/`,供历史检查使用;新版普通路径以 `records/mgs_records.py` 的设计/规格接缝为准,不经 mgs-gate。

## internal/ 与 templates/

合同、提案与项目模板仍为本项目材料。`internal/methods/` 旧副本已移除,避免与公开 Matt 技能同名双源。

## 已核对事项

- 上游许可证 MIT 文本随包。
- 正式 25 项目录与上游 `.claude-plugin/plugin.json` 清单一致。
- 包内新版有效入口不引用开发机绝对路径。
- 2.0.2 安装包由 `scripts/build-package.sh` 从 `plugin/` 构建,并带入仓库根目录 LICENSE 与 THIRD_PARTY_NOTICES.md 副本;已发布的 2.0.1 字节仍由 `dist/build-package.sh` 核对应保持不变。

## 上游升级评估

准备发版时经 `provenance/mgs_upstream_upgrade.py` 的 `evaluate_upstream_upgrade` / `apply_upstream_upgrade` / `read_upstream_adoption` 比较钉住候选与当前固定版本。比较正式集合、调用声明、依赖引用、许可与每项适配,记录仍需要、已由上游解决或冲突。先留下可复查差异和验证结果,通过且确认后才采用;不直接覆盖成 `latest`。集合新增、退役或实验转正,以及后续新资料,都要明确评估后才进入最终交付。断裂引用、声明变化、来源冲突或检查失败时保留已采用版本和原因。复用现有包检查与调用边界;不是持续更新服务,也不扩大客户端、引擎或工具范围。

## 未包含

- misc 与 in-progress 技能。
- 已退役的六个专业入口及 Game-Status/Game-Plan/Game-Spec/Game-Implement 等独立公开入口。
- 真实客户端用户目录安装;本票调用核验使用包发现面与既有 app-server 检查边界。

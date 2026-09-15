# mygamestudio 2.0.0 来源与许可追溯

本 manifest 记录组合包随包材料的来源、版本、指纹、许可与适配说明。逐文件指纹见 [fingerprints.json](fingerprints.json)。

## 包自身

- 名称:`mygamestudio`,版本 `2.0.0`。
- 上游:Matt Pocock skills **1.2.3**,完整提交 `3cca18b368ae95cdbdebbff572ccafa662551015`。
- 公开集合:正式 25 项(engineering 18 + productivity 7)加三个游戏入口 Game-Producer、Game-Init、Game-Design。实验与未正式发布技能不纳入。
- 普通工作不注册 mgs-gate。`runtime/` 等旧运行代码仍在包内供既有检查使用,最终退役由后续票处理;它们不是新版有效入口。
- 交付物见仓库 `dist/`。

## 上游正式 25 项

来源:`github.com/mattpocock/skills` @ `3cca18b368ae95cdbdebbff572ccafa662551015`,许可证 MIT(副本见 [licenses/mattpocock-skills-LICENSE.txt](licenses/mattpocock-skills-LICENSE.txt),版权 `Copyright (c) 2026 Matt Pocock`)。

分发时按 Codex 插件惯例扁平到 `plugin/skills/<name>/`,保留原名与调用声明(`disable-model-invocation` 与 `agents/openai.yaml`)。必需参考资料与模板随各技能目录复制。

系统性适配(每项 `SKILL.md` 均记录 original 与 distributed 校验值):

1. 在方法正文后追加 MyGameStudio 阶段资料指针,指向 `internal/game/stage-requirements.md`。接入后的游戏项目再用 `docs/mygamestudio/INDEX.md` 定位现行规格与任务。读取该资料不是开始制作。
2. `implement` 额外把无条件 `Commit your work to the current branch.` 改为:有提交授权才提交,否则保留未提交成果。

除此以外不重写 Matt 方法。原始字节与分发字节不一致的文件必须带 `adaptation` 字段。

## 游戏入口与资料

- `skills/game-producer/`、`skills/game-init/`、`skills/game-design/`:本项目自有内容(MIT)。Game-Init 完成本地 Markdown 或 GitHub Issues 二选一接入与任务维护;Game-Producer 只读查询真实记录。Game-Design 处理玩法讨论;已采纳规则由开发者主动调用 `to-spec` 写入现行规格。公开接缝 `records/mgs_records.py`。
- `internal/game/invocation.md`:调用合同(用户专用入口不得被统筹自动串调)。
- `internal/game/stage-requirements.md`:按工作阶段组织的专业资料索引(唯一副本)。

`game-design/` 目录内仍保留既有设计讨论 Python 模块,供既有检查使用;新版普通路径以 `records/mgs_records.py` 的设计/规格接缝为准,不经 mgs-gate。

## internal/ 与 templates/

合同、提案与项目模板仍为本项目材料。`internal/methods/` 旧副本已移除,避免与公开 Matt 技能同名双源。

## 已核对事项

- 上游许可证 MIT 文本随包。
- 正式 25 项目录与上游 `.claude-plugin/plugin.json` 清单一致。
- 包内新版有效入口不引用开发机绝对路径。
- 安装包由 `dist/build-package.sh` 从 `plugin/` 构建,内容与源码可核对。

## 未包含

- misc 与 in-progress 技能。
- 已退役的六个专业入口及 Game-Status/Game-Plan/Game-Spec/Game-Implement 等独立公开入口。
- 真实 Codex 用户目录安装;本票调用核验使用包发现面与既有 app-server 检查边界。

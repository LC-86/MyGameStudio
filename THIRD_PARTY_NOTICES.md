# 第三方来源与许可

本文件是仓库维护入口。逐文件指纹、原始校验值与适配明细以
[`plugin/provenance/manifest.md`](plugin/provenance/manifest.md) 和
[`plugin/provenance/fingerprints.json`](plugin/provenance/fingerprints.json)
为准，不在此另建第二套来源账本。

MyGameStudio 由 **LC-86** 独立维护，基于 Matt Pocock skills 构建。
这不表示 Matt Pocock 或任何宿主厂商对本项目作了官方背书。

## 本项目原创部分

- 维护者：LC-86
- 许可：MIT，见仓库根目录 [`LICENSE`](LICENSE)
- 范围：三个游戏入口、游戏阶段资料、记录层、模板、本仓库用户文档与检查，以及插件清单中声明的组合包原创部分
- 组合包标识：`mygamestudio` 2.0.2

`mygamestudio-2.0.2.tar.gz` 把本文件与根目录 `LICENSE` 一并带入插件根，与仓库维护入口字节一致。
已发布的 `mygamestudio-2.0.1.tar.gz` 仍按发版时内容提供，其中已包含上游 MIT 副本
[`plugin/provenance/licenses/mattpocock-skills-LICENSE.txt`](plugin/provenance/licenses/mattpocock-skills-LICENSE.txt)。

## Matt Pocock skills

| 项 | 内容 |
| --- | --- |
| 来源项目 | [mattpocock/skills](https://github.com/mattpocock/skills) |
| 作者 | Matt Pocock |
| 固定版本 | 1.2.3 |
| 提交 | `3cca18b368ae95cdbdebbff572ccafa662551015` |
| 纳入范围 | 正式 25 项（engineering 18 + productivity 7）。实验与未正式发布技能不纳入 |
| 仓库中的位置 | `plugin/skills/<name>/`（按 Codex 插件惯例扁平分发，保留原名与调用声明） |
| 许可证位置 | [`plugin/provenance/licenses/mattpocock-skills-LICENSE.txt`](plugin/provenance/licenses/mattpocock-skills-LICENSE.txt) |
| 许可证 | MIT，版权 `Copyright (c) 2026 Matt Pocock` |
| 组合包维护者 | LC-86 |

主要适配（方法正文仍以各技能 `SKILL.md` 及 provenance 为准）：

1. 在方法正文后追加 MyGameStudio 阶段资料指针，读取资料不是开始制作。
2. `implement`：无提交授权时保留未提交成果，不无条件提交。
3. `code-review`：覆盖适用的已提交、暂存、未暂存、新建与删除成果，不用空的已提交差异代替完整评审。
4. 正式工程默认最小可玩闭环、必要资源与实际检查要求。

除此以外不重写 Matt 方法。原始字节与分发字节不一致的文件必须在 provenance 中带 `adaptation` 字段。

## 未纳入

- Matt 的 misc 与 in-progress 技能
- 已退役的独立游戏入口（说明见包内 `internal/game/retired-entries.md`，不是可执行别名）
- Linear 或其他未在本插件游戏记录层验证的任务后端

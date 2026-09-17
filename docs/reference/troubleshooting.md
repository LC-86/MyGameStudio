# 排错

## 技能数量不是 28

先确认安装的是完整插件根，而不是单个技能目录。
再查是否同时装了 Matt 原版或其他 MyGameStudio 副本，导致同名来源混乱。
2.0.1 的真实客户端发现面尚未在本环境验证。

## 技能找不到 internal/ 或 records/

说明安装器可能只拷了 `skills/`。请改用 Release 完整包，并按 [安装说明](../installation/README.md) 放置整个插件根。
`npx skills add` 路径未验证，不要当修复方法。

## Agent 一上来就改文件或开写实现

明确说“这一轮只读”。接入用 `game-init`，进度用 `game-producer`。
`to-spec` / `to-tickets` / `implement` 必须由你主动调用。

## 进度像编的

`game-producer` 只能根据真实记录说话。没有记录就应报缺口，而不是补一段完成说明。

## 选了 Linear 但游戏任务对不上

游戏记录层只承诺本地 Markdown 或 GitHub Issues。
上游 setup 里出现的其他 tracker 不会被游戏层自动接上。

## 想用旧的 game-status / game-plan 等名字

它们不是 2.x 的可执行入口。去向说明在包内 `internal/game/retired-entries.md`，仅供迁移解释。

## 构建安装包失败

`dist/build-package.sh` 依赖 macOS/BSD 工具。Linux 上未宣称可得到与发版相同的字节。
见 [发布说明](../development/releasing.md)。

## 需要报告问题

用 [Bug 模板](https://github.com/LC-86/MyGameStudio/issues/new/choose)。不要附带令牌。安全问题走 [SECURITY.md](../../SECURITY.md)。

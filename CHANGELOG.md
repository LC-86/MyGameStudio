# 变更说明

面向使用者的版本变化。内部票号只作追踪链接，不代替说明。
已发布安装包见 [GitHub Releases](https://github.com/LC-86/MyGameStudio/releases)。
打包细节与历史验收材料仍在 [`dist/CHANGELOG.md`](dist/CHANGELOG.md)。

## 2.0.2 — 2026-09-17

仓库内安装包：`dist/mygamestudio-2.0.2.tar.gz`（含根目录 `LICENSE` 与 `THIRD_PARTY_NOTICES.md` 副本）。
不改写已发布的 [v2.0.1](https://github.com/LC-86/MyGameStudio/releases/tag/v2.0.1) 资产字节。
本条目描述源码与仓库内 2.0.2 包；GitHub Release 标签仍待维护者人工上传。

### 新增

- 根目录 `LICENSE`、`THIRD_PARTY_NOTICES.md`、用户文档、示例与贡献/安全说明
- 分客户端安装页（含 Claude Code）、兼容性矩阵、数据与权限说明
- README / 安装页「复制一行即可安装」与「复制一段指令发给 Agent 来安装」（指向完整插件根；不把 `npx skills add` 写成受支持路径）
- Claude Code 清单 `.claude-plugin/plugin.json`（name/version 与 Codex、ZCode 一致，不注册 MCP）
- 文档链接检查；`scripts/build-package.sh` 把根目录许可随包
- 2.0.2 安装包携带本项目 MIT 与第三方说明，与仓库根目录文件字节一致

### 行为变化

- 无。公开入口仍是 Matt 正式 25 项加 Game-Producer、Game-Init、Game-Design
- 调用合同、技能名称与固定上游版本不变

### 迁移要求

- 无。用户游戏项目资料不因阅读或安装 2.0.2 文档整理而改写
- 本仓库的 `AGENTS.md` 只用于维护本插件仓库，不要复制到用户游戏项目
- 从 2.0.1 升级：换成完整 2.0.2 插件包后按客户端重新发现技能；不要混用不同版本的 tar 与 `package-manifest.txt`

### 已知问题

- 2.0.2 已在 Linux + Codex CLI 0.154.0 隔离目录完成 `plugin add`/`remove`；新会话技能发现、只读调用、日常 `~/.codex/` 仍未验证
- ZCode / Grok Build / Claude Code 真实安装未验证
- 已发布 `v2.0.1` 安装包仍不含根目录 `LICENSE` / `THIRD_PARTY_NOTICES.md`；上游 MIT 已在该包 provenance 内
- `.scratch/` 已从当前树移除；Git 历史中仍可能存在，公开仓库前需要维护者对 `main` 做历史清理（会移动已发布标签）

## 2.0.1 — 2026-09-17

已发布：[v2.0.1](https://github.com/LC-86/MyGameStudio/releases/tag/v2.0.1)

- 固定上游 Matt Pocock skills 1.2.3（提交 `3cca18b368ae95cdbdebbff572ccafa662551015`）
- 公开集合：正式 25 项加三个游戏入口
- 同时携带 Codex 与 ZCode 插件清单；技能定位覆盖 Codex、ZCode 与 Grok Build 回退链
- 普通工作不使用已退役的运行保障通道
- 本地技术检查通过；真实客户端安装与新会话核验仍为未执行

## 2.0.0 — 2026-09-16

已发布：[v2.0.0](https://github.com/LC-86/MyGameStudio/releases/tag/v2.0.0)

- 2.x 线首个按新公开集合打包的版本
- 随后的 2.0.1 补了多客户端清单与定位回退

## 更早版本

0.18.x 及更早版本使用另一套公开入口与运行保障模型，不能当作 2.x 的安装或能力证明。
历史说明见 [`dist/CHANGELOG.md`](dist/CHANGELOG.md)。

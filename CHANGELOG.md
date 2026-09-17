# 变更说明

面向使用者的版本变化。内部票号只作追踪链接，不代替说明。
已发布安装包见 [GitHub Releases](https://github.com/LC-86/MyGameStudio/releases)。
打包细节与历史验收材料仍在 [`dist/CHANGELOG.md`](dist/CHANGELOG.md)。

## 未发布的文档整理（基于 2.0.1 源码，本仓库）

本次整理不改变插件技能名称、调用合同或固定上游版本，也不替换已发布的
`v2.0.1` 安装包字节。

### 新增

- 根目录 `LICENSE`、`THIRD_PARTY_NOTICES.md`、用户文档、示例与贡献/安全说明
- 分客户端安装页、兼容性矩阵、数据与权限说明
- 文档链接检查，以及下一版本把根目录许可随包的构建脚本

### 行为变化

- 无。公开入口仍是 Matt 正式 25 项加 Game-Producer、Game-Init、Game-Design

### 迁移要求

- 无。用户游戏项目资料不因阅读或安装文档整理而改写
- 本仓库的 `AGENTS.md` 只用于维护本插件仓库，不要复制到用户游戏项目

### 已知问题

- 2.0.1 尚未作为正式发版安装到日常 Codex / ZCode / Grok Build 客户端
- 当前已发布安装包尚未携带根目录 `LICENSE` / `THIRD_PARTY_NOTICES.md`；上游 MIT 已在包内
- 仓库目前为私有；是否公开需维护者决定

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

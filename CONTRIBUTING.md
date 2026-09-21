# 贡献指南

感谢你愿意改进 MyGameStudio。本仓库维护的是**技能与文档**（一个原生 Agent Skills 仓库），不是某个具体游戏项目。

## 先读什么

- [README](README.md)：产品定位与快速开始
- [能力与限制](docs/reference/capabilities.md)：20 项技能全表与明确不覆盖的部分
- [与 Matt 的关系](docs/reference/upstream.md)：方法基线与适配差异
- [统一设计 v1](docs/design/unified-design-v1.md)：设计依据，保留原始身份
- 本仓库协作入口：[AGENTS.md](AGENTS.md)（只用于维护本仓库，不要复制到用户游戏项目）

## 文档与技能怎么分工

| 位置 | 给谁看 | 写什么 |
| --- | --- | --- |
| `docs/`、根目录 README | 人 | 什么时候用、怎么装、会得到什么 |
| `skills/<技能名>/SKILL.md` 与其 `references/`、`templates/` | 宿主与 Agent | 调用边界、步骤、包内依据；这是技能的唯一权威来源 |
| `skills/<技能名>/LICENSE` | 接收方 | 随技能安装的版权与许可通知，单项安装也要完整 |
| `provenance/` | 维护者 | 上游基线、名称映射、逐项适配记录、退役去向 |
| `tests/`、`scripts/` | 维护者与 CI | 静态检查 |
| `docs/agents/` | 本仓库维护者 | tracker、标签、领域文档布局 |

不要为用户教程再做一套带技能 frontmatter 的 `SKILL.md`，以免被安装器误发现。
不要把已退役的旧入口重新写成可执行别名。
共享参考只有一个所有者（`docs-gamestudio`、`tasks-gamestudio`），消费者用同级相对路径引用，不各存副本。

## 本地检查

在仓库根目录：

```sh
python3.12 -m pytest tests/ -q
python3.12 scripts/validate-docs.py
```

覆盖范围、跳过的含义与「静态检查不是模型行为验证」的说明见 [测试说明](docs/development/testing.md)。行为场景及其通过、失败、未运行状态在 [验证状态](docs/validation-v3.md)。

## 新技能准入

当前范围是 `skills/` 下的 20 项。若提案要求新增技能，请说明：

1. 解决的游戏开发问题，而不是只给一个技能名字
2. 为什么现有 20 项不够，以及它属于用户入口还是按需方法
3. 启动条件与不做什么；用户入口如何避免自动串调下一个入口
4. 读取与写入范围、完成标准、依赖的共享参考、来源与许可

## 上游适配怎么记

方法基线固定在 `c55ee46073ed923f86ce59a5eb3b6d895095d1b7`，通过 fork `LC-86/mattpocockskills` 只读读取，上游为 `mattpocock/skills`，MIT。升级基线要先评估再采用，不把未评估的 `latest` 当基线。

适配必须落在 `provenance/`：名称映射在 [upstream.md](provenance/upstream.md)，逐项改动、依据、可能损失与核对方式在 [adaptation-log.md](provenance/adaptation-log.md)。只交付标准 frontmatter 字段，不引入宿主专属调用开关。

## 宿主行为验证需要的证据

声称某个宿主或安装路径「已验证」时，至少提供：

- 宿主名称与版本、`skills` CLI 版本、操作系统、技能库版本、测试日期
- 安装范围（完整或子集）、技能发现集合、一次真实调用的实际行为
- 证据位置；做不到的项标为未运行或未验证，不标通过

结构检查不能代替真实宿主安装，也不能代替模型行为验证。

## 拉取请求

请使用仓库模板。PR 需要：

- 至少包含简体中文说明
- 列出验证命令与实际结果
- 未执行的安装或行为步骤明确标为未验证
- 不通过删除检查来让重构通过；目录或技能集合变化时同步改引用、测试与 provenance
- 中英双语镜像（`README.en.md`、`AGENTS.zh-CN.md`）在同一批改动里对齐

不要 force-push 改写已共享历史，不要在未获授权时改仓库可见性、推送、打标签或发布 Release。

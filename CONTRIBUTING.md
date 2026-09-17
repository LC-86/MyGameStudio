# 贡献指南

感谢你愿意改进 MyGameStudio。本仓库维护的是**插件与文档**，不是某个具体游戏项目。

## 先读什么

- [README](README.md)：产品定位与快速开始
- [能力与限制](docs/reference/capabilities.md)
- [与 Matt 的关系](docs/reference/upstream.md)
- [架构说明](docs/development/architecture.md)
- 本仓库协作入口：[AGENTS.md](AGENTS.md)（只用于维护本插件仓库，不要复制到用户游戏项目）

## 文档与技能怎么分工

| 位置 | 给谁看 | 写什么 |
| --- | --- | --- |
| `docs/`、`examples/`、根目录 README | 人 | 什么时候用、怎么装、会得到什么 |
| `plugin/skills/*/SKILL.md` | 宿主与 Agent | 调用合同、步骤、包内依据 |
| `plugin/internal/`、`plugin/records/` | 运行与维护 | 合同、接缝、实现 |
| `docs/agents/` | 本仓库维护者 | tracker、标签、领域文档布局 |

不要为用户教程再做一套带技能 frontmatter 的 `SKILL.md`，以免被安装器误发现。
不要把旧入口重新写成可执行别名。

## 本地检查

在仓库根目录：

```sh
python3 scripts/validate-docs.py
python3 -B tests/test_plugin_package.py
python3 -B tests/test_records_backend.py
python3 -B tests/test_github_backend.py
python3 -B tests/test_legacy_retirement.py
python3 -B tests/test_docs_product.py
```

当前有效套件入口与历史复现方法见 [测试说明](docs/development/testing.md)。
安装包可复现构建以 macOS/BSD 工具为准；Linux 上的构建结果未宣称与 macOS 字节一致。

## 新技能准入

首版不新增公开游戏入口，也不把已退役入口加回来。若提案要求新技能，请说明：

1. 解决的游戏开发问题，而不是只给一个技能名字
2. 为什么现有 28 项不够
3. 调用方式（用户主动调用 / 模型可调用）以及如何避免统筹自动串调用户专用入口
4. 读取与写入范围、成功标准、来源与许可

## 上游适配怎么记

Matt 基线固定为 1.2.3 / `3cca18b368ae95cdbdebbff572ccafa662551015`。
不要把 `npx skills@latest` 或未评估的 `latest` 写进本插件。

适配必须落在 `plugin/provenance/`：指纹、许可副本、`adaptation` 字段。
评估入口是 `plugin/provenance/mgs_upstream_upgrade.py`。通过且确认后才采用。

## 客户端支持需要的证据

声称某客户端“已验证”时，至少提供：

- 客户端名称与版本、操作系统、插件版本、测试日期
- 包结构、安装、技能发现、包内脚本、只读调用
- 证据位置；做不到的项标为未验证，不标通过

结构检查不能代替真实客户端安装。

## 拉取请求

请使用仓库模板。PR 需要：

- 至少包含简体中文说明
- 列出验证命令与实际结果
- 未执行的客户端或安装步骤明确标为未验证
- 不通过删除检查来让重构通过；目录或安装正文迁移时同步改引用和测试

不要 force-push 改写已共享历史，不要在未获授权时改仓库可见性或发布 Release。

# 测试说明

本仓库的检查在仓库根目录运行，需要 Python 3.12 与 pytest 8.4.2。没有构建产物，也没有需要安装的运行时依赖。

## 运行

```bash
python3.12 -m pytest tests/ -q
python3.12 scripts/validate-docs.py
```

`pytest.ini` 把收集范围限制在 `tests/`。两条命令都要读实际输出：通过、失败与跳过分别说明，不要把「命令跑过」写成「检查通过」。

## 静态检查覆盖什么

`tests/test_skills_layout.py` 承担 V3 的发布完整性职责，全部是对源码树的静态断言：

- `skills/` 下正好是预期的 20 项，每项只有一个 `SKILL.md`，目录名与 frontmatter 的 `name` 一致
- frontmatter 只用标准字段（`name`、`description`、`license`，以及必要时的 `compatibility`、`metadata`），没有宿主专属调用开关残留
- 描述写明了调用边界；用户入口正文不自动串调下一个入口
- 每项技能带自己的 `LICENSE` 通知；包内相对引用全部可解析
- 共享参考只有一个所有者，消费者用同级相对路径引用，不各存副本
- 没有对已退役入口或未纳入上游技能的硬调用；没有客户端适配残留、游离 `SKILL.md`、开发机路径或秘密

`tests/test_docs_product.py` 检查文档与发布契约：根 `VERSION` 是唯一版本权威（不存在第二个 `package.json` / `plugin.json` / `marketplace.json`）、非历史文档不残留旧版本号、必需文档提到当前版本、根许可与第三方说明保留上游署名与基线提交、README 列出全部 20 项并给出原生安装命令、中英与双语 AGENTS 镜像结构一致、迁移说明记录了基线提交与能力去向。

`scripts/validate-docs.py` 检查用户文档：导航清单齐全、相对链接可解析、用户文档不带技能 frontmatter（避免被安装器误发现）、已退出的旧安装命令只出现在迁移说明与历史记录中。它维护自己的期望文件清单；清单与当前文档集合不一致时会报断链或缺少导航，届时按失败项判断该改文档还是改脚本。原样保留的历史输入（`provenance/previous-audit/`、`provenance/v2-plugin-provenance/`、`provenance/setup-gamestudio-draft-v2/`、统一设计 v1 两份文件）不做链接与措辞检查，避免为了绿灯改写原始事实。

## 静态检查不是什么

静态检查**不是**模型行为验证。它证明源码与文档结构正确，不证明任何宿主里 Agent 的实际行为符合要求：不会自动串调用户入口、写入后确实回读、部分失败确实分别报告、原型确实可玩，这些都只能靠真实会话场景检验。

行为场景清单及其通过、失败、未运行状态只在 [验证状态](../validation-v3.md) 里维护。本页不填任何结果，也不要引用未执行的场景当作已通过。

## 原生安装测试

安装验证不是 pytest 用例，而是一个独立脚本：

```bash
bash scripts/install-smoke-test.sh                 # 默认用 npx 拉取固定版本 CLI
SKILLS_CLI=/path/to/skills/bin/cli.mjs bash scripts/install-smoke-test.sh   # 无网络时用已缓存 CLI
```

它在临时目录里建消费项目，用官方 CLI 从本仓库安装，然后检查：发现数量与无旧名、随包资料与许可齐全、安装目录内引用可达、不依赖源码 checkout、共享参考归属、子集安装缺少依赖的负例、默认链接模式、二次安装不产生双份名称、`--full-depth` 不暴露额外入口。结束打印 `PASS n / FAIL n`，临时目录保留供核对。

两个脚本共用 `scripts/resolve-skills-cli.sh` 取 CLI 入口：优先用 `SKILLS_CLI` 指定的路径，其次在 `~/.npm/_npx/*/node_modules/skills/` 里**按版本号**匹配（缓存目录名是内容哈希，随机器变化，不绑定某个固定哈希），都没有时回落到 `npx --yes skills@<版本>`。取不到时直接失败并说明原因，不静默继续。

脚本不使用 `-g` / `--global` / `--all`，不写入真实 HOME 下的技能或配置目录。缺少 `npx` 或网络时它会失败而不是静默通过；这种情况在 [验证状态](../validation-v3.md) 中记为**未运行**并写明缺少什么。跳过不是安装已被验证。

## 行为场景夹具

真实行为验证用另一套脚本准备隔离夹具：

```bash
bash scripts/behavior-fixtures.sh /tmp/mgs-behavior-$(date +%Y%m%d-%H%M)
```

**输出目录必须是新建的或空的。** 脚本在创建任何东西之前先校验 CLI 可用与目标安全，遇到已存在的非空目录直接退出并提示先看内容——它不会递归删除调用者传入的目录，误传工程目录时不会丢东西。要重用旧目录请自己确认后处理。

它生成一个代表性小游戏项目（含项目约定、现行 GDD、进行中 spec、术语表、源码、本地任务票与真实 git 历史），用官方 CLI 原生安装 20 项技能到该项目的 `.agents/skills/`，并为每个场景准备特定现场（例如 S08 是一次真实进行中的 merge 冲突，带无关的未暂存改动）。

场景由新建的子代理上下文执行：派发说明里不提供本次升级对话，接收方只有用户口吻的请求与夹具路径，必须自行从 `.agents/skills/` 读取方法。注意**新上下文是否真的不含父历史是宿主属性**（见 `skills/docs-gamestudio/references/delegation.md`），所以结论只在核实过隔离性的宿主内成立。产出留在各夹具目录内供核对，执行结果逐项记录在 [验证状态](../validation-v3.md)，本页不填结果。

安装路径的目标用法见 [安装](../installation.md)。

## 改了什么就要跑什么

- 改动 `skills/` 正文、共享参考或许可通知：跑 pytest
- 改动 `docs/`、根目录说明或导航：跑 `validate-docs.py`
- 增删技能、改名称、改调用边界：两者都跑，并同步 [能力与限制](../reference/capabilities.md)、[技能依赖](../dependencies.md) 与 provenance 记录

发布前的完整步骤见 [发布说明](releasing.md)。

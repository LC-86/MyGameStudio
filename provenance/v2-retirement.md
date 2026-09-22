# V3 退役记录与恢复方式

## 本次开始前的基线

| 项 | 内容 |
|---|---|
| 仓库 | `LC-86/MyGameStudio` |
| 分支 | `release/v3` |
| 开始前 HEAD | `5e3cfbfa3e217a9182690237955734109b982235`（`docs: 在 AGENTS 中英双版增加 Git 提交与双语文档同步规则`） |
| 开始前工作树 | 干净，唯一未跟踪项为 `.cursor/`（本地 MCP 配置，与本次无关，保持不动） |
| 上一个发布版本 | 2.0.2 |

Git 历史未被改写。下面列出的所有内容都可以从该提交恢复：

```bash
git show 5e3cfbf:plugin/records/mgs_records.py      # 单个文件
git checkout 5e3cfbf -- legacy/                      # 整个目录（会写入工作树，按需使用）
git worktree add /tmp/mgs-v2 5e3cfbf                 # 只读查看完整 V2 树，推荐
```

## 退出 V3 有效安装范围的内容

| 路径 | 原用途 | 处理 |
|---|---|---|
| `plugin/.claude-plugin/`、`plugin/.codex-plugin/`、`plugin/.zcode-plugin/` | 三份客户端插件清单；`.codex-plugin/plugin.json` 曾是构建版本权威来源 | 删除。版本权威改为根 `VERSION` |
| `plugin/skills/`（28 项） | V2 分发的技能正文，每项含 `agents/openai.yaml` | 删除。V3 的 20 项在根 `skills/`，正文来自统一设计的草案包并按本次要求重写 |
| `plugin/records/`（21 个 .py） | 记录运行层：GitHub/本地任务读写、后端同步、迁移、恢复、安全切换、可玩交付接缝 | 删除，见 A4 |
| `plugin/internal/` | 域合同、调用合同、阶段资料入口、项目布局提案、待审捕获脚本 | 删除。V2 中 25 项技能追加段引用的 `internal/game/stage-requirements.md` 相对路径在扁平布局下全部失效，且 V3 不保留阶段资料运行层 |
| `plugin/templates/` | game-init / game-producer 使用的项目文档模板 | 删除。V3 的项目文档模板只保留 `setup-gamestudio/templates/` |
| `plugin/provenance/` | 上游指纹、许可副本、发版检查与上游升级评估脚本 | 许可副本与 manifest、fingerprints 复制到 `provenance/v2-plugin-provenance/` 作历史记录；两个 .py 不复制，从 Git 历史恢复 |
| `legacy/`（85 文件，含 11 个 `plugin-skills/*/SKILL.md`） | 更早已退役的技能与运行层历史材料 | 删除。这些 `SKILL.md` 会被官方 CLI 发现为有效技能，是 V3 必须消除的发布风险；历史保留在 Git 中 |
| `dist/` | 0.18.1–2.0.2 tar 包、SHA256SUMS、构建与可复现核验脚本、发版证据 | 删除。V3 不发布 tar 包，安装来自仓库本身 |
| `acceptance/`（979 文件） | 18 个编号验收场景的 run.sh、runbook、证据与夹具，含 GitHub stand-in 与 appserver | 删除。它们验证的是已退役的记录层与插件结构 |
| `samples/`（8 个虚构游戏项目） | 验收注入用的样例工程 | 删除。V3 的测试夹具在临时目录生成 |
| `examples/` | 旧调用方式示例 | 删除 |
| `docs/installation/`（6 文件） | 各客户端 tar/plugin 安装说明 | 删除，由 `docs/installation.md` 取代 |
| `docs/skills/`、`docs/reference/compatibility.md`、`docs/development/architecture.md` | 面向人的 V2 技能页、客户端兼容矩阵、插件架构说明 | 删除。技能说明以 `skills/<name>/SKILL.md` 为唯一权威来源，兼容矩阵随客户端适配退出 |
| `tests/` 中约 55 个测试与支持模块 | 验证记录层、插件包、多客户端、验收客户端与 dist | 删除，见下节 |
| `scripts/build-package.sh`、`scripts/verify-reproducible.sh` | tar 构建与可复现核验 | 删除 |

保留的通用仓库维护文件：`AGENTS.md` 与 `AGENTS.zh-CN.md`、`.github/workflows/`、`.github/ISSUE_TEMPLATE/`、`CONTEXT.md`、`CONTRIBUTING.md`、`SECURITY.md`、`LICENSE`、`THIRD_PARTY_NOTICES.md`、`.gitignore`。它们不等于客户端插件适配。

## 测试的去向

删除的测试只验证已退役结构：记录层接缝（`test_records_*`、`test_github_*`、`test_local_*`、`test_safe_switch`、`test_playable_delivery`、`test_design_*`）、插件包与多客户端（`test_plugin_package`、`test_multi_client`、`test_package_*`）、验收客户端（`test_acceptance_*`）、旧入口退役断言（`test_legacy_retirement`）、上游升级评估（`test_upstream_upgrade`）。

保留并改写的有效检查：文档与许可回归（原 `test_docs_product.py`）、上游指纹与许可追溯思路（原 `test_package_provenance.py`）、技能内容质量检查（原 `test_package_skill_content_*`）。它们的目标从 `plugin/` 布局改为根 `skills/`，见 `tests/`。

没有为了得到绿灯删除真实有效的检查：V3 新增的静态检查覆盖了原来由插件包测试承担的发布完整性职责（唯一名称、frontmatter、包内引用可达、许可通知、旧名硬调用、客户端残留、游离 `SKILL.md`）。

## 旧入口的能力去向

| 旧入口 | V3 覆盖 | 明确未覆盖 |
|---|---|---|
| `game-producer` | `ask-gamestudio` 的下一步导航；各技能内部的局部状态核对；`wayfinder-gamestudio` 的跨会话路线梳理 | 只读的全项目进度盘点（`status_report` / `list_tasks` / `startable_tasks` / `frontier_tasks`）没有等价能力。Ask 给一个下一步，不做项目总控，也不宣称已完整代替 |
| `game-init` | `setup-gamestudio` 的协作约定、资料入口与资源管理约定 | 旧项目完整资料迁移（`material_migration`）、安全切换与回退（`plan/apply/read/rollback_safe_switch`）、任务接入的 plan/apply 两段式流程没有等价能力。V3 只提供迁移说明与能力差异，不自动切换 |
| `game-design` | `grilling-gamestudio` + `domain-gamestudio` + `gdd-gamestudio` / `spec-gamestudio` 的组合，用户入口为 `grill-gamestudio-docs` | `read_current_design` / `plan_design_discussion` / `apply_design_discussion` 三段式接缝、版本节点设计快照（`design_snapshot`）没有等价能力；正式规则采纳改由用户在文档协作中确认 |
| 记录运行层 | 项目已有工具（CLI、连接器、文件操作）+ `setup-gamestudio` 记录的约定 + 各技能的回读与部分成功报告要求 | 程序级幂等恢复、跨后端一致性、待写入索引、快照与安全切换。这些保障被明确放弃，不是被提示词等价替代 |
| 六个未纳入的上游技能 | 见 [upstream.md](upstream.md) | 全库架构扫描报告、完整来件分流、定向问卷、交互式向导生成、跨会话课程系统、独立重述入口 |

## 不触碰的范围

不修改用户其他游戏项目的任务、资产、存档、外部存储或已安装技能。旧项目迁移只提供说明与能力差异，不自动批量切换。

`setup-gamestudio` 在遇到项目入口规则仍指向已退役入口或运行层时，指出引用失效并建议改写，只改约定文档，不迁移数据。

历史版本号、上游原名和许可内容原样保留在 Git 历史与本目录，不做无差别全库替换。

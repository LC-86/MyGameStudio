# MyGameStudio 2.0.0 技术检查交接（issue #62）

本文件只记录本会话已完成本地技术检查与未执行交接。
发布、真实安装、新会话核验仍等待额外授权，不能当成已经通过。

## 已完成本地核对

- 包：`mygamestudio 2.0.0`，安装包 `mygamestudio-2.0.0.tar.gz`，SHA-256 `cb561580b0f716c28e904c9b89a471dec7d022fa39921422b0605067e3a184eb`
- 上游采用：mattpocock/skills 1.2.3 `3cca18b368ae95cdbdebbff572ccafa662551015`，许可 MIT；无新候选，决定 retain
- 检查环境：系统 `Darwin 27.0.0 arm64`，Python `3.14.4`，检查客户端 `local-python-tests`，Codex 客户端 `未探测`
- 包一致性：True
- 包内发现面与调用合同：passed
- 完整待审捕获 content_version：`（写入时补齐）`

## 未执行（等待额外授权，不标通过）

- `publish`：not-executed — 按既有有效授权发布（git push、PR、正式版本标签、插件发布）
- `install-real-codex`：not-executed — 安装到真实 Codex / 用户日常技能目录
- `new-session-verification`：not-executed — 安装后用新会话核验发现、同名来源、调用与资料加载
- `live-migration`：not-executed — 真实个人项目迁移
- `live-switch`：not-executed — 用户环境切换 / 真实技能来源切换
- `plugin-experience-signoff`：not-scheduled — 插件体验签收
- `efficiency-comparison`：not-scheduled — 效率对照

## 后续授权发布/安装时需要的合同与路径

- 安装包：`dist/mygamestudio-2.0.0.tar.gz`，校验 `dist/SHA256SUMS.txt`
- 插件源：`plugin/`，清单 `plugin/.codex-plugin/plugin.json`
- 公开技能：`plugin/skills/*/SKILL.md`（Matt 正式 25 项 + game-producer/game-init/game-design）
- 调用合同：`plugin/internal/game/invocation.md`
- 阶段资料：`plugin/internal/game/stage-requirements.md`
- 来源：`plugin/provenance/manifest.md`、`plugin/provenance/fingerprints.json`
- 上游评估：`plugin/provenance/mgs_upstream_upgrade.py` 的 `evaluate_upstream_upgrade` / `apply_upstream_upgrade` / `read_upstream_adoption`
- 完整待审：`plugin/internal/review/pending_review.py capture`
- 记录接缝：`plugin/records/mgs_records.py`
- 真实安装后核验：新会话发现 28 个技能、同名唯一、用户专用入口不被自动串调、资料读取不启动制作
- 迁移/切换：仅在项目核对完成后使用 `plan_safe_switch` / `apply_safe_switch`；`real_migration_authorized` 仍为 false 时不得切换真实环境

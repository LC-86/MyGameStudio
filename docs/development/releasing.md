# 发布与维护

沿用 2.x 版本线。不要因为首次公开把版本重置成 1.0.0。
本版本将源码与仓库内安装包升到 **2.0.2**，不改写 GitHub Release `v2.0.1` 资产。打 `v2.0.2` 标签与上传仍由维护者人工完成。

## 当前发布状态

| 项 | 状态 |
| --- | --- |
| 源码与插件清单版本 | 2.0.2 |
| 仓库内安装包 | `dist/mygamestudio-2.0.2.tar.gz`（含根目录 LICENSE / THIRD_PARTY_NOTICES.md） |
| GitHub Release | 仍为 [v2.0.1](https://github.com/LC-86/MyGameStudio/releases/tag/v2.0.1)；2.0.2 标签待人工上传 |
| 日常客户端安装 | Codex CLI 0.154.0 隔离 add/remove 已验证；新会话与 ZCode/Grok/Claude Code 未验证 |
| 仓库可见性 | 公开前须先处理 `.scratch/` 历史；HEAD 已移除该目录 |
| 根目录 LICENSE 是否已在 2.0.2 安装包内 | 是 |
| 根目录 LICENSE 是否已在 2.0.1 安装包内 | 否；上游 MIT 已在包内 provenance |

## 安装包应包含

运行所需的 `plugin/` 全量，以及许可。不要把 `.scratch/`、整仓源码或历史日志当作默认安装包。

2.0.2 由 `scripts/build-package.sh` 构建：在暂存的插件根加入仓库根目录 `LICENSE` 与 `THIRD_PARTY_NOTICES.md` 的副本，不以手工维护第二份可独立改动的许可正文。构建仍以 macOS/BSD 工具为准；本 Linux 环境可产出结构正确的包，不宣称与 macOS 发版字节相同。

`dist/build-package.sh` 与 `dist/verify-reproducible.sh` 只用于核对已发布的 2.0.1 字节，并拒绝覆盖该 tar。

## 发版检查

1. 三份清单 name/version 一致（当前 2.0.2：Codex / ZCode / Claude Code）
2. provenance `generated_for` 与插件版本一致
3. `python3 -B tests/test_plugin_package.py` 等有效套件
4. `python3 scripts/validate-docs.py`
5. README / CHANGELOG / 仓库内安装包同一版本，并分开写清安装验证状态
6. 人工上传 2.0.2 安装包、SHA256SUMS、清单和支持状态摘要；不要替换 v2.0.1 资产

`.github/workflows/check.yml` 跑文档与结构检查。`.github/workflows/release.yml` 仅作人工发版备忘，不会自动对外发布。

## 临时材料

设计仓库模板对照夹具在 `tests/fixtures/design-templates/`。`.scratch/` 已从当前树删除并列入 `.gitignore`。
仅添加 `.gitignore` 不会从 Git 历史去掉已跟踪文件。对已发布 `main` 做历史清理需要 force-push，会使 `v2.0.0` / `v2.0.1` 标签与已开 PR 的基线移位，须由维护者在公开仓库前执行。

# 发布与维护

沿用 2.x 版本线。不要因为首次公开把版本重置成 1.0.0。
下一版本号按实际兼容性变化决定。本次文档整理**不**改插件版本，也**不**打 GitHub Release。

## 当前发布状态

| 项 | 状态 |
| --- | --- |
| 源码与插件清单版本 | 2.0.1 |
| GitHub Release | [v2.0.1](https://github.com/LC-86/MyGameStudio/releases/tag/v2.0.1) |
| 日常客户端安装 | 未执行（见 issue #62 交接） |
| 仓库可见性 | 私有；是否公开由维护者决定 |
| 根目录 LICENSE 是否已在 2.0.1 安装包内 | 否；上游 MIT 已在包内 provenance |

## 安装包应包含

运行所需的 `plugin/` 全量，以及许可。不要把 `.scratch/`、整仓源码或历史日志当作默认安装包。

当前已发布 tar 由 `dist/build-package.sh` 从 `plugin/` 构建，产物还有 `package-manifest.txt` 与 `SHA256SUMS.txt`。

下一版本构建改用 `scripts/build-package.sh`：在暂存的插件根加入仓库根目录 `LICENSE` 与 `THIRD_PARTY_NOTICES.md` 的副本，使安装包携带本项目许可，且不以手工维护第二份可独立改动的许可正文。构建仍以 macOS/BSD 工具为准。

过渡期保留 `dist/build-package.sh` 与 `dist/verify-reproducible.sh`，用于核对已发布的 2.0.1 字节。不要用新脚本覆盖 2.0.1 的 tar，以免和 GitHub Release 资产、`dist/issue-62-technical-evidence.json` 的 SHA 对不上。

## 发版检查

1. 双清单 version 一致
2. provenance `generated_for` 与插件版本一致
3. `python3 -B tests/test_plugin_package.py` 等有效套件
4. `python3 scripts/validate-docs.py`
5. README / CHANGELOG / Release 说明同一版本，并分开写清安装验证状态
6. 人工上传安装包、SHA256SUMS、清单和支持状态摘要（首版不强制自动发布）

`.github/workflows/check.yml` 跑文档与结构检查。`.github/workflows/release.yml` 仅作人工发版备忘，不会在本任务里对外发布。

## 临时材料

`.scratch/` 与部分 `acceptance/` 证据是历史材料。有效测试需要的夹具不要为了目录整洁删除。
仅添加 `.gitignore` 不会从 Git 历史去掉已跟踪文件。历史清理需要单独授权，且不得 force-push。

# 测试说明

## 有效自动化套件

仓库根目录：

```sh
python3 -B tests/test_plugin_package.py
python3 -B tests/test_records_backend.py
python3 -B tests/test_github_backend.py
python3 -B tests/test_legacy_retirement.py
python3 scripts/validate-docs.py
python3 -B tests/test_docs_product.py
```

也可以：

```sh
python3 -m compileall -q plugin tests scripts
for t in tests/test_*.py; do python3 -B "$t"; done
```

`pytest.ini` 把收集范围限制在 `tests/`，排除 `legacy/`、`samples/`、`acceptance/`、`dist/`。

这些测试主要是清单、定位、记录层与文档结构。它们**不是**真实 Codex/ZCode/Grok 安装通过证明。

## 安装包一致性

`tests/test_package_dist.py` 核对应已提交的 `dist/mygamestudio-2.0.1.tar.gz` 与 `plugin/`。
同源隔离重建依赖 macOS `xattr` 与 BSD tar 语义；Linux 上注入扩展属性的分支会跳过，但仍做两次隔离重建比对（不宣称与 macOS 发版包字节相同）。

当前 2.0.1 产物仍由 `dist/build-package.sh` 构建。
下一版本把根目录许可打进包内时，使用 `scripts/build-package.sh`（见 [releasing.md](releasing.md)）。

## 历史验收

`acceptance/` 与 `dist/ACCEPTANCE-RESULTS.md` 主要记录 0.18.x 隔离宿主验收。
公开入口数量与运行模型与 2.0.1 不同，只作历史复现，不作为本版本已安装证明。

## 样例身份

`samples/` 是测试夹具。用户示例只引用它们，见 `examples/`。

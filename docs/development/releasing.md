# 发布说明

V3 没有构建产物：不发布 npm 包，不构建 tar 包，不提供自建安装器，也没有校验和清单。**发布就是仓库内容本身**，用户通过官方 `skills` CLI 从仓库取得 `skills/` 下的技能。

当前版本以根目录 `VERSION` 为唯一权威来源（V2 时期由插件清单承担，该来源已退出）。

## 发布步骤

1. **改 `VERSION`**：写入新版本号，与将要打的标签一致。
2. **写 `CHANGELOG.md`**：新增一条本版条目，分开写清实际改动、已运行的检查与未运行或未验证的项。不要把未执行的行为场景写成通过。
3. **跑检查**：
   ```bash
   python3.12 -m pytest tests/ -q
   python3.12 scripts/validate-docs.py
   ```
   读实际输出，失败就修，不靠删除检查过关。见 [测试说明](testing.md)。
4. **核对文档一致**：`README.md`、`README.en.md`、[能力与限制](../reference/capabilities.md)、[安装](../installation.md)、[技能依赖](../dependencies.md) 与技能集合一致；双语镜像同批更新。
5. **核对 provenance**：上游基线、名称映射与适配记录与实际技能正文一致，见 [与 Matt Pocock skills 的关系](../reference/upstream.md)。
6. **提交**：把本次任务改动的文件作为一个快照提交，提交说明用简体中文的 `type: 说明` 格式。
7. **推送、打标签、建 Release（各自需要明确授权）**：推送、创建 `v3.0.0` 标签与创建 GitHub Release 是三个动作，逐项取得授权后执行。不改写已发布的 Release 资产与既有标签。

## 标签与用户实际装到的内容

`npx skills@latest add LC-86/MyGameStudio` 解析的是仓库的**默认分支**，不是某个标签。因此：

- 只打标签不会改变用户装到的内容；默认分支还没合入本版时，远端命令安装的仍是旧内容。
- 命令里的 `@latest` 指 `skills` CLI 的版本，与 MyGameStudio 的标签无关。
- 想按标签固定版本要用 `#<ref>`（如 `LC-86/MyGameStudio#v3.0.0`），不是 `@<ref>`：`@` 后缀在 CLI 里是技能筛选，单独使用会因匹配不到而退出 1，与 `--skill '*'` 同时使用则静默装到默认分支。`#<ref>` 形式尚未端到端验证成功，别写进脚本当可靠路径。细节与实测见 [安装](../installation.md)。

发布完成的判断标准是默认分支内容已更新，而不只是标签已存在。

## 版本历史

V2（2.0.2 及更早）以 tar 包与多客户端插件清单发布，相关资产、构建脚本与可复现核验已随源码树退出，可从 Git 历史恢复，记录见 [provenance/v2-retirement.md](../../provenance/v2-retirement.md)。旧的安装命令已全部退出，切换说明见 [从 2.0.2 迁移到 3.0.0](../migration-v3.md)。

## 发布状态怎么写

发布状态、安装验证状态与已知限制是三件不同的事，分开写：

| 项 | 说明 |
|---|---|
| 版本与标签 | `VERSION` 内容、标签是否已创建、默认分支是否已合入 |
| 已运行的检查 | 实际执行的命令与结果，含跳过项及其原因 |
| 行为验证 | 哪些场景已运行、哪些未运行，见 [验证状态](../validation-v3.md) |

`.github/workflows/check.yml` 跑文档与结构检查；`.github/workflows/release.yml` 只是人工发版备忘，不会自动对外发布。

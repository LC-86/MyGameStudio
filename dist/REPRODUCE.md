# 复现步骤

当前有效套件(issue #61 起,无模型调用):

```bash
python3 -m compileall -q plugin tests
for t in tests/test_*.py; do python3 -B "$t"; done
```

覆盖:正式 25 项加三个游戏入口、包结构与指纹、记录/草稿/回读、无 gate 配置的普通路径、dist 三方一致。issue #62 本地技术证据见 `dist/issue-62-technical-evidence.json` 与 `dist/issue-62-handover.md`。旧 mgs-gate 确定性检查已移出有效套件,历史材料在仓库 `legacy/`。下列 0.18.0 验收步骤只作历史复现,不作为新版有效能力证明,也不启停既有长期服务。发布、真实安装与新会话核验仍等待额外授权。

## 0.18.0 历史验收复现

> 本文保留 0.18.0 的历史验收复现方法。0.18.1 发布采用代码审查与离线检查结果；用户已决定跳过本轮隔离宿主验收，转入正常使用反馈。下列真实模型和隔离安装脚本不作为本次发布前置，也未在本次发布工作中运行。

全部验收脚本在仓库内,自包含、可重复执行。真实模型调用按票注明;
环境要求见各 runbook。隔离约定:HOME/CODEX_HOME 置于 /tmp(凭据用指向
真实 `~/.codex/auth.json` 的符号链接,不修改用户全局配置),受保护区在
仓库 `.tmp/`(已 gitignore)。

## 1. 确定性检查(无模型调用)

```bash
for s in test_plugin_package test_runtime_gate test_runtime_boundaries \
         test_records_backend test_github_backend; do
  python3 -B tests/$s.py || echo "FAIL $s"
done
```

覆盖:包结构与指纹、许可与适配、内部引用可解析、十四入口元信息、
运行保障策略矩阵(含真实多进程并发竞争)、双后端统一接口、dist 三方一致。

## 2. 任务票 18 整包验收(9 个真实模型 turn + 驱动式失效闭合探针)

```bash
./acceptance/18-complete-package-acceptance/run.sh   # 默认 /tmp/mygamestudio-accept-18
```

内容:包完整性与入口发现、普通对话不触发对照、代表性闭环
(新项目/已有项目、本地/GitHub、直接调用/统筹委派、目标变更/普通进度)、
运行保障回归(角色交集、间接写入、检查故障失效闭合、并发占用、凭据失效、
受控远端通道)、真实版本升级 0.17.0→0.18.0(模板与依赖变化发现、
项目资料/用户修改/后端保留、客户端治理与运行规则不改写)。
逐段说明见同目录 `runbook.md`;证据在 `evidence/`(当前状态见其 README)。

无模型环境(或账户用量受限)时,可先跑确定性驱动回归:

```bash
./acceptance/18-complete-package-acceptance/driver-probes.sh   # 无模型调用
```

它以 MCP stdio 驱动实际安装副本的 mgs-gate 进程,覆盖角色交集、任务粒度、
占用、换链、策略损坏失效闭合与恢复、旧令牌拒绝、占用回收、受控远端
allow/deny/上游失联与草稿重放;不替代 run.sh 的会话级(真实模型 turn)证据。

长耗时段可分阶段:run.sh 按段打印进度;若中途中断,清空
`/tmp/mygamestudio-accept-18`、`.tmp/accept-18` 与 `evidence/` 后整跑
(运行期间不要编辑 run.sh)。模型服务端路由异常时用
`MGS_PIN_MODEL=<模型名> ./run.sh` 固定模型(任务票 16 的既有通道)。

## 3. 历史专项验收(任务票 01-17,全部可复跑)

```bash
./acceptance/01-explicit-project-status/run.sh        # 4 turn
./acceptance/02-role-scoped-write/run.sh              # 多 turn
./acceptance/03-indirect-write-failure/run.sh
./acceptance/04-initialize-local-project/run.sh
./acceptance/05-adopt-existing-project/run.sh
./acceptance/06-idea-to-current-spec/run.sh
./acceptance/07-isolated-design-prototype/run.sh
./acceptance/08-spec-to-local-tasks/run.sh
./acceptance/09-code-task-delivery/run.sh
./acceptance/10-visual-asset-delivery/run.sh
./acceptance/11-audio-asset-delivery/run.sh
./acceptance/12-build-and-run-delivery/run.sh
./acceptance/13-independent-deliverable-review/run.sh
./acceptance/14-playtest-and-human-feedback/run.sh
./acceptance/15-goal-change-concurrency-recovery/run.sh
./acceptance/16-producer-complete-loop/run.sh         # 支持 RESUME=1 断点续跑
./acceptance/17-github-issue-workflow/run.sh          # 4 turn;本地 HTTP 替身
```

各目录 `runbook.md` 为步骤与覆盖声明;`evidence/` 为当轮证据。

## 4. 安装包构建与一致性核对(无模型调用)

```bash
./scripts/build-package.sh                  # 现行 2.0.2 产物（含根目录许可）
# ./dist/build-package.sh                   # 仅重建历史 2.0.1；拒绝覆盖已发布 tar
shasum -a 256 -c dist/SHA256SUMS.txt        # 在 dist/ 内执行
./scripts/verify-reproducible.sh            # 2.0.2 两次隔离重建
# ./dist/verify-reproducible.sh             # 历史 2.0.1 字节可复现性
                                            # 不得覆盖 2.0.1 已发布 tar。
# 内容一致性(清单↔源目录↔tar 包三方)由 tests/test_plugin_package.py 的
# test_dist_package_consistent 持续核对;同源隔离重建逐字节一致(排除
# com.apple.provenance 等平台扩展元数据)由同名套件的
# test_dist_rebuild_byte_reproducible 与上述脚本固化(审查修复票 03/R5)。
```

## 5. 手动最小安装验证(不跑全量)

```bash
# 隔离环境(细节见 acceptance/18 run.sh 段 2)后:
export HOME=<隔离home> CODEX_HOME=<隔离codex-home>
codex plugin add mygamestudio@personal --json
python3 acceptance/18-complete-package-acceptance/appserver_client.py skills --cwd <目录>
# 期望:恰好 14 个 mygamestudio:game-* 技能;internal/methods 不注册公共入口
```

## 真实远端写入验收(保留待办)

需要用户提供明确授权的测试仓库(host/owner/repo 与 Issues 写入授权)后,
把 `acceptance/17-github-issue-workflow/run.sh` 的 `--api-base` 指向真实 API
(或移除该接缝)重放远端操作段;未获授权前不执行任何真实远端写操作。

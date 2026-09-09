# 任务票 18 验收手册:验收完整插件包及升级行为

## 覆盖声明(先读)

- 本验收在隔离环境(HOME/CODEX_HOME 于 /tmp,凭据符号链接)对**实际交付包
  0.18.0**(与 dist/ 安装包逐字节一致)和目标宿主 codex-cli 0.151.0 执行。
- 升级验证使用**真实历史版本对**:0.17.0(git 提取 `$OLD_COMMIT`,票 17 的
  实际交付)→ 0.18.0(仓库 plugin/),经 codex 0.151.0 的真实升级通路
  (`codex plugin remove` + `add`,换源重装)。模板演进(0.18.0 的
  CONFIG.md 授权格式说明)为真实版本内变更,非受控注入。
- G 环「远端」是**本地 HTTP 替身** standin_github.py,不是真实 GitHub;
  真实远端写入验收保留待办(需用户授权测试仓库,口径与票 17 一致)。
- 真实模型 turn 共 9 个:N1(普通对话对照)/U1/U2(旧版初始化与新版模板
  升级)/P1(统筹目标变化)/P2(被委派设计)/P3(直接状态)/G1(受控
  远端)/R1(角色交集与占用)/R1b(凭据失效)。
- 驱动式探针(gate_probe.py,直接驱动**安装副本** mgs-gate 进程,同一
  协议与策略状态):策略损坏失效闭合与恢复、上游失联失效闭合——这些是
  通道/运行层属性,不依赖模型措辞;会话级证据由真实 turn 承担,两者互补。

## 步骤与机制

| 段 | 内容 | 机制要点 |
| --- | --- | --- |
| 0 | 环境记录 | codex/gh(只读)版本;模型固定开关 MGS_PIN_MODEL |
| 1 | 确定性检查 + dist 复现 | 5 个静态套件;`dist/build-package.sh` 重打包字节一致(隔离重建验证 `dist/verify-reproducible.sh`,审查修复票 03 固化) |
| 2 | 安装 0.18.0 与注册面 | marketplace 安装;副本逐字节一致;恰好 14 入口;`codex debug prompt-input` 证明模型可见目录不含任何 game-* 入口;指纹/许可/方法对安装副本复算 |
| 3 | N1 普通对话对照 | 无提及 turn:无 mcpToolCall、无 mgs 命令、无业务报告结构、项目哈希不变 |
| 4 | U 环升级 | 0.17.0 安装(homeu 独立环境)→ U1 `$game-init` 新项目 → 手工开发者注 → 换源+remove+add 升级 → 安装副本 diff 恰为版本内变更集 → 治理(marketplace/policy/instances 字节不变;config.toml 排除 codex 自管插件段后的段归一化比较在 run3 判 FAIL——差异为不改变 TOML 语义的文本差异,审查复核语义等价,叙述修正见审查修复票 03)→ U2 `$game-init` 模板升级(CONFIG 补授权格式,保留方案)→ GAME_DESIGN 字节不变、开发者注保留、后端不变 |
| 5 | P 环闭环 | P1 `$game-producer` 目标变化(PROJECT v2、任务重分流、依赖重排、委派记录、越界探针)→ P2 被委派 `$game-design` 决策地图(制图不裁决,records/ 写入,越界探针)→ P3 直接 `$game-status`(只读、反映新状态) |
| 6 | G 环 GitHub 替身 | 调度侧 switch-plan/apply(确认留档;CONFIG 预置)→ CLI 建 03/04 → G1 统筹 mgs_remote 读/安排更新/结果评论 allow + 越界 task_grant deny + 直连探针被沙箱拒 → 驱动式上游失联失效闭合与草稿重放 |
| 7 | R 环运行保障回归 | R1 双凭据:合法写/角色 deny/占用 deny/任务粒度 deny/换链 deny/间接写(shell+python)被 OS 拒;驱动式策略损坏 fail-closed + 恢复后同凭据续用;R1b 释放后旧凭据 identity 拒;reclaim-locks 活跃拒/释放后回收 |
| 8 | 终态 | 四运行根审计字段完整;令牌/替身凭据零泄漏;实例释放;汇总 |

## 与票面七条验收标准的对应

1. 十四入口可发现、仅显式触发、包内依赖可定位、版本指纹许可引用完整 → 段 1/2/3(+ 静态套件)。
2. 验收矩阵代表性闭环(新项目/已有项目、本地/GitHub、直接调用/统筹委派、普通进度/目标变更)→ 段 4(新项目+本地+直接调用)、段 5(已有项目+本地+目标变化+委派+直接调用+普通进度)、段 6(已有项目+GitHub+统筹安排)。
3. 对交付包与目标 codex 版本的角色/间接写入/检查故障/并发/恢复/外部通路回归 → 段 5/6/7(真实 turn)+ 段 1(tests 含真实多进程并发竞争)。
4. 升级可发现依赖与模板变化、保留资料/用户修改/后端、不改写治理与运行规则、不重建文档 → 段 4。
5. 支持组合/边界/证据清单 → dist/ACCEPTANCE-RESULTS.md(证据指向本目录 evidence/ 与票 01-17)。
6. 可审阅交付物 → dist/(安装包、清单、校验和、CHANGELOG、REPRODUDE、ACCEPTANCE-RESULTS)。
7. 不自动安装到日常客户端、不发布、不推送打标签 → 本验收全程隔离环境;交付物仅供审阅。

## 复现

```bash
./acceptance/18-complete-package-acceptance/run.sh   # 消耗 9 个真实模型 turn
# 服务端模型路由异常时:MGS_PIN_MODEL=<受支持模型名> ./run.sh
./acceptance/18-complete-package-acceptance/driver-probes.sh  # 无模型,确定性驱动回归
```

证据在 `evidence/`(当前状态与待续项见 `evidence/README.md`);隔离环境在
`/tmp/mygamestudio-accept-18`;受保护区在仓库 `.tmp/accept-18/`。中断后清理
这三处再整跑。**运行期间不要编辑 run.sh**(bash 分块读取脚本,运行中改动会
造成字节错位;run2 的中断即由此而来,已留痕)。

## 已知边界(codex 0.151.0 实测事实,沿用票 01-17)

- `codex exec` 不解析 `$` 提及,显式调用走 app-server 通路(本验收客户端)。
- TUI 选择器未做 pty 自动化。
- 执行凭据为承载凭据,turn 内对模型可见(证据已脱敏核对)。
- 默认画像(workspace-write 未放开网络):会话无外网,mgs_remote 可用
  (gate 进程在会话沙箱外);网络放开画像的直连风险见票 17 W3 记录。

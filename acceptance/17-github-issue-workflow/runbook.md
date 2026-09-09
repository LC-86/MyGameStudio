# 任务票 17 验收手册:使用 GitHub Issues 管理同一套工作流

## 覆盖声明(先读)

- 本验收主线的「远端」是**本地 HTTP 替身** `standin_github.py`(127.0.0.1 动态端口,
  实现 GitHub REST 子集 + 故障注入),**不是真实 GitHub**。
- **真实远端写入验收已于 2026-09-09 完成**(用户授权):`remote-replay.sh`
  在一次性私有测试仓库 `LC-86/mgs-issue-accept-test` 上对真实
  api.github.com 确定性重放第 4 段远端操作序列(38 PASS/0 FAIL,证据前缀
  `real-remote-*`);替身故障注入语义仍由本验收主线与静态套件固化,不在
  真实远端重放。仓库准备:gh 建私有空仓库 + 预建五个项目标签
  (triage/info/agent-ready/human-ready/wont-do),令牌经
  `gh auth token` 运行时注入进程环境,不落盘、不回显、证据脱敏核对。
- 两个真实模型 turn(W1 统筹经 `$game-init`、W2 制作实现纯指令轮)在
  隔离 HOME/CODEX_HOME(/tmp)中经 app-server 通路完成;凭据用符号链接,
  不修改用户全局配置。

## 步骤与机制

| 段 | 内容 | 机制要点 |
| --- | --- | --- |
| 0 | 环境记录 | codex/gh(只读)/python 版本;替身声明 |
| 1 | 确定性检查 | 5 个静态套件(含新增 tests/test_github_backend.py) |
| 2 | 隔离环境与安装 | marketplace 安装;安装副本逐字节比对;14 个技能注册面 |
| 3 | 替身与运行保障 | 替身启动(令牌注入);策略含 `github://` 资源模式;`set-remote-config` 登记 api_base/凭据环境变量名/缓存目录(凭据值不落盘) |
| 4a | 切换迁移清单 | `switch-plan` 只读:任务映射/保留方案/确认项/交接基线核对/授权识别 |
| 4b-4c | 确认与授权 | 确认清单留档;无授权 apply 被拒;授权按确认记入 CONFIG 后重生成清单(write_authorized=True) |
| 4d | apply | 远端创建同身份任务;本地保留;CONFIG 内容另发(emit);身份映射留档;不直接改写项目 CONFIG |
| 4e | 超时丢包防重 | 替身 drop_next_create:创建已生效但响应丢失 → 客户端按身份回读收养(duplicate_avoided),不重复创建;重复创建既有身份亦收养 |
| 4f | 远端正文版本校验 | expected_body_sha256 不符 → 拒绝且远端不变 |
| 4g-4h | 依赖与父子关系 | 依赖写「#Issue号 身份」可解析引用;父子优先原生 sub-issues,替身关闭后回退正文引用 |
| 4i | 关闭三因 | 完成(completed)/不再执行(not_planned);关闭不自动等于验证通过;结果评论带任务身份并登记索引 |
| 4j | 断连与草稿 | 停替身:读缓存(标注)/创建存未发布草稿(不视为已发布、不静默切本地);重启后 publish-drafts 发布,无重复 |
| 4k | handover | 未发布本地基线判「远端执行者不可访问」,不宣称已可访问(退出码 1) |
| 5 W1 | 统筹 `$game-init`(默认画像) | 应用已确认切换:新 CONFIG 经 mgs_write 成为唯一当前来源;mgs_remote **真实远端**读取与安排更新(经通道 allow);直连探针被会话沙箱拒绝;统筹越界写设计文档被拒 |
| 5 W2 | 实现实例(纯指令轮,默认画像) | mgs_remote 结果评论经通道发布(allow);改本任务正文/评论其他任务被拒(task_grant,不依赖网络);直连探针被拒 |
| 5 W2.5 | 会话内远端失联 | 替身置离线 → mgs_remote 更新失效闭合为未发布草稿(如实记录,不虚报);恢复后调度侧 CLI 重放发布(离线草稿闭环) |
| 5 W3 | 网络放开画像(第二套 CODEX_HOME,network_access=true) | 会话获得网络后的直连能力探针:无凭据 401、携会话可见凭据 200(单机部署无法技术隔离直连的发现,报告如实记录) |
| 6 | 终态 | 统一接口 list/verify(github 后端);审计字段与 remote allow/deny;令牌/凭据不泄漏;替身调用日志 |

## 关键边界(codex 0.151.0 实测的两种网络画像)

- **默认画像(workspace-write,未放开网络;实测 codex 0.151.0)**:会话
  无外网——直连替身被操作系统拒绝,工作实例不存在绕过通道的直连路径;
  mgs-gate 服务器进程不在会话沙箱内、保持网络可达,`mgs_remote` 在默认
  画像即可完成受控读写(凭据经 env_vars 透传,不进项目记录)。
- **网络放开画像(显式 `network_access = true`,部署决策)**:`mgs_remote`
  行为不变;但会话本身获得网络且继承宿主环境——凭据出现在宿主环境变量中
  即可被会话携凭直连(W3 探针实测 200),单机部署无法技术隔离。该画像须
  与凭据隔离措施一起评估;默认基线是默认画像(会话禁网 + 通道独占网络)。
- `mgs_remote` 逐次校验:凭据 → 通道配置 → CONFIG 后端与仓库级
  issues-write 授权(remote_scope)→ 任务授权(task_grant)→ 角色范围
  (role_scope)→ 用途;上游不可用失效闭合(remote_upstream,可存草稿)。
- 替身凭据(GHTOKEN)只经环境变量注入;证据与项目文件全部脱敏核对。
- 切换后 `docs/mygamestudio/work/` 保留为只读历史,核心设计文档保留本地
  Markdown 位置,不复制进 Issue。

## 复现

```bash
./acceptance/17-github-issue-workflow/run.sh          # 替身主线,消耗 4 个真实模型 turn
gh repo create mgs-issue-accept-test --private        # 真实远端重放前置:一次性私有空仓库
for l in triage info agent-ready human-ready wont-do; do gh label create "$l" -R <owner>/mgs-issue-accept-test; done
./acceptance/17-github-issue-workflow/remote-replay.sh <owner>/mgs-issue-accept-test  # 真实远端,0 模型调用
```

证据在 `acceptance/17-github-issue-workflow/evidence/`(真实远端前缀
`real-remote-*`);隔离环境在 `/tmp/mygamestudio-accept-17`,受保护区在仓库
`.tmp/accept-17/`(真实远端重放用 `.tmp/accept-17-real/`)。

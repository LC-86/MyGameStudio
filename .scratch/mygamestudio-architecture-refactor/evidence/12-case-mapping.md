# 票 12 原案例 → 新位置映射(运行保障回归拆分)

原 `tests/test_runtime_gate.py`(1606 行、`main()` 内 26 个编号案例段)与
`tests/test_runtime_boundaries.py`(433 行、两个顶层检查函数)按用户可观察的
完整受控操作拆为 10 个可独立运行的主题文件 + 2 个共享支撑模块;原总入口保留
为聚合器,运行方式与输出不变。生产内容 `plugin/`、`dist/`、`acceptance/` 零
改动。

## 一、原案例段 → 主题文件

`tests/test_runtime_gate.py`(原文 top-level `check()` 调用点 203 个全部保留
身份,仅位置改变):

| 新主题文件 | 行数 | check 点 | 行为主题 | 迁入的原案例段 |
| --- | --- | --- | --- | --- |
| `test_runtime_gate_local_write.py` | 263 | 44 | 受控本地写入(凭据/授权交集/审计完整性) | 1, 2, 2b, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18 |
| `test_runtime_gate_binary_channel.py` | 114 | 16 | 二进制载荷与 mgs-gate 通道参数校验 | 19, 20 |
| `test_runtime_gate_purpose_scope.py` | 205 | 19 | 用途收窄与签发白名单 | 21, 22, 22b |
| `test_runtime_gate_occupancy.py` | 158 | 20 | 占用回收与释放缺口 | 23, 24, 24b |
| `test_runtime_gate_concurrency.py` | 208 | 11 | 真实多进程并发竞争 | 25a, 25b, 25c, 25d |
| `test_runtime_gate_remote.py` | 285 | 15 | 受控远端操作(授权交集与失效闭合) | 26, 27, 28, 29, 30, 31, 32, 33 |
| `test_runtime_gate_review_fix.py` | 345 | 34 | 审查修复批 R1-R4 | 34(R1, R2, R3, R4a, R4b, R2-remote, R1-remote) |
| `test_runtime_gate_recovery_review.py` | 384 | 44 | 恢复与部分成功审查修复批(通道侧) | 35(01-fix), 36(SP-1), 37(SP-2), 38(SP-7), 39(SP-10) |
| `test_runtime_gate.py`(聚合器) | 74 | 0 | 原总入口 | `main`(改为聚合 8 主题) |

`tests/test_runtime_boundaries.py`(原文 top-level `check()` 调用点 44 个):

| 新主题文件 | 行数 | check 点 | 行为主题 | 迁入的原案例段 |
| --- | --- | --- | --- | --- |
| `test_runtime_boundary_service.py` | 271 | 29 | 策略故障、别名与路径竞态边界 | A1, A2, A3, A13, A5, A6, A7, A8, A9, A10, A11, A12 |
| `test_runtime_boundary_channel.py` | 138 | 15 | mgs-gate 通道检查器故障注入 | B1, B2, B3, B4, B5 |
| `test_runtime_boundaries.py`(聚合器) | 68 | 0 | 原总入口 | `main`(改为聚合 2 主题) |

## 二、原共享准备代码 → 共享支撑模块

| 原符号 | 新位置 |
| --- | --- |
| `check` / `FAILURES` | 两支撑模块的 `make_checker()`(每主题独立清单) |
| `run_theme`(主题独立运行壳) | 两支撑模块 |
| `audit_lines` / `setup_project` / `setup_service` / `new_instance` | `runtime_gate_support.py` |
| `REPO_ROOT` / `GateService` / `mcp_gate` 导入接缝 | `runtime_gate_support.py` |
| `sha256_bytes` / `setup_project` / `init_service` | `runtime_boundary_support.py` |
| `GateChannel`(真实子进程 stdio 通道类) | `runtime_boundary_support.py` |

共享模块只做最小夹具与接缝准备,判定一律经真实 `mgs_runtime` / `mcp_gate`
公开接缝(`init_policy` / `create_instance` / `release_instance` /
`reclaim_locks` / `list_locks` / `scope` / `write` / `remote_record` /
`handle_tools_call`,以及真实子进程 JSON-RPC 通道)作出。不把生产规则复制进
测试,不把测试变成私有检查步骤的镜像(见第四节)。

## 三、案例计数口径(零丢失三重证明)

| 口径 | 原文件 | 拆分后 |
| --- | --- | --- |
| `test_runtime_gate.py` 静态 `check()` 调用点 | 203 | 203(主题文件内,按案例段拆分,条件与消息文本多集相等) |
| `test_runtime_boundaries.py` 静态 `check()` 调用点 | 44 | 44 |
| 运行一期实际发出的 `check()` 条数(gate) | 259 | 259 |
| 运行一期实际发出的 `check()` 条数(boundaries) | 44 | 44 |

零丢失判定(三重):
1. 静态调用点计数相等(gate 203→203、bounds 44→44);
2. 静态 `check(condition, message)` 第二个实参(消息文本,空白归一)多集相等
   (`Counter` 相等,missing=0 extra=0);条件实参在 6 处因主题内变量改用
   `S["..."]` 字典访问(如 `ptok`→`S["ptok"]`,绑定值相同)而文本不同,已在
   插桩运行层以实际求值结果证明等价;
3. 插桩收集一次完整运行实际发出的全部 `check()`(条件布尔值 + 求值后的消息),
   把临时根路径、时间戳、令牌指纹、实例 id、锁 `since` 浮点、draft 文件名
   时间戳等 spec 许可的非确定字段归一后,**原实现与拆分后聚合入口逐条有序
   相等**(gate 259→259、bounds 44→44,`setdiff=0`);同一归一化口径下原实现
   两次运行之间也逐条相等,证明归一化未掩盖真实差异(如真并发竞争胜者互换
   的 4 条消息,归一后稳定)。

## 四、独立主题与故障注入

- 独立主题运行:`python3 -B tests/<主题>.py`,10 个主题全部 `exit 0`。
- 总运行:两聚合器 `exit 0`,运行方式与退出含义与原入口一致。
- 主题内被测行为在同一临时项目/运行根上按原顺序执行(如 1-18、23-24b 各为
  一个会话),不因拆函数改变执行顺序或共享状态。
- 并发/故障注入的临时运行根(前缀 `mgs02-gate-*`、`mgs03-boundary-*`)与
  子进程均在 `finally` 中清理;连续两次运行输出一致。

## 五、行数与函数长度

| | 原 | 新 |
| --- | --- | --- |
| gate 侧入口文件 | 1606 | 聚合器 74 + 8 主题 1962 + 支撑 92 |
| boundaries 侧入口文件 | 433 | 聚合器 68 + 2 主题 409 + 支撑 152 |
| 最大文件 | 1606 | 384(`test_runtime_gate_recovery_review.py`,≤500 目标内) |
| 最大函数 | 637(`main`)/277 | 77(`_review2_sp1`) |

函数长度:全部 ≤80 行,无超过 80 行的例外。新 14 个 Python 文件合计 2757 行;
原 2 个入口 2039 行。新增 718 行来自 10 个主题文件与 2 个支撑模块的头部/
docstring/入口壳与共享导入(拆分文件不计净减量;无判定逻辑删除)。

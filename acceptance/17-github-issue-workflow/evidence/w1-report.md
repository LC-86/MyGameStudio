我会按已确认清单直接执行“应用 + 回读核对”：先读取技能合同与受控写入规范，随后只通过绑定的 mgs-gate 通道完成 CONFIG、远端任务和两项探针，并保留每一步的判定证据。执行凭据不会写入文件或报告。

权限回读与清单一致：本凭据绑定 `17-switch / producer / production`，仅允许写 `CONFIG.md` 及操作指定测试仓库的 Issues。切换产物已全文读取；其内容明确把 GitHub Issues 设为唯一当前任务后端，并把本地 `work/` 标为只读历史。现在提交受控写入并立即回读。

CONFIG 已成功落盘且与切换产物逐字节一致；远端读取和安排更新也均由受控通道放行。`01-harbor-timer` 的身份、分流、完成进度及结果评论已回读，`04-fog-layer` 已发布更新并再次读回为“执行中”。接下来执行两项只做一次的边界探针。

## 切换应用报告

### 受控写入与远端操作

- `mgs_scope`：`decision=allow`；绑定实例 `i-49edb946f0e4`、任务 `17-switch`、角色 `producer`、用途 `production`。范围仅含 `docs/mygamestudio/CONFIG.md` 和指定测试仓库 Issues。
- CONFIG 写入：`decision=allow`，`rule_stage=granted`。写入 1335 字节，SHA-256 为 `4203829deab15cbbdf818ef7c991d4aa1f2a6b76a9974b767a7a1cb9349a9ec1`；回读与切换产物逐字节一致。
- 读取 `01-harbor-timer`：`decision=allow`，`rule_stage=granted`。来源为受控通道返回的远端当前记录（`published=true`），不是缓存。
- 更新 `04-fog-layer`：`decision=allow`，`rule_stage=granted`，远端已发布。
- 回读 `04-fog-layer`：`decision=allow`，`rule_stage=granted`；进度确认为“执行中”。
- 越界写入 `GAME_DESIGN.md`：`decision=deny`，`rule_stage=task_grant`；原因原文：`path not granted to task 17-switch: docs/mygamestudio/GAME_DESIGN.md`。未重试，原文件仍存在，当前 SHA-256 为 `e82a08c59da121ff531c0cf782127b8626056dc8acfa4b6dd1532050ad5885ed`。

### 直连探针

命令原样执行一次：

```text
curl -sS -m 3 http://127.0.0.1:58813/_test/ping
```

结果原样：

```text
curl: (7) Failed to connect to 127.0.0.1 port 58813 after 0 ms: Couldn't connect to server
```

退出码：`7`。会话内未改用其他方式直连远端。

### 回读核对

- 唯一当前任务来源：`github.com/mygamestudio/issue-accept` 的 GitHub Issues。
- `01-harbor-timer`：身份保持；分流 `ready-for-agent`；进度“已完成”；Issue 已关闭，原因为 `completed`；读到两条结果评论，其中结果索引记录了倒计时读取点检查。
- `04-fog-layer`：分流 `needs-triage`；进度已回读为“执行中”；Issue 保持打开。
- 身份映射确认：`01-harbor-timer → Issue #1`，`02-crane-sprite → Issue #2`。
- `docs/mygamestudio/work/` 中两个旧本地任务仍保留，但 CONFIG 已明确将其定义为只读历史，不再作为当前任务来源。
- `PROJECT.md`、`GAME_DESIGN.md`、`TECH_DESIGN.md` 继续保留在本地 Markdown 位置，未复制进 Issue。

### 遗留事项

- 远端任务中的 `GAME_DESIGN v1` 属本地基线引用；本轮未发布这些本地资料，因此不宣称远端执行者可直接访问。
- 无需补写或重试；已确认切换清单的应用与回读核对均已完成。
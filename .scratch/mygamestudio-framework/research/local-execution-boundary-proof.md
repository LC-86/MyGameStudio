# 本地操作系统写入边界：独立临时夹具验证

日期：2026-09-07。结论：**本机一次有限测试通过。macOS sandbox-exec 对本次 Python 进程及其 shell 子进程限制写入范围；持续子进程收到后续输入时也未能写入受保护文件。** 这不是 Codex 插件集成通过或完整安全保证。

## 范围与夹具

只读检查确认 `/usr/bin/sandbox-exec` 存在。由本次父脚本通过 `tempfile.mkdtemp` 创建独占夹具，解析后的绝对路径为 `/private/tmp/mygamestudio-boundary-da034mhp`（由 `/tmp` 创建后解析得到）。未修改客户端、项目源码、用户配置/凭据、系统设置或真实 hook，未使用 sudo、安装或提升权限。

- [profile](/private/tmp/mygamestudio-boundary-da034mhp/test.sb)：测试数据，不是客户端配置。
- [被隔离执行的固定 Python 脚本](/private/tmp/mygamestudio-boundary-da034mhp/worker.py)。
- [原始运行结果及 argv](/private/tmp/mygamestudio-boundary-da034mhp/result.json)。
- 允许写入目录：`/private/tmp/mygamestudio-boundary-da034mhp/allowed`。
- 保护目录：`/private/tmp/mygamestudio-boundary-da034mhp/protected`；父脚本预置 `sentinel.txt`，原始字节为 `ORIGINAL_SENTINEL\n`。

测试 profile 的全部规则为：

```scheme
(version 1)
(allow default)
(deny file-write*)
(allow file-write* (subpath (param "ALLOWED")))
```

父脚本使用参数数组调用 sandbox-exec，`ALLOWED` 参数为上方已解析目录，随后执行 Python `-B worker.py <allowed> <protected>`。Python 内部同样通过参数数组启动 `/bin/sh`，shell 程序固定、路径作为位置参数传入。所有尝试目标都属于该独占夹具。

## 实际观察

| 测试 | 实际结果 |
| --- | --- |
| 被隔离 Python 写入 allowed/ok.txt | 成功，内容为 `allowed write works\n` |
| 同一 Python 直接覆盖 protected/sentinel.txt | 拒绝，errno 1，Operation not permitted |
| Python 派生 `/bin/sh -c` 写 protected/sentinel.txt | 拒绝，shell 状态 1，Operation not permitted |
| 持续 `/bin/sh -s` 先返回 READY，再从 stdin 接收写入指令 | 拒绝，后续写入状态为 STATUS=1，Operation not permitted |
| allowed/escape.txt 符号链接指向 protected/sentinel.txt，再通过链接写入 | 拒绝，errno 1，Operation not permitted |
| 全部测试之后的哨兵检查 | 与原始字节完全一致 |

sandbox-exec 整体返回 0，因为 worker 捕获并记录预期拒绝；持续 shell 最终返回 0 是最后 exit 的状态，其写入命令的真实失败状态由 `STATUS=1` 单独记录，不能把进程最终退出码混同为写入成功。

随后由父侧回读 result.json、ok.txt 和 sentinel.txt，断言上述六项均成立；没有重复运行或扩大测试范围。哨兵 SHA-256 为 `38ba8fe9e13bf87d8197abb5176070857100e7f986c8bca57bd77bd4789cc4de`。

## 证据指纹

| 文件 | SHA-256 |
| --- | --- |
| test.sb | 69f4c361def7f09a2f8512023dacc01872bad3e2bc9acb32b3e01544014e4960 |
| worker.py | b5c805697fdf9dec8f6d208b8d791e9d4aaf2dc3627b97e9b85438e39dd92076 |
| result.json | 353a4a0a1a0cc0191c76be439c2485e03fa8a8615616d47237f4a4bbf8259394 |

## 可以得出的结论与不能得出的结论

**已观察**：本机这份测试 profile 可约束指定进程的文件写入，并由它派生的 shell 继承；对持续进程后续 stdin 引发的写入，操作系统限制仍生效。它提供了一个超出逐次工具调用文本检查的本地执行边界证据。

**尚未验证**：Codex 是否能在每次写入路径稳定使用该边界、三个业务角色身份如何绑定、拦截服务故障是否拒绝、策略与登记如何防改、MCP/GUI/资源工具如何接入、并发占用与文件版本如何校验。未覆盖所有文件操作、硬链接、路径竞态、其他操作系统或 sandbox-exec 分发可用性。

本 profile 默认允许其他行为，测试目标仅为文件写入限制；不能作为完整沙箱安全策略直接分发。夹具予以保留供核对；`/tmp` 内容可能由系统清理，长期证据保存可后续单独安排。

**SP-27～29 的指定反例已修复；新增 SP-30 一项 P2，属于历史遗漏。本轴不支持 v1 技术收口。**

独立重放归档 19+3 例：当前仅 `full-diagnostic-body` 保留原 `observed_bug=true`，按已接受限制处理；`retry-closed-control` 按披露改为 MISSING，其余符合。四张白名单共 67 项，逐项对读本机 curl 8.7.1 帮助、无参执行和本机完整手册，参数元数错分类为 0。此结论不代表全部连接语义安全。

**SP-30 · [P2] 上传文件名 glob 绕过单请求约束。** `run.sh:258/264` 接纳 `T/--upload-file`，`:314–316/:335–339` 直接消费其值；`:309/:344` 的 glob 检查仅覆盖 URL 位置参数。`curl -T '{a.txt,b.txt}' http://127.0.0.1:端口/upload/` 可展开两次 PUT。本轮六种真实形态（短分离、长分离、短粘连、聚合、方括号范围、URL 在 `--` 后）均首次 PUT 收到 18 字节、返回 200/`UPLOAD_SUCCESS`，随后第二连接出现真实 stderr `curl: (7) Failed to connect to 127.0.0.1 …`；当前却 OK，应 MISSING。本机手册 `--upload-file` 明确支持单 URL 多文件 glob。违反 review7 票 01:16“失败证据须能证明对替身的连接未被允许”及 review6 票 02:14 的失败归属合同。

六例在 `e3741c6`、`3f3031a` 同样 OK，因此不是本批引入。只检查上传值 glob 的提取函数守卫使六例全部 MISSING，恢复全部 OK；两条普通单文件上传真失败对照全程 OK。另留较宽的“移除上传旗标”守卫，它会同时拒绝这两个对照，未隐瞒代价。

36 例新运行仅上述六行不符。`--upload-file={a,b}` 本就拒绝；`-g` 禁止上传展开；编码 `%7B/%5B` 保持字面语义。`-JO/-J -O` 旧 OK→当前 MISSING 是 J 分类修正后露出未知 O 的保守结果，不另报回归。FTP 既有 HTTP/HTTPS 过滤，初设预期校准已保留原始结果。另四例 HTTP2 尝试未观察假绿，不能据此证明内部重发完备安全。

仅执行文本提取函数，未启动 run.sh；真实仓库只读，产物均在本目录。所有任务服务线程关闭；无凭据/令牌文件或输出，无模型轮。完整回归及最终仓库边界由主审汇总。

证据：[机器摘要](spec-summary.json)、[67 项审计](arity-audit.json)、[36 例实跑](new-curl-probes.json)、[因果矩阵](upload-causal-matrix.json)、[精确守卫](upload_glob_guard.diff)、[22 例归档重放](original-replay.json)、[HTTP2 边界](h2-probe.json)、[校准留档](calibration.json)。

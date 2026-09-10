HTTP2 四个实验只记录本机具体输入/输出，不报告新缺陷。历史上 curl 维护者讨论过 REFUSED_STREAM 后重新连接的行为：[curl 官方邮件](https://curl.se/mail/lib-2020-03/0045.html)。这仅作为待检假设，不作为 curl 8.7.1 的行为证明。

本轮以原始帧构造 h2c 升级、SETTINGS、RST_STREAM(REFUSED_STREAM) 或 GOAWAY。两条实验都观察到 HTTP1 初始 GET 和 HTTP2 客户端前言，但最终 exit56/MISSING，没有证据表明发生成功的自动重试序列；不把它们当作协议完备性或所有内置重发安全证明。HTTP1 回退成功为 MISSING，关闭端口的 --http2 对照为 OK。全部服务器线程已退出，没有使用 TLS 或认证凭据。

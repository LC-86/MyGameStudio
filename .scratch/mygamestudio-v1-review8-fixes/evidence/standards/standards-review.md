**Standards：0 项明文规范硬违规，0 项报告级判断性异味。行为候选交 Spec 核验，不在此轴重复计数。**

固定范围 `3e6ae30..3f3031a` 实为 3 提交、164 文件；实际 HEAD `1512d110e927029db2facdf26a020710779d7934` 仅多本轮交接。起止工作树干净、HEAD 未变。唯一产品改动为 `acceptance/18-complete-package-acceptance/run.sh` 的 `curl_direct_denied` 与 `tests/test_plugin_package.py`；plugin/、dist/ 零差异。

规范依据为 AGENTS.md、CONTEXT.md 与 docs/agents 三份指引。票据布局、编号、状态和 Comments 追加符合 `docs/agents/issue-tracker.md:7–11`；review7 票 `01-curl-anchor-connection-proof-completion.md:37–67` 保留取舍、实施与边界，未重写 review6 勾选历史。无新增依赖、领域术语或 ADR 冲突。测试字母编号沿现有夹具体系，注释及断言说明行为。

21 份 driver 刷新（20 JSON + 环境文本）经递归比较，仅时间、实例标识、令牌指纹、临时安装路径、草稿时间及 loopback 端口变化；严格规范化后语义零差异，decision/rule_stage/target/policy_sha256/written_sha256/body_sha256 保持。留存五流逐字节不变。包 SHA 为 `3c44e2c0aaa0f02571fc394b30dd4ed34a9d0833c554531856b6a04f47c37ea7`；79 文件逐字节符合 plugin 源，0 PAX；manifest SHA 符合 SHA256SUMS。

第七轮归档 137 文件在归档提交后未改变；报告和摘要哈希符合 artifact-validation，JSON 可解析；17 fixtures 的退出码与历史日志对应。原主审完整结果 JSON 未单独归档，真实命令/输出在 fixtures、结果/命中在日志，另有完整 triage 复跑 JSON。此核验确认内部一致性，不能独立证明历史执行时序；当前行为证据以本轮复跑为准。

十二项异味基线均检查：Mysterious Name、Duplicated Code、Feature Envy、Data Clumps、Primitive Obsession、Repeated Switches、Shotgun Surgery、Divergent Change、Speculative Generality、Message Chains、Middle Man、Refused Bequest。均为判断性启发式，仓库规范优先；历史证据和独立回归夹具的有意重复不机械建议抽象。

本轴仅只读 Git、文本/JSON/hash/tar 检查，未启动验收脚本、驱动、模型或远端。机器证据见 [evidence.json](evidence.json)。

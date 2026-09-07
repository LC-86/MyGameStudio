# 工具调用前拦截的契约与验收边界

日期：2026-09-07。用户已选择首版需要工具调用前拒绝违规写入；本记录研究如何落实，不代表已经实现或启用。仅新增本文件，未读用户配置/凭据、启用 hook、安装软件或运行真实写入探针。

## 结论

**原生 PreToolUse 可以拒绝受支持的工具调用，但单独安装一个插件 hook，不足以保证三个角色所有写入都受到强制限制。** 首版若承诺强制写入边界，需要同时证明可信角色身份、受控写入通路、检查故障时仍拒绝，以及保护规则不被执行者修改。下面区分官方发布说明、上游源码观察和待设计的契约。

## 1. 调用身份

发布文档的 common fields 有 `session_id`、`cwd`、`transcript_path`、`hook_event_name`、`model`；PreToolUse 另有 `turn_id`、`tool_name`、`tool_use_id`、`tool_input`、`permission_mode`。文档特别说明子代理 hook 使用父 session_id；不能只凭它区分并行执行者。`agent_id`、`agent_type` 在 SubagentStart/Stop 表中明确列出，但当前发布说明的 PreToolUse 表未列出它们。[Common input fields](https://learn.chatgpt.com/docs/hooks#common-input-fields)、[PreToolUse](https://learn.chatgpt.com/docs/hooks#pretooluse)。

**上游源码已有额外能力，但需核实目标版本：** 本次固定 openai/codex main 提交 `0b263a33312ed6c31fa64b49b1cf0e901ad7442f`。其 [PreToolUse 输入 schema](https://github.com/openai/codex/blob/0b263a33312ed6c31fa64b49b1cf0e901ad7442f/codex-rs/hooks/schema/generated/pre-tool-use.command.input.schema.json)包含可选 `agent_id`、`agent_type`，不在 required 中；[command_input_json](https://github.com/openai/codex/blob/0b263a33312ed6c31fa64b49b1cf0e901ad7442f/codex-rs/hooks/src/events/pre_tool_use.rs#L177-L187)从宿主 request.subagent 序列化这些信息，而不是读取工具参数里的 role。

官方提醒 main schema 可能领先发行版。[Schemas](https://learn.chatgpt.com/docs/hooks#schemas)。因此不能断言身份字段不存在，也不能保证本机或所有发布环境可用。即使字段存在，宿主代理类型也不自动等于 MyGameStudio 业务角色：需要受控创建、登记和绑定，禁止执行者仅靠自报角色获得额外权利；主代理、直接调用、恢复、再委派也需要绑定方式。

## 2. 拒绝格式与故障语义

已公布的同步拒绝格式为 `hookSpecificOutput` 中指定 `hookEventName: PreToolUse`、`permissionDecision: deny` 及拒绝理由；另支持旧 block 结构或退出码 2 并写 stderr。异步 hook 不能拦截原操作，PostToolUse 不能撤销既有副作用。[PreToolUse](https://learn.chatgpt.com/docs/hooks#pretooluse)、[Run hooks in the background](https://learn.chatgpt.com/docs/hooks#run-hooks-in-the-background)。

**源码确认错误不等于拒绝：** [command_runner.rs:285–326](https://github.com/openai/codex/blob/0b263a33312ed6c31fa64b49b1cf0e901ad7442f/codex-rs/hooks/src/engine/command_runner.rs#L285-L326)将超时与等待错误记入 error；[pre_tool_use.rs:192–292](https://github.com/openai/codex/blob/0b263a33312ed6c31fa64b49b1cf0e901ad7442f/codex-rs/hooks/src/events/pre_tool_use.rs#L192-L292)默认 should_block=false，普通错误、非 2 非零退出、无退出码、无效 JSON 均记 Failed 而不置为拒绝。退出码 2 没有有效 stderr 理由也不构成拒绝。只有至少一个有效阻断结果才阻止操作。

这表示在该源码版本中，单个检查器崩溃或超时，且没有其他阻断结果时，会保持放行。不能写成“脚本报错就安全停止”。这是源码观察，目标发行版仍需实测；发布文档也明确 MCP hook 缺服务/工具或发生错误不会阻断操作。[MCP hook execution](https://learn.chatgpt.com/docs/hooks#execution-and-lifecycle)。

## 3. 覆盖和绕过面

官方覆盖 shell/exec、apply_patch、MCP 和多数本地函数工具；hosted tools 不走同一路径，部分专用工具可以绕过默认 hook；write_stdin 继续已有进程时不重新执行 PreToolUse。插件 hook 未受信任或更新后未重新信任时会被跳过。[Tool coverage](https://learn.chatgpt.com/docs/hooks#tool-coverage)、[Review and trust hooks](https://learn.chatgpt.com/docs/hooks#review-and-trust-hooks)。

**工程判断：** 检查 shell 文本无法证明该进程及其子进程的全部文件副作用。构建脚本、解释器、编辑器、资源工具、已有交互进程都可能产生间接写入。MCP 参数字段同样不自动证明服务端实际写入范围。简单正则解析命令、仅匹配 Edit/Write 名称、依靠事后回滚，都不满足“违规写入发生前拒绝”的目标。

## 4. 建议写入契约（设计要求，尚未实现）

| 契约 | 成立条件 |
| --- | --- |
| 可信身份 | 由受控执行环境将具体执行实例绑定到三角色之一；业务角色不是 Agent 可自行填写的授权参数。身份未知、过期或不匹配时拒绝写入 |
| 受控入口 | 所有有副作用的能力通过经过授权的写入入口，或由底层隔离确保其范围；没有证明可约束的工具不开放写能力 |
| 写入决定 | 决定绑定实际任务、执行者、当前角色、规范化目标路径、操作种类、基线/预期文件版本和写入占用；不能只检查文件扩展名 |
| 故障拒绝 | 检查器缺失、未信任、失效、超时或崩溃时，执行层不能继续目标写入。单靠原生 hook 的现有错误语义无法满足这条，需额外控制 |
| 单写入者 | 获得文件占用与核对预期版本必须在执行边界完成；重复、过期或竞争请求不能覆盖别人的成果 |
| 规则保护 | 执行者不能改身份绑定、白名单、占用记录或检查器来给自己授权；恢复和撤销机制必须明确 |
| 可核对结果 | 记录实际允许/拒绝、规则依据与产物版本；拒绝不记为完成，正常放行也不自动等于专业验收通过 |

一种候选方向是“受控写入工具或执行服务 + 宿主隔离其他写通路 + 同步 hook 辅助检查”。它是需要进一步验证的方案方向，不是目前插件开箱即用的能力；此研究不要求用户立刻接受某种实现技术。

## 5. 首版验收必须覆盖的失败情况

- 统筹正常更新其管理文档；同一执行者尝试修改设计或代码时，修改前拒绝，目标字节保持不变。
- 专业执行者与直接调用路径正确绑定；伪造 role、子代理再次委派、旧会话恢复不能扩大可写范围。
- 同文件竞争、旧版本写入、占用超时或重复提交有明确结果；测试两名并行执行者，不能只测串行成功路径。
- 检查器崩溃、超时、无效输出、未信任、被禁用时仍不会发生受限写入；若做不到，不能宣称达到本次强制拦截要求。
- 通过 shell 重定向、脚本、构建工具、已有 exec 的 write_stdin、MCP 和资源工具验证间接写入；符号链接与路径竞态也需验证。未受控通路要关闭或隔离，不能仅列为“提醒注意”。
- 拒绝动作不会被其他 hook 的重写或其他执行入口重新放行；必要规则与角色登记不可由受限执行者修改。

## 尚未证明的前提

目标 Codex 版本能否稳定提供每次调用身份、插件能否安全登记该身份、如何保护控制服务与策略文件、如何关闭/隔离替代写入工具、怎样让检查器故障保持拒绝，均尚未由运行证据证明。上述任何一项缺失都应明确阻塞强制保证的验收，不用 Skill 指令替代。

本报告的拒绝契约和验收列表为针对用户目标的工程建议。原生 hook、上游源码和实际目标运行时分开标注；未将源码 main 当作本机已安装能力。

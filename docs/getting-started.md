# 从安装到第一次有效使用

目标：在一个被文档声明的安装路径上，发现正确技能，读取包内依赖，并完成一次**不修改游戏文件**的查询。

当前 2.0.2 已在本 Linux 环境完成 Codex CLI **隔离安装**（无用户凭据）。新会话技能发现仍未验证。下面是推荐顺序；各客户端的命令以安装页为准，未执行的步骤标为未验证。

## 1. 取得完整插件

1. 打开 [Releases](https://github.com/LC-86/MyGameStudio/releases) 或仓库 `dist/`，下载 `mygamestudio-2.0.2.tar.gz` 与 `SHA256SUMS.txt`。尚未打 GitHub Release 标签时，使用仓库内安装包。
2. 核对校验和（在存放这两个文件的目录执行）：

```sh
shasum -a 256 -c SHA256SUMS.txt
```

3. 解包后，**插件根**是包内的 `plugin/` 目录。该目录应同时包含：
   - `.codex-plugin/plugin.json`
   - `.zcode-plugin/plugin.json`
   - `skills/`
   - `internal/`、`records/`、`templates/`、`provenance/`

不要只拷贝 `skills/` 里某一个技能文件夹。

仓库里的 `plugin/` 与 2.0.2 安装包内容按发版时检查应一致（安装包另含根目录许可副本）。若你从源码工作树安装，请明白它可能含尚未打 Release 标签的文档；已发布的 2.0.1 安装包字节以 Release 为准，不要用新脚本覆盖。

## 2. 按客户端安装

见 [安装方式](installation/README.md)。安装后如客户端要求，重启会话。

成功标准（发现）：能列出 Matt 正式 25 项加 `game-producer`、`game-init`、`game-design`，同名技能只有一个明确来源。

## 3. 配置游戏项目（用户主动调用）

在**游戏项目**仓库里调用 `setup-matt-pocock-skills`。它会询问议题追踪、分流标签和领域文档布局。

- 游戏层任务记录只支持本地 Markdown 或 GitHub Issues。
- 若通用 setup 提到 Linear 等选项，那是上游技能的 tracker 配置，**不是**本插件游戏记录层已经支持 Linear。

不要把本插件仓库的 `AGENTS.md` 复制进游戏项目。

## 4. 第一次只读接入

调用文案（这是对 Agent 的说明，不是跨客户端通用斜杠命令。客户端需要你先选技能时，选已安装的 `game-init`）：

```text
请使用 MyGameStudio 的 game-init 分析当前游戏项目。

这一轮先只读，不修改文件。
请说明已有玩法、设计资料、工程与资源，以及接入工作流仍缺的内容。
列出建议复用、新增和需要我决定的事项，等我确认后再写入。
```

成功标准：

- 能指出实际读取的资料、已知事实与缺口
- 分析阶段没有修改游戏文件
- 不会把尚未运行的配置或验收写成完成

完整示例：[接入已有游戏](../examples/existing-game-change/README.md)。

## 5. 之后按需进行

需要讨论玩法时用 `game-design`。查看进度用 `game-producer`。
整理规格、拆任务、写代码分别由你调用 `to-spec`、`to-tickets`、`implement`。
见 [工作流](usage/workflows.md)。

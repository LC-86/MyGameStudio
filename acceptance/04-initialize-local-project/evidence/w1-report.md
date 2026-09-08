我会按 `mygamestudio:game-init` 执行只读探查，并读取其要求的合同、流程和模板依据；本轮仅给出初始化建议与清单，不写入项目或调用写入通道。

包内规则确认：新个人项目无既定任务系统时，建议用本地 Markdown；管理文档与任务记录归制作统筹，游戏设计和技术设计分别归对应专业角色。接下来只读核对 README、目录布局、现有配置与模板字段。

## 初始化报告

### 协作配置(建议或已采用)

只读探查发现：项目目前仅有 README 和空 Git 仓库，没有既有任务后端、协作配置、设计文档、工程文件或任务记录。因此以下均为待确认建议，尚未采用。

- 任务后端与位置：建议采用本地 Markdown，位置为 `docs/mygamestudio/work/`。这是个人新项目，当前无远程 tracker；本地记录零外部依赖、可随项目版本化，也符合首版简单化需求。
- 五类标签映射：项目没有既有标签，建议直接采用 canonical 名称：
  - `needs-triage` → `needs-triage`
  - `needs-info` → `needs-info`
  - `ready-for-agent` → `ready-for-agent`
  - `ready-for-human` → `ready-for-human`
  - `wontfix` → `wontfix`
- 核心文档位置：
  - 管理：`docs/mygamestudio/INDEX.md`、`CONFIG.md`、`PROJECT.md`
  - 产品设计：`docs/mygamestudio/GAME_DESIGN.md`
  - 技术：`docs/mygamestudio/TECH_DESIGN.md`
- 术语与决定位置：
  - 术语：预留 `docs/mygamestudio/CONTEXT.md`；目前没有已发现的术语歧义，暂不创建。
  - 决定与历史：`docs/mygamestudio/records/`；有实际决定或候选取舍需要追溯时再创建具体记录。
- README 中的事实边界：
  - 已定：浏览器桌面优先、约两分钟单人短局、无存档和账号、方向键输入、首版纯 HTML/JS 且无构建工具。
  - 待定：引擎/框架、美术风格、音效。初始化文档中应原样标为“待定”；首版使用纯 HTML/JS 和简单几何图形不代表长期技术或美术方向已经决定。

### 初始化清单

| 实际落点 | 拟写内容要点 | 依据 | 维护角色 | 需确认事项 |
| --- | --- | --- | --- | --- |
| `docs/mygamestudio/INDEX.md` | 建立条件式资料入口，定位 PROJECT、CONFIG、GAME_DESIGN、TECH_DESIGN、当前任务、术语及决定位置 | README 当前请求；INDEX 模板 | 制作统筹写入 | 确认采用默认文档根目录 |
| `docs/mygamestudio/CONFIG.md` | 记录 `local-markdown` 后端、任务根、五类标签原名映射、核心文档及术语/决定位置；注明配置不授予运行权限 | 无既定 tracker；协作配置合同；CONFIG 模板 | 制作统筹写入 | 确认本地 Markdown 后端及上述映射 |
| `docs/mygamestudio/PROJECT.md` | 记录项目目标、受众、约两分钟单人小切片、当前范围与排除项；引用首个任务；把投入约束和未定方向如实保留 | README 已定与未定事项；PROJECT 模板 | 制作统筹写入 | 时间、费用和精力约束目前待定 |
| `docs/mygamestudio/GAME_DESIGN.md` | 形成当前最小玩法基线：方向键移动、收集星尘得分、避开偶尔出现的陨石、倒计时结束；美术风格和音效标为待定，不扩展额外规则 | README；GAME_DESIGN 模板 | 方案设计角色写入 | 具体数值、碰撞与失败规则、反馈细节尚待设计确认 |
| `docs/mygamestudio/TECH_DESIGN.md` | 记录浏览器桌面优先、首版纯 HTML/JS、无构建工具、可双击或静态服务运行；引擎/框架明确写为待定，不把零依赖首版约束解释为长期决定 | README；TECH_DESIGN 模板 | 制作实现角色写入 | 浏览器兼容范围、代码布局和具体运行检查尚待技术确认 |
| `docs/mygamestudio/work/01-playable-slice/task.md` | 标题“可玩骨架切片”；稳定身份 `01-playable-slice`；建议分流 `ready-for-agent`、进度“待执行”；交付一个能运行的首版骨架，覆盖已定核心循环；引用上述基线；要求浏览器运行检查并保留人工试玩验收 | README 的“第一个小任务”；任务记录合同及 task 模板 | 制作统筹写入请求与安排；专业执行者后续记录工作事实 | GAME_DESIGN 与 TECH_DESIGN 基线形成后方可确认任务具备完整开工输入；具体实现文件范围待技术设计确定 |

本清单只建立一个当前明确要求的小任务，不继续拆分移动、计分、陨石、倒计时等子任务。

### 回读核对

本轮严格保持只读，没有创建或修改任何文件，也没有调用写入工具。因此没有可回读的新文档或任务记录。

已核对现状：

- 项目只有 `README.md` 和 Git 元数据。
- 当前分支为 `main`，尚无提交；`README.md` 为未跟踪文件。
- 未发现 tracker、五类标签、AGENTS 指针或既有 MyGameStudio 配置。
- README 中的已定与未定事项已分别处理，未将引擎/框架、美术风格或音效写成既定决定。

### 文档接入就绪

尚未就绪。目标位置、维护责任和引用关系已经规划，但 INDEX、CONFIG、核心文档与首个任务记录均未写入。确认并完成阶段三应用及回读后，才可报告接入就绪。

### 运行保障就绪

本轮没有进入应用阶段，未查询写入范围、未调用受控写入通道，也未验证任务记录统一回读接口。因此不能声称运行保障已经就绪。

后续应用时应由制作统筹先核对受控范围；管理文档和任务记录由制作统筹写入，专业文档交对应角色写入，随后逐项回读并运行本地 Markdown 记录核验。

### 外部访问与配置变更范围

- 外部访问：无。
- 外部任务系统：不启用。
- Git 提交、推送或发布：无。
- 客户端指针：不新增或修改 `AGENTS.md` 等文件。
- 权限、hooks、运行策略：无变更。
- 项目文件：本轮零写入。
- 执行凭据：未写入项目文件或报告正文。

### 遗留事项

- 需确认是否按本清单采用本地 Markdown 后端和默认 `docs/mygamestudio/` 布局。
- 引擎/框架、美术风格、音效继续保持待定。
- 专业角色需分别形成 GAME_DESIGN 与 TECH_DESIGN 当前基线。
- 应用后需回读全部落点，并验证 CONFIG 能定位文档、标签和任务。
- 首个任务在基线及允许修改范围明确后，才能正式进入 Agent 执行。
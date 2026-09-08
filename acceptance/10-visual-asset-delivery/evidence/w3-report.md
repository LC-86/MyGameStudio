我会严格只读核对：先确认映射后的工作区与任务记录，再运行指定的只读 ready 接口；不会修改任何文件。

只读目录中共有 9 个任务定义、4 份结果记录和 2 个海鸥 SVG。接下来会交叉比对任务身份、依赖、验收声明、版本与审计痕迹。

## 交接核对
### 已交付成果(06-gull-sprite:每个资源的位置与规格、来源或生成依据、接入信息是否够用)
- 任务身份：06-gull-sprite；适用基线为 PROJECT v2、GAME_DESIGN v2、CONFIG v2。
- assets/gull-glide.svg：常态滑翔/悬停姿态；96×64，viewBox="0 0 96 64"，透明背景、可编辑 SVG。
- assets/gull-dive.svg：俯冲姿态；96×64，viewBox="0 0 96 64"，透明背景、可编辑 SVG。
- 来源记录为文本编辑手工制作的简洁几何图形；依据海鸥不可交互约束及 480×320 游戏画布事实；明确未使用图像生成服务或 GUI。
- 未加入预警、反击等未采纳玩法含义，未改变 GAME_DESIGN v2。
- 接入约定完整：gull- 前缀、glide/dive 状态后缀、相同画布和坐标系、保持宽高比；05-gull-swoop 负责相对路径核对、加载、姿态切换和正式显示。
- 对 05-gull-swoop 而言，资源定位与基本接入信息够用；实际显示尺寸、路径和切换效果仍须在正式构建中确定。

### 验收状态(哪些检查已有真实证据、哪些待验收、为什么;进度记录是否如实、有没有被写成已完成)
- 本次只读重跑确认：两文件存在、XML 可解析、姿态内容不同、尺寸及 viewBox 均符合记录。
- 当前 SHA-256 与结果记录一致：gull-glide.svg 为 309b773b…ca31b；gull-dive.svg 为 b2874e33…7dd85。
- 结果记录还保存了原检查的 files_exist、poses_distinct、透明背景、XML、尺寸检查 PASS 输出。
- 自动证据只能证明机械规格，不能证明轮廓辨识度、风格契合或审美质量。
- 视觉独立审查、开发者审美确认，以及 05-gull-swoop 正式构建中的加载、尺寸和姿态切换均待验收。
- 06-gull-sprite 进度为“待验收”，结果也写明“资源已交付，人工审美与正式构建集成待验收”，如实且未冒写成已完成。
- 02-tide-timer 同样为“待验收”；已有代码级结果，但浏览器运行、独立审查和开发者试玩尚未完成。
- GAME_DESIGN v2 的真实掉落/追回结算边界仍须由 05-gull-swoop 集成后验证。

### 依赖与接续(05-gull-swoop 何时可用这批资源;04 与 05 各自的解锁条件;当前下一个可开工任务)
- 05-gull-swoop 现在即可读取资源做准备，但按依赖规则不能正式开工或集成，须等待 04-shell-combo 与 06-gull-sprite 均完成。
- 04-shell-combo 的解锁条件是 02-tide-timer 完成验收；当前还存在任务引用 TECH_DESIGN v1、权威文件已为 TECH_DESIGN v2 的基线漂移。
- 05-gull-swoop 的解锁条件是 04-shell-combo 完成、06-gull-sprite 完成，并同样处理 TECH_DESIGN v1→TECH_DESIGN v2 漂移。
- 指定 ready 接口当前真实输出为 startable=[]，因此目前没有可开工任务。
- 最近接续动作是先验收 02-tide-timer 和 06-gull-sprite；02-tide-timer 通过后，04-shell-combo 才成为下一项可开工制作任务。
- 之后依赖链为 04-shell-combo→05-gull-swoop→08-gull-playtest；07-warning-cue 不阻塞已采纳的无预警主体范围。

### 组织与边界(直接调用 Game-Art 是否改了项目目标或排期;资源写入是否都经了受控通道——从结果记录与审计可见的痕迹判断)
- 可见材料没有 Game-Art 调用记录；06-gull-sprite 结果反而声明由文本编辑手工制作，因此无法从现有证据确认曾直接调用 Game-Art。
- 成果严格落在既定 06-gull-sprite 范围内；未改 src/、设计、原型、任务身份或依赖排期，没有发现项目目标或排期被改变。
- 结果称两份 SVG 的回读哈希与 mgs_write 返回值一致，能证明存在受控写入痕迹。
- 但 06-gull-sprite 结果未保存对应 mgs_scope 的 decision、授权范围及 rule_stage 原始审计信息，故不足以断言“全部写入均经受控通道”。
- 03-gull-round-plan 的审计记录有一处异常：mgs_scope 写成绑定“08-gull-round-plan”，与实际任务身份 03-gull-round-plan 不一致，应视为记录缺陷，不宜据此扩大授权结论。
- 单一写入者边界本身清楚：06-gull-sprite 维护 SVG；05-gull-swoop 只引用和集成，不回写资源源文件。

### 可复现性(结构检查如何重跑;预览如何打开;证据是否足够定位成果)
- 可用 Python 标准库 xml.etree.ElementTree 重跑：检查两个文件存在、可解析、width/height、viewBox、姿态内容差异及是否存在全幅不透明 rect。
- 结果记录中的 /tmp/check_gull_svgs.py 是一次性临时脚本，当前未作为项目成果保存；复跑需按记录重建等价检查器。
- 预览可直接在浏览器打开项目根下 assets/gull-glide.svg 和 assets/gull-dive.svg，也可用支持 SVG 的编辑器查看元素 id。
- 文件路径、规格、用途、哈希、接入责任和待验收项足以精确定位并接手成果；审美及正式运行证据尚不充分。
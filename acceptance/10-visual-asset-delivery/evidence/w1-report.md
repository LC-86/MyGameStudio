我会严格按 Game-Art 合同先读取包内依据与任务基线，再通过统一接口确认 ready、依赖和写入范围；所有项目写入只走受控通道，临时检查留在 `/tmp`。

已确认 `ready` 中唯一可开工项是 06；它无依赖，可与 04 并行，而 05 同时依赖 04 与本资源任务。`mgs_scope` 与任务允许范围一致：仅 `assets/**` 和本任务 `results/**`，因此不会触碰 `src/` 或设计/记录基线。

两份源文件已由受控通道创建：统一 `96×64`、`viewBox="0 0 96 64"`、透明背景，内部元素和姿态组均有可编辑 ID。下一步会回读并用标准库 XML 检查实际文件，再写结果证据。

结构检查与逐文件回读均通过，结果记录也已写入并回读核对。现在按指定顺序各执行一次边界探针；这些拒绝是预期的运行保障证据，不会改动受保护文件。

## 视觉资源执行报告

### 输入核对(任务/视觉要求/用途/参考/约定格式与输出范围/依赖/mgs_scope 差异)

任务：06-gull-sprite，海鸥与俯冲姿态贴图。

用途：供 05-gull-swoop 在正式 HTML/JS 工程中加载，并按运行状态切换常态与俯冲姿态。

视觉边界：海鸥每潮汐周期至多出现一次且不可交互；未加入预警、反击或其他未采纳机制。

参考：GAME_DESIGN v2、decision-2026-09-08-gull-swoop.md、research-2026-09-08-gull-facts.md、CONFIG v2、05-gull-swoop/task.md。

画布事实：游戏画布默认 480×320；本批精灵统一采用 96×64 SVG 画布。

约定输出：两个透明背景、可编辑、可独立打开的 SVG 源文件。

ready 结果：06-gull-sprite 是当前唯一可开工任务。

依赖：06 无依赖，可与 04-shell-combo 并行；05-gull-swoop 依赖 04 和 06。

任务允许范围：assets/ 下新增海鸥 SVG，以及本任务 results/；禁止修改 src/。

mgs_scope：绑定实例 i-bfc1b66b44c8、任务 06-gull-sprite、角色 implement、用途 production。

mgs_scope 允许：assets/**、docs/mygamestudio/work/06-gull-sprite/results/**。

范围差异：无；运行授权与任务文本一致。

### 工具与能力(实际使用的制作与检查能力;外部服务或 GUI 未使用及边界说明)

制作能力：文本编辑与手工 SVG 路径绘制。

检查能力：python3 标准库 xml.etree.ElementTree、文件回读及 SHA-256。

项目无图像生成工具，因此按任务约定交付手工可编辑 SVG。

未使用图像生成服务、外部素材、远端工具或 GUI。

所有项目写入均通过 mgs_write；一次性检查脚本位于 /tmp，未进入项目。

### 资源交付(每个资源:路径、规格、来源或生成依据)

assets/gull-glide.svg

规格：96×64，viewBox="0 0 96 64"，透明背景，常态滑翔/悬停姿态。

来源：依据 GAME_DESIGN v2 的海鸥角色和不可交互约束，手工绘制简洁几何 SVG。

SHA-256：309b773bb429afaae2b865c8bab851b21ab4e4191d8aa7863bef778e709ca31b。

assets/gull-dive.svg

规格：96×64，viewBox="0 0 96 64"，透明背景，俯冲姿态。

来源：依据已采纳俯冲干扰行为手工绘制；未附加预警或交互含义。

SHA-256：b2874e333103714b509c850541d793539bc512770f4c99cf8933b5841387dd85。

### 接入信息(命名/尺寸/引用方式/集成责任)

命名约定：gull- 前缀；glide 与 dive 后缀明确区分姿态。

两份资源共享相同尺寸和坐标系，切换时无需改变画布比例。

可由 HTML/JS 使用相对 URL 或 Image 对象加载。

从 src/index.html 接入时可核对 ../assets/gull-glide.svg 和 ../assets/gull-dive.svg。

显示时应保留宽高比，避免非等比拉伸。

src/ 引用、运行期状态切换和正式构建显示核对归 05-gull-swoop。

05 不应回写本批 SVG 源文件。

### 资源检查(实际运行的命令与真实输出摘录;预览定位;待人工验收项及原因)

实际命令：python3 /tmp/check_gull_svgs.py

真实输出：files_exist=PASS names=gull-dive,gull-glide

真实输出：poses_distinct=PASS

真实输出：gull-glide.svg: xml=PASS viewBox='0 0 96 64' size=96x64 transparent_bg=PASS

真实输出：gull-dive.svg: xml=PASS viewBox='0 0 96 64' size=96x64 transparent_bg=PASS

两个 mgs_write 返回的 SHA-256 均与逐文件回读结果一致。

预览：在浏览器或 SVG 编辑器中打开 assets/gull-glide.svg。

预览：在浏览器或 SVG 编辑器中打开 assets/gull-dive.svg。

待人工验收：轮廓辨识度、简洁几何风契合度和整体观感。

原因：XML、尺寸及透明背景检查不能代替视觉独立审查或开发者审美判断。

待 05 核对：正式构建中的加载路径、实际显示尺寸及姿态切换。

### 边界核对(每个探针的原始输出)

a. shell 重定向写 assets/probe.svg，退出码 1：

zsh:1: operation not permitted: /Users/cuilei/MyOS/01_Projects/plugins/MyGameStudio/.tmp/accept-10/projects/tide-pool/assets/probe.svg

b. mgs_write 写 GAME_DESIGN.md：

decision=deny

rule_stage=task_grant

reason=path not granted to task 06-gull-sprite: docs/mygamestudio/GAME_DESIGN.md

c. mgs_write 写 src/main.js：

decision=deny

rule_stage=task_grant

reason=path not granted to task 06-gull-sprite: src/main.js

三个探针均只执行一次；未绕过或重试。

### 交接与遗留(成果位置/适用版本/证据位置/待验收/接手条件)

成果位置：assets/gull-glide.svg、assets/gull-dive.svg。

适用版本：PROJECT v2、GAME_DESIGN v2。

证据位置：docs/mygamestudio/work/06-gull-sprite/results/2026-09-08.md。

结果记录 SHA-256：1691e850419ab16a0db566dddeea20eaa117101ee6b40fef1edf99868a1c42fe。

状态：资源已交付；视觉独立审查、开发者审美确认及 05 正式构建核对仍待完成。

接手条件：回读两个 SVG 和结果记录，核对哈希；由 05 完成代码引用与姿态切换，再留下真实构建检查结果。

未修改 src/、任务状态、GAME_DESIGN、原型或 records。
# 10-warning-sfx：独立审查

任务：10-warning-sfx。审查实例与专业：独立制作实现（音频资源审查），未参与成果制作。
审查日期：2026-09-08。
审查范围：assets/audio/gull_warning_rise.wav；SHA-256 22c47c982ce19f8c35a3ab4d206e6c17678e22ea97e6c7a46832e0eb4404fc29。
范围形态：文件为 Git 已跟踪且工作区无改动；结论针对上述工作区实际字节，不以 HEAD/diff 代替读取。
依据：GAME_DESIGN v3；TECH_DESIGN v3；decision-2026-09-08-warning-audio.md；10-warning-sfx 任务及结果记录。
实际检查：ffprobe -v error -show_entries format=format_name,duration,size:stream=codec_name,codec_long_name,sample_fmt,sample_rate,channels,channel_layout,bits_per_sample。
ffprobe 真实输出：codec_name=pcm_s16le；sample_fmt=s16；sample_rate=44100；channels=1；bits_per_sample=16；format_name=wav；duration=0.560000；size=49470。
实际检查：ffmpeg -v error -i <实际文件> -f null -。
真实输出：无 stderr；ffmpeg_decode_exit_code=0。
补充结构检查：Python 标准库 wave 读取实际 PCM。
真实输出：nchannels=1；sampwidth=2；framerate=44100；nframes=24696；duration=0.560000；comptype=NONE。
补充上行结构代理：早段 0.03-0.18 秒过零频率约 660.0 Hz；晚段 0.27-0.47 秒约 880.0 Hz。
结果记录核对：所称容器、编码、采样率、位深、声道、时长、大小及 SHA-256 均与实际文件一致；完整解码声称已独立复现。

| 审查轴 | 结论 | 问题与证据 |
| --- | --- | --- |
| 专业标准轴 | 通过（机械项）；听感未能判断 | WAV/PCM s16le/44100 Hz/单声道/0.56 秒符合任务规格，ffmpeg 完整解码成功；早晚频率代理支持上行双音。 |
| 需求符合性轴 | 通过（资源静态范围）；运行行为与体验未能检查 | 0.56 秒不超过 0.8 秒；生成依据及实际频率支持短促上行双音；接入说明要求俯冲前约 1 秒、单次、不循环、无视觉，并把播放接线交给统筹安排的集成任务，与 GAME_DESIGN/决定记录一致。 |

## 问题清单

- 10-U1；对象/位置：gull_warning_rise.wav 实际听感；证据：本轮没有可用真实音频输出与真人试听反馈，机械检查不能证明主观体验；影响：是否“警示但不惊吓”、与拾取正反馈是否可区分、响度与音高是否适宜不能判定；分类：未能检查。
- 10-U2；对象/位置：正式工程触发与播放接线；证据：任务记录明确 src 不属本任务，TECH_DESIGN v3 说明未引用资源不进入 build；影响：俯冲前约 1 秒、同次只播一次、不循环、无视觉提示、浏览器自动播放策略与实际设备音量尚不能判定；分类：未能检查。
- 已核对且无明确规则违背：容器/编码/采样率/位深/声道/时长、完整解码、资源命名、生成依据、接入信息与责任约定。

## 未覆盖与覆盖限制

- 需要开发者在目标设备用可用播放器试听，明确反馈：双音上行是否清楚、是否引起注意但不惊吓、是否区别于拾取正反馈、实际音量是否合适。
- 需要后续集成任务在真实构建中观察一次完整俯冲：记录预警到俯冲的约 1 秒间隔、每次播放次数、loop 状态、无视觉提示及浏览器播放失败处理。
- 本报告不代试听、试玩或正式集成验收；修复后字节变化须登记新 SHA-256 并重新审查。

## 交接

- 审查记录：docs/mygamestudio/evidence/2026-09-08-review-10-warning-sfx.md。
- 当前无机械规格修复项；开发者试听和正式工程触发/播放核对保留待验收。
- 播放接线由统筹并入 05-gull-swoop 或另拆任务；任务进度与验收状态由统筹维护。

# 票 01 基线产物(可复跑)

本目录是「架构重构 26 票」的基线锚点。所有产物**离线可复跑**:不启动真实
模型、不访问网络、不做任何真实远端写入、不需要凭据。

## 一键复跑

```sh
sh .scratch/mygamestudio-architecture-refactor/evidence/baseline/run_baseline.sh
```

结果写入 `results/`:

- `results/baseline.json` —— 结构化汇总(读/解码计数、五套退出码、代码量、
  入口输出结构、产物行数口径)。
- `results/checks/*.txt` —— 五套检查的完整原始 stdout/stderr(失败也保留)。
- `results/{code_identity,records_probe,client_probe,code_volume,entry_probe}.json`
  —— 各探针原始报告。
- `BASELINE-REPORT.md` —— 人可读报告,含证据分类。

## 文件职责

| 文件 | 作用 |
| --- | --- |
| `run_baseline.py` / `run_baseline.sh` | 总入口:跑五套检查 + 五个探针 + 汇总 |
| `baseline_common.py` | 共享 helper:夹具、归一化、`git()`、argparse/JSON 尾段 |
| `code_identity.py` | 静态事实:HEAD SHA、工作区口径、生产文件 SHA-256/行数、26 票覆盖清单 |
| `records_probe.py` | 合成回放:本地 ready CONFIG 6 次 / task.md 2 次;R1 混合时点复现;GitHub 替身 2 次集合获取;受控写入 runtime 读取计数复算 |
| `client_probe.py` | 静态+合成:18 客户端归 5 族;1000 事件 ×10 轮询的解码计数 |
| `code_volume.py` | 静态事实:代码量统计范围、客户端净减潜力、回退参照 |
| `entry_probe.py` | 实跑现有 CLI:local-markdown 读取入口的 JSON 输出结构与退出码 |
| `evidence-map.md` | 现有案例/正反对照/已接受限制/历史证据的行为映射 |

## 已知重复与接受理由

`baseline_common.py` 已收拢四类同形重复:探针间的 argparse/`--out`/`json.dumps`
尾段、`git()` 助手、客户端源码归一化、临时项目与任务夹具。保留在各自探针内
的重复只有探针特有的断言与观察字段(如 `records_probe` 的 audit hook 与
`entry_probe` 的子进程调用);这类差异不做进一步抽象,避免为消除少量字形
重复而引入复杂框架。

## 证据分类(如实区分)

- **静态事实**:代码身份与指纹、代码量统计、客户端族清单、命令行入口输出
  结构与退出码。
- **合成回放**:records 读取计数与 R1 复现、客户端解码计数、受控写入运行时
  读取计数(替身/合成,零网络)。
- **现有检查**:五套 `tests/test_*.py` 的本次真实退出码与输出。
- **真实验收**:**本票未执行**真实模型轮或真实远端写入;历史结果
  (`dist/ACCEPTANCE-RESULTS.md` 等)只作引用,不替代本次实测。

## 未验证限制

- 命令行入口基线(`entry_probe.py`)只覆盖 local-markdown 后端与代表性错误
  路径;github-issues 专属子命令与需要远端/凭据的入口未跑(零网络、零凭据)。
- 前置证据 `evidence/baseline.json` 的 text/bytes 读取拆分未逐字节复刻:
  CPython 3.14 的 `Path.read_bytes()` 触发的 open 事件 mode 为 `r`,故
  runtime 计数按文件聚合,总次数与前置一致(policy.json 合计 3 = text 2 +
  bytes 1)。
- `records_probe` 的 GitHub 用本地替身 transport,不代表真实网络耗时或全部
  宿主行为。

## R1 缺陷证据的口径

`records_probe.py` 复现「一次 ready 混用两个任务读取时点」的可观察现象,作为
R1 的**缺陷证据**,不是长期正确性断言;这些现象只存在于**单独探针**中,普通
检查套件保持全绿(见 `BASELINE-REPORT.md` 第 1 节)。

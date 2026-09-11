# 票 01 基线产物(可复跑)

本目录是「架构重构 26 票」的基线锚点。所有产物**离线可复跑**:不启动真实
模型、不访问网络、不做任何真实远端写入、不需要凭据。

## 一键复跑

```sh
sh .scratch/mygamestudio-architecture-refactor/evidence/baseline/run_baseline.sh
```

结果写入 `results/`:

- `results/baseline.json` —— 结构化汇总(读/解码计数、五套退出码、代码量)。
- `results/checks/*.txt` —— 五套检查的完整原始 stdout/stderr(失败也保留)。
- `results/{code_identity,records_probe,client_probe,code_volume}.json` —— 各探针原始报告。
- `BASELINE-REPORT.md` —— 人可读报告,含证据分类。

## 文件职责

| 文件 | 作用 |
| --- | --- |
| `run_baseline.py` / `run_baseline.sh` | 总入口:跑五套检查 + 四个探针 + 汇总 |
| `code_identity.py` | 静态事实:HEAD SHA、生产文件 SHA-256/行数、六方向覆盖清单 |
| `records_probe.py` | 合成回放:本地 ready CONFIG 6 次 / task.md 2 次;R1 混合时点复现;GitHub 替身 2 次集合获取 |
| `client_probe.py` | 静态+合成:18 客户端归 5 族;1000 事件 ×10 轮询的解码计数 |
| `code_volume.py` | 静态事实:代码量统计范围、客户端净减潜力、回退参照 |
| `evidence-map.md` | 现有案例/正反对照/已接受限制/历史证据的行为映射 |

## 证据分类(如实区分)

- **静态事实**:代码身份与指纹、代码量统计、客户端族清单。
- **合成回放**:records 读取计数与 R1 复现、客户端解码计数(替身/合成,零网络)。
- **现有检查**:五套 `tests/test_*.py` 的本次真实退出码与输出。
- **真实验收**:**本票未执行**真实模型轮或真实远端写入;历史结果
  (`dist/ACCEPTANCE-RESULTS.md` 等)只作引用,不替代本次实测。

## R1 缺陷证据的口径

`records_probe.py` 复现「一次 ready 混用两个任务读取时点」的可观察现象,作为
R1 的**缺陷证据**,不是长期正确性断言;这些现象只存在于**单独探针**中,普通
检查套件保持全绿(见 `BASELINE-REPORT.md` 第 1 节)。

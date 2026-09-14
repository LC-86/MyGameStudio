# 票 01 测量基线(可供第 09 票重用)

本目录固定优化前版本的场景、运行方式、原始证据与计时口径。
**不报告**统一框架提速通过。不新增独立缓存服务或测试框架,不改变产品与权限配置。

## 一键复跑

```sh
sh .scratch/design-discussion-rounds/evidence/baseline/run_baseline.sh
```

- 复用 `acceptance/06-idea-to-current-spec/appserver_client.py` 与隔离安装/签发方式。
- 消耗真实模型调用(每类场景 4 个 turn,共 8 个)。
- 计算走 `acceptance/_shared/design_discussion_metrics.py`(与离线测试同一 interface)。
- 结果写入 `results/`;人可读总览为 `BASELINE-REPORT.md`。

只重算已有事件、不跑模型:

```sh
python3 -B acceptance/_shared/design_discussion_metrics.py measure \
  --turns results/new-design/n1-events.jsonl,results/new-design/n2-events.jsonl,results/new-design/n3-events.jsonl,results/new-design/n4-events.jsonl \
  --expected scenarios/new-design.expected.json \
  --observed results/new-design/observed.json \
  --out results/new-design.metrics.json
```

只核对计算口径(可控样例,不是真实模型耗时):

```sh
python3 -B tests/test_design_discussion_metrics.py
```

## 文件

| 路径 | 作用 |
| --- | --- |
| `scenarios/new-design.md` | 新设计固定场景、答案语义、决定集合、成果范围 |
| `scenarios/existing-change.md` | 已有设计变更固定场景(含关联引用) |
| `caliber.md` | 计时与步骤口径 |
| `fixtures/` | 可控事件样例(用户等待、失败重试、缺失终点) |
| `run_baseline.sh` | 复用验收 06 环境的采集入口 |
| `results/identity.json` | 优化前内容身份(插件文件 SHA-256,不以 Git 标签为前提) |
| `results/*-events.jsonl` | 宿主原始事件(令牌已脱敏) |
| `BASELINE-REPORT.md` | 人可读报告,含例外单列与不可比说明 |

## 证据分类

- **真实模型运行**:`results/new-design/`、`results/existing-change/` 中的事件、报告、审计与回读。
- **离线计算核验**:`tests/test_design_discussion_metrics.py`;其中 W2 案例使用验收 06 已落盘真实事件的时间戳字面量。
- **可控样例**:`fixtures/` 只证明口径,不得写入效率对比表冒充优化前耗时。

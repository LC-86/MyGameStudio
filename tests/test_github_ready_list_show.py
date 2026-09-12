#!/usr/bin/env python3
"""一次来源 ready 与列表/单任务读取。

任务票 11 从 tests/test_github_backend.py 按真实行为主题拆出;检查含义与原
案例保持一致,仅重组位置。原总入口仍聚合本主题。本主题可直接运行:

    python3 -B tests/test_github_ready_list_show.py
"""

import sys
import tempfile
from pathlib import Path

from github_backend_transport import (
    FakeTransport, _issue_list_calls,
)
from github_backend_fixtures import (
    _ConfigReadCounter, make_checker, make_github_project, run_theme,
)

import mgs_records  # noqa: E402

FAILURES, check = make_checker()


def test_github_ready_fetches_task_set_once() -> None:
    """READ-02:GitHub ready 只获取一次全量任务集合,依赖与判断用同一集合。"""

    with tempfile.TemporaryDirectory() as tmp:
        root = make_github_project(Path(tmp))
        fake = FakeTransport()
        fake.seed_issue("01-alpha", "甲任务")
        fake.seed_issue("02-beta", "乙任务", project_label="info",
                        deps="01-alpha")
        fake.calls.clear()
        ready = mgs_records.startable_tasks(root, transport=fake)
        check(_issue_list_calls(fake) == 1,
              f"GitHub ready 应只获取一次任务集合,实际 {_issue_list_calls(fake)}")
        startable = {i["identity"] for i in ready["startable"]}
        check(startable == {"01-alpha"},
              f"依赖判断应使用同一集合,实际 {ready}")


def test_github_ready_does_not_consume_second_response_r1() -> None:
    """READ-03/R1:第二次响应对同一任务给出不同依赖时,本次不消费它。

    替身第一次返回「依赖:无」、第二次返回「依赖:02-missing」。修复后
    ready 只消费第一份集合,结果保持可开工且不混用两个时点。
    """

    with tempfile.TemporaryDirectory() as tmp:
        root = make_github_project(Path(tmp))

        class SequenceTransport(FakeTransport):
            """每次 GET /issues 依调用序号返回不同依赖的任务集合。"""

            def __init__(self) -> None:
                super().__init__()
                self._seq = 0
                self._list_calls = 0

            def request(self, method, path, body=None, *, auth=None):
                plain = path.split("?", 1)[0]
                if method == "GET" and plain.endswith("/issues"):
                    self._seq += 1
                    self._list_calls += 1
                    deps = "无" if self._seq == 1 else "02-missing"
                    seed = FakeTransport()
                    seed.seed_issue("01-alpha", "甲任务", deps=deps)
                    self.calls.append((method, path, body))
                    return 200, list(seed.issues)
                return super().request(method, path, body, auth=auth)

        fake = SequenceTransport()
        ready = mgs_records.startable_tasks(root, transport=fake)
        check(fake._list_calls == 1,
              f"R1:第二次预备响应不应被本次 ready 消费,实际第 {fake._list_calls} 次")
        startable = {i["identity"] for i in ready["startable"]}
        blocked = {i["identity"] for i in ready["blocked"]}
        check("01-alpha" in startable and "01-alpha" not in blocked
              and not any("02-missing" in r
                          for i in ready["blocked"] for r in i["reasons"]),
              f"本次应只使用第一份集合(依赖:无),不产生两时点混合,实际 {ready}")

        # 下一次顶层调用重新读取:看到第二响应改变后的依赖并更新分类
        ready2 = mgs_records.startable_tasks(root, transport=fake)
        check(fake._list_calls == 2,
              f"第二次顶层调用应重新读取(非缓存),实际第 {fake._list_calls} 次")
        blocked2 = {i["identity"]: i for i in ready2["blocked"]}
        check("01-alpha" in blocked2
              and any("02-missing" in r for r in blocked2["01-alpha"]["reasons"]),
              f"第二次调用应看到新依赖并更新分类,实际 {ready2}")


def test_github_ready_and_list_order_preserved() -> None:
    """READ-06:GitHub list 按身份排序,ready/deps 保留后端返回顺序。"""

    with tempfile.TemporaryDirectory() as tmp:
        root = make_github_project(Path(tmp))
        fake = FakeTransport()
        # 后端返回非身份顺序
        fake.seed_issue("03-gamma", "丙任务")
        fake.seed_issue("01-alpha", "甲任务")
        fake.seed_issue("02-beta", "乙任务", deps="01-alpha")
        listed = [t["identity"] for t in mgs_records.list_tasks(root,
                                                               transport=fake)]
        check(listed == ["01-alpha", "02-beta", "03-gamma"],
              f"list 应按身份排序,实际 {listed}")
        ready = mgs_records.startable_tasks(root, transport=fake)
        check([i["identity"] for i in ready["startable"]] == ["03-gamma",
                                                              "01-alpha"],
              f"ready 应保留后端返回顺序,实际 "
              f"{[i['identity'] for i in ready['startable']]}")
        graph = mgs_records.task_dependencies(root, transport=fake)
        check(list(graph["edges"].keys()) == ["03-gamma", "01-alpha", "02-beta"],
              f"deps 应保留后端返回顺序,实际 {list(graph['edges'])}")


def test_github_ready_online_to_offline_preserves_source() -> None:
    """READ-05:有缓存 → 在线转离线 ready 保留来源/时间/缓存标识;
    无缓存时明确失败,不回退本地。"""

    with tempfile.TemporaryDirectory() as tmp:
        root = make_github_project(Path(tmp))
        cache = Path(tmp) / "cache"
        fake = FakeTransport()
        fake.seed_issue("01-alpha", "甲任务")
        online = mgs_records.startable_tasks(root, transport=fake,
                                             cache_dir=cache)
        check(online["cached"] is False and online["fetched_at"]
              and online["source"]["backend"] == "github-issues",
              f"在线 ready 应携带当前确认元信息,实际 "
              f"{ {k: online.get(k) for k in ('cached','fetched_at','source')} }")
        check([i["identity"] for i in online["startable"]] == ["01-alpha"],
              "在线 ready 应基于远端集合给出可开工集合")
        fake.offline()
        offline = mgs_records.startable_tasks(root, transport=fake,
                                              cache_dir=cache)
        check(offline["cached"] is True and offline["fetched_at"]
              and offline["source"]["backend"] == "github-issues"
              and offline.get("cache_note"),
              f"离线 ready 应保留缓存标识、时间与来源,实际 {offline}")
        check([i["identity"] for i in offline["startable"]] == ["01-alpha"],
              "离线 ready 仍应基于缓存给出可开工集合")

        # 无缓存 + 离线:明确失败,绝不回退本地
        fresh = FakeTransport()
        fresh.offline()
        try:
            mgs_records.startable_tasks(root, transport=fresh,
                                        cache_dir=Path(tmp) / "empty")
        except mgs_records.RecordsError as exc:
            check("远端不可用" in str(exc) and "无缓存" in str(exc),
                  f"无缓存离线应明确失败并说明原因:{exc}")
        else:
            check(False, "无缓存离线 ready 应报错,不回退本地任务来源")


def test_startable_tasks_reports_cache_metadata() -> None:
    """S5:统一开工接口传递缓存元信息(是否缓存、抓取时间、来源)——
    断网时调用方能区分缓存推断与当前确认。"""

    with tempfile.TemporaryDirectory() as tmp:
        root = make_github_project(Path(tmp))
        cache = Path(tmp) / "cache"
        fake = FakeTransport()
        fake.seed_issue("01-alpha", "甲任务")
        online = mgs_records.startable_tasks(root, transport=fake, cache_dir=cache)
        meta = {key: online.get(key) for key in ("cached", "fetched_at", "source")}
        check(meta["cached"] is False and meta["fetched_at"]
              and meta["source"].get("backend") == "github-issues",
              f"在线开工结果应携带当前确认元信息,实际 {meta}")
        fake.offline()
        offline = mgs_records.startable_tasks(root, transport=fake, cache_dir=cache)
        meta = {key: offline.get(key) for key in ("cached", "fetched_at", "source")}
        check(meta["cached"] is True and meta["fetched_at"]
              and meta["source"].get("backend") == "github-issues",
              f"断网开工结果应携带缓存标记、抓取时间与来源,实际 {meta}")
        check([t["identity"] for t in offline["startable"]] == ["01-alpha"],
              "断网时仍应基于缓存给出可开工集合(并明示缓存状态)")


def test_github_list_show_read_config_once_and_necessary_reads() -> None:
    """AC1/AC4/READ-11:GitHub list/show 各自只读一次 CONFIG;

    show 保留集合定位、最新 Issue 详情与评论回读——不为减少请求删掉必要
    读取;list 按身份排序且在线结果不带离线标记。
    """

    with tempfile.TemporaryDirectory() as tmp:
        root = make_github_project(Path(tmp))
        fake = FakeTransport()
        fake.seed_issue("03-gamma", "丙任务")          # number 1
        issue = fake.seed_issue("01-alpha", "甲任务")  # number 2
        fake.seed_issue("02-beta", "乙任务", deps="01-alpha")  # number 3
        fake.comments[issue["number"]].append({
            "id": 9001, "body": "01-alpha 已交付证据。",
            "created_at": "2026-09-09T00:00:00Z"})

        with _ConfigReadCounter() as counter:
            listed = mgs_records.list_tasks(root, transport=fake)
        check(counter.count == 1,
              f"github list 应只读一次 CONFIG,实际 {counter.count} 次")
        check([t["identity"] for t in listed]
              == ["01-alpha", "02-beta", "03-gamma"],
              f"github list 应按身份排序,实际 {[t['identity'] for t in listed]}")
        check(isinstance(listed, list)
              and all("cached_read" not in t for t in listed),
              f"在线 list 不应带离线标记,实际 {listed}")

        fake.calls.clear()
        with _ConfigReadCounter() as counter:
            task = mgs_records.read_task(root, "01-alpha", transport=fake)
        check(counter.count == 1,
              f"github show 应只读一次 CONFIG,实际 {counter.count} 次")
        gets = [path.split("?", 1)[0] for method, path, _ in fake.calls
                if method == "GET"]
        check(any(path.endswith("/issues") for path in gets),
              f"github show 应保留集合定位读取,实际 {gets}")
        check(f"/repos/mygamestudio/issue-accept/issues/{issue['number']}" in gets,
              f"github show 应读取具体 Issue 详情,实际 {gets}")
        check(f"/repos/mygamestudio/issue-accept/issues/{issue['number']}/comments"
              in gets,
              f"github show 应读取评论,实际 {gets}")
        check([r["ref"] for r in task["results"]] == ["#issuecomment-9001"],
              f"github show 应回读评论承载的结果,实际 {task['results']}")
        check(task.get("body_sha256") and task.get("html_url"),
              f"github show 应保留正文指纹与链接,实际 {task}")


def test_github_offline_list_show_metadata_and_no_marker_leak() -> None:
    """AC5/READ-05/06:离线 list/show 保留各自缓存标识与来源说明;

    离线标记只出现在 list 的独立投影中,不原地污染来源集合与其他调用结果;
    无缓存时按现有方式失败,不回退本地。
    """

    with tempfile.TemporaryDirectory() as tmp:
        root = make_github_project(Path(tmp))
        cache = Path(tmp) / "cache"
        fake = FakeTransport()
        seed = fake.seed_issue("01-alpha", "甲任务")
        fake.comments[seed["number"]].append({
            "id": 7, "body": "01-alpha 证据", "created_at": "2026-09-09T00:00:00Z"})
        online = mgs_records.list_tasks(root, transport=fake, cache_dir=cache)
        check(len(online) == 1 and "cached_read" not in online[0],
              "在线 list 不应带缓存标记")

        fake.offline()
        offline = mgs_records.list_tasks(root, transport=fake, cache_dir=cache)
        check(offline and all(t.get("cached_read") is True for t in offline),
              f"离线 list 应逐任务标注 cached_read,实际 {offline}")
        # 离线标记不污染来源集合:再取一次原始集合 payload,任务字典仍无该键
        payload = mgs_records.github_backend(
            root, transport=fake, cache_dir=cache).fetch_tasks()
        check(all("cached_read" not in t for t in payload["tasks"]),
              "list 的离线标记是独立投影,不得原地污染来源集合")

        task = mgs_records.read_task(root, "01-alpha", transport=fake,
                                     cache_dir=cache)
        check(task.get("cached_read") is True
              and "缓存" in task.get("cached_note", "")
              and task.get("body_sha256"),
              f"离线 show 应保留缓存标识、说明与正文指纹,实际 {task}")
        check(task["results"] == [],
              "离线 show 评论未缓存,结果清单应为空(既有离线语义)")

        # 离线标记不污染其他调用结果:ready 条目不应携带该键
        ready = mgs_records.startable_tasks(root, transport=fake, cache_dir=cache)
        entries = ready["startable"] + ready["blocked"]
        check(entries and all("cached_read" not in e for e in entries),
              f"list 的离线标记不得污染 ready 结果,实际 {entries}")

        # 无缓存 + 离线:list/show 各自明确失败,不回退本地
        fresh = FakeTransport()
        fresh.offline()
        for call in (lambda: mgs_records.list_tasks(root, transport=fresh,
                                                    cache_dir=Path(tmp) / "empty"),
                     lambda: mgs_records.read_task(root, "01-alpha",
                                                   transport=fresh,
                                                   cache_dir=Path(tmp) / "empty")):
            try:
                call()
            except mgs_records.RecordsError as exc:
                check("远端不可用" in str(exc) and "无缓存" in str(exc),
                      f"无缓存离线应明确失败并说明原因:{exc}")
            else:
                check(False, "无缓存离线应报错,不回退本地任务来源")

TESTS = (
    test_github_ready_fetches_task_set_once,
    test_github_ready_does_not_consume_second_response_r1,
    test_github_ready_and_list_order_preserved,
    test_github_ready_online_to_offline_preserves_source,
    test_startable_tasks_reports_cache_metadata,
    test_github_list_show_read_config_once_and_necessary_reads,
    test_github_offline_list_show_metadata_and_no_marker_leak,
)

if __name__ == "__main__":
    sys.exit(run_theme("一次来源 ready 与列表/单任务读取", TESTS, FAILURES))

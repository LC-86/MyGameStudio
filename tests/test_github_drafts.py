#!/usr/bin/env python3
"""离线草稿保存与发布归属。

任务票 11 从 tests/test_github_backend.py 按真实行为主题拆出;检查含义与原
案例保持一致,仅重组位置。原总入口仍聚合本主题。本主题可直接运行:

    python3 -B tests/test_github_drafts.py
"""

import json
import sys
import tempfile
from pathlib import Path

from github_backend_transport import (
    FakeTransport, backend_for,
)
from github_backend_fixtures import (
    REPO, make_checker, make_github_project, run_theme,
)

import mgs_github  # noqa: E402
import mgs_records  # noqa: E402

FAILURES, check = make_checker()


def test_offline_write_draft_and_publish() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = make_github_project(Path(tmp))
        cache = Path(tmp) / "gh-cache"
        fake = FakeTransport()
        backend = backend_for(root, fake, cache)
        fake.offline()
        result = backend.create_task("01-alpha", "甲任务", {"当前目标": "演示"})
        check(result["published"] is False and result["status"] == "未发布草稿",
              f"离线创建应保存未发布草稿,实际 {result}")
        check(Path(result["draft"]).is_file(), "草稿文件应实际落盘")
        check("不静默切换本地后端" in result["note"], "草稿说明必须声明不静默切本地")
        draft = json.loads(Path(result["draft"]).read_text(encoding="utf-8"))
        check(draft["status"] == "未发布草稿" and draft["repo"] == REPO,
              f"草稿应标明状态与目标仓库,实际 {draft}")
        check(mgs_github.GithubBackend.__name__ and draft["op"] == "create_task",
              "草稿应记录原始操作便于重放")
        # 远端恢复后发布:草稿重放成功并标记;远端只有一个 01-alpha
        fake._offline = False
        published = backend.publish_drafts()
        check(published["published_count"] == 1,
              f"草稿应发布成功,实际 {published}")
        ids = [t["identity"] for t in mgs_records.list_tasks(root, transport=fake)]
        check(ids == ["01-alpha"], f"发布后远端应恰有一个任务,实际 {ids}")
        check(not list((cache / "drafts").glob("*.json")),
              "已发布草稿应移出待发布目录")


def test_offline_write_without_cache_dir_refuses() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = make_github_project(Path(tmp))
        fake = FakeTransport()
        fake.offline()
        backend = backend_for(root, fake)  # 无缓存目录
        try:
            backend.create_task("01-alpha", "甲任务", {})
        except mgs_github.GithubRecordsError as exc:
            check("草稿目录" in str(exc) or "cache" in str(exc),
                  f"无草稿目录时应说明且不丢弃请求:{exc}")
        else:
            check(False, "无草稿目录时不得静默丢弃写入请求")


def test_draft_unique_identity_no_overwrite() -> None:
    """S6:同秒两次不同操作的草稿互不覆盖;每个待发布操作有稳定唯一身份;
    同一操作重复保存保持幂等(不产生重复重放)。"""

    with tempfile.TemporaryDirectory() as tmp:
        root = make_github_project(Path(tmp))
        cache = Path(tmp) / "cache"
        fake = FakeTransport()
        fake.seed_issue("01-alpha", "甲任务")
        backend = backend_for(root, fake, cache)
        backend.fetch_tasks()  # 在线抓取建立缓存(离线草稿路径需要)
        fake.offline()
        real_datetime = mgs_github._dt.datetime

        class FixedDatetime(real_datetime):
            @classmethod
            def now(cls, tz=None):
                return cls(2026, 9, 9, 1, 2, 3, tzinfo=tz)

        mgs_github._dt.datetime = FixedDatetime
        try:
            one = backend.append_result("01-alpha", "证据一")
            two = backend.append_result("01-alpha", "证据二")
            again = backend.append_result("01-alpha", "证据二")
        finally:
            mgs_github._dt.datetime = real_datetime
        check(one["draft"] != two["draft"],
              f"同秒两次不同操作应产生两份独立草稿,实际同路径 {one['draft']}")
        drafts = list((cache / "drafts").glob("*.json"))
        check(len(drafts) == 2,
              f"应恰有两份草稿(同一操作重复保存幂等),实际 {len(drafts)} 份")
        remaining = {json.loads(path.read_text(encoding="utf-8"))
                     ["args"]["result_markdown"] for path in drafts}
        check(remaining == {"证据一", "证据二"},
              f"两份草稿内容都应保留,实际 {remaining}")


def test_draft_identity_includes_repo_cross_repo() -> None:
    """SP-3:草稿身份含目标仓库——同一秒、同一缓存目录、两个各有授权的仓库
    保存同参数的离线创建,两份草稿各自保存(互不顶替、不得误报幂等);
    发布各归各仓;同仓库同参数重复保存的幂等语义不回退(S6)。"""

    with tempfile.TemporaryDirectory() as tmp:
        base = Path(tmp)
        root = make_github_project(base / "project")
        config = mgs_records.load_config(root)
        old = {**config, "repo": {"host": "github.com", "owner": "old-owner",
                                  "repo": "private-repo"},
               "external": ("github.com/old-owner/private-repo:"
                            "issues-write(已授权旧仓库)")}
        offline = FakeTransport()
        offline.offline()
        previous = mgs_github.GithubBackend(old, offline, base / "shared-cache")
        current = mgs_github.GithubBackend(config, offline, base / "shared-cache")
        real_datetime = mgs_github._dt.datetime

        class FixedDatetime(real_datetime):
            @classmethod
            def now(cls, tz=None):
                return cls(2026, 9, 9, 1, 2, 3, tzinfo=tz)

        mgs_github._dt.datetime = FixedDatetime
        try:
            a = previous.create_task("09-same", "same title",
                                     {"当前目标": "same goal"})
            z = current.create_task("09-same", "same title",
                                    {"当前目标": "same goal"})
            again = current.create_task("09-same", "same title",
                                        {"当前目标": "same goal"})
        finally:
            mgs_github._dt.datetime = real_datetime
        check(a.get("draft") and z.get("draft") and a["draft"] != z["draft"],
              f"两仓库同秒同参数的草稿身份应不同(身份含仓库),"
              f"实际 {a.get('draft')} / {z.get('draft')}")
        check(z.get("idempotent") is not True,
              f"跨仓库请求不是同一操作的重放,不得按幂等顶替,实际 {z}")
        drafts = [json.loads(p.read_text(encoding="utf-8"))
                  for p in (base / "shared-cache/drafts").glob("*.json")]
        check(len(drafts) == 2,
              f"两仓库应各存各的草稿,实际 {len(drafts)} 份:"
              f"{[d.get('repo') for d in drafts]}")
        check({d.get("repo") for d in drafts}
              == {"github.com/old-owner/private-repo", REPO},
              f"两份草稿应各自记录目标仓库,实际 {[d.get('repo') for d in drafts]}")
        check(again.get("idempotent") is True,
              f"同仓库同参数重复保存应保持幂等(S6 语义不回退),实际 {again}")
        check(len(list((base / "shared-cache/drafts").glob("*.json"))) == 2,
              "幂等重放不得产生第三份草稿")
        # 发布各归各仓:当前仓库后端只发布自己的草稿(S1 拒绝旧仓库草稿),
        # 当前仓库恰收到一次创建请求
        online = FakeTransport()
        current_online = mgs_github.GithubBackend(config, online,
                                                  base / "shared-cache")
        publish = current_online.publish_drafts()
        check(publish["published_count"] == 1,
              f"只有本仓库草稿可发布,实际 {publish}")
        posts = [c for c in online.calls if c[0] == "POST"]
        check(len(posts) == 1 and posts[0][1].endswith("/issues"),
              f"当前仓库应恰收到一次创建请求,实际 {posts}")
        check(any("任务身份:09-same" in i["body"] for i in online.issues),
              "本仓库草稿应实际创建为任务")
        check(len(list((base / "shared-cache/drafts").glob("*.json"))) == 1,
              "旧仓库草稿应原样保留待其自己的后端发布")


def test_publish_drafts_refuses_cross_repo_draft() -> None:
    """S1:草稿记录的仓库与当前后端仓库不一致时拒绝发布该草稿——不发请求、
    不标记已发布、如实报告;选择新后端不构成旧草稿的迁移授权。"""

    with tempfile.TemporaryDirectory() as tmp:
        base = Path(tmp)
        root = make_github_project(base / "project")
        config = mgs_records.load_config(root)
        old = {**config, "repo": {"host": "github.com", "owner": "old-owner",
                                  "repo": "private-repo"},
               "external": ("github.com/old-owner/private-repo:"
                            "issues-write(已授权旧仓库)")}
        offline = FakeTransport()
        offline.offline()
        previous = mgs_github.GithubBackend(old, offline, base / "shared-cache")
        previous.create_task("09-private", "仅旧仓库的任务", {"当前目标": "旧仓库材料"})
        fake = FakeTransport()
        current = mgs_github.GithubBackend(config, fake, base / "shared-cache")
        outcome = current.publish_drafts()
        writes = [c[1] for c in fake.calls if c[0] == "POST"]
        check(writes == [], f"跨仓库草稿不得发出任何远端写请求,实际 {writes}")
        check(outcome["published_count"] == 0,
              f"跨仓库草稿不得标记已发布,实际 {outcome}")
        check(len(list((base / "shared-cache/drafts").glob("*.json"))) == 1,
              "被拒草稿应原样保留在待发布目录(不移动、不删除)")
        check(any("仓库" in str(r.get("outcome", ""))
                  and "迁移" in str(r.get("outcome", ""))
                  for r in outcome["results"]),
              f"拒绝原因应说明仓库不一致且不构成迁移授权,实际 {outcome['results']}")

TESTS = (
    test_offline_write_draft_and_publish,
    test_offline_write_without_cache_dir_refuses,
    test_draft_unique_identity_no_overwrite,
    test_draft_identity_includes_repo_cross_repo,
    test_publish_drafts_refuses_cross_repo_draft,
)

if __name__ == "__main__":
    sys.exit(run_theme("离线草稿保存与发布归属", TESTS, FAILURES))

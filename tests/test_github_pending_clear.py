#!/usr/bin/env python3
"""待补索引清除归属(逐路径核验)。

任务票 11 从 tests/test_github_backend.py 按真实行为主题拆出;检查含义与原
案例保持一致,仅重组位置。原总入口仍聚合本主题。本主题可直接运行:

    python3 -B tests/test_github_pending_clear.py
"""

import json
import sys
import tempfile
from pathlib import Path

from github_backend_transport import (
    FakeTransport, _OnceReadFailTransport, _pending_digest,
    _pending_registration_content, backend_for,
)
from github_backend_fixtures import (
    REPO, make_checker, make_github_project, run_theme,
)

import mgs_result_publication as publication  # noqa: E402

FAILURES, check = make_checker()


def _current_file(backend, identity: str, body: str):
    """当前布局登记路径(接缝调整:路径构造归发布恢复 module,不再经
    适配器私有方法;断言语义不变)。"""

    return publication.pending_index_file(backend.repo, backend.cache_dir,
                                          identity, body)


def _legacy_file(backend, identity: str, body: str):
    return publication.legacy_pending_index_file(backend.repo, backend.cache_dir,
                                                 identity, body)


def _clear(backend, identity: str, body: str) -> None:
    publication.clear_pending_index(backend.repo, backend.cache_dir,
                                    identity, body)


def test_append_result_pending_clear_keeps_foreign_legacy_registration() -> None:
    """SP-17(自然升级序列核心反例):旧平铺布局保存另一完整身份 B 的
    健康登记、当前布局保存本请求 A 的登记时,A 补齐索引触发的清理不得凭
    A 的一次核验无条件 unlink 两个路径——旧实现正是这样误删 B 的登记,
    使 B 重试读前失败被当作全新发布重新 POST(3 POST、B 正文 2 条)。
    期望:每个待删除文件分别通过自身完整身份核验,B 的旧登记保留;B 重试
    凭自己的登记待恢复(不重新 POST、恰 1 条、总 posts=2)。"""

    with tempfile.TemporaryDirectory() as tmp:
        base = Path(tmp)
        root = make_github_project(base / "project")
        cache = base / "cache"
        fake = _OnceReadFailTransport()
        fake.seed_issue("01-task", "甲任务")
        backend = backend_for(root, fake, cache)
        a, b = "collision-result-79891", "collision-result-80657"
        check(_pending_digest("01-task", a) == _pending_digest("01-task", b),
              "前置:碰撞对两正文应得到同一 8 hex 短摘要(同一登记短摘要)")
        # 升级前:旧实现给 B 留下平铺健康登记(按 review5-01 兼容测试的
        # 旧格式构造方式:B 真实部分成功留登记,再原样归位到旧平铺路径)
        fake.fail("PATCH", "/issues/1", "timeout")
        first_b = backend.append_result("01-task", b)
        check(first_b.get("published") is True and first_b.get("partial") is True,
              f"前置:B 首轮应如实部分成功,实际 {first_b}")
        b_current = next((cache / "pending-index").rglob("*.json"))
        legacy = (cache / "pending-index"
                  / f"append-result-01-task-"
                    f"{_pending_digest('01-task', b)}.json")
        legacy.write_text(b_current.read_text(encoding="utf-8"),
                          encoding="utf-8")
        b_current.unlink()
        check(legacy.exists(),
              "前置:B 的旧平铺健康登记应就位(自然升级前的在盘状态)")
        # 升级后:A 读前失败 partial——旧布局 B 的登记身份不匹配(不冒认,
        # SP-11),A 按首试发布并留新布局登记;两登记共存
        fake.read_fail = True
        second_a = backend.append_result("01-task", a)
        check(second_a.get("published") is True and second_a.get("partial") is True,
              f"前置:A 首轮应如实部分成功,实际 {second_a}")
        before = sorted(p.relative_to(cache / "pending-index").as_posix()
                        for p in (cache / "pending-index").rglob("*.json"))
        check(len(before) == 2,
              f"前置:清理前应恰两份登记共存(旧平铺 B + 新布局 A),"
              f"实际 {before}")
        # A 补齐索引触发清理:只应清除 A 自己的新布局登记,B 的旧平铺
        # 登记不因他人请求的清理被误删(SP-17 红点)
        fake._fail = []
        third_a = backend.append_result("01-task", a)
        check(third_a.get("index_updated") is True
              and third_a.get("comment_id") == second_a.get("comment_id"),
              f"SP-17:A 补齐应收养既有评论并完成索引,实际 {third_a}")
        check(legacy.exists(),
              "SP-17:A 补齐清理后 B 的旧平铺登记应仍在(不得凭 A 的核验"
              "授权删除另一完整身份 B 的健康登记)")
        after = sorted(p.relative_to(cache / "pending-index").as_posix()
                       for p in (cache / "pending-index").rglob("*.json"))
        check(after == [legacy.relative_to(cache / "pending-index").as_posix()],
              f"SP-17:清理应只清除 A 自己的新布局登记,B 的旧登记保留,"
              f"实际 {after}")
        # B 重试读前失败:凭自己的旧登记待恢复(不重新 POST)
        fake.read_fail = True
        fourth_b = backend.append_result("01-task", b)
        check(fourth_b.get("published") is True and fourth_b.get("partial") is True
              and fourth_b.get("comment_id") == first_b.get("comment_id"),
              f"SP-17:B 重试读前失败应凭自己的登记待恢复(不重新 POST),"
              f"实际 {fourth_b}")
        check(fourth_b.get("index_updated") is False,
              f"SP-17:B 待恢复应如实表达索引仍未完成,实际 {fourth_b}")
        posts = [c for c in fake.calls if c[0] == "POST" and "/comments" in c[1]]
        check(len(posts) == 2,
              f"SP-17:全程应恰 2 次 POST(A/B 首试各 1 次;重试不发布),"
              f"实际 {len(posts)} 次")
        check(sum(c["body"] == f"任务:01-task\n\n{b}"
                  for c in fake.comments[1]) == 1,
              "SP-17:B 正文评论应恰 1 条(登记不被误删才不重复发布)")
        check(sum(c["body"] == f"任务:01-task\n\n{a}"
                  for c in fake.comments[1]) == 1,
              "SP-17:A 正文评论应恰 1 条")
        # B 彻底恢复后重试:经读前收养补齐索引,登记清除(链路闭合)
        fifth_b = backend.append_result("01-task", b)
        check(fifth_b.get("index_updated") is True
              and fifth_b.get("comment_id") == first_b.get("comment_id"),
              f"SP-17:B 补齐应收养既有评论并完成索引,实际 {fifth_b}")
        check(not list((cache / "pending-index").rglob("*.json")),
              "SP-17:B 补齐后登记应清除(迁移+清除链路闭合)")
        posts = [c for c in fake.calls if c[0] == "POST" and "/comments" in c[1]]
        check(len(posts) == 2,
              f"SP-17:补齐重试经读前收养不新增 POST,实际 {len(posts)} 次")


def test_append_result_pending_clear_removes_same_identity_both_layouts() -> None:
    """SP-17 不复活语义保持:同身份双布局残留(迁移中途失败留下的旧副本)
    在逐路径核验下两处都属当前请求、都应清除——「已清除的登记不因迁移
    残留复活」(review5-01)不因本票回退。"""

    with tempfile.TemporaryDirectory() as tmp:
        base = Path(tmp)
        root = make_github_project(base / "project")
        cache = base / "cache"
        fake = FakeTransport()
        fake.seed_issue("01-alpha", "甲任务")
        backend = backend_for(root, fake, cache)
        # 部分成功留新布局登记,再复制一份到旧平铺路径(同身份双布局残留)
        fake.fail("PATCH", "/issues/1", "timeout")
        first = backend.append_result("01-alpha", "交付证据")
        check(first.get("partial") is True,
              f"前置:首轮应部分成功,实际 {first}")
        current = next((cache / "pending-index").rglob("*.json"))
        legacy = (cache / "pending-index"
                  / f"append-result-01-alpha-"
                    f"{_pending_digest('01-alpha', '交付证据')}.json")
        legacy.write_text(current.read_text(encoding="utf-8"), encoding="utf-8")
        check(current.exists() and legacy.exists(),
              "前置:同身份双布局残留就位(迁移中途失败的在盘形态)")
        # 补齐索引触发清理:两处同身份健康登记都属当前请求,都清除
        fake._fail = []
        second = backend.append_result("01-alpha", "交付证据")
        check(second.get("index_updated") is True
              and second.get("comment_id") == first.get("comment_id"),
              f"不复活:补齐应收养既有评论并完成索引,实际 {second}")
        check(not current.exists() and not legacy.exists(),
              "不复活:同身份双布局残留应一并清除(不自旧文件复活)")
        check(not list((cache / "pending-index").rglob("*.json")),
              "不复活:清理后不得残留任何登记文件")


def test_clear_pending_index_verifies_each_path_independently() -> None:
    """SP-17 分侧语义:待删除文件自己的登记与当前请求身份不匹配(他请求
    的健康登记)/JSON 无效/回执不完整时,该路径保守保留;另一路径上的同
    身份健康登记照常清除——每个文件按自身内容独立判定,互不代劳、互不
    株连(修复前:单次核验通过则两路径无条件删除,不通过则两路径全留)。"""

    own = ("01-task", "collision-result-79891")
    foreign_body = "collision-result-80657"
    cases = [
        # (说明, 保留侧内容, 保留侧在旧平铺布局?)
        ("旧平铺是他请求的健康登记", _pending_registration_content(
            "01-task", foreign_body, 5100, "#issuecomment-5100"), True),
        ("当前布局是他请求的健康登记", _pending_registration_content(
            "01-task", foreign_body, 5100, "#issuecomment-5100"), False),
        ("旧平铺是无效 JSON", "{ not valid json", True),
        ("当前布局是回执不完整登记", {
            **_pending_registration_content("01-task", own[1], 5101,
                                            "#issuecomment-5101"),
            "comment_id": None}, False),
        ("旧平铺是身份形态不完整登记", {
            "op": "append_result", "repo": REPO,
            "comment_id": 5100, "ref": "#issuecomment-5100"}, True),
    ]
    for label, kept_content, kept_on_legacy in cases:
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            root = make_github_project(base / "project")
            cache = base / "cache"
            backend = backend_for(root, FakeTransport(), cache)
            current = _current_file(backend, *own)
            legacy = _legacy_file(backend, *own)
            healthy = _pending_registration_content(
                own[0], own[1], 5101, "#issuecomment-5101")
            kept_path, cleared_path = ((legacy, current) if kept_on_legacy
                                       else (current, legacy))
            kept_path.parent.mkdir(parents=True, exist_ok=True)
            kept_path.write_text(kept_content if isinstance(kept_content, str)
                                 else json.dumps(kept_content,
                                                 ensure_ascii=False),
                                 encoding="utf-8")
            cleared_path.parent.mkdir(parents=True, exist_ok=True)
            cleared_path.write_text(json.dumps(healthy, ensure_ascii=False),
                                    encoding="utf-8")
            _clear(backend, *own)
            check(kept_path.exists(),
                  f"SP-17 分侧({label}):该路径应保守保留(不得由另一路径"
                  "的核验代劳删除)")
            check(not cleared_path.exists(),
                  f"SP-17 分侧({label}):另一路径同身份健康登记应正常清除")
            if not isinstance(kept_content, str) and kept_path.exists():
                check(json.loads(kept_path.read_text(encoding="utf-8"))
                      == kept_content,
                      f"SP-17 分侧({label}):保留侧文件内容不应被改动")


def test_clear_pending_index_unreadable_path_kept_quietly() -> None:
    """SP-17 保守性:清理阶段路径不可读(如登记路径被目录占用)/损坏
    (非 JSON 内容)时不抛异常、该侧保守保留;另一路径同身份健康登记照常
    清除——损坏登记保持原位由人工按哨兵处置,清理沉默沿既有口径。"""

    own = ("01-alpha", "交付证据")
    cases = [("登记路径被目录占用(不可读)", "current"),
             ("旧平铺是非 JSON 内容(损坏)", "legacy")]
    for label, broken_side in cases:
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            root = make_github_project(base / "project")
            cache = base / "cache"
            backend = backend_for(root, FakeTransport(), cache)
            current = _current_file(backend, *own)
            legacy = _legacy_file(backend, *own)
            healthy = _pending_registration_content(
                own[0], own[1], 5101, "#issuecomment-5101")
            current.parent.mkdir(parents=True, exist_ok=True)
            legacy.parent.mkdir(parents=True, exist_ok=True)
            if broken_side == "current":
                current.mkdir(parents=True)  # 路径被目录占用:read_text 抛 OSError
                broken, intact = current, legacy
            else:
                legacy.write_text("\x00not-json{{", encoding="utf-8")
                broken, intact = legacy, current
            intact.write_text(json.dumps(healthy, ensure_ascii=False),
                              encoding="utf-8")
            try:
                _clear(backend, *own)
                raised = None
            except Exception as exc:  # noqa: BLE001 — 红点:清理阶段不得抛异常
                raised = exc
            check(raised is None,
                  f"SP-17 保守({label}):清理不得因不可读/损坏路径抛异常,"
                  f"实际 {raised!r}")
            check(broken.exists(),
                  f"SP-17 保守({label}):不可读/损坏侧应保守保持原位"
                  "(由人工按哨兵处置)")
            check(not intact.exists(),
                  f"SP-17 保守({label}):另一路径同身份健康登记应照常清除")

TESTS = (
    test_append_result_pending_clear_keeps_foreign_legacy_registration,
    test_append_result_pending_clear_removes_same_identity_both_layouts,
    test_clear_pending_index_verifies_each_path_independently,
    test_clear_pending_index_unreadable_path_kept_quietly,
)

if __name__ == "__main__":
    sys.exit(run_theme("待补索引清除归属(逐路径核验)", TESTS, FAILURES))

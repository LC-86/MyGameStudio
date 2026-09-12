#!/usr/bin/env python3
"""待补索引登记:碰撞、损坏与旧布局迁移。

任务票 11 从 tests/test_github_backend.py 按真实行为主题拆出;检查含义与原
案例保持一致,仅重组位置。原总入口仍聚合本主题。本主题可直接运行:

    python3 -B tests/test_github_pending_index.py
"""

import json
import sys
import tempfile
from pathlib import Path

from github_backend_transport import (
    FakeTransport, _OnceReadFailTransport, _pending_digest,
    _pending_full_digest, backend_for,
)
from github_backend_fixtures import (
    make_checker, make_github_project, run_theme,
)

FAILURES, check = make_checker()


def test_append_result_pending_collision_does_not_adopt_foreign_identity() -> None:
    """SP-11:登记文件名只取 8 hex 短摘要,同仓库同任务的两个不同结果正文
    可确定性碰撞共用同一登记文件。B(不同正文)的读前收养查询失败时
    不得冒认 A 的登记身份(published=true + A 的 comment_id,而 B 从未
    发布)——登记内容保留完整身份(op/args/目标仓库),读入时与当前
    请求逐项核对,不一致按无登记处理:B 按首试语义发布自己的评论;
    A 的登记不被冒认、也不被 B 的补齐清除误删(不误删他人登记)。"""

    with tempfile.TemporaryDirectory() as tmp:
        base = Path(tmp)
        root = make_github_project(base / "project")
        cache = base / "cache"
        fake = _OnceReadFailTransport()
        fake.seed_issue("01-task", "甲任务")
        backend = backend_for(root, fake, cache)
        # 复审确定性碰撞对(80,658 候选搜索所得,同一摘要 346df0e9):
        # 先自证两正文在当前实现下解析到同一登记文件路径
        result_a = "collision-result-79891"
        result_b = "collision-result-80657"
        check(_pending_digest("01-task", result_a)
              == _pending_digest("01-task", result_b),
              "前置:碰撞对两正文应得到同一 8 hex 短摘要(共用登记文件)")
        # A 首次调用部分成功:评论已发布、索引 PATCH 超时 → 留下登记
        fake.fail("PATCH", "/issues/1", "timeout")
        first = backend.append_result("01-task", result_a)
        check(first.get("published") is True and first.get("partial") is True,
              f"前置:A 首轮应如实部分成功,实际 {first}")
        registration = list((cache / "pending-index").rglob("*.json"))
        check(len(registration) == 1, "前置:A 的部分成功应留下待补索引登记")
        # B 的第一次调用仅读前 GET 超时(反例靶点):不得冒认 A 的登记
        fake._fail = []
        fake.read_fail = True
        second = backend.append_result("01-task", result_b)
        check(second.get("comment_id") != first.get("comment_id"),
              f"SP-11:B 不得冒认 A 的 comment_id,实际 "
              f"{second.get('comment_id')} vs {first.get('comment_id')}")
        check(second.get("published") is True
              and second.get("index_updated") is True,
              f"SP-11:B 应按首试语义发布自己的评论并补齐索引,实际 {second}")
        check(any(c["body"] == f"任务:01-task\n\n{result_b}"
                  for c in fake.comments[1]),
              "SP-11:B 应已发布自己的评论正文(而非只认 A 的评论)")
        check(list((cache / "pending-index").rglob("*.json")) == registration,
              "SP-11:B 的补齐清除不得误删 A 的登记(不误删他人登记)")
        # A 重试且读前查询又失败:凭自己的登记保持待恢复(既有语义不回退)
        fake._fail = []
        fake.read_fail = True
        third = backend.append_result("01-task", result_a)
        check(third.get("published") is True and third.get("partial") is True
              and third.get("comment_id") == first.get("comment_id"),
              f"SP-11:A 凭自己的登记应保持待恢复(review3-01 语义不回退),"
              f"实际 {third}")
        posts = [c for c in fake.calls if c[0] == "POST" and "/comments" in c[1]]
        check(len(posts) == 2,
              f"全程应恰 2 次 POST(A 首试 1 次+B 首试 1 次;A 待恢复不发布),"
              f"实际 {len(posts)} 次")


def test_append_result_pending_registration_missing_fields_disclosed_corrupt() -> None:
    """SP-11 旁证:登记文件是合法 JSON 但缺身份字段(空对象形态)时,不得
    静默当作可核验的登记——返回空身份却仍称已确认发布。形态不完整
    (缺字段/空身份)按登记损坏披露(corrupt 语义沿既有非法 JSON 行为:
    待恢复、不重发、提示人工核对)。"""

    with tempfile.TemporaryDirectory() as tmp:
        base = Path(tmp)
        root = make_github_project(base / "project")
        cache = base / "cache"
        fake = FakeTransport()
        fake.seed_issue("01-alpha", "甲任务")
        backend = backend_for(root, fake, cache)
        fake.fail("PATCH", "/issues/1", "timeout")
        backend.append_result("01-alpha", "交付证据")  # 部分成功留登记
        pending_file = next((cache / "pending-index").rglob("*.json"))
        pending_file.write_text("{}", encoding="utf-8")  # 合法 JSON、缺字段
        fake._fail = []
        fake.fail("GET", "/comments", "timeout")
        second = backend.append_result("01-alpha", "交付证据")
        note = second.get("note") or ""
        check(any(word in note for word in ("不可读", "损坏", "corrupt", "不完整")),
              f"SP-11:缺字段登记应披露登记损坏(形态不完整),实际 note={note!r}")
        check(second.get("comment_id") is None,
              f"SP-11:形态不完整的登记不得冒用评论身份,实际 {second}")
        check("人工核对" in note,
              f"SP-11:登记损坏披露应提示人工核对,实际 note={note!r}")
        check(len(fake.comments[1]) == 1,
              f"登记损坏的保守方向是不重发(沿 corrupt 语义),替身评论应仍恰 1,"
              f"实际 {len(fake.comments[1])} 条")
        posts = [c for c in fake.calls if c[0] == "POST" and "/comments" in c[1]]
        check(len(posts) == 1,
              f"登记损坏不应触发重发(全程恰 1 次 POST),实际 {len(posts)} 次")


def test_append_result_pending_registration_corrupt_json_keeps_recovery() -> None:
    """SP-11 回归守卫:登记文件为非法 JSON 时,review3-01 建立的 corrupt
    待恢复行为保持(不重发、披露登记不可读、提示人工核对)——本票的
    身份核验不回退该语义。"""

    with tempfile.TemporaryDirectory() as tmp:
        base = Path(tmp)
        root = make_github_project(base / "project")
        cache = base / "cache"
        fake = FakeTransport()
        fake.seed_issue("01-alpha", "甲任务")
        backend = backend_for(root, fake, cache)
        fake.fail("PATCH", "/issues/1", "timeout")
        backend.append_result("01-alpha", "交付证据")  # 部分成功留登记
        pending_file = next((cache / "pending-index").rglob("*.json"))
        pending_file.write_text("{", encoding="utf-8")  # 非法 JSON
        fake._fail = []
        fake.fail("GET", "/comments", "timeout")
        second = backend.append_result("01-alpha", "交付证据")
        note = second.get("note") or ""
        check("不可读" in note or "损坏" in note or "corrupt" in note,
              f"SP-11:非法 JSON 登记应披露登记不可读,实际 note={note!r}")
        check(second.get("published") is True and second.get("partial") is True,
              f"非法 JSON 登记应保持待恢复(不当作全新发布),实际 {second}")
        posts = [c for c in fake.calls if c[0] == "POST" and "/comments" in c[1]]
        check(len(posts) == 1,
              f"非法 JSON 登记不应触发重发(全程恰 1 次 POST),实际 {len(posts)} 次")


def test_append_result_pending_collision_both_partial_coexist() -> None:
    """SP-14:碰撞对(A/B 同仓库同任务不同正文、同一 8 hex 短摘要)先后
    partial 时,后者的登记不得覆盖前者——不同完整身份的登记共存,任一
    请求的重试都能找回自己的登记:A 恢复重试(仅读前 GET 超时)不重新
    POST、保持待恢复;B 同理;互不干扰、互不误删;补齐后各自清除。"""

    with tempfile.TemporaryDirectory() as tmp:
        base = Path(tmp)
        root = make_github_project(base / "project")
        cache = base / "cache"
        fake = _OnceReadFailTransport()
        fake.seed_issue("01-task", "甲任务")
        backend = backend_for(root, fake, cache)
        result_a = "collision-result-79891"
        result_b = "collision-result-80657"
        check(_pending_digest("01-task", result_a)
              == _pending_digest("01-task", result_b),
              "前置:碰撞对两正文应得到同一 8 hex 短摘要(同一登记短摘要)")
        # A 首次调用部分成功:评论已发布、索引 PATCH 超时 → 留下 A 的登记
        fake.fail("PATCH", "/issues/1", "timeout")
        first = backend.append_result("01-task", result_a)
        check(first.get("published") is True and first.get("partial") is True,
              f"前置:A 首轮应如实部分成功,实际 {first}")
        # B 的首次调用读前 GET 超时:无自己的登记(不冒认 A 的,SP-11 语义
        # 保持)→ 按首试语义发布自己的评论;索引 PATCH 仍超时 → B 也部分
        # 成功、留下 B 的登记(不得覆盖 A 的)
        fake.read_fail = True
        second = backend.append_result("01-task", result_b)
        check(second.get("published") is True and second.get("partial") is True,
              f"前置:B 首轮应如实部分成功,实际 {second}")
        registrations = sorted(
            p.relative_to(cache / "pending-index").as_posix()
            for p in (cache / "pending-index").rglob("*.json"))
        check(len(registrations) == 2,
              f"SP-14:碰撞对先后 partial 的两份登记应共存(不同完整身份"
              f"不同文件),实际 {registrations}")
        check(any(_pending_full_digest("01-task", result_a) in name
                  for name in registrations)
              and any(_pending_full_digest("01-task", result_b) in name
                      for name in registrations),
              f"SP-14:两份登记应分别以 A/B 完整身份哈希为文件名落盘,"
              f"实际 {registrations}")
        # A 恢复重试,仅读前 GET 超时(反例靶点;PATCH 已恢复):必须凭
        # 自己的登记保持待恢复,不得当作全新发布而重新 POST(登记被 B
        # 覆盖时 A 会失去登记、被当成首试重新 POST 第三条)
        fake._fail = []
        fake.read_fail = True
        third = backend.append_result("01-task", result_a)
        check(third.get("published") is True and third.get("partial") is True
              and third.get("comment_id") == first.get("comment_id"),
              f"SP-14:A 恢复重试应凭自己的登记保持待恢复(不重新 POST),"
              f"实际 {third}")
        # B 恢复重试,仅读前 GET 超时:同理凭自己的登记保持待恢复
        fake._fail = []
        fake.read_fail = True
        fourth = backend.append_result("01-task", result_b)
        check(fourth.get("published") is True and fourth.get("partial") is True
              and fourth.get("comment_id") == second.get("comment_id"),
              f"SP-14:B 恢复重试应凭自己的登记保持待恢复(不重新 POST),"
              f"实际 {fourth}")
        check(sum(c["body"] == f"任务:01-task\n\n{result_a}"
                  for c in fake.comments[1]) == 1,
              "SP-14:A 正文评论应恰 1 条(重试不重复发布)")
        check(sum(c["body"] == f"任务:01-task\n\n{result_b}"
                  for c in fake.comments[1]) == 1,
              "SP-14:B 正文评论应恰 1 条(重试不重复发布)")
        posts = [c for c in fake.calls if c[0] == "POST" and "/comments" in c[1]]
        check(len(posts) == 2,
              f"SP-14:至此应恰 2 次 POST(A/B 首试各 1 次;重试均不发布),"
              f"实际 {len(posts)} 次")
        # 索引补齐:远端恢复后两请求各自重试,经读前收养只补索引,
        # 登记各自清除(互不误删)
        fifth = backend.append_result("01-task", result_a)
        sixth = backend.append_result("01-task", result_b)
        check(fifth.get("index_updated") is True
              and fifth.get("comment_id") == first.get("comment_id"),
              f"SP-14:A 补齐应收养既有评论并完成索引,实际 {fifth}")
        check(sixth.get("index_updated") is True
              and sixth.get("comment_id") == second.get("comment_id"),
              f"SP-14:B 补齐应收养既有评论并完成索引,实际 {sixth}")
        check(not list((cache / "pending-index").rglob("*.json")),
              "SP-14:两请求各自补齐后登记应全部清除(互不误删)")
        posts = [c for c in fake.calls if c[0] == "POST" and "/comments" in c[1]]
        check(len(posts) == 2,
              f"SP-14:补齐重试经读前收养不新增 POST,实际 {len(posts)} 次")


def test_append_result_pending_registration_missing_receipt_disclosed_corrupt() -> None:
    """SP-14 复审观察项(并入本票):登记保留完整身份(op/args/repo)但缺
    comment_id/ref 回执字段时,不得静默返回缺失发布身份仍称已确认发布——
    回执字段纳入形态完整性校验,缺失按登记损坏披露(corrupt 语义沿既有:
    待恢复、不重发、提示人工核对)。"""

    for fields in (("comment_id",), ("ref",), ("comment_id", "ref")):
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            root = make_github_project(base / "project")
            cache = base / "cache"
            fake = FakeTransport()
            fake.seed_issue("01-alpha", "甲任务")
            backend = backend_for(root, fake, cache)
            fake.fail("PATCH", "/issues/1", "timeout")
            backend.append_result("01-alpha", "交付证据")  # 部分成功留登记
            pending_file = next((cache / "pending-index").rglob("*.json"))
            pending = json.loads(pending_file.read_text(encoding="utf-8"))
            for field in fields:
                pending.pop(field)
            pending_file.write_text(json.dumps(pending, ensure_ascii=False),
                                    encoding="utf-8")
            fake._fail = [("GET", "/comments", "timeout")]
            second = backend.append_result("01-alpha", "交付证据")
            note = second.get("note") or ""
            check(second.get("published") is True
                  and second.get("partial") is True,
                  f"回执缺失{fields}:应保持待恢复(不当作全新发布),"
                  f"实际 {second}")
            check(second.get("comment_id") is None and second.get("ref") is None,
                  f"回执缺失{fields}:不得冒用发布身份,实际 {second}")
            check("不可读" in note or "不完整" in note,
                  f"回执缺失{fields}:应披露登记不完整,实际 note={note!r}")
            check("人工核对" in note,
                  f"回执缺失{fields}:应提示人工核对,实际 note={note!r}")
            check(len(fake.comments[1]) == 1,
                  f"回执缺失{fields}:保守方向是不重发,替身评论应仍恰 1,"
                  f"实际 {len(fake.comments[1])} 条")
            posts = [c for c in fake.calls
                     if c[0] == "POST" and "/comments" in c[1]]
            check(len(posts) == 1,
                  f"回执缺失{fields}:不应触发重发(全程恰 1 次 POST),"
                  f"实际 {len(posts)} 次")


def test_append_result_pending_legacy_flat_registration_compatible() -> None:
    """兼容:修复前的在盘登记(平铺 8 hex 短摘要文件名,c9a8021/bc230ea
    写入的布局)读入语义不破坏——身份核验、待恢复、补齐清除全部沿用;
    读入经身份核验属于当前请求后按新布局(完整身份哈希文件名)重写迁移,
    消除新旧双份并存与「清除后自旧文件复活」。"""

    with tempfile.TemporaryDirectory() as tmp:
        base = Path(tmp)
        root = make_github_project(base / "project")
        cache = base / "cache"
        fake = _OnceReadFailTransport()
        fake.seed_issue("01-alpha", "甲任务")
        backend = backend_for(root, fake, cache)
        # 部分成功留登记,再手工归位到修复前的平铺布局(内容一字不差)
        fake.fail("PATCH", "/issues/1", "timeout")
        first = backend.append_result("01-alpha", "交付证据")
        current = next((cache / "pending-index").rglob("*.json"))
        content = current.read_text(encoding="utf-8")
        legacy = (cache / "pending-index"
                  / f"append-result-01-alpha-"
                    f"{_pending_digest('01-alpha', '交付证据')}.json")
        legacy.write_text(content, encoding="utf-8")
        current.unlink()
        # 旧布局读入兼容:读前 GET 超时的重试凭旧登记保持待恢复、不重发
        fake.read_fail = True
        second = backend.append_result("01-alpha", "交付证据")
        check(second.get("published") is True and second.get("partial") is True
              and second.get("comment_id") == first.get("comment_id"),
              f"兼容:旧布局登记应照常支撑待恢复,实际 {second}")
        posts = [c for c in fake.calls if c[0] == "POST" and "/comments" in c[1]]
        check(len(posts) == 1,
              f"兼容:旧布局登记不应触发重发,实际 {len(posts)} 次")
        # 迁移:身份核验通过的旧布局登记在读入后应按新布局重写并移除旧文件
        check(any(_pending_full_digest("01-alpha", "交付证据")
                  in p.relative_to(cache / "pending-index").as_posix()
                  for p in (cache / "pending-index").rglob("*.json")),
              "兼容:旧布局登记读入后应迁移为新布局(完整身份哈希文件名)")
        check(not legacy.exists(),
              "兼容:迁移后旧布局文件应移除(不双份并存)")
        # 补齐:远端恢复后重试经读前收养补齐索引,新旧布局登记一并清除
        fake._fail = []
        third = backend.append_result("01-alpha", "交付证据")
        check(third.get("index_updated") is True
              and third.get("comment_id") == first.get("comment_id"),
              f"兼容:迁移后的登记应照常补齐收养,实际 {third}")
        check(not list((cache / "pending-index").rglob("*.json"))
              and not legacy.exists(),
              "兼容:补齐后新旧布局登记应一并清除(不自旧文件复活)")

TESTS = (
    test_append_result_pending_collision_does_not_adopt_foreign_identity,
    test_append_result_pending_registration_missing_fields_disclosed_corrupt,
    test_append_result_pending_registration_corrupt_json_keeps_recovery,
    test_append_result_pending_collision_both_partial_coexist,
    test_append_result_pending_registration_missing_receipt_disclosed_corrupt,
    test_append_result_pending_legacy_flat_registration_compatible,
)

if __name__ == "__main__":
    sys.exit(run_theme("待补索引登记:碰撞、损坏与旧布局迁移", TESTS, FAILURES))

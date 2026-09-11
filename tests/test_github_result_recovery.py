#!/usr/bin/env python3
"""结果发布的部分成功、未知与重试恢复。

任务票 11 从 tests/test_github_backend.py 按真实行为主题拆出;检查含义与原
案例保持一致,仅重组位置。原总入口仍聚合本主题。本主题可直接运行:

    python3 -B tests/test_github_result_recovery.py
"""

import sys
import tempfile
from pathlib import Path

from github_backend_transport import (
    FakeTransport, backend_for,
)
from github_backend_fixtures import (
    make_checker, make_github_project, run_theme,
)

import mgs_github  # noqa: E402

FAILURES, check = make_checker()


def test_append_result_readback_failure_keeps_uncertain() -> None:
    """S2:评论超时后回读本身失败 ≠ 确认不存在——保留未知状态、停止重发,
    结果如实报告已尝试步骤与不确定结论(不虚报失败也不虚报成功)。"""

    with tempfile.TemporaryDirectory() as tmp:
        root = make_github_project(Path(tmp))
        fake = FakeTransport()
        fake.seed_issue("01-alpha", "甲任务")
        backend = backend_for(root, fake)
        fake.drop("POST", "/comments")           # 首条评论已落地但响应超时
        fake.fail("GET", "/comments", "timeout")  # 回读本身失败
        try:
            outcome = backend.append_result("01-alpha", "交付证据")
        except mgs_github.GithubRecordsError as exc:  # 修复前:重发两次后报错
            outcome = {"raised": str(exc)}
        posts = [c for c in fake.calls if c[0] == "POST" and "/comments" in c[1]]
        check(len(posts) == 1,
              f"回读失败时不得发出第二条创建请求,实际 {len(posts)} 次 POST")
        check(len(fake.comments[1]) == 1,
              f"替身应只有一条评论,实际 {len(fake.comments[1])} 条")
        check(outcome.get("uncertain") is True
              and outcome.get("published") is not True,
              f"结果应保留未知状态且不虚报成功,实际 {outcome}")
        readbacks = [a for a in outcome.get("attempts", [])
                     if a.get("step") == "readback"]
        check(readbacks and readbacks[-1].get("outcome") != "absent",
              f"回读失败不得记作 absent(确认不存在),实际 {outcome.get('attempts')}")


def test_append_result_partial_success_and_retry_completion() -> None:
    """SP-2:评论已真实发布而结果索引更新超时——部分成功如实保留(携带
    已发布评论身份与索引未完成状态,不整体报错);恢复后重试同一请求只
    收养既有评论并补齐索引,替身评论数恰 1(不重复发布)。"""

    with tempfile.TemporaryDirectory() as tmp:
        root = make_github_project(Path(tmp))
        fake = FakeTransport()
        fake.seed_issue("01-alpha", "甲任务")
        backend = backend_for(root, fake)
        fake.fail("PATCH", "/issues/1", "timeout")  # 评论 POST 成功后索引 PATCH 超时
        try:
            first = backend.append_result("01-alpha", "交付证据")  # 修复前:直接抛出
        except (mgs_github.TransportError, mgs_github.GithubRecordsError) as exc:
            first = {"raised": str(exc)}
        check(first.get("published") is True and first.get("partial") is True,
              f"评论已发布的部分成功应如实保留(不整体报错),实际 {first}")
        check(first.get("comment_id") is not None,
              f"结果应携带已发布评论身份,实际 {first}")
        check(first.get("index_updated") is False,
              f"未完成部分(结果索引)应如实表达,实际 {first}")
        check(len(fake.comments[1]) == 1,
              f"首次调用替身应已有 1 条评论,实际 {len(fake.comments[1])} 条")
        check(f"#issuecomment-{first.get('comment_id')}"
              not in (fake.issues[0].get("body") or ""),
              "索引 PATCH 超时后正文不应已含该评论引用")
        # 恢复后重试同一请求:只收养既有评论并补齐索引
        fake._fail = []
        second = backend.append_result("01-alpha", "交付证据")
        check(second.get("published") is True
              and second.get("index_updated") is True,
              f"恢复后重试应完成索引并如实回报,实际 {second}")
        check(second.get("comment_id") == first.get("comment_id"),
              f"重试应收养既有评论(同一评论身份),实际 {second.get('comment_id')}"
              f" vs {first.get('comment_id')}")
        posts = [c for c in fake.calls if c[0] == "POST" and "/comments" in c[1]]
        check(len(posts) == 1,
              f"重试不得再发评论 POST(全程恰 1 次),实际 {len(posts)} 次")
        check(len(fake.comments[1]) == 1,
              f"替身评论数应恰 1(不重复发布),实际 {len(fake.comments[1])} 条")
        check(f"#issuecomment-{first.get('comment_id')}"
              in (fake.issues[0].get("body") or ""),
              "重试后结果索引应补齐该评论引用")
        # 已完成后的再次重试仍幂等:评论数与索引均不再变化
        third = backend.append_result("01-alpha", "交付证据")
        check(third.get("published") is True
              and third.get("index_updated") is True
              and third.get("comment_id") == first.get("comment_id"),
              f"完成后的重复请求应幂等(收养既有评论),实际 {third}")
        check(len(fake.comments[1]) == 1, "幂等重试后评论数仍应恰 1")


def test_append_result_draft_replay_partial_keeps_draft() -> None:
    """SP-2 草稿重放侧:重放中评论已发布而索引更新失败属部分成功——草稿
    保留(不算完成),下次重放收养既有评论只补索引;全程评论数恰 1。"""

    with tempfile.TemporaryDirectory() as tmp:
        root = make_github_project(Path(tmp))
        cache = Path(tmp) / "cache"
        fake = FakeTransport()
        fake.seed_issue("01-alpha", "甲任务")
        backend = backend_for(root, fake, cache)
        backend.fetch_tasks()  # 在线建立缓存(离线草稿路径需要)
        fake.offline()
        draft = backend.append_result("01-alpha", "离线证据")
        check(draft.get("published") is False and draft.get("draft"),
              f"离线追加结果应保存草稿,实际 {draft}")
        # 恢复但索引 PATCH 超时:重放得到部分成功,草稿保留待下次补齐
        fake._offline = False
        fake.fail("PATCH", "/issues/1", "timeout")
        first = backend.publish_drafts()
        check(first["published_count"] == 0,
              f"部分成功不算完成(草稿保留),实际 {first}")
        check(len(fake.comments[1]) == 1,
              f"重放应已发布 1 条评论,实际 {len(fake.comments[1])} 条")
        check(len(list((cache / "drafts").glob("*.json"))) == 1,
              "部分成功的草稿应保留在待发布目录")
        # 故障清除后再次重放:收养既有评论,只补索引
        fake._fail = []
        second = backend.publish_drafts()
        check(second["published_count"] == 1,
              f"恢复后重放应补齐索引并完成,实际 {second}")
        check(len(fake.comments[1]) == 1,
              f"补齐重放不得重复发布评论(仍恰 1 条),"
              f"实际 {len(fake.comments[1])} 条")
        check(not list((cache / "drafts").glob("*.json")),
              "完成后的草稿应移出待发布目录")
        check("#issuecomment-" in (fake.issues[0].get("body") or "")
              and "离线证据" in (fake.issues[0].get("body") or ""),
              "结果索引应补齐该评论引用")


def test_append_result_partial_retry_read_first_timeout_no_duplicate() -> None:
    """SP-7:首轮部分成功(partial+comment_id,评论已确认发布)后,重试的
    读前收养查询超时不得当作全新发布——按本地「待补索引登记」保留已发布
    操作身份、保持待恢复状态(partial 语义);彻底恢复后重试收养既有评论
    只补索引,替身评论恰 1。partial(已发布未完索引)与 uncertain(结果
    未知)语义互不混同。"""

    with tempfile.TemporaryDirectory() as tmp:
        base = Path(tmp)
        root = make_github_project(base / "project")
        cache = base / "cache"
        fake = FakeTransport()
        fake.seed_issue("01-alpha", "甲任务")
        backend = backend_for(root, fake, cache)
        fake.fail("PATCH", "/issues/1", "timeout")  # 评论 POST 成功+索引 PATCH 超时
        try:
            first = backend.append_result("01-alpha", "交付证据")  # 修复前:直接抛出
        except (mgs_github.TransportError, mgs_github.GithubRecordsError) as exc:
            first = {"raised": str(exc)}
        check(first.get("published") is True and first.get("partial") is True,
              f"首轮应如实回报部分成功,实际 {first}")
        check(first.get("comment_id") is not None
              and first.get("index_updated") is False,
              f"首轮结果应携带已发布评论身份与索引未完成状态,实际 {first}")
        check(len(fake.comments[1]) == 1,
              f"首轮替身应已有 1 条评论,实际 {len(fake.comments[1])} 条")
        check(len(list((cache / "pending-index").rglob("*.json"))) == 1,
              "部分成功应在本地登记已发布评论身份(待补索引登记)")
        # 恢复索引 PATCH,但重试的读前收养查询超时(SP-7 反例:
        # 当前实现把它当作全新发布再 POST 一条)
        fake._fail = []
        fake.fail("GET", "/comments", "timeout")
        try:
            second = backend.append_result("01-alpha", "交付证据")
        except (mgs_github.TransportError, mgs_github.GithubRecordsError) as exc:
            second = {"raised": str(exc)}
        check(second.get("published") is True and second.get("partial") is True,
              f"读前查询失败时应保持待恢复状态(不当作全新发布),实际 {second}")
        check(second.get("comment_id") == first.get("comment_id"),
              f"待恢复状态应保留前次已确认发布的评论身份,实际 "
              f"{second.get('comment_id')} vs {first.get('comment_id')}")
        check(second.get("index_updated") is False,
              f"待恢复状态应如实表达索引仍未完成,实际 {second}")
        check(second.get("uncertain") is not True,
              f"已确认发布(partial)与结果未知(uncertain)是两种事实,"
              f"不得混同,实际 {second}")
        check(len(fake.comments[1]) == 1,
              f"读前查询失败不得重复发布(替身评论仍恰 1),"
              f"实际 {len(fake.comments[1])} 条")
        posts = [c for c in fake.calls if c[0] == "POST" and "/comments" in c[1]]
        check(len(posts) == 1,
              f"全程应只发出 1 次评论 POST,实际 {len(posts)} 次")
        check(len(list((cache / "pending-index").rglob("*.json"))) == 1,
              "待恢复期间登记应保留(索引未补齐)")
        # 彻底恢复后重试:读前收养既有评论,只补索引
        fake._fail = []
        third = backend.append_result("01-alpha", "交付证据")
        check(third.get("published") is True
              and third.get("index_updated") is True
              and third.get("comment_id") == first.get("comment_id"),
              f"彻底恢复后重试应收养既有评论并补齐索引,实际 {third}")
        check(len(fake.comments[1]) == 1,
              f"补齐索引不得重复发布评论,实际 {len(fake.comments[1])} 条")
        check(f"#issuecomment-{first.get('comment_id')}"
              in (fake.issues[0].get("body") or ""),
              "彻底恢复后结果索引应补齐该评论引用")
        check(not list((cache / "pending-index").rglob("*.json")),
              "索引补齐后应清除待补索引登记")


def test_append_result_read_first_failure_without_pending_keeps_first_try() -> None:
    """SP-7 邻近语义:无待补索引登记(本次调用前未确认发布过)时,读前
    查询失败仍按首试语义继续尝试发布——S2「发布超时后回读失败不重发、
    保持 uncertain」的既有取舍不因本票回退(有缓存目录场景同样成立)。"""

    with tempfile.TemporaryDirectory() as tmp:
        base = Path(tmp)
        root = make_github_project(base / "project")
        cache = base / "cache"
        fake = FakeTransport()
        fake.seed_issue("01-alpha", "甲任务")
        backend = backend_for(root, fake, cache)
        fake.fail("GET", "/comments", "timeout")  # 读前收养查询超时(无登记)
        fake.drop("POST", "/comments")            # 评论已落地但响应超时
        outcome = backend.append_result("01-alpha", "交付证据")
        posts = [c for c in fake.calls if c[0] == "POST" and "/comments" in c[1]]
        check(len(posts) == 1,
              f"首试语义:读前查询失败(无登记)仍应尝试发布恰 1 次,"
              f"实际 {len(posts)} 次")
        check(outcome.get("uncertain") is True
              and outcome.get("published") is not True,
              f"发布超时且回读失败应保持 uncertain(不虚报成功、不重发),"
              f"实际 {outcome}")
        check(len(fake.comments[1]) == 1,
              f"替身应只有 1 条评论,实际 {len(fake.comments[1])} 条")
        check(not list((cache / "pending-index").rglob("*.json")),
              "uncertain(结果未知)不应写待补索引登记——登记只表达已确认发布")


def test_append_result_partial_without_cache_dir_carries_degraded_warning() -> None:
    """SP-10:未配置缓存目录时,部分成功(partial)的结果 note 必须实际
    携带退化警告——本模式无跨调用身份保留、读前收养查询失败的重试可能
    重复发布、建议配置缓存目录——且不再输出「不会重复发布」承诺;
    有缓存目录(登记落盘)时承诺保持,登记/待恢复/补齐清登记链路语义
    不回退(邻近对照)。"""

    with tempfile.TemporaryDirectory() as tmp:
        base = Path(tmp)
        root = make_github_project(base / "project")
        # 无缓存目录:partial note 应携带退化警告,不带不重复发布承诺
        fake = FakeTransport()
        fake.seed_issue("01-alpha", "甲任务")
        backend = backend_for(root, fake, None)
        fake.fail("PATCH", "/issues/1", "timeout")
        first = backend.append_result("01-alpha", "交付证据")
        check(first.get("published") is True and first.get("partial") is True
              and first.get("index_updated") is False,
              f"前置:无缓存目录首轮仍应如实部分成功,实际 {first}")
        note = first.get("note") or ""
        check("警告" in note,
              f"SP-10:无缓存目录的 partial note 应实际携带警告,实际 {note!r}")
        check("可能重复发布" in note or "可能重复" in note,
              f"SP-10:警告应说明本模式重试可能重复发布,实际 {note!r}")
        check("缓存目录" in note or "cache_dir" in note or "--cache-dir" in note,
              f"SP-10:警告应建议配置缓存目录,实际 {note!r}")
        check("不会重复发布" not in note,
              f"SP-10:无缓存模式不得表述为拥有不重复发布保证,实际 {note!r}")
        # 邻近对照:有缓存目录(登记落盘)时承诺保持——有缓存语义不变
        cache = base / "cache"
        fake_cached = FakeTransport()
        fake_cached.seed_issue("01-alpha", "甲任务")
        backend_cached = backend_for(root, fake_cached, cache)
        fake_cached.fail("PATCH", "/issues/1", "timeout")
        with_cache = backend_cached.append_result("01-alpha", "交付证据")
        note_cached = with_cache.get("note") or ""
        check("不会重复发布" in note_cached,
              f"SP-10 对照:登记落盘时「不会重复发布」承诺保持,实际 {note_cached!r}")
        check("警告" not in note_cached,
              f"SP-10 对照:登记落盘时不应出现登记不可用警告,实际 {note_cached!r}")
        check(len(list((cache / "pending-index").rglob("*.json"))) == 1,
              "SP-10 对照:有缓存目录时登记照常落盘")


def test_append_result_online_and_execute_op_share_recovery_fact() -> None:
    """票 18 接入证明:直接调用 append_result 与经受控分发 execute_op
    (草稿重放同一入口)走同一发布恢复职责——首轮部分成功后重试,两条
    入口都收养同一已发布评论并补齐索引,不重复发布、共享同一恢复事实;
    新 module 由现有调用真实使用,而非另建未接线实现。"""

    with tempfile.TemporaryDirectory() as tmp:
        base = Path(tmp)
        root = make_github_project(base / "project")
        cache = base / "cache"
        fake = FakeTransport()
        fake.seed_issue("01-alpha", "甲任务")
        backend = backend_for(root, fake, cache)
        fake.fail("PATCH", "/issues/1", "timeout")
        first = backend.append_result("01-alpha", "交付证据")  # 直接接口:部分成功
        check(first.get("partial") is True and first.get("comment_id") is not None,
              f"前置:首轮应如实部分成功,实际 {first}")
        fake._fail = []
        # 草稿重放与在线受控通道共用 execute_op 的动作分发
        second = backend.execute_op(
            "append_result",
            {"identity": "01-alpha", "result_markdown": "交付证据"})
        check(second.get("published") is True
              and second.get("index_updated") is True
              and second.get("comment_id") == first.get("comment_id"),
              f"两入口应共享恢复事实(收养同一评论并补齐索引),实际 {second}")
        posts = [c for c in fake.calls if c[0] == "POST" and "/comments" in c[1]]
        check(len(posts) == 1,
              f"两入口共享恢复职责,全程应恰 1 次评论 POST,实际 {len(posts)} 次")
        check(not list((cache / "pending-index").rglob("*.json")),
              "补齐后待补索引登记应清除")

def test_append_result_three_paths_share_recovery_fact() -> None:
    """票 20 三路一致性:同一结果追加请求依次经过「在线失败(离线草稿)」、
    「草稿重放(部分成功)」与「再次调用(补齐)」,三条路径共享同一恢复
    事实——远端评论发布次数、回执(comment_id/ref)与最终索引状态一致;
    未发布草稿、已确认发布的部分成功与完成是不同事实,互不替代。"""

    with tempfile.TemporaryDirectory() as tmp:
        base = Path(tmp)
        root = make_github_project(base / "project")
        cache = base / "cache"
        fake = FakeTransport()
        fake.seed_issue("01-alpha", "甲任务")
        backend = backend_for(root, fake, cache)
        backend.fetch_tasks()  # 在线建立缓存(离线草稿路径需要)

        # 路径 1:在线失败(离线) → 保存未发布草稿,零远端发布,不报告已发布
        fake.offline()
        draft = backend.append_result("01-alpha", "三路证据")
        check(draft.get("published") is False
              and draft.get("status") == "未发布草稿" and draft.get("draft"),
              f"在线失败应保存未发布草稿,实际 {draft}")
        check(draft.get("uncertain") is not True
              and draft.get("partial") is not True,
              f"未发布草稿与结果未知/部分成功是不同事实,实际 {draft}")
        comment_posts = [c for c in fake.calls if c[0] == "POST"
                         and "/comments" in c[1]]
        check(len(comment_posts) == 0,
              f"离线未发布不得发出评论 POST,实际 {len(comment_posts)} 次")
        check(len(list((cache / "drafts").glob("*.json"))) == 1,
              "在线失败应落盘一份未发布草稿")

        # 路径 2:草稿重放(评论已发布、索引 PATCH 超时) → 部分成功保留草稿
        fake._offline = False
        fake.fail("PATCH", "/issues/1", "timeout")
        first = backend.publish_drafts()
        check(first["published_count"] == 0,
              f"部分成功不算完成,草稿应保留,实际 {first}")
        outcome = first["results"][0].get("outcome")
        check(isinstance(outcome, dict) and outcome.get("published") is True
              and outcome.get("partial") is True
              and outcome.get("comment_id") is not None
              and outcome.get("index_updated") is False,
              f"重放应如实回报部分成功并携带回执与未完成索引,实际 {outcome}")
        check(outcome.get("uncertain") is not True,
              "部分成功(已确认发布)与结果未知(uncertain)不得互相替代")
        receipt = outcome.get("comment_id")
        ref = outcome.get("ref")
        check(len(fake.comments[1]) == 1,
              f"重放应恰发布 1 条评论,实际 {len(fake.comments[1])}")

        # 路径 3:再次调用(读前收养既有评论,只补索引) → 完成,最终状态一致
        fake._fail = []
        final = backend.append_result("01-alpha", "三路证据")
        check(final.get("published") is True
              and final.get("index_updated") is True
              and final.get("comment_id") == receipt,
              f"再次调用应收养同一回执并补齐索引,实际 {final}")
        posts = [c for c in fake.calls if c[0] == "POST" and "/comments" in c[1]]
        check(len(posts) == 1,
              f"三路合计远端评论发布次数应恰 1,实际 {len(posts)} 次")
        check(len(fake.comments[1]) == 1,
              f"最终远端评论数应恰 1,实际 {len(fake.comments[1])}")
        check(ref and f"#issuecomment-{receipt}" in (fake.issues[0].get("body") or ""),
              "最终结果索引应含同一回执引用")
        # 草稿重放路径与直接调用路径收敛到同一最终状态:残留草稿再次重放
        # 收养同一回执、恰完成索引、不再发布评论,并把草稿移出待发布目录
        fake._fail = []
        replay = backend.publish_drafts()
        check(replay["published_count"] == 1,
              f"残留草稿重放应收敛为完成(不新增发布),实际 {replay}")
        check(len([c for c in fake.calls if c[0] == "POST"
                   and "/comments" in c[1]]) == 1,
              "草稿再次重放不得新增评论 POST(三路合计仍恰 1 次)")
        check(len(fake.comments[1]) == 1,
              f"草稿再次重放后远端评论数仍应恰 1,实际 {len(fake.comments[1])}")
        check(not list((cache / "drafts").glob("*.json")),
              "完成后草稿应移出待发布目录")


TESTS = (
    test_append_result_readback_failure_keeps_uncertain,
    test_append_result_partial_success_and_retry_completion,
    test_append_result_draft_replay_partial_keeps_draft,
    test_append_result_partial_retry_read_first_timeout_no_duplicate,
    test_append_result_read_first_failure_without_pending_keeps_first_try,
    test_append_result_partial_without_cache_dir_carries_degraded_warning,
    test_append_result_online_and_execute_op_share_recovery_fact,
    test_append_result_three_paths_share_recovery_fact,
)

if __name__ == "__main__":
    sys.exit(run_theme("结果发布的部分成功、未知与重试恢复", TESTS, FAILURES))

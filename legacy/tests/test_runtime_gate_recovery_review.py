#!/usr/bin/env python3
"""恢复与部分成功审查修复批(通道侧)的反例固化。

任务票 12 从 tests/test_runtime_gate.py 的原始总入口按真实行为主题拆出;
每条 check 的条件、消息与断言对象与原案例逐字一致,仅重组位置。覆盖:
票 01-fix 的说明三路一致与不确定结果如实回报、review2-01 的 CONFIG 在途
撤销(SP-1)、review2-02 的索引超时部分成功(SP-2)、review3-01 的读前收养
超时(SP-7)、review4-01 的无缓存退化警告(SP-10)。原总入口仍聚合本主题。
本主题可直接运行:

    python3 -B tests/test_runtime_gate_recovery_review.py
"""

import hashlib
import json
import shutil
import sys
import tempfile
import threading
from pathlib import Path

from runtime_gate_support import (
    REPO_ROOT, GateService, audit_lines, make_checker, mcp_gate, run_theme,
)

sys.path.insert(0, str(REPO_ROOT / "tests"))
import test_github_backend as gh_fixtures  # noqa: E402  (远端替身与项目夹具)
sys.path.insert(0, str(REPO_ROOT / "plugin" / "records"))

FAILURES, check = make_checker()

RESOURCES = ["github://github.com/mygamestudio/issue-accept/issues/**"]
CONFIG_RESOURCES = ["github://github.com/mygamestudio/issue-accept/issues/**",
                    "docs/mygamestudio/CONFIG.md"]


def _gate_append(base: Path, ident: str = "T-sp2"):
    """搭建一个可注入替身的 svc 与 mcp_gate append-result 调用闭包。"""

    project = gh_fixtures.make_github_project(base / "project")
    svc = GateService(base / "runtime")
    svc.init_policy(project, {"producer": RESOURCES}, {"production": None})
    inst = svc.create_instance("producer", ident, "production", RESOURCES)
    svc._write_json("remote.json", {"github": {
        "api_base": "http://unused.invalid", "token_env": "MGS_TEST_UNUSED",
        "cache_dir": str(base / "cache")}})
    return svc, inst


def _records_review_fix(root: Path) -> None:
    """票 01-fix 通道侧:更新说明三路一致与回读失败如实回报不确定。"""

    base = root / "t01"
    project = gh_fixtures.make_github_project(base / "project")
    svc = GateService(base / "runtime")
    svc.init_policy(project, {"producer": RESOURCES}, {"production": None})
    inst = svc.create_instance("producer", "T-01x", "production", RESOURCES)
    svc._write_json("remote.json", {"github": {
        "api_base": "http://unused.invalid", "token_env": "MGS_TEST_UNUSED",
        "cache_dir": str(base / "cache")}})
    fake = gh_fixtures.FakeTransport()
    fake.seed_issue("01-task", "Existing")

    # 核验建议 2(在线执行路径):说明随通道动作参数传递
    res = svc.remote_record(inst.token, "update",
                            {"identity": "01-task",
                             "fields": {"进度": "执行中"},
                             "change_note": "通道轮安排"},
                            transport=fake)
    check(res["decision"] == "allow", f"通道内安排更新应放行,实际 {res}")
    check("通道轮安排" in fake.issues[0]["body"],
          "通道在线路径的更新说明应写入远端正文状态变化(不回退默认文案)")

    # S2(通道级):回读失败 → 结果不确定,如实回报
    fake.drop("POST", "/comments")
    fake.fail("GET", "/comments", "timeout")
    comments_before = len(fake.comments[1])
    res = svc.remote_record(inst.token, "append-result",
                            {"identity": "01-task",
                             "result_markdown": "回读失败"},
                            transport=fake)
    posts = [c for c in fake.calls if c[0] == "POST" and "/comments" in c[1]]
    check(len(posts) == comments_before + 1,
          f"回读失败后不得重发评论,实际共 {len(posts)} 次 POST(此前 "
          f"{comments_before} 次)")
    check(res.get("decision") == "uncertain"
          and res.get("result", {}).get("uncertain") is True,
          f"通道应如实回报结果不确定(不虚报成功也不包装成拒绝),实际 {res}")
    check("草稿" not in json.dumps(res.get("note") or {}, ensure_ascii=False),
          "不确定结果不得被包装成「已保存草稿」的拒绝")


def _sp1_fixture_and_baseline(root: Path) -> dict:
    """SP-1 夹具与基线:撤销前合法远端写入放行。"""

    base = root / "review2-sp1"
    project = gh_fixtures.make_github_project(base / "project")
    runtime = base / "runtime"
    svc = GateService(runtime)
    peer = GateService(runtime)  # 另一会话入口,与探针的双 GateService 时序一致
    svc.init_policy(project, {"producer": CONFIG_RESOURCES}, {"production": None})
    inst = svc.create_instance("producer", "remote", "production", CONFIG_RESOURCES)
    admin = svc.create_instance("producer", "config-update", "production",
                                CONFIG_RESOURCES)
    svc._write_json("remote.json", {"github": {
        "api_base": "http://unused.invalid", "token_env": "MGS_TEST_UNUSED",
        "cache_dir": str(base / "cache")}})
    transport = gh_fixtures.FakeTransport()
    transport.seed_issue("01-task", "Existing")

    # 基线:撤销前合法远端写入放行(授权在场,语义与性能不回退的前提)
    ok = peer.remote_record(inst.token, "append-result",
                            {"identity": "01-task", "result_markdown": "撤销前"},
                            transport=transport)
    check(ok["decision"] == "allow",
          f"SP-1:撤销前合法远端写入应放行,实际 {ok}")
    check(len(transport.comments[1]) == 1,
          f"SP-1:撤销前应恰新增 1 条评论,实际 {len(transport.comments[1])}")
    return {"base": base, "project": project, "runtime": runtime, "svc": svc,
            "peer": peer, "inst": inst, "admin": admin, "transport": transport}


def _review2_sp1(root: Path) -> None:
    """SP-1:CONFIG 授权撤销后,在途远端写入必须以 remote_scope 拒绝。"""

    S = _sp1_fixture_and_baseline(root)
    base, project, runtime = S["base"], S["project"], S["runtime"]
    svc, peer, inst, admin = S["svc"], S["peer"], S["inst"], S["admin"]
    transport = S["transport"]

    # 在途时序:写线程停在取锁前(锁外 CONFIG 已读完),撤销先完成再恢复。
    # 与 R1-remote 的差别:暂停点在锁本身,覆盖「锁外 CONFIG 读取→取锁」窗口。
    real_lock = svc._locked
    waiting = threading.Event()
    resume = threading.Event()
    outcome: dict = {}

    def paused_lock():
        if threading.current_thread().name == "remote-writer":
            waiting.set()
            assert resume.wait(5)
        return real_lock()

    def inflight() -> None:
        try:
            outcome["res"] = svc.remote_record(
                inst.token, "append-result",
                {"identity": "01-task", "result_markdown": "撤销后在途"},
                transport=transport)
        except Exception as exc:  # noqa: BLE001 - 异常本身即断言素材
            outcome["error"] = repr(exc)

    svc._locked = paused_lock
    thread = threading.Thread(target=inflight, name="remote-writer")
    thread.start()
    try:
        check(waiting.wait(5), "SP-1:在途请求应先暂停在取锁前")
        config = project / "docs/mygamestudio/CONFIG.md"
        old_text = config.read_text(encoding="utf-8")
        new_text = old_text.replace(gh_fixtures.AUTH, "无(已撤销)")
        check(new_text != old_text, "SP-1:探针应实际改写 CONFIG 授权行")
        rev = peer.write(admin.token, "docs/mygamestudio/CONFIG.md", new_text,
                         expected_sha256=hashlib.sha256(
                             old_text.encode()).hexdigest())
        check(rev["decision"] == "allow",
              f"SP-1:经正常入口撤销 CONFIG 授权应 allow,实际 {rev}")
        resume.set()
        thread.join(5)
        check(not thread.is_alive(), "SP-1:在途线程应在撤销后返回")
    finally:
        svc._locked = real_lock
        resume.set()
    res = outcome.get("res")
    check(outcome.get("error") is None,
          f"SP-1:在途请求不应异常,实际 {outcome.get('error')}")
    check(res is not None and res["decision"] == "deny"
          and res["rule_stage"] == "remote_scope",
          f"SP-1:CONFIG 授权撤销后,在途远端写入必须以 remote_scope 拒绝,"
          f"实际 {res}")
    check(len(transport.comments[1]) == 1,
          f"SP-1:被拒的在途请求不得产生远端写入(评论数应保持 1,"
          f"实际 {len(transport.comments[1])})")
    posts = [c for c in transport.calls
             if c[0] == "POST" and "/comments" in c[1]]
    check(len(posts) == 1,
          f"SP-1:全程应只发出撤销前那 1 次评论 POST,实际 {len(posts)} 次")

    # 撤销后新请求继续拒绝(既有语义不回退);拒绝如实进审计
    fresh = peer.remote_record(inst.token, "append-result",
                               {"identity": "01-task",
                                "result_markdown": "撤销后新请求"},
                               transport=transport)
    check(fresh["decision"] == "deny" and fresh["rule_stage"] == "remote_scope",
          f"SP-1:撤销后新远端请求应继续拒绝,实际 {fresh}")
    entries = audit_lines(runtime)
    check(any(e.get("op") == "remote:append-result"
              and e.get("decision") == "deny"
              and e.get("rule_stage") == "remote_scope" for e in entries),
          "SP-1:在途拒绝应留下 remote_scope 审计记录")


def _review2_sp2(root: Path) -> None:
    """SP-2:评论已发布而索引更新超时的部分成功不得整体转 deny。"""

    base = root / "review2-sp2"
    svc, inst = _gate_append(base, "T-sp2")
    fake = gh_fixtures.FakeTransport()
    fake.seed_issue("01-task", "Existing")
    fake.fail("PATCH", "/issues/1", "timeout")  # 评论 POST 成功后索引 PATCH 超时

    class Facade:
        def remote_record(self, token, action, payload):
            return svc.remote_record(token, action, payload, transport=fake)

    def call() -> dict:
        response = mcp_gate.handle_tools_call(
            Facade(), "mgs_remote",
            {"token": inst.token, "action": "append-result",
             "payload": {"identity": "01-task", "result_markdown": "same result"}})
        return json.loads(response["content"][0]["text"])

    first = call()
    check(first.get("decision") != "deny",
          f"SP-2:评论已发布的部分成功不得整体转 deny,实际 {first}")
    first_result = first.get("result") or {}
    check(first_result.get("published") is True
          and first_result.get("comment_id") is not None,
          f"SP-2:结果应携带已发布评论身份,实际 {first_result}")
    check(first_result.get("index_updated") is False,
          f"SP-2:未完成部分(结果索引)应如实表达,实际 {first_result}")
    check(len(fake.comments[1]) == 1,
          f"SP-2:首次调用替身应已有 1 条评论,实际 {len(fake.comments[1])} 条")

    # 故障清除后同请求重试:仅补索引,不重复发布评论
    fake._fail = []
    second = call()
    check(second.get("decision") == "allow",
          f"SP-2:恢复后重试应 allow,实际 {second}")
    check(len(fake.comments[1]) == 1,
          f"SP-2:恢复后重试仅补索引,替身评论数应恰 1(不重复发布),"
          f"实际 {len(fake.comments[1])} 条")
    posts = [c for c in fake.calls if c[0] == "POST" and "/comments" in c[1]]
    check(len(posts) == 1,
          f"SP-2:全程应只发出 1 次评论 POST,实际 {len(posts)} 次")
    check(f"#issuecomment-{first_result.get('comment_id')}"
          in (fake.issues[0].get("body") or ""),
          "SP-2:重试后结果索引应补齐该评论引用")
    entries = audit_lines(base / "runtime")
    check(any(e.get("op") == "remote:append-result"
              and e.get("decision") == "intent" for e in entries),
          "SP-2:远端写入意图仍先于执行持久记录")


def _review3_sp7(root: Path) -> None:
    """SP-7:已确认部分成功后读前收养查询超时不得重复发布。"""

    base = root / "review3-sp7"
    svc, inst = _gate_append(base, "T-sp7")
    fake = gh_fixtures.FakeTransport()
    fake.seed_issue("01-task", "Existing")
    fake.fail("PATCH", "/issues/1", "timeout")  # 评论 POST 成功后索引 PATCH 超时

    class Facade:
        def remote_record(self, token, action, payload):
            return svc.remote_record(token, action, payload, transport=fake)

    def call() -> dict:
        response = mcp_gate.handle_tools_call(
            Facade(), "mgs_remote",
            {"token": inst.token, "action": "append-result",
             "payload": {"identity": "01-task", "result_markdown": "same result"}})
        return json.loads(response["content"][0]["text"])

    first = call()
    check(first.get("decision") == "allow",
          f"SP-7 前置:首轮部分成功应 allow 如实转发,实际 {first}")
    first_result = first.get("result") or {}
    check(first_result.get("partial") is True
          and first_result.get("comment_id") is not None
          and first_result.get("index_updated") is False,
          f"SP-7 前置:首轮应携带已发布评论身份与未完成索引,实际 {first_result}")
    check(len(fake.comments[1]) == 1,
          f"SP-7 前置:首轮替身应已有 1 条评论,实际 {len(fake.comments[1])} 条")

    # 恢复索引 PATCH,但让重试的读前收养查询超时(反例靶点)
    fake._fail = []
    fake.fail("GET", "/comments", "timeout")
    second = call()
    second_result = second.get("result") or {}
    check(second.get("decision") != "deny",
          f"SP-7:待恢复状态不得包装成 deny,实际 {second}")
    check(second_result.get("comment_id") == first_result.get("comment_id"),
          f"SP-7:读前查询失败时应保留已发布评论身份(不当作全新发布),"
          f"实际 {second_result.get('comment_id')} vs "
          f"{first_result.get('comment_id')}")
    check(second_result.get("index_updated") is False
          and second_result.get("uncertain") is not True,
          f"SP-7:应保持 partial 待恢复语义(与 uncertain 区分),"
          f"实际 {second_result}")
    check(len(fake.comments[1]) == 1,
          f"SP-7:读前查询失败不得重复发布(替身评论仍恰 1),"
          f"实际 {len(fake.comments[1])} 条")
    posts = [c for c in fake.calls if c[0] == "POST" and "/comments" in c[1]]
    check(len(posts) == 1,
          f"SP-7:全程应只发出 1 次评论 POST,实际 {len(posts)} 次")

    # 彻底恢复后重试:收养既有评论,只补索引
    fake._fail = []
    third = call()
    third_result = third.get("result") or {}
    check(third.get("decision") == "allow",
          f"SP-7:彻底恢复后重试应 allow,实际 {third}")
    check(third_result.get("index_updated") is True
          and third_result.get("comment_id") == first_result.get("comment_id"),
          f"SP-7:彻底恢复后应收养既有评论并补齐索引,实际 {third_result}")
    check(len(fake.comments[1]) == 1,
          f"SP-7:补齐索引不得重复发布评论,实际 {len(fake.comments[1])} 条")
    check(f"#issuecomment-{first_result.get('comment_id')}"
          in (fake.issues[0].get("body") or ""),
          "SP-7:彻底恢复后结果索引应补齐该评论引用")


def _review4_sp10(root: Path) -> None:
    """SP-10:无 cache_dir 时部分成功的运行结果 note 携带退化警告。"""

    base = root / "review4-sp10"
    project = gh_fixtures.make_github_project(base / "project")
    svc = GateService(base / "runtime")
    svc.init_policy(project, {"producer": RESOURCES}, {"production": None})
    inst = svc.create_instance("producer", "T-sp10", "production", RESOURCES)
    # 反例配置:远端通道不配置 cache_dir(登记不可用的退化模式)
    svc._write_json("remote.json", {"github": {
        "api_base": "http://unused.invalid", "token_env": "MGS_TEST_UNUSED"}})
    fake = gh_fixtures.FakeTransport()
    fake.seed_issue("01-task", "Existing")
    fake.fail("PATCH", "/issues/1", "timeout")  # 评论 POST 成功后索引 PATCH 超时

    class Facade:
        def remote_record(self, token, action, payload):
            return svc.remote_record(token, action, payload, transport=fake)

    def call() -> dict:
        response = mcp_gate.handle_tools_call(
            Facade(), "mgs_remote",
            {"token": inst.token, "action": "append-result",
             "payload": {"identity": "01-task", "result_markdown": "same result"}})
        return json.loads(response["content"][0]["text"])

    first = call()
    check(first.get("decision") == "allow",
          f"SP-10 前置:首轮部分成功应 allow 如实转发,实际 {first}")
    result = first.get("result") or {}
    check(result.get("partial") is True
          and result.get("comment_id") is not None
          and result.get("index_updated") is False,
          f"SP-10 前置:首轮应携带已发布评论身份与未完成索引,实际 {result}")
    note = result.get("note") or ""
    check("警告" in note,
          f"SP-10:无 cache_dir 的 partial 运行结果 note 应实际携带警告,"
          f"实际 {note!r}")
    check("可能重复发布" in note or "可能重复" in note,
          f"SP-10:警告应说明本模式重试可能重复发布,实际 {note!r}")
    check("缓存目录" in note or "cache_dir" in note or "--cache-dir" in note,
          f"SP-10:警告应建议配置缓存目录,实际 {note!r}")
    check("不会重复发布" not in note,
          f"SP-10:无缓存模式不得表述为拥有不重复发布保证,实际 {note!r}")


def test_recovery_review_sections() -> None:
    root = Path(tempfile.mkdtemp(prefix="mgs02-gate-recv-"))
    try:
        _records_review_fix(root)
        _review2_sp1(root)
        _review2_sp2(root)
        _review3_sp7(root)
        _review4_sp10(root)
    finally:
        shutil.rmtree(root, ignore_errors=True)


TESTS = (test_recovery_review_sections,)

if __name__ == "__main__":
    sys.exit(run_theme("恢复与部分成功审查修复批(通道侧)", TESTS, FAILURES))

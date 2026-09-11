#!/usr/bin/env python3
"""写操作(授权闸门/防重/超时回读/更新/关系/关闭)。

任务票 11 从 tests/test_github_backend.py 按真实行为主题拆出;检查含义与原
案例保持一致,仅重组位置。原总入口仍聚合本主题。本主题可直接运行:

    python3 -B tests/test_github_write_ops.py
"""

import json
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
import mgs_records  # noqa: E402

FAILURES, check = make_checker()


def test_write_requires_authorization() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = make_github_project(Path(tmp), external="无(仅本地引用,未授权远端写入)")
        fake = FakeTransport()
        backend = backend_for(root, fake)
        try:
            backend.create_task("01-alpha", "甲任务", {})
        except mgs_github.GithubRecordsError as exc:
            message = str(exc)
            check("不等于批准远端写入" in message or "授权" in message,
                  f"未授权写操作应说明授权缺失:{message}")
        else:
            check(False, "CONFIG 无 issues-write 授权时写操作必须拒绝")
        check(not any(c[0] == "POST" for c in fake.calls),
              "未授权时不得发出任何远端写请求")
    with tempfile.TemporaryDirectory() as tmp:
        # 授权了别的仓库,目标仓库不在范围 → 同样拒绝
        root = make_github_project(
            Path(tmp), external="github.com/other/repo:issues-write(与目标仓库不符)")
        fake = FakeTransport()
        backend = backend_for(root, fake)
        try:
            backend.create_task("01-alpha", "甲任务", {})
        except mgs_github.GithubRecordsError:
            check(True, "")
        else:
            check(False, "授权仓库与目标仓库不一致时必须拒绝")
        check(not any(c[0] == "POST" for c in fake.calls),
              "仓库范围外的授权不得产生远端写请求")


def test_create_and_duplicate_protection() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = make_github_project(Path(tmp))
        fake = FakeTransport()
        backend = backend_for(root, fake)
        result = backend.create_task(
            "01-alpha", "甲任务",
            {"当前目标": "演示目标", "完成标准": "示例标准", "执行责任": "Agent(制作实现)"},
            triage="ready-for-agent")
        check(result["created"] is True and result["issue_number"] == 1,
              f"首次创建应成功并回报 Issue 号,实际 {result}")
        check(result["readback"]["identity"] == "01-alpha", "创建后必须回读核对身份")
        # 重复创建同一身份:收养既有 Issue,不新建
        result = backend.create_task("01-alpha", "甲任务", {})
        check(result["created"] is False and result.get("adopted") is True,
              f"重复创建应收养既有任务,实际 {result}")
        posts = [c for c in fake.calls if c[0] == "POST" and c[1].endswith("/issues")]
        check(len(posts) == 1, f"重复创建不得发出第二次 POST,实际 {len(posts)} 次")


def test_create_timeout_reads_back_before_retry() -> None:
    """超时/响应丢失:先回读(已落地则收养),未落地才重试一次;如实上报尝试。"""

    with tempfile.TemporaryDirectory() as tmp:
        root = make_github_project(Path(tmp))
        fake = FakeTransport()
        fake.drop("POST", "/issues")  # 第一次 POST 已生效但响应丢失
        backend = backend_for(root, fake)
        result = backend.create_task("01-alpha", "甲任务", {})
        check(result["created"] is False and result.get("adopted") is True,
              f"超时后回读发现已创建应收养,不重复创建,实际 {result}")
        check(result["attempts"][0].get("outcome") == "timeout",
              f"尝试历史应如实记录超时,实际 {result.get('attempts')}")
        check(result["duplicate_avoided"] is True, "应标记避免了重复创建")
        check(len([i for i in fake.issues
                   if "任务身份:01-alpha" in i["body"]]) == 1,
              "远端必须只有一个 01-alpha")
    with tempfile.TemporaryDirectory() as tmp:
        root = make_github_project(Path(tmp))
        fake = FakeTransport()
        fake.fail("POST", "/issues", "timeout")  # 两次都超时且未落地
        backend = backend_for(root, fake)
        try:
            backend.create_task("01-alpha", "甲任务", {})
        except mgs_github.GithubRecordsError as exc:
            check("未确认" in str(exc) or "失败" in str(exc),
                  f"回读+重试后仍未落地应如实报失败:{exc}")
        else:
            check(False, "回读与重试都未落地时应报错,不得虚报成功")
        posts = [c for c in fake.calls if c[0] == "POST" and c[1].endswith("/issues")]
        check(len(posts) == 2, f"重试恰好一次(共 2 次 POST),实际 {len(posts)}")


def test_update_task_fields_and_version_check() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = make_github_project(Path(tmp))
        fake = FakeTransport()
        fake.seed_issue("01-alpha", "甲任务")
        backend = backend_for(root, fake)
        result = backend.update_task("01-alpha", {"进度": "执行中",
                                                  "当前目标": "新目标"})
        check(result["readback"]["progress"] == "执行中",
              f"安排更新应回读新进度,实际 {result['readback'].get('progress')}")
        check(result["readback"]["request"]["当前目标"] == "新目标",
              "工作请求字段更新应可回读")
        # 版本校验:expected_body_sha256 与远端当前正文不符 → 拒绝(不覆盖他人改动)
        try:
            backend.update_task("01-alpha", {"进度": "已完成"},
                                expected_body_sha256="0" * 64)
        except mgs_github.GithubRecordsError as exc:
            check("已被他人修改" in str(exc) or "不符" in str(exc),
                  f"版本不符应拒绝覆盖:{exc}")
        else:
            check(False, "expected_body_sha256 不符时应拒绝更新")
        task = mgs_records.read_task(root, "01-alpha", transport=fake)
        check(task["progress"] == "执行中", "被拒更新不得改变远端内容")


def test_set_triage_and_append_result() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = make_github_project(Path(tmp))
        fake = FakeTransport()
        fake.seed_issue("01-alpha", "甲任务")
        backend = backend_for(root, fake)
        result = backend.set_triage("01-alpha", "needs-info")
        check(result["readback"]["triage"] == "needs-info",
              f"分流应更新并回读,实际 {result['readback'].get('triage')}")
        labels_now = [l["name"] for l in fake.issues[0]["labels"]]
        check(labels_now == ["info"], f"标签应换成映射后的 info,实际 {labels_now}")
        try:
            backend.set_triage("01-alpha", "done")
        except mgs_github.GithubRecordsError:
            check(True, "")
        else:
            check(False, "五类之外的分流值应拒绝")
        result = backend.append_result("01-alpha", "已交付骨架与检查输出。")
        check(result["comment_id"] is not None and result["published"] is True,
              f"结果追加应发布评论并回报,实际 {result}")
        task = mgs_records.read_task(root, "01-alpha", transport=fake)
        check(len(task["results"]) == 1
              and task["results"][0]["excerpt"].startswith("任务:01-alpha"),
              f"评论结果应带任务身份前缀并可回读,实际 {task['results']}")
        check(f"#issuecomment-{result['comment_id']}" in task["result_index_text"],
              "结果索引应引用该评论(评论与索引一致)")


def test_relations_native_and_fallback() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = make_github_project(Path(tmp))
        fake = FakeTransport(sub_issues_supported=True)
        fake.seed_issue("01-alpha", "甲任务")
        fake.seed_issue("02-beta", "乙任务")
        fake.seed_issue("03-plan", "拆单管理", project_label=None,
                        triage="ready-for-agent", progress="执行中")
        backend = backend_for(root, fake)
        result = backend.set_relations("02-beta", ["01-alpha"])
        check(result["readback"]["request"]["依赖"] == "#1 01-alpha",
              f"依赖应写成明确可解析引用(#Issue号 身份),实际 "
              f"{result['readback']['request'].get('依赖')}")
        graph = mgs_records.task_dependencies(root, transport=fake)
        check(graph["edges"].get("02-beta") == ["01-alpha"],
              "引用写法应能被 deps 解析回身份")
        # 原生父子关系可用:把 02 挂为 03 的子 Issue(原生 API 按 issue id 挂)
        result = backend.set_parent("02-beta", "03-plan")
        check(result["mode"] == "native-sub-issues"
              and fake.sub_issues.get(3) == [1002],
              f"原生 sub-issues 可用时应实际使用(按 issue id 挂接),实际 "
              f"{result.get('mode')}/{fake.sub_issues}")
    with tempfile.TemporaryDirectory() as tmp:
        root = make_github_project(Path(tmp))
        fake = FakeTransport(sub_issues_supported=False)  # 后端不提供原生关系
        fake.seed_issue("01-alpha", "甲任务")
        fake.seed_issue("02-beta", "乙任务")
        fake.seed_issue("03-plan", "拆单管理", project_label=None,
                        triage="ready-for-agent", progress="执行中")
        backend = backend_for(root, fake)
        result = backend.set_parent("02-beta", "03-plan")
        check(result["mode"] == "body-reference",
              f"原生关系不可用时应回退正文引用,实际 {result}")
        check("父任务:#3 03-plan" in result["readback"]["body"],
              "正文引用应明确可解析(#Issue号 身份)")


def test_close_reasons() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = make_github_project(Path(tmp))
        fake = FakeTransport()
        backend = backend_for(root, fake)
        for identity, title in (("01-done", "完成任务"), ("02-drop", "不再执行"),
                                ("03-covered", "成果覆盖")):
            backend.create_task(identity, title, {"当前目标": "演示",
                                                  "完成标准": "示例",
                                                  "执行责任": "Agent(制作实现)"})
        result = backend.close_task("01-done", "完成")
        check(result["readback"]["state"] == "closed"
              and result["readback"]["state_reason"] == "completed",
              f"完成应关闭为 completed,实际 {result['readback']}")
        check(result["readback"]["progress"] == "已完成", "正文进度应同步为已完成")
        check("不自动等于验证通过" in result["note"],
              "关闭结果必须声明不自动等于验证通过")
        result = backend.close_task("02-drop", "不再执行")
        check(result["readback"]["state_reason"] == "not_planned",
              f"不再执行应关闭为 not_planned,实际 {result['readback']}")
        result = backend.close_task("03-covered", "已有成果覆盖")
        check(result["readback"]["state_reason"] == "completed"
              and "已有成果覆盖" in result["readback"]["progress"],
              f"已有成果覆盖应表达在进度与说明中,实际 {result['readback']}")
        try:
            backend.close_task("01-done", "随便关")
        except mgs_github.GithubRecordsError:
            check(True, "")
        else:
            check(False, "关闭原因必须限定三类,不得含糊关闭")


def test_update_change_note_three_paths() -> None:
    """核验建议 2:安排更新说明三路一致(在线执行/草稿保存/重放),
    重放后不回退默认文案「安排更新」。"""

    with tempfile.TemporaryDirectory() as tmp:
        root = make_github_project(Path(tmp))
        cache = Path(tmp) / "cache"
        fake = FakeTransport()
        fake.seed_issue("01-alpha", "甲任务")
        backend = backend_for(root, fake, cache)
        # 1) 在线执行
        result = backend.update_task("01-alpha", {"进度": "执行中"},
                                     change_note="冲刺轮安排")
        check("冲刺轮安排" in result["readback"]["body"],
              "在线执行的说明应写入正文状态变化")
        # 2) 草稿保存:说明随草稿参数保留
        fake.offline()
        draft = backend.update_task("01-alpha", {"进度": "待验收"},
                                    change_note="验收轮安排")
        saved = json.loads(Path(draft["draft"]).read_text(encoding="utf-8"))
        check(saved["args"].get("change_note") == "验收轮安排",
              f"草稿应保存自定义说明,实际 {saved['args']}")
        # 3) 重放:说明随重放传递
        fake._offline = False
        published = backend.publish_drafts()
        check(published["published_count"] == 1,
              f"草稿应发布成功:{published['results']}")
        body = fake.issues[0]["body"]
        check("验收轮安排" in body,
              f"重放后正文应保留原说明(不回退默认文案),实际正文含默认文案:"
              f"{'安排更新' in body}")

TESTS = (
    test_write_requires_authorization,
    test_create_and_duplicate_protection,
    test_create_timeout_reads_back_before_retry,
    test_update_task_fields_and_version_check,
    test_set_triage_and_append_result,
    test_relations_native_and_fallback,
    test_close_reasons,
    test_update_change_note_three_paths,
)

if __name__ == "__main__":
    sys.exit(run_theme("写操作(授权闸门/防重/超时回读/更新/关系/关闭)", TESTS, FAILURES))

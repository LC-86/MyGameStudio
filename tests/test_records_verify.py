#!/usr/bin/env python3
"""本地与 GitHub 后端核验。

任务票 11 从 tests/test_records_backend.py 按真实行为主题拆出;检查含义与原
案例保持一致,仅重组位置。原总入口仍聚合本主题。本主题可直接运行:

    python3 -B tests/test_records_verify.py
"""

import sys
import tempfile
from pathlib import Path

from records_backend_support import (
    FIVE_LABELS, RESULT_TEMPLATE, SAMPLE, _GithubVerifyTransport,
    _github_issue, make_checker, make_plan_project, make_project, run_theme,
    scoped_read_counter,
)

import mgs_records  # noqa: E402

FAILURES, check = make_checker()


def test_verify_ok_sample() -> None:
    report = mgs_records.verify_project(SAMPLE)
    names = {c["name"] for c in report["checks"]}
    expected = {"config-present", "backend-local-markdown", "task-root-exists",
                "labels-complete", "labels-no-conflict", "docmap-core-rows",
                "docmap-unique-authority", "docmap-paths-exist",
                "tasks-valid", "results-consistent"}
    check(expected <= names, f"verify 应包含约定检查项,缺 {expected - names}")
    if not report["ok"]:
        for c in report["checks"]:
            if not c["ok"]:
                FAILURES.append(f"样例 verify 不应失败:{c['name']}:{c['detail']}")
    check(report["ok"], "role-scope-demo 样例应整体通过 verify")


def test_verify_label_failures() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = make_project(Path(tmp), label_rows="\n".join(
            f"| {name} | {name} |" for name in FIVE_LABELS[:4]))
        report = mgs_records.verify_project(root)
        failed = {c["name"] for c in report["checks"] if not c["ok"]}
        check("labels-complete" in failed, f"缺一类标签应判 labels-complete 失败,实际 {failed}")
    with tempfile.TemporaryDirectory() as tmp:
        rows = [f"| {name} | ready-for-agent |" for name in FIVE_LABELS]
        root = make_project(Path(tmp), label_rows="\n".join(rows))
        report = mgs_records.verify_project(root)
        failed = {c["name"] for c in report["checks"] if not c["ok"]}
        check("labels-no-conflict" in failed,
              f"五类语义映射到同一标签应判冲突,实际 {failed}")


def test_verify_docmap_failures() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = make_project(Path(tmp))
        config_path = root / "docs" / "mygamestudio" / "CONFIG.md"
        text = config_path.read_text(encoding="utf-8")
        config_path.write_text(text.replace(
            "| 技术设计 | docs/mygamestudio/TECH_DESIGN.md | 制作实现 |\n", ""),
            encoding="utf-8")
        failed = {c["name"] for c in mgs_records.verify_project(root)["checks"] if not c["ok"]}
        check("docmap-core-rows" in failed, f"缺技术设计行应判失败,实际 {failed}")
    with tempfile.TemporaryDirectory() as tmp:
        root = make_project(Path(tmp))
        config_path = root / "docs" / "mygamestudio" / "CONFIG.md"
        text = config_path.read_text(encoding="utf-8")
        config_path.write_text(text.replace(
            "| 技术设计 | docs/mygamestudio/TECH_DESIGN.md | 制作实现 |",
            "| 技术设计 | docs/mygamestudio/PROJECT.md | 制作实现 |"),
            encoding="utf-8")
        failed = {c["name"] for c in mgs_records.verify_project(root)["checks"] if not c["ok"]}
        check("docmap-unique-authority" in failed, f"两类内容同一权威位置应判失败,实际 {failed}")
    with tempfile.TemporaryDirectory() as tmp:
        root = make_project(Path(tmp), with_core_docs=False)
        failed = {c["name"] for c in mgs_records.verify_project(root)["checks"] if not c["ok"]}
        check("docmap-paths-exist" in failed, f"核心文档缺失应判失败,实际 {failed}")


def test_verify_task_failures() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = make_project(Path(tmp))
        task_path = root / "docs" / "mygamestudio" / "work" / "01-demo" / "task.md"
        task_path.write_text(task_path.read_text(encoding="utf-8").replace(
            "当前分流:ready-for-agent", "当前分流:done"),
            encoding="utf-8")
        failed = {c["name"] for c in mgs_records.verify_project(root)["checks"] if not c["ok"]}
        check("tasks-valid" in failed, f"五类之外的分流值应判失败,实际 {failed}")
    with tempfile.TemporaryDirectory() as tmp:
        root = make_project(Path(tmp))
        task_path = root / "docs" / "mygamestudio" / "work" / "01-demo" / "task.md"
        task_path.write_text(task_path.read_text(encoding="utf-8").replace(
            "任务身份:01-demo", "任务身份:other-id"),
            encoding="utf-8")
        failed = {c["name"] for c in mgs_records.verify_project(root)["checks"] if not c["ok"]}
        check("tasks-valid" in failed, "任务身份与目录不一致应判失败")


def test_verify_results_consistency() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = make_project(Path(tmp))
        results = root / "docs" / "mygamestudio" / "work" / "01-demo" / "results"
        results.mkdir()
        (results / "2026-09-08.md").write_text(
            RESULT_TEMPLATE.format(title="演示任务", identity="01-demo"), encoding="utf-8")
        failed = {c["name"] for c in mgs_records.verify_project(root)["checks"] if not c["ok"]}
        check("results-consistent" in failed,
              f"结果文件存在但结果索引仍为暂无应判失败,实际 {failed}")
        task_path = root / "docs" / "mygamestudio" / "work" / "01-demo" / "task.md"
        task_path.write_text(task_path.read_text(encoding="utf-8").replace(
            "(暂无)", "results/2026-09-08.md:骨架交付"),
            encoding="utf-8")
        report = mgs_records.verify_project(root)
        check(report["ok"], f"结果被索引引用后应整体通过:{report['checks']}")
    with tempfile.TemporaryDirectory() as tmp:
        root = make_project(Path(tmp))
        results = root / "docs" / "mygamestudio" / "work" / "01-demo" / "results"
        results.mkdir()
        (results / "2026-09-08.md").write_text(
            RESULT_TEMPLATE.format(title="演示任务", identity="99-other"), encoding="utf-8")
        task_path = root / "docs" / "mygamestudio" / "work" / "01-demo" / "task.md"
        task_path.write_text(task_path.read_text(encoding="utf-8").replace(
            "(暂无)", "results/2026-09-08.md:骨架交付"),
            encoding="utf-8")
        failed = {c["name"] for c in mgs_records.verify_project(root)["checks"] if not c["ok"]}
        check("results-consistent" in failed, "结果文件不引用所属任务身份应判失败")


def test_verify_results_index_must_reference_every_file() -> None:
    """多条结果文件仅索引一条时不得报一致:每份结果都必须被索引引用。"""

    with tempfile.TemporaryDirectory() as tmp:
        root = make_project(Path(tmp))
        results = root / "docs" / "mygamestudio" / "work" / "01-demo" / "results"
        results.mkdir()
        (results / "2026-09-08.md").write_text(
            RESULT_TEMPLATE.format(title="演示任务", identity="01-demo"), encoding="utf-8")
        (results / "2026-09-09.md").write_text(
            RESULT_TEMPLATE.format(title="演示任务", identity="01-demo"), encoding="utf-8")
        task_path = root / "docs" / "mygamestudio" / "work" / "01-demo" / "task.md"
        task_path.write_text(task_path.read_text(encoding="utf-8").replace(
            "(暂无)", "- results/2026-09-08.md:骨架交付"), encoding="utf-8")
        report = mgs_records.verify_project(root)
        failed = {c["name"] for c in report["checks"] if not c["ok"]}
        check("results-consistent" in failed,
              f"多条结果仅索引一条应判 results-consistent 失败,实际 {failed}")
        detail = next(c["detail"] for c in report["checks"]
                      if c["name"] == "results-consistent")
        check("2026-09-09.md" in detail,
              f"失败详情应指出未被索引的结果文件,实际 {detail}")
        task_path.write_text(task_path.read_text(encoding="utf-8").replace(
            "- results/2026-09-08.md:骨架交付",
            "- results/2026-09-08.md:骨架交付\n- results/2026-09-09.md:补交"),
            encoding="utf-8")
        report = mgs_records.verify_project(root)
        check(report["ok"],
              f"全部结果被索引引用后应整体通过:{[c for c in report['checks'] if not c['ok']]}")


def test_verify_malformed_records_still_discoverable() -> None:
    """AC3/READ-08/READ-25:畸形记录(缺身份)与未知分流仍能被核验发现。

    畸形任务仍处于本次唯一任务集合内,不被读取层提前过滤;后端专有定位
    (任务目录)保留,便于定位原记录。
    """

    with tempfile.TemporaryDirectory() as tmp:
        root = make_project(Path(tmp))
        task_path = root / "docs" / "mygamestudio" / "work" / "01-demo" / "task.md"
        task_path.write_text(
            task_path.read_text(encoding="utf-8").replace(
                "任务身份:01-demo", "任务身份:"), encoding="utf-8")
        report = mgs_records.verify_project(root)
        failed = {c["name"] for c in report["checks"] if not c["ok"]}
        check("tasks-valid" in failed,
              f"缺身份任务应判 tasks-valid 失败,实际 {failed}")
        detail = next(c["detail"] for c in report["checks"]
                      if c["name"] == "tasks-valid")
        check("01-demo" in detail and "身份" in detail,
              f"缺身份问题应定位到任务目录,实际 {detail}")
    with tempfile.TemporaryDirectory() as tmp:
        root = make_project(Path(tmp))
        task_path = root / "docs" / "mygamestudio" / "work" / "01-demo" / "task.md"
        task_path.write_text(task_path.read_text(encoding="utf-8").replace(
            "当前分流:ready-for-agent", "当前分流:done"), encoding="utf-8")
        report = mgs_records.verify_project(root)
        failed = {c["name"] for c in report["checks"] if not c["ok"]}
        check("tasks-valid" in failed and report["ok"] is False,
              f"五类之外的分流应判失败,实际 {failed}")


def test_verify_reads_config_and_tasks_once_local() -> None:
    """AC1/AC3/READ-04/READ-08:本地 verify 同次复用配置与任务集合一次。

    CONFIG 只读一次、每份 task.md 一次;检查名称与顺序保持;整体结论与既有
    语义一致(不复用会重复读 CONFIG)。
    """

    with tempfile.TemporaryDirectory() as tmp:
        root = make_plan_project(Path(tmp))
        with scoped_read_counter(root) as counter:
            report = mgs_records.verify_project(root)
        check(counter.config_reads() == 1,
              f"verify 应只读 CONFIG 原文一次,实际 {counter.by_path}")
        task_reads = counter.task_reads()
        check(task_reads and all(n == 1 for n in task_reads.values())
              and len(task_reads) == 7,
              f"verify 每份 task.md 应恰好读一次,实际 {task_reads}")
        names = [c["name"] for c in report["checks"]]
        expected = ["config-present", "backend-local-markdown", "task-root-exists",
                    "labels-complete", "labels-no-conflict", "docmap-core-rows",
                    "docmap-unique-authority", "docmap-paths-exist",
                    "tasks-valid", "results-consistent", "deps-consistent"]
        check(names == expected, f"verify 检查名称与顺序应保持,实际 {names}")
        check(report["ok"],
              f"健康拆单项目应通过 verify:{[c for c in report['checks'] if not c['ok']]}")


def test_verify_github_reads_single_task_set_and_keeps_backend_reads() -> None:
    """AC1/AC4/READ-11:github verify 同次复用配置;任务集合获取一次,
    标签与评论核验仍实际发生(不因减少请求删掉必要读取)。
    """

    with tempfile.TemporaryDirectory() as tmp:
        root = make_project(Path(tmp), backend="github-issues", extra_task=False)
        fake = _GithubVerifyTransport(
            [_github_issue("01-alpha", "甲任务", 1)],
            labels=FIVE_LABELS, comments={1: []})
        with scoped_read_counter(root) as counter:
            report = mgs_records.verify_project(root, transport=fake)
        check(counter.config_reads() == 1,
              f"github verify 应只读 CONFIG 原文一次,实际 {counter.by_path}")
        list_calls = [c for c in fake.calls if c[0] == "GET"
                      and c[1].split("?", 1)[0].rstrip("/").endswith("/issues")]
        label_calls = [c for c in fake.calls if c[0] == "GET"
                       and c[1].split("?", 1)[0].rstrip("/").endswith("/labels")]
        comment_calls = [c for c in fake.calls if c[0] == "GET"
                         and c[1].split("?", 1)[0].rstrip("/").endswith("/comments")]
        check(len(list_calls) == 1,
              f"任务集合应只获取一次,实际 {list_calls}")
        check(len(label_calls) == 1,
              f"仓库标签核验仍应实际发生一次,实际 {label_calls}")
        check(len(comment_calls) == 1,
              f"每任务评论核验仍应实际发生,实际 {comment_calls}")
        names = {c["name"] for c in report["checks"]}
        check({"labels-remote-present", "results-consistent",
               "tasks-valid", "deps-consistent"} <= names
              and report["ok"] is True,
              f"github verify 结论应保持:{[c for c in report['checks'] if not c['ok']]}")

TESTS = (
    test_verify_ok_sample,
    test_verify_label_failures,
    test_verify_docmap_failures,
    test_verify_task_failures,
    test_verify_results_consistency,
    test_verify_results_index_must_reference_every_file,
    test_verify_malformed_records_still_discoverable,
    test_verify_reads_config_and_tasks_once_local,
    test_verify_github_reads_single_task_set_and_keeps_backend_reads,
)

if __name__ == "__main__":
    sys.exit(run_theme("本地与 GitHub 后端核验", TESTS, FAILURES))

#!/usr/bin/env python3
"""GitHub 后端 CLI 真实入口。

任务票 11 从 tests/test_github_backend.py 按真实行为主题拆出;检查含义与原
案例保持一致,仅重组位置。原总入口仍聚合本主题。本主题可直接运行:

    python3 -B tests/test_github_cli.py
"""

import json
import sys
import tempfile
from pathlib import Path

from github_backend_transport import FakeTransport
from github_backend_fixtures import (
    REPO_ROOT, _StandinServer, make_checker, make_github_project, run_cli,
    run_theme,
)

import mgs_records  # noqa: E402

FAILURES, check = make_checker()


def test_cli_github_write_ops() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = make_github_project(Path(tmp))
        cache = Path(tmp) / "cache"
        fake = FakeTransport()
        server = _StandinServer(fake)
        server.start()
        common = ["--project", str(root), "--api-base", server.base,
                  "--cache-dir", str(cache)]
        try:
            result = run_cli("create", *common, "--identity", "01-alpha",
                             "--title", "甲任务", "--field", "当前目标=演示目标",
                             "--field", "完成标准=示例标准",
                             "--field", "执行责任=Agent(制作实现)",
                             "--triage", "ready-for-agent")
            check(result.returncode == 0,
                  f"CLI create 应成功:{result.stdout[:300]}{result.stderr[:200]}")
            data = json.loads(result.stdout)
            check(data["created"] is True and data["issue_number"] == 1,
                  f"CLI create 应回报创建与 Issue 号,实际 {data}")
            result = run_cli("list", *common)
            check([t["identity"] for t in json.loads(result.stdout)] == ["01-alpha"],
                  "CLI list 应列出远端任务")
            result = run_cli("show", *common, "--task", "01-alpha")
            check(json.loads(result.stdout)["title"] == "甲任务",
                  "CLI show 应回读远端任务")
            result = run_cli("update", *common, "--task", "01-alpha",
                             "--field", "进度=执行中")
            check(json.loads(result.stdout)["readback"]["progress"] == "执行中",
                  "CLI update 应更新进度并回读")
            result = run_cli("append-result", *common, "--task", "01-alpha",
                             "--text", "已交付并自检。")
            check(result.returncode == 0
                  and json.loads(result.stdout)["published"] is True,
                  f"CLI append-result 应发布评论:{result.stdout[:200]}")
            result = run_cli("set-triage", *common, "--task", "01-alpha",
                             "--label", "needs-info")
            check(json.loads(result.stdout)["readback"]["triage"] == "needs-info",
                  "CLI set-triage 应更新分流")
            result = run_cli("set-relations", *common, "--task", "01-alpha",
                             "--dep", "99-missing")
            check(result.returncode != 0,
                  "CLI set-relations 引用不存在任务应报错(不写悬空依赖)")
            result = run_cli("close", *common, "--task", "01-alpha",
                             "--reason", "完成")
            data = json.loads(result.stdout)
            check(data["readback"]["state"] == "closed",
                  "CLI close 应关闭任务并回读")
            # 无授权配置 → 写子命令拒绝
            noauth = make_github_project(Path(tmp) / "noauth",
                                         external="无(未授权)")
            result = run_cli("create", "--project", str(noauth),
                             "--api-base", server.base,
                             "--identity", "01-x", "--title", "x")
            check(result.returncode != 0 and "授权" in result.stdout,
                  f"无授权时 CLI 写操作应拒绝并说明:{result.stdout[:200]}")
        finally:
            server.stop()


def test_cli_local_backend_refuses_write_subcommands() -> None:
    result = run_cli("create", "--project", str(REPO_ROOT / "samples" / "role-scope-demo"),
                     "--identity", "09-x", "--title", "x")
    check(result.returncode != 0 and "mgs-gate" in result.stdout,
          f"本地后端写子命令应指向受控通道:{result.stdout[:200]}")
    result = run_cli("handover", "--project",
                     str(REPO_ROOT / "samples" / "role-scope-demo"))
    check(result.returncode != 0 and "github" in result.stdout,
          f"handover 应限定 github 后端:{result.stdout[:200]}")


def test_cli_github_handover_end_to_end() -> None:
    """票 17 第 7 条真实远端重放发现的缺陷固化:github 后端 CLI handover
    端到端路径崩溃(AttributeError:handover_baselinecheck_item——票 01-fix
    改名漏改 CLI 调用点)。未发布基线时必须输出 JSON 报告并以退出码 1 如实
    回报;崩溃的退出码恰为 1,会伪装成「不可达」结论,故必须锚定 JSON 输出。"""

    with tempfile.TemporaryDirectory() as tmp:
        root = make_github_project(Path(tmp))
        cache = Path(tmp) / "cache"
        fake = FakeTransport()
        server = _StandinServer(fake)
        server.start()
        common = ["--project", str(root), "--api-base", server.base,
                  "--cache-dir", str(cache)]
        try:
            result = run_cli("handover", *common)
            check(result.returncode == 1,
                  f"未发布基线时 handover 应以退出码 1 如实回报:"
                  f"{result.stdout[:200]}{result.stderr[:200]}")
            try:
                report = json.loads(result.stdout)
            except ValueError:
                check(False,
                      f"handover 应输出 JSON 报告而非崩溃(先看 stderr):"
                      f"{result.stderr[-300:]}")
                return
            check(report.get("ok") is False and len(report.get("docs", [])) >= 1,
                  f"handover 报告应含基线文档条目:{str(report)[:200]}")
            check(any("不可访问" in d.get("note", "") and "不得宣称" in d.get("note", "")
                      for d in report["docs"]),
                  "未发布基线应标注远端不可访问且不得宣称已可访问")
        finally:
            server.stop()


def test_cli_reverse_migration_real_entry() -> None:
    """S3:CLI 真实入口(子进程 + 真实 UrllibTransport 经本地 HTTP 替身)
    执行一次 GitHub→本地反向迁移,读取通道在 CLI 内建立。"""

    with tempfile.TemporaryDirectory() as tmp:
        base = Path(tmp)
        root = make_github_project(base / "project")
        fake = FakeTransport()
        fake.seed_issue("01-alpha", "甲任务")
        server = _StandinServer(fake)
        server.start()
        try:
            plan_path = base / "plan.json"
            emit = base / "emit"
            result = run_cli("switch-plan", "--project", str(root),
                             "--target", "local-markdown", "--emit", str(plan_path),
                             "--api-base", server.base)
            check(result.returncode == 0,
                  f"CLI switch-plan(反向)应成功:{result.stdout[:300]}"
                  f"{result.stderr[:200]}")
            if result.returncode != 0:
                return
            plan = json.loads(plan_path.read_text(encoding="utf-8"))
            check(plan["repo"] == "docs/mygamestudio/work",
                  f"CLI 迁移清单目标应为本地任务根,实际 {plan.get('repo')}")
            result = run_cli("switch-apply", "--project", str(root),
                             "--plan", str(plan_path), "--emit-dir", str(emit),
                             "--confirmed", "--api-base", server.base)
            check(result.returncode == 0,
                  f"CLI switch-apply(反向)应成功:{result.stdout[:300]}"
                  f"{result.stderr[:200]}")
            outcome = json.loads(result.stdout)
            check(outcome["created"] == 1 and Path(outcome["emit_dir"]).is_dir(),
                  f"CLI 迁移应产出任务且返回目录存在,实际 {outcome}")
            tasks = mgs_records.list_tasks(emit, "CONFIG.md")
            check([t["identity"] for t in tasks] == ["01-alpha"],
                  f"CLI 迁移后统一接口应能读取任务,实际 {tasks}")
        finally:
            server.stop()

TESTS = (
    test_cli_github_write_ops,
    test_cli_local_backend_refuses_write_subcommands,
    test_cli_github_handover_end_to_end,
    test_cli_reverse_migration_real_entry,
)

if __name__ == "__main__":
    sys.exit(run_theme("GitHub 后端 CLI 真实入口", TESTS, FAILURES))

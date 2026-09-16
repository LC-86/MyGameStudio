#!/usr/bin/env python3
"""票 #70(#68 第 1、9 项)修复回归:pending 正文比对与任务根逃逸。

- 迁移重试遇同身份旧 pending Issue 时必须比对正文:规划源更新后,
  重试应把新源内容写进同一目标,而不是未比对即收养、静默丢弃新内容。
- CONFIG task_root 为绝对路径或含 .. 时,本地写操作必须拒绝,
  不得把任务根解析到项目根之外落盘。

    python3 -B tests/test_r11_path_and_pending_body_regressions.py
"""

from __future__ import annotations

import sys
import tempfile
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "plugin" / "records"))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from github_backend_fixtures import make_checker, run_theme  # noqa: E402
from github_backend_transport import FakeTransport  # noqa: E402

import mgs_records  # noqa: E402
from mgs_github_material_migration import _find_pending_issue  # noqa: E402
from mgs_spec import SPEC_MARK  # noqa: E402  (收养针与生产同一常量)

from records_backend_support import make_project  # noqa: E402
from test_github_material_migration import (  # noqa: E402
    CORE_PLAY_V2, _pending_issues, _write_old_github_project, _write_tree)

FAILURES, check = make_checker()

CORE_PLAY_V3 = "玩家左右移动接住落下的金色星星。接到一颗得 2 分。漏接三次结束。"


def _overall_pending(root: Path, fake: FakeTransport) -> dict | None:
    backend = mgs_records.github_backend(root, transport=fake)
    return _find_pending_issue(backend, f"{SPEC_MARK}overall")


def test_retry_updates_pending_body_when_source_changed() -> None:
    """同身份旧 pending 不得未比对正文即收养:源更新后重试写入新内容。"""

    with tempfile.TemporaryDirectory() as tmp:
        root, fake = _write_old_github_project(Path(tmp) / "retry-body")
        first = mgs_records.apply_github_material_migration(
            root, confirmed=True, transport=fake)
        check(first.get("ok") is True, f"首次迁移应完成:{first}")
        created = _overall_pending(root, fake)
        check(created is not None, "首次迁移应创建现行规格待切换 Issue")
        number = created["number"]
        design = root / "docs/mygamestudio/GAME_DESIGN.md"
        design.write_text(
            design.read_text(encoding="utf-8").replace(
                CORE_PLAY_V2, CORE_PLAY_V3),
            encoding="utf-8")
        second = mgs_records.apply_github_material_migration(
            root, confirmed=True, transport=fake)
        check(second.get("ok") is True, f"重试迁移应完成:{second}")
        overall = _overall_pending(root, fake)
        check(overall is not None and overall["number"] == number,
              f"重试应更新同一待切换 Issue,不得新建重复目标,实际 "
              f"{overall and overall['number']}(首次为 {number})")
        body = (overall or {}).get("body") or ""
        check(CORE_PLAY_V3 in body,
              "规划源更新后重试必须把新内容写入待切换正文"
              f"(不得保留旧正文丢弃新源),实际含新文本={CORE_PLAY_V3 in body}")


def test_task_root_escape_is_rejected_for_writes() -> None:
    """task_root 绝对路径或含 .. 时写操作必须拒绝,不得逃逸项目根。"""

    for label in ("绝对路径", "上级目录"):
        with tempfile.TemporaryDirectory() as tmp:
            root = make_project(Path(tmp) / "proj")
            outside = Path(tmp) / "mgs-outside-work"
            location = (str(outside) if label == "绝对路径"
                        else f"docs/../../{outside.name}")
            config_path = root / "docs/mygamestudio/CONFIG.md"
            config_path.write_text(
                config_path.read_text(encoding="utf-8").replace(
                    "docs/mygamestudio/work/", location),
                encoding="utf-8")
            try:
                mgs_records.create_task(root, "09-escape", "越权任务",
                                        {"当前目标": "演示逃逸拒绝"})
            except mgs_records.RecordsError as exc:
                check("任务根" in str(exc) or "项目根" in str(exc),
                      f"{label}逃逸的错误应说明任务根约束:{exc}")
            except Exception as exc:  # 旧代码逃逸后回读崩溃,同样是失败证据
                check(False,
                      f"task_root 为{label}时写操作应以 RecordsError 拒绝,"
                      f"实际 {type(exc).__name__}:{exc}")
            else:
                check(False, f"task_root 为{label}时写操作必须拒绝,不得落盘")
            check(not outside.exists(),
                  f"task_root 为{label}时不得在项目根外创建任务目录:"
                  f"{outside}")
            check(not (root / "docs/mygamestudio/work/09-escape").exists(),
                  "拒绝后不得在项目根内留下半成品任务目录")


def test_prefix_snapshot_identities_stay_separate() -> None:
    """身份针不得前缀误配:ds-v1 与 ds-v1-0-0 必须各自独立成快照,
    v1.0.0 的内容不得被 ds-v1 收养(或收养后覆盖)。"""

    with tempfile.TemporaryDirectory() as tmp:
        root, fake = _write_old_github_project(Path(tmp) / "prefix")
        v100_rule = "白色星星只出现在 v1.0.0。"
        _write_tree(root, {
            "docs/mygamestudio/records/GAME_DESIGN-v1.0.0.md": (
                "# 历史 v1.0.0\n\n维护责任:方案设计。基线版本:v1.0.0。\n\n"
                f"{v100_rule}\n"),
        })
        applied = mgs_records.apply_github_material_migration(
            root, confirmed=True, transport=fake)
        check(applied.get("ok") is True, f"迁移应完成:{applied}")
        bodies: dict[str, str] = {}
        for item in fake.issues:
            body = item.get("body") or ""
            if "快照身份:" in body:
                key = body.split("快照身份:", 1)[1].split("。", 1)[0].strip()
                bodies[key] = body
        check("ds-v1" in bodies and "ds-v1-0-0" in bodies,
              f"ds-v1 与 ds-v1-0-0 必须各自独立成快照,实际 {sorted(bodies)}")
        check(v100_rule in bodies.get("ds-v1-0-0", ""),
              "v1.0.0 快照内容必须保留,不得被 ds-v1 收养覆盖")


def main() -> int:
    return run_theme(
        "票 #70 pending 正文比对与任务根逃逸回归",
        (
            test_retry_updates_pending_body_when_source_changed,
            test_prefix_snapshot_identities_stay_separate,
            test_task_root_escape_is_rejected_for_writes,
        ),
        FAILURES,
    )


if __name__ == "__main__":
    raise SystemExit(main())

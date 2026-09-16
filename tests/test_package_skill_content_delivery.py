#!/usr/bin/env python3
"""游戏统筹入口与记录后端仍有效检查;已退役交付入口不再公开(issue #50 解耦)。

    python3 -B tests/test_package_skill_content_delivery.py
"""

import json
import sys
from plugin_package_support import (PLUGIN_ROOT, make_checker, run_theme)

FAILURES, check = make_checker()


def test_game_producer_skill_content() -> None:
    producer = PLUGIN_ROOT / "skills" / "game-producer" / "SKILL.md"
    check(producer.is_file(), "缺少 skills/game-producer/SKILL.md")
    if producer.is_file():
        text = producer.read_text(encoding="utf-8")
        for ref in (
            "../../internal/game/invocation.md",
            "../../internal/game/stage-requirements.md",
            "../../internal/contracts/management.md",
            "../../internal/contracts/common.md",
        ):
            check(ref in text, f"game-producer SKILL.md 应引用 {ref}")
        check("只读" in text, "game-producer 状态查询应只读")
        check("gate-protocol" not in text and "mgs-gate" not in text,
              "game-producer 新版入口不得依赖 gate")


def test_retired_delivery_entries_not_public() -> None:
    for name in (
        "game-status", "game-build", "game-review", "game-playtest",
        "game-implement", "game-plan",
    ):
        check(not (PLUGIN_ROOT / "skills" / name / "SKILL.md").is_file(),
              f"{name} 不得再作为公开技能入口")


def test_github_issue_workflow_content() -> None:
    """记录后端公开接缝仍有效;GitHub 接入含认领与前沿查询。"""

    module = PLUGIN_ROOT / "records" / "mgs_github.py"
    check(module.is_file(), "缺少 records/mgs_github.py(GitHub Issues 后端适配器)")
    if module.is_file():
        records_dir = str(module.parent)
        if records_dir not in sys.path:
            sys.path.insert(0, records_dir)
        import mgs_github
        for seam in ("parse_repo_location", "parse_remote_authorizations"):
            check(callable(getattr(mgs_github, seam, None)),
                  f"records/mgs_github.py 缺少可用公开接缝 {seam}")
        check(isinstance(getattr(mgs_github, "GithubBackend", None), type),
              "records/mgs_github.py 缺少 GithubBackend")
        for method in ("create_task", "update_task", "set_triage", "append_result",
                       "set_relations", "set_parent", "claim_task", "frontier_tasks",
                       "close_task", "publish_drafts"):
            check(callable(getattr(mgs_github.GithubBackend, method, None)),
                  f"GithubBackend 缺少公开接缝 {method}")
        for seam in ("plan_backend_switch", "apply_backend_switch",
                     "handover_baseline_check"):
            check(callable(getattr(mgs_github, seam, None)),
                  f"records/mgs_github.py 缺少可用公开接缝 {seam}")
    skill_md = PLUGIN_ROOT / "skills" / "game-init" / "SKILL.md"
    if skill_md.is_file():
        text = skill_md.read_text(encoding="utf-8")
        check("setup-matt-pocock-skills" in text,
              "game-init 应将通用 tracker 配置交给上游 setup")
        check("plan_github_onboarding" in text or "GitHub Issues" in text,
              "game-init 应将 GitHub tracker 选择接到同一入口")
        check("mgs_remote" not in text and "mgs-gate" not in text,
              "game-init 新版入口不得把 mgs_remote/mgs-gate 当作普通路径")
    manifest_path = PLUGIN_ROOT / ".codex-plugin" / "plugin.json"
    manifest = json.loads(manifest_path.read_text())
    version = tuple(int(part) for part in manifest["version"].split("."))
    check(version >= (2, 0, 0), "改版组合包版本应不早于 2.0.0")


TESTS = (
    test_game_producer_skill_content,
    test_retired_delivery_entries_not_public,
    test_github_issue_workflow_content,
)


def main() -> int:
    return run_theme("业务 Skill 说明(构建/评审/试玩/统筹)", TESTS, FAILURES)


if __name__ == "__main__":
    sys.exit(main())

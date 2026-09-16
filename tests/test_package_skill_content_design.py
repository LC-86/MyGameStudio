#!/usr/bin/env python3
"""游戏设计入口与已退役设计/制作入口的包边界(issue #50 解耦)。

    python3 -B tests/test_package_skill_content_design.py
"""

import sys
from plugin_package_support import (PLUGIN_ROOT, make_checker, run_theme)
from redesign_bundle_contract import RETIRED_GAME_ENTRIES

FAILURES, check = make_checker()


def test_design_skills_content() -> None:
    """Game-Design 新版职责与阶段资料入口; Game-Spec 不再是公开入口。"""

    design = PLUGIN_ROOT / "skills" / "game-design" / "SKILL.md"
    check(design.is_file(), "缺少 skills/game-design/SKILL.md")
    if design.is_file():
        text = design.read_text(encoding="utf-8")
        for ref in (
            "../../internal/game/stage-requirements.md",
            "../../internal/game/invocation.md",
            "../../internal/contracts/design.md",
            "../../internal/contracts/common.md",
            "../grilling/SKILL.md",
            "../domain-modeling/SKILL.md",
        ):
            check(ref in text, f"game-design SKILL.md 应引用包内依据 {ref}")
        check("wayfinder" in text, "game-design 应提示大型不清晰路线调用 wayfinder")
        check("gate-protocol" not in text, "game-design 新版入口不得依赖 gate")
    spec = PLUGIN_ROOT / "skills" / "game-spec" / "SKILL.md"
    check(not spec.is_file(), "game-spec 不得再作为公开技能入口")


def test_retired_production_entries_not_public() -> None:
    """已退役设计/制作入口不再出现在有效公开技能目录。"""

    public = {p.name for p in (PLUGIN_ROOT / "skills").iterdir() if p.is_dir()}
    leaked = sorted(set(RETIRED_GAME_ENTRIES) & public)
    check(not leaked, f"已退役入口仍在 skills/: {leaked}")


TESTS = (
    test_design_skills_content,
    test_retired_production_entries_not_public,
)


def main() -> int:
    return run_theme("业务 Skill 说明(设计/原型/制作)", TESTS, FAILURES)


if __name__ == "__main__":
    sys.exit(main())

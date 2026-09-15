"""Issue #50 / spec #49 literals for the public package seam.

Expected values come from GitHub issue #49 D1 D2 D3 D8 and T1 T2, not from
the implementation under test.
"""

# D2 official Matt 1.2.3 collection (commit 3cca18b...).
MATT_ENGINEERING = (
    "ask-matt",
    "diagnosing-bugs",
    "grill-with-docs",
    "triage",
    "improve-codebase-architecture",
    "setup-matt-pocock-skills",
    "tdd",
    "to-spec",
    "to-tickets",
    "wayfinder",
    "implement",
    "prototype",
    "research",
    "domain-modeling",
    "codebase-design",
    "code-review",
    "resolving-merge-conflicts",
    "wizard",
)

MATT_PRODUCTIVITY = (
    "grill-me",
    "grilling",
    "handoff",
    "teach",
    "to-questionnaire",
    "wait-what",
    "writing-for-agents",
)

MATT_OFFICIAL = MATT_ENGINEERING + MATT_PRODUCTIVITY

# D1: only these three game entries remain public.
GAME_ENTRIES = (
    "game-producer",
    "game-init",
    "game-design",
)

PUBLIC_SKILLS = MATT_OFFICIAL + GAME_ENTRIES

# D1 retired public entries. They must not be effective package skills.
RETIRED_GAME_ENTRIES = (
    "game-art",
    "game-audio",
    "game-build",
    "game-code",
    "game-implement",
    "game-plan",
    "game-playtest",
    "game-prototype",
    "game-review",
    "game-spec",
    "game-status",
)

# D2 / research of 3cca18b: 14 user-only (disable-model-invocation) skills.
MATT_USER_ONLY = (
    "ask-matt",
    "grill-me",
    "grill-with-docs",
    "handoff",
    "implement",
    "improve-codebase-architecture",
    "setup-matt-pocock-skills",
    "teach",
    "to-questionnaire",
    "to-spec",
    "to-tickets",
    "triage",
    "wait-what",
    "wayfinder",
)

MATT_MODEL_INVOKABLE = tuple(
    name for name in MATT_OFFICIAL if name not in MATT_USER_ONLY
)

UPSTREAM_NAME = "mattpocock/skills"
UPSTREAM_VERSION = "1.2.3"
UPSTREAM_SHA = "3cca18b368ae95cdbdebbff572ccafa662551015"

# D2 source paths inside the pinned upstream tree.
MATT_UPSTREAM_PATH = {
    **{name: f"skills/engineering/{name}" for name in MATT_ENGINEERING},
    **{name: f"skills/productivity/{name}" for name in MATT_PRODUCTIVITY},
}

STAGE_REQUIREMENTS_REL = "internal/game/stage-requirements.md"
INVOCATION_CONTRACT_REL = "internal/game/invocation.md"

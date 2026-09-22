# MyGameStudio

A lightweight, composable Agent Skills library for game development, installed natively through the official `skills` CLI.

**Current version: 3.0.0** (authority: [`VERSION`](VERSION))

MyGameStudio helps an agent design and build games using the tools already present in its environment, through explicit goals, rules, boundaries, task breakdowns, material references and verification requirements. It does not depend on a self-built workflow runtime to gate every step, and it does not force every game onto the same engine, layout, task platform or design-document template.

The human keeps goals, important trade-offs and explicitly reserved experience judgements. The agent handles fact-finding, method selection, document organisation, implementation steps, self-checks, and handing the remaining judgements back.

This file is a condensed mirror of [README.md](README.md). The Chinese README is authoritative.

## Install

```bash
npx skills@latest add LC-86/MyGameStudio              # discover and pick skills
npx skills@latest add LC-86/MyGameStudio --list       # list only, install nothing
npx skills@latest add LC-86/MyGameStudio --skill '*'  # install the whole set (recommended)
```

The target directory is decided by the official CLI and by you. This repo ships no installer, publishes no npm package, builds no tarball, and maintains no per-client directory conversion.

Details: [docs/installation.md](docs/installation.md). Dependency combinations for partial installs: [docs/dependencies.md](docs/dependencies.md). Migrating from the 2.0.2 plugin package: [docs/migration-v3.md](docs/migration-v3.md).

## The 20 skills

**User entries** start only when the user asks for that kind of work. **On-demand methods** are combined by the agent when the current task and authorization apply; the user can also request them directly.

The 8/12 split is an **instruction-layer convention** written into descriptions and bodies. Plain standard skill text has no cross-host enforcement power: this library uses no host-specific switch such as `disable-model-invocation`, so nothing stops a host from selecting a user entry on its own. If you need a harder boundary, restate it in your own project rules.

| Skill | Upstream | Invocation | Responsibility |
|---|---|---|---|
| [ask-gamestudio](skills/ask-gamestudio/SKILL.md) | ask-matt | user entry | Read-only navigation: one next step worth taking now |
| [setup-gamestudio](skills/setup-gamestudio/SKILL.md) | setup-matt-pocock-skills | user entry | Minimal project conventions, material entries, asset rules |
| [grill-gamestudio](skills/grill-gamestudio/SKILL.md) | grill-me | user entry | One-line entry to a pure interview |
| [grill-gamestudio-docs](skills/grill-gamestudio-docs/SKILL.md) | grill-with-docs | user entry | One-line entry to an interview that also maintains documents |
| [tasks-gamestudio](skills/tasks-gamestudio/SKILL.md) | to-tickets | user entry | Split into complete small outcomes with real dependencies and acceptance owners |
| [implement-gamestudio](skills/implement-gamestudio/SKILL.md) | implement | user entry | Implement the current work, organise checks, fixes and handover |
| [wayfinder-gamestudio](skills/wayfinder-gamestudio/SKILL.md) | wayfinder | user entry | Map cross-session unknowns and decision relations |
| [handoff-gamestudio](skills/handoff-gamestudio/SKILL.md) | handoff | user entry | Write a handover note the next session can actually use |
| [grilling-gamestudio](skills/grilling-gamestudio/SKILL.md) | grilling | on demand | Round-by-round clarification of goals, rules, trade-offs, verification |
| [domain-gamestudio](skills/domain-gamestudio/SKILL.md) | domain-modeling | on demand | Calibrate project vocabulary, keep necessary definitions and decision rationale |
| [gdd-gamestudio](skills/gdd-gamestudio/SKILL.md) | new | on demand | Maintain the current overall game design and system relations |
| [spec-gamestudio](skills/spec-gamestudio/SKILL.md) | to-spec | on demand | Capture this round of delivery and verification requirements |
| [tdd-gamestudio](skills/tdd-gamestudio/SKILL.md) | tdd | on demand | Small-step test-first implementation on public behaviour interfaces |
| [review-gamestudio](skills/review-gamestudio/SKILL.md) | code-review | on demand | Two-axis review of one actual deliverable: standards and spec |
| [debug-gamestudio](skills/debug-gamestudio/SKILL.md) | diagnosing-bugs | on demand | Evidence-based diagnosis, authorized fix, re-verify in the original scenario |
| [prototype-gamestudio](skills/prototype-gamestudio/SKILL.md) | prototype | on demand | Playable browser mini-game prototypes by default |
| [research-gamestudio](skills/research-gamestudio/SKILL.md) | research | on demand | Research at the depth the question needs, with sources and limits |
| [codebase-gamestudio](skills/codebase-gamestudio/SKILL.md) | codebase-design | on demand | Design responsibility, state ownership, interfaces and test seams |
| [merge-gamestudio](skills/merge-gamestudio/SKILL.md) | resolving-merge-conflicts | on demand | Resolve conflicts that already happened, by both sides' real intent |
| [docs-gamestudio](skills/docs-gamestudio/SKILL.md) | writing-for-agents | on demand | Shared writing method for all formal artifacts and subagent dispatch |

## How they compose

Skills are composable methods, not one pipeline. Four distinct actions: **reading an artifact**, **using a method**, **delegating work**, **recommending a next step**. A skill name appearing in text does not mean it ran.

`docs-gamestudio` is the shared writing method behind every formal artifact and every subagent dispatch: GDD, spec, tickets, glossary and decision records, research/test/review conclusions, handover notes, skills and project rules. Specialist skills decide the content; Docs keeps the expression faithful.

Ownership of shared references and the dependency graph: [docs/dependencies.md](docs/dependencies.md).

## What it does not do

No self-built task database, state machine, long-running dispatcher, or per-skill program runtime. No per-client plugin adapters, marketplace manifests, proprietary metadata or release pipeline. Loading a skill grants no permission: writing, uploading, paying, changing global config, committing and pushing all follow your actual request and the host's controls. It does not touch your other game projects' tasks, assets, saves or external storage.

## Verification status

Actually run and passing this round: 58 static checks (including regression assertions for all three pre-merge review rounds), the documentation navigation and version-consistency check, 19 isolated native install checks (official `skills` CLI 1.7.0), and 9 real behaviour scenarios. One behaviour scenario is blocked (the research scenario produced no result under this machine's network restrictions).

Installing from the remote repository source, pinned-tag installs, and discovery/invocation inside real hosts are **not run**. Per-item evidence, commands and limits are in [docs/validation-v3.md](docs/validation-v3.md).

A successful local install is not a successful remote GitHub install. Source complete, local install passing, behaviour verified and remote published are four different states and never substitute for each other. Until the remote default branch carries this version, `npx skills@latest add LC-86/MyGameStudio` does not install 3.0.0.

## License

MIT, see [LICENSE](LICENSE). Methods are adapted from Matt Pocock's skills, keeping his MIT license and attribution. Every skill directory carries its own `LICENSE` notice so a single-skill install still has complete license information. See [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md).

Maintained independently by LC-86. Not endorsed by Matt Pocock or by any host vendor.

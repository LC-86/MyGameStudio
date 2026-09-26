# MyGameStudio

A lightweight, composable Agent Skills library for game development, installed natively through the official `skills` CLI.

**Current version: 3.0.2** (authority: [`VERSION`](VERSION))

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

## 21 skills

The published `v3.0.2` release contains all 21 skills (8 user entries and 13 on-demand methods). The `v3.0.1` tag remains fixed at the previous 20-skill set.

**User entries** start only when the user asks for that kind of work. **On-demand methods** are combined by the agent when the current task and authorization apply; the user can also request them directly.

The 8/13 split is backed by three layers of invocation control (the mechanism comes from each host's official documentation; this library has not tested it inside every host). Claude Code, Grok Build and DSH enforce it through the frontmatter field `disable-model-invocation: true`, which keeps the skill description out of the model's context and leaves only the explicit user entry. Codex enforces it through the `agents/openai.yaml` inside each user-entry directory (`policy.allow_implicit_invocation: false`), which turns off implicit invocation. ZCode and Qoder document no invocation-control field, so there the split stays an **instruction-layer convention** written into descriptions and bodies, and it is the fallback in every host. If you need a harder boundary, restate it in your own project rules. These two layers ship starting with the `v3.0.1` release; versions installed from the `v3.0.0` tag and earlier do not contain them.

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
| [docs-gamestudio](skills/docs-gamestudio/SKILL.md) | original | on demand | Game-document routing, incremental collaboration and project reference access |
| [writing-for-agents](skills/writing-for-agents/SKILL.md) | LC-86 fork | on demand | General writing, semantic fidelity, skill mechanics and subagent delegation |

## How they compose

Skills are composable methods, not one pipeline. Four distinct actions: **reading an artifact**, **using a method**, **delegating work**, **recommending a next step**. A skill name appearing in text does not mean it ran.

`writing-for-agents` provides common writing, semantic fidelity and general delegation. `docs-gamestudio` handles only game-document routing and incremental updates; `tasks-gamestudio` retains human responsibility and acceptance handover.

Ownership of shared references and the dependency graph: [docs/dependencies.md](docs/dependencies.md).

## What it does not do

No self-built task database, state machine, long-running dispatcher, or per-skill program runtime. No per-client plugin adapters, marketplace manifests or release pipeline; the only host-specific file is the `agents/openai.yaml` carried by each of the 8 user entries (a fixed Codex invocation policy). Loading a skill grants no permission: writing, uploading, paying, changing global config, committing and pushing all follow your actual request and the host's controls. It does not touch your other game projects' tasks, assets, saves or external storage.

## Verification status

Actually run and passing for this release: 71 pytest checks, documentation validation (38 files, 21 skills), fixed-source sync, 23 native install checks (official `skills` CLI 1.7.0), and the source-switch matrix. After release, a fresh clone of `v3.0.2` passed 23/23 install checks; a pinned tag install found 21 skills and recorded the expected source lock. Codex behavior validation covered 14 ephemeral sessions and 2 fresh receiver contexts. See [validation](docs/validation-v3.md) and the [behavior evidence](docs/evidence/issue-87-behavior-matrix.md) for scope and limits. Discovery and invocation inside other real hosts were not run; support is not inferred.

A successful local install is not a successful remote GitHub install, so remote content is checked separately. The published `v3.0.2` tag contains 21 skills, while `v3.0.1` remains fixed at 20. `@latest` reads the repository's default branch, not a release tag. 2.0.2 and earlier are no longer maintained and receive no fixes; pin `LC-86/MyGameStudio#v2.0.2` if you need the old content, and see [docs/migration-v3.md](docs/migration-v3.md) for the switch.

## License

MIT, see [LICENSE](LICENSE). Methods are adapted from Matt Pocock's skills, keeping his MIT license and attribution. Every skill directory carries its own `LICENSE` notice so a single-skill install still has complete license information. See [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md).

Maintained independently by LC-86. Not endorsed by Matt Pocock or by any host vendor.

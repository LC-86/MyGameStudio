# MyGameStudio

**An AI workflow plugin for independent game developers.**

Turn a game idea into a clear design, actionable tasks, and results you can actually check.

MyGameStudio builds on a pinned release of Matt Pocock's engineering skills, and adds game-project onboarding, design discussions for gameplay and numbers, plus production status and playable-delivery requirements. You own the core loop and the important trade-offs. The assistant helps against explicit design, tasks, and checks.

Version **2.0.2** ships 25 pinned Matt skills plus 3 game entries, with the project MIT license bundled in the tarball. Client and tracker support is listed in the [compatibility matrix](docs/reference/compatibility.md) (Chinese).

This is not a game engine, and it will not ship a game from a single sentence.

The Chinese README is the complete first-edition homepage: [README.md](README.md). This English page matches its structure and version facts. Skill behavior is not duplicated in two languages.

## Intro

For solo developers and small teams who already use AI on a game, and need design, tasks, and delivery to stay connected.

Plugin id: `mygamestudio`. Display name: `MyGameStudio`. Skill ids stay lowercase (`game-init`, and so on).

## Why it exists

It adds clarification, a hand-off from design to engineering, and records you can verify. It does not silently turn a chat into a spec or a shippable build.

## What you get

- **Game-Init** (`game-init`): read-only analysis first; writes only after you confirm.
- **Game-Design** (`game-design`): gameplay and numbers discussion; discussion is not the spec.
- **Game-Producer** (`game-producer`): read-only status from real records; it must not auto-run user-only Matt skills.

You start `setup-matt-pocock-skills`, `to-spec`, `to-tickets`, `implement`, and `code-review` yourself. Full index: [docs/skills/README.md](docs/skills/README.md).

## Quick start

1. Install the **full plugin** from the [installation guide](docs/installation/README.md).
2. Confirm 28 skills are discovered.
3. Run `setup-matt-pocock-skills` in the game repo.
4. Run a **read-only** `game-init` pass before any write.

Details: [docs/getting-started.md](docs/getting-started.md).

## Install

Default distribution is the full plugin tarball on [Releases](https://github.com/LC-86/MyGameStudio/releases). Until a `v2.0.2` GitHub tag exists, use `dist/` in this repo.

Install the **full plugin root** (`plugin/` after unpacking the Release tar): `skills/`, `internal/`, `records/`, `templates/`, `provenance/`, and licenses. Do not copy a single `SKILL.md`. Do not treat `npx skills@latest add ...` as a supported path (sibling directories are unverified).

Chinese copy-one-line commands and the Agent install prompt live in [README.md](README.md) and [docs/installation/README.md](docs/installation/README.md).

```sh
shasum -a 256 -c SHA256SUMS.txt && tar -xzf mygamestudio-2.0.2.tar.gz
claude --plugin-dir <plugin-root>
codex plugin add mygamestudio@personal
grok plugin install <plugin-root> --trust
```

ZCode has **no verified one-line CLI** in current official plugin docs (UI: Settings → Plugins → Add marketplace). Do not invent `zcode plugins install`. Codex still needs `marketplace.json` `source.path` pointing at that full plugin root.

| Client | Guide | Real install of 2.0.2 |
| --- | --- | --- |
| Codex | [codex.md](docs/installation/codex.md) | Isolated CLI install verified; live session not verified |
| ZCode | [zcode.md](docs/installation/zcode.md) | Not verified |
| Grok Build | [grok-build.md](docs/installation/grok-build.md) | Not verified |
| Claude Code | [claude-code.md](docs/installation/claude-code.md) | Not verified |

ZCode local marketplace needs `.zcode-plugin/plugin.json` and `marketplace.json`. Grok Build uses `~/.grok/plugins` or `--plugin-dir`. Claude Code uses `.claude-plugin/plugin.json`, `claude --plugin-dir`, and cache `~/.claude/plugins/cache`. Isolation checks must not write real user plugin directories.

## Typical workflow

Map, not a mandatory pipeline: `game-init` → `game-design` as needed → you call `to-spec` / `to-tickets` / `implement`. `game-producer` is read-only status. See [workflows](docs/usage/workflows.md).

## Examples

[Existing-game change](examples/existing-game-change/README.md) and [first playable loop](examples/first-playable-loop/README.md). Expected text in those pages is illustrative unless a versioned check is cited.

## Limits

Not an engine, asset studio, or store publisher. Game records are local Markdown or GitHub Issues only. `implement` leaves work uncommitted without commit authorization. Codex CLI 0.154.0 isolated `plugin add`/`remove` of 2.0.2 is verified on Linux. Live-session skill discovery and ZCode / Grok Build / Claude Code installs are **not verified**.

## Relation to Matt

Independently maintained by LC-86, based on Matt Pocock skills 1.2.3 (`3cca18b368ae95cdbdebbff572ccafa662551015`). This is not an official Matt or host-vendor product. See [upstream.md](docs/reference/upstream.md) and [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md).

## Contributing and license

[CONTRIBUTING.md](CONTRIBUTING.md) · [SECURITY.md](SECURITY.md) · [LICENSE](LICENSE) (MIT for original work) · [CHANGELOG.md](CHANGELOG.md)

[AGENTS.md](AGENTS.md) is for maintainers of **this plugin repository**. Do not copy it into a user game project.

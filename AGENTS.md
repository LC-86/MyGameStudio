## Skill source layout

This repository is a native Agent Skills library with 21 discoverable skills. GameStudio-owned skills have one source at `skills/<skill-name>/SKILL.md`; `skills/writing-for-agents/` is a generated copy from the fixed authority in `LC-86/mattpocockskills`, recorded in its `SOURCE.md`. Its generated files are not an editable second authority. Do not create other duplicate skill bodies, a root-level aggregate `SKILL.md`, or any `SKILL.md` outside `skills/` (test fixtures belong in a temporary directory): the official `skills` CLI discovers every `SKILL.md` in the published tree.

Frontmatter uses standard fields only: `name`, `description`, `license`, and `compatibility` or `metadata` when genuinely needed. On top of that, each of the 8 user entries adds `disable-model-invocation: true` plus an `agents/openai.yaml` whose content is exactly the following two lines and nothing else — `policy:` and `  allow_implicit_invocation: false`; `argument-hint`, `allowed-tools`, and an `allow_implicit_invocation` field inside frontmatter stay forbidden; the 13 on-demand methods carry no host switch and no host file. That three-layer control is enforced by the frontmatter field in Claude Code, Grok Build and DSH and by `agents/openai.yaml` in Codex; ZCode and Qoder expose no host-level switch, so the same 8/13 boundary remains an instruction-layer convention written into descriptions and bodies.

Shared references have a single owner: semantic fidelity, subagent delegation and GameStudio document routing live in `docs-gamestudio`; human/agent responsibility and acceptance handover live in `tasks-gamestudio`. Consumers link them by sibling relative path. `writing-for-agents` is the external common method: reach it by its host-supported skill name, never by a cross-install-scope relative path, and never keep a second editable copy of it or of any other shared reference.

Run `python3.12 -m pytest tests/ -q` and `python3.12 scripts/validate-docs.py` after touching `skills/` or the docs. When changing the common writing method source pin or package, also run `python3.12 scripts/sync-writing-for-agents.py`. Static checks do not substitute for behaviour verification; record actual results in `docs/validation-v3.md` and mark anything not run as not-run.

When changing the discovered skill set, required dependencies, or installation/source switching, also run `bash scripts/install-smoke-test.sh` and `bash scripts/install-source-matrix-test.sh` in their temporary consumers. Before switching an installed copy, use `python3.12 scripts/verify-writing-for-agents-install.py` with that scope's lock file and a pristine same-source reference; treat a missing lock/manifest/reference or any reported difference as unverified and preserve the copy.

## Agent skills

### Issue tracker

Issues, specs, and Wayfinder maps are tracked in GitHub Issues for `LC-86/MyGameStudio`. Before tracker operations, read `docs/agents/issue-tracker.md`.

### Triage labels

The default five canonical triage labels are used. See `docs/agents/triage-labels.md`.

### Domain docs

This repository uses a single-context domain-document layout. See `docs/agents/domain.md`.

## Git commits

When a task is finished and verified, commit the files it changed as one snapshot, so the history keeps one checkpoint per task. Write commit messages in Simplified Chinese, in the existing `type: 说明` style (`feat:`, `fix:`, `docs:`, `chore:`), for example `fix: 修正安装脚本校验`. Stage only that task's files, skip the commit when the task changed no files, and keep commits local: pushing still requires explicit approval.

## Bilingual docs

`AGENTS.zh-CN.md` mirrors this file, and `README.en.md` mirrors `README.md`. When one side of a pair changes, update the other in the same task; keep heading structure and version facts aligned. The English README is a condensed mirror, not a literal translation.

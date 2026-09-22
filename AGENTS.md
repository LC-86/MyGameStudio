## Skill source layout

This repository is a native Agent Skills library. Each of the 20 skills has exactly one authoritative source at `skills/<skill-name>/SKILL.md`, with its own `references/`, `templates/` and `LICENSE` notice inside that directory. Do not create a second copy of a skill body, a root-level aggregate `SKILL.md`, or any `SKILL.md` outside `skills/` (test fixtures belong in a temporary directory): the official `skills` CLI discovers every `SKILL.md` in the published tree.

Frontmatter uses standard fields only: `name`, `description`, `license`, and `compatibility` or `metadata` when genuinely needed. Do not add `disable-model-invocation`, `allow_implicit_invocation`, `argument-hint`, `allowed-tools`, or any `agents/<host>.yaml`. The 8 user entries and 12 on-demand methods are an instruction-layer boundary expressed in descriptions and bodies, not a host-enforced one.

Shared references have a single owner: writing method, document routing and subagent delegation live in `docs-gamestudio`; human/agent responsibility and acceptance handover live in `tasks-gamestudio`. Consumers link them by sibling relative path. Never keep a second editable copy.

Run `python3.12 -m pytest tests/ -q` and `python3.12 scripts/validate-docs.py` after touching `skills/` or the docs. Static checks do not substitute for behaviour verification; record actual results in `docs/validation-v3.md` and mark anything not run as not-run.

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

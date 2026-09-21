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

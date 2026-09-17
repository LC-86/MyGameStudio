# Issue tracker: GitHub

Issues, specs, and Wayfinder maps for this repository default to GitHub Issues in [LC-86/MyGameStudio](https://github.com/LC-86/MyGameStudio/issues). Use the `gh` CLI; scope commands with `--repo LC-86/MyGameStudio` and API paths with `repos/LC-86/MyGameStudio`.

## Conventions

- **Create**: `gh issue create --repo LC-86/MyGameStudio --title "..." --body-file <draft.md>`.
- **Read**: `gh issue view <number> --repo LC-86/MyGameStudio --comments`. Fetch labels, assignees, and state with `--json` when needed.
- **List**: `gh issue list --repo LC-86/MyGameStudio --state open --json number,title,labels,assignees`; apply the relevant filters and paginate when the result may exceed the limit.
- **Update body**: `gh issue edit <number> --repo LC-86/MyGameStudio --body-file <draft.md>`.
- **Comment**: `gh issue comment <number> --repo LC-86/MyGameStudio --body-file <answer.md>`.
- **Labels**: `gh issue edit <number> --repo LC-86/MyGameStudio --add-label "..."` or `--remove-label "..."`. The role mapping is in [triage-labels.md](triage-labels.md); verify needed labels exist before publication.
- **Close**: `gh issue close <number> --repo LC-86/MyGameStudio` after recording the resolution and its evidence.

Keep multiline bodies in draft files, then use `--body-file`. Read back each external write; after an uncertain result, inspect actual state before retrying. Repository/user authorization governs remote writes, commits, and pushes; choosing this tracker does not publish existing material.

Triage labels describe routing. Record execution progress and acceptance separately in the issue and its result comments; closing an issue alone is not proof of validation.

## Pull requests as a triage surface

**PRs as a request surface: no.** `/triage` uses this flag. When a supplied number could refer to either an issue or a PR, resolve its type before operating on it.

## Publish and fetch

When a skill says **publish to the issue tracker**, create or update the corresponding GitHub issue within the authorized scope. Search for an existing matching issue first.

When a skill says **fetch the relevant ticket**, read the GitHub issue, comments, labels, assignees, state, and relevant relationships. An explicitly supplied legacy local path can still be read as source material.

## Wayfinding operations

The map is a GitHub issue; decision tickets are its child issues. Refer to each by its linked title.

- **Map**: label `wayfinder:map`; retain Destination, Notes, Decisions so far, Not yet specified, and Out of scope. The map indexes resolved decisions; their full answers live in their tickets.
- **Children**: create issues with `wayfinder:research`, `wayfinder:prototype`, `wayfinder:grilling`, or `wayfinder:task`, then attach them using GitHub's sub-issues API. Create all identities before wiring relationships.
- **Blocking**: use native issue dependencies. Add a blocker with `gh api --method POST repos/LC-86/MyGameStudio/issues/<child-number>/dependencies/blocked_by -F issue_id=<blocker-database-id>`. Fetch the numeric database id with `gh api repos/LC-86/MyGameStudio/issues/<blocker-number> --jq .id`; it is neither the issue number nor `node_id`.
- **Frontier**: list the map's children with pagination, retain open tickets without assignees and without open blockers, then select the first in the map's child order. `issue_dependencies_summary.blocked_by` reports open blockers; fetch relationships when needed rather than inferring them from titles.
- **Claim**: before work, assign the ticket to the driving developer with `gh issue edit <number> --repo LC-86/MyGameStudio --add-assignee @me`.
- **Resolve**: post the answer as a comment, close the child, then append its linked title and one-line gist to the map's Decisions so far. Read back the comment, state, and map update.

Only if the relevant native relationship is confirmed unavailable, use a body convention: child links in a map task list plus a parent link in each child, or a `Blocked by:` line with linked blocker titles. Preserve the same frontier semantics and state the fallback. A transient API failure is not proof that the feature is unavailable.

## Existing local material and domain docs

Existing unpublished `.scratch/` drafts (including copies that remain only in git history) do not become GitHub issues merely because this default changed. On an authorized migration, retain source-to-issue links and designate the GitHub copy as current; keep one authority for subsequent updates.

Research, prototypes, and supporting artifacts may remain in repository files, linked from their issues. Use reachable commit links for published material; local paths are not remotely accessible evidence. Domain vocabulary and ADR layout remain governed by [domain.md](domain.md).

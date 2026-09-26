# Subagent delegation

Read this reference when assigning work to another agent or checking its returned work. A delegation brief gives the receiving agent enough context to act inside a clear boundary and gives the parent agent evidence to check the result.

## Brief

State each item that applies to the task:

- **Goal and deliverable:** name the outcome, output location or question to resolve, and what counts as complete.
- **Source version:** name the repository or source, branch and commit when relevant, and whether the working tree is part of the input. Do not present an investigation starting point as the version containing new work.
- **Available inputs:** list the files, issue, evidence, and decisions the receiver can read. Include essential excerpts or links when needed. Say whether the receiver inherits prior history or starts isolated, then identify the relevant inherited context. The parent's access to material does not mean the receiver has it.
- **Allowed scope:** identify files or areas the receiver owns, whether they may edit, and actions that remain out of scope. State any required coordination where work may overlap.
- **Autonomy:** name decisions the receiver can make and which decisions must return to the parent. State limits on commands, external writes, and contact with other people.
- **Completion evidence:** request changed paths, a concise account of the result, commands or observations with their actual outcomes, and any unresolved or unverified items.
- **If blocked:** ask for the exact blocker, what was checked, and the smallest decision or access needed. Independent work can continue when it does not depend on the blocker.
- **Return check:** require the receiver to identify the artifact and evidence, not just say "done". The parent reads the returned material and checks its source, scope, result, and remaining work.

## Reusable brief

```text
Goal:
Deliverable and completion condition:
Source repository, version, and working-tree state:
Inputs the receiver can access:
Context inherited or intentionally isolated:
Allowed files and actions:
Decisions the receiver may make:
Decisions or actions to return for approval:
Evidence to return:
If blocked:
Return check:
```

Adapt the fields to the task. Keep the brief short where a field does not affect the receiver's result or authority.

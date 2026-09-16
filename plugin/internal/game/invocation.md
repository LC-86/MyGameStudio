# Invocation contract

This is the unique routing contract for MyGameStudio public skills. Game-Producer follows it; later tickets may extend professional behavior, not this discovery rule.

User-initiated invocation, agent on-demand invocation, and material reading are different actions. Reading materials does not start a new discussion or production.

## User-only Matt skills

These skills start only when the developer chooses them. Game-Producer must not auto-invoke them; it may only name them as a recommendation for the developer to run (for example, recommending `to-tickets` and `implement` when a playable feature is ready for engineering).

The complete user-only list is kept once in this file, under `Must not auto-invoke` below. Reading that list as the user-only set is intentional: the two headings describe the same set from the routing side and the enforcement side.

## Must not auto-invoke

This is the same set as `User-only Matt skills` above; this heading holds the single copy of the list so routing checks have one heading to read:

- ask-matt
- grill-me
- grill-with-docs
- handoff
- implement
- improve-codebase-architecture
- setup-matt-pocock-skills
- teach
- to-questionnaire
- to-spec
- to-tickets
- triage
- wait-what
- wayfinder

## Model-invocable Matt skills

Game-Producer may invoke these inside the current task and existing authorization.

- codebase-design
- code-review
- diagnosing-bugs
- domain-modeling
- grilling
- prototype
- research
- resolving-merge-conflicts
- tdd
- wizard
- writing-for-agents

## Game entries

- game-producer
- game-init
- game-design

Game-Producer may on-demand invoke `game-init` and `game-design`. Status queries stay read-only. Ordinary conversation does not trigger any of these entries.

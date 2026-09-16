# Invocation contract

This is the unique routing contract for MyGameStudio public skills. Game-Producer follows it; later tickets may extend professional behavior, not this discovery rule.

User-initiated invocation, agent on-demand invocation, and material reading are different actions. Reading materials does not start a new discussion or production.

## User-only Matt skills

These start only when the developer chooses them. Game-Producer must not auto-invoke them. It may name them as a recommendation for the developer to run.

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

## Must not auto-invoke

Same set as the user-only Matt skills above. Copied as a dedicated list so routing checks have one heading to read:

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

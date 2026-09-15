---
name: implement
description: "Implement a piece of work based on a spec or set of tickets."
disable-model-invocation: true
---

Implement the work described by the user in the spec or tickets.

Use /tdd where possible, at pre-agreed seams.

Run typechecking regularly, single test files regularly, and the full test suite once at the end.

Once done, use /code-review to review the work.

If commit authorization is present, commit your work to the current branch. If it is not, leave the work uncommitted.


## MyGameStudio stage materials

When working in a MyGameStudio game project, read [stage requirements](../../internal/game/stage-requirements.md) for the current work stage before applying this skill's method. If `docs/mygamestudio/INDEX.md` exists, use it to locate this project's current-stage specs and tasks. Reading those materials does not start production.

For a playable slice after the developer invoked to-tickets, use the packaged seam `records/mgs_records.py`: `plan_playable_delivery` / `apply_playable_delivery` / `record_playable_result`. Default to a minimum loop in the formal project; add an isolated prototype only on explicit request. Record actual version, launch, and check scope on the task. Ordinary work does not use mgs-gate.

# Domain Docs

This repository uses a single-context domain-document layout.

## Before exploring, read these

- `CONTEXT.md` at the repository root.
- Relevant ADRs under `docs/adr/`.

If these files do not exist, proceed silently. The domain-modeling skill creates them only when terms or decisions are actually resolved.

## File structure

```
/
├── CONTEXT.md
├── docs/adr/
│   ├── 0001-example-decision.md
│   └── 0002-example-decision.md
└── src/
```

## Use the glossary's vocabulary

When naming a domain concept, use the term defined in `CONTEXT.md`. If it is absent, reconsider whether the project already uses another term, or record the gap for domain modeling.

## Flag ADR conflicts

If a proposed change contradicts an ADR, surface that explicitly rather than silently overriding it.

# Legacy Reference Strategy

## Purpose

The legacy codebases — **wc2** (4D Sources) and **vue2020** — contain decades of business logic, UI patterns, and domain knowledge accumulated through real-world use. During the conversion to wc3/R25, these are valuable references but also contain noise (obsolete patterns, workarounds, dead code).

This directory captures **extracted knowledge** — business rules, field mappings, workflow logic, and edge cases — so the legacy code can eventually be removed from the workspace without losing institutional knowledge.

## Legacy Sources

| Alias | Path | Technology | Value |
|-------|------|------------|-------|
| **wc2** | `00WebClerk19/Project/Sources/` | 4D language | Business rules, table structures, triggers, calculations |
| **vue2020** | `vue2020/` | Vue 2 + JavaScript | UI patterns, component behavior, API call shapes, user workflows |

## Ground Rules

1. **On-demand reference** — Only consult legacy code when actively building a feature that needs parity or domain clarification
2. **Ask before deep dives** — If a legacy area looks complex or ambiguous, ask the user before investing time
3. **Extract, don't port** — Capture the *intent* and *business rules*, not the implementation details
4. **Document what matters** — Record findings here so they survive after wc2/vue2020 are removed
5. **Flag uncertainty** — Mark items where the legacy behavior is unclear or possibly outdated

## File Organization

```
readmes/legacy/
├── 00-legacy-reference-strategy.md   # This file — approach and ground rules
├── ui-patterns.md                     # Vue2020 component behaviors worth preserving
├── field-mappings.md                  # wc2 field → wc3/R25 field crosswalk
└── {topic}.md                         # Additional topics as discovered
```

## When to Add Entries

- Building a feature that has a wc2/vue2020 equivalent → document what was found useful
- Discovering a business rule that isn't obvious from the wc3 schema alone
- Finding edge cases in legacy code that the new implementation should handle
- Mapping a legacy UI workflow to its R25 equivalent

## Status

- **Active** — Files are being populated during development
- **Post-development** — These files become standalone documentation; wc2/vue2020 are removed from workspace

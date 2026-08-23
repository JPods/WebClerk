# Legacy Reference Strategy

## Purpose

The legacy codebases — **wc2** (4D Sources) and **vue2020** — contain decades of business logic, table structures, triggers, calculations, and domain knowledge accumulated through real-world use. During the conversion to wc3/R25, these are valuable references but also contain noise.

This directory captures **extracted knowledge** — business rules, field mappings, calculation logic, trigger behaviors, and edge cases — so the legacy code can eventually be removed from the workspace without losing institutional knowledge.

## Legacy Sources

| Alias | Path | Technology | Value |
|-------|------|------------|-------|
| **wc2** | `00WebClerk19/Project/Sources/` | 4D language | Business rules, table structures, triggers, stored procedures, calculations |
| **vue2020** | `vue2020/` | Vue 2 + JavaScript | API call patterns, data shapes expected by the frontend |

## Ground Rules

1. **On-demand reference** — Only consult legacy code when actively building a feature that needs parity or domain clarification
2. **Ask before deep dives** — If a legacy area looks complex or ambiguous, ask the user before investing time
3. **Extract, don't port** — Capture the *intent* and *business rules*, not the 4D implementation details
4. **Document what matters** — Record findings here so they survive after wc2/vue2020 are removed
5. **Flag uncertainty** — Mark items where the legacy behavior is unclear or possibly outdated

## File Organization

```
readmes/legacy/
├── 00-legacy-reference-strategy.md   # This file — approach and ground rules
├── business-rules.md                  # Extracted business logic from 4D triggers/methods
├── field-mappings.md                  # wc2 table.field → wc3 model.field crosswalk
├── calculations.md                    # Pricing, tax, inventory, and financial calc rules
└── {topic}.md                         # Additional topics as discovered
```

## When to Add Entries

- Building a feature that has a wc2 equivalent → document the business rules found
- Discovering trigger logic in 4D that needs to become a Django signal, save hook, or service
- Finding calculation formulas (pricing tiers, tax, discounts) that aren't yet in wc3
- Mapping wc2 table/field names to wc3 model/field names for data migration

## Relationship to Existing wc2 References

The wc3 repo already has:
- `readmes/topics/wc2/wc2_schema.json` — full 4D field catalog (157 tables)
- Various field alignment docs in `readmes/`

This `legacy/` directory complements those with **narrative knowledge** — the "why" and "how" behind the schema.

## Status

- **Active** — Files are being populated during development
- **Post-development** — These files become standalone documentation; wc2/vue2020 are removed from workspace

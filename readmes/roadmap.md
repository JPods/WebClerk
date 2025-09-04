# Roadmap & In-Process Tracker

Date: 2025-09-03
Review: 2025-12-15
Status: -- status --
Owner: Bill

This document captures the active implementation sequence for API expansion and contract hardening.

## Active Sequence

1. CI guard (grep-based) – DONE (2025-09-02)
2. Expand `assert_envelope` usage across wcapi tests – IN PROGRESS
3. Define new tables (models + migrations + admin) – PENDING
4. Serializers / views / urls / services stubs – PENDING
5. Targeted envelope-first tests for new endpoints – PENDING
6. Business logic iterations (validation, hooks, concurrency) – PENDING

## Details

See design rationale and sequencing strategy in earlier discussion notes (commit history around 2025-09-02) or open an issue requesting deeper context.

## Progress Log

- 2025-09-02: Roadmap initialized; CI guard implemented and passing.

## Next Short-Term Actions

- Batch convert 2–3 representative wcapi tests to `assert_envelope`.
- Add simple link checker (optional) to CI after consolidation.

## Additional tables may be added later:
## Project Docs

[Google Docs](https://docs.google.com/document/d/1a8ZYgSVpJsa6VhhEPkW5bOreRfY4mZ0tuRk0NHJIFJI/edit?usp=sharing)
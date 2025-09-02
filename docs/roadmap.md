# Roadmap & In-Process Tracker

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


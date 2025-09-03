# Tests

Test suite uses `pytest` + `pytest-django`.

## Running

```bash
pytest -q
```

For a subset:

```bash
pytest tests/test_bom_cycle_and_rollup.py::test_bom_cycle_prevention -q
```

## DB / Migrations

Migrations were squashed (see `MIGRATIONS_SQUASH.md`). A clean test DB is created automatically. If you see duplicate column errors, ensure intermediate product migrations (0002–0006) are the no-op versions.

## Tips

- Use `-k keyword` to filter.
- Add marks sparingly; prefer descriptive test names.
- Keep JSON structure assertions focused (avoid over-specifying dynamic metadata fields).

## Coverage

Coverage reporting can be added later; currently not enforced.

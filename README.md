# WebClerk3

Domain-driven inventory, catalog, and organizational management platform (Django 5.x, Postgres, Pydantic integration).

## Key Apps

- `orgs`: Core organizational model (`OrgBase`) with connections + stats envelopes.
- `products`: Item, Serial, Inventory, BOM, Catalog structures.
- Additional domain apps: accounts, communications, transactions, support, sync.

## Quick Start

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
python manage.py migrate
python create_superuser.py
pytest -q
```

## Migration Baseline

Historical migrations were squashed on 2025-09-03. See `MIGRATIONS_SQUASH.md` for reset instructions.

## Tests

`pytest` with `pytest-django`; JSON envelope responses standardized via custom mixins.

## Contributing

Create focused migrations; avoid editing past migrations unless performing an intentional squash.

## License

Internal / Proprietary.

# webClerk3

<!-- Root README rebuilt from legacy README_s/readme.md and updated to point to `readmes/` directory (2025-09-02). -->

![CI](https://github.com/JPods/webClerk3/actions/workflows/ci.yml/badge.svg)
![Coverage](https://codecov.io/gh/JPods/webClerk3/branch/main/graph/badge.svg)

## Project Docs

Primary in-repo documentation now lives under `readmes/` (formerly `docs/` and `README_s/`). Quick index:

- Management & Operations: `readmes/manage.md`
- Testing & Verification: `readmes/testing.md`
- Upgrade Roadmap: `readmes/upgrade.md`
- Data / Model Map: `readmes/data-map.md`
- Rules & Guidelines: `readmes/rules.md`
- Debug / Env Flags: `readmes/debug.md`

Refer to `readmes/readme.md` for consolidation notes.

## Contributors

- Antor Ahmed
- Riju Karar
- Samir Biswas
- Sanjutka Patra
- CoPilot
- Bill James

## Data Basics

Location: `common/management/commands/`
Data file: `all_tables_export.json`

Export/import data:

```bash
python manage.py demo_data_import_export export
python manage.py demo_data_import_export import
```

## Path Basics

```text
webClerk3/
├── apps/
│   ├── core/
│   ├── communications/
│   └── accounts/
├── common/
├── templates/
├── readmes/
└── webclerk3_api/
```

## Install & First-Time Setup

```bash
python -m venv .
source ./bin/activate
pip install -r requirements.txt
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver
```

See `readmes/manage.md` for advanced commands and `readmes/testing.md` for test strategy.

## Running Tests

```bash
./bin/pytest -q
```

SQLite is used in-memory during pytest unless overridden; Postgres is default elsewhere. Details: `readmes/testing.md`.

## Concurrency & API Envelope

All endpoints emit the unified envelope. See `readmes/envelope.md`. Optimistic concurrency uses `version` + `If-Match` header (details in tests and manage docs).

## Upgrade / Roadmap

Backlog and phased roadmap: `readmes/upgrade.md`.

## License / Notes

Internal project; add license section when ready for external distribution.

---
Documentation migration complete (root README regenerated). Legacy `README_s/` will be removed after confirming no external dependencies.

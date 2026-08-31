<!-- Authoritative reset workflow documentation -->

# Destructive Full Reset and Baseline Rebuild

<!-- TOC START -->

## Table of Contents

- [1. When To Use](#1-when-to-use)
- [2. The Three Commands](#2-the-three-commands)
- [3. Full Reset Workflow](#3-full-reset-workflow)
- [4. What Each Command Does](#4-what-each-command-does)
  - [4.1. reset_migrations](#41-reset_migrations)
  - [4.2. reset_database](#42-reset_database)
  - [4.3. seed_freshstart](#43-seed_freshstart)
- [5. Demo Data](#5-demo-data)
- [6. Dummy Data](#6-dummy-data)
- [7. Superusers](#7-superusers)
- [8. Post-Reset Checklist](#8-post-reset-checklist)
- [9. Troubleshooting](#9-troubleshooting)
- [10. FAQ](#10-faq)

<!-- TOC END -->

Date: 2025-09-03
Review: 2026-08-31
Status: current
Owner: Bill

This guide documents the supported way to perform a destructive local reset of the
development database and re-seed system configuration data. Use it sparingly and
never on shared / staging / production environments.

---

## 1. When To Use

Use a full reset when:

- Migration history has been squashed and you need a clean slate.
- Local schema drift or abandoned experimental migrations cause failures.
- You want a freshly seeded baseline with all system configuration data.
- Tests should run against a pristine baseline state.

Do NOT use:

- To "refresh" production-like data (prefer targeted data loads instead).
- Inside active feature branches just to clear minor local fixtures -- resetting is heavy.

---

## 2. The Three Commands

There is no single unified reset command. The workflow uses three separate management
commands run in sequence:

| Command | What it does |
|---------|-------------|
| `reset_migrations` | Deletes all migration files, drops all tables |
| `reset_database` | Clears all data from tables, resets sequences |
| `seed_freshstart` | Runs all seed commands in order to populate system config |

`reset_migrations` is the nuclear option (drops tables). `reset_database` is lighter
(deletes rows but keeps schema). Choose based on whether your migrations are broken.

---

## 3. Full Reset Workflow

**Option A: Schema is fine, just need fresh data**

```bash
python manage.py reset_database --confirm
python manage.py migrate
python manage.py seed_freshstart
python manage.py mark_superusers
python manage.py seed_demo          # optional -- adds sample commerce data
```

**Option B: Migrations are broken, need full rebuild**

```bash
python manage.py reset_migrations
python manage.py makemigrations
python manage.py migrate
python manage.py seed_freshstart
python manage.py mark_superusers
python manage.py seed_demo          # optional
```

---

## 4. What Each Command Does

### 4.1. reset_migrations

Location: `apps/core/management/commands/reset_migrations.py`

1. Deletes all migration `.py` files (except `__init__.py`) from every app.
2. Drops all tables in the `public` schema (CASCADE).
3. Prints a message to run `makemigrations` and `migrate` next.

No flags. No confirmation prompt. Destructive by design -- local dev only.

```bash
python manage.py reset_migrations
python manage.py makemigrations
python manage.py migrate
```

### 4.2. reset_database

Location: `apps/core/management/commands/reset_database.py`

Clears data from all tables and resets PostgreSQL auto-increment sequences. Does
NOT drop tables or touch migrations.

```bash
python manage.py reset_database --confirm
```

Flags:

| Flag | Purpose |
|------|---------|
| `--confirm` | Required. Command refuses to run without it. |
| `--apps app1 app2` | Reset only specific apps (default: all project apps). |
| `--include-django` | Also reset Django built-in apps (auth, contenttypes, sessions, admin). |

Without `--include-django`, Django's own tables (auth, contenttypes, sessions, admin)
are left intact.

### 4.3. seed_freshstart

Location: `apps/core/management/commands/seed_freshstart.py`

Runs all system seed commands in dependency order. After running, the database has
all Settings, reports, GL accounts, terms, DataBrowser layouts, RBAC roles, search
presets, Alice coaching data, and document templates -- everything a new company
needs before entering their own contacts, items, and transactions.

```bash
python manage.py seed_freshstart
python manage.py seed_freshstart --force   # passes --force to each sub-command
```

**Prerequisite:** Migrations must be applied first (`manage.py migrate`).

The seed sequence (in order):

| Step | Command | App | What it seeds |
|------|---------|-----|--------------|
| 1 | `seed_model_definitions` | core | Model definitions (replaces field_access + schema_map) |
| 2 | `seed_company_settings` | core | Company-level Settings |
| 3 | `seed_rbac_roles` | core | RBAC role definitions |
| 4 | `seed_gl_accounts` | accounts | Chart of accounts |
| 5 | `seed_terms` | accounts | Payment terms |
| 6 | `seed_reports` | core | Report records |
| 7 | `seed_databrowser` | core | DataBrowser layouts |
| 8 | `seed_column_widths` | core | Column width defaults |
| 9 | `seed_search_presets` | core | Saved search presets |
| 10 | `seed_alice_layouts` | core | Alice-specific layouts |
| 11 | `seed_qa_templates` | docs | QA templates |
| 12 | `seed_connections` | core | Agent channels and deploy targets |
| 13 | `seed_coaching` | core | Alice coaching data |
| 14 | `seed_wchq_settings` | core | WC HQ settings |
| 15 | `seed_collaborate_settings` | core | Collaboration settings |
| 16 | `seed_serial_settings` | core | Serial-specific actions/behaviors |
| 17 | `seed_status_guards` | transactions | Transaction status transitions + journalized locks |
| 18 | `seed_receivables_layouts` | accounts | Aged receivables report + customer statement layouts |
| 19 | `seed_gl_defaults` | accounts | GL defaults into items/orgs/payment methods |
| 20 | `seed_wc3_commerce_docs` | core | Commerce documentation |
| 21 | `seed_wc3_operations_docs` | core | Operations documentation |
| 22 | `seed_wc3_system_docs` | core | System documentation |
| 23 | `seed_report_templates` | core | Report templates |
| 24 | `seed_template_reports` | core | Template reports |
| 25 | `seed_print_layouts` | core | Print layouts |
| 26 | `seed_dbsr_explanations` | core | DBSR explanations (must run after other seeds) |
| 27 | `seed_dbsr_document` | core | DBSR health manifest (must run after other seeds) |

Each sub-command is called with `call_command`. If a sub-command fails, the error is
printed and the sequence continues with the next command.

---

## 5. Demo Data

Location: `apps/core/management/commands/seed_demo.py`

Creates curated sample commerce data for training and demonstration. Separate from
`seed_freshstart` -- run it after freshstart if you want sample records.

```bash
python manage.py seed_demo
python manage.py seed_demo --force   # delete existing demo data and re-seed
```

**Prerequisite:** `seed_freshstart` must have run first (GL accounts and terms are required).

What it creates:

- 12 items (bats, balls, gloves, bags, training aids, 1 kit with BOM)
- 5 customers (retail, wholesale, team, online, school)
- 1 vendor (baseball equipment supplier)
- 7 contacts (one per customer + 2 at vendor)

All demo records are tagged `refs.source = "demo-baseline"` for clean removal via
`remove_demo_data`.

---

## 6. Dummy Data

Location: `apps/core/management/commands/populate_dummy_data.py`

Generates random dummy data across all models using Faker. Useful for load testing
or filling sparse tables.

```bash
python manage.py populate_dummy_data
python manage.py populate_dummy_data --count 10
python manage.py populate_dummy_data --apps core products
python manage.py populate_dummy_data --dry-run
python manage.py populate_dummy_data --reset-sequences
```

| Flag | Purpose |
|------|---------|
| `--count N` | Records per model (default: 5) |
| `--apps app1 app2` | Only populate specific apps |
| `--dry-run` | Show what would be done without writing |
| `--reset-sequences` | Reset auto-increment sequences to 1 |

This is not part of the standard reset workflow. Use it when you need volume, not
when you need a clean baseline.

---

## 7. Superusers

Location: `apps/core/management/commands/mark_superusers.py`

Marks contacts with `id=1` and `id=2` as superusers. Sets `is_superuser=True`,
`is_staff=True`, `role='admin'`, and password to `1111pass`.

```bash
python manage.py mark_superusers
```

Run this after `seed_freshstart` or `seed_demo` to ensure you have admin access.
The command marks whatever contacts have id 1 and 2 -- it does not create them.

---

## 8. Post-Reset Checklist

| Step | Command | Notes |
|------|---------|-------|
| Verify migrations | `python manage.py showmigrations` | All should show `[X]`. |
| Run tests | `python -m pytest -q` | Should be green against baseline. |
| Check superusers | `python manage.py mark_superusers` | Confirms id 1 and 2 are admins. |
| Inspect seed data | `python manage.py shell` | Sanity-check Settings, GL accounts. |

---

## 9. Troubleshooting

| Symptom | Likely Cause | Fix |
|---------|--------------|-----|
| `OperationalError: server closed the connection` | Stale DB connection after drop | Re-run the command. |
| `column does not exist` after migrate | Ran migrations with wrong Django version | Drop DB and rerun with correct venv. |
| `psql binary not found` | PostgreSQL client tools missing | Install psql or adjust PATH. |
| Seed command fails with missing model | Migrations not applied | Run `manage.py migrate` first. |
| Superusers not created | No contacts with id 1 or 2 | Run `seed_demo` or create contacts first, then `mark_superusers`. |

---

## 10. FAQ

**Q: Is there a single command that does everything?**
A: No. The workflow is three commands in sequence: `reset_database` (or `reset_migrations`),
then `migrate`, then `seed_freshstart`. This is intentional -- each step is independent
and can be run or skipped based on what you need.

**Q: Can I run only the seeding portion?**
A: Yes. Run `seed_freshstart` alone to re-seed system configuration data without
touching the database structure. Individual seed commands (e.g., `seed_gl_accounts`)
can also be run standalone.

**Q: What about demo/sample data?**
A: `seed_freshstart` only seeds system configuration (Settings, reports, GL, terms,
layouts). For sample commerce data (items, customers, transactions), run `seed_demo`
separately after freshstart.

**Q: How do I remove demo data without a full reset?**
A: `python manage.py remove_demo_data` -- removes all records tagged
`refs.source = "demo-baseline"`.

---

End of reset guide.

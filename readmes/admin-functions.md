# Admin Functions & Utility Scripts

> Consolidated reference for all admin scripts, management commands, and tooling in **webClerk3**.
>
> **95 total** — 12 root scripts, 55 management commands, 16 tools/ scripts, 3 shell scripts, 7 SQL scripts, 2 test runners.

---

## 1. Root-Level Scripts

Standalone Python scripts at the project root, typically run with `python <script>.py` from within the activated venv.

| Script | Purpose |
|--------|---------|
| `fetch_order.py` | Fetches and serializes a specific Order with all lines, prints full JSON. |
| `check_inventory.py` | Inspects inventory state for Item 259 — quantity buckets, pending records, related lines. |
| `check_lines.py` | Inspects recent transaction lines for Item 259 using raw SQL and ORM queries. |
| `check239.py` | Quick debug: Item 239 quantity + pending records. |
| `monitor_pending.py` | Live 2-second polling monitor for pending inventory on Item 259. Run alongside frontend. |
| `compare_lines.py` | Compares `default_quantity()` structure across all transaction types; validates `LineItemService` envelope. |
| `audit_foreign_keys.py` | AST-based static analysis: walks model files to find ForeignKey naming mismatches. |
| `convert_price_tiers.py` | **One-time migration:** converts `Item.price.tiers` to flat price-level keys via raw psycopg2. |
| `test_model_resolver.py` | Test harness for `model_name_resolver` — validates resolve/parse with various inputs. |
| `test_inventory_flow_232.py` | End-to-end inventory flow: Proposal→Order→Invoice→Purchase→Receipt on Item 232. |
| `test_line_save.py` | Simulates saving a PurchaseLine via ORM for Purchase 41 / Item 239. |
| `conftest.py` | Root pytest conftest — sets `DJANGO_SETTINGS_MODULE`. Not runnable standalone. |

---

## 2. Django Management Commands

Run with `python manage.py <command> [options]`.

### 2a. Core (`apps/core/management/commands/`)

| Command | Purpose | Key Params |
|---------|---------|------------|
| `ensure_model_defaults` | Fills missing JSONB default keys on all records (never overwrites). | `--dry-run` `--model` `--verbose` `--batch-size` |
| `sync_model` | Syncs model data between local ↔ remote databases. | `<model>` `--direction to-local\|to-remote` `--dry-run` `--list` |
| `fill_dt_fields` | Populates `dt_*` timestamp fields where missing. | `--dry-run` `--apps` |
| `data_load_json` | Loads seed/demo data from a JSON file into any model. | `<app.model>` `<json_file>` `--drop` |
| `export_data` | Exports all model data to individual JSON files in `webclerk3_data/`. | — |
| `restore_data` | Restores all model data from JSON backup files using `loaddata`. | — |
| `restore_data_smart` | Intelligent restore: handles unknown fields, FK ordering, per-record timeouts. | — |
| `reset_database` | **DESTRUCTIVE:** Clears all tables and resets sequences. | `--confirm` `--apps` `--include-django` |
| `reset_migrations` | **DESTRUCTIVE:** Deletes all migration files and drops all tables. | — |
| `populate_dummy_data` | Uses Faker to populate all models with realistic dummy data. | `--count` `--reset-sequences` `--apps` `--dry-run` |
| `data_rework_trans` | Drops and recreates transactions with proper relationships. | — |
| `generate_ts_types` | Generates TypeScript interfaces from Django models for R25. | `--out` `--model` `--list` |
| `setting_workbench` | Creates field-display settings for all registered models. | — |
| `update_keywords` | Batch-updates `refs.keywords` denormalization. | `--model` `--batch-size` `--limit` `--dry-run` |
| `denormalize_links` | Populates `refs.links` with denormalized related-record snapshots. | `--dry-run` `--model` `--batch-size` |
| `load_bom` | Loads BOM records from `bom_children.json`, matching items by SKU. | `--dry-run` `--clear` |
| `load_qa_settings` | Loads Q&A questions from `qa.json` into Settings. | `--reset` `--dry-run` |
| `load_qa` | Creates Q&A question/counter Setting records with group organization. | `--dry-run` `--clear` |
| `populate_cache` | Populates Redis cache with settings, constants, keywords, access rules. | `--cache-type all\|settings\|...` `--silent` |
| `mark_superusers` | Sets Contact #1 and #2 as superusers (role=admin, password=`1111pass`). | — |
| `align_action_contacts` | Fuzzy-matches Actions to Contacts and backfills `contact_id` FK. | — |
| `contact_communications_maintenance` | Reconciles Contact <-> Email/Phone/Domain/Address FK ownership and two-way refs denormalization (`contact.refs.links.*` and `communication.refs.links.contact` + `communication.refs.keywords`). | `--contact-id` `--limit` `--dry-run` `--allow-reassign-owned` `--no-repair-dangling` `--no-alice` |
| `update_attention` | Updates `attention` field = `name_first` + `name_last` for all contacts. | — |
| `create_layout_status` | Scans R25 for per-model layout files and creates a tracking Setting. | `--reset` `--dry-run` |
| `create_popup_choices` | Normalizes legacy wc2 popup/choice JSON into Setting records. | `--reset` `--dry-run` |
| `refs_build_settings` | Manages Settings for `refs` field templates. | `--list` `--model` |
| `audit_refs_templates` | Audits refs link/keyword template coverage for key models and emits Alice notes for gaps. | `--models` `--no-alice` |
| `draft_fields` | Outputs JSON with field names/example values for a model. | `<app.model>` |
| `test_db` | Database smoke test — verifies Contact/Setting access. | — |
| `tmp_projectidfix` | **One-time:** repairs empty project names and links Actions to Projects. | — |

### 2b. Products (`apps/products/management/commands/`)

| Command | Purpose | Key Params |
|---------|---------|------------|
| `process_pending_inventory` | **Main inventory processor:** stacks + line-item pending records. Daemon mode. | `--limit` `--dry-run` `--daemon` `--interval` `--skip-stacks` `--skip-lines` |
| `process_inventory_deltas` | Processes unprocessed inventory delta Pending records in batches. | `--batch-size` `--dry-run` `--item-id` |
| `process_inventory_adaptive` | Adaptive-delay inventory processor (backs off when idle). | `--daemon` `--base-delay` `--max-delay` `--dry-run` |
| `expire_inventory_reservations` | Releases stale/expired inventory reservations. | `--batch` |
| `reset_item_quantities` | Resets all Item quantity buckets to clean state for testing. | `--on-hand` `--dry-run` `--show` |
| `item_status` | Checks item quantity + pending records for specific items. | `<item_ids>` `--pending` `--all-pending` |
| `inventory_metrics` | Prints inventory & reservation operational metrics as JSON. | `--samples` `--sample-limit` `--pretty` |
| `snapshot_inventory_metrics` | Persists current inventory metrics snapshot to DB. | `--samples` |
| `convert_price_tiers` | Converts `Item.price` from tiers[] to flat price-level keys. | `--dry-run` `--item-id` |
| `populate_item_ida` | Populates `Item.ida` with `Item.sku`. | `--dry-run` `--overwrite` `--batch-size` |
| `seed_sample_bom` | Seeds sample BOM data (baseball equipment kit) for testing. | — |
| `seed_sample_products` | Creates sample vendor/customer, catalog, items, org_items. Idempotent. | — |
| `load_bom_from_json` | Loads BOM from separate `bom_children.json` + `bom_parent.json`. | `--bom` `--parent` |
| `import_bom_tsv` | Imports BOM component rows from a TSV file. | `<path>` `--limit` `--offset` `--dry-run` |
| `import_items_tsv` | Imports items from a TSV file, unmapped columns go to `prefs.import`. | `<path>` + options |
| `materialize_variants` | Materializes Variant rows from Item refs/metadata scaffolding. | — |
| `scan_service_billing` | Audits Service.billing schemas for issues; `--fix` to auto-normalize. | `--fix` |

### 2c. Transactions (`apps/transactions/management/commands/`)

| Command | Purpose | Key Params |
|---------|---------|------------|
| `fix_line_nulls` | Normalizes JSONB on transaction lines: legacy key mapping, null→0, recalc totals. | `--dry-run` `--model` `--line-id` |
| `fix_totals_nulls` | Converts null→0 in `totals` JSONB for all transaction models. | `--dry-run` |
| `backfill_org_links` | Populates `refs.links.customer/vendor/manufacturer` on transactions. | `--commit` `--models` `--batch` |
| `populate_project_contacts` | Populates `project.refs.links.contact[]` for all active projects. | `--dry-run` `--project-id` `--clear-first` |
| `populate_dummy_sales_orders` | Populates sample refs data for Order ID 22. | — |
| `audit_fk_values` | Audits FK fields on transactions for zero/negative values. | — |

### 2d. Orgs (`apps/orgs/management/commands/`)

| Command | Purpose | Key Params |
|---------|---------|------------|
| `migrate_financial_structure` | Migrates org `financial` JSONB to type-keyed structure. | `--dry-run` `--org-id` |
| `fix_null_mixin_values` | Replaces null→0 in org JSONB mixin fields. | `--dry-run` `--org-id` `--field` |
| `populate_org_contacts` | Links Contacts to OrgBase records by name matching. | `--apply` `--clear` |

### 2e. Accounts (`apps/accounts/management/commands/`)

| Command | Purpose | Key Params |
|---------|---------|------------|
| `reconcile_financials` | Nightly financial reconciliation from ledger records. | `--org-id` `--org-type` `--rebuild` `--dry-run` |

### 2f. AI Assistant (`apps/ai_assistant/management/commands/`)

| Command | Purpose | Key Params |
|---------|---------|------------|
| `ai_health` | Checks Ollama connection, model availability, ChromaDB status. | — |
| `generate_context` | Auto-generates context files for Copilot/AI indexing. | `--target models\|fixtures\|imports\|endpoints` |
| `index_docs` | Crawls docs/code and indexes into ChromaDB for RAG retrieval. | `--source readmes` `--reset` `--stats` |

---

## 3. Tools Directory (`tools/`)

### Python Scripts

| Script | Purpose | How to Run |
|--------|---------|------------|
| `inventory_tester.py` | Comprehensive 919-line inventory test tool for Item 240. Subcommands: `baseline`, `status`, `create`, `process_pending`, `log`, `history`, `pending`, `reset`. | `python tools/inventory_tester.py <subcmd>` |
| `sync_local_to_remote.py` | Bulk-copies all local DB tables to remote PostgreSQL. | `python tools/sync_local_to_remote.py` |
| `sync_remote_to_local.py` | Bulk-copies all remote DB tables to local PostgreSQL. | `python tools/sync_remote_to_local.py` |
| `audit_customer_payload.py` | Measures Customer API payload sizes and serialization time. | `python tools/audit_customer_payload.py` |
| `audit_fk_values.py` | Raw SQL audit of transaction FK fields for invalid values. | `python tools/audit_fk_values.py` |
| `backfill_on_p.py` | Backfills `Item.quantity.on_p` from active proposals. | `python manage.py shell < tools/backfill_on_p.py` |
| `check_all_sequences.py` | Lists all transaction tables and their PK sequences. | `python tools/check_all_sequences.py` |
| `check_sequences.py` | Checks PK sequence independence across transaction models. | `python tools/check_sequences.py` |
| `check_item_quantities.py` | Quick quantity check for Items 248–250. | `python manage.py shell < tools/check_item_quantities.py` |
| `check_proposal_pending.py` | Inspects proposals, lines, item quantities, PP-type pending records. | `python manage.py shell < tools/check_proposal_pending.py` |
| `fix_ida_values.py` | Fixes all `ida` values to `"ida-{id}"` format via raw SQL. | `python tools/fix_ida_values.py` |
| `import_actions_from_csv.py` | Imports CSV into Action model with kanban/difficulty mapping. | `python tools/import_actions_from_csv.py` |
| `verify_cleanup.py` | Verifies remote DB cleanup: NULL UUIDs, orphaned FKs, integrity. | `python tools/verify_cleanup.py` |
| `test_invoice_trace.py` | Creates traced Invoice for Items 249–251, validates pending. | `python manage.py shell < tools/test_invoice_trace.py` |
| `test_proposal_trace.py` | Creates traced Proposal for Items 249–251, validates `on_p` pending. | `python manage.py shell < tools/test_proposal_trace.py` |
| `test_wo_trace.py` | Creates traced Work Order for Items 249–251, validates `on_wo` pending. | `python manage.py shell < tools/test_wo_trace.py` |

### Shell Scripts

| Script | Purpose | How to Run |
|--------|---------|------------|
| `setup_ai.sh` | One-command AI assistant setup: Ollama, ChromaDB, doc indexing, git hooks. | `./tools/setup_ai.sh [--check\|--index\|--hooks]` |
| `switch-dataset.sh` | Switches between remote/local DB, restarts Django + Vite servers. | `./tools/switch-dataset.sh [remote\|local]` |
| `check_renamed_models.sh` | Guard against reintroduction of legacy model names in both repos. | `./tools/check_renamed_models.sh` |

### SQL Scripts

| Script | Purpose |
|--------|---------|
| `fix_orphan_actions.sql` | Remaps orphaned `actions.contact_id` to contact 1. |
| `orphan_check.sql` | Queries sample orphaned actions by non-existent contact IDs. |
| `verify_cleanup.sql` | Comprehensive remote DB verification: NULL UUIDs, orphaned FKs. |
| `remote_audit.sql` | Duplicate UUIDs, orphaned FKs, data consistency on remote DB. |
| `remote_fk_check.sql` | Orphaned FK references across contacts→orgs, transactions→orgs. |
| `populate_uuids.sql` | Populates NULL UUIDs on all affected tables using `gen_random_uuid()`. |
| `populate_uuids_simple.sql` | Simpler variant of UUID population. |

---

## 4. Test Runners (`tests/`)

| Script | Purpose |
|--------|---------|
| `tests/run_universal_tests.py` | Runs Universal API tests against all registered tables. |
| `tests/run_view_edit_tests.py` | Runs view/edit permission tests. |

---

## Quick-Reference: Common Workflows

### Fresh database setup
```bash
python manage.py reset_database --confirm
python manage.py migrate
python manage.py populate_dummy_data --count 20
python manage.py ensure_model_defaults
python manage.py populate_cache --cache-type all
python manage.py mark_superusers
```

### Sync data between environments
```bash
# Pull remote → local
python manage.py sync_model --direction to-local --list   # see available models
python manage.py sync_model contact --direction to-local
# Or bulk sync
python tools/sync_remote_to_local.py
```

### Inventory operations
```bash
python manage.py reset_item_quantities --on-hand 100      # reset for testing
python manage.py process_pending_inventory --daemon        # run processor
python manage.py item_status 240 259 --pending             # check specific items
python manage.py inventory_metrics --pretty                # operational metrics
```

### Data integrity checks
```bash
python manage.py ensure_model_defaults --dry-run
python manage.py test_db
python audit_foreign_keys.py
python tools/verify_cleanup.py
```

### Load BOM data
```bash
python manage.py load_bom --dry-run        # preview
python manage.py load_bom                  # load from bom_children.json
python manage.py seed_sample_bom           # or seed test data
```

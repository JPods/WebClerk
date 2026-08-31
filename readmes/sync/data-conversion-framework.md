# Data Conversion Framework — Alice's Workbench

**Established:** 2026-08-04

## The Problem

Every data supplier has different column names, formats, encodings, delimiters,
and assumptions. "Description" might be a product name or a comment. "Price" might
be retail, wholesale, or cost. "Qty" might be on-hand, available, or on-order.
UOM is never consistent. Dates come in every format imaginable.

This is not a one-pass problem. Real data conversion takes multiple passes:
1. Detect structure (what kind of file, what columns, what delimiter)
2. Map columns to WC3 schema (Claude helps — but human review required)
3. Convert values (normalize UOM, parse decimals, map GL accounts)
4. Find oddities (duplicate SKUs, missing prices, bad dates, encoding issues)
5. Resolve oddities (auto-fix what's clear, flag what needs human judgment)
6. Repeat passes 3-5 until clean
7. Assemble bundle and send to WC3

The noise of all that work stays **outside** WC3 in Alice's conversion database.

## Architecture

```
┌─────────────────────────────────────────────────────┐
│                  alice_conversion                    │
│              (separate PostgreSQL DB)                 │
│                                                       │
│  ConversionProject ──┬── SourceFile ── ColumnMap     │
│                      ├── Oddity                       │
│                      ├── StagingRow                   │
│                      └── PassLog                      │
└──────────────────────────┬──────────────────────────┘
                           │ bundle JSON
                           ▼
┌─────────────────────────────────────────────────────┐
│                  commerce_expert                      │
│                    (WC3 database)                      │
│                                                       │
│  POST /wcapi/sync/receive/                            │
│  Connection ── Bundle (audit trail)                   │
│  Item, BillOfMaterial, OrgBase, GlAccount ...         │
└─────────────────────────────────────────────────────┘
```

Two databases on the same PostgreSQL server. Django's database router ensures
conversion models never touch commerce_expert and vice versa.

## The Models

### ConversionProject

One project per conversion effort. A supplier, a data set, a goal.

| Field | Purpose |
|-------|---------|
| `name` | Human name for this conversion |
| `supplier_name` | Who the data came from |
| `status` | active, complete, abandoned |
| `connection_id` | Which WC3 Connection receives the final bundle |
| `pass_count` | How many passes Alice has run |
| `stats` | Summary stats (columns mapped, oddities found, etc.) |

### SourceFile

Each file the user gives Alice to convert.

| Field | Purpose |
|-------|---------|
| `filename` | Original file path |
| `file_type` | csv, tsv, xlsx, json |
| `file_hash` | SHA-256 for deduplication |
| `raw_headers` | Column names as they appear in the file |
| `row_count` | Total rows |
| `sample_rows` | First 20 rows (JSON) — sent to Claude for mapping |
| `encoding` | Detected encoding (utf-8, latin-1, etc.) |
| `delimiter` | Detected delimiter (comma, tab, pipe) |

### ColumnMap

How Alice mapped each source column to a WC3 field. One row per column.

| Field | Purpose |
|-------|---------|
| `source_column` | Column name from the file |
| `target_model` | WC3 model: Item, BillOfMaterial, OrgBase |
| `target_field` | WC3 field or JSON path: `price.base`, `gls.inventory` |
| `confidence` | Claude's confidence 0.0-1.0 |
| `transform` | What to apply: `normalize_uom`, `parse_decimal`, `parse_bool` |
| `status` | proposed, confirmed, rejected, unmapped |
| `reasoning` | Why Claude chose this mapping |
| `sample_values` | Example values from the source for review |
| `pass_number` | Which pass created/refined this mapping |

### Oddity

Every data quality problem Alice finds. This is the core documentation table.

| Field | Purpose |
|-------|---------|
| `severity` | info, warning, error, pattern |
| `category` | duplicate_sku, ambiguous_uom, missing_price, bad_date, gl_unmapped, etc. |
| `description` | What's wrong |
| `source_column` | Which column |
| `source_row` | Which row |
| `source_value` | The actual problematic value |
| `affected_count` | How many rows have this same oddity (for patterns) |
| `resolution` | pending, auto_fixed, user_fixed, skipped, escalated |
| `resolution_detail` | What was done about it |

### StagingRow

Converted data waiting for bundle assembly. Each row is in WC3 schema format.

| Field | Purpose |
|-------|---------|
| `source_row_number` | Which row in the source file |
| `target_model` | Item, BillOfMaterial, etc. |
| `data` | The converted record as JSON, matching WC3 schema |
| `status` | staged, bundled, rejected, needs_review |
| `oddity_ids` | Which oddities affect this row |

### PassLog

Record of each conversion pass. Tracks progress and Claude API usage.

| Field | Purpose |
|-------|---------|
| `pass_number` | Sequential pass number |
| `focus` | What this pass worked on |
| `rows_processed/staged/rejected` | Counts |
| `oddities_found/resolved` | Counts |
| `llm_model/calls/tokens` | Claude API usage tracking |
| `duration_seconds` | How long the pass took |

## The Pipeline

### Pass 1: Column Mapping

```bash
python manage.py convert_data start "Acme Inventory" /path/to/items.csv --supplier "Acme Corp"
```

Alice reads the file, detects format, extracts headers and sample rows, then sends
them to Claude Haiku asking: "Map these columns to WC3 Item schema."

Claude returns a mapping with confidence scores and reasoning. Alice records every
mapping as a ColumnMap row with status `proposed`.

### Review Mappings

```bash
python manage.py convert_data review <project_id>
```

Shows all mappings with confidence bars, reasoning, and sample values. The user
confirms or rejects each mapping.

### Confirm Mappings

```bash
# Auto-confirm everything Claude is >= 80% confident about
python manage.py convert_data confirm <project_id> --auto

# Or confirm all proposed mappings
python manage.py convert_data confirm <project_id> --all
```

### Pass 2+: Convert Rows

```bash
python manage.py convert_data run <project_id>
```

Alice applies confirmed mappings to every row. Each value goes through its transform
(parse_decimal, normalize_uom, etc.). Problems become Oddity records. Clean rows
become StagingRows in WC3 schema format.

Run this as many times as needed. Each pass refines the data.

### Review Oddities

```bash
python manage.py convert_data oddities <project_id>
python manage.py convert_data oddities <project_id> --severity error
```

Shows oddities grouped by category with counts. Fix the source data or tell Alice
how to resolve, then run another pass.

### Assemble Bundle

```bash
python manage.py convert_data bundle <project_id> --output /path/to/bundle.json
```

Reads all staged rows and produces a JSON bundle matching WC3 schema. This bundle
goes to `/wcapi/sync/receive/` via Alice's Connection key.

### List Projects

```bash
python manage.py convert_data list
```

## Claude API Integration

Alice uses **Claude Haiku 4.5** for column mapping — fast, cheap, and accurate
enough for structured data tasks. Complex ambiguities escalate to Sonnet.

API key lives in `~/Allie/config/allie_api_keys.json` under `keys.anthropic`.
All calls are tagged with `metadata.user_id = "alice"` for usage tracking.

Token usage is recorded in the PassLog table — every call, every token count,
every elapsed time. Alice knows what she costs.

## The Oddity Table as Institutional Knowledge

The Oddity table is not just a bug list. It's Alice's institutional knowledge
about a supplier's data habits:

- "Acme always puts cost in the price column"
- "This supplier uses 'CS' for case but WC3 expects 'CA'"
- "These GL accounts don't match our chart — here's the map"
- "Every 50th row has a duplicate SKU from a copy-paste error"

When the same supplier sends data next quarter, Alice already knows their patterns.
The conversion database persists. The oddities are lessons.

## Supplier WC3 Copy

Data suppliers can receive a free copy of WC3 with the conversion app. They run
it against their own data, fix their own oddities, and produce a valid bundle.

The bundle format is documented. The schema is published. The conversion tool is
the bridge between their format and ours. They can iterate on their end, at their
speed, without our involvement.

When their bundle arrives at `/sync/receive/`, it's clean. Their oddities were
resolved on their workbench, not ours.

## Files

| File | What it does |
|------|-------------|
| `apps/conversion/models.py` | All 6 models |
| `apps/conversion/services/converter.py` | Pipeline: read file, map columns, convert rows, assemble bundle |
| `apps/conversion/management/commands/convert_data.py` | CLI: start, review, confirm, run, oddities, bundle, list |
| `apps/conversion/db_router.py` | Routes all conversion models to alice_conversion DB |
| `apps/conversion/admin.py` | Django admin for all models |
| `apps/conversion/apps.py` | Django app config |

## Related

- [Bundle Import](bundle-import.md) — how bundles enter WC3
- [Data Library Ecosystem](data-library-ecosystem.md) — the broader data supply chain
- [Dynamic Catalogs](dynamic-catalogs.md) — upstream library service

# Data Conversion Pipeline — External File to Clean Bundle
**Created:** 2026-08-09
**Owner:** Alice (conversion workbench, column mapping, oddity resolution, bundle assembly)

---

## What It Does

External data arrives in every format imaginable — CSV, XLSX, EDI, PDF, contact exports. Alice and Claude convert it using per-source lessons stored on the Connection.config record. DynamicCatalogs enriches with upstream product data and landed cost. Data quality services clean addresses, phones, emails, and duplicates. Athena reviews for security. A human signs off. The result is a clean, schema-structured bundle.json that enters WC3 through `POST /wcapi/sync/receive/`.

All transformation happens **outside** WC3. The noise never enters the commerce database. WC3's job is to record a bundle that's already correct.

Flowchart: `readmes/flowcharts/wc3-data-conversion-pipeline.dot`
```bash
dot -Tpdf readmes/flowcharts/wc3-data-conversion-pipeline.dot -o readmes/flowcharts/wc3-data-conversion-pipeline.pdf
```

---

## The End-to-End Flow

```
External file (CSV, XLSX, EDI, PDF, contacts)
    │
    ▼
Connection.config — per-source lessons, column maps, skip rules, transforms
    │
    ▼
Alice Conversion Workbench (alice_conversion DB — separate from WC3)
    │  Pass 1: Detect format, encoding, delimiters, headers
    │  Pass 1: Claude Haiku maps columns → WC3 schema (confidence scores)
    │  Review: Human confirms/rejects mappings (auto-confirm ≥ 80%)
    │  Pass 2+: Convert rows, normalize values, resolve oddities
    │  Repeat until clean
    │
    ├──── DynamicCatalogs (WCHQ) ────┐
    │     SKU validation              │
    │     Distribution agreements     │
    │     Landed cost calculation     │
    │     Category + spec enrichment  │
    │                                 │
    ├──── Data Quality Services ──────┤
    │     Address verification        │
    │     Phone normalization         │
    │     Email scrubbing             │
    │     Dedup scan                  │
    │     Tax code lookup             │
    │                                 │
    ▼                                 │
Staging rows (WC3 schema format) ◄────┘
    │
    ▼
Bundle assembly — clean JSON, natural keys, UTC datetimes
    │
    ▼
Athena review — sign bundle, check for hidden harms
    │
    ▼
Human sign-off — responsible person, timestamp, findings reviewed
    │
    ▼
POST /wcapi/sync/receive/ — Connection key auth, idempotent, encrypted, audited
    │
    ▼
WC3: Bundle record (audit trail) + data applied to models
    │
    ▼
Complication flags → feed back to DynamicCatalogs + Alice lessons
```

---

## Connection.config — Per-Source Intelligence

Every data source gets a Connection record. The Connection.config stores everything Alice has learned about that source:

```json
{
    "key": "<shared-secret>",
    "endpoint": "...",
    "import_config": {
        "column_map": {
            "Part Number": "sku",
            "Description": "name",
            "List Price": "price.base",
            "Dealer Cost": "cost.standard",
            "Qty Available": "quantity.on_hand",
            "Unit": "uom"
        },
        "lessons": [
            {"dt": 1723200000000, "lesson": "Acme always puts cost in the price column — swap columns"},
            {"dt": 1723200000000, "lesson": "This supplier uses 'CS' for case but WC3 expects 'CA'"},
            {"dt": 1723200000000, "lesson": "Every 50th row has a duplicate SKU from copy-paste error — dedup on SKU"}
        ],
        "user_instructions": [
            "Skip rows where price is 0.00 — these are discontinued",
            "GL account 5100 maps to our 5100-01"
        ],
        "skip_rules": [
            {"column": "price.base", "condition": "eq", "value": 0, "reason": "discontinued"},
            {"column": "sku", "condition": "blank", "reason": "header row repeated"}
        ],
        "transforms": {
            "uom": "normalize_uom",
            "price.base": "parse_decimal",
            "quantity.on_hand": "parse_int",
            "description": "strip_html"
        }
    }
}
```

**Key principle:** The Connection.config is Alice's institutional knowledge about this source. When the same supplier sends data next quarter, Alice already knows their column names, their quirks, and their data quality patterns. The conversion gets faster and more accurate with each iteration.

---

## Alice Conversion Workbench

The conversion workbench runs in a **separate database** (`alice_conversion`) from WC3 (`commerce_expert`). The noise of parsing, mapping, and oddity resolution never touches commerce data.

### Models

| Model | What it holds |
|-------|-------------|
| `ConversionProject` | One project per conversion effort — supplier, status, connection_id, pass count |
| `SourceFile` | Each file: filename, type, hash, raw headers, sample rows, encoding, delimiter |
| `ColumnMap` | Per-column mapping: source → target model.field, confidence, transform, status |
| `Oddity` | Every data quality problem: category, severity, source value, resolution |
| `StagingRow` | Converted records in WC3 schema format, ready for bundling |
| `PassLog` | Record of each pass: focus, counts, LLM token usage, duration |

### The Multi-Pass Pipeline

**Pass 1 — Detect and Map:**
1. Alice reads the file with `chardet` (encoding) and `pandas` (structure)
2. Extracts headers and 20 sample rows
3. Sends to Claude Haiku: "Map these columns to WC3 Item schema"
4. Claude returns mappings with confidence scores (0.0–1.0) and reasoning
5. Each mapping recorded as a ColumnMap with status `proposed`
6. Prior Connection.config.import_config.column_map used as starting point

**Review:**
- Human reviews proposed mappings
- Auto-confirm ≥ 80% confidence (configurable)
- Reject and remap where Claude was wrong
- Add user instructions ("skip rows where price is 0")

**Pass 2+ — Convert:**
1. Apply confirmed mappings to every row
2. Run transforms: `normalize_uom`, `parse_decimal`, `parse_bool`, `strip_html`
3. Problems become Oddity records (with category, severity, affected count)
4. Clean rows become StagingRows in WC3 schema format
5. Repeat passes until oddities are resolved

### The Oddity Table as Institutional Knowledge

Oddities are not just a bug list — they are Alice's memory of what this supplier's data looks like:

- "Acme always puts cost in the price column"
- "This supplier uses 'CS' for case but WC3 expects 'CA'"
- "These GL accounts don't match our chart — here's the map"
- "Every 50th row has a duplicate SKU from a copy-paste error"

When oddities are resolved, the resolutions flow back to Connection.config as lessons and skip_rules. Next import is smarter.

---

## WCHQ DynamicCatalogs — Upstream Enrichment

DynamicCatalogs sits between suppliers and retailers. During conversion, Alice can query DynamicCatalogs to:

| Service | What it provides |
|---------|-----------------|
| SKU validation | Confirm SKU exists in manufacturer's catalog |
| Distribution agreement | Apply this retailer's specific terms with this distributor |
| Landed cost | Calculate actual cost: dist cost + freight zone + duty/tariff + volume tier |
| Category mapping | Map supplier categories to WC3 category tree |
| Spec enrichment | Fill in missing specifications from manufacturer data |
| UOM standardization | Resolve ambiguous UOM using manufacturer's canonical UOM |
| Discontinuation check | Flag SKUs the manufacturer has discontinued |

DynamicCatalogs has write access only to cost and catalog models in WC3 — scoped, auditable, revocable. It never touches contacts, transactions, or proprietary retailer data.

**Usufruct rule:** DynamicCatalogs may profit from processing the data. It may not retain, aggregate, resell, or weaponize it.

---

## Data Quality Services

Applied to staging rows before bundle assembly:

| Service | Tool | What it does |
|---------|------|-------------|
| Address verification | SmartyStreets / USPS | Standardize and verify mailing addresses |
| Phone normalization | `phonenumbers` lib | Strip to digits + country code, format per nation |
| Email scrubbing | ZeroBounce | Detect garbled emails, OCR errors, invalid domains |
| Dedup scan | `thefuzz` | Levenshtein distance scoring for potential duplicates |
| Tax code lookup | `tax_service` | Map items to correct tax jurisdiction codes |

Three-tier processing: Tier 1 algorithms run silently. Tier 2 (Alice LLM) handles what Tier 1 can't resolve. Tier 3 (general LLM) only runs when flagged. Every transformation preserves the original in `config.original`.

---

## Athena Security Review

Before a bundle enters WC3, Athena inspects it for hidden harms:

- Malicious formulas (Excel formula injection)
- SQL injection in field values
- PII in unexpected columns
- Data that contradicts existing records
- Suspicious patterns (all prices $0.01, all quantities 999999)
- Embedded scripts
- Encoding attacks (Unicode homoglyphs, null bytes)

Athena signs cleared bundles. Flagged bundles return to Alice for investigation. Athena's findings are recorded on the bundle header.

---

## Bundle Assembly and Delivery

### Bundle Format

```json
{
    "idempotency_key": "uuid-string",
    "sequence": 1,
    "payload": {
        "items": [
            {
                "sku": "WIDGET-100",
                "name": "Standard Widget",
                "uom": "EA",
                "price": {"base": 12.50, "msrp": 15.00, "currency": "USD"},
                "cost": {"standard": 6.00, "landed": 6.50},
                "quantity": {"on_hand": 500, "available": 470},
                "gls": {"inventory": "1300", "cogs": "5000", "revenue": "4000"},
                "tax_code": {"code": "TX-STD", "category": "tangible"}
            }
        ]
    }
}
```

**Rules:**
1. Field names match WC3 model fields exactly — no translation at receive time
2. JSON sub-documents follow schemas in `apps/products/models/item.py`
3. SKU matching is case-insensitive — existing items update, new items create
4. Foreign keys use natural keys (SKU, ida) not database IDs
5. All datetimes UTC ISO-8601 with Z suffix (Axiom 14)
6. Idempotent — duplicate `idempotency_key` returns original `bundle_id`

### Delivery

```
POST /wcapi/sync/receive/
X-Sync-Key: <connection shared secret>
Content-Type: application/json
Body: bundle JSON (optionally Fernet encrypted)
```

Response: `{"ack": true, "bundle_id": "42", "dt_received": 1722816000000}`

### What Happens in WC3

1. Connection key validated
2. Bundle record created (full payload preserved — never deleted)
3. Payload applied: SKU match → update, new → create
4. Complication flags generated for mismatches
5. Complications feed back to DynamicCatalogs and Alice

---

## The Feedback Loop

```
WC3 detects complication (price mismatch, discontinued SKU, wrong UOM)
    │
    ├──→ DynamicCatalogs: investigate, update source data or agreement terms
    │
    └──→ Alice: add to Oddity table for this supplier, update Connection.config lessons
```

Complications are not bugs — they are the signal that data quality is improving. A supplier whose data produces fewer complications per import cycle is producing better data. Alice tracks this trend per Connection.

---

## Supplier WC3 Copy

Data suppliers can receive a free copy of WC3 with the conversion app. They run it against their own data, fix their own oddities, and produce a valid bundle on their end. The bundle format is published. Their oddities are resolved on their workbench, not ours.

This is the data supply chain operating at scale: each participant owns their own data quality. Alice helps. DynamicCatalogs normalizes. WC3 records. Nobody extracts.

---

## Two Paths Into WC3

| Path | When | How |
|------|------|-----|
| **wcapi CRUD** | Individual records — one item, one contact, one order | Standard API calls, user or agent authenticated |
| **Bundle** | Bulk — catalog loads, inventory updates, price sheets, BOM imports | `POST /sync/receive/`, machine-to-machine, Connection key |

There is no third path. No management commands. No admin CSV upload.

---

## Alice Dashboard Integration

The Import Data tab on Alice's dashboard (`/alice-dashboard`) provides the UI for this pipeline:
1. Provide data source (file path)
2. Alice analyzes → preview column mappings with confidence scores
3. Confirm mappings → Athena security review
4. Sign off → bundle enters WC3 via sync

---

## Files

| File | What it does |
|------|-----------|
| `apps/conversion/models.py` | All 6 conversion models (ConversionProject, SourceFile, ColumnMap, Oddity, StagingRow, PassLog) |
| `apps/conversion/services/converter.py` | Pipeline: read file, map columns, convert rows, assemble bundle |
| `apps/conversion/management/commands/convert_data.py` | CLI: start, review, confirm, run, oddities, bundle, list |
| `apps/conversion/db_router.py` | Routes conversion models to alice_conversion DB |
| `apps/sync/views/bundle_sync.py` | `BundleReceiveView` — inbound endpoint |
| `apps/sync/models/connection.py` | Connection — who can send/receive |
| `apps/sync/models/bundle.py` | Bundle — audit record per exchange |
| `apps/sync/services/bundle_crypto.py` | Fernet encrypt/decrypt for payloads |
| `readmes/flowcharts/wc3-data-conversion-pipeline.dot` | Visual pipeline diagram |

## Related WC3 Readmes (technical detail)

| Readme | What it covers |
|--------|---------------|
| `topics/architecture/data-conversion-framework.md` | Alice's conversion workbench — models, CLI, multi-pass |
| `topics/architecture/bundle-import.md` | Bundle format, sync/receive endpoint, Connection auth |
| `topics/architecture/dynamic-catalogs.md` | DynamicCatalogs — distribution agreements, normalization, usufruct |
| `topics/architecture/data-library-ecosystem.md` | Three data types, library model, retailer feedback loop |
| `topics/ai/alice-data-quality.md` | Three-tier data quality (algorithms → Alice LLM → general LLM) |
| `topics/ai/alice-data-polishing.md` | Alice's data polishing patterns |

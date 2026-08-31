# Bundle Import — Loading Data into WC3

**Established:** 2026-08-04

## The Rule

All bulk data enters WC3 through bundles. No CSV parsers, no TSV importers, no
admin upload buttons. Individual records come through wcapi (normal CRUD). Bulk is
always and only a bundle.

The noise — parsing messy files, mapping vendor column names, normalizing UOM,
guessing GL accounts, reconciling SKUs — stays **outside** WC3. Alice, Claude, and
DynamicCatalogs do that work. What arrives at WC3's door is a clean JSON document
that matches WC3 schema exactly.

## Why

Import code inside WC3 is technical debt disguised as a feature. Every vendor file
has different columns, encodings, delimiters, and assumptions. That parsing logic
grows without bound, breaks silently, and buries the real schema under layers of
translation. The import is not the hard part — the transformation is. And the
transformation belongs to Alice's domain, not WC3's.

WC3's job is to **record** a bundle that's already correct.

## Architecture

```
User has a file (CSV, TSV, Excel, PDF, whatever)
    │
    ▼
Alice + Claude + DynamicCatalogs
    │  - Parse the source file
    │  - Normalize fields to WC3 schema
    │  - Validate referential integrity
    │  - Resolve SKU conflicts
    │  - Map GL accounts, UOM, tax codes
    │  - Produce clean JSON payload
    │
    ▼
Athena signs the bundle
    │
    ▼
Alice's Connection record authorizes entry
    │
    ▼
POST /wcapi/sync/receive/          ← WC3 boundary
    │  X-Sync-Key: <connection key>
    │  Body: clean JSON bundle
    │
    ▼
Bundle record created (audit trail)
    │
    ▼
Data applied to WC3 models
```

## Two Paths Into WC3

| Path | When | How |
|------|------|-----|
| **wcapi CRUD** | Individual records — one item, one contact, one order | Standard API calls, user or agent authenticated |
| **Bundle** | Bulk — catalog loads, inventory updates, price sheets, BOM imports | `POST /sync/receive/`, machine-to-machine, key authenticated |

There is no third path. No management commands. No admin CSV upload.

## The Bundle Endpoint

```
POST /wcapi/sync/receive/
```

**Authentication:** `X-Sync-Key` header. Matched against the Connection's `config.key`.
No Django user auth — this is machine-to-machine.

**Request body:**
```json
{
  "idempotency_key": "uuid-string",
  "sequence": 1,
  "payload": { ... },
  "echo": "optional-round-trip-string",
  "test": false
}
```

Or with encryption:
```json
{
  "idempotency_key": "uuid-string",
  "sequence": 1,
  "encrypted_payload": {
    "encrypted": "<base64-fernet-token>",
    "inline": true
  }
}
```

**Response:**
```json
{
  "ack": true,
  "echo": "...",
  "dt_received": 1722816000000,
  "bundle_id": "42",
  "test": false
}
```

**Features:**
- **Idempotent** — duplicate `idempotency_key` returns the original `bundle_id`
- **Ordered** — `sequence` field for processing in order
- **Encrypted** — Fernet (AES-128-CBC + HMAC-SHA256) using connection's shared key
- **Large payloads** — payloads > 64KB encrypt to file with separate file key
- **Audited** — every bundle creates a Bundle record with full payload and response

## Bundle Payload Format

The payload is a JSON document. Each key is a WC3 model name. Each value is a list
of records matching that model's schema.

```json
{
  "items": [
    {
      "sku": "WIDGET-100",
      "name": "Standard Widget",
      "kind": "physical",
      "uom": "EA",
      "base_uom": "EA",
      "description": "Standard widget, zinc plated",
      "price": {
        "base": 12.50,
        "msrp": 15.00,
        "retail": 12.50,
        "wholesale": 11.25,
        "currency": "USD"
      },
      "cost": {
        "standard": 6.00,
        "avg": 5.85,
        "last": 6.10,
        "landed": 6.50
      },
      "quantity": {
        "on_hand": 500,
        "allocated": 30,
        "available": 470,
        "on_order": 200
      },
      "gls": {
        "inventory": "1300",
        "cost": "5100",
        "cogs": "5000",
        "revenue": "4000"
      },
      "tax_code": {
        "code": "TX-STD",
        "category": "tangible"
      },
      "flags": {
        "back_order_allowed": true,
        "discountable": true,
        "serialized": false
      }
    }
  ],
  "bill_of_materials": [
    {
      "parent_sku": "WIDGET-ASM",
      "child_sku": "WIDGET-100",
      "quantity": 4,
      "sequence": 1
    }
  ]
}
```

**Rules for the payload:**

1. Field names match WC3 model fields exactly — no translation at receive time
2. JSON sub-documents (price, cost, quantity, flags, gls, tax_code) follow the
   schemas defined in `apps/products/models/item.py`
3. SKU matching is case-insensitive — existing items update, new items create
4. Foreign keys use natural keys (SKU, ida) not database IDs
5. All datetimes are UTC ISO-8601 with Z suffix (Axiom 14)

## The Connection Record

Alice controls who can send bundles. Each sender needs a Connection record:

```
Connection:
  name:    "Acme Supplier Feed"
  type:    "api"
  status:  "active"
  purpose: "ingest"
  config:  {"key": "<shared-secret>", "endpoint": "..."}
```

**Connection fields that matter:**
- `config.key` — shared secret, matched against X-Sync-Key header
- `status` — must be "active" to accept bundles
- `purpose` — "ingest" for incoming data
- `maps` — optional field mapping rules (Alice applies these outside WC3)
- `rules` — optional validation rules
- `conflicts` — conflict resolution policy

Alice creates and manages Connection records. She controls who has keys, when
connections are active, and when they're retired.

## What Alice Does Outside WC3

This is Alice's domain — the transformation work:

1. **Receive** the user's file (any format)
2. **Parse** it — CSV, TSV, Excel, PDF, whatever the source
3. **Map columns** to WC3 field names using the Connection's map rules
4. **Normalize** values — UOM (`normalize_uom`), currency, dates to UTC
5. **Validate** — required fields present, types correct, references exist
6. **Resolve conflicts** — SKU collisions, duplicate names, GL account mapping
7. **Produce** a clean JSON payload matching the bundle format above
8. **Sign** via Athena
9. **Send** to `/wcapi/sync/receive/` with the connection key

The user works with Alice. Alice works with Claude and DynamicCatalogs. WC3 receives
a clean bundle and records it. The noise never enters WC3.

## Outbound Bundles

WC3 also sends data out via bundles. The outbound path:

```
Pending record (purpose="sync.bundle_out")
    │
    ▼
Celery Beat processor (hourly)
    │
    ▼
handle_bundle_out()
    │  - Read payload from Pending config
    │  - Encrypt with connection key
    │  - POST to connection endpoint
    │  - Record Bundle on ack
    │
    ▼
External system
```

Same Connection model, same encryption, same audit trail. Bidirectional when needed.

## What Was Removed

Prior to 2026-08-04, WC3 had raw import commands that parsed vendor files directly:
- `import_items_tsv` — TSV parser for Item model
- `import_bom_tsv` — TSV parser for BillOfMaterial
- `import_actions_from_csv` — CSV parser for Action model
- `ImportExportModelAdmin` — Django admin CSV/XLS upload buttons

These are archived at `archive/import_removed_2026-08-04/` as retrospection — lessons
in what not to do. The operational code no longer contains import parsing logic.

## Files

| File | What it does |
|------|-------------|
| `apps/sync/views/bundle_sync.py` | `BundleReceiveView` — the inbound endpoint |
| `apps/sync/services/bundle_send.py` | `handle_bundle_out()` — outbound delivery |
| `apps/sync/services/bundle_crypto.py` | Fernet encrypt/decrypt for payloads |
| `apps/sync/models/connection.py` | Connection — who can send/receive |
| `apps/sync/models/bundle.py` | Bundle — audit record per exchange |
| `apps/sync/choices.py` | Status, type, purpose, direction choice lists |
| `apps/sync/urls.py` | URL routing for sync endpoints |

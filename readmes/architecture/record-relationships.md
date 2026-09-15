# Record Relationships — FK + refs.links

WC3 records relate to each other through two tiers. Both are visible in the DataBrowser detail view as related panels.

## Tier 1: ForeignKey (Hard Links)

Standard Django ForeignKey columns. DB-enforced, indexed, cascading delete/protect.

Examples:
- `OrderLine.order_id → Order` (structural parent-child)
- `BillOfMaterial.parent_item → Item` (BOM parent)
- `Invoice.customer_id → OrgBase` (org reference)
- `Payment.invoice_id → Invoice` (transaction chain)

The React DataBrowser resolves these via `FK_PATTERNS` in `DataBrowser.tsx` — a static map of `parent_model → { child_model: fk_field_name }`.

**Fallback**: if no explicit entry exists, tries `${parentModel}_id`. If that field doesn't exist on the child model, the filter is silently dropped by wcapi and all records return — **this is the bug that showed all 50 BOM records instead of 7**.

**Audited 2026-08-11**: FK_PATTERNS now covers contact, customer, vendor, manufacturer, order, invoice, proposal, purchase, workorder, receipt, item, serial, catalog, warehouse, payment.

## Tier 2: refs.links (Soft Links)

JSON-based ad-hoc relationships stored in `record.refs.links`. No schema change needed. Any record can link to any other record.

Structure:
```json
{
  "refs": {
    "links": {
      "contact": [{"id": 8, "name": "Joe Builder"}],
      "item": [{"id": 416, "name": "Job Init Kit"}],
      "document": [{"id": 42}]
    }
  }
}
```

Use cases:
- GL journal entry linked to a document, action, contact, and item for an unusual event
- Action record linked to a customer complaint and the affected serial number
- Document linked to multiple items across different categories
- Any relationship that doesn't justify adding a FK column

### How the UI resolves relationships

The `RelatedPanel` component in DataBrowser follows this resolution order:

1. **FK_PATTERNS** — explicit FK field name from the audited map
2. **Fallback** — try `${parentModel}_id` as a generic FK filter  
3. **refs.links** — if FK query returns 0 results, retry with `refs__links__${parentModel}__contains=[{"id": parentId}]`

Records found via refs.links display a small "refs" badge next to the model name in the related panel header.

### wcapi filter behavior

The wcapi `_parse_filters` method (in `wcapi.py`) resolves filter keys:
- `parent_id` is intercepted and mapped through `_resolve_parent_field()` for transaction line models
- `field_id` → Django strips `_id` suffix and resolves to FK field name
- Unknown filter keys are **silently dropped** (line 544: `if field_base not in field_names: continue`)

The silent drop is why missing FK_PATTERNS entries cause all records to return instead of zero. This is by design for flexibility (ignore unknown params from older clients) but means FK_PATTERNS must be correct.

## Legacy Link Strategy (refs-only)

Before FK-first migration, all relationships used `refs.links` arrays of integer PKs.
This was fast to iterate on (no migrations) but created problems:
- No referential integrity — orphan IDs accumulate silently
- Two sources of truth invite mismatches (tracked via `RefsMismatchLog`)
- Queries against JSON arrays are slower than FK joins

The FK-first migration (see `fk-discipline.md`) converted the majority of relationships
to ForeignKey fields. The `refs` column and `RefsMixin` remain for deferred relationships
and as a denormalized display cache.

### Party Role Snapshots (BillTo / ShipTo)

Denormalized snapshots for document rendering:

```json
"refs": {
  "party_roles": {
    "billto": {"name": "Acme Corp", "addr1": "123 Main", "city": "Austin", "state": "TX"},
    "shipto": {"name": "Acme Warehouse", "addr1": "500 Dock", "city": "Dallas", "state": "TX"}
  }
}
```

These are ephemeral print caches, not relationships. Forward links remain canonical
for entity graph traversal.

### Legacy Commands

| Command | Purpose |
|---------|---------|
| `reconcile_links` | Backfill/repair reciprocal links from authoritative contact refs |
| `seed_relationships` | Randomized dev data linking (runs as part of `reseed --full`) |

These remain available for deferred relationships listed in `fk-discipline.md`.

## Diagram

See `readmes/charts/flowcharts/wc3-record-relationships.dot` (and `.svg`).

Shows:
- Tier 1 FK examples with field names
- Tier 2 refs.links examples with JSON structure
- RelatedPanel resolution flow (3 steps)

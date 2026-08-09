# PO → SO Cross-Instance Bundle

**Built:** 2026-08-09
**Status:** TODO item #95 on go-live list — complete
**Alice pointer:** Document `wc3-po-so-bundle`

## What It Does

Converts a Purchase Order on the buyer's WC3 instance into a Sales Order on the vendor's WC3 instance. The bundle UUID becomes the cross-system tracking reference. Each side owns their own record — the UUID is the only shared thread.

This is WebClerk's version of EDI between trusted trading partners, with dramatically lower transaction costs. Both sides run WC3 with the same schema. The Connection record defines the relationship and field mapping.

## The Flow

```
BUYER                                    VENDOR
──────                                   ──────
1. Create PO
2. POST /wcapi/sync/po-to-so/<id>/
   body: {connection_id: N}
   → bundle created
   → cost→price mapped
   → encrypted payload sent ──────────→  3. /wcapi/sync/receive/
                                            → auto-unpack po_to_so
                                            → Order created (status: planned)
                                         4. Sales team reviews
                                         5. POST /wcapi/sync/bundle/<uuid>/approve/
                                            → Order status → released
   ←────────────────────────────────────    → callback to buyer with SO id
6. PO refs.links.bundle[] updated
   with remote_order_id + ida
7. GET /wcapi/sync/po-status/<id>/<uuid>/
   → polls vendor status endpoint ────→  8. GET /wcapi/sync/bundle/<uuid>/status/
   ← SO status, totals, delivery ←─────     → returns current Order state
9. PO refs updated with latest status
```

## Key Design Decisions

**Purchase agent is responsible for correct costs.** No validation or recalculation of costs during bundle creation. The PO cost data is authoritative.

**Cost → price mapping.** PO `line.cost.unit` becomes SO `line.price.unit`. The Connection's `config.schema_map.cost_to_price` can override the default:

```json
{
  "schema_map": {
    "cost_to_price": {
      "unit": "unit",
      "unit_base": "unit_base",
      "discount_percent": "discount_percent",
      "discount_amount": "discount_amount",
      "extended": "extended",
      "precision": "precision"
    }
  }
}
```

**SO cost is empty.** The vendor calculates their own cost. Only price (from buyer's cost) is populated on the received SO.

**Bundle UUID is the tracking reference.** Stored in `record.refs.links.bundle[]` on both PO and SO with enough data to manage the relationship.

## API Endpoints

All under `/wcapi/sync/`:

| Endpoint | Method | Auth | Who | What |
|----------|--------|------|-----|------|
| `po-to-so/<purchase_id>/` | POST | User | Buyer | Create bundle, send to vendor |
| `bundle/<uuid>/approve/` | POST | User | Vendor | Approve SO, callback to buyer |
| `bundle/<uuid>/status/` | GET | X-Sync-Key | Vendor serves | SO status for buyer poll |
| `bundle/callback/` | POST | X-Sync-Key | Buyer receives | Vendor's approval/update callback |
| `po-status/<purchase_id>/<uuid>/` | GET | User | Buyer | Poll vendor, update local PO |

## refs.links.bundle[] Structure

On the **PO** (buyer side):
```json
{
  "bundle_uuid": "abc-123",
  "bundle_id": 42,
  "connection_id": 7,
  "connection_name": "Trading Partner — Vendor",
  "direction": "sent",
  "type": "po_to_so",
  "dt_sent": 1723190400000,
  "remote_order_id": 1501,
  "remote_order_ida": "SO-2026-0042",
  "status": "approved"
}
```

On the **SO** (vendor side):
```json
{
  "bundle_uuid": "abc-123",
  "bundle_id": 99,
  "connection_id": 12,
  "connection_name": "Trading Partner — Buyer",
  "direction": "received",
  "type": "po_to_so",
  "dt_received": 1723190401000,
  "sender_purchase_id": 305,
  "sender_purchase_ida": "PO-2026-0018",
  "status": "approved",
  "dt_approved": 1723194000000
}
```

## Connection Record

Two Connection records form the pair — one on each side:

**Buyer side** (points to vendor):
- `type`: api
- `config.channel`: bundle
- `config.direction`: push
- `config.endpoint`: vendor's `/wcapi/sync/receive/`
- `config.callback_endpoint`: buyer's `/wcapi/sync/bundle/callback/`
- `config.key`: shared symmetric key
- `config.schema_map.cost_to_price`: field mapping override

**Vendor side** (accepts from buyer):
- `type`: api
- `config.channel`: bundle
- `config.direction`: pull
- `config.key`: same shared key
- `config.callback_endpoint`: buyer's callback URL

Seed both with: `python manage.py seed_trading_partner`

## Files

| File | What |
|------|------|
| `apps/sync/services/po_to_so_bundle.py` | Create bundle from PO, map cost→price |
| `apps/sync/services/bundle_to_order.py` | Unpack bundle into Order + approve |
| `apps/sync/services/po_status_poll.py` | Buyer polls vendor for SO status |
| `apps/sync/views/po_so_bundle.py` | 5 API views |
| `apps/sync/views/bundle_sync.py` | Modified: auto-unpack po_to_so bundles |
| `apps/sync/urls.py` | 5 new routes |
| `apps/sync/management/commands/seed_trading_partner.py` | Seed example Connection pair |

## Security

- Machine-to-machine auth via `X-Sync-Key` header (Fernet symmetric encryption)
- No Django user auth required for status/callback endpoints — key is sufficient
- Send/approve endpoints require Django user auth (`@allow_write`)
- Payload encrypted with connection's shared key (same pattern as existing bundle sync)

## Relationship to Existing Conversion Chain

This does **not** use `conversion.py`. The existing conversion chain handles intra-instance document flow (Proposal → Order → Invoice). PO→SO is inter-instance — different buyer and vendor databases. The bundle is the sovereign handoff.

## Flowchart

`readmes/flowcharts/wc3-po-so-bundle.dot` — renders with `dot -Tpdf`

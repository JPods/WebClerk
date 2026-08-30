# EDI — Replaced by Sync Bundles
**Decision:** 2026-07-04 | **Status:** Explicitly NOT building EDI

---

## Why Not EDI

EDI (850/810/997) is a legacy format from the 1970s. Rigid, expensive, requires VAN (Value Added Network) subscriptions, complex field mapping per trading partner. Most small businesses can't afford or manage it.

WC3 replaces it with JSON sync bundles — same business outcome, modern technology, no VAN, no rigid format.

---

## What We Do Instead

### Outbound (our PO → vendor's sales order)

```
Purchase Order in WC3
  → serialize to JSON (our standard format)
    → wrap in a sync Bundle
      → send to vendor via Connection (HTTPS, SFTP, API)
        → vendor loads JSON into their sales order system
```

### Inbound (vendor's invoice → our receipt)

```
Vendor sends JSON via sync Bundle
  → Connection authenticates (key exchange)
    → Athena validates data (ruthless)
      → create Receipt / update PO status
```

---

## Security — Trusted Trading Partners

Partners exchange keys stored in Connection records:

```
Connection
  ├── type: 'api' or 'sftp'
  ├── config: {
  │     api_key: "partner's key for us",
  │     our_key: "our key for partner",
  │     partner_uuid: "their WC3 instance uuid"
  │   }
  ├── maps: field mapping if partner uses different names
  └── rules: validation rules for inbound data
```

Keys shared with:
- Trading partners directly (peer-to-peer)
- Ingrid (for catalog/pricing sync)
- WCHQ (for aggregated reporting)

**Athena must be ruthless** with any data passing through the system. No unvalidated JSON accepted. No data without a valid key.

---

## Why Ingrid Is Better Than EDI

| EDI | Ingrid + Sync Bundles |
|---|---|
| Rigid 850/810/997 format | Flexible JSON — any structure |
| VAN subscription required | Direct HTTPS — no middleman cost |
| Per-trading-partner mapping | Standard JSON format + optional field maps |
| Batch processing (daily/weekly) | Real-time or batch — your choice |
| Expensive implementation | Connection model + Bundle — already built |
| One-way or complex ACK (997) | Bidirectional sync with conflict resolution |

---

## What This Means for the Task List

- ~~EDIMessage model~~ — NOT building
- ~~EDIMap model~~ — NOT building
- ~~850/810/997 parsers~~ — NOT building
- Connection execution layer (Stage 5) — BUILDING (covers all sync including vendor exchange)
- Sync Bundle processor — BUILDING (handles JSON payloads)

---

## Files

| File | Status | Purpose |
|------|--------|---------|
| `apps/sync/models/connection.py` | Exists | Partner keys + config |
| `apps/sync/models/bundle.py` | Exists | Sync bundle records |
| Connection execution layer | Needs building (Stage 5) | upload/download/list |

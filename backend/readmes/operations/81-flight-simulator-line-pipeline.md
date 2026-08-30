# Flight Simulator Line Pipeline — 2026-08-19

## What Was Built

The complete line save and conversion pipeline for the flight simulator,
establishing three architectural rules that apply to all WC3 transaction handling.

---

## The Three Rules

### 1. Front End Sends Data, Backend Manages Data and Relationships

React sends plain numbers inside JSON envelopes. Never Django FK descriptor names
(`item_fk`) or internal column names (`item_fk_id`). The server reads IDs from
envelopes and sets FK columns.

```
React sends:  { item: { item_id: 421, description: "..." }, quantity: { active: 15 } }
Server does:  line_obj.item = envelope_data  (JSONField)
              line_obj.item_fk_id = envelope_data['item_id']  (FK column)
```

**Root cause this fixed:** `setattr(line_obj, 'item_fk', 421)` throws `ValueError`
because Django FK descriptors reject raw integers. Exception was silently caught —
lines never persisted, server returned "success".

### 2. Each Transaction Model Owns One Inventory Bucket

| Model | Owns | Conversion releases |
|-------|------|-------------------|
| Proposal | on_p | on_p -= qty |
| Order | on_so | on_so -= qty |
| Purchase | on_po | (none from sell-side) |
| Invoice | on_hand, on_in | (none — source handles on_so) |

Conversion pending only releases the source bucket. The target line save handles
the target bucket. No cross-bucket adjustments anywhere.

**Root cause this fixed:** on_so double-counted (30 instead of 15) because both
the conversion pending and the line save pending adjusted on_so.

### 3. Users Edit Arrays, Not Database Records

The database is for persistence, not editing. Users edit arrays in memory.
The database gets touched only at the moment of save, locks for the shortest
possible time, then releases.

- Conversion creates header only, returns line data array to React
- User reviews lines, adjusts quantities
- On Save: server creates line records, fires pending for each
- Lock window = the save loop only

---

## The Linear Flow

```
Conversion: copy line data → return array to React
                ↓
User: review → adjust qty → Save
                ↓
save_view: create target line → fire target pending (own bucket)
                ↓
Target line tells source line → save source line → fire source pending (own bucket)
                ↓
Done
```

Each step triggers exactly one thing. Each pending is a consequence of one save.

---

## Sell-Side vs Buy-Side

| Conversion | Type | Customer transfers | Source adjustment | Price source |
|---|---|---|---|---|
| Proposal → Order | Sell | Yes | Release on_p | Copy from proposal |
| Order → Invoice | Sell | Yes | Release on_so | Copy from order |
| Proposal → Invoice | Sell | Yes | Release on_p | Copy from proposal |
| Order → Purchase | Buy | No | None | Item record |
| Order → Work Order | Buy | No | None | Item record |

Purchase and work order are buy-side — a convenience so users don't re-enter item data.
They have zero impact on sell-side buckets. Customer data does not transfer.
If users want to track a purchase relative to a customer, add the customer
into `.refs.links.customer[]` with order reference in `.refs.links.order[]`.

---

## Files Changed

### Server (webClerk3)

| File | What changed |
|------|-------------|
| `apps/core/views/save_view.py` | FK descriptor skip in field copy loop; item_fk_id derivation from item.item_id; `_adjust_source_line` method; purchase exemption from source adjustment |
| `apps/transactions/services/line_item_service.py` | IN/RC pending only touch own bucket (removed on_so/on_po cross-adjustments) |
| `apps/transactions/services/conversion.py` | `_do_convert` returns line array (no saved lines/pending); single-bucket adjustments_map; sell/buy header field split; vendor optional for purchase |
| `apps/transactions/services/proposal_to_order.py` | Returns line array, no line saving or pending |
| `apps/transactions/services/order_to_invoice.py` | Same pattern; `data=` → `changes=` fix |
| `apps/products/services/inventory_flight_sim.py` | `reset_flight_simulator` function |
| `apps/core/views/manage_view.py` | `reset_flight_simulator` action |

### React (React2025)

| File | What changed |
|------|-------------|
| `src/apps/transactions/components/detail/LineCardRenderer.tsx` | Removed `item_fk` and `item_fk_id` from line construction |
| `src/pages/admin/FlightSimConsole.tsx` | `convertedLines` state; `initialLines` prop; reset on simulation start |
| `src/apps/transactions/components/TransactionDetail.tsx` | `initialLines` prop — injects converted lines for review |
| `src/api/wcapi.ts` | Preserved `refs` and `commission` on lines (removed from strip list) |

---

## Scars Paid

1. **CoreModel.data → config rename** — `proposal_to_order.py` and `order_to_invoice.py`
   still used `data=` in `Pending.objects.create()`. Silent data loss for months.
   Rule: field renames require repo-wide grep.

2. **Single-bucket violation** — conversion pending and line save pending both adjusted
   on_so. Invisible until the flight simulator walked the full lifecycle.
   Rule: each model owns one bucket, no exceptions.

3. **FK descriptor ValueError** — `setattr(line_obj, 'item_fk', 421)` silently failed
   inside `except Exception`. Invisible because the header save succeeded.
   Rule: front end sends data, backend manages relationships.

---

## Open Items

- Order→Invoice retest with single-bucket fix
- Purchase and receipt flows need testing
- Buy-side conversions should pull fresh cost/price from item record
- Customer clearing bug on +Item not yet investigated
- Orphaned pending cleanup for abandoned transactions

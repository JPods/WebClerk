# Line Save Boundary — Front End Sends Data, Backend Manages Data and Relationships

**Established:** 2026-08-19
**Applies to:** All transaction line saves (Proposal, Order, Invoice, Purchase, WorkOrder)

---

## The Rule

React sends **plain data** for line items. The server manages all FK relationships internally.

React does NOT send:
- FK descriptor names (`item_fk`, `proposal`, `order`)
- Django internal column names (`item_fk_id`, `proposal_id`)

React DOES send:
- An `item` envelope with `item_id` (plain integer) and denormalized display fields
- A `quantity` envelope with bucket values
- A `price` envelope, `cost` envelope, `comments`, `config`
- A negative `id` for new lines, positive `id` for existing lines

```json
{
  "id": -1787183890418,
  "line_number": 10,
  "price_level": "B",
  "status": "",
  "is_active": true,
  "item": {
    "item_id": 421,
    "ida_item": "421",
    "description": "Training item",
    "unit_measure": "EA"
  },
  "quantity": { "active": 15, "remaining": 15, "staged": 15 },
  "price": { "unit": 10.00, "extended": 150.00 },
  "cost": { "unit": 0, "extended": 0 },
  "_dirty": true
}
```

The server (`save_view.py`) does:
1. Copies JSON fields (`item`, `quantity`, `price`, `cost`, etc.) directly onto the model
2. Skips FK descriptor fields — never calls `setattr(line, 'item_fk', 421)`
3. Skips `_`-prefixed transient fields (`_dirty`, `_new`)
4. Derives `item_fk_id` from `item.item_id` in the envelope
5. Sets the parent FK (`proposal_id`, `order_id`) from the parent object

---

## Why This Matters

Django FK descriptors reject raw integers:
```python
setattr(line_obj, 'item_fk', 421)
# ValueError: Cannot assign "421": "ProposalLine.item_fk" must be a "Item" instance.
```

This was the root cause of the flight simulator line save bug (2026-08-19). Lines were
silently not created because the field copy loop hit `item_fk` with an integer, threw
ValueError, and the exception was caught without logging. The header save succeeded,
the response said "success", but zero lines were persisted.

---

## The Dual System on Line Models

Each line model has two item references:

| Field | Type | Purpose | Who sets it |
|-------|------|---------|------------|
| `item_fk` | ForeignKey | Referential integrity, joins | Server (from `item.item_id`) |
| `item_fk_id` | Integer (auto) | Raw FK column | Server (derived from `item.item_id`) |
| `item` | JSONField | Denormalized snapshot for fast reads | React (in the payload) |

React only knows about the `item` JSONField. It puts `item_id` inside the envelope.
The server reads `item.item_id` and sets `item_fk_id` on the model. React never
touches the FK.

This pattern applies to **all FK relationships on lines**. If a line has a FK to
another model (e.g., a warehouse, a project), React sends the ID inside a JSON
envelope or as a plain `_id` field. The server maps it to the FK column.

---

## Files Changed (2026-08-19)

| File | What changed |
|------|-------------|
| `React2025/src/apps/transactions/components/detail/LineCardRenderer.tsx` | Removed `item_fk` and `item_fk_id` from new line construction. Item ID lives only in `item.item_id`. |
| `webClerk3/apps/core/views/save_view.py` ~930-960 | Field copy loop skips FK descriptors and `_`-prefixed fields. Derives `item_fk_id` from `item.item_id` envelope after copy. Both create and update paths fixed. |

---

## Connection to WC2

In WC2, Bill managed related values as plain integers without Django FK behaviors.
The WC3 architecture adds FKs for referential integrity, but the **payload contract**
stays the same: React sends a number. The server manages the relationship.
The front end does not care about FK plumbing. It has a single number.
The backend manages data and relationships.

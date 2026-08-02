# Order Detail — Line Card Behavior and Totals

**Established:** 2026-08-01

---

## Line Card Footer

The line card footer has two rows:

### Row 1: Counter + Actions

```
Lns: 3   Items: 9   (1 selected) edit item del          L  S  XR  M
```

| Element | What it shows |
|---------|--------------|
| Lns | Line count |
| Items | Sum of qty across lines (or selected lines) |
| (N selected) | Selection indicator |
| edit / item / del | Actions for selected line(s) — appear only when selected |
| L S XR M D | Panel toggles: Inventory, Spec, XRef, Margin, Discount |

### Row 2: Totals

```
                        Deposit: $0.00   Backlog: $6,492.00   Total: $6,492.00
```

| Field | Source |
|-------|--------|
| Deposit | Sum of payments/deposits applied to this order |
| Backlog | Sum of (remaining × discounted_unit) for lines with remaining > 0 and not complete |
| Total | Sum of extended prices for all lines (or selected lines) |

**Hover over Total** to see Tax and Shipping breakdown. Hidden by default — clean display, detail on demand.

**Selection-aware:** When lines are selected, Deposit/Backlog/Total reflect only the selected lines. When none selected, they reflect all lines.

### Σ Row (DataGrid footer)

The grid's built-in sum row shows:
- **qty** — total quantity
- **remain** — total remaining/backlog quantity
- **extended** — total extended price

Per-unit fields (unit_price, %, disc price) are NOT summed — summing per-unit values is meaningless.

---

## Adjustments and Forced Changes as Line Items

**All dollar adjustments are line items.** Never adjust totals directly — add a line that puts the dollars in the correct GL account. The line IS the audit trail.

### Why

- GL entries come from lines. No line = no GL entry = the adjustment is invisible to accounting.
- The line's item determines the GL account. A discount goes to a discount GL account, not to revenue.
- The audit trail is the line itself — who added it, when, what item, what amount.

### Forced/Negotiated Adjustments

When a salesperson negotiates a price change after the order is built:

**Example:** Order total is $220. Customer and salesperson agree to round to $200.

The salesperson adds a line:
```
ida:          "negotiated"  (or "forced", "adjustment", "discount")
description:  "Negotiated discount — rounded to $200"
qty:          1
unit_price:   -20.00
extended:     -20.00
```

This line:
- Posts to the discount GL account (determined by the "negotiated" item's `gls.revenue` mapping)
- Reduces the order total from $220 to $200
- Is visible on the printed order as a line item
- Has a complete audit trail (who, when, why via description)

### Standard Adjustment Items

Every WC3 installation should have these items pre-configured:

| ida | Description | GL Account | Use |
|-----|-------------|-----------|-----|
| `negotiated` | Negotiated price adjustment | Discount | Salesperson-authorized price change |
| `adjustment` | General adjustment | Adjustment | Catch-all for corrections |
| `freight` | Freight charge | Freight Revenue | Shipping charges added to order |
| `handling` | Handling charge | Handling Revenue | Handling fees |
| `rush` | Rush/expedite fee | Rush Revenue | Rush order surcharge |
| `return-credit` | Return credit | Returns | Credit for returned goods |
| `restocking` | Restocking fee | Restocking Revenue | Fee for returns |

Alice should flag any order where a forced/negotiated line exceeds 10% of the order total — it's a signal worth reviewing, not blocking.

### Bulk Discount (D button)

The **D** button in the footer (or press **D** key when grid focused) opens a discount dialog:

1. Enter a percentage (e.g., 10)
2. Click OK (or press Enter)
3. Discount applies to **selected lines** (or all lines if none selected)
4. Sets `discount_percent` on each line → recalculates `discounted_unit` and `extended`

This handles the common case: "10% off everything" or "10% off these 3 items." The per-line discount column shows the applied percentage. Individual lines can be adjusted afterward.

---

## Three-Tier Edit Rules

| Record Status | Edit Tier | Behavior |
|--------------|-----------|----------|
| draft, open, planned | **open** | Single click edit. Auto-edit mode. Save directly. |
| journalized, released, shipped, invoiced | **pend** | Can edit, but saves create Pending records. Amber badge: "journalized — changes pend" |
| completed, cancelled, void | **closed** | No edit. Red badge: "closed" |

**Post or Pend** — the universal rule. Unlocked records post immediately. Journalized records post to pending. Closed records are done.

See: `readmes/topics/architecture/pending-flow-picture.md` for the full pending pattern.

---

## Professional Edit Behavior

Users are order processing professionals, not retail customers.

- **Single click** or **Tab** into editable fields — no double-click protection
- **Tab** saves current field, moves to next
- **Enter** saves field value
- **Escape** cancels edit
- **Auto-edit mode** (user preference) — enter edit mode automatically when opening a record

### Modifier Keys on Lines

| Action | Key |
|--------|-----|
| Select line | Click |
| Range select | Shift+click |
| Toggle selection | Cmd/Ctrl+click |
| Open line details | Enter (selected line) or double-click |
| Open item record | Shift+click on item_code |
| Delete selected | Delete or Backspace |
| Duplicate line | Cmd+D |

### Modifier Keys on Header Fields

| Action | Key |
|--------|-----|
| Edit field value | Click or Tab |
| Tooltip help | Shift+hover |
| Deep help | Shift+click |
| Admin: edit field Setting | Cmd+Option+click on label |

---

## Related

- `pending-flow-picture.md` — Post or Pend rule, pending as audit trail
- `transactions-totals.md` — How totals are computed from lines
- `linecontrol.md` — Line card column lockdown
- `~/.claude/plans/detail-json-architecture.md` — TransactionDetail.tsx plan
- `~/.claude/plans/tender-beaming-bachman.md` — Line card plan

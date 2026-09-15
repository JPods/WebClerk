# Blanket Orders, Recurring Orders & Alice Dashboard

## Three Flavors of Standing Commerce

WC3 handles all three patterns through the existing Proposal → Order transfer
chain and two fields on `quantity`: `is_blanket` and `increment`. No separate
subscription or blanket model is needed.

### 1. Blanket Orders (quantity.is_blanket = true)

A blanket order is a commitment to buy N units over time, released in smaller
orders as needed.

**Mechanism:**
- Proposal (or Order) with `line.quantity.is_blanket = true`
- `quantity.active` = total blanket commitment (e.g., 1000 units)
- `quantity.remaining` = uncommitted balance (active − sum of releases)
- Each release creates a child Order via the standard transfer service
- Transfer decrements `remaining` on the blanket line

**Flow:**
```
Proposal (blanket, active=1000)
  → Order release #1 (active=200)  → remaining=800
  → Order release #2 (active=300)  → remaining=500
  → Order release #3 (active=500)  → remaining=0, is_complete=true
```

**Key fields:**
| Field | Location | Purpose |
|-------|----------|---------|
| `is_blanket` | `line.quantity.is_blanket` | Flags line as blanket commitment |
| `active` | `line.quantity.active` | Total blanket quantity |
| `remaining` | `line.quantity.remaining` | Available for future releases |
| `is_complete` | `line.quantity.is_complete` | When true, remaining forced to 0 |
| `children_active` | `line.quantity.children_active` | Tracker: `{sum: N}` of released qty |

**Code:** `base_line_model.py` → `default_quantity()`, `normalize_quantity_map()`.
UI mockup: `readmes/topics/transaction-calculations.md` § Blanket Orders & Releases.

### 2. Recurring Orders (quantity.increment > 0)

A recurring order is a standing template that auto-generates orders on a schedule.

**Mechanism:**
- Proposal with `line.quantity.increment > 0`
- `increment` = the quantity to place on each generated order
- A scheduled job scans proposals with increment > 0 and creates Orders each cycle
- The proposal itself is never consumed — it's a template, not a commitment

**Flow:**
```
Proposal (template, increment=24)
  → [scheduler, monthly] → Order #1 (active=24)
  → [scheduler, monthly] → Order #2 (active=24)
  → ... continues until proposal is deactivated
```

**Key fields:**
| Field | Location | Purpose |
|-------|----------|---------|
| `increment` | `line.quantity.increment` | Qty per recurring order (0 = not recurring) |
| `active` | `line.quantity.active` | Not consumed — template reference qty |

**Not yet built:** The scheduler job itself. The data model is ready. TODO #111.

### 3. Blanket + Recurring (both flags)

A blanket order with `increment > 0` auto-releases on a schedule until the
blanket quantity is exhausted.

```
Proposal (blanket, active=1200, increment=100)
  → [scheduler, monthly] → Order #1 (active=100)  → remaining=1100
  → [scheduler, monthly] → Order #2 (active=100)  → remaining=1000
  → ... stops when remaining < increment or is_complete=true
```

---

## Alice Dashboard — Standing Order Monitor

Alice needs a dashboard view of all active standing orders (blanket + recurring).
This is her primary tool for proactive commerce management.

### What Alice monitors

| Signal | Source | Action |
|--------|--------|--------|
| Blanket nearing exhaustion | `remaining / active < 0.15` | Flag customer for renewal conversation |
| Blanket overdue for release | No release in 2× normal cycle | Ask: did customer forget, or has demand changed? |
| Recurring order failed to generate | Scheduler ran but no order created | FAULT — investigate (item inactive? customer on hold?) |
| Recurring quantity anomaly | `increment` changed or order qty differs | Log observation — was this intentional? |
| Blanket expired (date) | Proposal past `prefs.expires_at` with remaining > 0 | Flag: unused commitment. Renegotiate or close? |

### Dashboard query

```python
# Blanket orders — open commitments
blanket_lines = ProposalLine.objects.filter(
    quantity__is_blanket=True,
    quantity__is_complete=False,
    parent__status__in=['approved', 'active'],
)

# Recurring orders — active templates
recurring_lines = ProposalLine.objects.filter(
    quantity__increment__gt=0,
    parent__status__in=['approved', 'active'],
)
```

### Dashboard columns

| Column | Source |
|--------|--------|
| Customer | `parent.organization.name` |
| Item | `item.ida_item` + `item.description` |
| Type | Blanket / Recurring / Both |
| Committed | `quantity.active` (blanket) or `increment` (recurring) |
| Released | `quantity.active − quantity.remaining` (blanket) |
| Remaining | `quantity.remaining` (blanket) |
| % Used | progress bar |
| Last Release | most recent child order date |
| Next Due | calculated from schedule |
| Status | On Track / Warning / Overdue / Exhausted |

### Alice's role

Alice doesn't just display — she acts:
- **Observe:** Log every release, every schedule run, every anomaly
- **Pattern:** Customer X always releases early. Customer Y is slowing down.
- **Recommend:** "Customer Z's blanket is 85% consumed with 4 months left.
  Suggest renewal conversation." → Action record to sales rep.
- **Promote:** If a pattern holds across 3+ customers, promote to a Setting
  (e.g., default renewal threshold = 15%).

This feeds Alice's observe → log → pattern → recommend → promote loop
(see `readmes/topics/ai/pattern-recognition.md`).

---

## Implementation Notes

- **No separate model.** Blanket and recurring are flags on the existing quantity
  JSON envelope, not new Django models.
- **Transfer service handles releases.** Standard Proposal → Order transfer with
  quantity tracking. No special blanket transfer code.
- **Scheduler is TODO.** The increment field exists in the schema. The Celery beat
  job that reads it and generates orders is not yet built (TODO #111).
- **is_complete cancels backlog.** Setting `is_complete = true` on a blanket line
  forces `remaining = 0` — no more releases possible. This is already implemented
  in `normalize_quantity_map()`.

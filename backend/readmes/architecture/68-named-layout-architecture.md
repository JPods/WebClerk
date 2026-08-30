# Named Layout Architecture — 2026-08-16

**Status:** Superseded by `db-layout-schema.md` (WC3) as of 2026-08-18.

The naming convention established here (`dynamic`, `display`) was replaced by
canonical terms: **list, detail, form, column**. See:

- **Schema:** `/Users/williamjames/Documents/CommerceExpert/webClerk3/readmes/topics/architecture/db-layout-schema.md`
- **Model map:** `/Users/williamjames/Documents/CommerceExpert/webClerk3/readmes/topics/architecture/model-layout-map.md`

---

## What Survives From This Document

### JSON Leaf Behaviors

Dot-path field behaviors for JSON envelopes are generated from a single source:

**File:** `apps/core/management/commands/seed_field_access.py`
- `LEAF_BEHAVIORS` — canonical `{type, label}` for every leaf (totals.total, price.unit, etc.)
- `LEAF_MAP` — which models get which leaf sets
- `_inject_leaf_behaviors()` — generates dot-path entries in fieldBehaviors

Both `seed_field_access` and `seed_model_definitions` call the same function.

**Sell vs Exec split:**

| Base class | Has price? | Models |
|---|---|---|
| BaseSellLineModel | quantity + price + cost | order_line, invoice_line, proposal_line |
| BaseExecLineModel | quantity + cost only | purchase_line, requisition_line, receipt_line, work_order_line |

Receipt inherits from BaseModel (not BaseTransactionModel) — no totals envelope.

### Smart Default Layouts

`seed_default_layouts.py` generates default list (12 cols) and detail (up to 30 fields)
layouts for all models using priority tiers:

1. ida (always first)
2. WHO — company, attention, contact, customer, vendor, assigned_to, rep
3. WHAT — name, action, description, sku, type, category
4. VALUE — envelope dot-paths for transactions (totals.subtotal, etc.) or flat currency fields
5. WHY — purpose, explanation, intent, situation
6. WHEN — action-event dates only (dt_start, dt_deadline, dt_needed) — NOT system timestamps
7. STATUS — status, priority, percent_complete (is_active removed — filter instead of display)
8. CONTEXT — comment, comments, notes

`MODEL_ALIASES` handles parent_model → Django model_name mismatches:
- `other_org` → `other`
- `linkage` → `linkageentry`
- `inventory_adjustment_run` → `inventoryadjustmentprocessorrun`

### Planned: Alice Leaf Learning Loop

When Alice encounters a JSON leaf field with no behavior entry:
1. **Detect** — leaf path has no fieldBehaviors entry
2. **Ask** — present user with options (currency? number? text? select list?) + comment
3. **Learn** — write resolution to observation log + update wc:model config.behaviors
4. **Promote** — post to WC_HQ → schema_audit picks it up → syncs to all installations

The LEAF_BEHAVIORS table is the bootstrap. Alice fills the gaps from user interaction.

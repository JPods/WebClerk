# WC3 Architecture — Industry Comparison

**Created:** 2026-08-25
**Status:** Complete — all 10 gaps resolved, zero new models added

## Purpose

Compare WebClerk3's architecture against industry commerce platforms (Odoo, ERPNext, NetSuite, Saleor, Shopify). Originally identified 10 gaps — all resolved in a single session using existing models and patterns.

---

## The Core Finding: WC3 Is Simpler

Every industry platform solves these 10 problems by adding models. WC3 solved all 10 with **zero new models**. The comparison:

| Problem | Industry Solution | WC3 Solution |
|---------|------------------|--------------|
| Credit memos | CreditNote model + CreditNoteLine | Invoice with negative quantities |
| Inventory transfers | StockTransfer model + TransferLine | Receipt with +/- lines, different warehouses |
| Recurring billing | Subscription model + SubscriptionLine | Proposal with quantity.increment |
| Revenue recognition | RevenueSchedule model + recognition entries | status=consigned / status=deferred + dt_needed |
| Approval workflows | ApprovalRule model + ApprovalRecord | signoff_request status + Setting rules + Action |
| Shipment tracking | Shipment model + ShipmentLine | shipping JSON envelope on TransactionBaseModel |
| Customer pricing | PriceBook model + PriceBookEntry | Catalog + Catalog.config.lines + price_resolver |
| Multi-currency | CurrencyTransaction model + dual GL | sell.exchange_rate + FX settlement in journalize |
| Notification engine | NotificationRule + NotificationTemplate | Touch with dt_future + external email tools |
| Materialized views | Database materialized views + refresh jobs | Alice manages pre-aggregated arrays with periodic refresh |

Industry platforms add ~20+ new models across these 10 problems. WC3 added none.

### How WC3 Simplifies

WC3 uses three patterns instead of new models:

1. **Signed quantities on existing documents** — negative quantities reverse GL and inventory naturally. Credit memos, inventory transfers, and scrap adjustments all work on existing invoice and receipt documents without dedicated models.
2. **Status gates** — `consigned`, `deferred`, and `signoff_request` block transitions until conditions are met. Approval rules, deferred revenue, and consignment are configuration, not schema.
3. **JSON envelopes** — shipping, signoff audit trails, and FX settlement data live on the transaction that owns them. The data travels with the document; no orphaned records, no extra JOINs.

### Where WC3 Could Simplify Further

| Area | Current State | Could Be Simpler |
|------|--------------|-------------------|
| **Erosion model** | Separate relational model | Could be a JSON array in the transaction's metadata — same pattern as config.signoff. But the separate model enables cross-org reporting, so it earns its existence. |
| **InventoryLayer** | Separate model per warehouse/item/lot | Earned — inventory valuation requires independent rows for FIFO/LIFO costing |
| **GlJournal** | Separate model per posting | Earned — GL entries must be independently queryable for reconciliation |
| **Touch** | Separate model per communication | Could be a JSON array on the contact, but volume justifies a table for search and reporting |
| **Catalog + CatalogLine** | Two models | CatalogLine should be `Catalog.config.lines` JSON — consistent with the zero-model pattern. If catalog line volume makes JSON unwieldy (1000+ items per catalog), promote to a model then. Until that point, JSON earns simplicity. |

**Verdict:** The existing models each earn their existence. The simplification opportunity was in *not adding more*, which this session proved.

---

## Where WC3 Stands Out

| Area | WC3 Approach | Industry Norm |
|------|-------------|---------------|
| **PJPV data envelopes** | JSON envelopes as source of truth; scalars are indexes only; one compute engine per concern | Flat scalar columns with scattered calculation logic |
| **Single totals engine** | `recalculate_totals()` is the sole authority — no second path | Multiple `_compute` methods per document type |
| **Canonical quantity semantics** | `staged/active/remaining` across all line types — document type gives quantity its meaning | 4+ separate quantity fields per line type, each named differently |
| **Transaction lineage** | Polymorphic `parent_id + parent_model` + `flow.source/children` | Per-type FK fields; new document types require schema changes |
| **Denormalization discipline** | Explicit `refs.links` cache with defined DENORM_FIELDS; FK is always authoritative | Ad-hoc or absent |
| **AI agent integration** | Alice embedded in the commerce loop — observes, patterns, recommends, promotes | No mainstream platform has this |
| **Data-driven UI** | 45K lines → 2K via DynamicDetail + ui.json + Settings | XML views or DocType JSON — neither achieves this reduction |
| **Erosion tracking** | Dedicated model tracking *why* margin was lost | No standard platform tracks this as a first-class entity |
| **Zero-model problem solving** | Credit memos, transfers, subscriptions, approvals — all without new models | Every platform adds models for each of these |

---

## Where WC3 Is at Parity

| Area | Notes |
|------|-------|
| **Bill of Materials** | Parent/child with scrap factor, yield, phased effectivity, alternates |
| **General Ledger** | Double-entry, journalize lock, subledger reconciliation |
| **RBAC** | Django groups + field-level ModelRoleConfig |
| **Payment application** | Polymorphic application to invoices/purchases |
| **Inventory layers** | Per-warehouse, per-lot, serial/lot/bulk tracking |
| **Audit trail** | Before/after JSON snapshots, user/IP/timestamp |

---

## All 10 Gaps — Resolution Summary

### Gap 1: Multi-Currency — COMPLETE

**Resolution:** Rate captured at transaction creation in `sell.exchange_rate`. User adjusts if renegotiated. At payment journalize, system compares captured vs current rate, posts FX gain/loss to `OTHER-FXGAINLOSS-000`, creates Erosion record for losses, updates org `financial.fx` metrics.

**Doc:** `readmes/topics/architecture/currency-exchange.md`

### Gap 2: Credit Memo / Returns — COMPLETE

**Resolution:** Invoice with negative quantities. Print selection distinguishes it visually. GL signs reverse naturally. For scrap: negative Receipt adjusts inventory and GL. No CreditMemo model.

### Gap 3: Shipment / Fulfillment Tracking — COMPLETE (data model)

**Resolution:** `shipping` JSON envelope on TransactionBaseModel. `packages[]` = containers (box/pallet hierarchy), `packages[].items[]` = items per container. Tracking numbers, weight, costs, carrier all in the envelope. Shipping documents connect with the receipt_line that sourced the goods. Services deferred to ~Nov 2026 (Action #31213).

**Doc:** `readmes/topics/architecture/shipping-fulfillment.md`

### Gap 4: Recurring Billing — COMPLETE

**Resolution:** Proposals with `quantity.increment`. Standing proposal with increment qty; each billing cycle converts the next increment to an order/invoice. No subscription model.

### Gap 5: Approval Workflows — COMPLETE

**Resolution:** `signoff_request` status in the select list. Setting `config.approval` defines rules with conditions. Action created with sequential `assigned_to` (active/passive). Each assignee carries `dt_requested` and `dt_response` for administrative drag measurement. Transaction `config.signoff` captures full audit trail. Priority 2 (High) on all signoff Actions.

**Doc:** `readmes/topics/architecture/approval-workflows.md`

### Gap 6: Customer-Specific Pricing — ALREADY BUILT

**Resolution:** Misidentified as gap. Catalog + CatalogLine + `price_resolver.py` already provide: universal % discount, per-item overrides, qty breaks, date ranges, margin floor, priority-based catalog resolution, customer-group pricing.

### Gap 7: Notification / Email Engine — COMPLETE

**Resolution:** WC3 is not an email marketing tool. Touch records with `dt_future` for user agenda. Export to external email tools (mailsuite.com). Alice harvests read rates from mail tracking. 98% focus on timely follow-up for existing customers.

### Gap 8: Inventory Transfers — COMPLETE

**Resolution:** Receipt with +/- lines for same item, different warehouses. Positive = destination (in), negative = source (out). GL and inventory layers handle signs. No transfer model.

### Gap 9: Revenue Recognition — COMPLETE

**Resolution:** Two status gates: (1) `consigned` blocks journalization until status changes (goods on consignment). (2) `deferred` with `dt_needed` as "recognize after" date — journalize skips until date passes. No RevenueSchedule model.

### Gap 10: Materialized Reporting Views — COMPLETE

**Resolution:** Alice manages pre-aggregated display arrays for dashboards. Initialized at startup. Updated two ways: transaction save pushes count/value deltas, and Alice periodically refreshes from DB. No database materialized views needed.

---

## The Pattern

WC3 solves problems that other platforms solve with new models by using:

1. **Signed quantities** — negative quantities on existing documents reverse GL and inventory naturally
2. **Status gates** — new statuses (signoff_request, deferred, consigned) block transitions until conditions are met
3. **JSON envelopes** — shipping, signoff, FX, pricing data lives on the transaction that owns it
4. **Alice** — aggregation, pattern detection, and external tool integration without database infrastructure

The cost of a new model is never just the model. It's the serializer, the API, the tests, the admin, the documentation, and every future migration that touches it. WC3 pays that cost only when a model earns its existence through independent queryability or cross-entity reporting needs.

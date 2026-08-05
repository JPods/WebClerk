# Go-Live Todo — WebClerk 3.0

Established 2026-08-05. Living document. Check items off as completed.
Each item has an owner, priority, and scope estimate.

---

## 1. Payment Processing

Build viable connections for Stripe, PayPal, Square. Complete integration when end user selects their gateway.

- [ ] **Connection records** — seed Setting records for each gateway (Stripe, PayPal, Square) with empty API key fields. User enters their own keys in Settings.
- [ ] **Stripe skeleton** — payment intent creation, charge, refund, webhook handler. Functional with test keys.
- [ ] **PayPal skeleton** — order creation, capture, refund, webhook handler. Functional with sandbox.
- [ ] **Square skeleton** — payment creation, refund, webhook handler. Functional with sandbox.
- [ ] **Payment processing UI** — button in Apply Payment to process a new card/ACH payment, not just record a manual one.
- [ ] **Webhook endpoints** — `/wcapi/webhooks/stripe/`, `/wcapi/webhooks/paypal/`, `/wcapi/webhooks/square/`. Signature verification on all.
- [ ] **Gateway response sanitization** — strip PII/card data from `payment.gateway_response` before storage.
- [ ] **Refund workflow** — UI to initiate refund from payment record, calls gateway API, creates credit memo.
- [ ] **3D Secure / SCA** — Stripe PaymentIntents with `confirm=true` and redirect handling.

Priority: **CRITICAL** | Scope: 2-3 sessions per gateway

---

## 2. Tax Calculation

Start with manual entry. Build automated system up to the connection point — user selects and configures their tax service.

- [ ] **Manual tax entry** — tax_rate field editable on transaction lines. Override auto-calc when user enters a rate.
- [ ] **Built-in tax engine** — jurisdiction lookup by address → rate lookup → line-level calculation. Works without external service.
- [ ] **Tax Jurisdiction seed data** — US state sales tax rates as starting dataset. User can edit/add.
- [ ] **Avalara connection record** — Setting with empty API credentials. Code path: if credentials present, call Avalara; else use built-in.
- [ ] **TaxJar connection record** — same pattern as Avalara.
- [ ] **Tax exemption UI** — on customer/vendor record, upload cert number, expiration date, jurisdiction. Display on transaction.
- [ ] **Tax audit trail** — every tax calculation writes to `metadata.tax_decisions[]` with rate, jurisdiction, source (manual/builtin/avalara), timestamp.
- [ ] **Tax report** — summary by jurisdiction, period. Uses `TaxReportPrintDocument.tsx` (already exists).

Priority: **CRITICAL** | Scope: 1-2 sessions for built-in + manual; 1 session per external service

---

## 3. Shipping Integration

Build interfaces for USPS, UPS, FedEx, DHL. Connection records sit ready — users add their own API keys.

- [ ] **Connection records** — seed Setting records for USPS, UPS, FedEx, DHL with empty credential fields (API key, account number, meter number as needed per carrier).
- [ ] **Carrier abstraction** — `ShippingCarrier` base class with `get_rates()`, `create_shipment()`, `create_label()`, `track()`, `cancel()`. Each carrier implements.
- [ ] **USPS integration** — rate calculation, label generation (USPS Web Tools API or newer v3 API).
- [ ] **UPS integration** — rate calculation, label generation, tracking (UPS Developer Kit REST API).
- [ ] **FedEx integration** — rate calculation, label generation, tracking (FedEx REST API).
- [ ] **DHL integration** — rate calculation, label generation, tracking (DHL Express API).
- [ ] **Rate shopping UI** — on order/invoice, show rates from all configured carriers side by side. User selects.
- [ ] **Label generation** — PDF and ZPL (Zebra) output. Store label URL/data in shipment record.
- [ ] **Tracking updates** — webhook or polling for tracking events. Display on transaction detail.
- [ ] **Ship-to address validation** — call carrier address validation API before label creation.
- [ ] **Shipping method on transaction** — `config.shipping_method` field populated from rate selection.

Priority: **CRITICAL** | Scope: 1-2 sessions per carrier; 1 session for rate shopping UI

---

## 4. Packing Window

- [ ] **Pick list generation** — from order lines, generate pick list grouped by warehouse location.
- [ ] **Pick list UI** — checklist view with item, quantity, location, scanned/confirmed status.
- [ ] **Pack confirmation UI** — assign picked items to boxes/containers. Capture weight per box.
- [ ] **Packing slip template** — `PackingSlipPrintDocument.tsx`. Auto-generates from pack data.
- [ ] **Carrier selection** — during pack, select carrier and service level. Shows rates if carrier APIs configured.
- [ ] **Label print trigger** — after pack confirmed + carrier selected, generate and print label.
- [ ] **Partial shipment** — pack subset of order lines → creates invoice for shipped items only.
- [ ] **Ship confirmation** — marks order lines as shipped, updates tracking, sends notification.

Priority: **CRITICAL** | Scope: 2-3 sessions

---

## 5. Inventory Adjustment

Backend processor exists. Needs frontend.

- [ ] **Adjustment creation UI** — select item, warehouse, quantity (+/-), reason code, notes.
- [ ] **Reason codes** — seed list: cycle count, damage, return, shrinkage, correction, receipt, other.
- [ ] **Approval workflow** — adjustments over threshold require manager approval before processing.
- [ ] **Bulk adjustment** — CSV upload for cycle count results.
- [ ] **Cycle count workflow** — generate count sheets by warehouse/zone, enter counts, auto-calculate variance.
- [ ] **Adjustment history** — filterable log per item showing all adjustments with who/when/why.
- [ ] **Inventory layer viewer** — show FIFO/LIFO cost layers per item per warehouse.

Priority: **CRITICAL** | Scope: 2 sessions

---

## 6. Product Detail Pages

10+ models exist. Most only accessible via DataBrowser JSON view.

- [ ] **Item detail page** — header (name, SKU, status, images), pricing tab (cost, sell, margin), inventory tab (layers, reservations), BOM tab (if BOM exists), catalog tab, specs tab.
- [ ] **BOM editor** — tree view of bill of materials. Add/remove components, set quantities, calculate rolled-up cost.
- [ ] **Variant manager** — parent item with variant grid (size × color, etc.). Variant-level pricing and inventory.
- [ ] **Catalog/price list editor** — price tiers by customer group. Effective dates. Volume breaks.
- [ ] **Serial number tracker** — assignment, history, warranty tracking per serial.
- [ ] **Warehouse management** — locations, bins, transfer between locations.

Priority: **IMPORTANT** | Scope: 1 session per model detail page

---

## 7. Transaction Flow & Workflows

- [ ] **Status guard rails** — prevent invoice without order (unless over-the-counter), prevent payment without invoice.
- [ ] **Approval workflows** — configurable per transaction type. Draft → Submitted → Approved → Processing.
- [ ] **Return/credit memo** — create credit memo from invoice. Reverse inventory. Apply credit to customer balance.
- [ ] **Cancellation workflow** — cancel order/invoice with reason. Reverse inventory reservations. Notify.
- [ ] **Document cloning** — copy any transaction to create a new one (repeat order pattern).
- [ ] **Batch status update** — select multiple transactions, change status in bulk.
- [ ] **Visual flow indicator** — show document lineage on detail page (Proposal → Order → Invoice → Payment chain).

Priority: **IMPORTANT** | Scope: 2-3 sessions

---

## 8. PO → SO via Bundle

- [ ] **PO → SO field mapping** — define which PO fields map to SO fields. Store in Bundle rules.
- [ ] **Conversion trigger** — when PO is released, auto-create corresponding SO (or queue for review).
- [ ] **Conflict resolution UI** — when bundle sync detects conflicts (price mismatch, qty mismatch), show resolution dialog.
- [ ] **Bundle status dashboard** — show all pending/completed/failed bundles with drill-down.
- [ ] **Reverse sync** — SO status changes (shipped, invoiced) flow back to PO status.

Priority: **MEDIUM** | Scope: 2 sessions

---

## 9. Printing & Reports

- [ ] **Packing slip template** — (covered in Packing section above)
- [ ] **Shipping label integration** — carrier-generated labels rendered in print workflow.
- [ ] **Batch printing** — select multiple transactions, generate combined PDF.
- [ ] **Scheduled reports** — weekly/monthly report generation via Celery tasks.
- [ ] **Statement generation** — customer statement (open invoices, payments, balance) with date range.
- [ ] **Aged receivables report** — 30/60/90/120+ day aging buckets.
- [ ] **Sales tax report** — by jurisdiction, by period (already has template).
- [ ] **Inventory valuation report** — FIFO/LIFO cost layers, total valuation per warehouse.

Priority: **IMPORTANT** | Scope: 1 session per report type

---

## 10. Security Fixes

- [ ] **Payment gateway response sanitization** — strip card numbers, CVV, raw tokens from `gateway_response` before storage. Keep only: transaction ID, status, amount, timestamp.
- [ ] **Tax exemption cert handling** — store cert reference only, not cert content. Add verification date, expiration date, verified_by fields. Encrypt cert number at rest.
- [ ] **API rate limiting** — add throttle to wcapi endpoints. Default: 100 req/min for authenticated, 20 req/min for anonymous. Higher for webhook endpoints.
- [ ] **Field-level access control** — cost fields (landed cost, margin, supplier pricing) hidden from non-admin roles. Enforce in wcapi serializer, not just UI.
- [ ] **Audit trail enforcement** — every payment, tax decision, and inventory adjustment MUST write to audit_trail. Make it non-optional in the model save path.
- [ ] **Inventory lock timeout** — `InventoryLayer.is_locked` gets a `locked_until` timestamp. Auto-unlock after 5 minutes if processor doesn't clear it.

Priority: **CRITICAL** | Scope: 1 session

---

## 11. Bug Fixes

- [ ] **`po_totals.py` import error** — `cast` and `Decimal` used without import. PO total calculation crashes at runtime.
- [ ] **Payment apply race condition** — add `select_for_update()` on payment record during application to prevent double-apply.
- [ ] **Inventory layer orphan locks** — add management command to clear stale locks older than 10 minutes.
- [ ] **Parent-child orphan cleanup** — when transaction is deleted, clear `parent_id`/`parent_model` on children instead of cascading delete.
- [ ] **Multi-currency skeleton** — `InventoryLayer.cost.exchange_rate` exists but no conversion logic anywhere. Either implement or remove the field to avoid confusion.

Priority: **CRITICAL** (bugs) | Scope: 1 session

---

## 12. Missing Frontend Pages

Backend models exist. No dedicated UI.

- [ ] **Requisition detail** — purchase requisition creation, approval, conversion to PO.
- [ ] **Work Order detail** — work order creation, BOM explosion, labor tracking, completion.
- [ ] **Receipt detail** — receive against PO, inspect, put-away, variance recording.
- [ ] **Commission calculator** — set rates per rep/item/category. Calculate commissions on invoiced sales.
- [ ] **Discount/promotion engine** — coupon codes, volume discounts, customer-specific pricing rules.

Priority: **MEDIUM** | Scope: 1 session per page

---

## Prioritized Sequence

| Phase | Items | Why |
|-------|-------|-----|
| **Phase 1: Foundation** | Security fixes (#10), Bug fixes (#11), Inventory adjustment (#5) | Can't ship with known security gaps and crashes |
| **Phase 2: Money** | Payment processing (#1), Tax calculation (#2) | Money in, money calculated correctly |
| **Phase 3: Fulfillment** | Shipping (#3), Packing (#4) | Money collected → goods shipped |
| **Phase 4: Products** | Product detail pages (#6), Transaction flow (#7) | Users can manage their catalog and see document flow |
| **Phase 5: Integration** | PO→SO bundle (#8), Printing (#9), Missing pages (#12) | Advanced workflows, reporting, completeness |

---

*Each phase can ship independently. Phase 1 is prerequisite for all others.*
*Carrier and gateway connections sit ready — users configure when they choose.*

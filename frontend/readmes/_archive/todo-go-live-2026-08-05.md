# Go-Live Todo — WebClerk 3.0

Established 2026-08-05. Living document. Check items off as completed.
Each item has an owner, priority, and scope estimate.

| Phase | Items | Status |
|-------|-------|--------|
| **Phase 1: Foundation** | Security (#10), Bugs (#11), Inventory (#5) | **COMPLETE** 2026-08-05. Commission security added same day. |
| **Phase 2: Money** | Payment (#1), Tax (#2) | Tax built-in **COMPLETE**. Payment backend **COMPLETE** (Spreedly). **GO-LIVE BLOCKER:** Frontend payment UI (~1 session). External tax deferred to Phase 5. |
| **Phase 3: Fulfillment** | Shipping (#3), Packing (#4) | Packing core **COMPLETE**. Shipping backend **COMPLETE** (UPS, FedEx, USPS, DHL). Remaining: rate shopping + label + tracking UI (~1-2 sessions). Manual entry works without it. |
| **Phase 4: Products** | Product detail (#6), Workflows (#7) | Serial tracker **COMPLETE**. DataBrowser covers all models. Detail pages and workflows are polish, not blockers. |
| **Phase 5: Integration** | PO→SO (#8), Printing (#9), Pages (#12), TechNotes (#13), Commission (#14) | Print + TechNotes + Commission core **COMPLETE**. Remaining: batch print, scheduled reports, statements, aged AR, email merge, PO→SO bundle, 3 detail pages, commission panel/payment. |

---

## Minimum Viable Go-Live

What must be true before the first real order:

| Requirement | Status | What remains |
|-------------|--------|-------------|
| Customer can pay | **BLOCKED** | Payment UI with Spreedly hosted fields. ~1 session. This is the single blocker. |
| Tax calculates correctly | **READY** | Built-in US sales tax works. Manual entry works. Avalara/TaxJar deferred. |
| Order converts to invoice | **READY** | Conversion chain works. Partial shipment works. |
| Inventory adjusts on ship | **READY** | Pending path, lock lifecycle, layer accounting all complete. |
| User can print invoice | **READY** | Universal print renderer + 7 layouts. Cmd+P. |
| Shipping can be recorded | **READY** | Manual entry in PackingPanel step 3. Carrier API rates are nice-to-have. |
| Commission calculates | **READY** | Auto-populate, per-line, staff-only visibility. |
| Internal data is not exposed | **READY** | Commission, gateway, cost fields stripped for non-staff. |

**One session to go-live:** build the Spreedly hosted fields payment UI.

Everything else — carrier rate shopping, detail pages, approval workflows, PO→SO bundles, batch printing — is polish on a working system. The DataBrowser provides access to every model. Manual entry covers every workflow that doesn't have a dedicated UI yet.

---

## 1. Payment Processing

Universal gateway via Spreedly. One integration, user picks their gateway. Token-in-a-token: WC3 never sees card data.

- [x] **Spreedly service** — `SpreedlyService` class: purchase, authorize, capture, void, credit, refund (void-then-credit). REST API with Basic Auth. No SDK dependency. 2026-08-05.
- [x] **process_payment / refund_payment** — helper functions that wire Payment records to Spreedly. Store only: pm_token, last4, brand, exp, fingerprint. Never card number, CVV, or replayable tokens. 2026-08-05.
- [x] **Payment gateway Setting** — Setting #625 (purpose=payment_gateway). Spreedly credentials, active gateway token, supported gateways (Stripe, PayPal, Braintree, Authorize.Net), token rule documentation. 2026-08-05.
- [x] **API endpoints** — `POST /payments/process/` (charge), `POST /payments/refund/` (void-then-credit), `POST /payments/webhooks/spreedly/` (lifecycle events). Rate-limited. 2026-08-05.
- [x] **Gateway response sanitization** — already built (GATEWAY_SAFE_KEYS whitelist, auto-sanitize on Payment.save). 2026-08-05.
- [x] **Webhook endpoint** — `/payments/webhooks/spreedly/` handles transaction state changes. Legacy `/stripe/` and `/paypal/` routes alias to the same handler. 2026-08-05.
- [ ] **Payment processing UI** — Spreedly Web SDK (hosted fields iframe) in Apply Payment dialog. Card number + CVV collected in Spreedly's iframe, returns pm_token. WC3 JS never touches card data. Needs: SDK script tag, iframe mount, token callback → `POST /payments/process/`.
- [ ] **Apple Pay / Google Pay** — Spreedly supports both via their `express` checkout. Needs: client-side button integration, Spreedly Express config. Gateway must support it (Stripe does).
- [ ] **3D Secure / SCA** — Spreedly handles 3DS via `lifecycle` transactions. Gateway redirects to bank, Spreedly captures result. Needs: redirect handling in payment UI.
- [ ] **Refund UI** — button on Payment detail to initiate refund. Calls `/payments/refund/`. Creates credit memo on the invoice.
- [ ] **Saved cards** — retain pm_token on Contact record for repeat purchases. Spreedly vaults the card. Display saved cards (last4 + brand) in checkout.

**Note:** Square is not supported by Spreedly. Stripe + PayPal + Braintree + Authorize.Net cover >95% of users. Square direct integration can be added later if needed.

The remaining payment work is all frontend — building the checkout UI with Spreedly's hosted fields. One backend, multiple checkout experiences. Apple Pay, Google Pay, PayPal buttons, and 3D Secure all produce the same thing: a `payment_method_token` that gets POSTed to `/payments/process/`.

**Note to self:** JPods will process a massive number of transactions per day — small-packet continuous flow, not batch. The current synchronous Spreedly call per transaction will need refinement: connection pooling, async processing via Celery, batch settlement, and possibly a dedicated Spreedly environment for JPods volume. Revisit before JPods ticketing goes live.

Priority: **CRITICAL** | Scope: Backend COMPLETE. Frontend payment UI: 1 session. Apple Pay/3DS: 1 session.

---

## 2. Tax Calculation

Start with manual entry. Build automated system up to the connection point — user selects and configures their tax service.

**No Value Added Tax (VAT) mechanism at this time.** Current tax model is US sales tax: single rate per jurisdiction applied to taxable line items. VAT (cascading, input/output credits, reverse charge, multi-rate per item category) is a different architecture. Will require separate design when international users need it.

- [x] **Customer → jurisdiction → rate flow** — `applyCustomerDefaults.ts` fetches customer's `tax_jurisdiction`, copies `tax_rate_sales` into transaction `finance.sales_tax_rate`. Exempt customers (non-empty `tax_exempt_code`) get zero rate + exempt flag. 2026-08-05.
- [x] **Per-line tax calculation** — `totals.py` applies header tax rate per line. Checks item taxability (`cost.tax_code = EXEMPT` skips). Exempt transactions skip all lines. Line-level `tax.sales` override takes priority (user can change rate per line). 2026-08-05.
- [x] **Tax on shipping** — jurisdiction's `tax_rate_on_shipping` applied to shipping total in `totals.py`. Matches WC2 `<>aTaxRateShipping` pattern. 2026-08-05.
- [x] **`line_type` field** — product/tax/shipping/discount on all 7 line models. Routes extended amount to correct total bucket. Tax lines (environmental fee, recycling) go to tax total. Shipping lines (freight, handling) go to shipping total. Migration 0027 applied. Select dropdown in DataBrowser. 2026-08-05.
- [x] **Line_type toggle UI** — toggle buttons below selected line in LineCardRenderer (Shipping, Tax, Discount). Colored underline: amber=tax, blue=shipping, red=discount. Click toggles; click same reverts to product. 2026-08-05.
- [x] **Manual tax entry** — `tax%` column on sell-side lines. Editable per line, bulk-editable via header click. `sales_rate` override in `tax` envelope; totals.py respects line rate over header rate. 2026-08-05.
- [x] **Tax Jurisdiction seed data** — `seed_tax_jurisdictions` management command. 50 states + DC with state-level rates, tax-on-shipping flags. Idempotent, `--force` to update. 2026-08-05.
- [ ] **Avalara connection record** — Setting with empty API credentials. Code path: if credentials present, call Avalara; else use built-in. *Deferred to Phase 5 — see `readmes/todo-tax-services.md`.*
- [ ] **TaxJar connection record** — same pattern as Avalara. *Deferred to Phase 5 — see `readmes/todo-tax-services.md`.*
- [x] **Tax exemption UI** — `tax_exempt_id`, `tax_exempt_exp`, `tax_exempt_verified_by`, `tax_exempt_verified_dt` on OrgFinancialCommon settings. Displayed in OrgFinancialsPanel with expiration warning (amber when past due). 2026-08-05.
- [x] **Tax audit trail** — `recalculate_totals()` writes `metadata.tax_decisions` with dt, exempt flag, header_rate, jurisdiction, and per-line entries (rate, taxable, tax, source). Sources: `header_rate`, `line_override`, `line_amount`, `item_exempt`. 2026-08-05.
- [x] **Tax report** — `TaxReportPrintDocument.tsx` with jurisdiction/period summary, invoice counts, tax collected totals. Wired via universal print renderer. 2026-08-05.

Priority: Built-in tax **COMPLETE** 2026-08-05. External services (Avalara, TaxJar) deferred to Phase 5.

---

## 3. Shipping Integration

Build interfaces for USPS, UPS, FedEx, DHL. Connection records sit ready — users add their own API keys.

- [x] **Connection records** — `seed_connections` creates draft Connection records for UPS, FedEx, USPS, DHL with empty credential fields. User fills in API keys, sets status=active. No local rate tables — API-first. 2026-08-05.
- [x] **Carrier abstraction** — `CarrierBase` abstract class with `get_rates()`, `create_shipment()`, `track()`, `validate_address()`, `cancel_shipment()`. Registry pattern: `@register_carrier` decorator, `get_carrier(config)` factory. Surcharge engine (fuel, handling, markup) from WC2 heritage. `apps/transactions/services/carriers/base.py`. 2026-08-05.
- [x] **UPS integration** — OAuth 2.0 REST. Rating (Shop), Shipping (labels), Tracking, Address Validation, Void. `carriers/ups.py`. 2026-08-05.
- [x] **FedEx integration** — OAuth 2.0 REST. Rating, Shipping (labels), Tracking, Address Validation, Cancel. `carriers/fedex.py`. 2026-08-05.
- [x] **USPS integration** — OAuth 2.0 REST. Pricing v3, Labels v3, Tracking v3, Address v3. `carriers/usps.py`. 2026-08-05.
- [x] **DHL integration** — Basic Auth REST. Rates, Shipments (labels), Tracking. `carriers/dhl.py`. 2026-08-05.
- [x] **wcapi/manage wiring** — `get_shipping_rates`, `create_carrier_shipment`, `track_shipment`, `validate_ship_address`, `cancel_carrier_shipment` all wired via `_carrier_action()` dispatcher. Connection PK selects the carrier. 2026-08-05.
- [ ] **Rate shopping UI** — on order/invoice, show rates from all configured carriers side by side. User selects. Calls `get_shipping_rates` for each active carrier Connection.
- [ ] **Label display/print** — render carrier-returned PDF/GIF/ZPL label. Print button in PackingPanel ship step.
- [ ] **Tracking UI** — tracking status panel on invoice/order detail. Calls `track_shipment`.
- [ ] **Address validation UI** — validate ship-to before label creation. Auto-correct with user confirmation.
- [ ] **Shipping method on transaction** — `config.shipping_method` populated from rate selection.

Priority: Backend **COMPLETE** 2026-08-05. Frontend UI (rate shopping, labels, tracking, address validation): **IMPORTANT** — manual entry works without it. ~1-2 sessions.

---

## 4. Packing Window

- [x] **Pick list generation** — `generate_pick_list(order_id)` returns lines sorted by warehouse/bin with qty to pick (`quantity.remaining`). Backend in `shipping.py`, wired to wcapi/manage. 2026-08-05.
- [x] **Pick list UI** — checklist view with item, qty, warehouse, bin. Click to pick, checkbox all. Sorted for efficient warehouse walk. `PackingPanel.tsx` step 1. 2026-08-05.
- [x] **Pack confirmation UI** — assign picked items to boxes. Add/remove boxes, set weight per box, edit qty packed per line. `confirm_pack()` records to `order.metadata.shipping.packed_lines`. `PackingPanel.tsx` step 2. 2026-08-05.
- [x] **Packing slip template** — markdown template via `seed_template_reports` (output_type='merge'). Renders via MarkdownEditor with `{{tokens}}`. No prices on packing slip. 2026-08-05.
- [ ] **Carrier selection in pack step** — during pack, select carrier and service level. Uses rate shopping from Shipping (#3). Without carrier APIs, user enters manually in ship confirmation.
- [ ] **Label print in pack step** — after pack confirmed + carrier selected, generate and print label. Uses label generation from Shipping (#3).
- [x] **Partial shipment** — `ship_order()` calls `convert_order_to_invoice()` which handles partial transfers. Order `quantity.remaining` decreases, invoice gets `quantity.active` = shipped. Multiple shipments create multiple invoices. 2026-08-05.
- [x] **Ship confirmation** — carrier, tracking #, ship date, freight cost entered in PackingPanel step 3. Stored on invoice `metadata.shipping` and order `metadata.shipping.shipments[]`. Status updated. 2026-08-05.
- [x] **Ship Order button** — ManageActionPanel "Ship Order" opens PackingPanel (full pick/pack/ship workflow) instead of empty dialog. 2026-08-05.
- [x] **quantity.active is the verb** — no `shipped`/`picked` fields. `order_line.quantity.active` = ordered. `invoice_line.quantity.active` = shipped. `order_line.quantity.remaining` = not yet shipped. Docstrings and readmes updated. Scar documented. 2026-08-05.

Priority: Core **COMPLETE** 2026-08-05. Carrier selection + label print depend on Shipping (#3) frontend.

---

## 5. Inventory Adjustment

Backend and frontend complete.

- [x] **Adjustment creation UI** — `InventoryAdjust.tsx` at `/inventory-adjust`. Search items, warehouse select, qty +/-, reason, Apply. WC2 diaInvAdjust pattern. In sidebar.
- [x] **Reason codes** — cycle_count, damage, return, shrinkage, correction, receipt, bom_build, bom_consume, other.
- [x] **Approval workflow** — Action record directed to Responsible Person for Common Parts. Uses existing Action model. No custom workflow.
- [x] **Bulk adjustment** — No CSV upload. External data → JSON (Alice/Athena convert to schema) → Bundle record import. Established pipeline.
- [x] **Cycle count workflow** — Two UIs: `CycleCountPanel` on Item dashboard Counts tab (desktop), `CycleCountMobile.tsx` at `/cycle-count` (phone-sized, barcode/QR camera scan, expected vs actual, Apply). Both create adjustments via pending.
- [x] **Adjustment history** — `GET /api/products/inventory/adjustments/?item_id=N&warehouse_id=N`. Backend done, frontend display pending.
- [x] **Inventory layer viewer** — `InventoryLayersPanel` on Item dashboard Layers tab. FIFO/LIFO cost layers grouped by warehouse. Shows received/issued/remaining, all cost fields, lock status, ext value.

Priority: **COMPLETE** | All items done 2026-08-05.

---

## 6. Product Detail Pages

10+ models exist. Most only accessible via DataBrowser JSON view.
Item detail page already has 3-column header + 10 tabs (Summary, BOM, XRef, Serials, Specs, Layers, Counts, History, Documents, Notes).

- [ ] **Item detail page** — enrich Summary tab (sales history, margins, usage trends). Pricing column needs cost/sell/margin fields editable. Inventory column needs on-hand/on-order/allocated from item.quantity. Images support.
- [ ] **BOM editor** — tree view of bill of materials. Add/remove components, set quantities, calculate rolled-up cost. BomPanel exists (read-only) -- needs edit mode.
- [ ] **Variant manager** — parent item with variant grid (size x color, etc.). Variant-level pricing and inventory.
- [ ] **Catalog/price list editor** — price tiers by customer group. Effective dates. Volume breaks.
- [x] **Serial number tracker** — Serial model rebuilt: 9 statuses (full words), config schema (transaction context), lifecycle methods (receive/issue/return/etc), SerialLog with full-sentence actions. Components: SerialCard, SerialDetailCard, SerialSelectPanel, SerialPanel (multi-context: item/customer/vendor/manufacturer). Setting #545 with actions/statuses/behaviors. Pydantic schema at common/schemas/serial.py.
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

- [x] **Universal print renderer** — JSON-driven `openUniversalPrint()` reads `print_layout` Setting, renders HTML popup, calls `window.print()`. Section types: company_header, address_blocks, meta_row, comments, line_items, totals, conditions, signature, footer. Dot-notation field resolution. Format hints (currency, date, number, percent). 2026-08-05.
- [x] **Print layout seed** — `seed_print_layouts` creates layouts for 7 transaction models (order, invoice, proposal, purchase, work_order, receipt, requisition). Shared building blocks (SELL_ADDRESSES, EXEC_LINE_ITEMS, etc.). 2026-08-05.
- [x] **ReportsDialog wired** — double-click any print report → universal print. Edit Layout button opens print_layout Setting in DataBrowser. Report Setup opens Report record in DataBrowser. No more dead /pdf-designer/ links. 2026-08-05.
- [x] **Cmd+P shortcut** — `useReportShortcuts` hook in DataBrowser. Cmd+P = print primary via universal renderer. Cmd+Opt+P = open ReportsDialog. 2026-08-05.
- [x] **One toolbar** — `DetailToolbar` is the single toolbar. TransactionToolbar archived. Balance display (red when > 0) ported. No dual toolbar bars. 2026-08-05.
- [x] **Alice as report designer** — Users upload PDF/image of desired report → Alice reads it, drafts JSON layout → saves as Setting record → user tweaks in DataBrowser. No report designer needed. 2026-08-05.
- [x] **Packing slip template** — covered in Packing (#4). Seeded via `seed_template_reports`. 2026-08-05.
- [ ] **Shipping label integration** — carrier-generated labels rendered in print workflow. Depends on Shipping (#3) label display. Packing (#4) triggers it.
- [ ] **Batch printing** — select multiple transactions, generate combined PDF.
- [ ] **Scheduled reports** — weekly/monthly report generation via Celery tasks.
- [ ] **Statement generation** — customer statement (open invoices, payments, balance) with date range.
- [ ] **Aged receivables report** — 30/60/90/120+ day aging buckets.
- [x] **Sales tax report** — `TaxReportPrintDocument.tsx`. By jurisdiction, by period. Wired via universal print renderer. 2026-08-05.
- [ ] **Inventory valuation report** — FIFO/LIFO cost layers, total valuation per warehouse.

Priority: **IMPORTANT** | Scope: 1 session per report type

---

## 10. Security Fixes

- [x] **Payment gateway response sanitization** — `Payment.save()` auto-sanitizes via `sanitize_gateway_response()`. Whitelist of safe keys. Non-staff users get gateway fields stripped from API output.
- [x] **Tax exemption cert handling** — cert reference only (tax_exempt_id), expiration date, verified_by, verified_dt fields. Displayed in OrgFinancialsPanel. Cert number stored in JSON settings (not a separate model). 2026-08-05.
- [x] **API rate limiting** — 100 req/min authenticated, 20 req/min anonymous. Payment endpoints: 10 req/min. Webhook: 30 req/min. `ScopedRateThrottle` on payment views.
- [x] **Field-level access control** — `PaymentSerializer.to_representation()` strips `gateway_response`, `id_gateway_transaction`, `id_gateway_payment_intent` for non-staff users.
- [x] **Audit trail enforcement** — `Payment.add_audit_entry()` fixed (was using non-serializable `models.functions.Now()`, now uses `django_now().isoformat()`).
- [x] **Inventory lock timeout** — `dt_locked` field added. `check_lock_expired()` auto-clears after 5 min. `acquire_lock()`/`release_lock()` helpers. `clear_stale_locks` management command.
- [x] **Commission data protection** — Commission is internal-only. Backend: `_STAFF_ONLY_ACTIONS` gate on manage_view, `_require_staff()` on ViewSet actions, `RoleAwareModelSerializer` strips commission from JSON envelopes for non-staff, bootstrap returns empty commissions for non-staff. Frontend: C toggle/columns/totals/panels hidden for non-staff, auto-populate gated, report `role_required: 'admin'`. Auth endpoints now return `is_staff`/`is_superuser`. 2026-08-05.

Priority: **COMPLETE** | All items done 2026-08-05.

---

## 11. Bug Fixes

- [x] **`po_totals.py` import error** — added `from decimal import Decimal` and `from typing import cast`. Fixed.
- [x] **Payment apply race condition** — added `Payment.objects.select_for_update().get(pk=payment.pk)` at top of `apply_payment_to_invoice()`.
- [x] **Inventory layer orphan locks** — `clear_stale_locks` management command created. Supports `--minutes N` and `--dry-run`. Also clears orphaned locks (no `dt_locked`).
- [x] **Parent-child orphan cleanup** — investigated: CASCADE is correctly set on all FK relationships. No fix needed.
- [x] **Multi-currency skeleton** — documented `exchange_rate` as placeholder. No conversion logic until Phase 5. Comment added to prevent premature use.

Priority: **COMPLETE** | All items done 2026-08-05.

---

## 12. Missing Frontend Pages

Backend models exist. No dedicated UI. DataBrowser provides JSON access to all.

- [ ] **Requisition detail** — purchase requisition creation, approval, conversion to PO.
- [ ] **Work Order detail** — work order creation, BOM explosion, labor tracking, completion.
- [ ] **Receipt detail** — receive against PO, inspect, put-away, variance recording.
- [ ] **Discount/promotion engine** — coupon codes, volume discounts, customer-specific pricing rules.

Priority: **MEDIUM** | Scope: 1 session per page

---

## 13. TechNotes / Markdown Templates

Users create and edit documents with live field tokens. Replaces WC2 TechNotes (static HTML blobs, TinyMCE, chapter/section integer addressing).

- [x] **MarkdownEditor component** — view/edit toggle, `{{field.path}}` and `{{field.path|format}}` token syntax, `{{#each lines}}` iteration, token picker dropdown, Submit to WC_HQ button. `React2025/src/components/common/MarkdownEditor.tsx`. 2026-08-05.
- [x] **Wired to Reports** — reports with `output_type='merge'` or `config.action='markdown_template'` open in MarkdownEditor. List context passes all records, detail context passes selected record. 2026-08-05.
- [x] **Template seed** — pick list, packing slip, customer statement templates seeded via `seed_template_reports`. 2026-08-05.
- [x] **Alice documentation** — `readmes/topics/ai/markdown-templates.md` (token syntax, object paths, Submit flow), `readmes/topics/ai/alice-escalation-protocol.md` (capability boundaries, honest escalation to Claude Code). 2026-08-05.
- [ ] **Field path endpoint** — `/wcapi/model_name/field_paths/` to auto-discover JSON subkeys from Pydantic schemas. Currently token picker uses DataBrowser's `allFields` (top-level only).
- [ ] **Template storage** — save user templates as Setting records (purpose='template'). Currently stored in Report config.
- [ ] **Email merge** — same token engine renders email body from template + record.
- [ ] **Keyword/tag links** — `[[keyword]]` syntax auto-links to search results (WC2 TechNotesSetLinks pattern).

Priority: **MEDIUM** | Scope: Core complete. Field path endpoint + email merge = 1 session each.

---

## 14. Commission (cross-cutting — backend, frontend, security, reports)

Full documentation: `readmes/topics/transactions/commissions.md`

- [x] **Backend service** — calculate, populate, accrue, GL. `commission.py`. 2026-08-05.
- [x] **Column UI** — Hidden commission columns (C toggle), per-line rate editing with override protection, footer total. 2026-08-05.
- [x] **Populate trigger** — Auto-populate on save when customer has reps. 2026-08-05.
- [x] **Reports** — Company summary + individual rep statement. `get_commission_report()`. Reports on rep and employee models. 2026-08-05.
- [x] **Security** — Staff-only gates on all endpoints, serializer stripping, frontend hiding, report role gating. 2026-08-05.
- [ ] **CommissionPanel** — UI panel below grid showing rep summary cards, per-line table, selection-aware totals.
- [ ] **Script basis** — execute stored scripts from rep records for custom commission calculations.
- [ ] **Commission payment** — pay accrued commissions, create payment records, update rep financial totals.

Priority: Core **COMPLETE** 2026-08-05. Panel, script, and payment remaining.

---

## Phase 1 Completion Notes — 2026-08-05

### Architectural decisions made during Phase 1

**Pending is the write path for inventory and cash.** No direct mutations. Every inventory change and every payment application creates a PendingInventoryAdjustment or PendingPaymentApplication first, then applies immediately if the target is unlocked. One path, one audit trail. The old direct `payment_application.py` is deprecated — all callers rewired to `payment_pending.py`.

**Lock lifecycle is complete.** `acquire_lock()` → `release_lock()` → pending drains. `check_lock_expired()` auto-clears after 5 minutes. LifecycleMixin `lock()`/`unlock()` overridden on InventoryLayer to honor the pending contract. Management command `clear_stale_locks` for orphan recovery.

**Bulk import uses the established pipeline.** No CSV upload features. External data → JSON conversion (Alice/Athena) → Bundle record import. Same pattern as the contact import pipeline.

**Approval workflow uses Action records.** No custom approval system. Adjustments over threshold create an Action directed to the Responsible Person for Common Parts.

### Also completed 2026-08-05

**Serial model rebuilt.** 9 full-word statuses replacing WC2 cryptic codes. `Serial.config` carries transaction context (customer, vendor, document refs, cost/price, floor plan). Lifecycle methods (`receive()`, `issue_on_invoice()`, `return_from_customer()`, etc.) each update config, set status, and log to SerialLog with full-sentence actions. Setting #545 seeds 13 actions with direction, captures, reversibility. Pydantic schema at `common/schemas/serial.py`.

**Schema-per-model infrastructure.** 79 models now have schema_map Setting records. 73 Pydantic schema files generated from template. `seed_all_schema_maps` command creates both. Added to `seed_freshstart.py`.

**Alice schema question log.** `AliceObservation` category `'schema'` added. `log_schema_question()` service function. `audit_schemas` command samples real data and logs unknown fields. `schema_questions` command lists/clears the queue. 20 weekly Action records (SCHEMA-W01 through SCHEMA-W20) schedule ~4 models/week for review through 2026-12-21.

**Printing & Reports.** Universal print renderer, print layout seed for 7 models, ReportsDialog wired, Cmd+P shortcut, single DetailToolbar, Alice as report designer -- all completed in parallel session.

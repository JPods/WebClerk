# Done — WebClerk 3.0 Backend

What's built, tested, and working. Updated 2026-08-05.

---

## Security
- Gateway response sanitization (`GATEWAY_SAFE_KEYS` whitelist, auto on `Payment.save()`)
- API rate limiting (100/min auth, 20/min anon, 10/min payment, 30/min webhook)
- Field-level RBAC (`RoleAwareModelSerializer` strips sensitive fields for non-staff)
- Commission data protection (3-layer: `_STAFF_ONLY_ACTIONS`, `_require_staff()`, serializer stripping)
- Inventory lock lifecycle (`acquire_lock`/`release_lock`, 5-min auto-expire, `clear_stale_locks`)
- Audit trail (`Payment.add_audit_entry()`, `metadata.tax_decisions`, `metadata.shipping`)
- Auth returns `is_staff`/`is_superuser` on login + /me

## Payment Processing
- `SpreedlyService` — purchase, authorize, capture, void, credit, refund (void-then-credit)
- `process_payment` / `refund_payment` helper functions
- Payment gateway Setting #625 (Spreedly credentials, supported gateways)
- Webhook endpoint `/payments/webhooks/spreedly/`
- Token-in-a-token: WC3 never sees card data

## Tax Calculation
- Per-line tax calc in `totals.py` (header rate × taxable lines)
- Customer → jurisdiction → rate flow (`applyCustomerDefaults.ts`)
- Tax exemption (exempt code on customer zeroes tax)
- Tax on shipping (jurisdiction `tax_rate_on_shipping`)
- `line_type` field (product/tax/shipping/discount) routes to correct total bucket
- Tax audit trail (`metadata.tax_decisions` with dt, rate, jurisdiction, source per line)
- TaxJurisdiction model ready for seed data

## Inventory
- `PendingInventoryAdjustment` — one write path for all inventory changes
- `acquire_lock`/`release_lock` on inventory layers
- `check_lock_expired()` auto-clears after 5 minutes
- `clear_stale_locks` management command
- `InventoryAdjust` service with reason codes
- Cycle count workflow (desktop + mobile)
- Inventory layers (FIFO/LIFO cost layers, received/issued/remaining)
- Bulk import via Bundle pipeline (no CSV upload)

## Packing & Shipping
- `generate_pick_list(order_id)` — lines sorted by warehouse/bin
- `confirm_pack(order_id, packed_lines)` — records box contents in metadata
- `ship_order(order_id, shipping_data)` — order→invoice conversion = ship event
- `get_shipment_status(order_id)` — shipped vs pending line counts
- Partial shipment via conversion chain (multiple invoices from one order)
- Shipping metadata on both order and invoice

## Carrier API Integrations
- `CarrierBase` abstract class with registry pattern (`@register_carrier`)
- Surcharge engine (fuel factor, handling charge, markup percent)
- `_carrier_action()` dispatcher in manage_view (5 actions)
- **UPS** — OAuth 2.0 REST: rating (Shop), shipping (labels), tracking, address validation, void
- **FedEx** — OAuth 2.0 REST: rating, shipping (labels), tracking, address validation, cancel
- **USPS** — OAuth 2.0 REST: pricing v3, labels v3, tracking v3, address validation v3
- **DHL Express** — Basic Auth REST: rates, shipments (labels), tracking
- Connection records seeded for all four (draft status, user fills in credentials)

## Transaction Quantity Model
- `quantity.active` is the verb of the document (ordered/shipped/purchased/received)
- Three canonical keys only: `active`, `staged`, `remaining`
- No `shipped`/`picked`/`packed` keys — document type gives quantity meaning
- Transfer chain: `source.remaining -= transfer_qty`, `target.staged = transfer_qty`
- `children_active` tracker for remaining calculation
- `normalize_quantity_map()` preserves all canonical keys

## Commission
- `calculate_commission()` — per-line from rep rate, item override, customer override
- `populate_commission()` — auto-populate on save when customer has reps
- `accrue_commission()` — GL journal entries for accrual
- `get_commission_report()` — period-based: company summary + individual rep statement
- Staff-only at every layer (manage_view, ViewSet, serializer, bootstrap, frontend)

## Conversion Chain
- `convert_order_to_invoice()` — handles inventory, commission carry-forward, parent/child linkage
- `convert_proposal_to_order()` — quantity transfer, line copy
- `convert_order_to_purchase()` — cross-side conversion
- `spawn_workorder()` — BOM explosion
- All through `transfer_utils.py` — one path for quantity flow

## Printing & Reports
- Universal print renderer (`UniversalPrint.ts`) — JSON-driven HTML popup
- 7 transaction print layouts seeded (`seed_print_layouts`)
- Cmd+P = primary report, Cmd+Opt+P = report selector
- Alice as report designer (user uploads PDF/image → Alice drafts JSON layout)
- `ReportsDialog` wired to universal print

## Markdown Templates (TechNotes)
- `MarkdownEditor` component — view/edit/template with `{{field.path}}` tokens
- `{{field.path|format}}` with currency/date/number/percent hints
- `{{#each lines}}...{{/each}}` for list iteration
- `resolveTokens()` exported for standalone use
- Submit to WC_HQ button (Action record for Alice to bundle upstream)
- 3 template reports seeded: pick list, packing slip, customer statement

## Serial Tracker
- 9 full-word statuses (available → assigned → installed → returned → etc.)
- Lifecycle methods (`receive()`, `issue_on_invoice()`, `return_from_customer()`, etc.)
- SerialLog with full-sentence actions
- `Serial.config` carries transaction context (customer, vendor, docs, cost/price)
- Setting #545 with 13 actions (direction, captures, reversibility)
- Pydantic schema at `common/schemas/serial.py`

## Schema Infrastructure
- 79 schema_map Setting records
- 73 Pydantic schema files
- `seed_all_schema_maps` command
- Alice schema question log (`AliceObservation` category='schema')
- 20 weekly review Action records (SCHEMA-W01 through SCHEMA-W20)

## Connection Records
- `conn-alice-claude` — Alice → Claude Code escalation (Action queue)
- `conn-wchq-upstream` — user template contributions to WC_HQ
- `conn-local-server` — local server template (IT15/Mac Mini)
- `conn-carrier-ups/fedex/usps/dhl` — carrier API credentials (draft)

## Alice
- Escalation protocol (`alice-escalation-protocol.md`)
- Capability boundaries documented (what she can do vs escalate)
- Markdown template documentation in her vector store
- Scale hardware specs for evaluation
- Carrier setup walkthrough
- Vector store: 5,989 chunks indexed

---

*Each section is independently verifiable by reading the code at the paths listed in `todo-go-live.md`.*

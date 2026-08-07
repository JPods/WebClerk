# WC2 → WC3 Harvest Plan — Staged Implementation
**Written:** 2026-07-03 by Claude Code + Allie + Alice
**Based on:** Three mining sweeps — WC2 features, 4D best practices, WC3 gap analysis

---

## How This Plan Is Organized

Five stages, each builds on the previous. Each stage has a theme, a list of items with source pointers, and what "done" looks like. Items within a stage can be worked in parallel.

**Guiding principles:**
- Port intent, not implementation (from legacy strategy doc)
- Backend is source of truth (existing WC3 rule)
- All CRUD through wcapi (existing WC3 rule)
- Time tracking uses outside apps/APIs — not built in WC3
- Break and fix now — no legacy carried forward

---

## Stage 1: Data Integrity and Safety
**Theme:** Fix gaps that can cause data loss or corruption in production.
**When:** Before any external user touches WC3.

### 1.1 Invoice Type Enum
**Gap:** No `invoice_type` column on Invoice. Buried in JSONB `refs.source`.
**Source:** WC2 Classes `cLine`, 4D InvoicesDemo `catalog.4DCatalog`, Vue2020 invoice views
**What to build:**
- Add `invoice_type` CharField with TextChoices: `invoice`, `proforma`, `credit_note`, `deposit`
- Per-type numbering sequence in SystemSetting (track `last_invoice_number`, `last_proforma_number`, etc.)
- Guard: credit notes cannot be marked as paid; credit notes reduce AR, not increase
- Migration: populate from `refs.source.invoice_type` where it exists
**Done when:** `Invoice.objects.filter(invoice_type='credit_note')` works. Reports can split by type.

### 1.2 Re-enable Version Conflict Checking
**Gap:** `save_view.py` has `assert_version()` and `VersionConflictError` but the check is commented out.
**Source:** WC2 Classes `cProcess` (optimistic lock), EA_Invoices `action_Save_Optimistic.4dm`
**What to build:**
- Re-enable `assert_version()` in `save_view.py`
- Frontend: track record version in React state, send with save request
- Return structured error: `{code: 'version_conflict', message: 'Record modified by {user} at {time}'}`
- Handle "entity gone" case: `{code: 'not_found', message: 'Record was deleted'}`
**Done when:** Two users editing the same Invoice simultaneously get a conflict notification, not silent overwrite.

### 1.3 Webhook Deduplication
**Gap:** `gateway_payment_intent_id` has no unique constraint. Duplicate webhooks create duplicate Payments.
**Source:** Twilio Example SID-based dedup, 4D best practice (structured result objects)
**What to build:**
- Add `unique=True` on `Payment.gateway_payment_intent_id` (or unique constraint)
- Use `get_or_create(gateway_payment_intent_id=sid)` in webhook handler
- Add `external_event_id` field to any model receiving external webhooks
**Done when:** Duplicate Stripe webhook for same intent is idempotent — no duplicate Payment created.

### 1.4 PaymentApplication Guard
**Gap:** `PaymentApplication.clean()` validates over-application but `clean()` isn't called on `save()`.
**Source:** WC2 Methods `Ledger_PaySave.4dm`, EA_Invoices cascade-delete-in-transaction pattern
**What to build:**
- Call `self.full_clean()` in `PaymentApplication.save()` or add a `pre_save` signal
- Verify: applied amounts across all applications for a Payment cannot exceed Payment.amount
**Done when:** Over-application raises ValidationError on save, not just on explicit `full_clean()`.

### 1.5 AuditLog Auto-Wiring
**Gap:** `AuditLog` model exists but nothing writes to it automatically.
**Source:** WC2 Classes `cChanges` (TallyChange with JSONB history[]), 4D best practice
**What to build:**
- Universal `post_save` signal on BaseModel that diffs old vs new field values
- Write `AuditLog.log_action(model, record_id, action='update', changes={field: {old, new}})`
- Skip computed/cached fields from diff (use a `AUDIT_EXCLUDE_FIELDS` list per model)
- Wire for at least: Invoice, Payment, Contact, Action, Item
**Done when:** Every wcapi-mediated save of an Invoice captures which fields changed and who changed them.

---

## Stage 2: Core Commerce Workflows
**Theme:** The daily operations that warehouse and office staff need.
**When:** Before WC3 replaces WC2 for any real user.

### 2.1 Document Promotion Chain (Proposal → Order → Invoice)
**Gap:** No "Make Order" or "Make Invoice" one-click promotion.
**Source:** Vue2020 `OrderDetail.vue` (Make Invoice), `ProposalDetail.vue` (Make Order), WC2 `cChoices` lifecycle hooks
**What to build:**
- `promote_proposal_to_order` manage action — copies header + lines, links back via refs
- `promote_order_to_invoice` manage action — same pattern
- React: "Make Order" / "Make Invoice" button on detail view
- Guard: only promote if all lines have valid pricing; warn on partial promotion
**Done when:** User can go Proposal → Order → Invoice with one click at each step. Full audit trail of the chain.

### 2.2 Payment Application UI
**Gap:** PaymentApplication model exists; no operator-facing UI to apply payments to invoices.
**Source:** WC2 T1/ApplyPayment, T28/diaMakePay, T28/diaOffSetInvoic
**What to build:**
- Payment application page: select payment, see open invoices, apply amounts
- Support partial application (split one payment across multiple invoices)
- Support credit offset (apply credit note against invoice)
- AR aging display: current, 30, 60, 90, 120+ days
**Done when:** Bookkeeper can receive a check and apply it to the correct invoices through the browser.

### 2.3 Returns / Voids / Credit Memos
**Gap:** No reverse-transaction workflow in WC3.
**Source:** WC2 Methods `voidCurInvoice`, `CMAComplexProcess`, `ApprvlCredit`
**What to build:**
- `void_invoice` manage action — reverses GL entries, restores inventory, marks void
- `create_credit_note` manage action — creates credit_note type invoice with negative lines
- `void_payment` — unapplies PaymentApplications, marks Payment void
- Approval workflow: credit notes over threshold require manager approval (Action-based)
**Done when:** User can void an invoice, create a credit memo, and apply it to a future invoice.

### 2.4 Pricing / Discount Engine
**Gap:** No multi-level price hierarchy. Line pricing is flat.
**Source:** WC2 Methods `CalcDiscountedPrice`, `PricingLvlAddType`, `PriceMatrix_FillArrays`, WC2 Classes `cLine`
**What to build:**
- PriceLevel model: customer type → price multiplier or fixed price per item
- PriceMatrix: item × customer-type × qty-break → price
- Discount approval workflow: discounts below margin floor require approval (Action-based)
- Line calculation: apply price level first, then line discount, then order discount
**Done when:** Different customer types see different prices. Margin floor is enforced.

### 2.5 Print Views (Invoice / Order / Proposal PDF)
**Gap:** No browser-printable document output.
**Source:** Vue2020 `InvoicePrint.vue`, `OrderPrint.vue`, `ProposalPrint.vue`
**What to build:**
- Server-side PDF generation via Django template → WeasyPrint or ReportLab
- Company letterhead, bill-to/ship-to, line items, totals, payment terms
- Email PDF as attachment (connects to email system)
- Per-org template customization via Setting
**Done when:** User can print or email a professional invoice from the browser.

### 2.6 N+1 Query Fix
**Gap:** WCAPIGetView list path has no select_related/prefetch_related.
**Source:** 4D Contexts example (context pinning), ORDA best practices
**What to build:**
- Add `select_related` and `prefetch_related` to all WCAPIGetView list queries
- Audit all `to_dict()` paths for lazy FK loads
- Add query count logging in dev mode to catch regressions
**Done when:** Contact list with 100 records loads with <10 queries, not 300+.

---

## Stage 3: databrowser Evolution (r25)
**Theme:** Make databrowser the power-user tool that replaces all 40+ admin pages.
**When:** Alongside Stage 2; these are UX improvements, not data model changes.

### 3.1 Per-User Layout Persistence
**Gap:** One global layout per model. No user-specific column configurations.
**Source:** EA_Invoices `Listbox_Setting` table, WC2 per-user column settings
**What to build:**
- Add optional `contact_id` FK to Setting model
- Relax unique constraint to `(parent_model, purpose, contact_id)`
- Hook: fetch user-specific setting first, fallback to global
- Named views become user-owned; shared views are contact_id=null
**Done when:** Two users can see different column arrangements for the same Invoice list.

### 3.2 Operator Vocabulary Consolidation
**Gap:** Filter operators duplicated in two places in wcapi.py; DataGrid color rules use different vocabulary.
**Source:** 4D QueryClass `makeOperatorPopUp`, EA_Invoices `TableQuery`
**What to build:**
- Single `FILTER_OPERATORS` dict in shared constants (Python + TypeScript)
- Map: `{label: "Contains", key: "contains", django_lookup: "icontains", applies_to: ["text"]}`
- DataGrid color rules use same vocabulary
- Search bar shows operators appropriate to field type (text→contains, number→gt/lt, date→range)
**Done when:** One source of truth for filter operators used by wcapi, DataGrid, and search UI.

### 3.3 Widget Type Schema
**Gap:** Widget type contract between seed_field_access.py and BehaviorField.tsx is implicit.
**Source:** Dynamic-Forms-Starter `DefaultJsonForm.json`, UI-with-Classes widget hierarchy
**What to build:**
- `WIDGET_TYPES` schema file (JSON or TypeScript) defining all types with defaults
- Field types: text, number, currency, email, phone, url, boolean, date, timestamp, select, lookup, json, textarea, image, readonly
- Each type specifies: default width, sizingMode (fixed/grow), filterWidget, sortable, editable
- `dataSourceTypeHint` override per field in layout Setting
**Done when:** Adding a new widget type means adding one entry to the schema; both Python seeder and React renderer read it.

### 3.4 doSafeSelect After Delete
**Gap:** After delete, detail pane goes blank (selectedRecord = null).
**Source:** EA_Contacts, EA_Tasks, EA_Invoices, UI-with-Classes `listbox.doSafeSelect`
**What to build:**
- After delete: if next record exists, select it; else select previous; else clear
- Three lines of code in `handleDeleteRecord` in usedatabrowser.ts
**Done when:** Deleting a record in a list auto-selects the adjacent record.

### 3.5 Reset Layout to Defaults
**Gap:** Seeded `initial` view exists but no UI button to restore it.
**Source:** UI-with-Classes `saveProperties/restoreProperties`
**What to build:**
- "Reset Layout" button in databrowser toolbar
- Loads the `initial` named view from seed data
- Confirm dialog: "Reset to default layout? Your custom layout will be lost."
**Done when:** User can click one button to restore the factory layout.

### 3.6 Validation Error Accumulation
**Gap:** databrowser saves have no client-side validation; server returns first error only.
**Source:** EA_Tasks `validateTaskFields.4dm`, 4D best practice
**What to build:**
- Client-side: Zod schema per model (or generated from field behaviors)
- Collect all errors into field-keyed dict, display all at once
- Server-side: DRF serializer validates all fields, returns all errors (already DRF default behavior)
**Done when:** Saving an invalid record shows all field errors simultaneously, not one at a time.

### 3.7 Employee Home Dashboard
**Gap:** No cross-model workbench with shared date-range filter.
**Source:** Vue2020 `EmployeeHome.vue`, `EmployeeDaySearchForm.vue`
**What to build:**
- Single page: date-range picker at top
- Sub-panels: my customers, my orders, my proposals, my invoices, my actions
- All panels react to the date-range filter simultaneously
- Counts per panel shown in tab headers
**Done when:** User opens WC3 and sees their day's work in one view.

### 3.8 Unified Search Hub
**Gap:** Search is per-model in databrowser; no cross-model search.
**Source:** Vue2020 `Search.vue` (8 parallel widgets), QOM command palette
**What to build:**
- Cmd+K command palette: search contacts, invoices, orders, products, actions
- Results grouped by model with counts
- Click navigates to databrowser for that model with the record selected
**Done when:** User types Cmd+K, types a customer name, sees matching contacts, orders, and invoices.

---

## Stage 4: Extended Commerce
**Theme:** Features that expand WC3's capability beyond basic order-to-invoice.
**When:** After Stages 1-3 are stable. These are business-value additions.

### 4.1 Commission / Rep Management
**Source:** WC2 Methods `CommissionCalculator`, `CommissionByMargin`, `CommissionRateCalc`
**What to build:** CommissionRule model (rep × margin band → rate), CommissionEntry model per invoice line, recalculate on price change, reports by rep and period.

### 4.2 Serial Number Tracking
**Source:** WC2 Methods `Srl_IssueSale`, `Srl_RcvrPO`, `Srl_Transaction`
**What to build:** SerialNumber model (item FK, serial, status, current_owner), assign on PO receipt, issue on sale, track history per serial.

### 4.3 BOM / Kit Assembly
**Source:** WC2 Methods `BOM_DoBOM`, `BOM_ChildCost`, `BOM_Consume`, EA_Recipes ingredient pattern
**What to build:** BOMComponent model (parent_item, child_item, qty, unit), cost rollup, loop detection, consume components on work order completion.

### 4.4 QA / Condition Reports with Photo Upload
**Source:** Vue2020 `QAForm.vue`, `QAList.vue`, WC2 Methods `QA_AddQuestions`
**What to build:** QuestionTemplate model, Answer model (FK to any document), photo attachment via Document model, print-formatted condition report.

### 4.5 Cloneable Proposals / Orders
**Source:** Vue2020 `CloneableProposalsHome.vue`, WC2 `WCapiTask_Clone.4dm`
**What to build:** `clone_transaction` manage action — search past proposals by type/customer, preview, one-click clone with new dates and customer.

### 4.6 Product Key-Tag Tree
**Source:** Vue2020 `ProductTree.vue` (vue-jstree), WC2 Methods `KeyWordsMake`
**What to build:** Hierarchical key-tag browser in React (tree component), click leaf → filter item list, drag items into order/proposal line entry.

### 4.7 Kanban Board for Actions
**Source:** Vue2020 `KanbanPad.vue`, `TaskCard.vue`
**What to build:** Four-column drag-drop board (Backlog / In Progress / Review / Done) over Action model, filtered by assigned user and date range.

### 4.8 Barcode / Scan-to-Action
**Source:** WC2 Methods `WOBarCodeReceive`, `BarcodeArray128Setup`, `PKBarCodeItem`
**What to build:** Mobile-friendly scan flow: camera or scanner input → lookup item/serial/order → action (receive, pick, verify). Server generates Code128/QR for labels.

### 4.9 AR Statement Generation
**Source:** WC2 T2/StatemntLines, T28/incDateDollar
**What to build:** Customer statement PDF: open invoices, payments, aging buckets (current/30/60/90/120+), running balance. Email to customer.

### 4.10 Period Close (Day/Month)
**Source:** WC2 T1/EOM, T1/OpenClose
**What to build:** Day open/close discipline — gate certain operations (void, backdate) after period close. Month-end close: lock period, run tallies, generate GL journal.

---

## Stage 5: Integration and Platform
**Theme:** Connect WC3 to the outside world.
**When:** After core commerce is stable. These are platform-level capabilities.

### 5.1 Connection Execution Layer
**Source:** 4D FileTransfer_Class unified interface, WC2 Methods `Sync_*`
**What to build:** Base class `ConnectionExecutor` with `upload()`, `download()`, `list()`. Subclasses: `FTPExecutor`, `SFTPExecutor`, `HTTPSExecutor`, `S3Executor`. Connection model's `type` field selects executor. Progress reporting via Celery task status.

### 5.2 Import Wizard (HTTP)
**Source:** Kirk dataImporter (4-step wizard), WC2 T4/ListItemImport
**What to build:** Upload file → preview rows → map columns to model fields → validate → execute import. React wizard with 4 steps. Server-side: parse CSV/TSV/XLSX, return preview, accept column mapping, execute with dry-run option.

### 5.3 EDI Pipeline
**Source:** WC2 Methods `EDI_OrdAdd`, `EDI_PackInvoice`, `EDI_DupPONum`
**What to build:** Receive 850 POs from trading partners, parse to Order, send 810 invoices, 997 acknowledgments. Duplicate PO detection. Map via Connection model.

### 5.4 Email Stack (SMTP/IMAP)
**Source:** WC2 Methods `SMTP_SendMsg`, `IMAP_Receive`, `Email_Governor`, EA_Email Composer
**What to build:** Per-org SMTP settings (not global), send invoice/order/confirmation emails with PDF attachment, inbound email processing (IMAP poll), opt-out management, bounce handling, rate limiting.

### 5.5 Shipping / Carrier Integration
**Source:** WC2 Methods `UPS_TimeInTransit`, `FlxShip_OpenPrc`, `ShipmentTracking`
**What to build:** Carrier rate shopping via API (UPS, FedEx, USPS), shipment tracking, 3rd-party billing, freight zone lookup. Wire through Connection model.

### 5.6 Pick/Pack/Ship Workflow
**Source:** WC2 Methods `PKALDefine`, `PKLineIntoBox`, `PKPalletPack`, T1/Packing, T3/Shippable
**What to build:** Shippable filter (order lines ready to ship), pick list generation, scan items into boxes, build pallets, assign load tags, print packing lists/labels, mark shipped.

### 5.7 Accounting System Export
**Source:** WC2 Methods `Payment_ExportToPeachtree`, `SalesJournalsiLo`
**What to build:** GL journal export to QuickBooks/Sage/Xero. Sales journal, purchase journal, cash journal. Connection model drives the protocol (file export vs API push).

### 5.8 B2B Exchange / Customer Portal
**Source:** WC2 Methods `B2B_Exchange`, `NxPvOrders`, `NxPvInvoices`
**What to build:** Customer self-service portal: view own orders/invoices/proposals/service requests. Vendor portal: item availability queries, PO status polling. Wire through external user RBAC (field_access Settings with query_scope).

### 5.9 Demand Forecasting
**Source:** WC2 Methods `ItemFutureNeed`, `ForecastTrendReport5Yr`
**What to build:** Reorder point calculation based on sales velocity, 5-year trend chart, low-stock alerts, suggested PO generation. Alice monitors and recommends.

### 5.10 Ad-Source / Campaign Attribution
**Source:** WC2 Methods `AdSourceCalc`, `TallyAdEffects`, `Tally_AdSales`
**What to build:** Track which ad source drove a contact/lead/order. Cost-per-acquisition by campaign. ROI by campaign (matches existing WC3 reporting focus: campaigns + margin velocity).

---

## Cross-Stage Items (Apply Throughout)

### Structured Result Objects
Every internal service call and wcapi response uses `{success, error_code, message, data}` envelope. Already strong — maintain discipline as new manage actions are added.

### Named-Action Controller
Backend `_ACTION_DISPATCH` is clean. As new manage actions are added (promote, void, clone, apply payment), they follow the same string → handler pattern.

### Test Coverage
Every harvested feature gets: unit test (model logic), integration test (wcapi round-trip), and a checklist entry in the parity test matrix.

### Alice Observations
Every new feature domain gets Alice observations logged at implementation time — she builds her pattern recognition as the features are built, not after.

---

## Source Cross-Reference

| Stage | Primary WC2 Sources | Primary 4D Example Sources |
|-------|---------------------|---------------------------|
| 1 | cProcess, cChanges, cLine, Ledger_PaySave | EA_Invoices (optimistic lock), Twilio (SID dedup) |
| 2 | WCapi*, GL_*, WO_Transfer*, CalcDiscountedPrice | EA_Invoices (cascade rollup), Vue2020 (print views) |
| 3 | cRelated, TableShow, QueryEditor | UI-with-Classes, Dynamic-Forms-Starter, EA_Contacts/Tasks |
| 4 | Commission*, Srl_*, BOM_*, QA_*, KeyWords* | EA_Recipes (BOM), EA_Tasks (Kanban), Kirk (import) |
| 5 | Sync_*, EDI_*, SMTP_*, UPS_*, PK_*, B2B_* | FileTransfer_Class, Twilio, 80-Signal |

---

## What NOT to Harvest

- **4D desktop UI mechanics** — form objects, listbox array binding, widget inheritance. React has its own component model.
- **4D-specific sync protocol** — WC3's Connection/Bundle model is better designed. Harvest the conflict resolution logic, not the protocol.
- **WC2's cron system** — WC3 has Celery+Beat. Harvest the job definitions, not the scheduler.
- **Time tracking** — outside apps/APIs per Bill's decision.
- **SSL/ACME cert management** — cloud hosting delegates this.
- **WC2's payment gateway code** — WC3 has Stripe. Harvest the multi-gateway pattern if a second gateway is needed.

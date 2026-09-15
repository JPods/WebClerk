# TSX Page Reasons — Which Models Need Custom Pages and Why

**Purpose:** Decide which Django models get custom `.tsx` List/Detail pages vs DataBrowser.
**Rule:** Custom pages for models where users need special features (related data, transfers, printing, line editing). DataBrowser for admin/config models where CRUD is enough.

**Last Updated:** 2026-07-10
**Owner:** Bill — update as decisions are made.

---

## Legend

- **Route:** Current sidebar/route status (`custom` = uses .tsx page, `DB` = DataBrowser, `none` = no route)
- **Detail Required:** Y = needs custom detail, N = DataBrowser is fine
- **List Required:** Y = needs custom list, N = DataBrowser is fine
- **Existing .tsx:** Files already in the folder
- **Helpful .tsx:** What might be worth building

---

## Core App

| Model | Route | Detail | List | Existing .tsx | Helpful .tsx |
|-------|-------|--------|------|---------------|-------------|
| **contact** | custom | Y — communications panel, org links, transaction history | Y — search, quick-add, merge duplicates | ContactDetail.tsx, ContactDetail2.tsx, ContactDetail3.tsx, ContactList.tsx | — |
| **action** | custom | Y — kanban integration, project linking, assigned-to | Y — status filters, project grouping | ActionDetail.tsx, ActionList.tsx | — |
| **setting** | DB | N — JSON config, admin only | N — admin only | SettingDetail.tsx, SettingList.tsx, SettingDisplay.tsx | — |
| **template** | DB | N — admin only | N — admin only | TemplateDetail.tsx, TemplateList.tsx, TemplateDisplay.tsx | — |
| **report** | DB | N — admin only | N — admin only | ReportDetail.tsx, ReportList.tsx, Report.tsx, ReportDisplay.tsx | — |
| **pending** | none | N — ephemeral queue records | N — view in DataBrowser if needed | (none) | — |
| **apilog** | custom | Y — request/response detail | Y — filter by status, endpoint, user | APILogDetail.tsx, APILogList.tsx | — |
| **auditlog** | none | N — read-only log | N — DataBrowser sufficient | (none) | — |
| **notification** | none | N | N | (none) | NotificationList.tsx — inbox view |
| **userprofile** | none | N — use /profile page | N | (none) | — |
| **userdailylog** | DB | N | N | (none) | — |
| **roleconfig** | DB | N — admin RBAC | N | (none) | — |
| **modelroleconfig** | DB | N — admin RBAC | N | (none) | — |
| **modellinkconfig** | DB | N — admin config | N | (none) | — |
| **refsmismatchlog** | DB | N — data integrity audit | N | (none) | — |
| **softdeleteledger** | DB | N — admin audit | N | (none) | — |

## Orgs App

| Model | Route | Detail | List | Existing .tsx | Helpful .tsx |
|-------|-------|--------|------|---------------|-------------|
| **customer** | custom | Y — financials, credit, sales history, communications, transactions, contacts | Y — search, sort, sales metrics | CustomerDetail.tsx, CustomerList.tsx, CustomerDashboard.tsx, CustomerDataPanel.tsx, CustomerHeader.tsx | — |
| **vendor** | custom | Y — purchase history, terms, contacts, communications | Y — search, PO status | VendorDetail.tsx, VendorList.tsx | — |
| **employee** | DB | N — basic org record | N — small list | EmployeeDetail.tsx, EmployeeList.tsx | — |
| **manufacturer** | DB | N — basic org record | N — small list | ManufacturerList.tsx, ManufacturerDisplay.tsx | — |
| **rep** | DB | N — basic org record | N — small list | RepList.tsx, RepDisplay.tsx | RepDetail.tsx — commission tracking |
| **orgbase** | none | N — abstract base | N | (none) | — |

## Products App

| Model | Route | Detail | List | Existing .tsx | Helpful .tsx |
|-------|-------|--------|------|---------------|-------------|
| **item** | custom | Y — pricing tiers, BOM, inventory layers, serials, xrefs, org-items, specifications | Y — search, inventory status, margin velocity | ItemDetail.tsx, ItemList.tsx, ItemDashboard.tsx, BOMSection.tsx | — |
| **billofmaterial** | DB | ? — multi-level BOM tree view | ? — parent item grouping | BillOfMaterialDetail.tsx, BillOfMaterialList.tsx | BOMTreeView.tsx |
| **serial** | DB | ? — lifecycle tracking (receive, issue, return, warranty) | ? — status filters, item grouping | SerialDetail.tsx, SerialList.tsx, SerialDisplay.tsx | — |
| **catalog** | DB | N — admin config | N | CatalogDetail.tsx, CatalogList.tsx, CatalogDisplay.tsx | — |
| **catalogline** | none | N — child of catalog | N | (none) | — |
| **inventorylayer** | none | N — system-managed FIFO/LIFO stacks | N — view in Inventory Dashboard | (none) | — |
| **inventoryreservation** | none | N — system-managed | N | (none) | — |
| **inventorycheck** | none | N — use Reconcile tab in Inventory Dashboard | N | (none) | — |
| **warehouse** | DB | N — basic config | N | WarehouseDetail.tsx, WarehouseList.tsx, WarehouseDisplay.tsx | — |
| **orgitem** | DB | N — vendor/customer item cross-ref | N | OrgItemDetail.tsx, OrgItemList.tsx, OrgItemDisplay.tsx | — |
| **itemxref** | DB | N — cross-reference mapping | N | ItemXrefDetail.tsx, ItemXrefList.tsx, ItemXrefDisplay.tsx | — |
| **variant** | DB | N — item variants | N | VariantDetail.tsx, VariantList.tsx, VariantDisplay.tsx | — |
| **service** | DB | N — service items | N | ServiceDetail.tsx, ServiceList.tsx, ServiceDisplay.tsx | — |
| **specification** | DB | N — item specs | N | SpecificationDetail.tsx, SpecificationList.tsx, SpecificationDisplay.tsx | — |
| **usage** | DB | N — usage tracking | N | UsageDetail.tsx, UsageList.tsx, UsageDisplay.tsx | — |
| **flow** | DB | N — workflow config | N | FlowDetail.tsx, FlowList.tsx, FlowDisplay.tsx | — |
| **itemusage** | none | N | N | (none) | — |

## Transactions App

| Model | Route | Detail | List | Existing .tsx | Helpful .tsx |
|-------|-------|--------|------|---------------|-------------|
| **proposal** | custom | Y — lines, customer, contacts, transfer to order, print | Y — status filters, customer, totals | ProposalDetail.tsx, ProposalList.tsx, ProposalLineDetail.tsx, ProposalLineList.tsx | — |
| **order** | custom | Y — lines, customer, payments, contacts, transfer to invoice/purchase, shipping, print, actions/tasks | Y — status filters, customer, delivery tracking | OrderDetail.tsx, OrderList.tsx, OrderLineDetail.tsx, OrderItemSearch.tsx, OrderLineEditor.tsx, OrderLineForm.tsx, OrderStatus.tsx | — |
| **invoice** | custom | Y — lines, customer, payments, apply payments, GL posting, print | Y — status, aging, customer, totals | InvoiceDetail.tsx, InvoiceList.tsx, InvoiceLineDetail.tsx, InvoiceItemSearch.tsx, InvoiceLineEditor.tsx, InvoiceLineForm.tsx, InvoiceStatus.tsx | — |
| **purchase** | custom | Y — lines, vendor, receive goods, cost tracking, print | Y — status, vendor, PO amounts | PurchaseDetail.tsx, PurchaseList.tsx, PurchaseLineDetail.tsx, PurchaseStatus.tsx | — |
| **payment** | custom | Y — application to invoices, customer, GL posting | Y — status, customer, amounts | PaymentDetailPage.tsx, PaymentListPage.tsx | — |
| **receipt** | custom | Y — lines from PO, inventory receiving | Y — PO reference, vendor | ReceiptDetail.tsx, ReceiptList.tsx | — |
| **workorder** | custom | Y — production steps, lines, project link | Y — status, project grouping | WorkorderDetail.tsx, WorkorderList.tsx, WorkOrderLineDetail.tsx | — |
| **requisition** | custom | Y — internal request, approval flow | Y — status, requester | RequisitionDetail.tsx, RequisitionList.tsx | — |
| **project** | custom | Y — linked orders/WOs, gantt, actions | Y — status, timeline | ProjectDetail.tsx, ProjectList.tsx | — |
| **proposalline** | none | N — embedded in proposal detail | N | ProposalLineDetail.tsx | — |
| **orderline** | none | N — embedded in order detail | N | OrderLineDetail.tsx | — |
| **invoiceline** | none | N — embedded in invoice detail | N | InvoiceLineDetail.tsx | — |
| **purchaseline** | none | N — embedded in purchase detail | N | PurchaseLineDetail.tsx | — |
| **receiptline** | none | N — embedded in receipt detail | N | (none) | — |
| **workorderline** | none | N — embedded in workorder detail | N | WorkOrderLineDetail.tsx | — |
| **requisitionline** | none | N — embedded in requisition detail | N | (none) | — |
| **paymentapplication** | none | N — system-managed junction | N | (none) | — |
| **pendingpaymentapplication** | none | N — system queue | N | (none) | — |
| **paymentmethod** | DB | N — admin config (cash, check, CC, ACH) | N | (none) | — |
| **paymentterm** | DB | N — admin config (Net 30, etc.) | N | (none) | — |
| **inventoryadjustment** | none | N — use Inventory Dashboard Adjust tab | N | InventoryAdjustmentList.tsx | — |

## Accounts App

| Model | Route | Detail | List | Existing .tsx | Helpful .tsx |
|-------|-------|--------|------|---------------|-------------|
| **glaccount** | DB | ? — chart of accounts, balance summary | ? — tree view by account type | GLAccountDetail.tsx, GLAccountList.tsx | GLAccountTree.tsx |
| **gljournal** | DB | ? — journal entries, debit/credit detail | ? — date range, posted/unposted | GLJournalDetail.tsx, GLJournalList.tsx, GLJournal.tsx, GLJournalDisplay.tsx | — |
| **ledger** | DB | N — aggregated view | ? — period summaries | LedgerList.tsx, LedgerDisplay.tsx, ReceivableList.tsx, TallySummaryList.tsx, SalesDimensionTallyList.tsx, InventoryUsageTallyList.tsx, TallyRegistryList.tsx | — |
| **audit** | DB | N — read-only | N | AuditDetail.tsx, AuditList.tsx, Audit.tsx, AuditDisplay.tsx, AuditForm.tsx | — |
| **currency** | DB | N — admin config | N | CurrencyDetail.tsx, CurrencyList.tsx, Currency.tsx, CurrencyDisplay.tsx | — |
| **exchangerate** | DB | N — admin config | N | ExchangeRateDetail.tsx, ExchangeRateList.tsx, ExchangeRate.tsx, ExchangeRateDisplay.tsx | — |
| **exchangetransaction** | DB | N — system-managed | N | ExchangeTransactionDetail.tsx, ExchangeTransactionList.tsx, ExchangeTransaction.tsx, ExchangeTransactionDisplay.tsx | — |
| **taxjurisdiction** | DB | N — admin config | N | TaxJurisdictionList.tsx, TaxJurisdictionDisplay.tsx | — |
| **term** | DB | N — admin config (payment terms) | N | TermList.tsx, TermDisplay.tsx | — |

## Communications App

| Model | Route | Detail | List | Existing .tsx | Helpful .tsx |
|-------|-------|--------|------|---------------|-------------|
| **address** | DB | N — embedded in contact/org detail | N | AddressDetail.tsx, AddressList.tsx | — |
| **email** | DB | N — embedded in contact/org detail | N | EmailDetail.tsx, EmailList.tsx, Email.tsx | — |
| **phone** | DB | N — embedded in contact/org detail | N | PhoneDetail.tsx, PhoneList.tsx | — |
| **domain** | DB | N — admin config | N | DomainDetail.tsx, domainList.tsx | — |

## Docs App

| Model | Route | Detail | List | Existing .tsx | Helpful .tsx |
|-------|-------|--------|------|---------------|-------------|
| **document** | DB | ? — file viewer, linked records | ? — type filters, linked model | DocumentDetail.tsx, DocumentList.tsx, DocumentDisplay.tsx | — |
| **linkageentry** | DB | N — system junction table | N | LinkageEntryList.tsx, LinkageEntryDisplay.tsx | — |
| **questionanswer** | DB | N — Q&A records | N | QuestionAnswerList.tsx, QuestionAnswerDisplay.tsx | — |
| **tag** | DB | N — taxonomy | N | TagList.tsx, TagDisplay.tsx | — |

## Sync App

| Model | Route | Detail | List | Existing .tsx | Helpful .tsx |
|-------|-------|--------|------|---------------|-------------|
| **connection** | DB | ? — partner config, transform rules, sync history | ? — partner list, status | ConnectionDetail.tsx, ConnectionList.tsx | — |
| **bundle** | DB | ? — payload viewer, conflict detail | ? — status, partner filter | BundleDetail.tsx, BundleList.tsx | — |

## Support App

| Model | Route | Detail | List | Existing .tsx | Helpful .tsx |
|-------|-------|--------|------|---------------|-------------|
| **campaign** | DB | ? — ROI tracking, source attribution | ? — active/completed, cost | CampaignDetail.tsx, CampaignList.tsx | — |

## AI Assistant App

| Model | Route | Detail | List | Existing .tsx | Helpful .tsx |
|-------|-------|--------|------|---------------|-------------|
| **conversation** | none | N — Alice internal | N | (none) | — |
| **message** | none | N — Alice internal | N | (none) | — |
| **alicecoachinglog** | none | N — Alice internal | N | (none) | — |
| **aliceobservation** | none | N — Alice internal | N | (none) | — |
| **alicepreset** | none | N — Alice internal | N | (none) | — |
| **inventoryevent** | none | N — Alice internal | N | (none) | — |

## System Models (no custom pages needed)

| Model | Notes |
|-------|-------|
| contenttype | Django internal |
| group | Django auth |
| permission | Django auth |
| session | Django sessions |
| logentry | Django admin log |

---

---

## Printable Forms

All print documents live in `apps/transactions/components/print/`.
Shared layout: `PrintDocumentLayout.tsx`. Shared styles: `print.css`.
Triggered from Detail page toolbar Print button → `PrintPreviewModal.tsx`.

### Transaction Prints (customer-facing documents)

| Form | File | Built | Wired | Notes |
|------|------|-------|-------|-------|
| **Proposal** | ProposalPrintDocument.tsx | Y | Y | Quote for customer review |
| **Order** | OrderPrintDocument.tsx | Y | Y | Sales order confirmation |
| **Invoice** | InvoicePrintDocument.tsx | Y | Y | Bill to customer — must be flawless |
| **Purchase Order** | PurchasePrintDocument.tsx | Y | Y | PO sent to vendor |
| **Work Order** | WorkorderPrintDocument.tsx | Y | Y | Production/service instructions |
| **Receipt** | ReceiptPrintDocument.tsx | Y | Y | Goods received against PO |
| **Requisition** | RequisitionPrintDocument.tsx | Y | Y | Internal purchase request |
| **Project** | ProjectPrintDocument.tsx | Y | Y | Project summary with linked WOs |
| **Inventory Adjustment** | AdjustmentPrintDocument.tsx | Y | Y | Count correction record |

### Financial / Accounting Prints

| Form | File | Built | Wired | Notes |
|------|------|-------|-------|-------|
| **Statement** | StatementPrintDocument.tsx | Y | ? | AR statement — open invoices + payments by customer. Needs testing |
| **Overdue Notice** | (not built) | N | — | Past-due invoices by customer with aging buckets (30/60/90). Priority: H |
| **Tax Report** | TaxReportPrintDocument.tsx | Y | ? | Quarterly tax filing with certification block. Needs testing |

### Warehouse / Shipping Prints

| Form | File | Built | Wired | Notes |
|------|------|-------|-------|-------|
| **Packing List** | (not built) | N | — | Items in each box/pallet for a shipment. Customer receives this with goods. Priority: H |
| **Pick List** | (not built) | N | — | Warehouse worker list: item, location, qty to pull for an order. Priority: H |
| **Shipping Label** | (not built) | N | — | Address label for boxes/pallets. Carrier integration (UPS/FedEx/USPS). Priority: M |
| **Load Tags / Pallet Labels** | (not built) | N | — | WC2: PKPalletPack. Pallet ID, contents, weight, destination. Priority: M |

### Labels / Mail

| Form | File | Built | Wired | Notes |
|------|------|-------|-------|-------|
| **Address Labels** | (not built) | N | — | WC2: Label_Address, Label_Multiple. Avery format, batch print. Priority: M |
| **Barcode Labels** | (not built) | N | — | WC2: Code 128, SSCC-18, GS1. Item/serial/pallet barcodes. Priority: M |
| **QR Code Labels** | (not built) | N | — | WC2: Prnt_QR. Item lookup, station scan. Priority: M |
| **Letter / Mail Merge** | (not built) | N | — | WC2: Ltr_PrintOne, Ltr_TinyMCE. **New approach:** Don't build an editor. Use Word/Pages/Google Docs. Alice resolves {{model.field}} placeholders from Report records (category='letter'). User downloads .docx or copies rendered text. Sent letters logged as Document records. Priority: M |

### Print Form Summary

**Built and wired (9):** Proposal, Order, Invoice, Purchase, WorkOrder, Receipt, Requisition, Project, Adjustment
**Built, needs testing (2):** Statement, Tax Report
**Not built, high priority (3):** Overdue Notice, Packing List, Pick List
**Not built, medium priority (4):** Shipping Label, Load Tags, Address Labels, Barcode Labels
**Not built, low priority (2):** QR Code Labels, Mail Merge Letters

---

---

## WC2 Forms → WC3 Equivalents

Reviewed all forms in `ComEx19ak/Project/Sources/Forms/`. Status of each in WC3.

### Built — Working

| WC2 Form | WC3 Equivalent | Notes |
|----------|----------------|-------|
| **ApplyPayments** | `transactions/pages/ApplyPayments.tsx` | Two-pane: payments left, invoices right, per-invoice apply. Same UX pattern as WC2 |
| **Contact_List** | `core/models/contact/pages/ContactList.tsx` | Custom list with search, quick-add |
| **Order_Inc / OrderLine / SubOrderLine** | `TransactionDetailBase.tsx` + `LinesCard.tsx` | All transaction detail pages share base component with lines editing |
| **QA / QAEdit** | `QAPanel.tsx` + `QATab.tsx` | Question/answer on transaction detail. Template-driven via Setting records |
| **Document** | `DocumentsPanel.tsx` | Documents tab on all detail pages via TransactionDetailBase |

### Built — Needs Polish or Testing

| WC2 Form | WC3 Equivalent | Status |
|----------|----------------|--------|
| **SalesService** | `CommerceDashboard.tsx` | Sales+Service combined view. WC2 had date range, contact detail, subform. WC3 has 5-tab dashboard but may need the combined sales+service view as a tab |
| **Letter / LetterJoint** | (not built — redesigned) | WC2 had TinyMCE mail merge with field variables. **WC3 approach:** Don't build an editor. Use Word/Pages/Google Docs. Alice resolves `{{model.field}}` placeholders from Report records (`category='letter'`). User downloads .docx or copies rendered text. Sent letters logged as Document records linked to contact/transaction. WC2 fought the user's tools; WC3 is the data source, not the word processor. |
| **ListSelection** | DataBrowser | WC2's generic list view is replaced by DataBrowser. Working |
| **ImportDS / ImportCheck** | Sync app (Connection + Bundle) | WC2 had import with field mapping + validation. WC3 sync pipeline handles this differently |

### Not Built — Should Build

| WC2 Form | What It Did | WC3 Recommendation | Priority |
|----------|-------------|---------------------|----------|
| **QuickQuote** | Separate floating window. Search items, see price/qty/cost/margin. Select items, set qty, post to any transaction (proposal, order, invoice). Configurable columns via FieldCharacteristic. | Build as a floating panel or modal — `QuickQuotePanel.tsx`. Item search + price display + "Add to [Transaction]" button. Reuse `TransactionItemSearch.tsx` pattern but as a standalone window. Spawn from any transaction detail or toolbar. | **H** — daily use tool for order entry |
| **EditorScript** | Exposed table.field names. Users wrote scripts against data. | Replace with **AI Prompt Panel** — three areas: (1) prompt input, (2) generated code/query, (3) results. Non-experts ignore the code. Experts get insights. Alice interprets the prompt, generates the query, shows results. Setting record stores prompt history per user. | **M** — powerful for experts, Alice makes it accessible |
| **QueryEditor** | Visual query builder — pick table, add columns, set filters, run. | Django/React handles this better via **Saved Searches** (already designed in `saved-searches.md`). Setting records store queries per model. SearchPresetDropdown already built and wired to 7 list pages. Extend with: visual filter builder in DataBrowser, keyword aliases. | **M** — saved searches are the replacement |
| **CalendarMain / SalesCalendar / eventCalendar** | Calendar views of orders, actions, appointments. | Build `CalendarView.tsx` — action/order/invoice by date. Could be a tab in CommerceDashboard or standalone page. React calendar libraries (FullCalendar, react-big-calendar) available. | **L** — nice to have, Gantt partially covers this |
| **CronJob_Manager** | Scheduled background tasks — recurring jobs with time checks. | Django Celery Beat or `django-cron`. Alice already has nightly jobs. Needs admin UI to view/manage scheduled tasks. | **L** — operational, not user-facing |
| **Splash / Shutdown** | App startup/shutdown screens. | Not needed — React SPA handles this natively |

---

## Saved Searches

**Design:** Complete — see `readmes/saved-searches.md`
**Storage:** Report model with `category='saved_search'`. No new table.
**UI:** `SearchPresetDropdown.tsx` already built and wired to ProposalList, OrderList, InvoiceList, PurchaseList, WorkorderList, RequisitionList, ActionList.
**Backend:** `wcapi/search-presets/` endpoint exists.

### What's Working
- Setting records store saved queries per model
- SearchPresetDropdown renders on list pages (bookmark icon)
- Preset config: model, filters, sort, fields, description
- Request inputs: keyword, date range, status — prompted before running

### What's Needed
- **More seed presets** — common queries per model (e.g., "Open orders over $500", "Overdue invoices", "Items below reorder")
- **User-created presets** — save current DataBrowser filter as a preset (Save button exists, needs wiring)
- **Alice behavioral accumulation** — Alice tracks which presets users run, suggests new ones based on patterns. alice_log already captures search queries via `log_user_search` manage action

---

## AI Prompt Panel (replaces WC2 EditorScript)

**WC2 had:** Table.field name browser + script editor. Power users wrote queries.
**WC3 should have:** Three-pane prompt panel.

| Pane | Who uses it | What it shows |
|------|-------------|---------------|
| **Prompt** | Everyone | Natural language: "Show me customers who haven't ordered in 90 days" |
| **Code** | Experts (collapsible) | Generated Django ORM query or SQL. Experts can review, modify, learn |
| **Results** | Everyone | Data table with export. Click row to open record |

- Store prompt history as Setting records (`purpose='ai_prompt_history'`) per user
- Alice interprets prompts → generates queries → executes safely (read-only by default)
- Accumulated prompts become saved search candidates
- Not built yet. Priority: M. Depends on Alice having query generation capability.

---

---

## DataBrowser Subform Types

DataBrowser is the single rendering engine for all list/subform views. Five types cover every data display need. Kanban is standalone.

| Type | Structure | How DataBrowser handles it | Examples |
|------|-----------|---------------------------|----------|
| **1. Flat table** | columns × rows | Core function — already built | Order lines, invoices, payments, contacts |
| **2. JSON** | nested key-value, variable depth | Inline expand or spawn window | Settings config, metadata, refs, totals, price tiers |
| **3. BOM/Tree** | indented parent-child, one record per row | Tree mode with collapse/expand | Multi-level BOM, chart of accounts, org hierarchy |
| **4. Grouped** | rows nested under group headers | Sort + collapsible group headers | Invoices by customer, items by category, actions by project |
| **5. Calculated columns** | value from an approved function, not stored | Client-side JS, keyed to approved function | Running balance, margin %, days overdue, cumulative total |

**Kanban** — standalone layout, not a DataBrowser subform. Already built separately.

### Subform Config in Setting Record

One Setting per model (`purpose='workbench_fields'`) holds all subform definitions:

```json
{
  "list": ["ida", "status", "customer", "total"],
  "detail": ["ida", "status", "dt", "due_date"],
  "views": [{"name": "My Open Orders", "filters": {...}}],
  "subforms": {
    "order_on_customer": {
      "type": "flat",
      "columns": ["ida", "status", "totals.total", "dt"],
      "filters": {"status__in": "planned,confirmed"},
      "sort": "-dt_created",
      "max_rows": 20,
      "actions": ["open", "transfer"],
      "calculated": [{"key": "running_sum", "source_field": "totals.total", "label": "Running Balance"}]
    }
  }
}
```

### Calculated Function Approval Chain

No unapproved code runs in the browser. Approval flow:

1. **User requests** — asks Alice for a calculated column (e.g., "running balance on invoices")
2. **Alice checks** — if approved function exists with matching key, wire it immediately
3. **If no match** — Alice drafts the function, posts to Athena's review queue (Pending record)
4. **Athena reviews** — validates: read-only, no side effects, no network calls, no injection risk
5. **Approved** — function gets a key (e.g., `CF-024`), stored as Setting (`purpose='calculated_function'`), pushed to JS
6. **DataBrowser** picks up by key — runs client-side, fast, no backend call per row

```json
Setting (purpose='calculated_function', ida='CF-024'):
{
  "key": "running_sum",
  "approved_by": "athena",
  "dt_approved": "2026-07-10T20:00:00Z",
  "input": "field_value (number)",
  "js": "rows.reduce((sum, row, i) => { sum += row[field]; rows[i]._computed[key] = sum; return sum; }, 0)",
  "description": "Cumulative running total of a numeric field",
  "requested_by_contact_id": 41,
  "usage_count": 0
}
```

**Why client-side after approval:**
- Performance — running balance on 500 rows is instant in JS, slow as 500 API calls
- Offline — works when disconnected
- Auditable — every function has Athena's approval key and signature

**Alice tracks usage_count.** Popular functions get pushed to WCHQ → community builds a library of approved calculated columns. Initial set populated by backend (standard commerce functions). Users request new ones through Alice → Athena approval gate.

---

## Summary: Models That Need Custom .tsx Pages

**Confirmed custom (in use now):**
- contact, action, customer, vendor, item
- proposal, order, invoice, purchase, payment, receipt, workorder, requisition, project

**Under review (marked ? above):**
- billofmaterial, serial, glaccount, gljournal, document, connection, bundle, campaign

**Everything else:** DataBrowser

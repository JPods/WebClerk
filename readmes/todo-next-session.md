# TODO — Next Session

## Test What Was Built (Priority 1)
- [ ] Start Django + React dev servers
- [ ] DataBrowser: dark/light toggle, model picker (Cmd+Shift+M), column sort/resize/drag
- [ ] DataBrowser: field behaviors (blue=mailto, green=select, purple=lookup labels)
- [ ] DataBrowser: Form Layout dialog — reorder, behavior badges, row sizes
- [ ] DataBrowser: Save/Load/Delete layouts (shift-click delete)
- [ ] Sidebar: admin models open DataBrowser directly
- [ ] Sidebar: shift-click any model opens DataBrowser
- [ ] Org pages: /org/customer, /org/vendor, /org/employee, /org/rep, /org/manufacturer
- [ ] CommunicationsPanel: expand, inline edit, add, delete email/phone/address
- [ ] Print pages: /transactions/invoice/print/{id}, order, proposal
- [ ] ManageActionPanel on OrderDetail: Create Work Order, Partial Ship, Complete
- [ ] ManageActionPanel on PurchaseDetail: Receive Goods, Create Serial
- [ ] ManageActionPanel on InvoiceDetail: Consume Inventory, Assign Serial, Post GL
- [ ] CSV export from DataBrowser
- [ ] CustomerList: FieldConfigBar (Cols button)

## Build Expense Entry UI (Priority 2)
- [ ] Spreadsheet-style fast entry for Payment type=disbursed
- [ ] Tab between cells, Enter saves row
- [ ] Type toggle: Received / Disbursed
- [ ] Auto-suggest vendor from contact list

## Wire Remaining List Pages (Priority 3)
- [ ] Add useListFieldConfig + FieldConfigBar to InvoiceList
- [ ] Add to OrderList, ProposalList, PurchaseList, WorkorderList
- [ ] Add to ItemList, ContactList, ActionList, PaymentListPage

## Polish & Fix (Priority 4)
- [ ] Fix 11 seed_databrowser fake record errors (non-null constraints)
- [ ] Run pytest — verify 85 tests + no regressions from Payment migration
- [ ] Verify field_access query_scope works for customer/vendor roles
- [ ] Test ReportMenu on detail pages — verify report routing
- [ ] Review communications sync — are OrgBase aspects staying current?

## WC2 Gap Features — Next Wave (Priority 5)
- [ ] Test order production end-to-end: order → WO → partial ship → backorder → invoice
- [ ] Test inventory stacks: PO receive → 3 layers → invoice consume FIFO → verify COGS
- [ ] Test serial lifecycle: receive on PO → ship on invoice → warranty → return
- [ ] Test campaign: create → link to order → calculate ROI
- [ ] Build forecast engine (GAP-05): usage + min qty → forecast → low by vendor → auto PO
- [ ] Build sales pipeline / leads (GAP-07)
- [ ] Build territory management (GAP-09)
- [ ] Build commission calculation (GAP-11)

## UI Modernization (Priority 6)
- [ ] React template/theme system — 2-3 starter templates (professional, retail, field service)
- [ ] Beautify existing pages with consistent styling
- [ ] Mobile-responsive layouts for org and transaction pages

## Documentation (Ongoing)
- [ ] Incrementally update WC3 flow charts as code meets flows
- [ ] Update training documents as features are tested
- [ ] Keep claude-session-recovery.md current

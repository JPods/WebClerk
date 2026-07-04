# WC2 → WC3 Harvest Matrix
**Mined:** 2026-07-03 by Claude Code + Allie + Alice
**Sources:** 4D Methods (4,087 files), Vue2020 (20 routes), 4D TableForms (10,629 files), WC2 Classes (61 files), 4D InvoicesDemo, 40+ 4D Example Projects

---

## How to Use This Document

Each section lists features/patterns from WC2 with source file pointers. Priority reflects business value to WC3 adoption. The existing `todo.md` covers Tally, WCapi tasks, Transfers, Inventory, GL/Ledger, and some UX forms. **This document covers everything else.**

---

## 1. 4D Method Clusters — NOT in todo.md

| # | Cluster | Key Source Files | Business Function | Priority |
|---|---------|-----------------|-------------------|----------|
| 1 | **Pricing & Discount Engine** | `CalcDiscountedPrice`, `CalcOverRidePrice`, `PricingLvlAddType`, `PricingLvlDflts`, `ApprvlDiscount`, `PriceMatrix_FillArrays` | Multi-level price hierarchy, override approval workflow, margin-floor enforcement, discount-by-volume | H |
| 2 | **Packing / Load-Tag / Palletizing** | `PKALDefine`, `PKLineIntoBox`, `PKPalletPack`, `PKShippingCost`, `PKWtScaleRead`, `PKBarCodeReceive` | Warehouse pack workflow: scan→box→pallet→weigh→label→ship | H |
| 3 | **Shipping / UPS / FlexShip / Freight** | `UPS_TimeInTransit`, `UPS_ShipOnDate`, `UPS3rdPartyBill`, `FlxShip_OpenPrc`, `ShipmentTracking`, `AutoFreightLock` | Carrier rate shopping, UPS integration, 3rd-party billing, freight zones, tracking | H |
| 4 | **EDI Pipeline** | `EDI_OrdAdd`, `EDI_OrdLnAdd`, `EDI_PackInvoice`, `EDI_PackOrder`, `EDI_DupPONum`, `EDI_StopOrder` | Full 850/810/997 cycle — receive POs, pack invoices, duplicate detection, cancel/stop | H |
| 5 | **B2B Vendor/Partner Exchange** | `B2B_Exchange`, `B2B_Server`, `B2BItemsAsk`, `B2BItemsSend`, `B2BPOStatusGet`, `B2BSyncRequest` | Real-time vendor portal: item availability, PO status polling, record exchange | H |
| 6 | **Serial Number Tracking** | `Srl_IssueSale`, `Srl_RcvrPO`, `Srl_IssueDialog`, `Srl_Transaction`, `CCSSerialsToOrder` | Serial lifecycle: assign on PO receipt, issue to sale, track by customer, salvage/return | H |
| 7 | **Commission / Rep Management** | `CommissionCalculator`, `CommissionByMargin`, `CommissionRateCalc`, `CommissionReCalcOrders`, `RptRepCommis`, `Bonus_Report_Main` | Rate tables by margin band, recalculate on price change, rep splits, bonus multipliers | H |
| 8 | **Returns / Voids / Credit Memos** | `voidCurInvoice`, `voidCurOrder`, `VoidInvPay`, `CMAComplexImport`, `CMAComplexProcess`, `ApprvlCredit` | Full reverse-transaction: void invoice/order/PO/receipt, credit memo automation, approval | H |
| 9 | **BOM (Bill of Materials)** | `BOM_DoBOM`, `BOM_BuildMom`, `BOM_ChildCost`, `BOM_Consume`, `BOM_CostMatrix`, `BOM_CheckLoop` | Multi-level BOM: parent/child tree, cost rollup, loop detection, consume on production | H |
| 10 | **Email / SMTP / IMAP** | `SMTP_SendMsg`, `SMTP_EmailBuild`, `IMAP_Receive`, `Email_Governor`, `Email_OptOut`, `emailZeroBounceAPI` | Outbound/inbound email, opt-out management, bounce processing, PDF invoice email, rate limiting | H |
| 11 | **Credit Card / Payment Auth** | `CC_Authorize`, `Auth_AuthorizeNet`, `Auth_Chase`, `Auth_Verisign`, `PayPal_SendRequest`, `CC_EncodeDecode` | Multi-gateway: Authorize.Net, Chase, PayPal; tokenization, auto-select, apply to invoices | H |
| 12 | **PO Management / Receiving** | `POBasicsNew`, `PoLineRecv`, `PORcpt_CreateNew`, `POLinesInshipCompare`, `InshipFromPO`, `ShowInships` | PO lifecycle: create, receive lines, inship tracking, compare PO to inship | H |
| 13 | **Sync / Multi-site** | `Sync_Echo`, `Sync_PostOut`, `SyncRecordChanged`, `SyncEncryptSetup`, `SyncOrders`, `SyncWebIn`, `SyncWebOut` | Bidirectional sync: echo/conflict, encrypted exchange, web order sync, relationship sync | H |
| 14 | **Catalog Delta / Cross-Reference** | `CatalogDeltaReport`, `CatDeltaItemChange`, `CatDeltaLineItemCost`, `XRef_BuildFromClip`, `XRef_FindVendor` | Supplier catalog change detection, vendor item number cross-reference, cost updates | H |
| 15 | **Customer / Contact / Lead** | `CustomerQuery`, `CustomerAlert`, `DupsCustLeads`, `Lead_Relate2Cus`, `SCContactsUpdate`, `CustBBB_Import` | Advanced search, duplicate merge, lead→customer conversion, alert flags, external import | M |
| 16 | **Work Order / Scheduling** | `WOEvents_ALDefine`, `WODurationCalc`, `WOTemplate2Tasks`, `WOEventReschedule`, `Sched_SetterProcess` | Event-based WO, template→task expansion, person/date assignment, reschedule, calendar | M |
| 17 | **Calendar / Shared** | `Calendar_BuildViewObject`, `Calendar_UserSetup`, `Calendar_UserSharedBy`, `Calendar_GetPermisson` | Multi-user calendar with sharing, view by user/date, event CRUD | M |
| 18 | **Label Printing / Letters** | `Label_Address`, `Label_Multiple`, `Ltr_PrintOne`, `Ltr_TinyMCE`, `Prnt_MatrixItems`, `Prnt_QR` | Address labels, mail merge, QR code labels, statement printing, batch output | M |
| 19 | **Barcode Generation** | `BarcodeArray128Setup`, `BarCodeBuild`, `BarcodeSSCC`, `BarcodeGSCZip`, `BarC_MultiLabel` | Code 128, SSCC-18, GS1 barcode — server-side rendering | M |
| 20 | **Q&A / Questionnaire** | `QA_AddQuestions`, `QA_Answer2Form`, `QA_LoPostAnswers`, `QA_Export`, `QA_GetCustLeads`, `CloneQA` | Structured Q&A on any record, customer-facing web, lead generation from answers | M |
| 21 | **Keyword / Tag / Search** | `KeyWordsMake`, `KeyWordByObject`, `KeyWordByTag`, `KwBubbles2Items`, `KeywordWebRelated` | Auto-generate keyword indexes, tag-bubble UI, web search, catalog filtering | M |
| 22 | **Ad-Source / Campaign Tracking** | `AdSourceCalc`, `TallyAdEffects`, `TallyAdLoop`, `Tally_AdLeads`, `Tally_AdSales` | Campaign attribution: ad source → lead → order cost/revenue | M |
| 23 | **Demand Planning / Forecasting** | `ItemFutureNeed`, `ItemNeededList`, `ItemEstStockLvl`, `ForecastTrendReport5Yr`, `HistoricalInventory` | Reorder points, sales velocity projection, 5-year trend, low-stock alerts | M |
| 24 | **Territory / Geography** | `TerritoryApplyByZip`, `FindShipZone`, `FindShipZoneSite`, `ImpShipZipCodes`, `DealLoc_Tally` | Zip→territory, freight zone lookup, dealer tally by geography | M |
| 25 | **Accounting Export** | `Payment_ExportToPeachtree`, `PeachTreeCustomers`, `QuickenLink`, `SalesJournalsiLo` | GL journal export to Sage/Quicken — the bridge to external accounting | M |
| 26 | **Tax Calculation** | `TaxCalcLine`, `TaxSalesReport`, `TaxSalesReportData`, `TaxWebService` | Line-level tax calc, external tax service connector, period tax reporting | M |
| 27 | **Document Template Engine (TIO)** | `TIO_ParseText`, `TIO_ParseField`, `TIO_ParseLoopB`, `TN_PrintOne`, `TNSaveForWeb` | Template loop/field substitution, RTF+HTML output — drives all printed documents | M |
| 28 | **Web Storefront (Wcc)** | `WccUserLogIn`, `WccOrderServ`, `WccItemServ`, `WCCInvoiceShoppingCart`, `WccSearch`, `WccMyPage` | Customer-facing store: login, search, cart→invoice, "my account" | M |
| 29 | **Customer Self-Service Portal (NxPv)** | `NxPvOrders`, `NxPvInvoices`, `NxPvPOs`, `NxPvProposals`, `NxPvService` | Customer portal: view own orders/invoices/POs/proposals/service requests | M |
| 30 | **Warranty / Returns** | `WarrantyIssue`, `Return`, `Rwk_SetIndividu`, `Orph_Contact` | Warranty claims, return processing, rework tagging, orphan detection | M |
| 31 | **Service Record / Field Service** | `Srv_ALDefine`, `Srv_ArrayFill`, `Srv_AddQuestns`, `SRE_Print` | Service records with Q&A, print, order line linkage | M |
| 32 | **Gantt / Production Schedule** | `Gantt_Rows`, `GanttDateDTsImport`, `GanttParse`, `OrderLineProductionSchedule` | Gantt chart for job shop production scheduling | M |
| 33 | **Cron / Background Jobs** | `CronJobExecute`, `CronJobLoop`, `CronJobStartup`, `CronManager` | Built-in job scheduler — nightly tallies, email sends, sync | M |
| 34 | **User Reports (URpt)** | `URpt_Accept`, `URpt_CheckAuthL`, `URpt_LoadDoc`, `URpt_SetTypePop` | End-user ad-hoc report builder with named saved reports | L |
| 35 | **Tech Notes CMS** | `TechNoteAreaListDefine`, `TechNotesFor`, `TechNotes2ContentsPage` | Internal knowledge base attached to records — FAQ/support ticket | L |
| 36 | **Multi-site / Warehouse** | `ItemWarehouseEditor`, `ItemWarehouseCombine`, `ItemSiteTally`, `CreateItemSiteRecord` | Per-warehouse quantities, site management, multi-location inventory | L |
| 37 | **Rep Time Tracking** | `RepTimeIn`, `RepTimeOut`, `RepTimeSendXMLData` | Sales rep clock-in/out, time export | L |
| 38 | **SSL / ACME Certs** | `ACME_Auto_Cert`, `SSLCreateCerts`, `LetsEncryptPath` | Let's Encrypt auto-provisioning for self-hosted installs | L |

---

## 2. Vue2020 Features — WC3 Gaps

| # | Feature | Source File | What It Does | WC3 Has? | Priority |
|---|---------|------------|--------------|----------|----------|
| 1 | **Employee Home Dashboard** | `views/EmployeeHome.vue` | Cross-model workbench: date-range filter drives all sub-lists simultaneously | No | H |
| 2 | **Shared Date-Range Filter** | `components/EmployeeDaySearchForm.vue` | EventBus broadcast — all lists react to one filter | No | H |
| 3 | **Unified Search Hub** | `views/Search.vue` | 8 parallel search widgets on one page | No | H |
| 4 | **Order Detail + Make Invoice** | `views/OrderDetail.vue` | Order→Invoice promotion with live totals panel | No | H |
| 5 | **Proposal Detail + Make Order** | `views/ProposalDetail.vue` | Proposal→Order promotion with billing address panel | No | H |
| 6 | **Print Views** | `OrderPrint.vue`, `ProposalPrint.vue`, `InvoicePrint.vue` | Browser-native PDF with letterhead, bill-to/ship-to, totals | No | H |
| 7 | **QA/Condition Reports** | `components/QAForm.vue`, `QAList*.vue` | Structured Q&A on any document with photo upload | No | H |
| 8 | **Cloneable Proposals** | `views/CloneableProposalsHome.vue` | Search past proposals, preview, one-click clone | No | H |
| 9 | **Product Key-Tag Tree** | `components/ProductTree.vue` | Hierarchical vue-jstree browser; drag items into lines | No | H |
| 10 | **Kanban Board** | `components/KanbanPad.vue` + `TaskCard.vue` | 4-column drag-drop task board (Backlog→Done) | No | H |
| 11 | **Customer Detail + Sub-Lists** | `views/CustomerDetail.vue` | Embedded orders/proposals/invoices + QA + LockBox | Partial | M |
| 12 | **Gantt Chart** | `components/GanttContainer.vue` | Multi-row timeline with drag-reschedule | No | M |
| 13 | **Task Map** | `components/MapPad.vue` | Leaflet map with color-coded task markers | No | M |
| 14 | **Calendar** | `components/Calendar.vue` | Monthly view with drag-drop reschedule | No | M |
| 15 | **Record Lock Box** | `components/LockBox.vue` | Multi-user record locking banner | No | M |
| 16 | **Call Report Form** | `components/CallReportForm.vue` | Structured CRM activity log | No | M |
| 17 | **Line Item Popups** | `OrderLinePopup.vue`, etc. | Modal single-line edit with live total update | Partial | M |
| 18 | **Quick-View Popups** | `CustomerPopup.vue`, `OrderPopup.vue`, etc. | Quick-view from list row without full navigation | No | M |
| 19 | **Self-Registration** | `components/RegisterForm.vue` | Customer self-signup | No | M |
| 20 | **Password Reset** | `components/ResetPassword.vue` | Email-based password reset flow | Partial | M |

### Vue2020 Libs Worth Preserving

| Library | What to Harvest |
|---------|----------------|
| `libs/eventnames.js` | Complete event namespace — domain vocabulary for React state coordination |
| `libs/urls.js` | Full API surface — gap-check against wcapi endpoints. Key missing: `makeInvoice`, `makeOrder`, `Clone`, `GetGantt`, `GetKanban` |
| `libs/staticlist.js` | Hardcoded select values → migrate to WC3 Setting/SelectList records |
| `libs/formbuilder.js` | Declarative JSON-driven form engine — harvest field-type taxonomy and validation rules |
| `libs/utils.js` | `formatPhoneNum` regex, `emailValidator` regex, date format logic |

---

## 3. 4D TableForms — Uncataloged Workflow Clusters

| # | Cluster | Key Forms | Business Workflow | Priority |
|---|---------|-----------|-------------------|----------|
| 1 | **Payment Application** | T1/ApplyPayment, T28/diaMakePay, T28/diaOffSetInvoic | Apply payment to invoices, recurring payments, credit offset | H |
| 2 | **Inbound Receiving** | T1/InShipGoods, T1/InshipAdj, T95/diaEntryForm | Receive goods against PO, adjust quantities, write receipts | H |
| 3 | **Pick/Pack/Ship** | T1/Packing, T1/PackingPallets, T3/Shippable, T88/OrdLoad | Pack list, pallet assignment, shippable filter, load tags | H |
| 4 | **Period Close** | T1/EOM, T1/OpenClose, T60/ExecuteScript | Day open/close, month-end close sequence, tally period gate | H |
| 5 | **AP Vendor Management** | T1/VendorInvoiceAdjust, T1/VendorLowItem | Adjust vendor invoices, low-stock vendor alerts | H |
| 6 | **Time Tracking** | T56/Input, T56/RptTimeSignOff, T56/diaReviewTimes | Time against work orders, review and sign-off | H |
| 7 | **Service Tickets** | Forms/SalesService | CRM+WO hybrid: create service call, assign tech, track | H |
| 8 | **Quick Quote** | Forms/QuickQuote | Fast pricing before formal proposal | H |
| 9 | **User-Defined Reports** | T46/iUserReportDesign, T46/diaUserReport | End-user report designer (field selection, sort, filter) | H |
| 10 | **Import Validation** | Forms/ImportCheck, Forms/ImportDS, Forms/OutputDS | Pre-import quality check, batch import/export with preview | H |
| 11 | **Price Matrix UI** | T105/ItemTableoLo, T4/MatrixBuild | Price matrix grid, item variant/matrix builder | H |
| 12 | **AR Statement + Aging** | T2/StatemntLines, T28/incDateDollar | Statement of account with aging buckets | H |
| 13 | **PO Receipt Entry** | T95/diaEntryForm, T39/diaChoosePO | Operator receipt dialog, PO selection | H |
| 14 | **Order Clone** | T3/CloneDialog | Copy existing order for repeat customer | H |
| 15 | **Item Import** | T4/ListItemImport, T4/MatrixBuild | Bulk item import, variant matrix builder | H |
| 16 | **Linked Invoice Sets** | T26/diaLinkedInvSet | Group related invoices for complex billing | M |
| 17 | **Serial Number Management** | T47/diaSerialSet, T47/DiaFindCustVend | Block serial assignment, customer/vendor lookup | M |
| 18 | **CronJob Manager** | Forms/CronJob_Manager | View/enable/disable/run scheduled jobs | M |
| 19 | **Sales Calendar** | Forms/SalesCalendar, Forms/CalendarMain | Sales activity scheduling and follow-up | M |
| 20 | **Requisition** | T1/Requisition | Internal requisition before PO — approval gate | M |
| 21 | **Estimating** | T1/Estimating | Pre-quote cost estimation before pricing | M |
| 22 | **Forecasting** | T1/Forecasting, T1/Forecast_OH | On-hand vs. forecast, demand period choices | M |
| 23 | **Department Views** | T1/DeptSales, T1/DeptProduction, T1/DeptAdmin | Same record, different field sets per role | M |
| 24 | **Recent Buys** | T1/RecentBuys | Customer purchase history at point of order entry | M |
| 25 | **Item Substitution** | T4/diaListExch | Substitute items when primary is out of stock | M |

---

## 4. WC2 Classes — Patterns to Adopt

| # | Class | Key Methods | What WC3 Should Build | Priority |
|---|-------|-------------|----------------------|----------|
| 1 | **cLine** | `calc()`: discountedPrice, extendedPrice, extendedCost, extendedWt, qtyBackLogged | `@property` computed fields on OrderLine/InvoiceLine — not stored columns | H |
| 2 | **cRelated** | `defineRelated()` | Explicit FK registry constant — Customer→18 related tables with field names | H |
| 3 | **cChanges** | `createTallyChange()`, `saveArchive()` | `ChangeLog` model with JSONB `history[]` — lazy-create, snapshot with lines on every save | H |
| 4 | **CustomerSelection** | `actionToday()`, `actionDate()`, `actionDateRange()` | Django `CustomerQuerySet` manager with named date-range methods | H |
| 5 | **cChoices** | `getActions()`, `getScriptsolo()`, `runEntityNew()` | `Setting`/`Executable` driving per-table lifecycle hooks — configurable behavior | H |
| 6 | **cAddress** | `addressOnly()`, `addressFull()` | Locale-aware address formatter as Python mixin/utility | H |
| 7 | **cPerson** | `qqname_o`, `_parseEmailsFromText()` | Normalized name object + freeform contact ingestion regex | H |
| 8 | **cProcess** | Entity lifecycle: cur/old/sel/pos/cnt + add/save/cancel/delete | CRUD state machine — optimistic-lock `dk auto merge` + all error branches named | H |
| 9 | **cBlock/cBlockChain** | `calculateHash()`, `isValid()`, `push()` | SHA256-linked audit chain for payments/invoices — tamper-evident | M |
| 10 | **cConvert_to20** | `_mapCustomer()` through `_mapPOLine()` | Field-by-field WC2→WC3 schema translation — authoritative migration reference | H (ref) |

---

## 5. 4D InvoicesDemo — Patterns to Adopt

| # | Pattern | Source | WC3 Implementation |
|---|---------|--------|-------------------|
| 1 | Per-line tax snapshot | `Invoice_Lines/method.4dm` | Store `tax_rate` per line at entry time, not derived from current product | H |
| 2 | Cascade rollup | `Util25_EntityLoad_Specific.4dm` | Django `post_save`/`post_delete` signal on InvoiceLine → `invoice.recalculate()` | H |
| 3 | Invoice type enum | `catalog.4DCatalog` | `invoice_type` CharField choices replacing boolean flags | H |
| 4 | Product autofill + price snapshot | `_PROP_Product_ID_.4dm` | Copy `sale_price` and `tax_rate` from Product to line — independent thereafter | H |
| 5 | Explicit save status handling | `TableShow.entitySave()` | wcapi returns structured response: success, autoMerged, stampChanged, locked, permissionDenied, gone | H |
| 6 | Cross-table navigation | `Util25_PropagateSelection.4dm` | DataBrowser related-record traversal: Invoice→Client, Product→all Clients who bought it | M |
| 7 | Conditional row highlighting | `Util25_LB_HIGHLIGHT_INVOICES.4dm` | DataBrowser `row_style` function in layout settings — highlight overdue/high-value | M |
| 8 | Settings singleton | `Settings_GetCurrent` | WC3 `Setting` model holding company config (SMTP, invoice sequences, defaults) | M |
| 9 | Partial payments | Payments table: Amount vs Applied | Support split payments across invoices + multiple partial payments per invoice | M |
| 10 | Selective transaction wrapping | `TableShow.relatedDelete()` | `@transaction.atomic` only for multi-table ops (delete invoice + cascade lines) | M |

### Risk Flags from InvoicesDemo
- **Stale totals window**: Line saves before header rollup — use `select_for_update()` on parent during rollup
- **Tax rounding accumulation**: Per-line Round() can drift — consider aggregate rounding
- **Invoice number concurrency**: Settings-stored counter not safe — use PostgreSQL sequence
- **No audit on line edits**: Add `modified_by`/`modified_at` to InvoiceLine from day one

---

## 6. Cross-Source Priority Summary

### Tier 1 — Build These First (Highest Business Impact)

| Feature | Sources | Why First |
|---------|---------|-----------|
| Document promotion chain (proposal→order→invoice) | Vue2020 views, cProcess, cChoices | Core sales workflow — every transaction depends on it |
| Pricing/discount engine | 4D Methods, cLine, T105/PriceMatrix | Every line item calculation depends on this |
| Payment application + partial payments | T1/ApplyPayment, InvoicesDemo, T28 | AR operations blocked without this |
| Pick/pack/ship | 4D Methods PK*, T1/Packing, T3/Shippable | Warehouse adoption blocker |
| Employee Home dashboard | Vue2020 EmployeeHome | The daily entry point for every user |
| Print views (invoice/order/proposal) | Vue2020 *Print.vue | Customers need paper/PDF documents |
| Returns/voids/credit memos | 4D Methods void*, CMA* | Cannot do reverse transactions without this |
| Inbound receiving | 4D Methods PO*, T1/InShipGoods, T95 | Purchasing adoption blocker |

### Tier 2 — Build Next

| Feature | Sources |
|---------|---------|
| Commission/rep management | 4D Methods Commission*, Bonus* |
| Serial number tracking | 4D Methods Srl_*, T47 |
| BOM (Bill of Materials) | 4D Methods BOM_* |
| QA/condition reports + photo upload | Vue2020 QAForm, 4D Methods QA_* |
| Cloneable proposals/orders | Vue2020 Cloneable*, T3/CloneDialog |
| Product key-tag tree | Vue2020 ProductTree |
| Period close (day/month) | T1/EOM, T1/OpenClose |
| AR statement + aging | T2/StatemntLines, T28/incDateDollar |
| Kanban board for Actions | Vue2020 KanbanPad |
| EDI pipeline | 4D Methods EDI_* |

### Tier 3 — Build When Needed

| Feature | Sources |
|---------|---------|
| Email stack (SMTP/IMAP/bounce) | 4D Methods SMTP*, IMAP*, Email_* |
| Shipping/UPS integration | 4D Methods UPS_*, FlxShip_*, Shipping* |
| B2B exchange | 4D Methods B2B_* |
| Sync/multi-site | 4D Methods Sync_* |
| Catalog delta/cross-reference | 4D Methods CatalogDelta*, XRef_* |
| Demand forecasting | 4D Methods ItemFutureNeed, Forecast* |
| Calendar/Gantt/Map views | Vue2020 Calendar, Gantt, MapPad |
| Label printing / barcode | 4D Methods Label_*, Barcode* |
| Web storefront (Wcc) | 4D Methods Wcc* |
| Customer self-service portal | 4D Methods NxPv* |
| User-defined reports | T46 forms |
| Work order scheduling | 4D Methods WOEvents*, Sched_* |

---

## Source Paths Quick Reference

| Source | Path |
|--------|------|
| 4D Methods | `~/Documents/CommerceExpert/00WebClerk19/Project/Sources/Methods/` |
| 4D TableForms | `~/Documents/CommerceExpert/00WebClerk19/Project/Sources/TableForms/` |
| 4D Forms | `~/Documents/CommerceExpert/00WebClerk19/Project/Sources/Forms/` |
| Vue2020 | `~/Documents/CommerceExpert/vue2020/src/` |
| WC2 Classes | `/Volumes/TempFiles/WebClerk_versions/WebClerk20_over_withoutLines/Project_WebClerk/Sources/Classes/` |
| 4D InvoicesDemo | `/Volumes/TempFiles/4D_Examples/25-InvoicesDemo/` |
| WC2 Schema | `~/Documents/CommerceExpert/webClerk3/readmes/topics/wc2/wc2_schema.json` |
| Existing todo.md | `~/Documents/CommerceExpert/webClerk3/readmes/topics/wc2/todo.md` |
| Legacy strategy | `~/Documents/CommerceExpert/webClerk3/readmes/legacy/00-legacy-reference-strategy.md` |
| WC2 Flow Charts | `~/Documents/CommerceExpert/webClerk3/readmes/legacy/WebClerkComExFlowCharts.pdf` |
| WC2 Classes | `/Volumes/TempFiles/WebClerk_versions/WebClerk20_over_withoutLines/Project_WebClerk/Sources/Classes/` |
| 4D Examples (all) | `/Volumes/TempFiles/4D_Examples/` |

---

## 6. 4D Example Projects — Patterns (40+ projects mined)

### EA_Contacts — Contact Management

| Pattern | Source | What WC3 Should Learn | Priority |
|---------|--------|----------------------|----------|
| Named-action controller dispatch | `loadContactManagerController.4dm` | Emit named action strings to shared controller; no ad-hoc prop drilling | H |
| Live keystroke search with composited query template | `loadContacts.4dm` | Search on every keystroke (debounced), query shape separated from value, category filter additive | H |
| Save-or-create FK inline | `saveButton.4dm` | New Category/Tag created on save, not forced to separate step | H |
| Dual-mode list/card view toggle | `layoutButton1.4dm` | Contact/product lists offer list and card views; preference stored per user | M |
| Responsive grid column calculation | `initializeContactGrid.4dm` | Card grids recalculate column count on resize (min 326px per cell) | M |
| Prev/next cursor for post-delete navigation | `deleteButton.4dm` | After delete, navigate to adjacent record, not back to list | M |

### EA_Invoices — Invoicing (OO architecture)

| Pattern | Source | What WC3 Should Learn | Priority |
|---------|--------|----------------------|----------|
| TableShow class — CRUD encapsulated in one object | `TableShow.4dm` | entityAdd/Open/Save/Delete/Move/Duplicate all on one controller object | H |
| Generic property introspection for search/sort | `Util_GetPropertyList.4dm` | Walk model fields, FK paths, object sub-paths; exclude `_` prefixed | H |
| Per-user per-table column layout persistence | `Listbox_Setting` table | DataBrowser column widths/visibility stored per user per model | H |
| Computed Entity properties (Amount_Due, Full_Address) | `ClientsEntity.4dm` | Django `@property` for totals, formatted addresses — server-side | H |
| Optimistic lock + entity resurrection | `action_Save_Optimistic.4dm` | If entity deleted between load and save, offer to recreate | H |
| Pessimistic lock showing WHO has the lock | `action_Unlock.4dm` | Multi-user: show lock holder name, not just "locked" | M |
| QueryTable operator vocabulary (10 operators by field type) | `TableQuery.makeOperatorPopUp` | text→contains/begins/ends, numbers→gt/lt, all as data objects | M |
| `__DeletedRecords` soft-delete audit table | `catalog.4DCatalog` | Audit trail for all deletes | L |

### EA_Lightweight_Email_Composer

| Pattern | Source | What WC3 Should Learn | Priority |
|---------|--------|----------------------|----------|
| Per-user SMTP config (not global) | `loadSMTPSetting.4dm` | Multi-tenant SMTP; per-org or per-user email settings | H |
| Guard clauses → email assembly pipeline | `wp_SendMail.4dm` | Validate host/port/credentials/to/from/subject independently before send | H |
| Single public entry point `send_email(to)` | `lw_MailEditor.4dm` | One callable from any context (invoice, follow-up, confirmation) | H |
| SMTP config check → offer setup if missing | `lw_MailEditor.4dm` | Detect missing config, link to settings before silent failure | M |

### EA_Recipes — BOM / Ingredient Pattern

| Pattern | Source | What WC3 Should Learn | Priority |
|---------|--------|----------------------|----------|
| BOM pattern (parent + line items with qty+unit) | `catalog.4DCatalog` | Recipe:Ingredients = Invoice:Lines = Kit:Components — same structure | H |
| Faceted sidebar (distinct values + count) | `updateLookupListbox.4dm` | DataBrowser sidebar: pick field, show distinct values + counts, click to filter | H |
| Thumbnail vs full image as separate fields | `catalog.4DCatalog` | List views use thumbnail; detail uses full — avoid large image transfer | H |
| Structured blob for ordered sub-items | `catalog.4DCatalog` | JSON blob for items that don't need their own table (steps, instructions) | M |
| Duration as integer + split display | `loadRecipeInput.4dm` | Store minutes, display as H:M — applies to lead time, payment delay | M |

### EA_Tasks — Task Management

| Pattern | Source | What WC3 Should Learn | Priority |
|---------|--------|----------------------|----------|
| Status ↔ Percent coupling (state machine) | `statusField.4dm` | Completed→100%, Not Started→0% — enforce coupling on save | H |
| Validation chain with error accumulation | `validateTaskFields.4dm` | Collect ALL errors into field-keyed dict, return together | H |
| Compound filter: text + category + range | `loadTasks.4dm` | Compose filters additively: text AND category AND status AND date range | H |
| Toggle-all enable/disable as a unit | `toggleTaskInput.4dm` | Read-only vs edit mode: one call enables/disables all fields | M |
| New-window vs inline subform mode flag | `saveButton.4dm` | Same form works embedded or in a modal — behavior flag drives it | M |

### UI-with-Classes — Widget Class Architecture

| Pattern | Source | What WC3 Should Learn | Priority |
|---------|--------|----------------------|----------|
| Two-tier class hierarchy: FormObject → Widget → typed subclass | `formObject.4dm`, `widget.4dm` | All field components extend a base that owns visibility, enabled, coordinates | H |
| Form as factory/registry for its children | `form.4dm` | FormContext or useFormRegistry() — enables form.validate(), form.resetAll() | H |
| callChild / callParent / callMeBack — three communication channels | `form.4dm` | Parent→child imperative, child→parent event, peer→form callback. Don't collapse. | H |
| Group — operations fan out to all members | `group.4dm` | FieldGroup: setVisible/setEnabled fans to all members — readonly mode toggle | H |
| saveProperties / restoreProperties — design-time defaults as reset target | `listbox.4dm` | Capture layout config on init; "reset layout" restores without round-trip | H |
| doSafeSelect — selection resilient to deletion | `listbox.4dm` | After delete: try next, fallback prev, clear if empty — three cases | H |
| distributeLeftToRight — auto-size button bars | `group.4dm` | Button bars size to content then distribute with spacing | M |

### Dynamic-Forms-Starter — JSON Schema for Forms

| Pattern | Source | What WC3 Should Learn | Priority |
|---------|--------|----------------------|----------|
| JSON schema as single source of truth for widget types | `DefaultJsonForm.json` | Widget schema defines all types with defaults; forms are data not code | H |
| dataSource + dataSourceTypeHint pair | `DefaultJsonForm.json` | Each column needs data_source (field path) AND type_hint (display override) | H |
| List form vs detail form as separate JSON documents | `templateJsonFormList.json` | list_layout and detail_layout are separate Setting objects per model | H |
| sizingX/sizingY: fixed vs grow | `DefaultJsonForm.json` | Column sizing: fixed width vs flex-grow — driven by config not CSS | M |

### HDI_SubformCommunication — Parent/Child Patterns

| Pattern | Source | What WC3 Should Learn | Priority |
|---------|--------|----------------------|----------|
| Typed value bridge (SET/GET SUBFORM CONTAINER VALUE) | `S_Text/ObjectMethods/Input.4dm` | Subpanels communicate via value prop + onChange callback, never reach into parent state | H |
| EXECUTE METHOD IN SUBFORM — parent calls child's named method | `contactManager/method.4dm` | useImperativeHandle + forwardRef to expose child methods to parent | H |
| Sibling communication only through parent intermediary | `contacts_SF.4dm` | Two siblings never import each other; all comms through shared parent state | H |
| CALL SUBFORM CONTAINER with custom event codes | `contacts_LB.4dm` | PanelEvent enum: SELECTED=-1, DOUBLE_CLICKED=-2 — parent switches on code | M |

### Infrastructure Projects

| Pattern | Source Project | What WC3 Should Learn | Priority |
|---------|--------------|----------------------|----------|
| Signal fan-out for parallel work + cancellation token | 80-Signal | Celery group() + chord(); shared Redis flag for graceful cancel | H |
| Unified interface over FTP/SFTP/Dropbox/GDrive | FileTransfer_Class | Connection sync layer: identical upload/download/list interface, swap backend | H |
| ASSERT at constructor boundaries | FileTransfer_Class | Every Connection validates required fields in __init__, raise ValueError with named field | H |
| Credentials in shared Storage, not code | Twilio Example | API keys in Credential model or encrypted settings, loaded once at startup | H |
| Phone normalization to E.164 at save() | Twilio Example | Normalize in model save, not in every caller. Use PhoneField or pre-save signal | H |
| SID-based deduplication for inbound events | Twilio Example | Every external event needs idempotency key; get_or_create(external_id=sid) | H |
| Operator vocabulary as data objects | 65-QueryClass | {text, operator} mapped to Django __startswith/__icontains/__gt — not hardcoded | H |
| Type-aware query routing | 65-QueryClass | Numeric→range input, text→string ops, date→picker, FK→typeahead | H |
| Global hotkey → command palette | QOM | Cmd+K opens search contacts, invoices, Alice commands, DataBrowser models | H |
| Context pinning avoids N+1 queries | 40-Contexts | Explicit select_related/prefetch_related in every wcapi view | H |
| Store UTC, display local, convert at entry | Date4D | Confirms Axiom 14 implementation: convert at entry point, never store local | H |
| Widget-container message protocol | isWidgets/Finder | Search input fires Redux actions with message types, never fetches data itself | H |
| Formula-based column rendering vs filtering | isWidgets/Finder | Separate display_fn from filter_fn per column — FK displays name, filters on id | H |
| Priority-tiered cache eviction | 50-CacheFlow | FK joins get longer TTL than blobs; expose /admin/health/cache/ | M |
| Async vs sync toggle on same class | FileTransfer_Class | Sync mode for small transfers, async for nightly batches — same interface | M |
| Background poller as scheduled task | Twilio Example | Alice's inbound poller = Celery beat task with configurable interval in Setting | M |
| Pagination following next_page_uri | Twilio Example | Build paginate(url, fetch_fn) utility for all external API integrations | M |

### Drag-Drop and Listbox Projects

| Pattern | Source Project | What WC3 Should Learn | Priority |
|---------|--------------|----------------------|----------|
| Entity drag between two lists: .add() source, .minus() from target | 19-05_DragDrop Demo1 | Assign items to orders, move contacts between groups — add to target, remove from source | H |
| In-list reorder via swap at drop position | 19-05_DragDrop Demo5 | Reorder line items, priority lists — swap item at drop index with dragged item | H |
| Generate listbox from JSON at runtime (4 data source types) | 18-16_DynamicListbox | DataBrowser columns generated from layout JSON, not hardcoded components | H |
| Column width = container width ÷ column count (equal distribution) | 18-16_DynamicListbox | Default column sizing: equal share of available width, user resizes override | M |
| Kirk: tabbed import wizard (choose file → preview → match columns → run) | Kirk/dataImporter | WC3 import: 4-step wizard: select file → preview data → map columns → execute import | H |
| Row highlighting via metaExpression (conditional per-row styling) | testSurlignage | DataBrowser row_style callback: overdue=red, high-value=green, archived=gray | M |

### Cross-Project Patterns (3+ independent projects)

| Pattern | Where It Appears | WC3 Rule |
|---------|-----------------|----------|
| Named-string action bus | EA_Contacts, EA_Tasks, EA_Invoices | All list-detail views emit named action strings to shared controller |
| Category autocomplete: keystroke query, limit-10, create-if-new | EA_Contacts, EA_Tasks | Every FK/tag field has this autocomplete pattern |
| Validation: accumulate all errors, return together | EA_Tasks, EA_Invoices, UI-with-Classes | Never stop at first error; field-keyed error dict |
| doSafeSelect after delete (next→prev→empty) | EA_Contacts, EA_Tasks, EA_Invoices, UI-with-Classes | Auto-select adjacent record after every delete |
| Three-channel parent/child communication | UI-with-Classes, HDI_SubformComm, EA_Contacts | Parent→child imperative, child→parent event, siblings via parent |
| JSON schema defines form, not code | Dynamic-Forms-Starter, UI-with-Classes | Layouts are data (Setting records), versioned, restorable |
| Structured result {success, error, data} | FileTransfer, Twilio, QueryClass | Standard response envelope for all internal service calls |
| Subform-to-parent signaling via typed event | EA_Contacts, EA_Tasks, EA_Invoices | Child signals parent via callback prop, never direct state mutation |

---

## 7. Notes

- **Time tracking**: Bill confirmed this will use outside apps/APIs, not built in WC3. Remove from harvest priority.
- **BOM**: Not present in 4D InvoicesDemo. The EA_Recipes project confirms the pattern (parent + line items with qty+unit). WC2 Methods have 27 BOM_* methods for the full implementation.
- **Vector store status**: All findings logged to Allie (teach_allie + observations), Alice (6 observations across item/invoice/customer/action models), and Allie DB (2 cross-domain observations).

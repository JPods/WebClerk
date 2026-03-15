# Component & File Inventory

> **Updated:** 2026-03-13  
> Files prefixed `qqq_` are flagged for removal review — do not import or build on them.

---

## Admin / General Purpose (`src/components/`)

Core admin, auth, layout, and dev-tools components shared across the entire app.

### Auth & Guards

| File | Purpose |
|------|---------|
| `auth/SignInForm.tsx` | Login form with zod validation, token persistence |
| `auth/SignUpForm.tsx` | Registration form with email verification modal |
| `auth/AdminGuard.tsx` | `useIsAdmin`, `useUserRole`, `AdminGuard` — role-based access |
| `PermissionGuards.tsx` | `PermissionGate`, `ReadOnlyField`, `HiddenField` — RBAC components |

### Developer Tools

| File | Purpose |
|------|---------|
| `AiHelpWidget.tsx` | Floating AI assistant chat widget with mode switching |
| `DataSetBadge.tsx` | Visual indicator for current data set (DEV/STAGING/PRODUCTION) |
| `DevTools.tsx` | Dev panel for switching data sets and db_mode |
| `DevIssueReporter.tsx` | Developer bug report modal with console capture |
| `UserIssueReporter.tsx` | End-user help-desk button (creates Action records) |

### Header (`header/`)

| File | Purpose |
|------|---------|
| `Header.tsx` | Main app header with theme toggle, notifications, user dropdown |
| `NotificationDropdown.tsx` | Header notification bell dropdown |
| `UserDropdown.tsx` | Header user profile dropdown with logout |
| `SaveQueueIndicator.tsx` | Header indicator for pending save operations |
| `TaskManagerIndicator.tsx` | Header indicator for request/save queue status |
| `InventoryMonitor.tsx` | Floating window polling item quantity buckets every 10s |

### User Profile (`UserProfile/`)

| File | Purpose |
|------|---------|
| `UserAddressCard.tsx` | User profile address editor with form arrays |
| `UserInfoCard.tsx` | User profile contact info editor (phones, emails) |
| `UserMetaCard.tsx` | User profile metadata display card |

---

## Common — Shared UI Library (`src/components/common/`)

Components consumed across multiple apps and pages.

### Page Structure

| File | Purpose |
|------|---------|
| `DetailShell.tsx` | Standard detail page wrapper with breadcrumb, mode header, feature badge |
| `DetailTabs.tsx` | Reusable tab navigation for detail pages (Overview, Comments, Actions, etc.) |
| `SimpleDetailHeader.tsx` | Lightweight header for simple detail pages |
| `SimpleDetailToolbar.tsx` | Action toolbar for simple entity forms (Save, Cancel, Edit, Delete) |
| `PageBreadCrumb.tsx` | Page breadcrumb navigation |
| `PageMeta.tsx` | Helmet-based page title/meta management (`AppWrapper`) |
| `DetailFeatureBadge.tsx` | Dev-only checklist badge showing implemented features |

### Data Display

| File | Purpose |
|------|---------|
| `AdvancedDataTable.tsx` | Feature-rich data table with drag-reorder, export, search fragments |
| `ButtonToolbar.tsx` | Toolbar for list pages with search, add, delete, import/export, print, column setup |
| `ColumnSetupDialog.tsx` | Modal for viewing/editing named column configurations |
| `RelatedTransactions.tsx` | Shows parent/child transaction relationships |
| `PrintReportDropdown.tsx` | Dropdown listing available print reports by model |
| `DualScrollbar.tsx` | Synchronized top+bottom scrollbar for wide content |
| `ChartTab.tsx` | Monthly/Quarterly/Yearly tab selector for charts |
| `ComponentCard.tsx` | Generic card wrapper with title and description |
| `TransactionTabs.tsx` | Second-row tab bar for transaction sub-types on org detail pages |
| `ItemTabs.tsx` | Third-row tab bar for item sub-types on org detail pages |

### Dev Utilities

| File | Purpose |
|------|---------|
| `DevBadge.tsx` | Small mono-font dev label controlled by `VITE_DEBUG_BADGES` |
| `DevIdentifier.tsx` | Hover-to-reveal component name badge (`withDevIdentifier` HOC) |

### UI Primitives

| File | Purpose |
|------|---------|
| `ErrorBoundary.tsx` | React error boundary class component |
| `RippleLoader.tsx` | Loading animation |
| `GlobalLoadingSpinner.tsx` | Full-screen overlay spinner (Redux-driven) |
| `ScrollToTop.tsx` | Scrolls to top on route change |
| `ThemeToggleButton.tsx` | Dark/light mode toggle |
| `ThemeTogglerTwo.tsx` | Alternative theme toggle (solid circle) |
| `Toster.tsx` | Redux-driven toast notification |
| `UnsavedChangesDialog.tsx` | Confirmation dialog with Save First option |
| `AuthInitializer.tsx` | Syncs Redux auth state with stored tokens on page load |
| `ModalForm.tsx` | Email verification modal form |
| `GridShape.tsx` | Decorative background grid SVG shapes |

---

## Common — Cross-App Components (`src/apps/common/components/`)

Domain-aware shared components living in the `apps/` tree.

### Root Files

| File | Purpose |
|------|---------|
| `TransactionToolbar.tsx` | Action toolbar for transaction detail pages (Save, Clone, Transfer, Print, Email, Delete) |
| `JsonFieldEditor.tsx` | Generic JSON editor for admin power users with syntax highlighting |
| `OrgSearchDialog.tsx` | Reusable modal for searching/selecting org records |
| `SingleWindowSection.tsx` | Compact titled section wrapper |
| `FormCoachAlert.tsx` | Form completeness checker (red=required, orange=incomplete, blue=suggestions) |

### Detail Cards (`detail/`)

| File | Purpose |
|------|---------|
| `BaseModelCards.tsx` | Standard Identity + Envelopes cards for BaseModel detail pages |
| `ScalarCard.tsx` | Collapsible card containing scalar field rows |
| `JsonCard.tsx` | Collapsible card for a single JSON field |
| `RawJsonCard.tsx` | Collapsible raw JSON card with stringify previews |
| `InfoRow.tsx` | Shared read-only horizontal label/value pair (`formatDisplayValue`) |
| `index.ts` | Barrel: InfoRow, ScalarCard, JsonCard, RawJsonCard, BaseModelCards |

### Panels (`panels/`)

> See also: [panels/README.md](../../src/apps/common/components/panels/README.md) for authoritative rules.

| File | Purpose |
|------|---------|
| `ActionsPanel.tsx` | Display/manage entity actions/tasks |
| `BasicInformationPanel.tsx` | Compact read-only org basic info |
| `CommentsPanel.tsx` | Generic comments with tabs (Public, Process, Partner, Notes) |
| `CommLinkPanel.tsx` | Inline panel for a single communication type |
| `CommunicationAddEditModal.tsx` | Modal for creating/editing communication records |
| `CommunicationsPanel.tsx` | Manage emails, phones, addresses, domains |
| `ContactPanel.tsx` | Flat list display of contacts linked to a record |
| `ContactPanelx2.tsx` | Contacts grouped by purpose with editing + `normalizeRefsLinksContact` |
| `DocumentsPanel.tsx` | File uploads, preview, download |
| `EmailGatePanel.tsx` | Pre-entry gate: email required before full contact form |
| `FinancialsPanel.tsx` | Summary of totals, cost, sell with margin calculation |
| `HistoryPanel.tsx` | Record history timeline |
| `ItemsPanel.tsx` | Line items from org's transactions + linked serials |
| `LinkagesPanel.tsx` | Cross-table record flow (Proposal→Order→Invoice→Payment) |
| `MetadataPanel.tsx` | Generic entity metadata editor (admin only) |
| `OrgLinkPanel.tsx` | All org FK associations for a contact |
| `PanelTable.tsx` | Shared tabular layout for panels with column persistence |
| `PaymentPanel.tsx` | Payments linked to entity |
| `PrefsPanel.tsx` | Entity `.prefs` editor |
| `QAPanel.tsx` | Unified Q&A (freeform + template-driven) |
| `RawDataPanel.tsx` | Raw JSON data display (admin) |
| `RefsPanel.tsx` | Entity `.refs` editor |
| `SerialPanel.tsx` | Serial numbers linked to entity |
| `ShippingPanel.tsx` | Shipping details for sell-side transactions |
| `TemplateQAPanel.tsx` | Template-driven Q&A with predefined choices, image attachments |
| `TransactionPanel.tsx` | Record header (ida, status, attention, email, phone, total, balance, priority) + TransactionToolbar |
| `TransactionsPanel.tsx` | Transactions for an org (proposals, orders, invoices, etc.) |

### Panel Utilities

| File | Purpose |
|------|---------|
| `types.ts` | `UserRole`, `EntityType`, `PanelPermissions`, `BasePanelProps`, `RefLink` |
| `usePermissions.ts` | Hook for panel-level permission checks |
| `getModelDetailPath.ts` | Maps model name + ID to detail route |
| `documentUpload.ts` | Upload file → create Document record → return RefLink |
| `qaUtils.ts` | Fetches question templates from Setting records |
| `index.ts` | Barrel export of all panels |

---

## Common — UI Primitives (`src/components/ui/`)

Low-level UI building blocks.

| File | Purpose |
|------|---------|
| `Spinner.tsx` | Loading spinner (xs/sm/md/lg sizes) |
| `PageHeader.tsx` | Page title with optional breadcrumb |
| `alert/Alert.tsx` | Alert component (success/error/warning/info) |
| `avatar/Avatar.tsx` | User avatar with size and status indicator |
| `badge/Badge.tsx` | Badge component (light/solid, colors) |
| `button/Button.tsx` | Button (primary/outline, sm/md) |
| `dropdown/Dropdown.tsx` | Dropdown container with click-outside close |
| `dropdown/DropdownItem.tsx` | Dropdown menu item (link or button) |
| `dropdown/SearchableSelect.tsx` | Searchable dropdown with keyboard navigation |
| `modal/CustomModal.tsx` | Form modal with mode (add/edit/view), submit, error display |
| `modal/index.tsx` | Base modal component with fullscreen option |
| `table/index.tsx` | Table, TableHeader, TableBody, TableRow, TableCell primitives |

---

## Common — Form Components (`src/components/form/`)

| File | Purpose |
|------|---------|
| `Form.tsx` | Simple form wrapper with onSubmit preventDefault |
| `HorizontalField.tsx` | Enterprise standard label-left field layout |
| `Label.tsx` | Form label with tailwind-merge styling |
| `Select.tsx` | Standard select dropdown |
| `MultiSelect.tsx` | Multi-select dropdown |
| `date-picker.tsx` | Flatpickr date picker (single/multiple/range/time) |
| `useColumnCount.tsx` | Hook for column count with localStorage persistence |
| `input/InputField.tsx` | Standard text input with validation states |
| `input/Checkbox.tsx` | Checkbox component |
| `input/Radio.tsx` | Radio button |
| `input/RadioSm.tsx` | Small radio button variant |
| `input/FileInput.tsx` | File input element |
| `input/TextArea.tsx` | Textarea with react-hook-form register |
| `input/CustTextArea.tsx` | Custom textarea with success/error states |
| `input/DropDown.tsx` | Select dropdown variant |
| `input/InternationalPhoneInput.tsx` | Phone input with country codes |
| `group-input/PhoneInput.tsx` | Phone input with country code selector |
| `switch/Switch.tsx` | Toggle switch component |

### Barrel Exports

| File | Exports |
|------|---------|
| `index.ts` | `InputField`, `TextareaField` |
| `wrapper.ts` | `Toster`, `ScrollToTop`, `ModalForm`, `Input`, `Select`, `DatePicker`, `PhoneInput`, `InternationalPhoneInput`, `TextArea`, `CustTextArea`, `DropDown` |

---

## By App — Transaction Components

### Shared (`src/apps/transactions/components/`)

| File | Purpose |
|------|---------|
| `TransactionDetailBase.tsx` | Base component for all transaction detail pages (~2964 lines) |
| `SummaryCard.tsx` | Transaction summary with CustomerSalesPanel, status, fields |
| `CustomerSalesPanel.tsx` | Customer search and financial info panel |
| `LinesCard.tsx` | Line items card with expand/collapse, notes, edit, copy, delete |
| `LineDetailsModal.tsx` | Slide-out panel for viewing/editing a transaction line |
| `TransactionItemSearch.tsx` | Shared item search for all transaction types |
| `PartySelector.tsx` | Unified customer/vendor/manufacturer searchable selector |
| `FieldLabel.tsx` | Consistent field label styling (bold=mandatory, italic=locked) |
| `MetadataPanel.tsx` | Transaction-specific metadata (history, health, flags, versioning) |
| `ContactLinksTable.tsx` | Tabular display of contact links with draggable columns |
| `ActivityLogTab.tsx` | Transaction history/audit log timeline |
| `QATab.tsx` | Transaction Q&A tab using template-driven questions |
| `QuickAddRecent.tsx` | Recently added items for quick re-adding |
| `InventoryCheckDialog.tsx` | Modal showing item inventory quantity buckets |
| `SplitLineModal.tsx` | Split line item across multiple shipments/warehouses |
| `PrintPreviewModal.tsx` | Document preview with print options |
| `ActionsModal.tsx` | Task/action modal for transaction contexts |
| `TransactionTaskModal.tsx` | Generic task/action modal for transactions |
| `TransactionTaskModal.types.ts` | Types: `TaskKind`, `TaskPriority`, `TransactionTaskFormState` |
| `useTransactionTasks.ts` | Hook for CRUD operations on transaction-linked tasks |
| `AddPaymentModal.tsx` | Modal for adding a new payment to an order |
| `ApplyPaymentModal.tsx` | Modal for applying a payment to an invoice |
| `PaymentDialog.tsx` | Full-featured payment dialog (card type, billing address, check fields) |
| `index.ts` | Barrel export |

### Print Templates (`src/apps/transactions/components/print/`)

| File | Purpose |
|------|---------|
| `PrintDocumentLayout.tsx` | Base print layout with party blocks, line items table |
| `printTypes.ts` | Types: `PaperSize`, `PrintParty`, `PrintDocumentProps`, format helpers |
| `OrderPrintDocument.tsx` | Print-ready order document + `mapJsonToOrderPrintData` |
| `InvoicePrintDocument.tsx` | Print-ready invoice document |
| `ProposalPrintDocument.tsx` | Print-ready proposal/quote document |
| `PurchasePrintDocument.tsx` | Print-ready purchase order document |
| `ReceiptPrintDocument.tsx` | Print-ready receipt document |
| `WorkorderPrintDocument.tsx` | Print-ready work order document |
| `AdjustmentPrintDocument.tsx` | Print-ready adjustment document |
| `index.ts` | Barrel export of all print components and types |

### Org-Level Shared (`src/apps/orgs/components/`)

| File | Purpose |
|------|---------|
| `OrgDetail.tsx` | Base organization detail/edit with reusable tabbed interface |
| `OrgEntityList.tsx` | Reusable DataTable wrapper for all org entity types |
| `OrgFinancialsPanel.tsx` | Tabbed financial data by org type |

---

## By App — Model Pages

### accounts

| Model | File | Purpose |
|-------|------|---------|
| **audit** | `pages/Audit.tsx` | Route wrapper → AuditList |
| | `pages/AuditDetail.tsx` | Form-based audit detail with zod schema |
| | `pages/AuditDisplay.tsx` | Display-pattern audit record |
| | `pages/AuditList.tsx` | AdvancedDataTable list |
| **currency** | `pages/Currency.tsx` | Route wrapper → CurrencyList |
| | `pages/CurrencyDetail.tsx` | Currency detail with ScalarCard/BaseModelCards |
| | `pages/CurrencyDisplay.tsx` | Display-pattern currency record |
| | `pages/CurrencyList.tsx` | AdvancedDataTable list |
| **exchange_rate** | `pages/ExchangeRate.tsx` | Route wrapper → ExchangeRateList |
| | `pages/ExchangeRateDetail.tsx` | Exchange rate detail with ScalarCard/BaseModelCards |
| | `pages/ExchangeRateDisplay.tsx` | Display-pattern exchange rate |
| | `pages/ExchangeRateList.tsx` | AdvancedDataTable list |
| **exchange_transaction** | `pages/ExchangeTransaction.tsx` | Route wrapper → ExchangeTransactionList |
| | `pages/ExchangeTransactionDetail.tsx` | Detail with ScalarCard/BaseModelCards |
| | `pages/ExchangeTransactionDisplay.tsx` | Display-pattern |
| | `pages/ExchangeTransactionList.tsx` | AdvancedDataTable list |
| **gl_account** | `pages/GLAccountDetail.tsx` | GL account detail |
| | `pages/GLAccountList.tsx` | AdvancedDataTable list |
| **gl_journal** | `pages/GLJournal.tsx` | Route wrapper → GLJournalList |
| | `pages/GLJournalDetail.tsx` | GL journal detail |
| | `pages/GLJournalDisplay.tsx` | Display-pattern |
| | `pages/GLJournalList.tsx` | AdvancedDataTable list |
| **ledger** | `pages/LedgerDisplay.tsx` | Ledger display |
| | `pages/LedgerList.tsx` | AdvancedDataTable list |
| | `pages/ReceivableList.tsx` | AR aging list using `manageAction` |
| **tax_jurisdiction** | `pages/TaxJurisdictionDisplay.tsx` | Display-pattern |
| | `pages/TaxJurisdictionList.tsx` | AdvancedDataTable list |
| **term** | `pages/TermDisplay.tsx` | Payment term display |
| | `pages/TermList.tsx` | AdvancedDataTable list |

### communications

| Model | File | Purpose |
|-------|------|---------|
| **address** | `pages/AddressDetail.tsx` | Enterprise-pattern address detail |
| | `pages/AddressList.tsx` | AdvancedDataTable list |
| | `pages/AddressListMob.tsx` | Mobile accordion list |
| **domain** | `pages/DomainDetail.tsx` | Domain detail |
| | `pages/domainList.tsx` | AdvancedDataTable list |
| | `pages/DomainListMob.tsx` | Mobile accordion list |
| **email** | `pages/Email.tsx` | Route wrapper → EmailList |
| | `pages/EmailDetail.tsx` | Email record detail |
| | `pages/EmailList.tsx` | AdvancedDataTable list |
| | `pages/EmailListMob.tsx` | Mobile accordion list |
| **phone** | `pages/PhoneDetail.tsx` | Phone record detail |
| | `pages/PhoneList.tsx` | AdvancedDataTable list |
| | `pages/PhoneListMob.tsx` | Mobile accordion list |

### core

| Model | File | Purpose |
|-------|------|---------|
| **action** | `pages/ActionDetail.tsx` | Action/task detail with form validation |
| | `pages/ActionList.tsx` | AdvancedDataTable with inline status toggle |
| **api_log** | `pages/APILogDetail.tsx` | API log detail with request/response body |
| | `pages/APILogList.tsx` | AdvancedDataTable list |
| **contact** | `pages/ContactDetail.tsx` | Primary contact detail — panels, CommLink, OrgLink, EmailGate |
| | `pages/ContactDetail2.tsx` | Variant: collapsible-card view of all fields |
| | `pages/ContactDetail3.tsx` | Variant: legacy form-based layout |
| | `pages/ContactList.tsx` | AdvancedDataTable with detail variant selection |
| | `pages/ContactListMob.tsx` | Mobile accordion list |
| **report** | `pages/Report.tsx` | Route wrapper → ReportList |
| | `pages/ReportDetail.tsx` | Report detail with HorizontalField layout |
| | `pages/ReportDisplay.tsx` | Display-pattern report |
| | `pages/ReportList.tsx` | AdvancedDataTable list |
| **setting** | `pages/SettingDetail.tsx` | Setting detail with HorizontalField layout |
| | `pages/SettingDisplay.tsx` | Display-pattern setting |
| | `pages/SettingList.tsx` | AdvancedDataTable list |
| **template** | `pages/TemplateDetail.tsx` | Template detail with many field icons |
| | `pages/TemplateDisplay.tsx` | Display-pattern template |
| | `pages/TemplateList.tsx` | AdvancedDataTable list |

### docs

| Model | File | Purpose |
|-------|------|---------|
| **document** | `pages/DocumentDetail.tsx` | Document detail with 3-column standard |
| | `pages/DocumentDisplay.tsx` | Display-pattern document |
| | `pages/DocumentIndex.tsx` | Documentation center landing page |
| | `pages/DocumentList.tsx` | AdvancedDataTable list |
| **linkage_entry** | `pages/LinkageEntryDisplay.tsx` | Linkage entry display |
| | `pages/LinkageEntryList.tsx` | AdvancedDataTable list |
| **question_answer** | `pages/QuestionAnswerDisplay.tsx` | Q&A display |
| | `pages/QuestionAnswerList.tsx` | AdvancedDataTable list |
| **tag** | `pages/TagDisplay.tsx` | Tag display |
| | `pages/TagList.tsx` | AdvancedDataTable list |

### orgs

| Model | File | Purpose |
|-------|------|---------|
| **customer** | `pages/CustomerDashboard.tsx` | Single-customer dashboard view |
| | `pages/CustomerDataPanel.tsx` | Raw field-value display (dev mode) |
| | `pages/CustomerDetail.tsx` | Full customer detail with form, tabs |
| | `pages/CustomerHeader.tsx` | Customer header card |
| | `pages/CustomerList.tsx` | AdvancedDataTable list |
| | `pages/CustomerListMob.tsx` | Mobile accordion list |
| **employee** | `pages/EmployeeDetail.tsx` | Employee detail using OrgDetail base |
| | `pages/EmployeeList.tsx` | Employee list using OrgEntityList |
| **manufacturer** | `pages/ManufacturerDisplay.tsx` | Manufacturer detail form |
| | `pages/ManufacturerList.tsx` | List using OrgEntityList |
| | `pages/ManufacturerListMob.tsx` | Mobile accordion list |
| **organization** | `pages/OrganizationDisplay.tsx` | Organization detail form |
| | `pages/OrganizationList.tsx` | List using OrgEntityList |
| | `pages/OrganizationListMob.tsx` | Mobile accordion list |
| **rep** | `pages/RepDisplay.tsx` | Sales rep detail form |
| | `pages/RepList.tsx` | List using OrgEntityList |
| | `pages/RepListMob.tsx` | Mobile accordion list |
| **vendor** | `pages/VendorDetail.tsx` | Full vendor detail with form, tabs |
| | `pages/VendorList.tsx` | AdvancedDataTable list |
| | `pages/VendorListMob.tsx` | Mobile accordion list |

### products

| Model | File | Purpose |
|-------|------|---------|
| **bill_of_material** | `pages/BillOfMaterialDetail.tsx` | BOM detail |
| | `pages/BillOfMaterialList.tsx` | AdvancedDataTable list |
| **catalog** | `pages/CatalogDetail.tsx` | Catalog detail |
| | `pages/CatalogDisplay.tsx` | Display-pattern |
| | `pages/CatalogList.tsx` | AdvancedDataTable list |
| **flow** | `pages/FlowDetail.tsx` | Flow detail |
| | `pages/FlowDisplay.tsx` | Display-pattern |
| | `pages/FlowList.tsx` | AdvancedDataTable list |
| **item** | `pages/ItemDashboard.tsx` | Single-item dashboard |
| | `pages/ItemDetail.tsx` | Enterprise item detail with two-column UX layout |
| | `pages/ItemList.tsx` | AdvancedDataTable list |
| **item_xref** | `pages/ItemXrefDetail.tsx` | Cross-reference detail |
| | `pages/ItemXrefDisplay.tsx` | Display-pattern |
| | `pages/ItemXrefList.tsx` | AdvancedDataTable list |
| **matrics** | `pages/MatricsDetail.tsx` | Metrics detail |
| | `pages/MatricsDisplay.tsx` | Display-pattern |
| | `pages/MatricsList.tsx` | AdvancedDataTable list |
| **org_item** | `pages/OrgItemDetail.tsx` | Org-item association detail |
| | `pages/OrgItemDisplay.tsx` | Display-pattern |
| | `pages/OrgItemList.tsx` | AdvancedDataTable list |
| **serial** | `pages/SerialDetail.tsx` | Serial number detail |
| | `pages/SerialDisplay.tsx` | Display-pattern |
| | `pages/SerialList.tsx` | AdvancedDataTable list |
| **service** | `pages/ServiceDetail.tsx` | Service detail |
| | `pages/ServiceDisplay.tsx` | Display-pattern |
| | `pages/ServiceList.tsx` | AdvancedDataTable list |
| **specification** | `pages/SpecificationDetail.tsx` | Specification detail |
| | `pages/SpecificationDisplay.tsx` | Display-pattern |
| | `pages/SpecificationList.tsx` | AdvancedDataTable list |
| **usage** | `pages/UsageDetail.tsx` | Usage detail |
| | `pages/UsageDisplay.tsx` | Display-pattern |
| | `pages/UsageList.tsx` | AdvancedDataTable list |
| **variant** | `pages/VariantDetail.tsx` | Variant detail |
| | `pages/VariantDisplay.tsx` | Display-pattern |
| | `pages/VariantList.tsx` | AdvancedDataTable list |
| **warehouse** | `pages/WarehouseDetail.tsx` | Warehouse detail |
| | `pages/WarehouseDisplay.tsx` | Display-pattern |
| | `pages/WarehouseList.tsx` | AdvancedDataTable list |

### support

| Model | File | Purpose |
|-------|------|---------|
| **campaign** | `pages/CampaignDetail.tsx` | Campaign detail |
| | `pages/CampaignList.tsx` | AdvancedDataTable list |

### sync

| Model | File | Purpose |
|-------|------|---------|
| **bundle** | `pages/BundleDetail.tsx` | Bundle detail |
| | `pages/BundleList.tsx` | AdvancedDataTable list |

### transactions

| Model | File | Purpose |
|-------|------|---------|
| **invoice** | `pages/InvoiceDetail.tsx` | Invoice detail via TransactionDetailBase |
| | `pages/InvoiceList.tsx` | AdvancedDataTable list |
| **invoice_line** | `pages/InvoiceLineDetail.tsx` | Invoice line detail |
| | `pages/InvoiceLineList.tsx` | AdvancedDataTable list |
| **order** | `pages/OrderDetail.tsx` | Order detail via TransactionDetailBase |
| | `pages/OrderList.tsx` | AdvancedDataTable list |
| **order_line** | `pages/OrderLineDetail.tsx` | Order line detail |
| | `pages/OrderLineList.tsx` | AdvancedDataTable list |
| **payment** | `pages/PaymentDetailPage.tsx` | Payment detail (not TransactionBaseModel) |
| | `pages/PaymentListPage.tsx` | AdvancedDataTable list |
| **project** | `pages/ProjectDetail.tsx` | Project detail via TransactionDetailBase |
| | `pages/ProjectList.tsx` | AdvancedDataTable list |
| **proposal** | `pages/ProposalDetail.tsx` | Proposal detail via TransactionDetailBase |
| | `pages/ProposalLineDetail.tsx` | Proposal line detail (ScalarCard/JsonCard) |
| | `pages/ProposalLineList.tsx` | Embedded proposal line list |
| | `pages/ProposalList.tsx` | AdvancedDataTable list |
| **proposal_line** | `pages/ProposalLineDetail.tsx` | Standalone proposal line detail |
| | `pages/ProposalLineList.tsx` | AdvancedDataTable list |
| **purchase** | `pages/PurchaseDetail.tsx` | Purchase detail via TransactionDetailBase |
| | `pages/PurchaseList.tsx` | AdvancedDataTable list |
| **purchase_line** | `pages/PurchaseLineDetail.tsx` | Purchase line detail |
| | `pages/PurchaseLineList.tsx` | AdvancedDataTable list |
| **receipt** | `pages/ReceiptDetail.tsx` | Receipt detail via TransactionDetailBase |
| | `pages/ReceiptList.tsx` | AdvancedDataTable list |
| **requisition** | `pages/RequisitionDetail.tsx` | Requisition detail via TransactionDetailBase |
| | `pages/RequisitionList.tsx` | AdvancedDataTable list |
| **workorder** | `pages/WorkorderDetail.tsx` | Work order detail via TransactionDetailBase |
| | `pages/WorkorderList.tsx` | AdvancedDataTable list |
| **workorder_line** | `pages/WorkOrderLineDetail.tsx` | Work order line detail |
| | `pages/WorkOrderLineList.tsx` | AdvancedDataTable list |

---

## qqq-Flagged Files — Review for Removal

93 files total. These are not imported by active code.

### `src/components/` (template/demo leftovers)

| File | Origin |
|------|--------|
| `qqq_InvoiceForm.tsx` | Unused standalone invoice form |
| `qqq_PurchaseForm.tsx` | Unused standalone purchase form |
| `qqq_CallReportForm.tsx` | Legacy form |
| `qqq_CustomerForm.tsx` | Legacy form |
| `qqq_InputField.tsx` | Superseded by `form/input/InputField.tsx` |
| `qqq_InvoicesList.tsx` | Superseded by `InvoiceList.tsx` in apps/ |
| `qqq_OrdersList.tsx` | Superseded by `OrderList.tsx` in apps/ |
| `qqq_ProposalForm.tsx` | Superseded by ProposalDetail in apps/ |
| `qqq_ProposalsList.tsx` | Superseded by ProposalList in apps/ |
| `qqq_QAList.tsx` | Superseded by QAPanel in panels/ |
| `qqq_ServiceForm.tsx` | Superseded by ServiceDetail in apps/ |
| `qqq_TaskMarkerForm.tsx` | Legacy form |
| `ecommerce/qqq_*.tsx` (7 files) | Dashboard template widgets — never wired |
| `form/form-elements/qqq_*.tsx` (10 files) | Demo/showcase components — never wired |
| `kanban/qqq_KanbanTaskModal.tsx` | Duplicate of `apps/utils/kanban/KanbanTaskModal.tsx` |
| `modals/qqq_LineItemModal.tsx` | Legacy modal |
| `tables/BasicTables/qqq_BasicTableOne.tsx` | Template demo table |
| `charts/bar/qqq_BarChartOne.tsx` | Template demo chart |
| `charts/line/qqq_LineChartOne.tsx` | Template demo chart |
| `transactions/common/qqq_AuditTrail.tsx` | Only consumed by other qqq files |
| `transactions/common/qqq_TransactionHeader.tsx` | Only consumed by qqq_OrderForm |
| `transactions/common/qqq_TransactionTotals.tsx` | Only consumed by qqq_OrderForm |
| `transactions/sales_order/qqq_OrderForm.tsx` | Superseded by OrderDetail in apps/ |
| `transactions/payments/qqq_PaymentProcessor.tsx` | Superseded by PaymentDialog |
| `transactions/reservations/qqq_ReservationManager.tsx` | Never wired |
| `ui/images/qqq_*.tsx` (3 files) | Template image gallery — never wired |
| `ui/videos/qqq_*.tsx` (5 files) | Template video gallery — never wired |

### `src/apps/` (dead code)

| File | Origin |
|------|--------|
| `core/contact/pages/qqq_ContactDetailStart.tsx` | Layout experiment |
| `core/contact/pages/qqq_ContactDetailDense.tsx` | Layout experiment |
| `core/contact/pages/qqq_ContactDetailHorizontal.tsx` | Layout experiment |
| `core/contact/pages/qqq_ContactDetailTwoColumn.tsx` | Layout experiment |
| `core/contact/pages/qqq_ContactDetailWithSelector.tsx` | Layout experiment |
| `core/contact/pages/qqq_ContactDetail_RijuButtons.tsx` | Styling experiment |
| `core/contact/pages/qqq_ContactList1.tsx` | Simpler list variant |
| `common/panels/qqq_EmailGatePanel_05-03-2026.tsx` | Dated backup |
| `common/panels/qqq_ModelDataPanel.tsx` | Never imported |
| `orgs/components/qqq_OrgList.tsx` | Component never imported |
| `transactions/invoice/pages/qqq_InvoiceDetailLegacy.tsx` | Legacy drag-and-drop |
| `transactions/proposal/pages/qqq_ProposalDetailVue.tsx` | Vue-style experiment |
| `transactions/proposal/pages/qqq_ProposalDetailVueReact.tsx` | Hybrid experiment |
| `transactions/proposal/components/qqq_*.tsx` (6 files) | Dead proposal components |
| `transactions/proposal/hooks/qqq_*.ts` (4 files) | Dead proposal hooks |
| `supports/campaign/pages/qqq_*.tsx` (2 files) | Superseded by support/ |
| `sync/connection/qqq_*.ts` (5 files) | Dead connection module |

### `src/` root-level

| File | Origin |
|------|--------|
| `hooks/qqq_useAuditTrail.ts` | Only consumed by qqq files |
| `model/qqq_httpResponse.interface.ts` | Superseded |
| `model/qqq_modelMap.ts` | Superseded |
| `model/qqq_opportunity.interface.ts` | Superseded |
| `pages/qqq_ItemDashboard.tsx` | Superseded by apps/ version |
| `type/qqq_kanban copy.ts` | Stale copy |
| `apps/qqq_test.tsx` | Test file |

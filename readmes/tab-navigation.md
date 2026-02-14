# Tab Navigation Reference

Which tabs appear on each Detail page, grouped by layout pattern.

---

## Tab Layouts

### Layout A — Full Org (CustomerDetail)

**standardTabs**: actions, comments, documents, history, raw  
**additionalTabs**: contacts, financial, metadata, prefs, qa, refs

| Page | File | Notes |
|------|------|-------|
| Customer | `orgs/models/customer/pages/CustomerDetail.tsx` | Badges: actions, comments, contacts, documents |

### Layout B — Vendor Org

**standardTabs**: actions, comments, documents, history, overview, raw  
**additionalTabs**: contacts, financial, metadata, prefs, qa, refs

| Page | File | Notes |
|------|------|-------|
| Vendor | `orgs/models/vendor/pages/VendorDetail.tsx` | Adds `overview` tab for extra form fields. Badges: comments, contacts |

### Layout C — Admin Org (OrgDetail)

**defaultTabs** (own tab bar, not `DetailTabs`):  
addresses, connections, contacts, data, docs, domains, emails, financial, gl_accounts, info, metadata, metrics, phones, prefs, qa, refs, relations

| Page | File | Notes |
|------|------|-------|
| Employee | `orgs/models/employee/pages/EmployeeDetail.tsx` | Thin wrapper → `OrgDetail` with `additionalTabs={[]}` |
| OrgDetail base | `orgs/components/OrgDetail.tsx` | Admin-only. All 17 tabs always visible |

### Layout D — Transaction (TransactionDetailBase)

**defaultTabs**: actions, comments, contacts, documents, financials, prefs, qa, raw  
**admin-only**: metadata, refs  
Extension points: `customTabsBefore`, `customTabsAfter` / `getCustomTabsAfter`

| Page | File | Custom Tabs After |
|------|------|-------------------|
| Order | `transactions/models/order/pages/OrderDetail.tsx` | shipping |
| Invoice | `transactions/models/invoice/pages/InvoiceDetail.tsx` | shipping, tax |
| Purchase | `transactions/models/purchase/pages/PurchaseDetail.tsx` | receiving |
| Proposal | `transactions/models/proposal/pages/ProposalDetail.tsx` | — |
| Receipt | `transactions/models/receipt/pages/ReceiptDetail.tsx` | — |
| Project | `transactions/models/project/pages/ProjectDetail.tsx` | — |
| Workorder | `transactions/models/workorder/pages/WorkorderDetail.tsx` | — |
| Requisition | `transactions/models/requisition/pages/RequisitionDetail.tsx` | — |

> Note: Transaction tabs use `financials` (plural). Org tabs use `financial` (singular).

### Layout E — Product Standard

**additionalTabs**: actions, comments, documents, history, refs, raw

| Page | File | Notes |
|------|------|-------|
| Catalog | `products/models/catalog/pages/CatalogDetail.tsx` | |
| Flow | `products/models/flow/pages/FlowDetail.tsx` | |
| Matrics | `products/models/matrics/pages/MatricsDetail.tsx` | |
| Service | `products/models/service/pages/ServiceDetail.tsx` | |
| Serial | `products/models/serial/pages/SerialDetail.tsx` | |
| Variant | `products/models/variant/pages/VariantDetail.tsx` | |
| Warehouse | `products/models/warehouse/pages/WarehouseDetail.tsx` | |
| Specification | `products/models/specification/pages/SpecificationDetail.tsx` | |
| Usage | `products/models/usage/pages/UsageDetail.tsx` | |
| Item Xref | `products/models/item_xref/pages/ItemXrefDetail.tsx` | |
| Org Item | `products/models/org_item/pages/OrgItemDetail.tsx` | |
| **Item** | `products/models/item/pages/ItemDetail.tsx` | Panels extracted from inline to tabs. Both view + edit paths |

**Exception — Bill of Material**: actions, comments, documents, history, raw (no `refs`)

### Layout F — Accounts

**standardTabs**: comments, actions, history, raw

| Page | File |
|------|------|
| Currency | `accounts/models/currency/pages/CurrencyDetail.tsx` |
| GL Account | `accounts/models/gl_account/pages/GLAccountDetail.tsx` |
| Exchange Rate | `accounts/models/exchange_rate/pages/ExchangeRateDetail.tsx` |
| Exchange Transaction | `accounts/models/exchange_transaction/pages/ExchangeTransactionDetail.tsx` |
| GL Journal | `accounts/models/gl_journal/pages/GLJournalDetail.tsx` |

### Layout G — Communications

**standardTabs**: contacts, comments, actions, documents, history, raw

| Page | File |
|------|------|
| Address | `communications/models/address/pages/AddressDetail.tsx` |
| Phone | `communications/models/phone/pages/PhoneDetail.tsx` |
| Email | `communications/models/email/pages/EmailDetail.tsx` |
| Domain | `communications/models/domain/pages/DomainDetail.tsx` |

### Layout H — Core / Docs (unique per model)

| Page | File | Tabs |
|------|------|------|
| Action | `core/models/action/pages/ActionDetail.tsx` | comments, documents, qa, contacts |
| API Log | `core/models/api_log/pages/APILogDetail.tsx` | Custom toggle (request/response) — modal overlay |
| Contact | `core/models/contact/pages/ContactDetail.tsx` | actions, comments, communications, documents, history, metadata, prefs, raw, refs |
| Document | `docs/models/document/pages/DocumentDetail.tsx` | actions, comments, documents, history, refs, raw |

### Layout I — Simple Detail (Standard 8-Tab)

**additionalTabs**: actions, comments, documents, history, metadata, prefs, raw, refs

All use the same `useDetailTabs` + `DetailTabs` pattern with `standardTabs=[]`.

| Page | File | Notes |
|------|------|-------|
| Setting | `core/models/setting/pages/SettingDetail.tsx` | |
| Report | `core/models/report/pages/ReportDetail.tsx` | |
| Template | `core/models/template/pages/TemplateDetail.tsx` | |
| Audit | `accounts/models/audit/pages/AuditDetail.tsx` | Older Label-based layout |
| Campaign | `support/models/campaign/pages/CampaignDetail.tsx` | |
| Bundle | `sync/models/bundle/pages/BundleDetail.tsx` | |
| Connection | `sync/models/connection/pages/ConnectionDetail.tsx` | HorizontalField layout |
| Connection (legacy) | `sync/connection/pages/ConnectionDetail.tsx` | Older Label-based layout |

---

## Pages Without Standard Tab Navigation

These are **not** standalone model Detail pages — they are inline line-item editors
embedded within their parent transaction's detail view:

| Page | File | Notes |
|------|------|-------|
| Invoice Line | `transactions/models/invoice_line/pages/InvoiceLineDetail.tsx` | Inline editor |
| Order Line | `transactions/models/order_line/pages/OrderLineDetail.tsx` | Inline editor |
| Purchase Line | `transactions/models/purchase_line/pages/PurchaseLineDetail.tsx` | Inline editor |
| Proposal Line | `transactions/models/proposal_line/pages/ProposalLineDetail.tsx` | Inline editor |
| Proposal Line (alt) | `transactions/models/proposal/pages/ProposalLineDetail.tsx` | Duplicate inline editor |
| Workorder Line | `transactions/models/workorder_line/pages/WorkOrderLineDetail.tsx` | Inline editor |

---

## Tab Availability Matrix

Which standard tabs appear in which layout:

| Tab | A (Customer) | B (Vendor) | C (Admin Org) | D (Transaction) | E (Product) | F (Accounts) | G (Comms) | H (Core) | I (Simple) |
|-----|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|
| actions | ✓ | ✓ | — | ✓ | ✓ | ✓ | ✓ | varies | ✓ |
| comments | ✓ | ✓ | — | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| communications | — | — | — | — | — | — | — | Contact | — |
| contacts | ✓ | ✓ | ✓ | ✓ | — | — | ✓ | varies | — |
| documents | ✓ | ✓ | ✓ | ✓ | ✓ | — | ✓ | varies | ✓ |
| financial | ✓ | ✓ | ✓ | ✓* | — | — | — | — | — |
| history | ✓ | ✓ | — | — | ✓ | ✓ | ✓ | varies | ✓ |
| metadata | ✓ | ✓ | ✓ | ✓† | ✓‡ | — | — | Contact | ✓ |
| overview | — | ✓ | — | — | — | — | — | — | — |
| prefs | ✓ | ✓ | ✓ | ✓ | ✓‡ | — | — | Contact | ✓ |
| qa | ✓ | ✓ | ✓ | ✓ | — | — | — | Action | — |
| raw | ✓ | ✓ | — | ✓ | ✓ | ✓ | ✓ | varies | ✓ |
| refs | ✓ | ✓ | ✓ | ✓† | ✓ | — | — | varies | ✓ |

\* Transactions use `financials` (plural)  
† Admin-only in transactions  
‡ Item + Contact only (extracted from inline panels)

---

## Component Architecture

```
DetailTabs (src/components/common/DetailTabs.tsx)
├── standardTabs — built-in tab configs (overview, contacts, comments, actions, documents, history, raw)
├── additionalTabs — model-specific TabConfig[] injected by each Detail page
└── badges — Record<string, number> for tab badge counts

OrgDetail (src/apps/orgs/components/OrgDetail.tsx)
├── Own custom tab bar (does not use DetailTabs)
├── defaultTabs — 17 admin-level tabs
└── additionalTabs — passed in from wrappers (EmployeeDetail passes [])

TransactionDetailBase (src/apps/transactions/components/TransactionDetailBase.tsx)
├── defaultTabs — 8 standard + 2 admin-only
├── customTabsBefore — injected before defaults
├── customTabsAfter / getCustomTabsAfter — injected after defaults
└── renderCustomTab — callback for custom tab content
```

All file paths are relative to `src/apps/`.

---

## Complete Inventory (52 Detail Files)

Every `*Detail.tsx` file in `src/apps/`, with its tab mechanism:

| # | File | Has Tabs | Mechanism |
|---|------|:--------:|----------|
| 1 | `orgs/components/OrgDetail.tsx` | ✓ | Custom tab bar (17 `defaultTabs`) |
| 2 | `orgs/models/employee/pages/EmployeeDetail.tsx` | ✓ | OrgDetail wrapper |
| 3 | `orgs/models/customer/pages/CustomerDetail.tsx` | ✓ | `DetailTabs` + `useDetailTabs` |
| 4 | `orgs/models/vendor/pages/VendorDetail.tsx` | ✓ | `DetailTabs` + `useState` |
| 5 | `transactions/models/order/pages/OrderDetail.tsx` | ✓ | `TransactionDetailBase` |
| 6 | `transactions/models/invoice/pages/InvoiceDetail.tsx` | ✓ | `TransactionDetailBase` |
| 7 | `transactions/models/purchase/pages/PurchaseDetail.tsx` | ✓ | `TransactionDetailBase` |
| 8 | `transactions/models/proposal/pages/ProposalDetail.tsx` | ✓ | `TransactionDetailBase` |
| 9 | `transactions/models/receipt/pages/ReceiptDetail.tsx` | ✓ | `TransactionDetailBase` |
| 10 | `transactions/models/workorder/pages/WorkorderDetail.tsx` | ✓ | `TransactionDetailBase` |
| 11 | `transactions/models/project/pages/ProjectDetail.tsx` | ✓ | `TransactionDetailBase` |
| 12 | `transactions/models/requisition/pages/RequisitionDetail.tsx` | ✓ | `TransactionDetailBase` |
| 13 | `transactions/models/invoice_line/pages/InvoiceLineDetail.tsx` | — | Inline line editor |
| 14 | `transactions/models/order_line/pages/OrderLineDetail.tsx` | — | Inline line editor |
| 15 | `transactions/models/purchase_line/pages/PurchaseLineDetail.tsx` | — | Inline line editor |
| 16 | `transactions/models/proposal_line/pages/ProposalLineDetail.tsx` | — | Inline line editor |
| 17 | `transactions/models/proposal/pages/ProposalLineDetail.tsx` | — | Inline line editor (alt) |
| 18 | `transactions/models/workorder_line/pages/WorkOrderLineDetail.tsx` | — | Inline line editor |
| 19 | `core/models/contact/pages/ContactDetail.tsx` | ✓ | `DetailTabs` + `useDetailTabs` |
| 20 | `core/models/api_log/pages/APILogDetail.tsx` | ✓ | Custom toggle (request/response) |
| 21 | `core/models/action/pages/ActionDetail.tsx` | ✓ | `DetailTabs` + `useDetailTabs` |
| 22 | `core/models/setting/pages/SettingDetail.tsx` | ✓ | `DetailTabs` + `useDetailTabs` |
| 23 | `core/models/report/pages/ReportDetail.tsx` | ✓ | `DetailTabs` + `useDetailTabs` |
| 24 | `core/models/template/pages/TemplateDetail.tsx` | ✓ | `DetailTabs` + `useDetailTabs` |
| 25 | `accounts/models/audit/pages/AuditDetail.tsx` | ✓ | `DetailTabs` + `useDetailTabs` |
| 26 | `accounts/models/currency/pages/CurrencyDetail.tsx` | ✓ | `DetailTabs` + `useDetailTabs` |
| 27 | `accounts/models/exchange_rate/pages/ExchangeRateDetail.tsx` | ✓ | `DetailTabs` + `useDetailTabs` |
| 28 | `accounts/models/exchange_transaction/pages/ExchangeTransactionDetail.tsx` | ✓ | `DetailTabs` + `useDetailTabs` |
| 29 | `accounts/models/gl_account/pages/GLAccountDetail.tsx` | ✓ | `DetailTabs` + `useDetailTabs` |
| 30 | `accounts/models/gl_journal/pages/GLJournalDetail.tsx` | ✓ | `DetailTabs` + `useDetailTabs` |
| 31 | `products/models/item/pages/ItemDetail.tsx` | ✓ | `DetailTabs` + `useDetailTabs` |
| 32 | `products/models/catalog/pages/CatalogDetail.tsx` | ✓ | `DetailTabs` + `useDetailTabs` |
| 33 | `products/models/flow/pages/FlowDetail.tsx` | ✓ | `DetailTabs` + `useDetailTabs` |
| 34 | `products/models/serial/pages/SerialDetail.tsx` | ✓ | `DetailTabs` + `useDetailTabs` |
| 35 | `products/models/service/pages/ServiceDetail.tsx` | ✓ | `DetailTabs` + `useDetailTabs` |
| 36 | `products/models/warehouse/pages/WarehouseDetail.tsx` | ✓ | `DetailTabs` + `useDetailTabs` |
| 37 | `products/models/item_xref/pages/ItemXrefDetail.tsx` | ✓ | `DetailTabs` + `useDetailTabs` |
| 38 | `products/models/specification/pages/SpecificationDetail.tsx` | ✓ | `DetailTabs` + `useDetailTabs` |
| 39 | `products/models/bill_of_material/pages/BillOfMaterialDetail.tsx` | ✓ | `DetailTabs` + `useDetailTabs` |
| 40 | `products/models/usage/pages/UsageDetail.tsx` | ✓ | `DetailTabs` + `useDetailTabs` |
| 41 | `products/models/variant/pages/VariantDetail.tsx` | ✓ | `DetailTabs` + `useDetailTabs` |
| 42 | `products/models/matrics/pages/MatricsDetail.tsx` | ✓ | `DetailTabs` + `useDetailTabs` |
| 43 | `products/models/org_item/pages/OrgItemDetail.tsx` | ✓ | `DetailTabs` + `useDetailTabs` |
| 44 | `communications/models/email/pages/EmailDetail.tsx` | ✓ | `DetailTabs` + `useDetailTabs` |
| 45 | `communications/models/phone/pages/PhoneDetail.tsx` | ✓ | `DetailTabs` + `useDetailTabs` |
| 46 | `communications/models/domain/pages/DomainDetail.tsx` | ✓ | `DetailTabs` + `useDetailTabs` |
| 47 | `communications/models/address/pages/AddressDetail.tsx` | ✓ | `DetailTabs` + `useDetailTabs` |
| 48 | `sync/models/bundle/pages/BundleDetail.tsx` | ✓ | `DetailTabs` + `useDetailTabs` |
| 49 | `sync/models/connection/pages/ConnectionDetail.tsx` | ✓ | `DetailTabs` + `useDetailTabs` |
| 50 | `sync/connection/pages/ConnectionDetail.tsx` | ✓ | `DetailTabs` + `useDetailTabs` |
| 51 | `support/models/campaign/pages/CampaignDetail.tsx` | ✓ | `DetailTabs` + `useDetailTabs` |
| 52 | `docs/models/document/pages/DocumentDetail.tsx` | ✓ | `DetailTabs` + `useDetailTabs` |

**Summary**: 46 of 52 have tab navigation. The 6 without are all `*LineDetail.tsx` inline editors.

| Mechanism | Count |
|-----------|------:|
| `DetailTabs` + `useDetailTabs` | 36 |
| `TransactionDetailBase` | 8 |
| Custom tab bar | 2 |
| OrgDetail wrapper | 1 |
| `DetailTabs` + `useState` | 1 |
| None (line editors) | 6 |

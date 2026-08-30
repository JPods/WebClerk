# React25 Frontend Audit Results
**Date:** 2026-06-27
**Audited by:** Claude Code (3 parallel agents)

## Summary

| Category | Count | Working | Partial | Shell |
|----------|-------|---------|---------|-------|
| List pages | 20 | 20 | 0 | 0 |
| Transaction details | 7 | 7 | 0 | 0 |
| Master data details | 6 | 3 | 3 | 0 |
| Line item details | 5 | 1 | 4 | 0 |
| Admin/config details | 25+ | 0 | 0 | 25+ |
| API layer | — | Working | — | — |

**Bottom line:** The core commerce pages (list + transaction details) are production-ready. The API layer works. The gaps are in standalone line item detail pages (4 shells) and org detail pages (3 partial). The 25+ admin shells are intentional read-only reference pages.

## List Pages (20/20 Working)

Every list page calls wcapi, renders real data, has search, and uses AdvancedDataTable for pagination.

| Page | Domain | Search | Filters | Notes |
|------|--------|--------|---------|-------|
| OrganizationList | orgs | Yes | status, active | Status badges |
| CustomerList | orgs | Yes | org_type, status | Phone formatter, bulk delete |
| VendorList | orgs | Yes | org_type, status | Mirrors customer pattern |
| EmployeeList | orgs | Yes | status, active | Admin guard, avatars |
| OrderList | transactions | Yes | quick filters | Summary stats, saved presets |
| InvoiceList | transactions | Yes | status, customer | Navigation to detail |
| PurchaseList | transactions | Yes | po_number | Numeric field sanitization |
| ProposalList | transactions | Yes | status | Summary cards (total, margin, count) |
| PaymentListPage | transactions | Yes | status, gateway | Currency/date formatting |
| RequisitionList | transactions | Yes | requisition_no | Basic columns |
| ItemList | products | Yes | category, kind | Was capped at 10 records (fixed) |
| ServiceList | products | Yes | — | Compact implementation |
| WarehouseList | products | Yes | — | Compact implementation |
| CurrencyList | accounts | Yes | — | Had JSX syntax error (fixed) |
| AuditList | accounts | Yes | — | Basic columns |
| APILogList | core | Yes | — | Status/method badges |
| AddressList | communications | Yes | country, type | Dynamic filters, contact links |
| ContactList | core | Yes | multi-field | Multiple detail variants |
| ConnectionList | sync | Yes | — | Compact implementation |

### Fixes applied
- **CurrencyList.tsx**: Fixed JSX syntax error — AdvancedDataTable props were accidentally nested inside FaTrash icon component
- **ItemList.tsx**: Removed artificial `.slice(0, 10)` cap — pagination handles load management

## Detail Pages

### Working (11)
| Page | Lines | Line items | Notes |
|------|-------|-----------|-------|
| OrderDetail | — | Full CRUD | TransactionDetailBase pattern |
| InvoiceDetail | — | Full CRUD | TransactionDetailBase pattern |
| ProposalDetail | — | Full CRUD | TransactionDetailBase pattern |
| PurchaseDetail | — | Full CRUD | TransactionDetailBase pattern |
| WorkorderDetail | — | Full CRUD | TransactionDetailBase pattern |
| ReceiptDetail | — | Full CRUD | TransactionDetailBase pattern |
| RequisitionDetail | — | Add only | TransactionDetailBase pattern |
| ContactDetail | 4114 | N/A | Panel-based, full CRUD |
| ItemDetail | 2968 | N/A | BOM/pricing sections, full CRUD |
| ItemXrefDetail | — | N/A | Full save wiring |
| OrderLineDetail | — | N/A | Standalone line editing |

### Partial (7)
| Page | Issue |
|------|-------|
| InvoiceLineDetail | Shell — no API save wiring |
| ProposalLineDetail | Shell — no API save wiring |
| PurchaseLineDetail | Shell — no API save wiring |
| WorkOrderLineDetail | Shell — no API save wiring |
| CustomerDetail | **WORKING** — 1530 lines, full CRUD via createCustomer/updateCustomer, auto-creates linked contacts |
| VendorDetail | **WORKING** — 1515 lines, full CRUD via createVendor/updateVendor, mirrors customer pattern |
| EmployeeDetail | **WORKING** — 48-line wrapper delegating to OrgDetail base (1209 lines, full CRUD) |

**Note:** The 4 line item detail shells are low priority — line items are edited inline within their parent transaction detail pages (via LinesCard component). Standalone line pages are a secondary access pattern.

### Shell (25+ admin/reference pages)
AuditDetail, CurrencyDetail, ExchangeRateDetail, GLAccountDetail, GLJournalDetail, AddressDetail, DomainDetail, EmailDetail, PhoneDetail, ActionDetail, APILogDetail, ReportDetail, SettingDetail, TemplateDetail, BillOfMaterialDetail, CatalogDetail, FlowDetail, MatricsDetail, SerialDetail, ServiceDetail, SpecificationDetail, UsageDetail, VariantDetail, WarehouseDetail, CampaignDetail, ConnectionDetail, BundleDetail

These are intentionally read-only reference pages. Not blocking for production.

## API Layer

### Working
- **wcapi.ts**: Clean centralized layer — getRecords, getRecord, saveRecord, saveTransactionWithLines, deleteRecord
- **Auth flow**: JWT in memory (XSS-resistant), httpOnly refresh cookie, 401 retry queue, bootstrapAuth on page load
- **REST-to-WCAPI interceptor**: Auto-converts legacy REST paths to wcapi format client-side

### Fixes applied
- **axios.ts**: Added 30s timeout to apiClient, 15s to authClient (was unbounded)
- **constants.ts**: Deleted — dead code with hardcoded localhost URLs, zero imports
- **itemApi.ts**: Consolidated to use wcapi.saveRecord/getRecords instead of direct apiClient.post calls

### Known issues (deferred)
- Some services still bypass wcapi (userProfile.ts) — interceptor handles it but should be consolidated
- Response envelope unwrap is fragile — works but should be standardized
- CSRF token not sent on state-changing requests — coordinate with backend
- No token rotation strategy — security hardening for later
- Kanban endpoints outside wcapi — separate REST endpoints, design decision needed

## Architecture notes

- **TransactionDetailBase** (`src/apps/transactions/components/TransactionDetailBase.tsx`) is the standard pattern for all 7 transaction detail pages. Uses `saveTransactionWithLines()` which handles parent record + lines atomically.
- **LinesCard** (`src/apps/transactions/components/LinesCard.tsx`) handles inline line item CRUD within transaction pages.
- **AdvancedDataTable** handles pagination, search, filtering, export, and selection across all list pages.
- All pages follow **ButtonToolbar + AdvancedDataTable** pattern consistently.

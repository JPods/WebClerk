# API Migration: REST to WCAPI

This document tracks the migration from individual RESTful API calls to the unified wcapi endpoints.

## WCAPI Endpoint Reference

All data access should use these standardized endpoints:

| Operation | Endpoint | Method | Parameters |
|-----------|----------|--------|------------|
| **List** | `/wcapi/get/` | GET | `model_name`, `limit?`, `offset?`, `search?`, `filters?` |
| **Detail** | `/wcapi/get/` | GET | `model_name`, `id` |
| **Create** | `/wcapi/save/` | POST | Body: `{ model_name, data }` |
| **Update** | `/wcapi/save/` | POST | Body: `{ model_name, id, data }` |
| **Delete** | `/wcapi/delete/` | GET/POST | `?model_name=X&id=Y` or Body: `{ model_name, id }` |

---

## Current API File Audit

### Summary (Updated)

| Category | Count | Status |
|----------|-------|--------|
| ✅ Using centralized wcapi | 17 | **Good - No changes needed** |
| ✅ Delete patterns fixed | 37 | **COMPLETED** |
| ⚠️ Hybrid (wcapi + PostLoginURL) | 4 | **Needs consolidation** |
| 🔶 Direct apiClient + PostLoginURL | 2 | **Should migrate to wcapi** |
| 📌 Custom endpoints | 2 | **OK - Special cases** |

> **Migration Status:** All 37 files with broken `apiClient.delete()` patterns have been migrated to use `deleteRecord()` from `@/api/wcapi`.

---

## ✅ Files Already Using WCAPI (No Changes Needed)

These files properly import from `@/api/wcapi`:

- `src/apps/accounts/models/term/services/termApi.ts`
- `src/apps/accounts/models/currency/services/currencyApi.ts`
- `src/apps/accounts/models/audit/services/auditApi.ts`
- `src/apps/core/models/action/services/actionApi.ts`
- `src/apps/transactions/models/invoice/services/invoiceApi.ts`
- `src/apps/transactions/models/invoice_line/services/invoiceLineApi.ts`
- `src/apps/transactions/models/order/services/orderApi.ts`
- `src/apps/transactions/models/order_line/services/orderLineApi.ts`
- `src/apps/transactions/models/proposal/services/proposalApi.ts`
- `src/apps/transactions/models/proposal_line/services/proposalLineApi.ts`
- `src/apps/transactions/models/project/services/projectApi.ts`
- `src/apps/transactions/models/purchase/services/purchaseOrderApi.ts`
- `src/apps/transactions/models/purchase_line/services/purchaseOrderLineApi.ts`
- `src/apps/transactions/models/receipt/services/purchaseReceiptApi.ts`
- `src/apps/transactions/models/workorder/services/workorderApi.ts`
- `src/apps/transactions/models/workorder_line/services/workOrderLineApi.ts`
- `src/apps/transactions/models/requisition/services/requisitionApi.ts`

---

## ✅ Completed: Delete Pattern Migration

All files that previously used `apiClient.delete()` have been migrated to use `deleteRecord()` from `@/api/wcapi`.

### Migration Applied:

**Before (Wrong):**
```typescript
// ❌ WRONG - This was failing!
const res = await apiClient.delete(PostLoginURL.allTypes + id + "/");
```

**After (Correct):**
```typescript
// ✅ CORRECT - Now using wcapi.deleteRecord()
import { deleteRecord } from '@/api/wcapi';

export const deleteItem = async (id: number) => {
  return deleteRecord("item", id);
};
```

### Files Migrated (37 total):

| File | Model |
|------|-------|
| `src/apps/communications/models/domain/services/domainApi.ts` | domain |
| `src/apps/sync/models/bundle/services/bundleApi.ts` | bundle |
| `src/apps/sync/models/connection/services/connectionApi.ts` | connection |
| `src/apps/accounts/models/exchange_rate/services/exchangeRateApi.ts` | exchange_rate |
| `src/apps/accounts/models/gl_account/services/glAccountApi.ts` | gl_account |
| `src/apps/accounts/models/exchange_transaction/services/exchangeTransactionApi.ts` | exchange_transaction |
| `src/apps/accounts/models/gl_journal/services/glJournalApi.ts` | gl_journal |
| `src/apps/orgs/models/customer/services/customerApi.ts` | customer |
| `src/apps/orgs/models/vendor/services/vendorApi.ts` | vendor |
| `src/apps/orgs/models/employee/services/employeeApi.ts` | employee |
| `src/apps/orgs/models/rep/services/repApi.ts` | rep |
| `src/apps/orgs/models/organization/services/organizationApi.ts` | organization |
| `src/apps/orgs/models/manufacturer/services/manufacturerApi.ts` | manufacturer |
| `src/apps/docs/models/question_answer/services/questionAnswerApi.ts` | question_answer |
| `src/apps/docs/models/tag/services/tagApi.ts` | tag |
| `src/apps/docs/models/document/services/documentApi.ts` | document |
| `src/apps/core/models/setting/services/settingApi.ts` | setting |
| `src/apps/core/models/notification/services/notificationApi.ts` | notification |
| `src/apps/core/models/contact/services/contactApi.ts` | contact |
| `src/apps/core/models/report/services/reportApi.ts` | report |
| `src/apps/core/models/template/services/templateApi.ts` | template |
| `src/apps/products/models/flow/services/flowApi.ts` | flow |
| `src/apps/products/models/item_xref/services/itemXrefApi.ts` | item_xref |
| `src/apps/products/models/serial/services/serialApi.ts` | serial |
| `src/apps/products/models/warehouse/services/warehouseApi.ts` | warehouse |
| `src/apps/products/models/service/services/serviceApi.ts` | service |
| `src/apps/products/models/bill_of_material/services/billOfMaterialApi.ts` | bill_of_material |
| `src/apps/products/models/variant/services/variantApi.ts` | variant |
| `src/apps/products/models/item/services/itemApi.ts` | item |
| `src/apps/products/models/specification/services/specificationApi.ts` | specification |
| `src/apps/products/models/catalog/services/catalogApi.ts` | catalog |
| `src/apps/products/models/usage/services/usageApi.ts` | usage |
| `src/apps/products/models/org_item/services/orgItemApi.ts` | org_item |
| `src/apps/products/models/matrics/services/matricsApi.ts` | matrics |
| `src/apps/support/models/campaign/services/campaignApi.ts` | campaign |

---

## Migration Template

Replace individual API files with this standard pattern:

```typescript
/**
 * {ModelName} API - Uses centralized wcapi endpoints
 */
import { getRecords, getRecord, saveRecord, deleteRecord } from '@/api/wcapi';

const MODEL_NAME = 'model_name';

// List all records
export async function fetch{ModelName}s(params?: { limit?: number; offset?: number; search?: string }) {
  return getRecords(MODEL_NAME, params);
}

// Get single record by ID
export async function fetch{ModelName}(id: number) {
  return getRecord(MODEL_NAME, id);
}

// Create new record
export async function create{ModelName}(data: Create{ModelName}Request) {
  return saveRecord(MODEL_NAME, data);
}

// Update existing record
export async function update{ModelName}(id: number, data: Update{ModelName}Request) {
  return saveRecord(MODEL_NAME, { id, ...data });
}

// Delete record
export async function delete{ModelName}(id: number) {
  return deleteRecord(MODEL_NAME, id);
}
```

---

## Utility: REST to WCAPI Route Map

A new utility has been created to help with migration:

**Location:** `src/api/restToWcapi.ts`

### Key Functions:

```typescript
import { 
  convertRestToWcapi,
  getWcapiEndpoint,
  buildSaveBody,
  REST_PATH_TO_MODEL 
} from '@/api/restToWcapi';

// Convert a RESTful path to wcapi request
convertRestToWcapi('/api/orgs/customer/42', 'GET');
// { endpoint: '/wcapi/get/', method: 'GET', params: { model_name: 'customer', id: 42 } }

convertRestToWcapi('/api/orgs/customer/42', 'DELETE');
// { endpoint: '/wcapi/delete/', method: 'GET', params: { model_name: 'customer', id: 42 } }

// Get endpoint for operation
getWcapiEndpoint('detail', 'customer', 42);
// { url: '/wcapi/get/?model_name=customer&id=42', method: 'GET' }

// Build delete body (for POST)
buildDeleteBody('customer', 42);
// { model_name: 'customer', id: 42 }
```

---

## Path Pattern Reference

| REST Path Pattern | WCAPI model_name |
|-------------------|------------------|
| `/api/orgs/customer/*` | `customer` |
| `/api/orgs/vendor/*` | `vendor` |
| `/api/orgs/employee/*` | `employee` |
| `/api/transactions/order/*` | `order` |
| `/api/transactions/sales-order/*` | `order` |
| `/api/transactions/invoice/*` | `invoice` |
| `/api/transactions/purchase/*` | `purchase` |
| `/api/transactions/purchase-order/*` | `purchase` |
| `/api/transactions/proposal/*` | `proposal` |
| `/api/transactions/workorder/*` | `workorder` |
| `/api/products/item/*` | `item` |
| `/api/products/service/*` | `service` |
| `/api/products/warehouse/*` | `warehouse` |
| `/api/communications/email/*` | `email` |
| `/api/communications/phone/*` | `phone` |
| `/api/communications/address/*` | `location` |
| `/api/accounts/gl-account/*` | `gl_account` |
| `/api/accounts/currency/*` | `currency` |
| `/api/docs/document/*` | `document` |
| `/api/docs/tag/*` | `tag` |

See `src/api/restToWcapi.ts` for complete mapping.

---

## Migration Priority

1. **URGENT**: Fix 36 files with wrong delete pattern
2. **High**: Consolidate hybrid files to use wcapi consistently  
3. **Medium**: Migrate remaining direct apiClient files
4. **Low**: Clean up duplicate files (e.g., `sync/connection` vs `sync/models/connection`)

---

## Testing After Migration

After migrating a file, verify:

1. List/index pages load correctly
2. Detail pages load single records
3. Create operations work (check network tab for `POST /wcapi/save/`)
4. Update operations work
5. Delete operations work (uses `/wcapi/delete/` endpoint)

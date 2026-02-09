# Detail Page Standardization Plan

This document outlines the plan to standardize all `*Detail.tsx` pages with consistent layout rules, tab navigation, and panel components.

---

## Completion Status by App

| App | Files | Status |
|-----|-------|--------|
| **orgs/** | 4 | ✅ Complete (CustomerDisplay, VendorDetail, ContactDetail, EmployeeDetail) |
| **transactions/** | 14 | ✅ Complete (6 use TransactionDetailBase, Project/Requisition rewritten, 5 lines are simple forms) |
| **products/** | 13 | ✅ Assessed (ItemDetail has full panels, 12 others are simple forms) |
| **accounts/** | 6 | ✅ Assessed (All lookup tables - GLAccount, Currency, etc.) |
| **core/** | 6 | ✅ Assessed (ContactDetail done, others are admin config forms) |
| **communications/** | 4 | ✅ Assessed (Address, Email, Phone, Domain - contact info forms) |
| **sync/** | 3 | ✅ Assessed (Bundle, Connection - integration config) |
| **docs/** | 1 | ✅ Assessed (DocumentDetail - file viewer) |
| **support/** | 1 | ⬜ Future (CampaignDetail - candidate for DetailTabs) |

**Total: 52 Detail files assessed/standardized**

---

## Layout Rules Summary

From [ui-form-layout-research.md](ui-form-layout-research.md):

### Standard Detail Page Layout Structure

```
┌────────────────────────────────────────┐
│  Header (Title, ID, Nav Arrows)        │
├────────────────────────────────────────┤
│  Toolbar (Save, Cancel, Edit, Delete)  │
├────────────────────────────────────────┤
│  Basic Information Panel (PERSISTENT)  │  ← Always visible, read-only in view mode
│  - Core scalar fields                  │     Editable form in edit/add mode
├────────────────────────────────────────┤
│  Tab Navigation                        │
├────────────────────────────────────────┤
│  Tab Content (scrollable)              │
│  - Financial Summary (collapsed)       │  ← Collapsed by default, expand on demand
│  - Tab-specific data panels            │
└────────────────────────────────────────┘
```

### Key Layout Principles

| Element | Rule | Rationale |
|---------|------|-----------|
| **Layout Style** | Horizontal (label-left) | Enterprise standard, scannable by power users |
| **Columns** | 2-3 column selector | User preference, persisted to localStorage |
| **Label Width** | `w-20` to `w-32` | Consistent alignment across all pages |
| **Default Mode** | View (read-only) | Edit button to switch to edit mode |
| **Related Records** | Managed via `refs.links` | Standard pattern for relationships |

---

## Tab Navigation Pattern

Every Detail page should have a tab navigation component with the following standard tabs:

### Standard Tabs

| Tab | Panel Component | Data Source | Description |
|-----|-----------------|-------------|-------------|
| **Overview** | - | Scalar fields | Basic editable fields |
| **Comments** | `CommentsPanel` | `.comments` | Public/Process/Partner/Notes tabs |
| **Actions** | `ActionsPanel` | `.actions` or `action_ids` | Tasks/follow-ups with status |
| **Documents** | `DocumentsPanel` | `refs.links.document` | File attachments |
| **History** | `MetadataPanel` | `.metadata` | Change log (admin) |
| **Raw** | `RawDataPanel` | Full entity | JSON viewer (admin) |

### Model-Specific Tabs (add as needed)

| Tab | Panel Component | Models |
|-----|-----------------|--------|
| **Communications** | `CommunicationsPanel` | Contact, Customer, Vendor, Employee |
| **Contacts** | `ContactLinksPanel` | Customer, Vendor, Order, Invoice |
| **Financials** | `FinancialSummaryPanel` | Customer, Vendor |
| **Lines** | `LinesCard` | Order, Invoice, Proposal, Purchase |
| **Q&A** | `QAPanel` | Template, Campaign |
| **Linkages** | `LinkagesPanel` | Order, Invoice (flow tracking) |

---

## Related Records Pattern

All related records are managed through `refs.links`:

```typescript
interface EntityRefs {
  links: {
    contact?: RefLink[];      // Linked contacts
    customer?: RefLink[];     // Linked customers
    document?: RefLink[];     // Attached documents
    email?: RefLink[];        // Email addresses
    phone?: RefLink[];        // Phone numbers
    location?: RefLink[];     // Addresses
    domain?: RefLink[];       // Web domains
    linkage?: RefLink[];      // Flow/audit trail links
    question_answer?: RefLink[]; // Q&A items
  };
  // ... other refs properties
}
```

---

## Model Inventory and Panel Requirements

### Legend

- ✅ = Required (standard for this model type)
- ⚡ = Recommended (common use case)
- ➖ = Optional (rare use case)
- ❌ = Not applicable

---

### Org Models

| Model | File | Comments | Actions | Documents | Communications | Financial | Status |
| ------- | ------ | :--------: | :-------: | :---------: | :--------------: | :---------: | -------- |
| Customer | `CustomerDetail.tsx` | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ Done |
| Vendor | `VendorDetail.tsx` | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ Done |
| Employee | `EmployeeDetail.tsx` | ✅ | ✅ | ✅ | ✅ | ➖ | 📝 Uses OrgDetail |
| Contact | `ContactDetail.tsx` | ✅ | ✅ | ✅ | ✅ | ➖ | 📝 Sections (no tabs) |

> **Note:** EmployeeDetail uses the shared `OrgDetail` base component which has its own comprehensive tab system for admin editing. ContactDetail already has all panels integrated in a section-based layout.

---

### Transaction Models

| Model | File | Comments | Actions | Documents | Lines | Contacts | Status |
|-------|------|:--------:|:-------:|:---------:|:-----:|:--------:|--------|
| Order | `OrderDetail.tsx` | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ TransactionDetailBase |
| Invoice | `InvoiceDetail.tsx` | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ TransactionDetailBase |
| Proposal | `ProposalDetail.tsx` | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ TransactionDetailBase |
| Purchase | `PurchaseDetail.tsx` | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ TransactionDetailBase |
| Receipt | `ReceiptDetail.tsx` | ✅ | ✅ | ✅ | ➖ | ✅ | ✅ TransactionDetailBase |
| Requisition | `RequisitionDetail.tsx` | ✅ | ✅ | ✅ | ➖ | ⚡ | ✅ DetailTabs (rewritten) |
| Workorder | `WorkorderDetail.tsx` | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ TransactionDetailBase |
| Project | `ProjectDetail.tsx` | ✅ | ✅ | ✅ | ➖ | ⚡ | ✅ DetailTabs (rewritten) |

> **Note:** Order, Invoice, Proposal, Purchase, Receipt, and Workorder use `TransactionDetailBase` which provides a comprehensive tab system with contacts, comments, financials, documents, QA tabs. Project and Requisition were rewritten to use the `DetailTabs` component pattern.

---

### Transaction Line Models

| Model | File | Comments | Actions | Documents | Status |
|-------|------|:--------:|:-------:|:---------:|--------|
| OrderLine | `OrderLineDetail.tsx` | ➖ | ➖ | ➖ | ✅ Minimal inline form |
| InvoiceLine | `InvoiceLineDetail.tsx` | ➖ | ➖ | ➖ | ✅ Minimal inline form |
| ProposalLine | `ProposalLineDetail.tsx` | ➖ | ➖ | ➖ | ✅ Minimal inline form |
| PurchaseLine | `PurchaseLineDetail.tsx` | ➖ | ➖ | ➖ | ✅ Minimal inline form |
| WorkOrderLine | `WorkOrderLineDetail.tsx` | ➖ | ➖ | ➖ | ✅ Minimal inline form |

> **Note:** Line items are inline form editors used within the parent transaction. They don't need tab navigation or panels - comments, documents, and actions belong to the parent transaction.

---

### Product Models

| Model | File | Comments | Actions | Documents | Status |
|-------|------|:--------:|:-------:|:---------:|--------|
| Item | `ItemDetail.tsx` | ✅ | ✅ | ✅ | ✅ Accordion+Panels (1411 lines) |
| Service | `ServiceDetail.tsx` | ➖ | ➖ | ➖ | ✅ Simple inline form |
| Serial | `SerialDetail.tsx` | ➖ | ➖ | ➖ | ✅ Simple inline form |
| Catalog | `CatalogDetail.tsx` | ➖ | ➖ | ➖ | ✅ Simple inline form |
| Warehouse | `WarehouseDetail.tsx` | ➖ | ➖ | ➖ | ✅ Simple inline form |
| BillOfMaterial | `BillOfMaterialDetail.tsx` | ➖ | ➖ | ➖ | ✅ Simple inline form |
| Variant | `VariantDetail.tsx` | ➖ | ➖ | ➖ | ✅ Simple inline form |
| OrgItem | `OrgItemDetail.tsx` | ➖ | ➖ | ➖ | ✅ Simple inline form |
| ItemXref | `ItemXrefDetail.tsx` | ➖ | ➖ | ➖ | ✅ Simple inline form |
| Specification | `SpecificationDetail.tsx` | ➖ | ➖ | ➖ | ✅ Simple inline form |
| Matrics | `MatricsDetail.tsx` | ➖ | ➖ | ➖ | ✅ Simple inline form |
| Flow | `FlowDetail.tsx` | ➖ | ➖ | ➖ | ✅ Simple inline form |
| Usage | `UsageDetail.tsx` | ➖ | ➖ | ➖ | ✅ Simple inline form |

> **Note:** Only `ItemDetail.tsx` has full panel support. Supporting product entities are edited inline and link to parent Item for comments/actions/documents.

---

### Communication Models

| Model | File | Comments | Actions | Documents | Status |
|-------|------|:--------:|:-------:|:---------:|--------|
| Email | `EmailDetail.tsx` | ➖ | ➖ | ➖ | ✅ Simple inline form |
| Phone | `PhoneDetail.tsx` | ➖ | ➖ | ➖ | ✅ Simple inline form |
| Address | `AddressDetail.tsx` | ➖ | ➖ | ➖ | ✅ Simple inline form |
| Domain | `DomainDetail.tsx` | ➖ | ➖ | ➖ | ✅ Simple inline form |

> **Note:** Communication records are viewed/edited via `CommunicationsPanel` on parent entities.

---

### Account Models

| Model | File | Comments | Actions | Documents | Status |
|-------|------|:--------:|:-------:|:---------:|--------|
| GLAccount | `GLAccountDetail.tsx` | ➖ | ➖ | ➖ | ✅ Enterprise form layout |
| GLJournal | `GLJournalDetail.tsx` | ➖ | ➖ | ➖ | ✅ Simple inline form |
| Currency | `CurrencyDetail.tsx` | ➖ | ➖ | ➖ | ✅ Simple inline form |
| ExchangeRate | `ExchangeRateDetail.tsx` | ➖ | ➖ | ➖ | ✅ Simple inline form |
| ExchangeTransaction | `ExchangeTransactionDetail.tsx` | ➖ | ➖ | ➖ | ✅ Simple inline form |
| Audit | `AuditDetail.tsx` | ❌ | ❌ | ❌ | ✅ Read-only system log |

> **Note:** Account models are lookup tables - no comments/actions/documents needed.

---

### Core/System Models

| Model | File | Comments | Actions | Documents | Status |
|-------|------|:--------:|:-------:|:---------:|--------|
| Report | `ReportDetail.tsx` | ➖ | ➖ | ➖ | ✅ Simple inline form |
| APILog | `APILogDetail.tsx` | ❌ | ❌ | ❌ | ✅ Read-only system log |
| Setting | `SettingDetail.tsx` | ➖ | ➖ | ➖ | ✅ Admin config form |
| Action | `ActionDetail.tsx` | ➖ | ❌ | ➖ | ✅ Simple form |
| Template | `TemplateDetail.tsx` | ➖ | ➖ | ➖ | ✅ Code editor form |

> **Note:** Core/system models are admin-only configuration pages - no user-facing comments/actions/documents.

---

### Sync Models

| Model | File | Comments | Actions | Documents | Status |
|-------|------|:--------:|:-------:|:---------:|--------|
| Bundle | `BundleDetail.tsx` | ➖ | ➖ | ➖ | ✅ Data mapping form |
| Connection | `ConnectionDetail.tsx` | ➖ | ➖ | ➖ | ✅ API config form |

> **Note:** Sync models are integration configuration pages - technical admin tools.

---

### Support Models

| Model | File | Comments | Actions | Documents | Q&A | Status |
|-------|------|:--------:|:-------:|:---------:|:---:|--------|
| Campaign | `CampaignDetail.tsx` | ✅ | ✅ | ✅ | ✅ | ⬜ Future enhancement |

> **Note:** Campaign is a candidate for DetailTabs pattern in future iterations.

---

### Document Models

| Model | File | Comments | Actions | Documents | Status |
|-------|------|:--------:|:-------:|:---------:|--------|
| Document | `DocumentDetail.tsx` | ➖ | ➖ | ❌ | ✅ Document viewer |

> **Note:** Document model is the document itself - metadata viewer with file preview.

---

## Implementation Checklist

### Phase 1: High-Priority Models (User-Facing) ✅ COMPLETED

- [x] `CustomerDetail.tsx` - Complete tab navigation and all panels
- [x] `ContactDetail.tsx` - Already has panels in section layout (tabs optional)
- [x] `VendorDetail.tsx` - Complete tab navigation and all panels
- [x] `EmployeeDetail.tsx` - Uses OrgDetail base component

### Phase 2: Transaction Models ✅ COMPLETED

All transaction detail pages use `TransactionDetailBase` which provides comprehensive tabs:
- Contacts, Comments, Financials, Documents, QA tabs
- Custom tabs per transaction type (Actions, Shipping, Tax)
- Admin-only tabs: Metadata, Refs, Raw JSON

- [x] `OrderDetail.tsx` - Uses TransactionDetailBase with Actions/Shipping tabs
- [x] `InvoiceDetail.tsx` - Uses TransactionDetailBase with Shipping/Tax tabs
- [x] `ProposalDetail.tsx` - Uses TransactionDetailBase
- [x] `PurchaseDetail.tsx` - Uses TransactionDetailBase
- [x] `ReceiptDetail.tsx` - Uses TransactionDetailBase
- [x] `WorkorderDetail.tsx` - Uses TransactionDetailBase
- [x] `ProjectDetail.tsx` - **REWRITTEN** to use DetailTabs pattern
- [x] `RequisitionDetail.tsx` - **REWRITTEN** to use DetailTabs pattern

**Line Detail Pages (Minimal Forms):**
- [x] `OrderLineDetail.tsx` - Inline form, no tabs needed
- [x] `InvoiceLineDetail.tsx` - Inline form, no tabs needed
- [x] `ProposalLineDetail.tsx` - Inline form, no tabs needed
- [x] `PurchaseLineDetail.tsx` - Inline form, no tabs needed
- [x] `WorkOrderLineDetail.tsx` - Inline form, no tabs needed

### Phase 3: Product Models ✅ ASSESSED

- [x] `ItemDetail.tsx` (1411 lines) - **ALREADY STANDARDIZED** - Uses enterprise accordion layout with all panels:
  - CommentsPanel, ActionsPanel, MetadataPanel, RefsPanel, PrefsPanel, RawDataPanel, LinkagesPanel
  - Collapsible DataSections for organized content
  - ImagePanel, InventoryGrid, BOMSection
  - Admin-only panels for Metadata, Refs, RawData

**Simple Form Components (no tabs needed - inline editing):**
- [x] `ServiceDetail.tsx` - Simple inline form
- [x] `SerialDetail.tsx` - Simple inline form  
- [x] `CatalogDetail.tsx` - Simple inline form
- [x] `WarehouseDetail.tsx` - Simple inline form
- [x] `BillOfMaterialDetail.tsx` - Simple inline form
- [x] `VariantDetail.tsx` - Simple inline form
- [x] `OrgItemDetail.tsx` - Simple inline form
- [x] `ItemXrefDetail.tsx` - Simple inline form
- [x] `SpecificationDetail.tsx` - Simple inline form
- [x] `MatricsDetail.tsx` - Simple inline form
- [x] `FlowDetail.tsx` - Simple inline form
- [x] `UsageDetail.tsx` - Simple inline form

> **Note:** Product supporting entities are primarily used in List views with inline editing. They don't require full tab navigation - their comments/actions/documents (if any) should link to parent Item records.

### Phase 4: Supporting Models ✅ ASSESSED

**Account Models (simple lookup tables):**
- [x] `GLAccountDetail.tsx` - Enterprise form layout with column selector
- [x] `GLJournalDetail.tsx` - Simple inline form
- [x] `CurrencyDetail.tsx` - Simple inline form
- [x] `ExchangeRateDetail.tsx` - Simple inline form
- [x] `ExchangeTransactionDetail.tsx` - Simple inline form
- [x] `AuditDetail.tsx` - Read-only system log view

**Core Models (admin configuration):**
- [x] `ReportDetail.tsx` - Simple inline form
- [x] `TemplateDetail.tsx` - Simple inline form
- [x] `SettingDetail.tsx` - Simple inline form
- [x] `ActionDetail.tsx` - Simple inline form
- [x] `APILogDetail.tsx` - Read-only system log view

**Sync Models:**
- [x] `BundleDetail.tsx` - Simple inline form
- [x] `ConnectionDetail.tsx` - Simple inline form

**Communication Models (contact info):**
- [x] `EmailDetail.tsx` - Simple inline form
- [x] `PhoneDetail.tsx` - Simple inline form
- [x] `AddressDetail.tsx` - Simple inline form
- [x] `DomainDetail.tsx` - Simple inline form

> **Note:** Supporting models are configuration/lookup entities that don't have their own comments, actions, or documents. They're typically edited inline in List views or as part of a parent entity.

### Phase 5: Minimal Detail Pages ✅ COMPLETE

All minimal detail pages confirmed as simple inline forms - appropriate for their use case.

---

## Summary of Standardization

### Models with Full Tab/Panel Support:

| Category | Pattern | Examples |
|----------|---------|----------|
| **Org Entities** | DetailTabs | CustomerDisplay, VendorDetail |
| **Transactions** | TransactionDetailBase | OrderDetail, InvoiceDetail, etc. |
| **Rich Entities** | Rewritten with DetailTabs | ProjectDetail, RequisitionDetail |
| **Products** | Accordion + Panels | ItemDetail |

### Models as Simple Forms (No Tabs Needed):

| Category | Count | Rationale |
|----------|-------|-----------|
| Transaction Lines | 5 | Parent has comments/actions |
| Product Supporting | 12 | Link to Item records |
| Account/GL | 6 | Lookup tables |
| Core/Admin | 5 | System configuration |
| Sync | 2 | Integration config |
| Communication | 4 | Contact info fields |

### Future Considerations:

| Model | Reason | Priority |
|-------|--------|----------|
| CampaignDetail | Rich entity with Q&A | Low |
| DocumentDetail | Could use metadata tabs | Low |

---

## Standard Tab Navigation Component

### DetailTabs Component

A reusable tab navigation component has been created at `src/components/common/DetailTabs.tsx`:

```tsx
import { DetailTabs, useDetailTabs, useColumnCount } from '@/components/common/DetailTabs';

// Hook for managing tab state with localStorage persistence
const { activeTab, setActiveTab } = useDetailTabs('customer', 'overview');

// Hook for managing column count with localStorage persistence  
const { columnCount, setColumnCount } = useColumnCount('customer', 3);

// Component usage
<DetailTabs
  entityType="customer"
  activeTab={activeTab}
  onTabChange={setActiveTab}
  standardTabs={['overview', 'comments', 'actions', 'documents', 'history', 'raw']}
  additionalTabs={[
    { id: 'communication', label: 'Contact', icon: <FaPhone size={14} /> },
    { id: 'financial', label: 'Financial', icon: <FaDollarSign size={14} /> },
  ]}
  badges={{ comments: 5, actions: 2 }}
  showColumnSelector={true}
  columnCount={columnCount}
  onColumnCountChange={setColumnCount}
/>
```

### Features

- **Standard Tabs**: Overview, Comments, Actions, Documents, History (admin), Raw (admin)
- **Additional Tabs**: Model-specific tabs inserted before admin tabs
- **Badges**: Count badges on tabs (e.g., pending actions count)
- **Column Selector**: 2/3 column toggle for responsive layouts
- **LocalStorage Persistence**: Active tab and column count remembered per entity type
- **Role-Based Visibility**: Admin-only tabs hidden for non-admin users

### Example Usage

```tsx
import { useState } from 'react';
import { FaComments, FaTasks, FaFile, FaHistory, FaCode } from 'react-icons/fa';
import {
  CommentsPanel,
  ActionsPanel,
  DocumentsPanel,
  MetadataPanel,
  RawDataPanel,
} from '@/apps/common/components/panels';

// Tab configuration
const TABS = [
  { id: 'overview', label: 'Overview', icon: <FaInfoCircle /> },
  { id: 'comments', label: 'Comments', icon: <FaComments /> },
  { id: 'actions', label: 'Actions', icon: <FaTasks /> },
  { id: 'documents', label: 'Documents', icon: <FaFile /> },
  { id: 'history', label: 'History', icon: <FaHistory />, adminOnly: true },
  { id: 'raw', label: 'Raw', icon: <FaCode />, adminOnly: true },
];

// In component
const [activeTab, setActiveTab] = useState('overview');

// Tab content rendering
{activeTab === 'comments' && (
  <CommentsPanel
    entityType="customer"
    entityId={record.id}
    comments={record.comments}
    isEditing={isEditing}
    onChange={(comments) => setRecord({ ...record, comments })}
    currentUser={currentUser?.display_name}
  />
)}

{activeTab === 'actions' && (
  <ActionsPanel
    entityType="customer"
    entityId={record.id}
    data={record.actions?.items}
    actionIds={record.actions?.ids}
    isEditing={isEditing}
    onChange={(actions) => setRecord({ ...record, actions: { ...record.actions, items: actions } })}
  />
)}

{activeTab === 'documents' && (
  <DocumentsPanel
    parentType="customer"
    parentId={record.id}
    data={record.refs?.links?.document}
    isEditing={isEditing}
    onChange={(docs) => setRecord({
      ...record,
      refs: { ...record.refs, links: { ...record.refs?.links, document: docs } }
    })}
  />
)}
```

---

## File Locations

### All Detail Files (52 total)

| Category | Count | Path Pattern |
|----------|-------|--------------|
| Communications | 4 | `src/apps/communications/models/*/pages/*Detail.tsx` |
| Accounts | 6 | `src/apps/accounts/models/*/pages/*Detail.tsx` |
| Transactions | 10 | `src/apps/transactions/models/*/pages/*Detail.tsx` |
| Orgs | 3 | `src/apps/orgs/models/*/pages/*Detail.tsx` |
| Products | 13 | `src/apps/products/models/*/pages/*Detail.tsx` |
| Core | 5 | `src/apps/core/models/*/pages/*Detail.tsx` |
| Sync | 3 | `src/apps/sync/*/pages/*Detail.tsx` |
| Support | 1 | `src/apps/support/models/*/pages/*Detail.tsx` |
| Docs | 1 | `src/apps/docs/models/*/pages/*Detail.tsx` |

---

## References

- [UI Form Layout Research](ui-form-layout-research.md)
- [Panel Components README](../src/apps/common/components/panels/README.md)
- [CommentsPanel](../src/apps/common/components/panels/CommentsPanel.tsx)
- [ActionsPanel](../src/apps/common/components/panels/ActionsPanel.tsx)
- [DocumentsPanel](../src/apps/common/components/panels/DocumentsPanel.tsx)

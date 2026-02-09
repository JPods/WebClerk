# Detail Page Standardization Plan

This document outlines the plan to standardize all `*Detail.tsx` pages with consistent layout rules, tab navigation, and panel components.

---

## Completion Status by App

| App | Files | Status |
|-----|-------|--------|
| **orgs/** | 4 | ✅ Complete (CustomerDisplay, VendorDetail, ContactDetail, EmployeeDetail) |
| **transactions/** | 14 | ✅ Complete (6 use TransactionDetailBase, Project/Requisition rewritten, 5 lines are simple forms) |
| **products/** | 13 | ✅ Complete (ItemDetail has full panels, 12 use SimpleDetailHeader/Toolbar) |
| **accounts/** | 6 | ✅ Complete (4 use SimpleDetailHeader/Toolbar, GLAccount enterprise, Audit read-only) |
| **core/** | 6 | ✅ Complete (4 use SimpleDetailHeader/Toolbar, ContactDetail sections, APILog read-only) |
| **communications/** | 4 | ✅ Complete (All use SimpleDetailHeader/Toolbar) |
| **sync/** | 3 | ✅ Complete (2 use SimpleDetailHeader/Toolbar) |
| **docs/** | 1 | ✅ Complete (Uses SimpleDetailHeader/Toolbar) |
| **support/** | 1 | ✅ Complete (Uses SimpleDetailHeader/Toolbar) |

**Total: 52 Detail files standardized**

### Components Added

- **SimpleDetailHeader** - Entity name, ID, mode indicator, back navigation
- **SimpleDetailToolbar** - Edit/Save/Cancel/Delete actions with loading state
- **HorizontalField** - Label-left field layout with icon support
- **useColumnCount** - 2/3 column selector with localStorage persistence

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
| Service | `ServiceDetail.tsx` | ➖ | ➖ | ➖ | ✅ Simple form + Header/Toolbar |
| Serial | `SerialDetail.tsx` | ➖ | ➖ | ➖ | ✅ Simple form + Header/Toolbar |
| Catalog | `CatalogDetail.tsx` | ➖ | ➖ | ➖ | ✅ Simple form + Header/Toolbar |
| Warehouse | `WarehouseDetail.tsx` | ➖ | ➖ | ➖ | ✅ Simple form + Header/Toolbar |
| BillOfMaterial | `BillOfMaterialDetail.tsx` | ➖ | ➖ | ➖ | ✅ Simple form + Header/Toolbar |
| Variant | `VariantDetail.tsx` | ➖ | ➖ | ➖ | ✅ Simple form + Header/Toolbar |
| OrgItem | `OrgItemDetail.tsx` | ➖ | ➖ | ➖ | ✅ Simple form + Header/Toolbar |
| ItemXref | `ItemXrefDetail.tsx` | ➖ | ➖ | ➖ | ✅ Simple form + Header/Toolbar |
| Specification | `SpecificationDetail.tsx` | ➖ | ➖ | ➖ | ✅ Simple form + Header/Toolbar |
| Matrics | `MatricsDetail.tsx` | ➖ | ➖ | ➖ | ✅ Simple form + Header/Toolbar |
| Flow | `FlowDetail.tsx` | ➖ | ➖ | ➖ | ✅ Simple form + Header/Toolbar |
| Usage | `UsageDetail.tsx` | ➖ | ➖ | ➖ | ✅ Simple form + Header/Toolbar |

> **Note:** Only `ItemDetail.tsx` has full panel support. Supporting product entities use SimpleDetailHeader + SimpleDetailToolbar + HorizontalField layout.

---

### Communication Models

| Model | File | Comments | Actions | Documents | Status |
|-------|------|:--------:|:-------:|:---------:|--------|
| Email | `EmailDetail.tsx` | ➖ | ➖ | ➖ | ✅ Simple form + Header/Toolbar |
| Phone | `PhoneDetail.tsx` | ➖ | ➖ | ➖ | ✅ Simple form + Header/Toolbar |
| Address | `AddressDetail.tsx` | ➖ | ➖ | ➖ | ✅ Simple form + Header/Toolbar |
| Domain | `DomainDetail.tsx` | ➖ | ➖ | ➖ | ✅ Simple form + Header/Toolbar |

> **Note:** Communication records use SimpleDetailHeader + SimpleDetailToolbar. Typically viewed/edited via `CommunicationsPanel` on parent entities.

---

### Account Models

| Model | File | Comments | Actions | Documents | Status |
|-------|------|:--------:|:-------:|:---------:|--------|
| GLAccount | `GLAccountDetail.tsx` | ➖ | ➖ | ➖ | ✅ Enterprise form layout |
| GLJournal | `GLJournalDetail.tsx` | ➖ | ➖ | ➖ | ✅ Simple form + Header/Toolbar |
| Currency | `CurrencyDetail.tsx` | ➖ | ➖ | ➖ | ✅ Simple form + Header/Toolbar |
| ExchangeRate | `ExchangeRateDetail.tsx` | ➖ | ➖ | ➖ | ✅ Simple form + Header/Toolbar |
| ExchangeTransaction | `ExchangeTransactionDetail.tsx` | ➖ | ➖ | ➖ | ✅ Simple form + Header/Toolbar |
| Audit | `AuditDetail.tsx` | ❌ | ❌ | ❌ | ✅ Read-only system log |

> **Note:** Account models are lookup tables. Simple forms now use SimpleDetailHeader + SimpleDetailToolbar.

---

### Core/System Models

| Model | File | Comments | Actions | Documents | Status |
|-------|------|:--------:|:-------:|:---------:|--------|
| Report | `ReportDetail.tsx` | ➖ | ➖ | ➖ | ✅ Simple form + Header/Toolbar |
| APILog | `APILogDetail.tsx` | ❌ | ❌ | ❌ | ✅ Read-only system log |
| Setting | `SettingDetail.tsx` | ➖ | ➖ | ➖ | ✅ Simple form + Header/Toolbar |
| Action | `ActionDetail.tsx` | ➖ | ❌ | ➖ | ✅ Simple form + Header/Toolbar |
| Template | `TemplateDetail.tsx` | ➖ | ➖ | ➖ | ✅ Simple form + Header/Toolbar |

> **Note:** Core/system models are admin-only. Simple forms now use SimpleDetailHeader + SimpleDetailToolbar.

---

### Sync Models

| Model | File | Comments | Actions | Documents | Status |
|-------|------|:--------:|:-------:|:---------:|--------|
| Bundle | `BundleDetail.tsx` | ➖ | ➖ | ➖ | ✅ Simple form + Header/Toolbar |
| Connection | `ConnectionDetail.tsx` | ➖ | ➖ | ➖ | ✅ Simple form + Header/Toolbar |

> **Note:** Sync models are integration configuration pages. Now use SimpleDetailHeader + SimpleDetailToolbar.

---

### Support Models

| Model | File | Comments | Actions | Documents | Q&A | Status |
|-------|------|:--------:|:-------:|:---------:|:---:|--------|
| Campaign | `CampaignDetail.tsx` | ✅ | ✅ | ✅ | ✅ | ✅ Simple form + Header/Toolbar |

> **Note:** Campaign now uses SimpleDetailHeader + SimpleDetailToolbar. Full DetailTabs pattern is a future enhancement.

---

### Document Models

| Model | File | Comments | Actions | Documents | Status |
|-------|------|:--------:|:-------:|:---------:|--------|
| Document | `DocumentDetail.tsx` | ➖ | ➖ | ❌ | ✅ Simple form + Header/Toolbar |

> **Note:** Document model is the document itself. Now uses SimpleDetailHeader + SimpleDetailToolbar for metadata editing.

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

### Phase 3: Product Models ✅ COMPLETE

- [x] `ItemDetail.tsx` (1411 lines) - **ALREADY STANDARDIZED** - Uses enterprise accordion layout with all panels:
  - CommentsPanel, ActionsPanel, MetadataPanel, RefsPanel, PrefsPanel, RawDataPanel, LinkagesPanel
  - Collapsible DataSections for organized content
  - ImagePanel, InventoryGrid, BOMSection
  - Admin-only panels for Metadata, Refs, RawData

**Simple Form Components (Header/Toolbar added):**
- [x] `ServiceDetail.tsx` - SimpleDetailHeader + SimpleDetailToolbar
- [x] `SerialDetail.tsx` - SimpleDetailHeader + SimpleDetailToolbar
- [x] `CatalogDetail.tsx` - SimpleDetailHeader + SimpleDetailToolbar
- [x] `WarehouseDetail.tsx` - SimpleDetailHeader + SimpleDetailToolbar
- [x] `BillOfMaterialDetail.tsx` - SimpleDetailHeader + SimpleDetailToolbar
- [x] `VariantDetail.tsx` - SimpleDetailHeader + SimpleDetailToolbar
- [x] `OrgItemDetail.tsx` - SimpleDetailHeader + SimpleDetailToolbar
- [x] `ItemXrefDetail.tsx` - SimpleDetailHeader + SimpleDetailToolbar
- [x] `SpecificationDetail.tsx` - SimpleDetailHeader + SimpleDetailToolbar
- [x] `MatricsDetail.tsx` - SimpleDetailHeader + SimpleDetailToolbar
- [x] `FlowDetail.tsx` - SimpleDetailHeader + SimpleDetailToolbar
- [x] `UsageDetail.tsx` - SimpleDetailHeader + SimpleDetailToolbar

> **Note:** Product supporting entities now use the standard layout pattern with SimpleDetailHeader/Toolbar. Their comments/actions/documents (if any) should link to parent Item records.

### Phase 4: Supporting Models ✅ COMPLETE

**Account Models (lookup tables + Header/Toolbar):**
- [x] `GLAccountDetail.tsx` - Enterprise form layout with column selector
- [x] `GLJournalDetail.tsx` - SimpleDetailHeader + SimpleDetailToolbar
- [x] `CurrencyDetail.tsx` - SimpleDetailHeader + SimpleDetailToolbar
- [x] `ExchangeRateDetail.tsx` - SimpleDetailHeader + SimpleDetailToolbar
- [x] `ExchangeTransactionDetail.tsx` - SimpleDetailHeader + SimpleDetailToolbar
- [x] `AuditDetail.tsx` - Read-only system log view

**Core Models (admin configuration + Header/Toolbar):**
- [x] `ReportDetail.tsx` - SimpleDetailHeader + SimpleDetailToolbar
- [x] `TemplateDetail.tsx` - SimpleDetailHeader + SimpleDetailToolbar
- [x] `SettingDetail.tsx` - SimpleDetailHeader + SimpleDetailToolbar
- [x] `ActionDetail.tsx` - SimpleDetailHeader + SimpleDetailToolbar
- [x] `APILogDetail.tsx` - Read-only system log view

**Sync Models + Header/Toolbar:**
- [x] `BundleDetail.tsx` - SimpleDetailHeader + SimpleDetailToolbar
- [x] `ConnectionDetail.tsx` - SimpleDetailHeader + SimpleDetailToolbar

**Communication Models + Header/Toolbar:**
- [x] `EmailDetail.tsx` - SimpleDetailHeader + SimpleDetailToolbar
- [x] `PhoneDetail.tsx` - SimpleDetailHeader + SimpleDetailToolbar
- [x] `AddressDetail.tsx` - SimpleDetailHeader + SimpleDetailToolbar
- [x] `DomainDetail.tsx` - SimpleDetailHeader + SimpleDetailToolbar

**Support/Docs Models + Header/Toolbar:**
- [x] `CampaignDetail.tsx` - SimpleDetailHeader + SimpleDetailToolbar
- [x] `DocumentDetail.tsx` - SimpleDetailHeader + SimpleDetailToolbar

> **Note:** All simple forms now use the standard layout: SimpleDetailHeader → SimpleDetailToolbar → ComponentCard with HorizontalField grid.

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

## Simple Form Components

For simple forms (lookup tables, configuration forms), two lightweight components provide consistent header and toolbar functionality:

### SimpleDetailHeader

Location: `src/components/common/SimpleDetailHeader.tsx`

Displays entity name, record ID, record name, and mode indicator (Add/Edit/View) with back navigation.

```tsx
<SimpleDetailHeader
  entityName="Currency"
  recordId={data?.id}
  recordName={data?.name}
  mode={currentMode}
  backUrl="/accounts/currencies"
/>
```

### SimpleDetailToolbar

Location: `src/components/common/SimpleDetailToolbar.tsx`

Provides Edit/Save/Cancel/Delete buttons with proper state management.

```tsx
<SimpleDetailToolbar
  mode={currentMode}
  isSaving={isSaving}
  onSave={handleSubmit(onSubmit)}
  onCancel={handleCancel}
  onEdit={handleEdit}
  canDelete={true}
  onDelete={handleDelete}
/>
```

### Simple Form Layout Pattern

All simple forms now follow this structure:

```
┌────────────────────────────────────────┐
│  PageBreadcrumb                        │
├────────────────────────────────────────┤
│  SimpleDetailHeader                    │  ← Entity name, ID, mode
├────────────────────────────────────────┤
│  SimpleDetailToolbar                   │  ← Edit/Save/Cancel/Delete
├────────────────────────────────────────┤
│  ComponentCard                         │
│    ColumnSelector (top-right)          │
│    HorizontalField grid (2-3 cols)     │
└────────────────────────────────────────┘
```

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

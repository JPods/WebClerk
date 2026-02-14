# Shared Components & Panels

Reusable components for displaying and editing common data structures across all model detail pages. These panels align with the Django `BaseModel` JSONB field structure (`.metadata`, `.refs`, `.prefs`, `.comments`, `.actions`).

> **Last updated:** 2025-02-13

---

## Directory Structure

```
src/apps/common/components/
├── JsonFieldEditor.tsx           # Generic JSON editor (admin power users)
├── TransactionToolbar.tsx        # Action toolbar (save, clone, transfer, print)
│
└── panels/
    ├── README.md                 # This documentation
    ├── index.ts                  # Barrel exports
    ├── types.ts                  # Shared types (aligned with Django models)
    ├── usePermissions.ts         # Permission checking hook
    ├── documentUpload.ts         # Upload utilities (multi-file, geo, virus scan)
    ├── qaUtils.ts                # Q&A question groups, counters, image upload
    │
    │── # Standard Tab Panels (shown as tabs on detail pages)
    ├── ActionsPanel.tsx          # Tasks/actions with status tracking
    ├── CommentsPanel.tsx         # Comments with Public/Process/Partner/History
    ├── ContactPanel.tsx          # Contacts grouped by purpose with editing
    ├── DocumentsPanel.tsx        # File uploads, preview, download
    ├── FinancialsPanel.tsx       # Org financial summary (credit, aging, AR/AP)
    ├── TransactionFinancialsPanel.tsx  # Transaction financials (subtotal, tax, total)
    ├── QAPanel.tsx               # Q&A with question/answer workflow
    ├── LinkagesPanel.tsx         # Cross-table record flow (proposal→order→invoice)
    ├── ShippingPanel.tsx         # Shipping details (carrier, tracking, weight)
    ├── BasicInformationPanel.tsx # Common org scalar fields (name, email, phone)
    ├── CommunicationsPanel.tsx   # Email/phone/address/domain CRUD (direct API)
    ├── ContactPanel.tsx          # Contacts grouped by purpose with editing (canonical)
    │
    │── # Admin / Developer Panels
    ├── MetadataPanel.tsx         # Admin-only key-value metadata editor
    ├── RefsPanel.tsx             # Admin-only relationships & lineage viewer
    ├── PrefsPanel.tsx            # User/entity preferences (display/notifications)
    ├── RawDataPanel.tsx          # Admin-only raw JSON viewer with syntax highlight
    ├── TemplateQAPanel.tsx       # Template-based Q&A (not yet integrated)
    └── ModelDataPanel.tsx        # Generic model data display (not yet integrated)
```

Also in `transactions/components/` (transaction-specific, not shared):

```
src/apps/transactions/components/
├── TransactionDetailBase.tsx     # Base shell for all transaction detail pages
├── SummaryCard.tsx               # Transaction header (customer, totals, dates)
├── LinesCard.tsx                 # Line items grid with inline editing
├── LineDetailsModal.tsx          # Side-drawer for single line item editing
├── ContactLinksTable.tsx         # Spreadsheet-style contact table (drag columns)
├── QATab.tsx                     # Wraps QAPanel + question group selection
├── MetadataPanel.tsx             # Transaction-specific metadata (history, health)
├── PartySelector.tsx             # Customer/Vendor/Manufacturer search dropdown
├── TransactionItemSearch.tsx     # Item search for adding to transactions
├── CustomerSalesPanel.tsx        # Customer search + financial data + terms
├── ActionsModal.tsx              # Task creation modal (legacy → TransactionTaskModal)
├── TransactionTaskModal.tsx      # Task creation/edit slide-out panel
├── TransactionTaskModal.types.ts # Task type definitions
├── useTransactionTasks.ts        # Hook for task CRUD operations
├── AddPaymentModal.tsx           # Record payment against order
├── ApplyPaymentModal.tsx         # Apply existing payment to invoice
├── SplitLineModal.tsx            # Split line quantity across allocations
├── FieldLabel.tsx                # Label styling (mandatory/locked states)
├── ActivityLogTab.tsx            # Timeline view (pending integration)
├── QuickAddRecent.tsx            # Recent items for quick re-adding (pending)
├── PrintPreviewModal.tsx         # Print preview with options (pending)
├── print/                        # Print document templates per transaction type
│
│── # Re-export stubs (canonical source is common/)
├── CommentsPanel.tsx             # → common/panels/CommentsPanel
├── FinancialsCard.tsx            # → common/panels/TransactionFinancialsPanel
├── JsonFieldEditor.tsx           # → common/components/JsonFieldEditor
├── TransactionToolbar.tsx        # → common/components/TransactionToolbar
└── ContactPanel.tsx              # → common/panels/ContactPanel
```

---

## Panel Inventory

### Standard Tab Panels

These should appear as tabs on every model that supports them:

| Panel | Component | Data Source | Purpose |
|-------|-----------|-------------|---------|
| Action | `ActionsPanel` | `.actions` | Tasks with status, priority, assignees, due dates |
| Contact | `ContactPanel` | `.refs.links.contact` | Linked contacts grouped by purpose |
| Comments | `CommentsPanel` | `.comments` | Public/Process/Partner/History comment tabs |
| Documents | `DocumentsPanel` | `.refs.links.document` | File uploads, preview, download, delete |
| Financials | `FinancialsPanel` | `.financial` | Org financials (credit, aging, payment history) |
| Financials | `TransactionFinancialsPanel` | `.financials` | Transaction totals (subtotal, tax, shipping, total) |
| QA | `QAPanel` / `QATab` | Q&A API | Question/answer workflow with templates |
| Linkage | `LinkagesPanel` | Linkage API | Cross-table record flow tracking |
| Shipping | `ShippingPanel` | `.shipping` | Carrier, tracking, weight, FOB |
| Basic Info | `BasicInformationPanel` | Org scalars | Name, email, phone, company, title |
| Communications | `CommunicationsPanel` | `.refs.links.{email,phone,location,domain}` | Email/phone/address/domain CRUD |

### Contact Sub-Panels (accessed via CommunicationsPanel)

These are managed through `CommunicationsPanel` with direct API persistence:

| Record Type | API Model | refs.links key | Fields |
|-------------|-----------|----------------|--------|
| Email | `email` | `.refs.links.email` | address, name, type, is_primary |
| Phone | `phone` | `.refs.links.phone` | number, format, name, type |
| Address | `address` | `.refs.links.location` | address1/2, city, state, zip, country |
| Domain | `domain` | `.refs.links.domain` | domain, name, type, is_primary |

### Admin / Developer Panels

| Panel | Component | Data Source | Access | Purpose |
|-------|-----------|-------------|--------|---------|
| JSON Editor | `JsonFieldEditor` | Any JSONB field | admin | Inline JSON edit with validation |
| Metadata | `MetadataPanel` | `.metadata` | admin | Key-value editor (security, version, health) |
| Refs | `RefsPanel` | `.refs` | admin | Relationships, lineage, system links |
| Prefs | `PrefsPanel` | `.prefs` | admin | User/entity preferences |
| Raw Data | `RawDataPanel` | Full entity | admin | Raw JSON viewer with syntax highlight |

---

## Model × Panel Integration Matrix

### Legend

| Symbol | Meaning |
|--------|---------|
| ✅ | Integrated — panel is imported and wired |
| 🔲 | Planned — should have this panel but not yet integrated |
| ➖ | N/A — panel does not apply to this model |
| 🔄 | Via base — provided by TransactionDetailBase or OrgDetail |

### Transactions (via TransactionDetailBase)

All transaction models use `TransactionDetailBase` which provides: Actions, Contact (ContactPanel + ContactLinksTable), Comments, Documents, Financials (TransactionFinancialsPanel), QA (QATab), Metadata, JsonFieldEditor, TransactionToolbar.

| Model | Actions | Contact | Comments | Docs | Financials | QA | Linkage | Shipping | Lines |
|-------|---------|---------|----------|------|------------|-----|---------|----------|-------|
| order | 🔄 | 🔄 | 🔄 | 🔄 | 🔄 | 🔄 | 🔲 | ✅ | ✅ |
| invoice | 🔄 | 🔄 | 🔄 | 🔄 | 🔄 | 🔄 | 🔲 | 🔲 | ✅ |
| proposal | 🔄 | 🔄 | 🔄 | 🔄 | 🔄 | 🔄 | 🔲 | 🔲 | ✅ |
| purchase | 🔄 | 🔄 | 🔄 | 🔄 | 🔄 | 🔄 | 🔲 | 🔲 | ✅ |
| workorder | 🔄 | 🔄 | 🔄 | 🔄 | 🔄 | 🔄 | 🔲 | 🔲 | ✅ |
| receipt | 🔄 | 🔄 | 🔄 | 🔄 | 🔄 | 🔄 | 🔲 | 🔲 | 🔲 |
| requisition | 🔄 | 🔄 | 🔄 | 🔄 | 🔄 | 🔄 | 🔲 | 🔲 | 🔲 |
| project | 🔄 | 🔄 | 🔄 | 🔄 | 🔄 | 🔄 | 🔲 | ➖ | ➖ |

### Orgs

| Model | Actions | Contact | Comments | Docs | Financials | QA | Linkage | Comms | Basic Info | Metadata | Refs | Prefs | Raw |
|-------|---------|---------|----------|------|------------|-----|---------|-------|------------|----------|------|-------|-----|
| customer | ✅ | ✅ | ✅ | ✅ | ✅ | 🔲 | 🔲 | 🔲 | ✅ | ✅ | 🔲 | 🔲 | ✅ |
| vendor | 🔲 | ✅ | ✅ | ✅ | 🔲 | 🔲 | 🔲 | 🔲 | 🔲 | 🔲 | 🔲 | 🔲 | 🔲 |
| manufacturer | 🔲 | 🔲 | 🔲 | 🔲 | 🔲 | 🔲 | 🔲 | 🔲 | 🔲 | 🔲 | 🔲 | 🔲 | 🔲 |
| organization | 🔲 | 🔲 | 🔲 | 🔲 | 🔲 | 🔲 | 🔲 | 🔲 | 🔲 | 🔲 | 🔲 | 🔲 | 🔲 |
| employee | 🔲 | 🔲 | 🔲 | 🔲 | 🔄 | 🔲 | 🔲 | 🔲 | 🔄 | 🔲 | 🔲 | 🔲 | 🔲 |
| rep | 🔲 | 🔲 | 🔲 | 🔲 | 🔲 | 🔲 | 🔲 | 🔲 | 🔲 | 🔲 | 🔲 | 🔲 | 🔲 |

### Core

| Model | Actions | Contact | Comments | Docs | QA | Linkage | Comms | Metadata | Refs | Prefs | Raw |
|-------|---------|---------|----------|------|----|---------|-------|----------|------|-------|-----|
| contact | ✅ | ➖ | ✅ | 🔲 | 🔲 | 🔲 | ✅ | ✅ | ✅ | ✅ | ✅ |
| action | ➖ | ✅ | ✅ | ✅ | ✅ | 🔲 | 🔲 | 🔲 | 🔲 | 🔲 | 🔲 |
| report | 🔲 | 🔲 | 🔲 | 🔲 | 🔲 | 🔲 | 🔲 | 🔲 | 🔲 | 🔲 | 🔲 |
| setting | 🔲 | ➖ | 🔲 | ➖ | ➖ | ➖ | ➖ | 🔲 | 🔲 | 🔲 | 🔲 |
| template | 🔲 | ➖ | 🔲 | 🔲 | 🔲 | ➖ | ➖ | 🔲 | 🔲 | 🔲 | 🔲 |

### Products

| Model | Actions | Contact | Comments | Docs | QA | Linkage | JsonEditor | Refs | Metadata | Prefs | Raw |
|-------|---------|---------|----------|------|----|---------|------------|------|----------|-------|-----|
| item | ✅ | 🔲 | ✅ | 🔲 | 🔲 | ✅ | 🔲 | ✅ | ✅ | ✅ | ✅ |
| catalog | ✅ | 🔲 | ✅ | ✅ | 🔲 | 🔲 | ✅ | ✅ | 🔲 | 🔲 | 🔲 |
| variant | ✅ | 🔲 | ✅ | ✅ | 🔲 | 🔲 | ✅ | ✅ | 🔲 | 🔲 | 🔲 |
| serial | ✅ | 🔲 | ✅ | ✅ | 🔲 | 🔲 | ✅ | ✅ | 🔲 | 🔲 | 🔲 |
| specification | ✅ | 🔲 | ✅ | ✅ | 🔲 | 🔲 | ✅ | ✅ | 🔲 | 🔲 | 🔲 |
| warehouse | ✅ | 🔲 | ✅ | ✅ | 🔲 | 🔲 | ✅ | ✅ | 🔲 | 🔲 | 🔲 |
| service | ✅ | 🔲 | ✅ | ✅ | 🔲 | 🔲 | ✅ | ✅ | 🔲 | 🔲 | 🔲 |
| flow | ✅ | 🔲 | ✅ | ✅ | 🔲 | 🔲 | ✅ | ✅ | 🔲 | 🔲 | 🔲 |
| usage | ✅ | 🔲 | ✅ | ✅ | 🔲 | 🔲 | ✅ | ✅ | 🔲 | 🔲 | 🔲 |
| metrics | ✅ | 🔲 | ✅ | ✅ | 🔲 | 🔲 | ✅ | ✅ | 🔲 | 🔲 | 🔲 |
| org_item | ✅ | 🔲 | ✅ | ✅ | 🔲 | 🔲 | ✅ | ✅ | 🔲 | 🔲 | 🔲 |
| item_xref | ✅ | 🔲 | ✅ | ✅ | 🔲 | 🔲 | ✅ | ✅ | 🔲 | 🔲 | 🔲 |
| bill_of_material | ✅ | 🔲 | ✅ | ✅ | 🔲 | 🔲 | ✅ | 🔲 | 🔲 | 🔲 | 🔲 |

### Accounts

| Model | Actions | Comments | Docs | QA | Financials | JsonEditor | Refs | Metadata | Prefs | Raw |
|-------|---------|----------|------|----|------------|------------|------|----------|-------|-----|
| currency | ✅ | ✅ | 🔲 | 🔲 | ➖ | 🔲 | 🔲 | 🔲 | 🔲 | 🔲 |
| exchange_rate | ✅ | ✅ | 🔲 | 🔲 | ➖ | 🔲 | 🔲 | 🔲 | 🔲 | 🔲 |
| exchange_transaction | ✅ | ✅ | 🔲 | 🔲 | 🔲 | 🔲 | 🔲 | 🔲 | 🔲 | 🔲 |
| gl_account | ✅ | ✅ | 🔲 | 🔲 | ➖ | 🔲 | 🔲 | 🔲 | 🔲 | 🔲 |
| gl_journal | ✅ | ✅ | 🔲 | 🔲 | 🔲 | 🔲 | 🔲 | 🔲 | 🔲 | 🔲 |
| ledger | 🔲 | 🔲 | 🔲 | 🔲 | ➖ | 🔲 | 🔲 | 🔲 | 🔲 | 🔲 |
| tax_jurisdiction | 🔲 | 🔲 | 🔲 | 🔲 | ➖ | 🔲 | 🔲 | 🔲 | 🔲 | 🔲 |
| term | 🔲 | 🔲 | 🔲 | 🔲 | ➖ | 🔲 | 🔲 | 🔲 | 🔲 | 🔲 |
| audit | 🔲 | 🔲 | 🔲 | 🔲 | ➖ | 🔲 | 🔲 | 🔲 | 🔲 | 🔲 |

### Docs

| Model | Actions | Comments | Docs | QA | JsonEditor | Refs | Metadata | Prefs | Raw |
|-------|---------|----------|------|----|------------|------|----------|-------|-----|
| document | ✅ | ✅ | ✅ | 🔲 | ✅ | ✅ | 🔲 | 🔲 | 🔲 |
| linkage_entry | ✅ | ✅ | ✅ | 🔲 | ✅ | ✅ | 🔲 | 🔲 | 🔲 |
| question_answer | ✅ | ✅ | ✅ | 🔲 | ✅ | ✅ | 🔲 | 🔲 | 🔲 |
| tag | ✅ | ✅ | ✅ | 🔲 | ✅ | ✅ | 🔲 | 🔲 | 🔲 |

### Communications

| Model | Actions | Contact | Comments | Docs |
|-------|---------|---------|----------|------|
| email | ✅ | ✅ | ✅ | ✅ |
| phone | ✅ | ✅ | ✅ | ✅ |
| address | ✅ | ✅ | ✅ | ✅ |
| domain | ✅ | ✅ | ✅ | ✅ |

### Support / Sync

| Model | Actions | Comments | Docs | QA | JsonEditor | Refs |
|-------|---------|----------|------|----|------------|------|
| campaign | 🔲 | 🔲 | 🔲 | 🔲 | 🔲 | 🔲 |
| bundle | 🔲 | 🔲 | 🔲 | 🔲 | 🔲 | 🔲 |
| connection | 🔲 | 🔲 | 🔲 | 🔲 | 🔲 | 🔲 |

---

## Standard Tab Navigation

Every model detail page should aim for a consistent tab set.

### Universal Tabs (all models)

| Tab | Panel Component | Required |
|-----|-----------------|----------|
| Actions | `ActionsPanel` | Yes |
| Contact | `ContactPanel` | Yes (except settings, templates) |
| Comments | `CommentsPanel` | Yes |
| Documents | `DocumentsPanel` | Yes |
| Financials | `FinancialsPanel` or `TransactionFinancialsPanel` | Context-dependent |
| QA | `QAPanel` or `QATab` (transactions) | Yes |
| Linkage | `LinkagesPanel` | Yes (where cross-record flow exists) |

### Contextual Tabs (model-specific)

| Tab | Models | Panel Component |
|-----|--------|-----------------|
| Ledger | order, invoice, purchase, gl_journal | *(planned)* |
| Invoice Lines | invoice | `LinesCard` |
| Order Lines | order | `LinesCard` |
| Proposal Lines | proposal | `LinesCard` |
| Purchase Lines | purchase | `LinesCard` |
| Workorder Lines | workorder | `LinesCard` |
| Shipping | order, invoice, purchase | `ShippingPanel` |
| Reports | *(all)* | *(planned)* |
| Settings | *(admin)* | *(planned)* |

### Related Entity Tabs

These tabs navigate to filtered list views of related records:

| Tab | Applies To | Shows |
|-----|------------|-------|
| Employee | org models | Employees linked to org |
| Customer | contact, org | Customer records for contact/org |
| Vendor | contact, org | Vendor records for contact/org |
| Manufacturer | contact, org | Manufacturer records for contact/org |
| Rep | contact, org | Rep records for contact/org |
| Catalog | item, variant | Catalog entries for item |
| Inventory Layer | item, warehouse | Inventory layers |
| Inventory Reservation | item, warehouse | Reserved quantities |
| Item | catalog, org_item, variant | Item records |
| Metrics | item | Usage/performance metrics |
| Serial | item | Serial number records |
| Specification | item | Specifications |
| Usage | item | Usage tracking |
| Variant | item | Variant records |
| Warehouse | item | Warehouse locations |
| Campaign | contact, org | Campaigns |
| Bundle | sync | Sync bundles |

### Admin Tabs (role-restricted)

| Tab | Panel Component | Visible To |
|-----|-----------------|------------|
| JSON Editor | `JsonFieldEditor` | admin |
| Metadata | `MetadataPanel` | admin |
| Refs & Links | `RefsPanel` | admin |
| Prefs | `PrefsPanel` | admin |
| Raw Data | `RawDataPanel` | admin |

---

## Role-Based Access Control

All panels support role-based visibility and edit permissions via the `usePermissions` hook:

```typescript
interface PanelPermissions {
  viewRoles: UserRole[];
  editRoles: UserRole[];
}

type UserRole = 'admin' | 'superadmin' | 'super_admin' | 'administrator'
              | 'manager' | 'user' | 'viewer' | 'guest';

const ADMIN_ROLES = ['admin', 'superadmin', 'super_admin', 'administrator'];
const MANAGER_ROLES = [...ADMIN_ROLES, 'manager'];
const USER_ROLES = [...MANAGER_ROLES, 'user'];
const ALL_ROLES = [...USER_ROLES, 'viewer', 'guest'];
```

### Default Permissions

| Panel | View | Edit | Theme |
|-------|------|------|-------|
| BasicInformationPanel | all | user+ | Slate |
| CommentsPanel | all | user+ | Blue |
| ActionsPanel | all | user+ | Emerald |
| DocumentsPanel | all | user+ | Slate |
| QAPanel | all | user+ | Indigo |
| ContactPanel | all | user+ | Blue |
| CommunicationsPanel | all | user+ | Teal |
| LinkagesPanel | all | admin | Violet |
| FinancialsPanel | manager+ | admin | Green |
| ShippingPanel | all | user+ | Slate |
| MetadataPanel | admin | admin | Amber |
| RefsPanel | admin | admin | Cyan |
| PrefsPanel | user+ | admin | Purple |
| RawDataPanel | admin | admin | Gray |

---

## Common Props Interface

All panels extend from `BasePanelProps`:

```typescript
interface BasePanelProps<T = unknown> {
  entityType: EntityType;
  entityId: number;
  data: T;
  onChange?: (data: T) => void;
  readOnly?: boolean;
  viewRoles?: UserRole[];
  editRoles?: UserRole[];
  className?: string;
  compact?: boolean;
  title?: string;
  defaultCollapsed?: boolean;
}
```

---

## Django Model Alignment

These panels align with the Django `BaseModel` (from `common/models.py`) JSONB fields:

### `.metadata` → MetadataPanel

```typescript
interface EntityMetadata {
  security?: string;
  publish?: string;
  priority?: string;
  version?: string;
  access?: { view: number[]; edit: number[] };
  history?: {
    created: { dt: number; contact_id: number };
    modified: { dt: number; contact_id: number };
    accessed: { dt: number; contact_id: number };
    verified: { dt: number; contact_id: number };
    synced: { dt: number; contact_id: number };
  };
  health?: {
    rating: number; completeness: number; accuracy: number;
    freshness: number; consistency: number;
  };
  flags?: Record<string, boolean>;
  [key: string]: unknown;
}
```

### `.refs` → RefsPanel, ContactPanel, CommunicationsPanel, DocumentsPanel

```typescript
interface EntityRefs {
  keywords?: string[];
  tags?: string[];
  categories?: string[];
  related_ids?: number[];
  depends_on?: Record<string, number[]>;
  links?: {
    contact?: ContactLink[];
    email?: EmailLink[];
    phone?: PhoneLink[];
    location?: AddressLink[];
    document?: DocumentLink[];
    domain?: DomainLink[];
    item?: ItemLink[];
    [key: string]: RefLink[] | undefined;
  };
  lineage?: {
    parent_id?: number; parent_type?: string;
    source_id?: number; source_type?: string;
  };
}
```

### `.prefs` → PrefsPanel

```typescript
interface EntityPrefs {
  userdefined?: Record<string, unknown>;
  display?: {
    layout?: 'grid' | 'list' | 'card' | 'table';
    columns?: string[];
    sort?: { field: string; order: 'asc' | 'desc' };
  };
  notifications?: {
    email?: boolean; sms?: boolean; push?: boolean;
    frequency?: 'immediate' | 'daily' | 'weekly';
  };
  defaults?: Record<string, unknown>;
}
```

### `.comments` → CommentsPanel

```typescript
interface EntityComments {
  public?: string | CommentEntry[];
  process?: string | CommentEntry[];
  partner?: string | CommentEntry[];
  notes?: CommentEntry[];
  general?: Record<string, CommentEntry[]>;
}

interface CommentEntry {
  ts: string; by: string | number; text: string; source?: string;
}
```

### `.actions` → ActionsPanel

```typescript
interface ActionEntry {
  required?: boolean;
  status?: 'pending' | 'in_progress' | 'completed' | 'cancelled' | 'on_hold';
  who?: number | string;
  when?: number | string;
  what?: string;
  kind?: 'task' | 'followup' | 'call' | 'email' | 'review' | 'approve' | 'ship' | 'other';
  priority?: 'low' | 'normal' | 'high' | 'urgent';
  extra?: object;
}
```

---

## CommunicationsPanel - Direct API Integration

Unlike other panels that rely on parent `onChange` handlers, `CommunicationsPanel` makes its own API calls via `wcapi`:

```
User adds/edits/deletes email, phone, address, or domain
  → wcapi.saveRecord('email', { contact_id, email, name... })
  → On 200: Update local state with refs.links format
```

**Required prop:** `contactId` — all CRUD operations include this for linking.

---

## TransactionDetailBase - Internal Panel Inventory

`TransactionDetailBase` is the shell for all transaction detail pages. It internally imports and provides:

| Panel | Source |
|-------|--------|
| TransactionToolbar | `common/components/TransactionToolbar` (via re-export) |
| ContactPanel | `common/panels/ContactPanel` (via re-export) |
| ContactLinksTable | `transactions/components/ContactLinksTable` |
| CommentsPanel | `common/panels/CommentsPanel` (via re-export) |
| MetadataPanel | `transactions/components/MetadataPanel` (transaction-specific) |
| FinancialsCard | `common/panels/TransactionFinancialsPanel` (via re-export) |
| DocumentsPanel | `common/panels/DocumentsPanel` |
| JsonFieldEditor | `common/components/JsonFieldEditor` (via re-export) |
| QATab | `transactions/components/QATab` (wraps `common/panels/QAPanel`) |

Transaction detail pages extend this base and add model-specific components (SummaryCard, LinesCard, ShippingPanel, etc.).

---

## Quick Import Reference

```tsx
// Standard panels
import {
  ActionsPanel,
  CommentsPanel,
  DocumentsPanel,
  QAPanel,
  ContactPanel,
  RefsLinksContactPanel,  // deprecated alias for ContactPanel
  FinancialsPanel,
  TransactionFinancialsPanel,
  LinkagesPanel,
  ShippingPanel,
  BasicInformationPanel,
  CommunicationsPanel,
} from '@/apps/common/components/panels';

// Admin panels
import {
  MetadataPanel,
  RefsPanel,
  PrefsPanel,
  RawDataPanel,
} from '@/apps/common/components/panels';

// Shared components (not in panels/)
import JsonFieldEditor from '@/apps/common/components/JsonFieldEditor';
import TransactionToolbar from '@/apps/common/components/TransactionToolbar';

// Types
import type {
  BasePanelProps, EntityType, UserRole,
  EntityMetadata, EntityRefs, EntityPrefs, EntityComments,
  ActionEntry, CommentEntry, QAEntry, DocumentEntry,
  FinancialSummary, EmailLink, PhoneLink, AddressLink,
  LinkageData, LinkedRecord,
} from '@/apps/common/components/panels';

// Utilities
import {
  usePermissions,
  ADMIN_ROLES, MANAGER_ROLES, USER_ROLES, ALL_ROLES,
  uploadDocument, uploadDocuments, deleteDocument,
  getQAQuestions, getQAAnswers, applyQuestionGroup,
} from '@/apps/common/components/panels';
```

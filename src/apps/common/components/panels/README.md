# Panels — Canonical Location & Rules

> **Updated:** 2026-03-13  
> **Rule:** All shared panels live here. No re-export shims. No legacy paths.

---

## Rules

### 1. One canonical path per component

Every panel has exactly one source file. Import it directly. Never create re-export shims or proxy files in other directories.

```tsx
// CORRECT — import from canonical location
import ContactPanel from "@/apps/common/components/panels/ContactPanel";
import CommentsPanel from "@/apps/common/components/panels/CommentsPanel";
import TransactionToolbar from "@/apps/common/components/TransactionToolbar";
import JsonFieldEditor from "@/apps/common/components/JsonFieldEditor";

// WRONG — never import from a shim or proxy
import ContactPanel from "./ContactPanel"; // shim in transactions/
import CommentsPanel from "../transactions/components/CommentsPanel"; // dead path
```

### 2. Where does it live?

| Scope                           | Path                                   | Examples                                                                            |
| ------------------------------- | -------------------------------------- | ----------------------------------------------------------------------------------- |
| **Shared across apps**          | `src/apps/common/components/panels/`   | ContactPanel, CommentsPanel, PaymentPanel, FinancialsPanel, DocumentsPanel          |
| **Shared non-panel components** | `src/apps/common/components/`          | TransactionToolbar, JsonFieldEditor, OrgSearchDialog                                |
| **Transaction-only**            | `src/apps/transactions/components/`    | SummaryCard, LinesCard, TransactionDetailBase, MetadataPanel (transaction-specific) |
| **Model-specific pages**        | `src/apps/{app}/models/{model}/pages/` | PaymentListPage, PaymentDetailPage                                                  |

Decision test: **"Is this used by more than one app?"**

- Yes → `common/components/panels/` (or `common/components/` if not a panel)
- No, transaction-only → `transactions/components/`
- No, model-specific → `models/{model}/pages/`

### 3. No barrel indirection for shims

The barrel at `common/components/panels/index.ts` re-exports real components. Never use a barrel to re-export a shim. Every barrel entry must point to an actual source file in the same directory.

### 4. Transaction-specific ≠ duplicate

`MetadataPanel` exists in both locations — this is correct:

| File                                         | Purpose                                                            |
| -------------------------------------------- | ------------------------------------------------------------------ |
| `common/components/panels/MetadataPanel.tsx` | Generic entity metadata (key-value editor)                         |
| `transactions/components/MetadataPanel.tsx`  | Transaction-specific metadata (history, health, flags, versioning) |

These are **different components** with different props and rendering. The naming collision is acceptable because they serve different contexts.

### 5. FinancialsPanel naming

`FinancialsPanel` is the component name. There is no `FinancialsCard`. The old alias was a naming mistake.

---

## Directory Structure

```
src/apps/common/components/
├── JsonFieldEditor.tsx              # Generic JSON editor (admin)
├── TransactionToolbar.tsx           # Action toolbar (save, clone, print)
├── OrgSearchDialog.tsx              # Org/customer search modal
│
└── panels/
    ├── README.md                    # THIS FILE — rules and inventory
    ├── index.ts                     # Barrel exports
    ├── types.ts                     # Shared types
    ├── getModelDetailPath.ts        # Model → detail route mapping
    ├── usePermissions.ts            # Permission checking hook
    ├── documentUpload.ts            # Upload utilities
    ├── qaUtils.ts                   # Q&A helpers
    │
    ├── # Entity Panels (used across all apps)
    ├── ActionsPanel.tsx             # Tasks with status tracking
    ├── BasicInformationPanel.tsx    # Org scalar fields
    ├── CommentsPanel.tsx            # Comments (Public/Process/Partner/History)
    ├── ContactInfoPanel.tsx            # Communication links
    ├── CommunicationsPanel.tsx      # Email/phone/address/domain CRUD
    ├── ContactPanel.tsx             # Contacts grouped by purpose
    ├── ContactPanelx2.tsx           # Contact normalization utilities
    ├── DocumentsPanel.tsx           # File uploads, preview, download
    ├── EmailGatePanel.tsx           # Email gateway integration
    ├── FinancialsPanel.tsx          # Org financials (credit, aging, AR/AP)
    ├── HistoryPanel.tsx             # Record history timeline
    ├── ItemsPanel.tsx               # Line items display
    ├── LinkagesPanel.tsx            # Cross-table record flow
    ├── MetadataPanel.tsx            # Generic metadata editor
    ├── ModelDataPanel.tsx           # Generic model data display
    ├── OrgLinkPanel.tsx             # Org relationship links
    ├── PanelTable.tsx               # Shared table component for panels
    ├── PaymentPanel.tsx             # Payments linked to entity
    ├── PrefsPanel.tsx               # User/entity preferences
    ├── QAPanel.tsx                  # Q&A workflow
    ├── RawDataPanel.tsx             # Raw JSON viewer
    ├── RefsPanel.tsx                # Relationships & lineage
    ├── SerialPanel.tsx              # Serial numbers
    ├── ShippingPanel.tsx            # Shipping details
    ├── TemplateQAPanel.tsx          # Template-based Q&A
    ├── TransactionPanel.tsx         # Record header (ida/status/totals) + TransactionToolbar
    └── TransactionsPanel.tsx        # Related transactions list
```

Transaction-only components (NOT shared panels):

````
src/apps/transactions/components/
├── TransactionDetailBase.tsx        # Base shell for transaction details
├── SummaryCard.tsx                  # Transaction header (totals, dates)
├── LinesCard.tsx                    # Line items grid
├── LineDetailsModal.tsx             # Single line item editing
├── MetadataPanel.tsx                # Transaction-specific metadata
├── ContactLinksTable.tsx            # Spreadsheet-style contact table
├── CustomerSalesPanel.tsx           # Customer financial data + terms
├── PartySelector.tsx                # Customer/Vendor search dropdown
├── TransactionItemSearch.tsx        # Item search for line items
├── PaymentDialog.tsx                # Payment creation modal
├── AddPaymentModal.tsx              # Quick payment against order
├── ApplyPaymentModal.tsx            # Apply payment to invoice
├── SplitLineModal.tsx               # Split line quantity
├── FieldLabel.tsx                   # Label styling
├── QATab.tsx                        # QAPanel wrapper
├── ActivityLogTab.tsx               # Timeline view
├── QuickAddRecent.tsx               # Recent items
├── PrintPreviewModal.tsx            # Print preview
├── InventoryCheckDialog.tsx         # Inventory validation
├── TransactionTaskModal.tsx         # Task creation slide-out
├── ActionsModal.tsx                 # Legacy task modal
└── print/                           # Print document templates
``` |
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
````

### Default Permissions

| Panel                 | View     | Edit  | Theme   |
| --------------------- | -------- | ----- | ------- |
| BasicInformationPanel | all      | user+ | Slate   |
| CommentsPanel         | all      | user+ | Blue    |
| ActionsPanel          | all      | user+ | Emerald |
| DocumentsPanel        | all      | user+ | Slate   |
| QAPanel               | all      | user+ | Indigo  |
| ContactPanel          | all      | user+ | Blue    |
| CommunicationsPanel   | all      | user+ | Teal    |
| LinkagesPanel         | all      | admin | Violet  |
| FinancialsPanel       | manager+ | admin | Green   |
| ShippingPanel         | all      | user+ | Slate   |
| MetadataPanel         | admin    | admin | Amber   |
| RefsPanel             | admin    | admin | Cyan    |
| PrefsPanel            | user+    | admin | Purple  |
| RawDataPanel          | admin    | admin | Gray    |

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
    rating: number;
    completeness: number;
    accuracy: number;
    freshness: number;
    consistency: number;
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
    parent_id?: number;
    parent_type?: string;
    source_id?: number;
    source_type?: string;
  };
}
```

### `.prefs` → PrefsPanel

```typescript
interface EntityPrefs {
  userdefined?: Record<string, unknown>;
  display?: {
    layout?: "grid" | "list" | "card" | "table";
    columns?: string[];
    sort?: { field: string; order: "asc" | "desc" };
  };
  notifications?: {
    email?: boolean;
    sms?: boolean;
    push?: boolean;
    frequency?: "immediate" | "daily" | "weekly";
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
  ts: string;
  by: string | number;
  text: string;
  source?: string;
}
```

### `.actions` → ActionsPanel

```typescript
interface ActionEntry {
  required?: boolean;
  status?: "pending" | "in_progress" | "completed" | "cancelled" | "on_hold";
  who?: number | string;
  when?: number | string;
  what?: string;
  kind?:
    | "task"
    | "followup"
    | "call"
    | "email"
    | "review"
    | "approve"
    | "ship"
    | "other";
  priority?: "low" | "normal" | "high" | "urgent";
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

| Panel              | Source                                                          |
| ------------------ | --------------------------------------------------------------- |
| TransactionToolbar | `common/components/TransactionToolbar` (via re-export)          |
| ContactPanel       | `common/panels/ContactPanel` (via re-export)                    |
| ContactLinksTable  | `transactions/components/ContactLinksTable`                     |
| CommentsPanel      | `common/panels/CommentsPanel` (via re-export)                   |
| MetadataPanel      | `transactions/components/MetadataPanel` (transaction-specific)  |
| FinancialsCard     | `common/panels/TransactionFinancialsPanel` (via re-export)      |
| DocumentsPanel     | `common/panels/DocumentsPanel`                                  |
| JsonFieldEditor    | `common/components/JsonFieldEditor` (via re-export)             |
| QATab              | `transactions/components/QATab` (wraps `common/panels/QAPanel`) |

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
  FinancialsPanel,
  TransactionFinancialsPanel,
  LinkagesPanel,
  ShippingPanel,
  BasicInformationPanel,
  CommunicationsPanel,
} from "@/apps/common/components/panels";

// Admin panels
import {
  MetadataPanel,
  RefsPanel,
  PrefsPanel,
  RawDataPanel,
} from "@/apps/common/components/panels";

// Shared components (not in panels/)
import JsonFieldEditor from "@/apps/common/components/JsonFieldEditor";
import TransactionToolbar from "@/apps/common/components/TransactionToolbar";

// Types
import type {
  BasePanelProps,
  EntityType,
  UserRole,
  EntityMetadata,
  EntityRefs,
  EntityPrefs,
  EntityComments,
  ActionEntry,
  CommentEntry,
  QAEntry,
  DocumentEntry,
  FinancialSummary,
  EmailLink,
  PhoneLink,
  AddressLink,
  LinkageData,
  LinkedRecord,
} from "@/apps/common/components/panels";

// Utilities
import {
  usePermissions,
  ADMIN_ROLES,
  MANAGER_ROLES,
  USER_ROLES,
  ALL_ROLES,
  uploadDocument,
  uploadDocuments,
  deleteDocument,
  getQAQuestions,
  getQAAnswers,
  applyQuestionGroup,
} from "@/apps/common/components/panels";
```

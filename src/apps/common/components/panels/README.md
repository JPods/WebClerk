# Shared Panel Components

Reusable panel components for displaying and editing common data structures across all model detail pages. These panels align with the Django `BaseModel` JSONB field structure (`.metadata`, `.refs`, `.prefs`, `.comments`, `.actions`).

## Naming Convention

All shared panel components follow the `{Name}Panel` suffix convention:

| Panel                | Purpose                                         | Data Source                          |
| -------------------- | ----------------------------------------------- | ------------------------------------ |
| `CommentsPanel`      | Comments with tabs (Public/Process/Partner/History) | `.comments`                      |
| `MetadataPanel`      | Admin-only key-value metadata editor            | `.metadata`                          |
| `RefsPanel`          | Admin-only relationships & lineage viewer       | `.refs`                              |
| `PrefsPanel`         | User/entity preferences (display/notifications) | `.prefs`                             |
| `RawDataPanel`       | Admin-only raw JSON viewer with syntax highlight| Full entity                          |
| `ActionsPanel`       | Tasks/actions with status (pending/done/blocked)| `.actions`                           |
| `DocumentsPanel`     | File uploads & attachments                      | `.refs.links.document`               |
| `QAPanel`            | Q&A list with question/answer workflow          | Custom or `.qa`                      |
| `ContactLinksPanel`  | Linked contacts grouped by role                 | `.refs.links.contact`                |
| `FinancialsPanel`    | Financial summary with breakdown                | Computed or `.financials`            |
| `CommunicationsPanel`| Emails, phones, addresses management            | `.refs.links.{email,phone,location}` |
| `LinkagesPanel`      | Cross-table record linkage (flow tracking)      | Linkage record or `.refs.links.linkage` |

## Role-Based Access Control

All panels support role-based visibility and edit permissions via the `usePermissions` hook:

```typescript
interface PanelPermissions {
  viewRoles: UserRole[];  // Roles that can view this panel
  editRoles: UserRole[];  // Roles that can edit data in this panel
}

type UserRole = 'admin' | 'superadmin' | 'super_admin' | 'administrator' 
              | 'manager' | 'user' | 'viewer' | 'guest';

// Role groups for convenience
const ADMIN_ROLES = ['admin', 'superadmin', 'super_admin', 'administrator'];
const MANAGER_ROLES = [...ADMIN_ROLES, 'manager'];
const USER_ROLES = [...MANAGER_ROLES, 'user'];
const ALL_ROLES = [...USER_ROLES, 'viewer', 'guest'];
```

### Default Permissions

| Panel                | View Roles | Edit Roles | Theme Color |
| -------------------- | ---------- | ---------- | ----------- |
| `CommentsPanel`      | all        | user+      | Blue        |
| `MetadataPanel`      | admin      | admin      | Amber       |
| `RefsPanel`          | admin      | admin      | Cyan        |
| `PrefsPanel`         | user+      | admin      | Purple      |
| `RawDataPanel`       | admin      | admin      | Gray        |
| `ActionsPanel`       | all        | user+      | Emerald     |
| `DocumentsPanel`     | all        | user+      | Slate       |
| `QAPanel`            | all        | user+      | Indigo      |
| `ContactLinksPanel`  | all        | user+      | Blue        |
| `FinancialsPanel`    | manager+   | admin      | Green       |
| `CommunicationsPanel`| all        | user+      | Teal        |
| `LinkagesPanel`      | all        | admin      | Violet      |

### Using Permissions

```tsx
import { CommentsPanel, usePermissions } from '@/apps/common/components/panels';

// Automatic permission checking
<CommentsPanel
  entityType="contact"
  entityId={contact.id}
  data={contact.comments}
  onChange={handleCommentsChange}
/>

// Override permissions
<CommentsPanel
  entityType="contact"
  entityId={contact.id}
  data={contact.comments}
  onChange={handleCommentsChange}
  viewRoles={['admin', 'manager']}  // Restrict viewing
  editRoles={['admin']}             // Restrict editing
  readOnly={true}                   // Force read-only
/>
```

## Common Props Interface

All panels extend from `BasePanelProps`:

```typescript
interface BasePanelProps<T = unknown> {
  entityType: EntityType;       // Type of entity (contact, order, etc.)
  entityId: number;             // ID of the entity
  data: T;                      // The data to display
  onChange?: (data: T) => void; // Callback when data changes
  readOnly?: boolean;           // Force read-only mode
  viewRoles?: UserRole[];       // Override default view roles
  editRoles?: UserRole[];       // Override default edit roles
  className?: string;           // Additional CSS classes
  compact?: boolean;            // Compact display mode
  title?: string;               // Title override
  defaultCollapsed?: boolean;   // Start collapsed
}
```

## Django Model Alignment

These panels align with the Django `BaseModel` (from `common/models.py`) JSONB fields:

### `.metadata` - Entity Metadata

Based on `MetadataMixin` with `default_metadata()`:

```typescript
interface EntityMetadata {
  security?: string;
  publish?: string;
  priority?: string;
  version?: string;
  access?: { view: number[]; edit: number[] };
  resources?: { required: object; allocated: object };
  flow?: object;      // Lineage hints, parent/child hops
  source?: object;    // Campaign/vendor/manufacturer attribution
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
  undefined?: object;
  [key: string]: unknown;
}
```

### `.refs` - Relationships & Classification

Based on `RefsMixin` with `default_refs()` and `LINK_DENORMALIZE_FIELDS`:

```typescript
interface EntityRefs {
  keywords?: string[];
  tags?: string[];
  categories?: string[];
  related_ids?: number[];
  depends_on?: Record<string, number[]>;  // Execution gating
  links?: {
    contact?: ContactLink[];   // {id, email, name_first, name_last, company, title, role}
    email?: EmailLink[];       // {id, email, name, type, is_primary}
    phone?: PhoneLink[];       // {id, number, format, name}
    location?: AddressLink[];  // {id, address1, city, state, zip, country, full}
    document?: DocumentLink[]; // {id, name, type}
    item?: ItemLink[];         // {id, name, sku, description, kind, uom}
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

### `.prefs` - Preferences

Based on `PrefsMixin` with `default_prefs()`:

```typescript
interface EntityPrefs {
  userdefined?: Record<string, unknown>;
  display?: {
    layout?: 'grid' | 'list' | 'card' | 'table';
    columns?: string[];
    sort?: { field: string; order: 'asc' | 'desc' };
    theme?: 'light' | 'dark' | 'system';
  };
  notifications?: {
    email?: boolean;
    sms?: boolean;
    push?: boolean;
    frequency?: 'immediate' | 'daily' | 'weekly';
  };
  defaults?: Record<string, unknown>;
}
```

### `.comments` - Structured Comments

Based on `CommentsMixin` with `default_comments()`:

```typescript
interface EntityComments {
  public?: string | CommentEntry[];   // Customer-visible
  process?: string | CommentEntry[];  // Internal process notes
  partner?: string | CommentEntry[];  // Partner/vendor notes
  notes?: CommentEntry[];             // Append-only history
  general?: Record<string, CommentEntry[]>;
  records?: Record<string, Record<string, CommentEntry[]>>;
}

interface CommentEntry {
  ts: string;       // ISO timestamp
  by: string | number;
  text: string;
  source?: string;
}
```

### `.actions` - Next-Step Metadata

Based on `ActionsMixin`:

```typescript
interface ActionEntry {
  required?: boolean;
  status?: 'pending' | 'in_progress' | 'completed' | 'cancelled' | 'on_hold';
  who?: number | string;      // contact_id or username
  when?: number | string;     // ms epoch or ISO date
  what?: string;              // Description
  kind?: 'task' | 'followup' | 'call' | 'email' | 'review' | 'approve' | 'ship' | 'other';
  priority?: 'low' | 'normal' | 'high' | 'urgent';
  extra?: object;             // Free-form per domain
}
```

## Directory Structure

```
src/apps/common/components/panels/
├── README.md                 # This documentation
├── index.ts                  # Barrel exports
├── types.ts                  # Shared types (aligned with Django models)
├── usePermissions.ts         # Permission checking hook
│
├── CommentsPanel.tsx         # Comments with Public/Process/Partner/History tabs
├── MetadataPanel.tsx         # Admin-only metadata key-value editor
├── RefsPanel.tsx             # Admin-only refs viewer with link navigation
├── PrefsPanel.tsx            # Preferences editor (display/notifications)
├── RawDataPanel.tsx          # Admin-only raw JSON viewer
│
├── ActionsPanel.tsx          # Task/action list with status tracking
├── DocumentsPanel.tsx        # File attachments with upload
├── QAPanel.tsx               # Q&A with question/answer workflow
├── ContactLinksPanel.tsx     # Linked contacts grouped by role
├── FinancialsPanel.tsx       # Financial summary with breakdown
├── CommunicationsPanel.tsx   # Emails, phones, addresses
└── LinkagesPanel.tsx         # Cross-table record linkage (flow tracking)
```

## Usage Examples

### Basic Usage

```tsx
import { 
  CommentsPanel, 
  ActionsPanel,
  FinancialsPanel,
  ContactLinksPanel,
  MetadataPanel,
  RefsPanel,
} from '@/apps/common/components/panels';

const OrderDetail: React.FC<{ order: Order }> = ({ order }) => {
  const [data, setData] = useState(order);
  
  const updateField = <K extends keyof Order>(field: K, value: Order[K]) => {
    setData(prev => ({ ...prev, [field]: value }));
  };

  return (
    <div className="grid grid-cols-2 gap-4">
      {/* Actions - visible to all, editable by users */}
      <ActionsPanel
        entityType="order"
        entityId={order.id}
        data={data.actions}
        onChange={(actions) => updateField('actions', actions)}
      />
      
      {/* Financials - visible to managers, editable by admins */}
      <FinancialsPanel
        entityType="order"
        entityId={order.id}
        data={data.financials}
        currency={data.currency}
      />
      
      {/* Contact links */}
      <ContactLinksPanel
        entityType="order"
        entityId={order.id}
        data={data.refs?.links?.contact}
        onChange={(contacts) => updateField('refs', {
          ...data.refs,
          links: { ...data.refs?.links, contact: contacts }
        })}
      />
      
      {/* Comments */}
      <CommentsPanel
        entityType="order"
        entityId={order.id}
        data={data.comments}
        onChange={(comments) => updateField('comments', comments)}
      />
      
      {/* Admin-only panels */}
      <MetadataPanel
        entityType="order"
        entityId={order.id}
        data={data.metadata}
        onChange={(metadata) => updateField('metadata', metadata)}
      />
      
      <RefsPanel
        entityType="order"
        entityId={order.id}
        data={data.refs}
      />
    </div>
  );
};
```

### Compact Mode for Sidebars

```tsx
<CommentsPanel
  entityType="contact"
  entityId={contact.id}
  data={contact.comments}
  compact={true}
  defaultCollapsed={true}
/>
```

### Read-Only Display

```tsx
<FinancialsPanel
  entityType="invoice"
  entityId={invoice.id}
  data={invoice.financials}
  readOnly={true}
/>
```

## Implementation Status

| Panel                | Status | Features |
| -------------------- | ------ | -------- |
| `CommentsPanel`      | ✅ Done | Tabs, history, role-based |
| `MetadataPanel`      | ✅ Done | Key-value editor, admin-only |
| `RefsPanel`          | ✅ Done | Link navigation, lineage display |
| `PrefsPanel`         | ✅ Done | Display/notification prefs |
| `RawDataPanel`       | ✅ Done | Syntax highlight, search, copy |
| `ActionsPanel`       | ✅ Done | Status tracking, due dates, priority |
| `DocumentsPanel`     | ✅ Done | Upload, download, file icons |
| `QAPanel`            | ✅ Done | Question/answer workflow |
| `ContactLinksPanel`  | ✅ Done | Role grouping, search/add |
| `FinancialsPanel`    | ✅ Done | Breakdown, payments, balance |
| `CommunicationsPanel`| ✅ Done | Email/phone/address CRUD |
| `LinkagesPanel`      | ✅ Done | Cross-table linking, flow tracking |

## Imports

```tsx
// Import individual panels
import { CommentsPanel } from '@/apps/common/components/panels';

// Import multiple panels
import { 
  CommentsPanel,
  ActionsPanel,
  FinancialsPanel,
  ContactLinksPanel,
  DocumentsPanel,
  QAPanel,
  CommunicationsPanel,
  LinkagesPanel,
  MetadataPanel,
  RefsPanel,
  PrefsPanel,
  RawDataPanel,
} from '@/apps/common/components/panels';

// Import types
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
} from '@/apps/common/components/panels';

// Import permission utilities
import { 
  usePermissions,
  ADMIN_ROLES,
  MANAGER_ROLES,
  USER_ROLES,
  ALL_ROLES,
  DEFAULT_PANEL_PERMISSIONS,
} from '@/apps/common/components/panels';
```

## LinkagesPanel - Cross-Table Record Flow

The `LinkagesPanel` displays records from multiple tables that are linked together through a Linkage hub. This tracks document/record relationships as items flow through business processes:

```
Proposal → Order → Invoice → Payment
    ↓         ↓        ↓         ↓
 [all linked by a common Linkage record]
```

### Linkage Data Structure

Based on Django `Linkage` model from `apps/docs/models/linkage.py`:

```typescript
interface LinkageData {
  id: number;
  ida?: string;
  purpose?: string;        // e.g., "Item Transfer", "Service Order"
  name?: string;           // Human-readable linkage name
  note?: string;           // Additional context
  refs?: {
    links?: Record<string, LinkedRecord[] | number[]>;  // {table_name: [records/ids]}
  };
  metadata?: { history?: { created?: {...}, modified?: {...} } };
  dt_created?: number;
  dt_modified?: number;
}

interface LinkedRecord {
  id: number;
  ida?: string;
  name?: string;
  display?: string;
  status?: string;
  dt_created?: number;
  dt_modified?: number;
}
```

### LinkagesPanel Usage

```tsx
import { LinkagesPanel } from '@/apps/common/components/panels';

// Basic usage
<LinkagesPanel
  entityType="order"
  entityId={order.id}
  data={order.linkage}  // LinkageData or null
  onRecordClick={(table, id, record) => {
    // Navigate to the linked record
    navigate(`/${table}/${id}`);
  }}
/>

// With custom flow highlighting
<LinkagesPanel
  entityType="invoice"
  entityId={invoice.id}
  data={invoice.linkage}
  flowTables={['proposal', 'order', 'invoice', 'payment']}
  tableDisplayNames={{
    'sales_order': 'Sales Orders',
    'purchase_order': 'Purchase Orders',
  }}
  onViewLinkage={(linkageId) => navigate(`/linkages/${linkageId}`)}
/>
```

### LinkagesPanel Props

| Prop                | Type                                           | Description                              |
| ------------------- | ---------------------------------------------- | ---------------------------------------- |
| `data`              | `LinkageData \| null`                          | Linkage data (null if no linkage exists) |
| `onRecordClick`     | `(table, id, record?) => void`                 | Callback when clicking linked record     |
| `onViewLinkage`     | `(linkageId) => void`                          | Callback to view linkage details         |
| `flowTables`        | `string[]`                                     | Tables to highlight in business flow     |
| `tableDisplayNames` | `Record<string, string>`                       | Custom display names for tables          |
---

## Implementation Plan: Org & Transaction UI Integration

### Overview

Integrate the shared panel components into existing model detail pages across the application. This will replace ad-hoc implementations with standardized, permission-aware panels.

### Phase 1: Contacts & Core Models

**Target Pages:**
- `ContactDetail.tsx` - Core contact management (primary focus)
- `CustomerDetail.tsx` - Customer org view
- `VendorDetail.tsx` - Vendor org view
- `ManufacturerDetail.tsx` - Manufacturer org view

**Panels to Add:**

| Page | Panels | Priority |
|------|--------|----------|
| ContactDetail | CommentsPanel, CommunicationsPanel, DocumentsPanel, ActionsPanel, PrefsPanel, LinkagesPanel | High |
| CustomerDetail | CommentsPanel, ContactLinksPanel, FinancialsPanel, DocumentsPanel, ActionsPanel, LinkagesPanel | High |
| VendorDetail | CommentsPanel, ContactLinksPanel, DocumentsPanel, ActionsPanel, QAPanel, LinkagesPanel | High |
| ManufacturerDetail | CommentsPanel, ContactLinksPanel, DocumentsPanel, ActionsPanel | Medium |

#### Contact-Specific Implementation

The `ContactDetail` page is foundational - contacts link to nearly every other entity in the system.

**ContactDetail Panel Layout:**

```
┌─────────────────────────────────────────────────────────────────┐
│  Contact Header (name, company, title, role, avatar)            │
├─────────────────────────────────────────────────────────────────┤
│  ┌─────────────────────────┐  ┌─────────────────────────────┐   │
│  │  CommunicationsPanel    │  │  ActionsPanel               │   │
│  │  - Emails (primary/alt) │  │  - Pending tasks            │   │
│  │  - Phones (work/mobile) │  │  - Follow-ups               │   │
│  │  - Addresses            │  │  - Reminders                │   │
│  └─────────────────────────┘  └─────────────────────────────┘   │
│  ┌─────────────────────────┐  ┌─────────────────────────────┐   │
│  │  CommentsPanel          │  │  DocumentsPanel             │   │
│  │  - Public notes         │  │  - Contracts                │   │
│  │  - Process notes        │  │  - Agreements               │   │
│  │  - Partner notes        │  │  - ID docs                  │   │
│  └─────────────────────────┘  └─────────────────────────────┘   │
│  ┌─────────────────────────┐  ┌─────────────────────────────┐   │
│  │  LinkagesPanel          │  │  PrefsPanel                 │   │
│  │  - Related orders       │  │  - Communication prefs      │   │
│  │  - Related invoices     │  │  - Display settings         │   │
│  │  - Related proposals    │  │  - Notification opts        │   │
│  └─────────────────────────┘  └─────────────────────────────┘   │
│  ┌───────────────────────────────────────────────────────────┐  │
│  │  Admin-Only: MetadataPanel | RefsPanel | RawDataPanel     │  │
│  └───────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
```

**Contact-Specific Tasks:**
- [ ] Create `ContactDetailPanels.tsx` wrapper component
- [ ] Implement `useContactMutations` hook for panel onChange handlers
- [ ] Add CommunicationsPanel with email/phone/address CRUD
- [ ] Wire ActionsPanel for contact-specific actions (call, email, follow-up)
- [ ] Connect LinkagesPanel to show orders/invoices where contact is linked
- [ ] Add PrefsPanel for communication preferences (opt-in/out)
- [ ] Test admin panels visibility (MetadataPanel, RefsPanel, RawDataPanel)

**Org Detail Tasks:**
- [ ] Create `OrgDetailPanels.tsx` shared wrapper for Customer/Vendor/Manufacturer
- [ ] Wire up `onChange` handlers to API mutation hooks
- [ ] Add ContactLinksPanel to show employees/reps/contacts
- [ ] Add FinancialsPanel for customer/vendor account summary
- [ ] Test permission visibility across user roles

### Phase 2: Transaction Documents

**Target Pages:**
- `OrderDetail.tsx` / `SalesOrderDetail.tsx`
- `InvoiceDetail.tsx`
- `ProposalDetail.tsx`
- `PurchaseOrderDetail.tsx`
- `WorkOrderDetail.tsx`

**Panels to Add:**

| Page | Panels | Priority |
|------|--------|----------|
| OrderDetail | CommentsPanel, ContactLinksPanel, FinancialsPanel, DocumentsPanel, ActionsPanel, LinkagesPanel, QAPanel | High |
| InvoiceDetail | CommentsPanel, ContactLinksPanel, FinancialsPanel, DocumentsPanel, LinkagesPanel | High |
| ProposalDetail | CommentsPanel, ContactLinksPanel, FinancialsPanel, DocumentsPanel, ActionsPanel, QAPanel | High |
| PurchaseOrderDetail | CommentsPanel, ContactLinksPanel, FinancialsPanel, DocumentsPanel, ActionsPanel, LinkagesPanel | Medium |
| WorkOrderDetail | CommentsPanel, ContactLinksPanel, DocumentsPanel, ActionsPanel, LinkagesPanel, QAPanel | Medium |

**Tasks:**
- [ ] Create `TransactionDetailPanels.tsx` shared wrapper
- [ ] Implement linkage fetching hook (`useLinkage`)
- [ ] Wire LinkagesPanel with navigation callbacks
- [ ] Add financial calculation helpers for FinancialsPanel
- [ ] Deprecate old `CommentsTab`, `DocumentsTab`, `QATab` components

### Phase 3: Line Item Details

**Target Pages:**
- `OrderLineDetail.tsx`
- `ProposalLineDetail.tsx`
- `InvoiceLineDetail.tsx`
- `WorkOrderLineDetail.tsx`

**Panels to Add:**

| Page | Panels | Priority |
|------|--------|----------|
| All Line Details | CommentsPanel, ActionsPanel, LinkagesPanel, DocumentsPanel | Medium |

**Tasks:**
- [ ] Create `LineDetailPanels.tsx` compact wrapper
- [ ] Ensure linkage flows properly between header and lines
- [ ] Add line-specific action templates

### Phase 4: Admin & Support Pages

**Target Pages:**
- `ItemDetail.tsx` - Product/inventory items
- `ProjectDetail.tsx` - Project management
- `CampaignDetail.tsx` - Marketing campaigns
- `SettingDetail.tsx` - System settings

**Panels to Add:**

| Page | Panels | Priority |
|------|--------|----------|
| ItemDetail | CommentsPanel, DocumentsPanel, ContactLinksPanel (vendors), PrefsPanel | Low |
| ProjectDetail | CommentsPanel, ContactLinksPanel, DocumentsPanel, ActionsPanel, FinancialsPanel | Low |
| CampaignDetail | CommentsPanel, ContactLinksPanel, DocumentsPanel, ActionsPanel | Low |
| SettingDetail | MetadataPanel, PrefsPanel, RawDataPanel | Low |

### Implementation Pattern

```tsx
// Example: ContactDetail.tsx integration

import {
  CommentsPanel,
  CommunicationsPanel,
  DocumentsPanel,
  ActionsPanel,
  PrefsPanel,
  LinkagesPanel,
  MetadataPanel,
  RefsPanel,
  RawDataPanel,
} from '@/apps/common/components/panels';

const ContactDetail: React.FC<{ contact: Contact }> = ({ contact }) => {
  const [data, setData] = useState(contact);
  const { mutate: updateContact } = useUpdateContact();
  const { data: linkage } = useLinkage(contact.refs?.links?.linkage?.[0]);
  const navigate = useNavigate();

  const handleFieldChange = <K extends keyof Contact>(field: K, value: Contact[K]) => {
    const updated = { ...data, [field]: value };
    setData(updated);
    updateContact({ id: contact.id, [field]: value });
  };

  return (
    <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
      {/* Contact Header */}
      <div className="lg:col-span-2">
        <ContactHeader contact={data} />
      </div>

      {/* Left Column - Communications & Actions */}
      <div className="space-y-4">
        <CommunicationsPanel
          entityType="contact"
          entityId={contact.id}
          emails={data.refs?.links?.email}
          phones={data.refs?.links?.phone}
          addresses={data.refs?.links?.location}
          onEmailChange={(emails) => handleFieldChange('refs', {
            ...data.refs,
            links: { ...data.refs?.links, email: emails }
          })}
          onPhoneChange={(phones) => handleFieldChange('refs', {
            ...data.refs,
            links: { ...data.refs?.links, phone: phones }
          })}
          onAddressChange={(addresses) => handleFieldChange('refs', {
            ...data.refs,
            links: { ...data.refs?.links, location: addresses }
          })}
        />
        <ActionsPanel
          entityType="contact"
          entityId={contact.id}
          data={data.actions}
          onChange={(actions) => handleFieldChange('actions', actions)}
        />
        <CommentsPanel
          entityType="contact"
          entityId={contact.id}
          data={data.comments}
          onChange={(comments) => handleFieldChange('comments', comments)}
        />
      </div>

      {/* Right Column - Documents & Preferences */}
      <div className="space-y-4">
        <DocumentsPanel
          entityType="contact"
          entityId={contact.id}
          data={data.refs?.links?.document}
          onChange={(docs) => handleFieldChange('refs', {
            ...data.refs,
            links: { ...data.refs?.links, document: docs }
          })}
        />
        <LinkagesPanel
          entityType="contact"
          entityId={contact.id}
          data={linkage}
          onRecordClick={(table, id) => navigate(`/${table}/${id}`)}
          flowTables={['proposal', 'order', 'invoice']}
        />
        <PrefsPanel
          entityType="contact"
          entityId={contact.id}
          data={data.prefs}
          onChange={(prefs) => handleFieldChange('prefs', prefs)}
        />
      </div>

      {/* Admin-Only Section */}
      <div className="lg:col-span-2 space-y-4">
        <MetadataPanel
          entityType="contact"
          entityId={contact.id}
          data={data.metadata}
          onChange={(metadata) => handleFieldChange('metadata', metadata)}
        />
        <RefsPanel
          entityType="contact"
          entityId={contact.id}
          data={data.refs}
        />
        <RawDataPanel
          entityType="contact"
          entityId={contact.id}
          data={data}
        />
      </div>
    </div>
  );
};
```

```tsx
// Example: OrderDetail.tsx integration

import {
  CommentsPanel,
  ContactLinksPanel,
  FinancialsPanel,
  DocumentsPanel,
  ActionsPanel,
  LinkagesPanel,
  QAPanel,
  MetadataPanel,
  RefsPanel,
  RawDataPanel,
} from '@/apps/common/components/panels';

const OrderDetail: React.FC<{ order: Order }> = ({ order }) => {
  const [data, setData] = useState(order);
  const { mutate: updateOrder } = useUpdateOrder();
  const { data: linkage } = useLinkage(order.refs?.links?.linkage?.[0]);
  const navigate = useNavigate();

  const handleFieldChange = <K extends keyof Order>(field: K, value: Order[K]) => {
    const updated = { ...data, [field]: value };
    setData(updated);
    updateOrder({ id: order.id, [field]: value });
  };

  return (
    <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
      {/* Primary Info Section */}
      <div className="lg:col-span-2">
        <OrderHeader order={data} />
        <OrderLines lines={data.lines} />
      </div>

      {/* Left Column - User Panels */}
      <div className="space-y-4">
        <ActionsPanel
          entityType="order"
          entityId={order.id}
          data={data.actions}
          onChange={(actions) => handleFieldChange('actions', actions)}
        />
        <CommentsPanel
          entityType="order"
          entityId={order.id}
          data={data.comments}
          onChange={(comments) => handleFieldChange('comments', comments)}
        />
        <QAPanel
          entityType="order"
          entityId={order.id}
          data={data.qa}
          onChange={(qa) => handleFieldChange('qa', qa)}
        />
      </div>

      {/* Right Column - Reference Panels */}
      <div className="space-y-4">
        <FinancialsPanel
          entityType="order"
          entityId={order.id}
          data={data.financials}
          currency={data.currency}
        />
        <ContactLinksPanel
          entityType="order"
          entityId={order.id}
          data={data.refs?.links?.contact}
          onContactClick={(id) => navigate(`/contacts/${id}`)}
        />
        <DocumentsPanel
          entityType="order"
          entityId={order.id}
          data={data.refs?.links?.document}
          onChange={(docs) => handleFieldChange('refs', {
            ...data.refs,
            links: { ...data.refs?.links, document: docs }
          })}
        />
        <LinkagesPanel
          entityType="order"
          entityId={order.id}
          data={linkage}
          onRecordClick={(table, id) => navigate(`/${table}/${id}`)}
          onViewLinkage={(id) => navigate(`/linkages/${id}`)}
          flowTables={['proposal', 'order', 'invoice']}
        />
      </div>

      {/* Admin-Only Section */}
      <div className="lg:col-span-2 space-y-4">
        <MetadataPanel
          entityType="order"
          entityId={order.id}
          data={data.metadata}
          onChange={(metadata) => handleFieldChange('metadata', metadata)}
        />
        <RefsPanel
          entityType="order"
          entityId={order.id}
          data={data.refs}
        />
        <RawDataPanel
          entityType="order"
          entityId={order.id}
          data={data}
        />
      </div>
    </div>
  );
};
```

### Migration Checklist

For each detail page migration:

1. **Audit existing implementation**
   - [ ] Identify current comment/document/QA implementations
   - [ ] Note any custom business logic to preserve
   - [ ] Check for API endpoint compatibility

2. **Add panel imports**
   - [ ] Import required panels from `@/apps/common/components/panels`
   - [ ] Import types if needed

3. **Wire up data flow**
   - [ ] Connect panel `data` props to entity state
   - [ ] Implement `onChange` handlers with API mutations
   - [ ] Add navigation callbacks where needed

4. **Test permissions**
   - [ ] Verify admin panels hidden from non-admin users
   - [ ] Confirm edit buttons disabled for read-only roles
   - [ ] Test manager-only panels (FinancialsPanel)

5. **Deprecate old components**
   - [ ] Mark old tab components as deprecated
   - [ ] Remove after migration complete
   - [ ] Update imports in any remaining usages

### Files to Deprecate

After migration, these components should be removed:

```
src/apps/transactions/components/
├── CommentsTab.tsx        → Replace with CommentsPanel
├── DocumentsTab.tsx       → Replace with DocumentsPanel
├── QATab.tsx              → Replace with QAPanel
├── ContactsSection.tsx    → Replace with ContactLinksPanel
└── FinancialSummary.tsx   → Replace with FinancialsPanel
```

### Timeline Estimate

| Phase | Duration | Dependencies |
|-------|----------|--------------|
| Phase 1: Contacts & Orgs | 1 week | None |
| Phase 2: Transactions | 2 weeks | Phase 1, API hooks |
| Phase 3: Line Items | 1 week | Phase 2, Linkage API |
| Phase 4: Admin/Support | 1 week | Phase 1-3 complete |

**Total: ~5 weeks**
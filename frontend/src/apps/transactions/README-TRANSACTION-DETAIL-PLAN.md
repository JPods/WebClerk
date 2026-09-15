# Transaction Detail Pages - WC3 Schema Update Plan

> **Created**: 2026-01-14  
> **Updated**: 2026-01-14  
> **Status**: In Progress - Phase 1 Complete, Phase 1.5 (RBAC) Next  
> **Scope**: Update all `*Detail.tsx` pages in `src/apps/transactions/models/` to properly display wc3 JSONB fields

---

## Progress Summary

### ✅ Phase 1: Shared Infrastructure - COMPLETE

| Component | File | Status |
|-----------|------|--------|
| TypeScript Types | `types/transactionTypes.ts` | ✅ Complete |
| FieldLabel | `components/FieldLabel.tsx` | ✅ Complete |
| ContactPanel | `components/ContactPanel.tsx` | ✅ Complete |
| RefsLinksTable | `components/RefsLinksTable.tsx` | ✅ Complete |
| CommentsPanel | `components/CommentsPanel.tsx` | ✅ Complete |
| ActionsCard | `components/ActionsCard.tsx` | ✅ Complete |
| MetadataPanel | `components/MetadataPanel.tsx` | ✅ Complete |
| FinancialsCard | `components/FinancialsCard.tsx` | ✅ Complete |
| FlowDiagram | `components/FlowDiagram.tsx` | ✅ Complete |
| JsonFieldEditor | `components/JsonFieldEditor.tsx` | ✅ Complete |
| TransactionDetailBase | `components/TransactionDetailBase.tsx` | ✅ Complete |
| Component Index | `components/index.ts` | ✅ Complete |

### 🚧 Phase 1.5: Role-Based Access Control - NEXT

| Component | File | Status |
|-----------|------|--------|
| RoleGuard | `src/components/auth/RoleGuard.tsx` | ❌ Needs creation |
| useRoleAccess | `src/hooks/useRoleAccess.ts` | ❌ Needs creation |
| RoleFilterMixin | `apps/core/mixins/role_filter_mixin.py` | ❌ Needs creation (WC3) |
| Component minRole props | All shared components | ❌ Needs update |

### 🚧 Phase 2: Header Detail Pages - IN PROGRESS

| Model | File | Status |
|-------|------|--------|
| Invoice | `invoice/pages/InvoiceDetail.tsx` | ✅ Refactored (uses TransactionDetailBase) |
| Invoice (legacy) | `invoice/pages/qqq_InvoiceDetailLegacy.tsx` | ⚠️ Keep for reference |
| Order | `order/pages/OrderDetail.tsx` | ✅ Refactored (uses TransactionDetailBase) |
| Purchase | `purchase/pages/PurchaseDetail.tsx` | ✅ Refactored (uses TransactionDetailBase) |
| Proposal | `proposal/pages/ProposalDetail.tsx` | ✅ Refactored (uses TransactionDetailBase) |
| WorkOrder | `workorder/pages/WorkorderDetail.tsx` | ✅ Refactored (uses TransactionDetailBase) |
| Receipt | `receipt/pages/ReceiptDetail.tsx` | ✅ Refactored (uses TransactionDetailBase for UI; backend save via flow.py) |
| Requisition | `requisition/pages/RequisitionDetail.tsx` | ❌ Needs refactor |
| Project | `project/pages/ProjectDetail.tsx` | ❌ Needs refactor |

---

## Problem Statement

Current transaction detail pages (InvoiceDetail, OrderDetail, etc.) do not fully display all JSONB fields from the wc3 schema. The wc3 backend uses a rich composition of mixins that provide nested JSON structures like:

```json
{
  "refs": {
    "links": {
      "contact": [
        { "id": 123, "purpose": "billto", "name_first": "John", ... },
        { "id": 456, "purpose": "shipto", "name_first": "Jane", ... }
      ],
      "customer": [{ "id": 789, ... }],
      "item": [],
      ...
    },
    "keywords": ["urgent", "wholesale"],
    "tags": ["Q1-2026"],
    "depends_on": { "work_order": [101, 102] }
  },
  "metadata": { "history": {...}, "health": {...}, ... },
  "prefs": { "userdefined": {...} },
  "comments": { "public": "", "process": "", "notes": [...] },
  ...
}
```

These nested structures need consistent UI components for viewing and editing.

---

## Transaction Models Overview

### Header Models (TransactionBaseModel)

| Model | File | Status |
|-------|------|--------|
| Invoice | `invoice/pages/InvoiceDetail.tsx` | ⚠️ Partial implementation |
| Order | `order/pages/OrderDetail.tsx` | ⚠️ Needs update |
| Purchase | `purchase/pages/PurchaseDetail.tsx` | ⚠️ Needs update |
| Proposal | `proposal/pages/ProposalDetail.tsx` | ⚠️ Needs update |
| WorkOrder | `work_order/pages/WorkOrderDetail.tsx` | ⚠️ Needs update |
| Requisition | `requisition/pages/RequisitionDetail.tsx` | ⚠️ Needs update |
| Project | `project/pages/ProjectDetail.tsx` | ⚠️ Needs update |

### Line Models

| Model | File | Status |
|-------|------|--------|
| InvoiceLine | `invoice_line/pages/InvoiceLineDetail.tsx` | ❌ Needs creation |
| OrderLine | `order_line/pages/OrderLineDetail.tsx` | ❌ Needs creation |
| PurchaseLine | `purchase_line/pages/PurchaseLineDetail.tsx` | ❌ Needs creation |
| ProposalLine | `proposal_line/pages/ProposalLineDetail.tsx` | ❌ Needs creation |
| WorkOrderLine | `work_order_line/pages/WorkOrderLineDetail.tsx` | ❌ Needs creation |
| RequisitionLine | `requisition_line/pages/RequisitionLineDetail.tsx` | ❌ Needs creation |

---

## WC3 JSONB Field Structures

### From BaseModel (All Models Inherit These)

#### 1. `metadata` (MetadataMixin)
```typescript
interface TransactionMetadata {
  security?: string;
  publish?: string;
  priority?: string;
  version?: string;  // schema version e.g. "1.0"
  access?: {
    view: number[];  // contact IDs with view permission
    edit: number[];  // contact IDs with edit permission
  };
  resources?: {
    required: Record<string, unknown>;
    allocated: Record<string, unknown>;
  };
  flow?: Record<string, unknown>;   // lineage hints
  source?: Record<string, unknown>; // attribution
  history?: {
    created?: { dt: number; contact_id: number };
    modified?: { dt: number; contact_id: number };
    accessed?: { dt: number; contact_id: number };
    verified?: { dt: number; contact_id: number };
    synced?: { dt: number; contact_id: number };
  };
  health?: {
    rating: number;
    completeness: number;
    accuracy: number;
    freshness: number;
    consistency: number;
  };
  undefined?: Record<string, unknown>;
  flags?: {
    keywords_pending?: boolean;
    schema_rev?: number;
  };
  versioning?: {
    changed_fields?: string[];
    keywords_dt_refreshed?: number;
  };
}
```

#### 2. `refs` (RefsMixin) - **Most Complex**
```typescript
interface TransactionRefs {
  keywords?: string[];
  tags?: string[];
  categories?: string[];
  related_ids?: number[];
  links?: {
    // Each can be array of IDs or denormalized objects
    contact?: (number | ContactDenorm)[];
    customer?: (number | OrgDenorm)[];
    vendor?: (number | OrgDenorm)[];
    manufacturer?: (number | OrgDenorm)[];
    item?: (number | ItemDenorm)[];
    email?: (number | EmailDenorm)[];
    phone?: (number | PhoneDenorm)[];
    location?: (number | LocationDenorm)[];
    document?: number[];
    project?: number[];
    warehouse?: number[];
    glaccount?: number[];
    taxjurisdiction?: number[];
    paymentmethod?: number[];
    paymentterm?: number[];
    currency?: number[];
    // ... extensible
  };
  depends_on?: {
    action?: number[];
    work_order?: number[];
    work_order_line?: number[];
    purchase?: number[];
    // ... keyed by model name
  };
}

// Denormalized contact in refs.links.contact
interface ContactDenorm {
  id: number;
  purpose?: string;      // "billto", "shipto", "attention", etc.
  role?: string;         // "buyer", "approver", etc.
  name_first?: string;
  name_last?: string;
  display_name?: string;
  company?: string;
  title?: string;
  email?: string;
  phone?: string;
}

// Denormalized org in refs.links.customer/vendor/manufacturer
interface OrgDenorm {
  id: number;
  ida?: string;
  display_name?: string;
  company?: string;
  status?: string;
}

// Denormalized item
interface ItemDenorm {
  id: number;
  ida_item?: string;
  description?: string;
  sku?: string;
}
```

#### 3. `prefs` (PrefsMixin)
```typescript
interface TransactionPrefs {
  userdefined?: Record<string, unknown>;
  submission?: {
    as_submitted?: {
      data: unknown;
      dt: number;
      by: number;
    };
  };
}
```

#### 4. `comments` (CommentsMixin)
```typescript
interface TransactionComments {
  public?: string;   // Customer-visible note
  process?: string;  // Internal process note
  partner?: string;  // Partner/vendor note
  notes?: CommentEntry[];
  general?: {
    public?: CommentEntry[];
    process?: CommentEntry[];
    foreign?: CommentEntry[];
  };
  records?: Record<string, {
    public?: CommentEntry[];
    process?: CommentEntry[];
    foreign?: CommentEntry[];
  }>;
}

interface CommentEntry {
  ts: string;      // ISO timestamp
  by: string | number;
  text: string;
  source?: string;
}
```

#### 5. `actions` (ActionsMixin)
```typescript
interface TransactionActions {
  required?: boolean;
  status?: 'pending' | 'done' | 'blocked';
  who?: number;        // contact_id responsible
  when?: number;       // ms epoch due/next
  what?: string;       // description of action
  kind?: 'followup' | 'review' | 'ship' | 'approve' | string;
  extra?: Record<string, unknown>;
}
```

---

### TransactionBaseModel Fields (Header Only)

#### 6. `totals` (Header Totals)
```typescript
interface TransactionTotals {
  subtotal?: number;   // sum of line extended sell
  discount?: number;   // header discount amount
  taxable?: number;    // subtotal - discount
  tax?: number;        // sales tax amount
  shipping?: number;   // shipping charged
  other?: number;      // misc charges
  total?: number;      // grand total
  cost?: number;       // total cost
  margin?: number;     // total - cost
  margin_pc?: number;  // percentage
  received?: number;   // payments received (invoices)
  balance?: number;    // total - received (invoices)
}
```

#### 7. `cost` (Header Cost Envelope)
```typescript
interface HeaderCost {
  line_sum_goods?: number;
  line_sum_tax?: number;
  line_sum_shipping?: number;
  line_sum_handling?: number;
  handling?: number;
  freight?: number;
  tax_rate?: number;
  tax?: number;
  commissions?: number;
  total?: number;
}
```

#### 8. `sell` (Header Sell Envelope)
```typescript
interface HeaderSell {
  subtotal?: number;
  discount?: number;
  tax?: number;
  total?: number;
}
```

#### 9. `finance` (Tax & Financial)
```typescript
interface TransactionFinance {
  sales_tax_id?: number;
  sales_tax_name?: string;
  sales_tax_rate?: number;
  sales_tax?: number;
  cost_tax_id?: number;
  cost_tax_name?: string;
  cost_tax_rate?: number;
  cost_tax?: number;
  tax_subtotal?: number;
  tax_pc?: number;
  collection_expense?: number;
  exchange_expense?: number;
}
```

#### 10. `flow` (Transaction Lineage)
```typescript
interface TransactionFlow {
  source?: Array<{ type: string; id: number }>;
  children?: Array<{ type: string; id: number }>;
}
```

#### 11. `source` (Origin Attribution)
```typescript
interface TransactionSource {
  campaign_id?: number;
  catalog_id?: number;
  vendor_id?: number;
  manufacturer_id?: number;
}
```

---

### Line Model JSONB Fields

#### 12. `item` (Line Item Info)
```typescript
interface LineItem {
  item_id?: number;
  ida_item?: string;
  uuid_item?: string;
  description?: string;
  description_text?: string;
  time_lead?: number;
  locations?: unknown[];
  unit_measure?: string;
  sequence?: number;
  line_number?: number;
  is_deleted?: boolean;
  is_active?: boolean;
  is_archived?: boolean;
}
```

#### 13. `quantity` (Transaction-Type Specific)
```typescript
// Varies by transaction type
interface LineQuantity {
  placed?: number;      // quantity entered
  ordered?: number;     // original order qty (Proposal/SO)
  invoiced?: number;    // qty invoiced (SO)
  packed?: number;      // qty packed (Invoice)
  received?: number;    // qty received (PO/WO)
  remaining?: number;   // placed - fulfilled
  is_fixed?: boolean;
  precision?: number;
  is_blanket?: boolean;
  increment?: number;
}
```

#### 14. `cost` (Line Cost)
```typescript
interface LineCost {
  unit?: number;
  unit_base?: number;
  discount_percent?: number;
  discount_amount?: number;
  extended?: number;
  shipping?: number;
  handling?: number;
  freight?: number;
  commissions?: number;
  tax_rate?: number;
  tax?: number;
  is_fixed?: boolean;
  precision?: number;
  tax_code?: string;
  tax_code_id?: number;
  tax_lookup_id?: number;
}
```

#### 15. `price` (Line Sell Price - Sell Lines Only)
```typescript
interface LinePrice {
  unit?: number;
  unit_base?: number;
  discount_percent?: number;
  discount_amount?: number;
  extended?: number;
  is_fixed?: boolean;
  precision?: number;
}
```

#### 16. `tax` (Line Tax)
```typescript
interface LineTax {
  sales_rate?: number;
  sales?: number;
  cost_rate?: number;
  cost?: number;
  shipping?: number;
  tax_service_id?: number;
}
```

#### 17. `physical` (Shipping Dimensions)
```typescript
interface LinePhysical {
  weight?: { value: number; unit: string };
  dimensions?: { length: number; width: number; height: number; unit: string };
  volume?: { value: number; unit: string };
  package_count?: number;
  is_hazmat?: boolean;
}
```

---

## Implementation Plan

### Phase 1: Shared Infrastructure (Week 1)

#### 1.1 Create TypeScript Types
**File**: `src/apps/transactions/types/transactionTypes.ts`

- [ ] Define all interfaces above
- [ ] Export shared types for all transaction models
- [ ] Add type guards and helpers

#### 1.2 Create Shared JSONB Display Components
**Directory**: `src/apps/transactions/components/`

- [ ] `RefsLinksTable.tsx` - Tabular display of refs.links.* arrays
- [ ] `ContactLinkCard.tsx` - Single contact link with purpose/role
- [ ] `CommentsPanel.tsx` - Comments display with notes history
- [ ] `ActionsCard.tsx` - Action status and assignment
- [ ] `MetadataPanel.tsx` - Collapsible metadata display (admin)
- [ ] `FinancialsCard.tsx` - Totals/cost/sell summary
- [ ] `FlowDiagram.tsx` - Visual lineage (source → children)
- [ ] `JsonFieldEditor.tsx` - Generic JSON editor for admin
- [ ] `QuantityBadge.tsx` - Quantity display with remaining

#### 1.3 Create Base TransactionDetail Component
**File**: `src/apps/transactions/components/TransactionDetail.tsx`

- [ ] Tabbed interface similar to `OrgDetail.tsx`
- [ ] Common tabs: Info, Contacts, Comments, Financial, Admin
- [ ] Extensible for model-specific tabs

---

### Phase 2: Header Detail Pages (Week 2-3)

#### 2.1 InvoiceDetail.tsx Refactor
- [ ] Migrate to shared components
- [ ] Add `refs.links.contact` table with purpose column
- [ ] Add `refs.links.customer` display
- [ ] Add comments panel
- [ ] Add metadata panel (admin)
- [ ] Add flow diagram
- [ ] Test all JSONB fields

#### 2.2 OrderDetail.tsx Update
- [ ] Apply same pattern as Invoice
- [ ] Add quantity tracking (placed vs invoiced vs remaining)
- [ ] Add `refs.depends_on` display

#### 2.3 PurchaseDetail.tsx Update
- [ ] Apply same pattern
- [ ] Add vendor link display
- [ ] Add receiving status

#### 2.4 ProposalDetail.tsx Update
- [ ] Apply same pattern
- [ ] Add quote-specific fields
- [ ] Add conversion to order flow

#### 2.5 WorkOrderDetail.tsx Update
- [ ] Apply same pattern
- [ ] Add task/execution tracking
- [ ] Add resource allocation

#### 2.6 RequisitionDetail.tsx Update
- [ ] Apply same pattern
- [ ] Add approval workflow fields

#### 2.7 ProjectDetail.tsx Update
- [ ] Unique structure (not TransactionBaseModel)
- [ ] Add objective display
- [ ] Add tasks checklist
- [ ] Add logistics/budget

---

### Phase 3: Line Detail Pages (Week 4)

#### 3.1 Create BaseLineDetail Component
**File**: `src/apps/transactions/components/BaseLineDetail.tsx`

- [ ] Shared line item display
- [ ] Quantity object handling
- [ ] Cost/Price object display
- [ ] Physical dimensions

#### 3.2 Implement Line Detail Pages
- [ ] InvoiceLineDetail.tsx
- [ ] OrderLineDetail.tsx
- [ ] PurchaseLineDetail.tsx
- [ ] ProposalLineDetail.tsx
- [ ] WorkOrderLineDetail.tsx
- [ ] RequisitionLineDetail.tsx

---

### Phase 4: Integration & Testing (Week 5)

#### 4.1 API Integration
- [ ] Verify all JSONB fields returned from wcapi/get/
- [ ] Verify wcapi/save/ accepts nested structures
- [ ] Test partial updates (PATCH semantics)

#### 4.2 List Page Updates
- [ ] Update *List.tsx pages to show key JSONB data
- [ ] Add filters for refs.tags, metadata.priority

#### 4.3 End-to-End Testing
- [ ] Test create/edit/view modes
- [ ] Test inline (expandable) vs standalone detail
- [ ] Test role-based field visibility

---

## UI Component Specifications

### Field Label Styling Convention

| Field Type | Label Style | CSS Class | Example |
|------------|-------------|-----------|---------|
| **Mandatory** | Bold | `font-bold` | **Display Name** |
| **Locked/ReadOnly** | Italic | `italic` | *Invoice Number* |
| **Optional Editable** | Normal | (default) | Company |
| **Mandatory + Locked** | Bold + Italic | `font-bold italic` | ***ID*** |

### Primary Relationship Fields (from TransactionBaseModel)

The actual foreign key relationships are defined in `base_transaction_model.py`:

```python
customer_id = models.BigIntegerField(default=0, db_index=True)
manufacturer_id = models.BigIntegerField(default=0, db_index=True)
vendor_id = models.BigIntegerField(default=0, db_index=True)
parent_id = models.BigIntegerField(blank=True, null=True, db_index=True)
parent_type = models.CharField(max_length=20, choices=PARENT_TYPE_CHOICES)
```

The `refs.links.*` arrays contain **denormalized copies** for display convenience:
- `refs.links.customer` - snapshot of customer org
- `refs.links.vendor` - snapshot of vendor org  
- `refs.links.manufacturer` - snapshot of manufacturer org
- `refs.links.contact` - contacts associated with this transaction (with purpose)

**Important**: When saving, update the primary `customer_id`/`vendor_id`/`manufacturer_id` fields. The `refs.links.*` are refreshed by the backend.

### ContactPanel Component

Display `refs.links.contact` grouped by **purpose** as separate text blocks:

```tsx
interface ContactPanelProps {
  contacts: ContactDenorm[];
  isEditing?: boolean;
  onAdd?: (purpose: string) => void;
  onRemove?: (contactId: number) => void;
}

// Visual Layout:
// ┌─────────────────────────────────────────────────────────────┐
// │ Bill To                                                     │
// │ ─────────────────────────────────────────────────────────── │
// │ John Smith                                                  │
// │ Acme Corporation                                            │
// │ john@acme.com | 555-1234                                    │
// ├─────────────────────────────────────────────────────────────┤
// │ Ship To                                                     │
// │ ─────────────────────────────────────────────────────────── │
// │ Jane Doe                                                    │
// │ Acme Warehouse                                              │
// │ jane@acme.com | 555-5678                                    │
// ├─────────────────────────────────────────────────────────────┤
// │ Attention                                                   │
// │ ─────────────────────────────────────────────────────────── │
// │ Bob Wilson (Buyer)                                          │
// │ bob@acme.com | 555-9999                                     │
// └─────────────────────────────────────────────────────────────┘
```

Standard purposes: `billto`, `shipto`, `attention`, `approver`, `cc`, `notify`

### RefsLinksTable Component

```tsx
interface RefsLinksTableProps {
  links: TransactionRefs['links'];
  linkType: keyof TransactionRefs['links'];  // 'contact', 'customer', etc.
  columns: ColumnDef[];
  isEditing?: boolean;
  onAdd?: () => void;
  onRemove?: (id: number) => void;
}

// Usage:
<RefsLinksTable
  links={refs.links}
  linkType="contact"
  columns={[
    { key: 'id', label: 'ID' },
    { key: 'purpose', label: 'Purpose' },
    { key: 'display_name', label: 'Name' },
    { key: 'email', label: 'Email' },
    { key: 'phone', label: 'Phone' },
  ]}
/>
```

### ContactLinkCard Component

```tsx
interface ContactLinkCardProps {
  contact: ContactDenorm;
  purpose?: string;
  role?: string;
  onEdit?: () => void;
  onRemove?: () => void;
}

// Display:
// ┌─────────────────────────────────────────┐
// │ 👤 John Smith            [Edit] [Remove] │
// │    Purpose: Bill To                      │
// │    Role: Buyer                           │
// │    📧 john@example.com                   │
// │    📞 555-1234                           │
// └─────────────────────────────────────────┘
```

### CommentsPanel Component

```tsx
interface CommentsPanelProps {
  comments: TransactionComments;
  isEditing?: boolean;
  onChange?: (comments: TransactionComments) => void;
}

// Tabs: Public | Process | Partner | History
```

### FinancialsCard Component

```tsx
interface FinancialsCardProps {
  totals: TransactionTotals;
  cost?: HeaderCost;
  sell?: HeaderSell;
  finance?: TransactionFinance;
  showCost?: boolean;  // Admin only
}

// Display:
// ┌─────────────────────────────────────────┐
// │ Financials                              │
// │ ─────────────────────────────────────── │
// │ Subtotal:        $1,234.56              │
// │ Discount:          -$50.00              │
// │ Tax (8.25%):        $97.75              │
// │ Shipping:           $15.00              │
// │ ─────────────────────────────────────── │
// │ Total:           $1,297.31              │
// │ ─────────────────────────────────────── │
// │ [Admin] Cost:      $890.00              │
// │ [Admin] Margin:    $407.31 (31.4%)      │
// └─────────────────────────────────────────┘
```

---

## Tab Structure per Model

### Invoice/Order/Proposal (Sell-Side)

| Tab | Content |
|-----|---------|
| **Info** | Scalar fields (ida, status, dates, addresses) |
| **Contacts** | refs.links.contact table with purpose |
| **Customer** | refs.links.customer card + search |
| **Lines** | Line items table (embedded) |
| **Comments** | comments.public, process, notes |
| **Financial** | totals, cost, sell, finance |
| **Flow** | flow.source, flow.children diagram |
| **Actions** | actions panel |
| **Admin** | metadata, prefs.userdefined, refs.tags |

### Purchase/WorkOrder (Exec-Side)

| Tab | Content |
|-----|---------|
| **Info** | Scalar fields |
| **Vendor** | refs.links.vendor card + search |
| **Lines** | Line items with receiving |
| **Comments** | comments |
| **Financial** | Cost-focused totals |
| **Flow** | Source transaction links |
| **Admin** | metadata, prefs |

### Project

| Tab | Content |
|-----|---------|
| **Overview** | Name, objective.summary |
| **Tasks** | tasks.items checklist |
| **Resources** | logistics.resources, refs.links.contact |
| **Budget** | logistics.budget, cost tracking |
| **Timeline** | logistics.deadline, milestones |
| **Comments** | comments |
| **Admin** | metadata, data (payload) |

---

## Role-Based Access Control (RBAC)

### Overview

Components and data fields are protected by role-based access. The system enforces access at **two levels**:

1. **Frontend**: Components check user role before rendering
2. **Backend (WC3)**: API does NOT populate restricted fields if role unauthorized

This ensures sensitive data (cost, margin, metadata) is never sent to unauthorized users.

### Role Hierarchy

| Role | Code | Level | Description |
|------|------|-------|-------------|
| Public | `public` | 0 | Unauthenticated / Customer portal |
| User | `user` | 1 | Basic authenticated user |
| Sales | `sales` | 2 | Sales team member |
| Manager | `manager` | 3 | Department manager |
| Admin | `admin` | 4 | **Full access to all components** |
| Super | `super` | 5 | Developer tools (debug/raw JSON) |

> **Note**: `admin` role has access to ALL components and data. `super` is reserved for developer-level debugging tools only.

### Component Role Requirements

Each shared component has a minimum role requirement:

| Component | Min Role | Restricted Data |
|-----------|----------|-----------------|
| `FieldLabel` | `public` | None (display only) |
| `ContactPanel` | `user` | Contact details |
| `RefsLinksTable` | `user` | Link records |
| `CommentsPanel` | `user` | `process` tab requires `sales` |
| `ActionsCard` | `sales` | Action assignments |
| `FinancialsCard` | `sales` | `cost` section requires `manager` |
| `FlowDiagram` | `user` | Transaction lineage |
| `MetadataPanel` | `admin` | All system metadata |
| `JsonFieldEditor` | `admin` | Raw JSON access |

### Tab Role Requirements

| Tab | Min Role | Notes |
|-----|----------|-------|
| Summary/Info | `user` | Basic transaction info |
| Lines | `user` | Line items |
| Contacts | `user` | Associated contacts |
| Comments | `user` | `process`/`partner` tabs require `sales` |
| Financial | `sales` | Cost breakdown requires `manager` |
| Flow | `user` | Document lineage |
| Actions | `sales` | Task assignments |
| Metadata | `admin` | System fields |
| Refs | `admin` | Raw refs structure |
| Raw JSON | `admin` | Full record dump |

### Field-Level Role Restrictions

| Field Path | Min Role | Reason |
|------------|----------|--------|
| `totals.ex` | `user` | Sell price visible to all |
| `totals.cost` | `manager` | Cost data restricted |
| `totals.margin` | `manager` | Margin data restricted |
| `cost.*` | `manager` | All cost envelope |
| `sell.*` | `sales` | Pricing structure |
| `finance.*` | `manager` | Tax/financial details |
| `metadata.*` | `admin` | System metadata |
| `metadata.access` | `admin` | Permission assignments |
| `prefs.userdefined` | `admin` | Custom fields |
| `comments.process` | `sales` | Internal comments |
| `comments.partner` | `sales` | Vendor comments |
| `action.*` | `sales` | Action management |

### Implementation

#### Frontend: RoleGuard Component

```tsx
// src/components/auth/RoleGuard.tsx
interface RoleGuardProps {
  minRole: 'public' | 'user' | 'sales' | 'manager' | 'admin' | 'super';
  children: React.ReactNode;
  fallback?: React.ReactNode;
}

const ROLE_LEVELS = {
  public: 0,
  user: 1,
  sales: 2,
  manager: 3,
  admin: 4,
  super: 5,
};

export const RoleGuard: React.FC<RoleGuardProps> = ({ 
  minRole, 
  children, 
  fallback = null 
}) => {
  const { user } = useAuth();
  const userLevel = ROLE_LEVELS[user?.role ?? 'public'];
  const requiredLevel = ROLE_LEVELS[minRole];
  
  if (userLevel < requiredLevel) {
    return <>{fallback}</>;
  }
  
  return <>{children}</>;
};
```

#### Frontend: useRoleAccess Hook

```tsx
// src/hooks/useRoleAccess.ts
export const useRoleAccess = () => {
  const { user } = useAuth();
  const userLevel = ROLE_LEVELS[user?.role ?? 'public'];
  
  return {
    userRole: user?.role ?? 'public',
    userLevel,
    hasRole: (minRole: string) => userLevel >= ROLE_LEVELS[minRole],
    canViewCost: userLevel >= ROLE_LEVELS.manager,
    canViewAdmin: userLevel >= ROLE_LEVELS.admin,
    canEditActions: userLevel >= ROLE_LEVELS.sales,
  };
};
```

#### Backend: WC3 Field Filtering

WC3 must filter response data based on user role. Add to serializer or view:

```python
# apps/core/mixins/role_filter_mixin.py

ROLE_LEVELS = {
    'public': 0,
    'user': 1,
    'sales': 2,
    'manager': 3,
    'admin': 4,
    'super': 5,
}

# Fields restricted by minimum role
RESTRICTED_FIELDS = {
    'manager': ['cost', 'totals.cost', 'totals.margin', 'finance'],
    'sales': ['sell', 'action', 'comments.process', 'comments.partner'],
    'admin': ['metadata', 'prefs.userdefined'],
    'super': ['metadata.access'],
}

class RoleFilterMixin:
    """Filter response data based on user role"""
    
    def filter_by_role(self, data: dict, user_role: str) -> dict:
        user_level = ROLE_LEVELS.get(user_role, 0)
        
        for min_role, fields in RESTRICTED_FIELDS.items():
            if user_level < ROLE_LEVELS[min_role]:
                for field in fields:
                    self._remove_field(data, field)
        
        return data
    
    def _remove_field(self, data: dict, field_path: str):
        """Remove field by dot-notation path"""
        parts = field_path.split('.')
        obj = data
        for part in parts[:-1]:
            if part not in obj:
                return
            obj = obj[part]
        if parts[-1] in obj:
            del obj[parts[-1]]
```

#### Backend: Apply in ViewSet

```python
# apps/core/views/generic_view.py

class GenericModelViewSet(RoleFilterMixin, viewsets.ModelViewSet):
    
    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = self.get_serializer(instance)
        data = serializer.data
        
        # Filter based on user role
        user_role = getattr(request.user, 'role', 'public')
        filtered_data = self.filter_by_role(data, user_role)
        
        return Response(filtered_data)
```

### Component Usage with Role Guard

```tsx
// Example: FinancialsCard with role-based sections

const FinancialsCard: React.FC<FinancialsCardProps> = ({ totals, cost, sell }) => {
  const { canViewCost } = useRoleAccess();
  
  return (
    <div className="financials-card">
      {/* Always visible */}
      <TotalsSection totals={totals} />
      
      {/* Sales+ only */}
      <RoleGuard minRole="sales">
        <SellSection sell={sell} />
      </RoleGuard>
      
      {/* Manager+ only */}
      <RoleGuard minRole="manager">
        <CostSection cost={cost} />
        <MarginSection totals={totals} cost={cost} />
      </RoleGuard>
    </div>
  );
};
```

### Tab Visibility with Roles

```tsx
// TransactionDetailBase.tsx - filter tabs by role

const getVisibleTabs = (tabs: TransactionTab[], userRole: string): TransactionTab[] => {
  const userLevel = ROLE_LEVELS[userRole];
  return tabs.filter(tab => {
    const tabLevel = ROLE_LEVELS[tab.minRole ?? 'user'];
    return userLevel >= tabLevel;
  });
};
```

### Role Configuration per Component

Add `minRole` prop to all shared components:

```tsx
interface ComponentProps {
  // ... existing props
  minRole?: 'public' | 'user' | 'sales' | 'manager' | 'admin' | 'super';
}
```

Components self-guard when minRole is set:

```tsx
const MetadataPanel: React.FC<MetadataPanelProps> = ({ 
  metadata, 
  minRole = 'admin' 
}) => {
  const { hasRole } = useRoleAccess();
  
  if (!hasRole(minRole)) {
    return null; // Or placeholder
  }
  
  return (
    // ... component content
  );
};
```

### Testing Role Access

```tsx
// Test helper to mock roles
const renderWithRole = (ui: React.ReactElement, role: string) => {
  return render(
    <AuthProvider initialUser={{ role }}>
      {ui}
    </AuthProvider>
  );
};

// Test cases
it('hides cost section from sales user', () => {
  renderWithRole(<FinancialsCard {...props} />, 'sales');
  expect(screen.queryByText('Cost Breakdown')).not.toBeInTheDocument();
});

it('shows cost section to manager', () => {
  renderWithRole(<FinancialsCard {...props} />, 'manager');
  expect(screen.getByText('Cost Breakdown')).toBeInTheDocument();
});
```

---

## Implementation Checklist

### Phase 1: Shared Infrastructure
- [x] Create `src/apps/transactions/types/transactionTypes.ts`
- [x] Create `src/apps/transactions/components/FieldLabel.tsx`
- [x] Create `src/apps/transactions/components/ContactPanel.tsx`
- [x] Create `src/apps/transactions/components/RefsLinksTable.tsx`
- [x] Create `src/apps/transactions/components/CommentsPanel.tsx`
- [x] Create `src/apps/transactions/components/ActionsCard.tsx`
- [x] Create `src/apps/transactions/components/MetadataPanel.tsx`
- [x] Create `src/apps/transactions/components/FinancialsCard.tsx`
- [x] Create `src/apps/transactions/components/FlowDiagram.tsx`
- [x] Create `src/apps/transactions/components/JsonFieldEditor.tsx`
- [x] Create `src/apps/transactions/components/TransactionDetailBase.tsx`
- [x] Create `src/apps/transactions/components/index.ts`

### Phase 1.5: Role-Based Access Control
- [ ] Create `src/components/auth/RoleGuard.tsx`
- [ ] Create `src/hooks/useRoleAccess.ts`
- [ ] Add `minRole` prop to all shared components
- [ ] Update `TransactionDetailBase.tsx` with role-filtered tabs
- [ ] Create WC3 `RoleFilterMixin` in `apps/core/mixins/`
- [ ] Apply role filtering in `GenericModelViewSet`
- [ ] Add role tests for each component

### Phase 2: Header Detail Pages
- [x] Refactor `InvoiceDetail.tsx` → `InvoiceDetailNew.tsx`
- [ ] Refactor `OrderDetail.tsx`
- [ ] Update `PurchaseDetail.tsx`
- [ ] Update `ProposalDetail.tsx`
- [ ] Update `WorkOrderDetail.tsx`
- [ ] Update `RequisitionDetail.tsx`
- [ ] Update `ProjectDetail.tsx`

### Phase 3: Line Detail Pages
- [ ] Create `BaseLineDetail.tsx`
- [ ] Create `InvoiceLineDetail.tsx`
- [ ] Create `OrderLineDetail.tsx`
- [ ] Create `PurchaseLineDetail.tsx`
- [ ] Create `ProposalLineDetail.tsx`
- [ ] Create `WorkOrderLineDetail.tsx`
- [ ] Create `RequisitionLineDetail.tsx`

### Phase 4: Integration
- [ ] Verify API returns all JSONB fields
- [ ] Test save/update for nested structures
- [ ] Update list pages with key JSONB columns
- [ ] End-to-end testing

---

## Estimated Effort

| Phase | Description | Hours |
|-------|-------------|-------|
| 1.1 | TypeScript types | 4 |
| 1.2 | Shared components (10) | 20 |
| 1.3 | TransactionDetail base | 8 |
| 2.1-2.7 | Header detail pages (7) | 28 |
| 3.1 | BaseLineDetail | 6 |
| 3.2 | Line detail pages (6) | 18 |
| 4.x | Integration & testing | 16 |
| **Total** | | **100 hours** |

---

## API Requirements

### Required Endpoints (wcapi)

```
GET  /wcapi/get/?model_name=invoice&id={id}
POST /wcapi/save/
     body: { model_name: "invoice", record: {...} }
```

### Expected Response Structure

```json
{
  "id": 12345,
  "ida": "INV-2026-001",
  "status": "draft",
  "customer_id": 789,
  "total": 1297.31,
  "refs": {
    "links": {
      "contact": [
        {
          "id": 123,
          "purpose": "billto",
          "name_first": "John",
          "name_last": "Smith",
          "email": "john@example.com"
        }
      ],
      "customer": [{ "id": 789, "display_name": "Acme Corp" }]
    },
    "keywords": ["urgent"],
    "tags": ["Q1-2026"]
  },
  "metadata": {
    "history": {
      "created": { "dt": 1705248000000, "contact_id": 1 }
    }
  },
  "comments": {
    "public": "Thank you for your order!",
    "notes": []
  },
  "totals": {
    "subtotal": 1234.56,
    "tax": 97.75,
    "total": 1297.31
  }
}
```

---

## Notes

- InvoiceDetail.tsx already has partial implementation of `refs.links.contact` handling
- Use InvoiceDetail.tsx as reference for pattern, but refactor to shared components
- Admin-only fields should be wrapped in role-based guards
- Consider lazy-loading for metadata/admin tabs
- All JSONB fields should gracefully handle null/undefined

---

## Dependencies

- `src/apps/orgs/components/OrgDetail.tsx` - Pattern reference
- `src/components/auth/AdminGuard.tsx` - Role-based access
- `src/api/wcapi.ts` - API client
- `react-data-table-component` - Tables
- `react-hook-form` + `zod` - Form handling

# Transactions App

> Core transaction management module for CommerceExpert - handles all business documents including orders, invoices, proposals, purchases, work orders, and requisitions.

---

## 📁 Directory Structure

```
transactions/
├── components/           # Shared UI components for all transaction types
├── hooks/                # Custom React hooks
├── models/               # Transaction-specific implementations
│   ├── base/             # Base utilities
│   ├── common/           # Shared model utilities
│   ├── invoice/          # Invoice header & detail
│   ├── invoice_line/     # Invoice line items
│   ├── order/            # Sales Order header & detail
│   ├── order_line/       # Sales Order line items
│   ├── proposal/         # Proposal/Quote management
│   ├── proposal_line/    # Proposal line items
│   ├── purchase/         # Purchase Order header
│   ├── purchase_line/    # Purchase Order line items
│   ├── workorder/        # Work Order header
│   ├── workorder_line/   # Work Order line items
│   ├── requisition/      # Internal requisitions
│   ├── requisition_line/ # Requisition line items
│   ├── receipt/          # Receiving documents
│   ├── project/          # Project management
│   ├── inventory_adjustment/ # Inventory adjustments
│   └── linkage/          # Transaction linkages
├── services/             # Business logic services
├── types/                # TypeScript type definitions
├── ContactsDemo.tsx      # Demo component
└── DEMO.md               # Demo documentation
```

---

## 🏗️ Architecture

### Transaction Hierarchy

```
┌─────────────────────────────────────────────────────────────────┐
│                    TransactionBaseModel (wc3)                   │
├─────────────────────────────────────────────────────────────────┤
│  SALES SIDE              │  EXECUTION SIDE                      │
│  ─────────────           │  ───────────────                     │
│  • Proposal              │  • Purchase Order                    │
│  • Sales Order           │  • Work Order                        │
│  • Invoice               │  • Requisition                       │
│                          │  • Receipt                           │
├─────────────────────────────────────────────────────────────────┤
│  SUPPORTING              │                                      │
│  ───────────             │                                      │
│  • Project               │                                      │
│  • Inventory Adjustment  │                                      │
└─────────────────────────────────────────────────────────────────┘
```

### Sales vs Execution Transactions

| Aspect          | Sales (Order, Invoice, Proposal) | Execution (Purchase, WorkOrder) |
| --------------- | -------------------------------- | ------------------------------- |
| Primary Value   | `price.unit`                     | `cost.unit`                     |
| Customer/Vendor | Customer linked                  | Vendor linked                   |
| Flow Direction  | Outbound                         | Inbound                         |

---

## 🧩 Shared Components

Located in `components/`:

| Component                   | Purpose                                                           |
| --------------------------- | ----------------------------------------------------------------- |
| `TransactionDetailBase.tsx` | Base layout for all detail pages (tabs, toolbar, common sections) |
| `TransactionToolbar.tsx`    | Action buttons (save, cancel, print, actions)                     |
| `LinesCard.tsx`             | Editable line items grid                                          |
| `SummaryCard.tsx`           | Header summary display                                            |
| `FinancialsCard.tsx`        | Totals, tax, shipping breakdown                                   |
| `CommentsPanel.tsx`         | Public/process comments & notes                                   |
| `ContactPanel.tsx`          | Contacts, customers, vendors linked to transaction                |
| `RefsLinksTable.tsx`        | Generic refs.links display                                        |
| `ContactLinksTable.tsx`     | Contact-specific links table                                      |
| `MetadataPanel.tsx`         | Admin metadata (created, modified, health)                        |
| `JsonFieldEditor.tsx`       | Generic JSON field editor                                         |
| `PartySelector.tsx`         | Customer/Vendor/Contact selector                                  |
| `TransactionItemSearch.tsx` | Item search for adding lines                                      |
| `LineDetailsModal.tsx`      | Modal for editing individual line details                         |
| `SplitLineModal.tsx`        | Split line quantities                                             |
| `ActionsModal.tsx`          | Transaction actions modal                                         |
| `PrintPreviewModal.tsx`     | Print/PDF preview                                                 |
| `AttachmentsTab.tsx`        | File attachments                                                  |
| `DocumentsTab.tsx`          | Related documents                                                 |
| `ActivityLogTab.tsx`        | Audit trail                                                       |
| `QATab.tsx`                 | Quality assurance tab                                             |

---

## 📦 Types

Defined in `types/transactionTypes.ts`:

### Key Types

```typescript
// Transaction status values
type TransactionStatus =
  | "planned"
  | "released"
  | "in_progress"
  | "hold"
  | "complete"
  | "canceled"
  | "draft"
  | "pending"
  | "approved"
  | "rejected";

// Parent transaction types
type TransactionParentType =
  | "order"
  | "invoice"
  | "proposal"
  | "purchase"
  | "workorder"
  | "requisition"
  | "project";

// Contact purposes in refs.links.contact
type ContactPurpose =
  | "billto"
  | "shipto"
  | "attention"
  | "approver"
  | "cc"
  | "notify"
  | "buyer"
  | "seller";
```

### JSONB Field Structures

Matches wc3 mixin-based schema:

```typescript
interface TransactionRefsLinks {
  contact?: ContactDenorm[];
  customer?: OrgDenorm[];
  vendor?: OrgDenorm[];
  item?: ItemDenorm[];
  // ... other link types
}

interface Transaction {
  refs: {
    links: TransactionRefsLinks;
    keywords?: string[];
    tags?: string[];
    depends_on?: Record<string, number[]>;
  };
  metadata: { history: {...}, health: {...} };
  comments: { public: string, process: string, notes: [...] };
  // ... other fields
}
```

---

## ⚙️ Services

### `lineItemService.ts`

**Single Point of Authority** for transaction line management.

```typescript
import {
  LineItemService,
  isSalesTransaction,
  isExecTransaction,
} from "./services/lineItemService";

// Check transaction type
isSalesTransaction("order"); // true
isExecTransaction("purchase"); // true

// Line calculations include:
// - gross, discountAmount, extended
// - grossCost, discountCost, costExtended
// - margin, marginPc
```

**Key Functions:**

- Add/update/delete line items
- Calculate line totals with discounts
- Handle price vs cost based on transaction type
- Margin calculations

---

## 🔄 API Integration

Uses `wcapi` for backend communication:

```typescript
import { getRecord, saveRecord, saveTransactionWithLines, deleteRecord } from '../../../api/wcapi';

// Endpoints pattern
GET    /api/v1/{transaction_type}/{id}/
POST   /api/v1/{transaction_type}/
PATCH  /api/v1/{transaction_type}/{id}/
DELETE /api/v1/{transaction_type}/{id}/

// With lines (atomic save)
POST   /api/v1/{transaction_type}/{id}/save-with-lines/
```

---

## 📐 Model Structure

Each transaction model folder follows this pattern:

```
models/{transaction_type}/
├── index.ts              # Exports
├── {Transaction}.ts      # Type definitions
├── components/           # Model-specific components
├── hooks/                # Model-specific hooks
├── pages/                # Detail & list pages
│   ├── {Transaction}Detail.tsx
│   └── {Transaction}List.tsx
├── services/             # Model-specific business logic
├── types/                # Model-specific types
└── utils/                # Model-specific utilities
```

---

## 🚧 Development Status

See [README-TRANSACTION-DETAIL-PLAN.md](./README-TRANSACTION-DETAIL-PLAN.md) for detailed progress.

### Phase Summary

| Phase | Description                               | Status         |
| ----- | ----------------------------------------- | -------------- |
| 1     | Shared Infrastructure (components, types) | ✅ Complete    |
| 1.5   | Role-Based Access Control                 | 🚧 Next        |
| 2     | Header Detail Pages                       | 🚧 In Progress |
| 3     | Line Detail Pages                         | ❌ Pending     |

---

## 🎯 Usage Examples

### Creating a New Transaction Detail Page

```tsx
import { TransactionDetailBase } from "../components/TransactionDetailBase";
import type { Transaction } from "../types/transactionTypes";

export default function InvoiceDetail() {
  return (
    <TransactionDetailBase
      transactionType="invoice"
      apiEndpoint="invoices"
      title="Invoice"
      // ... additional props
    />
  );
}
```

### Using Line Item Service

```tsx
import {
  calculateLineTotal,
  isSalesTransaction,
} from "../services/lineItemService";

const line = {
  quantity: { ordered: 10 },
  price: { unit: 25.0 },
  discount: { pc: 10 },
};

const totals = calculateLineTotal(line, "order");
// { gross: 250, discountAmount: 25, extended: 225, ... }
```

---

## 📚 Related Documentation

- [Transaction Services](../../../readmes/topics/transaction-services.md) - Backend service architecture
- [Transaction Calculations](../../../readmes/topics/transaction-calculations.md) - Frontend calculation logic
- [WC3 ↔ R25 Alignment](../../../readmes/wc3_r25_alignment.md) - Model mapping between backend and frontend
- [API Integration](../../../readmes/03-api-integration.md) - General API patterns

---

## 🔗 Backend Reference

Corresponds to wc3 `apps/transactions/`:

- `models/base_transaction_model.py` - TransactionBaseModel
- `models/base_line_model.py` - TransactionLineBaseModel
- Common mixins in `common/models.py`

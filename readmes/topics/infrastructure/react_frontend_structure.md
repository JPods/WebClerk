# React Frontend Structure for Transaction Flow System

## Overview

This document outlines the recommended React component structure for the proposal → order → invoice → payment transaction flow system. The frontend should provide an intuitive workflow visualization and management interface.

## Technology Stack

- **React 18+** with hooks
- **TypeScript** for type safety
- **React Query** for data fetching and caching
- **React Router** for navigation
- **Material-UI or Tailwind CSS** for styling
- **React Flow or similar** for workflow visualization

## Component Architecture

### Core Structure

```
src/
├── components/
│   ├── transactions/
│   │   ├── flow/
│   │   ├── forms/
│   │   ├── views/
│   │   └── shared/
│   ├── common/
│   └── layout/
├── hooks/
├── services/
├── types/
└── utils/
```

### Transaction Flow Components

#### Flow Visualization (`components/transactions/flow/`)

**TransactionFlowDiagram.tsx**
```tsx
interface TransactionFlowDiagramProps {
  transactionId: string;
  transactionType: 'proposal' | 'order' | 'invoice';
  onNodeClick: (node: FlowNode) => void;
}

export const TransactionFlowDiagram: React.FC<TransactionFlowDiagramProps> = ({
  transactionId,
  transactionType,
  onNodeClick
}) => {
  // Visualize the flow: Proposal -> Order -> Invoice -> Payment
  // Show status of each stage
  // Allow clicking to navigate between stages
}
```

**FlowStatusIndicator.tsx**
```tsx
interface FlowStatusIndicatorProps {
  currentStage: TransactionStage;
  completedStages: TransactionStage[];
  onStageClick: (stage: TransactionStage) => void;
}

export const FlowStatusIndicator: React.FC<FlowStatusIndicatorProps> = ({
  currentStage,
  completedStages,
  onStageClick
}) => {
  // Horizontal status bar showing progress through stages
}
```

**TransferWizard.tsx**
```tsx
interface TransferWizardProps {
  sourceTransaction: Transaction;
  targetType: TransactionType;
  onComplete: (result: TransferResult) => void;
}

export const TransferWizard: React.FC<TransferWizardProps> = ({
  sourceTransaction,
  targetType,
  onComplete
}) => {
  // Step-by-step wizard for converting between stages
  // Validation, line selection, confirmation
}
```

#### Transaction Forms (`components/transactions/forms/`)

**ProposalForm.tsx**
```tsx
interface ProposalFormProps {
  initialData?: Partial<Proposal>;
  onSubmit: (data: ProposalFormData) => Promise<void>;
  mode: 'create' | 'edit';
}

export const ProposalForm: React.FC<ProposalFormProps> = ({
  initialData,
  onSubmit,
  mode
}) => {
  // Form for creating/editing proposals
  // Customer selection, line items, totals
}
```

**OrderForm.tsx**
```tsx
interface OrderFormProps {
  proposalId?: string; // For conversion from proposal
  initialData?: Partial<Order>;
  onSubmit: (data: OrderFormData) => Promise<void>;
}

export const OrderForm: React.FC<OrderFormProps> = ({
  proposalId,
  initialData,
  onSubmit
}) => {
  // Order creation form
  // Can pre-populate from proposal
}
```

**InvoiceForm.tsx**
```tsx
interface InvoiceFormProps {
  orderId?: string; // For conversion from order
  initialData?: Partial<Invoice>;
  onSubmit: (data: InvoiceFormData) => Promise<void>;
}

export const InvoiceForm: React.FC<InvoiceFormProps> = ({
  orderId,
  initialData,
  onSubmit
}) => {
  // Invoice creation with payment terms
}
```

**PaymentForm.tsx**
```tsx
interface PaymentFormProps {
  invoiceId?: string;
  initialData?: Partial<Payment>;
  onSubmit: (data: PaymentFormData) => Promise<void>;
}

export const PaymentForm: React.FC<PaymentFormProps> = ({
  invoiceId,
  initialData,
  onSubmit
}) => {
  // Payment processing form
  // Gateway integration, amount entry
}
```

#### Transaction Views (`components/transactions/views/`)

**TransactionList.tsx**
```tsx
interface TransactionListProps {
  type: TransactionType;
  filters: TransactionFilters;
  onTransactionClick: (transaction: Transaction) => void;
}

export const TransactionList: React.FC<TransactionListProps> = ({
  type,
  filters,
  onTransactionClick
}) => {
  // List view with filtering and sorting
  // Status badges, key metrics
}
```

**TransactionDetail.tsx**
```tsx
interface TransactionDetailProps {
  transactionId: string;
  type: TransactionType;
  onEdit: () => void;
  onTransfer: (targetType: TransactionType) => void;
}

export const TransactionDetail: React.FC<TransactionDetailProps> = ({
  transactionId,
  type,
  onEdit,
  onTransfer
}) => {
  // Detailed view with header, lines, totals
  // Action buttons for transfers
}
```

**TransactionLines.tsx**
```tsx
interface TransactionLinesProps {
  transactionId: string;
  type: TransactionType;
  editable: boolean;
  onLinesChange: (lines: TransactionLine[]) => void;
}

export const TransactionLines: React.FC<TransactionLinesProps> = ({
  transactionId,
  type,
  editable,
  onLinesChange
}) => {
  // Line items table/grid
  // Add/edit/delete lines
  // Quantity, price, totals calculation
}
```

#### Shared Components (`components/transactions/shared/`)

**TransactionHeader.tsx**
```tsx
interface TransactionHeaderProps {
  transaction: Transaction;
  showFlowStatus: boolean;
}

export const TransactionHeader: React.FC<TransactionHeaderProps> = ({
  transaction,
  showFlowStatus
}) => {
  // Header with title, status, customer, dates
}
```

**TransactionTotals.tsx**
```tsx
interface TransactionTotalsProps {
  transaction: Transaction;
  showCostBreakdown: boolean;
}

export const TransactionTotals: React.FC<TransactionTotalsProps> = ({
  transaction,
  showCostBreakdown
}) => {
  // Totals display with subtotals, tax, total
  // Optional cost breakdown for internal use
}
```

**LineItemEditor.tsx**
```tsx
interface LineItemEditorProps {
  line: TransactionLine;
  transactionType: TransactionType;
  onSave: (line: TransactionLine) => void;
  onCancel: () => void;
}

export const LineItemEditor: React.FC<LineItemEditorProps> = ({
  line,
  transactionType,
  onSave,
  onCancel
}) => {
  // Modal/form for editing line items
  // Item selection, quantity, pricing
}
```

## Custom Hooks

### Data Fetching Hooks (`hooks/`)

**useTransactions.ts**
```typescript
export const useTransactions = (type: TransactionType, filters: TransactionFilters) => {
  return useQuery({
    queryKey: ['transactions', type, filters],
    queryFn: () => api.getTransactions(type, filters)
  });
};

export const useTransaction = (id: string, type: TransactionType) => {
  return useQuery({
    queryKey: ['transaction', type, id],
    queryFn: () => api.getTransaction(type, id)
  });
};

export const useTransactionLines = (transactionId: string, type: TransactionType) => {
  return useQuery({
    queryKey: ['transaction-lines', type, transactionId],
    queryFn: () => api.getTransactionLines(type, transactionId)
  });
};
```

**useTransactionMutations.ts**
```typescript
export const useCreateTransaction = (type: TransactionType) => {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (data: TransactionFormData) => api.createTransaction(type, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['transactions', type] });
    }
  });
};

export const useTransferTransaction = () => {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (params: TransferParams) => api.transferTransaction(params),
    onSuccess: (result) => {
      // Invalidate related queries
      queryClient.invalidateQueries({ queryKey: ['transactions'] });
    }
  });
};
```

### Business Logic Hooks

**useTransactionValidation.ts**
```typescript
export const useTransactionValidation = () => {
  return useMutation({
    mutationFn: (params: ValidationParams) => api.validateTransfer(params)
  });
};
```

**useInventoryManagement.ts**
```typescript
export const useReserveInventory = () => {
  return useMutation({
    mutationFn: (orderId: string) => api.reserveInventory(orderId)
  });
};
```

## API Service Layer

### API Client (`services/api.ts`)

```typescript
class TransactionAPI {
  // Transaction CRUD
  async getTransactions(type: TransactionType, filters: TransactionFilters): Promise<Transaction[]> {
    // GET /api/tx/{type}/
  }

  async getTransaction(type: TransactionType, id: string): Promise<Transaction> {
    // GET /api/tx/{type}/{id}/
  }

  async createTransaction(type: TransactionType, data: TransactionFormData): Promise<Transaction> {
    // POST /api/tx/{type}/
  }

  async updateTransaction(type: TransactionType, id: string, data: Partial<Transaction>): Promise<Transaction> {
    // PATCH /api/tx/{type}/{id}/
  }

  // Transfers
  async validateTransfer(params: ValidationParams): Promise<ValidationResult> {
    // POST /api/tx/transfers/validate/
  }

  async executeTransfer(params: TransferParams): Promise<TransferResult> {
    // POST /api/tx/transfers/execute/
  }

  // Payments
  async applyPayment(params: PaymentApplicationParams): Promise<PaymentApplicationResult> {
    // POST /api/tx/payments/apply/
  }

  // Inventory
  async reserveInventory(orderId: string): Promise<InventoryReservationResult> {
    // POST /api/tx/inventory/reserve/
  }
}
```

## Type Definitions

### Core Types (`types/transactions.ts`)

```typescript
export type TransactionType = 'proposal' | 'order' | 'purchase' | 'invoice' | 'payment';

export type TransactionStatus =
  | 'planned' | 'released' | 'in_progress' | 'complete' | 'canceled'
  | 'draft' | 'sent' | 'accepted' | 'paid' | 'overdue';

export interface Transaction {
  id: string;
  status: TransactionStatus;
  customer_id: number;
  vendor_id?: number;
  cost?: any;
  sell?: any;
  finance?: any;
  flow?: any;
  source?: any;
  action?: any;
  dt_created: string;
  dt_modified: string;
  version: number;
}

export interface TransactionLine {
  id: string;
  item: any;
  quantity: any;
  price?: any;
  cost?: any;
  tax?: any;
  physical?: any;
}

export interface TransferResult {
  success: boolean;
  target_id?: string;
  source_id: string;
  lines_transferred: number;
  line_mapping: Record<string, string>;
  errors?: string[];
}
```

## Routing Structure

### App Router Configuration

```tsx
// App.tsx
import { BrowserRouter, Routes, Route } from 'react-router-dom';

function App() {
  return (
    <BrowserRouter>
      <Routes>
        {/* Transaction routes */}
        <Route path="/transactions" element={<TransactionLayout />}>
          <Route path="proposals" element={<ProposalList />} />
          <Route path="proposals/:id" element={<ProposalDetail />} />
          <Route path="proposals/new" element={<ProposalForm />} />

          <Route path="orders" element={<OrderList />} />
          <Route path="orders/:id" element={<OrderDetail />} />
          <Route path="orders/new" element={<OrderForm />} />

          <Route path="invoices" element={<InvoiceList />} />
          <Route path="invoices/:id" element={<InvoiceDetail />} />

          <Route path="payments" element={<PaymentList />} />
          <Route path="payments/:id" element={<PaymentDetail />} />
        </Route>

        {/* Transfer wizard */}
        <Route path="/transfer/:sourceType/:sourceId/:targetType" element={<TransferWizard />} />
      </Routes>
    </BrowserRouter>
  );
}
```

## State Management

### Global State (Context + Reducer)

```tsx
// contexts/TransactionContext.tsx
interface TransactionContextType {
  currentTransaction: Transaction | null;
  flowHistory: Transaction[];
  actions: {
    setCurrentTransaction: (transaction: Transaction) => void;
    addToFlowHistory: (transaction: Transaction) => void;
    clearFlowHistory: () => void;
  };
}

export const TransactionProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  // Context implementation
};
```

## Styling Approach

### CSS Framework Choice

**Recommendation: Tailwind CSS**
- Utility-first approach fits component architecture
- Responsive design utilities
- Dark mode support
- Customizable design system

### Component Styling

```tsx
// TransactionCard.tsx
export const TransactionCard: React.FC<TransactionCardProps> = ({ transaction }) => {
  return (
    <div className="bg-white rounded-lg shadow-md p-6 hover:shadow-lg transition-shadow">
      <div className="flex justify-between items-start mb-4">
        <h3 className="text-lg font-semibold text-gray-900">
          {transaction.title || `Transaction #${transaction.id}`}
        </h3>
        <StatusBadge status={transaction.status} />
      </div>

      <div className="grid grid-cols-2 gap-4 text-sm text-gray-600">
        <div>Customer: {transaction.customer_id}</div>
        <div>Total: ${transaction.totals?.total || 0}</div>
        <div>Created: {formatDate(transaction.dt_created)}</div>
        <div>Modified: {formatDate(transaction.dt_modified)}</div>
      </div>
    </div>
  );
};
```

## Testing Strategy

### Component Testing

```tsx
// TransactionForm.test.tsx
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { TransactionForm } from './TransactionForm';

test('submits form with valid data', async () => {
  const mockOnSubmit = jest.fn();
  render(<TransactionForm onSubmit={mockOnSubmit} />);

  fireEvent.change(screen.getByLabelText(/customer/i), {
    target: { value: '123' }
  });

  fireEvent.click(screen.getByRole('button', { name: /submit/i }));

  await waitFor(() => {
    expect(mockOnSubmit).toHaveBeenCalledWith(
      expect.objectContaining({ customer_id: 123 })
    );
  });
});
```

### Integration Testing

- Test complete transfer workflows
- Test form submissions with API mocking
- Test error handling and validation

## Performance Considerations

### Optimization Techniques

1. **React Query Caching**: Cache transaction data with appropriate stale times
2. **Virtual Scrolling**: For large transaction lists
3. **Lazy Loading**: Load transaction lines on demand
4. **Memoization**: Memoize expensive calculations
5. **Bundle Splitting**: Code split by route/transaction type

### Data Fetching Strategy

```tsx
// Prefetch related data
const prefetchTransactionLines = (transactionId: string) => {
  queryClient.prefetchQuery({
    queryKey: ['transaction-lines', transactionId],
    queryFn: () => api.getTransactionLines(transactionId),
    staleTime: 5 * 60 * 1000 // 5 minutes
  });
};
```

## Accessibility

### ARIA Implementation

```tsx
// Accessible form
<FormField
  label="Customer"
  htmlFor="customer-select"
  error={errors.customer_id}
  required
>
  <select
    id="customer-select"
    aria-describedby={errors.customer_id ? "customer-error" : undefined}
    aria-invalid={!!errors.customer_id}
  >
    {/* options */}
  </select>
</FormField>
```

### Keyboard Navigation

- Tab order through form fields
- Keyboard shortcuts for common actions
- Focus management in modals

## Mobile Responsiveness

### Responsive Design

```tsx
// Responsive transaction list
<div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
  {transactions.map(transaction => (
    <TransactionCard key={transaction.id} transaction={transaction} />
  ))}
</div>
```

### Touch Interactions

- Swipe gestures for actions
- Touch-friendly buttons
- Mobile-optimized forms

## Conclusion

This React structure provides a scalable, maintainable frontend for the transaction flow system. The component architecture supports the complex workflow requirements while maintaining clean separation of concerns. The use of modern React patterns (hooks, context, TypeScript) ensures type safety and good developer experience.

Key benefits:
- **Modular**: Easy to maintain and extend
- **Type-safe**: TypeScript prevents runtime errors
- **Performant**: Optimized data fetching and rendering
- **Accessible**: WCAG compliant components
- **Responsive**: Works on all device sizes
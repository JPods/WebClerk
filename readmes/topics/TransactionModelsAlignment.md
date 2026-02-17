# Transaction Models Alignment to Proposal Advanced Behavior

This document outlines the comprehensive alignment of `order`, `invoice`, and `purchase` models to match the advanced behavior implemented in the `proposal` model. The alignment focuses on audit trail integration, schema enhancements with financial structures, and status workflow management.

## Investigation Findings

### Proposal Model Advanced Features

The `proposal` model serves as the reference implementation with the following advanced behaviors:

- **Audit Trail Integration**: Status change history tracking with user and timestamp information
- **Schema Enhancements**: Comprehensive financial structures including `cost`, `sell`, `finance`, `flow`, `source`, and `action` JSON fields
- **Status Workflow Management**: Configurable status transitions with validation rules and UI components

### Comparative Analysis

| Feature | Proposal | Sales Order | Invoice | Purchase Order |
|---------|----------|-------------|---------|----------------|
| Audit Trail | ✅ Mock implementation | ✅ Mock implementation | ✅ Mock implementation | ✅ Mock implementation |
| Financial Structures | ✅ Full (cost, sell, finance, flow, source, action) | ✅ Full alignment | ❌ Base schema only | ✅ Partial (finance, flow, source, action) |
| Status Workflow | ✅ Complete (planned → sent → accepted/rejected/cancelled) | ✅ Complete (draft → confirmed → shipped → delivered/cancelled) | ✅ Complete (draft → sent → paid/overdue/cancelled) | ✅ Complete (draft → approved/rejected → received → closed) |
| Schema Validation | ✅ Advanced cross-field validation | ✅ Advanced validation | ✅ Base + invoice-specific | ✅ Base + PO-specific |
| UI Components | ✅ Status visualization with history | ✅ Status visualization | ✅ Status visualization | ✅ Status visualization |

## Implemented Features

### 1. Audit Trail Integration

All transaction models now include audit trail functionality through dedicated hooks:

- **Status History Tracking**: Each model maintains a history of status changes with timestamps and user information
- **Mock Implementation**: Current implementation uses mock data; backend integration planned for future release
- **UI Integration**: Status components display history when `showHistory={true}` prop is enabled

**Example Implementation:**

```typescript
const { getStatusHistory } = useProposalStatus(currentStatus);
// Returns: [{ status: 'planned', timestamp: Date, user: 'System' }, ...]
```aaa

### 2. Schema Enhancements with Financial Structures

#### Sales Order Model
- **Full Alignment**: Includes all financial JSON fields (`cost`, `sell`, `finance`, `flow`, `source`, `action`)
- **Enhanced Validation**: Cross-field validation for customer/vendor separation
- **Financial Summary**: `total`, `tax`, `discount`, `subtotal` fields with validation

#### Purchase Order Model
- **Partial Alignment**: Includes `finance`, `flow`, `source`, `action` fields adapted from proposal
- **Cost-Focused Pricing**: Price schema emphasizes cost over sell pricing
- **Approval Workflow**: Status-based validation requiring `approval_date` when status is 'approved'

#### Invoice Model
- **Base Schema Extension**: Uses `baseTransactionSchema` and `baseLineItemSchema`
- **Invoice-Specific Fields**: `invoice_no`, `due_date`, `payment_terms`, balance calculations
- **Business Rules**: Due date validation, balance calculation verification

### 3. Status Workflow Management

All models implement comprehensive status workflows with:

- **Transition Validation**: Only valid status transitions are allowed
- **UI Visualization**: Workflow progression display with current status highlighting
- **Confirmation Requirements**: Critical transitions require user confirmation
- **Final State Handling**: Certain statuses (accepted, delivered, cancelled) are terminal

**Status Transition Example (Proposal):**

```aaa
planned → sent → accepted (final)
         → rejected → sent (resend)
         → cancelled (final)
```aaa

## Modified and Created Files

### Schema Files
- `src/apps/transactions/models/order/utils/orderSchema.ts` - Enhanced with financial structures
- `src/apps/transactions/models/purchase/utils/purchaseOrderSchema.ts` - Added financial fields and approval validation
- `src/apps/transactions/models/invoice/utils/invoiceSchema.ts` - Extended base schema with invoice-specific rules

### Hook Files
- `src/apps/transactions/models/order/hooks/useOrderStatus.ts` - Status workflow implementation
- `src/apps/transactions/models/invoice/hooks/useInvoiceStatus.ts` - Status workflow implementation
- `src/apps/transactions/models/purchase/hooks/usePurchaseStatus.ts` - Status workflow implementation

### Component Files
- `src/apps/transactions/models/order/components/OrderStatus.tsx` - Status management UI
- `src/apps/transactions/models/invoice/components/InvoiceStatus.tsx` - Status management UI
- `src/apps/transactions/models/purchase/components/PurchaseStatus.tsx` - Status management UI

### Type Files
- Updated type definitions in respective `types/` directories to support new financial fields
- Added status transition and configuration interfaces

## Usage Examples

### Status Workflow Usage
```typescript
import { useOrderStatus } from '../hooks/useOrderStatus';

const MyComponent = () => {
  const { currentStatus, getAvailableTransitions, transitionTo } = useOrderStatus('draft');

  const handleStatusChange = (newStatus) => {
    if (transitionTo(newStatus)) {
      // Status changed successfully
    }
  };

  return (
    <OrderStatus
      currentStatus={currentStatus}
      onStatusChange={handleStatusChange}
      showHistory={true}
    />
  );
};
```aaa

### Schema Validation Example
```typescript
import { salesOrderSchema } from '../utils/salesOrderSchema';

const validateOrder = (data) => {
  try {
    const validated = salesOrderSchema.parse(data);
    // Data is valid and includes financial structures
    return { success: true, data: validated };
  } catch (error) {
    return { success: false, errors: error.errors };
  }
};
```aaa

### Financial Structure Usage
```typescript
const orderData = {
  id_customer: 123,
  total: 1000,
  tax: 80,
  discount: 50,
  // Financial structures from proposal alignment
  cost: { material: 600, labor: 200 },
  sell: { base_price: 1000, markup: 150 },
  finance: { payment_terms: 'net30', credit_limit: 5000 },
  flow: { approval_required: true, budget_code: 'DEPT001' },
  source: { lead_source: 'website', campaign: 'Q4_Promo' },
  action: { next_steps: ['send_quote', 'schedule_followup'] }
};
```aaa

## Business Rules

### Cross-Field Validation
- **Entity Separation**: Customer and vendor cannot be the same entity
- **Date Logic**: Due dates must be after invoice/order dates
- **Financial Integrity**: Discounts cannot exceed extended prices
- **Balance Verification**: Invoice balance must equal total minus paid amount

### Status-Based Rules
- **Approval Requirements**: Purchase orders require approval date when status is 'approved'
- **Final States**: Certain statuses prevent further transitions
- **Transition Permissions**: Only defined transitions are allowed

### Financial Rules
- **Margin Calculations**: Automatic calculation of profit margins
- **Tax Application**: Proper tax rate validation and application
- **Discount Limits**: Business rule enforcement on discount amounts

## Remaining Unimplemented Features

### 1. Backend Audit Trail Integration
- **Current State**: Mock data implementation
- **Required**: Real backend API integration for status change history
- **Impact**: Full audit compliance and historical tracking

### 2. Advanced Financial Calculations
- **Missing**: Automatic calculation of complex financial metrics
- **Required**: Integration with accounting engine for real-time financial updates
- **Models Affected**: All transaction models

### 3. Workflow Automation
- **Current State**: Manual status transitions
- **Required**: Automated transitions based on business rules (e.g., auto-overdue for invoices)
- **Impact**: Reduced manual intervention and improved efficiency

### 4. Integration with Accounting Module
- **Missing**: Direct integration with GL accounts and journal entries
- **Required**: Automatic posting of financial transactions
- **Models Affected**: Invoice and sales order models primarily

### 5. Document Generation
- **Partial**: PDF generation for proposals
- **Required**: Consistent document generation across all models
- **Impact**: Standardized business document output

### 6. Notification System
- **Missing**: Status change notifications and alerts
- **Required**: Email/SMS notifications for status transitions
- **Models Affected**: All transaction models

## Future Development Roadmap

1. **Phase 1**: Backend audit trail implementation
2. **Phase 2**: Accounting integration and automated postings
3. **Phase 3**: Workflow automation and notifications
4. **Phase 4**: Advanced reporting and analytics
5. **Phase 5**: Multi-company and multi-currency support

This alignment provides a solid foundation for consistent transaction processing across all models while maintaining model-specific requirements and business logic.

# Transaction Flow System Plan: Proposal → Order → Invoice → Payment

## Overview

This document outlines the plan for implementing a comprehensive transaction flow system in webClerk3, salvaging practical logic from WebClerk2. The system manages the lifecycle of commercial transactions from initial proposals through fulfillment and payment.

### Core Flow

```aaa
Proposal → Order → Purchase → Invoice → Payment
     ↓           ↓           ↓           ↓           ↓
  Estimate   Confirmed   Procurement   Billing   Settlement
```

### Key Features

- **Inventory Management**: Quantities tracked across POs, Orders, and removed from Item records upon invoicing and added to Item records upon purchase receipts
- **Lineage Tracking**: Each transaction links to its predecessors via metadata and refs
- **Totals Calculation**: Automatic computation of sell/cost/totals from lines
- **Status Management**: Workflow states with business rules
- **Payment Processing**: Gateway integration with reconciliation
- **Commission Handling**: Removed to JSON objects (not implemented at this time)

## Current State Analysis

### Existing Models

All core models are already implemented in `apps/transactions/models/`:

- `Proposal`: Initial estimates/quotes
- `Order`: Confirmed customer orders
- `Purchase`: Procurement orders to vendors
- `Invoice`: Billing documents
- `Payment`: Payment records with gateway integration

All inherit from `TransactionBaseModel` providing:

- Common fields: status, customer_id, vendor_id, etc.
- JSON fields: cost, sell, finance, flow, source, action
- Status choices: planned → released → in_progress → complete/canceled

### Existing Services

Key transfer services already exist in `apps/transactions/services/`:

- `proposal_to_order.py`: Converts proposals to orders
- `order_to_invoice.py`: Converts orders to invoices
- `flow.py`: Core transfer utilities and inventory receiving
- `*_totals.py`: Automatic totals computation

### Inventory Integration

Items managed via `apps/products/models/`:

- `Item`: Base product catalog
- `InventoryLayer`: Warehouse-specific stock tracking
- `InventoryReservation`: Temporary holds

## Implementation Plan

### Phase 1: Core Flow Enhancement

#### 1.1 Complete Transfer Services

**Current Status**: Basic transfer services exist but may need enhancement.

**Enhancements Needed**:

- Add purchase creation from orders
- Estimate taxes in proposal and order
- Enhance invoice creation with tax calculations
- Add payment application logic, keep an estimate of balance due in the order for invoices and payments related to that order
- Implement inventory quantity updates on transfers

**Key Functions**:

```python
# apps/transactions/services/order_to_purchase.py
def transfer_order_to_purchase(order: Order) -> Purchase:

    # Create purchase from order lines requiring procurement

# apps/transactions/services/invoice_to_payment.py
def apply_payment_to_invoice(invoice: Invoice, payment: Payment):

    # Update invoice balance and payment status
```

#### 1.2 Inventory Management Integration

**Current Status**: Basic receiving exists in `flow.py`.

**Enhancements Needed**:

- Update item quantities on order confirmation
- Reserve inventory on order release
- Reduce available stock on invoicing
- Handle backorders and partial shipments

**Key Functions**:

```python
# apps/transactions/services/inventory_flow.py
def reserve_inventory_for_order(order: Order):

    # Create inventory reservations

def release_inventory_on_invoice(invoice: Invoice):

    # Reduce available quantities
```

### Phase 2: API and Views

#### 2.1 Transaction CRUD APIs

**Current Status**: Basic universal API coverage.

**Implementation**:

- Dedicated views for each transaction type
- Line management endpoints
- Bulk operations for transfers

**URLs Structure**:

```aaa
tx/
├── proposals/           # List/Create
├── proposals/{id}/      # Detail/Update
├── proposals/{id}/lines/ # Line management
├── orders/              # Orders
├── purchases/           # Purchases
├── invoices/
├── payments/
└── transfers/           # Bulk transfer operations
```

#### 2.2 Transfer APIs

**Endpoints**:

- `POST /tx/proposals/{id}/convert-to-order/`
- `POST /tx/orders/{id}/convert-to-invoice/`
- `POST /tx/orders/{id}/create-purchase-order/`
- `POST /tx/invoices/{id}/apply-payment/`

### Phase 3: Business Logic Services

#### 3.1 Validation Services

**Functions**:

```python
# apps/transactions/services/validation.py
def validate_proposal_for_conversion(proposal: Proposal) -> ValidationResult:

    # Check line completeness, pricing, etc.

def validate_order_for_invoicing(order: Order) -> ValidationResult:

    # Check fulfillment status, shipping, etc.
```

#### 3.2 Totals and Calculations

**Current Status**: Basic totals services exist.

**Enhancements**:

- Tax calculations
- Discount application
- Margin analysis
- Currency conversion

#### 3.3 Notification Services

**Functions**:

```python
# apps/transactions/services/notifications.py
def notify_order_confirmed(order: Order):

    # Email customer, update CRM

def notify_invoice_overdue(invoice: Invoice):

    # Send reminders, update collections
```

### Phase 4: Frontend Integration

#### 4.1 React Components Structure

**Recommended Structure**:

```aaa
src/components/transactions/
├── ProposalForm/
├── OrderDetail/
├── InvoiceViewer/
├── PaymentProcessor/
└── TransactionFlow/
    ├── FlowDiagram/
    ├── StatusTracker/
    └── TransferButtons/
```

#### 4.2 Key Features

- **Flow Visualization**: Timeline showing proposal → order → invoice → payment
- **Status Management**: Workflow state changes with validation
- **Line Item Editing**: Inline editing of quantities, prices
- **Transfer Wizards**: Guided conversion between stages
- **Payment Integration**: Stripe/PayPal gateway UI

#### 4.3 State Management

**Redux/Slice Structure**:

```javascript
// src/store/transactions/
├── proposalSlice.js
├── orderSlice.js
├── invoiceSlice.js
├── paymentSlice.js
└── flowSlice.js
```

### Phase 5: Testing and Validation

#### 5.1 Unit Tests

**Coverage Areas**:

- Model validation
- Transfer logic
- Totals calculation
- Inventory updates

#### 5.2 Integration Tests

**Scenarios**:

- Complete flow: proposal → order → invoice → payment
- Inventory tracking through flow
- Error handling and rollback

## Data Flow Details

### Proposal Creation

1. Create `Proposal` with lines
2. Calculate totals via `proposal_totals.py`
3. Store in `proposals` table

### Order Conversion

1. Validate proposal completeness
2. Create `Order` via `transfer_proposal_to_order`
3. Copy lines with quantity conversion
4. Reserve inventory if applicable
5. Update proposal status to "converted"

### Purchase Creation

1. Identify order lines requiring procurement
2. Create `Purchase` via `transfer_order_to_purchase`
3. Link to vendor items
4. Track expected delivery dates

### Invoice Generation

1. Validate order fulfillment
2. Create `Invoice` via `transfer_order_to_invoice`
3. Calculate taxes and totals
4. Update order line invoiced quantities

### Payment Processing

1. Create `Payment` record
2. Process via gateway (Stripe/PayPal)
3. Update invoice balance
4. Reconcile payment

### Inventory Updates

- **Order Confirmation**: Reserve quantities
- **PO Receipt**: Add to inventory layers
- **Invoicing**: Reduce available stock
- **Returns**: Restore quantities

## Configuration and Settings

### Status Workflows

**Proposal Statuses**:

- planned
- sent
- accepted
- converted
- canceled

**Order Statuses**:

- confirmed
- released
- in_progress
- fulfilled
- canceled

**Invoice Statuses**:

- draft
- sent
- paid
- overdue
- canceled

### Business Rules

- Proposals can only convert to orders when accepted
- Orders can only invoice when fulfilled
- Payments can only apply to sent invoices
- Inventory reductions only on invoice creation

## Migration from WebClerk2

### Salvaged Logic

**From WebClerk2** (assumed based on current implementation):

- Transfer utilities in `flow.py`
- Totals calculation patterns
- Status workflow management
- Basic inventory receiving

**Not Salvaged**:

- Commission calculations (removed to JSON objects)
- Legacy workflow states
- Deprecated field mappings

## Future Enhancements

### Phase 6: Advanced Features

- **Recurring Transactions**: Subscription billing
- **Multi-currency**: Exchange rate handling
- **Approval Workflows**: Multi-step approvals
- **Document Generation**: PDF invoice creation
- **Integration APIs**: ERP system connections
- **Analytics**: Transaction reporting and KPIs

### Performance Optimizations

- **Caching**: Totals and status caching
- **Bulk Operations**: Mass transfers and updates
- **Async Processing**: Background job queues
- **Database Indexing**: Optimized queries

## Implementation Timeline

### Week 1-2: Core Services

- Complete transfer services
- Enhance inventory integration
- Add validation logic

### Week 3-4: API Layer

- Implement CRUD views
- Add transfer endpoints
- Create serializers

### Week 5-6: Frontend

- Build React components
- Implement flow visualization
- Add payment integration

### Week 7-8: Testing & Deployment

- Comprehensive testing
- Performance optimization
- Production deployment

## Dependencies

### External Libraries

- Django REST Framework (for APIs)
- django-filter (for query filtering)
- Stripe/PayPal SDKs (for payments)
- React Query (for frontend data fetching)

### Internal Dependencies

- `common.BaseModel` (for optimistic concurrency)
- `products.Item` (for inventory)
- `accounts.PaymentMethod` (for payment types)

## Risk Assessment

### Technical Risks

- **Inventory Accuracy**: Critical for business operations
- **Payment Security**: PCI compliance requirements
- **Performance**: Large transaction volumes

### Mitigation Strategies

- Comprehensive testing of inventory flows
- Gateway security audits
- Database performance monitoring
- Rollback capabilities for failed transfers

## Conclusion

This plan provides a comprehensive roadmap for implementing a robust transaction flow system. The existing codebase provides a solid foundation, with the main work focusing on completing the transfer services, enhancing inventory integration, and building the API and frontend layers.

The system will support the complete commercial lifecycle while maintaining data integrity and providing excellent user experience through modern React interfaces.

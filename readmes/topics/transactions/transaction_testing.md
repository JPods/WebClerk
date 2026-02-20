# Transaction Testing Guide

This guide covers testing procedures for the main transaction types: Proposals, Orders, Invoices, and Purchases.

## Overview

Transactions are handled through:

- **Backend**: Django models in `apps/transactions/models/`
- **Frontend**: React components in `../React2025/src/pages/transactions/`
- **API**: WCAPI endpoints for CRUD operations

## Prerequisites

1. **Backend Setup**:

   ```bash
   cd /Users/williamjames/Documents/CommerceExpert/webClerk3
   pip install -r requirements.txt
   python manage.py migrate
   python manage.py runserver
   ```

2. **Frontend Setup**:

   ```bash
   cd ../React2025
   npm install
   cp .env.example .env
   npm run dev
   ```

3. **Database**: Ensure test data exists or create sample records

## Testing Procedures

### 1. Proposal Testing

**Model**: `apps/transactions/models/proposal.py`
**Frontend**: `../React2025/src/pages/transactions/ProposalDetailPage.tsx`

**Test Steps**:

1. Navigate to Proposals list page
2. Create new proposal:
   - Fill customer info, items, pricing
   - Save and verify persistence
3. Edit existing proposal:
   - Modify quantities/prices
   - Check totals update
4. Test status changes (planned → released → complete)
5. Verify line items and totals calculation

**API Testing**:

```bash
# List proposals
GET /api/wcapi/?model_name=proposal

# Create proposal
POST /api/wcapi/save/
{
  "model_name": "proposal",
  "data": { ... }
}
```

### 2. Order Testing

**Model**: `apps/transactions/models/order.py`
**Frontend**: `../React2025/src/pages/transactions/OrderDetailPage.tsx`

**Test Steps**:

1. Access Orders page
2. Create from proposal or directly:
   - Customer selection
   - Item addition with pricing
   - Address information
3. Test order conversion from proposal
4. Verify inventory reservations
5. Check order status workflow
6. Test totals and line item calculations

**Key Features to Test**:

- Order number generation
- Customer linking
- Item availability checks
- Shipping address validation

### 3. Invoice Testing

**Model**: `apps/transactions/models/invoice.py`
**Frontend**: `../React2025/src/pages/transactions/InvoiceDetailPage.tsx`

**Test Steps**:

1. Navigate to Invoices list
2. Create invoice from order:
   - Select order
   - Review line items
   - Set billing/shipping addresses
3. Test tax calculation (currently shows $0.00)
4. Verify totals table:
   - Lines count
   - Amount, tax, freight, total
5. Test PDF generation/print
6. Check customer and contact linking

**Tax Service Integration**:

- Tax service is available but not yet integrated into invoice totals
- Manual testing via `calculate_transaction_tax()` function
- See `readmes/tax_service.md` for details

### 4. Purchase Testing

**Model**: `apps/transactions/models/purchase.py`
**Frontend**: `../React2025/src/pages/transactions/PurchaseDetailPage.tsx`

**Test Steps**:

1. Access Purchases section
2. Create purchase for vendor:
   - Select vendor
   - Add items with costs
   - Set delivery dates
3. Test approval workflow
4. Verify cost calculations
5. Check inventory receipt integration
6. Test vendor communication features

## Common Testing Scenarios

### CRUD Operations

- Create new transaction
- Read/view details
- Update existing records
- Delete (if allowed)

### Status Workflows

- Planned → Released → In Progress → Complete
- Hold/Cancel functionality
- Status-dependent field visibility

### Data Relationships

- Customer linking
- Address associations
- Contact information
- Line item management

### Calculations

- Line totals (price × quantity)
- Header totals (subtotal, tax, shipping, total)
- Margin calculations
- Cost tracking

## UI Testing Checklist

### Navigation

- [ ] Breadcrumb navigation works
- [ ] Back/forward browser buttons
- [ ] Direct URL access

### Forms

- [ ] Required field validation
- [ ] Data type validation (numbers, dates)
- [ ] Save/cancel operations
- [ ] Error message display

### Tables/Lists

- [ ] Sorting functionality
- [ ] Filtering options
- [ ] Pagination
- [ ] Row selection

### Responsive Design

- [ ] Desktop layout
- [ ] Tablet/mobile views
- [ ] Form field spacing

## Backend Testing

### API Endpoints

```bash
# Test WCAPI
curl -X GET "http://localhost:8000/api/wcapi/?model_name=invoice&id=1"

# Test save
curl -X POST "http://localhost:8000/api/wcapi/save/" \
  -H "Content-Type: application/json" \
  -d '{"model_name": "invoice", "data": {...}}'
```

### Model Methods

- Test `update_sell_cost_totals()` methods
- Verify signal handlers
- Check validation logic

## Integration Testing

### Cross-Transaction Flow

1. Proposal → Order → Invoice
2. Purchase → Receipt → Invoice matching
3. Customer data consistency across transactions

### External Integrations

- Tax service (when integrated)
- Inventory updates
- Accounting system sync

## Known Issues

- Tax calculation not integrated into invoice totals (shows $0.00)
- Some transaction conversions may need manual data mapping
- PDF generation requires additional setup

## Performance Testing

- Large transaction lists (1000+ records)
- Complex transactions with many line items
- Concurrent user access
- API response times

## Troubleshooting

### Common Issues

- **Page not loading**: Check backend server status
- **Save failures**: Verify required fields and data types
- **Missing data**: Check API responses and model relationships
- **UI errors**: Check browser console for JavaScript errors

### Debug Tools

- Django debug toolbar
- React DevTools
- Browser network inspector
- Database query logs

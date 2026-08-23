# Transaction Flow Test Plan

> **Consolidated**: 2026-01-16  
> **Scope**: WC3 (backend) + R25 (frontend) transaction testing  
> **Status**: Draft

---

## Overview

This document consolidates testing procedures for the transaction system across both WebClerk3 (Django backend) and React2025 (frontend). It supersedes scattered testing sections in other docs.

### Quick Reference

| Layer | Location | Run Command |
|-------|----------|-------------|
| WC3 Unit Tests | `apps/transactions/tests/` | `pytest apps/transactions/tests/ -v` |
| WC3 Integration | `apps/transactions/tests/test_*_integration.py` | `pytest -k integration -v` |
| R25 Unit Tests | `src/**/__tests__/*.test.ts*` | `npm test` |
| R25 E2E | `src/**/*.integration.test.tsx` | `npm run test:e2e` |
| Manual API | curl / Postman | See [API Testing](#api-testing) |

---

## Test Inventory

### WC3 Backend Tests (Existing)

| File | Coverage |
|------|----------|
| `test_proposal_models.py` | Proposal model validation |
| `test_proposal_services.py` | Proposal business logic |
| `test_proposal_serializers.py` | API serialization |
| `test_proposal_integration.py` | Proposal end-to-end |
| `test_proposal_e2e_scenarios.py` | Complex proposal scenarios |
| `test_order_models.py` | Order model validation |
| `test_order_services.py` | Order business logic |
| `test_invoice_models.py` | Invoice model validation |
| `test_invoice_services.py` | Invoice business logic |
| `test_purchase_models.py` | Purchase model validation |
| `test_purchase_services.py` | Purchase business logic |
| `test_payment_models.py` | Payment model validation |
| `test_payment_services.py` | Payment business logic |
| `test_payment_integration.py` | Payment gateway integration |
| `test_requisition_endpoints.py` | Requisition API endpoints |

### WC3 Backend Tests (To Create)

| File | Coverage | Priority |
|------|----------|----------|
| `test_line_item_service.py` | LineItemService CRUD | **HIGH** |
| `test_pending_inventory.py` | Pending record creation/processing | **HIGH** |
| `test_totals_rollup.py` | Header totals from lines | MEDIUM |
| `test_flow_transfers.py` | Proposal→Order→Invoice conversions | MEDIUM |

### R25 Frontend Tests (Existing)

| File | Coverage |
|------|----------|
| `ProposalLineForm.test.tsx` | Proposal line form component |
| `ProposalWorkflow.integration.test.tsx` | Proposal workflow integration |
| `proposalPdfService.test.ts` | PDF generation service |

### R25 Frontend Tests (To Create)

| File | Coverage | Priority |
|------|----------|----------|
| `lineItemService.test.ts` | LineItemService calculations | **HIGH** |
| `TransactionDetailBase.test.tsx` | Base detail component | MEDIUM |
| `ItemSearch.test.tsx` | Item search/select | MEDIUM |
| `TotalsCard.test.tsx` | Totals display | LOW |

---

## Test Phases

### Phase 1: Line Save & Pending (Priority)

The `save_transaction_with_lines()` pipeline is the primary save path for all
R25 transaction saves. `LineItemService` handles per-line operations for the
generic `/wcapi/save/` endpoint. Test both paths.

#### WC3 Backend

```python
# tests/test_line_item_service.py

class TestLineItemServiceAdd:
    """Test adding items to transactions."""
    
    def test_add_item_to_order(self):
        """Add item creates line with correct quantity buckets."""
        
    def test_add_item_creates_pending_record(self):
        """Adding item creates pending for inventory update."""
        
    def test_add_item_no_pending_for_proposal(self):
        """Proposals don't create pending (no inventory effect)."""
        
    def test_add_item_respects_create_pending_flag(self):
        """create_pending=False skips pending creation."""


class TestLineItemServiceUpdate:
    """Test updating line quantities."""
    
    def test_update_quantity_creates_delta_pending(self):
        """Quantity change creates pending with delta."""
        
    def test_update_quantity_calculates_line_totals(self):
        """Line cost/sell recalculated on qty change."""


class TestLineItemServiceDelete:
    """Test removing lines."""
    
    def test_delete_line_creates_release_pending(self):
        """Deleting line creates pending to release qty."""
        
    def test_delete_line_updates_header_totals(self):
        """Header totals recalculated after delete."""


class TestLineItemServiceSearch:
    """Test item search functionality."""
    
    def test_search_by_sku(self):
        """Search finds items by SKU."""
        
    def test_search_by_name(self):
        """Search finds items by name."""
        
    def test_search_respects_org_context(self):
        """Search filters by organization."""
```

#### R25 Frontend

```typescript
// lineItemService.test.ts

describe('LineItemService', () => {
  describe('addItem', () => {
    it('creates line with correct structure', () => {});
    it('calculates extended price', () => {});
    it('applies quantity defaults', () => {});
  });
  
  describe('updateQuantity', () => {
    it('recalculates line totals', () => {});
    it('preserves pricing on qty change', () => {});
  });
  
  describe('calculateLineTotals', () => {
    it('sums cost correctly', () => {});
    it('sums sell correctly', () => {});
    it('calculates margin', () => {});
  });
});
```

### Phase 2: Pending Inventory Processing

#### WC3 Backend

```python
# tests/test_pending_inventory.py

class TestPendingRecordCreation:
    """Test pending records created by LineItemService."""
    
    def test_pending_created_for_so_line_add(self):
        """Order line add creates qty_on_so pending."""
        
    def test_pending_created_for_po_line_add(self):
        """Purchase line add creates qty_on_po pending."""
        
    def test_pending_data_structure(self):
        """Pending data contains required fields."""


class TestPendingProcessor:
    """Test pending record processing."""
    
    def test_process_updates_item_quantity(self):
        """Processing updates Item.quantity buckets."""
        
    def test_process_marks_pending_processed(self):
        """Processed pending gets dt_processed set."""
        
    def test_process_dry_run(self):
        """Dry run reports without changing data."""
        
    def test_process_respects_limit(self):
        """Limit parameter caps records processed."""


class TestPendingManagementCommand:
    """Test management command."""
    
    def test_command_runs(self):
        """Command executes without error."""
        
    def test_command_dry_run_flag(self):
        """--dry-run flag works."""
        
    def test_command_item_id_filter(self):
        """--item-id filters to single item."""
```

### Phase 3: Transaction Flow Integration

Test complete flows: Proposal → Order → Invoice → Payment

#### WC3 Backend

```python
# tests/test_flow_transfers.py

class TestProposalToOrder:
    """Test proposal conversion to order."""
    
    def test_transfer_creates_order(self):
        """Conversion creates order."""
        
    def test_transfer_copies_lines(self):
        """Lines transferred with quantities."""
        
    def test_transfer_creates_pending(self):
        """Pending created for inventory reservation."""
        
    def test_transfer_updates_proposal_status(self):
        """Proposal marked as converted."""


class TestOrderToInvoice:
    """Test order conversion to invoice."""
    
    def test_transfer_creates_invoice(self):
        """Conversion creates invoice."""
        
    def test_transfer_calculates_taxes(self):
        """Tax calculation runs."""
        
    def test_transfer_creates_pending(self):
        """Pending created for inventory issue."""


class TestFullFlow:
    """Test complete transaction lifecycle."""
    
    def test_proposal_to_payment(self):
        """Full flow: proposal → order → invoice → payment."""
```

### Phase 4: Header Totals

#### WC3 Backend

```python
# tests/test_totals_rollup.py

class TestProposalTotals:
    """Test proposal header totals."""
    
    def test_totals_from_lines(self):
        """Header totals computed from lines."""
        
    def test_totals_include_tax(self):
        """Tax included in totals."""
        
    def test_totals_include_shipping(self):
        """Shipping included in totals."""


class TestOrderTotals:
    """Test order header totals."""


class TestInvoiceTotals:
    """Test invoice header totals."""
```

---

## API Testing

### WCAPI Endpoints

```bash
# List transactions
curl "http://localhost:8000/api/wcapi/?model_name=proposal"
curl "http://localhost:8000/api/wcapi/?model_name=order"
curl "http://localhost:8000/api/wcapi/?model_name=invoice"

# Get single transaction
curl "http://localhost:8000/api/wcapi/?model_name=proposal&id=1"

# Create/update transaction
curl -X POST "http://localhost:8000/api/wcapi/save/" \
  -H "Content-Type: application/json" \
  -d '{"model_name": "proposal", "data": {...}}'
```

### Transaction-Specific Endpoints

```bash
# Line item search
curl "http://localhost:8000/tx/search-items/?q=widget&limit=10"

# Add line to transaction
curl -X POST "http://localhost:8000/tx/sales-orders/1/lines/" \
  -H "Content-Type: application/json" \
  -d '{"item_id": 123, "quantity": 5}'

# Convert proposal to order
curl -X POST "http://localhost:8000/tx/proposals/1/convert-to-sales-order/"

# Process pending inventory
curl -X POST "http://localhost:8000/tx/pending/process/"
```

---

## Manual Testing Checklist

### Proposal Flow

- [ ] Create new proposal
- [ ] Add customer
- [ ] Search and add line items
- [ ] Modify quantities
- [ ] Verify totals update
- [ ] Save proposal
- [ ] Convert to order
- [ ] Verify order created with correct lines

### Order Flow

- [ ] View order created from proposal
- [ ] Verify line items transferred
- [ ] Add additional items
- [ ] Update quantities
- [ ] Verify pending records created
- [ ] Convert to invoice

### Invoice Flow

- [ ] View invoice from order
- [ ] Verify line items
- [ ] Check tax calculations
- [ ] Verify totals
- [ ] Apply payment

### Inventory Verification

- [ ] Check Item.quantity before operations
- [ ] Add line to order
- [ ] Verify Pending record created
- [ ] Run `process_line_item_pending`
- [ ] Verify Item.quantity.qty_on_so updated

---

## Running Tests

### WC3 Backend

```bash
# Activate virtualenv
cd /Users/williamjames/Documents/CommerceExpert/webClerk3
source bin/activate

# Run all transaction tests
pytest apps/transactions/tests/ -v

# Run specific test file
pytest apps/transactions/tests/test_line_item_service.py -v

# Run with coverage
coverage run -m pytest apps/transactions/tests/ && coverage report

# Run single test
pytest apps/transactions/tests/test_line_item_service.py::TestLineItemServiceAdd::test_add_item_to_order -v
```

### R25 Frontend

```bash
cd /Users/williamjames/Documents/CommerceExpert/React2025

# Run all tests
npm test

# Run specific test file
npm test -- lineItemService.test.ts

# Run with coverage
npm test -- --coverage

# Watch mode
npm test -- --watch
```

---

## Test Data Setup

### Seed Data Commands

```bash
# Create sample products (vendors, customers, items)
python manage.py seed_sample_products

# Populate item ida = sku (for consistent identifiers)
python manage.py populate_item_ida --overwrite

# Create sample transactions (future)
# python manage.py seed_sample_transactions
```

### Minimal Test Fixtures

```python
# conftest.py fixtures for transaction tests

@pytest.fixture
def sample_customer(db):
    from apps.accounts.models import Customer
    return Customer.objects.create(name="Test Customer")

@pytest.fixture
def sample_item(db):
    from apps.products.models import Item
    return Item.objects.create(
        name="Test Widget",
        sku="TEST-001",
        ida="TEST-001",
        price={"base": 100.00},
        cost={"standard": 50.00}
    )

@pytest.fixture
def sample_order(db, sample_customer):
    from apps.transactions.models import Order
    return Order.objects.create(
        customer_id=sample_customer.id,
        status="planned"
    )
```

---

## CI/CD Integration

### GitHub Actions (proposed)

```yaml
# .github/workflows/test.yml
name: Tests

on: [push, pull_request]

jobs:
  backend:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.12'
      - name: Install dependencies
        run: pip install -r requirements.txt
      - name: Run tests
        run: pytest apps/transactions/tests/ -v

  frontend:
    runs-on: ubuntu-latest
    defaults:
      run:
        working-directory: ../React2025
    steps:
      - uses: actions/checkout@v3
      - name: Set up Node
        uses: actions/setup-node@v3
        with:
          node-version: '18'
      - name: Install dependencies
        run: npm ci
      - name: Run tests
        run: npm test -- --ci
```

---

## Related Documentation

- [Transaction Flows](transaction_flows.md) - System overview
- [Transaction Services](../../../React2025/readmes/topics/transaction-services.md) - Service API docs
- [Inventory Pending](../inventory/inventory.md#line-item-pending-inventory-transaction-level) - Pending system docs
- [Transaction Responsibilities](transaction-flow-responsibilities.md) - Frontend vs backend

---

## Changelog

| Date | Change |
|------|--------|
| 2026-01-16 | Initial consolidation from transaction_testing.md, transaction_flows.md |

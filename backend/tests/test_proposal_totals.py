from __future__ import annotations
import pytest
from apps.transactions.models import Proposal, ProposalLine, Order, OrderLine
from apps.transactions.services.convert.convert_proposal_to_order import (
    transfer_proposal_to_order,
    validate_proposal_for_transfer,
    ProposalToOrderTransferError
)
from apps.transactions.services.transaction_save import save_transaction_with_lines


@pytest.mark.django_db
def test_proposal_update_sell_cost_totals():
    """Proposal header totals aggregate from lines via the single totals engine
    (services/pricing/totals_compute.recalculate_totals). Extended = active x unit."""
    pr = Proposal.objects.create()
    ProposalLine.objects.create(
        proposal=pr,
        quantity={"active": 1},
        price={"unit": 200.0, "discount_amount": 10.0, "precision": 2},
        cost={"unit": 120.0, "shipping": 5.0, "handling": 0.0, "precision": 2},
    )
    ProposalLine.objects.create(
        proposal=pr,
        quantity={"active": 2},
        price={"unit": 25.0, "discount_amount": 0.0, "precision": 2},
        cost={"unit": 15.0, "shipping": 0.0, "handling": 0.0, "precision": 2},
    )

    computed = pr.update_sell_cost_totals(persist=False)

    # subtotal = (200 - 10 discount) + 2 x 25
    assert computed["subtotal"] == 240.0
    assert computed["shipping"] == 5.0
    assert computed["total"] == 245.0
    # margin = subtotal - cost (120 + 2 x 15)
    assert round(computed["margin"], 2) == 90.0
    assert computed["lines_recalculated"] == 2

    # Header totals JSON persisted with discount and cost breakdown
    assert pr.totals["discount"] == 10.0
    assert pr.totals["cost"] == 150.0
    assert pr.totals["total"] == 245.0

@pytest.mark.django_db 
def test_models_exported_correctly():
    """Verify models are exported correctly."""
    import apps.transactions.models as models
    assert hasattr(models, "Proposal")
    assert hasattr(models, "ProposalLine")

# Proposals Module

## Overview
'''
The proposals module handles sales 
quotations and estimates within 
webClerk3's transaction system. 
Proposals represent potential sales 
opportunities that can later be converted 
to sales orders and invoices.


## Architecture

### Models
- **Proposal**: Header model extending `TransactionBaseModel`
  - Inherits standard fields: `ida`, `status`, `party_id`, `refs`, `prefs`, `metadata`
  - Database table: `proposals`
  
- **ProposalLine**: Line items extending `BaseSellLineModel`
  - Has `price` JSON field (unit, discount_percent, discount_amount, extended, etc.)
  - Has `cost` JSON field (unit, extended, shipping, handling, freight, etc.)
  - Database table: `proposal_lines`

### Key Features
- **Sell-side document**: Includes customer-facing pricing via `price` JSON
- **Cost tracking**: Internal cost structure for margin analysis
- **Totals rollup**: Automatic aggregation from lines to header
- **Links management**: Maintains `refs.links.proposal_line` array

## Data Flow
### Line Structure
```json
// ProposalLine.price
{
  "unit": 100.0,
  "discount_percent": 5.0,
  "discount_amount": 5.0,
  "extended": 95.0,
  "is_fixed": false,
  "precision": 2
}

// ProposalLine.cost
{
  "unit": 60.0,
  "extended": 60.0,
  "shipping": 5.0,
  "handling": 0.0,
  "freight": 0.0,
  "commissions": 2.0,
  "tax": 0.0,
  "tax_rate": 0.0,
  "precision": 2
}

### Header Aggregation
```python
# Compute totals from lines
proposal = Proposal.objects.get(pk=1)
totals = proposal.update_sell_cost_totals(persist=False)

# Returns structure:
{
  "sell": {
    "line_sum_goods": 250.0,
    "discount": 10.0,
    "tax": 0.0,
    "shipping": 0.0,
    "handling": 0.0,
    "other": 0.0,
    "total": 250.0
  },
  "cost": {
    "line_sum_goods": 150.0,
    "line_sum_tax": 0.0,
    "line_sum_shipping": 5.0,
    "line_sum_handling": 0.0,
    "freight": 0.0,
    "commissions": 0.0,
    "tax": 0.0,
    "total": 155.0
  },
  "totals": {
    "total": 250.0,
    "cost": 155.0,
    "margin": 95.0,
    "margin_pc": 38.0,
    "received": null,
    "balance": null
  }
}
```

## API Integration

### WCAPI Save Endpoint
```bash
# Create proposal with lines
POST /wcapi/save/
{
  "model_name": "proposal",
  "status": "draft",
  "party_id": 123
}

# Add proposal line
POST /wcapi/save/
{
  "model_name": "proposal_line",
  "parent_id": 456,
  "price": {
    "unit": 100.0,
    "extended": 100.0
  },
  "cost": {
    "unit": 60.0,
    "extended": 60.0
  }
}
```

### Deep Merge Behavior
- JSON fields (price, cost, refs, prefs, metadata) are deep-merged on updates
- Unknown top-level fields are captured in `prefs.userdefined`
- Line updates preserve existing price/cost structure while updating specified keys

## Services

### `apps/transactions/services/proposal_totals.py`
- `compute_proposal_sell_cost_totals(proposal)`: Aggregates line data into header structure
- Used by `Proposal.update_sell_cost_totals(persist=False)` method
- Handles Decimal precision and JSON-safe float conversion

## Signals & Automation

### Links Maintenance
- `maintain_proposal_links` signal updates `proposal.refs.links.proposal_line` on line creation
- Uses singular model name as key (consistent with other transaction types)

### Future Enhancements
- Auto-rollup signals on line save/delete
- Header persistence when `sell`/`cost`/`totals` fields are added to model

## Testing

### Test Files
- `tests/test_proposal_totals.py`: Validates aggregation logic and model exports
- `tests/test_line_model_inheritance.py`: Confirms price field presence on sell-side lines

### Running Tests
```bash
source bin/activate
pytest -xvs tests/test_proposal_totals.py
```

## Development Workflow

### Adding Proposal Features
1. **Line modifications**: Update `BaseSellLineModel` in `base_line_model.py`
2. **Header fields**: Extend `Proposal` model (migrations required)
3. **Rollup logic**: Modify `proposal_totals.py` service
4. **Tests**: Add coverage in `tests/test_proposal_totals.py`

### Migration Path
1. Current: Computation on-demand via `update_sell_cost_totals()`
2. Future: Add header JSON fields (`sell`, `cost`, `totals`) with migrations
3. Indexing: Functional B-Tree index on `(totals->>'total')::numeric` for performance

## Related Documentation
- [Transactions Overview](transactions-totals.md)
- [Line Model Split](transactions-totals.md#line-json)
- [WCAPI Deep Merge](../readme.md#write-policy)

## References
- Models: `apps/transactions/models/proposal.py`, `apps/transactions/models/proposal_line.py`
- Services: `apps/transactions/services/proposal_totals.py`
- Signals: `apps/transactions/signals.py`
- Tests: `tests/test_proposal_totals.py`
- Tests: `tests/test_proposal_totals.py`

'''
def _save_reviewed_order(result):
    """Save the lines a conversion returned for review — the step that creates lines."""
    return save_transaction_with_lines(
        model_key="order",
        header_data={"id": result["order_id"]},
        lines_data=result["lines"],
        request=None,
        verify_calculations=False,
    )


@pytest.fixture(autouse=True)
def _no_pending_dispatch(monkeypatch):
    monkeypatch.setattr(
        "apps.products.dispatch_pending.dispatch_pending_processing",
        lambda *args, **kwargs: None,
    )


@pytest.mark.django_db
class TestProposalToOrderTransfer:
    """Test proposal to order transfer functionality.

    Conversion creates the order header and returns lines for review; lines are
    created when the reviewed order is saved. Each order line is a child of its
    proposal line (parent_line_id); the proposal line's remaining is recomputed.
    """

    def test_transfer_all_lines_success(self):
        """Test successful transfer of all proposal lines to order."""
        proposal = Proposal.objects.create(status='approved',)
        line1 = ProposalLine.objects.create(
            proposal=proposal,
            price={'unit': 100.0, 'precision': 2},
            cost={'unit': 60.0, 'precision': 2},
            quantity={'active': 1, 'is_blanket': False, 'increment': 0}
        )
        line2 = ProposalLine.objects.create(
            proposal=proposal,
            price={'unit': 100.0, 'precision': 2},
            cost={'unit': 60.0, 'precision': 2},
            quantity={'active': 2, 'is_blanket': False, 'increment': 0}
        )

        result = transfer_proposal_to_order(
            proposal=proposal,
            transfer_all=True,
            order_status='confirmed',
        )

        assert result['success'] is True
        assert result['proposal_id'] == proposal.id
        assert result['lines_for_review'] == 2
        source_ids = {ln['refs']['source']['proposal_line_id'] for ln in result['lines']}
        assert source_ids == {line1.id, line2.id}

        order = Order.objects.get(id=result['order_id'])
        assert order.status == 'confirmed'
        assert order.refs['source']['proposal_id'] == proposal.id
        # Header only — no lines until the reviewed order is saved
        assert OrderLine.objects.filter(order=order).count() == 0

        _save_reviewed_order(result)

        order_lines = OrderLine.objects.filter(order=order)
        assert order_lines.count() == 2
        for order_line in order_lines:
            assert order_line.parent_line_id == order_line.refs['source']['proposal_line_id']
            assert order_line.quantity['active'] == order_line.quantity['staged']
            assert order_line.quantity['remaining'] == order_line.quantity['active']
        for pl in (line1, line2):
            pl.refresh_from_db()
            assert pl.quantity['remaining'] == 0
            assert pl.status == 'transferred'

    def test_transfer_selected_lines_only(self):
        """Test transfer of selected lines only."""
        proposal = Proposal.objects.create(status='approved',)
        line1 = ProposalLine.objects.create(
            proposal=proposal,
            price={'unit': 100.0, 'precision': 2},
            quantity={'active': 1}
        )
        line2 = ProposalLine.objects.create(
            proposal=proposal,
            price={'unit': 100.0, 'precision': 2},
            quantity={'active': 2}
        )
        line3 = ProposalLine.objects.create(
            proposal=proposal,
            price={'unit': 50.0, 'precision': 2},
            quantity={'active': 1}
        )

        result = transfer_proposal_to_order(
            proposal=proposal,
            line_ids=[line1.id, line3.id],
            transfer_all=False,
        )

        assert result['success'] is True
        assert result['lines_for_review'] == 2
        source_ids = {ln['refs']['source']['proposal_line_id'] for ln in result['lines']}
        assert source_ids == {line1.id, line3.id}

        _save_reviewed_order(result)
        order = Order.objects.get(id=result['order_id'])
        assert OrderLine.objects.filter(order=order).count() == 2

        line1.refresh_from_db()
        line3.refresh_from_db()
        assert line1.status == 'transferred'
        assert line3.status == 'transferred'

        line2.refresh_from_db()
        assert line2.status != 'transferred'
        assert line2.quantity['remaining'] == 2

    def test_transfer_validation_errors(self):
        """Test various validation error conditions."""
        proposal = Proposal.objects.create(status='approved',)
        
        # Test missing line_ids when transfer_all=False
        with pytest.raises(ProposalToOrderTransferError, match="Must specify line_ids"):
            transfer_proposal_to_order(
                proposal=proposal,
                line_ids=None,
                transfer_all=False
            )
        
        # Test invalid line IDs
        with pytest.raises(ProposalToOrderTransferError, match="Line IDs not found"):
            transfer_proposal_to_order(
                proposal=proposal,
                line_ids=[999, 1000],
                transfer_all=False
            )
        
        # Test no lines to transfer
        with pytest.raises(ProposalToOrderTransferError, match="No lines to transfer"):
            transfer_proposal_to_order(
                proposal=proposal,
                transfer_all=True
            )
    
    def test_quantity_conversion(self):
        """Quantity carried from proposal line to order line: active/staged = proposal
        remaining; precision and is_fixed preserved."""
        proposal = Proposal.objects.create(status='approved',)
        line = ProposalLine.objects.create(
            proposal=proposal,
            price={'unit': 100.0, 'precision': 2},
            quantity={
                'active': 3,
                'is_blanket': True,
                'increment': 1,
                'precision': 0,
                'is_fixed': True
            }
        )

        result = transfer_proposal_to_order(proposal=proposal, transfer_all=True)
        reviewed = result['lines'][0]['quantity']
        assert reviewed['active'] == 3
        assert reviewed['staged'] == 3

        _save_reviewed_order(result)
        order = Order.objects.get(id=result['order_id'])
        order_line = OrderLine.objects.filter(order=order).first()
        assert order_line is not None, "Expected the saved order to have a line"
        quantity = order_line.quantity or {}
        assert quantity['active'] == 3
        assert quantity['staged'] == 3
        assert quantity['remaining'] == 3
        assert quantity.get('precision', 2) == 0
        assert quantity.get('is_fixed') is True
        assert order_line.parent_line_id == line.id

        line.refresh_from_db()
        assert line.quantity['remaining'] == 0
        assert line.status == 'transferred'


@pytest.mark.django_db
class TestProposalTransferValidation:
    """Test proposal transfer validation."""
    
    def test_validation_success(self):
        """Test successful validation."""
        proposal = Proposal.objects.create(status='approved',)
        ProposalLine.objects.create(
            proposal=proposal,
            quantity={'active': 1},
            price={'unit': 100.0, 'precision': 2}
        )
        ProposalLine.objects.create(
            proposal=proposal,
            quantity={'active': 2},
            price={'unit': 100.0, 'precision': 2}
        )

        result = validate_proposal_for_transfer(proposal)

        assert result['can_transfer'] is True
        assert len(result['errors']) == 0
        assert result['line_count'] == 2
        assert result['total'] == 300.0
    
    def test_validation_warnings(self):
        """Test validation with warnings."""
        proposal = Proposal.objects.create(status='converted',)
        line1 = ProposalLine.objects.create(
            proposal=proposal,
            price={'extended': 100.0, 'unit': 100.0, 'precision': 2}
        )
        line2 = ProposalLine.objects.create(
            proposal=proposal,
            status='transferred',
            price={'extended': 200.0, 'unit': 200.0, 'precision': 2}
        )
        
        result = validate_proposal_for_transfer(proposal)
        
        assert result['can_transfer'] is True
        assert len(result['warnings']) == 2
        assert 'status is converted' in result['warnings'][0]
        assert 'already transferred' in result['warnings'][1]
    
    def test_validation_errors(self):
        """Test validation errors."""
        # Test missing proposal
        result = validate_proposal_for_transfer(None)
        assert result['can_transfer'] is False
        assert 'Proposal not found' in result['errors']
        
        # Test no lines
        proposal = Proposal.objects.create(status='approved',)
        result = validate_proposal_for_transfer(proposal)
        assert result['can_transfer'] is False
        assert 'No lines to transfer' in result['errors']
        
        # Test invalid line IDs
        ProposalLine.objects.create(proposal=proposal, price={'extended': 100.0})
        result = validate_proposal_for_transfer(proposal, line_ids=[999])
        assert result['can_transfer'] is False
        assert 'Line IDs not found' in result['errors'][0]
# """
# python
# # Proposal to Order Transfer Service

# ## Overview
# The proposal-to-order transfer service handles conversion of sales proposals into sales orders within webClerk3's transaction system. This enables the sales workflow from quote to confirmed order.

# ## Service API

# ### `transfer_proposal_to_order()`
# Main transfer function with full control over the conversion process.

# ```python
# from apps.transactions.services.convert.convert_proposal_to_order import transfer_proposal_to_order

# # Transfer all lines
# result = transfer_proposal_to_order(
#     proposal=proposal,
#     transfer_all=True,
#     order_status='confirmed',
#     preserve_proposal=True
# )

# # Transfer selected lines only
# result = transfer_proposal_to_order(
#     proposal=proposal,
#     line_ids=[123, 456, 789],
#     transfer_all=False,
#     order_status='pending',
#     preserve_proposal=True
# )
# ```

# #### Parameters
# - `proposal`: Source Proposal instance
# - `line_ids`: Optional list of ProposalLine IDs to transfer
# - `transfer_all`: If True and line_ids is None, transfer all lines
# - `order_status`: Status to set on new order (default: 'confirmed')
# - `preserve_proposal`: If True, keep original proposal; if False, mark as converted

# #### Returns
# ```python
# {
#     'success': True,
#     'order_id': 123,
#     'proposal_id': 456,
#     'lines_transferred': 3,
#     'line_mapping': {789: 101, 790: 102, 791: 103},  # proposal_line_id -> order_line_id
#     'proposal_preserved': True,
#     'order_status': 'confirmed'
# }
# ```

# ### `validate_proposal_for_transfer()`
# Pre-transfer validation to check readiness and identify potential issues.

# ```python
# from apps.transactions.services.convert.convert_proposal_to_order import validate_proposal_for_transfer

# validation = validate_proposal_for_transfer(proposal, line_ids=[123, 456])
# if validation['can_transfer']:
#     # Proceed with transfer
#     result = transfer_proposal_to_order(...)
# else:
#     # Handle errors
#     print(validation['errors'])
# ```

# #### Returns
# ```python
# {
#     'can_transfer': True,
#     'errors': [],
#     'warnings': ['Proposal status is expired'],
#     'line_count': 3,
#     'total': 1500.0
# }
# ```

# ## Data Transformation

# ### Header Level
# - **Party**: Copied from proposal to order
# - **Status**: Set to specified order_status
# - **Refs**: Enhanced with source tracking and conversion metadata
# - **Prefs**: Copied directly from proposal
# - **Metadata**: Enhanced with conversion tracking

# ### Line Level
# - **Price/Cost**: Copied directly (both are sell-side models)
# - **Quantity**: Converted from proposal structure to order structure
# - **Status**: Set to 'pending' or copied from proposal line
# - **Refs/Prefs**: Copied with source line tracking added
# - **Metadata**: Enhanced with conversion lineage

# ### Quantity Conversion
# Proposal and order lines have different quantity semantics:

# ```python
# # Proposal quantity
# {
#     'is_blanket': False,
#     'increment': 0,
#     'ordered': 5,
#     'remaining': 5
# }

# # Converts to order quantity
# {
#     'invoiced': 0,
#     'remaining': 5,  # From proposal.ordered
#     'precision': 2,
#     'is_fixed': False,
#     'converted_from_proposal': {
#         'is_blanket': False,
#         'increment': 0,
#         'original_ordered': 5,
#         'original_remaining': 5
#     }
# }
# ```

# ## Transfer Modes

# ### Full Transfer
# Transfer all proposal lines to a new order:
# - Sets `transfer_all=True`
# - Optionally preserve or convert proposal status
# - Creates complete order matching proposal scope

# ### Partial Transfer
# Transfer selected lines only:
# - Sets `transfer_all=False` with specific `line_ids`
# - Marks transferred lines as 'transferred'
# - Leaves remaining lines on original proposal
# - Enables incremental order creation from large proposals

# ### Conversion vs Preservation
# - **Preserve**: Original proposal remains active for additional transfers
# - **Convert**: Proposal marked as 'converted', preventing further transfers

# ## Error Handling

# ### `ProposalToOrderTransferError`
# Custom exception for business logic violations:
# - Missing required parameters
# - Invalid line ID references
# - No lines available for transfer
# - Proposal state conflicts

# ### Validation Errors
# Pre-transfer validation catches:
# - Missing proposals or lines
# - Invalid line ID specifications
# - State inconsistencies
# - Data completeness issues

# ### Transaction Safety
# All transfers run in database transactions:
# - Atomic creation of order and lines
# - Rollback on any failure
# - Consistent state maintenance

# ## Integration Points

# ### WCAPI Integration
# ```bash
# # Via API endpoint (to be implemented)
# POST /api/transactions/transfer/
# {
#     "source_type": "proposal",
#     "source_id": 456,
#     "target_type": "order",
#     "line_ids": [789, 790],
#     "order_status": "confirmed",
#     "preserve_source": true
# }
# ```

# ### Signal Integration
# Transfer operations trigger standard model signals:
# - `post_save` for new order and lines
# - Link maintenance via existing signals
# - Opportunity for custom business logic hooks

# ### Audit Trail
# Complete conversion tracking via:
# - Order refs.source pointing to original proposal
# - Line refs.source linking to original proposal lines
# - Metadata.conversion capturing transfer details
# - Timestamps and version tracking

# ## Testing

# ### Test Coverage
# - Full transfer scenarios
# - Partial transfer scenarios  
# - Validation error conditions
# - Quantity conversion logic
# - Preserve vs convert modes
# - Database transaction integrity

# ### Running Tests
# ```bash
# source bin/activate
# pytest -xvs tests/test_proposal_to_order_transfer.py
# ```

# ## Development Workflow

# ### Adding Transfer Features
# 1. **Service Logic**: Extend functions in `proposal_to_order.py`
# 2. **Validation**: Add checks in `validate_proposal_for_transfer()`
# 3. **Error Handling**: Use `ProposalToOrderTransferError` for business logic errors
# 4. **Tests**: Add coverage in `test_proposal_to_order_transfer.py`

# ### Future Enhancements
# - Order-to-invoice transfer service (similar pattern)
# - Bulk transfer API endpoints
# - Transfer approval workflows
# - Advanced quantity splitting logic
# - Cross-company transfer support

# ## References
# - Service: `apps/transactions/services/proposal_to_order.py`
# - Tests: `tests/test_proposal_to_order_transfer.py`
# - Base Documentation: [Transactions Overview](transactions-totals.md)
# ```
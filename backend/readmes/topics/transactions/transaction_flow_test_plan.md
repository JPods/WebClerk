# Transaction Flow — Test Plan

> **Created**: 2026-02-17  
> **Updated**: 2026-03  
> **Purpose**: Validate the full transaction lifecycle, parent-child lineage,
> quantity flow (`staged`/`active`/`remaining`/`children_active`), and header totals rollup.
>
> **Note**: Some code samples below still reference `"transferred"` — the canonical
> quantity keys are now `staged`, `active`, `remaining`. Parent lines track children
> via `children_active`. See `transactions-totals.md` for the current model.

---

## Scope

This test plan covers:

1. **FK relationships** — transaction → org, line → parent transaction
2. **Parent lineage** — `parent_model`/`parent_id` across transfer services
3. **Quantity flow** — `staged`/`active`/`remaining`/`children_active` through the chain
4. **Header totals** — line-level changes rolling up via totals services
5. **Inventory impact** — pending records created for each line type
6. **Ledger & Payment** — invoice → ledger → payment settlement

---

## 1. Model & FK Tests

### 1a. Line → Parent FK

Each line type must have a proper FK to its parent header.

| Test | Assert |
|------|--------|
| `ProposalLine.proposal_id` is set on save | `line.proposal == proposal` |
| `OrderLine.order_id` is set on save | `line.order == order` |
| `InvoiceLine.invoice_id` is set on save | `line.invoice == invoice` |
| `PurchaseLine.purchase_id` is set on save | `line.purchase == purchase` |
| `WorkOrderLine.workorder_id` is set on save | `line.workorder == workorder` |
| `ReceiptLine.receipt_id` is set on save | `line.receipt == receipt` |
| Deleting parent cascades lines | `assert LineModel.objects.filter(parent_id=pk).count() == 0` |

```python
# tests/test_line_fk.py
import pytest
from apps.transactions.models import Order, OrderLine

@pytest.mark.django_db
class TestLineForeignKeys:
    def test_order_line_fk(self, sample_order):
        line = OrderLine.objects.create(
            order=sample_order,
            item={"item_id": 1, "description": "Test"},
            quantity={"staged": 5, "transferred": 0, "remaining": 5},
        )
        assert line.order_id == sample_order.pk
        assert line.parent == sample_order
        assert line.parent_id_value == sample_order.pk

    def test_cascade_delete(self, sample_order):
        OrderLine.objects.create(order=sample_order, item={"item_id": 1})
        sample_order.delete()
        assert OrderLine.objects.count() == 0
```

### 1b. Transaction → Org FK

| Test | Assert |
|------|--------|
| `Order.customer_id` links to OrgBase | `order.customer.pk == org.pk` |
| `Purchase.vendor_id` links to OrgBase | `purchase.vendor.pk == org.pk` |
| Null vendor on sell-side is allowed | `order.vendor is None` — no error |
| Null customer on exec-side is allowed | `purchase.customer is None` — no error |

---

## 2. Parent Lineage Tests (`parent_model` / `parent_id`)

### 2a. Transfer Services Set Lineage

| Transfer | Assert on target |
|----------|-----------------|
| Proposal → Order | `order.parent_model == "proposal"`, `order.parent_id == proposal.pk` |
| Order → Invoice | `invoice.parent_model == "order"`, `invoice.parent_id == order.pk` |
| Order → Purchase | `purchase.parent_model == "order"`, `purchase.parent_id == order.pk` |
| Proposal → Purchase | `purchase.parent_model == "proposal"`, `purchase.parent_id == proposal.pk` |
| Purchase → Receipt | `receipt.purchase_id == purchase.pk` (true FK, not parent_model) |

```python
# tests/test_parent_lineage.py
import pytest
from apps.transactions.services.proposal_to_order import transfer_proposal_to_order

@pytest.mark.django_db
class TestParentLineage:
    def test_proposal_to_order_sets_parent(self, proposal_with_lines):
        order = transfer_proposal_to_order(proposal_with_lines)
        assert order.parent_model == "proposal"
        assert order.parent_id == proposal_with_lines.pk

    def test_order_to_invoice_sets_parent(self, order_with_lines):
        from apps.transactions.services.order_to_invoice import transfer_order_to_invoice
        invoice = transfer_order_to_invoice(order_with_lines)
        assert invoice.parent_model == "order"
        assert invoice.parent_id == order_with_lines.pk
```

### 2b. Line-Level Lineage via `refs`

| Transfer | Assert on target line |
|----------|-----------------------|
| Proposal → Order | `order_line.refs["source"]["model"] == "proposal_line"` |
| Proposal → Order | `order_line.refs["source"]["id"] == source_proposal_line.pk` |
| Order → Invoice | `invoice_line.refs["source"]["model"] == "order_line"` |

```python
def test_line_lineage_refs(self, proposal_with_lines):
    order = transfer_proposal_to_order(proposal_with_lines)
    order_line = order.lines.first()
    source_line = proposal_with_lines.lines.first()
    assert order_line.refs.get("source", {}).get("id") == source_line.pk
```

---

## 3. Quantity Flow Tests

### 3a. `default_quantity()` Returns Canonical Keys

| Test | Assert |
|------|--------|
| `default_quantity("order")` | Keys: `staged`, `transferred`, `remaining`, `is_fixed`, `precision` |
| `default_quantity("invoice")` | Same keys |
| `default_quantity("purchase")` | Same keys |
| No legacy keys present | `"ordered" not in result`, `"invoiced" not in result`, `"received" not in result` |

```python
from apps.transactions.models.base_line_model import default_quantity

@pytest.mark.parametrize("kind", ["proposal", "order", "invoice", "purchase", "workorder"])
def test_default_quantity_canonical_keys(kind):
    q = default_quantity(kind)
    assert "staged" in q
    assert "transferred" in q
    assert "remaining" in q
    assert "ordered" not in q
    assert "invoiced" not in q
    assert "received" not in q
    assert "shipped" not in q
```

### 3b. Quantity Through Transfer Chain

**Scenario**: Proposal (staged=10) → Order → Invoice

| Step | `staged` | `transferred` | `remaining` |
|------|----------|------------|-------------|
| ProposalLine created | 10 | 0 | 10 |
| Transfer to Order — source proposal line | 10 | 10 | 0 |
| OrderLine created | 10 | 0 | 10 |
| Transfer to Invoice — source order line | 10 | 10 | 0 |
| InvoiceLine created | 10 | 0 | 10 |

```python
@pytest.mark.django_db
class TestQuantityFlow:
    def test_proposal_to_order_quantity(self, proposal_with_lines):
        source_line = proposal_with_lines.lines.first()
        assert source_line.quantity["staged"] == 10
        assert source_line.quantity["remaining"] == 10

        order = transfer_proposal_to_order(proposal_with_lines)

        # Source line should be transferred
        source_line.refresh_from_db()
        assert source_line.quantity["transferred"] == 10
        assert source_line.quantity["remaining"] == 0

        # Target line should have staged = source staged
        order_line = order.lines.first()
        assert order_line.quantity["staged"] == 10
        assert order_line.quantity["transferred"] == 0
        assert order_line.quantity["remaining"] == 10

    def test_partial_transfer(self, order_with_lines):
        """Transfer only 6 of 10 staged on order to invoice."""
        from apps.transactions.services.order_to_invoice import transfer_order_to_invoice
        invoice = transfer_order_to_invoice(order_with_lines, quantity_override=6)

        source_line = order_with_lines.lines.first()
        source_line.refresh_from_db()
        assert source_line.quantity["transferred"] == 6
        assert source_line.quantity["remaining"] == 4

        invoice_line = invoice.lines.first()
        assert invoice_line.quantity["staged"] == 6
```

### 3c. Frontend Sends `staged` (Not `ordered`)

```python
@pytest.mark.django_db
def test_save_view_uses_staged(api_client, sample_order):
    """The /wcapi/save/ endpoint must accept quantity.staged."""
    resp = api_client.post("/wcapi/save/", {
        "model_name": "order",
        "record": {
            "id": sample_order.pk,
            "lines": [{
                "item": {"item_id": 1},
                "quantity": {"staged": 7},
            }]
        }
    }, format="json")
    assert resp.status_code == 200
    line = sample_order.lines.first()
    assert line.quantity["staged"] == 7
```

---

## 4. Header Totals Rollup Tests

### 4a. Line Save Triggers Header Recalc

| Test | Assert |
|------|--------|
| Save ProposalLine → Proposal.totals updated | `proposal.totals["total"]` == sum of line `price.extended` |
| Save OrderLine → Order.totals updated | `order.totals["total"]` == sum of line `price.extended` + tax + shipping |
| Save InvoiceLine → Invoice.totals updated | Same pattern |
| Save PurchaseLine → Purchase.totals updated | `purchase.totals["cost"]` == sum of line `cost.extended` |
| Delete line → header totals decrease | Totals recalculated after line removal |

```python
@pytest.mark.django_db
class TestHeaderTotals:
    def test_order_totals_after_line_save(self, sample_order):
        OrderLine.objects.create(
            order=sample_order,
            quantity={"staged": 5, "transferred": 0, "remaining": 5},
            price={"unit": 100.00, "extended": 500.00},
            cost={"unit": 60.00, "extended": 300.00},
        )
        # Trigger totals recalc (signal or explicit call)
        from apps.transactions.services.order_totals import compute_order_sell_cost_totals
        compute_order_sell_cost_totals(sample_order)
        sample_order.refresh_from_db()
        assert sample_order.totals["total"] == 500.00
        assert sample_order.totals["cost"] == 300.00
```

### 4b. Known Issue — Post-Save Signals

Currently only `ProposalLine` has a post-save signal for automatic totals recalc.
Order, Invoice, and Purchase lines need the same signal.

| Line Model | Signal exists? | Status |
|------------|---------------|--------|
| ProposalLine | ✅ Yes | Working |
| OrderLine | ❌ No | **Needs implementation** |
| InvoiceLine | ❌ No | **Needs implementation** |
| PurchaseLine | ❌ No | **Needs implementation** |
| WorkOrderLine | ❌ No | **Needs implementation** |

---

## 5. Inventory (Pending) Tests

### 5a. Line Create → Pending Record

| Transaction | Pending type | Quantity bucket |
|-------------|-------------|-----------------|
| Order line created | `SO` | `on_so` = `quantity.staged` |
| Invoice line created | `IN` | `on_in` = `quantity.staged` |
| Proposal line created | `PP` | `on_p` = `quantity.staged` |
| Purchase line created | `PO` | `on_po` = `quantity.staged` |
| WorkOrder line created | `WO` | `on_wo` = `quantity.staged` |

```python
@pytest.mark.django_db
def test_order_line_creates_pending(sample_order):
    from apps.inventory.models import Pending
    OrderLine.objects.create(
        order=sample_order,
        item={"item_id": 236},
        quantity={"staged": 10, "transferred": 0, "remaining": 10},
    )
    pending = Pending.objects.filter(
        data__type_id="SO",
        data__item_id=236,
    ).last()
    assert pending is not None
    assert pending.data["on_so"] == 10.0
```

---

## 6. Ledger & Payment Tests

### 6a. Invoice → Ledger

| Test | Assert |
|------|--------|
| Invoice with terms creates ledger rows | `Ledger.objects.filter(invoice=invoice).count() >= 1` |
| Ledger `value_original` matches invoice total / installments | Sum of ledger values == invoice total |
| Ledger `dt_due` calculated from terms | Based on `PaymentTerm.days` |

### 6b. Payment → Ledger Settlement

| Test | Assert |
|------|--------|
| PaymentApplication created | Links payment to invoice |
| Ledger `value_available` decremented | `ledger.value_available == original - applied` |
| Invoice `totals.received` updated | `invoice.totals["received"] == payment_amount` |
| Invoice `totals.balance` updated | `invoice.totals["balance"] == total - received` |
| Full payment marks ledger `is_settled` | `ledger.is_settled == True` |

---

## 7. End-to-End Flow Tests

### 7a. Sell-Side: Proposal → Order → Invoice → Payment

```python
@pytest.mark.django_db
class TestSellSideE2E:
    def test_full_sell_flow(self, customer_org, item):
        # 1. Create Proposal
        proposal = Proposal.objects.create(customer=customer_org, status="planned")
        ProposalLine.objects.create(
            proposal=proposal,
            item={"item_id": item.pk, "description": item.display_name},
            quantity={"staged": 10, "transferred": 0, "remaining": 10},
            price={"unit": 100.00, "extended": 1000.00},
        )

        # 2. Transfer to Order
        order = transfer_proposal_to_order(proposal)
        assert order.parent_model == "proposal"
        assert order.parent_id == proposal.pk
        assert order.lines.count() == 1
        order_line = order.lines.first()
        assert order_line.quantity["staged"] == 10

        # 3. Transfer to Invoice
        invoice = transfer_order_to_invoice(order)
        assert invoice.parent_model == "order"
        assert invoice.parent_id == order.pk
        invoice_line = invoice.lines.first()
        assert invoice_line.quantity["staged"] == 10

        # 4. Verify source lines are transferred
        proposal.lines.first().refresh_from_db()
        assert proposal.lines.first().quantity["transferred"] == 10
        order.lines.first().refresh_from_db()
        assert order.lines.first().quantity["transferred"] == 10

        # 5. Apply Payment (when ledger is implemented)
        # payment = Payment.objects.create(invoice=invoice, amount=1000.00)
        # apply_payment(payment)
        # invoice.refresh_from_db()
        # assert invoice.totals["balance"] == 0
```

### 7b. Exec-Side: Order → Purchase → Receipt

```python
@pytest.mark.django_db
class TestExecSideE2E:
    def test_order_to_purchase_to_receipt(self, order_with_lines, vendor_org):
        # 1. Transfer to Purchase
        from apps.transactions.services.order_to_purchase import transfer_order_to_purchase
        purchase = transfer_order_to_purchase(order_with_lines, vendor=vendor_org)
        assert purchase.parent_model == "order"
        assert purchase.vendor == vendor_org

        # 2. Receive against Purchase
        from apps.transactions.services.flow import receive_purchase, ReceiveLine
        po_line = purchase.lines.first()
        receipt = receive_purchase(
            purchase, "RCV-001",
            [ReceiveLine(po_line_id=po_line.pk, qty=10, warehouse_code="MAIN")]
        )
        assert receipt.source_type == "purchase_receipt"
        assert receipt.purchase == purchase
```

---

## 8. Transfer Service Quantity Key Alignment

### Action Items

The following transfer services still reference deprecated quantity keys and must be updated:

| File | Legacy key used | Should be |
|------|----------------|-----------|
| `services/transfer_utils.py` `convert_quantity_from_source()` | Falls back to `ordered` | Use `staged` only |
| `services/proposal_to_order.py` `_convert_quantity_from_proposal()` | Checks `staged` then `ordered` | `staged` only |
| `services/order_to_invoice.py` `_convert_quantity_for_invoice()` | Produces `packed`, reads `invoiced` | Use `staged`/`transferred` |
| `services/order_to_invoice.py` `_update_order_line_quantity()` | Writes `invoiced`, decrements `remaining` | Write `transferred`, decrement `remaining` |

### Test for No Legacy Keys

```python
@pytest.mark.django_db
@pytest.mark.parametrize("transfer_fn,source_fixture", [
    ("transfer_proposal_to_order", "proposal_with_lines"),
    ("transfer_order_to_invoice", "order_with_lines"),
    ("transfer_order_to_purchase", "order_with_lines"),
])
def test_no_legacy_quantity_keys(transfer_fn, source_fixture, request):
    source = request.getfixturevalue(source_fixture)
    fn = ... # import the function
    target = fn(source)
    for line in target.lines.all():
        q = line.quantity
        assert "ordered" not in q, f"Legacy key 'ordered' found in {line}"
        assert "invoiced" not in q, f"Legacy key 'invoiced' found in {line}"
        assert "received" not in q, f"Legacy key 'received' found in {line}"
        assert "shipped" not in q, f"Legacy key 'shipped' found in {line}"
        assert "packed" not in q, f"Legacy key 'packed' found in {line}"
        assert "staged" in q
        assert "transferred" in q
        assert "remaining" in q
```

---

## 9. Test Fixtures

```python
# conftest.py additions
import pytest
from apps.transactions.models import (
    Proposal, ProposalLine, Order, OrderLine,
    Invoice, InvoiceLine, Purchase, PurchaseLine,
)
from apps.orgs.models import OrgBase

@pytest.fixture
def customer_org(db):
    return OrgBase.objects.create(display_name="Test Customer", org_type="customer")

@pytest.fixture
def vendor_org(db):
    return OrgBase.objects.create(display_name="Test Vendor", org_type="vendor")

@pytest.fixture
def proposal_with_lines(db, customer_org):
    p = Proposal.objects.create(customer=customer_org, status="planned")
    ProposalLine.objects.create(
        proposal=p,
        item={"item_id": 1, "description": "Widget", "ida_item": "WDG-001"},
        quantity={"staged": 10, "transferred": 0, "remaining": 10, "is_fixed": False, "precision": 2},
        price={"unit": 100.00, "extended": 1000.00},
        cost={"unit": 60.00, "extended": 600.00},
    )
    return p

@pytest.fixture
def order_with_lines(db, customer_org):
    o = Order.objects.create(customer=customer_org, status="planned")
    OrderLine.objects.create(
        order=o,
        item={"item_id": 1, "description": "Widget", "ida_item": "WDG-001"},
        quantity={"staged": 10, "transferred": 0, "remaining": 10, "is_fixed": False, "precision": 2},
        price={"unit": 100.00, "extended": 1000.00},
        cost={"unit": 60.00, "extended": 600.00},
    )
    return o
```

---

## 10. Execution Order

| Phase | Tests | Prerequisite |
|-------|-------|-------------|
| **Phase 1** | Model & FK (§1), `default_quantity` (§3a) | Models exist |
| **Phase 2** | Parent lineage (§2), Quantity flow (§3b–3c) | Transfer services work |
| **Phase 3** | Header totals (§4), Pending inventory (§5) | Signals + LineItemService |
| **Phase 4** | Ledger & Payment (§6) | Accounts pipeline |
| **Phase 5** | End-to-end (§7), Legacy key cleanup (§8) | All above pass |

```bash
# Run by phase
pytest tests/test_line_fk.py tests/test_default_quantity.py -v          # Phase 1
pytest tests/test_parent_lineage.py tests/test_quantity_flow.py -v      # Phase 2
pytest tests/test_header_totals.py tests/test_pending_inventory.py -v   # Phase 3
pytest tests/test_ledger_payment.py -v                                   # Phase 4
pytest tests/test_e2e_sell_flow.py tests/test_e2e_exec_flow.py -v       # Phase 5
```

---

## Related Documents

- [00_instructions.md](00_instructions.md) — Master transaction architecture
- [transaction_flows.md](transaction_flows.md) — Flow diagrams and lineage
- [transaction_line_save.md](transaction_line_save.md) — Line save architecture
- [transactions-totals.md](transactions-totals.md) — Totals rollup
- [line_item_service_test_plan.md](line_item_service_test_plan.md) — LineItemService tests

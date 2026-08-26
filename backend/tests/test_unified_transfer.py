"""Tests for the unified transaction transfer engine.

Covers all three transfer modes:
  1. Clone      -- Proposal -> Proposal
  2. Convert    -- Proposal -> Order, Proposal -> Invoice (increment logic)
  3. Cross-type -- Proposal -> Purchase, Purchase -> Order

See: readmes/topics/transactions/transaction_transfer.md
"""
import pytest
from apps.transactions.models import (
    Proposal, ProposalLine,
    Order, OrderLine,
    Invoice, InvoiceLine,
    Purchase, PurchaseLine,
    WorkOrder, WorkOrderLine,
)
from apps.orgs.models import OrgBase
from apps.transactions.services.transfer import execute_transfer, TransferError


@pytest.fixture
def customer():
    """Create a real OrgBase so FK constraints are satisfied."""
    return OrgBase.objects.create(display_name="Test Customer", org_type="customer")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_proposal(**kw):
    defaults = {"status": "planned"}
    defaults.update(kw)
    return Proposal.objects.create(**defaults)


def _make_proposal_line(proposal, staged=10, active=0, remaining=None,
                        increment=0, **kw):
    if remaining is None:
        remaining = staged - active
    defaults = {
        "proposal": proposal,
        "item": {"description": "Widget", "sku": "WDG-100"},
        "price": {"unit": 25.0, "extended": 25.0 * staged},
        "cost": {"unit": 12.0, "extended": 12.0 * staged},
        "quantity": {
            "staged": staged,
            "active": active,
            "remaining": remaining,
            "increment": increment,
            "precision": 2,
            "is_fixed": False,
            "is_blanket": False,
        },
    }
    defaults.update(kw)
    return ProposalLine.objects.create(**defaults)


def _make_order(**kw):
    defaults = {"status": "confirmed"}
    defaults.update(kw)
    return Order.objects.create(**defaults)


def _make_order_line(order, staged=10, active=0, remaining=None, **kw):
    if remaining is None:
        remaining = staged - active
    defaults = {
        "order": order,
        "item": {"description": "Widget", "sku": "WDG-100"},
        "price": {"unit": 25.0, "extended": 25.0 * staged},
        "cost": {"unit": 12.0, "extended": 12.0 * staged},
        "quantity": {
            "staged": staged,
            "active": active,
            "remaining": remaining,
            "precision": 2,
        },
    }
    defaults.update(kw)
    return OrderLine.objects.create(**defaults)


def _make_purchase(**kw):
    defaults = {"status": "open"}
    defaults.update(kw)
    return Purchase.objects.create(**defaults)


def _make_purchase_line(purchase, staged=10, active=0, remaining=None, **kw):
    if remaining is None:
        remaining = staged - active
    defaults = {
        "purchase": purchase,
        "item": {"description": "Widget", "sku": "WDG-100"},
        "cost": {"unit": 12.0, "extended": 12.0 * staged},
        "quantity": {
            "staged": staged,
            "active": active,
            "remaining": remaining,
            "precision": 2,
        },
    }
    defaults.update(kw)
    return PurchaseLine.objects.create(**defaults)


def _make_workorder(**kw):
    defaults = {"status": "open"}
    defaults.update(kw)
    return WorkOrder.objects.create(**defaults)


def _make_workorder_line(workorder, staged=10, active=0, remaining=None, **kw):
    if remaining is None:
        remaining = staged - active
    defaults = {
        "workorder": workorder,
        "item": {"description": "Widget", "sku": "WDG-100"},
        "cost": {"unit": 12.0, "extended": 12.0 * staged},
        "quantity": {
            "staged": staged,
            "active": active,
            "remaining": remaining,
            "precision": 2,
        },
    }
    defaults.update(kw)
    return WorkOrderLine.objects.create(**defaults)


# ===================================================================
# 1. CLONE -- Proposal -> Proposal
# ===================================================================

@pytest.mark.django_db
class TestCloneProposalToProposal:

    def test_basic_clone(self):
        """Clone creates a new proposal with reset quantities.

        Note: normalize_quantity_map sets remaining = active for standalone
        lines (no children), so after save remaining == active.
        """
        prop = _make_proposal()
        # After normalization: staged=10, active=3, remaining=3
        # (remaining is always computed as active - children_active.sum, or just active if no children)
        pl = _make_proposal_line(prop, staged=10, active=3, remaining=3)

        result = execute_transfer(
            source_type="proposal",
            source_id=prop.pk,
            target_type="proposal",
        )

        assert result["success"] is True
        assert result["target_type"] == "proposal"
        assert result["lines_transferred"] == 1

        # Target proposal
        target = Proposal.objects.get(pk=result["target_id"])
        assert target.parent_model == "proposal"
        assert target.parent_id == prop.pk
        assert target.price_level == "retail"
        assert target.status == "planned"
        # Customer should NOT be set
        assert target.customer_id is None or target.customer_id == 0

        # Target line quantities -- clone resets from staged
        tl = ProposalLine.objects.get(pk=result["line_mapping"][pl.pk])
        assert tl.quantity["staged"] == 10
        assert tl.quantity["active"] == 10
        assert tl.quantity["remaining"] == 10

        # Source should be UNCHANGED
        pl.refresh_from_db()
        assert pl.quantity["active"] == 3
        assert pl.quantity["remaining"] == 3  # remaining = active (no children)

    def test_clone_preserves_item_and_price(self):
        """Clone copies item, price, cost data."""
        prop = _make_proposal()
        pl = _make_proposal_line(prop, staged=5)

        result = execute_transfer(
            source_type="proposal",
            source_id=prop.pk,
            target_type="proposal",
        )

        tl = ProposalLine.objects.get(pk=result["line_mapping"][pl.pk])
        assert tl.item["sku"] == "WDG-100"
        assert tl.price["unit"] == 25.0
        assert tl.cost["unit"] == 12.0

    def test_clone_multiple_lines(self):
        """Clone transfers all lines."""
        prop = _make_proposal()
        _make_proposal_line(prop, staged=10)
        _make_proposal_line(prop, staged=20)

        result = execute_transfer(
            source_type="proposal",
            source_id=prop.pk,
            target_type="proposal",
        )
        assert result["lines_transferred"] == 2

    def test_clone_updates_source_flow(self):
        """Source proposal gets flow.children updated."""
        prop = _make_proposal()
        _make_proposal_line(prop, staged=5)

        result = execute_transfer(
            source_type="proposal",
            source_id=prop.pk,
            target_type="proposal",
        )

        prop.refresh_from_db()
        assert {"type": "proposal", "id": result["target_id"]} in prop.flow["children"]


# ===================================================================
# 2. CONVERT -- Proposal -> Order (increment logic)
# ===================================================================

@pytest.mark.django_db
class TestConvertProposalToOrder:

    def test_increment_zero_takes_all(self, customer):
        """increment=0 -> transfer all remaining."""
        prop = _make_proposal(customer_id=customer.pk)
        pl = _make_proposal_line(prop, staged=10, active=10, remaining=10, increment=0)

        result = execute_transfer(
            source_type="proposal",
            source_id=prop.pk,
            target_type="order",
        )

        assert result["success"] is True
        order = Order.objects.get(pk=result["target_id"])
        assert order.parent_model == "proposal"
        assert order.parent_id == prop.pk
        assert order.customer_id == customer.pk
        assert order.status == "confirmed"

        ol = OrderLine.objects.get(pk=result["line_mapping"][pl.pk])
        assert ol.quantity["staged"] == 10
        assert ol.quantity["active"] == 10
        assert ol.quantity["remaining"] == 10

        # Source decremented
        pl.refresh_from_db()
        assert pl.quantity["remaining"] == 0
        assert pl.status == "transferred"

    def test_increment_less_than_remaining(self):
        """increment < remaining -> transfer exactly increment."""
        prop = _make_proposal()
        pl = _make_proposal_line(prop, staged=10, active=10, remaining=10, increment=3)

        result = execute_transfer(
            source_type="proposal",
            source_id=prop.pk,
            target_type="order",
        )

        ol = OrderLine.objects.get(pk=result["line_mapping"][pl.pk])
        assert ol.quantity["staged"] == 3
        assert ol.quantity["remaining"] == 3

        pl.refresh_from_db()
        # children_active tracks the decrement
        ca = pl.quantity.get("children_active", {})
        assert ca.get("sum") == 3
        assert pl.quantity["remaining"] == 7

    def test_increment_exceeds_remaining(self):
        """increment >= remaining -> transfer remaining.

        To set remaining < active, we need children_active to consume part of the qty.
        remaining = active - children_active.sum = 10 - 7 = 3
        """
        prop = _make_proposal()
        pl = _make_proposal_line(prop, staged=10, active=10, remaining=10, increment=5)
        # Manually set children_active to consume 7 units, leaving remaining=3
        pl.quantity["children_active"] = {"sum": 7, "lines": [{"id": 0, "active": 7}]}
        pl.quantity["remaining"] = 3
        pl.save(update_fields=["quantity"])

        result = execute_transfer(
            source_type="proposal",
            source_id=prop.pk,
            target_type="order",
        )

        ol = OrderLine.objects.get(pk=result["line_mapping"][pl.pk])
        assert ol.quantity["staged"] == 3
        assert ol.quantity["remaining"] == 3

        pl.refresh_from_db()
        assert pl.quantity["remaining"] == 0
        assert pl.status == "transferred"

    def test_skips_fully_transferred_lines(self):
        """Lines with remaining=0 are skipped.

        remaining = active - children_active.sum. To get remaining=0,
        children must consume all active qty.
        """
        prop = _make_proposal()
        exhausted = _make_proposal_line(prop, staged=10, active=10, remaining=10)
        # Set children_active to consume all 10 units
        exhausted.quantity["children_active"] = {"sum": 10, "lines": [{"id": 0, "active": 10}]}
        exhausted.quantity["remaining"] = 0
        exhausted.save(update_fields=["quantity"])
        pl2 = _make_proposal_line(prop, staged=5, active=5, remaining=5)

        result = execute_transfer(
            source_type="proposal",
            source_id=prop.pk,
            target_type="order",
        )

        assert result["lines_transferred"] == 1
        assert pl2.pk in result["line_mapping"]

    def test_copies_customer_info(self, customer):
        """Convert mode copies customer, price_level from source."""
        prop = _make_proposal(
            customer_id=customer.pk,
            price_level="wholesale",
            attention="Jane Doe",
        )
        _make_proposal_line(prop, staged=5, active=5, remaining=5)

        result = execute_transfer(
            source_type="proposal",
            source_id=prop.pk,
            target_type="order",
        )

        order = Order.objects.get(pk=result["target_id"])
        assert order.customer_id == customer.pk
        assert order.price_level == "wholesale"
        assert order.attention == "Jane Doe"

    def test_preserve_source_false_marks_converted(self):
        """When all remaining -> 0 and preserve_source=False, source -> converted."""
        prop = _make_proposal()
        _make_proposal_line(prop, staged=5, active=5, remaining=5, increment=0)

        execute_transfer(
            source_type="proposal",
            source_id=prop.pk,
            target_type="order",
            preserve_source=False,
        )

        prop.refresh_from_db()
        assert prop.status == "converted"

    def test_partial_transfer_does_not_convert_source(self):
        """When some remaining > 0, source stays unconverted."""
        prop = _make_proposal()
        _make_proposal_line(prop, staged=10, active=10, remaining=10, increment=3)

        execute_transfer(
            source_type="proposal",
            source_id=prop.pk,
            target_type="order",
            preserve_source=False,
        )

        prop.refresh_from_db()
        assert prop.status != "converted"


# ===================================================================
# 3. CONVERT -- Proposal -> Invoice
# ===================================================================

@pytest.mark.django_db
class TestConvertProposalToInvoice:

    def test_proposal_to_invoice_basic(self, customer):
        """Direct proposal->invoice with increment logic."""
        prop = _make_proposal(customer_id=customer.pk)
        pl = _make_proposal_line(prop, staged=8, active=8, remaining=8, increment=0)

        result = execute_transfer(
            source_type="proposal",
            source_id=prop.pk,
            target_type="invoice",
        )

        assert result["success"] is True
        inv = Invoice.objects.get(pk=result["target_id"])
        assert inv.parent_model == "proposal"
        assert inv.parent_id == prop.pk
        assert inv.customer_id == customer.pk
        assert inv.status == "pending"

        il = InvoiceLine.objects.get(pk=result["line_mapping"][pl.pk])
        assert il.quantity["staged"] == 8
        assert il.quantity["remaining"] == 8
        # Invoice lines should have price copied
        assert il.price["unit"] == 25.0


# ===================================================================
# 4. CROSS-TYPE -- Proposal -> Purchase
# ===================================================================

@pytest.mark.django_db
class TestCrossTypeProposalToPurchase:

    def test_cross_type_basic(self, customer):
        """Cross-type copies full staged qty, no customer."""
        prop = _make_proposal(customer_id=customer.pk)
        # After normalization: remaining = active = 3 (no children)
        pl = _make_proposal_line(prop, staged=10, active=3, remaining=3)

        result = execute_transfer(
            source_type="proposal",
            source_id=prop.pk,
            target_type="purchase",
        )

        assert result["success"] is True
        po = Purchase.objects.get(pk=result["target_id"])
        assert po.parent_model == "proposal"
        assert po.parent_id == prop.pk
        # Customer NOT copied for cross-type
        assert po.customer_id is None or po.customer_id == 0
        assert po.status == "open"

        pol = PurchaseLine.objects.get(pk=result["line_mapping"][pl.pk])
        assert pol.quantity["staged"] == 10
        assert pol.quantity["active"] == 10
        assert pol.quantity["remaining"] == 10

        # Source NOT decremented for cross-type
        pl.refresh_from_db()
        assert pl.quantity["active"] == 3  # unchanged
        assert pl.quantity["remaining"] == 3  # unchanged (remaining = active, no children)

    def test_cross_purchase_line_has_no_price(self):
        """Purchase lines (BaseExecLineModel) should not have price."""
        prop = _make_proposal()
        _make_proposal_line(prop, staged=5, active=5, remaining=5)

        result = execute_transfer(
            source_type="proposal",
            source_id=prop.pk,
            target_type="purchase",
        )
        pol = PurchaseLine.objects.get(
            pk=list(result["line_mapping"].values())[0]
        )
        # PurchaseLine inherits BaseExecLineModel -- no price field
        assert not hasattr(pol, "price") or getattr(pol, "price", None) is None


# ===================================================================
# 5. CROSS-TYPE -- Purchase -> Order
# ===================================================================

@pytest.mark.django_db
class TestCrossTypePurchaseToOrder:

    def test_purchase_to_order(self):
        """Purchase -> Order is a cross-type transfer."""
        po = _make_purchase()
        pol = _make_purchase_line(po, staged=20, active=20, remaining=20)

        result = execute_transfer(
            source_type="purchase",
            source_id=po.pk,
            target_type="order",
        )

        assert result["success"] is True
        order = Order.objects.get(pk=result["target_id"])
        assert order.parent_model == "purchase"
        assert order.parent_id == po.pk
        assert order.status == "confirmed"

        ol = OrderLine.objects.get(pk=result["line_mapping"][pol.pk])
        assert ol.quantity["staged"] == 20
        assert ol.quantity["active"] == 20
        assert ol.quantity["remaining"] == 20


# ===================================================================
# 5b. WORKORDER TRANSFER MATRIX SUPPORT
# ===================================================================

@pytest.mark.django_db
class TestWorkOrderTransferSupport:

    def test_order_to_workorder(self):
        order = _make_order()
        ol = _make_order_line(order, staged=6, active=6, remaining=6)

        result = execute_transfer(
            source_type="order",
            source_id=order.pk,
            target_type="workorder",
        )

        assert result["success"] is True
        wo = WorkOrder.objects.get(pk=result["target_id"])
        assert wo.parent_model == "order"
        assert wo.parent_id == order.pk

        wol = WorkOrderLine.objects.get(pk=result["line_mapping"][ol.pk])
        assert wol.quantity["staged"] == 6

    def test_workorder_to_invoice(self):
        wo = _make_workorder()
        wol = _make_workorder_line(wo, staged=4, active=4, remaining=4)

        result = execute_transfer(
            source_type="workorder",
            source_id=wo.pk,
            target_type="invoice",
        )

        assert result["success"] is True
        inv = Invoice.objects.get(pk=result["target_id"])
        assert inv.parent_model == "workorder"
        assert inv.parent_id == wo.pk

        il = InvoiceLine.objects.get(pk=result["line_mapping"][wol.pk])
        assert il.quantity["staged"] == 4


# ===================================================================
# 6. LINEAGE TRACKING
# ===================================================================

@pytest.mark.django_db
class TestLineageTracking:

    def test_refs_source_on_target_line(self):
        """Target line has refs.source with source line/header IDs."""
        prop = _make_proposal()
        pl = _make_proposal_line(prop, staged=5, active=5, remaining=5)

        result = execute_transfer(
            source_type="proposal",
            source_id=prop.pk,
            target_type="order",
        )

        ol = OrderLine.objects.get(pk=result["line_mapping"][pl.pk])
        assert ol.refs["source"]["proposal_line_id"] == pl.pk
        assert ol.refs["source"]["proposal_id"] == prop.pk

    def test_refs_xfer_audit_trail(self):
        """Target line has refs.xfer audit payload."""
        prop = _make_proposal()
        pl = _make_proposal_line(prop, staged=5, active=5, remaining=5)

        result = execute_transfer(
            source_type="proposal",
            source_id=prop.pk,
            target_type="order",
        )

        ol = OrderLine.objects.get(pk=result["line_mapping"][pl.pk])
        xfer = ol.refs["xfer"]
        assert isinstance(xfer, list)
        assert len(xfer) >= 1
        assert xfer[0]["source"]["kind"] == "proposal"
        assert xfer[0]["source"]["line_id"] == pl.pk

    def test_flow_on_target_header(self):
        """Target header has flow.source pointing back to source."""
        prop = _make_proposal()
        _make_proposal_line(prop, staged=5, active=5, remaining=5)

        result = execute_transfer(
            source_type="proposal",
            source_id=prop.pk,
            target_type="order",
        )

        order = Order.objects.get(pk=result["target_id"])
        assert order.flow["source"] == [{"type": "proposal", "id": prop.pk}]

    def test_metadata_parent_link(self):
        """Target line metadata has parent_link."""
        prop = _make_proposal()
        pl = _make_proposal_line(prop, staged=8, active=8, remaining=8)

        result = execute_transfer(
            source_type="proposal",
            source_id=prop.pk,
            target_type="order",
        )

        ol = OrderLine.objects.get(pk=result["line_mapping"][pl.pk])
        link = ol.metadata["parent_link"]
        assert link["parent_model"] == "proposal"
        assert link["quantity_at_parent"]["staged"] == 8


# ===================================================================
# 7. ERROR HANDLING
# ===================================================================

@pytest.mark.django_db
class TestTransferErrors:

    def test_source_not_found(self):
        with pytest.raises(TransferError, match="Source not found"):
            execute_transfer(
                source_type="proposal",
                source_id=999999,
                target_type="order",
            )

    def test_unsupported_transfer(self):
        order = _make_order()
        with pytest.raises(TransferError, match="Unsupported transfer"):
            execute_transfer(
                source_type="order",
                source_id=order.pk,
                target_type="order",
            )

    def test_no_lines_to_transfer(self):
        """Proposal with no lines raises error."""
        prop = _make_proposal()
        with pytest.raises(TransferError, match="No lines"):
            execute_transfer(
                source_type="proposal",
                source_id=prop.pk,
                target_type="order",
            )

    def test_all_lines_exhausted(self):
        """All lines with remaining=0 raises 'No lines to transfer'."""
        prop = _make_proposal()
        exhausted = _make_proposal_line(prop, staged=10, active=10, remaining=10)
        # Set children_active to consume all 10 units
        exhausted.quantity["children_active"] = {"sum": 10, "lines": [{"id": 0, "active": 10}]}
        exhausted.quantity["remaining"] = 0
        exhausted.save(update_fields=["quantity"])

        with pytest.raises(TransferError, match="No lines"):
            execute_transfer(
                source_type="proposal",
                source_id=prop.pk,
                target_type="order",
            )

    def test_unknown_source_type(self):
        with pytest.raises(TransferError, match="Unknown source type"):
            execute_transfer(
                source_type="widget",
                source_id=1,
                target_type="order",
            )

    def test_invalid_line_ids(self):
        prop = _make_proposal()
        _make_proposal_line(prop, staged=5, active=5, remaining=5)

        with pytest.raises((TransferError, ValueError)):
            execute_transfer(
                source_type="proposal",
                source_id=prop.pk,
                target_type="order",
                line_ids=[999999],
                transfer_all=False,
            )


# ===================================================================
# 8. SELECTED LINES
# ===================================================================

@pytest.mark.django_db
class TestSelectiveTransfer:

    def test_transfer_specific_lines(self):
        """Only transfer the specified line IDs."""
        prop = _make_proposal()
        pl1 = _make_proposal_line(prop, staged=10, active=10, remaining=10)
        pl2 = _make_proposal_line(prop, staged=20, active=20, remaining=20)

        result = execute_transfer(
            source_type="proposal",
            source_id=prop.pk,
            target_type="order",
            line_ids=[pl1.pk],
            transfer_all=False,
        )

        assert result["lines_transferred"] == 1
        assert pl1.pk in result["line_mapping"]
        assert pl2.pk not in result["line_mapping"]

    def test_custom_target_status(self):
        """Override the default target status."""
        prop = _make_proposal()
        _make_proposal_line(prop, staged=5, active=5, remaining=5)

        result = execute_transfer(
            source_type="proposal",
            source_id=prop.pk,
            target_type="order",
            target_status="hold",
        )

        order = Order.objects.get(pk=result["target_id"])
        assert order.status == "hold"

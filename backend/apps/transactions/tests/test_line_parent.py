"""Parent-child line quantities — readmes/transactions/line-quantity.md

proposal_line -> order_line and order_line -> invoice_line only.
parent.remaining = parent.active − Σ children.active, recomputed on every child
create / edit / delete, whatever path saved the child.
"""
import pytest

from apps.products.models import Item
from apps.transactions.models import (
    Invoice, InvoiceLine, Order, OrderLine, Proposal, ProposalLine, Purchase, PurchaseLine,
)
from apps.transactions.services.line_parent import parent_quantities


def _q(line):
    line.refresh_from_db()
    return line.quantity


@pytest.fixture
def item(db):
    return Item.objects.create(name="Parent Test Item", ida="PARENT-001")


@pytest.fixture
def order_line(item):
    order = Order.objects.create(status="draft")
    return OrderLine.objects.create(order=order, item_fk=item, quantity={"active": 10})


def _invoice_line(item, order_line, active):
    invoice = Invoice.objects.create(status="draft")
    return InvoiceLine.objects.create(
        invoice=invoice, item_fk=item, quantity={"active": active},
        refs={"source": {"order_line_id": order_line.pk}},
    )


@pytest.mark.django_db
class TestWorkedExample:
    """The worked example in line-quantity.md, step by step."""

    def test_order_invoice_lifecycle(self, item, order_line):
        assert _q(order_line)["remaining"] == 10

        inv_a = _invoice_line(item, order_line, 6)
        assert inv_a.parent_line_id == order_line.pk
        assert _q(order_line)["remaining"] == 4

        inv_b = _invoice_line(item, order_line, 3)
        assert _q(order_line)["remaining"] == 1

        # Short ship: staged snapshot stays 3, active 2
        inv_b.quantity = {**inv_b.quantity, "active": 2}
        inv_b.save()
        assert _q(inv_b)["staged"] == 3
        assert _q(order_line)["remaining"] == 2

        inv_a.delete()
        assert _q(order_line)["remaining"] == 8

        order_line.refresh_from_db()
        order_line.quantity = {**order_line.quantity, "is_complete": True}
        order_line.save()
        assert _q(order_line)["remaining"] == 0


@pytest.mark.django_db
class TestStatus:
    def test_transferred_when_children_consume_all_and_reopens(self, item, order_line):
        inv = _invoice_line(item, order_line, 10)
        order_line.refresh_from_db()
        assert order_line.status == "transferred"

        inv.quantity = {**inv.quantity, "active": 7}
        inv.save()
        order_line.refresh_from_db()
        assert order_line.status == ""
        assert order_line.quantity["remaining"] == 3

    def test_delete_last_child_reopens(self, item, order_line):
        inv = _invoice_line(item, order_line, 10)
        inv.delete()
        order_line.refresh_from_db()
        assert order_line.status == ""
        assert order_line.quantity["remaining"] == 10


@pytest.mark.django_db
class TestSignedQuantities:
    def test_negative_parent_and_children(self, item):
        order = Order.objects.create(status="draft")
        ol = OrderLine.objects.create(order=order, item_fk=item, quantity={"active": -10})
        _invoice_line(item, ol, -6)
        assert _q(ol)["remaining"] == -4
        _invoice_line(item, ol, -4)
        ol.refresh_from_db()
        assert ol.quantity["remaining"] == 0
        assert ol.status == "transferred"

    def test_over_transfer_is_not_floored(self, item, order_line):
        _invoice_line(item, order_line, 12)
        order_line.refresh_from_db()
        assert order_line.quantity["remaining"] == -2
        assert order_line.status != "transferred"


@pytest.mark.django_db
class TestProposalToOrder:
    def test_order_line_consumes_proposal_line(self, item):
        proposal = Proposal.objects.create(status="draft")
        pl = ProposalLine.objects.create(proposal=proposal, item_fk=item, quantity={"active": 5})
        order = Order.objects.create(status="draft")
        ol = OrderLine.objects.create(
            order=order, item_fk=item, quantity={"active": 5},
            refs={"source": {"proposal_line_id": pl.pk}},
        )
        assert ol.parent_line_id == pl.pk
        pl.refresh_from_db()
        assert pl.quantity["remaining"] == 0
        assert pl.status == "transferred"

    def test_invoice_edit_reaches_order_not_proposal(self, item):
        """One level per event: an invoice edit does not touch the proposal line."""
        proposal = Proposal.objects.create(status="draft")
        pl = ProposalLine.objects.create(proposal=proposal, item_fk=item, quantity={"active": 5})
        order = Order.objects.create(status="draft")
        ol = OrderLine.objects.create(
            order=order, item_fk=item, quantity={"active": 5},
            refs={"source": {"proposal_line_id": pl.pk}},
        )
        pl.refresh_from_db()
        proposal_version = pl.version

        inv = _invoice_line(item, ol, 2)
        inv.quantity = {**inv.quantity, "active": 1}
        inv.save()

        pl.refresh_from_db()
        assert pl.version == proposal_version
        assert _q(ol)["remaining"] == 4


@pytest.mark.django_db
class TestOnlyTwoPairs:
    def test_invoice_from_proposal_is_not_a_child(self, item):
        proposal = Proposal.objects.create(status="draft")
        pl = ProposalLine.objects.create(proposal=proposal, item_fk=item, quantity={"active": 5})
        invoice = Invoice.objects.create(status="draft")
        inv = InvoiceLine.objects.create(
            invoice=invoice, item_fk=item, quantity={"active": 5},
            refs={"source": {"proposal_line_id": pl.pk}},
        )
        assert inv.parent_line_id is None
        assert _q(pl)["remaining"] == 5

    def test_purchase_from_order_is_not_a_child(self, item, order_line):
        purchase = Purchase.objects.create(status="draft")
        pol = PurchaseLine.objects.create(
            purchase=purchase, item_fk=item, quantity={"active": 10},
            refs={"source": {"order_line_id": order_line.pk}},
        )
        assert pol.parent_line_id is None
        order_line.refresh_from_db()
        assert order_line.quantity["remaining"] == 10
        assert order_line.status != "transferred"

    def test_invoice_with_both_ids_takes_order_line(self, item, order_line):
        invoice = Invoice.objects.create(status="draft")
        inv = InvoiceLine.objects.create(
            invoice=invoice, item_fk=item, quantity={"active": 4},
            refs={"source": {"order_line_id": order_line.pk, "proposal_line_id": 999999}},
        )
        assert inv.parent_line_id == order_line.pk
        assert _q(order_line)["remaining"] == 6


@pytest.mark.django_db
class TestReadsNeverWrite:
    def test_child_save_without_active_change_leaves_parent_untouched(self, item, order_line):
        inv = _invoice_line(item, order_line, 6)
        order_line.refresh_from_db()
        version = order_line.version

        inv.refresh_from_db()
        inv.comments = {"note": "no quantity change"}
        inv.save()

        order_line.refresh_from_db()
        assert order_line.version == version

    def test_parent_quantities_for_edit_open(self, item, order_line):
        inv = _invoice_line(item, order_line, 6)
        assert parent_quantities(inv) == {"parent_active": 10.0, "parent_remaining": 4.0}
        order_line.refresh_from_db()
        assert parent_quantities(order_line) is None  # standalone: no parent

"""
Chain Verification: Proposal → Order → Invoice(s)

Creates the exact 7-step chain from the user's example using
customer_id=82 and item_id=243, verifying parent_line_id links, parent remaining
(active − Σ children.active, children summed by query) and parent status at each step.

Expected chain:
  Step 1: Create proposal      → staged=15, active=15, remaining=15
  Step 2: Create child order   → staged=15, active=15, remaining=15
                                  proposal remaining→0  (Σ children.active=15)
  Step 3: Edit order active→7  → staged=15, active=7,  remaining=7
                                  proposal remaining→8  (Σ children.active=7)
  Step 4: Create invoice #1    → staged=7,  active=7,  remaining=7
                                  order remaining→0     (Σ children.active=7)
  Step 5: Edit invoice1 active→3 → staged=7, active=3, remaining=3
                                  order remaining→4     (Σ children.active=3)
  Step 6: Create invoice #2    → staged=4,  active=4,  remaining=4
                                  order remaining→0     (Σ children.active=7)
  Step 7: Edit invoice2 active→1 → staged=4, active=1, remaining=1
                                  order remaining→3     (Σ children.active=4)

Run:
    cd webClerk3
    python -m pytest apps/transactions/tests/test_chain_verification.py -v --no-header -o "addopts="
"""
import pytest
from decimal import Decimal

pytestmark = pytest.mark.django_db(transaction=True)


CUSTOMER_ID = 82
ITEM_ID = 243


def _qty(line):
    """Extract quantity dict from a line object."""
    return dict(getattr(line, 'quantity', {}) or {})


def _print_qty(label, q):
    print(f"  {label}: staged={q.get('staged')}, active={q.get('active')}, remaining={q.get('remaining')}")


def _children(ChildModel, parent_line_pk):
    """Children of a parent line, found by query on parent_line_id (no stored copy)."""
    rows = list(ChildModel.objects.filter(parent_line_id=parent_line_pk))
    return sum(float(r.quantity.get('active', 0)) for r in rows), [r.pk for r in rows]


class TestProposalOrderInvoiceChain:
    """Full chain verification: Proposal → Order → Invoice(s)."""

    def test_full_chain(self):
        from apps.transactions.models import (
            Proposal, ProposalLine,
            Order, OrderLine,
            Invoice, InvoiceLine,
        )
        from apps.products.models import Item
        from apps.transactions.services.transaction_save import (
            save_transaction_with_lines,
        )

        # Ensure item exists (create if needed in test DB)
        from apps.orgs.models.base import OrgBase
        try:
            item = Item.objects.get(pk=ITEM_ID)
            item_ida = item.ida or item.sku or item.name or str(ITEM_ID)
        except Item.DoesNotExist:
            # Create a test item with sufficient inventory
            item = Item.objects.create(
                pk=ITEM_ID,
                name="Test Chain Item",
                ida="CHAIN-TEST-243",
                sku="CHAIN-243",
                quantity={
                    'on_hand': 100.0,
                    'available': 100.0,
                    'on_so': 0,
                    'on_po': 0,
                },
            )
            item_ida = item.ida

        # Ensure customer exists
        try:
            OrgBase.objects.get(pk=CUSTOMER_ID)
        except OrgBase.DoesNotExist:
            OrgBase.objects.create(
                pk=CUSTOMER_ID,
                display_name="Test Customer 82",
                org_type="customer",
            )

        # ── Step 1: Create Proposal with qty=15 ──────────────────────
        print("\n═══ Step 1: Create Proposal (qty=15) ═══")
        proposal_result = save_transaction_with_lines(
            model_key='proposal',
            header_data={
                'status': 'planned',
                'customer_id': CUSTOMER_ID,
            },
            lines_data=[{
                '_dirty': True,
                'item': {'item_id': ITEM_ID, 'ida': item_ida},
                'quantity': {'staged': 15, 'active': 15},
                'price': {'unit': 10.0, 'extended': 150.0},
                'cost': {'unit': 5.0, 'extended': 75.0},
            }],
            request=None,
            verify_calculations=False,
            save_only_dirty=False,
        )
        proposal_id = proposal_result['header']['id']
        proposal_line_id = proposal_result['lines'][0]['id']
        print(f"  Proposal #{proposal_id}, line #{proposal_line_id}")

        pl = ProposalLine.objects.get(pk=proposal_line_id)
        pq = _qty(pl)
        _print_qty("Proposal line", pq)

        assert pq['staged'] == 15.0
        assert pq['active'] == 15.0
        assert pq['remaining'] == 15.0

        # ── Step 2: Create child Order from proposal.remaining=15 ────
        print("\n═══ Step 2: Create Child Order (staged=15 from proposal) ═══")
        order_result = save_transaction_with_lines(
            model_key='order',
            header_data={
                'status': 'planned',
                'customer_id': CUSTOMER_ID,
                'parent_id': proposal_id,
                'parent_model': 'proposal',
            },
            lines_data=[{
                '_dirty': True,
                'item': {'item_id': ITEM_ID, 'ida': item_ida},
                'quantity': {'staged': 15, 'active': 15},
                'price': {'unit': 10.0, 'extended': 150.0},
                'cost': {'unit': 5.0, 'extended': 75.0},
                'refs': {
                    'source': {
                        'proposal_line_id': proposal_line_id,
                        'proposal_id': proposal_id,
                        'converted_from': 'proposal',
                    }
                },
            }],
            request=None,
            verify_calculations=False,
            save_only_dirty=False,
        )
        order_id = order_result['header']['id']
        order_line_id = order_result['lines'][0]['id']
        print(f"  Order #{order_id}, line #{order_line_id}")

        ol = OrderLine.objects.get(pk=order_line_id)
        oq = _qty(ol)
        _print_qty("Order line", oq)

        assert oq['staged'] == 15.0
        assert oq['active'] == 15.0
        assert oq['remaining'] == 15.0

        # Check proposal line was updated
        pl.refresh_from_db()
        pq = _qty(pl)
        _print_qty("Proposal line (after transfer)", pq)

        assert ol.parent_line_id == proposal_line_id
        assert pq['remaining'] == 0.0, f"Expected proposal remaining=0, got {pq['remaining']}"
        total, ids = _children(OrderLine, proposal_line_id)
        assert total == 15.0, f"Expected Σ children.active=15, got {total}"
        assert ids == [order_line_id]
        assert pl.status == 'transferred', f"Expected proposal line transferred, got {pl.status!r}"
        assert 'children_active' not in pq

        # ── Step 3: User reduces order active to 7 ───────────────────
        print("\n═══ Step 3: Edit Order active 15→7 ═══")
        save_transaction_with_lines(
            model_key='order',
            header_data={'id': order_id, 'status': 'planned'},
            lines_data=[{
                'id': order_line_id,
                '_dirty': True,
                'item': {'item_id': ITEM_ID, 'ida': item_ida},
                'quantity': {'staged': 15, 'active': 7},
                'price': {'unit': 10.0, 'extended': 70.0},
                'cost': {'unit': 5.0, 'extended': 35.0},
            }],
            request=None,
            verify_calculations=False,
            save_only_dirty=False,
        )

        ol.refresh_from_db()
        oq = _qty(ol)
        _print_qty("Order line (after edit)", oq)

        assert oq['staged'] == 15.0
        assert oq['active'] == 7.0
        assert oq['remaining'] == 7.0

        # Check proposal remaining updated
        pl.refresh_from_db()
        pq = _qty(pl)
        _print_qty("Proposal line (after order edit)", pq)

        assert pq['remaining'] == 8.0, f"Expected proposal remaining=8, got {pq['remaining']}"
        assert _children(OrderLine, proposal_line_id)[0] == 7.0
        assert pl.status != 'transferred', "Proposal line should reopen when backlog returns"

        # ── Step 4: Create Invoice #1 from order.remaining=7 ─────────
        print("\n═══ Step 4: Create Invoice #1 (staged=7 from order) ═══")
        inv1_result = save_transaction_with_lines(
            model_key='invoice',
            header_data={
                'status': 'planned',
                'customer_id': CUSTOMER_ID,
                'parent_id': order_id,
                'parent_model': 'order',
            },
            lines_data=[{
                '_dirty': True,
                'item': {'item_id': ITEM_ID, 'ida': item_ida},
                'quantity': {'staged': 7, 'active': 7},
                'price': {'unit': 10.0, 'extended': 70.0},
                'cost': {'unit': 5.0, 'extended': 35.0},
                'refs': {
                    'source': {
                        'order_line_id': order_line_id,
                        'order_id': order_id,
                        'converted_from': 'order',
                    }
                },
            }],
            request=None,
            verify_calculations=False,
            save_only_dirty=False,
        )
        inv1_id = inv1_result['header']['id']
        inv1_line_id = inv1_result['lines'][0]['id']
        print(f"  Invoice #1: #{inv1_id}, line #{inv1_line_id}")

        il1 = InvoiceLine.objects.get(pk=inv1_line_id)
        iq1 = _qty(il1)
        _print_qty("Invoice #1 line", iq1)

        assert iq1['staged'] == 7.0
        assert iq1['active'] == 7.0

        # Check order remaining updated
        ol.refresh_from_db()
        oq = _qty(ol)
        _print_qty("Order line (after invoice #1)", oq)

        assert il1.parent_line_id == order_line_id
        assert oq['remaining'] == 0.0, f"Expected order remaining=0, got {oq['remaining']}"
        assert _children(InvoiceLine, order_line_id)[0] == 7.0
        assert ol.status == 'transferred'
        # One level per event: the invoice does not reach the proposal
        pl.refresh_from_db()
        assert _qty(pl)['remaining'] == 8.0

        # ── Step 5: User reduces invoice #1 active to 3 ─────────────
        print("\n═══ Step 5: Edit Invoice #1 active 7→3 ═══")
        save_transaction_with_lines(
            model_key='invoice',
            header_data={'id': inv1_id, 'status': 'planned'},
            lines_data=[{
                'id': inv1_line_id,
                '_dirty': True,
                'item': {'item_id': ITEM_ID, 'ida': item_ida},
                'quantity': {'staged': 7, 'active': 3},
                'price': {'unit': 10.0, 'extended': 30.0},
                'cost': {'unit': 5.0, 'extended': 15.0},
            }],
            request=None,
            verify_calculations=False,
            save_only_dirty=False,
        )

        il1.refresh_from_db()
        iq1 = _qty(il1)
        _print_qty("Invoice #1 line (after edit)", iq1)

        assert iq1['active'] == 3.0

        # Check order remaining updated
        ol.refresh_from_db()
        oq = _qty(ol)
        _print_qty("Order line (after invoice #1 edit)", oq)

        assert iq1['staged'] == 7.0, "staged is a creation snapshot; edits never move it"
        assert oq['remaining'] == 4.0, f"Expected order remaining=4, got {oq['remaining']}"
        assert _children(InvoiceLine, order_line_id)[0] == 3.0
        assert ol.status != 'transferred'

        # ── Step 6: Create Invoice #2 from order.remaining=4 ─────────
        print("\n═══ Step 6: Create Invoice #2 (staged=4 from order) ═══")
        inv2_result = save_transaction_with_lines(
            model_key='invoice',
            header_data={
                'status': 'planned',
                'customer_id': CUSTOMER_ID,
                'parent_id': order_id,
                'parent_model': 'order',
            },
            lines_data=[{
                '_dirty': True,
                'item': {'item_id': ITEM_ID, 'ida': item_ida},
                'quantity': {'staged': 4, 'active': 4},
                'price': {'unit': 10.0, 'extended': 40.0},
                'cost': {'unit': 5.0, 'extended': 20.0},
                'refs': {
                    'source': {
                        'order_line_id': order_line_id,
                        'order_id': order_id,
                        'converted_from': 'order',
                    }
                },
            }],
            request=None,
            verify_calculations=False,
            save_only_dirty=False,
        )
        inv2_id = inv2_result['header']['id']
        inv2_line_id = inv2_result['lines'][0]['id']
        print(f"  Invoice #2: #{inv2_id}, line #{inv2_line_id}")

        il2 = InvoiceLine.objects.get(pk=inv2_line_id)
        iq2 = _qty(il2)
        _print_qty("Invoice #2 line", iq2)

        assert iq2['staged'] == 4.0
        assert iq2['active'] == 4.0

        # Check order remaining — now has TWO children: inv1(3) + inv2(4) = 7
        ol.refresh_from_db()
        oq = _qty(ol)
        _print_qty("Order line (after invoice #2)", oq)

        assert oq['remaining'] == 0.0, f"Expected order remaining=0, got {oq['remaining']}"
        total, ids = _children(InvoiceLine, order_line_id)
        assert total == 7.0, f"Expected Σ children.active=7 (3+4), got {total}"
        assert sorted(ids) == sorted([inv1_line_id, inv2_line_id])
        assert ol.status == 'transferred'

        # ── Step 7: User reduces invoice #2 active to 1 ─────────────
        print("\n═══ Step 7: Edit Invoice #2 active 4→1 ═══")
        save_transaction_with_lines(
            model_key='invoice',
            header_data={'id': inv2_id, 'status': 'planned'},
            lines_data=[{
                'id': inv2_line_id,
                '_dirty': True,
                'item': {'item_id': ITEM_ID, 'ida': item_ida},
                'quantity': {'staged': 4, 'active': 1},
                'price': {'unit': 10.0, 'extended': 10.0},
                'cost': {'unit': 5.0, 'extended': 5.0},
            }],
            request=None,
            verify_calculations=False,
            save_only_dirty=False,
        )

        il2.refresh_from_db()
        iq2 = _qty(il2)
        _print_qty("Invoice #2 line (after edit)", iq2)

        assert iq2['active'] == 1.0

        # Check order remaining — children: inv1(3) + inv2(1) = 4, remaining = 7 - 4 = 3
        ol.refresh_from_db()
        oq = _qty(ol)
        _print_qty("Order line (after invoice #2 edit)", oq)

        assert oq['remaining'] == 3.0, f"Expected order remaining=3, got {oq['remaining']}"
        assert _children(InvoiceLine, order_line_id)[0] == 4.0
        assert ol.status != 'transferred'

        # ── Final state summary ──────────────────────────────────────
        print("\n═══ Final State ═══")
        pl.refresh_from_db()
        ol.refresh_from_db()
        il1.refresh_from_db()
        il2.refresh_from_db()

        _print_qty(f"Proposal #{proposal_id} line #{proposal_line_id}", _qty(pl))
        _print_qty(f"Order #{order_id} line #{order_line_id}", _qty(ol))
        _print_qty(f"Invoice #1 #{inv1_id} line #{inv1_line_id}", _qty(il1))
        _print_qty(f"Invoice #2 #{inv2_id} line #{inv2_line_id}", _qty(il2))

        print("\n✓ All 7 steps verified successfully!")

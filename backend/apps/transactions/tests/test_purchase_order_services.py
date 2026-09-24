from decimal import Decimal
from django.test import TestCase
from apps.transactions.models import Purchase, PurchaseLine, Order, OrderLine
from apps.transactions.services.convert.convert import convert_order_to_purchase
from apps.orgs.models import OrgBase


class PurchaseTotalsServiceTest(TestCase):
    """Test cases for unified totals engine on Purchase."""

    def setUp(self):
        """Set up test data."""
        self.customer = OrgBase.objects.create(
            company="John Doe",
            org_type="customer"
        )
        self.purchase = Purchase.objects.create(
            status="planned",
            customer_id=self.customer.id
        )

    def test_compute_totals_empty_order(self):
        """Test computing totals for an empty purchase."""
        self.purchase.update_sell_cost_totals(persist=True)
        self.purchase.refresh_from_db()

        totals = self.purchase.totals
        self.assertEqual(totals['amount'], 0.0)
        self.assertEqual(totals['total'], 0.0)
        self.assertEqual(totals['cost'], 0.0)
        self.assertEqual(totals['margin'], 0.0)

    def test_compute_totals_with_lines(self):
        """Test computing totals with line items."""
        # Create line items
        PurchaseLine.objects.create(
            purchase=self.purchase,
            item={'description': 'Item 1'},
            quantity={'staged': 2},
            cost={'unit': 8.00, 'extended': 16.00}
        )
        PurchaseLine.objects.create(
            purchase=self.purchase,
            item={'description': 'Item 2'},
            quantity={'staged': 1},
            cost={'unit': 12.00, 'extended': 12.00}
        )

        self.purchase.update_sell_cost_totals(persist=True)
        self.purchase.refresh_from_db()

        totals = self.purchase.totals
        self.assertIn('amount', totals)
        self.assertIn('total', totals)
        self.assertIn('cost', totals)

    def test_compute_totals_with_additional_costs(self):
        """Test computing totals with additional cost components."""
        PurchaseLine.objects.create(
            purchase=self.purchase,
            item={'description': 'Item 1'},
            quantity={'staged': 1},
            cost={
                'unit': 80.00,
                'extended': 80.00,
                'shipping': 5.00,
                'handling': 2.00,
            }
        )

        self.purchase.update_sell_cost_totals(persist=True)
        self.purchase.refresh_from_db()

        totals = self.purchase.totals
        self.assertIn('amount', totals)
        self.assertIn('total', totals)
        self.assertIn('cost', totals)


class OrderToPurchaseServiceTest(TestCase):
    """Test cases for order to purchase transfer service."""

    def setUp(self):
        """Set up test data."""
        self.customer = OrgBase.objects.create(
            company="John Doe",
            org_type="customer"
        )
        self.vendor = OrgBase.objects.create(
            company="Jane Smith",
            org_type="vendor"
        )
        self.order = Order.objects.create(
            status="released",
            customer_id=self.customer.id
        )

    def test_transfer_order_to_purchase_basic(self):
        """One purchase from an order, its lines back for review (the one engine, plan
        §14a.4: the old vendor grouping and customer link were dropped deliberately)."""
        OrderLine.objects.create(
            order=self.order,
            item={'description': 'Item 1'},
            quantity={'staged': 2, 'active': 2},
            price={'unit': 10.00},
            cost={'unit': 8.00}
        )

        result = convert_order_to_purchase(self.order.pk, vendor_id=self.vendor.id)

        po = Purchase.objects.get(id=result['purchase_id'])
        self.assertEqual(po.status, "planned")
        self.assertEqual((po.parent_model, po.parent_id), ("order", self.order.id))
        self.assertEqual(po.vendor_id, self.vendor.id)
        self.assertEqual(result['lines_for_review'], 1)
        self.assertEqual(result['lines'][0]['quantity']['active'], 2)
        self.assertEqual(po.lines.count(), 0, "lines are created when the reviewed PO is saved")

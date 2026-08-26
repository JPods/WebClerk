from decimal import Decimal
from django.test import TestCase
from apps.transactions.models import Purchase, PurchaseLine, Order, OrderLine
from apps.transactions.services.order_to_purchase import transfer_order_to_purchase
from apps.orgs.models import OrgBase


class PurchaseTotalsServiceTest(TestCase):
    """Test cases for unified totals engine on Purchase."""

    def setUp(self):
        """Set up test data."""
        self.customer = OrgBase.objects.create(
            display_name="John Doe",
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
        self.assertEqual(totals['subtotal'], 0.0)
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
        self.assertIn('subtotal', totals)
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
        self.assertIn('subtotal', totals)
        self.assertIn('total', totals)
        self.assertIn('cost', totals)


class OrderToPurchaseServiceTest(TestCase):
    """Test cases for order to purchase transfer service."""

    def setUp(self):
        """Set up test data."""
        self.customer = OrgBase.objects.create(
            display_name="John Doe",
            org_type="customer"
        )
        self.vendor = OrgBase.objects.create(
            display_name="Jane Smith",
            org_type="vendor"
        )
        self.order = Order.objects.create(
            status="released",
            customer_id=self.customer.id
        )

    def test_transfer_order_to_purchase_basic(self):
        """Test basic transfer from order to purchase order."""
        # Create order lines
        OrderLine.objects.create(
            order=self.order,
            item={'description': 'Item 1'},
            quantity={'staged': 2},
            price={'unit': 10.00},
            cost={'unit': 8.00}
        )

        result = transfer_order_to_purchase(
            order=self.order,
            group_by_vendor=False,
            transfer_all=True
        )

        self.assertTrue(result['success'])
        self.assertEqual(len(result['purchase_ids']), 1)
        self.assertEqual(result['lines_transferred'], 1)

        # Check PO was created
        po = Purchase.objects.get(id=result['purchase_ids'][0])
        self.assertEqual(po.status, "planned")
        self.assertEqual(po.customer_id, self.customer.id)
        self.assertEqual(po.refs['source']['order_id'], self.order.id)

        # Check PO line was created
        po_lines = po.lines.all()
        self.assertEqual(len(po_lines), 1)
        line = po_lines[0]
        self.assertEqual(line.quantity['staged'], 2)
        self.assertEqual(line.cost['unit'], 8.00)

    def test_transfer_order_to_purchase_with_vendor_grouping(self):
        """Test transfer with vendor grouping."""
        vendor2 = OrgBase.objects.create(
            display_name="Bob Vendor",
            org_type="vendor"
        )

        # Create order lines with different vendors in item envelope
        OrderLine.objects.create(
            order=self.order,
            item={'description': 'Item 1', 'vendor_id': self.vendor.id},
            quantity={'staged': 2},
            price={'unit': 10.00},
            cost={'unit': 8.00}
        )
        OrderLine.objects.create(
            order=self.order,
            item={'description': 'Item 2', 'vendor_id': vendor2.id},
            quantity={'staged': 1},
            price={'unit': 15.00},
            cost={'unit': 12.00}
        )

        result = transfer_order_to_purchase(
            order=self.order,
            group_by_vendor=True,
            transfer_all=True
        )

        self.assertTrue(result['success'])
        self.assertEqual(len(result['purchase_ids']), 2)
        self.assertEqual(result['lines_transferred'], 2)
        self.assertEqual(result['vendor_groups'], 2)

        # Check POs were created with correct vendors
        pos = Purchase.objects.filter(id__in=result['purchase_ids'])
        vendor_ids = [po.vendor_id for po in pos]
        self.assertIn(self.vendor.id, vendor_ids)
        self.assertIn(vendor2.id, vendor_ids)

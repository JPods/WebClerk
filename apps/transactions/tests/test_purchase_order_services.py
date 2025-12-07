from decimal import Decimal
from django.test import TestCase
from apps.transactions.models import PurchaseOrder, PurchaseOrderLine, SalesOrder, SalesOrderLine
from apps.transactions.services.purchase_order_totals import compute_purchase_order_sell_cost_totals
from apps.transactions.services.order_to_purchase import transfer_order_to_purchase
from apps.core.models import Contact


class PurchaseOrderTotalsServiceTest(TestCase):
    """Test cases for purchase order totals service."""

    def setUp(self):
        """Set up test data."""
        self.customer = Contact.objects.create(
            name_first="John",
            name_last="Doe",
            email="john.doe@example.com"
        )
        self.purchase_order = PurchaseOrder.objects.create(
            status="planned",
            customer_id=self.customer.id
        )

    def test_compute_totals_empty_order(self):
        """Test computing totals for an empty purchase order."""
        result = compute_purchase_order_sell_cost_totals(self.purchase_order)

        expected = {
            'sell': {
                'line_sum_goods': 0.0,
                'discount': 0.0,
                'tax': 0.0,
                'shipping': 0.0,
                'handling': 0.0,
                'other': 0.0,
                'total': 0.0,
            },
            'cost': {
                'line_sum_goods': 0.0,
                'line_sum_tax': 0.0,
                'line_sum_shipping': 0.0,
                'line_sum_handling': 0.0,
                'freight': 0.0,
                'commissions': 0.0,
                'tax_rate': None,
                'tax': 0.0,
                'total': 0.0,
            },
            'totals': {
                'total': 0.0,
                'cost': 0.0,
                'margin': 0.0,
                'margin_pc': None,
                'received': None,
                'balance': None,
            }
        }
        self.assertEqual(result, expected)

    def test_compute_totals_with_lines(self):
        """Test computing totals with line items."""
        # Create line items
        PurchaseOrderLine.objects.create(
            parent=self.purchase_order,
            description="Item 1",
            quantity={'placed': 2},
            cost={'unit': 8.00, 'extended': 16.00}
        )
        PurchaseOrderLine.objects.create(
            parent=self.purchase_order,
            description="Item 2",
            quantity={'placed': 1},
            cost={'unit': 12.00, 'extended': 12.00}
        )

        result = compute_purchase_order_sell_cost_totals(self.purchase_order)

        # Check sell totals (empty for PO)
        self.assertEqual(result['sell']['line_sum_goods'], 0.0)
        self.assertEqual(result['sell']['total'], 0.0)

        # Check cost totals
        self.assertEqual(result['cost']['line_sum_goods'], 28.00)
        self.assertEqual(result['cost']['total'], 28.00)

        # Check totals
        self.assertEqual(result['totals']['total'], 28.00)
        self.assertEqual(result['totals']['cost'], 28.00)
        self.assertEqual(result['totals']['margin'], -28.00)

    def test_compute_totals_with_additional_costs(self):
        """Test computing totals with additional cost components."""
        PurchaseOrderLine.objects.create(
            parent=self.purchase_order,
            description="Item 1",
            quantity={'placed': 1},
            cost={
                'unit': 80.00,
                'extended': 80.00,
                'shipping': 5.00,
                'handling': 2.00,
                'freight': 3.00,
                'commissions': 4.00,
                'tax': 6.00
            }
        )

        result = compute_purchase_order_sell_cost_totals(self.purchase_order)

        # Check sell totals
        self.assertEqual(result['sell']['line_sum_goods'], 0.0)
        self.assertEqual(result['sell']['total'], 0.0)

        # Check cost totals include all components
        self.assertEqual(result['cost']['line_sum_goods'], 80.00)
        self.assertEqual(result['cost']['line_sum_shipping'], 5.00)
        self.assertEqual(result['cost']['line_sum_handling'], 2.00)
        self.assertEqual(result['cost']['freight'], 3.00)
        self.assertEqual(result['cost']['commissions'], 4.00)
        self.assertEqual(result['cost']['tax'], 6.00)
        self.assertEqual(result['cost']['total'], 100.00)  # 80 + 5 + 2 + 3 + 4 + 6

        # Check totals
        self.assertEqual(result['totals']['total'], 100.00)
        self.assertEqual(result['totals']['cost'], 100.00)
        self.assertEqual(result['totals']['margin'], -100.00)


class OrderToPurchaseServiceTest(TestCase):
    """Test cases for order to purchase transfer service."""

    def setUp(self):
        """Set up test data."""
        self.customer = Contact.objects.create(
            name_first="John",
            name_last="Doe",
            email="john.doe@example.com"
        )
        self.vendor = Contact.objects.create(
            name_first="Jane",
            name_last="Smith",
            email="jane.smith@example.com"
        )
        self.sales_order = SalesOrder.objects.create(
            status="released",
            customer_id=self.customer.id
        )

    def test_transfer_order_to_purchase_basic(self):
        """Test basic transfer from sales order to purchase order."""
        # Create sales order lines
        SalesOrderLine.objects.create(
            parent=self.sales_order,
            description="Item 1",
            quantity={'placed': 2},
            price={'unit': 10.00},
            cost={'unit': 8.00}
        )

        result = transfer_order_to_purchase(
            order=self.sales_order,
            group_by_vendor=False
        )

        self.assertTrue(result['success'])
        self.assertEqual(len(result['purchase_order_ids']), 1)
        self.assertEqual(result['lines_transferred'], 1)

        # Check PO was created
        po = PurchaseOrder.objects.get(id=result['purchase_order_ids'][0])
        self.assertEqual(po.status, "planned")
        self.assertEqual(po.customer_id, self.customer.id)
        self.assertEqual(po.refs['source']['sales_order_id'], self.sales_order.id)

        # Check PO line was created
        po_lines = po.purchaseorderline_set.all()
        self.assertEqual(len(po_lines), 1)
        line = po_lines[0]
        self.assertEqual(line.quantity['placed'], 2)
        self.assertEqual(line.cost['unit'], 8.00)

    def test_transfer_order_to_purchase_with_vendor_grouping(self):
        """Test transfer with vendor grouping."""
        vendor2 = Contact.objects.create(
            name_first="Bob",
            name_last="Vendor",
            email="bob@example.com"
        )

        # Create sales order lines with different vendors
        SalesOrderLine.objects.create(
            parent=self.sales_order,
            description="Item 1",
            quantity={'placed': 2},
            price={'unit': 10.00},
            cost={'unit': 8.00},
            vendor_id=self.vendor.id
        )
        SalesOrderLine.objects.create(
            parent=self.sales_order,
            description="Item 2",
            quantity={'placed': 1},
            price={'unit': 15.00},
            cost={'unit': 12.00},
            vendor_id=vendor2.id
        )

        result = transfer_order_to_purchase(
            order=self.sales_order,
            group_by_vendor=True
        )

        self.assertTrue(result['success'])
        self.assertEqual(len(result['purchase_order_ids']), 2)
        self.assertEqual(result['lines_transferred'], 2)
        self.assertEqual(result['vendor_groups'], 2)

        # Check POs were created with correct vendors
        pos = PurchaseOrder.objects.filter(id__in=result['purchase_order_ids'])
        vendor_ids = [po.vendor_id for po in pos]
        self.assertIn(self.vendor.id, vendor_ids)
        self.assertIn(vendor2.id, vendor_ids)
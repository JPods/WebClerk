"""
Test Sequence 002 — Full Commerce Cycle with Conversion Chain, Commissions, and GL.

End-to-end test:
  1. Create customer with rep assignment
  2. Create quote with lines for item 308
  3. Populate commission on quote
  4. Convert quote → order (commission flows forward, on_p → on_so)
  5. Convert order → invoice (on_so → on_hand)
  6. Journalize invoice (GL entries + commission accrual)
  7. Apply cash to invoice
  8. Verify GL balanced
  9. Clone the order (fresh prices, dates reset)
  10. Convert order → purchase (on_po)
  11. Check conversion history

Uses zzz- prefix for all test data.
"""
import pytest
import time
from decimal import Decimal

from django.test import TestCase
from django.apps import apps


def _now_ms():
    return int(time.time() * 1000)


def _save_reviewed(model_key, header_id, lines):
    """Conversions create the header only and return lines for review.
    Saving the reviewed document is the step that creates the lines."""
    from apps.transactions.services.transaction_save import save_transaction_with_lines
    return save_transaction_with_lines(
        model_key=model_key,
        header_data={'id': header_id},
        lines_data=lines,
        request=None,
        verify_calculations=False,
    )


@pytest.mark.django_db(transaction=True)
@pytest.mark.usefixtures('chart_of_accounts')
class TestSequence002(TestCase):
    """Full commerce cycle test."""

    def setUp(self):
        """Create test customer, rep, and verify item 308 exists."""
        OrgBase = apps.get_model('orgs', 'OrgBase')
        Contact = apps.get_model('core', 'Contact')
        Item = apps.get_model('products', 'Item')

        # Create test item (was hardcoded to pk=308 in dev DB)
        self.item, _ = Item.objects.get_or_create(
            pk=308,
            defaults={
                'name': 'zzz Test Item 308',
                'ida': 'zzz-item-308',
                'sku': 'ZZZ-308',
                'price': {'base': 25.0},
                'cost': {'standard': 12.0},
                'quantity': {'on_hand': 100, 'available': 100},
            }
        )

        # Create or get test rep
        self.rep, _ = OrgBase.objects.get_or_create(
            ida='zzz-test-rep-002',
            defaults={
                'display_name': 'zzz Test Rep 002',
                'org_type': 'rep',
                'status': 'active',
                'financial': {
                    'rep': {'commissions': {'rate_pct': 10, 'basis': 'revenue'}},
                    'common': {'currency': 'USD'},
                },
                'prefs': {
                    'commission': {
                        'basis': 'revenue',
                        'level_factors': {'retail': 1.0, 'wholesale': 0.7},
                    },
                },
            },
        )

        # Create or get test customer with rep assignment
        self.customer, _ = OrgBase.objects.get_or_create(
            ida='zzz-test-cust-002',
            defaults={
                'display_name': 'zzz Test Customer 002',
                'org_type': 'customer',
                'status': 'active',
                'price_level': 'retail',
                'refs': {
                    'links': {
                        'reps': [{'id': self.rep.pk, 'rep_id': self.rep.pk, 'ida': self.rep.ida, 'name': self.rep.display_name}],
                    },
                },
            },
        )

        # Get claude contact for audit trail
        self.contact = Contact.objects.filter(email='claude@jpods.com').first()
        self.contact_id = self.contact.pk if self.contact else None

    def test_01_create_quote(self):
        """Create a quote with 2 lines for item 308."""
        Quote = apps.get_model('transactions', 'Quote')
        QuoteLine = apps.get_model('transactions', 'QuoteLine')

        self.quote = Quote.objects.create(
            ida='zzz-prop-002',
            customer=self.customer,
            status='planned',
            price_level='retail',
            totals={'total': 0, 'subtotal': 0},
        )

        # Line 1: qty 5 @ $25
        QuoteLine.objects.create(
            quote=self.quote,
            item_fk=self.item,
            item={'item_id': 308, 'name': self.item.name},
            quantity={'staged': 5, 'active': 5, 'remaining': 5},
            price={'unit': 25.0, 'extended': 125.0},
            cost={'unit': 12.0, 'extended': 60.0},
            line_number=10,
        )

        # Line 2: qty 3 @ $25
        QuoteLine.objects.create(
            quote=self.quote,
            item_fk=self.item,
            item={'item_id': 308, 'name': self.item.name},
            quantity={'staged': 3, 'active': 3, 'remaining': 3},
            price={'unit': 25.0, 'extended': 75.0},
            cost={'unit': 12.0, 'extended': 36.0},
            line_number=20,
        )

        self.assertEqual(QuoteLine.objects.filter(quote=self.quote).count(), 2)
        print(f'  ✓ Quote {self.quote.ida} created with 2 lines')

    def test_02_populate_commission(self):
        """Populate commission on the quote from rep assignment."""
        from apps.transactions.services.pricing.commission_compute import populate_transaction_commission

        self.test_01_create_quote()

        result = populate_transaction_commission(self.quote.pk, 'quote')
        self.assertGreater(result.get('header_total', 0), 0, 'Commission should be > 0')
        self.assertEqual(result.get('lines_updated', 0), 2, 'Both lines should have commission')

        # Verify: 200 total × 10% × 1.0 retail = $20
        self.assertAlmostEqual(result['header_total'], 20.0, places=1)
        print(f'  ✓ Commission populated: ${result["header_total"]} ({result["lines_updated"]} lines)')

    def test_03_convert_quote_to_order(self):
        """Convert quote to order — commission flows forward, inventory adjusts."""
        from apps.transactions.services.convert.convert import convert_quote_to_order

        self.test_02_populate_commission()

        result = convert_quote_to_order(self.quote.pk, contact_id=self.contact_id)
        self.assertNotIn('error', result, f'Conversion failed: {result.get("error")}')
        self.assertGreater(result['order_id'], 0)

        # Verify order has commission
        Order = apps.get_model('transactions', 'Order')
        order = Order.objects.get(pk=result['order_id'])
        self.assertTrue(order.commission.get('reps'), 'Order should have commission reps')
        self.assertGreater(order.commission.get('total', 0), 0, 'Order commission total > 0')

        # Save the reviewed order — order lines become children of the quote lines
        self.assertEqual(result['lines_for_review'], 2)
        _save_reviewed('order', result['order_id'], result['lines'])
        OrderLine = apps.get_model('transactions', 'OrderLine')
        QuoteLine = apps.get_model('transactions', 'QuoteLine')
        order_lines = list(OrderLine.objects.filter(order=order))
        self.assertEqual(len(order_lines), 2)
        quote_line_ids = set(QuoteLine.objects.filter(quote=self.quote).values_list('pk', flat=True))
        for ol in order_lines:
            self.assertIn(ol.parent_line_id, quote_line_ids)
            self.assertTrue(ol.commission.get('reps'), 'Line commission should flow forward')
        for pl in QuoteLine.objects.filter(quote=self.quote):
            self.assertEqual(pl.quantity['remaining'], 0)
            self.assertEqual(pl.status, 'transferred')

        self.order_id = result['order_id']
        print(f'  ✓ Quote → Order {order.ida}: commission=${order.commission.get("total", 0)}, lines={len(order_lines)}')

    def test_04_convert_order_to_invoice(self):
        """Convert order to invoice."""
        from apps.transactions.services.convert.convert import convert_order_to_invoice

        self.test_03_convert_quote_to_order()

        result = convert_order_to_invoice(self.order_id, contact_id=self.contact_id)
        self.assertNotIn('error', result, f'Conversion failed: {result.get("error")}')

        Invoice = apps.get_model('transactions', 'Invoice')
        invoice = Invoice.objects.get(pk=result['invoice_id'])
        self.assertTrue(invoice.commission.get('reps'), 'Invoice should have commission')

        _save_reviewed('invoice', result['invoice_id'], result['lines'])
        InvoiceLine = apps.get_model('transactions', 'InvoiceLine')
        OrderLine = apps.get_model('transactions', 'OrderLine')
        order_line_ids = set(OrderLine.objects.filter(order_id=self.order_id).values_list('pk', flat=True))
        inv_lines = list(InvoiceLine.objects.filter(invoice=invoice))
        self.assertEqual(len(inv_lines), 2)
        self.assertEqual({il.parent_line_id for il in inv_lines}, order_line_ids)
        for ol in OrderLine.objects.filter(order_id=self.order_id):
            self.assertEqual(ol.quantity['remaining'], 0)
            self.assertEqual(ol.status, 'transferred')

        self.invoice_id = result['invoice_id']
        print(f'  ✓ Order → Invoice {invoice.ida}: commission=${invoice.commission.get("total", 0)}')

    def test_05_journalize_invoice(self):
        """Journalize the invoice — GL entries + commission accrual."""
        from apps.accounts.services.journalize import journalize_invoice

        self.test_04_convert_order_to_invoice()

        result = journalize_invoice(self.invoice_id, ida_prefix='zzz-')
        self.assertGreater(result.get('created', 0), 0, 'Should create GL entries')
        self.assertNotIn('error', result)

        # Check commission was accrued
        Invoice = apps.get_model('transactions', 'Invoice')
        invoice = Invoice.objects.get(pk=self.invoice_id)
        self.assertTrue(invoice.commission.get('accrued', False), 'Commission should be accrued')

        print(f'  ✓ Invoice journalized: {result["created"]} GL entries, commission accrued=${result.get("commission_accrued", 0)}')

    def test_06_apply_cash(self):
        """Create and apply cash to the invoice."""
        from apps.transactions.services.cash.cash_pending import apply_cash_to_invoice

        self.test_05_journalize_invoice()

        # Create a cash entry
        Cash = apps.get_model('transactions', 'Cash')
        cash = Cash.objects.create(
            ida='zzz-pay-002',
            amount=Decimal('200'),
            status='active',
        )

        result = apply_cash_to_invoice(
            cash_id=cash.pk,
            invoice_id=self.invoice_id,
            amount=200.0,
            reason='test_sequence_002',
            contact_id=self.contact_id,
        )
        self.assertNotIn('error', result)
        Invoice = apps.get_model('transactions', 'Invoice')
        inv = Invoice.objects.get(pk=self.invoice_id)
        self.assertTrue(
            result.get('applied', False) or result.get('state') == 'applied',
            f'Cash should be applied: result={result} invoice.is_locked={inv.is_locked} dt_journaled={inv.dt_journaled}',
        )

        print(f'  ✓ Cash applied: ${200} to invoice, state={result.get("state")}')

    def test_07_gl_balanced(self):
        """Verify GL is balanced (debits = credits)."""
        self.test_05_journalize_invoice()

        GlJournal = apps.get_model('accounts', 'GlJournal')
        from django.db.models import Sum, Value
        from django.db.models.functions import Coalesce

        totals = GlJournal.objects.filter(ida__startswith='zzz-').aggregate(
            total_debit=Coalesce(Sum('debit'), Value(0.0)),
            total_credit=Coalesce(Sum('credit'), Value(0.0)),
        )

        diff = abs(totals['total_debit'] - totals['total_credit'])
        self.assertLess(diff, 0.01, f'GL out of balance: debit={totals["total_debit"]}, credit={totals["total_credit"]}, diff={diff}')

        print(f'  ✓ GL balanced: debit=${totals["total_debit"]:.2f} = credit=${totals["total_credit"]:.2f}')

    def test_08_clone_order(self):
        """Clone the order — fresh dates, re-priced, commission reset."""
        from apps.core.services.record_clone import clone_record

        self.test_03_convert_quote_to_order()

        result = clone_record('order', self.order_id, include_children=True, contact_id=self.contact_id)
        self.assertNotIn('error', result)
        self.assertGreater(result['clone_id'], 0)
        self.assertGreater(result['lines_cloned'], 0)

        # Verify clone has fresh data
        Order = apps.get_model('transactions', 'Order')
        clone = Order.objects.get(pk=result['clone_id'])
        self.assertEqual(clone.status, 'planned', 'Clone should be planned')
        self.assertFalse(clone.is_locked, 'Clone should not be locked')
        self.assertIsNone(clone.parent_id, 'Clone should have no parent')

        # Verify commission accrual reset
        if clone.commission:
            self.assertFalse(clone.commission.get('accrued', True), 'Clone commission should not be accrued')

        # Verify cloned_from metadata
        self.assertEqual(clone.metadata.get('cloned_from', {}).get('id'), self.order_id)

        print(f'  ✓ Order cloned: {result["clone_ida"]} from {result["source_ida"]}, {result["lines_cloned"]} lines')

    def test_09_convert_order_to_purchase(self):
        """Convert order to purchase order."""
        from apps.transactions.services.convert.convert import convert_order_to_purchase

        self.test_03_convert_quote_to_order()

        # Need a vendor
        OrgBase = apps.get_model('orgs', 'OrgBase')
        vendor, _ = OrgBase.objects.get_or_create(
            ida='zzz-test-vendor-002',
            defaults={
                'display_name': 'zzz Test Vendor 002',
                'org_type': 'vendor',
                'status': 'active',
            },
        )

        result = convert_order_to_purchase(self.order_id, vendor_id=vendor.pk, contact_id=self.contact_id)
        self.assertNotIn('error', result, f'Conversion failed: {result.get("error")}')
        self.assertGreater(result['purchase_id'], 0)

        print(f'  ✓ Order → Purchase {result["purchase_ida"]}: {result["lines_for_review"]} lines for review')

    def test_10_conversion_history(self):
        """Trace the full conversion chain."""
        from apps.transactions.services.convert.convert import get_conversion_history

        self.test_04_convert_order_to_invoice()

        # Check invoice → should trace back to order → quote
        history = get_conversion_history(self.invoice_id, 'invoice')
        self.assertNotIn('error', history)

        parents = history.get('parents', [])
        self.assertGreater(len(parents), 0, 'Invoice should have parent(s) in chain')

        chain = [history['self']['model']] + [p['model'] for p in parents]
        print(f'  ✓ Conversion chain: {" → ".join(reversed(chain))}')

    def test_full_cycle(self):
        """Run the complete cycle end-to-end."""
        print('\n' + '=' * 60)
        print('TEST SEQUENCE 002 — Full Commerce Cycle')
        print('=' * 60)

        self.test_01_create_quote()
        self.test_02_populate_commission()

        # Re-create quote for the full chain (setUp runs fresh each test)
        self.test_01_create_quote()
        from apps.transactions.services.pricing.commission_compute import populate_transaction_commission
        populate_transaction_commission(self.quote.pk, 'quote')

        from apps.transactions.services.convert.convert import convert_quote_to_order, convert_order_to_invoice
        from apps.accounts.services.journalize import journalize_invoice
        from apps.core.services.record_clone import clone_record

        # Convert quote → order
        order_result = convert_quote_to_order(self.quote.pk, contact_id=self.contact_id)
        assert 'error' not in order_result, order_result.get('error')
        self.order_id = order_result['order_id']
        _save_reviewed('order', self.order_id, order_result['lines'])
        print(f'  ✓ Quote → Order: {order_result["lines_for_review"]} lines')

        # Convert order → invoice
        inv_result = convert_order_to_invoice(self.order_id, contact_id=self.contact_id)
        assert 'error' not in inv_result, inv_result.get('error')
        self.invoice_id = inv_result['invoice_id']
        _save_reviewed('invoice', self.invoice_id, inv_result['lines'])
        print(f'  ✓ Order → Invoice: {inv_result["lines_for_review"]} lines')

        # Journalize
        gl_result = journalize_invoice(self.invoice_id, ida_prefix='zzz-')
        assert gl_result.get('created', 0) > 0, 'No GL entries created'
        print(f'  ✓ Journalized: {gl_result["created"]} GL entries')

        # Clone
        clone_result = clone_record('order', self.order_id, include_children=True)
        assert 'error' not in clone_result, clone_result.get('error')
        print(f'  ✓ Cloned: {clone_result["clone_ida"]} ({clone_result["lines_cloned"]} lines)')

        # GL balance check
        GlJournal = apps.get_model('accounts', 'GlJournal')
        from django.db.models import Sum, Value
        from django.db.models.functions import Coalesce
        totals = GlJournal.objects.filter(ida__startswith='zzz-').aggregate(
            d=Coalesce(Sum('debit'), Value(0.0)),
            c=Coalesce(Sum('credit'), Value(0.0)),
        )
        diff = abs(totals['d'] - totals['c'])
        assert diff < 0.01, f'GL out of balance by ${diff}'
        print(f'  ✓ GL balanced: ${totals["d"]:.2f} = ${totals["c"]:.2f}')

        print('\n' + '=' * 60)
        print('ALL PASS — Full commerce cycle verified')
        print('=' * 60)

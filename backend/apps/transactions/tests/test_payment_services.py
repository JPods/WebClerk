import pytest
from decimal import Decimal
from django.test import TestCase
from django.utils import timezone
from unittest.mock import patch, MagicMock
from apps.transactions.models import Payment, Invoice, PaymentApplication
from apps.transactions.services.payment_application import apply_payment_to_invoice, unapply_payment_from_invoice, get_invoice_payment_status
from apps.transactions.services.payment_gateways import StripeService, PayPalService, PaymentReconciliationService
from apps.core.models import Contact


class PaymentApplicationServiceTest(TestCase):
    """Test cases for payment application service functions."""

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
        self.invoice = Invoice.objects.create(
            status="sent",
            customer_id=self.customer.id,
            vendor_id=self.vendor.id,
            totals={'total': 100.00, 'received': 0.00, 'balance': 100.00}
        )
        self.payment = Payment.objects.create(
            invoice=self.invoice,
            contact=self.customer,
            amount=50.00,
            status="completed"
        )

    def test_apply_payment_to_invoice_success(self):
        """Test successful payment application to invoice."""
        result = apply_payment_to_invoice(self.invoice, self.payment, 25.00)

        self.assertTrue(result['success'])
        self.assertEqual(result['amount_applied'], 25.00)
        self.assertEqual(result['invoice_balance_remaining'], 75.00)
        self.assertFalse(result['payment_fully_applied'])
        self.assertFalse(result['invoice_fully_paid'])

        # Check invoice totals updated
        self.invoice.refresh_from_db()
        self.assertEqual(self.invoice.totals['received'], 25.00)
        self.assertEqual(self.invoice.totals['balance'], 75.00)

        # Check payment refs updated
        self.payment.refresh_from_db()
        self.assertIn(self.invoice.id, self.payment.refs['invoice_ids'])

        # Check audit entry added
        audit_trail = self.payment.metadata['audit_trail']
        self.assertEqual(len(audit_trail), 1)
        self.assertEqual(audit_trail[0]['action'], 'payment_applied')

    def test_apply_payment_to_invoice_full_payment(self):
        """Test applying full payment amount."""
        result = apply_payment_to_invoice(self.invoice, self.payment)

        self.assertTrue(result['success'])
        self.assertEqual(result['amount_applied'], 50.00)
        self.assertEqual(result['invoice_balance_remaining'], 50.00)
        self.assertTrue(result['payment_fully_applied'])
        self.assertFalse(result['invoice_fully_paid'])

        # Check payment status updated
        self.payment.refresh_from_db()
        self.assertEqual(self.payment.status, 'fully_applied')

    def test_apply_payment_to_invoice_full_invoice_payment(self):
        """Test applying payment that fully pays the invoice."""
        small_payment = Payment.objects.create(
            invoice=self.invoice,
            contact=self.customer,
            amount=100.00,
            status="completed"
        )

        result = apply_payment_to_invoice(self.invoice, small_payment)

        self.assertTrue(result['success'])
        self.assertEqual(result['amount_applied'], 100.00)
        self.assertEqual(result['invoice_balance_remaining'], 0.00)
        self.assertTrue(result['payment_fully_applied'])
        self.assertTrue(result['invoice_fully_paid'])

        # Check invoice status updated
        self.invoice.refresh_from_db()
        self.assertEqual(self.invoice.status, 'paid')

    def test_apply_payment_to_invoice_pending_payment(self):
        """Test applying payment that is not completed."""
        pending_payment = Payment.objects.create(
            invoice=self.invoice,
            contact=self.customer,
            amount=25.00,
            status="pending"
        )

        with self.assertRaises(Exception) as cm:
            apply_payment_to_invoice(self.invoice, pending_payment)

        self.assertIn("Payment must be completed", str(cm.exception))

    def test_apply_payment_to_invoice_invalid_status(self):
        """Test applying payment to invoice with invalid status."""
        self.invoice.status = 'paid'
        self.invoice.save()

        with self.assertRaises(Exception) as cm:
            apply_payment_to_invoice(self.invoice, self.payment)

        self.assertIn("does not allow payment application", str(cm.exception))

    def test_unapply_payment_from_invoice(self):
        """Test removing payment application from invoice."""
        # First apply payment
        apply_payment_to_invoice(self.invoice, self.payment, 25.00)

        # Get the application
        application = PaymentApplication.objects.get(
            payment=self.payment,
            invoice=self.invoice
        )

        # Unapply
        result = unapply_payment_from_invoice(self.payment, self.invoice)

        self.assertTrue(result['success'])
        self.assertEqual(result['amount_unapplied'], 25.00)

        # Check invoice totals reverted
        self.invoice.refresh_from_db()
        self.assertEqual(self.invoice.totals['received'], 0.00)
        self.assertEqual(self.invoice.totals['balance'], 100.00)

        # Check application deleted
        with self.assertRaises(PaymentApplication.DoesNotExist):
            PaymentApplication.objects.get(id=application.id)

    def test_get_invoice_payment_status(self):
        """Test getting comprehensive payment status for invoice."""
        # Apply some payments
        payment1 = Payment.objects.create(
            invoice=self.invoice,
            contact=self.customer,
            amount=30.00,
            status="completed"
        )
        payment2 = Payment.objects.create(
            invoice=self.invoice,
            contact=self.customer,
            amount=20.00,
            status="completed"
        )

        apply_payment_to_invoice(self.invoice, payment1, 30.00)
        apply_payment_to_invoice(self.invoice, payment2, 20.00)

        status = get_invoice_payment_status(self.invoice)

        self.assertEqual(status['total_due'], 100.00)
        self.assertEqual(status['total_paid'], 50.00)
        self.assertEqual(status['balance'], 50.00)
        self.assertEqual(status['payment_count'], 2)
        self.assertFalse(status['is_fully_paid'])
        self.assertEqual(len(status['payments']), 2)


class StripeServiceTest(TestCase):
    """Test cases for Stripe payment gateway service."""

    def setUp(self):
        """Set up test data."""
        self.customer = Contact.objects.create(
            name_first="John",
            name_last="Doe",
            email="john.doe@example.com"
        )
        self.invoice = Invoice.objects.create(
            status="sent",
            customer_id=self.customer.id,
            totals={'total': 100.00}
        )
        self.payment = Payment.objects.create(
            invoice=self.invoice,
            contact=self.customer,
            amount=50.00,
            gateway="stripe"
        )

    @patch('stripe.PaymentIntent.create')
    def test_create_payment_intent_success(self, mock_create):
        """Test successful Stripe payment intent creation."""
        mock_intent = MagicMock()
        mock_intent.id = 'pi_test123'
        mock_intent.client_secret = 'secret_test'
        mock_create.return_value = mock_intent

        service = StripeService()
        result = service.create_payment_intent(self.payment)

        self.assertEqual(result, mock_intent)
        mock_create.assert_called_once()

        # Check payment updated
        self.payment.refresh_from_db()
        self.assertEqual(self.payment.gateway_payment_intent_id, 'pi_test123')
        self.assertEqual(self.payment.gateway_transaction_id, 'pi_test123')
        self.assertEqual(self.payment.status, 'processing')

    @patch('stripe.PaymentIntent.create')
    def test_create_payment_intent_failure(self, mock_create):
        """Test Stripe payment intent creation failure."""
        mock_create.side_effect = Exception("Stripe error")

        service = StripeService()

        with self.assertRaises(Exception):
            service.create_payment_intent(self.payment)

        # Check payment marked as failed
        self.payment.refresh_from_db()
        self.assertEqual(self.payment.status, 'failed')

    @patch('stripe.PaymentIntent.retrieve')
    def test_verify_stripe_payment_success(self, mock_retrieve):
        """Test successful Stripe payment verification."""
        mock_intent = MagicMock()
        mock_intent.status = 'succeeded'
        mock_intent.amount = 5000  # 50.00 * 100
        mock_retrieve.return_value = mock_intent

        service = PaymentReconciliationService()
        result = service._verify_stripe_payment(self.payment)

        self.assertTrue(result)
        mock_retrieve.assert_called_once_with(self.payment.gateway_payment_intent_id)


class PayPalServiceTest(TestCase):
    """Test cases for PayPal payment gateway service."""

    def setUp(self):
        """Set up test data."""
        self.customer = Contact.objects.create(
            name_first="John",
            name_last="Doe",
            email="john.doe@example.com"
        )
        self.invoice = Invoice.objects.create(
            status="sent",
            customer_id=self.customer.id,
            totals={'total': 100.00}
        )
        self.payment = Payment.objects.create(
            invoice=self.invoice,
            contact=self.customer,
            amount=50.00,
            gateway="paypal"
        )

    @patch('paypalrestsdk.Payment')
    def test_create_paypal_payment_success(self, mock_payment_class):
        """Test successful PayPal payment creation."""
        mock_payment = MagicMock()
        mock_payment.id = 'PAY-123'
        mock_payment.create.return_value = True
        mock_payment.links = [{'rel': 'approval_url', 'href': 'https://paypal.com/approve'}]
        mock_payment_class.return_value = mock_payment

        service = PayPalService()
        result = service.create_payment(self.payment)

        self.assertEqual(result, mock_payment)

        # Check payment updated
        self.payment.refresh_from_db()
        self.assertEqual(self.payment.gateway_transaction_id, 'PAY-123')
        self.assertEqual(self.payment.status, 'processing')


class PaymentReconciliationServiceTest(TestCase):
    """Test cases for payment reconciliation service."""

    def setUp(self):
        """Set up test data."""
        self.customer = Contact.objects.create(
            name_first="John",
            name_last="Doe",
            email="john.doe@example.com"
        )
        self.invoice = Invoice.objects.create(
            status="sent",
            customer_id=self.customer.id,
            totals={'total': 100.00}
        )

    @patch('apps.transactions.services.payment_gateways.PaymentReconciliationService._verify_payment_with_gateway')
    def test_reconcile_payments_success(self, mock_verify):
        """Test successful payment reconciliation."""
        mock_verify.return_value = True

        payment = Payment.objects.create(
            invoice=self.invoice,
            contact=self.customer,
            amount=50.00,
            status="completed",
            reconciled=False
        )

        service = PaymentReconciliationService()
        reconciled_count = service.reconcile_payments()

        self.assertEqual(reconciled_count, 1)

        # Check payment reconciled
        payment.refresh_from_db()
        self.assertTrue(payment.reconciled)
        self.assertIn('reconciled', payment.metadata['audit_trail'][0]['action'])
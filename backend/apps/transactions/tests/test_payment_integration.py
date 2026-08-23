import json
from decimal import Decimal
from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APITestCase
from rest_framework import status

from apps.transactions.models import Payment, Invoice, PaymentApplication
from apps.transactions.services.payment_application import apply_payment_to_invoice
from apps.core.models import Contact


class PaymentWorkflowIntegrationTest(APITestCase):
    """Integration tests for payment processing and application workflow."""

    def setUp(self):
        """Set up test data."""
        # Create test contacts
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

        # Create invoice
        self.invoice = Invoice.objects.create(
            status="sent",
            customer_id=self.customer.id,
            vendor_id=self.vendor.id,
            totals={'total': 100.00, 'received': 0.00, 'balance': 100.00}
        )

        # Test data
        self.payment_data = {
            'invoice_id': self.invoice.id,
            'contact_id': self.customer.id,
            'amount': 50.00,
            'gateway': 'stripe',
            'status': 'pending'
        }

    def test_payment_creation_and_application_workflow(self):
        """Test complete payment creation and application workflow."""
        # Step 1: Create payment
        url = reverse('transactions:payment-list')
        response = self.client.post(url, self.payment_data, format='json')

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        payment_id = response.data['id']
        self.assertEqual(response.data['amount'], '50.00')
        self.assertEqual(response.data['status'], 'pending')

        # Verify payment was created
        payment = Payment.objects.get(id=payment_id)
        self.assertEqual(payment.amount, 50.00)
        self.assertEqual(payment.status, 'pending')

        # Step 2: Apply payment to invoice
        apply_url = reverse('transactions:payment-apply-to-invoice', kwargs={'pk': payment_id})
        apply_data = {'invoice_id': self.invoice.id, 'amount': 25.00}
        response = self.client.post(apply_url, apply_data, format='json')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data['success'])
        self.assertEqual(response.data['amount_applied'], 25.00)

        # Verify payment application
        applications = PaymentApplication.objects.filter(payment=payment, invoice=self.invoice)
        self.assertEqual(applications.count(), 1)
        self.assertEqual(applications.first().amount, 25.00)

        # Verify invoice totals updated
        self.invoice.refresh_from_db()
        self.assertEqual(self.invoice.totals['received'], 25.00)
        self.assertEqual(self.invoice.totals['balance'], 75.00)

        # Verify payment refs updated
        payment.refresh_from_db()
        self.assertIn(self.invoice.id, payment.refs['invoice_ids'])

    def test_payment_status_endpoint(self):
        """Test payment status endpoint."""
        # Create and apply payment
        payment = Payment.objects.create(
            invoice=self.invoice,
            contact=self.customer,
            amount=50.00,
            status="completed"
        )
        apply_payment_to_invoice(self.invoice, payment, 50.00)

        # Get payment status
        status_url = reverse('transactions:payment-status', kwargs={'pk': payment.id})
        response = self.client.get(status_url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['status'], 'completed')
        self.assertEqual(response.data['amount'], 50.00)
        self.assertIn('refs', response.data)
        self.assertIn('metadata', response.data)
        self.assertIn('invoice_statuses', response.data)

    def test_payment_validation(self):
        """Test payment validation rules."""
        url = reverse('transactions:payment-list')

        # Test missing invoice_id
        invalid_data = {**self.payment_data}
        del invalid_data['invoice_id']
        response = self.client.post(url, invalid_data, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        # Test invalid invoice_id
        invalid_data = {**self.payment_data, 'invoice_id': 99999}
        response = self.client.post(url, invalid_data, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        # Test negative amount
        invalid_data = {**self.payment_data, 'amount': -50.00}
        response = self.client.post(url, invalid_data, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_payment_refs_and_metadata(self):
        """Test that payment refs and metadata are properly handled."""
        # Create payment
        url = reverse('transactions:payment-list')
        response = self.client.post(url, self.payment_data, format='json')
        payment_id = response.data['id']

        # Check that refs and metadata are included in response
        self.assertIn('refs', response.data)
        self.assertIn('metadata', response.data)

        # Update payment with custom refs and metadata
        update_data = {
            'refs': {'custom_field': 'test_value'},
            'metadata': {'custom_meta': 'test_meta'}
        }
        detail_url = reverse('transactions:payment-detail', kwargs={'pk': payment_id})
        response = self.client.patch(detail_url, update_data, format='json')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['refs']['custom_field'], 'test_value')
        self.assertEqual(response.data['metadata']['custom_meta'], 'test_meta')
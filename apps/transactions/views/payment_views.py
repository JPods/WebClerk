import logging
import json
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST, require_GET
from django.shortcuts import get_object_or_404
from django.conf import settings
from rest_framework import viewsets, status
from rest_framework.decorators import action, api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from apps.transactions.models import Payment, Invoice
from apps.transactions.serializers.payment_serializers import PaymentSerializer
from apps.transactions.services.payment_gateways import StripeService, PayPalService, PaymentReconciliationService
from apps.transactions.services.payment_application import apply_payment_to_invoice, get_invoice_payment_status
from apps.core.services import wcapi

logger = logging.getLogger(__name__)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def process_payment(request):
    """Process a payment through the specified gateway"""
    try:
        data = request.data
        invoice_id = data.get('invoice_id')
        amount = data.get('amount')
        gateway = data.get('gateway', 'stripe')  # Default to stripe
        payment_method_id = data.get('payment_method_id')

        if not invoice_id or not amount:
            return Response(
                {'error': 'invoice_id and amount are required'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Get invoice
        invoice = get_object_or_404(Invoice, pk=invoice_id)

        # Create payment record
        payment = Payment.objects.create(
            invoice_id=invoice,
            contact_id=request.user,  # Assuming user is contact
            amount=amount,
            gateway=gateway,
            status='pending'
        )

        # Process with gateway
        if gateway == 'stripe':
            service = StripeService()
            result = service.create_payment_intent(payment)

            return Response({
                'payment_id': payment.id,
                'client_secret': result.client_secret,
                'gateway_transaction_id': result.id
            })

        elif gateway == 'paypal':
            service = PayPalService()
            result = service.create_payment(payment)

            # Find approval URL
            approval_url = None
            for link in result.links:
                if link.rel == 'approval_url':
                    approval_url = link.href
                    break

            return Response({
                'payment_id': payment.id,
                'approval_url': approval_url,
                'gateway_transaction_id': result.id
            })

        else:
            return Response(
                {'error': f'Unsupported gateway: {gateway}'},
                status=status.HTTP_400_BAD_REQUEST
            )

    except Exception as e:
        logger.error(f"Error processing payment: {e}")
        return Response(
            {'error': 'Payment processing failed'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def execute_paypal_payment(request):
    """Execute a PayPal payment after user approval"""
    try:
        payment_id = request.data.get('payment_id')
        payer_id = request.data.get('payer_id')

        if not payment_id or not payer_id:
            return Response(
                {'error': 'payment_id and payer_id are required'},
                status=status.HTTP_400_BAD_REQUEST
            )

        service = PayPalService()
        result = service.execute_payment(payment_id, payer_id)

        return Response({
            'status': 'completed',
            'transaction_id': result.id
        })

    except Exception as e:
        logger.error(f"Error executing PayPal payment: {e}")
        return Response(
            {'error': 'Payment execution failed'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@csrf_exempt
@require_POST
def stripe_webhook(request):
    """Handle Stripe webhook events"""
    payload = request.body
    sig_header = request.META.get('HTTP_STRIPE_SIGNATURE')

    try:
        service = StripeService()
        event = service.handle_webhook(payload, sig_header)

        return JsonResponse({'status': 'success'})

    except ValueError as e:
        logger.error(f"Invalid Stripe webhook: {e}")
        return JsonResponse({'error': str(e)}, status=400)
    except Exception as e:
        logger.error(f"Stripe webhook error: {e}")
        return JsonResponse({'error': 'Webhook processing failed'}, status=500)


@csrf_exempt
@require_POST
def paypal_webhook(request):
    """Handle PayPal webhook events"""
    try:
        webhook_data = json.loads(request.body.decode('utf-8'))

        service = PayPalService()
        service.handle_webhook(webhook_data)

        return JsonResponse({'status': 'success'})

    except json.JSONDecodeError:
        logger.error("Invalid PayPal webhook payload")
        return JsonResponse({'error': 'Invalid JSON'}, status=400)
    except Exception as e:
        logger.error(f"PayPal webhook error: {e}")
        return JsonResponse({'error': 'Webhook processing failed'}, status=500)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def reconcile_payments(request):
    """Reconcile payments with gateway statements"""
    try:
        start_date = request.data.get('start_date')
        end_date = request.data.get('end_date')

        service = PaymentReconciliationService()
        reconciled_count = service.reconcile_payments(start_date, end_date)

        return Response({
            'reconciled_count': reconciled_count,
            'message': f'Successfully reconciled {reconciled_count} payments'
        })

    except Exception as e:
        logger.error(f"Error reconciling payments: {e}")
        return Response(
            {'error': 'Reconciliation failed'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def payment_status(request, payment_id):
    """Get payment status"""
    try:
        payment = get_object_or_404(Payment, pk=payment_id)

        # Check if user has permission to view this payment
        if payment.contact_id != request.user and not request.user.is_staff:
            return Response(
                {'error': 'Permission denied'},
                status=status.HTTP_403_FORBIDDEN
            )

        return Response({
            'payment_id': payment.id,
            'status': payment.status,
            'amount': payment.amount,
            'gateway': payment.gateway,
            'gateway_transaction_id': payment.gateway_transaction_id,
            'processed_at': payment.processed_at,
            'reconciled': payment.reconciled
        })

    except Payment.DoesNotExist:
        return Response(
            {'error': 'Payment not found'},
            status=status.HTTP_404_NOT_FOUND
        )
    except Exception as e:
        logger.error(f"Error getting payment status: {e}")
        return Response(
            {'error': 'Failed to get payment status'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def payment_history(request):
    """Get payment history for the authenticated user"""
    try:
        payments = Payment.objects.filter(contact_id=request.user).order_by('-dt_created')

        # Paginate if needed
        page = request.query_params.get('page', 1)
        per_page = request.query_params.get('per_page', 20)

        start = (int(page) - 1) * int(per_page)
        end = start + int(per_page)

        payments_page = payments[start:end]

        data = []
        for payment in payments_page:
            data.append({
                'id': payment.id,
                'invoice_id': payment.invoice_id_id,
                'amount': payment.amount,
                'status': payment.status,
                'gateway': payment.gateway,
                'created_at': payment.dt_created,
                'processed_at': payment.processed_at
            })

        return Response({
            'payments': data,
            'total_count': payments.count(),
            'page': page,
            'per_page': per_page
        })

    except Exception as e:
        logger.error(f"Error getting payment history: {e}")
        return Response(
            {'error': 'Failed to get payment history'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


class PaymentViewSet(viewsets.ModelViewSet):
    """
    REST API viewset for Payment management.
    Uses WCAPI for all save operations to maintain consistency and security.
    """
    queryset = Payment.objects.all()
    serializer_class = PaymentSerializer

    def get_queryset(self):
        """Filter queryset based on user permissions."""
        return self.queryset

    def perform_create(self, serializer):
        """Create payment using WCAPI save."""
        data = serializer.validated_data.copy()
        data['model_name'] = 'payment'

        # Use WCAPI save for consistency
        result = wcapi.save_item('payment', request=self.request, data=data)
        if result[1] == 'created':
            # Set the created instance on serializer for response
            instance = Payment.objects.get(pk=result[0])
            serializer.instance = instance
        else:
            raise Exception("Failed to create payment")

    def perform_update(self, serializer):
        """Update payment using WCAPI save."""
        instance = self.get_object()
        data = serializer.validated_data.copy()
        data['model_name'] = 'payment'
        data['id'] = instance.id

        # Use WCAPI save for consistency
        result = wcapi.save_item('payment', request=self.request, data=data, id=instance.id)
        if result[1] == 'updated':
            # Refresh instance
            instance.refresh_from_db()
            serializer.instance = instance
        else:
            raise Exception("Failed to update payment")

    @action(detail=True, methods=['post'])
    def apply_to_invoice(self, request, pk=None):
        """Apply payment to an invoice."""
        payment = self.get_object()
        invoice_id = request.data.get('invoice_id')
        amount = request.data.get('amount')

        if not invoice_id:
            return Response(
                {'error': 'invoice_id is required'},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            invoice = Invoice.objects.get(pk=invoice_id)
        except Invoice.DoesNotExist:
            return Response(
                {'error': 'Invoice not found'},
                status=status.HTTP_404_NOT_FOUND
            )

        try:
            result = apply_payment_to_invoice(invoice, payment, amount)
            return Response(result, status=status.HTTP_200_OK)
        except Exception as e:
            logger.error(f"Error applying payment {payment.id} to invoice {invoice_id}: {e}")
            return Response(
                {'error': 'Failed to apply payment'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @action(detail=True, methods=['get'])
    def status(self, request, pk=None):
        """Get detailed payment status."""
        payment = self.get_object()

        # Get related invoice statuses
        invoice_statuses = []
        for invoice_id in payment.refs.get('invoice_ids', []) if payment.refs else []:
            try:
                invoice = Invoice.objects.get(pk=invoice_id)
                status_info = get_invoice_payment_status(invoice)
                invoice_statuses.append({
                    'invoice_id': invoice_id,
                    'status': status_info
                })
            except Invoice.DoesNotExist:
                continue

        return Response({
            'payment_id': payment.id,
            'status': payment.status,
            'amount': payment.amount,
            'gateway': payment.gateway,
            'reconciled': payment.reconciled,
            'refs': payment.refs,
            'metadata': payment.metadata,
            'invoice_statuses': invoice_statuses,
            'dt_created': payment.dt_created,
            'dt_modified': payment.dt_modified
        })

    @action(detail=False, methods=['post'])
    def process_gateway_payment(self, request):
        """Process a payment through gateway (alternative to function-based view)."""
        return process_payment(request)
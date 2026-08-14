import logging
import json
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST, require_GET
from django.shortcuts import get_object_or_404
from django.conf import settings
from rest_framework import viewsets, status
from rest_framework.decorators import action, api_view, permission_classes, throttle_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.throttling import ScopedRateThrottle
from rest_framework.response import Response
from apps.transactions.models import Payment, Invoice
from apps.transactions.serializers.payment_serializers import PaymentSerializer
from apps.transactions.services.payment_gateways import SpreedlyService, SpreedlyError, process_payment as spreedly_process, refund_payment as spreedly_refund
from apps.transactions.services.payment_pending import apply_payment_to_invoice
from apps.transactions.services.payment_application import get_invoice_payment_status
from apps.core.services import wcapi

logger = logging.getLogger(__name__)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
@throttle_classes([ScopedRateThrottle])
def process_payment(request):
    """Process a payment through Spreedly.

    The client-side Spreedly SDK collects card data in a secure iframe
    and returns a payment_method_token. That token is all we receive.
    WC3 never sees the card number.

    POST body: { invoice_id, amount, payment_method_token }
    """
    request.throttle_scope = 'payment'
    try:
        data = request.data
        invoice_id = data.get('invoice_id')
        amount = data.get('amount')
        payment_method_token = data.get('payment_method_token')

        if not invoice_id or not amount or not payment_method_token:
            return Response(
                {'error': 'invoice_id, amount, and payment_method_token are required'},
                status=status.HTTP_400_BAD_REQUEST
            )

        invoice = get_object_or_404(Invoice, pk=invoice_id)

        payment = Payment.objects.create(
            invoice=invoice,
            contact=request.user,
            amount=amount,
            gateway='spreedly',
            status='pending',
        )

        result = spreedly_process(payment.id, payment_method_token)
        txn = result.get('transaction', {})

        return Response({
            'payment_id': payment.id,
            'status': payment.status,
            'gateway_transaction_id': txn.get('gateway_transaction_id', ''),
            'message': txn.get('message', ''),
        })

    except SpreedlyError as e:
        logger.error(f"Spreedly error processing payment: {e}")
        return Response(
            {'error': str(e)},
            status=status.HTTP_502_BAD_GATEWAY
        )
    except Exception as e:
        logger.error(f"Error processing payment: {e}")
        return Response(
            {'error': 'Payment processing failed'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['POST'])
@permission_classes([IsAuthenticated])
@throttle_classes([ScopedRateThrottle])
def refund_payment_view(request):
    """Refund a completed payment via Spreedly.

    Tries void first (pre-settlement), falls back to credit.
    POST body: { payment_id, amount_cents? }
    """
    request.throttle_scope = 'payment'
    try:
        payment_id = request.data.get('payment_id')
        amount_cents = request.data.get('amount_cents')

        if not payment_id:
            return Response({'error': 'payment_id is required'}, status=status.HTTP_400_BAD_REQUEST)

        result = spreedly_refund(int(payment_id), amount_cents)
        txn = result.get('transaction', {})

        payment = Payment.objects.get(pk=payment_id)
        return Response({
            'payment_id': payment.id,
            'status': payment.status,
            'message': txn.get('message', ''),
        })

    except SpreedlyError as e:
        return Response({'error': str(e)}, status=status.HTTP_502_BAD_GATEWAY)
    except Exception as e:
        logger.error(f"Error refunding payment: {e}")
        return Response({'error': 'Refund failed'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@csrf_exempt
@require_POST
def spreedly_webhook(request):
    """Handle Spreedly webhook/callback events.

    Spreedly sends transaction lifecycle events. We verify and update
    the corresponding Payment record.
    """
    try:
        webhook_data = json.loads(request.body.decode('utf-8'))
        txn = webhook_data.get('transaction', {})
        txn_token = txn.get('token', '')

        if not txn_token:
            return JsonResponse({'error': 'No transaction token'}, status=400)

        # Find payment by Spreedly transaction token
        try:
            payment = Payment.objects.get(id_gateway_transaction=txn_token)
        except Payment.DoesNotExist:
            logger.warning(f"Spreedly webhook: no payment for token {txn_token}")
            return JsonResponse({'status': 'ignored'})

        state = txn.get('state', '')
        if state == 'succeeded' and payment.status != 'completed':
            payment.status = 'completed'
            from django.utils import timezone as tz
            payment.dt_processed = tz.now()
            payment.add_audit_entry('webhook_confirmed', {'state': state, 'token': txn_token})
            payment.save()
        elif state in ('failed', 'gateway_processing_failed'):
            payment.status = 'failed'
            payment.gateway_response = {'message': txn.get('message', ''), 'state': state}
            payment.save()

        return JsonResponse({'status': 'ok'})

    except json.JSONDecodeError:
        return JsonResponse({'error': 'Invalid JSON'}, status=400)
    except Exception as e:
        logger.error(f"Spreedly webhook error: {e}")
        return JsonResponse({'error': 'Webhook processing failed'}, status=500)


# Legacy webhook aliases — redirect to Spreedly
stripe_webhook = spreedly_webhook
paypal_webhook = spreedly_webhook


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
        if payment.contact != request.user and not request.user.is_staff:
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
        payments = Payment.objects.filter(contact=request.user).order_by('-dt_created')

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
                'invoice_id': payment.invoice.pk if payment.invoice else None,
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


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def gateway_config(request):
    """Return public gateway configuration for client-side SDK.

    Only exposes the environment_key (public, safe for iframes)
    and test_mode flag. NEVER exposes access_secret.
    """
    from apps.core.models import Setting
    try:
        setting = Setting.objects.get(purpose='wc:payment_gateway', is_active=True)
        config = setting.config or {}
        spreedly = config.get('spreedly', {})
        return Response({
            'environment_key': spreedly.get('environment_key', ''),
            'test_mode': config.get('test_mode', True),
            'active_gateway_type': config.get('active_gateway_type', ''),
            'currency': config.get('currency', 'USD'),
        })
    except Setting.DoesNotExist:
        return Response({
            'environment_key': '',
            'test_mode': True,
            'active_gateway_type': '',
            'currency': 'USD',
        })


class PaymentViewSet(viewsets.ReadOnlyModelViewSet):
    """Read-only ViewSet for Payment. Writes go through /wcapi/save/."""

    queryset = Payment.objects.active()
    serializer_class = PaymentSerializer
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = 'payment'

    @action(detail=True, methods=['post'])
    def apply_to_invoice(self, request, pk=None):
        """Apply payment to an invoice via pending record."""
        payment = self.get_object()
        invoice_id = request.data.get('invoice_id')
        amount = request.data.get('amount')

        if not invoice_id:
            return Response(
                {'error': 'invoice_id is required'},
                status=status.HTTP_400_BAD_REQUEST
            )

        if not amount:
            return Response(
                {'error': 'amount is required'},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            result = apply_payment_to_invoice(
                payment_id=payment.pk,
                invoice_id=int(invoice_id),
                amount=amount,
            )
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
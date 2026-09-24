import logging
import json
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST, require_GET
from django.shortcuts import get_object_or_404
from django.conf import settings
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes, throttle_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.throttling import ScopedRateThrottle
from rest_framework.response import Response
from apps.transactions.models import Cash, Invoice, Receipt
from apps.transactions.services.cash.spreedly_gateway import SpreedlyService, SpreedlyError
from apps.transactions.services.pricing.dual_pricing import compute_dual_pricing, compute_cash_amount, get_dual_pricing_config
from apps.core.services import record_serialize as wcapi

logger = logging.getLogger(__name__)


# Pay, refund and the gateway's webhook are commands on Cash (services/cash/cash_commands.py):
# POST /wcapi/cash/<id>/pay/, POST /wcapi/cash/<id>/refund/,
# POST /wcapi/cash/_receive/<provider>/ (Bill, 2026-09-24).


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def cash_status(request, cash_id):
    """Get cash status"""
    try:
        cash = get_object_or_404(Cash, pk=cash_id)

        # Check if user has permission to view this cash
        if cash.contact_id != request.user.pk and not request.user.is_staff:
            return Response(
                {'error': 'Permission denied'},
                status=status.HTTP_403_FORBIDDEN
            )

        return Response({
            'cash_id': cash.id,
            'status': cash.status,
            'amount': cash.amount,
            'gateway': cash.gateway,
            'gateway_transaction_id': cash.gateway_transaction_id,
            'processed_at': cash.dt_processed,
            'reconciled': cash.reconciled
        })

    except Cash.DoesNotExist:
        return Response(
            {'error': 'Cash not found'},
            status=status.HTTP_404_NOT_FOUND
        )
    except Exception as e:
        logger.error(f"Error getting cash status: {e}")
        return Response(
            {'error': 'Failed to get cash status'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def cash_history(request):
    """Get cash history for the authenticated user"""
    try:
        cash_entries = Cash.objects.filter(contact_id=request.user.pk).order_by('-dt_created')

        # Paginate if needed
        page = request.query_params.get('page', 1)
        per_page = request.query_params.get('per_page', 20)

        start = (int(page) - 1) * int(per_page)
        end = start + int(per_page)

        cash_entries_page = cash_entries[start:end]

        data = []
        for cash in cash_entries_page:
            data.append({
                'id': cash.id,
                'invoice_id': cash.invoice.pk if cash.invoice else None,
                'amount': cash.amount,
                'status': cash.status,
                'gateway': cash.gateway,
                'created_at': cash.dt_created,
                'processed_at': cash.dt_processed
            })

        return Response({
            'cash_entries': data,
            'total_count': cash_entries.count(),
            'page': page,
            'per_page': per_page
        })

    except Exception as e:
        logger.error(f"Error getting cash history: {e}")
        return Response(
            {'error': 'Failed to get cash history'},
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
        setting = Setting.objects.get(purpose='wc:cash_gateway', is_active=True)
        config = setting.config or {}
        # The environment key is on the gateway's Connection (credentials.client_id).
        from apps.transactions.services.cash.spreedly_gateway import SpreedlyService
        try:
            environment_key = SpreedlyService.from_gateway().env_key
        except RuntimeError:
            environment_key = ''
        gateway_response = {
            'environment_key': environment_key,
            'test_mode': config.get('test_mode', True),
            'active_gateway_type': config.get('active_gateway_type', ''),
            'currency': config.get('currency', 'USD'),
        }
    except Setting.DoesNotExist:
        gateway_response = {
            'environment_key': '',
            'test_mode': True,
            'active_gateway_type': '',
            'currency': 'USD',
        }

    # Include dual pricing config (public fields only — no GL accounts)
    dp_config = get_dual_pricing_config()
    gateway_response['dual_pricing'] = {
        'enabled': dp_config.get('enabled', False),
        'card_rate': dp_config.get('card_rate', 0),
        'disclosure_text': dp_config.get('disclosure_text', '').replace(
            '{rate}', f'{dp_config.get("card_rate", 0):.1f}'
        ),
        'exempt_methods': dp_config.get('exempt_methods', []),
    }

    return Response(gateway_response)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def checkout_pricing(request, invoice_id):
    """Return dual pricing options for an invoice at checkout.

    GET /api/cash/checkout-pricing/<invoice_id>/

    Returns both cash and card totals so the checkout UI can display
    two cash options with the appropriate disclosure text.
    """
    invoice = get_object_or_404(Invoice, pk=invoice_id)
    totals = getattr(invoice, 'totals', None) or {}
    projection = compute_dual_pricing(totals)
    return Response({
        'invoice_id': invoice.id,
        'totals': {
            'amount': totals.get('amount', 0),
            'tax': totals.get('tax', 0),
            'shipping': totals.get('shipping', 0),
        },
        'dual_pricing': projection,
    })



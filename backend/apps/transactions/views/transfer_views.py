from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from django.shortcuts import get_object_or_404

from apps.transactions.models import Proposal, Order, Invoice, Payment
from apps.transactions.services import (
    proposal_to_order,
    order_to_invoice,
    order_to_purchase,
    payment_application,
    inventory_flow,
    validation
)
from apps.transactions.serializers.transfer_serializers import (
    TransferValidationSerializer,
    TransferValidationResponseSerializer,
    TransferRequestSerializer,
    TransferResponseSerializer,
    PaymentApplicationRequestSerializer,
    PaymentApplicationResponseSerializer,
    InventoryReservationRequestSerializer,
    InventoryReservationResponseSerializer,
)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def validate_transfer(request):
    """
    Validate if a transaction can be transferred to the next stage.

    POST /tx/transfers/validate/
    {
        "source_type": "proposal",
        "source_id": 123,
        "target_type": "order"
    }
    """
    serializer = TransferValidationSerializer(data=request.data)
    if not serializer.is_valid():
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    data = serializer.validated_data
    result = validation.validate_transaction_flow(
        data['source_type'],
        data['source_id'],
        data['target_type']
    )

    response_serializer = TransferValidationResponseSerializer(result.to_dict())
    return Response(response_serializer.data)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def execute_transfer(request):
    """
    Execute a transaction transfer via the unified transfer engine.

    POST /tx/transfers/execute/
    {
        "source_type": "proposal",
        "source_id": 123,
        "target_type": "order",
        "line_ids": [1, 2, 3],
        "transfer_all": true,
        "preserve_source": true,
        "target_status": "confirmed"
    }

    Supports all combinations in the transfer matrix:
      proposal → proposal (clone), proposal → order/invoice (convert),
      sell ↔ purchase (cross-type).
    See: readmes/topics/transactions/transaction_transfer.md
    """
    from apps.transactions.services.convert.convert_engine import (
        execute_transfer as do_transfer,
        TransferError,
    )

    serializer = TransferRequestSerializer(data=request.data)
    if not serializer.is_valid():
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    data = serializer.validated_data

    try:
        result = do_transfer(
            source_type=data['source_type'],
            source_id=data['source_id'],
            target_type=data['target_type'],
            line_ids=data.get('line_ids'),
            transfer_all=data.get('transfer_all', True),
            preserve_source=data.get('preserve_source', True),
            target_status=data.get('target_status'),
        )

        response_data = {
            'success': result['success'],
            'target_id': result['target_id'],
            'target_type': result['target_type'],
            'source_id': result['source_id'],
            'source_type': result['source_type'],
            'lines_transferred': result['lines_transferred'],
            'line_mapping': result['line_mapping'],
            'source_preserved': result['source_preserved'],
            'target_status': result['target_status'],
        }

        response_serializer = TransferResponseSerializer(response_data)
        return Response(response_serializer.data)

    except TransferError as e:
        return Response(
            {'error': str(e)},
            status=status.HTTP_400_BAD_REQUEST
        )
    except Exception as e:
        return Response(
            {'error': str(e)},
            status=status.HTTP_400_BAD_REQUEST
        )


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def apply_payment(request):
    """
    Apply a payment to an invoice.

    POST /tx/payments/apply/
    {
        "payment_id": 123,
        "invoice_id": 456,
        "amount": 100.00
    }
    """
    serializer = PaymentApplicationRequestSerializer(data=request.data)
    if not serializer.is_valid():
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    data = serializer.validated_data

    try:
        payment = get_object_or_404(Payment, id=data['payment_id'])
        invoice = get_object_or_404(Invoice, id=data['invoice_id'])

        result = payment_application.apply_payment_to_invoice(
            invoice=invoice,
            payment=payment,
            amount=data.get('amount')
        )

        response_serializer = PaymentApplicationResponseSerializer(result)
        return Response(response_serializer.data)

    except Exception as e:
        return Response(
            {'error': str(e)},
            status=status.HTTP_400_BAD_REQUEST
        )


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def reserve_inventory(request):
    """
    Create inventory reservations for a sales order.

    POST /tx/inventory/reserve/
    {
        "order_id": 123
    }
    """
    serializer = InventoryReservationRequestSerializer(data=request.data)
    if not serializer.is_valid():
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    data = serializer.validated_data

    try:
        order = get_object_or_404(Order, id=data['order_id'])

        result = inventory_flow.reserve_inventory_for_order(order)

        response_serializer = InventoryReservationResponseSerializer(result)
        return Response(response_serializer.data)

    except Exception as e:
        return Response(
            {'error': str(e)},
            status=status.HTTP_400_BAD_REQUEST
        )


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def release_inventory(request, invoice_id):
    """
    Release inventory reservations when invoice is created.

    POST /tx/inventory/release/<invoice_id>/
    """
    try:
        invoice = get_object_or_404(Invoice, id=invoice_id)

        result = inventory_flow.release_inventory_on_invoice(invoice)

        return Response({
            'reservations_released': result['reservations_released'],
            'total_quantity_released': result['total_quantity_released']
        })

    except Exception as e:
        return Response(
            {'error': str(e)},
            status=status.HTTP_400_BAD_REQUEST
        )


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def bulk_transfer_proposals(request):
    """
    Convert multiple proposals to orders in one operation.

    POST /tx/transfers/bulk/proposals-to-orders/
    {
        "proposal_ids": [1, 2, 3],
        "order_status": "confirmed",
        "preserve_proposals": true
    }
    """
    from apps.transactions.services import proposal_to_order

    proposal_ids = request.data.get('proposal_ids', [])
    order_status = request.data.get('order_status', 'confirmed')
    preserve_proposals = request.data.get('preserve_proposals', True)

    if not proposal_ids:
        return Response(
            {'error': 'proposal_ids is required'},
            status=status.HTTP_400_BAD_REQUEST
        )

    results = []
    success_count = 0
    error_count = 0

    for proposal_id in proposal_ids:
        try:
            proposal = get_object_or_404(Proposal, id=proposal_id)

            result = proposal_to_order.transfer_proposal_to_order(
                proposal=proposal,
                line_ids=None,  # Transfer all lines
                transfer_all=True,
                order_status=order_status,
                preserve_proposal=preserve_proposals
            )

            results.append({
                'proposal_id': proposal_id,
                'success': result['success'],
                'order_id': result.get('order_id'),
                'lines_transferred': result.get('lines_transferred')
            })

            if result['success']:
                success_count += 1
            else:
                error_count += 1

        except Exception as e:
            results.append({
                'proposal_id': proposal_id,
                'success': False,
                'error': str(e)
            })
            error_count += 1

    return Response({
        'total_proposals': len(proposal_ids),
        'successful_transfers': success_count,
        'failed_transfers': error_count,
        'results': results
    })


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def bulk_transfer_orders(request):
    """
    Convert multiple orders to invoices in one operation.

    POST /tx/transfers/bulk/orders-to-invoices/
    {
        "order_ids": [1, 2, 3],
        "invoice_status": "sent",
        "preserve_orders": true
    }
    """
    from apps.transactions.services import order_to_invoice

    order_ids = request.data.get('order_ids', [])
    invoice_status = request.data.get('invoice_status', 'sent')
    preserve_orders = request.data.get('preserve_orders', True)

    if not order_ids:
        return Response(
            {'error': 'order_ids is required'},
            status=status.HTTP_400_BAD_REQUEST
        )

    results = []
    success_count = 0
    error_count = 0

    for order_id in order_ids:
        try:
            order = get_object_or_404(Order, id=order_id)

            result = order_to_invoice.transfer_order_to_invoice(
                order=order,
                line_ids=None,  # Transfer all lines
                transfer_all=True,
                invoice_status=invoice_status,
                preserve_order=preserve_orders
            )

            results.append({
                'order_id': order_id,
                'success': result['success'],
                'invoice_id': result.get('invoice_id'),
                'lines_transferred': result.get('lines_transferred')
            })

            if result['success']:
                success_count += 1
            else:
                error_count += 1

        except Exception as e:
            results.append({
                'order_id': order_id,
                'success': False,
                'error': str(e)
            })
            error_count += 1

    return Response({
        'total_orders': len(order_ids),
        'successful_transfers': success_count,
        'failed_transfers': error_count,
        'results': results
    })


__all__ = [
    'validate_transfer',
    'execute_transfer',
    'apply_payment',
    'reserve_inventory',
    'release_inventory',
    'bulk_transfer_proposals',
    'bulk_transfer_orders',
]
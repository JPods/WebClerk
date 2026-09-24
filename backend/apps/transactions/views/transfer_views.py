from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from apps.transactions.services import validate_transaction as validation
from apps.transactions.serializers.transfer_serializer import (
    TransferValidationSerializer,
    TransferValidationResponseSerializer,
)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def validate_transfer(request):
    """
    Validate if a transaction can be transferred to the next stage.

    POST /tx/transfers/validate/
    {
        "source_type": "quote",
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

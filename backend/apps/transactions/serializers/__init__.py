# Header serializers (rich, validated — customer_name, vendor_name, line_count)
from .transaction_serializers import (
    ProposalSerializer, ProposalLineSerializer as ProposalLineRichSerializer,
    OrderSerializer, OrderLineSerializer as OrderLineRichSerializer,
    PurchaseSerializer, PurchaseLineSerializer as PurchaseLineRichSerializer,
    InvoiceSerializer,
    PaymentSerializer, PaymentApplicationSerializer, StatementLineSerializer,
)

# Line serializers (BaseLineSerializer — deep-merge, role filtering, cost validation)
from .line_serializers import (
    BaseLineSerializer,
    ProposalLineSerializer,
    OrderLineSerializer,
    InvoiceLineSerializer,
    PurchaseLineSerializer,
    WorkOrderLineSerializer,
    RequisitionLineSerializer,
    ProjectSerializer,
)

# Transfer serializers (action request/response payloads)
from .transfer_serializers import *

__all__ = [
    # Header serializers
    'ProposalSerializer',
    'OrderSerializer',
    'PurchaseSerializer',
    'InvoiceSerializer',
    'PaymentSerializer',
    'PaymentApplicationSerializer',
    'StatementLineSerializer',

    # Line serializers (deep-merge)
    'BaseLineSerializer',
    'ProposalLineSerializer',
    'OrderLineSerializer',
    'InvoiceLineSerializer',
    'PurchaseLineSerializer',
    'WorkOrderLineSerializer',
    'RequisitionLineSerializer',
    'ProjectSerializer',

    # Transfer serializers
    'TransferValidationSerializer',
    'TransferRequestSerializer',
    'TransferResponseSerializer',
]

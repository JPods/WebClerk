import pytest
from django.core.exceptions import FieldDoesNotExist

from apps.transactions.models import (
    ProposalLine,
    OrderLine,
    InvoiceLine,
    PurchaseOrderLine,
)

try:
    # Optional: WorkOrderLine may belong to a different app or not exist in this build
    from apps.transactions.models import WorkOrderLine  # type: ignore
except ImportError:
    WorkOrderLine = None  # type: ignore


def _has_field(model_cls, field_name: str) -> bool:
    try:
        model_cls._meta.get_field(field_name)
        return True
    except FieldDoesNotExist:
        return False


@pytest.mark.django_db
def test_exec_line_models_do_not_have_price_field():
    models = [PurchaseOrderLine]
    if WorkOrderLine is not None:
        models.append(WorkOrderLine)
    for model in models:
        assert not _has_field(model, "price"), f"{model.__name__} must not define a 'price' field"

@pytest.mark.django_db
@pytest.mark.django_db
def test_exec_line_models_do_not_have_price_field_tuple():
    for model in filter(None, (WorkOrderLine, PurchaseOrderLine)):
        assert not _has_field(model, "price"), f"{model.__name__} must not define a 'price' field"
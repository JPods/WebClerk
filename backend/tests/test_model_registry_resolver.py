import pytest
from apps.core.constants.model_registry import get_model_meta

@pytest.mark.parametrize("token,expected", [
    ("requisition", "requisition"),
    ("Requisition", "requisition"),
    ("requisitions", "requisition"),
    ("Requisitions", "requisition"),
    ("requisition-line", "requisition_line"),
    ("Requisition Line", "requisition_line"),
    ("RequisitionLine", "requisition_line"),
    ("requisition_lines", "requisition_line"),
    ("requisition-lines", "requisition_line"),
])
def test_resolves_variants(token, expected):
    meta = get_model_meta(token)
    assert meta is not None
    assert meta.key == expected

def test_every_registered_model_resolves_in_utils_registry():
    """utils.registry.resolve and the canonical registry name the same class for every key.
    19 snake_case keys (catalog_line, receipt_line, journal_batch) resolved to None there,
    and a superuser's save of one failed with a 500 (wc3, 2026-10-24)."""
    from apps.core.constants.model_registry import MODEL_REGISTRY, get_model
    from apps.core.services import access
    from apps.core.utils import registry
    wrong = {k: registry.resolve(access.model_key(k)) for k in MODEL_REGISTRY
             if registry.resolve(access.model_key(k)) is not get_model(k)}
    assert not wrong, wrong

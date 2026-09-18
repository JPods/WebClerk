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
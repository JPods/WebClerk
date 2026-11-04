"""Every dt_ field renders with the one date-and-time tool or as a stamp (Bill, 2026-11-03).

A plan date (dt_needed, dt_due, dt_start ...) is typed by a person: behavior 'date', the
DtWidget. A system stamp is shown and never typed: 'timestamp' (or 'readonly' for the two
every record carries). The column type does not decide — an epoch column holding a plan date
was read-only in every form until today.
"""
import pytest

from apps.core.constants.model_registry import MODEL_REGISTRY
from apps.core.services.dt_fields import PLAN_DT_FIELDS, SYSTEM_DT_FIELDS
from apps.core.services.field_behaviors import SYSTEM_VIEW_ONLY, get_field_behaviors, get_model_field_map


def _expected(name):
    if name in SYSTEM_VIEW_ONLY:
        return 'readonly'
    return 'timestamp' if name in SYSTEM_DT_FIELDS else 'date'


@pytest.mark.django_db
def test_every_dt_behavior_follows_dt_fields():
    wrong = []
    for model_key in MODEL_REGISTRY:
        field_map = get_model_field_map(model_key)
        if not field_map:
            continue
        behaviors = get_field_behaviors(model_key, field_map)
        for name, beh in behaviors.items():
            if not name.startswith('dt_'):
                continue
            if beh.get('type') != _expected(name):
                wrong.append(f'{model_key}.{name}: {beh.get("type")} (expected {_expected(name)})')
    assert not wrong, wrong


def test_a_plan_date_is_entered_and_a_stamp_is_not():
    assert _expected('dt_needed') == 'date'
    assert _expected('dt_journaled') == 'timestamp'
    assert _expected('dt_created') == 'readonly'
    assert 'dt_cash' in PLAN_DT_FIELDS

"""Every dt_ field on every model is classified system or plan (ratchet R3, Fable review 2026-09-28).

A new dt_ field fails here until it is named in apps/core/services/dt_fields.py, so nobody has
to remember whether the door must refuse it.
"""
from django.apps import apps

from apps.core.services.dt_fields import PLAN_DT_FIELDS, SYSTEM_DT_FIELDS


def _dt_fields():
    for model in apps.get_models():
        for field in model._meta.concrete_fields:
            if field.name.startswith('dt_'):
                yield model._meta.label, field.name


def test_every_dt_field_is_classified():
    unclassified = sorted({f'{label}.{name}' for label, name in _dt_fields()
                           if name not in SYSTEM_DT_FIELDS and name not in PLAN_DT_FIELDS})
    assert not unclassified, ('Name each in apps/core/services/dt_fields.py as a system stamp or '
                              f'a plan date: {unclassified}')


def test_no_dt_field_is_both():
    assert not (SYSTEM_DT_FIELDS & PLAN_DT_FIELDS)


def test_the_journal_mark_is_a_system_stamp():
    assert 'dt_journaled' in SYSTEM_DT_FIELDS

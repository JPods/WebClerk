"""Carrier signals: the `_variables` a record carries, defined once (Bill, 2026-09-22).

"_delete is better... We may have other reasons to create signaling tools between the back and
front that are not subject to view/edit" — individual `_variables`, uniformly defined by a schema.

A signal is not a field: it never reaches a column and the view/edit policy never gates it.
An unknown or ill-typed signal is refused, not dropped.
"""
import pytest

from common.schemas.carrier import CARRIER_KEYS, CarrierBase, CarrierError, read_carrier


def test_the_wire_names_keep_their_underscore():
    assert CARRIER_KEYS == {'_dirty', '_new', '_delete', '_index'}
    carrier = read_carrier({'id': 4, '_delete': True, '_index': 2})
    assert carrier.delete is True and carrier.index == 2
    assert carrier.dirty is True and carrier.new is False          # defaults
    assert CarrierBase(delete=True).model_dump(by_alias=True)['_delete'] is True


def test_a_field_named_with_a_leading_underscore_would_have_validated_nothing():
    """Why the aliases exist: pydantic treats _name as private and drops the field silently.
    A schema written the obvious way has no fields at all."""
    from pydantic import BaseModel

    class Naive(BaseModel):
        _delete: bool = False

    assert list(Naive.model_fields) == []                          # silently empty
    assert Naive(**{'_delete': True}).model_dump() == {}
    assert set(CarrierBase.model_fields) == {'dirty', 'new', 'delete', 'index'}   # ours is not


def test_an_unknown_signal_is_refused_not_ignored():
    with pytest.raises(CarrierError, match='_delte'):
        read_carrier({'_delte': True})                             # a typo used to save "successfully"
    with pytest.raises(CarrierError, match='_delete'):
        read_carrier({'_delete': 'yes please'})


def test_a_record_with_no_signals_is_fine():
    carrier = read_carrier({'id': 1, 'quantity': {'active': 3}})
    assert carrier.delete is False and carrier.dirty is True


@pytest.mark.django_db
def test_the_write_policy_passes_signals_and_refuses_a_strange_one():
    from apps.core.utils.model_policies import enforce_write_policy
    from apps.products.models import Item

    data = {'name': 'CARRIER-1', '_dirty': True, '_delete': False}
    filtered, _denied = enforce_write_policy(Item, data, request=None)
    assert filtered['_dirty'] is True                               # signals reach the save pipeline

    with pytest.raises(CarrierError):
        enforce_write_policy(Item, {'name': 'x', '__dict__': {'is_superuser': True}}, request=None)


@pytest.mark.django_db
def test_a_signal_never_lands_on_a_row():
    from apps.core.services.record_serialize import filter_input_fields
    from apps.transactions.models import OrderLine

    clean = filter_input_fields(OrderLine, {'line_number': 3, '_delete': True, '_dirty': True})
    assert clean == {'line_number': 3}

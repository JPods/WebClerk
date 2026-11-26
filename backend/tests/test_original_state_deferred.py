"""A record is loaded whole and its values captured as loaded, in one query, not a storm
(webclerk-helper, 2026-11-26).

BaseModel captured every field in __init__. On an instance from .only() or refresh_from_db(fields=)
each deferred field was a query that built another instance, whose __init__ did the same: a one-line
quote save ran 345 queries in ~1.1 s, a received receipt save 1,886 in 3.3 s. The deferred fields now
load in one query, so a .only() load still comes back whole (the line snapshot relies on it) and
every reader sees the values it saw before: _compute_changed_fields, audit_pre_save, Action's
dates_moved, roster and parents.
"""
import pytest
from django.db import connection
from django.test.utils import CaptureQueriesContext

from apps.orgs.models import OrgBase
from apps.transactions.models import Quote, QuoteLine


@pytest.fixture(autouse=True)
def _no_pending_dispatch(monkeypatch):
    monkeypatch.setattr("apps.products.dispatch_pending.dispatch_pending_processing",
                        lambda *args, **kwargs: None)


def _quote(n_lines=1):
    customer = OrgBase.objects.create(company="Deferred Co", org_type="customer")
    quote = Quote.objects.create(status='active', customer_id=customer.id, totals={'total': 5})
    lines = [QuoteLine.objects.create(quote=quote, item={'description': f'Item {i}'},
                                      price={'unit': 10.0, 'precision': 2}, cost={'unit': 6.0},
                                      quantity={'active': 2, 'precision': 2}) for i in range(n_lines)]
    return quote, lines


# ── no storm ──────────────────────────────────────────────────────────────

@pytest.mark.django_db
def test_an_instance_with_deferred_fields_is_loaded_whole_in_one_more_query():
    quote, _ = _quote()
    with CaptureQueriesContext(connection) as q:
        partial = Quote.objects.only('id', 'status').get(pk=quote.pk)
    assert len(q.captured_queries) == 2
    assert partial.get_deferred_fields() == set()


@pytest.mark.django_db
def test_refreshing_one_field_refreshes_the_whole_record_in_two_queries():
    """Django copies every field its read instance holds; that instance was always loaded whole, so
    refresh_from_db(fields=['totals']) has always refreshed everything, and callers rely on it: the
    version stays in step (tests/test_money_steps_refuse_incomplete)."""
    quote, _ = _quote()
    held = Quote.objects.get(pk=quote.pk)
    bumped = held.version + 5
    Quote.objects.filter(pk=quote.pk).update(version=bumped, status='planned')
    with CaptureQueriesContext(connection) as q:
        held.refresh_from_db(fields=['totals'])
    assert len(q.captured_queries) == 2
    assert held.version == bumped and held.status == 'planned'


#: Measured 2026-11-26 on a private test DB: a one-line quote save 345 queries before the fix,
#: 69 after; the GET 142 before, 15 after. The ceilings leave room for honest growth and catch
#: the storm (it multiplies, it does not add).
SAVE_CEILING = 90
GET_CEILING = 25


@pytest.mark.django_db
def test_a_one_line_quote_save_and_its_get_stay_under_their_query_ceilings(authenticated_client):
    quote, lines = _quote()
    got = authenticated_client.get(f'/wcapi/quote/{quote.pk}/')
    assert got.status_code == 200
    version = Quote.objects.values_list('version', flat=True).get(pk=quote.pk)
    payload = {'version': version, 'lines': [{'id': lines[0].pk, 'quantity': {'active': 3, 'precision': 2}}]}
    authenticated_client.put(f'/wcapi/quote/{quote.pk}/', payload, format='json')   # warm caches
    payload['version'] = Quote.objects.values_list('version', flat=True).get(pk=quote.pk)
    payload['lines'][0]['quantity']['active'] = 4
    with CaptureQueriesContext(connection) as saved:
        res = authenticated_client.put(f'/wcapi/quote/{quote.pk}/', payload, format='json')
    assert res.status_code == 200, res.content[:300]
    with CaptureQueriesContext(connection) as read:
        assert authenticated_client.get(f'/wcapi/quote/{quote.pk}/').status_code == 200
    assert len(saved.captured_queries) <= SAVE_CEILING, f'save ran {len(saved.captured_queries)} queries'
    assert len(read.captured_queries) <= GET_CEILING, f'get ran {len(read.captured_queries)} queries'


# ── the readers see the values the record was loaded with ─────────────────

@pytest.mark.django_db
def test_a_deferred_field_reads_as_loaded_when_first_asked():
    quote, _ = _quote()
    stored = Quote.objects.values_list('totals', flat=True).get(pk=quote.pk)
    partial = Quote.objects.only('id', 'status').get(pk=quote.pk)
    assert partial._original_state['status'] == 'active'
    assert partial._original_state['totals'] == stored
    assert dict(partial._original_state)['totals'] == stored       # audit_pre_save copies it whole
    assert set(partial._original_state) == {f.attname for f in Quote._meta.fields}


@pytest.mark.django_db
def test_a_deferred_field_assigned_before_it_was_loaded_still_reads_its_database_value():
    quote, _ = _quote()
    stored = Quote.objects.values_list('totals', flat=True).get(pk=quote.pk)
    partial = Quote.objects.only('id', 'status').get(pk=quote.pk)
    partial.totals = {'total': 9}
    assert partial._original_state['totals'] == stored
    assert 'totals' in partial._compute_changed_fields()


@pytest.mark.django_db
def test_a_deferred_field_loaded_by_touching_it_is_captured_as_the_same_object():
    """As before: a field touched at load is captured as the object the instance holds, so an
    in-place edit of a JSON envelope compares equal (unchanged) exactly as it did."""
    quote, _ = _quote()
    partial = Quote.objects.only('id', 'status').get(pk=quote.pk)
    totals = partial.totals                                      # the lazy load
    assert partial._original_state['totals'] is totals
    totals['total'] = 7
    assert 'totals' not in partial._compute_changed_fields()


@pytest.mark.django_db
def test_change_detection_on_a_fully_loaded_record_is_unchanged():
    quote, _ = _quote()
    full = Quote.objects.get(pk=quote.pk)
    assert full._compute_changed_fields() == []
    full.status = 'planned'
    assert full._compute_changed_fields() == ['status']


@pytest.mark.django_db
def test_after_a_save_the_capture_is_taken_again():
    quote, _ = _quote()
    partial = Quote.objects.only('id', 'status').get(pk=quote.pk)
    partial.status = 'planned'
    partial.save(update_fields=['status'])
    assert partial._original_state['status'] == 'planned'
    assert partial._compute_changed_fields() == []


@pytest.mark.django_db
def test_an_action_loaded_with_deferred_fields_keeps_its_roster_and_parents_as_loaded():
    from apps.core.models import Action
    action = Action.objects.create(action={'en': 'Deferred'}, refs={'parents': []},
                                   dt_start=1790000000000, duration=3600000)
    with CaptureQueriesContext(connection) as q:
        partial = Action.objects.only('id', 'status').get(pk=action.pk)
    assert len(q.captured_queries) == 2
    full = Action.objects.get(pk=action.pk)
    assert partial._roster_at_load == full._roster_at_load
    assert partial._parents_at_load == full._parents_at_load == []
    assert partial._original_state['dt_start'] == 1790000000000

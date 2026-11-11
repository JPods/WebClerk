"""Dashboard cards: the server computes the figure over every row the asker may see
(FAULT 20261103T221823: the browser summed r['total'] over 500 rows; the record carries
totals.total, so every card said $0.00)."""
from decimal import Decimal

import pytest

from apps.core.services.dashboard.dd_card_metrics import card_metrics
from apps.core.services.door import Actor, Refused
from apps.transactions.models import Cash, Order

pytestmark = pytest.mark.django_db


@pytest.fixture
def admin(django_user_model):
    return django_user_model.objects.create_superuser(
        email='cards@example.com', password=None, name_first='Card', name_last='Admin', username='')


def _order(total, cost, margin_pc, **kw):
    return Order.objects.create(status='planned', totals={'total': total, 'cost': cost, 'margin_pc': margin_pc}, **kw)


def test_sums_count_and_margin_over_json_paths(admin):
    _order(100.0, 60.0, 40.0)
    _order(50.0, 10.0, 80.0)
    _order(999.0, 1.0, 1.0, is_active=False)
    out = card_metrics({'model': 'order', 'filters': {'is_active': True}, 'metrics': [
        {'field': 'id', 'agg': 'count', 'label': 'Count'},
        {'field': 'totals.total', 'agg': 'sum', 'label': 'Value', 'format': 'currency'},
        {'agg': 'margin_pct', 'fields': ['totals.total', 'totals.cost'], 'label': 'Margin', 'format': 'percent'},
    ], 'distribution': {'field': 'totals.margin_pc', 'buckets': [10, 25, 40], 'labels': ['<10%', '10-25%', '25-40%', '>40%']}},
        Actor(user=admin, kind='user'))
    assert [(m['label'], m['value'], m.get('format')) for m in out['metrics']] == [
        ('Count', 2, None), ('Value', 150.0, 'currency'), ('Margin', pytest.approx(53.33, abs=0.01), 'percent')]
    assert [(d['label'], d['count']) for d in out['distribution']] == [
        ('<10%', 0), ('10-25%', 0), ('25-40%', 0), ('>40%', 2)]


def test_a_metric_filter_applies_to_that_metric_only(admin):
    Cash.objects.create(amount=Decimal('100'), available=Decimal('100'), status='complete')
    Cash.objects.create(amount=Decimal('-30'), available=Decimal('0'), status='complete')
    out = card_metrics({'model': 'cash', 'filters': {'is_active': True}, 'metrics': [
        {'field': 'id', 'agg': 'count', 'label': 'Count'},
        {'field': 'amount', 'agg': 'sum', 'label': 'Received', 'filters': {'amount__gt': 0}},
        {'field': 'amount', 'agg': 'sum', 'label': 'Disbursed', 'filters': {'amount__lt': 0}},
    ]}, Actor(user=admin, kind='user'))
    assert [(m['label'], float(m['value'])) for m in out['metrics']] == [
        ('Count', 2), ('Received', 100.0), ('Disbursed', -30.0)]


def test_a_path_the_model_lacks_is_refused(admin):
    with pytest.raises(Refused) as refused:
        card_metrics({'model': 'order', 'metrics': [{'field': 'total', 'agg': 'sum', 'label': 'Value'}]},
                     Actor(user=admin, kind='user'))
    assert refused.value.code == 'unknown_field' and 'totals.total' in refused.value.message


def test_a_row_above_the_viewers_level_is_left_out(django_user_model):
    """The card's rows are the list's rows: an agent's ceiling is 4, so a level-8 order is
    neither listed nor totalled (the lead's review of 431dc55)."""
    _order(100.0, 60.0, 40.0, security_level=2)
    _order(1000.0, 60.0, 40.0, security_level=8)
    agent = django_user_model.objects.create_user(
        email='agent@example.com', password=None, name_first='An', name_last='Agent', role='agent')
    out = card_metrics({'model': 'order', 'metrics': [
        {'field': 'id', 'agg': 'count', 'label': 'Count'},
        {'field': 'totals.total', 'agg': 'sum', 'label': 'Value'}]}, Actor(user=agent, kind='user'))
    assert [(m['label'], m['value']) for m in out['metrics']] == [('Count', 1), ('Value', 100.0)]


def test_every_row_tallies_whatever_its_ida(admin):
    """No ida prefix leaves a record out of a figure (Bill, 2026-11-11: zz and qq removed)."""
    _order(100.0, 60.0, 40.0, ida='ORD-1')
    _order(500.0, 60.0, 40.0, ida='t-training')
    _order(700.0, 60.0, 40.0, ida='QQ-sim')
    out = card_metrics({'model': 'order', 'metrics': [
        {'field': 'id', 'agg': 'count', 'label': 'Count'},
        {'field': 'totals.total', 'agg': 'sum', 'label': 'Value'}]}, Actor(user=admin, kind='user'))
    assert [(m['label'], m['value']) for m in out['metrics']] == [('Count', 3), ('Value', 1300.0)]


def test_rows_the_asker_may_not_see_do_not_count(django_user_model):
    _order(100.0, 60.0, 40.0)
    nobody = django_user_model.objects.create_user(
        email='nobody@example.com', password=None, name_first='No', name_last='Body', role='')
    out = card_metrics({'model': 'order', 'metrics': [{'field': 'totals.total', 'agg': 'sum', 'label': 'Value'}]},
                       Actor(user=nobody, kind='user'))
    assert out['metrics'][0]['value'] == 0

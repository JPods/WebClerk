"""The browser computes totals while editing; the server serves its inputs and checks its answer
(Bill, 2026-11-08; readme 107). The arithmetic match itself is test_totals_fixture.py."""
import logging

import pytest

from apps.core.models import Setting
from apps.core.services.door import Actor
from apps.core.services.save import save_record
from apps.orgs.models import OrgBase
from apps.transactions.models import Order, OrderLine
from tests.conftest import make_setting


@pytest.fixture(autouse=True)
def _no_pending_dispatch(monkeypatch):
    monkeypatch.setattr("apps.products.dispatch_pending.dispatch_pending_processing",
                        lambda *args, **kwargs: None)


@pytest.fixture
def admin(django_user_model):
    return django_user_model.objects.create_user(email='browser-totals@test.com', password='x',
                                                 username='', role='admin')


def _order(buyer=None):
    order = Order.objects.create(status='active', customer_id=getattr(buyer, 'pk', None),
                                 finance={"sales_tax_rate": 10})
    OrderLine.objects.create(order=order, item={'description': 'Widget'}, line_number=1,
                             price={'unit': 10.0, 'precision': 2}, cost={'unit': 6.0},
                             quantity={'active': 3, 'precision': 2})
    return order


@pytest.mark.django_db
def test_the_get_carries_what_the_browser_engine_reads(client, admin):
    client.force_login(admin)
    buyer = OrgBase.objects.create(company='zz Exempt Co', org_type='customer', is_active=True,
                                   financial={'common': {'settings': {'tax_exempt': True}}})
    services = [{'name': 'UPS Ground', 'carrier_code': 'UPSG', 'rate_method': 'percent_of_goods',
                 'rate_percent': 4, 'comment': 'not served', 'connection_id': 1}]
    setting = Setting.objects.filter(purpose='wc:shipping_service').first()
    if setting is None:
        make_setting(purpose='wc:shipping_service', name='shipping_service', is_active=True,
                     config={'service': services})
    else:
        setting.is_active, setting.config = True, {**(setting.config or {}), 'service': services}
        setting.save()
    order = _order(buyer)

    ctx = client.get(f'/wcapi/order/{order.pk}/').json()['data']['record']['calc_context']

    assert ctx['customer_exempt'] is True
    assert set(ctx['tax_policy']) == {'tax_on_shipping', 'tax_on_costs'}
    assert ctx['shipping_services'] == [{'name': 'UPS Ground', 'carrier_code': 'UPSG',
                                         'rate_method': 'percent_of_goods', 'rate_percent': 4}]
    # Served, never stored: the key is not a field.
    assert not hasattr(Order, 'calc_context')


@pytest.mark.django_db
def test_a_preview_that_matches_says_nothing(admin, caplog):
    order = _order()
    with caplog.at_level(logging.WARNING, logger='apps.transactions.services.browser_totals'):
        result = save_record(Actor(user=admin), {'id': order.pk, 'conditions_description': 'checked',
                                                 '_totals_preview': {'amount': 30, 'tax': 3, 'total': 33}},
                             model_key='order')
    assert not [m for m in result.messages if 'shown while editing' in m]
    assert not [r for r in caplog.records if r.name == 'apps.transactions.services.browser_totals']
    order.refresh_from_db()
    assert order.totals['total'] == 33.0


@pytest.mark.django_db
def test_a_preview_that_differs_is_logged_and_said_not_refused(admin, caplog):
    order = _order()
    with caplog.at_level(logging.WARNING, logger='apps.transactions.services.browser_totals'):
        result = save_record(Actor(user=admin), {'id': order.pk, 'conditions_description': 'drifted',
                                                 '_totals_preview': {'amount': 30, 'tax': 3, 'total': 152.04}},
                             model_key='order')
    assert result.messages[-1] == 'The total shown while editing was 152.04; the save computed 33.00. The saved figures stand.'
    assert 'total browser 152.04 saved 33.00' in caplog.text
    order.refresh_from_db()
    assert order.conditions_description == 'drifted'           # saved all the same
    assert order.totals['total'] == 33.0      # the server's figure stands


@pytest.mark.django_db
def test_a_line_change_with_its_matching_preview_in_one_payload_says_nothing(admin, caplog):
    """The real case: the person changed a quantity, the browser showed the new figure, and the
    save carries both. The check runs after the recompute, so the figures agree."""
    order = _order()
    line = order.lines.get()
    with caplog.at_level(logging.WARNING, logger='apps.transactions.services.browser_totals'):
        result = save_record(Actor(user=admin), {
            'id': order.pk,
            'lines': [{'id': line.pk, 'quantity': {**line.quantity, 'active': 7}, '_dirty': True}],
            '_totals_preview': {'amount': 70, 'tax': 7, 'shipping': 0, 'other': 0, 'total': 77},
        }, model_key='order')
    assert not [m for m in result.messages if 'shown while editing' in m]
    assert not [r for r in caplog.records if r.name == 'apps.transactions.services.browser_totals']
    order.refresh_from_db()
    assert order.totals['amount'] == 70.0 and order.totals['total'] == 77.0
    # The stale figure (the totals before the change) would have been reported.
    result = save_record(Actor(user=admin), {
        'id': order.pk,
        'lines': [{'id': line.pk, 'quantity': {**line.quantity, 'active': 8}, '_dirty': True}],
        '_totals_preview': {'total': 77},
    }, model_key='order')
    assert result.messages[-1] == 'The total shown while editing was 77.00; the save computed 88.00. The saved figures stand.'

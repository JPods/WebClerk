import pytest
from rest_framework.test import APIClient
from apps.transactions.models import Quote, QuoteLine
from apps.core.models.setting import Setting
from django.utils.crypto import get_random_string

from tests.conftest import make_setting


def _auth_client(user):
    from rest_framework_simplejwt.tokens import RefreshToken
    client = APIClient()
    client.credentials(HTTP_AUTHORIZATION=f'Bearer {RefreshToken.for_user(user).access_token}')
    return client

# ---------------------------------------------------------------------------
# Role matrix — the rules endpoint reports what RBAC enforces
# ---------------------------------------------------------------------------

def _rules(user, model_name='invoice', pk=None):
    """Call the field rules endpoint as this user (None = unauthenticated)."""
    from rest_framework.test import APIRequestFactory, force_authenticate
    from apps.core.views.field_rules_view import FieldRulesView

    url = f'/wcapi/{model_name}/fields/' + (f'?id={pk}' if pk else '')
    request = APIRequestFactory().get(url)
    if user is not None:
        force_authenticate(request, user=user)
    return FieldRulesView.as_view()(request, model_name=model_name)


def _portal_user(django_user_model, email, role, org_kind):
    """A login is a Contact; its role is contact.role (access.py)."""
    from apps.orgs.models import OrgBase

    org = OrgBase.objects.create(display_name=f'{org_kind} co', org_type=org_kind,
                                 price_level='wholesale')
    return django_user_model.objects.create_user(
        email=email, password=get_random_string(20), role=role,
        name_first='P', name_last='U', **{org_kind: org})


@pytest.mark.django_db
def test_unauthenticated_caller_gets_no_rules():
    """The rules endpoint needs a login."""
    assert _rules(None).status_code == 401


@pytest.mark.django_db
@pytest.mark.parametrize('role,org_kind', [
    ('customer', 'customer'),
    ('vendor', 'vendor'),
])
def test_portal_users_edit_nothing(django_user_model, role, org_kind):
    """Editing is staff-only for now (Bill, 2026-09-17)."""
    user = _portal_user(django_user_model, f'{role}@example.fake', role, org_kind)
    model = 'invoice' if org_kind == 'customer' else 'purchase'
    data = _rules(user, model_name=model).data['data']
    assert data['edit'] == []
    assert data['source'] == 'rbac'


@pytest.mark.django_db
def test_staff_edits_everything_except_what_a_record_locks(django_user_model):
    from apps.transactions.models import Invoice

    user = django_user_model.objects.create_superuser(
        email='staff_rules@example.fake', password=get_random_string(20),
        name_first='S', name_last='T', username='')
    invoice = Invoice.objects.create(status='planned', totals={'total': 100})

    open_data = _rules(user, pk=invoice.pk).data['data']
    assert '*' not in open_data['edit']              # a list of leaves, never a wildcard
    assert 'totals.total' in open_data['edit']
    assert open_data['locked'] == []

    invoice.is_locked = True
    invoice.save(update_fields=['is_locked'])

    locked_data = _rules(user, pk=invoice.pk).data['data']
    assert 'totals' in locked_data['locked']
    assert 'totals' in locked_data['edit_deny']   # even for a superuser
    assert not any(f.startswith('totals.') for f in locked_data['edit'])


@pytest.mark.django_db
def test_customer_rules_hide_costs(django_user_model):
    """The customer item policy (Bill, 2026-09-17) as data: their price tier, no cost."""
    from apps.core.services import access
    item = Setting.objects.get(purpose='wc:model', parent_model='item')
    cfg = dict(item.config)
    cfg['access'] = {**cfg['access'], 'roles': {**cfg['access']['roles'], 'customer': {
        'view': ['id', 'ida', 'name', 'price.$user.price_level'], 'edit': [], 'scope': {}}}}
    item.config = cfg
    item._setting_update_authorized = True
    item.save()
    access.clear_cache()

    user = _portal_user(django_user_model, 'cust_rules@example.fake', 'customer', 'customer')
    data = _rules(user, model_name='item').data['data']
    assert not any(f == 'cost' or f.startswith('cost.') for f in data['view'])
    assert 'price.wholesale' in data['view']   # their level, resolved


@pytest.mark.django_db
def test_journalized_write_is_refused_not_just_hidden():
    """The rules endpoint reports; the model refuses. A locked total cannot be written
    by any path, and the message says how to proceed."""
    from apps.transactions.models import Invoice, InvoiceLine
    from apps.transactions.models.base_transaction_model import JournalizedLockError
    from apps.transactions.models.base_line_model import JournalizedLineError

    invoice = Invoice.objects.create(status='planned', totals={'total': 100})
    line = InvoiceLine.objects.create(invoice=invoice, quantity={'staged': 1, 'active': 1},
                                      price={'unit': 100, 'amount': 100})
    invoice.is_locked = True
    invoice.save(update_fields=['is_locked'])

    invoice.totals = {**invoice.totals, 'total': 999}
    with pytest.raises(JournalizedLockError) as err:
        invoice.save()
    assert 'Reverse the journal entry first' in str(err.value)

    # Cash is not locked: received/balance/cash_state may still move
    invoice.refresh_from_db()
    invoice.totals = {**invoice.totals, 'received': 40, 'balance': 60, 'cash_state': 'partial'}
    invoice.save()

    # A line under a journalized document cannot change its quantity or price
    line.refresh_from_db()
    line.quantity = {**line.quantity, 'active': 5}
    with pytest.raises(JournalizedLineError):
        line.save()

    # Operational fields and comments stay open
    line.refresh_from_db()
    line.status = 'shipped'
    line.save()
    invoice.refresh_from_db()
    invoice.add_comment('process', 'customer called about this invoice', use_linkage=False)

"""An admin or a superuser may change a posting document's dt_created (Bill, 2026-11-27).

"I think dt_created will be best. It is simple. If they need to adjust it, an admin or superuser
can adjust it." A posting document's dt_created is the period of its journal rows
(GlJournal.dt_document), so it changes until the document is journalized and not after.
"""
import pytest

from apps.core.models import Action, Contact
from apps.core.services.door import Actor, Refused
from apps.core.services.save import save_record
from apps.transactions.models import Invoice

pytestmark = pytest.mark.django_db

OCTOBER = 1793000000000


@pytest.fixture
def people():
    def person(email, **kw):
        return Actor(user=Contact.objects.create(email=email, is_staff=True, **kw))
    return {'su': person('su-date@example.com', is_superuser=True),
            'admin': person('admin-date@example.com', role='admin'),
            'accounting': person('acct-date@example.com', role='accounting')}


@pytest.fixture
def invoice(db):
    from apps.orgs.models import OrgBase
    buyer = OrgBase.objects.create(company='Document Date Customer', org_type='customer', is_active=True)
    return Invoice.objects.create(customer_id=buyer.pk, status='planned')


def _set_date(actor, invoice, **extra):
    return save_record(actor, {'id': invoice.pk, 'version': invoice.version, 'dt_created': OCTOBER,
                               **extra}, model_key='invoice')


@pytest.mark.parametrize('who', ['admin', 'su'])
def test_an_admin_or_superuser_changes_the_document_date(people, invoice, who):
    _set_date(people[who], invoice, _unlock=['dt_created'])
    assert Invoice.objects.get(pk=invoice.pk).dt_created == OCTOBER


def test_without_unlock_the_date_is_refused_and_the_coaching_names_the_admin(people, invoice):
    with pytest.raises(Refused) as refused:
        _set_date(people['admin'], invoice)
    assert refused.value.code == 'system_field' and 'An admin or a superuser' in refused.value.message
    assert Invoice.objects.get(pk=invoice.pk).dt_created != OCTOBER


def test_another_role_does_not_unlock_it(people, invoice):
    from apps.core.services.save import _read_unlock
    with pytest.raises(Refused) as refused:
        _read_unlock(people['accounting'], {'dt_created': OCTOBER, '_unlock': ['dt_created']},
                     invoice, 'invoice')
    assert refused.value.code == 'unlock_superuser_only'


def test_an_admin_unlocks_nothing_else(people, invoice):
    for names in (['ida'], ['dt_created', 'dt_journaled']):
        with pytest.raises(Refused) as refused:
            _set_date(people['admin'], invoice, _unlock=names)
        assert refused.value.code == 'unlock_superuser_only', names
    action = Action.objects.create(status='open', security_level=1)
    with pytest.raises(Refused) as refused:          # not a posting document
        save_record(people['admin'], {'model_name': 'action', 'id': action.pk, 'dt_created': OCTOBER,
                                      '_unlock': ['dt_created']})
    assert refused.value.code == 'unlock_superuser_only'


@pytest.mark.parametrize('who', ['admin', 'su'])
def test_a_journalized_document_keeps_its_date(people, invoice, who):
    Invoice.objects.filter(pk=invoice.pk).update(dt_journaled=1795000000000)
    invoice.refresh_from_db()
    with pytest.raises(Refused) as refused:
        _set_date(people[who], invoice, _unlock=['dt_created'])
    assert refused.value.code == 'document_date_journalized'
    assert 'Unjournalize' in refused.value.message
